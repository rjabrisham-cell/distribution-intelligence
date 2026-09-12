import secrets
import re
import importlib.util
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from alembic.operations import Operations
from alembic.migration import MigrationContext
from fastapi import HTTPException
from app.services.audit.tests.test_demo_security import engine, db, client, identity
from app.models.demo_access import DemoAccessCode, DemoAccessCodeUsage
from app.models import Account
from app.services.demo_code_service import DemoCodeService, access_hash, ALPHABET


def seed(db, active=True):
    value = ''.join(secrets.choice(ALPHABET) for _ in range(8))
    record = DemoAccessCode(code_hash=access_hash(value), max_mobile_uses=3, is_active=active)
    db.add(record); db.commit()
    return value, record.id


def mobile(): return '09' + str(secrets.randbelow(10**9)).zfill(9)


def test_capacity_repeat_hash_and_no_sms_claim(db):
    value, rid = seed(db)
    numbers = [mobile() for _ in range(4)]
    service = DemoCodeService(db)
    for n in numbers[:3]: service.login(n, value, uuid4().hex)
    service.login(numbers[0], value, uuid4().hex)
    with pytest.raises(HTTPException) as e: service.login(numbers[3], value, uuid4().hex)
    assert e.value.status_code == 400
    assert db.query(DemoAccessCodeUsage).filter_by(access_code_id=rid).count() == 3
    assert db.get(DemoAccessCode, rid).code_hash != value
    account = db.scalar(select(Account).where(Account.mobile==numbers[0]))
    assert account.demo_access_granted_at and account.mobile_verified_at is None


def test_concurrent_capacity(engine, db):
    value, rid = seed(db)
    def redeem(_):
        with Session(engine) as session:
            try:
                DemoCodeService(session).login(mobile(), value, uuid4().hex)
                return True
            except HTTPException: return False
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert sum(pool.map(redeem, range(6))) == 3
    assert db.query(DemoAccessCodeUsage).filter_by(access_code_id=rid).count() == 3


def test_http_errors_rate_csrf_and_login(client, db, caplog):
    value, rid = seed(db)
    disabled, _ = seed(db, False)
    response = client.get('/demo/login')
    assert '/demo/access' in response.text and '/demo/otp/request' not in response.text
    csrf = re.search('name="csrf_token" value="([^"]+)"', response.text)[1]
    assert client.post('/demo/access', data={'mobile':mobile(),'code':value}).status_code == 403
    n = mobile()
    details=[]
    for number, code in [(n,'BAD'),(n,disabled),('invalid',value)]:
        result=client.post('/demo/access',data={'mobile':number,'code':code,'csrf_token':csrf})
        assert result.status_code==400
        details.append(result.json()['detail'])
    assert len(set(details))==1
    result=client.post('/demo/access',data={'mobile':n,'code':value,'csrf_token':csrf},follow_redirects=False)
    assert result.status_code==303 and 'dip_session' in client.cookies
    assert client.get('/projects/api/').json()==[]
    _, other, _, _ = identity(db)
    assert client.get('/projects/'+str(other.id)).status_code==404
    assert client.post('/projects/new',data={}).status_code==403
    for _ in range(6):
        result=client.post('/demo/access',data={'mobile':n,'code':'BAD','csrf_token':csrf})
    assert result.status_code==429
    assert value not in caplog.text and n not in caplog.text and access_hash(value) not in caplog.text


def test_migration_upgrade_downgrade(engine):
    schema='code_migration_'+uuid4().hex[:12]
    spec=importlib.util.spec_from_file_location('codes_migration','alembic/versions/20260913_010000_demo_codes.py')
    migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with engine.begin() as c:
        c=c.execution_options(schema_translate_map=None)
        c.execute(text('CREATE SCHEMA '+schema))
        c.execute(text('SET LOCAL search_path TO '+schema+', public'))
        c.execute(text('CREATE TABLE accounts (id integer PRIMARY KEY)'))
        c.execute(text('INSERT INTO accounts VALUES (1)'))
        with Operations.context(MigrationContext.configure(c)):
            migration.upgrade()
            assert c.execute(text('SELECT demo_access_granted_at FROM accounts')).scalar() is None
            migration.downgrade()
            assert c.execute(text('SELECT count(*) FROM accounts')).scalar()==1
            migration.upgrade()
