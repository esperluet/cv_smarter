from importlib.metadata import PackageNotFoundError, version
from typing import Any

from app.domain.models.document_pipeline import CanonicalDocument, IngestionPolicy, IngestionResult, InputDocument, ProcessingReport


class DoclingDocumentIngestor:
    def __init__(
        self,
        supported_media_types: set[str] | None = None,
        *,
        enable_pdf_ocr: bool = False,
    ) -> None:
        default_media_types = {
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/tiff",
            "image/bmp",
        }
        self._supported_media_types = supported_media_types or default_media_types
        self._enable_pdf_ocr = enable_pdf_ocr

    def supports(self, media_type: str) -> bool:
        return media_type in self._supported_media_types

    def ingest(self, document: InputDocument, *, policy: IngestionPolicy | None = None) -> IngestionResult:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pdf_options = PdfPipelineOptions()
        should_enable_ocr = self._enable_pdf_ocr
        if policy is not None:
            should_enable_ocr = policy.ocr_enabled
        pdf_options.do_ocr = should_enable_ocr
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            }
        )
        conversion_result = converter.convert(str(document.source_path))
        docling_document = self._resolve_document(conversion_result)

        markdown = self._export_markdown(docling_document)
        docling_payload = self._export_payload(docling_document)

        canonical_document = CanonicalDocument(
            schema_version="1.0",
            source_media_type=document.media_type,
            text=markdown,
            metadata={"original_name": document.original_name},
            extensions={"docling": docling_payload},
        )

        report = ProcessingReport(
            engine_name="docling",
            engine_version=self._resolve_docling_version(),
            warnings=[],
        )

        return IngestionResult(canonical_document=canonical_document, report=report)

    def _resolve_docling_version(self) -> str | None:
        try:
            return version("docling")
        except PackageNotFoundError:
            return None

    def _resolve_document(self, conversion_result: Any) -> Any:
        if hasattr(conversion_result, "document"):
            return conversion_result.document
        return conversion_result

    def _export_markdown(self, docling_document: Any) -> str:
        if hasattr(docling_document, "export_to_markdown"):
            return docling_document.export_to_markdown()
        return str(docling_document)

    def _export_payload(self, docling_document: Any) -> dict[str, Any]:
        if hasattr(docling_document, "export_to_dict"):
            exported = docling_document.export_to_dict()
            if isinstance(exported, dict):
                return exported
        return {"content": str(docling_document)}
