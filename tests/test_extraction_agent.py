"""Tests for deterministic extraction-report helpers and stage wiring.

These tests cover the pure helper logic that canonicalizes and formats
workflow extraction output, plus the team composition seam that runs
extraction before testing and execution.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_agents.agents.critic_agent import CriticReview
from research_agents.agents.extraction_agent import (
    ExtractionReport,
    PaperRepoLink,
    WorkflowDefinition,
    canonicalize_extraction_report,
    format_extraction_report_for_downstream,
)
from research_agents.agents.react_agent import ReActAnswer, ReActStep
from research_agents.agents.testing_agent import (
    TestingReport as WorkflowTestingReport,
    WorkflowValidation,
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


def _extraction_report() -> ExtractionReport:
    return ExtractionReport(
        paper_summary="The paper predicts protein interactions.",
        research_objective="Predict binding affinity from paired sequences.",
        workflow_definitions=[
            WorkflowDefinition(
                workflow_name="affinity-prediction",
                paper_reference="Section 4.1",
                repo_entrypoints=["notebooks/run_affinity.py"],
                config_files=["configs/affinity.yaml"],
                required_inputs=["data/receptor.fasta", "data/ligand.fasta"],
                expected_outputs=["output/affinity.json"],
                dependency_hints=["torch", "cpu or gpu"],
                ambiguity_notes=["Weights path is implied, not documented."],
                notes="README mentions an affinity example.",
            )
        ],
        paper_repo_links=[
            PaperRepoLink(
                paper_reference="Table 1",
                repo_assets=["results/table1.csv"],
                rationale="Result filename matches the table naming in the README.",
            )
        ],
        notes="Extraction completed from paper plus README.",
    )


def _testing_report() -> WorkflowTestingReport:
    return WorkflowTestingReport(
        overall_status="partial",
        workflows=[
            WorkflowValidation(
                workflow_name="affinity-prediction",
                status="partial",
                files_staged=["notebooks/run_affinity.py"],
                commands_run=["python notebooks/run_affinity.py --help"],
                observed_outputs=["usage text printed"],
                confidence_notes="CLI loads but weights are still unresolved.",
            )
        ],
        recommendations=["Start with the affinity workflow."],
        notes="Testing followed the extraction report entrypoints.",
    )


def test_canonicalize_extraction_report_derives_aggregate_fields():
    report = canonicalize_extraction_report(_extraction_report())

    assert report.identified_experiments == ["affinity-prediction"]
    assert report.repo_entrypoints == [
        "notebooks/run_affinity.py",
        "results/table1.csv",
    ]
    assert report.config_files == ["configs/affinity.yaml"]
    assert report.input_artifacts == ["data/receptor.fasta", "data/ligand.fasta"]
    assert report.expected_outputs == ["output/affinity.json"]
    assert report.ambiguous_mappings == ["Weights path is implied, not documented."]


def test_format_extraction_report_for_downstream_includes_workflow_details():
    text = format_extraction_report_for_downstream(_extraction_report())

    assert "EXTRACTION REPORT" in text
    assert "research_objective: Predict binding affinity from paired sequences." in text
    assert "affinity-prediction" in text
    assert "entrypoints=notebooks/run_affinity.py" in text
    assert "inputs=data/receptor.fasta, data/ligand.fasta" in text


def test_testing_team_runs_extraction_before_testing_and_worker():
    root = Path("tests/.tmp-extraction-team")
    context = _context(root)
    extraction_result = SimpleNamespace(final_output=_extraction_report())
    testing_result = SimpleNamespace(final_output=_testing_report())
    final_answer = ReActAnswer(
        chain=[
            ReActStep(
                step=1,
                thought="Start from the extracted affinity workflow.",
                action='execute_command("python notebooks/run_affinity.py")',
                observation="Exit code: 0",
                reflection="The affinity workflow is the correct path.",
            )
        ],
        final_answer="42",
    )
    exec_result = TeamRunResult(
        answer=final_answer,
        worker_result=SimpleNamespace(final_output=final_answer),
        captures=[],
        reviews=[CriticReview(verdict="pass", reasoning="Grounded in execution.")],
        install_events=[],
    )

    with (
        patch("research_agents.teams.testing_worker_critic.Runner.run_sync") as run_sync,
        patch("research_agents.teams.testing_worker_critic.run_with_critic") as run_with_critic,
    ):
        run_sync.side_effect = [extraction_result, testing_result]
        run_with_critic.return_value = exec_result

        result = run_testing_worker_critic(
            context=context,
            question="Predict affinity for the paired FASTA files.",
            ground_truth="42",
            entry_id="Q001",
            model="gpt-5-mini-2025-08-07",
        )

    assert result.answer.final_answer == "42"
    assert len(result.captures) == 2
    assert result.extraction_report is not None
    assert result.extraction_report["identified_experiments"] == ["affinity-prediction"]
    assert result.testing_report is not None
    testing_prompt = run_sync.call_args_list[1].args[1]
    worker_prompt = run_with_critic.call_args.kwargs["question"]
    assert "EXTRACTION REPORT" in testing_prompt
    assert "affinity-prediction" in testing_prompt
    assert "EXTRACTION REPORT" in worker_prompt
    assert "WORKFLOW TESTING REPORT" in worker_prompt
