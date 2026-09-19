// Browser-side performance telemetry for the dashboard panes (2026-09-06). The kernel's own counters
// (`romp perf`, GET /perf) say what the kernel spent; nothing said what the BROWSER spent on the frames it
// received, so a dashboard that felt slow could not be attributed to a pane, a frame type or a function.
// The feed, Outline, Waiting on you, chat and timeline bundles wrap their window "message" handler through
// this module (the kernel-served timeline page has no bundle of its own: its inline boot wraps through the
// window.__rompPerf that federation.js publishes before it runs); federation times its own merge and
// dispatch of every frame as `fed:<type>`, nested outside the pane's handler, and the collector records
// each level's OWN time (the outer minus what its inner brackets took), so the per-type figures add up.
// The file viewer (file-view.ts perfTimed) brackets each paint of a shown document's text body, a file on disk
// or a markdown URL, as `fileview:paint` under the pane that hosts it (chat, feed or files), so a large document's
// paint shows per minute beside the pane's frames.
// The Files pane gets no frames and times something else (2026-09-09): the bracket above lands under app "files"
// there, and the pane's viewer also brackets `fileview:reflow` (the panel's re-place of its cards over reflowed
// text: the body's width changed, or a text-size step), so the cost of a large reviewed file shows per minute
// under app "files", beside the socket's op replies counted as `fed:<type>`.
// Per frame type the module keeps a count, the summed and maximum handler time, exact counts over 16.7 ms
// (one dropped frame at 60 Hz) and at or over 100 ms, and a fixed log2 histogram (one increment per frame),
// which is additive across minutes so `romp perf client` computes true window percentiles. Two
// requestAnimationFrame callbacks after the outermost handler it records how long the main thread stayed
// busy with the work the handler queued, and it observes the browser's long-animation-frame reports with
// their script attribution. Once a minute it folds all of that into ONE clientDiag row (surface "perf",
// what "minute") on the channel the panes already use for breadcrumbs, so the kernel appends it to
// client-diag.jsonl beside the shim's wsclose rows. A frame whose whole synchronous handling ran 100 ms or
// more also sends a "slowframe" row at once, carrying the long-frame attribution when the browser reports
// one for that frame; at most SLOW_ROWS_PER_MINUTE of those per timer minute, the rest counted in the minute
// row. That budget is re-armed by the minute timer and by pagehide only: the hide flush below starts a new
// minute row without re-arming it, so a page that hides and returns inside a minute posts one cap's worth.
//
// Rows carry numbers and code identifiers only: frame type strings, script file basenames, function names
// with their character position, and invoker names reduced to a tag and event (element ids and any URL
// removed). Never card text, session names, file paths or transcript content.
//
// Idle cost: a 60 s interval that checks one flag, plus an observer callback that runs only when the
// browser reports a long frame. Every browser API is behind a feature check; a page without
// performance.now (the node test stand-ins) gets no telemetry and an unwrapped handler; nothing in here
// throws into the pane. DevTools: window.__rompPerf.snapshot() is the minute in progress.
//
// Two facts about the transport shape the frame types this module sees on a kernel page. The pane shim
// (kernel.py `_shim`) swallows `ka` frames before dispatch, and reassembles `{type:"delta"}` frames into
// the full slot message the bundle always received, so a local delta is counted under its slot's type
// (`bars`, `feed`). A federated remote socket hands frames straight to federation's inbound, where a
// raw delta can still appear; those count as `delta:<slot>`. The shim's JSON.parse and delta reassembly
// run before any bracket here and are visible only through the long-frame attribution (`page:` keys).
//
// The beacon extension (the user 2026-09-18, who wanted the phone's page-load and return timing shared only by
// choice). Two per-browser switches in the gear's store (`romp:settings`, read raw here as the shim and the shell
// scripts read it, so no pane bundle grows by the settings module): SHARE_SETTING adds the fields below to the
// minute row; MUTE_SETTING stops every row this module posts (the shim drops its own rows on the same switch). Both
// are off by default, so a browser with neither posts exactly the row it posted before. The switches are read at
// every flush and on the storage event a save in another document fires, so a change lands within a minute and
// without a reload. Shared fields, numbers and fixed-vocabulary identifiers only: once per page (the first shared
// row) `nav` (the navigation entry's type and three timestamps), `res` (resource timing folded per same-origin
// bundle basename, query stripped, at most MAX_RES then `other`), `marks` (ms from the time origin to the socket
// open, the bundle's ready and the first delivered frame, stamped by the shim on window.__rompPerfMarks, and the
// paint entries); `env` once and again when the pane's own width/height aspect flips (standalone, iOS major version,
// touch, viewport, pixel ratio, the entry types the browser supports from a fixed list, requestIdleCallback, the dist
// token); every row `vis` (visibility transitions and hidden time inside the minute), `wsBytes` (text-frame characters
// the shim received on the pane's LOCAL socket in the minute, from its counter), `wsBytesByHost` (the same unit, per
// REMOTE host by its position on the page, h1 the first remote host this page attached, one key per host the page
// attached, however many, from federation's page-lifetime totals through window.__rompFed.wsBytesByHost and the hosts
// attached at the flush through window.__rompFed.attachedHostOrdinals: a position is on the row when its host is attached
// at the flush or received characters in the minute, so the row closing a detach's minute carries the host and the rows
// after it do not, an attached idle host reads 0, and the key is absent, not null, when no host is attached and none
// received characters, a page that never attached one and the shell included; disjoint from wsBytes: a remote socket's
// characters are counted here and never there; 2026-09-19, the user approved the field as one number per host and no
// content) and `rafGap` (animation-frame gaps over RAF_GAP_MS while visible, from a loop that runs only while the switch
// is on and the document visible). A Performance API the browser lacks reads as null, never a guess. The pending minute also flushes on visibilitychange to hidden: iOS fires that on an
// app switch and then freezes the page, and pagehide, a navigation event, never comes. That flush leaves a held
// slowframe row for its long-frame report (the timer tick and pagehide stay its backstops) and does not re-arm the
// slowframe budget.

export const SLOW_FRAME_MS = 100;      // a frame whose whole handling is at or over this sends a slowframe row
export const LONG_FRAME_MS = 50;       // the browser's own long-frame threshold; entries under it are ignored
export const DROPPED_FRAME_MS = 16.7;  // one frame at 60 Hz: handlers over this drop at least one paint
export const SLOW_ROWS_PER_MINUTE = 5; // slowframe rows sent per pane per timer minute (PerfTelemetry.slowBudget); the rest are counted in the minute row
export const FREE_RING = 64;           // main-thread-free samples kept for the minute's percentiles
export const MAX_FRAME_TYPES = 32;     // distinct wire frame types per minute, the rest fold into "other"; the federation layer's fed:<type> keys have the same cap of their own (fed:other)
export const MAX_TOP = 5;              // attributed keys reported per minute
export const MAX_TOP_KEYS = 64;        // distinct attribution keys tracked per minute; the rest fold into "other"
export const FLUSH_MS = 60_000;
/** Upper edges (exclusive) of the histogram's buckets 0..12; bucket 13 is everything at or over 4096 ms. */
export const HIST_EDGES: readonly number[] = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096];
export const HIST_BUCKETS = HIST_EDGES.length + 1;
// the beacon extension (2026-09-18)
export const SETTINGS_KEY = "romp:settings";   // the gear's store (settings.ts KEY)
export const SHARE_SETTING = "perfShare";      // the store's key for the opt-in: `true` alone turns it on
export const MUTE_SETTING = "perfMute";        // the store's key for the kill switch: `true` alone turns it on
export const RAF_GAP_MS = 50;                  // an animation-frame gap over this counts (one long frame at 60 Hz is three missed paints)
export const MAX_RES = 24;                     // named resource entries per page; the rest fold into "other"
/** The entry types `env.entryTypes` may name, in this order: what the browser supports of the observers this module
 *  and the phone work could use. Anything else the browser lists is left out. */
