import json
import tempfile
import unittest
from pathlib import Path

from research_agents.token_utils import (
    append_cost_log,
    calculate_cost,
    estimate_tokens,
    load_cost_log,
)


class CostCalculationTests(unittest.TestCase):
    def test_calculate_cost_default_model(self):
        cost = calculate_cost(input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(cost, 2.00, places=2)  # 0.40 + 1.60

    def test_calculate_cost_zero_tokens(self):
        self.assertEqual(calculate_cost(0, 0), 0.0)


class CostLogTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_log_is_created_on_first_run(self):
        append_cost_log(self.project_dir, "run-001", "What is X?", "gpt-4.1-mini-2025-04-14", 100, 500, 50)
        self.assertTrue((self.project_dir / "costs.json").exists())

    def test_entries_accumulate(self):
        append_cost_log(self.project_dir, "run-001", "Q1", "gpt-4.1-mini-2025-04-14", 100, 500, 50)
        append_cost_log(self.project_dir, "run-002", "Q2", "gpt-4.1-mini-2025-04-14", 100, 600, 60)
        entries = load_cost_log(self.project_dir)
        self.assertEqual(len(entries), 2)

    def test_entry_contains_expected_fields(self):
        append_cost_log(self.project_dir, "run-001", "Q1", "gpt-4.1-mini-2025-04-14", 100, 500, 50)
        entry = load_cost_log(self.project_dir)[0]
        self.assertIn("timestamp", entry)
        self.assertIn("cost_usd", entry)
        self.assertIn("total_tokens", entry)
        self.assertEqual(entry["total_tokens"], 550)

    def test_corrupted_log_returns_empty_list(self):
        (self.project_dir / "costs.json").write_text("not valid json", encoding="utf-8")
        entries = load_cost_log(self.project_dir)
        self.assertEqual(entries, [])


class TiktokenEstimateTests(unittest.TestCase):
    def test_returns_positive_integer(self):
        count = estimate_tokens("You are a helpful assistant.", "What is the main contribution?")
        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_longer_text_gives_higher_count(self):
        short = estimate_tokens("short prompt", "short question")
        long  = estimate_tokens("short prompt", "question " * 100)
        self.assertGreater(long, short)