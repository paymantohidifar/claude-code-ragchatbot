"""
API endpoint tests for app.py.

Tests /api/query, /api/courses, and the static-file root mount using a
TestClient backed by a mock RAGSystem — no ChromaDB, embeddings, or
Anthropic API calls are made.
"""
import pytest


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_returns_200_with_valid_query(self, client):
        response = client.post("/api/query", json={"query": "What is Python?"})
        assert response.status_code == 200

    def test_response_contains_required_fields(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    def test_answer_matches_mock_return_value(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert data["answer"] == "Test answer."

    def test_sources_returned_as_list(self, client):
        data = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert isinstance(data["sources"], list)

    def test_auto_generates_session_id_when_not_provided(self, client, mock_rag):
        data = client.post("/api/query", json={"query": "test"}).json()
        assert data["session_id"] == "test-session-id"
        mock_rag.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag):
        data = client.post("/api/query", json={"query": "test", "session_id": "my-session"}).json()
        assert data["session_id"] == "my-session"
        mock_rag.session_manager.create_session.assert_not_called()

    def test_calls_rag_query_with_correct_arguments(self, client, mock_rag):
        client.post("/api/query", json={"query": "What is ML?", "session_id": "s1"})
        mock_rag.query.assert_called_once_with("What is ML?", "s1")

    def test_missing_query_field_returns_422(self, client):
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_empty_query_string_is_accepted(self, client):
        response = client.post("/api/query", json={"query": ""})
        assert response.status_code == 200

    def test_rag_exception_returns_500(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("DB connection lost")
        response = client.post("/api/query", json={"query": "test"})
        assert response.status_code == 500

    def test_500_detail_contains_exception_message(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("DB connection lost")
        data = client.post("/api/query", json={"query": "test"}).json()
        assert "DB connection lost" in data["detail"]


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    def test_returns_200(self, client):
        response = client.get("/api/courses")
        assert response.status_code == 200

    def test_response_contains_total_courses(self, client):
        assert "total_courses" in client.get("/api/courses").json()

    def test_response_contains_course_titles(self, client):
        assert "course_titles" in client.get("/api/courses").json()

    def test_total_courses_matches_mock(self, client):
        assert client.get("/api/courses").json()["total_courses"] == 2

    def test_course_titles_match_mock(self, client):
        titles = client.get("/api/courses").json()["course_titles"]
        assert titles == ["Python Basics", "ML Fundamentals"]

    def test_course_titles_is_a_list(self, client):
        assert isinstance(client.get("/api/courses").json()["course_titles"], list)

    def test_analytics_exception_returns_500(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("Analytics unavailable")
        response = client.get("/api/courses")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Root / static-file mount
# ---------------------------------------------------------------------------

class TestRootMount:
    def test_root_mount_is_registered_in_routes(self, fastapi_app):
        """The frontend static-file mount must be present in the app's route table.
        Starlette stores a root mount with path '' (empty string)."""
        route_paths = [getattr(r, "path", None) for r in fastapi_app.app.routes]
        # Root mount is stored as "" by Starlette
        assert "" in route_paths

    def test_api_routes_not_shadowed_by_root_mount(self, client):
        """API endpoints must remain reachable even with a catch-all mount at /."""
        assert client.get("/api/courses").status_code == 200
