"""YouTube video fetcher.

This module provides the YoutubeVideoFetcher class for extracting metadata
from YouTube videos using yt-dlp (no authentication, no video download).
"""

import json
import logging
import re
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from src.core.exceptions import FetchError, UnsupportedFormatError, ValidationError
from src.core.formatters import markdown_to_text
from src.core.interfaces import BaseFetcher
from src.core.types import ConfigOption, FetcherMetadata, FetchResult

logger = logging.getLogger(__name__)

# YouTube URL patterns (video ID is always 11 characters)
YOUTUBE_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})"),
]


def extract_video_id(url: str) -> str | None:
    """Extract video ID from YouTube URL.

    Args:
        url: YouTube URL (any supported format)

    Returns:
        11-character video ID or None if not found
    """
    for pattern in YOUTUBE_PATTERNS:
        match = pattern.match(url)
        if match:
            return match.group(1)
    return None


def normalize_url(video_id: str) -> str:
    """Build canonical YouTube URL from video ID.

    Args:
        video_id: 11-character YouTube video ID

    Returns:
        Canonical URL: https://www.youtube.com/watch?v={video_id}
    """
    return f"https://www.youtube.com/watch?v={video_id}"


class YoutubeVideoFetcher(BaseFetcher):
    """Fetcher for YouTube video metadata.

    Extracts metadata from YouTube videos using yt-dlp without downloading
    the video or requiring authentication.
    """

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="youtube-video",
            description="Fetcher for YouTube video metadata (using yt-dlp)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "lang": ConfigOption(
                    default="ru",
                    description="Language for metadata (e.g., 'en', 'ru', 'de')",
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the URL.

        Args:
            url: The URL to check

        Returns:
            True if the URL is a YouTube video URL
        """
        return extract_video_id(url) is not None

    def fetch(self, url: str, output_format: str) -> FetchResult:
        """Fetch video metadata from the URL in the specified format.

        Args:
            url: The YouTube video URL to fetch from
            output_format: The output format (markdown, text, json)

        Returns:
            FetchResult containing the video metadata

        Raises:
            UnsupportedFormatError: If the format is not supported
            ValidationError: If the URL is not a valid YouTube video URL
            FetchError: If fetching fails
        """
        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching YouTube video {url} with format {output_format}")

        video_id = extract_video_id(url)
        if not video_id:
            raise ValidationError(f"Invalid YouTube video URL: {url}")

        canonical_url = normalize_url(video_id)
        logger.debug(f"Canonical URL: {canonical_url}")

        # Get lang from config (default from metadata)
        lang = self.metadata.config_options["lang"].default

        # yt-dlp options for metadata extraction only
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "extractor_args": {
                "youtube": {
                    "lang": [lang],
                },
            },
        }

        logger.debug(f"Extracting metadata with yt-dlp, lang={lang}")

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(canonical_url, download=False)
                info_dict = ydl.sanitize_info(info)
        except (DownloadError, ExtractorError) as e:
            logger.error(f"yt-dlp error: {e}")
            raise FetchError(f"Failed to fetch YouTube video metadata: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise FetchError(f"Unexpected error fetching YouTube video: {e}") from e

        if not info_dict:
            raise FetchError(f"No metadata returned for video {video_id}")

        # Extract relevant fields
        video_data = self._extract_fields(info_dict, video_id, canonical_url)
        logger.debug(f"Extracted video data: id={video_data['id']}, title={video_data['title']}")

        # Format output
        content = self._format_output(video_data, output_format)

        return FetchResult(
            content=content,
            url=canonical_url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
            metadata=video_data,
        )

    def _extract_fields(self, info: dict[str, Any], video_id: str, canonical_url: str) -> dict[str, Any]:
        """Extract relevant metadata fields from yt-dlp info dict.

        Args:
            info: Sanitized info dict from yt-dlp
            video_id: YouTube video ID
            canonical_url: Canonical YouTube URL

        Returns:
            Dictionary with extracted metadata
        """
        return {
            "id": video_id,
            "url": canonical_url,
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "duration": info.get("duration"),  # seconds
            "duration_string": info.get("duration_string", ""),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "comment_count": info.get("comment_count"),
            "upload_date": info.get("upload_date", ""),  # YYYYMMDD
            "uploader": info.get("uploader", ""),
            "channel": info.get("channel", ""),
            "channel_url": info.get("channel_url", ""),
            "channel_id": info.get("channel_id", ""),
            "thumbnail": info.get("thumbnail", ""),
            "tags": info.get("tags", []),
        }

    def _format_output(self, data: dict[str, Any], output_format: str) -> str:
        """Format video data for output.

        Args:
            data: Video metadata dictionary
            output_format: Output format (markdown, text, json)

        Returns:
            Formatted string
        """
        if output_format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        # Build markdown
        lines = [
            f"# {data['title']}",
            "",
            f"**URL:** {data['url']}",
            f"**Channel:** [{data['channel']}]({data['channel_url']})" if data['channel_url'] else f"**Channel:** {data['channel']}",
            f"**Duration:** {data['duration_string']}" if data['duration_string'] else "",
            f"**Views:** {data['view_count']:,}" if data['view_count'] is not None else "",
            f"**Likes:** {data['like_count']:,}" if data['like_count'] is not None else "",
            f"**Upload Date:** {self._format_date(data['upload_date'])}" if data['upload_date'] else "",
            "",
            "## Description",
            "",
            data['description'] or "(no description)",
        ]

        # Add tags if present
        if data['tags']:
            lines.extend([
                "",
                "## Tags",
                "",
                ", ".join(data['tags'][:10]),  # Limit to 10 tags
            ])

        # Filter out empty lines from optional fields
        markdown = "\n".join(line for line in lines if line is not None)

        if output_format == "text":
            return markdown_to_text(markdown)

        return markdown

    def _format_date(self, date_str: str) -> str:
        """Format YYYYMMDD date to readable format.

        Args:
            date_str: Date in YYYYMMDD format

        Returns:
            Formatted date (e.g., "2025-01-15")
        """
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str


def cli():
    """Entry point for console script."""
    YoutubeVideoFetcher.run_cli(url_help="YouTube video URL")


if __name__ == "__main__":
    cli()
