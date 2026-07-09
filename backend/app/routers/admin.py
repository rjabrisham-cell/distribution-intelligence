from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.request_service import RequestService

router = APIRouter(prefix="/admin")

templates = Jinja2Templates(directory="app/templates")


@router.get("/requests", response_class=HTMLResponse)
async def requests_page(

    request: Request,

    db: Session = Depends(get_db)

):

    service = RequestService(db)

    requests = service.get_all_requests()

    return templates.TemplateResponse(

        request=request,

        name="admin_requests.html",

        context={

            "requests": requests

        }

    )