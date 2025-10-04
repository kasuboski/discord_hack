"""Router models and utilities for LLM-based conversation routing.

Router selects both persona and relevant context messages.
Beats naive "last N messages" approach by selecting semantically relevant messages.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC

from pydantic import BaseModel

from discord_hack.conversation_store import ConversationMessage, ConversationThread

logger = logging.getLogger(__name__)


class PersonaInfo(BaseModel):
    """Simplified persona information for router (doesn't need full config)."""

    name: str
    role: str


class RouterDecision(BaseModel):
    """Structured output from LLM router.

    should_respond, suggested_persona, and relevant_message_ids are all used.
    conversation_id is used for conversation threading.
    """

    should_respond: bool  # Should the bot respond to this message?
    conversation_id: str | None  # Existing conversation or null for new
    suggested_persona: str | None  # Which persona should respond
    relevant_message_ids: list[str]  # Which messages to include as context
    confidence: float  # 0.0 to 1.0 (confidence in routing decision)
    reasoning: str  # Explanation (for logging/debugging)
    topic_summary: str  # Brief summary of what this message is about


@dataclass
class RouterContext:
    """Context provided to router agent."""

    current_message: ConversationMessage
    active_conversations: list[ConversationThread]
    available_personas: list[PersonaInfo]
    explicit_persona: str | None = (
        None  # If set, user explicitly mentioned this persona
    )
    is_bot_mentioned: bool = False  # True if bot/persona was mentioned
    current_time: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )  # Current time when LLM is called


@dataclass
class RouterConfig:
    """Configuration for LLM router."""

    model_name: str = "llama3.1-8b"
    confidence_threshold: float = 0.5  # Below this, create new conversation
    max_context_messages: int = 15  # Max messages to include as context
    max_recent_for_routing: int = 20  # Max messages to show router per conversation
    conversation_stale_minutes: int = 30  # When to consider conversation inactive
    max_conversations_per_channel: int = 5  # Max active conversations tracked
    enable_persona_suggestion: bool = True  # Let router suggest persona
    enable_context_selection: bool = True  # Let router select context

    # Future features
    enable_proactive_interjection: bool = False
    interjection_confidence_threshold: float = 0.8


# Helper functions for router decision processing


def normalize_message_ids(message_ids: list[str]) -> list[str]:
    """Filter out invalid message IDs and strip '#' prefix.

    The router sometimes returns 'null' or 'none' as strings when it
    can't find relevant context. This filters those out along with empty strings.
    Also strips '#' prefix from message IDs (e.g., '#141272' -> '141272').

    Args:
        message_ids: Raw list of message IDs from router decision

    Returns:
        Filtered list of valid message IDs with '#' prefix removed

    Example:
        >>> normalize_message_ids(["123", "null", "#456", "none", ""])
        ["123", "456"]
    """
    normalized: list[str] = []
    for msg_id in message_ids:
        if not msg_id or msg_id.lower() in ("null", "none"):
            continue
        # Strip '#' prefix if present
        clean_id = msg_id.lstrip("#")
        if clean_id:
            normalized.append(clean_id)
    return normalized


def get_context_messages_by_ids(
    conversation: ConversationThread,
    message_ids: list[str],
) -> tuple[list[ConversationMessage], list[str]]:
    """Get context messages from conversation by IDs.

    Args:
        conversation: The conversation thread to search
        message_ids: List of message IDs to retrieve (should be normalized first)

    Returns:
        Tuple of (found_messages, missing_ids):
        - found_messages: List of matching messages (in conversation order)
        - missing_ids: List of IDs that weren't found in the conversation

    Example:
        >>> messages, missing = get_context_messages_by_ids(conv, ["123", "456"])
        >>> if missing:
        ...     logger.warning(f"Missing message IDs: {missing}")
    """
    message_ids_set = set(message_ids)
    context_messages = [
        msg for msg in conversation.messages if msg.id in message_ids_set
    ]

    found_ids = {msg.id for msg in context_messages}
    missing_ids = [msg_id for msg_id in message_ids if msg_id not in found_ids]

    return context_messages, missing_ids


