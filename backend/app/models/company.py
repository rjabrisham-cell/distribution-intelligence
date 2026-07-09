from sqlalchemy import Column, String

from app.models.base import BaseModel


class Company(BaseModel):
    __tablename__ = "companies"

    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, index=True, nullable=True)