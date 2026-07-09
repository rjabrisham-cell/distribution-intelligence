from sqlalchemy.orm import Session
from app.models.request import Request
from app.models.request_file import RequestFile
import uuid


class RequestRepository:

    def __init__(self, db: Session):
        self.db = db

    # -----------------------
    # Request
    # -----------------------

    def create(self, request: Request):
        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        return request

    def get_all(self):
        return (
            self.db.query(Request)
            .order_by(Request.id.desc())
            .all()
        )

    def get_by_id(self, request_id: int):
        return (
            self.db.query(Request)
            .filter(Request.id == request_id)
            .first()
        )

    # -----------------------
    # Request Files
    # -----------------------

    def create_request_file(
        self,
        request_id: int,
        file_name: str,
        file_path: str,
        file_type: str,
        content_type: str | None = None,
        file_size: int = 0,
    ):
        request_file = RequestFile(
            request_id=request_id,
            file_type=file_type,
            original_name=file_name,
            stored_name=f"{uuid.uuid4()}_{file_name}",
            file_path=file_path,
            content_type=content_type,
            file_size=file_size,
        )

        self.db.add(request_file)
        self.db.commit()
        self.db.refresh(request_file)

        return request_file