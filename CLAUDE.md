# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- **Install dependencies**: `uv install`
- **Run bot (Discord mode)**: `uv run src/main.py discord`
- **Run bot (CLI mode)**: `uv run src/main.py <knowledge_base_file> <question>`

### Testing
- **Run all tests**: `uv run pytest`
- **Run specific test file**: `uv run pytest tests/test_agent.py`
- **Run tests with output**: `uv run pytest -v`

### Code Quality
- **Lint code**: `uv run ruff check`
- **Lint with auto-fix**: `uv run ruff check --fix`
- **Format code**: `uv run ruff format`

## Architecture Overview

This is a multi-persona Discord AI bot with Retrieval-Augmented Generation (RAG) capabilities. The bot responds to mentions with contextually relevant answers from domain-specific knowledge bases.

### Core Architecture Patterns

**Multi-Persona System**: The bot features multiple AI "personas" (e.g., JohnPM, SarahArch, DevMike), each with:
- Unique personality and system prompt
- Isolated knowledge base (`kbs/` directory)
- Discord webhook for custom avatar/name display
- Persona-specific agent instance (cached in `agent.py`)

**Message Routing Flow**:
1. Discord message arrives → `discord_bot.py:on_message()`
2. Check for persona mention (`@PersonaName`) → route to `_handle_persona_mention()`
3. If no persona, check for bot mention → route to `_handle_mention()`
4. Agent runs with persona's knowledge base via `retrieve` tool
5. Response sent via webhook (as persona) or normal message (fallback)

**RAG Implementation**:
- Agent uses pydantic-ai with Cerebras API (Meta Llama models)
- `retrieve` tool reads entire knowledge base file for context
- Knowledge bases are text files in `kbs/` mapped to personas in `personas.json`

**Conversation Context System**:
- `context/` module tracks conversation threads using embeddings
- `ConversationManager` routes messages to existing conversations via semantic similarity
- Uses sentence-transformers (all-MiniLM-L6-v2 model) for message embeddings
- Supports topic-level and message-level similarity scoring

### Key Components

- **`agent.py`**: Creates pydantic-ai agents with RAG `retrieve` tool. Maintains agent cache to avoid recreation.
- **`discord_bot.py`**: Discord client handling message events, mention detection, and webhook-based persona responses.
- **`config.py`**: Loads `personas.json` and manages persona configurations (display names, avatars, knowledge bases).
- **`webhook_manager.py`**: Creates/caches Discord webhooks per channel for persona impersonation. Persists to `webhooks.json`.
- **`context/manager.py`**: Routes messages to conversations using hybrid semantic similarity (topic + recent messages).
- **`context/models.py`**: Data models for conversations, messages, and routing results.

### Configuration

- **`personas.json`**: Array of persona definitions (name, display_name, role, avatar_url, system_prompt, knowledge_base_path)
- **`webhooks.json`**: Cached webhook URLs per channel (auto-managed, don't edit manually)
- **Environment variables**: `DISCORD_BOT_TOKEN`, `CEREBRAS_API_KEY` (required)

### Important Implementation Details

1. **Persona Agent Caching**: Agents are created once per persona and cached in `_persona_agents` dict to avoid recreation overhead.

2. **Webhook Fallback**: All persona responses attempt webhook delivery first, falling back to normal messages with persona name prefixed if webhook fails.

3. **Knowledge Base Paths**: Relative paths in config (e.g., `./kbs/foo.txt`) are resolved from project root (parent of `src/`).

4. **Model Configuration**: Uses Cerebras API with `llama-4-scout-17b-16e-instruct` model via OpenAI provider compatibility layer.

5. **Embedding Model**: Context system uses `sentence-transformers` with `all-MiniLM-L6-v2` model for semantic similarity.

6. **Testing**: Project uses pytest with `pythonpath = src` (see `pytest.ini`). Tests located in `tests/` mirror `src/discord_hack/` structure.
