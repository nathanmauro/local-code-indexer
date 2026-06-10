# ADR 0001: Embedding backend — Ollama by default, OpenAI-compatible seam later

Date: 2026-06-10 · Status: accepted

## Context

Embeddings come from a localhost-only service (hard constraint: no hosted APIs). The
candidates were Ollama (`/api/embed`, nomic-embed-text F16, 768-dim) and LM Studio
(`/v1/embeddings` OpenAI-compatible, nomic v1.5 Q4_K_M, 768-dim). Both were installed,
running, and benchmarked live on the development machine with 200 short code chunks:

| Path | Ollama | LM Studio |
|---|---|---|
| Per-chunk loop (current `LocalEmbedder` usage) | 50 chunks/s | 123 chunks/s |
| One batched request | 178 chunks/s | 213 chunks/s |

## Decision

Stay on **Ollama** as the default backend. Plan a follow-up that adds batching
(`embed_batch()`) and env-configurable backend selection
(`LOCAL_CODE_INDEXER_EMBED_URL` / `_MODEL` / `_API={ollama|openai}`) so any
OpenAI-compatible local server becomes a configuration swap, not a code change.

## Rationale, ranked for this use case (unattended background indexing daemon)

1. **Daemon fit (decisive).** Ollama runs as a launchd daemon with no GUI dependency.
   LM Studio's server runs as a child of the desktop app by default; its headless mode
   (`llmster`) exists but adds setup and a moving part.
2. **Licensing.** Ollama is MIT. LM Studio is free for work use but proprietary.
3. **Throughput.** LM Studio's ~2.5× per-chunk advantage is real but mis-targeted:
   batching on Ollama (178/s) already beats LM Studio per-chunk (123/s). The per-chunk
   loop is the bottleneck, not the runtime.

## Consequences

- Reindex throughput work goes into batching, not a backend migration.
- The two runtimes ship different quantizations of nomic (F16 vs Q4_K_M); vectors are
  not comparable across backends, so any future backend swap requires a full reindex
  (the existing dimension-change rebuild handles the mechanics when dims differ).
- `LocalEmbedder` keeps enforcing loopback-only URLs regardless of backend.
