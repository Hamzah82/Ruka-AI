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
- **UI/UX ala Claude Code** — Tampilan terminal bersih & minimalis: panel sambutan rounded, marker `⏺`/`⎿` untuk tool & jawaban, prompt chevron `❯`, palet coral hangat, dan spinner animasi dengan timer berjalan
- **Interupsi Real-Time** — Tekan `q` kapan saja untuk menghentikan proses yang sedang berjalan
- **Markdown to Terminal Formatter** — Output AI diformat dari markdown ke styled terminal text yang rapi (header, list, code block, tabel)
- **Retry dengan Exponential Backoff** — Otomatis retry hingga 5 kali jika request ke API gagal
- **Lapisan Keamanan Best-Effort** — Pembatasan path (realpath+commonpath ke BASE_DIR/SCRIPT_DIR), denylist perintah destruktif (best-effort, **bukan sandbox**), scrub API key dari env subprocess, dan cap output. Lihat bagian [Keamanan](#-keamanan) untuk model ancaman
- **Unlimited Rounds** — Tidak ada batas maksimum round per sesi
- **Workspace = Folder Pemanggil** — Workspace otomatis mengikuti folder tempat kamu menjalankan perintah (cwd). Pasang alias `ruka` lewat `install.sh`, lalu `cd` ke folder mana pun dan ketik `ruka`. Bisa juga di-override dengan `python main.py <path> <namaSesi>`. Folder `SKILL/`, `sessions/`, dan `.env` selalu diakses dari folder instalasi
- **Konfigurasi Fleksibel via CLI** — Ubah endpoint API, model AI, dan API key dengan mudah menggunakan command `ruka change` (atau `ruka model` untuk ganti model saja). Konfigurasi disimpan di `config.json` dan aman dari commit Git
- **Ganti Model dalam Sesi** — Slash command `/model <namaModel>` untuk mengganti model AI aktif tanpa restart, lengkap dengan **sistem alias** supaya tidak perlu mengetik nama model panjang: `/model set <alias>|<namaModel>` lalu cukup `/model <alias>`

---

## 🎨 Tampilan

Ruka AI mengadopsi gaya antarmuka **bersih dan minimalis ala Claude Code** — fokus pada konten, bukan bingkai yang ramai.

**Layar sambutan:**

```
╭────────────────────────────────────────────────────────────────╮
│ ✻ Selamat datang di Ruka AI                                    │
│                                                                │
│ Agen kura-kura untuk file, folder & terminal.                  │
│ Bijak, sabar, teliti. 🐢                                       │
╰────────────────────────────────────────────────────────────────╯

  cwd      • ~/Ruka-AI
  model    • meng/deepseek-v4-flash
  session  • kerja-proyek (42 pesan · dibuat 2026-06-20 14:30)

  Ketik /help untuk bantuan, exit untuk keluar, q untuk interupsi.

  Coba sesuatu seperti:
  ❯ Tampilkan daftar file dan folder
  ❯ Baca isi file catatan.txt lalu ringkas
  ❯ Buat file todo.txt berisi daftar belanja
```

**Saat percakapan berlangsung** — prompt chevron `❯`, pemanggilan tool ditandai `⏺` dengan ringkasan hasil `⎿`, dan jawaban akhir ber-marker `⏺`:

```
❯ Baca config.py lalu jelaskan isinya

  ⏺ Read(config.py)
    ⎿  import os  +2 baris

  ⏺ Bash(wc -l config.py)
    ⎿  76 config.py

  ⏺ File config.py berisi konfigurasi utama:

    • MODEL — model AI yang dipakai
    • MAX_RETRIES — jumlah retry saat API gagal

  Total 76 baris.

  ⎿ selesai dalam 12s
```

> Saat menunggu respons API, spinner animasi berdenyut menampilkan status & timer:
> `✷  Menelaah… (3s · q untuk interupsi)`
>
> Timer berjalan untuk **satu giliran penuh** — dari prompt user sampai jawaban akhir — dan tidak ter-reset di antara pemanggilan tool. Setelah selesai, durasi total ditampilkan sebagai ringkasan kecil & redup: `⎿ selesai dalam 12s`.

Elemen visual: aksen **coral** hangat sebagai warna utama, skala abu-abu berlapis untuk teks sekunder, titik status **hijau** (sukses) / **merah** (error) pada setiap tool, serta panel rounded-corner `╭─╮`.

---

## 🛠️ Kemampuan Tools (12 Total)

**Tangan Kanan (File Operations):**
- `read_file` — Membaca isi file teks dari direktori kerja
- `write_file` — Menulis atau membuat file teks baru
- `edit_file` — Mengedit isi file (replace, append, prepend)
- `delete_file` — Menghapus file dari direktori kerja
- `copy_file` — Menyalin file dari sumber ke tujuan
- `move_file` — Memindahkan atau me-rename file/folder

**Tangan Kiri (Folder Operations):**
- `create_folder` — Membuat folder baru
- `delete_folder` — Menghapus folder (opsional rekursif)
- `list_all` — Menampilkan struktur direktori lengkap dalam format tree

**Mata & Telinga (Information Gathering):**
- `list_files` — Menampilkan daftar semua file di direktori kerja
- `get_file_info` — Menampilkan info detail file/folder (ukuran, tanggal, izin)

**Mulut & Kaki (Terminal Execution):**
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

**5. (Opsional, disarankan) Pasang alias `ruka`:**

Supaya bisa memanggil Ruka AI dari folder mana pun, pasang alias `ruka` ke `~/.bashrc`:

```bash
bash install.sh
source ~/.bashrc
```

Setelah itu cukup `cd` ke folder yang ingin dikerjakan lalu ketik `ruka` — folder
tempat kamu berada otomatis menjadi **workspace**. Jika alias `ruka` sudah ada,
installer akan memberi tahu bahwa Ruka AI sudah terinstall (tidak menambah duplikat).

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

### Mengubah Konfigurasi API

```bash
python main.py change
# atau gunakan alias pendek:
python main.py chg
```

Command ini membuka interface interaktif untuk mengubah:
- **Endpoint API** - URL endpoint model AI
- **Model AI** - Nama model yang digunakan  
- **API Key** - Kunci autentikasi API

Untuk **hanya mengganti model** (tanpa mengubah endpoint/key), gunakan:

```bash
python main.py model
# atau alias pendek:
python main.py mdl
```

Konfigurasi tersimpan di `config.json` dan otomatis ditambahkan ke `.gitignore` untuk keamanan. Untuk detail lebih lanjut, lihat [CHANGE_CONFIG_GUIDE.md](CHANGE_CONFIG_GUIDE.md).

### Melihat Daftar Session

```bash
python main.py listSessions
```

Atau saat dalam sesi chat, ketik:

```
❯ /sessions
```

### Mulai Session Baru

```
❯ /new
```

Session saat ini akan otomatis tersimpan, lalu session baru dimulai.

### Melihat Riwayat Chat

```
❯ /history
```

### Bantuan & Bersihkan Layar

```
❯ /help      # tampilkan menu bantuan
❯ /clear     # bersihkan layar
```

### Menghapus Session

```bash
# Dari CLI:
python main.py deleteSession kerja-proyek

# Dari dalam chat:
❯ /delete kerja-proyek
```

### Rename Session

```bash
# Dari CLI:
python main.py renameSession nama-lama nama-baru

# Dari dalam chat:
❯ /rename nama-baru
```

### Ganti Model dalam Sesi (Tanpa Restart)

Slash command `/model` memungkinkan mengganti model AI aktif langsung di dalam sesi berjalan, tanpa perlu keluar dan restart.

**Ganti model langsung:**

```
❯ /model meng/deepseek-v4-flash
```

**Set alias untuk model (agar tidak perlu mengetik nama panjang):**

```
❯ /model set flash|meng/deepseek-v4-flash
```

Setelah alias diset, cukup gunakan alias untuk ganti model:

```
❯ /model flash
```

**Lihat daftar alias tersimpan:**

```
❯ /model alias
```

**Hapus alias:**

```
❯ /model rm flash
# atau: /model del flash / /model remove flash
```

Alias disimpan persisten di `config.json` (key `model_aliases`), jadi tetap tersedia walau aplikasi di-restart.

### Tips Awal Session

Saat memulai session baru, ucapkan **"Hai"** terlebih dahulu ke Ruka AI. Hal ini membantu model AI memahami system prompt dengan lebih baik sebelum melanjutkan ke percakapan utama.

```
❯ Hai
⏺ Hai! Ada yang bisa saya bantu? 🐢

❯ Tampilkan daftar file dan folder
```

Dengan memulai percakapan menggunakan sapaan, AI akan lebih responsif dan memahami konteks session yang sedang berjalan.

### Contoh Percakapan

```
❯ Tampilkan daftar file dan folder
❯ Baca isi file catatan.txt
❯ Buat file todo.txt berisi daftar belanja
❯ Hapus file lama.txt
❯ Salin data.txt ke backup/data.txt
❯ Buat folder baru bernama 'projects'
❯ Jalankan perintah 'ls -la' di terminal
❯ Cek penggunaan disk dengan 'df -h'
❯ Tampilkan struktur direktori saat ini
❯ /history
❯ /sessions
❯ /new
❯ exit
```

### Workspace = Folder Tempat Kamu Memanggil

Secara default, **workspace = folder tempat kamu menjalankan perintah** (current
working directory). Jadi cukup `cd` ke folder yang ingin dikerjakan lalu jalankan:

```bash
cd ~/proyek-ku
ruka                 # (atau: python /path/instalasi/main.py)
```

Semua operasi file/folder AI akan dilakukan di folder itu.

Kamu juga masih bisa **meng-override** workspace lewat argumen path:

```bash
# Override workspace ke path tertentu
python main.py /home/user/project

# Override workspace + nama session
python main.py /home/user/project kerja-proyek

# Path relatif juga bisa
python main.py ./my-project sesi-baru
```

Catatan penting:
- Semua operasi file (baca, tulis, hapus, dll) dilakukan di **workspace** (cwd atau path override)
- File internal — folder `sessions/`, `SKILL/`, dan `.env` — **selalu** dibaca dari **folder instalasi** (tempat `main.py` berada), bukan dari workspace. Jadi API key & panduan AI tetap terbaca meskipun kamu memanggil `ruka` dari folder mana pun.

### Mode Single Prompt

```bash
python main.py "Tampilkan semua file di direktori ini"
python main.py "Buat file hello.txt berisi 'Halo Dunia'"
python main.py "Jalankan perintah ping google.com -c 3"
```

### Interupsi Proses

Saat AI sedang memproses (multi-step), ketik `q` untuk menghentikan. Spinner animasi menampilkan status berjalan beserta timer:

```
✷  Menelaah… (3s · q untuk interupsi)
q
■  Interupsi diminta — menyelesaikan round saat ini lalu berhenti…
```

---

## 💾 Session Management

Ruka AI menyimpan semua riwayat percakapan secara otomatis di folder `sessions/` dalam format JSON. Setiap session berisi:

- **Nama session** — Identifier unik untuk sesi
- **Riwayat pesan** — Seluruh percakapan (system, user, assistant, tool)
- **Metadata** — Tanggal dibuat, tanggal diupdate, jumlah pesan

### Perintah Session dalam Chat (Slash Command)

- `/help` — Tampilkan menu bantuan
- `/sessions` — Tampilkan daftar semua session tersimpan
- `/new` — Mulai session baru (session lama auto-save)
- `/history` — Tampilkan riwayat chat sesi saat ini
- `/clear` — Bersihkan layar
- `/delete <nama>` — Hapus session tertentu
- `/rename <nama baru>` — Rename session aktif
- `/model <namaModel>` — Ganti model AI aktif tanpa restart
- `/model set <alias>|<model>` — Set alias singkat untuk model
- `/model alias` — Daftar alias model yang tersimpan
- `/model rm <alias>` — Hapus alias model
- `/team <tugas>` — Bentuk tim & diskusi kolaboratif multi-agent

> Slash command tetap menggunakan format kebab-case dengan prefix `/`.

### Perintah Session dari CLI

- `python main.py <nama>` — Load atau buat session dengan nama tertentu (workspace = cwd)
- `python main.py <workspace_path>` — Override workspace ke path tertentu
- `python main.py <workspace_path> <nama>` — Override workspace + session tertentu
- `python main.py listSessions` — Lihat daftar semua session
- `python main.py deleteSession <nama>` — Hapus session tertentu dari CLI
- `python main.py renameSession <lama> <baru>` — Rename session dari CLI
- `python main.py clearSessions` — Hapus semua session tanpa nama (auto-generated) dari CLI
- `python main.py searchSessions <keyword>` — Cari session berdasarkan keyword dari CLI
- `python main.py change` — Ubah konfigurasi API endpoint, model, dan API key
- `python main.py help` — Tampilkan menu help lengkap

> **Catatan:** CLI command menggunakan **camelCase** (tanpa tanda `-`), sedangkan slash command di dalam chat tetap menggunakan kebab-case dengan prefix `/`.

### Menu Help

```bash
python main.py help
```

Atau menggunakan alias:

```bash
python main.py --help
python main.py -h
```

Command ini akan menampilkan menu help yang rapi dan terbagi dalam beberapa bagian: **Penggunaan**, **Slash command**, **CLI command**, dan **Tips**. Di dalam sesi chat, kamu juga bisa mengetik `/help` untuk memunculkan menu yang sama.

### Mencari Session

```bash
python main.py searchSessions proyek
```

Command ini akan mencari semua session yang namanya mengandung keyword `proyek` (case-insensitive). Berguna ketika punya banyak session dan ingin cepat menemukan session tertentu.

Output contoh:

```
  ✻ Pencarian 'proyek' — 2/8 session
  ────────────────────────────────────────────────────────────────
   1 ⏺ kerja-proyek
       45 pesan · diupdate 2025-07-03 09:15 · 120.3 KB
   2 ⏺ proyek-akhir
       23 pesan · diupdate 2025-07-05 18:22 · 58.7 KB
```

### Mengubah Konfigurasi API dari CLI

```bash
python main.py change
```

Untuk mengubah endpoint model AI, API key, atau konfigurasi lainnya dengan mudah melalui interface interaktif. File konfigurasi otomatis ditambahkan ke `.gitignore`. Lihat [CHANGE_CONFIG_GUIDE.md](CHANGE_CONFIG_GUIDE.md) untuk panduan lengkap.

### Menghapus Session Tanpa Nama

```bash
python main.py clearSessions
```

Command ini akan menghapus semua session yang **tidak memiliki nama** (auto-generated), yaitu session dengan pola nama `session_YYYYMMDD_HHMMSS`. Session dengan nama custom yang kamu buat sendiri **tidak akan dihapus**.

Output contoh:

```
  ⏺ 3 session auto-generated dihapus
    ⎿  session_20250701_143022
    ⎿  session_20250702_091530
    ⎿  session_20250703_164510

  ⏺ 2 session custom dipertahankan
    ⎿  kerja-proyek
    ⎿  catatan-harian
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
├── config.py         # Konfigurasi (API key, model, BASE_DIR, SCRIPT_DIR)
├── dynamic_config.py # Gabungan konfigurasi config.json (prioritas) + config.py
├── config.json       # Konfigurasi API endpoint & model + alias (disimpan lokal, tidak di-push)
├── CHANGE_CONFIG_GUIDE.md  # Panduan penggunaan command 'ruka change'
├── install.sh        # Installer alias `ruka` ke ~/.bashrc
├── requirements.txt  # Dependensi Python yang dibutuhkan
├── .env.example      # Template konfigurasi API key
├── .env              # Konfigurasi API key (tidak di-push ke git)
├── .gitignore        # Daftar file/folder yang diabaikan git
├── LICENSE           # Lisensi MIT
├── SKILL/            # Folder panduan AI (skills, tidak di-push ke git)
│   ├── skills.md     # Panduan utama capabilities & constraints
│   ├── pptSkill.md   # Panduan pembuatan PPT
│   ├── browsingSkill.md  # Panduan browsing & web scraping
│   ├── vercelSkill.md    # Panduan deploy Vercel
│   └── emailSkill.md     # Panduan email via msmtp
├── sessions/         # Folder penyimpanan session (tidak di-push ke git)
│   ├── session_20250701_143022.json
│   ├── kerja-proyek.json
│   └── ...
└── README.md         # Dokumentasi project ini
```

---

## ⚙️ Konfigurasi

Konfigurasi dapat diatur di `config.py` (hardcode) atau `config.json` (dinamis, prioritas lebih tinggi):

- `MODEL` — Default: `meng/deepseek-v4-flash` — Model AI yang digunakan via OpenRouter (bisa di-override via env `RUKA_MODEL`)
- `DEFAULT_CMD_TIMEOUT` — Default: `60` — Timeout default untuk eksekusi perintah (detik)
- `MAX_RETRIES` — Default: `7` — Jumlah maksimum retry jika request gagal
- `RETRY_BASE_DELAY` — Default: `2` — Delay dasar untuk exponential backoff (detik)
- `BASE_DIR` — Default: `os.getcwd()` (folder tempat user memanggil) — Workspace tempat file dikelola (bisa di-override via CLI)
- `SCRIPT_DIR` — Path absolut ke folder main.py — dipakai untuk akses SKILL/, .env, dan file internal (tidak pernah berubah)
- `SESSIONS_DIR` — Default: `<SCRIPT_DIR>/sessions/` — Folder penyimpanan session (selalu di folder instalasi, bukan workspace)

### Model Aktif vs config.json

`config.json` memiliki prioritas tertinggi untuk `api_endpoint`, `model`, dan `api_key`. File ini juga menyimpan **alias model** di key `model_aliases` (hasil dari `/model set`). Saat runtime, `dynamic_config.py` menggabungkan `config.json` (prioritas) dengan fallback ke `config.py`.

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
