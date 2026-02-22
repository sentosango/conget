"""Config management CLI command."""

import logging
from typing import Any


def _format_value(value: Any) -> str:
    """Format a value for display as it appears in TOML."""
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        return f'"{value}"'
    return str(value)


def run(args):
    """Handle config command.

    Shows config path, upgrades config with new fetcher options,
    and displays what was added.

    Args:
        args: Parsed argparse arguments.
    """
    logger = logging.getLogger(__name__)

    from src.core.config import AddedItem, get_config_path, upgrade_config

    config_path = get_config_path()
    print(f"Config: {config_path}")
    print()

    logger.debug("Running config upgrade")
    was_upgraded, added_items = upgrade_config()

    if was_upgraded:
        # Group by section for better readability
        sections: dict[str, list[AddedItem]] = {}
        new_sections: set[str] = set()
        updated_sections: set[str] = set()

        for item in added_items:
            if item.type == "section":
                new_sections.add(item.section)
                if item.section not in sections:
                    sections[item.section] = []
            else:
                if item.section not in sections:
                    sections[item.section] = []
                sections[item.section].append(item)
                updated_sections.add(item.section)

        # Print sections
        for i, section in enumerate(sections):
            print(f"  [{section}]")
            for item in sections[section]:
                print(f"    + {item.name} = {_format_value(item.value)}")
            # Add blank line between sections, but not after the last one
            if i < len(sections) - 1:
                print()

        total_options = sum(len(items) for items in sections.values())
        total_sections = len(new_sections) + len(updated_sections)

        if total_options > 0:
            print()
            print(f"Updated: {total_options} item(s) added in {total_sections} section(s)")
    else:
        print("Already up to date")
