import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

# Add backend/ to path so tests can import backend modules directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_rag():
    """Pre-configured mock RAGSystem for API endpoint tests."""
    mock = MagicMock()
    mock.session_manager.create_session.return_value = "test-session-id"
    mock.query.return_value = ("Test answer.", ["Python Basics - Lesson 1"])
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Basics", "ML Fundamentals"],
    }
    return mock


@pytest.fixture(scope="session")
def fastapi_app():
    """
    Import app.py once per test session with external deps patched at import time.

    RAGSystem is patched so the module-level instantiation doesn't connect to ChromaDB
    or sentence-transformers. StaticFiles is patched so the frontend directory check
    doesn't fail in the test environment.
    """
    sys.modules.pop("app", None)
    with (
        patch("rag_system.RAGSystem"),
        patch("fastapi.staticfiles.StaticFiles"),
    ):
        import app as _app_module
    return _app_module


@pytest.fixture
def client(fastapi_app, mock_rag):
    """Per-test TestClient with a fresh mock RAGSystem injected."""
    fastapi_app.rag_system = mock_rag
    return TestClient(fastapi_app.app)
