document.addEventListener('DOMContentLoaded', async () => {
  if (!localStorage.getItem(CONFIG.STORAGE_KEYS.AUTH_TOKEN)) {
    window.location.href = 'sign-in.html';
    return;
  }
  try {
    const res = await apiFetch('/auth/me');
    if (!res.ok) throw new Error();
    const me = await res.json();
    document.getElementById('user-display-name').textContent = me.full_name || me.username;
    const menuId = me.role === 'owner' ? 'owner-menu' : 'beneficiary-menu';
    document.getElementById(menuId).classList.remove('hidden');
  } catch (e) {
    window.location.href = 'sign-in.html';
  }
});
