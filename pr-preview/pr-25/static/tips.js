// Clippy as a coach (#17): "Did you know?" Vim-style tips, taught by doing.
//
// A tip appears only after you have done something the slow way twice, once per browser, and
// never once you already use that key. It is spoken by Clippy, so it follows his rules: no tip
// while he is hidden ("Hide assistant" silences them), never on a timer, one at a time.
// The library page reports what happens with SMLTips.note(event); nothing else is tracked, and
// nothing leaves the browser.
(function () {
  const KEY = 'sml-tips-v1';
  const TIPS = {
    // slow-way event   -> the tip, and the key whose use makes it unnecessary
    'category-dialog': { key: 'c', anim: 'Explain', text: 'Did you know? Select a link with j and press c to change its category, no edit window needed. In Vim, c means change.' },
    'category-twice':  { key: '.', anim: 'GetAttention', text: 'Did you know? In Vim, . repeats your last change. Press j to move to the next link, then . to give it the same category.' },
    'mouse-delete':    { key: 'd', anim: 'Explain', text: 'Did you know? Select a link with j and press d to delete it. You can still Undo. In Vim, d means delete.' },
    'mouse-open':      { key: 'j', anim: 'GestureUp', text: 'Did you know? j and k move between links like lines in Vim, and o opens the selected one.' },
    'search-click':    { key: '/', anim: 'Searching', text: 'Did you know? Press / anywhere to jump to search, the same key as searching in Vim.' },
  };

  let saved = { shown: [], used: [] };
  try { saved = { ...saved, ...JSON.parse(localStorage.getItem(KEY) || '{}') }; } catch (e) { /* private window: tips still work for this visit */ }
  const persist = () => { try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch (e) { /* blocked */ } };
  const counts = {};
  let speaking = false;

  function show(name) {
    const tip = TIPS[name];
    const agent = window.smlAssistant;
    if (!tip || speaking || !agent || !agent.visible) return false; // hidden Clippy: stay quiet, try again later
    speaking = true;
    agent.play(tip.anim, { timeout: 3000 });
    agent.speak(tip.text, { duration: 10000 });
    setTimeout(() => { speaking = false; }, 10000);
    saved.shown.push(name); persist();
    return true;
  }

  window.SMLTips = {
    // A slow-way event happened. The second time, teach the faster key (once, ever).
    note(event) {
      const tip = TIPS[event];
      if (!tip || saved.shown.includes(event) || saved.used.includes(tip.key)) return;
      counts[event] = (counts[event] || 0) + 1;
      if (counts[event] >= 2 && show(event)) counts[event] = 0;
    },
    // A key was used: its tip is never needed.
    used(key) {
      if (!saved.used.includes(key)) { saved.used.push(key); persist(); }
    },
    reset() { saved = { shown: [], used: [] }; persist(); }, // for "show me the tips again"
    _state: () => ({ shown: [...saved.shown], used: [...saved.used], counts: { ...counts } }),
  };
})();
