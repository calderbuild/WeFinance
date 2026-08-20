#!/usr/bin/env python3
"""wefinance-chat -- Anna Executa Tool: WeFinance conversational financial advisor.

Speaks JSON-RPC 2.0 over stdio (Anna Executa protocol v2). Uses Anna's Sampling
capability (host_capabilities: ["llm.sample"]) instead of shipping our own
OpenAI key -- the host routes the LLM call through the user's own plan.

Protocol details below are confirmed against staging.anna.partners
(developers/tools/executa-intro.md, executa-lifecycle.md, executa-sampling.md,
executa-pitfalls.md), cross-checked against the shipped reference plugin at
github.com/whtcjdtc2007/anna-executa-examples/.../executa-agent-demo, 2026-08-09.
One conflict worth flagging: that reference plugin's initialize() response uses
a "client_capabilities" key, but BOTH executa-lifecycle.md's own worked example
(the authoritative page both executa-sampling.md and executa-agent.md point to
for the v2 handshake) AND executa-sampling.md's own runnable "Minimal Python
example" use plain "capabilities" -- the same shape this file already used
before this pass. Two independent doc-level sources beat one demo script, so
this file keeps "capabilities" rather than switching to "client_capabilities".
"""

import json
import queue
import sys
import threading
import uuid

MANIFEST = {
    "name": "wefinance-chat",
    "display_name": "WeFinance Advisor Chat",
    "version": "0.1.5",
    "description": "Ask financial questions about your spending and get advice grounded in your actual transactions.",
    "author": "calderbuild",
    "host_capabilities": ["llm.sample"],
    "runtime": {"type": "uv", "min_version": "0.1.0"},
    "tools": [
        {
            "name": "ask_advisor",
            "description": "Answer a financial question using the user's recent transaction summary as context.",
            "parameters": [
                {
                    "name": "question",
                    "type": "string",
                    "description": "The user's financial question.",
                    "required": True,
                },
                {
                    "name": "transactions_summary",
                    "type": "string",
                    "description": "Pre-formatted text summary of recent transactions (date, merchant, category, amount).",
                    "required": True,
                },
            ],
        }
    ],
}

SYSTEM_PROMPT = (
    "You are WeFinance's financial advisor. Ground your answer in the transaction "
    "data provided as context -- be specific and reference actual merchants, "
    "categories, or amounts from that data, and never invent transactions or "
    "spending figures that aren't in it. In addition to the transaction data, the "
    "user's question may state financial details directly -- income, salary, "
    "savings, budget limits, goals, or timelines. Treat anything the user states "
    "about themselves in their own question as true and factor it into your "
    "answer (for example, weigh a stated monthly income against the spending "
    "shown in the transaction data). Keep answers concise (3-5 sentences). If "
    "neither the transaction data nor the question gives you enough to answer, "
    "say so honestly instead of guessing."
)

# executa-sampling.md "Error codes" table -- error.data.errorCode carries the
# symbolic name; fall back to the numeric code if data is missing.
SAMPLING_ERROR_MESSAGES = {
    "SAMPLING_NOT_GRANTED": "You haven't enabled sampling for WeFinance Advisor yet -- turn it on in Anna Admin.",
    "SAMPLING_QUOTA_EXCEEDED": "Your account's LLM quota is used up for now.",
    "SAMPLING_PROVIDER_ERROR": "The LLM provider had an error. Try again in a moment.",
    "SAMPLING_INVALID_REQUEST": "Internal error building the request to the LLM (this is a WeFinance bug, not you).",
    "SAMPLING_TIMEOUT": "The advisor took too long to respond. Try a shorter question.",
    "SAMPLING_MAX_CALLS_EXCEEDED": "This conversation turn made too many LLM calls.",
    "SAMPLING_MAX_TOKENS_EXCEEDED": "This conversation turn used up its LLM token budget.",
    "SAMPLING_NOT_NEGOTIATED": "Sampling isn't available for this session (protocol not negotiated).",
    "SAMPLING_USER_DENIED": "You declined to allow this LLM call.",
    "SAMPLING_UNSUPPORTED_RESPONSE_FORMAT": "The selected model can't produce the response format this tool needs.",
}


