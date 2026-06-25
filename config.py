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
MODEL = "openrouter/owl-alpha"

# URL endpoint API
API_URL = "https://openrouter.ai/api/v1/chat/completions"

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
MAX_RETRIES = 5

# Delay dasar untuk exponential backoff (detik)
# Retry delays: 5s, 10s, 20s, 40s, 80s
RETRY_BASE_DELAY = 5

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
