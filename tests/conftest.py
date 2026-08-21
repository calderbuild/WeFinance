"""Shared pytest fixtures for the WeFinance test suite."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
import streamlit as st

from models.entities import Transaction
from utils import storage as storage_module


@pytest.fixture(autouse=True)
def _clean_session_state():
    """Reset Streamlit's session_state singleton before every test."""
    st.session_state.clear()
    yield
    st.session_state.clear()


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path, monkeypatch):
    """Redirect file-based storage to a throwaway path so tests never touch
    the real user's ~/.wefinance/data.json."""
    isolated_backend = storage_module.FileStorageBackend(tmp_path / "data.json")
    monkeypatch.setattr(storage_module, "_storage", isolated_backend)
    yield isolated_backend


@pytest.fixture
def sample_transactions() -> list[Transaction]:
    """A small, deterministic set of transactions spanning two categories."""
    today = date.today()
    return [
        Transaction(
            id="t1",
            date=today - timedelta(days=2),
            merchant="Starbucks",
            category="餐饮",
            amount=36.5,
        ),
        Transaction(
            id="t2",
            date=today - timedelta(days=1),
            merchant="Metro",
            category="交通",
            amount=12.0,
        ),
        Transaction(
            id="t3",
            date=today,
            merchant="Starbucks",
            category="餐饮",
            amount=42.0,
        ),
    ]


@pytest.fixture
def dummy_env_api_key(monkeypatch):
    """Provide a fake OPENAI_API_KEY so services init without hitting real APIs."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
