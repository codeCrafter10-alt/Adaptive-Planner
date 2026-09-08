"""Model and database-constraint tests for `AvailabilityException`.

Like `test_availability_model.py`, these go through the SQLAlchemy model
directly to exercise the `ck_availability_exceptions_time_pair`,
`ck_availability_exceptions_time_range`, and `uq_availability_exceptions_date`
constraints defined in `app/models/availability_exception.py`.
"""

from datetime import date, time

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.availability_exception import AvailabilityException


def _make(db_session, **overrides):
    defaults = {
        "date": date(2026, 12, 25),
        "is_available": False,
        "start_time": None,
        "end_time": None,
        "reason": "Holiday",
    }
    defaults.update(overrides)
    exception = AvailabilityException(**defaults)
    db_session.add(exception)
    db_session.commit()
    return exception


class TestTimePairConstraint:
    def test_unavailable_day_with_no_times_is_valid(self, db_session):
        exception = _make(db_session, is_available=False, start_time=None, end_time=None)
        assert exception.id is not None

    def test_available_day_with_both_times_is_valid(self, db_session):
        exception = _make(
            db_session,
            is_available=True,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        assert exception.id is not None

    def test_only_start_time_set_is_rejected_by_the_database(self, db_session):
        db_session.add(
            AvailabilityException(
                date=date(2026, 12, 26),
                is_available=True,
                start_time=time(9, 0),
                end_time=None,
            )
        )

        with pytest.raises(IntegrityError, match="ck_availability_exceptions_time_pair"):
            db_session.commit()

        db_session.rollback()

    def test_only_end_time_set_is_rejected_by_the_database(self, db_session):
        db_session.add(
            AvailabilityException(
                date=date(2026, 12, 26),
                is_available=True,
                start_time=None,
                end_time=time(12, 0),
            )
        )

        with pytest.raises(IntegrityError, match="ck_availability_exceptions_time_pair"):
            db_session.commit()

        db_session.rollback()


class TestTimeRangeConstraint:
    def test_start_before_end_is_valid(self, db_session):
        exception = _make(
            db_session,
            is_available=True,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )
        assert exception.id is not None

    def test_start_equal_to_end_is_rejected_by_the_database(self, db_session):
        db_session.add(
            AvailabilityException(
                date=date(2026, 12, 26),
                is_available=True,
                start_time=time(9, 0),
                end_time=time(9, 0),
            )
        )

        with pytest.raises(IntegrityError, match="ck_availability_exceptions_time_range"):
            db_session.commit()

        db_session.rollback()

    def test_start_after_end_is_rejected_by_the_database(self, db_session):
        db_session.add(
            AvailabilityException(
                date=date(2026, 12, 26),
                is_available=True,
                start_time=time(12, 0),
                end_time=time(9, 0),
            )
        )

        with pytest.raises(IntegrityError, match="ck_availability_exceptions_time_range"):
            db_session.commit()

        db_session.rollback()

    def test_null_times_do_not_trigger_the_time_range_constraint(self, db_session):
        """A CHECK constraint comparing two NULLs (`NULL < NULL`) evaluates
        to NULL, which Postgres treats as satisfied - this documents that
        an unavailable day with no times is unaffected by the range check."""
        exception = _make(db_session, is_available=False, start_time=None, end_time=None)
        assert exception.start_time is None
        assert exception.end_time is None


class TestUniqueDateConstraint:
    def test_two_exceptions_on_the_same_date_are_rejected_by_the_database(self, db_session):
        _make(db_session, date=date(2026, 11, 1))

        db_session.add(
            AvailabilityException(date=date(2026, 11, 1), is_available=False)
        )

        with pytest.raises(IntegrityError, match="uq_availability_exceptions_date"):
            db_session.commit()

        db_session.rollback()

    def test_exceptions_on_different_dates_are_allowed(self, db_session):
        _make(db_session, date=date(2026, 11, 1))
        _make(db_session, date=date(2026, 11, 2))

        rows = db_session.query(AvailabilityException).all()
        assert len(rows) == 2


class TestPersistence:
    def test_valid_record_can_be_inserted_committed_and_retrieved(self, db_session):
        created = _make(
            db_session,
            date=date(2026, 10, 15),
            is_available=True,
            start_time=time(13, 0),
            end_time=time(16, 0),
            reason="Half day",
        )

        db_session.expire_all()
        fetched = db_session.get(AvailabilityException, created.id)

        assert fetched is not None
        assert fetched.date == date(2026, 10, 15)
        assert fetched.is_available is True
        assert fetched.start_time == time(13, 0)
        assert fetched.end_time == time(16, 0)
        assert fetched.reason == "Half day"

    def test_reason_is_optional(self, db_session):
        exception = _make(db_session, reason=None)
        assert exception.reason is None


class TestTimestamps:
    def test_created_at_and_updated_at_are_set_on_insert(self, db_session):
        exception = _make(db_session)

        assert exception.created_at is not None
        assert exception.updated_at is not None
