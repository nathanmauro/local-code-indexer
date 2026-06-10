import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.asyncio
async def test_mcp_lists_tools_and_returns_status(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["LOCAL_CODE_INDEXER_DB_PATH"] = str(tmp_path / "mcp.db")
    env["LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS"] = "1"

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
                "code_index_read_file",
                "code_index_symbols",
                "code_index_status",
            }.issubset(names)

            result = await session.call_tool("code_index_status", {})
            payload = json.loads(result.content[0].text)
            assert payload["repos"] == 0
            assert payload["db_path"].endswith("mcp.db")
