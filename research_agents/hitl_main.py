"""Enhanced interactive CLI (REPL) for all registered agent teams.

Improvements over the original hitl_main.py:
  --team           Select any registered team, not just human-in-the-loop
                   (default: human-in-the-loop)
  --questions-file Semi-supervised batch mode: step through a JSON question
                   file with per-question confirm / skip / quit prompts and
                   a running accuracy score when ground truths are present.
  --dry-run        For the human-in-the-loop team: run triage only and print
                   the routing decision (read-only vs execution) without
                   actually executing. For other teams: list all questions in
                   the file and exit without running anything.
  history          New REPL command: show this session's question/answer log
                   with per-task elapsed time and cost.
  Per-task cost    Printed from costs.json after each run so you can see
                   spend without leaving the REPL.
  MaxTurnsExceeded Caught and reported with the partial step count so you
                   know how far the agent got rather than seeing a bare error.

Usage:
    uv run python -m research_agents.hitl_main --project papers/<slug>
    uv run python -m research_agents.hitl_main --project papers/<slug> --team worker-critic-plus
    uv run python -m research_agents.hitl_main --project papers/<slug> --questions-file question-answers/PPLM.json
    uv run python -m research_agents.hitl_main --project papers/<slug> --questions-file question-answers/PPLM.json --dry-run
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from agents.exceptions import MaxTurnsExceeded, ModelRefusalError

from research_agents.agents.react_agent import REACT_INSTRUCTIONS
from research_agents.config import ALTERNATE_MODEL, DEFAULT_MODEL, OPENAI_API_KEY
from research_agents.hitl import ConsoleHuman, ConsoleReporter
from research_agents.project import resolve_project
from research_agents.react_main import _build_record, run_react_query
from research_agents.teams import DEFAULT_TEAM, TEAMS
from research_agents.token_utils import estimate_tokens, load_cost_log

# Default team for the interactive REPL when no --team is given.
# The human-in-the-loop team is the right default here because it is the
# only team that can ask the operator for help mid-run.  All other teams
# also work but degrade ask_human to "proceed autonomously".
DEFAULT_HITL_TEAM = "human-in-the-loop"

HELP_TEXT = """\
Commands:
  <anything>       ask the agents a question or give them a task
  history          show questions asked this session with answers and cost
  verbose on|off   toggle the full reasoning-chain dump (default off)
  help             show this help
  exit | quit      leave (Ctrl-D also works)