def extract_context_messages(
    conversation: ConversationThread,
    router_decision: RouterDecision,
    strict: bool = False,
) -> list[ConversationMessage]:
    """Extract context messages from router decision with validation.

    This is the main helper that combines normalization and retrieval.
    Use this in bot code to process router decisions consistently.

    Args:
        conversation: The conversation thread
        router_decision: Router decision containing relevant_message_ids
        strict: If True, raise ValueError when messages are missing

    Returns:
        List of context messages found in the conversation

    Raises:
        ValueError: If strict=True and any normalized message IDs are not found

    Example:
        >>> # Strict mode - fail fast on missing messages
        >>> context = extract_context_messages(conv, decision, strict=True)
        >>> # Lenient mode - log and continue with partial results
        >>> context = extract_context_messages(conv, decision, strict=False)
    """
    # Normalize IDs (filter out null/none)
    normalized_ids = normalize_message_ids(router_decision.relevant_message_ids)

    if not normalized_ids:
        logger.debug("No relevant message IDs after normalization")
        return []

    # Get messages and check for missing
    context_messages, missing_ids = get_context_messages_by_ids(
        conversation, normalized_ids
    )

    if missing_ids:
        error_msg = f"Router selected {len(missing_ids)} message IDs not found in conversation: {missing_ids}"
        if strict:
            raise ValueError(error_msg)
        else:
            logger.debug(
                f"Could not find {len(missing_ids)} context messages: {missing_ids}"
            )

    logger.debug(
        f"Extracted {len(context_messages)} context messages from {len(normalized_ids)} IDs"
    )

    return context_messages


def build_router_prompt(
    current_message: ConversationMessage,
    active_conversations: list[ConversationThread],
    current_time: datetime | None = None,
) -> str:
    """Build prompt for router agent with conversation history.

    Shows multiple active conversations for router to choose from.

    Args:
        current_message: The message to route
        active_conversations: List of active conversation threads in channel
        current_time: Current time when LLM is called (defaults to now)

    Returns:
        Formatted prompt for router
    """
    config = RouterConfig()

    if current_time is None:
        current_time = datetime.now(UTC)

    prompt_parts = [
        "# Task: Route this message to a conversation and select relevant context",
        "",
        "## Current Message",
        f"From: {current_message.author_name}",
        f"Content: {current_message.content}",
        f"Message time: {current_message.timestamp.strftime('%H:%M:%S')}",
        f"Current time: {current_time.strftime('%H:%M:%S')}",
        f"Time since message: {(current_time - current_message.timestamp).total_seconds():.1f}s",
    ]

    # Add metadata about current message
    if current_message.reply_to_id:
        prompt_parts.append(f"Replying to: message ID {current_message.reply_to_id}")
    if current_message.has_attachments:
        attachment_types = ", ".join(current_message.attachment_types[:3])
        prompt_parts.append(f"Attachments: {attachment_types}")

    prompt_parts.extend(["", "## Active Conversations in Channel"])

    if not active_conversations:
        prompt_parts.append(
            "No active conversations. This will start a new conversation (conversation_id=null)."
        )
    else:
        for conv in active_conversations:
            recent = conv.get_recent_messages(limit=config.max_recent_for_routing)
            prompt_parts.append(f"### Conversation: {conv.id}")
            if conv.topic_summary:
                prompt_parts.append(f"Topic: {conv.topic_summary}")
            prompt_parts.append(f"Last active: {conv.last_active.strftime('%H:%M')}")
            prompt_parts.append(
                f"Recent {len(recent)} messages (for context selection):"
            )
            for msg in recent:
                # Exclude current message from history
                if msg.id == current_message.id:
                    continue

                msg_preview = msg.content[:150]
                author = msg.author_name
                if msg.is_bot and msg.persona_name:
                    author = f"{msg.persona_name} (bot)"

                metadata_hints = []
                if msg.reply_to_id:
                    metadata_hints.append("reply")
                if msg.has_attachments:
                    metadata_hints.append(f"{len(msg.attachment_types)} files")

                metadata_str = (
                    f" [{', '.join(metadata_hints)}]" if metadata_hints else ""
                )
                prompt_parts.append(
                    f"  - ID:{msg.id} | {author}: {msg_preview}{metadata_str}"
                )
            prompt_parts.append("")  # Blank line between conversations

    prompt_parts.extend(
        [
            "## Your Task",
            "1. Determine which conversation this message belongs to (return conversation_id) OR start new (return null)",
            "2. Suggest which persona should respond (or null if none fit)",
            "3. Select message IDs that provide relevant context from that conversation (or empty list if none needed)",
            "4. Provide reasoning for your decisions",
        ]
    )

    return "\n".join(prompt_parts)
