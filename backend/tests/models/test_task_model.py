"""Model-level tests for `Task`.

Unlike `Availability`, the `Task` model has no `CheckConstraint`s of its
own. `priority` uses a SQLAlchemy `Enum(..., native_enum=False,
create_constraint=True, validate_strings=True)`, which validates at the
Python/ORM layer (raising `LookupError` for an invalid value before it
ever reaches the database) - the tests below confirm this is where the
protection actually lives, since the database column itself is a plain
`VARCHAR(20)` with no CHECK constraint (see `test_invalid_priority...`).
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import StatementError

from app.models.task import Task, TaskPriority


def _make(db_session, **overrides):
    defaults = {
        "title": "Write project report",
        "description": "Quarterly summary",
        "estimated_duration_minutes": 60,
        "due_date": datetime(2026, 12, 1, 17, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    task = Task(**defaults)
    db_session.add(task)
    db_session.commit()
    return task


class TestDefaults:
    def test_priority_defaults_to_medium(self, db_session):
        task = _make(db_session)
        assert task.priority == TaskPriority.medium

    def test_completed_at_defaults_to_none(self, db_session):
        task = _make(db_session)
        assert task.completed_at is None

    def test_description_is_optional(self, db_session):
        task = _make(db_session, description=None)
        assert task.description is None


class TestPriorityValidation:
    def test_valid_priority_values_persist(self, db_session):
        for priority in TaskPriority:
            task = _make(db_session, title=f"Task {priority.value}", priority=priority)
            assert task.priority == priority

    def test_invalid_priority_is_rejected_before_reaching_the_database(self, db_session):
        """`validate_strings=True` makes SQLAlchemy's `Enum` type reject an
        unknown value at the Python layer. This is the only protection
        against an invalid priority - see the DB-level test below."""
        with pytest.raises((LookupError, StatementError)):
            _make(db_session, priority="urgent")

    def test_database_column_has_no_check_constraint_on_priority(self, db_session):
        """Documents current behavior: `priority` is stored as a plain
        VARCHAR(20) (native_enum=False), so nothing at the database layer
        itself would reject an invalid value inserted outside the ORM's
        Python-level enum validation, e.g. via raw SQL."""
        task = _make(db_session)

        db_session.execute(
            text("UPDATE tasks SET priority = 'not_a_real_priority' WHERE id = :id"),
            {"id": task.id},
        )
        db_session.commit()

        raw_value = db_session.execute(
            text("SELECT priority FROM tasks WHERE id = :id"), {"id": task.id}
        ).scalar_one()
        assert raw_value == "not_a_real_priority"


class TestPersistence:
    def test_valid_task_can_be_inserted_committed_and_retrieved(self, db_session):
        created = _make(db_session, title="Prepare invoices", estimated_duration_minutes=45)

        db_session.expire_all()
        fetched = db_session.get(Task, created.id)

        assert fetched is not None
        assert fetched.title == "Prepare invoices"
        assert fetched.estimated_duration_minutes == 45


class TestTimestamps:
    def test_created_at_and_updated_at_are_set_on_insert(self, db_session):
        task = _make(db_session)

        assert task.created_at is not None
        assert task.updated_at is not None
