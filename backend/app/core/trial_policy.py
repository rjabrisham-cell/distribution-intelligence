"""Single source of limits for the public trial; no provider credentials here."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrialPolicy:
    access_code_capacity: int = int(os.getenv("DEMO_CODE_MAX_MOBILES", "3"))
    access_mobile_attempts: int = 5
    access_ip_attempts: int = 30
    access_cooldown_seconds: int = 900
    quota: int = int(os.getenv("TRIAL_PROJECT_QUOTA", "1"))
    file_bytes: int = 2 * 1024 * 1024
    rows: int = 1000
    min_columns: int = 5
    max_columns: int = 13
    extra_columns: int = 5
    expanded_bytes: int = 20 * 1024 * 1024
    zip_entries: int = 100
    zip_ratio: int = 200
    otp_seconds: int = 120
    resend_seconds: int = 60
    otp_attempts: int = 5
    session_seconds: int = 8 * 3600
    otp_mobile_limit: int = 5
    otp_ip_limit: int = 10
    otp_window_seconds: int = 3600
    verify_ip_limit: int = 30
    verify_window_seconds: int = 600
    write_limit: int = 20
    write_window_seconds: int = 600


policy = TrialPolicy()
