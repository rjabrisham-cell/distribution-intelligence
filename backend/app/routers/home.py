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
        {},
    )


@router.get("/demo/sample", response_class=HTMLResponse)
def demo_sample(request: Request, db: Session = Depends(get_db)):
    from app.routers.project import readiness_step
    if not settings.DEMO_SAMPLE_PROJECT_ID:
        raise HTTPException(503, "نمونه عمومی هنوز تعیین نشده است.")
    with db.no_autoflush:
        response = readiness_step(request, settings.DEMO_SAMPLE_PROJECT_ID, db)
    if not response.context.get("batch") or response.context.get("audit_error"):
        raise HTTPException(503, "نمونه تحلیل‌شده فعلاً در دسترس نیست.")
    context = dict(response.context, demo_sample=True)
    return templates.TemplateResponse(request=request, name="projects/readiness.html", context=context)


@router.get("/demo/trial")
def demo_trial():
    # Temporary existing onboarding route; OTP gate replaces this in milestone 4.
    return RedirectResponse("/projects/new", status_code=303)
