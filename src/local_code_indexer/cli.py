"""Command-line interface for local-code-indexer."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import __version__
from .config import db_path_from_env
from .registration import claude_mcp_config, codex_mcp_config
from .service import IndexService, _normalize_kind_filter, _normalize_lang_filter

EMPTY_INDEX_HINT = "No repos indexed. Run `local-code-indexer index <repo_path>` to index one."


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


def _format_known_values(values: list[str]) -> str:
    return ", ".join(values) or "(none)"


def _empty_filter_hint_lines(
    service: IndexService,
    *,
    lang: str | None = None,
    kind: str | None = None,
) -> list[str]:
    hints = []
    lang_filter = _normalize_lang_filter(lang)
    if lang_filter is not None:
        languages = service.list_languages()
        if lang_filter not in languages:
            hints.append(
                f"note: --lang '{lang_filter}' matches nothing. "
                f"indexed languages: {_format_known_values(languages)}"
            )
    kind_filter = _normalize_kind_filter(kind)
    if kind_filter is not None:
        kinds = service.list_kinds()
        if kind_filter not in kinds:
            hints.append(
                f"note: --kind '{kind_filter}' matches nothing. "
                f"indexed kinds: {_format_known_values(kinds)}"
            )
    return hints


def _vector_skip_hint_line(reason: str | None) -> str | None:
    if reason == "embeddings-disabled":
        return (
            "note: vector search unavailable: embeddings are disabled "
            "(LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS=1). try --mode lexical."
        )
    if reason == "query-embedding-failed":
        return (
            "note: vector search unavailable: query embedding failed; "
            "check the local embedding service, or try --mode lexical."
        )
    if reason == "no-embedded-chunks":
        return (
            "note: vector search unavailable: no embedded chunks are stored in the searched scope. "
            "rerun `local-code-indexer index <repo_path>` with the embedding service up."
        )
    return None


def _print_read_results(
    payload: list[dict],
    service: IndexService,
    json_output: bool,
    text_printer,
    *,
    lang: str | None = None,
    kind: str | None = None,
    vector_skip_reason: str | None = None,
) -> None:
    if json_output:
        _print_json(payload)
        return
    if not payload:
        if not service.list_repos():
            print(EMPTY_INDEX_HINT)
            return
        text_printer(payload)
        for line in _empty_filter_hint_lines(service, lang=lang, kind=kind):
            print(line)
        vector_hint = _vector_skip_hint_line(vector_skip_reason)
        if vector_hint is not None:
            print(vector_hint)
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
        print(EMPTY_INDEX_HINT)
        return
    for row in rows:
        print(
            f"{row['name']} files={row['files']} chunks={row['chunks']} "
            f"embedded_chunks={row['embedded_chunks']} path={row['path']} "
            f"updated_at={row['updated_at']}"
        )


def _print_status(status: dict) -> None:
    for key in (
        "version",
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


def _index_result_fields(result: dict) -> str:
    return (
        f"path={result['path']} "
        f"indexed_files={result['indexed_files']} "
        f"unchanged_files={result['unchanged_files']} "
        f"skipped_files={result['skipped_files']} "
        f"deleted_files={result['deleted_files']} "
        f"indexed_chunks={result['indexed_chunks']} "
        f"embedded_chunks={result['embedded_chunks']} "
        f"embedding_failures={result['embedding_failures']} "
        f"degraded={result['degraded']}"
    )


def _degraded_marker(result: dict) -> str:
    return " DEGRADED" if result.get("degraded") else ""


def _print_index_result(result: dict) -> None:
    print(f"Indexed {result['repo']} {_index_result_fields(result)}{_degraded_marker(result)}")


def _print_reindex_all(result: dict) -> None:
    for repo in result["repos"]:
        if repo.get("skipped"):
            print(f"{repo['repo']} path={repo['path']} skipped=True error={repo['error']}")
            continue
        print(f"{repo['repo']} {_index_result_fields(repo)}{_degraded_marker(repo)}")
    print(f"reindexed: {result['reindexed']}")


def _print_remove(result: dict) -> None:
    print(f"Removed {result['repo']} ({result['deleted_files']} files).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-code-indexer")
    parser.add_argument("--version", action="version", version=__version__)
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
            _print_json_or_text(service.status(), args.json_output, _print_status)
        elif args.command == "index":
            result = service.index_repo(Path(args.repo_path), name=args.name or None)
            _print_json_or_text(result, args.json_output, _print_index_result)
        elif args.command == "watch":
            while True:
                try:
                    result = service.index_repo(Path(args.repo_path), name=args.name or None)
                    _print_json_or_text(result, args.json_output, _print_index_result)
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
            _print_read_results(
                results,
                service,
                args.json_output,
                _print_search,
                lang=args.lang or None,
                kind=args.kind or None,
                vector_skip_reason=(
                    service.last_vector_skip_reason if args.mode == "vector" else None
                ),
            )
        elif args.command == "symbols":
            results = service.symbols(
                repo=args.repo or None,
                query=args.query or None,
                path=args.path or None,
                limit=args.limit,
                lang=args.lang or None,
                kind=args.kind or None,
            )
            _print_read_results(
                results,
                service,
                args.json_output,
                _print_symbols,
                lang=args.lang or None,
                kind=args.kind or None,
            )
        elif args.command == "list-files":
            results = service.list_files(
                repo=args.repo or None,
                glob=args.glob or None,
                limit=args.limit,
                lang=args.lang or None,
            )
            _print_read_results(
                results,
                service,
                args.json_output,
                _print_list_files,
                lang=args.lang or None,
            )
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
            _print_json_or_text(service.reindex_all(), args.json_output, _print_reindex_all)
        elif args.command == "remove":
            _print_json_or_text(service.remove_repo(args.name), args.json_output, _print_remove)
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
