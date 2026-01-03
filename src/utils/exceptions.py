class PipelineError(Exception):
    """Base exception for all pipeline operations.

    Attributes:
        retryable: Class-level flag indicating if this error type is transient
                   and may succeed on retry. Subclasses should override this.
    """

    retryable: bool = False  # Default to non-retryable

    def __init__(self, message: str, company_name: str | None = None):
        self.company_name = company_name
        super().__init__(message)


class CompanyProcessingError(PipelineError):
    """Error processing a specific company."""

    def __init__(
        self, company_name: str, original_error: Exception, stage: str = "unknown"
    ):
        self.original_error = original_error
        self.stage = stage
        message = f"Failed to process company '{company_name}' in stage '{stage}': {original_error}"
        super().__init__(message, company_name)


class ConfigurationError(PipelineError):
    """Error in pipeline configuration."""

    def __init__(self, message: str, config_field: str | None = None):
        self.config_field = config_field
        if config_field:
            message = f"Configuration error in '{config_field}': {message}"
        super().__init__(message)


class OpenAIProcessingError(PipelineError):
    """Error processing content with OpenAI API.

    Retryable because API errors (rate limits, timeouts) are typically transient.
    """

    retryable = True

    def __init__(
        self,
        message: str,
        company_name: str | None = None,
        response_text: str | None = None,
    ):
        self.response_text = response_text
        super().__init__(f"OpenAI processing failed: {message}", company_name)


class FileOperationError(PipelineError):
    """Error performing file operations."""

    def __init__(
        self,
        operation: str,
        file_path: str,
        message: str,
        company_name: str | None = None,
    ):
        self.operation = operation
        self.file_path = file_path
        full_message = (
            f"File operation '{operation}' failed for '{file_path}': {message}"
        )
        super().__init__(full_message, company_name)


class ValidationError(PipelineError):
    """Error validating data or configuration."""

    def __init__(self, field: str, value: str, message: str):
        self.field = field
        self.value = value
        full_message = (
            f"Validation failed for field '{field}' with value '{value}': {message}"
        )
        super().__init__(full_message)


class WebExtractionError(PipelineError):
    """Error during web extraction operations.

    Retryable because network issues and page load timeouts are typically transient.
    """

    retryable = True

    def __init__(
        self,
        url: str,
        original_error: Exception,
        company_name: str | None = None,
        retry_attempt: int | None = None,
    ):
        self.url = url
        self.original_error = original_error
        self.company_name = company_name
        self.retry_attempt = retry_attempt

        # Build descriptive error message
        message = f"Web extraction failed for URL: {url}"

        if company_name:
            message += f" (Company: {company_name})"

        if retry_attempt is not None:
            message += f" (Retry attempt: {retry_attempt})"

        message += f" - {original_error!s}"

        super().__init__(message, company_name)


class DatabaseOperationError(PipelineError):
    """Error performing database operations.

    Retryable because connection issues and temporary unavailability are transient.
    """

    retryable = True

    def __init__(
        self,
        operation: str,
        message: str,
        company_name: str | None = None,
        stage: str | None = None,
    ):
        self.operation = operation
        self.stage = stage

        full_message = f"Database operation '{operation}' failed: {message}"

        if stage:
            full_message += f" (Stage: {stage})"

        super().__init__(full_message, company_name)
