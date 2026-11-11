const CONFIG = {
  API_BASE_URL: window.location.origin.includes(':8000') 
    ? `${window.location.origin}/api`
    : 'http://localhost:8000/api',
  STORAGE_KEYS: {
    AUTH_TOKEN: 'tlw_auth_token',
    USER_PROFILE: 'tlw_user_profile',
  }
};

window.CONFIG = CONFIG;

// Global helper for authenticated API calls
window.apiFetch = async function(endpoint, options = {}) {
  const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  const headers = options.headers || {};
  
  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // Set Content-Type only if not FormData
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }
  
  const url = endpoint.startsWith('http') ? endpoint : `${CONFIG.API_BASE_URL}${endpoint}`;
  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401 && !endpoint.includes('/auth/login')) {
    // Session expired
    localStorage.removeItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_PROFILE);
    window.location.href = 'sign-in.html';
    throw new Error('Sesi telah berakhir. Silakan login kembali.');
  }
  
  return response;
};
