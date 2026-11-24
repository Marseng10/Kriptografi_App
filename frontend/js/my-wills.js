let allAssets = [];
let currentFilter = 'all';

document.addEventListener('DOMContentLoaded', async () => {
  if (window.requireAuth && !window.requireAuth('owner')) return;
  await Promise.all([loadAssets(), loadBeneficiaries()]);
  if (window.lucide) lucide.createIcons();
});

function showAlert(msg, isError = false) {
  const el = document.getElementById('wills-alert');
  el.className = `p-3 rounded-lg text-xs leading-relaxed ${
    isError
      ? 'bg-rose-950/80 border border-rose-800 text-rose-200'
      : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'
  }`;
  el.textContent = msg;
  el.classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadAssets() {
  const box = document.getElementById('assets-list');
  try {
    const res = await apiFetch('/assets/');
    if (!res.ok) throw new Error('Gagal memuat daftar wasiat');
    allAssets = await res.json();
    renderAssets();
  } catch (err) {
    box.innerHTML = `<div class="will-card p-5 rounded-lg text-xs text-rose-400">${esc(err.message)}</div>`;
  }
}

function setFilter(filter) {
  currentFilter = filter;
  ['all', 'released', 'locked'].forEach(f => {
    const btn = document.getElementById(`filter-${f}`);
    if (btn) {
      if (f === filter) {
        btn.className = 'px-3 py-1 rounded bg-willGold text-ink-dark font-medium transition';
      } else {
        btn.className = 'px-3 py-1 rounded bg-slate-800 text-slate-300 hover:text-white transition';
      }
    }
  });
  renderAssets();
}

function renderAssets() {
  const box = document.getElementById('assets-list');
  if (!box) return;

  let filtered = allAssets.filter(a => {
    const perms = a.permissions || [];
    const isReleased = perms.some(p => p.release_status === 'released');
    if (currentFilter === 'released' && !isReleased) return false;
    if (currentFilter === 'locked' && isReleased) return false;
    return true;
  });

  if (filtered.length === 0) {
    box.innerHTML = `
      <div class="will-card p-8 rounded-xl text-center text-xs text-slate-400">
        ${allAssets.length === 0
          ? 'Belum ada wasiat tersimpan. <a href="create-will.html" class="text-willGold underline font-semibold ml-1">Tulis wasiat sekarang</a>.'
          : 'Tidak ada wasiat yang sesuai dengan filter yang dipilih.'}
      </div>
    `;
    return;
  }

  box.innerHTML = filtered.map(a => {
    const hasMsg = Boolean(a.has_message || a.asset_type === 'message');
    const hasDoc = Boolean(a.has_document || (a.asset_type === 'document' && a.original_filename));
    const typeLabel = hasMsg && hasDoc
      ? `Pesan & Berkas (${esc(a.original_filename || 'Dokumen')})`
      : (hasDoc ? `Dokumen: ${esc(a.original_filename || '')}` : 'Pesan Teks');
    const iconName = hasMsg && hasDoc ? 'layers' : (hasDoc ? 'file-text' : 'mail');
    const perms = a.permissions || [];

    const rows = perms.map(p => {
      const released = p.release_status === 'released';
      return `
        <div class="flex flex-wrap items-center justify-between gap-2 py-2.5 border-t border-slate-800 first:border-t-0">
          <div class="text-xs">
            <span class="font-medium text-slate-200">${esc(p.beneficiary_name)}</span>
            <span class="ml-2 text-[10px] font-mono px-2 py-0.5 rounded border ${
              released
                ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                : 'bg-amber-950/60 border-amber-800 text-amber-300'
            }">
              ${released ? 'Siap Diklaim' : 'Terkunci'}
            </span>
          </div>
          <div class="flex items-center gap-2">
            ${p.stego_url ? `
              <a href="${p.stego_url}" download="kartu_akses_${esc(p.beneficiary_name)}.png"
                 class="px-2.5 py-1 text-[11px] bg-slate-800 hover:bg-slate-700 text-willGold rounded border border-willGold/40 transition">
                Unduh Kartu Akses
              </a>
            ` : ''}
            <button onclick="togglePermissionRelease(${p.permission_id}, '${released ? 'locked' : 'released'}')"
              class="px-2.5 py-1 text-[11px] rounded border transition ${
                released
                  ? 'text-amber-300 border-amber-800 hover:bg-amber-900/40'
                  : 'text-emerald-300 border-emerald-800 hover:bg-emerald-900/40'
              }">
              ${released ? 'Kunci Kembali' : 'Izinkan Buka'}
            </button>
          </div>
        </div>
      `;
    }).join('');

    return `
      <div class="will-card p-5 rounded-xl space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-willGold">
              <i data-lucide="${iconName}" class="w-4 h-4"></i>
            </div>
            <div>
              <div class="font-semibold text-white text-sm">${esc(a.asset_name)}</div>
              <div class="text-[11px] text-slate-400">
                ${typeLabel} &bull; ${formatDate(a.created_at)}
              </div>
            </div>
          </div>
          <div class="flex items-center space-x-2 self-end sm:self-auto">
            <a href="access-key.html?asset_id=${a.asset_id}" class="text-[11px] text-willGold hover:underline px-2 py-1 rounded hover:bg-slate-800">
              Ganti Foto Kunci
            </a>
            <button onclick="handleDeleteAsset(${a.asset_id}, '${esc(a.asset_name)}')" class="text-[11px] text-rose-400 hover:text-rose-300 px-2 py-1 rounded hover:bg-slate-800" title="Hapus Wasiat">
              Hapus
            </button>
          </div>
        </div>

        <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
          <div class="text-[10px] uppercase font-mono tracking-wider text-slate-500 mb-1">Penerima &amp; Hak Akses:</div>
          ${rows || '<div class="text-xs text-slate-500">Belum ada penerima ditugaskan.</div>'}
        </div>
      </div>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

async function togglePermissionRelease(permId, targetStatus) {
  try {
    const res = await apiFetch('/assets/permission/release-toggle', {
      method: 'PUT',
      body: JSON.stringify({ permission_id: permId, release_status: targetStatus })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mengubah status');
    showAlert(targetStatus === 'released' ? 'Wasiat kini diizinkan untuk dibuka oleh ahli waris.' : 'Wasiat dikunci kembali.');
    await loadAssets();
  } catch (e) {
    showAlert(e.message, true);
  }
}

async function handleDeleteAsset(assetId, assetName) {
  if (!confirm(`Hapus wasiat "${assetName}"? Tindakan ini tidak dapat dibatalkan.`)) return;
  try {
    const res = await apiFetch(`/assets/${assetId}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal menghapus');
    }
    showAlert(`Wasiat "${assetName}" berhasil dihapus.`);
    await loadAssets();
  } catch (err) {
    showAlert(err.message, true);
  }
}

async function loadBeneficiaries() {
  const box = document.getElementById('beneficiaries-list');
  try {
    const res = await apiFetch('/beneficiaries/');
    if (!res.ok) throw new Error('Gagal memuat ahli waris');
    const bens = await res.json();

    if (bens.length === 0) {
      box.innerHTML = `<div class="will-card p-4 text-center text-xs text-slate-500">Belum ada ahli waris terdaftar.</div>`;
      return;
    }

    box.innerHTML = bens.map(b => `
      <div class="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex items-center justify-between gap-3">
        <div>
          <div class="text-xs font-semibold text-white">${esc(b.full_name || b.username)}</div>
          <div class="text-[11px] text-slate-400">
            ${esc(b.relationship || 'Ahli waris')} &bull; @${esc(b.username)}
          </div>
          <div class="mt-1">
            ${b.has_reference_image
              ? '<span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">Foto Ada</span>'
              : '<span class="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">Belum Ada Foto</span>'}
          </div>
        </div>
        <button onclick="handleRevokeBeneficiary(${b.beneficiary_id}, '${esc(b.full_name || b.username)}')" class="text-xs text-rose-400 hover:text-rose-300 hover:underline">
          Hapus
        </button>
      </div>
    `).join('');
  } catch (err) {
    box.innerHTML = `<div class="text-xs text-rose-400">${esc(err.message)}</div>`;
  }
}

async function handleAddBeneficiary(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-submit-ben');
  btn.disabled = true;
  btn.textContent = 'Menyimpan...';

  const username = document.getElementById('modal-ben-username').value.trim();
  const relationship = document.getElementById('modal-ben-relationship').value.trim();
  const photoInput = document.getElementById('modal-ben-photo');

  let base64Photo = null;
  if (photoInput.files && photoInput.files[0]) {
    try {
      base64Photo = await fileToBase64(photoInput.files[0]);
    } catch (e) {
      console.warn('Gagal membaca foto:', e);
    }
  }

  try {
    const res = await apiFetch('/beneficiaries/add', {
      method: 'POST',
      body: JSON.stringify({
        beneficiary_username_or_email: username,
        relationship: relationship,
        consent_confirmed: true,
        reference_image_base64: base64Photo
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menambahkan ahli waris');

    showAlert(`Ahli waris "${username}" berhasil ditambahkan.`);
    document.getElementById('form-add-ben').reset();
    await loadBeneficiaries();
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Simpan Ahli Waris';
  }
}

async function handleRevokeBeneficiary(benId, name) {
  if (!confirm(`Hapus ahli waris "${name}" dari daftar?`)) return;
  try {
    const res = await apiFetch(`/beneficiaries/${benId}/revoke`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal menghapus');
    }
    showAlert(`Ahli waris "${name}" berhasil dihapus.`);
    await loadBeneficiaries();
  } catch (e) {
    showAlert(e.message, true);
  }
}

window.setFilter = setFilter;
window.togglePermissionRelease = togglePermissionRelease;
window.handleDeleteAsset = handleDeleteAsset;
window.handleAddBeneficiary = handleAddBeneficiary;
window.handleRevokeBeneficiary = handleRevokeBeneficiary;