export const ENV_ENTRY_TYPES: readonly string[] = ["longtask", "long-animation-frame", "event", "largest-contentful-paint", "layout-shift", "paint", "resource", "navigation"];
/** The navigation types `nav.type` may carry; another value reads "other". */
export const NAV_TYPES: readonly string[] = ["navigate", "reload", "back_forward", "prerender"];

export type PerfPost = (m: Record<string, unknown>) => void;
export type UaClass = "chrome-desktop" | "safari-ios" | "other";

/** A PerformanceObserver-shaped constructor: what the module needs of the real one. */
export interface ObserverCtor {
  new (cb: (list: { getEntries(): any[] }) => void): { observe(opts: any): void; disconnect(): void };
}

/** Everything the module reads from the page, injectable so the tests run it on a fake clock. */
export interface PerfDeps {
  now(): number;                     // performance.now(): the handler clock, and the clock long-frame entries carry
  wallNow(): number;                 // Date.now(): stamps the minute
  post: PerfPost | null;             // the clientDiag transport; null keeps measuring and sends nothing
  raf: ((cb: (t: number) => void) => number) | null;
  caf: ((id: number) => void) | null;
  setInterval: ((cb: () => void, ms: number) => unknown) | null;
  observer: ObserverCtor | null;
  supportedEntryTypes: readonly string[];
  heapBytes(): number | null;        // performance.memory.usedJSHeapSize (Chrome); null when absent
  domCount(): number | null;         // document.getElementsByTagName("*").length; null when absent
  visible(): boolean;                // document.visibilityState !== "hidden"
  hiddenPane(): boolean;             // the pane shim's test: the zero-viewport probe (a framed pane the shell has display:none'd) OR the pane's published word (window.__rompPaneHidden, paint-gate.ts; Chromium keeps a hidden iframe's size)
  ua: UaClass;
  pageUrl: string;                   // location.href without query or fragment: an inline script's sourceURL
  windowEvents: EventTarget | null;  // pagehide flushes the minute; resize cancels a free sample when the viewport goes to zero; storage re-reads the switches
  documentEvents: EventTarget | null; // visibilitychange cancels a free-thread sample the hide would inflate, counts the transition, and flushes on hidden
  // the beacon extension (2026-09-18)
  switches(): BeaconSwitches;        // the gear's two per-browser switches, read from the store (readSwitches)
  entries(type: string): any[] | null;   // performance.getEntriesByType(type); null where the API is absent
  marks(): Record<string, unknown> | null;   // window.__rompPerfMarks: the shim's stamps (wsOpen, bundleReady, firstFrame), its wsBytes counter and the dist token dv; null without a shim
  fedBytes(): Record<string, unknown> | null;   // window.__rompFed.wsBytesByHost(): federation's page-lifetime characters per remote host position (h<ordinal>); null without federation, or with a federation bundle before the getter
  fedAttached(): readonly string[] | null;   // window.__rompFed.attachedHostOrdinals(): the positions attached right now; null without federation, or with a bundle before the read (then a position is on the row only for the minute's characters)
  env(): EnvInfo | null;             // the page's environment, read live (envInfo over the window); null where nothing can be read
}

export interface BeaconSwitches { share: boolean; mute: boolean }
export interface NavInfo { type: string; responseEnd: number; domContentLoaded: number; loadEventEnd: number }
export interface ResStat { transferSize: number; encodedBodySize: number; duration: number }
/** What envInfo reads of the page. */
export interface EnvSource {
  standalone: unknown;               // navigator.standalone (iOS: the page runs as an installed app)
  ua: string;
  maxTouchPoints: number;
  vw: number; vh: number;            // innerWidth, innerHeight
  dpr: number;                       // devicePixelRatio
  entryTypes: readonly string[];     // PerformanceObserver.supportedEntryTypes
  ric: boolean;                      // typeof requestIdleCallback === "function"
}
export interface EnvInfo {
  standalone: boolean; iosMajor: number; touch: boolean; vw: number; vh: number; dpr: number;
  entryTypes: string[]; ric: boolean; dv?: number;
}

/** The object every pane, federation and the kernel page's timeline boot reach through window.__rompPerf. */
export interface RompPerf {
  timed<T>(type: string, fn: () => T): T;
  frame<T>(msg: unknown, fn: () => T): T;
  wrapFrameHandler(handler: (e: MessageEvent) => void): (e: MessageEvent) => void;
  snapshot(): Record<string, unknown>;
  tick(): void;
  setPost(post: PerfPost | null): void;
}

// ── pure pieces ─────────────────────────────────────────────────────────────────────────────────────

/** A fixed-capacity ring of numbers: the newest `cap` samples, in arrival order once full. */
export class Ring {
  private buf: number[] = [];
  private at = 0;
  n = 0;                              // samples pushed, beyond the capacity too
  constructor(readonly cap: number) {}
  push(v: number): void {
    if (this.buf.length < this.cap) this.buf.push(v);
    else this.buf[this.at] = v;
    this.at = (this.at + 1) % this.cap;
    this.n++;
  }
  values(): number[] { return this.buf.slice(); }
}

/** Nearest-rank percentile (p in 0..1) over the values; 0 for none. */
export function percentile(vals: readonly number[], p: number): number {
  if (!vals.length) return 0;
  const s = vals.slice().sort((a, b) => a - b);
  const rank = Math.min(s.length, Math.max(1, Math.ceil(p * s.length)));
  return s[rank - 1];
}

/** The histogram bucket a duration falls in: 0 for under 1 ms, 13 for 4096 ms and over. */
export function histBucket(ms: number): number {
  let i = 0;
  while (i < HIST_EDGES.length && ms >= HIST_EDGES[i]) i++;
  return i;
}

/** Nearest-rank quantile of a histogram, as the index of the bucket it lands in; -1 for an empty one.
 *  The bucket's upper edge (HIST_EDGES[i], or "4096 and over" for the last) is the figure to print. */
export function histQuantileBucket(hist: readonly number[], q: number): number {
  let total = 0;
  for (const c of hist) total += c;
  if (!total) return -1;
  const rank = Math.min(total, Math.max(1, Math.ceil(q * total)));
  let cum = 0;
  for (let i = 0; i < hist.length; i++) {
    cum += hist[i];
    if (cum >= rank) return i;
  }
  return hist.length - 1;
}

