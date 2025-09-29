"""Unit tests for the agent."""

import sys
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from pydantic_ai import capture_run_messages

from discord_hack.agent import get_agent
from discord_hack.dependencies import Deps

# Mark all tests in this file as async
pytestmark = pytest.mark.anyio

# Prevent accidental real LLM calls during tests
models.ALLOW_MODEL_REQUESTS = False


@pytest.mark.xfail(
    condition=sys.platform == "darwin", reason="Trio raises RuntimeError on macOS"
)
async def test_agent_uses_rag_tool(monkeypatch):
    """Verify that the agent calls the retrieve tool and returns a structured response."""
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")
    agent = get_agent()

    file_path = "./kbs/kb.txt"
    question = "What is the AI Team Bot?"
    deps = Deps(file_path=file_path)

    with capture_run_messages() as messages:
        with agent.override(model=TestModel()):
            result = await agent.run(question, deps=deps)

            # By default, TestModel returns a JSON string of its activity.
            assert "retrieve" in result.output

    # Verify the tool was called via captured messages
    assert any(
        part.part_kind == "tool-call" and part.tool_name == "retrieve"
        for message in messages
        for part in message.parts
    )
