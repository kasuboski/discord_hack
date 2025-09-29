# AI Team Bot - Discord RAG Assistant

The **AI Team Bot** is a multi-persona AI agent for Discord designed to assist software development teams. It leverages Retrieval-Augmented Generation (RAG) to provide contextually relevant answers from project-specific knowledge bases. The system features distinct AI "personas" (e.g., Project Manager, Lead Architect) that can be directly mentioned for targeted queries.

Built with Python, discord.py, pydantic-ai, and powered by Meta Llama models via the Cerebras API.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Discord bot token
- Cerebras API key

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd discord_hack
```

2. Install dependencies:
```bash
uv install
```

3. Set up environment variables:
```bash
export DISCORD_BOT_TOKEN="your_discord_bot_token_here"
export CEREBRAS_API_KEY="your_cerebras_api_key_here"
```

### Running the Bot

Start the Discord bot:
```bash
uv run src/main.py discord
```

## 🤖 Features

- **Multi-Persona Support**: Interact with a team of AI assistants, each with a unique personality, avatar, and knowledge base (e.g., `@JohnPM`, `@SarahArch`).
- **Persona Mention Detection**: Mention a persona directly (`@PersonaName`) to get a targeted answer from their specific domain of expertise.
- **Webhook-Based Impersonation**: Each persona responds with their own name and a unique, dynamically generated avatar.
- **Persona-Specific RAG**: Each persona has an isolated knowledge base, ensuring domain-specific and contextually relevant answers.
- **Dynamic Configuration**: Personas are defined and managed through `personas.json`, allowing for easy customization.
- **General Bot Interaction**: Mention the bot by its name (`@AITeamBot`) for general questions.

## Usage

### Interacting with the Bot

- **General Question**: `@AITeamBot What is the project architecture?`
- **Persona-Specific Question**: `@JohnPM how should we prioritize these features?`
- **Empty Mention**: `@AITeamBot` (The bot will greet you)

The bot will detect the mention and route the query to the appropriate agent.

## Development

### Running Commands

- **Run Tests**:
  ```bash
  uv run pytest
  ```
- **Lint and Format Code**:
  ```bash
  uv run ruff check --fix
  uv run ruff format
  ```

## 🏗️ Architecture

The bot's architecture is designed around a multi-persona, RAG-based system. For a detailed overview, see [docs/arch.md](docs/arch.md).

### Core Components

- **Discord Bot** (`discord_bot.py`): Manages Discord API integration, message handling, and webhook-based responses.
- **RAG Agent** (`agent.py`): Core AI agent that uses Retrieval-Augmented Generation.
- **Configuration Manager** (`config.py`): Loads and manages persona definitions from `personas.json`.
- **Webhook Manager** (`webhook_manager.py`): Handles the creation and caching of Discord webhooks for persona impersonation.
- **Knowledge Bases**: Text files in the `kbs/` directory, with each persona having its own dedicated knowledge source.

## 🚦 Development Phases

### ✅ Phase 1: Core RAG Engine
- [x] Standalone AI agent with RAG capability
- [x] Integration with Cerebras/Llama models
- [x] Basic knowledge base retrieval

### ✅ Phase 2: Discord @Mention Integration
- [x] Discord.py bot with mention detection
- [x] Message processing and query extraction
- [x] Integration with existing RAG agent
- [x] Error handling and logging

### ✅ Phase 3: Multi-Persona Team & Dynamic RAG
- [x] Multiple AI personas with distinct personalities and knowledge bases.
- [x] Persona mention detection (`@PersonaName`).
- [x] Discord webhooks for persona avatars and names.
- [x] Configuration-driven persona management via `personas.json`.

### 🔄 Phase 4: Context-Aware Interjection (Planned)
- [ ] Conversation tracking and context management
- [ ] Proactive interjection without mentions
- [ ] Stateful conversation routing

### 🔄 Phase 5: Polish & Deployment (Planned)
- [ ] Docker containerization
- [ ] Production deployment guides
- [ ] Advanced error handling and monitoring

## 🔧 Configuration

### Personas
Personas are configured in `personas.json`. Each persona has a name, role, system prompt, and a path to their knowledge base.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Your Discord bot token |
| `CEREBRAS_API_KEY` | Yes | Your Cerebras API key for Llama models |

## 🔗 Technologies Used

- **Python 3.12+**
- **discord.py** - Discord API integration
- **pydantic-ai** - Structured AI agent framework
- **Cerebras API** - Meta Llama model inference
- **pytest** - Testing framework
- **Ruff** - Code formatting and linting
- **uv** - Fast Python package manager
