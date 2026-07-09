from app.models.request import Request
from app.repositories.request_repository import RequestRepository


class RequestService:

    def __init__(self, db):
        self.repository = RequestRepository(db)

    def create_request(
        self,
        company_name,
        contact_name,
        mobile,
        email,
        industry,
        goal,
    ):
        request = Request(
            company_name=company_name,
            contact_name=contact_name,
            mobile=mobile,
            email=email,
            industry=industry,
            goal=goal,
            status="SUBMITTED",
        )

        return self.repository.create(request)

    def get_all_requests(self):
        return self.repository.get_all()

    def add_request_file(
        self,
        request_id,
        file_name,
        file_path,
        file_type,
        content_type=None,
        file_size=0,
    ):
        return self.repository.create_request_file(
            request_id=request_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            content_type=content_type,
            file_size=file_size,
        )