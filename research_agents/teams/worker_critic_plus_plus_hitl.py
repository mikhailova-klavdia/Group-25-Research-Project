"""Worker-critic-plus-plus team augmented with a ClaudeHuman operator channel.

Merges the plus-plus ReAct prompt with the three-stage HITL pipeline
(triage → setup → execution) so every ask_human call is answered by Claude
rather than blocked on terminal input or returned as NO_HUMAN_REPLY.  This lets
the team run fully autonomously on batch evals while still making the practical
judgment calls that previously required a human operator: choosing open model
variants, resolving version conflicts, approving expensive steps, interpreting
ambiguous questions, etc.

The run function is a thin wrapper: it attaches a ClaudeHuman to the context and
delegates entirely to run_human_in_the_loop, which owns all stage logic.
"""

from research_agents.claude_human import ClaudeHuman
from research_agents.orchestration import TeamRunResult
from research_agents.project import ResearchContext
from research_agents.teams.human_in_the_loop import run_human_in_the_loop


def run_worker_critic_plus_plus_hitl(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Attach a ClaudeHuman to the context then run the full HITL pipeline.

    Setting context.human before calling run_human_in_the_loop ensures every
    ask_human call inside the triage, setup, and execution stages routes to
    Claude instead of returning NO_HUMAN_REPLY.  The ResearchContext dataclass
    is mutable (not frozen), so the assignment is safe.  The rest of the
    orchestration — triage routing, setup retries, worker+critic loop, and
    integrity guard — is unchanged from the existing human-in-the-loop team.
    """
    # Only attach ClaudeHuman when no human channel is already present (batch/headless
    # runs via react_main).  Interactive runs via hitl_main pre-attach a ConsoleHuman,
    # and overwriting it would silence the terminal prompts.
    if getattr(context, "human", None) is None:
        context.human = ClaudeHuman()
    return run_human_in_the_loop(context, question, ground_truth, entry_id, model)
