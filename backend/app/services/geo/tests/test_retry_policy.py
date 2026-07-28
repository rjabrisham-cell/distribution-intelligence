# tests/test_retry_policy.py
"""Unit tests for RetryPolicy and RetryExecutor (Sync)."""

import pytest

from app.services.geo.clients.retry_policy import (
    RetryPolicy,
    RetryExecutor,
    BackoffStrategy,
)
from app.services.geo.clients.exceptions import (
    ProviderConnectionError,
    ProviderTimeoutError,
    ProviderServerError,
    ProviderRateLimitError,
)


class TestRetryPolicy:
    """Tests for RetryPolicy configuration dataclass."""

    def test_defaults(self):
        p = RetryPolicy()
        assert p.max_retries == 3
        assert p.backoff_base_seconds == 1.0
        assert p.backoff_multiplier == 2.0
        assert p.max_backoff_seconds == 30.0
        assert 429 in p.retryable_statuses
        assert 502 in p.retryable_statuses
        assert 503 in p.retryable_statuses
        assert 504 in p.retryable_statuses

    def test_custom_values(self):
        p = RetryPolicy(max_retries=1, backoff_base_seconds=0.5)
        assert p.max_retries == 1
        assert p.backoff_base_seconds == 0.5

    def test_disabled_has_zero_retries(self):
        p = RetryPolicy.disabled()
        assert p.max_retries == 0

    def test_default_strategy_is_exponential(self):
        p = RetryPolicy()
        assert p.backoff_strategy == BackoffStrategy.EXPONENTIAL


class TestRetryExecutor:
    """Tests for RetryExecutor (Sync)."""

    def test_success_on_first_attempt(self):
        """Callable succeeds → returns result immediately."""
        executor = RetryExecutor(RetryPolicy(max_retries=2))
        result = executor.execute(lambda: "ok")
        assert result == "ok"

    def test_raises_after_exhausted_retries__connection_error(self):
        """Retryable error → retries exhausted → last exception raised."""
        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ProviderConnectionError("test", "no route to host")

        executor = RetryExecutor(RetryPolicy(
            max_retries=2,
            backoff_base_seconds=0.0,  # no delay in tests
        ))

        with pytest.raises(ProviderConnectionError) as exc_info:
            executor.execute(always_fails)

        assert call_count == 3  # initial + 2 retries
        assert "no route to host" in str(exc_info.value)

    def test_raises_after_exhausted_retries__timeout_error(self):
        """Timeout → retryable → exhausted."""
        call_count = 0

        def always_timeout():
            nonlocal call_count
            call_count += 1
            raise ProviderTimeoutError("test", 10.0, "timed out")

        executor = RetryExecutor(RetryPolicy(
            max_retries=1,
            backoff_base_seconds=0.0,
        ))

        with pytest.raises(ProviderTimeoutError):
            executor.execute(always_timeout)

        assert call_count == 2

    def test_non_retryable_server_error_propagates_immediately(self):
        """500 is NOT in default retryable_statuses → no retry."""
        executor = RetryExecutor(RetryPolicy(max_retries=3))
        call_count = 0

        def raise_500():
            nonlocal call_count
            call_count += 1
            raise ProviderServerError("test", 500, "internal error")

        with pytest.raises(ProviderServerError):
            executor.execute(raise_500)

        assert call_count == 1  # no retry

    def test_retryable_server_error_is_retried(self):
        """502 IS in default retryable_statuses → retried."""
        call_count = 0

        def raise_502():
            nonlocal call_count
            call_count += 1
            raise ProviderServerError("test", 502, "bad gateway")

        executor = RetryExecutor(RetryPolicy(
            max_retries=2,
            backoff_base_seconds=0.0,
        ))

        with pytest.raises(ProviderServerError):
            executor.execute(raise_502)

        assert call_count == 3  # initial + 2 retries

    def test_rate_limit_error_uses_retry_after_hint(self):
        """ProviderRateLimitError with retry_after → uses hint for wait."""
        call_count = 0

        def rate_limited_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProviderRateLimitError("test", retry_after=0.01)
            return "recovered"

        executor = RetryExecutor(RetryPolicy(
            max_retries=2,
            backoff_base_seconds=0.0,
        ))

        result = executor.execute(rate_limited_then_ok)
        assert result == "recovered"
        assert call_count == 2

    def test_rate_limit_without_retry_after(self):
        """ProviderRateLimitError without retry_after → uses backoff."""
        call_count = 0

        def rate_limited_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ProviderRateLimitError("test")  # no retry_after
            return "ok"

        executor = RetryExecutor(RetryPolicy(
            max_retries=1,
            backoff_base_seconds=0.0,
        ))

        result = executor.execute(rate_limited_then_ok)
        assert result == "ok"
        assert call_count == 2

    def test_unknown_exception_propagates_immediately(self):
        """Non-retryable exception (e.g. ValueError) → no retry."""
        executor = RetryExecutor(RetryPolicy(max_retries=3))
        call_count = 0

        def raise_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("unexpected")

        with pytest.raises(ValueError):
            executor.execute(raise_value_error)

        assert call_count == 1

    def test_max_retries_zero_disables_retry(self):
        """max_retries=0 → fails immediately."""
        executor = RetryExecutor(RetryPolicy.disabled())
        call_count = 0

        def fail():
            nonlocal call_count
            call_count += 1
            raise ProviderConnectionError("test", "down")

        with pytest.raises(ProviderConnectionError):
            executor.execute(fail)

        assert call_count == 1


class TestBackoffCalculation:
    """Tests for wait-time calculation."""

    def test_exponential_backoff_grows(self):
        executor = RetryExecutor(RetryPolicy(
            backoff_base_seconds=1.0,
            backoff_multiplier=2.0,
            max_backoff_seconds=60.0,
        ))
        w0 = executor._calc_wait(0)
        w1 = executor._calc_wait(1)
        w2 = executor._calc_wait(2)
        assert w0 == 1.0
        assert w1 == 2.0
        assert w2 == 4.0

    def test_backoff_respects_max(self):
        executor = RetryExecutor(RetryPolicy(
            backoff_base_seconds=1.0,
            backoff_multiplier=10.0,
            max_backoff_seconds=5.0,
        ))
        w3 = executor._calc_wait(3)  # 1 * 10^3 = 1000 → clamped to 5
        assert w3 == 5.0

    def test_hint_overrides_backoff(self):
        """Provider hint (retry_after) takes priority."""
        executor = RetryExecutor(RetryPolicy(
            backoff_base_seconds=10.0,
            max_backoff_seconds=60.0,
        ))
        wait = executor._calc_wait(0, hint=2.5)
        assert wait == 2.5

    def test_hint_respects_max(self):
