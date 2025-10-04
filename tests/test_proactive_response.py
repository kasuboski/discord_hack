"""Tests for proactive interjection functionality."""

import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from discord_hack.conversation_store import ConversationMessage
from discord_hack.discord_bot import AITeamBot
from discord_hack.router import RouterDecision


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    bot = AITeamBot(default_knowledge_base="kbs/default.txt")
    bot.conversation_store = MagicMock()
    bot.config = MagicMock()
    bot.config.personas = []
    bot.webhook_manager = AsyncMock()
    bot.agent = AsyncMock()
    return bot


@pytest.fixture
def sample_message():
    """Create a sample conversation message."""
    return ConversationMessage(
        id="123456",
        author_name="TestUser",
        author_id="789012",
        content="I'm stuck on this authentication bug",
        timestamp=datetime.datetime.now(datetime.UTC),
        channel_id="123456789",
        is_bot=False,
        persona_name=None,
        reply_to_id=None,
        mentions_user_ids=[],
        has_attachments=False,
        attachment_types=[],
        has_embeds=False,
    )


@pytest.fixture
def router_decision_proactive():
    """Create a router decision for proactive interjection."""
    return RouterDecision(
        should_respond=True,
        conversation_id=None,
        suggested_persona="DevMike",
        relevant_message_ids=[],
        confidence=0.8,
        reasoning="User is asking for help with a technical bug, DevMike can assist",
        topic_summary="Authentication bug help request",
    )


@pytest.fixture
def router_decision_no_response():
    """Create a router decision for no response."""
    return RouterDecision(
        should_respond=False,
        conversation_id=None,
        suggested_persona=None,
        relevant_message_ids=[],
        confidence=0.9,
        reasoning="This is a personal message between users, bot should not respond",
        topic_summary="Personal conversation",
    )


@pytest.mark.asyncio
async def test_proactive_interjection_should_respond(
    mock_bot, sample_message, router_decision_proactive
):
    """Test that bot responds proactively when router says should_respond=True."""
    # Mock dependencies
    mock_bot.conversation_store.get_active_conversations.return_value = []
    mock_bot.conversation_store.create_conversation.return_value = MagicMock()

    # Mock persona config
    mock_persona = MagicMock()
    mock_persona.name = "DevMike"
    mock_bot.config.get_persona_by_name.return_value = mock_persona

    # Mock router agent
    with patch("discord_hack.discord_bot.get_router_agent") as mock_get_router:
        mock_router = AsyncMock()
        mock_get_router.return_value = mock_router
        mock_router.run.return_value = MagicMock(output=router_decision_proactive)

        # Mock _respond_as_persona
        mock_bot._respond_as_persona = AsyncMock()

        # Call the method
        await mock_bot._handle_message_with_router(
            conv_message=sample_message,
            explicit_persona=None,
            is_mentioned=False,
            mention_string=None,
        )

        # Verify router was called
        mock_router.run.assert_called_once()

        # Verify conversation was created
        mock_bot.conversation_store.create_conversation.assert_called_once()

        # Verify response was sent
        mock_bot._respond_as_persona.assert_called_once()


@pytest.mark.asyncio
async def test_proactive_interjection_no_response(
    mock_bot, sample_message, router_decision_no_response
):
    """Test that bot doesn't respond when router says should_respond=False."""
    # Mock dependencies
    mock_bot.conversation_store.get_active_conversations.return_value = []
    mock_bot.conversation_store.create_conversation.return_value = MagicMock()

    # Mock router agent
    with patch("discord_hack.discord_bot.get_router_agent") as mock_get_router:
        mock_router = AsyncMock()
        mock_get_router.return_value = mock_router
        mock_router.run.return_value = MagicMock(output=router_decision_no_response)

        # Mock _respond_as_persona (should not be called)
        mock_bot._respond_as_persona = AsyncMock()

        # Call the method
        await mock_bot._handle_message_with_router(
            conv_message=sample_message,
            explicit_persona=None,
            is_mentioned=False,
            mention_string=None,
        )

        # Verify router was called
        mock_router.run.assert_called_once()

        # Verify conversation was still created for context
        mock_bot.conversation_store.create_conversation.assert_called_once()

        # Verify no response was sent
        mock_bot._respond_as_persona.assert_not_called()


