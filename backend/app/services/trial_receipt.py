"""Short-lived proof that a completed result page was rendered; GET stays read-only."""
import hashlib
import hmac
import os
import secrets
import time
from fastapi import HTTPException
from app.core.config import settings

_local_key = secrets.token_bytes(32)


def key():
    configured = os.getenv("DEMO_RECEIPT_SECRET", "")
    if len(configured) >= 32:
        return configured.encode()
    if settings.APP_ENV != "development":
        raise HTTPException(503, "پیکربندی ارزیابی آزمایشی کامل نیست.")
    return _local_key


def issue(account_id, project_id, batch_id):
    payload = f"{account_id}:{project_id}:{batch_id}:{int(time.time()) + 900}"
    return payload + ":" + hmac.new(key(), payload.encode(), hashlib.sha256).hexdigest()


def verify(receipt, account_id, project_id, batch_id):
    try:
        account, project, batch, expires, signature = receipt.split(":")
        payload = ":".join([account, project, batch, expires])
        return ((int(account), int(project), int(batch)) == (account_id, project_id, batch_id)
                and int(expires) >= int(time.time())
                and hmac.compare_digest(signature, hmac.new(key(), payload.encode(), hashlib.sha256).hexdigest()))
    except (ValueError, TypeError, AttributeError):
        return False
