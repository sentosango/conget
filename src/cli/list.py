"""List command for conget CLI."""

import logging

import typer
from typing import Annotated

from src.core.registry import get_fetchers

logger = logging.getLogger(__name__)


def list_cmd(
    format: Annotated[
        str | None,
        typer.Option("-f", "--format", help="Show fetchers supporting this format"),
    ] = None,
):
    """Execute the list command.

    Args:
        format: Optional format filter for fetchers.
    """
    fetchers = get_fetchers()

    if not fetchers:
        print("No fetchers available")
        return

    print("Available fetchers:")
    print()

    for name, cls in fetchers.items():
        fetcher = cls()

        # Filter by format if specified
        if format and format not in fetcher.metadata.supported_formats:
            continue

        special_marker = " [special]" if fetcher.metadata.is_special else ""
        print(f"  {name}{special_marker}")
        print(f"    Description: {fetcher.metadata.description}")
        print(f"    Formats: {', '.join(fetcher.metadata.supported_formats)}")

        if fetcher.metadata.config_options:
            print("    Options:")
            for option_name, option in fetcher.metadata.config_options.items():
                print(
                    f"      {option_name}: {option.description} (default: {repr(option.default)})"
                )

        print()
