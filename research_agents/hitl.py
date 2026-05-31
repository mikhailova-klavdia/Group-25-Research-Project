"""Human-in-the-loop plumbing for the ``human-in-the-loop`` agent team.

A *human channel* lets agents pause mid-run and ask the operator for help
(a credential, a concrete workaround, a go/no-go) instead of silently
giving up.  The channel is carried on ``ResearchContext.human`` so the
``ask_human`` tool reads it from the SDK-injected context — exactly like
every other tool reads paths from the context, and without the LLM ever
seeing it.

When no channel is attached (the existing headless/batch ``react_main``
path), ``ask_human`` degrades to a clear "proceed autonomously" reply, so
the existing teams keep their fully-automatic behaviour and never block on
input that will never arrive.
"""

from typing import TYPE_CHECKING, Protocol

from agents import RunContextWrapper, function_tool

from research_agents.project import ResearchContext

if TYPE_CHECKING:
    # Type-only import: ``apply_integrity_guard`` duck-types ``model_copy`` at
    # runtime, so we never import the agent module (and its SDK Agent build)
    # just for a hint, and there is no import cycle.
    from research_agents.agents.react_agent import ReActAnswer


# Returned to the agent when it calls ``ask_human`` in a run with no human
# attached.  Phrased as an instruction (not just "none") so the model keeps
# working on its own instead of stalling for input that cannot come.
NO_HUMAN_REPLY = (
    "NO_HUMAN_AVAILABLE: no operator is attached to this run. Proceed "
    "autonomously using your best judgment and standard practice; do not wait."
)


class HumanChannel(Protocol):
    """Anything that can answer an agent's question from a human.

    Kept as a ``Protocol`` (structural) rather than a base class so the
    console reader, a test fake, or any other implementation can satisfy it
    without a shared import or inheritance.
    """

    def ask(self, question: str, *, agent: str = "") -> str:
        """Return the human's reply to ``question`` (``agent`` is a label)."""
        ...


class ConsoleHuman:
    """Human channel backed by the terminal (stdin/stdout); used by ``hitl_main``.

    Prints the agent's question inside a visible banner so the operator can
    tell an agent-question apart from ordinary log output, then blocks on
    ``input()`` until they reply.  A closed/piped stdin (``EOFError``) is
    treated as "no human available" so a non-interactive invocation does
    not crash.
    """

    def ask(self, question: str, *, agent: str = "") -> str:
        """Prompt the operator on the terminal and return their typed reply."""
        who = f" ({agent})" if agent else ""
        print(f"\n┌─ I need a hand{who} " + "─" * max(0, 48 - len(who)))
        for line in question.splitlines() or [question]:
            print(f"│ {line}")
        print("└" + "─" * 64)
        try:
            reply = input("➜ your answer: ").strip()
        except EOFError:
            return NO_HUMAN_REPLY
        return reply or "(no answer given; proceed with your best judgment)"


class FakeHuman:
    """Scripted human channel for tests — no stdin, no LLM.

    Pops replies in order; once the script is exhausted it returns a fixed
    fallback rather than blocking, so a test that triggers more asks than it
    scripted fails predictably instead of hanging.  ``asked`` records the
    questions for assertions.
    """

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.asked: list[str] = []

    def ask(self, question: str, *, agent: str = "") -> str:
        """Record the question and return the next scripted reply."""
        self.asked.append(question)
        if self._replies:
            return self._replies.pop(0)
        return "(no more scripted replies)"


class Reporter(Protocol):
    """Receives short progress updates so a front-end can show live activity.

    The team writes to this (when one is attached to the context) at stage
    boundaries and around tool calls. It is ``None`` on headless/batch runs,
    which means total silence — so ``react_main`` / batch output is unchanged.
    """

    def stage(self, message: str) -> None:
        """Announce a new high-level stage (e.g. 'Setting up the environment…')."""
        ...

    def detail(self, message: str) -> None:
        """Announce a finer-grained step (e.g. 'running a command…')."""
        ...


class ConsoleReporter:
    """Reporter that prints friendly progress lines to the terminal (``hitl_main``)."""

    def stage(self, message: str) -> None:
        """Print a high-level stage line."""
        print(f"\n▸ {message}", flush=True)

    def detail(self, message: str) -> None:
        """Print an indented finer-grained step line."""
        print(f"   · {message}", flush=True)


