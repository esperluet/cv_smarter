class ApplicationError(Exception):
    pass


class EmailAlreadyExistsError(ApplicationError):
    pass


class InvalidCredentialsError(ApplicationError):
    pass


class InvalidRefreshTokenError(ApplicationError):
    pass


class UserNotFoundError(ApplicationError):
    pass


class MissingFileNameError(ApplicationError):
    pass


class UnsupportedFileTypeError(ApplicationError):
    pass


class UploadedFileTooLargeError(ApplicationError):
    pass


class UnsupportedOutputFormatError(ApplicationError):
    pass


class IngestorNotFoundError(ApplicationError):
    pass


class IngestionFailedError(ApplicationError):
    pass


class LowQualityExtractionError(ApplicationError):
    pass


class RenderingFailedError(ApplicationError):
    pass


class ArtifactPersistenceError(ApplicationError):
    pass


class InvalidJobDescriptionError(ApplicationError):
    pass


class InvalidGroundSourceNameError(ApplicationError):
    pass


class GroundSourceNotFoundError(ApplicationError):
    pass


class CvExportError(ApplicationError):
    pass


class CvGenerationConfigurationError(ApplicationError):
    pass


class CvGenerationExecutionError(ApplicationError):
    pass


class PromptResolutionError(ApplicationError):
    pass
