import tempfile
import unittest
from pathlib import Path

from research_agents.tools import exec_tools
from research_agents.tools.exec_tools import (
    execute_command_text,
    list_workspace_files_text,
    stage_repo_path_text,
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
