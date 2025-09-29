# AI Team Bot - Discord RAG Assistant

A multi-persona AI agent for Discord designed to assist software development teams using Retrieval-Augmented Generation (RAG). Built with Python, discord.py, pydantic-ai, and powered by Meta Llama models via Cerebras API.

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

### Usage

#### Discord Bot Mode

Start the Discord bot:
```bash
uv run python src/main.py discord
```

Or with a custom knowledge base:
```bash
uv run python src/main.py discord path/to/your/knowledge_base.txt
```

#### CLI Mode (for testing)

Test the RAG system directly:
```bash
uv run python src/main.py kbs/default.txt "What is the AI Team Bot?"
```

## 🤖 Discord Bot Features

### Phase 2 Implementation (Current)

- **@Mention Support**: Mention the bot (`@BotName`) followed by your question
- **Knowledge Base Integration**: Responses are powered by RAG from project documentation
- **Error Handling**: Graceful error handling and user feedback
- **Logging**: Comprehensive logging for debugging and monitoring

### Example Discord Usage

```
@AITeamBot What is the project architecture?
@AITeamBot How do I set up the development environment?
@AITeamBot
```

## 🏗️ Architecture

### Core Components

- **Discord Bot** (`discord_bot.py`): Discord.py integration with message handling
- **RAG Agent** (`agent.py`): AI agent with retrieval-augmented generation
- **Dependencies** (`dependencies.py`): Dependency injection for file paths
- **Knowledge Base**: Text files in `kbs/` directory

### Project Structure

```
src/
├── discord_hack/
│   ├── __init__.py
│   ├── agent.py          # RAG agent implementation
│   ├── dependencies.py   # Dependency injection
│   ├── discord_bot.py    # Discord bot client
│   └── discord_main.py   # Discord entry point
├── main.py              # CLI and Discord entry points
kbs/
├── default.txt          # Default knowledge base
└── kb.txt              # Additional knowledge base
tests/
├── test_agent.py        # Agent tests
└── test_discord_bot.py  # Discord bot tests
```

## 🧪 Testing

Run all tests:
```bash
uv run pytest
```

Run specific test files:
```bash
uv run pytest tests/test_discord_bot.py -v
```

Format code:
```bash
uv run ruff format
uv run ruff check --fix
```

## 📋 Setup Guide

### 1. Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section
4. Copy the bot token and set it as `DISCORD_BOT_TOKEN`
5. Enable "Message Content Intent" in the Privileged Gateway Intents section

### 2. Discord Server Setup

1. Generate an invite link with these permissions:
   - Send Messages
   - Read Messages
   - Read Message History
   - Use Slash Commands (future use)

2. Invite the bot to your server

### 3. Cerebras API Setup

1. Get your Cerebras API key
2. Set it as `CEREBRAS_API_KEY` environment variable

## 🔧 Configuration

### Knowledge Base

- Place your knowledge base files in the `kbs/` directory
- Supported formats: `.txt`, `.md`
- The bot will read the entire file content for RAG context

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Your Discord bot token |
| `CEREBRAS_API_KEY` | Yes | Your Cerebras API key for Llama models |

## 🚦 Development Phases

### ✅ Phase 1: Core RAG Engine
- [x] Standalone AI agent with RAG capability
- [x] Integration with Cerebras/Llama models
- [x] Basic knowledge base retrieval

### ✅ Phase 2: Discord @Mention Integration (Current)
- [x] Discord.py bot with mention detection
- [x] Message processing and query extraction
- [x] Integration with existing RAG agent
- [x] Error handling and logging
- [x] Comprehensive testing

### 🔄 Phase 3: Multi-Persona Team (Planned)
- [ ] Multiple AI personas with distinct personalities
- [ ] Persona-specific knowledge bases
- [ ] Discord webhooks for persona avatars
- [ ] Configuration-driven persona management

### 🔄 Phase 4: Context-Aware Interjection (Planned)
- [ ] Conversation tracking and context management
- [ ] Proactive interjection without mentions
- [ ] Stateful conversation routing

### 🔄 Phase 5: Polish & Deployment (Planned)
- [ ] Docker containerization
- [ ] Production deployment guides
- [ ] Advanced error handling and monitoring

## 💡 Usage Examples

### Basic Q&A
```
User: @AITeamBot What is this project about?
Bot: The AI Team Bot is a multi-persona AI agent designed for Discord to assist software development teams...
```

### Empty Mention
```
User: @AITeamBot
Bot: Hello, @User! How can I help you?
```

### Error Scenarios
The bot gracefully handles:
- API failures
- Invalid knowledge base files
- Rate limiting
- Network issues

## 🤝 Contributing

1. Follow the existing code style (enforced by Ruff)
2. Write tests for new functionality
3. Update documentation as needed
4. Run tests before submitting PRs

## 📄 License

This is a hackathon project. Please check with the project authors for licensing terms.

## 🔗 Technologies Used

- **Python 3.12+**
- **discord.py** - Discord API integration
- **pydantic-ai** - Structured AI agent framework
- **Cerebras API** - Meta Llama model inference
- **pytest** - Testing framework
- **Ruff** - Code formatting and linting
- **uv** - Fast Python package manager

## 📞 Support

This is a hackathon project. For issues or questions, please check the project documentation or contact the development team.