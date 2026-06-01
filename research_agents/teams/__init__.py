# Composable agent teams for ReAct evaluation.
#
# A "team" is a named composition of one or more agents plus the
# orchestration that runs them.  Every team's run function has the same
# signature, so the CLI dispatcher (``react_main.py``) and downstream
# comparison scripts don't care which team produced a chain JSON — they
# read the ``team`` field at the top of the record and treat the rest
# uniformly.
#
# Adding a new team
# -----------------
# 1. Write a new module under ``research_agents/teams/`` exposing a
#    ``run(context, question, ground_truth, entry_id, model)`` function
#    that returns a ``TeamRunResult``.
# 2. Register it in the ``TEAMS`` dict below with a unique short name,
#    a human-readable description, and the ``apply_setup`` flag that says
#    whether ``resolve_project`` should honor the per-paper ``[setup]``
#    table (typically ``True`` for variants that download model weights
#    up front, ``False`` otherwise).
# 3. Use it from the CLI with ``--team <your-name>``.
#
# Five teams ship today, in increasing complexity:
#   * ``solo`` — single ReAct worker, no critic, no install retry.
#   * ``worker-critic`` — two-agent system (worker + LLM critic +
#     deterministic missing-module install retry).
#   * ``worker-critic-plus`` — same shape as worker-critic but with the
#     improved-variant prompt and up-front setup-script downloads.
#   * ``worker-verifier-critic`` — three-agent system: worker +
#     code verifier (bug checklist) + critic. The verifier catches
#     specific numeric/indexing bugs that the critic misses because the
#     chain looks real but the script indexing is wrong.
#   * ``human-in-the-loop`` — two-stage setup-crew → execution-crew that
#     can ask a human for help (no config file).

from collections.abc import Callable
from dataclasses import dataclass

from research_agents.orchestration import TeamRunResult
from research_agents.project import ResearchContext
from research_agents.teams.human_in_the_loop import run_human_in_the_loop
from research_agents.teams.solo import run_solo
from research_agents.teams.worker_critic import run_worker_critic
from research_agents.teams.worker_critic_plus import run_worker_critic_plus
from research_agents.teams.worker_verifier_critic import run_worker_verifier_critic


# A team's run function takes a context + a question and returns a
# ``TeamRunResult``.  The signature is repeated in each team's module
# docstring; the type alias here is for static-checker friendliness.
TeamRunFunction = Callable[
    [ResearchContext, str, str | None, str, str],
    TeamRunResult,
]


@dataclass(frozen=True)
class TeamSpec:
    """Metadata + the run callable for one composable team.

    ``apply_setup`` is the only flag that affects venv creation; the
    rest of the per-team behavior lives inside the ``run`` function.
    Frozen so the registry can't be mutated by accident at runtime.
    """

    name: str
    description: str
    run: TeamRunFunction
    apply_setup: bool


# Registry — keys are the CLI-facing short names.  Order is significant
# only for ``--help`` listing; the dispatch is purely keyed.
TEAMS: dict[str, TeamSpec] = {
    "solo": TeamSpec(
        name="solo",
        description=(
            "Single ReAct worker; no critic, no automatic dependency install retry. "
            "Matches the legacy `--no-critic` path."
        ),
        run=run_solo,
        apply_setup=False,
    ),
    "worker-critic": TeamSpec(
        name="worker-critic",
        description=(
            "Two agents: ReAct worker + LLM critic, with deterministic missing-module "
            "install retry before the critic runs. Reproduces the 2026-05-28 baseline."
        ),
        run=run_worker_critic,
        apply_setup=False,
    ),
    "worker-critic-plus": TeamSpec(
        name="worker-critic-plus",
        description=(
            "Same shape as worker-critic but with the improved-variant prompt "
            "(ESM-2 BOS/EOS strip + tool-deterministic synthesis carve-out) and "
            "up-front venv setup scripts (model-weight downloads, framework warmups)."
        ),
        run=run_worker_critic_plus,
        apply_setup=True,
    ),
    "worker-verifier-critic": TeamSpec(
        name="worker-verifier-critic",
        description=(
            "Three agents: improved ReAct worker + code verifier + LLM critic. "
            "The verifier checks a finite bug checklist (ESM-2 BOS/EOS indexing, "
            "numpy 2.x removed aliases, Python 2 pickle encoding, FASTA counting, "
            "off-by-one after filtering, curl redirect failures) derived from "
            "annotation of 65 benchmark chains. When it finds a fixable bug it "
            "rewrites the script, re-executes in the existing workspace, and the "
            "corrected answer replaces the worker's answer before the critic sees it."
        ),
        run=run_worker_verifier_critic,
        apply_setup=False,
    ),
    "human-in-the-loop": TeamSpec(
        name="human-in-the-loop",
        description=(
            "Two-stage human-in-the-loop crew: a setup engineer prepares the venv "
            "interactively (no config file — it discovers deps from the repo and asks "
            "the operator when stuck), hands a typed EnvReport to a ReAct execution "
            "worker + integrity critic; both can chat with the human via ask_human. "
            "Run interactively with `python -m research_agents.hitl_main`. Headless "
            "runs degrade ask_human to autonomous."
        ),
        run=run_human_in_the_loop,
        apply_setup=False,
    ),
}


DEFAULT_TEAM = "solo"


__all__ = ["TEAMS", "DEFAULT_TEAM", "TeamSpec", "TeamRunResult", "TeamRunFunction"]
