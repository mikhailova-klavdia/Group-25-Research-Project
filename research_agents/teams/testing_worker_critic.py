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
    """Extract workflows, validate them, then answer via the worker+critic loop.

    Extraction produces a stable paper/repo inventory first.  The testing
    stage then validates those extracted workflows instead of rediscovering
    them from scratch, and the worker receives both reports as structured
    prompt context before execution-time reasoning begins.
    """
    extraction_capture = ToolOutputCapture()
    extraction_result = Runner.run_sync(
        create_extraction_agent(model),
        question,
        context=context,
        max_turns=150,
        hooks=extraction_capture,
    )
    extraction_report: ExtractionReport = canonicalize_extraction_report(
        extraction_result.final_output
    )

    extraction_preamble = format_extraction_report_for_downstream(extraction_report)
    testing_capture = ToolOutputCapture()
    testing_result = Runner.run_sync(
        create_testing_agent(model),
        f"{extraction_preamble}\n\nQUESTION:\n{question}",
        context=context,
        max_turns=150,
        hooks=testing_capture,
    )
    report: TestingReport = canonicalize_testing_report(testing_result.final_output)

    worker_input = (
        f"{extraction_preamble}\n\n"
        f"{format_testing_report_for_worker(report)}\n\n"
        f"QUESTION:\n{question}"
    )
    exec_result = run_with_critic(
        context=context,
        question=worker_input,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_execution_agent_with_testing,
    )

    return TeamRunResult(
        answer=exec_result.answer,
        worker_result=exec_result.worker_result,
        captures=[extraction_capture, testing_capture, *exec_result.captures],
        reviews=exec_result.reviews,
        install_events=exec_result.install_events,
        extraction_report=extraction_report.model_dump(),
        testing_report=report.model_dump(),
    )
