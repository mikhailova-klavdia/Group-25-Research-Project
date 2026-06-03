"""CLI-facing tests for graceful interruption handling in ReAct runs.

These focus on host-side control flow rather than live SDK behavior. The
goal is to ensure operator interrupts produce a clean exit code and short
stderr message instead of an asyncio traceback.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from research_agents.project import ResearchContext
from research_agents.react_main import run_react_query


def _context(tmp_path: Path) -> ResearchContext:
    project = tmp_path / "paper"
    repo = project / "repo"
    run = project / "runs" / "run-1"
    workspace = run / "workspace"
    venv = project / ".venv"
    artifacts = project / ".artifacts"
    for path in (repo, workspace, venv / "bin", artifacts):
        path.mkdir(parents=True, exist_ok=True)
    (project / "paper.pdf").write_text("paper", encoding="utf-8")
    return ResearchContext(
        project_dir=project,
        paper_path=project / "paper.pdf",
        repo_path=repo,
        run_id="run-1",
        run_dir=run,
        workspace_path=workspace,
        venv_path=venv,
        artifacts_path=artifacts,
    )


def test_run_react_query_exits_cleanly_on_keyboard_interrupt(capsys):
    context = _context(Path("tests/.tmp-react-main"))
    team = SimpleNamespace(
        name="solo",
        description="stub team",
        run=lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    with pytest.raises(SystemExit) as excinfo:
        run_react_query(
            context=context,
            question="Run the workflow.",
            model="gpt-4.1-mini-2025-04-14",
            entry_id="Q001",
            biorxiv_url="",
            ground_truth="",
            team=team,
        )

    captured = capsys.readouterr()
    assert excinfo.value.code == 130
    assert "Interrupted by user. Partial output was not saved." in captured.err
