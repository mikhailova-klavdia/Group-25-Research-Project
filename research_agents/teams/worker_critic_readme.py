"""worker-critic-readme (RQ3, static-help): the lean worker+critic team, but the worker is
given a per-paper help README of steering tips (``AGENT_HINTS.md``, placed alongside the
repo by the runner). The help is exposed two ways: via the ``read_help`` tool and — for
reliability — injected as a "TASK HINTS" preamble to the worker's input.

This isolates the effect of the static help against the plain ``worker-critic`` baseline:
identical orchestration and critic, identical worker prompt except for the appended
read-help section, plus the hints prepended to the question. When no help file is present,
``read_help_text`` returns the no-help sentinel and nothing is prepended, so the team
behaves exactly like ``worker-critic``.
"""

from research_agents.agents.readme_agents import create_react_agent_readme
from research_agents.orchestration import TeamRunResult, run_with_critic
from research_agents.project import ResearchContext
from research_agents.tools.help_tools import NO_HELP_TEXT, read_help_text


def _with_hints(context: ResearchContext, question: str) -> str:
    """Prepend the paper's help text to the question as an authoritative TASK HINTS block.

    Falls back to the plain question when no help file is attached, so non-assisted runs are
    unaffected.
    """
    help_text = read_help_text(getattr(context, "help_path", None))
    if help_text == NO_HELP_TEXT:
        return question
    # Record (on the context) that help was actually injected for this question, so the
    # saved chain can attest to it — the preamble itself is not stored in the record.
    context.help_injected = True
    return (
        "TASK HINTS (expert guidance for this paper — tips only, NOT the answer; "
        "follow them and still run the real workflow):\n"
        f"{help_text}\n"
        "=== END TASK HINTS ===\n\n"
        f"{question}"
    )


def run_worker_critic_readme(
    context: ResearchContext,
    question: str,
    ground_truth: str | None,
    entry_id: str,
    model: str,
) -> TeamRunResult:
    """Run worker+critic with the help README injected and the read_help-equipped worker."""
    return run_with_critic(
        context=context,
        question=_with_hints(context, question),
        ground_truth=ground_truth,
        entry_id=entry_id,
        worker_model=model,
        worker_factory=create_react_agent_readme,
    )
