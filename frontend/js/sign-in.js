let activeCameraStream = null;

function showAlert(msg, isError = true) {
  const el = document.getElementById('auth-alert');
  el.className = `p-3 rounded-lg text-xs leading-relaxed ${
    isError
      ? 'bg-rose-950/80 border border-rose-800 text-rose-200'
      : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'
  }`;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function hideAlert() {
  document.getElementById('auth-alert').classList.add('hidden');
}

function goAfterLogin(user) {
  window.location.href = user.role === 'beneficiary' ? 'claim.html' : 'dashboard.html';
}

function saveSession(data) {
  if (window.saveAuthSession) {
    window.saveAuthSession(data);
  } else {
    localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, data.access_token);
    localStorage.setItem(CONFIG.STORAGE_KEYS.USER_PROFILE, JSON.stringify(data.user));
  }
}

function switchAuthTab(tab) {
  hideAlert();
  stopCamera();
  const isLogin = tab === 'login';
  document.getElementById('login-section').classList.toggle('hidden', !isLogin);
  document.getElementById('register-section').classList.toggle('hidden', isLogin);

  const loginTab = document.getElementById('tab-login-btn');
  const regTab = document.getElementById('tab-register-btn');
  if (isLogin) {
    loginTab.className = 'flex-1 pb-3 text-xs md:text-sm font-semibold border-b-2 border-willGold text-willGold transition';
    regTab.className = 'flex-1 pb-3 text-xs md:text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
  } else {
    regTab.className = 'flex-1 pb-3 text-xs md:text-sm font-semibold border-b-2 border-willGold text-willGold transition';
    loginTab.className = 'flex-1 pb-3 text-xs md:text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
  }
  if (window.lucide) lucide.createIcons();
}

function switchLoginMode(mode) {
  hideAlert();
  stopCamera();
  const pwdBtn = document.getElementById('subtab-pwd-btn');
  const faceBtn = document.getElementById('subtab-face-btn');
  const pwdForm = document.getElementById('form-login-pwd');
  const faceForm = document.getElementById('form-login-face');

  if (mode === 'password') {
    pwdBtn.className = 'flex-1 py-1.5 rounded font-medium bg-willGold text-ink-dark transition';
    faceBtn.className = 'flex-1 py-1.5 rounded font-medium text-slate-400 hover:text-white transition flex items-center justify-center space-x-1';
    pwdForm.classList.remove('hidden');
    faceForm.classList.add('hidden');
  } else {
    faceBtn.className = 'flex-1 py-1.5 rounded font-medium bg-willGold text-ink-dark transition flex items-center justify-center space-x-1';
    pwdBtn.className = 'flex-1 py-1.5 rounded font-medium text-slate-400 hover:text-white transition';
    pwdForm.classList.add('hidden');
    faceForm.classList.remove('hidden');
    const idVal = document.getElementById('login-identifier').value;
    if (idVal) document.getElementById('face-login-identifier').value = idVal;
  }
  if (window.lucide) lucide.createIcons();
}

async function startCamera(target) {
  stopCamera();
  const video = document.getElementById(target === 'login' ? 'login-video' : 'reg-video');
  const overlay = document.getElementById(target === 'login' ? 'camera-overlay' : 'reg-camera-overlay');
  try {
    activeCameraStream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 360 } });
    video.srcObject = activeCameraStream;
    overlay.classList.add('hidden');
  } catch (err) {
    showAlert('Kamera tidak dapat diakses: ' + err.message, true);
  }
}

function stopCamera() {
  if (activeCameraStream) {
    activeCameraStream.getTracks().forEach(t => t.stop());
    activeCameraStream = null;
  }
}

function captureFrame(videoEl, canvasEl) {
  if (!videoEl || !videoEl.videoWidth) throw new Error('Kamera belum aktif');
  canvasEl.width = videoEl.videoWidth;
  canvasEl.height = videoEl.videoHeight;
  canvasEl.getContext('2d').drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
  return canvasEl.toDataURL('image/jpeg', 0.85);
}

function captureFace(target) {
  try {
    const base64 = captureFrame(document.getElementById('reg-video'), document.getElementById('reg-canvas'));
    document.getElementById('reg-face-base64').value = base64;
    document.getElementById('reg-face-status').classList.remove('hidden');
  } catch (e) {
    showAlert(e.message, true);
  }
}

async function handlePasswordLogin(e) {
  e.preventDefault();
  hideAlert();
  const btn = document.getElementById('btn-login-submit');
  btn.disabled = true;
  btn.textContent = 'Memverifikasi...';

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username_or_email: document.getElementById('login-identifier').value.trim(),
        password: document.getElementById('login-password').value
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login gagal');
    saveSession(data);
    goAfterLogin(data.user);
  } catch (err) {
    showAlert(err.message, true);
    btn.disabled = false;
    btn.textContent = 'Masuk ke Vault';
  }
}

