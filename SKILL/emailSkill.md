# 🐢 Ruka AI — Email Skills & msmtp Guide

> Dokumentasi teknis cara mengirim & membaca email dari CLI menggunakan `msmtp` dan Python `imaplib`.
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
- [11. Membaca Inbox via Python imaplib](#11-membaca-inbox-via-python-imaplib)

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
- Untuk membaca inbox, gunakan Python `imaplib` (bawaan Python, tidak perlu install)
- Butuh SMTP/IMAP credentials dari provider email
- Gmail butuh **App Password** (bukan password biasa)

---

## 2. Credential & Config Path

> ⚠️ **JANGAN tulis credential langsung di file skill ini.**
> Credential disimpan terpisah di folder config.

**Lokasi config email:**
```
SKILL/config/email/msmtprc
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
chmod 600 SKILL/config/email/msmtprc
```
File config HARUS punya permission `600` (hanya owner yang bisa baca/tulis).
Jika permission salah, `msmtp` akan menolak membaca config.

**Cek apakah config sudah ada:**
```bash
ls -la SKILL/config/email/msmtprc
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

Buat file `SKILL/config/email/msmtprc` dengan format:

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
chmod 600 SKILL/config/email/msmtprc
```

### 3.6 Test Kirim Email

```bash
echo -e "Subject: Test Setup\n\nJika kamu menerima ini, setup berhasil!" | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
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
echo -e "Subject: Subjek Email\n\nIsi pesan di sini." | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
```

**Penjelasan:**
- `-e` pada echo menginterpretasikan `\n` sebagai baris baru
- Baris pertama setelah `Subject:` adalah subjek
- Baris kosong memisahkan header dan body
- `--file=SKILL/config/email/msmtprc` path ke file config

### 4.2 Email dengan Body Multi-baris

```bash
cat <<'EOF' | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
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
msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com < /tmp/email.txt
```

### 4.4 Email dengan Subjek Spesifik via -s Flag

`msmtp` tidak punya flag `-s` untuk subjek. Subjek HARUS ditulis di header pesan:

```bash
# SALAH — msmtp tidak punya flag -s
msmtp -s "Subjek" tujuan@gmail.com

# BENAR — tulis Subject di header
echo -e "Subject: Subjek\n\nBody" | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
```

### 4.5 Email ke Multiple Penerima

```bash
echo -e "Subject: Halo Semua\n\nPesan untuk semua." | msmtp --file=SKILL/config/email/msmtprc tujuan1@gmail.com tujuan2@gmail.com tujuan3@gmail.com
```

Atau via header `To:`:

```bash
cat <<'EOF' | msmtp --file=SKILL/config/email/msmtprc tujuan1@gmail.com tujuan2@gmail.com
Subject: Halo Semua
To: tujuan1@gmail.com, tujuan2@gmail.com

Pesan untuk semua.
EOF
```

### 4.6 Email dengan CC dan BCC

```bash
cat <<'EOF' | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
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
echo "test" | msmtp --verbose --file=SKILL/config/email/msmtprc tujuan@gmail.com 2>&1
```

---

## 8. Keamanan

### 8.1 Permission File Config

**SELALU** set permission `600` pada file config:

```bash
chmod 600 SKILL/config/email/msmtprc
```

Jangan biarkan file config bisa dibaca user lain — berisi password!

### 8.2 Jangan Hardcode Password di Script

**SALAH:**
```bash
msmtp --host=smtp.gmail.com --user=kamu@gmail.com --password=rahasia tujuan@gmail.com
```

**BENAR:**
```bash
msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
```

### 8.3 Jangan Commit Config ke Git

Pastikan `SKILL/config/email/msmtprc` ada di `.gitignore`:

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
ls -la SKILL/config/email/msmtprc

# Pastikan pakai --file yang benar
msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
```

### 9.4 "535-5.7.8 Username and Password not accepted"

**Penyebab:**
- Password salah
- Gmail: belum pakai App Password
- Gmail: 2FA belum aktif
- Akun terkunci

**Solusi:**
1. Buat App Password baru di https://myaccount.google.com/apppasswords
2. Update password di `SKILL/config/email/msmtprc`
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
ls -la SKILL/config/email/msmtprc              # Cek config ada
cat ~/.msmtp.log                         # Cek log

# === KIRIM EMAIL ===
# Sederhana
echo -e "Subject: Halo\n\nIsi pesan." | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com

# Multi-baris via heredoc
cat <<'EOF' | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
Subject: Subjek
To: tujuan@gmail.com

Isi pesan multi baris.
EOF

# Dari file
msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com < /tmp/email.txt

# Multiple penerima
echo -e "Subject: Halo\n\nPesan." | msmtp --file=SKILL/config/email/msmtprc tujuan1@gmail.com tujuan2@gmail.com

# === SETUP AWAL ===
pkg install -y msmtp msmtp-mta           # Install
mkdir -p config/email                     # Buat folder
chmod 600 SKILL/config/email/msmtprc           # Set permission

# === DEBUG ===
cat ~/.msmtp.log                          # Lihat log
echo "test" | msmtp --verbose --file=SKILL/config/email/msmtprc tujuan@gmail.com 2>&1

# === BACA INBOX (Python imaplib) ===
# Lihat 10 email terbaru
python3 -c "
import imaplib, email
from email.header import decode_header
mail = imaplib.IMAP4_SSL(\"imap.gmail.com\", 993)
mail.login(\"EMAIL@gmail.com\", \"APP_PASSWORD\")
mail.select(\"INBOX\")
status, msgs = mail.search(None, \"ALL\")
ids = msgs[0].split()
for eid in reversed(ids[-10:]):
    _, data = mail.fetch(eid, \"(RFC822)\")
    for part in data:
        if isinstance(part, tuple):
            m = email.message_from_bytes(part[1])
            s = decode_header(m[\"Subject\"] or \"\")
            subject = \"\".join(p.decode(e or \"utf-8\") if isinstance(p, bytes) else p for p,e in s)
            print(f\"[{m['From']}] {subject}\")
mail.logout()
"

# Cari email belum dibaca
# Ganti 'UNSEEN' dengan search keyword lain (lihat bagian 11.5)
python3 -c "
import imaplib, email
mail = imaplib.IMAP4_SSL(\"imap.gmail.com\", 993)
mail.login(\"EMAIL@gmail.com\", \"APP_PASSWORD\")
mail.select(\"INBOX\")
status, msgs = mail.search(None, \"UNSEEN\")
ids = msgs[0].split()
print(f\"Email belum dibaca: {len(ids)}\")
mail.logout()
"
```

### Decision Tree: Mau Kirim Email?

```
Mau kirim email?
│
├─ Config sudah ada?
│  ├─ YA → Langsung kirim:
│  │       echo -e "Subject: ...\n\n..." | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
│  │
│  └─ BELUM → Setup dulu:
│     1. pkg install -y msmtp msmtp-mta
│     2. mkdir -p config/email
│     3. Buat App Password (Gmail) / siapkan password
│     4. Buat SKILL/config/email/msmtprc
│     5. chmod 600 SKILL/config/email/msmtprc
│     6. Test kirim
│
├─ Butuh lampiran (attachment)?
│  └─ msmtp TIDAK support attachment.
│     Gunakan mpack atau Python script.
│
├─ Butuh HTML email?
│  └─ Tulis header Content-Type: text/html di pesan:
│     echo -e "Subject: HTML\nContent-Type: text/html\n\n<h1>Halo</h1>" | msmtp --file=SKILL/config/email/msmtprc tujuan@gmail.com
│
├─ Mau baca inbox?
│  └─ Pakai Python imaplib:
│     1. Pastikan IMAP aktif di Gmail settings
│     2. Gunakan App Password yang sama
│     3. Lihat bagian 11 untuk script lengkap
│     4. Server: imap.gmail.com:993 (SSL)
│
├─ Mau download lampiran?
│  └─ Pakai Python imaplib (lihat bagian 11.7)
│     Loop multipart, cek Content-Disposition == "attachment"
│
└─ Kirim gagal?
   └─ Cek log: cat ~/.msmtp.log
      ├─ 535 error → Password salah / belum App Password
      ├─ 530 error → TLS belum aktif
      ├─ timeout → Cek koneksi / port
      └─ EX_OK tapi tidak diterima → Cek spam penerima
```

---

## 11. Membaca Inbox via Python imaplib

`msmtp` hanya bisa mengirim email. Untuk **membaca inbox**, kita gunakan module bawaan Python `imlib` + `email`.

### 11.1 Prasyarat

**IMAP harus aktif di Gmail:**
1. Buka Gmail → Settings (ikon gear) → See all settings
2. Tab "Forwarding and POP/IMAP"
3. Pilih "Enable IMAP"
4. Klik Save Changes

**App Password:**
- Sama seperti setup msmtp — pakai App Password yang sudah dibuat
- App Password yang sama bisa dipakai untuk SMTP (msmtp) dan IMAP (Python)

**Tidak perlu install apapun** — `imaplib` dan `email` adalah module bawaan Python.

### 11.2 Script Baca Inbox (10 Email Terbaru)

```python
import imaplib
import email
from email.header import decode_header

# Connect ke Gmail IMAP
mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("EMAIL_KAMU@gmail.com", "APP_PASSWORD")
mail.select("INBOX")

# Cari semua email di inbox
status, messages = mail.search(None, "ALL")
email_ids = messages[0].split()
total = len(email_ids)
print(f"Total email di inbox: {total}")

# Ambil 10 email terbaru
latest_ids = email_ids[-10:]
for eid in reversed(latest_ids):
    status, msg_data = mail.fetch(eid, "(RFC822)")
    if status != "OK":
        continue
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])

            # Decode subject
            subject_raw = msg["Subject"]
            if subject_raw:
                decoded = decode_header(subject_raw)
                subject = ""
                for part, enc in decoded:
                    if isinstance(part, bytes):
                        subject += part.decode(enc or "utf-8", errors="replace")
                    else:
                        subject += part
            else:
                subject = "(Tanpa subjek)"

            # Decode sender
            from_raw = msg["From"]
            if from_raw:
                decoded = decode_header(from_raw)
                sender = ""
                for part, enc in decoded:
                    if isinstance(part, bytes):
                        sender += part.decode(enc or "utf-8", errors="replace")
                    else:
                        sender += part
            else:
                sender = "(Unknown)"

            # Date
            date = msg["Date"] or "(Tanpa tanggal)"

            # Body preview
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")[:200]
                        except:
                            body = "(tidak bisa decode)"
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="replace")[:200]
                except:
                    body = "(tidak bisa decode)"

            print(f"Subjek  : {subject}")
            print(f"Dari    : {sender}")
            print(f"Tanggal : {date}")
            print(f"Preview : {body[:150]}")
            print("-" * 60)

mail.logout()
```

### 11.3 Baca Email Lengkap Berdasarkan Index

Untuk membaca satu email secara lengkap (bukan preview), ganti bagian loop dengan:

```python
# Baca email ke-N terbaru (0 = paling baru)
idx = 0
eid = email_ids[-(idx+1)]
status, msg_data = mail.fetch(eid, "(RFC822)")
for response_part in msg_data:
    if isinstance(response_part, tuple):
        msg = email.message_from_bytes(response_part[1])
        print(f"Subject: {msg['Subject']}")
        print(f"From: {msg['From']}")
        print(f"Date: {msg['Date']}")
        print("=" * 60)
        # Print full body
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    print(part.get_payload(decode=True).decode("utf-8", errors="replace"))
        else:
            print(msg.get_payload(decode=True).decode("utf-8", errors="replace"))
```

### 11.4 Cari Email dengan Kata Kunci

```python
# Cari email yang mengandung kata kunci di subjek
status, messages = mail.search(None, 'SUBJECT "keyword"')

# Cari email dari pengirim tertentu
status, messages = mail.search(None, 'FROM "pengirim@email.com"')

# Cari email yang belum dibaca
status, messages = mail.search(None, 'UNSEEN')

# Cari email dalam rentang tanggal
status, messages = mail.search(None, 'SINCE "01-Jun-2026" BEFORE "15-Jun-2026"')

# Kombinasi: belum dibaca + dari pengirim tertentu
status, messages = mail.search(None, 'UNSEEN FROM "pengirim@email.com"')
```

### 11.5 IMAP Search Keywords

```
ALL          — Semua email
UNSEEN       — Belum dibaca
SEEN         — Sudah dibaca
FROM "x"     — Dari pengirim tertentu
SUBJECT "x"  — Subjek mengandung kata
SINCE "x"    — Setelah tanggal (format: DD-Mon-YYYY)
BEFORE "x"   — Sebelum tanggal
LARGER "x"   — Lebih besar dari x bytes
SMALLER "x"  — Lebih kecil dari x bytes
TO "x"       — Tertuju ke
CC "x"       — CC ke
BCC "x"      — BCC ke
TEXT "x"     — Body mengandung kata
OR / AND     — Kombinasi kondisi
```

### 11.6 Baca Email dari Folder Lain

```python
# List semua folder
status, folders = mail.list()
for folder in folders:
    print(folder)

# Baca dari folder tertentu
mail.select("[Gmail]/Sent")       # Sent mail
mail.select("[Gmail]/Drafts")     # Drafts
mail.select("[Gmail]/Trash")      # Trash
mail.select("[Gmail]/Spam")       # Spam
mail.select("[Gmail]/All Mail")   # All Mail
```

### 11.7 Download Lampiran (Attachment)

```python
import os

if msg.is_multipart():
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename()
            if filename:
                # Decode filename jika perlu
                decoded = decode_header(filename)
                fname = ""
                for part_name, enc in decoded:
                    if isinstance(part_name, bytes):
                        fname += part_name.decode(enc or "utf-8", errors="replace")
                    else:
                        fname += part_name
                # Simpan file
                filepath = os.path.join("/tmp", fname)
                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))
                print(f"Lampiran disimpan: {filepath}")
```

### 11.8 Tandai Email sebagai Sudah Dibaca / Belum Dibaca

```python
# Tandai sebagai SUDAH dibaca (add \Seen flag)
mail.store(eid, "+FLAGS", "\\Seen")

# Tandai sebagai BELUM dibaca (remove \Seen flag)
mail.store(eid, "-FLAGS", "\\Seen")

# Tandai sebagai dihapus
mail.store(eid, "+FLAGS", "\\Deleted")
mail.expunge()
```

### 11.9 IMAP Server Settings untuk Baca Inbox

```
Gmail:
  IMAP: imap.gmail.com:993 (SSL)
  SMTP: smtp.gmail.com:587 (STARTTLS)

Outlook:
  IMAP: imap-mail.outlook.com:993 (SSL)
  SMTP: smtp-mail.outlook.com:587 (STARTTLS)

Yahoo:
  IMAP: imap.mail.yahoo.com:993 (SSL)
  SMTP: smtp.mail.yahoo.com:587 (STARTTLS)

iCloud:
  IMAP: imap.mail.me.com:993 (SSL)
  SMTP: smtp.mail.me.com:587 (STARTTLS)
```

### 11.10 Troubleshooting IMAP

**Error: `[AUTHENTICATIONFAILED] Invalid credentials`**
- Pastikan App Password benar (bukan password biasa)
- Pastikan 2FA sudah aktif di Gmail
- Buat App Password baru jika perlu

**Error: `LOGIN failed`**
- Cek apakah IMAP sudah aktif di Gmail settings
- Coba login manual: `openssl s_client -connect imap.gmail.com:993`

**Error: `Connection refused`**
- Cek koneksi internet
- Cek apakah port 993 diblokir firewall

**Email body kosong atau HTML:**
- Cek `text/plain` dulu, fallback ke `text/html`
- Untuk HTML, bisa convert ke text dengan `html2text` atau regex

**Decode error pada subject/sender:**
- Selalu gunakan `decode_header()` dari `email.header`
- Gunakan `errors="replace"` untuk hindari crash

---

## 📌 Catatan Penting

- **Config path:** `SKILL/config/email/msmtprc` (JANGAN di-commit ke git)
- **Log path:** `~/.msmtp.log`
- **Gmail wajib pakai App Password** — password biasa tidak akan bekerja
- **Permission config HARUS 600** — msmtp akan menolak jika terlalu open
- **msmtp hanya kirim** — tidak bisa menerima/baca email
- **Baca inbox pakai Python `imaplib`** — module bawaan Python, tidak perlu install
- **Attachment tidak native di msmtp** — butuh `mpack` atau Python `smtplib` + `email.mime`
- **Download lampiran via `imaplib`** — lihat bagian 11.7
- **IMAP Gmail:** `imap.gmail.com:993` (SSL) — harus aktifkan IMAP di Gmail settings

---

<div align="center">

**🐢 Ruka AI — Email Skills v1.1**
*Di-generate berdasarkan percobaan langsung msmtp + Python imaplib + Gmail di environment Termux.*
*Update file ini setiap ada penemuan baru.*

</div>
