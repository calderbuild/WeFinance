"""Tests for services/vision_ocr_service.py -- JSON/markdown-fence parsing,
transaction validation/auto-fix, and a mocked Vision API call."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.vision_ocr_service import (
    VisionOCRService,
    _apply_typo_fix,
    _robust_json_parse,
    _strip_markdown_fences,
    _validate_and_fix_transaction,
)


def test_strip_markdown_fences_removes_json_fence():
    raw = '```json\n[{"amount": 1}]\n```'
    assert _strip_markdown_fences(raw) == '[{"amount": 1}]'


def test_strip_markdown_fences_removes_bare_fence():
    raw = '```\n[{"amount": 1}]\n```'
    assert _strip_markdown_fences(raw) == '[{"amount": 1}]'


def test_strip_markdown_fences_noop_on_plain_json():
    raw = '[{"amount": 1}]'
    assert _strip_markdown_fences(raw) == raw


def test_robust_json_parse_new_format_with_transactions_key():
    content = (
        '{"transaction_count": 1, "transactions": [{"amount": 10, "merchant": "A"}]}'
    )
    result = _robust_json_parse(content)
    assert result == [{"amount": 10, "merchant": "A"}]


def test_robust_json_parse_legacy_array_format():
    content = '[{"amount": 10, "merchant": "A"}, {"amount": 5, "merchant": "B"}]'
    result = _robust_json_parse(content)
    assert len(result) == 2


def test_robust_json_parse_recovers_embedded_array_with_prose():
    content = 'Here is the data: [{"amount": 10, "merchant": "A"}] Hope this helps!'
    result = _robust_json_parse(content)
    assert result == [{"amount": 10, "merchant": "A"}]


def test_robust_json_parse_fixes_common_field_typos():
    content = '[{"amout": 10, "marchant": "A", "catagory": "餐饮"}]'
    result = _robust_json_parse(content)
    assert result[0]["amount"] == 10
    assert result[0]["merchant"] == "A"
    assert result[0]["category"] == "餐饮"


def test_robust_json_parse_unparseable_content_returns_empty_list():
    assert _robust_json_parse("complete garbage, not json at all") == []


def test_robust_json_parse_empty_content_returns_empty_list():
    assert _robust_json_parse("") == []


def test_apply_typo_fix_preserves_correct_field_if_already_present():
    entry = {"amout": 5, "amount": 10}
    fixed = _apply_typo_fix(entry)
    assert fixed["amount"] == 10  # correct field wins, typo is not clobbering it


def test_validate_and_fix_transaction_missing_amount_returns_none():
    result = _validate_and_fix_transaction({"merchant": "A"}, idx=0, source_hash="h")
    assert result is None


def test_validate_and_fix_transaction_missing_category_returns_none():
    """Unlike merchant/date/currency, category has no auto-fix default --
    a transaction missing it fails Transaction's pydantic validation and
    is dropped (logged, not raised)."""
    txn = _validate_and_fix_transaction(
        {"amount": 10, "merchant": "A", "date": "2025-01-01"}, idx=0, source_hash="h"
    )
    assert txn is None


def test_validate_and_fix_transaction_missing_merchant_defaults_to_unknown():
    txn = _validate_and_fix_transaction(
        {"amount": 10, "date": "2025-01-01", "category": "餐饮"}, idx=0, source_hash="h"
    )
    assert txn is not None
    assert txn.merchant == "Unknown Merchant"


def test_validate_and_fix_transaction_missing_date_defaults_to_today():
    from datetime import date as date_cls

    txn = _validate_and_fix_transaction(
        {"amount": 10, "merchant": "A", "category": "餐饮"}, idx=0, source_hash="h"
    )
    assert txn is not None
    assert txn.date == date_cls.today()


def test_validate_and_fix_transaction_invalid_date_falls_back_to_today():
    from datetime import date as date_cls

    txn = _validate_and_fix_transaction(
        {
            "amount": 10,
            "merchant": "A",
            "category": "餐饮",
            "date": "not-a-date-at-all-xyz",
        },
        idx=0,
        source_hash="h",
    )
    assert txn is not None
    assert txn.date == date_cls.today()


def test_validate_and_fix_transaction_missing_currency_defaults_to_cny():
    txn = _validate_and_fix_transaction(
        {"amount": 10, "merchant": "A", "category": "餐饮"}, idx=0, source_hash="h"
    )
    assert txn is not None
    assert txn.currency == "CNY"


def test_validate_and_fix_transaction_generates_deterministic_id():
    txn_a = _validate_and_fix_transaction(
        {"amount": 10, "merchant": "A", "category": "餐饮", "date": "2025-01-01"},
        idx=0,
        source_hash="h",
    )
    txn_b = _validate_and_fix_transaction(
        {"amount": 10, "merchant": "A", "category": "餐饮", "date": "2025-01-01"},
        idx=0,
        source_hash="h",
    )
    assert txn_a is not None and txn_b is not None
    assert txn_a.id == txn_b.id


def test_vision_ocr_service_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        VisionOCRService()


def test_extract_transactions_from_image_parses_mocked_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")

    service = VisionOCRService()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        '{"transaction_count": 1, "transactions": '
        '[{"date": "2025-01-01", "merchant": "Starbucks", "category": "餐饮", '
        '"amount": 36.5, "currency": "CNY"}]}'
    )

    with patch.object(
        service.client.chat.completions, "create", return_value=mock_response
    ):
        transactions = service.extract_transactions_from_image(b"fake-image-bytes")

    assert len(transactions) == 1
    assert transactions[0].merchant == "Starbucks"
    assert transactions[0].amount == 36.5


def test_extract_transactions_from_image_empty_result_on_no_transactions(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")

    service = VisionOCRService()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        '{"transaction_count": 0, "transactions": []}'
    )

    with patch.object(
        service.client.chat.completions, "create", return_value=mock_response
    ):
        transactions = service.extract_transactions_from_image(b"fake-image-bytes")

    assert transactions == []
