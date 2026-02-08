import pytest

from app.application.errors import CvExportError
from app.application.use_cases.export_cv_pdf import ExportCvPdfUseCase
from app.application.use_cases.generate_targeted_cv_pdf_from_source import GenerateTargetedCvPdfFromSourceUseCase


class FakeExporter:
    def __init__(self, content: bytes = b"%PDF-1.7\n...") -> None:
        self.content = content
        self.calls: list[tuple[str, str | None]] = []

    def render_pdf(self, *, content: str, format_hint: str | None = None) -> bytes:
        self.calls.append((content, format_hint))
        return self.content


class FakeGenerator:
    def execute(self, *, user_id: str, source_id: str, job_description: str, graph_id: str | None = None):
        return type(
            "GenerationResult",
            (),
            {
                "source": type("Source", (), {"name": "My Full Career"})(),
                "generation_result": type(
                    "CvResult",
                    (),
                    {
                        "run_id": "run_123",
                        "final_cv": "# Title\n\n- Bullet",
                    },
                )(),
            },
        )()


def test_export_cv_pdf_use_case_success() -> None:
    exporter = FakeExporter()
    use_case = ExportCvPdfUseCase(exporter=exporter)

    result = use_case.execute(content="# Hello", format_hint="markdown", filename="my_cv")

    assert result.filename == "my_cv.pdf"
    assert result.media_type == "application/pdf"
    assert result.content_bytes.startswith(b"%PDF")
    assert exporter.calls == [("# Hello", "markdown")]


def test_export_cv_pdf_use_case_rejects_empty_content() -> None:
    use_case = ExportCvPdfUseCase(exporter=FakeExporter())

    with pytest.raises(CvExportError):
        use_case.execute(content="   ")


def test_generate_targeted_cv_pdf_from_source_use_case_success() -> None:
    exporter_use_case = ExportCvPdfUseCase(exporter=FakeExporter())
    use_case = GenerateTargetedCvPdfFromSourceUseCase(
        generator=FakeGenerator(),
        exporter=exporter_use_case,
    )

    result = use_case.execute(
        user_id="user_1",
        source_id="source_1",
        job_description="Target role",
        graph_id="cv_rewrite_v1",
    )

    assert result.filename.endswith(".pdf")
    assert result.filename.startswith("my_full_career_")
    assert result.media_type == "application/pdf"
    assert result.content_bytes.startswith(b"%PDF")
    assert result.run_id == "run_123"
