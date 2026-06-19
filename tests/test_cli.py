import json
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
