"""Webhook management for persona impersonation in Discord."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional

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
        self._webhooks: Dict[int, str] = {}  # channel_id -> webhook_url
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
    ) -> Optional[discord.Webhook]:
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

    async def send_as_persona(
        self,
        channel: discord.TextChannel,
        persona_config: PersonaConfig,
        content: str,
        reply_to: Optional[discord.Message] = None,
    ) -> Optional[discord.WebhookMessage]:
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

            # Prepare the content with reply reference if needed
            final_content = content
            if reply_to:
                final_content = f"Replying to {reply_to.author.mention}:\n\n{content}"

            # Use aiohttp session for webhook execution
            async with aiohttp.ClientSession() as session:
                webhook_with_session = discord.Webhook.from_url(
                    webhook.url, session=session
                )

                # Send the message via webhook
                logger.debug(
                    f"Sending webhook message as {persona_config.display_name} "
                    f"with avatar URL: {persona_config.avatar_url or 'None (will use default)'}"
                )

                message = await webhook_with_session.send(
                    content=final_content,
                    username=persona_config.display_name,
                    avatar_url=persona_config.avatar_url,
                    wait=True,
                    allowed_mentions=discord.AllowedMentions(replied_user=True)
                    if reply_to
                    else None,
                )

                logger.info(
                    f"Successfully sent webhook message as {persona_config.display_name} "
                    f"in channel {channel.id} (Message ID: {message.id})"
                )
                return message

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
_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """Get the global webhook manager instance."""
    global _webhook_manager
    if _webhook_manager is None:
        # Store webhooks file in the project root
        webhooks_path = Path(__file__).parent.parent.parent / "webhooks.json"
        _webhook_manager = WebhookManager(webhooks_path)
    return _webhook_manager
