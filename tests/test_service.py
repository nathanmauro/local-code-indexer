import json
import shutil
import sqlite3
from pathlib import Path

import pytest

import local_code_indexer.service as service_module
from local_code_indexer.service import EMBED_BREAKER_CONSECUTIVE_FAILURES, IndexService


class FakeEmbedder:
    dim = 4

    def __init__(self):
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
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
    assert indexed["unchanged_files"] == 0
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
    assert after_delete["indexed_files"] == 0
    assert after_delete["unchanged_files"] == 2
    assert after_delete["deleted_files"] == 1
    assert all(file["path"] != "src/calendar.py" for file in service.list_files(repo="demo"))


def test_search_path_filter_applies_to_merged_hybrid_candidates_before_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "src/auth.py", "def login_token_handler(token):\n    return token\n")
    write(repo / "docs/auth_notes.md", "authorization grant details only\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    unfiltered = service.search("login token", repo="demo", mode="hybrid", limit=10)
    assert {result["path"] for result in unfiltered} == {"docs/auth_notes.md", "src/auth.py"}
    assert service.search("login token", repo="demo", mode="hybrid", limit=10, path=None) == unfiltered
    assert service.search("login token", repo="demo", mode="hybrid", limit=10, path="") == unfiltered
    assert service.search("login token", repo="demo", mode="hybrid", limit=10, path="missing/*") == []
    assert service.search("login token", repo="demo", mode="hybrid", limit=1)[0]["path"] == "src/auth.py"

    filtered = service.search("login token", repo="demo", mode="hybrid", limit=1, path="docs/*.md")

    assert [result["path"] for result in filtered] == ["docs/auth_notes.md"]
    assert filtered[0]["score_reason"] == "vector"


def test_search_lang_filter_applies_to_merged_hybrid_candidates_before_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "src/auth.py", "def login_token_handler(token):\n    return token\n")
    write(repo / "docs/auth_notes.md", "authorization grant details only\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    unfiltered = service.search("login token", repo="demo", mode="hybrid", limit=10)
    assert {result["path"] for result in unfiltered} == {"docs/auth_notes.md", "src/auth.py"}
    assert {result["language"] for result in unfiltered} == {"md", "py"}
    assert service.search("login token", repo="demo", mode="hybrid", limit=10, lang=None) == unfiltered
    assert service.search("login token", repo="demo", mode="hybrid", limit=10, lang="") == unfiltered
    assert service.search("login token", repo="demo", mode="hybrid", limit=10, lang="rs") == []
    assert service.search("login token", repo="demo", mode="hybrid", limit=1)[0]["path"] == "src/auth.py"

    filtered = service.search("login token", repo="demo", mode="hybrid", limit=1, lang="md")

    assert [result["path"] for result in filtered] == ["docs/auth_notes.md"]
    assert [result["language"] for result in filtered] == ["md"]
    assert filtered[0]["score_reason"] == "vector"
    assert [result["path"] for result in service.search("login token", repo="demo", lang="py")] == [
        "src/auth.py"
    ]
    assert [result["path"] for result in service.search("login token", repo="demo", lang=".py")] == [
        "src/auth.py"
    ]
    assert [result["path"] for result in service.search("login token", repo="demo", lang="PY")] == [
        "src/auth.py"
    ]


def test_list_files_accepts_lang_filter(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "src/auth.py", "def login(token):\n    return token\n")
    write(repo / "docs/auth.md", "token docs\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    unfiltered = service.list_files(repo="demo")
    assert {file["path"] for file in unfiltered} == {"docs/auth.md", "src/auth.py"}
    assert service.list_files(repo="demo", lang=None) == unfiltered
    assert service.list_files(repo="demo", lang="") == unfiltered
    assert [file["path"] for file in service.list_files(repo="demo", lang="py")] == ["src/auth.py"]
    assert [file["path"] for file in service.list_files(repo="demo", lang=".py")] == ["src/auth.py"]
    assert [file["path"] for file in service.list_files(repo="demo", lang="PY")] == ["src/auth.py"]
    assert service.list_files(repo="demo", lang="rs") == []


def test_symbols_accepts_lang_filter_before_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "a.py", "def python_symbol():\n    return 1\n")
    write(repo / "z.md", "```python\ndef markdown_symbol():\n    return 2\n```\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    unfiltered = service.symbols(repo="demo", limit=10)
    assert {symbol["path"] for symbol in unfiltered} == {"a.py", "z.md"}
    assert service.symbols(repo="demo", lang=None, limit=10) == unfiltered
    assert service.symbols(repo="demo", lang="", limit=10) == unfiltered
    assert [symbol["path"] for symbol in service.symbols(repo="demo", lang="py")] == ["a.py"]
    assert [symbol["path"] for symbol in service.symbols(repo="demo", lang=".py")] == ["a.py"]
    assert [symbol["path"] for symbol in service.symbols(repo="demo", lang="PY")] == ["a.py"]
    assert service.symbols(repo="demo", lang="rs") == []
    assert [symbol["path"] for symbol in service.symbols(repo="demo", lang="md", limit=1)] == ["z.md"]


def test_symbols_capture_kind_and_accept_kind_filter_before_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(
        repo / "model.py",
        "class Account:\n"
        "    def balance(self):\n"
        "        return 1\n\n"
        "def load_account():\n"
        "    return Account()\n",
    )

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    unfiltered = service.symbols(repo="demo", limit=10)
    by_symbol = {symbol["symbol"]: symbol for symbol in unfiltered}
    assert by_symbol["Account"]["kind"] == "class"
    assert by_symbol["balance"]["kind"] == "method"
    assert by_symbol["load_account"]["kind"] == "function"
    assert service.symbols(repo="demo", kind=None, limit=10) == unfiltered
    assert service.symbols(repo="demo", kind="", limit=10) == unfiltered
    assert [symbol["symbol"] for symbol in service.symbols(repo="demo", kind="class")] == ["Account"]
    assert [symbol["symbol"] for symbol in service.symbols(repo="demo", kind="function")] == [
        "load_account"
    ]
    assert [symbol["symbol"] for symbol in service.symbols(repo="demo", kind="method")] == ["balance"]
    assert [symbol["symbol"] for symbol in service.symbols(repo="demo", kind="METHOD")] == ["balance"]
    assert service.symbols(repo="demo", kind="constant") == []


def test_init_migrates_existing_symbols_table_to_store_kind(tmp_path: Path) -> None:
    db_path = tmp_path / "index.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE symbols (
                id INTEGER PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                chunk_id TEXT,
                symbol TEXT NOT NULL,
                path TEXT NOT NULL,
                line INTEGER NOT NULL
            )
            """
        )

    service = IndexService(db_path, embedder=FakeEmbedder())
    service.init()

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(symbols)")}
    assert "kind" in columns


def test_index_repo_skips_unchanged_files_without_reembedding(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "src/auth.py", "def login(token):\n    return token.strip()\n")
    write(repo / "README.md", "# Demo\nSQLite FTS code index notes\n")

    embedder = FakeEmbedder()
    service = IndexService(tmp_path / "index.db", embedder=embedder)
    service.init()
    first = service.index_repo(repo, name="demo")
    calls_after_first = len(embedder.calls)

    second = service.index_repo(repo, name="demo")

    assert first["indexed_files"] == 2
    assert first["unchanged_files"] == 0
    assert second["indexed_files"] == 0
    assert second["indexed_chunks"] == 0
    assert second["embedded_chunks"] == 0
    assert second["unchanged_files"] == 2
    assert len(embedder.calls) == calls_after_first
    results = service.search("login token", repo="demo", mode="lexical", limit=3)
    assert results[0]["path"] == "src/auth.py"
    assert len(embedder.calls) == calls_after_first


def test_index_repo_reindexes_only_modified_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "src/auth.py", "def login(token):\n    return token.strip()\n")
    write(repo / "src/calendar.py", "def schedule_meeting(title):\n    return title.lower()\n")

    embedder = FakeEmbedder()
    service = IndexService(tmp_path / "index.db", embedder=embedder)
    service.init()
    service.index_repo(repo, name="demo")
    calls_after_first = len(embedder.calls)

    write(
        repo / "src/auth.py",
        "def login(token):\n    return token.strip()\n\n\ndef refresh_token(token):\n    return token\n",
    )
    result = service.index_repo(repo, name="demo")

    assert result["indexed_files"] == 1
    assert result["indexed_chunks"] == 1
    assert result["embedded_chunks"] == 1
    assert result["unchanged_files"] == 1
    assert len(embedder.calls) == calls_after_first + 1
    assert "refresh_token" in embedder.calls[-1]
    assert service.search("refresh_token", repo="demo", mode="lexical")[0]["path"] == "src/auth.py"
    assert service.search("schedule meeting", repo="demo", mode="lexical")[0]["path"] == "src/calendar.py"


def test_index_repo_incremental_delete_still_purges_missing_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "src/auth.py", "def login(token):\n    return token.strip()\n")
    write(repo / "src/calendar.py", "def schedule_meeting(title):\n    return title.lower()\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(repo, name="demo")

    (repo / "src/calendar.py").unlink()
    result = service.index_repo(repo, name="demo")

    assert result["indexed_files"] == 0
    assert result["unchanged_files"] == 1
    assert result["deleted_files"] == 1
    assert [file["path"] for file in service.list_files(repo="demo")] == ["src/auth.py"]
    assert service.search("schedule meeting", repo="demo", mode="lexical") == []


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


def test_list_repos_returns_zero_one_and_multiple_repo_summaries(tmp_path: Path) -> None:
    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()

    assert service.list_repos() == []

    beta = tmp_path / "beta"
    write(beta / "app.py", "def beta():\n    return 'sqlite fts'\n")
    service.index_repo(beta, name="beta")

    one_repo = service.list_repos()
    assert len(one_repo) == 1
    assert one_repo[0]["name"] == "beta"
    assert one_repo[0]["path"] == str(beta.resolve())
    assert one_repo[0]["files"] == 1
    assert one_repo[0]["chunks"] >= 1
    assert one_repo[0]["embedded_chunks"] == one_repo[0]["chunks"]
    assert isinstance(one_repo[0]["updated_at"], str)
    assert one_repo[0]["updated_at"]

    alpha = tmp_path / "alpha"
    write(alpha / "lib.py", "def alpha():\n    return 'auth token'\n")
    write(alpha / "README.md", "# Alpha\n")
    service.index_repo(alpha, name="alpha")

    repos = service.list_repos()
    assert [repo["name"] for repo in repos] == ["alpha", "beta"]
    by_name = {repo["name"]: repo for repo in repos}
    assert by_name["alpha"]["files"] == 2
    assert by_name["alpha"]["chunks"] >= 2
    assert by_name["alpha"]["embedded_chunks"] == by_name["alpha"]["chunks"]
    assert by_name["beta"]["files"] == 1


def test_reindex_all_reindexes_every_registered_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS", "1")
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    write(alpha / "a.py", "def alpha():\n    return 'old'\n")
    write(beta / "b.py", "def beta():\n    return 'old'\n")

    service = IndexService(tmp_path / "index.db")
    service.init()
    service.index_repo(beta, name="beta")
    service.index_repo(alpha, name="alpha")
    write(alpha / "a.py", "def alpha():\n    return 'new alpha'\n")
    write(beta / "b.py", "def beta():\n    return 'new beta'\n")

    result = service.reindex_all()

    assert result["reindexed"] == 2
    assert result["db_path"] == str(tmp_path / "index.db")
    assert [repo["repo"] for repo in result["repos"]] == ["alpha", "beta"]
    by_repo = {repo["repo"]: repo for repo in result["repos"]}
    assert by_repo["alpha"]["path"] == str(alpha.resolve())
    assert by_repo["alpha"]["indexed_files"] == 1
    assert by_repo["alpha"]["unchanged_files"] == 0
    assert by_repo["beta"]["path"] == str(beta.resolve())
    assert by_repo["beta"]["indexed_files"] == 1
    assert by_repo["beta"]["unchanged_files"] == 0
    assert service.read_file("alpha", "a.py")["content"] == "def alpha():\n    return 'new alpha'"
    assert service.read_file("beta", "b.py")["content"] == "def beta():\n    return 'new beta'"


def test_reindex_all_skips_missing_repo_path_and_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS", "1")
    missing = tmp_path / "missing"
    present = tmp_path / "present"
    write(missing / "gone.py", "def gone():\n    return 'old'\n")
    write(present / "stay.py", "def stay():\n    return 'old'\n")

    service = IndexService(tmp_path / "index.db")
    service.init()
    service.index_repo(missing, name="missing")
    service.index_repo(present, name="present")
    shutil.rmtree(missing)
    write(present / "stay.py", "def stay():\n    return 'new'\n")

    result = service.reindex_all()

    assert result["reindexed"] == 1
    by_repo = {repo["repo"]: repo for repo in result["repos"]}
    assert by_repo["missing"] == {
        "repo": "missing",
        "path": str(missing.resolve()),
        "skipped": True,
        "error": "path missing",
    }
    assert by_repo["present"]["indexed_files"] == 1
    assert by_repo["present"]["path"] == str(present.resolve())
    assert service.read_file("present", "stay.py")["content"] == "def stay():\n    return 'new'"


def test_status_includes_per_repo_breakdown_and_respects_repo_filter(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    write(alpha / "a.py", "def alpha():\n    return 'auth token'\n")
    write(alpha / "docs.txt", "index sqlite fts\n")
    beta = tmp_path / "beta"
    write(beta / "b.py", "def beta():\n    return 'calendar meeting'\n")

    service = IndexService(tmp_path / "index.db", embedder=FakeEmbedder())
    service.init()
    service.index_repo(beta, name="beta")
    service.index_repo(alpha, name="alpha")

    status = service.status()

    assert [repo["name"] for repo in status["per_repo"]] == ["alpha", "beta"]
    by_name = {repo["name"]: repo for repo in status["per_repo"]}
    assert by_name["alpha"]["path"] == str(alpha.resolve())
    assert by_name["alpha"]["files"] == 2
    assert by_name["alpha"]["chunks"] >= 2
    assert by_name["alpha"]["embedded_chunks"] == by_name["alpha"]["chunks"]
    assert by_name["beta"]["files"] == 1
    assert by_name["beta"]["embedded_chunks"] == by_name["beta"]["chunks"]

    filtered = service.status(repo="beta")

    assert filtered["repos"] == 1
    assert filtered["files"] == by_name["beta"]["files"]
    assert filtered["chunks"] == by_name["beta"]["chunks"]
    assert filtered["embedded_chunks"] == by_name["beta"]["embedded_chunks"]
    assert filtered["per_repo"] == [by_name["beta"]]


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


class ModelEmbedder:
    dim = 4

    def __init__(self, model: str, marker: float):
        self.model = model
        self.marker = marker
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [self.marker, 0.0, 0.0, 0.0]


class BackendEmbedder:
    dim = 4
    model = "shared-model"

    def __init__(self, api: str, base_url: str, marker: float):
        self.api = api
        self.base_url = base_url
        self.marker = marker
        self.calls: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return [self.marker, 0.0, 0.0, 0.0]


def test_index_repo_persists_embed_model_and_status_reports_it(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    service = IndexService(tmp_path / "index.db", embedder=ModelEmbedder("model-a", 1.0))
    service.init()
    service.index_repo(repo, name="demo")

    with sqlite3.connect(tmp_path / "index.db") as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'embed_model'").fetchone()
    assert row == ("model-a",)
    assert service.status()["embed_model"] == "model-a"


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


def test_same_dimension_model_change_forces_reindex(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    first_embedder = ModelEmbedder("model-a", 1.0)
    first = IndexService(tmp_path / "index.db", embedder=first_embedder)
    first.init()
    first.index_repo(repo, name="demo")

    second_embedder = ModelEmbedder("model-b", 2.0)
    second = IndexService(tmp_path / "index.db", embedder=second_embedder)
    result = second.index_repo(repo, name="demo")

    assert result["indexed_files"] == 1
    assert result["unchanged_files"] == 0
    assert result["embedded_chunks"] == result["indexed_chunks"]
    assert len(second_embedder.calls) == result["indexed_chunks"]
    with sqlite3.connect(tmp_path / "index.db") as conn:
        row = conn.execute("SELECT embedding_json FROM chunks").fetchone()
    assert json.loads(row[0])[0] == 2.0
    assert second.status()["embed_model"] == "model-b"


def test_same_model_backend_change_forces_reindex(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    first = IndexService(
        tmp_path / "index.db",
        embedder=BackendEmbedder("ollama", "http://127.0.0.1:11434", 1.0),
    )
    first.init()
    first.index_repo(repo, name="demo")
    # Databases created before backend identity tracking have only embed_model.
    with sqlite3.connect(tmp_path / "index.db") as conn:
        conn.execute("DELETE FROM settings WHERE key = 'embed_backend'")

    second_embedder = BackendEmbedder("openai", "http://localhost:1234", 2.0)
    second = IndexService(tmp_path / "index.db", embedder=second_embedder)
    result = second.index_repo(repo, name="demo")

    assert result["indexed_files"] == 1
    assert result["unchanged_files"] == 0
    assert len(second_embedder.calls) == result["indexed_chunks"]
    with sqlite3.connect(tmp_path / "index.db") as conn:
        row = conn.execute("SELECT embedding_json FROM chunks").fetchone()
    assert json.loads(row[0])[0] == 2.0


def test_interrupted_same_dimension_model_change_retries_stale_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "a.py", "def alpha():\n    return 1\n")
    write(repo / "b.py", "def beta():\n    return 2\n")

    first = IndexService(tmp_path / "index.db", embedder=ModelEmbedder("model-a", 1.0))
    first.init()
    first.index_repo(repo, name="demo")

    second = IndexService(tmp_path / "index.db", embedder=ModelEmbedder("model-b", 2.0))
    real_upsert_file = second._upsert_file
    upserted: list[str] = []

    def interrupt_after_first_file(*args, **kwargs):
        rel_path = args[2]
        if upserted:
            raise RuntimeError("stop after first committed file")
        upserted.append(rel_path)
        return real_upsert_file(*args, **kwargs)

    second._upsert_file = interrupt_after_first_file
    with pytest.raises(RuntimeError, match="stop after first"):
        second.index_repo(repo, name="demo")

    retry_embedder = ModelEmbedder("model-b", 2.0)
    retry = IndexService(tmp_path / "index.db", embedder=retry_embedder)
    result = retry.index_repo(repo, name="demo")

    assert result["indexed_files"] == 2
    assert result["unchanged_files"] == 0
    assert len(retry_embedder.calls) == result["indexed_chunks"]
    with sqlite3.connect(tmp_path / "index.db") as conn:
        markers = [
            json.loads(row[0])[0]
            for row in conn.execute("SELECT embedding_json FROM chunks ORDER BY path")
        ]
    assert markers == [2.0, 2.0]


def test_unchanged_files_skip_when_sqlite_vec_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service_module, "sqlite_vec", None)
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    embedder = ModelEmbedder("model-a", 1.0)
    service = IndexService(tmp_path / "index.db", embedder=embedder)
    service.init()
    service.index_repo(repo, name="demo")
    calls_after_first = len(embedder.calls)

    second = service.index_repo(repo, name="demo")

    assert second["indexed_files"] == 0
    assert second["unchanged_files"] == 1
    assert len(embedder.calls) == calls_after_first


def test_disabled_embeddings_leave_embed_model_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS", "1")
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    service = IndexService(tmp_path / "index.db")
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["embedded_chunks"] == 0
    assert result["embedding_failures"] == 0
    assert service.status()["embeddings"] == "disabled"
    assert service.status()["embed_model"] is None


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


class CountingFailingBatchEmbedder:
    def __init__(self):
        self.batches: list[list[str]] = []

    def embed(self, text: str) -> list[float]:
        raise RuntimeError("embedding service died")

    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        self.batches.append(list(texts))
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


def test_embedding_breaker_stops_calls_after_consecutive_failed_batches(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    assert EMBED_BREAKER_CONSECUTIVE_FAILURES >= 5
    file_count = EMBED_BREAKER_CONSECUTIVE_FAILURES + 3
    for index in range(file_count):
        write(
            repo / f"file_{index}.py",
            f"def breaker_sentinel_{index}():\n    return {index}\n",
        )

    embedder = CountingFailingBatchEmbedder()
    service = IndexService(tmp_path / "index.db", embedder=embedder)
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["indexed_files"] == file_count
    assert len(embedder.batches) == EMBED_BREAKER_CONSECUTIVE_FAILURES
    assert result["embedding_failures"] == sum(len(batch) for batch in embedder.batches)
    assert result["degraded"] is True
    assert len(service.list_files(repo="demo")) == file_count
    lexical_hits = service.search("breaker_sentinel_7", repo="demo", mode="lexical")
    assert lexical_hits[0]["path"] == "file_7.py"
    status = service.status()
    assert status["degraded"] is True
    assert status["embedded_chunks"] == 0
    assert status["chunks"] == result["indexed_chunks"]


def test_disabled_embeddings_report_not_degraded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS", "1")
    repo = tmp_path / "repo"
    write(repo / "app.py", "def run():\n    return 'ok'\n")

    service = IndexService(tmp_path / "index.db")
    service.init()
    result = service.index_repo(repo, name="demo")

    assert result["degraded"] is False
    assert service.status()["degraded"] is False
