# ReAct agent for Paper2AgentBench evaluation.
#
# Forces the agent to produce explicit Thought / Action / Observation /
# Reflection steps for every tool call, then collects the full chain into
# the structured output alongside a final answer to the benchmark question.
#
# Usage:
#   uv run python -m research_agents.react_main \
#     --project papers/<slug> \
#     --question "..." \
#     --ground-truth "..." \
#     --id REPO_001 \
#     --biorxiv-url "https://biorxiv.org/..."

from pydantic import BaseModel, Field

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.tools.paper_tools import read_paper
from research_agents.tools.repo_tools import list_repo_files, read_repo_file, search_repo
from research_agents.tools.exec_tools import (
    write_file,
    stage_repo_path,
    execute_command,
    list_workspace_files,
    read_workspace_file,
)


# --- Structured output models ---


class ReActStep(BaseModel):
    """One Thought → Action → Observation → Reflection cycle."""

    step: int = Field(description="Step number, starting from 1")
    thought: str = Field(
        description="What you intend to do in this step and why, "
        "written BEFORE calling the tool"
    )
    action: str = Field(
        description="The exact tool call or command you executed, "
        "e.g. 'read_paper()' or 'execute_command(\"python predict.py\")'"
    )
    observation: str = Field(
        description="Concise summary of what the tool returned (truncate long outputs)"
    )
    reflection: str = Field(
        description="What you conclude from this observation and "
        "how it shapes the next step"
    )


class ReActAnswer(BaseModel):
    """Top-level output for a single Paper2AgentBench question."""

    chain: list[ReActStep] = Field(
        description="All T/A/O/R steps taken to reach the final answer. "
        "Every tool call must appear as its own step."
    )
    final_answer: str = Field(
        description="Direct, concise answer to the benchmark question. "
        "For yes/no questions use 'Yes' or 'No'. "
        "For numeric questions include the value and units. "
        "For name/method questions give the exact name from the paper."
    )


# --- System prompt ---


REACT_INSTRUCTIONS = """\
You are an expert research assistant that reads scientific papers and their
code repositories to answer benchmark questions.

You MUST answer the question by working through a series of explicit
Thought / Action / Observation / Reflection (T/A/O/R) steps.

CRITICAL RULES FOR THE CHAIN
─────────────────────────────
1. Record EVERY tool call as its own step — do not batch multiple calls
   into one step.
2. For each step, fill in all four fields in order:
   • thought     — what you intend to do and WHY, written BEFORE the call
   • action      — the exact tool call, e.g. read_paper() or
                   execute_command("python run.py --flag")
   • observation — concise summary of what the tool returned
   • reflection  — what you conclude and what you will do next
3. Number steps sequentially starting at 1.
4. Aim for at least 3 steps; complex questions typically need 5–15.

WORKFLOW
────────
1. UNDERSTAND  — Call read_paper() first. Identify what the question is
                 asking. Decide whether execution is required.

2. EXPLORE     — Use list_repo_files(), search_repo(), and read_repo_file()
                 to locate relevant scripts, configs, and data.

3. EXECUTE     — If the question requires running code:
   • stage_repo_path() to copy scripts/data into workspace/
   • execute_command() to install dependencies and run experiments
   • read_workspace_file() to inspect output files
   • Retry failures up to 5 times per experiment; record each attempt.

4. ANSWER      — Set final_answer to a direct, concise answer:
   • Yes / No for boolean questions
   • The exact numeric value (with units) for numeric questions
   • The exact method or model name for identification questions
   • A short phrase for other questions

INTEGRITY RULES
───────────────
- Base every observation and final_answer on what you actually read or ran.
- Never copy paper-reported numbers into key findings as if you produced them.
- If execution was required but failed, say so in the final_answer and explain
  what was blocked.
- Do not fabricate tool outputs or results.
"""


def create_react_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the ReAct research agent."""
    return Agent(
        name="ReAct Research Assistant",
        instructions=REACT_INSTRUCTIONS,
        tools=[
            read_paper,
            list_repo_files, search_repo, read_repo_file,
            write_file, stage_repo_path, execute_command,
            list_workspace_files, read_workspace_file,
        ],
        model=model,
        output_type=ReActAnswer,
    )
