import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_dev_extra_includes_local_build_tools() -> None:
    dev_dependencies = set(_pyproject()["project"]["optional-dependencies"]["dev"])

    assert "build>=1.0" in dev_dependencies
    assert "hatchling>=1.21" in dev_dependencies


def test_ci_runs_build_artifact_verification_after_tests_and_ruff() -> None:
    workflow = CI_WORKFLOW.read_text()

    tests_step = workflow.index("Run tests")
    ruff_step = workflow.index("Run Ruff")
    build_step = workflow.index("Verify package build artifacts")

    assert tests_step < ruff_step < build_step
    assert "python -m pytest tests/test_build_artifact.py -q" in workflow


def test_built_distributions_include_expected_files(tmp_path: Path) -> None:
    pytest.importorskip("build")
    pytest.importorskip("hatchling")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--sdist",
            "--outdir",
            str(tmp_path),
            "--no-isolation",
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    assert result.returncode == 0, result.stdout

    wheels = sorted(tmp_path.glob("*.whl"))
    sdists = sorted(tmp_path.glob("*.tar.gz"))

    assert len(wheels) == 1
    assert len(sdists) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        wheel_names = wheel.namelist()

    assert "local_code_indexer/py.typed" in wheel_names
    assert "local_code_indexer/cli.py" in wheel_names
    assert not any(name.startswith("tests/") for name in wheel_names)
    assert not any(PurePosixPath(name).match("test_*.py") for name in wheel_names)

    with tarfile.open(sdists[0], "r:gz") as sdist:
        sdist_names = [PurePosixPath(member.name) for member in sdist.getmembers()]

    for expected in ("LICENSE", "README.md", "pyproject.toml"):
        assert any(len(name.parts) == 2 and name.name == expected for name in sdist_names)
