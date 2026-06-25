"""Test _safe_path: anti path-traversal via realpath + commonpath.

Semua headless: tanpa jaringan/TTY. Memonkeypatch config.BASE_DIR & SCRIPT_DIR
ke folder tmp agar terisolasi.
"""
import os
import pytest

import config
import main


def _real(p):
    return os.path.realpath(str(p))


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """BASE_DIR = tmp/proj, SCRIPT_DIR = tmp/script (terpisah & tak ber-prefix)."""
    base = tmp_path / "proj"
    base.mkdir()
    script = tmp_path / "script"
    script.mkdir()
    monkeypatch.setattr(config, "BASE_DIR", str(base))
    monkeypatch.setattr(config, "SCRIPT_DIR", str(script))
    return base, script


def test_relative_inside_allowed(workspace):
    base, _ = workspace
    assert main._safe_path("catatan.txt") == os.path.join(_real(base), "catatan.txt")


def test_absolute_inside_allowed(workspace):
    base, _ = workspace
    assert main._safe_path(str(base / "x.txt")) is not None


def test_sibling_prefix_blocked(tmp_path, monkeypatch):
    base = tmp_path / "proj"
    base.mkdir()
    sibling = tmp_path / "proj-rahasia"
    sibling.mkdir()
    monkeypatch.setattr(config, "BASE_DIR", str(base))
    monkeypatch.setattr(config, "SCRIPT_DIR", str(tmp_path / "nope"))
    # bug startswith lama: /a/proj-rahasia keliru lolos. Sekarang harus None.
    assert main._safe_path(str(sibling / "x.txt")) is None


def test_dotdot_blocked(workspace):
    assert main._safe_path("../../etc/passwd") is None


def test_new_nested_file_allowed(workspace):
    base, _ = workspace
    got = main._safe_path("subdir/baru.txt")
    assert got is not None
    assert os.path.commonpath([_real(base), got]) == _real(base)


def test_path_equals_base(workspace):
    base, _ = workspace
    assert main._safe_path(".") is not None
    assert main._safe_path(str(base)) is not None


def test_script_dir_allowed(workspace):
    _, script = workspace
    (script / "SKILL").mkdir()
    assert main._safe_path(str(script / "SKILL" / "skills.md")) is not None


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_symlink_parent_escape_blocked(tmp_path, monkeypatch):
    base = tmp_path / "proj"
    base.mkdir()
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "passwd.txt").write_text("rahasia")
    try:
        os.symlink(str(secret), str(base / "link"))
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlink")
    monkeypatch.setattr(config, "BASE_DIR", str(base))
    monkeypatch.setattr(config, "SCRIPT_DIR", str(tmp_path / "nope"))
    assert main._safe_path("link/passwd.txt") is None


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_symlink_leaf_escape_blocked(tmp_path, monkeypatch):
    base = tmp_path / "proj"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("rahasia")
    try:
        os.symlink(str(outside), str(base / "evil"))
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlink")
    monkeypatch.setattr(config, "BASE_DIR", str(base))
    monkeypatch.setattr(config, "SCRIPT_DIR", str(tmp_path / "nope"))
    assert main._safe_path("evil") is None


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlink unsupported")
def test_base_under_symlink_allowed(tmp_path, monkeypatch):
    realbase = tmp_path / "realbase"
    realbase.mkdir()
    linkbase = tmp_path / "linkbase"
    try:
        os.symlink(str(realbase), str(linkbase))
    except (OSError, NotImplementedError):
        pytest.skip("cannot create symlink")
    monkeypatch.setattr(config, "BASE_DIR", str(linkbase))
    monkeypatch.setattr(config, "SCRIPT_DIR", str(tmp_path / "nope"))
    # base sendiri di bawah symlink: akses sah harus tetap lolos (cegah regresi).
    assert main._safe_path("a.txt") is not None


def test_nullbyte_failsafe(workspace):
    assert main._safe_path("catatan\x00.txt") is None


def test_commonpath_valueerror_failsafe(workspace, monkeypatch):
    def boom(_):
        raise ValueError("boom")
    monkeypatch.setattr(os.path, "commonpath", boom)
    assert main._safe_path("catatan.txt") is None


def test_regression_callers(workspace):
    main.tool_write_file("reg.txt", "halo")
    assert "halo" in main.tool_read_file("reg.txt")
    assert "ditolak" in main.tool_read_file("../../etc/passwd").lower()
