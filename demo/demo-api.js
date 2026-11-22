// SaveMyLinks demo: answers the app's /api/resources calls inside the browser, so the real
// pages run on a static host (GitHub Pages) with no server. Links are kept in this browser
// only (localStorage), and fall back to memory when storage is blocked.
// It mirrors the FastAPI routes in app/routes/resources.py: newest first, categories
// alphabetical, 201 on save, 409 for an address already saved, 422 for a bad field.
(function () {
  const KEY = 'sml-demo-v2'; // v2: portfolio and source first; a new key so returning visitors see it
  const realFetch = window.fetch.bind(window);
  const now = () => new Date().toISOString();
  const daysAgo = (n) => new Date(Date.now() - n * 86400000).toISOString();

  const SEED = [
    // Newest first in the library: the author's portfolio, then this app's source.
    ['https://joethesaint.github.io/', 'Joseph Taiwo Bamisaye: portfolio', 'Who built SaveMyLinks.', 'Projects', 'joethesaint.github.io', 'Software engineer: backend systems, quantitative analysis, portfolio optimization and scalable web architectures.', 0.05],
    ['https://github.com/joethesaint/savemylinks', 'SaveMyLinks source code', 'This app, on GitHub: MIT licensed.', 'Projects', 'GitHub', 'Save any page in one move and find it again in seconds. FastAPI, Rust, Jinja.', 0.1, 'https://opengraph.githubassets.com/1/joethesaint/savemylinks'],
    ['https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog', 'The dialog element (MDN)', 'How the edit window in this app works.', 'Web', 'MDN Web Docs', 'The HTML dialog element represents a modal or non-modal dialog box.', 1],
    ['https://fastapi.tiangolo.com/tutorial/background-tasks/', 'Background tasks in FastAPI', 'How link previews are fetched after the save returns.', 'Python', 'FastAPI', 'Define background tasks to be run after returning a response.', 2],
    ['https://www.alxafrica.com/', 'ALX Africa', 'Where SaveMyLinks started, as a capstone project.', 'Learning', 'ALX Africa', 'Tech training programmes for Africa.', 3],
    ['https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html', 'SQLAlchemy asyncio', null, 'Python', 'SQLAlchemy', 'Asynchronous I/O support for Core and ORM.', 4],
    ['https://web.dev/articles/optimize-lcp', 'Optimize Largest Contentful Paint', 'Checklist for a fast first screen.', 'Web', 'web.dev', 'A step-by-step guide on how to break down LCP and identify key areas to improve.', 6],
    ['https://www.nngroup.com/articles/ten-usability-heuristics/', '10 Usability Heuristics', 'Read before any design review.', 'Design', 'Nielsen Norman Group', "Jakob Nielsen's 10 general principles for interaction design.", 8],
    ['https://refactoringui.com/', 'Refactoring UI', null, 'Design', 'Refactoring UI', 'Learn how to design awesome UIs by yourself using specific tactics.', 11],
    ['https://docs.pydantic.dev/latest/concepts/validators/', 'Pydantic validators', 'Where the 422 messages come from.', 'Python', 'Pydantic', 'Field and model validators in Pydantic v2.', 13],
    ['https://developer.chrome.com/docs/extensions/develop', 'Build a Chrome extension', 'For the one-click save button.', 'Web', 'Chrome for Developers', 'Learn how to develop extensions for Chrome.', 16],
    ['https://www.smashingmagazine.com/2022/09/inline-validation-web-forms-ux/', 'Inline validation in web forms', null, 'Design', 'Smashing Magazine', 'How to design inline validation that helps instead of nags.', 21],
    ['https://pytest-asyncio.readthedocs.io/', 'pytest-asyncio', null, 'Python', 'pytest-asyncio', 'Pytest support for asyncio.', 25],
  ];
  const seed = () => ({
    next: SEED.length + 1,
    items: SEED.map(([url, title, description, category, site_name, summary, age, image], i) => ({
      id: SEED.length - i, url, title, description, category,
      created_at: daysAgo(age), updated_at: daysAgo(age),
      link_metadata: { title, description: summary, site_name, ...(image ? { image } : {}) },
    })),
  });

  let memory = null;
  function load() {
    try { const s = localStorage.getItem(KEY); if (s) return JSON.parse(s); } catch (e) { /* blocked */ }
    return memory || (memory = seed());
  }
  function save(db) { memory = db; try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) { /* memory only */ } }
  window.smlDemoReset = function () { try { localStorage.removeItem(KEY); } catch (e) { /* blocked */ } memory = null; location.reload(); };

  const json = (status, body) => Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  const norm = (u) => { try { const x = new URL(u); return (x.protocol + '//' + x.host.toLowerCase() + x.pathname.replace(/\/$/, '') + x.search); } catch (e) { return u; } };

  // The same checks as app/schemas.py, in FastAPI's 422 shape, so the pages show their own messages.
  function validate(body, partial) {
    const detail = [];
    const bad = (field, msg, ctx) => detail.push({ loc: ['body', field], msg, input: body[field], ...(ctx ? { ctx } : {}) });
    if (!partial || body.url !== undefined) {
      let ok = false;
      try { ok = /^https?:$/.test(new URL(body.url).protocol); } catch (e) { /* not a URL */ }
      if (!ok) bad('url', 'Input should be a valid URL');
    }
    if (!partial || body.title !== undefined) {
      if (!body.title) bad('title', 'String should have at least 1 character');
      else if (body.title.length > 200) bad('title', 'String too long', { max_length: 200 });
    }
    if (body.description && body.description.length > 1000) bad('description', 'String too long', { max_length: 1000 });
    if (body.category && body.category.length > 100) bad('category', 'String too long', { max_length: 100 });
    return detail;
  }

  // Stands in for the background preview fetch: a static site can't read other pages.
  // A link is marked pending; the first read a second later fills its preview. No timer, because
  // the save page navigates away before a timer would fire.
  function previewLater(r) { r.link_metadata = null; r.pending_at = Date.now(); }
  function ripen(db) {
    let changed = false;
    for (const r of db.items) {
      if (r.link_metadata || !r.pending_at || Date.now() - r.pending_at < 1000) continue;
      let host = r.url; try { host = new URL(r.url).hostname.replace(/^www\./, ''); } catch (e) { /* keep */ }
      r.link_metadata = { title: r.title, site_name: host, description: 'Demo preview. The full app reads the page’s own title, picture and summary here.' };
      delete r.pending_at; changed = true;
    }
    if (changed) save(db);
  }

  function handle(method, url, body) {
    const db = load();
    ripen(db);
    const path = url.pathname.replace(/\/+$/, '') || '/';
    const m = /^\/api\/resources\/(\d+)(\/metadata)?$/.exec(path);

    if (path === '/api/resources/categories' && method === 'GET') {
      return json(200, [...new Set(db.items.map((r) => r.category).filter(Boolean))].sort());
    }
    if (path === '/api/resources' && method === 'GET') {
      const q = (url.searchParams.get('search') || '').toLowerCase();
      const cat = url.searchParams.get('category');
      const page = Math.max(1, Number(url.searchParams.get('page')) || 1);
      const per = Math.min(100, Math.max(1, Number(url.searchParams.get('per_page')) || 20));
      const hits = db.items
        .filter((r) => !cat || r.category === cat)
        .filter((r) => !q || r.title.toLowerCase().includes(q) || (r.description || '').toLowerCase().includes(q))
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      return json(200, { resources: hits.slice((page - 1) * per, page * per), total: hits.length, page, per_page: per });
    }
    if (path === '/api/resources' && method === 'POST') {
      const detail = validate(body, false);
      if (detail.length) return json(422, { detail });
      if (db.items.some((r) => norm(r.url) === norm(body.url))) return json(409, { detail: 'A resource with this URL already exists' });
      const r = { id: db.next++, url: body.url, title: body.title, description: body.description || null, category: body.category || null, created_at: now(), updated_at: now(), link_metadata: null };
      previewLater(r); db.items.push(r); save(db);
      return json(201, r);
    }
    if (m) {
      const id = Number(m[1]);
      const r = db.items.find((x) => x.id === id);
      if (!r) return json(404, { detail: 'Resource not found' });
      if (m[2] && method === 'POST') {
        if (!r.link_metadata && !r.pending_at) { previewLater(r); save(db); }
        return json(200, r);
      }
      if (method === 'GET') return json(200, r);
      if (method === 'DELETE') { db.items = db.items.filter((x) => x.id !== id); save(db); return json(200, { message: 'Resource deleted successfully' }); }
      if (method === 'PUT') {
        const detail = validate(body, true);
        if (detail.length) return json(422, { detail });
        if (body.url && db.items.some((x) => x.id !== id && norm(x.url) === norm(body.url))) return json(409, { detail: 'A resource with this URL already exists' });
        if (body.url && norm(body.url) !== norm(r.url)) previewLater(r);
        for (const k of ['url', 'title', 'description', 'category']) if (body[k] !== undefined) r[k] = body[k];
        r.updated_at = now(); save(db);
        return json(200, r);
      }
    }
    return json(404, { detail: 'Not Found' });
  }

  window.fetch = function (input, init = {}) {
    const raw = typeof input === 'string' ? input : input.url;
    const url = new URL(raw, location.origin);
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return realFetch(input, init);
    let body = {};
    try { body = init.body ? JSON.parse(init.body) : {}; } catch (e) { return json(422, { detail: [{ loc: ['body'], msg: 'Invalid JSON' }] }); }
    // A short pause so loading states and the assistant behave as they do against the server.
    return new Promise((resolve) => setTimeout(resolve, 120)).then(() => handle((init.method || 'GET').toUpperCase(), url, body));
  };
})();
