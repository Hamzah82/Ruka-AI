#!/usr/bin/env bash
#
# uninstall.sh — Hapus semua jejak instalasi Ruka AI
#
# Membalikkan semua yang dilakukan oleh install.sh:
#   - Hapus alias 'ruka' dari ~/.bashrc
#   - Hapus fungsi 'ruka' dari PowerShell $PROFILE
#   - Hapus file ruka.cmd (batch script untuk CMD)
#
# Jalankan:  bash uninstall.sh   (atau ./uninstall.sh setelah chmod +x)

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

printf '\n  %s🐢 Ruka AI — uninstaller%s\n\n' "${ACCENT}${BOLD}" "$R"

# ── Folder instalasi = folder tempat uninstall.sh ini berada ──
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAIN_PY="$INSTALL_DIR/main.py"

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

# ── Deteksi WSL ──────────────────────────────────────────────
is_wsl() {
    [ -f /proc/sys/fs/binfmt_misc/WSLInterop ] 2>/dev/null && return 0
    grep -qi microsoft /proc/version 2>/dev/null && return 0
    return 1
}

# ── Konversi path ke format Windows jika perlu ───────────────
to_win_path() {
    local unix_path="$1"
    if command -v cygpath >/dev/null 2>&1; then
        cygpath -w "$unix_path"
    elif command -v wslpath >/dev/null 2>&1; then
        wslpath -w "$unix_path"
    else
        echo "$unix_path" | sed -E 's|^/mnt/([a-zA-Z])/|\1:/|; s|/|\\|g'
    fi
}

WIN_INSTALL_DIR="$(to_win_path "$INSTALL_DIR")"

# ═══════════════════════════════════════════════════════════════
# 1. HAPUS DARI BASH (Linux, macOS, WSL, Git Bash, MSYS2)
# ═══════════════════════════════════════════════════════════════

uninstall_bash() {
    local BASHRC="$HOME/.bashrc"
    local REMOVED_COUNT=0

    if [ ! -f "$BASHRC" ]; then
        warn "~/.bashrc tidak ditemukan. Tidak ada yang dihapus dari Bash."
        return 0
    fi

    # Buat backup dulu
    local BACKUP="${BASHRC}.bak.$(date +%Y%m%d%H%M%S)"
    cp "$BASHRC" "$BACKUP"

    # Hapus baris alias ruka dan komentar di atasnya
    # Pola: menghapus blok yang terdiri dari:
    #   - Baris komentar "# Ruka AI — alias ..."
    #   - Baris alias "alias ruka=..."
    # Juga hapus baris alias standalone (tanpa komentar sebelumnya)
    # serta baris kosong di antara mereka (opsional)

    local TMPFILE
    TMPFILE="$(mktemp)"

    # Strategi: hapus baris yang mengandung 'alias ruka=' dan
    # baris komentar "# Ruka AI" yang mendahuluinya.
    # Kita lakukan dengan awk: hapus baris komentar Ruka AI,
    # lalu hapus baris alias ruka, lalu hapus baris kosong
    # yang tersisa di antara.
    awk '
    BEGIN { skip = 0 }
    /^[[:space:]]*#[[:space:]]*Ruka AI/ { skip = 1; next }
    /^[[:space:]]*alias[[:space:]]+ruka[=]/ { skip = 0; next }
    /^[[:space:]]*alias[[:space:]]+ruka / { skip = 0; next }
    # Jika baris kosong dan sebelumnya skip, lewati juga
    /^[[:space:]]*$/ && skip { next }
    { skip = 0; print }
    ' "$BASHRC" > "$TMPFILE"

    # Cek apakah ada perubahan
    if cmp -s "$BASHRC" "$TMPFILE"; then
        rm -f "$TMPFILE" "$BACKUP"
        warn "Alias 'ruka' tidak ditemukan di ~/.bashrc. Tidak ada yang dihapus."
        return 0
    fi

    mv "$TMPFILE" "$BASHRC"
    rm -f "$BACKUP"  # backup hanya jika berhasil hapus

    ok "${BOLD}Ruka AI berhasil dihapus dari Bash!${R}"
    info "Alias 'ruka' telah dihapus dari ${BASHRC}."
    info "Aktifkan perubahan:  ${BOLD}source ~/.bashrc${R}"
}

# ═══════════════════════════════════════════════════════════════
# 2. HAPUS DARI POWERSHELL (Windows PowerShell / pwsh)
# ═══════════════════════════════════════════════════════════════

