#!/usr/bin/env node
// tools/ui-bench.mjs: a reproducible headless-Chrome performance bench for romp's dashboard panes.
//
// The kernel pushes JSON frames over a WebSocket to each pane page (feed, Outline, waiting, chat,
// timeline). How long the page's main thread takes to absorb a frame is what the user feels as a
// laggy dashboard, and until now it was measured by eye. This tool makes it a number, in three steps:
//
//   1. --record <app> --seconds N --out /tmp/…/frames.jsonl
//      Connect to the LIVE kernel's WebSocket exactly as the browser page does (same URL, same
//      ?caps, the token as the romp_token cookie with a same-origin Origin header, the {type:"ready"}
//      handshake) and save every frame the kernel sends, with a receive timestamp, as JSONL. The
//      client is read-only: it sends the ready handshake and nothing else (the ws library answers
//      protocol pings, which the kernel's liveness check needs). Recorded frames are REAL session
//      data, so the output path must be under /tmp and outside any git checkout; the tool refuses
//      anything else.
//
//   2. --replay <app> --frames FILE [--cpu-throttle K] [--iters N] [--fast] [--json OUT] [--cpu-profile OUT]
//      Serve the pane page and its bundles from the built dist and replay the recorded frames into a
//      headless Chromium at their recorded pacing (or back-to-back with --fast), measuring per frame
//      the bytes, the synchronous handler time, and the time until the main thread is free again
//      (message receipt to the second requestAnimationFrame after it); plus long-animation-frame
//      entries with script attribution (the task's entry point: the message handler, a rAF, a timer,
//      a script's evaluation; not the bundle function), JS heap after a forced GC, DOM size, and page
//      console errors. --cpu-profile OUT.cpuprofile samples the page's JavaScript with the V8 profiler
//      across the replay, writes a file Chrome DevTools loads, and prints the functions with the most
//      self and total time (with their source positions through the dist's .map files, and for the
//      hottest functions the lines that hold the time), overall and inside the first content frame and
//      the largest frame of each type: the attribution the long-animation-frame entries cannot give.
//
//      Serving design: the REAL kernel HTTP Handler runs in a python3 subprocess under an isolated
//      environment, the pattern of tests/test_color_route.py with the floors tests/conftest.py applies:
//      private XDG_STATE_HOME and TMUX_TMPDIR; the manager variables and the API-key variables removed;
//      the manager's key FILE and the boot model-catalog fetch pointed away (the kernel would otherwise
//      read ~/.config/romp/service.env and carry its key to the Models API); the Claude binary floored
//      to /bin/false; the postal peer bus off; ROMP_KERNEL_NO_OPEN=1; a serve token minted for the run.
//      So the page HTML and the WebSocket shim are the kernel's own bytes. The subprocess holds a pipe
//      from the parent and exits when it closes, so it cannot outlive the bench however the bench ends.
//      Its directory, and the browser's profile and artifacts, live under one per-user parent whose
//      dead-owner entries the next run sweeps: a process-group SIGKILL leaves them until then, nothing
//      else does. The shim connects its
//      socket to location.host, so a small Node front server sits in front: it answers /ws itself as
//      the replay server and proxies every other request (the page, /dist/*, /media/*, the small
//      JSON routes the bundles fetch) to the kernel Handler. Nothing is rewritten. The live kernel is
//      never started, restarted, or imported with its manager variables set.
//
//   3. --synthesize <app> --cards N --out FILE
//      A plausible frame stream with invented content (the notes-api demo domain, placeholder
//      uuids) in the kernel's wire shapes, for tests and for a bench that must not depend on a live
//      board. Frames mirror kernel.py: build_feed's {type:"feed"} and _feed_delta's {type:"feedDelta"}
//      for the feed, Outline and waiting pages; build_timeline's skeleton ({type:"data"}), the
//      {type:"bars"} slot with its _keys list and _send_slot_delta's {type:"delta", slot:"bars"} for
//      the timeline; keepalives throughout. The chat's {type:"session"} frame is not synthesized:
//      build_session's shape is too rich to fake faithfully, so record it from the live kernel.
//
//   --compare A.json B.json prints the deltas between two replay reports.
//
// Run from the repo root; playwright and ws come from vscode-extension/node_modules. Examples:
//   node tools/ui-bench.mjs --synthesize feed --cards 200 --out /tmp/romp-perf/synth-feed.jsonl
//   node tools/ui-bench.mjs --replay feed --frames /tmp/romp-perf/synth-feed.jsonl --fast --json /tmp/romp-perf/a.json
//   node tools/ui-bench.mjs --record feed --seconds 90 --out /tmp/romp-perf/frames-feed.jsonl
//   node tools/ui-bench.mjs --replay feed --frames /tmp/romp-perf/frames-feed.jsonl --json /tmp/romp-perf/b.json
//   node tools/ui-bench.mjs --compare /tmp/romp-perf/a.json /tmp/romp-perf/b.json
//
// tests/ui-bench.test.mjs covers the classifier, the compare arithmetic, the synthesizer's shapes,
// the /tmp path guard, the recording client against a local WebSocket server, the Handler subprocess's
// environment and its exit with the parent, the CPU-profile aggregation, and a real replay of
// synthetic streams on the feed and timeline pages.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import crypto from "node:crypto";
import { spawn } from "node:child_process";
import { createRequire, SourceMap } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const REPO = path.resolve(HERE, "..");
const EXT_DIR = path.join(REPO, "vscode-extension");
const requireExt = createRequire(path.join(EXT_DIR, "package.json"));

// The wire capabilities each page's shim announces (kernel.py: the _shim(app, v, caps=…) call sites).
export const APP_CAPS = {
  feed: "feedDelta,readyGate",
  fleet: "feedDelta,readyGate",
  waiting: "feedDelta,readyGate",
  chat: "readyGate",
  timeline: "readyGate",
  files: "readyGate,noStale",
};
export const APPS = Object.keys(APP_CAPS);
export const DELTA_SEP = "\u001f";   // kernel.py _DELTA_SEP: joins the keys of a keyed collection

// ── frame classification ─────────────────────────────────────────────────────────────────────────

const TYPE_RE = /"type"\s*:\s*"([^"\\]*)"/;
const SLOT_RE = /"slot"\s*:\s*"([^"\\]*)"/;

/** The report row a wire frame files under: its `type`, or `delta:<slot>` for a view delta; "other"
 *  when the text carries no type. A regex over the head of the string, so classifying a multi-megabyte
 *  frame costs nothing like a parse; the kernel writes `type` (and a delta's `slot`) first or right
 *  after `now`, in both json.dumps spacing and the hand-concatenated compact form. */
export function classifyFrame(text) {
  if (typeof text !== "string") return "other";
  const head = text.length > 4096 ? text.slice(0, 4096) : text;
  let type = null, slot = null;
  const m = TYPE_RE.exec(head);
  if (m) {
    type = m[1];
    if (type === "delta") { const s = SLOT_RE.exec(head); slot = s ? s[1] : null; }
  } else {
    try {
      const o = JSON.parse(text);
      if (o && typeof o.type === "string") { type = o.type; if (type === "delta") slot = typeof o.slot === "string" ? o.slot : null; }
    } catch { return "other"; }
  }
  if (!type) return "other";
  return type === "delta" ? "delta:" + (slot || "?") : type;
}

// ── statistics ───────────────────────────────────────────────────────────────────────────────────

/** Nearest-rank percentile of a numeric array (p in 0..100); null for an empty array. */
export function percentile(values, p) {
  const xs = values.filter((v) => typeof v === "number" && Number.isFinite(v)).sort((a, b) => a - b);
  if (!xs.length) return null;
  const rank = Math.min(xs.length - 1, Math.max(0, Math.ceil((p / 100) * xs.length) - 1));
  return xs[rank];
}

export function summarize(values) {
  const xs = values.filter((v) => typeof v === "number" && Number.isFinite(v));
  if (!xs.length) return { n: 0, p50: null, p90: null, max: null, mean: null };
  const sum = xs.reduce((a, b) => a + b, 0);
  return { n: xs.length, p50: percentile(xs, 50), p90: percentile(xs, 90), max: Math.max(...xs), mean: sum / xs.length };
}

// ── paths ────────────────────────────────────────────────────────────────────────────────────────

/** A recording holds real session data, so it may live only under /tmp and never inside a git
 *  checkout (a stray `git add` there would publish it). Both sides of the comparison are resolved
 *  through symlinks: on macOS /tmp is a link to /private/tmp and os.tmpdir() lives under /var/folders,
 *  so a root compared by name never matched a candidate compared by realpath. A directory that does
 *  not exist yet is resolved through its deepest existing ancestor. A symlink at the leaf is refused:
 *  a write through it lands wherever the link points. Returns the absolute path or throws. `roots` is
 *  a test seam; the default is /tmp and os.tmpdir(). */
export function assertTmpPath(p, { roots = ["/tmp", os.tmpdir()] } = {}) {
  const abs = path.resolve(p);
  const resolvedRoots = new Set();
  for (const r of roots) {
    if (!r) continue;
    const named = path.resolve(r);
    resolvedRoots.add(named);
    const real = safeReal(named);
    if (real) resolvedRoots.add(real);
  }
  const dir = resolveExistingPrefix(path.dirname(abs));
  const inTmp = [...resolvedRoots].some((r) => dir === r || dir.startsWith(r + path.sep));
  if (!inTmp) throw new Error(`refusing to write a recording outside /tmp: ${abs}`);
  let leaf = null;
  try { leaf = fs.lstatSync(abs); } catch (e) { if (e.code !== "ENOENT" && e.code !== "ENOTDIR") throw e; }
  if (leaf && leaf.isSymbolicLink()) throw new Error(`refusing to write a recording through a symlink: ${abs}`);
  for (let d = dir; ; d = path.dirname(d)) {
    if (fs.existsSync(path.join(d, ".git"))) throw new Error(`refusing to write a recording inside a git checkout: ${abs} (a .git lives at ${d})`);
    if (path.dirname(d) === d) break;
  }
  return abs;
}

function safeReal(p) {
  try { return fs.realpathSync(p); } catch { return null; }
}

/** The realpath of the deepest existing ancestor of `p`, with the missing tail appended unchanged. */
function resolveExistingPrefix(p) {
  const missing = [];
  for (let d = p; ; d = path.dirname(d)) {
    const real = safeReal(d);
    if (real) return missing.length ? path.join(real, ...missing) : real;
    if (path.dirname(d) === d) return p;
    missing.unshift(path.basename(d));
  }
}

// ── JSONL frame files ────────────────────────────────────────────────────────────────────────────

/** Read a frames file: rows {t, data} in file order (meta and event rows skipped). */
export function loadFrames(file) {
  const rows = [];
  let meta = null;
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line.trim()) continue;
    const row = JSON.parse(line);
    if (row.meta) { meta = row.meta; continue; }
    if (typeof row.data !== "string") continue;
    rows.push({ t: Number(row.t) || 0, data: row.data });
  }
  return { meta, frames: rows };
}

/** Write a frames file private to the user: directory 0700, file 0600 (re-applied when the file
 *  already existed), and never through a symlink at the leaf (O_NOFOLLOW). A recording holds every
 *  frame the kernel pushed, and /tmp is readable by every local account. */
export function writeFrames(file, meta, frames) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const out = [JSON.stringify({ meta })];
  for (const f of frames) out.push(JSON.stringify({ t: f.t, bytes: Buffer.byteLength(f.data, "utf8"), data: f.data }));
  const buf = Buffer.from(out.join("\n") + "\n", "utf8");
  const flags = fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_TRUNC | (fs.constants.O_NOFOLLOW || 0);
  const fd = fs.openSync(file, flags, 0o600);
  try {
    fs.fchmodSync(fd, 0o600);
    for (let off = 0; off < buf.length;) off += fs.writeSync(fd, buf, off, buf.length - off);
  } finally {
    fs.closeSync(fd);
  }
}

// ── --record: a read-only client of the live kernel ──────────────────────────────────────────────

function stateDir() {
  if (process.env.ROMP_STATE_DIR) return process.env.ROMP_STATE_DIR;
  const xdg = process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state");
  return path.join(xdg, "romp");
}

