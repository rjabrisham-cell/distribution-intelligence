"""
retry_policy.py — Retry Policy & Executor (Sync)
==================================================
Contract v1.2 — Decision: Sync (گزینه A)

Generic, provider-agnostic, synchronous retry logic.

Features:
    - Exponential backoff with configurable multiplier
    - Configurable retryable HTTP statuses
    - Disable retry via max_retries=0
    - Jitter-ready architecture (backoff_strategy slot)
    - Provider-agnostic: works with any callable, not just HTTP
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ═════════════════════════════════════════════════════════════
# Backoff Strategy Enum (for future Jitter)
# ═════════════════════════════════════════════════════════════

class BackoffStrategy(Enum):
    """استراتژی محاسبه wait time بین retryها."""

    EXPONENTIAL = auto()     # base * multiplier^attempt
    EXPONENTIAL_JITTER = auto()  # exponential + random jitter
    LINEAR = auto()          # base * attempt


# ═════════════════════════════════════════════════════════════
# RetryPolicy
# ═════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RetryPolicy:
    """
    Immutable retry configuration.

    Attributes:
        max_retries: حداکثر تعداد retry (0 = بدون retry).
        backoff_base_seconds: زمان پایه انتظار قبل از اولین retry.
        backoff_multiplier: ضریب نمایی برای retryهای متوالی.
        max_backoff_seconds: سقف زمان انتظار.
        retryable_statuses: HTTP status codes که retry می‌شوند.
        backoff_strategy: استراتژی backoff (پیش‌بینی برای Jitter).
        jitter_factor: درصد نویز برای EXPONENTIAL_JITTER (0.0 ~ 0.3).
    """

    max_retries: int = 3
    backoff_base_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 30.0
    retryable_statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 502, 503, 504})
    )
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter_factor: float = 0.1

    @classmethod
    def disabled(cls) -> RetryPolicy:
        """ساخت RetryPolicy بدون retry."""
        return cls(max_retries=0)

    @classmethod
    def from_config(cls) -> RetryPolicy:
        """ساخت RetryPolicy از Config (با fallback به defaultها)."""
        try:
            from app.core.config import settings
            return cls(
                max_retries=getattr(settings, "GEO_RETRY_MAX_RETRIES", 3),
                backoff_base_seconds=getattr(settings, "GEO_RETRY_BASE_SECONDS", 1.0),
                backoff_multiplier=getattr(settings, "GEO_RETRY_MULTIPLIER", 2.0),
                max_backoff_seconds=getattr(settings, "GEO_RETRY_MAX_BACKOFF", 30.0),
                retryable_statuses=frozenset(
                    getattr(settings, "GEO_RETRYABLE_STATUSES", [429, 502, 503, 504])
                ),
            )
        except ImportError:
            return cls()


# ═════════════════════════════════════════════════════════════
# RetryExecutor
# ═════════════════════════════════════════════════════════════

class RetryExecutor:
    """
    اجرای callable با retry logic (Sync / Generic).

    این کلاس provider-agnostic است و با هر callable ای کار می‌کند،
    نه فقط HTTP. تشخیص retryable بودن خطا از طریق Exception type
    انجام می‌شود (نه HTTP status code مستقیم).

    Usage:
        policy = RetryPolicy(max_retries=3)
        executor = RetryExecutor(policy)
        result = executor.execute(lambda: client.get("/api/data"))
    """

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._policy = policy or RetryPolicy.from_config()

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def execute(self, func: Callable[[], T]) -> T:
        """
        اجرای func با retry logic (Sync/blocking).

        Args:
            func: callable بدون آرگومان که نتیجه را برمی‌گرداند.

        Returns:
            خروجی func (نوع T).

        Raises:
            آخرین Exception پس از exhaust شدن تمام retryها.
        """
        from app.services.geo.clients.exceptions import (
            ProviderConnectionError,
            ProviderTimeoutError,
            ProviderServerError,
            ProviderRateLimitError,
        )

        last_exception: Exception | None = None
        total_attempts = self._policy.max_retries + 1  # initial + retries

        for attempt in range(total_attempts):
            try:
                return func()
            except ProviderRateLimitError as e:
                last_exception = e
                if attempt == self._policy.max_retries:
                    break
                wait = self._calc_wait(attempt, hint=e.retry_after)
                logger.warning(
                    "Rate-limited. Retrying in %.1fs (attempt %d/%d).",
                    wait,
                    attempt + 1,
                    total_attempts,
                )
                time.sleep(wait)
            except (ProviderConnectionError, ProviderTimeoutError) as e:
                last_exception = e
                if attempt == self._policy.max_retries:
                    break
                wait = self._calc_wait(attempt)
                logger.warning(
                    "Transient error (%s). Retrying in %.1fs (attempt %d/%d).",
                    type(e).__name__,
                    wait,
                    attempt + 1,
                    total_attempts,
                )
                time.sleep(wait)
            except ProviderServerError as e:
                last_exception = e
                if e.status_code in self._policy.retryable_statuses and attempt < self._policy.max_retries:
                    wait = self._calc_wait(attempt)
                    logger.warning(
                        "Server error %s (retryable). Retrying in %.1fs (attempt %d/%d).",
                        e.status_code,
                        wait,
                        attempt + 1,
                        total_attempts,
                    )
                    time.sleep(wait)
                else:
                    raise  # non-retryable server error → propagate
            except Exception as e:
                # Unknown / non-retryable → propagate immediately
                logger.error(
                    "Non-retryable error (%s). Aborting.",
                    type(e).__name__,
                )
                raise

        # Exhausted all retries
        assert last_exception is not None  # silenced mypy
        logger.error(
            "All %d attempts exhausted. Last error: %s",
            total_attempts,
            last_exception,
        )
        raise last_exception

    # ═══════════════════════════════════════════════════════
    # Private: Backoff Calculation
    # ═══════════════════════════════════════════════════════

    def _calc_wait(self, attempt: int, *, hint: float | None = None) -> float:
        """
        محاسبه wait time بر اساس backoff strategy.

        Args:
            attempt: شماره retry فعلی (0-based).
            hint: زمان پیشنهادی از Provider (مثلاً Retry-After header).

        Returns:
            زمان انتظار به ثانیه.
        """
        # Provider hint اولویت دارد (با clamp)
        if hint is not None and hint > 0:
            return min(hint, self._policy.max_backoff_seconds)

        strategy = self._policy.backoff_strategy

        if strategy == BackoffStrategy.EXPONENTIAL:
            wait = self._policy.backoff_base_seconds * (
                self._policy.backoff_multiplier ** attempt
            )
        elif strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            base = self._policy.backoff_base_seconds * (
                self._policy.backoff_multiplier ** attempt
            )
            jitter = base * self._policy.jitter_factor * random.random()
            wait = base + jitter
        elif strategy == BackoffStrategy.LINEAR:
            wait = self._policy.backoff_base_seconds * (attempt + 1)
        else:
            wait = self._policy.backoff_base_seconds

        return min(wait, self._policy.max_backoff_seconds)
