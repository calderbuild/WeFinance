#!/usr/bin/env python3
"""wefinance-recommend -- Anna Executa Tool: explainable investment recommendations.

Ports the core of WeFinance's services/recommendation_service.py:
_generate_llm_recommendations() + analyze_transactions() metrics. Speaks
JSON-RPC 2.0 over stdio (Anna Executa protocol v2). Uses Anna's Sampling
capability with responseFormat=json_schema (host_capabilities: ["llm.sample"])
instead of shipping our own OpenAI key -- the strict schema replaces the
temperature=0.0 + hand-rolled JSON prompt the original service used.

See wefinance_chat.py's module docstring for the initialize()
"capabilities" vs "client_capabilities" note -- same reasoning applies here.
"""

import json
import queue
import statistics
import sys
import threading
import uuid
from collections import defaultdict

MANIFEST = {
    "name": "wefinance-recommend",
    "display_name": "WeFinance Investment Recommendations",
    "version": "0.1.4",
    "description": "Generate explainable investment recommendations grounded in the user's real spending data.",
    "author": "calderbuild",
    "host_capabilities": ["llm.sample"],
    "runtime": {"type": "uv", "min_version": "0.1.0"},
    "tools": [
        {
            "name": "generate_recommendations",
            "description": "Analyze the user's transactions and return 2-3 personalized, explainable investment recommendations.",
            "parameters": [
                {
                    "name": "transactions",
                    "type": "array",
                    "description": (
                        "List of {date: YYYY-MM-DD, amount: number, category: string, "
                        "currency: string (optional, ISO-4217 code e.g. USD/CNY/EUR -- "
                        "defaults to USD if omitted or if rows disagree on currency)} objects."
                    ),
                    "required": True,
                },
                {
                    "name": "risk_profile",
                    "type": "string",
                    "description": "One of: conservative, balanced, aggressive.",
                    "required": True,
                },
                {
                    "name": "investment_goal",
                    "type": "string",
                    "description": "Free-text investment goal, e.g. 'car down payment in 3 years'. Optional.",
                    "required": False,
                },
                {
                    "name": "monthly_income",
                    "type": "number",
                    "description": (
                        "User's explicitly stated monthly income, if they gave one. When "
                        "provided, the investable amount is computed as monthly_income minus "
                        "average monthly spending instead of a spending-only heuristic. Optional."
                    ),
                    "required": False,
                },
                {
                    "name": "investment_horizon",
                    "type": "string",
                    "description": "Free-text investment horizon, e.g. '5 years'. Optional.",
                    "required": False,
                },
            ],
        }
    ],
}

RISK_LABELS = {
    "conservative": "Conservative (avoids volatility, prioritizes steady, stable returns)",
    "balanced": "Balanced (accepts moderate volatility, balances return and risk)",
    "aggressive": "Aggressive (comfortable with larger swings, targets higher returns)",
}

RECOMMENDATIONS_SCHEMA = {
    "name": "wefinance_recommendations",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "rationale_steps": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "risk_level": {"type": "string"},
                    },
                    "required": ["title", "summary", "rationale_steps", "risk_level"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["recommendations"],
        "additionalProperties": False,
    },
}

