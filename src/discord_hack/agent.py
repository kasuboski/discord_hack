"""Core Agent and RAG Tool implementation."""

from __future__ import annotations as _annotations

import os

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles import ModelProfile
from pydantic_ai.profiles.google import GoogleJsonSchemaTransformer
from pydantic_ai.providers.openai import OpenAIProvider

from .dependencies import Deps


def get_agent() -> Agent[Deps]:
    """Create and return the main AI agent."""
    profile = ModelProfile(json_schema_transformer=GoogleJsonSchemaTransformer)
    cerebras_provider = OpenAIProvider(
        base_url="https://api.cerebras.ai/v1",
        api_key=os.environ.get("CEREBRAS_API_KEY"),
    )
    model = OpenAIChatModel("llama3.1-8b", provider=cerebras_provider, profile=profile)
    agent = Agent(
        model=model,
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
