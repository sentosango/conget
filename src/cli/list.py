"""List command for conget CLI."""

import logging

from src.core.registry import get_fetchers

logger = logging.getLogger(__name__)


def run(args):
    """Execute the list command.

    Args:
        args: Parsed command-line arguments.
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
        if args.format and args.format not in fetcher.metadata.supported_formats:
            continue

        special_marker = " [special]" if fetcher.metadata.is_special else ""
        print(f"  {name}{special_marker}")
        print(f"    Description: {fetcher.metadata.description}")
        print(f"    Formats: {', '.join(fetcher.metadata.supported_formats)}")
        print()
