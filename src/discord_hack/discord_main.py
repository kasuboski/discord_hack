"""Entry point for running the Discord bot."""

import sys
from pathlib import Path

from .discord_bot import run_bot


def main() -> None:
    """Main function for the Discord bot."""
    knowledge_base_path = None

    # Allow optional command line argument for knowledge base path
    if len(sys.argv) == 2:
        knowledge_base_path = sys.argv[1]
        # Verify the file exists
        if not Path(knowledge_base_path).exists():
            print(f"Error: Knowledge base file '{knowledge_base_path}' not found.")
            sys.exit(1)
    elif len(sys.argv) > 2:
        print("Usage: python discord_main.py [knowledge_base_file]")
        print(
            "If no knowledge base is specified, will use default from kbs/default.txt"
        )
        sys.exit(1)

    try:
        run_bot(knowledge_base_path)
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure to set the DISCORD_BOT_TOKEN environment variable.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