SAMPLING_ERROR_MESSAGES = {
    "SAMPLING_NOT_GRANTED": "You haven't enabled sampling for WeFinance Advisor yet -- turn it on in Anna Admin.",
    "SAMPLING_QUOTA_EXCEEDED": "Your account's LLM quota is used up for now.",
    "SAMPLING_PROVIDER_ERROR": "The LLM provider had an error. Try again in a moment.",
    "SAMPLING_INVALID_REQUEST": "Internal error building the request to the LLM (this is a WeFinance bug, not you).",
    "SAMPLING_TIMEOUT": "The recommendation engine took too long to respond. Try again.",
    "SAMPLING_MAX_CALLS_EXCEEDED": "This conversation turn made too many LLM calls.",
    "SAMPLING_MAX_TOKENS_EXCEEDED": "This conversation turn used up its LLM token budget.",
    "SAMPLING_NOT_NEGOTIATED": "Sampling isn't available for this session (protocol not negotiated).",
    "SAMPLING_USER_DENIED": "You declined to allow this LLM call.",
    "SAMPLING_UNSUPPORTED_RESPONSE_FORMAT": "The selected model can't produce structured output, and no fallback was configured.",
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


# --- Metrics (ported from RecommendationService.analyze_transactions,
#     re-implemented without pandas since the plugin runs as a bare subprocess)


def _monthly_average(rows: list) -> float:
    if not rows:
        return 0.0
    by_month: dict = defaultdict(float)
    for r in rows:
        month = r["date"][:7]  # YYYY-MM
        by_month[month] += r["amount"]
    return statistics.mean(by_month.values()) if by_month else 0.0


def _spending_volatility(rows: list) -> float:
    if not rows:
        return 0.0
    by_month: dict = defaultdict(float)
    for r in rows:
        by_month[r["date"][:7]] += r["amount"]
    values = list(by_month.values())
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / mean


def _category_breakdown(rows: list) -> dict:
    if not rows:
        return {}
    totals: dict = defaultdict(float)
    for r in rows:
        totals[r.get("category") or "Other"] += r["amount"]
    total = sum(totals.values())
    if total == 0:
        return {}
    shares = {cat: amt / total for cat, amt in totals.items()}
    return dict(sorted(shares.items(), key=lambda item: item[1], reverse=True))


def _detect_currency(rows: list) -> str:
    """Best-effort currency code for prompt rendering. Falls back to USD when
    rows don't declare a currency or declare more than one -- mixed-currency
    aggregation isn't supported, so we render a defensible default rather
    than silently picking whichever currency happened to come first.
    """
    codes = {
        (r.get("currency") or "").strip().upper()
        for r in rows
        if (r.get("currency") or "").strip()
    }
    if len(codes) == 1:
        return next(iter(codes))
    return "USD"


def _estimate_investable(monthly_avg: float, monthly_income) -> tuple:
    """Returns (investable_amount, basis) where basis is "income_minus_spending"
    when the caller gave us a usable monthly_income, else "spending_heuristic".

    The income-based path is a real, deterministic surplus calculation -- this
    is what the Anna App Review flagged as missing: the tool was previously
    ignoring an explicitly stated income and always falling back to the
    heuristic below, so the outer model ended up doing this subtraction
    itself instead of the dedicated Tool.
    """
    if isinstance(monthly_income, (int, float)) and monthly_income > 0:
        return round(max(monthly_income - monthly_avg, 0.0), 2), "income_minus_spending"
    if monthly_avg <= 0:
        return 0.0, "spending_heuristic"
    # NOTE: these tier thresholds are CNY-scaled magic numbers carried over
    # from the original service and are not currency-aware -- a $2,900/month
    # USD spender gets the same low-tier ratio as a low CNY spender. Only
    # used as a fallback now that a stated income takes the branch above;
    # still not currency-aware, left as-is for now.
    ratio = 0.1 if monthly_avg < 3_000 else 0.2 if monthly_avg < 10_000 else 0.3
    return round(monthly_avg * ratio, 2), "spending_heuristic"


def analyze_transactions(rows: list, monthly_income=None) -> dict:
    monthly_avg = _monthly_average(rows)
    investable_amount, investable_basis = _estimate_investable(
        monthly_avg, monthly_income
    )
    return {
        "monthly_average": monthly_avg,
        "spending_volatility": _spending_volatility(rows),
        "category_breakdown": _category_breakdown(rows),
        "investable_amount": investable_amount,
        "investable_basis": investable_basis,
    }


# --- Reverse-RPC (Sampling) plumbing ----------------------------------------

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


def _request_structured_completion(
    invoke_id: str, prompt: str, max_tokens: int
) -> tuple:
    """Single sampling/createMessage round trip. Returns (parsed_json,
    downgraded_missing_key) -- the second value is True exactly when the host
    downgraded from json_schema AND the parsed body lacks "recommendations".
    """
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
                "temperature": 0.3,
                "includeContext": "none",
                "responseFormat": {
                    "type": "json_schema",
                    "json_schema": RECOMMENDATIONS_SCHEMA,
                },
                "onUnsupported": "json_object",
                "metadata": {"executa_invoke_id": invoke_id},
            },
        }
    )
    resp = q.get(timeout=50)
    if "error" in resp:
        raise RuntimeError(_friendly_sampling_error(resp["error"]))

    result = resp["result"]
    text = result["content"]["text"]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"model did not return valid JSON: {exc}; text={text[:200]!r}"
        ) from exc

    # executa-sampling.md "Reading the result": onUnsupported="json_object"
    # asks the host to silently downgrade instead of erroring when the model
    # can't honour our strict schema. A downgraded response missing
    # "recommendations" would otherwise become success:true + empty list,
    # masking exactly the failure the schema was meant to catch.
    response_format_meta = (result.get("_meta") or {}).get("responseFormat") or {}
    downgraded_missing = bool(
        response_format_meta.get("downgraded") and "recommendations" not in data
    )
    return data, downgraded_missing


