"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- Commands name this proxy when the site is served by one ---------- */

if (/^https?:$/.test(location.protocol) && !/^(localhost|127\.)/.test(location.hostname)) {
  $$("[data-origin]").forEach((el) => { el.textContent = location.origin; });
}

$$(".copy").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const text = btn.parentElement.querySelector("code").textContent.trim();
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied";
      btn.classList.add("done");
    } catch {
      btn.textContent = "Select and copy";
    }
    setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("done"); }, 1800);
  });
});

/* ---------- Leesin protocol: a real seal, in this browser ---------- */

// Server-to-browser messages count up from 2**52 (shared/services/security.py).
const OUTBOUND_BASE = 2 ** 52;

const SAMPLE_ALERTS = [
  { id: 41, platform: "roblox", child: "mia_builds", from: "xX_shadow_Xx", probability: 0.53, preview: "send me a pic of you, just for me" },
  { id: 42, platform: "discord", child: "leo.plays", from: "trusted_friend99", probability: 0.71, preview: "dont tell your mom we talk ok" },
  { id: 43, platform: "minecraft", child: "Nova_7", from: "builder_dan", probability: 0.62, preview: "are you home alone right now" },
];

const b64url = (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const hex = (bytes) => Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");

function xorNonce(base, sequence) {
  const nonce = new Uint8Array(base);
  let seq = BigInt(sequence);
  for (let i = nonce.length - 1; i >= 0; i--) {
    nonce[i] ^= Number(seq & 0xffn);
    seq >>= 8n;
  }
  return nonce;
}

let sealCount = 0;

async function sealAlert() {
  const alert = SAMPLE_ALERTS[sealCount % SAMPLE_ALERTS.length];
  const plaintext = JSON.stringify({ type: "alert", ...alert });
  const cipherEl = $("#view-proxy");
  const platform = { roblox: "Roblox", discord: "Discord", minecraft: "Minecraft" }[alert.platform];

  $("#open-risk").textContent = `${Math.round(alert.probability * 100)}%`;
  $("#open-who").textContent = `${alert.child} on ${platform}`;
  $("#open-msg").textContent = `“${alert.preview}”`;

  if (!window.crypto?.subtle) {
    cipherEl.textContent = "This browser can't lock messages here. Open the page over https to see it.";
    return;
  }

  const sessionId = hex(crypto.getRandomValues(new Uint8Array(16)));
  const key = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, false, ["encrypt"]);
  const nonceBase = crypto.getRandomValues(new Uint8Array(12));
  const sequence = OUTBOUND_BASE + 1 + sealCount;
  const nonce = xorNonce(nonceBase, sequence);
  const aad = new TextEncoder().encode(`${sessionId}:${sequence}`);
  const sealed = new Uint8Array(await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce, additionalData: aad }, key, new TextEncoder().encode(plaintext),
  ));

  // The whole sealed frame is long; the first stretch makes the point.
  cipherEl.textContent = `${b64url(sealed).slice(0, 132)}…`;

  sealCount += 1;
  cipherEl.classList.remove("fresh");
  void cipherEl.offsetWidth;
  cipherEl.classList.add("fresh");

  const packet = $("#packet");
  if (packet && !reducedMotion) {
    packet.classList.remove("run");
    void packet.offsetWidth;
    packet.classList.add("run");
  }
}

const sealInterval = setInterval(sealAlert, 5000);
sealAlert();

/* ---------- Build flow: hover a step, its clip plays ---------- */

const tabs = $$(".step-btn");
const panels = $$(".panel");
const desktop = matchMedia("(min-width: 901px)");
const PLACEHOLDER_MS = 6000;
let active = 1;
let hovering = false;
let buildVisible = false;
let placeholderTimer = null;
let progressFrame = null;

function loadVideo(video) {
  if (video.dataset.loaded) return;
  video.dataset.loaded = "1";
  const media = video.closest(".media");
  const sources = $$("source", video);
  // A missing file fails on its <source>, not on the <video>; the last one
  // failing means none of the formats exist yet.
  sources[sources.length - 1].addEventListener("error", () => media.classList.add("missing"));
  sources.forEach((s) => { s.src = s.dataset.src; });
  video.load();
}

