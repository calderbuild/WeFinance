#!/usr/bin/env python3
"""wefinance-ocr -- Anna Executa Tool: bill/receipt photo -> structured transactions.

Ports services/vision_ocr_service.py's "count first, then extract" Vision OCR
prompt and its robust JSON parsing / field-fixup logic. Speaks JSON-RPC 2.0
over stdio (Anna Executa protocol v2).

The image goes to the model through Anna's Agent Sessions family
(host_capabilities: ["llm.sample", "llm.agent.auto"]):

    agent/session.create(agent_submode="auto")
    agent/session.run(content=prompt, allowed_tools=[],
                      attachments=[{"type": "image/png", "data": "<base64>",
                                    "filename": "bill.png"}])
    agent/session.delete(...)

`attachments` on session.run is the only image input Anna documents
(llm-and-agent.md section 3.0a, "the same field works on the plugin path").
agent/complete (v0.2.0-v0.2.2) does NOT carry images: calling
/copilot/app/complete directly on 2026-09-22 with the image as an MCP
`{type: image, data, mimeType}` block, an OpenAI `image_url` block and an
Anthropic `source` block all returned "no image visible", and the
gemini-2.5-flash hint was routed to google/gemini-2.5-flash-image anyway.
The model answered the prompt blind, which is how a US card statement came
back as invented CNY convenience-store rows, or as zero transactions.

Same probe against /copilot/app/agent with `attachments` read every merchant
and amount correctly (google/gemini-3-flash-preview under the "gemini" hint,
qwen3.7-plus with no hint). allowed_tools=[] keeps the run a pure model
reply: v0.1.x never passed it and died with OpenRouter's "No endpoints found
that support tool use" once tools were inherited.

Deploying: publish/cut/submit-review only registers a build. The agent keeps
running its old binary until Executa Hub -> My Tools -> Install pushes it.

Wire protocol notes:
- session.run is buffered streaming: the host returns {run_id, stream_id,
  frames, final} once the run ends. Text arrives as 'sse' frames wrapping
  OpenAI-style chunks (choices[0].delta.content); a provider failure rides
  in on an 'sse' frame as a top-level `error` string.
- initialize()'s "capabilities" key (not "client_capabilities") is confirmed
  correct -- see wefinance_chat.py's module docstring for the full reasoning;
  same applies here, extended with an empty "agent": {} entry since this tool
  also negotiates the Agent Sessions family (executa-lifecycle.md: "an empty
  object is fine -- it means I'm aware of this capability, no extra
  options").
"""

import base64
import binascii
import hashlib
import json
import math
import queue
import re
import sys
import threading
import uuid
from datetime import date, datetime

MANIFEST = {
    "name": "wefinance-ocr",
    "display_name": "WeFinance Bill Scanner",
    "version": "0.2.4",
    "description": "Extract structured transactions from a photo of a bill, receipt, or payment screenshot.",
    "author": "calderbuild",
    "host_capabilities": ["llm.sample", "llm.agent.auto"],
    "runtime": {"type": "uv", "min_version": "0.1.0"},
    "tools": [
        {
            "name": "extract_transactions",
            "description": "Analyze a bill/receipt/payment-screenshot image and return every transaction found in it.",
            "parameters": [
                {
                    "name": "image_base64",
                    "type": "string",
                    "description": "Base64-encoded image bytes (no data: URI prefix).",
                    "required": True,
                },
                {
                    "name": "image_type",
                    "type": "string",
                    "description": "MIME type of the image, e.g. image/jpeg, image/png.",
                    "required": True,
                },
            ],
        }
    ],
}

TYPO_FIELD_MAP = {
    "amout": "amount",
    "marchant": "merchant",
    "catagory": "category",
}

