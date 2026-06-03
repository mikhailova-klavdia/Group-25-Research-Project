# CLI entry point for running research queries.
#
# Usage:
#   uv run python -m research_agents.main \
#     --project papers/<slug> --question "..."

import argparse
import sys
from pathlib import Path

from agents import Runner
from agents.exceptions import MaxTurnsExceeded, ModelRefusalError

from research_agents.config import OPENAI_API_KEY, DEFAULT_MODEL, ALTERNATE_MODEL
from research_agents.agents.research_agent import INSTRUCTIONS
from research_agents.agents.research_agent import create_research_agent
from research_agents.project import ResearchContext, resolve_project
from research_agents.token_utils import append_cost_log, estimate_tokens, print_token_report
from research_agents.tracing import enable_local_tracing


def run_research_query(
    context: ResearchContext,
    question: str,
    model: str,
    trace: bool = False,
):
    """Run the agent on a single question and print the result.

    When ``trace`` is True, every span and trace event produced by the
    SDK is written to ``runs/<run-id>/trace.jsonl`` for post-mortem
    inspection.  The path is printed at the end of the run.  When
    False (the default), tracing follows whatever the SDK is
    configured to do — which is the OpenAI cloud dashboard by default.
    """
    # Enable local tracing BEFORE the agent is constructed so every
    # span — including the outer trace wrapper the SDK creates around
    # Runner.run_sync — is captured.  Wiring this later would miss
    # the first few events.
    trace_path: Path | None = None
    if trace:
        trace_path = enable_local_tracing(context.run_dir / "trace.jsonl")

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
    #
    # ModelRefusalError is treated the same way. Since openai-agents 0.15,
    # a model refusal on a structured-output agent (i.e. one with
    # output_type=) raises immediately instead of silently retrying until
    # the turn limit. A refusal still produces no ResearchAnswer, so it
    # gets the same non-zero exit so the batch harness sees it as a failed
    # run rather than a successful empty one.
    pre_estimate = estimate_tokens(INSTRUCTIONS, question, model)
    print(f"Pre-run token estimate (tiktoken): ~{pre_estimate:,}")
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
    except ModelRefusalError as exc:
        print(
            f"\nError: Model refused to answer the question: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Partial output was not saved.", file=sys.stderr)
        sys.exit(130)

    output = result.final_output
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
    # --- Token usage ---
    print(f"\nAnswer:\n{output.answer}")
    print(f"\nReasoning:\n{output.reasoning}")
    print(f"\nSources: {', '.join(output.sources)}")
    # Surface execution_attempted explicitly so readers (and the future
    # batch grader) can tell "no code was ever run" apart from "code
    # was run and every attempt failed" — both scenarios can produce
    # empty or all-failing experiments lists.
    print(f"\nExecution attempted: {output.execution_attempted}")

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
                print("  Key findings:")
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

    # Printed last so it's the final line of normal output and easy to
    # copy into a follow-up `cat` / `jq` invocation.  Only emitted when
    # --trace was set; otherwise this block is silent.
    if trace_path is not None:
        print(f"\nTrace log: {trace_path}")


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
    # Opt-in local tracing.  Off by default because the SDK's built-in
    # tracing goes to platform.openai.com/traces — which requires an
    # OpenAI dashboard login not everyone has.  When --trace is set,
    # the default processor is replaced with a JSONL writer under the
    # run dir, and no traces leave the local machine.
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Write a local trace log (runs/<run-id>/trace.jsonl) "
        "instead of sending traces to the OpenAI dashboard.",
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

    run_research_query(context, args.question, args.model, trace=args.trace)


if __name__ == "__main__":
    main()
