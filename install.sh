#!/usr/bin/env bash
#
# install.sh — Pasang alias `ruka` ke shell config (Linux/macOS/Windows)
#
# Setelah dipasang, kamu cukup `cd` ke folder mana pun lalu ketik `ruka`.
# Ruka AI akan menjadikan folder tempat kamu berada (cwd) sebagai workspace,
# sementara file internal (SKILL/, sessions/, .env) tetap dibaca dari folder
# instalasi ini.
#
# Jalankan:  bash install.sh   (atau ./install.sh setelah chmod +x)
#
# Dukungan platform:
#   - Linux/macOS   → alias di ~/.bashrc
#   - Windows (WSL) → alias di ~/.bashrc
#   - Windows (Git Bash / MSYS2) → alias di ~/.bashrc
#   - Windows (PowerShell) → fungsi di $PROFILE
#   - Windows (CMD) → batch script ruka.cmd di folder instalasi

set -euo pipefail

# ── Warna (selaras palet Ruka: coral/abu) ────────────────────
if [ -t 1 ]; then
    ACCENT=$'\033[38;5;209m'; OK=$'\033[38;5;114m'; WARN=$'\033[38;5;215m'
    ERR=$'\033[38;5;203m'; GREY=$'\033[38;5;245m'; BOLD=$'\033[1m'; R=$'\033[0m'
else
    ACCENT=""; OK=""; WARN=""; ERR=""; GREY=""; BOLD=""; R=""
fi

info()  { printf '%s\n' "  ${GREY}$*${R}"; }
ok()    { printf '%s\n' "  ${OK}✓${R} $*"; }
warn()  { printf '%s\n' "  ${WARN}!${R} $*"; }
fail()  { printf '%s\n' "  ${ERR}✗${R} $*" >&2; exit 1; }

printf '\n  %s🐢 Ruka AI — installer%s\n\n' "${ACCENT}${BOLD}" "$R"

# ── Folder instalasi = folder tempat install.sh ini berada ───
# Absolut, apa pun cwd pemanggil.
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_PY="$INSTALL_DIR/main.py"

# ── Validasi main.py ada di folder instalasi ─────────────────
[ -f "$MAIN_PY" ] || fail "main.py tidak ditemukan di ${INSTALL_DIR}"

# ── Deteksi OS ───────────────────────────────────────────────
detect_os() {
    case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
        linux*)   echo "linux" ;;
        darwin*)  echo "macos" ;;
        cygwin*|msys*|mingw*) echo "windows-gitbash" ;;
        *)        echo "unknown" ;;
    esac
}

OS="$(detect_os)"

# ── Deteksi apakah berjalan di WSL ───────────────────────────
is_wsl() {
    [ -f /proc/sys/fs/binfmt_misc/WSLInterop ] 2>/dev/null && return 0
    grep -qi microsoft /proc/version 2>/dev/null && return 0
    return 1
}

# ── Deteksi apakah berjalan di PowerShell (via pwsh/bash) ────
# Ini hanya relevan jika script dipanggil dari dalam PowerShell.
# Kita tetap prioritaskan bash alias, tapi beri info tambahan.

# ── Tentukan interpreter Python ──────────────────────────────
# Di Linux/macOS biasanya 'python3', di Windows (Git Bash / MSYS2) 'python'.
detect_python() {
    local os="$1"
    if [ "$os" = "windows-gitbash" ]; then
        # Windows: prioritas python (python3 jarang ada)
        if command -v python >/dev/null 2>&1; then
            echo "python"
        elif command -v python3 >/dev/null 2>&1; then
            echo "python3"
        else
            return 1
        fi
    else
        # Linux/macOS: prioritas python3
        if command -v python3 >/dev/null 2>&1; then
            echo "python3"
        elif command -v python >/dev/null 2>&1; then
            echo "python"
        else
            return 1
        fi
    fi
}

PYTHON_BIN="$(detect_python "$OS")" || fail "Python tidak ditemukan. Install python3 dulu."

