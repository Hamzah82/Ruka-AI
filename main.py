"""
Ruka AI - OpenRouter Chat Client dengan Tool Use (File, Folder & Terminal Command)
AI Kura-Kura yang dapat membaca, menulis, menghapus, menyalin, memindahkan file,
mengelola folder, serta menjalankan perintah terminal (bash) di local device.
Output AI diformat dari markdown ke styled terminal text.

Session Management:
  python main.py              → session baru dengan nama timestamp
  python main.py <namaSesi>   → load atau buat sesi dengan nama tertentu
  python main.py listSessions → tampilkan daftar semua sesi (CLI)
  python main.py deleteSession <nama> → hapus sesi tertentu (CLI)
  python main.py renameSession <lama> <baru> → rename sesi (CLI)
  python main.py clearSessions → hapus semua session tanpa nama (CLI)
  python main.py searchSessions <keyword> → cari session berdasarkan nama (CLI)
  /sessions                  → tampilkan daftar semua sesi (slash command)
  /new                       → mulai sesi baru (slash command)
  /history                   → tampilkan riwayat chat sesi saat ini (slash command)
  /delete-session <nama>     → hapus sesi tertentu (slash command)
  /rename-session <lama> <baru> → rename sesi (slash command)
"""

import os
import re
import sys
import json
import shutil
import stat
import time
import random
import subprocess
import threading
import queue
import unicodedata
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# KONFIGURASI — dimuat dari config.py
# ============================================================
from config import (
    OPENROUTER_API_KEY,
    MODEL,
    API_URL,
    HEADERS,
    BASE_DIR,
    SESSIONS_DIR,
    DEFAULT_CMD_TIMEOUT,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    BLOCKED_COMMANDS,
)

# ============================================================
# INTERRUPT MECHANISM — queue-based, single input source
# ============================================================
_input_queue = queue.Queue()
_interrupt_event = threading.Event()
_input_thread = None
_input_running = threading.Event()


def _input_reader():
    """
    Satu-satunya thread yang membaca dari stdin.
    Semua input user masuk ke _input_queue.
    """
    while _input_running.is_set():
        try:
            line = sys.stdin.readline()
            if not line:  # EOF
                _input_queue.put(None)
                break
            line = line.rstrip('\n').rstrip('\r')
            _input_queue.put(line)
        except (EOFError, OSError):
            _input_queue.put(None)
            break


def _start_input_reader():
    """Mulai thread input reader (hanya dipanggil sekali di awal)."""
    global _input_thread
    _input_running.set()
    _input_thread = threading.Thread(target=_input_reader, daemon=True)
    _input_thread.start()


def _stop_input_reader():
    """Hentikan thread input reader."""
    _input_running.clear()


def _get_input(prompt_text=""):
    """
    Ambil input user dari queue. Satu-satunya fungsi input di seluruh program.
    Menampilkan prompt, lalu tunggu item dari queue.
    """
    if prompt_text:
        sys.stdout.write(prompt_text)
        sys.stdout.flush()
    while True:
        try:
            item = _input_queue.get(timeout=0.1)
            if item is None:  # EOF
                raise EOFError
            return item
        except queue.Empty:
            continue


def _check_interrupt_nonblock():
    """
    Cek apakah ada input 'q' yang pending di queue (non-blocking).
    Jika ada 'q', set interrupt event dan return True.
    Item lain yang bukan 'q' disimpan kembali ke queue tanpa infinite loop.
    """
    found_non_q = []
    try:
        while True:
            item = _input_queue.get_nowait()
            if item is None:
                for saved in found_non_q:
                    _input_queue.put(saved)
                return False
            if item.strip().lower() == "q":
                for saved in found_non_q:
                    _input_queue.put(saved)
                _interrupt_event.set()
                return True
            else:
                found_non_q.append(item)
    except queue.Empty:
        for saved in found_non_q:
            _input_queue.put(saved)
        return False


def _reset_interrupt():
    """Reset interrupt flag untuk sesi baru."""
    _interrupt_event.clear()


def _is_interrupted() -> bool:
    """Cek apakah interrupt telah di-request."""
    return _interrupt_event.is_set()


# ============================================================
# WARNA & DEKORASI
# ============================================================
class Style:
    # Warna dasar
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"
    ORANGE  = "\033[38;5;208m"
    PINK    = "\033[38;5;213m"
    TEAL    = "\033[38;5;30m"

    # ── Palet ala Claude Code ──────────────────────────────────
    # Aksen utama: coral/salmon hangat (warna khas Claude)
    ACCENT      = "\033[38;5;209m"   # coral terang  — branding & marker utama
    ACCENT_DIM  = "\033[38;5;174m"   # coral lembut  — aksen sekunder
    # Skala abu-abu berlapis untuk teks sekunder/meta
    GREY        = "\033[38;5;245m"   # abu medium    — teks meta
    GREY_DARK   = "\033[38;5;240m"   # abu gelap     — garis & border
    GREY_LIGHT  = "\033[38;5;250m"   # abu terang    — teks isi sekunder
    OK          = "\033[38;5;114m"   # hijau lembut  — status sukses
    WARN        = "\033[38;5;215m"   # kuning hangat — peringatan
    ERR         = "\033[38;5;203m"   # merah lembut  — error

    # Gaya
    BOLD    = "\033[1m"
    ITALIC  = "\033[3m"
    UNDERLINE = "\033[4m"
    STRIKE  = "\033[9m"
    RESET   = "\033[0m"


# ============================================================
# UI HELPER — primitif tampilan ala Claude Code
# ============================================================

# Lebar konten standar untuk panel & garis
UI_WIDTH = 64

_ANSI_RE = re.compile(r'\033\[[0-9;]*m')


def _strip_ansi(text: str) -> str:
    """Hapus semua kode warna ANSI — dipakai untuk menghitung lebar visual."""
    return _ANSI_RE.sub('', text)


def _visible_len(text: str) -> int:
    """
    Lebar tampil teks (tanpa kode ANSI), sadar karakter lebar-ganda.
    Emoji & CJK (East Asian Width 'W'/'F') dihitung 2 kolom agar border
    panel tetap rata. Variation selector (mis. ️) dihitung 0.
    """
    width = 0
    for ch in _strip_ansi(text):
        if unicodedata.combining(ch) or ch == "️":
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def _rule(width: int = UI_WIDTH, color: str = Style.GREY_DARK, char: str = "─") -> str:
    """Garis horizontal tipis."""
    return f"{color}{char * width}{Style.RESET}"


def _box(lines, color=Style.GREY_DARK, pad=1, width=UI_WIDTH):
    """
    Bungkus daftar baris dalam panel rounded-corner ala Claude Code.
    Tiap elemen `lines` boleh mengandung kode ANSI; lebar dihitung dari teks
    tampak sehingga border tetap rata.
    Mengembalikan string multi-baris siap di-print.
    """
    inner = width - (pad * 2)
    out = [f"{color}╭{'─' * width}╮{Style.RESET}"]
    for ln in lines:
        vis = _visible_len(ln)
        filler = max(0, inner - vis)
        out.append(
            f"{color}│{Style.RESET}{' ' * pad}{ln}{' ' * filler}{' ' * pad}{color}│{Style.RESET}"
        )
    out.append(f"{color}╰{'─' * width}╯{Style.RESET}")
    return "\n".join(out)


class Spinner:
    """
    Spinner animasi satu-baris ala Claude Code:

        ✷  Menelaah… (4s · q untuk interupsi)

    Bintang berdenyut, kata kerja berganti tiap beberapa detik, dan timer
    berjalan. Berjalan di thread daemon terpisah; berhenti rapi dengan
    membersihkan barisnya sehingga output berikutnya mulai dari baris bersih.
    """

    # Bintang berdenyut (tumbuh-menyusut) — terasa "hidup"
    FRAMES = ["✶", "✷", "✸", "✹", "✺", "✹", "✸", "✷"]

    # Kata kerja yang berganti-ganti (sentuhan menyenangkan khas Claude)
    WORDS = [
        "Berpikir", "Menelaah", "Merangkai", "Menimbang", "Menyusun",
        "Memproses", "Menggali", "Meramu", "Mencerna", "Menalar",
    ]

    def __init__(self):
        self._thread = None
        self._running = threading.Event()
        self._label = None
        self._start_ts = 0.0
        self._enabled = sys.stdout.isatty()

    def start(self, label: str = None):
        """Mulai animasi. `label` tetap jika diberikan; jika None, kata berganti otomatis."""
        if not self._enabled or self._running.is_set():
            return
        self._label = label
        self._start_ts = time.time()
        self._running.set()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        i = 0
        while self._running.is_set():
            elapsed = time.time() - self._start_ts
            frame = self.FRAMES[i % len(self.FRAMES)]
            if self._label:
                word = self._label
            else:
                # ganti kata kerja tiap ~3.5 detik
                word = self.WORDS[int(elapsed // 3.5) % len(self.WORDS)]
            secs = int(elapsed)
            line = (
                f"\r  {Style.ACCENT}{frame}{Style.RESET}  "
                f"{Style.GREY_LIGHT}{word}…{Style.RESET} "
                f"{Style.GREY}({secs}s · q untuk interupsi){Style.RESET}"
            )
            sys.stdout.write(line + "\033[K")  # \033[K = bersihkan sisa baris
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)

    def stop(self):
        """Hentikan animasi dan bersihkan baris spinner."""
        if not self._running.is_set():
            return
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=0.3)
        # Bersihkan seluruh baris spinner agar output berikut mulai bersih
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


# Spinner global tunggal — siklus hidupnya dikelola di dalam chat()
_spinner = Spinner()


# ============================================================
# MARKDOWN TO TERMINAL FORMATTER
# ============================================================

