"""
Application custom exceptions.
"""


class FileProcessingError(Exception):
    """Raised when an uploaded/imported file cannot be processed."""

    def __init__(self, message: str):
        super().__init__(message)


class ValidationError(Exception):
    """Raised when imported data fails validation."""

    def __init__(self, message: str):
        super().__init__(message)


class ImportError(Exception):
    """Raised when an import operation fails."""

    def __init__(self, message: str):
        super().__init__(message)