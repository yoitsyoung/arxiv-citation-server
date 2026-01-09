"""
ArXiv Citation MCP Server
=========================

This module implements an MCP server for citation analysis
using the Semantic Scholar API.
"""

import logging
from typing import Any, Dict, List

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from .config import Settings
from .prompts.handlers import get_prompt as handler_get_prompt
from .prompts.handlers import list_prompts as handler_list_prompts
from .tools import (
    build_graph_tool,
    get_citations_tool,
    get_references_tool,
    handle_build_graph,
    handle_get_citations,
    handle_get_references,
)

# Initialize settings and server
settings = Settings()

# Configure logging
logger = logging.getLogger("arxiv-citation-server")
logger.setLevel(logging.INFO)

# Create MCP server
server = Server(settings.APP_NAME)


@server.list_prompts()
async def list_prompts() -> List[types.Prompt]:
    """List available citation analysis prompts."""
    return await handler_list_prompts()


@server.get_prompt()
async def get_prompt(
    name: str,
    arguments: Dict[str, str] | None = None,
) -> types.GetPromptResult:
    """Get a specific prompt with arguments."""
    return await handler_get_prompt(name, arguments)


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available citation tools."""
    return [
        get_citations_tool,
        get_references_tool,
        build_graph_tool,
    ]


@server.call_tool()
async def call_tool(
    name: str,
    arguments: Dict[str, Any],
) -> List[types.TextContent]:
    """Handle tool calls for citation operations."""
    logger.debug(f"Calling tool {name} with arguments {arguments}")

    try:
        if name == "get_paper_citations":
            return await handle_get_citations(arguments)
        elif name == "get_paper_references":
            return await handle_get_references(arguments)
        elif name == "build_citation_graph":
            return await handle_build_graph(arguments)
        else:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{name}'",
                )
            ]
    except Exception as e:
        logger.error(f"Tool error: {str(e)}")
        return [
            types.TextContent(
                type="text",
                text=f"Error: {str(e)}",
            )
        ]


async def main():
    """Run the MCP server."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Storage path: {settings.STORAGE_PATH}")

    async with stdio_server() as streams:
        await server.run(
            streams[0],
            streams[1],
            InitializationOptions(
                server_name=settings.APP_NAME,
                server_version=settings.APP_VERSION,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(
                        resources_changed=True,
                    ),
                    experimental_capabilities={},
                ),
            ),
        )
