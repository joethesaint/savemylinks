// Runs extension/background.js against a fake `chrome` and a fake app (no browser).
// node --test tests/extension/background.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const SRC = readFileSync(new URL('../../extension/background.js', import.meta.url), 'utf8');

function load({ tabs = [], grant = true, app }) {
  const badge = [];
  const requested = [];
  const posted = [];
  const listeners = {};
  const on = (name) => ({ addListener: (f) => { listeners[name] = f; } });
  const chrome = {
    storage: { sync: { get: async (d) => d } },
    action: {
      setBadgeBackgroundColor: async () => {},
      setBadgeText: async ({ text }) => badge.push({ text }),
      setTitle: async ({ title }) => { badge[badge.length - 1].title = title; },
      onClicked: on('action'),
    },
    permissions: { request: async (p) => { requested.push(p); return grant; } },
    tabs: { query: async () => tabs, onUpdated: on('tabUpdated') },
    contextMenus: { removeAll: (cb) => cb(), create: () => {}, onClicked: on('menu') },
    runtime: { onInstalled: on('installed') },
  };
  const fetch = async (url, init) => {
    const body = JSON.parse(init.body);
    posted.push(body.url);
    const r = app(body.url);
    if (r === 'offline') throw new TypeError('Failed to fetch');
    return { status: r.status, json: async () => r.body };
  };
  const self = {};
  vm.runInNewContext(SRC, { chrome, fetch, self, console, URL });
  return { self, badge, requested, posted, last: () => badge[badge.length - 1] };
}

const tab = (url, title = url) => ({ id: 1, windowId: 7, url, title });
const created = (u) => ({ status: 201, body: { resource: { title: u } } });
const exists = (u) => ({ status: 200, body: { resource: { title: u } } });

test('saves every web tab once, skips browser pages and repeats, and sums it up', async () => {
  const t = load({
    tabs: [tab('https://a.dev'), tab('chrome://extensions'), tab('https://b.dev'), tab('https://a.dev'), tab('https://c.dev')],
    app: (u) => (u === 'https://b.dev' ? exists(u) : created(u)),
  });
  const r = await t.self.smlSaveAllTabs(tab('https://a.dev'));
  assert.equal(JSON.stringify(t.requested), '[{"permissions":["tabs"]}]');
  assert.deepEqual(t.posted, ['https://a.dev', 'https://b.dev', 'https://c.dev']);
  assert.deepEqual({ ...r }, { ok: true, saved: 2, already: 1, failed: 0, skipped: 2 });
  assert.equal(t.last().text, '✓');
  assert.equal(t.last().title, 'Saved 2 tabs. 1 already in your library. 2 tabs skipped (not web pages or repeats).');
});

test('all already saved shows "="', async () => {
  const t = load({ tabs: [tab('https://a.dev')], app: exists });
  await t.self.smlSaveAllTabs(tab('https://a.dev'));
  assert.equal(t.last().text, '=');
});

test('permission refused: nothing is read or sent', async () => {
  const t = load({ tabs: [tab('https://a.dev')], grant: false, app: created });
  const r = await t.self.smlSaveAllTabs(tab('https://a.dev'));
  assert.equal(r.reason, 'no-permission');
  assert.deepEqual(t.posted, []);
  assert.equal(t.last().text, '!');
});

test('app not running: stops after the first try and counts the rest as not saved', async () => {
  const t = load({ tabs: [tab('https://a.dev'), tab('https://b.dev'), tab('https://c.dev')], app: () => 'offline' });
  const r = await t.self.smlSaveAllTabs(tab('https://a.dev'));
  assert.deepEqual(t.posted, ['https://a.dev']);
  assert.equal(r.failed, 3);
  assert.equal(t.last().text, '!');
  assert.match(t.last().title, /^3 not saved \(SaveMyLinks isn't reachable at http:\/\/127\.0\.0\.1:8000/);
});

test('a window with no web pages says so', async () => {
  const t = load({ tabs: [tab('chrome://newtab')], app: created });
  const r = await t.self.smlSaveAllTabs(tab('chrome://newtab'));
  assert.equal(r.reason, 'nothing');
  assert.deepEqual(t.posted, []);
});

test('the one-page save still works as before', async () => {
  const t = load({ app: created });
  const r = await t.self.smlSave({ url: 'https://a.dev', title: 'A' }, 1);
  assert.equal(r.created, true);
  assert.equal(t.last().text, '✓');
  assert.equal(t.last().title, 'Saved: https://a.dev');
});
