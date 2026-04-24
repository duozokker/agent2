# Knowledge Management

## Overview

Knowledge is foundational to the expert cloning pattern in Agent2. Domain experts do not just think -- they reference books, regulations, internal procedures, and institutional memory. The knowledge layer gives agents the same access to reference materials that a human expert would have.

The framework uses:

- R2R for ingestion and search
- Docling for OCR and document conversion
- Knowledge MCP for tool access from agents

## Collections

Collections are declared in [`knowledge/collections.yaml`](../knowledge/collections.yaml).

Each collection defines:

- a description
- a source directory
- the agents that are allowed to use it

## Ingestion flow

```text
PDFs or source documents
  -> Docling
  -> markdown / extracted content
  -> R2R chunking and embedding
  -> searchable collection
```

## Agent wiring

An agent that uses Knowledge MCP should:

1. declare its collections in `config.yaml`
2. attach the MCP toolset
3. optionally apply tool policies for extra scoping

## Default vs full stack

Knowledge infrastructure requires the full Docker profile. For domain expert agents, this is the recommended setup.

Use:

```bash
docker compose --profile full up -d
```

when you need Knowledge MCP, R2R, Docling, or the RAG-oriented demos. The default profile is available for simpler agents that do not need knowledge search.
