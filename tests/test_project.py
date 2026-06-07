import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from research_agents.project import (
    ResearchContext,
    _ensure_venv,
    _run_setup_scripts,
    _venv_bin_name,
    delete_venv,
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

    def test_ensure_venv_runs_setup_download_scripts(self):
        """`_ensure_venv` invokes `bash <script>` after the seed install."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            script_rel = "weights/download.sh"
            script_abs = repo / script_rel
            script_abs.parent.mkdir(parents=True)
            script_abs.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            script_abs.chmod(0o755)

            def fake_run(command, **kwargs):
                if command[:3] == ["uv", "venv", "--seed"]:
                    _fake_uv_venv(command, **kwargs)
                return None

            with patch("research_agents.project.subprocess.run", side_effect=fake_run) as mock_run:
                _ensure_venv(
                    venv,
                    config={"setup": {"download_scripts": [script_rel]}},
                    repo_path=repo,
                )

            commands = [c.args[0] for c in mock_run.call_args_list]
            self.assertEqual(commands[0][:3], ["uv", "venv", "--seed"])
            self.assertEqual(commands[1], ["bash", str(script_abs.resolve())])
            # The bash invocation must run from cwd=repo so relative paths
            # in the script (download targets, etc.) land in the right place.
            self.assertEqual(mock_run.call_args_list[1].kwargs.get("cwd"), str(repo))
            # And the venv's bin/ should be first on PATH so the script
            # picks up the right pip / python.
            env = mock_run.call_args_list[1].kwargs.get("env", {})
            self.assertTrue(
                env.get("PATH", "").startswith(str(venv / "bin")),
                f"expected venv bin first on PATH, got {env.get('PATH')!r}",
            )
            self.assertEqual(env.get("VIRTUAL_ENV"), str(venv))

    def test_ensure_venv_runs_setup_warmup_imports(self):
        """`_ensure_venv` runs `<venv>/bin/python -c <oneliner>` for each warmup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"

            def fake_run(command, **kwargs):
                if command[:3] == ["uv", "venv", "--seed"]:
                    _fake_uv_venv(command, **kwargs)
                return None

            with patch("research_agents.project.subprocess.run", side_effect=fake_run) as mock_run:
                _ensure_venv(
                    venv,
                    config={
                        "setup": {
                            "warmup_imports": [
                                "from esm.pretrained import esm2_t33_650M_UR50D; "
                                "esm2_t33_650M_UR50D()",
                            ]
                        }
                    },
                )

            commands = [c.args[0] for c in mock_run.call_args_list]
            self.assertEqual(commands[0][:3], ["uv", "venv", "--seed"])
            self.assertEqual(commands[1][0], str(venv / "bin" / "python"))
            self.assertEqual(commands[1][1], "-c")
            self.assertIn("esm2_t33_650M_UR50D", commands[1][2])

    def test_run_setup_scripts_warns_but_does_not_raise_on_failure(self):
        """A failing download script must not propagate; it warns to stderr."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            script_abs = repo / "fail.sh"
            script_abs.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            script_abs.chmod(0o755)

            import subprocess as _sp

            def failing_run(command, **kwargs):
                raise _sp.CalledProcessError(returncode=1, cmd=command)

            with patch("research_agents.project.subprocess.run", side_effect=failing_run):
                # Should NOT raise — failures are non-fatal by design.
                _run_setup_scripts(
                    venv,
                    repo,
                    {"setup": {"download_scripts": ["fail.sh"]}},
                )

    def test_ensure_venv_skips_setup_scripts_when_apply_setup_is_false(self):
        """`apply_setup=False` short-circuits _run_setup_scripts entirely.

        This is the gate the ``solo`` and ``worker-critic`` teams rely on to
        reproduce the colleague's baseline behavior even when a paper's
        ``.research_config.toml`` has a ``[setup]`` block configured.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            script_rel = "weights/download.sh"
            script_abs = repo / script_rel
            script_abs.parent.mkdir(parents=True)
            script_abs.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            script_abs.chmod(0o755)

            def fake_run(command, **kwargs):
                if command[:3] == ["uv", "venv", "--seed"]:
                    _fake_uv_venv(command, **kwargs)
                return None

            with patch("research_agents.project.subprocess.run", side_effect=fake_run) as mock_run:
                _ensure_venv(
                    venv,
                    config={"setup": {"download_scripts": [script_rel]}},
                    repo_path=repo,
                    apply_setup=False,
                )

            commands = [c.args[0] for c in mock_run.call_args_list]
            # Only the venv-creation call; no bash <script>.
            self.assertEqual(len(commands), 1)
            self.assertEqual(commands[0][:3], ["uv", "venv", "--seed"])

    def test_run_setup_scripts_skips_missing_script_with_warning(self):
        """A download_scripts entry that doesn't exist on disk is skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
            repo = Path(tmpdir) / "repo"
            repo.mkdir()

            with patch("research_agents.project.subprocess.run") as mock_run:
                _run_setup_scripts(
                    venv,
                    repo,
                    {"setup": {"download_scripts": ["does_not_exist.sh"]}},
                )

            # No subprocess at all — we filtered before invoking bash.
            mock_run.assert_not_called()

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


class DeleteVenvTests(unittest.TestCase):
    """delete_venv must wipe the venv but never touch weights stored elsewhere."""

    def test_delete_venv_removes_existing_venv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")

            delete_venv(venv)

            self.assertFalse(venv.exists())

    def test_delete_venv_missing_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            venv = Path(tmpdir) / ".venv"
            # Never created — calling delete on a missing path must not raise,
            # so the batch loop can invoke it unconditionally before each run.
            delete_venv(venv)
            self.assertFalse(venv.exists())

    def test_delete_venv_preserves_weights_outside_the_venv(self):
        """Weights live outside the venv, so wiping the venv must leave them intact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            venv = root / ".venv"
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")

            # Stand-ins for weights that live OUTSIDE the venv: a repo
            # checkpoint and a framework-cache checkpoint.
            repo_ckpt = root / "repo" / "weights" / "affinity_models.pkl"
            repo_ckpt.parent.mkdir(parents=True)
            repo_ckpt.write_text("WEIGHT", encoding="utf-8")
            cache_ckpt = root / "torch_hub" / "esm2.pt"
            cache_ckpt.parent.mkdir(parents=True)
            cache_ckpt.write_text("ESM", encoding="utf-8")

            delete_venv(venv)

            self.assertFalse(venv.exists())
            self.assertTrue(repo_ckpt.exists())
            self.assertEqual(repo_ckpt.read_text(encoding="utf-8"), "WEIGHT")
            self.assertTrue(cache_ckpt.exists())
            self.assertEqual(cache_ckpt.read_text(encoding="utf-8"), "ESM")
