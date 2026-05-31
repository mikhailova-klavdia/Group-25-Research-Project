"""Interactive CLI (REPL) for the ``human-in-the-loop`` team.

Conversational by design: you describe a task, the team **streams what it's doing**
(triage → answering, or setup → running → reviewing) so it never looks frozen, asks YOU
for help inline when it's stuck, then prints a clean answer. Type ``help`` for commands,
``verbose on`` for the full reasoning-chain dump, ``exit`` / ``quit`` (or Ctrl-D) to leave.

    uv run python -m research_agents.hitl_main --project papers/<slug> [--model ...] [--verbose]

Additive: reuses ``react_main`` helpers for running/saving; the batch ``react_main`` path is
unchanged (it attaches no reporter, so the team stays silent there).
"""

import argparse
import json
import sys
import time

from research_agents.agents.react_agent import REACT_INSTRUCTIONS
from research_agents.config import ALTERNATE_MODEL, DEFAULT_MODEL, OPENAI_API_KEY
from research_agents.hitl import ConsoleHuman, ConsoleReporter
from research_agents.project import resolve_project
from research_agents.react_main import _build_record, run_react_query
from research_agents.teams import TEAMS
from research_agents.token_utils import estimate_tokens

TEAM_NAME = "human-in-the-loop"

HELP_TEXT = """\
Commands:
  <anything>       ask the agents a question or give them a task
  verbose on|off   toggle the full reasoning-chain dump (default off)
  help             show this help
  exit | quit      leave (Ctrl-D also works)

While the agents work they may ask YOU questions — just type your answer inline.
"""


def _run_concise(context, question: str, model: str, entry_id: str, team) -> None:
    """Run the team and print a clean result (live progress already streamed via the reporter)."""
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


def main() -> None:
    """Parse args and run the interactive human-in-the-loop chat loop."""
    parser = argparse.ArgumentParser(
        description="Interactive human-in-the-loop research agent (chat REPL).",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Path to the project folder (must contain paper.pdf and repo/).",
    )
    parser.add_argument(
        "--model",
        default=ALTERNATE_MODEL,
        choices=[DEFAULT_MODEL, ALTERNATE_MODEL],
        help=(
            f"Model to use (default: {ALTERNATE_MODEL}). The HITL team defaults to the "
            "stronger model because its agents must reliably decide to ask for help and "
            "follow through on the reply."
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

    team = TEAMS[TEAM_NAME]
    human = ConsoleHuman()
    reporter = ConsoleReporter()
    verbose = args.verbose

    bar = "═" * 70
    print(bar)
    print("Human-in-the-loop research agent")
    print(f"  project: {args.project}   ·   model: {args.model}")
    print("  Ask a question or give a task. The agents stream what they're doing and may ask")
    print("  YOU for help while they work — just answer inline.")
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

        counter += 1
        entry_id = f"HITL_{counter:03d}"

        # Fresh workspace per task (per-paper venv is reused/warm); attach the
        # console human + the progress reporter so the agents can talk to this terminal.
        try:
            context = resolve_project(args.project, apply_setup=False)
        except ValueError as exc:
            print(f"Error resolving project: {exc}", file=sys.stderr)
            continue
        context.human = human
        context.reporter = reporter

        # One bad task must not kill the session (MaxTurnsExceeded / ModelRefusalError
        # surface as exceptions; run_react_query also exits the process on those).
        try:
            if verbose:
                run_react_query(
                    context=context,
                    question=line,
                    model=args.model,
                    entry_id=entry_id,
                    biorxiv_url="",
                    ground_truth="",
                    team=team,
                )
            else:
                _run_concise(context, line, args.model, entry_id, team)
        except SystemExit:
            print("[task ended early — see the message above]", file=sys.stderr)
        except KeyboardInterrupt:
            print("\n[interrupted this task]", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001 — keep the REPL alive on any task error
            print(f"[task failed: {type(exc).__name__}: {exc}]", file=sys.stderr)

    print("Bye.")


if __name__ == "__main__":
    main()
