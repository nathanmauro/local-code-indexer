---
project: local-code-indexer
tier: production
status: doing
current_round: 1
verify_cmd: ".venv/bin/python -m pytest -q && .venv/bin/ruff check ."
push_allowed: true
danger: "GA arc: reposition this project as the fully-local retrieval stack for LOCAL coding models — Ollama/LM Studio embeddings + SQLite FTS5/sqlite-vec index + MCP retrieval, loopback-enforced by design. Frontier agents have agentic grep; local models need retrieval help — that is the story. Goal: GA-ready open-source presentation on the default branch (next): a clean README that tells this story with mermaid architecture diagrams, a local-model quickstart (Ollama embeddings + a local coding agent via MCP), packaging polish (PyPI-ready metadata, LICENSE, versioning), and hardening from docs/audit-*.md leftovers. The first slice must also rewrite the docs/fleet/spec.md Intent section to this repositioning. The prior PR stack (#1-#6) is fully merged into next; base new round branches on next. The stale main branch is a cleanup item (default branch is next). Draft PRs to next are allowed and desired."
branch_lineage:
  - round: 1
    branch: "fleet/round-1-human-readable-cli-output"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/1"
    commit: "e81ed25"
    status: "done"
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
    status: "done"
    note: ""
  - round: 4
    branch: "fleet/round-4-empty-index-guidance"
    base: "fleet/round-3-unknown-repo-errors"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/4"
    commit: "27794aa"
    status: "done"
    note: "trajectory: intended keyFiles all covered; changed cli.py+service.py+tests/test_cli.py+README.md+docs/fleet/spec.md; tools.py/test_mcp_server.py verified unchanged-green as planned"
  - round: 2
    branch: "fleet/round-2-filter-value-hints"
    base: "fleet/round-4-empty-index-guidance"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/5"
    commit: "5a012dd"
    status: "done"
    note: "trajectory: matched keyFiles exactly (cli/service/test_cli/test_service/README + spec render); human-only hints, JSON+MCP untouched"
  - round: 5
    branch: "fleet/round-5-explain-empty-vector-search"
    base: "fleet/round-2-filter-value-hints"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/6"
    commit: "795649d"
    status: "done"
    note: "trajectory: matched keyFiles exactly; vector-only skip-reason hints, JSON+MCP unchanged; codex self-corrected mirror current_round 2->5 per orchestrator lineage note"
---

# local-code-indexer — fleet spec

## Intent

Fully-local retrieval stack for LOCAL coding models. Frontier hosted coding agents have agentic
grep/search and huge context windows; local coding models running through Ollama, LM Studio, or
llama.cpp are smaller and need retrieval help before they can reason over a repo. `local-code-indexer`
is that retrieval layer: loopback-enforced local embeddings, SQLite FTS5 plus sqlite-vec/JSON vector
search, and MCP retrieval tools that let local agents fetch relevant code without sending code or
embeddings off-machine.

GA arc: make the default `next` branch presentable as an open-source GA candidate. The arc includes
a README that tells the local-model retrieval story with mermaid architecture diagrams and a
local-model quickstart, packaging polish such as a real MIT `LICENSE`, PyPI-ready metadata and
versioning, and later hardening work only where the audit docs still leave accepted leftovers. The
prior useability arc, rounds 1-5 via PRs #1-#6, is fully merged into `next`; do not redo that work.

## Stakes

production

## Acceptance bar

- verify: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` green
- README.md opens with the local-model-retrieval narrative (frontier agents have agentic grep, local models need retrieval, this project is that layer, fully local via loopback)
- README.md contains at least one mermaid architecture diagram and a 'Local-model quickstart' section with CLI steps verified against src/local_code_indexer/cli.py
- All currently-documented CLI commands, MCP tools, env vars, and behaviors remain documented (no accurate content silently dropped)
- New LICENSE file at repo root: MIT text, copyright Nathan Mauro
- docs/fleet/spec.md '## Intent' section is rewritten for the GA local-model retrieval arc
- No files under src/ or tests/ modified
- `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` stays green (baseline: 114 tests passing, ruff clean on next HEAD a94a18c — independently reproduced, not just claimed)

## Decided

## Deferred

## Rounds

### Round 1 — fleet/round-1-human-readable-cli-output
base: next
branch: fleet/round-1-human-readable-cli-output
pr: https://github.com/nathanmauro/local-code-indexer/pull/1
commit: e81ed25
status: done
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
status: done
note:

### Round 4 — fleet/round-4-empty-index-guidance
base: fleet/round-3-unknown-repo-errors
branch: fleet/round-4-empty-index-guidance
pr: https://github.com/nathanmauro/local-code-indexer/pull/4
commit: 27794aa
status: done
note: trajectory: intended keyFiles all covered; changed cli.py+service.py+tests/test_cli.py+README.md+docs/fleet/spec.md; tools.py/test_mcp_server.py verified unchanged-green as planned

### Round 2 — fleet/round-2-filter-value-hints
base: fleet/round-4-empty-index-guidance
branch: fleet/round-2-filter-value-hints
pr: https://github.com/nathanmauro/local-code-indexer/pull/5
commit: 5a012dd
status: done
note: trajectory: matched keyFiles exactly (cli/service/test_cli/test_service/README + spec render); human-only hints, JSON+MCP untouched

### Round 5 — fleet/round-5-explain-empty-vector-search
base: fleet/round-2-filter-value-hints
branch: fleet/round-5-explain-empty-vector-search
pr: https://github.com/nathanmauro/local-code-indexer/pull/6
commit: 795649d
status: done
note: trajectory: matched keyFiles exactly; vector-only skip-reason hints, JSON+MCP unchanged; codex self-corrected mirror current_round 2->5 per orchestrator lineage note

### Round 1 — GA README rewrite + LICENSE + fleet spec Intent repositioning
why: The spec mirror ~/.codex-goals/local-code-indexer.spec.json confirms status:'planned', current_round:1, tier:'production', and an 'intent' field explicitly framing this GA repositioning, stating verbatim that 'The first slice must also rewrite the docs/fleet/spec.md Intent section to this repositioning.' docs/fleet/spec.md's own Intent section was still the stale running-scope placeholder before this slice (verified by reading the file), and the current README (113 lines, verified) had all the right technical facts but zero narrative, no mermaid diagram, no 'Local-model quickstart' section, and no LICENSE file anywhere in git history despite pyproject.toml declaring license = "MIT".
acceptance:
- README.md opens with the local-model-retrieval narrative (frontier agents have agentic grep, local models need retrieval, this project is that layer, fully local via loopback)
- README.md contains at least one mermaid architecture diagram and a 'Local-model quickstart' section with CLI steps verified against src/local_code_indexer/cli.py
- All currently-documented CLI commands, MCP tools, env vars, and behaviors remain documented (no accurate content silently dropped)
- New LICENSE file at repo root: MIT text, copyright Nathan Mauro
- docs/fleet/spec.md '## Intent' section is rewritten for the GA local-model retrieval arc
- No files under src/ or tests/ modified
- `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` stays green (baseline: 114 tests passing, ruff clean on next HEAD a94a18c — independently reproduced, not just claimed)
key files: README.md, docs/fleet/spec.md, LICENSE (new), pyproject.toml, src/local_code_indexer/cli.py, docs/decisions/0001-embedding-backend-ollama.md
