#!/usr/bin/env python3
"""Test kebijakan retry API & compaction adaptif."""
import sys
import os
import unittest
from unittest import mock

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402


class FakeResponse:
    def __init__(self, status=200, text="", headers=None):
        self.status_code = status
        self.text = text
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


def _ok(content="ok"):
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "usage": {}}


class RetryPolicyTest(unittest.TestCase):
    def setUp(self):
        self.sleeps = []
        self._orig = (main.time.sleep, main._consume_stream, main.requests.post)
        main.time.sleep = lambda s: self.sleeps.append(s)
        main._consume_stream = lambda response: _ok()

    def tearDown(self):
        main.time.sleep, main._consume_stream, main.requests.post = self._orig

    def _run(self, side_effect, **kwargs):
        with mock.patch.object(main.requests, "post", side_effect=side_effect) as post:
            try:
                result = main.chat(
                    [{"role": "user", "content": "hi"}],
                    max_retries=3,
                    retry_base_delay=0.01,
                    quiet=True,
                    **kwargs,
                )
            finally:
                self.calls = post.call_count
        return result

    def test_context_length_is_not_retried(self):
        side = [FakeResponse(400, "maximum context length exceeded")]
        with self.assertRaises(main.ContextLengthError):
            self._run(side)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.sleeps, [])

    def test_auth_error_is_not_retried(self):
        side = [FakeResponse(401, "invalid api key")]
        with self.assertRaises(requests.HTTPError):
            self._run(side)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.sleeps, [])

    def test_server_error_is_retried_then_succeeds(self):
        main._consume_stream = lambda response: _ok("pulih")
        side = [FakeResponse(500, "server error"), FakeResponse(200)]
        result = self._run(side)
        self.assertEqual(result["choices"][0]["message"]["content"], "pulih")
        self.assertEqual(self.calls, 2)
        self.assertEqual(len(self.sleeps), 1)

    def test_retry_after_is_honored(self):
        main._consume_stream = lambda response: _ok("pulih")
        side = [FakeResponse(429, "rate limit", {"Retry-After": "5"}), FakeResponse(200)]
        self._run(side)
        self.assertEqual(self.calls, 2)
        self.assertGreaterEqual(self.sleeps[0], 5)

    def test_success_first_try(self):
        result = self._run([FakeResponse(200)])
        self.assertEqual(result["choices"][0]["message"]["content"], "ok")
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.sleeps, [])


class CompactionAdaptiveTest(unittest.TestCase):
    def setUp(self):
        self._orig = (main.chat, main._summarize_detailed, main.config.COMPACT_KEEP_TURNS)

    def tearDown(self):
        main.chat, main._summarize_detailed, main.config.COMPACT_KEEP_TURNS = self._orig

    def test_chunk_splits_on_context_error(self):
        responses = [
            main.ContextLengthError("too long"),
            _ok("kiri"),
            _ok("kanan"),
        ]

        def fake_chat(messages, **kwargs):
            item = responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        main.chat = fake_chat
        result = main._summarize_chunk_detailed(
            [{"role": "user", "content": "a"}, {"role": "user", "content": "b"}]
        )
        self.assertIn("kiri", result)
        self.assertIn("kanan", result)

    def test_failure_is_reported(self):
        main._summarize_detailed = lambda messages: ""
        main.config.COMPACT_KEEP_TURNS = 1
        msgs = [{"role": "system", "content": "prompt utama"}]
        for i in range(3):
            msgs.append({"role": "user", "content": f"u{i}"})
            msgs.append({"role": "assistant", "content": f"a{i}"})
        new_msgs, compacted, info = main.compact_history(msgs, force=True)
        self.assertFalse(compacted)
        self.assertIs(new_msgs, msgs)
        self.assertIn("gagal", info.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