def ask_human_text(
    human: HumanChannel | None,
    question: str,
    *,
    agent: str = "",
) -> str:
    """Pure helper behind the ``ask_human`` tool (unit-tested directly).

    Split out from the ``@function_tool`` wrapper so the degrade-to-
    autonomous path and the reply formatting can be tested without booting
    the SDK.  ``human`` is ``None`` on headless runs.  A real reply is
    prefixed with ``HUMAN REPLY:`` so it is unmistakable in the agent's
    observation (and therefore in the saved chain).
    """
    if human is None:
        return NO_HUMAN_REPLY
    answer = human.ask(question, agent=agent)
    return f"HUMAN REPLY: {answer}"


@function_tool
def ask_human(context: RunContextWrapper[ResearchContext], question: str) -> str:
    """Ask the human operator for help when you are blocked or unsure.

    Use this ONLY when you genuinely cannot proceed from the repository and
    paper alone — for example you need a credential or token, a gated
    download, a concrete workaround (such as an alternative model version),
    or a go/no-go before an expensive or destructive action. Always state
    what you already tried, the exact error, and one or two specific
    options. Returns the human's reply, or a note to proceed on your own if
    no operator is attached to this run.
    """
    human = getattr(context.context, "human", None)
    return ask_human_text(human, question)


# A normal ``execute_command`` result always starts with "Exit code: N";
# "Exit code: 0" specifically means the command SUCCEEDED. Crucially, paper and
# repo reads (read_paper / read_repo_file) never carry this prefix, so filtering
# on it isolates *real successful execution* from mere reading — that's what
# lets the grounding check ignore, e.g., the word "generated" sitting in a paper.
_EXEC_SUCCESS_PREFIX = "exit code: 0"


def _successful_execution_text(real_outputs: list[str]) -> str:
    """Join (lowercased) only the outputs of SUCCESSFUL execute_command calls."""
    chunks = [
        out for out in real_outputs if (out or "").lstrip().lower().startswith(_EXEC_SUCCESS_PREFIX)
    ]
    return "\n".join(chunks).lower()


def execution_grounded(final_answer: str, real_outputs: list[str]) -> bool:
    """Conservative backstop: is an 'answered' execution result backed by a real run?

    Returns ``False`` only on a *clear* absence of grounding: the answer is empty, or the
    answering agent never produced a single **successful** ``execute_command`` output (the
    "answered without actually running anything" failure mode — e.g. the binoculars
    hallucination, where the worker jumped straight to a guess). It deliberately does NOT
    try to verify the answer's value appears in output (that would false-flag values
    legitimately read back from a generated workspace file), so genuine runs always pass.
    """
    if not (final_answer or "").strip():
        return False
    return bool(_successful_execution_text(real_outputs).strip())


def apply_integrity_guard(
    answer: "ReActAnswer",
    real_outputs: list[str],
    *,
    needs_execution: bool,
) -> "ReActAnswer":
    """Downgrade an ungrounded 'answered' execution result to 'blocked' (HITL backstop).

    Acts only when the question required execution, the worker reported ``answered``, and
    ``execution_grounded`` is ``False``. Genuine runs and honestly-blocked answers pass
    through untouched. Returns a (possibly) modified copy — duck-typed via ``model_copy`` so
    this module needs no runtime import of ``ReActAnswer``.
    """
    if not needs_execution:
        return answer
    if getattr(answer, "answer_status", "answered") != "answered":
        return answer
    if execution_grounded(getattr(answer, "final_answer", ""), real_outputs):
        return answer
    note = (
        "Auto-flagged by the integrity guard: this answer did not come from any successful "
        "command execution, so it could not be confirmed by a real run."
    )
    prior = getattr(answer, "final_answer", "")
    return answer.model_copy(
        update={
            "answer_status": "blocked",
            "blocker_type": "unknown",
            "blocker_explanation": note,
            "blocker_evidence": [f"unconfirmed answer: {prior[:200]}"],
            "final_answer": f"EXECUTION_REQUIRED — {note}",
        }
    )
