// Browser-side performance telemetry for the dashboard panes (2026-09-06). The kernel's own counters
// (`romp perf`, GET /perf) say what the kernel spent; nothing said what the BROWSER spent on the frames it
// received, so a dashboard that felt slow could not be attributed to a pane, a frame type or a function.
// Every pane bundle installs this module and wraps its window "message" handler; the module measures each
// frame's synchronous handling time, how long the main thread stays busy after the handler (two
// requestAnimationFrame callbacks later), and the browser's own long-animation-frame reports with their
// script attribution. Once a minute it folds all of that into ONE clientDiag row (surface "perf", what
// "minute") on the channel the panes already use for breadcrumbs, so the kernel appends it to
// client-diag.jsonl beside the shim's wsclose rows, and `romp perf client` reads it back. A frame whose
// handler ran 100 ms or more also sends a "slowframe" row at once, carrying the long-frame attribution
// when the browser reports one for that frame.
//
// Rows carry numbers and code identifiers only: frame type strings, script file basenames, function names
// and invoker names with any element id stripped. Never card text, session names or transcript content.
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
// raw delta can still appear; those count as `delta:<slot>`.

export const SLOW_FRAME_MS = 100;      // a handler at or over this sends a slowframe row at once
export const LONG_FRAME_MS = 50;       // the browser's own long-frame threshold; entries under it are ignored
export const RING_CAPACITY = 64;       // per-type handler durations kept for the minute's p90
export const MAX_FRAME_TYPES = 24;     // distinct frame-type keys per minute; the rest fold into "other"
export const MAX_TOP = 5;              // attributed (file:function) entries reported per minute
export const MAX_TOP_KEYS = 64;        // distinct attribution keys tracked per minute; the rest fold into "other"
export const MAX_PENDING_SLOW = 8;     // slowframe rows waiting for their long-frame report
export const FLUSH_MS = 60_000;

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
  hiddenPane(): boolean;             // the shim's zero-viewport test: a framed pane the shell has display:none'd
  ua: UaClass;
  windowEvents: EventTarget | null;  // pagehide flushes the minute in progress
  documentEvents: EventTarget | null; // visibilitychange cancels a free-thread sample the hide would inflate
}

/** The object every pane and the timeline view reach through window.__rompPerf. */
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
  n = 0;                              // samples pushed since the last reset, beyond the capacity too
  constructor(readonly cap: number) {}
  push(v: number): void {
    if (this.buf.length < this.cap) this.buf.push(v);
    else this.buf[this.at] = v;
    this.at = (this.at + 1) % this.cap;
    this.n++;
  }
  values(): number[] { return this.buf.slice(); }
  reset(): void { this.buf = []; this.at = 0; this.n = 0; }
}

/** Nearest-rank percentile (p in 0..1) over the values; 0 for none. */
export function percentile(vals: readonly number[], p: number): number {
  if (!vals.length) return 0;
  const s = vals.slice().sort((a, b) => a - b);
  const rank = Math.min(s.length, Math.max(1, Math.ceil(p * s.length)));
  return s[rank - 1];
}

/** One decimal place; keeps the rows short. */
export function round1(x: number): number { return Math.round(x * 10) / 10; }

