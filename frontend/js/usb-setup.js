document.addEventListener('DOMContentLoaded', async () => {
  await loadUsbDevices();
});

function showAlert(msg, isError = false) {
  const el = document.getElementById('usb-alert');
  el.className = `p-4 rounded text-xs leading-relaxed ${isError ? 'bg-rose-950/80 border border-rose-800 text-rose-200' : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'}`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

async function loadUsbDevices() {
  const tbody = document.getElementById('usb-devices-tbody');
  try {
    const res = await apiFetch('/usb/');
    if (!res.ok) throw new Error('Gagal memuat perangkat');
    const devices = await res.json();

    if (devices.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-500">Belum ada perangkat USB yang didaftarkan.</td></tr>`;
      return;
    }

    tbody.innerHTML = devices.map(d => `
      <tr class="hover:bg-slate-900/40 transition">
        <td class="py-2.5 px-3 font-semibold text-white">${d.device_name}</td>
        <td class="py-2.5 px-3 font-mono text-[11px] text-willGold">${d.device_fingerprint}</td>
        <td class="py-2.5 px-3">
          <span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase font-mono">
            ${d.device_status}
          </span>
        </td>
        <td class="py-2.5 px-3 text-slate-400 text-[11px] font-mono">
          ${d.last_used_at ? new Date(d.last_used_at).toLocaleString('id-ID') : 'Belum pernah'}
        </td>
        <td class="py-2.5 px-3 text-right">
          <a href="${CONFIG.API_BASE_URL}/usb/download-keyfile/${d.device_id}" 
             download="wariscrypt.key"
             class="px-2.5 py-1 text-[11px] bg-slate-800 hover:bg-slate-700 text-willGold rounded border border-willGold/40 transition inline-flex items-center space-x-1">
            <i data-lucide="download" class="w-3 h-3"></i>
            <span>Unduh .key</span>
          </a>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-rose-400">${err.message}</td></tr>`;
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

async function handleRegisterUsb(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-reg-usb');
  btn.disabled = true;
  btn.textContent = 'Membuat Kunci Kriptografis...';

  const deviceName = document.getElementById('usb-device-name').value.trim();

  try {
    const res = await apiFetch('/usb/register', {
      method: 'POST',
      body: JSON.stringify({ device_name: deviceName })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal mendaftarkan USB');

    showAlert(`Perangkat '${data.device_name}' berhasil didaftarkan! Mengunduh berkas wariscrypt.key...`, false);

    // Trigger download of key file
    const blob = new Blob([data.raw_key_payload], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'wariscrypt.key';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    await loadUsbDevices();
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="key" class="w-4 h-4 mr-2"></i><span>Buat & Unduh Kunci wariscrypt.key</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

window.handleRegisterUsb = handleRegisterUsb;
