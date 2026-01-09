"""
ArXiv Citation MCP Server
=========================

This module implements an MCP server for arXiv paper management
and citation analysis using the Semantic Scholar API.
"""

import logging
import sys
from typing import Any, Dict, List

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from .config import Settings
from .prompts.handlers import get_prompt as handler_get_prompt
from .prompts.handlers import list_prompts as handler_list_prompts
from .tools import (
    # Paper tools
    search_papers_tool,
    handle_search_papers,
    search_semantic_scholar_tool,
    handle_search_semantic_scholar,
    download_paper_tool,
    handle_download_paper,
    list_papers_tool,
    handle_list_papers,
    read_paper_tool,
    handle_read_paper,
    # Citation tools
    build_graph_tool,
    get_citations_tool,
    get_references_tool,
    handle_build_graph,
    handle_get_citations,
    handle_get_references,
)

# Initialize settings and server
settings = Settings()

# Configure logging to stderr (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("arxiv-citation-server")

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
    """List available paper and citation tools."""
    return [
        # Paper tools
        search_papers_tool,
        search_semantic_scholar_tool,
        download_paper_tool,
        list_papers_tool,
        read_paper_tool,
        # Citation tools
        get_citations_tool,
        get_references_tool,
        build_graph_tool,
    ]


@server.call_tool()
async def call_tool(
    name: str,
    arguments: Dict[str, Any],
) -> List[types.TextContent]:
    """Handle tool calls for paper and citation operations."""
    logger.debug(f"Calling tool {name} with arguments {arguments}")

    try:
        # Paper tools
        if name == "search_papers":
            return await handle_search_papers(arguments)
        elif name == "search_semantic_scholar":
            return await handle_search_semantic_scholar(arguments)
        elif name == "download_paper":
            return await handle_download_paper(arguments)
        elif name == "list_papers":
            return await handle_list_papers(arguments)
        elif name == "read_paper":
            return await handle_read_paper(arguments)
        # Citation tools
        elif name == "get_paper_citations":
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


async def _async_main():
    """Async entry point for the MCP server."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Papers path: {settings.PAPERS_PATH}")
    logger.info(f"Citations path: {settings.STORAGE_PATH}")

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


def main():
    """Run the MCP server (synchronous entry point)."""
    import asyncio
    asyncio.run(_async_main())