class TerminalFormatter:
    """
    Mengkonversi markdown text ke formatted terminal output.
    Mendukung: headers, bold, italic, strikethrough, code, lists,
    blockquotes, horizontal rules, links, dan tabel.
    """

    # Lebar default terminal
    TERM_WIDTH = 70

    # Bullet styles untuk nested lists
    BULLETS = ["•", "◦", "▪", "▫", "→"]
    NUMBER_WIDTH = 4

    @classmethod
    def format(cls, text: str) -> str:
        """Main entry: konversi full markdown text ke terminal-formatted text."""
        if not text:
            return text

        result = text

        # Proses tabel dulu (sebelum inline formatting)
        result = cls._format_tables(result)

        # Code blocks (fenced) — proses dulu sebelum inline
        result = cls._format_code_blocks(result)

        # Horizontal rules
        result = cls._format_horizontal_rules(result)

        # Headers
        result = cls._format_headers(result)

        # Blockquotes
        result = cls._format_blockquotes(result)

        # Lists (ordered & unordered) — multi-level
        result = cls._format_lists(result)

        # Inline formatting
        result = cls._format_inline_code(result)
        result = cls._format_bold(result)
        result = cls._format_bold_italic(result)
        result = cls._format_strikethrough(result)
        result = cls._format_links(result)
        result = cls._format_italic(result)

        # Bersihkan trailing whitespace per baris
        lines = result.split("\n")
        lines = [line.rstrip() for line in lines]
        result = "\n".join(lines)

        # Bersihkan lebih dari 2 consecutive blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result.strip()

    # ── Headers ──────────────────────────────────────────────
    @classmethod
    def _format_headers(cls, text: str) -> str:
        lines = text.split("\n")
        result = []

        for line in lines:
            stripped = line.strip()

            if re.match(r'^#\s+', stripped) and not re.match(r'^##\s+', stripped):
                title = re.sub(r'^#\s+', '', stripped)
                title = cls._strip_inline_md(title)
                width = cls.TERM_WIDTH - 4
                padded = f"  {Style.ACCENT}{Style.BOLD}{title}{Style.RESET}"
                result.append(padded)
                result.append(f"  {Style.GREY_DARK}{'─' * width}{Style.RESET}")

            elif re.match(r'^##\s+', stripped) and not re.match(r'^###\s+', stripped):
                title = re.sub(r'^##\s+', '', stripped)
                title = cls._strip_inline_md(title)
                padded = f"  {Style.ACCENT}{Style.BOLD}{title}{Style.RESET}"
                result.append("")
                result.append(padded)

            elif re.match(r'^###\s+', stripped) and not re.match(r'^####\s+', stripped):
                title = re.sub(r'^###\s+', '', stripped)
                title = cls._strip_inline_md(title)
                result.append(f"\n  {Style.BOLD}{title}{Style.RESET}")

            elif re.match(r'^#{4}\s+', stripped) and not re.match(r'^#{5}\s+', stripped):
                title = re.sub(r'^#{4}\s+', '', stripped)
                title = cls._strip_inline_md(title)
                result.append(f"  {Style.WHITE}{Style.BOLD}  • {title}{Style.RESET}")

            elif re.match(r'^#{5,}\s+', stripped):
                title = re.sub(r'^#{5,}\s+', '', stripped)
                title = cls._strip_inline_md(title)
                result.append(f"  {Style.DIM}  ◦ {title}{Style.RESET}")

            else:
                result.append(line)

        return "\n".join(result)

    # ── Tables ───────────────────────────────────────────────
    @classmethod
    def _format_tables(cls, text: str) -> str:
        lines = text.split("\n")
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if '|' in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                if re.match(r'^\s*\|?[\s\-:|]+\|?\s*$', next_line) and '-' in next_line:
                    table_lines = [line]
                    i += 1
                    while i < len(lines) and '|' in lines[i]:
                        table_lines.append(lines[i])
                        i += 1

                    table_output = cls._render_table(table_lines)
                    result.append(table_output)
                    continue

            result.append(line)
            i += 1

        return "\n".join(result)

    @classmethod
    def _render_table(cls, table_lines: list) -> str:
        rows = []
        for tl in table_lines:
            stripped = tl.strip()
            if re.match(r'^\|?[\s\-:|]+\|?$', stripped):
                continue
            cells = [c.strip() for c in stripped.split('|')]
            if cells and cells[0] == '':
                cells = cells[1:]
            if cells and cells[-1] == '':
                cells = cells[:-1]
            if cells:
                cells = [cls._strip_inline_md(c) for c in cells]
                rows.append(cells)

        if not rows:
            return "\n".join(table_lines)

        num_cols = max(len(r) for r in rows)
        col_widths = [0] * num_cols
        for row in rows:
            for j, cell in enumerate(row):
                if j < num_cols:
                    col_widths[j] = max(col_widths[j], len(cell))

        col_widths = [max(w, 3) for w in col_widths]

        lines = []

        def h_line(left, mid, right):
            parts = ['─' * (w + 2) for w in col_widths]
            return f"  {Style.DIM}{left}{mid.join(parts)}{right}{Style.RESET}"

        lines.append(h_line('┌', '┬', '┐'))

        for i, row in enumerate(rows):
            padded_cells = []
            for j in range(num_cols):
                cell = row[j] if j < len(row) else ""
                padded_cells.append(f" {cell:<{col_widths[j]}} ")

            row_str = f"  {Style.DIM}│{Style.RESET}" + f"{Style.DIM}│{Style.RESET}".join(padded_cells) + f"{Style.DIM}│{Style.RESET}"
            lines.append(row_str)

            if i == 0:
                lines.append(h_line('├', '┼', '┤'))

        lines.append(h_line('└', '┴', '┘'))

        return "\n".join(lines)

    # ── Code Blocks ──────────────────────────────────────────
    @classmethod
    def _format_code_blocks(cls, text: str) -> str:
        def replace_block(match):
            lang = match.group(1) or ""
            code = match.group(2).rstrip('\n')

            code_lines = code.split("\n")
            result_lines = [""]

            # Label bahasa tipis di atas (mis. "python")
            if lang:
                result_lines.append(f"  {Style.GREY_DARK}{lang}{Style.RESET}")

            # Gaya Claude Code: garis kiri tipis + teks kode VERBATIM
            # (jangan strip markdown/indentasi — kode harus apa adanya)
            for cl in code_lines:
                result_lines.append(f"  {Style.GREY_DARK}│{Style.RESET} {Style.GREY_LIGHT}{cl}{Style.RESET}")

            result_lines.append("")
            return "\n".join(result_lines)

        return re.sub(r'```(\w*)\n(.*?)```', replace_block, text, flags=re.DOTALL)

    # ── Blockquotes ──────────────────────────────────────────
    @classmethod
    def _format_blockquotes(cls, text: str) -> str:
        lines = text.split("\n")
        result = []
        in_quote = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('>'):
                content = re.sub(r'^>\s?', '', stripped)
                content = cls._strip_inline_md(content)
                result.append(f"  {Style.DIM}┃ {Style.WHITE}{content}{Style.RESET}")
                in_quote = True
            else:
                if in_quote:
                    result.append(f"  {Style.DIM}┃{Style.RESET}")
                    in_quote = False
                result.append(line)

        return "\n".join(result)

    # ── Lists ────────────────────────────────────────────────
    @classmethod
    def _format_lists(cls, text: str) -> str:
        lines = text.split("\n")
        result = []

        for line in lines:
            stripped = line

            unordered_match = re.match(r'^(\s*)[-*+]\s+(.*)', stripped)
            ordered_match = re.match(r'^(\s*)(\d+)[.)]\s+(.*)', stripped)

            if unordered_match:
                indent = unordered_match.group(1)
                content = unordered_match.group(2)
                level = len(indent) // 2
                bullet = cls.BULLETS[min(level, len(cls.BULLETS) - 1)]
                indent_str = "  " + "    " * level
                result.append(f"{indent_str}{Style.ACCENT_DIM}{bullet}{Style.RESET} {content}")

            elif ordered_match:
                indent = ordered_match.group(1)
                number = ordered_match.group(2)
                content = ordered_match.group(3)
                level = len(indent) // 2
                indent_str = "  " + "    " * level
                result.append(f"{indent_str}{Style.ACCENT_DIM}{number}.{Style.RESET} {content}")

            else:
                result.append(line)

        return "\n".join(result)

    # ── Horizontal Rules ─────────────────────────────────────
    @classmethod
    def _format_horizontal_rules(cls, text: str) -> str:
        def replace_hr(match):
            return f"\n  {Style.DIM}{'─' * (cls.TERM_WIDTH - 4)}{Style.RESET}\n"
        return re.sub(r'^\s*[-*_]{3,}\s*$', replace_hr, text, flags=re.MULTILINE)

    # ── Inline Formatting ────────────────────────────────────
    @classmethod
    def _format_bold_italic(cls, text: str) -> str:
        return re.sub(
            r'\*\*\*(.+?)\*\*\*',
            rf'{Style.BOLD}{Style.ITALIC}\1{Style.RESET}',
            text
        )

    @classmethod
    def _format_bold(cls, text: str) -> str:
        text = re.sub(
            r'\*\*(.+?)\*\*',
            rf'{Style.BOLD}\1{Style.RESET}',
            text
        )
        text = re.sub(
            r'__(.+?)__',
            rf'{Style.BOLD}\1{Style.RESET}',
            text
        )
        return text

    @classmethod
    def _format_italic(cls, text: str) -> str:
        text = re.sub(
            r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)',
            rf'{Style.ITALIC}\1{Style.RESET}',
            text
        )
        text = re.sub(
            r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)',
            rf'{Style.ITALIC}\1{Style.RESET}',
            text
        )
        return text

    @classmethod
    def _format_strikethrough(cls, text: str) -> str:
        return re.sub(
            r'~~(.+?)~~',
            rf'{Style.STRIKE}\1{Style.RESET}',
            text
        )

    @classmethod
    def _format_inline_code(cls, text: str) -> str:
        # Inline code: aksen coral lembut, tanpa spasi tambahan yang mengganggu
        return re.sub(
            r'`([^`]+)`',
            rf'{Style.ACCENT_DIM}\1{Style.RESET}',
            text
        )

    @classmethod
    def _format_links(cls, text: str) -> str:
        return re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            rf'{Style.UNDERLINE}{Style.CYAN}\1{Style.RESET} {Style.GREY}({Style.RESET}{Style.GREY}\2{Style.RESET}{Style.GREY}){Style.RESET}',
            text
        )

    # ── Helper ───────────────────────────────────────────────
    @classmethod
    def _strip_inline_md(cls, text: str) -> str:
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        text = re.sub(r'~~(.+?)~~', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
        return text.strip()


def format_reply(text: str) -> str:
    """Shortcut: format markdown reply ke terminal output."""
    return TerminalFormatter.format(text)


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def _ensure_sessions_dir():
    """Pastikan folder sessions/ ada."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def _session_path(name: str) -> str:
    """Dapatkan path file session berdasarkan nama."""
    # Sanitize nama session — hanya alphanumeric, dash, underscore
    safe_name = re.sub(r'[^\w\-]', '_', name).strip('_')
    if not safe_name:
        safe_name = "untitled"
    return os.path.join(SESSIONS_DIR, f"{safe_name}.json")


def _generate_session_name() -> str:
    """Generate nama session otomatis berdasarkan timestamp."""
    return datetime.now().strftime("session_%Y%m%d_%H%M%S")


def save_session(name: str, messages: list) -> str:
    """
    Simpan session ke file JSON.
    Returns: pesan status.
    """
    _ensure_sessions_dir()
    path = _session_path(name)

    session_data = {
        "name": name,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "message_count": len(messages),
        "messages": messages,
    }

    # Jika file sudah ada, pertahankan created_at
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                old = json.load(f)
            session_data["created_at"] = old.get("created_at", session_data["created_at"])
        except (json.JSONDecodeError, IOError):
            pass

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return f"Session '{name}' berhasil disimpan ({len(messages)} messages)."
    except Exception as e:
        return f"Error menyimpan session: {e}"


def load_session(name: str) -> tuple:
    """
    Load session dari file JSON.
    Returns: (messages, metadata_dict) atau (None, None) jika gagal.
    """
    path = _session_path(name)

    if not os.path.exists(path):
        return None, None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        messages = data.get("messages", [])
        metadata = {
            "name": data.get("name", name),
            "created_at": data.get("created_at", "unknown"),
            "updated_at": data.get("updated_at", "unknown"),
            "message_count": data.get("message_count", len(messages)),
        }
        return messages, metadata
    except json.JSONDecodeError:
        return None, None
    except Exception:
        return None, None


def list_sessions() -> list:
    """
    Dapatkan daftar semua session yang tersimpan.
    Returns: list of dicts dengan info session.
    """
    _ensure_sessions_dir()
    sessions = []

    try:
        files = sorted(os.listdir(SESSIONS_DIR))
    except OSError:
        return sessions

    for f in files:
        if not f.endswith(".json"):
            continue
        path = os.path.join(SESSIONS_DIR, f)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            name = data.get("name", f[:-5])
            created = data.get("created_at", "unknown")
            updated = data.get("updated_at", "unknown")
            msg_count = data.get("message_count", 0)
            file_size = os.path.getsize(path)

            # Format tanggal agar readable
            try:
                created_dt = datetime.fromisoformat(created)
                created_fmt = created_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                created_fmt = str(created)[:16]

            try:
                updated_dt = datetime.fromisoformat(updated)
                updated_fmt = updated_dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                updated_fmt = str(updated)[:16]

            sessions.append({
                "name": name,
                "created": created_fmt,
                "updated": updated_fmt,
                "messages": msg_count,
                "size": file_size,
            })
        except (json.JSONDecodeError, IOError):
            # File corrupt, tetap tampilkan
            sessions.append({
                "name": f[:-5],
                "created": "?",
                "updated": "?",
                "messages": 0,
                "size": os.path.getsize(path),
            })

    return sessions


def delete_session(name: str) -> str:
    """Hapus file session."""
    path = _session_path(name)
    if not os.path.exists(path):
        return f"Session '{name}' tidak ditemukan."
    try:
        os.remove(path)
        return f"Session '{name}' berhasil dihapus."
    except Exception as e:
        return f"Error menghapus session: {e}"


def clear_sessions() -> str:
    """
    Hapus semua session auto-generated (tanpa nama).
    Session auto-generated memiliki pola nama: session_YYYYMMDD_HHMMSS
    Session dengan nama custom (user-defined) TIDAK akan dihapus.
    Returns: pesan status dengan jumlah session yang dihapus.
    """
    _ensure_sessions_dir()

    # Regex pattern untuk session auto-generated
    auto_pattern = re.compile(r'^session_\d{8}_\d{6}$')

    deleted = []
    skipped = []

    try:
        files = os.listdir(SESSIONS_DIR)
    except OSError as e:
        return f"Error membaca folder sessions: {e}"

    for f in files:
        if not f.endswith(".json"):
            continue
        name = f[:-5]  # hapus .json
        if auto_pattern.match(name):
            path = os.path.join(SESSIONS_DIR, f)
            try:
                os.remove(path)
                deleted.append(name)
            except OSError as e:
                skipped.append(f"{name} (error: {e})")
        else:
            skipped.append(name)

    # Build result message — gaya bersih ala Claude Code
    parts = []
    if deleted:
        parts.append(f"\n  {Style.OK}⏺{Style.RESET} {Style.GREY_LIGHT}{len(deleted)} session auto-generated dihapus{Style.RESET}")
        for d in deleted:
            parts.append(f"    {Style.GREY_DARK}⎿{Style.RESET}  {Style.GREY}{d}{Style.RESET}")
    else:
        parts.append(f"\n  {Style.GREY}Tidak ada session auto-generated yang ditemukan.{Style.RESET}")

    if skipped:
        parts.append(f"\n  {Style.ACCENT_DIM}⏺{Style.RESET} {Style.GREY_LIGHT}{len(skipped)} session custom dipertahankan{Style.RESET}")
        for s in skipped:
            parts.append(f"    {Style.GREY_DARK}⎿{Style.RESET}  {Style.GREY}{s}{Style.RESET}")

    return "\n".join(parts)


def search_sessions(keyword: str) -> str:
    """
    Cari session berdasarkan keyword (case-insensitive).
    Mencocokkan keyword dengan nama session.
    Returns: formatted string dengan hasil pencarian.
    """
    all_sessions = list_sessions()

    if not all_sessions:
        return "ℹ️ Tidak ada session tersimpan."

    keyword_lower = keyword.strip().lower()
    matched = [s for s in all_sessions if keyword_lower in s["name"].lower()]

    if not matched:
        return f"  {Style.GREY}Tidak ditemukan session yang mengandung {Style.GREY_LIGHT}'{keyword}'{Style.GREY}.{Style.RESET}"

    # Format hasil pencarian — gaya bersih ala Claude Code
    lines = [
        f"\n  {Style.ACCENT}✻{Style.RESET} {Style.BOLD}Pencarian{Style.RESET} {Style.GREY}'{keyword}' — {len(matched)}/{len(all_sessions)} session{Style.RESET}",
        f"  {_rule()}",
    ]

    for i, s in enumerate(matched, 1):
        size_str = _format_size(s["size"])
        lines.append(f"  {Style.GREY_DARK}{i:>2}{Style.RESET} {Style.ACCENT_DIM}⏺{Style.RESET} {Style.GREY_LIGHT}{s['name']}{Style.RESET}")
        lines.append(f"       {Style.GREY}{s['messages']} pesan · diupdate {s['updated']} · {size_str}{Style.RESET}")

    return "\n".join(lines)


def rename_session(old_name: str, new_name: str) -> str:
    """Rename file session."""
    old_path = _session_path(old_name)
    new_path = _session_path(new_name)

    if not os.path.exists(old_path):
        return f"Session '{old_name}' tidak ditemukan."
    if os.path.exists(new_path):
        return f"Session '{new_name}' sudah ada. Pilih nama lain."

    try:
        # Load, update metadata, save ke file baru, hapus file lama
        with open(old_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["name"] = new_name
        data["updated_at"] = datetime.now().isoformat()

        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        os.remove(old_path)
        return f"Session '{old_name}' berhasil di-rename menjadi '{new_name}'."
    except Exception as e:
        return f"Error rename session: {e}"


# ============================================================
# UI FUNCTIONS - RUKA AI (KURA-KURA)
# ============================================================

def _help_section(title: str):
    """Header bagian help: judul aksen + garis tipis."""
    print(f"\n  {Style.ACCENT}{Style.BOLD}{title}{Style.RESET}")


def _help_row(cmd: str, desc: str, cmd_color: str = Style.GREY_LIGHT):
    """Satu baris help dengan kolom command sejajar."""
    pad = max(0, 30 - len(cmd))
    print(f"    {cmd_color}{cmd}{Style.RESET}{' ' * pad}{Style.GREY}{desc}{Style.RESET}")


def show_help():
    """Tampilkan menu help — gaya bersih ala Claude Code (header tipis, kolom sejajar)."""
    star = f"{Style.ACCENT}{Style.BOLD}✻{Style.RESET}"
    print()
    print(f"  {star} {Style.BOLD}Ruka AI{Style.RESET} {Style.GREY}— bantuan{Style.RESET}")
    print(f"  {_rule()}")

    _help_section("Penggunaan")
    _help_row("python main.py", "Mode interaktif (session baru otomatis)")
    _help_row("python main.py <namaSesi>", "Load atau buat session bernama")
    _help_row("python main.py \"<prompt>\"", "Mode prompt tunggal (langsung jawab)")

    _help_section("Slash command (dalam sesi)")
    _help_row("/help", "Tampilkan bantuan ini")
    _help_row("/sessions", "Lihat daftar semua session")
    _help_row("/new", "Mulai session baru (lama auto-save)")
    _help_row("/history", "Lihat riwayat chat sesi ini")
    _help_row("/clear", "Bersihkan layar")
    _help_row("/delete-session <nama>", "Hapus session tertentu")
    _help_row("/rename-session <l> <b>", "Rename session")

    _help_section("CLI command (dari terminal)")
    _help_row("listSessions", "Daftar semua session tersimpan")
    _help_row("searchSessions <keyword>", "Cari session (case-insensitive)")
    _help_row("deleteSession <nama>", "Hapus session tertentu")
    _help_row("renameSession <l> <b>", "Rename session")
    _help_row("clearSessions", "Hapus semua session auto-generated")

    _help_section("Tips")
    print(f"    {Style.GREY}•{Style.RESET} {Style.GREY}Ketik {Style.GREY_LIGHT}q{Style.GREY} saat AI memproses untuk interupsi.{Style.RESET}")
    print(f"    {Style.GREY}•{Style.RESET} {Style.GREY}Ketik {Style.GREY_LIGHT}exit{Style.GREY} atau {Style.GREY_LIGHT}quit{Style.GREY} untuk keluar.{Style.RESET}")
    print(f"    {Style.GREY}•{Style.RESET} {Style.GREY}Session tersimpan otomatis di folder {Style.GREY_LIGHT}sessions/{Style.GREY}.{Style.RESET}")
    print()


def ruka_print():
    """Sapaan pembuka — panel sambutan rounded ala Claude Code."""
    star = f"{Style.ACCENT}{Style.BOLD}✻{Style.RESET}"
    lines = [
        f"{star} {Style.BOLD}Selamat datang di Ruka AI{Style.RESET}",
        "",
        f"{Style.GREY}Agen kura-kura untuk file, folder & terminal.{Style.RESET}",
        f"{Style.GREY}Bijak, sabar, teliti. 🐢{Style.RESET}",
    ]
    print()
    print(_box(lines, color=Style.ACCENT_DIM))


def _shorten_path(path: str, limit: int = 44) -> str:
    """Persingkat path panjang dengan menyisipkan … di tengah."""
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]
    if len(path) <= limit:
        return path
    keep = limit - 1
    head = keep // 2
    tail = keep - head
    return path[:head] + "…" + path[-tail:]


def show_banner(session_name: str = None, session_meta: dict = None, is_new: bool = True):
    """
    Ringkasan konteks ala Claude Code: baris-baris meta tipis di bawah
    panel sambutan, bukan boks ganda yang berat.
    """
    bullet = f"{Style.GREY_DARK}•{Style.RESET}"

    print()
    print(f"  {Style.GREY}cwd{Style.RESET}      {bullet} {Style.GREY_LIGHT}{_shorten_path(BASE_DIR)}{Style.RESET}")
    print(f"  {Style.GREY}model{Style.RESET}    {bullet} {Style.GREY_LIGHT}{MODEL}{Style.RESET}")

    if session_name:
        if is_new:
            tag = f"{Style.GREY}(baru){Style.RESET}"
        else:
            msg_count = session_meta.get("message_count", 0) if session_meta else 0
            created = session_meta.get("created_at", "?") if session_meta else "?"
            try:
                created = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass
            meta = f"{msg_count} pesan" + (f" · dibuat {created}" if created != "?" else "")
            tag = f"{Style.GREY}({meta}){Style.RESET}"
        print(f"  {Style.GREY}session{Style.RESET}  {bullet} {Style.ACCENT}{session_name}{Style.RESET} {tag}")

    print()
    print(f"  {Style.GREY}Ketik {Style.RESET}{Style.GREY_LIGHT}/help{Style.RESET} {Style.GREY}untuk bantuan, {Style.RESET}{Style.GREY_LIGHT}exit{Style.RESET} {Style.GREY}untuk keluar, {Style.RESET}{Style.GREY_LIGHT}q{Style.RESET} {Style.GREY}untuk interupsi.{Style.RESET}")


def show_examples():
    """Beberapa contoh perintah singkat — gaya 'tips' Claude Code, ringan & tidak berbingkai."""
    examples = [
        "Tampilkan daftar file dan folder",
        "Baca isi file catatan.txt lalu ringkas",
        "Buat file todo.txt berisi daftar belanja",
        "Jalankan 'ls -la' lalu jelaskan hasilnya",
        "Cari semua file .py dan hitung jumlah barisnya",
    ]
    print()
    print(f"  {Style.GREY}Coba sesuatu seperti:{Style.RESET}")
    for ex in examples:
        print(f"  {Style.ACCENT_DIM}❯{Style.RESET} {Style.GREY_LIGHT}{ex}{Style.RESET}")
    print()


def show_session_list():
    """Tampilkan daftar semua session yang tersimpan."""
    sessions = list_sessions()

    if not sessions:
        print(f"\n  {Style.GREY}Belum ada session tersimpan.{Style.RESET}")
        print(f"  {Style.GREY}Mulai dengan {Style.GREY_LIGHT}python main.py <nama>{Style.GREY}.{Style.RESET}")
        return

    print(f"\n  {Style.ACCENT}✻{Style.RESET} {Style.BOLD}Session{Style.RESET} {Style.GREY}({len(sessions)}){Style.RESET}")
    print(f"  {_rule()}")

    for i, s in enumerate(sessions, 1):
        size_str = _format_size(s["size"])
        print(f"  {Style.GREY_DARK}{i:>2}{Style.RESET} {Style.ACCENT_DIM}⏺{Style.RESET} {Style.GREY_LIGHT}{s['name']}{Style.RESET}")
        print(f"       {Style.GREY}{s['messages']} pesan · diupdate {s['updated']} · {size_str}{Style.RESET}")

    print(f"\n  {Style.GREY}Lanjutkan dengan {Style.GREY_LIGHT}python main.py <nama>{Style.GREY}.{Style.RESET}")


def show_session_history(messages: list, session_name: str):
    """Tampilkan riwayat chat sesi saat ini."""
    # Filter hanya role user dan assistant (skip system & tool)
    chat_messages = [m for m in messages if m.get("role") in ("user", "assistant")]

    if not chat_messages:
        print(f"\n  {Style.GREY}Belum ada riwayat chat di sesi ini.{Style.RESET}")
        return

    print(f"\n  {Style.ACCENT}✻{Style.RESET} {Style.BOLD}Riwayat{Style.RESET} {Style.GREY}— {session_name}{Style.RESET}")
    print(f"  {_rule()}")

    for i, msg in enumerate(chat_messages, 1):
        role = msg.get("role", "?")
        content = msg.get("content", "")

        # Skip system messages
        if role == "system":
            continue

        # Truncate content jika terlalu panjang
        if content and len(content) > 200:
            content = content[:200] + "…"
        if not content:
            content = f"{Style.GREY_DARK}(tool call){Style.RESET}"

        if role == "user":
            print(f"\n  {Style.GREY}❯{Style.RESET} {Style.GREY_LIGHT}{content}{Style.RESET}")
        elif role == "assistant":
            print(f"  {Style.ACCENT}⏺{Style.RESET} {content}")

    print()


def show_separator():
    # Pemisah antar-giliran sangat tipis & lapang (gaya Claude Code)
    print()


# ── Pemetaan nama tool internal → label ringkas ala Claude Code ──
TOOL_LABELS = {
    "read_file":     "Read",
    "write_file":    "Write",
    "edit_file":     "Edit",
    "list_files":    "List",
    "delete_file":   "Delete",
    "copy_file":     "Copy",
    "move_file":     "Move",
    "get_file_info": "Info",
    "create_folder": "MkDir",
    "delete_folder": "RmDir",
    "list_all":      "Tree",
    "exec_command":  "Bash",
}


def _tool_label(name: str) -> str:
    return TOOL_LABELS.get(name, name)


def _tool_arg_summary(tool_name: str, args: dict) -> str:
    """Ringkas argumen tool jadi satu baris bersih: Read(main.py), Bash(ls -la)."""
    if not args:
        return ""
    if tool_name in ("copy_file", "move_file") and "source" in args:
        dst = args.get("destination", "?")
        return f"{args['source']} → {dst}"
    for k in ("command", "filename", "name", "foldername", "source", "path"):
        if k in args and args[k] not in (None, ""):
            return str(args[k])
    return ", ".join(f"{k}={v}" for k, v in args.items())


def _result_summary(result: str) -> tuple:
    """
    Ringkas hasil tool untuk baris ⎿. Return (teks, is_error).
    Tampilkan baris pertama yang berarti + jumlah baris sisa.
    """
    if result is None:
        return "(tidak ada output)", False
    text = str(result).strip()
    if not text:
        return "(kosong)", False
    is_error = text.lower().startswith("error")
    lines = [l for l in text.split("\n")]
    first = lines[0].strip()
    if len(first) > 60:
        first = first[:59] + "…"
    extra = len(lines) - 1
    if extra > 0:
        first = f"{first}  {Style.GREY_DARK}+{extra} baris{Style.RESET}"
    return first, is_error


def _emit_agent_text(text: str, interrupted: bool = False):
    """
    Cetak teks asisten dengan marker ⏺ ala Claude Code.
    Baris pertama menempel pada marker; lanjutannya diberi margin kiri rapi.
    """
    marker = Style.WARN if interrupted else Style.ACCENT
    if text is None or not text.strip():
        print(f"\n  {marker}⏺{Style.RESET} {Style.GREY_DARK}(tidak ada jawaban){Style.RESET}")
        return
    formatted = format_reply(text)
    lines = formatted.split("\n")
    first = lines[0].lstrip()
    print(f"\n  {marker}⏺{Style.RESET} {first}")
    for ln in lines[1:]:
        print(f"  {ln}" if ln.strip() else "")


def show_model_narration(round_num, content):
    """
    Narasi singkat model sebelum/diantara pemanggilan tool.
    Ditampilkan sebagai teks asisten ber-marker ⏺ (tanpa boks).
    """
    if not content or not content.strip():
        return
    _emit_agent_text(content)


def show_tool_call(tool_name, args, result):
    """
    Tampilkan pemanggilan tool ala Claude Code:

        ⏺ Bash(ls -la)
          ⎿ total 192  +14 baris
    """
    label = _tool_label(tool_name)
    arg_str = _tool_arg_summary(tool_name, args) if isinstance(args, dict) else str(args)
    if len(arg_str) > 52:
        arg_str = arg_str[:51] + "…"

    summary, is_error = _result_summary(result)
    dot = Style.ERR if is_error else Style.OK

    head = f"\n  {dot}⏺{Style.RESET} {Style.BOLD}{label}{Style.RESET}"
    if arg_str:
        head += f"{Style.GREY}({Style.RESET}{Style.GREY_LIGHT}{arg_str}{Style.GREY}){Style.RESET}"
    print(head)

    res_color = Style.ERR if is_error else Style.GREY
    print(f"    {Style.GREY_DARK}⎿{Style.RESET}  {res_color}{summary}{Style.RESET}")


def show_round_info(round_num):
    # Tidak lagi dipakai — spinner animasi yang menandakan pemrosesan.
    pass


def show_interrupt_notice():
    print(f"\n  {Style.WARN}■{Style.RESET}  {Style.WARN}Interupsi diminta{Style.RESET} {Style.GREY}— menyelesaikan round saat ini lalu berhenti…{Style.RESET}")


def show_interrupted_reply_header():
    # marker ⏺ ditangani oleh _emit_agent_text(interrupted=True)
    pass


def show_exit(session_name: str = None):
    print(f"\n  {Style.ACCENT}✻{Style.RESET} {Style.GREY_LIGHT}Sampai jumpa! 🐢{Style.RESET}")
    if session_name:
        print(f"    {Style.GREY_DARK}⎿{Style.RESET}  {Style.GREY}Session {Style.GREY_LIGHT}{session_name}{Style.GREY} tersimpan otomatis.{Style.RESET}")
    print()


def show_error(error_msg):
    print(f"\n  {Style.ERR}⏺{Style.RESET} {Style.ERR}Terjadi kesalahan{Style.RESET}")
    print(f"    {Style.GREY_DARK}⎿{Style.RESET}  {Style.GREY}{error_msg}{Style.RESET}")


def show_retry(error_msg, attempt, max_retries, delay):
    """Tampilkan pesan retry — gaya baris tipis ala Claude Code."""
    print(f"\n  {Style.WARN}⏺{Style.RESET} {Style.WARN}Request gagal{Style.RESET} {Style.GREY}— mencoba lagi {attempt}/{max_retries} dalam {delay}s…{Style.RESET}")
    print(f"    {Style.GREY_DARK}⎿{Style.RESET}  {Style.GREY}{error_msg}{Style.RESET}")


def show_retry_giving_up(error_msg):
    """Tampilkan pesan ketika semua retry sudah habis."""
    print(f"\n  {Style.ERR}⏺{Style.RESET} {Style.ERR}Gagal setelah {MAX_RETRIES} percobaan{Style.RESET}")
    print(f"    {Style.GREY_DARK}⎿{Style.RESET}  {Style.GREY}{error_msg}{Style.RESET}")


def show_thinking():
    # Animasi spinner menggantikan teks statis; siklus hidup dikelola di chat().
    pass


def show_reply_header():
    # marker ⏺ ditangani oleh _emit_agent_text()
    pass


def show_user_prompt(session_name: str = None):
    # Prompt minimalis ala Claude Code: chevron coral '❯'
    return _get_input(f"\n{Style.ACCENT}❯{Style.RESET} ").strip()


# ============================================================
# HELPER: Keamanan Path
# ============================================================

def _safe_path(name: str) -> str | None:
    """
    Mengembalikan path absolut yang aman, atau None jika path traversal terdeteksi.
    """
    path = os.path.join(BASE_DIR, name)
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(BASE_DIR):
        return None
    return abs_path


def _format_size(size_bytes: int) -> str:
    """Format ukuran file menjadi human-readable."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _is_command_blocked(command: str) -> str | None:
    """
    Cek apakah perintah termasuk yang diblokir untuk keamanan.
    Mengembalikan pesan blokir jika dilarang, None jika aman.
    """
    cmd_lower = command.strip().lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return f"Perintah diblokir untuk keamanan: mengandung '{blocked}'"
    return None


# ============================================================
# DEFINISI TOOLS (dikirim ke model)
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Membaca isi file teks dari direktori kerja. "
                "Gunakan ini ketika user meminta membaca, melihat, atau menganalisis isi file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Nama file yang ingin dibaca, misalnya 'catatan.txt' atau 'data.json'."
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Menulis atau membuat file teks di direktori kerja. "
                "Gunakan ini ketika user meminta menyimpan, membuat, atau mengganti isi file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Nama file yang ingin ditulis, misalnya 'output.txt'."
                    },
                    "content": {
                        "type": "string",
                        "description": "Isi konten yang akan ditulis ke file."
                    }
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Mengedit isi file teks yang sudah ada. Mendukung 3 mode operasi: "
                "replace (mengganti teks tertentu), append (menambah teks di akhir file), "
                "prepend (menambah teks di awal file). "
                "Gunakan ini ketika user ingin mengubah sebagian isi file tanpa "
                "menulis ulang seluruh file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Nama file yang ingin diedit, misalnya 'catatan.txt'."
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "append", "prepend"],
                        "description": (
                            "Mode operasi edit: "
                            "'replace' — mengganti old_text dengan new_text, "
                            "'append' — menambah new_text di akhir file, "
                            "'prepend' — menambah new_text di awal file."
                        )
                    },
                    "old_text": {
                        "type": "string",
                        "description": (
                            "Teks lama yang akan diganti (hanya untuk operation='replace'). "
                            "Harus persis sama termasuk spasi dan baris baru."
                        )
                    },
                    "new_text": {
                        "type": "string",
                        "description": (
                            "Teks baru yang akan dimasukkan. "
                            "Untuk 'replace': menggantikan old_text. "
                            "Untuk 'append': ditambahkan di akhir file. "
                            "Untuk 'prepend': ditambahkan di awal file."
                        )
                    }
                },
                "required": ["filename", "operation", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Menampilkan daftar semua file di direktori kerja.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": (
                "Menghapus file dari direktori kerja. "
                "Gunakan ini ketika user meminta untuk menghapus sebuah file. "
                "Tidak bisa menghapus folder, hanya file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Nama file yang ingin dihapus, misalnya 'lama.txt'."
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": (
                "Menyalin file dari sumber ke tujuan di direktori kerja. "
                "Gunakan ini ketika user meminta menyalin/menduplikat file. "
                "Jika folder tujuan belum ada, akan otomatis dibuat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Nama file sumber yang akan disalin, misalnya 'data.txt'."
                    },
                    "destination": {
                        "type": "string",
                        "description": "Nama/path file tujuan, misalnya 'backup/data.txt' atau 'data_copy.txt'."
                    }
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": (
                "Memindahkan atau me-rename file dari sumber ke tujuan di direktori kerja. "
                "Gunakan ini ketika user meminta memindahkan atau me-rename file. "
                "Jika folder tujuan belum ada, akan otomatis dibuat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Nama file sumber yang akan dipindahkan, misalnya 'file.txt'."
                    },
                    "destination": {
                        "type": "string",
                        "description": "Nama/path file tujuan, misalnya 'arsip/file.txt' atau 'nama_baru.txt'."
                    }
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": (
                "Menampilkan informasi detail tentang sebuah file atau folder, "
                "meliputi: ukuran, tanggal dibuat, tanggal modifikasi terakhir, "
                "apakah file atau folder, dan path absolut. "
                "Gunakan ini ketika user meminta info/detail tentang file atau folder tertentu."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nama file atau folder yang ingin dicek infonya, misalnya 'data.json' atau 'backup'."
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": (
                "Membuat folder baru di direktori kerja. "
                "Gunakan ini ketika user meminta membuat folder/direktori baru. "
                "Jika folder sudah ada, akan memberikan pesan error."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "foldername": {
                        "type": "string",
                        "description": "Nama folder yang ingin dibuat, misalnya 'projects' atau 'backup/2024'."
                    }
                },
                "required": ["foldername"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_folder",
            "description": (
                "Menghapus folder dari direktori kerja. "
                "Gunakan ini ketika user meminta menghapus folder/direktori. "
                "Secara default hanya bisa menghapus folder kosong. "
                "Jika folder berisi file/folder lain, gunakan recursive=true untuk menghapus semuanya."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "foldername": {
                        "type": "string",
                        "description": "Nama folder yang ingin dihapus, misalnya 'temp' atau 'backup/old'."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": (
                            "Jika true, menghapus folder beserta semua isinya secara rekursif. "
                            "Jika false (default), hanya menghapus jika folder kosong."
                        ),
                        "default": False
                    }
                },
                "required": ["foldername"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_all",
            "description": (
                "Menampilkan semua file dan folder di direktori kerja dalam format tree/struktur. "
                "Gunakan ini ketika user ingin melihat struktur direktori secara lengkap, "
                "termasuk isi subfolder. Menampilkan ukuran file dan jumlah item dalam folder."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "max_depth": {
                        "type": "integer",
                        "description": (
                            "Kedalaman maksimal folder yang ditampilkan. "
                            "Default: 3. Gunakan angka yang lebih kecil untuk tampilan lebih ringkas."
                        ),
                        "default": 3
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "exec_command",
            "description": (
                "Menjalankan perintah terminal (bash/shell) di local device pengguna. "
                "Gunakan ini ketika user meminta untuk menjalankan perintah sistem, "
                "misalnya: ls, pwd, whoami, df -h, ps aux, ping, cat, grep, find, dll. "
                "Perintah dijalankan dari direktori kerja agent. "
                "Output (stdout dan stderr) dikembalikan sebagai hasil. "
                "Beberapa perintah berbahaya diblokir untuk keamanan (misalnya rm -rf /, format, dll). "
                "Untuk perintah interaktif, gunakan timeout yang sesuai."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "Perintah terminal yang ingin dijalankan, misalnya 'ls -la', "
                            "'pwd', 'whoami', 'df -h', 'ps aux', 'cat /etc/os-release', "
                            "'ping -c 3 google.com', 'find . -name *.py', dll."
                        )
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "Timeout dalam detik untuk eksekusi perintah. "
                            "Default: 60 detik. Untuk perintah yang membutuhkan waktu lama "
                            "(misalnya download, compile), gunakan nilai yang lebih besar."
                        ),
                        "default": 60
                    }
                },
                "required": ["command"]
            }
        }
    }
]

