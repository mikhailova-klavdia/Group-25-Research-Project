"""Unit tests for the Environment Agent pure helpers.

Corrected for the current main-branch team set (7 teams + worker-env-critic = 8).
"""

import unittest

from research_agents.agents.environment_agent import (
    DEPENDENCY_FILE_NAMES,
    EnvironmentReport,
    classify_dependency_file,
    detect_platform_requirements,
    format_environment_report_for_worker,
)


class ClassifyDependencyFileTests(unittest.TestCase):
    def test_requirements_txt(self):
        self.assertEqual(classify_dependency_file("requirements.txt"), "pip-requirements")
    def test_requirements_dev_txt(self):
        self.assertEqual(classify_dependency_file("requirements-dev.txt"), "pip-requirements")
    def test_requirements_underscore_dev(self):
        self.assertEqual(classify_dependency_file("requirements_dev.txt"), "pip-requirements")
    def test_pyproject_toml(self):
        self.assertEqual(classify_dependency_file("pyproject.toml"), "pyproject-toml")
    def test_setup_py(self):
        self.assertEqual(classify_dependency_file("setup.py"), "setup-py")
    def test_setup_cfg(self):
        self.assertEqual(classify_dependency_file("setup.cfg"), "setup-py")
    def test_environment_yml(self):
        self.assertEqual(classify_dependency_file("environment.yml"), "conda-environment")
    def test_environment_yaml(self):
        self.assertEqual(classify_dependency_file("environment.yaml"), "conda-environment")
    def test_pipfile(self):
        self.assertEqual(classify_dependency_file("Pipfile"), "pipenv")
    def test_unknown_file(self):
        self.assertEqual(classify_dependency_file("Makefile"), "unknown")
    def test_path_with_subdirectory_strips_prefix(self):
        self.assertEqual(classify_dependency_file("envs/base/requirements.txt"), "pip-requirements")
    def test_case_insensitive(self):
        self.assertEqual(classify_dependency_file("REQUIREMENTS.TXT"), "pip-requirements")


class DetectPlatformRequirementsTests(unittest.TestCase):
    def test_detects_cuda(self):
        self.assertIn("CUDA GPU required", detect_platform_requirements("Requires a CUDA GPU."))
    def test_detects_gpu(self):
        self.assertIn("GPU required", detect_platform_requirements("A GPU is needed."))
    def test_detects_linux(self):
        self.assertIn("Linux OS required", detect_platform_requirements("Linux only."))
    def test_detects_docker(self):
        self.assertIn("Docker required", detect_platform_requirements("Use Docker."))
    def test_detects_r_language(self):
        self.assertIn("R language required", detect_platform_requirements("R language >= 4.1"))
    def test_detects_pysam(self):
        self.assertIn("pysam requires htslib (Linux/macOS build)", detect_platform_requirements("pysam for BAM"))
    def test_detects_bioconda(self):
        self.assertIn("bioconda channel required (conda install)", detect_platform_requirements("bioconda install"))
    def test_no_false_positive_clean_readme(self):
        self.assertEqual(detect_platform_requirements("Install with pip."), [])
    def test_deduplicates_repeated_keywords(self):
        reqs = detect_platform_requirements("CUDA support. Requires CUDA 11+.")
        self.assertEqual(reqs.count("CUDA GPU required"), 1)
    def test_empty_text(self):
        self.assertEqual(detect_platform_requirements(""), [])


class DependencyFileNamesTests(unittest.TestCase):
    def test_contains_requirements_txt(self):
        self.assertIn("requirements.txt", DEPENDENCY_FILE_NAMES)
    def test_contains_pyproject_toml(self):
        self.assertIn("pyproject.toml", DEPENDENCY_FILE_NAMES)
    def test_contains_environment_yml(self):
        self.assertIn("environment.yml", DEPENDENCY_FILE_NAMES)
    def test_contains_setup_py(self):
        self.assertIn("setup.py", DEPENDENCY_FILE_NAMES)
    def test_does_not_contain_readme(self):
        self.assertNotIn("README.md", DEPENDENCY_FILE_NAMES)
    def test_is_frozenset(self):
        self.assertIsInstance(DEPENDENCY_FILE_NAMES, frozenset)


class EnvironmentReportDefaultsTests(unittest.TestCase):
    def test_minimal_blocked_report(self):
        r = EnvironmentReport(status="blocked", blockers=["pysam cannot build on Windows"])
        self.assertEqual(r.status, "blocked")
        self.assertEqual(len(r.blockers), 1)
        self.assertEqual(r.detected_dependency_files, [])
        self.assertIsNone(r.python_version)
        self.assertEqual(r.notes, "")

    def test_full_ready_report(self):
        r = EnvironmentReport(
            status="ready",
            detected_dependency_files=["requirements.txt"],
            installed_packages=["numpy==1.26.4", "torch==1.13.1"],
            validation_checks=["import torch — OK"],
            python_version="3.9.17",
        )
        self.assertEqual(r.status, "ready")
        self.assertEqual(r.python_version, "3.9.17")

    def test_partial_with_gpu_requirement(self):
        r = EnvironmentReport(status="partial", platform_requirements=["CUDA GPU required"])
        self.assertIn("CUDA GPU required", r.platform_requirements)


