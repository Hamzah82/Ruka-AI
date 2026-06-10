# 🐢 Ruka AI — Kura-Kura File & Terminal Agent

> **AI agent berbasis OpenRouter yang dapat mengelola file, folder, dan menjalankan perintah terminal langsung di perangkat lokal Anda.**

Ruka AI adalah agent CLI (Command Line Interface) yang terinspirasi dari karakter kura-kura — bijaksana, sabar, dan teliti. Dibangun dengan Python dan memanfaatkan model AI dari OpenRouter, Ruka AI mampu melakukan berbagai operasi file serta menjalankan perintah bash/shell secara otonom melalui percakapan bahasa natural.

---

## ✨ Fitur Utama

- **Manajemen File Lengkap** — Baca, tulis, hapus, salin, dan pindahkan file
- **Manajemen Folder** — Buat, hapus folder (termasuk rekursif), dan tampilkan struktur direktori dalam format tree
- **Eksekusi Terminal** — Jalankan perintah bash/shell langsung dari percakapan
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

### Mode Interaktif (Chat Session)

```bash
python main.py
```

Kemudian ketik perintah dalam bahasa natural:

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
