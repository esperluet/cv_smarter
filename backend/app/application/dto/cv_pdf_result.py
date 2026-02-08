from dataclasses import dataclass


@dataclass(frozen=True)
class CvPdfResult:
    filename: str
    content_bytes: bytes
    media_type: str = "application/pdf"
    run_id: str | None = None
