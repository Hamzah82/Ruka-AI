# Ruka AI — Engineering Documentation

> Dokumentasi teknis untuk developer yang ingin memahami, memodifikasi, atau berkontribusi pada project Ruka AI.

---

## Daftar Isi

- [1. Overview](#1-overview)
- [2. Arsitektur Sistem](#2-arsitektur-sistem)
- [3. Tech Stack](#3-tech-stack)
- [4. Struktur Kode](#4-struktur-kode)
- [5. Agentic Loop](#5-agentic-loop)
- [6. Tool System](#6-tool-system)
- [7. Interrupt Mechanism](#7-interrupt-mechanism)
- [8. FooterUI — Floating Prompt](#8-footerui--floating-prompt)
- [9. Terminal Formatter](#9-terminal-formatter)
- [10. Session Management](#10-session-management)
- [11. Keamanan](#11-keamanan)
- [12. Error Handling & Retry](#12-error-handling--retry)
- [13. Konfigurasi](#13-konfigurasi)
- [14. System Prompt](#14-system-prompt)
- [15. Auto-Update](#15-auto-update)
- [16. Development Guide](#16-development-guide)
- [17. Troubleshooting](#17-troubleshooting)

---

## 1. Overview

Ruka AI adalah **CLI-based AI agent** yang memungkinkan user berinteraksi dengan sistem file dan terminal melalui bahasa natural. Agent ini menggunakan model AI dari OpenRouter sebagai "otak" dan mengeksekusi operasi lokal (file I/O, command execution, multi-agent discussion) sebagai "tangan".

### Karakteristik Utama

- **Agentic** — AI memutuskan sendiri tool mana yang dipanggil, dalam urutan apa, multi-step
- **Local-first** — Semua operasi file dan terminal berjalan di mesin lokal
- **Workspace = cwd** — Agent bekerja di folder tempat user menjalankan `ruka`, bukan folder instalasi
- **Session-based** — Percakapan disimpan persisten di folder instalasi, bisa dilanjutkan
- **Model-agnostic** — Default `openrouter/owl-alpha`, bisa di-override via `RUKA_MODEL` env var
- **Interruptible** — Ketik `q` kapan saja untuk menghentikan proses
- **Floating prompt** — Prompt input mengambang di bawah layar via FooterUI (scroll region ANSI)

---

## 2. Arsitektur Sistem

```
┌─────────────────────────────────────────────────┐
│                USER (Terminal)                   │
│     FooterUI: prompt "❯" mengambang di bawah     │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│               AGENT LOOP (main.py)               │
│                                                 │
│  ┌────────────┐  ┌───────────┐  ┌────────────┐  │
│  │  Session   │  │ Security  │  │ Terminal   │  │
│  │  Manager   │  │  Layer    │  │ Formatter  │  │
│  └─────┬──────┘  └─────┬─────┘  └─────┬──────┘  │
│        │               │              │          │
│  ┌─────▼───────────────▼──────────────▼───────┐  │
│  │            CORE AGENTIC LOOP                │  │
│  │  1. Terima input dari FooterUI / linear     │  │
│  │  2. Kirim ke OpenRouter API                 │  │
│  │  3. Parse response (text atau tool_calls)   │  │
│  │  4. Jika tool_calls → eksekusi → loop ulang │  │
│  │  5. Cek interrupt ('q') setiap round        │  │
│  └─────────────────────┬───────────────────────┘  │
│                        │                          │
│  ┌─────────────────────▼───────────────────────┐  │
│  │              TOOL EXECUTOR (13 tools)        │  │
│  │  read_file │ write_file │ edit_file          │  │
│  │  list_files │ delete_file │ copy_file        │  │
│  │  move_file │ get_file_info │ create_folder   │  │
│  │  delete_folder │ list_all │ exec_command     │  │
│  │  discuss                                    │  │
│  └─────────────────────┬───────────────────────┘  │
└───────────────────────┼─────────────────────────┘
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
      ┌──────────┐ ┌────────┐ ┌─────────┐
      │  File    │ │Terminal│ │OpenRouter│
      │  System  │ │(bash)  │ │  API     │
      └──────────┘ └────────┘ └─────────┘
```

### Workspace vs Script Directory

Sejak workspace diubah ke model `cwd`:

| Variable | Nilai | Fungsi |
|---|---|---|
| `BASE_DIR` | `os.getcwd()` | Folder kerja AI (workspace user) |
| `SCRIPT_DIR` | `dirname(abspath(__file__))` | Folder instalasi (SKILL/, sessions/, .env) |

Ini memungkinkan alias `ruka` dipakai dari folder mana pun: `cd ~/proyek && ruka` → AI bekerja di `~/proyek`, tapi session dan file internal tetap di folder instalasi.

---

## 3. Tech Stack

### Bahasa & Runtime

- **Python 3.10+** — bahasa utama

### Dependensi

- **requests** (≥2.28.0) — HTTP client untuk OpenRouter API
- **python-dotenv** (≥1.0.0) — load `.env` dari folder instalasi
- **termios / tty** (stdlib, Unix only) — raw mode untuk FooterUI; fallback otomatis jika tidak tersedia

### External Services

- **OpenRouter API** — `https://openrouter.ai/api/v1/chat/completions` (OpenAI-compatible)

### Model Default

- **openrouter/owl-alpha** — ~1M token context window, dioptimalkan untuk agentic tool use
- Override: set `RUKA_MODEL=provider/model-name` di `.env` atau environment

---

## 4. Struktur Kode

`main.py` — **4641 baris**. Seluruh logic agent ada di sini.
`config.py` — **~120 baris**. Semua konstanta konfigurasi; tunable tanpa sentuh `main.py`.

### 4.1 config.py — Konstanta Konfigurasi

```
OPENROUTER_API_KEY   → API key (dari .env)
MODEL                → Model aktif (default owl-alpha, override via RUKA_MODEL)
API_URL              → https://openrouter.ai/api/v1/chat/completions
HEADERS              → HTTP headers untuk request API
BASE_DIR             → os.getcwd() — workspace user
SCRIPT_DIR           → dirname(__file__) — folder instalasi
SESSIONS_DIR         → SCRIPT_DIR/sessions/
DEFAULT_CMD_TIMEOUT  → 60 detik (exec_command)
MAX_RETRIES          → 5
RETRY_BASE_DELAY     → 5 detik (delays: 5s → 10s → 20s → 40s → 80s)
BLOCKED_COMMANDS     → List perintah yang diblokir
MAX_READ_LINES       → 20.000 baris (batas read_file tanpa offset/limit)
MAX_READ_CHARS       → 1.000.000 karakter
MAX_EXEC_OUTPUT_CHARS→ 200.000 karakter (stdout+stderr masing-masing)
BINARY_SNIFF_BYTES   → 8.192 byte (deteksi file biner)
MAX_HISTORY_TOKENS   → 800.000 token estimasi (trim riwayat sebelum kirim API)
KEEP_RECENT_MESSAGES → 1.000.000 (lantai keras pesan terbaru dipertahankan)
HISTORY_TRIM_NOTICE  → True (tampilkan notice saat trim)
```

### 4.2 Interrupt Mechanism

```
_input_queue           → queue.Queue — buffer semua input user
_interrupt_event       → threading.Event — flag interupsi
_input_reader()        → Thread daemon, baca stdin secara kontinyu
_check_interrupt_nonblock() → Cek queue non-blocking, deteksi 'q'
```

### 4.3 FooterUI

Kelas `FooterUI` — floating prompt di bawah layar via ANSI scroll region.
Lihat [Bagian 8](#8-footerui--floating-prompt) untuk detail.

### 4.4 Terminal Formatter

Kelas `TerminalFormatter` — konversi markdown ke styled terminal output.
Lihat [Bagian 9](#9-terminal-formatter) untuk detail.

### 4.5 Tool Definitions & Executor

- `TOOLS` array — 13 tool dalam format OpenAI Function Calling Schema (baris ~2370)
- `execute_tool(name, arguments)` — dispatcher ke fungsi tool masing-masing

### 4.6 Core Functions

```
get_system_prompt(session_name)   → Bangun system prompt
load_session(name)                → Load session dari JSON
save_session(name, messages)      → Simpan session ke JSON
list_sessions()                   → Daftar semua session
delete_session(name)              → Hapus session
rename_session(old, new)          → Rename session
call_openrouter_api(messages)     → Request ke API dengan retry
execute_tool(name, arguments)     → Eksekusi tool yang dipanggil AI
process_response(messages, data)  → Agentic loop — handle tool_calls & interrupt
chat_session(session_name)        → Loop utama interaksi user
check_for_updates()               → Cek & jalankan git pull saat startup
main()                            → Entry point CLI
```

### 4.7 Entry Point & CLI

```bash
python main.py                            # workspace=cwd, session timestamp
python main.py <namaSession>              # workspace=cwd, session tertentu
python main.py <workspacePath>            # override workspace
python main.py <workspacePath> <session>  # workspace + session tertentu
python main.py listSessions               # tampilkan semua session (CLI)
python main.py deleteSession <nama>       # hapus session (CLI)
python main.py renameSession <lama> <baru># rename session (CLI)
python main.py clearSessions              # hapus semua session auto-generated
python main.py searchSessions <keyword>   # cari session by nama
```

Slash commands dalam sesi:
```
/sessions           → daftar semua session
/new                → mulai session baru
/history            → tampilkan riwayat chat sesi ini
/delete <n> → hapus session
/rename <nama baru> → rename session aktif
/help               → tampilkan bantuan
/clear              → bersihkan layar
```

---

## 5. Agentic Loop

Jantung Ruka AI. AI dapat melakukan multi-step reasoning dan tool execution secara otonom.

### Algoritma chat_session()

```
1. Load atau buat session
2. Inisialisasi FooterUI (floating prompt)
3. Mulai _input_reader() thread

while True:
    4. Terima input user (FooterUI atau linear fallback)
    5. Handle perintah khusus (exit, /help, /sessions, dll.)
    6. Tambah user message ke messages[]
    7. Simpan session

    ┌── AGENT ROUND LOOP ──┐
    │  a. Cek interrupt     │
    │  b. Kirim messages[]  │
    │     ke OpenRouter API │
    │  c. Jika tool_calls:  │
    │     → Tampilkan narasi│
    │       (jika ada)      │
    │     → Eksekusi tool   │
    │     → Append hasil    │
    │     → Loop round lagi │
    │  d. Jika text (stop): │
    │     → Format output   │
    │     → Tampilkan user  │
    │     → Break loop      │
    │  e. Cek interrupt     │
    └───────────────────────┘

    8. Simpan session
    9. Kembali ke step 4
```

### Context Window & History Trim

Setiap round menambah pesan ke `messages[]` yang dikirim ulang ke API. Untuk mencegah "context length exceeded":

- `MAX_HISTORY_TOKENS = 800_000` — jika estimasi token melebihi ini, segmen riwayat tertua dibuang
- System message dan pesan terbaru selalu dipertahankan
- `HISTORY_TRIM_NOTICE = True` — satu baris notice ditampilkan saat trim terjadi
- Estimasi pakai rumus `len(text) / 4` (konservatif, UNDER-estimate teks Indonesia)

---

## 6. Tool System

### Daftar Tools (13 total)

| Tool | Fungsi |
|------|--------|
| `read_file` | Baca file teks; support `offset`, `limit`, `line_numbers` |
| `write_file` | Tulis/buat file teks |
| `edit_file` | Edit file: `replace`, `append`, `prepend`; support `replace_all` |
| `list_files` | Daftar file di workspace |
| `delete_file` | Hapus file |
| `copy_file` | Salin file |
| `move_file` | Pindah/rename file |
| `get_file_info` | Info detail file/folder |
| `create_folder` | Buat folder baru |
| `delete_folder` | Hapus folder (bisa rekursif) |
| `list_all` | Struktur direktori tree (max_depth default 3) |
| `exec_command` | Jalankan perintah terminal; timeout default 60s |
| `discuss` | Diskusi kolaboratif multi-agent dengan peran berbeda |

### Tool `discuss` (Multi-Agent Discussion)

Tool `discuss` menjalankan diskusi antara beberapa agen virtual dengan peran berbeda. Setiap anggota melihat seluruh riwayat diskusi sebelum giliran mereka. Koordinator hadir otomatis di akhir untuk merangkum.

```python
discuss(
    topic="Apakah arsitektur ini sudah optimal?",
    team=[
        {"name": "Developer", "role": "Fokus pada implementasi teknis"},
        {"name": "Reviewer", "role": "Kritis terhadap potensi bug"}
    ],
    max_rounds=0   # 0 = auto (default 2 putaran)
)
```

Catatan: `Koordinator` **jangan** dimasukkan ke `team` — muncul otomatis.

### Output Limits

Output tool dibatasi untuk mencegah context explosion:

- `read_file` tanpa offset/limit: maks `MAX_READ_LINES` baris atau `MAX_READ_CHARS` karakter
- `exec_command`: maks `MAX_EXEC_OUTPUT_CHARS` karakter per stdout/stderr
- File biner: dideteksi via `BINARY_SNIFF_BYTES` byte pertama, ditolak pembacaan

### Menambah Tool Baru

3 langkah:

1. Implementasi `tool_nama_baru(...)` — return string hasil atau error
2. Tambah entry JSON ke array `TOOLS` (baris ~2370)
3. Tambah `elif name == "nama_baru"` di `execute_tool()` (baris ~3641)

---

## 7. Interrupt Mechanism

User bisa mengetik `q` kapan saja selama agent bekerja untuk menghentikan proses.

### Komponen

- `_input_reader()` — thread daemon, terus baca stdin
- `_input_queue` — buffer semua input
- `_interrupt_event` — flag threading.Event
- `_check_interrupt_nonblock()` — polling non-blocking di setiap round

### Alur

1. Thread `_input_reader` berjalan di background sejak session dimulai
2. Semua input (termasuk karakter 'q') masuk ke `_input_queue`
3. Di tiap round agentic, `_check_interrupt_nonblock()` drain queue
4. Jika 'q' ditemukan → set `_interrupt_event`
5. Model diberi system message: "User meminta interupsi, selesaikan ringkas, jangan panggil tool lagi"
6. Setelah round saat ini selesai → kembali ke prompt utama

---

## 8. FooterUI — Floating Prompt

`FooterUI` mengelola prompt input `❯` yang mengambang di bawah layar via ANSI scroll region.

### Layout Terminal

```
┌─────────────────────────┐
│  baris 1..H-(2+L)       │  ← scroll region: output AI bergulir di sini
├─────────────────────────┤
│  baris H-1-L            │  ← garis pemisah ─────────────────
│  baris H-L              │  ← status/spinner ATAU hint idle
│  baris H-L+1 .. H       │  ← "❯ input..." (wrap ke L baris)
└─────────────────────────┘
```

Footer tinggi-variabel: `_reserved` tumbuh saat input panjang wrap ke banyak baris.

### Thread Safety

Satu `threading.RLock` menjaga setiap penulisan ke stdout (3 penulis: main/print, spinner, input thread). Footer memakai positioning absolut (`\033[r;cH`), tidak menggunakan save/restore cursor untuk menghindari drift antar-thread.

### Fallback

Jika terminal tidak mendukung (non-TTY, atau `_HAS_TERMIOS = False`), `_footer = None` dan prompt kembali ke mode linear biasa.

---

## 9. Terminal Formatter

`TerminalFormatter` mengkonversi markdown ke styled terminal output via ANSI escape codes.

### Fitur

| Markdown | Output Terminal |
|---|---|
| `# Header` | Judul TEAL + garis `═` |
| `## Header` | Subjudul HIJAU + garis `─` |
| `### Header` | Sub-subjudul dengan `▸` |
| `**bold**` | ANSI bold |
| `` `code` `` | Inline code warna HIJAU |
| ` ```block``` ` | Code block dengan border kotak |
| `\|tabel\|` | Tabel box-drawing characters |
| `> quote` | Blockquote dengan border `┃` |
| `- list` | Bullet KUNING, multi-level |
| `[link](url)` | CYAN underline |
| `---` | Horizontal rule |

Lebar default: **`shutil.get_terminal_size()`** (fail-safe, bukan hardcode).

---

## 10. Session Management

### Format Session File

```json
{
  "name": "nama-session",
  "created_at": "2026-06-01T14:30:22.123456",
  "updated_at": "2026-06-01T15:45:33.654321",
  "message_count": 10,
  "messages": [...]
}
```

Session disimpan di `SESSIONS_DIR` = `SCRIPT_DIR/sessions/` — selalu di folder instalasi, terlepas dari workspace user.

### Auto-Save

Session disimpan di 2 titik:
1. Setelah user mengirim pesan (sebelum AI memproses)
2. Setelah AI selesai merespons

### Session Commands Lengkap

| Command | Keterangan |
|---|---|
| `/sessions` | Daftar semua session |
| `/new` | Session baru |
| `/history` | Riwayat chat sesi ini |
| `/delete <nama>` | Hapus session |
| `/rename <nama baru>` | Rename session aktif |
| `python main.py listSessions` | CLI: list sessions |
| `python main.py clearSessions` | CLI: hapus semua session auto-generated |
| `python main.py searchSessions <kw>` | CLI: cari session by nama |

---

## 11. Keamanan

### Path Traversal Protection

Semua operasi file dibatasi ke `BASE_DIR` (workspace user):

```python
requested_path = os.path.abspath(os.path.join(BASE_DIR, user_input))
if not requested_path.startswith(BASE_DIR):
    return "Error: Akses ditolak — path di luar direktori kerja"
```

Mencegah: `../../etc/passwd`, `/etc/shadow`, dll.

### Blocked Commands

Didefinisikan di `config.BLOCKED_COMMANDS`. Saat ini diblokir:

```
rm -rf /    rm -rf /*    mkfs.    dd if=/dev/zero
shutdown    poweroff     reboot   :(){:|:&};:
del /s /q   rd /s /q     format c:
```

### Command Timeout

Default 60 detik per `exec_command`. Mencegah infinite loop dan resource exhaustion.

---

## 12. Error Handling & Retry

### Exponential Backoff

```
Retry 1: 5 detik
Retry 2: 10 detik
Retry 3: 20 detik
Retry 4: 40 detik
Retry 5: 80 detik
```

Formula: `delay = RETRY_BASE_DELAY * 2^(n-1)`, di mana `RETRY_BASE_DELAY = 5`.

### Error Types

- **Network errors** — koneksi terputus, DNS failure, timeout
- **API errors** — rate limit (429), server error (5xx), auth error (401)
- **JSON parse errors** — response tidak valid
- **Tool execution errors** — file tidak ditemukan, permission denied
- **Binary file** — ditolak saat read_file

### Graceful Degradation

Jika semua retry gagal, user menerima pesan error yang menjelaskan penyebabnya.

---

## 13. Konfigurasi

Semua konfigurasi ada di `config.py`. Edit file ini tanpa menyentuh `main.py`.

### Environment Variables (`.env` di SCRIPT_DIR)

```
OPENROUTER_API_KEY=sk-or-v1-xxxxx   # wajib
RUKA_MODEL=openrouter/model-name     # opsional, override model
```

### Mengganti Model

Via `.env`:
```
RUKA_MODEL=openrouter/anthropic/claude-sonnet-4
```

Via `config.py` (hardcode fallback):
```python
_DEFAULT_MODEL = "openrouter/owl-alpha"
```

### Tuning Output Limits

Edit di `config.py`:
```python
MAX_READ_LINES = 20_000         # baca file
MAX_EXEC_OUTPUT_CHARS = 200_000 # output command
MAX_HISTORY_TOKENS = 800_000    # context window trim
```

---

## 14. System Prompt

Dibangun oleh `get_system_prompt(session_name)`, dikirim sebagai pesan `system` pertama.

### Isi

1. Karakter & personality — "Ruka AI, agent kura-kura 🐢, bijaksana dan teliti"
2. Daftar 13 tools dan cara penggunaannya
3. Instruksi multi-step execution (tanpa konfirmasi user per langkah)
4. Instruksi format output — Bahasa Indonesia, bullet point, emoji 🐢
5. **Instruksi wajib baca `SKILL/skills.md`** via `read_file` saat awal session
6. Info session — nama, path, perintah session tersedia

### SKILL/ Directory

Dokumentasi internal yang dibaca model AI:

```
SKILL/
├── skills.md       # Capabilities, tools, batasan, best practices, orchestration
├── browsingSkill.md# Panduan browsing web (curl/lynx/python3)
├── pptSkill.md     # Panduan membuat presentasi PowerPoint
├── vercelSkill.md  # Panduan deploy via Vercel CLI
└── emailSkill.md   # Panduan kirim email via msmtp
```

---

## 15. Auto-Update

`check_for_updates()` dijalankan otomatis saat startup (`main()`).

### Alur

1. Jalankan `git fetch origin` di `SCRIPT_DIR`
2. Bandingkan `HEAD` vs `origin/HEAD`
3. Jika ada commit baru → jalankan `git pull --ff-only`
4. Jika berhasil → tampilkan notice, restart otomatis atau informasi ke user

Jika git tidak tersedia atau bukan git repo, update check dilewati secara silent.

---

## 16. Development Guide

### Setup

```bash
git clone https://github.com/Hamzah82/Ruka-AI.git
cd Ruka-AI
pip install -r requirements.txt
cp .env.example .env
# Edit .env, isi OPENROUTER_API_KEY
python main.py
```

### Install Alias

```bash
./install.sh   # membuat alias `ruka` agar bisa dipakai dari folder mana pun
```

### Testing

```bash
pytest                           # jalankan semua tests
python main.py test              # session bernama "test"
python main.py listSessions      # cek session
```

### Menambah Skill Baru

1. Buat `SKILL/namaSkill.md` dengan dokumentasi
2. Update `SKILL/skills.md` — tambah referensi ke skill baru
3. System prompt sudah menginstruksikan model membaca `SKILL/skills.md` di awal session

---

## 17. Troubleshooting

**"Error: API key tidak ditemukan"**
Buat `.env` di folder instalasi dan isi `OPENROUTER_API_KEY`.

**"Connection refused" / "Timeout"**
Cek koneksi internet. Retry mechanism sudah menangani ini otomatis (maks 5x).

**"Context length exceeded"**
Mulai session baru dengan `/new`. Atau turunkan `MAX_HISTORY_TOKENS` di `config.py`.

**Floating prompt tidak muncul**
Terminal tidak mendukung termios (non-TTY atau Windows). Fallback ke mode linear otomatis.

**Output markdown tidak terformat**
Terminal tidak mendukung ANSI escape codes. Gunakan terminal modern (iTerm2, Windows Terminal, dll.).

**Tool execution gagal terus**
Cek path — harus dalam `BASE_DIR` (workspace saat ini). Cek izin file/folder.

**Auto-update gagal**
Folder instalasi bukan git repo, atau tidak ada koneksi. Coba manual: `cd ~/Ruka-AI && git pull`.

---

## Spesifikasi Teknis

```
Language         : Python 3.10+
Dependencies     : requests, python-dotenv (+ termios stdlib)
Architecture     : Single-file CLI agent (main.py ~4641 baris) + config.py
AI Backend       : OpenRouter API (OpenAI-compatible)
Default Model    : openrouter/owl-alpha (~1M context window)
Model Override   : RUKA_MODEL env var atau config.py
Tools            : 13 (file ops, folder ops, exec_command, discuss)
Session Format   : JSON files di SCRIPT_DIR/sessions/
Workspace        : os.getcwd() — folder tempat user menjalankan `ruka`
Security         : Path traversal protection, command filter, timeout
Retry            : 5x, exponential backoff 5s → 80s
History Trim     : 800K token estimasi, deterministik (bukan LLM summary)
Output Limits    : 20K baris / 1M chars (read), 200K chars (exec)
Interrupt        : Queue-based real-time ('q' untuk stop)
UI               : FooterUI floating prompt (ANSI scroll region) + fallback linear
Output Format    : Markdown → TerminalFormatter (ANSI styled)
Auto-update      : git pull saat startup
Skills Dir       : SKILL/ (skills.md, browsingSkill.md, pptSkill.md, dll.)
```

---

## Struktur Project

```
Ruka-AI/
├── main.py              # Logic utama (~4641 baris)
├── config.py            # Semua konstanta konfigurasi
├── requirements.txt     # Dependensi Python
├── install.sh           # Setup alias `ruka`
├── pyproject.toml       # Project metadata & test config
├── conftest.py          # Pytest fixtures
├── engineering.md       # Dokumentasi teknis (file ini)
├── README.md            # Dokumentasi user
├── SECURITY.md          # Security policy
├── SKILL/               # Dokumentasi internal untuk model AI
│   ├── skills.md        # Capabilities utama (WAJIB dibaca model)
│   ├── browsingSkill.md # Panduan browsing web
│   ├── pptSkill.md      # Panduan PowerPoint
│   ├── vercelSkill.md   # Panduan Vercel deploy
│   └── emailSkill.md    # Panduan email via msmtp
├── sessions/            # Data session user (tidak di-push ke git)
│   └── *.json
└── .env                 # API key (tidak di-push ke git)
```
