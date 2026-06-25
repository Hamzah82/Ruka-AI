"""Test cap output exec_command: stdout/stderr dipotong, exit code tetap utuh.

Headless tapi butuh shell unix → skip di Windows.
"""
import sys

import pytest

import config
import main


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BASE_DIR", str(tmp_path))
    return tmp_path


@pytest.mark.skipif(sys.platform == "win32", reason="butuh shell unix")
def test_exec_stdout_capped(workdir, monkeypatch):
    monkeypatch.setattr(config, "MAX_EXEC_OUTPUT_CHARS", 100)
    out = main.tool_exec_command("python3 -c \"print('x'*5000)\"", timeout=20)
    assert "dipotong" in out
    assert len(out) < 1000  # jauh di bawah 5000 char asli


@pytest.mark.skipif(sys.platform == "win32", reason="butuh shell unix")
def test_exec_exit_code_preserved_after_cap(workdir, monkeypatch):
    monkeypatch.setattr(config, "MAX_EXEC_OUTPUT_CHARS", 100)
    out = main.tool_exec_command(
        "python3 -c \"import sys; sys.stderr.write('e'*5000); sys.exit(3)\"", timeout=20
    )
    assert "[Exit code: 3]" in out  # tak ikut terpotong
    assert "dipotong" in out


@pytest.mark.skipif(sys.platform == "win32", reason="butuh shell unix")
def test_exec_small_output_not_capped(workdir):
    out = main.tool_exec_command("echo halo", timeout=10)
    assert "halo" in out and "dipotong" not in out
