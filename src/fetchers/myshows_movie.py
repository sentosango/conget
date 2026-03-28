"""MyShows.me movie fetcher.

This module provides the MyShowsMovieFetcher class for fetching movie data from MyShows.me.
"""

import json
import logging
import re
from typing import Any, Dict

import requests

from src.core.exceptions import (
    FetchError,
    HTTPError,
    TimeoutError as CongetTimeoutError,
    UnsupportedFormatError,
    ValidationError,
)
from src.core.interfaces import BaseFetcher
from src.core.types import ConfigOption, FetcherMetadata, FetchResult
from src.core.formatters import html_to_markdown

logger = logging.getLogger(__name__)

# Pattern for MyShows.me movie URLs
MYSHOWS_MOVIE_PATTERN = re.compile(r"https?://(?:[\w-]+\.)?myshows\.me/movie/(\d+)")


class MyShowsMovieFetcher(BaseFetcher):
    """Fetcher for MyShows.me movies using HTML parsing."""

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="myshows-movie",
            description="Fetcher for MyShows.me movies (HTML parsing)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "timeout": ConfigOption(
                    default=30, description="Request timeout in seconds"
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if URL is a valid MyShows.me movie page."""
        return bool(MYSHOWS_MOVIE_PATTERN.match(url))

    def fetch(
        self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None
    ) -> FetchResult:
        """Fetch movie data from MyShows.me HTML page."""
        fetch_options = fetch_options or {}

        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching MyShows movie {url} with format {output_format}")

        match = MYSHOWS_MOVIE_PATTERN.match(url)
        if not match:
            raise ValidationError(f"Invalid MyShows.me movie URL: {url}")

        movie_id = int(match.group(1))

        # Get timeout from fetch_options or use default
        timeout = fetch_options.get(
            "timeout",
            self.metadata.config_options["timeout"].default,
        )
        logger.debug(f"Using timeout: {timeout}")

        # Fetch HTML page
        html_content = self._fetch_html(url, timeout)

        # Parse data from HTML
        data = self._parse_html(html_content, movie_id, url)

        # Format output
        if output_format == "json":
            content = json.dumps(data, ensure_ascii=False, indent=2)
        elif output_format == "markdown":
            content = self._format_to_markdown(data)
        else:  # text
            content = self._format_to_text(data)

        return FetchResult(
            content=content,
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
            metadata={"movie_id": movie_id},
        )

    def _fetch_html(self, url: str, timeout: int = 30) -> str:
        """Fetch HTML page from MyShows.me."""
        logger.debug(f"Fetching HTML from: {url}")

        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                },
            )
            response.raise_for_status()
            return response.text

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout fetching {url}: {e}")
            raise CongetTimeoutError(
                f"Request timeout while fetching {url}"
            ) from e
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            logger.error(f"HTTP error fetching {url}: {e}")
            raise HTTPError(
                message=f"HTTP error fetching {url}: {e}",
                status_code=status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            raise FetchError(f"Error fetching {url}: {e}") from e

    def _parse_html(self, html: str, movie_id: int, url: str) -> Dict[str, Any]:
        """Parse movie data from HTML page."""
        data: Dict[str, Any] = {"id": movie_id, "url": url}

        # Extract JSON-LD
        json_ld = self._extract_json_ld(html)
        if json_ld:
            data["json_ld"] = json_ld
            # Map JSON-LD fields to our data structure
            data["title"] = json_ld.get("name", "Фильм без названия")
            data["image"] = json_ld.get("image", "")
            data["duration"] = json_ld.get("timeRequired")  # in minutes
            data["date_published"] = json_ld.get("datePublished", "")
            data["genres"] = json_ld.get("genre", [])
            data["actors"] = [
                actor.get("name") for actor in json_ld.get("actor", [])
                if isinstance(actor, dict)
            ]
            data["country"] = json_ld.get("countryOfOrigin", {}).get("name", "")

            # Rating
            rating_data = json_ld.get("aggregateRating", {})
            if rating_data:
                data["rating"] = rating_data.get("ratingValue")
                data["rating_count"] = rating_data.get("ratingCount")
                data["rating_max"] = rating_data.get("bestRating", "5")

        # Extract description from HTML
        description = self._extract_description(html)
        data["description"] = description

        return data

    def _extract_json_ld(self, html: str) -> Dict[str, Any] | None:
        """Extract JSON-LD data from HTML."""
        pattern = r'<script type="application/ld\+json"[^>]*>([\s\S]*?)</script>'
        match = re.search(pattern, html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON-LD: {e}")
        return None

    def _extract_description(self, html: str) -> str:
        """Extract description from HTML."""
        # Look for <div class="HtmlContent"> inside description section
        pattern = r'<div class="HtmlContent">([\s\S]*?)</div>'
        match = re.search(pattern, html)
        if match:
            description = match.group(1).strip()
            # Convert HTML to markdown for cleaner output
            return html_to_markdown(description)
        return "Описание отсутствует"

    def _format_duration(self, minutes: int | None) -> str:
        """Format duration in minutes to human readable string."""
        if minutes is None:
            return "Не указана"
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours} ч {mins} мин" if mins > 0 else f"{hours} ч"
        return f"{mins} мин"

    def _format_rating(self, rating: str | None, count: str | None, max_rating: str = "5") -> str:
        """Format rating value."""
        if rating is None:
            return "Нет оценок"
        result = f"{rating}/{max_rating}"
        if count:
            result += f" ({count} оценок)"
        return result

    def _format_to_markdown(self, data: Dict[str, Any]) -> str:
        """Convert movie data to Markdown."""
        title = data.get("title", "Фильм без названия")
        image = data.get("image", "")
        duration = self._format_duration(data.get("duration"))
        date_published = data.get("date_published", "Не указана")
        genres = data.get("genres", [])
        country = data.get("country", "Не указана")
        actors = data.get("actors", [])
        description = data.get("description", "Описание отсутствует")
        rating = data.get("rating")
        rating_count = data.get("rating_count")
        rating_max = data.get("rating_max", "5")
        url = data.get("url", "")

        md = f"# {title}\n\n"

        if image:
            md += f"![Постер]({image})\n\n"

        md += f"""## Основная информация

