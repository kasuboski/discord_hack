"""Configuration management for personas and bot settings."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PersonaConfig(BaseModel):
    """Configuration for a single AI persona."""

    name: str = Field(description="The mention name for the persona (e.g., 'JohnPM')")
    display_name: str = Field(description="The human-readable display name")
    role: str = Field(description="The persona's role/title")
    avatar_url: str = Field(description="URL for the persona's avatar image")
    system_prompt: str = Field(
        description="The system prompt defining the persona's behavior"
    )
    knowledge_base_path: str = Field(
        description="Path to the persona's knowledge base file"
    )

    def get_knowledge_base_path(self) -> Path:
        """Get the resolved path to the knowledge base file."""
        # Convert relative paths to absolute paths from project root
        if self.knowledge_base_path.startswith("./"):
            # Assume project root is the parent of src/discord_hack
            project_root = Path(__file__).parent.parent.parent
            return project_root / self.knowledge_base_path[2:]
        return Path(self.knowledge_base_path)


class BotConfig(BaseModel):
    """Configuration for the Discord bot."""

    personas: list[PersonaConfig] = Field(default_factory=list)
    default_knowledge_base: str = Field(default="./kbs/default.txt")

    def get_persona_by_name(self, name: str) -> PersonaConfig | None:
        """Get a persona by its mention name."""
        for persona in self.personas:
            if persona.name.lower() == name.lower():
                return persona
        return None

    def get_persona_names(self) -> list[str]:
        """Get a list of all persona mention names."""
        return [persona.name for persona in self.personas]


class ConfigManager:
    """Manages bot configuration and persona loading."""

    def __init__(self, config_path: str | Path = "personas.json"):
        """Initialize the configuration manager."""
        self.config_path = Path(config_path)
        self._config: BotConfig | None = None

    def load_config(self) -> BotConfig:
        """Load configuration from the personas.json file."""
        if self._config is not None:
            return self._config

        try:
            # Find the config file relative to project root
            if not self.config_path.is_absolute():
                # Assume project root is the parent of src/discord_hack
                project_root = Path(__file__).parent.parent.parent
                config_file = project_root / self.config_path
            else:
                config_file = self.config_path

            if not config_file.exists():
                logger.warning(f"Config file not found: {config_file}")
                self._config = BotConfig()
                return self._config

            with open(config_file) as f:
                config_data = json.load(f)

            # If the JSON is a list, assume it's the personas array
            if isinstance(config_data, list):
                personas = [
                    PersonaConfig(**persona_data) for persona_data in config_data
                ]
                self._config = BotConfig(personas=personas)
            else:
                # If it's a dict, parse as full BotConfig
                self._config = BotConfig(**config_data)

            logger.info(
                f"Loaded {len(self._config.personas)} personas from {config_file}"
            )

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._config = BotConfig()

        return self._config

    def get_config(self) -> BotConfig:
        """Get the current configuration, loading it if necessary."""
        return self.load_config()

    def reload_config(self) -> BotConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load_config()


# Global config manager instance
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> BotConfig:
    """Get the current bot configuration."""
    return get_config_manager().get_config()
