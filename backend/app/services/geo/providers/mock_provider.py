"""
mock_provider.py — Mock Geo Provider for Testing
=================================================
Contract v1.0 (Frozen) — کاملاً Sync

Provider ساختگی برای تست‌های واحد و یکپارچگی.
کاملاً Configurable و بدون هیچ وابستگی به Async/Network.
"""

from __future__ import annotations

import hashlib
import logging
import random
import time
from typing import TYPE_CHECKING

from app.services.geo.geo_models import CONTRACT_VERSION
from app.services.geo.geo_provider import GeoProvider

if TYPE_CHECKING:
    from app.services.geo.geo_models import (
        GeoAddress,
        GeoCoordinate,
        AddressValidationResult,
        GeoProviderCapability,
        CapabilityLevel,
        CapabilityInfo,
    )

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Constants — داده‌های Mock (فارسی)
# ═══════════════════════════════════════════════════════════════════

MOCK_PROVINCES = ["تهران", "اصفهان", "خراسان رضوی", "فارس", "آذربایجان شرقی"]
MOCK_CITIES = ["تهران", "اصفهان", "مشهد", "شیراز", "تبریز"]
MOCK_REGIONS = ["منطقه ۱", "منطقه ۲", "منطقه ۳", "منطقه ۴", "منطقه ۵"]
MOCK_STREETS = ["ولیعصر", "شریعتی", "مطهری", "بهشتی", "انقلاب"]
MOCK_POSTAL_PREFIX = "123456"

MOCK_WARNING_MESSAGE = "این یک پاسخ mock است."

# Default Configuration
DEFAULT_DELAY = 0.05
DEFAULT_FAILURE_RATE = 0.2
DEFAULT_COUNT_MIN = 0
DEFAULT_COUNT_MAX = 5


