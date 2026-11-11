document.addEventListener('DOMContentLoaded', async () => {
  await loadDashboardData();
});

async function loadDashboardData() {
  const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  if (!token) {
    window.location.href = 'sign-in.html';
    return;
  }

  try {
    // 1. Fetch user info
    const meRes = await apiFetch('/auth/me');
    if (!meRes.ok) throw new Error('Gagal mengambil data profil');
    const me = await meRes.json();

    document.getElementById('user-display-name').textContent = me.full_name || me.username;
    document.getElementById('user-role-badge').textContent = me.role;

    const isOwner = me.role === 'owner';

    // 2. Fetch Assets & Beneficiaries if Owner
    if (isOwner) {
      const [assetsRes, bensRes] = await Promise.all([
        apiFetch('/assets/'),
        apiFetch('/beneficiaries/')
      ]);

      if (assetsRes.ok) {
        const assets = await assetsRes.json();
        document.getElementById('stat-total-assets').textContent = assets.length;
        document.getElementById('stat-active-assets').textContent = `${assets.length} Aktif`;

        // Check if any asset is released
        let hasReleased = false;
        for (const a of assets) {
          if (a.permissions && a.permissions.some(p => p.release_status === 'released')) {
            hasReleased = true;
            break;
          }
        }
        const relEl = document.getElementById('stat-release-state');
        if (hasReleased) {
          relEl.textContent = 'Sebagian Rilis';
          relEl.className = 'text-xl font-bold text-emerald-400 font-cinzel';
        } else {
          relEl.textContent = 'Terkunci (Locked)';
          relEl.className = 'text-xl font-bold text-amber-400 font-cinzel';
        }
      }

      if (bensRes.ok) {
        const bens = await bensRes.json();
        document.getElementById('stat-total-bens').textContent = bens.length;
        const withRef = bens.filter(b => b.has_reference_image).length;
        document.getElementById('stat-bens-with-ref').textContent = `${withRef} Biometrik Terdata`;
      }
    } else {
      // Beneficiary view
      document.getElementById('stat-total-assets').textContent = 'N/A';
      document.getElementById('stat-active-assets').textContent = 'Akses Terbatas';
      document.getElementById('stat-total-bens').textContent = 'N/A';
      document.getElementById('stat-release-state').textContent = 'Klaim Mandiri';
    }

    // 3. Fetch Blockchain Stats
    const [auditRes, verifyRes] = await Promise.all([
      apiFetch('/audit/chain?limit=8'),
      apiFetch('/audit/verify')
    ]);

    if (auditRes.ok) {
      const logs = await auditRes.json();
      document.getElementById('stat-total-blocks').textContent = logs.length;
      renderRecentActivity(logs);
    }

    if (verifyRes.ok) {
      const verif = await verifyRes.json();
      const badge = document.getElementById('stat-chain-integrity');
      if (verif.is_valid) {
        badge.textContent = `Valid (${verif.total_blocks} Blok)`;
        badge.className = 'text-emerald-400';
      } else {
        badge.textContent = `Tampering Terdeteksi!`;
        badge.className = 'text-rose-400 font-bold';
      }
    }

  } catch (err) {
    console.error(err);
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

function renderRecentActivity(logs) {
  const tbody = document.getElementById('dashboard-activity-rows');
  if (!tbody) return;

  if (!logs || logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500">Belum ada aktivitas tercatat di blockchain.</td></tr>`;
    return;
  }

  tbody.innerHTML = logs.map(l => {
    const metaStr = l.event_metadata ? JSON.stringify(l.event_metadata) : '-';
    const shortHash = l.current_hash ? `${l.current_hash.substring(0, 8)}...${l.current_hash.substring(56)}` : '-';
    const dateStr = new Date(l.created_at).toLocaleString('id-ID', { hour12: false });

    return `
      <tr class="hover:bg-slate-900/50 transition">
        <td class="py-2.5 px-3 font-mono text-willGold font-bold">#${l.log_id}</td>
        <td class="py-2.5 px-3">
          <span class="inline-block px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono border border-slate-700">
            ${l.activity_type}
          </span>
        </td>
        <td class="py-2.5 px-3 text-slate-400 max-w-xs truncate font-mono text-[11px]" title='${metaStr}'>
          ${metaStr}
        </td>
        <td class="py-2.5 px-3 font-mono text-slate-400 text-[11px]" title="${l.current_hash}">
          ${shortHash}
        </td>
        <td class="py-2.5 px-3 text-slate-400 whitespace-nowrap text-[11px]">
          ${dateStr}
        </td>
      </tr>
    `;
  }).join('');
}
