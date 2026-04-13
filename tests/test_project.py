import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_agents.project import ResearchContext, resolve_project


def _fake_uv_venv(command, **kwargs):
    venv_path = Path(command[-1])
    python_path = venv_path / "bin" / "python"
    python_path.parent.mkdir(parents=True, exist_ok=True)
    python_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_path.chmod(0o755)
    return None


class ResolveProjectTests(unittest.TestCase):
    @patch("research_agents.project.subprocess.run", side_effect=_fake_uv_venv)
    def test_resolve_project_returns_expected_paths(self, _mock_run):
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
            self.assertEqual(context.run_dir.parent, (root / "runs").resolve())
            self.assertEqual(context.workspace_path, (context.run_dir / "workspace").resolve())
            self.assertTrue(context.workspace_path.is_dir())
            self.assertEqual(context.venv_path, (context.run_dir / ".venv").resolve())
            self.assertTrue((context.venv_path / "bin" / "python").exists())

    @patch("research_agents.project.subprocess.run", side_effect=_fake_uv_venv)
    def test_resolve_project_creates_fresh_run_each_time(self, _mock_run):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "sample-project"
            root.mkdir()
            (root / "paper.pdf").write_text("placeholder", encoding="utf-8")
            (root / "repo").mkdir()

            ctx1 = resolve_project(str(root))
            ctx2 = resolve_project(str(root))

            self.assertEqual(ctx1.project_dir, ctx2.project_dir)
            self.assertEqual(ctx1.paper_path, ctx2.paper_path)
            self.assertEqual(ctx1.repo_path, ctx2.repo_path)
            self.assertNotEqual(ctx1.run_id, ctx2.run_id)
            self.assertNotEqual(ctx1.run_dir, ctx2.run_dir)
            self.assertNotEqual(ctx1.workspace_path, ctx2.workspace_path)
            self.assertNotEqual(ctx1.venv_path, ctx2.venv_path)
            self.assertTrue((ctx1.venv_path / "bin" / "python").exists())
            self.assertTrue((ctx2.venv_path / "bin" / "python").exists())

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