/** One decimal place; keeps the rows short. */
export function round1(x: number): number { return Math.round(x * 10) / 10; }

/** A code identifier a row may carry: letters, digits, `_ . : -`, at most 32 chars; anything else is "other". */
function ident(s: unknown): string {
  const v = String(s ?? "");
  return /^[A-Za-z0-9_.:-]{1,32}$/.test(v) ? v : "other";
}

function stripQuery(url: string): string {
  const cut = url.search(/[?#]/);
  return cut >= 0 ? url.slice(0, cut) : url;
}

/** The frame-type key a message counts under: its `type`, a raw delta as `delta:<slot>`, a shell message
 *  (`romp:` field, no type) as "shell", anything else as "other". */
export function classifyFrame(m: unknown): string {
  if (!m || typeof m !== "object") return "other";
  const o = m as Record<string, unknown>;
  if (o.type === "delta") return "delta:" + ident(o.slot);
  if (typeof o.type === "string" && o.type) return ident(o.type);
  if (typeof o.romp === "string" && o.romp) return "shell";
  return "other";
}

/** The attribution key of one long-frame script entry: `<script basename>:<function>@<char position>`.
 *  The browser names the top-level callback it invoked, not the hottest function, so most keys are an
 *  anonymous arrow; the character position tells those apart and resolves against the bundle. A script
 *  whose sourceURL is the page itself (an inline script: the pane shim, the shell's boot code) is
 *  `page:<fn>`, never the page path, which would read like a frame type; an empty sourceURL is `unknown:`. */
export function scriptKey(s: { sourceURL?: unknown; sourceFunctionName?: unknown; sourceCharPosition?: unknown }, pageUrl = ""): string {
  const url = stripQuery(String(s.sourceURL ?? ""));
  const fn = (String(s.sourceFunctionName ?? "") || "(anonymous)").slice(0, 48);
  const pos = typeof s.sourceCharPosition === "number" && s.sourceCharPosition >= 0 ? "@" + Math.floor(s.sourceCharPosition) : "";
  if (!url) return "unknown:" + fn + pos;
  const base = url.slice(url.lastIndexOf("/") + 1);
  if ((pageUrl && url === pageUrl) || !base) return "page:" + fn + pos;
  return base.slice(0, 48) + ":" + fn + pos;
}

/** An invoker name reduced to code identifiers: `DIV#tab-web.onclick` becomes `DIV.onclick` (an element id
 *  can embed a session name); `IMG[src=/file?path=...].onload` becomes `IMG[src].onload` (a source URL can
 *  carry a file path); a classic or module script's invoker, which the browser reports as the script's URL
 *  (host, port and dist token included), becomes the script's basename. */
export function sanitizeInvoker(inv: unknown): string {
  let s = String(inv ?? "");
  s = s.replace(/\[src=[^\]]*\]/g, "[src]");
  s = s.replace(/#[^.\s[]*/g, "");
  if (s.includes("://") || s.startsWith("/")) {
    s = stripQuery(s);
    s = s.slice(s.lastIndexOf("/") + 1) || "page";
  }
  return s.slice(0, 64);
}

/** A coarse browser class; iPadOS reports a Macintosh UA and is told apart by its touch points. */
export function uaClass(ua: string, maxTouchPoints = 0): UaClass {
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && maxTouchPoints > 1)) return "safari-ios";
  if (/Chrome\//.test(ua) && !/Mobile|Android/.test(ua)) return "chrome-desktop";
  return "other";
}

// ── the beacon extension's pure pieces ──

/** The gear's two switches as the store holds them: the literal `true` alone turns one on (the store's off-default
 *  idiom, settings.ts loadSettings). A store that cannot be read, or holds anything else, reads both off. */
export function readSwitches(storage: { getItem(k: string): string | null } | null | undefined): BeaconSwitches {
  try {
    const raw = storage ? storage.getItem(SETTINGS_KEY) : null;
    const s = raw ? JSON.parse(raw) : null;
    return { share: !!(s && s[SHARE_SETTING] === true), mute: !!(s && s[MUTE_SETTING] === true) };
  } catch (e) {
    return { share: false, mute: false };
  }
}

/** A whole millisecond from a timing figure; -1 where the browser gave none (a load event that has not fired
 *  reads 0 from the browser, which is a figure). */
function wholeMs(v: unknown): number { return typeof v === "number" && isFinite(v) ? Math.round(v) : -1; }

/** The page's navigation entry as the row carries it; null where the browser recorded none. */
export function navInfo(entries: readonly any[] | null): NavInfo | null {
  const e = entries && entries[0];
  if (!e || typeof e !== "object") return null;
  return { type: NAV_TYPES.indexOf(e.type) >= 0 ? e.type : "other",
           responseEnd: wholeMs(e.responseEnd), domContentLoaded: wholeMs(e.domContentLoadedEventEnd), loadEventEnd: wholeMs(e.loadEventEnd) };
}

const RES_BASENAME = /^[A-Za-z0-9_-]+\.(js|css|woff2?|ttf|otf|svg|png|ico|webmanifest|json)$/;
/** The root files a page fetches by name: the service worker, the app manifest, the browser's own icon request. */
export const RES_ROOT_FILES: readonly string[] = ["sw.js", "manifest.webmanifest", "favicon.ico"];

/** The key a resource entry folds under: the basename of a same-origin asset under /dist/ or /media/ whose
 *  basename is a plain asset name, or one of RES_ROOT_FILES at the root, query and fragment stripped. Everything
 *  else is "other": a cross-origin fetch (a figure host's image is named by the document that embeds it), a
 *  route with a path (a file read carries the path), any other root name, a data: or blob: URL. */
export function resourceKey(name: unknown, origin: string): string {
  const url = stripQuery(String(name ?? ""));
  if (!origin || url.slice(0, origin.length + 1) !== origin + "/") return "other";
  const segs = url.slice(origin.length + 1).split("/");
  const base = segs[segs.length - 1];
  if (segs.length === 1) return RES_ROOT_FILES.indexOf(base) >= 0 ? base : "other";
  if (segs.length === 2 && (segs[0] === "dist" || segs[0] === "media") && RES_BASENAME.test(base)) return base;
  return "other";
}

/** The page's resource entries folded per resourceKey, sizes and durations summed, the MAX_RES largest by encoded
 *  body first and the rest into "other"; null where the browser recorded none. */
export function foldResources(entries: readonly any[] | null, origin: string): Record<string, ResStat> | null {
  if (!entries) return null;
  const by = new Map<string, ResStat>();
  const add = (k: string, e: any) => {
    const cur = by.get(k) || { transferSize: 0, encodedBodySize: 0, duration: 0 };
    cur.transferSize += Math.max(0, wholeMs(e.transferSize));
    cur.encodedBodySize += Math.max(0, wholeMs(e.encodedBodySize));
    cur.duration += Math.max(0, wholeMs(e.duration));
    by.set(k, cur);
  };
  for (const e of entries) if (e && typeof e === "object") add(resourceKey(e.name, origin), e);
  const other = by.get("other");
  by.delete("other");
  const named = [...by.entries()].sort((a, b) => b[1].encodedBodySize - a[1].encodedBodySize);
  const out: Record<string, ResStat> = {};
  let rest: ResStat | null = other || null;
  named.forEach(([k, v], i) => {
    if (i < MAX_RES) { out[k] = v; return; }
    rest = rest || { transferSize: 0, encodedBodySize: 0, duration: 0 };
    rest.transferSize += v.transferSize; rest.encodedBodySize += v.encodedBodySize; rest.duration += v.duration;
  });
  if (rest) out.other = rest;
  return out;
}

/** The page's marks, whole ms from the time origin: the shim's stamps where they are numbers, and the paint
 *  entries' first-paint (fp) and first-contentful-paint (fcp). Only what is known is present. */
export function pageMarks(marks: Record<string, unknown> | null, paints: readonly any[] | null): Record<string, number> {
  const out: Record<string, number> = {};
  for (const k of ["wsOpen", "bundleReady", "firstFrame"]) {
    const v = marks ? marks[k] : undefined;
    if (typeof v === "number" && isFinite(v) && v >= 0) out[k] = Math.round(v);
  }
  if (paints) {
    for (const e of paints) {
      if (!e || typeof e.startTime !== "number") continue;
      if (e.name === "first-paint") out.fp = Math.round(e.startTime);
      else if (e.name === "first-contentful-paint") out.fcp = Math.round(e.startTime);
    }
  }
  return out;
}

/** The iOS major version an iPhone, iPad or iPod user agent states (`OS 17_4`); 0 elsewhere, an iPad with the
 *  desktop Macintosh user agent included (its `touch` tells it apart). */
/** The minute's characters per remote host position (the row's wsBytesByHost) from federation's page-lifetime totals
 *  (`now`, keyed h<ordinal>, the getter's shape; a key off that pattern or a non-numeric value is ignored) against the
 *  minute's baselines (`base`, the same shape, {} where a position had no total when the minute began: a host attached
 *  mid-minute counts from 0), for the positions `attached` at the flush (federation's attachedHostOrdinals; null when
 *  federation cannot say, a bundle before the read). A position is on the row when its host is attached at the flush or
 *  received characters in the minute: the row closing a detach's minute carries the host's characters and the rows after
 *  it carry no key for it, an attached idle host (a down one; an up one hears a keepalive every 10 s) reads 0, and a
 *  position both detached and silent is left off. Every qualifying position keeps its own key, h1, h2 and so on; no cap,
 *  one number per attached host (the owner's decision of 2026-09-19). Null when no position qualifies (no remote host attached at
 *  the flush and none received characters in the minute, a page that never attached one included), and the caller leaves
 *  the key off the row. Pure. */
export function bytesByHost(now: Record<string, unknown> | null, base: Record<string, number>, attached: readonly string[] | null): Record<string, number> | null {
  if (!now || typeof now !== "object") return null;
  const up = new Set(attached || []);
  const ords: number[] = [];
  for (const k of Object.keys(now)) {
    const m = /^h([1-9][0-9]*)$/.exec(k);
    const v = now[k];
    if (m && typeof v === "number" && isFinite(v)) ords.push(Number(m[1]));
  }
  ords.sort((a, b) => a - b);
  const out: Record<string, number> = {};
  for (const o of ords) {
    const k = "h" + o;
    const d = Math.max(0, Math.round((now[k] as number) - (base[k] || 0)));
    if (d <= 0 && !up.has(k)) continue;   // detached at the flush and silent in the minute: no key
    out[k] = d;
  }
  return Object.keys(out).length ? out : null;
}

export function iosMajor(ua: string): number {
  if (!/iPhone|iPad|iPod/.test(ua)) return 0;
  const m = /OS (\d+)_/.exec(ua);
  return m ? Number(m[1]) : 0;
}

export function envInfo(s: EnvSource): EnvInfo {
  return { standalone: s.standalone === true, iosMajor: iosMajor(s.ua), touch: s.maxTouchPoints > 0,
           vw: Math.max(0, wholeMs(s.vw)), vh: Math.max(0, wholeMs(s.vh)), dpr: round1(typeof s.dpr === "number" && isFinite(s.dpr) ? s.dpr : 0),
           entryTypes: ENV_ENTRY_TYPES.filter((t) => s.entryTypes.indexOf(t) >= 0), ric: !!s.ric };
}

/** The viewport class whose change re-sends `env`: the pane's own width/height aspect, landscape (wider than tall) or
 *  portrait. The figures are the pane iframe's innerWidth and innerHeight, not the device's, so a divider drag, a window
 *  resize or a device rotation can flip it. */
export function orientation(vw: number, vh: number): string { return vw > vh ? "landscape" : "portrait"; }

/** The scripts of one long-frame entry as `{k, ms, inv}` rows, summed per key, largest first. */
export function attributeScripts(scripts: any[], pageUrl = ""): { k: string; ms: number; inv: string }[] {
  const by = new Map<string, { k: string; ms: number; inv: string }>();
  for (const s of scripts) {
    if (!s || typeof s.duration !== "number") continue;
    const k = scriptKey(s, pageUrl);
    const cur = by.get(k) || { k, ms: 0, inv: "" };
    cur.ms += s.duration;
    const inv = sanitizeInvoker(s.invoker);
    if (inv) cur.inv = inv;
    by.set(k, cur);
  }
  return [...by.values()].sort((a, b) => b.ms - a.ms).map((r) => ({ k: r.k, ms: round1(r.ms), inv: r.inv }));
}

// ── the collector ───────────────────────────────────────────────────────────────────────────────────

interface TypeStat { n: number; ms_sum: number; ms_max: number; n16: number; n100: number; hist: number[] }
interface TopStat { ms: number; n: number; inv: string }
interface Bucket {
  since: number;                       // wallNow() when the minute began
  active: boolean;                     // a frame arrived or a long frame was observed
  frames: Map<string, TypeStat>;
  free: Ring;
  loaf: { n: number; blocking_ms: number; worst_ms: number; top: Map<string, TopStat> };
  slowSent: number;                    // slowframe rows sent or held in this bucket (the row's slow.sent); the cap's counter is the collector's slowBudget
  slowSuppressed: number;              // slow frames past the cap: counted, not sent
  slowSuppressedWorst: number;
  wireTypes: number;                   // distinct keys in `frames` that are wire types, and fed:<type> keys, for the two caps
  fedTypes: number;
  // the beacon extension: kept every minute, reported only when the share switch is on
  vis: { hiddenN: number; visibleN: number; hiddenMs: number };   // visibility transitions in the minute, and the time hidden inside it
  rafGap: { n: number; worst: number };   // animation-frame gaps over RAF_GAP_MS while visible
  bytes0: number;                      // the shim's wsBytes counter when the minute began
  fedBytes0: Record<string, number>;   // federation's per-position totals (wsBytesByHost) when the minute began; a position absent here counts from 0
}
interface PendingSlow { type: string; ms: number; dom: number | null; t0: number; t1: number }
interface Open { t0: number; child: number }   // a bracket in progress: its start, and the time its inner brackets took
type ObserverKind = "loaf" | "longtask" | "none";

export class PerfTelemetry implements RompPerf {
  private bucket: Bucket;
  private open: Open[] = [];           // the brackets in progress, outermost first
  private freePending = false;
  private freeFrom = 0;
  private rafId = 0;
  private pendingSlow: PendingSlow[] = [];
  private slowBudget = 0;              // slowframe rows sent or held since the timer's last tick: the cap slow() checks. Each bucket books the same rows for its row's `slow`, but a hide flush starts a new bucket inside the timer's minute and must not re-arm the cap (2026-09-18)
  readonly observerKind: ObserverKind = "none";
  // the beacon extension
  private sw: BeaconSwitches = { share: false, mute: false };
  private hiddenAt = -1;               // d.now() when the document went hidden; -1 while visible
  private pageSent = false;            // nav, res and marks have gone out (once per page life)
  private envSent = false;
  private envOrient = "";              // the pane's aspect (orientation()) the last env went out with; a change re-sends it
  private gap = { running: false, id: 0, last: -1 };   // the animation-frame gap loop: on only while share is on and the document visible

  constructor(readonly app: string, private readonly d: PerfDeps) {
    this.bucket = this.newBucket();
    this.observerKind = this.startObserver();
    this.hiddenAt = this.safe(() => d.visible(), true) ? -1 : d.now();
    if (d.setInterval) {
      try {
        const h: any = d.setInterval(() => { try { this.tick(); } catch (e) { /* never into the pane */ } }, FLUSH_MS);
        if (h && typeof h.unref === "function") h.unref();   // a node host must not be kept alive by the flush
      } catch (e) { /* no timer: the minute flushes on the next pagehide only */ }
    }
    try {
      d.windowEvents?.addEventListener("pagehide", () => { try { this.tick(); } catch (e) { /* never into the pane */ } });
      // the shell hides a pane by display:none, which has no event of its own; the iframe's viewport going to
      // zero fires resize, and a sample armed before the hide would otherwise measure the hidden interval. The
      // gap loop drops its baseline on every resize: a pane shown again after display:none gets its callbacks back
      // with the whole hidden stretch as the gap, and the resize runs before the frame's callbacks do.
      d.windowEvents?.addEventListener("resize", () => { try { this.gap.last = -1; if (d.hiddenPane()) this.cancelFree(); } catch (e) { /* ditto */ } });
      d.documentEvents?.addEventListener("visibilitychange", () => { try { this.onVisibility(); } catch (e) { /* ditto */ } });
      // a save in the gear (another document of this browser) fires storage here; the gear's own document fires
      // romp:settings (settings.ts saveSettings, gear.js save)
      d.windowEvents?.addEventListener("storage", (e: any) => { try { if (!e || !e.key || e.key === SETTINGS_KEY) this.refreshSwitches(); } catch (err) { /* ditto */ } });
      d.windowEvents?.addEventListener("romp:settings", () => { try { this.refreshSwitches(); } catch (e) { /* ditto */ } });
    } catch (e) { /* no event hooks */ }
    this.refreshSwitches();
  }

  setPost(post: PerfPost | null): void { this.d.post = post; }

  /** Run fn as the handling of one frame of `type`, timing it. Brackets nest: each level records its OWN
   *  time (its total minus its inner brackets'), so `fed:feed` and `feed` add up to the frame's cost; the
   *  slowframe test and the free-thread sample use the outermost bracket's total. The pane's own exceptions
   *  propagate. */
  timed<T>(type: string, fn: () => T): T {
    const fr: Open = { t0: this.d.now(), child: 0 };
    this.open.push(fr);
    try {
      return fn();
    } finally {
      this.open.pop();
      try {
        const t1 = this.d.now();
        const total = t1 - fr.t0;
        const parent = this.open[this.open.length - 1];
        if (parent) parent.child += total;
        this.record(type, Math.max(0, total - fr.child), total, fr.t0, t1, !parent);
      } catch (e) { /* telemetry never throws into the pane */ }
    }
  }

  frame<T>(msg: unknown, fn: () => T): T { return this.timed(classifyFrame(msg), fn); }

  wrapFrameHandler(handler: (e: MessageEvent) => void): (e: MessageEvent) => void {
    return (e: MessageEvent) => this.frame(e ? e.data : null, () => handler(e));
  }

  /** The minute timer's callback, also run on pagehide: send any slowframe row still waiting for a long-frame report
   *  (none is coming for a frame this old), re-arm the slowframe budget, and flush the minute. The budget is the
   *  timer's minute, not the minute row's: the hide flush (onVisibility) starts a new row without re-arming it, so a
   *  page that hides and returns inside a minute posts one cap's worth of rows, not one per return. The switches are
   *  re-read first, so a save lands within a minute. */
  tick(): void {
    this.refreshSwitches();
    for (const p of this.pendingSlow.splice(0)) this.sendSlow(p, null);
    this.slowBudget = 0;
    this.flush();
  }

  /** Send the minute if anything happened and start the next. tick() and the hide flush share it; the caller has
   *  re-read the switches. A held slowframe row is left alone: it waits for its long-frame report, and the later
   *  report, tick() and pagehide are its backstops. */
  private flush(): void {
    const b = this.bucket;
    this.settleHidden(b);
    // a muted minute builds no row at all: extend() would otherwise spend the once-per-page fields on a row that never leaves
    let sent = false;
    if (b.active && !this.sw.mute) {
      const data = this.minuteData(b);
      if (this.sw.share) this.extend(data, b);
      this.send("minute", data);
      sent = true;
    }
    this.bucket = this.newBucket(sent ? null : b);
  }

  /** The minute in progress, in the row's shape, plus the collector's own state and a derived p90 per type
   *  (`p90_le`: the upper edge of the histogram bucket the p90 lands in; Infinity for the top bucket). */
  snapshot(): Record<string, unknown> {
    const data = this.minuteData(this.bucket);
    const frames = data.frames as Record<string, any>;
    for (const k of Object.keys(frames)) {
      const b = histQuantileBucket(frames[k].hist, 0.9);
      frames[k].p90_le = b < 0 ? null : (b < HIST_EDGES.length ? HIST_EDGES[b] : Infinity);
    }
    return Object.assign(data, {
      active: this.bucket.active, observer: this.observerKind,
      pending_slow: this.pendingSlow.length, free_pending: this.freePending,
      share: this.sw.share, mute: this.sw.mute, gap_running: this.gap.running,
    });
  }

  // ── the beacon extension ──

  /** Re-read the gear's two switches; the gap loop follows the share switch. */
  private refreshSwitches(): void {
    this.sw = this.safe(() => this.d.switches(), { share: false, mute: false });
    if (this.sw.share && !this.sw.mute) this.gapStart(); else this.gapStop();
  }

  /** The document's visibility flipped: count the transition, keep the hidden clock, and on hidden cancel the
   *  free sample, stop the gap loop and FLUSH the minute (iOS fires this on an app switch and then freezes the
   *  page; pagehide never comes, and the minute was lost with it). The flush is flush(), not tick(): it leaves a
   *  held slowframe row for its long-frame report and does not re-arm the slowframe budget, which is the timer's. */
  private onVisibility(): void {
    const now = this.d.now();
    if (!this.d.visible()) {
      this.cancelFree();
      if (this.hiddenAt < 0) { this.bucket.vis.hiddenN++; this.hiddenAt = now; }   // the count and the clock move together: a hide the clock already holds (a page that began hidden) is no transition
      this.gapStop();
      this.refreshSwitches();
      this.flush();
    } else {
      this.bucket.vis.visibleN++;
      if (this.hiddenAt >= 0) { this.bucket.vis.hiddenMs += now - this.hiddenAt; this.hiddenAt = -1; }
      this.gapStart();
    }
  }

  /** At a flush, the hidden stretch so far is the minute's; the clock restarts for the next. */
  private settleHidden(b: Bucket): void {
    if (this.hiddenAt < 0) return;
    const now = this.d.now();
    b.vis.hiddenMs += Math.max(0, now - this.hiddenAt);
    this.hiddenAt = now;
  }

  /** The animation-frame gap loop: one callback per frame, the gap since the last one counted when it is over
   *  RAF_GAP_MS. Runs only while share is on and the document visible (requestAnimationFrame does not run hidden,
   *  and a stretch with no callbacks is not a gap); a pane with no viewport gets no callbacks either, and the
   *  resize its return fires drops the baseline first. A gap marks the minute active: a visible pane that receives
   *  no frames but stutters under the user's scroll is what the loop is for. */
  private gapStart(): void {
    const d = this.d;
    const g = this.gap;
    if (g.running || !d.raf || !this.sw.share || this.sw.mute) return;
    if (!this.safe(() => d.visible(), true)) return;
    g.running = true;
    g.last = -1;
    const step = () => {
      try {
        if (!g.running) return;
        const now = d.now();
        if (g.last >= 0 && !d.hiddenPane()) {
          const gap = now - g.last;
          if (gap > RAF_GAP_MS) {
            const r = this.bucket.rafGap;
            r.n++;
            if (gap > r.worst) r.worst = gap;
            this.bucket.active = true;
          }
        }
        g.last = now;
        g.id = d.raf!(step);
      } catch (e) { g.running = false; g.id = 0; }
    };
    g.id = d.raf(step);
  }

  private gapStop(): void {
    const g = this.gap;
    if (g.running && g.id && this.d.caf) { try { this.d.caf(g.id); } catch (e) { /* nothing to cancel */ } }
    g.running = false;
    g.id = 0;
    g.last = -1;
  }

  /** The origin of the page, for the same-origin test the resource fold makes. */
  private origin(): string {
    const m = /^[A-Za-z][A-Za-z0-9+.-]*:\/\/[^/]+/.exec(this.d.pageUrl || "");
    return m ? m[0] : "";
  }

  /** The shared fields, added to a minute row when the share switch is on. */
  private extend(data: Record<string, unknown>, b: Bucket): void {
    const marks = this.safe(() => this.d.marks(), null);
    if (!this.pageSent) {
      this.pageSent = true;
      data.nav = navInfo(this.safe(() => this.d.entries("navigation"), null));
      data.res = foldResources(this.safe(() => this.d.entries("resource"), null), this.origin());
      data.marks = pageMarks(marks, this.safe(() => this.d.entries("paint"), null));
    }
    const env = this.safe(() => this.d.env(), null);
    const orient = env ? orientation(env.vw, env.vh) : "";
    if (!this.envSent || (env && orient !== this.envOrient)) {
      if (env && marks && typeof marks.dv === "number" && isFinite(marks.dv)) env.dv = Math.round(marks.dv);
      data.env = env;
      this.envSent = true;
      this.envOrient = orient;
    }
    data.vis = { hiddenN: b.vis.hiddenN, visibleN: b.vis.visibleN, hiddenMs: Math.round(b.vis.hiddenMs) };
    const bytes = marks ? marks.wsBytes : undefined;
    data.wsBytes = typeof bytes === "number" && isFinite(bytes) ? Math.max(0, Math.round(bytes - b.bytes0)) : null;
    // per remote host position, the same unit, from federation's page-lifetime totals against this minute's baselines, for
    // the positions attached at the flush or delivered to in the minute; the key is left off when none qualifies
    // (bytesByHost returns null), never written as null
    const byHost = bytesByHost(this.safe(() => this.d.fedBytes(), null), b.fedBytes0, this.safe(() => this.d.fedAttached(), null));
    if (byHost) data.wsBytesByHost = byHost;
    data.rafGap = { n: b.rafGap.n, worst: Math.round(b.rafGap.worst) };
  }

  /** The shim's received-characters counter now; 0 without one. */
  private bytesNow(): number {
    const m = this.safe(() => this.d.marks(), null);
    const v = m ? m.wsBytes : undefined;
    return typeof v === "number" && isFinite(v) ? v : 0;
  }

  /** Federation's per-position totals now (the minute's wsBytesByHost baselines), numeric h<ordinal> entries only; {} without federation. */
  private fedBytesNow(): Record<string, number> {
    const m = this.safe(() => this.d.fedBytes(), null);
    const out: Record<string, number> = {};
    if (m && typeof m === "object") for (const k of Object.keys(m)) { const v = m[k]; if (/^h[1-9][0-9]*$/.test(k) && typeof v === "number" && isFinite(v)) out[k] = v; }
    return out;
  }

  // ── recording ──

  private record(type: string, own: number, total: number, t0: number, t1: number, outermost: boolean): void {
    const b = this.bucket;
    b.active = true;
    // the key the frame is counted under: its type, or the fold key once the minute has its cap of distinct
    // types. Wire types and the federation layer's fed:<type> keys are capped separately (on a kernel page every
    // wire type has both), and the fold changes the key only: a slow frame below still names its wire type.
    const fed = type.startsWith("fed:");
    let key = type;
    let st = b.frames.get(key);
    if (!st) {
      const fold = fed ? "fed:other" : "other";
      if (key !== fold && (fed ? b.fedTypes : b.wireTypes) >= MAX_FRAME_TYPES) { key = fold; st = b.frames.get(key); }
      if (!st) {
        st = { n: 0, ms_sum: 0, ms_max: 0, n16: 0, n100: 0, hist: new Array(HIST_BUCKETS).fill(0) };
        b.frames.set(key, st);
        if (fed) b.fedTypes++; else b.wireTypes++;
      }
    }
    st.n++;
    st.ms_sum += own;
    if (own > st.ms_max) st.ms_max = own;
    if (own > DROPPED_FRAME_MS) st.n16++;
    if (own >= SLOW_FRAME_MS) st.n100++;
    st.hist[histBucket(own)]++;
    if (!outermost) return;
    if (total >= SLOW_FRAME_MS) this.slow(fed ? type.slice(4) : type, total, t0, t1);
    this.scheduleFree(t1);
  }

  /** Two animation frames after the outermost handler: the gap is how long the main thread stayed busy with
   *  the work the handler queued (a deferred render, layout, paint). One sample in flight at a time — frames
   *  landing before it resolves are part of that same busy stretch. Not taken while the document is hidden
   *  or the pane has no viewport: requestAnimationFrame does not run there, and a sample bridging a hide
   *  would measure the hide (the visibilitychange and resize listeners cancel one that was already armed). */
  private scheduleFree(t1: number): void {
    const d = this.d;
    const raf = d.raf;
    if (this.freePending || !raf) return;
    if (!d.visible() || d.hiddenPane()) return;
    this.freePending = true;
    this.freeFrom = t1;
    this.rafId = raf(() => {
      this.rafId = raf(() => {
        this.freePending = false;
        this.rafId = 0;
        try {
          if (d.visible() && !d.hiddenPane()) {
            this.bucket.free.push(d.now() - this.freeFrom);
            this.bucket.active = true;
          }
        } catch (e) { /* never into the pane */ }
      });
    });
  }

  private cancelFree(): void {
    if (this.rafId && this.d.caf) { try { this.d.caf(this.rafId); } catch (e) { /* nothing to cancel */ } }
    this.rafId = 0;
    this.freePending = false;
  }

  private slow(type: string, ms: number, t0: number, t1: number): void {
    const b = this.bucket;
    if (this.slowBudget >= SLOW_ROWS_PER_MINUTE) {
      // a pane that is slow on every frame would post one row per frame; past the cap the frames are counted
      // in the minute row with the worst of them, and the rows already sent are the minute's first. The cap is
      // the budget's, per timer minute; the bucket's own counts book what its row reports and are additive
      // across rows (a hide flush inside the minute splits them over two rows, never counts one twice)
      b.slowSuppressed++;
      if (ms > b.slowSuppressedWorst) b.slowSuppressedWorst = ms;
      return;
    }
    this.slowBudget++;
    b.slowSent++;
    const row: PendingSlow = { type, ms, dom: this.safeDom(), t0, t1 };
    if (this.observerKind !== "loaf") { this.sendSlow(row, null); return; }
    // hold it for the long-frame report that covers this handler; the observer callback attaches the
    // attribution and sends it, a later report that starts after it proves none is coming, and the minute
    // tick is the last backstop. Bounded by the cap above: at most SLOW_ROWS_PER_MINUTE wait at once.
    this.pendingSlow.push(row);
  }

  // ── long frames ──

  private startObserver(): ObserverKind {
    const d = this.d;
    if (!d.observer) return "none";
    let kind: ObserverKind = "none";
    let entryType = "";
    try {
      const types = d.supportedEntryTypes || [];
      if (types.indexOf("long-animation-frame") >= 0) { kind = "loaf"; entryType = "long-animation-frame"; }
      else if (types.indexOf("longtask") >= 0) { kind = "longtask"; entryType = "longtask"; }
      if (kind === "none") return kind;
      const po = new d.observer((list) => {
        try { for (const e of list.getEntries()) this.observeEntry(e); } catch (e) { /* never into the pane */ }
      });
      po.observe({ type: entryType, buffered: false });
      return kind;
    } catch (e) {
      return "none";
    }
  }

  /** One long-animation-frame (or longtask) entry: fold it into the minute, and settle any slowframe row
   *  waiting on it. */
  private observeEntry(e: any): void {
    if (!e || typeof e.duration !== "number" || e.duration < LONG_FRAME_MS) return;
    const start = typeof e.startTime === "number" ? e.startTime : 0;
    const blocking = typeof e.blockingDuration === "number" ? e.blockingDuration : Math.max(0, e.duration - LONG_FRAME_MS);
    const b = this.bucket;
    b.active = true;
    b.loaf.n++;
    b.loaf.blocking_ms += blocking;
    if (e.duration > b.loaf.worst_ms) b.loaf.worst_ms = e.duration;
    const attributed = attributeScripts(Array.isArray(e.scripts) ? e.scripts : [], this.d.pageUrl);
    for (const a of attributed) {
      let key = a.k;
      let t = b.loaf.top.get(key);
      if (!t) {
        if (b.loaf.top.size >= MAX_TOP_KEYS && key !== "other") { key = "other"; t = b.loaf.top.get(key); }
        if (!t) { t = { ms: 0, n: 0, inv: "" }; b.loaf.top.set(key, t); }
      }
      t.ms += a.ms;
      t.n += 1;
      if (a.inv) t.inv = a.inv;
    }
    if (!this.pendingSlow.length) return;
    const end = start + e.duration;
    const keep: PendingSlow[] = [];
    for (const p of this.pendingSlow) {
      if (start <= p.t0 + 1 && end >= p.t1 - 1) {
        this.sendSlow(p, { ms: round1(e.duration), blocking_ms: round1(blocking), top: attributed.slice(0, 3) });
      } else if (start > p.t1) {
        this.sendSlow(p, null);                // a later frame reported first: none is coming for this one
      } else {
        keep.push(p);
      }
    }
    this.pendingSlow = keep;
  }

  /** Test seam: feed synthetic long-frame entries as the observer would. */
  observeEntries(entries: any[]): void { for (const e of entries) this.observeEntry(e); }

  // ── rows ──

  /** A fresh minute. `carry` is the bucket a flush did not send (idle, or muted): its visibility counts and its byte
   *  baselines (the local socket's and each remote host position's) pass on, so `vis`, `wsBytes` and `wsBytesByHost` read
   *  "since this pane's previous row" (a hide that found nothing to send still counts in the row that follows); the
   *  per-minute figures (`since`, `span_ms`, the frames) start over. */
  private newBucket(carry: Bucket | null = null): Bucket {
    return { since: this.d.wallNow(), active: false, frames: new Map(), free: new Ring(FREE_RING),
             loaf: { n: 0, blocking_ms: 0, worst_ms: 0, top: new Map() },
             slowSent: 0, slowSuppressed: 0, slowSuppressedWorst: 0, wireTypes: 0, fedTypes: 0,
             vis: carry ? carry.vis : { hiddenN: 0, visibleN: 0, hiddenMs: 0 }, rafGap: { n: 0, worst: 0 },
             bytes0: carry ? carry.bytes0 : this.bytesNow(), fedBytes0: carry ? carry.fedBytes0 : this.fedBytesNow() };
  }

  private minuteData(b: Bucket): Record<string, unknown> {
    const frames: Record<string, { n: number; ms_sum: number; ms_max: number; n16: number; n100: number; hist: number[] }> = {};
    for (const [k, st] of b.frames) {
      frames[k] = { n: st.n, ms_sum: round1(st.ms_sum), ms_max: round1(st.ms_max), n16: st.n16, n100: st.n100, hist: st.hist.slice() };
    }
    const fv = b.free.values();
    const free = b.free.n
      ? { n: b.free.n, p50: round1(percentile(fv, 0.5)), p90: round1(percentile(fv, 0.9)), max: round1(Math.max(...fv)) }
      : null;
    const top = [...b.loaf.top.entries()]
      .sort((x, y) => y[1].ms - x[1].ms)
      .slice(0, MAX_TOP)
      .map(([k, t]) => ({ k, ms: round1(t.ms), n: t.n, inv: t.inv }));
    const data: Record<string, unknown> = {
      app: this.app, since: b.since, span_ms: Math.max(0, this.d.wallNow() - b.since),
      frames, free,
      loaf: { n: b.loaf.n, blocking_ms: round1(b.loaf.blocking_ms), worst_ms: round1(b.loaf.worst_ms), top, src: this.observerKind },
      slow: { sent: b.slowSent, suppressed: b.slowSuppressed, suppressed_worst_ms: round1(b.slowSuppressedWorst) },
      dom: this.safeDom(), visible: this.safe(() => this.d.visible(), true), hidden_pane: this.safe(() => this.d.hiddenPane(), false),
      ua: this.d.ua,
    };
    const heap = this.safe(() => this.d.heapBytes(), null);
    if (typeof heap === "number") data.heap_mb = round1(heap / 1048576);
    return data;
  }

  private sendSlow(p: PendingSlow, loaf: Record<string, unknown> | null): void {
    const data: Record<string, unknown> = { app: this.app, type: p.type, ms: round1(p.ms), dom: p.dom };
    if (loaf) data.loaf = loaf;
    this.send("slowframe", data);
  }

  private send(what: string, data: Record<string, unknown>): void {
    const post = this.d.post;
    if (!post || this.sw.mute) return;   // the kill switch: measuring goes on (snapshot() still answers), nothing leaves the page
    try { post({ type: "clientDiag", surface: "perf", what, data }); } catch (e) { /* the transport's problem, not the pane's */ }
  }

  private safeDom(): number | null { return this.safe(() => this.d.domCount(), null); }
  private safe<T>(fn: () => T, fallback: T): T { try { return fn(); } catch (e) { return fallback; } }
}

export function createPerfTelemetry(app: string, deps: PerfDeps): PerfTelemetry { return new PerfTelemetry(app, deps); }

// ── the browser singleton ───────────────────────────────────────────────────────────────────────────

function browserDeps(post: PerfPost | null): PerfDeps | null {
  const w: any = window;
  const doc: any = document;
  const perf: any = w.performance;
  if (!perf || typeof perf.now !== "function") return null;   // not a browser this module measures
  const PO: any = typeof w.PerformanceObserver === "function" ? w.PerformanceObserver : null;
  const nav: any = w.navigator || {};
  let pageUrl = "";
  try { pageUrl = stripQuery(String((w.location && w.location.href) || "")); } catch (e) { pageUrl = ""; }
  return {
    now: () => perf.now(),
    wallNow: () => Date.now(),
    post,
    raf: typeof w.requestAnimationFrame === "function" ? (cb) => w.requestAnimationFrame(cb) : null,
    caf: typeof w.cancelAnimationFrame === "function" ? (id) => w.cancelAnimationFrame(id) : null,
    setInterval: typeof w.setInterval === "function" ? (cb, ms) => w.setInterval(cb, ms) : null,
    observer: PO,
    supportedEntryTypes: (PO && Array.isArray(PO.supportedEntryTypes)) ? PO.supportedEntryTypes : [],
    heapBytes: () => { const m = perf.memory; return m && typeof m.usedJSHeapSize === "number" ? m.usedJSHeapSize : null; },
    domCount: () => (doc && typeof doc.getElementsByTagName === "function") ? doc.getElementsByTagName("*").length : null,
    visible: () => !doc || doc.visibilityState !== "hidden",
    hiddenPane: () => { try { return (w.parent !== w && (w.innerWidth === 0 || w.innerHeight === 0)) || w.__rompPaneHidden === true; } catch (e) { return false; } },
    ua: uaClass(String(nav.userAgent || ""), Number(nav.maxTouchPoints) || 0),
    pageUrl,
    windowEvents: typeof w.addEventListener === "function" ? w : null,
    documentEvents: doc && typeof doc.addEventListener === "function" ? doc : null,
    // the beacon extension: the store (window.localStorage can throw in a sandboxed frame: both switches off then),
    // the timeline entries, the shim's marks object and the environment, each read at the moment of the flush
    switches: () => { let st: any = null; try { st = w.localStorage || null; } catch (e) { st = null; } return readSwitches(st); },
    entries: (type) => typeof perf.getEntriesByType === "function" ? perf.getEntriesByType(type) : null,
    marks: () => { const m = w.__rompPerfMarks; return m && typeof m === "object" ? m : null; },
    // federation's per-host totals (federation.ts wsBytesByHost, published on window.__rompFed): null on a page without
    // federation (the shell, VS Code) or with a federation bundle that predates the getter, and the row carries no key
    fedBytes: () => { const f = w.__rompFed; if (!f || typeof f.wsBytesByHost !== "function") return null; const m = f.wsBytesByHost(); return m && typeof m === "object" ? m : null; },
    // the positions attached at the flush (federation.ts attachedHostOrdinals): null on a page without federation or with a
    // bundle before the read, and a position is then on the row only for the minute's characters
    fedAttached: () => { const f = w.__rompFed; if (!f || typeof f.attachedHostOrdinals !== "function") return null; const a = f.attachedHostOrdinals(); return Array.isArray(a) ? a : null; },
    env: () => envInfo({ standalone: nav.standalone, ua: String(nav.userAgent || ""), maxTouchPoints: Number(nav.maxTouchPoints) || 0,
                         vw: Number(w.innerWidth) || 0, vh: Number(w.innerHeight) || 0, dpr: Number(w.devicePixelRatio) || 0,
                         entryTypes: (PO && Array.isArray(PO.supportedEntryTypes)) ? PO.supportedEntryTypes : [],
                         ric: typeof w.requestIdleCallback === "function" }),
  };
}

/** The default transport on a kernel page: federation's outbound (which routes a local message to the shim's
 *  send), else the shim's send itself. A pane passes its own acquireVsCodeApi().postMessage instead, which
 *  is the same path on a kernel page and the extension host's pipe in VS Code. */
function defaultPost(): PerfPost {
  return (m) => {
    const w: any = window;
    const f = w.__rompFed;
    if (f && typeof f.outbound === "function") f.outbound(m);
    else if (typeof w.__rompLocalSend === "function") w.__rompLocalSend(m);
  };
}

/** The page's one collector, created on first call and published as window.__rompPerf; later callers get
 *  the same object (federation.js and the pane bundle each carry a copy of this module, so identity is by
 *  the window slot, not the class). A caller's `post` replaces the transport. Null where nothing can be
 *  measured (no window, no performance.now), and the pane runs exactly as before. */
export function installPerfTelemetry(app: string, opts: { post?: PerfPost } = {}): RompPerf | null {
  try {
    if (typeof window === "undefined" || typeof document === "undefined") return null;
    const w: any = window;
    const existing = w.__rompPerf;
    if (existing && typeof existing.timed === "function") {
      if (opts.post) existing.setPost(opts.post);
      return existing as RompPerf;
    }
    const deps = browserDeps(opts.post || defaultPost());
    if (!deps) return null;
    const p = new PerfTelemetry(app, deps);
    w.__rompPerf = p;
    return p;
  } catch (e) {
    return null;
  }
}

/** The one-line install for a pane: its window "message" handler, timed per frame. */
export function perfFrameHandler(app: string, post: PerfPost | undefined, handler: (e: MessageEvent) => void): (e: MessageEvent) => void {
  const p = installPerfTelemetry(app, post ? { post } : {});
  return p ? p.wrapFrameHandler(handler) : handler;
}
