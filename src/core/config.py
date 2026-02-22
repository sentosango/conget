"""Configuration module for conget."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import tomlkit
from platformdirs import user_config_dir


@dataclass
class AddedItem:
    """Represents an item added during config upgrade."""
    type: str  # "section" or "option"
    section: str
    name: str  # section name for type=section, option name for type=option
    value: Any | None = None  # option value for type=option

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "default_format": "markdown",
    "cache_ttl": 300,
}


def get_config_dir() -> Path:
    """Get the conget configuration directory.

    Returns:
        Path to platform-specific config directory (e.g., ~/.config/conget/ on Linux).
    """
    return Path(user_config_dir("conget"))


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
    default_format = general.get("default_format", DEFAULT_CONFIG["default_format"])
    logger.debug(f"[FIX] Default format from config: {default_format}")
    return default_format


def get_default_cache_ttl() -> int:
    """Get the default cache TTL from configuration.

    Returns:
        Default cache TTL in seconds.
    """
    config = get_config()
    general = config.get("general", {})
    cache_ttl = general.get("cache_ttl", DEFAULT_CONFIG["cache_ttl"])
    return cache_ttl


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
    """Collect config options from all fetchers via registry.

    Loads fetchers dynamically from entry-points instead of hardcoding.
    This ensures new fetchers are automatically discovered.

    Returns:
        Dictionary mapping fetcher names to their config options.
    """
    from src.core.registry import get_fetchers

    logger.debug("Loading fetchers for config options collection")
    fetcher_classes = get_fetchers()
    logger.debug(f"Found {len(fetcher_classes)} fetcher(s) in registry")

    options = {}

    for name, fetcher_cls in fetcher_classes.items():
        try:
            fetcher = fetcher_cls()
            metadata = fetcher.metadata
            options[metadata.name] = metadata.config_options
            logger.debug(f"Loaded config options for fetcher: {metadata.name}")
        except Exception as e:
            logger.warning(f"Failed to load fetcher {name}: {e}")

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
    general.add("default_format", DEFAULT_CONFIG["default_format"])
    general.add("cache_ttl", DEFAULT_CONFIG["cache_ttl"])
    doc.add("general", general)

    options = collect_fetcher_options()

    for section_name, section_options in options.items():
        section = tomlkit.table()

        for option_name, option_def in section_options.items():
            default = option_def.default
            desc = option_def.description

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


def upgrade_config() -> tuple[bool, list[AddedItem] | str]:
    """Upgrade config file with new fetcher options.

    Loads the existing config, compares with available fetcher options,
    and adds any missing sections or options. Preserves user's existing
    values and comments.

    Returns:
        Tuple of (was_upgraded, list of AddedItem or "created new config file").
    """
    config_file = get_config_path()
    logger.debug(f"Starting config upgrade for: {config_file}")

    # Ensure config file exists
    if not config_file.exists():
        logger.debug("Config file doesn't exist, creating new one")
        init_config()

        # Return all sections and options as AddedItem for display
        fetcher_options = collect_fetcher_options()
        added_items: list[AddedItem] = []
        for section_name, section_options in fetcher_options.items():
            added_items.append(AddedItem("section", section_name, section_name))
            for option_name, option_def in section_options.items():
                added_items.append(AddedItem("option", section_name, option_name, option_def.default))
        return (True, added_items)

    # Load existing config as TOML document (preserves comments)
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            doc = tomlkit.load(f)
        logger.debug("Loaded existing config file")
    except Exception as e:
        logger.warning(f"Failed to load config for upgrade: {e}")
        return (False, [])

    # Get all fetcher options
    fetcher_options = collect_fetcher_options()
    added_items: list[AddedItem] = []
    sections_with_additions: set[str] = set()

    # Check each fetcher section
    for section_name, section_options in fetcher_options.items():
        logger.debug(f"Checking section: {section_name}")

        # Create section if it doesn't exist
        if section_name not in doc:
            section = tomlkit.table()
            doc.add(section_name, section)
            added_items.append(AddedItem("section", section_name, section_name))
            logger.info(f"Added new section: [{section_name}]")

        # Get or use the section
        section = doc[section_name] if section_name in doc else doc[section_name]

        # Add missing options
        for option_name, option_def in section_options.items():
            if option_name not in section:
                default = option_def.default
                desc = option_def.description

                # Add with inline comment
                item = tomlkit.item(default)
                item.comment(desc)
                section.add(option_name, item)

                added_items.append(AddedItem("option", section_name, option_name, default))
                sections_with_additions.add(section_name)
                logger.info(f"Added new option: {section_name}.{option_name}")

    # Save if changes were made
    if added_items:
        config_file.write_text(tomlkit.dumps(doc), encoding="utf-8")
        logger.debug(f"Saved upgraded config with {len(added_items)} additions")
        return (True, added_items)

    logger.debug("Config is already up to date")
    return (False, [])
