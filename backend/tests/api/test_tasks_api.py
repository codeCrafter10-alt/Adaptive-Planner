"""API tests for `/tasks`."""

from tests.helpers import task_payload


class TestCreateTask:
    def test_create_task_returns_201_with_full_representation(self, client):
        response = client.post("/tasks", json=task_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Write project report"
        assert body["priority"] == "medium"
        assert body["completed_at"] is None
        assert body["id"] is not None
        assert body["created_at"] is not None
        assert body["updated_at"] is not None

    def test_title_is_trimmed(self, client):
        response = client.post("/tasks", json=task_payload(title="  Buy milk  "))

        assert response.status_code == 201
        assert response.json()["title"] == "Buy milk"

    def test_blank_title_is_rejected(self, client):
        response = client.post("/tasks", json=task_payload(title="   "))

        assert response.status_code == 422

    def test_missing_title_is_rejected(self, client):
        payload = task_payload()
        del payload["title"]

        response = client.post("/tasks", json=payload)

        assert response.status_code == 422

    def test_non_positive_duration_is_rejected(self, client):
        response = client.post(
            "/tasks", json=task_payload(estimated_duration_minutes=0)
        )

        assert response.status_code == 422

    def test_negative_duration_is_rejected(self, client):
        response = client.post(
            "/tasks", json=task_payload(estimated_duration_minutes=-30)
        )

        assert response.status_code == 422

    def test_invalid_priority_is_rejected(self, client):
        response = client.post("/tasks", json=task_payload(priority="urgent"))

        assert response.status_code == 422

    def test_priority_defaults_to_medium_when_omitted(self, client):
        payload = task_payload()
        del payload["priority"]

        response = client.post("/tasks", json=payload)

        assert response.status_code == 201
        assert response.json()["priority"] == "medium"

    def test_description_is_optional(self, client):
        payload = task_payload()
        del payload["description"]

        response = client.post("/tasks", json=payload)

        assert response.status_code == 201
        assert response.json()["description"] is None


class TestListTasks:
    def test_list_is_empty_when_no_tasks_exist(self, client):
        response = client.get("/tasks")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_created_tasks_ordered_by_creation(self, client):
        client.post("/tasks", json=task_payload(title="First"))
        client.post("/tasks", json=task_payload(title="Second"))

        response = client.get("/tasks")

        assert response.status_code == 200
        titles = [task["title"] for task in response.json()]
        assert titles == ["First", "Second"]


class TestGetTask:
    def test_get_existing_task_returns_it(self, client):
        created = client.post("/tasks", json=task_payload()).json()

        response = client.get(f"/tasks/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_missing_task_returns_404(self, client):
        response = client.get("/tasks/999999")

        assert response.status_code == 404


class TestUpdateTask:
    def test_partial_update_only_changes_given_fields(self, client):
        created = client.post("/tasks", json=task_payload()).json()

        response = client.patch(f"/tasks/{created['id']}", json={"title": "New title"})

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "New title"
        assert body["estimated_duration_minutes"] == created["estimated_duration_minutes"]
        assert body["due_date"] == created["due_date"]

    def test_completed_true_sets_completed_at(self, client):
        created = client.post("/tasks", json=task_payload()).json()
        assert created["completed_at"] is None

        response = client.patch(f"/tasks/{created['id']}", json={"completed": True})

        assert response.status_code == 200
        assert response.json()["completed_at"] is not None

    def test_completed_false_clears_completed_at(self, client):
        created = client.post("/tasks", json=task_payload()).json()
        client.patch(f"/tasks/{created['id']}", json={"completed": True})

        response = client.patch(f"/tasks/{created['id']}", json={"completed": False})

        assert response.status_code == 200
        assert response.json()["completed_at"] is None

    def test_setting_title_to_null_is_rejected(self, client):
        created = client.post("/tasks", json=task_payload()).json()

        response = client.patch(f"/tasks/{created['id']}", json={"title": None})

        assert response.status_code == 422

    def test_setting_duration_to_null_is_rejected(self, client):
        created = client.post("/tasks", json=task_payload()).json()

        response = client.patch(
            f"/tasks/{created['id']}", json={"estimated_duration_minutes": None}
        )

        assert response.status_code == 422

    def test_update_missing_task_returns_404(self, client):
        response = client.patch("/tasks/999999", json={"title": "New title"})

        assert response.status_code == 404


class TestDeleteTask:
    def test_delete_existing_task_returns_204_and_removes_it(self, client):
        created = client.post("/tasks", json=task_payload()).json()

        delete_response = client.delete(f"/tasks/{created['id']}")
        get_response = client.get(f"/tasks/{created['id']}")

        assert delete_response.status_code == 204
        assert get_response.status_code == 404

    def test_delete_missing_task_returns_404(self, client):
        response = client.delete("/tasks/999999")

        assert response.status_code == 404
