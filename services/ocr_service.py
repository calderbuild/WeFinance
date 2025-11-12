"""Services responsible for OCR extraction and structuring."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, BinaryIO, Iterable, List, Optional

from models.entities import OCRParseResult, Transaction
from services.vision_ocr_service import VisionOCRService
from utils.error_handling import UserFacingError

try:  # pragma: no cover - 外部依赖按需安装
    import pypdfium2 as pdfium
except ImportError:  # pragma: no cover - 运行时再提示用户安装
    pdfium = None

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 200
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
PDF_RENDER_SCALE = 2.0


def _t(key: str, fallback: str, **kwargs) -> str:
    """Translate error messages when session/i18n is available."""

    try:
        from utils.session import get_i18n  # Imported lazily to avoid hard dependency

        return get_i18n().t(key, **kwargs)
    except Exception:  # pylint: disable=broad-except
        try:
            return fallback.format(**kwargs)
        except Exception:  # pragma: no cover - 格式化失败时回退原文
            return fallback


def _looks_like_pdf(filename: str, mime_type: str | None) -> bool:
    """判断文件是否为PDF，避免误把CSV交给OCR。"""

    suffix_match = Path(filename or "").suffix.lower() == ".pdf"
    mime_match = (mime_type or "").lower().endswith("pdf")
    return suffix_match or mime_match


def _convert_pdf_to_images(file_bytes: bytes, filename: str) -> List[bytes]:
    """把PDF逐页渲染为PNG字节，方便Vision模型处理。"""

    if pdfium is None:
        message = _t(
            "errors.pdf_render_fail",
            "PDF support is not enabled on this server.",
        )
        suggestion = _t(
            "errors.pdf_render_fail_suggestion",
            "Install pypdfium2 or enable PDF rendering before uploading.",
        )
        raise UserFacingError(message, suggestion=suggestion)

    try:
        pdf_doc = pdfium.PdfDocument(io.BytesIO(file_bytes))
    except Exception as exc:  # pylint: disable=broad-except
        message = _t(
            "errors.pdf_render_fail",
            "Unable to read the PDF file {filename}.",
            filename=filename,
        )
        suggestion = _t(
            "errors.pdf_render_fail_suggestion",
            "Please confirm the PDF is not encrypted and retry.",
        )
        raise UserFacingError(message, suggestion=suggestion, original_error=exc) from exc

    if len(pdf_doc) == 0:
        message = _t(
            "errors.pdf_render_fail",
            "PDF does not contain any pages: {filename}.",
            filename=filename,
        )
        raise UserFacingError(message)

    images: List[bytes] = []
    for page in pdf_doc:
        bitmap = page.render(scale=PDF_RENDER_SCALE)
        pil_image = bitmap.to_pil()
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        images.append(buffer.getvalue())
        buffer.close()
        pil_image.close()

    pdf_doc.close()
    return images


class OCRService:
    """使用Vision LLM进行高精度OCR识别和结构化（替代PaddleOCR）."""

    def __init__(
        self,
        use_angle_class: bool = True,
        lang: str = "ch",
        structuring_service: Optional[Any] = None,
    ) -> None:
        """
        初始化OCR服务

        Args:
            use_angle_class: 保留参数用于向后兼容，但不再使用
            lang: 保留参数用于向后兼容，但不再使用
            structuring_service: 不再需要，Vision LLM直接输出结构化数据
        """
        # 使用Vision LLM服务（默认gpt-4o）
        self._vision_ocr = VisionOCRService(model="gpt-4o")
        logger.info("OCR服务初始化完成，使用Vision LLM (gpt-4o)")

    def extract_text(self, image_bytes: bytes) -> str:
        """
        运行OCR识别（仅用于兼容性，实际使用Vision LLM直接提取交易）

        Args:
            image_bytes: 图片字节数据

        Returns:
            OCR识别的文本（简化版本，主要用于日志）
        """
        try:
            # 使用Vision LLM提取交易
            transactions = self._vision_ocr.extract_transactions_from_image(image_bytes)

            # 生成简单的文本表示用于日志
            lines = []
            for txn in transactions:
                lines.append(
                    f"{txn.date} | {txn.merchant} | {txn.category} | ¥{txn.amount}"
                )

            return (
                "\n".join(lines)
                if lines
                else _t(
                    "bill_upload.vision_structured_placeholder",
                    "Vision OCR returned structured transactions directly.",
                )
            )

        except UserFacingError:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("OCR识别失败：%s", exc)
            raise RuntimeError(
                _t("errors.ocr_run_fail", "OCR failed. Please check image quality.")
            ) from exc

    def structure_transactions(self, ocr_text: str) -> List[Transaction]:
        """
        结构化交易数据（已弃用，Vision LLM直接输出结构化数据）

        Args:
            ocr_text: OCR文本（不再使用）

        Returns:
            空列表（实际数据在process_files中直接获取）
        """
        logger.warning("structure_transactions已弃用，请直接使用Vision LLM提取交易")
        return []

    def process_files(self, files: Iterable[BinaryIO]) -> List[OCRParseResult]:
        """
        处理上传的文件，使用Vision LLM提取交易记录

        Args:
            files: 上传的文件对象

        Returns:
            OCRParseResult列表
        """
        outcomes: List[OCRParseResult] = []
        for file_obj in files:
            filename = getattr(
                file_obj,
                "name",
                _t("common.unnamed_file", "Uploaded file"),
            )
            mime_type = getattr(file_obj, "type", None)
            file_obj.seek(0)
            raw_bytes = file_obj.read()
            if not raw_bytes:
                logger.warning("文件%s为空，已跳过。", filename)
                continue

            if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
                message = _t(
                    "errors.file_too_large",
                    "File {filename} exceeds the {size}MB upload limit.",
                    filename=filename,
                    size=MAX_FILE_SIZE_MB,
                )
                suggestion = _t(
                    "errors.file_too_large_suggestion",
                    "Please compress the file or split it before retrying.",
                )
                raise UserFacingError(message, suggestion=suggestion)

            try:
                if _looks_like_pdf(filename, mime_type):
                    # PDF需要先渲染为图片再识别
                    page_images = _convert_pdf_to_images(raw_bytes, filename)
                    transactions: List[Transaction] = []
                    for page_bytes in page_images:
                        transactions.extend(
                            self._vision_ocr.extract_transactions_from_image(
                                page_bytes
                            )
                        )
                else:
                    # 使用Vision LLM直接提取交易记录
                    transactions = self._vision_ocr.extract_transactions_from_image(
                        raw_bytes
                    )

                # 生成简单的OCR文本用于显示
                raw_text = "\n".join(
                    f"{txn.date} | {txn.merchant} | {txn.category} | ¥{txn.amount}"
                    for txn in transactions
                )

                outcomes.append(
                    OCRParseResult(
                        filename=filename, text=raw_text, transactions=transactions
                    )
                )
                logger.info(f"文件 {filename} 识别到 {len(transactions)} 条交易记录")

            except UserFacingError:
                # 让UI层展示友好错误
                raise
            except Exception as exc:  # pylint: disable=broad-except
                logger.error(f"处理文件 {filename} 失败: {exc}")
                # 返回空结果而不是抛出异常，让用户可以继续处理其他文件
                failure_text = _t("errors.ocr_run_fail", "OCR failed.")
                outcomes.append(
                    OCRParseResult(
                        filename=filename,
                        text=f"{failure_text}: {str(exc)}",
                        transactions=[],
                    )
                )

        return outcomes
