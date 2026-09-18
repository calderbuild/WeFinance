#!/usr/bin/env python3
"""Local smoke test for wefinance-ocr's plugin.py.

Same host-simulation approach as the other two Tools' test_local.py: spawn
the plugin as a real subprocess and play the "host" role ourselves. This one
simulates a single agent/complete round trip instead of Sampling, since
sampling/createMessage cannot carry image content.

v0.2.0 switched off the stateful agent/session.create + session.run +
session.delete sequence (kept 404ing in production -- no documented way to
opt this Tool's session out of tool inheritance, see wefinance_ocr.py's
module docstring for the full root-cause writeup) to a single agent/complete
call, which never creates a tool-using session in the first place.

Wire shapes below (method name, buffered {frames: [...]} response) are
confirmed against staging.anna.partners/developers/tools/executa-agent.md
and .../developers/apps/llm-and-agent.md (2026-08-09), not guessed -- see
the docstring in wefinance_ocr.py for what changed and why.
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
        #    carrying the image as an attachment (no session.create/delete)
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
                        "filename": "receipt.jpg",
                    },
                    "context": {"invoke_id": "test-invoke-3"},
                },
            },
        )

        complete_rpc = recv(proc)
        assert complete_rpc["method"] == "agent/complete", complete_rpc
        assert (
            complete_rpc["params"]["modelPreferences"]["hints"][0]["name"] == "gemini"
        ), complete_rpc
        attachments = complete_rpc["params"]["attachments"]
        assert len(attachments) == 1, complete_rpc
        assert attachments[0]["type"] == "image/jpeg", complete_rpc
        assert attachments[0]["data"] == FAKE_IMAGE_BASE64, complete_rpc
        assert attachments[0]["filename"] == "receipt.jpg", complete_rpc
        assert "transaction_count" in complete_rpc["params"]["content"], complete_rpc
        print(
            "agent/complete request: OK (attachment + modelPreferences well-formed, "
            "no session.create/delete)"
        )

        # buffered-streaming response shape: {run_id, stream_id, frames: [...], final}
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": complete_rpc["id"],
                "result": {
                    "run_id": "run-fake-1",
                    "stream_id": "strm-fake-1",
                    "frames": [
                        {"event": "started"},
                        {
                            "event": "final",
                            "text": json.dumps(FAKE_OCR_RESPONSE),
                            "usage": {"totalTokens": 123},
                        },
                    ],
                    "final": True,
                },
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

        # 5. a run terminating via sentinel-only event=="complete" (no text)
        #    must fall back to accumulated delta/token/message text, matching
        #    the shipped reference plugin's documented streaming pattern.
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
                    "context": {"invoke_id": "test-invoke-complete"},
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
                    "run_id": "run-fake-2",
                    "stream_id": "strm-fake-2",
                    "frames": [
                        {"event": "delta", "text": simple_text[:half]},
                        {"event": "delta", "text": simple_text[half:]},
                        {"event": "complete"},
                    ],
                },
            },
        )
        final = recv(proc)
        assert final["id"] == 5, final
        assert final["result"]["success"] is True, final
        txns = final["result"]["data"]["transactions"]
        assert len(txns) == 1 and txns[0]["merchant"] == "Test Shop", final
        print("sentinel 'complete' frame: OK (fell back to accumulated deltas)")

        # 5a. image_base64 arrives as a data: URI (the natural shape a browser
        #     file input / Anna App UI FileReader would hand us) -> must be
        #     stripped to clean base64 before it's forwarded as an attachment,
        #     and the sanitized (not raw) value must be what agent/complete sees.
        #     This is the fix for the Anna App Review's Bill Scanner 400:
        #     "the image payload is not accepted as valid base64 image data."
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
        assert complete_rpc["params"]["attachments"][0]["data"] == FAKE_IMAGE_BASE64, (
            "data: URI prefix must be stripped before forwarding",
            complete_rpc,
        )
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": complete_rpc["id"],
                "result": {
                    "run_id": "run-fake-datauri",
                    "stream_id": "strm-fake-datauri",
                    "frames": [
                        {"event": "final", "text": json.dumps(FAKE_OCR_RESPONSE)}
                    ],
                    "final": True,
                },
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

        # 5c. real production failure shape: a provider/routing error (e.g.
        #     OpenRouter 404 "no endpoints support tool use") rides in on a
        #     normal event=="sse" frame as a top-level `error` string sibling
        #     to `choices`, then a stream_end frame, then a raw "[DONE]" --
        #     none of which carry usable content. Must surface a short,
        #     diagnosable error, not silently fall through to the generic
        #     "no usable frame" fallback with the whole response dumped.
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
                    "context": {"invoke_id": "test-invoke-routing-404"},
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
                    "run_id": "run-fake-404",
                    "stream_id": "strm-fake-404",
                    "frames": [
                        {"event": "started"},
                        {
                            "event": "run_meta",
                            "model": "google/gemini-2.5-flash-image",
                            "provider": "openrouter",
                        },
                        {
                            "event": "sse",
                            "error": (
                                "Error code: 404 - {'error': {'message': "
                                "'No endpoints found that support tool use.'"
                                "}}"
                            ),
                        },
                        {
                            "event": "sse",
                            "event_type": "stream_end",
                            "reason": "task_failed",
                        },
                        {"event": "raw", "text": "[DONE]"},
                    ],
                    "final": None,
                },
            },
        )
        final = recv(proc)
        assert final["id"] == 53, final
        assert final["result"]["success"] is False, final
        err = final["result"]["error"]
        assert "No endpoints found that support tool use" in err, err
        assert len(err) < 300, ("error must stay short, not dump all frames", err)
        print("routing/provider 404 on an sse frame: OK (short, diagnosable error)")

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