# ── Install dependensi Python dari requirements.txt ──────────
# Cek pip dulu, bootstrap bila perlu, lalu install requirements.
# Menangani PEP 668 (externally-managed-environment) & error izin.
install_requirements() {
    local REQ_FILE="$INSTALL_DIR/requirements.txt"

    printf '\n'
    info "${BOLD}Memeriksa dependensi Python...${R}"

    # ── requirements.txt ada? ────────────────────────────────────
    if [ ! -f "$REQ_FILE" ]; then
        warn "requirements.txt tidak ditemukan di folder instalasi. Melewati."
        return 0
    fi

    # ── Pastikan pip tersedia ────────────────────────────────────
    if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
        warn "pip tidak ditemukan untuk '${PYTHON_BIN}'."
        info "Mencoba bootstrap pip via ensurepip..."

        if "$PYTHON_BIN" -m ensurepip --upgrade >/dev/null 2>&1 \
           || "$PYTHON_BIN" -m ensurepip >/dev/null 2>&1; then
            ok "pip berhasil di-bootstrap."
        else
            # Gagal bootstrap — beri petunjuk spesifik per OS
            case "$OS" in
                linux)
                    info "Debian/Ubuntu: ${BOLD}sudo apt install python3-pip${R}"
                    info "Fedora:        ${BOLD}sudo dnf install python3-pip${R}"
                    info "Arch:          ${BOLD}sudo pacman -S python-pip${R}"
                    fail "pip tidak tersedia. Install pip untuk Python Anda dulu."
                    ;;
                macos)
                    info "Coba: ${BOLD}brew install python${R} (atau 'python3 -m ensurepip')"
                    fail "pip tidak tersedia. Install pip untuk Python Anda dulu."
                    ;;
                windows-gitbash)
                    info "Install Python dari python.org dan centang opsi 'pip'."
                    fail "pip tidak tersedia. Install pip untuk Python Anda dulu."
                    ;;
                *)
                    fail "pip tidak tersedia. Install pip untuk Python Anda dulu."
                    ;;
            esac
        fi
    fi

    local PIP_VER
    PIP_VER="$("$PYTHON_BIN" -m pip --version 2>/dev/null | head -1)"
    ok "pip tersedia: ${GREY}${PIP_VER}${R}"

    # ── Install requirements ─────────────────────────────────────
    info "Menginstall dependensi dari requirements.txt..."

    local PIP_LOG
    PIP_LOG="$(mktemp 2>/dev/null || echo /tmp/ruka_pip_install.log)"

    # Percobaan 1: install biasa
    if "$PYTHON_BIN" -m pip install -r "$REQ_FILE" >"$PIP_LOG" 2>&1; then
        ok "${BOLD}Dependensi berhasil diinstall.${R}"
        rm -f "$PIP_LOG"
        return 0
    fi

    # Percobaan 2: PEP 668 (externally-managed-environment) → --break-system-packages
    if grep -qi "externally-managed" "$PIP_LOG" 2>/dev/null; then
        warn "Lingkungan Python dikelola sistem (PEP 668)."
        info "Mencoba ulang dengan ${BOLD}--break-system-packages${R}..."
        if "$PYTHON_BIN" -m pip install -r "$REQ_FILE" --break-system-packages >>"$PIP_LOG" 2>&1; then
            ok "${BOLD}Dependensi berhasil diinstall (--break-system-packages).${R}"
            rm -f "$PIP_LOG"
            return 0
        fi
    fi

    # Percobaan 3: error izin → --user
    if grep -qiE "permission denied|access is denied|not writable" "$PIP_LOG" 2>/dev/null; then
        warn "Gagal karena izin akses."
        info "Mencoba ulang dengan ${BOLD}--user${R}..."
        if "$PYTHON_BIN" -m pip install -r "$REQ_FILE" --user >>"$PIP_LOG" 2>&1; then
            ok "${BOLD}Dependensi berhasil diinstall (--user).${R}"
            rm -f "$PIP_LOG"
            return 0
        fi
    fi

    # Semua percobaan gagal — tampilkan ringkas + saran manual
    warn "${BOLD}Gagal menginstall dependensi otomatis.${R}"
    info "Jalankan manual:"
    printf '      %s%s -m pip install -r "%s"%s\n' "$ACCENT" "$PYTHON_BIN" "$REQ_FILE" "$R"
    # Tampilkan 3 baris terakhir log untuk petunjuk
    if [ -f "$PIP_LOG" ]; then
        local tail_out
        tail_out="$(tail -3 "$PIP_LOG" 2>/dev/null)"
        if [ -n "$tail_out" ]; then
            info "Pesan terakhir pip:"
            printf '      %s%s%s\n' "$GREY" "$tail_out" "$R"
        fi
    fi
    rm -f "$PIP_LOG"
    return 0
}

# ── Konversi path ke format Windows jika perlu ───────────────
# Untuk Git Bash / MSYS2, kita bisa gunakan path Unix langsung.
# Untuk CMD/PowerShell native, kita perlu path Windows.
to_win_path() {
    local unix_path="$1"
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$unix_path"
    elif command -v wslpath >/dev/null 2>&1; then
        wslpath -w "$unix_path"
    else
        # Fallback manual: /mnt/c/... → C:\...
        echo "$unix_path" | sed -E 's|^/mnt/([a-zA-Z])/|\1:/|; s|/|\\|g'
    fi
}

