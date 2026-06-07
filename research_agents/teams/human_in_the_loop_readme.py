"""human-in-the-loop-readme (RQ3, static-help): the autonomous HITL crew, given a per-paper
help README.

The HITL team is a multi-stage crew (triage -> read-only | setup -> execution+critic ->
integrity guard). Rather than rewire any stage, this variant simply injects the paper's help
text as a "TASK HINTS" preamble into the question via ``_with_hints``; ``run_human_in_the_loop``
then propagates that question through every stage (triage, setup, and the execution worker's
input). So the HITL architecture is UNCHANGED — only the help is added — which keeps the
comparison against the plain ``human-in-the-loop`` baseline clean. ``_with_hints`` also records
``help_injected`` on the context for the saved audit flag. With no help file present it is a
no-op, so the team behaves exactly like ``human-in-the-loop``.

Run headless via ``react_main --team human-in-the-loop-readme`` (ask_human degrades to
autonomous), matching the autonomous HITL baseline.
"""

from research_agents.orchestration import TeamRunResult
from research_agents.project import ResearchContext
from research_agents.teams.human_in_the_loop import run_human_in_the_loop
from research_agents.teams.worker_critic_readme import _with_hints


def run_human_in_the_loop_readme(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Run the autonomous HITL crew with the per-paper help injected into the question."""
    return run_human_in_the_loop(
        context,
        _with_hints(context, question),
        ground_truth,
        entry_id,
        model,
    )
