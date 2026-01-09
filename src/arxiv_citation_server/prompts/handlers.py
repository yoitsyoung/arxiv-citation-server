"""
Handlers for prompt-related requests.

These handlers process prompt requests and generate appropriate
responses for citation analysis workflows.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptMessage,
    TextContent,
)

from .prompts import PROMPTS


# Analysis guidance templates
CITATION_ANALYSIS_GUIDANCE = """
## Citation Analysis for {paper_id}

Please analyze how this paper is being cited in the literature.

### Analysis Focus: {focus}

First, fetch the citations using the `get_paper_citations` tool with:
- paper_id: "{paper_id}"
- limit: {limit}
- include_contexts: true

Then analyze the results to identify:

1. **Citation Volume & Trends**
   - How many papers cite this work?
   - Are citations increasing over time?
   - What venues/fields are citing it?

2. **Citation Intents**
   - Background: Used for historical context
   - Method: The techniques/approaches are being adopted
   - Result: Building on the findings

3. **Influential Citations**
   - Which citations are marked as influential?
   - What makes them influential?

4. **Key Themes**
   - What aspects of the paper are most cited?
   - Are there unexpected uses of the work?

{focus_specific}

Provide a structured summary with specific examples from the citation contexts.
"""

FOCUS_GUIDANCE = {
    "influence": """
### Influence Analysis
Focus on:
- Papers that heavily build on this work
- Highly-cited papers that cite this
- How the paper's ideas have spread
""",
    "usage": """
### Usage Analysis
Focus on:
- How the methodology is being applied
- What domains are using this work
- Adaptations and extensions
""",
    "criticism": """
### Critical Analysis
Focus on:
- Papers that critique or challenge this work
- Alternative approaches that compare to this
- Limitations identified by citing papers
""",
    "all": """
### Comprehensive Analysis
Cover all aspects: influence, usage patterns, and critical reception.
""",
}

LITERATURE_MAP_GUIDANCE = """
## Literature Map for {paper_id}

Please build a comprehensive literature map around this paper.

### Parameters
- Depth: {depth} levels
- Direction: {direction}

First, build the citation graph using `build_citation_graph` with:
- paper_id: "{paper_id}"
- depth: {depth}
- direction: "{direction}"

Then analyze the resulting graph to identify:

1. **Central Papers**
   - Which papers appear most frequently in the graph?
   - What are the most influential nodes?

2. **Research Clusters**
   - Are there distinct groups of related papers?
   - What topics do these clusters represent?

3. **Foundational Works**
   - What are the seminal papers in this area?
   - Which references appear across many papers?

4. **Research Trends**
   - How has the field evolved over time?
   - What are the emerging directions?

5. **Key Relationships**
   - What are the strongest citation chains?
   - Which papers bridge different areas?

Provide a structured map with paper titles, relationships, and insights.
"""

RELATED_WORK_GUIDANCE = """
## Finding Related Work for {paper_id}

Please find papers related to this work through citation analysis.

### Relationship Type: {relationship_type}

{relationship_instructions}

For each related paper found, provide:
1. Title and basic metadata
2. How it relates to the target paper
3. Why it might be relevant

Group related papers by theme or methodology.
"""

RELATIONSHIP_INSTRUCTIONS = {
    "cites": """
Use `get_paper_references` to find papers this work builds on.
These represent the foundational literature for understanding this paper.
""",
    "cited_by": """
Use `get_paper_citations` to find papers that cite this work.
These represent follow-up work and applications of this paper.
""",
    "both": """
Use both `get_paper_references` and `get_paper_citations` to find:
- Papers this work builds on (references)
- Papers that build on this work (citations)

This gives a complete picture of related work.
""",
}


async def list_prompts() -> List[Prompt]:
    """List all available prompts."""
    return list(PROMPTS.values())


async def get_prompt(
    name: str,
    arguments: Optional[Dict[str, str]] = None,
) -> GetPromptResult:
    """
    Get a specific prompt with arguments.

    Args:
        name: The name of the prompt to get.
        arguments: Arguments for the prompt.

    Returns:
        GetPromptResult with the prompt messages.

    Raises:
        ValueError: If prompt not found or required arguments missing.
    """
    if name not in PROMPTS:
        raise ValueError(f"Prompt not found: {name}")

    prompt = PROMPTS[name]
    arguments = arguments or {}

    # Validate required arguments
    for arg in prompt.arguments or []:
        if arg.required and arg.name not in arguments:
            raise ValueError(f"Missing required argument: {arg.name}")

    # Generate prompt content based on type
    if name == "citation-analysis":
        content = _generate_citation_analysis_prompt(arguments)
    elif name == "literature-map":
        content = _generate_literature_map_prompt(arguments)
    elif name == "find-related-work":
        content = _generate_related_work_prompt(arguments)
    else:
        raise ValueError(f"No handler for prompt: {name}")

    return GetPromptResult(
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=content),
            )
        ]
    )


def _generate_citation_analysis_prompt(arguments: Dict[str, str]) -> str:
    """Generate citation analysis prompt content."""
    paper_id = arguments["paper_id"]
    focus = arguments.get("focus", "all")
    limit = arguments.get("limit", "30")

    if focus not in FOCUS_GUIDANCE:
        focus = "all"

    return CITATION_ANALYSIS_GUIDANCE.format(
        paper_id=paper_id,
        focus=focus.title(),
        limit=limit,
        focus_specific=FOCUS_GUIDANCE[focus],
    )


def _generate_literature_map_prompt(arguments: Dict[str, str]) -> str:
    """Generate literature map prompt content."""
    paper_id = arguments["paper_id"]
    depth = arguments.get("depth", "2")
    direction = arguments.get("direction", "both")

    # Validate direction
    if direction not in ("citations", "references", "both"):
        direction = "both"

    return LITERATURE_MAP_GUIDANCE.format(
        paper_id=paper_id,
        depth=depth,
        direction=direction,
    )


def _generate_related_work_prompt(arguments: Dict[str, str]) -> str:
    """Generate related work prompt content."""
    paper_id = arguments["paper_id"]
    relationship_type = arguments.get("relationship_type", "both")

    if relationship_type not in RELATIONSHIP_INSTRUCTIONS:
        relationship_type = "both"

    return RELATED_WORK_GUIDANCE.format(
        paper_id=paper_id,
        relationship_type=relationship_type.title(),
        relationship_instructions=RELATIONSHIP_INSTRUCTIONS[relationship_type],
    )