function play(video) {
  loadVideo(video);
  const p = video.play();
  if (p) p.catch(() => {});
}

function stopAll(except) {
  $$(".panel video").forEach((v) => { if (v !== except) v.pause(); });
}

function trackProgress(panel) {
  cancelAnimationFrame(progressFrame);
  clearTimeout(placeholderTimer);
  const bar = $(`#tab-${panel.dataset.step} .bar i`);
  const video = $("video", panel);
  const media = $(".media", panel);
  const started = performance.now();

  if (!desktop.matches) return;

  const tick = () => {
    let ratio = 0;
    if (media.classList.contains("missing")) {
      ratio = Math.min(1, (performance.now() - started) / PLACEHOLDER_MS);
      if (ratio >= 1 && !hovering && buildVisible) return advance();
    } else if (video.duration) {
      ratio = video.currentTime / video.duration;
    }
    if (bar) bar.style.transform = `scaleX(${ratio})`;
    progressFrame = requestAnimationFrame(tick);
  };
  tick();
}

function activate(step, { focus = false } = {}) {
  active = step;
  tabs.forEach((t) => {
    const on = Number(t.dataset.step) === step;
    t.setAttribute("aria-selected", String(on));
    t.tabIndex = on ? 0 : -1;
    if (!on) $(".bar i", t).style.transform = "scaleX(0)";
    if (on && focus) t.focus();
  });
  if (!desktop.matches) return;
  panels.forEach((p) => { p.hidden = Number(p.dataset.step) !== step; });
  const panel = panels[step - 1];
  const video = $("video", panel);
  stopAll(video);
  video.currentTime = 0;
  // While someone is looking at one step, it loops; left alone, the flow
  // moves on to the next step when the clip ends.
  video.loop = hovering;
  if (buildVisible) play(video); else loadVideo(video);
  trackProgress(panel);
}

function advance() {
  activate(active % tabs.length + 1);
}

tabs.forEach((tab) => {
  const step = Number(tab.dataset.step);
  tab.addEventListener("mouseenter", () => { if (active !== step) activate(step); });
  tab.addEventListener("focus", () => { if (active !== step) activate(step); });
  tab.addEventListener("click", () => activate(step));
  tab.addEventListener("keydown", (e) => {
    const move = { ArrowRight: 1, ArrowLeft: -1, Home: -99, End: 99 }[e.key];
    if (!move) return;
    e.preventDefault();
    const next = Math.min(tabs.length, Math.max(1, step + move));
    activate(next, { focus: true });
  });
});

panels.forEach((panel) => {
  const video = $("video", panel);
  video.addEventListener("ended", () => {
    if (desktop.matches && !hovering && Number(panel.dataset.step) === active) advance();
  });
});

const flowArea = [$(".flow"), $(".stage")].filter(Boolean);
flowArea.forEach((el) => {
  el.addEventListener("mouseenter", () => {
    hovering = true;
    const v = $("video", panels[active - 1]);
    if (v) v.loop = true;
  });
  el.addEventListener("mouseleave", () => {
    hovering = false;
    const v = $("video", panels[active - 1]);
    if (v) v.loop = false;
    trackProgress(panels[active - 1]);
  });
});

const buildSection = $("#build");
if (buildSection) {
  new IntersectionObserver(([entry]) => {
    buildVisible = entry.isIntersecting;
    if (!desktop.matches) return;
    const v = $("video", panels[active - 1]);
    if (buildVisible) { play(v); trackProgress(panels[active - 1]); }
    else { v.pause(); clearTimeout(placeholderTimer); cancelAnimationFrame(progressFrame); }
  }, { threshold: 0.25 }).observe(buildSection);
}

