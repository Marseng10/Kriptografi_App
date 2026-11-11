document.addEventListener('DOMContentLoaded', () => {
  renderNavigation();
});

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
    const isOwner = user.role === 'owner';

    navLinks = `
      <a href="dashboard.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'dashboard.html' ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">Dashboard</a>
      ${isOwner ? `
        <a href="create-will.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'create-will.html' ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">+ Tulis Wasiat</a>
        <a href="my-wills.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'my-wills.html' ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">Kelola Wasiat</a>
        <a href="usb-setup.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'usb-setup.html' ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">USB Key</a>
      ` : `
        <a href="access-key.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'access-key.html' ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">Klaim Warisan</a>
      `}
      <a href="audit-trail.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'audit-trail.html' ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">Blockchain Audit</a>
      <a href="crypto-demo.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'crypto-demo.html' ? 'text-willGold border-b-2 border-willGold' : 'text-slate-300 hover:text-willGold'}">Crypto Lab</a>
    `;

    authButton = `
      <div class="flex items-center space-x-3">
        <span class="text-xs bg-slate-800 text-willGold px-2.5 py-1 rounded border border-willGold/30 uppercase tracking-wider">${user.role}</span>
        <span class="text-sm text-slate-200 hidden md:inline font-medium">${user.full_name || user.username}</span>
        <button onclick="handleLogout()" class="text-xs text-rose-400 hover:text-rose-300 bg-rose-950/40 border border-rose-800/50 px-3 py-1.5 rounded transition">
          Logout
        </button>
      </div>
    `;
  } else {
    navLinks = `
      <a href="index.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'index.html' ? 'text-willGold' : 'text-slate-300 hover:text-willGold'}">Beranda</a>
      <a href="access-key.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'access-key.html' ? 'text-willGold' : 'text-slate-300 hover:text-willGold'}">Portal Klaim</a>
      <a href="crypto-demo.html" class="px-3 py-2 text-sm font-medium transition ${currentPage === 'crypto-demo.html' ? 'text-willGold' : 'text-slate-300 hover:text-willGold'}">Laboratorium Kripto</a>
    `;

    authButton = `
      <div class="flex items-center space-x-2">
        <a href="access-key.html" class="px-3 py-1.5 text-xs text-willGold border border-willGold/40 rounded hover:bg-willGold/10 transition">Buka Kunci</a>
        <a href="sign-in.html" class="gold-btn px-4 py-1.5 text-xs font-semibold rounded">Masuk</a>
      </div>
    `;
  }

  navContainer.innerHTML = `
    <header class="border-b border-willGold/20 bg-ink-dark/90 backdrop-blur sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center space-x-3">
            <a href="index.html" class="flex items-center space-x-3 group">
              <div class="wax-seal">W</div>
              <div>
                <span class="font-cinzel text-lg font-bold tracking-wider text-willGold group-hover:text-white transition">WARISCRYPT</span>
                <span class="text-[10px] text-slate-400 block tracking-widest -mt-1 font-sans">THE LAST WILL</span>
              </div>
            </a>
          </div>

          <nav class="hidden md:flex items-center space-x-2">
            ${navLinks}
          </nav>

          <div>
            ${authButton}
          </div>
        </div>
      </div>
    </header>
  `;
}

function handleLogout() {
  localStorage.removeItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN);
  localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_PROFILE);
  window.location.href = 'sign-in.html';
}

window.handleLogout = handleLogout;
