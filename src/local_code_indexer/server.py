"""MCP server entrypoint."""

from __future__ import annotations

from .tools import mcp


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
