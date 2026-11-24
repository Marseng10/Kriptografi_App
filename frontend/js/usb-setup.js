document.addEventListener('DOMContentLoaded', async () => {
  if (window.requireAuth && !window.requireAuth('owner')) return;
  await Promise.all([checkLiveUsbPort(), loadUsbDevices()]);
  setInterval(checkLiveUsbPort, 3000);
  if (window.lucide) lucide.createIcons();
});

function showAlert(msg, isError = false) {
  const el = document.getElementById('usb-alert');
  el.className = `p-3.5 rounded-lg text-xs leading-relaxed ${
    isError
      ? 'bg-rose-950/80 border border-rose-800 text-rose-200'
      : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'
  }`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

async function checkLiveUsbPort() {
  const card = document.getElementById('live-usb-card');
  const iconBox = document.getElementById('live-usb-icon-box');
  const dot = document.getElementById('live-usb-dot');
  const title = document.getElementById('live-usb-title');
  const desc = document.getElementById('live-usb-desc');
  const badge = document.getElementById('live-usb-badge');
  const btnText = document.getElementById('btn-reg-usb-text');

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/usb/detect`);
    if (!res.ok) return;
    const state = await res.json();

    if (state.usb_plugged) {
      const driveStr = state.active_drive || 'USB';
      const labelStr = state.active_label || 'Flashdisk';

      card.className = 'will-card p-5 rounded-xl border border-emerald-700/60 bg-emerald-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4';
      iconBox.className = 'w-12 h-12 rounded-xl bg-emerald-950 border border-emerald-600/50 flex items-center justify-center text-emerald-400';
      dot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse';
      title.textContent = `Flashdisk Terhubung di Drive ${driveStr} (${labelStr})`;

      if (state.verified) {
        desc.textContent = `Berkas wariscrypt.key aktif & terverifikasi untuk akun @${state.owner_username} (${state.device_name}).`;
        badge.className = 'px-3 py-1.5 rounded-lg bg-emerald-950 border border-emerald-700 text-xs font-mono text-emerald-300 self-start sm:self-center';
        badge.textContent = `BOOTABLE AKTIF (${driveStr})`;
      } else {
        desc.textContent = `Flashdisk siap dipasangi kunci bootable wariscrypt.key & Boot_WARISCRYPT.bat.`;
        badge.className = 'px-3 py-1.5 rounded-lg bg-amber-950/80 border border-amber-700 text-xs font-mono text-amber-300 self-start sm:self-center';
        badge.textContent = `SIap DIPASANG (${driveStr})`;
      }

      if (btnText) {
        btnText.textContent = `Buat & Pasang Kunci Bootable Langsung ke Flashdisk (${driveStr})`;
      }
    } else {
      card.className = 'will-card p-5 rounded-xl border border-rose-800/60 bg-rose-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4';
      iconBox.className = 'w-12 h-12 rounded-xl bg-rose-950 border border-rose-700/50 flex items-center justify-center text-rose-400';
      dot.className = 'w-2.5 h-2.5 rounded-full bg-rose-400 animate-ping';
      title.textContent = 'Tidak Ada Flashdisk yang Tercolok di Port USB';
      desc.textContent = 'Colokkan Flashdisk Anda ke port USB komputer agar kunci bootable dapat dipasang langsung.';
      badge.className = 'px-3 py-1.5 rounded-lg bg-rose-950 border border-rose-800 text-xs font-mono text-rose-300 self-start sm:self-center';
      badge.textContent = 'USB TIDAK TERDETEKSI';

      if (btnText) {
        btnText.textContent = 'Buat & Unduh Kunci wariscrypt.key';
      }
    }
  } catch (e) {
    // ignore transient network errors
  }
}

async function loadUsbDevices() {
  const tbody = document.getElementById('usb-devices-tbody');
  try {
    const res = await apiFetch('/usb/');
    if (!res.ok) throw new Error('Gagal memuat perangkat');
    const devices = await res.json();

    if (devices.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500">Belum ada perangkat flashdisk yang didaftarkan. Klik tombol di atas untuk memasang kunci ke Flashdisk Anda.</td></tr>`;
      return;
    }

    tbody.innerHTML = devices.map(d => `
      <tr class="hover:bg-slate-900/50 transition">
        <td class="py-3 px-3 font-semibold text-white">
          <div class="flex items-center space-x-2">
            <span>${esc(d.device_name)}</span>
            ${d.is_currently_plugged ? `
              <span class="px-2 py-0.5 rounded-full text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-700 font-mono flex items-center space-x-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>TERCOLOK</span>
              </span>
            ` : ''}
          </div>
        </td>
        <td class="py-3 px-3 font-mono text-[11px] text-willGold">${esc(d.device_fingerprint)}</td>
        <td class="py-3 px-3">
          <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase font-mono">
            ${esc(d.device_status)}
          </span>
        </td>
        <td class="py-3 px-3 text-slate-400 text-[11px] font-mono">
          ${d.last_used_at ? formatDate(d.last_used_at) : 'Baru dibuat'}
        </td>
        <td class="py-3 px-3 text-right space-x-1.5 whitespace-nowrap">
          <button onclick="installKeyToPluggedUsb(${d.device_id})"
             title="Pasang berkas wariscrypt.key & Boot_WARISCRYPT.bat langsung ke Flashdisk yang tercolok"
             class="px-2.5 py-1 text-[11px] bg-willGold/20 hover:bg-willGold/30 text-willGold rounded border border-willGold/40 transition inline-flex items-center space-x-1 cursor-pointer">
            <i data-lucide="usb" class="w-3 h-3"></i>
            <span>Pasang ke USB</span>
          </button>
          <button onclick="downloadKeyFile(${d.device_id})"
             class="px-2.5 py-1 text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition inline-flex items-center space-x-1 cursor-pointer">
            <i data-lucide="download" class="w-3 h-3"></i>
            <span>Unduh .key</span>
          </button>
          <button onclick="deleteUsbDevice(${d.device_id})"
             class="px-2 py-1 text-[11px] bg-rose-950/60 hover:bg-rose-900/60 text-rose-300 rounded border border-rose-800/60 transition inline-flex items-center cursor-pointer"
             title="Hapus kunci ini">
            <i data-lucide="trash-2" class="w-3 h-3"></i>
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-rose-400">${esc(err.message)}</td></tr>`;
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

async function installKeyToPluggedUsb(deviceId) {
  try {
    const res = await apiFetch(`/usb/install-to-drive/${deviceId}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal memasang kunci ke Flashdisk');
    showAlert(data.message, false);
    await Promise.all([checkLiveUsbPort(), loadUsbDevices()]);
  } catch (err) {
    showAlert(err.message, true);
  }
}

async function deleteUsbDevice(deviceId) {
  if (!confirm('Hapus kunci Flashdisk ini? Jika dihapus, kunci ini tidak akan bisa digunakan untuk login lagi.')) return;
  try {
    const res = await apiFetch(`/usb/${deviceId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal menghapus perangkat');
    showAlert(data.message, false);
    await Promise.all([checkLiveUsbPort(), loadUsbDevices()]);
  } catch (err) {
    showAlert(err.message, true);
  }
}

async function downloadKeyFile(deviceId) {
  try {
    const res = await apiFetch(`/usb/download-keyfile/${deviceId}`);
    if (!res.ok) throw new Error('Gagal mengunduh berkas kunci');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wariscrypt.key';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    showAlert(err.message, true);
  }
}

async function handleRegisterUsb(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-reg-usb');
  btn.disabled = true;
  btn.textContent = 'Memasang Kunci Bootable ke Flashdisk...';

  const deviceName = document.getElementById('usb-device-name').value.trim();

  try {
    const res = await apiFetch('/usb/register', {
      method: 'POST',
      body: JSON.stringify({ device_name: deviceName })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mendaftarkan USB');

    if (data.written_to_drive) {
      showAlert(
        `Berhasil! Kunci Bootable '${data.device_name}' (wariscrypt.key & Boot_WARISCRYPT.bat) telah otomatis dipasang langsung ke Flashdisk ${data.written_to_drive}!`,
        false
      );
    } else {
      showAlert(
        `Kunci '${data.device_name}' berhasil dibuat! Karena tidak ada Flashdisk yang terdeteksi, mengunduh berkas wariscrypt.key...`,
        false
      );
      const blob = new Blob([data.raw_key_payload], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'wariscrypt.key';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }

    await Promise.all([checkLiveUsbPort(), loadUsbDevices()]);
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="zap" class="w-4 h-4 mr-1 inline"></i><span id="btn-reg-usb-text">Buat &amp; Pasang Kunci Bootable Langsung ke Flashdisk</span>`;
    await checkLiveUsbPort();
    if (window.lucide) lucide.createIcons();
  }
}

Object.assign(window, {
  checkLiveUsbPort,
  handleRegisterUsb,
  installKeyToPluggedUsb,
  deleteUsbDevice,
  downloadKeyFile
});
