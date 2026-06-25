#!/usr/bin/env bash
#
# install.sh — Pasang alias `ruka` ke ~/.bashrc
#
# Setelah dipasang, kamu cukup `cd` ke folder mana pun lalu ketik `ruka`.
# Ruka AI akan menjadikan folder tempat kamu berada (cwd) sebagai workspace,
# sementara file internal (SKILL/, sessions/, .env) tetap dibaca dari folder
# instalasi ini.
#
# Jalankan:  bash install.sh   (atau ./install.sh setelah chmod +x)

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
BASHRC="$HOME/.bashrc"

# ── Validasi main.py ada di folder instalasi ─────────────────
[ -f "$MAIN_PY" ] || fail "main.py tidak ditemukan di ${INSTALL_DIR}"

# ── Tentukan interpreter Python (prefer python3) ─────────────
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    fail "Python tidak ditemukan. Install python3 dulu."
fi

# Baris alias final. Path di-quote (double-quote di dalam single-quote) agar
# tetap aman bila folder instalasi mengandung spasi.
ALIAS_LINE="alias ruka='${PYTHON_BIN} \"${MAIN_PY}\"'"

# ── Pastikan ~/.bashrc ada ───────────────────────────────────
[ -f "$BASHRC" ] || touch "$BASHRC"

# ── Sudah terpasang? ─────────────────────────────────────────
# Cek alias `ruka` apa pun yang sudah ada (dipasang installer ini atau manual).
if grep -qE '^[[:space:]]*alias[[:space:]]+ruka=' "$BASHRC"; then
    warn "${BOLD}Ruka AI sudah terinstall.${R}"
    info "Alias 'ruka' sudah ada di ${BASHRC}."
    info "Untuk memperbarui path, edit baris alias tersebut secara manual."
    printf '\n'
    exit 0
fi

# ── Pasang alias ─────────────────────────────────────────────
{
    printf '\n'
    printf '# Ruka AI — alias (ditambahkan oleh install.sh)\n'
    printf '%s\n' "$ALIAS_LINE"
} >> "$BASHRC"

ok "${BOLD}Ruka AI terinstall!${R}"
info "Alias ditambahkan ke ${BASHRC}:"
printf '      %s%s%s\n' "$ACCENT" "$ALIAS_LINE" "$R"
printf '\n'
info "Aktifkan sekarang:  ${BOLD}source ~/.bashrc${R}"
info "Lalu dari folder mana pun:  ${BOLD}cd ~/proyek-ku && ruka${R}"
printf '\n'
