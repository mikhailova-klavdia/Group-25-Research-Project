# Solo ReAct team: one worker agent, no critic, no install retry.
#
# This is the simplest possible composition.  It matches what
# ``react_main.py`` did with the legacy ``--no-critic`` flag, but exposed
# as a first-class team so it's selectable via ``--team solo`` like any
# other team.  No dependency on the orchestration module's retry logic;
# the worker either finishes or it doesn't.

from agents import Runner

from research_agents.agents.react_agent import create_react_agent
from research_agents.config import resolve_max_turns
from research_agents.orchestration import TeamRunResult, ToolOutputCapture, usage_from_result
from research_agents.project import ResearchContext


def run_solo(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,  # accepted for signature symmetry; unused
    entry_id: str,  # accepted for signature symmetry; unused
    model: str,
) -> TeamRunResult:
    """Run a single ReAct worker and return the result.

    Signature matches every other team's ``run`` function so the CLI
    dispatcher in ``react_main.py`` can call any team uniformly.
    ``ground_truth`` and ``entry_id`` are accepted but unused — only
    teams with a critic feed the ground truth in, and only the saved
    JSON cares about the entry id.

    Returns a ``TeamRunResult`` with empty ``reviews`` and
    ``install_events`` lists (this team has neither).
    """
    del ground_truth, entry_id  # explicitly mark them unused

    worker = create_react_agent(model=model)
    capture = ToolOutputCapture()
    result = Runner.run_sync(
        worker,
        question,
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
                agent_name=getattr(worker, "name", "ReAct worker"),
                model=model,
                attempt=1,
            )
        ],
    )
