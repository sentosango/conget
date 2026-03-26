"""MyShows.me TV show fetcher.

This module provides the MyShowsShowFetcher class for fetching TV show data from MyShows.me.
"""

import json
import logging
import re
from datetime import datetime
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
from src.core.formatters import html_to_markdown, markdown_to_text

logger = logging.getLogger(__name__)

# Pattern for MyShows.me show URLs (supports subdomains like en.myshows.me)
MYSHOWS_SHOW_PATTERN = re.compile(r"https?://(?:[\w-]+\.)?myshows\.me/view/(\d+)")


class MyShowsShowFetcher(BaseFetcher):
    """Fetcher for MyShows.me TV shows using official JSON-RPC API."""

    def __init__(self):
        self.api_url = "https://api.myshows.me/v2/rpc/"

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="myshows-show",
            description="Fetcher for MyShows.me TV shows (using official API)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "timeout": ConfigOption(
                    default=30, description="Request timeout in seconds"
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if URL is a valid MyShows.me show page."""
        return bool(MYSHOWS_SHOW_PATTERN.match(url))

    def fetch(
        self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None
    ) -> FetchResult:
        """Fetch TV show data from MyShows.me API."""
        fetch_options = fetch_options or {}

        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching MyShows show {url} with format {output_format}")

        match = MYSHOWS_SHOW_PATTERN.match(url)
        if not match:
            raise ValidationError(f"Invalid MyShows.me URL: {url}")

        show_id = int(match.group(1))

        # Get timeout from fetch_options or use default
        timeout = fetch_options.get(
            "timeout",
            self.metadata.config_options["timeout"].default,
        )
        logger.debug(f"Using timeout: {timeout}")

        # Fetch data from API
        data = self._fetch_show_data(show_id, timeout)

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
            metadata={"show_id": show_id},
        )

    def _fetch_show_data(self, show_id: int, timeout: int = 30) -> Dict[str, Any]:
        """Fetch show data from MyShows.me JSON-RPC API."""
        payload = {
            "jsonrpc": "2.0",
            "method": "shows.GetById",
            "params": {"showId": show_id},
            "id": 1,
        }

        logger.debug(f"Fetching from API: {self.api_url} with payload: {payload}")

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=timeout,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                },
            )
            response.raise_for_status()

            result = response.json()

            # Check for JSON-RPC error
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown API error")
                logger.error(f"API error for show {show_id}: {error_msg}")
                raise FetchError(f"MyShows API error: {error_msg}")

            return result.get("result", {})

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout fetching show {show_id}: {e}")
            raise CongetTimeoutError(
                f"Request timeout while fetching show {show_id}"
            ) from e
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            logger.error(f"HTTP error fetching show {show_id}: {e}")
            raise HTTPError(
                message=f"HTTP error fetching show {show_id}: {e}",
                status_code=status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching show {show_id}: {e}")
            raise FetchError(f"Error fetching show {show_id}: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response: {e}")
            raise FetchError(f"Failed to parse API response: {e}") from e

    def _format_status(self, status: str | None) -> str:
        """Format show status."""
        status_map = {
            "Returning Series": "Продолжается",
            "Continuing": "Продолжается",
            "New Series": "Новый сериал",
            "Ended": "Завершён",
            "Canceled": "Отменён",
            "TBD": "Статус неизвестен",
            "Pilot": "Пилотная серия",
        }
        if status is None:
            return "Не указан"
        return status_map.get(status, status)

    def _format_date(self, date_str: str | None) -> str:
        """Format date string from API."""
        if not date_str:
            return "Не указана"
        try:
            # API returns dates like "Dec/25/2020"
            dt = datetime.strptime(date_str, "%b/%d/%Y")
            return dt.strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            return date_str

    def _format_rating(self, rating: float | None, votes: int | None = None) -> str:
        """Format rating value."""
        if rating is None:
            return "Нет оценок"

        result = f"{rating:.1f}/10"
        if votes:
            result += f" ({votes:,} оценок)".replace(",", " ")
        return result

    def _format_to_markdown(self, data: Dict[str, Any]) -> str:
        """Convert show data to Markdown."""
        title = data.get("title", "Сериал без названия")
        title_original = data.get("titleOriginal", "")
        year = data.get("year", "Не указан")
        status = self._format_status(data.get("status"))
        runtime = data.get("runtime")
        runtime_total = data.get("runtimeTotal", "")
        total_seasons = data.get("totalSeasons", 0)

        # Country
        country_title = data.get("countryTitle", "")

        # Network
        network_data = data.get("network", {})
        network_title = (
            network_data.get("title", "") if isinstance(network_data, dict) else ""
        )

        # Ratings
        rating = data.get("rating")
        voted = data.get("voted")
        myshows_rating = self._format_rating(rating, voted)

        imdb_rating = data.get("imdbRating")
        imdb_voted = data.get("imdbVoted")
        imdb_rating_str = self._format_rating(imdb_rating, imdb_voted)

        kinopoisk_rating = data.get("kinopoiskRating")
        kinopoisk_voted = data.get("kinopoiskVoted")
        kinopoisk_rating_str = self._format_rating(kinopoisk_rating, kinopoisk_voted)

        # Watching stats
        watching = data.get("watching", 0)
        watching_total = data.get("watchingTotal", 0)
        watching_formatted = f"{watching:,}".replace(",", " ")
        watching_total_formatted = f"{watching_total:,}".replace(",", " ")

        # Description
        description = data.get("description", "Описание отсутствует")
        if description:
            description = html_to_markdown(description)

        # Image and URL
        image = data.get("image", "")
        show_url = f"https://myshows.me/view/{data.get('id', '')}/"

        # External links
        imdb_url = data.get("imdbUrl", "")
        kinopoisk_url = data.get("kinopoiskUrl", "")

        # Dates
        started = self._format_date(data.get("started"))
        ended = self._format_date(data.get("ended"))

        # Build markdown
        md = f"# {title}\n\n"

        if title_original:
            md += f"**Оригинальное название:** {title_original}\n\n"

        md += f"""## Основная информация

