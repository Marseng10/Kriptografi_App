WARISCRYPT (Secure Digital Inheritance System) adalah aplikasi berbasis web yang dirancang untuk mengamankan dan mengelola proses pewarisan pesan serta dokumen digital. Sistem ini mengintegrasikan kriptografi klasik dan modern, steganografi, Face Recognition, USB Launcher, serta blockchain sederhana.

Aplikasi memungkinkan seseorang sebagai pewaris (owner) untuk membuat pesan pribadi, mengunggah dokumen penting, dan menentukan ahli waris (beneficiary) yang berhak menerima data tersebut. Pesan dan file yang disimpan dienkripsi menggunakan algoritma yang berbeda sesuai dengan jenis datanya.

Setelah proses enkripsi selesai, sistem menghasilkan token klaim khusus. Token tersebut dienkripsi menggunakan algoritma kriptografi tersendiri, kemudian disisipkan ke dalam gambar menggunakan teknik steganografi. Gambar hasil steganografi diberikan oleh pewaris kepada ahli waris sebagai salah satu persyaratan untuk mengajukan klaim warisan.

Pada proses klaim, ahli waris mengunggah gambar tersebut. Sistem mengekstrak token tersembunyi, mendekripsi, dan memvalidasinya. Selanjutnya, sistem mencocokkan foto ahli waris yang diunggah saat klaim dengan foto referensi penerima yang sebelumnya didaftarkan oleh pewaris. Face Recognition juga digunakan untuk autentikasi login pengguna.

Aplikasi dilengkapi USB Launcher, yaitu aplikasi pendamping lokal yang mendeteksi keberadaan flashdisk WARISCRYPT dan membuka aplikasi web apabila perangkat terdeteksi. Aktivitas penting, seperti pembuatan dan klaim warisan, dicatat dalam blockchain sederhana untuk membantu menjaga integritas riwayat aktivitas.