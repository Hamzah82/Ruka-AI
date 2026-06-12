# 🐢 Ruka AI — Vercel CLI Skill Guide

> Dokumentasi teknis lengkap cara deploy dan mengelola project di Vercel
> menggunakan Vercel CLI dari terminal.
> File ini berfungsi sebagai MEMORI PERSISTEN — baca setiap session baru
> ketika user minta bantuan soal Vercel.

---

## 📋 Daftar Isi

- [1. Overview](#1-overview)
- [2. Prasyarat & Instalasi](#2-prasyarat--instalasi)
- [3. Login & Autentikasi](#3-login--autentikasi)
- [4. Deploy Project](#4-deploy-project)
- [5. Project Management](#5-project-management)
- [6. Environment Variables](#6-environment-variables)
- [7. Custom Domain](#7-custom-domain)
  - [7.7 Set Subdomain Vercel (*.vercel.app)](#77-set-subdomain-vercel-vercelapp)
- [8. Deployments Management](#8-deployments-management)
- [9. Secrets](#9-secrets)
- [10. Teams & Organizations](#10-teams--organizations)
- [11. Logs](#11-logs)
- [12. Build Configuration (vercel.json)](#12-build-configuration-verceljson)
- [13. Framework Support](#13-framework-support)
- [14. Limits & Keterbatasan](#14-limits--keterbatasan)
- [15. Troubleshooting](#15-troubleshooting)
- [16. Cheat Sheet](#16-cheat-sheet)

---

## 1. Overview

**Apa itu Vercel?**
- Platform cloud untuk deploy web applications
- Dibuat oleh tim yang sama dengan Next.js
- Fokus pada **frontend** dan **serverless functions**
- Gratis untuk penggunaan dasar (Hobby plan)
- Deploy otomatis dari Git (GitHub, GitLab, Bitbucket)

**Apa itu Vercel CLI?**
- Command-line interface untuk mengontrol Vercel dari terminal
- Bisa melakukan hampir semua hal yang tersedia di dashboard web
- Lebih cepat dan fleksibel untuk power users

**Kenapa pakai Vercel CLI?**
- Tidak perlu buka browser untuk deploy
- Bisa otomatis di script / CI/CD
- Bisa atur semua settings dari terminal
- Cocok untuk environment tanpa GUI (seperti Termux)

---

## 2. Prasyarat & Instalasi

### 2.1 Prasyarat
- **Node.js** — harus terinstall (cek: `node --version`)
- **npm** atau **yarn** — package manager
- **Akun Vercel** — daftar di https://vercel.com/signup
- **Git** — opsional, tapi direkomendasikan

### 2.2 Install Vercel CLI

**Via npm:**
```bash
npm install -g vercel
```

**Via yarn:**
```bash
yarn global add vercel
```

**Via pnpm:**
```bash
pnpm add -g vercel
```

### 2.3 Cek Instalasi
```bash
vercel --version
```

### 2.4 Update Vercel CLI
```bash
npm install -g vercel@latest
```

---

## 3. Login & Autentikasi

### 3.1 Login
```bash
vercel login
```
- Akan membuka browser untuk autentikasi
- Pilih metode: GitHub, GitLab, Bitbucket, atau email
- Setelah login, token tersimpan lokal di mesin

### 3.2 Cek Status Login
```bash
vercel whoami
```
Output: username Vercel kamu

### 3.3 Logout
```bash
vercel logout
```

---

## 4. Deploy Project

### 4.1 Deploy Pertama Kali (Interaktif)
```bash
cd /path/to/project
vercel
```

CLI akan menanyakan:
- **Set up and deploy?** → `Y`
- **Which scope?** → pilih user atau team
- **Link to existing project?** → `N` (untuk project baru)
- **Project name?** → ketik nama project
- **Directory?** → `.` (direktori saat ini)
- **Override settings?** → `N` (kecuali perlu custom)

### 4.2 Deploy ke Production
```bash
vercel --prod
```
- Tanpa `--prod`, deploy hanya ke **preview** (URL unik)
- Dengan `--prod`, deploy ke **production** (domain utama)

### 4.3 Deploy Non-Interaktif (untuk script/CI)
```bash
vercel --yes --prod
```
- `--yes` → skip semua pertanyaan, pakai default

### 4.4 Deploy dengan Token (untuk CI/CD)
```bash
vercel --token=YOUR_TOKEN --prod
```

### 4.5 Deploy Build yang Sudah Ada (Skip Build)
```bash
vercel deploy --prebuilt
```
- Berguna jika build sudah dilakukan sebelumnya

### 4.6 Output Deploy
Setelah deploy berhasil, CLI menampilkan:
- **Preview URL** — URL unik untuk preview
- **Production URL** — URL production (jika `--prod`)
- **Inspect URL** — URL untuk inspect detail deployment

---

## 5. Project Management

### 5.1 Link Folder Lokal ke Project Vercel
```bash
vercel link
```
- Menghubungkan folder lokal ke project yang sudah ada di Vercel
- Membuat folder `.vercel/` berisi `project.json`

### 5.2 List Semua Project
```bash
vercel project ls
```
- Menampilkan semua project di akun/team

### 5.3 Buat Project Baru
```bash
vercel project add <project-name>
```
- Membuat project baru di Vercel tanpa deploy

### 5.4 Hapus Project
```bash
vercel project rm <project-name>
```
- **Hati-hati:** ini hapus project dan semua deployments

### 5.5 Lihat Info Project
```bash
vercel inspect <deployment-url>
```
- Detail lengkap sebuah deployment

---

## 6. Environment Variables

### 6.1 Tambah Environment Variable
```bash
# Production
vercel env add <variable-name>

# Preview
vercel env add <variable-name> preview

# Development
vercel env add <variable-name> development
```
- CLI akan minta input value
- Bisa juga pipe value: `echo "myvalue" | vercel env add KEY`

### 6.2 List Environment Variables
```bash
vercel env ls
```
- Menampilkan semua env var (production, preview, development)

### 6.3 Hapus Environment Variable
```bash
vercel env rm <variable-name>
```

### 6.4 Pull Environment Variables ke File Lokal
```bash
vercel env pull .env.local
```
- Download semua env var ke file `.env.local`
- Berguna untuk development lokal

### 6.5 Tipe Environment Variable
| Tipe | Kegunaan |
|------|----------|
| `production` | Hanya untuk production deployment |
| `preview` | Hanya untuk preview deployment |
| `development` | Hanya untuk `vercel dev` (local) |
| `encrypted` | Terenkripsi (pakai `vercel secrets`) |

---

## 7. Custom Domain

### 7.1 Tambah Custom Domain
```bash
vercel domains add <domain.com>
```
- Akan diminta setup DNS record
- Tambah CNAME atau A record sesuai instruksi

### 7.2 List Domain
```bash
vercel domains ls
```
- Menampilkan semua domain yang terhubung

### 7.3 Hapus Domain
```bash
vercel domains rm <domain.com>
```

### 7.4 Inspect Domain
```bash
vercel domains inspect <domain.com>
```
- Info detail: DNS record, SSL status, dll

### 7.5 Transfer Domain ke Vercel
```bash
vercel domains transfer <domain.com>
```
- Transfer domain dari registrar lain ke Vercel

### 7.6 Konfigurasi DNS yang Diperlukan

**Untuk apex domain (domain.com):**
```
Type: A
Name: @
Value: 76.76.21.21
```

**Untuk subdomain (www.domain.com):**
```
Type: CNAME
Name: www
Value: cname.vercel-dns.com
```

### 7.7 Set Subdomain Vercel (*.vercel.app)

Berbeda dengan custom domain yang perlu setup DNS, subdomain `*.verlangsung bisa dipakai tanpa konfigurasi DNS tambahan. Caranya adalah dengan **alias** langsung ke deployment production.

**Langkah-langkah:**

1. **Pastikan project sudah di-deploy ke production**
   ```bash
   cd /path/to/project
   vercel --prod
   ```

2. **Cek deployment production terbaru**
   ```bash
   vercel ls
   ```
   Output akan menampilkan daftan deployment, contoh:
   ```
   3h  project-name  https://project-name-abc123-user.vercel.app  ● Ready  Production
   ```

3. **Set alias subdomain vercel.app ke deployment**
   ```bash
   vercel alias <deployment-url> <subdomain>.vercel.app
   ```
   Contoh:
   ```bash
   vercel alias project-name-abc123-user.vercel.app ular-tangga-ruka-ai.vercel.app
   ```

4. **Hasil sukses:**
   ```
   > Success! https://ular-tangga-ruka-ai.vercel.app now points to project-name-abc123-user.vercel.app [2s]
   ```

5. **Verifikasi alias sudah terdaftar**
   ```bash
   vercel alias ls
   ```

**⚠️ Catatan penting:**
- Subdomain `*.vercel.app` **tidak perlu setup DNS** — langsung aktif setelah alias dibuat
- Subdomain harus **unik** secara global di seluruh Vercel (jika sudah dipakai user lain, akan error)
- Jika `vercel domains inspect <subdomain>.vercel.app` error "You don't have access", itu artinya domain belum ter-assign ke scope kamu — **langsung pakai `vercel alias` saja** sudah cukup
- `vercel domains add` **tidak bisa** dipakai untuk subdomain `*.vercel.app` — hanya untuk custom domain yang dimiliki (misal `domain.com`)
- Alias ini **mengarahkan** (redirect) subdomain ke deployment tertentu, bukan membuat deployment baru
- Setiap kali deploy ulang ke production, URL deployment berubah (suffix random), tapi **alias subdomain tetap menunjuk ke deployment terbaru** yang kamu assign

**Perbedaan `vercel domains add` vs `vercel alias`:**

| Aspek | `vercel domains add` | `vercel alias` |
|-------|---------------------|----------------|
| Custom domain sendiri (domain.com) | ✅ | ❌ |
| Subdomain vercel.app (*.vercel.app) | ❌ | ✅ |
| Perlu setup DNS | ✅ | ❌ |
| Langsung aktif | ❌ (tunggu propagasi) | ✅ (beberapa detik) |
| SSL otomatis | ✅ | ✅ |

---

## 8. Deployments Management

### 8.1 List Semua Deployment
```bash
vercel ls
# atau
vercel list
```
- Menampilkan semua deployment (preview + production)

### 8.2 Lihat Detail Deployment
```bash
vercel inspect <deployment-url>
```
- Info lengkap: status, URL, build logs, env vars, dll

### 8.3 Hapus Deployment
```bash
vercel rm <deployment-url>
```

### 8.4 Rollback ke Deployment Sebelumnya
```bash
vercel rollback <deployment-url>
```
- Instant rollback ke deployment tertentu
- Tidak perlu rebuild

### 8.5 Alias Deployment

**Custom domain (domain sendiri):**
```bash
vercel alias <deployment-url> <custom-domain.com>
```

**Subdomain vercel.app (tanpa DNS):**
```bash
vercel alias <deployment-url> <subdomain>.vercel.app
```

- Pasang custom domain / subdomain ke deployment tertentu
- Lihat detail penggunaan di [7.7 Set Subdomain Vercel](#77-set-subdomain-vercel-vercelapp)

### 8.6 List Alias
```bash
vercel alias ls
```

### 8.7 Remove Alias
```bash
vercel alias rm <domain.com>
```

---

## 9. Secrets

Secrets adalah environment variable terenkripsi, lebih aman untuk data sensitif.

### 9.1 Tambah Secret
```bash
vercel secrets add <secret-name> <value>
```
- Value terenkripsi di Vercel

### 9.2 List Secrets
```bash
vercel secrets ls
```
- Menampilkan nama secret (value tidak ditampilkan)

### 9.3 Hapus Secret
```bash
vercel secrets rm <secret-name>
```

### 9.4 Rename Secret
```bash
vercel secrets rename <old-name> <new-name>
```

### 9.5 Pakai Secret di Environment Variable
Setelah buat secret, reference di env var:
```bash
vercel env add DATABASE_URL
# Value: @secret-name (pakai prefix @)
```

---

## 10. Teams & Organizations

### 10.1 List Teams
```bash
vercel teams ls
```

### 10.2 Switch Scope (ganti team)
```bash
vercel switch <team-name>
```
- Semua command selanjutnya akan menggunakan scope team tersebut

### 10.3 Invite Member (via Dashboard)
- Harus via web dashboard: https://vercel.com/team

---

## 11. Logs

### 11.1 Lihat Logs Deployment
```bash
vercel logs <deployment-url>
```
- Menampilkan runtime logs dari serverless functions

### 11.2 Logs Real-time
```bash
vercel logs <deployment-url> --follow
```
- Stream logs secara real-time (mirip `tail -f`)

---

## 12. Build Configuration (vercel.json)

File `vercel.json` di root project untuk konfigurasi custom.

### 12.1 Struktur Dasar
```json
{
  "version": 2,
  "builds": [...],
  "routes": [...],
  "headers": [...],
  "redirects": [...],
  "rewrites": [...],
  "cleanUrls": true,
  "trailingSlash": false
}
```

### 12.2 Builds Configuration
```json
{
  "builds": [
    {
      "src": "index.html",
      "use": "@vercel/static"
    },
    {
      "src": "api/*.js",
      "use": "@vercel/node"
    },
    {
      "src": "package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ]
}
```

### 12.3 Routes Configuration
```json
{
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/$1" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```

### 12.4 Redirects
```json
{
  "redirects": [
    { "source": "/old-page", "destination": "/new-page", "permanent": true },
    { "source": "/blog/:slug", "destination": "/posts/:slug" }
  ]
}
```
- `permanent: true` → HTTP 308 (permanent redirect)
- `permanent: false` → HTTP 307 (temporary redirect)

### 12.5 Rewrites
```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://api.example.com/$1" }
  ]
}
```
- Sama seperti redirect tapi URL di browser tidak berubah

### 12.6 Headers
```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Cache-Control", "value": "public, max-age=31536000" }
      ]
    }
  ]
}
```

### 12.7 Build Settings via CLI Flags
```bash
# Custom build environment
vercel --build-env KEY=value

# Custom install command
vercel --install-command="npm install --legacy-peer-deps"

# Pilih region
vercel --regions cdg1  # Paris
```

---

## 13. Framework Support

### 13.1 Framework yang Didukung

**JavaScript / TypeScript:**
- Next.js ⭐ (optimal, dari pembuat yang sama)
- React (CRA, Vite)
- Vue.js / Nuxt
- Angular
- Svelte / SvelteKit
- Express.js
- Node.js standalone
- Remix
- Astro
- SolidStart
- Qwik

**Python:**
- Flask
- Django
- FastAPI
- Streamlit

**Go:**
- Native Go server
- Gin, Fiber

**Ruby:**
- Ruby on Rails
- Sinatra

**PHP:**
- Laravel

**Rust:**
- Actix, Axum

**Static Sites:**
- HTML/CSS/JS murni
- Hugo
- Gatsby
- Jekyll
- Eleventy (11ty)
- Docusaurus

### 13.2 Build Command Default per Framework

| Framework | Build Command | Output Directory |
|-----------|---------------|-----------------|
| Next.js | `next build` | `.next` |
| React (CRA) | `react-scripts build` | `build` |
| Vue | `vite build` | `dist` |
| Nuxt | `nuxt build` | `.output/public` |
| SvelteKit | `vite build` | `build` |
| Astro | `astro build` | `dist` |
| Hugo | `hugo` | `public` |
| Gatsby | `gatsby build` | `public` |
| Static | (tidak ada) | `.` |

### 13.3 Override Build Settings
Jika framework tidak terdeteksi otomatis, buat `vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm install",
  "framework": "vite"
}
```

---

## 14. Limits & Keterbatasan

### 14.1 Hobby Plan (Gratis)
| Limit | Nilai |
|-------|-------|
| Bandwidth | 100 GB/bulan |
| Serverless Execution | 10 detik per function |
| Build Time | 45 menit per deployment |
| Team Members | 1 (solo) |
| Custom Domain | ✅ |
| Environment Variables | ✅ |
| Preview Deployments | ✅ |
| Analytics | Basic |

### 14.2 Pro Plan ($20/bulan)
| Limit | Nilai |
|-------|-------|
| Bandwidth | 1 TB/bulan |
| Serverless Execution | 300 detik (5 menit) |
| Build Time | 45 menit per deployment |
| Team Members | Unlimited |
| Analytics | Advanced |
| Password Protection | ✅ |
| Concurrent Builds | 3 |

### 14.3 Keterbatasan Penting
- **Tidak untuk long-running process** — serverless functions punya timeout
- **Tidak cocok untuk WebSocket** — Vercel tidak support persistent connections
- **Tidak cocok untuk cron jobs** — pakai external cron service
- **Cold start** — serverless function bisa lambat pertama kali dipanggil
- **File system read-only** — kecuali `/tmp` (temporary, 512MB max)
- **Tidak bisa install package sistem** — hanya Node.js packages

---

## 15. Troubleshooting

### 15.1 "Command not found: vercel"
**Solusi:**
```bash
npm install -g vercel
# atau cek PATH
which vercel
```

### 15.2 Build Gagal
**Debug:**
```bash
# Lihat logs
vercel logs <deployment-url>

# Cek build settings di vercel.json
# Pastikan build command benar
# Pastikan output directory benar
```

### 15.3 "No Output Directory named 'build' found"
**Solusi:**
- Cek `outputDirectory` di `vercel.json`
- Pastikan build script menghasilkan folder yang benar
- Override di project settings

### 15.4 Environment Variable Tidak Muncul
**Solusi:**
- Pastikan env var ditambahkan untuk environment yang benar (production/preview/development)
- Redeploy setelah menambah env var
- Cek dengan `vercel env ls`

### 15.5 Custom Domain Tidak Bekerja
**Solusi:**
- Cek DNS record sudah benar: `vercel domains inspect domain.com`
- Tunggu propagasi DNS (bisa sampai 48 jam, biasanya beberapa menit)
- Pastikan SSL certificate sudah issued (cek di dashboard)

### 15.6 "Too Many Requests" (429)
**Solusi:**
- Rate limit dari Vercel API
- Tunggu beberapa saat lalu coba lagi
- Untuk CI/CD, gunakan `--token` flag

### 15.7 Rollback Cepat
Jika deploy production bermasalah:
```bash
# Lihat deployment sebelumnya
vercel ls

# Rollback ke deployment tertentu
vercel rollback <deployment-url>
```

---

## 16. Cheat Sheet

### Quick Commands

```bash
# === INSTALL & LOGIN ===
npm install -g vercel          # Install CLI
vercel --version               # Cek versi
vercel login                   # Login
vercel whoami                  # Cek user
vercel logout                  # Logout

# === DEPLOY ===
vercel                         # Deploy (preview, interaktif)
vercel --prod                  # Deploy ke production
vercel --yes --prod            # Deploy non-interaktif
vercel deploy --prebuilt       # Deploy tanpa build

# === PROJECT ===
vercel project ls              # List project
vercel project add <name>      # Buat project baru
vercel project rm <name>       # Hapus project
vercel link                    # Link folder ke project

# === ENVIRONMENT VARIABLES ===
vercel env add <key>           # Tambah env var (production)
vercel env add <key> preview   # Tambah env var (preview)
vercel env add <key> development  # Tambah env var (dev)
vercel env ls                  # List env var
vercel env rm <key>            # Hapus env var
vercel env pull .env.local     # Download env var ke file lokal

# === DOMAIN ===
vercel domains add <domain>    # Tambah custom domain
vercel domains ls              # List domain
vercel domains rm <domain>     # Hapus domain
vercel domains inspect <domain> # Info detail domain

# === DEPLOYMENTS ===
vercel ls                      # List semua deployment
vercel list                    # (sama dengan ls)
vercel inspect <url>           # Detail deployment
vercel rm <url>                # Hapus deployment
vercel rollback <url>          # Rollback ke deployment tertentu

# === ALIAS ===
vercel alias <url> <domain>    # Pasang custom domain ke deployment
vercel alias <url> <sub>.vercel.app  # Pasang subdomain vercel.app (tanpa DNS)
vercel alias ls                # List alias
vercel alias rm <domain>       # Hapus alias

# === SECRETS ===
vercel secrets add <name> <value>  # Tambah secret
vercel secrets ls              # List secrets
vercel secrets rm <name>       # Hapus secret
vercel secrets rename <old> <new>  # Rename secret

# === TEAMS ===
vercel teams ls                # List teams
vercel switch <team>           # Ganti scope ke team

# === LOGS ===
vercel logs <url>              # Lihat logs
vercel logs <url> --follow     # Logs real-time

# === BUILD FLAGS ===
vercel --build-env KEY=value   # Custom build env
vercel --regions cdg1          # Pilih region
```

### Decision Tree: Mau Deploy Project?

```
Mau deploy project ke Vercel?
│
├─ Belum install Vercel CLI?
│  └─ npm install -g vercel
│
├─ Belum login?
│  └─ vercel login
│
├─ Project baru (belum pernah deploy)?
│  ├─ cd /path/to/project
│  └─ vercel
│     (ikuti prompt interaktif)
│
├─ Project lama (sudah pernah deploy)?
│  ├─ cd /path/to/project
│  ├─ vercel --prod
│  └─ (otomatis detect project dari .vercel/project.json)
│
├─ Mau deploy non-interaktif (CI/CD)?
│  └─ vercel --yes --prod --token=YOUR_TOKEN
│
├─ Mau tambah custom domain?
│  └─ vercel domains add domain.com
│     (lalu setup DNS sesuai instruksi)
│
├─ Ada error di production?
│  ├─ Cek logs: vercel logs <url>
│  └─ Rollback: vercel rollback <url>
│
└─ Mau atur environment variable?
   └─ vercel env add KEY
      (pilih environment: production/preview/development)
```

### Alur Deploy Lengkap (Step by Step)

```
1. Install CLI
   npm install -g vercel

2. Login
   vercel login

3. Masuk ke folder project
   cd /path/to/project

4. (Opsional) Buat vercel.json jika perlu custom config
   {
     "buildCommand": "npm run build",
     "outputDirectory": "dist"
   }

5. Deploy pertama kali
   vercel
   → Ikuti prompt: Y → pilih scope → N → nama project → . → N

6. Deploy ke production
   vercel --prod

7. (Opsional) Tambah custom domain
   vercel domains add domain.com
   → Setup DNS sesuai instruksi

8. (Opsional) Tambah environment variable
   vercel env add DATABASE_URL

9. Cek deployment
   vercel ls

10. Cek logs jika ada masalah
    vercel logs <deployment-url>
```

---

<div align="center">

**🐢 Ruka AI — Vercel CLI Skill Guide v1.0**
*Dokumentasi lengkap Vercel CLI untuk deploy dan manage project.*
*Di-generate berdasarkan percobaan langsung di environment Termux.*
*Update file ini setiap ada penemuan baru.*

</div>
