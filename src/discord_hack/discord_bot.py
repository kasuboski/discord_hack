"""Discord bot client implementation."""

from __future__ import annotations

import logging
import os
import re

import discord

from .agent import get_agent, get_persona_agent, get_router_agent
from .config import get_config, PersonaConfig
from .conversation_store import (
    ConversationMessage,
    ConversationThread,
    get_conversation_store,
)
from .dependencies import Deps
from .persona_agent import build_enhanced_query
from .router import (
    PersonaInfo,
    RouterContext,
    extract_context_messages,
    build_router_prompt,
)
from .webhook_manager import get_webhook_manager

logger = logging.getLogger(__name__)


class AITeamBot(discord.Client):
    """Discord bot client for the AI Team Bot."""

    def __init__(self, default_knowledge_base: str) -> None:
        """Initialize the bot with required intents and default knowledge base."""
        # Set up intents - we need message content to read the actual message text
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(intents=intents)

        self.agent = get_agent()
        self.default_knowledge_base = default_knowledge_base
        self.config = get_config()
        self.webhook_manager = get_webhook_manager()
        self.conversation_store = get_conversation_store()

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        assert self.user is not None
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")

    def bot_mentioned(self, message: discord.Message) -> str | None:
        """Check if the bot was mentioned and return the mention string if found.

        This function checks for both direct user mentions (<@USER_ID>) and role
        mentions (<@&ROLE_ID>) where the bot is a member of the mentioned role.

        Args:
            message: The Discord message to check for bot mentions.

        Returns:
            The mention string that triggered the bot (e.g., '<@123456>' for user
            mentions or '<@&789012>' for role mentions), or None if the bot was
            not mentioned.

        Note:
            Role mentions are only checked in guild (server) messages, not in DMs.
        """
        if not self.user:
            return None

        # Check for direct user mention
        if self.user.mentioned_in(message):
            return self.user.mention

        # Check for role mention (only possible in a guild)
        if message.guild:
            bot_member = message.guild.get_member(self.user.id)
            if bot_member:
                # Check if any of the mentioned roles are roles the bot has
                for role in message.role_mentions:
                    if role in bot_member.roles:
                        return role.mention

        return None

    def detect_persona_mention(self, content: str) -> PersonaConfig | None:
        """Check if a persona was mentioned and return the persona config.

        Args:
            content: The message content to check for persona mentions.

        Returns:
            The PersonaConfig for the mentioned persona, or None if no persona was mentioned.
        """
        # Check for @PersonaName mentions in the message content
        for persona in self.config.personas:
            # Look for @PersonaName mentions (case-insensitive)
            pattern = rf"@{re.escape(persona.name)}\b"
            if re.search(pattern, content, re.IGNORECASE):
                return persona

        return None

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages.

        Router runs on ALL messages and decides whether to respond.
        """
        # Ignore messages from bots to prevent infinite loops
        if message.author.bot:
            return

        logger.debug(f"Received message: {message.content}")

        # Convert Discord message to internal format (boundary conversion)
        conv_message = ConversationMessage.from_discord_message(message)

        # Check for persona mentions first (safety override)
        persona_config = self.detect_persona_mention(message.content)
        explicit_mention = persona_config is not None

        # Check if the bot was mentioned (safety override)
        mention_string = self.bot_mentioned(message)
        bot_mentioned = mention_string is not None

        # Router runs on EVERY message to analyze conversation context
        await self._handle_message_with_router(
            conv_message,
            explicit_persona=persona_config,
            is_mentioned=explicit_mention or bot_mentioned,
            mention_string=mention_string,
        )

    async def _handle_mention(
        self, conv_message: ConversationMessage, mention_string: str
    ) -> None:
        """Handle a message that mentions the bot.

        Use router to suggest persona AND select relevant context messages.
        """
        try:
            # Extract the query by removing the specific mention string
            query = conv_message.content.replace(mention_string, "", 1).strip()

            # Handle empty queries
            if not query:
                # Fetch channel for sending response
                channel = self.get_channel(int(conv_message.channel_id))
                if not channel:
                    logger.error(f"Could not find channel {conv_message.channel_id}")
                    return

                # Ensure channel supports sending messages
                assert isinstance(channel, discord.abc.Messageable), (
                    f"Channel {conv_message.channel_id} does not support sending messages"
                )

                author_mention = f"<@{conv_message.author_id}>"
                response_msg = await channel.send(
                    f"Hello, {author_mention}! How can I help you?"
                )
                # Store bot response
                if response_msg:
                    bot_conv_message = ConversationMessage.from_discord_message(
                        response_msg, persona_name=None
                    )
                    self.conversation_store.get_or_create_conversation(
                        bot_conv_message.channel_id, bot_conv_message
                    )
                return

            # Get all active conversations for router to choose from
            active_conversations = self.conversation_store.get_active_conversations(
                conv_message.channel_id
            )

            # Prepare router context with all active conversations
            router_context = RouterContext(
                current_message=conv_message,
                active_conversations=active_conversations,
                available_personas=[
                    PersonaInfo(name=p.name, role=p.role) for p in self.config.personas
                ],
                explicit_persona=None,  # No explicit persona mention
                is_bot_mentioned=True,  # Bot was mentioned
            )

            # Get router decision (conversation routing + persona + context selection)
            router_agent = get_router_agent()

            # Build prompt with all active conversations for router
            router_prompt = build_router_prompt(conv_message, active_conversations)
            decision = await router_agent.run(
                router_prompt,
                deps=router_context,
            )

            logger.info(f"Router decision: {decision.output.reasoning}")
            logger.info(f"Router conversation: {decision.output.conversation_id}")
            logger.info(f"Suggested persona: {decision.output.suggested_persona}")
            logger.info(f"Confidence: {decision.output.confidence:.2f}")

            # Get or create conversation based on router decision
            if decision.output.conversation_id:
                # Router wants to use existing conversation
                conversation = self.conversation_store.get_conversation(
                    decision.output.conversation_id
                )
                if conversation:
                    logger.info(
                        f"Routing to existing conversation: {decision.output.conversation_id}"
                    )
                    self.conversation_store.add_message(conversation.id, conv_message)
                else:
                    # Conversation ID not found, create new one
                    logger.warning(
                        f"Router suggested conversation {decision.output.conversation_id} not found, creating new"
                    )
                    conversation = self.conversation_store.create_conversation(
                        conv_message.channel_id, conv_message
                    )
            else:
                # Router wants to create new conversation
                logger.info("Router decided to create new conversation")
                conversation = self.conversation_store.create_conversation(
                    conv_message.channel_id, conv_message
                )

            # Update topic summary from router
            if decision.output.topic_summary:
                conversation.topic_summary = decision.output.topic_summary

            # Get relevant context messages selected by router
            context_messages = extract_context_messages(
                conversation, decision.output, strict=False
            )
            logger.info(f"Using {len(context_messages)} context messages")

            # Get persona based on router suggestion
            persona_config = None
            if decision.output.suggested_persona:
                persona_config = self.config.get_persona_by_name(
                    decision.output.suggested_persona
                )

            if persona_config:
                # Use router-suggested persona with router-selected context
                logger.info(f"Using router-suggested persona: {persona_config.name}")
                await self._respond_as_persona(
                    conv_message,
                    query,
                    persona_config,
                    context_messages,
                    router_reasoning=decision.output.reasoning,
                    selection_type="router",
                )
            else:
                # No persona suggested, use default agent
                logger.info("No persona suggested, using default agent")
                deps = Deps(file_path=self.default_knowledge_base)

                # Build enhanced prompt with context
                enhanced_query = build_enhanced_query(
                    query,
                    context_messages,
                    router_reasoning=decision.output.reasoning,
                    selection_type="router",
                )
                response = await self.agent.run(enhanced_query, deps=deps)

                # Fetch channel for sending response
                channel = self.get_channel(int(conv_message.channel_id))
                if not channel:
                    logger.error(f"Could not find channel {conv_message.channel_id}")
                    return

                # Ensure channel supports sending messages
                assert isinstance(channel, discord.abc.Messageable), (
                    f"Channel {conv_message.channel_id} does not support sending messages"
                )

                response_msg = await channel.send(response.output)

                # Store bot response
                if response_msg:
                    bot_message = ConversationMessage.from_discord_message(
                        response_msg, persona_name=None
                    )
                    conversation.add_message(bot_message)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

            # Fetch channel for sending error response
            channel = self.get_channel(int(conv_message.channel_id))
            if not channel:
                logger.error(f"Could not find channel {conv_message.channel_id}")
                return

            # Ensure channel supports sending messages
            assert isinstance(channel, discord.abc.Messageable), (
                f"Channel {conv_message.channel_id} does not support sending messages"
            )

            error_msg = await channel.send(
                "I apologize, but I encountered an error processing your request. "
                + "Please try again later."
            )
            # Store error response
            if error_msg:
                error_conv_message = ConversationMessage.from_discord_message(
                    error_msg, persona_name=None
                )
                self.conversation_store.get_or_create_conversation(
                    error_conv_message.channel_id, error_conv_message
                )

    async def _respond_as_persona(
        self,
        conv_message: ConversationMessage,
        query: str,
        persona_config: PersonaConfig,
        context_messages: list[ConversationMessage] | None = None,
        router_reasoning: str | None = None,
        selection_type: str = "fallback",
    ) -> None:
        """Generate and send a response as a specific persona.

        Args:
            conv_message: Original conversation message
            query: Cleaned query text (without mentions)
            persona_config: Persona to respond as
            context_messages: Router-selected relevant context messages
        """
        try:
            # Process the query with the persona's RAG agent
            knowledge_base_path = persona_config.get_knowledge_base_path()
            deps = Deps(file_path=str(knowledge_base_path))

            # Build enhanced query with router-selected context
            enhanced_query = build_enhanced_query(
                query,
                context_messages or [],
                router_reasoning=router_reasoning,
                selection_type=selection_type,
            )

            # Get the persona-specific agent
            persona_agent = get_persona_agent(persona_config)
            response = await persona_agent.run(enhanced_query, deps=deps)

            # Fetch channel for sending response
            channel = self.get_channel(int(conv_message.channel_id))
            if not channel:
                logger.error(f"Could not find channel {conv_message.channel_id}")
                return

            # Ensure channel supports sending messages
            assert isinstance(channel, discord.abc.Messageable), (
                f"Channel {conv_message.channel_id} does not support sending messages"
            )

            # Send the response as the persona via webhook if possible
            response_msg = None
            if isinstance(channel, discord.TextChannel):
                # Get original Discord message for reply_to functionality
                original_message = await channel.fetch_message(int(conv_message.id))
                webhook_message = await self.webhook_manager.send_as_persona(
                    channel, persona_config, response.output, reply_to=original_message
                )
                if webhook_message:
                    response_msg = webhook_message
                else:
                    # Fallback to regular message if webhook fails
                    response_msg = await channel.send(
                        f"**{persona_config.display_name}** ({persona_config.role}):\n{response.output}"
                    )
            else:
                response_msg = await channel.send(
                    f"**{persona_config.display_name}** ({persona_config.role}):\n{response.output}"
                )

            # Store bot response
            if response_msg:
                bot_conv_message = ConversationMessage.from_discord_message(
                    response_msg, persona_name=persona_config.name
                )
                self.conversation_store.get_or_create_conversation(
                    bot_conv_message.channel_id, bot_conv_message
                )

        except Exception as e:
            logger.error(
                f"Error generating persona response for {persona_config.name}: {e}"
            )
            author_mention = f"<@{conv_message.author_id}>"
            error_message = (
                f"I apologize, {author_mention}, but I encountered an error "
                f"processing your request. Please try again later."
            )

            # Fetch channel for sending error response
            channel = self.get_channel(int(conv_message.channel_id))
            if not channel:
                logger.error(f"Could not find channel {conv_message.channel_id}")
                return

            # Ensure channel supports sending messages
            assert isinstance(channel, discord.abc.Messageable), (
                f"Channel {conv_message.channel_id} does not support sending messages"
            )

            # Try to send error as persona, fallback to regular message
            error_msg = None
            if isinstance(channel, discord.TextChannel):
                # Get original Discord message for reply_to functionality
                original_message = await channel.fetch_message(int(conv_message.id))
                webhook_message = await self.webhook_manager.send_as_persona(
                    channel, persona_config, error_message, reply_to=original_message
                )
                if webhook_message:
                    error_msg = webhook_message
                else:
                    error_msg = await channel.send(error_message)
            else:
                error_msg = await channel.send(error_message)

            # Store error response
            if error_msg:
                error_conv_message = ConversationMessage.from_discord_message(
                    error_msg, persona_name=persona_config.name
                )
                self.conversation_store.get_or_create_conversation(
                    error_conv_message.channel_id, error_conv_message
                )

    async def _handle_persona_mention(
        self, conv_message: ConversationMessage, persona_config: PersonaConfig
    ) -> None:
        """Handle a message that mentions a specific persona.

        Use router to select relevant context messages.
        Persona is already explicit, so router suggestion is ignored.
        """
        try:
            # Extract the query by removing the persona mention
            pattern = rf"@{re.escape(persona_config.name)}\b"
            query = re.sub(
                pattern, "", conv_message.content, flags=re.IGNORECASE
            ).strip()

            # Handle empty queries
            if not query:
                author_mention = f"<@{conv_message.author_id}>"
                response_content = (
                    f"Hello, {author_mention}! I'm {persona_config.display_name}, "
                    f"{persona_config.role}. How can I help you?"
                )

                # Fetch channel for sending response
                channel = self.get_channel(int(conv_message.channel_id))
                if not channel:
                    logger.error(f"Could not find channel {conv_message.channel_id}")
                    return

                # Ensure channel supports sending messages
                assert isinstance(channel, discord.abc.Messageable), (
                    f"Channel {conv_message.channel_id} does not support sending messages"
                )

                # Try to send as persona via webhook, fallback to normal message
                response_msg = None
                if isinstance(channel, discord.TextChannel):
                    # Get original Discord message for reply_to functionality
                    original_message = await channel.fetch_message(int(conv_message.id))
                    webhook_message = await self.webhook_manager.send_as_persona(
                        channel,
                        persona_config,
                        response_content,
                        reply_to=original_message,
                    )
                    if webhook_message:
                        response_msg = webhook_message
                    else:
                        # Fallback to regular message if webhook fails
                        response_msg = await channel.send(response_content)
                else:
                    response_msg = await channel.send(response_content)

                # Store bot response
                if response_msg:
                    bot_conv_message = ConversationMessage.from_discord_message(
                        response_msg, persona_name=persona_config.name
                    )
                    _ = self.conversation_store.get_or_create_conversation(
                        bot_conv_message.channel_id, bot_conv_message
                    )
                return

            # Get all active conversations for router to choose from
            active_conversations = self.conversation_store.get_active_conversations(
                conv_message.channel_id
            )

            # Prepare router context (persona is explicit, so router suggestion will be ignored)
            router_context = RouterContext(
                current_message=conv_message,
                active_conversations=active_conversations,
                available_personas=[
                    PersonaInfo(name=p.name, role=p.role) for p in self.config.personas
                ],
                explicit_persona=persona_config.name,  # Explicit persona mention
                is_bot_mentioned=True,
            )

            # Get router decision for conversation routing + context selection
            router_agent = get_router_agent()
            router_prompt = build_router_prompt(conv_message, active_conversations)
            decision = await router_agent.run(
                router_prompt,
                deps=router_context,
            )

            logger.info(
                f"Router decision for {persona_config.name}: {decision.output.reasoning}"
            )
            logger.info(f"Router conversation: {decision.output.conversation_id}")

            # Get or create conversation based on router decision
            if decision.output.conversation_id:
                # Router wants to use existing conversation
                conversation = self.conversation_store.get_conversation(
                    decision.output.conversation_id
                )
                if conversation:
                    logger.info(
                        f"Routing to existing conversation: {decision.output.conversation_id}"
                    )
                    self.conversation_store.add_message(conversation.id, conv_message)
                else:
                    # Conversation ID not found, create new one
                    logger.warning(
                        f"Router suggested conversation {decision.output.conversation_id} not found, creating new"
                    )
                    conversation = self.conversation_store.create_conversation(
                        conv_message.channel_id, conv_message
                    )
            else:
                # Router wants to create new conversation
                logger.info("Router decided to create new conversation")
                conversation = self.conversation_store.create_conversation(
                    conv_message.channel_id, conv_message
                )

            # Update topic summary from router
            if decision.output.topic_summary:
                conversation.topic_summary = decision.output.topic_summary

            # Get relevant context messages selected by router
            context_messages = extract_context_messages(
                conversation, decision.output, strict=False
            )
            logger.info(f"Using {len(context_messages)} context messages")

            # Use helper method to respond as persona with router-selected context
            await self._respond_as_persona(
                conv_message,
                query,
                persona_config,
                context_messages,
                router_reasoning=decision.output.reasoning,
                selection_type="mention",
            )

        except Exception as e:
            logger.error(
                f"Error processing persona mention for {persona_config.name}: {e}"
            )

            author_mention = f"<@{conv_message.author_id}>"
            error_message = (
                f"I apologize, {author_mention}, but I encountered an error "
                f"processing your request. Please try again later."
            )

            # Fetch channel for sending error response
            channel = self.get_channel(int(conv_message.channel_id))
            if not channel:
                logger.error(f"Could not find channel {conv_message.channel_id}")
                return

            # Ensure channel supports sending messages
            assert isinstance(channel, discord.abc.Messageable), (
                f"Channel {conv_message.channel_id} does not support sending messages"
            )

            # Try to send error as persona, fallback to regular message
            error_msg = None
            if isinstance(channel, discord.TextChannel):
                # Get original Discord message for reply_to functionality
                original_message = await channel.fetch_message(int(conv_message.id))
                webhook_message = await self.webhook_manager.send_as_persona(
                    channel, persona_config, error_message, reply_to=original_message
                )
                if webhook_message:
                    error_msg = webhook_message
                else:
                    error_msg = await channel.send(error_message)
            else:
                error_msg = await channel.send(error_message)

            # Store error response
            if error_msg:
                error_conv_message = ConversationMessage.from_discord_message(
                    error_msg, persona_name=persona_config.name
                )
                self.conversation_store.get_or_create_conversation(
                    error_conv_message.channel_id, error_conv_message
                )

    async def _handle_message_with_router(
        self,
        conv_message: ConversationMessage,
        explicit_persona: PersonaConfig | None = None,
        is_mentioned: bool = False,
        mention_string: str | None = None,
    ) -> None:
        """Handle a message using the router for conversation analysis.

        Router runs on all messages and decides whether to respond.

        Args:
            conv_message: The message in internal format
            explicit_persona: If user mentioned a specific persona (@JohnPM)
            is_mentioned: True if bot or persona was mentioned (safety override)
            mention_string: The actual mention string for response processing
        """
        try:
            # Get all active conversations for router to choose from
            active_conversations = self.conversation_store.get_active_conversations(
                conv_message.channel_id
            )

            # Prepare router context
            router_context = RouterContext(
                current_message=conv_message,
                active_conversations=active_conversations,
                available_personas=[
                    PersonaInfo(name=p.name, role=p.role) for p in self.config.personas
                ],
                explicit_persona=explicit_persona.name if explicit_persona else None,
                is_bot_mentioned=is_mentioned,
            )

            # Get router decision (conversation routing + persona + context + should_respond)
            router_agent = get_router_agent()

            # Build prompt with all active conversations for router
            router_prompt = build_router_prompt(conv_message, active_conversations)
            decision = await router_agent.run(
                router_prompt,
                deps=router_context,
            )

            logger.info(f"Router decision: {decision.output.reasoning}")
            logger.info(f"Router should_respond: {decision.output.should_respond}")
            logger.info(f"Router conversation: {decision.output.conversation_id}")
            logger.info(f"Suggested persona: {decision.output.suggested_persona}")
            logger.info(f"Confidence: {decision.output.confidence:.2f}")

            # Always store the message for context, regardless of response decision
            if decision.output.conversation_id:
                # Router wants to use existing conversation
                conversation = self.conversation_store.get_conversation(
                    decision.output.conversation_id
                )
                if conversation:
                    logger.info(
                        f"Routing to existing conversation: {decision.output.conversation_id}"
                    )
                    self.conversation_store.add_message(conversation.id, conv_message)
                else:
                    # Conversation ID not found, create new one
                    logger.warning(
                        f"Router suggested conversation {decision.output.conversation_id} not found, creating new"
                    )
                    conversation = self.conversation_store.create_conversation(
                        conv_message.channel_id, conv_message
                    )
            else:
                # Router wants to create new conversation
                logger.info("Router decided to create new conversation")
                conversation = self.conversation_store.create_conversation(
                    conv_message.channel_id, conv_message
                )

            # Update topic summary from router
            if decision.output.topic_summary:
                conversation.topic_summary = decision.output.topic_summary

            # Respect should_respond decision unless explicitly mentioned (safety)
            if not decision.output.should_respond:
                if is_mentioned:
                    # Safety override: explicit mentions MUST get a response
                    logger.warning(
                        "Router returned should_respond=False but explicit mention detected. "
                        "Overriding to True for safety."
                    )
                    decision.output.should_respond = True
                else:
                    # Log why bot isn't responding (for debugging)
                    logger.info(
                        f"Bot not responding to message: {decision.output.reasoning}"
                    )
                    return  # Don't respond, but message is already stored for context

            # Get relevant context messages selected by router
            context_messages = extract_context_messages(
                conversation, decision.output, strict=False
            )
            logger.info(f"Using {len(context_messages)} context messages")

            # Handle explicit persona mention
            if explicit_persona:
                logger.info(f"Using explicit persona: {explicit_persona.name}")
                # Extract query by removing the persona mention
                pattern = rf"@{re.escape(explicit_persona.name)}\b"
                query = re.sub(
                    pattern, "", conv_message.content, flags=re.IGNORECASE
                ).strip()

                # Handle empty queries for explicit persona mentions
                if not query:
                    await self._handle_empty_persona_mention(
                        conv_message, explicit_persona
                    )
                    return

                # Use explicit persona with router-selected context
                await self._respond_as_persona(
                    conv_message,
                    query,
                    explicit_persona,
                    context_messages,
                    router_reasoning=decision.output.reasoning,
                    selection_type="mention",
                )
                return

            # Handle bot mention (no explicit persona)
            if is_mentioned and mention_string:
                logger.info("Handling bot mention with router-suggested persona")
                # Extract the query by removing the mention string
                query = conv_message.content.replace(mention_string, "", 1).strip()

                # Handle empty queries for bot mentions
                if not query:
                    await self._handle_empty_bot_mention(conv_message)
                    return

                # Get persona based on router suggestion
                persona_config = None
                if decision.output.suggested_persona:
                    persona_config = self.config.get_persona_by_name(
                        decision.output.suggested_persona
                    )

                if persona_config:
                    # Use router-suggested persona with router-selected context
                    logger.info(
                        f"Using router-suggested persona: {persona_config.name}"
                    )
                    await self._respond_as_persona(
                        conv_message,
                        query,
                        persona_config,
                        context_messages,
                        router_reasoning=decision.output.reasoning,
                        selection_type="router",
                    )
                else:
                    # No persona suggested, use default agent
                    logger.info("No persona suggested, using default agent")
                    await self._respond_as_default(
                        conv_message,
                        query,
                        context_messages,
                        conversation,
                        router_reasoning=decision.output.reasoning,
                        selection_type="router",
                    )
                return

            # Proactive interjection (no explicit mention, but should_respond=True)
            if decision.output.should_respond:
                logger.info("Proactive interjection based on router decision")
                # Get persona based on router suggestion
                persona_config = None
                if decision.output.suggested_persona:
                    persona_config = self.config.get_persona_by_name(
                        decision.output.suggested_persona
                    )

                if persona_config:
                    # Use router-suggested persona with router-selected context
                    logger.info(f"Proactive response as: {persona_config.name}")
                    await self._respond_as_persona(
                        conv_message,
                        conv_message.content,
                        persona_config,
                        context_messages,
                        router_reasoning=decision.output.reasoning,
                        selection_type="proactive",
                    )
                else:
                    # No persona suggested, use default agent
                    logger.info("Proactive response with default agent")
                    await self._respond_as_default(
                        conv_message,
                        conv_message.content,
                        context_messages,
                        conversation,
                        router_reasoning=decision.output.reasoning,
                        selection_type="proactive",
                    )
                return

        except Exception as e:
            logger.error(f"Error processing message with router: {e}")

            # For explicit mentions, still try to respond despite router error
            if is_mentioned:
                await self._handle_router_error_fallback(conv_message, explicit_persona)
            else:
                # For proactive mode, just log the error and don't respond
                logger.error("Router error in proactive mode, not responding")

    async def _handle_empty_persona_mention(
        self, conv_message: ConversationMessage, persona_config: PersonaConfig
    ) -> None:
        """Handle empty query for explicit persona mention."""
        author_mention = f"<@{conv_message.author_id}>"
        response_content = (
            f"Hello, {author_mention}! I'm {persona_config.display_name}, "
            f"{persona_config.role}. How can I help you?"
        )

        # Fetch channel for sending response
        channel = self.get_channel(int(conv_message.channel_id))
        if not channel:
            logger.error(f"Could not find channel {conv_message.channel_id}")
            return

        # Ensure channel supports sending messages
        assert isinstance(channel, discord.abc.Messageable), (
            f"Channel {conv_message.channel_id} does not support sending messages"
        )

        # Try to send as persona via webhook, fallback to normal message
        response_msg = None
        if isinstance(channel, discord.TextChannel):
            # Get original Discord message for reply_to functionality
            original_message = await channel.fetch_message(int(conv_message.id))
            webhook_message = await self.webhook_manager.send_as_persona(
                channel,
                persona_config,
                response_content,
                reply_to=original_message,
            )
            if webhook_message:
                response_msg = webhook_message
            else:
                # Fallback to regular message if webhook fails
                response_msg = await channel.send(response_content)
        else:
            response_msg = await channel.send(response_content)

        # Store bot response
        if response_msg:
            bot_conv_message = ConversationMessage.from_discord_message(
                response_msg, persona_name=persona_config.name
            )
            self.conversation_store.get_or_create_conversation(
                bot_conv_message.channel_id, bot_conv_message
            )

    async def _handle_empty_bot_mention(
        self, conv_message: ConversationMessage
    ) -> None:
        """Handle empty query for bot mention."""
        # Fetch channel for sending response
        channel = self.get_channel(int(conv_message.channel_id))
        if not channel:
            logger.error(f"Could not find channel {conv_message.channel_id}")
            return

        # Ensure channel supports sending messages
        assert isinstance(channel, discord.abc.Messageable), (
            f"Channel {conv_message.channel_id} does not support sending messages"
        )

        author_mention = f"<@{conv_message.author_id}>"
        response_msg = await channel.send(
            f"Hello, {author_mention}! How can I help you?"
        )
        # Store bot response
        if response_msg:
            bot_conv_message = ConversationMessage.from_discord_message(
                response_msg, persona_name=None
            )
            self.conversation_store.get_or_create_conversation(
                bot_conv_message.channel_id, bot_conv_message
            )

    async def _respond_as_default(
        self,
        conv_message: ConversationMessage,
        query: str,
        context_messages: list[ConversationMessage] | None,
        conversation: ConversationThread,
        router_reasoning: str | None = None,
        selection_type: str = "fallback",
    ) -> None:
        """Generate and send a response using the default agent."""
        deps = Deps(file_path=self.default_knowledge_base)

        # Build enhanced prompt with context
        enhanced_query = build_enhanced_query(
            query,
            context_messages or [],
            router_reasoning=router_reasoning,
            selection_type=selection_type,
        )
        response = await self.agent.run(enhanced_query, deps=deps)

        # Fetch channel for sending response
        channel = self.get_channel(int(conv_message.channel_id))
        if not channel:
            logger.error(f"Could not find channel {conv_message.channel_id}")
            return

        # Ensure channel supports sending messages
        assert isinstance(channel, discord.abc.Messageable), (
            f"Channel {conv_message.channel_id} does not support sending messages"
        )

        response_msg = await channel.send(response.output)

        # Store bot response
        if response_msg:
            bot_message = ConversationMessage.from_discord_message(
                response_msg, persona_name=None
            )
            conversation.add_message(bot_message)

    async def _handle_router_error_fallback(
        self,
        conv_message: ConversationMessage,
        explicit_persona: PersonaConfig | None = None,
    ) -> None:
        """Fallback response when router fails but user mentioned bot."""
        author_mention = f"<@{conv_message.author_id}>"
        error_message = (
            f"I apologize, {author_mention}, but I encountered an error "
            f"processing your request. Please try again later."
        )

        # Fetch channel for sending error response
        channel = self.get_channel(int(conv_message.channel_id))
        if not channel:
            logger.error(f"Could not find channel {conv_message.channel_id}")
            return

        # Ensure channel supports sending messages
        assert isinstance(channel, discord.abc.Messageable), (
            f"Channel {conv_message.channel_id} does not support sending messages"
        )

        if explicit_persona:
            # Try to send error as persona, fallback to regular message
            error_msg = None
            if isinstance(channel, discord.TextChannel):
                # Get original Discord message for reply_to functionality
                original_message = await channel.fetch_message(int(conv_message.id))
                webhook_message = await self.webhook_manager.send_as_persona(
                    channel, explicit_persona, error_message, reply_to=original_message
                )
                if webhook_message:
                    error_msg = webhook_message
                else:
                    error_msg = await channel.send(error_message)
            else:
                error_msg = await channel.send(error_message)

            # Store error response
            if error_msg:
                error_conv_message = ConversationMessage.from_discord_message(
                    error_msg, persona_name=explicit_persona.name
                )
                self.conversation_store.get_or_create_conversation(
                    error_conv_message.channel_id, error_conv_message
                )
        else:
            # Send as regular bot message
            error_msg = await channel.send(error_message)
            if error_msg:
                error_conv_message = ConversationMessage.from_discord_message(
                    error_msg, persona_name=None
                )
                self.conversation_store.get_or_create_conversation(
                    error_conv_message.channel_id, error_conv_message
                )


def create_bot(knowledge_base_path: str | None = None) -> AITeamBot:
    """Create and return a configured Discord bot instance."""
    if knowledge_base_path is None:
        # Default to a knowledge base if none specified
        knowledge_base_path = os.path.join("kbs", "default.txt")

    return AITeamBot(default_knowledge_base=knowledge_base_path)


def run_bot(knowledge_base_path: str | None = None) -> None:
    """Run the Discord bot."""
    bot_token = os.getenv("DISCORD_BOT_TOKEN")
    if not bot_token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")

    # Get log level from environment variable
    log_level = os.getenv("LOGLEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Set up logging
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    bot = create_bot(knowledge_base_path)
    bot.run(bot_token)
