"""
Tests for AIGenerator in ai_generator.py.

These tests mock the Anthropic client — no real API key or network needed.
Tests marked with DIAGNOSTIC are expected to fail and reveal missing error handling.
"""
import pytest
from unittest.mock import MagicMock, patch, call


def make_text_block(text="Answer text."):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(name="search_course_content", tool_id="tu_001", input_data=None):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = input_data or {"query": "Python basics"}
    return block


def make_response(stop_reason="end_turn", content_blocks=None):
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = content_blocks if content_blocks is not None else [make_text_block()]
    return resp


@pytest.fixture
def generator():
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")
        gen._mock_client = mock_client  # expose for assertions
        return gen


# ---------------------------------------------------------------------------
# generate_response() — direct (no tool use)
# ---------------------------------------------------------------------------

class TestGenerateResponseDirect:
    def test_returns_text_for_end_turn(self, generator):
        generator._mock_client.messages.create.return_value = make_response(
            stop_reason="end_turn",
            content_blocks=[make_text_block("Direct answer.")],
        )
        result = generator.generate_response(query="What is 2+2?")
        assert result == "Direct answer."

    def test_api_called_with_query_as_user_message(self, generator):
        generator._mock_client.messages.create.return_value = make_response()
        generator.generate_response(query="Hello world")
        call_kwargs = generator._mock_client.messages.create.call_args[1]
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello world"

    def test_conversation_history_injected_into_system(self, generator):
        generator._mock_client.messages.create.return_value = make_response()
        generator.generate_response(query="follow-up", conversation_history="User: hi\nAssistant: hello")
        call_kwargs = generator._mock_client.messages.create.call_args[1]
        assert "Previous conversation" in call_kwargs["system"]
        assert "User: hi" in call_kwargs["system"]

    def test_tools_included_when_provided(self, generator):
        generator._mock_client.messages.create.return_value = make_response()
        tools = [{"name": "search_course_content", "description": "Search"}]
        generator.generate_response(query="search this", tools=tools)
        call_kwargs = generator._mock_client.messages.create.call_args[1]
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_no_tools_key_when_tools_is_none(self, generator):
        generator._mock_client.messages.create.return_value = make_response()
        generator.generate_response(query="simple question")
        call_kwargs = generator._mock_client.messages.create.call_args[1]
        assert "tools" not in call_kwargs


# ---------------------------------------------------------------------------
# generate_response() — tool use path
# ---------------------------------------------------------------------------

class TestGenerateResponseToolUse:
    def test_tool_use_triggers_tool_execution(self, generator):
        tool_block = make_tool_use_block(name="search_course_content", input_data={"query": "Python"})
        initial_resp = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        final_resp = make_response(stop_reason="end_turn", content_blocks=[make_text_block("Final answer.")])
        generator._mock_client.messages.create.side_effect = [initial_resp, final_resp]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Search result text"

        result = generator.generate_response(
            query="What is Python?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="Python"
        )
        assert result == "Final answer."

    def test_tool_result_added_to_messages_with_correct_id(self, generator):
        tool_block = make_tool_use_block(name="search_course_content", tool_id="tu_abc", input_data={"query": "ML"})
        initial_resp = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        final_resp = make_response()
        generator._mock_client.messages.create.side_effect = [initial_resp, final_resp]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "ML content here"

        generator.generate_response(query="ML question", tools=[], tool_manager=mock_tool_manager)

        second_call_kwargs = generator._mock_client.messages.create.call_args[1]
        messages = second_call_kwargs["messages"]
        # Last user message should be tool_result
        tool_result_msg = messages[-1]
        assert tool_result_msg["role"] == "user"
        tool_result_content = tool_result_msg["content"][0]
        assert tool_result_content["type"] == "tool_result"
        assert tool_result_content["tool_use_id"] == "tu_abc"
        assert tool_result_content["content"] == "ML content here"

    def test_second_api_call_omits_tools(self, generator):
        """Final API call must not include tools to prevent infinite tool loops."""
        tool_block = make_tool_use_block()
        initial_resp = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        final_resp = make_response()
        generator._mock_client.messages.create.side_effect = [initial_resp, final_resp]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"
        tools = [{"name": "search_course_content"}]

        generator.generate_response(query="q", tools=tools, tool_manager=mock_tool_manager)

        second_call_kwargs = generator._mock_client.messages.create.call_args[1]
        assert "tools" not in second_call_kwargs


# ---------------------------------------------------------------------------
# DIAGNOSTIC TESTS — expected to FAIL, revealing missing error handling
# ---------------------------------------------------------------------------

class TestGenerateResponseErrorHandling:
    def test_api_error_on_first_call_returns_error_string_not_raises(self, generator):
        """
        DIAGNOSTIC: generate_response() should catch API errors and return a graceful
        error string. ai_generator.py line 83 has no try/except, so this test FAILS —
        the exception propagates up and the endpoint returns HTTP 500 ("query failed").
        """
        generator._mock_client.messages.create.side_effect = Exception("API connection refused")
        result = generator.generate_response(query="What is Python?")
        assert isinstance(result, str)
        assert len(result) > 0  # any non-empty graceful message is acceptable

    def test_empty_content_list_returns_error_string_not_raises(self, generator):
        """
        DIAGNOSTIC: response.content[0].text on line 90 raises IndexError when content
        is empty. Should return a graceful error string instead.
        """
        generator._mock_client.messages.create.return_value = make_response(
            stop_reason="end_turn", content_blocks=[]
        )
        result = generator.generate_response(query="What is Python?")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_api_error_on_second_call_returns_error_string_not_raises(self, generator):
        """
        DIAGNOSTIC: _handle_tool_execution() line 137 has no try/except around the
        second client.messages.create() call. Should return graceful error.
        """
        tool_block = make_tool_use_block()
        initial_resp = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        generator._mock_client.messages.create.side_effect = [
            initial_resp,
            Exception("API timeout on second call"),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "some result"

        result = generator.generate_response(
            query="course question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert isinstance(result, str)
        assert len(result) > 0  # any non-empty graceful message is acceptable

    def test_empty_content_after_tool_use_returns_error_string_not_raises(self, generator):
        """
        DIAGNOSTIC: _handle_tool_execution() line 138 accesses content[0] unsafely.
        """
        tool_block = make_tool_use_block()
        initial_resp = make_response(stop_reason="tool_use", content_blocks=[tool_block])
        final_resp = make_response(stop_reason="end_turn", content_blocks=[])
        generator._mock_client.messages.create.side_effect = [initial_resp, final_resp]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        result = generator.generate_response(
            query="course question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )
        assert isinstance(result, str)
        assert len(result) > 0