uninstall_powershell() {
    local PWSH=""
    if command -v pwsh.exe >/dev/null 2>&1; then
        PWSH="pwsh.exe"
    elif command -v powershell.exe >/dev/null 2>&1; then
        PWSH="powershell.exe"
    else
        info "PowerShell tidak terdeteksi. Melewati."
        return 0
    fi

    local PROFILE_PATH
    PROFILE_PATH="$("$PWSH" -NoProfile -Command 'Write-Host $PROFILE' 2>/dev/null || echo "")"

    if [ -z "$PROFILE_PATH" ]; then
        info "Tidak dapat membaca \$PROFILE PowerShell. Melewati."
        return 0
    fi

    # Konversi ke path Unix
    if command -v cygpath >/dev/null 2>&1; then
        PROFILE_PATH="$(cygpath -u "$PROFILE_PATH")"
    elif command -v wslpath >/dev/null 2>&1; then
        PROFILE_PATH="$(wslpath -u "$PROFILE_PATH")"
    fi

    if [ ! -f "$PROFILE_PATH" ]; then
        warn "PowerShell profile tidak ditemukan di ${PROFILE_PATH}. Melewati."
        return 0
    fi

    # Backup
    local BACKUP="${PROFILE_PATH}.bak.$(date +%Y%m%d%H%M%S)"
    cp "$PROFILE_PATH" "$BACKUP"

    local TMPFILE
    TMPFILE="$(mktemp)"

    # Hapus blok function ruka dan komentar Ruka AI
    awk '
    BEGIN { skip = 0 }
    /^[[:space:]]*#[[:space:]]*Ruka AI/ { skip = 1; next }
    /^[[:space:]]*function[[:space:]]+ruka/ { skip = 0; next }
    /^[[:space:]]*$/ && skip { next }
    { skip = 0; print }
    ' "$PROFILE_PATH" > "$TMPFILE"

    if cmp -s "$PROFILE_PATH" "$TMPFILE"; then
        rm -f "$TMPFILE" "$BACKUP"
        warn "Fungsi 'ruka' tidak ditemukan di PowerShell profile. Melewati."
        return 0
    fi

    mv "$TMPFILE" "$PROFILE_PATH"
    rm -f "$BACKUP"

    ok "${BOLD}Ruka AI berhasil dihapus dari PowerShell!${R}"
    info "Fungsi 'ruka' telah dihapus dari:"
    printf '      %s%s%s\n' "$GREY" "$PROFILE_PATH" "$R"
    info "Reload profile:  ${BOLD}. \$PROFILE${R}  (atau buka ulang PowerShell)"
}

# ═══════════════════════════════════════════════════════════════
# 3. HAPUS ruka.cmd (Windows Command Prompt)
# ═══════════════════════════════════════════════════════════════

uninstall_cmd() {
    local CMD_SCRIPT="$INSTALL_DIR/ruka.cmd"

    if [ ! -f "$CMD_SCRIPT" ]; then
        info "ruka.cmd tidak ditemukan di folder instalasi. Melewati."
        return 0
    fi

    # Verifikasi bahwa file ini benar-benar milik Ruka AI
    # (cek apakah berisi string "Ruka AI" atau "main.py")
    if grep -qi "Ruka AI\|main.py" "$CMD_SCRIPT" 2>/dev/null; then
        rm -f "$CMD_SCRIPT"
        ok "${BOLD}ruka.cmd berhasil dihapus!${R}"
        info "File batch script dihapus:"
        printf '      %s%s%s\n' "$ACCENT" "$CMD_SCRIPT" "$R"
    else
        warn "ruka.cmd ditemukan tapi tidak dikenali sebagai milik Ruka AI."
        info "Hapus manual jika perlu: ${CMD_SCRIPT}"
    fi

    # Info PATH — tidak bisa otomatis hapus dari PATH user,
    # tapi kita beri petunjuk
    warn "Folder instalasi mungkin masih ada di PATH environment."
    info "Untuk menghapus dari PATH:"
    printf '\n'
    info "  ${BOLD}CMD (Admin):${R}"
    printf '      %s<Hapus manual "%s" dari PATH>%s\n' "$ACCENT" "$WIN_INSTALL_DIR" "$R"
    info "  ${BOLD}Atau via GUI:${R}"
    info "  System Properties → Environment Variables → Path → Edit → Hapus"
    printf '      %s%s%s\n\n' "$GREY" "$WIN_INSTALL_DIR" "$R"
}

# ═══════════════════════════════════════════════════════════════
# MAIN: Jalankan uninstaller sesuai OS
# ═══════════════════════════════════════════════════════════════

printf '\n'
info "OS terdeteksi: ${BOLD}${OS}${R}"
printf '\n'

case "$OS" in
    linux)
        uninstall_bash
        ;;

    macos)
        uninstall_bash
        ;;

    windows-gitbash)
        # Git Bash / MSYS2: hapus bash + PowerShell + CMD
        uninstall_bash
        printf '\n'
        uninstall_powershell
        printf '\n'
        uninstall_cmd
        ;;

    *)
        warn "OS tidak dikenali. Mencoba uninstall bash sebagai fallback."
        uninstall_bash
        ;;
esac

# ── Info tambahan jika di WSL ─────────────────────────────────
if is_wsl; then
    printf '\n'
    info "${BOLD}WSL terdeteksi.${R}"
    info "Jika kamu juga memasang Ruka AI di Windows (PowerShell/CMD),"
    info "jalankan uninstall.sh dari Git Bash untuk membersihkan semuanya."
fi

printf '\n'
ok "${BOLD}Selesai!${R} Semua jejak Ruka AI telah dibersihkan. 🐢\n"