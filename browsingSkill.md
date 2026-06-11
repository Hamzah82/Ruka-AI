# 🐢 Ruka AI — Browsing Skills & Web Scraping Guide

> Dokumentasi teknis cara browsing dan mengambil data dari internet
> menggunakan tools yang tersedia di environment Termux (Android).
> File ini berfungsi sebagai MEMORI PERSISTEN — baca setiap session baru.

---

## 📋 Daftar Isi

- [1. Environment Overview](#1-environment-overview)
- [2. Tools yang Tersedia](#2-tools-yang-tersedia)
- [3. Masalah Utama: Google Blocking](#3-masalah-utama-google-blocking)
- [4. Solusi: Search Engine Alternatif](#4-solusi-search-engine-alternatif)
- [5. Pattern Scraping yang Sudah Teruji](#5-pattern-scraping-yang-sudah-teruji)
- [6. API Endpoints yang Berguna](#6-api-endpoints-yang-berguna)
- [7. Troubleshooting](#7-troubleshooting)
- [8. Cheat Sheet](#8-cheat-sheet)

---

## 1. Environment Overview

**Platform:** Termux (Android) — Linux-like environment di Android
**Base Dir:** Direktori kerja agent (bisa dicek dengan `pwd`)
**Package Manager:** `pkg` (bukan `apt`)
**Python:** Tersedia (`python3`)
**Shell:** Bash via `/bin/bash`

**Keterbatasan:**
- Tidak ada GUI browser (Chrome, Firefox)
- Google memblokir semua text-based browser (lynx, w3m)
- Google memblokir curl/python requests tanpa JS engine
- Tidak bisa menjalankan JavaScript
- Beberapa command Unix tidak tersedia (`which` perlu diinstall)

---

## 2. Tools yang Tersedia

### 2.1 curl
- **Status:** ✅ Tersedia (pre-installed)
- **Fungsi:** HTTP requests dari terminal
- **Keterbatasan:** Google memblokir request tanpa JS
- **Usage dasar:**
  ```bash
  curl -s "URL"                    # Silent mode
  curl -s -L "URL"                 # Follow redirects
  curl -s -L -H "Header" "URL"     # Custom headers
  ```

### 2.2 lynx
- **Status:** ✅ Tersedia (install: `pkg install -y lynx`)
- **Versi:** 2.9.2
- **Fungsi:** Text-based web browser, bisa dump halaman HTML sebagai teks
- **Keterbatasan:** Google memblokir dengan "Update browser Anda"
- **Usage dasar:**
  ```bash
  lynx -dump "URL"                                    # Dump halaman sebagai teks
  lynx -dump -useragent="UA_STRING" "URL"             # Custom user-agent
  lynx -dump "URL" 2>&1 | head -100                   # Batasi output
  ```
- **Catatan Penting:** Custom user-agent TIDAK membantu bypass Google.
  Google tetap mendeteksi lynx dari behavior (tidak ada JS execution).

### 2.3 w3m
- **Status:** ✅ Tersedia (install: `pkg install -y w3m`)
- **Versi:** 0.5.6
- **Fungsi:** Text-based web browser alternatif
- **Keterbatasan:** Sama seperti lynx — Google memblokir
- **Usage dasar:**
  ```bash
  w3m -dump "URL"                    # Dump halaman sebagai teks
  w3m -dump "URL" 2>&1 | head -100   # Batasi output
  ```

### 2.4 python3
- **Status:** ✅ Tersedia (pre-installed)
- **Fungsi:** HTTP requests via `urllib`, parsing HTML, regex
- **Modules tersedia:** `urllib.request`, `json`, `re`
- **Usage dasar:**
  ```python
  import urllib.request, json, re

  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'Accept-Language': 'en-US,en;q=0.9'
  }
  req = urllib.request.Request(url, headers=headers)
  with urllib.request.urlopen(req, timeout=10) as resp:
      html = resp.read().decode('utf-8')
  ```

---

## 3. Masalah Utama: Google Blocking

### 3.1 Gejala
- Google menampilkan "Update browser Anda" untuk lynx/w3m
- Google menampilkan halaman JS redirect untuk curl/python
- Google menampilkan CAPTCHA atau halaman kosong
- Output tidak mengandung hasil pencarian yang berguna

### 3.2 Penyebab
- Google mendeteksi text-based browser dari User-Agent
- Google membutuhkan JavaScript execution untuk render hasil
- Google menggunakan bot detection berbasis behavior
- Semua tools kita tidak bisa menjalankan JavaScript

### 3.3 Kesimpulan
**GOOGLE TIDAK BISA DIAKSES langsung dari environment ini.**
Jangan buang waktu mencoba bypass Google dengan custom headers/UA.
Langsung gunakan alternatif (lihat bagian 4).

---

## 4. Solusi: Search Engine Alternatif

### 4.1 DuckDuckGo (HTML Version) — ⭐ REKOMENDASI UTAMA
- **URL:** `https://html.duckduckgo.com/html/?q=QUERY`
- **Status:** ✅ BERHASIL — Tidak memblokir text-based browser
- **Output:** HTML sederhana yang bisa di-dump dengan lynx/w3m
- **Usage:**
  ```bash
  lynx -dump "https://html.duckduckgo.com/html/?q=QUERY" 2>&1
  ```
- **Contoh berhasil:**
  ```bash
  lynx -dump "https://html.duckduckgo.com/html/?q=instagram+walikota+surabaya"
  ```
  Output: Hasil pencarian lengkap dengan URL, snippet, dan ranking.

- **Parsing tips:**
  - Hasil ada di section `[N]URL` dan deskripsi setelahnya
  - Format: `[number]URL_TITLE` lalu deskripsi, lalu `[link_number]actual_url`
  - Gunakan `grep` atau `head` untuk filter output

### 4.2 DuckDuckGo (Lite Version)
- **URL:** `https://lite.duckduckgo.com/lite/?q=QUERY`
- **Status:** ✅ Bisa dicoba sebagai alternatif
- **Usage:**
  ```bash
  lynx -dump "https://lite.duckduckgo.com/lite/?q=QUERY"
  ```

### 4.3 Bing
- **URL:** `https://www.bing.com/search?q=QUERY`
- **Status:** Perlu diuji — mungkin juga memblokir
- **Usage:**
  ```bash
  lynx -dump "https://www.bing.com/search?q=QUERY"
  ```

### 4.4 Startpage
- **URL:** `https://www.startpage.com/do/search?q=QUERY`
- **Status:** Perlu diuji

---

## 5. Pattern Scraping yang Sudah Teruji

### 5.1 Pattern: Cari Info via DuckDuckGo + lynx
```bash
lynx -dump "https://html.duckduckgo.com/html/?q=SEARCH_QUERY" 2>&1 | head -100
```
**Kapan digunakan:** Butuh hasil pencarian umum dari internet.

### 5.2 Pattern: Ambil Data dari API JSON
```bash
curl -s "API_ENDPOINT" 2>&1
```
**Kapan digunakan:** Tersedia API publik yang mengembalikan JSON.
**Contoh berhasil:**
```bash
curl -s "https://api.exchangerate-api.com/v4/latest/USD"
curl -s "https://wise.com/rates/live?source=USD&target=IDR"
```

### 5.3 Pattern: Scrape Halaman Spesifik via Python
```python
import urllib.request, re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=10) as resp:
    html = resp.read().decode('utf-8')
    # Parse dengan regex
    matches = re.findall(r'PATTERN', html)
```
**Kapan digunakan:** Perlu scrape halaman spesifik yang tidak memblokir bot.

### 5.4 Pattern: Scrape via lynx dump + grep
```bash
lynx -dump "URL" 2>&1 | grep -i "keyword"
```
**Kapan digunakan:** Perlu extract informasi spesifik dari halaman.

---

## 6. API Endpoints yang Berguna

### 6.1 Kurs / Exchange Rate
| Provider | URL | Status |
|----------|-----|--------|
| ExchangeRate-API | `https://api.exchangerate-api.com/v4/latest/USD` | ✅ BERHASIL |
| Wise | `https://wise.com/rates/live?source=USD&target=IDR` | ✅ BERHASIL |
| Google Finance | `https://www.google.com/finance/quote/USD-IDR` | ❌ DIBLOKIR |

### 6.2 Search
| Provider | URL Pattern | Status |
|----------|-------------|--------|
| DuckDuckGo HTML | `https://html.duckduckgo.com/html/?q=QUERY` | ✅ BERHASIL |
| Google Search | `https://www.google.com/search?q=QUERY` | ❌ DIBLOKIR |
| DuckDuckGo Lite | `https://lite.duckduckgo.com/lite/?q=QUERY` | ✅ Perlu diuji |

### 6.3 Lainnya (Perlu Diuji)
| Provider | URL | Kegunaan |
|----------|-----|----------|
| Wikipedia API | `https://en.wikipedia.org/api/rest_v1/page/summary/TITLE` | Info Wikipedia |
| OpenWeatherMap | `https://api.openweathermap.org/data/2.5/weather?q=CITY&appid=KEY` | Cuaca |
| GitHub API | `https://api.github.com/users/USERNAME` | Info GitHub user |
| JSONPlaceholder | `https://jsonplaceholder.typicode.com/posts` | Testing API |

---

## 7. Troubleshooting

### 7.1 "Update browser Anda" dari Google
**Solusi:** Jangan pakai Google. Pakai DuckDuckGo HTML:
```bash
lynx -dump "https://html.duckduckgo.com/html/?q=QUERY"
```

### 7.2 curl tidak ada output
**Kemungkinan penyebab:**
- URL salah / 404
- Server memblokir bot
- Perlu redirect (`-L` flag)
- Perlu custom headers (`-H` flag)

**Debug:**
```bash
curl -v "URL" 2>&1 | head -30    # Verbose mode untuk debug
```

### 7.3 lynx/w3m tidak ditemukan
**Solusi:**
```bash
pkg install -y lynx w3m
```

### 7.4 Permission denied saat write file
**Penyebab:** Mencoba write ke direktori yang tidak diizinkan (misal `/tmp`)
**Solusi:** Selalu write ke direktori kerja agent (cek dengan `pwd`)

### 7.5 Python urllib error
**Kemungkinan:**
- `URLError` — URL salah atau tidak ada koneksi
- `HTTPError` — Server mengembalikan error (403, 404, 500)
- `TimeoutError` — Koneksi timeout

**Debug:**
```python
try:
    # request code
except Exception as e:
    print(f'Error type: {type(e).__name__}')
    print(f'Error msg: {e}')
```

---

## 8. Cheat Sheet

### Quick Commands

```bash
# === SEARCH (DuckDuckGo) ===
lynx -dump "https://html.duckduckgo.com/html/?q=QUERY" 2>&1 | head -80

# === EXCHANGE RATE ===
curl -s "https://api.exchangerate-api.com/v4/latest/USD" | python3 -c "import sys,json; d=json.load(sys.stdin); print('IDR:', d['rates']['IDR'])"

curl -s "https://wise.com/rates/live?source=USD&target=IDR" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Rate:', d['value'])"

# === INSTALL TOOLS ===
pkg install -y lynx w3m which curl

# === CHECK TOOLS ===
which lynx w3m curl python3

# === PYTHON HTTP REQUEST ===
python3 -c "
import urllib.request, json
req = urllib.request.Request('URL', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    print(r.read().decode('utf-8')[:2000])
"
```

### Decision Tree: Mau Ambil Data dari Internet?

```
Butuh data dari internet?
│
├─ Butuh hasil pencarian (search)?
│  └─ GUNAKAN DuckDuckGo HTML:
│     lynx -dump "https://html.duckduckgo.com/html/?q=QUERY"
│
├─ Butuh data dari API spesifik?
│  └─ GUNAKAN curl:
│     curl -s "API_ENDPOINT"
│
├─ Butuh scrape halaman spesifik?
│  └─ GUNAKAN python3 + urllib + regex:
│     python3 -c "import urllib.request, re; ..."
│
└─ Mau pakai Google?
   └─ TIDAK BISA. Google memblokir semua text-based tools.
      Langsung pakai DuckDuckGo.
```

---

## 📝 Catatan Session

**Session: temp_2 (11 Juni 2026)**
- Berhasil install: lynx, w3m, which
- Berhasil akses: DuckDuckGo HTML, ExchangeRate-API, Wise API
- Gagal akses: Google Search, Google Finance (dibot detection)
- Walikota Surabaya: Eri Cahyadi, IG: @ericahyadi_ (267K followers)

---

<div align="center">

**🐢 Ruka AI — Browsing Skills v1.0**
*Di-generate berdasarkan percobaan langsung di environment Termux.*
*Update file ini setiap ada penemuan baru.*

</div>
