# 🐢 Ruka AI — Frontend Design Skill Guide

> Panduan lengkap merancang UI yang clean, profesional, dan punya identitas visual unik.
> Bukan template generik, bukan "AI-generated look" — tapi desain yang memiliki karakter.
> File ini berfungsi sebagai MEMORI PERSISTEN — baca setiap kali user minta buat UI/frontend.

---

## 📋 Daftar Isi

- [1. Filosofi Desain](#1-filosofi-desain)
- [2. Anti-Pattern: Hindari "Tampilan AI"](#2-anti-pattern-hindari-tampilan-ai)
- [3. Proses Kerja](#3-proses-kerja)
- [4. Sistem Token Desain](#4-sistem-token-desain)
- [5. Tipografi](#5-tipografi)
- [6. Layout & Struktur](#6-layout--struktur)
- [7. Double UI: Mobile & Desktop](#7-double-ui-mobile--desktop)
- [8. Motion & Interaksi](#8-motion--interaksi)
- [9. Penulisan Konten (Copy)](#9-penulisan-konten-copy)
- [10. Template HTML Siap Pakai](#10-template-html-siap-pakai)
- [11. Cheat Sheet](#11-cheat-sheet)

---

## 1. Filosofi Desain

**Identitas dulu, estetika kemudian.** Setiap project punya dunia sendiri — materialnya, audiensnya, satu tujuan utama halaman itu. Desain yang bagus lahir dari sana, bukan dari template.

**Tiga pertanyaan sebelum menulis satu baris CSS:**

- Apa *satu hal* yang paling khas dari subject ini?
- Siapa yang akan melihat ini, dan apa yang mereka butuhkan?
- Apa satu keputusan berani yang bisa membuat halaman ini tidak terlupakan?

**Gunakan keberanian di satu tempat.** Jadikan satu elemen sebagai "signature" — hal yang paling diingat. Semuanya di sekitarnya harus tenang dan terdisiplin. Satu aksen kuat lebih berkesan dari sepuluh dekorasi.

**Kompleksitas harus sesuai visi.** Desain minimalis butuh presisi dalam spacing dan tipografi. Desain maximalist butuh eksekusi yang elaboratif. Keduanya valid — yang tidak valid adalah setengah-setengah.

---

## 2. Anti-Pattern: Hindari "Tampilan AI"

Tiga tampilan generik yang harus dihindari kecuali brief secara eksplisit memintanya:

**Tampilan #1 — "Warm Minimal":**
- Background krem hangat (#F4F1EA)
- Display serif kontras tinggi
- Aksen terracotta atau sage
- *Kapan boleh:* hanya jika subject memang tentang buku, kopi, atau artisan

**Tampilan #2 — "Dark Tech":**
- Background near-black
- Satu aksen acid-green atau vermilion
- Font monospace di hero
- *Kapan boleh:* hanya jika subject memang developer tool atau cybersecurity

**Tampilan #3 — "Broadsheet":**
- Layout koran, hairline rules, zero border-radius
- Kolom teks padat
- Numbered markers 01 / 02 / 03 tanpa alasan urutan
- *Kapan boleh:* hanya jika content memang artikel panjang atau editorial

**Numbered markers (01/02/03) hanya dipakai kalau konten memang berurutan** — proses nyata atau timeline yang urutannya penting. Jangan pakai sebagai dekorasi.

**Animasi berlebihan = terlihat AI.** Setiap elemen yang bergerak harus punya alasan. Satu momen terkoordinasi lebih kuat dari efek tersebar di mana-mana.

---

## 3. Proses Kerja

### Tahap 1: Rencana Desain (sebelum nulis kode)

Buat rencana singkat yang mencakup:

**Warna** — 4–6 hex dengan nama deskriptif:
```
--ink:      #1a1a2e   (teks utama)
--paper:    #f8f7f4   (background)
--accent:   #c84b31   (aksen, dipakai hemat)
--muted:    #6b6b7a   (teks sekunder)
--surface:  #eeecea   (card/panel)
--border:   #d4d2cf   (divider)
```

**Tipografi** — 2–3 peran yang disengaja:
```
Display:  [nama font] — dipakai dengan sangat hemat di hero/heading besar
Body:     [nama font] — teks paragraf dan UI
Utility:  [nama font] — label, caption, data (opsional)
```

**Layout** — konsep satu kalimat + ASCII wireframe singkat

**Signature** — satu elemen unik yang paling diingat

### Tahap 2: Kritik Diri Sebelum Build

Tanya: *"Apakah rencana ini bisa dipakai untuk project lain yang mirip?"*

Kalau jawabannya iya → revisi. Ubah apa dan kenapa, lalu baru mulai kode.

### Tahap 3: Build & Kritik Lagi

Setelah selesai, cek: apakah ada elemen yang bisa dihilangkan tanpa kehilangan makna? Kalau iya, hapus.

---

## 4. Sistem Token Desain

Selalu definisikan variabel CSS di `:root` — jangan hardcode warna atau ukuran.

```css
:root {
  /* === WARNA === */
  --ink:      #1a1a2e;
  --ink-soft: #4a4a5a;
  --paper:    #f8f7f4;
  --surface:  #eeecea;
  --border:   #d4d2cf;
  --accent:   #c84b31;

  /* === TIPOGRAFI === */
  --font-display: 'Playfair Display', Georgia, serif;
  --font-body:    'Inter', system-ui, sans-serif;

  --text-xs:   0.75rem;   /* 12px */
  --text-sm:   0.875rem;  /* 14px */
  --text-base: 1rem;      /* 16px */
  --text-lg:   1.125rem;  /* 18px */
  --text-xl:   1.25rem;   /* 20px */
  --text-2xl:  1.5rem;    /* 24px */
  --text-3xl:  1.875rem;  /* 30px */
  --text-4xl:  2.25rem;   /* 36px */
  --text-5xl:  3rem;      /* 48px */

  /* === SPACING === */
  --space-1:   0.25rem;
  --space-2:   0.5rem;
  --space-3:   0.75rem;
  --space-4:   1rem;
  --space-6:   1.5rem;
  --space-8:   2rem;
  --space-12:  3rem;
  --space-16:  4rem;
  --space-24:  6rem;

  /* === RADIUS === */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 16px;
  --radius-full: 9999px;

  /* === SHADOW === */
  --shadow-sm:  0 1px 3px rgba(0,0,0,0.08);
  --shadow-md:  0 4px 16px rgba(0,0,0,0.10);
  --shadow-lg:  0 12px 40px rgba(0,0,0,0.14);

  /* === TRANSISI === */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --duration: 220ms;
}
```

---

## 5. Tipografi

### Prinsip Utama

- **Display face** = kepribadian, dipakai hemat (hero, heading besar H1/H2 saja)
- **Body face** = kenyamanan baca, dipakai di semua teks paragraf dan UI
- **Pasangan yang berkarakter** — jangan pakai dua font dari keluarga yang sama

### Pasangan Font yang Tidak Generik

**Kontras Serif + Sans:**
```
Display: 'Playfair Display' + Body: 'Inter'
Display: 'Cormorant Garamond' + Body: 'DM Sans'
Display: 'Libre Baskerville' + Body: 'Source Sans 3'
```

**Modern Geometric:**
```
Display: 'Fraunces' + Body: 'Nunito'
Display: 'Syne' + Body: 'Karla'
```

**Industrial / Technical:**
```
Display: 'Bebas Neue' + Body: 'IBM Plex Sans'
Display: 'Space Grotesk' + Body: 'Outfit'
```

### Cara Load via Google Fonts (di `<head>`)

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

### Skala Tipografi

```css
h1 { font-family: var(--font-display); font-size: var(--text-5xl); line-height: 1.1; font-weight: 700; }
h2 { font-family: var(--font-display); font-size: var(--text-3xl); line-height: 1.2; font-weight: 700; }
h3 { font-family: var(--font-body); font-size: var(--text-xl); line-height: 1.4; font-weight: 600; }
p  { font-family: var(--font-body); font-size: var(--text-base); line-height: 1.7; color: var(--ink-soft); }
```

---

## 6. Layout & Struktur

### Grid System

```css
.container {
  width: 100%;
  max-width: 1200px;
  margin-inline: auto;
  padding-inline: var(--space-6);
}

.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-8); }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-6); }
.grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-6); }
```

### Prinsip Struktur

- **Whitespace adalah konten** — jangan takut ruang kosong
- **Alignment lebih penting dari dekorasi** — teks yang sejajar rapi lebih "mewah" dari ornamen
- **Hierarchy visual** — satu elemen dominan per section, sisanya pendukung
- **Section harus punya tujuan** — kalau tidak bisa dijelaskan dalam satu kalimat, rethink

### Pola Layout Hero yang Tidak Generik

**Asimetris:**
```
┌─────────────────────────────────┐
│  [Tagline besar, 2 kolom kiri]  │  [Visual/gambar kanan] │
│  [Sub-text]                     │                         │
│  [CTA]                          │                         │
└─────────────────────────────────┘
```

**Full-bleed dengan teks overlay:**
```
┌─────────────────────────────────┐
│                                 │
│   [Background: gambar/video]    │
│                                 │
│   [Teks di tengah/bawah kiri]  │
│                                 │
└─────────────────────────────────┘
```

**Minimalis dengan satu aksen besar:**
```
┌─────────────────────────────────┐
│                                 │
│   [Banyak whitespace]           │
│   [Satu headline sangat besar]  │
│   [Satu tombol]                 │
│                                 │
└─────────────────────────────────┘
```

---

## 7. Double UI: Mobile & Desktop

**Wajib support kedua viewport.** Gunakan pendekatan **mobile-first**: tulis CSS untuk mobile dulu, tambahkan breakpoint untuk desktop.

### Breakpoint Standar

```css
/* Mobile: default (< 768px) */
/* Tablet: */
@media (min-width: 768px) { ... }
/* Desktop: */
@media (min-width: 1024px) { ... }
/* Wide: */
@media (min-width: 1280px) { ... }
```

### Perbedaan Layout Mobile vs Desktop

**Navigasi:**
```
Mobile:  Hamburger menu → drawer/bottom sheet
Desktop: Navbar horizontal dengan link langsung
```

**Grid:**
```
Mobile:  1 kolom (grid-template-columns: 1fr)
Tablet:  2 kolom
Desktop: 3–4 kolom
```

**Tipografi:**
```
Mobile:  h1 = text-3xl (30px), padding lebih kecil
Desktop: h1 = text-5xl (48px), padding lebih besar
```

**Touch vs Mouse:**
```
Mobile:  Target touch minimal 44×44px, no hover states sebagai primary
Desktop: Hover states, cursor pointer, tooltip
```

### Template CSS Double UI

```css
/* === MOBILE (default) === */
.nav-links { display: none; }
.hamburger { display: flex; }

.hero {
  padding-block: var(--space-16) var(--space-12);
  text-align: center;
}

.hero h1 { font-size: var(--text-3xl); }

.features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-6);
}

/* === DESKTOP === */
@media (min-width: 1024px) {
  .nav-links { display: flex; gap: var(--space-8); }
  .hamburger { display: none; }

  .hero {
    padding-block: var(--space-24);
    text-align: left;
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: center;
    gap: var(--space-16);
  }

  .hero h1 { font-size: var(--text-5xl); }

  .features-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### Hamburger Menu (Mobile)

```html
<button class="hamburger" aria-label="Buka menu" aria-expanded="false" onclick="toggleMenu()">
  <span></span><span></span><span></span>
</button>

<nav class="mobile-drawer" id="mobileMenu">
  <a href="#fitur">Fitur</a>
  <a href="#tentang">Tentang</a>
  <a href="#kontak">Kontak</a>
</nav>
```

```js
function toggleMenu() {
  const btn = document.querySelector('.hamburger');
  const menu = document.getElementById('mobileMenu');
  const isOpen = menu.classList.toggle('open');
  btn.setAttribute('aria-expanded', isOpen);
}
```

---

## 8. Motion & Interaksi

### Prinsip Motion

- **Satu momen terkoordinasi** lebih kuat dari banyak efek tersebar
- **Sembunyikan detail teknis** — animasi harus memperjelas, bukan menghibur
- **Hormati `prefers-reduced-motion`** selalu

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Animasi Masuk (Fade + Slide)

```css
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

.fade-up {
  animation: fadeUp 600ms var(--ease-out) both;
}

/* Delay bertahap untuk efek stagger */
.fade-up:nth-child(1) { animation-delay: 0ms; }
.fade-up:nth-child(2) { animation-delay: 80ms; }
.fade-up:nth-child(3) { animation-delay: 160ms; }
```

### Hover States yang Berasa

```css
.card {
  transition: transform var(--duration) var(--ease-out),
              box-shadow var(--duration) var(--ease-out);
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.btn {
  transition: background var(--duration), transform var(--duration);
}

.btn:hover { transform: translateY(-1px); }
.btn:active { transform: translateY(0); }
```

### Scroll Reveal (Intersection Observer)

```js
const observer = new IntersectionObserver((entries) => {
  entries.forEach(el => {
    if (el.isIntersecting) {
      el.target.classList.add('visible');
      observer.unobserve(el.target);
    }
  });
}, { threshold: 0.15 });

document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
```

```css
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 500ms var(--ease-out), transform 500ms var(--ease-out);
}
.reveal.visible {
  opacity: 1;
  transform: none;
}
```

---

## 9. Penulisan Konten (Copy)

**Kata-kata adalah material desain.** Konten yang generik membuat desain terasa generik.

**Tulis dari sisi pengguna:**
- Bukan: "Sistem kami mengoptimalkan workflow manajemen konten"
- Tapi: "Tulis, edit, dan publish — dari satu tempat"

**Aktif, bukan pasif:**
- Tombol: "Mulai sekarang" bukan "Submit"
- Toast: "Tersimpan" setelah tombol "Simpan"
- Error: "Email tidak valid — periksa format @domain.com" bukan "Terjadi kesalahan"

**Spesifik mengalahkan puitis:**
- Headline: "Kelola 10.000 produk tanpa spreadsheet" lebih kuat dari "Solusi bisnis terpadu"

**Layar kosong = undangan bertindak:**
- Bukan: "Tidak ada data"
- Tapi: "Belum ada produk. Tambahkan produk pertama kamu."

---

## 10. Template HTML Siap Pakai

Gunakan template ini sebagai titik awal, lalu modifikasi sesuai brief.

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[NAMA PROJECT]</title>

  <!-- Font: ganti sesuai brief -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

  <style>
    /* ===== RESET ===== */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    img, svg { display: block; max-width: 100%; }
    a { color: inherit; text-decoration: none; }
    button { cursor: pointer; border: none; background: none; font: inherit; }

    /* ===== TOKEN ===== */
    :root {
      /* Warna — GANTI sesuai brief */
      --ink:      #1a1a2e;
      --ink-soft: #5a5a6a;
      --paper:    #f8f7f4;
      --surface:  #eeecea;
      --border:   #d4d2cf;
      --accent:   #c84b31;
      --accent-dk:#a33a22;

      /* Font */
      --font-display: 'Playfair Display', Georgia, serif;
      --font-body:    'Inter', system-ui, sans-serif;

      /* Spacing */
      --space-2: 0.5rem;   --space-3: 0.75rem;  --space-4: 1rem;
      --space-6: 1.5rem;   --space-8: 2rem;     --space-12: 3rem;
      --space-16: 4rem;    --space-24: 6rem;

      /* Efek */
      --radius-sm: 4px; --radius-md: 8px; --radius-lg: 16px;
      --shadow-md:  0 4px 16px rgba(0,0,0,0.10);
      --shadow-lg:  0 12px 40px rgba(0,0,0,0.14);
      --ease-out:   cubic-bezier(0.16, 1, 0.3, 1);
      --duration:   220ms;
    }

    /* ===== BASE ===== */
    html { scroll-behavior: smooth; }
    body {
      font-family: var(--font-body);
      background: var(--paper);
      color: var(--ink);
      line-height: 1.6;
    }

    .container {
      width: 100%;
      max-width: 1200px;
      margin-inline: auto;
      padding-inline: var(--space-6);
    }

    /* ===== NAVBAR ===== */
    .navbar {
      position: sticky; top: 0; z-index: 100;
      padding-block: var(--space-4);
      background: rgba(248,247,244,0.9);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
    }

    .navbar .container {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .logo {
      font-family: var(--font-display);
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--ink);
    }

    .nav-links {
      display: none; /* Mobile: tersembunyi */
      list-style: none;
      gap: var(--space-8);
    }

    .nav-links a {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--ink-soft);
      transition: color var(--duration);
    }
    .nav-links a:hover { color: var(--ink); }

    .hamburger {
      display: flex;
      flex-direction: column;
      gap: 5px;
      padding: var(--space-2);
    }
    .hamburger span {
      display: block;
      width: 22px; height: 2px;
      background: var(--ink);
      border-radius: 2px;
      transition: transform var(--duration), opacity var(--duration);
    }
    .hamburger.open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
    .hamburger.open span:nth-child(2) { opacity: 0; }
    .hamburger.open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

    /* Mobile Drawer */
    .mobile-drawer {
      display: none;
      flex-direction: column;
      gap: var(--space-4);
      padding: var(--space-6);
      background: var(--paper);
      border-bottom: 1px solid var(--border);
    }
    .mobile-drawer.open { display: flex; }
    .mobile-drawer a {
      font-size: 1rem;
      font-weight: 500;
      color: var(--ink-soft);
      padding-block: var(--space-2);
      border-bottom: 1px solid var(--border);
    }

    /* ===== HERO ===== */
    .hero {
      padding-block: var(--space-16) var(--space-12);
      text-align: center;
    }

    .hero-eyebrow {
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: var(--space-4);
    }

    .hero h1 {
      font-family: var(--font-display);
      font-size: clamp(2rem, 6vw, 3.5rem);
      line-height: 1.1;
      font-weight: 700;
      color: var(--ink);
      margin-bottom: var(--space-6);
      max-width: 14ch;
      margin-inline: auto;
    }

    .hero p {
      font-size: 1.125rem;
      color: var(--ink-soft);
      max-width: 50ch;
      margin-inline: auto;
      margin-bottom: var(--space-8);
      line-height: 1.7;
    }

    .hero-actions {
      display: flex;
      gap: var(--space-3);
      justify-content: center;
      flex-wrap: wrap;
    }

    /* ===== BUTTONS ===== */
    .btn {
      display: inline-flex;
      align-items: center;
      gap: var(--space-2);
      padding: 0.75rem 1.5rem;
      border-radius: var(--radius-md);
      font-size: 0.9rem;
      font-weight: 600;
      transition: background var(--duration), transform var(--duration), box-shadow var(--duration);
    }
    .btn:hover { transform: translateY(-1px); }
    .btn:active { transform: translateY(0); }

    .btn-primary {
      background: var(--accent);
      color: #fff;
    }
    .btn-primary:hover {
      background: var(--accent-dk);
      box-shadow: 0 4px 20px rgba(200,75,49,0.3);
    }

    .btn-ghost {
      background: transparent;
      color: var(--ink);
      border: 1.5px solid var(--border);
    }
    .btn-ghost:hover {
      background: var(--surface);
      border-color: var(--ink-soft);
    }

    /* ===== SECTION ===== */
    .section { padding-block: var(--space-16); }
    .section-label {
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: var(--space-3);
    }
    .section-title {
      font-family: var(--font-display);
      font-size: clamp(1.75rem, 4vw, 2.5rem);
      font-weight: 700;
      line-height: 1.2;
      margin-bottom: var(--space-4);
    }
    .section-subtitle {
      font-size: 1.1rem;
      color: var(--ink-soft);
      max-width: 55ch;
      line-height: 1.7;
    }

    /* ===== CARD ===== */
    .card {
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      padding: var(--space-8);
      transition: transform var(--duration) var(--ease-out),
                  box-shadow var(--duration) var(--ease-out);
    }
    .card:hover {
      transform: translateY(-4px);
      box-shadow: var(--shadow-lg);
    }

    .card-icon {
      width: 48px; height: 48px;
      border-radius: var(--radius-md);
      background: var(--surface);
      display: flex; align-items: center; justify-content: center;
      margin-bottom: var(--space-4);
      font-size: 1.5rem;
    }

    /* ===== GRID ===== */
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--space-6);
    }

    /* ===== DIVIDER ===== */
    .divider {
      border: none;
      border-top: 1px solid var(--border);
      margin-block: 0;
    }

    /* ===== FOOTER ===== */
    footer {
      padding-block: var(--space-12);
      border-top: 1px solid var(--border);
    }
    .footer-inner {
      display: flex;
      flex-direction: column;
      gap: var(--space-6);
      align-items: center;
      text-align: center;
    }
    .footer-copy {
      font-size: 0.8rem;
      color: var(--ink-soft);
    }

    /* ===== ANIMASI ===== */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(20px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .fade-up { animation: fadeUp 600ms var(--ease-out) both; }
    .fade-up:nth-child(2) { animation-delay: 80ms; }
    .fade-up:nth-child(3) { animation-delay: 160ms; }
    .fade-up:nth-child(4) { animation-delay: 240ms; }

    .reveal {
      opacity: 0;
      transform: translateY(20px);
      transition: opacity 500ms var(--ease-out), transform 500ms var(--ease-out);
    }
    .reveal.visible { opacity: 1; transform: none; }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
      }
    }

    /* ===== DESKTOP ===== */
    @media (min-width: 1024px) {
      /* Navbar */
      .nav-links { display: flex; }
      .hamburger { display: none; }

      /* Hero */
      .hero { text-align: left; padding-block: var(--space-24); }
      .hero h1 { margin-inline: 0; }
      .hero p { margin-inline: 0; }
      .hero-actions { justify-content: flex-start; }

      /* Grid */
      .grid-2 { grid-template-columns: repeat(2, 1fr); }
      .grid-3 { grid-template-columns: repeat(3, 1fr); }
      .grid-4 { grid-template-columns: repeat(4, 1fr); }

      /* Footer */
      .footer-inner {
        flex-direction: row;
        justify-content: space-between;
        text-align: left;
      }
    }
  </style>
</head>
<body>

  <!-- ===== NAVBAR ===== -->
  <header class="navbar">
    <div class="container">
      <a href="#" class="logo">[Logo]</a>
      <ul class="nav-links">
        <li><a href="#fitur">Fitur</a></li>
        <li><a href="#tentang">Tentang</a></li>
        <li><a href="#kontak">Kontak</a></li>
      </ul>
      <button class="hamburger" id="hamburgerBtn" aria-label="Buka menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
    <nav class="mobile-drawer" id="mobileDrawer">
      <a href="#fitur">Fitur</a>
      <a href="#tentang">Tentang</a>
      <a href="#kontak">Kontak</a>
    </nav>
  </header>

  <!-- ===== HERO ===== -->
  <section class="hero section">
    <div class="container">
      <span class="hero-eyebrow fade-up">Tagline singkat</span>
      <h1 class="fade-up">[Headline utama yang spesifik]</h1>
      <p class="fade-up">[Sub-text yang menjelaskan nilai, bukan fitur]</p>
      <div class="hero-actions fade-up">
        <a href="#" class="btn btn-primary">Mulai sekarang</a>
        <a href="#" class="btn btn-ghost">Pelajari lebih</a>
      </div>
    </div>
  </section>

  <hr class="divider">

  <!-- ===== FITUR ===== -->
  <section class="section" id="fitur">
    <div class="container">
      <p class="section-label">Fitur</p>
      <h2 class="section-title reveal">[Headline section]</h2>
      <p class="section-subtitle reveal">[Deskripsi singkat]</p>

      <div class="grid grid-3" style="margin-top: var(--space-12);">
        <div class="card reveal">
          <div class="card-icon">✦</div>
          <h3 style="font-size:1.1rem; font-weight:600; margin-bottom:var(--space-2);">[Nama Fitur]</h3>
          <p style="font-size:0.9rem; color:var(--ink-soft);">[Deskripsi fitur dalam 1-2 kalimat]</p>
        </div>
        <div class="card reveal">
          <div class="card-icon">◈</div>
          <h3 style="font-size:1.1rem; font-weight:600; margin-bottom:var(--space-2);">[Nama Fitur]</h3>
          <p style="font-size:0.9rem; color:var(--ink-soft);">[Deskripsi fitur dalam 1-2 kalimat]</p>
        </div>
        <div class="card reveal">
          <div class="card-icon">⬡</div>
          <h3 style="font-size:1.1rem; font-weight:600; margin-bottom:var(--space-2);">[Nama Fitur]</h3>
          <p style="font-size:0.9rem; color:var(--ink-soft);">[Deskripsi fitur dalam 1-2 kalimat]</p>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== FOOTER ===== -->
  <footer>
    <div class="container">
      <div class="footer-inner">
        <a href="#" class="logo">[Logo]</a>
        <p class="footer-copy">© 2025 [Nama]. Semua hak dilindungi.</p>
      </div>
    </div>
  </footer>

  <script>
    // === Hamburger Menu ===
    const btn = document.getElementById('hamburgerBtn');
    const drawer = document.getElementById('mobileDrawer');

    btn.addEventListener('click', () => {
      const isOpen = drawer.classList.toggle('open');
      btn.classList.toggle('open', isOpen);
      btn.setAttribute('aria-expanded', isOpen);
    });

    // Tutup drawer saat klik link
    drawer.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        drawer.classList.remove('open');
        btn.classList.remove('open');
        btn.setAttribute('aria-expanded', 'false');
      });
    });

    // === Scroll Reveal ===
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(el => {
        if (el.isIntersecting) {
          el.target.classList.add('visible');
          observer.unobserve(el.target);
        }
      });
    }, { threshold: 0.12 });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  </script>
</body>
</html>
```

---

## 11. Cheat Sheet

```
┌──────────────────────────────────────────────────────────────┐
│  🐢 RUKA AI — FRONTEND DESIGN QUICK REFERENCE               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  PROSES WAJIB:                                               │
│    1. Baca SKILL/frontendDesignSkill.md dulu                 │
│    2. Tentukan: subject, audiens, satu tujuan utama          │
│    3. Buat rencana: warna + font + layout + signature        │
│    4. Kritik: apakah bisa untuk project lain? Kalau iya,     │
│       revisi dulu baru build                                 │
│    5. Build dari template, modifikasi sesuai brief           │
│                                                              │
│  ANTI-PATTERN (hindari default ini):                         │
│    ❌ Krem #F4F1EA + serif + terracotta (kecuali artisan)    │
│    ❌ Near-black + acid-green/vermilion (kecuali tech tool)  │
│    ❌ Layout koran + numbered markers tanpa urutan logis     │
│    ❌ Animasi di mana-mana tanpa tujuan                      │
│                                                              │
│  DOUBLE UI — WAJIB DUA VIEWPORT:                             │
│    Mobile:  1 kolom, hamburger menu, clamp() untuk font      │
│    Desktop: multi-kolom, nav horizontal, layout asimetris    │
│    Breakpoint: 768px (tablet) + 1024px (desktop)             │
│                                                              │
│  FONT PAIR YANG TIDAK GENERIK:                               │
│    Playfair Display + Inter (kontras serif+sans)             │
│    Cormorant Garamond + DM Sans (elegan)                     │
│    Fraunces + Nunito (playful tapi berkarakter)              │
│    Space Grotesk + Outfit (modern geometric)                 │
│    Bebas Neue + IBM Plex Sans (industrial)                   │
│                                                              │
│  TOKEN WAJIB DI :root:                                       │
│    --ink, --ink-soft, --paper, --surface                     │
│    --border, --accent, --accent-dk                           │
│    --font-display, --font-body                               │
│    --space-*, --radius-*, --shadow-*                         │
│    --ease-out, --duration                                    │
│                                                              │
│  COPY YANG BAIK:                                             │
│    ✅ "Tulis dan publish dari satu tempat"                   │
│    ❌ "Solusi konten terintegrasi terdepan"                  │
│    ✅ Tombol: "Mulai sekarang" | Toast: "Tersimpan"          │
│    ✅ Error spesifik: "Format email salah — butuh @"         │
│    ✅ Layar kosong = undangan bertindak                      │
│                                                              │
│  AKSESIBILITAS MINIMAL:                                      │
│    aria-label untuk icon buttons                             │
│    aria-expanded untuk hamburger menu                        │
│    prefers-reduced-motion selalu dihormati                   │
│    Keyboard navigable (tab order logis)                      │
│    Kontras teks minimum 4.5:1                                │
│                                                              │
│  ALUR UNTUK SETIAP PROJECT FRONTEND:                         │
│    Round 1: read_file("SKILL/frontendDesignSkill.md")        │
│    Round 2: Buat rencana desain (warna, font, layout, sig.)  │
│    Round 3: Kritik rencana — cukup unik? Jika tidak, revisi  │
│    Round 4: write_file("index.html") dari template + modif   │
│    Round 5: exec_command("open index.html") atau preview     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

<div align="center">

**🐢 Ruka AI — Frontend Design Skill Guide v1.0**

*Panduan desain UI clean, profesional, dan tidak generik.*
*Selalu punya identitas — bukan template.*

</div>
