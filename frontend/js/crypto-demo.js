document.addEventListener('DOMContentLoaded', () => {
  runCryptoComparison();
});

async function runCryptoComparison() {
  const plaintext = document.getElementById('demo-plaintext').value;
  const key = document.getElementById('demo-key').value;
  const btn = document.getElementById('btn-run-demo');

  btn.disabled = true;
  btn.textContent = 'Menghitung Matematis...';

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/demo/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plaintext, key })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal memproses perbandingan');

    document.getElementById('out-vigenere').textContent = data.vigenere_ciphertext;
    document.getElementById('out-aes').textContent = data.aes_ciphertext;
    document.getElementById('out-chacha').textContent = data.chacha_ciphertext;
    document.getElementById('out-notes').textContent = data.comparison_notes;
  } catch (err) {
    document.getElementById('out-notes').textContent = 'Error: ' + err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="zap" class="w-4 h-4 mr-2"></i><span>Enkripsi Secara Paralel & Bandingkan</span>`;
    if (window.lucide) lucide.createIcons();
  }
}

window.runCryptoComparison = runCryptoComparison;
