from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")

    upload_dir: str = Field(default="/app/uploads", alias="UPLOAD_DIR")
    artifact_dir: str = Field(default="/app/artifacts", alias="ARTIFACT_DIR")
    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_UPLOAD_SIZE_BYTES")
    document_ingestor_preferred: str = Field(default="fallback", alias="DOCUMENT_INGESTOR_PREFERRED")
    document_output_formats: str = Field(default="markdown,json", alias="DOCUMENT_OUTPUT_FORMATS")
    document_pdf_do_ocr: bool = Field(default=False, alias="DOCUMENT_PDF_DO_OCR")
    document_ocr_auto_retry_on_quality_failure: bool = Field(
        default=True,
        alias="DOCUMENT_OCR_AUTO_RETRY_ON_QUALITY_FAILURE",
    )
    document_ocr_retry_min_text_length: int = Field(
        default=120,
        alias="DOCUMENT_OCR_RETRY_MIN_TEXT_LENGTH",
    )
    cv_generation_providers_config_path: str = Field(
        default="config/llm/providers.yml",
        alias="CV_GENERATION_PROVIDERS_CONFIG_PATH",
    )
    cv_generation_profiles_config_path: str = Field(
        default="config/llm/profiles.yml",
        alias="CV_GENERATION_PROFILES_CONFIG_PATH",
    )
    cv_generation_graph_index_config_path: str = Field(
        default="config/graphs/index.yml",
        alias="CV_GENERATION_GRAPH_INDEX_CONFIG_PATH",
    )
    cv_generation_prompts_dir: str = Field(default="prompts", alias="CV_GENERATION_PROMPTS_DIR")
    cv_generation_trace_dir: str = Field(default="traces", alias="CV_GENERATION_TRACE_DIR")
    cv_generation_max_job_description_chars: int = Field(
        default=12000,
        alias="CV_GENERATION_MAX_JOB_DESCRIPTION_CHARS",
    )
    preserve_failed_uploads: bool = Field(default=False, alias="PRESERVE_FAILED_UPLOADS")
    artifact_download_mode: str = Field(default="auto", alias="ARTIFACT_DOWNLOAD_MODE")
    artifact_download_token_ttl_seconds: int = Field(default=300, alias="ARTIFACT_DOWNLOAD_TOKEN_TTL_SECONDS")

    database_url: str = Field(
        default="postgresql+psycopg://cv_optimizer:cv_optimizer@postgres:5432/cv_optimizer",
        alias="DATABASE_URL",
    )

    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    security_strict_mode: bool | None = Field(default=None, alias="SECURITY_STRICT_MODE")

    smtp_host: str = Field(default="mailpit", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_use_tls: bool = Field(default=False, alias="SMTP_USE_TLS")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="noreply@cv-optimizer.local", alias="SMTP_FROM_EMAIL")

    @staticmethod
    def normalize_database_url_value(value: str) -> str:
        if not isinstance(value, str):
            return value

        lower_value = value.lower()
        if lower_value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://") :]
            lower_value = value.lower()

        if lower_value.startswith("postgresql+psycopg2://"):
            return "postgresql+psycopg://" + value[len("postgresql+psycopg2://") :]

        if lower_value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://") :]

        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return cls.normalize_database_url_value(value)

    @model_validator(mode="after")
    def validate_security(self) -> "Settings":
        if self.security_strict_mode is None:
            strict_mode = not self.is_development_env()
        else:
            strict_mode = self.security_strict_mode

        if strict_mode and (self.jwt_secret_key == "change-me" or len(self.jwt_secret_key) < 24):
            raise ValueError("JWT_SECRET_KEY must be set with a strong value outside development")
        if self.artifact_download_mode not in {"auto", "legacy", "signed"}:
            raise ValueError("ARTIFACT_DOWNLOAD_MODE must be one of: auto, legacy, signed")
        if self.artifact_download_token_ttl_seconds < 30:
            raise ValueError("ARTIFACT_DOWNLOAD_TOKEN_TTL_SECONDS must be >= 30")
        return self

    def is_development_env(self) -> bool:
        return self.app_env.lower() in {"dev", "development", "local", "test", "testing"}

    def is_security_strict_mode(self) -> bool:
        if self.security_strict_mode is None:
            return not self.is_development_env()
        return self.security_strict_mode

    def use_signed_artifact_download(self) -> bool:
        if self.artifact_download_mode == "signed":
            return True
        if self.artifact_download_mode == "legacy":
            return False
        return self.is_security_strict_mode()


settings = Settings()