@pytest.mark.asyncio
async def test_explicit_mention_overrides_should_respond_false(
    mock_bot, sample_message, router_decision_no_response
):
    """Test that explicit mentions override should_respond=False (safety)."""
    # Mock dependencies
    mock_bot.conversation_store.get_active_conversations.return_value = []
    mock_bot.conversation_store.create_conversation.return_value = MagicMock()

    # Mock persona config
    mock_persona = MagicMock()
    mock_persona.name = "JohnPM"

    # Mock router agent
    with patch("discord_hack.discord_bot.get_router_agent") as mock_get_router:
        mock_router = AsyncMock()
        mock_get_router.return_value = mock_router
        mock_router.run.return_value = MagicMock(output=router_decision_no_response)

        # Mock _respond_as_persona (should be called after safety override)
        mock_bot._respond_as_persona = AsyncMock()

        # Call the method with explicit persona mention
        await mock_bot._handle_message_with_router(
            conv_message=sample_message,
            explicit_persona=mock_persona,
            is_mentioned=True,
            mention_string=None,
        )

        # Verify router was called
        mock_router.run.assert_called_once()

        # Verify safety override triggered response despite should_respond=False
        mock_bot._respond_as_persona.assert_called_once()


@pytest.mark.asyncio
async def test_bot_mention_overrides_should_respond_false(
    mock_bot, sample_message, router_decision_no_response
):
    """Test that bot mentions override should_respond=False (safety)."""
    # Mock dependencies
    mock_bot.conversation_store.get_active_conversations.return_value = []
    mock_bot.conversation_store.create_conversation.return_value = MagicMock()

    # Mock router agent
    with patch("discord_hack.discord_bot.get_router_agent") as mock_get_router:
        mock_router = AsyncMock()
        mock_get_router.return_value = mock_router
        mock_router.run.return_value = MagicMock(output=router_decision_no_response)

        # Mock _respond_as_default (should be called after safety override)
        mock_bot._respond_as_default = AsyncMock()

        # Call the method with bot mention
        await mock_bot._handle_message_with_router(
            conv_message=sample_message,
            explicit_persona=None,
            is_mentioned=True,
            mention_string="<@123456789>",
        )

        # Verify router was called
        mock_router.run.assert_called_once()

        # Verify safety override triggered response despite should_respond=False
        mock_bot._respond_as_default.assert_called_once()


@pytest.mark.asyncio
async def test_router_error_fallback_for_mentions(mock_bot, sample_message):
    """Test that router errors still allow responses for explicit mentions."""
    # Mock dependencies
    mock_bot.conversation_store.get_active_conversations.return_value = []

    # Mock router agent to raise exception
    with patch("discord_hack.discord_bot.get_router_agent") as mock_get_router:
        mock_router = AsyncMock()
        mock_get_router.return_value = mock_router
        mock_router.run.side_effect = Exception("Router error")

        # Mock _handle_router_error_fallback
        mock_bot._handle_router_error_fallback = AsyncMock()

        # Call the method with explicit mention
        mock_persona = MagicMock()
        await mock_bot._handle_message_with_router(
            conv_message=sample_message,
            explicit_persona=mock_persona,
            is_mentioned=True,
            mention_string=None,
        )

        # Verify fallback was called for explicit mention
        mock_bot._handle_router_error_fallback.assert_called_once_with(
            sample_message, mock_persona
        )


@pytest.mark.asyncio
async def test_router_error_no_fallback_for_proactive(mock_bot, sample_message):
    """Test that router errors don't trigger responses in proactive mode."""
    # Mock dependencies
    mock_bot.conversation_store.get_active_conversations.return_value = []

    # Mock router agent to raise exception
    with patch("discord_hack.discord_bot.get_router_agent") as mock_get_router:
        mock_router = AsyncMock()
        mock_get_router.return_value = mock_router
        mock_router.run.side_effect = Exception("Router error")

        # Mock _handle_router_error_fallback (should not be called)
        mock_bot._handle_router_error_fallback = AsyncMock()

        # Call the method without explicit mention (proactive mode)
        await mock_bot._handle_message_with_router(
            conv_message=sample_message,
            explicit_persona=None,
            is_mentioned=False,
            mention_string=None,
        )

        # Verify fallback was NOT called for proactive mode
        mock_bot._handle_router_error_fallback.assert_not_called()