**Год:** {year}
**Статус:** {status}
**Сезонов:** {total_seasons}
"""
        if runtime:
            md += f"**Длительность эпизода:** {runtime} мин.\n"
        if runtime_total:
            md += f"**Общая длительность:** {runtime_total}\n"

        md += f"""
**Страна:** {country_title or "Не указана"}
**Сеть:** {network_title or "Не указана"}

**Дата начала:** {started}
"""
        if ended and ended != "Не указана":
            md += f"**Дата окончания:** {ended}\n"

        md += f"""
## Рейтинги

**MyShows:** {myshows_rating}
**IMDb:** {imdb_rating_str}
**Кинопоиск:** {kinopoisk_rating_str}

## Популярность

**Смотрят сейчас:** {watching_formatted} человек
**Всего смотрели:** {watching_total_formatted} человек

## Описание

{description}
"""

        # Add external links
        external_links = []
        if imdb_url:
            external_links.append(f"[IMDb]({imdb_url})")
        if kinopoisk_url:
            external_links.append(f"[Кинопоиск]({kinopoisk_url})")

        if external_links:
            md += f"\n\n## Внешние ссылки\n\n{' • '.join(external_links)}\n"

        # Add image link if available
        if image:
            md += f"\n**Постер:** {image}\n"

        # Add MyShows page link
        md += f"\n**Страница на MyShows:** {show_url}\n"

        # Add episodes if available
        episodes = data.get("episodes", [])
        if episodes:
            md += "\n\n## Эпизоды\n\n"
            current_season = None
            for episode in sorted(
                episodes,
                key=lambda e: (e.get("seasonNumber", 0), e.get("episodeNumber", 0)),
            ):
                season = episode.get("seasonNumber", 0)
                if season != current_season:
                    current_season = season
                    md += f"\n### Сезон {season}\n\n"

                episode_num = episode.get("episodeNumber", 0)
                episode_title = episode.get("title", "Без названия")
                short_name = episode.get("shortName", "")
                air_date = episode.get("airDate", "")
                is_special = episode.get("isSpecial", False)

                title_display = episode_title or short_name or "Без названия"
                special_marker = " (спецвыпуск)" if is_special else ""

                md += f"**{episode_num}.** {title_display}{special_marker}"
                if air_date:
                    try:
                        dt = datetime.fromisoformat(air_date.replace("Z", "+00:00"))
                        md += f" ({dt.strftime('%d.%m.%Y')})"
                    except (ValueError, TypeError):
                        pass
                md += "\n"

        return md

    def _format_to_text(self, data: Dict[str, Any]) -> str:
        """Convert show data to plain text."""
        markdown = self._format_to_markdown(data)
        return markdown_to_text(markdown)


def cli():
    """Entry point for console script."""
    MyShowsShowFetcher.run_cli(url_help="MyShows.me show URL")


if __name__ == "__main__":
    cli()
