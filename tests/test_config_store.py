#!/usr/bin/env python3
"""Test penyimpanan config.json: atomik, valid, dan permission 0600."""
import json
import os
import stat
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402


class ConfigWriteTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_cfgtest_")
        self._orig_script = main.SCRIPT_DIR
        main.SCRIPT_DIR = self._tmp.name
        self.path = os.path.join(self._tmp.name, "config.json")

    def tearDown(self):
        main.SCRIPT_DIR = self._orig_script
        self._tmp.cleanup()

    def test_write_creates_valid_json(self):
        main._write_config_data({"model": "x", "api_key": "secret"})
        with open(self.path) as f:
            data = json.load(f)
        self.assertEqual(data["model"], "x")
        self.assertIn("updated_at", data)

    def test_mode_is_owner_only(self):
        main._write_config_data({"api_key": "secret"})
        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(mode, 0o600, oct(mode))

    def test_overwrite_keeps_valid_json(self):
        main._write_config_data({"model": "a"})
        main._write_config_data({"model": "b"})
        with open(self.path) as f:
            self.assertEqual(json.load(f)["model"], "b")
        backups = os.path.join(self._tmp.name, "backups")
        self.assertTrue(os.path.isdir(backups))

    def test_read_roundtrip(self):
        main._write_config_data({"model": "m", "api_key": "k"})
        data = main._read_config_data()
        self.assertEqual(data["model"], "m")
        self.assertEqual(data["api_key"], "k")


if __name__ == "__main__":
    unittest.main(verbosity=2)
