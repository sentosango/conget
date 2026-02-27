"""Interfaces for conget fetchers."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.core.cache import CacheManager
from src.core.config import get_section_config, merge_cli_options
from src.core.types import FetcherMetadata, FetchResult

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Base interface that all fetchers must implement.

    All fetchers must provide metadata through the metadata property and
    implement the can_fetch and fetch methods. The fetch_with_cache method handles
    caching automatically.
    """

    @property
    @abstractmethod
    def metadata(self) -> FetcherMetadata:
        """Fetcher metadata containing all fetcher information.

        Returns:
            FetcherMetadata: Object containing name, description, is_special flag,
                supported formats, and configuration options.
        """

    @abstractmethod
    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this fetcher can handle the URL, False otherwise.
        """

    @abstractmethod
    def fetch(self, url: str, output_format: str) -> FetchResult:
        """Fetch content from the URL in the specified format.

        Args:
            url: The URL to fetch from.
            output_format: The output format (html, markdown, text, json, etc.).

        Returns:
            FetchResult: Object containing the fetched content, URL, format,
                and optional metadata.

        Raises:
            UnsupportedFormatError: If the format is not supported by this fetcher.
            ValidationError: If the URL or parameters are invalid.
            FetchError: If fetching content fails for a general reason.
            HTTPError: If an HTTP error occurs during fetching.
            ParsingError: If parsing the fetched content fails.
            CongetError: For other conget-specific errors.
        """

    def fetch_with_cache(
        self,
        url: str,
        output_format: str,
        cache_ttl: int = 0,
        fetch_options: Dict[str, Any] | None = None,
    ) -> FetchResult:
        """Fetch content from the URL with optional caching.

        This method handles caching automatically. If cache_ttl > 0, it
        checks the cache first and returns cached results if available.
        Otherwise, it calls fetch and caches the result.

        Args:
            url: The URL to fetch from.
            output_format: The output format (html, markdown, text, json, etc.).
            cache_ttl: Cache time-to-live in seconds. 0 disables caching.
            fetch_options: Fetcher options for cache key generation (optional).

        Returns:
            FetchResult: Object containing the fetched content, URL, format,
                and optional metadata.
        """
        # Skip cache if TTL is not set
        if cache_ttl <= 0:
            return self.fetch(url, output_format)

        cache = CacheManager(namespace=self.metadata.name)

        # Use provided fetch_options for cache key
        cache_key = CacheManager.generate_key(
            url=url,
            output_format=output_format,
            options=fetch_options if fetch_options else None,
        )

        cached = cache.get(cache_key, ttl=cache_ttl)
        if cached is not None:
            logger.debug(f"Cache hit for {url}")
            return cached

        # Perform actual fetch
        result = self.fetch(url, output_format)

        cache.set(cache_key, result)
        logger.debug(f"Cached result for {url}")

        return result

    @classmethod
    def run_cli(
        cls,
        description: Optional[str] = None,
        url_help: str = "URL to fetch",
    ) -> None:
        """Run the CLI for this fetcher.

        This method creates a standard CLI interface for the fetcher with
        argument parsing, logging setup, and error handling.

        Args:
            description: Custom description for the CLI. If None, uses the
                fetcher's metadata description.
            url_help: Help text for the URL argument.

        Example:
            >>> # In fetcher.py
            >>> if __name__ == "__main__":
            ...     MyFetcher.run_cli()
        """
        import logging
        import sys
        from typing import Annotated

        import typer

        from .config import get_default_format

        logger = logging.getLogger(__name__)

        # Create fetcher instance to get metadata and supported formats
        fetcher = cls()

        # Use metadata description if not provided
        if description is None:
            description = fetcher.metadata.description

        supported_formats = fetcher.metadata.supported_formats

        # Create typer app
        app = typer.Typer(
            add_completion=False,
            no_args_is_help=False,
        )

        def _run(
            url: Annotated[str, typer.Argument(help=url_help)],
            format: Annotated[
                str | None,
                typer.Option(
                    "-f",
                    "--format",
                    help=f"Output format (default: from config or 'markdown'). Supported: {', '.join(supported_formats)}",
                ),
            ] = None,
            verbose: Annotated[
                bool,
                typer.Option("-v", "--verbose", help="Enable verbose logging"),
            ] = False,
            options: Annotated[
                str | None,
                typer.Option("--options", help='Fetcher options as JSON (e.g., \'{"option": "value"}\')'),
            ] = None,
        ) -> None:
            # Setup logging
            logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING)

            # Get format (from args or config)
            format_val = format or get_default_format()

            # Validate format is supported
            if format_val not in supported_formats:
                logger.error(
                    f"Format '{format_val}' not supported by {fetcher.metadata.name}. "
                    f"Supported formats: {', '.join(supported_formats)}"
                )
                print(
                    f"Error: Format '{format_val}' not supported. "
                    f"Supported formats: {', '.join(supported_formats)}",
                    file=sys.stderr,
                )
                raise SystemExit(1)

            # Parse fetch options from --options argument
            fetch_options = None
            if options:
                try:
                    fetch_options = json.loads(options)
                    logger.debug(f"Parsed fetch options: {fetch_options}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse --options JSON: {e}. Ignoring options.")
                    fetch_options = None

            # Merge CLI options with config and defaults
            merged_options = merge_cli_options(fetcher.metadata.name, fetch_options)
            logger.debug(f"Using merged options: {merged_options}")

            # Fetch and print content
            try:
                from .config import get_default_cache_ttl
                result = fetcher.fetch_with_cache(
                    url,
                    output_format=format_val,
                    cache_ttl=get_default_cache_ttl(),
                    fetch_options=merged_options if merged_options else None,
                )
                print(result.content)
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"Error: {e}", file=sys.stderr)
                raise SystemExit(1)

        # Override help text
        app.command(
            name="",
            help=description,
        )(_run)

        # Show help if no arguments provided
        if len(sys.argv) == 1:
            sys.argv.append("--help")

        # Run the typer app
        app()
