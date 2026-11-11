document.addEventListener('DOMContentLoaded', async () => {
  await loadBlockchain();
});

async function loadBlockchain() {
  const container = document.getElementById('blockchain-container');
  try {
    const res = await apiFetch('/audit/chain?limit=50');
    if (!res.ok) throw new Error('Gagal memuat rantai audit');
    const logs = await res.json();

    document.getElementById('stat-blocks-count').textContent = `${logs.length} Blok`;
    if (logs.length > 0) {
      document.getElementById('stat-latest-hash').textContent = logs[0].current_hash;
    }

    if (logs.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-slate-500 will-card rounded-lg">Belum ada blok audit tercatat di sistem.</div>`;
      return;
    }

    container.innerHTML = logs.map((block, idx) => {
      const isGenesis = !block.previous_hash || block.previous_hash.startsWith('0000000000');
      const dateStr = new Date(block.created_at).toLocaleString('id-ID', { hour12: false });
      const meta = block.event_metadata ? JSON.stringify(block.event_metadata, null, 2) : '{}';

      return `
        <div class="will-card rounded-lg p-5 border-l-4 ${isGenesis ? 'border-l-purple-500' : 'border-l-willGold'} space-y-3">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-2.5 gap-2">
            <div class="flex items-center space-x-2">
              <span class="px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-800 text-willGold border border-willGold/40">
                BLOK #${block.log_id}
              </span>
              <span class="text-xs font-semibold text-white uppercase tracking-wider font-mono">
                ${block.activity_type}
              </span>
              ${isGenesis ? '<span class="text-[10px] bg-purple-950 text-purple-300 px-2 py-0.5 rounded border border-purple-800 font-mono">GENESIS</span>' : ''}
            </div>
            <div class="text-[11px] text-slate-400 font-mono">
              ${dateStr}
            </div>
          </div>

          <!-- Hashes -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
            <div class="bg-black/40 p-2.5 rounded border border-slate-800/80">
              <span class="text-slate-500 block text-[10px] uppercase font-semibold">Previous Hash:</span>
              <span class="text-slate-400 break-all select-all">${block.previous_hash || 'GENESIS (0x000...)'}</span>
            </div>
            <div class="bg-black/40 p-2.5 rounded border border-slate-800/80">
              <span class="text-willGold block text-[10px] uppercase font-semibold">Current Block Hash:</span>
              <span class="text-emerald-300 break-all select-all font-semibold">${block.current_hash}</span>
            </div>
          </div>

          <!-- Metadata -->
          <details class="text-xs">
            <summary class="cursor-pointer text-slate-400 hover:text-willGold font-mono text-[11px] select-none">
              &gt; Lihat Detail Data Blok
            </summary>
            <pre class="mt-2 p-3 bg-black/60 rounded border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto">${meta}</pre>
          </details>
        </div>
      `;
    }).join('');

  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-400 will-card rounded-lg">${err.message}</div>`;
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

async function runChainVerification() {
  const banner = document.getElementById('chain-verif-banner');
  const btn = document.getElementById('btn-verify-chain');
  btn.disabled = true;
  btn.textContent = 'Memverifikasi Rantai SHA-256...';

  try {
    const res = await apiFetch('/audit/verify');
    const data = await res.json();

    if (data.is_valid) {
      banner.className = 'p-4 rounded-lg text-xs leading-relaxed bg-emerald-950/80 border border-emerald-700 text-emerald-200 block';
      banner.innerHTML = `
        <div class="font-bold text-sm text-white mb-1">Integritas Blockchain Berhasil Diverifikasi!</div>
        <div>${data.details}</div>
        <div class="mt-1 font-mono text-[10px] text-emerald-400">Total Blok Diverifikasi: ${data.total_blocks} &bull; Tanda tangan signature kriptografis utuh.</div>
      `;
    } else {
      banner.className = 'p-4 rounded-lg text-xs leading-relaxed bg-rose-950/80 border border-rose-700 text-rose-200 block';
      banner.innerHTML = `
        <div class="font-bold text-sm text-white mb-1">PERINGATAN: Modifikasi Tak Sah Terdeteksi!</div>
        <div>${data.details}</div>
        <div class="mt-1 font-mono text-[10px] text-rose-300">Rantai terputus pada blok: #${data.broken_at_block}</div>
      `;
    }
  } catch (err) {
    banner.className = 'p-4 rounded-lg text-xs leading-relaxed bg-rose-950/80 border border-rose-700 text-rose-200 block';
    banner.textContent = 'Gagal memverifikasi: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="shield-check" class="w-4 h-4 mr-2"></i><span>Verifikasi Integritas Chain</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

window.runChainVerification = runChainVerification;
