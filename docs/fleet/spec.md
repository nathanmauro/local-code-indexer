---
project: local-code-indexer
tier: prototype
status: doing
current_round: 2
verify_cmd: ".venv/bin/python -m pytest -q && .venv/bin/ruff check ."
push_allowed: true
danger: "useability"
branch_lineage:
  - round: 1
    branch: "fleet/round-1-human-readable-cli-output"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/1"
    commit: "e81ed25"
    status: "review"
    note: ""
---

# local-code-indexer — fleet spec

## Intent

<running scope conversation>

## Stakes

prototype

## Acceptance bar

- verify: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` green
- init, index, watch, reindex-all, and remove print compact human-readable text by DEFAULT (no --json). `mcp-config` is INTENTIONALLY LEFT printing JSON and must NOT be converted.
- `index`/`reindex-all` human output surfaces the useability-relevant fields from the result dict: repo/path, indexed_files, unchanged_files, skipped_files, deleted_files, embedded_chunks, embedding_failures, and a clear 'degraded' indicator when degraded is true.
- `reindex-all` renders one line per repo (including path-missing skipped repos: 'skipped: path missing') plus a reindexed count.
- `remove` renders e.g. 'Removed <repo> (<n> files).'; `init` renders a brief status-style summary (may reuse the existing _print_status renderer).
- `watch` prints a human one-line summary per pass by default and the JSON blob per pass when --json is set; transient failure stderr logging is unchanged.
- Passing `--json` to ANY of init/index/watch/reindex-all/remove reproduces the EXACT prior output: print(json.dumps(payload, indent=2, sort_keys=True)) via _print_json — same shape the read-side --json uses. mcp-config output is unchanged.
- New/updated tests in tests/test_cli.py assert human substrings for index (e.g. an indexed_files count / a degraded marker), reindex-all, and remove, AND assert that --json still yields json.loads-parseable output of the prior shape. All pre-existing tests stay green; ruff stays clean.
- README CLI section updated: state that init/index/watch/reindex-all/remove are now human-readable by default with --json for machine output, while mcp-config still emits JSON (remove the blanket 'Mutation and setup commands keep their existing JSON output by default' wording but keep mcp-config's JSON accurately described).

## Decided

## Deferred

## Rounds

### Round 1 — fleet/round-1-human-readable-cli-output
base: next
branch: fleet/round-1-human-readable-cli-output
pr: https://github.com/nathanmauro/local-code-indexer/pull/1
commit: e81ed25
status: review
note:

### Round 2 — Human-readable output for mutation/setup commands with --json escape hatch (mcp-config stays JSON)
why: Context hint and spec.danger are both 'useability'. Round 1 (e81ed25, PR #1) made the read-side commands human-readable but deliberately left the write/setup commands (init, index, watch, reindex-all, remove) printing raw JSON via _print_json in cli.py main(). `index` is the FIRST command a human runs and its degraded/embedding_failures/skipped signals are exactly the useability payload — yet it dumps a JSON blob. Finishing the human-readable story across these commands is the direct, well-scoped continuation per docs/fleet/spec.md (empty Decided/Deferred, so not blocked). `mcp-config` is intentionally excluded because it emits a client-config blob meant to be pasted verbatim into a config file, where JSON is the correct format. Existing tests already pass --json on these commands' assertion calls, so the work is low-risk.
acceptance:
- init, index, watch, reindex-all, and remove print compact human-readable text by DEFAULT (no --json). `mcp-config` is INTENTIONALLY LEFT printing JSON and must NOT be converted.
- `index`/`reindex-all` human output surfaces the useability-relevant fields from the result dict: repo/path, indexed_files, unchanged_files, skipped_files, deleted_files, embedded_chunks, embedding_failures, and a clear 'degraded' indicator when degraded is true.
- `reindex-all` renders one line per repo (including path-missing skipped repos: 'skipped: path missing') plus a reindexed count.
- `remove` renders e.g. 'Removed <repo> (<n> files).'; `init` renders a brief status-style summary (may reuse the existing _print_status renderer).
- `watch` prints a human one-line summary per pass by default and the JSON blob per pass when --json is set; transient failure stderr logging is unchanged.
- Passing `--json` to ANY of init/index/watch/reindex-all/remove reproduces the EXACT prior output: print(json.dumps(payload, indent=2, sort_keys=True)) via _print_json — same shape the read-side --json uses. mcp-config output is unchanged.
- New/updated tests in tests/test_cli.py assert human substrings for index (e.g. an indexed_files count / a degraded marker), reindex-all, and remove, AND assert that --json still yields json.loads-parseable output of the prior shape. All pre-existing tests stay green; ruff stays clean.
- README CLI section updated: state that init/index/watch/reindex-all/remove are now human-readable by default with --json for machine output, while mcp-config still emits JSON (remove the blanket 'Mutation and setup commands keep their existing JSON output by default' wording but keep mcp-config's JSON accurately described).
key files: src/local_code_indexer/cli.py, tests/test_cli.py, src/local_code_indexer/service.py (return shapes index_repo, reindex_all, remove_repo, status — read-only reference), README.md
