// The browser timeline's frame listener hears exactly the senders windowSender hears (2026-09-25). The timeline has two
// hosts: the VS Code webview runs timeline-main.ts, whose frame handler is installed through listenForFrames
// (frame-listener.ts), whose window path drops a message windowSender (window-sender.ts) names foreign; the kernel's
// /timeline page runs the inline boot (kernel.py _TIMELINE_BOOT), a plain script, which spells the same rule inline as
// heardSender in front of its frame listener. This file pins the two as a pair by behaviour, not by chosen rows: the
// kernel's boot is run as served, once over each receiving window below, and its one window message listener is handed
// a data frame from every sender and origin below; the frame must be drawn exactly when windowSender, reading the same
// window, does not name the sender foreign. So the pair cannot drift apart for any sender the grid can express: a
// window that opened this one, a sibling or child frame, an origin whose text overlaps this one's or drops its port, a
// sourceless post with the opaque origin, a page whose own origin is opaque, a window with no location, a missing event.
// The grid runs twice: without a performance collector, and with a real one (perf-telemetry.ts) on window.__rompPerf,
// as federation.js publishes it on the kernel's page. Both hosts wrap the frame listener in that collector and run the
// sender check outside the wrapper, so a foreign message is neither drawn nor counted in the page's telemetry.
// tests/test_timeline_boot_shim.py runs the same boot from the kernel's own suite, over named rows.
// Synthetic world only: loopback and example origins, a placeholder webview id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import { windowSender } from "./window-sender";
import { createPerfTelemetry, type PerfDeps, type RompPerf } from "./perf-telemetry";

const ROOT = path.resolve(process.cwd(), "..");   // npm test runs in vscode-extension
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");

/** The inline boot's text: the body of kernel.py's `_TIMELINE_BOOT = """…"""`. The kernel serves the string's value;
 *  with no backslash in the literal, the value is this text character for character. */
function timelineBoot(): string {
  const head = '_TIMELINE_BOOT = """';
  const i = KERNEL.indexOf(head);
  assert.ok(i > 0, "kernel.py defines _TIMELINE_BOOT");
  assert.equal(KERNEL.indexOf(head, i + 1), -1, "one _TIMELINE_BOOT definition");
  const body = KERNEL.slice(i + head.length, KERNEL.indexOf('"""', i + head.length));
  assert.ok(!body.includes("\\"), "no escape in the literal, so the served boot is this text");
  assert.ok(body.includes('window.addEventListener("message",'), "the boot registers a window message listener");
  return body;
}

const ORIGIN = "http://127.0.0.1:1";
const VSCODE_ORIGIN = "vscode-webview://11111111-2222-3333-4444-555555555555";
// another webview's origin: VS Code gives each webview its own, and only this webview's is the host's
const OTHER_VSCODE_ORIGIN = "vscode-webview://aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
const OTHER_ORIGIN = "https://example.invalid";
const ABSENT = Symbol("absent");   // the event carries no such key at all

type Win = { name: string; parent?: unknown; opener?: unknown; top?: unknown; location?: { origin?: string } };
/** A window: its fields first, then hideEdges, so its edges (parent, and the others the helper hides) enumerate as
 *  nothing and a dump of it is its name and serial. */
function win(name: string, fields: Record<string, unknown> = {}): Win {
  const w: any = { name, ...fields };
  if (!("parent" in fields)) w.parent = w;          // a top-level window is its own parent
  if (!("top" in fields)) w.top = w;
  return hideEdges(w);
}
const GRAND = win("the shell's own parent");
const SHELL = win("the romp shell", { parent: GRAND, top: GRAND });
const OPENER = win("a page on another origin that opened this one");
/** The receiving windows: each kind the boot can run in, or that tells a rule apart. */
function receivers(): Win[] {
  return [
    win("a pane framed in the shell, opened by another page", { parent: SHELL, top: GRAND, opener: OPENER, location: { origin: ORIGIN } }),
    win("a top-level page another page opened", { opener: OPENER, location: { origin: ORIGIN } }),
    win("a top-level page no page opened", { opener: null, location: { origin: ORIGIN } }),
    win("a framed page whose own origin is opaque", { parent: SHELL, top: GRAND, opener: OPENER, location: { origin: "null" } }),
    win("a framed page with no location", { parent: SHELL, top: GRAND, opener: OPENER, location: undefined }),
    win("a VS Code webview frame whose parent is the frame itself", { opener: null, location: { origin: VSCODE_ORIGIN } }),
    win("a VS Code webview frame whose parent is deleted", { parent: undefined, top: undefined, opener: null, location: { origin: VSCODE_ORIGIN } }),
  ];
}
/** The senders, relative to the receiving window. */
function sources(w: Win): Array<[string, unknown]> {
  return [
    ["this window", w], ["its parent", w.parent], ["a sibling frame", win("a sibling frame", { parent: w.parent })],
    ["a frame inside it", win("a frame inside it", { parent: w })], ["the page that opened it", w.opener], ["its top window", w.top],
    ["the shell's parent", GRAND], ["a window it does not know", win("a stray window")],
    ["null", null], ["undefined", undefined], ["no source key", ABSENT],
  ];
}
const ORIGINS: unknown[] = [ORIGIN, ORIGIN + "0", "http://127.0.0.1", "https://127.0.0.1:1", "http://127.0.0.1:2", VSCODE_ORIGIN,
  OTHER_VSCODE_ORIGIN, OTHER_ORIGIN, "null", "", undefined, null, ABSENT];

