from datetime import datetime, timezone, timedelta
from hashlib import sha256
from sqlalchemy import select, text
from app.models import Account, Company, Project, File, ImportBatch
from app.models.demo_access import DemoChallenge, DemoSession, DemoRateEvent


def digest(value):
    return sha256(value.encode()).hexdigest()


def now():
    return datetime.now(timezone.utc)


class DemoAccessRepository:
    def __init__(self, db):
        self.db = db

    def lock(self, key):
        # Held by the enclosing request transaction even if a legacy service commits.
        number = int(digest(key)[:15], 16)
        return self.db.execute(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": number}).scalar()

    def rate(self, key, limit, seconds):
        key_hash = digest(key)
        if not self.lock(key):
            return False
        count = self.db.query(DemoRateEvent).filter(DemoRateEvent.key_hash == key_hash, DemoRateEvent.created_at > now() - timedelta(seconds=seconds)).count()
        if count >= limit:
            return False
        self.db.add(DemoRateEvent(key_hash=key_hash))
        self.db.flush()
        return True

    def challenge(self, reference):
        return self.db.scalar(select(DemoChallenge).where(DemoChallenge.reference == reference).with_for_update())

    def latest_challenge(self, mobile):
        return self.db.scalar(select(DemoChallenge).where(DemoChallenge.mobile == mobile).order_by(DemoChallenge.id.desc()).limit(1))

    def session(self, token):
        return self.db.scalar(select(DemoSession).where(DemoSession.token_hash == digest(token), DemoSession.expires_at > now(), DemoSession.revoked_at.is_(None)))

    def verified_account(self, account_id):
        return self.db.scalar(select(Account).where(Account.id == account_id, Account.mobile_verified_at.is_not(None)))

    def verify_account(self, mobile):
        account = self.db.scalar(select(Account).where(Account.mobile == mobile))
        if account is None:
            account = Account(mobile=mobile)
            self.db.add(account)
            self.db.flush()
        account.mobile_verified_at = now()
        return account

    def owned_project(self, account_id, project_id):
        return self.db.scalar(select(Project).where(Project.id == project_id, Project.trial_owner_id == account_id))

    def projects(self, account_id):
        return self.db.scalars(select(Project).where(Project.trial_owner_id == account_id).order_by(Project.created_at.desc())).all()

    def file_project_id(self, file_id):
        return self.db.scalar(select(File.entity_id).where(File.id == file_id, File.entity_type == "PROJECT", File.removed_at.is_(None)))

    def batch_project_id(self, batch_id):
        return self.db.scalar(select(File.entity_id).join(ImportBatch, ImportBatch.file_id == File.id).where(ImportBatch.id == batch_id, File.entity_type == "PROJECT", File.removed_at.is_(None)))

    def company(self, account_id):
        company = self.db.scalar(select(Company).where(Company.account_id == account_id))
        if company is None:
            company = Company(account_id=account_id, name="شبکه پخش آزمایشی")
            self.db.add(company)
            self.db.flush()
        return company
