#!/usr/bin/env python3
"""wefinance-ocr -- Anna Executa Tool: bill/receipt photo -> structured transactions.

Ports services/vision_ocr_service.py's "count first, then extract" Vision OCR
prompt and its robust JSON parsing / field-fixup logic. Speaks JSON-RPC 2.0
over stdio (Anna Executa protocol v2).

Unlike wefinance-chat/wefinance-recommend, this Tool does NOT use Sampling
(sampling/createMessage only accepts text content -- confirmed with Anna's
team, see annaresearch.md). It uses Anna's Agent Sessions instead
(host_capabilities: ["llm.sample", "llm.agent.auto"]), which support native
image input via an `attachments` array:

    session.run(content=prompt, attachments=[
        {"type": "image/jpeg", "data": "<base64>", "filename": "receipt.jpg"}
    ])

per developers/apps/llm-and-agent.md section 3.0a and developers/tools/executa-agent.md
(both confirmed 2026-08-09 against staging.anna.partners). This lets the Tool
avoid shipping its own OPENAI_API_KEY entirely -- the host routes the vision
call through the user's own plan, same as the other two Tools do for text.

Wire protocol notes (confirmed, not inferred):
- Reverse-RPC methods: agent/session.create, agent/session.run,
  agent/session.delete (NOT .close -- earlier draft guessed wrong).
- session.create uses kind="agent" + agent_submode="auto" (kind="fixed" is
  for pinning to ONE other already-registered executa tool via
  fixed_client_id -- not applicable here, we're not calling another tool).
  Response carries the session id under app_session_uuid (not session_id).
- session.run is buffered streaming in protocol v2: the host returns
  {run_id, stream_id, frames: [...], final} once the run completes, not a
  single text blob like sampling's response. The answer text lives on the
  frame with event == "final" -- and per the shipped reference plugin
  (examples/python/executa-agent-demo), a run can also terminate on a
  sentinel-only event == "complete" frame with no text at all, in which case
  the answer is whatever "delta"/"token"/"message" frames were accumulated
  along the way. Handle both, or a model that streams tokens and terminates
  via "complete" would silently return zero transactions.
- modelPreferences (to force a vision-capable model, avoiding
  APP_MODEL_NOT_VISION_CAPABLE) is a per-RUN param on session.run, not on
  session.create.
- initialize()'s "capabilities" key (not "client_capabilities") is confirmed
  correct -- see wefinance_chat.py's module docstring for the full reasoning;
  same applies here, extended with an empty "agent": {} entry since this tool
  also negotiates Agent Sessions (executa-lifecycle.md: "an empty object is
  fine -- it means I'm aware of this capability, no extra options").
Still unverified without live Dev Access: whether agent_submode="auto"
ever causes the model to attempt a tool call instead of answering directly
(we don't grant this Tool access to any other executa tools, so it should
have nothing to call, but this hasn't been exercised against a real host).
"""

import base64
import binascii
import hashlib
import json
import queue
import re
import sys
import threading
import uuid
from datetime import date, datetime

