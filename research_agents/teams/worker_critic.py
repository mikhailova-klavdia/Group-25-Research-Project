# Worker + critic team — reproduces the colleague's 2026-05-28 baseline.
#
# Thin wrapper around ``orchestration.run_with_critic`` that pins the
# worker factory to ``create_react_agent`` (the baseline prompt).  No
# setup scripts; the per-paper venv is created without honoring the
# ``[setup]`` table.  Use ``--team worker-critic`` to invoke.

from research_agents.agents.react_agent import create_react_agent
from research_agents.orchestration import TeamRunResult, run_with_critic
from research_agents.project import ResearchContext


def run_worker_critic(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Run worker + critic with the baseline ReAct prompt.

    Pins ``worker_factory=create_react_agent`` so even if a future
    refactor changes the orchestration default, this team's behavior
    remains anchored to the 2026-05-28 baseline.  The critic uses
    ``DEFAULT_MODEL`` (gpt-4.1-mini) regardless of which model the
    worker uses — that's the colleague's original choice and we don't
    second-guess it here.
    """
    return run_with_critic(
        context=context,
        question=question,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent,
    )
