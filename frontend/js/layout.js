// WARISCRYPT - Left Sidebar Navigation Component
function renderLayout() {
  const token = window.getAuthToken ? window.getAuthToken() : '';
  const user = window.getUserProfile ? window.getUserProfile() : null;
  const esc = window.esc || function(s) {
    return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  };

  const isLoggedIn = !!(token && user && (user.user_id || user.username));
  const isBeneficiary = isLoggedIn && user.role === 'beneficiary';
  const roleLabel = !isLoggedIn ? 'Tamu' : (isBeneficiary ? 'Ahli Waris' : 'Pewaris');
  const userName = !isLoggedIn ? 'Pengunjung' : (user.full_name || user.username || 'Pengguna');

  // GUEST MENU (Sebelum Login) - Ramping tanpa duplikasi
  const GUEST_MENU = [
    { key: 'home', href: 'index.html', icon: 'home', label: 'Halaman Depan' },
    { key: 'claim', href: 'claim.html', icon: 'unlock', label: 'Klaim Warisan' },
  ];

  // PEWARIS MENU (Setelah Login sebagai Pewaris)
  const OWNER_MENU = [
    { key: 'dashboard', href: 'dashboard.html', icon: 'layout-dashboard', label: 'Beranda' },
    { key: 'create-will', href: 'create-will.html', icon: 'pen-tool', label: 'Tulis Wasiat' },
    { key: 'my-wills', href: 'my-wills.html', icon: 'folder', label: 'Wasiat & Ahli Waris' },
    { key: 'access-key', href: 'access-key.html', icon: 'key', label: 'Kartu Akses Foto' },
    { key: 'usb-setup', href: 'usb-setup.html', icon: 'usb', label: 'Flashdisk' },
  ];

  // AHLI WARIS MENU (Setelah Login sebagai Ahli Waris)
  const BENEFICIARY_MENU = [
    { key: 'dashboard', href: 'dashboard.html', icon: 'layout-dashboard', label: 'Beranda' },
    { key: 'claim', href: 'claim.html', icon: 'unlock', label: 'Klaim Warisan' },
  ];

  const menu = !isLoggedIn ? GUEST_MENU : (isBeneficiary ? BENEFICIARY_MENU : OWNER_MENU);
  const active = document.body.dataset.active || '';

  const linksHtml = menu.map(m => {
    const on = m.key === active;
    return `
      <a href="${m.href}" class="flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-xs md:text-sm font-medium transition ${
        on
          ? 'bg-willGold/20 text-willGold border-l-4 border-willGold font-semibold shadow-inner'
          : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
      }">
        <i data-lucide="${m.icon}" class="w-4 h-4 ${on ? 'text-willGold' : 'text-slate-400'}"></i>
        <span>${m.label}</span>
      </a>
    `;
  }).join('');

  const shell = document.getElementById('shell');
  if (shell) {
    shell.innerHTML = `
      <!-- Sidebar Kiri Tetap -->
      <aside id="sidebar" class="app-sidebar">
        <div class="space-y-6 flex-1 overflow-y-auto pr-1">
          <!-- Brand Logo -->
          <a href="${!isLoggedIn ? 'index.html' : 'dashboard.html'}" class="flex items-center space-x-3 px-2 py-1">
            <div class="wax-seal">W</div>
            <div class="flex flex-col">
              <span class="font-cinzel text-lg font-bold tracking-wider text-willGold">WARISCRYPT</span>
              <span class="text-[10px] text-slate-400 tracking-wider uppercase">Wasiat Digital Aman</span>
            </div>
          </a>

          <!-- User Role Badge -->
          <div class="p-3 rounded-lg bg-slate-900/90 border border-slate-800 flex items-center justify-between">
            <div class="flex flex-col min-w-0 pr-2">
              <span class="text-xs font-semibold text-white truncate">${esc(!isLoggedIn ? 'Selamat Datang' : userName)}</span>
              <span class="text-[11px] ${!isLoggedIn ? 'text-slate-400' : 'text-willGold'} font-mono">${roleLabel} &bull; ${!isLoggedIn ? 'Belum Masuk' : 'Aktif'}</span>
            </div>
            ${!isLoggedIn 
              ? `<a href="sign-in.html" class="text-xs text-willGold hover:underline font-semibold shrink-0">Masuk</a>` 
              : `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>`
            }
          </div>

          <!-- Navigation Links -->
          <nav class="space-y-1">
            ${linksHtml}
          </nav>
        </div>

        <!-- Footer Sidebar -->
        <div class="pt-4 border-t border-slate-800 space-y-2 shrink-0">
          ${isLoggedIn ? `
            <a href="index.html" class="flex items-center space-x-3 px-3.5 py-2 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/40 transition">
              <i data-lucide="home" class="w-4 h-4 text-slate-400"></i>
              <span>Halaman Depan</span>
            </a>
            <button onclick="handleLogout()" class="w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-xs font-medium text-rose-400 hover:bg-rose-950/40 border border-transparent hover:border-rose-900/50 transition text-left cursor-pointer">
              <i data-lucide="log-out" class="w-4 h-4 text-rose-400"></i>
              <span>Keluar Akun</span>
            </button>
          ` : `
            <a href="sign-in.html" class="gold-btn w-full py-2.5 text-xs font-semibold text-center flex items-center justify-center space-x-2">
              <i data-lucide="log-in" class="w-4 h-4"></i>
              <span>Masuk Akun</span>
            </a>
          `}
        </div>
      </aside>

      <!-- Mobile Backdrop -->
      <div id="sidebar-backdrop" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-40 hidden md:hidden" onclick="toggleSidebar()"></div>

      <!-- Header Atas -->
      <header class="app-header">
        <div class="flex items-center space-x-3">
          <button class="md:hidden p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800" onclick="toggleSidebar()" aria-label="Buka Menu">
            <i data-lucide="menu" class="w-5 h-5"></i>
          </button>
          <div class="flex items-center space-x-2">
            <span class="font-cinzel text-sm md:text-base font-semibold text-willGold">${document.title.split('-')[0].trim()}</span>
          </div>
        </div>

        <div class="flex items-center space-x-3">
          ${isLoggedIn ? `
            <div class="hidden sm:flex flex-col text-right">
              <span class="text-xs font-medium text-slate-200">${esc(userName)}</span>
              <span class="text-[10px] text-willGold font-mono">${roleLabel}</span>
            </div>
            <div class="w-8 h-8 rounded-full bg-slate-800 border border-willGold/40 flex items-center justify-center text-xs font-bold text-willGold">
              ${esc((userName || 'U')[0].toUpperCase())}
            </div>
            <button onclick="handleLogout()" title="Keluar Akun" class="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition">
              <i data-lucide="log-out" class="w-4 h-4"></i>
            </button>
          ` : `
            <a href="sign-in.html" class="gold-btn px-3.5 py-1.5 text-xs font-semibold flex items-center space-x-1.5">
              <i data-lucide="log-in" class="w-3.5 h-3.5"></i>
              <span>Masuk Akun</span>
            </a>
          `}
        </div>
      </header>
    `;

    if (window.lucide) {
      lucide.createIcons();
    }
  }
}

function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const bd = document.getElementById('sidebar-backdrop');
  if (sb) sb.classList.toggle('sidebar-open');
  if (bd) bd.classList.toggle('hidden');
}

function handleLogout() {
  if (window.clearAuthSession) {
    window.clearAuthSession();
  } else {
    localStorage.clear();
    sessionStorage.clear();
  }
  window.location.replace('sign-in.html');
}

window.toggleSidebar = toggleSidebar;
window.handleLogout = handleLogout;
window.renderLayout = renderLayout;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', renderLayout);
} else {
  renderLayout();
}
