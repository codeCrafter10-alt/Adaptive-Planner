"""API tests for `/availability/exceptions`.

Database-level constraint coverage (time-pair, time-range, unique date)
lives in `tests/models/test_availability_exception_model.py`. This file
covers schema validation and the application-level date-conflict rule
(`_has_date_conflict` in `app/api/availability_exceptions.py`), including
the merge-then-revalidate behavior used by the PUT endpoint.
"""

from tests.helpers import availability_exception_payload


class TestCreateAvailabilityException:
    def test_unavailable_day_returns_201(self, client):
        response = client.post(
            "/availability/exceptions", json=availability_exception_payload()
        )

        assert response.status_code == 201
        body = response.json()
        assert body["is_available"] is False
        assert body["start_time"] is None
        assert body["end_time"] is None

    def test_available_day_with_times_returns_201(self, client):
        response = client.post(
            "/availability/exceptions",
            json=availability_exception_payload(
                date="2026-12-27",
                is_available=True,
                start_time="09:00:00",
                end_time="13:00:00",
                reason="Half day",
            ),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["start_time"] == "09:00:00"
        assert body["end_time"] == "13:00:00"

    def test_available_day_without_times_is_rejected(self, client):
        response = client.post(
            "/availability/exceptions",
            json=availability_exception_payload(is_available=True),
        )

        assert response.status_code == 422

    def test_unavailable_day_with_times_is_rejected(self, client):
        response = client.post(
            "/availability/exceptions",
            json=availability_exception_payload(
                is_available=False, start_time="09:00:00", end_time="13:00:00"
            ),
        )

        assert response.status_code == 422

    def test_start_after_end_is_rejected(self, client):
        response = client.post(
            "/availability/exceptions",
            json=availability_exception_payload(
                is_available=True, start_time="13:00:00", end_time="09:00:00"
            ),
        )

        assert response.status_code == 422

    def test_duplicate_date_is_rejected(self, client):
        client.post("/availability/exceptions", json=availability_exception_payload())

        response = client.post(
            "/availability/exceptions", json=availability_exception_payload()
        )

        assert response.status_code == 409

    def test_reason_is_optional(self, client):
        payload = availability_exception_payload()
        del payload["reason"]

        response = client.post("/availability/exceptions", json=payload)

        assert response.status_code == 201
        assert response.json()["reason"] is None


class TestListAvailabilityExceptions:
    def test_list_orders_by_date(self, client):
        client.post(
            "/availability/exceptions",
            json=availability_exception_payload(date="2026-12-25"),
        )
        client.post(
            "/availability/exceptions",
            json=availability_exception_payload(date="2026-11-01"),
        )

        response = client.get("/availability/exceptions")

        assert response.status_code == 200
        dates = [row["date"] for row in response.json()]
        assert dates == ["2026-11-01", "2026-12-25"]


class TestUpdateAvailabilityException:
    def test_partial_update_of_reason_preserves_other_fields(self, client):
        created = client.post(
            "/availability/exceptions", json=availability_exception_payload()
        ).json()

        response = client.put(
            f"/availability/exceptions/{created['id']}", json={"reason": "Updated reason"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["reason"] == "Updated reason"
        assert body["date"] == created["date"]
        assert body["is_available"] == created["is_available"]

    def test_update_to_a_conflicting_date_is_rejected(self, client):
        client.post(
            "/availability/exceptions",
            json=availability_exception_payload(date="2026-12-25"),
        )
        movable = client.post(
            "/availability/exceptions",
            json=availability_exception_payload(date="2026-12-26"),
        ).json()

        response = client.put(
            f"/availability/exceptions/{movable['id']}", json={"date": "2026-12-25"}
        )

        assert response.status_code == 409

    def test_update_revalidates_the_merged_record(self, client):
        """Making a previously-unavailable day available without also
        supplying times must fail, even though neither field changed on
        its own - `PUT` re-validates the full merged record."""
        created = client.post(
            "/availability/exceptions", json=availability_exception_payload()
        ).json()
        assert created["is_available"] is False

        response = client.put(
            f"/availability/exceptions/{created['id']}", json={"is_available": True}
        )

        assert response.status_code == 422

    def test_update_missing_exception_returns_404(self, client):
        response = client.put(
            "/availability/exceptions/999999", json={"reason": "New reason"}
        )

        assert response.status_code == 404


class TestDeleteAvailabilityException:
    def test_delete_existing_exception_removes_it(self, client):
        created = client.post(
            "/availability/exceptions", json=availability_exception_payload()
        ).json()

        delete_response = client.delete(f"/availability/exceptions/{created['id']}")
        list_response = client.get("/availability/exceptions")

        assert delete_response.status_code == 204
        assert list_response.json() == []

    def test_delete_missing_exception_returns_404(self, client):
        response = client.delete("/availability/exceptions/999999")

        assert response.status_code == 404
