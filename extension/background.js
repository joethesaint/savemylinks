// SaveMyLinks extension: one code path for the toolbar button, the keyboard
// shortcut and the right-click menu. The badge shows what happened:
//   "…" saving   "✓" saved   "=" already saved   "!" not saved (hover for why)

const DEFAULTS = { server: 'http://127.0.0.1:8000', category: '' };
const BADGE = {
  saving: { text: '…', color: '#53656a' },
  saved: { text: '✓', color: '#1d6b45' },
  already: { text: '=', color: '#2f6f7a' },
  error: { text: '!', color: '#b3261e' },
};
const DEFAULT_TITLE = 'Save this page to SaveMyLinks (Alt+Shift+S)';

async function settings() {
  const stored = await chrome.storage.sync.get(DEFAULTS);
  return { server: String(stored.server || DEFAULTS.server).replace(/\/+$/, ''), category: stored.category || '' };
}

async function show(tabId, state, title) {
  if (tabId == null) return;
  const b = BADGE[state];
  await chrome.action.setBadgeBackgroundColor({ tabId, color: b.color });
  await chrome.action.setBadgeText({ tabId, text: b.text });
  await chrome.action.setTitle({ tabId, title: title || DEFAULT_TITLE });
}

function isWebPage(url) {
  return /^https?:\/\//i.test(url || '');
}

// One POST to the app. No badge: callers decide what to show.
// Returns { state: 'saved' | 'already' | 'error', resource?, why?, offline? }.
async function post(page, server, category) {
  try {
    const res = await fetch(`${server}/api/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: page.url, title: page.title || null, category: category || null }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 201) return { state: 'saved', resource: body.resource };
    if (res.status === 200) return { state: 'already', resource: body.resource };
    const why = typeof body.detail === 'string' ? body.detail : `The server answered ${res.status}.`;
    return { state: 'error', why };
  } catch (e) {
    return { state: 'error', offline: true, why: `SaveMyLinks isn't reachable at ${server}. Start the app, or change the address in the extension's options.` };
  }
}

// The one save path. `page` = { url, title }; `tabId` is where the badge goes.
async function save(page, tabId) {
  if (!isWebPage(page.url)) {
    await show(tabId, 'error', "This page can't be saved: only web pages (http or https) can.");
    return { ok: false, reason: 'not-web' };
  }
  const { server, category } = await settings();
  await show(tabId, 'saving', 'Saving…');
  const r = await post(page, server, category);
  if (r.state === 'saved') {
    await show(tabId, 'saved', `Saved${category ? ' to ' + category : ''}: ${r.resource.title}`);
    return { ok: true, created: true, resource: r.resource };
  }
  if (r.state === 'already') {
    await show(tabId, 'already', `Already in your library: ${r.resource.title}`);
    return { ok: true, created: false, resource: r.resource };
  }
  await show(tabId, 'error', `Not saved. ${r.why}`);
  return { ok: false, reason: r.offline ? 'offline' : r.why };
}

function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}

// Save every web page open in the window of `tab`, one at a time (the app dedupes).
// Reading other tabs' addresses needs the optional `tabs` permission: asked once, here,
// while the right-click still counts as the user's gesture (granted = no prompt).
async function saveAllTabs(tab) {
  const tabId = tab && tab.id;
  const granted = await chrome.permissions.request({ permissions: ['tabs'] }).catch(() => false);
  if (!granted) {
    await show(tabId, 'error', "Not saved. Saving all tabs needs permission to read your tabs' addresses.");
    return { ok: false, reason: 'no-permission' };
  }
  const tabs = await chrome.tabs.query(tab && tab.windowId != null ? { windowId: tab.windowId } : { currentWindow: true });
  const seen = new Set();
  const pages = [];
  for (const t of tabs) {
    if (!isWebPage(t.url) || seen.has(t.url)) continue;
    seen.add(t.url);
    pages.push({ url: t.url, title: t.title });
  }
  const skipped = tabs.length - pages.length;
  if (!pages.length) {
    await show(tabId, 'error', 'Nothing to save: no web pages (http or https) are open in this window.');
    return { ok: false, reason: 'nothing', saved: 0, already: 0, failed: 0, skipped };
  }
  const { server, category } = await settings();
  const count = { saved: 0, already: 0, failed: 0 };
  let lastWhy = '';
  for (let i = 0; i < pages.length; i++) {
    await show(tabId, 'saving', `Saving ${i + 1} of ${pages.length}…`);
    const r = await post(pages[i], server, category);
    if (r.state === 'saved') count.saved++;
    else if (r.state === 'already') count.already++;
    else {
      count.failed++;
      lastWhy = r.why;
      if (r.offline) { count.failed += pages.length - i - 1; break; } // the app is down: stop asking
    }
  }
  const parts = [];
  if (count.saved) parts.push(`Saved ${plural(count.saved, 'tab', 'tabs')}${category ? ' to ' + category : ''}`);
  if (count.already) parts.push(`${count.already} already in your library`);
  if (count.failed) parts.push(`${count.failed} not saved (${lastWhy})`);
  if (skipped) parts.push(`${plural(skipped, 'tab', 'tabs')} skipped (not web pages or repeats)`);
  const state = count.failed ? 'error' : count.saved ? 'saved' : 'already';
  await show(tabId, state, parts.join('. ') + '.');
  return { ok: !count.failed, ...count, skipped };
}

// Toolbar button and Alt+Shift+S (the shortcut runs the action).
chrome.action.onClicked.addListener((tab) => save({ url: tab.url, title: tab.title }, tab.id));

// Right-click: save the page, the link under the pointer, or every tab in the window.
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: 'save-page', title: 'Save this page to SaveMyLinks', contexts: ['page'] });
    chrome.contextMenus.create({ id: 'save-link', title: 'Save link to SaveMyLinks', contexts: ['link'] });
    chrome.contextMenus.create({ id: 'save-all-tabs', title: 'Save all tabs in this window', contexts: ['page', 'action'] });
  });
});
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'save-all-tabs') saveAllTabs(tab);
  else if (info.menuItemId === 'save-link') save({ url: info.linkUrl, title: info.selectionText || '' }, tab && tab.id);
  else save({ url: info.pageUrl || (tab && tab.url), title: tab && tab.title }, tab && tab.id);
});

// The badge describes this page only: clear it when the tab goes somewhere else.
chrome.tabs.onUpdated.addListener((tabId, change) => {
  if (change.url) {
    chrome.action.setBadgeText({ tabId, text: '' });
    chrome.action.setTitle({ tabId, title: DEFAULT_TITLE });
  }
});

// Exposed for the options page's "Test connection" and for automated tests.
self.smlSave = save;
self.smlSaveAllTabs = saveAllTabs;
