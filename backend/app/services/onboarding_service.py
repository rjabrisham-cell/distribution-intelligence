# app/services/onboarding_service.py

from sqlalchemy.orm import Session

from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository


class OnboardingService:
    def __init__(self, db: Session):
        self.account_repository = AccountRepository(db)
        self.company_repository = CompanyRepository(db)

    def get_or_create_account_and_company(self, mobile: str, company_name: str):
        account = self.account_repository.get_by_mobile(mobile)

        if not account:
            account = self.account_repository.create(mobile)

        company = self.company_repository.get_by_account(account.id)

        if not company:
            company = self.company_repository.create(
                account_id=account.id,
                name=company_name,
            )

        return account, company
