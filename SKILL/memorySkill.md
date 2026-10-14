# Memory Skill — Catatan Lintas-Sesi

> Panduan untuk Ruka AI dalam menggunakan sistem **memory / catatan lintas-sesi**.
> Baca skill ini saat: user minta mencatat hal penting, saat perlu mengingat
> preferensi/keputusan dari sesi lain, atau saat butuh menyimpan pengetahuan
> yang berguna di masa depan.

---

## 1. Apa Itu Memory?

**Memory** = catatan PERSISTEN yang bertahan **lintas sesi** (bukan hanya di sesi
berjalan). Berbeda dari `sessions/` (riwayat chat per-sesi), memory bisa dibaca
dari sesi mana pun — jadi kamu bisa "mengingat" hal penting di masa mendatang.

**Lokasi:** `data/memory/` (di folder instalasi, di-ignore git)

**Struktur:**
```
data/memory/
├── index.json          ← index: daftar catatan + keterangannya
├── preferensi-user.md  ← catatan (satu materi = satu file)
└── ...
```

---

## 2. Kapan Menggunakan Memory?

**GUNAKAN memory untuk hal yang berguna jangka panjang:**
- Preferensi user (gaya bahasa, teknologi favorit, cara kerja)
- Keputusan teknis penting (arsitektur, library, konfigurasi)
- Info proyek (nama, struktur, tujuan)
- Alur kerja / SOP yang berulang
- Hal yang user minta "ingat ini"

**JANGAN gunakan memory untuk:**
- Info sementara / sekali pakai
- Data sensitif (API key, password) — JANGAN pernah disimpan
- Hal yang sudah jelas dari konteks workspace

---

## 3. Tool Memory

| Tool | Fungsi |
|---|---|
| `memory_list` | Daftar semua catatan + keterangan |
| `memory_read` | Baca isi lengkap satu catatan |
| `memory_write` | Buat/perbarui catatan |
| `memory_search` | Cari catatan berdasar keyword |
| `memory_delete` | Hapus catatan |

---

## 3b. Auto-Inject: Daftar Catatan Selalu Terlihat

**PENTING:** Daftar catatan (slug + keterangan) otomatis disisipkan ke
system prompt-mu di antara marker `<!--MEMORY_START-->` … `<!--MEMORY_END-->`.

Artinya:
- Kamu **SELALU melihat daftar catatan yang tersimpan** tanpa perlu memanggil
  `memory_list` lebih dulu.
- Saat kamu menulis/menghapus catatan (`memory_write`/`memory_delete`), daftar
  itu **di-refresh otomatis** di akhir giliran — jadi selalu ter-update.
- Untuk **isi lengkap** sebuah catatan, tetap panggil `memory_read <nama>`
  (membaca file `.md` dari disk, selalu fresh).
- Untuk pencarian mendalam, pakai `memory_search <kw>`.

Jadi alurnya:
```
Kamu lihat daftar catatan di system prompt (otomatis)
   → jika salah satu relevan, panggil memory_read <nama> untuk isi lengkap
   → jika butuh cari, panggil memory_search <kw>
   → jika mencatat hal baru, panggil memory_write (daftar auto-refresh)
```

> SEMUA catatan ditampilkan di prompt (tanpa batas) — karena hanya slug +
> keterangan singkat, sangat hemat token (~13 token per catatan).

---

## 4. Alur Kerja yang Benar

### Di AWAL sesi
```
Daftar catatan sudah OTOMATIS ada di system prompt — tak perlu memory_list.
Jika ada yang relevan → memory_read <nama> untuk isi lengkap.
```

### Saat menemukan hal penting untuk dicatat
```
1. memory_search <keyword>  → cek apakah sudah ada catatan serupa
2. Jika ada  → memory_write (mode='append') untuk menambah
   Jika belum → memory_write (mode='replace') untuk buat baru
```

### Prinsip: SATU MATERI = SATU CATATAN
Jangan gabung banyak topik dalam satu catatan. Pisahkan per materi:
- `preferensi-user` — preferensi & gaya user
- `proyek-ruka` — info proyek Ruka AI
- `konfigurasi-server` — detail konfigurasi server

---

## 5. Contoh Penggunaan

### Contoh 1: Mencatat preferensi user
```json
{
  "name": "memory_write",
  "arguments": {
    "name": "preferensi-user",
    "description": "Preferensi user: gaya jawaban, bahasa, format kode",
    "content": "# Preferensi User\n\n- Bahasa: Indonesia santai\n- Gaya jawaban: ringkas + bullet\n- Kode: selalu pakai komentar",
    "tags": ["preferensi", "gaya"]
  }
}
```

### Contoh 2: Menambah info ke catatan yang ada
```json
{
  "name": "memory_write",
  "arguments": {
    "name": "proyek-ruka",
    "description": "Info tentang proyek Ruka AI",
    "content": "\n## Update\n- Ditambahkan fitur memory lintas-sesi",
    "mode": "append"
  }
}
```

### Contoh 3: Mencari catatan relevan
```json
{"name": "memory_search", "arguments": {"query": "preferensi"}}
```

### Contoh 4: Membaca catatan
```json
{"name": "memory_read", "arguments": {"name": "preferensi-user"}}
```

---

## 6. Aturan Penting

1. **`description` WAJIB** — keterangan singkat untuk apa catatan ini. Ini yang
   membuat catatan mudah ditemukan (muncul di `memory_list` & `memory_search`).
2. **Nama = slug** — huruf kecil, tanda hubung (mis. `preferensi-user`).
3. **Satu materi satu file** — jangan campur topik.
4. **Update, jangan duplikat** — kalau catatan sudah ada, pakai `mode='append'`.
5. **JANGAN simpan data sensitif** (API key, password, token).
6. **Konfirmasi ke user** setelah mencatat hal penting.

---

## 7. Kapan PROAKTIF Mencatat?

Catat secara proaktif (tanpa diminta) saat:
- User menyatakan preferensi ("aku suka...", "jangan pakai...")
- Ada keputusan teknis penting yang disepakati
- User menjelaskan konteks proyek yang berguna jangka panjang
- Ada alur kerja yang kemungkinan diulang

Tapi JANGAN mencatat hal sepele — biar catatan tetap relevan & mudah dicari.