# English prompt + English categories: the App UI and its "Other" fallbacks
# (app.js, wefinance-recommend) are English. The example uses a placeholder
# merchant on purpose -- a realistic one gets echoed back when the model
# can't read the image.
OCR_PROMPT = """You extract transactions from financial documents. Read the attached image (a bill, receipt, bank or card statement, or payment screenshot) and extract every transaction in it.

Rules:
1. First count the transactions: each separate line with its own amount is one transaction. Then extract each one, so the length of "transactions" equals "transaction_count".
2. Total, subtotal, balance and payment-due lines are only for cross-checking. Never report them as transactions.
3. Report only what is actually visible in the image. Never invent merchants, dates or amounts.
4. If no image is attached or you cannot read it, return exactly {"transaction_count": 0, "transactions": [], "error": "no_image"}.

Fields for each transaction:
- date: YYYY-MM-DD, or null if the image doesn't show one. Today's date is given at the end of this message. Resolve relative dates ("today", "yesterday", a weekday name) against it. If the year isn't shown, use the most recent year that doesn't put the date after today, and list "date" in inferred_fields.
- merchant: the merchant or payee exactly as written, in its original language (do not translate); "Unknown Merchant" if none is shown
- category: one of Dining, Groceries, Transport, Shopping, Entertainment, Healthcare, Education, Housing, Utilities, Other
- amount: a number without currency symbols. Money spent is positive. Refunds and other money coming back to the payer (shown with "+", or labelled refund / 退款) are negative, so they cancel the original purchase.
- currency: ISO 4217 code. "$" means USD unless marked otherwise ("S$" is SGD, "HK$" is HKD); "¥", "元" or "RMB" means CNY; "RM" means MYR; "฿" means THB; "₩" means KRW; "€" means EUR; "£" means GBP. With no symbol, infer it from the document's language and country.
- partial_data: true if any field was inferred rather than read from the image
- inferred_fields: names of the inferred fields, e.g. ["category"]

Return a single JSON object and nothing else (no markdown code fences):
{"transaction_count": 1, "transactions": [{"date": "2026-01-01", "merchant": "Example Store", "category": "Shopping", "amount": 10.0, "currency": "USD", "partial_data": false, "inferred_fields": []}]}

If the image shows no transactions, return {"transaction_count": 0, "transactions": []}."""


# --- JSON parsing / field fixup (ported from vision_ocr_service.py, no
#     dateutil/pydantic -- the Tool subprocess only has stdlib available) ---


