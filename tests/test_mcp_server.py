import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from local_code_indexer.service import IndexService


@pytest.mark.asyncio
async def test_mcp_lists_tools_and_returns_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env = os.environ.copy()
    db_path = tmp_path / "mcp.db"
    env["LOCAL_CODE_INDEXER_DB_PATH"] = str(db_path)
    env["LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS"] = "1"
    monkeypatch.setenv("LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS", "1")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def run():\n    return 'ok'\n")
    service = IndexService(db_path)
    service.init()
    service.index_repo(repo, name="demo")

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "local_code_indexer", "mcp"],
        env=env,
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert {
                "code_index_search",
                "code_index_list_files",
                "code_index_list_repos",
                "code_index_read_file",
                "code_index_symbols",
                "code_index_status",
            }.issubset(names)

            result = await session.call_tool("code_index_status", {})
            payload = json.loads(result.content[0].text)
            assert payload["repos"] == 1
            assert payload["db_path"].endswith("mcp.db")

            repos_result = await session.call_tool("code_index_list_repos", {})
            repos = json.loads(repos_result.content[0].text)
            assert repos == [
                {
                    "chunks": 1,
                    "embedded_chunks": 0,
                    "files": 1,
                    "name": "demo",
                    "path": str(repo.resolve()),
                    "updated_at": repos[0]["updated_at"],
                }
            ]
            assert repos[0]["updated_at"]
