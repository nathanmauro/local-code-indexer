import json
from pathlib import Path

from local_code_indexer.registration import claude_mcp_config, codex_mcp_config


def test_registration_snippets_are_local_indexer_only(tmp_path: Path) -> None:
    db_path = tmp_path / "index.db"
    claude = claude_mcp_config(db_path)
    codex = codex_mcp_config(db_path)

    merged = json.dumps({"claude": claude, "codex": codex}).lower()

    assert "local-code-indexer" in merged
    assert "augment" not in merged
    assert claude["mcpServers"]["local-code-indexer"]["args"] == ["mcp"]
    assert codex["mcp_servers"]["local-code-indexer"]["args"] == ["mcp"]
    assert codex["mcp_servers"]["local-code-indexer"]["env"]["LOCAL_CODE_INDEXER_DB_PATH"] == str(
        db_path
    )
