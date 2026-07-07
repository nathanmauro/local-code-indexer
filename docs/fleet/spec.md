---
project: local-code-indexer
tier: production
status: review
current_round: 5
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
  - round: 1
    branch: "fleet/round-1-ga-readme-rewrite"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/7"
    commit: "bdd14de"
    status: "done"
    note: "trajectory: intended keyFiles README.md+docs/fleet/spec.md+LICENSE all changed as planned; pyproject.toml/cli.py/decisions doc were read-only references, correctly untouched. Orchestrator note: fleet-open-pr.sh auto-detected PR base from a stale branch_lineage tail left over from the PRIOR (already-merged) arc and opened the draft PR against fleet/round-5-explain-empty-vector-search instead of next; corrected via gh pr edit 7 --base next post-hoc, and this lineage entry base field corrected to match. Root cause (spec mirror branch_lineage not reset between arcs) noted for a future round."
  - round: 2
    branch: "fleet/round-2-pypi-packaging-metadata"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/8"
    commit: "412cd2f"
    status: "review"
    note: "Development Status classifier set to 3 - Alpha; verify command passed with pytest and Ruff clean. | trajectory: matched keyFiles exactly (pyproject.toml+tests/test_packaging.py+docs/fleet/spec.md changed; __init__.py correctly read-only, untouched); no README/LICENSE/src touched, independent of unmerged PR #7 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#8 base correctly targets next."
  - round: 3
    branch: "fleet/round-3-packaging-file-hygiene"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/9"
    commit: "93a8127"
    status: "review"
    note: "trajectory: matched keyFiles exactly (py.typed+gitignore+new test+spec render); README/LICENSE/pyproject version-classifiers-urls correctly untouched; independent of unmerged PR #7/#8 as scoped; independently reproduced verify: pytest all green, ruff clean. Orchestrator note: fleet-open-pr.sh base-detection bug recurred (2nd time, same root cause as round 1) — opened draft PR against fleet/round-2-pypi-packaging-metadata instead of next; corrected via gh pr edit 9 --base next. Root-caused and FIXED this time: fleet-open-pr.sh now checks git merge-base --is-ancestor before trusting the last lineage branch as base, falling back to default_branch when the round was scoped independently (as this GA arc's sibling-branch pattern requires). Future rounds should no longer need this manual patch."
  - round: 4
    branch: "fleet/round-4-add-changelog-contributing-docs"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/10"
    commit: "49c6bf3"
    status: "review"
    note: "trajectory: matched keyFiles exactly (CHANGELOG.md+CONTRIBUTING.md+tests/test_ga_docs.py+spec render); README/LICENSE/pyproject/.gitignore/py.typed correctly untouched; independent of unmerged PR #7/#8/#9 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#10 base correctly targets next (fleet-open-pr.sh fix from round 3 confirmed working, no manual correction needed this round)."
  - round: 5
    branch: "fleet/round-5-add-ci-workflow"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/11"
    commit: "c9ac6f7"
    status: "review"
    note: "trajectory: matched keyFiles exactly (.github/workflows/ci.yml+tests/test_ci_workflow.py+spec render); README/LICENSE/pyproject/.gitignore/CHANGELOG/CONTRIBUTING/py.typed correctly untouched; independent of unmerged PR #7/#8/#9/#10 as scoped; TDD followed (red test on missing ci.yml, green after); independently reproduced verify: pytest all green, ruff clean; PR#11 base correctly targets next; no pyyaml dependency added as instructed."
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
- New file .github/workflows/ci.yml exists, triggers on push to next/main and on pull_request, sets up Python 3.11 (matching pyproject.toml's requires-python >=3.11 and the local .venv, confirmed Python 3.11.15), installs the project with `pip install -e '.[dev]'`, and runs the exact verify command in two steps (or one combined step): `python -m pytest -q` and `ruff check .`
- CI job fails (non-zero exit) if either pytest or ruff fails -- do not swallow errors or use continue-on-error
- New test file tests/test_ci_workflow.py (do not edit any existing test file) asserts .github/workflows/ci.yml exists and contains both 'pytest' and 'ruff' substrings plus top-level 'on:' and 'jobs:' keys. PyYAML is CONFIRMED NOT installed in .venv and is NOT a pyproject.toml dependency -- do NOT add pyyaml (or any new dependency) to pyproject.toml to make YAML parsing work; write a dependency-free structural check (string/regex checks) instead, since pyproject.toml is explicitly off-limits this round
- README.md, LICENSE, pyproject.toml, .gitignore, CHANGELOG.md, CONTRIBUTING.md, src/local_code_indexer/py.typed are NOT touched -- those are owned by unmerged PRs #7, #8, #9, #10
- No files under src/local_code_indexer/ are modified (no behavior changes)
- `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` passes locally, independently reproduced, not just claimed
- docs/fleet/spec.md is re-rendered via the fleet-spec.sh script and staged with this round's entry

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

### Round 1 — fleet/round-1-ga-readme-rewrite
base: next
branch: fleet/round-1-ga-readme-rewrite
pr: https://github.com/nathanmauro/local-code-indexer/pull/7
commit: bdd14de
status: done
note: trajectory: intended keyFiles README.md+docs/fleet/spec.md+LICENSE all changed as planned; pyproject.toml/cli.py/decisions doc were read-only references, correctly untouched. Orchestrator note: fleet-open-pr.sh auto-detected PR base from a stale branch_lineage tail left over from the PRIOR (already-merged) arc and opened the draft PR against fleet/round-5-explain-empty-vector-search instead of next; corrected via gh pr edit 7 --base next post-hoc, and this lineage entry base field corrected to match. Root cause (spec mirror branch_lineage not reset between arcs) noted for a future round.

### Round 2 — fleet/round-2-pypi-packaging-metadata
base: next
branch: fleet/round-2-pypi-packaging-metadata
pr: https://github.com/nathanmauro/local-code-indexer/pull/8
commit: 412cd2f
status: review
note: Development Status classifier set to 3 - Alpha; verify command passed with pytest and Ruff clean. | trajectory: matched keyFiles exactly (pyproject.toml+tests/test_packaging.py+docs/fleet/spec.md changed; __init__.py correctly read-only, untouched); no README/LICENSE/src touched, independent of unmerged PR #7 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#8 base correctly targets next.

### Round 3 — fleet/round-3-packaging-file-hygiene
base: next
branch: fleet/round-3-packaging-file-hygiene
pr: https://github.com/nathanmauro/local-code-indexer/pull/9
commit: 93a8127
status: review
note: trajectory: matched keyFiles exactly (py.typed+gitignore+new test+spec render); README/LICENSE/pyproject version-classifiers-urls correctly untouched; independent of unmerged PR #7/#8 as scoped; independently reproduced verify: pytest all green, ruff clean. Orchestrator note: fleet-open-pr.sh base-detection bug recurred (2nd time, same root cause as round 1) — opened draft PR against fleet/round-2-pypi-packaging-metadata instead of next; corrected via gh pr edit 9 --base next. Root-caused and FIXED this time: fleet-open-pr.sh now checks git merge-base --is-ancestor before trusting the last lineage branch as base, falling back to default_branch when the round was scoped independently (as this GA arc's sibling-branch pattern requires). Future rounds should no longer need this manual patch.

### Round 4 — fleet/round-4-add-changelog-contributing-docs
base: next
branch: fleet/round-4-add-changelog-contributing-docs
pr: https://github.com/nathanmauro/local-code-indexer/pull/10
commit: 49c6bf3
status: review
note: trajectory: matched keyFiles exactly (CHANGELOG.md+CONTRIBUTING.md+tests/test_ga_docs.py+spec render); README/LICENSE/pyproject/.gitignore/py.typed correctly untouched; independent of unmerged PR #7/#8/#9 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#10 base correctly targets next (fleet-open-pr.sh fix from round 3 confirmed working, no manual correction needed this round).

### Round 5 — fleet/round-5-add-ci-workflow
base: next
branch: fleet/round-5-add-ci-workflow
pr: https://github.com/nathanmauro/local-code-indexer/pull/11
commit: c9ac6f7
status: review
note: trajectory: matched keyFiles exactly (.github/workflows/ci.yml+tests/test_ci_workflow.py+spec render); README/LICENSE/pyproject/.gitignore/CHANGELOG/CONTRIBUTING/py.typed correctly untouched; independent of unmerged PR #7/#8/#9/#10 as scoped; TDD followed (red test on missing ci.yml, green after); independently reproduced verify: pytest all green, ruff clean; PR#11 base correctly targets next; no pyyaml dependency added as instructed.

### Round 5 — Add GitHub Actions CI workflow running the verify command on PRs
why: Direct inspection (not a spec citation) confirms there is no .github/ directory anywhere in this repo -- not in the working tree, not on `next`, and not on any of the four open GA-arc draft PRs (#7 README/LICENSE, #8 packaging metadata, #9 py.typed/.gitignore, #10 CHANGELOG/CONTRIBUTING) -- so this repo has zero automated test/lint gate despite being public on GitHub with a GA-readiness arc underway. This is a real, independent, well-scoped hole distinct from all four claimed rounds. Note: the GA-arc danger field does NOT literally name 'GitHub Actions CI workflow' -- that specific phrase does not appear in docs/fleet/spec.md, the audits, or the codex-fleet skill; this task is justified by direct repo inspection and the danger field's general call for 'GA-ready open-source presentation' and 'hardening', not by a verbatim citation.
acceptance:
- New file .github/workflows/ci.yml exists, triggers on push to next/main and on pull_request, sets up Python 3.11 (matching pyproject.toml's requires-python >=3.11 and the local .venv, confirmed Python 3.11.15), installs the project with `pip install -e '.[dev]'`, and runs the exact verify command in two steps (or one combined step): `python -m pytest -q` and `ruff check .`
- CI job fails (non-zero exit) if either pytest or ruff fails -- do not swallow errors or use continue-on-error
- New test file tests/test_ci_workflow.py (do not edit any existing test file) asserts .github/workflows/ci.yml exists and contains both 'pytest' and 'ruff' substrings plus top-level 'on:' and 'jobs:' keys. PyYAML is CONFIRMED NOT installed in .venv and is NOT a pyproject.toml dependency -- do NOT add pyyaml (or any new dependency) to pyproject.toml to make YAML parsing work; write a dependency-free structural check (string/regex checks) instead, since pyproject.toml is explicitly off-limits this round
- README.md, LICENSE, pyproject.toml, .gitignore, CHANGELOG.md, CONTRIBUTING.md, src/local_code_indexer/py.typed are NOT touched -- those are owned by unmerged PRs #7, #8, #9, #10
- No files under src/local_code_indexer/ are modified (no behavior changes)
- `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` passes locally, independently reproduced, not just claimed
- docs/fleet/spec.md is re-rendered via the fleet-spec.sh script and staged with this round's entry
key files: .github/workflows/ci.yml (new), tests/test_ci_workflow.py (new), docs/fleet/spec.md, pyproject.toml (read-only reference for Python version/dev extras -- confirmed no pyyaml present), README.md (read-only reference, do not edit)