export function readServeToken() {
  const f = path.join(stateDir(), "serve-token");
  const t = fs.readFileSync(f, "utf8").trim();
  if (!t) throw new Error(`empty serve token at ${f}`);
  return t;
}

export async function recordFrames({ app, seconds, out, port, log = console.error }) {
  if (!APP_CAPS[app]) throw new Error(`unknown app ${app}; one of ${APPS.join(", ")}`);
  const file = assertTmpPath(out);
  const token = readServeToken();
  const WebSocket = requireExt("ws");
  const origin = `http://127.0.0.1:${port}`;
  const iid = crypto.randomUUID();
  const caps = APP_CAPS[app];
  const url = `ws://127.0.0.1:${port}/ws?app=${app}&delta=1&iid=${encodeURIComponent(iid)}&caps=${encodeURIComponent(caps)}`;
  // The browser's credential form: the romp_token cookie plus a same-origin Origin header (the kernel's
  // _authorize accepts the cookie only with an acceptable Origin). No ?token=, no X-Romp-Token.
  const ws = new WebSocket(url, { origin, headers: { Cookie: `romp_token=${token}` }, maxPayload: 512 * 1024 * 1024 });
  const frames = [];
  const events = [];
  const started = Date.now();
  const meta = { tool: "ui-bench", mode: "record", app, caps, port, seconds, startedAt: new Date(started).toISOString(), iid };
  await new Promise((resolve, reject) => {
    let done = false;
    const onInterrupt = () => { log("ui-bench: interrupted; writing what was recorded"); finish(); };
    const finish = (err) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      process.removeListener("SIGINT", onInterrupt);   // one listener per recording, gone when it ends
      try { ws.close(); } catch {}
      err ? reject(err) : resolve();
    };
    const timer = setTimeout(() => finish(), seconds * 1000);
    process.once("SIGINT", onInterrupt);
    ws.on("open", () => {
      events.push({ t: Date.now(), event: "open" });
      ws.send(JSON.stringify({ type: "ready" }));   // the bundle's handshake: lifts the ready-gate hold and serves the cached frame
    });
    ws.on("message", (data, isBinary) => {
      const text = isBinary ? data.toString("utf8") : data.toString();
      frames.push({ t: Date.now(), data: text });
    });
    ws.on("unexpected-response", (_req, res) => {
      let body = "";
      res.on("data", (c) => { body += c; });
      res.on("end", () => finish(new Error(`the kernel refused the WebSocket: HTTP ${res.statusCode} ${body.trim()}`)));
    });
    ws.on("error", (e) => finish(new Error(`WebSocket error: ${e.message}`)));
    ws.on("close", (code, reason) => {
      events.push({ t: Date.now(), event: "close", code, reason: String(reason || "") });
      if (!done) finish(new Error(`the kernel closed the socket early (code ${code}) after ${frames.length} frames`));
    });
  }).finally(() => {
    meta.endedAt = new Date().toISOString();
    meta.frames = frames.length;
    meta.events = events;
    writeFrames(file, meta, frames);
  });
  const summary = streamSummary(frames);
  log(`ui-bench: recorded ${frames.length} frames (${fmtBytes(summary.bytes)}) from app=${app} over ${((Date.now() - started) / 1000).toFixed(1)}s → ${file}`);
  for (const [type, s] of Object.entries(summary.byType)) log(`  ${type.padEnd(12)} ${String(s.count).padStart(6)}  ${fmtBytes(s.bytes).padStart(10)}  max ${fmtBytes(s.max)}`);
  return { file, frames: frames.length, summary };
}

export function streamSummary(frames) {
  const byType = {};
  let bytes = 0;
  for (const f of frames) {
    const type = classifyFrame(f.data);
    const n = Buffer.byteLength(f.data, "utf8");
    bytes += n;
    const s = (byType[type] ||= { count: 0, bytes: 0, max: 0 });
    s.count++; s.bytes += n; if (n > s.max) s.max = n;
  }
  return { frames: frames.length, bytes, byType };
}

// ── --synthesize: invented frames in the kernel's shapes ─────────────────────────────────────────

const SIDS = ["11111111-2222-3333-4444-555555555501", "11111111-2222-3333-4444-555555555502", "11111111-2222-3333-4444-555555555503"];
const NAMES = ["web", "api", "tests"];
const COLORS = [{ bg: "#1EA1EB", fg: "white" }, { bg: "#54B204", fg: "black" }, { bg: "#E0B020", fg: "black" }];
const VERBS = ["Add", "Fix", "Refactor", "Document", "Test", "Wire", "Profile", "Remove"];
const OBJECTS = ["pagination on the notes list", "the notes-api auth middleware", "the search index rebuild", "the markdown export",
  "the tag filter query", "the rate limiter", "the notes sync endpoint", "the attachment upload path", "the CLI's note picker",
  "the flaky integration test", "the OpenAPI schema", "the migration runner"];
const SYNTH_NOW = 1_760_000_000;   // a fixed clock so a synthesized stream is byte-stable run to run

