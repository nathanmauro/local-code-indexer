from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_exists_and_runs_verify_tools() -> None:
    assert CI_WORKFLOW.exists()

    workflow = CI_WORKFLOW.read_text()

    for expected in ("on:", "jobs:", "pytest", "ruff"):
        assert expected in workflow
