# CLI entry point for running research queries.
#
# Usage:
#   uv run python -m research_agents.main \
#     --project papers/<slug> --question "..."

import argparse
import sys

from agents import Runner
from agents.exceptions import MaxTurnsExceeded

from research_agents.config import OPENAI_API_KEY, DEFAULT_MODEL, ALTERNATE_MODEL
from research_agents.agents.research_agent import create_research_agent
from research_agents.project import ResearchContext, resolve_project


def run_research_query(context: ResearchContext, question: str, model: str):
    """Run the agent on a single question and print the result."""
    agent = create_research_agent(model=model)

    print(f"Running Research Assistant with {model}...")
    print(f"Project: {context.project_dir}")
    print(f"Paper: {context.paper_path}")
    print(f"Repository: {context.repo_path}")
    print(f"Run: {context.run_id}")
    print(f"Run directory: {context.run_dir}")
    print(f"Workspace: {context.workspace_path}")
    print(f"Question: {question}")
    print("-" * 60)

    # Fresh per-run environments require more setup turns than read-only Q&A.
    try:
        result = Runner.run_sync(agent, question, context=context, max_turns=60)
    except MaxTurnsExceeded:
        print(
            "\nError: Agent did not finish within 60 turns. "
            "The task may be too complex or the agent may be stuck in a loop.",
            file=sys.stderr,
        )
        sys.exit(1)

    output = result.final_output
    print(f"\nAnswer: {output.answer}")
    print(f"\nReasoning: {output.reasoning}")
    print(f"\nSources: {', '.join(output.sources)}")
    if output.execution:
        ex = output.execution
        status = "SUCCESS" if ex.success else "FAILED"
        print(f"\nExecution: {status} (attempts: {ex.attempts})")
        print(f"  Script: {ex.script_path}")
        print(f"  Commands: {', '.join(ex.commands_run)}")
        print(f"  Output: {ex.output_summary}")
        if ex.error_summary:
            print(f"  Errors: {ex.error_summary}")


def main():
    """Parse CLI args and kick off the agent."""
    parser = argparse.ArgumentParser(description="Research Agent — analyze local paper projects")
    parser.add_argument(
        "--project",
        required=True,
        help="Path to a project folder containing paper.pdf and repo/",
    )
    parser.add_argument("--question", required=True, help="Question to answer about the paper")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        choices=[DEFAULT_MODEL, ALTERNATE_MODEL],
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set. Create a .env file or export it.", file=sys.stderr)
        sys.exit(1)

    try:
        context = resolve_project(args.project)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    run_research_query(context, args.question, args.model)


if __name__ == "__main__":
    main()
