"""Default markdown fetcher for direct .md URLs.

This module provides the DefaultMdFetcher class for fetching markdown files
directly from URLs ending with .md extension.
"""

import logging
import re
from typing import Any, Dict

import requests

from src.core.exceptions import FetchError, HTTPError, UnsupportedFormatError
from src.core.interfaces import BaseFetcher
from src.core.types import ConfigOption, FetcherMetadata, FetchResult

logger = logging.getLogger(__name__)

# Pattern for markdown file URLs
MD_URL_PATTERN = re.compile(r"\.md$", re.IGNORECASE)


class DefaultMdFetcher(BaseFetcher):
    """Fetcher for markdown files from direct URLs.

    This fetcher handles URLs that directly point to markdown files (.md extension).
    It returns the content as-is without any HTML parsing.
    """

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="default-md",
            description="Fetcher for direct markdown file URLs (.md)",
            is_special=False,
            supported_formats=["markdown", "text"],
            config_options={
                "timeout": ConfigOption(
                    default=30, description="Request timeout in seconds"
                ),
                "no_ssl": ConfigOption(
                    default=False, description="Disable SSL verification"
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the URL.

        Args:
            url: The URL to check

        Returns:
            True if URL ends with .md extension
        """
        return bool(MD_URL_PATTERN.search(url))

    def fetch(
        self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None
    ) -> FetchResult:
        """Fetch markdown content from the URL.

        Args:
            url: The URL to fetch from
            output_format: The output format (markdown, text)
            fetch_options: Optional configuration options

        Returns:
            FetchResult containing the fetched content

        Raises:
            UnsupportedFormatError: If the format is not supported
            HTTPError: If an HTTP error occurs
            FetchError: If fetching fails
        """
        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching markdown file: {url}")

        timeout = fetch_options.get("timeout", 30) if fetch_options else 30
        no_ssl = fetch_options.get("no_ssl", False) if fetch_options else False

        try:
            response = requests.get(url, timeout=timeout, verify=not no_ssl)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise FetchError(f"Request timeout for URL: {url}")
        except requests.exceptions.SSLError:
            raise FetchError(f"SSL error for URL: {url}")
        except requests.exceptions.HTTPError as e:
            raise HTTPError(
                message=f"HTTP error for URL: {url}",
                status_code=e.response.status_code if e.response else None,
            )
        except requests.exceptions.RequestException as e:
            raise FetchError(f"Failed to fetch URL: {url}. Error: {e}")

        content = response.text

        # For text format, just return as-is (markdown is readable text)
        # Could add markdown-to-text conversion if needed in the future

        return FetchResult(
            content=content,
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
        )


def cli():
    """Entry point for console script."""
    DefaultMdFetcher.run_cli()


if __name__ == "__main__":
    cli()