# ============================================================
# IMPLEMENTASI TOOLS (dieksekusi secara lokal)
# ============================================================

def tool_read_file(filename: str) -> str:
    path = _safe_path(filename)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(path):
        return f"Error: File '{filename}' tidak ditemukan."
    if not os.path.isfile(path):
        return f"Error: '{filename}' bukan file."
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content if content else "(file kosong)"
    except Exception as e:
        return f"Error membaca file: {e}"


def tool_write_file(filename: str, content: str) -> str:
    path = _safe_path(filename)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    try:
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{filename}' berhasil disimpan ({len(content)} karakter)."
    except Exception as e:
        return f"Error menulis file: {e}"


def tool_edit_file(filename: str, operation: str, new_text: str, old_text: str = None) -> str:
    """
    Mengedit isi file teks yang sudah ada.
    
    Mode operasi:
    - replace: mengganti old_text dengan new_text
    - append: menambah new_text di akhir file
    - prepend: menambah new_text di awal file
    """
    path = _safe_path(filename)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(path):
        return f"Error: File '{filename}' tidak ditemukan."
    if not os.path.isfile(path):
        return f"Error: '{filename}' bukan file."
    
    try:
        # Baca isi file saat ini
        with open(path, "r", encoding="utf-8") as f:
            current_content = f.read()
        
        if operation == "replace":
            if old_text is None:
                return "Error: Parameter 'old_text' diperlukan untuk operasi 'replace'."
            if old_text not in current_content:
                return f"Error: Teks '{old_text[:50]}{'...' if len(old_text) > 50 else ''}' tidak ditemukan dalam file '{filename}'."
            new_content = current_content.replace(old_text, new_text, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"File '{filename}' berhasil diedit (replace: '{old_text[:30]}...' → '{new_text[:30]}...')."
        
        elif operation == "append":
            with open(path, "a", encoding="utf-8") as f:
                f.write(new_text)
            return f"File '{filename}' berhasil diedit (append: {len(new_text)} karakter ditambahkan di akhir)."
        
        elif operation == "prepend":
            new_content = new_text + current_content
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return f"File '{filename}' berhasil diedit (prepend: {len(new_text)} karakter ditambahkan di awal)."
        
        else:
            return f"Error: Operasi '{operation}' tidak dikenal. Gunakan: replace, append, prepend."
    
    except Exception as e:
        return f"Error mengedit file: {e}"


def tool_list_files() -> str:
    try:
        files = [
            f for f in os.listdir(BASE_DIR)
            if os.path.isfile(os.path.join(BASE_DIR, f))
        ]
        if not files:
            return "Direktori kosong, tidak ada file."
        return "File di direktori kerja:\n" + "\n".join(f"  - {f}" for f in sorted(files))
    except Exception as e:
        return f"Error membaca direktori: {e}"


def tool_delete_file(filename: str) -> str:
    path = _safe_path(filename)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(path):
        return f"Error: File '{filename}' tidak ditemukan."
    if not os.path.isfile(path):
        return f"Error: '{filename}' bukan file. Gunakan delete_folder untuk menghapus folder."
    try:
        os.remove(path)
        return f"File '{filename}' berhasil dihapus."
    except Exception as e:
        return f"Error menghapus file: {e}"


def tool_copy_file(source: str, destination: str) -> str:
    src_path = _safe_path(source)
    dst_path = _safe_path(destination)
    if src_path is None or dst_path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(src_path):
        return f"Error: File sumber '{source}' tidak ditemukan."
    if not os.path.isfile(src_path):
        return f"Error: '{source}' bukan file. Tidak bisa menyalin folder."
    try:
        dst_parent = os.path.dirname(dst_path)
        if dst_parent and not os.path.exists(dst_parent):
            os.makedirs(dst_parent, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        size = os.path.getsize(dst_path)
        return f"File '{source}' berhasil disalin ke '{destination}' ({_format_size(size)})."
    except Exception as e:
        return f"Error menyalin file: {e}"


def tool_move_file(source: str, destination: str) -> str:
    src_path = _safe_path(source)
    dst_path = _safe_path(destination)
    if src_path is None or dst_path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(src_path):
        return f"Error: File/folder sumber '{source}' tidak ditemukan."
    try:
        dst_parent = os.path.dirname(dst_path)
        if dst_parent and not os.path.exists(dst_parent):
            os.makedirs(dst_parent, exist_ok=True)
        shutil.move(src_path, dst_path)
        return f"'{source}' berhasil dipindahkan/direname ke '{destination}'."
    except Exception as e:
        return f"Error memindahkan file: {e}"


def tool_get_file_info(name: str) -> str:
    path = _safe_path(name)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(path):
        return f"Error: '{name}' tidak ditemukan."
    try:
        stat_info = os.stat(path)
        is_file = os.path.isfile(path)
        is_dir = os.path.isdir(path)

        info_lines = [
            f"Info: {name}",
            f"  Path      : {path}",
            f"  Tipe      : {'File' if is_file else 'Folder'}",
        ]

        if is_file:
            info_lines.append(f"  Ukuran    : {_format_size(stat_info.st_size)} ({stat_info.st_size} bytes)")
        elif is_dir:
            try:
                items = os.listdir(path)
                file_count = sum(1 for i in items if os.path.isfile(os.path.join(path, i)))
                dir_count = sum(1 for i in items if os.path.isdir(os.path.join(path, i)))
                info_lines.append(f"  Isi       : {file_count} file, {dir_count} folder ({len(items)} total)")
            except PermissionError:
                info_lines.append(f"  Isi       : (tidak bisa membaca - izin ditolak)")

        info_lines.extend([
            f"  Dibuat    : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_ctime))}",
            f"  Dimodif   : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_mtime))}",
            f"  Diakses   : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat_info.st_atime))}",
        ])

        mode = stat_info.st_mode
        perms = stat.filemode(mode) if hasattr(stat, 'filemode') else oct(mode)[-3:]
        info_lines.append(f"  Izin      : {perms}")

        return "\n".join(info_lines)
    except Exception as e:
        return f"Error mendapatkan info: {e}"


def tool_create_folder(foldername: str) -> str:
    path = _safe_path(foldername)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if os.path.exists(path):
        if os.path.isdir(path):
            return f"Error: Folder '{foldername}' sudah ada."
        else:
            return f"Error: '{foldername}' sudah ada sebagai file, bukan folder."
    try:
        os.makedirs(path, exist_ok=False)
        return f"Folder '{foldername}' berhasil dibuat."
    except Exception as e:
        return f"Error membuat folder: {e}"


def tool_delete_folder(foldername: str, recursive: bool = False) -> str:
    path = _safe_path(foldername)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(path):
        return f"Error: Folder '{foldername}' tidak ditemukan."
    if not os.path.isdir(path):
        return f"Error: '{foldername}' bukan folder. Gunakan delete_file untuk menghapus file."
    try:
        if recursive:
            file_count = 0
            dir_count = 0
            for root, dirs, files in os.walk(path):
                file_count += len(files)
                dir_count += len(dirs)
            shutil.rmtree(path)
            return (
                f"Folder '{foldername}' berhasil dihapus beserta isinya "
                f"({file_count} file, {dir_count} subfolder)."
            )
        else:
            os.rmdir(path)
            return f"Folder '{foldername}' berhasil dihapus."
    except OSError as e:
        if "Directory not empty" in str(e) or "tidak kosong" in str(e).lower():
            return (
                f"Error: Folder '{foldername}' tidak kosong. "
                f"Gunakan recursive=true untuk menghapus beserta isinya."
            )
        return f"Error menghapus folder: {e}"
    except Exception as e:
        return f"Error menghapus folder: {e}"


def tool_list_all(max_depth: int = 3) -> str:
    try:
        lines = [f"Struktur Direktori: {BASE_DIR}"]

        def _walk(current_path: str, prefix: str, current_depth: int):
            if current_depth > max_depth:
                lines.append(f"{prefix}  ... (kedalaman maksimum tercapai)")
                return
            try:
                entries = sorted(os.listdir(current_path))
            except PermissionError:
                lines.append(f"{prefix}  (tidak bisa membaca - izin ditolak)")
                return

            dirs = [e for e in entries if os.path.isdir(os.path.join(current_path, e))]
            files = [e for e in entries if os.path.isfile(os.path.join(current_path, e))]

            for d in dirs:
                dir_path = os.path.join(current_path, d)
                try:
                    item_count = len(os.listdir(dir_path))
                    lines.append(f"{prefix}📁 {d}/ ({item_count} item)")
                except PermissionError:
                    lines.append(f"{prefix}📁 {d}/ (izin ditolak)")
                _walk(dir_path, prefix + "│   ", current_depth + 1)

            for f in files:
                file_path = os.path.join(current_path, f)
                try:
                    size = os.path.getsize(file_path)
                    lines.append(f"{prefix}📄 {f} ({_format_size(size)})")
                except OSError:
                    lines.append(f"{prefix}📄 {f}")

        _walk(BASE_DIR, "  ", 1)

        total_files = sum(1 for _, _, files in os.walk(BASE_DIR) for _ in files)
        total_dirs = sum(1 for _, dirs, _ in os.walk(BASE_DIR) for _ in dirs)
        lines.append(f"\n  Total: {total_dirs} folder, {total_files} file")

        return "\n".join(lines)
    except Exception as e:
        return f"Error membaca struktur direktori: {e}"


def tool_exec_command(command: str, timeout: int = 60) -> str:
    block_reason = _is_command_blocked(command)
    if block_reason:
        return f"Error Keamanan: {block_reason}"

    try:
        is_windows = sys.platform == "win32"

        if is_windows:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=BASE_DIR,
                env=os.environ.copy(),
            )
        else:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=BASE_DIR,
                env=os.environ.copy(),
            )

        output_parts = []

        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(f"[stderr] {result.stderr}")

        if result.returncode != 0:
            output_parts.append(f"\n[Exit code: {result.returncode}]")

        if not output_parts:
            return "(perintah dijalankan, tidak ada output)"

        return "\n".join(output_parts).strip()

    except subprocess.TimeoutExpired:
        return f"Error: Perintah melebihi batas waktu {timeout} detik (timeout). Coba tambahkan timeout parameter."
    except FileNotFoundError:
        return f"Error: Perintah tidak ditemukan. Pastikan command yang dimasukkan valid."
    except PermissionError:
        return f"Error: Izin ditolak. Tidak memiliki akses untuk menjalankan perintah tersebut."
    except Exception as e:
        return f"Error menjalankan perintah: {e}"


