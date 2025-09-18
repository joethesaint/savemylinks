(function(n,a){typeof exports=="object"&&typeof module<"u"?a(exports):typeof define=="function"&&define.amd?define(["exports"],a):(n=typeof globalThis<"u"?globalThis:n||self,a(n.ModernClippy={}))})(this,function(n){"use strict";var c=Object.defineProperty;var g=(n,a,m)=>a in n?c(n,a,{enumerable:!0,configurable:!0,writable:!0,value:m}):n[a]=m;var r=(n,a,m)=>g(n,typeof a!="symbol"?a+"":a,m);class a{constructor(i){r(this,"element");r(this,"container");r(this,"currentAnimation");r(this,"queue",[]);r(this,"data");r(this,"overlay");this.data=i,this.setupDOM()}setupDOM(){this.container=document.createElement("div"),this.container.className="clippy-agent",this.container.style.cssText=`
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 1000;
    `,this.element=document.createElement("div"),this.element.className="clippy-main",this.element.style.cssText=`
      position: relative;
      width: ${this.data.framesize[0]}px;
      height: ${this.data.framesize[1]}px;
    `,this.overlay=document.createElement("div"),this.overlay.className="clippy-overlay",this.overlay.style.cssText=`
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: none;
    `,this.container.appendChild(this.element),this.container.appendChild(this.overlay)}show(){document.body.appendChild(this.container),this.play("Idle")}hide(){this.container.remove()}async play(i){const e=this.data.animations[i];if(!e){console.error(`Animation ${i} not found`);return}if(this.currentAnimation){if(e.useQueue)return new Promise(t=>{this.queue.push(async()=>{await this.playAnimation(e),t()})});clearTimeout(this.currentAnimation)}return this.playAnimation(e)}async playAnimation(i){return new Promise(e=>{let t=0;const o=()=>{const s=i.frames[t];if(this.renderFrame(s),t++,t<i.frames.length)this.currentAnimation=setTimeout(o,s.duration);else{if(this.currentAnimation=void 0,this.queue.length>0){const d=this.queue.shift();d==null||d()}e()}};o()})}renderFrame(i){const{imageMap:e,position:t}=i;this.element.style.cssText=`
      position: relative;
      width: ${e.width}px;
      height: ${e.height}px;
      background-image: url(${e.source});
      background-position: -${e.x}px -${e.y}px;
      transform: translate(${t.x}px, ${t.y}px);
    `}speak(i,e=3e3){const t=document.createElement("div");t.className="clippy-bubble",t.style.cssText=`
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
    `,t.textContent=i,this.overlay.appendChild(t),requestAnimationFrame(()=>{t.style.opacity="1"}),setTimeout(()=>{t.style.opacity="0",setTimeout(()=>t.remove(),300)},e)}moveTo(i,e,t=1e3){const o=parseInt(this.container.style.right)||20,s=parseInt(this.container.style.bottom)||20,d=this.container.animate([{right:`${o}px`,bottom:`${s}px`},{right:`${i}px`,bottom:`${e}px`}],{duration:t,easing:"ease-in-out",fill:"forwards"});d.onfinish=()=>{this.container.style.right=`${i}px`,this.container.style.bottom=`${e}px`},t===0&&(this.container.style.right=`${i}px`,this.container.style.bottom=`${e}px`)}}function m(u){const t=o=>({frames:o.map(s=>({duration:s.duration,imageMap:{source:`${u}/agents/Clippy/map.png`,x:s.images[0][0],y:s.images[0][1],width:124,height:93},position:{x:0,y:s.images[0][1]===0?0:-10}})),useQueue:!0});return{Idle:{frames:[{duration:400,imageMap:{source:`${u}/agents/Clippy/map.png`,x:0,y:0,width:124,height:93},position:{x:0,y:0}}],useQueue:!1},Wave:t([{duration:100,images:[[1116,1767]]},{duration:100,images:[[1240,1767]]},{duration:100,images:[[1364,1767]]},{duration:100,images:[[1488,1767]]},{duration:100,images:[[1612,1767]]},{duration:100,images:[[1736,1767]]},{duration:100,images:[[1860,1767]]},{duration:100,images:[[1984,1767]]},{duration:100,images:[[2108,1767]]},{duration:100,images:[[2232,1767]]},{duration:100,images:[[2356,1767]]},{duration:100,images:[[2480,1767]]},{duration:100,images:[[2604,1767]]},{duration:100,images:[[2728,1767]]}]),Thinking:t([{duration:100,images:[[124,93]]},{duration:100,images:[[248,93]]},{duration:100,images:[[372,93]]},{duration:100,images:[[496,93]]},{duration:100,images:[[620,93]]},{duration:100,images:[[744,93]]},{duration:100,images:[[868,93]]},{duration:100,images:[[992,93]]}]),Explain:t([{duration:100,images:[[1116,186]]},{duration:100,images:[[1240,186]]},{duration:900,images:[[1364,186]]},{duration:100,images:[[1240,186]]},{duration:100,images:[[1116,186]]}]),GetAttention:t([{duration:100,images:[[1240,651]]},{duration:100,images:[[1364,651]]},{duration:100,images:[[1488,651]]},{duration:100,images:[[1612,651]]},{duration:100,images:[[1736,651]]},{duration:100,images:[[1860,651]]},{duration:100,images:[[1984,651]]},{duration:100,images:[[2108,651]]}]),Congratulate:t([{duration:100,images:[[0,0]]},{duration:100,images:[[124,0]]},{duration:100,images:[[248,0]]},{duration:100,images:[[372,0]]},{duration:100,images:[[496,0]]},{duration:100,images:[[620,0]]},{duration:100,images:[[744,0]]},{duration:100,images:[[868,0]]}])}}async function p(u,i=""){const e=`${i}/agents/Clippy/map.png`;return await new Promise((t,o)=>{const s=new Image;s.onload=t,s.onerror=o,s.src=e}),new a({animations:m(i),framesize:[124,93],overlayCount:1,sounds:[],sizes:[[124,93]]})}async function l(u={basePath:""}){const i=await p("Clippy",u.basePath);return i.show(),i}n.ModernClippy=a,n.initClippy=l,n.loadAgent=p,Object.defineProperty(n,Symbol.toStringTag,{value:"Module"})});
