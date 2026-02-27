"""Cache management for Conget fetchers.

This module provides the CacheManager class for caching fetch results
to reduce redundant network requests.
"""

import hashlib
import json
import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from platformdirs import user_cache_dir
from src.core.types import FetchResult

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages file-based caching for fetch results.

    Uses XDG cache directory on Linux (~/.cache/conget/), platform-specific
    directories on other systems.

    Attributes:
        namespace: Cache namespace (typically fetcher name).
        cache_dir: Base cache directory path.
    """

    CACHE_APP_NAME = "conget"

    def __init__(self, namespace: str = "default"):
        """Initialize cache manager.

        Args:
            namespace: Cache namespace for organizing cached items.
        """
        self.namespace = namespace
        self.cache_dir = Path(user_cache_dir(self.CACHE_APP_NAME)) / namespace
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Failed to create cache directory: {e}")

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key.

        Args:
            key: Cache key string.

        Returns:
            Path to the cache file.
        """
        # Use SHA256 hash of key as filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    @staticmethod
    def generate_key(
        url: str, output_format: str, options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a cache key from fetch parameters.

        Args:
            url: The URL being fetched.
            output_format: The output format.
            options: Optional fetcher-specific options.

        Returns:
            A cache key string.
        """
        parts = [url, output_format]
        if options:
            # Sort options for consistent keys
            sorted_options = sorted(options.items())
            parts.extend(f"{k}={v}" for k, v in sorted_options)
        return "|".join(parts)

    def get(self, key: str, ttl: int = 0) -> Optional[FetchResult]:
        """Retrieve a cached result if it exists and is not expired.

        Args:
            key: Cache key.
            ttl: Time-to-live in seconds. If 0, cache is disabled.

        Returns:
            FetchResult if cached and valid, None otherwise.
        """
        if ttl <= 0:
            return None

        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check expiration
            cached_at = data.get("cached_at", 0)
            if time.time() - cached_at > ttl:
                return None

            # Reconstruct FetchResult
            result_data = data.get("result")
            if result_data:
                return FetchResult(**result_data)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to read cache: {e}")

        return None

    def set(self, key: str, result: FetchResult) -> bool:
        """Store a fetch result in cache.

        Args:
            key: Cache key.
            result: FetchResult to cache.

        Returns:
            True if cached successfully, False otherwise.
        """
        cache_path = self._get_cache_path(key)

        try:
            data = {
                "cached_at": time.time(),
                "result": asdict(result),
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except (OSError, TypeError) as e:
            logger.warning(f"Failed to write cache: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a cached item.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False if not found or error.
        """
        cache_path = self._get_cache_path(key)

        try:
            if cache_path.exists():
                cache_path.unlink()
                return True
        except OSError as e:
            logger.warning(f"Failed to delete cache: {e}")

        return False

    def clear(self) -> int:
        """Clear all cached items for this namespace.

        Returns:
            Number of items cleared.
        """
        count = 0

        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    count += 1
                except OSError as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")
        except OSError as e:
            logger.warning(f"Failed to clear cache directory: {e}")

        return count
