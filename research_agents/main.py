import argparse
import sys

from agents import Runner

from research_agents.config import OPENAI_API_KEY, DEFAULT_MODEL, ALTERNATE_MODEL
from research_agents.agents.research_agent import create_research_agent


def run_research_query(paper: str, question: str, model: str):
    agent = create_research_agent(model=model)
    prompt = f"Paper URL: {paper}\n\nQuestion: {question}"

    print(f"Running Research Assistant with {model}...")
    print(f"Paper: {paper}")
    print(f"Question: {question}")
    print("-" * 60)

    result = Runner.run_sync(agent, prompt)

    output = result.final_output
    print(f"\nAnswer: {output.answer}")
    print(f"\nReasoning: {output.reasoning}")
    print(f"\nSources: {', '.join(output.sources)}")


def main():
    parser = argparse.ArgumentParser(description="Research Agent — analyze scientific papers")
    parser.add_argument("--paper", required=True, help="URL or local file path of the paper to analyze")
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

    run_research_query(args.paper, args.question, args.model)


if __name__ == "__main__":
    main()