def execute_tool(name: str, arguments: dict) -> str:
    if name == "read_file":
        result = tool_read_file(arguments["filename"])
    elif name == "write_file":
        result = tool_write_file(arguments["filename"], arguments["content"])
    elif name == "edit_file":
        operation = arguments["operation"]
        new_text = arguments["new_text"]
        old_text = arguments.get("old_text")
        result = tool_edit_file(arguments["filename"], operation, new_text, old_text)
    elif name == "list_files":
        result = tool_list_files()
    elif name == "delete_file":
        result = tool_delete_file(arguments["filename"])
    elif name == "copy_file":
        result = tool_copy_file(arguments["source"], arguments["destination"])
    elif name == "move_file":
        result = tool_move_file(arguments["source"], arguments["destination"])
    elif name == "get_file_info":
        result = tool_get_file_info(arguments["name"])
    elif name == "create_folder":
        result = tool_create_folder(arguments["foldername"])
    elif name == "delete_folder":
        recursive = arguments.get("recursive", False)
        result = tool_delete_folder(arguments["foldername"], recursive)
    elif name == "list_all":
        max_depth = arguments.get("max_depth", 3)
        result = tool_list_all(max_depth)
    elif name == "exec_command":
        timeout = arguments.get("timeout", DEFAULT_CMD_TIMEOUT)
        result = tool_exec_command(arguments["command"], timeout)
    else:
        result = f"Error: Tool '{name}' tidak dikenal."
    return result


