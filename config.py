"""
Ruka AI — Configuration File
Semua konfigurasi agent ada di sini.
Edit file ini untuk mengubah behavior agent tanpa menyentuh main.py.
"""

import os

# ============================================================
# API CONFIGURATION
# ============================================================

# API Key — prioritaskan .env, fallback ke string kosong (harus di-set via .env)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Model AI yang digunakan (format: provider/model-name)
# Contoh: "openrouter/owl-alpha", "openrouter/qwen/qwen3-8b", dll.
# Bisa di-override via environment variable RUKA_MODEL (atau lewat .env, karena
# load_dotenv jalan sebelum import config di main.py). Nilai kosong/whitespace
# → fallback ke default agar payload API tidak rusak.
_DEFAULT_MODEL = "meng/deepseek-v4-flash"
MODEL = (os.getenv("RUKA_MODEL") or "").strip() or _DEFAULT_MODEL

# URL endpoint API
API_URL = "https://ai.meongtopup.my.id/v1/chat/completions"

# HTTP Headers untuk request API
HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://myapp.com",
    "X-Title": "Ruka AI - Kura-Kura Agent",
}

# ============================================================
# DIRECTORY CONFIGURATION
# ============================================================

# Direktori kerja (workspace) = folder TEMPAT USER MEMANGGIL `python main.py`
# (current working directory), BUKAN folder tempat main.py berada.
# Dengan begitu alias `ruka` beroperasi pada folder tempat user sedang berada
# saat menjalankan perintah (mis. `cd ~/proyek && ruka`).
# Masih bisa di-override eksplisit dari CLI: python main.py <workspace_path> [session_name]
# JANGAN ubah ini kecuali tahu apa yang dilakukan
BASE_DIR = os.getcwd()

# Path ke folder tempat main.py berada — dipakai untuk akses SKILL/, sessions/,
# .env, dan file internal lain. Ini TIDAK PERNAH berubah meskipun workspace
# (BASE_DIR) user berbeda dari folder instalasi.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Folder untuk menyimpan sesi chat — SELALU di SCRIPT_DIR, bukan BASE_DIR
# Session harus tetap di folder main.py meskipun workspace user berbeda
SESSIONS_DIR = os.path.join(SCRIPT_DIR, "sessions")

# ============================================================
# TIMEOUT & RETRY CONFIGURATION
# ============================================================

# Timeout default untuk eksekusi perintah terminal (detik)
DEFAULT_CMD_TIMEOUT = 60

# Jumlah maksimum retry saat request API gagal
MAX_RETRIES = 7

# Delay dasar untuk exponential backoff (detik)
# Retry delays: 5s, 10s, 20s, 40s, 80s
RETRY_BASE_DELAY = 2

# ============================================================
# OUTPUT LIMITS — batasi volume output tool ke message history
# ============================================================
# Output tool masuk ke riwayat percakapan & dikirim ULANG tiap round agentic,
# sehingga output besar (cat file besar, find /) cepat meledakkan token & bisa
# memicu "context length exceeded" — terutama untuk model konteks-kecil.
# Nilai di sini tunable tanpa menyentuh main.py.

# read_file: batas baris & karakter untuk pembacaan penuh (tanpa offset/limit).
# Dikurangi dari 20K/1M jadi 5K/250K untuk hemat context (default cukup untuk sebagian besar kasus)
MAX_READ_LINES = 5_000         # ↓ dari 20,000 → hemat ~75% chars
MAX_READ_CHARS = 250_000       # ↓ dari 1,000,000 → hemat 75% chars

# exec_command: batas karakter stdout & stderr (masing-masing) sebelum di-return.
# Dikurangi dari 200K jadi 80K untuk command yang biasanya menghasilkan output pendek-sedang
MAX_EXEC_OUTPUT_CHARS = 80_000  # ↓ dari 200,000 → hemat 60% chars

# Jumlah byte awal yang disampel untuk mendeteksi file biner di read_file.
BINARY_SNIFF_BYTES = 8192

# Limit baru: truncation threshold untuk file yang terlalu panjang
# Jika file > limit ini, baca 3 bagian saja (awal + tengah + akhir) + summary
TRUNCATION_THRESHOLD = 4_000    # garis/file untuk trigger mode ringkas

# ============================================================
# HISTORY / CONTEXT WINDOW — hard-trim riwayat sebelum kirim API
# ============================================================
# Riwayat 'messages' dikirim ULANG utuh tiap round agentic. Tanpa batas →
# "context length exceeded" pada model konteks-kecil. Trim DETERMINISTIK
# (bukan ringkasan-LLM yang rapuh): buang segmen tertua, jaga system + terbaru.
# Catatan ambang: estimasi token memakai char/4 (cenderung UNDER-estimate teks
# non-ASCII/Indonesia) dan TIDAK menghitung schema TOOLS + system + completion
# yang juga memakan window → dibuat KONSERVATIF dengan margin. Tunable.
MAX_HISTORY_TOKENS = 400_000     # ambang estimasi token (char/4) riwayat yang DIKIRIM (↓ dari 800K — lebih konservatif untuk hemat token)
KEEP_RECENT_MESSAGES = 500_000   # lantai keras: minimal pesan terbaru dipertahankan (↓ dari 1M — batasi riwayat agar tidak boros)
HISTORY_TRIM_NOTICE = True       # tampilkan notice 1 baris (sekali per giliran) saat trim

# ============================================================
# SUMMARIZATION — ringkas riwayat lama secara cerdas (LLM)
# ============================================================
# Saat riwayat mendekati batas MAX_HISTORY_TOKENS, segmen PALING TUA
# diringkas jadi 1-2 pesan ringkas (bukan dibuang mentah) supaya konteks
# tetap terjaga TANPA mengirim teks penuh. Ini komplementer dengan
# _trim_history() yang deterministik — summarization dipakai untuk
# "memadatkan" segmen lama yang masih relevan.
ENABLE_SUMMARIZATION = True      # aktifkan ringkasan LLM untuk riwayat lama
SUMMARIZE_TRIGGER_RATIO = 0.7    # mulai ringkas saat riwayat ≥70% dari MAX_HISTORY_TOKENS
SUMMARIZE_CHUNK_SIZE = 80        # pesan per chunk yang diringkas dalam satu call LLM
SUMMARIZE_MAX_CHARS = 6_000      # panjang maks ringkasan per chunk (agar hemat token)
SUMMARIZE_MODEL = None           # None → pakai MODEL aktif; bisa di-set model murah khusus ringkasan
SUMMARIZE_TEMPERATURE = 0.2      # deterministik untuk ringkasan
SUMMARIZE_MAX_TOKENS = 2_000     # token maks output ringkasan per call

# Token estimation — estimasi token dari teks (char/4 untuk ASCII, lebih akurat
# untuk campuran). Bisa disetel per-karakter untuk model tertentu.
ESTIMATE_CHARS_PER_TOKEN = 4     # rasio char→token untuk estimasi (konservatif: 4 char = 1 token)

# ============================================================
# SECURITY — BLOCKED COMMANDS
# ============================================================
# Perintah yang TIDAK BOLEH dijalankan oleh agent.
# JANGAN hapus atau modifikasi kecuali tahu risikonya.

BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs.",
    "dd if=/dev/zero",
    "shutdown -h now",
    "shutdown -r now",
    "poweroff",
    "reboot",
    ":(){:|:&};:",
    "del /s /q \\",
    "rd /s /q \\",
    "format c:",
]
