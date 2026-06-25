"""Test penulisan sesi atomik (crash-safe) + backup ringan.

Headless: memonkeypatch config.SESSIONS_DIR ke tmp_path.
"""
import json
import os

import pytest

import config
import main


@pytest.fixture
def sessdir(tmp_path, monkeypatch):
    d = tmp_path / "sessions"
    d.mkdir()
    monkeypatch.setattr(config, "SESSIONS_DIR", str(d))
    return d


def _names(sessions):
    return {s["name"] for s in sessions}


def test_save_creates_valid_json(sessdir):
    main.save_session("s1", [{"role": "user", "content": "hai"}])
    msgs, meta = main.load_session("s1")
    assert msgs == [{"role": "user", "content": "hai"}]
    assert meta["message_count"] == 1


def test_save_no_tmp_left(sessdir):
    main.save_session("s1", [{"role": "user", "content": "x"}])
    assert not any(f.startswith(".tmp-") for f in os.listdir(sessdir))


def test_save_preserves_created_at(sessdir):
    main.save_session("s1", [{"role": "user", "content": "a"}])
    _, meta1 = main.load_session("s1")
    main.save_session("s1", [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])
    _, meta2 = main.load_session("s1")
    assert meta1["created_at"] == meta2["created_at"]


def test_save_creates_backup_of_old(sessdir):
    main.save_session("s1", [{"role": "user", "content": "v1"}])
    main.save_session("s1", [{"role": "user", "content": "v2"}])
    bak = sessdir / "backups" / "s1.json.bak"
    assert bak.exists()
    assert json.loads(bak.read_text())["messages"] == [{"role": "user", "content": "v1"}]


def test_save_failure_keeps_old_intact(sessdir, monkeypatch):
    main.save_session("s1", [{"role": "user", "content": "v1"}])

    def boom(*a, **k):
        raise OSError("disk penuh")

    with monkeypatch.context() as m:
        m.setattr(os, "replace", boom)
        res = main.save_session("s1", [{"role": "user", "content": "v2"}])
        assert "Error" in res
    # os.replace dipulihkan; SESSIONS_DIR (dari fixture) tetap ter-patch.
    msgs, _ = main.load_session("s1")
    assert msgs == [{"role": "user", "content": "v1"}]  # file lama utuh


def test_save_failure_cleans_tmp(sessdir, monkeypatch):
    main.save_session("s1", [{"role": "user", "content": "v1"}])
    with monkeypatch.context() as m:
        m.setattr(os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
        main.save_session("s1", [{"role": "user", "content": "v2"}])
    assert not any(f.startswith(".tmp-") for f in os.listdir(sessdir))


def test_orphan_tmp_swept_and_not_listed(sessdir):
    # Bahkan orphan ber-suffix .json (gaya lama) ber-prefix .tmp- harus disapu.
    (sessdir / ".tmp-leftover.json").write_text("{}")
    sessions = main.list_sessions()
    assert "leftover" not in _names(sessions)
    assert not (sessdir / ".tmp-leftover.json").exists()


def test_backups_not_listed_as_session(sessdir):
    main.save_session("s1", [{"role": "user", "content": "v1"}])
    main.save_session("s1", [{"role": "user", "content": "v2"}])
    sessions = main.list_sessions()
    assert _names(sessions) == {"s1"}


def test_fsync_dir_failure_nonfatal(sessdir, monkeypatch):
    real_open = os.open

    def fake_open(path, *a, **k):
        if os.path.isdir(path):
            raise OSError("simulasi: fsync direktori tak didukung")
        return real_open(path, *a, **k)

    with monkeypatch.context() as m:
        m.setattr(os, "open", fake_open)
        res = main.save_session("s1", [{"role": "user", "content": "x"}])
        assert "berhasil" in res
    msgs, _ = main.load_session("s1")
    assert msgs == [{"role": "user", "content": "x"}]


def test_rename_atomic_and_old_removed(sessdir):
    main.save_session("old", [{"role": "user", "content": "x"}])
    main.rename_session("old", "baru")
    msgs, meta = main.load_session("baru")
    assert meta["name"] == "baru" and msgs == [{"role": "user", "content": "x"}]
    assert not os.path.exists(main._session_path("old"))


def test_rename_failure_keeps_old(sessdir, monkeypatch):
    main.save_session("old", [{"role": "user", "content": "x"}])
    with monkeypatch.context() as m:
        m.setattr(os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
        res = main.rename_session("old", "baru")
        assert "Error" in res
    assert os.path.exists(main._session_path("old"))
    assert not os.path.exists(main._session_path("baru"))


def test_rename_target_exists_guard(sessdir):
    main.save_session("old", [{"role": "user", "content": "x"}])
    main.save_session("baru", [{"role": "user", "content": "y"}])
    res = main.rename_session("old", "baru")
    assert "sudah ada" in res
    assert os.path.exists(main._session_path("old"))
    assert os.path.exists(main._session_path("baru"))