WIN_INSTALL_DIR="$(to_win_path "$INSTALL_DIR")"
WIN_MAIN_PY="$(to_win_path "$MAIN_PY")"

# ═══════════════════════════════════════════════════════════════
# 1. INSTALL UNTUK BASH (Linux, macOS, WSL, Git Bash, MSYS2)
# ═══════════════════════════════════════════════════════════════

install_bash() {
    local BASHRC="$HOME/.bashrc"

    # Baris alias final. Path di-quote (double-quote di dalam single-quote) agar
    # tetap aman bila folder instalasi mengandung spasi.
    local ALIAS_LINE="alias ruka='${PYTHON_BIN} \"${MAIN_PY}\"'"

    # ── Pastikan ~/.bashrc ada ───────────────────────────────────
    [ -f "$BASHRC" ] || touch "$BASHRC"

    # ── Sudah terpasang? ─────────────────────────────────────────
    if grep -qE '^[[:space:]]*alias[[:space:]]+ruka=' "$BASHRC"; then
        warn "${BOLD}Ruka AI sudah terinstall di bash.${R}"
        info "Alias 'ruka' sudah ada di ${BASHRC}."
        info "Untuk memperbarui path, edit baris alias tersebut secara manual."
        return 0
    fi

    # ── Pasang alias ─────────────────────────────────────────────
    {
        printf '\n'
        printf '# Ruka AI — alias (ditambahkan oleh install.sh)\n'
        printf '%s\n' "$ALIAS_LINE"
    } >> "$BASHRC"

    ok "${BOLD}Ruka AI terinstall untuk Bash!${R}"
    info "Alias ditambahkan ke ${BASHRC}:"
    printf '      %s%s%s\n' "$ACCENT" "$ALIAS_LINE" "$R"
    printf '\n'
    info "Aktifkan sekarang:  ${BOLD}source ~/.bashrc${R}"
    info "Lalu dari folder mana pun:  ${BOLD}cd ~/proyek-ku && ruka${R}"
}

# ═══════════════════════════════════════════════════════════════
# 2. INSTALL UNTUK POWERSHELL (Windows PowerShell / pwsh)
# ═══════════════════════════════════════════════════════════════

install_powershell() {
    # Cek apakah PowerShell tersedia
    local PWSH=""
    if command -v pwsh.exe >/dev/null 2>&1; then
        PWSH="pwsh.exe"
    elif command -v powershell.exe >/dev/null 2>&1; then
        PWSH="powershell.exe"
    else
        info "PowerShell tidak terdeteksi. Melewati instalasi PowerShell."
        return 0
    fi

    # Dapatkan path $PROFILE dari PowerShell
    local PROFILE_PATH
    PROFILE_PATH="$("$PWSH" -NoProfile -Command 'Write-Host $PROFILE' 2>/dev/null || echo "")"

    if [ -z "$PROFILE_PATH" ]; then
        info "Tidak dapat membaca \$PROFILE PowerShell. Melewati."
        return 0
    fi

    # Konversi ke path Unix jika output Windows
    if command -v cygpath >/dev/null 2>&1; then
        PROFILE_PATH="$(cygpath -u "$PROFILE_PATH")"
    elif command -v wslpath >/dev/null 2>&1; then
        PROFILE_PATH="$(wslpath -u "$PROFILE_PATH")"
    fi

    local PROFILE_DIR="$(dirname "$PROFILE_PATH")"

    # Buat folder profile jika belum ada
    mkdir -p "$PROFILE_DIR"

    # Fungsi PowerShell yang akan ditambahkan
    # Di Windows, interpreter Python biasanya 'python' bukan 'python3'
    local PS_PYTHON="${PYTHON_BIN}"
    if [ "$OS" = "windows-gitbash" ]; then
        PS_PYTHON="python"
    fi
    local PS_FUNC="function ruka { & ${PS_PYTHON} '${WIN_MAIN_PY}' @args }"

    # Cek apakah sudah ada fungsi ruka di profile
    if [ -f "$PROFILE_PATH" ] && grep -q 'function ruka' "$PROFILE_PATH" 2>/dev/null; then
        warn "${BOLD}Ruka AI sudah terinstall di PowerShell.${R}"
        info "Fungsi 'ruka' sudah ada di ${PROFILE_PATH}."
        return 0
    fi

    # Tambahkan ke profile
    {
        printf '\n'
        printf '# Ruka AI — fungsi (ditambahkan oleh install.sh)\n'
        printf '%s\n' "$PS_FUNC"
    } >> "$PROFILE_PATH"

    ok "${BOLD}Ruka AI terinstall untuk PowerShell!${R}"
    info "Fungsi ditambahkan ke:"
    printf '      %s%s%s\n' "$GREY" "$PROFILE_PATH" "$R"
    printf '\n'
    info "Reload profile:  ${BOLD}. \$PROFILE${R}  (atau buka ulang PowerShell)"
    info "Lalu dari folder mana pun:  ${BOLD}ruka${R}"
}

