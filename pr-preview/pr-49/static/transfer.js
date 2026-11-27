// Move your links: export the whole library to a JSON file, and import a JSON file of links.
// Works in the app and on a phone (the static demo answers the same /api/resources calls in the browser).
// A file is a list of { title, url, description, category, tags }; { resources: [...] } is accepted too.
// Import adds each link once: an address already saved (409) is skipped, never overwritten.
(function () {
  const $ = (s) => document.querySelector(s);
  const toast = (m, o) => (window.SML && window.SML.toast ? window.SML.toast(m, o) : alert(m));
  const FIELDS = ['title', 'url', 'description', 'category', 'tags'];
  const pick = (r) => Object.fromEntries(FIELDS.filter((k) => r[k] != null && r[k] !== '').map((k) => [k, r[k]]));

  async function allLinks() {
    const out = [];
    for (let page = 1; page < 1000; page++) {
      const res = await fetch(`/api/resources/?page=${page}&per_page=100`);
      if (!res.ok) throw new Error(`couldn't read your links (${res.status})`);
      const body = await res.json();
      out.push(...body.resources.map(pick));
      if (out.length >= body.total || body.resources.length === 0) break;
    }
    return out;
  }

  async function exportLinks() {
    try {
      const links = await allLinks();
      const blob = new Blob([JSON.stringify(links, null, 2)], { type: 'application/json' });
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(blob), download: `savemylinks-${new Date().toISOString().slice(0, 10)}.json`,
      });
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
      toast(`Exported ${links.length} link${links.length === 1 ? '' : 's'}.`);
    } catch (e) {
      toast(`Export failed: ${e.message}`, { tone: 'danger' });
    }
  }

  /** The links in a file's text, or an error saying what's wrong with it. */
  function parseLinks(text) {
    let data;
    try { data = JSON.parse(text); } catch (e) { throw new Error("that file isn't JSON"); }
    const list = Array.isArray(data) ? data : Array.isArray(data?.resources) ? data.resources : null;
    if (!list) throw new Error('expected a list of links');
    const links = list.filter((r) => r && typeof r.url === 'string').map((r) => pick({ ...r, title: r.title || r.url }));
    if (!links.length) throw new Error('no links with a url in that file');
    return links;
  }

  async function importLinks(file) {
    let links;
    try { links = parseLinks(await file.text()); } catch (e) { toast(`Import failed: ${e.message}`, { tone: 'danger' }); return; }
    let added = 0, had = 0, failed = 0;
    for (const link of links) {
      try {
        const res = await fetch('/api/resources/', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(link),
        });
        if (res.status === 201) added++; else if (res.status === 409) had++; else failed++;
      } catch (e) { failed++; }
    }
    const parts = [`${added} added`];
    if (had) parts.push(`${had} already saved`);
    if (failed) parts.push(`${failed} couldn't be saved`);
    toast(`Import: ${parts.join(', ')}.`, { tone: failed ? 'danger' : '' });
    if (added) setTimeout(() => location.reload(), 1200);
  }

  function wire() {
    const file = $('#importFile');
    $('#exportBtn')?.addEventListener('click', exportLinks);
    $('#importBtn')?.addEventListener('click', () => file?.click());
    file?.addEventListener('change', () => { if (file.files[0]) importLinks(file.files[0]); file.value = ''; });
  }
  window.SMLTransfer = { parseLinks, pick };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire); else wire();
})();
