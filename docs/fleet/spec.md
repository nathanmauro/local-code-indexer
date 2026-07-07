---
project: local-code-indexer
tier: production
status: doing
current_round: 8
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
    status: "done"
    note: "Development Status classifier set to 3 - Alpha; verify command passed with pytest and Ruff clean. | trajectory: matched keyFiles exactly (pyproject.toml+tests/test_packaging.py+docs/fleet/spec.md changed; __init__.py correctly read-only, untouched); no README/LICENSE/src touched, independent of unmerged PR #7 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#8 base correctly targets next."
  - round: 3
    branch: "fleet/round-3-packaging-file-hygiene"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/9"
    commit: "93a8127"
    status: "done"
    note: "trajectory: matched keyFiles exactly (py.typed+gitignore+new test+spec render); README/LICENSE/pyproject version-classifiers-urls correctly untouched; independent of unmerged PR #7/#8 as scoped; independently reproduced verify: pytest all green, ruff clean. Orchestrator note: fleet-open-pr.sh base-detection bug recurred (2nd time, same root cause as round 1) — opened draft PR against fleet/round-2-pypi-packaging-metadata instead of next; corrected via gh pr edit 9 --base next. Root-caused and FIXED this time: fleet-open-pr.sh now checks git merge-base --is-ancestor before trusting the last lineage branch as base, falling back to default_branch when the round was scoped independently (as this GA arc's sibling-branch pattern requires). Future rounds should no longer need this manual patch."
  - round: 4
    branch: "fleet/round-4-add-changelog-contributing-docs"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/10"
    commit: "49c6bf3"
    status: "done"
    note: "trajectory: matched keyFiles exactly (CHANGELOG.md+CONTRIBUTING.md+tests/test_ga_docs.py+spec render); README/LICENSE/pyproject/.gitignore/py.typed correctly untouched; independent of unmerged PR #7/#8/#9 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#10 base correctly targets next (fleet-open-pr.sh fix from round 3 confirmed working, no manual correction needed this round)."
  - round: 5
    branch: "fleet/round-5-add-ci-workflow"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/11"
    commit: "c9ac6f7"
    status: "done"
    note: "trajectory: matched keyFiles exactly (.github/workflows/ci.yml+tests/test_ci_workflow.py+spec render); README/LICENSE/pyproject/.gitignore/CHANGELOG/CONTRIBUTING/py.typed correctly untouched; independent of unmerged PR #7/#8/#9/#10 as scoped; TDD followed (red test on missing ci.yml, green after); independently reproduced verify: pytest all green, ruff clean; PR#11 base correctly targets next; no pyyaml dependency added as instructed."
  - round: 6
    branch: "fleet/round-6-build-artifact-verification"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/12"
    commit: "86ad1b6"
    status: "review"
    note: ""
  - round: 7
    branch: "fleet/round-7-add-version-flag"
    base: "next"
    pr: "https://github.com/nathanmauro/local-code-indexer/pull/13"
    commit: "2a0b4d3"
    status: "done"
    note: ""
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
- README.md gains a new '## Installation' section placed between the intro paragraph/architecture diagrams and the existing '## Local-model quickstart' section, containing at minimum the literal command `pip install local-code-indexer`, and one sentence noting the Python 3.11+ requirement matching pyproject.toml's `requires-python = ">=3.11"`. Do not edit any other existing README section (Architecture, Local-model quickstart, CLI reference, MCP tools, Retrieval mechanics, Indexing behavior, Configuration, Ignore rules, License) beyond inserting this new section
- tests/test_ga_docs.py gets a new test function (or an extension of the existing one) asserting README.md contains both the heading '## Installation' and the literal substring 'pip install local-code-indexer'. Do not weaken or remove the existing CHANGELOG/CONTRIBUTING assertions already in that file
- CHANGELOG.md's [Unreleased] section gets exactly one new bullet under '### Added' describing the new Installation section (no other CHANGELOG edits)
- Do not touch pyproject.toml, LICENSE, CONTRIBUTING.md, src/local_code_indexer/**, or any other test file -- this is a docs-plus-test-only slice
- verify command green: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .`
- docs/fleet/spec.md is re-rendered via fleet-spec.sh and staged with this round's entry

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
status: done
note: Development Status classifier set to 3 - Alpha; verify command passed with pytest and Ruff clean. | trajectory: matched keyFiles exactly (pyproject.toml+tests/test_packaging.py+docs/fleet/spec.md changed; __init__.py correctly read-only, untouched); no README/LICENSE/src touched, independent of unmerged PR #7 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#8 base correctly targets next.

### Round 3 — fleet/round-3-packaging-file-hygiene
base: next
branch: fleet/round-3-packaging-file-hygiene
pr: https://github.com/nathanmauro/local-code-indexer/pull/9
commit: 93a8127
status: done
note: trajectory: matched keyFiles exactly (py.typed+gitignore+new test+spec render); README/LICENSE/pyproject version-classifiers-urls correctly untouched; independent of unmerged PR #7/#8 as scoped; independently reproduced verify: pytest all green, ruff clean. Orchestrator note: fleet-open-pr.sh base-detection bug recurred (2nd time, same root cause as round 1) — opened draft PR against fleet/round-2-pypi-packaging-metadata instead of next; corrected via gh pr edit 9 --base next. Root-caused and FIXED this time: fleet-open-pr.sh now checks git merge-base --is-ancestor before trusting the last lineage branch as base, falling back to default_branch when the round was scoped independently (as this GA arc's sibling-branch pattern requires). Future rounds should no longer need this manual patch.

### Round 4 — fleet/round-4-add-changelog-contributing-docs
base: next
branch: fleet/round-4-add-changelog-contributing-docs
pr: https://github.com/nathanmauro/local-code-indexer/pull/10
commit: 49c6bf3
status: done
note: trajectory: matched keyFiles exactly (CHANGELOG.md+CONTRIBUTING.md+tests/test_ga_docs.py+spec render); README/LICENSE/pyproject/.gitignore/py.typed correctly untouched; independent of unmerged PR #7/#8/#9 as scoped; independently reproduced verify: pytest all green, ruff clean; PR#10 base correctly targets next (fleet-open-pr.sh fix from round 3 confirmed working, no manual correction needed this round).

### Round 5 — fleet/round-5-add-ci-workflow
base: next
branch: fleet/round-5-add-ci-workflow
pr: https://github.com/nathanmauro/local-code-indexer/pull/11
commit: c9ac6f7
status: done
note: trajectory: matched keyFiles exactly (.github/workflows/ci.yml+tests/test_ci_workflow.py+spec render); README/LICENSE/pyproject/.gitignore/CHANGELOG/CONTRIBUTING/py.typed correctly untouched; independent of unmerged PR #7/#8/#9/#10 as scoped; TDD followed (red test on missing ci.yml, green after); independently reproduced verify: pytest all green, ruff clean; PR#11 base correctly targets next; no pyyaml dependency added as instructed.

### Round 6 — fleet/round-6-build-artifact-verification
base: next
branch: fleet/round-6-build-artifact-verification
pr: https://github.com/nathanmauro/local-code-indexer/pull/12
commit: 86ad1b6
status: review
note:

### Round 7 — fleet/round-7-add-version-flag
base: next
branch: fleet/round-7-add-version-flag
pr: https://github.com/nathanmauro/local-code-indexer/pull/13
commit: 2a0b4d3
status: done
note:

### Round 8 — Add a README Installation section (pip install + Python 3.11+ note), locked in by a test
why: The GA danger field explicitly calls for 'a clean README that tells this story' plus 'packaging polish'; direct inspection confirmed README.md has architecture diagrams, a local-model quickstart, CLI reference, and MCP tools sections but literally no 'pip install' / 'pipx' / 'uv tool' string anywhere -- a new user cannot learn how to obtain the local-code-indexer command from the README. All 19+4 audit-doc hardening findings I checked are already remediated in source (sqlite-vec k constraint, async MCP tools, UTF-8 sniff boundary, secret-name/env exclusion, symlink skip, path-first repo identity, repo_path directory validation, per-file commit boundaries), so hardening is not the remaining gap; the install-instructions gap is the one concrete, verifiable GA-readiness item left, and it is independent of PR #12 (build-artifact verification only touches ci.yml/pyproject.toml/tests/test_build_artifact.py, no README) and distinct from all 12 prior merged/draft PRs. docs/fleet/spec.md's Decided/Deferred sections are empty and its Rounds log has no round 8 entry, so this is genuinely open, not already attempted or explicitly deferred.
acceptance:
- README.md gains a new '## Installation' section placed between the intro paragraph/architecture diagrams and the existing '## Local-model quickstart' section, containing at minimum the literal command `pip install local-code-indexer`, and one sentence noting the Python 3.11+ requirement matching pyproject.toml's `requires-python = ">=3.11"`. Do not edit any other existing README section (Architecture, Local-model quickstart, CLI reference, MCP tools, Retrieval mechanics, Indexing behavior, Configuration, Ignore rules, License) beyond inserting this new section
- tests/test_ga_docs.py gets a new test function (or an extension of the existing one) asserting README.md contains both the heading '## Installation' and the literal substring 'pip install local-code-indexer'. Do not weaken or remove the existing CHANGELOG/CONTRIBUTING assertions already in that file
- CHANGELOG.md's [Unreleased] section gets exactly one new bullet under '### Added' describing the new Installation section (no other CHANGELOG edits)
- Do not touch pyproject.toml, LICENSE, CONTRIBUTING.md, src/local_code_indexer/**, or any other test file -- this is a docs-plus-test-only slice
- verify command green: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .`
- docs/fleet/spec.md is re-rendered via fleet-spec.sh and staged with this round's entry
key files: README.md (add the new Installation section only), tests/test_ga_docs.py (add/extend the assertion), CHANGELOG.md ([Unreleased] > Added only), docs/fleet/spec.md (re-rendered), pyproject.toml (read-only reference for package name + requires-python, do not edit)