# Appended to the prompt on the single repair retry -- kept short and blunt on
# purpose: the model already saw the full prompt once, so the point isn't to
# re-explain the task, it's to strip away any ambiguity about response *shape*
# for a model that couldn't honour strict json_schema mode.
RETRY_REPAIR_SUFFIX = (
    "\n\nIMPORTANT: Respond with ONLY a single JSON object of this exact shape "
    "and nothing else -- no markdown fences, no commentary before or after it:\n"
    '{"recommendations": [{"title": "...", "summary": "...", '
    '"rationale_steps": ["...", "..."], "risk_level": "..."}]}'
)


def sample_structured(invoke_id: str, prompt: str, *, max_tokens: int = 3000) -> dict:
    data, downgraded_missing = _request_structured_completion(
        invoke_id, prompt, max_tokens
    )
    if not downgraded_missing:
        return data

    # Before failing loudly, give the model exactly ONE more chance with a
    # blunter, shape-only instruction appended -- some models that ignore a
    # schema embedded in responseFormat will still follow an explicit inline
    # instruction. No further retries after this: a second failure means the
    # model genuinely can't produce the shape we need, and silently looping
    # would just burn the invoke's sampling-call budget for no benefit. Keep
    # the fail-loud behavior as the final fallback -- do not silently return
    # an empty recommendations list.
    print(
        "sample_structured: downgraded response missing 'recommendations', "
        "retrying once with an explicit shape instruction",
        file=sys.stderr,
    )
    retry_data, retry_downgraded_missing = _request_structured_completion(
        invoke_id, prompt + RETRY_REPAIR_SUFFIX, max_tokens
    )
    if retry_downgraded_missing:
        raise RuntimeError(
            "Model response was downgraded from json_schema and did not contain "
            "'recommendations' (after one retry with an explicit shape "
            f"instruction): {json.dumps(retry_data)[:200]!r}"
        )
    return retry_data


# --- Tool logic --------------------------------------------------------------


