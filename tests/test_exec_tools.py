import tempfile
import unittest
from pathlib import Path

from research_agents.tools import exec_tools
from research_agents.tools.exec_tools import (
    cache_workspace_artifact_text,
    execute_command_text,
    list_paper_artifacts_text,
    list_workspace_files_text,
    read_workspace_file_text,
    revert_repo_writes,
    snapshot_repo_tree,
    stage_paper_artifact_text,
    stage_repo_path_text,
    venv_status_text,
    write_file_text,
)


def _make_fake_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


class WriteFileTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name) / "workspace"
        self.workspace.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_creates_file_and_returns_confirmation(self):
        result = write_file_text(self.workspace, "hello.py", "print('hi')\n")

        self.assertIn("hello.py", result)
        self.assertTrue((self.workspace / "hello.py").exists())
        self.assertEqual((self.workspace / "hello.py").read_text(), "print('hi')\n")

    def test_creates_nested_directories(self):
        result = write_file_text(self.workspace, "scripts/sub/run.py", "pass\n")

        self.assertIn("scripts/sub/run.py", result)
        self.assertTrue((self.workspace / "scripts" / "sub" / "run.py").exists())

    def test_rejects_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "outside the workspace"):
            write_file_text(self.workspace, "../outside.txt", "nope")

    def test_rejects_absolute_path(self):
        with self.assertRaisesRegex(ValueError, "must be relative"):
            write_file_text(self.workspace, "/tmp/bad.txt", "nope")

    def test_rejects_oversized_content(self):
        big_content = "x" * 600_000
        with self.assertRaisesRegex(ValueError, "byte limit"):
            write_file_text(self.workspace, "big.txt", big_content)


class StageRepoPathTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.repo = root / "repo"
        self.workspace = root / "workspace"
        self.repo.mkdir()
        self.workspace.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_stages_file_using_same_relative_path_by_default(self):
        (self.repo / "data").mkdir()
        (self.repo / "data" / "input.txt").write_text("hello\n", encoding="utf-8")

        result = stage_repo_path_text(self.repo, self.workspace, "data/input.txt")

        self.assertIn("data/input.txt", result)
        self.assertEqual(
            (self.workspace / "data" / "input.txt").read_text(encoding="utf-8"),
            "hello\n",
        )

    def test_stages_directory_and_skips_ignored_dirs(self):
        (self.repo / "pkg").mkdir()
        (self.repo / "pkg" / "module.py").write_text("print('ok')\n", encoding="utf-8")
        (self.repo / "pkg" / ".git").mkdir()
        (self.repo / "pkg" / ".git" / "ignored").write_text("nope\n", encoding="utf-8")
        (self.repo / "pkg" / "dist").mkdir()
        (self.repo / "pkg" / "dist" / "artifact.whl").write_text("nope\n", encoding="utf-8")
        (self.repo / "pkg" / ".mypy_cache").mkdir()
        (self.repo / "pkg" / ".mypy_cache" / "cache").write_text("nope\n", encoding="utf-8")

        result = stage_repo_path_text(self.repo, self.workspace, "pkg", "staged/pkg")

        self.assertIn("staged/pkg", result)
        self.assertTrue((self.workspace / "staged" / "pkg" / "module.py").exists())
        self.assertFalse((self.workspace / "staged" / "pkg" / ".git").exists())
        self.assertFalse((self.workspace / "staged" / "pkg" / "dist").exists())
        self.assertFalse((self.workspace / "staged" / "pkg" / ".mypy_cache").exists())

    def test_rejects_source_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "outside the repo"):
            stage_repo_path_text(self.repo, self.workspace, "../outside.txt")

    def test_rejects_destination_path_traversal(self):
        (self.repo / "file.txt").write_text("hello\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "outside the workspace"):
            stage_repo_path_text(self.repo, self.workspace, "file.txt", "../outside.txt")


class ExecuteCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name) / "workspace"
        self.workspace.mkdir()
        self.venv = Path(self.tmpdir.name) / "venv"
        _make_fake_executable(
            self.venv / "bin" / "python",
            "#!/bin/sh\nprintf '%s\\n' \"$0\"\n",
        )
        _make_fake_executable(
            self.venv / "bin" / "pip",
            "#!/bin/sh\nprintf '%s\\n' \"$0\"\n",
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_captures_stdout(self):
        result = execute_command_text(self.workspace, "echo hello world")

        self.assertIn("Exit code: 0", result)
        self.assertIn("hello world", result)

    def test_captures_stderr_from_failing_command(self):
        result = execute_command_text(self.workspace, "python3 -c 'raise Exception(\"boom\")'")

        self.assertNotIn("Exit code: 0", result)
        self.assertIn("boom", result)

    def test_returns_nonzero_exit_code(self):
        result = execute_command_text(self.workspace, "exit 42")

        self.assertIn("Exit code: 42", result)

    def test_times_out_on_long_command(self):
        result = execute_command_text(self.workspace, "sleep 30", timeout=1)

        self.assertIn("timed out", result)

    def test_truncates_long_output(self):
        result = execute_command_text(
            self.workspace,
            "python3 -c \"print('x' * 80000)\"",
        )

        self.assertIn("truncated", result)

    def test_runs_in_correct_directory(self):
        (self.workspace / "marker.txt").write_text("here\n", encoding="utf-8")
        result = execute_command_text(self.workspace, "ls marker.txt")

        self.assertIn("Exit code: 0", result)
        self.assertIn("marker.txt", result)

    def test_venv_python_resolves_to_venv(self):
        result = execute_command_text(
            self.workspace,
            "python",
            venv_path=self.venv,
        )
        self.assertIn("Exit code: 0", result)
        self.assertIn(str(self.venv / "bin" / "python"), result)

    def test_venv_pip_resolves_to_venv(self):
        result = execute_command_text(
            self.workspace,
            "pip",
            venv_path=self.venv,
        )
        self.assertIn("Exit code: 0", result)
        self.assertIn(str(self.venv / "bin" / "pip"), result)

    def test_passes_custom_env_vars(self):
        result = execute_command_text(
            self.workspace,
            "python3 -c \"import os; print(os.environ['RESEARCH_REPO_PATH'])\"",
            env_vars={"RESEARCH_REPO_PATH": "/tmp/example-repo"},
        )
        self.assertIn("Exit code: 0", result)
        self.assertIn("/tmp/example-repo", result)

    def test_timeout_is_clamped_to_one_hour(self):
        self.assertEqual(exec_tools.MAX_TIMEOUT, 3600)


class RepoWriteGuardTests(unittest.TestCase):
    """repo/ is input-only: execute_command must revert/flag any write into it."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.repo = root / "repo"
        self.workspace = root / "workspace"
        self.repo.mkdir()
        self.workspace.mkdir()
        # A pre-existing repo file the guard must protect.
        (self.repo / "source.py").write_text("original\n", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    # --- pure helpers ---

    def test_snapshot_records_files_and_skips_ignored_dirs(self):
        (self.repo / ".git").mkdir()
        (self.repo / ".git" / "HEAD").write_text("ref\n", encoding="utf-8")
        snap = snapshot_repo_tree(self.repo)
        self.assertIn("source.py", snap)
        self.assertNotIn(".git/HEAD", snap)

    def test_revert_deletes_created_file_and_warns(self):
        before = snapshot_repo_tree(self.repo)
        (self.repo / "junk.txt").write_text("nope\n", encoding="utf-8")
        warning = revert_repo_writes(self.repo, before)
        self.assertFalse((self.repo / "junk.txt").exists())
        self.assertIn("BLOCKED WRITE", warning)
        self.assertIn("junk.txt", warning)

    def test_revert_prunes_empty_created_dirs(self):
        before = snapshot_repo_tree(self.repo)
        (self.repo / "outdir").mkdir()
        (self.repo / "outdir" / "result.csv").write_text("a\n", encoding="utf-8")
        revert_repo_writes(self.repo, before)
        self.assertFalse((self.repo / "outdir").exists())

    def test_revert_keeps_preexisting_dir(self):
        (self.repo / "pkg").mkdir()
        (self.repo / "pkg" / "keep.py").write_text("keep\n", encoding="utf-8")
        before = snapshot_repo_tree(self.repo)
        (self.repo / "pkg" / "new.py").write_text("new\n", encoding="utf-8")
        revert_repo_writes(self.repo, before)
        self.assertFalse((self.repo / "pkg" / "new.py").exists())
        self.assertTrue((self.repo / "pkg" / "keep.py").exists())

    def test_revert_flags_modified_file_without_restoring(self):
        before = snapshot_repo_tree(self.repo)
        # Different length so the change is detected regardless of mtime granularity.
        (self.repo / "source.py").write_text("tampered-and-clearly-longer\n", encoding="utf-8")
        warning = revert_repo_writes(self.repo, before)
        self.assertIn("MODIFIED", warning)
        self.assertEqual((self.repo / "source.py").read_text(), "tampered-and-clearly-longer\n")

    def test_revert_returns_empty_when_untouched(self):
        before = snapshot_repo_tree(self.repo)
        self.assertEqual(revert_repo_writes(self.repo, before), "")

    # --- end-to-end through execute_command_text ---

    def test_execute_command_reverts_write_into_repo(self):
        target = self.repo / "created_by_cmd.txt"
        result = execute_command_text(
            self.workspace, f"echo polluted > '{target}'", repo_path=self.repo
        )
        self.assertFalse(target.exists())          # reverted
        self.assertIn("BLOCKED WRITE", result)
        self.assertIn("Exit code: 0", result)      # the command itself still ran

    def test_execute_command_allows_workspace_write(self):
        result = execute_command_text(
            self.workspace, "echo fine > out.txt", repo_path=self.repo
        )
        self.assertTrue((self.workspace / "out.txt").exists())
        self.assertNotIn("BLOCKED WRITE", result)

    def test_execute_command_without_repo_path_is_unguarded(self):
        # Backward-compatible: no repo_path means no snapshot and no warning.
        result = execute_command_text(self.workspace, "echo hi")
        self.assertNotIn("BLOCKED WRITE", result)


class ListWorkspaceFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name) / "workspace"
        self.workspace.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_lists_created_files(self):
        (self.workspace / "script.py").write_text("pass\n", encoding="utf-8")
        (self.workspace / "data").mkdir()
        (self.workspace / "data" / "input.csv").write_text("a,b\n", encoding="utf-8")

        result = list_workspace_files_text(self.workspace)

        self.assertIn("script.py", result)
        self.assertIn("data/input.csv", result)

    def test_empty_workspace(self):
        result = list_workspace_files_text(self.workspace)

        self.assertIn("empty", result.lower())


class ReadWorkspaceFileTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name) / "workspace"
        self.workspace.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_reads_file_contents(self):
        (self.workspace / "output.csv").write_text("a,b\n1,2\n", encoding="utf-8")

        result = read_workspace_file_text(self.workspace, "output.csv")

        self.assertIn("a,b", result)
        self.assertIn("1,2", result)

    def test_reads_nested_file(self):
        (self.workspace / "results").mkdir()
        (self.workspace / "results" / "log.txt").write_text("done\n", encoding="utf-8")

        result = read_workspace_file_text(self.workspace, "results/log.txt")

        self.assertIn("done", result)

    def test_truncates_large_file(self):
        big_content = "x" * 300_000
        (self.workspace / "big.txt").write_text(big_content, encoding="utf-8")

        result = read_workspace_file_text(self.workspace, "big.txt")

        self.assertIn("truncated", result)

    def test_rejects_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "outside the workspace"):
            read_workspace_file_text(self.workspace, "../outside.txt")

    def test_rejects_absolute_path(self):
        with self.assertRaisesRegex(ValueError, "must be relative"):
            read_workspace_file_text(self.workspace, "/tmp/bad.txt")

    def test_rejects_nonexistent_file(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            read_workspace_file_text(self.workspace, "nope.txt")


class PaperArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.workspace = root / "workspace"
        self.artifacts = root / ".artifacts"
        self.workspace.mkdir()
        self.artifacts.mkdir()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_lists_cached_artifacts(self):
        (self.artifacts / "weights").mkdir()
        (self.artifacts / "weights" / "model.pt").write_bytes(b"weights")

        result = list_paper_artifacts_text(self.artifacts)

        self.assertIn("weights/model.pt", result)

    def test_empty_artifact_cache(self):
        result = list_paper_artifacts_text(self.artifacts)

        self.assertIn("empty", result.lower())

    def test_cache_workspace_artifact_then_stage_it(self):
        (self.workspace / "outputs").mkdir()
        (self.workspace / "outputs" / "seq.pkl").write_bytes(b"pickle")

        cached = cache_workspace_artifact_text(
            self.workspace,
            self.artifacts,
            "outputs/seq.pkl",
            "pplm/seq.pkl",
        )
        staged = stage_paper_artifact_text(
            self.artifacts,
            self.workspace,
            "pplm/seq.pkl",
            "reused/seq.pkl",
        )

        self.assertIn(".artifacts/pplm/seq.pkl", cached)
        self.assertIn("workspace/reused/seq.pkl", staged)
        self.assertEqual((self.workspace / "reused" / "seq.pkl").read_bytes(), b"pickle")

    def test_cache_workspace_artifact_rejects_traversal(self):
        with self.assertRaisesRegex(ValueError, "outside the workspace"):
            cache_workspace_artifact_text(self.workspace, self.artifacts, "../bad")

    def test_stage_paper_artifact_rejects_traversal(self):
        with self.assertRaisesRegex(ValueError, "outside the .artifacts"):
            stage_paper_artifact_text(self.artifacts, self.workspace, "../bad")


class VenvStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.venv = Path(self.tmpdir.name) / "venv"
        _make_fake_executable(
            self.venv / "bin" / "python",
            "#!/bin/sh\n"
            'if [ "$1" = "--version" ]; then echo \'Python 3.12.0\'; exit 0; fi\n'
            'if [ "$1" = "-m" ]; then echo \'torch==1.13.1\'; exit 0; fi\n',
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_reports_python_and_installed_packages(self):
        result = venv_status_text(self.venv)

        self.assertIn("Python 3.12.0", result)
        self.assertIn("torch==1.13.1", result)

    def test_reports_missing_venv(self):
        result = venv_status_text(Path(self.tmpdir.name) / "missing")

        self.assertIn("does not exist", result)


class ToolSchemaTests(unittest.TestCase):
    def test_write_file_does_not_expose_workspace_path(self):
        props = exec_tools.write_file.params_json_schema["properties"]
        self.assertNotIn("workspace_path", props)
        self.assertIn("relative_path", props)
        self.assertIn("content", props)

    def test_stage_repo_path_does_not_expose_runtime_paths(self):
        props = exec_tools.stage_repo_path.params_json_schema["properties"]
        self.assertNotIn("repo_path", props)
        self.assertNotIn("workspace_path", props)
        self.assertIn("relative_path", props)
        self.assertIn("destination_path", props)

    def test_execute_command_does_not_expose_runtime_paths_or_working_dir(self):
        props = exec_tools.execute_command.params_json_schema["properties"]
        self.assertNotIn("workspace_path", props)
        self.assertNotIn("repo_path", props)
        self.assertNotIn("working_dir", props)
        self.assertIn("command", props)

    def test_list_workspace_files_has_no_params(self):
        self.assertEqual(exec_tools.list_workspace_files.params_json_schema["properties"], {})
        self.assertEqual(exec_tools.list_workspace_files.params_json_schema["required"], [])

    def test_read_workspace_file_does_not_expose_workspace_path(self):
        props = exec_tools.read_workspace_file.params_json_schema["properties"]
        self.assertNotIn("workspace_path", props)
        self.assertIn("relative_path", props)

    def test_list_paper_artifacts_has_no_params(self):
        self.assertEqual(exec_tools.list_paper_artifacts.params_json_schema["properties"], {})
        self.assertEqual(exec_tools.list_paper_artifacts.params_json_schema["required"], [])

    def test_stage_paper_artifact_does_not_expose_runtime_paths(self):
        props = exec_tools.stage_paper_artifact.params_json_schema["properties"]
        self.assertNotIn("artifacts_path", props)
        self.assertNotIn("workspace_path", props)
        self.assertIn("relative_path", props)
        self.assertIn("destination_path", props)

    def test_cache_workspace_artifact_does_not_expose_runtime_paths(self):
        props = exec_tools.cache_workspace_artifact.params_json_schema["properties"]
        self.assertNotIn("artifacts_path", props)
        self.assertNotIn("workspace_path", props)
        self.assertIn("relative_path", props)
        self.assertIn("destination_path", props)

    def test_venv_status_has_no_params(self):
        self.assertEqual(exec_tools.venv_status.params_json_schema["properties"], {})
        self.assertEqual(exec_tools.venv_status.params_json_schema["required"], [])