MANIFEST = {
    "name": "wefinance-ocr",
    "display_name": "WeFinance Bill Scanner",
    "version": "0.1.6",
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
                {
                    "name": "filename",
                    "type": "string",
                    "description": "Original filename, used only as an attachment label. Optional.",
                    "required": False,
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

OCR_PROMPT = """你是一个专业的财务账单识别助手。请仔细分析这张账单图片，提取所有交易记录。

【核心识别规则】：
★ 首先统计图片中有多少笔交易（有几行独立金额就有几笔交易）
★ 然后逐行提取每一笔的详细信息，确保 transactions 数组长度 = transaction_count
★ 如看到合计行，仅用于验证总额，不作为单独交易计数

多语言处理规则：
1. **语言识别**：
   - 如果账单为韩文/日文/泰文等非中英文：
     * 商户名保留原文（不要翻译）
     * 金额(amount)和分类(category)必须提取
     * 如果有英文字段，优先使用英文值
   - 如果账单为中文/英文：正常提取所有字段

2. **字段容错策略**：
   - date缺失 → 尝试从receipt_time推断，或设为null（但标记partial_data=true）
   - merchant缺失 → 从票据抬头/店铺名提取，找不到则设为"Unknown Merchant"
   - category缺失 → 根据商品明细智能推断（食品→餐饮，服装→购物，交通卡→交通）
   - **即使部分字段缺失，也要返回数据，不要直接返回空数组[]**

3. **货币识别增强**：
   - RM 或 MYR → "MYR"（马来西亚林吉特）
   - ฿ 或 THB → "THB"（泰铢）
   - ₩ 或 KRW → "KRW"（韩元）
   - ¥ → "CNY"（人民币）
   - $ → "USD"（美元，但S$为SGD新加坡元）
   - 无符号且无法判断 → 默认"CNY"

4. **提取字段**：
   - date: 日期（YYYY-MM-DD格式）或 null
   - merchant: 商户名称（保持原文）或 "Unknown Merchant"
   - category: 分类（餐饮、交通、购物、娱乐、医疗、教育、其他）
   - amount: 总金额（数字，不带货币符号，必需）
   - currency: 货币代码（见上述规则）
   - partial_data: 布尔值（如果有字段被推断，设为true）
   - inferred_fields: 数组（列出哪些字段是推断的，如 ["date", "merchant"]）

5. **详细收据字段**（可选）：
   - line_items: 商品明细数组
   - subtotal: 小计
   - total_discount: 总折扣金额
   - receipt_number: 收据编号

返回格式（纯JSON对象，不要markdown代码块）：
{
  "transaction_count": 4,
  "transactions": [
    {
      "date": "2025-11-01",
      "merchant": "星巴克",
      "category": "餐饮",
      "amount": 45.0,
      "currency": "CNY",
      "partial_data": false,
      "inferred_fields": []
    }
  ]
}

如果图片中没有交易记录，返回：{"transaction_count": 0, "transactions": []}

重要：即使部分字段缺失，也要尝试返回部分数据，并标记inferred_fields。"""


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
    """Returns {"transaction_count": int, "transactions": [...]}."""

    text = _strip_markdown_fences(content or "")

    direct = _try_json_load(text)
    if direct is not None:
        if isinstance(direct, dict):
            return {
                "transaction_count": direct.get(
                    "transaction_count", len(direct["transactions"])
                ),
                "transactions": _fix_entries(direct["transactions"]),
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

    print(f"JSON parse failed, raw snippet: {text[:200]}", file=sys.stderr)
    return {"transaction_count": 0, "transactions": []}


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


def _validate_and_fix_transaction(item: dict, idx: int, source_hash: str):
    payload = dict(item)
    for typo, correct in TYPO_FIELD_MAP.items():
        if typo in payload and correct not in payload:
            payload[correct] = payload.pop(typo)

    if "amount" not in payload:
        print(f"Transaction {idx} missing amount field, skipping", file=sys.stderr)
        return None

    try:
        payload["amount"] = float(payload["amount"])
    except (TypeError, ValueError):
        print(f"Transaction {idx} has non-numeric amount, skipping", file=sys.stderr)
        return None

    if not payload.get("merchant"):
        payload["merchant"] = "Unknown Merchant"

    payload["date"] = _parse_date(payload.get("date"))
    payload.setdefault("currency", "CNY")
    payload.setdefault("category", "其他")
    payload.setdefault("line_items", [])

    if not payload.get("id"):
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


def create_session(invoke_id: str) -> str:
    if not v2_negotiated:
        raise RuntimeError(
            "Agent Sessions unavailable: host did not negotiate protocol v2 for this session."
        )
    result = _call(
        "agent/session.create",
        {
            "kind": "agent",
            "agent_submode": "auto",
            "label": "wefinance-ocr",
            "metadata": {"executa_invoke_id": invoke_id},
        },
        timeout=25,
    )
    return result["app_session_uuid"]


def run_session(
    invoke_id: str, app_session_uuid: str, content: str, attachments: list
) -> str:
    result = _call(
        "agent/session.run",
        {
            "app_session_uuid": app_session_uuid,
            "content": content,
            "attachments": attachments,
            # vision-capable model required or the run fails fast with
            # APP_MODEL_NOT_VISION_CAPABLE (no silent fallback).
            "modelPreferences": {"hints": [{"name": "gemini"}]},
            "metadata": {"executa_invoke_id": invoke_id},
        },
        # executa-lifecycle.md documents a 60s default invoke budget, but the
        # shipped reference plugin waits up to 180s for its own agent runs --
        # a real, unresolved conflict between the two authoritative-looking
        # sources. Vision extraction is plausibly slower than plain sampling,
        # so we lean toward the reference's number here rather than risk
        # truncating legitimate slow runs; revisit once a real host confirms
        # which one actually governs.
        timeout=90,
    )
    # Buffered streaming (v2): host accumulates SSE frames and returns
    # {run_id, stream_id, frames: [...], final}. The answer is on the
    # terminal frame -- either event=="final" (text, or empty if the
    # producer only emitted deltas) or a sentinel-only event=="complete"
    # with no text at all (shipped reference plugin's documented pattern).
    # Accumulate delta/token/message text along the way as a fallback so
    # neither terminal shape silently returns empty.
    deltas: list = []
    final_text = ""
    for frame in result.get("frames", []):
        ev = frame.get("event")
        if ev == "sse":
            # Real host shape (not documented in executa-lifecycle.md's worked
            # example): each 'sse' frame wraps an OpenAI-style streaming chat
            # completion delta -- content text lives at
            # choices[0].delta.content, alongside control-only deltas like
            # task_info/processing_started/task_complete that carry no text.
            for choice in frame.get("choices") or []:
                content = (choice.get("delta") or {}).get("content")
                if isinstance(content, str) and content:
                    deltas.append(content)
        elif ev in ("delta", "token", "message"):
            txt = frame.get("text") or ""
            if txt:
                deltas.append(txt)
        elif ev == "final":
            final_text = (frame.get("text") or "").strip() or "".join(deltas)
        elif ev == "complete":
            if not final_text:
                final_text = "".join(deltas)
    if final_text:
        return final_text
    final = result.get("final")
    if isinstance(final, dict) and final.get("text"):
        return final["text"]
    if deltas:
        return "".join(deltas)
    raise RuntimeError(f"agent/session.run returned no usable frame: {result!r}")


def close_session(app_session_uuid: str) -> None:
    try:
        _call(
            "agent/session.delete", {"app_session_uuid": app_session_uuid}, timeout=10
        )
    except Exception as exc:  # noqa: BLE001
        print(f"session.delete failed (non-fatal): {exc}", file=sys.stderr)


# --- Image payload sanitization ----------------------------------------------
# The Anna host rejects agent/session.run's attachments[].data with a 400 if it
# isn't clean base64. Callers (the Anna App UI, a browser file input, etc.) may
# naturally hand us a full `data:image/jpeg;base64,...` URI or base64 wrapped
# with newlines -- neither is clean base64, and the host's rejection surfaces
# as an opaque 400 deep inside session.run with no hint about the real cause.
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


def extract_transactions(
    invoke_id: str, image_base64: str, image_type: str, filename: str
) -> list:
    image_base64 = _validate_base64_image(image_base64)
    source_hash = hashlib.sha256(image_base64.encode("utf-8")).hexdigest()

    app_session_uuid = create_session(invoke_id)
    try:
        raw_text = run_session(
            invoke_id,
            app_session_uuid,
            OCR_PROMPT,
            [
                {
                    "type": image_type,
                    "data": image_base64,
                    "filename": filename or "receipt.jpg",
                }
            ],
        )
    finally:
        close_session(app_session_uuid)

    parsed = _robust_json_parse(raw_text)
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
        ctx = params.get("context") or {}
        invoke_id = str(ctx.get("invoke_id") or req_id)

        if tool != "extract_transactions":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"unknown tool: {tool}"},
            }

        image_base64 = args.get("image_base64", "")
        image_type = args.get("image_type", "")
        filename = args.get("filename", "")

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
            transactions = extract_transactions(
                invoke_id, image_base64, image_type, filename
            )
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
