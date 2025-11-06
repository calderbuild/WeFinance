"""Internationalization support for WeFinance Copilot."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


class I18n:
    """Simple i18n manager for bilingual support."""

    def __init__(self, locale: str = "zh_CN") -> None:
        self.locale = locale
        self.translations = self._load_translations(locale)

    @staticmethod
    @lru_cache(maxsize=8)
    def _read_locale_file(locale: str) -> Dict[str, Any]:
        """Read translation JSON for the locale (cached)."""
        locale_file = Path(__file__).parent.parent / "locales" / f"{locale}.json"
        if locale_file.exists():
            with locale_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        return {}

    def _load_translations(self, locale: str) -> Dict[str, Any]:
        """Load translation file for given locale."""
        return self._read_locale_file(locale)

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate key with optional formatting."""
        segments = key.split(".")
        value: Any = self.translations
        for segment in segments:
            if isinstance(value, dict) and segment in value:
                value = value[segment]
            else:
                value = key
                break

        if isinstance(value, str):
            return value.format(**kwargs) if kwargs else value
        return str(value)

    def switch_locale(self, locale: str) -> None:
        """Switch to different locale."""
        self.locale = locale
        self.translations = self._load_translations(locale)
