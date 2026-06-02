"""Interactive CLI (REPL) for HITL-capable teams.

Conversational by design: a lightweight gateway LLM holds the chat, asks
clarifying questions when needed, and only fires the full research pipeline
(triage → setup → execution) when the user has a specific question that
needs it.  The team then **streams what it's doing** so it never looks frozen,
asks YOU for help inline when stuck, and prints a clean answer.

    uv run python -m research_agents.hitl_main --project papers/<slug> [--team ...] [--model ...] [--verbose]

Per-project memory is stored at ``papers/<slug>/.hitl_memory.json`` so the
gateway remembers what was asked in previous sessions and the paper is not
re-read every time.  Supports any team registered in ``TEAMS`` that uses the
HITL pipeline internally (``human-in-the-loop`` and
``worker-critic-plus-plus-hitl``).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

from research_agents.agents.react_agent import REACT_INSTRUCTIONS
from research_agents.config import ALTERNATE_MODEL, DEFAULT_MODEL, OPENAI_API_KEY
from research_agents.hitl import ConsoleHuman, ConsoleReporter
from research_agents.project import fresh_workspace, resolve_project
from research_agents.react_main import _build_record, run_react_query
from research_agents.teams import TEAMS
from research_agents.token_utils import estimate_tokens

HITL_TEAMS = ("human-in-the-loop", "worker-critic-plus-plus-hitl")

HELP_TEXT = """\
Commands:
  <anything>       chat or ask a research question — the agent decides what to do
  verbose on|off   toggle the full reasoning-chain dump (default off)
  help             show this help
  exit | quit      leave (Ctrl-D also works)

While the research agents work they may ask YOU questions — just type your answer inline.
"""

_GATEWAY_SYSTEM = """\
You are the conversational interface for a research agent set up for the project "{project}".

Your job is to have a natural chat with the user and decide when they have a real
research question that needs the full investigation pipeline (reading the paper,
exploring the repository, running code experiments).

Always respond with valid JSON in exactly one of these two forms:

{{"action": "reply", "reply": "<your conversational response>"}}
  Use for: greetings, identity questions ("who are you", "who r u", "what r u"),
  capability questions, acknowledgments ("ok", "thanks", "cool"), small-talk,
  vague openers where you want to ask the user to be more specific, or anything
  that does not require reading a paper or running code.
  If the conversation history contains action=research_complete entries, you can
  answer follow-up questions about those results directly here without re-running
  the pipeline.

{{"action": "research", "question": "<the specific, self-contained question>"}}
  Use for: any question whose answer requires reading the paper, exploring the
  repository, or running code — a specific numeric result, a method detail,
  a reproduction request, "what does X return when...", "run Y and report Z", etc.
  Write the question as a clear, standalone sentence even if the user was terse.

Rules:
- "hi", "hello", "hey", "who are you", "who r u", "what can u do", "thanks", "ok",
  "great", "bye" and similar casual inputs are ALWAYS action=reply.
- If the user is vague ("tell me about this", "what's interesting here"), use
  action=reply and ask what specifically they want to know.
- Only use action=research when you have a clear, answerable question in hand.
- History entries with action=research_complete record what the pipeline found for
  a previous question — use them to answer follow-up questions directly.
- Keep replies short and friendly — one or two sentences is usually enough.
"""

# How many gateway messages to keep across sessions.  Each turn is 2 messages
# (user + assistant), so 40 stores the last 20 turns — enough to cover a
# typical multi-question session without bloating the context window.
_HISTORY_CAP = 40

_MEMORY_FILE = ".hitl_memory.json"


def _memory_path(project_dir: Path) -> Path:
    return project_dir / _MEMORY_FILE


def _load_memory(path: Path) -> tuple[list[dict], str | None]:
    """Load gateway history and session_overview from a previous session, or return empty."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("history", []), data.get("session_overview")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return [], None


def _save_memory(path: Path, history: list[dict], session_overview: str | None) -> None:
    """Persist gateway history (capped) and session_overview for the next session."""
    trimmed = history[-_HISTORY_CAP:]
    data = {"session_overview": session_overview, "history": trimmed}
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        print(f"[warning: could not save memory: {exc}]", file=sys.stderr)


