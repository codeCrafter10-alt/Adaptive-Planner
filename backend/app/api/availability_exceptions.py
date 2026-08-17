from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.availability_exception import AvailabilityException
from app.schemas.availability_exception import (
    AvailabilityExceptionBase,
    AvailabilityExceptionCreate,
    AvailabilityExceptionResponse,
    AvailabilityExceptionUpdate,
)


router = APIRouter(
    prefix="/availability/exceptions",
    tags=["availability"],
)


def _get_availability_exception_or_404(
    db: Session,
    exception_id: int,
) -> AvailabilityException:
    availability_exception = db.get(AvailabilityException, exception_id)
    if availability_exception is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability exception not found.",
        )
    return availability_exception


def _has_date_conflict(
    db: Session,
    exception_date: date,
    exclude_id: int | None = None,
) -> bool:
    query = select(AvailabilityException).where(
        AvailabilityException.date == exception_date,
    )

    if exclude_id is not None:
        query = query.where(AvailabilityException.id != exclude_id)

    return db.scalars(query).first() is not None


@router.get(
    "",
    response_model=list[AvailabilityExceptionResponse],
)
def get_availability_exceptions(
    db: Session = Depends(get_db),
):
    query = select(AvailabilityException).order_by(
        AvailabilityException.date,
        AvailabilityException.id,
    )

    return db.scalars(query).all()


@router.post(
    "",
    response_model=AvailabilityExceptionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability_exception(
    availability_exception_in: AvailabilityExceptionCreate,
    db: Session = Depends(get_db),
):
    if _has_date_conflict(db, availability_exception_in.date):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability exception for this date already exists.",
        )

    availability_exception = AvailabilityException(
        date=availability_exception_in.date,
        is_available=availability_exception_in.is_available,
        start_time=availability_exception_in.start_time,
        end_time=availability_exception_in.end_time,
        reason=availability_exception_in.reason,
    )

    db.add(availability_exception)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability exception for this date already exists.",
        )

    db.refresh(availability_exception)
    return availability_exception


@router.put(
    "/{exception_id}",
    response_model=AvailabilityExceptionResponse,
)
def update_availability_exception(
    exception_id: int,
    availability_exception_in: AvailabilityExceptionUpdate,
    db: Session = Depends(get_db),
):
    availability_exception = _get_availability_exception_or_404(db, exception_id)
    update_data = availability_exception_in.model_dump(exclude_unset=True)

    current_data = {
        "date": availability_exception.date,
        "is_available": availability_exception.is_available,
        "start_time": availability_exception.start_time,
        "end_time": availability_exception.end_time,
        "reason": availability_exception.reason,
    }
    merged_data = {**current_data, **update_data}

    try:
        AvailabilityExceptionBase.model_validate(merged_data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )

    if _has_date_conflict(db, merged_data["date"], exclude_id=exception_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability exception for this date already exists.",
        )

    for field, value in update_data.items():
        setattr(availability_exception, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability exception for this date already exists.",
        )

    db.refresh(availability_exception)
    return availability_exception


@router.delete(
    "/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_availability_exception(
    exception_id: int,
    db: Session = Depends(get_db),
):
    availability_exception = _get_availability_exception_or_404(db, exception_id)
    db.delete(availability_exception)
    db.commit()

    return None
