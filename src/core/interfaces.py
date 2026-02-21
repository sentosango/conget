"""Interfaces for conget fetchers."""

from abc import ABC, abstractmethod
from typing import Optional

from .types import FetcherMetadata, FetchResult


class BaseFetcher(ABC):
    """Base interface that all fetchers must implement.

    All fetchers must provide metadata through the metadata property and
    implement the can_fetch and fetch methods. The fetch method returns
    a FetchResult object containing the fetched content and metadata.
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
        import argparse
        import logging
        import sys

        from .config import get_default_format

        logger = logging.getLogger(__name__)

        # Create fetcher instance to get metadata and supported formats
        fetcher = cls()

        # Use metadata description if not provided
        if description is None:
            description = fetcher.metadata.description

        supported_formats = fetcher.metadata.supported_formats

        # Show help if no arguments provided
        if len(sys.argv) == 1:
            sys.argv.append("--help")

        # Create argument parser
        parser = argparse.ArgumentParser(description=description)
        parser.add_argument("url", help=url_help)
        parser.add_argument(
            "--format",
            "-f",
            choices=supported_formats,
            help="Output format (default: from config or 'markdown')",
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Enable verbose logging",
        )

        args = parser.parse_args()

        # Setup logging
        logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

        # Get format (from args or config)
        format = args.format or get_default_format()

        # Validate format is supported
        if format not in supported_formats:
            logger.error(
                f"Format '{format}' not supported by {fetcher.metadata.name}. "
                f"Supported formats: {', '.join(supported_formats)}"
            )
            print(
                f"Error: Format '{format}' not supported. "
                f"Supported formats: {', '.join(supported_formats)}",
                file=sys.stderr,
            )
            raise SystemExit(1)

        # Fetch and print content
        try:
            result = fetcher.fetch(args.url, format)
            print(result.content)
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}", file=sys.stderr)
            raise SystemExit(1)
