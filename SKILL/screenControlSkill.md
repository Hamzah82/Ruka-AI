# GUI Control Skill — Kontrol Desktop & Layar

> Panduan untuk Ruka AI dalam mengontrol GUI desktop (X11) via tool bawaan.
> Baca skill ini saat user meminta: kontrol GUI, klik, ketik, screenshot,
> buka/tutup jendela, kontrol mouse/keyboard, atau otomasi desktop.

---

## 1. Prasyarat (X11 Only)

Tool GUI control **HANYA berfungsi di sesi X11** — bukan Wayland.

Cek dulu sebelum pakai:
```bash
echo "$XDG_SESSION_TYPE"   # harus 'x11'
echo "$DISPLAY"            # harus ':0' atau sejenisnya
```

Tool yang dibutuhkan (semua sudah terinstall di mesin target):
- **`xdotool`** — simulasi mouse & keyboard
- **`wmctrl`** — kelola jendela (fokus, tutup, maximize)
- **`scrot`** / **`gnome-screenshot`** — screenshot layar

Cek ketersediaan:
```bash
for t in xdotool wmctrl scrot; do command -v $t; done
```

Jika Wayland (bukan X11), tool ini TIDAK akan jalan. Beri tahu user.

---

## 2. Tool yang Tersedia di Ruka

Ada 4 tool GUI control yang bisa dipanggil langsung:

| Tool | Fungsi | Aksi Utama |
|---|---|---|
| `gui_screenshot` | Ambil screenshot layar | `output` (path PNG) |
| `gui_mouse` | Kontrol kursor mouse | `move`, `click`, `click_at`, `scroll`, `get` |
| `gui_keyboard` | Input keyboard | `key` (tombol), `type` (teks) |
| `gui_window` | Kelola jendela | `list`, `focus`, `close`, `maximize`, `minimize`, `move` |

---

## 3. Alur Kerja yang Benar (PENTING)

**Jangan langsung klik/ketik tanpa tahu kondisi layar!** Ikuti alur ini:

```
1. gui_window(action="list")      → lihat jendela apa saja yang terbuka
2. gui_screenshot()               → ambil screenshot untuk pahami tata letak
3. gui_window(action="focus", title="...") → fokus ke aplikasi target
4. gui_mouse(action="click_at", x=..., y=...)  → klik di koordinat
5. gui_keyboard(action="type", text="...")     → ketik
6. gui_screenshot()               → verifikasi hasilnya
```

**Aturan emas:**
- **Ambil screenshot dulu** sebelum aksi — supaya tahu posisi tombol/menu
- **Verifikasi dengan screenshot** setelah aksi — pastikan hasil sesuai
- **Koordinat buta** — Ruka tidak "melihat" layar; butuh koordinat eksplisit atau screenshot untuk menentukan posisi
- **Satu langkah per aksi** — jangan boros; lakukan bertahap

---

## 4. Detail Penggunaan Tool

### gui_screenshot
```json
{"name": "gui_screenshot", "arguments": {"output": "/tmp/ruka_screen.png"}}
```
Hasil: path file PNG. Bisa dibaca/dianalisis untuk menentukan koordinat.

### gui_mouse
Koordinat layar: **0,0 = kiri-atas**. Geser kanan = X naik, geser bawah = Y naik.

```json
{"name": "gui_mouse", "arguments": {"action": "get"}}
{"name": "gui_mouse", "arguments": {"action": "move", "x": 500, "y": 300}}
{"name": "gui_mouse", "arguments": {"action": "click", "button": "1"}}
{"name": "gui_mouse", "arguments": {"action": "click_at", "x": 500, "y": 300, "button": "1"}}
{"name": "gui_mouse", "arguments": {"action": "click_at", "x": 500, "y": 300, "clicks": 2}}  // double-click
{"name": "gui_mouse", "arguments": {"action": "scroll", "y": 1}}   // scroll ke atas
{"name": "gui_mouse", "arguments": {"action": "scroll", "y": -1}}  // scroll ke bawah
```

