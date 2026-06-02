# CLI entry point for ReAct-style Paper2AgentBench evaluation.
#
# Usage:
#   uv run python -m research_agents.react_main \
#     --project papers/<slug> \
#     --question "What is the AUROC reported for human PPI prediction?" \
#     --ground-truth "0.97" \
#     --id REPO_001 \
#     --biorxiv-url "https://www.biorxiv.org/content/..." \
#     [--output results/REPO_001.json] \
#     [--model gpt-4.1-mini-2025-04-14]
#
# Output JSON schema:
#   {
#     "id": "REPO_001",
#     "repo_link": "https://...",
#     "question": "...",
#     "ground_truth": "...",
#     "chain": [{"step": 1, "thought": ..., "action": ...,
#                "observation": ..., "reflection": ...}, ...],
#     "final_answer": "...",
#     "failure_analysis": {"answer_status": ..., "blocker_type": ...},
#     "correct": true/false
#   }

import argparse
import json
import sys
from pathlib import Path

import openai
from agents.exceptions import MaxTurnsExceeded, ModelRefusalError

from research_agents.config import OPENAI_API_KEY, DEFAULT_MODEL, ALTERNATE_MODEL
from research_agents.agents.react_agent import REACT_INSTRUCTIONS, ReActAnswer
from research_agents.orchestration import ToolOutputCapture
from research_agents.project import ResearchContext, resolve_project
from research_agents.teams import DEFAULT_TEAM, TEAMS, TeamSpec
from research_agents.token_utils import (
    append_cost_log,
    calculate_cost,
    estimate_tokens,
    print_token_report,
)


def _is_correct(final_answer: str, ground_truth: str) -> bool:
    """Heuristic correctness check used for the 'correct' field.

    Strategy (applied in order, short-circuits on first match):
      1. Exact match after stripping whitespace and lowercasing.
      2. Ground truth is a contiguous substring of the final answer
         (handles cases where the agent gives a verbose answer that
         contains the right value, e.g. "The AUROC is 0.97" vs "0.97").
      3. Final answer is a contiguous substring of the ground truth
         (handles abbreviated answers vs long ground truths).
      4. Numeric tolerance: if both strings parse as floats and agree to
         a 1e-5 relative tolerance, treat as a match.  Catches the case
         where the agent rounds to fewer sig figs than the ground truth
         (e.g. "0.9431089" vs "0.94310874" — same number, just truncated).

    This is intentionally permissive — downstream reviewers should
    validate the 'correct' field; it is a convenience flag, not a
    rigorous evaluation metric.
    """
    if not ground_truth.strip():
        return False

    def norm(s: str) -> str:
        return s.strip().lower()

    fa = norm(final_answer)
    gt = norm(ground_truth)

    # Guard against the empty-string false positive: "" is a substring of
    # everything, so `fa in gt` would otherwise be True and mark any
    # 1-step chain with a missing final_answer as correct.
    if not fa:
        return False

    FAILURE_PHRASES = {
        "execution_required",
        "cannot determine",
        "could not",
        "execution failed",
        "unable to",
        "not determined",
        "i could not",
        "did not successfully",
    }
    if any(p in fa for p in FAILURE_PHRASES):
        return False

    if fa == gt or gt in fa or fa in gt:
        return True

    try:
        fa_num, gt_num = float(fa), float(gt)
        # Pure relative tolerance: scale to the larger magnitude so tiny
        # scientific numbers (e.g. 5e-8) are not swallowed by a fixed floor.
        # 0.1% (1e-3) handles 2–3 sig fig rounding without false-matching
        # values that differ by orders of magnitude.
        # 1e-15 epsilon only guards the true-zero vs true-zero edge case.
        scale = max(abs(fa_num), abs(gt_num), 1e-15)
        if abs(fa_num - gt_num) <= 1e-3 * scale:
            return True
    except ValueError:
        pass

    return False