function rng(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const pick = (r, xs) => xs[Math.floor(r() * xs.length)];

function synthCard(i, r, now) {
  const k = i % SIDS.length;
  const column = i % 5 === 3 ? "needs_input" : i % 5 === 4 ? "completed" : "working";
  const text = `${VERBS[i % VERBS.length]} ${OBJECTS[i % OBJECTS.length]} (#${i + 1})`;
  const t = now - 300 * i - 17;
  const nodes = [];
  const kids = 1 + (i % 3);
  for (let j = 0; j < kids; j++) {
    nodes.push({
      id: `n${i}-${j}`, kind: "ask", text: `${text}: step ${j + 1}`, who: NAMES[k], whoSid: SIDS[k], whoColor: COLORS[k],
      status: column === "completed" ? "done" : (column === "needs_input" && j === kids - 1) ? "question" : (j === 0 ? "done" : "open"),
      t: t + 30 * j, last: t + 60 * j + 5, anchorUuid: null, promptAnchorUuid: null, children: [],
    });
  }
  const card = {
    itemId: `card-${i}`, sid: SIDS[k], name: NAMES[k], color: COLORS[k], text, t, live: true, turnId: `turn-${i}`,
    column, tree: nodes, notify: null, summary: column === "completed" ? `Done: ${text.toLowerCase()} landed with a test.` : null,
    blockSummary: null, background: null, distillState: column === "completed" ? "completed" : null,
  };
  if (column === "working") card.working = { since: now - 40 - (i % 7) * 10, toolUses: 1 + (i % 9) };
  if (i % 11 === 6) card.awaiting = { why: "waiting on the test suite", kind: "task", since: now - 90, tasks: ["npm test"] };
  return card;
}

function synthLedger(k, cards, now) {
  const own = cards.filter((c) => c.sid === SIDS[k]);
  const tree = [];
  for (const c of own) {
    tree.push({ id: c.itemId, text: c.text, depth: 0, done: c.column === "completed", blocked: c.column === "needs_input", t: c.t, mt: c.t + 120,
      current: c.column === "working", children: c.tree.map((n) => n.id), summary: c.summary, blockSummary: null });
    for (const n of c.tree) tree.push({ id: n.id, text: n.text, depth: 1, done: n.status === "done", blocked: n.status === "question", t: n.t, mt: n.last, current: false, children: [] });
  }
  return { sid: SIDS[k], name: NAMES[k], color: COLORS[k], status: { state: k === 2 ? "ready" : "working" },
    ledger: { summary: `${NAMES[k]} is working through ${own.length} goals on notes-api.`, tree, current: { t: now - 60 } } };
}

function synthFeedFull(cards, now, buildId, withLedgers) {
  const asks = cards.map((c) => ({ ...c }));
  const frame = {
    type: "feed", asks, now, buildId,
    userTodos: {}, userTodoRows: [], userTodosOn: true,
    sessions: SIDS.map((sid, k) => ({ sid, name: NAMES[k], color: COLORS[k] })),
    order: SIDS.slice(), working: [NAMES[0], NAMES[1]], awaiting: [], stateUnknown: [], bgServices: {},
    dismissedCount: 0, showDismissed: false, canUndoClear: false, clearNotices: [], sdkNotices: [], syncNotices: [],
  };
  if (withLedgers) frame.ledgers = SIDS.map((_s, k) => synthLedger(k, cards, now));
  frame.userTodoRows = [{ sid: SIDS[0], name: NAMES[0], color: COLORS[0], todos: [{ id: "t1", text: "Pick the pagination page size", createdT: now - 600 }] }];
  return frame;
}

function feedRest(frame) {
  const rest = {};
  for (const [k, v] of Object.entries(frame)) if (k !== "asks" && k !== "ledgers" && k !== "now" && k !== "buildId" && k !== "type") rest[k] = v;
  return rest;
}

/** A feed-protocol stream (feed, Outline, waiting pages): one full frame, then feedDelta frames and
 *  keepalives over about a minute of invented activity. */
function synthFeedStream(app, cards, r, now) {
  const t0 = now * 1000;
  const withLedgers = app === "fleet";
  const items = [];
  for (let i = 0; i < cards; i++) items.push(synthCard(i, r, now));
  let buildId = 1;
  const full = synthFeedFull(items, now, buildId, withLedgers);
  const frames = [{ t: t0, data: JSON.stringify(full) }];
  let nextNew = cards;
  const ka = (t) => frames.push({ t, data: JSON.stringify({ type: "ka", dv: now }) });
  for (let step = 1; step <= 24; step++) {
    const t = t0 + step * 2500;
    if (step % 4 === 0) ka(t - 400);
    buildId++;
    const d = { type: "feedDelta", now: now + Math.round((t - t0) / 1000), buildId };
    const nUp = 1 + Math.floor(r() * 3);
    const ups = [];
    for (let u = 0; u < nUp && items.length; u++) {
      const c = items[Math.floor(r() * items.length)];
      c.text = c.text.replace(/( · rev \d+)?$/, ` · rev ${step}`);
      if (c.working) c.working = { ...c.working, toolUses: (c.working.toolUses || 0) + 1 };
      ups.push({ ...c });
    }
    d.asks = ups;
    if (step % 5 === 0 && items.length > 1) {
      const gone = items.splice(Math.floor(r() * items.length), 1)[0];
      d.removeAsks = [gone.itemId];
      const fresh = synthCard(nextNew++, r, now + step);
      items.push(fresh);
      d.asks.push({ ...fresh });
    }
    if (step % 7 === 0) {
      full.working = step % 2 ? [NAMES[0]] : [NAMES[0], NAMES[1], NAMES[2]];
      d.top = feedRest(full);
    }
    if (withLedgers && step % 3 === 0) d.ledgers = [synthLedger(step % SIDS.length, items, now + step)];
    frames.push({ t, data: JSON.stringify(d) });
  }
  ka(t0 + 63_000);
  return frames;
}

function synthLane(k, now, live) {
  return {
    id: SIDS[k], name: NAMES[k], live, state: live ? (k === 2 ? "idle" : "working") : "idle",
    awaitingBg: null, awaitingKind: null, awaitingCount: null, awaitingPeers: null, awaitingTasks: [],
    since: now - 120 * (k + 1), color: COLORS[k].bg, model: "opus", effort: "high", modelPending: false,
    modelColor: null, effortColor: null, fast: "", modelTone: null, effortTone: null, ctxTone: null,
    context: 20 + 15 * k, ctxColor: null, subagents: [], awaiting: [], compacting: [], compactions: [], clears: [],
    faded: false, branch: null, comments: [], hideFromFeed: false, postalServiceOff: false, notify: true,
  };
}

function synthBar(k, j, now, open) {
  const start = now - 3600 + 240 * j;
  const text = `${VERBS[(j + k) % VERBS.length]} ${OBJECTS[(j * 3 + k) % OBJECTS.length]}`;
  return {
    id: `seg-${k}-${j}`, promptId: `aaaaaaaa-0000-4000-8000-${String(k).padStart(4, "0")}${String(j).padStart(8, "0")}`,
    workId: `bbbbbbbb-0000-4000-8000-${String(k).padStart(4, "0")}${String(j).padStart(8, "0")}`,
    start, end: open ? now : start + 150, open, cont: false, prompt: text, summary: `Working on ${text.toLowerCase()}`,
    msgCaption: text, src: "typed", mids: [], pending: false, tid: SIDS[k],
    uuid: `aaaaaaaa-0000-4000-8000-${String(k).padStart(4, "0")}${String(j).padStart(8, "0")}`,
    nudgeAuto: false, romp: false,
    workUuid: `bbbbbbbb-0000-4000-8000-${String(k).padStart(4, "0")}${String(j).padStart(8, "0")}`,
    replyUuid: `cccccccc-0000-4000-8000-${String(k).padStart(4, "0")}${String(j).padStart(8, "0")}`,
  };
}

/** The kernel's _keys list for a {type:"bars"} full frame (kernel.py _delta_split / _delta_key). */
export function barsKeys(bars) {
  const turns = [];
  for (const [sid, lane] of Object.entries(bars.turns || {})) {
    if (!Array.isArray(lane) || !lane.length) { turns.push(sid + DELTA_SEP); continue; }
    for (const b of lane) turns.push(sid + DELTA_SEP + String(b.id));
  }
  const judging = (bars.judging || []).map((row) => ["sid", "t", "judge", "t1"].map((f) => String(row[f])).join(DELTA_SEP));
  const messages = (bars.messages || []).map((m) => String(m.id));
  return { turns, judging, messages };
}

/** A timeline stream: the lanes skeleton, the keyed bars slot, then bar-level deltas, a skeleton
 *  re-push and keepalives. */
function synthTimelineStream(cards, r, now) {
  const t0 = now * 1000;
  const skeleton = () => ({
    type: "data",
    data: { type: "timeline", now, sessions: SIDS.map((_s, k) => synthLane(k, now, true)), turns: {}, messages: [], judging: [],
      palette: COLORS.map((c) => c.bg), cmapGrad: null, activeChat: null, focus: null, hover: null, usage: null },
  });
  const frames = [{ t: t0, data: JSON.stringify(skeleton()) }];
  const perLane = Math.max(1, Math.ceil(cards / SIDS.length));
  const turns = {};
  SIDS.forEach((sid, k) => {
    turns[sid] = [];
    for (let j = 0; j < perLane; j++) turns[sid].push(synthBar(k, j, now, k < 2 && j === perLane - 1));
  });
  const judging = [];
  for (let j = 0; j < Math.min(perLane, 12); j++) {
    const k = j % SIDS.length;
    const t = now - 3400 + 240 * j;
    judging.push({ judge: pick(r, ["planner", "closer", "distiller", "captioner"]), sid: SIDS[k], t, t1: t + 8, kind: "run", text: "",
      ms: 7200, in: 4000 + j * 10, out: 300, sent: t, recv: t + 8 });
  }
  const bars = { type: "bars", turns, judging, messages: [], now, warming: false };
  frames.push({ t: t0 + 300, data: JSON.stringify({ ...bars, _keys: barsKeys(bars) }) });
  let rev = 0;
  const ka = (t) => frames.push({ t, data: JSON.stringify({ type: "ka", dv: now }) });
  for (let step = 1; step <= 24; step++) {
    const t = t0 + step * 2500;
    const nowS = now + Math.round((t - t0) / 1000);
    if (step % 4 === 0) ka(t - 400);
    const k = step % 2;   // the two working lanes take turns
    const lane = turns[SIDS[k]];
    const set = {};
    if (step % 6 === 0) {
      // the open bar closes and a new one opens: two entries cross
      const last = lane[lane.length - 1];
      last.open = false; last.end = nowS - 5;
      set[SIDS[k] + DELTA_SEP + last.id] = { ...last };
      const fresh = synthBar(k, lane.length, nowS, true);
      lane.push(fresh);
      set[SIDS[k] + DELTA_SEP + fresh.id] = fresh;
    } else {
      const last = lane[lane.length - 1];
      last.end = nowS;
      set[SIDS[k] + DELTA_SEP + last.id] = { ...last };
    }
    frames.push({ t, data: JSON.stringify({ type: "delta", slot: "bars", base: rev, rev: rev + 1, coll: { turns: { set } }, rest: { now: nowS } }) });
    rev++;
    if (step % 8 === 0) {
      const sk = skeleton();
      sk.data.now = nowS;
      sk.data.sessions[2].state = step % 16 ? "working" : "idle";
      frames.push({ t: t + 200, data: JSON.stringify(sk) });
    }
  }
  ka(t0 + 63_000);
  return frames;
}

export function synthesizeFrames(app, cards, { seed = 7, now = SYNTH_NOW } = {}) {
  if (!APP_CAPS[app]) throw new Error(`unknown app ${app}; one of ${APPS.join(", ")}`);
  if (app === "chat") throw new Error("chat frames are not synthesized (the session frame is built by build_session and is too rich to fake); record them from the live kernel with --record");
  if (app === "files") throw new Error("files frames are not synthesized (the Files pane parses no frames: its socket carries keepalives and op replies only); record its stream from the live kernel with --record");
  const r = rng(seed);
  if (app === "timeline") return synthTimelineStream(cards, r, now);
  return synthFeedStream(app, cards, r, now);
}

// ── --replay: the kernel page route in a subprocess, a Node front server, headless Chromium ─────

// The kernel's HTTP Handler, alone, in a python3 subprocess. The import pattern is tests/test_color_route.py's:
// the two sibling modules first (they resolve their state root at import), then the kernel by its bin/ name.
// The Handler is the kernel's whole route surface (the pages, /ws, the POST routes that spawn and revive
// sessions), gated by the serve token, so it must not outlive the bench: a daemon thread blocks on stdin,
// which the parent holds open as a pipe, and when the parent exits, however it exits, the read returns
// EOF, the thread removes the run directory and the process ends. When the whole process group is
// killed the thread never runs and the directory stays; the next run's dead-owner sweep reclaims it.
const PAGE_SERVER_PY = `
import os, shutil, sys, threading
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
root, tmp = sys.argv[1], sys.argv[2]
def _parent_gone():
    try:
        sys.stdin.buffer.read()
    except Exception:
        pass
    shutil.rmtree(tmp, ignore_errors=True)
    os._exit(0)
threading.Thread(target=_parent_gone, daemon=True).start()
b = os.path.join(root, "bin")
SourceFileLoader("romp_event_model", os.path.join(b, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(b, "romp-judge")).load_module()
km = SourceFileLoader("romp_kernel_ui_bench", os.path.join(b, "romp-kernel")).load_module()
srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
sys.stdout.write("PORT %d\\n" % srv.server_address[1]); sys.stdout.flush()
srv.serve_forever()
`;

/** The variables the Handler subprocess must not inherit: the manager's (so the kernel module never
 *  believes it is the supervised live kernel), the live kernel's ports and state root, and the API keys
 *  and Claude binary a spawned session would run with (nothing the bench needs reads them). */
export const STRIPPED_ENV = ["ROMP_MANAGER_PORT", "ROMP_MANAGER_PID", "ROMP_SUPERVISED", "ROMP_STATE_DIR", "ROMP_SERVE_PORT", "ROMP_KERNEL_PORT", "ROMP_PERF", "TMUX"];

/** The parent every run of this tool on this machine keeps its state under: <tmp>/romp-ui-bench-<uid>,
 *  private to the user and refused when something else holds the name. Each run gets a subdirectory
 *  holding owner.pid, the Handler's XDG_STATE_HOME and TMUX_TMPDIR and, through TMPDIR at launch, the
 *  browser's profile and artifacts. This small parent is the only directory the tool ever lists. */
export function benchRoot(base = os.tmpdir()) {
  const uid = typeof os.userInfo === "function" ? os.userInfo().uid : -1;
  const root = path.join(base, `romp-ui-bench-${uid}`);
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  const st = fs.lstatSync(root);
  if (st.isSymbolicLink() || !st.isDirectory()) throw new Error(`${root} is not a directory; refusing to use it`);
  if (uid >= 0 && st.uid !== uid) throw new Error(`${root} belongs to uid ${st.uid}; refusing to use it`);
  if ((st.mode & 0o077) !== 0) fs.chmodSync(root, 0o700);
  return root;
}

/** Remove the run directories under `root` whose recorded owner process is gone: what a process-group
 *  SIGKILL leaves behind (the Handler dies with the group before its rmtree runs; Playwright removes its
 *  directories from exit hooks a SIGKILL skips). An entry without owner.pid is left alone. Returns the
 *  names removed. */
export function sweepDeadRuns(root) {
  const swept = [];
  let names = [];
  try { names = fs.readdirSync(root); } catch { return swept; }
  for (const name of names) {
    const dir = path.join(root, name);
    let pid = NaN;
    try { pid = Number(fs.readFileSync(path.join(dir, "owner.pid"), "utf8").trim()); } catch { continue; }
    if (!Number.isInteger(pid) || pid <= 0) continue;
    let alive = true;
    try { process.kill(pid, 0); } catch (e) { alive = e.code === "EPERM"; }   // EPERM: it exists and is not ours
    if (alive) continue;
    try { fs.rmSync(dir, { recursive: true, force: true }); swept.push(name); } catch {}
  }
  return swept;
}

/** Start the kernel Handler subprocess under the isolated environment. Resolves to {port, token, pid,
 *  tmp, root, stderr, stop}; on a start failure (an interpreter that cannot be spawned, exits before
 *  its port, or never announces one) the child is gone and its directory removed before the rejection.
 *  The serve token is minted per run: the Handler is the kernel's whole route surface on a loopback
 *  port any local process can reach, and a token in the source would open it to all of them. */
export async function startPageServer({ dist, python = "python3", log = () => {} } = {}) {
  const distDir = dist || path.join(EXT_DIR, "dist");
  if (!fs.existsSync(path.join(distDir, "feed.js"))) throw new Error(`no built bundles at ${distDir} (run: cd vscode-extension && npm run build)`);
  const root = benchRoot();
  const swept = sweepDeadRuns(root);
  if (swept.length) log(`ui-bench: removed ${swept.length} run director${swept.length === 1 ? "y" : "ies"} left behind by dead runs`);
  const tmp = fs.mkdtempSync(path.join(root, "run-"));
  fs.writeFileSync(path.join(tmp, "owner.pid"), `${process.pid}\n`);
  const token = crypto.randomBytes(18).toString("base64url");
  const env = { ...process.env };
  for (const k of Object.keys(env)) if (k.startsWith("ANTHROPIC_") || STRIPPED_ENV.includes(k)) delete env[k];
  env.XDG_STATE_HOME = path.join(tmp, "state");
  env.TMUX_TMPDIR = path.join(tmp, "tmux");
  fs.mkdirSync(env.XDG_STATE_HOME, { recursive: true });
  fs.mkdirSync(env.TMUX_TMPDIR, { recursive: true });
  env.ROMP_KERNEL_NO_OPEN = "1";
  env.ROMP_POSTAL_PEERS = "0";   // the feed page polls /tunnels, which otherwise asks the LIVE postal bus for its peers
  // The floors tests/conftest.py applies, for the same reasons. The kernel's live API key is the manager's
  // env FILE (kernel/keysource.py falls back to ~/.config/romp/service.env when these two are unset), the
  // boot model-catalog fetch would carry that key to the Models API from the first /sessions request a
  // pane makes, and a missing ROMP_CLAUDE_BIN resolves to the real CLI, so it is set to a binary that runs
  // nothing rather than removed.
  env.ROMP_SERVICE_ENV_FILE = env.ROMP_SERVICE_ENV = path.join(tmp, "no-service.env");   // never created
  env.ROMP_MODEL_CATALOG = "off";
  env.ROMP_CLAUDE_BIN = "/bin/false";
  env.ROMP_SERVE_TOKEN = token;
  env.ROMP_DIST_DIR = distDir;
  const child = spawn(python, ["-c", PAGE_SERVER_PY, REPO, tmp], { env, stdio: ["pipe", "pipe", "pipe"] });
  child.stdin.on("error", () => {});   // EPIPE once the child is gone
  let stderr = "";
  child.stderr.on("data", (c) => { stderr += c; if (stderr.length > 64_000) stderr = stderr.slice(-32_000); log(String(c)); });
  let stopped = false;
  const stop = (signal = "SIGTERM") => {
    if (!stopped) { stopped = true; try { child.stdin.end(); } catch {} }
    try { child.kill(signal); } catch {}
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {}
  };
  const port = await new Promise((resolve, reject) => {
    let buf = "";
    const timer = setTimeout(() => { stop("SIGKILL"); reject(new Error(`the kernel page server did not start within 60s\n${stderr}`)); }, 60_000);
    // An interpreter that cannot be spawned (ENOENT) emits 'error' and never 'exit'; unhandled, that is an
    // uncaught exception thrown from a tick outside the promise chain, and the directory stays behind.
    child.on("error", (e) => { clearTimeout(timer); try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {} reject(new Error(`could not start ${python}: ${e.message}`)); });
    child.stdout.on("data", (c) => {
      buf += c;
      const m = /PORT (\d+)/.exec(buf);
      if (m) { clearTimeout(timer); resolve(Number(m[1])); }
    });
    child.on("exit", (code) => { clearTimeout(timer); try { fs.rmSync(tmp, { recursive: true, force: true }); } catch {} reject(new Error(`the kernel page server exited with ${code}\n${stderr}`)); });
  });
  return { port, token, pid: child.pid, tmp, root, stderr: () => stderr, stop: () => stop() };
}

/** The front server: /ws is ours (the replay socket), everything else proxies to the kernel Handler. */
export async function startFront({ pagePort }) {
  const { WebSocketServer } = requireExt("ws");
  let onSocket = null;
  const server = http.createServer((req, res) => {
    // The browser's Host header passes through untouched: the kernel's _origin_ok compares a request's Origin
    // against its Host, and Chrome sends Origin on CORS-mode subresource loads (the woff2 fonts), so a
    // rewritten Host turned every font load into a 403.
    const upstream = http.request({ host: "127.0.0.1", port: pagePort, method: req.method, path: req.url, headers: req.headers }, (up) => {
      res.writeHead(up.statusCode, up.headers);
      up.pipe(res);
    });
    upstream.on("error", (e) => { res.writeHead(502, { "Content-Type": "text/plain" }); res.end("front proxy: " + e.message); });
    req.pipe(upstream);
  });
  const wss = new WebSocketServer({ noServer: true, maxPayload: 512 * 1024 * 1024 });
  server.on("upgrade", (req, socket, head) => {
    const u = new URL(req.url, "http://127.0.0.1");
    const selfOrigin = `http://127.0.0.1:${server.address().port}`;
    if (u.pathname !== "/ws" || (req.headers.origin && req.headers.origin !== selfOrigin)) {
      socket.write("HTTP/1.1 403 Forbidden\r\n\r\n"); socket.destroy(); return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => { if (onSocket) onSocket(ws, u); else ws.close(); });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  return {
    port: server.address().port,
    setSocketHandler(fn) { onSocket = fn; },
    stop() { for (const c of wss.clients) { try { c.terminate(); } catch {} } server.close(); },
  };
}

// In-page instrumentation, installed before any page script runs. It wraps WebSocket.prototype's
// onmessage setter so the shim's handler is timed: t0 at handler entry, `handler` when it returns,
// `settle` at the second requestAnimationFrame after it (the main thread has rendered and is free).
// Long animation frames are observed with script attribution; longtask is the fallback.
const INIT_SCRIPT = `
(() => {
  const R = window.__rompBench = { recs: [], loaf: [], loafKind: null, n: 0, addListenerMessages: 0 };
  const proto = WebSocket.prototype;
  const desc = Object.getOwnPropertyDescriptor(proto, "onmessage");
  function wrap(fn) {
    return function rompBenchOnMessage(ev) {
      const i = R.n++;
      const t0 = performance.now();
      const rec = { i, t0, len: typeof ev.data === "string" ? ev.data.length : -1, handler: -1, settle: -1 };
      R.recs.push(rec);
      try { return fn.call(this, ev); }
      finally {
        rec.handler = performance.now() - t0;
        requestAnimationFrame(() => requestAnimationFrame(() => { rec.settle = performance.now() - t0; }));
      }
    };
  }
  Object.defineProperty(proto, "onmessage", {
    configurable: true, enumerable: desc.enumerable,
    get() { return desc.get.call(this); },
    set(fn) { desc.set.call(this, typeof fn === "function" ? wrap(fn) : fn); },
  });
  const origAdd = proto.addEventListener;
  proto.addEventListener = function (type, fn, opts) { if (type === "message") R.addListenerMessages++; return origAdd.call(this, type, fn, opts); };
  const types = (window.PerformanceObserver && PerformanceObserver.supportedEntryTypes) || [];
  if (types.includes("long-animation-frame")) {
    R.loafKind = "long-animation-frame";
    R.obs = new PerformanceObserver((list) => { for (const e of list.getEntries()) R.loaf.push(loafRow(e)); });
    R.obs.observe({ type: "long-animation-frame", buffered: true });
  } else if (types.includes("longtask")) {
    R.loafKind = "longtask";
    R.obs = new PerformanceObserver((list) => { for (const e of list.getEntries()) R.loaf.push({ start: e.startTime, duration: e.duration, blocking: Math.max(0, e.duration - 50), scripts: [] }); });
    R.obs.observe({ type: "longtask", buffered: true });
  }
  function loafRow(e) {
    return { start: e.startTime, duration: e.duration, blocking: e.blockingDuration, renderStart: e.renderStart, styleAndLayoutStart: e.styleAndLayoutStart,
      scripts: Array.from(e.scripts || [], (s) => ({ url: s.sourceURL || "", fn: s.sourceFunctionName || "", invoker: s.invoker || "", invokerType: s.invokerType || "", duration: s.duration, line: s.sourceCharPosition })) };
  }
  R.collect = () => {
    if (R.obs) for (const e of R.obs.takeRecords()) R.loaf.push(R.loafKind === "long-animation-frame" ? loafRow(e) : { start: e.startTime, duration: e.duration, blocking: Math.max(0, e.duration - 50), scripts: [] });
    const mem = performance.memory ? { used: performance.memory.usedJSHeapSize, total: performance.memory.totalJSHeapSize, limit: performance.memory.jsHeapSizeLimit } : null;
    const bar = document.getElementById("romp-stale-self");   // the shim's banner: "build" when a keepalive's dv outran the served dist, "conn" for a dead socket
    return { recs: R.recs, loaf: R.loaf, loafKind: R.loafKind, domElements: document.getElementsByTagName("*").length, heap: mem, addListenerMessages: R.addListenerMessages,
      banner: bar ? (bar.dataset.kind || "?") : null };
  };
})();
//# sourceURL=ui-bench-instrument.js
`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(fn, timeoutMs, what) {
  const t0 = Date.now();
  for (;;) {
    if (await fn()) return;
    if (Date.now() - t0 > timeoutMs) throw new Error(`timed out after ${timeoutMs} ms waiting for ${what}`);
    await sleep(25);
  }
}

/** Which browser --replay can launch: {ok, how, why}. Playwright's own Chromium when installed, else a
 *  system Google Chrome / Chromium through playwright's channel option. */
export function browserAvailability() {
  let chromium;
  try { ({ chromium } = requireExt("playwright")); } catch (e) { return { ok: false, why: `playwright is not installed under vscode-extension/ (npm ci there): ${e.message}` }; }
  try { const exe = chromium.executablePath(); if (exe && fs.existsSync(exe)) return { ok: true, how: "playwright chromium", exe }; } catch {}
  for (const name of ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]) {
    for (const dir of (process.env.PATH || "").split(path.delimiter)) {
      const p = path.join(dir, name);
      if (dir && fs.existsSync(p)) return { ok: true, how: `system ${name}`, exe: p, channel: name.startsWith("google") ? "chrome" : "chromium" };
    }
  }
  return { ok: false, why: "no Chromium: run `cd vscode-extension && npx playwright install chromium`, or install Google Chrome" };
}

/** Launch headless Chromium. Playwright creates the browser's profile and its artifacts directory with
 *  mkdtemp under os.tmpdir(), which follows TMPDIR, and removes them only from exit hooks a SIGKILL
 *  skips; with TMPDIR pointed at the run directory for the launch, both land inside it, where stop() and
 *  the next run's dead-owner sweep reach them. The browser process inherits the same TMPDIR. */
export async function launchBrowser({ tmpRoot } = {}) {
  const avail = browserAvailability();
  if (!avail.ok) throw new Error(avail.why);
  const { chromium } = requireExt("playwright");
  const saved = process.env.TMPDIR;
  if (tmpRoot) process.env.TMPDIR = tmpRoot;
  try {
    if (avail.how === "playwright chromium") return await chromium.launch({ headless: true });
    try { return await chromium.launch({ headless: true, channel: avail.channel }); }
    catch { return await chromium.launch({ headless: true, executablePath: avail.exe }); }
  } finally {
    if (tmpRoot) { if (saved === undefined) delete process.env.TMPDIR; else process.env.TMPDIR = saved; }
  }
}

async function replayOnce({ browser, app, frames, fast, cpuThrottle, front, token, cpuProfile = false, log }) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [], pageErrors = [];
  let warnings = 0;
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); else if (m.type() === "warning") warnings++; });
  page.on("pageerror", (e) => pageErrors.push(String((e && e.message) || e)));
  const failedResources = [];
  page.on("response", (resp) => { if (resp.status() >= 400) failedResources.push(`${resp.status()} ${new URL(resp.url()).pathname}`); });
  await page.addInitScript(INIT_SCRIPT);
  const cdp = await context.newCDPSession(page);
  await cdp.send("Performance.enable");
  if (cpuThrottle && cpuThrottle !== 1) await cdp.send("Emulation.setCPUThrottlingRate", { rate: cpuThrottle });
  if (cpuProfile) {
    await cdp.send("Profiler.enable");
    await cdp.send("Profiler.setSamplingInterval", { interval: PROFILE_INTERVAL_US });
  }

  const session = { current: null, clientMessages: {}, clientDiag: {}, reconnects: 0, readyAt: 0 };
  let readyResolve;
  const ready = new Promise((r) => { readyResolve = r; });
  front.setSocketHandler((ws) => {
    ws.on("message", (data) => {
      let m = null;
      try { m = JSON.parse(data.toString()); } catch {}
      const type = (m && typeof m.type === "string") ? m.type : "?";
      session.clientMessages[type] = (session.clientMessages[type] || 0) + 1;
      if (type === "clientDiag" && m) { const w = `${m.surface || "?"}:${m.what || "?"}`; session.clientDiag[w] = (session.clientDiag[w] || 0) + 1; }
      if (type === "ready") {
        if (session.current && session.current !== ws) session.reconnects++;
        session.current = ws;
        if (!session.readyAt) session.readyAt = Date.now();
        readyResolve();
      }
    });
  });

  const navT0 = Date.now();
  await page.goto(`http://127.0.0.1:${front.port}/${app}?token=${encodeURIComponent(token)}`, { waitUntil: "load", timeout: 60_000 });
  let handshakeTimer;
  try {
    await Promise.race([ready, new Promise((_, rej) => { handshakeTimer = setTimeout(() => rej(new Error("the pane never sent its {type:\"ready\"} handshake within 30s")), 30_000); })]);
  } finally {
    clearTimeout(handshakeTimer);   // a losing timer left armed kept every replay process alive for the full 30 s
  }
  const readyMs = session.readyAt - navT0;
  // The profile's clock is V8's; the page's records are performance.now(). Bracketing Profiler.start
  // with two reads of performance.now() puts the profile's startTime between them, so a page time maps to
  // the profile's to within half the gap (alignMs, about a millisecond).
  let profiling = null;
  if (cpuProfile) {
    const before = await page.evaluate(() => performance.now());
    await cdp.send("Profiler.start");
    const after = await page.evaluate(() => performance.now());
    profiling = { p0: (before + after) / 2, alignMs: (after - before) / 2, profile: null };
  }

  const sent = [];
  const t0 = Date.now();
  let prev = frames.length ? frames[0].t : 0;
  for (const f of frames) {
    const gap = fast ? 0 : Math.max(0, f.t - prev);
    prev = f.t;
    if (gap > 0) await sleep(gap);
    const ws = session.current;
    if (!ws || ws.readyState !== 1) throw new Error(`the pane's socket is not open at frame ${sent.length} (state ${ws ? ws.readyState : "none"})`);
    ws.send(f.data);
    sent.push({ type: classifyFrame(f.data), bytes: Buffer.byteLength(f.data, "utf8"), at: Date.now() - t0 });
  }
  const replayMs = Date.now() - t0;
  // Every sent frame dispatched in the page, then every settle stamped, then one more rendered frame.
  const budget = 30_000 + sent.reduce((a, s) => a + s.bytes, 0) / 1024;   // a second per MB on top of the floor
  await waitFor(async () => (await page.evaluate(() => window.__rompBench.n)) >= sent.length, budget, `the page to dispatch all ${sent.length} frames`);
  await waitFor(async () => page.evaluate(() => window.__rompBench.recs.every((r) => r.settle >= 0)), 10_000, "every frame's settle stamp").catch((e) => log(`ui-bench: ${e.message}`));
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 0)))));
  if (profiling) {
    profiling.profile = (await cdp.send("Profiler.stop")).profile;
    await cdp.send("Profiler.disable");
  }
  // Collect the heap after a forced GC: without it the figure is live objects plus whatever garbage
  // happens to be pending, and two replays of the same page differed by a third.
  await cdp.send("HeapProfiler.collectGarbage");
  const data = await page.evaluate(() => window.__rompBench.collect());
  const { metrics } = await cdp.send("Performance.getMetrics");
  const met = Object.fromEntries(metrics.map((m) => [m.name, m.value]));
  await context.close();

  const perFrame = sent.map((s, i) => {
    const r = data.recs[i];
    return { i, type: s.type, bytes: s.bytes, at: s.at, handlerMs: r ? r.handler : null, settleMs: r ? r.settle : null, t0: r ? r.t0 : null, lenMatch: r ? r.len === frames[i].data.length : false };
  });
  const misaligned = perFrame.filter((f) => f.handlerMs != null && !f.lenMatch).length;
  return {
    readyMs, replayMs, sent, perFrame, misaligned, reconnects: session.reconnects, clientMessages: session.clientMessages, clientDiag: session.clientDiag,
    loaf: data.loaf, loafKind: data.loafKind, domElements: data.domElements, heap: data.heap, addListenerMessages: data.addListenerMessages, banner: data.banner,
    profiling,
    cdp: { nodes: met.Nodes, documents: met.Documents, jsEventListeners: met.JSEventListeners, layoutCount: met.LayoutCount, recalcStyleCount: met.RecalcStyleCount,
      layoutMs: (met.LayoutDuration || 0) * 1000, recalcStyleMs: (met.RecalcStyleDuration || 0) * 1000, scriptMs: (met.ScriptDuration || 0) * 1000,
      taskMs: (met.TaskDuration || 0) * 1000, heapUsed: met.JSHeapUsedSize, heapTotal: met.JSHeapTotalSize },
    consoleErrors, pageErrors, warnings, failedResources,
  };
}

