document.addEventListener('DOMContentLoaded', loadDashboardData);

async function loadDashboardData() {
  if (window.requireAuth && !window.requireAuth()) return;

  const localUser = window.getUserProfile ? window.getUserProfile() : null;

  // Tampilkan data lokal segera jika ada
  if (localUser) {
    const nameEl = document.getElementById('user-display-name');
    if (nameEl) nameEl.textContent = localUser.full_name || localUser.username;

    if (localUser.role === 'beneficiary') {
      showBeneficiaryView();
    }
  }

  try {
    const meRes = await apiFetch('/auth/me');
    if (!meRes.ok) throw new Error('Gagal memuat profil');
    const me = await meRes.json();

    const nameEl = document.getElementById('user-display-name');
    if (nameEl) nameEl.textContent = me.full_name || me.username;

    if (me.role === 'beneficiary') {
      showBeneficiaryView();
      return;
    }

    const [assetsRes, bensRes, usbRes] = await Promise.all([
      apiFetch('/assets/'),
      apiFetch('/beneficiaries/'),
      apiFetch('/usb/detect')
    ]);

    if (assetsRes.ok) {
      const assets = await assetsRes.json();
      const countEl = document.getElementById('stat-total-assets');
      if (countEl) countEl.textContent = assets.length;
      renderRecentWills(assets);
    }

    if (bensRes.ok) {
      const bens = await bensRes.json();
      const countEl = document.getElementById('stat-total-bens');
      if (countEl) countEl.textContent = bens.length;
    }

    if (usbRes && usbRes.ok) {
      const usbState = await usbRes.json();
      const usbStatEl = document.getElementById('stat-usb-status');
      if (usbStatEl) {
        if (usbState.verified) {
          usbStatEl.className = 'text-xs font-bold text-emerald-400 mt-1';
          usbStatEl.textContent = `Bootable Aktif (${usbState.active_drive})`;
        } else if (usbState.usb_plugged) {
          usbStatEl.className = 'text-xs font-bold text-willGold mt-1';
          usbStatEl.textContent = `Tercolok (${usbState.active_drive}) - Siap Pasang`;
        } else {
          usbStatEl.className = 'text-xs font-bold text-rose-400 mt-1';
          usbStatEl.textContent = 'Tidak Tercolok';
        }
      }
    }

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.warn('Dashboard fetch notice:', err);
  }
}

function showBeneficiaryView() {
  const ownerStats = document.getElementById('owner-stats');
  const ownerMenu = document.getElementById('owner-menu');
  const recentSection = document.getElementById('recent-wills-section');
  const benMenu = document.getElementById('beneficiary-menu');

  if (ownerStats) ownerStats.classList.add('hidden');
  if (ownerMenu) ownerMenu.classList.add('hidden');
  if (recentSection) recentSection.classList.add('hidden');
  if (benMenu) benMenu.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

function renderRecentWills(assets) {
  const container = document.getElementById('recent-wills-container');
  if (!container) return;

  if (!assets || assets.length === 0) {
    container.innerHTML = `
      <div class="p-6 text-center text-xs text-slate-400">
        Belum ada wasiat yang dibuat.
        <a href="create-will.html" class="text-willGold underline font-semibold ml-1">Tulis wasiat pertama Anda</a>.
      </div>
    `;
    return;
  }

  const recent = assets.slice(0, 4);

  container.innerHTML = `
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      ${recent.map(a => {
        const hasMsg = Boolean(a.has_message || a.asset_type === 'message');
        const hasDoc = Boolean(a.has_document || (a.asset_type === 'document' && a.original_filename));
        const typeStr = hasMsg && hasDoc ? 'Pesan & Berkas' : (hasDoc ? 'Dokumen' : 'Pesan Teks');
        const iconName = hasMsg && hasDoc ? 'layers' : (hasDoc ? 'file-text' : 'mail');
        const perms = a.permissions || [];
        const isReleased = perms.some(p => p.release_status === 'released');

        return `
          <div class="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-willGold">
                <i data-lucide="${iconName}" class="w-4 h-4"></i>
              </div>
              <div>
                <div class="text-xs font-semibold text-white">${esc(a.asset_name)}</div>
                <div class="text-[11px] text-slate-400">${formatDate(a.created_at)} &bull; ${typeStr}</div>
              </div>
            </div>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded border ${
              isReleased
                ? 'bg-emerald-950/60 border-emerald-800 text-emerald-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }">
              ${isReleased ? 'Siap Diklaim' : 'Terkunci'}
            </span>
          </div>
        `;
      }).join('')}
    </div>
  `;

  if (window.lucide) lucide.createIcons();
}
