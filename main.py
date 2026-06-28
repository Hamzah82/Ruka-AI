"""
Ruka AI - OpenRouter Chat Client dengan Tool Use (File, Folder & Terminal Command)
AI Kura-Kura yang dapat membaca, menulis, menghapus, menyalin, memindahkan file,
mengelola folder, serta menjalankan perintah terminal (bash) di local device.
Output AI diformat dari markdown ke styled terminal text.

Workspace:
  Workspace (folder kerja AI) = folder TEMPAT user menjalankan perintah (cwd).
  Pasang alias `ruka` lewat ./install.sh, lalu `cd` ke folder mana pun dan
  ketik `ruka` — AI bekerja di folder itu. File internal (SKILL/, sessions/,
  .env) tetap dibaca dari folder instalasi, bukan dari workspace.

Session Management:
  python main.py                          → workspace = cwd, session nama timestamp
  python main.py <namaSesi>               → workspace = cwd, sesi dengan nama tertentu
  python main.py <workspacePath>           → override workspace ke path tertentu
  python main.py <workspacePath> <namaSesi> → session tertentu di workspace tertentu
  python main.py listSessions              → tampilkan daftar semua sesi (CLI)
  python main.py deleteSession <nama>      → hapus sesi tertentu (CLI)
  python main.py renameSession <lama> <baru> → rename sesi (CLI)
  python main.py clearSessions             → hapus semua session tanpa nama (CLI)
  python main.py searchSessions <keyword>   → cari session berdasarkan nama (CLI)
  /sessions                               → tampilkan daftar semua sesi (slash command)
  /new                                    → mulai sesi baru (slash command)
  /history                                → tampilkan riwayat chat sesi saat ini (slash command)
  /delete-session <nama>                  → hapus sesi tertentu (slash command)
  /rename-session <lama> <baru>           → rename sesi (slash command)
"""

import os
import re
import sys
import json
import shutil
import stat
import tempfile
import time
import random
import subprocess
import threading
import queue
import unicodedata
import readline
import select
import codecs
import atexit
import signal
import requests
from datetime import datetime
from dotenv import load_dotenv

# termios/tty hanya tersedia di Unix — dibutuhkan untuk floating prompt (raw mode).
# Di platform tanpa termios, floating prompt otomatis nonaktif (fallback linear).
try:
    import termios
    import tty
    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False

# Muat .env dari FOLDER main.py (folder instalasi), BUKAN dari cwd.
# Penting: sejak workspace = cwd tempat user memanggil `ruka`, user bisa
# berada di folder mana pun. API key tetap harus dibaca dari .env di folder
# instalasi, bukan dari folder kerja user yang acak.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ============================================================
# KONFIGURASI — dimuat dari config.py
# ============================================================
import config
from config import (
    OPENROUTER_API_KEY,
    MODEL,
    API_URL,
    HEADERS,
    BASE_DIR,
    SCRIPT_DIR,
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

# FooterUI aktif → prompt "❯" mengambang di bawah layar. None/disarmed → mode linear.
_footer = None


def _footer_active() -> bool:
    """True jika prompt mengambang sedang aktif."""
    return _footer is not None and _footer.armed


# ============================================================
# FLOATING PROMPT — footer tetap di bawah + scroll region (DECSTBM)
# ============================================================

class _RegionWriter:
    """
    Proxy stdout: setiap print() otomatis ditulis ke scroll region (di atas
    footer), lalu footer digambar ulang — semuanya atomik di bawah satu lock.
    Dengan ini semua print() yang sudah ada aman tanpa perlu disentuh.
    """

    def __init__(self, footer):
        self._footer = footer

    def write(self, text):
        if text:
            self._footer.write_output(text)
        return len(text) if text else 0

    def flush(self):
        try:
            self._footer._real.flush()
        except Exception:
            pass

    # Beberapa kode mungkin mengakses atribut stdout asli (mis. isatty).
    def __getattr__(self, name):
        return getattr(self._footer._real, name)


class FooterUI:
    """
    Mengelola footer mengambang di bawah layar memakai scroll region ANSI.

    Layout (1-indexed, H = tinggi terminal, L = jumlah baris input):
        baris H-1-L      : garis pemisah
        baris H-L        : status/spinner (saat memproses) atau hint (saat idle)
        baris H-L+1 .. H : "❯ <input>" — DI-WRAP ke L baris bila panjang
    Region scroll = baris 1..H-(2+L) — semua output AI bergulir di sini.
    Footer tinggi-variabel: L tumbuh saat input wrap, menyusut saat memendek.

    Aturan anti-bug:
      • SATU RLock menjaga setiap penulisan ke stdout (3 penulis: main/print,
        spinner, input thread).
      • Posisi konten disimpan di slot save-cursor terminal (DECSC \0337/DECRC
        \0338) — HANYA disentuh oleh write_output(). render() footer murni
        memakai positioning ABSOLUT (\033[r;cH), tak pernah save/restore,
        sehingga tidak ada drift kursor antar-thread.
    """

    RESERVED = 3  # baris dasar: pemisah + status + 1 baris input

    def __init__(self):
        self.lock = threading.RLock()
        self.armed = False
        self.H = 0
        self.W = 0
        self._status = ""
        self._buffer = ""
        self._cursor = 0
        # Jumlah baris footer SAAT INI (tinggi-variabel: tumbuh saat input wrap
        # ke beberapa baris). Selalu = 2 (pemisah+status) + jumlah baris input.
        self._reserved = self.RESERVED
        self._resized = False
        self._real = sys.stdout
        self._prev_stdout = None
        self._fd = None
        self._saved_termios = None
        self._idle_hint = ""

    # ── Util lebar karakter (sadar lebar-ganda) ──────────────
    @staticmethod
    def _char_w(ch: str) -> int:
        if unicodedata.combining(ch) or ch == "️":
            return 0
        return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1

    def _size_ok(self) -> bool:
        # Butuh minimal 2 baris konten + RESERVED baris footer, dan lebar wajar.
        return self.H >= (self.RESERVED + 2) and self.W >= 10

    def _read_size(self):
        size = shutil.get_terminal_size(fallback=(80, 24))
        self.H, self.W = size.lines, size.columns

    # ── Lifecycle ────────────────────────────────────────────
    def arm(self, idle_hint: str = "") -> bool:
        """Aktifkan footer mengambang. Return False bila tak memungkinkan."""
        if self.armed:
            return True
        if not _HAS_TERMIOS:
            return False
        try:
            if not (sys.stdout.isatty() and sys.stdin.isatty()):
                return False
        except Exception:
            return False
        self._read_size()
        if not self._size_ok():
            return False

        self._idle_hint = idle_hint
        self._status = idle_hint
        self._real = sys.stdout
        self._fd = sys.stdin.fileno()

        # Masuk raw mode (canonical/echo/signal off) TAPI biarkan OPOST (output)
        # tetap aktif agar "\n" pada print() tetap berfungsi normal.
        try:
            self._saved_termios = termios.tcgetattr(self._fd)
            new = termios.tcgetattr(self._fd)
            new[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG | termios.IEXTEN)
            new[0] &= ~(termios.IXON | termios.ICRNL | termios.INLCR | termios.IGNCR)
            new[6][termios.VMIN] = 1
            new[6][termios.VTIME] = 0
            termios.tcsetattr(self._fd, termios.TCSADRAIN, new)
        except Exception:
            self._saved_termios = None
            return False

        with self.lock:
            self._reserved = self.RESERVED
            # Pesan baris dasar di bawah untuk footer.
            self._emit("\n" * self._reserved)
            self._emit("\033[?2004h")                      # bracketed paste on
            self._set_region()
            # Seed posisi konten di baris konten terbawah (chat: terbaru di bawah).
            self._emit(f"\033[{self.H - self._reserved};1H")
            self._emit("\0337")                            # simpan posisi konten
            self._render_locked()
            self.armed = True

        # Pasang handler resize + jaring pengaman teardown.
        try:
            signal.signal(signal.SIGWINCH, self._on_sigwinch)
        except (ValueError, AttributeError, OSError):
            pass
        atexit.register(self.disarm)

        # Alihkan semua print() ke region.
        self._prev_stdout = sys.stdout
        sys.stdout = _RegionWriter(self)
        return True

    def disarm(self):
        """Kembalikan terminal ke keadaan normal. Idempotent."""
        with self.lock:
            if not self.armed:
                return
            self.armed = False
            # Pulihkan stdout asli.
            try:
                if self._prev_stdout is not None:
                    sys.stdout = self._prev_stdout
            except Exception:
                pass
            try:
                self._emit("\033[r")                       # reset scroll region
                self._emit(f"\033[{self.H};1H")            # ke baris paling bawah
                self._emit("\033[?2004l")                  # bracketed paste off
                self._emit("\033[?25h")                    # tampilkan kursor
                self._emit("\n")
            except Exception:
                pass
        # Pulihkan termios.
        if self._saved_termios is not None and self._fd is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved_termios)
            except Exception:
                pass
        try:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)
        except (ValueError, AttributeError, OSError):
            pass

    # ── Primitif tulis ───────────────────────────────────────
    def _emit(self, seq: str):
        """Tulis langsung ke stdout asli (pemanggil HARUS memegang lock)."""
        try:
            self._real.write(seq)
            self._real.flush()
        except Exception:
            pass

    def _set_region(self):
        self._emit(f"\033[1;{self.H - self._reserved}r")

    # ── Output AI → region di atas footer ────────────────────
    def write_output(self, text: str):
        with self.lock:
            if not self.armed:
                # Belum/again tidak aktif → tulis apa adanya.
                self._emit(text)
                return
            # Deteksi resize secara langsung (TIOCGWINSZ) dan via flag SIGWINCH.
            # Pengecekan langsung menangkap jendela sempit di mana terminal sudah
            # berubah ukuran tapi SIGWINCH belum terkirim — dalam kasus itu self.H
            # masih basi sehingga footer dirender di baris yang salah (masuk content).
            # Beberapa terminal (alacritty, wezterm) juga mereset scroll region saat
            # resize, jadi _set_region() selalu dipanggil sebelum menulis.
            size = shutil.get_terminal_size(fallback=(self.W, self.H))
            if self._resized or size.lines != self.H or size.columns != self.W:
                self._resized = False
                if not self._apply_resize():
                    # Terminal terlalu kecil; tulis apa adanya, skip region.
                    self._emit(text)
                    return
            self._emit("\033[?25l")        # sembunyikan kursor saat menulis
            self._set_region()             # pastikan region valid (terminal bisa reset saat resize)
            self._emit("\0338")            # kembali ke posisi konten
            self._real.write(text)         # mengalir alami di dalam region
            self._real.flush()
            self._emit("\0337")            # simpan posisi konten baru
            self._render_locked()

    # ── Render footer (positioning absolut, tanpa save/restore) ──
    def _truncate(self, text: str, max_cols: int) -> str:
        """Potong text (sadar ANSI & lebar-ganda) agar muat max_cols kolom."""
        if max_cols <= 0:
            return ""
        out = []
        cols = 0
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "\033":  # lewati sekuens ANSI utuh (tak menambah kolom)
                j = text.find("m", i)
                if j == -1:
                    break
                out.append(text[i:j + 1])
                i = j + 1
                continue
            w = self._char_w(ch)
            if cols + w > max_cols:
                break
            out.append(ch)
            cols += w
            i += 1
        return "".join(out)

    def _wrap_input(self):
        """
        Pecah buffer input jadi beberapa baris (wrap berdasarkan lebar tampil,
        sadar lebar-ganda) — BUKAN geser horizontal. Setiap baris muat dalam
        (W-3) kolom. Return (lines, cursor_row, cursor_col_dalam_teks).
        """
        text_cols = max(1, self.W - 3)         # kolom teks per baris (prefix 2 kol)
        buf = self._buffer
        lines = []
        seg = []
        seg_w = 0
        counts = []                            # jumlah karakter tiap baris selesai
        for ch in buf:
            w = self._char_w(ch)
            if seg and seg_w + w > text_cols:
                lines.append("".join(seg))
                counts.append(len(seg))
                seg = []
                seg_w = 0
            seg.append(ch)
            seg_w += w
        lines.append("".join(seg))
        counts.append(len(seg))

        # Posisi kursor → (baris, kolom teks)
        cur = max(0, min(self._cursor, len(buf)))
        row = 0
        rem = cur
        while row < len(counts) and rem > counts[row]:
            rem -= counts[row]
            row += 1
        if row >= len(lines):
            row = len(lines) - 1
            rem = counts[row] if counts else 0
        col = sum(self._char_w(c) for c in lines[row][:rem])
        # Jika kursor tepat di ujung baris penuh → pindah ke awal baris berikut.
        if col >= text_cols and rem == len(lines[row]):
            if row + 1 < len(lines):
                row += 1
                col = 0
            elif cur == len(buf):
                lines.append("")
                row += 1
                col = 0
        return lines, row, col

    def _resize_reserved(self, new_reserved: int):
        """
        Ubah jumlah baris footer (tinggi-variabel). Saat tumbuh, konten digulung
        ke atas agar tidak tertutup; posisi konten (slot DECSC) dikoreksi.
        Pemanggil HARUS memegang lock.
        """
        old = self._reserved
        delta = new_reserved - old
        if delta == 0:
            return
        if delta > 0:
            # Bersihkan baris footer lama agar tidak jadi "sampah" konten saat scroll.
            for r in range(self.H - old + 1, self.H + 1):
                self._emit(f"\033[{r};1H\033[2K")
            self._emit("\033[r")                       # region penuh sementara
            self._emit(f"\033[{self.H};1H")            # baris terbawah
            self._emit("\n" * delta)                   # gulung seluruh layar naik
            # Posisi konten ikut naik delta → koreksi slot simpan.
            self._emit("\0338")                        # ke posisi konten (basi, delta kebawah)
            self._emit(f"\033[{delta}A")               # naik delta → posisi benar
            self._emit("\0337")                        # simpan ulang
            self._reserved = new_reserved
            self._set_region()
        else:
            # Menyusut: perluas region ke bawah, bersihkan baris footer lama
            # yang kini jadi area konten.
            self._reserved = new_reserved
            self._set_region()
            for r in range(self.H - old + 1, self.H - new_reserved + 1):
                self._emit(f"\033[{r};1H\033[2K")

    def _render_locked(self):
        """
        Gambar footer (tinggi-variabel) secara absolut. Pemanggil memegang lock.
        Input panjang DI-WRAP ke beberapa baris (footer tumbuh ke atas), bukan
        digeser horizontal.
        """
        if not (self.armed or self._fd is not None):
            return
        if self.H < self.RESERVED + 1:
            return

        lines, crow, ccol = self._wrap_input()
        # Batasi tinggi input agar selalu sisa >=2 baris konten (reserved<=H-2).
        cap = max(1, self.H - 4)
        if len(lines) > cap:
            drop = len(lines) - cap
            lines = lines[drop:]
            crow = max(0, crow - drop)
        L = len(lines)

        new_reserved = 2 + L
        if new_reserved != self._reserved:
            self._resize_reserved(new_reserved)

        sep_row = self.H - 1 - L
        status_row = self.H - L
        sep = self._truncate(_rule(self.W), self.W)
        status = self._truncate("  " + (self._status or ""), self.W)
        text_cols = max(1, self.W - 3)
        R = Style.RESET

        out = ["\033[?25l", "\033[?7l"]         # hide cursor, autowrap off
        out.append(f"\033[{sep_row};1H\033[2K{sep}{R}")
        out.append(f"\033[{status_row};1H\033[2K{status}{R}")
        for i, ln in enumerate(lines):
            row = self.H - L + 1 + i
            prefix = f"{Style.ACCENT}❯{R} " if i == 0 else "  "
            body = self._truncate(ln, text_cols)
            out.append(f"\033[{row};1H\033[2K{prefix}{body}{R}")
        # Kursor di posisi (baris,kolom) hasil wrap; teks mulai kolom 3.
        crow = max(0, min(crow, L - 1))
        cur_row = self.H - L + 1 + crow
        cur_col = min(3 + ccol, self.W)
        out.append(f"\033[{cur_row};{cur_col}H")
        out.append("\033[?7h")                  # autowrap on lagi
        out.append("\033[?25h")                 # show cursor
        self._emit("".join(out))

    # ── API publik (dipanggil spinner / editor) ──────────────
    def set_status(self, text: str):
        with self.lock:
            self._status = text
            if self.armed:
                self._render_locked()

    def set_idle(self):
        self.set_status(self._idle_hint)

    def set_input(self, buffer: str, cursor: int):
        with self.lock:
            self._buffer = buffer
            self._cursor = cursor
            if self.armed:
                self._render_locked()

    def clear_region(self):
        """/clear: bersihkan layar tapi pertahankan footer & region."""
        with self.lock:
            if not self.armed:
                return
            self._reserved = self.RESERVED    # kembali ke tinggi dasar
            self._emit("\033[r")              # reset region sementara
            self._emit("\033[2J\033[H")       # bersihkan layar
            self._set_region()
            self._emit("\033[1;1H")           # konten mulai dari atas
            self._emit("\0337")
            self._render_locked()

    # ── Resize ───────────────────────────────────────────────
    def _on_sigwinch(self, signum, frame):
        # Hanya set flag; reflow dilakukan di luar handler (di bawah lock).
        self._resized = True

    def _apply_resize(self) -> bool:
        """
        Bersihkan footer lama, baca ukuran baru, pasang ulang region & simpan
        posisi konten. Pemanggil HARUS memegang lock.
        Return True bila berhasil; False bila terminal terlalu kecil.
        """
        old_H = self.H
        old_reserved = self._reserved
        self._read_size()
        if not self._size_ok():
            return False
        # Reset region ke penuh sementara, lalu hapus baris footer lama.
        # Ini krusial saat terminal membesar: baris footer lama kini masuk ke
        # scroll-region baru dan akan muncul sebagai "ghost" di output AI.
        self._emit("\033[r")
        for r in range(max(1, old_H - old_reserved + 1), old_H + 1):
            self._emit(f"\033[{r};1H\033[2K")
        # Pasang ulang reserved dasar, region baru, posisi konten tersimpan.
        self._reserved = self.RESERVED
        self._set_region()
        self._emit(f"\033[{self.H - self._reserved};1H")
        self._emit("\0337")
        return True

    def check_resize(self):
        if not self._resized:
            return
        with self.lock:
            self._resized = False
            if not self.armed:
                return
            if self._apply_resize():
                self._render_locked()


