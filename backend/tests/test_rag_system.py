"""
Tests for RAGSystem.query() in rag_system.py.

All heavy dependencies (ChromaDB, sentence-transformers, Anthropic client) are mocked.
Tests marked DIAGNOSTIC are expected to FAIL and reveal missing error handling in query().
"""
import pytest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


@pytest.fixture
def config():
    return SimpleNamespace(
        ANTHROPIC_API_KEY="test-key",
        ANTHROPIC_MODEL="claude-test",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        CHROMA_PATH="./chroma_db",
        MAX_RESULTS=5,
        MAX_HISTORY=2,
    )


@pytest.fixture
def rag(config):
    """Return a RAGSystem with all external I/O fully mocked."""
    with (
        patch("chromadb.PersistentClient"),
        patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"),
        patch("anthropic.Anthropic"),
    ):
        from rag_system import RAGSystem
        system = RAGSystem(config)

        # Replace live components with controllable mocks
        system.ai_generator = MagicMock()
        system.tool_manager = MagicMock()
        system.session_manager = MagicMock()

        system.tool_manager.get_tool_definitions.return_value = [
            {"name": "search_course_content"}
        ]
        system.tool_manager.get_last_sources.return_value = []
        system.session_manager.get_conversation_history.return_value = None
        system.session_manager.create_session.return_value = "session-1"

        return system


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestRAGSystemQueryHappyPath:
    def test_returns_tuple_of_answer_and_sources(self, rag):
        rag.ai_generator.generate_response.return_value = "Here is the answer."
        answer, sources = rag.query("What is machine learning?")
        assert answer == "Here is the answer."
        assert isinstance(sources, list)

    def test_calls_generate_response_with_tools(self, rag):
        rag.ai_generator.generate_response.return_value = "answer"
        rag.query("a question")
        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["tools"] is not None
        assert len(call_kwargs["tools"]) > 0

    def test_tool_manager_passed_to_generate_response(self, rag):
        rag.ai_generator.generate_response.return_value = "answer"
        rag.query("a question")
        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["tool_manager"] is rag.tool_manager

    def test_query_wrapped_in_prompt_template(self, rag):
        rag.ai_generator.generate_response.return_value = "answer"
        rag.query("What is gradient descent?")
        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert "What is gradient descent?" in call_kwargs["query"]

    def test_session_history_passed_as_conversation_history(self, rag):
        rag.session_manager.get_conversation_history.return_value = "User: hi\nAssistant: hello"
        rag.ai_generator.generate_response.return_value = "answer"
        rag.query("follow-up question", session_id="session-1")
        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert "User: hi" in call_kwargs["conversation_history"]

    def test_sources_collected_from_tool_manager(self, rag):
        rag.ai_generator.generate_response.return_value = "answer"
        rag.tool_manager.get_last_sources.return_value = ["Course A - Lesson 1", "Course B - Lesson 2"]
        _, sources = rag.query("What is Python?")
        assert sources == ["Course A - Lesson 1", "Course B - Lesson 2"]

    def test_sources_reset_after_query(self, rag):
        rag.ai_generator.generate_response.return_value = "answer"
        rag.query("a question")
        rag.tool_manager.reset_sources.assert_called_once()

    def test_session_history_updated_after_response(self, rag):
        rag.ai_generator.generate_response.return_value = "great answer"
        rag.query("my question", session_id="session-1")
        rag.session_manager.add_exchange.assert_called_once_with(
            "session-1", "my question", "great answer"
        )

    def test_no_session_history_when_no_session_id(self, rag):
        rag.ai_generator.generate_response.return_value = "answer"
        rag.query("question with no session")
        rag.session_manager.get_conversation_history.assert_not_called()


# ---------------------------------------------------------------------------
# DIAGNOSTIC TESTS — expected to FAIL, revealing missing error handling
# ---------------------------------------------------------------------------

class TestRAGSystemQueryErrorHandling:
    def test_ai_generator_exception_returns_error_string_not_raises(self, rag):
        """
        DIAGNOSTIC: rag_system.py line 124 calls generate_response() with no try/except.
        When AIGenerator throws (e.g. API failure), the exception propagates to app.py,
        which catches it and returns HTTP 500 — this is the "query failed" bug.

        This test FAILS currently because rag_system.query() does not catch the exception.
        Fix: wrap generate_response() in try/except and return a user-friendly error string.
        """
        rag.ai_generator.generate_response.side_effect = Exception("Anthropic API error: 401 Unauthorized")
        answer, sources = rag.query("What is Python?")
        # Should get a graceful string, not raise
        assert isinstance(answer, str)
        assert len(answer) > 0
        assert isinstance(sources, list)

    def test_tool_manager_exception_returns_error_string_not_raises(self, rag):
        """
        DIAGNOSTIC: ToolManager errors should also be caught gracefully.
        """
        rag.tool_manager.get_tool_definitions.side_effect = Exception("ToolManager failure")
        answer, sources = rag.query("course question")
        assert isinstance(answer, str)
        assert isinstance(sources, list)


# ---------------------------------------------------------------------------
# Tool integration — verify tools are wired correctly
# ---------------------------------------------------------------------------

class TestRAGSystemToolWiring:
    def test_both_search_and_outline_tools_registered(self, config):
        """Verify that RAGSystem registers both CourseSearchTool and CourseOutlineTool."""
        with (
            patch("chromadb.PersistentClient"),
            patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"),
            patch("anthropic.Anthropic"),
        ):
            from rag_system import RAGSystem
            system = RAGSystem(config)
            tool_names = {t["name"] for t in system.tool_manager.get_tool_definitions()}
            assert "search_course_content" in tool_names
            assert "get_course_outline" in tool_names

    def test_tool_manager_is_not_none_when_calling_generate_response(self, rag):
        rag.ai_generator.generate_response.return_value = "answer"
        rag.query("a question")
        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert call_kwargs["tool_manager"] is not None
