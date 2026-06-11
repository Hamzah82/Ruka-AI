# 🐢 Ruka AI — PPT Skill Guide

> Panduan internal cara membuat file PPT (.pptx) menggunakan Python.
> File ini ditujukan untuk DIBACA ULANG oleh Ruka AI di masa depan
> ketika diminta membuat PPT. JANGAN HAPUS file ini.
> Bahasa: teknis, detail, dan mudah difahami oleh AI.

---

## 📋 Daftar Isi

- [1. Overview](#1-overview)
- [2. Prasyarat & Instalasi](#2-prasyarat--instalasi)
- [3. Cara Menjalankan](#3-cara-menjalankan)
- [4. Struktur Dasar Script PPT](#4-struktur-dasar-script-ppt)
- [5. Konstanta & Konfigurasi](#5-konstanta--konfigurasi)
- [6. Helper Functions (WAJIB PUNYA)](#6-helper-functions-wajib-punya)
- [7. Cara Membuat Setiap Slide](#7-cara-membuat-setiap-slide)
- [8. Warna & Tema](#8-warna--tema)
- [9. Tipografi & Font](#9-tipografi--font)
- [10. Shape & Dekorasi](#10-shape--dekorasi)
- [11. Layout Tips & Best Practices](#11-layout-tips--best-practices)
- [12. Contoh Template Slide](#12-contoh-template-slide)
- [13. Troubleshooting](#13-troubleshooting)
- [14. Catatan Penting](#14-catatan-penting)

---

## 1. Overview

**Apa ini?** Cara membuat file `.pptx` (Microsoft PowerPoint) secara programatik menggunakan Python.

**Library yang dipakai:** `python-pptx`
- Install: `pip install python-pptx`
- Dokumentasi resmi: https://python-pptx.readthedocs.io/
- Library ini sudah TERINSTALL di environment ini (per 2025-06-11)

**Kenapa pakai ini?**
- Tidak perlu install PowerPoint
- Bisa generate file .pptx murni
- Buka di PowerPoint, WPS, LibreOffice, Google Slides (via import)
- Full control atas posisi, warna, font, shape

**File contoh yang sudah pernah dibuat:**
- `workspace/rukaPPT/buat_ppt_ruka.py` — Script lengkap 9 slide tentang pengenalan Ruka AI
- `workspace/rukaPPT/Ruka_AI_Pengenalan.pptx` — Output file PPT

---

## 2. Prasyarat & Instalasi

### Python
```bash
python3 --version
# Harus Python 3.x (3.13.13 di environment ini)
```

### pip
```bash
pip --version
# Harus ada (26.1.2 di environment ini)
```

### Install python-pptx
```bash
pip install python-pptx
```

### Dependencies otomatis terinstall:
- `Pillow >= 3.3.2` — untuk image processing
- `XlsxWriter >= 0.5.7` — untuk dukungan xlsx
- `lxml >= 3.1.0` — untuk XML manipulation
- `typing_extensions >= 4.9.0` — untuk type hints

### Cek apakah sudah terinstall:
```bash
pip show python-pptx
```

---

## 3. Cara Menjalankan

### Langkah-langkah:
1. Buat file Python (contoh: `buat_ppt_saya.py`)
2. Tulis script-nya (lihat contoh di bawah)
3. Jalankan: `python3 buat_ppt_saya.py`
4. Output: file `.pptx` akan muncul di direktori yang sama

### Command:
```bash
python3 nama_script.py
```

### Output yang diharapkan:
```
✅ File PPT berhasil dibuat: Nama_File.pptx
📊 Jumlah slide: X
📐 Ukuran: ..., ...
```

---

## 4. Struktur Dasar Script PPT

Setiap script PPT harus punya struktur ini (urutan penting!):

```python
# ─── STEP 1: Import ───
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ─── STEP 2: Warna tema (konstanta) ───
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)
ACCENT_BLUE = RGBColor(0x00, 0xD2, 0xFF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
# ... (sesuaikan dengan tema)

# ─── STEP 3: Helper functions ───
def dark_bg(slide): ...
def add_shape(slide, left, top, width, height, color, shape_type=...): ...
def add_text_box(slide, left, top, width, height, text, ...): ...
def add_circle(slide, left, top, size, color): ...
def add_bullet_list(slide, left, top, width, height, items, ...): ...

# ─── STEP 4: Buat objek Presentation ───
prs = Presentation()
prs.slide_width = Inches(13.333)   # 16:9 widescreen
prs.slide_height = Inches(7.5)
SLIDE_W = prs.slide_width
SLIDE_H = prs.slide_height

# ─── STEP 5: Buat slide satu per satu ───
slide1 = prs.slides.add_slide(prs.slide_layouts[6])  # 6 = blank layout
dark_bg(slide1)
# ... tambahkan konten slide 1 ...

slide2 = prs.slides.add_slide(prs.slide_layouts[6])
dark_bg(slide2)
# ... tambahkan konten slide 2 ...

# ... (ulangi untuk slide 3, 4, dst ...)

# ─── STEP 6: Simpan ───
output_path = "Nama_File.pptx"
prs.save(output_path)
print(f"✅ File PPT berhasil dibuat: {output_path}")
```

---

## 5. Konstanta & Konfigurasi

### Ukuran Slide (WAJIB SET INI)
```python
prs = Presentation()
prs.slide_width = Inches(13.333)   # 16:9 widescreen
prs.slide_height = Inches(7.5)
```

### Satuan Ukuran
| Satuan | Kegunaan | Contoh |
|--------|----------|--------|
| `Inches(x)` | Ukuran besar (slide, shape, posisi) | `Inches(1.5)` |
| `Pt(x)` | Ukuran font | `Pt(18)` |
| `Emu(x)` | Ukuran presisi tinggi (jarang dipakai langsung) | `Emu(914400)` |

### Layout Slide
```python
prs.slide_layouts[6]  # Blank layout (paling sering dipakai)
```
- Index 0-18 tersedia, tapi **selalu pakai [6]** (blank) untuk full control
- Layout lain punya placeholder yang tidak kita butuhkan

### Warna RGB
```python
# Format: RGBColor(0xRR, 0xGG, 0xBB)
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)       # Navy gelap
ACCENT_BLUE = RGBColor(0x00, 0xD2, 0xFF)    # Cyan
ACCENT_PURPLE = RGBColor(0xA8, 0x5C, 0xFF)  # Ungu
ACCENT_GREEN = RGBColor(0x00, 0xE6, 0x96)   # Hijau mint
ACCENT_ORANGE = RGBColor(0xFF, 0x8C, 0x42)  # Oranye
WHITE = RGBColor(0xFF, 0xFF, 0xFF)          # Putih
LIGHT_GRAY = RGBColor(0xCC, 0xCC, 0xCC)     # Abu terang
YELLOW = RGBColor(0xFF, 0xD7, 0x00)         # Kuning
```

### Alignment
```python
PP_ALIGN.LEFT      # Rata kiri (default)
PP_ALIGN.CENTER    # Rata tengah
PP_ALIGN.RIGHT     # Rata kanan
PP_ALIGN.JUSTIFY   # Rata kiri-kanan
```

---

## 6. Helper Functions (WAJIB PUNYA)

Ini adalah fungsi-fungsi pembantu yang dipakai di SETIAP slide. Simpan di bagian atas script, setelah import dan konstanta.

### 6.1 dark_bg — Background Gelap
```python
def dark_bg(slide):
    """Set background gelap untuk slide.
    Panggil ini PERTAMA kali sebelum menambahkan apapun ke slide."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = DARK_BG   # Ganti dengan warna background pilihanmu
```

### 6.2 add_shape — Tambah Shape/Persegi
```python
def add_shape(slide, left, top, width, height, color, shape_type=MSO_SHAPE.ROUNDED_RECTANGLE):
    """Tambah shape (kotak, rounded rect, dll) dengan warna.
    Return: shape object (bisa untuk set text)."""
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()  # Hilangkan border
    shape.shadow.inherit = False
    return shape
```

### 6.3 add_text_box — Tambah Text Box
```python
def add_text_box(slide, left, top, width, height, text, font_size=18, color=WHITE, bold=False, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    """Tambah text box dengan styling.
    Return: textbox object."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox
```

### 6.4 add_circle — Tambah Lingkaran
```python
def add_circle(slide, left, top, size, color):
    """Tambah lingkaran dengan warna.
    Sering dipakai untuk dekorasi atau penomoran."""
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, top, size, size)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape
```

### 6.5 add_bullet_list — Tambah Bullet List
```python
def add_bullet_list(slide, left, top, width, height, items, font_size=16, color=WHITE, spacing=Pt(8)):
    """Tambah bullet list (daftar poin).
    'items' adalah list of string. String kosong = baris kosong."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = item
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.font.name = "Calibri"
        p.space_after = spacing
        p.level = 0   # Level bullet (0 = level 1)
    return txBox
```

### 6.6 add_icon_text — Teks dengan Emoji/Icon
```python
def add_icon_text(slide, left, top, icon, text, font_size=14, color=WHITE):
    """Tambah teks dengan icon emoji di depannya.
    Contoh: icon='🐢', text='Ruka AI' → '🐢  Ruka AI'"""
    full_text = f"{icon}  {text}"
    txBox = slide.shapes.add_textbox(left, top, Inches(5), Inches(0.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = full_text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.name = "Calibri"
    return txBox
```

---

## 7. Cara Membuat Setiap Slide

### Alur per slide:
```python
# 1. Buat slide baru (selalu pakai layout[6] = blank)
slide = prs.slides.add_slide(prs.slide_layouts[6])

# 2. Set background
dark_bg(slide)

# 3. Tambah dekorasi (lingkaran, garis, shape) — opsional
add_circle(slide, ...)
add_shape(slide, ...)

# 4. Tambah konten (judul, teks, list, card, dll)
add_text_box(slide, ...)
add_bullet_list(slide, ...)

# 5. (Selesai — lanjut ke slide berikutnya)
```

### Template Slide Cover (Judul):
```python
slide1 = prs.slides.add_slide(prs.slide_layouts[6])
dark_bg(slide1)

# Dekorasi lingkaran di background
add_circle(slide1, Inches(-1), Inches(-1), Inches(4), RGBColor(0x16, 0x21, 0x37))

# Garis aksen di kiri
add_shape(slide1, Inches(1.2), Inches(1.5), Inches(0.08), Inches(4.5), ACCENT_BLUE, MSO_SHAPE.RECTANGLE)

# Judul utama (font besar, bold, putih)
add_text_box(slide1, Inches(1.2), Inches(1.8), Inches(10), Inches(1.2),
             "JUDUL PPT", font_size=60, color=WHITE, bold=True)

# Sub judul (font sedang, warna aksen)
add_text_box(slide1, Inches(1.2), Inches(3.0), Inches(10), Inches(0.8),
             "Sub judul deskripsi", font_size=32, color=ACCENT_BLUE, bold=True)

# Deskripsi (font kecil, warna abu)
add_text_box(slide1, Inches(1.2), Inches(3.9), Inches(10), Inches(1),
             "Deskripsi panjang di sini...", font_size=18, color=LIGHT_GRAY)
```

### Template Slide Konten (Judul + List):
```python
slide = prs.slides.add_slide(prs.slide_layouts[6])
dark_bg(slide)

# Header judul slide
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(10), Inches(0.8),
             "Judul Slide  🐢", font_size=40, color=WHITE, bold=True)

# Garis bawah header
add_shape(slide, Inches(0.8), Inches(1.2), Inches(3), Inches(0.05), ACCENT_BLUE, MSO_SHAPE.RECTANGLE)

# Bullet list
items = [
    "Pertama — deskripsi detail",
    "Kedua — deskripsi detail",
    "Ketiga — deskripsi detail",
]
add_bullet_list(slide, Inches(0.8), Inches(1.7), Inches(11), Inches(5), items, font_size=18)
```

### Template Slide Konten (2 Kolom):
```python
slide = prs.slides.add_slide(prs.slide_layouts[6])
dark_bg(slide)

# Header
add_text_box(slide, Inches(0.8), Inches(0.4), Inches(10), Inches(0.8),
             "Judul Slide", font_size=40, color=WHITE, bold=True)
add_shape(slide, Inches(0.8), Inches(1.2), Inches(3), Inches(0.05), ACCENT_BLUE, MSO_SHAPE.RECTANGLE)

# Kolom kiri
add_text_box(slide, Inches(0.8), Inches(1.6), Inches(5.5), Inches(0.6),
             "Kolom Kiri", font_size=24, color=ACCENT_BLUE, bold=True)
add_bullet_list(slide, Inches(0.8), Inches(2.2), Inches(5.5), Inches(4), items_kiri, font_size=16)

# Kolom kanan
add_text_box(slide, Inches(7), Inches(1.6), Inches(5.5), Inches(0.6),
             "Kolom Kanan", font_size=24, color=ACCENT_PURPLE, bold=True)
add_bullet_list(slide, Inches(7), Inches(2.2), Inches(5.5), Inches(4), items_kanan, font_size=16)
```

### Template Slide Card Grid (3x2 atau 2x4):
```python
# Card dengan posisi manual
for i, (title, desc) in enumerate(data):
    col = i % 3          # 3 kolom
    row = i // 3         # baris
    x = Inches(0.8) + col * Inches(4.2)
    y = Inches(1.7) + row * Inches(1.5)

    # Card background
    card = add_shape(slide, x, y, Inches(3.8), Inches(1.2), RGBColor(0x22, 0x22, 0x3A), MSO_SHAPE.ROUNDED_RECTANGLE)

    # Card title
    txBox = slide.shapes.add_textbox(x + Inches(0.2), y + Inches(0.1), Inches(3.4), Inches(0.4))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(16)
    p.font.color.rgb = ACCENT_BLUE
    p.font.bold = True
    p.font.name = "Calibri"

    # Card description
    txBox2 = slide.shapes.add_textbox(x + Inches(0.2), y + Inches(0.55), Inches(3.4), Inches(0.5))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = desc
    p2.font.size = Pt(12)
    p2.font.color.rgb = LIGHT_GRAY
    p2.font.name = "Calibri"
```

---

## 8. Warna & Tema

### Tema Gelap (Dark Theme) — Paling Sering Dipakai
```python
DARK_BG = RGBColor(0x1A, 0x1A, 0x2E)       # Background utama
CARD_BG = RGBColor(0x22, 0x22, 0x3A)       # Background card/box
BORDER_DARK = RGBColor(0x16, 0x21, 0x37)    # Border/dekorasi gelap
ACCENT_BLUE = RGBColor(0x00, 0xD2, 0xFF)    # Aksen utama (cyan)
ACCENT_PURPLE = RGBColor(0xA8, 0x5C, 0xFF)  # Aksen kedua (ungu)
ACCENT_GREEN = RGBColor(0x00, 0xE6, 0x96)   # Aksen sukses (hijau)
ACCENT_ORANGE = RGBColor(0xFF, 0x8C, 0x42)  # Aksen peringatan (oranye)
ACCENT_RED = RGBColor(0xFF, 0x44, 0x44)     # Aksen error (merah)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)          # Teks utama
LIGHT_GRAY = RGBColor(0xCC, 0xCC, 0xCC)     # Teks sekunder
YELLOW = RGBColor(0xFF, 0xD7, 0x00)         # Highlight/kutipan
```

### Aturan Warna:
- **Background:** Selalu gelap (DARK_BG atau CARD_BG)
- **Teks utama:** Putih (WHITE)
- **Teks sek Abu (LIGHT_GRAY)
- **Judul/Header:** Warna aksen (ACCENT_BLUE atau ACCENT_PURPLE)
- **Card/Box:** CARD_BG (lebih terang dari background sedikit)
- **Dekorasi lingkaran:** BORDER_DARK (gelap, hampir menyatu dengan bg)
- **Kutipan:** YELLOW (kuning)
- **Sukses/positif:** ACCENT_GREEN
- **Peringatan:** ACCENT_ORANGE
- **Error/berbahaya:** ACCENT_RED

---

## 9. Tipografi & Font

### Font yang Dipakai:
| Font | Kegunaan |
|------|----------|
| `Calibri` | Teks umum, deskripsi, body text |
| `Consolas` | Nama function/tech (monospace) |
| `Arial` | Alternatif judul |

### Ukuran Font Standar:
| Elemen | Ukuran | Bold? |
|--------|--------|-------|
| Judul slide (header) | Pt(36-40) | Ya |
| Judul cover | Pt(54-60) | Ya |
| Sub judul cover | Pt(28-32) | Ya |
| Card title | Pt(16-18) | Ya |
| Body text | Pt(14-16) | Tidak |
| Deskripsi kecil | Pt(12-14) | Tidak |
| Footer/copyright | Pt(10-12) | Tidak |
| Tag/label | Pt(12) | Tidak |

### Spacing:
```python
p.space_after = Pt(8)    # Jarak setelah paragraf
p.space_before = Pt(4)   # Jarak sebelum paragraf
p.level = 0              # Level bullet (0 = level 1, 1 = sub-bullet)
```

---

## 10. Shape & Dekorasi

### Shape Types yang Sering Dipakai:
```python
MSO_SHAPE.RECTANGLE           # Persegi panjang
MSO_SHAPE.ROUNDED_RECTANGLE   # Persegi rounded (paling sering dipakai untuk card)
MSO_SHAPE.OVAL                # Lingkaran / oval
MSO_SHAPE.DOWN_ARROW          # Panah bawah
MSO_SHAPE.UP_ARROW            # Panah atas
```

### Dekorasi yang Sering Dipakai:

**1. Lingkaran Background (dekorasi):**
```python
# Lingkaran besar di pojok, warna hampir sama dengan bg
add_circle(slide, Inches(-1), Inches(-1), Inches(4), RGBColor(0x16, 0x21, 0x37))
```

**2. Garis Aksen (di bawah header):**
```python
add_shape(slide, Inches(0.8), Inches(1.2), Inches(3), Inches(0.05), ACCENT_BLUE, MSO_SHAPE.RECTANGLE)
```

**3. Left Bar (garis berwarna di kiri card):**
```python
left_bar = add_shape(slide, Inches(2), y_pos, Inches(0.08), Inches(0.75), color, MSO_SHAPE.RECTANGLE)
```

**4. Card dengan Rounded Rectangle:**
```python
card = add_shape(slide, x, y, Inches(3.8), Inches(1.2), RGBColor(0x22, 0x22, 0x3A), MSO_SHAPE.ROUNDED_RECTANGLE)
```

---

## 11. Layout Tips & Best Practices

### ✅ DO:
1. **Selalu pakai `prs.slide_layouts[6]`** (blank layout) — full control
2. **Selalu panggil `dark_bg(slide)` pertama kali** sebelum tambah apapun
3. **Pakai helper functions** — jangan tulis ulang kode yang sama
4. **Konsisten dengan warna** — pakai konstanta RGB, jangan hardcode warna berbeda
5. **Konsisten dengan spacing** — jarak antar elemen harus rata
6. **Pakai `tf.word_wrap = True`** — teks panjang akan wrap otomatis
7. **Font size jangan terlalu kecil** — minimum Pt(12) untuk keterbacaan
8. **Judul slide selalu di posisi yang sama** — Inches(0.8), Inches(0.4)
9. **Garis aksen di bawah header** — konsisten di semua slide
10. **Test dulu** — jalankan script dan cek outputnya

### ❌ DON'T:
1. **Jangan pakai tabel markdown** — tidak terformat di PPT
2. **Jangan campur terlalu banyak warna** — maksimal 3-4 warna per slide
3. **Jangan terlalu banyak teks per slide** — maksimal 6-8 poin
4. **Jangan lupa `fill.solid()`** — tanpa ini, shape tidak terisi warna
5. **Jangan lupa `shape.line.fill.background()`** — tanpa ini, shape punya border hitam
6. **Jangan pakai font yang tidak umum** — stick to Calibri, Arial, Consolas

### 📐 Panduan Posisi:
| Elemen | Left | Top | Width | Height |
|--------|------|-----|-------|--------|
| Header judul | Inches(0.8) | Inches(0.4) | Inches(10) | Inches(0.8) |
| Garis aksen | Inches(0.8) | Inches(1.2) | Inches(3) | Inches(0.05) |
| Konten full | Inches(0.8) | Inches(1.7) | Inches(11.5) | Inches(5) |
| Kolom kiri | Inches(0.8) | Inches(1.6) | Inches(5.5) | Inches(5) |
| Kolom kanan | Inches(7) | Inches(1.6) | Inches(5.5) | Inches(5) |
| Card (3 kolom) | Inches(0.8) + col*4.2 | Inches(1.7) + row*1.5 | Inches(3.8) | Inches(1.2) |
| Footer | Inches(0.8) | Inches(6.5) | Inches(11.5) | Inches(0.5) |

---

## 12. Contoh Template Slide

### Slide Quote/Kutipan:
```python
slide = prs.slides.add_slide(prs.slide_layouts[6])
dark_bg(slide)

quote_shape = add_shape(slide, Inches(2), Inches(2.5), Inches(9), Inches(1.5), RGBColor(0x22, 0x22, 0x3A), MSO_SHAPE.ROUNDED_RECTANGLE)
tf = quote_shape.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = '"Teks kutipan di sini"'
p.font.size = Pt(20)
p.font.color.rgb = YELLOW
p.font.italic = True
p.font.name = "Calibri"
p.alignment = PP_ALIGN.CENTER
```

### Slide Penutup:
```python
slide = prs.slides.add_slide(prs.slide_layouts[6])
dark_bg(slide)

# Dekorasi
add_circle(slide, Inches(8), Inches(-2), Inches(6), RGBColor(0x16, 0x21, 0x37))

# Judul besar tengah
add_text_box(slide, Inches(0.8), Inches(1.5), Inches(11.5), Inches(1),
             "Terima Kasih!  🐢", font_size=54, color=WHITE, bold=True, alignment=PP_ALIGN.CENTER)

# Sub
add_text_box(slide, Inches(0.8), Inches(2.5), Inches(11.5), Inches(0.8),
             "Sub judul penutup", font_size=24, color=ACCENT_BLUE, alignment=PP_ALIGN.CENTER)

# Link
add_text_box(slide, Inches(0.8), Inches(3.8), Inches(11.5), Inches(0.5),
             "📂 GitHub: github.com/user/repo", font_size=18, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

# Footer
add_text_box(slide, Inches(0.8), Inches(6.5), Inches(11.5), Inches(0.5),
             "© 2025 Nama", font_size=12, color=RGBColor(0x66, 0x66, 0x66), alignment=PP_ALIGN.CENTER)
```

### Slide dengan Flow/Diagram:
```python
# Flow step-by-step dengan kotak + panah
steps = [
    ("Judul Step", "Deskripsi step", WARNAR),
    ("Judul Step 2", "Deskripsi step 2", WARNA2),
]

y_pos = Inches(1.7)
for i, (title, desc, color) in enumerate(steps):
    # Kotak
    box = add_shape(slide, Inches(2), y_pos, Inches(9), Inches(0.75), RGBColor(0x22, 0x22, 0x3A), MSO_SHAPE.ROUNDED_RECTANGLE)
    # Left bar
    add_shape(slide, Inches(2), y_pos, Inches(0.08), Inches(0.75), color, MSO_SHAPE.RECTANGLE)
    # Title
    txBox = slide.shapes.add_textbox(Inches(2.3), y_pos + Inches(0.05), Inches(8), Inches(0.35))
    # ... (set text, font, color)
    # Desc
    txBox2 = slide.shapes.add_textbox(Inches(2.3), y_pos + Inches(0.4), Inches(8), Inches(0.35))
    # ... (set text, font, color)

    # Panah (kecuali step terakhir)
    if i < len(steps) - 1:
        arrow = add_shape(slide, Inches(6.3), y_pos + Inches(0.75), Inches(0.5), Inches(0.15), RGBColor(0x44, 0x44, 0x6A), MSO_SHAPE.DOWN_ARROW)

    y_pos += Inches(0.9)
```

---

## 13. Troubleshooting

### Error: `ModuleNotFoundError: No module named 'pptx'`
**Solusi:** `pip install python-pptx`

### Error: `ImportError: cannot import name '...'`
**Solusi:** Cek nama import, pastikan sesuai:
- `from pptx import Presentation`
- `from pptx.util import Inches, Pt, Emu`
- `from pptx.dml.color import RGBColor`
- `from pptx.enum.text import PP_ALIGN, MSO_ANCHOR`
- `from pptx.enum.shapes import MSO_SHAPE`

### Shape tidak terlihat:
- Pastikan `fill.solid()` sudah dipanggil
- Pastikan warna bukan sama dengan background
- Cek posisi — mungkin di luar area slide

### Teks terpotong:
- Tambah `tf.word_wrap = True` pada text frame
- Perbesar height text box
- Kurangi font size

### Font tidak berubah:
- Pastikan `p.font.name = "Calibri"` (atau font yang diinginkan)
- Font harus terinstall di sistem (Calibri biasanya ada)

### Posisi tidak tepat:
- Slide width default: 10 inches, height: 7.5 inches
- Kalau set `prs.slide_width = Inches(13.333)`, semua posisi harus disesuaikan
- 1 inch = 914400 EMU

---

## 14. Catatan Penting

### 🔑 WAJIB INGAT:
1. **Library:** `python-pptx` — bukan `py-pptx`, bukan `pptx`
2. **Install:** `pip install python-pptx`
3. **Import:** `from pptx import Presentation`
4. **Layout:** Selalu pakai `prs.slide_layouts[6]` (blank)
5. **Background:** Panggil `dark_bg(slide)` PERTAMA sebelum tambah elemen
6. **Shape fill:** Selalu `shape.fill.solid()` + `shape.fill.fore_color.rgb = warna`
7. **Shape border:** `shape.line.fill.background()` untuk hilangkan border
8. **Text wrap:** `tf.word_wrap = True` untuk teks panjang
9. **Satuan:** `Inches()` untuk posisi/ukuran, `Pt()` untuk font size
10. **Simpan:** `prs.save("nama_file.pptx")` di baris terakhir

### 📁 File Referensi:
- Script contoh lengkap: `workspace/rukaPPT/buat_ppt_ruka.py`
- Output contoh: `workspace/rukaPPT/Ruka_AI_Pengenalan.pptx`

### 🔄 Cara Pakai Ulang:
1. Baca file ini dulu
2. Copy helper functions
3. Ganti warna tema jika perlu
4. Buat slide satu per satu
5. Jalankan script
6. File .pptx jadi

---

<div align="center">

**🐢 Ruka AI — PPT Skill Guide v1.0**

*Dokumentasi ini menjelaskan cara membuat file PPT menggunakan Python.*
*Di-generate berdasarkan pengalaman pembuatan Ruka_AI_Pengenalan.pptx.*

</div>
