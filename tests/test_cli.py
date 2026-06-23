import json
import shutil
from pathlib import Path

import pytest

from local_code_indexer.cli import main


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_CODE_INDEXER_DB_PATH", str(tmp_path / "index.db"))
    monkeypatch.setenv("LOCAL_CODE_INDEXER_DISABLE_EMBEDDINGS", "1")


def test_index_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["index", str(tmp_path / "missing")])
    assert excinfo.value.code == 2


def test_watch_rejects_non_positive_interval(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(SystemExit) as excinfo:
        main(["watch", str(repo), "--interval", "0"])
    assert excinfo.value.code == 2


def test_index_remove_roundtrip(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def run():\n    return 'ok'\n")

    main(["index", str(repo), "--name", "demo"])
    indexed = json.loads(capsys.readouterr().out)
    assert indexed["indexed_files"] == 1

    main(["remove", "demo"])
    removed = json.loads(capsys.readouterr().out)
    assert removed["repo"] == "demo"

    main(["status"])
    status = json.loads(capsys.readouterr().out)
    assert status["repos"] == 0


def test_list_repos_outputs_repo_summary_shape(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def run():\n    return 'ok'\n")

    main(["index", str(repo), "--name", "demo"])
    capsys.readouterr()

    main(["list-repos"])
    repos = json.loads(capsys.readouterr().out)

    assert repos == [
        {
            "chunks": 1,
            "embedded_chunks": 0,
            "files": 1,
            "name": "demo",
            "path": str(repo.resolve()),
            "updated_at": repos[0]["updated_at"],
        }
    ]
    assert isinstance(repos[0]["updated_at"], str)
    assert repos[0]["updated_at"]


def test_search_accepts_path_filter(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "src" / "auth.py").write_text("def login(token):\n    return token\n")
    (repo / "docs" / "auth.md").write_text("token docs\n")

    main(["index", str(repo), "--name", "demo"])
    capsys.readouterr()

    main(["search", "token", "--repo", "demo", "--limit", "10"])
    unfiltered = json.loads(capsys.readouterr().out)
    assert {result["path"] for result in unfiltered} == {"docs/auth.md", "src/auth.py"}

    main(["search", "token", "--repo", "demo", "--limit", "10", "--path", "docs/*.md"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["docs/auth.md"]

    main(["search", "token", "--repo", "demo", "--path", "missing/*"])
    assert json.loads(capsys.readouterr().out) == []


def test_search_accepts_lang_filter(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "src" / "auth.py").write_text("def login(token):\n    return token\n")
    (repo / "docs" / "auth.md").write_text("token docs\n")

    main(["index", str(repo), "--name", "demo"])
    capsys.readouterr()

    main(["search", "token", "--repo", "demo", "--limit", "10"])
    unfiltered = json.loads(capsys.readouterr().out)
    assert {result["path"] for result in unfiltered} == {"docs/auth.md", "src/auth.py"}
    assert {result["language"] for result in unfiltered} == {"md", "py"}

    main(["search", "token", "--repo", "demo", "--limit", "10", "--lang", "py"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["src/auth.py"]
    assert [result["language"] for result in filtered] == ["py"]

    main(["search", "token", "--repo", "demo", "--limit", "10", "--lang", ".py"])
    assert [result["path"] for result in json.loads(capsys.readouterr().out)] == ["src/auth.py"]

    main(["search", "token", "--repo", "demo", "--limit", "10", "--lang", "PY"])
    assert [result["path"] for result in json.loads(capsys.readouterr().out)] == ["src/auth.py"]

    main(["search", "token", "--repo", "demo", "--lang", "rs"])
    assert json.loads(capsys.readouterr().out) == []


def test_search_accepts_kind_filter(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "model.py").write_text("class LoginTokenRecord:\n    pass\n")
    (repo / "src" / "handler.py").write_text("def login_token_handler(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo"])
    capsys.readouterr()

    main(["search", "login token", "--repo", "demo", "--limit", "10"])
    unfiltered = json.loads(capsys.readouterr().out)
    assert {result["path"] for result in unfiltered} == {"src/handler.py", "src/model.py"}

    main(["search", "login token", "--repo", "demo", "--limit", "10", "--kind", "class"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["src/model.py"]

    main(["search", "login token", "--repo", "demo", "--limit", "10", "--kind", "function"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["src/handler.py"]

    main(["search", "login token", "--repo", "demo", "--kind", "constant"])
    assert json.loads(capsys.readouterr().out) == []


def test_symbols_command_accepts_filters(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "model.py").write_text("class LoginTokenRecord:\n    pass\n")
    (repo / "src" / "handler.py").write_text("def login_token_handler(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo"])
    capsys.readouterr()

    main(
        [
            "symbols",
            "login",
            "--repo",
            "demo",
            "--path",
            "src/handler.py",
            "--limit",
            "5",
            "--lang",
            "py",
            "--kind",
            "function",
        ]
    )
    symbols = json.loads(capsys.readouterr().out)

    assert symbols == [
        {
            "chunk_id": symbols[0]["chunk_id"],
            "kind": "function",
            "line": 1,
            "path": "src/handler.py",
            "repo": "demo",
            "symbol": "login_token_handler",
        }
    ]


def test_list_files_command_accepts_filters(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "docs").mkdir()
    auth_source = "def login(token):\n    return token\n"
    (repo / "src" / "auth.py").write_text(auth_source)
    (repo / "docs" / "auth.md").write_text("token docs\n")

    main(["index", str(repo), "--name", "demo"])
    capsys.readouterr()

    main(["list-files", "--repo", "demo", "--glob", "src/*.py", "--limit", "10", "--lang", "py"])
    files = json.loads(capsys.readouterr().out)

    assert files == [
        {
            "file_hash": files[0]["file_hash"],
            "indexed_at": files[0]["indexed_at"],
            "language": "py",
            "path": "src/auth.py",
            "repo": "demo",
            "size": len(auth_source),
        }
    ]


def test_read_file_command_accepts_line_range(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text(
        "def login(token):\n"
        "    normalized = token.strip()\n"
        "    return normalized\n"
    )

    main(["index", str(repo), "--name", "demo"])
    capsys.readouterr()

    main(["read-file", "demo", "src/app.py", "--start-line", "2", "--end-line", "3"])
    file_range = json.loads(capsys.readouterr().out)

    assert file_range == {
        "content": "    normalized = token.strip()\n    return normalized",
        "end_line": 3,
        "file_hash": file_range["file_hash"],
        "path": "src/app.py",
        "repo": "demo",
        "start_line": 2,
    }


def test_reindex_all_outputs_registered_repo_results(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    alpha = tmp_path / "alpha"
    alpha.mkdir()
    (alpha / "a.py").write_text("def alpha():\n    return 'old'\n")
    beta = tmp_path / "beta"
    beta.mkdir()
    (beta / "b.py").write_text("def beta():\n    return 'old'\n")

    main(["index", str(beta), "--name", "beta"])
    capsys.readouterr()
    main(["index", str(alpha), "--name", "alpha"])
    capsys.readouterr()
    (alpha / "a.py").write_text("def alpha():\n    return 'new alpha'\n")
    (beta / "b.py").write_text("def beta():\n    return 'new beta'\n")

    main(["reindex-all"])
    result = json.loads(capsys.readouterr().out)

    assert result["reindexed"] == 2
    assert [repo["repo"] for repo in result["repos"]] == ["alpha", "beta"]
    by_repo = {repo["repo"]: repo for repo in result["repos"]}
    assert by_repo["alpha"]["indexed_files"] == 1
    assert by_repo["alpha"]["path"] == str(alpha.resolve())
    assert by_repo["beta"]["indexed_files"] == 1
    assert by_repo["beta"]["path"] == str(beta.resolve())


def test_reindex_all_skips_missing_path_without_aborting(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    missing = tmp_path / "missing"
    missing.mkdir()
    (missing / "gone.py").write_text("def gone():\n    return 'old'\n")
    present = tmp_path / "present"
    present.mkdir()
    (present / "stay.py").write_text("def stay():\n    return 'old'\n")

    main(["index", str(missing), "--name", "missing"])
    capsys.readouterr()
    main(["index", str(present), "--name", "present"])
    capsys.readouterr()
    shutil.rmtree(missing)
    (present / "stay.py").write_text("def stay():\n    return 'new'\n")

    main(["reindex-all"])
    result = json.loads(capsys.readouterr().out)

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


def test_repo_name_conflict_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    one = tmp_path / "a" / "api"
    one.mkdir(parents=True)
    (one / "one.py").write_text("def one():\n    return 1\n")
    two = tmp_path / "b" / "api"
    two.mkdir(parents=True)
    (two / "two.py").write_text("def two():\n    return 2\n")

    main(["index", str(one)])
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        main(["index", str(two)])
    assert excinfo.value.code == 1
    assert "api" in capsys.readouterr().err
