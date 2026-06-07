"""worker-critic-assisted (RQ3): the lean worker+critic team, but the worker can call
``ask_human`` and the questions are answered by an operator (the Claude Code session via
``SessionFileHuman``) — no triage/setup, no extra scaffolding beyond the ask_human tool.

This isolates the effect of operator assistance against the plain ``worker-critic``
baseline: identical orchestration and critic, identical prompt except for the appended
ask-human section, plus a human channel on the context.

The operator channel is attached only when ``RESEARCH_ASK_HUMAN=session`` is set (the
interactive driver sets it). Without it, ``context.human`` stays None and ``ask_human``
degrades to NO_HUMAN_REPLY, so the team still runs autonomously.
"""

import os

from research_agents.agents.assisted_agents import create_react_agent_assisted
from research_agents.orchestration import TeamRunResult, run_with_critic
from research_agents.project import ResearchContext
from research_agents.session_human import SessionFileHuman


def run_worker_critic_assisted(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Attach the session operator (if enabled), then run worker+critic with the
    ask_human-equipped baseline worker."""
    if getattr(context, "human", None) is None and os.environ.get("RESEARCH_ASK_HUMAN") == "session":
        context.human = SessionFileHuman()
    return run_with_critic(
        context=context,
        question=question,
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent_assisted,
    )
