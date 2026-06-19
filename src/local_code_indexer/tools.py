"""FastMCP tools for local code indexing."""

from __future__ import annotations

import json
from pathlib import Path

import anyio.to_thread
from mcp.server.fastmcp import FastMCP

from .config import db_path_from_env, embeddings_disabled
from .embeddings import LocalEmbedder
from .service import IndexService

mcp = FastMCP("local-code-indexer")


def _service() -> IndexService:
    embedder = None if embeddings_disabled() else LocalEmbedder()
    service = IndexService(db_path_from_env(), embedder=embedder)
    service.init()
    return service


def _json(payload) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


async def _run(work) -> str:
    # FastMCP executes sync tools directly on the event loop; SQLite work and the
    # blocking Ollama embed call must run in a worker thread so the stdio server
    # stays responsive.
    return await anyio.to_thread.run_sync(work)


@mcp.tool()
async def code_index_search(
    query: str,
    repo: str = "",
    mode: str = "hybrid",
    limit: int = 10,
) -> str:
    """Search indexed code chunks by lexical, vector, path, and symbol signals."""
    return await _run(
        lambda: _json(_service().search(query=query, repo=repo or None, mode=mode, limit=limit))
    )


@mcp.tool()
async def code_index_list_files(repo: str = "", glob: str = "", limit: int = 50) -> str:
    """List indexed files, optionally filtered by repo and glob."""
    return await _run(
        lambda: _json(_service().list_files(repo=repo or None, glob=glob or None, limit=limit))
    )


@mcp.tool()
async def code_index_list_repos() -> str:
    """List indexed repositories with file, chunk, and embedding counts."""
    return await _run(lambda: _json(_service().list_repos()))


@mcp.tool()
async def code_index_read_file(
    repo: str,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read an indexed repo-relative file range."""
    return await _run(
        lambda: _json(
            _service().read_file(repo=repo, path=path, start_line=start_line, end_line=end_line)
        )
    )


@mcp.tool()
async def code_index_symbols(
    repo: str = "",
    query: str = "",
    path: str = "",
    limit: int = 50,
) -> str:
    """Search indexed symbols by repo, symbol text, and path."""
    return await _run(
        lambda: _json(
            _service().symbols(
                repo=repo or None,
                query=query or None,
                path=path or None,
                limit=limit,
            )
        )
    )


@mcp.tool()
async def code_index_status(repo: str = "") -> str:
    """Return database, repo, file, chunk, vector, and embedding status."""
    return await _run(lambda: _json(_service().status(repo=repo or None)))


def index_path(repo_path: str, name: str = "") -> str:
    return _json(_service().index_repo(Path(repo_path), name=name or None))
