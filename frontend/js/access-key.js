let claimCameraStream = null;

function showAlert(msg, isError = false) {
  const el = document.getElementById('claim-alert');
  el.className = `mb-6 p-4 rounded text-xs leading-relaxed ${isError ? 'bg-rose-950/80 border border-rose-800 text-rose-200' : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function onStegoFileSelected(input) {
  const label = document.getElementById('stego-file-label');
  if (input.files && input.files[0]) {
    label.textContent = `Gambar Stego Dipilih: ${input.files[0].name} (${(input.files[0].size / 1024).toFixed(1)} KB)`;
  }
}

async function startClaimCamera() {
  const video = document.getElementById('claim-video');
  const overlay = document.getElementById('claim-cam-overlay');
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 360 } });
    claimCameraStream = stream;
    video.srcObject = stream;
    if (overlay) overlay.classList.add('hidden');
  } catch (err) {
    showAlert('Tidak dapat mengakses kamera: ' + err.message, true);
  }
}

function captureClaimFace() {
  const video = document.getElementById('claim-video');
  const canvas = document.getElementById('claim-canvas');
  if (!video || !video.videoWidth) {
    showAlert('Nyalakan kamera terlebih dahulu', true);
    return;
  }
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const base64 = canvas.toDataURL('image/jpeg', 0.85);

  document.getElementById('claim-face-base64').value = base64;
  document.getElementById('face-captured-indicator').classList.remove('hidden');
  showAlert('Foto wajah berhasil diambil!', false);
}

async function handleClaimSubmission(e) {
  e.preventDefault();
  const alertEl = document.getElementById('claim-alert');
  alertEl.classList.add('hidden');

  const btn = document.getElementById('btn-submit-claim');
  btn.disabled = true;
  btn.textContent = 'Mengekstrak Stego & Memverifikasi Biometrik...';

  const stegoInput = document.getElementById('claim-stego-file');
  if (!stegoInput.files || !stegoInput.files[0]) {
    showAlert('Pilih berkas gambar steganografi PNG terlebih dahulu', true);
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="unlock" class="w-4 h-4 mr-2"></i><span>Ekstrak Token, Verifikasi Identitas & Buka Wasiat</span>`;
    return;
  }

  const faceBase64 = document.getElementById('claim-face-base64').value;
  const faceFileInput = document.getElementById('claim-face-file');

  const formData = new FormData();
  formData.append('stego_image', stegoInput.files[0]);

  if (faceFileInput.files && faceFileInput.files[0]) {
    formData.append('face_image', faceFileInput.files[0]);
  } else if (faceBase64) {
    formData.append('face_image_base64', faceBase64);
  } else {
    showAlert('Ambil foto via kamera atau unggah berkas foto wajah untuk verifikasi biometrik', true);
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="unlock" class="w-4 h-4 mr-2"></i><span>Ekstrak Token, Verifikasi Identitas & Buka Wasiat</span>`;
    return;
  }

  try {
    const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    const res = await fetch(`${CONFIG.API_BASE_URL}/claims/verify-and-claim`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Proses klaim gagal');
    }

    if (data.status === 'rejected') {
      showAlert(`Klaim ditolak: ${data.failure_reason || 'Pemeriksaan gagal'}`, true);
      return;
    }

    // Success
    showClaimSuccess(data);
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="unlock" class="w-4 h-4 mr-2"></i><span>Ekstrak Token, Verifikasi Identitas & Buka Wasiat</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

function showClaimSuccess(data) {
  const box = document.getElementById('claim-success-box');
  const scoreEl = document.getElementById('claim-match-score');
  const container = document.getElementById('decrypted-assets-container');

  scoreEl.textContent = `Kecocokan Biometrik Wajah: ${(data.similarity_score * 100).toFixed(1)}% &bull; Token RSA Sah & Diotentikasi &bull; Audit Block #${data.claim_id}`;

  const assets = data.released_assets || [];
  container.innerHTML = assets.map(a => {
    if (a.asset_type === 'message') {
      return `
        <div class="p-6 bg-slate-900 border border-willGold/40 rounded-lg space-y-3">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="font-cinzel text-willGold font-bold text-sm">${a.asset_name}</span>
            <span class="text-[10px] bg-amber-950 text-amber-300 px-2 py-0.5 rounded border border-amber-800 font-mono">DIDEKRIPSI (AES-256-GCM)</span>
          </div>
          <div class="p-4 bg-black/60 rounded border border-slate-800 font-serif text-slate-100 text-sm whitespace-pre-line leading-relaxed">
            ${a.decrypted_content}
          </div>
        </div>
      `;
    } else {
      return `
        <div class="p-6 bg-slate-900 border border-blue-500/40 rounded-lg space-y-3">
          <div class="flex items-center justify-between border-b border-slate-800 pb-2">
            <span class="font-cinzel text-white font-bold text-sm">${a.asset_name}</span>
            <span class="text-[10px] bg-blue-950 text-blue-300 px-2 py-0.5 rounded border border-blue-800 font-mono">DOKUMEN CHACHA20-POLY1305</span>
          </div>
          <p class="text-xs text-slate-300">Dokumen asli: <strong class="text-white">${a.original_filename || 'document'}</strong></p>
          <a href="${a.download_url}" class="gold-btn inline-flex items-center space-x-2 px-4 py-2 text-xs font-bold rounded">
            <i data-lucide="download" class="w-4 h-4"></i>
            <span>Unduh Dokumen Hasil Dekripsi</span>
          </a>
        </div>
      `;
    }
  }).join('');

  box.classList.remove('hidden');
  box.scrollIntoView({ behavior: 'smooth' });
}

window.onStegoFileSelected = onStegoFileSelected;
window.startClaimCamera = startClaimCamera;
window.captureClaimFace = captureClaimFace;
window.handleClaimSubmission = handleClaimSubmission;
