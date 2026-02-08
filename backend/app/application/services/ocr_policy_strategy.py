from dataclasses import dataclass

from app.domain.models.document_pipeline import IngestionPolicy, InputDocument


@dataclass(frozen=True)
class OcrRetryContext:
    quality_flags: list[str]
    extracted_text: str
    previous_policy: IngestionPolicy


class RuleBasedOcrPolicyStrategy:
    def __init__(
        self,
        *,
        default_ocr_enabled: bool = False,
        auto_retry_on_quality_failure: bool = True,
        retry_min_text_length: int = 120,
    ) -> None:
        self._default_ocr_enabled = default_ocr_enabled
        self._auto_retry_on_quality_failure = auto_retry_on_quality_failure
        self._retry_min_text_length = retry_min_text_length

    def initial_policy(self, document: InputDocument) -> IngestionPolicy:
        if not self._is_ocr_candidate(document.media_type):
            return IngestionPolicy(ocr_enabled=False, decision_reason="ocr_not_applicable")
        if self._default_ocr_enabled:
            return IngestionPolicy(ocr_enabled=True, decision_reason="configured_default_on")
        return IngestionPolicy(ocr_enabled=False, decision_reason="configured_default_off")

    def retry_policy(self, document: InputDocument, *, context: OcrRetryContext) -> IngestionPolicy | None:
        if not self._auto_retry_on_quality_failure:
            return None
        if context.previous_policy.ocr_enabled:
            return None
        if not self._is_ocr_candidate(document.media_type):
            return None
        if not self._should_retry(context):
            return None
        return IngestionPolicy(ocr_enabled=True, decision_reason="quality_gate_retry")

    def _is_ocr_candidate(self, media_type: str) -> bool:
        return media_type == "application/pdf" or media_type.startswith("image/")

    def _should_retry(self, context: OcrRetryContext) -> bool:
        retry_flags = {"pdf_internal_markers", "non_printable_ratio_high", "empty_text"}
        if retry_flags.intersection(context.quality_flags):
            return True
        return len(context.extracted_text.strip()) < self._retry_min_text_length