class MockGeoProvider(GeoProvider):
    """
    Provider ساختگی که پاسخ‌های ساختگی (deterministic/random) برمی‌گرداند.

    استفاده در:
    - تست‌های واحد Ruleها
    - تست‌های یکپارچگی بدون نیاز به شبکه
    - توسعه frontend هنگام عدم دسترسی به سرویس واقعی

    Configuration Options:
        delay: تاخیر مصنوعی برای شبیه‌سازی شبکه (ثانیه)
        seed: عدد ثابت برای تولید پاسخ‌های تکراری (None برای تصادفی)
        failure_rate: احتمال شکست عملیات (0.0 تا 1.0)
        count_range: tuple(min, max) برای تعداد نتایج جستجو
    """

    def __init__(
        self,
        provider_name: str = "mock",
        *,
        delay: float = DEFAULT_DELAY,
        seed: int | None = None,
        failure_rate: float = DEFAULT_FAILURE_RATE,
        count_range: tuple[int, int] = (DEFAULT_COUNT_MIN, DEFAULT_COUNT_MAX),
    ):
        """
        Args:
            provider_name: نام یکتای Provider (مثلاً 'mock').
            delay: تاخیر مصنوعی به ثانیه (0 برای اجرای فوری).
            seed: عدد ثابت برای تولید نتایج تکراری (None برای تصادفی واقعی).
            failure_rate: احتمال شکست (0.0 تا 1.0).
            count_range: بازه تعداد نتایج برای عملیات‌های جستجو (min, max).
        """
        self._name = provider_name
        self._delay = delay
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._count_min, self._count_max = count_range

        if seed is not None:
            self._seed = seed
            self._rng = random.Random(seed)
        else:
            self._seed = random.randint(1, 10_000)
            self._rng = random.Random(self._seed)

    # ═══════════════════════════════════════════════════════════
    # شناسنامه (Identification)
    # ═══════════════════════════════════════════════════════════

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def provider_version(self) -> str:
        return "1.0.0"  # TODO Sprint 3: خواندن از Config

    @property
    def contract_version(self) -> str:
        return CONTRACT_VERSION

    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════

    def _should_fail(self) -> bool:
        """بررسی احتمال شکست عملیات."""
        return self._rng.random() < self._failure_rate

    def _safe_confidence(self, min_val: float, max_val: float) -> float:
        """
        تولید confidence در بازه امن [0.0, 1.0].

        ✅ اصلاح: کران پایین با max(min_val, 0.0) clamp می‌شود
        (قبلاً اشتباهاً min(max_val, 0.0) نوشته شده بود که min_val را ignore می‌کرد).
        """
        lo = max(min_val, 0.0)
        hi = min(max_val, 1.0)
        return self._rng.uniform(lo, hi)

    @staticmethod
    def _stable_hash(*args) -> int:
        """
        تولید hash پایدار با hashlib (برای deterministic بودن بین اجراها).
        برخلاف hash() داخلی Python که بین اجراها تغییر می‌کند.
        """
        raw = "|".join(str(a) for a in args).encode("utf-8")
        return int(hashlib.md5(raw).hexdigest(), 16) % (10**8)

    # ═══════════════════════════════════════════════════════════
    # Core Methods (Frozen v1.0)
    # ═══════════════════════════════════════════════════════════

    def validate_address(self, address: GeoAddress) -> AddressValidationResult:
        """
        اعتبارسنجی ساختگی آدرس (Sync).
        """
        time.sleep(self._delay)

        if self._should_fail():
            logger.warning(f"[{self._name}] validate_address: simulated failure")
            from app.services.geo.geo_models import AddressValidationResult as AVR
            return AVR(
                provider_name=self._name,
                province_exists=False,
                province_confidence=0.0,
                city_exists=False,
                city_confidence=0.0,
                region_exists=False,
                region_confidence=0.0,
                street_exists=False,
                street_confidence=0.0,
                postal_code_valid=False,
                postal_confidence=0.0,
                coordinate_valid=False,
                coordinate_confidence=0.0,
                warnings=(f"[{self._name}] خطای شبیه‌سازی شده",),
            )

        seed = self._stable_hash(address.province or "", address.city or "", address.street or "")
        rng = random.Random(self._seed + seed)
        from app.services.geo.geo_models import AddressValidationResult as AVR

        return AVR(
            provider_name=self._name,
            province_exists=rng.random() > 0.3,
            province_confidence=rng.uniform(0.7, 1.0),
            city_exists=rng.random() > 0.2,
            city_confidence=rng.uniform(0.8, 1.0),
            region_exists=rng.random() > 0.5,
            region_confidence=rng.uniform(0.6, 1.0),
            street_exists=rng.random() > 0.4,
            street_confidence=rng.uniform(0.7, 1.0),
            postal_code_valid=rng.random() > 0.6,
            postal_confidence=rng.uniform(0.9, 1.0),
            coordinate_valid=rng.random() > 0.1,
            coordinate_confidence=rng.uniform(0.95, 1.0),
            warnings=(MOCK_WARNING_MESSAGE,) if rng.random() > 0.8 else (),
        )

    def validate_coordinate(self, coordinate: GeoCoordinate) -> AddressValidationResult:
        """
        اعتبارسنجی ساختگی مختصات (Sync).
        """
        time.sleep(self._delay)

        if self._should_fail():
            from app.services.geo.geo_models import AddressValidationResult as AVR
            return AVR(
                provider_name=self._name,
                coordinate_valid=False,
                coordinate_confidence=0.0,
                warnings=(f"[{self._name}] خطای شبیه‌سازی شده",),
            )

        seed = self._stable_hash(coordinate.latitude, coordinate.longitude)
        rng = random.Random(self._seed + seed)
        from app.services.geo.geo_models import AddressValidationResult as AVR

        return AVR(
            provider_name=self._name,
            coordinate_valid=rng.random() > 0.15,
            coordinate_confidence=rng.uniform(0.9, 1.0),
        )

    def reverse_geocode(self, coordinate: GeoCoordinate) -> GeoAddress | None:
        """
        تبدیل ساختگی مختصات به آدرس (Sync).
        """
        time.sleep(self._delay)

        if self._should_fail():
            logger.warning(f"[{self._name}] reverse_geocode: simulated failure")
            return None

        seed = self._stable_hash(coordinate.latitude, coordinate.longitude)
        rng = random.Random(self._seed + seed)

        if rng.random() > 0.2:
            from app.services.geo.geo_models import GeoAddress
            return GeoAddress(
                province=rng.choice(MOCK_PROVINCES),
                city=rng.choice(MOCK_CITIES),
                region=rng.choice(MOCK_REGIONS),
                street=rng.choice(MOCK_STREETS),
                postal_code=f"{MOCK_POSTAL_PREFIX}{rng.randint(1000, 9999)}",
                coordinate=coordinate,
            )
        return None

    def health_check(self) -> bool:
        """
        بررسی سلامت ساختگی (Sync).
        """
        time.sleep(min(self._delay, 0.1))
        return not self._should_fail()

    def get_capabilities(self) -> GeoProviderCapability:
        """
        اعلام قابلیت‌های ساختگی.
        """
        from app.services.geo.geo_models import GeoProviderCapability, CapabilityInfo, CapabilityLevel

        return GeoProviderCapability(
            provider_name=self._name,
            address_validation=CapabilityInfo(
                level=CapabilityLevel.FULL,
                accuracy=0.97,
                coverage="iran",
                notes="پشتیبانی کامل ساختگی برای تست",
            ),
            reverse_geocoding=CapabilityInfo(
                level=CapabilityLevel.PARTIAL,
                accuracy=0.85,
                coverage="iran",
                notes="تبدیل مختصات به آدرس با پوشش محدود",
            ),
            coordinate_validation=CapabilityInfo(
                level=CapabilityLevel.FULL,
                accuracy=0.95,
                coverage="iran",
                notes="اعتبارسنجی مختصات داخل مرزهای ایران",
            ),
        )

    def get_supported_contract_version(self) -> str:
        """
        نسخه Contract پشتیبانی‌شده.
        """
        return CONTRACT_VERSION

    # ═══════════════════════════════════════════════════════════
    # Dunder Methods
    # ═══════════════════════════════════════════════════════════

    def __str__(self) -> str:
        return f"MockGeoProvider(name={self._name}, version={self.provider_version}, seed={self._seed})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self._name!r} seed={self._seed!r}>"
