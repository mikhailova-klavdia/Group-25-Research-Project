"""Tests for the team composition registry.

These tests verify the registry's shape and the factory wiring of each
team without invoking any live LLM call.  The actual run paths are
exercised by the smoke tests; here we just make sure that adding a new
team to ``research_agents/teams/`` will Just Work for the dispatcher.
"""

import inspect

import pytest

from research_agents.agents.react_agent import (
    create_react_agent,
    create_react_agent_improved,
    create_react_agent_plus_plus,
)
from research_agents.orchestration import TeamRunResult
from research_agents.teams import DEFAULT_TEAM, TEAMS, TeamSpec
from research_agents.teams.human_in_the_loop import run_human_in_the_loop
from research_agents.teams.solo import run_solo
from research_agents.teams.testing_worker_critic import run_testing_worker_critic
from research_agents.teams.worker_critic import run_worker_critic
from research_agents.teams.worker_critic_plus import run_worker_critic_plus
from research_agents.teams.worker_critic_plus_plus_hitl import run_worker_critic_plus_plus_hitl
from research_agents.teams.worker_critic_plus_plus import run_worker_critic_plus_plus


def test_registry_contains_all_shipped_teams():
    """All shipped teams are registered by name."""
    assert set(TEAMS.keys()) == {
        "solo",
        "worker-critic",
        "worker-critic-plus",
        "worker-verifier-critic",
        "testing-worker-critic",
        "worker-critic-plus-plus",
        "human-in-the-loop",
        "worker-critic-plus-plus-hitl",
        "worker-critic-assisted",
        "worker-critic-plus-plus-assisted",
        "worker-critic-readme",
        "worker-critic-plus-plus-readme",
        "worker-env-critic",
    }


def test_default_team_is_solo():
    """Per the architecture review, the simplest team is the CLI default."""
    assert DEFAULT_TEAM == "solo"
    assert DEFAULT_TEAM in TEAMS


@pytest.mark.parametrize("name", list(TEAMS.keys()))
def test_team_spec_shape(name):
    """Every team spec has the fields the dispatcher relies on."""
    spec = TEAMS[name]
    assert isinstance(spec, TeamSpec)
    assert spec.name == name
    assert spec.description  # non-empty
    assert callable(spec.run)
    assert isinstance(spec.apply_setup, bool)


def test_only_plus_teams_apply_setup():
    """The worker-critic-plus and worker-critic-plus-plus teams trigger setup scripts."""
    assert TEAMS["solo"].apply_setup is False
    assert TEAMS["worker-critic"].apply_setup is False
    assert TEAMS["worker-critic-plus"].apply_setup is True
    assert TEAMS["testing-worker-critic"].apply_setup is True
    assert TEAMS["worker-critic-plus-plus"].apply_setup is True
    # The human-in-the-loop team deliberately does NOT use the config file;
    # it sets up the venv interactively instead.
    assert TEAMS["human-in-the-loop"].apply_setup is False
    assert TEAMS["worker-critic-plus-plus-hitl"].apply_setup is False


@pytest.mark.parametrize(
    "name,run_fn",
    [
        ("solo", run_solo),
        ("worker-critic", run_worker_critic),
        ("worker-critic-plus", run_worker_critic_plus),
        ("testing-worker-critic", run_testing_worker_critic),
        ("worker-critic-plus-plus", run_worker_critic_plus_plus),
        ("human-in-the-loop", run_human_in_the_loop),
        ("worker-critic-plus-plus-hitl", run_worker_critic_plus_plus_hitl),
    ],
)
def test_team_run_fn_matches_module(name, run_fn):
    """Registry entries point at the module-level run functions."""
    assert TEAMS[name].run is run_fn


@pytest.mark.parametrize(
    "run_fn",
    [
        run_solo,
        run_worker_critic,
        run_worker_critic_plus,
        run_testing_worker_critic,
        run_worker_critic_plus_plus,
        run_human_in_the_loop,
        run_worker_critic_plus_plus_hitl,
    ],
)
def test_team_run_signatures_are_uniform(run_fn):
    """Dispatcher relies on every team having the same call signature.

    The 5 positional/keyword params are: context, question, ground_truth,
    entry_id, model.  If a team adds new arguments they must be optional
    (with defaults) so the dispatcher in react_main.py still works.
    """
    sig = inspect.signature(run_fn)
    required = [name for name, p in sig.parameters.items() if p.default is inspect.Parameter.empty]
    assert required == ["context", "question", "ground_truth", "entry_id", "model"]


def test_worker_critic_uses_baseline_factory():
    """The worker-critic team must build a worker from create_react_agent."""
    src = inspect.getsource(run_worker_critic)
    assert "create_react_agent" in src
    assert "create_react_agent_improved" not in src


def test_worker_critic_plus_uses_improved_factory():
    """The worker-critic-plus team must build a worker from create_react_agent_improved."""
    src = inspect.getsource(run_worker_critic_plus)
    assert "create_react_agent_improved" in src


def test_testing_worker_critic_uses_testing_aware_factory():
    """The testing team must hand off to the testing-aware execution worker."""
    src = inspect.getsource(run_testing_worker_critic)
    assert "create_execution_agent_with_testing" in src


def test_worker_critic_plus_plus_uses_plus_plus_factory():
    """The worker-critic-plus-plus team must build a worker from create_react_agent_plus_plus."""
    src = inspect.getsource(run_worker_critic_plus_plus)
    assert "create_react_agent_plus_plus" in src


def test_baseline_and_improved_factories_produce_distinct_prompts():
    """Sanity: all three prompt variants are genuinely distinct."""
    baseline = create_react_agent()
    improved = create_react_agent_improved()
    plus_plus = create_react_agent_plus_plus()
    assert isinstance(baseline.instructions, str)
    assert isinstance(improved.instructions, str)
    assert isinstance(plus_plus.instructions, str)
    assert baseline.instructions != improved.instructions
    assert baseline.instructions != plus_plus.instructions
    assert improved.instructions != plus_plus.instructions
    # Improved has ESM-2 BOS/EOS strip and synthesis carve-out.
    assert "embeddings[1:-1]" in improved.instructions
    assert "Tool-deterministic synthesis carve-out" in improved.instructions
    # Plus-plus has the static-files gate and second-strategy fallbacks.
    assert "ANSWER FROM STATIC FILES" in plus_plus.instructions
    assert "TRY A SECOND STRATEGY" in plus_plus.instructions


def test_team_run_result_type_is_shared():
    """All teams must return the same TeamRunResult so the dispatcher works."""
    # We can't easily call the run functions without an LLM, but we can
    # check the type-annotation surface matches.
    for run_fn in (
        run_solo,
        run_worker_critic,
        run_worker_critic_plus,
        run_testing_worker_critic,
        run_worker_critic_plus_plus,
        run_human_in_the_loop,
        run_worker_critic_plus_plus_hitl,
    ):
        sig = inspect.signature(run_fn)
        ret = sig.return_annotation
        assert ret is TeamRunResult, f"{run_fn.__name__} returns {ret}, expected TeamRunResult"
