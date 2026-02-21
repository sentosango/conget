"""Formatting utilities for converting between different text formats."""

import logging
import re

import markdownify

logger = logging.getLogger(__name__)


def html_to_markdown(html: str, strip_links: bool = True) -> str:
    """Convert HTML to Markdown with proper error handling.

    Args:
        html: HTML string to convert.
        strip_links: If True, removes anchor tags, keeping only text.

    Returns:
        Markdown-formatted string.
    """
    try:
        strip_tags = ["a"] if strip_links else []
        return markdownify.markdownify(html, strip=strip_tags)
    except Exception as e:
        logger.warning(f"Failed to convert HTML to markdown: {e}")
        return html


def markdown_to_text(markdown: str) -> str:
    """Convert Markdown to plain text by removing formatting.

    Args:
        markdown: Markdown-formatted string.

    Returns:
        Plain text string without markdown formatting.
    """
    text = markdown

    # Remove headers (# Title)
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic (**text**, *text*)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    # Remove links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove list markers
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^-{3,}$", "", text, flags=re.MULTILINE)

    return text
