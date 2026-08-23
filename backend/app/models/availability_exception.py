from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Integer,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AvailabilityException(Base):
    """Date-specific override for the recurring weekly availability schedule."""

    __tablename__ = "availability_exceptions"
    __table_args__ = (
        CheckConstraint(
            "(start_time IS NULL AND end_time IS NULL) OR (start_time IS NOT NULL AND end_time IS NOT NULL)",
            name="ck_availability_exceptions_time_pair",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_availability_exceptions_time_range",
        ),
        UniqueConstraint("date", name="uq_availability_exceptions_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