// Phones: every step is on the page, and each clip plays while it is on screen.
const panelObserver = new IntersectionObserver((entries) => {
  if (desktop.matches) return;
  entries.forEach((entry) => {
    const v = $("video", entry.target);
    v.loop = true;
    if (entry.isIntersecting) play(v); else v.pause();
  });
}, { threshold: 0.6 });
panels.forEach((p) => panelObserver.observe(p));

function applyLayout() {
  if (desktop.matches) {
    activate(active);
  } else {
    panels.forEach((p) => { p.hidden = false; });
    cancelAnimationFrame(progressFrame);
  }
}
desktop.addEventListener("change", applyLayout);
applyLayout();

/* ---------- Playground: a synthetic chat, scored by the real classifier ---------- */

const MIN_MESSAGES = 7; // backend/core/config.py CLASSIFIER_MIN_MESSAGES
const THRESHOLD = 0.5;
const params = new URLSearchParams(location.search);
const API = (params.get("playground") || $('meta[name="tellmom-playground"]')?.content || "/api/playground").replace(/\/$/, "");

const PRESETS = {
  grooming: [
    ["stranger", "hey ur really good at this game"],
    ["child", "thx"],
    ["stranger", "how old r u"],
    ["child", "13"],
    ["stranger", "nice, youre so mature for 13. im 19"],
    ["child", "lol ok"],
    ["stranger", "you can talk to me about anything you know"],
    ["child", "my parents are annoying"],
    ["stranger", "yeah they dont get you like i do"],
    ["stranger", "i can give you robux if you want"],
    ["child", "really?"],
    ["stranger", "yeah but dont tell anyone ok, its our secret"],
    ["child", "ok"],
    ["stranger", "do you have snapchat? we can talk there"],
    ["stranger", "are you home alone right now"],
    ["stranger", "send me a pic of you, just for me"],
  ],
  ordinary: [
    ["stranger", "anyone want to trade"],
    ["child", "i have a golden sword"],
    ["stranger", "what do u want for it"],
    ["child", "50 coins"],
    ["stranger", "deal"],
    ["child", "sent"],
    ["stranger", "thx"],
    ["child", "gg"],
    ["stranger", "anyone doing the raid tonight"],
    ["child", "yeah at 7"],
    ["stranger", "ill be there"],
  ],
};
const NAMES = { stranger: "xX_shadow_Xx", child: "mia_builds" };

const log = $("#log");
const playBtn = $("#play-btn");
const digitsEl = $("#digits");
const verdictEl = $("#verdict");
const fillEl = $("#meter-fill");
const progressEl = $("#progress");

let preset = "grooming";
let cursor = 0;
let messages = [];
let trace = [];
let playing = null;
let pending = Promise.resolve();

$$(".digit .reel", digitsEl).forEach((reel) => {
  reel.innerHTML = Array.from({ length: 10 }, (_, d) => `<span>${d}</span>`).join("");
});

function setDigits(value) {
  const pct = Math.min(99, Math.round(value * 100));
  const ds = [Math.floor(pct / 10), pct % 10];
  $$(".digit .reel", digitsEl).forEach((reel, i) => {
    reel.style.transform = `translateY(-${ds[i] * 10}%)`;
  });
}

const ICONS = {
  wait: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',
  read: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>',
  ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 5 5 9-10"/></svg>',
  flag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 8v5M12 16.5v.01"/><path d="M10.3 3.9 2.6 17.3A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.7L13.7 3.9a2 2 0 0 0-3.4 0Z"/></svg>',
  err: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 8v5M12 16v.01"/></svg>',
};

function setVerdict(kind, title, sub) {
  verdictEl.className = `verdict ${{ flag: "flagged", ok: "ok", err: "error" }[kind] || ""}`;
  $("#verdict-icon").innerHTML = ICONS[kind];
  $("#verdict-title").textContent = title;
  $("#verdict-sub").textContent = sub;
}