def _strip_markdown_fences(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _try_json_load(payload: str):
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "transactions" in data and isinstance(data["transactions"], list):
            return data
        return [data]
    return None


def _apply_typo_fix(entry: dict) -> dict:
    for typo, correct in TYPO_FIELD_MAP.items():
        if typo in entry and correct not in entry:
            entry[correct] = entry.pop(typo)
    return entry


def _fix_entries(items) -> list:
    return [_apply_typo_fix(dict(entry)) for entry in items]


def _robust_json_parse(content: str) -> dict:
    """Returns {"transaction_count": int, "transactions": [...], "error": str|None}."""

    text = _strip_markdown_fences(content or "")

    direct = _try_json_load(text)
    if direct is not None:
        if isinstance(direct, dict):
            return {
                "transaction_count": direct.get(
                    "transaction_count", len(direct["transactions"])
                ),
                "transactions": _fix_entries(direct["transactions"]),
                "error": direct.get("error"),
            }
        return {"transaction_count": len(direct), "transactions": _fix_entries(direct)}

    array_match = re.search(r"\[\s*\{.*\}\s*\]", text, re.DOTALL)
    if array_match:
        parsed = _try_json_load(array_match.group(0))
        if parsed is not None:
            rows = parsed if isinstance(parsed, list) else parsed["transactions"]
            return {"transaction_count": len(rows), "transactions": _fix_entries(rows)}

    object_matches = re.findall(r"\{[^{}]+\}", text)
    if len(object_matches) > 1:
        joined = "[" + ",".join(object_matches) + "]"
        parsed = _try_json_load(joined)
        if parsed is not None:
            rows = parsed if isinstance(parsed, list) else parsed["transactions"]
            return {"transaction_count": len(rows), "transactions": _fix_entries(rows)}

    typo_fixed = text
    for typo, correct in TYPO_FIELD_MAP.items():
        typo_fixed = typo_fixed.replace(f'"{typo}"', f'"{correct}"')
        typo_fixed = typo_fixed.replace(typo, correct)
    fallback = _try_json_load(typo_fixed)
    if fallback is not None:
        rows = fallback if isinstance(fallback, list) else fallback["transactions"]
        return {"transaction_count": len(rows), "transactions": _fix_entries(rows)}

    # Raise instead of returning []: a non-JSON reply (e.g. "I can't see an
    # image") used to surface as "No transactions found in that image."
    # The reply is receipt text, so only its length goes into the error.
    raise RuntimeError(
        f"Bill Scanner couldn't read a transaction list from the model's reply "
        f"({len(text)} characters). Please try again."
    )


_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%m/%d/%Y", "%d/%m/%Y")


def _parse_date(raw) -> str:
    if not raw:
        return date.today().isoformat()
    text = str(raw).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    iso_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if iso_match:
        return iso_match.group(0)
    return date.today().isoformat()


def _generate_transaction_id(
    merchant: str,
    date_value: str,
    amount: float,
    currency: str,
    source_hash: str,
    sequence: int,
) -> str:
    merchant_key = (merchant or "").strip().lower()
    currency_key = (currency or "CNY").strip().upper()
    parts = [
        merchant_key,
        date_value,
        f"{float(amount):.2f}",
        currency_key,
        source_hash,
        str(sequence),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


# Every field here is read off an image someone else may have written, so the
# row that leaves this tool is rebuilt from known fields with known shapes
# instead of passing the model's dict through.
CATEGORIES = {
    "Dining",
    "Groceries",
    "Transport",
    "Shopping",
    "Entertainment",
    "Healthcare",
    "Education",
    "Housing",
    "Utilities",
    "Other",
}
MAX_MERCHANT_LEN = 80
INFERABLE_FIELDS = {"date", "merchant", "category", "amount", "currency"}
# The prompt asks for ISO codes, but a symbol sometimes slips through. Map the
# common ones; anything else falls back to CNY and is marked as a guess.
CURRENCY_SYMBOLS = {"$": "USD", "¥": "CNY", "元": "CNY", "RMB": "CNY", "€": "EUR", "£": "GBP"}


def _validate_and_fix_transaction(item: dict, idx: int, source_hash: str):
    if not isinstance(item, dict):
        print(f"Transaction {idx} is not an object, skipping", file=sys.stderr)
        return None
    raw = dict(item)
    for typo, correct in TYPO_FIELD_MAP.items():
        if typo in raw and correct not in raw:
            raw[correct] = raw.pop(typo)

    try:
        amount = float(raw["amount"])
    except (KeyError, TypeError, ValueError):
        print(f"Transaction {idx} has no numeric amount, skipping", file=sys.stderr)
        return None
    if not math.isfinite(amount):
        print(f"Transaction {idx} has a non-finite amount, skipping", file=sys.stderr)
        return None

    merchant = " ".join(str(raw.get("merchant") or "").split())[:MAX_MERCHANT_LEN]
    category = str(raw.get("category") or "").strip().title()
    currency = str(raw.get("currency") or "").strip().upper()
    currency = CURRENCY_SYMBOLS.get(currency, currency)
    inferred = raw.get("inferred_fields")
    inferred = [f for f in inferred if f in INFERABLE_FIELDS] if isinstance(inferred, list) else []
    partial = raw.get("partial_data") is True
    if not re.fullmatch(r"[A-Z]{3}", currency):
        currency, partial = "CNY", True
        inferred = sorted(set(inferred) | {"currency"})
    payload = {
        "date": _parse_date(raw.get("date")),
        "merchant": merchant or "Unknown Merchant",
        "category": category if category in CATEGORIES else "Other",
        "amount": amount,
        "currency": currency,
        "partial_data": partial,
        "inferred_fields": inferred,
    }
    payload["id"] = _generate_transaction_id(
        merchant=payload["merchant"],
        date_value=payload["date"],
        amount=payload["amount"],
        currency=payload["currency"],
        source_hash=source_hash,
        sequence=idx,
    )
    return payload


# --- Error-code mapping (executa-agent.md's "Error codes" table; AgentError
#     shares its base class with SamplingError in the official SDKs, so we
#     mirror the same {data.errorCode -> friendly message} pattern here) ----

AGENT_ERROR_MESSAGES = {
    "AGENT_NOT_GRANTED": "Agent Sessions aren't enabled for WeFinance Bill Scanner yet -- turn it on in Anna Admin.",
    "AGENT_INVALID_SUBMODE": "Internal error: invalid agent submode (this is a WeFinance bug, not you).",
    "AGENT_FIXED_REQUIRES_CLIENT_ID": "Internal error: fixed-mode session missing a client id (this is a WeFinance bug, not you).",
    "AGENT_UNKNOWN_SESSION": "The scan session expired before we could finish -- please try uploading again.",
    "AGENT_INVALID_UUID": "Internal error: session id mismatch (this is a WeFinance bug, not you).",
    "AGENT_NEXUS_ERROR": "The scanning backend had an error. Try again in a moment.",
    "AGENT_RUN_TOO_LARGE": "This image needed too many steps to process -- try a clearer or simpler photo.",
    "AGENT_TOOL_NOT_GRANTED": "Internal error: requested a tool this session isn't allowed to use.",
    "APP_MODEL_NOT_VISION_CAPABLE": "The selected model can't read images -- pick a vision-capable model in Anna settings.",
}

AGENT_ERROR_CODES_BY_NUMBER = {
    -32041: "AGENT_NOT_GRANTED",
    -32042: "AGENT_INVALID_SUBMODE",
    -32043: "AGENT_FIXED_REQUIRES_CLIENT_ID",
    -32044: "AGENT_UNKNOWN_SESSION",
    -32045: "AGENT_INVALID_UUID",
    -32046: "AGENT_NEXUS_ERROR",
    -32047: "AGENT_RUN_TOO_LARGE",
    -32048: "AGENT_TOOL_NOT_GRANTED",
}


def _friendly_agent_error(error: dict) -> str:
    data = error.get("data") if isinstance(error, dict) else None
    code_name: str = ""
    if isinstance(data, dict) and isinstance(data.get("errorCode"), str):
        code_name = data["errorCode"]
    if not code_name:
        code_num = error.get("code") if isinstance(error, dict) else None
        code_name = (
            AGENT_ERROR_CODES_BY_NUMBER.get(code_num, "")
            if isinstance(code_num, int)
            else ""
        )
    return AGENT_ERROR_MESSAGES.get(code_name, str(error))


# --- Reverse-RPC (Agent Sessions) plumbing ----------------------------------

agent_requests: queue.Queue = queue.Queue()
host_responses: dict = {}
v2_negotiated = False


def _reader() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"bad json: {exc}", file=sys.stderr)
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
            )
            continue
        try:
            if not isinstance(msg, dict):
                print(f"ignoring non-object frame: {msg!r}", file=sys.stderr)
                continue
            if "method" in msg:
                agent_requests.put(msg)
            else:
                q = host_responses.pop(msg.get("id"), None)
                if q is not None:
                    q.put(msg)
        except Exception as exc:  # noqa: BLE001
            print(f"reader routing error (continuing): {exc}", file=sys.stderr)


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _call(method: str, params: dict, timeout: float) -> dict:
    rid = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    host_responses[rid] = q
    _send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
    resp = q.get(timeout=timeout)
    if "error" in resp:
        raise RuntimeError(_friendly_agent_error(resp["error"]))
    return resp["result"]


