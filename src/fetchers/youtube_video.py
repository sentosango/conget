"""YouTube video fetcher.

This module provides the YoutubeVideoFetcher class for extracting metadata
from YouTube videos using yt-dlp (no authentication, no video download).
"""

import json
import logging
import re
from typing import Any, Dict

import requests
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
                "with_subs": ConfigOption(
                    default=True,
                    description="Include subtitles/transcript in output",
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

    def fetch(self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None) -> FetchResult:
        """Fetch video metadata from the URL in the specified format.

        Args:
            url: The YouTube video URL to fetch from
            output_format: The output format (markdown, text, json)
            fetch_options: Optional dictionary of fetch options

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

        # Use merged options from fetch_options, falling back to metadata defaults
        options = fetch_options or {}
        lang = options.get("lang", self.metadata.config_options["lang"].default)
        with_subs_raw = options.get("with_subs")

        # Convert with_subs to boolean, handling potential string/bool values
        if with_subs_raw is None:
            with_subs = self.metadata.config_options["with_subs"].default
        elif isinstance(with_subs_raw, bool):
            with_subs = with_subs_raw
        else:
            with_subs = bool(with_subs_raw)

        logger.debug(f"with_subs: raw={with_subs_raw!r}, converted={with_subs}")

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

        # Add subtitle extraction if requested
        if with_subs:
            ydl_opts["writesubtitles"] = True
            ydl_opts["subtitleslangs"] = [lang]
            logger.debug(f"Extracting subtitles with language: {lang}")

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
        video_data = self._extract_fields(info_dict, video_id, canonical_url, lang, with_subs)
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

    def _extract_fields(self, info: dict[str, Any], video_id: str, canonical_url: str, lang: str, with_subs: bool) -> dict[str, Any]:
        """Extract relevant metadata fields from yt-dlp info dict.

        Args:
            info: Sanitized info dict from yt-dlp
            video_id: YouTube video ID
            canonical_url: Canonical YouTube URL
            lang: Priority language for subtitles
            with_subs: Whether to extract subtitles

        Returns:
            Dictionary with extracted metadata
        """
        result = {
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

        # Extract subtitles if requested
        if with_subs:
            subtitles = self._extract_subtitles(info, lang)
            result["subtitles"] = subtitles
        else:
            result["subtitles"] = None

        return result

    def _extract_subtitles(self, info: dict[str, Any], lang: str) -> dict[str, Any] | None:
        """Extract subtitle content from yt-dlp info dict.

        Args:
            info: Sanitized info dict from yt-dlp
            lang: Priority language for subtitle extraction

        Returns:
            Dictionary with lang and text keys, or None if no subtitles found
        """
        def _fetch_subtitle_text(url: str) -> str | None:
            """Fetch subtitle JSON from URL and extract text."""
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                # Extract text from events structure
                text_parts = []
                if "events" in data:
                    for event in data["events"]:
                        if "segs" in event:
                            for seg in event["segs"]:
                                if "utf8" in seg:
                                    text_parts.append(seg["utf8"])

                # Join without adding extra spaces - YouTube API already has proper spacing
                full_text = "".join(text_parts)
                return full_text if full_text else None
            except Exception as e:
                logger.warning(f"Failed to fetch subtitle from URL: {e}")
                return None

        # Try manual subtitles in preferred language
        subtitles = info.get("subtitles", {})
        if lang in subtitles:
            lang_subtitles = subtitles[lang]
            if lang_subtitles:
                subtitle_entry = lang_subtitles[0] if isinstance(lang_subtitles, list) else lang_subtitles
                if "data" in subtitle_entry:
                    logger.debug(f"Found manual subtitles in language: {lang}")
                    return {"lang": lang, "text": subtitle_entry["data"]}
                elif "url" in subtitle_entry:
                    text = _fetch_subtitle_text(subtitle_entry["url"])
                    if text:
                        logger.debug(f"Found manual subtitles in language: {lang}")
                        return {"lang": lang, "text": text}

        # Try auto-generated captions in preferred language
        auto_captions = info.get("automatic_captions", {})
        if lang in auto_captions:
            lang_captions = auto_captions[lang]
            if lang_captions:
                caption_entry = lang_captions[0] if isinstance(lang_captions, list) else lang_captions
                if "url" in caption_entry:
                    text = _fetch_subtitle_text(caption_entry["url"])
                    if text:
                        logger.debug(f"Using auto-generated captions in language: {lang}")
                        return {"lang": lang, "text": text}

        # Try any available manual subtitle
        if subtitles:
            first_lang = next(iter(subtitles))
            if first_lang:
                first_subtitles = subtitles[first_lang]
                subtitle_entry = first_subtitles[0] if isinstance(first_subtitles, list) else first_subtitles
                if "data" in subtitle_entry:
                    logger.debug(f"Using manual subtitles in language: {first_lang}")
                    return {"lang": first_lang, "text": subtitle_entry["data"]}
                elif "url" in subtitle_entry:
                    text = _fetch_subtitle_text(subtitle_entry["url"])
                    if text:
                        logger.debug(f"Using manual subtitles in language: {first_lang}")
                        return {"lang": first_lang, "text": text}

        # Try any available auto caption
        if auto_captions:
            first_lang = next(iter(auto_captions))
            if first_lang:
                first_captions = auto_captions[first_lang]
                caption_entry = first_captions[0] if isinstance(first_captions, list) else first_captions
                if "url" in caption_entry:
                    text = _fetch_subtitle_text(caption_entry["url"])
                    if text:
                        logger.debug(f"Using auto-generated captions in language: {first_lang}")
                        return {"lang": first_lang, "text": text}

        logger.debug(f"No subtitles found for video")
        return None

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

        # Add subtitles if present
        if data.get('subtitles'):
            subtitles = data['subtitles']
            # Add blockquote indentation to each line of subtitle text
            sub_text = subtitles.get('text', '(no text)')
            indented_text = "\n".join(f"    {line}" for line in sub_text.split("\n") if line.strip())

            lines.extend([
                "",
                "## Subtitles",
                "",
                f"**Language:** {subtitles.get('lang', 'unknown')}",
                "",
                indented_text,
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