def _failure_analysis(output: ReActAnswer) -> dict:
    """Build structured blocked-answer metadata for the saved JSON.

    The worker now fills these fields directly, but older/incomplete model
    outputs may only provide an EXECUTION_REQUIRED final_answer.  Treat
    those as blocked with an unknown category so downstream analysis still
    has a consistent shape.
    """
    final_lower = output.final_answer.strip().lower()
    looks_blocked = final_lower.startswith("execution_required") or any(
        phrase in final_lower
        for phrase in (
            "required file",
            "not found",
            "could not",
            "unable to",
            "cannot proceed",
            "execution failed",
        )
    )
    status = output.answer_status
    blocker_type = output.blocker_type
    if status == "answered" and looks_blocked:
        status = "blocked"
        blocker_type = "unknown" if blocker_type == "none" else blocker_type

    explanation = output.blocker_explanation
    if status == "blocked" and not explanation:
        explanation = output.final_answer

    return {
        "answer_status": status,
        "blocker_type": blocker_type if status == "blocked" else "none",
        "blocker_explanation": explanation if status == "blocked" else None,
        "blocker_evidence": output.blocker_evidence if status == "blocked" else [],
    }


def _build_record(
    entry_id: str,
    biorxiv_url: str,
    question: str,
    ground_truth: str,
    output: ReActAnswer,
    model: str,
    pre_estimate: int,
    result,
    capture: ToolOutputCapture,
    team_name: str,
    critic_reviews: list | None = None,
    install_events: list | None = None,
    extraction_report: dict | None = None,
    testing_report: dict | None = None,
) -> dict:
    correct = _is_correct(output.final_answer, ground_truth)

    if len(capture.outputs) != len(output.chain):
        print(
            f"[WARNING] Tool calls captured ({len(capture.outputs)}) != "
            f"chain steps ({len(output.chain)}). "
            "Injecting real observations where counts align; remainder use LLM-written text."
        )

    chain_steps = []
    for i, s in enumerate(output.chain):
        real_obs = capture.outputs[i] if i < len(capture.outputs) else s.observation
        chain_steps.append(
            {
                "step": s.step,
                "thought": s.thought,
                "action": s.action,
                "observation": real_obs,
                "reflection": s.reflection,
            }
        )

    # ``team`` lives at the top of the record so a comparison script can
    # bucket chains by team without parsing internals.  Schema version is
    # incremented when downstream tools need to detect new chain fields.
    record = {
        "id": entry_id,
        "team": team_name,
        "repo_link": biorxiv_url,
        "question": question,
        "ground_truth": ground_truth,
        "chain": chain_steps,
        "final_answer": output.final_answer,
        "failure_analysis": _failure_analysis(output),
        "correct": correct,
        "critic_reviews": [
            review.model_dump() if hasattr(review, "model_dump") else review
            for review in critic_reviews or []
        ],
        "install_events": [
            {
                "attempt": event.attempt,
                "modules": event.modules,
                "packages": event.packages,
                "command": event.command,
                "exit_code": event.exit_code,
                "output": event.output,
                "succeeded": event.succeeded,
            }
            for event in install_events or []
        ],
        "token_usage": {
            "pre_run_estimate": pre_estimate,
            "input_tokens": result.context_wrapper.usage.input_tokens if result else 0,
            "output_tokens": result.context_wrapper.usage.output_tokens if result else 0,
            "total_tokens": (
                result.context_wrapper.usage.input_tokens
                + result.context_wrapper.usage.output_tokens
            ) if result else 0,
            "estimated_cost_usd": calculate_cost(
                result.context_wrapper.usage.input_tokens,
                result.context_wrapper.usage.output_tokens,
                model,
            ) if result else 0.0,
        },
    }
    if extraction_report is not None:
        record["extraction_report"] = extraction_report
    if testing_report is not None:
        record["testing_report"] = testing_report
    return record


