#!/usr/bin/env python3
"""
Test keamanan path Ruka AI.

Fokus: pemisahan hak BACA vs TULIS (`_safe_path`) dan penolakan path traversal,
symlink escape, serta penulisan ke folder instalasi (main.py/SKILL/config.json).

Jalankan:
    python -m pytest tests/test_security.py -v
    python tests/test_security.py
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402


class SafePathTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_pathtest_")
        root = self._tmp.name
        self.base = os.path.join(root, "workspace")
        self.script = os.path.join(root, "install")
        self.outside = os.path.join(root, "outside")
        for d in (self.base, self.script, self.outside):
            os.makedirs(d, exist_ok=True)

        # File contoh di workspace & folder instalasi
        with open(os.path.join(self.base, "catatan.txt"), "w") as f:
            f.write("isi workspace")
        os.makedirs(os.path.join(self.base, "sub"), exist_ok=True)
        with open(os.path.join(self.script, "main.py"), "w") as f:
            f.write("# source")
        os.makedirs(os.path.join(self.script, "SKILL"), exist_ok=True)
        with open(os.path.join(self.script, "SKILL", "skills.md"), "w") as f:
            f.write("# skill")
        with open(os.path.join(self.outside, "rahasia.txt"), "w") as f:
            f.write("secret")

        self._orig = (
            main.config.BASE_DIR,
            main.config.SCRIPT_DIR,
            getattr(main.config, "ALLOW_INTERNAL_WRITE", False),
        )
        main.config.BASE_DIR = self.base
        main.config.SCRIPT_DIR = self.script
        main.config.ALLOW_INTERNAL_WRITE = False

    def tearDown(self):
        (
            main.config.BASE_DIR,
            main.config.SCRIPT_DIR,
            main.config.ALLOW_INTERNAL_WRITE,
        ) = self._orig
        self._tmp.cleanup()

    # ── Baca ────────────────────────────────────────────────────
    def test_read_workspace_ok(self):
        p = main._safe_path("catatan.txt")
        self.assertEqual(p, os.path.join(self.base, "catatan.txt"))

    def test_read_install_dir_ok(self):
        p = main._safe_path("SKILL/skills.md")
        self.assertEqual(p, os.path.join(self.script, "SKILL", "skills.md"))

    def test_read_outside_denied(self):
        self.assertIsNone(main._safe_path(os.path.join(self.outside, "rahasia.txt")))

    def test_read_traversal_denied(self):
        self.assertIsNone(main._safe_path("../outside/rahasia.txt"))

    def test_null_byte_denied(self):
        self.assertIsNone(main._safe_path("catatan.txt\x00.png"))

    # ── Tulis ───────────────────────────────────────────────────
    def test_write_workspace_ok(self):
        p = main._safe_path("baru.txt", write=True)
        self.assertEqual(p, os.path.join(self.base, "baru.txt"))

    def test_write_subdir_ok(self):
        p = main._safe_path("sub/baru.txt", write=True)
        self.assertEqual(p, os.path.join(self.base, "sub", "baru.txt"))

    def test_write_same_name_as_internal_resolves_to_workspace(self):
        # "main.py" ada di folder instalasi; operasi tulis tetap harus ke workspace.
        p = main._safe_path("main.py", write=True)
        self.assertEqual(p, os.path.join(self.base, "main.py"))

    def test_write_install_file_denied(self):
        # Path absolut ke folder instalasi harus ditolak.
        self.assertIsNone(main._safe_path(os.path.join(self.script, "main.py"), write=True))
        self.assertIsNone(
            main._safe_path(os.path.join(self.script, "SKILL", "skills.md"), write=True)
        )

    def test_write_relative_name_never_targets_install_dir(self):
        # Nama relatif yang kebetulan sama dengan file internal tetap ke workspace.
        self.assertEqual(
            main._safe_path("SKILL/skills.md", write=True),
            os.path.join(self.base, "SKILL", "skills.md"),
        )

    def test_write_outside_denied(self):
        self.assertIsNone(main._safe_path(os.path.join(self.outside, "x.txt"), write=True))

    def test_write_sibling_prefix_denied(self):
        evil = self.base + "-evil"
        os.makedirs(evil, exist_ok=True)
        self.assertIsNone(main._safe_path(os.path.join(evil, "x.txt"), write=True))

    def test_symlink_escape_denied(self):
        link = os.path.join(self.base, "link")
        try:
            os.symlink(self.outside, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlink tidak didukung")
        self.assertIsNone(main._safe_path("link/x.txt", write=True))
        self.assertIsNone(main._safe_path("link/rahasia.txt"))

    def test_allow_internal_write_opt_in(self):
        target = os.path.join(self.script, "SKILL", "skills.md")
        self.assertIsNone(main._safe_path(target, write=True))
        main.config.ALLOW_INTERNAL_WRITE = True
        self.assertEqual(main._safe_path(target, write=True), target)

    # ── Integrasi tool ──────────────────────────────────────────
    def test_tool_write_refuses_internal_file(self):
        result = main.tool_write_file(os.path.join(self.script, "main.py"), "backdoor")
        self.assertTrue(result.startswith("Error"), result)
        with open(os.path.join(self.script, "main.py")) as f:
            self.assertEqual(f.read(), "# source")

    def test_tool_write_same_relative_name_stays_in_workspace(self):
        result = main.tool_write_file("main.py", "workspace copy")
        self.assertIn("berhasil", result)
        with open(os.path.join(self.base, "main.py")) as f:
            self.assertEqual(f.read(), "workspace copy")
        with open(os.path.join(self.script, "main.py")) as f:
            self.assertEqual(f.read(), "# source")

    def test_tool_write_creates_workspace_file(self):
        result = main.tool_write_file("baru.txt", "halo")
        self.assertIn("berhasil", result)
        with open(os.path.join(self.base, "baru.txt")) as f:
            self.assertEqual(f.read(), "halo")

    def test_tool_edit_refuses_internal_file(self):
        target = os.path.join(self.script, "SKILL", "skills.md")
        result = main.tool_edit_file(target, "replace", "x", "# skill")
        self.assertTrue(result.startswith("Error"), result)

    def test_tool_delete_refuses_internal_file(self):
        result = main.tool_delete_file(os.path.join(self.script, "main.py"))
        self.assertTrue(result.startswith("Error"), result)
        self.assertTrue(os.path.exists(os.path.join(self.script, "main.py")))

    def test_tool_move_source_internal_denied(self):
        source = os.path.join(self.script, "SKILL", "skills.md")
        result = main.tool_move_file(source, "skills.md")
        self.assertTrue(result.startswith("Error"), result)
        self.assertTrue(os.path.exists(source))

    def test_delete_workspace_root_refused(self):
        result = main.tool_delete_folder(".", recursive=True)
        self.assertTrue(result.startswith("Error"), result)
        self.assertTrue(os.path.isdir(self.base))


if __name__ == "__main__":
    unittest.main(verbosity=2)