def create_session() -> str:
    if not v2_negotiated:
        raise RuntimeError(
            "Agent Sessions unavailable: host did not negotiate protocol v2 for this session."
        )
    result = _call(
        "agent/session.create",
        {
            "agent_submode": "auto",
            "label": "WeFinance Bill Scanner",
            "ttl_seconds": 300,
        },
        timeout=25,
    )
    return result["app_session_uuid"]


def run_session(app_session_uuid: str, prompt: str, attachment: dict) -> str:
    result = _call(
        "agent/session.run",
        {
            "app_session_uuid": app_session_uuid,
            "content": prompt,
            "attachments": [attachment],
            # Pure model reply: no tool calls, so no tool-use-only routing.
            "allowed_tools": [],
            "recursion_limit": 2,
            # "gemini" is the vision hint llm-and-agent.md itself uses; it
            # routed to google/gemini-3-flash-preview in the 2026-09-22 probe.
            "modelPreferences": {"hints": [{"name": "gemini"}]},
        },
        # executa-lifecycle.md documents a 60s default invoke budget; the
        # shipped reference plugin waits up to 180s for its agent runs.
        timeout=90,
    )
    deltas: list = []
    final_text = ""
    for frame in result.get("frames", []):
        ev = frame.get("event")
        if frame.get("error"):
            raise RuntimeError(f"scanning backend rejected the run: {frame['error']}")
        if ev == "sse":
            for choice in frame.get("choices") or []:
                delta_content = (choice.get("delta") or {}).get("content")
                if isinstance(delta_content, str) and delta_content:
                    deltas.append(delta_content)
        elif ev in ("delta", "token", "message"):
            txt = frame.get("text") or ""
            if txt:
                deltas.append(txt)
        elif ev == "final":
            final_text = (frame.get("text") or "").strip() or "".join(deltas)
    if final_text:
        return final_text
    final = result.get("final")
    if isinstance(final, dict) and final.get("text"):
        return final["text"]
    if deltas:
        return "".join(deltas)
    keys = sorted(result) if isinstance(result, dict) else type(result).__name__
    raise RuntimeError(f"agent/session.run returned no text (reply keys: {keys})")


def close_session(app_session_uuid: str) -> None:
    try:
        _call(
            "agent/session.delete", {"app_session_uuid": app_session_uuid}, timeout=10
        )
    except Exception as exc:  # noqa: BLE001
        # The host expires the session on its own TTL; a failed delete must
        # not turn a successful scan into an error.
        print(f"session.delete failed (non-fatal): {exc}", file=sys.stderr)


