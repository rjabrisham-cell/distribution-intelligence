"""
Request Model — Enterprise Data Model v3.1

Request = Project-level operational/request record.

Architecture
------------

Company
    │
    │ 1:M
    ▼
Project
    │
    │ 1:M
    ▼
Request
    │
    │ 1:M
    ▼
RequestFile

Rules
-----

- Every Request belongs to exactly one Project.
- A Project may have zero, one, or many Requests.
- A Request does not directly own a Company.
- Company ownership is inherited through Project.
- RequestFile records belong to a Request.
- Deleting a Project deletes its Requests.
- Deleting a Request deletes its RequestFiles.

Important
---------

Project.requests
    ↕
Request.project

Request.files
    ↕
RequestFile.request
"""

from __future__ import annotations

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.models.base import BaseModel


class Request(BaseModel):
    """
    Project-level request.

    A Request belongs to exactly one Project.

    The Company associated with the Request is determined through:

        Request
            ↓
        Project
            ↓
        Company

    Therefore, Request does not need a direct company_id.
    """

    __tablename__ = "requests"

    # ==========================================================
    # Identity
    # ==========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    # ==========================================================
    # Project Ownership
    # ==========================================================

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="Project مالک این Request",
    )

    # ==========================================================
    # Company Information
    # ==========================================================
    #
    # These fields represent the information submitted with
    # the original request.
    #
    # They are NOT the ownership relationship.
    #
    # Ownership is:
    #
    # Request -> Project -> Company
    #

    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="نام شرکت ثبت‌شده در درخواست",
    )

    contact_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="نام شخص تماس",
    )

    mobile: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        comment="شماره موبایل شخص تماس",
    )

    email: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="ایمیل شخص تماس",
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="صنعت یا حوزه فعالیت شرکت",
    )

    goal: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="هدف یا نیاز ثبت‌شده در درخواست",
    )

    # ==========================================================
    # Workflow
    # ==========================================================

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SUBMITTED",
        index=True,
        comment=(
            "Request workflow status. "
            "Example: SUBMITTED | REVIEWING | APPROVED | "
            "REJECTED | COMPLETED"
        ),
    )

    # ==========================================================
    # Relationships
    # ==========================================================

    # ----------------------------------------------------------
    # Project
    # ----------------------------------------------------------
    #
    # Project.requests <-> Request.project
    #
    # Every Request belongs to exactly one Project.
    #

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="requests",
        lazy="selectin",
    )

    # ----------------------------------------------------------
    # Files
    # ----------------------------------------------------------
    #
    # Request.files <-> RequestFile.request
    #
    # Deleting a Request deletes its RequestFiles.
    #

    files: Mapped[list["RequestFile"]] = relationship(
        "RequestFile",
        back_populates="request",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    # ==========================================================
    # Representation
    # ==========================================================

    def __repr__(self) -> str:
        return (
            f"<Request("
            f"id={self.id}, "
            f"project_id={self.project_id}, "
            f"company='{self.company_name}', "
            f"status='{self.status}'"
            f")>"
        )