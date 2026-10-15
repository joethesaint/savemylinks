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

// The one save path. `page` = { url, title }; `tabId` is where the badge goes.
async function save(page, tabId) {
  if (!isWebPage(page.url)) {
    await show(tabId, 'error', "This page can't be saved: only web pages (http or https) can.");
    return { ok: false, reason: 'not-web' };
  }
  const { server, category } = await settings();
  await show(tabId, 'saving', 'Saving…');
  try {
    const res = await fetch(`${server}/api/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: page.url, title: page.title || null, category: category || null }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 201) {
      await show(tabId, 'saved', `Saved${category ? ' to ' + category : ''}: ${body.resource.title}`);
      return { ok: true, created: true, resource: body.resource };
    }
    if (res.status === 200) {
      await show(tabId, 'already', `Already in your library: ${body.resource.title}`);
      return { ok: true, created: false, resource: body.resource };
    }
    const why = typeof body.detail === 'string' ? body.detail : `The server answered ${res.status}.`;
    await show(tabId, 'error', `Not saved. ${why}`);
    return { ok: false, reason: why };
  } catch (e) {
    await show(tabId, 'error', `Not saved. SaveMyLinks isn't reachable at ${server}. Start the server, or change the address in the extension's options.`);
    return { ok: false, reason: 'offline' };
  }
}

// Toolbar button and Alt+Shift+S (the shortcut runs the action).
chrome.action.onClicked.addListener((tab) => save({ url: tab.url, title: tab.title }, tab.id));

// Right-click: save the page, or the link under the pointer.
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: 'save-page', title: 'Save this page to SaveMyLinks', contexts: ['page'] });
    chrome.contextMenus.create({ id: 'save-link', title: 'Save link to SaveMyLinks', contexts: ['link'] });
  });
});
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'save-link') save({ url: info.linkUrl, title: info.selectionText || '' }, tab && tab.id);
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
