#!/usr/bin/env python3
"""Test kebijakan auto-update (opt-in) dan reuse HTTP session."""
import sys
import os
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402


class AutoUpdateTest(unittest.TestCase):
    def setUp(self):
        self._orig = main.config.AUTO_UPDATE

    def tearDown(self):
        main.config.AUTO_UPDATE = self._orig

    def test_disabled_by_default_no_network(self):
        main.config.AUTO_UPDATE = False
        with mock.patch.object(main.subprocess, "run") as run:
            self.assertFalse(main.check_for_updates())
            run.assert_not_called()

    def test_enabled_but_not_a_repo_is_noop(self):
        main.config.AUTO_UPDATE = True
        with mock.patch.object(main.os.path, "isdir", return_value=False), \
                mock.patch.object(main.subprocess, "run") as run:
            self.assertFalse(main.check_for_updates())
            run.assert_not_called()

    def test_force_needs_network_only_with_repo(self):
        main.config.AUTO_UPDATE = False
        with mock.patch.object(main.os.path, "isdir", return_value=False), \
                mock.patch.object(main.subprocess, "run") as run:
            self.assertFalse(main.check_for_updates(force=True))
            run.assert_not_called()


class HttpSessionTest(unittest.TestCase):
    def test_session_is_reused(self):
        import requests

        self.assertIsInstance(main.HTTP_SESSION, requests.Session)
        # Header tidak ditempel permanen: setiap request tetap mengirim HEADERS.
        self.assertEqual(main.HTTP_SESSION.headers.get("Authorization"), None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
