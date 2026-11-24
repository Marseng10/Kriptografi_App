document.addEventListener('DOMContentLoaded', () => {
  const token = window.getAuthToken ? window.getAuthToken() : '';
  const user = window.getUserProfile ? window.getUserProfile() : null;

  if (!token) {
    document.getElementById('guest-notice').classList.remove('hidden');
  } else if (user && user.role === 'owner') {
    const notice = document.getElementById('guest-notice');
    notice.innerHTML = `
      Anda sedang masuk sebagai <strong>Pewaris</strong>. Untuk mengklaim wasiat, Anda perlu masuk dengan akun <strong>Ahli Waris</strong>.
      <a href="dashboard.html" class="underline font-semibold ml-2 text-willGold">Ke Dasbor Pewaris &rarr;</a>
    `;
    notice.classList.remove('hidden');
  }

  if (window.lucide) lucide.createIcons();
});

function showAlert(msg, isError = false) {
  const el = document.getElementById('claim-alert');
  el.className = `p-3 rounded-lg text-xs leading-relaxed ${
    isError
      ? 'bg-rose-950/80 border border-rose-800 text-rose-200'
      : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'
  }`;
  el.textContent = msg;
  el.classList.remove('hidden');
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function onStegoFileSelected(input) {
  if (input.files && input.files[0]) {
    const file = input.files[0];
    document.getElementById('stego-file-label').textContent = `Dipilih: ${file.name}`;

    const reader = new FileReader();
    reader.onload = (e) => {
      const img = document.getElementById('stego-img-preview');
      img.src = e.target.result;
      img.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  }
}

async function handleClaimSubmission(e) {
  e.preventDefault();
  document.getElementById('claim-alert').classList.add('hidden');

  const token = window.getAuthToken ? window.getAuthToken() : '';
  if (!token) {
    showAlert('Silakan masuk dengan akun ahli waris terlebih dahulu.', true);
    setTimeout(() => {
      window.location.href = 'sign-in.html';
    }, 1200);
    return;
  }

  const btn = document.getElementById('btn-submit-claim');
  const stegoInput = document.getElementById('claim-stego-file');

  if (!stegoInput.files || !stegoInput.files[0]) {
    showAlert('Pilih berkas kartu akses (.png) terlebih dahulu.', true);
    return;
  }

  const formData = new FormData();
  formData.append('stego_image', stegoInput.files[0]);

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 mr-1 inline animate-spin"></i><span>Mengekstrak Kunci &amp; Membuka Wasiat...</span>`;
  if (window.lucide) lucide.createIcons();

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/claims/verify-and-claim`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Klaim gagal diproses');

    if (data.status === 'rejected') {
      showAlert(data.failure_reason || 'Klaim tidak dapat diproses.', true);
      return;
    }

    showClaimSuccess(data);
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="unlock" class="w-4 h-4 mr-1 inline"></i><span>Buka &amp; Dekripsi Wasiat Sekarang</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

async function downloadDocument(url, filename) {
  const token = window.getAuthToken ? window.getAuthToken() : '';
  try {
    const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!res.ok) throw new Error('Gagal mengunduh dokumen.');
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename || 'dokumen';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (e) {
    showAlert('Gagal mengunduh dokumen: ' + e.message, true);
  }
}

function showClaimSuccess(data) {
  const container = document.getElementById('decrypted-assets-container');
  const assets = data.released_assets || [];

  if (assets.length === 0) {
    container.innerHTML = `
      <div class="p-5 bg-slate-900 border border-slate-800 rounded-lg text-center text-xs text-slate-400">
        Wasiat telah diotorisasi, namun belum ada berkas pesan yang dilampirkan.
      </div>
    `;
  } else {
    container.innerHTML = assets.map(a => {
      const msgText = a.decrypted_content || a.content || '';
      const hasMsg = Boolean(a.has_message || (a.asset_type === 'message' && msgText));
      const hasDoc = Boolean(a.has_document || a.download_url);
      const fileName = a.original_filename || a.asset_name || 'dokumen_wasiat';

      return `
        <div class="p-5 bg-slate-900/90 border border-willGold/40 rounded-xl space-y-4 shadow-lg">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <div class="flex items-center space-x-2 text-willGold font-cinzel font-bold text-sm">
              <i data-lucide="scroll" class="w-4 h-4"></i>
              <span>${esc(a.asset_name)}</span>
            </div>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-willGold/15 text-willGold border border-willGold/30">
              ${hasMsg && hasDoc ? 'Pesan & Dokumen' : (hasDoc ? 'Dokumen' : 'Pesan Teks')}
            </span>
          </div>

          ${hasMsg ? `
            <div class="space-y-1.5">
              <div class="text-[11px] font-semibold text-slate-400 flex items-center space-x-1.5">
                <i data-lucide="mail" class="w-3.5 h-3.5 text-willGold"></i>
                <span>Isi Pesan Wasiat:</span>
              </div>
              <div class="p-4 bg-black/60 rounded-lg border border-slate-800 text-xs text-slate-200 whitespace-pre-line leading-relaxed">
                ${esc(msgText)}
              </div>
            </div>
          ` : ''}

          ${hasDoc ? `
            <div class="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div class="flex items-center space-x-2.5 min-w-0">
                <div class="w-8 h-8 rounded bg-willGold/15 border border-willGold/30 flex items-center justify-center text-willGold shrink-0">
                  <i data-lucide="file-text" class="w-4 h-4"></i>
                </div>
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-white truncate">${esc(fileName)}</div>
                  <div class="text-[10px] text-slate-400">Lampiran Berkas Wasiat Terdekripsi</div>
                </div>
              </div>
              <button type="button" onclick="downloadDocument('${CONFIG.API_BASE_URL.replace('/api', '')}${a.download_url}', '${esc(fileName)}')"
                class="gold-btn px-4 py-2 text-xs font-semibold whitespace-nowrap">
                <i data-lucide="download" class="w-3.5 h-3.5 mr-1"></i>
                <span>Unduh Berkas</span>
              </button>
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  }

  const box = document.getElementById('claim-success-box');
  box.classList.remove('hidden');
  box.scrollIntoView({ behavior: 'smooth' });
  if (window.lucide) lucide.createIcons();
}

window.onStegoFileSelected = onStegoFileSelected;
window.handleClaimSubmission = handleClaimSubmission;
window.downloadDocument = downloadDocument;
