"""Custom exceptions for conget fetchers."""


class CongetError(Exception):
    """Base exception for all conget-related errors."""

    pass


class HTTPError(CongetError):
    """Error during HTTP requests."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize HTTPError.

        Args:
            message: Error message.
            status_code: HTTP status code if available.
        """
        super().__init__(message)
        self.status_code = status_code


class FetchError(CongetError):
    """General error during content fetching."""

    pass


class ParsingError(CongetError):
    """Error during parsing HTML/content."""

    pass


class UnsupportedFormatError(CongetError):
    """Error when format is not supported by the fetcher."""

    def __init__(
        self, message: str, output_format: str, supported: list[str] | None = None
    ):
        """Initialize UnsupportedFormatError.

        Args:
            message: Error message.
            output_format: Requested format.
            supported: List of supported formats (optional).
        """
        super().__init__(message)
        self.output_format = output_format
        self.supported = supported


class ValidationError(CongetError):
    """Error during URL/parameter validation."""

    pass


class FetcherNotFoundError(CongetError):
    """Error when a fetcher cannot be found."""

    def __init__(self, message: str, fetcher_name: str | None = None):
        """Initialize FetcherNotFoundError.

        Args:
            message: Error message.
            fetcher_name: Name of the fetcher that was not found.
        """
        super().__init__(message)
        self.fetcher_name = fetcher_name


class PluginLoadError(CongetError):
    """Error during plugin/fetcher loading."""

    def __init__(self, message: str, plugin_name: str | None = None):
        """Initialize PluginLoadError.

        Args:
            message: Error message.
            plugin_name: Name of the plugin that failed to load.
        """
        super().__init__(message)
        self.plugin_name = plugin_name


class TimeoutError(CongetError):
    """Error when operation exceeds timeout."""

    pass
