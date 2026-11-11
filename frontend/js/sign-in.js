let activeCameraStream = null;

function showAlert(message, type = 'error') {
  const alertEl = document.getElementById('auth-alert');
  if (!alertEl) return;
  alertEl.className = `mb-4 p-3 rounded text-xs leading-relaxed ${
    type === 'error' 
      ? 'bg-rose-950/80 border border-rose-800 text-rose-200' 
      : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200'
  }`;
  alertEl.textContent = message;
  alertEl.classList.remove('hidden');
}

function hideAlert() {
  const alertEl = document.getElementById('auth-alert');
  if (alertEl) alertEl.classList.add('hidden');
}

function switchAuthTab(tab) {
  hideAlert();
  stopCamera();
  const loginSection = document.getElementById('login-section');
  const regSection = document.getElementById('register-section');
  const loginTabBtn = document.getElementById('tab-login-btn');
  const regTabBtn = document.getElementById('tab-register-btn');

  if (tab === 'login') {
    loginSection.classList.remove('hidden');
    regSection.classList.add('hidden');
    loginTabBtn.className = 'flex-1 pb-3 text-sm font-semibold border-b-2 border-willGold text-willGold transition';
    regTabBtn.className = 'flex-1 pb-3 text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
  } else {
    loginSection.classList.add('hidden');
    regSection.classList.remove('hidden');
    regTabBtn.className = 'flex-1 pb-3 text-sm font-semibold border-b-2 border-willGold text-willGold transition';
    loginTabBtn.className = 'flex-1 pb-3 text-sm font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 transition';
  }
}

function switchLoginMode(mode) {
  hideAlert();
  stopCamera();
  const pwdForm = document.getElementById('form-login-pwd');
  const faceForm = document.getElementById('form-login-face');
  const pwdBtn = document.getElementById('subtab-pwd-btn');
  const faceBtn = document.getElementById('subtab-face-btn');

  if (mode === 'password') {
    pwdForm.classList.remove('hidden');
    faceForm.classList.add('hidden');
    pwdBtn.className = 'flex-1 py-1.5 rounded font-medium bg-willGold text-ink-dark transition';
    faceBtn.className = 'flex-1 py-1.5 rounded font-medium text-slate-400 hover:text-white transition flex items-center justify-center space-x-1';
  } else {
    pwdForm.classList.add('hidden');
    faceForm.classList.remove('hidden');
    faceBtn.className = 'flex-1 py-1.5 rounded font-medium bg-willGold text-ink-dark transition flex items-center justify-center space-x-1';
    pwdBtn.className = 'flex-1 py-1.5 rounded font-medium text-slate-400 hover:text-white transition';
    
    // Copy identifier if user typed one
    const idVal = document.getElementById('login-identifier').value;
    if (idVal) {
      document.getElementById('face-login-identifier').value = idVal;
    }
  }
}

function fillDemoCredentials(username, password) {
  document.getElementById('login-identifier').value = username;
  document.getElementById('login-password').value = password;
  hideAlert();
}

async function startCamera(target) {
  stopCamera();
  const video = document.getElementById(target === 'login' ? 'login-video' : 'reg-video');
  const overlay = document.getElementById(target === 'login' ? 'camera-overlay' : 'reg-camera-overlay');
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 360 } });
    activeCameraStream = stream;
    video.srcObject = stream;
    if (overlay) overlay.classList.add('hidden');
  } catch (err) {
    showAlert('Kamera tidak dapat diakses: ' + err.message, 'error');
  }
}

function stopCamera() {
  if (activeCameraStream) {
    activeCameraStream.getTracks().forEach(track => track.stop());
    activeCameraStream = null;
  }
}

function captureFrame(videoEl, canvasEl) {
  if (!videoEl || !videoEl.videoWidth) {
    throw new Error('Video kamera belum siap atau belum aktif');
  }
  canvasEl.width = videoEl.videoWidth;
  canvasEl.height = videoEl.videoHeight;
  const ctx = canvasEl.getContext('2d');
  ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
  return canvasEl.toDataURL('image/jpeg', 0.85);
}

