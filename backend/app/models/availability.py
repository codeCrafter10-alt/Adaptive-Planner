from datetime import datetime, time

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Availability(Base):
    """Recurring weekly availability blocks used by the scheduling engine."""

    __tablename__ = "availabilities"
    __table_args__ = (
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_availability_day_of_week",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_availability_time_range",
        ),
        Index("ix_availabilities_day_of_week", "day_of_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    end_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
