import re

from app.domain.models.document_pipeline import CanonicalDocument
from app.domain.services.ingestion_quality_validator import IngestionQualityAssessment


class BasicIngestionQualityValidator:
    def assess(self, document: CanonicalDocument) -> IngestionQualityAssessment:
        text = document.text
        if not text.strip():
            return IngestionQualityAssessment(accepted=False, score=0.0, flags=["empty_text"])

        flags: list[str] = []

        pdf_markers = ["%PDF-", "endobj", "xref", "stream", "endstream"]
        marker_hits = sum(1 for marker in pdf_markers if marker in text)
        if marker_hits >= 3:
            flags.append("pdf_internal_markers")

        non_printable_count = sum(1 for char in text if ord(char) < 32 and char not in "\n\r\t")
        non_printable_ratio = non_printable_count / max(1, len(text))
        if non_printable_ratio > 0.02:
            flags.append("non_printable_ratio_high")

        words = re.findall(r"[A-Za-z]{2,}", text)
        lexical_density = len(words) / max(1, len(text.split()))
        if lexical_density < 0.4:
            flags.append("low_lexical_density")

        score = 1.0
        if "pdf_internal_markers" in flags:
            score -= 0.6
        if "non_printable_ratio_high" in flags:
            score -= 0.25
        if "low_lexical_density" in flags:
            score -= 0.2
        score = max(0.0, round(score, 3))

        accepted = not ({"pdf_internal_markers", "non_printable_ratio_high"} & set(flags))
        return IngestionQualityAssessment(accepted=accepted, score=score, flags=flags)
