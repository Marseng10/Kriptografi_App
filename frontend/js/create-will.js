document.addEventListener('DOMContentLoaded', async () => {
  await loadBeneficiaries();
});

let currentBeneficiaries = [];

function toggleAssetType(type) {
  const msgContainer = document.getElementById('container-message-input');
  const docContainer = document.getElementById('container-document-input');

  if (type === 'message') {
    msgContainer.classList.remove('hidden');
    docContainer.classList.add('hidden');
  } else {
    msgContainer.classList.add('hidden');
    docContainer.classList.remove('hidden');
  }
}

function updateFileNameDisplay(input) {
  const label = document.getElementById('file-label-text');
  if (input.files && input.files[0]) {
    label.textContent = `Berkas dipilih: ${input.files[0].name} (${(input.files[0].size / 1024).toFixed(1)} KB)`;
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
        <div class="text-xs text-amber-300 py-2">
          Belum ada ahli waris terdaftar. <a href="my-wills.html" class="underline font-semibold text-willGold">Tambah ahli waris terlebih dahulu</a>.
        </div>
      `;
      return;
    }

    listEl.innerHTML = currentBeneficiaries.map(b => `
      <label class="flex items-center space-x-3 p-2 rounded hover:bg-slate-800/80 cursor-pointer text-xs">
        <input type="checkbox" name="selected_bens" value="${b.beneficiary_id}" checked class="rounded text-willGold focus:ring-0">
        <div class="flex-1">
          <span class="font-semibold text-slate-200">${b.full_name || b.username}</span>
          <span class="text-slate-400">(${b.relationship || 'Ahli Waris'})</span>
        </div>
        ${b.has_reference_image ? '<span class="text-[10px] text-emerald-400 font-mono">Biometrik Wajah Aktif</span>' : '<span class="text-[10px] text-slate-500">Tanpa Foto Ref</span>'}
      </label>
    `).join('');
  } catch (err) {
    listEl.innerHTML = `<div class="text-xs text-rose-400 py-2">${err.message}</div>`;
  }
}

async function handleCreateWill(e) {
  e.preventDefault();
  const alertEl = document.getElementById('create-alert');
  alertEl.classList.add('hidden');

  const btn = document.getElementById('btn-submit-will');
  btn.disabled = true;
  btn.textContent = 'Memproses Enkripsi & Steganografi...';

  const assetType = document.querySelector('input[name="asset_type"]:checked').value;
  const assetName = document.getElementById('asset-name').value.trim();

  // Get selected beneficiaries
  const checkedBens = Array.from(document.querySelectorAll('input[name="selected_bens"]:checked')).map(el => parseInt(el.value));
  if (checkedBens.length === 0) {
    alertEl.className = 'mb-6 p-4 rounded text-xs bg-rose-950/80 border border-rose-800 text-rose-200';
    alertEl.textContent = 'Pilih minimal satu ahli waris penerima wasiat.';
    alertEl.classList.remove('hidden');
    btn.disabled = false;
    btn.textContent = 'Enkripsi & Hasilkan Gambar Steganografi';
    return;
  }

  try {
    let result = null;

    if (assetType === 'message') {
      const messageContent = document.getElementById('message-content').value.trim();
      if (!messageContent) throw new Error('Isi pesan rahasia tidak boleh kosong');

      const res = await apiFetch('/assets/message', {
        method: 'POST',
        body: JSON.stringify({
          asset_name: assetName,
          message_content: messageContent,
          beneficiary_ids: checkedBens
        })
      });

      result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Gagal mengenkripsi pesan');

      showSuccessResult(result.encryption_algorithm, result.latest_stego_download_url);
    } else {
      // Document upload
      const fileInput = document.getElementById('document-file');
      if (!fileInput.files || !fileInput.files[0]) {
        throw new Error('Pilih berkas dokumen yang ingin dienkripsi');
      }

      const formData = new FormData();
      formData.append('asset_name', assetName);
      formData.append('beneficiary_ids', checkedBens.join(','));
      formData.append('file', fileInput.files[0]);

      const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
      const res = await fetch(`${CONFIG.API_BASE_URL}/assets/document`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      result = await res.json();
      if (!res.ok) throw new Error(result.detail || 'Gagal mengenkripsi dokumen');

      showSuccessResult(result.encryption_algorithm, result.stego_download_url);
    }
  } catch (err) {
    alertEl.className = 'mb-6 p-4 rounded text-xs bg-rose-950/80 border border-rose-800 text-rose-200';
    alertEl.textContent = err.message;
    alertEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="shield" class="w-4 h-4 mr-2"></i><span>Enkripsi & Hasilkan Gambar Steganografi</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

function showSuccessResult(algo, downloadUrl) {
  const resultDiv = document.getElementById('success-result');
  document.getElementById('res-algo').textContent = algo;
  const dlBtn = document.getElementById('btn-download-stego');

  if (downloadUrl) {
    dlBtn.href = downloadUrl;
    dlBtn.classList.remove('hidden');
  } else {
    dlBtn.classList.add('hidden');
  }

  resultDiv.classList.remove('hidden');
  resultDiv.scrollIntoView({ behavior: 'smooth' });
}

window.toggleAssetType = toggleAssetType;
window.updateFileNameDisplay = updateFileNameDisplay;
window.handleCreateWill = handleCreateWill;