function attributeLoaf(loaf) {
  const by = new Map();
  for (const e of loaf) {
    for (const s of e.scripts || []) {
      const url = s.url ? path.basename(s.url.split("?")[0]) : "(inline)";
      const inv = s.invoker || s.invokerType || "?";
      const invoker = /^https?:\/\//.test(inv) ? "script " + (path.basename(inv.split("?")[0]) || "/") : inv;   // a script's own evaluation is invoked by its URL; keep the basename, never the query
      // A long-animation-frame script entry names the task's ENTRY POINT. For every pushed frame that is
      // the bench's own onmessage wrapper, inside which the shim's dispatch and the bundle's render run
      // synchronously, so the row is labelled for what it holds rather than for the instrument's file.
      const key = url === "ui-bench-instrument.js" ? `message handler (shim + bundle) <${invoker}>` : `${url}:${s.fn || "(anonymous)"} <${invoker}>`;
      const row = by.get(key) || { key, count: 0, durationMs: 0 };
      row.count++; row.durationMs += s.duration || 0;
      by.set(key, row);
    }
  }
  return Array.from(by.values()).sort((a, b) => b.durationMs - a.durationMs).slice(0, 10)
    .map((r) => ({ ...r, durationMs: round1(r.durationMs) }));
}

const round1 = (x) => (x == null ? null : Math.round(x * 10) / 10);
const roundStats = (s) => ({ n: s.n, p50: round1(s.p50), p90: round1(s.p90), max: round1(s.max), mean: round1(s.mean) });