While the agents work they may ask YOU questions — just type your answer inline.
Teams available: {teams}
"""


# ---------------------------------------------------------------------------
# Session history
# ---------------------------------------------------------------------------

@dataclass
class HistoryEntry:
    """One completed task in the interactive session."""

    entry_id: str
    question: str
    answer: str
    status: str          # "answered" or "blocked"
    elapsed: float       # seconds
    cost_usd: float | None = None


@dataclass
class SessionHistory:
    """Accumulates per-task results for the `history` REPL command."""

    entries: list[HistoryEntry] = field(default_factory=list)

    def add(self, entry: HistoryEntry) -> None:
        self.entries.append(entry)

    def print(self) -> None:
        """Pretty-print all completed tasks to the terminal."""
        if not self.entries:
            print("  (no tasks completed yet this session)")
            return
        bar = "─" * 70
        print(bar)
        for i, e in enumerate(self.entries, 1):
            q_short = e.question[:80] + "…" if len(e.question) > 80 else e.question
            ans_short = e.answer[:60] + "…" if len(e.answer) > 60 else e.answer
            cost_str = f"  ${e.cost_usd:.4f}" if e.cost_usd is not None else ""
            status_icon = "✓" if e.status == "answered" else "⚠"
            print(f"  {i:>2}. [{e.entry_id}] {status_icon}  {q_short}")
            print(f"       → {ans_short}")
            print(f"       {round(e.elapsed)}s{cost_str}")
        print(bar)
        total_cost = sum(e.cost_usd for e in self.entries if e.cost_usd is not None)
        if total_cost:
            print(f"  Session total cost: ${total_cost:.4f}")
        print(bar)


# ---------------------------------------------------------------------------
# Cost lookup
# ---------------------------------------------------------------------------

def _last_run_cost(project_dir: Path, run_id: str) -> float | None:
    """Return the cost in USD for a specific run_id from costs.json, or None."""
    try:
        entries = load_cost_log(project_dir)
        for entry in reversed(entries):
            if entry.get("run_id") == run_id:
                return entry.get("cost_usd")
    except Exception:  # noqa: BLE001
        pass
    return None


# ---------------------------------------------------------------------------
# Dry-run triage (HITL team only)
# ---------------------------------------------------------------------------

def _dry_run_triage(context, question: str, model: str) -> None:
    """Run the triage stage only and print the routing decision."""
    try:
        # Import here to avoid a hard dependency when using non-HITL teams.
        from research_agents.teams.human_in_the_loop import _run_triage_stage

        print("\n▸ Running triage (dry-run — no execution will happen)…")
        triage, _ = _run_triage_stage(context, question, model)
        bar = "─" * 70
        print(bar)
        needs = "EXECUTION REQUIRED" if triage.needs_execution else "READ-ONLY (no code needed)"
        print(f"  Routing: {needs}")
        print(f"  Rationale: {triage.rationale or '(none)'}")
        if triage.repo_overview:
            print(f"  Repo overview: {triage.repo_overview[:200]}")
        if triage.relevant_paths:
            print(f"  Relevant paths: {', '.join(triage.relevant_paths[:5])}")
        print(bar)
    except Exception as exc:  # noqa: BLE001
        print(f"[dry-run triage failed: {exc}]", file=sys.stderr)


# ---------------------------------------------------------------------------
# Core task runner
# ---------------------------------------------------------------------------

def _run_task(
    context,
    question: str,
    model: str,
    entry_id: str,
    team,
    verbose: bool,
    dry_run: bool,
    team_name: str,
) -> HistoryEntry:
    """Run one task and return a HistoryEntry with the result.

    Handles MaxTurnsExceeded and ModelRefusalError without exiting the
    process so a bad task doesn't kill the interactive session.
    """
    t0 = time.time()

    if dry_run:
        if team_name == "human-in-the-loop":
            _dry_run_triage(context, question, model)
        else:
            print(f"\n[dry-run] would run '{question[:80]}…' with team '{team_name}'")
        return HistoryEntry(
            entry_id=entry_id,
            question=question,
            answer="(dry-run — not executed)",
            status="answered",
            elapsed=time.time() - t0,
        )

    pre_estimate = estimate_tokens(REACT_INSTRUCTIONS, question, model)

    try:
        if verbose:
            run_react_query(
                context=context,
                question=question,
                model=model,
                entry_id=entry_id,
                biorxiv_url="",
                ground_truth="",
                team=team,
            )
            # verbose mode prints everything itself; build a minimal history entry
            elapsed = time.time() - t0
            cost = _last_run_cost(context.project_dir, context.run_id)
            return HistoryEntry(
                entry_id=entry_id,
                question=question,
                answer="(see verbose output above)",
                status="answered",
                elapsed=elapsed,
                cost_usd=cost,
            )

        # Concise mode: run + print clean result box
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

        elapsed = time.time() - t0
        cost = _last_run_cost(context.project_dir, context.run_id)
        status = record.get("failure_analysis", {}).get("answer_status", "answered")

        # Print result box
        bar = "═" * 70
        print(f"\n{bar}")
        if status == "blocked":
            print(f"⚠  {answer.final_answer}")
            why = record.get("failure_analysis", {}).get("blocker_explanation")
            if why:
                print(f"   why: {why}")
        else:
            print(f"✓  {answer.final_answer}")
        print("─" * 70)
        steps = len(record.get("chain", []))
        cost_str = f" · ${cost:.4f}" if cost is not None else ""
        try:
            saved = out_path.relative_to(context.project_dir.parent)
        except ValueError:
            saved = out_path
        print(f"   {steps} steps · {round(elapsed)}s{cost_str} · saved to {saved}")
        print(bar)

        return HistoryEntry(
            entry_id=entry_id,
            question=question,
            answer=answer.final_answer or "",
            status=status,
            elapsed=elapsed,
            cost_usd=cost,
        )

    except MaxTurnsExceeded:
        elapsed = time.time() - t0
        # The agent ran out of turns.  Print the partial step count if the
        # run dir has a JSON file we can inspect.
        partial_steps = "unknown"
        for p in context.run_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                partial_steps = len(data.get("chain", []))
                break
            except Exception:  # noqa: BLE001
                pass
        print(
            f"\n[{entry_id}] Agent hit the 150-turn limit after ~{partial_steps} recorded steps "
            f"({round(elapsed)}s). The task was too complex or the agent got stuck in a loop.",
            file=sys.stderr,
        )
        return HistoryEntry(
            entry_id=entry_id,
            question=question,
            answer="BLOCKED — max turns exceeded",
            status="blocked",
            elapsed=elapsed,
        )

    except ModelRefusalError as exc:
        elapsed = time.time() - t0
        print(f"\n[{entry_id}] Model refused: {exc}", file=sys.stderr)
        return HistoryEntry(
            entry_id=entry_id,
            question=question,
            answer=f"BLOCKED — model refusal: {exc}",
            status="blocked",
            elapsed=elapsed,
        )


# ---------------------------------------------------------------------------
# Questions-file batch mode
# ---------------------------------------------------------------------------

def _load_questions_file(path: str) -> list[dict]:
    """Load and validate a questions JSON file."""
    questions_path = Path(path)
    if not questions_path.exists():
        print(f"Error: questions file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        questions = json.loads(questions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in questions file: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(questions, list):
        print("Error: questions file must be a JSON array.", file=sys.stderr)
        sys.exit(1)
    return questions


def _run_questions_file(
    args,
    team,
    team_spec,
    history: SessionHistory,
    verbose: bool,
) -> None:
    """Step through all questions in a file with per-question prompts.

    For each question the operator chooses:
      Enter / y  — run it
      s          — skip (move to next without running)
      q          — quit the batch loop

    A running accuracy score is printed after each answered question when
    ground truths are present in the file.
    """
    questions = _load_questions_file(args.questions_file)
    n = len(questions)
    total = 0
    correct = 0
    has_gt = any("ground_truth" in q for q in questions)

    bar_thick = "═" * 70
    bar_thin = "─" * 70

    print(f"\n{bar_thick}")
    print(f"  Questions file: {args.questions_file}")
    print(f"  Team: {team_spec.name}   Model: {args.model}")
    print(f"  {n} question(s)   Ground truths: {'yes' if has_gt else 'no'}")
    if args.dry_run:
        print("  DRY-RUN mode — triage only, no execution.")
    print(bar_thick)

    for i, q in enumerate(questions, 1):
        q_id = q.get("id", f"Q{i:03d}")
        question = q.get("question", "")
        ground_truth = q.get("ground_truth", "")

        print(f"\n[{i}/{n}]  {q_id}")
        print(f"  Q: {question[:120]}{'…' if len(question) > 120 else ''}")
        if ground_truth:
            print(f"  GT: {ground_truth}")

        # Prompt operator
        try:
            choice = input("  Run? [Enter=yes / s=skip / q=quit] > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "q":
            print("  Quitting batch.")
            break
        if choice == "s":
            print("  Skipped.")
            continue

        # Run the task
        try:
            context = resolve_project(args.project, apply_setup=team_spec.apply_setup)
            if team_spec.name == "human-in-the-loop":
                context.human = ConsoleHuman()
                context.reporter = ConsoleReporter()
        except ValueError as exc:
            print(f"  Error resolving project: {exc}", file=sys.stderr)
            continue

        entry = _run_task(
            context=context,
            question=question,
            model=args.model,
            entry_id=q_id,
            team=team,
            verbose=verbose,
            dry_run=args.dry_run,
            team_name=team_spec.name,
        )
        history.add(entry)

        # Accuracy tracking
        if has_gt and ground_truth and not args.dry_run:
            total += 1
            # Simple substring match (same heuristic as react_main)
            fa = (entry.answer or "").strip().lower()
            gt = ground_truth.strip().lower()
            if gt in fa or fa in gt:
                correct += 1
                print(f"  ✅  Matches ground truth")
            else:
                print(f"  ❌  Expected: {ground_truth}")
            if total > 0:
                print(f"  Running score: {correct}/{total} ({100*correct//total}%)")

    print(f"\n{bar_thin}")
    if has_gt and total > 0:
        print(f"  Final score: {correct}/{total} ({100*correct//total}%)")
    print(f"  Answered {len(history.entries)} question(s) this session.")
    print(bar_thin)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse CLI args and start the interactive session."""
    team_names = list(TEAMS.keys())

    parser = argparse.ArgumentParser(
        description="Interactive research agent CLI — chat REPL or semi-supervised batch mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive chat with the human-in-the-loop team (default)
  uv run python -m research_agents.hitl_main --project papers/PPLM

  # Interactive chat with a different team
  uv run python -m research_agents.hitl_main --project papers/PPLM --team worker-critic-plus

  # Step through all PPLM questions with per-question confirm/skip
  uv run python -m research_agents.hitl_main --project papers/PPLM \\
      --questions-file question-answers/PPLM.json

  # Dry-run: show triage decisions for all questions without executing
  uv run python -m research_agents.hitl_main --project papers/PPLM \\
      --questions-file question-answers/PPLM.json --dry-run

  # Single dry-run triage in the REPL (type question then Ctrl+D)
  uv run python -m research_agents.hitl_main --project papers/PPLM --dry-run
""",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Path to the project folder (must contain paper.pdf and repo/).",
    )
    parser.add_argument(
        "--team",
        default=DEFAULT_HITL_TEAM,
        choices=team_names,
        help=(
            f"Agent team to use (default: {DEFAULT_HITL_TEAM}). "
            f"Choices: {', '.join(team_names)}."
        ),
    )
    parser.add_argument(
        "--model",
        default=ALTERNATE_MODEL,
        choices=[DEFAULT_MODEL, ALTERNATE_MODEL],
        help=(
            f"Model to use (default: {ALTERNATE_MODEL}). "
            "The HITL team defaults to the stronger model so agents reliably decide to ask for help."
        ),
    )
    parser.add_argument(
        "--questions-file",
        metavar="PATH",
        help=(
            "Path to a JSON questions file (same format as question-answers/*.json). "
            "Enables semi-supervised batch mode: step through each question with "
            "per-question confirm / skip / quit prompts and running accuracy display."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Triage-only mode. For the human-in-the-loop team: run triage and print the "
            "routing decision (read-only vs execution) without executing. "
            "For other teams with --questions-file: list all questions and exit."
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

    team_spec = TEAMS[args.team]
    team = team_spec
    verbose = args.verbose
    history = SessionHistory()
    counter = 0

    # ── Questions-file mode ──────────────────────────────────────────────────
    if args.questions_file:
        _run_questions_file(args, team, team_spec, history, verbose)
        return

    # ── Interactive REPL ─────────────────────────────────────────────────────
    bar = "═" * 70
    print(bar)
    print("Research Agent — interactive CLI")
    print(f"  project : {args.project}")
    print(f"  team    : {team_spec.name}  —  {team_spec.description[:60]}…")
    print(f"  model   : {args.model}")
    if args.dry_run:
        print("  DRY-RUN mode — triage only, no execution.")
    print("  Ask a question or give a task. Type 'help' for commands, 'exit' to quit.")
    print(bar)

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
            print(HELP_TEXT.format(teams=", ".join(team_names)))
            continue
        if low == "history":
            history.print()
            continue
        if low in {"verbose on", "verbose off"}:
            verbose = low.endswith("on")
            print(f"[verbose {'on' if verbose else 'off'}]")
            continue

        counter += 1
        entry_id = f"HITL_{counter:03d}"

        try:
            context = resolve_project(args.project, apply_setup=team_spec.apply_setup)
        except ValueError as exc:
            print(f"Error resolving project: {exc}", file=sys.stderr)
            continue

        # Attach human + reporter channels for the HITL team.
        if team_spec.name == "human-in-the-loop":
            context.human = ConsoleHuman()
            context.reporter = ConsoleReporter()

        try:
            entry = _run_task(
                context=context,
                question=line,
                model=args.model,
                entry_id=entry_id,
                team=team,
                verbose=verbose,
                dry_run=args.dry_run,
                team_name=team_spec.name,
            )
            history.add(entry)
        except SystemExit:
            print("[task ended early — see the message above]", file=sys.stderr)
        except KeyboardInterrupt:
            print("\n[interrupted — task cancelled]", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — keep REPL alive on task error
            print(f"[task failed: {type(exc).__name__}: {exc}]", file=sys.stderr)

    # Print session summary on exit
    if history.entries:
        print("\nSession summary:")
        history.print()
    print("Bye.")


if __name__ == "__main__":
    main()