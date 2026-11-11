document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([loadAssets(), loadBeneficiaries()]);
});

function showAlert(msg, isError = false) {
  const el = document.getElementById('wills-alert');
  el.className = `p-3 rounded text-sm ${isError ? 'bg-rose-950/80 border border-rose-800 text-rose-200' : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'}`;
  el.textContent = msg;
  el.classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function loadAssets() {
  const box = document.getElementById('assets-list');
  try {
    const res = await apiFetch('/assets/');
    if (!res.ok) throw new Error('Gagal memuat daftar wasiat');
    const assets = await res.json();

    if (assets.length === 0) {
      box.innerHTML = `<div class="will-card p-6 rounded-lg text-sm text-slate-400">Belum ada wasiat. <a href="create-will.html" class="text-willGold underline">Tulis wasiat pertama Anda</a>.</div>`;
      return;
    }

    box.innerHTML = assets.map(a => {
      const rows = (a.permissions || []).map(p => {
        const released = p.release_status === 'released';
        return `
          <div class="flex flex-wrap items-center justify-between gap-2 py-2 border-t border-slate-800 first:border-t-0">
            <div class="text-sm">
              <span class="text-slate-200">${esc(p.beneficiary_name)}</span>
              <span class="ml-2 text-xs ${released ? 'text-emerald-400' : 'text-amber-400'}">${released ? 'Boleh dibuka' : 'Terkunci'}</span>
            </div>
            <div class="flex items-center gap-2">
              ${p.stego_url ? `<a href="${p.stego_url}" download class="px-3 py-1 text-xs bg-slate-800 hover:bg-slate-700 text-willGold rounded border border-willGold/40">Unduh Kartu Akses</a>` : ''}
              <button onclick="togglePermissionRelease(${p.permission_id}, '${released ? 'locked' : 'released'}')"
                class="px-3 py-1 text-xs rounded border ${released ? 'text-amber-300 border-amber-800 hover:bg-amber-900/40' : 'text-emerald-300 border-emerald-800 hover:bg-emerald-900/40'}">
                ${released ? 'Kunci' : 'Izinkan Dibuka'}
              </button>
            </div>
          </div>`;
      }).join('');

      return `
        <div class="will-card p-5 rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <div>
              <div class="font-semibold text-white">${esc(a.asset_name)}</div>
              <div class="text-xs text-slate-400">${a.asset_type === 'message' ? 'Pesan teks' : 'Dokumen: ' + esc(a.original_filename || '')}</div>
            </div>
          </div>
          ${rows || '<div class="text-sm text-slate-500">Belum ada penerima.</div>'}
        </div>`;
    }).join('');
  } catch (err) {
    box.innerHTML = `<div class="will-card p-6 rounded-lg text-sm text-rose-400">${esc(err.message)}</div>`;
  }
}

async function togglePermissionRelease(permId, targetStatus) {
  try {
    const res = await apiFetch('/assets/permission/release-toggle', {
      method: 'PUT',
      body: JSON.stringify({ permission_id: permId, release_status: targetStatus })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mengubah status');
    showAlert(targetStatus === 'released' ? 'Wasiat kini boleh dibuka oleh ahli waris.' : 'Wasiat dikunci kembali.');
    await loadAssets();
  } catch (e) {
    showAlert(e.message, true);
  }
}

async function loadBeneficiaries() {
  const box = document.getElementById('beneficiaries-list');
  try {
    const res = await apiFetch('/beneficiaries/');
    if (!res.ok) throw new Error('Gagal memuat ahli waris');
    const bens = await res.json();

    if (bens.length === 0) {
      box.innerHTML = `<div class="text-sm text-slate-500">Belum ada ahli waris.</div>`;
      return;
    }

    box.innerHTML = bens.map(b => `
      <div class="flex items-center justify-between gap-3 p-3 bg-slate-900/60 border border-slate-800 rounded">
        <div>
          <div class="text-sm font-medium text-white">${esc(b.full_name || b.username)}</div>
          <div class="text-xs text-slate-400">${esc(b.relationship || 'Ahli waris')} &bull; ${b.has_reference_image ? 'Foto wajah ada' : 'Belum ada foto wajah'}</div>
        </div>
        <button onclick="handleRevokeBeneficiary(${b.beneficiary_id})" class="text-xs text-rose-400 hover:underline">Hapus</button>
      </div>`).join('');
  } catch (err) {
    box.innerHTML = `<div class="text-sm text-rose-400">${esc(err.message)}</div>`;
  }
}

async function handleAddBeneficiary(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-add-ben');
  btn.disabled = true;
  btn.textContent = 'Menyimpan...';

  const identifier = document.getElementById('ben-identifier').value.trim();
  const relation = document.getElementById('ben-relation').value.trim();
  const fileInput = document.getElementById('ben-face-file');
  const base64Photo = fileInput.files && fileInput.files[0] ? await fileToBase64(fileInput.files[0]) : null;

  try {
    const res = await apiFetch('/beneficiaries/add', {
      method: 'POST',
      body: JSON.stringify({
        beneficiary_username_or_email: identifier,
        relationship: relation,
        consent_confirmed: true,
        reference_image_base64: base64Photo
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menambahkan ahli waris');

    showAlert(`${data.full_name || data.username} berhasil ditambahkan sebagai ahli waris.`);
    document.getElementById('add-ben-form').reset();
    await loadBeneficiaries();
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Tambah';
  }
}

async function handleRevokeBeneficiary(benId) {
  if (!confirm('Hapus ahli waris ini?')) return;
  try {
    const res = await apiFetch(`/beneficiaries/${benId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menghapus');
    showAlert('Ahli waris dihapus.');
    await Promise.all([loadBeneficiaries(), loadAssets()]);
  } catch (e) {
    showAlert(e.message, true);
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

window.togglePermissionRelease = togglePermissionRelease;
window.handleAddBeneficiary = handleAddBeneficiary;
window.handleRevokeBeneficiary = handleRevokeBeneficiary;
