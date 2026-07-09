from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
    UploadFile,
    File,
)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pathlib import Path

from app.core.database import get_db
from app.services.request_service import RequestService

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


# ---------------------------
# GET PAGE
# ---------------------------
@router.get("/request", response_class=HTMLResponse)
async def request_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="request.html",
        context={}
    )


# ---------------------------
# POST REQUEST
# ---------------------------
@router.post("/request", response_class=HTMLResponse)
async def submit_request(
    request: Request,
    company_name: str = Form(...),
    contact_name: str = Form(...),
    mobile: str = Form(...),
    email: str = Form(""),
    industry: str = Form(""),
    goal: str = Form(""),

    orders_file: UploadFile = File(None),
    fleet_file: UploadFile = File(None),
    drivers_file: UploadFile = File(None),
    gps_file: UploadFile = File(None),
    other_files: list[UploadFile] = File(None),

    db: Session = Depends(get_db),
):
    service = RequestService(db)

    # create request
    new_request = service.create_request(
        company_name,
        contact_name,
        mobile,
        email,
        industry,
        goal,
    )

    request_id = new_request.id

    # upload folder
    base_path = Path(f"uploads/{request_id}")
    base_path.mkdir(parents=True, exist_ok=True)

    # ---------------------------
    # SAVE FILES
    # ---------------------------
    def save(upload_file: UploadFile, prefix: str):
        if not upload_file or not upload_file.filename:
            return

        content = upload_file.file.read()

        file_path = base_path / f"{request_id}_{prefix}_{upload_file.filename}"

        with open(file_path, "wb") as f:
            f.write(content)

        service.add_request_file(
            request_id=request_id,
            file_name=upload_file.filename,
            file_path=str(file_path),
            file_type=prefix,
            content_type=upload_file.content_type,
            file_size=len(content),
        )

    save(orders_file, "orders")
    save(fleet_file, "fleet")
    save(drivers_file, "drivers")
    save(gps_file, "gps")

    if other_files:
        for file in other_files:
            save(file, "other")

    return templates.TemplateResponse(
        request=request,
        name="request.html",
        context={
            "success": True,
            "request_id": request_id,
        }
    )