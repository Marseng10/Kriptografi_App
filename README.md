# WARISCRYPT — Secure Digital Inheritance System (The Last Will)

Sistem pewarisan pesan dan dokumen digital aman berbasis web dengan integrasi **Kriptografi Berlapis (Argon2id, AES-256-GCM, ChaCha20-Poly1305, RSA-OAEP)**, **Steganografi Gambar LSB**, **Verifikasi Biometrik Wajah (OpenCV)**, **Blockchain Audit Trail (Tamper-Evident SHA-256 Hash Chain)**, dan **USB Hardware Key Launcher**.

---

## 1. Fitur Utama & Arsitektur

### A. Peran Pengguna (Roles)
1. **Pewaris (Owner)**:
   - Registrasi dan login dengan kata sandi Argon2id atau Face Login.
   - Mengunggah pesan rahasia (dienkripsi AES-256-GCM) dan dokumen (dienkripsi ChaCha20-Poly1305).
   - Menghasilkan token klaim berpelindung RSA-OAEP dan menyisipkannya ke dalam gambar PNG melalui teknik steganografi LSB (Least Significant Bit).
   - Mendaftarkan ahli waris beserta foto referensi wajah biometrik untuk pencocokan klaim.
   - Mekanisme **Dead Man's Switch / Release Control** (status *locked* / *released*).
   - Mendaftarkan perangkat USB fisik dan mengunduh berkas kunci `wariscrypt.key`.

2. **Ahli Waris (Beneficiary)**:
   - Registrasi dan autentikasi aman.
   - Portal klaim warisan: mengunggah gambar steganografi PNG.
   - Verifikasi biometrik wajah langsung melalui webcam atau foto diri.
   - Dekripsi otomatis pesan rahasia dan unduh dokumen terenkripsi setelah otorisasi berhasil.

### B. Mesin Kriptografi (Cryptography Engine)
- **Password Hashing**: Argon2id (`time_cost=2`, `memory_cost=64MB`, `parallelism=2`).
- **Pesan Digital**: AES-256-GCM (Authenticated Encryption with Associated Data - AEAD).
- **Dokumen Digital**: ChaCha20-Poly1305 stream cipher.
- **Proteksi Token Klaim**: Enkripsi asimetris RSA-OAEP 2048-bit dengan SHA-256 MGF1.
- **Laboratorium Kriptografi Edukatif**: Demonstrasi interaktif cipher klasik Vigenère vs AES-256-GCM vs ChaCha20-Poly1305.

### C. Steganografi LSB (PNG Steganography)
- Menyisipkan token klaim ke dalam kanal warna LSB citra PNG dengan header biner penanda `WCPT`.
- Tidak tampak kasat mata (imperceptible) dan mempertahankan integritas data token.

### D. Biometrik Face Recognition (OpenCV)
- Analisis kontur, 3D color histogram correlation, grayscale structural similarity, dan ORB descriptor matching.
- Menghasilkan skor kesamaan kecocokan wajah (`similarity_score` 0.0 – 1.0) dengan ambang batas adaptif.

### E. Blockchain Audit Ledger (Tamper-Evident SHA-256 Chain)
- Setiap transaksi (registrasi, pembuatan wasiat, penambahan ahli waris, upaya klaim, perubahan status) dicatat dalam rantai blok hash yang saling terhubung (`previous_hash` $\rightarrow$ `current_hash`).
- Dilengkapi tombol verifikasi integritas rantai secara instan pada web explorer.

### F. USB Hardware Key Launcher
- Script pendamping `usb_launcher/usb_launcher.py` mendeteksi flashdisk fisik yang memuat `wariscrypt.key`.
- Memverifikasi fingerprint kriptografis ke backend dan otomatis membuka aplikasi web di browser default.

---

## 2. Struktur Basis Data (13 Tabel Relasional)

