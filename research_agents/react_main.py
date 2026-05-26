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
#     "correct": true/false
#   }

import argparse
import json
import sys
from pathlib import Path

from agents import Runner
from agents.exceptions import MaxTurnsExceeded

from research_agents.config import OPENAI_API_KEY, DEFAULT_MODEL, ALTERNATE_MODEL
from research_agents.agents.react_agent import ReActAnswer, create_react_agent
from research_agents.project import ResearchContext, resolve_project


def _is_correct(final_answer: str, ground_truth: str) -> bool:
    """Heuristic correctness check used for the 'correct' field.

    Strategy (applied in order, short-circuits on first match):
      1. Exact match after stripping whitespace and lowercasing.
      2. Ground truth is a contiguous substring of the final answer
         (handles cases where the agent gives a verbose answer that
         contains the right value, e.g. "The AUROC is 0.97" vs "0.97").
      3. Final answer is a contiguous substring of the ground truth
         (handles abbreviated answers vs long ground truths).

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

    return fa == gt or gt in fa or fa in gt


def _build_record(
    entry_id: str,
    biorxiv_url: str,
    question: str,
    ground_truth: str,
    output: ReActAnswer,
) -> dict:
    correct = _is_correct(output.final_answer, ground_truth)
    return {
        "id": entry_id,
        "repo_link": biorxiv_url,
        "question": question,
        "ground_truth": ground_truth,
        "chain": [
            {
                "step": s.step,
                "thought": s.thought,
                "action": s.action,
                "observation": s.observation,
                "reflection": s.reflection,
            }
            for s in output.chain
        ],
        "final_answer": output.final_answer,
        "correct": correct,
    }


def run_react_query(
    context: ResearchContext,
    question: str,
    model: str,
    entry_id: str,
    biorxiv_url: str,
    ground_truth: str,
    output_path: Path | None = None,
) -> dict:
    """Run the ReAct agent and return the output record as a dict.

    Also writes the record as JSON to output_path (default:
    <run_dir>/react_chain.json).
    """
    agent = create_react_agent(model=model)

    print(f"Running ReAct Research Assistant with {model}...")
    print(f"ID:           {entry_id}")
    print(f"Project:      {context.project_dir}")
    print(f"Run dir:      {context.run_dir}")
    print(f"Question:     {question}")
    print(f"Ground truth: {ground_truth or '(none)'}")
    print("-" * 60)

    try:
        result = Runner.run_sync(agent, question, context=context, max_turns=150)
    except MaxTurnsExceeded:
        print(
            "\nError: Agent did not finish within 150 turns. "
            "The task may be too complex or the agent may be stuck in a loop.",
            file=sys.stderr,
        )
        sys.exit(1)

    output = result.final_output
    record = _build_record(entry_id, biorxiv_url, question, ground_truth, output)

    # --- Print chain to stdout ---
    print(f"\nReAct Chain ({len(output.chain)} steps):")
    for step in output.chain:
        obs_preview = step.observation
        if len(obs_preview) > 200:
            obs_preview = obs_preview[:200] + "…"
        print(f"\n[Step {step.step}]")
        print(f"  Thought:     {step.thought}")
        print(f"  Action:      {step.action}")
        print(f"  Observation: {obs_preview}")
        print(f"  Reflection:  {step.reflection}")

    print(f"\nFinal Answer: {output.final_answer}")
    if ground_truth:
        print(f"Ground Truth: {ground_truth}")
        print(f"Correct:      {record['correct']}")

    # --- Save JSON ---
    if output_path is None:
        output_path = context.run_dir / f"{entry_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved chain to: {output_path}")

    return record


def main():
    """Parse CLI arguments and run the ReAct agent (single or batch)."""
    parser = argparse.ArgumentParser(
        description="ReAct Research Agent — Paper2AgentBench evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single question
  uv run python -m research_agents.react_main \\
      --project papers/PPLM \\
      --question "What is the AUROC for human PPI prediction?" \\
      --ground-truth "0.97" \\
      --id Q001

  # Batch (questions.json = [{"id":"Q001","question":"...","ground_truth":"..."},...]
  uv run python -m research_agents.react_main \\
      --project papers/PPLM \\
      --questions-file questions.json
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
    print(f"\n{'='*60}")
    print(f"Project:   {args.project}")
    print(f"Questions: {total}")
    print(f"{'='*60}\n")

    saved = []

    for i, entry in enumerate(entries, 1):
        entry_id = entry.get("id", f"Q{i:03d}")
        question = entry["question"]
        ground_truth = entry.get("ground_truth", "")

        print(f"\n[{i}/{total}] ID={entry_id} — fresh run")

        # Fresh context per question: own workspace, own venv, no bleed-over.
        try:
            context = resolve_project(args.project)
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
        )
        saved.append(context.run_dir / f"{entry_id}.json")

    print(f"\n{'='*60}")
    print("All chains saved:")
    for path in saved:
        print(f"  {path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
