// Demo only: is the SaveMyLinks app running on this computer? If so, offer the real library.
//
// The check loads one tiny image from the app (http://127.0.0.1:8000, the app's default
// address). It reads nothing and sends nothing. Browsers may ask before a website reaches
// into this computer ("local network access"), so the first check runs only when the visitor
// clicks; after a hit, later visits check by themselves (permission is already given).
(function () {
  const APP = 'http://127.0.0.1:8000/';
  const KEY = 'sml-app-found';
  const remembered = () => { try { return localStorage.getItem(KEY) === '1'; } catch (e) { return false; } };
  const remember = (found) => { try { found ? localStorage.setItem(KEY, '1') : localStorage.removeItem(KEY); } catch (e) { /* blocked */ } };

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

  function found(slots) {
    for (const el of slots) {
      el.innerHTML = '';
      const strong = document.createElement('strong');
      strong.textContent = 'SaveMyLinks is running on this computer. ';
      const a = Object.assign(document.createElement('a'), { href: APP, textContent: 'Open your library' });
      el.append(strong, a, ' (real previews, your own links).');
    }
  }

  function notFound(slots) {
    for (const el of slots) {
      el.innerHTML = '';
      el.append('Not running on this computer at 127.0.0.1:8000. ');
      el.append(Object.assign(document.createElement('a'), { href: 'download.html', textContent: 'Get the app' }));
      el.append(', open it, then try again.');
    }
  }

  async function check(slots, { quiet = false } = {}) {
    const ok = await probe();
    remember(ok);
    if (ok) found(slots);
    else if (!quiet) notFound(slots);
    return ok;
  }

  document.addEventListener('DOMContentLoaded', () => {
    const slots = [...document.querySelectorAll('[data-app-detect]')];
    if (!slots.length) return;
    for (const el of slots) {
      const b = el.querySelector('button');
      if (b) b.onclick = () => { b.disabled = true; b.textContent = 'Checking…'; check(slots); };
    }
    if (remembered()) check(slots, { quiet: true }); // found before: re-check silently
  });
  window.smlAppDetect = { probe, APP };
})();
