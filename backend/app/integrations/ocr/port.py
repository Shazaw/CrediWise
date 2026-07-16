"""`OcrPort` — the OCR integration interface (PLAN C4, §15.3 item 2).

Tesseract is invoked as a subprocess (filesystem + process I/O), so it lives
in `integrations/`, not `engines/` (PLAN §10.1 Golden Rule 3: "Engines never
do I/O... inject if needed"). `app/engines/extraction/image_parser.py` only
ever receives already-recognized text — it never calls this port itself.
"""

from typing import Protocol


class OcrPort(Protocol):
    def extract_text(self, image_bytes: bytes) -> str:
        """Returns recognized text for the given image. Raises
        `IntegrationError` if the OCR engine is unavailable or fails
        (PLAN C4: "must not block the whole pipeline if one path fails" —
        callers treat that as a per-document extraction failure, not a
        crash)."""
        ...
