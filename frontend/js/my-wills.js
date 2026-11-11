document.addEventListener('DOMContentLoaded', async () => {
  await Promise.all([loadAssets(), loadBeneficiaries()]);
});

function showAlert(msg, isError = false) {
  const el = document.getElementById('wills-alert');
  el.className = `p-4 rounded text-xs leading-relaxed ${isError ? 'bg-rose-950/80 border border-rose-800 text-rose-200' : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'}`;
  el.textContent = msg;
  el.classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function loadAssets() {
  const tbody = document.getElementById('assets-table-body');
  try {
    const res = await apiFetch('/assets/');
    if (!res.ok) throw new Error('Gagal memuat daftar aset');
    const assets = await res.json();

    if (assets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-500">Belum ada wasiat yang dibuat. Silakan buat wasiat baru.</td></tr>`;
      return;
    }

    tbody.innerHTML = assets.map(a => {
      const perms = a.permissions || [];
      const permSummary = perms.map(p => {
        const isReleased = p.release_status === 'released';
        return `
          <div class="flex items-center space-x-1.5 py-0.5">
            <span class="w-1.5 h-1.5 rounded-full ${isReleased ? 'bg-emerald-400' : 'bg-amber-400'}"></span>
            <span class="font-medium text-slate-200">${p.beneficiary_name}:</span>
            <span class="uppercase text-[10px] ${isReleased ? 'text-emerald-400 font-semibold' : 'text-amber-400'}">${p.release_status}</span>
          </div>
        `;
      }).join('');

      // Find primary stego URL
      const stegoPerm = perms.find(p => p.stego_url);
      const stegoBtn = stegoPerm && stegoPerm.stego_url ? `
        <a href="${stegoPerm.stego_url}" download class="inline-flex items-center space-x-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-willGold rounded border border-willGold/40 text-[11px] transition">
          <i data-lucide="download" class="w-3.5 h-3.5"></i>
          <span>Unduh PNG Stego</span>
        </a>
      ` : '<span class="text-slate-500 text-[10px]">-</span>';

      // Toggle buttons for each permission
      const actionButtons = perms.map(p => {
        const isReleased = p.release_status === 'released';
        return `
          <button onclick="togglePermissionRelease(${p.permission_id}, '${isReleased ? 'locked' : 'released'}')" 
                  class="px-2.5 py-1 text-[11px] rounded transition font-medium border ${isReleased ? 'bg-amber-950/40 text-amber-300 border-amber-800 hover:bg-amber-900/50' : 'bg-emerald-950/40 text-emerald-300 border-emerald-800 hover:bg-emerald-900/50'}">
            ${isReleased ? 'Kunci Kembali (Lock)' : 'Buka Akses (Release)'}
          </button>
        `;
      }).join(' ');

      return `
        <tr class="hover:bg-slate-900/40 transition">
          <td class="py-3 px-4 font-semibold text-white">
            ${a.asset_name}
            ${a.original_filename ? `<div class="text-[10px] text-slate-400 font-mono">${a.original_filename}</div>` : ''}
          </td>
          <td class="py-3 px-4">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono ${a.asset_type === 'message' ? 'bg-amber-950 text-amber-300 border border-amber-800' : 'bg-blue-950 text-blue-300 border border-blue-800'}">
              ${a.asset_type.toUpperCase()}
            </span>
          </td>
          <td class="py-3 px-4 font-mono text-[11px] text-willGold">
            ${a.encryption_algorithm}
          </td>
          <td class="py-3 px-4">
            ${permSummary || '<span class="text-slate-500">Tidak ada</span>'}
          </td>
          <td class="py-3 px-4">
            ${stegoBtn}
          </td>
          <td class="py-3 px-4">
            ${actionButtons}
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-rose-400">${err.message}</td></tr>`;
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

async function togglePermissionRelease(permId, targetStatus) {
  try {
    const res = await apiFetch('/assets/permission/release-toggle', {
      method: 'PUT',
      body: JSON.stringify({
        permission_id: permId,
        release_status: targetStatus
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mengubah status');
    showAlert(data.message, false);
    await loadAssets();
  } catch (e) {
    showAlert(e.message, true);
  }
}

async function loadBeneficiaries() {
  const tbody = document.getElementById('beneficiaries-table-body');
  try {
    const res = await apiFetch('/beneficiaries/');
    if (!res.ok) throw new Error('Gagal memuat ahli waris');
    const bens = await res.json();

    if (bens.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500">Belum ada ahli waris terdaftar.</td></tr>`;
      return;
    }

    tbody.innerHTML = bens.map(b => `
      <tr class="hover:bg-slate-900/40 transition">
        <td class="py-2.5 px-3 font-semibold text-slate-200">${b.full_name || b.username}</td>
        <td class="py-2.5 px-3 text-slate-400">${b.username} <span class="text-[10px] text-slate-500">(${b.email})</span></td>
        <td class="py-2.5 px-3 text-willGold">${b.relationship || 'Ahli Waris'}</td>
        <td class="py-2.5 px-3">
          ${b.has_reference_image ? `
            <span class="inline-flex items-center space-x-1 text-emerald-400 text-[10px] bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
              <i data-lucide="check" class="w-3 h-3"></i>
              <span>Foto Referensi Ada</span>
            </span>
          ` : `
            <span class="text-slate-500 text-[10px]">Belum Ada</span>
          `}
        </td>
        <td class="py-2.5 px-3 text-right">
          <button onclick="handleRevokeBeneficiary(${b.beneficiary_id})" class="text-rose-400 hover:text-rose-300 text-xs hover:underline">
            Cabut
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-rose-400">${err.message}</td></tr>`;
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

async function handleAddBeneficiary(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-add-ben');
  btn.disabled = true;
  btn.textContent = 'Mendaftarkan...';

  const identifier = document.getElementById('ben-identifier').value.trim();
  const relation = document.getElementById('ben-relation').value.trim();
  const fileInput = document.getElementById('ben-face-file');

  let base64Photo = null;
  if (fileInput.files && fileInput.files[0]) {
    base64Photo = await fileToBase64(fileInput.files[0]);
  }

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

    showAlert(`Ahli waris ${data.full_name || data.username} berhasil didaftarkan!`, false);
    document.getElementById('add-ben-form').reset();
    await loadBeneficiaries();
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Daftarkan Ahli Waris';
  }
}

async function handleRevokeBeneficiary(benId) {
  if (!confirm('Apakah Anda yakin ingin mencabut hak ahli waris ini?')) return;
  try {
    const res = await apiFetch(`/beneficiaries/${benId}`, { method: 'DELETE' });
    const data = await res.json();
    showAlert(data.message || 'Ahli waris dicabut', false);
    await loadBeneficiaries();
    await loadAssets();
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
