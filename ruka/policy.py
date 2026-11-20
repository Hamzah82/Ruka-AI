"""Kebijakan izin eksekusi tool untuk Ruka AI.

Modul ini sengaja tidak bergantung pada `main.py` agar mudah diuji dan dipakai
ulang. Ia menjawab satu pertanyaan: untuk mode approval tertentu, apakah sebuah
tool/perintah boleh jalan, harus minta konfirmasi, atau diblokir?

Mode:
- ``auto`` : semua diizinkan (perilaku lama). Blocklist keras tetap berlaku.
- ``ask``  : operasi berisiko tinggi minta konfirmasi user; sisanya otomatis.
- ``plan`` : hanya operasi baca & perintah read-only yang diizinkan.
"""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass

MODES = ("ask", "auto", "plan")
DEFAULT_MODE = "ask"

# Tool yang mengubah filesystem / state.
MUTATING_TOOLS = frozenset(
    {
        "write_file",
        "edit_file",
        "delete_file",
        "copy_file",
        "move_file",
        "create_folder",
        "delete_folder",
        "apply_patch",
        "memory_write",
        "memory_delete",
        "gui_mouse",
        "gui_keyboard",
        "gui_window",
    }
)

# Tool yang selalu minta konfirmasi di mode `ask` (kerusakan sulit dibatalkan).
ASK_TOOLS = frozenset({"delete_file", "delete_folder", "move_file"})

# Perintah yang dianggap read-only & aman untuk mode `plan`.
SAFE_COMMANDS = frozenset(
    """
    ls cat head tail grep rg ag find wc sort uniq cut tr sed awk pwd echo printf
    date whoami id groups uname hostname df du free ps uptime stat file which
    whereis type tree jq diff cmp comm basename dirname realpath readlink test
    true false pytest
    """.split()
)

# Perintah yang berpotensi merusak / mengubah sistem.
DANGER_COMMANDS = frozenset(
    """
    rm rmdir mv shred dd mkfs mkfs.ext4 mkfs.xfs fdisk parted wipefs blkdiscard
    chmod chown chgrp kill pkill killall shutdown reboot poweroff halt init
    systemctl service mount umount crontab at sudo su passwd useradd userdel
    usermod groupadd groupdel iptables nft ufw firewall-cmd modprobe insmod
    rmmod sysctl docker podman kubectl terraform ansible ansible-playbook
    ssh scp rsync nc netcat socat telnet ftp sftp
    apt apt-get dnf yum pacman zypper snap flatpak
    eval source
    """.split()
)

# Package manager: subcommand menentukan risiko.
PKG_MANAGERS = frozenset(
    {"pip", "pip3", "npm", "npx", "yarn", "pnpm", "cargo", "gem", "go", "poetry", "uv"}
)
PKG_DANGER_SUBCOMMANDS = frozenset(
    {"install", "i", "add", "remove", "rm", "uninstall", "upgrade", "update", "publish", "link", "exec"}
)

# Subcommand git yang mengubah state.
DANGER_GIT_SUBCOMMANDS = frozenset(
    {"push", "reset", "clean", "checkout", "switch", "merge", "rebase", "pull", "stash", "apply"}
)
SAFE_GIT_SUBCOMMANDS = frozenset(
    {"status", "diff", "log", "show", "branch", "remote", "rev-parse", "ls-files", "blame", "grep", "describe"}
)

# Pattern path sensitif — akses ke sini patut dikonfirmasi.
SENSITIVE_PATH_RE = re.compile(
    r"(?:^|[\s/])(?:\.ssh|\.aws|\.gnupg|\.netrc|\.git-credentials|\.docker|\.kube)(?:$|[\s/])"
    r"|(?:^|[\s/])(?:id_rsa|id_ed25519|credentials|shadow|sudoers)(?:$|[\s/])"
    r"|(?:^|[\s/])\.env(?:$|[\s/])"
    r"|(?:^|[\s/])(?:/etc/shadow|/etc/sudoers|/root|/boot)(?:$|[\s/])"
    r"|/dev/(?:sd|nvme|mmcblk)"
    r"|/proc/[^\s]*/environ"
)

