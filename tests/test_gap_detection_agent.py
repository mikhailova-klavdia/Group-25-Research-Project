"""Tests for pure gap-detection helpers.

These tests cover the deterministic shaping logic around gap records and
the structured evidence payload passed into the dedicated gap agent.
"""

import json

from research_agents.agents.gap_detection_agent import (
    GapDetectionReport,
    build_gap_detection_input,
    build_gap_record,
    canonicalize_gap_detection_report,
)


def test_build_gap_record_normalizes_empty_and_duplicate_evidence():
    gap = build_gap_record(
        title=" Missing checkpoint ",
        gap_type="missing_artifact",
        severity="high",
        explanation=" A required model checkpoint is absent. ",
        likely_impact=" The main workflow cannot run. ",
        paper_reference="  Section 4.2  ",
        related_repo_files=["weights/model.ckpt", "weights/model.ckpt", " "],
        related_workflow="  inference  ",
        execution_evidence=[
            "FileNotFoundError: weights/model.ckpt",
            "FileNotFoundError: weights/model.ckpt",
            "",
        ],
        possible_remediation=" Provide a download link. ",
    )

    assert gap.title == "Missing checkpoint"
    assert gap.paper_reference == "Section 4.2"
    assert gap.related_workflow == "inference"
    assert gap.related_repo_files == ["weights/model.ckpt"]
    assert gap.execution_evidence == ["FileNotFoundError: weights/model.ckpt"]
    assert gap.possible_remediation == "Provide a download link."


def test_canonicalize_gap_detection_report_rebuilds_buckets_and_severity_counts():
    report = GapDetectionReport(
        overall_gap_assessment="Several gaps remain.",
        identified_gaps=[
            build_gap_record(
                title="Missing dataset split",
                gap_type="missing_parameter",
                severity="medium",
                explanation="The split definition is not provided.",
                likely_impact="Results cannot be compared fairly.",
            ),
            build_gap_record(
                title="Checkpoint absent",
                gap_type="missing_artifact",
                severity="high",
                explanation="The checkpoint file is missing.",
                likely_impact="The main model cannot be executed.",
            ),
            build_gap_record(
                title="Evaluation script diverges",
                gap_type="workflow_mismatch",
                severity="low",
                explanation="The repo workflow differs from the paper description.",
                likely_impact="Reported evaluation steps are hard to map to code.",
            ),
        ],
    )

    canonical = canonicalize_gap_detection_report(report)

    assert canonical.missing_parameters == ["Missing dataset split"]
    assert canonical.missing_artifacts == ["Checkpoint absent"]
    assert canonical.paper_repo_mismatches == ["Evaluation script diverges"]
    assert canonical.severity_summary.high == 1
    assert canonical.severity_summary.medium == 1
    assert canonical.severity_summary.low == 1


def test_build_gap_detection_input_serializes_prior_stage_evidence():
    prompt = build_gap_detection_input(
        question="Why did reproduction fail?",
        testing_report={"overall_status": "partial"},
        execution_answer={"final_answer": "EXECUTION_REQUIRED — missing weights"},
        execution_tool_outputs=["Exit code: 1\nFileNotFoundError: weights/model.ckpt"],
        critic_reviews=[{"verdict": "pass"}],
        install_events=[{"packages": ["torch"], "exit_code": 0}],
    )

    assert "GapDetectionReport" in prompt
    payload = json.loads(prompt.split("\n\n", maxsplit=1)[1])
    assert payload["question"] == "Why did reproduction fail?"
    assert payload["testing_report"]["overall_status"] == "partial"
    assert payload["critic_reviews"][0]["verdict"] == "pass"
    assert payload["install_events"][0]["packages"] == ["torch"]
