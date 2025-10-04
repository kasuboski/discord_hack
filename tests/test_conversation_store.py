"""Tests for conversation store functionality."""

from datetime import datetime, timedelta, UTC
from unittest.mock import Mock

import discord
import pytest

from discord_hack.conversation_store import (
    ConversationMessage,
    ConversationStore,
    ConversationThread,
)


@pytest.fixture
def mock_discord_message() -> Mock:
    """Create a mock Discord message for testing."""
    message = Mock(spec=discord.Message)
    message.id = 123456789
    message.author.display_name = "TestUser"
    message.author.id = 987654321
    message.author.bot = False
    message.content = "Test message content"
    message.created_at = datetime.now(UTC)
    message.channel.id = 111222333
    message.reference = None
    message.mentions = []
    message.attachments = []
    message.embeds = []
    return message


@pytest.fixture
def sample_conv_message() -> ConversationMessage:
    """Create a sample ConversationMessage for testing."""
    return ConversationMessage(
        id="123456789",
        author_name="TestUser",
        author_id="987654321",
        content="Test message content",
        timestamp=datetime.now(UTC),
        channel_id="111222333",
        is_bot=False,
        persona_name=None,
        reply_to_id=None,
        mentions_user_ids=[],
        has_attachments=False,
        attachment_types=[],
        has_embeds=False,
    )


class TestConversationMessage:
    """Tests for ConversationMessage model."""

    def test_from_discord_message_basic(self, mock_discord_message: Mock) -> None:
        """Test basic conversion from Discord message."""
        conv_msg = ConversationMessage.from_discord_message(mock_discord_message)

        assert conv_msg.id == "123456789"
        assert conv_msg.author_name == "TestUser"
        assert conv_msg.author_id == "987654321"
        assert conv_msg.content == "Test message content"
        assert conv_msg.channel_id == "111222333"
        assert conv_msg.is_bot is False
        assert conv_msg.persona_name is None

    def test_from_discord_message_with_persona(
        self, mock_discord_message: Mock
    ) -> None:
        """Test conversion with persona name."""
        conv_msg = ConversationMessage.from_discord_message(
            mock_discord_message, persona_name="JohnPM"
        )

        assert conv_msg.persona_name == "JohnPM"

    def test_from_discord_message_with_reply(self, mock_discord_message: Mock) -> None:
        """Test conversion with reply reference."""
        mock_reference = Mock()
        mock_reference.message_id = 111111111
        mock_discord_message.reference = mock_reference

        conv_msg = ConversationMessage.from_discord_message(mock_discord_message)

        assert conv_msg.reply_to_id == "111111111"

    def test_from_discord_message_with_mentions(
        self, mock_discord_message: Mock
    ) -> None:
        """Test conversion with user mentions."""
        mock_user1 = Mock()
        mock_user1.id = 555555555
        mock_user2 = Mock()
        mock_user2.id = 666666666
        mock_discord_message.mentions = [mock_user1, mock_user2]

        conv_msg = ConversationMessage.from_discord_message(mock_discord_message)

        assert conv_msg.mentions_user_ids == ["555555555", "666666666"]

    def test_from_discord_message_with_attachments(
        self, mock_discord_message: Mock
    ) -> None:
        """Test conversion with attachments."""
        mock_attachment1 = Mock()
        mock_attachment1.content_type = "image/png"
        mock_attachment2 = Mock()
        mock_attachment2.content_type = "application/pdf"
        mock_discord_message.attachments = [mock_attachment1, mock_attachment2]

        conv_msg = ConversationMessage.from_discord_message(mock_discord_message)

        assert conv_msg.has_attachments is True
        assert conv_msg.attachment_types == ["image/png", "application/pdf"]

    def test_from_discord_message_with_embeds(self, mock_discord_message: Mock) -> None:
        """Test conversion with embeds."""
        mock_discord_message.embeds = [Mock()]

        conv_msg = ConversationMessage.from_discord_message(mock_discord_message)

        assert conv_msg.has_embeds is True


