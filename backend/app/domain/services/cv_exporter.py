from typing import Protocol


class CvExporter(Protocol):
    def render_pdf(self, *, content: str, format_hint: str | None = None) -> bytes:
        ...
