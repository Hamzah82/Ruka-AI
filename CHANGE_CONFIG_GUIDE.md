# Command Ruka Change - Ubah Endpoint Model dan API Key

## Fitur Baru: `ruka change`

Command baru yang memungkinkan Anda mengubah konfigurasi endpoint model AI dan API key dengan mudah melalui interface interaktif.

## Cara Menggunakan

### CLI Command
```bash
python main.py change
```

Atau gunakan alias pendek:
```bash
python main.py chg
```

### Interaktif Mode
Ketika menjalankan command, Anda akan diarahkan ke mode interaktif untuk mengubah:
1. **Endpoint API** - URL endpoint model AI (default: `https://ai.meongtopup.my.id/v1/chat/completions`)
2. **Model AI** - Nama model yang digunakan (default: `meng/deepseek-v4-flash`)
3. **API Key** - Kunci autentikasi untuk API (bisa kosong jika tidak menggunakan)

## Konfigurasi

Konfigurasi disimpan dalam file `config.json` di folder instalasi Ruka AI:

```json
{
  "api_endpoint": "https://ai.meongtopup.my.id/v1/chat/completions",
  "model": "meng/deepseek-v4-flash",
  "api_key": "",
  "updated_at": "2024-..."
}
```

## Keamanan

File `config.json` telah ditambahkan ke `.gitignore`, sehingga:
- ✅ File konfigurasi TIDAK akan ter-commit ke repository
- ✅ API key aman dari commit yang tidak sengaja
- ✅ File hanya tersimpan lokal di sistem Anda

## Cara Kerja

1. Jalankan `python main.py change`
2. Lihat konfigurasi saat ini
3. Tekan ENTER untuk tetap menggunakan nilai yang sama
4. Atau masukkan nilai baru untuk setiap field
5. Simpan perubahan otomatis

## Contoh Penggunaan

```bash
$ python main.py change

✻ Ubah Konfigurasi API
──────────────────────────────────────────────────────────────────
Endpoint saat ini:   https://ai.meongtopup.my.id/v1/chat/completions
Model saat ini:      meng/deepseek-v4-flash
API Key tersimpan:   Belum set

❯ Endpoint baru (Enter untuk tetap 'https://ai.meongtopup.my.id/v1/chat/completions'): 
❯ Model baru (Enter untuk tetap 'meng/deepseek-v4-flash'): new-model-name
❯ API Key baru (Ketik ENTER saja untuk HAPUS API key yang ada): sk-new-key-here

✓ Konfigurasi berhasil diubah!
  • Endpoint:   https://ai.meongtopup.my.id/v1/chat/completions
  • Model:      new-model-name
  • API Key:    ••••••••••••✓

• Konfigurasi tersimpan di /path/to/main.py/config.json
• File config.json sudah ditambahkan ke .gitignore
• Untuk menggunakan konfigurasi baru, silakan restart Ruka AI.
```

## Catatan Penting

- Perubahan konfigurasi memerlukan restart Ruka AI untuk diterapkan
- Jika Anda menghapus API key dengan menekan ENTER, konfigurasinya akan dikosongkan
- File `config.json` adalah file sensitif yang menyimpan credential penting
- Selalu pastikan file `.gitignore` mengandung `config.json` untuk keamanan
