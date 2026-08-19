"""README-assisted ReAct workers (RQ3, static-help variant): the worker-critic and
worker-critic-plus-plus workers, augmented with a ``read_help`` tool and a prompt section
telling them to read and follow the per-paper help file (``AGENT_HINTS.md``).

Unlike the interactive ``ask_human`` variant, the help here is STATIC: a per-paper README
of steering tips (authored from analysis of the teams' earlier autonomous failures) is
placed alongside the repo. The README-assisted team functions also inject the help text as
a preamble to the worker's input, so the hints are reliably in-context even if the model
forgets to call ``read_help`` (we observed that appended-only nudges get ignored). The
tips are guidance only — never the answer — so the worker still runs the real workflow.

Only the worker changes (prompt + the read_help tool); the critic is untouched, so an
assisted-vs-autonomous comparison isolates the effect of the help README.
"""

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.agents.react_agent import (
    REACT_INSTRUCTIONS,
    REACT_INSTRUCTIONS_PLUS_PLUS,
    ReActAnswer,
)
from research_agents.tools.paper_tools import read_paper
from research_agents.tools.help_tools import read_help
from research_agents.tools.repo_tools import (
    find_repo_files,
    list_repo_files,
    read_repo_file,
    resolve_repo_path,
    search_repo,
)
from research_agents.tools.exec_tools import (
    cache_workspace_artifact,
    write_file,
    stage_repo_path,
    execute_command,
    list_workspace_files,
    list_paper_artifacts,
    read_workspace_file,
    stage_paper_artifact,
    venv_status,
)


# Appended to the baseline / plus-plus prompt for the README-assisted variants. The help
# text is ALSO prepended to the worker's input by the team function, so this section frames
# how to treat it. Tips steer; they are not the answer, so the worker must still execute.
_READ_HELP_SECTION = """

TASK HINTS FILE (READ FIRST)
────────────────────────────
A help file of expert tips for THIS paper's tasks has been attached. Your input begins with
a "TASK HINTS" block containing it, and you can re-read it any time with the ``read_help``
tool. Treat these hints as authoritative steering from someone who has seen earlier attempts
at these tasks:
  • They tell you where required data/weights already live (so you don't wrongly conclude a
    file is missing or that something must be downloaded), which dependencies to install
    (e.g. a NumPy 1.x/2.x pin), and specific pitfalls that produced wrong answers before.
  • Follow them BEFORE giving up or reporting a blocker, and re-check them if a result looks
    off (wrong magnitude, off-by-one, etc.).
  • They are guidance ONLY — never the final answer. You must still run the real workflow
    and read the actual output; ground every number in a successful execution.
"""


_TOOLS = [
    read_paper,
    read_help,
    list_repo_files,
    find_repo_files,
    resolve_repo_path,
    search_repo,
    read_repo_file,
    write_file,
    stage_repo_path,
    execute_command,
    list_workspace_files,
    read_workspace_file,
    list_paper_artifacts,
    stage_paper_artifact,
    cache_workspace_artifact,
    venv_status,
]


def create_react_agent_readme(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Baseline worker (REACT_INSTRUCTIONS) + read_help — used by ``worker-critic-readme``."""
    return Agent(
        name="ReAct Research Assistant (readme-assisted)",
        instructions=REACT_INSTRUCTIONS + _READ_HELP_SECTION,
        tools=list(_TOOLS),
        model=model,
        output_type=ReActAnswer,
    )


def create_react_agent_plus_plus_readme(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Plus-plus worker (REACT_INSTRUCTIONS_PLUS_PLUS) + read_help — used by
    ``worker-critic-plus-plus-readme``."""
    return Agent(
        name="ReAct Research Assistant (plus-plus, readme-assisted)",
        instructions=REACT_INSTRUCTIONS_PLUS_PLUS + _READ_HELP_SECTION,
        tools=list(_TOOLS),
        model=model,
        output_type=ReActAnswer,
    )
