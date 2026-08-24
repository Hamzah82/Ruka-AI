# 🚀 Optimisasi Token untuk Ruka AI

## Ringkasan Perubahan

Dokumentasi ini menjelaskan optimisasi yang dilakukan untuk mengurangi konsumsi token pada project Ruka AI.

---

## 📊 Hasil Penghematan

### 1. **skills.md — Ringkas 76% Lebih Kecil**

- **Sebelum:** 60,384 bytes (1,474 baris)
- **Sesudah:** 13,903 bytes (368 baris)  
- **Penghematan:** 46,481 bytes = **76%**
- Backup asli tersedia di `SKILL/skills.md.backup`

### 2. **Auto-Load Skill (Lazy Loading)**

Fitur baru yang hanya memuat skill spesialis saat benar-benar dibutuhkan, bukan di-load ke system prompt setiap round.

**Skill yang tersedia untuk auto-load:**
| Skill | File Size | Trigger Keywords |
|-------|-----------|------------------|
| PPT Creation | 22 KB | ppt, powerpoint, presentasi, slide, .pptx |
| Web Browsing | 19 KB | cari info, browse, search online, web scraping, berita, kurs |
| Vercel Deploy | 21 KB | vercel, deploy ke vercel, konfigurasi vercel |
| Email Setup | 25 KB | kirim email, send email, setup email, msmtp |
| Frontend Design | 39 KB | website, landing page, ui, frontend, web design |

---

## 🔧 Cara Kerja Auto-Load Skill

### Flow:
1. User input: `"Buatkan PPT tentang AI"`
2. System deteksi keyword → load `SKILL/pptSkill.md`
3. Inject skill sebagai temporary system message:
   ```python
   messages.insert(1, {
       "role": "system",
       "content": "\n\n🔧 CONTEXT ADDITION — TASK-SPECIFIC SKILL LOADED:\n" +
                  "Ikuti panduan dari skill berikut untuk menyelesaikan tugas ini.\n---\n" +
                  skill_content
   })
   ```
4. Agentic loop berjalan dengan konteks skill
5. **Cleanup**: Skill message dihapus sebelum save ke session (tidak bocor ke task berikutnya)

### Keuntungan:
- ✅ **Hemat token** — skill tidak termuat di setiap round conversation
- ✅ **Caching** — file hanya dibaca sekali, disimpan di `_SKILL_CACHE`
- ✅ **Task-specific** — hanya skill relevan yang dimuat untuk task tertentu
- ✅ **Tidak bocor** — setelah giliran selesai, skill message dihapus dari `messages`

---

## 📁 Struktur File

```
SKILL/
├── skills.md              ← VERSI RINGKAS (13.9 KB, 76% lebih kecil)
├── skills.md.backup       ← Backup versi asli (60.4 KB)
├── pptSkill.md            (lazy-load: 22.5 KB)
├── browsingSkill.md       (lazy-load: 19.1 KB)
├── vercelSkill.md         (lazy-load: 21.7 KB)
├── emailSkill.md          (lazy-load: 24.6 KB)
└── frontendDesignSkill.md (lazy-load: 38.7 KB)
```

Total direktori: ~290 KB (termasuk backup)

---

## 🎯 Estimasi Penghematan Token

### Per Round Conversation (tanpa skill trigger):
- **Sebelum:** ~1,500 tokens (system prompt + full skills.md)
- **Sesudah:** ~350 tokens (system prompt + ringkas skills.md)  
- **Hemat:** ~1,150 tokens per round = **76%**

### Per Round dengan Skill Trigger (misalnya create PPT):
- **Sebelum:** ~1,500 tokens (full skills.md) + ~22K chars (~5.5K tokens) jika agent perlu baca file manual
- **Sesudah:** ~350 tokens (ringkas) + auto-load skill (sekitar 5.5K tokens HANYA untuk task yang relevan)
- **Net benefit:** Skill content tetap sama tapi **tidak di-cache** di session file (cleanup otomatis)

### Contoh Skenario Real:

#### Scenario A: Chat sederhana ("Apa kabar?")
- Token reduction: **76%** (hanya ringkas skills.md yang dikirim)

#### Scenario B: Create PPT
- Token per round: ~350 (ringkas) + 5,500 (auto-load skill) = 5,850 tokens
- Session storage: TIDAK BOCEK karena cleanup
- Total saved vs sebelumnya: skill content hanya dipakai untuk relevant tasks

#### Scenario C: Multiple conversations tanpa trigger skill
- Hemat signifikan karena setiap round mengirim 350bukan 1,500 tokens

---

## 🚦 Cara Menggunakan

### Normal Chat (no skill loading):
```
User: "Apa maksudnya terminal?"
→ Hanya ringkas skills.md yang digunakan (tidak ada extra skill load)
```

