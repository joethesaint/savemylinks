// SaveMyLinks — helpers shared by every page: toasts, theme, keyboard, categories, API errors.
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);

  // Toast: the API's status code beside a plain sentence (design system: "the code is honest").
  function toast(message, { code = '', tone = '' } = {}) {
    const box = $('#toasts');
    if (!box) return;
    const el = document.createElement('div');
    el.className = 'toast' + (tone ? ' toast-' + tone : '');
    if (code !== '') { const c = document.createElement('code'); c.textContent = code; el.append(c); }
    const msg = document.createElement('span'); msg.className = 'msg'; msg.textContent = message; el.append(msg);
    const close = document.createElement('button');
    close.className = 'btn btn-ghost btn-icon btn-sm'; close.type = 'button'; close.setAttribute('aria-label', 'Dismiss');
    close.innerHTML = '<svg class="icon" aria-hidden="true"><use href="#i-close"/></svg>';
    close.onclick = () => el.remove();
    el.append(close);
    box.append(el);
    setTimeout(() => el.remove(), tone === 'danger' ? 8000 : 5000);
  }

  // Theme: remembered per browser; the icon shows what a click switches to.
  function syncThemeButton() {
    const btn = $('#themeToggle');
    if (!btn) return;
    const dark = document.documentElement.dataset.theme === 'dark';
    btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    btn.querySelector('use').setAttribute('href', dark ? '#i-sun' : '#i-moon');
  }
  document.addEventListener('DOMContentLoaded', () => {
    syncThemeButton();
    const btn = $('#themeToggle');
    btn && btn.addEventListener('click', () => {
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch (e) { /* storage blocked */ }
      syncThemeButton();
    });
  });

  // "/" jumps to search from anywhere (or to the library's search from another page).
  document.addEventListener('keydown', (e) => {
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
    const t = e.target;
    if (t.closest('input, textarea, select, [contenteditable="true"], dialog')) return;
    e.preventDefault();
    const search = $('#searchInput');
    if (search) search.focus(); else location.href = './?focus=search';
  });

  // Categories keep their colour: assigned by their order from /api/resources/categories,
  // cycling green, blue, red, yellow (design system).
  let categoriesPromise = null;
  function categories() {
    categoriesPromise = categoriesPromise || fetch('/api/resources/categories').then(r => r.ok ? r.json() : []).catch(() => []);
    return categoriesPromise;
  }
  function categoryClass(name, list) {
    const i = list.indexOf(name);
    return 'cat-' + ((i < 0 ? list.length : i) % 4);
  }
  function resetCategories() { categoriesPromise = null; }

  // A 422 from FastAPI becomes one sentence per field that names the field and the fix.
  const FIELD_NAMES = { title: 'Title', url: 'URL', description: 'Description', category: 'Category' };
  function fieldErrors(detail) {
    const out = {};
    (Array.isArray(detail) ? detail : []).forEach(err => {
      const field = err.loc ? err.loc[err.loc.length - 1] : '';
      const name = FIELD_NAMES[field] || 'This field';
      let msg = err.msg || 'is not valid';
      const max = err.ctx && err.ctx.max_length;
      if (max) msg = `${name} is ${(err.input || '').length} characters; the limit is ${max}.`;
      else if (field === 'url') msg = 'Enter a full web address, starting with https://';
      else if (/at least 1 character/.test(msg)) msg = `${name} is required.`;
      else msg = `${name}: ${msg.replace(/^Value error, /, '')}.`;
      out[field] = msg;
    });
    return out;
  }

  window.SML = { toast, categories, categoryClass, resetCategories, fieldErrors };
})();
