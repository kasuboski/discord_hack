"""Command-line interface for the AI Team Bot RAG engine."""

import asyncio
import sys

from discord_hack.agent import get_agent
from discord_hack.dependencies import Deps


async def main():
    """Main function for the CLI."""
    if len(sys.argv) != 3:
        print("Usage: python main.py <knowledge_base_file> <question>")
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


if __name__ == "__main__":
    asyncio.run(main())
