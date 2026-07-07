---
project: local-code-indexer
tier: prototype
status: doing
current_round: 5
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
  - round: 2
    branch: "fleet/round-2-filter-value-hints"
    base: "fleet/round-4-empty-index-guidance"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/5"
    commit: "5a012dd"
    status: "review"
    note: "trajectory: matched keyFiles exactly (cli/service/test_cli/test_service/README + spec render); human-only hints, JSON+MCP untouched"
---

# local-code-indexer — fleet spec

## Intent

<running scope conversation>

## Stakes

prototype

## Acceptance bar

- verify: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` green
- Service: search() sets an inspectable attribute last_vector_skip_reason (reset to None alongside the existing last_vector_backend reset at service.py:858) when mode includes vector: 'embeddings-disabled' when self.embedder is None; 'query-embedding-failed' when the embedder is set but _embed_query returned None; 'no-embedded-chunks' when the query embedded successfully but zero embedded chunks are stored in the searched scope; None otherwise. Search return values and filter semantics unchanged.
- CLI: when `search --mode vector` human-readable output is empty and at least one repo is indexed, print 'No results.' plus one hint line naming the cause and a next action (e.g. "note: vector search unavailable: embeddings are disabled (LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS=1). try --mode lexical."; unreachable-service and no-embedded-chunks variants point at restoring the embedding service / re-running `local-code-indexer index <repo_path>`).
- Hybrid and lexical empty output unchanged: exactly 'No results.' plus only the existing filter hints; existing guard tests (test_cli.py test_empty_read_side_results_print_friendly_line at :493, filter-hint tests :511-633, test_known_filter_with_no_results_prints_only_no_results at :619) stay green.
- Zero-repos precedence unchanged: EMPTY_INDEX_HINT still wins (tests at test_cli.py:635 and :650 stay green); when both a filter hint and the vector hint apply, output order is deterministic and tested.
- --json empty results remain [] with no hint text (test_json_empty_results_stay_empty_arrays at test_cli.py:659 stays green); MCP tools.py untouched; tests/test_mcp_server.py green unmodified.
- New CLI tests: vector-mode empty search under the default DISABLE_EMBEDDINGS=1 fixture, using a query that matches no paths/symbols (path/symbol scoring runs in every mode and can make vector-mode output non-empty even with no embedder), prints the disabled hint; hybrid-mode empty search stays bare 'No results.'; --json vector-mode empty stays []. New service tests using an injected stub embedder (IndexService(db, embedder=...), pattern already used at tests/test_service.py:212): raising embedder yields 'query-embedding-failed'; embedder=None yields 'embeddings-disabled'; working stub embedder with no stored vectors yields 'no-embedded-chunks'; lexical-mode search leaves the reason None and no hints leak.
- README gets a one-line note about the vector-mode unavailability hint (near the existing empty-state hint paragraph at lines 41-43).
- Verify green: .venv/bin/python -m pytest -q && .venv/bin/ruff check . (baseline: 107 tests + ruff clean, independently confirmed on 5a012dd)

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

### Round 2 — fleet/round-2-filter-value-hints
base: fleet/round-4-empty-index-guidance
branch: fleet/round-2-filter-value-hints
pr: https://github.com/nathanmauro/local-code-indexer/pull/5
commit: 5a012dd
status: review
note: trajectory: matched keyFiles exactly (cli/service/test_cli/test_service/README + spec render); human-only hints, JSON+MCP untouched

### Round 5 — Explain empty --mode vector search results when vector search is unavailable
why: docs/fleet/spec.md Rounds 1-5 build one useability arc: every unknown/empty CLI state explains itself (round 3 unknown repos, round 4 empty index, round 5/PR#5 no-match filter values). Direct inspection of the current HEAD confirms the last silent state: `search --mode vector` with embeddings disabled (service.py:100-106, embedder None), a dead embedding service (_embed_query swallows all exceptions and returns None at service.py:746-752), or zero stored embedded chunks prints a bare 'No results.' via cli.py _print_read_results — indistinguishable from 'no semantically similar code'. Decided/Deferred in the living spec are empty; nothing blocks it, and it completes the arc without touching JSON or MCP surfaces, consistent with rounds 4-5.
acceptance:
- Service: search() sets an inspectable attribute last_vector_skip_reason (reset to None alongside the existing last_vector_backend reset at service.py:858) when mode includes vector: 'embeddings-disabled' when self.embedder is None; 'query-embedding-failed' when the embedder is set but _embed_query returned None; 'no-embedded-chunks' when the query embedded successfully but zero embedded chunks are stored in the searched scope; None otherwise. Search return values and filter semantics unchanged.
- CLI: when `search --mode vector` human-readable output is empty and at least one repo is indexed, print 'No results.' plus one hint line naming the cause and a next action (e.g. "note: vector search unavailable: embeddings are disabled (LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS=1). try --mode lexical."; unreachable-service and no-embedded-chunks variants point at restoring the embedding service / re-running `local-code-indexer index <repo_path>`).
- Hybrid and lexical empty output unchanged: exactly 'No results.' plus only the existing filter hints; existing guard tests (test_cli.py test_empty_read_side_results_print_friendly_line at :493, filter-hint tests :511-633, test_known_filter_with_no_results_prints_only_no_results at :619) stay green.
- Zero-repos precedence unchanged: EMPTY_INDEX_HINT still wins (tests at test_cli.py:635 and :650 stay green); when both a filter hint and the vector hint apply, output order is deterministic and tested.
- --json empty results remain [] with no hint text (test_json_empty_results_stay_empty_arrays at test_cli.py:659 stays green); MCP tools.py untouched; tests/test_mcp_server.py green unmodified.
- New CLI tests: vector-mode empty search under the default DISABLE_EMBEDDINGS=1 fixture, using a query that matches no paths/symbols (path/symbol scoring runs in every mode and can make vector-mode output non-empty even with no embedder), prints the disabled hint; hybrid-mode empty search stays bare 'No results.'; --json vector-mode empty stays []. New service tests using an injected stub embedder (IndexService(db, embedder=...), pattern already used at tests/test_service.py:212): raising embedder yields 'query-embedding-failed'; embedder=None yields 'embeddings-disabled'; working stub embedder with no stored vectors yields 'no-embedded-chunks'; lexical-mode search leaves the reason None and no hints leak.
- README gets a one-line note about the vector-mode unavailability hint (near the existing empty-state hint paragraph at lines 41-43).
- Verify green: .venv/bin/python -m pytest -q && .venv/bin/ruff check . (baseline: 107 tests + ruff clean, independently confirmed on 5a012dd)
key files: src/local_code_indexer/cli.py, src/local_code_indexer/service.py, tests/test_cli.py, tests/test_service.py, README.md, docs/fleet/spec.md