class GatewaySession:
    """Conversational front-door backed by a small, fast LLM.

    Keeps a full message history (optionally seeded from a previous session)
    so it can hold natural multi-turn chat: remembers what was asked in
    earlier sessions, can refer back to previous findings, and asks
    clarifying questions when the user is vague.  Returns either a chat
    reply to print directly, or a signal that the research pipeline should
    run with a specific (possibly rephrased) question.
    """

    def __init__(self, project_slug: str, history: list[dict] | None = None) -> None:
        self._client = OpenAI()
        # Use the cheaper model for the gateway — it's just routing chat.
        self._model = DEFAULT_MODEL
        self._system = _GATEWAY_SYSTEM.format(project=project_slug)
        # Seed from previous session if provided; otherwise start fresh.
        self._history: list[dict] = list(history) if history else []

    def send(self, user_message: str) -> tuple[str, str]:
        """Process one user turn; return ``(action, payload)``.

        ``action == "reply"``    → print payload as a conversational reply.
        ``action == "research"`` → run the pipeline with payload as the question.
        The question in the research case may be a cleaner restatement of what
        the user typed — use that version for the pipeline so it gets a better
        question.
        """
        self._history.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": self._system}] + self._history

        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=250,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content or ""
        self._history.append({"role": "assistant", "content": raw})

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return "reply", raw

        action = data.get("action", "reply")
        if action == "research":
            return "research", data.get("question", user_message)
        return "reply", data.get("reply", raw)

    def record_result(self, question: str, answer: str) -> None:
        """Record a pipeline result in history so the next session can reference it.

        Stored as a JSON assistant message with action=research_complete so
        the gateway system prompt knows to treat it as a factual memory entry
        rather than a routing decision.
        """
        entry = json.dumps(
            {
                "action": "research_complete",
                "question": question[:200],
                "answer": answer[:300],
            }
        )
        self._history.append({"role": "assistant", "content": entry})

    @property
    def history(self) -> list[dict]:
        """Current message history (for persistence)."""
        return list(self._history)


def _run_concise(context, question: str, model: str, entry_id: str, team) -> str:
    """Run the team, print a clean result, and return the final_answer string."""
    t0 = time.time()
    pre_estimate = estimate_tokens(REACT_INSTRUCTIONS, question, model)
    team_result = team.run(context, question, "", entry_id, model)
    answer = team_result.answer

    record = _build_record(
        entry_id,
        "",
        question,
        "",
        output=answer,
        model=model,
        pre_estimate=pre_estimate,
        result=team_result.worker_result,
        capture=team_result.final_capture,
        team_name=team.name,
        critic_reviews=team_result.reviews,
        install_events=team_result.install_events,
    )
    out_path = context.run_dir / f"{entry_id}.json"
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    bar = "═" * 70
    print(f"\n{bar}")
    if record["failure_analysis"]["answer_status"] == "blocked":
        print(f"⚠  {answer.final_answer}")
        why = record["failure_analysis"].get("blocker_explanation")
        if why:
            print(f"   why: {why}")
    else:
        print(f"✓  {answer.final_answer}")
    print("─" * 70)
    try:
        saved = out_path.relative_to(context.project_dir.parent)
    except ValueError:
        saved = out_path
    print(f"   {len(record['chain'])} steps · {round(time.time() - t0)}s · saved to {saved}")
    print(bar)

    return answer.final_answer


