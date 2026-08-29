#!/usr/bin/env python3
"""Local smoke test for wefinance-recommend's plugin.py.

Same approach as wefinance-chat/test_local.py: spawn the plugin as a real
subprocess and play the "host" role ourselves, answering the plugin's
sampling/createMessage reverse RPC with a fake structured completion so the
full describe -> initialize -> invoke -> sampling(json_schema) -> return
round trip is exercised against the real wire protocol.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).parent / "wefinance_recommend.py"


def test_friendly_sampling_error_surfaces_provider_detail() -> None:
    """The host's JSON-RPC error.message must not be discarded -- regression
    check for the bug Anna support flagged: -32003 was rendering as a canned
    "try again" string with no way to tell what actually failed upstream."""
    spec = importlib.util.spec_from_file_location("wefinance_recommend", PLUGIN)
    assert spec is not None and spec.loader is not None, "failed to load plugin module"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    friendly = module._friendly_sampling_error(
        {
            "code": -32003,
            "message": "upstream provider rejected the request: bad json_schema mode",
        }
    )
    assert "bad json_schema mode" in friendly, friendly
    assert "LLM provider had an error" in friendly, (
        friendly
    )  # still human-friendly, not raw dump
    print("friendly_sampling_error surfaces provider detail: OK")


FAKE_RECS = {
    "recommendations": [
        {
            "title": "Build an emergency fund first",
            "summary": "Save 3-6 months of expenses before investing",
            "rationale_steps": [
                "Your monthly spending volatility is relatively high",
                "A cash buffer makes investing safer once it's in place",
            ],
            "risk_level": "Conservative",
        }
    ]
}

SAMPLE_TRANSACTIONS = [
    {"date": "2026-06-05", "amount": 240.0, "category": "Dining", "currency": "USD"},
    {"date": "2026-06-15", "amount": 30.0, "category": "Transport", "currency": "USD"},
    {"date": "2026-07-05", "amount": 300.0, "category": "Dining", "currency": "USD"},
    {"date": "2026-07-20", "amount": 50.0, "category": "Transport", "currency": "USD"},
]


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
    test_friendly_sampling_error_surfaces_provider_detail()

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
        assert resp["result"]["name"] == "wefinance-recommend", resp
        assert resp["result"]["tools"][0]["name"] == "generate_recommendations", resp
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

        # 3. invoke with no transactions -> should fail gracefully, not crash
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "invoke",
                "params": {
                    "tool": "generate_recommendations",
                    "arguments": {"transactions": [], "risk_profile": "balanced"},
                },
            },
        )
        resp = recv(proc)
        assert resp["result"]["success"] is False, resp
        print("empty-transactions guard: OK")

        # 4. real invoke -> plugin computes metrics itself, then emits a
        #    reverse RPC asking for a json_schema-constrained completion
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "invoke",
                "params": {
                    "tool": "generate_recommendations",
                    "arguments": {
                        "transactions": SAMPLE_TRANSACTIONS,
                        "risk_profile": "conservative",
                        "investment_goal": "car down payment in 3 years",
                    },
                    "context": {"invoke_id": "test-invoke-2"},
                },
            },
        )

        reverse_rpc = recv(proc)
        assert reverse_rpc["method"] == "sampling/createMessage", reverse_rpc
        rf = reverse_rpc["params"]["responseFormat"]
        assert rf["type"] == "json_schema", rf
        assert rf["json_schema"]["name"] == "wefinance_recommendations", rf
        # sanity: the prompt should reference the real computed monthly average
        # (540/2 months = 270 dining + 40 transit -> monthly_average ~= 310)
        prompt_text = reverse_rpc["params"]["messages"][0]["content"]["text"]
        assert "Average monthly spending" in prompt_text, prompt_text
        assert "car down payment in 3 years" in prompt_text, prompt_text
        assert "USD" in prompt_text, prompt_text
        print(
            "sampling/createMessage request (json_schema): OK (well-formed, metrics embedded)"
        )

        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": reverse_rpc["id"],
                "result": {
                    "role": "assistant",
                    "content": {"type": "text", "text": json.dumps(FAKE_RECS)},
                },
            },
        )

        final = recv(proc)
        assert final["id"] == 4, final
        assert final["result"]["success"] is True, final
        assert (
            final["result"]["data"]["recommendations"] == FAKE_RECS["recommendations"]
        ), final
        print(
            "invoke generate_recommendations: OK (round trip returned fake recs unchanged)"
        )

        def _downgraded_result(text: str) -> dict:
            return {
                "role": "assistant",
                "content": {"type": "text", "text": text},
                "_meta": {
                    "responseFormat": {
                        "requested": "json_schema",
                        "applied": "json_object",
                        "structuredValid": True,
                        "downgraded": True,
                    }
                },
            }

        # 5. two downgraded responses in a row -> retry once (with an explicit
        #    shape instruction appended to the prompt), then surface as a
        #    clean failure -- never a silent success with an empty list
        #    (executa-sampling.md _meta.responseFormat.downgraded).
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "invoke",
                "params": {
                    "tool": "generate_recommendations",
                    "arguments": {
                        "transactions": SAMPLE_TRANSACTIONS,
                        "risk_profile": "balanced",
                    },
                    "context": {"invoke_id": "test-invoke-downgrade"},
                },
            },
        )
        reverse_rpc_1 = recv(proc)
        assert reverse_rpc_1["method"] == "sampling/createMessage", reverse_rpc_1
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": reverse_rpc_1["id"],
                "result": _downgraded_result("{}"),
            },
        )
        reverse_rpc_2 = recv(proc)  # the retry
        assert reverse_rpc_2["method"] == "sampling/createMessage", reverse_rpc_2
        assert (
            "IMPORTANT" in reverse_rpc_2["params"]["messages"][0]["content"]["text"]
        ), reverse_rpc_2
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": reverse_rpc_2["id"],
                "result": _downgraded_result("{}"),
            },
        )
        final = recv(proc)
        assert final["id"] == 5, final
        assert final["result"]["success"] is False, final
        assert "after one retry" in final["result"]["error"].lower(), final
        print("downgraded-response guard: OK (retried once, then surfaced as failure)")

        # 6. first response downgraded/missing, second response valid -> the
        #    retry must recover into a success, not just fail more gracefully.
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "invoke",
                "params": {
                    "tool": "generate_recommendations",
                    "arguments": {
                        "transactions": SAMPLE_TRANSACTIONS,
                        "risk_profile": "balanced",
                    },
                    "context": {"invoke_id": "test-invoke-downgrade-recovers"},
                },
            },
        )
        reverse_rpc_1 = recv(proc)
        assert reverse_rpc_1["method"] == "sampling/createMessage", reverse_rpc_1
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": reverse_rpc_1["id"],
                "result": _downgraded_result("{}"),
            },
        )
        reverse_rpc_2 = recv(proc)  # the retry
        assert reverse_rpc_2["method"] == "sampling/createMessage", reverse_rpc_2
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": reverse_rpc_2["id"],
                "result": {
                    "role": "assistant",
                    "content": {"type": "text", "text": json.dumps(FAKE_RECS)},
                },
            },
        )
        final = recv(proc)
        assert final["id"] == 6, final
        assert final["result"]["success"] is True, final
        assert (
            final["result"]["data"]["recommendations"] == FAKE_RECS["recommendations"]
        ), final
        print("downgraded-response retry: OK (recovered into a success)")

        # 7. monthly_income supplied -> investable amount must be the
        #    deterministic income-minus-spending surplus, not the spending
        #    heuristic, and the stated income + surplus basis must show up in
        #    the prompt sent to the model (Anna App Review finding: the tool
        #    was previously ignoring an explicitly stated income entirely).
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "invoke",
                "params": {
                    "tool": "generate_recommendations",
                    "arguments": {
                        "transactions": SAMPLE_TRANSACTIONS,
                        "risk_profile": "balanced",
                        "investment_goal": "5-year horizon growth",
                        "monthly_income": 8000,
                        "investment_horizon": "5 years",
                    },
                    "context": {"invoke_id": "test-invoke-income"},
                },
            },
        )
        reverse_rpc = recv(proc)
        assert reverse_rpc["method"] == "sampling/createMessage", reverse_rpc
        prompt_text = reverse_rpc["params"]["messages"][0]["content"]["text"]
        assert "Stated monthly income: 8000.00 USD" in prompt_text, prompt_text
        assert "verified monthly surplus" in prompt_text, prompt_text
        assert "Investment horizon: 5 years" in prompt_text, prompt_text
        # monthly_average across the 2 months of SAMPLE_TRANSACTIONS is 310
        # (270 dining + 40 transit), so surplus should be 8000 - 310 = 7690.00
        assert "7690.00 USD" in prompt_text, prompt_text
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": reverse_rpc["id"],
                "result": {
                    "role": "assistant",
                    "content": {"type": "text", "text": json.dumps(FAKE_RECS)},
                },
            },
        )
        final = recv(proc)
        assert final["id"] == 10, final
        assert final["result"]["success"] is True, final
        print(
            "monthly_income supplied: OK (deterministic surplus in prompt, not heuristic)"
        )

        # 8. health -- executa-lifecycle.md's documented shape
        send(proc, {"jsonrpc": "2.0", "id": 7, "method": "health"})
        resp = recv(proc)
        assert resp["result"]["status"] == "ready", resp
        print("health: OK")

        # 9. malformed JSON on stdin -> documented -32700 parse error, and
        #    the reader thread must survive it (not silently die).
        assert proc.stdin is not None
        proc.stdin.write("not valid json\n")
        proc.stdin.flush()
        resp = recv(proc)
        assert resp["error"]["code"] == -32700, resp
        print("malformed JSON: OK (-32700, reader thread survived)")

        # 10. shutdown handler
        send(proc, {"jsonrpc": "2.0", "id": 9, "method": "shutdown"})
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
