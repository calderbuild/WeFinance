"""Tests for utils/session.py -- session state helpers."""

from __future__ import annotations

from datetime import date

import streamlit as st

from utils.session import (
    add_trusted_merchant,
    build_chat_cache_key,
    get_active_anomalies,
    get_anomaly_history,
    get_chat_history,
    get_i18n,
    get_monthly_budget,
    get_trusted_merchants,
    init_session_state,
    record_anomaly_feedback,
    remove_trusted_merchant,
    reset_session_state,
    set_chat_history,
    set_monthly_budget,
    set_transactions,
    switch_locale,
    sync_anomaly_state,
    update_anomaly_state,
)


def test_init_session_state_sets_defaults():
    init_session_state()
    assert st.session_state["locale"] == "en_US"
    assert st.session_state["transactions"] == []
    assert st.session_state["monthly_budget"] == 5000.0


def test_init_session_state_does_not_clobber_existing_values():
    init_session_state()
    st.session_state["monthly_budget"] = 9999.0
    init_session_state()
    assert st.session_state["monthly_budget"] == 9999.0


def test_set_and_get_transactions_roundtrip(sample_transactions):
    set_transactions(sample_transactions)
    stored = st.session_state["transactions"]
    assert len(stored) == 3
    assert all(isinstance(entry, dict) for entry in stored)
    assert stored[0]["merchant"] == "Starbucks"


def test_set_transactions_accepts_dicts():
    entry = {
        "id": "d1",
        "date": date.today().isoformat(),
        "merchant": "Shop",
        "category": "购物",
        "amount": 10.0,
    }
    set_transactions([entry])
    assert st.session_state["transactions"][0]["merchant"] == "Shop"


def test_trusted_merchants_add_dedupe_and_remove():
    add_trusted_merchant("Costco")
    add_trusted_merchant("Costco")  # duplicate should be ignored
    add_trusted_merchant("  Walmart  ")
    merchants = get_trusted_merchants()
    assert merchants.count("Costco") == 1
    assert "Walmart" in merchants

    remove_trusted_merchant("Costco")
    assert "Costco" not in get_trusted_merchants()


def test_get_i18n_returns_cached_instance_matching_locale():
    init_session_state()
    i18n = get_i18n()
    assert i18n.locale == "en_US"
    assert get_i18n() is i18n  # same instance on repeat calls


def test_switch_locale_updates_session_and_i18n_instance():
    init_session_state()
    switch_locale("zh_CN")
    assert st.session_state["locale"] == "zh_CN"
    assert get_i18n().locale == "zh_CN"


def test_monthly_budget_default_and_set():
    assert get_monthly_budget() == 5000.0
    set_monthly_budget(3000.0)
    assert get_monthly_budget() == 3000.0


def test_monthly_budget_rejects_negative_values():
    set_monthly_budget(-500.0)
    assert get_monthly_budget() == 0.0


def test_chat_history_roundtrip():
    set_chat_history([{"role": "user", "content": "hi"}])
    assert get_chat_history() == [{"role": "user", "content": "hi"}]


def test_reset_session_state_clears_all_known_keys():
    init_session_state()
    st.session_state["monthly_budget"] = 1234.0
    reset_session_state()
    assert "monthly_budget" not in st.session_state


def test_reset_session_state_clears_specific_keys_only():
    init_session_state()
    st.session_state["monthly_budget"] = 1234.0
    st.session_state["locale"] = "zh_CN"
    reset_session_state(["monthly_budget"])
    assert "monthly_budget" not in st.session_state
    assert st.session_state["locale"] == "zh_CN"


def test_anomaly_state_update_and_retrieve():
    update_anomaly_state(active=[{"transaction_id": "t1", "amount": 500.0}])
    active = get_active_anomalies()
    assert len(active) == 1
    assert active[0]["transaction_id"] == "t1"


def test_record_anomaly_feedback_moves_item_into_history():
    anomaly = {"transaction_id": "t1", "amount": 500.0}
    record_anomaly_feedback(anomaly, "confirmed")
    history = get_anomaly_history()
    assert len(history) == 1
    assert history[0]["status"] == "confirmed"


def test_sync_anomaly_state_respects_prior_user_feedback():
    # Simulate a user having already confirmed t1 as legitimate.
    record_anomaly_feedback({"transaction_id": "t1", "amount": 500.0}, "confirmed")

    # A fresh anomaly report re-detects t1 (e.g. after recomputation) plus a new t2.
    report = {
        "items": [
            {"transaction_id": "t1", "amount": 500.0},
            {"transaction_id": "t2", "amount": 800.0},
        ],
        "message": None,
    }
    active = sync_anomaly_state(report)
    ids = {item["transaction_id"] for item in active}
    # t1 was already confirmed by the user -- it should not resurface as active.
    assert ids == {"t2"}


def test_build_chat_cache_key_is_stable_for_same_inputs(sample_transactions):
    key_a = build_chat_cache_key("hello", sample_transactions, 5000.0, "en_US")
    key_b = build_chat_cache_key("hello", sample_transactions, 5000.0, "en_US")
    assert key_a == key_b


def test_build_chat_cache_key_differs_by_locale(sample_transactions):
    key_en = build_chat_cache_key("hello", sample_transactions, 5000.0, "en_US")
    key_zh = build_chat_cache_key("hello", sample_transactions, 5000.0, "zh_CN")
    assert key_en != key_zh
