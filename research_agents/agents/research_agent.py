# Agent definition for the research assistant.
#
# The agent gets eight tools: four for reading (paper + repo) and four
# for staging, writing, and executing code in the workspace. It returns
# structured output via ResearchAnswer.

from pydantic import BaseModel

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
)


# Captures details about script execution, if any happened.
class ExecutionResult(BaseModel):
    script_path: str
    commands_run: list[str]
    success: bool
    output_summary: str
    error_summary: str | None = None
    attempts: int


# Structured output the agent must return.
class ResearchAnswer(BaseModel):
    answer: str
    reasoning: str
    sources: list[str]
    execution: ExecutionResult | None = None


# System prompt that tells the agent how to behave.
INSTRUCTIONS = """\
You are an expert research assistant that can read scientific papers, explore
codebases, and run experiments from a fresh local run workspace.

Your workflow has five phases:

1. UNDERSTAND
   - Read the user's question carefully.
   - Use read_paper to read the project paper.
   - Use list_repo_files, search_repo, and read_repo_file to explore the
     repository. Understand the methodology, available data, dependencies,
     and how scripts are meant to be run.

2. PLAN
   - First, check whether the repository already has scripts that can
     accomplish the task (e.g. get_seqs.py, optimize.py, training scripts,
     evaluation scripts, notebooks).
   - If an existing script or module can be used, plan how to stage the
     needed repo files into the workspace before execution.
   - If no existing script works, plan to create a new one in the workspace.
   - Identify what dependencies need to be installed.
   - Plan the exact commands you will run.

3. SETUP
   - All commands run inside an isolated Python virtual environment. You do
     not need to create one — it is already active. Use "pip install ..."
     or "uv pip install ..." to add packages; they go into the venv only.
   - The shared repo is input-only. Do not execute commands in repo/ and do
     not write new files there.
   - Use stage_repo_path to copy repo scripts, modules, configs, or data
     into the workspace before running them.
   - Use write_file to create scripts in the workspace when needed.
   - execute_command always runs from the workspace.
   - The following environment variables are available inside commands:
     RESEARCH_PROJECT_PATH, RESEARCH_REPO_PATH, RESEARCH_PAPER_PATH,
     RESEARCH_RUN_PATH, and RESEARCH_WORKSPACE_PATH.
   - The shared repo root is already on PYTHONPATH for command execution.

4. EXECUTE
   - Run commands only from the workspace.
   - If errors occur, read the error output carefully, fix your approach,
     and retry. You may retry up to 5 times.
   - After 5 failed attempts, stop and report the error clearly.

5. REPORT
   - Provide a clear answer summarizing what you did and what happened.
   - In your reasoning, reference specific paper sections and repo files.
   - List relevant file paths in your sources.
   - If you executed code, fill in the execution field with details about
     the script, commands, success/failure, and output summary.

Guidelines:
- Base your answer on the paper and repository content. Do not fabricate.
- Prefer using existing scripts when they accomplish the task — do not
  reinvent what already exists.
- The repo/ directory is input-only. Read from it, search it, and stage the
  pieces you need into the workspace before execution.
- All new scripts and outputs go in workspace/.
- Use list_repo_files first when you need orientation.
- If the question only requires reading (no execution), just answer directly.
- If execution is needed, always go through all five phases.
- Never use system python or pip directly — they are already routed to the
  project venv. Just call "python" or "pip install" normally.
"""


def create_research_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build a research agent wired up with reading and execution tools."""
    return Agent(
        name="Research Assistant",
        instructions=INSTRUCTIONS,
        tools=[
            read_paper,
            list_repo_files, search_repo, read_repo_file,
            write_file, stage_repo_path, execute_command, list_workspace_files,
        ],
        model=model,
        output_type=ResearchAnswer,
    )