/** A real performance collector (perf-telemetry.ts) on a still clock that posts its rows here: the object federation.js
 *  publishes on window.__rompPerf on the kernel's pages, whose wrapFrameHandler the boot wraps its frame listener in.
 *  `counted` is how many frames the minute in progress holds, over every type. */
function collector(): { perf: RompPerf; counted: () => number; posted: Array<Record<string, any>> } {
  const posted: Array<Record<string, any>> = [];
  const deps: PerfDeps = {
    now: () => 1000, wallNow: () => 1_700_000_000_000, post: (m) => posted.push(m), raf: null, caf: null, setInterval: null,
    observer: null, supportedEntryTypes: [], heapBytes: () => null, domCount: () => null, visible: () => true,
    hiddenPane: () => false, ua: "chrome-desktop", pageUrl: ORIGIN + "/timeline", windowEvents: null, documentEvents: null,
    switches: () => ({ share: false, mute: false }), entries: () => null, marks: () => null, env: () => null,
  };
  const perf = createPerfTelemetry("timeline", deps);
  const counted = (): number => Object.values(perf.snapshot().frames as Record<string, { n: number }>).reduce((a, st) => a + st.n, 0);
  return { perf, counted, posted };
}

type Booted = { listeners: Array<(e: unknown) => void>; registered: Array<(e: unknown) => void>; drawn: unknown[]; error: string | null };
/** Runs the boot as a plain script over the receiving window: every free name it reads resolves on that window first
 *  (window, parent, opener, location and the rest), a name the window lacks resolves to a real global (Object, URL),
 *  and a name neither holds reads as undefined. The window gets the few browser names the boot touches at load: the
 *  VS Code host bridge (the browser page's shim provides one), HTMLElement for the DOM helpers, addEventListener, and,
 *  when given, the page's performance collector (window.__rompPerf) and federation's frame registry (window.__rompFed,
 *  whose onFrame keeps what the boot registers). Then a panel is connected whose update counts the frames drawn. */
function bootOver(w: Win, boot: string, perf?: RompPerf, fed?: boolean): Booted {
  const out: Booted = { listeners: [], registered: [], drawn: [], error: null };
  const own: any = w;
  Object.defineProperty(own, "window", { value: w, enumerable: false, configurable: true });
  Object.defineProperty(own, "self", { value: w, enumerable: false, configurable: true });
  Object.defineProperty(own, "HTMLElement", { value: function () { /* the DOM helpers' prototype */ }, enumerable: false, configurable: true });
  Object.defineProperty(own, "acquireVsCodeApi", { value: () => ({ postMessage() { /* the host */ } }), enumerable: false, configurable: true });
  Object.defineProperty(own, "addEventListener", { value: (t: string, f: (e: unknown) => void) => { if (t === "message") out.listeners.push(f); },
    enumerable: false, configurable: true });
  if (perf) Object.defineProperty(own, "__rompPerf", { value: perf, enumerable: false, configurable: true });
  if (fed) Object.defineProperty(own, "__rompFed", { value: { onFrame: (f: (e: unknown) => void) => { out.registered.push(f); } },
    enumerable: false, configurable: true });
  const scope = new Proxy(own, {
    has: (t, k) => typeof k === "string" && (k in t || !(k in globalThis)),
    get: (t, k) => (typeof k === "string" && k in t ? t[k] : undefined),
  });
  try {
    new Function("__scope", "with (__scope) {\n" + boot + "\n}")(scope);
    own.__rompConnectTimeline({ update: (d: unknown) => out.drawn.push(d) });
  } catch (x) {
    out.error = String((x as Error)?.message || x);
  }
  return out;
}

