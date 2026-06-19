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

- `read_file` — Membaca isi file teks dari direktori kerja
- `write_file` — Menulis atau membuat file teks baru
- `list_files` — Menampilkan daftar semua file di direktori kerja
- `delete_file` — Menghapus file dari direktori kerja
- `copy_file` — Menyalin file dari sumber ke tujuan
- `move_file` — Memindahkan atau me-rename file/folder
- `get_file_info` — Menampilkan info detail file/folder (ukuran, tanggal, izin)
- `create_folder` — Membuat folder baru
- `delete_folder` — Menghapus folder (opsional rekursif)
- `list_all` — Menampilkan struktur direktori lengkap dalam format tree
- `exec_command` — Menjalankan perintah terminal (bash/shell)

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

Gunakan `requirements.txt` untuk install semua dependensi sekaligus:

```bash
pip install -r requirements.txt
```

Atau install manual satu per satu:

```bash
pip install requests python-dotenv
```

**3. Konfigurasi API key:**

Buat file `.env` di root project:

```env
OPENROUTER_API_KEY=sk-or-v1-your-api-key-here
```

Atau salin dari template yang sudah disediakan:

```bash
cp .env.example .env
```

Lalu edit `.env` dan masukkan API key kamu.

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
python main.py listSessions
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
python main.py deleteSession kerja-proyek

# Dari dalam chat:
👤  Kamu: /delete-session kerja-proyek
```

### Rename Session

```bash
# Dari CLI:
python main.py renameSession nama-lama nama-baru

# Dari dalam chat:
👤  Kamu: /rename-session nama-lama nama-baru
```

### Tips Awal Session

Saat memulai session baru, ucapkan **"Hai"** terlebih dahulu ke Ruka AI. Hal ini membantu model AI memahami system prompt dengan lebih baik sebelum melanjutkan ke percakapan utama.

```
👤  Kamu: Hai
🤖  Ruka AI: Hai! Ada yang bisa saya bantu? 🐢
👤  Kamu: Tampilkan daftar file dan folder
```

Dengan memulai percakapan menggunakan sapaan, AI akan lebih responsif dan memahami konteks session yang sedang berjalan.

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

### Perintah Session dalam Chat (Slash Command)

- `/sessions` — Tampilkan daftar semua session tersimpan
- `/new` — Mulai session baru (session lama auto-save)
- `/history` — Tampilkan riwayat chat sesi saat ini
- `/delete-session <nama>` — Hapus session tertentu
- `/rename-session <lama> <baru>` — Rename session

> Slash command tetap menggunakan format kebab-case dengan prefix `/`.

### Perintah Session dari CLI

- `python main.py <nama>` — Load atau buat session dengan nama tertentu
- `python main.py listSessions` — Lihat daftar semua session
- `python main.py deleteSession <nama>` — Hapus session tertentu dari CLI
- `python main.py renameSession <lama> <baru>` — Rename session dari CLI
- `python main.py clearSessions` — Hapus semua session tanpa nama (auto-generated) dari CLI

> **Catatan:** CLI command menggunakan **camelCase** (tanpa tanda `-`), sedangkan slash command di dalam chat tetap menggunakan kebab-case dengan prefix `/`.

### Menghapus Session Tanpa Nama

```bash
python main.py clearSessions
```

Command ini akan menghapus semua session yang **tidak memiliki nama** (auto-generated), yaitu session dengan pola nama `session_YYYYMMDD_HHMMSS`. Session dengan nama custom yang kamu buat sendiri **tidak akan dihapus**.

Output contoh:

```
✅ 3 session auto-generated berhasil dihapus:
   • session_20250701_143022
   • session_20250702_091530
   • session_20250703_164510

📌 2 session custom (tidak dihapus):
   • kerja-proyek
   • catatan-harian
```

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
├── main.py           # Source code utama — seluruh logic agent
├── requirements.txt  # Dependensi Python yang dibutuhkan
├── .env.example      # Template konfigurasi API key
├── .env              # Konfigurasi API key (tidak di-push ke git)
├── .gitignore        # Daftar file/folder yang diabaikan git
├── LICENSE           # Lisensi MIT
├── sessions/         # Folder penyimpanan session (tidak di-push ke git)
│   ├── session_20250701_143022.json
│   ├── kerja-proyek.json
│   └── ...
└── README.md         # Dokumentasi project ini
```

---

## ⚙️ Konfigurasi

Variabel konfigurasi yang dapat diubah di `main.py`:

- `MODEL` — Default: `openrouter/owl-alpha` — Model AI yang digunakan via OpenRouter
- `DEFAULT_CMD_TIMEOUT` — Default: `60` — Timeout default untuk eksekusi perintah (detik)
- `MAX_RETRIES` — Default: `5` — Jumlah maksimum retry jika request gagal
- `RETRY_BASE_DELAY` — Default: `2` — Delay dasar untuk exponential backoff (detik)
- `BASE_DIR` — Default: Direktori script — Direktori kerja tempat file dikelola
- `SESSIONS_DIR` — Default: `sessions/` — Folder penyimpanan session

---

## 📦 Dependensi

- **requests** (>=2.28.0) — HTTP client untuk berkomunikasi dengan OpenRouter API
- **python-dotenv** (>=1.0.0) — Memuat variabel environment dari file `.env`

---

## 📄 Lisensi

Project ini dilisensikan di bawah **MIT License**. Silakan gunakan, modifikasi, dan distribusikan sesuai kebutuhan.

---

<div align="center">

**🐢 Dibuat dengan kesabaran oleh Hamzah82**

*Ruka AI — Kura-Kura yang bijaksana, sabar, dan teliti.*

</div>
