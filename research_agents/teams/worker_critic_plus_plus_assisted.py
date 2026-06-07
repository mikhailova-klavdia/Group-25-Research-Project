"""worker-critic-plus-plus-assisted (RQ3): the plus-plus worker+critic team, but the
worker can call ``ask_human`` answered by an operator (the Claude Code session via
``SessionFileHuman``).

Same as ``worker-critic-assisted`` but with the plus-plus worker prompt. Isolates the
effect of operator assistance against the ``worker-critic-plus-plus`` baseline. The
operator channel is attached only when ``RESEARCH_ASK_HUMAN=session`` is set; otherwise
``ask_human`` degrades to NO_HUMAN_REPLY and the team runs autonomously.
"""

import os

from research_agents.agents.assisted_agents import create_react_agent_plus_plus_assisted
from research_agents.orchestration import TeamRunResult, run_with_critic
from research_agents.project import ResearchContext
from research_agents.session_human import SessionFileHuman


def run_worker_critic_plus_plus_assisted(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Attach the session operator (if enabled), then run worker+critic with the
    ask_human-equipped plus-plus worker."""
    if getattr(context, "human", None) is None and os.environ.get("RESEARCH_ASK_HUMAN") == "session":
        context.human = SessionFileHuman()
    return run_with_critic(
        context=context,
        question=question,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent_plus_plus_assisted,
    )
