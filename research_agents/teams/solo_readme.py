"""solo-readme (RQ3, static-help): the single-worker solo team, given a per-paper help README.

Mirrors ``run_solo`` exactly (one ReAct worker, no critic, no install retry) but swaps in the
read_help-equipped worker (``create_react_agent_readme``) and injects the paper's help text as
a "TASK HINTS" preamble via ``_with_hints``. Isolates the effect of the static help against the
plain ``solo`` baseline. With no help file present, ``_with_hints`` is a no-op, so it behaves
exactly like ``solo``.
"""

from agents import Runner

from research_agents.agents.readme_agents import create_react_agent_readme
from research_agents.config import resolve_max_turns
from research_agents.orchestration import TeamRunResult, ToolOutputCapture, usage_from_result
from research_agents.project import ResearchContext
from research_agents.teams.worker_critic_readme import _with_hints


def run_solo_readme(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,  # accepted for signature symmetry; unused
    entry_id: str,  # accepted for signature symmetry; unused
    model: str,
) -> TeamRunResult:
    """Run a single README-assisted ReAct worker (no critic) and return the result."""
    del ground_truth, entry_id

    worker = create_react_agent_readme(model=model)
    capture = ToolOutputCapture()
    result = Runner.run_sync(
        worker,
        _with_hints(context, question),
        context=context,
        max_turns=resolve_max_turns(),
        hooks=capture,
    )
    return TeamRunResult(
        answer=result.final_output,
        worker_result=result,
        captures=[capture],
        reviews=[],
        install_events=[],
        agent_usages=[
            usage_from_result(
                result,
                stage="execution_worker",
                agent_name=getattr(worker, "name", "ReAct worker (readme)"),
                model=model,
                attempt=1,
            )
        ],
    )