# Interpreter yang menerima kode inline (-c / -e).
INLINE_CODE_RE = re.compile(
    r"\b(?:python[0-9.]*|pypy[0-9.]*|perl|ruby|node|deno|bun|bash|sh|zsh|fish|ksh)\b"
    r"[^|;&\n]*\s(?:-c|-e|--eval|--command)\b"
)

REDIRECT_RE = re.compile(r"(>>?|\btee\b)\s*([^\s|;&]+)")
PIPE_TO_SHELL_RE = re.compile(r"\|\s*(?:sudo\s+)?(?:ba|z|k|fi)?sh\b")
PIPE_TO_SHELL_ALT_RE = re.compile(r"\|\s*(?:python[0-9.]*|perl|ruby|node)\b")
XARGS_DANGER_RE = re.compile(r"\bxargs\b[^|;&\n]*\b(?:rm|mv|dd|shred|chmod|chown|tee)\b")
ABS_PATH_RE = re.compile(r"(?:^|[\s='\"])(/[^\s'\";|&]+)")


@dataclass(frozen=True)
class Decision:
    """Hasil evaluasi kebijakan untuk satu pemanggilan tool."""

    allowed: bool
    needs_approval: bool
    reason: str = ""
    risk: str = "safe"


def _segments(command: str) -> list[str]:
    """Pecah command menjadi segmen per pipa/&&/;/newline (bukan pengganti parser)."""
    return [s for s in re.split(r"\|\||&&|;|\||\n", command) if s.strip()]


def _words(segment: str) -> list[str]:
    """Token pertama segmen, melewati assignment env (FOO=bar cmd ...)."""
    try:
        parts = shlex.split(segment, posix=True)
    except ValueError:
        parts = segment.split()
    while parts and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", parts[0]):
        parts = parts[1:]
    return parts


def _under(path: str, base: str) -> bool:
    """True bila path (setelah realpath) berada di bawah base."""
    if not base:
        return False
    try:
        return os.path.commonpath(
            [os.path.realpath(os.path.abspath(path)), os.path.realpath(os.path.abspath(base))]
        ) == os.path.realpath(os.path.abspath(base))
    except (ValueError, OSError):
        return False


