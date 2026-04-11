# Agent definition for the research assistant.
#
# The agent gets four tools (read_paper, list_repo_files, search_repo,
# read_repo_file) and returns structured output via ResearchAnswer.

from pydantic import BaseModel

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.tools.paper_tools import read_paper
from research_agents.tools.repo_tools import list_repo_files, read_repo_file, search_repo


# Structured output the agent must return.
class ResearchAnswer(BaseModel):
    answer: str
    reasoning: str
    sources: list[str]


# System prompt that tells the agent how to behave.
INSTRUCTIONS = """\
You are an expert research assistant specializing in scientific papers and local codebases.

Your workflow:
1. Read the user's question carefully and understand what they are asking.
2. Use the read_paper tool to read the local project paper.
3. Use the repo tools to inspect the local project codebase.
4. Analyze the paper and repository together when both are relevant.
5. Provide a precise, evidence-based answer grounded in the paper and repository.

Guidelines:
- Base your answer strictly on the paper and repository content. Do not fabricate information.
- If the paper does not contain enough information to answer, say so clearly.
- If the repository does not contain enough information to answer, say so clearly.
- Use list_repo_files first when you need orientation, then use search_repo and read_repo_file to inspect specific files.
- Do not download repositories, install dependencies, or execute repository code in this version.
- Treat the local project location as runtime context, not as something the user needs to provide again.
- In your reasoning, reference specific paper sections or specific repository files that support your answer.
- List the local paper path and any relevant repository file paths in your sources.
"""


def create_research_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build a research agent wired up with paper and repo tools."""
    return Agent(
        name="Research Assistant",
        instructions=INSTRUCTIONS,
        tools=[read_paper, list_repo_files, search_repo, read_repo_file],
        model=model,
        output_type=ResearchAnswer,
    )
