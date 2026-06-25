"""Test hard-trim riwayat: deterministik, jaga pasangan tool-call, tak memutasi.

Semua headless (tanpa jaringan/TTY). _trim_history/_drop_orphan_tools/_estimate_tokens
adalah fungsi murni → diuji langsung.
"""
import copy

import config
import main


def _seg(i, big=""):
    """Satu giliran utuh: user → assistant(tool_call) → tool → assistant(final)."""
    return [
        {"role": "user", "content": f"req{i} {big}"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": f"c{i}", "type": "function",
                         "function": {"name": "read_file", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": f"c{i}", "content": f"hasil{i} {big}"},
        {"role": "assistant", "content": f"jawaban{i}"},
    ]


def _build(n, big=""):
    msgs = [{"role": "system", "content": "system prompt"}]
    for i in range(n):
        msgs += _seg(i, big=big)
    return msgs


def _assert_pairing_valid(msgs):
    # Setiap 'tool' didahului assistant yang mendeklarasikan id-nya.
    seen = set()
    for m in msgs:
        if m["role"] == "assistant":
            for tc in (m.get("tool_calls") or []):
                seen.add(tc["id"])
        elif m["role"] == "tool":
            assert m["tool_call_id"] in seen, "orphan tool message"
    # Setiap assistant(tool_calls) dijawab pesan tool (tak dangling).
    answered = {m["tool_call_id"] for m in msgs if m["role"] == "tool"}
    for m in msgs:
        if m["role"] == "assistant":
            for tc in (m.get("tool_calls") or []):
                assert tc["id"] in answered, "dangling assistant tool_calls"


def _count_segments(body):
    n = 0
    for m in body:
        if m["role"] == "user":
            n += 1
    return n


def test_small_history_unchanged(monkeypatch):
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 100_000)
    msgs = _build(2)
    trimmed, dropped = main._trim_history(msgs)
    assert dropped == 0 and trimmed is msgs


def test_large_history_trimmed(monkeypatch):
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 500)
    monkeypatch.setattr(config, "KEEP_RECENT_MESSAGES", 4)
    msgs = _build(30, big="x" * 200)
    trimmed, dropped = main._trim_history(msgs)
    assert dropped > 0
    body = [m for m in trimmed if m["role"] != "system"]
    est = main._estimate_tokens(trimmed)
    # Assert toleran: di bawah ambang ATAU 1 segmen tersisa ATAU lantai keep_recent.
    assert est <= 500 or _count_segments(body) == 1 or len(body) <= 4


def test_system_always_first(monkeypatch):
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 300)
    monkeypatch.setattr(config, "KEEP_RECENT_MESSAGES", 4)
    trimmed, _ = main._trim_history(_build(20, big="y" * 200))
    assert trimmed[0]["role"] == "system"
    assert sum(1 for m in trimmed if m["role"] == "system") == 1


def test_pairing_valid_after_trim(monkeypatch):
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 400)
    monkeypatch.setattr(config, "KEEP_RECENT_MESSAGES", 4)
    trimmed, _ = main._trim_history(_build(25, big="z" * 150))
    _assert_pairing_valid(trimmed)


def test_pairing_valid_inflight_turn(monkeypatch):
    # Giliran berjalan: berakhir pada 'tool' (menunggu assistant final) — chat()
    # dipanggil mid-loop. Trim tak boleh memutus pasangan.
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 300)
    monkeypatch.setattr(config, "KEEP_RECENT_MESSAGES", 3)
    msgs = _build(15, big="w" * 150)
    msgs += [
        {"role": "user", "content": "req-now"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "cN", "type": "function",
                         "function": {"name": "list_files", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "cN", "content": "hasil-now"},
    ]
    trimmed, _ = main._trim_history(msgs)
    _assert_pairing_valid(trimmed)


def test_drop_orphan_tools_bidirectional():
    # (a) tool yatim dibuang
    a = main._drop_orphan_tools([
        {"role": "system", "content": "s"},
        {"role": "tool", "tool_call_id": "x", "content": "r"},
        {"role": "user", "content": "hi"},
    ])
    assert all(m["role"] != "tool" for m in a)
    # (b) assistant dangling (tool_calls tak terjawab) dibuang
    b = main._drop_orphan_tools([
        {"role": "system", "content": "s"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "x", "type": "function",
                         "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "assistant", "content": "final"},
    ])
    assert all(not (m["role"] == "assistant" and m.get("tool_calls")) for m in b)
    _assert_pairing_valid(b)


def test_keep_recent_floor(monkeypatch):
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 1)  # paksa trim maksimal
    monkeypatch.setattr(config, "KEEP_RECENT_MESSAGES", 8)
    trimmed, _ = main._trim_history(_build(20, big="q" * 100))
    body = [m for m in trimmed if m["role"] != "system"]
    assert len(body) >= 4  # tak digerus habis; segmen terakhir utuh (>=1 segmen)


def test_estimate_tokens_charsdiv4():
    est = main._estimate_tokens([{"role": "user", "content": "a" * 400}])
    assert 100 <= est <= 130  # (400 + overhead 16) // 4


def test_messages_not_mutated(monkeypatch):
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 300)
    monkeypatch.setattr(config, "KEEP_RECENT_MESSAGES", 4)
    msgs = _build(20, big="m" * 150)
    snapshot = copy.deepcopy(msgs)
    main._trim_history(msgs)
    assert msgs == snapshot  # input utuh → save_session/transkrip aman


def test_only_system_and_one_user_no_drop(monkeypatch):
    monkeypatch.setattr(config, "MAX_HISTORY_TOKENS", 1)
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "x" * 5000}]
    trimmed, dropped = main._trim_history(msgs)
    assert dropped == 0  # jangan pernah buang segmen terakhir


def test_show_trim_notice_prints(capsys):
    main.show_trim_notice(5, 1234)
    out = capsys.readouterr().out
    assert "dipangkas" in out and "5" in out


def test_begin_turn_resets_trim_flag():
    main._spinner._trim_notice_shown = True
    main._spinner.begin_turn()
    assert main._spinner._trim_notice_shown is False
