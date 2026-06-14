# 🐢 Ruka AI — Email Skills & msmtp Guide

> Dokumentasi teknis cara mengirim email dari CLI menggunakan `msmtp`.
> File ini berfungsi sebagai MEMORI PERSISTEN — baca setiap session baru
> sebelum melakukan operasi email.

---

## 📋 Daftar Isi

- [1. Overview](#1-overview)
- [2. Credential & Config Path](#2-credential--config-path)
- [3. Setup msmtp (Jika Belum Ada Config)](#3-setup-msmtp-jika-belum-ada-config)
- [4. Cara Kirim Email](#4-cara-kirim-email)
- [5. Format Pesan dari File](#5-format-pesan-dari-file)
- [6. Provider SMTP Settings](#6-provider-smtp-settings)
- [7. Logging & Debugging](#7-logging--debugging)
- [8. Keamanan](#8-keamanan)
- [9. Troubleshooting](#9-troubleshooting)
- [10. Cheat Sheet](#10-cheat-sheet)

---

## 1. Overview

**Tool:** `msmtp` — lightweight SMTP relay client
**Fungsi:** Mengirim email dari terminal tanpa perlu MTA penuh (Postfix/Sendmail)
**Keunggulan:**
- Ringan, cocok untuk Termux / environment minimal
- Support TLS/SSL
- Bisa pakai multiple accounts
- Cocok untuk automation / scripting

**Cara kerja:**
```
Pesan (stdin/file) → msmtp → SMTP Server (Gmail, dll) → Penerima
```

**Prinsip:**
- `msmtp` hanya mengirim (send-only), tidak bisa menerima email
- Butuh SMTP credentials dari provider email
- Gmail butuh **App Password** (bukan password biasa)

---

## 2. Credential & Config Path

> ⚠️ **JANGAN tulis credential langsung di file skill ini.**
> Credential disimpan terpisah di folder config.

**Lokasi config email:**
```
config/email/msmtprc
```

**Isi config (tanpa credential):**
```
account default
host smtp.gmail.com
port 587
from EMAIL_KAMU@gmail.com
auth on
user EMAIL_KAMU@gmail.com
password APP_PASSWORD_DISINI
tls on
tls_starttls on
logfile ~/.msmtp.log
```

**Permission file config:**
```
chmod 600 config/email/msmtprc
```
File config HARUS punya permission `600` (hanya owner yang bisa baca/tulis).
Jika permission salah, `msmtp` akan menolak membaca config.

**Cek apakah config sudah ada:**
```bash
ls -la config/email/msmtprc
```

Jika file belum ada, lakukan setup (lihat bagian 3).

---

## 3. Setup msmtp (Jika Belum Ada Config)

### 3.1 Install msmtp

**Debian/Ubuntu/Termux:**
```bash
pkg install -y msmtp msmtp-mta
```

**Fedora/RHEL:**
```bash
sudo dnf install msmtp
```

**Arch:**
```bash
sudo pacman -S msmtp
```

**macOS:**
```bash
brew install msmtp
```

**Cek instalasi:**
```bash
which msmtp
msmtp --version
```

### 3.2 Buat Folder Config

```bash
mkdir -p config/email
```

### 3.3 Buat App Password (Khusus Gmail)

Gmail TIDAK mengizinkan login pakai password biasa dari CLI/app pihak ketiga.
Harus pakai **App Password**:

1. Buka https://myaccount.google.com/apppasswords
2. Login dengan akun Gmail kamu
3. Pilih "Pilih aplikasi" → **"Lainnya (Nama kustom)"**
4. Ketik nama: `msmtp CLI`
5. Klik **Buat**
6. Akan muncul 16 karakter password, contoh: `abcd efgh ijkl mnop`
7. Simpan password ini — hanya ditampilkan sekali

**⚠️ Catatan:**
- App Password hanya muncul saat 2FA (Two-Factor Authentication) aktif
- Jika belum aktifkan 2FA, buka https://myaccount.google.com/security terlebih dahulu
- App Password berbeda dengan password login Gmail

### 3.4 Buat File Config

Buat file `config/email/msmtprc` dengan format:

```
account default
host smtp.gmail.com
port 587
from EMAIL@gmail.com
auth on
user EMAIL@gmail.com
password APP_PASSWORD_16_KARAKTER
tls on
tls_starttls on
logfile ~/.msmtp.log
```

Ganti:
- `EMAIL@gmail.com` → alamat Gmail kamu
- `APP_PASSWORD_16_KARAKTER` → App Password yang sudah dibuat

### 3.5 Set Permission

```bash
chmod 600 config/email/msmtprc
```

### 3.6 Test Kirim Email

```bash
echo -e "Subject: Test Setup\n\nJika kamu menerima ini, setup berhasil!" | msmtp --file=config/email/msmtprc tujuan@gmail.com
```

Cek log untuk memastikan:
```bash
cat ~/.msmtp.log
```

Output sukses:
```
smtpstatus=250 smtpmsg='250 2.0.0 OK ...'
exitcode=EX_OK
```

---

## 4. Cara Kirim Email

### 4.1 Email Sederhana (dari echo)

```bash
echo -e "Subject: Subjek Email\n\nIsi pesan di sini." | msmtp --file=config/email/msmtprc tujuan@gmail.com
```

**Penjelasan:**
- `-e` pada echo menginterpretasikan `\n` sebagai baris baru
- Baris pertama setelah `Subject:` adalah subjek
- Baris kosong memisahkan header dan body
- `--file=config/email/msmtprc` path ke file config

### 4.2 Email dengan Body Multi-baris

```bash
cat <<'EOF' | msmtp --file=config/email/msmtprc tujuan@gmail.com
Subject: Subjek Email
From: kamu@gmail.com
To: tujuan@gmail.com

Halo ini isi email.
Bisa multi baris.
Bahua ada paragraf juga.

Salam,
Nama Kamu
EOF
```

### 4.3 Email dari File

Simpan pesan di file terlebih dahulu:

```bash
# Buat file pesan
cat > /tmp/email.txt <<'EOF'
To: tujuan@gmail.com
From: kamu@gmail.com
Subject: Subjek dari File

Isi pesan di sini.
EOF

# Kirim
msmtp --file=config/email/msmtprc tujuan@gmail.com < /tmp/email.txt
```

### 4.4 Email dengan Subjek Spesifik via -s Flag

`msmtp` tidak punya flag `-s` untuk subjek. Subjek HARUS ditulis di header pesan:

```bash
# SALAH — msmtp tidak punya flag -s
msmtp -s "Subjek" tujuan@gmail.com

# BENAR — tulis Subject di header
echo -e "Subject: Subjek\n\nBody" | msmtp --file=config/email/msmtprc tujuan@gmail.com
```

### 4.5 Email ke Multiple Penerima

```bash
echo -e "Subject: Halo Semua\n\nPesan untuk semua." | msmtp --file=config/email/msmtprc tujuan1@gmail.com tujuan2@gmail.com tujuan3@gmail.com
```

Atau via header `To:`:

```bash
cat <<'EOF' | msmtp --file=config/email/msmtprc tujuan1@gmail.com tujuan2@gmail.com
Subject: Halo Semua
To: tujuan1@gmail.com, tujuan2@gmail.com

Pesan untuk semua.
EOF
```

### 4.6 Email dengan CC dan BCC

```bash
cat <<'EOF' | msmtp --file=config/email/msmtprc tujuan@gmail.com
Subject: Email dengan CC
To: tujuan@gmail.com
CC: cc1@gmail.com, cc2@gmail.com
BCC: bcc@gmail.com

Isi pesan.
EOF
```

**Catatan:** BCC tidak terlihat oleh penerima lain, tapi tetap harus dicantumkan di header.

---

## 5. Format Pesan dari File

### 5.1 Format Standar RFC 2822

```
To: penerima@email.com
From: pengirim@email.com
Subject: Subjek Email
CC: cc@email.com
BCC: bcc@email.com
Content-Type: text/plain; charset=UTF-8
MIME-Version: 1.0

Ini adalah body email.
Bisa multi baris.
```

**Aturan:**
- Header dan body dipisahkan oleh **baris kosong**
- Setiap header di satu baris
- Urutan header tidak penting (kecuali baris pertama sebaiknya `To:` atau `From:`)
- Body dimulai setelah baris kosong

### 5.2 Format Minimal (hanya Subject)

```
Subject: Subjek

Body pesan.
```

Jika tidak ada header `To:`, msmtp akan menggunakan email tujuan dari command line.

---

## 6. Provider SMTP Settings

### 6.1 Gmail

```
host smtp.gmail.com
port 587
tls on
tls_starttls on
auth on
```

- **Port 587** — STARTTLS (recommended)
- **Port 465** — SSL/TLS langsung (alternatif)
- **Butuh App Password** (bukan password biasa)
- **2FA harus aktif** untuk membuat App Password

### 6.2 Outlook / Hotmail / Microsoft 365

```
host smtp-mail.outlook.com
port 587
tls on
tls_starttls on
auth on
```

- Pakai password biasa (tidak perlu App Password)
- Beberapa akun mungkin perlu buat App Password juga

### 6.3 Yahoo Mail

```
host smtp.mail.yahoo.com
port 587
tls on
tls_starttls on
auth on
```

- Butuh App Password (seperti Gmail)
- Aktifkan "Allow apps that use less sign-in" di pengaturan keamanan Yahoo

### 6.4 Zoho Mail

```
host smtp.zoho.com
port 587
tls on
tls_starttls on
auth on
```

### 6.5 iCloud

```
host smtp.mail.me.com
port 587
tls on
tls_starttls on
auth on
```

- Butuh App-Specific Password dari appleid.apple.com

### 6.6 Custom SMTP (VPS / Self-hosted)

```
host mail.domain-kamu.com
port 587        # atau 465 untuk SSL langsung
tls on
tls_starttls on # hapus jika pakai port 465
auth on
```

---

## 7. Logging & Debugging

### 7.1 Cek Log msmtp

Log disimpan di `~/.msmtp.log` (sesuai config):

```bash
cat ~/.msmtp.log
```

### 7.2 Output Log Sukses

```
Jun 14 14:19:27 host=smtp.gmail.com tls=on auth=on user=kamu@gmail.com from=kamu@gmail.com recipients=tujuan@gmail.com mailsize=314 smtpstatus=250 smtpmsg='250 2.0.0 OK  1781421567 ...' exitcode=EX_OK
```

**Field penting:**
- `smtpstatus=250` — SMTP success code
- `exitcode=EX_OK` — Program exit sukses
- `mailsize=314` — Ukuran email dalam bytes

### 7.3 Output Log Gagal

```
... smtpstatus=535 smtpmsg='535-5.7.8 Username and Password not accepted' exitcode=EX_TEMPFAIL
```

**Kemungkinan penyebab:**
- Password salah
- App Password belum dibuat (Gmail)
- 2FA belum aktif (Gmail)
- Akun terkunci / perlu verifikasi

### 7.4 Verbose Mode

Untuk debug lebih detail, tambahkan `--tls-certificate-check=off` (hanya untuk debug):

```bash
echo "test" | msmtp --verbose --file=config/email/msmtprc tujuan@gmail.com 2>&1
```

---

## 8. Keamanan

### 8.1 Permission File Config

**SELALU** set permission `600` pada file config:

```bash
chmod 600 config/email/msmtprc
```

Jangan biarkan file config bisa dibaca user lain — berisi password!

### 8.2 Jangan Hardcode Password di Script

**SALAH:**
```bash
msmtp --host=smtp.gmail.com --user=kamu@gmail.com --password=rahasia tujuan@gmail.com
```

**BENAR:**
```bash
msmtp --file=config/email/msmtprc tujuan@gmail.com
```

### 8.3 Jangan Commit Config ke Git

Pastikan `config/email/msmtprc` ada di `.gitignore`:

```
config/email/
```

### 8.4 Gunakan App Password, Bukan Password Utama

- App Password bisa dicabut kapan saja tanpa mempengaruhi password utama
- Jika dicurigai bocor, hapus App Password dan buat yang baru
- Setiap app bisa punya App Password sendiri

### 8.5 TLS Wajib

Selalu aktifkan TLS:

```
tls on
tls_starttls on
```

Jangan kirim email tanpa enkripsi — password dan isi email bisa dibaca pihak ketiga.

---

## 9. Troubleshooting

### 9.1 "msmtp: command not found"

**Solusi:**
```bash
pkg install -y msmtp msmtp-mta    # Termux
sudo apt install msmtp msmtp-mta  # Debian/Ubuntu
```

### 9.2 "msmtp: /path/to/msmtprc: contains no account"

**Penyeausa:** Format config salah atau tidak ada `account default`

**Solusi:** Pastikan config punya `account default` di bagian atas

### 9.3 "msmtp: account default not found"

**Penyebab:** Config tidak terbaca atau path salah

**Solusi:**
```bash
# Cek path config
ls -la config/email/msmtprc

# Pastikan pakai --file yang benar
msmtp --file=config/email/msmtprc tujuan@gmail.com
```

### 9.4 "535-5.7.8 Username and Password not accepted"

**Penyebab:**
- Password salah
- Gmail: belum pakai App Password
- Gmail: 2FA belum aktif
- Akun terkunci

**Solusi:**
1. Buat App Password baru di https://myaccount.google.com/apppasswords
2. Update password di `config/email/msmtprc`
3. Test ulang

### 9.5 "530-5.7.0 Must issue a STARTTLS command first"

**Penyeausa:** TLS tidak aktif di config

**Solusi:** Pastikan config punya:
```
tls on
tls_starttls on
```

### 9.6 "Connection timed out"

**Penyebab:**
- Tidak ada koneksi internet
- Port diblokir firewall
- SMTP server down

**Solusi:**
```bash
# Cek koneksi
ping smtp.gmail.com

# Cek port
nc -zv smtp.gmail.com 587
```

### 9.7 "msmtp: cannot use a secure memory allocation strategy"

**Penyeausa:** Masalah permission di Termux/environment tertentu

**Solusi:**
```bash
export GCRYPT_ALLOW_RANDOM_SUCKING=1
```

Atau tambahkan di `~/.bashrc`:
```bash
echo 'export GCRYPT_ALLOW_RANDOM_SUCKING=1' >> ~/.bashrc
```

### 9.8 Email Masuk Spam

**Penyeausa:**
- Tidak ada DKIM/SPF record (pakai Gmail seharusnya otomatis)
- Konten terdeteksi spam
- Pengirim baru / tidak dikenal

**Solusi:**
- Pastikan `from:` sesuai dengan akun yang login
- Hindari kata-kata trigger spam di subjek
- Minta penerima tambahkan ke contacts

---

## 10. Cheat Sheet

### Quick Commands

```bash
# === CEK SETUP ===
which msmtp                              # Cek msmtp terinstall
msmtp --version                          # Cek versi
ls -la config/email/msmtprc              # Cek config ada
cat ~/.msmtp.log                         # Cek log

# === KIRIM EMAIL ===
# Sederhana
echo -e "Subject: Halo\n\nIsi pesan." | msmtp --file=config/email/msmtprc tujuan@gmail.com

# Multi-baris via heredoc
cat <<'EOF' | msmtp --file=config/email/msmtprc tujuan@gmail.com
Subject: Subjek
To: tujuan@gmail.com

Isi pesan multi baris.
EOF

# Dari file
msmtp --file=config/email/msmtprc tujuan@gmail.com < /tmp/email.txt

# Multiple penerima
echo -e "Subject: Halo\n\nPesan." | msmtp --file=config/email/msmtprc tujuan1@gmail.com tujuan2@gmail.com

# === SETUP AWAL ===
pkg install -y msmtp msmtp-mta           # Install
mkdir -p config/email                     # Buat folder
chmod 600 config/email/msmtprc           # Set permission

# === DEBUG ===
cat ~/.msmtp.log                          # Lihat log
echo "test" | msmtp --verbose --file=config/email/msmtprc tujuan@gmail.com 2>&1
```

### Decision Tree: Mau Kirim Email?

```
Mau kirim email?
│
├─ Config sudah ada?
│  ├─ YA → Langsung kirim:
│  │       echo -e "Subject: ...\n\n..." | msmtp --file=config/email/msmtprc tujuan@gmail.com
│  │
│  └─ BELUM → Setup dulu:
│     1. pkg install -y msmtp msmtp-mta
│     2. mkdir -p config/email
│     3. Buat App Password (Gmail) / siapkan password
│     4. Buat config/email/msmtprc
│     5. chmod 600 config/email/msmtprc
│     6. Test kirim
│
├─ Butuh lampiran (attachment)?
│  └─ msmtp TIDAK support attachment.
│     Gunakan mpack atau Python script.
│
├─ Butuh HTML email?
│  └─ Tulis header Content-Type: text/html di pesan:
│     echo -e "Subject: HTML\nContent-Type: text/html\n\n<h1>Halo</h1>" | msmtp --file=config/email/msmtprc tujuan@gmail.com
│
└─ Kirim gagal?
   └─ Cek log: cat ~/.msmtp.log
      ├─ 535 error → Password salah / belum App Password
      ├─ 530 error → TLS belum aktif
      ├─ timeout → Cek koneksi / port
      └─ EX_OK tapi tidak diterima → Cek spam penerima
```

---

## 📌 Catatan Penting

- **Config path:** `config/email/msmtprc` (JANGAN di-commit ke git)
- **Log path:** `~/.msmtp.log`
- **Gmail wajib pakai App Password** — password biasa tidak akan bekerja
- **Permission config HARUS 600** — msmtp akan menolak jika terlalu open
- **msmtp hanya kirim** — tidak bisa menerima/baca email
- **Attachment tidak native** — butuh `mpack` atau Python `smtplib` + `email.mime`

---

<div align="center">

**🐢 Ruka AI — Email Skills v1.0**
*Di-generate berdasarkan percobaan langsung msmtp + Gmail di environment Termux.*
*Update file ini setiap ada penemuan baru.*

</div>
