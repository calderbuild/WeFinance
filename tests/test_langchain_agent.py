"""Tests for services/langchain_agent.py -- tool functions exercised
directly (no LLM call needed) and the Phase-3 locale-aware currency symbol."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from models.entities import Transaction

# services.langchain_agent imports the legacy LangChain agent API, which only
# exists on langchain <1.0. requirements.txt pins that range, but if a resolver
# ever drags in an incompatible version we want a visible skip here rather than
# a collection error that takes the whole suite down with it.
LangChainFinanceAgent = pytest.importorskip(
    "services.langchain_agent",
    reason="LangChain agent API unavailable (incompatible langchain version)",
).LangChainFinanceAgent


def _txn(id_, days_ago, category, amount):
    return Transaction(
        id=id_,
        date=date.today() - timedelta(days=days_ago),
        merchant="M",
        category=category,
        amount=amount,
    )


@pytest.fixture
def agent_factory():
    """Build a LangChainFinanceAgent without hitting the real LangChain
    agent-initialization machinery -- only the plain tool methods are
    under test here, not the ChatOpenAI-backed executor."""

    def _build(locale="en_US", monthly_budget=1000.0, transactions=None):
        agent = LangChainFinanceAgent.__new__(LangChainFinanceAgent)
        agent.transactions = LangChainFinanceAgent._normalize_transactions(
            transactions or []
        )
        agent.monthly_budget = monthly_budget
        agent.currency_symbol = "¥" if locale == "zh_CN" else "$"
        return agent

    return _build


def test_currency_symbol_defaults_to_dollar_for_en_us(agent_factory):
    agent = agent_factory(locale="en_US")
    assert agent.currency_symbol == "$"


def test_currency_symbol_yuan_for_zh_cn(agent_factory):
    agent = agent_factory(locale="zh_CN")
    assert agent.currency_symbol == "¥"


def test_tool_query_budget_no_budget_set(agent_factory):
    agent = agent_factory(monthly_budget=0.0)
    result = agent._tool_query_budget("")
    assert "haven't set" in result.lower()


def test_tool_query_budget_uses_locale_currency_symbol(agent_factory):
    txns = [_txn("t1", 0, "餐饮", 100.0)]
    agent = agent_factory(locale="en_US", monthly_budget=1000.0, transactions=txns)
    result = agent._tool_query_budget("")
    assert "$" in result
    assert "¥" not in result


def test_tool_query_budget_zh_cn_uses_yuan_symbol(agent_factory):
    txns = [_txn("t1", 0, "餐饮", 100.0)]
    agent = agent_factory(locale="zh_CN", monthly_budget=1000.0, transactions=txns)
    result = agent._tool_query_budget("")
    assert "¥" in result


def test_tool_query_spending_no_data(agent_factory):
    agent = agent_factory(transactions=[])
    result = agent._tool_query_spending("")
    assert "no spending data" in result.lower()


def test_tool_query_spending_lists_top_categories_with_currency_symbol(agent_factory):
    txns = [_txn("t1", 0, "餐饮", 300.0), _txn("t2", 1, "交通", 100.0)]
    agent = agent_factory(locale="en_US", transactions=txns)
    result = agent._tool_query_spending("")
    assert "$300.00" in result
    assert "$100.00" in result


def test_tool_query_category_empty_input(agent_factory):
    agent = agent_factory()
    result = agent._tool_query_category("   ")
    assert "provide a category" in result.lower()


def test_tool_query_category_not_found(agent_factory):
    agent = agent_factory(transactions=[_txn("t1", 0, "餐饮", 100.0)])
    result = agent._tool_query_category("购物")
    assert "no spending records" in result.lower()


def test_tool_query_category_found_uses_currency_symbol(agent_factory):
    agent = agent_factory(locale="en_US", transactions=[_txn("t1", 0, "餐饮", 100.0)])
    result = agent._tool_query_category("餐饮")
    assert "$100.00" in result


def test_normalize_transactions_accepts_mixed_dict_and_model_input():
    txn_model = _txn("t1", 0, "餐饮", 100.0)
    txn_dict = {
        "id": "t2",
        "date": date.today().isoformat(),
        "merchant": "M",
        "category": "交通",
        "amount": 50.0,
    }
    normalized = LangChainFinanceAgent._normalize_transactions([txn_model, txn_dict])
    assert len(normalized) == 2
    assert all(isinstance(t, Transaction) for t in normalized)


def test_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        LangChainFinanceAgent([], api_key=None, base_url=None)
