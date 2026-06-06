# Worker + critic team with the improved-variant worker prompt.
#
# Same orchestration shape as ``worker-critic`` (LLM critic on top, with
# deterministic missing-module install retry), but the worker is built
# from ``create_react_agent_improved`` instead of ``create_react_agent``.
# The team's ``apply_setup=True`` in the registry also tells
# ``resolve_project`` to honor each paper's ``.research_config.toml``
# ``[setup]`` block, so model-weight downloads (PPLM) and framework
# cache warmups (ESM-2) happen once at venv-creation time.
#
# Two opt-in changes ride together because they're complementary: the
# setup scripts produce the artifacts the improved worker prompt now
# encourages it to use.

from research_agents.agents.react_agent import create_react_agent_improved
from research_agents.orchestration import TeamRunResult, run_with_critic
from research_agents.project import ResearchContext


def run_worker_critic_plus(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Run worker + critic with the improved worker prompt.

    Differs from ``run_worker_critic`` in exactly one line — the
    ``worker_factory`` argument.  Keeping the rest of the orchestration
    behavior identical makes the A/B between teams a single-prompt
    delta, which is exactly what we want for the comparison.
    """
    return run_with_critic(
        context=context,
        question=question,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent_improved,
        team_name="worker-critic-plus",
    )
