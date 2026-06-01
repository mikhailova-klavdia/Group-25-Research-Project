"""Unit tests for the code verifier agent and worker-verifier-critic team.

Pure-function tests only — no live LLM, no Runner calls.
Tests cover the input builder, script extraction, and output model defaults.
"""

import unittest

from research_agents.agents.verifier_agent import VerifierReview
from research_agents.agents.react_agent import ReActAnswer, ReActStep
from research_agents.teams.worker_verifier_critic import (
    _build_verifier_input,
    _extract_exec_outputs,
    _extract_scripts_from_chain,
)


def _make_answer(steps=None, final_answer="0.9649", status="answered"):
    return ReActAnswer(
        chain=steps or [],
        final_answer=final_answer,
        answer_status=status,
    )


def _make_step(step_num, action, observation=""):
    return ReActStep(
        step=step_num,
        thought="thinking",
        action=action,
        observation=observation,
        reflection="reflecting",
    )


class ExtractScriptsTests(unittest.TestCase):
    def test_extracts_write_file_steps(self):
        steps = [
            _make_step(1, 'read_paper()', 'paper text'),
            _make_step(2, 'write_file(relative_path="run.py", content="import numpy")', 'Written to workspace/run.py'),
            _make_step(3, 'execute_command("python run.py")', 'Exit code: 0\n0.9649'),
        ]
        answer = _make_answer(steps=steps)
        scripts = _extract_scripts_from_chain(answer)
        self.assertEqual(len(scripts), 1)
        self.assertEqual(scripts[0]["step"], 2)
        self.assertIn("write_file", scripts[0]["action"])

    def test_no_write_file_returns_empty(self):
        steps = [
            _make_step(1, 'read_paper()'),
            _make_step(2, 'list_repo_files()'),
        ]
        answer = _make_answer(steps=steps)
        self.assertEqual(_extract_scripts_from_chain(answer), [])

    def test_multiple_scripts_extracted(self):
        steps = [
            _make_step(1, 'write_file(relative_path="a.py", content="x=1")'),
            _make_step(2, 'execute_command("python a.py")'),
            _make_step(3, 'write_file(relative_path="b.py", content="y=2")'),
        ]
        answer = _make_answer(steps=steps)
        scripts = _extract_scripts_from_chain(answer)
        self.assertEqual(len(scripts), 2)
        self.assertEqual(scripts[0]["step"], 1)
        self.assertEqual(scripts[1]["step"], 3)


class ExtractExecOutputsTests(unittest.TestCase):
    def test_only_returns_execute_command_outputs(self):
        outputs = [
            "Contents of paper.pdf: blah blah",
            "Exit code: 0\nSTDOUT:\n0.9649",
            "Exit code: 1\nSTDERR:\nModuleNotFoundError",
            "Listed 5 files",
        ]
        exec_outs = _extract_exec_outputs(outputs)
        self.assertEqual(len(exec_outs), 2)
        self.assertIn("0.9649", exec_outs[0]["output"])
        self.assertIn("ModuleNotFoundError", exec_outs[1]["output"])

    def test_empty_outputs_returns_empty(self):
        self.assertEqual(_extract_exec_outputs([]), [])

    def test_no_exec_outputs_returns_empty(self):
        outputs = ["paper text", "repo listing", "workspace listing"]
        self.assertEqual(_extract_exec_outputs(outputs), [])


class BuildVerifierInputTests(unittest.TestCase):
    def test_builds_valid_json_string(self):
        import json
        answer = _make_answer(final_answer="(122, 1280)")
        tool_outputs = ["Exit code: 0\nSTDOUT:\n(122, 1280)"]
        result = _build_verifier_input("What is the shape?", "(122, 1280)", answer, tool_outputs)
        # Must be parseable JSON after the preamble
        json_part = result[result.index("{"):]
        parsed = json.loads(json_part)
        self.assertEqual(parsed["worker_final_answer"], "(122, 1280)")
        self.assertEqual(parsed["ground_truth"], "(122, 1280)")

    def test_handles_none_ground_truth(self):
        import json
        answer = _make_answer()
        result = _build_verifier_input("question", None, answer, [])
        json_part = result[result.index("{"):]
        parsed = json.loads(json_part)
        self.assertEqual(parsed["ground_truth"], "")

    def test_execution_required_answer_has_no_scripts(self):
        import json
        answer = _make_answer(
            final_answer="EXECUTION_REQUIRED — torch not found",
            status="blocked",
        )
        result = _build_verifier_input("Run this", None, answer, [])
        json_part = result[result.index("{"):]
        parsed = json.loads(json_part)
        self.assertEqual(parsed["scripts_written_by_worker"], [])