/** Fold one or more replay runs into the report shape --json writes and --compare reads. */
export function buildReport({ app, framesFile, cpuThrottle, fast, iters, browser, runs, cpuProfileFiles = [], sourceMapDir = null }) {
  const frames = runs.flatMap((r) => r.perFrame);
  const byType = {};
  for (const f of frames) {
    const s = (byType[f.type] ||= { count: 0, measured: 0, settleMissing: 0, bytes: 0, bytesMax: 0, handler: [], settle: [] });
    s.count++; s.bytes += f.bytes; if (f.bytes > s.bytesMax) s.bytesMax = f.bytes;
    if (f.handlerMs != null && f.handlerMs >= 0) { s.measured++; s.handler.push(f.handlerMs); }
    if (f.settleMs != null && f.settleMs >= 0) s.settle.push(f.settleMs);
    else if (f.settleMs != null) s.settleMissing++;   // dispatched and timed, but the two-rAF settle stamp never landed
  }
  const types = {};
  for (const [type, s] of Object.entries(byType).sort((a, b) => b[1].bytes - a[1].bytes)) {
    types[type] = { count: s.count / runs.length, measured: s.measured / runs.length, settleMissing: s.settleMissing, bytes: s.bytes / runs.length, bytesMax: s.bytesMax,
      handlerMs: roundStats(summarize(s.handler)), settleMs: roundStats(summarize(s.settle)) };
  }
  const settleMissing = Object.values(byType).reduce((a, s) => a + s.settleMissing, 0);
  const firstIdx = runs[0].perFrame.findIndex((f) => f.type !== "ka");
  const first = firstIdx >= 0 ? runs.map((r) => r.perFrame[firstIdx]).filter(Boolean) : [];
  const loafAll = runs.flatMap((r) => r.loaf);
  const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);
  return {
    tool: "ui-bench", version: 1, app, framesFile, cpuThrottle: cpuThrottle || 1, fast: !!fast, iters: runs.length, browser,
    generatedAt: new Date().toISOString(),
    frames: { total: runs[0].perFrame.length, bytes: runs[0].perFrame.reduce((a, f) => a + f.bytes, 0), replayMs: round1(mean(runs.map((r) => r.replayMs))),
      readyMs: round1(mean(runs.map((r) => r.readyMs))), reconnects: runs.reduce((a, r) => a + r.reconnects, 0), misaligned: runs.reduce((a, r) => a + r.misaligned, 0),
      settleMissing, addListenerMessages: runs.reduce((a, r) => a + (r.addListenerMessages || 0), 0),
      buildBannerRaised: runs.filter((r) => r.banner === "build").length, connBannerRaised: runs.filter((r) => r.banner === "conn").length },
    first: first.length ? { index: firstIdx, type: first[0].type, bytes: first[0].bytes, handlerMs: round1(mean(first.map((f) => f.handlerMs))), settleMs: round1(mean(first.map((f) => f.settleMs))) } : null,
    types,
    loaf: { kind: runs[0].loafKind, count: loafAll.length / runs.length, durationMs: round1(mean(runs.map((r) => r.loaf.reduce((a, e) => a + e.duration, 0)))),
      blockingMs: round1(mean(runs.map((r) => r.loaf.reduce((a, e) => a + (e.blocking || 0), 0)))), maxMs: round1(Math.max(0, ...loafAll.map((e) => e.duration))),
      topScripts: attributeLoaf(loafAll) },
    end: { afterGc: true, heapUsed: Math.round(mean(runs.map((r) => r.cdp.heapUsed ?? (r.heap ? r.heap.used : 0)))), heapTotal: Math.round(mean(runs.map((r) => r.cdp.heapTotal ?? (r.heap ? r.heap.total : 0)))),
      domElements: Math.round(mean(runs.map((r) => r.domElements))), cdpNodes: Math.round(mean(runs.map((r) => r.cdp.nodes))), jsEventListeners: Math.round(mean(runs.map((r) => r.cdp.jsEventListeners))),
      layoutCount: Math.round(mean(runs.map((r) => r.cdp.layoutCount))), recalcStyleCount: Math.round(mean(runs.map((r) => r.cdp.recalcStyleCount))),
      layoutMs: round1(mean(runs.map((r) => r.cdp.layoutMs))), recalcStyleMs: round1(mean(runs.map((r) => r.cdp.recalcStyleMs))),
      scriptMs: round1(mean(runs.map((r) => r.cdp.scriptMs))), taskMs: round1(mean(runs.map((r) => r.cdp.taskMs))) },
    console: { errors: runs.flatMap((r) => r.consoleErrors), pageErrors: runs.flatMap((r) => r.pageErrors), warnings: runs.reduce((a, r) => a + r.warnings, 0),
      failedResources: runs.flatMap((r) => r.failedResources) },
    clientMessages: runs.reduce((acc, r) => { for (const [k, v] of Object.entries(r.clientMessages)) acc[k] = (acc[k] || 0) + v; return acc; }, {}),
    clientDiag: runs.reduce((acc, r) => { for (const [k, v] of Object.entries(r.clientDiag)) acc[k] = (acc[k] || 0) + v; return acc; }, {}),
    perFrame: runs.length === 1 ? runs[0].perFrame.map((f) => ({ i: f.i, type: f.type, bytes: f.bytes, at: f.at, handlerMs: round1(f.handlerMs), settleMs: round1(f.settleMs) })) : undefined,
    cpuProfile: runs.some((r) => r.profiling && r.profiling.profile) ? profileReport(runs, firstIdx, cpuProfileFiles, sourceMapDir) : undefined,
  };
}

export async function replay({ app, framesFile, cpuThrottle = 1, iters = 1, fast = false, dist, jsonOut, cpuProfile, log = console.error }) {
  if (!APP_CAPS[app]) throw new Error(`unknown app ${app}; one of ${APPS.join(", ")}`);
  const { frames } = loadFrames(framesFile);
  if (!frames.length) throw new Error(`no frames in ${framesFile}`);
  const pageServer = await startPageServer({ dist, log: (s) => log("kernel page server: " + s.trimEnd()) });
  let front, browser;
  // A signal aimed at this process stops both servers before it exits; the finally below covers every
  // other way out. The Handler would also end on its own when its stdin pipe closes, but not the front.
  const onSignal = (sig) => {
    if (browser) browser.close().catch(() => {});
    if (front) front.stop();
    pageServer.stop();
    process.exit(sig === "SIGINT" ? 130 : 143);
  };
  process.once("SIGINT", onSignal);
  process.once("SIGTERM", onSignal);
  try {
    front = await startFront({ pagePort: pageServer.port });
    browser = await launchBrowser({ tmpRoot: pageServer.tmp });
    const runs = [];
    for (let i = 0; i < iters; i++) {
      log(`ui-bench: replaying ${frames.length} frames into app=${app} (${fast ? "back-to-back" : "recorded pacing"}, cpu x${cpuThrottle})${iters > 1 ? ` iteration ${i + 1}/${iters}` : ""}`);
      runs.push(await replayOnce({ browser, app, frames, fast, cpuThrottle, front, token: pageServer.token, cpuProfile: !!cpuProfile, log }));
    }
    const cpuProfileFiles = cpuProfile ? writeProfiles(cpuProfile, runs) : [];
    const report = buildReport({ app, framesFile, cpuThrottle, fast, iters, browser: browser.version(), runs, cpuProfileFiles, sourceMapDir: dist || path.join(EXT_DIR, "dist") });
    if (jsonOut) { fs.mkdirSync(path.dirname(path.resolve(jsonOut)), { recursive: true }); fs.writeFileSync(jsonOut, JSON.stringify(report, null, 1) + "\n"); }
    return report;
  } finally {
    process.removeListener("SIGINT", onSignal);
    process.removeListener("SIGTERM", onSignal);
    if (browser) await browser.close().catch(() => {});
    if (front) front.stop();
    pageServer.stop();
  }
}

// ── --cpu-profile: V8 samples across the replay, folded by function ─────────────────────────────

export const PROFILE_INTERVAL_US = 500;
const PROFILE_META = new Set(["(root)", "(program)", "(idle)", "(garbage collector)"]);
const TOP_OVERALL = 25, TOP_WINDOW = 20;

