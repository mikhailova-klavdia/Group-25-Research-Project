"""worker-critic-plus-plus-readme (RQ3, static-help): the plus-plus worker+critic team with
a per-paper help README of steering tips (``AGENT_HINTS.md``, placed alongside the repo).

Same as ``worker-critic-readme`` but with the plus-plus worker prompt. Isolates the effect
of the static help against the ``worker-critic-plus-plus`` baseline. The help is exposed via
the ``read_help`` tool and injected as a "TASK HINTS" preamble; with no help file present it
degrades to the plain plus-plus behavior.
"""

from research_agents.agents.readme_agents import create_react_agent_plus_plus_readme
from research_agents.orchestration import TeamRunResult, run_with_critic
from research_agents.project import ResearchContext
from research_agents.teams.worker_critic_readme import _with_hints


def run_worker_critic_plus_plus_readme(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Run worker+critic with the help README injected and the plus-plus read_help worker."""
    return run_with_critic(
        context=context,
        question=_with_hints(context, question),
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent_plus_plus_readme,
    )
