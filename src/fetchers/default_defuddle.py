"""Default defuddle fetcher using defuddle CLI.

This module provides the DefaultDefuddleFetcher class for generic web content
extraction using the defuddle CLI utility (npx defuddle parse).
"""

import json
import logging
import subprocess
from typing import Any, Dict

from src.core.exceptions import FetchError, UnsupportedFormatError
from src.core.interfaces import BaseFetcher
from src.core.types import ConfigOption, FetcherMetadata, FetchResult

logger = logging.getLogger(__name__)


class DefaultDefuddleFetcher(BaseFetcher):
    """Generic fetcher using defuddle CLI for web content extraction.

    Defuddle extracts clean content from web pages, returning structured data
    with title, author, published date, and markdown content.
    """

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="default-defuddle",
            description="Generic web content fetcher using defuddle CLI",
            is_special=False,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "timeout": ConfigOption(
                    default=30, description="Request timeout in seconds"
                ),
                "no_ssl": ConfigOption(
                    default=False, description="Disable SSL verification"
                ),
                "lang": ConfigOption(
                    default="ru",
                    description="Preferred language (en, ru, etc.)",
                ),
                "with_metadata": ConfigOption(
                    default=True,
                    description="Include metadata in extracted content",
                ),
                "only_metadata": ConfigOption(
                    default=False,
                    description="Return only frontmatter without content",
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the URL.

        The defuddle fetcher can handle any URL.

        Args:
            url: The URL to check

        Returns:
            Always returns True
        """
        return True

    def fetch(
        self, url: str, output_format: str, fetch_options: Dict[str, Any] | None = None
    ) -> FetchResult:
        """Fetch content from the URL using defuddle CLI.

        Args:
            url: The URL to fetch from
            output_format: The output format (markdown, text, json)
            fetch_options: Optional configuration options

        Returns:
            FetchResult containing the fetched content

        Raises:
            UnsupportedFormatError: If the format is not supported
            FetchError: If defuddle is not installed or fetching fails
        """
        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        timeout = fetch_options.get("timeout", 30) if fetch_options else 30
        lang = fetch_options.get("lang", "") if fetch_options else ""
        with_metadata = fetch_options.get("with_metadata", True) if fetch_options else True
        only_metadata = fetch_options.get("only_metadata", False) if fetch_options else False

        logger.info(f"Fetching {url} with defuddle (format={output_format}, timeout={timeout})")

        data = self._run_defuddle(url, timeout, lang=lang)

        content = self._format_output(data, output_format, with_metadata=with_metadata, only_metadata=only_metadata)

        logger.debug(f"Defuddle extracted content for {url}: title={data.get('title', 'N/A')}, "
                      f"word_count={data.get('wordCount', 'N/A')}")

        return FetchResult(
            content=content,
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
            metadata={
                "title": data.get("title", ""),
                "author": data.get("author", ""),
                "published": data.get("published", ""),
                "domain": data.get("domain", ""),
                "site": data.get("site", ""),
                "description": data.get("description", ""),
                "word_count": data.get("wordCount", 0),
            },
        )

    def _run_defuddle(self, url: str, timeout: int, *, lang: str = "") -> dict:
        """Run defuddle CLI and return parsed JSON result.

        Args:
            url: The URL to parse
            timeout: Timeout in seconds
            lang: Preferred language (BCP 47, e.g. en, ru, ja)

        Returns:
            Parsed JSON dict from defuddle output

        Raises:
            FetchError: If defuddle is not installed or command fails
        """
        cmd = ["npx", "defuddle", "parse", url, "--json", "--markdown"]
        if lang:
            cmd.extend(["--lang", lang])
        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,
            )
        except FileNotFoundError:
            raise FetchError(
                "npx not found. Install Node.js/npm to use defuddle fetcher"
            )
        except subprocess.TimeoutExpired:
            raise FetchError(f"Defuddle command timed out after {timeout}s for URL: {url}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else "unknown error"
            logger.error(f"Defuddle failed with exit code {e.returncode}: {stderr}")
            raise FetchError(f"Defuddle failed for URL: {url}. Error: {stderr}")

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse defuddle JSON output: {e}")
            raise FetchError(f"Failed to parse defuddle output for URL: {url}")

        logger.debug(f"Defuddle returned keys: {list(data.keys())}")
        return data

    @staticmethod
    def _build_frontmatter(data: dict) -> str:
        """Build YAML frontmatter from defuddle data."""
        parts = ["---"]
        for key, field in [
            ("title", data.get("title", "")),
            ("author", data.get("author", "")),
            ("source", data.get("url", "")),
            ("published", data.get("published", "")),
            ("domain", data.get("domain", "")),
            ("site", data.get("site", "")),
            ("description", data.get("description", "")),
            ("word_count", data.get("wordCount", 0)),
        ]:
            if field:
                parts.append(f"{key}: {json.dumps(field, ensure_ascii=False) if isinstance(field, str) else field}")
        parts.append("---")
        return "\n".join(parts)

    def _format_output(self, data: dict, output_format: str, *, with_metadata: bool = True, only_metadata: bool = False) -> str:
        """Format defuddle data into the requested output format.

        Args:
            data: Parsed JSON dict from defuddle
            output_format: Desired output format
            with_metadata: Include YAML frontmatter in markdown output
            only_metadata: Return only frontmatter without content

        Returns:
            Formatted content string
        """
        if output_format == "json":
            if only_metadata:
                data.pop("content", None)
            return json.dumps(data, ensure_ascii=False, indent=2)

        content = data.get("content") or ""
        title = data.get("title", "")


        if output_format == "markdown":
            if only_metadata:
                return self._build_frontmatter(data)

            parts = []
            if with_metadata:
                parts.append(self._build_frontmatter(data))
                parts.append("")
            if title:
                parts.append(f"# {title}")
                parts.append("")
            parts.append(content)
            return "\n".join(parts)

        # text format — return markdown content as-is (readable as plain text)
        return content


def cli():
    """Entry point for console script."""
    DefaultDefuddleFetcher.run_cli()


if __name__ == "__main__":
    cli()
