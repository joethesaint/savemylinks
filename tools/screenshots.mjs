// README visuals: screenshots and the keyboard-flow frames, taken from the demo build with its
// sample links (nothing personal), by driving headless Chrome over the DevTools protocol.
//
//   python demo/build.py _shots/savemylinks && python -m http.server 5180 --directory _shots
//   node tools/screenshots.mjs http://127.0.0.1:5180/savemylinks/ docs/screenshots
//   python tools/make_gif.py docs/screenshots/frames docs/screenshots/keyboard.gif
//
// Needs Chrome (set CHROME=path if it isn't in the usual place) and Node 18+.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const BASE = process.argv[2] || 'http://127.0.0.1:5180/savemylinks/';
const OUT = process.argv[3] || 'docs/screenshots';
const CHROME = process.env.CHROME || ['C:/Program Files/Google/Chrome/Application/chrome.exe', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome']
  .find((p) => fs.existsSync(p));
const PORT = 9333;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'sml-shots-'));
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--hide-scrollbars', '--no-first-run', 'about:blank'], { stdio: 'ignore' });

let ws, nextId = 0;
const pending = new Map();
const events = [];
function send(method, params = {}) {
  const id = ++nextId;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const tabs = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = tabs.find((t) => t.type === 'page');
      if (page) {
        ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
        ws.onmessage = (m) => {
          const msg = JSON.parse(m.data);
          if (msg.id && pending.has(msg.id)) { const p = pending.get(msg.id); pending.delete(msg.id); msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result); }
          else if (msg.method) events.push(msg.method);
        };
        return;
      }
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error('Chrome did not start');
}

// A clean demo each time: sample links, Clippy already greeted, tips off, the chosen theme.
const setup = (theme) => `try {
  localStorage.clear();
  localStorage.setItem('theme', '${theme}');
  localStorage.setItem('sml.assistant', JSON.stringify({ greeted: true }));
  localStorage.setItem('sml-tips-v1', JSON.stringify({ shown: [], used: ['c', '.', 'd', 'j', '/'] }));
} catch (e) {}`;
let setupId = null;

async function open(url, { width = 1280, height = 800, scale = 1, mobile = false, theme = 'light', wait = 2500 } = {}) {
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: scale, mobile });
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: theme }, { name: 'prefers-reduced-motion', value: 'no-preference' }] });
  if (setupId) await send('Page.removeScriptToEvaluateOnNewDocument', { identifier: setupId });
  setupId = (await send('Page.addScriptToEvaluateOnNewDocument', { source: setup(theme) })).identifier;
  await send('Page.navigate', { url });
  await sleep(wait);
  // Wait for card pictures (remote previews) so no shot shows an empty placeholder.
  await send('Runtime.evaluate', { awaitPromise: true, expression: `Promise.race([
    Promise.all([...document.images].map((i) => i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; }))),
    new Promise((r) => setTimeout(r, 8000))])` });
  await sleep(300);
}
async function shot(file) {
  const { data } = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(OUT, file), Buffer.from(data, 'base64'));
  console.log('wrote', path.join(OUT, file));
}
async function key(k, code) {
  // Enter needs its key code and a carriage return, or forms don't submit.
  const text = k === 'Enter' ? String.fromCharCode(13) : k.length === 1 ? k : undefined;
  const vk = k === 'Enter' ? 13 : k.length === 1 ? k.toUpperCase().charCodeAt(0) : 0;
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code: code || `Key${k.toUpperCase()}`, text, unmodifiedText: text, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code: code || `Key${k.toUpperCase()}` });
}
const run = (expression) => send('Runtime.evaluate', { expression, awaitPromise: true });

let frame = 0;
async function frameShot(hold = 1) {
  for (let i = 0; i < hold; i++) {
    const { data } = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(OUT, 'frames', String(++frame).padStart(3, '0') + '.png'), Buffer.from(data, 'base64'));
  }
}

try {
  await connect();
  await send('Page.enable');
  await send('Runtime.enable');

  // Stills
  await open(BASE, { theme: 'light' }); await shot('library-light.png');
  await open(BASE, { theme: 'dark' }); await shot('library-dark.png');
  await open(BASE + 'add.html', { theme: 'light' }); await shot('save-link.png');
  await open(BASE + '?keys=1', { theme: 'dark' }); await shot('keyboard-help.png');
  await open(BASE, { width: 390, height: 844, scale: 2, mobile: true, theme: 'light' }); await shot('phone.png');
  await open(BASE + 'download.html', { theme: 'light', wait: 4000 }); await shot('download.png');

  // Keyboard flow (frames for the GIF): select, change category, repeat with ".", delete with Undo, help.
  fs.rmSync(path.join(OUT, 'frames'), { recursive: true, force: true });
  fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
  await open(BASE, { width: 1280, height: 720, theme: 'dark' });
  await run('document.activeElement.blur(); window.scrollTo(0, 0)');
  await frameShot(3);
  await key('j'); await sleep(250); await frameShot(2);
  await key('j'); await sleep(250); await frameShot(2);
  await key('c'); await sleep(400); await frameShot(2);
  await send('Input.insertText', { text: 'Reading' }); await sleep(200); await frameShot(3);
  await key('Enter', 'Enter'); await sleep(900); await frameShot(4);
  await key('j'); await sleep(250); await frameShot(2);
  await key('.', 'Period'); await sleep(900); await frameShot(4);
  await key('j'); await sleep(250); await frameShot(2);
  await key('d'); await sleep(900); await frameShot(4);
  await run(`[...document.querySelectorAll('#toasts button')].find(b => b.textContent === 'Undo')?.click()`); await sleep(1200); await frameShot(3);
  await key('?', 'Slash'); await sleep(500); await frameShot(5);
  console.log(`wrote ${frame} frames`);
} finally {
  try { ws?.close(); } catch {}
  chrome.kill();
}
