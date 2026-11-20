"""Tool pencarian & patch yang lebih hemat token daripada shell.

- ``grep_files``  : cari regex di isi file workspace.
- ``glob_files``  : cari path berdasarkan pola glob.
- ``apply_patch`` : terapkan unified diff (multi-file) dengan validasi ketat.
- ``fuzzy_replace``: fallback edit ketika old_text tidak cocok persis karena
  perbedaan indentasi/spasi.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

from ruka.rules import is_ignored, load_ignore_patterns

MAX_GREP_FILE_BYTES = 2 * 1024 * 1024
MAX_LINE_CHARS = 400


class PatchError(ValueError):
    """Patch tidak valid / konteks tidak cocok."""


def _resolve(base_dir: str, rel: str) -> Path:
    """Resolve path relatif dan pastikan tidak keluar dari workspace."""
    rel = (rel or "").strip().replace("\\", "/")
    if rel.startswith("/"):
        raise ValueError("path absolut tidak diizinkan")
    if any(part == ".." for part in Path(rel).parts):
        raise ValueError("path traversal tidak diizinkan")
    base = Path(base_dir).resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError(f"path '{rel}' berada di luar workspace")
    return target


def _iter_files(base: Path, start: Path, patterns: list[str]):
    if not start.exists():
        return
    if start.is_file():
        yield start
        return
    for root, dirs, files in os.walk(start):
        rel_root = os.path.relpath(root, base).replace(os.sep, "/")
        dirs[:] = [
            d for d in dirs
            if not is_ignored(f"{rel_root}/{d}".lstrip("./"), patterns)
        ]
        for name in files:
            rel = f"{rel_root}/{name}".lstrip("./")
            if is_ignored(rel, patterns):
                continue
            yield Path(root) / name


def grep_files(
    pattern: str,
    base_dir: str,
    path: str = ".",
    glob: str | None = None,
    case_sensitive: bool = False,
    max_results: int = 100,
) -> str:
    """Cari regex di isi file. Returns baris ``path:line: isi``."""
    if not pattern:
        return "Error: pattern kosong."
    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        rx = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: regex tidak valid: {e}"

    base = Path(base_dir).resolve()
    try:
        start = _resolve(base_dir, path)
    except ValueError as e:
        return f"Error: {e}"
    patterns = load_ignore_patterns(base_dir)
    matches: list[str] = []
    scanned = 0

    for file_path in _iter_files(base, start, patterns):
        try:
            rel = file_path.relative_to(base).as_posix()
        except ValueError:
            continue
        if glob and not (fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(file_path.name, glob)):
            continue
        try:
            if file_path.stat().st_size > MAX_GREP_FILE_BYTES:
                continue
            raw = file_path.read_bytes()[:4096]
            if b"\x00" in raw:
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                line = line.strip()
                if len(line) > MAX_LINE_CHARS:
                    line = line[:MAX_LINE_CHARS] + "…"
                matches.append(f"{rel}:{lineno}: {line}")
                if len(matches) >= max_results:
                    break
        if len(matches) >= max_results:
            break

    if not matches:
        return f"Tidak ada hasil untuk '{pattern}' ({scanned} file dipindai)."
    suffix = f"\n[...dibatasi {max_results} hasil]" if len(matches) >= max_results else ""
    return "\n".join(matches) + suffix


def glob_files(pattern: str, base_dir: str, path: str = ".", max_results: int = 200) -> str:
    """Cari path dengan pola glob (mis. ``**/*.py``)."""
    if not pattern:
        return "Error: pattern kosong."
    base = Path(base_dir).resolve()
    try:
        start = _resolve(base_dir, path)
    except ValueError as e:
        return f"Error: {e}"
    patterns = load_ignore_patterns(base_dir)
    results: list[str] = []

    if pattern.startswith("/"):
        return "Error: pola absolut tidak diizinkan; gunakan path relatif terhadap workspace."

    # Path.glob mendukung '**'. Untuk pola absolut/traversal, _resolve sudah menolak.
    try:
        candidates = sorted(start.glob(pattern))
    except (ValueError, OSError, NotImplementedError) as e:
        return f"Error: pola glob tidak valid: {e}"

    for item in candidates:
        try:
            rel = item.relative_to(base).as_posix()
        except ValueError:
            continue
        if is_ignored(rel, patterns):
            continue
        results.append(rel + ("/" if item.is_dir() else ""))
        if len(results) >= max_results:
            break

    if not results:
        return f"Tidak ada path yang cocok dengan '{pattern}'."
    suffix = f"\n[...dibatasi {max_results} hasil]" if len(results) >= max_results else ""
    return "\n".join(results) + suffix


# ── apply_patch (unified diff) ────────────────────────────────────
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _clean_header(header: str) -> str:
    header = header.split("\t")[0].strip()
    if header.startswith(("a/", "b/")):
        header = header[2:]
    return header


def _parse_patch(patch_text: str):
    lines = patch_text.splitlines()
    i = 0
    files = []
    while i < len(lines):
        if not lines[i].startswith("--- "):
            i += 1
            continue
        old_header = _clean_header(lines[i][4:])
        i += 1
        if i >= len(lines) or not lines[i].startswith("+++ "):
            raise PatchError("header '+++' tidak ditemukan setelah '---'")
        new_header = _clean_header(lines[i][4:])
        i += 1
        hunks = []
        while i < len(lines) and lines[i].startswith("@@"):
            m = _HUNK_RE.match(lines[i])
            if not m:
                raise PatchError(f"header hunk tidak valid: {lines[i]!r}")
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) is not None else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) is not None else 1
            i += 1
            body = []
            while i < len(lines):
                line = lines[i]
                if line.startswith(("@@", "--- ")):
                    break
                if line.startswith("\\"):
                    i += 1
                    continue
                if not line:
                    # Baris kosong di patch = akhir hunk (context selalu berawalan spasi).
                    break
                if line[0] not in (" ", "+", "-"):
                    raise PatchError(f"baris hunk tidak valid: {line!r}")
                body.append(line)
                i += 1
            hunks.append((old_start, old_count, new_start, new_count, body))
        if not hunks:
            raise PatchError(f"file '{new_header}' tidak punya hunk")
        files.append((old_header, new_header, hunks))
    if not files:
        raise PatchError("tidak ada file dalam patch (format unified diff)")
    return files


def _apply_hunks(old_text: str, hunks) -> str:
    old_lines = old_text.splitlines()
    out: list[str] = []
    cursor = 0
    for old_start, old_count, _new_start, _new_count, body in hunks:
        start = old_start - 1 if old_count > 0 else old_start
        if start < cursor or start > len(old_lines):
            raise PatchError(
                f"hunk di baris {old_start} tumpang tindih / di luar file "
                f"({len(old_lines)} baris)"
            )
        out.extend(old_lines[cursor:start])
        idx = start
        for line in body:
            tag = line[0]
            text = line[1:]
            if tag == " ":
                if idx >= len(old_lines) or old_lines[idx] != text:
                    raise PatchError(
                        f"konteks tidak cocok di baris {idx + 1}: "
                        f"diharapkan {text!r}, ditemukan "
                        f"{old_lines[idx]!r}" if idx < len(old_lines) else
                        f"konteks melewati akhir file di baris {idx + 1}"
                    )
                out.append(text)
                idx += 1
            elif tag == "-":
                if idx >= len(old_lines) or old_lines[idx] != text:
                    raise PatchError(
                        f"baris yang dihapus tidak cocok di baris {idx + 1}: "
                        f"diharapkan {text!r}, ditemukan "
                        f"{old_lines[idx]!r}" if idx < len(old_lines) else
                        f"penghapusan melewati akhir file di baris {idx + 1}"
                    )
                idx += 1
            elif tag == "+":
                out.append(text)
        cursor = idx
    out.extend(old_lines[cursor:])
    if not out:
        return ""
    # File baru selalu ditutup newline; file lama mengikuti konvensi aslinya.
    trailing = "\n" if (not old_text or old_text.endswith("\n")) else ""
    return "\n".join(out) + trailing


def apply_patch(patch_text: str, base_dir: str) -> str:
    """Terapkan unified diff ke file di workspace. Returns ringkasan."""
    if not (patch_text or "").strip():
        return "Error: patch kosong."
    files = _parse_patch(patch_text)
    base = Path(base_dir).resolve()
    results: list[str] = []

    for old_header, new_header, hunks in files:
        creating = old_header == "/dev/null"
        deleting = new_header == "/dev/null"
        target_header = new_header if not deleting else old_header
        try:
            target = _resolve(base_dir, target_header)
        except ValueError as e:
            raise PatchError(str(e))

        if creating:
            old_text = ""
        else:
            if not target.exists() or not target.is_file():
                raise PatchError(f"file '{target_header}' tidak ditemukan")
            old_text = target.read_text(encoding="utf-8", errors="replace")

        new_text = _apply_hunks(old_text, hunks)

        if deleting:
            target.unlink()
            results.append(f"D {target.relative_to(base).as_posix()}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".ruka-patch.tmp")
        tmp.write_text(new_text, encoding="utf-8")
        os.replace(tmp, target)
        rel = target.relative_to(base).as_posix()
        results.append(f"{'A' if creating else 'M'} {rel}")

    return "Patch diterapkan:\n" + "\n".join(results)


# ── fuzzy edit ────────────────────────────────────────────────────
def fuzzy_replace(content: str, old_text: str, new_text: str, replace_all: bool = False):
    """Cocokkan old_text dengan mengabaikan spasi di awal/akhir tiap baris.

    Returns: (new_content | None, jumlah_match). ``None`` bila tidak ada /
    ambigu (tanpa replace_all).
    """
    old_lines = [line.strip() for line in old_text.splitlines() if line.strip()]
    if not old_lines:
        return None, 0
    lines = content.splitlines()
    matches: list[int] = []
    for i in range(0, len(lines) - len(old_lines) + 1):
        if all(lines[i + j].strip() == old_lines[j] for j in range(len(old_lines))):
            matches.append(i)
    if not matches:
        return None, 0
    if len(matches) > 1 and not replace_all:
        return None, len(matches)

    selected = list(reversed(matches if replace_all else matches[:1]))
    new_lines = new_text.splitlines()
    for i in selected:
        replace_from = i
        replace_to = i + len(old_lines)
        lines[replace_from:replace_to] = new_lines

    result = "\n".join(lines)
    if content.endswith("\n"):
        result += "\n"
    return result, len(matches)
