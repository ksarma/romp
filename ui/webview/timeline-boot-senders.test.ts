// The browser timeline's frame listener hears exactly the senders windowSender hears (2026-09-25). The timeline has two
// hosts: the VS Code webview runs timeline-main.ts, whose frame handler is installed through listenForFrames
// (frame-listener.ts), whose window path drops a message windowSender (window-sender.ts) names foreign; the kernel's
// /timeline page runs the inline boot (kernel.py _TIMELINE_BOOT), a plain script, which spells the same rule inline as
// heardSender at the head of its frame listener. This file pins the two as a pair by behaviour, not by chosen rows: the
// kernel's boot is run as served, once over each receiving window below, and its one window message listener is handed
// a data frame from every sender and origin below; the frame must be drawn exactly when windowSender, reading the same
// window, does not name the sender foreign. So the pair cannot drift apart for any sender the grid can express: a
// window that opened this one, a sibling or child frame, an origin whose text overlaps this one's or drops its port, a
// sourceless post with the opaque origin, a page whose own origin is opaque, a window with no location, a missing event.
// tests/test_timeline_boot_shim.py runs the same boot from the kernel's own suite, over named rows.
// Synthetic world only: loopback and example origins, a placeholder webview id.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import { windowSender } from "./window-sender";

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
  OTHER_ORIGIN, "null", "", undefined, null, ABSENT];

type Booted = { listeners: Array<(e: unknown) => void>; drawn: unknown[]; error: string | null };
/** Runs the boot as a plain script over the receiving window: every free name it reads resolves on that window first
 *  (window, parent, opener, location and the rest), a name the window lacks resolves to a real global (Object, URL),
 *  and a name neither holds reads as undefined. The window gets the few browser names the boot touches at load: the
 *  VS Code host bridge (the browser page's shim provides one), HTMLElement for the DOM helpers, addEventListener. Then
 *  a panel is connected whose update counts the frames drawn. */
function bootOver(w: Win, boot: string): Booted {
  const out: Booted = { listeners: [], drawn: [], error: null };
  const own: any = w;
  Object.defineProperty(own, "window", { value: w, enumerable: false, configurable: true });
  Object.defineProperty(own, "self", { value: w, enumerable: false, configurable: true });
  Object.defineProperty(own, "HTMLElement", { value: function () { /* the DOM helpers' prototype */ }, enumerable: false, configurable: true });
  Object.defineProperty(own, "acquireVsCodeApi", { value: () => ({ postMessage() { /* the host */ } }), enumerable: false, configurable: true });
  Object.defineProperty(own, "addEventListener", { value: (t: string, f: (e: unknown) => void) => { if (t === "message") out.listeners.push(f); },
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

test("the kernel's inline timeline boot draws a frame from exactly the senders windowSender does not name foreign: every receiving window, sender and origin, and a missing event", () => {
  const boot = timelineBoot();
  const bad: string[] = [];
  const classes = new Set<string>();
  let heard = 0, refused = 0;
  for (const w of receivers()) {
    const run = bootOver(w, boot);
    assert.equal(run.error, null, w.name + ": the boot ran");
    assert.equal(run.listeners.length, 1, w.name + ": the boot registers one window message listener");
    const listener = run.listeners[0];
    const deliver = (e: unknown): { n: number; threw: string | null } => {
      const before = run.drawn.length;
      let threw: string | null = null;
      try { listener(e); } catch (x) { threw = String((x as Error)?.message || x); }
      return { n: run.drawn.length - before, threw };
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
        const got = deliver(e);
        if (got.n !== want || got.threw !== null) {
          bad.push(w.name + " / " + who + " / origin " + (origin === ABSENT ? "(no key)" : JSON.stringify(origin)) + ": drawn " + got.n +
                   (got.threw ? " (threw: " + got.threw + ")" : "") + ", windowSender says " + cls);
        }
      }
    }
    for (const missing of [null, undefined]) {
      assert.equal(windowSender(missing, w), "foreign");
      const got = deliver(missing);
      if (got.n !== 0 || got.threw !== null) bad.push(w.name + " / a missing event (" + String(missing) + "): drawn " + got.n + (got.threw ? " (threw: " + got.threw + ")" : ""));
    }
  }
  assert.deepEqual(bad, [], "the inline boot and windowSender disagree:\n" + bad.join("\n"));
  // the grid is no sample of one class: windowSender reads every class over it, and both answers occur many times
  assert.deepEqual([...classes].sort(), ["dispatch", "embedder", "foreign", "peer", "self"], "the grid reaches every class windowSender names");
  assert.ok(heard >= 50 && refused >= 300, "the grid holds many heard and many foreign cases (" + heard + " heard, " + refused + " foreign)");
});
