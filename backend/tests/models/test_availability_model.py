"""Model and database-constraint tests for `Availability`.

These tests go through the SQLAlchemy model directly (not the API), so
they exercise exactly what PostgreSQL itself enforces via the
`ck_availability_day_of_week` and `ck_availability_time_range`
CHECK constraints defined in `app/models/availability.py`.

Overlap prevention between blocks is an *application-level* rule enforced
in `app/api/availability.py` (`_has_overlap`), not a database constraint -
those tests live in `tests/api/test_availability_api.py`. At the model/DB
layer, overlapping (and even identical) blocks are legal, and that's
covered explicitly below.
"""

import time as clock
from datetime import time

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.availability import Availability


def _make(db_session, **overrides):
    defaults = {
        "day_of_week": 0,
        "start_time": time(9, 0),
        "end_time": time(17, 0),
    }
    defaults.update(overrides)
    availability = Availability(**defaults)
    db_session.add(availability)
    db_session.commit()
    return availability


class TestValidDayOfWeek:
    def test_day_of_week_zero_is_valid(self, db_session):
        availability = _make(db_session, day_of_week=0)
        assert availability.id is not None

    def test_day_of_week_six_is_valid(self, db_session):
        availability = _make(db_session, day_of_week=6)
        assert availability.id is not None

    @pytest.mark.parametrize("day", [1, 2, 3, 4, 5])
    def test_day_of_week_middle_values_are_valid(self, db_session, day):
        availability = _make(db_session, day_of_week=day)
        assert availability.day_of_week == day


class TestInvalidDayOfWeek:
    def test_day_of_week_below_zero_is_rejected_by_the_database(self, db_session):
        db_session.add(Availability(day_of_week=-1, start_time=time(9, 0), end_time=time(17, 0)))

        with pytest.raises(IntegrityError, match="ck_availability_day_of_week"):
            db_session.commit()

        db_session.rollback()

    def test_day_of_week_above_six_is_rejected_by_the_database(self, db_session):
        db_session.add(Availability(day_of_week=7, start_time=time(9, 0), end_time=time(17, 0)))

        with pytest.raises(IntegrityError, match="ck_availability_day_of_week"):
            db_session.commit()

        db_session.rollback()


class TestTimeRangeConstraint:
    def test_start_before_end_is_valid(self, db_session):
        availability = _make(db_session, start_time=time(8, 0), end_time=time(9, 0))
        assert availability.id is not None

    def test_start_equal_to_end_is_rejected_by_the_database(self, db_session):
        db_session.add(
            Availability(day_of_week=0, start_time=time(9, 0), end_time=time(9, 0))
        )

        with pytest.raises(IntegrityError, match="ck_availability_time_range"):
            db_session.commit()

        db_session.rollback()

    def test_start_after_end_is_rejected_by_the_database(self, db_session):
        db_session.add(
            Availability(day_of_week=0, start_time=time(17, 0), end_time=time(9, 0))
        )

        with pytest.raises(IntegrityError, match="ck_availability_time_range"):
            db_session.commit()

        db_session.rollback()


class TestMultipleBlocksAllowed:
    def test_multiple_non_overlapping_blocks_on_the_same_day_are_allowed(self, db_session):
        _make(db_session, day_of_week=1, start_time=time(9, 0), end_time=time(12, 0))
        _make(db_session, day_of_week=1, start_time=time(13, 0), end_time=time(17, 0))

        rows = db_session.query(Availability).filter_by(day_of_week=1).all()
        assert len(rows) == 2

    def test_overlapping_blocks_on_the_same_day_are_allowed_at_the_database_level(
        self, db_session
    ):
        """No DB constraint prevents overlap; that rule lives in the API
        layer only. This documents the current, intentional split."""
        _make(db_session, day_of_week=2, start_time=time(9, 0), end_time=time(17, 0))
        _make(db_session, day_of_week=2, start_time=time(10, 0), end_time=time(11, 0))

        rows = db_session.query(Availability).filter_by(day_of_week=2).all()
        assert len(rows) == 2

    def test_identical_blocks_on_different_days_are_allowed(self, db_session):
        _make(db_session, day_of_week=0, start_time=time(9, 0), end_time=time(17, 0))
        _make(db_session, day_of_week=3, start_time=time(9, 0), end_time=time(17, 0))

        rows = db_session.query(Availability).all()
        assert len(rows) == 2


class TestPersistence:
    def test_valid_record_can_be_inserted_committed_and_retrieved(self, db_session):
        created = _make(
            db_session, day_of_week=4, start_time=time(10, 30), end_time=time(15, 45)
        )

        db_session.expire_all()
        fetched = db_session.get(Availability, created.id)

        assert fetched is not None
        assert fetched.day_of_week == 4
        assert fetched.start_time == time(10, 30)
        assert fetched.end_time == time(15, 45)


class TestTimestamps:
    def test_created_at_and_updated_at_are_set_on_insert(self, db_session):
        availability = _make(db_session)

        assert availability.created_at is not None
        assert availability.updated_at is not None

    def test_updated_at_advances_on_update(self, engine):
        """`updated_at` uses `onupdate=func.now()`, and Postgres's `now()`
        returns the *transaction* start time, not wall-clock time - so two
        updates inside a single transaction (like the shared, rolled-back
        `db_session` fixture used elsewhere in this file) would always see
        an identical value, regardless of `onupdate` working correctly.
        This test instead uses two separate, real, top-level transactions,
        the same as two separate API requests would produce, and cleans up
        its own row directly since it intentionally bypasses the
        rollback-based `db_session` fixture.
        """
        session_factory = sessionmaker(bind=engine)

        session = session_factory()
        availability = Availability(day_of_week=5, start_time=time(9, 0), end_time=time(10, 0))
        session.add(availability)
        session.commit()
        original_updated_at = availability.updated_at
        availability_id = availability.id
        session.close()

        clock.sleep(0.01)

        session = session_factory()
        try:
            availability = session.get(Availability, availability_id)
            availability.end_time = time(11, 0)
            session.commit()

            assert availability.updated_at > original_updated_at
        finally:
            session.delete(availability)
            session.commit()
            session.close()
