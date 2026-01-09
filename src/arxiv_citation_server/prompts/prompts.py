"""
Prompt definitions for citation analysis.

These prompts guide users through common citation analysis workflows.
"""

import mcp.types as types

# Prompt definitions
PROMPTS = {
    "citation-analysis": types.Prompt(
        name="citation-analysis",
        description="""Analyze how a paper is being cited in the literature.

This prompt guides analysis of citation patterns, helping you understand:
- How frequently and where a paper is cited
- What aspects of the paper are being used (Background, Method, Result)
- Whether citations are influential
- Trends in how the paper is received""",
        arguments=[
            types.PromptArgument(
                name="paper_id",
                description="arXiv paper ID to analyze (e.g., '2103.12345')",
                required=True,
            ),
            types.PromptArgument(
                name="focus",
                description="Analysis focus: 'influence' (impact), 'usage' (how it's used), 'criticism' (critical citations), or 'all'",
                required=False,
            ),
            types.PromptArgument(
                name="limit",
                description="Maximum citations to analyze (default: 30)",
                required=False,
            ),
        ],
    ),

    "literature-map": types.Prompt(
        name="literature-map",
        description="""Build a literature review map from citation relationships.

This prompt helps construct a comprehensive view of a research area by:
- Mapping citation relationships around a central paper
- Identifying key papers and their connections
- Discovering research clusters and trends
- Finding seminal works in the field""",
        arguments=[
            types.PromptArgument(
                name="paper_id",
                description="Central paper to map around (arXiv ID)",
                required=True,
            ),
            types.PromptArgument(
                name="depth",
                description="How many citation levels to explore (1-3, default: 2)",
                required=False,
            ),
            types.PromptArgument(
                name="direction",
                description="Direction to explore: 'citations' (who cites this), 'references' (what this cites), or 'both'",
                required=False,
            ),
        ],
    ),

    "find-related-work": types.Prompt(
        name="find-related-work",
        description="""Find papers related to a given paper through citation analysis.

This prompt helps discover related work by examining:
- Papers that cite the same references (co-citation analysis)
- Papers that are cited together (bibliographic coupling)
- Direct citation relationships""",
        arguments=[
            types.PromptArgument(
                name="paper_id",
                description="arXiv paper ID to find related work for",
                required=True,
            ),
            types.PromptArgument(
                name="relationship_type",
                description="Type of relationship: 'cites' (papers this cites), 'cited_by' (papers citing this), or 'both'",
                required=False,
            ),
        ],
    ),
}
