"""Fetch command for conget CLI."""

import json
import logging
import sys
from typing import Annotated, Any, Dict, List

import typer

from src.core.config import get_default_cache_ttl, get_default_format, merge_cli_options
from src.core.exceptions import CongetError, HTTPError, PluginLoadError
from src.core.registry import get_fetchers

logger = logging.getLogger(__name__)


def complete_fetcher(incomplete: str) -> List[str]:
    """Autocomplete function for --fetcher option."""
    try:
        fetchers = get_fetchers()
        return [name for name in fetchers if name.startswith(incomplete)]
    except Exception:
        return []


def complete_format(incomplete: str) -> List[str]:
    """Autocomplete function for --format option."""
    # Common formats across fetchers
    common_formats = ["markdown", "text", "html", "json"]
    return [fmt for fmt in common_formats if fmt.startswith(incomplete)]


def complete_url(incomplete: str) -> List[str]:
    """Autocomplete function for URL argument - returns empty list to disable file completion."""
    return []


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
            if (
                output_format is None
                or output_format in fetcher.metadata.supported_formats
            ):
                logger.debug(f"Selected specialized fetcher: {name}")
                return name

    # Try non-special fetchers that can handle the URL (except "default")
    for name, cls in fetchers.items():
        if name == "default":
            continue
        fetcher = cls()
        if not fetcher.metadata.is_special and fetcher.can_fetch(url):
            if (
                output_format is None
                or output_format in fetcher.metadata.supported_formats
            ):
                logger.debug(f"Selected non-special fetcher: {name}")
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


def fetch(
    url: Annotated[
        str,
        typer.Argument(help="URL to fetch from", autocompletion=complete_url),
    ],
    fetcher: Annotated[
        str | None,
        typer.Option(
            "-F",
            "--fetcher",
            help="Specific fetcher to use (default: auto-select)",
            autocompletion=complete_fetcher,
        ),
    ] = None,
    format: Annotated[
        str | None,
        typer.Option(
            "-f", "--format", help="Output format", autocompletion=complete_format
        ),
    ] = None,
    list_fetchers: Annotated[
        bool,
        typer.Option("--list-fetchers", help="List all available fetchers for URL"),
    ] = False,
    options: Annotated[
        str | None,
        typer.Option(
            "--options", help='Fetcher options as JSON (e.g., \'{"option": "value"}\')'
        ),
    ] = None,
):
    """Execute the fetch command.

    Args:
        url: URL to fetch from.
        fetcher: Specific fetcher to use (default: auto-select).
        format: Output format.
        list_fetchers: List all available fetchers for URL.
        options: Fetcher options as JSON.
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
    if list_fetchers:
        available = list_available_fetchers(url)

        if not available:
            print(f"No fetchers available for: {url}")
            return

        print(f"Available fetchers for {url}:")
        for f in available:
            special_marker = " [special]" if f["special"] else ""
            print(f"  {f['name']}{special_marker}: {f['description']}")
            print(f"    Formats: {', '.join(f['formats'])}")
        return

    # Select fetcher
    if fetcher:
        fetcher_name = fetcher
        if fetcher_name not in fetchers:
            print(f"Error: Unknown fetcher '{fetcher_name}'", file=sys.stderr)
            print(f"Available: {', '.join(fetchers.keys())}", file=sys.stderr)
            raise SystemExit(1)
    else:
        fetcher_name = select_best_fetcher(fetchers, url, format)

    fetcher_class = fetchers[fetcher_name]
    fetcher_instance = fetcher_class()
    output_format = format or get_default_format()

    # Validate format
    if output_format not in fetcher_instance.metadata.supported_formats:
        print(
            f"Error: Fetcher '{fetcher_name}' does not support format '{output_format}'",
            file=sys.stderr,
        )
        print(
            f"Supported formats: {', '.join(fetcher_instance.metadata.supported_formats)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    logger.info(f"Using fetcher: {fetcher_name}")

    # Parse --options JSON argument
    cli_options = None
    if options:
        try:
            cli_options = json.loads(options)
            logger.debug(f"Parsed CLI options: {cli_options}")
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --options argument: {e}", file=sys.stderr)
            raise SystemExit(1)

    # Merge CLI options with config
    fetcher_options = merge_cli_options(fetcher_instance.metadata.name, cli_options)
    logger.debug(f"Final fetcher options: {fetcher_options}")

    try:
        result = fetcher_instance.fetch_with_cache(
            url=url,
            output_format=output_format,
            cache_ttl=get_default_cache_ttl(),
            fetch_options=fetcher_options,
        )
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
