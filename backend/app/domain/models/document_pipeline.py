from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InputDocument:
    source_path: Path
    original_name: str
    media_type: str


@dataclass(frozen=True)
class IngestionPolicy:
    ocr_enabled: bool = False
    decision_reason: str = "default"


@dataclass(frozen=True)
class CanonicalDocument:
    schema_version: str
    source_media_type: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessingReport:
    engine_name: str
    engine_version: str | None = None
    warnings: list[str] = field(default_factory=list)
    quality_score: float | None = None
    quality_flags: list[str] = field(default_factory=list)
    engine_attempts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IngestionResult:
    canonical_document: CanonicalDocument
    report: ProcessingReport


@dataclass(frozen=True)
class RenderedArtifact:
    format: str
    media_type: str
    storage_path: str


@dataclass(frozen=True)
class DocumentProcessingResult:
    canonical_document: CanonicalDocument
    report: ProcessingReport
    artifacts: list[RenderedArtifact]
