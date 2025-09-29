"""Core Agent and RAG Tool implementation."""

from __future__ import annotations as _annotations

from pydantic_ai import Agent, RunContext

from .dependencies import Deps


def get_agent() -> Agent[Deps]:
    """Create and return the main AI agent."""
    agent = Agent(
        model="openai:gpt-3.5-turbo",
        deps_type=Deps,
        system_prompt="""
        You are an AI assistant. Your goal is to answer questions based on the content of a document.
        Use the `retrieve` tool to get the document content.
        """,
    )

    @agent.tool
    def retrieve(context: RunContext[Deps], query: str) -> str:
        """
        Retrieves the full content of the knowledge base document.

        Args:
            context: The run context, containing the file path dependency.
            query: The user's query (used by the agent to decide to call this tool).
        """
        with open(context.deps.file_path) as f:
            return f.read()

    return agent
