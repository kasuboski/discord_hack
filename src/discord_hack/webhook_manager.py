"""Webhook management for persona impersonation in Discord."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import discord
import aiohttp

from .config import PersonaConfig

logger = logging.getLogger(__name__)


class WebhookManager:
    """Manages Discord webhooks for persona impersonation."""

    def __init__(self, webhooks_file: str | Path = "webhooks.json"):
        """Initialize the webhook manager.

        Args:
            webhooks_file: Path to the JSON file storing webhook URLs.
        """
        self.webhooks_file = Path(webhooks_file)
        self._webhooks: dict[int, str] = {}  # channel_id -> webhook_url
        self._load_webhooks()

    def _load_webhooks(self) -> None:
        """Load existing webhooks from file."""
        if not self.webhooks_file.exists():
            logger.info(f"Webhooks file not found: {self.webhooks_file}")
            return

        try:
            with open(self.webhooks_file) as f:
                data = json.load(f)
                # Convert string keys back to int channel IDs
                self._webhooks = {int(k): v for k, v in data.items()}
                logger.info(
                    f"Loaded {len(self._webhooks)} webhooks from {self.webhooks_file}"
                )
        except Exception as e:
            logger.error(f"Error loading webhooks: {e}")
            self._webhooks = {}

    def _save_webhooks(self) -> None:
        """Save current webhooks to file."""
        try:
            # Ensure parent directory exists
            self.webhooks_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert int keys to strings for JSON serialization
            data = {str(k): v for k, v in self._webhooks.items()}

            with open(self.webhooks_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(
                f"Saved {len(self._webhooks)} webhooks to {self.webhooks_file}"
            )
        except Exception as e:
            logger.error(f"Error saving webhooks: {e}")

    async def get_webhook(
        self, channel: discord.TextChannel, persona_config: PersonaConfig
    ) -> discord.Webhook | None:
        """Get or create a webhook for the given channel.

        Args:
            channel: The Discord text channel.
            persona_config: Configuration for the persona (used for webhook name).

        Returns:
            A Discord webhook object, or None if creation failed.
        """
        try:
            # Check if we have a cached webhook URL for this channel
            if channel.id in self._webhooks:
                webhook_url = self._webhooks[channel.id]
                try:
                    # Create webhook from URL and test if it's still valid
                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(webhook_url, session=session)
                        # Try to fetch webhook info to validate it exists
                        await webhook.fetch()
                        logger.debug(f"Using existing webhook for channel {channel.id}")
                        return webhook
                except (discord.NotFound, discord.HTTPException):
                    # Webhook no longer exists, remove from cache
                    logger.warning(
                        f"Cached webhook for channel {channel.id} no longer exists"
                    )
                    del self._webhooks[channel.id]
                    self._save_webhooks()

            # Create a new webhook
            webhook_name = f"AI Team Bot - {persona_config.display_name}"
            webhook = await channel.create_webhook(
                name=webhook_name, reason="AI Team Bot persona impersonation"
            )

            # Cache the webhook URL
            self._webhooks[channel.id] = webhook.url
            self._save_webhooks()

            logger.info(f"Created new webhook for channel {channel.id}: {webhook_name}")
            return webhook

        except discord.Forbidden:
            logger.error(
                f"Missing permissions to create webhook in channel {channel.id}. "
                f"Bot needs 'Manage Webhooks' permission."
            )
            return None
        except Exception as e:
            logger.error(
                f"Error getting/creating webhook for channel {channel.id}: {e}"
            )
            return None

    def _split_message(self, content: str, max_length: int = 2000) -> list[str]:
        """Split a message into chunks that fit Discord's character limit.

        Args:
            content: The message content to split.
            max_length: Maximum length per chunk (default 2000 for Discord).

        Returns:
            List of message chunks.
        """
        if len(content) <= max_length:
            return [content]

        chunks = []
        current_chunk = ""

        # Split by lines first to avoid breaking in the middle of a line
        lines = content.split("\n")

        for line in lines:
            # If a single line is longer than max_length, split it by sentences
            if len(line) > max_length:
                # Split by common sentence endings
                sentences = re.split(r"([.!?]+\s+)", line)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            # Even a single sentence is too long, force split
                            chunks.append(sentence[:max_length])
                            current_chunk = sentence[max_length:]
                    else:
                        current_chunk += sentence
            # If adding this line would exceed the limit, start a new chunk
            elif len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def send_as_persona(
        self,
        channel: discord.TextChannel,
        persona_config: PersonaConfig,
        content: str,
        reply_to: discord.Message | None = None,
    ) -> discord.WebhookMessage | None:
        """Send a message as a persona using webhooks.

        Args:
            channel: The Discord text channel to send the message to.
            persona_config: Configuration for the persona.
            content: The message content to send.
            reply_to: Optional message to reply to.

        Returns:
            The sent webhook message, or None if sending failed.
        """
        try:
            webhook = await self.get_webhook(channel, persona_config)
            if not webhook:
                logger.error(f"Could not get webhook for channel {channel.id}")
                return None

            # Validate avatar URL
            if not persona_config.avatar_url:
                logger.warning(
                    f"No avatar URL provided for persona {persona_config.name}"
                )
            else:
                logger.debug(
                    f"Using avatar URL for {persona_config.name}: {persona_config.avatar_url}"
                )

            # Prepare content with reply prefix if needed
            final_content = content
            if reply_to:
                reply_prefix = f"Replying to {reply_to.author.mention}:\n\n"
                final_content = reply_prefix + content

            # Split content into chunks if needed (after adding reply prefix)
            chunks = self._split_message(final_content)

            # Use aiohttp session for webhook execution
            async with aiohttp.ClientSession() as session:
                webhook_with_session = discord.Webhook.from_url(
                    webhook.url, session=session
                )

                first_message = None

                # Send each chunk
                for i, chunk in enumerate(chunks):
                    logger.debug(
                        f"Sending webhook message chunk {i + 1}/{len(chunks)} as {persona_config.display_name}"
                    )

                    message = await webhook_with_session.send(
                        content=chunk,
                        username=persona_config.display_name,
                        avatar_url=persona_config.avatar_url,
                        wait=True,
                        allowed_mentions=discord.AllowedMentions(replied_user=True)
                        if reply_to and i == 0
                        else discord.AllowedMentions.none(),
                    )

                    if i == 0:
                        first_message = message

                logger.info(
                    f"Successfully sent {len(chunks)} webhook message(s) as {persona_config.display_name} "
                    f"in channel {channel.id}"
                )
                return first_message

        except Exception as e:
            logger.error(f"Error sending message as persona {persona_config.name}: {e}")
            return None

    def remove_webhook_cache(self, channel_id: int) -> None:
        """Remove a webhook from the cache without deleting it from Discord.

        Args:
            channel_id: The Discord channel ID.
        """
        if channel_id in self._webhooks:
            del self._webhooks[channel_id]
            self._save_webhooks()
            logger.info(f"Removed webhook cache for channel {channel_id}")

    def get_cached_channels(self) -> list[int]:
        """Get a list of channel IDs that have cached webhooks."""
        return list(self._webhooks.keys())


# Global webhook manager instance
_webhook_manager: WebhookManager | None = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance."""
    global _webhook_manager
    if _webhook_manager is None:
        # Store webhooks file in the project root
        webhooks_path = Path(__file__).parent.parent.parent / "webhooks.json"
        _webhook_manager = WebhookManager(webhooks_path)
    return _webhook_manager