/** The label a call frame files under: url-basename:function:line, the line 1-based as DevTools shows
 *  it. V8's bookkeeping nodes ((program), (idle), (garbage collector), (root)) keep their bare names; a
 *  builtin (no url, no line: getBoundingClientRect, querySelectorAll) is "(native):name"; code without a
 *  url but with a line (an eval) is "(inline)". A page's inline script carries the page URL, so the shim
 *  files under the page's basename with the query dropped. */
export function frameKey(cf) {
  if (!cf) return "(unknown)";
  const fn = cf.functionName || "";
  const line = cf.lineNumber ?? -1;
  if (!cf.url) {
    if (PROFILE_META.has(fn)) return fn;
    if (line < 0) return `(native):${fn || "(anonymous)"}`;
    return `(inline):${fn || "(anonymous)"}:${line + 1}`;
  }
  return `${path.basename(cf.url.split("?")[0]) || cf.url}:${fn || "(anonymous)"}:${line + 1}`;
}

/** Bundle positions to source positions through the .map files esbuild writes beside the bundles in
 *  `distDir`. Returns a function of a call frame giving "ui/webview/feed.ts:4477" (relative to the repo
 *  when the source lies inside it) or null when there is no map or no mapping. */
export function sourceLocator(distDir) {
  const maps = new Map();
  const loaded = new Set(), missing = new Set();
  const load = (base) => {
    if (maps.has(base)) return maps.get(base);
    let m = null;
    const file = path.join(distDir, base + ".map");
    try { m = { sm: new SourceMap(JSON.parse(fs.readFileSync(file, "utf8"))), dir: path.dirname(file) }; } catch { m = null; }
    maps.set(base, m);
    (m ? loaded : missing).add(base);
    return m;
  };
  const locate = (cf) => {
    if (!cf || !cf.url || cf.lineNumber == null || cf.lineNumber < 0) return null;
    const m = load(path.basename(cf.url.split("?")[0]));
    if (!m) return null;
    const e = m.sm.findEntry(cf.lineNumber, Math.max(0, cf.columnNumber || 0));
    // findEntry returns the nearest mapping at or before the position, on any line; a line the map does not
    // cover would borrow the previous line's source, so the mapping must sit on the asked-for line.
    if (!e || e.originalSource == null || e.originalLine == null || e.generatedLine !== cf.lineNumber) return null;
    const abs = path.resolve(m.dir, e.originalSource);
    const rel = path.relative(REPO, abs);
    const shown = rel && !rel.startsWith("..") && !path.isAbsolute(rel) ? rel : e.originalSource.replace(/^(\.\.\/)+/, "");
    return `${shown}:${e.originalLine + 1}`;
  };
  /** The source of a 0-based bundle LINE's first mapping, for V8's per-line ticks. A line's first mapping
   *  can start at its indentation column (bundled node_modules code does this), where a column-0 probe
   *  lands on the previous line and the same-line guard refuses it; so the columns are stepped until a
   *  mapping on the line answers. */
  locate.line = (cf, line) => {
    if (!cf || !cf.url || line == null || line < 0 || !load(path.basename(cf.url.split("?")[0]))) return null;
    for (let c = 0; c < 256; c++) { const r = locate({ ...cf, lineNumber: line, columnNumber: c }); if (r) return r; }
    return null;
  };
  /** Whether a bundle's map is beside it (loads it). */
  locate.probe = (base) => !!load(base);
  locate.loaded = loaded;
  locate.missing = missing;
  return locate;
}

/** Pin the page-to-profile clock offset with the profile's own evidence. Every sample whose stack holds
 *  the bench's onmessage wrapper was taken inside some frame's handler window, so the offsets that put
 *  the most of them inside the windows hold the right one; the bracketing reads of performance.now()
 *  only bound it. A grid search over ±bound ms at a quarter of the sampling interval; the offsets that
 *  tie for the maximum form a plateau, and the answer is its midpoint with half its width (at least one
 *  grid step) as the uncertainty. When even the best offset places under half the wrapper's samples
 *  inside, the evidence does not fit the windows and the bracketing estimate is returned unchanged.
 *  `windows` are [t0, t1] in page ms. Returns {p0, alignMs, inside, refined}. */
export function refineAlignment(profile, p0, bound, windows) {
  const nodes = new Map(), parent = new Map(), wrapped = new Map();
  for (const n of profile.nodes || []) { nodes.set(n.id, n); for (const c of n.children || []) parent.set(c, n.id); }
  const underWrapper = (id) => {
    if (wrapped.has(id)) return wrapped.get(id);
    let r = false;
    for (let cur = id; cur != null && nodes.has(cur); cur = parent.get(cur)) {
      const cf = nodes.get(cur).callFrame;
      if (cf && cf.url && path.basename(cf.url.split("?")[0]) === "ui-bench-instrument.js") { r = true; break; }
    }
    wrapped.set(id, r);
    return r;
  };
  const xs = [];
  const samples = profile.samples || [], deltas = profile.timeDeltas || [];
  let t = profile.startTime || 0;
  for (let i = 0; i < samples.length; i++) { t += deltas[i] || 0; if (underWrapper(samples[i])) xs.push((t - (profile.startTime || 0)) / 1000 + p0); }
  const sorted = windows.filter((w) => w[1] > w[0]).sort((a, b) => a[0] - b[0]);
  if (!xs.length || !sorted.length) return { p0, alignMs: bound, inside: null, refined: false };
  const inside = (x) => {
    let lo = 0, hi = sorted.length - 1;
    while (lo <= hi) { const mid = (lo + hi) >> 1; if (sorted[mid][0] <= x) lo = mid + 1; else hi = mid - 1; }
    return hi >= 0 && x < sorted[hi][1];
  };
  const step = PROFILE_INTERVAL_US / 1000 / 4;
  const span = Math.max(bound, 1);
  let bestN = -1;
  const plateau = [];
  for (let k = 0, d = -span; d <= span + 1e-9; k++, d = -span + k * step) {
    let n = 0;
    for (const x of xs) if (inside(x + d)) n++;
    if (n > bestN) { bestN = n; plateau.length = 0; }
    if (n === bestN) plateau.push(d);
  }
  const share = bestN / xs.length;
  if (share < 0.5) return { p0, alignMs: bound, inside: share, refined: false };
  const lo = plateau[0], hi = plateau[plateau.length - 1];
  return { p0: p0 + (lo + hi) / 2, alignMs: Math.max(step, (hi - lo) / 2), inside: share, refined: true };
}

/** Fold a V8 .cpuprofile ({nodes, samples, timeDeltas, startTime, endTime}, times in microseconds)
 *  into per-function time. Sample i owns the interval to sample i+1 (the last owns the interval to
 *  endTime): its node's function takes it as self time, and every distinct function on its stack takes
 *  it once as total time, so recursion is not double counted. The bookkeeping nodes are reported in
 *  `meta`, never ranked. `window` = [fromUs, toUs] on the profile's clock restricts the fold. */
export function aggregateProfile(profile, window = null) {
  const nodes = new Map(), parent = new Map(), keyOf = new Map(), stacks = new Map(), cfOf = new Map();
  for (const n of profile.nodes || []) { nodes.set(n.id, n); for (const c of n.children || []) parent.set(c, n.id); }
  const key = (id) => {
    let k = keyOf.get(id);
    if (k === undefined) { const n = nodes.get(id); k = frameKey(n && n.callFrame); keyOf.set(id, k); if (n && n.callFrame && !cfOf.has(k)) cfOf.set(k, n.callFrame); }
    return k;
  };
  const stackKeys = (id) => {
    let s = stacks.get(id);
    if (s) return s;
    const seen = new Set();
    for (let cur = id; cur != null && nodes.has(cur); cur = parent.get(cur)) { const k = key(cur); if (!PROFILE_META.has(k)) seen.add(k); }
    s = [...seen]; stacks.set(id, s); return s;
  };
  const self = new Map(), total = new Map(), count = new Map(), nodeSelf = new Map(), meta = {};
  const samples = profile.samples || [], deltas = profile.timeDeltas || [];
  let t = profile.startTime || 0, sampledUs = 0, inWindow = 0;
  for (let i = 0; i < samples.length; i++) {
    t += deltas[i] || 0;
    const dur = i + 1 < samples.length ? (deltas[i + 1] || 0) : Math.max(0, (profile.endTime || t) - t);
    if (window && (t < window[0] || t >= window[1])) continue;
    sampledUs += dur; inWindow++;
    const k = key(samples[i]);
    if (PROFILE_META.has(k)) { meta[k] = (meta[k] || 0) + dur; continue; }
    self.set(k, (self.get(k) || 0) + dur);
    count.set(k, (count.get(k) || 0) + 1);
    nodeSelf.set(samples[i], (nodeSelf.get(samples[i]) || 0) + dur);
    for (const sk of stackKeys(samples[i])) total.set(sk, (total.get(sk) || 0) + dur);
  }
  // V8's per-line ticks (positionTicks) split a node's self time over the lines of its function, 1-based
  // lines of the bundle. They cover the whole profile, so a window gets none; a node's self time is spread
  // over its lines in proportion to their ticks.
  const lines = new Map();
  if (!window) for (const n of profile.nodes || []) {
    if (!n.positionTicks || !n.positionTicks.length || !n.hitCount || !nodeSelf.has(n.id)) continue;
    const k = key(n.id);
    if (PROFILE_META.has(k)) continue;
    const perTick = nodeSelf.get(n.id) / n.hitCount;
    const m = lines.get(k) || new Map();
    for (const pt of n.positionTicks) m.set(pt.line, (m.get(pt.line) || 0) + pt.ticks * perTick);
    lines.set(k, m);
  }
  const functions = [...total.keys()].map((k) => ({ key: k, selfMs: (self.get(k) || 0) / 1000, totalMs: total.get(k) / 1000, samples: count.get(k) || 0, cf: cfOf.get(k),
    ...(lines.has(k) ? { lines: [...lines.get(k)].map(([line, us]) => ({ line, ms: us / 1000 })).sort((a, b) => b.ms - a.ms) } : {}) }));
  return { durationMs: (window ? window[1] - window[0] : (profile.endTime || 0) - (profile.startTime || 0)) / 1000, sampledMs: sampledUs / 1000, samples: inWindow,
    meta: Object.fromEntries(Object.entries(meta).map(([k, v]) => [k, v / 1000])), functions };
}

const bySelf = (fns) => [...fns].sort((a, b) => b.selfMs - a.selfMs || b.totalMs - a.totalMs || a.key.localeCompare(b.key));
const byTotal = (fns) => [...fns].sort((a, b) => b.totalMs - a.totalMs || b.selfMs - a.selfMs || a.key.localeCompare(b.key));
const HOT_LINES = 4, HOT_LINE_SHARE = 0.05;
const roundFn = (locate, withLines = false) => (f) => {
  const src = locate ? locate(f.cf) : null;
  const row = { key: f.key, selfMs: round1(f.selfMs), totalMs: round1(f.totalMs), samples: f.samples, ...(src ? { src } : {}) };
  if (withLines && f.lines && f.selfMs > 0 && f.cf && f.cf.url) {
    // The lines of the function that hold its self time (the 1-based bundle line, its share, its source). A
    // builtin's ticks name its call sites' lines with no file to read them in, so those stay unlisted.
    row.lines = f.lines.filter((l) => l.ms / f.selfMs >= HOT_LINE_SHARE).slice(0, HOT_LINES).map((l) => {
      const at = locate && f.cf ? locate.line(f.cf, l.line - 1) : null;
      return { line: l.line, ms: round1(l.ms), share: Math.round((l.ms / f.selfMs) * 100) / 100, ...(at ? { src: at } : {}) };
    });
  }
  return row;
};

/** Sum aggregates from several runs (iterations) by function key. */
export function mergeAggregates(aggs) {
  const fns = new Map(), meta = {};
  let durationMs = 0, sampledMs = 0, samples = 0;
  for (const a of aggs) {
    durationMs += a.durationMs; sampledMs += a.sampledMs; samples += a.samples;
    for (const [k, v] of Object.entries(a.meta)) meta[k] = (meta[k] || 0) + v;
    for (const f of a.functions) {
      const m = fns.get(f.key) || { key: f.key, selfMs: 0, totalMs: 0, samples: 0, cf: f.cf };
      m.selfMs += f.selfMs; m.totalMs += f.totalMs; m.samples += f.samples;
      if (f.lines) { const ln = new Map((m.lines || []).map((l) => [l.line, l.ms])); for (const l of f.lines) ln.set(l.line, (ln.get(l.line) || 0) + l.ms); m.lines = [...ln].map(([line, ms]) => ({ line, ms })).sort((a, b) => b.ms - a.ms); }
      fns.set(f.key, m);
    }
  }
  return { durationMs, sampledMs, samples, meta, functions: [...fns.values()] };
}

