"""Tests for modules/chat_manager.py -- context assembly, caching, heuristic
short-circuit, and the Phase-4 streaming-fallback regression."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from openai import OpenAIError

from modules.chat_manager import ChatManager


@pytest.fixture
def chat_manager(sample_transactions, dummy_env_api_key):
    manager = ChatManager(
        transactions=sample_transactions,
        monthly_budget=1000.0,
        locale="en_US",
    )
    # Disable the LangChain fallback path for these unit tests -- it is
    # covered separately in test_langchain_agent.py, and leaving it enabled
    # here would make heuristic-vs-LLM routing tests depend on a second
    # mocked subsystem.
    import modules.chat_manager as chat_manager_module

    manager._lc_agent = None
    with patch.object(chat_manager_module, "LangChainFinanceAgent", None):
        yield manager


def test_init_loads_locale_specific_system_prompt():
    manager = ChatManager(locale="zh_CN")
    assert "你是WeFinance Copilot" in manager.system_prompt_template

    manager_en = ChatManager(locale="en_US")
    assert "WeFinance Copilot" in manager_en.system_prompt_template


def test_query_transactions_budget_heuristic(chat_manager):
    answer = chat_manager.query_transactions("How much budget do I have left?")
    assert answer is not None
    assert "$" in answer


def test_query_transactions_no_budget_set_returns_setup_prompt(
    sample_transactions, dummy_env_api_key
):
    manager = ChatManager(
        transactions=sample_transactions, monthly_budget=0.0, locale="en_US"
    )
    answer = manager.query_transactions("how much budget do I have remaining?")
    assert answer == manager.i18n.t("chat.heuristic_no_budget")


def test_query_transactions_top_category_heuristic(chat_manager):
    answer = chat_manager.query_transactions("Where am I spending the most?")
    assert answer is not None
    assert "Dining" in answer or "$" in answer


def test_query_transactions_etf_heuristic(chat_manager):
    answer = chat_manager.query_transactions("What is an ETF?")
    assert answer == chat_manager.i18n.t("chat.heuristic_etf")


def test_query_transactions_unmatched_question_returns_none(chat_manager):
    assert chat_manager.query_transactions("Tell me a joke about finance") is None


def test_query_transactions_empty_prompt_returns_none(chat_manager):
    assert chat_manager.query_transactions("   ") is None


def test_generate_response_short_circuits_on_heuristic_match(chat_manager):
    """A heuristic-matched question must never reach the OpenAI client."""
    with patch.object(chat_manager, "_ensure_client") as mock_ensure_client:
        chunks = list(chat_manager.generate_response("What is an ETF?", stream=True))
        mock_ensure_client.assert_not_called()
    assert "".join(chunks) == chat_manager.i18n.t("chat.heuristic_etf")
    assert chat_manager.history[-1]["content"] == "".join(chunks)


def test_get_context_returns_last_n_messages(chat_manager):
    for i in range(15):
        chat_manager.add_message("user", f"message {i}")
    context = chat_manager.get_context(limit=5)
    assert len(context) == 5
    assert context[-1]["content"] == "message 14"


def test_transactions_summary_text_uses_currency_symbol_and_translated_category(
    chat_manager,
):
    summary = chat_manager._transactions_summary_text()
    assert "$" in summary
    assert "Dining" in summary  # 餐饮 -> Dining under en_US


def test_transactions_summary_text_empty_when_no_transactions(dummy_env_api_key):
    manager = ChatManager(transactions=[], locale="en_US")
    assert manager._transactions_summary_text() == manager.i18n.t("common.no_data")


def test_generate_response_streaming_all_retries_exhausted_yields_fallback(
    chat_manager,
):
    """Regression test for the Phase-4 fix: when every retry attempt raises,
    the generator must yield a non-empty fallback message instead of ending
    silently with zero chunks."""
    with (
        patch.object(chat_manager, "_ensure_client") as mock_ensure_client,
        patch("time.sleep"),
    ):
        mock_ensure_client.return_value.chat.completions.create.side_effect = (
            OpenAIError("simulated outage")
        )
        chunks = list(
            chat_manager.generate_response(
                "Tell me something only the LLM can answer", stream=True
            )
        )

    assert chunks, "streaming generator must not end silently with zero chunks"
    full_text = "".join(chunks)
    assert "simulated outage" in full_text
    assert chat_manager.history[-1]["content"] == full_text


def test_generate_response_passes_explicit_timeout_to_openai_call(chat_manager):
    """Regression test for the Phase-4 fix: both streaming and non-streaming
    completion calls must pass an explicit timeout so a hung request fails
    fast instead of blocking indefinitely."""
    with patch.object(chat_manager, "_ensure_client") as mock_ensure_client:
        mock_create = mock_ensure_client.return_value.chat.completions.create

        def _fake_stream(**kwargs):
            assert kwargs.get("timeout") == 15
            return iter([])

        mock_create.side_effect = _fake_stream
        with patch("time.sleep"):
            list(
                chat_manager.generate_response(
                    "only the LLM can answer this", stream=True
                )
            )
        assert mock_create.called
