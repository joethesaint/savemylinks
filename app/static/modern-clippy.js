// Modern Clippy: a small sprite player for the Clippy agent.
// Animation data (agent.json) and the player logic follow clippy.js (MIT, © Fireplace Inc, Pooya Parsa).
// The Clippy character and sprite sheet are Microsoft's.
//
// Exports: initClippy({ basePath }) → ModernClippy, loadAgent(basePath), ModernClippy.

const STYLE_ID = 'clippy-styles';
const STORE_KEY = 'sml.assistant';

const join = (base, path) => `${String(base || '').replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;
const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

function store(patch) {
  let s = {};
  try { s = JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); } catch { /* storage blocked */ }
  if (patch) {
    s = { ...s, ...patch };
    try { localStorage.setItem(STORE_KEY, JSON.stringify(s)); } catch { /* storage blocked */ }
  }
  return s;
}

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const css = document.createElement('style');
  css.id = STYLE_ID;
  css.textContent = `
  .clippy-agent { position: fixed; right: 20px; bottom: 20px; z-index: 1000; touch-action: none; user-select: none; }
  .clippy-main { cursor: grab; background-repeat: no-repeat; }
  .clippy-agent.is-dragging .clippy-main { cursor: grabbing; }
  .clippy-close { position: absolute; top: -6px; right: -6px; width: 24px; height: 24px; border-radius: 50%;
    border: 1px solid var(--line-strong, #6c7f84); background: var(--surface-raised, #fff); color: var(--ink, #1f2a2e);
    font: 500 14px/1 system-ui, sans-serif; cursor: pointer; opacity: 0; transition: opacity .16s; }
  .clippy-agent:hover .clippy-close, .clippy-close:focus-visible { opacity: 1; }
  .clippy-close:focus-visible, .clippy-main:focus-visible { outline: 2px solid var(--focus, #2f6f7a); outline-offset: 2px; opacity: 1; }
  .clippy-bubble { position: absolute; bottom: calc(100% + 10px); right: 0; width: max-content; max-width: 240px;
    padding: 10px 12px; border-radius: var(--radius-md, 8px); background: var(--surface-raised, #fff); color: var(--ink, #1f2a2e);
    border: 1px solid var(--line-strong, #6c7f84); box-shadow: 0 8px 20px rgba(31,42,46,.12);
    font: 400 14px/20px system-ui, sans-serif; opacity: 0; transform: translateY(8px);
    transition: opacity .2s, transform .48s cubic-bezier(.65,0,.35,1); }
  .clippy-bubble.is-on { opacity: 1; transform: none; }
  .clippy-bubble.is-passive { pointer-events: none; }
  .clippy-bubble::after { content: ""; position: absolute; right: 48px; bottom: -7px; width: 12px; height: 12px;
    background: inherit; border-right: inherit; border-bottom: inherit; transform: rotate(45deg); }
  .clippy-bubble--saved { border-color: var(--success, #1d6b45); }
  .clippy-bubble--duplicate { border-color: var(--notice, #7a5300); }
  .clippy-bubble--invalid { border-color: var(--danger, #b3261e); }
  @media (prefers-reduced-motion: reduce) { .clippy-bubble { transition: none; transform: none; } }`;
  document.head.appendChild(css);
}

export class ModernClippy {
  constructor(agent, mapUrl) {
    this.data = agent;
    this.mapUrl = mapUrl;
    this.timer = null;
    this.current = null;      // { name, frames, index, exiting, resolve }
    this.pending = null;      // at most one waiting animation; a newer request replaces it
    this.idleTimer = null;
    this.bubbleTimer = null;
    this.visible = false;
    this.setupDOM();
  }

  get animations() { return Object.keys(this.data.animations); }
  hasAnimation(name) { return !!this.data.animations[name]; }

  setupDOM() {
    injectStyles();
    const [w, h] = this.data.framesize;
    this.container = document.createElement('div');
    this.container.className = 'clippy-agent';
    this.container.setAttribute('role', 'complementary');
    this.container.setAttribute('aria-label', 'Assistant');

    this.element = document.createElement('div');
    this.element.className = 'clippy-main';
    this.element.tabIndex = 0;
    this.element.setAttribute('aria-label', 'Assistant. Drag to move, or press arrow keys.');
    this.element.style.cssText = `width:${w}px;height:${h}px;background-image:url("${this.mapUrl}")`;

    this.bubble = document.createElement('div');
    this.bubble.className = 'clippy-bubble';
    this.bubble.setAttribute('role', 'status');
    this.bubble.setAttribute('aria-live', 'polite');
    this.bubble.hidden = true;
    this.bubble.addEventListener('click', () => this.closeBubble());

    this.closeBtn = document.createElement('button');
    this.closeBtn.type = 'button';
    this.closeBtn.className = 'clippy-close';
    this.closeBtn.setAttribute('aria-label', 'Hide assistant');
    this.closeBtn.textContent = '×';
    this.closeBtn.addEventListener('click', (e) => { e.stopPropagation(); this.dismiss(); });

    this.container.append(this.bubble, this.element, this.closeBtn);
    this.setupDrag();
    this.restorePosition();
  }

  // ── visibility ──
  show() {
    if (this.visible) return;
    document.body.appendChild(this.container);
    this.visible = true;
    store({ hidden: false });
    this.renderFrame(this.data.animations.RestPose?.frames.at(-1) ?? { images: [[0, 0]] });
    if (reducedMotion()) return;
    this.play('Show').then(() => this.startIdle());
  }
  hide() {
    this.stopIdle();
    this.stop();
    this.closeBubble();
    this.container.remove();
    this.visible = false;
  }
  dismiss() {
    const done = () => { this.hide(); store({ hidden: true }); window.dispatchEvent(new CustomEvent('sml:assistant', { detail: { hidden: true } })); };
    if (reducedMotion() || !this.hasAnimation('Hide')) return done();
    this.stopIdle();
    this.stop(); // a hide request cuts in; it never waits behind the current animation
    this.play('Hide').then(done);
  }

  // ── animation ──
  // Plays an animation by name. Resolves when it ends. Unknown names resolve immediately (a warning, not an error).
  play(name, { timeout = 5000 } = {}) {
    const anim = this.data.animations[name];
    if (!anim) { console.warn(`[clippy] no animation "${name}". Known: ${this.animations.join(', ')}`); return Promise.resolve(false); }
    if (!this.visible) return Promise.resolve(false);
    if (reducedMotion()) { this.renderFrame(anim.frames.at(-1)); return Promise.resolve(true); }
    return new Promise((resolve) => {
      const job = { name, frames: anim.frames, index: 0, exiting: false, resolve };
      if (this.current) {
        // Replace whatever was waiting; ask the running one to leave by its exit branch.
        if (this.pending) this.pending.resolve(false);
        this.pending = job;
        this.current.exiting = true;
        return;
      }
      this.run(job, timeout);
    });
  }
  run(job, timeout) {
    this.current = job;
    const guard = setTimeout(() => { if (this.current === job) job.exiting = true; }, timeout);
    const step = () => {
      const frame = job.frames[job.index];
      this.renderFrame(frame);
      let next = job.index + 1;
      if (job.exiting && frame.exitBranch !== undefined) next = frame.exitBranch;
      // Once asked to leave, stop taking random loop-backs, so a looping animation still ends.
      else if (frame.branching && !job.exiting) {
        let rnd = Math.random() * 100;
        for (const b of frame.branching.branches) { if (rnd <= b.weight) { next = b.frameIndex; break; } rnd -= b.weight; }
      }
      if (next >= job.frames.length || next < 0) {
        this.timer = setTimeout(() => {
          clearTimeout(guard);
          this.current = null;
          job.resolve(true);
          const p = this.pending; this.pending = null;
          if (p) this.run(p, timeout);
        }, frame.duration);
        return;
      }
      job.index = next;
      this.timer = setTimeout(step, frame.duration);
    };
    step();
  }
  stop() {
    clearTimeout(this.timer);
    if (this.current) this.current.resolve(false);
    if (this.pending) this.pending.resolve(false);
    this.current = this.pending = null;
  }
  renderFrame(frame) {
    const img = frame?.images?.[0];
    this.element.style.visibility = img ? 'visible' : 'hidden';   // some frames are intentionally blank
    if (img) this.element.style.backgroundPosition = `-${img[0]}px -${img[1]}px`;
  }

  // ── idle: an occasional idle animation, never speech ──
  startIdle(min = 20000, max = 45000) {
    this.stopIdle();
    if (reducedMotion()) return;
    const idles = this.animations.filter((n) => n.startsWith('Idle'));
    const tick = () => {
      this.idleTimer = setTimeout(async () => {
        if (!this.current && !document.hidden) await this.play(idles[Math.floor(Math.random() * idles.length)], { timeout: 6000 });
        tick();
      }, min + Math.random() * (max - min));
    };
    tick();
  }
  stopIdle() { clearTimeout(this.idleTimer); this.idleTimer = null; }

  // ── speech: one bubble at a time ──
  speak(text, { duration = 5000, tone = '' } = {}) {
    if (!this.visible) return;
    clearTimeout(this.bubbleTimer);
    // A timed bubble lets clicks through to the page under it (it can cover footer controls);
    // a bubble that waits for a click (duration 0) stays clickable.
    this.bubble.className = 'clippy-bubble' + (tone ? ` clippy-bubble--${tone}` : '') + (duration > 0 ? ' is-passive' : '');
    this.bubble.textContent = text;
    this.bubble.hidden = false;
    requestAnimationFrame(() => this.bubble.classList.add('is-on'));
    if (duration > 0) this.bubbleTimer = setTimeout(() => this.closeBubble(), duration);
  }
  closeBubble() {
    clearTimeout(this.bubbleTimer);
    this.bubble.classList.remove('is-on');
    setTimeout(() => { if (!this.bubble.classList.contains('is-on')) this.bubble.hidden = true; }, 200);
  }

  // ── position: pointer drag (mouse, touch, pen) and arrow keys, remembered per browser ──
  setupDrag() {
    let start = null;
    this.element.addEventListener('pointerdown', (e) => {
      const r = this.container.getBoundingClientRect();
      start = { id: e.pointerId, dx: e.clientX - r.left, dy: e.clientY - r.top, moved: false };
      this.element.setPointerCapture(e.pointerId);
    });
    this.element.addEventListener('pointermove', (e) => {
      if (!start || e.pointerId !== start.id) return;
      if (!start.moved) { start.moved = true; this.container.classList.add('is-dragging'); this.stopIdle(); }
      this.placeAt(e.clientX - start.dx, e.clientY - start.dy);
    });
    const end = () => {
      if (!start) return;
      const moved = start.moved; start = null;
      this.container.classList.remove('is-dragging');
      if (moved) { this.savePosition(); this.startIdle(); }
    };
    this.element.addEventListener('pointerup', end);
    this.element.addEventListener('pointercancel', end);
    this.element.addEventListener('keydown', (e) => {
      const step = e.shiftKey ? 40 : 10;
      const moves = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
      if (e.key === 'Escape') { this.closeBubble(); return; }
      if (!moves[e.key]) return;
      e.preventDefault();
      const r = this.container.getBoundingClientRect();
      this.placeAt(r.left + moves[e.key][0], r.top + moves[e.key][1]);
      this.savePosition();
    });
    window.addEventListener('resize', () => { const r = this.container.getBoundingClientRect(); this.placeAt(r.left, r.top); });
  }
  placeAt(left, top) {
    const r = this.element.getBoundingClientRect();
    const x = Math.max(8, Math.min(left, window.innerWidth - r.width - 8));
    const y = Math.max(8, Math.min(top, window.innerHeight - r.height - 8));
    // Anchored right/bottom so the agent stays in its corner when the window resizes.
    this.container.style.right = `${Math.round(window.innerWidth - x - r.width)}px`;
    this.container.style.bottom = `${Math.round(window.innerHeight - y - r.height)}px`;
  }
  savePosition() { store({ right: parseInt(this.container.style.right, 10), bottom: parseInt(this.container.style.bottom, 10) }); }
  restorePosition() {
    const s = store();
    if (Number.isFinite(s.right)) this.container.style.right = `${Math.max(8, s.right)}px`;
    if (Number.isFinite(s.bottom)) this.container.style.bottom = `${Math.max(8, s.bottom)}px`;
  }
}

export async function loadAgent(basePath = '/static/', name = 'Clippy') {
  const dir = join(basePath, `agents/${name}`);
  const mapUrl = join(dir, 'map.png');
  const [agent] = await Promise.all([
    fetch(join(dir, 'agent.json')).then((r) => { if (!r.ok) throw new Error(`agent.json: HTTP ${r.status}`); return r.json(); }),
    new Promise((ok, fail) => { const i = new Image(); i.onload = ok; i.onerror = () => fail(new Error(`map.png failed to load: ${mapUrl}`)); i.src = mapUrl; }),
  ]);
  return new ModernClippy(agent, mapUrl);
}

// Creates the agent. Shows it unless the person hid it before (store: sml.assistant.hidden).
export async function initClippy({ basePath = '/static/', show = true } = {}) {
  const agent = await loadAgent(basePath);
  if (show && !store().hidden) agent.show();
  return agent;
}

export const assistantPrefs = { get: () => store(), set: (p) => store(p) };
