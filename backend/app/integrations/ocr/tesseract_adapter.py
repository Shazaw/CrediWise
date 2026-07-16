"""`OcrPort` adapter over the local Tesseract binary (PLAN C4).

Bounded: a hard timeout so a pathological image can't hang the `documents`
worker (mirrors the local-Kimi timeout requirement, PLAN §16.3, for the same
class of "external recognition engine" risk). No network call — Tesseract
runs entirely on controlled infrastructure, consistent with PLAN §16.1's
"raw statements never leave controlled infrastructure" posture.
"""

import io

import pytesseract
from PIL import Image, UnidentifiedImageError

from app.core.errors import IntegrationError

_OCR_TIMEOUT_SECONDS = 20


class TesseractOcrAdapter:
    def extract_text(self, image_bytes: bytes) -> str:
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                return str(pytesseract.image_to_string(img, timeout=_OCR_TIMEOUT_SECONDS))
        except UnidentifiedImageError as exc:
            raise IntegrationError("OCR failed: unreadable image") from exc
        except pytesseract.TesseractNotFoundError as exc:
            raise IntegrationError("OCR failed: Tesseract binary not available") from exc
        except RuntimeError as exc:
            # pytesseract raises RuntimeError for both a timeout and a
            # nonzero Tesseract exit code — neither is fatal to the pipeline.
            raise IntegrationError(f"OCR failed: {exc}") from exc
