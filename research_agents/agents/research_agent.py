from pydantic import BaseModel

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.tools.paper_tools import download_and_read_paper


class ResearchAnswer(BaseModel):
    answer: str
    reasoning: str
    sources: list[str]


INSTRUCTIONS = """\
You are an expert research assistant specializing in scientific papers.

Your workflow:
1. Read the user's question carefully and understand what they are asking.
2. Use the download_and_read_paper tool to fetch and read the provided paper.
3. Analyze the paper's content — methodology, results, and conclusions.
4. Provide a precise, evidence-based answer grounded in the paper's content.

Guidelines:
- Base your answer strictly on the paper's content. Do not fabricate information.
- If the paper does not contain enough information to answer, say so clearly.
- If the tool output indicates that only the abstract and metadata were available \
(not the full paper), explicitly state this limitation in your reasoning.
- In your reasoning, reference specific parts of the paper that support your answer.
- List the paper URL in your sources.
"""


def create_research_agent(model: str = DEFAULT_MODEL) -> Agent:
    return Agent(
        name="Research Assistant",
        instructions=INSTRUCTIONS,
        tools=[download_and_read_paper],
        model=model,
        output_type=ResearchAnswer,
    )
