import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/nathanmauro/local-code-indexer"


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_project_version_is_dynamic() -> None:
    project = _pyproject()["project"]

    assert "version" not in project
    assert "version" in project.get("dynamic", [])


def test_package_version_source_is_pep_440_shaped() -> None:
    init_text = (ROOT / "src" / "local_code_indexer" / "__init__.py").read_text()
    match = re.search(r'^__version__ = ["\']([^"\']+)["\']$', init_text, re.MULTILINE)

    assert match is not None
    assert re.fullmatch(
        r"(?:[1-9]\d*!)?\d+(?:\.\d+)*"
        r"(?:(?:a|b|rc)\d+)?"
        r"(?:\.post\d+)?"
        r"(?:\.dev\d+)?"
        r"(?:\+[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*)?",
        match.group(1),
    )


def test_project_urls_point_to_repository() -> None:
    urls = _pyproject()["project"]["urls"]

    assert urls["Homepage"] == REPO_URL
    assert urls["Repository"] == REPO_URL
    assert urls["Issues"] == f"{REPO_URL}/issues"


def test_project_classifiers_include_packaging_basics() -> None:
    classifiers = set(_pyproject()["project"]["classifiers"])

    assert "License :: OSI Approved :: MIT License" in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