test("the stand-ins inspect as their primitives: every enumerable key of each window holds a primitive", () => {
  const all: object[] = [GRAND, SHELL, OPENER, ...receivers()];
  for (const w of receivers()) all.push(...sources(w).map(([, s]) => s).filter((s): s is object => typeof s === "object" && s !== null));
  for (const o of all) for (const k of Object.keys(o)) assert.ok(staysEnumerable((o as any)[k]), k + " is enumerable and holds a " + typeof (o as any)[k]);
});

/** Runs the boot over every receiving window and hands its window listener a data frame from every sender and origin,
 *  and a missing event. With `withCollector`, each boot gets a fresh real collector, and every delivery must add to its
 *  count exactly what it adds to the frames drawn. Returns each disagreement with windowSender, and the tallies. */
function runGrid(boot: string, withCollector: boolean): { bad: string[]; classes: Set<string>; heard: number; refused: number; counted: number } {
  const bad: string[] = [];
  const classes = new Set<string>();
  let heard = 0, refused = 0, countedAll = 0;
  for (const w of receivers()) {
    const c = withCollector ? collector() : null;
    const run = bootOver(w, boot, c ? c.perf : undefined);
    assert.equal(run.error, null, w.name + ": the boot ran");
    assert.equal(run.listeners.length, 1, w.name + ": the boot registers one window message listener");
    const listener = run.listeners[0];
    const deliver = (e: unknown): { n: number; counted: number; threw: string | null } => {
      const before = run.drawn.length, countedBefore = c ? c.counted() : 0;
      let threw: string | null = null;
      try { listener(e); } catch (x) { threw = String((x as Error)?.message || x); }
      return { n: run.drawn.length - before, counted: c ? c.counted() - countedBefore : 0, threw };
    };
    const judge = (label: string, got: { n: number; counted: number; threw: string | null }, want: number, cls: string) => {
      const wantCounted = c ? want : 0;
      countedAll += got.counted;
      if (got.n !== want || got.counted !== wantCounted || got.threw !== null) {
        bad.push(w.name + " / " + label + ": drawn " + got.n + (c ? ", counted " + got.counted : "") +
                 (got.threw ? " (threw: " + got.threw + ")" : "") + ", windowSender says " + cls);
      }
    };
    for (const [who, src] of sources(w)) {
      for (const origin of ORIGINS) {
        const e: Record<string, unknown> = { data: { type: "data", data: { from: who } } };
        if (src !== ABSENT) e.source = src;
        if (origin !== ABSENT) e.origin = origin;
        const cls = windowSender(e, w);
        classes.add(cls);
        const want = cls === "foreign" ? 0 : 1;
        if (want) heard++; else refused++;
        judge(who + " / origin " + (origin === ABSENT ? "(no key)" : JSON.stringify(origin)), deliver(e), want, cls);
      }
    }
    for (const missing of [null, undefined]) {
      assert.equal(windowSender(missing, w), "foreign");
      judge("a missing event (" + String(missing) + ")", deliver(missing), 0, "foreign");
    }
  }
  return { bad, classes, heard, refused, counted: countedAll };
}

test("the kernel's inline timeline boot draws a frame from exactly the senders windowSender does not name foreign: every receiving window, sender and origin, and a missing event", () => {
  const { bad, classes, heard, refused } = runGrid(timelineBoot(), false);
  assert.deepEqual(bad, [], "the inline boot and windowSender disagree:\n" + bad.join("\n"));
  // the grid is no sample of one class: windowSender reads every class over it, and both answers occur many times
  assert.deepEqual([...classes].sort(), ["dispatch", "embedder", "foreign", "peer", "self"], "the grid reaches every class windowSender names");
  assert.ok(heard >= 50 && refused >= 300, "the grid holds many heard and many foreign cases (" + heard + " heard, " + refused + " foreign)");
});

test("with the page's performance collector on window.__rompPerf, the boot draws and counts a frame from exactly the senders windowSender does not name foreign: the check runs outside the collector's wrapper", () => {
  const { bad, heard, refused, counted } = runGrid(timelineBoot(), true);
  assert.deepEqual(bad, [], "with a collector, the inline boot draws or counts a frame windowSender does not hear (or misses one it does):\n" + bad.join("\n"));
  assert.ok(heard >= 50 && refused >= 300, heard + " heard, " + refused + " foreign");
  assert.equal(counted, heard, "the collector counted every heard frame once, and nothing else");
});