# --- Image payload sanitization ----------------------------------------------
# The Anna host rejects session.run's attachments[].data with a 400 if it
# isn't clean base64. Callers (the Anna App UI, a browser file input, etc.) may
# naturally hand us a full `data:image/jpeg;base64,...` URI or base64 wrapped
# with newlines -- neither is clean base64, and the host's rejection surfaces
# as an opaque 400 deep inside the call with no hint about the real cause.
# Strip/validate here so a bad payload fails fast with an actionable message
# instead of that opaque 400.


def _sanitize_base64_image(image_base64: str) -> str:
    s = (image_base64 or "").strip()
    if s.lower().startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            s = s[comma + 1 :]
    return re.sub(r"\s+", "", s)


def _validate_base64_image(image_base64: str) -> str:
    """Returns sanitized base64, or raises ValueError with a caller-facing message."""
    sanitized = _sanitize_base64_image(image_base64)
    if not sanitized:
        raise ValueError("image_base64 is empty after removing any data: URI prefix")
    try:
        base64.b64decode(sanitized, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"image_base64 is not valid base64 image data: {exc}") from exc
    return sanitized


# --- Tool logic --------------------------------------------------------------


def extract_transactions(image_base64: str, image_type: str) -> list:
    image_base64 = _validate_base64_image(image_base64)
    source_hash = hashlib.sha256(image_base64.encode("utf-8")).hexdigest()
    if not re.fullmatch(r"image/[a-z0-9.+-]{1,40}", image_type or ""):
        raise ValueError("image_type must be an image MIME type such as image/jpeg")
    extension = image_type.split("/")[-1].split("+")[0]
    attachment = {
        "type": image_type,
        "data": image_base64,
        "filename": f"bill.{extension}",
    }

    app_session_uuid = create_session()
    try:
        prompt = f"{OCR_PROMPT}\n\nToday's date: {date.today().isoformat()}"
        raw_text = run_session(app_session_uuid, prompt, attachment)
    finally:
        close_session(app_session_uuid)

    parsed = _robust_json_parse(raw_text)
    if parsed.get("error") == "no_image":
        raise RuntimeError(
            "The scanning model reported it could not see the image. Please try again."
        )
    declared = parsed["transaction_count"]
    rows = parsed["transactions"]
    if declared != len(rows):
        print(
            f"model declared {declared} transactions, got {len(rows)} rows",
            file=sys.stderr,
        )

    transactions = []
    for idx, item in enumerate(rows):
        txn = _validate_and_fix_transaction(item, idx, source_hash)
        if txn:
            transactions.append(txn)
    return transactions


# --- JSON-RPC dispatch -------------------------------------------------------


def handle(req: dict) -> dict:
    global v2_negotiated
    method = req.get("method")
    req_id = req.get("id")

    if method == "describe":
        return {"jsonrpc": "2.0", "id": req_id, "result": MANIFEST}

    if method == "initialize":
        proto = (req.get("params") or {}).get("protocolVersion")
        v2_negotiated = proto == "2.0"
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2.0" if v2_negotiated else (proto or "1.1"),
                "serverInfo": {
                    "name": MANIFEST["name"],
                    "version": MANIFEST["version"],
                },
                "capabilities": {"sampling": {}, "agent": {}} if v2_negotiated else {},
            },
        }

    if method == "health":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"status": "ready", "message": "", "details": {}},
        }

    if method == "shutdown":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"ok": True}}

    if method == "invoke":
        params = req.get("params") or {}
        tool = params.get("tool")
        args = params.get("arguments") or {}

        if tool != "extract_transactions":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"unknown tool: {tool}"},
            }

        image_base64 = args.get("image_base64", "")
        image_type = args.get("image_type", "")

        if not image_base64 or not image_type:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "success": False,
                    "error": "image_base64 and image_type are required",
                },
            }

        try:
            transactions = extract_transactions(image_base64, image_type)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"success": True, "data": {"transactions": transactions}},
            }
        except Exception as exc:  # noqa: BLE001
            print(f"extract_transactions failed: {exc}", file=sys.stderr)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"success": False, "error": str(exc)},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"unknown method: {method}"},
    }


def main() -> None:
    threading.Thread(target=_reader, daemon=True).start()
    while True:
        req = agent_requests.get()
        _send(handle(req))


if __name__ == "__main__":
    main()
