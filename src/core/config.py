"""Configuration module for conget."""

import logging
import os
from pathlib import Path
from typing import Any, Dict

import tomlkit

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "default_format": "markdown",
    "default": {},
}


def get_config_dir() -> Path:
    """Get the conget configuration directory.

    Returns:
        Path to ~/.config/conget/
    """
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return Path(config_home) / "conget"


def get_config_path() -> Path:
    """Get the path to the config.toml file.

    Returns:
        Path to ~/.config/conget/config.toml
    """
    return get_config_dir() / "config.toml"


def init_config() -> Dict[str, Any]:
    """Initialize the configuration with default values.

    Creates the config directory and config.toml file if they don't exist.

    Returns:
        The default configuration dictionary.
    """
    config_dir = get_config_dir()
    config_file = get_config_path()

    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created config directory: {config_dir}")

    if not config_file.exists():
        # Write default config generated from fetcher options
        content = generate_config_template()
        config_file.write_text(content)
        logger.debug(f"Created config file: {config_file}")

    return DEFAULT_CONFIG.copy()


def get_config() -> Dict[str, Any]:
    """Load the configuration from ~/.config/conget/config.toml.

    Returns:
        Configuration dictionary. If config file doesn't exist,
        returns default configuration.
    """
    config_file = get_config_path()

    if not config_file.exists():
        logger.debug(f"Config file not found: {config_file}, using defaults")
        return init_config()

    try:
        logger.debug(f"Loading configuration from: {config_file}")
        with open(config_file, "r", encoding="utf-8") as f:
            config = tomlkit.load(f)
        logger.debug("Configuration loaded successfully")
        return config.unwrap()
    except Exception as e:
        logger.warning(f"Failed to load config: {e}, using defaults")
        return DEFAULT_CONFIG.copy()


def get_default_format() -> str:
    """Get the default format from configuration.

    Returns:
        Default format string (e.g., 'markdown').
    """
    config = get_config()
    general = config.get("general", {})
    default_format = general.get("default_format", "markdown")
    logger.debug(f"[FIX] Default format from config: {default_format}")
    return default_format


def get_section_config(section: str) -> Dict[str, Any]:
    """Get configuration for a specific section.

    Args:
        section: Section name (e.g., 'default', 'github-repo', 'hh-vacancy').

    Returns:
        Configuration dictionary for the section.
    """
    config = get_config()
    return config.get(section, {})


def collect_fetcher_options() -> Dict[str, Dict[str, Any]]:
    """Collect config options from all fetchers.

    Returns:
        Dictionary mapping fetcher names to their config options.
    """
    from src.fetchers.conget_default.fetcher import DefaultFetcher
    from src.fetchers.conget_hh_vacancy.fetcher import HHVacancyFetcher
    from src.fetchers.conget_hh_employer.fetcher import HHEmployerFetcher
    from src.fetchers.conget_github_repo.fetcher import GitHubRepoFetcher

    fetchers = [
        DefaultFetcher(),
        HHVacancyFetcher(),
        HHEmployerFetcher(),
        GitHubRepoFetcher(),
    ]

    options = {}
    for fetcher in fetchers:
        options[fetcher.name] = fetcher.config_options

    return options


def generate_config_template() -> str:
    """Generate config.toml template with all fetcher options.

    Returns:
        Config file content as string.
    """
    doc = tomlkit.document()
    doc.add(tomlkit.comment("Conget Configuration"))

    # General section
    general = tomlkit.table()
    general.add("default_format", "markdown")
    doc.add("general", general)

    options = collect_fetcher_options()

    for section_name, section_options in options.items():
        section = tomlkit.table()

        for option_name, option_def in section_options.items():
            default = option_def["default"]
            desc = option_def["description"]

            # Add key-value and inline comment
            item = tomlkit.item(default)
            item.comment(desc)
            section.add(option_name, item)

        doc.add(section_name, section)

    return tomlkit.dumps(doc)


def regenerate_config() -> str:
    """Regenerate the config.toml file from fetcher options.

    Returns:
        Path to the regenerated config file.
    """
    config_file = get_config_path()
    config_dir = get_config_dir()

    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)

    content = generate_config_template()
    config_file.write_text(content, encoding="utf-8")
    logger.debug(f"Regenerated config file: {config_file}")

    return str(config_file)