SAMPLING_ERROR_CODES_BY_NUMBER = {
    -32001: "SAMPLING_NOT_GRANTED",
    -32002: "SAMPLING_QUOTA_EXCEEDED",
    -32003: "SAMPLING_PROVIDER_ERROR",
    -32004: "SAMPLING_INVALID_REQUEST",
    -32005: "SAMPLING_TIMEOUT",
    -32006: "SAMPLING_MAX_CALLS_EXCEEDED",
    -32007: "SAMPLING_MAX_TOKENS_EXCEEDED",
    -32008: "SAMPLING_NOT_NEGOTIATED",
    -32009: "SAMPLING_USER_DENIED",
    -32010: "SAMPLING_UNSUPPORTED_RESPONSE_FORMAT",
}


def _friendly_sampling_error(error: dict) -> str:
    data = error.get("data") if isinstance(error, dict) else None
    code_name: str = ""
    if isinstance(data, dict) and isinstance(data.get("errorCode"), str):
        code_name = data["errorCode"]
    if not code_name:
        code_num = error.get("code") if isinstance(error, dict) else None
        code_name = (
            SAMPLING_ERROR_CODES_BY_NUMBER.get(code_num, "")
            if isinstance(code_num, int)
            else ""
        )
    return SAMPLING_ERROR_MESSAGES.get(code_name, str(error))


# --- Reverse-RPC (Sampling) plumbing ----------------------------------------
# Two channels share stdin: Agent-initiated requests (have "method") and host
# responses to our own reverse RPCs (have only "id" + "result"/"error").

agent_requests: queue.Queue = queue.Queue()
host_responses: dict = {}
# Set once initialize() sees the host's proposed protocolVersion. Reverse-RPC
# (sampling) only works when the host negotiated v2 (executa-lifecycle.md
# "Fallback to v1"); attempting it against a v1 host would just hang until
# our own timeout, so we fail fast with a clear message instead.
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
            # Never let a single malformed line kill this daemon thread --
            # that starves agent_requests.get() forever with no symptom
            # other than the plugin looking "Stopped" (executa-pitfalls.md #1).
            print(f"reader routing error (continuing): {exc}", file=sys.stderr)


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def sample(invoke_id: str, prompt: str, *, max_tokens: int = 2000) -> str:
    if not v2_negotiated:
        raise RuntimeError(
            "Sampling unavailable: host did not negotiate protocol v2 for this session."
        )
    rid = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()
    host_responses[rid] = q
    _send(
        {
            "jsonrpc": "2.0",
            "id": rid,
            "method": "sampling/createMessage",
            "params": {
                "messages": [
                    {"role": "user", "content": {"type": "text", "text": prompt}}
                ],
                "maxTokens": max_tokens,
                "systemPrompt": SYSTEM_PROMPT,
                "includeContext": "none",
                "metadata": {"executa_invoke_id": invoke_id},
            },
        }
    )
    # executa-lifecycle.md: invoke's default host-side budget is 60s
    # (per-tool overridable). Stay comfortably under it so a slow model
    # surfaces as a clean tool error instead of a silent host-side abandon.
    resp = q.get(timeout=50)
    if "error" in resp:
        raise RuntimeError(_friendly_sampling_error(resp["error"]))
    result = resp["result"]
    text = result["content"]["text"]
    if not text:
        # executa-sampling.md's documented result shape carries stopReason /
        # usage / _meta.provider alongside content.text -- surface them
        # instead of silently returning "" so an empty completion shows up
        # as a diagnosable tool error, not a blank answer the UI shrugs off.
        raise RuntimeError(
            "Model returned an empty completion "
            f"(stopReason={result.get('stopReason')!r}, "
            f"usage={result.get('usage')!r}, "
            f"provider={(result.get('_meta') or {}).get('provider')!r})"
        )
    return text


# --- Tool logic --------------------------------------------------------------


def ask_advisor(invoke_id: str, question: str, transactions_summary: str) -> str:
    prompt = f"Transaction data:\n{transactions_summary}\n\nQuestion: {question}"
    return sample(invoke_id, prompt)


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
                "capabilities": {"sampling": {}} if v2_negotiated else {},
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

        if tool != "ask_advisor":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"unknown tool: {tool}"},
            }

        question = args.get("question", "")
        transactions_summary = args.get("transactions_summary", "")
        if not question or not transactions_summary:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "success": False,
                    "error": "question and transactions_summary are required",
                },
            }

        try:
            advice = ask_advisor(invoke_id, question, transactions_summary)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"success": True, "data": {"advice": advice}},
            }
        except Exception as exc:  # noqa: BLE001
            print(f"ask_advisor failed: {exc}", file=sys.stderr)
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
