---
project: local-code-indexer
tier: prototype
status: doing
current_round: 1
verify_cmd: ".venv/bin/python -m pytest -q && .venv/bin/ruff check ."
push_allowed: true
danger: "useability"
branch_lineage:
  []
---

# local-code-indexer — fleet spec

## Intent

<running scope conversation>

## Stakes

prototype

## Acceptance bar

- verify: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` green
- A global `--json` flag is accepted (works for every subcommand via a shared argparse parent parser so `search foo --json` works) and, when set, produces the EXACT current JSON output: print(json.dumps(payload, indent=2, sort_keys=True)).
- Without --json, the read-side query commands print compact human-readable text: `search` (repo/path:line-range, score+reason, symbols, snippet per hit), `symbols`, `list-files`, `list-repos`, `status`, and `read-file` (plain file content with optional line numbers).
- Empty results render a friendly line (e.g. 'No results.') instead of '[]'.
- Mutation/setup commands (init, index, watch, reindex-all, remove, mcp-config) keep their CURRENT JSON-via-_print_json default output unchanged and MUST still accept/honor --json without regressing machine output (--json is effectively a no-op for them).
- New tests in tests/test_cli.py assert: (a) human output contains expected substrings for search + status, (b) the empty-result friendly line, (c) `--json` still yields json.loads-parseable output matching prior shape.
- All pre-existing test_cli.py tests that json.loads(stdout) (21 sites) are updated to pass `--json`, and the FULL suite stays green; ruff stays clean.
- README CLI section notes the default is human-readable and `--json` gives machine output.

## Decided



## Deferred



## Rounds

### Round 1 — Human-readable CLI output with a --json escape hatch
why: Context hint is 'useability' and spec.danger is 'useability'. Recent work completed the read-side retrieval surface (search/symbols/list-files/read-file/status/list-repos with filters), but cli.py only ever prints raw indented JSON via _print_json (line 23). For a human running `local-code-indexer search 'auth'` in a terminal, a JSON blob is poor UX. No ROADMAP/plans/TODO exist to point elsewhere, and the audit-2026-06-19 doc only covers embedding/backend integrity, so README + git history are the spec. Making read-side commands human-readable by default while keeping --json for scripting/MCP-adjacent use is the highest-value, well-scoped next slice and is one coherent story: CLI rendering + tests.
acceptance:
- A global `--json` flag is accepted (works for every subcommand via a shared argparse parent parser so `search foo --json` works) and, when set, produces the EXACT current JSON output: print(json.dumps(payload, indent=2, sort_keys=True)).
- Without --json, the read-side query commands print compact human-readable text: `search` (repo/path:line-range, score+reason, symbols, snippet per hit), `symbols`, `list-files`, `list-repos`, `status`, and `read-file` (plain file content with optional line numbers).
- Empty results render a friendly line (e.g. 'No results.') instead of '[]'.
- Mutation/setup commands (init, index, watch, reindex-all, remove, mcp-config) keep their CURRENT JSON-via-_print_json default output unchanged and MUST still accept/honor --json without regressing machine output (--json is effectively a no-op for them).
- New tests in tests/test_cli.py assert: (a) human output contains expected substrings for search + status, (b) the empty-result friendly line, (c) `--json` still yields json.loads-parseable output matching prior shape.
- All pre-existing test_cli.py tests that json.loads(stdout) (21 sites) are updated to pass `--json`, and the FULL suite stays green; ruff stays clean.
- README CLI section notes the default is human-readable and `--json` gives machine output.
key files: src/local_code_indexer/cli.py, tests/test_cli.py, src/local_code_indexer/service.py (return shapes: search/symbols/list_files/list_repos/status/read_file — read-only reference), README.md