def main() -> None:
    """Parse args and run the interactive HITL chat loop."""
    parser = argparse.ArgumentParser(
        description="Interactive human-in-the-loop research agent (chat REPL).",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Path to the project folder (must contain paper.pdf and repo/).",
    )
    parser.add_argument(
        "--team",
        default="human-in-the-loop",
        choices=HITL_TEAMS,
        help=(
            "HITL team to use. 'human-in-the-loop' asks YOU inline; "
            "'worker-critic-plus-plus-hitl' routes ask_human to Claude and uses "
            "the plus-plus prompt (requires ANTHROPIC_API_KEY). "
            "Default: human-in-the-loop"
        ),
    )
    parser.add_argument(
        "--model",
        default=ALTERNATE_MODEL,
        choices=[DEFAULT_MODEL, ALTERNATE_MODEL],
        help=(
            f"Model for the research pipeline (default: {ALTERNATE_MODEL}). "
            "The conversational gateway always uses the cheaper model."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Start with the full reasoning-chain dump on (toggle live with 'verbose on|off').",
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set. Create a .env file or export it.", file=sys.stderr)
        sys.exit(1)

    team = TEAMS[args.team]
    human = ConsoleHuman()
    reporter = ConsoleReporter()
    verbose = args.verbose

    # Resolve the project once at session start so the shared venv is warm
    # for the entire session.  Each question gets a fresh workspace via
    # fresh_workspace(), which reuses venv_path, artifacts_path, etc.
    try:
        base_context = resolve_project(args.project, apply_setup=False)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    project_slug = os.path.basename(args.project.rstrip("/\\"))
    mem_path = _memory_path(base_context.project_dir)

    # Restore previous session: gateway history + cached repo overview.
    saved_history, session_overview = _load_memory(mem_path)
    gateway = GatewaySession(project_slug, history=saved_history)

    bar = "═" * 70
    print(bar)
    print("Human-in-the-loop research agent")
    print(f"  project: {args.project}   ·   team: {team.name}   ·   model: {args.model}")
    if saved_history:
        prior_turns = sum(
            1 for m in saved_history if m.get("role") == "user"
        )
        print(f"  memory: {prior_turns} previous turn(s) loaded from last session.")
    print("  Chat naturally — I'll investigate when you have a specific question.")
    print("  Type 'help' for commands, 'exit' to quit.")
    print(bar)

    counter = 0

    while True:
        try:
            line = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue
        low = line.lower()
        if low in {"exit", "quit"}:
            break
        if low == "help":
            print(HELP_TEXT)
            continue
        if low in {"verbose on", "verbose off"}:
            verbose = low.endswith("on")
            print(f"[verbose {'on' if verbose else 'off'}]")
            continue

        # Ask the gateway: chat reply, or fire the research pipeline?
        try:
            action, payload = gateway.send(line)
        except Exception as exc:  # noqa: BLE001
            print(f"[gateway error: {exc}]", file=sys.stderr)
            continue

        if action == "reply":
            print(f"\nagent> {payload}")
            continue

        # action == "research" — run the full pipeline with the (possibly
        # rephrased) question the gateway extracted.
        question = payload
        counter += 1
        entry_id = f"HITL_{counter:03d}"

        # Fresh workspace per task (per-paper venv is reused/warm); attach the
        # console human + progress reporter + cached repo overview.
        context = fresh_workspace(base_context)
        context.human = human
        context.reporter = reporter
        context.session_overview = session_overview

        final_answer = ""
        try:
            if verbose:
                record = run_react_query(
                    context=context,
                    question=question,
                    model=args.model,
                    entry_id=entry_id,
                    biorxiv_url="",
                    ground_truth="",
                    team=team,
                )
                final_answer = record.get("final_answer", "")
            else:
                final_answer = _run_concise(context, question, args.model, entry_id, team)
        except SystemExit:
            print("[task ended early — see the message above]", file=sys.stderr)
        except KeyboardInterrupt:
            print("\n[interrupted this task]", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — keep the REPL alive on any task error
            print(f"[task failed: {type(exc).__name__}: {exc}]", file=sys.stderr)
        else:
            # Cache the repo overview after the first successful triage so
            # follow-up questions skip re-reading the paper.
            if session_overview is None and context.session_overview:
                session_overview = context.session_overview

            # Record the result in gateway history and persist both for the
            # next session — the gateway can answer follow-ups from memory.
            if final_answer:
                gateway.record_result(question, final_answer)
            _save_memory(mem_path, gateway.history, session_overview)

    # Save on clean exit so any chat-only turns (greetings, clarifications)
    # are also remembered next time.
    _save_memory(mem_path, gateway.history, session_overview)
    print("Bye.")


if __name__ == "__main__":
    main()
