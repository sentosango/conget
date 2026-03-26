"""Conget Library API for programmatic usage.

This module provides the Conget class which allows using conget
programmatically as a library, without CLI dependencies.
"""

import logging
from typing import Any, Dict, List

from importlib.metadata import entry_points

from src.core.config import get_default_format

logger = logging.getLogger(__name__)


def get_fetchers() -> Dict[str, Any]:
    """Load all fetchers from entry-points.

    Returns:
        Dictionary mapping fetcher names to their classes.
    """
    logger.debug("Loading fetchers from entry-points")

    try:
        eps = entry_points(group="conget.fetchers")
    except TypeError:
        eps = entry_points().get("conget.fetchers", [])

    fetchers = {}
    for ep in eps:
        logger.debug(f"Loading fetcher: {ep.name}")
        try:
            fetchers[ep.name] = ep.load()
        except Exception as e:
            logger.warning(f"Failed to load fetcher {ep.name}: {e}")

    logger.debug(f"Loaded {len(fetchers)} fetcher(s)")
    return fetchers


class Conget:
    """Conget Library API for programmatic content fetching.

    Usage:
        conget = Conget()

        # Fetch content
        content = conget.fetch("https://example.com", format="markdown")

        # Analyze URL
        info = conget.analyze_url("https://github.com/user/repo")

        # List all fetchers
        fetchers = conget.list_fetchers()

        # Select best fetcher for a URL
        fetcher_name = conget.select_fetcher("https://example.com")
    """

    def __init__(self):
        """Initialize Conget instance."""
        logger.debug("Initializing Conget Library API")
        self._fetchers_cache: Dict[str, Any] | None = None

    @property
    def fetchers(self) -> Dict[str, Any]:
        """Lazy load and cache fetchers.

        Returns:
            Dictionary of fetcher classes.
        """
        if self._fetchers_cache is None:
            self._fetchers_cache = get_fetchers()
        return self._fetchers_cache

    def select_fetcher(self, url: str, format: str | None = None) -> str:
        """Select the best fetcher for a URL and format.

        Priority:
        1. Specialized fetchers that can handle the URL
        2. Generic (default) fetcher
        3. First available fetcher

        Args:
            url: The URL to fetch.
            format: Desired output format (optional).

        Returns:
            Name of the best fetcher.

        Raises:
            ValueError: If no fetchers are available.
        """
        logger.debug(f"Selecting best fetcher for URL: {url}")

        if not self.fetchers:
            raise ValueError("No fetchers available")

        # First, try to find a specialized fetcher that can handle the URL
        for name, cls in self.fetchers.items():
            fetcher = cls()
            if fetcher.metadata.is_special and fetcher.can_fetch(url):
                # Check format compatibility
                if format is None or format in fetcher.metadata.supported_formats:
                    logger.debug(f"Selected specialized fetcher: {name}")
                    return name

        # Try non-special fetchers that can handle the URL (except "default")
        for name, cls in self.fetchers.items():
            if name == "default":
                continue
            fetcher = cls()
            if not fetcher.metadata.is_special and fetcher.can_fetch(url):
                if format is None or format in fetcher.metadata.supported_formats:
                    logger.debug(f"Selected non-special fetcher: {name}")
                    return name

        # Fall back to generic fetcher
        if "default" in self.fetchers:
            logger.debug("Selected default fetcher")
            return "default"

        # Fall back to first available fetcher
        first_name = next(iter(self.fetchers))
        logger.debug(f"Selected first available fetcher: {first_name}")
        return first_name

    def fetch(
        self, url: str, format: str | None = None, fetcher_name: str | None = None
    ) -> str:
        """Fetch content from a URL.

        Args:
            url: The URL to fetch from.
            format: The output format (html, markdown, text, json, etc.).
                    If None, uses default format from config.
            fetcher_name: Name of specific fetcher to use.
                         If None, auto-selects the best fetcher.

        Returns:
            The fetched content as a string.

        Raises:
            ValueError: If no fetchers are available or format not supported.
            RuntimeError: If fetching fails.
        """
        if not self.fetchers:
            raise ValueError("No fetchers available")

        # Select fetcher
        if fetcher_name:
            if fetcher_name not in self.fetchers:
                raise ValueError(
                    f"Unknown fetcher '{fetcher_name}'. "
                    f"Available: {', '.join(self.fetchers.keys())}"
                )
            selected_name = fetcher_name
        else:
            selected_name = self.select_fetcher(url, format)

        fetcher_class = self.fetchers[selected_name]
        fetcher = fetcher_class()
        output_format = format or get_default_format()

        # Validate format
        if output_format not in fetcher.supported_formats:
            raise ValueError(
                f"Fetcher '{selected_name}' does not support format '{output_format}'. "
                f"Supported formats: {', '.join(fetcher.supported_formats)}"
            )

        logger.info(f"Using fetcher: {selected_name}")

        try:
            result = fetcher.fetch(url, output_format)
            return result
        except Exception as e:
            logger.error(f"Error fetching content: {e}")
            raise RuntimeError(f"Failed to fetch content: {e}") from e

    def analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze a URL and return available fetchers.

        Args:
            url: The URL to analyze.

        Returns:
            Dictionary with URL info and available fetchers:
            {
                "url": str,
                "available_fetchers": [
                    {
                        "name": str,
                        "description": str,
                        "formats": List[str],
                        "special": bool
                    },
                    ...
                ]
            }

        Raises:
            ValueError: If no fetchers are available.
        """
        if not self.fetchers:
            raise ValueError("No fetchers available")

        logger.debug(f"Analyzing URL: {url}")

        available = []

        for name, cls in self.fetchers.items():
            fetcher = cls()
            if fetcher.can_fetch(url):
                available.append(
                    {
                        "name": name,
                        "description": fetcher.description,
                        "formats": fetcher.supported_formats,
                        "special": fetcher.is_special,
                    }
                )

        # Sort: special fetchers first, then by name
        available.sort(key=lambda x: (not x["special"], x["name"]))

        return {
            "url": url,
            "available_fetchers": available,
        }

    def list_fetchers(self, format: str | None = None) -> List[Dict[str, Any]]:
        """List all available fetchers.

        Args:
            format: Optional filter by supported format.

        Returns:
            List of fetcher dictionaries:
            [
                {
                    "name": str,
                    "description": str,
                    "formats": List[str],
                    "special": bool
                },
                ...
            ]

        Raises:
            ValueError: If no fetchers are available.
        """
        if not self.fetchers:
            raise ValueError("No fetchers available")

        fetchers_list = []

        for name, cls in self.fetchers.items():
            fetcher = cls()

            # Filter by format if specified
            if format and format not in fetcher.supported_formats:
                continue

            fetchers_list.append(
                {
                    "name": name,
                    "description": fetcher.description,
                    "formats": fetcher.supported_formats,
                    "special": fetcher.is_special,
                }
            )

        # Sort: special fetchers first, then by name
        fetchers_list.sort(key=lambda x: (not x["special"], x["name"]))

        return fetchers_list

    def refresh_fetchers(self) -> None:
        """Refresh the fetchers cache.

        Useful when new fetchers are installed or removed.
        """
        logger.debug("Refreshing fetchers cache")
        self._fetchers_cache = None