# ============================================================
# RAW-MODE LINE EDITOR — prompt "❯" yang bisa diketik kapan pun
# ============================================================

class _LineEditor:
    """
    Editor satu-baris di footer: membaca byte mentah, merakit UTF-8 secara
    inkremental, dan mendukung navigasi (panah, history, Home/End, Ctrl-A/E/U/W).
    Pada Enter → kirim baris ke _input_queue (kontrak antrian/interrupt lama).
    """

    def __init__(self):
        self.buf = ""
        self.cur = 0
        self.history = []
        self.hist_idx = None       # None = sedang di baris aktif
        self.saved_line = ""       # simpan baris saat mulai menelusuri history
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.pending = b""         # sekuens escape yang belum lengkap
        self.paste = False

    def _sync(self):
        if _footer is not None:
            _footer.set_input(self.buf, self.cur)

    # ── Mutasi buffer ────────────────────────────────────────
    def _insert(self, s: str):
        if not s:
            return
        # Dalam mode paste, ubah newline jadi spasi (prompt satu baris).
        if self.paste:
            s = s.replace("\r", " ").replace("\n", " ")
        self.buf = self.buf[:self.cur] + s + self.buf[self.cur:]
        self.cur += len(s)

    def _backspace(self):
        if self.cur > 0:
            self.buf = self.buf[:self.cur - 1] + self.buf[self.cur:]
            self.cur -= 1

    def _delete(self):
        if self.cur < len(self.buf):
            self.buf = self.buf[:self.cur] + self.buf[self.cur + 1:]

    def _kill_to_start(self):
        self.buf = self.buf[self.cur:]
        self.cur = 0

    def _kill_word(self):
        i = self.cur
        while i > 0 and self.buf[i - 1] == " ":
            i -= 1
        while i > 0 and self.buf[i - 1] != " ":
            i -= 1
        self.buf = self.buf[:i] + self.buf[self.cur:]
        self.cur = i

    # ── History ──────────────────────────────────────────────
    def _hist_prev(self):
        if not self.history:
            return
        if self.hist_idx is None:
            self.saved_line = self.buf
            self.hist_idx = len(self.history)
        if self.hist_idx > 0:
            self.hist_idx -= 1
            self.buf = self.history[self.hist_idx]
            self.cur = len(self.buf)

    def _hist_next(self):
        if self.hist_idx is None:
            return
        self.hist_idx += 1
        if self.hist_idx >= len(self.history):
            self.hist_idx = None
            self.buf = self.saved_line
        else:
            self.buf = self.history[self.hist_idx]
        self.cur = len(self.buf)

    # ── Submit / EOF ─────────────────────────────────────────
    def _submit(self):
        line = self.buf
        self.buf = ""
        self.cur = 0
        self.hist_idx = None
        self.decoder.reset()
        if line.strip():
            if not self.history or self.history[-1] != line:
                self.history.append(line)
        _input_queue.put(line)
        self._sync()

    def _eof(self):
        _input_queue.put(None)

    # ── Parser byte ──────────────────────────────────────────
    def feed(self, data: bytes):
        data = self.pending + data
        self.pending = b""
        i = 0
        n = len(data)
        changed = False
        while i < n:
            b = data[i]
            if b == 0x1b:  # ESC → sekuens
                action, consumed, incomplete = self._parse_escape(data, i)
                if incomplete:
                    self.pending = data[i:]
                    break
                i += consumed
                if action:
                    if self._apply_action(action):
                        changed = True
                continue
            if self.paste:
                # Dalam paste: semua byte non-ESC = teks literal.
                ch = self.decoder.decode(bytes([b]))
                if ch:
                    self._insert(ch)
                    changed = True
                i += 1
                continue
            if b in (0x0d, 0x0a):          # Enter
                self._submit()
                changed = False
                i += 1
                continue
            if b in (0x7f, 0x08):          # Backspace
                self._backspace(); changed = True; i += 1; continue
            if b == 0x03:                  # Ctrl-C → keluar (seperti EOF lama)
                self._eof(); i += 1; continue
            if b == 0x04:                  # Ctrl-D
                if not self.buf:
                    self._eof()
                else:
                    self._delete(); changed = True
                i += 1; continue
            if b == 0x01:                  # Ctrl-A → awal
                self.cur = 0; changed = True; i += 1; continue
            if b == 0x05:                  # Ctrl-E → akhir
                self.cur = len(self.buf); changed = True; i += 1; continue
            if b == 0x15:                  # Ctrl-U → hapus ke awal
                self._kill_to_start(); changed = True; i += 1; continue
            if b == 0x17:                  # Ctrl-W → hapus kata
                self._kill_word(); changed = True; i += 1; continue
            if b < 0x20:                   # kontrol lain → abaikan
                i += 1; continue
            # Teks (termasuk UTF-8 multibyte: byte >= 0x80 dirakit decoder).
            ch = self.decoder.decode(bytes([b]))
            if ch:
                self._insert(ch); changed = True
            i += 1
        if changed:
            self._sync()

    def _apply_action(self, action: str) -> bool:
        if action == "left":
            if self.cur > 0:
                self.cur -= 1
            return True
        if action == "right":
            if self.cur < len(self.buf):
                self.cur += 1
            return True
        if action == "up":
            self._hist_prev(); return True
        if action == "down":
            self._hist_next(); return True
        if action == "home":
            self.cur = 0; return True
        if action == "end":
            self.cur = len(self.buf); return True
        if action == "delete":
            self._delete(); return True
        if action == "paste_start":
            self.paste = True; return False
        if action == "paste_end":
            self.paste = False; return False
        return False

    def _parse_escape(self, data: bytes, i: int):
        """Return (action|None, consumed, incomplete) untuk sekuens mulai di data[i]==ESC."""
        n = len(data)
        if i + 1 >= n:
            return None, 0, True
        c1 = data[i + 1]
        if c1 == ord('['):  # CSI
            j = i + 2
            params = b""
            while j < n:
                c = data[j]
                if 0x40 <= c <= 0x7e:      # byte final
                    final = chr(c)
                    seq = params.decode("ascii", "replace")
                    return self._csi_action(final, seq), (j - i + 1), False
                params += bytes([c])
                j += 1
            return None, 0, True           # belum lengkap
        if c1 == ord('O'):  # SS3 (mode aplikasi kursor)
            if i + 2 >= n:
                return None, 0, True
            final = chr(data[i + 2])
            mapping = {"A": "up", "B": "down", "C": "right", "D": "left",
                       "H": "home", "F": "end"}
            return mapping.get(final), 3, False
        # ESC + lain (mis. Alt+key) → konsumsi 2 byte, abaikan.
        return None, 2, False

    @staticmethod
    def _csi_action(final: str, params: str):
        if final == "A":
            return "up"
        if final == "B":
            return "down"
        if final == "C":
            return "right"
        if final == "D":
            return "left"
        if final == "H":
            return "home"
        if final == "F":
            return "end"
        if final == "~":
            return {"1": "home", "7": "home", "4": "end", "8": "end",
                    "3": "delete", "200": "paste_start", "201": "paste_end"}.get(params)
        return None


