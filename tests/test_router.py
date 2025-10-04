"""Tests for router helper functions."""

from datetime import datetime, UTC

from discord_hack.conversation_store import ConversationMessage, ConversationThread
from discord_hack.router import (
    RouterDecision,
    extract_context_messages,
    get_context_messages_by_ids,
    normalize_message_ids,
)


def test_normalize_message_ids_filters_invalid():
    """Test that normalize_message_ids filters out null/none/empty strings."""
    input_ids = ["123", "null", "456", "none", "", "789", "NULL", "None"]
    expected = ["123", "456", "789"]

    result = normalize_message_ids(input_ids)

    assert result == expected


def test_normalize_message_ids_empty_list():
    """Test normalize_message_ids with empty input."""
    result = normalize_message_ids([])
    assert result == []


def test_normalize_message_ids_all_invalid():
    """Test normalize_message_ids when all IDs are invalid."""
    input_ids = ["null", "none", "", "NULL", "None"]
    result = normalize_message_ids(input_ids)
    assert result == []


def test_get_context_messages_by_ids_all_found():
    """Test get_context_messages_by_ids when all messages exist."""
    # Create test messages
    messages = [
        ConversationMessage(
            id="1",
            author_name="Alice",
            author_id="u1",
            content="First message",
            timestamp=datetime.now(UTC),
            channel_id="c1",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        ),
        ConversationMessage(
            id="2",
            author_name="Bob",
            author_id="u2",
            content="Second message",
            timestamp=datetime.now(UTC),
            channel_id="c1",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        ),
        ConversationMessage(
            id="3",
            author_name="Charlie",
            author_id="u3",
            content="Third message",
            timestamp=datetime.now(UTC),
            channel_id="c1",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        ),
    ]

    conversation = ConversationThread(
        id="conv1",
        channel_id="c1",
        created_at=datetime.now(UTC),
        last_active=datetime.now(UTC),
        messages=messages,
        topic_summary=None,
    )

    found, missing = get_context_messages_by_ids(conversation, ["1", "3"])

    assert len(found) == 2
    assert found[0].id == "1"
    assert found[1].id == "3"
    assert missing == []


def test_get_context_messages_by_ids_some_missing():
    """Test get_context_messages_by_ids when some IDs don't exist."""
    messages = [
        ConversationMessage(
            id="1",
            author_name="Alice",
            author_id="u1",
            content="First message",
            timestamp=datetime.now(UTC),
            channel_id="c1",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        ),
    ]

    conversation = ConversationThread(
        id="conv1",
        channel_id="c1",
        created_at=datetime.now(UTC),
        last_active=datetime.now(UTC),
        messages=messages,
        topic_summary=None,
    )

    found, missing = get_context_messages_by_ids(conversation, ["1", "2", "3"])

    assert len(found) == 1
    assert found[0].id == "1"
    assert set(missing) == {"2", "3"}


def test_get_context_messages_by_ids_empty_conversation():
    """Test get_context_messages_by_ids with empty conversation."""
    conversation = ConversationThread(
        id="conv1",
        channel_id="c1",
        created_at=datetime.now(UTC),
        last_active=datetime.now(UTC),
        messages=[],
        topic_summary=None,
    )

    found, missing = get_context_messages_by_ids(conversation, ["1", "2"])

    assert found == []
    assert set(missing) == {"1", "2"}


def test_extract_context_messages_full_flow():
    """Test extract_context_messages end-to-end with RouterDecision."""
    messages = [
        ConversationMessage(
            id="1",
            author_name="Alice",
            author_id="u1",
            content="First message",
            timestamp=datetime.now(UTC),
            channel_id="c1",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        ),
        ConversationMessage(
            id="2",
            author_name="Bob",
            author_id="u2",
            content="Second message",
            timestamp=datetime.now(UTC),
            channel_id="c1",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        ),
    ]

    conversation = ConversationThread(
        id="conv1",
        channel_id="c1",
        created_at=datetime.now(UTC),
        last_active=datetime.now(UTC),
        messages=messages,
        topic_summary=None,
    )

    # Router decision with some valid and invalid IDs
    decision = RouterDecision(
        should_respond=True,
        conversation_id="conv1",
        suggested_persona="JohnPM",
        relevant_message_ids=["1", "null", "2", "none", "999"],  # Mix of valid/invalid
        confidence=0.9,
        reasoning="Test reasoning",
        topic_summary="Test topic",
    )

    context = extract_context_messages(conversation, decision, strict=False)

    # Should get messages 1 and 2, ignoring null/none/999
    assert len(context) == 2
    assert context[0].id == "1"
    assert context[1].id == "2"


def test_extract_context_messages_no_valid_ids():
    """Test extract_context_messages when all IDs are invalid."""
    conversation = ConversationThread(
        id="conv1",
        channel_id="c1",
        created_at=datetime.now(UTC),
        last_active=datetime.now(UTC),
        messages=[],
        topic_summary=None,
    )

    decision = RouterDecision(
        should_respond=True,
        conversation_id="conv1",
        suggested_persona="JohnPM",
        relevant_message_ids=["null", "none", ""],
        confidence=0.5,
        reasoning="No context",
        topic_summary="Test",
    )

    context = extract_context_messages(conversation, decision)

    assert context == []


def test_extract_context_messages_strict_mode_raises():
    """Test extract_context_messages raises ValueError in strict mode when IDs missing."""
    messages = [
        ConversationMessage(
            id="1",
            author_name="Alice",
            author_id="u1",
            content="First message",
            timestamp=datetime.now(UTC),
            channel_id="c1",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        ),
    ]

    conversation = ConversationThread(
        id="conv1",
        channel_id="c1",
        created_at=datetime.now(UTC),
        last_active=datetime.now(UTC),
        messages=messages,
        topic_summary=None,
    )

    decision = RouterDecision(
        should_respond=True,
        conversation_id="conv1",
        suggested_persona="JohnPM",
        relevant_message_ids=["1", "999"],  # 999 doesn't exist
        confidence=0.9,
        reasoning="Test",
        topic_summary="Test",
    )

    # strict=False should succeed with partial results
    context = extract_context_messages(conversation, decision, strict=False)
    assert len(context) == 1
    assert context[0].id == "1"

    # strict=True should raise ValueError
    import pytest

    with pytest.raises(ValueError, match="message IDs not found"):
        extract_context_messages(conversation, decision, strict=True)
