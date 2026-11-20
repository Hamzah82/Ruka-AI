#!/usr/bin/env python3
"""Test pencarian session (nama + isi) dan /stats."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402


class SessionSearchTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ruka_sess_")
        self.sessions = os.path.join(self._tmp.name, "sessions")
        os.makedirs(self.sessions)
        self.base = os.path.join(self._tmp.name, "ws")
        os.makedirs(self.base)
        self._orig = (main.config.SESSIONS_DIR, main.config.BASE_DIR, main.config.MEMORY_DIR)
        main.config.SESSIONS_DIR = self.sessions
        main.config.BASE_DIR = self.base
        main.config.MEMORY_DIR = os.path.join(self._tmp.name, "memory")

        self._make("deploy-vercel", [
            {"role": "user", "content": "tolong deploy ke vercel"},
            {"role": "assistant", "content": "Siap, saya jalankan vercel --prod."},
        ])
        self._make("catatan", [
            {"role": "user", "content": "ringkas laporan keuangan"},
            {"role": "assistant", "content": "Laporan singkat: pendapatan naik."},
        ])

    def _make(self, name, messages):
        data = {
            "name": name,
            "created_at": "2026-01-01T10:00:00",
            "updated_at": "2026-01-02T10:00:00",
            "message_count": len(messages),
            "messages": messages,
        }
        with open(os.path.join(self.sessions, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    def tearDown(self):
        (
            main.config.SESSIONS_DIR,
            main.config.BASE_DIR,
            main.config.MEMORY_DIR,
        ) = self._orig
        self._tmp.cleanup()

    def test_search_by_name(self):
        out = main.search_sessions("vercel")
        self.assertIn("deploy-vercel", out)
        self.assertNotIn("catatan", out.split("Pencarian")[1])

    def test_search_by_content(self):
        out = main.search_sessions("pendapatan")
        self.assertIn("catatan", out)
        self.assertIn("kecocokan isi", out)
        self.assertIn("pendapatan naik", out)

    def test_search_by_tool_arguments(self):
        self._make("tools", [
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "1", "type": "function",
                 "function": {"name": "read_file", "arguments": "{\"filename\": \"rahasia.txt\"}"}}
            ]},
        ])
        out = main.search_sessions("rahasia.txt")
        self.assertIn("tools", out)

    def test_no_match(self):
        out = main.search_sessions("zzz-tidak-ada")
        self.assertIn("Tidak ditemukan", out)

    def test_empty_keyword(self):
        self.assertIn("kosong", main.search_sessions("  "))

    def test_stats_reports_context_and_sessions(self):
        messages = [
            {"role": "system", "content": "s" * 400},
            {"role": "user", "content": "halo"},
        ]
        out = main._collect_stats(messages)
        self.assertIn("Statistik", out)
        self.assertIn("2 tersimpan", out)
        self.assertIn("token", out)
        self.assertIn("mode izin", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
