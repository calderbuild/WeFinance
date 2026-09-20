#!/usr/bin/env python3
"""wefinance-ocr -- Anna Executa Tool: bill/receipt photo -> structured transactions.

Ports services/vision_ocr_service.py's "count first, then extract" Vision OCR
prompt and its robust JSON parsing / field-fixup logic. Speaks JSON-RPC 2.0
over stdio (Anna Executa protocol v2).

Unlike wefinance-chat/wefinance-recommend, this Tool does NOT use plain
Sampling (sampling/createMessage's working shape, per wefinance_chat.py, is
text-only in practice). It uses Anna's Agent Sessions family instead
(host_capabilities: ["llm.sample", "llm.agent.auto"]) via agent/complete,
which supports native image input through MCP-shaped `messages`:

    agent/complete(messages=[
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image", "data": "<base64>", "mimeType": "image/jpeg"},
        ]},
    ])

This lets the Tool avoid shipping its own OPENAI_API_KEY entirely -- the
host routes the vision call through the user's own plan, same as the other
two Tools do for text.

History: v0.1.x used a stateful agent/session.create + session.run + delete
sequence (kind="agent", agent_submode="auto"). That's how Anna's own
reference plugin does it, but it kept 404ing in production with "No
endpoints found that support tool use": OpenRouter routes any session with
granted tools to tool-use-capable endpoints, and the vision model we get
hinted to (gemini-2.5-flash-image) has none. v0.1.9 tried to opt out via
quotaCaps.inherit_host_tools: false on session.create -- shipped, verified
through the CLI dev-harness, and still failed identically on three
consecutive real Chrome-UI retests (run_meta kept reporting
inherit_host_tools: True / granted_tools: ["*"] regardless of what the
create call asked for).

Root cause (confirmed by reading reference-executa-agent-sessions.json
directly, not guessed): quotaCaps/inherit_host_tools/allowed_tools/
granted_tools are ONLY documented under the Host API's agent.session.create
(the App's own iframe JS, postMessage transport) -- NOT under this Tool's
reverse-RPC agent/session.create, whose reference entry says nothing about
tool-grant control beyond "Identity is derived from the sampling_token --
the plugin cannot override it." The Host API docs even say allowed_tools
only narrows "sandbox sessions only" -- if the grant behind a session was
never sandboxed, no per-call param changes that. There is no documented way
for a stdio Tool to opt out of tool inheritance via session.create.

v0.2.0 switches to agent/complete: "L1 one-shot completion... sugar for
plugins that don't need state" (same host_capabilities grant, same auth
chain as agent/session.*, "same wire frames" per the reference docs). Bill
Scanner only ever needs one completion per invoke, so this avoids creating
a stateful, tool-using Agent Session in the first place -- sidestepping the
tool-inheritance question by construction instead of by an unsupported
parameter. This was unverified until tested against the real Chrome UI: the
CLI dev-harness's --agent-account path was later found to mint tokens via a
separate dev-only endpoint (POST /api/v1/anna-apps/dev/session/mint), so a
CLI pass alone doesn't prove anything about this class of bug -- see
test_local.py and the App Review thread for the real-UI verification.

v0.2.0's real bug (confirmed by Anna's team, 2026-09-20 forum reply): the
Developer Console's Install/reinstall only registers the app on the
account -- it never pushes bundled executa binaries to the agent. So every
v0.1.x/v0.2.0 build sat published and "current" per `executa status` and
local `describe` while the agent kept running the original v0.1.8 binary
all week. That's why three independent fixes "changed nothing" -- none of
them ever actually ran. Deploying a new build now requires an explicit push
via /executa (Executa Hub) -> My Tools -> Install on the target agent, on
top of the publish/cut/submit-review pipeline.

v0.2.1 also fixes a second bug agent/complete inherited from v0.1.x: the
modelPreferences hint "gemini" was resolving to google/gemini-2.5-flash-image,
which is an image-*generation* model, not a vision-input one. Hinting a real
vision-capable text model (gemini-2.5-flash) instead.

v0.2.1's remaining bug, found once the real v0.2.1 binary was finally
running on the agent (see above): agent/complete's actual params are
`content`/`attachments` -- an invented shape, guessed by analogy to
session.create, that never matched any documented field. It surfaced as a
live "'messages' must be a non-empty array" INVALID_REQUEST (-32043), since
the host silently ignored the unrecognized params and defaulted the real
required field to empty. Fixed by reading
reference-executa-agent-sessions.json's actual `agent/complete` param list
directly: `messages: list[dict]` (required, MCP-shaped `{role, content}`,
"multimodal content blocks accepted verbatim"), plus optional maxTokens/
modelPreferences/systemPrompt/temperature/stopSequences/metadata. No
`content`/`attachments` params exist at all.

Wire protocol notes (confirmed via reference-executa-agent-sessions.json,
not inferred):
- Reverse-RPC method: agent/complete. NOT buffered streaming (wire.
  buffered_streaming: false) -- returned verbatim from
  /copilot/app/complete as {content, model, usage}. `content` is a list of
  blocks (typically [{type: "text", text: ...}]), the same content-block
  family as sampling/createMessage's response but as a list instead of a
  single object (wefinance_chat.py's `result["content"]["text"]` does NOT
  apply here).
- modelPreferences (to force a vision-capable model, avoiding
  APP_MODEL_NOT_VISION_CAPABLE) is a param on the call itself.
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
import queue
import re
import sys
import threading
import uuid
from datetime import date, datetime

MANIFEST = {
    "name": "wefinance-ocr",
    "display_name": "WeFinance Bill Scanner",
    "version": "0.2.2",
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


def complete(invoke_id: str, prompt: str, image_base64: str, image_type: str) -> str:
    if not v2_negotiated:
        raise RuntimeError(
            "Agent Sessions unavailable: host did not negotiate protocol v2 for this session."
        )
    result = _call(
        "agent/complete",
        {
            # Real schema (confirmed 2026-09-20 against
            # reference-executa-agent-sessions.json's session_create "messages"
            # param, after `content`/`attachments` -- an invented shape that
            # never matched any documented field -- caused a live
            # "'messages' must be a non-empty array" INVALID_REQUEST). MCP-shaped
            # messages, mirroring wefinance_chat.py's working
            # sampling/createMessage call: {role, content}, content a single
            # block or (per "multimodal content blocks are accepted verbatim")
            # a list of blocks for one message.
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "data": image_base64,
                            "mimeType": image_type,
                        },
                    ],
                }
            ],
            "maxTokens": 4000,
            # vision-capable TEXT model required. A bare "gemini" hint
            # resolved to google/gemini-2.5-flash-image (an image-generation
            # model with almost no tool-use-compatible routing options,
            # confirmed by Anna's team 2026-09-20) -- name the text model
            # explicitly instead of a generic family hint.
            "modelPreferences": {"hints": [{"name": "gemini-2.5-flash"}]},
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
    # Not buffered streaming -- confirmed via reference doc's
    # wire.buffered_streaming: false. Returned verbatim from
    # /copilot/app/complete as {content, model, usage}, content a list of
    # blocks (typically [{type: 'text', text: ...}]), matching
    # sampling/createMessage's shape family but as a list instead of a single
    # object.
    blocks = result.get("content") or []
    if isinstance(blocks, dict):
        blocks = [blocks]
    texts = [
        b.get("text", "")
        for b in blocks
        if isinstance(b, dict) and b.get("type") == "text"
    ]
    text = "".join(texts).strip()
    if text:
        return text
    raise RuntimeError(f"agent/complete returned no text content: {result!r}")


# --- Image payload sanitization ----------------------------------------------
# The Anna host rejects agent/complete's attachments[].data with a 400 if it
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


def extract_transactions(invoke_id: str, image_base64: str, image_type: str) -> list:
    image_base64 = _validate_base64_image(image_base64)
    source_hash = hashlib.sha256(image_base64.encode("utf-8")).hexdigest()

    raw_text = complete(invoke_id, OCR_PROMPT, image_base64, image_type)

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
            transactions = extract_transactions(invoke_id, image_base64, image_type)
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
