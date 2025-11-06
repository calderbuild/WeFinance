"""Unit tests for OCRService covering OCR extraction and structuring integration."""

from __future__ import annotations

import io
from typing import List
from unittest.mock import Mock

import pytest
from PIL import Image

from models.entities import OCRParseResult, Transaction
from services.ocr_service import OCRService


def _create_image_bytes() -> io.BytesIO:
    """Generate an in-memory PNG for testing."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="white").save(buffer, format="PNG")
    buffer.name = "receipt.png"
    buffer.seek(0)
    return buffer


class DummyEngine:
    """Minimal PaddleOCR stub returning deterministic text."""

    def ocr(self, _image, cls=True):
        return [
            [
                (None, ("星巴克", 0.98)),
                (None, ("45.00 元", 0.95)),
            ]
        ]


def test_extract_text_success(monkeypatch):
    """Service should stitch PaddleOCR results into newline separated text."""
    service = OCRService()
    service._ocr_engine = DummyEngine()  # type: ignore[attr-defined]

    content = service.extract_text(_create_image_bytes().getvalue())
    assert "星巴克" in content
    assert "45.00 元" in content


def test_process_files_returns_structured_transactions(monkeypatch):
    """Full pipeline should generate OCRParseResult with transactions."""
    mock_structuring = Mock()
    mock_structuring.parse_transactions.return_value = [
        Transaction(
            id="txn-1",
            date="2025-11-01",
            merchant="星巴克",
            category="餐饮",
            amount=45.0,
            currency="CNY",
        )
    ]

    service = OCRService(structuring_service=mock_structuring)
    service._ocr_engine = DummyEngine()  # type: ignore[attr-defined]

    image_file = _create_image_bytes()

    results: List[OCRParseResult] = service.process_files([image_file])

    assert len(results) == 1
    assert results[0].filename == "receipt.png"
    assert len(results[0].transactions) == 1
    mock_structuring.parse_transactions.assert_called_once()


def test_process_files_invalid_image_raises_error():
    """Binary payload that is not an image should raise a friendly error."""
    service = OCRService()
    service._ocr_engine = DummyEngine()  # type: ignore[attr-defined]

    fake_file = io.BytesIO(b"not-an-image")
    fake_file.name = "bad.txt"

    with pytest.raises(RuntimeError):
        service.process_files([fake_file])


def test_structure_transactions_handles_api_failure(monkeypatch):
    """API errors from structuring service should be surfaced as RuntimeError."""
    mock_structuring = Mock()
    mock_structuring.parse_transactions.side_effect = RuntimeError("API failure")

    service = OCRService(structuring_service=mock_structuring)
    with pytest.raises(RuntimeError):
        service.structure_transactions("示例文本")
