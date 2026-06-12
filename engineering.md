# 🐢 Ruka AI — Engineering Documentation

> Dokumentasi teknis untuk developer yang ingin memahami, memodifikasi, atau berkontribusi pada project Ruka AI.

---

## 📋 Daftar Isi

- [1. Overview](#1-overview)
- [2. Arsitektur Sistem](#2-arsitektur-sistem)
- [3. Tech Stack](#3-tech-stack)
- [4. Struktur Kode](#4-struktur-kode)
- [5. Agentic Loop — Cara Kerja Inti](#5-agentic-loop--cara-kerja-inti)
- [6. Tool System](#6-tool-system)
- [7. Interrupt Mechanism](#7-interrupt-mechanism)
- [8. Terminal Formatter](#8-terminal-formatter)
- [9. Session Management](#9-session-management)
- [10. Keamanan](#10-keamanan)
- [11. Error Handling & Retry Mechanism](#11-error-handling--retry-mechanism)
- [12. Konfigurasi](#12-konfigurasi)
- [13. System Prompt](#13-system-prompt)
- [14. API Reference](#14-api-reference)
- [15. Browsing Skills](#15-browsing-skills)
- [16. Development Guide](#16-development-guide)
- [17. Troubleshooting](#17-troubleshooting)

---

## 1. Overview

Ruka AI adalah **CLI-based AI agent** yang memungkinkan user berinteraksi dengan sistem file dan terminal melalui bahasa natural. Agent ini menggunakan model AI dari OpenRouter sebagai "otak" dan mengeksekusi operasi lokal (file I/O, command execution) sebagai "tangan".

### Karakteristik Utama

- **Agentic** — AI dapat memutuskan sendiri tool mana yang perlu dipanggil, dalam urutan apa, dan bisa melakukan multi-step reasoning
- **Local-first** — Semua operasi file dan terminal berjalan di mesin lokal user, bukan di cloud
- **Session-based** — Percakapan disimpan secara persisten, memungkinkan melanjutkan kerja sebelumnya
- **Model-agnostic** — Mendukung model apapun yang tersedia di OpenRouter (default: `openrouter/owl-alpha`)
- **Interruptible** — User dapat mengetik `q` kapan saja untuk menghentikan proses yang sedang berjalan

---

## 2. Arsitektur Sistem

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      USER (Terminal)                     │
│                   Input: Bahasa Natural                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   AGENT LOOP (main.py)                   │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Session    │  │   Security   │  │   Terminal    │  │
│  │  Manager     │  │    Layer     │  │   Formatter   │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                │                   │          │
│  ┌──────▼────────────────▼───────────────────▼───────┐  │
│  │              CORE AGENT LOOP                       │  │
│  │                                                    │  │
│  │  1. Terima input user                              │  │
│  │  2. Kirim ke OpenRouter API                        │  │
│  │  3. Parse response (text atau tool_calls)          │  │
│  │  4. Jika tool_calls → eksekusi tool → kirim hasil  │  │
│  │  5. Ulangi sampai AI selesai (stop_reason=stop)    │  │
│  │  6. Cek interrupt ('q') setiap round               │  │
│  └──────────────────────┬────────────────────────────┘  │
│                         │                               │
│  ┌──────────────────────▼────────────────────────────┐  │
│  │              TOOL EXECUTOR                         │  │
│  │  read_file │ write_file │ edit_file │ exec_command  │  │
│  │  list_files │ delete_file │ copy_file │ move_file    │  │
│  │  get_file_info │ create_folder │ delete_folder     │  │
│  │  list_all                                          │  │
│  └──────────────────────┬────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌────────┐ ┌─────────┐
        │  File    │ │Terminal│ │OpenRouter│
        │  System  │ │(bash)  │ │  API     │
        └──────────┘ └────────┘ └─────────┘
```

### Data Flow

```
User Input
    │
    ▼
┌──────────────────┐
│  System Prompt   │ ← Berisi instruksi, daftar tools, session info,
│  + Chat History  │   instruksi baca skills.md saat awal session
│  + User Message  │ ← Input terbaru dari user
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  OpenRouter API  │ ← POST /api/v1/chat/completions
│  (AI Model)      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────┐
│  Response: Text  │     │ Response:       │
│  → Format ke     │     │ tool_calls      │
│    terminal      │     │ → Eksekusi tool │
│    via Terminal  │     │ → Kirim hasil   │
│    Formatter     │     │   kembali ke AI │
│  → Tampilkan     │     │ → Loop ulang    │
│    ke user       │     └─────────────────┘
└──────────────────┘
```

---

## 3. Tech Stack

### Bahasa Pemrograman

- **Python 3.10+** — Bahasa utama, dipilih karena ekosistem library yang kuat dan kemudahan prototyping

### Dependensi

- **requests** (>=2.28.0) — HTTP client untuk komunikasi dengan OpenRouter API
  - Dipilih karena: simple, reliable, tidak perlu async untuk use case ini
- **python-dotenv** (>=1.0.0) — Manajemen environment variable dari file `.env`
  - Memisahkan konfigurasi sensitif (API key) dari source code

### External Services

- **OpenRouter API** — Gateway AI yang menyediakan akses ke berbagai model LLM melalui satu API endpoint
  - Base URL: `https://openrouter.ai/api/v1`
  - Endpoint: `/chat/completions` (OpenAI-compatible)
  - Auth: Bearer token via `Authorization` header

### Model Default

- **openrouter/owl-alpha** — Foundation model dengan context window ~1M token, dioptimalkan untuk agentic workloads dan tool use

---

## 4. Struktur Kode

Seluruh logic ada di satu file: `main.py` (~88 KB, ~2200 baris). Berikut breakdown per komponen:

### 4.1 Configuration Constants (Baris awal)

```
MODEL                    → Nama model OpenRouter yang digunakan
DEFAULT_CMD_TIMEOUT      → Timeout default untuk exec_command (60 detik)
MAX_RETRIES              → Maksimum retry pada kegagalan API (5)
RETRY_BASE_DELAY         → Base delay untuk exponential backoff (2 detik)
BASE_DIR                 → Direktori kerja agent (folder script)
SESSIONS_DIR             → Folder penyimpanan session (sessions/)
OPENROUTER_API_KEY       → API key (dari .env)
API_URL                  → URL endpoint OpenRouter API
```

### 4.2 Interrupt Mechanism (Queue-Based)

Sistem interupsi berbasis **queue** yang memungkinkan user mengetik `q` kapan saja selama proses berjalan:

```
_input_reader()        → Thread daemon yang membaca stdin secara terus-menerus
_input_queue           → Queue yang menyimpan semua input user
_interrupt_event       → Threading event flag untuk sinyal interupsi
_check_interrupt_nonblock() → Cek queue non-blocking untuk deteksi 'q'
```

Alur interrupt:
1. `_input_reader()` berjalan di background thread, membaca stdin
2. Setiap input masuk ke `_input_queue`
3. Sebelum setiap round, `_check_interrupt_nonblock()` mengecek apakah ada 'q' di queue
4. Jika 'q' ditemukan → set `_interrupt_event` → model diminta berhenti setelah round saat ini
5. Model diberitahu via system message: "User telah meminta interupsi"

### 4.3 Terminal Formatter

Kelas `TerminalFormatter` mengkonversi markdown ke styled terminal output:
- Headers → styled dengan warna dan garis dekoratif
- Tabel → rendered dengan box-drawing characters (┌─┐│└┘)
- Code blocks → dengan border dan syntax highlighting warna
- Lists → bullet points dengan indentation multi-level
- Blockquotes → dengan border kiri
- Inline formatting → bold, italic, strikethrough, code, links

### 4.4 Tool Definitions (JSON Schema)

Setiap tool didefinisikan dalam format **OpenAI Function Calling Schema**:

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Membaca isi file teks dari direktori kerja.",
    "parameters": {
      "type": "object",
      "properties": {
        "filename": { "type": "string", "description": "Nama file yang ingin dibaca" }
      },
      "required": ["filename"]
    }
  }
}
```

Total: **12 tools** yang tersedia untuk AI.

### 4.5 System Prompt Builder

Membangun system prompt yang berisi:

- Karakter dan personality agent (kura-kura bijaksana)
- Daftar capabilities (membaca, menulis, menghapus, mengedit, dll.)
- Instruksi multi-step execution
- Instruksi format output (bullet point, bukan tabel markdown)
- **Instruksi wajib baca `skills.md` saat awal session** — model harus baca file ini sebelum mulai berinteraksi
- Session info (nama session, path penyimpanan, perintah session)

### 4.6 Core Functions

```
build_system_prompt()        → Membangun system prompt (alias: get_system_prompt)
load_session()               → Memuat session dari file JSON
save_session()               → Menyimpan session ke file JSON
list_sessions()              → Mendapatkan daftar semua session
delete_session()             → Menghapus session
rename_session()             → Rename session
call_openrouter_api()        → Mengirim request ke OpenRouter dengan retry (alias: chat)
execute_tool()               → Mengeksekusi tool yang dipanggil AI
format_markdown_to_terminal() → Konversi markdown ke styled terminal text (alias: format_reply)
TerminalFormatter.format()   → Class-based formatter untuk output terminal
process_response()           → Agentic loop — handle tool_calls dan interrupt
handle_slash_command()       → Memproses perintah /sessions, /new, dll.
main_loop()                  → Agentic loop utama (alias: chat_session)
```

### 4.7 Entry Point

```
main() → Parse argumen CLI → Load/buat session → Jalankan chat_session()
```

Mode CLI:
- `python main.py` → Session baru dengan nama timestamp
- `python main.py <nama>` → Load/buat session dengan nama tertentu
- `python main.py list-sessions` → Tampilkan daftar session
- `python main.py delete-session <nama>` → Hapus session
- `python main.py rename-session <lama> <baru>` → Rename session
- `python main.py "prompt"` → Single prompt mode (backward compatibility)

---

## 5. Agentic Loop — Cara Kerja Inti

Ini adalah jantung dari Ruka AI. Agentic loop memungkinkan AI melakukan multi-step reasoning dan tool execution secara otonom.

### Algoritma

```
function chat_session(session):
    while True:
        1. Terima input dari user (via _get_input)
        2. Jika input adalah perintah khusus (/new, /exit, dll):
           → Handle dan continue
        3. Tambahkan user message ke session["messages"]
        4. Simpan session (auto-save)
        
        5. ┌─── AGENT ROUND LOOP ───┐
           │                        │
           │  a. Cek interrupt      │
           │     ('q' di queue)     │
           │                        │
           │  b. Kirim semua        │
           │     messages ke        │
           │     OpenRouter API     │
           │                        │
           │  c. Parse response:    │
           │     - Tampilkan narasi │
           │       jika ada         │
           │       tool_calls       │
           │     - Jika ada         │
           │       tool_calls:      │
           │       → Eksekusi       │
           │         setiap tool    │
           │       → Kirim hasil    │
           │       → Loop round     │
           │         lagi           │
           │                        │
           │     - Jika hanya teks  │
           │       (stop):          │
           │       → Format output  │
           │       → Tampilkan      │
           │         ke user        │
           │       → Break round    │
           │         loop           │
           │                        │
           │  d. Cek interrupt      │
           │     SETELAH eksekusi   │
           │     tool              │
           └────────────────────────┘
        
        6. Simpan session (auto-save)
        7. Kembali ke step 1
```

### Multi-Step Execution

```
User: "Tampilkan daftar file, baca file README.md, lalu ringkas isinya"

Round 1:
  AI memutuskan → panggil list_files()
  Tool result → daftar file dikembalikan
  AI menerima hasil → masih butuh info lebih

Round 2:
  AI memutuskan → panggil read_file("README.md")
  Tool result → isi README.md dikembalikan
  AI menerima hasil → sudah cukup info

Round 3:
  AI memutuskan → tidak perlu tool lagi
  AI menghasilkan teks ringkasan
  → Tampilkan ke user (via TerminalFormatter)
  → Loop selesai
```

### Narasi Model

Jika model mengirim `content` (narasi/pikiran) **dan** `tool_calls` sekaligus, narasi ditampilkan sebelum tool dieksekusi. Ini memberi transparansi tentang apa yang sedang dipikirkan model.

Jika model langsung menjawab tanpa tools, narasi tidak ditampilkan (langsung return jawaban).

### Context Window Management

Setiap round menambahkan pesan baru ke `session["messages"]`. Semua pesan ini dikirim ulang ke API pada round berikutnya. Artinya:

- Semakin banyak round, semakin besar context yang dikirim
- Context window model menjadi batas maksimum (1.048.756 token untuk Owl Alpha)
- Jika context habis, API akan mengembalikan error

---

## 6. Tool System

### Daftar Tools

- `read_file` — Membaca isi file teks
- `write_file` — Menulis/membuat file teks
- `edit_file` — Mengedit isi file (replace/append/prepend)
- `list_files` — Daftar file di direktori kerja
- `delete_file` — Menghapus file
- `copy_file` — Menyalin file
- `move_file` — Memindahkan/menrename file
- `get_file_info` — Info detail file/folder
- `create_folder` — Membuat folder baru
- `delete_folder` — Menghapus folder (bisa rekursif)
- `list_all` — Struktur direktori dalam format tree
- `exec_command` — Menjalankan perintah terminal

### Tool Execution Flow

```
AI Response (tool_calls)
    │
    ▼
┌─────────────────────┐
│  Parse tool_call    │
│  - Ambil tool name  │
│  - Parse arguments  │
│    (JSON string)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Security Check     │
│  - Path validation  │
│  - Command filter   │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Execute Tool       │
│  - Call function    │
│  - Capture output   │
│  - Handle errors    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Return Result      │
│  - Format sebagai   │
│    tool response    │
│  - Tambahkan ke     │
│    messages[]       │
└─────────────────────┘
```

### Menambah Tool Baru

Untuk menambah tool baru, perlu melakukan 3 hal:

**1. Definisikan function:**

```python
def tool_do_something(param1: str) -> str:
    """Deskripsi apa yang dilakukan tool ini."""
    try:
        # Logic di sini
        return f"Hasil: {result}"
    except Exception as e:
        return f"Error: {e}"
```

**2. Tambahkan ke TOOLS JSON schema dan implementasi:**

Di bagian TOOLS array dan fungsi execute_tool().

**Contoh implementasi edit_file:**

```python
elif name == "edit_file":
    operation = arguments["operation"]
    new_text = arguments["new_text"]
    old_text = arguments.get("old_text")
    result = tool_edit_file(arguments["filename"], operation, new_text, old_text)
```

---

## 7. Interrupt Mechanism

Sistem interupsi real-time berbasis **queue** dan **threading** yang memungkinkan user menghentikan agent kapan saja.

### Komponen

- **`_input_reader()`** — Thread daemon yang terus membaca dari stdin
- **`_input_queue`** — `queue.Queue` sebagai buffer input
- **`_interrupt_event`** — `threading.Event` sebagai flag interupsi
- **`_check_interrupt_nonblock()`** — Cek queue non-blocking untuk deteksi 'q'

### Alur Kerja

```
1. _start_input_reader() dipanggil sekali di awal session
2. _input_reader() thread berjalan di background:
   - Terus membaca stdin via sys.stdin.readline()
   - Setiap line masuk ke _input_queue
3. Di setiap round, _check_interrupt_nonblock() dipanggil:
   - Mengosongkan queue secara non-blocking
   - Jika menemukan 'q' → set _interrupt_event
   - Item lain (bukan 'q') disimpan kembali ke queue
4. Model diberitahu via system message untuk berhenti
5. Setelah round saat ini selesai → kembali ke prompt utama
```

### Pesan Interrupt

Ketika user mengetik 'q', model menerima pesan:
```
[SYSTEM] User telah meminta interupsi (mengetik 'q'). 
Proses kamu telah diinterupsi setelah round N. 
Harap selesaikan jawaban akhir kamu sekarang dengan ringkas 
dan berikan status dari apa yang sudah berhasil dilakukan. 
Jangan memanggil tool lagi.
```

---

## 8. Terminal Formatter

Kelas `TerminalFormatter` mengkonversi markdown text ke styled terminal output yang cantif dan readable.

### Fitur Formatting

| Markdown Element | Terminal Output |
|-----------------|-----------------|
| `# Header` | Judul dengan warna TEAL + garis `═` |
| `## Header` | Subjudul dengan warna HIJAU + garis `─` |
| `### Header` | Sub-subjudul dengan `▸` |
| `**bold**` | **Bold** dengan ANSI bold |
| `*italic*` | *Italic* dengan ANSI italic |
| `` `code` `` | `Code` dengan warna HIJAU |
| ` ```code``` ` | Code block dengan border kotak |
| `\|tabel\|` | Tabel dengan box-drawing characters |
| `> quote` | Blockquote dengan border kiri `┃` |
| `- list` | Bullet dengan warna KUNING, multi-level |
| `[link](url)` | Link dengan warna CYAN underline |
| `---` | Horizontal rule dengan garis `─` |

### Kelas dan Fungsi

```
TerminalFormatter       → Class utama untuk format markdown → terminal
  .format(text)         → Main entry point
  ._format_headers()    → Format headers
  ._format_tables()     → Format tabel → box-drawing
  ._format_code_blocks()→ Format code blocks
  ._format_blockquotes()→ Format blockquotes
  ._format_lists()      → Format ordered/unordered lists
  ._format_inline_code()→ Format inline code
  ._format_bold()       → Format bold
  ._format_italic()     → Format italic
  ._format_strikethrough() → Format strikethrough
  ._format_links()      → Format links
  ._strip_inline_md()   → Hapus inline markdown syntax

format_reply(text)      → Shortcut function untuk TerminalFormatter.format()
```

### Lebar Terminal

Default lebar terminal: **70 karakter** (`TERM_WIDTH = 70`). Digunakan untuk padding dan garis dekoratif.

---

## 9. Session Management

### Format Session File

Setiap session disimpan sebagai file JSON di folder `sessions/`:

```json
{
  "name": "nama-session",
  "created_at": "2025-07-01T14:30:22.123456",
  "updated_at": "2025-07-01T15:45:33.654321",
  "message_count": 10,
  "messages": [...]
}
```

### Session Lifecycle

```
CREATE → LOAD → USE → SAVE → (repeat USE → SAVE) → DELETE/RENAME
```

- **Create:** Saat user memulai session baru (otomatis atau via `/new`)
- **Load:** Saat user menjalankan `python main.py <nama-session>`
- **Use:** Setiap interaksi user-AI
- **Save:** Otomatis setelah setiap exchange (user prompt + AI response)
- **Delete:** Via `/delete-session <nama>` atau CLI
- **Rename:** Via `/rename-session <lama> <baru>` atau CLI

### Auto-Save Mechanism

Session disimpan pada 2 titik:

1. Setelah user mengirim pesan (sebelum AI memproses)
2. Setelah AI selesai merespons

Ini memastikan tidak ada data yang hilang meskipun program crash.

### Session Backup

Folder `sessions/backups/` berisi backup dari session-session sebelumnya. Berguna untuk recovery jika session utama corrupt.

---

## 10. Keamanan

### 10.1 Path Traversal Protection

Semua operasi file dibatasi hanya di dalam `BASE_DIR` (direktori kerja). Mekanisme:

```python
# Resolve path absolut
requested_path = os.path.abspath(os.path.join(BASE_DIR, user_input))

# Cek apakah masih dalam BASE_DIR
if not requested_path.startswith(BASE_DIR):
    return "Error: Akses ditolak — path di luar direktori kerja"
```

Ini mencegah serangan seperti:

- `../../etc/passwd`
- `/etc/shadow`
- `../../../home/user/.ssh/id_rsa`

### 10.2 Dangerous Command Blocking

Perintah-perintah berikut diblokir dari `exec_command`:

- `rm -rf /` — Menghapus seluruh sistem
- `mkfs` — Format filesystem
- `dd if=/dev/zero` — Menghapus disk
- `shutdown` / `reboot` — Mematikan/mulai ulang sistem
- `format` — Format drive
- Dan perintah berbahaya lainnya

### 10.3 File Permission Handling

Setiap operasi file menggunakan try-catch untuk menangani:

- File tidak ditemukan
- Izin akses ditolak
- Disk penuh
- File sedang digunakan proses lain

### 10.4 Command Timeout

Setiap perintah terminal memiliki timeout default 60 detik untuk mencegah:

- Infinite loops
- Hanging processes
- Resource exhaustion

---

## 11. Error Handling & Retry Mechanism

### Exponential Backoff

Saat request ke OpenRouter API gagal, sistem melakukan retry dengan exponential backoff:

```
Retry 1: tunggu 2^1 = 2 detik
Retry 2: tunggu 2^2 = 4 detik
Retry 3: tunggu 2^3 = 8 detik
Retry 4: tunggu 2^4 = 16 detik
Retry 5: tunggu 2^5 = 32 detik
Total maksimum waktu retry: 62 detik
```

Formula: `delay = RETRY_BASE_DELAY * 2^(retry_number - 1)`

### Error Types yang Ditangani

- **Network errors** — Koneksi terputus, DNS failure, timeout
- **API errors** — Rate limit (429), server error (5xx), auth error (401)
- **JSON parse errors** — Response tidak valid
- **Tool execution errors** — File tidak ditemukan, permission denied
- **Keyboard interrupt** — User menekan Ctrl+C

### Graceful Degradation

Jika semua retry gagal:

```
"Maaf, terjadi masalah koneksi setelah 5x percobaan. 
Silakan coba lagi nanti. (Error: <detail error>)"
```

---

## 12. Konfigurasi

### Environment Variables (.env)

```
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
```

### Runtime Configuration (main.py)

```
MODEL = "openrouter/owl-alpha"
  → Ganti ke model lain yang didukung OpenRouter
  → Contoh: "openrouter/anthropic/claude-sonnet-4"

DEFAULT_CMD_TIMEOUT = 60
  → Timeout untuk exec_command dalam detik
  → Naikkan untuk perintah yang butuh waktu lama (compile, download)

MAX_RETRIES = 5
  → Jumlah maksimum retry pada kegagalan API

RETRY_BASE_DELAY = 2
  → Base delay untuk exponential backoff

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
  → Direktori kerja agent
  → Ubah ke path lain jika ingin agent bekerja di direktori berbeda

SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
  → Folder penyimpanan session
```

### Mengganti Model

Edit konstanta `MODEL` di `main.py`:

```python
MODEL = "openrouter/anthropic/claude-sonnet-4"
```

Atau gunakan model gratis:

```python
MODEL = "openrouter/google/gemini-2.0-flash-001"
```

---

## 13. System Prompt

System prompt dibangun oleh `get_system_prompt()` dan dikirim sebagai pesan `system` pertama di setiap session.

### Isi System Prompt

```
1. Karakter & Personality
   - "Kamu adalah Ruka AI, agent kura-kura (turtle)..."
   - Bijaksana, sabar, teliti
   - Gunakan emoji 🐢

2. Daftar Kemampuan
   - Manajemen file (baca, tulis, hapus, salin, pindah, edit)
   - Manajemen folder (buat, hapus, list)
   - Eksekusi terminal (bash)
   - Multi-step tool calling

3. Instruksi Multi-Step
   - Boleh memanggil tools secara berantai
   - Lakukan semua langkah tanpa konfirmasi user
   - Konfirmasi hasil akhir

4. Instruksi Output
   - Bahasa Indonesia
   - Bullet point (bukan tabel markdown)
   - Emoji 🐢

5. ═══ INSTRUKSI AWAL SESSION ═══
   - WAJIB baca 'skills.md' via read_file
   - Berisi: daftar tools, keamanan, agentic loop,
     gaya komunikasi, tips, daftar tool TIDAK ADA

6. Session Info (jika ada)
   - Nama session, path, perintah session
```

### Instruksi Baca skills.md

Saat session baru dimulai, system prompt berisi instruksi wajib:

```
Baca file 'skills.md' menggunakan tool read_file untuk memahami:
   - Daftar 12 tools yang tersedia dan cara menggunakannya
   - Batasan keamanan dan path traversal protection
   - Alur kerja agentic loop dan multi-step execution
   - Panduan gaya komunikasi (Bahasa Indonesia + emoji 🐢)
   - Tips & best practices untuk operasi file
   - Daftar tool yang TIDAK ADA (jangan panggil)
```

Ini memastikan model selalu punya context tentang capabilities-nya di setiap session baru.

---

## 14. API Reference

### OpenRouter API

**Endpoint:** `POST https://openrouter.ai/api/v1/chat/completions`

**Headers:**

```
Authorization: Bearer <OPENROUTER_API_KEY>
Content-Type: application/json
HTTP-Referer: https://myapp.com
X-Title: Ruka AI - Kura-Kura Agent
```

**Request Body:**

```json
{
  "model": "openrouter/owl-alpha",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": null, "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "...", "content": "..."}
  ],
  "tools": [...],
  "max_tokens": 2000,
  "temperature": 0.7
}
```

**Response:**

```json
{
  "id": "gen-xxx",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Response text atau null jika tool_calls",
      "tool_calls": [...]
    },
    "finish_reason": "stop" | "tool_calls" | "length"
  }]
}
```

---

## 15. Browsing Skills

Ruka AI memiliki kemampuan browsing web yang didokumentasikan di `browsingSkill.md`.

### Tools yang Tersedia

- **curl** — HTTP requests dari terminal
- **lynx** — Text-based web browser (dump HTML ke teks)
- **w3m** — Text-based web browser alternatif
- **python3** — HTTP requests via urllib, parsing HTML

### Search Engine

| Engine | Status | URL |
|--------|--------|-----|
| DuckDuckGo HTML | ✅ Utama | `https://html.duckduckgo.com/html/?q=QUERY` |
| DuckDuckGo Lite | ✅ Alternatif | `https://lite.duckduckgo.com/lite/?q=QUERY` |
| DuckDuckGo API | ✅ JSON | `https://api.duckduckgo.com/?q=QUERY&format=json` |
| Bing | ✅ Berat | `https://www.bing.com/search?q=QUERY` |
| Mojeek | ✅ Privacy | `https://www.mojeek.com/search?q=QUERY` |
| Brave Search | ⚠️ Sebagian | `https://search.brave.com/search?q=QUERY` |
| Google | ❌ Diblokir | Membutuhkan JavaScript |

### Rate Limiting Strategy

- Delay 3-5 detik antar request ke engine yang sama
- Rotasi search engine jika satu gagal
- Cache hasil — jangan request ulang query yang sama
- Exponential backoff: 2s → 4s → 8s, lalu pindah engine
- Prioritaskan API daripada scrape HTML

---

## 16. Development Guide

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/Hamzah82/Ruka-AI.git
cd Ruka-AI

# Buat virtual environment (opsional, recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependensi
pip install -r requirements.txt

# Setup API key
cp .env.example .env
# Edit .env, masukkan API key

# Jalankan
python main.py
```

### Testing

```bash
# Test dengan session bernama "test"
python main.py test

# Test single prompt
python main.py "Tampilkan daftar file"

# Test session management
python main.py list-sessions
python main.py delete-session test
```

### Git Workflow

```bash
# Buat branch baru
git checkout -b fitur-baru

# Commit perubahan
git add .
git commit -m "feat: menambahkan fitur X"

# Push ke remote
git push origin fitur-baru
```

### Code Style

- Gunakan type hints pada function parameters
- Dokumentasi dalam Bahasa Indonesia
- Error messages dalam Bahasa Indonesia
- Emoji 🐢 untuk branding konsisten

---

## 17. Troubleshooting

### Masalah Umum

**1. "Error: API key tidak ditemukan"**

Penyebab: File `.env` tidak ada atau API key belum diisi.
Solusi: Buat file `.env` dan masukkan API key yang valid.

**2. "Error: Connection refused" atau "Timeout"**

Penyebab: Tidak ada koneksi internet atau OpenRouter down.
Solusi: Cek koneksi internet, cek status OpenRouter di https://openrouter.ai

**3. "Error: Context length exceeded"**

Penyebab: Percakapan terlalu panjang, melebihi context window model.
Solusi: Mulai session baru dengan `/new` atau gunakan model dengan context window lebih besar.

**4. Session tidak tersimpan**

Penyebab: Folder `sessions/` tidak ada atau tidak bisa ditulis.
Solusi: Pastikan folder `sessions/` ada dan memiliki izin tulis.

**5. Tool execution gagal terus**

Penyebab: Path traversal atau permission issue.
Solusi: Cek path yang diminta, pastikan dalam direktori kerja dan memiliki izin.

**6. Output markdown tidak terformat dengan baik**

Penyebab: Terminal tidak mendukung ANSI escape codes.
Solusi: Gunakan terminal modern (Windows Terminal, iTerm2, dll.)

### Debug Mode

Untuk menambahkan debug output, tambahkan di fungsi `chat()`:

```python
print(f"[DEBUG] Request: {json.dumps(payload, indent=2)}")
print(f"[DEBUG] Response: {response.text}")
```

---

## 📊 Spesifikasi Teknis Ringkas

```
Language        : Python 3.10+
Dependencies    : requests, python-dotenv
Architecture    : Single-file CLI agent with tool-calling loop (12 tools)
AI Backend      : OpenRouter API (OpenAI-compatible)
Default Model   : openrouter/owl-alpha (1M context window)
Session Format  : JSON files
Security        : Path traversal protection, command filtering, timeout
Max Retries     : 5 (exponential backoff)
Session Storage : Local filesystem (sessions/)
Default Timeout : 60 seconds (exec_command)
Max Tokens      : 2000 (API request)
Temperature     : 0.7 (API request)
Interrupt       : Queue-based, real-time ('q' to interrupt)
Output Format   : Markdown → TerminalFormatter (styled terminal)
Browsing        : DuckDuckGo, Bing, Mojeek, Brave, Yahoo (via lynx/curl/python3)
Key Files       : main.py, skills.md, engineering.md, browsingSkill.md
Runtime Files   : sessions/*.json, sessions/backups/*.json
```

---

## 📁 Struktur Project

Berikut hanya file/folder yang merupakan bagian dari project (sesuai `.gitignore`):

```
Ruka-AI/
├── main.py              # Source code utama — seluruh logic agent (~88 KB, ~2200 baris)
├── requirements.txt     # Dependensi Python
├── LICENSE              # Lisensi MIT
├── README.md            # Dokumentasi project untuk user
├── engineering.md       # Dokumentasi teknis untuk developer (file ini)
├── skills.md            # Panduan capabilities & body agent (dibaca model di awal session)
├── browsingSkill.md     # Panduan browsing & web scraping
├── sessions/            # Folder penyimpanan session (tidak di-push ke git)
│   ├── *.json           # Session files (nama tergantung session)
│   └── backups/         # Backup session lama
```

> **Catatan:** File `.env`, `.env.example`, `__pycache__/`, `*.pyc`, `build/`, `dist/`, `*.egg-info/`, dan file/folder lain yang ada di `.gitignore` bukan bagian dari project. Folder `sessions/` ada di `.gitignore` karena berisi data lokal user.

---

<div align="center">

**🐢 Ruka AI — Engineering Docs v2.0**

*Dokumentasi ini mencakup seluruh aspek teknis project Ruka AI.*
*Terakhir diupdate: 2026-06-11*

</div>