Sistem mengimplementasikan 13 tabel relasional sesuai dokumen rancangan:
1. `users` — Akun pengguna, peran (owner/beneficiary), hash Argon2id.
2. `user_profiles` — Detail profil dan nama lengkap.
3. `biometric_templates` — Metadata template wajah terlindungi.
4. `usb_devices` — Fingerprint perangkat USB yang terdaftar.
5. `beneficiaries` — Hubungan pewaris dengan akun ahli waris.
6. `beneficiary_reference_images` — Metadata citra referensi wajah ahli waris.
7. `digital_assets` — Metadata pesan & dokumen (tipe, path terenkripsi, algoritma, nonce, auth tag).
8. `asset_permissions` — Otorisasi akses & status rilis (*locked* / *released*).
9. `claim_tokens` — Hash token, ciphertext RSA, masa berlaku, dan status penggunaan.
10. `inheritance_claims` — Riwayat pengajuan klaim ahli waris.
11. `claim_verifications` — Riwayat tahapan verifikasi token dan skor kecocokan wajah.
12. `encryption_keys` — Identifier metadata kunci pada vault (kunci plaintext disimpan terpisah).
13. `audit_logs` — Rantai hash audit log blockchain.

Skrip DDL MySQL 8.0 murni tersedia di `database/init_mysql.sql`. Secara default aplikasi berjalan mulus menggunakan SQLite bawaan atau MySQL jika disetel pada `.env`.

---

## 3. Akun Uji Coba Cepat (Pre-Seeded)

| Peran | Username | Password | Keterangan |
| :--- | :--- | :--- | :--- |
| **Pewaris (Owner)** | `pewaris` | `Password123!` | Akun pewaris dengan sampel wasiat brankas & ahli waris terhubung |
| **Ahli Waris (Beneficiary)** | `ahliwaris` | `Password123!` | Akun anak kandung yang berhak mengklaim wasiat |

---

## 4. Cara Menjalankan Aplikasi

### A. Jalankan Server Web & Portal Sekaligus
Cukup jalankan satu perintah:
```bash
python run.py
```
Aplikasi akan:
1. Menginisialisasi basis data dan data demo secara otomatis.
2. Menjalankan server backend FastAPI pada `http://localhost:8000`.
3. Membuka browser default secara otomatis ke `http://localhost:8000/static/index.html`.

### B. Akses Halaman Web:
- **Beranda (Landing)**: `http://localhost:8000/static/index.html`
- **Masuk / Face Login**: `http://localhost:8000/static/sign-in.html`
- **Dashboard**: `http://localhost:8000/static/dashboard.html`
- **Tulis Wasiat Baru**: `http://localhost:8000/static/create-will.html`
- **Kelola Wasiat & Ahli Waris**: `http://localhost:8000/static/my-wills.html`
- **Portal Klaim Wasiat**: `http://localhost:8000/static/access-key.html`
- **Blockchain Explorer**: `http://localhost:8000/static/audit-trail.html`
- **Laboratorium Kripto**: `http://localhost:8000/static/crypto-demo.html`
- **Pengaturan USB Key**: `http://localhost:8000/static/usb-setup.html`
- **Dokumentasi API Swagger**: `http://localhost:8000/api/docs`

### C. Menjalankan USB Hardware Launcher:
1. Pada menu **USB Key**, buat dan unduh berkas `wariscrypt.key`.
2. Letakkan file `wariscrypt.key` di root flashdisk Anda.
3. Jalankan launcher:
```bash
python usb_launcher/usb_launcher.py
```
atau mode baris perintah:
```bash
python usb_launcher/usb_launcher.py --cli
```
Saat flashdisk terpasang, aplikasi web akan langsung terbuka secara otomatis di browser!

---

## 5. Menjalankan dengan MySQL 8.0 (XAMPP / Standalone)
Jika ingin menggunakan MySQL XAMPP:
1. Pastikan modul MySQL di XAMPP Control Panel aktif (RUNNING).
2. Buat database:
   ```bash
   mysql -u root < database/init_mysql.sql
   ```
3. Buat file `.env` di folder root:
   ```env
   DATABASE_URL=mysql+pymysql://root:@localhost:3306/wariscrypt
   ```
4. Jalankan seeder atau `run.py`:
   ```bash
   python database/seed_demo.py
   python run.py
   ```
