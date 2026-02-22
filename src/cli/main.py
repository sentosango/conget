"""Main CLI entry point for conget."""

import logging
import sys
from typing import Annotated, Optional

import typer

from src.cli import analyze, config, fetch, list as list_cmd

# Global state for verbose mode
state = {"verbose": False}

app = typer.Typer(
    name="conget",
    help="Conget - Simple CLI for fetching web content with plugin architecture",
    no_args_is_help=True,
)


@app.callback()
def main(
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Enable verbose logging")] = False,
):
    """Conget - Simple CLI for fetching web content with plugin architecture."""
    state["verbose"] = verbose
    # Setup logging based on verbose flag
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING)


# Register commands
app.command(name="fetch")(fetch.fetch)
app.command(name="list")(list_cmd.list_cmd)
app.command(name="analyze")(analyze.analyze)
app.command(name="config")(config.config)


@app.command(name="mcp")
def mcp_cmd():
    """Start MCP server."""
    from src.cli.mcp import run
    run(None)


def main_entry():
    """Entry point for the CLI."""
    # Check if first positional argument is a known command
    known_commands = {"fetch", "list", "analyze", "mcp", "config", "--help", "--version", "--install-completion", "--show-completion"}

    # Find first positional argument (not starting with -)
    first_pos_arg = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            first_pos_arg = arg
            break

    # If first arg is not a known command, treat as implicit fetch
    if first_pos_arg and first_pos_arg not in known_commands:
        logging.debug(
            f"No command specified, treating '{first_pos_arg}' as URL for implicit fetch"
        )
        # Prepend "fetch" to arguments
        sys.argv = [sys.argv[0], "fetch"] + sys.argv[1:]

    app()


if __name__ == "__main__":
    main_entry()
