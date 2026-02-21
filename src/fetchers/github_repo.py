"""GitHub repository fetcher.

This module provides the GitHubRepoFetcher class for fetching GitHub repository content.
"""

import logging
import re

import trafilatura

from src.core.exceptions import FetchError, UnsupportedFormatError, ValidationError
from src.core.interfaces import BaseFetcher
from src.core.types import ConfigOption, FetcherMetadata, FetchResult

logger = logging.getLogger(__name__)

# Pattern for GitHub repository URLs
GITHUB_REPO_PATTERN = re.compile(r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$")


class GitHubRepoFetcher(BaseFetcher):
    """Fetcher for GitHub repositories.

    Fetches README.md content from GitHub repositories.
    """

    @property
    def metadata(self) -> FetcherMetadata:
        """Return fetcher metadata with all configuration options."""
        return FetcherMetadata(
            name="github-repo",
            description="Fetcher for GitHub repositories (fetches README.md)",
            is_special=True,
            supported_formats=["markdown", "text", "json"],
            config_options={
                "prefer_branch": ConfigOption(
                    default="main",
                    description="Preferred branch to fetch README from (main or master)",
                ),
            },
        )

    def can_fetch(self, url: str) -> bool:
        """Check if this fetcher can handle the URL.

        Args:
            url: The URL to check

        Returns:
            True if the URL is a GitHub repository URL
        """
        return bool(GITHUB_REPO_PATTERN.match(url))

    def fetch(self, url: str, output_format: str) -> FetchResult:
        """Fetch content from the URL in the specified format.

        Args:
            url: The GitHub repository URL to fetch from
            output_format: The output format (markdown, text, json)

        Returns:
            FetchResult containing the fetched README content and metadata

        Raises:
            UnsupportedFormatError: If the format is not supported
            ValidationError: If the URL is not a valid GitHub repository URL
            FetchError: If fetching fails
        """
        if output_format not in self.metadata.supported_formats:
            raise UnsupportedFormatError(
                message=f"Unsupported format: {output_format}. Supported: {self.metadata.supported_formats}",
                output_format=output_format,
                supported=self.metadata.supported_formats,
            )

        logger.info(f"Fetching GitHub repo {url} with format {output_format}")

        match = GITHUB_REPO_PATTERN.match(url)
        if not match:
            raise ValidationError(f"Invalid GitHub repository URL: {url}")

        owner, repo = match.groups()

        # Fetch README.md from GitHub
        readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
        logger.debug(f"Fetching README from: {readme_url}")

        downloaded = trafilatura.fetch_url(readme_url)
        if downloaded is None:
            # Try master branch as fallback
            readme_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
            )
            logger.debug(f"Trying master branch: {readme_url}")
            downloaded = trafilatura.fetch_url(readme_url)

        if downloaded is None:
            raise FetchError(f"Failed to fetch README for {owner}/{repo}")

        # Raw README is already markdown (trafilatura returns str or bytes)
        if isinstance(downloaded, bytes):
            content = downloaded.decode("utf-8", errors="replace")
        else:
            content = downloaded

        if output_format == "json":
            content = (
                f'{{"owner": "{owner}", "repo": "{repo}", "content": {repr(content)}}}'
            )
        elif output_format == "text":
            # Strip markdown formatting
            # Remove headers (# Title)
            content = re.sub(r"^#+\s+", "", content, flags=re.MULTILINE)
            # Remove bold/italic (**text**, *text*)
            content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
            content = re.sub(r"\*([^*]+)\*", r"\1", content)
            # Remove links [text](url) -> text
            content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
            # Remove code blocks
            content = re.sub(r"```[\s\S]*?```", "", content)
            content = re.sub(r"`([^`]+)`", r"\1", content)

        return FetchResult(
            content=content,
            url=url,
            output_format=output_format,
            fetcher_name=self.metadata.name,
            metadata={"owner": owner, "repo": repo},
        )


def cli():
    """Entry point for console script."""
    GitHubRepoFetcher.run_cli(url_help="GitHub repository URL")


if __name__ == "__main__":
    cli()