# ============================================================
# FUNGSI API (DENGAN RETRY)
# ============================================================

def chat(messages: list, temperature: float = 0.7, max_tokens: int = 2000,
         max_retries: int = MAX_RETRIES, retry_base_delay: float = RETRY_BASE_DELAY) -> dict:
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_error = None

    for attempt in range(1, max_retries + 1):
        # Spinner animasi berjalan selama menunggu respons API.
        _spinner.start()
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise Exception(f"OpenRouter error: {data['error']}")
            return data

        except Exception as e:
            # Hentikan spinner SEBELUM mencetak pesan retry/error.
            _spinner.stop()
            # Klasifikasi pesan error agar tetap informatif tanpa duplikasi blok.
            if isinstance(e, requests.exceptions.HTTPError):
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:80]}"
            elif isinstance(e, requests.exceptions.ConnectionError):
                error_msg = f"Connection error: {str(e)[:80]}"
            elif isinstance(e, requests.exceptions.Timeout):
                error_msg = f"Request timeout: {str(e)[:80]}"
            elif isinstance(e, requests.exceptions.RequestException):
                error_msg = f"Request error: {str(e)[:80]}"
            else:
                error_msg = f"Unexpected error: {str(e)[:80]}"

            last_error = e
            if attempt < max_retries:
                delay = retry_base_delay * (2 ** (attempt - 1))
                show_retry(error_msg, attempt, max_retries, delay)
                time.sleep(delay)
            else:
                show_retry_giving_up(error_msg)

        finally:
            # Apapun hasilnya, hentikan spinner sebelum mencetak apa pun.
            _spinner.stop()

    raise last_error


