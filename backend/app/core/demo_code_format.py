"""Shared host/backend contract; no settings, secrets or application dependencies."""
import hashlib

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def normalize_access_code(value):
    return str(value).strip().strip("\ufeff\u200e\u200f").strip().upper()


def access_hash(code):
    return hashlib.scrypt(normalize_access_code(code).encode(), salt=b"DIP-demo-access-v1", n=16384, r=8, p=1).hex()
