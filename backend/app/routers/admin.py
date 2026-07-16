from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.services.request_service import RequestService


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# -------------------------------------------------------
# Requests Management
# -------------------------------------------------------

@router.get(
    "/requests",
    response_class=HTMLResponse,
)
async def requests_page(
    request: Request,
    db: Session = Depends(get_db),
):

    service = RequestService(db)

    requests = service.get_all_requests()

    return templates.TemplateResponse(
        request,
        "admin_requests.html",
        {
            "requests": requests,
        },
    )


# -------------------------------------------------------
# Dashboard
# -------------------------------------------------------

@router.get(
    "",
    response_class=HTMLResponse,
)
async def admin_dashboard(
    request: Request,
):

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {},
    )