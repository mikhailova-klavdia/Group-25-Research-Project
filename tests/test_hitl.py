"""Unit tests for the human-in-the-loop plumbing.

Pure helpers only — no live LLM and no SDK Runner, matching the house test
style (the ``ask_human`` ``@function_tool`` wrapper is exercised indirectly
via its pure helper ``ask_human_text``).
"""

import asyncio
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from research_agents.agents.hitl_agents import (
    EnvReport,
    TriageReport,
    format_env_report_for_worker,
    format_triage_for_downstream,
)
from research_agents.agents.react_agent import ReActAnswer
from research_agents.hitl import (
    NO_HUMAN_REPLY,
    ConsoleHuman,
    ConsoleReporter,
    FakeHuman,
    HumanChannel,
    apply_integrity_guard,
    ask_human_text,
    execution_grounded,
)
from research_agents.project import ResearchContext
from research_agents.teams.human_in_the_loop import ReportingCapture


class AskHumanTextTests(unittest.TestCase):
    def test_degrades_to_autonomous_when_no_human(self):
        # The headless/batch path passes human=None; the agent must be told
        # to proceed on its own rather than wait for input that can't come.
        self.assertEqual(ask_human_text(None, "what now?"), NO_HUMAN_REPLY)

    def test_returns_prefixed_human_reply(self):
        human = FakeHuman(["use the open V2 model"])
        out = ask_human_text(human, "license gate hit, options?")
        self.assertEqual(out, "HUMAN REPLY: use the open V2 model")
        self.assertEqual(human.asked, ["license gate hit, options?"])

    def test_passes_agent_label_without_error(self):
        human = FakeHuman(["ok"])
        self.assertEqual(ask_human_text(human, "q", agent="setup"), "HUMAN REPLY: ok")


class FakeHumanTests(unittest.TestCase):
    def test_sequences_replies_then_falls_back(self):
        human = FakeHuman(["first", "second"])
        self.assertEqual(human.ask("q1"), "first")
        self.assertEqual(human.ask("q2"), "second")
        self.assertEqual(human.ask("q3"), "(no more scripted replies)")
        self.assertEqual(human.asked, ["q1", "q2", "q3"])

    def test_satisfies_human_channel_protocol(self):
        human: HumanChannel = FakeHuman([])
        self.assertTrue(hasattr(human, "ask"))


class ConsoleHumanTests(unittest.TestCase):
    def test_reads_and_strips_line_from_stdin(self):
        with patch("builtins.input", return_value="  use V2  "):
            self.assertEqual(ConsoleHuman().ask("q"), "use V2")

    def test_empty_input_returns_proceed_note(self):
        with patch("builtins.input", return_value=""):
            self.assertIn("proceed", ConsoleHuman().ask("q").lower())

    def test_eof_degrades_to_no_human(self):
        with patch("builtins.input", side_effect=EOFError):
            self.assertEqual(ConsoleHuman().ask("q"), NO_HUMAN_REPLY)


class EnvReportTests(unittest.TestCase):
    def test_defaults(self):
        env = EnvReport(venv_ready=True)
        self.assertTrue(env.venv_ready)
        self.assertEqual(env.installed_packages, [])
        self.assertEqual(env.verified_imports, [])
        self.assertEqual(env.downloaded_artifacts, [])
        self.assertEqual(env.known_gaps, [])
        self.assertEqual(env.notes, "")
        self.assertEqual(env.human_consults, [])

    def test_format_includes_gaps_notes_and_imports(self):
        env = EnvReport(
            venv_ready=True,
            installed_packages=["tabpfn"],
            verified_imports=["import tabpfn"],
            known_gaps=["default weights license-gated; use V2"],
            notes="run with create_default_for_version(V2)",
            human_consults=["Q: token? A: use V2"],
        )
        text = format_env_report_for_worker(env)
        self.assertIn("venv_ready: True", text)
        self.assertIn("tabpfn", text)
        self.assertIn("KNOWN GAPS", text)
        self.assertIn("license-gated", text)
        self.assertIn("create_default_for_version", text)
        self.assertIn("human guidance", text)

    def test_format_minimal_report_omits_optional_sections(self):
        text = format_env_report_for_worker(EnvReport(venv_ready=False))
        self.assertIn("venv_ready: False", text)
        self.assertNotIn("KNOWN GAPS", text)
        self.assertNotIn("installed:", text)


class ResearchContextHumanFieldTests(unittest.TestCase):
    def _ctx(self, **overrides):
        base = dict(
            project_dir=Path("/x"),
            paper_path=Path("/x/paper.pdf"),
            repo_path=Path("/x/repo"),
            run_id="r",
            run_dir=Path("/x/runs/r"),
            workspace_path=Path("/x/runs/r/workspace"),
            venv_path=Path("/x/.venv"),
            artifacts_path=Path("/x/.artifacts"),
        )
        base.update(overrides)
        return ResearchContext(**base)

    def test_human_defaults_to_none(self):
        self.assertIsNone(self._ctx().human)

    def test_human_can_be_attached(self):
        human = FakeHuman(["hi"])
        ctx = self._ctx(human=human)
        self.assertIs(ctx.human, human)

    def test_construction_without_human_is_unaffected(self):
        # The additive field must not break construction that predates it.
        ctx = self._ctx()
        self.assertEqual(ctx.run_id, "r")
        self.assertIsNone(ctx.human)

    def test_reporter_defaults_to_none_and_can_be_attached(self):
        self.assertIsNone(self._ctx().reporter)
        rep = ConsoleReporter()
        ctx = self._ctx(reporter=rep)
        self.assertIs(ctx.reporter, rep)


