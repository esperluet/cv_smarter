from app.domain.models.document_pipeline import CanonicalDocument


class MarkdownRenderer:
    @property
    def output_format(self) -> str:
        return "markdown"

    @property
    def media_type(self) -> str:
        return "text/markdown"

    def render(self, document: CanonicalDocument) -> str:
        return document.text
