"""Discord bot client implementation."""

from __future__ import annotations

import logging
import os

import discord

from .agent import get_agent
from .dependencies import Deps

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

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages."""
        # Ignore messages from bots to prevent infinite loops
        if message.author.bot:
            return

        logger.debug(f"Received message: {message.content}")

        # Check if the bot was mentioned
        mention_string = self.bot_mentioned(message)
        if mention_string:
            logger.info(f"Bot mentioned in message: {message.content}")
            await self._handle_mention(message, mention_string)

    async def _handle_mention(
        self, message: discord.Message, mention_string: str
    ) -> None:
        """Handle a message that mentions the bot."""
        try:
            # Extract the query by removing the specific mention string
            query = message.content.replace(mention_string, "", 1).strip()

            # Handle empty queries
            if not query:
                _ = await message.channel.send(
                    f"Hello, {message.author.mention}! How can I help you?"
                )
                return

            # Process the query with the RAG agent
            deps = Deps(file_path=self.default_knowledge_base)
            response = await self.agent.run(query, deps=deps)

            # Send the response
            _ = await message.channel.send(response.output)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            _ = await message.channel.send(
                "I apologize, but I encountered an error processing your request. "
                + "Please try again later."
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
