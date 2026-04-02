---
name: adding-knowledge
description: Use when an agent needs to search documents, PDFs, or reference material — covers R2R collection setup, document ingestion, Knowledge MCP wiring, per-tenant collection scoping, and knowledge package architecture
---

# Adding Knowledge to Agents

## Overview

Agent2 agents access knowledge through R2R (hybrid search) via Knowledge MCP. You add PDFs or documents to a collection, the agent searches them at runtime. No hardcoding of domain rules — the agent learns from books.

## When to Activate

- Agent needs to look up rules, standards, or reference material
- User says "add knowledge", "add books", "ingest documents", "RAG"
- Agent needs different knowledge per client/tenant/context
- User wants to replace hardcoded lookup tables with searchable knowledge

## Architecture

```
PDFs / Documents
  → R2R ingestion (chunking, embedding, indexing)
  → Searchable collection
  → Knowledge MCP server (FastMCP wrapper)
  → Agent calls search() and get_passage() via toolsets=
```

## Step-by-Step

### 1. Create Collection Directory

```bash
mkdir -p knowledge/books/my-collection/
# Place PDFs, markdown, or text files here
```

### 2. Register in collections.yaml

```yaml
# knowledge/collections.yaml
collections:
  my-collection:
    description: "What these documents contain"
    books_dir: books/my-collection/
    agents:
      - my-agent
```

### 3. Ingest Documents

```bash
# Start the full stack (includes R2R)
docker compose --profile full up -d

# Ingest all collections
python -m shared.ingest --all

# Or a specific collection
python -m shared.ingest --collection my-collection --dir knowledge/books/my-collection/
```

### 4. Wire Agent to Knowledge MCP

```python
# agents/my-agent/agent.py
from pydantic_ai.mcp import MCPServerStreamableHTTP

knowledge_mcp_url = os.environ.get("KNOWLEDGE_MCP_URL", "http://localhost:9090/mcp")
knowledge_server = MCPServerStreamableHTTP(knowledge_mcp_url)

agent = create_agent(
    name="my-agent",
    output_type=MySchema,
    instructions="... Use search() to look up relevant information ...",
    toolsets=[knowledge_server],
)
```

### 5. Add Collections to Agent Config

```yaml
# agents/my-agent/config.yaml
collections:
  - my-collection
```

## Knowledge Packages (Per-Tenant Scoping)

Different clients/users may need different knowledge sets. Pattern:

```python
from contextvars import ContextVar

DEFAULT_COLLECTIONS = ("base-knowledge",)
_ACTIVE_COLLECTIONS: ContextVar[tuple[str, ...]] = ContextVar(
    "active_collections", default=DEFAULT_COLLECTIONS
)

async def _scope_search(ctx, call_tool, name, tool_args):
    """Force searches into the active tenant's collections."""
    if name == "search":
        tool_args = dict(tool_args)
        tool_args["collections"] = list(_ACTIVE_COLLECTIONS.get())
    return await call_tool(name, tool_args)

knowledge_server = MCPServerStreamableHTTP(
    knowledge_mcp_url,
    process_tool_call=_scope_search,
)

def before_run(input_data: dict) -> dict:
    context = input_data.get("client_context", {})
    packages = context.get("knowledge_packages")
    if packages:
        _ACTIVE_COLLECTIONS.set(tuple(packages))
    return input_data
```

Now each request scopes searches to the right collections based on who's calling.

## Knowledge Package Architecture

```
knowledge/
  books/
    base/               # Always active (core rules, general reference)
    industry-standard/  # Activated per client type
    specialty-a/        # Activated for clients who need specialty A
    specialty-b/        # Activated for clients who need specialty B
```

The host product manages which packages are active per tenant. The agent only searches what's activated.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Hardcoding domain knowledge in Python | Put it in PDFs/books. Agent searches at runtime. |
| One giant collection for everything | Split into focused collections. Scope per tenant. |
| Forgetting `--profile full` | Knowledge MCP needs R2R. Use `docker compose --profile full up -d` |
| Not testing knowledge quality | Search for known answers. If retrieval is bad, improve chunking or add better source docs. |
| Mixed-context documents | If a document covers multiple contexts (e.g. multiple standards), the agent may pick the wrong one. Use per-context documents or add clear prompt instructions. |
