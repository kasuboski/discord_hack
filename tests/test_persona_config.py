"""Tests for persona configuration management."""

import json
import tempfile
from pathlib import Path


from discord_hack.config import BotConfig, ConfigManager, PersonaConfig


def test_persona_config_creation():
    """Test creating a PersonaConfig instance."""
    persona = PersonaConfig(
        name="TestBot",
        display_name="Test Bot",
        role="Test Role",
        avatar_url="https://example.com/avatar.png",
        system_prompt="You are a test bot.",
        knowledge_base_path="./kbs/test.txt",
    )

    assert persona.name == "TestBot"
    assert persona.display_name == "Test Bot"
    assert persona.role == "Test Role"
    assert persona.avatar_url == "https://example.com/avatar.png"
    assert persona.system_prompt == "You are a test bot."
    assert persona.knowledge_base_path == "./kbs/test.txt"


def test_persona_config_knowledge_base_path():
    """Test knowledge base path resolution."""
    persona = PersonaConfig(
        name="TestBot",
        display_name="Test Bot",
        role="Test Role",
        avatar_url="https://example.com/avatar.png",
        system_prompt="You are a test bot.",
        knowledge_base_path="./kbs/test.txt",
    )

    # The path should be resolved relative to project root
    kb_path = persona.get_knowledge_base_path()
    assert kb_path.name == "test.txt"
    assert "kbs" in str(kb_path)


def test_bot_config_persona_lookup():
    """Test persona lookup functionality in BotConfig."""
    personas = [
        PersonaConfig(
            name="JohnPM",
            display_name="John Parker",
            role="Project Manager",
            avatar_url="https://example.com/john.png",
            system_prompt="You are John.",
            knowledge_base_path="./kbs/pm.txt",
        ),
        PersonaConfig(
            name="SarahArch",
            display_name="Sarah Chen",
            role="Architect",
            avatar_url="https://example.com/sarah.png",
            system_prompt="You are Sarah.",
            knowledge_base_path="./kbs/arch.txt",
        ),
    ]

    config = BotConfig(personas=personas)

    # Test finding persona by name (case insensitive)
    john = config.get_persona_by_name("JohnPM")
    assert john is not None
    assert john.name == "JohnPM"

    john_lower = config.get_persona_by_name("johnpm")
    assert john_lower is not None
    assert john_lower.name == "JohnPM"

    # Test non-existent persona
    missing = config.get_persona_by_name("NonExistent")
    assert missing is None

    # Test getting all persona names
    names = config.get_persona_names()
    assert "JohnPM" in names
    assert "SarahArch" in names
    assert len(names) == 2


def test_config_manager_load_from_list():
    """Test loading configuration from a JSON list format."""
    personas_data = [
        {
            "name": "TestBot1",
            "display_name": "Test Bot 1",
            "role": "Tester",
            "avatar_url": "https://example.com/test1.png",
            "system_prompt": "You are test bot 1.",
            "knowledge_base_path": "./kbs/test1.txt",
        },
        {
            "name": "TestBot2",
            "display_name": "Test Bot 2",
            "role": "Developer",
            "avatar_url": "https://example.com/test2.png",
            "system_prompt": "You are test bot 2.",
            "knowledge_base_path": "./kbs/test2.txt",
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(personas_data, f)
        temp_path = f.name

    try:
        config_manager = ConfigManager(temp_path)
        config = config_manager.load_config()

        assert len(config.personas) == 2
        assert config.get_persona_by_name("TestBot1") is not None
        assert config.get_persona_by_name("TestBot2") is not None
    finally:
        Path(temp_path).unlink()


def test_config_manager_missing_file():
    """Test behavior when config file doesn't exist."""
    config_manager = ConfigManager("nonexistent.json")
    config = config_manager.load_config()

    # Should return empty config without errors
    assert isinstance(config, BotConfig)
    assert len(config.personas) == 0


def test_config_manager_reload():
    """Test config reloading functionality."""
    personas_data = [
        {
            "name": "TestBot",
            "display_name": "Test Bot",
            "role": "Tester",
            "avatar_url": "https://example.com/test.png",
            "system_prompt": "You are a test bot.",
            "knowledge_base_path": "./kbs/test.txt",
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(personas_data, f)
        temp_path = f.name

    try:
        config_manager = ConfigManager(temp_path)

        # Load initial config
        config1 = config_manager.load_config()
        assert len(config1.personas) == 1

        # Modify the file
        personas_data.append(
            {
                "name": "TestBot2",
                "display_name": "Test Bot 2",
                "role": "Developer",
                "avatar_url": "https://example.com/test2.png",
                "system_prompt": "You are test bot 2.",
                "knowledge_base_path": "./kbs/test2.txt",
            }
        )

        with open(temp_path, "w") as f:
            json.dump(personas_data, f)

        # Reload config
        config2 = config_manager.reload_config()
        assert len(config2.personas) == 2

    finally:
        Path(temp_path).unlink()


def test_personas_json_format():
    """Test that the actual personas.json format works correctly."""
    # This tests the actual format we're using in the project
    personas_data = [
        {
            "name": "JohnPM",
            "display_name": "John Parker",
            "role": "Project Manager",
            "avatar_url": "https://api.dicebear.com/7.x/personas/svg?seed=JohnPM",
            "system_prompt": "You are John Parker, a Project Manager.",
            "knowledge_base_path": "./kbs/project_management.txt",
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(personas_data, f)
        temp_path = f.name

    try:
        config_manager = ConfigManager(temp_path)
        config = config_manager.load_config()

        john = config.get_persona_by_name("JohnPM")
        assert john is not None
        assert john.display_name == "John Parker"
        assert john.role == "Project Manager"
        assert "dicebear.com" in john.avatar_url
        assert "Project Manager" in john.system_prompt

    finally:
        Path(temp_path).unlink()
