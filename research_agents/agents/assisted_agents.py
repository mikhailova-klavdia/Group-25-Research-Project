"""LLM-assisted ReAct workers (RQ3): the worker-critic and worker-critic-plus-plus
workers, augmented with an ``ask_human`` tool and a prompt section telling them when to
use it.

Paired with a ``HumanChannel`` attached to ``ResearchContext.human`` (e.g.
``SessionFileHuman``, which routes to the Claude Code session), ``ask_human`` lets the
worker request operator assistance when blocked. With no channel attached it degrades to
NO_HUMAN_REPLY, so these agents stay safe to run autonomously too.

Only the worker gains ``ask_human`` — the critic is unchanged. The prompt is the
corresponding baseline/plus-plus prompt plus one appended section; nothing else differs,
so an assisted-vs-baseline comparison isolates the effect of operator assistance.
"""

from agents import Agent

from research_agents.config import DEFAULT_MODEL
from research_agents.hitl import ask_human
from research_agents.project import ResearchContext
from research_agents.agents.react_agent import (
    REACT_INSTRUCTIONS,
    REACT_INSTRUCTIONS_PLUS_PLUS,
    ReActAnswer,
)
from research_agents.tools.paper_tools import read_paper
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


# Appended to the baseline / plus-plus prompt for the assisted variants. Tells the worker
# it has an operator on call and — crucially — to ASK BEFORE giving up. The operator gives
# how-to guidance only, never the answer, so the worker must still run the workflow.
_ASK_HUMAN_SECTION = """

ASKING THE OPERATOR FOR HELP
────────────────────────────
You have an ``ask_human(question)`` tool wired to an expert operator. Call it whenever a
person could unblock you better than guessing — and ALWAYS before you give up or report a
blocker. Good reasons to ask:
  • a model or tool needs a license token, API key, or gated download — ask for an
    open-weight equivalent or workaround (a missing token/license is ALWAYS a reason to
    ask before recording missing_weights / external_download);
  • a dependency will not install (version conflict, build error) — ask for a working
    version or a compatible replacement;
  • the question is ambiguous about what to compute — ask how to interpret it;
  • an operation seems to need a GPU, credential, or network resource you lack — ask for
    the CPU/offline fallback before declaring it impossible;
  • you are about to do something expensive or irreversible — ask for a go/no-go.
When you ask, state what you already tried, the exact error, and one or two concrete
options. Act on the reply immediately. The operator provides operational guidance ONLY —
never the answer value — so you must still run the workflow and read the real output.
"""


_TOOLS = [
    read_paper,
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
    ask_human,
]


def create_react_agent_assisted(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Baseline worker (REACT_INSTRUCTIONS) + ask_human — used by ``worker-critic-assisted``."""
    return Agent(
        name="ReAct Research Assistant (assisted)",
        instructions=REACT_INSTRUCTIONS + _ASK_HUMAN_SECTION,
        tools=list(_TOOLS),
        model=model,
        output_type=ReActAnswer,
    )


def create_react_agent_plus_plus_assisted(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Plus-plus worker (REACT_INSTRUCTIONS_PLUS_PLUS) + ask_human — used by
    ``worker-critic-plus-plus-assisted``."""
    return Agent(
        name="ReAct Research Assistant (plus-plus, assisted)",
        instructions=REACT_INSTRUCTIONS_PLUS_PLUS + _ASK_HUMAN_SECTION,
        tools=list(_TOOLS),
        model=model,
        output_type=ReActAnswer,
    )