### Task Spesial (auto-load triggered):
```
User: "Buatkan presentasi PPT tentang machine learning"
→ Deteksi "ppt" → load pptSkill.md secara otomatis
→ Agent ikuti panduan di pptSkill.md untuk membuat script PPT
```

Manual Load (jika mau override auto-load):
```
User: "Baca dulu SKILL/pptSkill.md, lalu buat PPT"
→ Agent akan read_file() skill tersebut sesuai instruksi user
```

---

## ⚠️ Catatan Penting

1. **Skill content TIDAK tersimpan permanen** — selalu di-cleanup setelah giliran selesai
2. **Cache global** — `_SKILL_CACHE` menyimpan hasil load_file agar tidak baca berulang kali dalam satu sesi
3. **Regex detection** — pattern matching cukup spesifik untuk menghindari false positive (misal: "email" sebagai kata sehari-hari tidak trigger skill)
4. **Backup aman** — original `skills.md` masih ada di `.backup`, bisa restore kapan saja

---

## 🔄 Restore Original

Jika ingin kembali ke versi lengkap:
```bash
cd /data/data/com.termux/files/home/RukaAI
mv SKILL/skills.md SKILL/skills.md.new
mv SKILL/skills.md.backup SKILL/skills.md
```

---

## 📈 Next Steps / Future Optimizations (Done ✓)

### ✅ Poin 1: Optimasi Konfigurasi (config.py)
Sudah dilakukan pada `config.py`:
| Parameter | Sebelum | Sesudah | Hemat |
|-----------|---------|---------|-------|
| `MAX_READ_LINES` | 20,000 | 5,000 | **75%** |
| `MAX_READ_CHARS` | 1,000,000 | 250,000 | **75%** |
| `MAX_EXEC_OUTPUT_CHARS` | 200,000 | 80,000 | **60%** |
| `MAX_HISTORY_TOKENS` | 800,000 | 400,000 | **50%** |
| `KEEP_RECENT_MESSAGES` | 1,000,000 | 500,000 | **50%** |
| `TRUNCATION_THRESHOLD` | — | 4,000 (baru) | File besar dibaca ringkas |

### ✅ Poin 2: Implementasi Summarization (main.py)
Fitur baru untuk meringkas riwayat lama secara cerdas:
- **`ENABLE_SUMMARIZATION = True`** → aktifkan ringkasan LLM
- **`SUMMARIZE_TRIGGER_RATIO = 0.7`** → mulai ringkas saat riwayat ≥70% dari batas
- **`SUMMARIZE_CHUNK_SIZE = 80`** → pesan per chunk yang diringkas
- **`SUMMARIZE_MAX_CHARS = 6_000`** → panjang maks ringkasan per chunk
- **`SUMMARIZE_MODEL = None`** → pakai model yang sama (bisa ganti model murah)
- **`SUMMARIZE_TEMPERATURE = 0.2`** → deterministik untuk ringkasan
- **`SUMMARIZE_MAX_TOKENS = 2_000`** → token maks output ringkasan per call
- **`ESTIMATE_CHARS_PER_TOKEN = 4`** → rasio estimasi token
- Anti-rekursi guard (`_summarize_and_trim._in_progress`) mencegah infinite loop
- Fallback ke hard-trim jika summarization gagal (API error)

### Cara Kerja Summarization (dengan loop):
```
_trim_history() dipanggil
        │
        ▼
┌─ while True: ──────────────────────────┐
│  estimasi token ≤ max_tokens? → return │
│        │ (tidak)                       │
│        ▼                               │
│  ENABLE_SUMMARIZATION &&               │
│  ratio ≥ 0.7?                          │
│     │ YA                               │
│     ▼                                  │
│  _summarize_and_trim() → ringkas 1     │
│  segmen tertua jadi 1 pesan ringkasan  │
│     │ (masih > max_tokens)             │
│     └── loop lagi ──────────────────── │
│        │ TIDAK                          │
│        ▼                               │
│  Hard-trim deterministik               │
│  (buang segmen tertua mentah)          │
└────────────────────────────────────────┘
```

**Keunggulan summarization vs hard-trim:**
- Summarization **mempertahankan konteks** (segmen lama jadi ringkasan, bukan hilang)
- Hard-trim hanya **membuang** segmen tertua
- Kombinasi keduanya: ringkas dulu (hemat konteks), lalu hard-trim jika masih over
     │          (buang segmen teetua mentah)
     ▼
1. Ambil 1 segmen tertua (round percakapan pertama)
2. Kirim ke LLM untuk diringkas (tanpa tools, hemat token)
3. Ganti segmen tersebut dengan ringkasan 1 pesan
4. Cleanup orphan tools
5. Jika gagal → fallback ke hard-trim
```

---

*Dokumen dibuat oleh tim optimisasi Ruka AI*
*Date: 2025-01-*
