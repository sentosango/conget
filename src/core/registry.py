"""Fetcher registry and loader.

This module provides functionality for loading and managing fetchers
through Python entry points.
"""

import logging
from typing import Any, Dict

from importlib.metadata import entry_points

from src.core.exceptions import PluginLoadError

logger = logging.getLogger(__name__)


def get_fetchers() -> Dict[str, Any]:
    """Load all fetchers from entry-points.

    Returns:
        Dictionary mapping fetcher names to their classes.

    Raises:
        PluginLoadError: If a fetcher plugin fails to load.
    """
    logger.debug("Loading fetchers from entry-points")

    try:
        eps = entry_points(group="conget.fetchers")
    except TypeError:
        # Python < 3.10 compatibility
        eps = entry_points().get("conget.fetchers", [])

    fetchers = {}
    for ep in eps:
        logger.debug(f"Loading fetcher: {ep.name}")
        try:
            fetchers[ep.name] = ep.load()
        except Exception as e:
            logger.warning(f"Failed to load fetcher {ep.name}: {e}")
            raise PluginLoadError(
                f"Failed to load fetcher plugin '{ep.name}'",
                plugin_name=ep.name,
            ) from e

    logger.debug(f"Loaded {len(fetchers)} fetcher(s)")
    return fetchers
