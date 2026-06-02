# Workflow-testing team: validation stage -> execution worker -> critic.
#
# This composition adds a dedicated Testing Agent before the existing
# worker+critic loop. The testing stage performs lightweight workflow
# validation and hands a typed TestingReport to the downstream worker,
# which then answers the question using the validated paths first.

from agents import Runner

from research_agents.agents.gap_detection_agent import (
    GapDetectionReport,
    build_gap_detection_input,
    canonicalize_gap_detection_report,
    create_gap_detection_agent,
)
from research_agents.agents.testing_agent import (
    TestingReport,
    canonicalize_testing_report,
    create_execution_agent_with_testing,
    create_testing_agent,
    format_testing_report_for_worker,
)
from research_agents.orchestration import TeamRunResult, ToolOutputCapture, run_with_critic
from research_agents.project import ResearchContext


def run_testing_worker_critic(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Validate workflows, execute, then run dedicated gap detection.

    The first stage is intentionally lightweight: it should de-risk the
    likely workflow(s) for the question, not fully reproduce the paper.
    Its typed report is prepended to the worker prompt so the ReAct worker
    can spend its turn budget executing promising paths instead of
    rediscovering obvious blockers from scratch. After execution, a
    separate gap-detection stage analyzes discrepancies using the
    testing report plus execution evidence rather than re-reading the repo.
    """
    testing_capture = ToolOutputCapture()
    testing_result = Runner.run_sync(
        create_testing_agent(model),
        question,
        context=context,
        max_turns=150,
        hooks=testing_capture,
    )
    report: TestingReport = canonicalize_testing_report(testing_result.final_output)

    worker_input = f"{format_testing_report_for_worker(report)}\n\nQUESTION:\n{question}"
    exec_result = run_with_critic(
        context=context,
        question=worker_input,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_execution_agent_with_testing,
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
    gap_result = Runner.run_sync(
        create_gap_detection_agent(model),
        gap_input,
        context=context,
        max_turns=20,
    )
    gap_report: GapDetectionReport = canonicalize_gap_detection_report(gap_result.final_output)

    return TeamRunResult(
        answer=exec_result.answer,
        worker_result=exec_result.worker_result,
        captures=[testing_capture, *exec_result.captures],
        reviews=exec_result.reviews,
        install_events=exec_result.install_events,
        testing_report=report.model_dump(),
        gap_report=gap_report.model_dump(),
    )
