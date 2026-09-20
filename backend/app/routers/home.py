from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        request,
        "index.html",
        {"public_demo": True},
    )


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse(request, "contact.html", {"public_demo": True})


@router.get("/demo/sample", response_class=HTMLResponse)
def demo_sample(request: Request):
    if not settings.DEMO_SAMPLE_PROJECT_ID:
        raise HTTPException(503, "نمونه عمومی هنوز تعیین نشده است.")
    from app.services.demo_sample_service import prepared_sample_context
    context = prepared_sample_context(settings.DEMO_SAMPLE_PROJECT_ID)
    return templates.TemplateResponse(request=request, name="projects/readiness.html", context=context)


@router.get("/demo/trial")
def demo_trial():
    return RedirectResponse("/demo/login", status_code=303)
