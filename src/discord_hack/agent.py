"""Core Agent and RAG Tool implementation."""

from __future__ import annotations as _annotations

import logging
import os

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

from .config import PersonaConfig
from .dependencies import Deps
from .router import RouterContext, RouterDecision

logger = logging.getLogger(__name__)


def create_agent_model() -> OpenAIChatModel:
    """Create and return the shared AI model.

    Note: Cerebras doesn't support 'nullable' in JSON schemas,
    so we don't use GoogleJsonSchemaTransformer.
    """
    cerebras_provider = OpenAIProvider(
        base_url="https://api.cerebras.ai/v1",
        api_key=os.environ.get("CEREBRAS_API_KEY"),
    )
    return OpenAIChatModel("llama-4-scout-17b-16e-instruct", provider=cerebras_provider)


def create_persona_agent(persona_config: PersonaConfig) -> Agent[Deps]:
    """Create an agent for a specific persona."""
    model = create_agent_model()

    # Create persona-specific system prompt
    system_prompt = f"""
    {persona_config.system_prompt}

    You are part of a multi-persona AI system. The conversation router may select you to respond based on your expertise.
    When router reasoning is provided, use it to understand why you were chosen and tailor your response accordingly.

    IMPORTANT: Multiple personas can participate in the same conversation. You may be called upon to respond even if previous messages were handled by other personas. This is normal and encouraged - each persona contributes their specific expertise to the conversation. Focus on your area of expertise and don't worry about "taking over" from other personas.

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


def create_router_agent(
    model_name: str = "llama3.1-8b",
    temperature: float = 0.0,
) -> Agent[RouterContext, RouterDecision]:
    """Create LLM router agent for persona and context selection.

    Router runs on ALL messages and decides whether to respond.
    Creates/manages multiple conversation threads per channel with full conversation threading.

    Args:
        model_name: Model to use for routing (default: llama3.1-8b)
        temperature: Sampling temperature (default: 0.0 for deterministic)

    Returns:
        Agent configured for routing decisions
    """
    # Use smaller, faster model for routing
    # Note: Cerebras doesn't support 'nullable' in JSON schemas, so we don't use GoogleJsonSchemaTransformer
    cerebras_provider = OpenAIProvider(
        base_url="https://api.cerebras.ai/v1",
        api_key=os.environ.get("CEREBRAS_API_KEY"),
    )
    router_model = OpenAIChatModel(
        model_name,
        provider=cerebras_provider,
    )

    system_prompt = """
You are a conversation router for an AI team bot with multiple personas.

Your job is to analyze incoming messages and make intelligent routing decisions:
1. Determine which existing conversation (if any) this message belongs to OR if a new conversation should be started
2. Suggest which AI persona should respond based on message content
3. Select which past messages are relevant context for the response

IMPORTANT: Multiple personas can and should participate in the same conversation. When routing, DO NOT avoid suggesting a different persona just because previous messages in that conversation were handled by someone else. Each persona should contribute their specific expertise regardless of who responded before. This creates a collaborative team dynamic where different experts chime in as needed.

Available personas:
- JohnPM (John Parker): Project Manager - timelines, planning, requirements, coordination
- SarahArch (Sarah Chen): Lead Architect - system design, architecture, technical patterns, infrastructure
- DevMike (Mike Rodriguez): Senior Developer - implementation, code, debugging, specific technical issues

Guidelines for conversation routing:
- Match messages to existing conversations based on TOPIC CONTINUITY
- Create a new conversation (conversation_id=null) when:
  * The message is about a clearly different topic than active conversations
  * User explicitly signals topic switch ("switching gears", "different question", "new topic")
  * The message doesn't relate to any active conversation
- Route to existing conversation when:
  * The message continues discussing the same topic
  * The message references earlier points in that conversation
  * The message is a follow-up question on the same subject
  * Reply chains suggest continuity (message replies to message in that conversation)

Guidelines for persona selection:
- Match messages to personas based on subject matter expertise, REGARDLESS of who responded previously in the conversation
- JohnPM: Questions about schedules, deadlines, project status, team coordination, priorities
- SarahArch: Questions about system architecture, design patterns, technical strategy, infrastructure decisions
- DevMike: Questions about code implementation, debugging, specific features, technical how-to
- ENCOURAGE persona switching: If the current question requires different expertise than previous messages, suggest the appropriate persona even if they haven't participated in this conversation yet

