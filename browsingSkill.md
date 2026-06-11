# 🐢 Ruka AI — Browsing & Web Scraping Skill

> Dokumentasi lengkap kemampuan browsing dan web scraping Ruka AI.
> File ini adalah "otak browsing" yang berisi tools, pattern, API endpoints,
> dan troubleshooting untuk mengakses informasi dari internet.

---

## 📋 Daftar Isi

- [1. Prinsip Utama](#1-prinsip-utama)
- [2. Tools untuk Browsing](#2-tools-untuk-browsing)
- [3. Search Engine](#3-search-engine)
- [4. Pattern Scraping yang Teruji](#4-pattern-scraping-yang-teruji)
- [5. API Endpoints yang Berguna](#5-api-endpoints-yang-berguna)
- [6. Contoh Alur Browsing](#6-contoh-alur-browsing)
- [7. Troubleshooting](#7-troubleshooting)
- [8. Catatan & Penemuan Baru](#8-catatan--penemuan-baru)

---

## 1. Prinsip Utama

Ketika user meminta informasi dari internet (search, kurs, data online, dll), **WAJIB** membaca file ini terlebih dahulu di awal session atau sebelum melakukan operasi browsing.

**⚠️ Aturan wajib:**
- JANGAN mencoba mengakses Google — Google memblokir semua text-based browser
- GUNAKAN DuckDuckGo HTML sebagai search engine utama
- BACA file ini dulu sebelum browsing, terutama di session baru
- Update file ini setiap ada penemuan baru (API baru, pattern baru, tools baru)

---

## 2. Tools untuk Browsing

Tools berikut perlu diinstall jika belum tersedia (`pkg install -y lynx w3m which`):

- `lynx` — Text-based web browser, bisa dump halaman HTML sebagai teks
- `w3m` — Text-based web browser alternatif
- `curl` — HTTP requests dari terminal (biasanya sudah terinstall)
- `python3` — HTTP requests via `urllib`, parsing HTML dengan regex

---

## 3. Search Engine

**Yang BISA diakses:**
- **DuckDuckGo HTML** — `https://html.duckduckgo.com/html/?q=QUERY` ✅

**Yang DIBLOKIR (jangan coba):**
- **Google** — Memblokir semua text-based browser ❌
- **Bing** — Sering memblokir ❌
- **Yahoo** — Sering memblokir ❌

---

## 4. Pattern Scraping yang Teruji

### DuckDuckGo + lynx (REKOMENDASI UTAMA)
```bash
lynx -dump "https://html.duckduckgo.com/html/?q=QUERY" 2>&1 | head -100
```
Pattern ini sudah teruji berhasil dan menghasilkan hasil pencarian yang lengkap.

### curl untuk API JSON
```bash
curl -s "API_ENDPOINT" 2>&1
```

### curl untuk halaman web
```bash
curl -s "URL" 2>&1 | head -200
```

### python3 untuk parsing HTML
```bash
python3 -c "
import urllib.request, re
url = 'URL'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req).read().decode('utf-8')
# Parse dengan regex
results = re.findall(r'PATTERN', html)
for r in results[:10]:
    print(r)
"
```

---

## 5. API Endpoints yang Berguna

### Exchange Rate
```
https://api.exchangerate-api.com/v4/latest/USD
```

### Cuaca / Weather
```
https://wttr.in/Jakarta?format=j1
```

### IP Info
```
https://ipapi.co/json
```

### Wikipedia API
```
https://en.wikipedia.org/api/rest_v1/page/summary/TOPIC
```

---

## 6. Contoh Alur Browsing

### Search sederhana
```
User: "Carikan info X di internet"

Round 1: read_file("browsingSkill.md") → baca panduan browsing
Round 2: exec_command("lynx -dump 'https://html.duckduckgo.com/html/?q=X'") → search
Round 3: Analisis hasil → tampilkan ke user
```

### Scrape halaman spesifik
```
Round 1: read_file("browsingSkill.md") → baca panduan browsing
Round 2: exec_command("lynx -dump 'URL_SPESIFIK'") → ambil halaman
Round 3: Parse hasil → extract info yang relevan → tampilkan ke user
```

### Ambil data API
```
Round 1: read_file("browsingSkill.md") → baca panduan browsing
Round 2: exec_command("curl -s 'API_ENDPOINT'") → ambil data JSON
Round 3: Parse JSON → tampilkan ke user
```

---

## 7. Troubleshooting

**Masalah: lynx tidak terinstall**
```bash
pkg install -y lynx
```

**Masalah: w3m tidak terinstall**
```bash
pkg install -y w3m
```

**Masalah: Google memblokir request**
- Jangan gunakan Google, gunakan DuckDuckGo

**Masalah: Halaman kosong atau error**
- Coba tambahkan `| head -100` untuk membatasi output
- Coba gunakan `curl` sebagai alternatif `lynx`

**Masalah: Output terlalu panjang**
- Gunakan `| head -N` atau `| grep -i "keyword"` untuk filter

---

## 8. Catatan & Penemuan Baru

File ini adalah file memori persisten untuk kemampuan browsing. Update file ini setiap ada penemuan baru (API baru, pattern baru, tools baru). File ini berfungsi sebagai "otak browsing" yang bertahan meski session tertutup.

**Format catatan baru:**
```
### [Tanggal] - [Judul Penemuan]
[Deskripsi detail]
```

---

<div align="center">

**🐢 Ruka AI — Browsing Skill v1.0**

*Dokumentasi ini adalah memori persisten kemampuan browsing Ruka AI.*
*Update setiap ada penemuan baru.*

</div>
