import tempfile
import unittest
from pathlib import Path

from fpdf import FPDF

from research_agents.tools import paper_tools, repo_tools
from research_agents.tools.paper_tools import read_paper_text
from research_agents.tools.repo_tools import (
    list_repo_files_text,
    read_repo_file_text,
    search_repo_text,
)


class RepoToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmpdir.name) / "repo"
        self.repo_root.mkdir()

        (self.repo_root / "src").mkdir()
        (self.repo_root / "src" / "main.py").write_text(
            "def build_pipeline():\n    return 'ok'\n",
            encoding="utf-8",
        )
        (self.repo_root / "README.md").write_text(
            "This repository defines the main model pipeline.\n",
            encoding="utf-8",
        )
        (self.repo_root / ".git").mkdir()
        (self.repo_root / ".git" / "config").write_text("secret=true\n", encoding="utf-8")
        (self.repo_root / "node_modules").mkdir()
        (self.repo_root / "node_modules" / "ignored.js").write_text(
            "build_pipeline\n",
            encoding="utf-8",
        )
        (self.repo_root / "large.txt").write_text("x" * 210_000, encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_list_repo_files_excludes_ignored_and_large_paths(self):
        result = list_repo_files_text(str(self.repo_root))

        self.assertIn("README.md", result)
        self.assertIn("src/main.py", result)
        self.assertNotIn(".git/config", result)
        self.assertNotIn("node_modules/ignored.js", result)
        self.assertNotIn("large.txt", result)

    def test_search_repo_finds_text_in_readable_files(self):
        result = search_repo_text(str(self.repo_root), "main model pipeline")

        self.assertIn("README.md:1:", result)
        self.assertNotIn("node_modules/ignored.js", result)

    def test_search_repo_no_matches(self):
        result = search_repo_text(str(self.repo_root), "nonexistent_term_xyz")

        self.assertIn("No matches found", result)

    def test_read_repo_file_returns_contents(self):
        result = read_repo_file_text(str(self.repo_root), "src/main.py")

        self.assertIn("Contents of ", result)
        self.assertIn("/repo/src/main.py:", result)
        self.assertIn("def build_pipeline()", result)

    def test_read_repo_file_rejects_traversal(self):
        outside_file = Path(self.tmpdir.name) / "outside.txt"
        outside_file.write_text("nope\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "outside the repo/ directory"):
            read_repo_file_text(str(self.repo_root), "../outside.txt")

    def test_read_repo_file_rejects_nonexistent(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            read_repo_file_text(str(self.repo_root), "no_such_file.py")

    def test_tool_schemas_do_not_expose_repo_path_or_paper_path(self):
        self.assertEqual(repo_tools.list_repo_files.params_json_schema["properties"], {})
        self.assertEqual(repo_tools.list_repo_files.params_json_schema["required"], [])
        self.assertEqual(
            set(repo_tools.search_repo.params_json_schema["properties"].keys()),
            {"query"},
        )
        self.assertNotIn("repo_path", repo_tools.search_repo.params_json_schema["properties"])
        self.assertEqual(
            set(repo_tools.read_repo_file.params_json_schema["properties"].keys()),
            {"relative_path"},
        )
        self.assertNotIn("repo_path", repo_tools.read_repo_file.params_json_schema["properties"])
        self.assertEqual(paper_tools.read_paper.params_json_schema["properties"], {})
        self.assertEqual(paper_tools.read_paper.params_json_schema["required"], [])


class PaperToolTests(unittest.TestCase):
    def test_read_paper_text_extracts_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "test.pdf"
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.cell(text="Antimicrobial peptides from extreme environments")
            pdf.output(str(pdf_path))

            result = read_paper_text(str(pdf_path))

            self.assertIn("Antimicrobial peptides from extreme environments", result)

    def test_read_paper_text_rejects_empty_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / "empty.pdf"
            pdf = FPDF()
            pdf.add_page()
            pdf.output(str(pdf_path))

            with self.assertRaisesRegex(ValueError, "no extractable text"):
                read_paper_text(str(pdf_path))
