#!/usr/bin/env python3
"""Test integrasi gerbang approval pada execute_tool()."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402


class ApprovalGateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_appr_")
        self.base = self._tmp.name
        self._orig = (main.config.BASE_DIR, main.config.APPROVAL_MODE, main._request_approval)
        self._real_request_approval = main._request_approval
        main.config.BASE_DIR = self.base
        self._answers = []
        main._request_approval = lambda *a, **k: (self._answers.pop(0), "")

    def tearDown(self):
        main.config.BASE_DIR, main.config.APPROVAL_MODE, main._request_approval = self._orig
        self._tmp.cleanup()

    def _write(self, name="a.txt", content="isi"):
        path = os.path.join(self.base, name)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_plan_blocks_write_and_delete(self):
        main.config.APPROVAL_MODE = "plan"
        result = main.execute_tool("write_file", {"filename": "a.txt", "content": "x"})
        self.assertTrue(result.startswith("Error"), result)
        self.assertFalse(os.path.exists(os.path.join(self.base, "a.txt")))

        path = self._write()
        result = main.execute_tool("delete_file", {"filename": "a.txt"})
        self.assertTrue(result.startswith("Error"), result)
        self.assertTrue(os.path.exists(path))

    def test_plan_allows_read(self):
        main.config.APPROVAL_MODE = "plan"
        self._write("a.txt", "halo")
        result = main.execute_tool("read_file", {"filename": "a.txt"})
        self.assertEqual(result, "halo")

    def test_ask_delete_denied(self):
        main.config.APPROVAL_MODE = "ask"
        path = self._write()
        self._answers = [False]
        result = main.execute_tool("delete_file", {"filename": "a.txt"})
        self.assertTrue(result.startswith("Error"), result)
        self.assertTrue(os.path.exists(path))

    def test_ask_delete_approved(self):
        main.config.APPROVAL_MODE = "ask"
        path = self._write()
        self._answers = [True]
        result = main.execute_tool("delete_file", {"filename": "a.txt"})
        self.assertIn("berhasil", result)
        self.assertFalse(os.path.exists(path))

    def test_ask_write_does_not_prompt(self):
        main.config.APPROVAL_MODE = "ask"

        def _boom(*a, **k):
            raise AssertionError("write_file tidak boleh minta approval di mode ask")

        main._request_approval = _boom
        result = main.execute_tool("write_file", {"filename": "b.txt", "content": "x"})
        self.assertIn("berhasil", result)

    def test_ask_dangerous_command_denied(self):
        main.config.APPROVAL_MODE = "ask"
        os.makedirs(os.path.join(self.base, "build"), exist_ok=True)
        self._answers = [False]
        result = main.execute_tool("exec_command", {"command": "rm -rf build"})
        self.assertTrue(result.startswith("Error"), result)
        self.assertTrue(os.path.isdir(os.path.join(self.base, "build")))

    def test_auto_runs_without_prompt(self):
        main.config.APPROVAL_MODE = "auto"

        def _boom(*a, **k):
            raise AssertionError("mode auto tidak boleh minta approval")

        main._request_approval = _boom
        result = main.execute_tool("exec_command", {"command": "echo halo"})
        self.assertIn("halo", result)

    def test_non_tty_approval_denied(self):
        # pytest/CI tidak punya TTY: aksi berisiko harus ditolak, bukan menggantung.
        import io
        from unittest import mock

        with mock.patch.object(main.sys, "stdin", io.StringIO("")):
            approved, note = self._real_request_approval("rm -rf build", "berbahaya")
        self.assertFalse(approved)
        self.assertIn("TTY", note)


if __name__ == "__main__":
    unittest.main(verbosity=2)
