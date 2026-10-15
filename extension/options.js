const DEFAULTS = { server: 'http://127.0.0.1:8000', category: '' };
const $ = (id) => document.getElementById(id);

function say(text, tone) {
  $('status').textContent = text;
  $('status').className = tone || '';
}

function originPattern(server) {
  const u = new URL(server);
  return `${u.protocol}//${u.host}/*`;
}

chrome.storage.sync.get(DEFAULTS).then(({ server, category }) => {
  $('server').value = server;
  $('category').value = category;
});

$('form').addEventListener('submit', async (e) => {
  e.preventDefault();
  let server = $('server').value.trim().replace(/\/+$/, '');
  try { if (!/^https?:$/.test(new URL(server).protocol)) throw 0; }
  catch { say('Enter the full server address, starting with http:// or https://', 'bad'); $('server').focus(); return; }
  // Talking to a server other than the defaults needs the browser's permission, asked once.
  const origins = [originPattern(server)];
  const granted = await chrome.permissions.contains({ origins }) || await chrome.permissions.request({ origins });
  if (!granted) { say("Not saved. The browser didn't allow the extension to reach that server.", 'bad'); return; }
  await chrome.storage.sync.set({ server, category: $('category').value.trim() });
  say('Options saved.', 'ok');
});

$('test').addEventListener('click', async () => {
  const server = $('server').value.trim().replace(/\/+$/, '');
  say('Checking…');
  try {
    const res = await fetch(`${server}/health`);
    if (!res.ok) throw new Error(res.status);
    say(`Connected to SaveMyLinks at ${server}.`, 'ok');
  } catch {
    say(`Can't reach ${server}. Is the app running?`, 'bad');
  }
});