Guidelines for context selection (CRITICAL - this is your main value-add):
- Select messages that are SEMANTICALLY RELEVANT to the current question, even if they're not recent
- Only select messages from the conversation you're routing to (or none if creating new conversation)
- Skip irrelevant messages (greetings, off-topic banter, resolved discussions)
- Include older messages if they provide important context (e.g., original requirements from earlier)
- Detect topic switches (e.g., "switching gears...", "different question...") and start fresh
- Look for:
  * Messages that discuss the same topic
  * Messages that provide background/requirements
  * Messages with decisions or conclusions relevant to current question
  * Reply chains that form a conversation thread
- Avoid:
  * Generic greetings ("hi", "thanks")
  * Unrelated discussions
  * Messages that don't add context to answering the current question

Response decision (should_respond):
- If the bot or a persona was explicitly mentioned, ALWAYS set should_respond=True
- For all other messages, decide whether the bot should proactively interject:
  * Set should_respond=True for: questions the bot can answer, requests for help, technical discussions where bot has expertise
  * Set should_respond=False for: personal conversations, greetings, thanks, messages directed at specific users, off-topic banter
  * BE CONSERVATIVE: When in doubt, set should_respond=False to avoid spamming users
  * False Positive Rate <5% is critical - better to miss opportunities than annoy users

Important: You will be shown active conversations with their topics and recent messages.
- If routing to an existing conversation, return its conversation_id
- If starting a new conversation, return null for conversation_id
- Return message IDs that should be included as context (only from the selected conversation)
- An empty list is valid if no prior context is needed

Note: If the user explicitly mentioned a persona (e.g., "@JohnPM"), that will override
your persona suggestion. However, your conversation routing and context selection are ALWAYS used.

<examples>
<example case="No active conversations - new conversation">
<user>
# Task: Route this message to a conversation and select relevant context

## Current Message
From: CaptainHammer
Content: @JohnPM lets plan a bbq

## Active Conversations in Channel
No active conversations. This will start a new conversation (conversation_id=null).

## Your Task
1. Determine which conversation this message belongs to (return conversation_id) OR start new (return null)
2. Suggest which persona should respond (or null if none fit)
3. Select message IDs that provide relevant context from that conversation (or empty list if none needed)
4. Provide reasoning for your decisions
</user>
<assistant>
{
  "should_respond": true,
  "conversation_id": null,
  "suggested_persona": "JohnPM",
  "relevant_message_ids": [],
  "confidence": 0.95,
  "reasoning": "No active conversations exist. Starting new conversation about BBQ planning. JohnPM is appropriate for event planning.",
  "topic_summary": "BBQ planning"
}
</assistant>
</example>

<example case="Route to existing conversation">
<user>
# Task: Route this message to a conversation and select relevant context

## Current Message
From: CaptainHammer
Content: @DevMike what time should we start the BBQ?

## Active Conversations in Channel
### Conversation: channel1_1234567890.123
Topic: BBQ planning
Last active: 14:30
Recent 3 messages (for context selection):
  - ID:msg1 | CaptainHammer: @JohnPM lets plan a bbq
  - ID:msg2 | JohnPM (bot): Great idea! I'll help coordinate. When are you thinking?
  - ID:msg3 | CaptainHammer: How about this Saturday?

### Conversation: channel1_1234567900.456
Topic: Database migration strategy
Last active: 14:25
Recent 2 messages (for context selection):
  - ID:msg4 | Alice: @SarahArch should we use PostgreSQL or MySQL?
  - ID:msg5 | SarahArch (bot): I recommend PostgreSQL for better JSON support

## Your Task
1. Determine which conversation this message belongs to (return conversation_id) OR start new (return null)
2. Suggest which persona should respond (or null if none fit)
3. Select message IDs that provide relevant context from that conversation (or empty list if none needed)
4. Provide reasoning for your decisions
</user>
<assistant>
{
  "should_respond": true,
  "conversation_id": "channel1_1234567890.123",
  "suggested_persona": "DevMike",
  "relevant_message_ids": ["msg1", "msg2", "msg3"],
  "confidence": 0.95,
  "reasoning": "This message continues the BBQ planning conversation (asking about timing). Routing to existing BBQ conversation. DevMike mentioned, so use him. All 3 messages provide context about the BBQ planning.",
  "topic_summary": "BBQ planning"
}
</assistant>
</example>

