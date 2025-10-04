"""Tests for conversation threading functionality."""

from datetime import datetime, UTC

from discord_hack.conversation_store import (
    ConversationMessage,
    ConversationStore,
)


def create_test_message(
    msg_id: str,
    content: str,
    channel_id: str = "test_channel",
    author_name: str = "TestUser",
) -> ConversationMessage:
    """Helper to create test messages."""
    return ConversationMessage(
        id=msg_id,
        author_name=author_name,
        author_id="user123",
        content=content,
        timestamp=datetime.now(UTC),
        channel_id=channel_id,
        is_bot=False,
        persona_name=None,
        reply_to_id=None,
        mentions_user_ids=[],
        has_attachments=False,
        attachment_types=[],
        has_embeds=False,
    )


class TestMultipleConversations:
    """Tests for managing multiple conversations per channel."""

    def test_multiple_conversations_in_same_channel(self) -> None:
        """Test that multiple conversations can exist in the same channel."""
        store = ConversationStore()

        # Create first conversation
        msg1 = create_test_message("1", "Let's discuss architecture")
        conv1 = store.create_conversation("channel1", msg1)

        # Create second conversation
        msg2 = create_test_message("2", "Different topic: database setup")
        conv2 = store.create_conversation("channel1", msg2)

        # Both should exist
        active_convs = store.get_active_conversations("channel1")
        assert len(active_convs) == 2
        assert conv1.id in [c.id for c in active_convs]
        assert conv2.id in [c.id for c in active_convs]

    def test_conversation_topic_summaries(self) -> None:
        """Test that conversations can have topic summaries."""
        store = ConversationStore()
        msg = create_test_message("1", "How do we handle auth?")
        conv = store.create_conversation("channel1", msg)

        # Set topic summary
        conv.topic_summary = "Authentication implementation discussion"

        # Verify it's stored
        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None
        assert retrieved.topic_summary == "Authentication implementation discussion"

    def test_messages_added_to_correct_conversation(self) -> None:
        """Test that messages are added to the correct conversation thread."""
        store = ConversationStore()

        # Create two conversations
        msg1 = create_test_message("1", "Architecture topic")
        conv1 = store.create_conversation("channel1", msg1)
        conv1.topic_summary = "Architecture"

        msg2 = create_test_message("2", "Database topic")
        conv2 = store.create_conversation("channel1", msg2)
        conv2.topic_summary = "Database"

        # Add message to first conversation
        msg3 = create_test_message("3", "More about architecture")
        store.add_message(conv1.id, msg3)

        # Add message to second conversation
        msg4 = create_test_message("4", "More about database")
        store.add_message(conv2.id, msg4)

        # Verify messages are in correct conversations
        retrieved_conv1 = store.get_conversation(conv1.id)
        assert retrieved_conv1 is not None
        assert len(retrieved_conv1.messages) == 2
        assert retrieved_conv1.messages[0].content == "Architecture topic"
        assert retrieved_conv1.messages[1].content == "More about architecture"

        retrieved_conv2 = store.get_conversation(conv2.id)
        assert retrieved_conv2 is not None
        assert len(retrieved_conv2.messages) == 2
        assert retrieved_conv2.messages[0].content == "Database topic"
        assert retrieved_conv2.messages[1].content == "More about database"

    def test_conversation_isolation_between_channels(self) -> None:
        """Test that conversations in different channels are isolated."""
        store = ConversationStore()

        # Create conversations in different channels
        msg1 = create_test_message("1", "Channel 1 topic", channel_id="channel1")
        conv1 = store.create_conversation("channel1", msg1)

        msg2 = create_test_message("2", "Channel 2 topic", channel_id="channel2")
        conv2 = store.create_conversation("channel2", msg2)

        # Check isolation
        channel1_convs = store.get_active_conversations("channel1")
        channel2_convs = store.get_active_conversations("channel2")

        assert len(channel1_convs) == 1
        assert len(channel2_convs) == 1
        assert channel1_convs[0].id == conv1.id
        assert channel2_convs[0].id == conv2.id


class TestConversationRouting:
    """Tests for routing messages to appropriate conversations."""

    def test_get_conversation_by_id(self) -> None:
        """Test retrieving specific conversation by ID."""
        store = ConversationStore()

        msg = create_test_message("1", "Test message")
        conv = store.create_conversation("channel1", msg)

        # Should be able to retrieve by ID
        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None
        assert retrieved.id == conv.id
        assert retrieved.messages[0].content == "Test message"

    def test_get_conversation_returns_none_for_invalid_id(self) -> None:
        """Test that invalid conversation ID returns None."""
        store = ConversationStore()
        retrieved = store.get_conversation("invalid_id")
        assert retrieved is None

    def test_conversation_last_active_updates(self) -> None:
        """Test that last_active updates when messages added."""
        store = ConversationStore()

        msg1 = create_test_message("1", "Initial message")
        conv = store.create_conversation("channel1", msg1)
        initial_time = conv.last_active

        # Wait briefly
        import time

        time.sleep(0.01)

        # Add another message
        msg2 = create_test_message("2", "Follow-up message")
        store.add_message(conv.id, msg2)

        # last_active should be updated
        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None
        assert retrieved.last_active > initial_time


class TestConversationContextSelection:
    """Tests for selecting context messages from conversations."""

    def test_context_from_specific_conversation(self) -> None:
        """Test that context messages come from the correct conversation."""
        store = ConversationStore()

        # Create two conversations with different topics
        msg1 = create_test_message("1", "Architecture: Use microservices")
        conv1 = store.create_conversation("channel1", msg1)

        msg2 = create_test_message("2", "Database: Use PostgreSQL")
        conv2 = store.create_conversation("channel1", msg2)

        # Add more messages to each
        msg3 = create_test_message("3", "Architecture: Add API gateway")
        store.add_message(conv1.id, msg3)

        msg4 = create_test_message("4", "Database: Add indexes")
        store.add_message(conv2.id, msg4)

        # Get messages from first conversation only
        conv1_retrieved = store.get_conversation(conv1.id)
        assert conv1_retrieved is not None
        conv1_messages = conv1_retrieved.messages

        # Should only have architecture messages
        assert len(conv1_messages) == 2
        assert all("Architecture" in msg.content for msg in conv1_messages)
        assert not any("Database" in msg.content for msg in conv1_messages)

    def test_get_recent_messages_respects_limit(self) -> None:
        """Test that get_recent_messages respects the limit parameter."""
        store = ConversationStore()

        msg1 = create_test_message("1", "Message 1")
        conv = store.create_conversation("channel1", msg1)

        # Add 10 more messages
        for i in range(2, 12):
            msg = create_test_message(str(i), f"Message {i}")
            store.add_message(conv.id, msg)

        # Get conversation and check recent messages
        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None

        # Should get last 5 messages
        recent = retrieved.get_recent_messages(limit=5)
        assert len(recent) == 5
        assert recent[-1].content == "Message 11"
        assert recent[0].content == "Message 7"
