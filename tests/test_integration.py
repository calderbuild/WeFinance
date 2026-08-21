"""End-to-end happy-path tests spanning module boundaries.

Scoped down per the plan: 1-2 true integration tests, not a sprawling
suite. Every LLM boundary is mocked or forced onto its documented
fallback path -- no real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from modules.analysis import compute_anomaly_report, generate_insights
from services.recommendation_service import RecommendationService
from services.vision_ocr_service import VisionOCRService
from utils.i18n import I18n
from utils.session import get_transactions, init_session_state, set_transactions


def test_ocr_upload_to_insights_end_to_end(monkeypatch):
    """Bill image -> mocked Vision API -> session state -> spending
    insights + anomaly detection, exercised in both locales.

    Uses 10 small dining transactions plus one large outlier: with a
    3-point sample the outlier's own mass inflates the population std
    enough that its z-score never crosses the (adaptively raised)
    threshold -- 11 points keeps sample_size >= 10 so the base 2.5
    threshold applies and the outlier reliably clears it.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")

    small_txns = [
        {
            "date": f"2025-01-{day:02d}",
            "merchant": "Starbucks",
            "category": "餐饮",
            "amount": 30.0,
            "currency": "CNY",
        }
        for day in range(1, 11)
    ]
    outlier_txn = {
        "date": "2025-01-11",
        "merchant": "Metro",
        "category": "交通",
        "amount": 5000.0,
        "currency": "CNY",
    }
    payload = {
        "transaction_count": 11,
        "transactions": small_txns + [outlier_txn],
    }

    ocr_service = VisionOCRService()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(payload)
    with patch.object(
        ocr_service.client.chat.completions, "create", return_value=mock_response
    ):
        extracted = ocr_service.extract_transactions_from_image(b"fake-image-bytes")
    assert len(extracted) == 11

    init_session_state()
    set_transactions(extracted)
    stored = get_transactions()
    assert len(stored) == 11
    assert {t.merchant for t in stored} == {"Starbucks", "Metro"}

    en_insights = generate_insights(stored, locale="en_US")
    assert en_insights
    assert all("¥" not in insight.detail for insight in en_insights)

    zh_insights = generate_insights(stored, locale="zh_CN")
    assert zh_insights
    assert any("¥" in insight.detail for insight in zh_insights)

    anomaly_report = compute_anomaly_report(stored, base_threshold=2.5, locale="en_US")
    assert anomaly_report["items"], "the 5000.0 outlier should be flagged"
    assert anomaly_report["items"][0]["merchant"] == "Metro"
    assert "σ" in anomaly_report["items"][0]["reason"]


def test_recommendation_pipeline_end_to_end_without_llm(
    monkeypatch, sample_transactions
):
    """Transactions -> risk assessment -> allocation -> recommendations,
    fully through RecommendationService.generate()'s fallback path
    (no OPENAI_API_KEY configured), exercised in both locales."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = RecommendationService()

    result_en = service.generate(
        transactions=sample_transactions,
        responses={"q1": 4, "q2": 4},
        investment_goal="save for a trip",
        locale="en_US",
    )
    assert result_en["risk_level"] == I18n("en_US").t(
        "recommendation.risk_name.aggressive"
    )
    assert result_en["recommendations"]
    assert result_en["financial_profile"]["monthly_average"] > 0

    result_zh = service.generate(
        transactions=sample_transactions,
        responses={"q1": 1, "q2": 1},
        investment_goal="",
        locale="zh_CN",
    )
    assert result_zh["risk_level"] == I18n("zh_CN").t(
        "recommendation.risk_name.conservative"
    )
    assert result_zh["recommendations"]