/** Rank an aggregate: the top functions by self time and by total time, the bookkeeping totals beside;
 *  `locate` (sourceLocator) adds each function's source position when the dist carries maps. */
export function rankProfile(agg, top, locate = null) {
  const r = roundFn(locate), rl = roundFn(locate, true);
  const self = bySelf(agg.functions);
  const hot = Math.min(top, HOT_FUNCTIONS);
  return { durationMs: round1(agg.durationMs), sampledMs: round1(agg.sampledMs), samples: agg.samples, functions: agg.functions.length,
    meta: Object.fromEntries(Object.entries(agg.meta).map(([k, v]) => [k, round1(v)])),
    topSelf: [...self.slice(0, hot).map(rl), ...self.slice(hot, top).map(r)], topTotal: byTotal(agg.functions).slice(0, top).map(r) };
}
const HOT_FUNCTIONS = 5;   // the top self-time functions whose lines are shown

/** The frames worth their own window: the first content frame and the largest frame of every type
 *  except keepalives. Windows cover the synchronous handler (t0 to t0 + handler), the part of a frame's
 *  cost the JavaScript sampler can see; style, layout and paint after it are not JavaScript. */
function profileWindows(perFrame, firstIdx) {
  const picks = [];
  if (firstIdx >= 0 && perFrame[firstIdx]) picks.push({ label: "first content frame", f: perFrame[firstIdx] });
  const largest = new Map();
  for (const f of perFrame) { if (f.type === "ka") continue; const cur = largest.get(f.type); if (!cur || f.bytes > cur.bytes) largest.set(f.type, f); }
  for (const [type, f] of largest) if (!picks.some((p) => p.f.i === f.i)) picks.push({ label: `largest ${type}`, f });
  return picks;
}

function profileReport(runs, firstIdx, files, sourceMapDir) {
  const locate = sourceMapDir ? sourceLocator(sourceMapDir) : null;
  const profiled = runs.filter((r) => r.profiling && r.profiling.profile);
  const handlerWindows = (r) => r.perFrame.filter((f) => f.t0 != null && f.handlerMs != null && f.handlerMs >= 0).map((f) => [f.t0, f.t0 + f.handlerMs]);
  const aligned = profiled.map((r) => ({ r, al: refineAlignment(r.profiling.profile, r.profiling.p0, r.profiling.alignMs, handlerWindows(r)) }));
  const overall = rankProfile(mergeAggregates(profiled.map((r) => aggregateProfile(r.profiling.profile))), TOP_OVERALL, locate);
  const windows = [];
  for (const { label, f } of profileWindows(runs[0].perFrame, firstIdx)) {
    const aggs = [];
    for (const { r, al } of aligned) {
      const pf = r.perFrame[f.i];
      if (!pf || pf.t0 == null || pf.handlerMs == null || pf.handlerMs < 0) continue;
      const { profile } = r.profiling;
      const toUs = (ms) => profile.startTime + (ms - al.p0) * 1000;
      aggs.push(aggregateProfile(profile, [toUs(pf.t0), toUs(pf.t0 + pf.handlerMs)]));
    }
    if (!aggs.length) continue;
    windows.push({ label, index: f.i, type: f.type, bytes: f.bytes, handlerMs: round1(f.handlerMs), ...rankProfile(mergeAggregates(aggs), TOP_WINDOW, locate) });
  }
  const insides = aligned.map(({ al }) => al.inside).filter((x) => x != null);
  // The bundles the profile names (served from /dist/): the source-position claim rests on their maps
  // having loaded, not on a directory having been configured. A --production dist is minified and has none.
  const bundles = new Set();
  for (const r of profiled) for (const n of r.profiling.profile.nodes || []) {
    const url = n.callFrame && n.callFrame.url;
    if (!url) continue;
    try { const u = new URL(url); if (u.pathname.startsWith("/dist/") && u.pathname.endsWith(".js")) bundles.add(path.basename(u.pathname)); } catch {}
  }
  const sourceMapsLoaded = [], sourceMapsMissing = [];
  for (const b of [...bundles].sort()) (locate && locate.probe(b) ? sourceMapsLoaded : sourceMapsMissing).push(b);
  return { files, samplingIntervalUs: PROFILE_INTERVAL_US,
    alignMs: round1(Math.max(...aligned.map(({ al }) => al.alignMs))), alignBoundMs: round1(Math.max(...profiled.map((r) => r.profiling.alignMs))),
    alignRefined: aligned.length > 0 && aligned.every(({ al }) => al.refined),
    wrapperSamplesInHandlers: insides.length ? round1(Math.min(...insides) * 100) / 100 : null,
    sourceMaps: sourceMapsLoaded.length > 0, sourceMapsLoaded, sourceMapsMissing, ...overall, windows };
}

/** Write each profiled iteration's .cpuprofile (Chrome DevTools loads it); with several iterations the
 *  index goes before the extension. Returns the paths written. */
function writeProfiles(out, runs) {
  const abs = path.resolve(out);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  const profiled = runs.filter((r) => r.profiling && r.profiling.profile);
  const files = [];
  profiled.forEach((r, i) => {
    const ext = path.extname(abs);
    const file = profiled.length === 1 ? abs : path.join(path.dirname(abs), `${path.basename(abs, ext)}-${i + 1}${ext}`);
    fs.writeFileSync(file, JSON.stringify(stripProfileQueries(r.profiling.profile)));
    files.push(file);
  });
  return files;
}

/** The profile with every call frame's URL query dropped: V8 records the document URL for the page's inline
 *  shim, and the page was navigated to /feed?token=<the run's serve token>; the file is meant to be opened
 *  and shared, so the token never reaches it (frameKey and the locator already drop the query). */
export function stripProfileQueries(profile) {
  const nodes = (profile.nodes || []).map((n) => (n.callFrame && typeof n.callFrame.url === "string" && n.callFrame.url.includes("?"))
    ? { ...n, callFrame: { ...n.callFrame, url: n.callFrame.url.split("?")[0] } } : n);
  return { ...profile, nodes };
}

const fmtFn = (f) => `${fmtMs(f.selfMs).padStart(9)} ${fmtMs(f.totalMs).padStart(9)} ${String(f.samples).padStart(7)}  ${f.key}${f.src ? `  ${f.src}` : ""}`;
const fmtMeta = (meta) => Object.entries(meta).map(([k, v]) => `${k} ${fmtMs(v)} ms`).join(", ") || "none";

export function renderProfile(cp) {
  const out = [];
  out.push(`cpu profile: ${cp.samples} samples over ${fmtMs(cp.durationMs)} ms at ${cp.samplingIntervalUs} us, ${cp.functions} functions; bookkeeping: ${fmtMeta(cp.meta)}`);
  const pct = cp.wrapperSamplesInHandlers != null ? `${Math.round(cp.wrapperSamplesInHandlers * 100)}% of the message handler's samples inside the frames' handler windows` : "no handler windows to check against";
  out.push(`  page-to-profile clock alignment ±${fmtMs(cp.alignMs)} ms ${cp.alignRefined ? `(refined from the ±${fmtMs(cp.alignBoundMs)} ms bracketing estimate; ${pct})` : `(the bracketing estimate; the refinement did not apply: ${pct})`}${cp.sourceMaps ? `; source positions from ${(cp.sourceMapsLoaded || []).map((b) => b + ".map").join(", ")}` : ""}`);
  if (cp.sourceMapsMissing && cp.sourceMapsMissing.length) out.push(`  warning: no ${cp.sourceMapsMissing.map((b) => b + ".map").join(", ")} beside the served bundle${cp.sourceMapsMissing.length === 1 ? "" : "s"}; names and lines are the bundle's own, and a --production build is minified (rebuild with node esbuild.js, no --production)`);
  for (const f of cp.files || []) out.push(`  written: ${f} (load it in Chrome DevTools, Performance panel)`);
  const head = `${"self ms".padStart(9)} ${"total ms".padStart(9)} ${"samples".padStart(7)}  url:function:line${cp.sourceMaps ? "  source:line" : ""}`;
  out.push(`  top ${cp.topSelf.length} by self time${cp.topSelf.some((f) => f.lines) ? " (under a function, the lines that hold its self time: share, ms, bundle line, source)" : ""}`, `  ${head}`);
  for (const f of cp.topSelf) {
    out.push(`  ${fmtFn(f)}`);
    for (const l of f.lines || []) out.push(`  ${" ".repeat(28)}${String(Math.round(l.share * 100)).padStart(3)}%  ${fmtMs(l.ms).padStart(7)} ms  line ${l.line}${l.src ? `  ${l.src}` : ""}`);
  }
  out.push(`  top ${cp.topTotal.length} by total time`, `  ${head}`);
  for (const f of cp.topTotal) out.push(`  ${fmtFn(f)}`);
  for (const w of cp.windows || []) {
    out.push("", `  window: ${w.label} (${w.type}, ${fmtBytes(w.bytes)}, frame ${w.index}): handler ${fmtMs(w.handlerMs)} ms, ${w.samples} samples, ${fmtMs(w.sampledMs)} ms sampled; bookkeeping: ${fmtMeta(w.meta)}`);
    out.push(`    top ${w.topSelf.length} by self time`, `    ${head}`);
    for (const f of w.topSelf) out.push(`    ${fmtFn(f)}`);
    out.push(`    top ${w.topTotal.length} by total time`, `    ${head}`);
    for (const f of w.topTotal) out.push(`    ${fmtFn(f)}`);
  }
  return out.join("\n");
}

// ── text rendering ───────────────────────────────────────────────────────────────────────────────

export function fmtBytes(n) {
  if (n == null) return "-";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}
const fmtMs = (x) => (x == null ? "-" : x >= 100 ? String(Math.round(x)) : x.toFixed(1));
const stats3 = (s) => `${fmtMs(s.p50)} / ${fmtMs(s.p90)} / ${fmtMs(s.max)}`;