**Button:** `1` = kiri, `2` = tengah, `3` = kanan.

### gui_keyboard
```json
{"name": "gui_keyboard", "arguments": {"action": "key", "keys": "Return"}}
{"name": "gui_keyboard", "arguments": {"action": "key", "keys": "Tab"}}
{"name": "gui_keyboard", "arguments": {"action": "key", "keys": "ctrl+c"}}
{"name": "gui_keyboard", "arguments": {"action": "key", "keys": "alt+F4"}}
{"name": "gui_keyboard", "arguments": {"action": "key", "keys": "ctrl+shift+n"}}
{"name": "gui_keyboard", "arguments": {"action": "type", "text": "Halo dari Ruka AI"}}
```

**Nama tombol umum:** `Return` (Enter), `Tab`, `space`, `BackSpace`, `Delete`,
`Escape`, `Home`, `End`, `Up`, `Down`, `Left`, `Right`, `F1`-`F12`,
`ctrl`, `alt`, `shift`, `super` (Windows key).

### gui_window
```json
{"name": "gui_window", "arguments": {"action": "list"}}
{"name": "gui_window", "arguments": {"action": "focus", "title": "Firefox"}}
{"name": "gui_window", "arguments": {"action": "close", "title": "Firefox"}}
{"name": "gui_window", "arguments": {"action": "maximize", "title": "Firefox"}}
{"name": "gui_window", "arguments": {"action": "minimize", "title": "Firefox"}}
{"name": "gui_window", "arguments": {"action": "move", "title": "Firefox", "x": 100, "y": 100, "width": 800, "height": 600}}
```

`title` adalah **substring** judul jendela — cukup sebagian (mis. "Firefox").

---

## 5. Contoh Skenario

### Buka aplikasi & ketik
```
User: "Buka terminal lalu ketik ls -la"

1. gui_keyboard(action="key", keys="super")       # buka menu aplikasi
2. gui_keyboard(action="type", text="terminal")
3. gui_keyboard(action="key", keys="Return")
4. gui_keyboard(action="type", text="ls -la")
5. gui_keyboard(action="key", keys="Return")
```

### Fokus ke browser & buka situs
```
User: "Fokus ke Firefox lalu buka youtube.com"

1. gui_window(action="focus", title="Firefox")
2. gui_keyboard(action="key", keys="ctrl+l")      # fokus address bar
3. gui_keyboard(action="type", text="youtube.com")
4. gui_keyboard(action="key", keys="Return")
```

### Screenshot lalu analisis
```
User: "Screenshot layar"

1. gui_screenshot(output="/tmp/screen.png")
2. Info: screenshot tersimpan, bisa dianalisis untuk menentukan koordinat
```

---

## 6. Keamanan & Batasan

- **Jangan klik tanpa tahu posisi** — bisa salah tekan. Selalu screenshot dulu.
- **Koordinat tidak presisi** — untuk klik presisi, minta user konfirmasi koordinat atau analisis screenshot dulu.
- **Jangan jalankan aksi destruktif** — mis. `close` tanpa konfirmasi user.
- **Timeout** — tiap perintah GUI punya timeout 15 detik.
- **Bukan vision** — Ruka tidak benar-benar "melihat" layar. Screenshot hanya disimpan, tidak otomatis dianalisis visual kecuali user minta.
- **X11 only** — di Wayland semua tool ini gagal.

---

## 7. Troubleshooting

**"Error: perintah tidak ditemukan"**
Tool GUI belum terinstall. Install:
```bash
sudo apt install xdotool wmctrl scrot
```

**"Error: DISPLAY tidak tersedia"**
Bukan sesi X11, atau DISPLAY belum di-set. Cek:
```bash
echo $DISPLAY   # harus ':0' atau sejenisnya
```

**Screenshot kosong / hitam**
Cek apakah sesi X11 aktif & ada akses ke display. Mungkin perlu `DISPLAY=:0`.

**Klik tidak kena sasaran**
Koordinat salah. Ambil screenshot, tentukan koordinat yang benar, coba lagi.