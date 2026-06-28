"""
Tests for CourseSearchTool.execute() in search_tools.py.

These tests mock VectorStore so no ChromaDB or embedding model is needed.
Some tests are EXPECTED TO FAIL — those failures reveal missing error handling in production code.
"""
import pytest
from unittest.mock import MagicMock, patch
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


def make_search_results(documents, metadata=None, distances=None):
    """Helper: build a valid SearchResults with no error."""
    if metadata is None:
        metadata = [{"course_title": "Test Course", "lesson_number": 1}] * len(documents)
    if distances is None:
        distances = [0.1] * len(documents)
    return SearchResults(documents=documents, metadata=metadata, distances=distances)


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    return store


@pytest.fixture
def tool(mock_store):
    return CourseSearchTool(vector_store=mock_store)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestCourseSearchToolHappyPath:
    def test_returns_formatted_string_on_results(self, tool, mock_store):
        mock_store.search.return_value = make_search_results(
            documents=["Lesson content about Python."],
            metadata=[{"course_title": "Python Basics", "lesson_number": 2}],
        )
        result = tool.execute(query="What is Python?")
        assert "Python Basics" in result
        assert "Lesson 2" in result
        assert "Lesson content about Python." in result

    def test_passes_query_to_vector_store(self, tool, mock_store):
        mock_store.search.return_value = make_search_results(["some content"])
        tool.execute(query="my query")
        mock_store.search.assert_called_once_with(
            query="my query", course_name=None, lesson_number=None
        )

    def test_passes_course_name_filter(self, tool, mock_store):
        mock_store.search.return_value = make_search_results(["content"])
        tool.execute(query="intro", course_name="Python Basics")
        mock_store.search.assert_called_once_with(
            query="intro", course_name="Python Basics", lesson_number=None
        )

    def test_passes_lesson_number_filter(self, tool, mock_store):
        mock_store.search.return_value = make_search_results(["content"])
        tool.execute(query="intro", lesson_number=3)
        mock_store.search.assert_called_once_with(
            query="intro", course_name=None, lesson_number=3
        )

    def test_sources_stored_on_last_sources(self, tool, mock_store):
        mock_store.search.return_value = make_search_results(
            documents=["content"],
            metadata=[{"course_title": "ML Course", "lesson_number": 1}],
        )
        tool.execute(query="ML basics")
        assert len(tool.last_sources) == 1

    def test_multiple_results_all_included(self, tool, mock_store):
        mock_store.search.return_value = make_search_results(
            documents=["doc1", "doc2", "doc3"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
                {"course_title": "Course C", "lesson_number": 3},
            ],
        )
        result = tool.execute(query="test")
        assert "doc1" in result
        assert "doc2" in result
        assert "doc3" in result


# ---------------------------------------------------------------------------
# Empty / error results from VectorStore
# ---------------------------------------------------------------------------

class TestCourseSearchToolErrorResults:
    def test_returns_error_string_when_search_has_error(self, tool, mock_store):
        mock_store.search.return_value = SearchResults.empty("No course found matching 'XYZ'")
        result = tool.execute(query="anything", course_name="XYZ")
        assert "No course found" in result

    def test_returns_no_results_message_on_empty_results(self, tool, mock_store):
        mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        result = tool.execute(query="something obscure")
        assert "No relevant content found" in result

    def test_empty_results_with_course_name_mentions_course(self, tool, mock_store):
        mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )
        result = tool.execute(query="intro", course_name="My Course")
        assert "My Course" in result


# ---------------------------------------------------------------------------
# Exception propagation — EXPECTED TO FAIL if no try/except in execute()
# These tests document the MISSING error handling.
# ---------------------------------------------------------------------------

class TestCourseSearchToolExceptionHandling:
    def test_search_exception_returns_error_string_not_raises(self, tool, mock_store):
        """
        DIAGNOSTIC TEST: execute() should catch exceptions from store.search() and
        return an error string. Currently search_tools.py has no try/except around
        store.search(), so this test is EXPECTED TO FAIL — that failure confirms the bug.
        """
        mock_store.search.side_effect = RuntimeError("ChromaDB connection failed")
        # Expect graceful error string, not a raised exception
        result = tool.execute(query="What is AI?")
        assert isinstance(result, str)
        assert "error" in result.lower() or "failed" in result.lower()