async function captureAndLoginFace() {
  hideAlert();
  const identifier = document.getElementById('face-login-identifier').value.trim();
  if (!identifier) {
    showAlert('Isi username atau email terlebih dahulu', true);
    return;
  }
  let base64;
  try {
    base64 = captureFrame(document.getElementById('login-video'), document.getElementById('login-canvas'));
  } catch (err) {
    showAlert('Nyalakan kamera dan pastikan wajah terlihat jelas', true);
    return;
  }

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/auth/face-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email: identifier, face_image_base64: base64 })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Verifikasi wajah gagal');
    stopCamera();
    saveSession(data);
    goAfterLogin(data.user);
  } catch (err) {
    showAlert(err.message, true);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  hideAlert();
  const btn = document.getElementById('btn-reg-submit');
  btn.disabled = true;
  btn.textContent = 'Mendaftarkan...';

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: document.getElementById('reg-username').value.trim(),
        email: document.getElementById('reg-email').value.trim(),
        password: document.getElementById('reg-password').value,
        full_name: document.getElementById('reg-fullname').value.trim(),
        role: document.querySelector('input[name="reg-role"]:checked').value,
        phone_number: document.getElementById('reg-phone').value.trim() || null,
        face_image_base64: document.getElementById('reg-face-base64').value || null
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Pendaftaran gagal');
    stopCamera();
    saveSession(data);
    goAfterLogin(data.user);
  } catch (err) {
    showAlert(err.message, true);
    btn.disabled = false;
    btn.textContent = 'Daftar & Masuk';
  }
}

let usbPollTimer = null;

async function checkUsbGateStatus(manual = false) {
  const lockedEl = document.getElementById('usb-gate-locked');
  const unlockedEl = document.getElementById('usb-gate-unlocked');
  const bootBoxEl = document.getElementById('usb-boot-login-box');
  const titleEl = document.getElementById('usb-banner-title');
  const subEl = document.getElementById('usb-banner-sub');
  const badgeEl = document.getElementById('usb-drive-badge');
  const ownerBadgeEl = document.getElementById('usb-key-owner-badge');
  const bootBtnText = document.getElementById('btn-usb-boot-text');

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/usb/detect`);
    if (!res.ok) throw new Error('Gagal memeriksa port USB');
    const state = await res.json();

    if (state.usb_plugged) {
      lockedEl.classList.add('hidden');
      unlockedEl.classList.remove('hidden');

      const driveStr = state.active_drive || 'USB';
      const labelStr = state.active_label || 'Flashdisk';
      if (badgeEl) badgeEl.textContent = `${driveStr} (${labelStr})`;

      if (state.verified && state.owner_username) {
        if (titleEl) titleEl.textContent = `Flashdisk Bootable Terverifikasi (${driveStr})`;
        if (subEl) subEl.textContent = `Kunci Perangkat: ${state.device_name || labelStr} • Milik: ${state.owner_full_name || state.owner_username}`;
        if (bootBoxEl) bootBoxEl.classList.remove('hidden');
        if (ownerBadgeEl) ownerBadgeEl.textContent = `@${state.owner_username}`;
        if (bootBtnText) bootBtnText.textContent = `Boot & Masuk sebagai ${state.owner_full_name || state.owner_username} (${driveStr})`;

        const loginInput = document.getElementById('login-identifier');
        if (loginInput && !loginInput.value) {
          loginInput.value = state.owner_username;
        }
      } else {
        if (titleEl) titleEl.textContent = `Flashdisk Fisik Terdeteksi di ${driveStr} (${labelStr})`;
        if (subEl) subEl.textContent = state.has_keyfile
          ? 'Berkas wariscrypt.key ditemukan namun belum terdaftar/tidak cocok.'
          : 'Akses Login terbuka. Setelah masuk, pasang Kunci Bootable di menu Flashdisk.';
        if (bootBoxEl) bootBoxEl.classList.add('hidden');
      }
    } else {
      // Tidak ada Flashdisk yang dicolok -> Kunci halaman login!
      stopCamera();
      unlockedEl.classList.add('hidden');
      lockedEl.classList.remove('hidden');
    }
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    if (manual) {
      alert('Gagal mendeteksi port USB: ' + err.message);
    }
  }
}

async function handleUsbBootLogin() {
  hideAlert();
  const btn = document.getElementById('btn-usb-boot-login');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Memverifikasi Kunci Bootable Flashdisk...';
  }

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/usb/boot-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Gagal login dengan Flashdisk');
    saveSession(data);
    goAfterLogin(data.user);
  } catch (err) {
    showAlert(err.message, true);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="zap" class="w-4 h-4"></i><span>Boot & Masuk Langsung via Flashdisk</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.redirectIfAuthenticated && window.redirectIfAuthenticated()) {
    return;
  }
  checkUsbGateStatus();
  usbPollTimer = setInterval(() => checkUsbGateStatus(false), 2000);
  if (window.lucide) lucide.createIcons();
});

function fillDemo(username, password) {
  document.getElementById('login-identifier').value = username;
  document.getElementById('login-password').value = password;
  hideAlert();
}

Object.assign(window, {
  fillDemo,
  checkUsbGateStatus,
  handleUsbBootLogin,
  switchAuthTab,
  switchLoginMode,
  startCamera,
  captureFace,
  captureAndLoginFace,
  handlePasswordLogin,
  handleRegister
});
