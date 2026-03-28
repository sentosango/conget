"""Telegram post fetcher.

This module provides the TelegramPostFetcher class for extracting content
from Telegram public channel/group posts without authentication.
"""

import json
import logging
import re
from typing import Any, Dict

import trafilatura

from src.core.exceptions import FetchError, UnsupportedFormatError
from src.core.formatters import markdown_to_text
from src.core.interfaces import BaseFetcher
from src.core.types import ConfigOption, FetcherMetadata, FetchResult

logger = logging.getLogger(__name__)

# Pattern for Telegram post URLs: https://t.me/channel/post_id
TELEGRAM_POST_PATTERN = re.compile(
    r"^https?://(?:www\.)?t\.me/([a-zA-Z0-9_]+)/(\d+)/?$"
)


def parse_telegram_url(url: str) -> tuple[str, str] | None:
    """Extract channel and post_id from Telegram URL.

    Args:
        url: Telegram post URL

    Returns:
        Tuple of (channel, post_id) or None if not a valid Telegram post URL
    """
    match = TELEGRAM_POST_PATTERN.match(url)
    if match:
        return match.group(1), match.group(2)
    return None


class TelegramPostFetcher(BaseFetcher):
    """Fetcher for Telegram public posts.

    Extracts content from Telegram public channel/group posts using the
    embed API (no authentication required).
    """

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="telegram-post",
            description="Fetcher for Telegram public posts (t.me/channel/post_id)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "include_links": ConfigOption(
                    default=True, description="Include links in extracted content"
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the URL.

        Args:
            url: The URL to check

        Returns:
            True if URL is a Telegram post URL (t.me/channel/post_id)
        """
        return parse_telegram_url(url) is not None

    def fetch(
        self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None
    ) -> FetchResult:
        """Fetch Telegram post content.

        Args:
            url: The Telegram post URL
            output_format: Output format (markdown, text, json)
            fetch_options: Optional configuration options

        Returns:
            FetchResult with the post content

        Raises:
            UnsupportedFormatError: If format is not supported
            FetchError: If fetching fails
        """
        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        parsed = parse_telegram_url(url)
        if not parsed:
            raise FetchError(f"Invalid Telegram post URL: {url}")

        channel, post_id = parsed
        logger.info(f"Fetching Telegram post: {channel}/{post_id}")

        # Convert to embed URL which has full HTML content
        embed_url = f"https://t.me/{channel}/{post_id}?embed=1&mode=tme"

        # Fetch using trafilatura
        downloaded = trafilatura.fetch_url(embed_url)

        if downloaded is None:
            raise FetchError(f"Failed to fetch URL: {url}")

        # Extract metadata
        tg_meta = trafilatura.extract_metadata(downloaded)

        # Extract text content (without metadata, we'll add our own)
        include_links = (
            fetch_options.get("include_links", True) if fetch_options else True
        )

        text_content = trafilatura.extract(
            downloaded,
            output_format="markdown",
            include_comments=False,
            include_tables=True,
            include_images=True,
            include_formatting=True,
            include_links=include_links,
            with_metadata=False,  # We'll add our own metadata
        )

        if text_content is None:
            raise FetchError(f"Failed to extract content from: {url}")

        # Build post data with custom metadata
        post_data = {
            "channel": channel,
            "post_id": post_id,
            "url": url,
            "author": tg_meta.author if tg_meta else None,
            "date": tg_meta.date if tg_meta else None,
            "text": text_content,
        }

        # Format output
        content = self._format_output(post_data, output_format)

        return FetchResult(
            content=content,
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
            metadata=post_data,
        )

    def _format_output(self, data: dict[str, Any], output_format: str) -> str:
        """Format post data for output.

        Args:
            data: Post data dictionary
            output_format: Output format (markdown, text, json)

        Returns:
            Formatted string
        """
        if output_format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        # Build markdown
        lines = [
            f"# {data['author'] or data['channel']}",
            "",
            f"**Channel:** {data['channel']}",
            f"**URL:** {data['url']}",
        ]

        if data.get("date"):
            lines.append(f"**Date:** {data['date']}")

        lines.extend(
            [
                "",
                "## Post",
                "",
                data["text"],
            ]
        )

        markdown = "\n".join(lines)

        if output_format == "text":
            return markdown_to_text(markdown)

        return markdown


def cli():
    """Entry point for console script."""
    TelegramPostFetcher.run_cli(url_help="Telegram post URL (t.me/channel/post_id)")


if __name__ == "__main__":
    cli()
