"""Aturan workspace & ignore patterns untuk Ruka AI.

- ``RUKA.md`` / ``AGENTS.md`` / ``.ruka/rules.md`` di workspace dibaca otomatis
  dan disisipkan ke system prompt sebagai aturan proyek.
- ``.rukaignore`` berisi pola (satu per baris) yang dilewati tool grep/glob.
"""
from __future__ import annotations

import fnmatch
import os

RULES_FILES = ("RUKA.md", "AGENTS.md", os.path.join(".ruka", "rules.md"))
MAX_RULES_BYTES = 32_000

DEFAULT_IGNORE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "dist",
        "build",
        ".ruka",
    }
)


def load_workspace_rules(base_dir: str) -> str:
    """Baca file aturan pertama yang ditemukan di workspace (maks 32 KB)."""
    if not base_dir:
        return ""
    for rel in RULES_FILES:
        path = os.path.join(base_dir, rel)
        try:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_RULES_BYTES + 1)
        except OSError:
            continue
        if len(content) > MAX_RULES_BYTES:
            content = content[:MAX_RULES_BYTES] + "\n…[aturan dipotong: melebihi 32 KB]"
        return content.strip()
    return ""


def build_rules_section(base_dir: str) -> str:
    """Section siap-sisip untuk system prompt (kosong bila tidak ada aturan)."""
    content = load_workspace_rules(base_dir)
    if not content:
        return ""
    return (
        "\n\n══════════════════════════════════════════════════════════════\n"
        "📌 ATURAN WORKSPACE (dari RUKA.md/AGENTS.md — WAJIB DIPATUHI):\n"
        "══════════════════════════════════════════════════════════════\n"
        + content
        + "\n══════════════════════════════════════════════════════════════\n"
    )


def load_ignore_patterns(base_dir: str) -> list[str]:
    """Baca pola .rukaignore (komentar ``#`` dan baris kosong diabaikan)."""
    patterns: list[str] = []
    path = os.path.join(base_dir or "", ".rukaignore")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
    except OSError:
        pass
    return patterns


def is_ignored(rel_path: str, patterns: list[str] | None = None) -> bool:
    """True bila path relatif harus dilewati tool pencarian."""
    rel_path = rel_path.replace(os.sep, "/")
    while rel_path.startswith("./"):
        rel_path = rel_path[2:]
    parts = rel_path.split("/")
    if any(part in DEFAULT_IGNORE_DIRS for part in parts[:-1]):
        return True
    for pattern in patterns or []:
        pat = pattern.strip().replace(os.sep, "/")
        if not pat:
            continue
        if pat.endswith("/"):
            prefix = pat.rstrip("/")
            if rel_path == prefix or rel_path.startswith(prefix + "/"):
                return True
            continue
        if fnmatch.fnmatch(rel_path, pat) or fnmatch.fnmatch(parts[-1], pat):
            return True
        # Pola direktori tanpa slash, mis. "vendor" → cocokkan komponen.
        if "/" not in pat and pat in parts[:-1]:
            return True
    return False
