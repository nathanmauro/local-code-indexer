import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_py_typed_marker_exists_and_has_no_content() -> None:
    marker = REPO_ROOT / "src" / "local_code_indexer" / "py.typed"

    assert marker.is_file()
    content = marker.read_bytes()
    assert content.strip() == b""
    assert len(content) <= 1


def test_local_editor_artifacts_are_gitignored() -> None:
    for probe in (".idea/probe", ".vscode/probe", ".python-version", ".coverage"):
        result = subprocess.run(
            ["git", "check-ignore", "-q", probe],
            cwd=REPO_ROOT,
            check=False,
        )
        assert result.returncode == 0, probe