def classify_command(command: str, workspace: str | None = None) -> tuple[str, list[str]]:
    """Klasifikasikan perintah: ``safe`` | ``moderate`` | ``danger``.

    Returns (level, reasons). Level keseluruhan adalah yang paling parah dari
    semua segmen. ``moderate`` berarti tidak jelas berbahaya, tetapi bukan
    read-only murni (mis. menjalankan script proyek).
    """
    cmd = (command or "").strip()
    if not cmd:
        return "safe", []

    workspace = workspace or os.getcwd()
    level = "safe"
    reasons: list[str] = []

    def bump(new_level: str, reason: str) -> None:
        nonlocal level
        order = {"safe": 0, "moderate": 1, "danger": 2}
        if order[new_level] > order[level]:
            level = new_level
        reasons.append(reason)

    if SENSITIVE_PATH_RE.search(cmd):
        bump("danger", "menyentuh file/path sensitif (kredensial/konfigurasi sistem)")

    if INLINE_CODE_RE.search(cmd):
        bump("danger", "menjalankan kode inline (-c/-e) yang bisa berbuat apa saja")

    if PIPE_TO_SHELL_RE.search(cmd) or PIPE_TO_SHELL_ALT_RE.search(cmd):
        bump("danger", "output dialirkan langsung ke interpreter/shell")

    if XARGS_DANGER_RE.search(cmd):
        bump("danger", "xargs meneruskan ke perintah destruktif")

    for m in REDIRECT_RE.finditer(cmd):
        target = m.group(2)
        if target.startswith(("/", "~")):
            if not _under(os.path.expanduser(target), workspace):
                bump("danger", f"menulis ke path di luar workspace ({target})")
            else:
                bump("moderate", f"menulis file ({target})")
        elif target in ("/dev/null", "&1", "&2", "1", "2"):
            continue
        else:
            bump("moderate", f"menulis file ({target})")

    for segment in _segments(cmd):
        words = _words(segment)
        if not words:
            continue
        base = os.path.basename(words[0])

        if base in DANGER_COMMANDS:
            # `find ... -delete` / `find ... -exec` juga destruktif.
            if base == "find" and re.search(r"\s-(delete|exec)\b", segment):
                bump("danger", "find dengan -delete/-exec")
            else:
                bump("danger", f"perintah '{base}' dapat mengubah sistem")
            continue

        if base in PKG_MANAGERS:
            sub = words[1] if len(words) > 1 else ""
            if sub in PKG_DANGER_SUBCOMMANDS:
                bump("danger", f"{base} {sub} memasang/mengubah paket")
            else:
                bump("moderate", f"{base} {sub or 'tanpa subcommand'} menjalankan tool pihak ketiga")
            continue

        if base == "git" and len(words) > 1:
            sub = words[1]
            if sub in DANGER_GIT_SUBCOMMANDS:
                # `git branch` tanpa argumen = read-only; dengan argumen = membuat branch.
                bump("danger", f"git {sub} mengubah state repository")
            elif sub in SAFE_GIT_SUBCOMMANDS:
                continue
            else:
                bump("moderate", f"git {sub} tidak dikenali sebagai read-only")
            continue

        if base in ("curl", "wget"):
            bump("moderate", f"{base} mengakses jaringan")
            continue

        if base in ("find", "sed"):
            if base == "find" and re.search(r"\s-(delete|exec)\b", segment):
                bump("danger", "find dengan -delete/-exec")
            elif base == "sed" and re.search(r"(^|\s)-i\b", segment):
                bump("danger", "sed -i menimpa file")
            else:
                continue
            continue

        if base in ("kill", "pkill", "killall"):
            bump("danger", f"{base} mematikan proses")
            continue

        # Perintah dengan path absolut di luar workspace → minimal moderate.
        for m in ABS_PATH_RE.finditer(segment):
            path = m.group(1)
            if path.startswith(("/dev/", "/proc/", "/sys/")):
                continue
            if not _under(path, workspace):
                bump("moderate", f"menyentuh path di luar workspace ({path})")
                break

        if base in SAFE_COMMANDS:
            continue

        # Tidak dikenal → moderate (bukan read-only murni).
        bump("moderate", f"perintah '{base}' tidak terdaftar sebagai read-only")

    # Deduplikasi alasan sambil mempertahankan urutan.
    seen = set()
    unique = [r for r in reasons if not (r in seen or seen.add(r))]
    return level, unique


def evaluate_tool(
    tool: str,
    arguments: dict | None,
    workspace: str | None = None,
    mode: str = DEFAULT_MODE,
) -> Decision:
    """Tentukan izin untuk satu pemanggilan tool pada mode approval tertentu."""
    arguments = arguments or {}
    mode = mode if mode in MODES else DEFAULT_MODE

    if tool == "exec_command":
        command = str(arguments.get("command", ""))
        level, reasons = classify_command(command, workspace)
        reason_text = "; ".join(reasons[:3])
        if mode == "plan" and level != "safe":
            return Decision(False, False, f"Mode plan: perintah tidak read-only ({reason_text}).", level)
        if mode == "ask" and level == "danger":
            return Decision(True, True, reason_text, level)
        return Decision(True, False, reason_text, level)

    if tool in MUTATING_TOOLS:
        if mode == "plan":
            return Decision(False, False, f"Mode plan: tool '{tool}' mengubah state.", "moderate")
        if mode == "ask" and tool in ASK_TOOLS:
            return Decision(True, True, f"tool '{tool}' bersifat destruktif", "danger")
        return Decision(True, False, "", "moderate")

    return Decision(True, False, "", "safe")
