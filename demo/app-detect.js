// Demo only: is the SaveMyLinks app running on this computer? If so, take you to your own library.
//
// The check loads one tiny image from the app (http://127.0.0.1:8000, the app's default
// address). It reads nothing and sends nothing. Browsers may ask before a website reaches
// into this computer ("local network access"), so the first check runs only when you click;
// after a hit, later visits check by themselves (permission is already given).
//
// Auto-open: once connected, the demo counts down and opens your library at the same page
// (a search, a category, a shared link carry over), unless you choose "Stay in the demo".
// That choice is remembered until you turn auto-open back on.
(function () {
  const APP = 'http://127.0.0.1:8000/';
  const FOUND = 'sml-app-found';
  const STAY = 'sml-stay-in-demo';
  const COUNTDOWN = 3;
  const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const set = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* blocked */ } };
  const isDownloadPage = /download\.html$/.test(location.pathname);

  // The same page in your app: the save page keeps a shared link, the library keeps its search.
  function target() {
    const q = location.search;
    return /add\.html$/.test(location.pathname) ? `${APP}add${q}` : `${APP}${q}`;
  }

  function probe(timeout = 2500) {
    return new Promise((resolve) => {
      const img = new Image();
      const done = (ok) => { clearTimeout(timer); img.onload = img.onerror = null; resolve(ok); };
      const timer = setTimeout(() => done(false), timeout);
      img.onload = () => done(true);
      img.onerror = () => done(false);
      img.src = `${APP}static/art/icon-32.png?probe=${Date.now()}`;
    });
  }

  const el = (tag, props = {}, ...kids) => { const n = Object.assign(document.createElement(tag), props); n.append(...kids); return n; };
  const statusLine = (text) => {
    const s = el('span', { className: 'app-status' });
    s.innerHTML = '<span class="app-dot" aria-hidden="true"></span><strong>Connected.</strong> ';
    s.append(text);
    return s;
  };

  let timer = null;
  function connected(slots, { auto }) {
    for (const slot of slots) {
      slot.innerHTML = '';
      slot.classList.add('is-connected');
      slot.closest('.demo-banner')?.classList.add('is-connected');
    }
    const open = () => slots.forEach((s) => {
      const stay = el('button', { type: 'button', className: 'btn btn-ghost btn-sm', textContent: 'Open it automatically' });
      stay.onclick = () => { set(STAY, null); location.href = target(); };
      s.replaceChildren(statusLine('Your SaveMyLinks is running on this computer.'),
        el('a', { href: target(), className: 'app-open', textContent: 'Open your library →' }),
        ...(get(STAY) === '1' && !isDownloadPage ? [stay] : []));
    });
    if (!auto) { open(); return; }
    // Counting down to your library, with a way to stay.
    let left = COUNTDOWN;
    const count = el('span', { className: 'app-count' });
    count.setAttribute('aria-live', 'polite');
    const stay = el('button', { type: 'button', className: 'btn btn-ghost btn-sm', textContent: 'Stay in the demo' });
    stay.onclick = () => { clearInterval(timer); set(STAY, '1'); open(); };
    const tick = () => { count.textContent = ` Opening your library in ${left}…`; };
    tick();
    slots.forEach((s, i) => s.replaceChildren(statusLine(''), ...(i === 0 ? [count, el('a', { href: target(), className: 'app-open', textContent: 'Open now →' }), stay] : [])));
    timer = setInterval(() => { left -= 1; if (left <= 0) { clearInterval(timer); location.href = target(); } else tick(); }, 1000);
  }

  function notFound(slots) {
    for (const slot of slots) {
      slot.replaceChildren('Not running on this computer at 127.0.0.1:8000. ',
        el('a', { href: 'download.html', textContent: 'Get the app' }), ', open it, then try again.');
    }
  }

  async function check(slots, { quiet = false, fromClick = false } = {}) {
    const ok = await probe();
    set(FOUND, ok ? '1' : null);
    // The download page never jumps away: people come there to download.
    if (ok) connected(slots, { auto: !isDownloadPage && get(STAY) !== '1' });
    else if (!quiet) notFound(slots);
    return ok;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const slots = [...document.querySelectorAll('[data-app-detect]')];
    if (!slots.length) return;
    for (const slot of slots) {
      const b = slot.querySelector('button');
      if (b) b.onclick = () => { b.disabled = true; b.textContent = 'Checking…'; check(slots, { fromClick: true }); };
    }
    if (get(FOUND) === '1') check(slots, { quiet: true }); // found before: re-check silently
  });
  window.smlAppDetect = { probe, APP, target };
})();
