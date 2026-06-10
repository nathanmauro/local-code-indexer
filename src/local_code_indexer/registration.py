"""MCP registration snippets for local clients."""

from __future__ import annotations

from pathlib import Path


def claude_mcp_config(db_path: str | Path | None = None) -> dict:
    env = {}
    if db_path:
        env["LOCAL_CODE_INDEXER_DB_PATH"] = str(db_path)
    return {
        "mcpServers": {
            "local-code-indexer": {
                "command": "local-code-indexer",
                "args": ["mcp"],
                **({"env": env} if env else {}),
            }
        }
    }


def codex_mcp_config(db_path: str | Path | None = None) -> dict:
    server = {
        "command": "local-code-indexer",
        "args": ["mcp"],
    }
    if db_path:
        server["env"] = {"LOCAL_CODE_INDEXER_DB_PATH": str(db_path)}
    return {"mcp_servers": {"local-code-indexer": server}}
