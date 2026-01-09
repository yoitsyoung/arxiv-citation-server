# arxiv-citation-server

Citation relationship analysis for arXiv papers using the Semantic Scholar API.

## Overview

This MCP server helps researchers analyze citation relationships between academic papers:
- Search papers on arXiv and Semantic Scholar
- Download papers and convert to markdown
- Discover papers that cite a given work
- Find papers referenced by a work
- Build citation network graphs
- Understand citation contexts and intents

## Installation

### Claude Desktop

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "arxiv-citation-server": {
      "command": "uvx",
      "args": ["arxiv-citation-server"]
    }
  }
}
```

With optional Semantic Scholar API key for higher rate limits:

```json
{
  "mcpServers": {
    "arxiv-citation-server": {
      "command": "uvx",
      "args": ["arxiv-citation-server"],
      "env": {
        "CITATION_S2_API_KEY": "your-api-key"
      }
    }
  }
}
```

### VS Code

Add to your VS Code settings (JSON) or use the MCP extension:

```json
{
  "mcp.servers": {
    "arxiv-citation-server": {
      "command": "uvx",
      "args": ["arxiv-citation-server"],
      "env": {
        "CITATION_S2_API_KEY": "your-api-key"
      }
    }
  }
}
```

Or install via command line:

```bash
code --add-mcp '{"name":"arxiv-citation-server","command":"uvx","args":["arxiv-citation-server"]}'
```

### Cursor

1. Go to **Settings** → **MCP** → **Add new MCP Server**
2. Enter:
   - **Name**: `arxiv-citation-server`
   - **Type**: `command`
   - **Command**: `uvx arxiv-citation-server`

### Other MCP Clients

Use the standard MCP configuration:

```json
{
  "mcpServers": {
    "arxiv-citation-server": {
      "command": "uvx",
      "args": ["arxiv-citation-server"],
      "env": {
        "CITATION_S2_API_KEY": "your-api-key",
        "CITATION_STORAGE_PATH": "/path/to/citations",
        "CITATION_PAPERS_PATH": "/path/to/papers"
      }
    }
  }
}
```

## Configuration

Environment variables (all optional):

| Variable | Description | Default |
|----------|-------------|---------|
| `CITATION_S2_API_KEY` | Semantic Scholar API key (recommended for higher rate limits) | None |
| `CITATION_STORAGE_PATH` | Where to store citation data | `~/.arxiv-citation-server/citations` |
| `CITATION_PAPERS_PATH` | Where to store downloaded papers | `~/.arxiv-citation-server/papers` |
| `CITATION_REQUEST_TIMEOUT` | API timeout in seconds | 60 |
| `CITATION_MAX_CITATIONS` | Max citations per request | 100 |
| `CITATION_MAX_SEARCH_RESULTS` | Max search results | 50 |
| `CITATION_MAX_GRAPH_DEPTH` | Max graph traversal depth | 3 |

### Getting a Semantic Scholar API Key

1. Visit [Semantic Scholar API](https://www.semanticscholar.org/product/api)
2. Sign up for an API key (free for research use)
3. Set the `CITATION_S2_API_KEY` environment variable

Without an API key, you're limited to ~100 requests per 5 minutes. With a key, you get ~1 request per second.

## Storage Format

Data is stored as human-readable markdown:

```
~/.arxiv-citation-server/
├── papers/                      # Downloaded paper content
│   ├── 2103.12345.md           # Full paper as markdown
│   └── 2104.56789.md
│
└── citations/                   # Citation data
    └── 2103.12345/
        ├── paper_info.md       # Paper metadata
        ├── citations.md        # Papers that cite this
        ├── references.md       # Papers this cites
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

## Tools

### Search

| Tool | Description |
|------|-------------|
| `search_papers` | Search for papers on arXiv |
| `search_semantic_scholar` | Search Semantic Scholar for papers by title, author, or keywords |

### Paper Management

| Tool | Description |
|------|-------------|
| `download_paper` | Download a paper and convert to markdown |
| `list_papers` | List all locally stored papers |
| `read_paper` | Read the content of a stored paper |

### Citations

| Tool | Description |
|------|-------------|
| `get_paper_citations` | Get papers that cite a given paper |
| `get_paper_references` | Get papers referenced by a given paper |
| `build_citation_graph` | Build a citation network graph |

## Prompts

| Prompt | Description |
|--------|-------------|
| `citation-analysis` | Analyze how a paper is being cited |
| `literature-map` | Build a literature review map |
| `find-related-work` | Find related papers via citations |

## Development

### Local Installation

```bash
git clone https://github.com/yourusername/arxiv-citation-server.git
cd arxiv-citation-server
uv venv && source .venv/bin/activate
uv pip install -e ".[test]"
```

### Running Locally with MCP Clients

Since this package is not yet published to PyPI, use `uv run` with the `--directory` flag instead of `uvx`:

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "arxiv-citation-server": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/arxiv-citation-server", "arxiv-citation-server"]
    }
  }
}
```

**Cursor**:

1. Go to **Settings** → **MCP** → **Add new MCP Server**
2. Enter:
   - **Name**: `arxiv-citation-server`
   - **Type**: `command`
   - **Command**: `uv run --directory /path/to/arxiv-citation-server arxiv-citation-server`

Replace `/path/to/arxiv-citation-server` with the actual path to the cloned repository.

### Running Tests

```bash
pytest
```

## License

MIT
