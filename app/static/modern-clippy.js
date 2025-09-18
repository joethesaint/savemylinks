var m = Object.defineProperty;
var u = (n, t, e) => t in n ? m(n, t, { enumerable: !0, configurable: !0, writable: !0, value: e }) : n[t] = e;
var o = (n, t, e) => u(n, typeof t != "symbol" ? t + "" : t, e);
class d {
  constructor(t) {
    o(this, "element");
    o(this, "container");
    o(this, "currentAnimation");
    o(this, "queue", []);
    o(this, "data");
    o(this, "overlay");
    this.data = t, this.setupDOM();
  }
  setupDOM() {
    this.container = document.createElement("div"), this.container.className = "clippy-agent", this.container.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 1000;
    `, this.element = document.createElement("div"), this.element.className = "clippy-main", this.element.style.cssText = `
      position: relative;
      width: ${this.data.framesize[0]}px;
      height: ${this.data.framesize[1]}px;
    `, this.overlay = document.createElement("div"), this.overlay.className = "clippy-overlay", this.overlay.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: none;
    `, this.container.appendChild(this.element), this.container.appendChild(this.overlay);
  }
  show() {
    document.body.appendChild(this.container), this.play("Idle");
  }
  hide() {
    this.container.remove();
  }
  async play(t) {
    const e = this.data.animations[t];
    if (!e) {
      console.error(`Animation ${t} not found`);
      return;
    }
    if (this.currentAnimation) {
      if (e.useQueue)
        return new Promise((i) => {
          this.queue.push(async () => {
            await this.playAnimation(e), i();
          });
        });
      clearTimeout(this.currentAnimation);
    }
    return this.playAnimation(e);
  }
  async playAnimation(t) {
    return new Promise((e) => {
      let i = 0;
      const s = () => {
        const a = t.frames[i];
        if (this.renderFrame(a), i++, i < t.frames.length)
          this.currentAnimation = setTimeout(s, a.duration);
        else {
          if (this.currentAnimation = void 0, this.queue.length > 0) {
            const r = this.queue.shift();
            r == null || r();
          }
          e();
        }
      };
      s();
    });
  }
  renderFrame(t) {
    const { imageMap: e, position: i } = t;
    this.element.style.cssText = `
      position: relative;
      width: ${e.width}px;
      height: ${e.height}px;
      background-image: url(${e.source});
      background-position: -${e.x}px -${e.y}px;
      transform: translate(${i.x}px, ${i.y}px);
    `;
  }
  speak(t, e = 3e3) {
    const i = document.createElement("div");
    i.className = "clippy-bubble", i.style.cssText = `
      position: absolute;
      background: white;
      border: 1px solid black;
      border-radius: 5px;
      padding: 8px;
      max-width: 200px;
      top: -60px;
      left: -100px;
      opacity: 0;
      transition: opacity 0.3s;
    `, i.textContent = t, this.overlay.appendChild(i), requestAnimationFrame(() => {
      i.style.opacity = "1";
    }), setTimeout(() => {
      i.style.opacity = "0", setTimeout(() => i.remove(), 300);
    }, e);
  }
  moveTo(t, e, i = 1e3) {
    const s = parseInt(this.container.style.right) || 20, a = parseInt(this.container.style.bottom) || 20, r = this.container.animate([
      { right: `${s}px`, bottom: `${a}px` },
      { right: `${t}px`, bottom: `${e}px` }
    ], {
      duration: i,
      easing: "ease-in-out",
      fill: "forwards"
    });
    r.onfinish = () => {
      this.container.style.right = `${t}px`, this.container.style.bottom = `${e}px`;
    }, i === 0 && (this.container.style.right = `${t}px`, this.container.style.bottom = `${e}px`);
  }
}
function p(n) {
  const i = (s) => ({
    frames: s.map((a) => ({
      duration: a.duration,
      imageMap: {
        source: `${n}/agents/Clippy/map.png`,
        x: a.images[0][0],
        y: a.images[0][1],
        width: 124,
        height: 93
      },
      // Add a small vertical offset for certain animations
      position: {
        x: 0,
        y: a.images[0][1] === 0 ? 0 : -10
      }
    })),
    // Set useQueue true if animation should play sequentially
    useQueue: !0
  });
  return {
    Idle: {
      frames: [{
        duration: 400,
        imageMap: {
          source: `${n}/agents/Clippy/map.png`,
          x: 0,
          y: 0,
          width: 124,
          height: 93
        },
        position: { x: 0, y: 0 }
      }],
      useQueue: !1
    },
    Wave: i([
      { duration: 100, images: [[1116, 1767]] },
      { duration: 100, images: [[1240, 1767]] },
      { duration: 100, images: [[1364, 1767]] },
      { duration: 100, images: [[1488, 1767]] },
      { duration: 100, images: [[1612, 1767]] },
      { duration: 100, images: [[1736, 1767]] },
      { duration: 100, images: [[1860, 1767]] },
      { duration: 100, images: [[1984, 1767]] },
      { duration: 100, images: [[2108, 1767]] },
      { duration: 100, images: [[2232, 1767]] },
      { duration: 100, images: [[2356, 1767]] },
      { duration: 100, images: [[2480, 1767]] },
      { duration: 100, images: [[2604, 1767]] },
      { duration: 100, images: [[2728, 1767]] }
    ]),
    Thinking: i([
      { duration: 100, images: [[124, 93]] },
      { duration: 100, images: [[248, 93]] },
      { duration: 100, images: [[372, 93]] },
      { duration: 100, images: [[496, 93]] },
      { duration: 100, images: [[620, 93]] },
      { duration: 100, images: [[744, 93]] },
      { duration: 100, images: [[868, 93]] },
      { duration: 100, images: [[992, 93]] }
    ]),
    Explain: i([
      { duration: 100, images: [[1116, 186]] },
      { duration: 100, images: [[1240, 186]] },
      { duration: 900, images: [[1364, 186]] },
      { duration: 100, images: [[1240, 186]] },
      { duration: 100, images: [[1116, 186]] }
    ]),
    GetAttention: i([
      { duration: 100, images: [[1240, 651]] },
      { duration: 100, images: [[1364, 651]] },
      { duration: 100, images: [[1488, 651]] },
      { duration: 100, images: [[1612, 651]] },
      { duration: 100, images: [[1736, 651]] },
      { duration: 100, images: [[1860, 651]] },
      { duration: 100, images: [[1984, 651]] },
      { duration: 100, images: [[2108, 651]] }
    ]),
    Congratulate: i([
      { duration: 100, images: [[0, 0]] },
      { duration: 100, images: [[124, 0]] },
      { duration: 100, images: [[248, 0]] },
      { duration: 100, images: [[372, 0]] },
      { duration: 100, images: [[496, 0]] },
      { duration: 100, images: [[620, 0]] },
      { duration: 100, images: [[744, 0]] },
      { duration: 100, images: [[868, 0]] }
    ])
  };
}
async function l(n, t = "") {
  const e = `${t}/agents/Clippy/map.png`;
  return await new Promise((i, s) => {
    const a = new Image();
    a.onload = i, a.onerror = s, a.src = e;
  }), new d({
    animations: p(t),
    framesize: [124, 93],
    overlayCount: 1,
    sounds: [],
    sizes: [[124, 93]]
  });
}
async function g(n = { basePath: "" }) {
  const t = await l("Clippy", n.basePath);
  return t.show(), t;
}
export {
  d as ModernClippy,
  g as initClippy,
  l as loadAgent
};