# ═══════════════════════════════════════════════════════════════
# 3. INSTALL UNTUK CMD (Windows Command Prompt)
# ═══════════════════════════════════════════════════════════════

install_cmd() {
    local CMD_SCRIPT="$INSTALL_DIR/ruka.cmd"

    # Cek apakah ruka.cmd sudah ada
    if [ -f "$CMD_SCRIPT" ]; then
        warn "${BOLD}ruka.cmd sudah ada di folder instalasi.${R}"
        info "File: ${CMD_SCRIPT}"
        return 0
    fi

    # Buat batch script untuk CMD
    cat > "$CMD_SCRIPT" << 'CMDEOF'
@echo off
REM ruka.cmd — Ruka AI launcher untuk Windows Command Prompt
REM Dibuat oleh install.sh

setlocal

REM Tentukan folder instalasi (folder tempat ruka.cmd berada)
set "RUKA_DIR=%~dp0"
set "MAIN_PY=%RUKA_DIR%main.py"

REM Cari python
set "PYTHON_BIN="
where python3 >nul 2>&1 && set "PYTHON_BIN=python3"
if not defined PYTHON_BIN where python >nul 2>&1 && set "PYTHON_BIN=python"
if not defined PYTHON_BIN (
    echo [ERROR] Python tidak ditemukan. Install python3 dulu.
    exit /b 1
)

REM Jalankan Ruka AI
%PYTHON_BIN% "%MAIN_PY%" %*
endlocal
CMDEOF

    ok "${BOLD}Ruka AI terinstall untuk Command Prompt (CMD)!${R}"
    info "Batch script dibuat:"
    printf '      %s%s%s\n' "$ACCENT" "$CMD_SCRIPT" "$R"
    printf '\n'

    # Cek apakah folder instalasi sudah ada di PATH
    if ! echo "$PATH" | grep -qF "$INSTALL_DIR"; then
        warn "Folder instalasi BELUM ada di PATH."
        info "Tambahkan folder ini ke PATH agar bisa memanggil 'ruka' dari mana saja:"
        printf '\n'
        info "  ${BOLD}CMD (Admin):${R}"
        printf '      %ssetx PATH "%%PATH%%;%s"%s\n\n' "$ACCENT" "$WIN_INSTALL_DIR" "$R"
        info "  ${BOLD}Atau via GUI:${R}"
        info "  System Properties → Environment Variables → Path → New"
        printf '      %s%s%s\n\n' "$GREY" "$WIN_INSTALL_DIR" "$R"
    else
        ok "Folder instalasi sudah ada di PATH."
    fi

    info "Setelah PATH diatur, dari CMD mana pun:  ${BOLD}ruka${R}"
}

# ═══════════════════════════════════════════════════════════════
# MAIN: Jalankan installer sesuai OS
# ═══════════════════════════════════════════════════════════════

printf '\n'
info "OS terdeteksi: ${BOLD}${OS}${R}"
printf '\n'

# ── Install dependensi Python dulu (sebelum alias) ────────────
install_requirements
printf '\n'

case "$OS" in
    linux)
        install_bash
        ;;

    macos)
        install_bash
        ;;

    windows-gitbash)
        # Git Bash / MSYS2: install bash + PowerShell + CMD
        install_bash
        printf '\n'
        install_powershell
        printf '\n'
        install_cmd
        ;;

    *)
        # Unknown OS — tetap coba bash (fallback)
        warn "OS tidak dikenali. Mencoba instalasi bash sebagai fallback."
        install_bash
        ;;
esac

# ── Info tambahan jika berjalan di WSL ────────────────────────
if is_wsl; then
    printf '\n'
    info "${BOLD}WSL terdeteksi.${R}"
    info "Kamu bisa menjalankan Ruka AI dari dalam WSL dengan alias 'ruka'."
    info "Untuk menjalankan dari Windows (PowerShell/CMD), jalankan install.sh dari Git Bash."
fi

printf '\n'
ok "${BOLD}Selesai!${R} 🐢\n"