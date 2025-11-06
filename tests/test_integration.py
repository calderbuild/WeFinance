"""High level integration scenarios covering core user journeys."""

from __future__ import annotations

import datetime as dt
from typing import Dict, List

import pytest

from models.entities import Transaction
from modules.analysis import (
    calculate_category_totals,
    detect_anomalies,
    generate_insights,
)
from modules.chat_manager import ChatManager
from services.recommendation_service import RecommendationService


@pytest.fixture(autouse=True)
def _ensure_env(monkeypatch):
    """Mock API keys to avoid accidental real calls."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://mock.endpoint/v1")


@pytest.fixture(autouse=True)
def _disable_langchain(monkeypatch):
    """Prevent LangChain agent instantiation during integration tests."""
    monkeypatch.setattr("modules.chat_manager.LangChainFinanceAgent", None)


@pytest.fixture
def sample_transactions() -> List[Transaction]:
    """Provide a baseline set of transactions for integration flows."""
    return [
        Transaction(
            id="txn-001",
            date=dt.date(2025, 10, 28),
            merchant="星巴克",
            category="餐饮",
            amount=45.0,
        ),
        Transaction(
            id="txn-002",
            date=dt.date(2025, 10, 30),
            merchant="地铁出行",
            category="交通",
            amount=6.0,
        ),
        Transaction(
            id="txn-003",
            date=dt.date(2025, 11, 1),
            merchant="美团外卖",
            category="餐饮",
            amount=58.0,
        ),
        Transaction(
            id="txn-004",
            date=dt.date(2025, 11, 2),
            merchant="京东",
            category="购物",
            amount=120.0,
        ),
        Transaction(
            id="txn-005",
            date=dt.date(2025, 11, 3),
            merchant="盒马鲜生",
            category="餐饮",
            amount=65.5,
        ),
        Transaction(
            id="txn-006",
            date=dt.date(2025, 11, 4),
            merchant="喜茶",
            category="餐饮",
            amount=28.0,
        ),
        Transaction(
            id="txn-007",
            date=dt.date(2025, 11, 4),
            merchant="滴滴出行",
            category="交通",
            amount=12.0,
        ),
        Transaction(
            id="txn-008",
            date=dt.date(2025, 11, 5),
            merchant="711便利店",
            category="日常",
            amount=35.0,
        ),
        Transaction(
            id="txn-009",
            date=dt.date(2025, 11, 5),
            merchant="商超采购",
            category="购物",
            amount=85.0,
        ),
        Transaction(
            id="txn-010",
            date=dt.date(2025, 11, 6),
            merchant="盒马鲜生",
            category="餐饮",
            amount=52.0,
        ),
    ]


def test_flow_upload_analysis_chat_recommendation(sample_transactions):
    """场景1：上传账单→分析→对话问答→推荐生成。"""
    totals = calculate_category_totals(sample_transactions)
    top_category = max(totals, key=totals.get)
    assert top_category == "餐饮"

    insights = generate_insights(sample_transactions)
    assert any("消费集中度提示" in insight.title for insight in insights)

    chat_manager = ChatManager(
        transactions=sample_transactions,
        monthly_budget=1000.0,
    )
    question = "我最近在哪方面花钱最多？"
    chat_manager.add_message("user", question)
    reply = chat_manager.generate_response(question)
    assert "餐饮" in reply

    rec_service = RecommendationService()
    risk_answers = {"q1": 1, "q2": 2, "q3": 2}
    recommendation_payload = rec_service.generate(
        transactions=sample_transactions,
        responses=risk_answers,
        investment_goal="我想在3年内存20万买车",
    )
    assert recommendation_payload["risk_level"] in {"保守型", "稳健型", "激进型"}
    assert "组合" in recommendation_payload["recommendation"].summary


def test_flow_batch_upload_anomaly_confirmation(sample_transactions):
    """场景2：批量上传→异常检测→用户确认。"""
    # 添加一笔明显异常的超大额消费
    outlier = Transaction(
        id="txn-100",
        date=dt.date(2025, 11, 4),
        merchant="未知商户",
        category="其他",
        amount=5200.0,
    )
    extended = sample_transactions + [outlier]
    anomalies = detect_anomalies(extended, threshold=2.0)
    assert anomalies, "应检测到异常支出"

    session_state: Dict[str, list] = {
        "active_anomalies": anomalies.copy(),
        "anomaly_history": [],
    }

    flagged = session_state["active_anomalies"].pop(0)
    flagged["status"] = "confirmed"
    session_state["anomaly_history"].append(flagged)

    assert len(session_state["active_anomalies"]) == len(anomalies) - 1
    assert session_state["anomaly_history"][0]["status"] == "confirmed"


def test_flow_multi_turn_chat_and_reset(sample_transactions):
    """场景3：多轮对话→清空历史→重新问答。"""
    manager = ChatManager(
        transactions=sample_transactions,
        monthly_budget=2000.0,
    )

    prompt_budget = "我这个月还能花多少？"
    manager.add_message("user", prompt_budget)
    _ = manager.generate_response(prompt_budget)

    prompt_etf = "ETF是什么？"
    manager.add_message("user", prompt_etf)
    _ = manager.generate_response(prompt_etf)
    assert len(manager.history) >= 4  # 至少包含两轮对话的用户与助手回复

    manager.history.clear()
    assert manager.history == []

    follow_up = "我最近在哪方面花钱最多？"
    manager.add_message("user", follow_up)
    reply = manager.generate_response(follow_up)
    assert "餐饮" in reply
    assert len(manager.history) == 2  # user + assistant


def test_flow_recommendation_and_xai(sample_transactions):
    """场景4：风险问卷→推荐生成→查看XAI解释。"""
    service = RecommendationService()
    payload = service.generate(
        transactions=sample_transactions,
        responses={"q1": 2, "q2": 2, "q3": 3},
        investment_goal="我想在5年内存30万教育金",
    )

    explanation: str = payload["explanation"]  # type: ignore[assignment]
    assert "为什么推荐这个组合" in explanation
    assert "- 预期年化收益" in explanation
    assert payload["metrics"]["expected_return"] > 0


def test_flow_anomaly_feedback_history(sample_transactions):
    """场景5：异常触发→用户标记欺诈→查看历史记录。"""
    outlier = Transaction(
        id="txn-200",
        date=dt.date(2025, 11, 5),
        merchant="可疑海外商户",
        category="其他",
        amount=8800.0,
    )
    anomalies = detect_anomalies(sample_transactions + [outlier], threshold=2.0)
    assert anomalies

    history: List[Dict[str, object]] = []
    suspect = anomalies[0]
    suspect["status"] = "fraud"
    history.append(suspect)

    assert history[0]["status"] == "fraud"
    assert history[0]["merchant"] == "可疑海外商户"