/** A code identifier a row may carry: letters, digits, `_ . : -`, at most 32 chars; anything else is "other". */
function ident(s: unknown): string {
  const v = String(s ?? "");
  return /^[A-Za-z0-9_.:-]{1,32}$/.test(v) ? v : "other";
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

/** `<script basename>:<function>` for a long-frame script entry; the query string and path go, an inline
 *  script is "inline", an anonymous function is "(anonymous)". */
export function scriptKey(s: { sourceURL?: unknown; sourceFunctionName?: unknown }): string {
  let url = String(s.sourceURL ?? "");
  const cut = url.search(/[?#]/);
  if (cut >= 0) url = url.slice(0, cut);
  const base = url.slice(url.lastIndexOf("/") + 1) || (url ? "other" : "inline");
  const fn = String(s.sourceFunctionName ?? "") || "(anonymous)";
  return base.slice(0, 48) + ":" + fn.slice(0, 48);
}

/** An invoker name with every `#id` fragment removed: `DIV#tab-web.onclick` becomes `DIV.onclick`, so an
 *  element id that embeds a session name never reaches a row. */
export function sanitizeInvoker(inv: unknown): string {
  return String(inv ?? "").replace(/#[^.\s]*/g, "").slice(0, 64);
}

/** A coarse browser class; iPadOS reports a Macintosh UA and is told apart by its touch points. */
export function uaClass(ua: string, maxTouchPoints = 0): UaClass {
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && maxTouchPoints > 1)) return "safari-ios";
  if (/Chrome\//.test(ua) && !/Mobile|Android/.test(ua)) return "chrome-desktop";
  return "other";
}

// ── the collector ───────────────────────────────────────────────────────────────────────────────────

interface TypeStat { n: number; ms_sum: number; ms_max: number; ring: Ring }
interface TopStat { ms: number; n: number; inv: string }
interface Bucket {
  since: number;                       // wallNow() when the minute began
  active: boolean;                     // a frame arrived or a long frame was observed
  frames: Map<string, TypeStat>;
  free: Ring;
  loaf: { n: number; blocking_ms: number; worst_ms: number; top: Map<string, TopStat> };
}
interface PendingSlow { type: string; ms: number; dom: number | null; t0: number; t1: number }
type ObserverKind = "loaf" | "longtask" | "none";

export class PerfTelemetry implements RompPerf {
  private bucket: Bucket;
  private depth = 0;                   // a timed() inside a timed() is the outer bracket's time, not a second frame
  private freePending = false;
  private freeFrom = 0;
  private rafId = 0;
  private pendingSlow: PendingSlow[] = [];
  readonly observerKind: ObserverKind = "none";

  constructor(readonly app: string, private readonly d: PerfDeps) {
    this.bucket = this.newBucket();
    this.observerKind = this.startObserver();
    if (d.setInterval) {
      try {
        const h: any = d.setInterval(() => { try { this.tick(); } catch (e) { /* never into the pane */ } }, FLUSH_MS);
        if (h && typeof h.unref === "function") h.unref();   // a node host must not be kept alive by the flush
      } catch (e) { /* no timer: the minute flushes on the next pagehide only */ }
    }
    try {
      d.windowEvents?.addEventListener("pagehide", () => { try { this.tick(); } catch (e) { /* never into the pane */ } });
      d.documentEvents?.addEventListener("visibilitychange", () => { try { if (!d.visible()) this.cancelFree(); } catch (e) { /* ditto */ } });
    } catch (e) { /* no event hooks */ }
  }

  setPost(post: PerfPost | null): void { this.d.post = post; }

  /** Run fn as the handling of one frame of `type`, timing it. The pane's own exceptions propagate. */
  timed<T>(type: string, fn: () => T): T {
    if (this.depth > 0) return fn();
    this.depth++;
    const t0 = this.d.now();
    try {
      return fn();
    } finally {
      this.depth--;
      try { this.record(type, t0, this.d.now()); } catch (e) { /* telemetry never throws into the pane */ }
    }
  }

  frame<T>(msg: unknown, fn: () => T): T { return this.timed(classifyFrame(msg), fn); }

  wrapFrameHandler(handler: (e: MessageEvent) => void): (e: MessageEvent) => void {
    return (e: MessageEvent) => this.frame(e ? e.data : null, () => handler(e));
  }

  /** The minute timer's callback, also run on pagehide: send the minute if anything happened, start the next. */
  tick(): void {
    // slowframe rows still waiting for a long-frame report: no report is coming for a frame this old
    for (const p of this.pendingSlow.splice(0)) this.sendSlow(p, null);
    if (this.bucket.active) this.send("minute", this.minuteData(this.bucket));
    this.bucket = this.newBucket();
  }

  /** The minute in progress, in the row's shape, plus the collector's own state. */
  snapshot(): Record<string, unknown> {
    return Object.assign(this.minuteData(this.bucket), {
      active: this.bucket.active, observer: this.observerKind,
      pending_slow: this.pendingSlow.length, free_pending: this.freePending,
    });
  }

  // ── recording ──

  private record(type: string, t0: number, t1: number): void {
    const ms = t1 - t0;
    const b = this.bucket;
    b.active = true;
    let st = b.frames.get(type);
    if (!st) {
      if (b.frames.size >= MAX_FRAME_TYPES && type !== "other") { type = "other"; st = b.frames.get(type); }
      if (!st) { st = { n: 0, ms_sum: 0, ms_max: 0, ring: new Ring(RING_CAPACITY) }; b.frames.set(type, st); }
    }
    st.n++;
    st.ms_sum += ms;
    if (ms > st.ms_max) st.ms_max = ms;
    st.ring.push(ms);
    if (ms >= SLOW_FRAME_MS) this.slow(type, ms, t0, t1);
    this.scheduleFree(t1);
  }

  /** Two animation frames after the handler: the gap is how long the main thread stayed busy with the
   *  work the handler queued (a deferred render, layout, paint). One sample in flight at a time — frames
   *  landing before it resolves are part of that same busy stretch. Not taken while the document is hidden
   *  or the pane has no viewport: requestAnimationFrame does not run there, and a sample bridging a hide
   *  would measure the hide. */
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
    const row: PendingSlow = { type, ms, dom: this.safeDom(), t0, t1 };
    if (this.observerKind !== "loaf") { this.sendSlow(row, null); return; }
    // hold it for the long-frame report that covers this handler; the observer callback attaches the
    // attribution and sends it, a later report that starts after it proves none is coming, and the minute
    // tick is the last backstop
    if (this.pendingSlow.length >= MAX_PENDING_SLOW) this.sendSlow(this.pendingSlow.shift()!, null);
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
   *  waiting on it. Exported through observeEntries for the tests. */
  private observeEntry(e: any): void {
    if (!e || typeof e.duration !== "number" || e.duration < LONG_FRAME_MS) return;
    const start = typeof e.startTime === "number" ? e.startTime : 0;
    const blocking = typeof e.blockingDuration === "number" ? e.blockingDuration : Math.max(0, e.duration - LONG_FRAME_MS);
    const b = this.bucket;
    b.active = true;
    b.loaf.n++;
    b.loaf.blocking_ms += blocking;
    if (e.duration > b.loaf.worst_ms) b.loaf.worst_ms = e.duration;
    const attributed = attributeScripts(Array.isArray(e.scripts) ? e.scripts : []);
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

  private newBucket(): Bucket {
    return { since: this.d.wallNow(), active: false, frames: new Map(), free: new Ring(RING_CAPACITY),
             loaf: { n: 0, blocking_ms: 0, worst_ms: 0, top: new Map() } };
  }

  private minuteData(b: Bucket): Record<string, unknown> {
    const frames: Record<string, { n: number; ms_sum: number; ms_max: number; p90: number }> = {};
    for (const [k, st] of b.frames) {
      frames[k] = { n: st.n, ms_sum: round1(st.ms_sum), ms_max: round1(st.ms_max), p90: round1(percentile(st.ring.values(), 0.9)) };
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
    if (!post) return;
    try { post({ type: "clientDiag", surface: "perf", what, data }); } catch (e) { /* the transport's problem, not the pane's */ }
  }

  private safeDom(): number | null { return this.safe(() => this.d.domCount(), null); }
  private safe<T>(fn: () => T, fallback: T): T { try { return fn(); } catch (e) { return fallback; } }
}

/** The scripts of one long-frame entry as `{k, ms, inv}` rows, summed per key, largest first. */
export function attributeScripts(scripts: any[]): { k: string; ms: number; inv: string }[] {
  const by = new Map<string, { k: string; ms: number; inv: string }>();
  for (const s of scripts) {
    if (!s || typeof s.duration !== "number") continue;
    const k = scriptKey(s);
    const cur = by.get(k) || { k, ms: 0, inv: "" };
    cur.ms += s.duration;
    const inv = sanitizeInvoker(s.invoker);
    if (inv) cur.inv = inv;
    by.set(k, cur);
  }
  return [...by.values()].sort((a, b) => b.ms - a.ms).map((r) => ({ k: r.k, ms: round1(r.ms), inv: r.inv }));
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
    hiddenPane: () => { try { return w.parent !== w && (w.innerWidth === 0 || w.innerHeight === 0); } catch (e) { return false; } },
    ua: uaClass(String(nav.userAgent || ""), Number(nav.maxTouchPoints) || 0),
    windowEvents: typeof w.addEventListener === "function" ? w : null,
    documentEvents: doc && typeof doc.addEventListener === "function" ? doc : null,
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
