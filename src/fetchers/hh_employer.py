"""HH.ru employer fetcher.

This module provides the HHEmployerFetcher class for fetching HH.ru employer data.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

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

# Pattern for HH.ru employer URLs (supports regional subdomains)
HH_EMPLOYER_PATTERN = re.compile(r"https?://(?:[\w-]+\.)?hh\.ru/employer/(\d+)")


class HHEmployerFetcher(BaseFetcher):
    """Fetcher for HH.ru employers using official API."""

    def __init__(self):
        self.base_url = "https://api.hh.ru"

    # Маппинг типов работодателей из справочника HH.ru
    EMPLOYER_TYPE_MAPPING = {
        "company": "Прямой работодатель",
        "agency": "Кадровое агентство",
        "project_director": "Руководитель проекта",
        "private_recruiter": "Частный рекрутер",
        "private_individual": "Частное лицо",
        "self_employed": "Самозанятый",
    }

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="hh-employer",
            description="Fetcher for HH.ru employers (using official API)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "timeout": ConfigOption(
                    default=30, description="Request timeout in seconds"
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        return bool(HH_EMPLOYER_PATTERN.match(url))

    def fetch(self, url: str, output_format: str) -> FetchResult:
        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching HH.ru employer {url} with format {output_format}")

        match = HH_EMPLOYER_PATTERN.match(url)
        if not match:
            raise ValidationError(f"Invalid HH.ru employer URL: {url}")

        employer_id = match.group(1)

        # Fetch data from API
        data = self._fetch_employer_data(employer_id)

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
            metadata={"employer_id": employer_id},
        )

    def _fetch_employer_data(self, employer_id: str) -> Dict[str, Any]:
        """Fetch employer data from hh.ru API."""
        url = f"{self.base_url}/employers/{employer_id}"
        logger.debug(f"Fetching from API: {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout fetching employer {employer_id}: {e}")
            raise CongetTimeoutError(
                f"Request timeout while fetching employer {employer_id}"
            ) from e
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            logger.error(f"HTTP error fetching employer {employer_id}: {e}")
            raise HTTPError(
                message=f"HTTP error fetching employer {employer_id}: {e}",
                status_code=status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching employer {employer_id}: {e}")
            raise FetchError(f"Error fetching employer {employer_id}: {e}") from e

    def _format_employer_type(self, employer_type: Optional[str]) -> str:
        """Format employer type from API response."""
        if not employer_type:
            return "Не указан"
        return self.EMPLOYER_TYPE_MAPPING.get(employer_type, "Не указан")

    def _format_to_markdown(self, data: Dict[str, Any]) -> str:
        """Convert employer data to Markdown."""
        # Basic information
        name = data.get("name", "Работодатель без названия")
        employer_type = self._format_employer_type(data.get("type"))

        # Format description
        description = data.get("description", "")
        if description:
            description = html_to_markdown(description)

        # Get URLs
        website = data.get("site_url", "")
        hh_url = data.get("alternate_url", "")

        # Additional status information
        accredited_it = data.get("accredited_it_employer", False)
        has_divisions = data.get("has_divisions", False)

        # Format area/country information
        area = data.get("area", {})
        area_name = area.get("name", "") if area else ""
        country_code = data.get("country_code", "")

        # Format industries
        industries = data.get("industries", [])
        industries_list = [
            f"- {industry.get('name', '')}"
            for industry in industries
            if industry.get("name")
        ]

        # Format open vacancies count
        open_vacancies = data.get("open_vacancies", 0)

        # Build markdown
        md = f"""# Работодатель: {name}

## Основная информация

**Название работодателя:** {name}
**Тип:** {employer_type}
**Город:** {area_name}
**Страна:** {country_code}
**Количество открытых вакансий:** {open_vacancies}

**Статусы:**
- Аккредитованный IT-работодатель: {"Да" if accredited_it else "Нет"}
- Имеет подразделения: {"Да" if has_divisions else "Нет"}

## Отрасли деятельности

{chr(10).join(industries_list) if industries_list else "Не указаны"}

## Описание компании

{description}

## Ссылки

**Веб-сайт:** {website if website else "не указан"}
**Страница компании на HH.ru:** {hh_url}
"""

        return md

    def _format_to_text(self, data: Dict[str, Any]) -> str:
        """Convert employer data to plain text."""
        markdown = self._format_to_markdown(data)
        return markdown_to_text(markdown)


def cli():
    """Entry point for console script."""
    HHEmployerFetcher.run_cli(url_help="HH.ru employer URL")


if __name__ == "__main__":
    cli()
