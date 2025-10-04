"""Persona agent prompt building utilities."""

from __future__ import annotations

from .conversation_store import ConversationMessage


def format_context_messages(messages: list[ConversationMessage]) -> str:
    """Format context messages for LLM consumption.

    Args:
        messages: List of context messages

    Returns:
        Formatted string for LLM prompt
    """
    if not messages:
        return "No prior context available."

    formatted = []
    for msg in messages:
        timestamp_str = msg.timestamp.strftime("%Y-%m-%d %H:%M")
        author = msg.author_name
        if msg.is_bot and msg.persona_name:
            author = f"{msg.author_name} [{msg.persona_name}]"

        # Add metadata hints
        metadata = []
        if msg.reply_to_id:
            metadata.append("reply")
        if msg.has_attachments:
            attachment_desc = ", ".join(msg.attachment_types[:2])
            metadata.append(f"attached: {attachment_desc}")

        metadata_str = f" ({', '.join(metadata)})" if metadata else ""

        formatted.append(f"[{timestamp_str}] {author}: {msg.content}{metadata_str}")

    return "\n".join(formatted)


def build_enhanced_query(
    query: str,
    context_messages: list[ConversationMessage],
    router_reasoning: str | None = None,
    selection_type: str = "router",
) -> str:
    """Build enhanced query with conversation context.

    Args:
        query: The user's query
        context_messages: Router-selected context messages
        router_reasoning: Router's reasoning for choosing this persona/context
        selection_type: How this persona was selected ("router", "mention", or "fallback")

    Returns:
        Enhanced query with context
    """
    parts = []

    # Add router reasoning if available
    if router_reasoning:
        parts.append("<router_reasoning>")
        parts.append(
            f"You were selected by the conversation router because: {router_reasoning}"
        )
        parts.append(f"Selection type: {selection_type}")
        parts.append("</router_reasoning>")
        parts.append("")

    # Add conversation context if available
    if context_messages:
        context_str = format_context_messages(context_messages)
        parts.append("<conversation_context>")
        parts.append(context_str)
        parts.append("</conversation_context>")
        parts.append("")

    parts.append("<current_message>")
    parts.append(query)
    parts.append("</current_message>")
    parts.append("")

    instruction = "Respond to the current message"
    if router_reasoning:
        instruction += ", keeping in mind the router's reasoning for selecting you"
    if context_messages:
        instruction += ", using the conversation context to inform your response"
    instruction += "."

    parts.append(instruction)

    return "\n".join(parts)
