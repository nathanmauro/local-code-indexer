---
project: local-code-indexer
tier: prototype
status: doing
current_round: 3
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
---

# local-code-indexer — fleet spec

## Intent

<running scope conversation>

## Stakes

prototype

## Acceptance bar

- verify: `.venv/bin/python -m pytest -q && .venv/bin/ruff check .` green
- A shared service helper (e.g. _require_known_repo(conn, repo)) raises ValueError when a non-empty repo name does not exist in the index, with a message of the form 'unknown repo: <name>. indexed repos: <comma-list or (none)>'.
- service.search, service.symbols, and service.list_files call it when a repo argument is provided (repo is not None/empty); when repo is empty/None they keep their current cross-repo behavior unchanged.
- service.read_file distinguishes the two cases: an unknown repo raises ValueError('unknown repo: ...') while a known repo with a missing file keeps the existing FileNotFoundError('<repo>:<path> is not indexed').
- A valid --repo that simply has no matches STILL returns empty results (prints 'No results.') — only a genuinely unknown repo errors.
- CLI behavior: running e.g. `search foo --repo nope` exits non-zero (code 1) and prints 'error: unknown repo: nope. indexed repos: ...' to stderr (the existing main() except-block at cli.py:328-330 already formats ValueError this way — confirm, do not duplicate).
- New tests in tests/test_cli.py assert: (a) search/symbols/list-files with an unknown --repo raise SystemExit code 1 and the stderr contains 'unknown repo' plus the name of an indexed repo; (b) read-file with an unknown repo errors with 'unknown repo' while read-file of a known repo + missing path still says 'is not indexed'; (c) a valid repo with no query matches still prints 'No results.' (regression guard).
- All pre-existing tests stay green and the MCP server tests (tests/test_mcp_server.py) still pass — they index a real 'demo' repo so they should be unaffected; verify rather than assume.
- README CLI section (the '## CLI' heading at README.md:9) gets a one-line note that read-side commands error with the list of indexed repos when an unknown --repo is given.
- verify command green: .venv/bin/python -m pytest -q && .venv/bin/ruff check .

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

### Round 3 — Unknown-repo validation with helpful errors across read-side commands
why: The fleet theme is useability (spec.danger='useability' + context hint). Rounds 1-2 finished the human-readable-output story across read and write commands, so the next useability defect is silent/confusing behavior on a mistyped repo name: search/symbols/list-files return empty (indistinguishable from 'no matches'), and read-file raises 'X:path is not indexed' which conflates an unknown repo with a missing file. Validating the repo against the index and failing fast with the list of available repos is the natural, well-scoped continuation per docs/fleet/spec.md (empty Decided/Deferred). It mirrors an existing pattern: remove_repo already raises ValueError('unknown repo: name') from the service (service.py:1324), and the CLI already catches ValueError/FileNotFoundError and exits 1 (cli.py:328-330). Verified by direct inspection that none of search/symbols/list_files currently validate the repo.
acceptance:
- A shared service helper (e.g. _require_known_repo(conn, repo)) raises ValueError when a non-empty repo name does not exist in the index, with a message of the form 'unknown repo: <name>. indexed repos: <comma-list or (none)>'.
- service.search, service.symbols, and service.list_files call it when a repo argument is provided (repo is not None/empty); when repo is empty/None they keep their current cross-repo behavior unchanged.
- service.read_file distinguishes the two cases: an unknown repo raises ValueError('unknown repo: ...') while a known repo with a missing file keeps the existing FileNotFoundError('<repo>:<path> is not indexed').
- A valid --repo that simply has no matches STILL returns empty results (prints 'No results.') — only a genuinely unknown repo errors.
- CLI behavior: running e.g. `search foo --repo nope` exits non-zero (code 1) and prints 'error: unknown repo: nope. indexed repos: ...' to stderr (the existing main() except-block at cli.py:328-330 already formats ValueError this way — confirm, do not duplicate).
- New tests in tests/test_cli.py assert: (a) search/symbols/list-files with an unknown --repo raise SystemExit code 1 and the stderr contains 'unknown repo' plus the name of an indexed repo; (b) read-file with an unknown repo errors with 'unknown repo' while read-file of a known repo + missing path still says 'is not indexed'; (c) a valid repo with no query matches still prints 'No results.' (regression guard).
- All pre-existing tests stay green and the MCP server tests (tests/test_mcp_server.py) still pass — they index a real 'demo' repo so they should be unaffected; verify rather than assume.
- README CLI section (the '## CLI' heading at README.md:9) gets a one-line note that read-side commands error with the list of indexed repos when an unknown --repo is given.
- verify command green: .venv/bin/python -m pytest -q && .venv/bin/ruff check .
key files: src/local_code_indexer/service.py, tests/test_cli.py, src/local_code_indexer/cli.py, src/local_code_indexer/tools.py, tests/test_mcp_server.py, README.md
