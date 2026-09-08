"""API tests for `/availability`.

Schema-level validation (`day_of_week` range, `start_time < end_time`) is
enforced by `app/schemas/availability.py` and is covered here only at the
boundary (a couple of representative cases); the exhaustive constraint
matrix lives in `tests/models/test_availability_model.py` against the
database directly.

The overlap-prevention business rule (`_has_overlap` in
`app/api/availability.py`) has no database-level equivalent - it only
exists at the API layer, so it's tested thoroughly here.
"""

from tests.helpers import availability_payload


class TestCreateAvailability:
    def test_create_returns_201(self, client):
        response = client.post("/availability", json=availability_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["day_of_week"] == 0
        assert body["start_time"] == "09:00:00"
        assert body["end_time"] == "17:00:00"

    def test_day_of_week_out_of_range_is_rejected(self, client):
        response = client.post("/availability", json=availability_payload(day_of_week=7))

        assert response.status_code == 422

    def test_negative_day_of_week_is_rejected(self, client):
        response = client.post("/availability", json=availability_payload(day_of_week=-1))

        assert response.status_code == 422

    def test_start_after_end_is_rejected(self, client):
        response = client.post(
            "/availability",
            json=availability_payload(start_time="17:00:00", end_time="09:00:00"),
        )

        assert response.status_code == 422

    def test_start_equal_to_end_is_rejected(self, client):
        response = client.post(
            "/availability",
            json=availability_payload(start_time="09:00:00", end_time="09:00:00"),
        )

        assert response.status_code == 422


class TestOverlapDetection:
    def test_overlapping_block_on_same_day_is_rejected(self, client):
        client.post(
            "/availability",
            json=availability_payload(day_of_week=0, start_time="09:00:00", end_time="17:00:00"),
        )

        response = client.post(
            "/availability",
            json=availability_payload(day_of_week=0, start_time="12:00:00", end_time="14:00:00"),
        )

        assert response.status_code == 409

    def test_identical_block_on_same_day_is_rejected(self, client):
        client.post("/availability", json=availability_payload(day_of_week=1))

        response = client.post("/availability", json=availability_payload(day_of_week=1))

        assert response.status_code == 409

    def test_non_overlapping_block_on_same_day_is_allowed(self, client):
        client.post(
            "/availability",
            json=availability_payload(day_of_week=1, start_time="09:00:00", end_time="12:00:00"),
        )

        response = client.post(
            "/availability",
            json=availability_payload(day_of_week=1, start_time="13:00:00", end_time="17:00:00"),
        )

        assert response.status_code == 201

    def test_back_to_back_blocks_are_not_treated_as_overlapping(self, client):
        """One block ending exactly when another starts should be allowed
        - the overlap check uses strict `<` on both sides."""
        client.post(
            "/availability",
            json=availability_payload(day_of_week=1, start_time="09:00:00", end_time="12:00:00"),
        )

        response = client.post(
            "/availability",
            json=availability_payload(day_of_week=1, start_time="12:00:00", end_time="15:00:00"),
        )

        assert response.status_code == 201

    def test_same_time_range_on_different_days_is_allowed(self, client):
        client.post(
            "/availability",
            json=availability_payload(day_of_week=0, start_time="09:00:00", end_time="17:00:00"),
        )

        response = client.post(
            "/availability",
            json=availability_payload(day_of_week=1, start_time="09:00:00", end_time="17:00:00"),
        )

        assert response.status_code == 201


class TestListAvailability:
    def test_list_orders_by_day_then_start_time(self, client):
        client.post(
            "/availability",
            json=availability_payload(day_of_week=1, start_time="13:00:00", end_time="17:00:00"),
        )
        client.post(
            "/availability",
            json=availability_payload(day_of_week=1, start_time="09:00:00", end_time="12:00:00"),
        )
        client.post(
            "/availability",
            json=availability_payload(day_of_week=0, start_time="09:00:00", end_time="17:00:00"),
        )

        response = client.get("/availability")

        assert response.status_code == 200
        ordering = [(row["day_of_week"], row["start_time"]) for row in response.json()]
        assert ordering == [
            (0, "09:00:00"),
            (1, "09:00:00"),
            (1, "13:00:00"),
        ]


class TestUpdateAvailability:
    def test_update_existing_block_succeeds(self, client):
        created = client.post("/availability", json=availability_payload()).json()

        response = client.put(
            f"/availability/{created['id']}",
            json=availability_payload(start_time="10:00:00", end_time="18:00:00"),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["start_time"] == "10:00:00"
        assert body["end_time"] == "18:00:00"

    def test_update_can_keep_its_own_time_unchanged(self, client):
        """Updating a block without changing its time range must not be
        rejected as overlapping itself (`exclude_id`)."""
        created = client.post("/availability", json=availability_payload()).json()

        response = client.put(f"/availability/{created['id']}", json=availability_payload())

        assert response.status_code == 200

    def test_update_that_would_overlap_another_block_is_rejected(self, client):
        client.post(
            "/availability",
            json=availability_payload(day_of_week=0, start_time="09:00:00", end_time="12:00:00"),
        )
        other = client.post(
            "/availability",
            json=availability_payload(day_of_week=0, start_time="13:00:00", end_time="17:00:00"),
        ).json()

        response = client.put(
            f"/availability/{other['id']}",
            json=availability_payload(day_of_week=0, start_time="10:00:00", end_time="14:00:00"),
        )

        assert response.status_code == 409

    def test_update_missing_block_returns_404(self, client):
        response = client.put("/availability/999999", json=availability_payload())

        assert response.status_code == 404


class TestDeleteAvailability:
    def test_delete_existing_block_removes_it(self, client):
        created = client.post("/availability", json=availability_payload()).json()

        delete_response = client.delete(f"/availability/{created['id']}")
        list_response = client.get("/availability")

        assert delete_response.status_code == 204
        assert list_response.json() == []

    def test_delete_missing_block_returns_404(self, client):
        response = client.delete("/availability/999999")

        assert response.status_code == 404
