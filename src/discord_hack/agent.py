"""Core Agent and RAG Tool implementation."""

from __future__ import annotations as _annotations

import logging
import os

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.profiles import ModelProfile
from pydantic_ai.profiles.google import GoogleJsonSchemaTransformer
from pydantic_ai.providers.openai import OpenAIProvider

from .config import PersonaConfig
from .dependencies import Deps

logger = logging.getLogger(__name__)


def create_agent_model() -> OpenAIChatModel:
    """Create and return the shared AI model."""
    profile = ModelProfile(json_schema_transformer=GoogleJsonSchemaTransformer)
    cerebras_provider = OpenAIProvider(
        base_url="https://api.cerebras.ai/v1",
        api_key=os.environ.get("CEREBRAS_API_KEY"),
    )
    return OpenAIChatModel(
        "llama-4-scout-17b-16e-instruct", provider=cerebras_provider, profile=profile
    )


def create_persona_agent(persona_config: PersonaConfig) -> Agent[Deps]:
    """Create an agent for a specific persona."""
    model = create_agent_model()

    # Create persona-specific system prompt
    system_prompt = f"""
    {persona_config.system_prompt}

    Use the `retrieve` tool to get relevant information from your knowledge base to answer questions.

    <output_format>
    Format your response using markdown.
    Remember you are chatting with the user in Discord. Discord is a real-time chat app. Long verbose responses are not the norm.
    Keep your responses conversational and helpful, staying in character as {persona_config.display_name}, {persona_config.role}.
    </output_format>
    """

    agent = Agent(
        model=model,
        deps_type=Deps,
        system_prompt=system_prompt,
    )

    @agent.tool
    def retrieve(context: RunContext[Deps], query: str) -> str:
        """
        Retrieves the full content of the persona's knowledge base document.

        Args:
            context: The run context, containing the file path dependency.
            query: The user's query (used by the agent to decide to call this tool).
        """
        try:
            with open(context.deps.file_path) as f:
                content = f.read()
                logger.debug(
                    f"Retrieved knowledge base content from {context.deps.file_path}"
                )
                return content
        except FileNotFoundError:
            logger.error(f"Knowledge base file not found: {context.deps.file_path}")
            return f"Knowledge base file not found: {context.deps.file_path}"
        except Exception as e:
            logger.error(f"Error reading knowledge base: {e}")
            return f"Error reading knowledge base: {e}"

    return agent


def get_agent() -> Agent[Deps]:
    """Create and return the default AI agent."""
    model = create_agent_model()

    agent = Agent(
        model=model,
        deps_type=Deps,
        system_prompt="""
        You are an AI assistant chatting with the user in Discord. Your goal is to answer questions based on the content of a document.
        Use the `retrieve` tool to get the document content.
        <output_format>
        Format your response using markdown.
        Remember you are chatting with the user in Discord. Discord is a real-time chat app. Long verbose responses are not the norm.
        </output_format>
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
        try:
            with open(context.deps.file_path) as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Knowledge base file not found: {context.deps.file_path}")
            return f"Knowledge base file not found: {context.deps.file_path}"
        except Exception as e:
            logger.error(f"Error reading knowledge base: {e}")
            return f"Error reading knowledge base: {e}"

    return agent


# Cache for persona agents to avoid recreating them
_persona_agents: dict[str, Agent[Deps]] = {}


def get_persona_agent(persona_config: PersonaConfig) -> Agent[Deps]:
    """Get or create an agent for a specific persona."""
    if persona_config.name not in _persona_agents:
        logger.info(f"Creating agent for persona: {persona_config.name}")
        _persona_agents[persona_config.name] = create_persona_agent(persona_config)
    return _persona_agents[persona_config.name]
