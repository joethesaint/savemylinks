# SaveMyLinks browser extension

Saves the page you're on to your SaveMyLinks library in one click. One package works in **Google Chrome** and **Microsoft Edge** (Edge replaced Internet Explorer, which Microsoft retired in 2022 and which runs no extensions).

## Install (until it's in the Chrome Web Store / Edge Add-ons)

1. Start the app: `uvicorn app.main:app --port 8000`.
2. Open the extensions page: `chrome://extensions` in Chrome, `edge://extensions` in Edge.
3. Turn on **Developer mode** (top right in Chrome, left panel in Edge).
4. Click **Load unpacked** and pick this `extension` folder.
5. Pin it: click the puzzle-piece icon in the toolbar, then the pin next to SaveMyLinks.

## Use

| Way to save | What it saves |
| --- | --- |
| Click the toolbar icon | The page you're on |
| Alt+Shift+S | The page you're on |
| Right-click the page → *Save this page to SaveMyLinks* | The page you're on |
| Right-click a link → *Save link to SaveMyLinks* | The link's address |
| Right-click the page or the icon → *Save all tabs in this window* | Every web page open in that window, one by one. The first time, the browser asks to let the extension read your tabs' addresses. |

The badge on the icon tells you what happened. Hover over the icon for the full sentence.

| Badge | Meaning |
| --- | --- |
| … | Saving |
| ✓ | Saved. The title, picture and summary arrive about a second later. After *Save all tabs*, hover for how many were new, already saved or skipped. |
| = | Already in your library. Nothing was duplicated. |
| ! | Not saved. Hover for the reason: a browser page (chrome://, edge://), or the app isn't running. |

## Options

Right-click the icon → **Options**: the server address (default `http://127.0.0.1:8000`) and a category every save goes into. **Test connection** checks the app is reachable. A server other than this computer asks the browser's permission once.

## How it works

`background.js` sends `POST /api/save` with the tab's address and title. The server normalizes the address (drops `#fragments`, `utm_*` and other tracking parameters, default ports and letter case in the host), returns the existing link if it's already saved (200) or creates it (201), and fetches the preview in the background.

Permissions: `activeTab` (the current tab's address and title, only when you click), `contextMenus`, `storage` (your options), and access to `127.0.0.1:8000` / `localhost:8000` only. *Save all tabs* asks for `tabs` (your open tabs' addresses and titles) the first time you use it; it never reads or changes the pages themselves.

## Test

`node --test tests/extension/background.test.mjs` (from the repo root) runs `background.js` against a fake browser and a fake app: no browser needed.
