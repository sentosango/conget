"""Default fetcher using trafilatura.

This module provides the DefaultFetcher class for generic web content extraction.
"""

import json
import logging
from typing import Any, Dict

import trafilatura

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
                "only_metadata": ConfigOption(
                    default=False,
                    description="Return only frontmatter without content",
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

    def fetch(
        self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None
    ) -> FetchResult:
        """Fetch content from the URL in the specified format.

        Args:
            url: The URL to fetch from
            output_format: The output format (html, markdown, text, xmltei, json, csv)
            fetch_options: Optional merged configuration options

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

        downloaded = trafilatura.fetch_url(
            url, no_ssl=fetch_options.get("no_ssl", False) if fetch_options else False
        )

        if downloaded is None:
            raise FetchError(f"Failed to fetch URL: {url}")

        # Map format names to trafilatura's internal names
        trafilatura_format = {
            "text": "txt",  # trafilatura uses 'txt', we expose 'text'
        }.get(output_format, output_format)

        only_metadata = fetch_options.get("only_metadata", False) if fetch_options else False

        # When only_metadata is requested, always extract with metadata to get frontmatter
        with_metadata = (
            fetch_options.get("with_metadata", True) if fetch_options else True
        ) or only_metadata

        content = trafilatura.extract(
            downloaded,
            output_format=trafilatura_format,
            include_comments=fetch_options.get("include_comments", True)
            if fetch_options
            else True,
            include_tables=fetch_options.get("include_tables", True)
            if fetch_options
            else True,
            include_images=fetch_options.get("include_images", True)
            if fetch_options
            else True,
            include_formatting=fetch_options.get("include_formatting", True)
            if fetch_options
            else True,
            include_links=fetch_options.get("include_links", True)
            if fetch_options
            else True,
            with_metadata=with_metadata,
        )

        # Extract only metadata if only_metadata is requested
        if only_metadata and content:
            if output_format == "json":
                # Remove content-bearing fields from JSON output
                try:
                    data = json.loads(content)
                    for key in ("raw_text", "text", "comments"):
                        data.pop(key, None)
                    content = json.dumps(data, ensure_ascii=False, indent=2)
                except (json.JSONDecodeError, TypeError):
                    pass
            else:
                frontmatter = self._extract_frontmatter(content)
                if frontmatter:
                    content = frontmatter

        return FetchResult(
            content=content or "",
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
        )

    @staticmethod
    def _extract_frontmatter(content: str) -> str | None:
        """Extract YAML frontmatter from trafilatura output.

        Trafilatura with with_metadata=True outputs YAML frontmatter
        between --- delimiters.

        Args:
            content: Full trafilatura output with metadata

        Returns:
            Frontmatter string (including --- delimiters) or None
        """
        if not content.startswith("---"):
            return None

        # Find the closing ---
        end = content.find("---", 3)
        if end == -1:
            return None

        return content[: end + 3]


def cli():
    """Entry point for console script."""
    DefaultFetcher.run_cli()


if __name__ == "__main__":
    cli()
