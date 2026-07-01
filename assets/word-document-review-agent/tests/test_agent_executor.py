"""Unit tests for AgentExecutor."""
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

APP_DIR = Path(__file__).parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import pytest
from a2a.types import TaskState


def _make_request_context(query="test query", task_id="task-1", context_id="ctx-1"):
    task = MagicMock()
    task.id = task_id
    task.context_id = context_id

    context = MagicMock()
    context.get_user_input.return_value = query
    context.current_task = task
    context.message = MagicMock()
    return context


@pytest.mark.asyncio
async def test_agent_executor_execute_completes():
    """Executor runs to completion and calls updater.complete()."""
    from agent_executor import AgentExecutor

    async def mock_stream(*args, **kwargs):
        yield {"is_task_complete": False, "require_user_input": False, "content": "Working..."}
        yield {"is_task_complete": True, "require_user_input": False, "content": "Done."}

    context = _make_request_context("/tmp/doc.docx")
    event_queue = AsyncMock()
    updater_mock = AsyncMock()

    with patch("agent_executor.WordReviewAgent") as MockAgent, \
         patch("agent_executor.get_mcp_tools", return_value=[]), \
         patch("agent_executor.get_user_token", return_value=None), \
         patch("agent_executor.get_load_skill_resource_tool", return_value=[]), \
         patch("agent_executor.TaskUpdater", return_value=updater_mock):

        mock_instance = MockAgent.return_value
        mock_instance.stream = mock_stream

        executor = AgentExecutor()
        await executor.execute(context, event_queue)

    updater_mock.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_executor_execute_working_updates():
    """Executor sends working status updates for non-final items."""
    from agent_executor import AgentExecutor

    async def mock_stream(*args, **kwargs):
        yield {"is_task_complete": False, "require_user_input": False, "content": "Processing step 1"}
        yield {"is_task_complete": False, "require_user_input": False, "content": "Processing step 2"}
        yield {"is_task_complete": True, "require_user_input": False, "content": "All done"}

    context = _make_request_context("/tmp/doc.docx")
    event_queue = AsyncMock()
    updater_mock = AsyncMock()

    with patch("agent_executor.WordReviewAgent") as MockAgent, \
         patch("agent_executor.get_mcp_tools", return_value=[]), \
         patch("agent_executor.get_user_token", return_value=None), \
         patch("agent_executor.get_load_skill_resource_tool", return_value=[]), \
         patch("agent_executor.TaskUpdater", return_value=updater_mock):

        mock_instance = MockAgent.return_value
        mock_instance.stream = mock_stream

        executor = AgentExecutor()
        await executor.execute(context, event_queue)

    # update_status should have been called for working updates
    assert updater_mock.update_status.await_count >= 2


@pytest.mark.asyncio
async def test_agent_executor_execute_requires_input():
    """When require_user_input=True, executor sets input_required status."""
    from agent_executor import AgentExecutor

    async def mock_stream(*args, **kwargs):
        yield {"is_task_complete": False, "require_user_input": True, "content": "Please provide a file path."}

    context = _make_request_context("no file path")
    event_queue = AsyncMock()
    updater_mock = AsyncMock()

    with patch("agent_executor.WordReviewAgent") as MockAgent, \
         patch("agent_executor.get_mcp_tools", return_value=[]), \
         patch("agent_executor.get_user_token", return_value=None), \
         patch("agent_executor.get_load_skill_resource_tool", return_value=[]), \
         patch("agent_executor.TaskUpdater", return_value=updater_mock):

        mock_instance = MockAgent.return_value
        mock_instance.stream = mock_stream

        executor = AgentExecutor()
        await executor.execute(context, event_queue)

    # Should have been called with input_required
    calls = updater_mock.update_status.call_args_list
    assert any(call.args[0] == TaskState.input_required for call in calls)


@pytest.mark.asyncio
async def test_agent_executor_no_current_task_creates_new_task():
    """When context has no current task, executor creates a new one."""
    from agent_executor import AgentExecutor

    async def mock_stream(*args, **kwargs):
        yield {"is_task_complete": True, "require_user_input": False, "content": "Done."}

    context = _make_request_context()
    context.current_task = None  # No current task

    event_queue = AsyncMock()
    updater_mock = AsyncMock()
    new_task_mock = MagicMock()
    new_task_mock.id = "new-task-id"
    new_task_mock.context_id = "new-ctx"

    with patch("agent_executor.WordReviewAgent") as MockAgent, \
         patch("agent_executor.get_mcp_tools", return_value=[]), \
         patch("agent_executor.get_user_token", return_value=None), \
         patch("agent_executor.get_load_skill_resource_tool", return_value=[]), \
         patch("agent_executor.TaskUpdater", return_value=updater_mock), \
         patch("agent_executor.new_task", return_value=new_task_mock):

        mock_instance = MockAgent.return_value
        mock_instance.stream = mock_stream

        executor = AgentExecutor()
        await executor.execute(context, event_queue)

    event_queue.enqueue_event.assert_awaited()


@pytest.mark.asyncio
async def test_agent_executor_cancel_raises_unsupported():
    """cancel() should raise ServerError with UnsupportedOperationError."""
    from agent_executor import AgentExecutor
    from a2a.utils.errors import ServerError

    with patch("agent_executor.WordReviewAgent"), \
         patch("agent_executor.get_load_skill_resource_tool", return_value=[]):
        executor = AgentExecutor()

    context = _make_request_context()
    event_queue = AsyncMock()

    with pytest.raises(ServerError):
        await executor.cancel(context, event_queue)