def run_react_query(
    context: ResearchContext,
    question: str,
    model: str,
    entry_id: str,
    biorxiv_url: str,
    ground_truth: str,
    team: TeamSpec,
    output_path: Path | None = None,
) -> dict:
    """Run the selected agent team and return the output record as a dict.

    Also writes the record as JSON to output_path (default:
    ``<run_dir>/<entry_id>.json``).  The dispatch goes through
    ``team.run`` so every team is invoked the same way — adding a new
    team means registering a ``TeamSpec`` in ``research_agents.teams``,
    not editing this function.
    """
    print(f"Running team '{team.name}' with worker model {model}...")
    print(f"ID:           {entry_id}")
    print(f"Project:      {context.project_dir}")
    print(f"Run dir:      {context.run_dir}")
    print(f"Question:     {question}")
    print(f"Ground truth: {ground_truth or '(none)'}")
    print(f"Team:         {team.name}  ({team.description})")
    print("-" * 60)

    pre_estimate = estimate_tokens(REACT_INSTRUCTIONS, question, model)
    print(f"Pre-run token estimate (tiktoken): ~{pre_estimate:,}")
    print("-" * 60)
    try:
        team_result = team.run(context, question, ground_truth, entry_id, model)
        result = team_result.worker_result
        output = team_result.answer
        capture = team_result.final_capture
        critic_reviews = team_result.reviews
        install_events = team_result.install_events
        extraction_report = team_result.extraction_report
        testing_report = team_result.testing_report
    except MaxTurnsExceeded:
        print(
            "\nError: Agent did not finish within 150 turns. "
            "The task may be too complex or the agent may be stuck in a loop.",
            file=sys.stderr,
        )
        sys.exit(1)
    except ModelRefusalError as exc:
        print(
            f"\nError: Model refused to answer the question: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except openai.RateLimitError as exc:
        print(
            f"\n[RATE LIMIT] OpenAI rate limit reached: {exc}",
            file=sys.stderr,
        )
        print(
            "The API has either hit a requests-per-minute / tokens-per-minute cap "
            "or exhausted the account quota. Wait a moment and re-run, or switch "
            "models with --model.",
            file=sys.stderr,
        )
        sys.exit(2)
    except openai.APIStatusError as exc:
        print(
            f"\n[API ERROR] OpenAI returned HTTP {exc.status_code}: {exc.message}",
            file=sys.stderr,
        )
        sys.exit(2)

    # --- Token usage ---
    usage = result.context_wrapper.usage
    print("\nToken usage:")
    print(f"  Input tokens:  {usage.input_tokens}")
    print(f"  Output tokens: {usage.output_tokens}")
    print(f"  Total tokens:  {usage.input_tokens + usage.output_tokens}")
    record = _build_record(
        entry_id,
        biorxiv_url,
        question,
        ground_truth,
        output=output,
        model=model,
        pre_estimate=pre_estimate,
        result=result,
        capture=capture,
        team_name=team.name,
        critic_reviews=critic_reviews,
        install_events=install_events,
        extraction_report=extraction_report,
        testing_report=testing_report,
    )

    # --- Print chain to stdout ---
    print(f"\nReAct Chain ({len(output.chain)} steps):")
    for step in record["chain"]:
        obs_preview = step["observation"]
        if len(obs_preview) > 200:
            obs_preview = obs_preview[:200] + "…"
        print(f"\n[Step {step['step']}]")
        print(f"  Thought:     {step['thought']}")
        print(f"  Action:      {step['action']}")
        print(f"  Observation: {obs_preview}")
        print(f"  Reflection:  {step['reflection']}")

    if critic_reviews:
        print(f"\nCritic reviews ({len(critic_reviews)}):")
        for review in critic_reviews:
            print(f"  Verdict: {review.verdict}")
            print(f"  Reasoning: {review.reasoning}")

    if install_events:
        print(f"\nDependency installs ({len(install_events)}):")
        for event in install_events:
            status = "ok" if event.succeeded else "failed"
            print(f"  Attempt {event.attempt}: {event.packages} [{status}]")

    print(f"\nFinal Answer: {output.final_answer}")
    failure = record["failure_analysis"]
    if failure["answer_status"] == "blocked":
        print(f"Blocked:      {failure['blocker_type']}")
        if failure["blocker_explanation"]:
            print(f"Why:          {failure['blocker_explanation']}")
    if ground_truth:
        print(f"Ground Truth: {ground_truth}")
        print(f"Correct:      {record['correct']}")

    # --- Save JSON ---
    if output_path is None:
        output_path = context.run_dir / f"{entry_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved chain to: {output_path}")
    if result is not None:
        append_cost_log(
            project_dir=context.project_dir,
            run_id=context.run_id,
            question=question,
            model=model,
            pre_estimate=pre_estimate,
            input_tokens=result.context_wrapper.usage.input_tokens,
            output_tokens=result.context_wrapper.usage.output_tokens,
        )
        print_token_report(
            pre_estimate,
            result.context_wrapper.usage.input_tokens,
            result.context_wrapper.usage.output_tokens,
            model,
            project_dir=context.project_dir,
        )
    return record


