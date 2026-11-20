#!/usr/bin/env python3
"""Test override config.json untuk preferensi keamanan."""
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import dynamic_config  # noqa: E402


class DynamicConfigTest(unittest.TestCase):
    def _load(self, data):
        with mock.patch.object(dynamic_config, "load_config_from_json", return_value=data):
            return dynamic_config.get_dynamic_config()

    def test_approval_mode_override(self):
        cfg = self._load({"approval_mode": "plan"})
        self.assertEqual(cfg["APPROVAL_MODE"], "plan")

    def test_invalid_approval_mode_ignored(self):
        cfg = self._load({"approval_mode": "ngawur"})
        self.assertIn(cfg["APPROVAL_MODE"], ("ask", "auto", "plan"))
        self.assertNotEqual(cfg["APPROVAL_MODE"], "ngawur")

    def test_auto_update_override(self):
        self.assertTrue(self._load({"auto_update": True})["AUTO_UPDATE"])
        self.assertFalse(self._load({"auto_update": False})["AUTO_UPDATE"])

    def test_checkpoint_override(self):
        self.assertFalse(self._load({"checkpoint_enabled": False})["CHECKPOINT_ENABLED"])
        self.assertTrue(self._load({"checkpoint_enabled": True})["CHECKPOINT_ENABLED"])

    def test_defaults_survive_without_json(self):
        cfg = self._load(None)
        self.assertIn("APPROVAL_MODE", cfg)
        self.assertIn("CHECKPOINT_ENABLED", cfg)
        self.assertIn("AUTO_UPDATE", cfg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
