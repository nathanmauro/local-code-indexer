# local-code-indexer

Fully local code indexing and MCP retrieval for private repositories.

This project is a local replacement path for hosted code-index retrieval. It stores index state in
SQLite, uses FTS5 for lexical search, uses `sqlite-vec` when available for vector search, and only
calls local embedding services such as Ollama on `127.0.0.1` or `localhost`.

## CLI

```bash
local-code-indexer init
local-code-indexer index <repo_path> [--name NAME]
local-code-indexer watch <repo_path> [--name NAME] [--interval SECONDS]
local-code-indexer search <query> [--repo NAME] [--limit N] [--mode hybrid|lexical|vector] [--path GLOB] [--lang LANG] [--kind KIND]
local-code-indexer status [--repo NAME]
local-code-indexer list-repos
local-code-indexer reindex-all
local-code-indexer remove <name>
local-code-indexer mcp-config --client codex|claude
local-code-indexer mcp
```

Repos are identified by their resolved directory path. The default name is the directory
basename; indexing a second directory whose basename collides with an existing repo fails with
an error asking for an explicit `--name`. Re-indexing the same directory with a new `--name`
renames the repo in place. `remove <name>` deletes a repo and all of its indexed data.
`reindex-all` refreshes every registered repo and skips stored paths that no longer exist.

`watch` polls and re-indexes on an interval; a failed pass logs to stderr and keeps polling.
Indexing is incremental: files with an unchanged content hash are skipped when their existing
embeddings still match the current vector dimension and stored model/backend identity. The index
run reports `unchanged_files`, `skipped_files` (unreadable or non-UTF-8 files),
`embedded_chunks`, and `embedding_failures` so a dead embedding service is visible rather than
silent. If five consecutive embedding batches fail during one run, a circuit breaker stops calling
the embedder for the remainder of that run; remaining files are still indexed for
lexical/path/symbol search with empty embeddings, breaker-skipped chunks are not counted as
`embedding_failures`, and the result includes
`degraded: true`.

The default database path is `~/.local/share/local-code-indexer/index.db`. Override it with
`LOCAL_CODE_INDEXER_DB_PATH=/path/to/index.db`.

Embeddings default to Ollama at `http://127.0.0.1:11434` with `nomic-embed-text`. Override the
backend with `LOCAL_CODE_INDEXER_EMBED_URL` (base URL), `LOCAL_CODE_INDEXER_EMBED_MODEL` (model
name), and `LOCAL_CODE_INDEXER_EMBED_API` (`ollama`, the default, or `openai` for any
OpenAI-compatible local server such as LM Studio or llama.cpp's llama-server, which is called via
`/v1/embeddings`). The embedding URL must point to a loopback host (`127.0.0.1`, `localhost`, or
`::1`) regardless of backend. Set `LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS=1` for
lexical/path/symbol-only indexing and search. `status` reports `degraded: true` when embeddings are
enabled but stored coverage is incomplete (`embedded_chunks < chunks`); disabled embeddings always
report `degraded: false`.

## MCP Tools

- `code_index_search(query, repo?, mode?, limit?, path?, lang?, kind?)`
- `code_index_list_files(repo?, glob?, limit?, lang?)`
- `code_index_list_repos()`
- `code_index_read_file(repo, path, start_line?, end_line?)`
- `code_index_symbols(repo?, query?, path?, limit?, lang?, kind?)`
- `code_index_status(repo?)`

Print client config snippets without editing live MCP config:

```bash
local-code-indexer mcp-config --client codex
local-code-indexer mcp-config --client claude
```

## Retrieval

Search blends BM25/FTS5, local vector similarity when embeddings are present, path matches, and
symbol matches. Results include repo, path, line range, score reason, chunk id, file hash, symbols,
and snippet text.

Files are chunked by line windows that snap to tree-sitter definition boundaries: when a window
would cut a function or class in half, the chunk breaks before it so the next chunk starts at the
definition. Symbols come from the same tree-sitter parse, with a captured kind (`class`,
`function`, or `method`) and a regex fallback for languages the parser pack does not cover.

The indexer loads `sqlite-vec` when the Python package and SQLite extension are available, and
queries it with a proper vec0 KNN (`k = ?`) constraint. It also stores embedding JSON as a local
fallback so search remains usable if the extension cannot load. Changing the embedding backend,
model name, or dimension is handled on the next index run by rebuilding vectors.

## Ignore rules

`.gitignore`, `.augmentignore`, and `.indexignore` are honored at every directory level, with
nested patterns scoped to their directory (gitignore semantics). Hard-skipped regardless of
ignore files: symlinks, dependency/build/cache directories (`node_modules`, `.venv`, `dist`,
`.cache`, ...), lockfiles (`uv.lock`, `package-lock.json`, ...), secret-shaped files (`.env*`,
key/cert suffixes, `id_rsa`-style names, `.netrc`, ...), binaries, and files over 1 MB.
