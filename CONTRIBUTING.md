# Contributing

Thanks for helping improve `local-code-indexer`. This project is intended to stay a
fully local retrieval stack for private code: SQLite for index state, FTS5 and
sqlite-vec for retrieval, and loopback-only local embedding services.

## Local Development

Create a virtual environment and install the project with development dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/pip install -e '.[dev]'
```

If you use `uv`, keep the editable install behavior equivalent to the commands above.
Do not rely on a globally installed `local-code-indexer` while working in this repo.

## Verification

Run the full local verification command before opening a pull request:

```bash
.venv/bin/python -m pytest -q && .venv/bin/ruff check .
```

For narrow changes, it is fine to run a targeted pytest command first, but the full
verify command above is the bar for review.

## Embedding Backends

Embedding calls must stay local-only. The default backend is Ollama on loopback, and
OpenAI-compatible local servers such as LM Studio are supported only through loopback
URLs like `127.0.0.1`, `localhost`, or `::1`.

Do not add hosted embedding services, non-loopback defaults, broader network access, or
fallbacks that silently leave the machine. The backend decision and rationale are
documented in [ADR 0001](docs/decisions/0001-embedding-backend-ollama.md).

## Pull Requests

- Branch from `next` unless the maintainer says a stack should use a different base.
- Keep changes focused on one behavior, docs slice, or packaging slice.
- Preserve existing JSON and MCP payloads unless the PR is explicitly about a machine
  contract change.
- Add or update tests for behavior changes and include documentation updates when user
  commands, setup, architecture, or public behavior changes.
- Mention the verification command you ran and whether embeddings were enabled,
  disabled, or faked during testing.
- Do not commit local editor files, virtual environments, databases, or secrets.
