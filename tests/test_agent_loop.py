#!/usr/bin/env python3
"""Test pengaman agent loop: batas putaran & deteksi tool identik."""
import json
import sys
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import main  # noqa: E402


def _tool_msg(call_id, filename="a.txt"):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"filename": filename}),
                },
            }
        ],
    }


def _final_msg(text="final"):
    return {"role": "assistant", "content": text}


def _resp(message):
    return {"choices": [{"message": message}]}


class AgentLoopGuardTest(unittest.TestCase):
    def setUp(self):
        self._orig = (
            main.chat,
            main.execute_tool,
            main._is_interrupted,
            main._check_interrupt_nonblock,
            main.show_thinking,
            main.show_tool_call,
            main.show_model_narration,
            main.config.MAX_ROUNDS_PER_TURN,
            main.config.MAX_IDENTICAL_TOOL_CALLS,
        )
        main._is_interrupted = lambda: False
        main._check_interrupt_nonblock = lambda: None
        main.show_thinking = lambda *a, **k: None
        main.show_tool_call = lambda *a, **k: None
        main.show_model_narration = lambda *a, **k: None
        self.executed = []
        main.execute_tool = lambda name, args: (self.executed.append((name, args)), "ok")[1]
        self.chat_calls = []
        self.responses = []

        def fake_chat(messages, **kwargs):
            self.chat_calls.append(dict(kwargs))
            return self.responses.pop(0)

        main.chat = fake_chat
        main.config.MAX_ROUNDS_PER_TURN = 50
        main.config.MAX_IDENTICAL_TOOL_CALLS = 2

    def tearDown(self):
        (
            main.chat,
            main.execute_tool,
            main._is_interrupted,
            main._check_interrupt_nonblock,
            main.show_thinking,
            main.show_tool_call,
            main.show_model_narration,
            main.config.MAX_ROUNDS_PER_TURN,
            main.config.MAX_IDENTICAL_TOOL_CALLS,
        ) = self._orig

    def test_max_rounds_forces_final_answer(self):
        main.config.MAX_ROUNDS_PER_TURN = 2
        main.config.MAX_IDENTICAL_TOOL_CALLS = 0  # nonaktifkan deteksi duplikat
        self.responses = [
            _resp(_tool_msg("1", "a")),
            _resp(_tool_msg("2", "b")),
            _resp(_tool_msg("3", "c")),  # tidak diproses: cap tercapai
            _resp(_final_msg("ringkasan akhir")),
        ]
        messages = [{"role": "system", "content": "s"}]
        reply, messages, interrupted = main.process_response(messages, self.responses.pop(0))
        self.assertEqual(reply, "ringkasan akhir")
        self.assertFalse(interrupted)
        self.assertEqual(len(self.executed), 2)
        self.assertEqual(self.chat_calls[-1].get("include_tools"), False)

    def test_identical_tool_call_is_blocked(self):
        main.config.MAX_IDENTICAL_TOOL_CALLS = 1
        self.responses = [
            _resp(_tool_msg("1")),
            _resp(_tool_msg("2")),  # identik → diblokir
            _resp(_final_msg("selesai")),
        ]
        messages = [{"role": "system", "content": "s"}]
        reply, messages, _ = main.process_response(messages, self.responses.pop(0))
        self.assertEqual(reply, "selesai")
        self.assertEqual(len(self.executed), 1)
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        self.assertEqual(len(tool_msgs), 2)
        self.assertIn("IDENTIK", tool_msgs[1]["content"])

    def test_no_progress_forces_final(self):
        main.config.MAX_IDENTICAL_TOOL_CALLS = 1
        main.config.MAX_ROUNDS_PER_TURN = 0
        self.responses = [
            _resp(_tool_msg("1")),
            _resp(_tool_msg("2")),
            _resp(_tool_msg("3")),
            _resp(_final_msg("menyerah dengan ringkasan")),
        ]
        messages = [{"role": "system", "content": "s"}]
        reply, messages, _ = main.process_response(messages, self.responses.pop(0))
        self.assertEqual(reply, "menyerah dengan ringkasan")
        self.assertEqual(len(self.executed), 1)
        self.assertEqual(self.chat_calls[-1].get("include_tools"), False)

    def test_normal_two_calls_not_blocked(self):
        main.config.MAX_IDENTICAL_TOOL_CALLS = 2
        self.responses = [
            _resp(_tool_msg("1", "a")),
            _resp(_tool_msg("2", "a")),  # kedua masih boleh
            _resp(_final_msg("ok")),
        ]
        messages = [{"role": "system", "content": "s"}]
        reply, _, _ = main.process_response(messages, self.responses.pop(0))
        self.assertEqual(reply, "ok")
        self.assertEqual(len(self.executed), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
