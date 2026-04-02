"""
CLI tool for ingesting documents into R2R via Docling preprocessing.

Usage::

    # Ingest a single collection
    python -m shared.ingest --collection example-docs --dir knowledge/books/example/

    # Ingest all collections defined in knowledge/collections.yaml
    python -m shared.ingest --all

    # Custom service URLs
    python -m shared.ingest --all --r2r-url http://localhost:7272 --docling-url http://localhost:5001
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx
import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default service URLs (can be overridden via CLI flags or env)
_DEFAULT_R2R_URL = "http://localhost:7272"
_DEFAULT_DOCLING_URL = "http://localhost:5001"


# ---------------------------------------------------------------------------
# Docling helpers
# ---------------------------------------------------------------------------

async def _docling_convert(
    file_path: Path,
    docling_url: str,
    client: httpx.AsyncClient,
) -> dict[str, Any]:
    """Send a file to Docling for OCR / PDF conversion and return the result.

    Docling-serve exposes ``POST /convert`` which accepts a file upload and
    returns structured Markdown / JSON.
    """
    logger.info("Sending '%s' to Docling for conversion...", file_path.name)

    with open(file_path, "rb") as fh:
        files = {"files": (file_path.name, fh, "application/octet-stream")}
        resp = await client.post(
            f"{docling_url}/v1alpha/convert/file",
            files=files,
            timeout=300.0,  # PDF conversion can be slow
        )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Docling conversion failed for '{file_path.name}': "
            f"{resp.status_code} {resp.text[:500]}"
        )

    return resp.json()


# ---------------------------------------------------------------------------
# R2R helpers
# ---------------------------------------------------------------------------

async def _ensure_collection(
    collection_name: str,
    r2r_base_url: str,
    client: httpx.AsyncClient,
) -> str:
    """Create a collection in R2R if it does not already exist.

    Returns the collection ID.
    """
    # Try to find existing collection
    resp = await client.get(
        f"{r2r_base_url}/v3/collections",
        params={"limit": 100},
        timeout=30.0,
    )

    if resp.status_code == 200:
        data = resp.json()
        results = data.get("results", [])
        for col in results:
            if col.get("name") == collection_name:
                logger.info("Collection '%s' already exists (id=%s)", collection_name, col["id"])
                return col["id"]

    # Create new collection
    resp = await client.post(
        f"{r2r_base_url}/v3/collections",
        json={"name": collection_name},
        timeout=30.0,
    )

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to create collection '{collection_name}': "
            f"{resp.status_code} {resp.text[:500]}"
        )

    result = resp.json()
    collection_id = result.get("results", {}).get("id", result.get("id", "unknown"))
    logger.info("Created collection '%s' (id=%s)", collection_name, collection_id)
    return collection_id


async def _ingest_to_r2r(
    file_path: Path,
    markdown_content: str,
    collection_id: str,
    r2r_base_url: str,
    client: httpx.AsyncClient,
) -> None:
    """Ingest a pre-processed document into R2R.

    Uses the R2R v3 documents API to create a document from raw text,
    then assigns it to the given collection.
    """
    # Create document via raw text ingestion
    resp = await client.post(
        f"{r2r_base_url}/v3/documents",
        json={
            "raw_text": markdown_content,
            "metadata": {
                "source_file": file_path.name,
                "source_path": str(file_path),
            },
        },
        timeout=120.0,
    )

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"R2R ingestion failed for '{file_path.name}': "
            f"{resp.status_code} {resp.text[:500]}"
        )

    result = resp.json()
    doc_id = result.get("results", {}).get("document_id", "unknown")
    logger.info("Ingested '%s' into R2R (doc_id=%s)", file_path.name, doc_id)

    # Assign to collection
    resp = await client.post(
        f"{r2r_base_url}/v3/collections/{collection_id}/documents/{doc_id}",
        timeout=30.0,
    )

    if resp.status_code not in (200, 204):
        logger.warning(
            "Could not assign doc %s to collection %s: %s %s",
            doc_id, collection_id, resp.status_code, resp.text[:200],
        )
    else:
        logger.info("Assigned doc '%s' to collection '%s'", file_path.name, collection_id)


# ---------------------------------------------------------------------------
# High-level orchestration
# ---------------------------------------------------------------------------

_SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".html", ".txt", ".md"}


async def ingest_file(
    file_path: Path,
    collection_id: str,
    docling_url: str,
    r2r_base_url: str,
) -> None:
    """Process one file: Docling OCR -> R2R ingestion."""
    async with httpx.AsyncClient() as client:
        # Step 1: Convert via Docling
        docling_result = await _docling_convert(file_path, docling_url, client)

        # Extract Markdown content from Docling response
        # Docling-serve returns a document list; we take the first one.
        documents = docling_result.get("document", [docling_result])
        if isinstance(documents, dict):
            documents = [documents]

        markdown_parts: list[str] = []
        for doc in documents if isinstance(documents, list) else [documents]:
            md = doc.get("md_content") or doc.get("markdown") or doc.get("text", "")
            if md:
                markdown_parts.append(md)

        if not markdown_parts:
            # Fall back to the whole JSON as text
            import json
            markdown_parts.append(json.dumps(docling_result, indent=2))

        markdown_content = "\n\n---\n\n".join(markdown_parts)

        # Step 2: Ingest into R2R
        await _ingest_to_r2r(
            file_path, markdown_content, collection_id, r2r_base_url, client
        )


async def ingest_collection(
    name: str,
    books_dir: str,
    r2r_base_url: str = _DEFAULT_R2R_URL,
    docling_url: str = _DEFAULT_DOCLING_URL,
) -> None:
    """Create collection in R2R if needed, then ingest all supported files."""
    books_path = _PROJECT_ROOT / books_dir
    if not books_path.exists():
        logger.error("Books directory does not exist: %s", books_path)
        return

    files = [
        f for f in sorted(books_path.iterdir())
        if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
    ]

    if not files:
        logger.warning("No supported files found in %s", books_path)
        return

    logger.info(
        "Ingesting %d file(s) into collection '%s' from %s",
        len(files), name, books_path,
    )

    async with httpx.AsyncClient() as client:
        collection_id = await _ensure_collection(name, r2r_base_url, client)

    for file_path in files:
        try:
            await ingest_file(file_path, collection_id, docling_url, r2r_base_url)
        except Exception as exc:
            logger.error("Failed to ingest '%s': %s", file_path.name, exc)


async def ingest_all(
    config_path: str = "knowledge/collections.yaml",
    r2r_base_url: str = _DEFAULT_R2R_URL,
    docling_url: str = _DEFAULT_DOCLING_URL,
) -> None:
    """Ingest all collections defined in the config file."""
    full_path = _PROJECT_ROOT / config_path

    if not full_path.exists():
        logger.error("Collections config not found: %s", full_path)
        return

    with open(full_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    raw = data.get("collections", {})
    if not raw:
        logger.warning("No collections defined in %s", full_path)
        return

    # Normalise to list of (name, books_dir) tuples.
    # Supports dict-keyed format: {name: {books_dir: ...}}
    # and list-of-dicts format: [{name: ..., books_dir: ...}]
    entries: list[tuple[str, str]] = []

    if isinstance(raw, dict):
        for col_name, col_data in raw.items():
            if isinstance(col_data, dict) and col_data.get("books_dir"):
                entries.append((col_name, col_data["books_dir"]))
    elif isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict):
                name = entry.get("name")
                books_dir = entry.get("books_dir")
                if name and books_dir:
                    entries.append((name, books_dir))

    if not entries:
        logger.warning("No valid collection entries found in %s", full_path)
        return

    logger.info("Starting ingestion of %d collection(s)", len(entries))

    for name, books_dir in entries:
        await ingest_collection(name, books_dir, r2r_base_url, docling_url)

    logger.info("Ingestion complete")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for ``python -m shared.ingest``."""
    parser = argparse.ArgumentParser(
        description="Ingest documents into R2R via Docling preprocessing",
    )
    parser.add_argument(
        "--collection",
        help="Name of a single collection to ingest",
    )
    parser.add_argument(
        "--dir",
        dest="books_dir",
        help="Directory containing documents (used with --collection)",
    )
    parser.add_argument(
        "--all",
        dest="ingest_all",
        action="store_true",
        help="Ingest all collections from knowledge/collections.yaml",
    )
    parser.add_argument(
        "--r2r-url",
        default=_DEFAULT_R2R_URL,
        help=f"R2R base URL (default: {_DEFAULT_R2R_URL})",
    )
    parser.add_argument(
        "--docling-url",
        default=_DEFAULT_DOCLING_URL,
        help=f"Docling service URL (default: {_DEFAULT_DOCLING_URL})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.ingest_all:
        asyncio.run(ingest_all(
            r2r_base_url=args.r2r_url,
            docling_url=args.docling_url,
        ))
    elif args.collection and args.books_dir:
        asyncio.run(ingest_collection(
            name=args.collection,
            books_dir=args.books_dir,
            r2r_base_url=args.r2r_url,
            docling_url=args.docling_url,
        ))
    else:
        parser.error("Specify either --all or both --collection and --dir")


if __name__ == "__main__":
    main()
