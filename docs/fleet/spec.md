---
project: local-code-indexer
tier: production
status: review
current_round: 6
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
- pyproject.toml [project.optional-dependencies].dev gains BOTH "build>=1.0" AND "hatchling>=1.21" (hatchling must be explicit here too -- confirmed NOT already present in .venv, and --no-isolation builds require it locally present; matches the version already pinned in [build-system] requires) -- these are the ONLY additions to this file, do not touch version/classifiers/urls/dependencies
- New test file tests/test_build_artifact.py (do not edit any existing test file) builds the project into a temp directory via `python -m build --wheel --sdist --outdir <tmp> --no-isolation` (subprocess, using sys.executable) and asserts: the build succeeds (returncode 0), exactly one .whl and one .tar.gz are produced, the wheel (a zip file) contains local_code_indexer/py.typed and local_code_indexer/cli.py, the wheel does NOT contain any tests/ or test_*.py files, and the sdist (a tar.gz) contains LICENSE, README.md, and pyproject.toml. Do NOT add an assertion that the sdist excludes arbitrary local files (e.g. dotfiles/session-lock files) -- hatchling's default sdist inclusion is not fully VCS-ignore-aware for locally-excluded-but-untracked files and such an assertion would be flaky/environment-dependent; only assert presence of required files and the wheel's test-exclusion (which is deterministic via [tool.hatch.build.targets.wheel] packages).
- The build-artifact test is skipped gracefully (pytest.importorskip("build") and pytest.importorskip("hatchling"), or an equivalent fixture) if either module cannot be imported, so `pytest -q` never hard-fails in an environment where the dev extra was not installed -- but locally, after installing the dev extra for real (see verify command below), the test must actually RUN, not skip
- .github/workflows/ci.yml gets one additional step after the existing test/ruff steps that runs `python -m build` (or `python -m pytest tests/test_build_artifact.py -q` is sufficient if the new test already exercises build) so a broken package build fails CI -- keep the existing steps and ordering intact, do not remove or reorder them, do not use continue-on-error. (CI installs via plain `pip install -e '.[dev]'` on a standard GitHub Actions Python setup, which has pip preinstalled -- the local uv-venv pip absence described below does not apply to CI.)
- README.md, LICENSE, CHANGELOG.md, CONTRIBUTING.md, .gitignore, src/local_code_indexer/py.typed, and any file under src/local_code_indexer/ are NOT modified (no src changes expected)
- Install the dev extra with `uv pip install --python .venv/bin/python -e '.[dev]'` (NOT `.venv/bin/python -m pip install ...` -- this repo's .venv is uv-managed and has NO pip module installed at all; that exact command was verified to fail with 'No module named pip'). If `uv` is unavailable in the session, fall back to `.venv/bin/python -m ensurepip && .venv/bin/python -m pip install -e '.[dev]'` as a bootstrap. Then `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` must pass green, independently reproduced, not just claimed.
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

### Round 6 — Prove the PyPI package actually builds correctly (wheel + sdist content verification)
why: The GA arc's danger field calls for 'packaging polish (PyPI-ready metadata, LICENSE, versioning)' and 'hardening from docs/audit-*.md leftovers'. Rounds 2-5 of the GA arc added pyproject metadata, py.typed, .gitignore hygiene, and CI, but nothing has ever actually run `python -m build` and inspected the resulting artifact -- tests/test_packaging.py and tests/test_py_typed_and_gitignore.py only check source-tree files and pyproject.toml fields, never a real built wheel/sdist. Verified by direct repo inspection: no test_build_artifact.py exists on any branch, `build` is absent from dev deps, and hatchling is not installed in .venv. This is the one remaining unverified claim in the GA packaging story and is a clean, well-scoped, independently testable slice distinct from all 11 prior merged PRs.
acceptance:
- pyproject.toml [project.optional-dependencies].dev gains BOTH "build>=1.0" AND "hatchling>=1.21" (hatchling must be explicit here too -- confirmed NOT already present in .venv, and --no-isolation builds require it locally present; matches the version already pinned in [build-system] requires) -- these are the ONLY additions to this file, do not touch version/classifiers/urls/dependencies
- New test file tests/test_build_artifact.py (do not edit any existing test file) builds the project into a temp directory via `python -m build --wheel --sdist --outdir <tmp> --no-isolation` (subprocess, using sys.executable) and asserts: the build succeeds (returncode 0), exactly one .whl and one .tar.gz are produced, the wheel (a zip file) contains local_code_indexer/py.typed and local_code_indexer/cli.py, the wheel does NOT contain any tests/ or test_*.py files, and the sdist (a tar.gz) contains LICENSE, README.md, and pyproject.toml. Do NOT add an assertion that the sdist excludes arbitrary local files (e.g. dotfiles/session-lock files) -- hatchling's default sdist inclusion is not fully VCS-ignore-aware for locally-excluded-but-untracked files and such an assertion would be flaky/environment-dependent; only assert presence of required files and the wheel's test-exclusion (which is deterministic via [tool.hatch.build.targets.wheel] packages).
- The build-artifact test is skipped gracefully (pytest.importorskip("build") and pytest.importorskip("hatchling"), or an equivalent fixture) if either module cannot be imported, so `pytest -q` never hard-fails in an environment where the dev extra was not installed -- but locally, after installing the dev extra for real (see verify command below), the test must actually RUN, not skip
- .github/workflows/ci.yml gets one additional step after the existing test/ruff steps that runs `python -m build` (or `python -m pytest tests/test_build_artifact.py -q` is sufficient if the new test already exercises build) so a broken package build fails CI -- keep the existing steps and ordering intact, do not remove or reorder them, do not use continue-on-error. (CI installs via plain `pip install -e '.[dev]'` on a standard GitHub Actions Python setup, which has pip preinstalled -- the local uv-venv pip absence described below does not apply to CI.)
- README.md, LICENSE, CHANGELOG.md, CONTRIBUTING.md, .gitignore, src/local_code_indexer/py.typed, and any file under src/local_code_indexer/ are NOT modified (no src changes expected)
- Install the dev extra with `uv pip install --python .venv/bin/python -e '.[dev]'` (NOT `.venv/bin/python -m pip install ...` -- this repo's .venv is uv-managed and has NO pip module installed at all; that exact command was verified to fail with 'No module named pip'). If `uv` is unavailable in the session, fall back to `.venv/bin/python -m ensurepip && .venv/bin/python -m pip install -e '.[dev]'` as a bootstrap. Then `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` must pass green, independently reproduced, not just claimed.
- docs/fleet/spec.md is re-rendered via fleet-spec.sh and staged with this round's entry
key files: pyproject.toml (add build + hatchling to dev extra only), tests/test_build_artifact.py (new), .github/workflows/ci.yml (add one build-verification step), docs/fleet/spec.md (re-rendered), tests/test_packaging.py (read-only reference, do not edit)

