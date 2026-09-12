"""Provider boundary is independent of DIP accounts, sessions and entitlements."""
import hashlib
import hmac
import os
import re
import secrets
from datetime import timedelta
from fastapi import HTTPException
from app.core.config import settings
from app.core.trial_policy import policy
from app.models.demo_access import DemoChallenge, DemoSession
from app.repositories.demo_access_repository import DemoAccessRepository, digest, now


def normalize_mobile(value):
    value = str(value).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    value = re.sub(r"[\s()-]", "", value)
    if value.startswith("0098"):
        value = "0" + value[4:]
    elif value.startswith("+98"):
        value = "0" + value[3:]
    elif value.startswith("98"):
        value = "0" + value[2:]
    if not re.fullmatch(r"09\d{9}", value):
        raise HTTPException(400, "شماره موبایل معتبر وارد کنید.")
    return value


def code_hash(code, salt):
    return hashlib.scrypt(code.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()


class LocalOtpProvider:
    """Explicit opt-in + development environment + loopback. No SMS or logging.

    DEMO_LOCAL_OTP_HASH is salt:scrypt_hex, never a plaintext OTP.
    Future remote providers implement issue(reference, mobile) and verify(proof, code).
    """
    def __init__(self, peer):
        if (settings.APP_ENV != "development" or os.getenv("DEMO_OTP_PROVIDER") != "local"
                or peer not in {"127.0.0.1", "::1", "testclient"}):
            raise HTTPException(503, "ورود آزمایشی هنوز فعال نشده است.")
        self.proof = os.getenv("DEMO_LOCAL_OTP_HASH", "")
        if not re.fullmatch(r"[a-f0-9]{32}:[a-f0-9]{128}", self.proof):
            raise HTTPException(503, "ورود آزمایشی هنوز فعال نشده است.")

    def issue(self, reference, mobile):
        return self.proof

    def verify(self, proof, code):
        if not re.fullmatch(r"\d{6}", code):
            return False
        salt, expected = proof.split(":", 1)
        return hmac.compare_digest(code_hash(code, salt), expected)


class DemoAuthService:
    def __init__(self, db, provider):
        self.db, self.repo, self.provider = db, DemoAccessRepository(db), provider

    def issue(self, mobile, peer):
        mobile = normalize_mobile(mobile)
        if not self.repo.lock("otp:" + mobile):
            raise HTTPException(429, "کمی بعد دوباره تلاش کنید.")
        previous = self.repo.latest_challenge(mobile)
        if previous and (now() - previous.created_at).total_seconds() < policy.resend_seconds:
            raise HTTPException(429, "برای درخواست دوباره حداقل ۶۰ ثانیه صبر کنید.")
        if not self.repo.rate("otp-mobile:" + mobile, policy.otp_mobile_limit, policy.otp_window_seconds) or not self.repo.rate("otp-ip:" + peer, policy.otp_ip_limit, policy.otp_window_seconds):
            raise HTTPException(429, "کمی بعد دوباره تلاش کنید.")
        if previous:
            previous.used_at = now()
        reference = secrets.token_hex(32)
        challenge = DemoChallenge(reference=reference, mobile=mobile, ip_hash=digest(peer),
                                  proof_hash=self.provider.issue(reference, mobile), attempts=0,
                                  expires_at=now() + timedelta(seconds=policy.otp_seconds))
        self.db.add(challenge)
        self.db.commit()
        return reference

    def verify(self, reference, code, peer):
        if not self.repo.rate("verify-ip:" + peer, policy.verify_ip_limit, policy.verify_window_seconds):
            raise HTTPException(429, "کمی بعد دوباره تلاش کنید.")
        challenge = self.repo.challenge(reference)
        if (not challenge or challenge.used_at or challenge.expires_at <= now()
                or challenge.attempts >= policy.otp_attempts or challenge.ip_hash != digest(peer)):
            self.db.commit()
            raise HTTPException(400, "کد نامعتبر یا منقضی شده است.")
        challenge.attempts += 1
        if not self.provider.verify(challenge.proof_hash, code):
            self.db.commit()  # Failed attempts must survive a rejected request.
            raise HTTPException(400, "کد نامعتبر یا منقضی شده است.")
        if not self.repo.lock("otp:" + challenge.mobile):
            raise HTTPException(429, "کمی بعد دوباره تلاش کنید.")
        challenge.used_at = now()
        account = self.repo.verify_account(challenge.mobile)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.db.add(DemoSession(account_id=account.id, token_hash=digest(token), csrf_hash=digest(csrf),
                                expires_at=now() + timedelta(seconds=policy.session_seconds)))
        self.db.commit()
        return token, csrf
