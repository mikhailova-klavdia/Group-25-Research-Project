# Worker + critic team with the plus-plus variant worker prompt.
#
# Same orchestration shape as ``worker-critic-plus`` (LLM critic on top,
# with deterministic missing-module install retry and up-front setup
# scripts), but the worker is built from ``create_react_agent_plus_plus``
# instead of ``create_react_agent_improved``.  REACT_INSTRUCTIONS_PLUS_PLUS
# is a fully independent prompt (not derived from the improved variant) with
# its own repo-first search strategy, static-file gate, and mandatory
# second-strategy rule before giving up.

from research_agents.agents.react_agent import create_react_agent_plus_plus
from research_agents.orchestration import TeamRunResult, run_with_critic
from research_agents.project import ResearchContext


def run_worker_critic_plus_plus(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Run worker + critic with the plus-plus variant worker prompt.

    Differs from ``run_worker_critic_plus`` in exactly one line — the
    ``worker_factory`` argument.  All orchestration behavior (critic,
    install retry, max_retries) is inherited unchanged.
    """
    return run_with_critic(
        context=context,
        question=question,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent_plus_plus,
        needs_execution=True,
        team_name="worker-critic-plus-plus",
    )
