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

# Model untuk analisis GAMBAR/vision (screenshot, dll). Dipisah dari model utama
# karena model vision biasanya lebih mahal. Bisa di-override di config.json (key
# 'vision_model') atau env RUKA_VISION_MODEL.
_DEFAULT_VISION_MODEL = "deepseek-v4.1-flash"
VISION_MODEL = (os.getenv("RUKA_VISION_MODEL") or "").strip() or _DEFAULT_VISION_MODEL

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
# Dinaikkan untuk model 1M context window - dapat membaca dan menulis file lebih banyak
MAX_READ_LINES = 25_000        # ↑ dari 5,000 → naik 5x untuk file besar
MAX_READ_CHARS = 1_500_000     # ↑ dari 250,000 → naik 6x untuk content panjang

# exec_command: batas karakter stdout & stderr (masing-masing) sebelum di-return.
# Dinaikkan untuk output yang lebih panjang
MAX_EXEC_OUTPUT_CHARS = 200_000  # ↑ dari 80,000 → naik 2.5x untuk command verbose

# Jumlah byte awal yang disampel untuk mendeteksi file biner di read_file.
BINARY_SNIFF_BYTES = 16384     # ↑ dari 8192 → sample lebih besar untuk deteksi akurat

# Limit baru: truncation threshold untuk file yang terlalu panjang
# Jika file > limit ini, baca 3 bagian saja (awal + tengah + akhir) + summary
TRUNCATION_THRESHOLD = 20_000  # ↑ dari 4,000 → naik 5x untuk model 1M context

# ============================================================
# CONTEXT / COMPACTION — ringkas riwayat secara PERMANEN
# ============================================================
# Riwayat 'messages' dikirim ULANG utuh tiap round agentic. Saat menyentuh
# ambang token, riwayat di-COMPACT (diringkas LLM) — bukan dibuang mentah —
# agar konteks tetap terjaga tanpa membuat model "halu".
#
# PENTING:
#  - Compaction dijalankan HANYA setelah model SELESAI menjawab (bukan di
#    tengah giliran saat tool call). Jadi model tak pernah "dipotong" saat bicara.
#  - Hasil compaction bersifat PERMANEN: disimpan ke file session, sehingga
#    tidak diulang setiap call API.
#  - SEMUA riwayat diringkas KECUALI sejumlah GILIRAN USER terakhir yang
#    dipertahankan utuh (COMPACT_KEEP_TURNS). Satu giliran = blok dari pesan
#    'user' hingga sebelum pesan 'user' berikutnya (termasuk jawaban AI &
#    hasil tool di dalamnya). Jadi konteks terdekat tetap utuh & akurat.
#
# ⚡ OPTIMASI BIAYA FLAT PER REQUEST:
#  Bila provider memakai tarif FLAT per request (bukan per token), maka:
#   • Jumlah request = biaya → MINIMALKAN request (chunk sebesar mungkin).
#   • Token output = gratis  → minta ringkasan sepanjang mungkin (detail).
#   • Context window = aset  → manfaatkan maksimal.
#  Karena itu: chunk dibuat besar (≈1 request per compact) & output diperbesar.
MAX_HISTORY_TOKENS = 650_000     # ambang compact (65% dari window 1jt; margin utk under-estimate token)
COMPACT_KEEP_TURNS = 5           # jumlah GILIRAN USER terakhir yang dipertahankan UTUH
ENABLE_COMPACTION = True         # aktifkan compact otomatis setelah model selesai
# Chunk ≥ MAX_HISTORY → SELURUH riwayat selesai dalam SATU request (bukan belasan).
# Batas aman: (chunk × faktor_under_estimate) + output < context window (1jt).
# Estimasi token cenderung UNDER-estimate (teks Indonesia ~3 char/token), jadi
# diberi margin: 700K × ~1.3 ≈ 910K aktual + 16K output ≈ 926K (< 1jt). Aman.
COMPACT_CHUNK_TOKENS = 700_000   # ukuran chunk (≥ MAX_HISTORY → 1 request per compact = hemat, krn flat per request)
COMPACT_MAX_CHARS = 120_000      # panjang maks ringkasan gabungan (longgar — output gratis, jangan dipotong)
COMPACT_MODEL = "deepseek-v4-flash"  # model untuk compaction (ringkas riwayat); None → pakai MODEL aktif
COMPACT_TEMPERATURE = 0.3        # sedikit kreatif agar ringkasan natural & informatif
COMPACT_MAX_TOKENS = 16_000      # token maks output ringkasan per chunk (gratis → minta detail maksimal)
COMPACT_MSG_MAX_CHARS = 12_000   # batas karakter per-pesan saat menyusun payload ringkasan (naik dari 4K agar detail utuh)

# Token estimation — estimasi token dari teks (char/4 untuk ASCII, lebih akurat
# untuk campuran). Bisa disetel per-karakter untuk model tertentu.
ESTIMATE_CHARS_PER_TOKEN = 3     # ↑ dari 4 → lebih aggressive untuk 1M context window

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
