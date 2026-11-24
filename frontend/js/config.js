const CONFIG = {
  API_BASE_URL: window.location.origin && window.location.origin.includes(':8000') 
    ? `${window.location.origin}/api`
    : 'http://localhost:8000/api',
  STORAGE_KEYS: {
    AUTH_TOKEN: 'wariscrypt_auth_token',
    USER_PROFILE: 'wariscrypt_user_profile',
    LEGACY_TOKEN: 'tlw_auth_token',
    LEGACY_PROFILE: 'tlw_user_profile',
  }
};

window.CONFIG = CONFIG;

// Decode payload dari JWT token secara aman
window.parseJwt = function(token) {
  if (!token || typeof token !== 'string') return null;
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(c => {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    const payload = JSON.parse(jsonPayload);
    // Jika token sudah kadaluarsa (exp dalam detik)
    if (payload.exp && (payload.exp * 1000) < Date.now()) {
      return null;
    }
    return payload;
  } catch (e) {
    return null;
  }
};

window.getAuthToken = function() {
  const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN) ||
                localStorage.getItem(CONFIG.STORAGE_KEYS.LEGACY_TOKEN) ||
                localStorage.getItem('token') || '';
  if (!token) return '';
  // Validasi apakah token JWT masih valid / belum expired
  const payload = window.parseJwt(token);
  if (!payload) {
    // Token kadaluarsa atau format rusak
    return '';
  }
  return token;
};

window.getUserProfile = function() {
  const raw = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_PROFILE) ||
              localStorage.getItem(CONFIG.STORAGE_KEYS.LEGACY_PROFILE) ||
              localStorage.getItem('user_profile');
  let user = null;
  if (raw && raw !== 'null' && raw !== 'undefined') {
    try {
      user = JSON.parse(raw);
    } catch(e) {
      user = null;
    }
  }

  // Jika profile di localStorage kosong tetapi ada token valid, pulihkan dari JWT!
  if (!user || (!user.username && !user.user_id)) {
    const token = window.getAuthToken();
    const payload = window.parseJwt(token);
    if (payload) {
      user = {
        user_id: payload.sub,
        username: payload.username || 'Pengguna',
        role: payload.role || 'owner',
        full_name: payload.username || 'Pengguna'
      };
      // Simpan kembali hasil pemulihan ke localStorage
      try {
        localStorage.setItem(CONFIG.STORAGE_KEYS.USER_PROFILE, JSON.stringify(user));
      } catch(e) {}
    }
  }

  return user;
};

window.saveAuthSession = function(data) {
  if (!data) return;
  if (data.access_token) {
    localStorage.setItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN, data.access_token);
    localStorage.setItem(CONFIG.STORAGE_KEYS.LEGACY_TOKEN, data.access_token);
    localStorage.setItem('token', data.access_token);
  }
  if (data.user) {
    const userStr = JSON.stringify(data.user);
    localStorage.setItem(CONFIG.STORAGE_KEYS.USER_PROFILE, userStr);
    localStorage.setItem(CONFIG.STORAGE_KEYS.LEGACY_PROFILE, userStr);
    localStorage.setItem('user_profile', userStr);
  }
};

window.clearAuthSession = function() {
  localStorage.removeItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_PROFILE);
  localStorage.removeItem(CONFIG.STORAGE_KEYS.LEGACY_TOKEN);
  localStorage.removeItem(CONFIG.STORAGE_KEYS.LEGACY_PROFILE);
  localStorage.removeItem('token');
  localStorage.removeItem('user_profile');
  sessionStorage.clear();
};

window.isAuthenticated = function() {
  const token = window.getAuthToken();
  return !!token;
};

window.requireAuth = function(requiredRole = null) {
  const token = window.getAuthToken();
  if (!token) {
    // Jangan panggil clearAuthSession secara agresif di sini
    window.location.replace('sign-in.html');
    return false;
  }
  const user = window.getUserProfile();
  if (requiredRole && user && user.role && user.role !== requiredRole) {
    if (user.role === 'beneficiary') {
      window.location.replace('claim.html');
    } else {
      window.location.replace('dashboard.html');
    }
    return false;
  }
  return true;
};

window.redirectIfAuthenticated = function() {
  if (window.isAuthenticated()) {
    const user = window.getUserProfile();
    const dest = (user && user.role === 'beneficiary') ? 'claim.html' : 'dashboard.html';
    window.location.replace(dest);
    return true;
  }
  return false;
};

// Global helper for authenticated API calls
window.apiFetch = async function(endpoint, options = {}) {
  const token = window.getAuthToken();
  const headers = options.headers || {};
  
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  
  const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.API_BASE_URL}${endpoint}`;
  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401 && !endpoint.includes('/auth/login')) {
    window.clearAuthSession();
    window.location.replace('sign-in.html');
    throw new Error('Sesi telah berakhir. Silakan login kembali.');
  }
  
  return response;
};

// Sinkronisasi data profil terbaru di latar belakang
window.syncUserProfile = async function() {
  const token = window.getAuthToken();
  if (!token) return;
  try {
    const res = await window.apiFetch('/auth/me');
    if (res.ok) {
      const profile = await res.json();
      window.saveAuthSession({ user: profile });
      // Update tampilan nama jika ada elemen DOM yang relevan
      const nameEl = document.getElementById('user-display-name');
      if (nameEl) nameEl.textContent = profile.full_name || profile.username;
    }
  } catch (e) {
    // Diamkan jika offline atau gagal minor
  }
};

// Helper UI bersama
window.esc = function (s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
};

window.setAlert = function (id, msg, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = 'p-3 rounded-lg text-xs leading-relaxed ' + (isError ? 'bg-rose-950/80 border border-rose-800 text-rose-200' : 'bg-emerald-950/80 border border-emerald-800 text-emerald-200');
  el.textContent = msg;
  el.classList.remove('hidden');
};

window.formatDate = function (iso) {
  if (!iso) return '-';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
};

window.fileToBase64 = function (file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
};

// Jalankan sinkronisasi profil saat script dimuat jika ada token
if (window.getAuthToken()) {
  window.syncUserProfile();
}
