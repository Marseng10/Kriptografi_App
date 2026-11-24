document.addEventListener('DOMContentLoaded', async () => {
  if (window.requireAuth && !window.requireAuth('owner')) return;
  await loadBeneficiaries();
  if (window.lucide) lucide.createIcons();
});

let currentBeneficiaries = [];

function updateFileNameDisplay(input) {
  const label = document.getElementById('file-label-text');
  const clearBtn = document.getElementById('btn-clear-file');
  if (input.files && input.files[0]) {
    const f = input.files[0];
    const sizeStr = f.size >= 1024 * 1024
      ? `${(f.size / (1024 * 1024)).toFixed(2)} MB`
      : `${(f.size / 1024).toFixed(1)} KB`;
    label.textContent = `Berkas dipilih: ${f.name} (${sizeStr})`;
    label.className = 'text-xs text-willGold font-semibold block';
    if (clearBtn) clearBtn.classList.remove('hidden');
  } else {
    label.textContent = 'Klik untuk melampirkan berkas dokumen pada wasiat ini';
    label.className = 'text-xs text-slate-300 font-medium block';
    if (clearBtn) clearBtn.classList.add('hidden');
  }
}

function clearSelectedFile() {
  const fileInput = document.getElementById('document-file');
  if (fileInput) {
    fileInput.value = '';
    updateFileNameDisplay(fileInput);
  }
}

async function loadBeneficiaries() {
  const listEl = document.getElementById('beneficiaries-list');
  try {
    const res = await apiFetch('/beneficiaries/');
    if (!res.ok) throw new Error('Gagal memuat ahli waris');
    currentBeneficiaries = await res.json();

    if (currentBeneficiaries.length === 0) {
      listEl.innerHTML = `
        <div class="text-xs text-amber-300/90 py-2 flex items-center justify-between">
          <span>Belum ada ahli waris terdaftar.</span>
          <button type="button" onclick="openAddBeneficiaryModal()" class="text-willGold underline font-semibold ml-2">+ Tambah Sekarang</button>
        </div>
      `;
      return;
    }

    listEl.innerHTML = currentBeneficiaries.map(b => `
      <label class="flex items-center space-x-3 p-2.5 rounded bg-slate-900 hover:bg-slate-800/80 cursor-pointer text-xs transition border border-slate-800/80">
        <input type="checkbox" name="selected_bens" value="${b.beneficiary_id}" checked class="rounded text-willGold focus:ring-0">
        <div class="flex-1 min-w-0">
          <span class="font-semibold text-white truncate block">${esc(b.full_name || b.username)}</span>
          <span class="text-[11px] text-slate-400">Hubungan: ${esc(b.relationship || 'Ahli Waris')} &bull; @${esc(b.username)}</span>
        </div>
      </label>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="text-xs text-rose-400 py-2">${esc(err.message)}</div>`;
  }
}

async function handleCreateWill(e) {
  e.preventDefault();
  const alertEl = document.getElementById('create-alert');
  alertEl.classList.add('hidden');

  const assetName = document.getElementById('asset-name').value.trim();
  const messageContent = document.getElementById('message-content').value.trim();
  const fileInput = document.getElementById('document-file');
  const hasFile = fileInput && fileInput.files && fileInput.files[0];

  if (!messageContent && !hasFile) {
    alertEl.className = 'p-3 rounded-lg text-xs bg-rose-950/80 border border-rose-800 text-rose-200';
    alertEl.textContent = 'Harap isi pesan teks wasiat atau lampirkan berkas dokumen (atau keduanya).';
    alertEl.classList.remove('hidden');
    return;
  }

  const checkedBens = Array.from(document.querySelectorAll('input[name="selected_bens"]:checked')).map(el => parseInt(el.value));
  if (checkedBens.length === 0) {
    alertEl.className = 'p-3 rounded-lg text-xs bg-rose-950/80 border border-rose-800 text-rose-200';
    alertEl.textContent = 'Pilih minimal satu ahli waris penerima wasiat.';
    alertEl.classList.remove('hidden');
    return;
  }

  const btn = document.getElementById('btn-submit-will');
  btn.disabled = true;
  btn.innerHTML = `Menyimpan &amp; Mengamankan Wasiat...`;

  try {
    const formData = new FormData();
    formData.append('asset_name', assetName);
    formData.append('beneficiary_ids', checkedBens.join(','));
    formData.append('message_content', messageContent);
    if (hasFile) {
      formData.append('file', fileInput.files[0]);
    }

    const token = window.getAuthToken ? window.getAuthToken() : '';
    const res = await fetch(`${CONFIG.API_BASE_URL}/assets/unified`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Gagal menyimpan wasiat');

    showSuccessResult(result.asset_id, result.stego_download_url || result.latest_stego_download_url);
  } catch (err) {
    alertEl.className = 'p-3 rounded-lg text-xs bg-rose-950/80 border border-rose-800 text-rose-200';
    alertEl.textContent = err.message;
    alertEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="lock" class="w-4 h-4 mr-1"></i><span>Simpan Wasiat (Pesan &amp; Berkas)</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

function showSuccessResult(assetId, downloadUrl) {
  const resultDiv = document.getElementById('success-result');
  const dlBtn = document.getElementById('btn-download-stego');
  const customBtn = document.getElementById('btn-custom-stego');

  if (downloadUrl) {
    dlBtn.href = downloadUrl;
    dlBtn.classList.remove('hidden');
  } else {
    dlBtn.classList.add('hidden');
  }

  if (assetId && customBtn) {
    customBtn.href = `access-key.html?asset_id=${assetId}`;
  }

  resultDiv.classList.remove('hidden');
  resultDiv.scrollIntoView({ behavior: 'smooth' });
  if (window.lucide) lucide.createIcons();
}

function openAddBeneficiaryModal() {
  document.getElementById('add-ben-modal').classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

function closeAddBeneficiaryModal() {
  document.getElementById('add-ben-modal').classList.add('hidden');
  document.getElementById('ben-modal-alert').classList.add('hidden');
  document.getElementById('form-quick-ben').reset();
}

async function handleQuickAddBeneficiary(e) {
  e.preventDefault();
  const alertEl = document.getElementById('ben-modal-alert');
  alertEl.classList.add('hidden');

  const btn = document.getElementById('btn-submit-quick-ben');
  btn.disabled = true;
  btn.textContent = 'Menyimpan...';

  const username = document.getElementById('ben-username').value.trim();
  const relationship = document.getElementById('ben-relationship').value.trim();

  try {
    const res = await apiFetch('/beneficiaries/add', {
      method: 'POST',
      body: JSON.stringify({
        beneficiary_username_or_email: username,
        relationship: relationship,
        consent_confirmed: true,
        reference_image_base64: null
      })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menambahkan ahli waris');

    closeAddBeneficiaryModal();
    await loadBeneficiaries();
  } catch (err) {
    alertEl.className = 'p-2.5 rounded text-xs bg-rose-950/80 border border-rose-800 text-rose-200';
    alertEl.textContent = err.message;
    alertEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Simpan';
  }
}

window.updateFileNameDisplay = updateFileNameDisplay;
window.clearSelectedFile = clearSelectedFile;
window.handleCreateWill = handleCreateWill;
window.openAddBeneficiaryModal = openAddBeneficiaryModal;
window.closeAddBeneficiaryModal = closeAddBeneficiaryModal;
window.handleQuickAddBeneficiary = handleQuickAddBeneficiary;