def _raw_input_loop():
    """Loop input raw mode: baca byte, render footer, kirim baris ke queue."""
    ed = _LineEditor()
    fd = sys.stdin.fileno()
    if _footer is not None:
        _footer.set_input("", 0)
    while _input_running.is_set():
        try:
            r, _, _ = select.select([fd], [], [], 0.2)
            if _footer is not None:
                _footer.check_resize()
            if not r:
                continue
            data = os.read(fd, 4096)
            if not data:
                _input_queue.put(None)
                break
            ed.feed(data)
        except OSError:
            _input_queue.put(None)
            break
        except Exception:
            continue


def _input_reader():
    """
    Reader legacy (mode linear / non-TTY): pakai input()/readline.
    Dipakai saat footer mengambang tidak aktif (mis. mode single-prompt).
    """
    while _input_running.is_set():
        try:
            line = input()
            _input_queue.put(line)
        except EOFError:
            _input_queue.put(None)
            break
        except (OSError, KeyboardInterrupt):
            _input_queue.put(None)
            break


def _start_input_reader():
    """Mulai thread input reader (hanya dipanggil sekali di awal)."""
    global _input_thread
    _input_running.set()

    if _footer_active():
        # Raw mode editor (footer mengambang).
        target = _raw_input_loop
    else:
        # Legacy readline — arrow key & history untuk mode linear.
        try:
            readline.set_history_length(1000)
            readline.read_init_file()
            readline.set_completer(None)
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set disable-completion on')
        except Exception:
            pass
        target = _input_reader

    _input_thread = threading.Thread(target=target, daemon=True)
    _input_thread.start()


def _stop_input_reader():
    """Hentikan thread input reader."""
    _input_running.clear()


def _get_input(prompt_text=""):
    """
    Ambil input user dari queue. Satu-satunya fungsi input di seluruh program.
    Saat footer mengambang aktif, prompt dimiliki footer (tidak dicetak inline).
    """
    if prompt_text and not _footer_active():
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

# Lebar konten panel & garis — DINAMIS mengikuti terminal, di-clamp agar terbaca
# di Termux (sempit) dan tak meraksasa di monitor lebar.
UI_WIDTH_MIN = 40   # batas bawah keterbacaan boks/tabel
UI_WIDTH_MAX = 100  # batas atas (≈ tampilan lama di terminal lebar)


def _term_cols(fallback: int = 80) -> int:
    """
    Lebar terminal NYATA saat ini, di-clamp ke [UI_WIDTH_MIN..UI_WIDTH_MAX].
    Memakai shutil.get_terminal_size (sama seperti FooterUI) yang fail-safe:
    tanpa TTY / COLUMNS kosong → fallback (default 80).
    """
    try:
        cols = shutil.get_terminal_size(fallback=(fallback, 24)).columns
    except Exception:
        cols = fallback
    return max(UI_WIDTH_MIN, min(UI_WIDTH_MAX, cols))

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


def _rule(width: int | None = None, color: str = Style.GREY_DARK, char: str = "─") -> str:
    """Garis horizontal tipis. width=None → ikut lebar terminal."""
    if width is None:
        width = _term_cols() - 4
    return f"{color}{char * width}{Style.RESET}"


def _box(lines, color=Style.GREY_DARK, pad=1, width=None):
    """
    Bungkus daftar baris dalam panel rounded-corner ala Claude Code.
    Tiap elemen `lines` boleh mengandung kode ANSI; lebar dihitung dari teks
    tampak sehingga border tetap rata.
    Mengembalikan string multi-baris siap di-print.
    """
    if width is None:
        width = _term_cols() - 4
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


def _format_duration(secs: float) -> str:
    """
    Format durasi jadi ringkas & manusiawi: '45s', '2m', '2m 3s', '1j 2m'.
    Memakai floor agar konsisten dengan timer berjalan (stopwatch).
    Contoh: 123s → '2m 3s', 120s → '2m', 3661s → '1j 1m'.
    """
    secs = max(0, int(secs))
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        m, s = divmod(secs, 60)
        return f"{m}m {s}s" if s else f"{m}m"
    h, rem = divmod(secs, 3600)
    m = rem // 60
    return f"{h}j {m}m" if m else f"{h}j"


def _format_tokens(n: int) -> str:
    """
    Format jumlah token ringkas dengan huruf KAPITAL:
      - < 1000     → angka apa adanya ('850')
      - ribuan (K) → 1 desimal       ('13.2K')
      - jutaan (M) → 2 desimal       ('1.25M')
    """
    n = max(0, int(n))
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K"
    return f"{n / 1_000_000:.2f}M"


def _format_tokens_counter(n: int) -> str:
    """
    Format token untuk counter berpikir (realtime): angka PENUH dengan pemisah
    ribuan + label ' Token' (mis. '13,452 Token').

    Sengaja TIDAK diringkas ke K/M: format ringkas (langkah 0.1K = 100 token)
    membuat counter tampak "diam" di range ribuan. Angka penuh berubah tiap
    token sehingga terasa realtime. Ringkasan akhir tetap ringkas via
    _format_tokens() ('13.2K' / '1.25M').
    """
    return f"{max(0, int(n)):,} Token"


