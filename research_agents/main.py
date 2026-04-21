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

    # Announce the run parameters up-front — mirrored into the log files so
    # we can trace back which model / project / run dir produced which output.
    print(f"Running Research Assistant with {model}...")
    print(f"Project: {context.project_dir}")
    print(f"Paper: {context.paper_path}")
    print(f"Repository: {context.repo_path}")
    print(f"Run: {context.run_id}")
    print(f"Run directory: {context.run_dir}")
    print(f"Workspace: {context.workspace_path}")
    print(f"Question: {question}")
    print("-" * 60)

    # max_turns=150 is deliberately generous: reproducing every experiment
    # in a paper involves reading the PDF, exploring the repo, installing
    # dependencies, staging files, and running+inspecting each experiment.
    # Typical runs land between 30-80 turns; 150 leaves enough headroom for
    # a paper with many experiments or a few retries, without letting a
    # genuinely stuck agent run forever.
    #
    # MaxTurnsExceeded is the SDK's hard stop — when it fires, the agent
    # did NOT produce a ResearchAnswer, so we exit with a non-zero status
    # instead of trying to salvage partial output. This is the right
    # default for batch benchmarking: a timed-out run is a failure, and
    # downstream scripts can distinguish it from a successful run by the
    # exit code.
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
    print(f"\nAnswer:\n{output.answer}")
    print(f"\nReasoning:\n{output.reasoning}")
    print(f"\nSources: {', '.join(output.sources)}")

    if output.experiments:
        print(f"\n{'=' * 60}")
        print(f"EXPERIMENTS ({len(output.experiments)} total)")
        print("=" * 60)
        for i, exp in enumerate(output.experiments, 1):
            status = "SUCCESS" if exp.success else "FAILED"
            print(f"\n--- Experiment {i}: {exp.name} [{status}] ---")
            print(f"  Paper ref:      {exp.paper_reference}")
            print(f"  Scripts:        {', '.join(exp.scripts_used)}")
            print(f"  Commands:       {', '.join(exp.commands_run)}")
            print(f"  Attempts:       {exp.attempts}")
            if exp.key_findings:
                print(f"  Key findings:")
                for finding in exp.key_findings:
                    print(f"    - {finding}")
            if exp.output_files:
                print(f"  Output files:   {', '.join(exp.output_files)}")
            print(f"  Interpretation: {exp.interpretation}")
            if exp.paper_comparison:
                print(f"  vs. paper:      {exp.paper_comparison}")
            if exp.error_summary:
                print(f"  Errors:         {exp.error_summary}")

    if output.overall_interpretation:
        print(f"\nOverall Interpretation:\n{output.overall_interpretation}")
    if output.reproducibility_assessment:
        print(f"\nReproducibility Assessment:\n{output.reproducibility_assessment}")


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

    # Fail fast on missing API key: the SDK would raise a cryptic 401 later.
    # `config.py` reads OPENAI_API_KEY from the environment (with dotenv), so
    # this single check covers both `.env` and exported-var workflows.
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
