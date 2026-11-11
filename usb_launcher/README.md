# WARISCRYPT USB Launcher

Aplikasi pendamping lokal untuk mendeteksi flashdisk fisik berlisensi WARISCRYPT dan meluncurkan aplikasi web secara otomatis setelah autentikasi kriptografis berhasil.

## Cara Kerja:
1. Pengguna (Pewaris) mendaftarkan perangkat USB pada menu **USB Security Key** di aplikasi web.
2. Unduh berkas `wariscrypt.key` yang berisi fingerprint kriptografis dan simpan di root flashdisk.
3. Jalankan `python usb_launcher/usb_launcher.py`.
4. Launcher akan memindai flashdisk yang terpasang, mengirim fingerprint ke API backend (`/api/usb/verify`), dan otomatis membuka browser ke portal WARISCRYPT bila terverifikasi!

## Menjalankan Mode CLI:
```bash
python usb_launcher/usb_launcher.py --cli
```
