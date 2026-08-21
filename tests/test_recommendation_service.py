"""Tests for services/recommendation_service.py -- pure math helpers,
allocation fallback rules, and LLM-unavailable fallback paths.

All tests avoid real network calls: `_conduct_risk_assessment_llm`,
`generate_personalized_questions`, and `generate_detailed_report` all
short-circuit to their fallback behavior whenever OPENAI_API_KEY is unset,
which is the default test environment (see conftest.py -- no fixture sets a
real key unless a test explicitly requests `dummy_env_api_key`, and even
then the OpenAI client itself is mocked).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from models.entities import Transaction
from services.recommendation_service import RecommendationService


@pytest.fixture
def service(monkeypatch):
    # Ensure no real API key leaks in from the developer's local .env,
    # forcing every LLM-backed method onto its documented fallback path.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return RecommendationService()


def _txn(id_, days_ago, category, amount, base=None):
    base = base or date.today()
    return Transaction(
        id=id_,
        date=base - timedelta(days=days_ago),
        merchant="M",
        category=category,
        amount=amount,
    )


@pytest.mark.parametrize(
    "monthly_avg,expected",
    [
        (0.0, 0.0),
        (-100.0, 0.0),
        (2999.0, round(2999.0 * 0.1, 2)),
        (2999.99, round(2999.99 * 0.1, 2)),
        (3000.0, round(3000.0 * 0.2, 2)),
        (9999.0, round(9999.0 * 0.2, 2)),
        (10000.0, round(10000.0 * 0.3, 2)),
        (50000.0, round(50000.0 * 0.3, 2)),
    ],
)
def test_estimate_investable_tier_boundaries(service, monthly_avg, expected):
    assert service._estimate_investable(monthly_avg) == expected


def test_conduct_risk_assessment_falls_back_to_score_rules_without_api_key(service):
    assert service.conduct_risk_assessment({"q1": 1, "q2": 1}) == "conservative"
    assert service.conduct_risk_assessment({"q1": 3, "q2": 3}) == "balanced"
    assert service.conduct_risk_assessment({"q1": 4, "q2": 4}) == "aggressive"


def test_generate_allocation_uses_fixed_rules_without_llm_recommendation(service):
    allocation = service.generate_allocation("conservative")
    assert allocation == RecommendationService.ALLOCATION_RULES["conservative"]
    assert sum(allocation.values()) == pytest.approx(1.0)


def test_generate_allocation_unknown_profile_falls_back_to_balanced(service):
    allocation = service.generate_allocation("not_a_real_profile")
    assert allocation == RecommendationService.ALLOCATION_RULES["balanced"]


@pytest.mark.parametrize(
    "goal_text,expected_amount,expected_months",
    [
        # _parse_goal's amount regex uses re.search (first match only) and
        # matches any bare digit, even one that is really a horizon -- it
        # does NOT skip ahead to find "20万" here, it stops at the leading
        # "3" (from "3年") with no currency unit attached. Harmless in
        # practice since create_plan() discards this parsed amount/horizon
        # and only keeps the raw goal text, but the test must reflect the
        # regex's actual (not idealized) first-match behavior.
        ("我想在3年内存20万买车", 3.0, 36),
        # The horizon regex only recognizes Chinese unit characters
        # (年/个月/月), so English "months" never matches -- only the
        # bare-digit amount regex (language-agnostic) picks up the "6".
        ("Save for 6 months", 6.0, None),
        ("", None, None),
        ("存5000元", 5000.0, None),
    ],
)
def test_parse_goal_extracts_amount_and_horizon(
    service, goal_text, expected_amount, expected_months
):
    _, amount, months = service._parse_goal(goal_text)
    assert amount == expected_amount
    assert months == expected_months


def test_analyze_transactions_empty_list_returns_zeroed_profile(service):
    metrics = service.analyze_transactions([])
    assert metrics["monthly_average"] == 0.0
    assert metrics["spending_volatility"] == 0.0
    assert metrics["category_breakdown"] == {}
    assert metrics["investable_amount"] == 0.0


def test_analyze_transactions_computes_category_breakdown_shares_sum_to_one(service):
    txns = [
        _txn("t1", 0, "餐饮", 300.0),
        _txn("t2", 1, "交通", 100.0),
    ]
    metrics = service.analyze_transactions(txns)
    breakdown = metrics["category_breakdown"]
    assert breakdown["餐饮"] == pytest.approx(0.75)
    assert breakdown["交通"] == pytest.approx(0.25)
    assert sum(breakdown.values()) == pytest.approx(1.0)


def test_generate_recommendations_without_llm_uses_fixed_allocation(service):
    txns = [_txn("t1", i, "餐饮", 100.0) for i in range(5)]
    recs = service.generate_recommendations(
        txns, risk_profile="balanced", investment_goal="", locale="en_US"
    )
    assert len(recs) >= 1
    assert recs[0].title  # primary recommendation always present
    assert recs[0].risk_level


def test_generate_recommendations_includes_category_tip_when_breakdown_present(service):
    txns = [_txn("t1", i, "餐饮", 100.0) for i in range(5)]
    recs = service.generate_recommendations(
        txns, risk_profile="balanced", locale="en_US"
    )
    assert len(recs) == 2
    assert "餐饮" in recs[1].title or "Dining" in recs[1].title


def test_create_plan_returns_recommendations_metrics_and_risk_name(service):
    txns = [_txn("t1", i, "餐饮", 100.0) for i in range(5)]
    recs, metrics, risk_name = service.create_plan(
        responses={"q1": 1, "q2": 1},
        investment_goal="save for a trip",
        transactions=txns,
        locale="en_US",
    )
    assert isinstance(recs, list) and recs
    assert "monthly_average" in metrics
    assert risk_name  # localized risk label, not the raw key


def test_generate_public_api_shape(service):
    txns = [_txn("t1", i, "餐饮", 100.0) for i in range(5)]
    result = service.generate(
        transactions=txns,
        responses={"q1": 2, "q2": 2},
        investment_goal="",
        locale="en_US",
    )
    assert set(result.keys()) == {
        "recommendations",
        "financial_profile",
        "risk_level",
        "locale",
    }
    assert result["locale"] == "en_US"


def test_generate_personalized_questions_returns_none_without_api_key(service):
    txns = [_txn("t1", i, "餐饮", 100.0) for i in range(3)]
    assert service.generate_personalized_questions(txns, budget=3000.0) is None


def test_generate_detailed_report_returns_empty_string_without_api_key(service):
    txns = [_txn("t1", i, "餐饮", 100.0) for i in range(3)]
    metrics = service.analyze_transactions(txns)
    report = service.generate_detailed_report(
        transactions=txns,
        responses={},
        investment_goal="",
        risk_profile="balanced",
        metrics=metrics,
    )
    assert report == ""


def test_parse_llm_json_handles_markdown_fences(service):
    payload = '```json\n{"a": 1}\n```'
    assert service._parse_llm_json(payload) == {"a": 1}


def test_parse_llm_json_extracts_embedded_object():
    payload = 'Sure! Here you go: {"a": 1, "b": 2} Hope that helps.'
    assert RecommendationService._parse_llm_json(payload) == {"a": 1, "b": 2}


def test_parse_llm_json_raises_on_unparseable_content():
    import json

    with pytest.raises(json.JSONDecodeError):
        RecommendationService._parse_llm_json("not json at all, sorry")
