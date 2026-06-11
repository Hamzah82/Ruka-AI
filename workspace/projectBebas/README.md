# 🐢 Task Manager CLI

Aplikasi manajemen tugas berbasis terminal yang dibuat dengan Python.

## ✨ Fitur

- 📋 **Lihat semua tugas** — Tampilkan daftar tugas dengan format yang rapi
- ➕ **Tambah tugas baru** — Buat tugas dengan judul, deskripsi, dan prioritas
- ✏️ **Edit tugas** — Ubah judul, deskripsi, atau prioritas tugas
- 🗑️ **Hapus tugas** — Hapus tugas dengan konfirmasi
- 🔍 **Cari tugas** — Cari berdasarkan kata kunci
- 📊 **Statistik** — Lihat ringkasan jumlah tugas berdasarkan status dan prioritas
- 🔄 **Ubah status** — Ganti status: todo / dikerjakan / selesai
- 💾 **Export CSV** — Export semua tugas ke file CSV

## 📁 Struktur Project

```
projectBebas/
├── main.py                  # Entry point aplikasi
├── README.md                # Dokumentasi
├── requirements.txt         # Dependencies
├── data/                    # Folder data JSON & CSV
│   └── tasks.json           # Database tugas (auto-generated)
├── task_manager/            # Package utama
│   ├── __init__.py          # Package init & version
│   ├── models.py            # Task model class
│   ├── storage.py           # JSON file storage handler
│   ├── display.py           # UI & formatting
│   └── utils.py             # Utility functions
└── tests/                   # Unit tests
    ├── __init__.py
    ├── test_models.py       # Tests untuk Task model
    └── test_storage.py      # Tests untuk TaskStorage
```

## 🚀 Cara Menjalankan

```bash
# Masuk ke folder project
cd workspace/projectBebas

# Jalankan aplikasi
python main.py

# Jalankan tests
python -m pytest tests/
# atau
python -m unittest discover tests/
```

## 📖 Penggunaan

1. Jalankan `python main.py`
2. Pilih menu dengan memasukkan angka 1-9
3. Ikuti instruksi di layar

## 📝 Contoh Tampilan

```
  [1] 📋 Belajar Python
       Prioritas: 🟡 sedang
       Status: todo
       Deskripsi: Pelajari dasar-dasar Python
       Dibuat: 2025-06-11 21:00:00
       Diupdate: 2025-06-11 21:00:00
```

## 🛠️ Teknologi

- Python 3.x
- JSON untuk penyimpanan data
- CSV untuk export
- unittest untuk testing

## 📄 Lisensi

MIT License — Dibuat oleh Ruka AI 🐢
