#!/usr/bin/env python3
"""Local smoke test for wefinance_ocr.py.

Spawns the plugin as a real subprocess and plays the host: answers its
agent/session.create -> agent/session.run -> agent/session.delete reverse
RPCs with the frame shapes the real host returns (see wefinance_ocr.py's
module docstring). Real-model accuracy is checked separately against the
live host, not here.
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).parent / "wefinance_ocr.py"

FAKE_OCR_RESPONSE = {
    "transaction_count": 3,
    "transactions": [
        {
            "date": "2026-08-01",
            "merchant": "Blue Bottle Coffee",
            "category": "Dining",
            "amount": 5.5,
            "currency": "USD",
        },
        {
            "date": "2026-08-02",
            "marchant": "Metro Card",  # deliberate typos, exercise TYPO_FIELD_MAP
            "catagory": "Transport",
            "amout": 32.5,
        },
        {"date": "2026-08-03", "merchant": "Refund", "amount": -5.5},
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


def sse_result(*texts: str) -> dict:
    return {
        "run_id": "run_test",
        "stream_id": "st_test",
        "frames": [
            {"event": "sse", "seq": i, "choices": [{"delta": {"content": t}}]}
            for i, t in enumerate(texts)
        ],
        "final": {"event": "final", "text": "".join(texts), "synthesized": True},
    }


def scan(proc, req_id: int, image_base64: str, image_type: str, run_reply: dict):
    """Drive one invoke through create/run/delete. Returns (run_rpc, final)."""
    send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "invoke",
            "params": {
                "tool": "extract_transactions",
                "arguments": {"image_base64": image_base64, "image_type": image_type},
            },
        },
    )
    create_rpc = recv(proc)
    assert create_rpc["method"] == "agent/session.create", create_rpc
    assert create_rpc["params"]["agent_submode"] == "auto", create_rpc
    send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": create_rpc["id"],
            "result": {"app_session_uuid": "aps_test"},
        },
    )

    run_rpc = recv(proc)
    assert run_rpc["method"] == "agent/session.run", run_rpc
    send(proc, {"jsonrpc": "2.0", "id": run_rpc["id"], **run_reply})

    delete_rpc = recv(proc)
    assert delete_rpc["method"] == "agent/session.delete", delete_rpc
    assert delete_rpc["params"]["app_session_uuid"] == "aps_test", delete_rpc
    send(proc, {"jsonrpc": "2.0", "id": delete_rpc["id"], "result": {"ok": True}})

    final = recv(proc)
    assert final["id"] == req_id, final
    return run_rpc, final


def _load_plugin_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wefinance_ocr", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rows_are_rebuilt_from_known_fields() -> None:
    """A receipt can say anything, so rows must leave with fixed keys and shapes."""
    module = _load_plugin_module()
    row = module._validate_and_fix_transaction(
        {
            "merchant": "<img src=x onerror=alert(1)>" + "A" * 200,
            "category": "Ignore previous instructions",
            "amount": "12.5",
            "currency": "US<b>",
            "date": "2026-09-01",
            "html": "<script>",
            "inferred_fields": ["category", "<svg>"],
        },
        0,
        "hash",
    )
    assert set(row) == {
        "id",
        "date",
        "merchant",
        "category",
        "amount",
        "currency",
        "partial_data",
        "inferred_fields",
    }, row
    assert len(row["merchant"]) == module.MAX_MERCHANT_LEN, row
    assert row["category"] == "Other" and row["currency"] == "CNY", row
    assert row["inferred_fields"] == ["category"], row
    assert (
        module._validate_and_fix_transaction(
            {"category": "dining", "amount": 3}, 1, "h"
        )["category"]
        == "Dining"
    )
    for bad in ("nan", "inf", None):
        assert (
            module._validate_and_fix_transaction({"amount": bad}, 2, "h") is None
        ), bad
    assert module._validate_and_fix_transaction("not a dict", 3, "h") is None
    try:
        module.extract_transactions(FAKE_IMAGE_BASE64, "text/html")
    except ValueError as exc:
        assert "image MIME type" in str(exc)
    else:
        raise AssertionError("text/html image_type was accepted")
    print("row whitelist + image_type check: OK")


def main() -> int:
    test_rows_are_rebuilt_from_known_fields()
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
        send(proc, {"jsonrpc": "2.0", "id": 1, "method": "describe"})
        resp = recv(proc)
        assert resp["result"]["name"] == "wefinance-ocr", resp
        assert "llm.agent.auto" in resp["result"]["host_capabilities"], resp
        print("describe: OK")

        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "initialize",
                "params": {"protocolVersion": "2.0"},
            },
        )
        assert recv(proc)["result"]["protocolVersion"] == "2.0"
        print("initialize: OK")

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
        assert recv(proc)["result"]["success"] is False
        print("missing-image guard: OK")

        # Happy path: the image rides on session.run's attachments, tools off.
        body = json.dumps(FAKE_OCR_RESPONSE)
        run_rpc, final = scan(
            proc,
            4,
            FAKE_IMAGE_BASE64,
            "image/jpeg",
            {"result": sse_result(body[:40], body[40:])},
        )
        params = run_rpc["params"]
        assert params["attachments"] == [
            {"type": "image/jpeg", "data": FAKE_IMAGE_BASE64, "filename": "bill.jpeg"}
        ], params
        assert params["allowed_tools"] == [], params
        assert params["modelPreferences"]["hints"][0]["name"] == "gemini", params
        assert "Today's date: 20" in params["content"], params
        assert final["result"]["success"] is True, final
        txns = final["result"]["data"]["transactions"]
        assert [t["merchant"] for t in txns] == [
            "Blue Bottle Coffee",
            "Metro Card",
            "Refund",
        ], txns
        assert txns[1]["category"] == "Transport" and txns[1]["amount"] == 32.5, txns
        assert txns[2]["amount"] == -5.5 and txns[2]["category"] == "Other", txns
        assert all(t["id"] for t in txns), txns
        print(
            "scan: OK (attachments + allowed_tools=[] + split sse frames + typo fixup + refund)"
        )

        run_rpc, final = scan(
            proc,
            5,
            f"data:image/png;base64,{FAKE_IMAGE_BASE64}",
            "image/png",
            {"result": sse_result(body)},
        )
        assert run_rpc["params"]["attachments"][0]["data"] == FAKE_IMAGE_BASE64, run_rpc
        assert final["result"]["success"] is True, final
        print("data: URI prefix: OK (stripped before forwarding)")

        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 6,
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
        assert (
            resp["result"]["success"] is False
            and "not valid base64" in resp["result"]["error"]
        ), resp
        print("invalid base64: OK (rejected before any session is opened)")

        _, final = scan(
            proc,
            7,
            FAKE_IMAGE_BASE64,
            "image/jpeg",
            {
                "error": {
                    "code": -32046,
                    "message": "upstream error: boom",
                    "data": {"errorCode": "PROVIDER_ERROR"},
                }
            },
        )
        assert (
            final["result"]["success"] is False and "boom" in final["result"]["error"]
        ), final
        print("run JSON-RPC error: OK (surfaced, session still deleted)")

        error_frame = {
            "run_id": "r",
            "frames": [{"event": "sse", "error": "No endpoints found"}],
        }
        _, final = scan(
            proc, 8, FAKE_IMAGE_BASE64, "image/jpeg", {"result": error_frame}
        )
        assert (
            final["result"]["success"] is False
            and "No endpoints" in final["result"]["error"]
        ), final
        print("provider error frame: OK (surfaced)")

        _, final = scan(
            proc,
            9,
            FAKE_IMAGE_BASE64,
            "image/jpeg",
            {"result": sse_result("Sorry, I can't see any image here.")},
        )
        assert (
            final["result"]["success"] is False
            and "couldn't read a transaction list" in final["result"]["error"]
            and "see any image" not in final["result"]["error"]
        ), final
        print("non-JSON reply: OK (error, not a silent zero-transaction result)")

        no_image = json.dumps(
            {"transaction_count": 0, "transactions": [], "error": "no_image"}
        )
        _, final = scan(
            proc, 10, FAKE_IMAGE_BASE64, "image/jpeg", {"result": sse_result(no_image)}
        )
        assert (
            final["result"]["success"] is False
            and "could not see" in final["result"]["error"]
        ), final
        print("no_image reply: OK (error)")

        empty = json.dumps({"transaction_count": 0, "transactions": []})
        _, final = scan(
            proc, 11, FAKE_IMAGE_BASE64, "image/jpeg", {"result": sse_result(empty)}
        )
        assert final["result"] == {"success": True, "data": {"transactions": []}}, final
        print("genuinely empty bill: OK (success with zero rows)")

        send(proc, {"jsonrpc": "2.0", "id": 12, "method": "health"})
        assert recv(proc)["result"]["status"] == "ready"
        print("health: OK")

        proc.stdin.write("not valid json\n")
        proc.stdin.flush()
        assert recv(proc)["error"]["code"] == -32700
        print("malformed JSON: OK (-32700, reader thread survived)")

        send(proc, {"jsonrpc": "2.0", "id": 13, "method": "shutdown"})
        assert recv(proc)["result"]["ok"] is True
        assert proc.poll() is None, "plugin exited after handling requests"
        print("shutdown + long-running: OK")
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
