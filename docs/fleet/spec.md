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
  - round: 4
    branch: "fleet/round-4-empty-index-guidance"
    base: "fleet/round-3-unknown-repo-errors"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/4"
    commit: "27794aa"
    status: "review"
    note: "trajectory: intended keyFiles all covered; changed cli.py+service.py+tests/test_cli.py+README.md+docs/fleet/spec.md; tools.py/test_mcp_server.py verified unchanged-green as planned"
---

# local-code-indexer — fleet spec

## Intent

<running scope conversation>

## Stakes

prototype

## Acceptance bar

- verify: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` green
- Service gains list_languages() and list_kinds(): sorted distinct non-empty LOWERCASED values (SELECT DISTINCT lower(...)) from files.language and symbols.kind respectively — lowering is required because files.language stores the raw-cased suffix at index time (service.py:443) while filters compare lowercase; unit tests in tests/test_service.py including a mixed-case fixture.
- CLI: when search/symbols/list-files human-readable output is empty, at least one repo is indexed, and a supplied --lang value (normalized via the same lstrip('.').lower() semantics as _normalize_lang_filter) is not in list_languages(), print 'No results.' plus a hint line naming the value and the indexed languages (e.g. "note: --lang 'rs' matches nothing. indexed languages: md, py, toml"); same for --kind vs list_kinds() on search/symbols. list-files only has --lang.
- When supplied filter values DO exist in the index (or no filters given), empty output remains exactly 'No results.' — the existing guard test_empty_read_side_results_print_friendly_line (tests/test_cli.py:493-508) stays green.
- Zero-repos case unchanged: EMPTY_INDEX_HINT still prints and takes precedence over filter hints (existing tests at tests/test_cli.py:511 and :526 stay green).
- --json empty results remain [] with no hint text (tests/test_cli.py:535 test_json_empty_results_stay_empty_arrays stays green); MCP tools.py untouched; tests/test_mcp_server.py green unmodified.
- Service filter semantics preserved: unknown lang/kind still return [] (test_service.py:117,183,202,221,253 unchanged and green).
- New tests in tests/test_cli.py: search --lang unknown prints hint with real indexed language; search --kind unknown prints hint with indexed kinds; symbols and list-files analogs; known-lang-no-match prints exactly 'No results.'; --json stays [].
- README gets a one-line note about the no-match filter hint.
- Verify green: .venv/bin/python -m pytest -q && .venv/bin/ruff check . (baseline: 99 tests + ruff clean, confirmed)

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

### Round 4 — fleet/round-4-empty-index-guidance
base: fleet/round-3-unknown-repo-errors
branch: fleet/round-4-empty-index-guidance
pr: https://github.com/nathanmauro/local-code-indexer/pull/4
commit: 27794aa
status: review
note: trajectory: intended keyFiles all covered; changed cli.py+service.py+tests/test_cli.py+README.md+docs/fleet/spec.md; tools.py/test_mcp_server.py verified unchanged-green as planned

### Round 4 — Explain no-match --lang/--kind filter values with indexed-value hints
why: docs/fleet/spec.md Rounds 1-4 build one useability story: output is human-readable and every unknown/empty state explains itself (round 3 unknown repos, round 4 empty index + status/remove). Direct inspection confirms the last silent state: `search --lang rs` or `symbols --kind constant` against an index with no such language/kind prints a bare 'No results.' (cli.py _print_search/_print_symbols/_print_list_files via _print_read_results), indistinguishable from no matches. Service-layer errors are ruled out by pinned tests (test_service.py:117,183,202,221,253 assert [] for unknown lang/kind), so the round-4-consistent move is a human-output-only hint listing indexed languages/kinds. Decided/Deferred in the living spec are empty; nothing blocks it.
acceptance:
- Service gains list_languages() and list_kinds(): sorted distinct non-empty LOWERCASED values (SELECT DISTINCT lower(...)) from files.language and symbols.kind respectively — lowering is required because files.language stores the raw-cased suffix at index time (service.py:443) while filters compare lowercase; unit tests in tests/test_service.py including a mixed-case fixture.
- CLI: when search/symbols/list-files human-readable output is empty, at least one repo is indexed, and a supplied --lang value (normalized via the same lstrip('.').lower() semantics as _normalize_lang_filter) is not in list_languages(), print 'No results.' plus a hint line naming the value and the indexed languages (e.g. "note: --lang 'rs' matches nothing. indexed languages: md, py, toml"); same for --kind vs list_kinds() on search/symbols. list-files only has --lang.
- When supplied filter values DO exist in the index (or no filters given), empty output remains exactly 'No results.' — the existing guard test_empty_read_side_results_print_friendly_line (tests/test_cli.py:493-508) stays green.
- Zero-repos case unchanged: EMPTY_INDEX_HINT still prints and takes precedence over filter hints (existing tests at tests/test_cli.py:511 and :526 stay green).
- --json empty results remain [] with no hint text (tests/test_cli.py:535 test_json_empty_results_stay_empty_arrays stays green); MCP tools.py untouched; tests/test_mcp_server.py green unmodified.
- Service filter semantics preserved: unknown lang/kind still return [] (test_service.py:117,183,202,221,253 unchanged and green).
- New tests in tests/test_cli.py: search --lang unknown prints hint with real indexed language; search --kind unknown prints hint with indexed kinds; symbols and list-files analogs; known-lang-no-match prints exactly 'No results.'; --json stays [].
- README gets a one-line note about the no-match filter hint.
- Verify green: .venv/bin/python -m pytest -q && .venv/bin/ruff check . (baseline: 99 tests + ruff clean, confirmed)
key files: src/local_code_indexer/cli.py, src/local_code_indexer/service.py, tests/test_cli.py, tests/test_service.py, README.md, docs/fleet/spec.md
