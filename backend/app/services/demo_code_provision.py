"""Receive hashes only over stdin; refuse to provision an existing code set."""
import json
import re
import sys
from sqlalchemy.orm import Session
from app.core.database import engine
from app.core.trial_policy import policy
from app.models.demo_access import DemoAccessCode
from app.repositories.demo_access_repository import DemoAccessRepository


def provision(hashes):
    if len(hashes) != 1000 or len(set(hashes)) != 1000 or any(not re.fullmatch('[a-f0-9]{128}', h) for h in hashes):
        raise ValueError('Invalid provision manifest')
    with Session(engine) as db:
        if not DemoAccessRepository(db).lock('demo-code-provision') or db.query(DemoAccessCode).count():
            raise ValueError('Code set already exists or provisioning is busy')
        db.add_all([DemoAccessCode(code_hash=h, is_active=True, max_mobile_uses=policy.access_code_capacity) for h in hashes])
        db.commit()


if __name__ == '__main__':
    try:
        provision(json.load(sys.stdin))
        print('1000 access code hashes registered')
    except Exception:
        # Database diagnostics must not expose hashes or configuration.
        print('Provisioning stopped; preserve the code file and investigate safely', file=sys.stderr)
        sys.exit(1)
