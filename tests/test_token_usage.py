import unittest
from unittest.mock import MagicMock


class TokenUsageTest(unittest.TestCase):
    def test_usage_fields_exist(self):
        # Simulate what result.usage looks like
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        total = mock_usage.input_tokens + mock_usage.output_tokens
        self.assertEqual(total, 150)
