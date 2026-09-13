"""Presentation only: preserve HTTP status and fail-closed access decisions."""
from fastapi.responses import JSONResponse
from app.core.templates import templates


def wants_html(request):
    path = request.url.path
    if ('api' in path.split('/') or path.startswith(('/geography/', '/demo/result/'))
            or path.rstrip('/').endswith('/api') or path == '/health'):
        return False
    return 'text/html' in request.headers.get('accept', '') or request.headers.get('sec-fetch-mode') == 'navigate'


def error_response(request, status, detail=None):
    if not wants_html(request):
        return JSONResponse({'detail': detail or 'سرویس موقتاً در دسترس نیست.'}, status_code=status)
    message = 'امکان دسترسی به این صفحه وجود ندارد.'
    if status == 401:
        message = 'برای ادامه، دوباره وارد حساب خود شوید.'
    elif status == 409:
        message = 'عملیات دیگری در حال اجراست. چند لحظه صبر کنید و سپس وضعیت را بررسی کنید.'
    elif status == 429:
        message = 'تعداد درخواست‌ها زیاد است. کمی صبر کنید و دوباره تلاش کنید.'
    elif status == 403 and detail and 'سهمیه' in str(detail):
        message = 'سهمیه ارزیابی رایگان این حساب مصرف شده است. برای ارزیابی بیشتر با تیم DIP تماس بگیرید.'
    elif status >= 500:
        message = 'سرویس موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.'
    elif status in (400, 413, 422):
        message = 'درخواست قابل پردازش نیست. اطلاعات فرم یا فایل را بررسی کنید.'
    project = getattr(request.state, 'demo_project', None)
    upload_error = (status in (400, 413, 422) and request.url.path.startswith('/uploads/project/')
                    and getattr(request.state, 'demo_account_id', None) is not None)
    destination = '/demo/login' if status == 401 else '/'
    if project is not None and status not in (401, 404):
        destination = f'/projects/{project.id}/readiness'
    elif getattr(request.state, 'demo_account_id', None):
        destination = '/projects/'
    return templates.TemplateResponse(request=request, name='web_error.html', context={
        'public_demo': True, 'error_status': status, 'error_message': message,
        'return_url': destination,
        'upload_error': upload_error,
    }, status_code=status)
