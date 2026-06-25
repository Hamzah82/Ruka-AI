"""Test lebar UI dinamis: clamp [40..100], fallback, & back-compat width eksplisit.

Headless: monkeypatch main.shutil.get_terminal_size agar deterministik.
"""
import os

import pytest

import main


def _setcols(monkeypatch, cols):
    monkeypatch.setattr(
        main.shutil, "get_terminal_size",
        lambda fallback=(80, 24): os.terminal_size((cols, 24)),
    )


def test_term_cols_clamp_min(monkeypatch):
    _setcols(monkeypatch, 20)
    assert main._term_cols() == 40


def test_term_cols_clamp_max(monkeypatch):
    _setcols(monkeypatch, 200)
    assert main._term_cols() == 100


def test_term_cols_passthrough(monkeypatch):
    _setcols(monkeypatch, 72)
    assert main._term_cols() == 72


def test_term_cols_fallback_on_exception(monkeypatch):
    def boom(*a, **k):
        raise OSError("no tty")
    monkeypatch.setattr(main.shutil, "get_terminal_size", boom)
    assert main._term_cols() == 80                       # default fallback
    assert main.TerminalFormatter._term_width() == 70    # fallback=TERM_WIDTH


def test_rule_dynamic_and_explicit(monkeypatch):
    _setcols(monkeypatch, 50)
    assert len(main._strip_ansi(main._rule())) == 46     # 50 - 4
    assert len(main._strip_ansi(main._rule(width=10))) == 10  # eksplisit menang


def test_box_within_terminal(monkeypatch):
    _setcols(monkeypatch, 48)
    lines = main._box(["x"]).splitlines()
    for ln in lines:
        assert main._visible_len(ln) <= 48               # tak overflow


def test_box_explicit_width_unchanged(monkeypatch):
    _setcols(monkeypatch, 48)
    top = main._box(["x"], width=30).splitlines()[0]
    assert main._strip_ansi(top).count("─") == 30        # back-compat


def test_formatter_hr_dynamic(monkeypatch):
    _setcols(monkeypatch, 60)
    out = main.TerminalFormatter._format_horizontal_rules("---")
    assert "─" * (60 - 4) in out
