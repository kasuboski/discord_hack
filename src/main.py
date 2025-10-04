"""Entry point for the AI Team Bot - supports both CLI and Discord modes."""

import asyncio
import sys

from dotenv import load_dotenv

from discord_hack.agent import get_agent
from discord_hack.dependencies import Deps
from discord_hack.discord_main import main as discord_main

import logfire


async def cli_main():
    """Main function for the CLI mode."""
    if len(sys.argv) != 3:
        print("Usage for CLI: python main.py <knowledge_base_file> <question>")
        sys.exit(1)

    file_path = sys.argv[1]
    question = sys.argv[2]

    agent = get_agent()
    deps = Deps(file_path=file_path)

    response = await agent.run(
        question,
        deps=deps,
    )
    print("--- Agent Response ---")
    print(f"Answer: {response.output}")


def main():
    """Main entry point - determines whether to run CLI or Discord mode."""
    if len(sys.argv) == 1:
        print("AI Team Bot")
        print("===========")
        print()
        print("Usage:")
        print("  CLI mode:     python main.py <knowledge_base_file> <question>")
        print("  Discord mode: python main.py discord [knowledge_base_file]")
        print()
        print(
            "For Discord mode, make sure DISCORD_BOT_TOKEN is set in your environment."
        )
        sys.exit(1)

    _ = load_dotenv()

    _ = logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_pydantic_ai()

    if sys.argv[1] == "discord":
        # Remove 'discord' from args so discord_main can parse remaining args
        _ = sys.argv.pop(1)
        discord_main()
    else:
        # CLI mode
        asyncio.run(cli_main())


if __name__ == "__main__":
    main()
