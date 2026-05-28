from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_agents.agents.critic_agent import CriticReview
from research_agents.agents.react_agent import ReActAnswer, ReActStep
from research_agents.react_main import _failure_analysis
from research_agents.orchestration import (
    InstallEvent,
    _build_critic_input,
    _detect_missing_modules,
    _package_for_import,
    run_with_critic,
)
from research_agents.project import ResearchContext


def _answer(final_answer: str = "EXECUTION_REQUIRED — missing torch") -> ReActAnswer:
    return ReActAnswer(
        chain=[
            ReActStep(
                step=1,
                thought="Try running the script.",
                action='execute_command("python run.py")',
                observation="ModuleNotFoundError: No module named 'torch'",
                reflection="Need torch before retrying.",
            )
        ],
        final_answer=final_answer,
    )


def _result(final_answer: str = "EXECUTION_REQUIRED — missing torch"):
    return SimpleNamespace(
        final_output=_answer(final_answer),
        context_wrapper=SimpleNamespace(usage=SimpleNamespace(input_tokens=10, output_tokens=5)),
    )


def _context(tmp_path: Path) -> ResearchContext:
    project = tmp_path / "paper"
    repo = project / "repo"
    run = project / "runs" / "run-1"
    workspace = run / "workspace"
    venv = project / ".venv"
    artifacts = project / ".artifacts"
    for path in (repo, workspace, venv / "bin", artifacts):
        path.mkdir(parents=True)
    (project / "paper.pdf").write_text("paper", encoding="utf-8")
    (venv / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
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


def test_detect_missing_modules_extracts_unique_imports():
    outputs = [
        "ModuleNotFoundError: No module named 'torch'",
        'ImportError: No module named "torch_geometric"',
        "ModuleNotFoundError: No module named 'torch'",
    ]

    assert _detect_missing_modules(outputs) == ["torch", "torch_geometric"]


def test_package_for_import_maps_common_package_names():
    assert _package_for_import("torch_geometric") == "torch-geometric"
    assert _package_for_import("sklearn.metrics") == "scikit-learn"
    assert _package_for_import("torch") == "torch"


def test_build_critic_input_contains_question_truth_and_outputs():
    text = _build_critic_input(
        question="What is the score?",
        ground_truth="0.5",
        answer=_answer(),
        tool_outputs=["ModuleNotFoundError: No module named 'torch'"],
    )

    assert "What is the score?" in text
    assert "0.5" in text
    assert "ModuleNotFoundError" in text


def test_failure_analysis_preserves_structured_blocker_metadata():
    answer = _answer("EXECUTION_REQUIRED — checkpoint missing")
    answer.answer_status = "blocked"
    answer.blocker_type = "missing_weights"
    answer.blocker_explanation = "The CrossPPI checkpoint was not found in save/."
    answer.blocker_evidence = ["FileNotFoundError: save/model.pth"]

    analysis = _failure_analysis(answer)

    assert analysis == {
        "answer_status": "blocked",
        "blocker_type": "missing_weights",
        "blocker_explanation": "The CrossPPI checkpoint was not found in save/.",
        "blocker_evidence": ["FileNotFoundError: save/model.pth"],
    }


def test_failure_analysis_infers_blocked_status_for_old_style_failure_answer():
    answer = _answer("EXECUTION_REQUIRED — missing input file")

    analysis = _failure_analysis(answer)

    assert analysis["answer_status"] == "blocked"
    assert analysis["blocker_type"] == "unknown"
    assert "missing input file" in analysis["blocker_explanation"]


def test_run_with_critic_installs_missing_module_then_retries(tmp_path):
    context = _context(tmp_path)
    worker_first = _result()
    worker_second = _result("EXECUTION_REQUIRED — weights missing")
    critic_pass = SimpleNamespace(
        final_output=CriticReview(
            verdict="pass",
            reasoning="The worker retried after install and honestly reported a missing weight.",
        )
    )
    calls = {"count": 0}

    def fake_run_sync(agent, prompt, **kwargs):
        if kwargs.get("hooks") is not None:
            calls["count"] += 1
            if calls["count"] == 1:
                kwargs["hooks"].outputs.append("ModuleNotFoundError: No module named 'torch'")
                return worker_first
            kwargs["hooks"].outputs.append("FileNotFoundError: weights missing")
            return worker_second
        return critic_pass

    with (
        patch("research_agents.orchestration.Runner.run_sync", side_effect=fake_run_sync),
        patch("research_agents.orchestration._install_packages") as install,
    ):
        install.return_value = InstallEvent(
            attempt=1,
            modules=["torch"],
            packages=["torch"],
            command=["uv", "pip", "install", "torch"],
            exit_code=0,
            output="installed",
        )
        team_result = run_with_critic(
            context=context,
            question="Run the script.",
            ground_truth=None,
            entry_id="Q001",
            worker_model="gpt-5-mini-2025-08-07",
        )

    assert calls["count"] == 2
    assert install.called
    assert team_result.answer.final_answer == "EXECUTION_REQUIRED — weights missing"
    assert team_result.reviews[0].verdict == "pass"
