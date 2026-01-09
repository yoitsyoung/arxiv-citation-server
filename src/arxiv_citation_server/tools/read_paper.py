"""
MCP Tool: read_paper

Read the content of a stored paper.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types

from ..resources import PaperManager

logger = logging.getLogger("arxiv-citation-server")

# Lazy initialization
_manager: PaperManager | None = None


def _get_manager() -> PaperManager:
    """Get or create the paper manager."""
    global _manager
    if _manager is None:
        _manager = PaperManager()
    return _manager


# Tool definition
read_paper_tool = types.Tool(
    name="read_paper",
    description="""Read the content of a downloaded paper.

Returns the full markdown content of a paper that was
previously downloaded. The content includes:
- Paper metadata (title, authors, abstract)
- Full paper text converted from PDF

If the paper hasn't been downloaded yet, use download_paper first.""",
    inputSchema={
        "type": "object",
        "properties": {
            "paper_id": {
                "type": "string",
                "description": "arXiv paper ID (e.g., '2103.12345')",
            },
            "section": {
                "type": "string",
                "description": "Optional: Return only a specific section (e.g., 'abstract', 'introduction')",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum characters to return (default: no limit)",
            },
        },
        "required": ["paper_id"],
    },
)


async def handle_read_paper(arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle the read_paper tool call."""
    try:
        manager = _get_manager()
        paper_id = arguments["paper_id"]
        section = arguments.get("section")
        max_length = arguments.get("max_length")

        # Clean paper ID
        clean_id = paper_id.split("v")[0] if "v" in paper_id else paper_id

        # Check if paper exists
        if not await manager.has_paper(clean_id):
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({
                        "paper_id": clean_id,
                        "error": "Paper not found in storage",
                        "suggestion": f"Use download_paper with paper_id='{paper_id}' to download it first.",
                    }, indent=2),
                )
            ]

        # Get paper content
        content = await manager.get_paper_content(clean_id)

        # Filter by section if requested
        if section:
            content = _extract_section(content, section)
            if not content:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({
                            "paper_id": clean_id,
                            "error": f"Section '{section}' not found in paper",
                            "available_sections": _find_sections(await manager.get_paper_content(clean_id)),
                        }, indent=2),
                    )
                ]

        # Truncate if max_length specified
        truncated = False
        if max_length and len(content) > max_length:
            content = content[:max_length]
            truncated = True

        result = {
            "paper_id": clean_id,
            "content": content,
        }

        if truncated:
            result["truncated"] = True
            result["message"] = f"Content truncated to {max_length} characters"

        if section:
            result["section"] = section

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except ValueError as e:
        logger.error(f"Read paper error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({
                    "paper_id": arguments.get("paper_id"),
                    "error": str(e),
                }, indent=2),
            )
        ]
    except Exception as e:
        logger.error(f"Unexpected read error: {e}")
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]


def _extract_section(content: str, section_name: str) -> str:
    """Extract a specific section from the paper content."""
    section_lower = section_name.lower()
    lines = content.split("\n")

    in_section = False
    section_lines = []
    current_level = 0

    for line in lines:
        # Check for markdown headers
        if line.startswith("#"):
            header_level = len(line) - len(line.lstrip("#"))
            header_text = line.lstrip("#").strip().lower()

            if section_lower in header_text:
                in_section = True
                current_level = header_level
                section_lines.append(line)
            elif in_section and header_level <= current_level:
                # Reached next section of same or higher level
                break
            elif in_section:
                section_lines.append(line)
        elif in_section:
            section_lines.append(line)

    return "\n".join(section_lines).strip()


def _find_sections(content: str) -> list[str]:
    """Find all section headers in the paper."""
    sections = []
    for line in content.split("\n"):
        if line.startswith("#"):
            header = line.lstrip("#").strip()
            if header:
                sections.append(header)
    return sections[:20]  # Limit to first 20 sections
