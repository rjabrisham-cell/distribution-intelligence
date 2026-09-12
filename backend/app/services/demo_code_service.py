"""Temporary invitation access. This does not verify ownership of a mobile."""
import hashlib
import re
import secrets
from datetime import timedelta
from fastapi import HTTPException
from app.core.trial_policy import policy
from app.models.demo_access import DemoSession
from app.repositories.demo_access_repository import DemoAccessRepository, digest, now
from app.services.demo_auth_service import normalize_mobile

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ERROR = "اطلاعات ورود معتبر نیست یا امکان استفاده از این کد وجود ندارد."


def access_hash(code):
    return hashlib.scrypt(code.encode(), salt=b"DIP-demo-access-v1", n=16384, r=8, p=1).hex()


class DemoCodeService:
    def __init__(self, db):
        self.db, self.repo = db, DemoAccessRepository(db)

    def login(self, mobile, code, peer):
        try:
            normalized = normalize_mobile(mobile)
        except HTTPException:
            normalized = None
        # Both counters persist on rejected requests in the HTTP transaction.
        ip_ok = self.repo.rate("access-ip:" + peer, policy.access_ip_attempts, policy.access_cooldown_seconds)
        mobile_ok = self.repo.rate("access-mobile:" + (normalized or mobile[:64]), policy.access_mobile_attempts, policy.access_cooldown_seconds)
        if not ip_ok or not mobile_ok:
            raise HTTPException(429, "تلاش‌های ورود زیاد است؛ ۱۵ دقیقه بعد دوباره تلاش کنید.")
        value = code.strip().upper()
        if not normalized or not re.fullmatch("[" + ALPHABET + "]{8}", value):
            raise HTTPException(400, ERROR)
        if not self.repo.lock("otp:" + normalized):
            raise HTTPException(429, "کمی بعد دوباره تلاش کنید.")
        record = self.repo.access_code(access_hash(value))
        if not record or not record.is_active or record.disabled_at is not None:
            raise HTTPException(400, ERROR)
        account = self.repo.redeem_code(record, normalized)
        if account is None:
            raise HTTPException(400, ERROR)
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.db.add(DemoSession(account_id=account.id, token_hash=digest(token), csrf_hash=digest(csrf), expires_at=now()+timedelta(seconds=policy.session_seconds)))
        destination = "/projects/" if self.repo.projects(account.id) else "/projects/new"
        self.db.commit()
        return token, csrf, destination