class VerifierReviewDefaultsTests(unittest.TestCase):
    def test_pass_verdict_defaults(self):
        review = VerifierReview(verdict="pass", reasoning="looks good")
        self.assertEqual(review.verdict, "pass")
        self.assertEqual(review.bugs_found, [])
        self.assertIsNone(review.corrected_answer)
        self.assertEqual(review.corrections_made, [])

    def test_bug_found_fixed_carries_corrected_answer(self):
        review = VerifierReview(
            verdict="bug_found_fixed",
            bugs_found=["ESM-2 BOS token included in first-residue mean"],
            corrected_answer="9.6298",
            corrections_made=["Changed embeddings[0, 0, :] to embeddings[0, 1, :]"],
            reasoning="Row 0 is BOS token; first residue is row 1.",
        )
        self.assertEqual(review.corrected_answer, "9.6298")
        self.assertEqual(len(review.bugs_found), 1)

    def test_unfixable_has_no_corrected_answer(self):
        review = VerifierReview(
            verdict="bug_found_unfixable",
            bugs_found=["numpy 2.x alias np.bool removed"],
            reasoning="Tried numpy<2 install but it failed.",
        )
        self.assertIsNone(review.corrected_answer)
        self.assertEqual(review.verdict, "bug_found_unfixable")


class VerifierAgentFactoryTests(unittest.TestCase):
    def test_agent_has_correct_tools(self):
        from research_agents.agents.verifier_agent import create_verifier_agent
        agent = create_verifier_agent()
        tool_names = {t.name for t in agent.tools}
        # Must have exec tools
        self.assertIn("write_file", tool_names)
        self.assertIn("execute_command", tool_names)
        self.assertIn("read_workspace_file", tool_names)
        self.assertIn("list_workspace_files", tool_names)
        # Must NOT have repo tools — worker already staged everything
        self.assertNotIn("list_repo_files", tool_names)
        self.assertNotIn("read_repo_file", tool_names)
        self.assertNotIn("search_repo", tool_names)

    def test_agent_output_type_is_verifier_review(self):
        from research_agents.agents.verifier_agent import create_verifier_agent, VerifierReview
        agent = create_verifier_agent()
        self.assertIs(agent.output_type, VerifierReview)

    def test_verifier_instructions_contain_all_checklist_items(self):
        from research_agents.agents.verifier_agent import VERIFIER_INSTRUCTIONS
        required_checks = [
            "BOS",           # CHECK 1
            "numpy 2",       # CHECK 2
            "pickle",        # CHECK 3
            "FASTA",         # CHECK 4
            "off-by-one",    # CHECK 5 (lowercase in instructions)
            "curl",          # CHECK 6
        ]
        for term in required_checks:
            self.assertIn(term, VERIFIER_INSTRUCTIONS,
                          f"Expected '{term}' in VERIFIER_INSTRUCTIONS")


class TeamRegistryTests(unittest.TestCase):
    def test_worker_verifier_critic_is_registered(self):
        from research_agents.teams import TEAMS
        self.assertIn("worker-verifier-critic", TEAMS)

    def test_worker_verifier_critic_spec(self):
        from research_agents.teams import TEAMS
        from research_agents.teams.worker_verifier_critic import run_worker_verifier_critic
        spec = TEAMS["worker-verifier-critic"]
        self.assertEqual(spec.name, "worker-verifier-critic")
        self.assertIs(spec.run, run_worker_verifier_critic)
        # Does not pre-download weights — that's worker-critic-plus's job
        self.assertFalse(spec.apply_setup)

    def test_all_teams_still_present(self):
        from research_agents.teams import TEAMS
        expected = {
            "solo",
            "worker-critic",
            "worker-critic-plus",
            "worker-verifier-critic",
            "human-in-the-loop",
        }
        self.assertEqual(set(TEAMS.keys()), expected)


if __name__ == "__main__":
    unittest.main()
