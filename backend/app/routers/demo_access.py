import secrets
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from app.core.database import get_db
from app.core.templates import templates
from app.core.config import settings
from app.core.trial_policy import policy
from app.services.demo_auth_service import DemoAuthService, LocalOtpProvider
from app.services.trial_service import TrialService
from app.services.demo_code_service import DemoCodeService

router = APIRouter(prefix="/demo", tags=["Demo access"])


def cookie(response, name, value, httponly=True, seconds=None):
    response.set_cookie(name, value, httponly=httponly, secure=settings.APP_ENV != "development",
                        samesite="strict", max_age=seconds or policy.session_seconds, path="/")


@router.get("/login")
def login(request: Request):
    csrf = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(request=request, name="demo_login.html", context={"public_demo": True, "csrf_token": csrf})
    cookie(response, "dip_login_csrf", csrf, seconds=600)
    return response


@router.post("/otp/request")
def issue(request: Request, mobile: str = Form(...), db=Depends(get_db)):
    peer = request.client.host
    reference = DemoAuthService(db, LocalOtpProvider(peer)).issue(mobile, peer)
    response = templates.TemplateResponse(request=request, name="demo_login.html", context={
        "public_demo": True, "challenge": reference, "csrf_token": request.cookies["dip_login_csrf"]})
    return response


@router.post("/access")
def access(request: Request, mobile: str = Form(...), code: str = Form(...), db=Depends(get_db)):
    token, csrf, destination = DemoCodeService(db).login(mobile, code, request.client.host)
    response = RedirectResponse(destination, status_code=303)
    cookie(response, "dip_session", token)
    cookie(response, "dip_csrf", csrf, httponly=False)
    return response


@router.post("/otp/verify")
def verify(request: Request, reference: str = Form(...), code: str = Form(...), db=Depends(get_db)):
    peer = request.client.host
    token, csrf = DemoAuthService(db, LocalOtpProvider(peer)).verify(reference, code, peer)
    response = RedirectResponse("/projects/new", status_code=303)
    cookie(response, "dip_session", token)
    cookie(response, "dip_csrf", csrf, httponly=False)
    return response


@router.post("/logout")
def logout(request: Request, db=Depends(get_db)):
    from app.repositories.demo_access_repository import now
    request.state.demo_session.revoked_at = now()
    db.commit()
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("dip_session")
    response.delete_cookie("dip_csrf")
    return response


@router.post("/result/{project_id}/ack")
def acknowledge(request: Request, project_id: int, receipt: str = Form(...), db=Depends(get_db)):
    TrialService(db).acknowledge(request.state.demo_account_id, project_id, receipt)
    return {"status": "ok"}
