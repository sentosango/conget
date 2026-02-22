"""Main CLI entry point for conget."""

import argparse
import logging
import sys


def main():
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        sys.argv.append("--help")

    parser = argparse.ArgumentParser(
        description="Conget - Simple CLI for fetching web content with plugin architecture"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(
        dest="command", required=False, help="Available commands"
    )

    # conget fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fetch content from a URL")
    fetch_parser.add_argument("url", help="URL to fetch from")
    fetch_parser.add_argument(
        "--fetcher", "-F", help="Specific fetcher to use (default: auto-select)"
    )
    fetch_parser.add_argument("--format", "-f", help="Output format")
    fetch_parser.add_argument(
        "--list-fetchers",
        action="store_true",
        help="List all available fetchers for URL",
    )

    # conget list
    list_parser = subparsers.add_parser("list", help="List all available fetchers")
    list_parser.add_argument(
        "--format", "-f", help="Show fetchers supporting this format"
    )

    # conget analyze
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze URLs to see which fetchers can handle them"
    )
    analyze_parser.add_argument("urls", nargs="+", help="URLs to analyze")

    # conget mcp
    subparsers.add_parser("mcp", help="Start MCP server")

    # conget config
    subparsers.add_parser("config", help="Show and upgrade config file")

    # Check if first positional argument is a known command
    known_commands = {"fetch", "list", "analyze", "mcp", "config"}

    # Find first positional argument (not starting with -)
    first_pos_arg = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            first_pos_arg = arg
            break

    # If first arg is not a known command, treat as implicit fetch
    if first_pos_arg and first_pos_arg not in known_commands:
        logging.debug(
            f"[FIX] No command specified, treating '{first_pos_arg}' as URL for implicit fetch"
        )
        # Prepend "fetch" to arguments and re-parse
        sys.argv = [sys.argv[0], "fetch"] + sys.argv[1:]

    # Show fetch help if called without URL
    if len(sys.argv) >= 2 and sys.argv[1] == "fetch" and len(sys.argv) == 2:
        subparsers.choices["fetch"].print_help()
        sys.exit(0)

    # Show analyze help if called without URLs
    if len(sys.argv) >= 2 and sys.argv[1] == "analyze" and len(sys.argv) == 2:
        subparsers.choices["analyze"].print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    if args.command == "fetch":
        from src.cli.fetch import run

        run(args)
    elif args.command == "list":
        from src.cli.list import run

        run(args)
    elif args.command == "analyze":
        from src.cli.analyze import run

        run(args)
    elif args.command == "mcp":
        from src.cli.mcp import run

        run(args)
    elif args.command == "config":
        from src.cli.config import run
        run(args)


if __name__ == "__main__":
    main()
