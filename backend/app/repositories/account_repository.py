from typing import Optional

from sqlalchemy.orm import Session

from app.models.account import Account


class AccountRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_mobile(self, mobile: str) -> Optional[Account]:
        return self.db.query(Account).filter(
            Account.mobile == mobile
        ).first()

    def create(self, mobile: str) -> Account:
        account = Account(mobile=mobile)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account
