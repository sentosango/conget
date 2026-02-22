"""MCP server for conget CLI."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.core.registry import get_fetchers
from src.cli.fetch import select_best_fetcher
from src.core.config import get_default_format, get_default_cache_ttl, merge_cli_options

logger = logging.getLogger(__name__)

# Create MCP server
app = Server("conget-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="fetch",
            description="Fetch content from a URL using best available fetcher",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch content from",
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format (html, markdown, text, json, xmltei, csv)",
                        "enum": ["html", "markdown", "text", "json", "xmltei", "csv"],
                    },
                    "fetcher": {
                        "type": "string",
                        "description": "Specific fetcher to use (default: auto-select)",
                    },
                    "options": {
                        "type": "object",
                        "description": "Fetcher-specific options (e.g., {\"with_subs\": false})",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="analyze",
            description="Analyze URLs to see which fetchers can handle them",
            inputSchema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of URLs to analyze",
                    }
                },
                "required": ["urls"],
            },
        ),
    ]


async def fetch_url_handler(arguments: Any) -> list[TextContent]:
    """Fetch content from a URL."""
    url = arguments.get("url")
    output_format = arguments.get("format") or get_default_format()
    fetcher_name = arguments.get("fetcher")
    cli_options = arguments.get("options")

    logger.info(f"Fetching URL: {url} with format: {output_format}")

    fetchers = get_fetchers()

    if fetcher_name:
        if fetcher_name not in fetchers:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Unknown fetcher '{fetcher_name}'. Available: {', '.join(fetchers.keys())}",
                )
            ]
    else:
        fetcher_name = select_best_fetcher(fetchers, url, output_format)

    fetcher_class = fetchers[fetcher_name]
    fetcher = fetcher_class()

    # Merge CLI options with config file values
    merged_options = merge_cli_options(fetcher.metadata.name, cli_options)

    try:
        if output_format not in fetcher.metadata.supported_formats:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Fetcher '{fetcher_name}' does not support format '{output_format}'. Supported: {', '.join(fetcher.metadata.supported_formats)}",
                )
            ]

        result = fetcher.fetch_with_cache(
            url,
            output_format,
            cache_ttl=get_default_cache_ttl(),
            fetch_options=merged_options,
        )
        return [TextContent(type="text", text=result.content)]

    except Exception as e:
        logger.error(f"Error fetching URL: {e}")
        return [TextContent(type="text", text=f"Error: {e}")]


async def analyze_urls_handler(arguments: Any) -> list[TextContent]:
    """Analyze URLs to see which fetchers can handle them."""
    urls = arguments.get("urls", [])
    fetchers = get_fetchers()

    if not urls:
        return [TextContent(type="text", text="Error: No URLs provided")]

    output_lines = []

    for url in urls:
        output_lines.append(f"\n{url}:")
        output_lines.append("-" * len(url))

        available = []
        for fetcher_name, cls in fetchers.items():
            fetcher = cls()
            if fetcher.can_fetch(url):
                config_options = {}
                for opt_name, opt_value in fetcher.metadata.config_options.items():
                    config_options[opt_name] = {
                        "default": opt_value.default,
                        "description": opt_value.description,
                    }

                available.append(
                    {
                        "name": fetcher_name,
                        "special": fetcher.metadata.is_special,
                        "formats": fetcher.metadata.supported_formats,
                        "description": fetcher.metadata.description,
                        "config_options": config_options,
                    }
                )

        if not available:
            output_lines.append("  No fetchers available for this URL")
            continue

        for f in sorted(available, key=lambda x: (not x["special"], x["name"])):
            special_marker = " [SPECIAL]" if f["special"] else ""
            output_lines.append(f"  {f['name']}{special_marker}")
            output_lines.append(f"    Formats: {', '.join(f['formats'])}")
            output_lines.append(f"    Description: {f['description']}")
            if f["config_options"]:
                output_lines.append(f"    Config Options:")
                for opt_name, opt_info in f["config_options"].items():
                    output_lines.append(
                        f"      {opt_name}: {opt_info['default']} - {opt_info['description']}"
                    )

    return [TextContent(type="text", text="\n".join(output_lines))]


@app.call_tool()
async def call_tool_handler(name: str, arguments: Any) -> list[TextContent]:
    """Route tool calls to appropriate handlers."""
    handlers = {
        "fetch": fetch_url_handler,
        "analyze": analyze_urls_handler,
    }

    if name not in handlers:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return await handlers[name](arguments)


async def run_async():
    """Start the MCP server asynchronously."""
    logger.info("Starting conget MCP server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run(_args):
    """Start the MCP server."""
    asyncio.run(run_async())
