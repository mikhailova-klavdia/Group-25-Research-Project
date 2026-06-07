# Workflow-testing team: validation stage -> execution worker -> critic.
#
# This composition adds a dedicated Testing Agent before the existing
# worker+critic loop. The testing stage performs lightweight workflow
# validation and hands a typed TestingReport to the downstream worker,
# which then answers the question using the validated paths first.

from agents import Runner

from research_agents.agents.extraction_agent import (
    ExtractionReport,
    canonicalize_extraction_report,
    create_extraction_agent,
    format_extraction_report_for_downstream,
)
from research_agents.agents.gap_detection_agent import (
    GapDetectionReport,
    build_gap_detection_input,
    canonicalize_gap_detection_report,
    create_gap_detection_agent,
)
from research_agents.agents.gate_agent import (
    GateDecision,
    apply_gate_verdict,
    build_gate_input,
    create_gate_agent,
)
from research_agents.agents.react_agent import create_react_agent_plus_plus
from research_agents.agents.testing_agent import (
    TestingReport,
    canonicalize_testing_report,
    create_testing_agent,
    format_testing_report_for_worker,
)
from research_agents.orchestration import (
    TeamRunResult,
    ToolOutputCapture,
    run_with_critic,
    usage_from_result,
)
from research_agents.project import ResearchContext


def _announce_stage(stage_name: str) -> None:
    """Print a short stage marker so long team runs do not look frozen.

    The testing-worker-critic team chains multiple structured-agent calls
    before the final answer appears. Without explicit stage markers, a
    user watching stdout cannot tell whether the run is still progressing
    or which stage is currently spending tokens/time.
    """
    print(f"[team/testing-worker-critic] {stage_name}...")


def run_testing_worker_critic(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Extract workflows, validate them, execute, then run gap detection.

    Extraction produces a stable paper/repo inventory first. The testing
    stage validates those extracted workflows instead of rediscovering
    them from scratch, and the worker receives both reports as structured
    prompt context before execution-time reasoning begins. After the
    worker+critic loop finishes, a dedicated gap-detection stage
    summarizes paper/repo/execution discrepancies from the structured
    evidence rather than re-reading the repo.
    """
    _announce_stage("Extraction")
    extraction_capture = ToolOutputCapture()
    extraction_result = Runner.run_sync(
        create_extraction_agent(model),
        question,
        context=context,
        max_turns=150,
        hooks=extraction_capture,
    )
    extraction_usage = usage_from_result(
        extraction_result,
        stage="extraction",
        agent_name="Extraction Agent",
        model=model,
    )
    extraction_report: ExtractionReport = canonicalize_extraction_report(
        extraction_result.final_output
    )

    extraction_preamble = format_extraction_report_for_downstream(extraction_report)
    _announce_stage("Workflow testing")
    testing_capture = ToolOutputCapture()
    testing_result = Runner.run_sync(
        create_testing_agent(model),
        f"{extraction_preamble}\n\nQUESTION:\n{question}",
        context=context,
        max_turns=150,
        hooks=testing_capture,
    )
    testing_usage = usage_from_result(
        testing_result,
        stage="workflow_testing",
        agent_name="Workflow Testing Agent",
        model=model,
    )
    report: TestingReport = canonicalize_testing_report(testing_result.final_output)

    worker_input = (
        f"{extraction_preamble}\n\n"
        f"{format_testing_report_for_worker(report)}\n\n"
        f"QUESTION:\n{question}"
    )
    _announce_stage("Execution worker + critic")
    exec_result = run_with_critic(
        context=context,
        question=worker_input,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent_plus_plus,
    )
    gap_input = build_gap_detection_input(
        question=question,
        testing_report=report.model_dump(),
        execution_answer=exec_result.answer.model_dump(),
        execution_tool_outputs=exec_result.final_capture.outputs,
        critic_reviews=[
            review.model_dump() if hasattr(review, "model_dump") else review
            for review in exec_result.reviews
        ],
        install_events=[
            {
                "attempt": event.attempt,
                "modules": event.modules,
                "packages": event.packages,
                "exit_code": event.exit_code,
                "output": event.output,
            }
            for event in exec_result.install_events
        ],
    )
    _announce_stage("Gap detection")
    gap_result = Runner.run_sync(
        create_gap_detection_agent(model),
        gap_input,
        context=context,
        max_turns=20,
    )
    gap_usage = usage_from_result(
        gap_result,
        stage="gap_detection",
        agent_name="Gap Detection Agent",
        model=model,
    )
    gap_report: GapDetectionReport = canonicalize_gap_detection_report(gap_result.final_output)

    _announce_stage("Gate")
    gate_input = build_gate_input(
        question=question,
        final_answer=exec_result.answer.final_answer,
        answer_status=exec_result.answer.answer_status,
        gap_report=gap_report.model_dump(),
    )
    gate_result = Runner.run_sync(
        create_gate_agent(model),
        gate_input,
        context=context,
        max_turns=5,
    )
    gate_usage = usage_from_result(
        gate_result,
        stage="gate",
        agent_name="Gate Agent",
        model=model,
    )
    gate_decision: GateDecision = gate_result.final_output
    final_answer = apply_gate_verdict(exec_result.answer, gate_decision)

    return TeamRunResult(
        answer=final_answer,
        worker_result=exec_result.worker_result,
        captures=[extraction_capture, testing_capture, *exec_result.captures],
        reviews=exec_result.reviews,
        install_events=exec_result.install_events,
        extraction_report=extraction_report.model_dump(),
        testing_report=report.model_dump(),
        gap_report=gap_report.model_dump(),
        gate_decision=gate_decision.model_dump(),
        agent_usages=[
            extraction_usage,
            testing_usage,
            *exec_result.agent_usages,
            gap_usage,
            gate_usage,
        ],
    )
