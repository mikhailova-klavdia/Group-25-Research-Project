import tempfile
import unittest
from pathlib import Path

from research_agents.project import ResearchContext, resolve_project


class ResolveProjectTests(unittest.TestCase):
    def test_resolve_project_returns_expected_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "sample-project"
            root.mkdir()
            (root / "paper.pdf").write_text("placeholder", encoding="utf-8")
            (root / "repo").mkdir()

            context = resolve_project(str(root))

            self.assertIsInstance(context, ResearchContext)
            self.assertEqual(context.project_dir, root.resolve())
            self.assertEqual(context.paper_path, (root / "paper.pdf").resolve())
            self.assertEqual(context.repo_path, (root / "repo").resolve())

    def test_resolve_project_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing"

            with self.assertRaisesRegex(ValueError, "does not exist"):
                resolve_project(str(missing))

    def test_resolve_project_rejects_missing_paper(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "sample-project"
            root.mkdir()
            (root / "repo").mkdir()

            with self.assertRaisesRegex(ValueError, "Missing paper.pdf"):
                resolve_project(str(root))

    def test_resolve_project_rejects_missing_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "sample-project"
            root.mkdir()
            (root / "paper.pdf").write_text("placeholder", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Missing repo/"):
                resolve_project(str(root))
