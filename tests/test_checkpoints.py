#!/usr/bin/env python3
"""Test checkpoint & undo perubahan file."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ruka.checkpoints import (  # noqa: E402
    checkpoint_root,
    save_before_change,
    undo_last,
)

import main  # noqa: E402


def _write(base, rel, content):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class CheckpointTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_cp_")
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_restore_modified_file(self):
        path = _write(self.base, "a.txt", "lama")
        save_before_change(self.base, [path], "write_file")
        _write(self.base, "a.txt", "baru")
        msg = undo_last(self.base)
        self.assertIn("dipulihkan", msg)
        with open(path) as f:
            self.assertEqual(f.read(), "lama")

    def test_undo_created_file_is_removed(self):
        path = os.path.join(self.base, "baru.txt")
        save_before_change(self.base, [path], "write_file")
        _write(self.base, "baru.txt", "halo")
        msg = undo_last(self.base)
        self.assertIn("dihapus", msg)
        self.assertFalse(os.path.exists(path))

    def test_restore_deleted_file(self):
        path = _write(self.base, "hapus.txt", "penting")
        save_before_change(self.base, [path], "delete_file")
        os.unlink(path)
        undo_last(self.base)
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            self.assertEqual(f.read(), "penting")

    def test_restore_deleted_folder(self):
        _write(self.base, "dir/a.txt", "A")
        _write(self.base, "dir/sub/b.txt", "B")
        save_before_change(
            self.base, ["dir"], "delete_folder", recurse=["dir"]
        )
        import shutil

        shutil.rmtree(os.path.join(self.base, "dir"))
        undo_last(self.base)
        with open(os.path.join(self.base, "dir", "a.txt")) as f:
            self.assertEqual(f.read(), "A")
        with open(os.path.join(self.base, "dir", "sub", "b.txt")) as f:
            self.assertEqual(f.read(), "B")

    def test_nothing_to_undo(self):
        self.assertIn("Tidak ada checkpoint", undo_last(self.base))

    def test_prune_keeps_latest(self):
        for i in range(5):
            path = _write(self.base, "a.txt", f"versi{i}")
            save_before_change(self.base, [path], f"call{i}", keep=2)
        groups = os.listdir(checkpoint_root(self.base))
        self.assertEqual(len(groups), 2)

    def test_large_file_skipped(self):
        path = os.path.join(self.base, "big.bin")
        with open(path, "wb") as f:
            f.write(b"x" * (5 * 1024 * 1024 + 10))
        name = save_before_change(self.base, [path], "write_file")
        self.assertIsNotNone(name)
        msg = undo_last(self.base)
        self.assertIn("dilewati", msg)


class ExecuteToolUndoTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_cp_exec_")
        self.base = self._tmp.name
        self._orig = (
            main.config.BASE_DIR,
            main.config.APPROVAL_MODE,
            main.config.CHECKPOINT_ENABLED,
            main.config.CHECKPOINT_KEEP,
        )
        main.config.BASE_DIR = self.base
        main.config.APPROVAL_MODE = "auto"
        main.config.CHECKPOINT_ENABLED = True
        main.config.CHECKPOINT_KEEP = 30

    def tearDown(self):
        (
            main.config.BASE_DIR,
            main.config.APPROVAL_MODE,
            main.config.CHECKPOINT_ENABLED,
            main.config.CHECKPOINT_KEEP,
        ) = self._orig
        self._tmp.cleanup()

    def test_write_then_undo(self):
        main.execute_tool("write_file", {"filename": "a.txt", "content": "versi1"})
        main.execute_tool("write_file", {"filename": "a.txt", "content": "versi2"})
        self.assertEqual(main.checkpoint_undo(self.base).count("dipulihkan"), 1)
        with open(os.path.join(self.base, "a.txt")) as f:
            self.assertEqual(f.read(), "versi1")

    def test_delete_then_undo(self):
        _write(self.base, "a.txt", "isi")
        main.execute_tool("delete_file", {"filename": "a.txt"})
        self.assertFalse(os.path.exists(os.path.join(self.base, "a.txt")))
        main.execute_tool("read_file", {"filename": "a.txt"})  # read tidak bikin checkpoint
        main.checkpoint_undo(self.base)
        with open(os.path.join(self.base, "a.txt")) as f:
            self.assertEqual(f.read(), "isi")

    def test_apply_patch_then_undo(self):
        _write(self.base, "a.txt", "satu\ndua\n")
        patch = (
            "--- a/a.txt\n+++ b/a.txt\n@@ -1,2 +1,2 @@\n satu\n-dua\n+tiga\n"
        )
        result = main.execute_tool("apply_patch", {"patch": patch})
        self.assertIn("M a.txt", result)
        main.checkpoint_undo(self.base)
        with open(os.path.join(self.base, "a.txt")) as f:
            self.assertEqual(f.read(), "satu\ndua\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
