# 🐢 Ruka AI — Kura-Kura File & Terminal Agent

> **AI agent berbasis OpenRouter yang dapat mengelola file, folder, dan menjalankan perintah terminal langsung di perangkat lokal Anda.**

Ruka AI adalah agent CLI (Command Line Interface) yang terinspirasi dari karakter kura-kura — bijaksana, sabar, dan teliti. Dibangun dengan Python dan memanfaatkan model AI dari OpenRouter, Ruka AI mampu melakukan berbagai operasi file serta menjalankan perintah bash/shell secara otonom melalui percakapan bahasa natural.

---

## ✨ Fitur Utama

- **Manajemen File Lengkap** — Baca, tulis, hapus, salin, dan pindahkan file
- **Manajemen Folder** — Buat, hapus folder (termasuk rekursif), dan tampilkan struktur direktori dalam format tree
- **Eksekusi Terminal** — Jalankan perintah bash/shell langsung dari percakapan
- **Session Management** — Simpan, muat, hapus, dan rename sesi percakapan dengan mudah
- **Multi-Step Agentic Loop** — AI dapat memanggil tool secara berantai dalam satu sesi (misalnya: list file → baca → edit → simpan)
- **Interupsi Real-Time** — Tekan `q` kapan saja untuk menghentikan proses yang sedang berjalan
- **Markdown to Terminal Formatter** — Output AI diformat dari markdown ke styled terminal text yang cantik
- **Retry dengan Exponential Backoff** — Otomatis retry hingga 5 kali jika request ke API gagal
- **Keamanan Terintegrasi** — Path traversal protection dan pemblokiran perintah berbahaya
- **Unlimited Rounds** — Tidak ada batas maksimum round per sesi

---

## 🛠️ Kemampuan Tools

| # | Tool | Deskripsi |
|---|------|-----------|
| 1 | `read_file` | Membaca isi file teks dari direktori kerja |
| 2 | `write_file` | Menulis atau membuat file teks baru |
| 3 | `list_files` | Menampilkan daftar semua file di direktori kerja |
| 4 | `delete_file` | Menghapus file dari direktori kerja |
| 5 | `copy_file` | Menyalin file dari sumber ke tujuan |
| 6 | `move_file` | Memindahkan atau me-rename file/folder |
| 7 | `get_file_info` | Menampilkan info detail file/folder (ukuran, tanggal, izin) |
| 8 | `create_folder` | Membuat folder baru |
| 9 | `delete_folder` | Menghapus folder (opsional rekursif) |
| 10 | `list_all` | Menampilkan struktur direktori lengkap dalam format tree |
| 11 | `exec_command` | Menjalankan perintah terminal (bash/shell) |

---

## 🚀 Instalasi

### Prasyarat

- **Python 3.10+**
- **pip** (Python package manager)
- **Akun OpenRouter** dengan API key

### Langkah Instalasi

**1. Clone repository:**

```bash
git clone https://github.com/Hamzah82/Ruka-AI.git
cd Ruka-AI
```

**2. Install dependensi:**

```bash
pip install requests python-dotenv
```

**3. Konfigurasi API key:**

Buat file `.env` di root project:

```env
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
```

**4. Jalankan:**

```bash
python main.py
```

---

## 💡 Contoh Penggunaan

### Mode Interaktif (Session Baru Otomatis)

```bash
python main.py
```

Session baru akan dibuat secara otomatis dengan nama berbasis timestamp (contoh: `session_20250701_143022`).

### Mode Interaktif (Session dengan Nama)

```bash
python main.py kerja-proyek
```

Jika session `kerja-proyek` sudah ada, percakapan sebelumnya akan dimulai. Jika belum, session baru akan dibuat.

### Melihat Daftar Session

```bash
python main.py list-sessions
```

Atau saat dalam sesi chat, ketik:

```
👤  Kamu: /sessions
```

### Mulai Session Baru

```
👤  Kamu: /new
```

Session saat ini akan otomatis tersimpan, lalu session baru dimulai.

### Melihat Riwayat Chat

```
👤  Kamu: /history
```

### Menghapus Session

```bash
# Dari CLI:
python main.py delete-session kerja-proyek

# Dari dalam chat:
👤  Kamu: /delete-session kerja-proyek
```

### Rename Session

```bash
# Dari CLI:
python main.py rename-session nama-lama nama-baru

# Dari dalam chat:
👤  Kamu: /rename-session nama-lama nama-baru
```

### Contoh Percakapan

