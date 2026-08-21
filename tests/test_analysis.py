"""Tests for modules/analysis.py -- category/trend calculations, anomaly
detection, and the Phase-3 en_US-locale leak regression."""

from __future__ import annotations

import re
from datetime import date, timedelta

import pytest

from models.entities import Transaction
from modules.analysis import (
    calculate_category_totals,
    calculate_merchant_totals,
    calculate_spending_trend,
    compute_anomaly_report,
    detect_anomalies,
    generate_insights,
)

CJK_PATTERN = re.compile(r"[一-鿿]")


def _txn(id_, days_ago, merchant, category, amount, base=None):
    base = base or date.today()
    return Transaction(
        id=id_,
        date=base - timedelta(days=days_ago),
        merchant=merchant,
        category=category,
        amount=amount,
    )


def test_calculate_category_totals(sample_transactions):
    totals = calculate_category_totals(sample_transactions)
    assert totals["餐饮"] == pytest.approx(78.5)
    assert totals["交通"] == pytest.approx(12.0)


def test_calculate_merchant_totals(sample_transactions):
    totals = calculate_merchant_totals(sample_transactions)
    assert totals["Starbucks"] == pytest.approx(78.5)
    assert totals["Metro"] == pytest.approx(12.0)


def test_calculate_spending_trend_monthly_has_period_and_amount_columns(
    sample_transactions,
):
    trend = calculate_spending_trend(sample_transactions, frequency="M")
    assert list(trend.columns) == ["period", "amount"]
    assert trend["amount"].sum() == pytest.approx(90.5)


def test_calculate_spending_trend_empty_input_returns_empty_frame():
    trend = calculate_spending_trend([], frequency="D")
    assert trend.empty


def test_compute_anomaly_report_insufficient_data_returns_message_key():
    report = compute_anomaly_report([_txn("t1", 0, "A", "餐饮", 50.0)])
    assert report["sample_size"] == 1
    assert report["message"] == "spending.message_insufficient_data"
    assert report["items"] == []


def test_compute_anomaly_report_detects_outlier():
    base_txns = [_txn(f"t{i}", i, "A", "餐饮", 50.0 + i) for i in range(12)]
    outlier = _txn("outlier", 0, "B", "购物", 5000.0)
    report = compute_anomaly_report(base_txns + [outlier])
    ids = {item["transaction_id"] for item in report["items"]}
    assert "outlier" in ids


def test_compute_anomaly_report_respects_merchant_whitelist():
    base_txns = [_txn(f"t{i}", i, "A", "餐饮", 50.0 + i) for i in range(12)]
    outlier = _txn("outlier", 0, "TrustedShop", "购物", 5000.0)
    report = compute_anomaly_report(
        base_txns + [outlier], whitelist_merchants=["TrustedShop"]
    )
    ids = {item["transaction_id"] for item in report["items"]}
    assert "outlier" not in ids


def test_anomaly_reason_localized_by_locale():
    base_txns = [_txn(f"t{i}", i, "A", "餐饮", 50.0 + i) for i in range(12)]
    outlier = _txn("outlier", 0, "B", "购物", 5000.0)
    txns = base_txns + [outlier]

    report_zh = compute_anomaly_report(txns, locale="zh_CN")
    report_en = compute_anomaly_report(txns, locale="en_US")

    reason_zh = next(
        i["reason"] for i in report_zh["items"] if i["transaction_id"] == "outlier"
    )
    reason_en = next(
        i["reason"] for i in report_en["items"] if i["transaction_id"] == "outlier"
    )

    assert CJK_PATTERN.search(reason_zh)
    assert not CJK_PATTERN.search(reason_en)
    assert "σ" in reason_en


def test_detect_anomalies_backward_compatible_wrapper():
    base_txns = [_txn(f"t{i}", i, "A", "餐饮", 50.0 + i) for i in range(12)]
    outlier = _txn("outlier", 0, "B", "购物", 5000.0)
    items = detect_anomalies(base_txns + [outlier])
    assert isinstance(items, list)
    assert any(item["transaction_id"] == "outlier" for item in items)


def test_generate_insights_empty_transactions_returns_empty_list():
    assert generate_insights([]) == []


def test_generate_insights_en_us_has_no_hardcoded_chinese_or_yuan_symbol():
    """Regression guard for the Phase-3 fix: the LLM-failure fallback path
    must not leak Chinese text or a bare ¥ symbol when locale=en_US."""
    txns = []
    today = date.today()
    for i in range(20):
        txns.append(
            _txn(
                f"t{i}",
                i,
                f"Merchant{i % 3}",
                "餐饮" if i % 2 == 0 else "交通",
                50.0 + i,
                base=today,
            )
        )

    insights = generate_insights(txns, locale="en_US")
    assert insights, "expected at least one insight for 20 transactions"
    for insight in insights:
        assert not CJK_PATTERN.search(insight.title), insight.title
        assert not CJK_PATTERN.search(insight.detail), insight.detail
        assert "¥" not in insight.detail
        for action in insight.actions:
            assert not CJK_PATTERN.search(action), action
            assert "¥" not in action


def test_generate_insights_zh_cn_still_uses_yuan_symbol():
    txns = []
    today = date.today()
    for i in range(20):
        txns.append(
            _txn(
                f"t{i}",
                i,
                f"Merchant{i % 3}",
                "餐饮" if i % 2 == 0 else "交通",
                50.0 + i,
                base=today,
            )
        )

    insights = generate_insights(txns, locale="zh_CN")
    assert insights
    joined = " ".join(ins.detail for ins in insights)
    assert "¥" in joined


def test_generate_insights_translates_category_name_for_display():
    """A concentrated category ("购物") should render as "Shopping" in the
    en_US concentration insight, not leak the raw Chinese category label."""
    txns = [_txn(f"t{i}", i, "BigShop", "购物", 100.0) for i in range(5)]
    insights = generate_insights(txns, locale="en_US")
    concentration = next(i for i in insights if "spending category" in i.detail.lower())
    assert "Shopping" in concentration.detail
    assert "购物" not in concentration.detail