export function renderReport(r) {
  const out = [];
  out.push(`ui-bench ${r.app}: ${r.frames.total} frames, ${fmtBytes(r.frames.bytes)}, replay ${fmtMs(r.frames.replayMs)} ms (${r.fast ? "back-to-back" : "recorded pacing"}), cpu x${r.cpuThrottle}, ${r.iters} iteration${r.iters === 1 ? "" : "s"}, ${r.browser}`);
  out.push(`page ready (navigation to the bundle's handshake): ${fmtMs(r.frames.readyMs)} ms${r.frames.reconnects ? `; shim reconnects during replay: ${r.frames.reconnects}` : ""}${r.frames.misaligned ? `; frames whose page record did not match in length: ${r.frames.misaligned}` : ""}`);
  if (r.first) out.push(`first content frame: ${r.first.type}, ${fmtBytes(r.first.bytes)}, handler ${fmtMs(r.first.handlerMs)} ms, settled ${fmtMs(r.first.settleMs)} ms`);
  out.push("");
  out.push(`${"type".padEnd(14)} ${"count".padStart(7)} ${"bytes".padStart(10)} ${"max".padStart(10)}   ${"handler p50/p90/max ms".padEnd(26)} ${"settle p50/p90/max ms".padEnd(26)}`);
  for (const [type, s] of Object.entries(r.types)) {
    out.push(`${type.padEnd(14)} ${String(s.count).padStart(7)} ${fmtBytes(s.bytes).padStart(10)} ${fmtBytes(s.bytesMax).padStart(10)}   ${stats3(s.handlerMs).padEnd(26)} ${stats3(s.settleMs).padEnd(26)}${s.measured < s.count ? `  (${s.count - s.measured} unmeasured)` : ""}${s.settleMissing ? `  (${s.settleMissing} settle missing)` : ""}`);
  }
  if (r.frames.settleMissing) out.push(`warning: ${r.frames.settleMissing} frame${r.frames.settleMissing === 1 ? "" : "s"} never received a settle stamp; the settle columns are computed over the frames that did`);
  if (r.frames.addListenerMessages) out.push(`warning: ${r.frames.addListenerMessages} message listener${r.frames.addListenerMessages === 1 ? " was" : "s were"} added with addEventListener; the handler column does not time work done there`);
  if (r.frames.buildBannerRaised) out.push(`warning: the page raised its "newer build" banner in ${r.frames.buildBannerRaised} run${r.frames.buildBannerRaised === 1 ? "" : "s"} (a keepalive's dv is newer than the dist under test): a few extra elements and a layout the frames did not cause`);
  if (r.frames.connBannerRaised) out.push(`warning: the page raised its "connection stale" banner in ${r.frames.connBannerRaised} run${r.frames.connBannerRaised === 1 ? "" : "s"}`);
  out.push("");
  out.push(`long animation frames (${r.loaf.kind || "unsupported"}): ${r.loaf.count} entries, ${fmtMs(r.loaf.durationMs)} ms total, ${fmtMs(r.loaf.blockingMs)} ms blocking, longest ${fmtMs(r.loaf.maxMs)} ms`);
  out.push("  script attribution names each task's entry point (the message handler, a rAF, a timer, a script's evaluation), not the bundle function; --cpu-profile gives functions");
  for (const s of r.loaf.topScripts) out.push(`  ${fmtMs(s.durationMs).padStart(8)} ms  x${String(s.count).padEnd(4)} ${s.key}`);
  out.push(`end state: JS heap ${fmtBytes(r.end.heapUsed)} used of ${fmtBytes(r.end.heapTotal)} after a forced GC; DOM ${r.end.domElements} elements (${r.end.cdpNodes} nodes, ${r.end.jsEventListeners} listeners)`);
  out.push(`  cumulative since navigation (page load and idle timers included; the timeline redraws every animation frame while it follows now): ${r.end.layoutCount} layouts ${fmtMs(r.end.layoutMs)} ms; ${r.end.recalcStyleCount} style recalcs ${fmtMs(r.end.recalcStyleMs)} ms; script ${fmtMs(r.end.scriptMs)} ms; tasks ${fmtMs(r.end.taskMs)} ms`);
  out.push(`console: ${r.console.errors.length} errors, ${r.console.pageErrors.length} uncaught exceptions, ${r.console.warnings} warnings`);
  for (const e of r.console.errors.slice(0, 10)) out.push(`  error: ${e.slice(0, 300)}`);
  for (const e of r.console.pageErrors.slice(0, 10)) out.push(`  uncaught: ${e.slice(0, 300)}`);
  for (const e of r.console.failedResources.slice(0, 10)) out.push(`  failed resource: ${e}`);
  out.push(`messages the pane sent: ${Object.entries(r.clientMessages).map(([k, v]) => `${k} ${v}`).join(", ") || "none"}${Object.keys(r.clientDiag || {}).length ? ` (clientDiag: ${Object.entries(r.clientDiag).map(([k, v]) => `${k} ${v}`).join(", ")})` : ""}`);
  if (r.fast) out.push("note: back-to-back replay; a frame's settle time includes the frames dispatched after it before the next rendered frame, so settle percentiles overlap while handler times do not.");
  if (r.cpuProfile) out.push("", renderProfile(r.cpuProfile));
  return out.join("\n");
}

// ── --compare ────────────────────────────────────────────────────────────────────────────────────

function delta(a, b) {
  if (a == null || b == null) return { a, b, diff: null, pct: null };
  const diff = b - a;
  return { a, b, diff: round1(diff), pct: a ? round1((diff / a) * 100) : null };
}

/** The differences between two replay reports: per-type timing percentiles, long-animation-frame
 *  totals, and end state. Pure arithmetic over the JSON shape, no browser. */
export function compareReports(a, b) {
  const types = {};
  for (const type of new Set([...Object.keys(a.types || {}), ...Object.keys(b.types || {})])) {
    const x = a.types[type] || {}, y = b.types[type] || {};
    const sx = x.settleMs || {}, sy = y.settleMs || {}, hx = x.handlerMs || {}, hy = y.handlerMs || {};
    types[type] = { count: delta(x.count ?? null, y.count ?? null), bytes: delta(x.bytes ?? null, y.bytes ?? null),
      settleP50: delta(sx.p50, sy.p50), settleP90: delta(sx.p90, sy.p90), settleMax: delta(sx.max, sy.max),
      handlerP50: delta(hx.p50, hy.p50), handlerP90: delta(hx.p90, hy.p90), handlerMax: delta(hx.max, hy.max) };
  }
  // LayoutCount, ScriptDuration and TaskDuration are cumulative since navigation, so they scale with how
  // long the page sat there: a percentage between runs of different pacing or length says nothing.
  const replayMs = [a.frames?.replayMs ?? null, b.frames?.replayMs ?? null];
  const sameLength = replayMs[0] > 0 && replayMs[1] > 0 && Math.max(replayMs[0] / replayMs[1], replayMs[1] / replayMs[0]) <= 1.25;
  const endComparable = !!a.fast === !!b.fast && sameLength;
  return {
    apps: [a.app, b.app], cpuThrottle: [a.cpuThrottle, b.cpuThrottle], fast: [a.fast, b.fast], replayMs, endComparable,
    first: { bytes: delta(a.first?.bytes, b.first?.bytes), handlerMs: delta(a.first?.handlerMs, b.first?.handlerMs), settleMs: delta(a.first?.settleMs, b.first?.settleMs) },
    types,
    loaf: { count: delta(a.loaf?.count, b.loaf?.count), durationMs: delta(a.loaf?.durationMs, b.loaf?.durationMs), blockingMs: delta(a.loaf?.blockingMs, b.loaf?.blockingMs), maxMs: delta(a.loaf?.maxMs, b.loaf?.maxMs) },
    end: { heapUsed: delta(a.end?.heapUsed, b.end?.heapUsed), domElements: delta(a.end?.domElements, b.end?.domElements), layoutCount: delta(a.end?.layoutCount, b.end?.layoutCount),
      scriptMs: delta(a.end?.scriptMs, b.end?.scriptMs), taskMs: delta(a.end?.taskMs, b.end?.taskMs) },
    console: { errors: [a.console?.errors?.length ?? 0, b.console?.errors?.length ?? 0] },
  };
}

const fmtNum = (x) => (x == null ? "-" : Number.isInteger(x) ? String(x) : fmtMs(x));
const fmtDelta = (d, unit = "", { pct = true } = {}) => {
  if (d.diff == null) return `${fmtNum(d.a)} → ${fmtNum(d.b)}${unit}`;
  if (d.diff === 0) return `${fmtNum(d.a)} → ${fmtNum(d.b)}${unit} (unchanged)`;
  const sign = (x) => (x > 0 ? "+" : "-");
  return `${fmtNum(d.a)} → ${fmtNum(d.b)}${unit} (${sign(d.diff)}${fmtNum(Math.abs(d.diff))}${pct && d.pct != null ? `, ${sign(d.pct)}${fmtNum(Math.abs(d.pct))}%` : ""})`;
};

export function renderCompare(c) {
  const out = [];
  out.push(`compare: ${c.apps[0]} (cpu x${c.cpuThrottle[0]}, ${c.fast[0] ? "fast" : "paced"}) → ${c.apps[1]} (cpu x${c.cpuThrottle[1]}, ${c.fast[1] ? "fast" : "paced"})`);
  out.push(`first content frame: bytes ${fmtDelta(c.first.bytes)}; handler ${fmtDelta(c.first.handlerMs, " ms")}; settled ${fmtDelta(c.first.settleMs, " ms")}`);
  for (const [type, t] of Object.entries(c.types)) {
    out.push(`${type.padEnd(14)} count ${fmtDelta(t.count)}; settle p50 ${fmtDelta(t.settleP50, " ms")}, p90 ${fmtDelta(t.settleP90, " ms")}, max ${fmtDelta(t.settleMax, " ms")}; handler p50 ${fmtDelta(t.handlerP50, " ms")}`);
  }
  out.push(`long animation frames: count ${fmtDelta(c.loaf.count)}; total ${fmtDelta(c.loaf.durationMs, " ms")}; blocking ${fmtDelta(c.loaf.blockingMs, " ms")}; longest ${fmtDelta(c.loaf.maxMs, " ms")}`);
  const pct = { pct: c.endComparable !== false };
  out.push(`end state: heap ${fmtDelta(c.end.heapUsed, " B")}; DOM elements ${fmtDelta(c.end.domElements)}; layouts ${fmtDelta(c.end.layoutCount, "", pct)}; script ${fmtDelta(c.end.scriptMs, " ms", pct)}; tasks ${fmtDelta(c.end.taskMs, " ms", pct)}`);
  if (c.endComparable === false) out.push(`  layouts, script and tasks are cumulative since navigation and the runs differ in pacing or length (replay ${fmtNum(c.replayMs?.[0])} → ${fmtNum(c.replayMs?.[1])} ms), so they carry no percentage`);
  out.push(`console errors: ${c.console.errors[0]} → ${c.console.errors[1]}`);
  return out.join("\n");
}

// ── CLI ──────────────────────────────────────────────────────────────────────────────────────────

const USAGE = `usage:
  node tools/ui-bench.mjs --record <app> --seconds N --out /tmp/…/frames.jsonl [--port P]
  node tools/ui-bench.mjs --replay <app> --frames FILE [--cpu-throttle K] [--iters N] [--fast] [--json OUT] [--dist DIR] [--cpu-profile OUT.cpuprofile]
  node tools/ui-bench.mjs --synthesize <app> --cards N --out FILE [--seed S]
  node tools/ui-bench.mjs --compare A.json B.json
apps: ${APPS.join(", ")} (synthesize: feed, fleet, waiting, timeline)`;

export function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) { o._.push(a); continue; }
    const key = a.slice(2);
    const flags = new Set(["fast", "help"]);
    if (flags.has(key)) { o[key] = true; continue; }
    const v = argv[i + 1];
    if (v === undefined || v.startsWith("--")) throw new Error(`--${key} needs a value`);
    o[key] = v; i++;
  }
  return o;
}

async function main(argv) {
  const o = parseArgs(argv);
  if (o.help || !argv.length) { console.log(USAGE); return 0; }
  const num = (k, d) => (o[k] === undefined ? d : Number(o[k]));
  if (o.record) {
    const port = num("port", Number(process.env.ROMP_KERNEL_PORT) || 29855);
    if (!o.out) throw new Error("--record needs --out");
    await recordFrames({ app: o.record, seconds: num("seconds", 60), out: o.out, port });
    return 0;
  }
  if (o.synthesize) {
    if (!o.out) throw new Error("--synthesize needs --out");
    const frames = synthesizeFrames(o.synthesize, num("cards", 50), { seed: num("seed", 7) });
    writeFrames(o.out, { tool: "ui-bench", mode: "synthesize", app: o.synthesize, cards: num("cards", 50), seed: num("seed", 7), synthetic: true }, frames);
    const s = streamSummary(frames);
    console.error(`ui-bench: wrote ${frames.length} synthetic frames (${fmtBytes(s.bytes)}) for app=${o.synthesize} → ${o.out}`);
    for (const [type, st] of Object.entries(s.byType)) console.error(`  ${type.padEnd(12)} ${String(st.count).padStart(6)}  ${fmtBytes(st.bytes).padStart(10)}`);
    return 0;
  }
  if (o.replay) {
    if (!o.frames) throw new Error("--replay needs --frames FILE");
    const report = await replay({ app: o.replay, framesFile: o.frames, cpuThrottle: num("cpu-throttle", 1), iters: num("iters", 1), fast: !!o.fast, dist: o.dist, jsonOut: o.json, cpuProfile: o["cpu-profile"] });
    console.log(renderReport(report));
    return 0;
  }
  if (o.compare) {
    const b = o._[0];
    if (!b) throw new Error("--compare needs two report files: --compare A.json B.json");
    const A = JSON.parse(fs.readFileSync(o.compare, "utf8")), B = JSON.parse(fs.readFileSync(b, "utf8"));
    console.log(renderCompare(compareReports(A, B)));
    return 0;
  }
  console.log(USAGE);
  return 2;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).then((code) => process.exit(code), (e) => { console.error(`ui-bench: ${e.message}`); process.exit(1); });
}
