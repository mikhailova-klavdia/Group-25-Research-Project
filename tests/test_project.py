import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from research_agents.project import (
    ResearchContext,
    _ensure_venv,
    _venv_bin_name,
    resolve_project,
)


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
            self.assertEqual(context.venv_path, (root / ".venv").resolve())
            self.assertEqual(context.artifacts_path, (root / ".artifacts").resolve())
            self.assertTrue(context.artifacts_path.is_dir())
            self.assertTrue((context.venv_path / "bin" / "python").exists())

    @patch("research_agents.project.subprocess.run", side_effect=_fake_uv_venv)
    def test_resolve_project_reuses_paper_venv_across_fresh_runs(self, mock_run):
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
            self.assertEqual(ctx1.venv_path, ctx2.venv_path)
            self.assertTrue((ctx1.venv_path / "bin" / "python").exists())
            mock_run.assert_called_once()

    @patch("research_agents.project.subprocess.run", side_effect=_fake_uv_venv)
    def test_resolve_project_uses_python_version_from_config(self, mock_run):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "sample-project"
            root.mkdir()
            (root / "paper.pdf").write_text("placeholder", encoding="utf-8")
            (root / "repo").mkdir()
            (root / ".research_config.toml").write_text(
                '[venv]\npython_version = "3.9"\n',
                encoding="utf-8",
            )

            context = resolve_project(str(root))

            self.assertEqual(context.venv_path, (root / ".venv").resolve())
            self.assertEqual(
                mock_run.call_args.args[0],
                ["uv", "venv", "--seed", "--python", "3.9", str(root.resolve() / ".venv")],
            )

    def test_ensure_venv_installs_seed_packages_once(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"

            def fake_run(command, **kwargs):
                if command[:3] == ["uv", "venv", "--seed"]:
                    _fake_uv_venv(command, **kwargs)
                return None

            with patch("research_agents.project.subprocess.run", side_effect=fake_run) as mock_run:
                _ensure_venv(
                    venv,
                    config={"venv": {"seed_packages": ["torch==1.13.1"]}},
                )

            self.assertEqual(mock_run.call_count, 2)
            self.assertEqual(
                mock_run.call_args_list[0].args[0], ["uv", "venv", "--seed", str(venv)]
            )
            self.assertEqual(
                mock_run.call_args_list[1],
                call(
                    [
                        "uv",
                        "pip",
                        "install",
                        "--python",
                        str(venv / "bin" / "python"),
                        "torch==1.13.1",
                    ],
                    check=True,
                    capture_output=True,
                    timeout=1800,
                ),
            )

    def test_venv_bin_name_uses_scripts_on_windows(self):
        with patch("research_agents.project.sys.platform", "win32"):
            self.assertEqual(_venv_bin_name(), "Scripts")

    def test_venv_bin_name_uses_bin_on_non_windows(self):
        with patch("research_agents.project.sys.platform", "linux"):
            self.assertEqual(_venv_bin_name(), "bin")

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
