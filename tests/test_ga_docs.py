from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFY_COMMAND = ".venv/bin/python -m pytest -q && .venv/bin/ruff check ."


def test_ga_readiness_docs_exist_and_have_expected_structure() -> None:
    changelog = REPO_ROOT / "CHANGELOG.md"
    contributing = REPO_ROOT / "CONTRIBUTING.md"

    assert changelog.exists()
    assert contributing.exists()

    changelog_text = changelog.read_text(encoding="utf-8")
    contributing_text = contributing.read_text(encoding="utf-8")

    assert len(changelog_text) > 200
    assert len(contributing_text) > 200
    assert "## [Unreleased]" in changelog_text or "## [" in changelog_text
    assert VERIFY_COMMAND in contributing_text
