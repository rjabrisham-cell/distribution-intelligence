from sqlalchemy.orm import Session

from app.models.request_file import RequestFile


class RequestFileRepository:

    @staticmethod
    def create(db: Session, file: RequestFile) -> RequestFile:
        db.add(file)
        db.commit()
        db.refresh(file)
        return file