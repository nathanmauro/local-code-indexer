"""Command-line interface for local-code-indexer."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import db_path_from_env
from .registration import claude_mcp_config, codex_mcp_config
from .service import IndexService


def _service() -> IndexService:
    service = IndexService(db_path_from_env())
    service.init()
    return service


def _print_json(payload) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-code-indexer")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the local SQLite index database.")

    index = sub.add_parser("index", help="Index a repository now.")
    index.add_argument("repo_path")
    index.add_argument("--name", default="")

    watch = sub.add_parser("watch", help="Poll and reindex a repository.")
    watch.add_argument("repo_path")
    watch.add_argument("--name", default="")
    watch.add_argument("--interval", type=float, default=5.0)

    search = sub.add_parser("search", help="Search indexed code.")
    search.add_argument("query")
    search.add_argument("--repo", default="")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--mode", choices=("hybrid", "lexical", "vector"), default="hybrid")

    status = sub.add_parser("status", help="Show index status.")
    status.add_argument("--repo", default="")

    sub.add_parser("list-repos", help="List indexed repositories.")
    sub.add_parser("reindex-all", help="Reindex every registered repository.")

    remove = sub.add_parser("remove", help="Remove an indexed repo and all its data.")
    remove.add_argument("name")

    mcp_config = sub.add_parser("mcp-config", help="Print a Claude or Codex MCP config snippet.")
    mcp_config.add_argument("--client", choices=("claude", "codex"), required=True)
    mcp_config.add_argument("--db-path", default="")

    sub.add_parser("mcp", help="Run the stdio MCP server.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "mcp":
        from .server import main as server_main

        server_main()
        return

    if args.command in {"index", "watch"} and not Path(args.repo_path).is_dir():
        parser.error(f"repo path is not a directory: {args.repo_path}")
    if args.command == "watch" and args.interval <= 0:
        parser.error("--interval must be positive")

    service = _service()
    try:
        if args.command == "init":
            _print_json(service.status())
        elif args.command == "index":
            _print_json(service.index_repo(Path(args.repo_path), name=args.name or None))
        elif args.command == "watch":
            while True:
                try:
                    _print_json(service.index_repo(Path(args.repo_path), name=args.name or None))
                except Exception as error:  # keep polling through transient failures
                    print(f"watch: index pass failed: {error}", file=sys.stderr)
                time.sleep(args.interval)
        elif args.command == "search":
            _print_json(
                service.search(
                    args.query,
                    repo=args.repo or None,
                    limit=args.limit,
                    mode=args.mode,
                )
            )
        elif args.command == "status":
            _print_json(service.status(repo=args.repo or None))
        elif args.command == "list-repos":
            _print_json(service.list_repos())
        elif args.command == "reindex-all":
            _print_json(service.reindex_all())
        elif args.command == "remove":
            _print_json(service.remove_repo(args.name))
        elif args.command == "mcp-config":
            db_path = args.db_path or str(db_path_from_env())
            if args.client == "claude":
                _print_json(claude_mcp_config(db_path))
            else:
                _print_json(codex_mcp_config(db_path))
        else:  # pragma: no cover
            parser.error(f"unknown command {args.command}")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
