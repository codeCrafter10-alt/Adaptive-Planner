"""Small request-payload builders shared across API tests.

These intentionally return plain dicts (not model instances) so each test
can override just the field(s) it cares about while keeping the rest at a
known-valid baseline.
"""

from __future__ import annotations

from typing import Any


def task_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": "Write project report",
        "description": "Quarterly summary for stakeholders",
        "estimated_duration_minutes": 60,
        "due_date": "2026-12-01T17:00:00Z",
        "priority": "medium",
    }
    payload.update(overrides)
    return payload


def availability_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "day_of_week": 0,
        "start_time": "09:00:00",
        "end_time": "17:00:00",
    }
    payload.update(overrides)
    return payload


def availability_exception_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "date": "2026-12-25",
        "is_available": False,
        "start_time": None,
        "end_time": None,
        "reason": "Holiday",
    }
    payload.update(overrides)
    return payload
