from app.infrastructure.rendering.markdown_pdf_exporter import MarkdownPdfExporter


def test_markdown_pdf_exporter_renders_pdf_bytes() -> None:
    exporter = MarkdownPdfExporter()

    output = exporter.render_pdf(
        content="# CV Title\n\n**Profile**\n\n- Item 1\n- Item 2",
        format_hint="markdown",
    )

    assert output.startswith(b"%PDF")


def test_markdown_pdf_exporter_supports_plain_text_fallback() -> None:
    exporter = MarkdownPdfExporter()

    output = exporter.render_pdf(
        content="Plain text resume content\nwith multiple lines.",
        format_hint="text",
    )

    assert output.startswith(b"%PDF")


def test_markdown_pdf_exporter_falls_back_when_html_render_fails(monkeypatch) -> None:
    exporter = MarkdownPdfExporter()

    def fail_html_render(_body_html: str) -> bytes:
        raise ValueError("html render failed")

    monkeypatch.setattr(exporter, "_render_html_pdf", fail_html_render)
    output = exporter.render_pdf(
        content="# Title\n\n- first item",
        format_hint="markdown",
    )

    assert output.startswith(b"%PDF")
