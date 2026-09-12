from fastapi import HTTPException
from app.models import Project
from app.repositories.demo_access_repository import DemoAccessRepository, now
from app.services.entitlement_service import EntitlementService


class TrialService:
    def __init__(self, db):
        self.db = db
        self.repo = DemoAccessRepository(db)
        self.entitlement = EntitlementService(db)

    def mark_processing(self, account_id, project_id, batch_id):
        from sqlalchemy.orm import Session
        # Status is durable while the existing synchronous operation runs. The
        # request already holds the account advisory lock across service commits.
        with Session(self.db.get_bind().engine) as status_db:
            project = DemoAccessRepository(status_db).owned_project(account_id, project_id)
            project.trial_state = "PROCESSING"
            status_db.commit()
        self.db.info["trial_processing_started"] = (account_id, project_id, batch_id)

    @staticmethod
    def mark_failed(engine, started):
        from sqlalchemy.orm import Session
        account_id, project_id, batch_id = started
        with Session(engine) as status_db:
            repo = DemoAccessRepository(status_db)
            if not repo.lock("trial:" + str(account_id)):
                return
            project = repo.owned_project(account_id, project_id)
            if (project and project.active_store_batch_id == batch_id
                    and project.trial_state == "PROCESSING"):
                project.trial_state = "FAILED"
                status_db.commit()

    def create(self, account_id, name, description=None, code=None):
        if not self.repo.verified_account(account_id) or not self.repo.lock("trial:" + str(account_id)):
            raise HTTPException(409, "ورود معتبر نیست یا عملیات دیگری در حال اجراست.")
        # One reusable draft: refresh/retry cannot create another project.
        existing = [p for p in self.repo.projects(account_id) if p.trial_consumed_at is None]
        if existing:
            return existing[0]
        self.entitlement.assert_trial(account_id)
        if not name.strip() or len(name) > 255:
            raise HTTPException(400, "نام پروژه معتبر وارد کنید.")
        company = self.repo.company(account_id)
        project = Project(company_id=company.id, trial_owner_id=account_id, name=name.strip(),
                          description=description, code=code, trial_state="DRAFT")
        self.db.add(project)
        self.db.commit()
        return project

    def acknowledge(self, account_id, project_id, receipt):
        project = self.repo.owned_project(account_id, project_id)
        if not project:
            raise HTTPException(404)
        if project.trial_consumed_at:
            return
        self.entitlement.assert_trial(account_id, project_id)
        if (project.trial_state != "COMPLETED" or not project.active_store_batch_id
                or project.trial_result_batch_id != project.active_store_batch_id):
            raise HTTPException(409, "نتیجه آماده مشاهده نیست.")
        from app.services.trial_receipt import verify
        if not verify(receipt, account_id, project_id, project.active_store_batch_id):
            raise HTTPException(403, "ابتدا صفحه نتیجه را مشاهده کنید.")
        project.trial_consumed_at = now()
        self.db.commit()
