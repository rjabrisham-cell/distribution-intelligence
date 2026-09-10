# فایل: app/schemas/project.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectStatus(str, Enum):
    """انواع وضعیت پروژه (مطابق مدل SQLAlchemy)"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    CLOSED = "CLOSED"


# ==========================================================
# Base Schemas
# ==========================================================

class ProjectBase(BaseModel):
    """Schema پایه برای عملیات پروژه"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="نام پروژه (حداکثر ۲۵۵ کاراکتر)"
    )
    code: Optional[str] = Field(
        None,
        max_length=100,
        description="کد پروژه (اختیاری، حداکثر ۱۰۰ کاراکتر)"
    )
    description: Optional[str] = Field(
        None,
        description="توضیحات پروژه (اختیاری)"
    )
    status: Optional[ProjectStatus] = Field(
        ProjectStatus.DRAFT,
        description="وضعیت پروژه"
    )
    is_active: Optional[bool] = Field(
        True,
        description="وضعیت فعال بودن پروژه"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """اعتبارسنجی نام پروژه"""
        if not v.strip():
            raise ValueError("نام پروژه نمی‌تواند خالی باشد")
        return v.strip()


# ==========================================================
# Create/Update Schemas
# ==========================================================

class ProjectCreate(ProjectBase):
    """Schema برای ایجاد پروژه جدید"""
    company_id: int = Field(
        ...,
        gt=0,
        description="شناسه شرکت مالک پروژه"
    )
    
    # حذف فیلدهای غیرضروری برای ایجاد
    model_config = ConfigDict(extra="forbid")


class ProjectUpdate(BaseModel):
    """Schema برای به‌روزرسانی پروژه"""
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="نام پروژه"
    )
    code: Optional[str] = Field(
        None,
        max_length=100,
        description="کد پروژه"
    )
    description: Optional[str] = Field(
        None,
        description="توضیحات پروژه"
    )
    status: Optional[ProjectStatus] = Field(
        None,
        description="وضعیت پروژه"
    )
    is_active: Optional[bool] = Field(
        None,
        description="وضعیت فعال بودن"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name_update(cls, v: Optional[str]) -> Optional[str]:
        """اعتبارسنجی نام در به‌روزرسانی"""
        if v is not None and not v.strip():
            raise ValueError("نام پروژه نمی‌تواند خالی باشد")
        return v.strip() if v else v


# ==========================================================
# Response Schemas
# ==========================================================

class ProjectCompanyStoreRef(BaseModel):
    """ارجاع به رابطه Project-CompanyStore"""
    id: int
    company_store_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(ProjectBase):
    """Schema برای پاسخ خواندن پروژه"""
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    
    # فیلدهای محاسبه شده از روابط (برای جلوگیری از circular import)
    company_stores_count: Optional[int] = Field(
        0,
        description="تعداد فروشگاه‌های مرتبط"
    )
    vehicles_count: Optional[int] = Field(
        0,
        description="تعداد وسایل نقلیه تخصیص یافته"
    )
    drivers_count: Optional[int] = Field(
        0,
        description="تعداد رانندگان تخصیص یافته"
    )
    requests_count: Optional[int] = Field(
        0,
        description="تعداد درخواست‌ها"
    )
    orders_count: Optional[int] = Field(
        0,
        description="تعداد سفارشات"
    )
    
    # خصوصیات محاسبه شده (مطابق مدل SQLAlchemy)
    @property
    def is_draft(self) -> bool:
        return self.status == ProjectStatus.DRAFT
    
    @property
    def is_operational(self) -> bool:
        return self.is_active and self.status == ProjectStatus.ACTIVE
    
    @property
    def is_closed(self) -> bool:
        return self.status == ProjectStatus.CLOSED
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class ProjectDetailResponse(ProjectResponse):
    """Schema برای جزئیات کامل پروژه"""
    # برای جلوگیری از circular import، روابط به صورت خلاصه
    company_name: Optional[str] = Field(
        None,
        description="نام شرکت مالک"
    )


class ProjectListResponse(BaseModel):
    """Schema برای لیست‌کردن پروژه‌ها با صفحه‌بندی"""
    items: List[ProjectResponse]
    total: int
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    total_pages: int


# ==========================================================
# Service/Repository Compatibility
# ==========================================================

class ProjectSearchParams(BaseModel):
    """پارامترهای جستجو برای Repository"""
    company_id: Optional[int] = None
    status: Optional[ProjectStatus] = None
    is_active: Optional[bool] = None
    name_contains: Optional[str] = None
    code_contains: Optional[str] = None


class ProjectCreateParams(BaseModel):
    """پارامترهای ایجاد پروژه مطابق Service"""
    mobile: str = Field(..., description="شماره موبایل")
    company_name: str = Field(..., description="نام شرکت")
    project_name: str = Field(..., description="نام پروژه")
    description: Optional[str] = None
