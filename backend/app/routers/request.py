from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.services.file_service import FileService
from app.services.request_service import RequestService

router = APIRouter(
    prefix="/request",
    tags=["Request"],
)


# -------------------------------------------------------
# Request Form
# -------------------------------------------------------

@router.get(
    "",
    response_class=HTMLResponse,
)
async def request_page(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="request.html",
        context={},
    )


# -------------------------------------------------------
# Create Request
# -------------------------------------------------------

@router.post(
    "",
    response_class=HTMLResponse,
)
async def submit_request(
    request: Request,
    company_name: str = Form(...),
    contact_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(default=""),
    industry: str = Form(default=""),
    goal: str = Form(default=""),
    orders_file: UploadFile = File(default=None),
    fleet_file: UploadFile = File(default=None),
    drivers_file: UploadFile = File(default=None),
    gps_file: UploadFile = File(default=None),
    other_files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    # ۱. ایجاد درخواست
    request_service = RequestService(db)
    new_request = request_service.create_request(
        company_name=company_name,
        contact_name=contact_name,
        mobile=mobile,
        email=email,
        industry=industry,
        goal=goal,
    )

    # ۲. آپلود فایل‌ها با FileService.upload() (همان API فعلی)
    async def upload_if_exists(
        upload_file: UploadFile,
        category: str,
    ):
        if upload_file is None or upload_file.filename == "":
            return
        await FileService.upload(
            db=db,
            entity_type="REQUEST",
            entity_id=new_request.id,
            category=category,
            upload_file=upload_file,
        )

    await upload_if_exists(orders_file, "orders")
    await upload_if_exists(fleet_file, "fleet")
    await upload_if_exists(drivers_file, "drivers")
    await upload_if_exists(gps_file, "gps")

    if other_files:
        for file in other_files:
            await upload_if_exists(file, "other")

    # ۳. بازگشت پاسخ
    return templates.TemplateResponse(
        request=request,
        name="request.html",
        context={
            "success": True,
            "request_id": new_request.id,
        },
    )