class Spinner:
    """
    Spinner animasi satu-baris ala Claude Code:

        ✷  Menelaah… (4s · q untuk interupsi)

    Bintang berdenyut, kata kerja berganti tiap beberapa detik, dan timer
    berjalan. Berjalan di thread daemon terpisah; berhenti rapi dengan
    membersihkan barisnya sehingga output berikutnya mulai dari baris bersih.

    PENTING: timer mengikuti satu *giliran* penuh (dari prompt user sampai
    jawaban akhir), bukan tiap panggilan API. Jadi hitungan tidak ter-reset
    di antara tool call. Panggil begin_turn() saat user mengirim prompt, dan
    end_turn() setelah jawaban akhir untuk mendapatkan total durasi.
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
        self._turn_start_ts = 0.0   # awal giliran (di-reset hanya oleh begin_turn)
        self._turn_tokens = 0       # token EXACT terkumpul dari round yang sudah selesai
        self._live_chars = 0        # estimasi REALTIME: karakter output round berjalan
        self._trim_notice_shown = False  # notice pangkas riwayat: cetak sekali per giliran
        self._enabled = sys.stdout.isatty()

    def begin_turn(self):
        """Tandai awal giliran baru — titik nol timer & token. Dipanggil sekali per prompt user."""
        self._turn_start_ts = time.time()
        self._turn_tokens = 0
        self._live_chars = 0
        self._trim_notice_shown = False

    def end_turn(self) -> float:
        """Hentikan animasi (jika ada) dan kembalikan total durasi giliran (detik).

        Catatan: token giliran TIDAK di-reset di sini agar masih bisa dibaca
        via `turn_tokens` untuk ringkasan setelah jawaban akhir. Reset terjadi
        pada begin_turn() berikutnya.
        """
        self.stop()
        if not self._turn_start_ts:
            return 0.0
        elapsed = time.time() - self._turn_start_ts
        self._turn_start_ts = 0.0
        return elapsed

    def add_tokens(self, n: int):
        """Tambah token EXACT (dari field usage) saat satu round API selesai."""
        try:
            self._turn_tokens += int(n)
        except (TypeError, ValueError):
            pass

    def add_live_chars(self, c: int):
        """Tambah karakter output yang baru di-stream → estimasi token realtime naik."""
        self._live_chars += c

    def reset_live(self):
        """Nolkan estimasi realtime (dipanggil setelah token EXACT round difold)."""
        self._live_chars = 0

    def estimate_live_tokens(self) -> int:
        """Estimasi token dari karakter output yang sudah di-stream (~4 char/token)."""
        return self._live_chars // 4

    @property
    def turn_tokens(self) -> int:
        """Total token EXACT giliran (dipakai untuk ringkasan akhir)."""
        return self._turn_tokens

    @property
    def display_tokens(self) -> int:
        """Token yang ditampilkan realtime: EXACT terkumpul + estimasi output berjalan."""
        return self._turn_tokens + self.estimate_live_tokens()

    def start(self, label: str = None):
        """Mulai animasi. `label` tetap jika diberikan; jika None, kata berganti otomatis."""
        if not self._enabled or self._running.is_set():
            return
        # Jika belum ada giliran aktif (mis. mode single-prompt), mulai sekarang.
        if not self._turn_start_ts:
            self._turn_start_ts = time.time()
        self._label = label
        self._running.set()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        i = 0
        while self._running.is_set():
            # Elapsed dihitung dari AWAL GILIRAN, bukan dari start() ini —
            # sehingga timer terus berjalan menembus beberapa tool call.
            elapsed = time.time() - self._turn_start_ts
            frame = self.FRAMES[i % len(self.FRAMES)]
            if self._label:
                word = self._label
            else:
                # ganti kata kerja tiap ~3.5 detik
                word = self.WORDS[int(elapsed // 3.5) % len(self.WORDS)]
            # Token usage REALTIME: token EXACT round selesai + estimasi output
            # yang sedang di-stream. Naik hidup saat model menghasilkan teks.
            # Hanya tampil setelah ada token, agar awal round tak menampilkan "0".
            live_tokens = self.display_tokens
            tok = (
                f" · {_format_tokens_counter(live_tokens)}"
                if live_tokens > 0 else ""
            )
            content = (
                f"{Style.ACCENT}{frame}{Style.RESET}  "
                f"{Style.GREY_LIGHT}{word}…{Style.RESET} "
                f"{Style.GREY}({_format_duration(elapsed)}{tok} · q untuk interupsi){Style.RESET}"
            )
            if _footer_active():
                # Footer mengambang: tulis ke baris status (bukan inline \r).
                _footer.set_status(content)
            else:
                sys.stdout.write(f"\r  {content}\033[K")  # \033[K = bersihkan sisa baris
                sys.stdout.flush()
            i += 1
            time.sleep(0.1)

    def stop(self):
        """Hentikan animasi dan bersihkan baris spinner (timer giliran TIDAK di-reset)."""
        if not self._running.is_set():
            return
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=0.3)
        if _footer_active():
            # Kembalikan baris status ke hint idle.
            _footer.set_idle()
        else:
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

    # Lebar fallback terminal (dipakai _term_width() bila get_terminal_size gagal)
    TERM_WIDTH = 70

    # Bullet styles untuk nested lists
    BULLETS = ["•", "◦", "▪", "▫", "→"]

    @classmethod
    def _term_width(cls) -> int:
        """Lebar terminal dinamis untuk separator/rule; fallback ke TERM_WIDTH."""
        return _term_cols(fallback=cls.TERM_WIDTH)
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
                width = cls._term_width() - 4
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
            return f"\n  {Style.DIM}{'─' * (cls._term_width() - 4)}{Style.RESET}\n"
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
    """Pastikan folder sessions/ ada & sapu tmpfile yatim sisa crash (.tmp-*)."""
    os.makedirs(config.SESSIONS_DIR, exist_ok=True)
    try:
        for f in os.listdir(config.SESSIONS_DIR):
            if f.startswith(".tmp-"):
                try:
                    os.remove(os.path.join(config.SESSIONS_DIR, f))
                except OSError:
                    pass
    except OSError:
        pass


def _atomic_write_json(path: str, data: dict, make_backup: bool = True):
    """
    Tulis JSON secara atomik & crash-safe: tmpfile di folder SAMA → flush +
    os.fsync → os.replace (atomik lintas-OS pada filesystem yang sama). Backup
    ringan file lama (1 generasi) ke <dir>/backups/ sebelum menimpa. Meneruskan
    exception ke caller bila gagal — file lama TETAP utuh.
    """
    dir_ = os.path.dirname(path) or "."
    os.makedirs(dir_, exist_ok=True)

    # Backup file lama (best-effort; kegagalan tak boleh membatalkan penyimpanan).
    if make_backup and os.path.exists(path):
        try:
            backups_dir = os.path.join(dir_, "backups")
            os.makedirs(backups_dir, exist_ok=True)
            shutil.copy2(path, os.path.join(backups_dir, os.path.basename(path) + ".bak"))
        except OSError:
            pass

    # Tulis ke tmpfile di folder SAMA agar os.replace atomik (bukan cross-device).
    # suffix '.tmp' (BUKAN '.json') supaya orphan tmp tak terbaca list_sessions.
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".tmp", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # atomik di POSIX & Windows pada FS sama
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    else:
        # fsync direktori best-effort (durability entri baru) — POSIX; non-fatal
        # di Windows/Termux FS tertentu karena data sudah ter-replace & durable.
        try:
            dfd = os.open(dir_, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except Exception:
            pass


def _session_path(name: str) -> str:
    """Dapatkan path file session berdasarkan nama."""
    # Sanitize nama session — hanya alphanumeric, dash, underscore
    safe_name = re.sub(r'[^\w\-]', '_', name).strip('_')
    if not safe_name:
        safe_name = "untitled"
    return os.path.join(config.SESSIONS_DIR, f"{safe_name}.json")


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
        _atomic_write_json(path, session_data)
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
        files = sorted(os.listdir(config.SESSIONS_DIR))
    except OSError:
        return sessions

    for f in files:
        if not f.endswith(".json"):
            continue
        path = os.path.join(config.SESSIONS_DIR, f)
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
        files = os.listdir(config.SESSIONS_DIR)
    except OSError as e:
        return f"Error membaca folder sessions: {e}"

    for f in files:
        if not f.endswith(".json"):
            continue
        name = f[:-5]  # hapus .json
        if auto_pattern.match(name):
            path = os.path.join(config.SESSIONS_DIR, f)
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

        # Tulis target atomik; old hanya dihapus SETELAH new sukses ter-replace.
        _atomic_write_json(new_path, data)
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
    _help_row("ruka", "Mode interaktif — workspace = folder saat ini (cwd)")
    _help_row("ruka <namaSesi>", "Load atau buat session bernama (workspace = cwd)")
    _help_row("ruka <path> <namaSesi>", "Override workspace ke path tertentu")
    _help_row("ruka <path>", "Override workspace ke path tertentu")
    _help_row("ruka \"<prompt>\"", "Mode prompt tunggal (langsung jawab)")

    _help_section("Slash command (dalam sesi)")
    _help_row("/help", "Tampilkan bantuan ini")
    _help_row("/sessions", "Lihat daftar semua session")
    _help_row("/new", "Mulai session baru (lama auto-save)")
    _help_row("/history", "Lihat riwayat chat sesi ini")
    _help_row("/clear", "Bersihkan layar")
    _help_row("/delete-session <nama>", "Hapus session tertentu")
    _help_row("/rename-session <l> <b>", "Rename session")
    _help_row("/team <tugas>", "Bentuk tim & diskusi kolaboratif multi-agent")

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
    print(f"  {Style.GREY}cwd{Style.RESET}      {bullet} {Style.GREY_LIGHT}{_shorten_path(config.BASE_DIR)}{Style.RESET}")
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
    "discuss":       "Discuss",
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
    if tool_name == "discuss":
        topic = args.get("topic", "")[:30]
        team = args.get("team", [])
        names = [m.get("name", "?") for m in team if isinstance(m, dict)]
        if names:
            return f"{topic} · {', '.join(names)}"
        return topic
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
    # Buang kode ANSI & karakter kontrol mentah dari isi tool agar tidak
    # merusak scroll region / footer saat dicetak.
    first = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', _strip_ansi(lines[0])).strip()
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


def show_turn_summary(duration_secs: float, total_tokens: int = 0):
    """
    Ringkasan kecil & redup setelah jawaban akhir: total durasi & token giliran.
    Contoh:  ⎿ selesai dalam 12s | token : 13.2k
    """
    if duration_secs <= 0:
        return
    tok = f" | token : {_format_tokens(total_tokens)}" if total_tokens > 0 else ""
    print(f"\n  {Style.GREY_DARK}⎿ selesai dalam {_format_duration(duration_secs)}{tok}{Style.RESET}")


def show_trim_notice(dropped: int, est_tokens: int):
    """
    Notice satu baris (sekali per giliran) saat riwayat dipangkas untuk payload
    API. Transkrip penuh tetap utuh di memori & sesi — hanya yang DIKIRIM diciutkan.
    """
    print(
        f"\n  {Style.GREY_DARK}⎿ riwayat dipangkas: {dropped} pesan lama dibuang dari konteks "
        f"(~{_format_tokens(est_tokens)} token dikirim){Style.RESET}"
    )


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
    # Saat footer mengambang aktif, prompt dimiliki footer; tampilkan hint idle.
    if _footer_active():
        _footer.set_idle()
    line = _get_input(f"\n{Style.ACCENT}❯{Style.RESET} ")
    text = line.strip()
    # Mode footer: input hidup di footer & dikosongkan saat Enter, sehingga
    # tidak ter-echo otomatis (beda dengan readline di mode linear). Echo
    # manual ke area konten agar prompt tetap terlihat di scrollback chat.
    if _footer_active() and text:
        print(f"\n  {Style.ACCENT}❯{Style.RESET} {Style.GREY_LIGHT}{text}{Style.RESET}")
    return text


# ============================================================
# HELPER: Keamanan Path
# ============================================================

def _safe_path(name: str) -> str | None:
    """
    Mengembalikan path absolut yang aman, atau None jika path traversal terdeteksi.

    Mendukung dua mode:
    - Path absolut (contoh: /home/user/RukaAI/SKILL/skills.md) → pakai langsung
    - Path relatif (contoh: catatan.txt) → gabungkan dengan BASE_DIR

    Path traversal dicegah dengan memastikan hasil akhir masih dalam BASE_DIR
    atau SCRIPT_DIR (folder main.py, untuk akses SKILL/ dan file internal).
    """
    # Null byte tak pernah valid di path & bisa menipu pemeriksaan — tolak dini.
    if "\x00" in name:
        return None

    if os.path.isabs(name):
        raw = os.path.abspath(name)
    else:
        raw = os.path.abspath(os.path.join(config.BASE_DIR, name))

    # Resolusi symlink pada komponen PARENT (mencegah escape lewat symlink)
    # sambil MEMPERTAHANKAN leaf — agar file/folder yang belum ada (write_file
    # baru, create_folder, tujuan copy/move) tetap valid.
    parent = os.path.dirname(raw)
    leaf = os.path.basename(raw)
    try:
        real_parent = os.path.realpath(parent)
    except (OSError, ValueError):
        return None
    if leaf in ("", os.curdir, os.pardir):
        target = real_parent
    else:
        target = os.path.join(real_parent, leaf)
        # Bila leaf sendiri symlink yang SUDAH ada, ikut diresolusi.
        try:
            if os.path.islink(target):
                target = os.path.realpath(target)
        except (OSError, ValueError):
            return None

    # Keanggotaan path divalidasi dengan commonpath terhadap base yang juga
    # di-realpath — bukan startswith (yang lolos sibling-prefix: BASE_DIR=/a/proj
    # keliru mengizinkan /a/proj-rahasia). Fail-closed pada error apa pun.
    def _within(base: str) -> bool:
        try:
            base_real = os.path.realpath(base)
        except (OSError, ValueError):
            return False
        try:
            return os.path.commonpath([base_real, target]) == base_real
        except (ValueError, TypeError):
            return False  # beda drive (Windows) / campur abs-rel / null byte

    if _within(config.BASE_DIR) or _within(config.SCRIPT_DIR):
        return target
    return None


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
                "Gunakan ini ketika user meminta membaca, melihat, atau menganalisis isi file. "
                "Untuk file besar, gunakan offset & limit untuk membaca rentang baris; "
                "bila tak diisi, file dibaca dari awal dengan batas aman dan diberi penanda bila terpotong."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Nama file yang ingin dibaca, misalnya 'catatan.txt' atau 'data.json'."
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Opsional. Nomor baris awal (mulai dari 1). Default 1."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Opsional. Jumlah baris yang dibaca mulai dari offset."
                    },
                    "line_numbers": {
                        "type": "boolean",
                        "description": "Opsional (default false). Tampilkan nomor baris asli di depan tiap baris."
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
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": (
                            "Opsional (default false), hanya untuk operation='replace'. "
                            "Jika old_text muncul lebih dari sekali, set true untuk "
                            "mengganti SEMUA kemunculan. Bila false dan old_text ambigu "
                            "(muncul >1x), edit ditolak dan kamu diminta memperunik old_text."
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
    },
    {
        "type": "function",
        "function": {
            "name": "discuss",
            "description": (
                "Mulai diskusi kolaboratif antara beberapa agen dengan peran berbeda. "
                "Setiap anggota tim MELIHAT seluruh riwayat diskusi sebelum giliran mereka "
                "sehingga bisa merespons, menyanggah, atau menyempurnakan argumen anggota lain. "
                "Setelah semua putaran, Koordinator merangkum hasil dan memberikan keputusan akhir. "
                "Gunakan ini untuk masalah yang butuh perspektif beragam, "
                "tinjauan kolektif, atau keputusan bersama. "
                "PENTING: Koordinator sudah muncul OTOMATIS di akhir diskusi — "
                "JANGAN masukkan 'Koordinator' ke dalam parameter 'team'. "
                "Parameter 'team' hanya berisi anggota diskusi aktif (Developer, Reviewer, dll.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "Topik atau masalah yang akan didiskusikan tim. "
                            "Tulis dengan jelas agar setiap anggota memahami konteksnya."
                        )
                    },
                    "team": {
                        "type": "array",
                        "description": (
                            "Daftar anggota diskusi aktif (2-6 orang), masing-masing dengan nama dan peran. "
                            "Pilih peran yang saling melengkapi, misalnya: "
                            "Developer + Reviewer + Tester untuk tugas coding; "
                            "Arsitek + Implementer + Risk_Analyst untuk perencanaan; "
                            "Penulis + Editor + Kritikus untuk tugas menulis. "
                            "LARANGAN KERAS: JANGAN masukkan 'Koordinator' ke sini — "
                            "Koordinator sudah ditambahkan secara otomatis oleh sistem."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Nama anggota tim, mis. 'Backend Dev', 'Reviewer', 'DBA'."
                                },
                                "role": {
                                    "type": "string",
                                    "description": "Peran dan fokus anggota ini dalam diskusi."
                                }
                            },
                            "required": ["name", "role"]
                        }
                    },
                    "max_rounds": {
                        "type": "integer",
                        "description": (
                            "Batas putaran diskusi. Default 0 = tidak terbatas — "
                            "Koordinator yang memutuskan kapan diskusi selesai. "
                            "Isi hanya jika ada kebutuhan khusus untuk membatasi jumlah putaran."
                        ),
                        "default": 0
                    }
                },
                "required": ["topic", "team"]
            }
        }
    }
]

# ============================================================
# IMPLEMENTASI TOOLS (dieksekusi secara lokal)
# ============================================================

def _truncate_text(text: str, max_chars: int, at_line_boundary: bool = False) -> tuple:
    """
    Potong `text` ke maksimal `max_chars` KARAKTER (bukan byte, agar codepoint
    UTF-8 tak terbelah). Mengembalikan (teks_terpotong, was_truncated).
    Bila at_line_boundary=True, potong di newline terakhir yang muat agar baris
    tetap utuh. Penanda terpotong disusun oleh pemanggil (saran beda per konteks).
    """
    if len(text) <= max_chars:
        return text, False
    cut = text[:max_chars]
    if at_line_boundary:
        nl = cut.rfind("\n")
        if nl > 0:
            cut = cut[:nl]
    return cut, True


def _looks_binary(path: str, sniff: int = None) -> bool:
    """
    Deteksi file biner via SAMPEL byte awal: biner bila ada NUL byte (b'\\x00')
    atau proporsi byte kontrol non-teks tinggi. TIDAK memakai non-ASCII sebagai
    sinyal — file UTF-8 (Indonesia/emoji) tetap dianggap teks.
    """
    if sniff is None:
        sniff = config.BINARY_SNIFF_BYTES
    try:
        with open(path, "rb") as f:
            chunk = f.read(sniff)
    except OSError:
        return False
    if not chunk:
        return False
    if b"\x00" in chunk:
        return True
    # Byte teks lazim: tab(9), LF(10), CR(13), dan >=32. Byte kontrol lain
    # dianggap indikasi biner bila proporsinya tinggi.
    text_control = {9, 10, 13}
    nontext = sum(1 for b in chunk if b < 32 and b not in text_control)
    return nontext / len(chunk) > 0.30


def tool_read_file(filename: str, offset: int = 1, limit: int = None, line_numbers: bool = False) -> str:
    path = _safe_path(filename)
    if path is None:
        return "Error: Akses ditolak. Path harus berada di direktori kerja."
    if not os.path.exists(path):
        return f"Error: File '{filename}' tidak ditemukan."
    if not os.path.isfile(path):
        return f"Error: '{filename}' bukan file."

    if _looks_binary(path):
        size = os.path.getsize(path)
        return (
            f"Error: File '{filename}' terdeteksi biner ({_format_size(size)}); "
            f"read_file hanya untuk teks. Gunakan exec_command (mis. file/xxd/hexdump) bila perlu."
        )

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return f"Error membaca file: {e}"

    if content == "":
        return "(file kosong)"

    lines = content.splitlines()
    total = len(lines)

    # Fast path: tanpa parameter & muat dalam batas → kembalikan apa adanya
    # (kompatibilitas penuh dengan perilaku lama, termasuk newline akhir).
    no_params = offset <= 1 and limit is None and not line_numbers
    if no_params and len(content) <= config.MAX_READ_CHARS and total <= config.MAX_READ_LINES:
        return content

    # offset 1-based; klem ke 1 bila <1.
    start = max(offset, 1) - 1
    if start >= total:
        return f"Error: offset {offset} di luar rentang (file hanya punya {total} baris)."

    eff_limit = limit if (limit is not None and limit > 0) else config.MAX_READ_LINES
    end = min(start + eff_limit, total)
    chunk = lines[start:end]

    if line_numbers:
        width = len(str(end))
        # Penomoran memakai posisi ASLI di file (start+1..), bukan 1..limit.
        body = "\n".join(f"{i:>{width}}  {ln}" for i, ln in enumerate(chunk, start=start + 1))
    else:
        body = "\n".join(chunk)

    # Cap karakter (potong di batas baris) sebagai pengaman kedua.
    body, char_truncated = _truncate_text(body, config.MAX_READ_CHARS, at_line_boundary=True)

    shown = body.count("\n") + 1 if body else 0
    last_shown = start + shown
    # Penanda hanya saat CAP memaksa potong (bukan saat model sengaja meminta
    # window via limit eksplisit yang sudah dihormati penuh).
    explicit_limit = limit is not None and limit > 0
    if char_truncated or (not explicit_limit and end < total):
        body += (
            f"\n\n[...output dipotong — menampilkan baris {start + 1}-{last_shown} dari {total}; "
            f"lanjut dengan offset={last_shown + 1} (opsional limit) atau pakai grep untuk bagian spesifik]"
        )

    return body if body else "(file kosong)"


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


def tool_edit_file(filename: str, operation: str, new_text: str, old_text: str = None, replace_all: bool = False) -> str:
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
            if old_text == "":
                return "Error: Parameter 'old_text' tidak boleh string kosong untuk operasi 'replace'."
            count = current_content.count(old_text)
            if count == 0:
                return f"Error: Teks '{old_text[:50]}{'...' if len(old_text) > 50 else ''}' tidak ditemukan dalam file '{filename}'."
            if count > 1 and not replace_all:
                return (
                    f"Error: Teks '{old_text[:50]}{'...' if len(old_text) > 50 else ''}' "
                    f"ditemukan {count}x dalam file '{filename}' (ambigu). "
                    f"Sertakan konteks lebih unik di old_text agar cocok tepat 1x, "
                    f"atau set replace_all=true untuk mengganti SEMUA kemunculan."
                )
            n = count if replace_all else 1
            new_content = current_content.replace(old_text, new_text, n)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            if replace_all and count > 1:
                return f"File '{filename}' berhasil diedit (replace_all: {count}x '{old_text[:30]}...' → '{new_text[:30]}...')."
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
            f for f in os.listdir(config.BASE_DIR)
            if os.path.isfile(os.path.join(config.BASE_DIR, f))
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
        base = config.BASE_DIR
        lines = [f"Struktur Direktori: {base}"]

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

        _walk(base, "  ", 1)

        total_files = sum(1 for _, _, files in os.walk(base) for _ in files)
        total_dirs = sum(1 for _, dirs, _ in os.walk(base) for _ in dirs)
        lines.append(f"\n  Total: {total_dirs} folder, {total_files} file")

        return "\n".join(lines)
    except Exception as e:
        return f"Error membaca struktur direktori: {e}"


# Variabel lingkungan yang TIDAK boleh diturunkan ke subprocess yang dijalankan
# model (mis. lewat `printenv`/`env`). Denylist BERTARGET dengan nama EKSAK —
# sengaja BUKAN pola KEY/TOKEN/SECRET agar tidak ikut membuang variabel sah milik
# user (SSH_AUTH_SOCK, GPG_TTY, KEYBOARD_LAYOUT, dsb.).
_SENSITIVE_ENV_VARS = frozenset({
    "OPENROUTER_API_KEY",   # dipakai Ruka (config.py:14, .env)
    # Pengaman ke depan — nama eksak rahasia umum, BUKAN pola substring:
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_KEY",
    "HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGING_FACE_HUB_TOKEN",
    "GROQ_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
})


def _scrubbed_env() -> dict:
    """
    Salinan os.environ untuk subprocess dengan rahasia Ruka DIBUANG agar model
    tak bisa membacanya via `printenv`/`env`. PATH/HOME/LANG/PREFIX(Termux)/dll
    tetap utuh supaya perintah user normal tidak rusak. os.environ proses Ruka
    TIDAK dimutasi (memakai .copy()).
    """
    env = os.environ.copy()
    for var in _SENSITIVE_ENV_VARS:
        env.pop(var, None)
    # Jaring tambahan: buang variabel APAPUN yang nilainya PERSIS == API key Ruka
    # (menangkap key yang di-set lewat nama alias non-standar). Guard len>=8
    # mencegah false-positive massal bila key kebetulan sangat pendek/kosong.
    secret = config.OPENROUTER_API_KEY
    if secret and len(secret) >= 8:
        for k in list(env.keys()):
            if env.get(k) == secret:
                env.pop(k, None)
    return env


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
                cwd=config.BASE_DIR,
                env=_scrubbed_env(),
            )
        else:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=config.BASE_DIR,
                env=_scrubbed_env(),
            )

        cap = config.MAX_EXEC_OUTPUT_CHARS
        output_parts = []

        if result.stdout:
            out, trunc = _truncate_text(result.stdout, cap)
            if trunc:
                out += (
                    f"\n[...stdout dipotong, batas {cap} char; gunakan grep/head/tail "
                    f"atau alihkan ke file lalu read_file dengan offset/limit]"
                )
            output_parts.append(out)
        if result.stderr:
            err, trunc = _truncate_text(result.stderr, cap)
            if trunc:
                err += f"\n[...stderr dipotong, batas {cap} char]"
            output_parts.append(f"[stderr] {err}")

        # Exit code ditambahkan SETELAH capping → tak pernah ikut terpotong.
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


# ============================================================
# ORCHESTRATION — Multi-Agent
# ============================================================

# Kedalaman diskusi tim saat ini (0 = agen utama, >0 = di dalam discuss).
# Di-increment saat masuk tool_team_discuss dan di-decrement saat keluar (via finally).
_AGENT_DEPTH = 0
_AGENT_MAX_DEPTH = 3   # Cegah rekursi diskusi tak terbatas


def _show_team_banner(topic: str, done: bool = False, elapsed: float = 0.0):
    """
    Panel pembuka/penutup sesi diskusi tim.
    Warna ACCENT (coral) — berbeda dari panel sub-agent (Cyan/Magenta/Yellow)
    agar tim mudah dibedakan secara visual.

    Pembuka:  ╭─ Tim · <topic> ──────────────────────────────╮
    Penutup:  ╰─ diskusi selesai dalam 2m 5s ────────────────╯
    """
    width = _term_cols() - 4
    color = Style.ACCENT

    if not done:
        label = f" Tim · {topic[:46]}{'…' if len(topic) > 46 else ''} "
        fill = max(0, width - len(label) - 2)
        line = f"╭─{label}{'─' * fill}─╮"
    else:
        label = f" diskusi selesai dalam {_format_duration(elapsed)} "
        fill = max(0, width - len(label) - 2)
        line = f"╰─{label}{'─' * fill}─╯"

    print(f"\n  {color}{line}{Style.RESET}")


def _show_team_member_header(name: str, role: str, round_label, color: str):
    """
    Header speaker dalam diskusi tim:

        ◆ Nama  (Putaran 1)
        └ Peran anggota ini
        ──────────────────────────────────────
    """
    round_str = (
        f"Putaran {round_label}" if isinstance(round_label, int) else str(round_label)
    )
    print(
        f"\n  {color}◆ {Style.BOLD}{name}{Style.RESET}"
        f"  {Style.GREY}({round_str}){Style.RESET}"
    )
    print(f"  {Style.GREY_DARK}└ {Style.GREY}{role}{Style.RESET}")
    print(f"  {color}{'─' * max(4, _term_cols() - 8)}{Style.RESET}")


def _coordinator_check(topic: str, discussion: list) -> tuple:
    """
    Tanya koordinator apakah diskusi sudah cukup matang untuk ditutup.
    Panggilan ringan (tanpa tools, max 400 token) agar cepat.
    Returns (is_done: bool, note: str)
      - is_done=True  → koordinator minta tutup diskusi
      - is_done=False → koordinator minta lanjut + catatan apa yg perlu dibahas
    """
    hist_parts = [
        f"[{d['name']}, Putaran {d['round']}]:\n{d['content'][:1200]}"
        for d in discussion
    ]
    rounds_done = discussion[-1]["round"] if discussion else 0
    check_messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah koordinator diskusi yang bertugas menilai kematangan "
                "sebuah diskusi tim. Jawab singkat dan langsung. "
                "Bersikaplah kritis — satu putaran hampir tidak pernah cukup untuk "
                "topik yang kompleks. Pastikan ada dialog nyata antar anggota "
                "sebelum menutup diskusi."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Topik diskusi: {topic}\n\n"
                f"Diskusi sejauh ini ({len(discussion)} kontribusi, {rounds_done} putaran):\n"
                + "\n\n".join(hist_parts)
                + "\n\nEvaluasi: Apakah diskusi ini sudah cukup matang untuk ditutup?\n"
                "Kriteria SELESAI (SEMUA harus terpenuhi):\n"
                "- Sudah minimal 2 putaran sehingga anggota bisa MERESPONS satu sama lain\n"
                "- Ada dialog nyata: anggota menyebut nama rekan & merespons poin spesifik mereka\n"
                "- Konsensus atau keputusan teknis sudah jelas dan bisa langsung dieksekusi\n"
                "- Tidak ada pertanyaan kritis atau trade-off yang belum terjawab\n\n"
                "Jika SUDAH selesai → mulai jawaban dengan kata SELESAI\n"
                "Jika BELUM selesai → mulai jawaban dengan kata LANJUT "
                "dan sebutkan maksimal 3 poin yang masih perlu didialogkan di putaran berikutnya."
            ),
        },
    ]
    try:
        data = chat(check_messages, temperature=0.4, max_tokens=4096,
                    include_tools=False)
        reply = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content") or ""
        ).strip()
        is_done = reply.upper().startswith("SELESAI")
        return is_done, reply
    except Exception as e:
        # Jika gagal → anggap belum selesai (safer: lanjut daripada cut off)
        return False, f"(Error cek koordinator: {e})"


def tool_team_discuss(topic: str, team: list, max_rounds: int = 0) -> str:
    """
    Mulai diskusi kolaboratif antara beberapa agen dengan peran berbeda.

    Setiap anggota tim MELIHAT seluruh riwayat diskusi sebelum giliran mereka
    sehingga bisa merespons, menyanggah, atau menyempurnakan argumen anggota lain.
    Setelah setiap putaran, Koordinator mengevaluasi apakah diskusi sudah matang.
    Jika belum → lanjut putaran berikutnya dengan catatan apa yang masih perlu dibahas.
    Jika sudah → Koordinator menutup dan merangkum diskusi.

    topic      : topik atau masalah yang didiskusikan
    team       : list of {"name": str, "role": str} — minimal 2, maksimal 6 anggota
    max_rounds : batas putaran; 0 (default) = tidak terbatas, Koordinator yang memutuskan
    """
    global _AGENT_DEPTH

    if _AGENT_DEPTH >= _AGENT_MAX_DEPTH:
        return (
            f"Error: Kedalaman sub-agent maksimum ({_AGENT_MAX_DEPTH}) tercapai. "
            "Tidak bisa memulai diskusi tim baru."
        )
    if not isinstance(team, list) or not team:
        return "Error: Parameter 'team' harus berupa daftar anggota tim."

    # Buang anggota bernama "Koordinator" — sudah muncul otomatis, jangan duplikat.
    _RESERVED = {"koordinator", "coordinator"}
    filtered_team = [
        m for m in team
        if not (isinstance(m.get("name"), str)
                and m["name"].strip().lower() in _RESERVED)
    ]
    if len(filtered_team) < len(team):
        removed = len(team) - len(filtered_team)
        print(
            f"\n  {Style.WARN}◈ Peringatan: {removed} anggota bernama 'Koordinator' "
            f"dilewati — Koordinator sudah otomatis.{Style.RESET}"
        )
    team = filtered_team

    if len(team) < 2:
        return "Error: Diskusi tim membutuhkan minimal 2 anggota."
    if len(team) > 6:
        return "Error: Maksimum 6 anggota tim per diskusi."

    max_rounds = max(0, int(max_rounds))  # 0 = tidak terbatas

    # Riwayat diskusi bersama — semua anggota bisa membaca ini tiap giliran
    discussion: list[dict] = []  # {"name": str, "round": int, "content": str}

    # Warna per anggota (deterministik by index)
    member_colors = [
        Style.CYAN, Style.MAGENTA, Style.YELLOW,
        Style.GREEN, Style.ORANGE, Style.PINK,
    ]

    _show_team_banner(topic, done=False)
    _AGENT_DEPTH += 1
    disc_start = time.time()

    coordinator_note = ""  # catatan koordinator untuk putaran berikutnya

    try:
        round_num = 0
        while True:
            round_num += 1

            # ── Batas putaran (hanya berlaku jika max_rounds > 0) ───
            if max_rounds > 0 and round_num > max_rounds:
                print(
                    f"\n  {Style.WARN}◈ Batas {max_rounds} putaran tercapai "
                    f"— menutup diskusi.{Style.RESET}"
                )
                break

            # ── Setiap anggota tim berbicara ────────────────────────
            for i, member in enumerate(team):
                name = member.get("name")
                if not name:
                    for k, v in member.items():
                        if k.lower() in ("name", "role"):
                            continue
                        # key mirip "name" (mis. "namename") → nama ada di value
                        if "name" in k.lower():
                            name = v if isinstance(v, str) else k
                        else:
                            # key IS nama-nya (mis. "Backend Dev")
                            name = k
                        break
                if not name:
                    name = f"Agen {i + 1}"
                role = member.get("role", "Anggota tim")
                color = member_colors[i % len(member_colors)]

                _show_team_member_header(name, role, round_num, color)

                # Susun riwayat diskusi untuk konteks member ini
                if discussion:
                    hist_parts = [
                        f"[{d['name']}, Putaran {d['round']}]:\n{d['content']}"
                        for d in discussion
                    ]
                    context_part = (
                        "\n\nRiwayat diskusi tim sejauh ini:\n"
                        + "\n\n".join(hist_parts)
                    )
                else:
                    context_part = ""

                # Instruksi giliran
                if round_num == 1:
                    turn_note = (
                        "Ini putaran pertama. Sampaikan POSISI AWAL dan argumen utamamu — "
                        "bukan kesimpulan final. Sisakan ruang untuk diperdebatkan: "
                        "sebutkan asumsi yang masih perlu dikonfirmasi, trade-off yang belum jelas, "
                        "atau poin di mana kamu ingin mendengar pendapat anggota lain. "
                        "Kamu bisa menggunakan tools (read_file, exec_command, dll.) "
                        "untuk mengumpulkan data konkret sebelum berpendapat."
                    )
                else:
                    unresolved = (
                        f"\n\nCatatan koordinator — poin yang masih perlu dibahas:\n"
                        f"{coordinator_note}"
                        if coordinator_note else ""
                    )
                    turn_note = (
                        f"Ini putaran {round_num}. Baca kontribusi tim di atas, "
                        "lalu respons mereka — setuju, sanggah, atau sempurnakan. "
                        "Sebutkan nama anggota secara eksplisit jika kamu merespons "
                        f"poin spesifik mereka.{unresolved}"
                    )

                member_prompt = (
                    f"Kamu adalah **{name}** dalam sebuah diskusi tim.\n"
                    f"Peranmu: {role}\n\n"
                    f"Topik diskusi: {topic}"
                    f"{context_part}\n\n"
                    f"{turn_note}"
                )

                sub_messages = [
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": member_prompt},
                ]

                try:
                    data = chat(sub_messages, temperature=0.7, max_tokens=16384)
                    reply, sub_messages, was_interrupted = process_response(
                        sub_messages, data
                    )
                    if reply:
                        _emit_agent_text(reply, interrupted=was_interrupted)
                        discussion.append(
                            {"name": name, "round": round_num, "content": reply}
                        )
                    else:
                        discussion.append(
                            {"name": name, "round": round_num,
                             "content": "(tidak ada respons)"}
                        )
                except Exception as e:
                    err = f"Error anggota {name}: {e}"
                    discussion.append(
                        {"name": name, "round": round_num, "content": err}
                    )
                    _emit_agent_text(err)

            # ── Koordinator mengevaluasi setelah putaran selesai ────
            print(
                f"\n  {Style.GREY_DARK}◈ Koordinator mengevaluasi putaran "
                f"{round_num}…{Style.RESET}"
            )
            is_done, coord_reply = _coordinator_check(topic, discussion)

            if is_done:
                print(
                    f"  {Style.OK}◈ Koordinator: diskusi selesai "
                    f"— merangkum.{Style.RESET}"
                )
                break
            else:
                # Ekstrak catatan untuk putaran berikutnya (buang kata LANJUT)
                coordinator_note = (
                    coord_reply
                    .replace("LANJUT", "").replace("lanjut", "")
                    .strip(" :\n")
                )
                note_preview = coordinator_note[:180]
                print(
                    f"  {Style.WARN}◈ Koordinator: lanjut ke putaran "
                    f"{round_num + 1}.{Style.RESET}"
                )
                if note_preview:
                    print(f"  {Style.GREY}  └ {note_preview}{Style.RESET}")

        # ── Sintesis akhir oleh Koordinator ────────────────────────
        synthesis = ""
        if discussion:
            _show_team_member_header(
                "Koordinator",
                "Merangkum dan mensintesis hasil diskusi tim",
                "Sintesis",
                Style.ACCENT,
            )
            hist_parts = [
                f"[{d['name']}, Putaran {d['round']}]:\n{d['content']}"
                for d in discussion
            ]
            synthesis_prompt = (
                f"Kamu adalah koordinator teknis yang menyusun rangkuman eksekutif "
                f"dari diskusi tim berikut.\n\n"
                f"Topik: {topic}\n\n"
                f"Diskusi tim ({round_num} putaran, {len(discussion)} kontribusi):\n"
                + "\n\n".join(hist_parts)
                + "\n\n"
                "Susun rangkuman yang DETAIL dan TEKNIS sehingga main agent bisa "
                "langsung mengeksekusi tanpa perlu bertanya lagi. Struktur:\n\n"
                "## Keputusan Akhir\n"
                "Nyatakan keputusan final secara eksplisit. Jika ada beberapa opsi "
                "yang dipertimbangkan, sebutkan MANA yang dipilih dan MENGAPA "
                "(alasan teknis, bukan sekadar 'tim sepakat').\n\n"
                "## Justifikasi Teknis\n"
                "Jelaskan reasoning teknis di balik setiap keputusan:\n"
                "- Trade-off yang diidentifikasi selama diskusi\n"
                "- Argumen kunci yang memenangkan debat (kutip nama anggota jika relevan)\n"
                "- Asumsi atau constraint yang menjadi dasar keputusan\n\n"
                "## Spesifikasi Implementasi\n"
                "Detail teknis yang harus diikuti saat eksekusi:\n"
                "- Parameter, konfigurasi, versi, atau library spesifik yang disepakati\n"
                "- Pola arsitektur, struktur data, atau API contract yang ditentukan\n"
                "- Hal-hal yang WAJIB dilakukan vs. yang opsional\n\n"
                "## Peringatan & Edge Case\n"
                "Risiko, keterbatasan, atau edge case yang diidentifikasi tim "
                "yang harus diwaspadai saat implementasi.\n\n"
                "## Poin yang Masih Terbuka\n"
                "Jika ada hal yang belum tuntas diputuskan, sebutkan secara eksplisit "
                "beserta opsi yang ada — jangan sembunyikan ketidakpastian.\n\n"
                "## Langkah Eksekusi\n"
                "Urutan langkah konkret yang harus dilakukan, cukup spesifik untuk "
                "langsung dieksekusi (bukan daftar abstrak)."
            )
            synth_messages = [
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": synthesis_prompt},
            ]
            try:
                data = chat(synth_messages, temperature=0.7, max_tokens=16384)
                synthesis, synth_messages, _ = process_response(synth_messages, data)
                if synthesis:
                    _emit_agent_text(synthesis)
            except Exception as e:
                synthesis = f"Error sintesis: {e}"

        elapsed = time.time() - disc_start
        _show_team_banner(topic, done=True, elapsed=elapsed)

        members_str = ", ".join(m.get("name", "?") for m in team)
        return (
            f"Diskusi tim selesai: {len(discussion)} kontribusi dari {members_str} "
            f"({round_num} putaran, {_format_duration(elapsed)}).\n\n"
            f"Sintesis:\n{synthesis or '(tidak ada sintesis)'}"
        )

    finally:
        _AGENT_DEPTH -= 1


def execute_tool(name: str, arguments: dict) -> str:
    if name == "read_file":
        result = tool_read_file(
            arguments["filename"],
            arguments.get("offset", 1),
            arguments.get("limit"),
            arguments.get("line_numbers", False),
        )
    elif name == "write_file":
        result = tool_write_file(arguments["filename"], arguments["content"])
    elif name == "edit_file":
        operation = arguments["operation"]
        new_text = arguments["new_text"]
        old_text = arguments.get("old_text")
        replace_all = arguments.get("replace_all", False)
        result = tool_edit_file(arguments["filename"], operation, new_text, old_text, replace_all)
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
    elif name == "discuss":
        result = tool_team_discuss(
            arguments["topic"],
            arguments.get("team", []),
            arguments.get("max_rounds", 0),
        )
    else:
        result = f"Error: Tool '{name}' tidak dikenal."
    return result


# ============================================================
# FUNGSI API (DENGAN RETRY)
# ============================================================

def _consume_stream(response) -> dict:
    """
    Konsumsi respons streaming SSE (format OpenAI/OpenRouter) dan susun ulang
    menjadi dict berbentuk SAMA seperti respons non-stream, agar process_response
    tidak perlu diubah:

        {"choices": [{"message": {...}, "finish_reason": ...}], "usage": {...}}

    Selama streaming, tiap potongan teks/argument tool di-hitung sebagai estimasi
    token REALTIME ke spinner — sehingga counter token menanjak hidup saat model
    sedang menghasilkan jawaban (bukan hanya melompat di akhir round).
    """
    # PENTING: respons SSE bertipe "text/event-stream"; requests men-default-kan
    # encoding-nya ke ISO-8859-1 (Latin-1). Tanpa override ini, karakter multi-byte
    # UTF-8 (emoji, dsb.) ter-decode per-byte → mojibake. Paksa UTF-8 agar utuh.
    # (decode_unicode=True memakai incremental decoder, jadi karakter yang terbelah
    # antar-chunk jaringan tetap tersusun benar.)
    response.encoding = "utf-8"

    content_parts = []
    tool_calls = {}      # index → {"id","type","function":{"name","arguments"}}
    finish_reason = None
    usage = None
    role = "assistant"

    for raw in response.iter_lines(decode_unicode=True):
        if not raw:
            continue
        # SSE: hanya baris "data:" yang berisi payload. Lewati komentar keep-alive
        # (mis. ": OPENROUTER PROCESSING") dan baris lain.
        if not raw.startswith("data:"):
            continue
        chunk_str = raw[5:].strip()
        if chunk_str == "[DONE]":
            break
        try:
            chunk = json.loads(chunk_str)
        except json.JSONDecodeError:
            continue

        if chunk.get("error"):
            return {"error": chunk["error"]}
        if chunk.get("usage"):
            usage = chunk["usage"]

        choices = chunk.get("choices") or []
        if not choices:
            continue
        ch = choices[0]
        delta = ch.get("delta") or {}

        if delta.get("role"):
            role = delta["role"]

        piece = delta.get("content")
        if piece:
            content_parts.append(piece)
            _spinner.add_live_chars(len(piece))

        for tc in (delta.get("tool_calls") or []):
            idx = tc.get("index", 0)
            slot = tool_calls.setdefault(
                idx,
                {"id": None, "type": "function",
                 "function": {"name": "", "arguments": ""}},
            )
            if tc.get("id"):
                slot["id"] = tc["id"]
            if tc.get("type"):
                slot["type"] = tc["type"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["function"]["name"] += fn["name"]
            if fn.get("arguments"):
                slot["function"]["arguments"] += fn["arguments"]
                _spinner.add_live_chars(len(fn["arguments"]))

        if ch.get("finish_reason"):
            finish_reason = ch["finish_reason"]

    # ── Susun ulang message akhir (bentuk identik respons non-stream) ──
    message = {"role": role}
    text = "".join(content_parts)
    message["content"] = text if text else None
    if tool_calls:
        message["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]

    data = {"choices": [{"message": message, "finish_reason": finish_reason}]}
    if usage:
        data["usage"] = usage
    return data


def _estimate_tokens(messages: list) -> int:
    """
    Estimasi kasar token riwayat (char/4, konsisten dengan counter Spinner).
    Sengaja sederhana & tanpa dependency; cenderung UNDER-estimate teks non-ASCII.
    """
    total = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            total += len(c)
        for tc in (m.get("tool_calls") or []):
            fn = tc.get("function") or {}
            total += len(fn.get("name") or "") + len(fn.get("arguments") or "")
        total += 16  # overhead per-pesan (role/pembungkus)
    return total // 4


def _drop_orphan_tools(messages: list) -> list:
    """
    Jaring pengaman integritas pasangan tool-call (cegah API 400) untuk riwayat
    tak rapi (sesi lama / diedit manual). DUA ARAH:
    - buang pesan 'tool' yang tool_call_id-nya tak dideklarasikan assistant; dan
    - buang assistant ber-tool_calls yang TIDAK semua id-nya dijawab pesan 'tool'.
    Pesan system/user tak disentuh. Di alur normal tak pernah aktif (segmen utuh).
    """
    answered = {m["tool_call_id"] for m in messages
                if m.get("role") == "tool" and m.get("tool_call_id")}
    out, declared = [], set()
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            tcs = m.get("tool_calls") or []
            if tcs:
                ids = [tc.get("id") for tc in tcs if tc.get("id")]
                if ids and all(i in answered for i in ids):
                    declared.update(ids)
                    out.append(m)
                # else: assistant dengan tool_calls tak-terjawab → buang (dangling)
            else:
                out.append(m)
        elif role == "tool":
            if m.get("tool_call_id") in declared:
                out.append(m)
            # else: tool yatim → buang
        else:
            out.append(m)
    return out


def _trim_history(messages: list, max_tokens: int = None, keep_recent: int = None) -> tuple:
    """
    Hard-trim DETERMINISTIK untuk PAYLOAD API — TIDAK memutasi input.
    Buang SEGMEN tertua (segmen = blok mulai role=='user' hingga 'user' berikutnya;
    interrupt bisa membuka segmen baru di tengah giliran), pertahankan pesan system
    di depan & minimal `keep_recent` pesan terbaru. Returns (messages_baru, dibuang).

    Karena pembuangan SELALU dari kepala & boundary di 'user', pasangan
    assistant(tool_calls)↔tool tak pernah terputus. Hasil TIDAK dijamin <=
    max_tokens bila lantai keep_recent / sisa 1 segmen menghalangi (lebih baik
    kirim sedikit kelebihan daripada merusak riwayat). OUTPUT LIMITS = lapis-1.
    """
    if max_tokens is None:
        max_tokens = config.MAX_HISTORY_TOKENS
    if keep_recent is None:
        keep_recent = config.KEEP_RECENT_MESSAGES
    if _estimate_tokens(messages) <= max_tokens:
        return messages, 0

    # Prefix system (tak pernah dibuang).
    i = 0
    head = []
    while i < len(messages) and messages[i].get("role") == "system":
        head.append(messages[i])
        i += 1
    body = messages[i:]

    # Pecah body jadi segmen (boundary: role == 'user').
    segments, cur = [], []
    for m in body:
        if m.get("role") == "user" and cur:
            segments.append(cur)
            cur = []
        cur.append(m)
    if cur:
        segments.append(cur)

    # Buang segmen dari KEPALA selama: >1 segmen, masih di atas ambang, & tak
    # melanggar lantai keep_recent.
    while len(segments) > 1:
        if _estimate_tokens(head + [m for s in segments for m in s]) <= max_tokens:
            break
        remaining = sum(len(s) for s in segments)
        if remaining - len(segments[0]) < keep_recent:
            break
        segments.pop(0)

    trimmed = _drop_orphan_tools(head + [m for s in segments for m in s])
    return trimmed, len(messages) - len(trimmed)


def chat(messages: list, temperature: float = 0.7, max_tokens: int = 16384,
         max_retries: int = MAX_RETRIES, retry_base_delay: float = RETRY_BASE_DELAY,
         include_tools: bool = True) -> dict:
    # Hard-trim riwayat HANYA untuk payload yang dikirim (transkrip pemanggil &
    # save_session tetap utuh). Notice maksimum sekali per giliran.
    sent, dropped = _trim_history(messages)
    if dropped and config.HISTORY_TRIM_NOTICE and not _spinner._trim_notice_shown:
        show_trim_notice(dropped, _estimate_tokens(sent))
        _spinner._trim_notice_shown = True

    payload = {
        "model": MODEL,
        "messages": sent,
        "temperature": temperature,
        "max_tokens": max_tokens,
        # Streaming → token bisa dihitung realtime saat respons mengalir.
        "stream": True,
        "stream_options": {"include_usage": True},  # kompat OpenAI
        "usage": {"include": True},                 # param native OpenRouter
    }
    if include_tools:
        payload["tools"] = TOOLS

    last_error = None

    for attempt in range(1, max_retries + 1):
        # Spinner animasi berjalan selama menunggu respons API.
        _spinner.start()
        _spinner.reset_live()  # estimasi output round ini mulai dari nol
        try:
            response = requests.post(API_URL, headers=HEADERS, json=payload,
                                     timeout=120, stream=True)
            response.raise_for_status()
            data = _consume_stream(response)
            if "error" in data:
                raise Exception(f"OpenRouter error: {data['error']}")
            # Fold token EXACT round ini ke total giliran. total_tokens (prompt +
            # completion) = token yang benar-benar diproses; dijumlah lintas round
            # = total giliran. Jika provider tak kirim usage, pakai estimasi output.
            usage = data.get("usage") or {}
            total = usage.get("total_tokens")
            _spinner.add_tokens(total if total else _spinner.estimate_live_tokens())
            _spinner.reset_live()
            return data

        except Exception as e:
            _spinner.reset_live()
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
                data = chat(messages, temperature=0.7, max_tokens=16384)
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
                    data = chat(messages, temperature=0.7, max_tokens=16384)
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

            try:
                result = execute_tool(tool_name, tool_args)
            except Exception as e:
                result = (
                    f"Error: Eksekusi tool '{tool_name}' gagal dengan exception: {type(e).__name__}: {e}. "
                    "Periksa nama parameter yang benar sesuai definisi tool, lalu coba lagi."
                )

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
                data = chat(messages, temperature=0.7, max_tokens=16384)
            except Exception as e:
                return f"Error saat interrupt: {e}", messages, True
            continue

        # ── Panggil model lagi dengan semua hasil tool ───────────
        show_thinking()
        data = chat(messages, temperature=0.7, max_tokens=16384)


# ============================================================
# SYSTEM PROMPT
# ============================================================

def _load_skills() -> str:
    """Baca skills.md sekali dan cache hasilnya agar tidak berulang kali buka file."""
    if not hasattr(_load_skills, "_cache"):
        skills_path = os.path.join(SCRIPT_DIR, "SKILL", "skills.md")
        try:
            with open(skills_path, "r", encoding="utf-8") as f:
                _load_skills._cache = f.read()
        except Exception:
            _load_skills._cache = ""
    return _load_skills._cache


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

    skills_content = _load_skills()
    skills_section = (
        "\n\n══════════════════════════════════════════════════════════════\n"
        "📋 SKILLS & BODY GUIDE — PANDUAN LENGKAP KEMAMPUANMU:\n"
        "══════════════════════════════════════════════════════════════\n"
        + skills_content
        + "\n══════════════════════════════════════════════════════════════\n"
        if skills_content else ""
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
        "FORMAT OUTPUT: Balasanmu otomatis di-render (markdown → terminal) dan "
        "diberi marker serta warna oleh sistem. Pemanggilan tool beserta hasilnya "
        "juga ditampilkan otomatis. Maka: tulis markdown yang bersih (heading #, "
        "bold **, list -, `inline code`, blok kode ```), dan JANGAN menulis sendiri "
        "marker seperti ⏺/⎿, garis ═══/┌─┐, kode warna ANSI, atau menyalin-ulang "
        "output mentah tool. Jangan pakai ✅/❌/⚠️ sebagai penanda status tool — "
        "cukup jelaskan hasilnya dengan kata-kata.\n\n"
        "Kamu adalah kura-kura yang bijaksana, sabar, dan teliti. "
        "Gunakan emoji 🐢 untuk menandai dirimu.\n\n"
        "📌 CATATAN PENTING TENTANG WORKSPACE & SKILL:\n"
        "Workspace (BASE_DIR / direktori kerja) = folder TEMPAT user menjalankan\n"
        "perintah `ruka` (current working directory), bukan folder instalasi.\n"
        "Jadi BASE_DIR bisa berbeda-beda tergantung di mana user berada.\n"
        "Namun SEMUA file di folder SKILL/ SELALU berada di folder tempat main.py berada.\n"
        "Gunakan path absolut untuk membaca file SKILL lainnya (pptSkill.md, browsingSkill.md, dll):\n"
        "Contoh: read_file('" + os.path.join(SCRIPT_DIR, "SKILL/pptSkill.md") + "')\n"
        "        read_file('" + os.path.join(SCRIPT_DIR, "SKILL/browsingSkill.md") + "')"
        + skills_section
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

    # ── Aktifkan prompt mengambang di bawah layar (jika TTY) ───
    global _footer
    idle_hint = (
        f"{Style.GREY}Ketik pesan · {Style.GREY_LIGHT}/help{Style.GREY} bantuan · "
        f"{Style.GREY_LIGHT}exit{Style.GREY} keluar{Style.RESET}"
    )
    _footer = FooterUI()
    if not _footer.arm(idle_hint=idle_hint):
        _footer = None  # fallback: terminal tak mendukung → mode linear

    # Mulai input reader thread sekali di awal (raw editor bila footer aktif)
    _start_input_reader()

    # ── Loop utama ─────────────────────────────────────────────
    try:
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
                if _footer_active():
                    _footer.clear_region()  # region-aware: footer tetap di bawah
                else:
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

            # ── /team — orchestrasi multi-agent ──────────────────────────
            if user_input.lower().startswith("/team"):
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print(
                        f"\n  {Style.WARN}■{Style.RESET}  "
                        f"{Style.GREY}Gunakan: {Style.GREY_LIGHT}/team <deskripsi tugas>{Style.RESET}"
                    )
                    continue
                task_desc = parts[1].strip()
                # Ubah user_input menjadi instruksi orchestrasi lalu
                # fall-through ke normal chat flow (tidak ada continue di sini).
                user_input = (
                    f"Bentuk tim dan mulai diskusi kolaboratif untuk topik berikut "
                    f"menggunakan tool 'discuss'. Tentukan 2-4 anggota tim dengan peran "
                    f"yang saling melengkapi sesuai jenis tugas (contoh — coding: "
                    f"Developer, Reviewer, Tester; perencanaan: Arsitek, Implementer, "
                    f"Risk_Analyst; penulisan: Penulis, Editor, Kritikus). "
                    f"Jangan isi parameter max_rounds — biarkan diskusi berlangsung "
                    f"sepanjang yang dibutuhkan sampai Koordinator puas.\n\n"
                    f"Topik:\n{task_desc}"
                )
                # (tidak ada continue — lanjut ke blok normal chat di bawah)

            # ── Slash command tak dikenal → jangan kirim ke model ───
            if user_input.startswith("/"):
                cmd = user_input.split()[0]
                print(f"\n  {Style.WARN}■{Style.RESET}  {Style.GREY}Perintah {Style.GREY_LIGHT}{cmd}{Style.GREY} tidak dikenal. Ketik {Style.GREY_LIGHT}/help{Style.GREY} untuk daftar perintah.{Style.RESET}")
                continue

            # ── Normal chat flow ────────────────────────────────────
            show_separator()
            messages.append({"role": "user", "content": user_input})

            # Mulai timer giliran — titik nol yang bertahan menembus semua tool call
            _spinner.begin_turn()
            try:
                show_thinking()
                data = chat(messages)
                reply, messages, was_interrupted = process_response(messages, data)

                # Total durasi giliran (sebelum mencetak apa pun yang lain)
                turn_secs = _spinner.end_turn()

                # Jawaban akhir asisten dengan marker ⏺ ala Claude Code
                _emit_agent_text(reply, interrupted=was_interrupted)

                if was_interrupted:
                    print(f"\n  {Style.GREY}■ Sesi agent diinterupsi. Kembali ke prompt utama.{Style.RESET}")

                # Ringkasan kecil & redup: berapa lama giliran ini berjalan + token
                show_turn_summary(turn_secs, _spinner.turn_tokens)

                # Auto-save setelah setiap exchange
                save_session(session_name, messages)

            except Exception as e:
                _spinner.end_turn()
                show_error(str(e)[:80])
                # Tetap save meski error
                save_session(session_name, messages)
    finally:
        # Kembalikan terminal ke keadaan normal (scroll region, termios, kursor).
        if _footer is not None:
            _footer.disarm()
            _footer = None


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # Pastikan folder sessions ada
    _ensure_sessions_dir()

    # ── Parse CLI arguments ──────────────────────────────────
    # Workspace default = cwd (folder tempat user memanggil; di-set di config.BASE_DIR).
    # Format: python main.py [workspace_path] [session_name]
    #   - python main.py                        → workspace = cwd, session auto
    #   - python main.py /path/to/workspace      → override workspace = path, session auto
    #   - python main.py /path/to/workspace nama → override workspace = path, session = nama
    #   - python main.py nama                   → workspace = cwd, session = nama
    #   - CLI commands (listSessions, dll)       → tetap jalan seperti biasa

    # Deteksi apakah argumen adalah CLI command (bukan path/session)
    cli_commands = {
        "help", "--help", "-h",
        "listSessions", "deleteSession", "renameSession",
        "clearSessions", "searchSessions",
    }

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        # ── CLI commands (jalan di workspace apapun) ────────
        if arg in ("help", "--help", "-h"):
            show_help()
        elif arg == "listSessions":
            show_session_list()
        elif arg == "deleteSession" and len(sys.argv) > 2:
            target = sys.argv[2]
            result = delete_session(target)
            print(result)
        elif arg == "renameSession" and len(sys.argv) > 3:
            old_name = sys.argv[2]
            new_name = sys.argv[3]
            result = rename_session(old_name, new_name)
            print(result)
        elif arg == "clearSessions":
            result = clear_sessions()
            print(result)
        elif arg == "searchSessions" and len(sys.argv) > 2:
            keyword = " ".join(sys.argv[2:])
            result = search_sessions(keyword)
            print(result)

        # ── Workspace path + optional session name ──────────
        elif not arg.startswith("-"):
            # Cek apakah argumen pertama adalah path atau nama session
            # Path absolut/relatif yang bukan CLI command → treat sebagai workspace
            potential_path = os.path.abspath(arg)
            potential_script_dir = os.path.dirname(potential_path)

            # Heuristic: jika argumen adalah folder yang ATAU berisi main.py → workspace
            # Jika tidak → treat sebagai nama session (backward compat)
            if os.path.isdir(potential_path):
                # User memberikan path workspace
                workspace_path = potential_path
                session_name = None

                # Cek apakah ada argumen kedua sebagai nama session
                if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
                    session_name = sys.argv[2]

                # Override BASE_DIR ke workspace baru
                # SESSIONS_DIR tetap di SCRIPT_DIR (folder main.py) — JANGAN diubah
                config.BASE_DIR = workspace_path

                if session_name:
                    chat_session(session_name)
                else:
                    chat_session()
            else:
                # Bukan folder → treat sebagai nama session (backward compat)
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
                _spinner.begin_turn()
                data = chat(msgs)
                reply, _, was_interrupted = process_response(msgs, data)
                turn_secs = _spinner.end_turn()
                _emit_agent_text(reply, interrupted=was_interrupted)
                show_turn_summary(turn_secs, _spinner.turn_tokens)
                print()
            except Exception as e:
                _spinner.end_turn()
                show_error(str(e)[:80])
    else:
        # Mode interaktif tanpa nama session → auto-generate
        chat_session()