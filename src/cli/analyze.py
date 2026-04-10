"""Analyze command for conget CLI."""

import logging
from typing import Annotated, List

import typer

from src.core.registry import get_fetchers
from src.core.types import FetcherMatch

logger = logging.getLogger(__name__)


def complete_url(incomplete: str) -> List[str]:
    """Autocomplete function for URL argument - returns empty list to disable file completion."""
    return []


def analyze(
    urls: Annotated[
        list[str],
        typer.Argument(help="URLs to analyze", autocompletion=complete_url),
    ],
):
    """Execute the analyze command.

    Args:
        urls: URLs to analyze.
    """
    fetchers = get_fetchers()

    if not fetchers:
        print("No fetchers available")
        return

    for url in urls:
        print(f"\n{url}:")
        print("-" * len(url))

        matches = []
        for name, cls in fetchers.items():
            fetcher = cls()
            if fetcher.can_fetch(url):
                matches.append(
                    FetcherMatch(
                        name=name,
                        is_special=fetcher.metadata.is_special,
                        supported_formats=fetcher.metadata.supported_formats,
                        description=fetcher.metadata.description,
                        config_options=fetcher.metadata.config_options,
                    )
                )

        # Sort matches to match fetch selection logic:
        # 1. Special fetchers that can_fetch
        # 2. Non-special fetchers that can_fetch (except fallbacks)
        # 3. "default-defuddle" fetcher (preferred fallback)
        # 4. "default-trafilatura" fetcher
        # Within each group, sort alphabetically by name
        def sort_key(m: FetcherMatch) -> tuple[int, str]:
            if m.is_special:
                return (0, m.name)
            elif m.name == "default-defuddle":
                return (2, m.name)
            elif m.name == "default-trafilatura":
                return (3, m.name)
            else:
                return (1, m.name)

        matches = sorted(matches, key=sort_key)

        if not matches:
            print("  No fetchers available for this URL")
            continue

        for match in matches:
            special_marker = " [SPECIAL]" if match.is_special else ""
            print(f"  {match.name}{special_marker}")
            print(f"    Formats: {', '.join(match.supported_formats)}")
            print(f"    Description: {match.description}")
            if match.config_options:
                print("    Options:")
                for option_name, option in match.config_options.items():
                    print(
                        f"      {option_name}: {option.description} (default: {repr(option.default)})"
                    )