class TriageReportTests(unittest.TestCase):
    def test_defaults(self):
        t = TriageReport(needs_execution=False)
        self.assertFalse(t.needs_execution)
        self.assertEqual(t.rationale, "")
        self.assertEqual(t.repo_overview, "")
        self.assertEqual(t.relevant_paths, [])
        self.assertEqual(t.human_consults, [])

    def test_format_includes_overview_and_paths(self):
        t = TriageReport(
            needs_execution=True,
            rationale="asks to compute a value",
            repo_overview="an R causal-forest package",
            relevant_paths=["r-package/grf/R/forest_summary.R"],
        )
        text = format_triage_for_downstream(t)
        self.assertIn("REPO SCOUT NOTES", text)
        self.assertIn("an R causal-forest package", text)
        self.assertIn("forest_summary.R", text)


class ExecutionGroundedTests(unittest.TestCase):
    def test_empty_answer_is_not_grounded(self):
        self.assertFalse(execution_grounded("", ["Exit code: 0\n\nSTDOUT:\n0.97"]))

    def test_no_successful_command_is_not_grounded(self):
        # A paper read + a FAILED command → no execution evidence (the binoculars case).
        outs = [
            "Contents of paper.pdf:\n... machine-generated text ...",
            "Exit code: 1\n\nSTDERR:\nModuleNotFoundError",
        ]
        self.assertFalse(execution_grounded("AI-generated", outs))

    def test_successful_command_is_grounded(self):
        outs = ["Contents of paper.pdf:\n...", "Exit code: 0\n\nSTDOUT:\n0.9649\n"]
        self.assertTrue(execution_grounded("0.9649", outs))


class IntegrityGuardTests(unittest.TestCase):
    def _answer(self, **kw):
        base = dict(chain=[], final_answer="AI-generated", answer_status="answered")
        base.update(kw)
        return ReActAnswer(**base)

    def test_downgrades_ungrounded_execution_answer(self):
        outs = ["Contents of paper.pdf:\n...", "Exit code: 1\n\nSTDERR:\nfail"]
        guarded = apply_integrity_guard(self._answer(), outs, needs_execution=True)
        self.assertEqual(guarded.answer_status, "blocked")
        self.assertTrue(guarded.final_answer.startswith("EXECUTION_REQUIRED"))

    def test_keeps_grounded_execution_answer(self):
        ans = self._answer(final_answer="0.9649")
        guarded = apply_integrity_guard(
            ans, ["Exit code: 0\n\nSTDOUT:\n0.9649\n"], needs_execution=True
        )
        self.assertIs(guarded, ans)

    def test_no_op_for_read_only(self):
        ans = self._answer()
        self.assertIs(apply_integrity_guard(ans, [], needs_execution=False), ans)

    def test_no_op_for_already_blocked(self):
        ans = self._answer(answer_status="blocked", final_answer="EXECUTION_REQUIRED — x")
        self.assertIs(apply_integrity_guard(ans, [], needs_execution=True), ans)


class ConsoleReporterTests(unittest.TestCase):
    def test_stage_and_detail_print(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            reporter = ConsoleReporter()
            reporter.stage("Setting up")
            reporter.detail("running a command")
        out = buf.getvalue()
        self.assertIn("Setting up", out)
        self.assertIn("running a command", out)


class _RecordingReporter:
    def __init__(self):
        self.stages: list[str] = []
        self.details: list[str] = []

    def stage(self, message):
        self.stages.append(message)

    def detail(self, message):
        self.details.append(message)


class _FakeTool:
    def __init__(self, name):
        self.name = name


class ReportingCaptureTests(unittest.TestCase):
    def test_reports_friendly_label_on_tool_start(self):
        rep = _RecordingReporter()
        cap = ReportingCapture(rep)
        asyncio.run(cap.on_tool_start(None, None, _FakeTool("execute_command")))
        self.assertIn("running a command", rep.details)

    def test_still_records_output_on_tool_end(self):
        cap = ReportingCapture(None)
        asyncio.run(cap.on_tool_end(None, None, _FakeTool("x"), "result-text"))
        self.assertEqual(cap.outputs, ["result-text"])

    def test_none_reporter_is_silent_without_error(self):
        cap = ReportingCapture(None)
        asyncio.run(cap.on_tool_start(None, None, _FakeTool("read_paper")))  # must not raise


if __name__ == "__main__":
    unittest.main()