class TestConversationThread:
    """Tests for ConversationThread model."""

    def test_get_recent_messages(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test getting recent messages with limit."""
        # Create thread with multiple messages
        thread = ConversationThread(
            id="conv_1",
            channel_id="111222333",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            messages=[sample_conv_message] * 30,  # 30 identical messages for testing
        )

        recent = thread.get_recent_messages(limit=10)
        assert len(recent) == 10

    def test_get_recent_messages_fewer_than_limit(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test getting recent messages when fewer than limit exist."""
        thread = ConversationThread(
            id="conv_1",
            channel_id="111222333",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            messages=[sample_conv_message] * 5,
        )

        recent = thread.get_recent_messages(limit=10)
        assert len(recent) == 5

    def test_is_stale_active_conversation(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test that recent conversation is not stale."""
        thread = ConversationThread(
            id="conv_1",
            channel_id="111222333",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            messages=[sample_conv_message],
        )

        assert thread.is_stale(threshold_minutes=30) is False

    def test_is_stale_inactive_conversation(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test that old conversation is stale."""
        thread = ConversationThread(
            id="conv_1",
            channel_id="111222333",
            created_at=datetime.now(UTC) - timedelta(hours=2),
            last_active=datetime.now(UTC) - timedelta(hours=2),
            messages=[sample_conv_message],
        )

        assert thread.is_stale(threshold_minutes=30) is True

    def test_get_message_by_id_found(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test finding message by ID."""
        thread = ConversationThread(
            id="conv_1",
            channel_id="111222333",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            messages=[sample_conv_message],
        )

        found = thread.get_message_by_id("123456789")
        assert found is not None
        assert found.id == "123456789"

    def test_get_message_by_id_not_found(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test message not found by ID."""
        thread = ConversationThread(
            id="conv_1",
            channel_id="111222333",
            created_at=datetime.now(UTC),
            last_active=datetime.now(UTC),
            messages=[sample_conv_message],
        )

        found = thread.get_message_by_id("999999999")
        assert found is None


class TestConversationStore:
    """Tests for ConversationStore."""

    def test_create_conversation(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test creating a new conversation."""
        store = ConversationStore()
        conv = store.create_conversation("111222333", sample_conv_message)

        assert conv.channel_id == "111222333"
        assert len(conv.messages) == 1
        assert conv.messages[0] == sample_conv_message

    def test_get_conversation(self, sample_conv_message: ConversationMessage) -> None:
        """Test retrieving a conversation by ID."""
        store = ConversationStore()
        conv = store.create_conversation("111222333", sample_conv_message)

        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None
        assert retrieved.id == conv.id

    def test_get_conversation_not_found(self) -> None:
        """Test retrieving non-existent conversation."""
        store = ConversationStore()
        retrieved = store.get_conversation("nonexistent")
        assert retrieved is None

    def test_add_message_to_conversation(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test adding message to existing conversation."""
        store = ConversationStore()
        conv = store.create_conversation("111222333", sample_conv_message)

        # Create second message
        msg2 = ConversationMessage(
            id="987654321",
            author_name="TestUser2",
            author_id="123456789",
            content="Second message",
            timestamp=datetime.now(UTC),
            channel_id="111222333",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        )

        store.add_message(conv.id, msg2)

        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None
        assert len(retrieved.messages) == 2

    def test_add_message_updates_last_active(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test that adding message updates last_active timestamp."""
        store = ConversationStore()
        conv = store.create_conversation("111222333", sample_conv_message)
        original_time = conv.last_active

        # Wait a tiny bit to ensure timestamp difference
        import time

        time.sleep(0.01)

        # Add another message
        msg2 = ConversationMessage(
            id="987654321",
            author_name="TestUser2",
            author_id="123456789",
            content="Second message",
            timestamp=datetime.now(UTC),
            channel_id="111222333",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        )

        store.add_message(conv.id, msg2)

        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None
        assert retrieved.last_active > original_time

    def test_get_active_conversations(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test getting active conversations for a channel."""
        store = ConversationStore()
        conv1 = store.create_conversation("111222333", sample_conv_message)

        active = store.get_active_conversations("111222333")
        assert len(active) == 1
        assert active[0].id == conv1.id

    def test_get_active_conversations_filters_stale(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test that stale conversations are filtered out."""
        store = ConversationStore()
        conv = store.create_conversation("111222333", sample_conv_message)

        # Make conversation stale by setting old last_active
        conv.last_active = datetime.now(UTC) - timedelta(hours=2)

        active = store.get_active_conversations("111222333")
        assert len(active) == 0

    def test_get_or_create_conversation_creates_new(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test get_or_create creates new conversation when none exist."""
        store = ConversationStore()
        conv = store.get_or_create_conversation("111222333", sample_conv_message)

        assert conv.channel_id == "111222333"
        assert len(conv.messages) == 1

    def test_get_or_create_conversation_uses_existing(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test get_or_create uses existing active conversation."""
        store = ConversationStore()
        conv1 = store.create_conversation("111222333", sample_conv_message)

        # Create second message
        msg2 = ConversationMessage(
            id="987654321",
            author_name="TestUser2",
            author_id="123456789",
            content="Second message",
            timestamp=datetime.now(UTC),
            channel_id="111222333",
            is_bot=False,
            persona_name=None,
            reply_to_id=None,
            mentions_user_ids=[],
            has_attachments=False,
            attachment_types=[],
            has_embeds=False,
        )

        conv2 = store.get_or_create_conversation("111222333", msg2)

        # Should be same conversation
        assert conv2.id == conv1.id
        assert len(conv2.messages) == 2

    def test_message_trimming(self, sample_conv_message: ConversationMessage) -> None:
        """Test that messages are trimmed when exceeding max limit."""
        store = ConversationStore(max_messages_per_conversation=10)
        conv = store.create_conversation("111222333", sample_conv_message)

        # Add 15 more messages (16 total, should trim to 10)
        for i in range(15):
            msg = ConversationMessage(
                id=f"msg_{i}",
                author_name=f"User{i}",
                author_id=f"{i}",
                content=f"Message {i}",
                timestamp=datetime.now(UTC),
                channel_id="111222333",
                is_bot=False,
                persona_name=None,
                reply_to_id=None,
                mentions_user_ids=[],
                has_attachments=False,
                attachment_types=[],
                has_embeds=False,
            )
            store.add_message(conv.id, msg)

        retrieved = store.get_conversation(conv.id)
        assert retrieved is not None
        assert len(retrieved.messages) == 10
        # Should keep most recent messages
        assert retrieved.messages[-1].id == "msg_14"

    def test_conversation_cleanup(
        self, sample_conv_message: ConversationMessage
    ) -> None:
        """Test that old stale conversations are cleaned up."""
        store = ConversationStore(max_conversations=5)

        # Create 10 conversations, make first 8 stale
        for i in range(10):
            conv = store.create_conversation(f"channel_{i}", sample_conv_message)
            if i < 8:
                # Make first 8 stale
                conv.last_active = datetime.now(UTC) - timedelta(hours=2)

        # Should have cleaned up some stale conversations
        # At least the most recent conversations should remain
        assert len(store.conversations) <= 5
