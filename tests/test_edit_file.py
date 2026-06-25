"""Test edit_file: replace menolak teks ambigu + dukungan replace_all.

Headless: monkeypatch config.BASE_DIR ke tmp_path (pola test_session_atomic).
"""
import pytest

import config
import main


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", str(tmp_path))
    return tmp_path


def test_replace_unique_ok(workdir):
    (workdir / "f.txt").write_text("a=1\nb=2\n")
    res = main.tool_edit_file("f.txt", "replace", "a=99", old_text="a=1")
    assert "berhasil diedit" in res
    assert (workdir / "f.txt").read_text() == "a=99\nb=2\n"


def test_replace_ambiguous_rejected_and_file_unchanged(workdir):
    (workdir / "f.txt").write_text("x\nx\n")
    res = main.tool_edit_file("f.txt", "replace", "y", old_text="x")
    assert "ambigu" in res and "replace_all" in res and "2x" in res
    assert (workdir / "f.txt").read_text() == "x\nx\n"  # tak ada penulisan senyap


def test_replace_all_replaces_every_occurrence(workdir):
    (workdir / "f.txt").write_text("x\nx\nx\n")
    res = main.tool_edit_file("f.txt", "replace", "y", old_text="x", replace_all=True)
    content = (workdir / "f.txt").read_text()
    assert content.count("y") == 3 and content.count("x") == 0
    assert "replace_all" in res and "3" in res


def test_replace_not_found_error(workdir):
    (workdir / "f.txt").write_text("abc")
    res = main.tool_edit_file("f.txt", "replace", "y", old_text="zzz")
    assert "tidak ditemukan" in res
    assert (workdir / "f.txt").read_text() == "abc"


def test_replace_missing_old_text_error(workdir):
    (workdir / "f.txt").write_text("abc")
    res = main.tool_edit_file("f.txt", "replace", "y", old_text=None)
    assert "Parameter 'old_text' diperlukan" in res


def test_replace_empty_old_text_rejected(workdir):
    (workdir / "f.txt").write_text("abc")
    res = main.tool_edit_file("f.txt", "replace", "y", old_text="", replace_all=True)
    assert "tidak boleh string kosong" in res
    assert (workdir / "f.txt").read_text() == "abc"


def test_replace_all_true_with_single_occurrence(workdir):
    (workdir / "f.txt").write_text("solo")
    res = main.tool_edit_file("f.txt", "replace", "duo", old_text="solo", replace_all=True)
    assert "berhasil diedit" in res and "replace_all" not in res  # count==1 → format biasa
    assert (workdir / "f.txt").read_text() == "duo"


def test_dispatcher_default_replace_all(workdir):
    (workdir / "f.txt").write_text("x\n")
    ok = main.execute_tool("edit_file", {"filename": "f.txt", "operation": "replace", "old_text": "x", "new_text": "y"})
    assert "berhasil diedit" in ok
    (workdir / "g.txt").write_text("x\nx\n")
    amb = main.execute_tool("edit_file", {"filename": "g.txt", "operation": "replace", "old_text": "x", "new_text": "y"})
    assert "ambigu" in amb


def test_dispatcher_replace_all_true(workdir):
    (workdir / "f.txt").write_text("x\nx\n")
    res = main.execute_tool("edit_file", {"filename": "f.txt", "operation": "replace", "old_text": "x", "new_text": "y", "replace_all": True})
    assert "replace_all" in res
    assert (workdir / "f.txt").read_text() == "y\ny\n"


def test_append_prepend_unaffected(workdir):
    (workdir / "f.txt").write_text("mid")
    main.tool_edit_file("f.txt", "append", "-end", replace_all=True)
    main.tool_edit_file("f.txt", "prepend", "start-", replace_all=True)
    assert (workdir / "f.txt").read_text() == "start-mid-end"


def test_schema_has_replace_all_optional():
    fn = next(t["function"] for t in main.TOOLS if t["function"]["name"] == "edit_file")
    params = fn["parameters"]
    assert "replace_all" in params["properties"]
    assert "replace_all" not in params["required"]