def build_prompt(
    metrics: dict,
    risk_profile: str,
    investment_goal: str,
    currency: str = "USD",
    monthly_income=None,
    investment_horizon: str = "",
) -> str:
    monthly_avg = metrics["monthly_average"]
    breakdown = metrics["category_breakdown"]
    breakdown_str = (
        "\n".join(
            f"  - {cat}: {amt * monthly_avg:.2f} {currency} ({amt * 100:.1f}%)"
            for cat, amt in list(breakdown.items())[:5]
        )
        if breakdown and monthly_avg > 0
        else "  (no spending data yet)"
    )
    if metrics.get("investable_basis") == "income_minus_spending":
        investable_line = (
            f"- Investable amount: {metrics['investable_amount']:.2f} {currency}/month "
            f"(stated monthly income of {monthly_income:.2f} {currency} minus average "
            "monthly spending -- this IS the user's verified monthly surplus, present it "
            "as such)"
        )
    else:
        investable_line = (
            f"- Estimated investable amount: {metrics['investable_amount']:.2f} {currency}/month "
            "(a heuristic derived from spending patterns, NOT a verified income-minus-expenses "
            "surplus -- do not present it as the user's actual monthly surplus)"
        )
    income_line = (
        f"- Stated monthly income: {monthly_income:.2f} {currency}\n"
        if isinstance(monthly_income, (int, float)) and monthly_income > 0
        else ""
    )
    return f"""You are a professional financial advisor. Give personalized investment recommendations based on the user's real spending data.

User financial profile:
{income_line}- Average monthly spending: {monthly_avg:.2f} {currency}
- Spending volatility: {metrics["spending_volatility"]:.2%} (higher means less predictable spending)
{investable_line}
- Risk profile: {RISK_LABELS.get(risk_profile, risk_profile)}
- Investment goal: {investment_goal or "not specified"}
- Investment horizon: {investment_horizon or "not specified"}

Spending breakdown (top 5 categories):
{breakdown_str}

Based on this data, generate 2-3 specific, personalized investment recommendations. Each recommendation must include:
1. A title (short and punchy, 8 words or fewer)
2. A summary (one sentence describing the core of this recommendation, about 25 words)
3. Rationale steps (2-4 steps, each explaining WHY this is recommended, showing your reasoning -- e.g. "Because your X is Y, we recommend Z")
4. A risk level (Conservative / Balanced / Aggressive)

Requirements:
- Base every recommendation on the user's real data (income if stated, spending amount, structure, volatility, horizon if stated)
- Rationale steps must show cause and effect, not generic advice
- Avoid generic, one-size-fits-all suggestions -- personalize to this user's numbers
- If the investable amount is small relative to monthly spending, say so honestly and suggest realistic, low-barrier options instead of assuming a large investable surplus"""


def generate_recommendations(
    invoke_id: str,
    transactions: list,
    risk_profile: str,
    investment_goal: str,
    monthly_income=None,
    investment_horizon: str = "",
) -> list:
    metrics = analyze_transactions(transactions, monthly_income)
    currency = _detect_currency(transactions)
    prompt = build_prompt(
        metrics,
        risk_profile,
        investment_goal,
        currency,
        monthly_income,
        investment_horizon,
    )
    data = sample_structured(invoke_id, prompt)
    return data.get("recommendations", [])


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

        if tool != "generate_recommendations":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"unknown tool: {tool}"},
            }

        transactions = args.get("transactions") or []
        risk_profile = args.get("risk_profile", "balanced")
        investment_goal = args.get("investment_goal", "")
        investment_horizon = args.get("investment_horizon", "")

        monthly_income = None
        raw_income = args.get("monthly_income")
        if raw_income is not None:
            try:
                monthly_income = float(raw_income)
            except (TypeError, ValueError):
                print(
                    f"monthly_income {raw_income!r} is not numeric, ignoring",
                    file=sys.stderr,
                )

        if not transactions:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "success": False,
                    "error": "transactions is required and must be non-empty",
                },
            }

        try:
            recs = generate_recommendations(
                invoke_id,
                transactions,
                risk_profile,
                investment_goal,
                monthly_income,
                investment_horizon,
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"success": True, "data": {"recommendations": recs}},
            }
        except Exception as exc:  # noqa: BLE001
            print(f"generate_recommendations failed: {exc}", file=sys.stderr)
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