def main():
    """Parse CLI arguments and run the ReAct agent (single or batch).

    The CLI exposes the team registry via ``--team <name>`` so adding a
    new team in ``research_agents/teams/`` immediately makes it
    available here — this function never has to grow.
    """
    team_help = "Agent team to run. Choices:\n" + "\n".join(
        f"  {spec.name:<22} {spec.description}" for spec in TEAMS.values()
    )

    parser = argparse.ArgumentParser(
        description="ReAct Research Agent — Paper2AgentBench evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Single question, default team ({DEFAULT_TEAM})
  uv run python -m research_agents.react_main \\
      --project papers/PPLM \\
      --question "What is the AUROC for human PPI prediction?" \\
      --ground-truth "0.97" \\
      --id Q001

  # Same question, the colleague's 2-agent baseline
  uv run python -m research_agents.react_main \\
      --project papers/PPLM --id Q001 \\
      --question "..." --ground-truth "0.97" \\
      --team worker-critic

  # Batch with the improved variant (setup scripts + improved prompt)
  uv run python -m research_agents.react_main \\
      --project papers/PPLM \\
      --questions-file question-answers/PPLM.json \\
      --team worker-critic-plus
        """,
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Path to the project folder (must contain paper.pdf and repo/)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=[DEFAULT_MODEL, ALTERNATE_MODEL],
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--biorxiv-url",
        default="",
        metavar="URL",
        help="BioRxiv URL stored in repo_link (single mode only)",
    )
    parser.add_argument(
        "--team",
        default=DEFAULT_TEAM,
        choices=list(TEAMS.keys()),
        help=team_help,
    )
    # Deprecated alias kept so existing scripts that pass --no-critic
    # still resolve to the single-worker path.  Selecting --team and
    # --no-critic together raises a clear error rather than silently
    # picking one.
    parser.add_argument(
        "--no-critic",
        dest="no_critic",
        action="store_true",
        help="Deprecated alias for --team solo (kept for backward compatibility).",
    )

    # --- single mode ---
    single = parser.add_argument_group("single question")
    single.add_argument("--question", default=None, help="Benchmark question")
    single.add_argument("--ground-truth", default="", metavar="ANSWER")
    single.add_argument("--id", default="Q001", metavar="ID")

    # --- batch mode ---
    batch = parser.add_argument_group("batch questions")
    batch.add_argument(
        "--questions-file",
        default=None,
        metavar="PATH",
        help=(
            "JSON file with a list of questions. Each entry: "
            '{"id": "Q001", "question": "...", "ground_truth": "..."}'
        ),
    )

    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set. Create a .env file or export it.", file=sys.stderr)
        sys.exit(1)

    if not args.questions_file and not args.question:
        parser.error("Provide either --question (single) or --questions-file (batch).")

    # Resolve --no-critic into --team selection.  Refuse to silently
    # honor a mismatch — the user should pick one.
    if args.no_critic:
        if args.team != DEFAULT_TEAM and args.team != "solo":
            parser.error("--no-critic conflicts with --team " + args.team)
        team = TEAMS["solo"]
        print(
            "[warning] --no-critic is deprecated; pass --team solo instead.",
            file=sys.stderr,
        )
    else:
        team = TEAMS[args.team]

    # Build the list of entries to run
    if args.questions_file:
        entries = json.loads(Path(args.questions_file).read_text(encoding="utf-8"))
    else:
        entries = [
            {
                "id": args.id,
                "question": args.question,
                "ground_truth": args.ground_truth,
            }
        ]

    total = len(entries)
    print(f"\n{'=' * 60}")
    print(f"Project:   {args.project}")
    print(f"Team:      {team.name}")
    print(f"Questions: {total}")
    print(f"{'=' * 60}\n")

    saved = []

    for i, entry in enumerate(entries, 1):
        entry_id = entry.get("id", f"Q{i:03d}")
        question = entry["question"]
        ground_truth = entry.get("ground_truth", "")

        print(f"\n[{i}/{total}] ID={entry_id} — fresh workspace")

        # Fresh workspace per question; the paper-level venv is reused.
        # The team's ``apply_setup`` flag decides whether resolve_project
        # honors the paper's ``[setup]`` table (PPLM weight download, etc.).
        try:
            context = resolve_project(args.project, apply_setup=team.apply_setup)
        except ValueError as exc:
            print(f"Error resolving project: {exc}", file=sys.stderr)
            sys.exit(1)

        run_react_query(
            context=context,
            question=question,
            model=args.model,
            entry_id=entry_id,
            biorxiv_url=args.biorxiv_url,
            ground_truth=ground_truth,
            team=team,
        )
        saved.append(context.run_dir / f"{entry_id}.json")

    print(f"\n{'=' * 60}")
    print("All chains saved:")
    for path in saved:
        print(f"  {path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
