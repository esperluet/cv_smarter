import html
import re

from app.application.errors import CvExportError
from app.domain.services.cv_exporter import CvExporter


class MarkdownPdfExporter(CvExporter):
    def __init__(self) -> None:
        try:
            import markdown  # noqa: PLC0415
            from fpdf import FPDF  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - explicit runtime failure path
            raise CvExportError(
                "PDF export dependencies are missing. Install backend requirements to enable PDF export."
            ) from exc

        self._markdown = markdown
        self._pdf_class = FPDF

    def render_pdf(self, *, content: str, format_hint: str | None = None) -> bytes:
        normalized = content.strip()
        if not normalized:
            raise CvExportError("Cannot export empty content to PDF")

        normalized = _normalize_for_pdf(normalized)
        is_markdown = _is_markdown_content(normalized, format_hint=format_hint)
        body_html = self._render_body_html(normalized, is_markdown=is_markdown)

        try:
            return self._render_html_pdf(body_html)
        except Exception:
            # Some model outputs include HTML/Markdown combinations unsupported by
            # fpdf's HTML engine. Fallback keeps export available.
            plain = _markdown_to_plain_text(normalized)
            try:
                return self._render_plain_text_pdf(plain)
            except Exception as exc:  # pragma: no cover - converter errors vary by runtime
                raise CvExportError("Failed to render PDF from content") from exc

    def _render_body_html(self, content: str, *, is_markdown: bool) -> str:
        if is_markdown:
            return self._markdown.markdown(
                content,
                extensions=["extra", "sane_lists", "nl2br"],
            )

        escaped = html.escape(content)
        paragraphs = [segment.strip() for segment in escaped.splitlines()]
        joined = "</p><p>".join(segment for segment in paragraphs if segment)
        return f"<p>{joined}</p>" if joined else "<p></p>"

    def _render_html_pdf(self, body_html: str) -> bytes:
        pdf = self._pdf_class(format="A4")
        pdf.set_auto_page_break(auto=True, margin=14)
        pdf.set_margins(14, 14, 14)
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        pdf.write_html(body_html)
        return _coerce_pdf_output(pdf.output())

    def _render_plain_text_pdf(self, content: str) -> bytes:
        pdf = self._pdf_class(format="A4")
        pdf.set_auto_page_break(auto=True, margin=14)
        pdf.set_margins(14, 14, 14)
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)

        line_height = 6
        for line in content.splitlines():
            stripped = line.rstrip()
            if stripped:
                pdf.multi_cell(0, line_height, stripped)
            else:
                pdf.ln(line_height / 2)

        return _coerce_pdf_output(pdf.output())


def _is_markdown_content(content: str, *, format_hint: str | None) -> bool:
    normalized_hint = (format_hint or "").strip().lower()
    if normalized_hint in {"markdown", "md"}:
        return True
    if normalized_hint in {"text", "plain", "plain_text"}:
        return False

    markdown_markers = [
        r"^#{1,6}\s+",
        r"^\s*[-*+]\s+",
        r"^\s*\d+\.\s+",
        r"\*\*[^*]+\*\*",
        r"```",
    ]
    return any(re.search(marker, content, flags=re.MULTILINE) for marker in markdown_markers)


def _coerce_pdf_output(output: object) -> bytes:
    if isinstance(output, (bytes, bytearray)):
        return bytes(output)
    if isinstance(output, str):
        return output.encode("latin-1", errors="replace")
    raise CvExportError("PDF renderer returned unsupported output type")


def _normalize_for_pdf(content: str) -> str:
    return content.encode("latin-1", errors="replace").decode("latin-1")


def _markdown_to_plain_text(content: str) -> str:
    without_fences = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    without_headers = re.sub(r"^\s*#{1,6}\s*", "", without_fences, flags=re.MULTILINE)
    without_emphasis = re.sub(r"(\*\*|__|\*|_)", "", without_headers)
    without_links = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", without_emphasis)
    return without_links
