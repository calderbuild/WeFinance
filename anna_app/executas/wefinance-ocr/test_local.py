#!/usr/bin/env python3
"""Local smoke test for wefinance-ocr's plugin.py.

Same host-simulation approach as the other two Tools' test_local.py: spawn
the plugin as a real subprocess and play the "host" role ourselves. This one
simulates a single agent/complete round trip instead of Sampling, since
sampling/createMessage's working shape (per wefinance_chat.py) is text-only
in practice.

v0.2.2 request/response shapes are confirmed against
reference-executa-agent-sessions.json's actual `agent/complete` entry
(fetched 2026-09-20), not guessed: `messages: list[dict]` (required,
MCP-shaped `{role, content}`) in, `{content, model, usage}` out (NOT
buffered streaming -- wire.buffered_streaming: false). See wefinance_ocr.py's
module docstring for the full history of what changed and why.
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).parent / "wefinance_ocr.py"

FAKE_OCR_RESPONSE = {
    "transaction_count": 2,
    "transactions": [
        {
            "date": "2026-08-01",
            "merchant": "星巴克",
            "category": "餐饮",
            "amount": 45.0,
            "currency": "CNY",
            "partial_data": False,
            "inferred_fields": [],
        },
        {
            "date": "2026-08-02",
            "marchant": "滴滴出行",  # deliberate typo, exercises TYPO_FIELD_MAP
            "catagory": "交通",
            "amout": 32.5,
        },
    ],
}

FAKE_IMAGE_BASE64 = base64.b64encode(b"not a real image, just test bytes").decode(
    "ascii"
)


def send(proc: subprocess.Popen, obj: dict) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()


def recv(proc: subprocess.Popen) -> dict:
    assert proc.stdout is not None
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("plugin exited unexpectedly (empty stdout read)")
    return json.loads(line)


def fake_complete_result(text: str) -> dict:
    """{content, model, usage} -- agent/complete's real (non-streaming) shape."""
    return {
        "content": [{"type": "text", "text": text}],
        "model": "google/gemini-2.5-flash",
        "usage": {"input_tokens": 500, "output_tokens": 80, "total_tokens": 580},
    }


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, str(PLUGIN)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert (
        proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    )

    try:
        # 1. describe
        send(proc, {"jsonrpc": "2.0", "id": 1, "method": "describe"})
        resp = recv(proc)
        assert resp["result"]["name"] == "wefinance-ocr", resp
        assert resp["result"]["tools"][0]["name"] == "extract_transactions", resp
        assert "llm.agent.auto" in resp["result"]["host_capabilities"], resp
        print("describe: OK")

        # 2. initialize
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "initialize",
                "params": {"protocolVersion": "2.0"},
            },
        )
        resp = recv(proc)
        assert resp["result"]["protocolVersion"] == "2.0", resp
        print("initialize: OK")

        # 3. invoke with missing image -> should fail gracefully
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "invoke",
                "params": {
                    "tool": "extract_transactions",
                    "arguments": {"image_base64": "", "image_type": "image/jpeg"},
                },
            },
        )
        resp = recv(proc)
        assert resp["result"]["success"] is False, resp
        print("missing-image guard: OK")

        # 4. real invoke -> plugin should issue a single agent/complete call
        #    carrying the image as a content block on an MCP-shaped message
        #    (no session.create/delete, no invented content/attachments params)
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "invoke",
                "params": {
                    "tool": "extract_transactions",
                    "arguments": {
                        "image_base64": FAKE_IMAGE_BASE64,
                        "image_type": "image/jpeg",
                    },
                    "context": {"invoke_id": "test-invoke-3"},
                },
            },
        )

        complete_rpc = recv(proc)
        assert complete_rpc["method"] == "agent/complete", complete_rpc
        params = complete_rpc["params"]
        assert params["modelPreferences"]["hints"][0]["name"] == "gemini-2.5-flash", (
            complete_rpc
        )
        messages = params["messages"]
        assert len(messages) == 1 and messages[0]["role"] == "user", complete_rpc
        blocks = messages[0]["content"]
        text_blocks = [b for b in blocks if b["type"] == "text"]
        image_blocks = [b for b in blocks if b["type"] == "image"]
        assert len(image_blocks) == 1, complete_rpc
        assert image_blocks[0]["data"] == FAKE_IMAGE_BASE64, complete_rpc
        assert image_blocks[0]["mimeType"] == "image/jpeg", complete_rpc
        assert text_blocks and "transaction_count" in text_blocks[0]["text"], (
            complete_rpc
        )
        print(
            "agent/complete request: OK (messages/content blocks + modelPreferences "
            "well-formed, no session.create/delete)"
        )

        # {content, model, usage} -- NOT buffered streaming
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": complete_rpc["id"],
                "result": fake_complete_result(json.dumps(FAKE_OCR_RESPONSE)),
            },
        )

        final = recv(proc)
        assert final["id"] == 4, final
        assert final["result"]["success"] is True, final
        txns = final["result"]["data"]["transactions"]
        assert len(txns) == 2, txns
        assert txns[0]["merchant"] == "星巴克", txns
        assert txns[0]["amount"] == 45.0, txns
        # typo-field row: marchant/catagory/amout must have been fixed up,
        # and it must still get a generated id + default currency/category
        assert txns[1]["merchant"] == "滴滴出行", txns
        assert txns[1]["category"] == "交通", txns
        assert txns[1]["amount"] == 32.5, txns
        assert txns[1]["currency"] == "CNY", txns
        assert txns[1]["id"], txns
        print(
            "invoke extract_transactions: OK (typo fixup + defaults + id generation correct)"
        )

        # 5. multiple text blocks in the response must be concatenated, not
        #    just the first one taken (a model could split its answer across
        #    more than one text block).
        simple_response = {
            "transaction_count": 1,
            "transactions": [
                {
                    "date": "2026-08-03",
                    "merchant": "Test Shop",
                    "category": "购物",
                    "amount": 10.0,
                    "currency": "CNY",
                }
            ],
        }
        simple_text = json.dumps(simple_response)
        half = len(simple_text) // 2
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "invoke",
                "params": {
                    "tool": "extract_transactions",
                    "arguments": {
                        "image_base64": FAKE_IMAGE_BASE64,
                        "image_type": "image/jpeg",
                    },
                    "context": {"invoke_id": "test-invoke-split"},
                },
            },
        )
        complete_rpc = recv(proc)
        assert complete_rpc["method"] == "agent/complete", complete_rpc
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": complete_rpc["id"],
                "result": {
                    "content": [
                        {"type": "text", "text": simple_text[:half]},
                        {"type": "text", "text": simple_text[half:]},
                    ],
                    "model": "google/gemini-2.5-flash",
                },
            },
        )
        final = recv(proc)
        assert final["id"] == 5, final
        assert final["result"]["success"] is True, final
        txns = final["result"]["data"]["transactions"]
        assert len(txns) == 1 and txns[0]["merchant"] == "Test Shop", final
        print("split text blocks: OK (concatenated across blocks)")

        # 5a. image_base64 arrives as a data: URI (the natural shape a browser
        #     file input / Anna App UI FileReader would hand us) -> must be
        #     stripped to clean base64 before it's forwarded as an image
        #     content block, and the sanitized (not raw) value must be what
        #     agent/complete sees. This is the fix for the Anna App Review's
        #     Bill Scanner 400: "the image payload is not accepted as valid
        #     base64 image data."
        data_uri = f"data:image/png;base64,{FAKE_IMAGE_BASE64}"
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 51,
                "method": "invoke",
                "params": {
                    "tool": "extract_transactions",
                    "arguments": {
                        "image_base64": data_uri,
                        "image_type": "image/png",
                    },
                    "context": {"invoke_id": "test-invoke-datauri"},
                },
            },
        )
        complete_rpc = recv(proc)
        assert complete_rpc["method"] == "agent/complete", complete_rpc
        image_blocks = [
            b
            for b in complete_rpc["params"]["messages"][0]["content"]
            if b["type"] == "image"
        ]
        assert image_blocks[0]["data"] == FAKE_IMAGE_BASE64, (
            "data: URI prefix must be stripped before forwarding",
            complete_rpc,
        )
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": complete_rpc["id"],
                "result": fake_complete_result(json.dumps(FAKE_OCR_RESPONSE)),
            },
        )
        final = recv(proc)
        assert final["id"] == 51, final
        assert final["result"]["success"] is True, final
        print("data: URI prefix: OK (stripped before forwarding to agent/complete)")

        # 5b. genuinely invalid base64 -> fails fast with a clear message,
        #     never silently forwarded to agent/complete.
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 52,
                "method": "invoke",
                "params": {
                    "tool": "extract_transactions",
                    "arguments": {
                        "image_base64": "not-valid-base64!!! ###",
                        "image_type": "image/png",
                    },
                },
            },
        )
        resp = recv(proc)
        assert resp["result"]["success"] is False, resp
        assert "not valid base64" in resp["result"]["error"], resp
        print(
            "invalid base64: OK (rejected fast with a clear error, no session opened)"
        )

        # 5c. a JSON-RPC error on the agent/complete call itself (the shape
        #     the "'messages' must be a non-empty array" INVALID_REQUEST
        #     production failure actually took) must surface as a short,
        #     diagnosable error via the generic error path, not crash the
        #     plugin or get silently swallowed.
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 53,
                "method": "invoke",
                "params": {
                    "tool": "extract_transactions",
                    "arguments": {
                        "image_base64": FAKE_IMAGE_BASE64,
                        "image_type": "image/jpeg",
                    },
                    "context": {"invoke_id": "test-invoke-invalid-request"},
                },
            },
        )
        complete_rpc = recv(proc)
        assert complete_rpc["method"] == "agent/complete", complete_rpc
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": complete_rpc["id"],
                "error": {
                    "code": -32043,
                    "message": "'messages' must be a non-empty array",
                    "data": {"errorCode": "INVALID_REQUEST"},
                },
            },
        )
        final = recv(proc)
        assert final["id"] == 53, final
        assert final["result"]["success"] is False, final
        assert "non-empty array" in final["result"]["error"], final
        print("agent/complete JSON-RPC error: OK (surfaced, not swallowed)")

        # 5d. a response with no text content at all -> must raise a clear
        #     error instead of silently returning zero transactions.
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 54,
                "method": "invoke",
                "params": {
                    "tool": "extract_transactions",
                    "arguments": {
                        "image_base64": FAKE_IMAGE_BASE64,
                        "image_type": "image/jpeg",
                    },
                    "context": {"invoke_id": "test-invoke-empty"},
                },
            },
        )
        complete_rpc = recv(proc)
        assert complete_rpc["method"] == "agent/complete", complete_rpc
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": complete_rpc["id"],
                "result": {"content": [], "model": "google/gemini-2.5-flash"},
            },
        )
        final = recv(proc)
        assert final["id"] == 54, final
        assert final["result"]["success"] is False, final
        assert "no text content" in final["result"]["error"], final
        print("empty content: OK (raised, not silently zero transactions)")

        # 6. health -- executa-lifecycle.md's documented shape
        send(proc, {"jsonrpc": "2.0", "id": 6, "method": "health"})
        resp = recv(proc)
        assert resp["result"]["status"] == "ready", resp
        print("health: OK")

        # 7. malformed JSON on stdin -> documented -32700 parse error, and
        #    the reader thread must survive it (not silently die).
        assert proc.stdin is not None
        proc.stdin.write("not valid json\n")
        proc.stdin.flush()
        resp = recv(proc)
        assert resp["error"]["code"] == -32700, resp
        print("malformed JSON: OK (-32700, reader thread survived)")

        # 8. shutdown handler
        send(proc, {"jsonrpc": "2.0", "id": 8, "method": "shutdown"})
        resp = recv(proc)
        assert resp["result"]["ok"] is True, resp
        print("shutdown: OK")

        assert proc.poll() is None, "plugin exited after handling requests (pitfall #1)"
        print("long-running check: OK (process still alive)")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        stderr = proc.stderr.read()
        if stderr:
            print("--- plugin stderr ---", file=sys.stderr)
            print(stderr, file=sys.stderr)

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
