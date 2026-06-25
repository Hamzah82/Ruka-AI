"""Test _scrubbed_env: rahasia Ruka tidak bocor ke subprocess, env normal utuh.

Headless: mock subprocess.run untuk uji dua cabang tanpa eksekusi nyata;
test eksekusi nyata di-skip di Windows.
"""
import os
import sys
import types

import pytest

import config
import main


def test_scrub_removes_openrouter_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-secret-123456")
    assert "OPENROUTER_API_KEY" not in main._scrubbed_env()


def test_scrub_keeps_path_home(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("HOME", "/home/x")
    env = main._scrubbed_env()
    assert env["PATH"] == "/usr/bin"
    assert env["HOME"] == "/home/x"


def test_scrub_keeps_lookalike_user_vars(monkeypatch):
    # Var sah yang mengandung kata KEY/TOKEN/SECRET TIDAK boleh terbuang
    # (denylist bertarget nama eksak, bukan pola substring).
    for k in ("SSH_AUTH_SOCK", "GPG_TTY", "MY_TOKEN_DIR", "KEYBOARD_LAYOUT"):
        monkeypatch.setenv(k, "nilai-dummy")
    env = main._scrubbed_env()
    for k in ("SSH_AUTH_SOCK", "GPG_TTY", "MY_TOKEN_DIR", "KEYBOARD_LAYOUT"):
        assert k in env


def test_scrub_value_match_alias(monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "sk-abc12345")
    monkeypatch.setenv("LLM_KEY", "sk-abc12345")  # alias non-standar dgn nilai sama
    assert "LLM_KEY" not in main._scrubbed_env()


def test_scrub_empty_key_no_mass_delete(monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    monkeypatch.setenv("EMPTY_VAR", "")
    assert "EMPTY_VAR" in main._scrubbed_env()  # guard `if secret` mencegah hapus massal


def test_scrub_short_key_no_false_positive(monkeypatch):
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "1")  # < 8 char
    monkeypatch.setenv("X_SHORT", "1")
    assert "X_SHORT" in main._scrubbed_env()  # guard len>=8 mencegah false-positive


def test_scrub_does_not_mutate_os_environ(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-keep-in-environ-1234")
    before = dict(os.environ)
    main._scrubbed_env()
    assert dict(os.environ) == before
    assert "OPENROUTER_API_KEY" in os.environ  # proses Ruka tetap punya key


@pytest.mark.skipif(sys.platform == "win32", reason="butuh shell unix")
def test_exec_command_cannot_read_key(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-LEAK-9999999")
    out = main.tool_exec_command("printenv OPENROUTER_API_KEY || true", timeout=10)
    assert "sk-LEAK-9999999" not in out


@pytest.mark.skipif(sys.platform == "win32", reason="butuh shell unix")
def test_exec_command_still_sees_normal_env(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", "/home/dummy")
    out = main.tool_exec_command("echo $HOME", timeout=10)
    assert "/home/dummy" in out


def test_both_branches_use_scrubbed_env(tmp_path, monkeypatch):
    """Kedua cabang (win32 & unix) harus memakai env yang sudah di-scrub.

    Mock subprocess.run (rekam kwargs['env']) — tanpa eksekusi nyata.
    """
    monkeypatch.setattr(config, "BASE_DIR", str(tmp_path))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-LEAK-abcdef12")

    for platform in ("linux", "win32"):
        captured = {}

        def fake_run(*args, **kwargs):
            captured.update(kwargs)
            return types.SimpleNamespace(stdout="", stderr="", returncode=0)

        monkeypatch.setattr(main.subprocess, "run", fake_run)
        monkeypatch.setattr(main.sys, "platform", platform)
        main.tool_exec_command("true", timeout=5)
        assert "env" in captured, platform
        assert "OPENROUTER_API_KEY" not in captured["env"], platform
