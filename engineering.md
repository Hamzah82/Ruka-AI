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
- [7. Session Management](#7-session-management)
- [8. Keamanan](#8-keamanan)
- [9. Error Handling & Retry Mechanism](#9-error-handling--retry-mechanism)
- [10. Konfigurasi](#10-konfigurasi)
- [11. API Reference](#11-api-reference)
- [12. Development Guide](#12-development-guide)
- [13. Troubleshooting](#13-troubleshooting)

---

## 1. Overview

Ruka AI adalah **CLI-based AI agent** yang memungkinkan user berinteraksi dengan sistem file dan terminal melalui bahasa natural. Agent ini menggunakan model AI dari OpenRouter sebagai "otak" dan mengeksekusi operasi lokal (file I/O, command execution) sebagai "tangan".

### Karakteristik Utama

- **Agentic** — AI dapat memutuskan sendiri tool mana yang perlu dipanggil, dalam urutan apa, dan bisa melakukan multi-step reasoning
- **Local-first** — Semua operasi file dan terminal berjalan di mesin lokal user, bukan di cloud
- **Session-based** — Percakapan disimpan secara persisten, memungkinkan melanjutkan kerja sebelumnya
- **Model-agnostic** — Mendukung model apapun yang tersedia di OpenRouter (default: `openrouter/owl-alpha`)

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
│  │   Session    │  │   Security   │  │    Output     │  │
│  │  Manager     │  │    Layer     │  │   Formatter   │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                │                   │          │
│  ┌──────▼────────────────▼───────────────────▼───────┐  │
│  │              CORE AGENT LOOP                       │  │
│  │                                                    │  │
│  │  1. Terima input user                              │  │
│  │  2. Kirim ke OpenRouter API                        │  │
│  │  3. Parse response (text atau tool_call)           │  │
│  │  4. Jika tool_call → eksekusi tool → kirim hasil   │  │
│  │  5. Ulangi sampai AI selesai (stop_reason=stop)    │  │
│  └──────────────────────┬────────────────────────────┘  │
│                         │                               │
│  ┌──────────────────────▼────────────────────────────┐  │
│  │              TOOL EXECUTOR                         │  │
│  │  read_file │ write_file │ exec_command │ ...       │  │
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
│  System Prompt   │ ← Berisi instruksi, daftar tools, session info
│  + Chat History  │ ← Semua pesan sebelumnya (context window)
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
│  → Tampilkan ke  │     │ tool_calls      │
│    user          │     │ → Eksekusi tool │
└──────────────────┘     │ → Kirim hasil   │
                         │   kembali ke AI │
                         │ → Loop ulang    │
                         └─────────────────┘
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

Seluruh logic ada di satu file: `main.py` (82 KB). Berikut breakdown per komponen:

### 4.1 Configuration Constants (Baris awal)

```
MODEL                    → Nama model OpenRouter yang digunakan
DEFAULT_CMD_TIMEOUT      → Timeout default untuk exec_command (detik)
MAX_RETRIES              → Maksimum retry pada kegagalan API
RETRY_BASE_DELAY         → Base delay untuk exponential backoff
BASE_DIR                 → Direktori kerja agent
SESSIONS_DIR             → Folder penyimpanan session
OPENROUTER_API_KEY       → API key (dari .env)
OPENROUTER_URL           → URL endpoint API
```

### 4.2 Tool Definitions (JSON Schema)

Setiap tool didefinisikan dalam format **OpenAI Function Calling Schema**:

```json
{
  "name": "read_file",
  "description": "Membaca isi file teks dari direktori kerja",
  "parameters": {
    "type": "object",
    "properties": {
      "filename": {
        "type": "string",
        "description": "Nama file yang ingin dibaca"
      }
    },
    "required": ["filename"]
  }
}
```

Total: **12 tools** yang tersedia untuk AI.

### 4.3 System Prompt Builder

Membangun system prompt yang berisi:

- Karakter dan personality agent (kura-kura bijaksana)
- Daftar tools yang tersedia
- Session info (nama session, path penyimpanan)
- Instruksi format output (markdown → terminal)
- Perintah khusus (/sessions, /new, /history, dll.)

### 4.4 Core Functions

```
build_system_prompt()     → Membangun system prompt
load_session()            → Memuat session dari file JSON
save_session()            → Menyimpan session ke file JSON
list_sessions()           → Mendapatkan daftar semua session
delete_session()          → Menghapus session
rename_session()          → Rename session
call_openrouter_api()     → Mengirim request ke OpenRouter dengan retry
execute_tool()            → Mengeksekusi tool yang dipanggil AI
format_markdown_to_terminal() → Konversi markdown ke styled terminal text
handle_slash_command()    → Memproses perintah /sessions, /new, dll.
main_loop()               → Agentic loop utama
```

### 4.5 Entry Point

```
main() → Parse argumen CLI → Load/buat session → Jalankan main_loop()
```

---

## 5. Agentic Loop — Cara Kerja Inti

Ini adalah jantung dari Ruka AI. Agentic loop memungkinkan AI melakukan multi-step reasoning dan tool execution secara otonom.

### Algoritma

```
function main_loop(session):
    while True:
        1. Terima input dari user
        2. Jika input adalah perintah khusus (/new, /exit, dll):
           → Handle dan continue
        3. Tambahkan user message ke session["messages"]
        4. Simpan session (auto-save)
        
        5. ┌─── AGENT ROUND LOOP ───┐
           │                        │
           │  a. Kirim semua        │
           │     messages ke        │
           │     OpenRouter API     │
           │                        │
           │  b. Parse response:    │
           │     - Jika ada         │
           │       tool_calls:      │
           │       → Eksekusi       │
           │         setiap tool    │
           │       → Tambahkan      │
           │         hasil ke       │
           │         messages       │
           │       → Loop round     │
           │         lagi           │
           │                        │
           │     - Jika hanya teks  │
           │       (stop):          │
           │       → Tampilkan      │
           │         ke user        │
           │       → Break round    │
           │         loop           │
           └────────────────────────┘
        
        6. Simpan session (auto-save)
        7. Kembali ke step 1
```

### Contoh Multi-Step Execution

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
  → Tampilkan ke user
  → Loop selesai
```

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
- `edit_file` — Mengedit isi file (replace/append/prepend)

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

**2. Tambahkan ke TOOLS JSON schema:**

```python
TOOLS.append({
    "name": "do_something",
    "description": "Deskripsi untuk AI",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {
                "type": "string",
                "description": "Deskripsi parameter"
            }
        },
        "required": ["param1"]
    }
})
```

**3. Tambahkan ke execute_tool dispatcher:**

```python
def execute_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "do_something":
        return tool_do_something(arguments["param1"])
    # ... existing tools
```

**Contoh implementasi edit_file:**

```python
elif name == "edit_file":
    operation = arguments["operation"]
    new_text = arguments["new_text"]
    old_text = arguments.get("old_text")
    result = tool_edit_file(arguments["filename"], operation, new_text, old_text)
```

---

## 7. Session Management

### Format Session File

Setiap session disimpan sebagai file JSON di folder `sessions/`:

```json
{
  "session_name": "nama-session",
  "created_at": "2025-07-01T14:30:22.123456",
  "updated_at": "2025-07-01T15:45:33.654321",
  "messages": [
    {
      "role": "system",
      "content": "Kamu adalah Ruka AI..."
    },
    {
      "role": "user",
      "content": "Tampilkan daftar file"
    },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": {
            "name": "list_files",
            "arguments": "{}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "call_abc123",
      "content": "file1.txt\nfile2.py\n..."
    }
  ]
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

---

## 8. Keamanan

### 8.1 Path Traversal Protection

Semua operasi file dibatasi hanya di dalam `BASE_DIR` (direktori kerja). Mekanisme:

```python
# Resolve path absolut
requested_path = os.path.abspath(os.path.join(base_dir, user_input))

# Cek apakah masih dalam base_dir
if not requested_path.startswith(base_dir):
    return "Error: Akses ditolak — path di luar direktori kerja"
```

Ini mencegah serangan seperti:

- `../../etc/passwd`
- `/etc/shadow`
- `../../../home/user/.ssh/id_rsa`

### 8.2 Dangerous Command Blocking

Perintah-perintah berikut diblokir dari `exec_command`:

- `rm -rf /` — Menghapus seluruh sistem
- `mkfs` — Format filesystem
- `dd if=/dev/zero` — Menghapus disk
- `shutdown` / `reboot` — Mematikan/mulai ulang sistem
- `format` — Format drive
- Dan perintah berbahaya lainnya

### 8.3 File Permission Handling

Setiap operasi file menggunakan try-catch untuk menangani:

- File tidak ditemukan
- Izin akses ditolak
- Disk penuh
- File sedang digunakan proses lain

### 8.4 Command Timeout

Setiap perintah terminal memiliki timeout default 60 detik untuk mencegah:

- Infinite loops
- Hanging processes
- Resource exhaustion

---

## 9. Error Handling & Retry Mechanism

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

Formula: `delay = RETRY_BASE_DELAY ^ retry_number`

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

## 10. Konfigurasi

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

## 11. API Reference

### OpenRouter API

**Endpoint:** `POST https://openrouter.ai/api/v1/chat/completions`

**Headers:**

```
Authorization: Bearer <OPENROUTER_API_KEY>
Content-Type: application/json
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
  "tool_choice": "auto",
  "max_tokens": 4096,
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

## 12. Development Guide

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

## 13. Troubleshooting

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

Untuk menambahkan debug output, tambahkan di `call_openrouter_api()`:

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
```

---

<div align="center">

**🐢 Ruka AI — Engineering Docs v1.0**

*Dokumentasi ini mencakup seluruh aspek teknis project Ruka AI.*
*Untuk pertanyaan atau kontribusi, silakan buka issue di repository.*

</div>
