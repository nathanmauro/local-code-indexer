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

    main(["index", str(repo), "--name", "demo", "--json"])
    indexed = json.loads(capsys.readouterr().out)
    assert indexed == {
        "db_path": indexed["db_path"],
        "degraded": False,
        "deleted_files": 0,
        "embedded_chunks": 0,
        "embedding_failures": 0,
        "indexed_chunks": 1,
        "indexed_files": 1,
        "path": str(repo.resolve()),
        "repo": "demo",
        "skipped_files": 0,
        "unchanged_files": 0,
    }

    main(["remove", "demo", "--json"])
    removed = json.loads(capsys.readouterr().out)
    assert removed == {"deleted_files": 1, "repo": "demo"}

    main(["status", "--json"])
    status = json.loads(capsys.readouterr().out)
    assert status["repos"] == 0


def test_list_repos_outputs_repo_summary_shape(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def run():\n    return 'ok'\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["list-repos", "--json"])
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

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["search", "token", "--repo", "demo", "--limit", "10", "--json"])
    unfiltered = json.loads(capsys.readouterr().out)
    assert {result["path"] for result in unfiltered} == {"docs/auth.md", "src/auth.py"}

    main(["search", "token", "--repo", "demo", "--limit", "10", "--path", "docs/*.md", "--json"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["docs/auth.md"]

    main(["search", "token", "--repo", "demo", "--path", "missing/*", "--json"])
    assert json.loads(capsys.readouterr().out) == []


def test_search_accepts_lang_filter(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "src" / "auth.py").write_text("def login(token):\n    return token\n")
    (repo / "docs" / "auth.md").write_text("token docs\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["search", "token", "--repo", "demo", "--limit", "10", "--json"])
    unfiltered = json.loads(capsys.readouterr().out)
    assert {result["path"] for result in unfiltered} == {"docs/auth.md", "src/auth.py"}
    assert {result["language"] for result in unfiltered} == {"md", "py"}

    main(["search", "token", "--repo", "demo", "--limit", "10", "--lang", "py", "--json"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["src/auth.py"]
    assert [result["language"] for result in filtered] == ["py"]

    main(["search", "token", "--repo", "demo", "--limit", "10", "--lang", ".py", "--json"])
    assert [result["path"] for result in json.loads(capsys.readouterr().out)] == ["src/auth.py"]

    main(["search", "token", "--repo", "demo", "--limit", "10", "--lang", "PY", "--json"])
    assert [result["path"] for result in json.loads(capsys.readouterr().out)] == ["src/auth.py"]

    main(["search", "token", "--repo", "demo", "--lang", "rs", "--json"])
    assert json.loads(capsys.readouterr().out) == []


def test_search_accepts_kind_filter(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "model.py").write_text("class LoginTokenRecord:\n    pass\n")
    (repo / "src" / "handler.py").write_text("def login_token_handler(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["search", "login token", "--repo", "demo", "--limit", "10", "--json"])
    unfiltered = json.loads(capsys.readouterr().out)
    assert {result["path"] for result in unfiltered} == {"src/handler.py", "src/model.py"}

    main(["search", "login token", "--repo", "demo", "--limit", "10", "--kind", "class", "--json"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["src/model.py"]

    main(["search", "login token", "--repo", "demo", "--limit", "10", "--kind", "function", "--json"])
    filtered = json.loads(capsys.readouterr().out)
    assert [result["path"] for result in filtered] == ["src/handler.py"]

    main(["search", "login token", "--repo", "demo", "--kind", "constant", "--json"])
    assert json.loads(capsys.readouterr().out) == []


def test_symbols_command_accepts_filters(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "model.py").write_text("class LoginTokenRecord:\n    pass\n")
    (repo / "src" / "handler.py").write_text("def login_token_handler(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
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
            "--json",
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

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["list-files", "--repo", "demo", "--glob", "src/*.py", "--limit", "10", "--lang", "py", "--json"])
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

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["read-file", "demo", "src/app.py", "--start-line", "2", "--end-line", "3", "--json"])
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

    main(["index", str(beta), "--name", "beta", "--json"])
    capsys.readouterr()
    main(["index", str(alpha), "--name", "alpha", "--json"])
    capsys.readouterr()
    (alpha / "a.py").write_text("def alpha():\n    return 'new alpha'\n")
    (beta / "b.py").write_text("def beta():\n    return 'new beta'\n")

    main(["reindex-all", "--json"])
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

    main(["index", str(missing), "--name", "missing", "--json"])
    capsys.readouterr()
    main(["index", str(present), "--name", "present", "--json"])
    capsys.readouterr()
    shutil.rmtree(missing)
    (present / "stay.py").write_text("def stay():\n    return 'new'\n")

    main(["reindex-all", "--json"])
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


def test_index_defaults_to_human_readable_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def run():\n    return 'ok'\n")

    main(["index", str(repo), "--name", "demo"])
    output = capsys.readouterr().out

    assert output.startswith("Indexed demo ")
    assert f"path={repo.resolve()}" in output
    assert "indexed_files=1" in output
    assert "unchanged_files=0" in output
    assert "skipped_files=0" in output
    assert "deleted_files=0" in output
    assert "embedded_chunks=0" in output
    assert "embedding_failures=0" in output
    assert not output.lstrip().startswith("{")


def test_index_result_renderer_marks_degraded(capsys: pytest.CaptureFixture) -> None:
    from local_code_indexer.cli import _print_index_result

    _print_index_result(
        {
            "repo": "demo",
            "path": "/tmp/demo",
            "indexed_files": 2,
            "indexed_chunks": 3,
            "unchanged_files": 4,
            "skipped_files": 5,
            "deleted_files": 6,
            "embedded_chunks": 7,
            "embedding_failures": 8,
            "degraded": True,
            "db_path": "/tmp/index.db",
        }
    )
    output = capsys.readouterr().out

    assert "Indexed demo " in output
    assert "path=/tmp/demo" in output
    assert "indexed_files=2" in output
    assert "unchanged_files=4" in output
    assert "skipped_files=5" in output
    assert "deleted_files=6" in output
    assert "embedded_chunks=7" in output
    assert "embedding_failures=8" in output
    assert "DEGRADED" in output


def test_reindex_all_defaults_to_human_readable_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    missing = tmp_path / "missing"
    missing.mkdir()
    (missing / "gone.py").write_text("def gone():\n    return 'old'\n")
    present = tmp_path / "present"
    present.mkdir()
    (present / "stay.py").write_text("def stay():\n    return 'old'\n")

    main(["index", str(missing), "--name", "missing", "--json"])
    capsys.readouterr()
    main(["index", str(present), "--name", "present", "--json"])
    capsys.readouterr()
    shutil.rmtree(missing)
    (present / "stay.py").write_text("def stay():\n    return 'new'\n")

    main(["reindex-all"])
    output = capsys.readouterr().out

    assert f"missing path={missing.resolve()} skipped=True error=path missing" in output
    assert f"present path={present.resolve()}" in output
    assert "indexed_files=1" in output
    assert "unchanged_files=0" in output
    assert "skipped_files=0" in output
    assert "deleted_files=0" in output
    assert "embedded_chunks=0" in output
    assert "embedding_failures=0" in output
    assert "reindexed: 1" in output
    assert not output.lstrip().startswith("{")


def test_remove_defaults_to_human_readable_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def run():\n    return 'ok'\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["remove", "demo"])
    output = capsys.readouterr().out

    assert output == "Removed demo (1 files).\n"


def test_repo_name_conflict_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    one = tmp_path / "a" / "api"
    one.mkdir(parents=True)
    (one / "one.py").write_text("def one():\n    return 1\n")
    two = tmp_path / "b" / "api"
    two.mkdir(parents=True)
    (two / "two.py").write_text("def two():\n    return 2\n")

    main(["index", str(one), "--json"])
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        main(["index", str(two)])
    assert excinfo.value.code == 1
    assert "api" in capsys.readouterr().err


def test_search_defaults_to_human_readable_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def login(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["search", "login", "--repo", "demo", "--limit", "1"])
    output = capsys.readouterr().out

    assert "demo app.py:1-2" in output
    assert "score:" in output
    assert "score_reason:" in output
    assert "symbols: login" in output
    assert "def login(token):" in output
    assert not output.lstrip().startswith("[")


def test_status_defaults_to_human_readable_output(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def login(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["status"])
    output = capsys.readouterr().out

    assert "db_path:" in output
    assert "repos: 1" in output
    assert "files: 1" in output
    assert "chunks: 1" in output
    assert "embedded_chunks: 0" in output
    assert "embeddings: disabled" in output
    assert "degraded: False" in output
    assert "vector_query_backend:" in output
    assert "per_repo:" in output
    assert "demo files=1 chunks=1 embedded_chunks=0" in output
    assert not output.lstrip().startswith("{")


def test_empty_read_side_results_print_friendly_line(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def login(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["search", "missing", "--repo", "demo"])
    assert capsys.readouterr().out == "No results.\n"

    main(["symbols", "missing", "--repo", "demo"])
    assert capsys.readouterr().out == "No results.\n"

    main(["list-files", "--repo", "demo", "--glob", "missing/*"])
    assert capsys.readouterr().out == "No results.\n"


@pytest.mark.parametrize(
    "command",
    [
        ["search", "login", "--repo", "missing"],
        ["symbols", "login", "--repo", "missing"],
        ["list-files", "--repo", "missing"],
    ],
)
def test_read_side_commands_reject_unknown_repo(
    command: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def login(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        main(command)

    assert excinfo.value.code == 1
    error = capsys.readouterr().err
    assert "unknown repo: missing" in error
    assert "indexed repos: demo" in error


def test_read_file_distinguishes_unknown_repo_from_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def login(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    with pytest.raises(SystemExit) as excinfo:
        main(["read-file", "missing", "app.py"])

    assert excinfo.value.code == 1
    unknown_repo_error = capsys.readouterr().err
    assert "unknown repo: missing" in unknown_repo_error
    assert "indexed repos: demo" in unknown_repo_error

    with pytest.raises(SystemExit) as excinfo:
        main(["read-file", "demo", "missing.py"])

    assert excinfo.value.code == 1
    missing_file_error = capsys.readouterr().err
    assert "demo:missing.py is not indexed" in missing_file_error
    assert "unknown repo" not in missing_file_error


def test_json_flag_preserves_search_json_shape(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def login(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["search", "login", "--repo", "demo", "--limit", "1", "--json"])
    results = json.loads(capsys.readouterr().out)

    assert results == [
        {
            "chunk_id": results[0]["chunk_id"],
            "end_line": 2,
            "file_hash": results[0]["file_hash"],
            "language": "py",
            "line_range": "1-2",
            "path": "app.py",
            "repo": "demo",
            "score": results[0]["score"],
            "score_reason": results[0]["score_reason"],
            "snippet": "def login(token):\n    return token",
            "start_line": 1,
            "symbols": ["login"],
        }
    ]


def test_json_flag_is_global_before_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def login(token):\n    return token\n")

    main(["index", str(repo), "--name", "demo", "--json"])
    capsys.readouterr()

    main(["--json", "search", "login", "--repo", "demo", "--limit", "1"])
    results = json.loads(capsys.readouterr().out)

    assert results[0]["repo"] == "demo"
    assert results[0]["path"] == "app.py"
