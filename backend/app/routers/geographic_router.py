"""
Geographic Data Router.

Read-only endpoints for the Intake geographic selection:

Province -> City

Region is intentionally not exposed here because the Intake
workflow no longer uses Region.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.city import City
from app.models.province import Province


router = APIRouter(
    prefix="/geography",
    tags=["Geographic Data"],
)


@router.get("/provinces")
def list_provinces(
    db: Session = Depends(get_db),
):
    """
    Return active provinces ordered by name.
    """

    provinces = (
        db.query(Province)
        .filter(
            Province.status == "enable",
        )
        .order_by(
            Province.name,
        )
        .all()
    )

    return [
        {
            "id": province.id,
            "name": province.name,
        }
        for province in provinces
    ]


@router.get("/cities/{province_id}")
def list_cities(
    province_id: int,
    db: Session = Depends(get_db),
):
    """
    Return active cities for a given province.
    """

    cities = (
        db.query(City)
        .filter(
            City.province_id == province_id,
            City.status == "enable",
        )
        .order_by(
            City.name,
        )
        .all()
    )

    return [
        {
            "id": city.id,
            "name": city.name,
            "province_id": city.province_id,
        }
        for city in cities
    ]