# Distribution Intelligence Project

### شرح پروژه
این پروژه یک سامانه هوشمند برای مدیریت توزیع و تحلیل داده‌های جغرافیایی (Persian Geo Address) است که با معماری DDD و استفاده از FastAPI (Python) توسعه یافته و به صورت Containerized (Docker) مدیریت می‌شود.

---

### ۱. راه‌اندازی و اجرا (Docker)
برای بالا آوردن پروژه در محیط داکر، از دستورات زیر در مسیر پروژه استفاده کنید:

*   **ساخت و اجرای کانتینرها (Background):**
    ```bash
    docker-compose up -d --build
    ```
*   **مشاهده لاگ‌های زنده:**
    ```bash
    docker-compose logs -f
    ```
*   **توقف و حذف کانتینرها:**
    ```bash
    docker-compose down
    ```

---

### ۲. اجرای محلی برای تست و دیباگ (بدون داکر)
در صورتی که نیاز به اجرای مستقیم پایتون برای دیباگ سریع دارید:

*   **فعال‌سازی محیط مجازی:** `venv\Scripts\activate`
*   **اجرا با لاگ دقیق:**
    ```bash
    uvicorn app.main:app --reload --log-level debug
    ```

---

### ۳. مدیریت کد (Git)
دستورات پرکاربرد برای همگام‌سازی با مخزن GitHub:

*   **دریافت آخرین تغییرات از سرور:**
    ```bash
    git pull origin main
    ```
*   **ثبت و ارسال تغییرات جدید:**
    ```bash
    git add .
    git commit -m "توضیح تغییرات"
    git push origin main
    ```
*   **مشاهده وضعیت فایل‌ها:** `git status`

---

### ۴. دستورات کنترلی و نگهداری
*   **پاک‌سازی فایل‌های اضافی پایتون:** `del /s /q *.pyc`
*   **بررسی صحت اتصال Remote:** `git remote -v`
*   **ایجاد نسخه پشتیبان (Tag):**
    ```bash
    git tag -a v0.x -m "Description"
    git push origin v0.x
    ```

---
**مسیر اصلی پروژه:** `D:\distribution-intelligence`  
**تاریخ آخرین به‌روزرسانی:** ۱۸ تیر ۱۴۰۵
```