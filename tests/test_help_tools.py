"""Unit tests for the read_help pure helper (RQ3 static-help variant).

Pure helper only — the ``@function_tool`` wrapper is exercised indirectly via
``read_help_text``, matching the house test style.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from research_agents.tools.help_tools import NO_HELP_TEXT, read_help_text


class ReadHelpTextTests(unittest.TestCase):
    def test_none_path_degrades(self):
        # Non-assisted runs pass no help_path; the agent must be told to proceed.
        self.assertEqual(read_help_text(None), NO_HELP_TEXT)

    def test_missing_file_degrades(self):
        with TemporaryDirectory() as d:
            self.assertEqual(read_help_text(Path(d) / "AGENT_HINTS.md"), NO_HELP_TEXT)

    def test_empty_file_degrades(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "AGENT_HINTS.md"
            p.write_text("   \n", encoding="utf-8")
            self.assertEqual(read_help_text(p), NO_HELP_TEXT)

    def test_reads_real_help(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "AGENT_HINTS.md"
            p.write_text("# hints\nuse the cached v2 weights; numpy<2\n", encoding="utf-8")
            out = read_help_text(p)
            self.assertIn("cached v2 weights", out)
            self.assertIn("numpy<2", out)

    def test_accepts_str_path(self):
        with TemporaryDirectory() as d:
            p = Path(d) / "AGENT_HINTS.md"
            p.write_text("tip", encoding="utf-8")
            self.assertEqual(read_help_text(str(p)), "tip")


if __name__ == "__main__":
    unittest.main()
