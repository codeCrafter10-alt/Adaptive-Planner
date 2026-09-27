from datetime import datetime, timezone

import pytest

from app.scheduling.engine import schedule
from app.scheduling.models import SchedulingInput


def test_schedule_is_explicitly_unimplemented():
    start = datetime(2026, 9, 25, 9, 0, tzinfo=timezone.utc)
    end = datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc)
    scheduling_input = SchedulingInput(
        tasks=[],
        availability=[],
        existing_schedule=[],
        scheduling_start=start,
        scheduling_end=end,
    )

    with pytest.raises(NotImplementedError, match="not implemented"):
        schedule(scheduling_input)
