# app/services/entitlement_service.py

from sqlalchemy.orm import Session

from app.repositories.project_repository import ProjectRepository


class EntitlementService:
    def __init__(self, db: Session, max_projects_free: int = 2):
        self.db = db
        self.project_repository = ProjectRepository(db)
        self.max_projects_free = max_projects_free

    def assert_can_create_project(self, company_id: int) -> None:
        count = self.project_repository.count_by_company(company_id)
        if count >= self.max_projects_free:
            raise ValueError("Free plan limit reached.")

    def assert_trial(self, account_id: int, project_id: int | None = None):
        from fastapi import HTTPException
        from app.core.trial_policy import policy
        from app.repositories.demo_access_repository import DemoAccessRepository
        repo = DemoAccessRepository(self.db)
        if not repo.verified_account(account_id) or not repo.lock("trial:" + str(account_id)):
            raise HTTPException(409, "عملیات دیگری در حال اجراست یا ورود معتبر نیست.")
        projects = repo.projects(account_id)
        if sum(p.trial_consumed_at is not None for p in projects) >= policy.quota:
            raise HTTPException(403, "سهمیه ارزیابی رایگان شما مصرف شده است.")
        active = [p for p in projects if p.trial_consumed_at is None]
        if any(p.id != project_id for p in active):
            raise HTTPException(409, "ابتدا پروژه آزمایشی فعلی خود را تکمیل کنید.")