**Дата выхода:** {date_published or "Неизвестно"}
**Длительность:** {duration}
**Страна:** {country or "Неизвестно"}
"""

        if genres:
            if isinstance(genres, list):
                md += f"**Жанры:** {', '.join(genres)}\n"
            else:
                md += f"**Жанр:** {genres}\n"

        md += f"""
## Рейтинг

**MyShows:** {self._format_rating(rating, rating_count, rating_max)}
"""

        if actors:
            md += f"\n## Актёры\n\n{', '.join(actors[:10])}"
            if len(actors) > 10:
                md += f" и ещё {len(actors) - 10}"
            md += "\n"

        if description:
            md += f"""
## Описание

{description}
"""

        md += f"\n**Страница на MyShows:** {url}\n"

        return md

    def _format_to_text(self, data: Dict[str, Any]) -> str:
        """Convert movie data to plain text."""
        md = self._format_to_markdown(data)
        # Simple markdown to text conversion
        text = md
        text = re.sub(r'^# .+$', lambda m: m.group(0)[2:], text, flags=re.MULTILINE)
        text = re.sub(r'^## .+$', lambda m: m.group(0)[3:], text, flags=re.MULTILINE)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'!\[.*?\]\([^)]+\)', '', text)  # Remove images
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'\n{4,}', '\n\n\n', text)  # Max 3 consecutive newlines
        return text.strip()


def cli():
    """Entry point for console script."""
    MyShowsMovieFetcher.run_cli(url_help="MyShows.me movie URL")


if __name__ == "__main__":
    cli()