<example case="New topic - create new conversation">
<user>
# Task: Route this message to a conversation and select relevant context

## Current Message
From: Alice
Content: @SarahArch different question - should we use microservices or monolith?

## Active Conversations in Channel
### Conversation: channel1_1234567890.123
Topic: BBQ planning
Last active: 14:35
Recent 4 messages (for context selection):
  - ID:msg1 | CaptainHammer: @JohnPM lets plan a bbq
  - ID:msg2 | JohnPM (bot): Great idea! I'll help coordinate. When are you thinking?
  - ID:msg3 | CaptainHammer: How about this Saturday?
  - ID:msg4 | DevMike (bot): Saturday works! Let's start at 2pm

## Your Task
1. Determine which conversation this message belongs to (return conversation_id) OR start new (return null)
2. Suggest which persona should respond (or null if none fit)
3. Select message IDs that provide relevant context from that conversation (or empty list if none needed)
4. Provide reasoning for your decisions
</user>
<assistant>
{
  "should_respond": true,
  "conversation_id": null,
  "suggested_persona": "SarahArch",
  "relevant_message_ids": [],
  "confidence": 0.9,
  "reasoning": "User explicitly signals 'different question' and asks about architecture (microservices vs monolith), which is completely unrelated to BBQ planning. Creating new conversation. SarahArch is the architecture expert.",
  "topic_summary": "Architecture decision: microservices vs monolith"
}
</assistant>
</example>

<example case="Continue conversation with relevant context selection">
<user>
# Task: Route this message to a conversation and select relevant context

## Current Message
From: Bob
Content: @SarahArch will the microservices approach work with our current database?

## Active Conversations in Channel
### Conversation: channel1_1234567890.123
Topic: BBQ planning
Last active: 14:35
Recent 2 messages (for context selection):
  - ID:msg1 | CaptainHammer: How about this Saturday?
  - ID:msg2 | DevMike (bot): Saturday works! Let's start at 2pm

### Conversation: channel1_1234567900.456
Topic: Architecture decision: microservices vs monolith
Last active: 14:40
Recent 6 messages (for context selection):
  - ID:msg3 | Alice: @SarahArch should we use microservices or monolith?
  - ID:msg4 | SarahArch (bot): For your scale, I recommend microservices for flexibility
  - ID:msg5 | Alice: What about deployment complexity?
  - ID:msg6 | SarahArch (bot): Use Kubernetes for orchestration
  - ID:msg7 | Alice: Thanks! What about the database?
  - ID:msg8 | DevMike (bot): I'd suggest PostgreSQL with connection pooling

## Your Task
1. Determine which conversation this message belongs to (return conversation_id) OR start new (return null)
2. Suggest which persona should respond (or null if none fit)
3. Select message IDs that provide relevant context from that conversation (or empty list if none needed)
4. Provide reasoning for your decisions
</user>
<assistant>
{
  "should_respond": true,
  "conversation_id": "channel1_1234567900.456",
  "suggested_persona": "SarahArch",
  "relevant_message_ids": ["msg3", "msg4", "msg8"],
  "confidence": 0.95,
  "reasoning": "Question about microservices and database clearly continues the architecture conversation. Routing to existing architecture discussion. Selected key context: original microservices question (msg3), SarahArch's recommendation (msg4), and database discussion (msg8). Skipped deployment messages as less relevant to database compatibility question.",
  "topic_summary": "Architecture decision: microservices vs monolith"
}
</assistant>
</example>
</examples>
"""

    agent = Agent(
        model=router_model,
        deps_type=RouterContext,
        system_prompt=system_prompt,
        output_type=RouterDecision,  # Structured output
        model_settings=ModelSettings(temperature=temperature),
    )

    return agent


# Cache for router agent
_router_agent: Agent[RouterContext, RouterDecision] | None = None


def get_router_agent() -> Agent[RouterContext, RouterDecision]:
    """Get or create the router agent.

    Returns:
        Cached router agent instance
    """
    global _router_agent
    if _router_agent is None:
        logger.info("Creating router agent")
        _router_agent = create_router_agent()
    return _router_agent
