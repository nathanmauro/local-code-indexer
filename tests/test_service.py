from pathlib import Path

import pytest

from local_code_indexer.service import IndexService


class FakeEmbedder:
    dim = 4

    def embed(self, text: str) -> list[float]:
        lowered = text.lower()
        return [
            1.0 if any(term in lowered for term in ("auth", "login", "token")) else 0.0,
            1.0 if any(term in lowered for term in ("schedule", "calendar", "meeting")) else 0.0,
            1.0 if any(term in lowered for term in ("index", "sqlite", "fts")) else 0.0,
            0.5,
        ]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_index_repo_search_read_symbols_and_incremental_delete(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(
        repo / "src/auth.py",
        "class AuthService:\n    def login(self, token):\n        return token.strip()\n",
    )
    write(
        repo / "src/calendar.py",
        "def schedule_meeting(title):\n    return title.lower()\n",
    )
    write(repo / "README.md", "# Demo\nSQLite FTS code index notes\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    indexed = service.index_repo(repo, name="demo")

    assert indexed["indexed_files"] == 3
    assert indexed["deleted_files"] == 0

    auth_results = service.search("login token flow", repo="demo", limit=3)
    assert auth_results[0]["path"] == "src/auth.py"
    assert "vector" in auth_results[0]["score_reason"]
    assert "line_range" in auth_results[0]
    assert "file_hash" in auth_results[0]

    path_results = service.search("src/calendar.py", repo="demo", limit=3)
    assert path_results[0]["path"] == "src/calendar.py"
    assert "path" in path_results[0]["score_reason"]

    read = service.read_file("demo", "src/auth.py", start_line=2, end_line=2)
    assert read["content"] == "    def login(self, token):"
    assert read["start_line"] == 2
    assert read["end_line"] == 2

    symbols = service.symbols(repo="demo", query="Auth", limit=10)
    assert symbols[0]["symbol"] == "AuthService"
    assert symbols[0]["path"] == "src/auth.py"

    (repo / "src/calendar.py").unlink()
    after_delete = service.index_repo(repo, name="demo")
    assert after_delete["deleted_files"] == 1
    assert all(file["path"] != "src/calendar.py" for file in service.list_files(repo="demo"))


def test_symbols_table_uses_definition_lines(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "util.py", '"""Module that uses helper_fn for things."""\n\n\ndef helper_fn():\n    return 1\n')

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    rows = service.symbols(repo="demo", query="helper_fn")
    assert rows[0]["line"] == 4


def test_line_numbers_stay_consistent_with_form_feeds(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "pages.py", "x = 1\ny = 2\f\nz = 3\ndef target_fn():\n    return 1\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    line = service.symbols(repo="demo", query="target_fn")[0]["line"]
    read = service.read_file("demo", "pages.py", start_line=line, end_line=line)
    assert read["content"] == "def target_fn():"


def test_status_counts_repos_files_chunks_and_vector_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "main.py", "def build_index():\n    return 'sqlite fts'\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    status = service.status()

    assert status["db_path"].endswith("index.db")
    assert status["repos"] == 1
    assert status["files"] == 1
    assert status["chunks"] >= 1
    assert status["embedded_chunks"] == status["chunks"]
    assert status["sqlite_vec"] in {"loaded", "unavailable"}


def test_index_rejects_missing_path(tmp_path: Path) -> None:
    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()

    with pytest.raises(ValueError, match="directory"):
        service.index_repo(tmp_path / "missing")
    assert service.status()["repos"] == 0


def test_repo_identity_keyed_on_path_not_basename(tmp_path: Path) -> None:
    one = tmp_path / "a" / "api"
    write(one / "one.py", "def one():\n    return 1\n")
    two = tmp_path / "b" / "api"
    write(two / "two.py", "def two():\n    return 2\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(one)

    with pytest.raises(ValueError, match="api"):
        service.index_repo(two)

    service.index_repo(two, name="api-b")
    assert [f["path"] for f in service.list_files(repo="api")] == ["one.py"]
    assert [f["path"] for f in service.list_files(repo="api-b")] == ["two.py"]


def test_index_with_new_name_renames_instead_of_duplicating(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo)
    service.index_repo(repo, name="renamed")

    assert service.status()["repos"] == 1
    assert service.list_files(repo="renamed")
    assert not service.list_files(repo="repo")
    hits = [r["path"] for r in service.search("run", limit=10)]
    assert hits.count("app.py") == 1


def test_transient_file_errors_skip_the_file_not_the_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    write(repo / "good.py", "def good():\n    return 1\n")
    write(repo / "bad.py", "def bad():\n    return 0\n")

    real_read_bytes = Path.read_bytes

    def flaky_read_bytes(self):
        if self.name == "bad.py":
            raise OSError("vanished mid-scan")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["indexed_files"] == 1
    assert result["skipped_files"] == 1
    assert [f["path"] for f in service.list_files(repo="demo")] == ["good.py"]


def test_invalid_utf8_past_sniff_window_is_skipped(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "good.py", "def good():\n    return 1\n")
    (repo / "weird.py").write_bytes(b"# " + b"a" * 4200 + b"\n\xff\xfe garbage\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["skipped_files"] == 1
    assert [f["path"] for f in service.list_files(repo="demo")] == ["good.py"]


class FailingEmbedder:
    def embed(self, text: str) -> list[float]:
        raise RuntimeError("embedding service died")


def test_embedding_failures_are_visible_in_result_and_status(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    service = IndexService(tmp_path / "index.db", embedder=FailingEmbedder())
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["indexed_chunks"] >= 1
    assert result["embedded_chunks"] == 0
    assert result["embedding_failures"] == result["indexed_chunks"]
    assert service.status()["embedded_chunks"] == 0


class DimEmbedder:
    def __init__(self, dim: int):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        return [1.0] + [0.0] * (self.dim - 1)


def test_embedding_dimension_change_recovers_on_reindex(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    first = IndexService(tmp_path / "index.db", embedder=DimEmbedder(4))
    first.init()
    first.index_repo(repo, name="demo")
    assert first.status()["vector_dim"] == 4

    second = IndexService(tmp_path / "index.db", embedder=DimEmbedder(8))
    second.index_repo(repo, name="demo")
    assert second.status()["vector_dim"] == 8
    assert second.search("run", repo="demo", mode="vector")


def test_vector_search_uses_sqlite_vec_when_loaded(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "src/auth.py", "def login(token):\n    return token\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    results = service.search("auth login token", repo="demo", mode="vector")
    assert results
    if service.status()["sqlite_vec"] == "loaded":
        assert service.last_vector_backend == "sqlite-vec"


def test_empty_query_returns_nothing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    assert service.search("", repo="demo") == []
    assert service.search("   ", repo="demo") == []


def test_remove_repo_deletes_everything(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    removed = service.remove_repo("demo")
    assert removed["deleted_files"] == 1

    status = service.status()
    assert status["repos"] == 0
    assert status["files"] == 0
    assert status["chunks"] == 0
    assert service.search("run") == []
    with pytest.raises(ValueError, match="unknown repo"):
        service.remove_repo("demo")


class BatchEmbedder:
    def __init__(self):
        self.batches: list[list[str]] = []

    def embed(self, text: str) -> list[float]:
        return [1.0, 0.5]

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        self.batches.append(list(texts))
        return [[1.0, 0.5] for _ in texts]


def test_index_repo_batches_embeddings_per_file_capped_at_64(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    # 4600 plain lines chunk into 66 windows (80 lines, 10 overlap), forcing a
    # 64-chunk batch plus a 2-chunk remainder for one file.
    write(repo / "big.txt", "\n".join(f"value {i} of the data" for i in range(4600)) + "\n")
    write(repo / "small.py", "def run():\n    return 'ok'\n")

    embedder = BatchEmbedder()
    service = IndexService(tmp_path / "index.db", embedder=embedder)
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["embedded_chunks"] == result["indexed_chunks"]
    assert result["embedding_failures"] == 0
    assert sum(len(batch) for batch in embedder.batches) == result["indexed_chunks"]
    assert all(len(batch) <= 64 for batch in embedder.batches)
    assert any(len(batch) == 64 for batch in embedder.batches)


class RaisingBatchEmbedder:
    def embed(self, text: str) -> list[float]:
        raise RuntimeError("embedding service died")

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        raise RuntimeError("embedding service died")


def test_batch_embedding_failure_counts_every_chunk_and_keeps_indexing(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")
    write(repo / "other.py", "def stop():\n    return 'done'\n")

    service = IndexService(tmp_path / "index.db", embedder=RaisingBatchEmbedder())
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["indexed_files"] == 2
    assert result["indexed_chunks"] >= 2
    assert result["embedded_chunks"] == 0
    assert result["embedding_failures"] == result["indexed_chunks"]
