"""Services responsible for OCR extraction and structuring."""

from __future__ import annotations

import io
import logging
from typing import BinaryIO, Iterable, List, Optional

import numpy as np
from PIL import Image

from models.entities import OCRParseResult, Transaction
from services.structuring_service import StructuringService

logger = logging.getLogger(__name__)


class OCRService:
    """Facade wrapping PaddleOCR and GPT-4o structuring pipeline."""

    def __init__(
        self,
        use_angle_class: bool = True,
        lang: str = "ch",
        structuring_service: Optional[StructuringService] = None,
    ) -> None:
        self.use_angle_class = use_angle_class
        self.lang = lang
        self._ocr_engine = None
        self.structuring_service = structuring_service

    def _lazy_engine(self):
        """Instantiate PaddleOCR lazily to keep app startup fast."""
        if self._ocr_engine is not None:
            return self._ocr_engine

        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:  # pragma: no cover - runtime guard
            raise RuntimeError(
                "PaddleOCR 未安装。请先运行 `pip install paddleocr`。"
            ) from exc

        self._ocr_engine = PaddleOCR(
            use_angle_cls=self.use_angle_class,
            lang=self.lang,
            show_log=False,
        )
        return self._ocr_engine

    def extract_text(self, image_bytes: bytes) -> str:
        """Run PaddleOCR on uploaded image data."""
        engine = self._lazy_engine()

        try:
            image = Image.open(io.BytesIO(image_bytes))
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("无法读取图像数据：%s", exc)
            raise RuntimeError("账单文件解析失败，请确认文件格式是否正确。") from exc

        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        np_img = np.array(image)
        logger.debug("执行PaddleOCR识别，图像尺寸：%s", np_img.shape)
        try:
            result = engine.ocr(np_img, cls=self.use_angle_class)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("PaddleOCR识别失败：%s", exc)
            raise RuntimeError("图片识别失败，请确认账单是否清晰。") from exc

        lines: List[str] = []
        for page in result:
            for line in page:
                text = line[1][0]
                lines.append(text.strip())

        return "\n".join(line for line in lines if line)

    def structure_transactions(self, ocr_text: str) -> List[Transaction]:
        """Use GPT-4o (or rule-based fallback) to convert text into transactions."""
        if not ocr_text.strip():
            logger.warning("Empty OCR text received, returning no transactions.")
            return []

        if self.structuring_service is None:
            self.structuring_service = StructuringService()
        try:
            return self.structuring_service.parse_transactions(ocr_text)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("结构化解析失败：%s", exc)
            raise RuntimeError("结构化解析失败，请稍后重试。") from exc

    def process_files(self, files: Iterable[BinaryIO]) -> List[OCRParseResult]:
        """Entry point that accepts uploaded files and returns normalized transactions."""
        outcomes: List[OCRParseResult] = []
        for file_obj in files:
            filename = getattr(file_obj, "name", "未命名文件")
            file_obj.seek(0)
            raw_bytes = file_obj.read()
            if not raw_bytes:
                logger.warning("文件%s为空，已跳过。", filename)
                continue

            raw_text = self.extract_text(raw_bytes)
            transactions = self.structure_transactions(raw_text)

            outcomes.append(
                OCRParseResult(filename=filename, text=raw_text, transactions=transactions)
            )
        return outcomes
