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


def _print_json_or_text(payload, json_output: bool, text_printer) -> None:
    if json_output:
        _print_json(payload)
        return
    text_printer(payload)


def _print_search(results: list[dict]) -> None:
    if not results:
        print("No results.")
        return
    blocks = []
    for result in results:
        symbols = ", ".join(result.get("symbols") or []) or "(none)"
        blocks.append(
            "\n".join(
                [
                    f"{result['repo']} {result['path']}:{result['start_line']}-{result['end_line']}",
                    f"score: {result['score']}  score_reason: {result['score_reason']}",
                    f"symbols: {symbols}",
                    result.get("snippet", ""),
                ]
            )
        )
    print("\n\n".join(blocks))


def _print_symbols(rows: list[dict]) -> None:
    if not rows:
        print("No results.")
        return
    for row in rows:
        kind = row.get("kind") or "symbol"
        print(f"{row['repo']} {row['path']}:{row['line']} {kind} {row['symbol']}")


def _print_list_files(rows: list[dict]) -> None:
    if not rows:
        print("No results.")
        return
    for row in rows:
        print(
            f"{row['repo']} {row['path']} "
            f"language={row['language']} size={row['size']} indexed_at={row['indexed_at']}"
        )


def _print_list_repos(rows: list[dict]) -> None:
    if not rows:
        print("No results.")
        return
    for row in rows:
        print(
            f"{row['name']} files={row['files']} chunks={row['chunks']} "
            f"embedded_chunks={row['embedded_chunks']} path={row['path']} "
            f"updated_at={row['updated_at']}"
        )


def _print_status(status: dict) -> None:
    for key in (
        "db_path",
        "repos",
        "files",
        "chunks",
        "embedded_chunks",
        "embeddings",
        "degraded",
        "vector_query_backend",
    ):
        print(f"{key}: {status[key]}")
    print("per_repo:")
    if not status["per_repo"]:
        print("  No repos.")
        return
    for repo in status["per_repo"]:
        print(
            f"  {repo['name']} files={repo['files']} chunks={repo['chunks']} "
            f"embedded_chunks={repo['embedded_chunks']} path={repo['path']}"
        )


def _print_read_file(result: dict) -> None:
    print(result["content"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-code-indexer")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        default=False,
        help="Print machine-readable JSON.",
    )
    json_parent = argparse.ArgumentParser(add_help=False)
    json_parent.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        default=argparse.SUPPRESS,
        help="Print machine-readable JSON.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "init",
        parents=[json_parent],
        help="Initialize the local SQLite index database.",
    )

    index = sub.add_parser("index", parents=[json_parent], help="Index a repository now.")
    index.add_argument("repo_path")
    index.add_argument("--name", default="")

    watch = sub.add_parser("watch", parents=[json_parent], help="Poll and reindex a repository.")
    watch.add_argument("repo_path")
    watch.add_argument("--name", default="")
    watch.add_argument("--interval", type=float, default=5.0)

    search = sub.add_parser("search", parents=[json_parent], help="Search indexed code.")
    search.add_argument("query")
    search.add_argument("--repo", default="")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--mode", choices=("hybrid", "lexical", "vector"), default="hybrid")
    search.add_argument("--path", default="")
    search.add_argument("--lang", default="")
    search.add_argument("--kind", default="")

    symbols = sub.add_parser("symbols", parents=[json_parent], help="Search indexed symbols.")
    symbols.add_argument("query", nargs="?", default="")
    symbols.add_argument("--repo", default="")
    symbols.add_argument("--path", default="")
    symbols.add_argument("--limit", type=int, default=50)
    symbols.add_argument("--lang", default="")
    symbols.add_argument("--kind", default="")

    list_files = sub.add_parser("list-files", parents=[json_parent], help="List indexed files.")
    list_files.add_argument("--repo", default="")
    list_files.add_argument("--glob", default="")
    list_files.add_argument("--limit", type=int, default=50)
    list_files.add_argument("--lang", default="")

    read_file = sub.add_parser(
        "read-file",
        parents=[json_parent],
        help="Read an indexed repo-relative file range.",
    )
    read_file.add_argument("repo")
    read_file.add_argument("path")
    read_file.add_argument("--start-line", type=int, default=None)
    read_file.add_argument("--end-line", type=int, default=None)

    status = sub.add_parser("status", parents=[json_parent], help="Show index status.")
    status.add_argument("--repo", default="")

    sub.add_parser("list-repos", parents=[json_parent], help="List indexed repositories.")
    sub.add_parser(
        "reindex-all",
        parents=[json_parent],
        help="Reindex every registered repository.",
    )

    remove = sub.add_parser(
        "remove",
        parents=[json_parent],
        help="Remove an indexed repo and all its data.",
    )
    remove.add_argument("name")

    mcp_config = sub.add_parser(
        "mcp-config",
        parents=[json_parent],
        help="Print a Claude or Codex MCP config snippet.",
    )
    mcp_config.add_argument("--client", choices=("claude", "codex"), required=True)
    mcp_config.add_argument("--db-path", default="")

    sub.add_parser("mcp", parents=[json_parent], help="Run the stdio MCP server.")
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
            results = service.search(
                args.query,
                repo=args.repo or None,
                limit=args.limit,
                mode=args.mode,
                path=args.path or None,
                lang=args.lang or None,
                kind=args.kind or None,
            )
            _print_json_or_text(results, args.json_output, _print_search)
        elif args.command == "symbols":
            results = service.symbols(
                repo=args.repo or None,
                query=args.query or None,
                path=args.path or None,
                limit=args.limit,
                lang=args.lang or None,
                kind=args.kind or None,
            )
            _print_json_or_text(results, args.json_output, _print_symbols)
        elif args.command == "list-files":
            results = service.list_files(
                repo=args.repo or None,
                glob=args.glob or None,
                limit=args.limit,
                lang=args.lang or None,
            )
            _print_json_or_text(results, args.json_output, _print_list_files)
        elif args.command == "read-file":
            result = service.read_file(
                repo=args.repo,
                path=args.path,
                start_line=args.start_line,
                end_line=args.end_line,
            )
            _print_json_or_text(result, args.json_output, _print_read_file)
        elif args.command == "status":
            result = service.status(repo=args.repo or None)
            _print_json_or_text(result, args.json_output, _print_status)
        elif args.command == "list-repos":
            results = service.list_repos()
            _print_json_or_text(results, args.json_output, _print_list_repos)
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
    except (ValueError, FileNotFoundError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
