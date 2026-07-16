from typing import Optional

from sqlalchemy.orm import Session

from app.models.company import Company


class CompanyRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_account(self, account_id: int) -> Optional[Company]:
        return self.db.query(Company).filter(
            Company.account_id == account_id
        ).first()

    def create(self, account_id: int, name: str) -> Company:
        company = Company(account_id=account_id, name=name)
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company
