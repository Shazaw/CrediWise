"""`get_ocr_port`/`set_ocr_port` override seam (PLAN §16.1 pattern).

No real Tesseract call here — the binary isn't installed in this repo's CI
image (documented sandbox/CI limitation, see `docs/handoffs/`). Gate tests
only exercise the seam and the adapter's own error handling on bytes that
are guaranteed to fail before ever invoking the `tesseract` subprocess.
"""

from app.core.errors import IntegrationError
from app.integrations.ocr import get_ocr_port, set_ocr_port
from app.integrations.ocr.tesseract_adapter import TesseractOcrAdapter


def test_get_ocr_port_defaults_to_tesseract_adapter() -> None:
    set_ocr_port(None)
    try:
        assert isinstance(get_ocr_port(), TesseractOcrAdapter)
    finally:
        set_ocr_port(None)


def test_set_ocr_port_overrides_the_singleton() -> None:
    class _FakeOcr:
        def extract_text(self, image_bytes: bytes) -> str:
            return "fake recognized text"

    fake = _FakeOcr()
    set_ocr_port(fake)
    try:
        assert get_ocr_port() is fake
    finally:
        set_ocr_port(None)


def test_tesseract_adapter_raises_integration_error_on_unreadable_image() -> None:
    adapter = TesseractOcrAdapter()

    try:
        adapter.extract_text(b"not an image")
    except IntegrationError:
        pass
    else:
        raise AssertionError("expected IntegrationError for unreadable image bytes")
