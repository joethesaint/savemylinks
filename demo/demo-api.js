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

  // Images are each site's own share picture (og:image, fetched 22 Nov 2026). FastAPI, ALX,
  // SQLAlchemy, Chrome docs and pytest-asyncio publish none, so they show the stand-in, as in the app.
  const SEED = [
    // Newest first in the library: the author's portfolio, then this app's source.
    ['https://joethesaint.github.io/', 'Joseph Taiwo Bamisaye: portfolio', 'Who built SaveMyLinks.', 'Projects', 'joethesaint.github.io', 'Software engineer: backend systems, quantitative analysis, portfolio optimization and scalable web architectures.', 0.05, 'https://joethesaint.github.io/og-image.jpg'],
    ['https://github.com/joethesaint/savemylinks', 'SaveMyLinks source code', 'This app, on GitHub: MIT licensed.', 'Projects', 'GitHub', 'Save any page in one move and find it again in seconds. FastAPI, Rust, Jinja.', 0.1, 'https://opengraph.githubassets.com/1/joethesaint/savemylinks'],
    ['https://developer.mozilla.org/en-US/docs/Web/HTML/Element/dialog', 'The dialog element (MDN)', 'How the edit window in this app works.', 'Web', 'MDN Web Docs', 'The HTML dialog element represents a modal or non-modal dialog box.', 1, 'https://developer.mozilla.org/mdn-social-image.46ac2375.png'],
    ['https://fastapi.tiangolo.com/tutorial/background-tasks/', 'Background tasks in FastAPI', 'How link previews are fetched after the save returns.', 'Python', 'FastAPI', 'Define background tasks to be run after returning a response.', 2],
    ['https://www.alxafrica.com/', 'ALX Africa', 'Where SaveMyLinks started, as a capstone project.', 'Learning', 'ALX Africa', 'Tech training programmes for Africa.', 3],
    ['https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html', 'SQLAlchemy asyncio', null, 'Python', 'SQLAlchemy', 'Asynchronous I/O support for Core and ORM.', 4],
    ['https://web.dev/articles/optimize-lcp', 'Optimize Largest Contentful Paint', 'Checklist for a fast first screen.', 'Web', 'web.dev', 'A step-by-step guide on how to break down LCP and identify key areas to improve.', 6, 'https://web.dev/static/articles/optimize-lcp/image/thumbnail.png'],
    ['https://www.nngroup.com/articles/ten-usability-heuristics/', '10 Usability Heuristics', 'Read before any design review.', 'Design', 'Nielsen Norman Group', "Jakob Nielsen's 10 general principles for interaction design.", 8, 'https://media.nngroup.com/media/articles/opengraph_images/Updated10HeuristicSocialCard-36.png'],
    ['https://refactoringui.com/', 'Refactoring UI', null, 'Design', 'Refactoring UI', 'Learn how to design awesome UIs by yourself using specific tactics.', 11, 'https://refactoringui.com/img/homepage/og-image.png'],
    ['https://docs.pydantic.dev/latest/concepts/validators/', 'Pydantic validators', 'Where the 422 messages come from.', 'Python', 'Pydantic', 'Field and model validators in Pydantic v2.', 13, 'https://pydantic.dev/docs/og/validation/latest/concepts/validators.png'],
    ['https://developer.chrome.com/docs/extensions/develop', 'Build a Chrome extension', 'For the one-click save button.', 'Web', 'Chrome for Developers', 'Learn how to develop extensions for Chrome.', 16],
    ['https://www.smashingmagazine.com/2022/09/inline-validation-web-forms-ux/', 'Inline validation in web forms', null, 'Design', 'Smashing Magazine', 'How to design inline validation that helps instead of nags.', 21, 'https://archive.smashing.media/assets/344dbf88-fdf9-42bb-adb4-46f01eedd629/64066efe-71fa-45b6-8e86-caf46c423b64/clean-up-input-ux-pattern.jpg'],
    ['https://pytest-asyncio.readthedocs.io/', 'pytest-asyncio', null, 'Python', 'pytest-asyncio', 'Pytest support for asyncio.', 25],
  ];
  // Sample tags, by position in SEED.
  const SEED_TAGS = [
    ['portfolio'], ['savemylinks', 'rust', 'python'], ['html', 'ui'], ['python', 'async'], ['learning'],
    ['python', 'async', 'database'], ['performance'], ['ux'], ['ui', 'ux'], ['python', 'validation'],
    ['browser'], ['ux', 'forms'], ['python', 'testing', 'async'],
  ];
  const seed = () => ({
    next: SEED.length + 1,
    items: SEED.map(([url, title, description, category, site_name, summary, age, image], i) => ({
      id: SEED.length - i, url, title, description, category, tags: SEED_TAGS[i] || [],
      created_at: daysAgo(age), updated_at: daysAgo(age),
      link_metadata: { title, description: summary, site_name, ...(image ? { image } : {}) },
    })),
  });

  const norm0 = (u) => { try { const x = new URL(u); return x.host.toLowerCase() + x.pathname.replace(/\/$/, ''); } catch (e) { return u; } };
  // What the demo "knows" about its sample pages: "Fetch preview again" gives these back, and
  // visitors who saved the demo before the pictures were added get them on their next visit.
  const KNOWN = new Map(seed().items.map((r) => [norm0(r.url), r.link_metadata]));
  const KNOWN_TAGS = new Map(seed().items.map((r) => [norm0(r.url), r.tags]));
  const PORTFOLIO = SEED[0][0];

  let memory = null;
  function load() {
    try {
      const s = localStorage.getItem(KEY);
      if (s) {
        const db = JSON.parse(s);
        for (const r of db.items) {
          const k = KNOWN.get(norm0(r.url));
          if (k && k.image && r.link_metadata && !r.link_metadata.image) r.link_metadata = { ...r.link_metadata, image: k.image };
          if (!Array.isArray(r.tags)) r.tags = KNOWN_TAGS.get(norm0(r.url)) || [];
        }
        return db;
      }
    } catch (e) { /* blocked */ }
    return memory || (memory = seed());
  }
  function save(db) { memory = db; try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) { /* memory only */ } }
  // Clear all: start an empty library, keeping only the author's portfolio (delete that too if you like).
  window.smlDemoClear = function () {
    const db = load();
    const keep = db.items.filter((r) => norm0(r.url) === norm0(PORTFOLIO));
    db.items = keep.length ? keep : seed().items.filter((r) => r.url === PORTFOLIO);
    save(db); location.reload();
  };
  window.smlDemoReset = function () { try { localStorage.removeItem(KEY); } catch (e) { /* blocked */ } memory = null; location.reload(); };

  const json = (status, body) => Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  const norm = (u) => { try { const x = new URL(u); return (x.protocol + '//' + x.host.toLowerCase() + x.pathname.replace(/\/$/, '') + x.search); } catch (e) { return u; } };

  // Tags exactly as app/schemas.py normalize_tags: no leading #, no quotes or commas, lowercase,
  // spaces as -, no empties, no repeats. Returns null when a tag is too long.
  function normalizeTags(list) {
    const out = [];
    for (const raw of list) {
      const t = raw.trim().replace(/^#+/, '').trim().replace(/[",]/g, '').toLowerCase().replace(/\s+/g, '-');
      if (!t) continue;
      if ([...t].length > 30) return null;
      if (!out.includes(t)) out.push(t);
    }
    return out;
  }

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
    if (body.tags !== undefined && body.tags !== null) {
      if (!Array.isArray(body.tags)) bad('tags', 'Input should be a valid list');
      else if (body.tags.length > 10) bad('tags', `List should have at most 10 items after validation, not ${body.tags.length}`, { max_length: 10 });
      else if (body.tags.some((t) => typeof t !== 'string')) bad('tags', 'Input should be a valid string');
      else if (!normalizeTags(body.tags)) bad('tags', 'Value error, Each tag should have at most 30 characters');
    }
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

    if (path === '/api/resources/facets' && method === 'GET') {
      const count = (values) => {
        const m = new Map();
        values.forEach((v) => m.set(v, (m.get(v) || 0) + 1));
        return [...m].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([name, n]) => ({ name, count: n }));
      };
      return json(200, {
        total: db.items.length,
        categories: count(db.items.map((r) => r.category).filter(Boolean)),
        tags: count(db.items.flatMap((r) => r.tags || [])),
      });
    }
    if (path === '/api/resources/categories' && method === 'GET') {
      return json(200, [...new Set(db.items.map((r) => r.category).filter(Boolean))].sort());
    }
    if (path === '/api/resources' && method === 'GET') {
      const q = (url.searchParams.get('search') || '').toLowerCase();
      const cat = url.searchParams.get('category');
      const rawTag = url.searchParams.get('tag');
      const tag = rawTag ? ((normalizeTags([rawTag]) || [rawTag])[0] || null) : null;
      const page = Math.max(1, Number(url.searchParams.get('page')) || 1);
      const per = Math.min(100, Math.max(1, Number(url.searchParams.get('per_page')) || 20));
      const hits = db.items
        .filter((r) => !cat || r.category === cat)
        .filter((r) => !tag || (r.tags || []).includes(tag))
        .filter((r) => !q || r.title.toLowerCase().includes(q) || (r.description || '').toLowerCase().includes(q)
          || (r.tags || []).some((t) => t.includes(q)))
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
      return json(200, { resources: hits.slice((page - 1) * per, page * per), total: hits.length, page, per_page: per });
    }
    if (path === '/api/resources' && method === 'POST') {
      const detail = validate(body, false);
      if (detail.length) return json(422, { detail });
      if (db.items.some((r) => norm(r.url) === norm(body.url))) return json(409, { detail: 'A resource with this URL already exists' });
      const r = { id: db.next++, url: body.url, title: body.title, description: body.description || null, category: body.category || null, tags: normalizeTags(body.tags || []), created_at: now(), updated_at: now(), link_metadata: null };
      previewLater(r); db.items.push(r); save(db);
      return json(201, r);
    }
    if (m) {
      const id = Number(m[1]);
      const r = db.items.find((x) => x.id === id);
      if (!r) return json(404, { detail: 'Resource not found' });
      if (m[2] && method === 'POST') {
        const k = KNOWN.get(norm0(r.url));
        if (k) { r.link_metadata = { ...k }; delete r.pending_at; save(db); }
        else if (!r.link_metadata && !r.pending_at) { previewLater(r); save(db); }
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
        if (body.tags !== undefined) r.tags = normalizeTags(body.tags || []);
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
