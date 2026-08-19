# Tool for reading the per-paper help file (AGENT_HINTS.md).
#
# RQ3 (README-assisted variant): a steering README is placed alongside the repo and its
# path is injected via the SDK context (``ResearchContext.help_path``), so the LLM never
# sees the path — it just calls ``read_help``.  The file holds *tips* for the paper's tasks
# (where data/weights live, conceptual gotchas), never the answer.  When no help file is
# attached the tool returns a clear note so non-assisted runs are unaffected.

from pathlib import Path

from agents import RunContextWrapper, function_tool

from research_agents.project import ResearchContext


# Returned when no help file is attached/found, phrased so the agent simply proceeds
# on its own rather than treating it as an error.
NO_HELP_TEXT = "No help file is attached to this task. Proceed using the paper and repo."


def read_help_text(help_path: "str | Path | None") -> str:
    """Pure helper behind ``read_help`` (unit-tested directly).

    Returns the help file's contents, or ``NO_HELP_TEXT`` when no path is set or the file is
    absent/unreadable.  Kept free of the SDK so the read + degrade paths can be tested
    without booting a run.
    """
    if not help_path:
        return NO_HELP_TEXT
    p = Path(help_path)
    if not p.is_file():
        return NO_HELP_TEXT
    try:
        text = p.read_text(encoding="utf-8").strip()
    except OSError:
        return NO_HELP_TEXT
    return text or NO_HELP_TEXT


@function_tool
def read_help(context: RunContextWrapper[ResearchContext]) -> str:
    """Read the task-specific help file (expert tips for this paper) and return its text.

    Call this FIRST. It returns hints gathered from prior attempts — where data/weights
    already live, which dependencies to install, and pitfalls to avoid. The hints are
    guidance only (never the final answer); you must still run the real workflow.
    """
    return read_help_text(getattr(context.context, "help_path", None))
