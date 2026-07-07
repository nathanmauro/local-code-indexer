---
project: local-code-indexer
tier: prototype
status: doing
current_round: 4
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
  - round: 2
    branch: "fleet/round-2-human-readable-mutation-output"
    base: "fleet/round-1-human-readable-cli-output"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/2"
    commit: "42a0b04"
    status: "done"
    note: ""
  - round: 3
    branch: "fleet/round-3-unknown-repo-errors"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/3"
    commit: "7a11cd3"
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
- service.status calls _require_known_repo when a repo argument is provided (repo truthy); `status --repo nope` exits 1 via the existing CLI except-block with 'error: unknown repo: nope. indexed repos: ...' on stderr; status with no repo is unchanged (note cli.py `init` also calls service.status() with no repo — leave it alone).
- service.remove_repo reuses the shared helper/message so `remove nope` also lists indexed repos; the existing test at tests/test_service.py:564 (pytest.raises match='unknown repo: repo', a regex search) stays green with the richer message.
- When search/symbols/list-files return empty results AND the index contains zero repos, human-readable output includes a getting-started hint (e.g. "No repos indexed. Run `local-code-indexer index <repo_path>` to index one."); `list-repos` on an empty index prints the same hint instead of the generic 'No results.'
- When at least one repo is indexed and a query simply has no matches, text output remains exactly 'No results.' (regression guard — test_cli.py:473-488 already asserts this with a demo repo indexed), and --json output for empty results remains [] (the hint is human-output-only; JSON payload shapes are unchanged).
- MCP surface: code_index_status with an unknown repo now surfaces the ValueError (tools.py:130 passes `repo or None`; consistent with round-3 precedent for search/symbols/list_files); no hint text is added to any MCP JSON output; tests/test_mcp_server.py stays green (its status call passes no repo).
- New tests in tests/test_cli.py cover: status --repo unknown exits 1 with 'unknown repo' + an indexed repo name on stderr; remove of an unknown repo lists indexed repos; search and list-repos on a fresh empty DB print the getting-started hint; a valid repo with no matches still prints 'No results.'; --json empty results are still [].
- README CLI section gets a one-line note about the empty-index hint and that status/remove now error with the indexed-repos list on an unknown repo.
- Verify green: .venv/bin/python -m pytest -q && .venv/bin/ruff check . (baseline is green: 94 tests + ruff clean)

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

### Round 2 — fleet/round-2-human-readable-mutation-output
base: fleet/round-1-human-readable-cli-output
branch: fleet/round-2-human-readable-mutation-output
pr: https://github.com/nathanmauro/local-code-indexer/pull/2
commit: 42a0b04
status: done
note:

### Round 3 — fleet/round-3-unknown-repo-errors
base: next
branch: fleet/round-3-unknown-repo-errors
pr: https://github.com/nathanmauro/local-code-indexer/pull/3
commit: 7a11cd3
status: review
note:

### Round 4 — Empty-index getting-started guidance + unknown-repo validation for status and remove
why: The fleet theme is useability (mirror danger='useability', context hint 'useability'). docs/fleet/spec.md Rounds show rounds 1-2 made output human-readable and round 3 added unknown-repo errors to search/symbols/list-files/read-file via _require_known_repo (service.py:907). Direct inspection shows the story is unfinished: service.status (service.py:1354) accepts any --repo and silently reports zeros, remove_repo (service.py:1339) still raises the bare 'unknown repo: <name>' without the indexed-repos list, and a first-run user who searches before indexing gets a bare 'No results.' indistinguishable from no matches. Completing the 'every empty/unknown state explains itself' story is the natural round-4 continuation; Decided/Deferred in the living spec are empty so nothing blocks it.
acceptance:
- service.status calls _require_known_repo when a repo argument is provided (repo truthy); `status --repo nope` exits 1 via the existing CLI except-block with 'error: unknown repo: nope. indexed repos: ...' on stderr; status with no repo is unchanged (note cli.py `init` also calls service.status() with no repo — leave it alone).
- service.remove_repo reuses the shared helper/message so `remove nope` also lists indexed repos; the existing test at tests/test_service.py:564 (pytest.raises match='unknown repo: repo', a regex search) stays green with the richer message.
- When search/symbols/list-files return empty results AND the index contains zero repos, human-readable output includes a getting-started hint (e.g. "No repos indexed. Run `local-code-indexer index <repo_path>` to index one."); `list-repos` on an empty index prints the same hint instead of the generic 'No results.'
- When at least one repo is indexed and a query simply has no matches, text output remains exactly 'No results.' (regression guard — test_cli.py:473-488 already asserts this with a demo repo indexed), and --json output for empty results remains [] (the hint is human-output-only; JSON payload shapes are unchanged).
- MCP surface: code_index_status with an unknown repo now surfaces the ValueError (tools.py:130 passes `repo or None`; consistent with round-3 precedent for search/symbols/list_files); no hint text is added to any MCP JSON output; tests/test_mcp_server.py stays green (its status call passes no repo).
- New tests in tests/test_cli.py cover: status --repo unknown exits 1 with 'unknown repo' + an indexed repo name on stderr; remove of an unknown repo lists indexed repos; search and list-repos on a fresh empty DB print the getting-started hint; a valid repo with no matches still prints 'No results.'; --json empty results are still [].
- README CLI section gets a one-line note about the empty-index hint and that status/remove now error with the indexed-repos list on an unknown repo.
- Verify green: .venv/bin/python -m pytest -q && .venv/bin/ruff check . (baseline is green: 94 tests + ruff clean)
key files: src/local_code_indexer/service.py, src/local_code_indexer/cli.py, tests/test_cli.py, tests/test_service.py, src/local_code_indexer/tools.py, tests/test_mcp_server.py, README.md