def process_response(messages: list, data: dict) -> tuple:
    """
    Agentic loop — model dapat memanggil tools secara berantai (multi-step)
    dalam satu prompt hingga ia selesai dan mengembalikan teks akhir.

    Round UNLIMITED — tidak ada batas maksimum.
    Agent berhenti jika:
      1. Model selesai (tidak ada tool_calls)
      2. User mengetik 'q' untuk interupsi (setelah round saat ini selesai)

    PENTING: Narasi model (content) HANYA ditampilkan jika model juga
    memanggil tool_calls. Jika model langsung jawab tanpa tools,
    narasi tidak ditampilkan (langsung return jawaban).

    Returns: (teks_akhir, messages_updated, was_interrupted)
    """
    round_num = 0
    was_interrupted = False

    while True:  # ← UNLIMITED ROUNDS
        round_num += 1

        # ── Poll queue untuk deteksi 'q' real-time ──────────────
        _check_interrupt_nonblock()

        # ── Cek interrupt SEBELUM round dimulai ──────────────────
        if _is_interrupted():
            show_interrupt_notice()
            was_interrupted = True
            messages.append({
                "role": "user",
                "content": (
                    "[SYSTEM] User telah meminta interupsi (mengetik 'q'). "
                    "Proses kamu telah diinterupsi. "
                    "Harap selesaikan jawaban akhir kamu sekarang dengan ringkas "
                    "dan berikan status dari apa yang sudah berhasil dilakukan. "
                    "Jangan memanggil tool lagi."
                )
            })
            show_thinking()
            try:
                data = chat(messages, temperature=0.7, max_tokens=2000)
            except Exception as e:
                error_msg = f"Error saat interrupt: {e}"
                return error_msg, messages, True

            choice = data["choices"][0]
            message = choice["message"]
            messages.append(message)

            tool_calls = message.get("tool_calls")
            model_content = message.get("content")

            # Hanya tampilnarasi jika ada tool_calls
            if tool_calls and model_content and model_content.strip():
                show_model_narration(round_num, model_content)

            if not tool_calls:
                return message.get("content", ""), messages, True
            else:
                # Model masih memanggil tool — eksekusi lalu paksa jawaban akhir
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        tool_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}
                    result = execute_tool(tool_name, tool_args)
                    show_tool_call(tool_name, tool_args, result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result
                    })
                # Paksa model untuk memberikan jawaban akhir
                messages.append({
                    "role": "user",
                    "content": (
                        "[SYSTEM] User telah meminta interupsi. "
                        "Semua tool sudah dieksekusi. "
                        "Berikan jawaban akhir yang ringkas sekarang. "
                        "Jangan memanggil tool lagi."
                    )
                })
                show_thinking()
                try:
                    data = chat(messages, temperature=0.7, max_tokens=2000)
                except Exception as e:
                    return f"Error saat interrupt: {e}", messages, True
                choice = data["choices"][0]
                message = choice["message"]
                messages.append(message)
                return message.get("content", ""), messages, True

        # ── Normal round processing ───────────────────────────────
        choice  = data["choices"][0]
        message = choice["message"]

        messages.append(message)

        tool_calls = message.get("tool_calls")
        model_content = message.get("content")

        # ── Tampilkan narasi HANYA jika model memanggil tools ────
        # Jika tidak ada tool_calls, narasi tidak ditampilkan
        if tool_calls and model_content and model_content.strip():
            show_model_narration(round_num, model_content)

        # Tidak ada tool call → model sudah selesai, return langsung
        if not tool_calls:
            return message.get("content", ""), messages, was_interrupted

        # ── Eksekusi semua tool dalam round ini ──────────────────
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            try:
                tool_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError as e:
                tool_args = {}
                result = (
                    f"Error: Gagal parse arguments JSON untuk tool '{tool_name}'. "
                    f"Arguments: {tc['function']['arguments']}. "
                    f"JSON error: {e}. "
                    "Model harus mengirim arguments yang valid dalam format JSON."
                )
                show_tool_call(tool_name, {}, result)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })
                continue

            result = execute_tool(tool_name, tool_args)

            show_tool_call(tool_name, tool_args, result)

            # Jika tool error, tambahkan konteks agar model bisa retry
            if result.startswith("Error:"):
                result = (
                    f"{result}\n\n"
                    "⚠️ Tool call di atas GAGAL. "
                    "Silakan analisis penyebab error dan coba lagi dengan pendekatan yang berbeda. "
                    "Misalnya: periksa nama file, path, parameter, atau coba tool lain yang lebih sesuai. "
                    "Jangan mengulang tool yang sama dengan parameter yang sama jika sudah gagal."
                )

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result
            })

        # ── Cek interrupt SETELAH eksekusi tool, SEBELUM panggil API lagi ──
        if _is_interrupted():
            show_interrupt_notice()
            was_interrupted = True
            messages.append({
                "role": "user",
                "content": (
                    f"[SYSTEM] User telah meminta interupsi (menetik 'q'). "
                    f"Proses kamu telah diinterupsi setelah round {round_num}. "
                    f"Harap selesaikan jawaban akhir kamu sekarang dengan ringkas "
                    f"dan berikan status dari apa yang sudah berhasil dilakukan. "
                    f"Jangan memanggil tool lagi."
                )
            })
            show_thinking()
            try:
                data = chat(messages, temperature=0.7, max_tokens=2000)
            except Exception as e:
                return f"Error saat interrupt: {e}", messages, True
            continue

        # ── Panggil model lagi dengan semua hasil tool ───────────
        show_thinking()
        data = chat(messages, temperature=0.7, max_tokens=2000)