function captureFace(target) {
  try {
    const video = document.getElementById(target === 'login' ? 'login-video' : 'reg-video');
    const canvas = document.getElementById(target === 'login' ? 'login-canvas' : 'reg-canvas');
    const base64 = captureFrame(video, canvas);
    
    if (target === 'reg') {
      document.getElementById('reg-face-base64').value = base64;
      document.getElementById('reg-face-status').classList.remove('hidden');
    }
    return base64;
  } catch (e) {
    showAlert(e.message, 'error');
    return null;
  }
}

async function handlePasswordLogin(e) {
  e.preventDefault();
  hideAlert();
  const submitBtn = document.getElementById('btn-login-submit');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Memverifikasi...';

  const identifier = document.getElementById('login-identifier').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email: identifier, password: password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Login gagal');
    }

    // Save token & user
    localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, data.access_token);
    localStorage.setItem(CONFIG.STORAGE_KEYS.USER_PROFILE, JSON.stringify(data.user));

    showAlert('Autentikasi berhasil! Mengalihkan...', 'success');
    setTimeout(() => {
      window.location.href = data.user.role === 'beneficiary' ? 'access-key.html' : 'dashboard.html';
    }, 800);
  } catch (err) {
    showAlert(err.message, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Masuk ke Vault';
  }
}

async function captureAndLoginFace() {
  hideAlert();
  const identifier = document.getElementById('face-login-identifier').value.trim();
  if (!identifier) {
    showAlert('Masukkan username atau email terlebih dahulu', 'error');
    return;
  }

  const video = document.getElementById('login-video');
  const canvas = document.getElementById('login-canvas');
  let base64 = null;
  try {
    base64 = captureFrame(video, canvas);
  } catch (err) {
    showAlert('Nyalakan kamera dan pastikan wajah terlihat jelas', 'error');
    return;
  }

  showAlert('Menganalisis biometrik wajah...', 'success');

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/auth/face-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username_or_email: identifier, face_image_base64: base64 })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Verifikasi biometrik gagal');
    }

    localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, data.access_token);
    localStorage.setItem(CONFIG.STORAGE_KEYS.USER_PROFILE, JSON.stringify(data.user));

    showAlert('Wajah cocok! Mengalihkan ke sistem...', 'success');
    stopCamera();
    setTimeout(() => {
      window.location.href = data.user.role === 'beneficiary' ? 'access-key.html' : 'dashboard.html';
    }, 900);
  } catch (err) {
    showAlert(err.message, 'error');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  hideAlert();
  const btn = document.getElementById('btn-reg-submit');
  btn.disabled = true;
  btn.textContent = 'Mendaftarkan...';

  const role = document.querySelector('input[name="reg-role"]:checked').value;
  const fullName = document.getElementById('reg-fullname').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const phone = document.getElementById('reg-phone').value.trim() || null;
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const faceBase64 = document.getElementById('reg-face-base64').value || null;

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username,
        email,
        password,
        full_name: fullName,
        role,
        phone_number: phone,
        face_image_base64: faceBase64
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Registrasi gagal');
    }

    localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, data.access_token);
    localStorage.setItem(CONFIG.STORAGE_KEYS.USER_PROFILE, JSON.stringify(data.user));

    showAlert('Akun berhasil dibuat! Mengalihkan ke dashboard...', 'success');
    stopCamera();
    setTimeout(() => {
      window.location.href = data.user.role === 'beneficiary' ? 'access-key.html' : 'dashboard.html';
    }, 900);
  } catch (err) {
    showAlert(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Daftar & Masuk';
  }
}

window.switchAuthTab = switchAuthTab;
window.switchLoginMode = switchLoginMode;
window.fillDemoCredentials = fillDemoCredentials;
window.startCamera = startCamera;
window.captureFace = captureFace;
window.captureAndLoginFace = captureAndLoginFace;
window.handlePasswordLogin = handlePasswordLogin;
window.handleRegister = handleRegister;
