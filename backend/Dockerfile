# backend/Dockerfile
FROM python:3.11-slim

# تنظیم دایرکتوری کاری در کانتینر
WORKDIR /app

# نصب ابزارهای مورد نیاز سیستم برای psycopg2 و غیره
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# کپی فایل نیازمندی‌ها و نصب کتابخانه‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل محتویات پوشه backend به داخل کانتینر
COPY . .

# پورت پیش‌فرض FastAPI
EXPOSE 8000

# دستور اجرای سرور با uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
