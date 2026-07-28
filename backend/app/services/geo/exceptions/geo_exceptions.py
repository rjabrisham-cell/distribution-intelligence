"""
exceptions/geo_exceptions.py — Geo Domain Exceptions
======================================================
Contract v1.2

Domain Errors for the Geo layer — NOT HTTP errors.
These exceptions carry structured metadata (error_code, provider, url, ...)
so that upper layers (adapters, services, API handlers) can decide how to
translate them into HTTP responses, log entries, or retry decisions.

Hierarchy:
    GeoException                       # base for ALL geo errors
    ├── GeoProviderError               # base for provider-related errors
    │   ├── ProviderConnectionError
    │   ├── ProviderTimeoutError
    │   ├── ProviderRateLimitError
    │   ├── ProviderAuthError
    │   ├── ProviderServerError
    │   └── ProviderResponseError
    ├── MappingError
    ├── ConfigurationError
    └── AdapterNotImplementedError

No dependency on: providers/, adapters/, clients/, config/
No logging inside exceptions — logging happens at call sites.
"""

from __future__ import annotations

from typing import Any


# ═════════════════════════════════════════════════════════════════
# Base
# ═════════════════════════════════════════════════════════════════

class GeoException(Exception):
    """
    Base exception for ALL Geo-layer errors.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable code (e.g. 'GEO_PROVIDER_TIMEOUT').
        details: Arbitrary key-value context.
        cause: The original exception that caused this one (chaining).
    """

    error_code: str = "GEO_UNKNOWN"

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
        if error_code is not None:
            self.error_code = error_code

    # ── Serialization ─────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize to a JSON-safe dict.

        Does NOT include `cause` (to avoid leaking internal stack traces).
        """
        result: dict[str, Any] = {
            "error_code": self.error_code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result

    # ── Representation ────────────────────────────────────────

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (
            f"{cls}(error_code={self.error_code!r}, "
            f"message={self.message!r}, "
            f"details={self.details!r})"
        )


# ═════════════════════════════════════════════════════════════════
# Provider Errors (base)
# ═════════════════════════════════════════════════════════════════

class GeoProviderError(GeoException):
    """
    Base for errors originating from (or related to) an external Geo provider.

    Additional attributes:
        provider_name: Identifier of the provider (e.g. 'fimap', 'nominatim').
        url: The URL that was being accessed (if applicable).
        http_method: HTTP method (GET, POST, …) — None for non-HTTP providers.
    """

    def __init__(
        self,
        message: str,
        *,
        provider_name: str = "unknown",
        url: str | None = None,
        http_method: str | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            details=details,
            cause=cause,
        )
        self.provider_name = provider_name
        self.url = url
        self.http_method = http_method

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["provider_name"] = self.provider_name
        if self.url:
            result["url"] = self.url
        if self.http_method:
            result["http_method"] = self.http_method
        return result


# ── Concrete Provider Errors ────────────────────────────────────

class ProviderConnectionError(GeoProviderError):
    """
    Raised when the remote provider is unreachable.

    Network/DNS/connection-refused — before any HTTP response.

    Extra attributes:
        host: Hostname or IP that was targeted.
        port: Port number (if known).
    """

    error_code = "GEO_PROVIDER_CONNECTION"

    def __init__(
        self,
        message: str,
        *,
        provider_name: str = "unknown",
        url: str | None = None,
        host: str | None = None,
        port: int | None = None,
        http_method: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            provider_name=provider_name,
            url=url,
            http_method=http_method,
            details=details,
            cause=cause,
        )
        self.host = host
        self.port = port

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.host:
            result["host"] = self.host
        if self.port is not None:
            result["port"] = self.port
        return result


class ProviderTimeoutError(GeoProviderError):
    """
    Raised when a provider call exceeds the configured timeout.

    Extra attributes:
        configured_timeout: The timeout value that was exceeded (seconds).
    """

    error_code = "GEO_PROVIDER_TIMEOUT"

    def __init__(
        self,
        message: str,
        *,
        provider_name: str = "unknown",
        url: str | None = None,
        http_method: str | None = None,
        configured_timeout: float | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            provider_name=provider_name,
            url=url,
            http_method=http_method,
            details=details,
            cause=cause,
        )
        self.configured_timeout = configured_timeout

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.configured_timeout is not None:
            result["configured_timeout"] = self.configured_timeout
        return result


class ProviderRateLimitError(GeoProviderError):
    """
    Raised when the provider returns HTTP 429 or similar back-pressure.

    Extra attributes:
        retry_after: Seconds until the client may retry (from Retry-After header).
        limit: Rate-limit ceiling (from X-RateLimit-Limit header).
        remaining: Remaining requests in the current window.
    """

    error_code = "GEO_PROVIDER_RATE_LIMIT"

    def __init__(
        self,
        message: str,
        *,
        provider_name: str = "unknown",
        url: str | None = None,
        http_method: str | None = None,
        retry_after: float | None = None,
        limit: int | None = None,
        remaining: int | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            provider_name=provider_name,
            url=url,
            http_method=http_method,
            details=details,
            cause=cause,
        )
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        if self.limit is not None:
            result["limit"] = self.limit
        if self.remaining is not None:
            result["remaining"] = self.remaining
        return result


class ProviderAuthError(GeoProviderError):
    """
    Raised when authentication / authorisation fails (HTTP 401/403).

    Extra attributes:
        status_code: The actual HTTP status (401 or 403).
    """

    error_code = "GEO_PROVIDER_AUTH"

    def __init__(
        self,
        message: str,
        *,
        provider_name: str = "unknown",
        url: str | None = None,
        http_method: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        # Validate status_code if provided
        if status_code is not None and status_code not in (401, 403):
            raise ValueError(
                f"ProviderAuthError status_code must be 401 or 403, got {status_code}"
            )
        super().__init__(
            message,
            provider_name=provider_name,
            url=url,
            http_method=http_method,
            details=details,
            cause=cause,
        )
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result


class ProviderServerError(GeoProviderError):
    """
    Raised for 5xx responses (not retried or exhausted all retries).

    Extra attributes:
        status_code: The actual HTTP status (must be 5xx).
    """

    error_code = "GEO_PROVIDER_SERVER_ERROR"

    def __init__(
        self,
        message: str,
        *,
        provider_name: str = "unknown",
        url: str | None = None,
        http_method: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        # Validate: must be 5xx if provided
        if status_code is not None and not (500 <= status_code < 600):
            raise ValueError(
                f"ProviderServerError status_code must be 5xx, got {status_code}"
            )
        super().__init__(
            message,
            provider_name=provider_name,
            url=url,
            http_method=http_method,
            details=details,
            cause=cause,
        )
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result


class ProviderResponseError(GeoProviderError):
    """
    Raised when the provider responds but the payload cannot be parsed/mapped.

    This is for successful HTTP responses (2xx) whose body is malformed,
    or for any response whose Content-Type or structure is unexpected.

    Extra attributes:
        status_code: HTTP status code of the response.
        response_body: Raw response body (truncated for safety).
        content_type: Content-Type header value.
        response_headers: Selected response headers (sanitised).
    """

    error_code = "GEO_PROVIDER_RESPONSE_ERROR"

    _MAX_BODY_LENGTH = 2000  # truncate response body for safety

    def __init__(
        self,
        message: str,
        *,
        provider_name: str = "unknown",
        url: str | None = None,
        http_method: str | None = None,
        status_code: int | None = None,
        response_body: str | None = None,
        content_type: str | None = None,
        response_headers: dict[str, str] | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            provider_name=provider_name,
            url=url,
            http_method=http_method,
            details=details,
            cause=cause,
        )
        self.status_code = status_code
        self.content_type = content_type
        self.response_headers = response_headers or {}

        # Truncate body for safety
        if response_body and len(response_body) > self._MAX_BODY_LENGTH:
            self.response_body = response_body[: self._MAX_BODY_LENGTH] + "..."
        else:
            self.response_body = response_body

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.status_code is not None:
            result["status_code"] = self.status_code
        if self.content_type:
            result["content_type"] = self.content_type
        if self.response_body:
            result["response_body"] = self.response_body
        return result


# ═════════════════════════════════════════════════════════════════
# Internal Errors
# ═════════════════════════════════════════════════════════════════

class MappingError(GeoException):
    """
    Raised when a mapper cannot transform a provider DTO into a canonical DTO.

    Extra attributes:
        source_type: Type/name of the source data (e.g. 'FimapAddressDTO').
        target_type: Type/name of the target data (e.g. 'CanonicalAddressDTO').
    """

    error_code = "GEO_MAPPING_ERROR"

    def __init__(
        self,
        message: str,
        *,
        source_type: str | None = None,
        target_type: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code="GEO_MAPPING_ERROR",
            details=details,
            cause=cause,
        )
        self.source_type = source_type
        self.target_type = target_type

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.source_type:
            result["source_type"] = self.source_type
        if self.target_type:
            result["target_type"] = self.target_type
        return result


class ConfigurationError(GeoException):
    """
    Raised when provider configuration is missing or invalid.

    Extra attributes:
        parameter_name: The config key that caused the error
                        (e.g. 'GEO_FIMAP_TIMEOUT').
    """

    error_code = "GEO_CONFIGURATION_ERROR"

    def __init__(
        self,
        message: str,
        *,
        parameter_name: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code="GEO_CONFIGURATION_ERROR",
            details=details,
            cause=cause,
        )
        self.parameter_name = parameter_name

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.parameter_name:
            result["parameter_name"] = self.parameter_name
        return result


class AdapterNotImplementedError(GeoException):
    """
    Raised by skeleton adapters that have not been implemented yet.

    Extra attributes:
        adapter_name: Name of the adapter that is not yet implemented.
    """

    error_code = "GEO_ADAPTER_NOT_IMPLEMENTED"

    def __init__(
        self,
        adapter_name: str,
        *,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        message = f"Adapter '{adapter_name}' is a skeleton and not yet implemented."
        super().__init__(
            message,
            error_code="GEO_ADAPTER_NOT_IMPLEMENTED",
            details=details,
            cause=cause,
        )
        self.adapter_name = adapter_name

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["adapter_name"] = self.adapter_name
        return result