class FormatEnvironmentReportTests(unittest.TestCase):
    def _make(self, **kw):
        return EnvironmentReport(**{"status": "ready", **kw})

    def test_status_always_present(self):
        self.assertIn("ready", format_environment_report_for_worker(self._make()))

    def test_blocked_shows_blockers(self):
        text = format_environment_report_for_worker(
            self._make(status="blocked", blockers=["pysam cannot build"])
        )
        self.assertIn("BLOCKERS", text)
        self.assertIn("pysam", text)

    def test_missing_packages_flagged(self):
        text = format_environment_report_for_worker(self._make(missing_packages=["esm"]))
        self.assertIn("MISSING", text)

    def test_conflicts_appear(self):
        text = format_environment_report_for_worker(
            self._make(conflicts=["numpy 2.0 conflicts with torch 1.13"])
        )
        self.assertIn("CONFLICTS", text)

    def test_empty_optional_fields_omitted(self):
        text = format_environment_report_for_worker(
            self._make(missing_packages=[], conflicts=[])
        )
        self.assertNotIn("MISSING", text)
        self.assertNotIn("CONFLICTS", text)

    def test_long_installed_list_truncated(self):
        text = format_environment_report_for_worker(
            self._make(installed_packages=[f"pkg{i}==1.0" for i in range(25)])
        )
        self.assertIn("…", text)

    def test_python_version_appears(self):
        self.assertIn("3.9.17", format_environment_report_for_worker(
            self._make(python_version="3.9.17")
        ))

    def test_unknown_python_version(self):
        self.assertIn("unknown", format_environment_report_for_worker(
            self._make(python_version=None)
        ))


class EnvironmentAgentFactoryTests(unittest.TestCase):
    def test_correct_tools(self):
        from research_agents.agents.environment_agent import create_environment_agent
        names = {t.name for t in create_environment_agent().tools}
        for expected in ("list_repo_files", "find_repo_files", "read_repo_file",
                         "search_repo", "venv_status", "execute_command", "write_file"):
            self.assertIn(expected, names)

    def test_no_paper_or_staging_tools(self):
        from research_agents.agents.environment_agent import create_environment_agent
        names = {t.name for t in create_environment_agent().tools}
        for forbidden in ("read_paper", "stage_repo_path", "stage_paper_artifact"):
            self.assertNotIn(forbidden, names)

    def test_output_type(self):
        from research_agents.agents.environment_agent import create_environment_agent, EnvironmentReport
        self.assertIs(create_environment_agent().output_type, EnvironmentReport)

    def test_five_phases_in_instructions(self):
        from research_agents.agents.environment_agent import ENVIRONMENT_AGENT_INSTRUCTIONS
        for phase in ("DISCOVER", "INSPECT", "INSTALL", "VERIFY", "REPORT"):
            self.assertIn(phase, ENVIRONMENT_AGENT_INSTRUCTIONS)


class TeamRegistryTests(unittest.TestCase):
    # Current main-branch teams + the new worker-env-critic.
    # Update this set when new teams are added.
    EXPECTED = {
        "solo",
        "worker-critic",
        "worker-critic-plus",
        "worker-verifier-critic",
        "worker-critic-plus-plus",
        "testing-worker-critic",
        "human-in-the-loop",
        "worker-critic-plus-plus-hitl",
        "worker-critic-assisted",
        "worker-critic-plus-plus-assisted",
        "worker-critic-readme",
        "worker-critic-plus-plus-readme",
        "solo-readme",
        "human-in-the-loop-readme",
        "worker-env-critic",
    }

    def test_worker_env_critic_registered(self):
        from research_agents.teams import TEAMS
        self.assertIn("worker-env-critic", TEAMS)

    def test_apply_setup_false(self):
        from research_agents.teams import TEAMS
        self.assertFalse(TEAMS["worker-env-critic"].apply_setup)

    def test_run_fn_matches_module(self):
        from research_agents.teams import TEAMS
        from research_agents.teams.worker_env_critic import run_worker_env_critic
        self.assertIs(TEAMS["worker-env-critic"].run, run_worker_env_critic)

    def test_full_team_set(self):
        from research_agents.teams import TEAMS
        self.assertEqual(set(TEAMS.keys()), self.EXPECTED)

    def test_no_existing_team_removed(self):
        from research_agents.teams import TEAMS
        for name in self.EXPECTED - {"worker-env-critic"}:
            self.assertIn(name, TEAMS, f"'{name}' was unexpectedly removed")


if __name__ == "__main__":
    unittest.main()
