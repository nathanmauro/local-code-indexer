"""SQLite-backed code indexing service."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import math
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import config
from .chunking import CodeChunk, chunk_file_text, extract_symbol_definitions, split_lines
from .embeddings import LocalEmbedder
from .ignore import IgnoreMatcher
from .scanner import iter_indexable_files

try:
    import sqlite_vec
except Exception:  # pragma: no cover - exercised when dependency is absent
    sqlite_vec = None

TOKEN_RE = re.compile(r"[A-Za-z_][\w$./-]*")

EMBED_BATCH_SIZE = 64
EMBED_BREAKER_CONSECUTIVE_FAILURES = 5


@dataclass(frozen=True)
class _EmbedChunksResult:
    vectors: list[list[float] | None]
    attempted: list[bool]
    consecutive_failed_batches: int
    breaker_tripped: bool


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tokenize(query: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(query) if len(token) > 1]


def _fts_query(query: str) -> str:
    terms = []
    for token in _tokenize(query):
        clean = re.sub(r"[^A-Za-z0-9_]", " ", token).strip()
        if clean:
            terms.append(f'"{clean}"')
    return " OR ".join(terms[:12])


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(left * right for left, right in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(value * value for value in a))
    mag_b = math.sqrt(sum(value * value for value in b))
    if not mag_a or not mag_b:
        return 0.0
    return dot / (mag_a * mag_b)


def _snippet(content: str, max_chars: int = 500) -> str:
    text = content.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def _path_language(path: str) -> str:
    return Path(path).suffix.lstrip(".")


def _normalize_lang_filter(lang: str | None) -> str | None:
    if lang is None or lang == "":
        return None
    return lang.lstrip(".").lower()


def _normalize_kind_filter(kind: str | None) -> str | None:
    if kind is None:
        return None
    normalized = kind.strip().lower()
    return normalized or None


class IndexService:
    def __init__(self, db_path: Path, embedder=None):
        self.db_path = Path(db_path)
        if embedder is None and not config.embeddings_disabled():
            embedder = LocalEmbedder()
        self.embedder = embedder
        self._sqlite_vec_loaded = False
        self.last_vector_backend: str | None = None
        self.last_vector_skip_reason: str | None = None

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        self._sqlite_vec_loaded = self._load_sqlite_vec(conn)
        return conn

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _load_sqlite_vec(self, conn: sqlite3.Connection) -> bool:
        if sqlite_vec is None:
            return False
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            return True
        except Exception:
            try:
                conn.enable_load_extension(False)
            except Exception:
                pass
            return False

    def init(self) -> None:
        with self._session() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS repos (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY,
                    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    abs_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    language TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    indexed_at TEXT NOT NULL,
                    UNIQUE(repo_id, path)
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    symbols TEXT NOT NULL DEFAULT '[]',
                    file_hash TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    embedding_json TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS symbols (
                    id INTEGER PRIMARY KEY,
                    repo_id INTEGER NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                    file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                    chunk_id TEXT REFERENCES chunks(id) ON DELETE CASCADE,
                    symbol TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT '',
                    path TEXT NOT NULL,
                    line INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunk_vector_map (
                    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                    chunk_id TEXT NOT NULL UNIQUE REFERENCES chunks(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_files_repo_path ON files(repo_id, path);
                CREATE INDEX IF NOT EXISTS idx_chunks_repo_path ON chunks(repo_id, path);
                CREATE INDEX IF NOT EXISTS idx_symbols_repo_symbol ON symbols(repo_id, symbol);

                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    repo UNINDEXED,
                    path,
                    symbols,
                    content
                );
                """
            )
            self._ensure_symbols_kind_column(conn)
            conn.commit()

    def _ensure_symbols_kind_column(self, conn: sqlite3.Connection) -> None:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(symbols)")}
        if "kind" not in columns:
            conn.execute("ALTER TABLE symbols ADD COLUMN kind TEXT NOT NULL DEFAULT ''")

    def index_repo(self, repo_path: Path, name: str | None = None) -> dict:
        self.init()
        repo_path = Path(repo_path).resolve()
        if not repo_path.is_dir():
            raise ValueError(f"repo path is not a directory: {repo_path}")
        now = _utc_now()
        matcher = IgnoreMatcher(repo_path)
        seen_paths: set[str] = set()
        indexed_files = 0
        indexed_chunks = 0
        skipped_files = 0
        unchanged_files = 0
        embedded_chunks = 0
        embedding_failures = 0
        consecutive_failed_embed_batches = 0
        degraded = False

        conn = self._connect()
        try:
            repo_id, repo_name = self._resolve_repo(conn, name, repo_path, now)
            conn.commit()
            run_start_vector_dim = self._vector_dim(conn)
            run_start_embed_model = self._embed_model(conn)
            run_start_embed_backend = self._embed_backend(conn)
            embedder_dim = self._embedder_dim()
            embedder_model = self._embedder_model()
            embedder_backend = self._embedder_backend()
            for file_path in iter_indexable_files(repo_path, matcher):
                rel_path = file_path.relative_to(repo_path).as_posix()
                # Keep the previously indexed version if this file can't be read now.
                seen_paths.add(rel_path)
                try:
                    stat = file_path.stat()
                    data = file_path.read_bytes()
                    text = data.decode("utf-8")
                except (OSError, UnicodeDecodeError):
                    skipped_files += 1
                    continue
                file_hash = _sha256_bytes(data)
                existing_file = self._existing_file(conn, repo_id, rel_path)
                # Dimension or model changes force re-embedding even when file hashes match.
                if existing_file is not None and self._can_skip_unchanged_file(
                    conn,
                    existing_file,
                    file_hash,
                    text,
                    run_start_vector_dim,
                    embedder_dim,
                    run_start_embed_model,
                    embedder_model,
                    run_start_embed_backend,
                    embedder_backend,
                ):
                    unchanged_files += 1
                    continue
                chunks = chunk_file_text(repo_name, rel_path, text)
                # Embedding calls run between per-file commits, outside any write
                # transaction, so the SQLite write lock is never held across HTTP.
                embeddings: dict[str, list[float] | None] = {}
                if degraded:
                    embed_result = _EmbedChunksResult(
                        vectors=[None] * len(chunks),
                        attempted=[False] * len(chunks),
                        consecutive_failed_batches=consecutive_failed_embed_batches,
                        breaker_tripped=True,
                    )
                else:
                    embed_result = self._embed_chunks_for_run(
                        [chunk.content for chunk in chunks],
                        consecutive_failed_batches=consecutive_failed_embed_batches,
                    )
                    consecutive_failed_embed_batches = embed_result.consecutive_failed_batches
                    degraded = embed_result.breaker_tripped
                for chunk, embedding, attempted in zip(
                    chunks, embed_result.vectors, embed_result.attempted, strict=True
                ):
                    embeddings[chunk.id] = embedding
                    if embedding:
                        embedded_chunks += 1
                    elif attempted:
                        embedding_failures += 1
                file_id = self._upsert_file(
                    conn,
                    repo_id,
                    rel_path,
                    file_path,
                    file_hash,
                    len(data),
                    stat.st_mtime,
                    text,
                    now,
                )
                self._delete_chunks_for_file(conn, file_id)
                for chunk in chunks:
                    self._insert_chunk(
                        conn, repo_id, repo_name, file_id, chunk, file_hash, embeddings[chunk.id], now
                    )
                self._insert_symbols(conn, repo_id, file_id, rel_path, text, chunks)
                conn.commit()
                indexed_files += 1
                indexed_chunks += len(chunks)

            deleted_files = self._delete_missing_files(conn, repo_id, seen_paths)
            if embedder_model is not None:
                self._set_embed_model(conn, embedder_model)
            if embedder_backend is not None:
                self._set_embed_backend(conn, embedder_backend)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

        return {
            "repo": repo_name,
            "path": str(repo_path),
            "indexed_files": indexed_files,
            "indexed_chunks": indexed_chunks,
            "skipped_files": skipped_files,
            "unchanged_files": unchanged_files,
            "deleted_files": deleted_files,
            "embedded_chunks": embedded_chunks,
            "embedding_failures": embedding_failures,
            "degraded": degraded,
            "db_path": str(self.db_path),
        }

    def reindex_all(self) -> dict:
        self.init()
        with self._session() as conn:
            rows = conn.execute(
                """
                SELECT r.name, r.path
                FROM repos r
                ORDER BY r.name
                """
            ).fetchall()

        repos = []
        reindexed = 0
        for row in rows:
            repo_name = row["name"]
            repo_path = Path(row["path"])
            try:
                result = self.index_repo(repo_path, name=repo_name)
            except ValueError:
                if repo_path.is_dir():
                    raise
                repos.append(
                    {
                        "repo": repo_name,
                        "path": row["path"],
                        "skipped": True,
                        "error": "path missing",
                    }
                )
                continue
            repos.append(result)
            reindexed += 1

        return {
            "reindexed": reindexed,
            "repos": repos,
            "db_path": str(self.db_path),
        }

    def _resolve_repo(
        self, conn: sqlite3.Connection, name: str | None, path: Path, now: str
    ) -> tuple[int, str]:
        """Resolve the repo row by path first so a basename collision or rename can
        never hijack another directory's index."""
        requested = name or path.name
        by_path = conn.execute(
            "SELECT id, name FROM repos WHERE path = ?", (str(path),)
        ).fetchone()
        by_name = conn.execute(
            "SELECT id, path FROM repos WHERE name = ?", (requested,)
        ).fetchone()

        if by_path is not None:
            repo_id = int(by_path["id"])
            if name is None or by_path["name"] == requested:
                conn.execute("UPDATE repos SET updated_at = ? WHERE id = ?", (now, repo_id))
                return repo_id, by_path["name"]
            if by_name is not None and int(by_name["id"]) != repo_id:
                raise ValueError(
                    f"repo name '{requested}' already refers to {by_name['path']}"
                )
            conn.execute(
                "UPDATE repos SET name = ?, updated_at = ? WHERE id = ?",
                (requested, now, repo_id),
            )
            return repo_id, requested

        if by_name is not None:
            raise ValueError(
                f"repo name '{requested}' already refers to {by_name['path']}; "
                "pass a different --name for this directory"
            )
        cursor = conn.execute(
            "INSERT INTO repos (name, path, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (requested, str(path), now, now),
        )
        return int(cursor.lastrowid), requested

    def _upsert_file(
        self,
        conn: sqlite3.Connection,
        repo_id: int,
        rel_path: str,
        file_path: Path,
        file_hash: str,
        size: int,
        mtime: float,
        content: str,
        now: str,
    ) -> int:
        language = file_path.suffix.lstrip(".")
        conn.execute(
            """
            INSERT INTO files (
                repo_id, path, abs_path, file_hash, size, mtime, language, content, indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, path) DO UPDATE SET
                abs_path = excluded.abs_path,
                file_hash = excluded.file_hash,
                size = excluded.size,
                mtime = excluded.mtime,
                language = excluded.language,
                content = excluded.content,
                indexed_at = excluded.indexed_at
            """,
            (repo_id, rel_path, str(file_path), file_hash, size, mtime, language, content, now),
        )
        row = conn.execute(
            "SELECT id FROM files WHERE repo_id = ? AND path = ?",
            (repo_id, rel_path),
        ).fetchone()
        return int(row["id"])

    def _existing_file(
        self, conn: sqlite3.Connection, repo_id: int, rel_path: str
    ) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT id, file_hash FROM files WHERE repo_id = ? AND path = ?",
            (repo_id, rel_path),
        ).fetchone()

    def _can_skip_unchanged_file(
        self,
        conn: sqlite3.Connection,
        existing_file: sqlite3.Row,
        file_hash: str,
        text: str,
        run_start_vector_dim: int | None,
        embedder_dim: int | None,
        run_start_embed_model: str | None,
        embedder_model: str | None,
        run_start_embed_backend: str | None,
        embedder_backend: str | None,
    ) -> bool:
        if existing_file["file_hash"] != file_hash:
            return False
        chunk_rows = conn.execute(
            "SELECT embedding_json FROM chunks WHERE file_id = ?",
            (int(existing_file["id"]),),
        ).fetchall()
        if not chunk_rows:
            return text == ""
        if self.embedder is None:
            return True
        chunk_dims = [self._embedding_json_dim(row["embedding_json"]) for row in chunk_rows]
        if self._embed_model_changed(run_start_embed_model, embedder_model):
            return False
        if self._embed_backend_changed(run_start_embed_backend, embedder_backend):
            return False
        if run_start_vector_dim is not None and embedder_dim is not None:
            if run_start_vector_dim != embedder_dim:
                return False
        effective_dim = embedder_dim
        if effective_dim is None:
            effective_dim = run_start_vector_dim
        if effective_dim is None:
            stored_dims = set(chunk_dims)
            if None in stored_dims or len(stored_dims) != 1:
                return False
            effective_dim = stored_dims.pop()
        if (
            effective_dim is None
            or any(chunk_dim != effective_dim for chunk_dim in chunk_dims)
        ):
            return False
        return True

    def _embedder_dim(self) -> int | None:
        if self.embedder is None:
            return None
        dim = getattr(self.embedder, "dim", None)
        if callable(dim):
            dim = dim()
        if dim is None:
            return None
        try:
            return int(dim)
        except (TypeError, ValueError):
            return None

    def _embedder_model(self) -> str | None:
        if self.embedder is None:
            return None
        model = getattr(self.embedder, "model", None)
        if model is None:
            return None
        model_name = str(model).strip()
        return model_name or None

    def _embedder_backend(self) -> str | None:
        model = self._embedder_model()
        if model is None:
            return None
        api = getattr(self.embedder, "api", None)
        base_url = getattr(self.embedder, "base_url", None)
        if api is None and base_url is None:
            return model
        return json.dumps(
            {"api": str(api or ""), "base_url": str(base_url or ""), "model": model},
            sort_keys=True,
        )

    def _embed_model_changed(self, stored_model: str | None, current_model: str | None) -> bool:
        return stored_model is not None and current_model is not None and stored_model != current_model

    def _embed_backend_changed(self, stored_backend: str | None, current_backend: str | None) -> bool:
        return current_backend is not None and stored_backend != current_backend

    def _embedding_json_dim(self, embedding_json: str) -> int | None:
        if not embedding_json:
            return None
        try:
            embedding = json.loads(embedding_json)
        except json.JSONDecodeError:
            return None
        if not isinstance(embedding, list):
            return None
        return len(embedding)

    def _delete_chunks_for_file(self, conn: sqlite3.Connection, file_id: int) -> None:
        chunk_ids = [
            row["id"] for row in conn.execute("SELECT id FROM chunks WHERE file_id = ?", (file_id,))
        ]
        for chunk_id in chunk_ids:
            conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
            self._delete_vector(conn, chunk_id)
        conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
        conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))

    def _delete_missing_files(self, conn: sqlite3.Connection, repo_id: int, seen_paths: set[str]) -> int:
        rows = conn.execute("SELECT id, path FROM files WHERE repo_id = ?", (repo_id,)).fetchall()
        deleted = 0
        for row in rows:
            if row["path"] not in seen_paths:
                self._delete_chunks_for_file(conn, int(row["id"]))
                conn.execute("DELETE FROM files WHERE id = ?", (row["id"],))
                deleted += 1
        return deleted

    def _insert_chunk(
        self,
        conn: sqlite3.Connection,
        repo_id: int,
        repo_name: str,
        file_id: int,
        chunk: CodeChunk,
        file_hash: str,
        embedding: list[float] | None,
        now: str,
    ) -> None:
        content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
        embedding_json = json.dumps(embedding) if embedding else ""
        conn.execute(
            """
            INSERT INTO chunks (
                id, repo_id, file_id, path, start_line, end_line, content, symbols,
                file_hash, content_hash, embedding_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk.id,
                repo_id,
                file_id,
                chunk.path,
                chunk.start_line,
                chunk.end_line,
                chunk.content,
                json.dumps(chunk.symbols),
                file_hash,
                content_hash,
                embedding_json,
                now,
            ),
        )
        conn.execute(
            "INSERT INTO chunks_fts (chunk_id, repo, path, symbols, content) VALUES (?, ?, ?, ?, ?)",
            (chunk.id, repo_name, chunk.path, " ".join(chunk.symbols), chunk.content),
        )
        if embedding:
            self._upsert_vector(conn, chunk.id, embedding)

    def _insert_symbols(
        self,
        conn: sqlite3.Connection,
        repo_id: int,
        file_id: int,
        path: str,
        text: str,
        chunks: list[CodeChunk],
    ) -> None:
        for symbol, line, kind in dict.fromkeys(extract_symbol_definitions(path, text)):
            chunk_id = next(
                (chunk.id for chunk in chunks if chunk.start_line <= line <= chunk.end_line),
                chunks[0].id if chunks else None,
            )
            conn.execute(
                "INSERT INTO symbols (repo_id, file_id, chunk_id, symbol, kind, path, line) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (repo_id, file_id, chunk_id, symbol, kind, path, line),
            )

    def _embed_chunks(self, contents: list[str]) -> list[list[float] | None]:
        return self._embed_chunks_for_run(contents).vectors

    def _embed_chunks_for_run(
        self,
        contents: list[str],
        consecutive_failed_batches: int = 0,
    ) -> _EmbedChunksResult:
        if self.embedder is None or not contents:
            return _EmbedChunksResult(
                vectors=[None] * len(contents),
                attempted=[False] * len(contents),
                consecutive_failed_batches=consecutive_failed_batches,
                breaker_tripped=False,
            )
        embed_batch = getattr(self.embedder, "embed_batch", None)
        if embed_batch is None:
            return self._embed_chunks_individually(contents, consecutive_failed_batches)
        results: list[list[float] | None] = []
        attempted: list[bool] = []
        breaker_tripped = False
        for start in range(0, len(contents), EMBED_BATCH_SIZE):
            batch = contents[start : start + EMBED_BATCH_SIZE]
            if consecutive_failed_batches >= EMBED_BREAKER_CONSECUTIVE_FAILURES:
                results.extend([None] * len(batch))
                attempted.extend([False] * len(batch))
                breaker_tripped = True
                continue
            try:
                vectors = embed_batch(batch)
                if len(vectors) != len(batch):
                    raise RuntimeError("embed_batch returned a mismatched number of vectors")
            except Exception:
                vectors = [None] * len(batch)
            results.extend(
                [float(value) for value in vector] if vector else None for vector in vectors
            )
            attempted.extend([True] * len(batch))
            if all(vector is None for vector in results[-len(batch) :]):
                consecutive_failed_batches += 1
                breaker_tripped = (
                    consecutive_failed_batches >= EMBED_BREAKER_CONSECUTIVE_FAILURES
                )
            else:
                consecutive_failed_batches = 0
        return _EmbedChunksResult(
            vectors=results,
            attempted=attempted,
            consecutive_failed_batches=consecutive_failed_batches,
            breaker_tripped=breaker_tripped,
        )

    def _embed_chunks_individually(
        self,
        contents: list[str],
        consecutive_failed_batches: int,
    ) -> _EmbedChunksResult:
        results: list[list[float] | None] = []
        attempted: list[bool] = []
        breaker_tripped = False
        for content in contents:
            if consecutive_failed_batches >= EMBED_BREAKER_CONSECUTIVE_FAILURES:
                results.append(None)
                attempted.append(False)
                breaker_tripped = True
                continue
            embedding = self._embed_chunk(content)
            if not embedding:
                embedding = None
            results.append(embedding)
            attempted.append(True)
            if embedding is None:
                consecutive_failed_batches += 1
                breaker_tripped = (
                    consecutive_failed_batches >= EMBED_BREAKER_CONSECUTIVE_FAILURES
                )
            else:
                consecutive_failed_batches = 0
        return _EmbedChunksResult(
            vectors=results,
            attempted=attempted,
            consecutive_failed_batches=consecutive_failed_batches,
            breaker_tripped=breaker_tripped,
        )

    def _embed_chunk(self, content: str) -> list[float] | None:
        if self.embedder is None:
            return None
        try:
            return [float(value) for value in self.embedder.embed(content)]
        except Exception:
            return None

    def _embed_query(self, query: str) -> list[float] | None:
        if self.embedder is None:
            return None
        try:
            return [float(value) for value in self.embedder.embed(query)]
        except Exception:
            return None

    def _vector_dim(self, conn: sqlite3.Connection) -> int | None:
        row = conn.execute("SELECT value FROM settings WHERE key = 'vector_dim'").fetchone()
        return int(row["value"]) if row else None

    def _set_vector_dim(self, conn: sqlite3.Connection, dim: int) -> None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('vector_dim', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(dim),),
        )

    def _embed_model(self, conn: sqlite3.Connection) -> str | None:
        row = conn.execute("SELECT value FROM settings WHERE key = 'embed_model'").fetchone()
        if row is None:
            return None
        value = str(row["value"]).strip()
        return value or None

    def _set_embed_model(self, conn: sqlite3.Connection, model: str) -> None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('embed_model', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (model,),
        )

    def _embed_backend(self, conn: sqlite3.Connection) -> str | None:
        row = conn.execute("SELECT value FROM settings WHERE key = 'embed_backend'").fetchone()
        if row is None:
            return None
        value = str(row["value"]).strip()
        return value or None

    def _set_embed_backend(self, conn: sqlite3.Connection, backend: str) -> None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('embed_backend', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (backend,),
        )

    def _ensure_vector_table_for_write(self, conn: sqlite3.Connection, dim: int) -> bool:
        if not self._sqlite_vec_loaded or dim <= 0:
            return False
        existing_dim = self._vector_dim(conn)
        if existing_dim is not None and existing_dim != dim:
            # The embedding dimension changed; drop old vectors and let the
            # in-progress reindex repopulate comparable rows.
            conn.execute("DROP TABLE IF EXISTS chunk_vectors")
            conn.execute("DELETE FROM chunk_vector_map")
            existing_dim = None
        conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0(embedding float[{dim}])")
        if existing_dim is None:
            self._set_vector_dim(conn, dim)
        return True

    def _vector_table_readable(self, conn: sqlite3.Connection, dim: int) -> bool:
        return self._sqlite_vec_loaded and dim > 0 and self._vector_dim(conn) == dim

    def _upsert_vector(self, conn: sqlite3.Connection, chunk_id: str, embedding: list[float]) -> None:
        if not self._ensure_vector_table_for_write(conn, len(embedding)):
            return
        row = conn.execute(
            "SELECT rowid FROM chunk_vector_map WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if row is None:
            cursor = conn.execute("INSERT INTO chunk_vector_map (chunk_id) VALUES (?)", (chunk_id,))
            rowid = int(cursor.lastrowid)
        else:
            rowid = int(row["rowid"])
            conn.execute("DELETE FROM chunk_vectors WHERE rowid = ?", (rowid,))
        conn.execute(
            "INSERT INTO chunk_vectors (rowid, embedding) VALUES (?, ?)",
            (rowid, sqlite_vec.serialize_float32(embedding)),
        )

    def _delete_vector(self, conn: sqlite3.Connection, chunk_id: str) -> None:
        row = conn.execute(
            "SELECT rowid FROM chunk_vector_map WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if row is not None:
            try:
                conn.execute("DELETE FROM chunk_vectors WHERE rowid = ?", (row["rowid"],))
            except sqlite3.OperationalError:
                pass
            conn.execute("DELETE FROM chunk_vector_map WHERE chunk_id = ?", (chunk_id,))

    def search(
        self,
        query: str,
        repo: str | None = None,
        limit: int = 10,
        mode: str = "hybrid",
        path: str | None = None,
        lang: str | None = None,
        kind: str | None = None,
    ) -> list[dict]:
        self.init()
        with self._session() as conn:
            if repo:
                self._require_known_repo(conn, repo)
            if not query or not query.strip():
                return []
            limit = max(1, min(int(limit), 100))
            mode = mode or "hybrid"
            kind_filter = _normalize_kind_filter(kind)
            kind_sql, kind_params = self._kind_chunk_filter(kind_filter)
            self.last_vector_backend = None
            self.last_vector_skip_reason = None
            repo_filter, repo_params = self._repo_filter(repo)
            candidates: dict[str, dict[str, Any]] = {}
            if mode in {"hybrid", "lexical"}:
                self._add_fts_candidates(
                    conn,
                    candidates,
                    query,
                    repo_filter,
                    repo_params,
                    kind_sql,
                    kind_params,
                )
            if mode in {"hybrid", "vector"}:
                if self.embedder is None:
                    self.last_vector_skip_reason = "embeddings-disabled"
                else:
                    query_embedding = self._embed_query(query)
                    if query_embedding is None:
                        self.last_vector_skip_reason = "query-embedding-failed"
                    elif self._embedded_chunk_count(conn, repo_filter, repo_params) == 0:
                        self.last_vector_skip_reason = "no-embedded-chunks"
                    elif query_embedding:
                        self.last_vector_backend = self._add_vector_candidates(
                            conn,
                            candidates,
                            query_embedding,
                            repo_filter,
                            repo_params,
                            limit,
                            kind_sql,
                            kind_params,
                        )
                    else:
                        self.last_vector_skip_reason = "query-embedding-failed"
            self._add_path_symbol_scores(
                conn,
                candidates,
                query,
                repo_filter,
                repo_params,
                kind_sql,
                kind_params,
            )
            rows = list(candidates.values())
            if path:
                rows = [item for item in rows if fnmatch.fnmatch(item["path"], path)]
            lang_filter = _normalize_lang_filter(lang)
            if lang_filter is not None:
                rows = [item for item in rows if _path_language(item["path"]).lower() == lang_filter]
            rows = sorted(rows, key=lambda item: item["score"], reverse=True)[:limit]
            return [self._format_search_result(row) for row in rows]

    def _embedded_chunk_count(
        self,
        conn: sqlite3.Connection,
        repo_filter: str,
        repo_params: list[Any],
    ) -> int:
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM chunks c
            JOIN repos r ON c.repo_id = r.id
            WHERE c.embedding_json != ''{repo_filter}
            """,
            repo_params,
        ).fetchone()
        return int(row["count"])

    def _repo_filter(self, repo: str | None) -> tuple[str, list[Any]]:
        if repo:
            return " AND r.name = ?", [repo]
        return "", []

    def _require_known_repo(self, conn: sqlite3.Connection, repo: str | None) -> None:
        if not repo:
            return
        repos = [row["name"] for row in conn.execute("SELECT name FROM repos ORDER BY name")]
        if repo not in repos:
            available = ", ".join(repos) or "(none)"
            raise ValueError(f"unknown repo: {repo}. indexed repos: {available}")

    def _kind_chunk_filter(self, kind_filter: str | None) -> tuple[str, list[Any]]:
        if kind_filter is None:
            return "", []
        return (
            """
             AND EXISTS (
                SELECT 1
                FROM symbols kind_symbols
                WHERE kind_symbols.chunk_id = c.id
                  AND lower(kind_symbols.kind) = ?
             )
            """,
            [kind_filter],
        )

    def _repo_summaries(
        self,
        conn: sqlite3.Connection,
        repo_filter: str = "",
        repo_params: list[Any] | None = None,
        *,
        include_updated_at: bool = False,
    ) -> list[dict]:
        rows = conn.execute(
            f"""
            SELECT r.name, r.path, r.updated_at
            FROM repos r
            WHERE 1=1{repo_filter}
            ORDER BY r.name
            """,
            repo_params or [],
        ).fetchall()
        summaries = []
        for row in rows:
            count_params = (row["name"],)
            files = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM files f
                JOIN repos r ON f.repo_id = r.id
                WHERE r.name = ?
                """,
                count_params,
            ).fetchone()["count"]
            chunks = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM chunks c
                JOIN repos r ON c.repo_id = r.id
                WHERE r.name = ?
                """,
                count_params,
            ).fetchone()["count"]
            embedded_chunks = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM chunks c
                JOIN repos r ON c.repo_id = r.id
                WHERE c.embedding_json != '' AND r.name = ?
                """,
                count_params,
            ).fetchone()["count"]
            summary = {
                "name": row["name"],
                "path": row["path"],
                "files": int(files),
                "chunks": int(chunks),
                "embedded_chunks": int(embedded_chunks),
            }
            if include_updated_at:
                summary["updated_at"] = row["updated_at"]
            summaries.append(summary)
        return summaries

    def _base_candidate_sql(self, where: str = "") -> str:
        return f"""
            SELECT
                c.id AS chunk_id,
                r.name AS repo,
                c.path,
                c.start_line,
                c.end_line,
                c.content,
                c.symbols,
                c.file_hash,
                c.embedding_json
            FROM chunks c
            JOIN repos r ON c.repo_id = r.id
            {where}
        """

    def _row_candidate(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "chunk_id": row["chunk_id"],
            "repo": row["repo"],
            "path": row["path"],
            "start_line": int(row["start_line"]),
            "end_line": int(row["end_line"]),
            "content": row["content"],
            "symbols": json.loads(row["symbols"] or "[]"),
            "file_hash": row["file_hash"],
            "embedding_json": row["embedding_json"],
            "score": 0.0,
            "reasons": [],
        }

    def _candidate(self, candidates: dict[str, dict[str, Any]], row: sqlite3.Row) -> dict[str, Any]:
        chunk_id = row["chunk_id"]
        if chunk_id not in candidates:
            candidates[chunk_id] = self._row_candidate(row)
        return candidates[chunk_id]

    def _add_fts_candidates(
        self,
        conn: sqlite3.Connection,
        candidates: dict[str, dict[str, Any]],
        query: str,
        repo_filter: str,
        repo_params: list[Any],
        kind_sql: str,
        kind_params: list[Any],
    ) -> None:
        fts_query = _fts_query(query)
        if not fts_query:
            return
        rows = conn.execute(
            f"""
            SELECT
                c.id AS chunk_id,
                r.name AS repo,
                c.path,
                c.start_line,
                c.end_line,
                c.content,
                c.symbols,
                c.file_hash,
                c.embedding_json,
                bm25(chunks_fts) AS bm25_score
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.chunk_id
            JOIN repos r ON c.repo_id = r.id
            WHERE chunks_fts MATCH ?{repo_filter}{kind_sql}
            ORDER BY bm25_score
            LIMIT 100
            """,
            [fts_query, *repo_params, *kind_params],
        ).fetchall()
        for idx, row in enumerate(rows):
            candidate = self._candidate(candidates, row)
            candidate["score"] += max(0.2, 4.0 - (idx * 0.03))
            candidate["reasons"].append("bm25")

    def _add_vector_candidates(
        self,
        conn: sqlite3.Connection,
        candidates: dict[str, dict[str, Any]],
        query_embedding: list[float],
        repo_filter: str,
        repo_params: list[Any],
        limit: int,
        kind_sql: str,
        kind_params: list[Any],
    ) -> str:
        if self._vector_table_readable(conn, len(query_embedding)):
            # vec0 KNN requires an explicit k constraint inside the virtual-table
            # query — an outer LIMIT is not pushed through the joins. Over-fetch
            # because the repo filter applies after the global top-k selection.
            k = min(500, max(100, limit * 20))
            try:
                rows = conn.execute(
                    f"""
                    SELECT
                        c.id AS chunk_id,
                        r.name AS repo,
                        c.path,
                        c.start_line,
                        c.end_line,
                        c.content,
                        c.symbols,
                        c.file_hash,
                        c.embedding_json,
                        v.distance
                    FROM (
                        SELECT rowid, distance
                        FROM chunk_vectors
                        WHERE embedding MATCH ? AND k = ?
                    ) v
                    JOIN chunk_vector_map m ON m.rowid = v.rowid
                    JOIN chunks c ON c.id = m.chunk_id
                    JOIN repos r ON c.repo_id = r.id
                    WHERE 1=1{repo_filter}{kind_sql}
                    ORDER BY v.distance
                    """,
                    [sqlite_vec.serialize_float32(query_embedding), k, *repo_params, *kind_params],
                ).fetchall()
                for row in rows:
                    candidate = self._candidate(candidates, row)
                    score = 3.0 / (1.0 + float(row["distance"]))
                    candidate["score"] += score
                    candidate["reasons"].append("vector")
                return "sqlite-vec"
            except sqlite3.OperationalError:
                pass

        rows = conn.execute(
            self._base_candidate_sql(f"WHERE c.embedding_json != ''{repo_filter}{kind_sql}"),
            [*repo_params, *kind_params],
        ).fetchall()
        for row in rows:
            embedding = json.loads(row["embedding_json"])
            similarity = _cosine(query_embedding, [float(value) for value in embedding])
            if similarity <= 0:
                continue
            candidate = self._candidate(candidates, row)
            candidate["score"] += similarity * 3.0
            candidate["reasons"].append("vector")
        return "json-fallback"

    def _add_path_symbol_scores(
        self,
        conn: sqlite3.Connection,
        candidates: dict[str, dict[str, Any]],
        query: str,
        repo_filter: str,
        repo_params: list[Any],
        kind_sql: str,
        kind_params: list[Any],
    ) -> None:
        query_lower = query.lower().strip()
        tokens = _tokenize(query)
        if not tokens and len(query_lower) < 3:
            return
        rows = conn.execute(
            self._base_candidate_sql(f"WHERE 1=1{repo_filter}{kind_sql}"),
            [*repo_params, *kind_params],
        ).fetchall()
        for row in rows:
            path_lower = row["path"].lower()
            symbols = json.loads(row["symbols"] or "[]")
            symbol_text = " ".join(symbols).lower()
            path_score = 0.0
            symbol_score = 0.0
            if len(query_lower) >= 3 and (path_lower in query_lower or query_lower in path_lower):
                path_score = 4.5
            elif any(token in path_lower for token in tokens):
                path_score = 1.5
            if symbol_text and any(token in symbol_text for token in tokens):
                symbol_score = 2.0
            if path_score or symbol_score:
                candidate = self._candidate(candidates, row)
                if path_score:
                    candidate["score"] += path_score
                    candidate["reasons"].append("path")
                if symbol_score:
                    candidate["score"] += symbol_score
                    candidate["reasons"].append("symbol")

    def _format_search_result(self, row: dict[str, Any]) -> dict:
        reasons = []
        for reason in row["reasons"]:
            if reason not in reasons:
                reasons.append(reason)
        return {
            "repo": row["repo"],
            "path": row["path"],
            "language": _path_language(row["path"]),
            "line_range": f"{row['start_line']}-{row['end_line']}",
            "start_line": row["start_line"],
            "end_line": row["end_line"],
            "score": round(float(row["score"]), 4),
            "score_reason": "+".join(reasons) if reasons else "unknown",
            "chunk_id": row["chunk_id"],
            "file_hash": row["file_hash"],
            "symbols": row["symbols"],
            "snippet": _snippet(row["content"]),
        }

    def list_files(
        self,
        repo: str | None = None,
        glob: str | None = None,
        limit: int = 50,
        lang: str | None = None,
    ) -> list[dict]:
        self.init()
        limit = max(1, min(int(limit), 500))
        lang_filter = _normalize_lang_filter(lang)
        with self._session() as conn:
            if repo:
                self._require_known_repo(conn, repo)
            repo_filter, repo_params = self._repo_filter(repo)
            rows = conn.execute(
                f"""
                SELECT r.name AS repo, f.path, f.file_hash, f.size, f.indexed_at
                FROM files f
                JOIN repos r ON f.repo_id = r.id
                WHERE 1=1{repo_filter}
                ORDER BY r.name, f.path
                """,
                repo_params,
            ).fetchall()
        results = [
            {
                "repo": row["repo"],
                "path": row["path"],
                "language": _path_language(row["path"]),
                "file_hash": row["file_hash"],
                "size": row["size"],
                "indexed_at": row["indexed_at"],
            }
            for row in rows
            if not glob or fnmatch.fnmatch(row["path"], glob)
            if lang_filter is None or _path_language(row["path"]).lower() == lang_filter
        ]
        return results[:limit]

    def list_languages(self) -> list[str]:
        self.init()
        with self._session() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT lower(language) AS language
                FROM files
                WHERE language != ''
                ORDER BY language
                """
            ).fetchall()
        return [row["language"] for row in rows]

    def list_kinds(self) -> list[str]:
        self.init()
        with self._session() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT lower(kind) AS kind
                FROM symbols
                WHERE kind != ''
                ORDER BY kind
                """
            ).fetchall()
        return [row["kind"] for row in rows]

    def list_repos(self) -> list[dict]:
        self.init()
        with self._session() as conn:
            return self._repo_summaries(conn, include_updated_at=True)

    def read_file(self, repo: str, path: str, start_line: int | None = None, end_line: int | None = None) -> dict:
        self.init()
        clean_path = Path(path).as_posix()
        if clean_path.startswith("../") or clean_path == "..":
            raise ValueError("path must be repo-relative")
        with self._session() as conn:
            self._require_known_repo(conn, repo)
            row = conn.execute(
                """
                SELECT r.name AS repo, f.path, f.content, f.file_hash
                FROM files f
                JOIN repos r ON f.repo_id = r.id
                WHERE r.name = ? AND f.path = ?
                """,
                (repo, clean_path),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(f"{repo}:{clean_path} is not indexed")
        lines = split_lines(row["content"])
        total = len(lines)
        start = max(1, int(start_line or 1))
        end = min(total, int(end_line or total))
        if end < start:
            content = ""
        else:
            content = "\n".join(lines[start - 1 : end])
        return {
            "repo": row["repo"],
            "path": row["path"],
            "start_line": start,
            "end_line": end,
            "content": content,
            "file_hash": row["file_hash"],
        }

    def symbols(
        self,
        repo: str | None = None,
        query: str | None = None,
        path: str | None = None,
        limit: int = 50,
        lang: str | None = None,
        kind: str | None = None,
    ) -> list[dict]:
        self.init()
        limit = max(1, min(int(limit), 500))
        conditions = ["1=1"]
        params: list[Any] = []
        file_join = ""
        if repo:
            conditions.append("r.name = ?")
            params.append(repo)
        if query:
            conditions.append("lower(s.symbol) LIKE ?")
            params.append(f"%{query.lower()}%")
        if path:
            conditions.append("s.path = ?")
            params.append(path)
        lang_filter = _normalize_lang_filter(lang)
        if lang_filter is not None:
            file_join = "JOIN files f ON s.file_id = f.id"
            conditions.append("f.language = ?")
            params.append(lang_filter)
        kind_filter = _normalize_kind_filter(kind)
        if kind_filter is not None:
            conditions.append("lower(s.kind) = ?")
            params.append(kind_filter)
        with self._session() as conn:
            if repo:
                self._require_known_repo(conn, repo)
            rows = conn.execute(
                f"""
                SELECT r.name AS repo, s.symbol, s.kind, s.path, s.line, s.chunk_id
                FROM symbols s
                JOIN repos r ON s.repo_id = r.id
                {file_join}
                WHERE {' AND '.join(conditions)}
                ORDER BY
                    CASE WHEN ? != '' AND lower(s.symbol) = lower(?) THEN 0 ELSE 1 END,
                    r.name,
                    s.path,
                    s.line
                LIMIT ?
                """,
                [*params, query or "", query or "", limit],
            ).fetchall()
        return [
            {
                "repo": row["repo"],
                "symbol": row["symbol"],
                "kind": row["kind"],
                "path": row["path"],
                "line": row["line"],
                "chunk_id": row["chunk_id"],
            }
            for row in rows
        ]

    def remove_repo(self, name: str) -> dict:
        self.init()
        with self._session() as conn:
            self._require_known_repo(conn, name)
            row = conn.execute("SELECT id FROM repos WHERE name = ?", (name,)).fetchone()
            repo_id = int(row["id"])
            file_ids = [
                int(file_row["id"])
                for file_row in conn.execute(
                    "SELECT id FROM files WHERE repo_id = ?", (repo_id,)
                )
            ]
            # chunks_fts and chunk_vectors are virtual tables that do not cascade.
            for file_id in file_ids:
                self._delete_chunks_for_file(conn, file_id)
            conn.execute("DELETE FROM files WHERE repo_id = ?", (repo_id,))
            conn.execute("DELETE FROM repos WHERE id = ?", (repo_id,))
        return {"repo": name, "deleted_files": len(file_ids)}

    def status(self, repo: str | None = None) -> dict:
        self.init()
        with self._session() as conn:
            self._require_known_repo(conn, repo)
            repo_filter, repo_params = self._repo_filter(repo)
            repos = conn.execute(
                f"SELECT COUNT(*) AS count FROM repos r WHERE 1=1{repo_filter}",
                repo_params,
            ).fetchone()["count"]
            files = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM files f
                JOIN repos r ON f.repo_id = r.id
                WHERE 1=1{repo_filter}
                """,
                repo_params,
            ).fetchone()["count"]
            chunks = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM chunks c
                JOIN repos r ON c.repo_id = r.id
                WHERE 1=1{repo_filter}
                """,
                repo_params,
            ).fetchone()["count"]
            embedded_chunks = conn.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM chunks c
                JOIN repos r ON c.repo_id = r.id
                WHERE c.embedding_json != ''{repo_filter}
                """,
                repo_params,
            ).fetchone()["count"]
            vector_dim = self._vector_dim(conn)
            vector_query_backend = "unavailable"
            if self._sqlite_vec_loaded:
                vector_query_backend = (
                    "sqlite-vec"
                    if vector_dim is not None and self._vector_table_readable(conn, vector_dim)
                    else "json-fallback"
                )
            embed_model = self._embed_model(conn)
            degraded = self.embedder is not None and int(embedded_chunks) < int(chunks)
            per_repo = self._repo_summaries(conn, repo_filter, repo_params)
        return {
            "db_path": str(self.db_path),
            "repos": int(repos),
            "files": int(files),
            "chunks": int(chunks),
            "embedded_chunks": int(embedded_chunks),
            "sqlite_vec": "loaded" if self._sqlite_vec_loaded else "unavailable",
            "vector_query_backend": vector_query_backend,
            "vector_dim": vector_dim,
            "embed_model": embed_model,
            "embeddings": "enabled" if self.embedder is not None else "disabled",
            "degraded": degraded,
            "per_repo": per_repo,
        }
