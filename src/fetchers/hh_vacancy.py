"""HH.ru vacancy fetcher.

This module provides the HHVacancyFetcher class for fetching HH.ru vacancy data.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

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

# Pattern for HH.ru vacancy URLs (supports regional subdomains)
HH_VACANCY_PATTERN = re.compile(r"https?://(?:[\w-]+\.)?hh\.ru/vacancy/(\d+)")


class HHVacancyFetcher(BaseFetcher):
    """Fetcher for HH.ru vacancies using official API."""

    def __init__(self):
        self.base_url = "https://api.hh.ru"

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="hh-vacancy",
            description="Fetcher for HH.ru job vacancies (using official API)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "timeout": ConfigOption(
                    default=30, description="Request timeout in seconds"
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        return bool(HH_VACANCY_PATTERN.match(url))

    def fetch(self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None) -> FetchResult:
        fetch_options = fetch_options or {}

        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching HH.ru vacancy {url} with format {output_format}")

        match = HH_VACANCY_PATTERN.match(url)
        if not match:
            raise ValidationError(f"Invalid HH.ru vacancy URL: {url}")

        vacancy_id = match.group(1)

        # Get timeout from fetch_options or use default
        timeout = fetch_options.get(
            "timeout",
            self.metadata.config_options["timeout"].default,
        )
        logger.debug(f"Using timeout: {timeout}")

        # Fetch data from API
        data = self._fetch_vacancy_data(vacancy_id, timeout)

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
            metadata={"vacancy_id": vacancy_id},
        )

    def _fetch_vacancy_data(self, vacancy_id: str, timeout: int = 30) -> Dict[str, Any]:
        """Fetch vacancy data from hh.ru API."""
        url = f"{self.base_url}/vacancies/{vacancy_id}"
        logger.debug(f"Fetching from API: {url}")

        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout fetching vacancy {vacancy_id}: {e}")
            raise CongetTimeoutError(
                f"Request timeout while fetching vacancy {vacancy_id}"
            ) from e
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            logger.error(f"HTTP error fetching vacancy {vacancy_id}: {e}")
            raise HTTPError(
                message=f"HTTP error fetching vacancy {vacancy_id}: {e}",
                status_code=status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching vacancy {vacancy_id}: {e}")
            raise FetchError(f"Error fetching vacancy {vacancy_id}: {e}") from e

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date from API response."""
        if not date_str:
            return "Не указана"
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d"
            )
        except (ValueError, AttributeError):
            return "Не указана"

    def _format_salary(self, salary: Optional[Dict[str, Any]]) -> str:
        """Format salary from API response."""
        if not salary:
            return "Не указана"

        currency = salary.get("currency", "")
        currency_symbol = {"RUR": "₽", "USD": "$", "EUR": "€", "KZT": "₸"}.get(
            currency, currency
        )

        from_amount = salary.get("from")
        to_amount = salary.get("to")
        gross = salary.get("gross", True)

        parts = []
        if from_amount:
            parts.append(f"от {from_amount:,}".replace(",", " "))
        if to_amount:
            parts.append(f"до {to_amount:,}".replace(",", " "))
        if not from_amount and not to_amount:
            return "Не указана"

        salary_text = " ".join(parts)
        if currency_symbol:
            salary_text += f" {currency_symbol}"
        if gross:
            salary_text += " (до вычета налогов)"
        else:
            salary_text += " (на руки)"

        return salary_text

    def _format_address(self, address: Optional[Dict[str, Any]]) -> str:
        """Format address from API response."""
        if not address:
            return "Не указан"

        city = address.get("city", "")
        street = address.get("street", "")
        building = address.get("building", "")

        parts = []
        if city:
            parts.append(city)
        if street:
            parts.append(street)
        if building:
            parts.append(building)

        return ", ".join(parts) if parts else "Не указан"

    def _format_key_skills(self, key_skills: List[Any]) -> str:
        """Format key skills list."""
        if not key_skills:
            return "Не указаны"

        skills = []
        for skill in key_skills:
            if isinstance(skill, dict) and "name" in skill:
                skills.append(skill["name"])

        return ", ".join(skills) if skills else "Не указаны"

    def _format_professional_roles(self, professional_roles: List[Any]) -> str:
        """Format professional roles list."""
        if not professional_roles:
            return "Не указано"

        roles = []
        for role in professional_roles:
            if isinstance(role, dict) and "name" in role:
                roles.append(role["name"])

        return ", ".join(roles) if roles else "Не указано"

    def _format_to_markdown(self, data: Dict[str, Any]) -> str:
        """Convert vacancy data to Markdown."""
        # Basic information
        name = data.get("name", "Вакансия без названия")
        employer = data.get("employer", {}).get("name", "Не указан")
        employer_url = data.get("employer", {}).get("alternate_url", "")

        # Format salary
        salary = self._format_salary(data.get("salary"))

        # Format address
        address = self._format_address(data.get("address"))

        # Format area (region)
        area = data.get("area", {})
        area_name = area.get("name", "") if area else ""

        # Format experience, employment, and schedule
        experience = data.get("experience", {}).get("name", "Не указан")
        employment = data.get("employment", {}).get("name", "Не указан")
        schedule = data.get("schedule", {}).get("name", "Не указан")

        # Format professional roles
        professional_roles = self._format_professional_roles(
            data.get("professional_roles", [])
        )

        # Format description
        description = data.get("description", "")
        if description:
            description = html_to_markdown(description)

        # Format branded description
        branded_description = data.get("branded_description", "")
        if branded_description:
            branded_description = html_to_markdown(branded_description)

        # Format key skills
        key_skills = self._format_key_skills(data.get("key_skills", []))

        # Format dates
        created_date = self._format_date(data.get("created_at"))
        published_date = self._format_date(data.get("published_at"))

        # Get URLs and status
        url = data.get("alternate_url", "")

        # State
        archived = data.get("archived", False)

        # Build markdown
        md = f"""# Вакансия: {name}

## Основная информация

**Название вакансии:** {name}
**Профессиональная роль:** {professional_roles}
**Зарплата:** {salary}

**Опыт работы:** {experience}
**Тип занятости:** {employment}
**График работы:** {schedule}

**Компания:** {employer}
**Регион:** {area_name}
**Адрес:** {address}


## Ключевые навыки

{key_skills}


## Описание вакансии

{description}


"""

        # Add branded description if available
        if branded_description:
            md += f"""## Дополнительная информация

{branded_description}


"""

        # Add vacancy state section
        md += f"""## Состояние вакансии

**Дата публикации:** {published_date}
**Дата создания:** {created_date}
**Статус:** {"Неактуальная вакансия (архив)" if archived else "Актуальная вакансия"}


## Ссылки

**Страница вакансии на HH.ru:** {url}
{"**Страница компании на HH.ru:** " + employer_url if employer_url else ""}
"""

        return md

    def _format_to_text(self, data: Dict[str, Any]) -> str:
        """Convert vacancy data to plain text."""
        markdown = self._format_to_markdown(data)
        return markdown_to_text(markdown)


def cli():
    """Entry point for console script."""
    HHVacancyFetcher.run_cli(url_help="HH.ru vacancy URL")


if __name__ == "__main__":
    cli()
