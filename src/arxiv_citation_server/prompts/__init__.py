"""
MCP Prompts for guided citation analysis.

Prompts provide structured interactions for common
citation analysis workflows.
"""

from .prompts import PROMPTS
from .handlers import list_prompts, get_prompt

__all__ = ["PROMPTS", "list_prompts", "get_prompt"]
