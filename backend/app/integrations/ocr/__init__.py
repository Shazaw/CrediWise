"""Process-wide `OcrPort` singleton (PLAN §16.1).

Mirrors `app.integrations.storage`'s `get_storage_port`/`set_storage_port`
seam: `set_ocr_port` lets tests inject a fake instead of requiring a real
Tesseract binary (not installed in this repo's CI image — see
`docs/handoffs/` for the documented sandbox/CI limitation).
"""

from app.integrations.ocr.port import OcrPort
from app.integrations.ocr.tesseract_adapter import TesseractOcrAdapter

__all__ = ["OcrPort", "get_ocr_port", "set_ocr_port"]

_ocr_port: OcrPort | None = None


def get_ocr_port() -> OcrPort:
    global _ocr_port
    if _ocr_port is None:
        _ocr_port = TesseractOcrAdapter()
    return _ocr_port


def set_ocr_port(port: OcrPort | None) -> None:
    """Test hook — inject a fake `OcrPort` instead of a real one."""
    global _ocr_port
    _ocr_port = port
