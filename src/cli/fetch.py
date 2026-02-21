"""Fetch command for conget CLI."""

import logging
import sys
from typing import Any, Dict, List

from src.core.config import get_default_format
from src.core.exceptions import CongetError, HTTPError, PluginLoadError
from src.core.registry import get_fetchers

logger = logging.getLogger(__name__)


def select_best_fetcher(
    fetchers: Dict[str, Any], url: str, output_format: str | None = None
) -> str:
    """Select best fetcher for a URL and format.

    Priority:
    1. Specialized fetchers that can handle the URL
    2. Generic (default) fetcher
    3. First available fetcher

    Args:
        fetchers: Dictionary of fetcher classes.
        url: The URL to fetch.
        output_format: Desired output format (optional).

    Returns:
        Name of the best fetcher.
    """
    logger.debug(f"Selecting best fetcher for URL: {url}")

    # First, try to find a specialized fetcher that can handle the URL
    for name, cls in fetchers.items():
        fetcher = cls()
        if fetcher.metadata.is_special and fetcher.can_fetch(url):
            # Check format compatibility
            if output_format is None or output_format in fetcher.metadata.supported_formats:
                logger.debug(f"Selected specialized fetcher: {name}")
                return name

    # Fall back to generic fetcher
    if "default" in fetchers:
        logger.debug("Selected default fetcher")
        return "default"

    # Fall back to first available fetcher
    first_name = next(iter(fetchers))
    logger.debug(f"Selected first available fetcher: {first_name}")
    return first_name


def list_available_fetchers(url: str) -> List[Dict[str, Any]]:
    """List all fetchers that can handle a URL.

    Args:
        url: The URL to check.

    Returns:
        List of dictionaries with fetcher info.
    """
    logger.debug(f"Listing available fetchers for URL: {url}")

    fetchers = get_fetchers()
    available = []

    for name, cls in fetchers.items():
        fetcher = cls()
        if fetcher.can_fetch(url):
            available.append(
                {
                    "name": name,
                    "description": fetcher.metadata.description,
                    "formats": fetcher.metadata.supported_formats,
                    "special": fetcher.metadata.is_special,
                }
            )

    return available


def run(args):
    """Execute the fetch command.

    Args:
        args: Parsed command-line arguments.
    """
    try:
        fetchers = get_fetchers()
    except PluginLoadError as e:
        print(f"Plugin load error: {e}", file=sys.stderr)
        raise SystemExit(1)

    if not fetchers:
        print("Error: No fetchers available", file=sys.stderr)
        raise SystemExit(1)

    # List fetchers for URL if requested
    if args.list_fetchers:
        available = list_available_fetchers(args.url)

        if not available:
            print(f"No fetchers available for: {args.url}")
            return

        print(f"Available fetchers for {args.url}:")
        for f in available:
            special_marker = " [special]" if f["special"] else ""
            print(f"  {f['name']}{special_marker}: {f['description']}")
            print(f"    Formats: {', '.join(f['formats'])}")
        return

    # Select fetcher
    if args.fetcher:
        fetcher_name = args.fetcher
        if fetcher_name not in fetchers:
            print(f"Error: Unknown fetcher '{fetcher_name}'", file=sys.stderr)
            print(f"Available: {', '.join(fetchers.keys())}", file=sys.stderr)
            raise SystemExit(1)
    else:
        fetcher_name = select_best_fetcher(fetchers, args.url, args.format)

    fetcher_class = fetchers[fetcher_name]
    fetcher = fetcher_class()
    output_format = args.format or get_default_format()

    # Validate format
    if output_format not in fetcher.metadata.supported_formats:
        print(
            f"Error: Fetcher '{fetcher_name}' does not support format '{output_format}'",
            file=sys.stderr,
        )
        print(
            f"Supported formats: {', '.join(fetcher.metadata.supported_formats)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    logger.info(f"Using fetcher: {fetcher_name}")

    try:
        result = fetcher.fetch(args.url, output_format)
        print(result.content)
    except HTTPError as e:
        logger.error(f"HTTP error: {e}")
        status_msg = f" (status: {e.status_code})" if e.status_code else ""
        print(f"HTTP error{status_msg}: {e}", file=sys.stderr)
        raise SystemExit(1)
    except CongetError as e:
        logger.error(f"Conget error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        raise SystemExit(1)
