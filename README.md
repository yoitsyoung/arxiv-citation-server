# arxiv-citation-server

Citation relationship analysis for arXiv papers using the Semantic Scholar API.

## Overview

This project provides tools to analyze citation relationships between academic papers, helping researchers:
- Discover papers that cite a given work
- Find papers referenced by a work
- Build citation network graphs
- Understand citation contexts and intents

## Architecture

The project follows a clean separation of concerns:

```
arxiv-citation-server/
├── src/arxiv_citation_server/
│   ├── core/           # Pure Python (no MCP deps) - usable by web apps
│   │   ├── models.py   # Pydantic data models
│   │   ├── client.py   # Semantic Scholar API wrapper
│   │   ├── service.py  # CitationService - main business logic
│   │   └── graph.py    # Graph building logic
│   ├── resources/      # Storage management
│   │   └── citations.py # CitationManager - markdown storage
│   ├── tools/          # MCP tools
│   ├── prompts/        # MCP prompts
│   └── server.py       # MCP server entry point
```

### Key Design Decisions

1. **Core Layer is MCP-Independent**: The `core/` module has no MCP dependencies. Web applications can import and use `CitationService` directly.

2. **Human-Readable Storage**: All data is stored as markdown files, making it easy to inspect, edit, and version control.

3. **Separation of Concerns**:
   - `core/` = Business logic (API client, service, models)
   - `resources/` = Storage management
   - `tools/` = MCP tool definitions and handlers
   - `prompts/` = MCP prompt definitions

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/arxiv-citation-server.git
cd arxiv-citation-server

# Create virtual environment
uv venv
source .venv/bin/activate

# Install with dependencies
uv pip install -e .

# Install with test dependencies
uv pip install -e ".[test]"
```

## Usage

### As an MCP Server

Run the server:
```bash
arxiv-citation-server
# or
python -m arxiv_citation_server
```

### As a Python Library (for Web Apps)

```python
from arxiv_citation_server.core import CitationService

# Initialize service
service = CitationService(api_key="optional-s2-api-key")

# Get citations for a paper
citations = await service.get_citations("2103.12345", limit=50)
for cit in citations:
    print(f"{cit.citing_paper.title}")
    for ctx in cit.contexts:
        print(f"  Context: {ctx.text[:100]}...")
        print(f"  Intent: {ctx.intent.value}")

# Get references
references = await service.get_references("2103.12345")

# Build citation graph
graph = await service.build_citation_graph(
    "2103.12345",
    depth=2,
    direction="both"
)
print(f"Found {graph.node_count} papers, {graph.edge_count} relationships")
```

## Configuration

Environment variables (prefixed with `CITATION_`):

| Variable | Description | Default |
|----------|-------------|---------|
| `CITATION_STORAGE_PATH` | Where to store citation data | `~/.arxiv-citation-server/citations` |
| `CITATION_S2_API_KEY` | Semantic Scholar API key (optional) | None |
| `CITATION_REQUEST_TIMEOUT` | API timeout in seconds | 60 |
| `CITATION_MAX_CITATIONS` | Max citations per request | 100 |
| `CITATION_MAX_GRAPH_DEPTH` | Max graph traversal depth | 3 |

## Storage Format

Data is stored as human-readable markdown:

```
~/.arxiv-citation-server/citations/
└── 2103.12345/
    ├── paper_info.md    # Paper metadata
    ├── citations.md     # Papers that cite this
    ├── references.md    # Papers this cites
    └── graph_depth2_both.md  # Citation graph
```

Example `citations.md`:
```markdown
# Papers Citing 2103.12345

*Retrieved: 2025-01-04T10:30:00*
*Total: 42 papers*

---

## 1. BERT: Pre-training of Deep Bidirectional Transformers

**Authors:** Jacob Devlin, Ming-Wei Chang...
**Year:** 2018
**Venue:** NAACL
**arXiv:** [1810.04805](https://arxiv.org/abs/1810.04805)
**Influential:** Yes

### Citation Contexts

> Building on the transformer architecture introduced in [1], we propose...

*Intent: method*

---
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_paper_citations` | Get papers that cite a given arXiv paper |
| `get_paper_references` | Get papers referenced by a given paper |
| `build_citation_graph` | Build a citation network graph |

## MCP Prompts

| Prompt | Description |
|--------|-------------|
| `citation-analysis` | Analyze how a paper is being cited |
| `literature-map` | Build a literature review map |
| `find-related-work` | Find related papers via citations |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=arxiv_citation_server

# Run specific test file
pytest tests/test_models.py
```

## Citation Data

This project uses the [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/). Citation data includes:

- **Citation Contexts**: Text snippets showing how papers cite each other
- **Citation Intents**: Why a paper is cited (Background, Method, Result)
- **Influential Citations**: Whether a citation is particularly significant

## License

MIT