# ============================================================
# SYSTEM PROMPT
# ============================================================

def get_system_prompt(session_name: str = None) -> str:
    session_info = ""
    if session_name:
        session_info = (
            f"\n\n📌 SESSION INFO:\n"
            f"Nama session: {session_name}\n"
            f"Session tersimpan otomatis di folder 'sessions/'.\n"
            f"User bisa melihat daftar sesi dengan '/sessions', mulai sesi baru dengan '/new', "
            f"melihat riwayat dengan '/history', hapus sesi dengan '/delete-session <nama>', "
            f"dan rename sesi dengan '/rename-session <lama> <baru>'. "
            f"CLI command (dari terminal): python main.py listSessions, "
            f"python main.py deleteSession <nama>, "
            f"python main.py renameSession <lama> <baru>, "
            f"python main.py clearSessions (hapus semua session tanpa nama), "
            f"python main.py searchSessions <keyword> (cari session berdasarkan nama)."
        )

    return (
        "Kamu adalah Ruka AI, agent kura-kura (turtle) yang dapat mengelola file dan folder "
        "di direktori kerja pengguna, serta menjalankan perintah terminal (bash). "
        "Kamu memiliki kemampuan: membaca file, menulis file, menghapus file, "
        "menyalin file, memindahkan/rename file, membuat folder, menghapus folder, "
        "melihat info file/folder, melihat struktur direktori, dan "
        "menjalankan perintah terminal (bash/shell) di local device pengguna. "
        "Kamu BOLEH memanggil tools secara berantai dalam satu respons — "
        "misalnya: list_files dulu untuk tahu file apa yang ada, "
        "lalu read_file untuk membaca isinya, lalu write_file untuk mengedit, "
        "atau exec_command untuk menjalankan perintah sistem. "
        "Lakukan semua langkah yang diperlukan tanpa menunggu konfirmasi user "
        "kecuali diminta. Selalu konfirmasi hasil akhirnya. "
        "Jawab dalam Bahasa Indonesia.\n\n"
        "PENTING: Jangan menggunakan tabel markdown (| col | col |) karena tidak "
        "terformat dengan baik di terminal. Sebagai gantinya, gunakan format daftar "
        "dengan bullet point untuk menampilkan data terstruktur.\n\n"
        "Kamu adalah kura-kura yang bijaksana, sabar, dan teliti. "
        "Gunakan emoji 🐢 untuk menandai dirimu.\n\n"
        "══════════════════════════════════════════════════════════════\n"
        "📋 INSTRUKSI AWAL SESSION — BACA SEBELUM MULAI:\n"
        "══════════════════════════════════════════════════════════════\n"
        "Baca file 'SKILL/skills.md' menggunakan tool read_file untuk memahami:\n"
        "   - Daftar 12 tools yang tersedia dan cara menggunakannya\n"
        "   - Batasan keamanan dan path traversal protection\n"
        "   - Alur kerja agentic loop dan multi-step execution\n"
        "   - Panduan gaya komunikasi (Bahasa Indonesia + emoji 🐢)\n"
        "   - Tips & best practices untuk operasi file\n"
        "   - Daftar tool yang TIDAK ADA (jangan panggil)\n"
        "Setelah membaca skills.md, kamu akan memahami seluruh capabilities "
        "dan constraints tubuhmu sebelum mulai berinteraksi dengan user.\n"
        "══════════════════════════════════════════════════════════════"
        + session_info
    )