function renderReadout() {
  const n = messages.length;
  const scored = n >= MIN_MESSAGES && trace.length === n;
  const score = scored ? trace[n - 1] : 0;
  const flagged = scored && score > THRESHOLD;

  digitsEl.classList.toggle("idle", !scored);
  digitsEl.classList.toggle("flagged", flagged);
  setDigits(score);
  digitsEl.setAttribute("aria-label", scored ? `Risk ${Math.round(score * 100)} percent` : "No score yet");
  fillEl.style.transform = `scaleX(${score})`;
  fillEl.classList.toggle("hot", flagged);

  // One dot per message, at least seven: the chat has to fill the row before
  // TellMom judges it.
  const dots = Math.max(MIN_MESSAGES, n);
  progressEl.innerHTML = Array.from({ length: dots }, (_, i) => {
    let cls = "";
    if (i < n) {
      if (i < MIN_MESSAGES - 1 || trace[i] === undefined) cls = "read";
      else cls = trace[i] > THRESHOLD ? "hot" : "scored";
    }
    return `<li class="${cls}"></li>`;
  }).join("");
  progressEl.setAttribute("aria-label", `${n} message${n === 1 ? "" : "s"} read`);

  if (n === 0) {
    setVerdict("wait", "Press Play to start", "A made-up chat between a stranger and a child on Roblox.");
  } else if (n < MIN_MESSAGES) {
    setVerdict("read", "Reading the chat…", `${n} of ${MIN_MESSAGES} messages. It waits for more before judging.`);
  } else if (scored) {
    setVerdict(flagged ? "flag" : "ok",
      flagged ? "TellMom would alert you" : "Looks OK so far",
      flagged
        ? "This conversation crossed the alert line. You'd get a notification, and your Pi would take a closer look."
        : "Below the alert line. No alert would be sent.");
  }
}

async function score() {
  const texts = messages.map((m) => m.text);
  if (texts.length < MIN_MESSAGES) { trace = []; renderReadout(); return; }
  try {
    const res = await fetch(`${API}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: texts }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `The classifier answered ${res.status}.`);
    // A newer message may have arrived while this was in flight.
    if (texts.length !== messages.length) return;
    trace = data.trace;
    renderReadout();
  } catch (err) {
    stopPlaying();
    trace = [];
    renderReadout();
    setVerdict("err", "The demo can't reach the classifier",
      err instanceof TypeError ? "It may be restarting. Try again in a moment." : err.message);
  }
}

function addMessage(role, text) {
  messages.push({ role, text });
  const li = document.createElement("li");
  li.className = `msg ${role}`;
  li.innerHTML = `<span class="idx">${messages.length}</span><span class="who"></span><span class="bubble"></span>`;
  $(".who", li).textContent = NAMES[role];
  $(".bubble", li).textContent = text;
  log.appendChild(li);
  log.scrollTop = log.scrollHeight;
  renderReadout();
  pending = pending.then(score);
  return pending;
}

function nextFromPreset() {
  const list = PRESETS[preset];
  if (cursor >= list.length) { stopPlaying(); return false; }
  const [role, text] = list[cursor++];
  addMessage(role, text);
  return true;
}

function stopPlaying() {
  clearInterval(playing);
  playing = null;
  playBtn.textContent = cursor >= PRESETS[preset].length ? "Replay" : "Play";
}

function reset() {
  stopPlaying();
  messages = [];
  trace = [];
  cursor = 0;
  log.innerHTML = "";
  playBtn.textContent = "Play";
  renderReadout();
}

playBtn.addEventListener("click", () => {
  if (playing) return stopPlaying();
  if (cursor >= PRESETS[preset].length) reset();
  playBtn.textContent = "Pause";
  nextFromPreset();
  playing = setInterval(() => { if (!nextFromPreset()) stopPlaying(); }, 1500);
});
$("#reset-btn").addEventListener("click", reset);

$$(".preset").forEach((btn) => {
  btn.addEventListener("click", () => {
    preset = btn.dataset.preset;
    $$(".preset").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    reset();
  });
});

$("#compose").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = $("#text");
  const text = input.value.trim();
  if (!text) return;
  stopPlaying();
  addMessage($("#as").value, text);
  input.value = "";
});

renderReadout();
