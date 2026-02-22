"""Typed data structures for Conget.

This module provides dataclass definitions for type-safe data handling
throughout the Conget application.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError


@dataclass
class ConfigOption:
    """Represents a configuration option for a fetcher.

    Attributes:
        default: Default value for the option
        description: Human-readable description of the option
    """

    default: Any
    description: str

    def __post_init__(self):
        """Validate that description is not empty."""
        if not self.description:
            raise ValidationError("ConfigOption description cannot be empty")


@dataclass
class FetcherMetadata:
    """Represents metadata about a fetcher.

    Attributes:
        name: Unique name of the fetcher
        description: Human-readable description of what the fetcher does
        is_special: Whether this is a specialized fetcher (vs generic)
        supported_formats: List of output formats the fetcher supports
        config_options: Dictionary mapping option names to ConfigOption instances
    """

    name: str
    description: str
    is_special: bool
    supported_formats: List[str]
    config_options: Dict[str, ConfigOption] = field(default_factory=dict)

    def __post_init__(self):
        """Validate metadata fields."""
        if not self.name:
            raise ValidationError("FetcherMetadata name cannot be empty")
        if not self.supported_formats:
            raise ValidationError(
                "FetcherMetadata must have at least one supported format"
            )


@dataclass
class FetchResult:
    """Represents the result of a fetch operation.

    Attributes:
        content: The fetched content as a string
        url: The URL that was fetched
        output_format: The format of the content (must be in SUPPORTED_FORMATS)
        metadata: Optional dictionary of additional metadata
        fetcher_name: Optional name of the fetcher that produced this result
    """

    content: str
    url: str
    output_format: str
    metadata: Optional[Dict[str, Any]] = None
    fetcher_name: Optional[str] = None

    # Supported formats constant
    SUPPORTED_FORMATS = ["html", "markdown", "text", "xmltei", "json", "csv"]

    def __post_init__(self):
        """Validate that format is supported."""
        if self.output_format not in self.SUPPORTED_FORMATS:
            raise ValidationError(
                f"Unsupported format: {self.output_format}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )


@dataclass
class FetcherMatch:
    """Represents a fetcher that can handle a URL.

    Attributes:
        name: Name of the fetcher
        is_special: Whether this is a specialized fetcher
        supported_formats: List of formats this fetcher supports
        description: Description of the fetcher
        config_options: Dictionary mapping option names to ConfigOption instances
    """

    name: str
    is_special: bool
    supported_formats: List[str]
    description: str
    config_options: Dict[str, ConfigOption] = field(default_factory=dict)

    def __lt__(self, other: "FetcherMatch") -> bool:
        """Sort special fetchers first, then by name.

        Args:
            other: Another FetcherMatch to compare with

        Returns:
            True if this match should come before the other
        """
        if self.is_special != other.is_special:
            return self.is_special > other.is_special
        return self.name < other.name


@dataclass
class AnalysisResult:
    """Represents the result of analyzing which fetchers can handle a URL.

    Attributes:
        url: The URL that was analyzed
        matches: List of fetchers that can handle this URL
    """

    url: str
    matches: List[FetcherMatch] = field(default_factory=list)

    def __post_init__(self):
        """Sort matches with special fetchers first."""
        self.matches = sorted(self.matches)

    def has_matches(self) -> bool:
        """Check if any fetchers are available for this URL.

        Returns:
            True if at least one fetcher can handle the URL
        """
        return len(self.matches) > 0

    def get_best_match(self) -> Optional[FetcherMatch]:
        """Get the best matching fetcher.

        Returns the first special fetcher if available, otherwise the first
        generic fetcher, or None if no fetchers match.

        Returns:
            The best matching FetcherMatch, or None if no matches
        """
        return self.matches[0] if self.matches else None
