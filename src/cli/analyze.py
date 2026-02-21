"""Analyze command for conget CLI."""

import logging

from src.core.registry import get_fetchers
from src.core.types import AnalysisResult, FetcherMatch

logger = logging.getLogger(__name__)


def run(args):
    """Execute the analyze command.

    Args:
        args: Parsed command-line arguments.
    """
    fetchers = get_fetchers()

    if not fetchers:
        print("No fetchers available")
        return

    for url in args.urls:
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
                    )
                )

        result = AnalysisResult(url=url, matches=matches)

        if not result.has_matches():
            print("  No fetchers available for this URL")
            continue

        for match in result.matches:
            special_marker = " [SPECIAL]" if match.is_special else ""
            print(f"  {match.name}{special_marker}")
            print(f"    Formats: {', '.join(match.supported_formats)}")
            print(f"    Description: {match.description}")
