"""Tests for the workflow-testing agent helpers and team wiring.

These cover the deterministic parts of the new testing stage: aggregate
status calculation, worker handoff formatting, and the team composition
that runs testing before the existing worker+critic loop.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_agents.agents.gap_detection_agent import GapDetectionReport, GapRecord
from research_agents.agents.critic_agent import CriticReview
from research_agents.agents.react_agent import ReActAnswer, ReActStep
from research_agents.agents.testing_agent import (
    TestingReport as WorkflowTestingReport,
    WorkflowValidation,
    canonicalize_testing_report,
    format_testing_report_for_worker,
)
from research_agents.orchestration import TeamRunResult
from research_agents.project import ResearchContext
from research_agents.teams.testing_worker_critic import run_testing_worker_critic


def _context(root: Path) -> ResearchContext:
    project = root / "paper"
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


def _testing_report(status: str) -> WorkflowTestingReport:
    return WorkflowTestingReport(
        overall_status="blocked",
        workflows=[
            WorkflowValidation(
                workflow_name="example-workflow",
                status=status,
                files_staged=["scripts/run.py"],
                commands_run=["python scripts/run.py --help"],
                observed_outputs=["usage text printed"],
                confidence_notes="smoke test completed",
            )
        ],
        recommendations=["Use the staged script first."],
        notes="Derived from the benchmark question.",
    )


def _gap_report() -> GapDetectionReport:
    return GapDetectionReport(
        overall_gap_assessment="One high-severity missing artifact blocks full reproduction.",
        identified_gaps=[
            GapRecord(
                title="Missing checkpoint",
                gap_type="missing_artifact",
                severity="high",
                related_repo_files=["weights/model.ckpt"],
                execution_evidence=["FileNotFoundError: weights/model.ckpt"],
                explanation="The validated workflow expects a checkpoint that is absent.",
                likely_impact="The main inference path cannot be reproduced.",
                possible_remediation="Provide the checkpoint or a documented download link.",
            )
        ],
        evidence_sources=["testing_report.workflows", "execution_answer.blocker_evidence"],
        recommended_followups=["Check whether the paper artifacts cache already has the weight."],
    )


def test_canonicalize_testing_report_marks_ready_when_any_workflow_validates():
    report = canonicalize_testing_report(_testing_report("validated"))

    assert report.overall_status == "ready"
    assert report.validated_workflows == ["example-workflow"]
    assert report.partial_workflows == []
    assert report.blocked_workflows == []
    assert report.failed_workflows == []


def test_canonicalize_testing_report_marks_partial_without_full_validation():
    report = canonicalize_testing_report(_testing_report("partial"))

    assert report.overall_status == "partial"
    assert report.validated_workflows == []
    assert report.partial_workflows == ["example-workflow"]


def test_format_testing_report_for_worker_includes_actionable_evidence():
    text = format_testing_report_for_worker(_testing_report("validated"))

    assert "overall_status: ready" in text
    assert "validated: example-workflow" in text
    assert "commands=python scripts/run.py --help" in text
    assert "Use the validated workflows first." in text


def test_testing_team_runs_validation_before_worker_critic():
    root = Path("tests/.tmp-testing-team")
    context = _context(root)
    testing_result = SimpleNamespace(final_output=_testing_report("validated"))
    gap_result = SimpleNamespace(final_output=_gap_report())
    final_answer = ReActAnswer(
        chain=[
            ReActStep(
                step=1,
                thought="Use the validated workflow first.",
                action='execute_command("python scripts/run.py")',
                observation="Exit code: 0",
                reflection="The workflow ran successfully.",
            )
        ],
        final_answer="42",
    )
    exec_result = TeamRunResult(
        answer=final_answer,
        worker_result=SimpleNamespace(final_output=final_answer),
        captures=[SimpleNamespace(outputs=["Exit code: 0\nworkflow ok"])],
        reviews=[CriticReview(verdict="pass", reasoning="Grounded in execution.")],
        install_events=[],
    )

    with (
        patch("research_agents.teams.testing_worker_critic.Runner.run_sync") as run_sync,
        patch("research_agents.teams.testing_worker_critic.run_with_critic") as run_with_critic,
    ):
        run_sync.side_effect = [testing_result, gap_result]
        run_with_critic.return_value = exec_result

        result = run_testing_worker_critic(
            context=context,
            question="Run the example workflow.",
            ground_truth="42",
            entry_id="Q001",
            model="gpt-5-mini-2025-08-07",
        )

    assert result.answer.final_answer == "42"
    assert len(result.captures) == 2
    assert result.testing_report is not None
    assert result.gap_report is not None
    assert result.testing_report["overall_status"] == "ready"
    assert result.testing_report["validated_workflows"] == ["example-workflow"]
    assert result.gap_report["missing_artifacts"] == ["Missing checkpoint"]
    worker_prompt = run_with_critic.call_args.kwargs["question"]
    assert "WORKFLOW TESTING REPORT" in worker_prompt
    assert "validated: example-workflow" in worker_prompt
