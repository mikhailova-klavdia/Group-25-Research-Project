from research_agents.agents.critic_agent import CriticReview, create_critic_agent


def test_critic_review_schema_accepts_install_verdict():
    review = CriticReview(
        verdict="redo_with_install",
        reasoning="The worker hit a missing torch import and did not install it.",
        missing_packages=["torch"],
        suggested_action="Install torch and retry the failed command.",
    )

    assert review.verdict == "redo_with_install"
    assert review.missing_packages == ["torch"]


def test_critic_agent_has_no_tools():
    agent = create_critic_agent()

    assert agent.tools == []
