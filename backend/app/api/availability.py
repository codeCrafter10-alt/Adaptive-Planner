from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.availability import Availability

from datetime import time

from app.schemas.availability import (
    AvailabilityCreate,
    AvailabilityUpdate,
    AvailabilityResponse,
)


router = APIRouter(
    prefix="/availability",
    tags=["availability"],
)


def _has_overlap(
    db: Session,
    day_of_week: int,
    start_time: time,
    end_time: time,
    exclude_id: int | None = None,
) -> bool:
    """
    Check whether an availability block overlaps
    with an existing block on the same weekday.
    """

    query = select(Availability).where(
        Availability.day_of_week == day_of_week,
        Availability.start_time < end_time,
        start_time < Availability.end_time,
    )

    if exclude_id is not None:
        query = query.where(
            Availability.id != exclude_id
        )

    result = db.scalars(query).first()

    return result is not None


@router.get(
    "",
    response_model=list[AvailabilityResponse],
)
def get_availability(
    db: Session = Depends(get_db),
):
    query = (
        select(Availability)
        .order_by(
            Availability.day_of_week,
            Availability.start_time,
        )
    )

    return db.scalars(query).all()


@router.post(
    "",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    availability_data: AvailabilityCreate,
    db: Session = Depends(get_db),
):
    if _has_overlap(
        db,
        availability_data.day_of_week,
        availability_data.start_time,
        availability_data.end_time,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability blocks cannot overlap.",
        )

    availability = Availability(
        day_of_week=availability_data.day_of_week,
        start_time=availability_data.start_time,
        end_time=availability_data.end_time,
    )

    db.add(availability)
    db.commit()
    db.refresh(availability)

    return availability


@router.put(
    "/{availability_id}",
    response_model=AvailabilityResponse,
)
def update_availability(
    availability_id: int,
    availability_data: AvailabilityUpdate,
    db: Session = Depends(get_db),
):
    availability = db.get(
        Availability,
        availability_id,
    )

    if availability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability block not found.",
        )

    if _has_overlap(
        db,
        availability_data.day_of_week,
        availability_data.start_time,
        availability_data.end_time,
        exclude_id=availability_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability blocks cannot overlap.",
        )

    availability.day_of_week = availability_data.day_of_week
    availability.start_time = availability_data.start_time
    availability.end_time = availability_data.end_time

    db.commit()
    db.refresh(availability)

    return availability


@router.delete(
    "/{availability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_availability(
    availability_id: int,
    db: Session = Depends(get_db),
):
    availability = db.get(
        Availability,
        availability_id,
    )

    if availability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability block not found.",
        )

    db.delete(availability)
    db.commit()

    return None
