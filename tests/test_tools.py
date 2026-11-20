#!/usr/bin/env python3
"""Test tool pencarian/patch dan aturan workspace."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ruka.extra_tools import (  # noqa: E402
    PatchError,
    apply_patch,
    fuzzy_replace,
    glob_files,
    grep_files,
)
from ruka.rules import (  # noqa: E402
    build_rules_section,
    is_ignored,
    load_ignore_patterns,
    load_workspace_rules,
)


def _write(base, rel, content):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class RulesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_rules_")
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_rules_returns_empty(self):
        self.assertEqual(load_workspace_rules(self.base), "")
        self.assertEqual(build_rules_section(self.base), "")

    def test_ruka_md_is_loaded(self):
        _write(self.base, "RUKA.md", "Selalu pakai pytest.\n")
        self.assertIn("pytest", load_workspace_rules(self.base))
        self.assertIn("ATURAN WORKSPACE", build_rules_section(self.base))

    def test_agents_md_fallback(self):
        _write(self.base, "AGENTS.md", "Gunakan 2 spasi.\n")
        self.assertIn("2 spasi", load_workspace_rules(self.base))

    def test_rules_are_truncated(self):
        _write(self.base, "RUKA.md", "x" * 40_000)
        rules = load_workspace_rules(self.base)
        self.assertLessEqual(len(rules), 32_100)
        self.assertIn("dipotong", rules)

    def test_ignore_file_patterns(self):
        _write(self.base, ".rukaignore", "# komentar\nvendor/\n*.log\n")
        patterns = load_ignore_patterns(self.base)
        self.assertEqual(patterns, ["vendor/", "*.log"])
        self.assertTrue(is_ignored("vendor/lib.py", patterns))
        self.assertTrue(is_ignored("logs/app.log", patterns))
        self.assertFalse(is_ignored("src/app.py", patterns))

    def test_default_ignored_dirs(self):
        self.assertTrue(is_ignored(".git/config"))
        self.assertTrue(is_ignored("node_modules/x/index.js"))
        self.assertTrue(is_ignored("src/__pycache__/x.pyc"))
        self.assertFalse(is_ignored("src/app.py"))


class GrepGlobTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_grep_")
        self.base = self._tmp.name
        _write(self.base, "a.py", "def main():\n    return 1\n# TODO: rapikan\n")
        _write(self.base, "b.txt", "halo dunia\n")
        _write(self.base, "pkg/c.py", "def main():\n    pass\n")
        _write(self.base, "node_modules/d.js", "def main()\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_grep_finds_matches_with_location(self):
        out = grep_files("def main", self.base)
        self.assertIn("a.py:1:", out)
        self.assertIn("pkg/c.py:1:", out)

    def test_grep_skips_ignored_dirs(self):
        out = grep_files("def main", self.base)
        self.assertNotIn("node_modules", out)

    def test_grep_glob_filter(self):
        out = grep_files("def main", self.base, glob="*.py")
        self.assertIn("a.py", out)
        out = grep_files("dunia", self.base, glob="*.py")
        self.assertIn("Tidak ada hasil", out)

    def test_grep_case_sensitive(self):
        self.assertIn("Tidak ada hasil", grep_files("todo", self.base, case_sensitive=True))
        self.assertIn("TODO", grep_files("todo", self.base))

    def test_grep_invalid_regex(self):
        self.assertIn("regex tidak valid", grep_files("([", self.base))

    def test_grep_rejects_traversal(self):
        out = grep_files("x", self.base, path="../")
        self.assertTrue("tidak diizinkan" in out or "di luar workspace" in out, out)

    def test_glob_finds_paths(self):
        out = glob_files("**/*.py", self.base)
        self.assertIn("a.py", out)
        self.assertIn("pkg/c.py", out)
        self.assertNotIn("b.txt", out)

    def test_glob_skips_ignored(self):
        self.assertNotIn("node_modules", glob_files("**/*.js", self.base))

    def test_glob_rejects_absolute(self):
        self.assertIn("absolut", glob_files("/etc/*", self.base))


class ApplyPatchTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_patch_")
        self.base = self._tmp.name
        _write(self.base, "hello.py", "satu\ndua\ntiga\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_modify_file(self):
        patch = (
            "--- a/hello.py\n"
            "+++ b/hello.py\n"
            "@@ -1,3 +1,4 @@\n"
            " satu\n"
            "-dua\n"
            "+DUA\n"
            "+dua-baru\n"
            " tiga\n"
        )
        out = apply_patch(patch, self.base)
        self.assertIn("M hello.py", out)
        with open(os.path.join(self.base, "hello.py")) as f:
            self.assertEqual(f.read(), "satu\nDUA\ndua-baru\ntiga\n")

    def test_create_file(self):
        patch = "--- /dev/null\n+++ b/baru.txt\n@@ -0,0 +1,2 @@\n+halo\n+dunia\n"
        out = apply_patch(patch, self.base)
        self.assertIn("A baru.txt", out)
        with open(os.path.join(self.base, "baru.txt")) as f:
            self.assertEqual(f.read(), "halo\ndunia\n")

    def test_delete_file(self):
        patch = "--- a/hello.py\n+++ /dev/null\n@@ -1,3 +0,0 @@\n-satu\n-dua\n-tiga\n"
        out = apply_patch(patch, self.base)
        self.assertIn("D hello.py", out)
        self.assertFalse(os.path.exists(os.path.join(self.base, "hello.py")))

    def test_context_mismatch_rejected(self):
        patch = (
            "--- a/hello.py\n+++ b/hello.py\n@@ -1,2 +1,2 @@\n satu\n-tidak-ada\n+baru\n"
        )
        with self.assertRaises(PatchError):
            apply_patch(patch, self.base)
        with open(os.path.join(self.base, "hello.py")) as f:
            self.assertEqual(f.read(), "satu\ndua\ntiga\n")

    def test_traversal_rejected(self):
        patch = "--- /dev/null\n+++ b/../evil.txt\n@@ -0,0 +1 @@\n+x\n"
        with self.assertRaises(PatchError):
            apply_patch(patch, self.base)
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.base), "evil.txt")))

    def test_invalid_patch_rejected(self):
        with self.assertRaises(PatchError):
            apply_patch("bukan patch", self.base)


class FuzzyReplaceTest(unittest.TestCase):
    def test_matches_ignoring_indentation(self):
        content = "def f():\n    return 1\n"
        result, count = fuzzy_replace(content, "def f():\nreturn 1", "def f():\n    return 2")
        self.assertEqual(count, 1)
        self.assertIn("return 2", result)

    def test_ambiguous_without_replace_all(self):
        content = "a\nb\na\nb\n"
        result, count = fuzzy_replace(content, "a\nb", "c")
        self.assertIsNone(result)
        self.assertEqual(count, 2)

    def test_replace_all(self):
        result, count = fuzzy_replace("x\ny\nx\ny\n", "x\ny", "z", replace_all=True)
        self.assertEqual(count, 2)
        self.assertEqual(result, "z\nz\n")

    def test_no_match(self):
        result, count = fuzzy_replace("abc\n", "zzz", "y")
        self.assertIsNone(result)
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
