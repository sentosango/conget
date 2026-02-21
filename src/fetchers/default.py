"""Default fetcher using trafilatura.

This module provides the DefaultFetcher class for generic web content extraction.
"""

import logging

import trafilatura

from src.core.config import get_section_config
from src.core.exceptions import FetchError, UnsupportedFormatError
from src.core.interfaces import BaseFetcher
from src.core.types import ConfigOption, FetcherMetadata, FetchResult

logger = logging.getLogger(__name__)


class DefaultFetcher(BaseFetcher):
    """Generic fetcher using trafilatura for web content extraction.

    This fetcher can handle most web URLs and extracts content in various formats.
    """

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="default",
            description="Generic web content fetcher using trafilatura",
            is_special=False,
            supported_formats=["html", "markdown", "text", "xmltei", "json", "csv"],
            config_options={
                "include_comments": ConfigOption(
                    default=True, description="Include comments in extracted content"
                ),
                "include_tables": ConfigOption(
                    default=True, description="Include tables in extracted content"
                ),
                "include_images": ConfigOption(
                    default=True, description="Include images in extracted content"
                ),
                "include_formatting": ConfigOption(
                    default=True, description="Include formatting in extracted content"
                ),
                "include_links": ConfigOption(
                    default=True, description="Include links in extracted content"
                ),
                "with_metadata": ConfigOption(
                    default=True, description="Include metadata in extracted content"
                ),
                "no_ssl": ConfigOption(
                    default=False, description="Disable SSL verification"
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the URL.

        The default fetcher can handle any URL.

        Args:
            url: The URL to check

        Returns:
            Always returns True
        """
        return True

    def fetch(self, url: str, output_format: str) -> FetchResult:
        """Fetch content from the URL in the specified format.

        Args:
            url: The URL to fetch from
            output_format: The output format (html, markdown, text, xmltei, json, csv)

        Returns:
            FetchResult containing the fetched content and metadata

        Raises:
            UnsupportedFormatError: If the format is not supported
            FetchError: If fetching fails
        """
        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching {url} with format {output_format}")

        config = get_section_config("default")
        downloaded = trafilatura.fetch_url(url, no_ssl=config.get("no_ssl", False))

        if downloaded is None:
            raise FetchError(f"Failed to fetch URL: {url}")

        # Map format names to trafilatura's internal names
        trafilatura_format = {
            "text": "txt",  # trafilatura uses 'txt', we expose 'text'
        }.get(output_format, output_format)

        content = trafilatura.extract(
            downloaded,
            output_format=trafilatura_format,
            include_comments=config.get("include_comments", True),
            include_tables=config.get("include_tables", True),
            include_images=config.get("include_images", True),
            include_formatting=config.get("include_formatting", True),
            include_links=config.get("include_links", True),
            with_metadata=config.get("with_metadata", True),
        )

        return FetchResult(
            content=content,
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
        )


def cli():
    """Entry point for console script."""
    DefaultFetcher.run_cli()


if __name__ == "__main__":
    cli()