```
👤  Kamu: Tampilkan daftar file dan folder
👤  Kamu: Baca isi file catatan.txt
👤  Kamu: Buat file todo.txt berisi daftar belanja
👤  Kamu: Hapus file lama.txt
👤  Kamu: Salin data.txt ke backup/data.txt
👤  Kamu: Buat folder baru bernama 'projects'
👤  Kamu: Jalankan perintah 'ls -la' di terminal
👤  Kamu: Cek penggunaan disk dengan 'df -h'
👤  Kamu: Tampilkan struktur direktori saat ini
👤  Kamu: /history
👤  Kamu: /sessions
👤  Kamu: /new
👤  Kamu: exit
```

### Mode Single Prompt

```bash
python main.py "Tampilkan semua file di direktori ini"
python main.py "Buat file hello.txt berisi 'Halo Dunia'"
python main.py "Jalankan perintah ping google.com -c 3"
```

### Interupsi Proses

Saat AI sedang memproses (multi-step), ketik `q` untuk menghentikan:

```
🔄  [Round 3] Ruka AI sedang memproses...
q
⏸️  INTERRUPT: Proses akan dihentikan setelah round saat ini selesai.
```

---

## 💾 Session Management

Ruka AI menyimpan semua riwayat percakapan secara otomatis di folder `sessions/` dalam format JSON. Setiap session berisi:

- **Nama session** — Identifier unik untuk sesi
- **Riwayat pesan** — Seluruh percakapan (system, user, assistant, tool)
- **Metadata** — Tanggal dibuat, tanggal diupdate, jumlah pesan

### Perintah Session dalam Chat

| Perintah | Deskripsi |
|----------|-----------|
| `/sessions` | Tampilkan daftar semua session tersimpan |
| `/new` | Mulai session baru (session lama auto-save) |
| `/history` | Tampilkan riwayat chat sesi saat ini |
| `/delete-session <nama>` | Hapus session tertentu |
| `/rename-session <lama> <baru>` | Rename session |

### Perintah Session dari CLI

| Perintah | Deskripsi |
|----------|-----------|
| `python main.py <nama>` | Load atau buat session dengan nama tertentu |
| `python main.py list-sessions` | Lihat daftar semua session |
| `python main.py delete-session <nama>` | Hapus session dari CLI |
| `python main.py rename-session <lama> <baru>` | Rename session dari CLI |

### Auto-Save

Session disimpan secara otomatis setelah setiap exchange (user prompt + AI response), sehingga riwayat percakapan tidak hilang meskipun program ditutup secara tidak terduga.

---

## 🔒 Keamanan

Ruka AI dilengkapi dengan beberapa lapisan keamanan:

- **Path Traversal Protection** — Semua path dibatasi hanya di dalam direktori kerja, akses ke luar direktori ditolak
- **Perintah Berbahaya Diblokir** — Perintah seperti `rm -rf /`, `mkfs`, `dd if=/dev/zero`, `shutdown`, `format`, dan sejenisnya otomatis ditolak
- **Izin File Diperiksa** — Penanganan error untuk file/folder yang tidak memiliki izin akses
- **Timeout Perintah** — Setiap perintah terminal memiliki batas waktu default 60 detik

---

## 📁 Struktur Project

```
Ruka-AI/
├── main.py          # Source code utama — seluruh logic agent
├── .env             # Konfigurasi API key (tidak di-push ke git)
├── .gitignore       # Daftar file/folder yang diabaikan git
├── sessions/        # Folder penyimpanan session (tidak di-push ke git)
│   ├── session_20250701_143022.json
│   ├── kerja-proyek.json
│   └── ...
└── README.md        # Dokumentasi project ini
```

---

## ⚙️ Konfigurasi

Variabel konfigurasi yang dapat diubah di `main.py`:

| Variabel | Default | Deskripsi |
|----------|---------|-----------|
| `MODEL` | `openrouter/owl-alpha` | Model AI yang digunakan via OpenRouter |
| `DEFAULT_CMD_TIMEOUT` | `60` | Timeout default untuk eksekusi perintah (detik) |
| `MAX_RETRIES` | `5` | Jumlah maksimum retry jika request gagal |
| `RETRY_BASE_DELAY` | `2` | Delay dasar untuk exponential backoff (detik) |
| `BASE_DIR` | Direktori script | Direktori kerja tempat file dikelola |
| `SESSIONS_DIR` | `sessions/` | Folder penyimpanan session |

---

## 📦 Dependensi

- **requests** — HTTP client untuk berkomunikasi dengan OpenRouter API
- **python-dotenv** — Memuat variabel environment dari file `.env`

---

## 📄 Lisensi

Project ini bersifat open source. Silakan gunakan, modifikasi, dan distribusikan sesuai kebutuhan.

---

<div align="center">

**🐢 Dibuat dengan kesabaran oleh Hamzah82**

*Ruka AI — Kura-Kura yang bijaksana, sabar, dan teliti.*

</div>