# ============================================================
# SESI CHAT INTERAKTIF
# ============================================================

def chat_session(session_name: str = None):
    # ── Load atau buat session ──────────────────────────────────
    messages = []
    session_meta = None
    is_new_session = True

    if session_name:
        # Coba load session yang sudah ada
        loaded_messages, session_meta = load_session(session_name)
        if loaded_messages is not None:
            messages = loaded_messages
            is_new_session = False
        else:
            # Session belum ada — buat baru dengan nama ini
            session_meta = None
            is_new_session = True
    else:
        # Tidak ada nama — generate otomatis
        session_name = _generate_session_name()
        is_new_session = True

    # ── Inisialisasi messages dengan system prompt ─────────────
    if not messages:
        messages = [
            {
                "role": "system",
                "content": get_system_prompt(session_name)
            }
        ]

    # ── Tampilan awal ──────────────────────────────────────────
    ruka_print()
    show_banner(session_name, session_meta, is_new=is_new_session)
    show_examples()

    # Mulai input reader thread sekali di awal
    _start_input_reader()

    # ── Loop utama ─────────────────────────────────────────────
    while True:
        _reset_interrupt()

        try:
            user_input = show_user_prompt(session_name)
        except (EOFError, KeyboardInterrupt):
            save_session(session_name, messages)
            show_exit(session_name)
            break

        if not user_input:
            continue

        # ── Perintah khusus session ─────────────────────────────
        if user_input.lower() in ("exit", "quit", "keluar"):
            save_session(session_name, messages)
            show_exit(session_name)
            break

        if user_input.lower() in ("/help", "/?"):
            show_help()
            continue

        if user_input.lower() in ("/clear", "/cls"):
            # Bersihkan layar lalu tampilkan ulang sapaan ringkas
            os.system("clear" if os.name != "nt" else "cls")
            ruka_print()
            continue

        if user_input.lower() == "/sessions":
            show_session_list()
            continue

        if user_input.lower() == "/new":
            # Simpan session saat ini, lalu buat baru
            save_session(session_name, messages)
            session_name = _generate_session_name()
            messages = [
                {
                    "role": "system",
                    "content": get_system_prompt(session_name)
                }
            ]
            print(f"\n  {Style.OK}✻{Style.RESET} {Style.GREY_LIGHT}Session baru dimulai:{Style.RESET} {Style.ACCENT}{session_name}{Style.RESET}")
            continue

        if user_input.lower() == "/history":
            show_session_history(messages, session_name)
            continue

        if user_input.lower().startswith("/delete-session"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2:
                print(f"\n  {Style.WARN}■{Style.RESET}  {Style.GREY}Gunakan: {Style.GREY_LIGHT}/delete-session <nama>{Style.RESET}")
            else:
                target_name = parts[1].strip()
                result = delete_session(target_name)
                ok = "berhasil" in result.lower()
                dot = Style.OK if ok else Style.ERR
                print(f"\n  {dot}⏺{Style.RESET} {Style.GREY_LIGHT}{result}{Style.RESET}")
            continue

        if user_input.lower().startswith("/rename-session"):
            parts = user_input.split(maxsplit=2)
            if len(parts) < 3:
                print(f"\n  {Style.WARN}■{Style.RESET}  {Style.GREY}Gunakan: {Style.GREY_LIGHT}/rename-session <lama> <baru>{Style.RESET}")
            else:
                old_name = parts[1].strip()
                new_name = parts[2].strip()
                result = rename_session(old_name, new_name)
                if old_name == session_name:
                    session_name = new_name
                ok = "berhasil" in result.lower()
                dot = Style.OK if ok else Style.ERR
                print(f"\n  {dot}⏺{Style.RESET} {Style.GREY_LIGHT}{result}{Style.RESET}")
            continue

        # ── Slash command tak dikenal → jangan kirim ke model ───
        if user_input.startswith("/"):
            cmd = user_input.split()[0]
            print(f"\n  {Style.WARN}■{Style.RESET}  {Style.GREY}Perintah {Style.GREY_LIGHT}{cmd}{Style.GREY} tidak dikenal. Ketik {Style.GREY_LIGHT}/help{Style.GREY} untuk daftar perintah.{Style.RESET}")
            continue

        # ── Normal chat flow ────────────────────────────────────
        show_separator()
        messages.append({"role": "user", "content": user_input})

        try:
            show_thinking()
            data = chat(messages)
            reply, messages, was_interrupted = process_response(messages, data)

            # Jawaban akhir asisten dengan marker ⏺ ala Claude Code
            _emit_agent_text(reply, interrupted=was_interrupted)

            if was_interrupted:
                print(f"\n  {Style.GREY}■ Sesi agent diinterupsi. Kembali ke prompt utama.{Style.RESET}")

            # Auto-save setelah setiap exchange
            save_session(session_name, messages)

        except Exception as e:
            show_error(str(e)[:80])
            # Tetap save meski error
            save_session(session_name, messages)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Pastikan folder sessions ada
    _ensure_sessions_dir()

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        # Cek apakah argumen adalah perintah session
        if arg in ("help", "--help", "-h"):
            # Mode: tampilkan help
            show_help()
        elif arg == "listSessions":
            # Mode: tampilkan daftar session
            show_session_list()
        elif arg == "deleteSession" and len(sys.argv) > 2:
            # Mode: hapus session dari CLI
            target = sys.argv[2]
            result = delete_session(target)
            print(result)
        elif arg == "renameSession" and len(sys.argv) > 3:
            # Mode: rename session dari CLI
            old_name = sys.argv[2]
            new_name = sys.argv[3]
            result = rename_session(old_name, new_name)
            print(result)
        elif arg == "clearSessions":
            # Mode: hapus semua session auto-generated (tanpa nama)
            result = clear_sessions()
            print(result)
        elif arg == "searchSessions" and len(sys.argv) > 2:
            # Mode: cari session berdasarkan keyword
            keyword = " ".join(sys.argv[2:])
            result = search_sessions(keyword)
            print(result)
        elif not arg.startswith("/"):
            # Mode: session dengan nama tertentu
            session_name = arg
            chat_session(session_name)
        else:
            # Single prompt mode (backward compatibility)
            prompt = " ".join(sys.argv[1:])
            _start_input_reader()
            print(f"\n{Style.ACCENT}❯{Style.RESET} {Style.GREY_LIGHT}{prompt}{Style.RESET}")
            msgs = [
                {
                    "role": "system",
                    "content": get_system_prompt()
                },
                {"role": "user", "content": prompt}
            ]
            try:
                data = chat(msgs)
                reply, _, was_interrupted = process_response(msgs, data)
                _emit_agent_text(reply, interrupted=was_interrupted)
                print()
            except Exception as e:
                show_error(str(e)[:80])
    else:
        # Mode interaktif tanpa nama session → auto-generate
        chat_session()