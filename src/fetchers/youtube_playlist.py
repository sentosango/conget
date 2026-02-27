"""YouTube playlist fetcher.

This module provides the YoutubePlaylistFetcher class for extracting metadata
from YouTube playlists using yt-dlp (no authentication, no video download).
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

# YouTube playlist URL patterns
YOUTUBE_PLAYLIST_PATTERNS = [
    # Standard playlist format
    re.compile(
        r"(?:https?://)?(?:www\.|m\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)"
    ),
    # Embed format for playlists
    re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/videoseries\?list=([a-zA-Z0-9_-]+)"
    ),
    # List parameter in any URL (watch, etc.) - use simple pattern that searches for list= anywhere
    re.compile(r"[?&]list=([a-zA-Z0-9_-]+)"),
]


def extract_playlist_id(url: str) -> str | None:
    """Extract playlist ID from YouTube URL.

    Args:
        url: YouTube URL (any supported format)

    Returns:
        Playlist ID or None if not found
    """
    # First check if this is a YouTube URL
    if "youtube.com" not in url and "youtu.be" not in url:
        return None

    for pattern in YOUTUBE_PLAYLIST_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return None


def normalize_url(playlist_id: str) -> str:
    """Build canonical YouTube playlist URL from playlist ID.

    Args:
        playlist_id: YouTube playlist ID

    Returns:
        Canonical URL: https://www.youtube.com/playlist?list={playlist_id}
    """
    return f"https://www.youtube.com/playlist?list={playlist_id}"


class YoutubePlaylistFetcher(BaseFetcher):
    """Fetcher for YouTube playlist metadata.

    Extracts metadata from YouTube playlists using yt-dlp without downloading
    videos or requiring authentication.
    """

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="youtube-playlist",
            description="Fetcher for YouTube playlist metadata (using yt-dlp)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "lang": ConfigOption(
                    default="ru",
                    description="Language for metadata (e.g., 'en', 'ru', 'de')",
                ),
                "with_list": ConfigOption(
                    default=True,
                    description="Include video list in output",
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the URL.

        Args:
            url: The URL to check

        Returns:
            True if the URL is a YouTube playlist URL
        """
        return extract_playlist_id(url) is not None

    def fetch(
        self, url: str, output_format: str, fetch_options: dict[str, Any] | None = None
    ) -> FetchResult:
        """Fetch playlist metadata from the URL in the specified format.

        Args:
            url: The YouTube playlist URL to fetch from
            output_format: The output format (markdown, text, json)
            fetch_options: Optional dictionary of fetcher-specific options

        Returns:
            FetchResult containing the playlist metadata

        Raises:
            UnsupportedFormatError: If the format is not supported
            ValidationError: If the URL is not a valid YouTube playlist URL
            FetchError: If fetching fails
        """
        fetch_options = fetch_options or {}

        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching YouTube playlist {url} with format {output_format}")

        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            raise ValidationError(f"Invalid YouTube playlist URL: {url}")

        canonical_url = normalize_url(playlist_id)
        logger.debug(f"Canonical URL: {canonical_url}")

        # Get options from fetch_options or use defaults from metadata
        lang = fetch_options.get(
            "lang",
            self.metadata.config_options["lang"].default,
        )
        with_list = fetch_options.get(
            "with_list",
            self.metadata.config_options["with_list"].default,
        )
        logger.debug(f"Using lang={lang}, with_list={with_list}")

        # yt-dlp options for metadata extraction only
        # extract_flat='in_playlist' for fast video list without full extraction
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
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
            raise FetchError(f"Failed to fetch YouTube playlist metadata: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise FetchError(f"Unexpected error fetching YouTube playlist: {e}") from e

        if not info_dict:
            raise FetchError(f"No metadata returned for playlist {playlist_id}")

        # Extract relevant fields
        playlist_data = self._extract_fields(
            info_dict, playlist_id, canonical_url, with_list
        )
        logger.debug(
            f"Extracted playlist data: id={playlist_data['id']}, title={playlist_data['title']}, video_count={playlist_data['video_count']}"
        )

        # Format output
        content = self._format_output(playlist_data, output_format, with_list)

        return FetchResult(
            content=content,
            url=canonical_url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
            metadata=playlist_data,
        )

    def _extract_fields(
        self,
        info: dict[str, Any],
        playlist_id: str,
        canonical_url: str,
        with_list: bool,
    ) -> dict[str, Any]:
        """Extract relevant metadata fields from yt-dlp info dict.

        Args:
            info: Sanitized info dict from yt-dlp
            playlist_id: YouTube playlist ID
            canonical_url: Canonical YouTube playlist URL
            with_list: Whether to include video list

        Returns:
            Dictionary with extracted metadata
        """
        result = {
            "id": playlist_id,
            "url": canonical_url,
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "channel": info.get("channel", "") or info.get("uploader", ""),
            "channel_url": info.get("channel_url", "") or info.get("uploader_url", ""),
            "video_count": info.get("playlist_count", 0),
        }

        # Extract video list if requested
        if with_list:
            entries = info.get("entries", [])
            videos = []
            for entry in entries:
                if entry:
                    video_data = {
                        "id": entry.get("id", ""),
                        "title": entry.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={entry.get('id', '')}"
                        if entry.get("id")
                        else "",
                        "duration": entry.get("duration"),
                        "duration_string": entry.get("duration_string", ""),
                    }
                    videos.append(video_data)
            result["videos"] = videos
        else:
            result["videos"] = []

        return result

    def _format_output(
        self, data: dict[str, Any], output_format: str, with_list: bool
    ) -> str:
        """Format playlist data for output.

        Args:
            data: Playlist metadata dictionary
            output_format: Output format (markdown, text, json)
            with_list: Whether to include video list

        Returns:
            Formatted string
        """
        if output_format == "json":
            # For JSON, always include videos if with_list was True
            return json.dumps(data, indent=2, ensure_ascii=False)

        # Build markdown
        lines = [
            f"# {data['title']}",
            "",
            f"**URL:** {data['url']}",
        ]

        if data["channel_url"]:
            lines.append(f"**Channel:** [{data['channel']}]({data['channel_url']})")
        else:
            lines.append(f"**Channel:** {data['channel']}")

        lines.append(f"**Videos:** {data['video_count']}")
        lines.append("")
        lines.append("## Description")
        lines.append("")
        lines.append(data["description"] or "(no description)")

        # Add video list if requested
        if with_list and data.get("videos"):
            lines.append("")
            lines.append("## Videos")
            lines.append("")

            for i, video in enumerate(data["videos"], 1):
                duration = video.get("duration_string", "")
                duration_str = f" - {duration}" if duration else ""
                if video["url"]:
                    lines.append(
                        f"{i}. [{video['title']}]({video['url']}){duration_str}"
                    )
                else:
                    lines.append(f"{i}. {video['title']}{duration_str}")

        markdown = "\n".join(lines)

        if output_format == "text":
            return markdown_to_text(markdown)

        return markdown


def cli():
    """Entry point for console script."""
    YoutubePlaylistFetcher.run_cli(url_help="YouTube playlist URL")


if __name__ == "__main__":
    cli()
