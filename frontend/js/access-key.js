let availableAssets = [];
let selectedCarrierFile = null;

document.addEventListener('DOMContentLoaded', async () => {
  if (window.requireAuth && !window.requireAuth('owner')) return;
  await loadAssetsForAccessKey();
  if (window.lucide) lucide.createIcons();
});

function showAlert(msg, isError = false) {
  const el = document.getElementById('access-alert');
  el.className = `p-3 rounded-lg text-xs leading-relaxed ${
    isError
      ? 'bg-rose-950/80 border border-rose-800 text-rose-200'
      : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'
  }`;
  el.textContent = msg;
  el.classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadAssetsForAccessKey() {
  const selectAsset = document.getElementById('select-asset');
  try {
    const res = await apiFetch('/assets/');
    if (!res.ok) throw new Error('Gagal memuat daftar wasiat');
    availableAssets = await res.json();

    if (availableAssets.length === 0) {
      selectAsset.innerHTML = '<option value="">Belum ada wasiat. Buat wasiat terlebih dahulu.</option>';
      return;
    }

    selectAsset.innerHTML = '<option value="">-- Pilih Wasiat --</option>' +
      availableAssets.map(a => {
        const hasMsg = Boolean(a.has_message || a.asset_type === 'message');
        const hasDoc = Boolean(a.has_document || (a.asset_type === 'document' && a.original_filename));
        const typeStr = hasMsg && hasDoc ? 'Pesan & Berkas' : (hasDoc ? 'Dokumen' : 'Pesan');
        return `<option value="${a.asset_id}">${esc(a.asset_name)} (${typeStr})</option>`;
      }).join('');

    const urlParams = new URLSearchParams(window.location.search);
    const preselectedId = urlParams.get('asset_id');
    if (preselectedId) {
      selectAsset.value = preselectedId;
      onAssetSelected();
    }
  } catch (err) {
    showAlert(err.message, true);
  }
}

function onAssetSelected() {
  const selectAsset = document.getElementById('select-asset');
  const selectBen = document.getElementById('select-beneficiary');
  const assetId = selectAsset.value;

  if (!assetId) {
    selectBen.innerHTML = '<option value="">Pilih wasiat terlebih dahulu</option>';
    return;
  }

  const asset = availableAssets.find(a => String(a.asset_id) === String(assetId));
  if (!asset || !asset.permissions || asset.permissions.length === 0) {
    selectBen.innerHTML = '<option value="">Tidak ada ahli waris pada wasiat ini</option>';
    return;
  }

  selectBen.innerHTML = asset.permissions.map(p =>
    `<option value="${p.beneficiary_id}">${esc(p.beneficiary_name)} (${p.release_status === 'released' ? 'Siap Diklaim' : 'Terkunci'})</option>`
  ).join('');
}

function onCarrierFileChange(input) {
  if (input.files && input.files[0]) {
    selectedCarrierFile = input.files[0];
    document.getElementById('carrier-filename-label').textContent = selectedCarrierFile.name;
    document.getElementById('carrier-status-tag').textContent = `${(selectedCarrierFile.size / (1024 * 1024)).toFixed(2)} MB &bull; Loaded`;

    const reader = new FileReader();
    reader.onload = (e) => {
      document.getElementById('carrier-preview-image').src = e.target.result;
    };
    reader.readAsDataURL(selectedCarrierFile);
  }
}

async function handleGenerateAccessKey(e) {
  e.preventDefault();
  document.getElementById('access-alert').classList.add('hidden');
  document.getElementById('key-result-box').classList.add('hidden');

  const assetId = document.getElementById('select-asset').value;
  const beneficiaryId = document.getElementById('select-beneficiary').value;

  if (!assetId || !beneficiaryId) {
    showAlert('Silakan pilih wasiat dan ahli waris terlebih dahulu.', true);
    return;
  }

  const btn = document.getElementById('btn-generate-key');
  btn.disabled = true;
  btn.innerHTML = `Menyematkan Kunci...`;

  const formData = new FormData();
  formData.append('beneficiary_id', beneficiaryId);
  if (selectedCarrierFile) {
    formData.append('photo', selectedCarrierFile);
  }

  const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/assets/${assetId}/access-key`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal membuat kartu akses');

    const downloadBtn = document.getElementById('download-key-btn');
    downloadBtn.href = data.download_url;
    downloadBtn.download = data.filename || 'kartu_akses.png';

    const resultBox = document.getElementById('key-result-box');
    resultBox.classList.remove('hidden');
    resultBox.scrollIntoView({ behavior: 'smooth' });
    showAlert('Kunci rahasia berhasil disematkan ke dalam foto!');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="key" class="w-4 h-4 mr-1.5 inline"></i><span>Sisipkan Kunci ke Foto</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

window.onAssetSelected = onAssetSelected;
window.onCarrierFileChange = onCarrierFileChange;
window.handleGenerateAccessKey = handleGenerateAccessKey;
