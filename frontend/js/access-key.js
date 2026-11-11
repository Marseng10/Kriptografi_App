let claimCameraStream = null;
const BTN_LABEL = 'Buka Wasiat';

document.addEventListener('DOMContentLoaded', () => {
  if (!localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN)) {
    document.getElementById('guest-notice').classList.remove('hidden');
  }
});

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function showAlert(msg, isError = false) {
  const el = document.getElementById('claim-alert');
  el.className = `mb-5 p-3 rounded text-sm ${isError ? 'bg-rose-950/80 border border-rose-800 text-rose-200' : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function onStegoFileSelected(input) {
  if (input.files && input.files[0]) {
    document.getElementById('stego-file-label').textContent = `Dipilih: ${input.files[0].name}`;
  }
}

async function startClaimCamera() {
  try {
    claimCameraStream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 360 } });
    document.getElementById('claim-video').srcObject = claimCameraStream;
    document.getElementById('claim-cam-overlay').classList.add('hidden');
  } catch (err) {
    showAlert('Kamera tidak dapat diakses: ' + err.message, true);
  }
}

function captureClaimFace() {
  const video = document.getElementById('claim-video');
  const canvas = document.getElementById('claim-canvas');
  if (!video.videoWidth) {
    showAlert('Nyalakan kamera terlebih dahulu.', true);
    return;
  }
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  document.getElementById('claim-face-base64').value = canvas.toDataURL('image/jpeg', 0.85);
  document.getElementById('face-captured-indicator').classList.remove('hidden');
}

async function handleClaimSubmission(e) {
  e.preventDefault();
  document.getElementById('claim-alert').classList.add('hidden');

  const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  if (!token) {
    window.location.href = 'sign-in.html';
    return;
  }

  const btn = document.getElementById('btn-submit-claim');
  const stegoInput = document.getElementById('claim-stego-file');
  const faceBase64 = document.getElementById('claim-face-base64').value;
  const faceFile = document.getElementById('claim-face-file');

  const formData = new FormData();
  formData.append('stego_image', stegoInput.files[0]);
  if (faceFile.files && faceFile.files[0]) {
    formData.append('face_image', faceFile.files[0]);
  } else if (faceBase64) {
    formData.append('face_image_base64', faceBase64);
  } else {
    showAlert('Ambil foto wajah atau unggah foto terlebih dahulu.', true);
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Memverifikasi...';
  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/claims/verify-and-claim`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Klaim gagal diproses');
    if (data.status === 'rejected') {
      showAlert('Verifikasi wajah tidak cocok. Silakan coba lagi dengan foto yang lebih jelas.', true);
      return;
    }
    showClaimSuccess(data);
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = BTN_LABEL;
  }
}

async function downloadDocument(url, filename) {
  const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
  if (!res.ok) {
    showAlert('Gagal mengunduh dokumen.', true);
    return;
  }
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename || 'dokumen';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function showClaimSuccess(data) {
  const container = document.getElementById('decrypted-assets-container');
  container.innerHTML = (data.released_assets || []).map(a => {
    if (a.asset_type === 'message') {
      return `
        <div class="p-5 bg-slate-900 border border-willGold/40 rounded-lg">
          <div class="font-semibold text-willGold mb-2">${esc(a.asset_name)}</div>
          <div class="p-4 bg-black/50 rounded border border-slate-800 text-sm whitespace-pre-line leading-relaxed">${esc(a.decrypted_content)}</div>
        </div>`;
    }
    return `
      <div class="p-5 bg-slate-900 border border-willGold/40 rounded-lg">
        <div class="font-semibold text-willGold mb-1">${esc(a.asset_name)}</div>
        <div class="text-sm text-slate-300 mb-3">${esc(a.original_filename || 'Dokumen')}</div>
        <button type="button" onclick="downloadDocument('${CONFIG.API_BASE_URL.replace('/api', '')}${a.download_url}', '${esc(a.original_filename || 'dokumen')}')"
          class="gold-btn px-4 py-2 text-sm font-semibold">Unduh Dokumen</button>
      </div>`;
  }).join('');

  const box = document.getElementById('claim-success-box');
  box.classList.remove('hidden');
  box.scrollIntoView({ behavior: 'smooth' });
}

window.onStegoFileSelected = onStegoFileSelected;
window.startClaimCamera = startClaimCamera;
window.captureClaimFace = captureClaimFace;
window.handleClaimSubmission = handleClaimSubmission;
window.downloadDocument = downloadDocument;
