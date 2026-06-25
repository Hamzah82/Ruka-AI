"""Test read_file: offset/limit per-baris, penomoran, cap, deteksi biner,
plus helper _truncate_text & _looks_binary. Semua headless.
"""
import pytest

import config
import main


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", str(tmp_path))
    return tmp_path


# ---- helper _truncate_text ----
def test_truncate_under_cap():
    out, tr = main._truncate_text("abc", 10)
    assert out == "abc" and tr is False


def test_truncate_over_cap_chars():
    out, tr = main._truncate_text("abcdefghij", 5)
    assert out == "abcde" and tr is True


def test_truncate_at_line_boundary():
    out, tr = main._truncate_text("aa\nbb\ncc\n", 6, at_line_boundary=True)
    assert out == "aa\nbb" and tr is True


def test_truncate_utf8_no_split():
    out, tr = main._truncate_text("🐢" * 10, 5)
    assert out == "🐢" * 5 and tr is True  # tiap 🐢 = 1 char Python → tak terbelah


# ---- helper _looks_binary ----
def test_looks_binary_text_utf8(workdir):
    p = workdir / "t.txt"
    p.write_text("halo 🐢 café dunia\n", encoding="utf-8")
    assert main._looks_binary(str(p)) is False


def test_looks_binary_nul(workdir):
    p = workdir / "b.bin"
    p.write_bytes(b"abc\x00\x01\x02def")
    assert main._looks_binary(str(p)) is True


# ---- read_file ----
def test_read_backward_compat_small(workdir):
    (workdir / "f.txt").write_text("a\nb\nc\n")
    assert main.tool_read_file("f.txt") == "a\nb\nc\n"  # apa adanya, tanpa penanda


def test_read_offset_limit_1based(workdir):
    (workdir / "f.txt").write_text("l1\nl2\nl3\nl4\nl5\n")
    assert main.tool_read_file("f.txt", offset=3, limit=2) == "l3\nl4"


def test_read_line_numbers_real_position(workdir):
    (workdir / "f.txt").write_text("l1\nl2\nl3\nl4\nl5\n")
    out = main.tool_read_file("f.txt", offset=3, limit=2, line_numbers=True)
    rows = out.split("\n")
    assert rows[0].strip().startswith("3") and "l3" in rows[0]
    assert rows[1].strip().startswith("4") and "l4" in rows[1]


def test_read_utf8_not_binary(workdir):
    (workdir / "u.txt").write_text("emoji 🐢 café ☕ aksara\n", encoding="utf-8")
    out = main.tool_read_file("u.txt")
    assert "🐢" in out and "café" in out


def test_read_binary_rejected(workdir):
    (workdir / "b.bin").write_bytes(b"\x00\x01\x02BINARYDATA\x00")
    out = main.tool_read_file("b.bin")
    assert "biner" in out.lower()
    assert "BINARYDATA" not in out  # tidak dump byte mentah


def test_read_full_cap_line_boundary(workdir, monkeypatch):
    monkeypatch.setattr(config, "MAX_READ_LINES", 3)
    (workdir / "big.txt").write_text("".join(f"line{i}\n" for i in range(1, 11)))
    out = main.tool_read_file("big.txt")
    body = out.split("[")[0]
    assert "line1" in body and "line3" in body and "line4" not in body
    assert "dipotong" in out and "offset=4" in out


def test_read_offset_out_of_range(workdir):
    (workdir / "f.txt").write_text("a\nb\n")
    assert "di luar rentang" in main.tool_read_file("f.txt", offset=99)


def test_dispatcher_read_params(workdir):
    (workdir / "f.txt").write_text("a\nb\nc\n")
    assert main.execute_tool("read_file", {"filename": "f.txt"}) == "a\nb\nc\n"
    out = main.execute_tool("read_file", {"filename": "f.txt", "offset": 2, "limit": 1, "line_numbers": True})
    assert "b" in out and out.strip().startswith("2")


def test_schema_read_file_optional_params():
    fn = next(t["function"] for t in main.TOOLS if t["function"]["name"] == "read_file")
    props = fn["parameters"]["properties"]
    assert {"offset", "limit", "line_numbers"} <= set(props)
    assert fn["parameters"]["required"] == ["filename"]