// The grid above holds the boot to windowSender, whatever windowSender says; this leg holds both to the answer for one
// case outright: in a VS Code webview frame, a post from another webview's origin is drawn from no sender but the frame
// itself (heard as itself, whatever the origin), while the same senders on this webview's origin are drawn.
test("in a VS Code webview frame, a post from another webview's origin draws nothing from any sender but the frame itself", () => {
  const vscode = receivers().filter((w) => w.location && w.location.origin === VSCODE_ORIGIN);
  assert.equal(vscode.length, 2, "both VS Code frames: window.parent replaced by the frame, and deleted");
  for (const w of vscode) {
    const run = bootOver(w, timelineBoot());
    assert.equal(run.error, null, w.name + ": the boot ran");
    const listener = run.listeners[0];
    const drawnFrom = (origin: string): string[] => {
      const before = run.drawn.length;
      for (const [who, src] of sources(w)) {
        if (src === w) continue;   // this window: self, heard by what it is
        const e: Record<string, unknown> = { origin, data: { type: "data", data: { from: who } } };
        if (src !== ABSENT) e.source = src;
        assert.equal(windowSender(e, w), "foreign", w.name + " / " + who + " on another webview's origin: windowSender");
        listener(e);
      }
      return run.drawn.slice(before).map((d) => (d as { from: string }).from);
    };
    assert.deepEqual(drawnFrom(OTHER_VSCODE_ORIGIN), [], w.name + ": nothing drawn from another webview's origin");
    const stray = win("a window on this webview's origin");
    listener({ source: stray, origin: VSCODE_ORIGIN, data: { type: "data", data: { from: "this webview's origin" } } });
    assert.deepEqual(run.drawn.map((d) => (d as { from: string }).from), ["this webview's origin"], w.name + ": this webview's origin is drawn");
  }
});

test("a foreign window's posts add no frame type to the timeline page's telemetry, and the page's own frames keep their type", () => {
  // the collector keeps MAX_FRAME_TYPES wire types a minute and folds the rest into "other": posts from a foreign window,
  // each naming a type of its own, would crowd the page's real frames out of the minute's row if the collector saw them
  const w = receivers()[0];
  const c = collector();
  const run = bootOver(w, timelineBoot(), c.perf);
  assert.equal(run.error, null);
  const listener = run.listeners[0];
  const stranger = win("a window on another origin");
  const FOREIGN: Array<[string, unknown, string]> = [
    ["a window on another origin", stranger, OTHER_ORIGIN], ["a sandboxed frame", stranger, "null"], ["a sandboxed frame that is gone", null, "null"],
  ];
  for (const [who, source, origin] of FOREIGN) {
    for (let k = 0; k < 40; k++) {
      assert.equal(windowSender({ source, origin }, w), "foreign", who);
      listener({ source, origin, data: { type: "junk_" + k + "_x", from: who } });
    }
  }
  listener({ source: null, origin: "", data: { type: "data", data: { from: "the page's own dispatch" } } });
  assert.deepEqual(run.drawn, [{ from: "the page's own dispatch" }], "the page's own frame is drawn, no foreign post is");
  const frames = c.perf.snapshot().frames as Record<string, { n: number }>;
  assert.deepEqual(Object.keys(frames), ["data"], "the minute holds the page's own frame type alone");
  assert.equal(frames.data.n, 1);
  c.perf.tick();
  const rows = c.posted.filter((m) => m.what === "minute");
  assert.equal(rows.length, 1, "the minute's row was posted");
  assert.deepEqual(Object.keys(rows[0].data.frames), ["data"], "the posted row counts the page's frame under its own type");
});

test("federation's frame registry gets the wrapped frame listener itself, not the window's sender check: a frame it hands over directly is drawn and counted once", () => {
  const w = receivers()[0];
  const c = collector();
  const run = bootOver(w, timelineBoot(), c.perf, true);
  assert.equal(run.error, null);
  assert.equal(run.listeners.length, 1);
  assert.equal(run.registered.length, 1, "the boot registers one listener with federation");
  assert.notEqual(run.registered[0], run.listeners[0], "the registry holds the listener, the window holds the check in front of it");
  // federation.js builds this MessageEvent itself (federation.ts emit): no source, no origin
  run.registered[0]({ data: { type: "data", data: { from: "federation" } } });
  assert.deepEqual(run.drawn, [{ from: "federation" }]);
  assert.equal(c.counted(), 1, "timed by the collector on the registry path too");
});
