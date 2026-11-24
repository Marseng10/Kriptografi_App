document.addEventListener('DOMContentLoaded', () => {
  renderNavigation();
});

function navLink(href, label, currentPage) {
  const active = currentPage === href;
  return `<a href="${href}" class="px-3 py-2 text-sm font-medium transition ${active ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">${label}</a>`;
}

function renderNavigation() {
  const navContainer = document.getElementById('main-nav');
  if (!navContainer) return;

  const token = localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  let user = null;
  try {
    user = JSON.parse(localStorage.getItem(CONFIG.STORAGE_KEYS.USER_PROFILE) || 'null');
  } catch (e) {
    user = null;
  }

  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  let navLinks = '';
  let authButton = '';

  if (token && user) {
    if (user.role === 'owner') {
      navLinks =
        navLink('dashboard.html', 'Beranda', currentPage) +
        navLink('create-will.html', 'Tulis Wasiat', currentPage) +
        navLink('my-wills.html', 'Wasiat & Ahli Waris', currentPage) +
        navLink('usb-setup.html', 'Flashdisk', currentPage);
    } else {
      navLinks =
        navLink('access-key.html', 'Klaim Warisan', currentPage);
    }

    authButton = `
      <div class="flex items-center space-x-3">
        <span class="text-sm text-slate-200 hidden md:inline">${user.full_name || user.username}</span>
        <button onclick="handleLogout()" class="text-xs text-rose-400 hover:text-rose-300 border border-rose-800/50 px-3 py-1.5 rounded transition">Keluar</button>
      </div>`;
  } else {
    navLinks =
      navLink('index.html', 'Beranda', currentPage) +
      navLink('access-key.html', 'Klaim Warisan', currentPage);
    authButton = `<a href="sign-in.html" class="gold-btn px-4 py-1.5 text-xs font-semibold rounded">Masuk</a>`;
  }

  navContainer.innerHTML = `
    <header class="border-b border-willGold/20 bg-ink-dark/90 backdrop-blur sticky top-0 z-50">
      <div class="max-w-6xl mx-auto px-4 sm:px-6">
        <div class="flex items-center justify-between h-16">
          <a href="index.html" class="flex items-center space-x-3">
            <div class="wax-seal">W</div>
            <span class="font-cinzel text-lg font-bold tracking-wider text-willGold">WARISCRYPT</span>
          </a>
          <nav class="hidden md:flex items-center space-x-1">${navLinks}</nav>
          <div>${authButton}</div>
        </div>
      </div>
    </header>`;
}

function handleLogout() {
  localStorage.removeItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_PROFILE);
  window.location.href = 'sign-in.html';
}

window.handleLogout = handleLogout;
