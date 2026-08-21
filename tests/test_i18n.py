"""Tests for utils/i18n.py -- translation lookup, fallback chain, and
the zh_CN/en_US key-parity regression guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils.i18n import I18n

LOCALES_DIR = Path(__file__).parent.parent / "locales"


def _flatten_keys(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _flatten_keys(value, full_key)
        else:
            keys.add(full_key)
    return keys


def test_locale_files_are_valid_json():
    for locale in ("zh_CN", "en_US"):
        data = json.loads((LOCALES_DIR / f"{locale}.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert data, f"{locale}.json should not be empty"


def test_locale_key_parity():
    """zh_CN and en_US must expose the same translation keys.

    The `categories` namespace is a deliberate exception: category names are
    stored (and displayed) in Chinese for zh_CN, so zh_CN.json has no
    top-level `categories` map -- only en_US.json translates them for
    display via I18n.translate_category().
    """
    zh = json.loads((LOCALES_DIR / "zh_CN.json").read_text(encoding="utf-8"))
    en = json.loads((LOCALES_DIR / "en_US.json").read_text(encoding="utf-8"))

    zh_keys = {k for k in _flatten_keys(zh) if not k.startswith("categories.")}
    en_keys = {k for k in _flatten_keys(en) if not k.startswith("categories.")}

    missing_in_en = sorted(zh_keys - en_keys)
    missing_in_zh = sorted(en_keys - zh_keys)

    assert (
        not missing_in_en
    ), f"Keys present in zh_CN but missing in en_US: {missing_in_en}"
    assert (
        not missing_in_zh
    ), f"Keys present in en_US but missing in zh_CN: {missing_in_zh}"


@pytest.mark.parametrize("locale", ["zh_CN", "en_US"])
def test_t_returns_translated_string(locale):
    i18n = I18n(locale)
    assert i18n.t("app.title") == "WeFinance Copilot"


def test_t_interpolates_kwargs():
    i18n = I18n("en_US")
    result = i18n.t("bill_upload.success", count=5)
    assert "5" in result


def test_t_falls_back_to_key_when_missing():
    i18n = I18n("en_US")
    assert i18n.t("app.this_key_does_not_exist") == "app.this_key_does_not_exist"


def test_t_without_kwargs_returns_raw_unformatted_template():
    """Calling t() with zero kwargs skips .format() entirely, so a
    template's placeholders (e.g. `{count}`) are returned verbatim
    instead of raising -- this is how callers avoid a crash when they
    don't have interpolation values on hand."""
    i18n = I18n("en_US")
    assert i18n.t("bill_upload.success") == "Parsed {count} transactions successfully."


def test_t_with_incomplete_kwargs_raises_key_error():
    """Once any kwarg is passed, .format(**kwargs) runs for real -- a
    template requiring a placeholder not present in kwargs raises
    KeyError instead of degrading gracefully. Documents actual (if
    surprising) behavior; callers must always pass every placeholder
    a given key's template needs."""
    i18n = I18n("en_US")
    with pytest.raises(KeyError):
        i18n.t("bill_upload.success", unrelated_kwarg=1)


def test_currency_symbol_by_locale():
    assert I18n("zh_CN").currency_symbol == "¥"
    assert I18n("en_US").currency_symbol == "$"


def test_switch_locale_reloads_translations():
    i18n = I18n("zh_CN")
    assert i18n.t("app.title") == "WeFinance Copilot"
    assert i18n.currency_symbol == "¥"
    i18n.switch_locale("en_US")
    assert i18n.currency_symbol == "$"
    assert i18n.locale == "en_US"


def test_translate_category_known_category():
    i18n = I18n("en_US")
    assert i18n.translate_category("购物") == "Shopping"


def test_translate_category_unknown_category_passes_through():
    i18n = I18n("en_US")
    assert i18n.translate_category("NotACategory") == "NotACategory"


def test_translate_category_zh_cn_passthrough():
    """zh_CN has no categories map; raw Chinese category names pass through unchanged."""
    i18n = I18n("zh_CN")
    assert i18n.translate_category("购物") == "购物"
