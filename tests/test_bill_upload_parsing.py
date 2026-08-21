"""Tests for pages/bill_upload.py parsing helpers -- Excel column mapping,
manual JSON/CSV import, and Phase-3 localized error messages.

Includes a regression test for the manual-CSV-import crash bug found and
fixed during this pass: `_parse_manual_input`'s CSV branch referenced an
undefined `idx` whenever a row lacked an explicit `id` column.
"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from pages.bill_upload import _parse_excel_file, _parse_manual_input
from utils.i18n import I18n


def _excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


def test_parse_excel_file_maps_known_column_aliases():
    df = pd.DataFrame(
        {
            "posting_date": ["2025-01-01"],
            "name_customer": ["Starbucks"],
            "total_amount": [36.5],
        }
    )
    transactions = _parse_excel_file(_excel_bytes(df))
    assert len(transactions) == 1
    assert transactions[0].merchant == "Starbucks"
    assert transactions[0].amount == 36.5


def test_parse_excel_file_missing_date_column_raises_localized_error():
    df = pd.DataFrame({"merchant": ["A"], "amount": [10.0]})
    with pytest.raises(ValueError) as exc_info:
        _parse_excel_file(_excel_bytes(df), i18n=I18n("en_US"))
    assert "date" in str(exc_info.value).lower()


def test_parse_excel_file_missing_merchant_column_raises_localized_error():
    df = pd.DataFrame({"date": ["2025-01-01"], "amount": [10.0]})
    with pytest.raises(ValueError) as exc_info:
        _parse_excel_file(_excel_bytes(df), i18n=I18n("en_US"))
    assert "merchant" in str(exc_info.value).lower()


def test_parse_excel_file_missing_amount_column_raises_localized_error():
    df = pd.DataFrame({"date": ["2025-01-01"], "merchant": ["A"]})
    with pytest.raises(ValueError) as exc_info:
        _parse_excel_file(_excel_bytes(df), i18n=I18n("en_US"))
    assert "amount" in str(exc_info.value).lower()


def test_parse_excel_file_error_message_is_english_under_en_us_locale():
    df = pd.DataFrame({"merchant": ["A"], "amount": [10.0]})
    with pytest.raises(ValueError) as exc_info:
        _parse_excel_file(_excel_bytes(df), i18n=I18n("en_US"))
    message = str(exc_info.value)
    assert "缺少" not in message


def test_parse_excel_file_error_message_is_chinese_under_zh_cn_locale():
    df = pd.DataFrame({"merchant": ["A"], "amount": [10.0]})
    with pytest.raises(ValueError) as exc_info:
        _parse_excel_file(_excel_bytes(df), i18n=I18n("zh_CN"))
    assert "缺少" in str(exc_info.value)


def test_parse_excel_file_skips_rows_with_missing_merchant_or_zero_amount():
    df = pd.DataFrame(
        {
            "date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "merchant": ["Valid Co", "", "Also Valid"],
            "amount": [10.0, 20.0, 0.0],
        }
    )
    transactions = _parse_excel_file(_excel_bytes(df))
    # Row 2 has no merchant, row 3 has a zero amount -- both should be skipped.
    assert len(transactions) == 1
    assert transactions[0].merchant == "Valid Co"


def test_parse_excel_file_no_valid_rows_raises_localized_error():
    df = pd.DataFrame({"date": ["2025-01-01"], "merchant": [""], "amount": [10.0]})
    with pytest.raises(ValueError):
        _parse_excel_file(_excel_bytes(df), i18n=I18n("en_US"))


def test_parse_manual_input_json_list():
    raw = '[{"id": "1", "date": "2025-01-01", "merchant": "A", "category": "餐饮", "amount": 36.5}]'
    transactions = _parse_manual_input(raw)
    assert len(transactions) == 1
    assert transactions[0].merchant == "A"


def test_parse_manual_input_json_generates_id_when_missing():
    raw = (
        '[{"date": "2025-01-01", "merchant": "A", "category": "餐饮", "amount": 36.5}]'
    )
    transactions = _parse_manual_input(raw)
    assert transactions[0].id  # non-empty, auto-generated


def test_parse_manual_input_json_non_list_root_raises():
    with pytest.raises(ValueError):
        _parse_manual_input('{"not": "a list"}')


def test_parse_manual_input_csv_basic():
    raw = "id,date,merchant,category,amount\n1,2025-01-01,A,餐饮,36.5\n"
    transactions = _parse_manual_input(raw)
    assert len(transactions) == 1
    assert transactions[0].merchant == "A"


def test_parse_manual_input_csv_without_id_column_does_not_crash():
    """Regression test: this used to raise NameError('idx' not defined)
    whenever a pasted CSV row lacked an explicit `id` column -- the most
    common case for hand-typed manual entry."""
    raw = "date,merchant,category,amount\n2025-01-01,Starbucks,餐饮,36.5\n2025-01-02,Metro,交通,12.0\n"
    transactions = _parse_manual_input(raw)
    assert len(transactions) == 2
    assert transactions[0].id and transactions[1].id
    assert transactions[0].id != transactions[1].id


def test_parse_manual_input_empty_string_returns_empty_list():
    assert _parse_manual_input("   ") == []
