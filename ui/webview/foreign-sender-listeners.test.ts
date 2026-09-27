// Every window "message" listener in the webview bundles ignores a message from a foreign sender (window-sender.ts): a
// window that is not this document, not its embedder (the romp shell), not on this document's origin, and not this
// document's own dispatch of a kernel frame. The chat's frame handler got that check first (chat-foreign-frame.test.ts);
// this file holds it for the rest of the population:
//   - frame-listener.ts listenForFrames, the one window install every pane's frame handler shares (the feed, the Outline,
//     Waiting on you, the chat and the VS Code timeline): the window path hands the handler no message from a foreign
//     sender. The federation registry path is unchanged: only federation.js calls it, with a MessageEvent it built.
//   - every other window listener, each with its own check at its head: the Waiting pane's panes cache, the VS Code
//     settings sync, the shared file viewer's two (its viewFile relay, and the way back from a failed svg picture, which
//     runs the fetch again on hostUp and sends a probe of the picture's address on any other kernel message), the file
//     browser, the file-comments panel's replies, the gear's six listeners, the shell palette's two, and the VS Code
//     strip's.
// Each listener hears every class windowSender does not name foreign, which covers each one's real senders: the shell
// (the embedder of a pane; to the shell's own page, its panes are windows on its origin), this document (self), a window
// on the origin (a second chat column, a pane posting up to the shell, the VS Code webview host, which posts from its own
// window on the webview's origin) and this document's dispatch (the pane shim's and federation.js's kernel frames).
//
// Executed legs: every listener is run against the same senders. Four run as installed, over a stand-in window: the real
// listenForFrames, installSettingsSync, initFileView and initFileBrowse, each with that stand-in as the global window
// (which is also the window windowSender reads by default). The rest live inside modules that boot a page on import (the
// Waiting pane, the shell palette), behind module state (the comments panel's live panel) or inside a closure (the gear,
// the strip, the file viewer's way back), so each is lifted out of its file by the TypeScript parser, from its function to
// its closing brace, transpiled and run over stubs: every free identifier it reads is an inert stub except the effect it
// is tested for, which counts, windowSender, which is the real helper, and window, which is the stand-in the helper reads.
// A representative arm per listener reaches its effect once from every heard sender and never from a foreign one (the
// way back has a leg per arm: hostUp, and the probe); the head check sits before every arm, which the census below pins
// at source for every listener in ui/.
//
// The census reads the population instead of a list: every addEventListener("message", …) call in a ui/ source file
// (tests excluded), the method named or a computed member, and every onmessage handler assigned to the window (by window,
// self, globalThis or the bare global), must take the event as its one parameter, with no default, open with the check,
// preceded by nothing but reads of the message, and be one of the gated sites below, each with an executed leg here. A
// listener handed over by name is read at the function written in place that a const of that name holds, found by the
// name's binding; any other name fails. A new
// window listener anywhere in ui/ fails it until it is gated and given a leg. A second census reads what the name
// windowSender is bound to: in every ui/ file that calls the check, it is the helper's own import (gear.js: its require),
// bound once and never written, so a local helper of the same name that lets one more sender through cannot stand in for
// it. The first census reads the listeners the source spells, so two more hold the source to spellings it can read: a
// third holds that every addEventListener in ui/ is a call the first can read, and a fourth refuses the roads that spell
// neither (a method of the window or of a prototype read by a computed name, a function run with the window as its
// `this`, an onmessage handler set other than by assignment, code run from a string). What those cannot see is listed at
// the fourth. Synthetic world only: the notes-api demo, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { hideEdges, staysEnumerable, defineHidden } from "../test-dom-shim";
import { windowSender } from "./window-sender";
import { listenForFrames } from "./frame-listener";
import { installSettingsSync } from "./settings";
import { initFileView } from "./file-view";
import { initFileBrowse } from "./file-browse";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));   // esbuild and typescript from the extension
const UI = path.resolve(EXT, "..", "ui");
const ts = requireCjs("typescript");

const SID = "11111111-2222-3333-4444-555555555555";
const ORIGIN = "http://127.0.0.1:1";
const VSCODE_ORIGIN = "vscode-webview://11111111-2222-3333-4444-555555555555";
// another webview's origin: VS Code gives each webview its own, and only this webview's is the host's
const OTHER_VSCODE_ORIGIN = "vscode-webview://aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
const OTHER_ORIGIN = "https://example.invalid";

type Listener = (e: unknown) => void;
/** A receiving window: what windowSender reads (its parent, its location's origin), the target a listener under test is
 *  added to, and the methods those listeners call on window. Its edges and every object it holds are non-enumerable
 *  (hideEdges), so a dump of it is its name and serial. */
class Receiver {
  parent: unknown;
  location: { origin: string };
  listeners: Array<[string, Listener]> = [];
  dispatched: string[] = [];
  constructor(public name: string, parent: unknown, origin: string) {
    this.parent = parent;
    this.location = { origin };
    hideEdges(this);
  }
  addEventListener(type: string, fn: Listener): void { this.listeners.push([type, fn]); }
  dispatchEvent(ev: { type: string }): boolean { this.dispatched.push(ev.type); return true; }
  messageListeners(): Listener[] { return this.listeners.filter(([t]) => t === "message").map(([, f]) => f); }
}
type Ctx = "pane" | "shell" | "vscode" | "vscode, older";
const SHELL = hideEdges({ name: "the romp shell" });
/** A fresh receiving window of each kind: a pane in the romp shell (its parent is the shell), the shell's own top-level
 *  page (its parent is itself), and VS Code's webview frame, whose script sets window.parent to the frame itself (1.103 on)
 *  or deletes it (1.88 to 1.102). */
function receiver(ctx: Ctx): Receiver {
  if (ctx === "pane") return new Receiver("a pane in the romp shell", SHELL, ORIGIN);
  if (ctx === "shell") { const w = new Receiver("the romp shell's page", null, ORIGIN); w.parent = w; return w; }
  if (ctx === "vscode") { const w = new Receiver("a VS Code webview frame", null, VSCODE_ORIGIN); w.parent = w; return w; }
  return new Receiver("a VS Code webview frame, window.parent deleted", undefined, VSCODE_ORIGIN);
}
const SECOND_COLUMN = hideEdges({ name: "a second chat column" });
const CHILD_PANE = hideEdges({ name: "a pane of the shell" });
const VSCODE_HOST = hideEdges({ name: "the VS Code webview host" });
const OTHER_PAGE = hideEdges({ name: "a page on another origin" });
const OTHER_WEBVIEW = hideEdges({ name: "a window on another VS Code webview's origin" });
const sandboxed = (parent: unknown) => hideEdges({ name: "a sandboxed frame", parent });

type Row = { who: string; ctx: Ctx; source: (w: Receiver) => unknown; origin: string };
const HEARD: Row[] = [
  { who: "this document", ctx: "pane", source: (w) => w, origin: ORIGIN },
  { who: "its embedder, the romp shell", ctx: "pane", source: (w) => w.parent, origin: ORIGIN },
  { who: "a second chat column on this origin", ctx: "pane", source: () => SECOND_COLUMN, origin: ORIGIN },
  { who: "a pane posting up to the shell's page", ctx: "shell", source: () => CHILD_PANE, origin: ORIGIN },
  { who: "the shell's page itself", ctx: "shell", source: (w) => w, origin: ORIGIN },
  { who: "the VS Code webview host (the frame's window.parent replaced)", ctx: "vscode", source: () => VSCODE_HOST, origin: VSCODE_ORIGIN },
  { who: "the VS Code webview host (the frame's window.parent deleted)", ctx: "vscode, older", source: () => VSCODE_HOST, origin: VSCODE_ORIGIN },
  { who: "this document's own dispatch of a kernel frame (no source, no origin)", ctx: "pane", source: () => null, origin: "" },
  { who: "a sourceless post on this document's origin", ctx: "pane", source: () => null, origin: ORIGIN },
];
const FOREIGN: Row[] = [
  { who: "a sandboxed frame beside the pane in the shell (opaque origin)", ctx: "pane", source: (w) => sandboxed(w.parent), origin: "null" },
  { who: "a sandboxed frame inside the shell's page (opaque origin)", ctx: "shell", source: (w) => sandboxed(w), origin: "null" },
  { who: "a page on another origin that opened the pane", ctx: "pane", source: () => OTHER_PAGE, origin: OTHER_ORIGIN },
  { who: "a page on another origin that opened the shell", ctx: "shell", source: () => OTHER_PAGE, origin: OTHER_ORIGIN },
  { who: "a sandboxed frame inside the VS Code webview", ctx: "vscode", source: (w) => sandboxed(w), origin: "null" },
  { who: "a sandboxed frame that is gone (no source, opaque origin)", ctx: "pane", source: () => null, origin: "null" },
  { who: "a page on another origin that is gone (no source)", ctx: "shell", source: () => null, origin: OTHER_ORIGIN },
  { who: "a window on another VS Code webview's origin (the frame's window.parent replaced)", ctx: "vscode", source: () => OTHER_WEBVIEW, origin: OTHER_VSCODE_ORIGIN },
  { who: "a window on another VS Code webview's origin (the frame's window.parent deleted)", ctx: "vscode, older", source: () => OTHER_WEBVIEW, origin: OTHER_VSCODE_ORIGIN },
  { who: "a sourceless post from another VS Code webview's origin", ctx: "vscode", source: () => null, origin: OTHER_VSCODE_ORIGIN },
];

// ── the stand-ins stay small in a dump ──

test("the stand-ins inspect as their primitives: every enumerable key of a receiving window and of each sending window holds a primitive", () => {
  const all: object[] = [SHELL, SECOND_COLUMN, CHILD_PANE, VSCODE_HOST, OTHER_PAGE, OTHER_WEBVIEW, sandboxed(SHELL),
    receiver("pane"), receiver("shell"), receiver("vscode"), receiver("vscode, older")];
  for (const o of all) {
    for (const k of Object.keys(o)) assert.ok(staysEnumerable((o as any)[k]), k + " is enumerable and holds a " + typeof (o as any)[k]);
  }
  assert.ok(windowSender({ source: SHELL, origin: ORIGIN }, receiver("pane")) === "embedder", "a hidden parent is still read");
});

// ── the listeners run as installed ──

/** Runs `fn` with each key of `vals` set on globalThis, restoring every one after. */
function withGlobals<T>(vals: Record<string, unknown>, fn: () => T): T {
  const g: any = globalThis;
  const saved: Array<[string, boolean, unknown]> = Object.keys(vals).map((k) => [k, k in g, g[k]]);
  try {
    for (const k of Object.keys(vals)) g[k] = vals[k];
    return fn();
  } finally {
    for (const [k, had, v] of saved) { if (had) g[k] = v; else delete g[k]; }
  }
}
type Installed = { site: string; data: unknown; what: string; setup: (effect: () => void) => { globals?: Record<string, unknown>; install: () => void };
                   marker?: string };   // in a file with more than one window message listener: the text that picks the installed one's site
const INSTALLED: Installed[] = [
  { site: "webview/frame-listener.ts", what: "a kernel-shaped feed frame reaching a pane's frame handler through listenForFrames",
    data: { type: "feed", ledgers: [{ id: SID, name: "api" }] },
    setup: (effect) => ({ install: () => { listenForFrames(() => effect()); } }) },
  { site: "webview/settings.ts", what: "a settingsSync that replaces the settings store (installSettingsSync)",
    data: { type: "settingsSync", settings: { theme: "classic", figureHosts: ["example.invalid"] } },
    setup: (effect) => ({ globals: { localStorage: { setItem: (k: string) => { if (k === "romp:settings") effect(); } } },
                          install: () => installSettingsSync() }) },
  { site: "webview/file-view.ts", what: "a viewFile relay that opens a file in the viewer (initFileView)", marker: 'm.romp === "viewFile"',
    data: { romp: "viewFile", path: "docs/design.md", sid: SID },
    setup: (effect) => ({ globals: { document: { addEventListener: () => { /* the viewer's press watch */ } } },
                          install: () => initFileView(() => { /* the kernel poster */ }, () => effect()) }) },
  { site: "webview/file-browse.ts", what: "a browseFiles relay that lists a directory (initFileBrowse)",
    data: { romp: "browseFiles", path: "docs", sid: SID },
    setup: (effect) => ({ install: () => initFileBrowse(() => { /* the kernel poster */ }, { onRelay: () => effect() }) }) },
];
/** Installs the listener for real over a fresh receiving window of the row's kind (the global window while it installs
 *  and while the message is delivered), delivers the message from the row's sender, and returns the effect's count. */
function runInstalled(leg: Installed, row: Row): number {
  const w = receiver(row.ctx);
  let n = 0;
  const { globals, install } = leg.setup(() => { n++; });
  withGlobals({ ...(globals || {}), window: w }, () => {
    install();
    const ls = w.messageListeners();
    assert.equal(ls.length, 1, leg.site + ": the install added one window message listener");
    ls[0]({ data: leg.data, source: row.source(w), origin: row.origin });
  });
  return n;
}

for (const leg of INSTALLED) {
  test(leg.site + ": " + leg.what + " from a foreign sender reaches nothing", () => {
    const reached = FOREIGN.filter((row) => runInstalled(leg, row) !== 0).map((row) => row.who);
    assert.deepEqual(reached, [], leg.site + ": a foreign sender reached the effect: " + reached.join("; "));
  });
  test(leg.site + ": " + leg.what + " from every sender that is not foreign reaches the effect once", () => {
    const missed = HEARD.map((row) => [row.who, runInstalled(leg, row)] as const).filter(([, n]) => n !== 1).map(([who, n]) => who + " (" + n + ")");
    assert.deepEqual(missed, [], leg.site + ": a heard sender did not reach the effect once: " + missed.join("; "));
  });
}

// ── the listeners lifted out of their files ──

type Site = { file: string; line: number; receiver: string; fn: any; text: string; kind: "addEventListener" | "onmessage" };
const parsed = new Map<string, Site[]>();
/** The names a script reaches its own window by, for an onmessage assignment: window.onmessage, self.onmessage,
 *  globalThis.onmessage (or any of them by a computed member), or a bare `onmessage =`. Any other receiver (a WebSocket, a
 *  MessagePort, a worker) is not a window, and no other page can post to it. */
const WINDOW_NAMES = new Set(["window", "self", "globalThis"]);
/** Every window message listener in `src`, read by the TypeScript parser (so a spelling in a comment or a string is no
 *  listener): each addEventListener("message", fn) call, whether the method is named (x.addEventListener, a bare
 *  addEventListener) or a computed member (x["addEventListener"]), and each assignment of an onmessage handler to the
 *  window by any of WINDOW_NAMES. Where it is, what it is on, and the listener's node and text. A listener handed to
 *  addEventListener by a plain name (the file viewer's onKernelMessage, which its close removes by that name) is read at
 *  the function the name holds, when a const of that name, found by the name's binding (declOf), is initialised to a
 *  function written in place: a const is never rebound, and the binding, not the spelling, picks it, so another
 *  declaration of the name elsewhere in the file is not the one read. Any other name (a let or a var, which can be
 *  rebound; a parameter; a function declaration, which can be assigned to; a const holding a call's result) stays the
 *  name, which the head census refuses. */
function sitesIn(file: string, src: string): Site[] {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, file.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
  const out: Site[] = [];
  const line = (n: any) => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  /** the expression under any parentheses, type assertion or non-null mark: `(window as any)` is window */
  const bare = (n: any): any => {
    while (ts.isParenthesizedExpression(n) || ts.isAsExpression(n) || ts.isTypeAssertionExpression(n) || ts.isNonNullExpression(n)
           || (ts.isSatisfiesExpression && ts.isSatisfiesExpression(n))) n = n.expression;
    return n;
  };
  /** the member name of `x.name` or `x["name"]`, with its receiver's text; or a bare identifier's name, no receiver */
  const member = (n: any): { name: string; receiver: string } | null => {
    n = bare(n);
    if (ts.isPropertyAccessExpression(n)) return { name: n.name.text, receiver: bare(n.expression).getText(sf) };
    if (ts.isElementAccessExpression(n) && n.argumentExpression && ts.isStringLiteralLike(n.argumentExpression))
      return { name: n.argumentExpression.text, receiver: bare(n.expression).getText(sf) };
    if (ts.isIdentifier(n)) return { name: n.text, receiver: "" };
    return null;
  };
  /** the listener a registration hands over: the argument, or the function a const it names holds (see above) */
  const listenerOf = (a: any): any => {
    const u = bare(a);
    if (!ts.isIdentifier(u)) return a;
    const d = declOf(u);
    const init = d && isConstDecl(d) && ts.isIdentifier(d.name) && d.initializer ? bare(d.initializer) : null;
    return init && (ts.isArrowFunction(init) || ts.isFunctionExpression(init)) ? init : a;
  };
  const visit = (n: any): void => {
    if (ts.isCallExpression(n) && n.arguments.length >= 2 && ts.isStringLiteralLike(n.arguments[0]) && n.arguments[0].text === "message") {
      const m = member(n.expression);
      if (m && m.name === "addEventListener") {
        const fn = listenerOf(n.arguments[1]);
        out.push({ file, line: line(n), receiver: m.receiver, fn, text: fn.getText(sf), kind: "addEventListener" });
      }
    }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      const m = member(n.left);
      if (m && m.name === "onmessage" && (m.receiver === "" || WINDOW_NAMES.has(m.receiver))) {
        out.push({ file, line: line(n), receiver: m.receiver, fn: n.right, text: n.right.getText(sf), kind: "onmessage" });
      }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}
/** Every window message listener in a ui/ file (sitesIn). One parse per file. */
function messageSites(file: string): Site[] {
  const had = parsed.get(file);
  if (had) return had;
  const out = sitesIn(file, fs.readFileSync(path.join(UI, file), "utf8"));
  parsed.set(file, out);
  return out;
}
/** The one message listener in `file` whose text holds `marker`. */
function siteOf(file: string, marker: string): Site {
  const hits = messageSites(file).filter((s) => s.text.includes(marker));
  assert.equal(hits.length, 1, file + ": exactly one window message listener holds " + JSON.stringify(marker) + " (found " + hits.length + "); re-anchor");
  return hits[0];
}

/** The inert stub every unbound free identifier of a lifted listener resolves to: any read on it is the stub again, a
 *  call returns undefined, a write is dropped. */
const stub: any = new Proxy(function () { /* inert */ }, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => "" : stub),
  apply: () => undefined,
  set: () => true,
});
const chain: any = { then: () => chain, catch: () => chain };   // a fetch's promise chain that never settles

type Lifted = { file: string; marker: string; what: string; data: unknown;
                named: (hit: () => void, w: Receiver) => Record<string, unknown>;   // the effect's binding, counting through hit
                writes?: string;   // or: the effect is a write to this free name
                arm?: string };    // a listener with more than one arm the check must hold has a leg per arm, each naming its arm
/** The file viewer's way back (openFileView's onKernelMessage) over a pane that waits, with the probes' budget full. Both of
 *  its effects count: the way back (wayBackEvent, which runs the fetch again) and a probe of the picture's address
 *  (probeServed, which sends one), so each of its two legs reads that a foreign sender reaches neither, and that a heard
 *  sender reaches its own arm's effect and not the other's. */
const wayBackScope = (hit: () => void): Record<string, unknown> => ({
  wayBackEvent: hit, probeServed: () => { hit(); return true; }, paneWaits: () => true,
  wayBackProbing: false, wayBackProbes: 3, wayBackSeq: 0, objUrl: "/file?path=docs%2Ffigure.svg&sid=" + SID + "&v=1",
});
const LIFTED: Lifted[] = [
  { file: "webview/file-view.ts", marker: '"hostUp"', arm: "hostUp",
    what: "the viewer's way back from a failed svg picture on hostUp (federation.js's own dispatch), which runs the fetch again",
    data: { type: "hostUp", hosts: ["TESTHOST"] }, named: (hit) => wayBackScope(hit) },
  { file: "webview/file-view.ts", marker: "probeServed(", arm: "probe",
    what: "the viewer's way back from a failed svg picture on any other kernel message, which sends a probe of the picture's address",
    data: { type: "sessions", sessions: [] }, named: (hit) => wayBackScope(hit) },
  { file: "webview/waiting.ts", marker: 'm.romp !== "panes"', what: "the shell's panes word replacing the Waiting pane's pane-routing cache",
    data: { romp: "panes", on: { files: true }, avail: { files: true } }, named: () => ({}), writes: "panesAvail" },
  { file: "webview/file-comments.ts", marker: '"fileCommentsResult"', what: "a fileCommentsResult settling the live panel's request",
    data: { type: "fileCommentsResult", reqId: 1, store: { comments: [] } }, named: (hit) => ({ live: { settle: hit, failAll: () => { /* not this arm */ } } }) },
  { file: "webview/gear.js", marker: "'taskTracking'", what: "the gear's taskTracking echo, which tells the shell",
    data: { type: "taskTracking", on: false }, named: (hit) => ({ tellShellTracking: hit }) },
  { file: "webview/gear.js", marker: "'browseResult'", what: "the gear's browseResult, which fills the default directory and persists it",
    data: { type: "browseResult", target: "gear", path: "/srv/notes-api" }, named: (hit) => ({ dd: { value: "", dispatchEvent: hit } }) },
  { file: "webview/gear.js", marker: "'settingStale'", what: "the gear's settingStale toast, which advances the gesture clock",
    data: { type: "settingStale", setting: "judge-model", storedGt: 2000, gt: 1000, kept: "fable" }, named: (hit) => ({ gclock: { learn: hit, stamp: () => 0 } }) },
  { file: "webview/gear.js", marker: "'models'", what: "the gear's models frame, which re-reads /models",
    data: { type: "models", rev: 2 }, named: (hit) => ({ fetch: () => { hit(); return chain; } }) },
  { file: "webview/gear.js", marker: "'openSettings'", what: "the gear's openSettings ask, which opens the modal",
    data: { romp: "openSettings", tab: "tasks" }, named: (hit) => ({ openSettings: hit }) },
  { file: "webview/gear.js", marker: "'logUnseen'", what: "the gear's logUnseen count, which sets the Open log badge",
    data: { romp: "logUnseen", n: 3 }, named: (hit, w) => { defineHidden(w, "__rompSetLogCount", hit); return {}; } },
  { file: "webview/palette-main.ts", marker: '"openKeys"', what: "the shell's openKeys ask, which opens the shortcuts dialog",
    data: { romp: "openKeys" }, named: (hit) => ({ keys: { open: hit } }) },
  { file: "webview/palette-main.ts", marker: '"hotkeyConfigure"', what: "the shell's hotkeyConfigure ask, which binds a tab's hot key",
    data: { romp: "hotkeyConfigure", sid: SID, name: "web" }, named: (hit) => ({ configureHotkey: hit }) },
  { file: "webview/strip.ts", marker: '"stripShow"', what: "the VS Code strip's usage push, which repaints the bars",
    data: { type: "usage", usage: { fiveHour: { pct: 10 } } }, named: (hit) => ({ render: hit }) },
];

const compiled = new Map<string, (scope: unknown) => Listener>();
/** The lifted listener as a function of its scope (compiled once per site): sloppy-mode code, which `with` needs
 *  (esbuild's transform adds no strict prologue, and a .js listener is used as written). */
function compile(site: Site): (scope: unknown) => Listener {
  const key = site.file + ":" + site.line;
  const hit = compiled.get(key);
  if (hit) return hit;
  const src = "const __listener = " + site.text + ";\n";
  const code = site.file.endsWith(".ts") ? requireCjs("esbuild").transformSync(src, { loader: "ts", target: "es2020" }).code : src;
  const make = new Function("__scope", "with (__scope) {\n" + code + "\nreturn __listener;\n}") as (s: unknown) => Listener;
  compiled.set(key, make);
  return make;
}
/** Runs the lifted listener once, over a fresh receiving window of the row's kind, on the message from the row's sender,
 *  and returns the effect's count. */
function runLifted(leg: Lifted, row: Row): number {
  const site = siteOf(leg.file, leg.marker);
  const w = receiver(row.ctx);
  let n = 0;
  const hit = () => { n++; };
  const named: Record<string, unknown> = {
    windowSender: (e: { source?: unknown; origin?: unknown }) => windowSender(e, w),
    window: w,
    location: w.location,
    ...leg.named(hit, w),
  };
  const scope = new Proxy(named, {
    has: (t, k) => typeof k === "string" && (k in t || !(k in globalThis)),   // named first; other real globals (JSON, Object, Event) stay real
    get: (t, k) => (typeof k !== "string" ? undefined : (k in t ? t[k] : stub)),   // Symbol.unscopables reads undefined, so no name is skipped
    set: (t, k, v) => { if (typeof k === "string") { if (k === leg.writes) hit(); t[k] = v; } return true; },
  });
  compile(site)(scope)({ data: leg.data, source: row.source(w), origin: row.origin });
  return n;
}

for (const leg of LIFTED) {
  const label = leg.file + " (" + (leg.arm ? leg.arm + " arm" : leg.marker) + ")";
  test(label + ": " + leg.what + " from a foreign sender reaches nothing", () => {
    const reached = FOREIGN.filter((row) => runLifted(leg, row) !== 0).map((row) => row.who);
    assert.deepEqual(reached, [], label + ": a foreign sender reached the effect: " + reached.join("; "));
  });
  test(label + ": " + leg.what + " from every sender that is not foreign reaches the effect once", () => {
    const missed = HEARD.map((row) => [row.who, runLifted(leg, row)] as const).filter(([, n]) => n !== 1).map(([who, n]) => who + " (" + n + ")");
    assert.deepEqual(missed, [], label + ": a heard sender did not reach the effect once: " + missed.join("; "));
  });
}

// ── the census: every window message listener in ui/ ──

/** Every ui/ source file the parser should read: .ts, .js and .mjs under ui/ at any depth, tests (*.test.*) excluded. */
function uiSources(): string[] {
  const out: string[] = [];
  const walk = (rel: string): void => {
    for (const d of fs.readdirSync(path.join(UI, rel), { withFileTypes: true })) {
      const r = rel ? rel + "/" + d.name : d.name;
      if (d.isDirectory()) { if (d.name !== "node_modules" && d.name !== "dist") walk(r); continue; }
      if (/\.(ts|js|mjs)$/.test(d.name) && !/\.test\.(ts|js|mjs)$/.test(d.name) && !d.name.endsWith(".d.ts")) out.push(r);
    }
  };
  walk("");
  return out.sort();
}
/** Where the listener's `if (windowSender(<its event>) === "foreign") return;` is among its body's statements, or why it
 *  does not count: the listener takes one parameter, the event, a plain name with no default (a parameter's default runs
 *  before the body, so a default on it or on a second parameter would run ahead of the check), and every statement before
 *  the check must be a read of the message (a declaration initialised to <event>.data) or an early return on a condition
 *  that calls, constructs and assigns nothing, so no arm runs before the check. */
function headCheck(site: Site): string | null {
  const fn = site.fn;
  if (ts.isIdentifier(fn)) return "the listener is a name no const holding a function written in place binds (sitesIn): " + fn.text;
  if (!(ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) || !fn.body || !ts.isBlock(fn.body)) return "the listener is not a function with a body";
  if (!fn.parameters.length || !ts.isIdentifier(fn.parameters[0].name)) return "the listener names no event parameter";
  if (fn.parameters.length !== 1 || fn.parameters[0].initializer || fn.parameters[0].dotDotDotToken) {
    return "the listener takes more than its one event parameter, or gives it a default, and a parameter's default runs before the check: " + fn.parameters.map((q: any) => q.getText()).join(", ").slice(0, 80);
  }
  const ev = fn.parameters[0].name.text;
  const isReturn = (s: any) => ts.isReturnStatement(s) && !s.expression;
  const isGate = (s: any) => ts.isIfStatement(s) && !s.elseStatement && isReturn(s.thenStatement)
    && ts.isBinaryExpression(s.expression) && s.expression.operatorToken.kind === ts.SyntaxKind.EqualsEqualsEqualsToken
    && ts.isCallExpression(s.expression.left) && ts.isIdentifier(s.expression.left.expression) && s.expression.left.expression.text === "windowSender"
    && s.expression.left.arguments.length === 1 && ts.isIdentifier(s.expression.left.arguments[0]) && s.expression.left.arguments[0].text === ev
    && ts.isStringLiteralLike(s.expression.right) && s.expression.right.text === "foreign";
  const inert = (n: any): boolean => {
    if (ts.isCallExpression(n) || ts.isNewExpression(n) || ts.isTaggedTemplateExpression(n) || ts.isDeleteExpression(n) || ts.isAwaitExpression(n) || ts.isYieldExpression(n)
        || ts.isPrefixUnaryExpression(n) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken)
        || ts.isPostfixUnaryExpression(n) || ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment) return false;
    let ok = true;
    ts.forEachChild(n, (c: any) => { if (ok && !inert(c)) ok = false; });
    return ok;
  };
  const readsMessage = (s: any) => ts.isVariableStatement(s) && s.declarationList.declarations.every((d: any) =>
    d.initializer && ts.isPropertyAccessExpression(d.initializer) && ts.isIdentifier(d.initializer.expression)
    && d.initializer.expression.text === ev && d.initializer.name.text === "data");
  const earlyReturn = (s: any) => ts.isIfStatement(s) && !s.elseStatement && isReturn(s.thenStatement) && inert(s.expression);
  const body = fn.body.statements;
  for (let i = 0; i < body.length; i++) {
    if (isGate(body[i])) return null;
    if (!readsMessage(body[i]) && !earlyReturn(body[i])) return "statement " + (i + 1) + " runs before the foreign-sender check: " + body[i].getText().slice(0, 80);
  }
  return "no `if (windowSender(" + ev + ") === \"foreign\") return;` in the listener's body";
}
// The gated sites, by file and count. A listener that is not a window listener (a WebSocket's or a MessagePort's, which
// no other page can post to) would be listed in EXEMPT with its reason; there is none in ui/ today (federation.ts's
// sockets use onmessage, and the design leaves WebSocket and MessageChannel handlers out).
const GATED: Array<[string, number]> = [
  ["webview/file-browse.ts", 1], ["webview/file-comments.ts", 1], ["webview/file-view.ts", 2], ["webview/frame-listener.ts", 1],
  ["webview/gear.js", 6], ["webview/palette-main.ts", 2], ["webview/settings.ts", 1], ["webview/strip.ts", 1], ["webview/waiting.ts", 1],
];
const EXEMPT: Array<[string, number, string]> = [];

test("census: every window message listener in ui/ opens with the foreign-sender check, before any arm, and is one of the gated sites", () => {
  const sites = uiSources().flatMap(messageSites);
  const exempt = new Set(EXEMPT.map(([f, line]) => f + ":" + line));
  const counted = new Map<string, number>();
  for (const s of sites) if (!exempt.has(s.file + ":" + s.line)) counted.set(s.file, (counted.get(s.file) || 0) + 1);
  assert.deepEqual([...counted.entries()].sort(), GATED.slice().sort(),
    "the window message listeners in ui/ are not the gated sites: a new one is gated at its head, given an executed leg in this file and added to GATED");
  const bad = sites.filter((s) => !exempt.has(s.file + ":" + s.line)).map((s) => [s, headCheck(s)] as const).filter(([, why]) => why !== null)
    .map(([s, why]) => s.file + ":" + s.line + " (" + s.receiver + "): " + why);
  assert.deepEqual(bad, [], "a window message listener acts before it rules out a foreign sender:\n" + bad.join("\n"));
  assert.ok(sites.every((s) => s.receiver === "window" && s.kind === "addEventListener"),
    "every census site is window.addEventListener(\"message\", ...), the one spelling the gated sites use");
});

test("the census reads every spelling of a window message listener: addEventListener named or computed, an onmessage handler on window, self, globalThis or the bare global; a socket's onmessage is none", () => {
  const found = (src: string) => sitesIn("webview/probe.ts", src).map((s) => s.kind + " on " + (s.receiver || "(bare)"));
  const listener = "function (e) { go(e.data); }";
  assert.deepEqual(found("window.addEventListener(\"message\", " + listener + ");"), ["addEventListener on window"]);
  assert.deepEqual(found("window[\"addEventListener\"](\"message\", " + listener + ");"), ["addEventListener on window"]);
  assert.deepEqual(found("self['addEventListener'](`message`, " + listener + ");"), ["addEventListener on self"]);
  assert.deepEqual(found("addEventListener(\"message\", " + listener + ");"), ["addEventListener on (bare)"]);
  assert.deepEqual(found("window.onmessage = " + listener + ";"), ["onmessage on window"]);
  assert.deepEqual(found("(window as any).onmessage = " + listener + ";"), ["onmessage on window"], "a cast is still the window");
  assert.deepEqual(found("(<any>window)[\"addEventListener\"](\"message\", " + listener + ");"), ["addEventListener on window"]);
  assert.deepEqual(found("self.onmessage = " + listener + ";"), ["onmessage on self"]);
  assert.deepEqual(found("globalThis[\"onmessage\"] = " + listener + ";"), ["onmessage on globalThis"]);
  assert.deepEqual(found("onmessage = " + listener + ";"), ["onmessage on (bare)"]);
  assert.deepEqual(found("ws.onmessage = " + listener + "; port.onmessage = " + listener + ";"), [], "a socket's and a port's handler are not window listeners");
  assert.deepEqual(found("window.addEventListener(\"resize\", " + listener + "); const s = \"window.onmessage = f\";"), [], "another event, or a string");
  // a listener handed over by name is read at the function written in place that a const of that name holds, the const
  // the name's binding picks; any other name stays the name (the head census refuses it)
  const text = (src: string) => sitesIn("webview/probe.ts", src).map((s) => s.text);
  assert.deepEqual(text("const h = (e: MessageEvent): void => { go(e.data); }; window.addEventListener(\"message\", h);"), ["(e: MessageEvent): void => { go(e.data); }"], "a const arrow function");
  assert.deepEqual(text("const h = function (e) { go(e.data); }; window.addEventListener(\"message\", h); window.removeEventListener(\"message\", h);"),
    ["function (e) { go(e.data); }"], "a const function expression; a removal registers nothing");
  assert.deepEqual(text("const h = (e) => { stop(); }; function f() { const h = (e) => { go(e.data); }; window.addEventListener(\"message\", h); }"),
    ["(e) => { go(e.data); }"], "the binding picks the inner const, not the first declaration of the spelling");
  assert.deepEqual(text("const h = (e) => { go(e.data); }; { const h = (e) => { stop(); }; } window.addEventListener(\"message\", h);"),
    ["(e) => { go(e.data); }"], "the binding picks the outer const, not the last declaration of the spelling");
  assert.deepEqual(text("let h = (e) => { go(e.data); }; window.addEventListener(\"message\", h);"), ["h"], "a let can be rebound");
  assert.deepEqual(text("const h = wrap((e) => { go(e.data); }); window.addEventListener(\"message\", h);"), ["h"], "a const holding a call's result");
});

// ── the census: the name every check calls is the helper ──
//
// The lifted legs hand each listener the real windowSender under that name, and the head census accepts a call by that
// name, so neither reads what the name is bound to in the listener's file. This census does: in every ui/ source file
// that names windowSender (the gated sites, the chat's render.ts and any file that joins them), the name has exactly one
// binding, the helper itself, and nothing writes to it. In a TypeScript file the binding is
// `import { windowSender } from "./window-sender"`, unaliased; in gear.js, a CommonJS script, it is
// `var windowSender = require('./window-sender.ts').windowSender;` at the file's top level. A second binding anywhere in
// the file (a local, a parameter, a function, a destructured name, an import aliased so that another binding takes the
// name), an assignment to the name, or a `with` statement, which can rebind any name, fails it.

const TS_BINDING = 'import { windowSender } from "./window-sender";';
const GEAR_BINDING = "var windowSender = require('./window-sender.ts').windowSender;";
/** Why `windowSender` in this source does not certainly name the helper, or null when it does: its declarations, the
 *  writes to it and any `with` statement, read by the TypeScript parser (so a spelling in a comment or a string is none). */
function senderBinding(file: string, src: string): string | null {
  const isJs = !file.endsWith(".ts");
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, isJs ? ts.ScriptKind.JS : ts.ScriptKind.TS);
  const decls: any[] = [], writes: string[] = [], withs: string[] = [];
  const DECL = [ts.SyntaxKind.VariableDeclaration, ts.SyntaxKind.Parameter, ts.SyntaxKind.BindingElement, ts.SyntaxKind.FunctionDeclaration,
    ts.SyntaxKind.FunctionExpression, ts.SyntaxKind.ClassDeclaration, ts.SyntaxKind.ClassExpression, ts.SyntaxKind.ImportSpecifier,
    ts.SyntaxKind.ImportClause, ts.SyntaxKind.NamespaceImport, ts.SyntaxKind.ImportEqualsDeclaration, ts.SyntaxKind.EnumDeclaration,
    ts.SyntaxKind.ModuleDeclaration];
  const named = (n: any): boolean => !!n && ts.isIdentifier(n) && n.text === "windowSender";
  const mentions = (n: any): boolean => { let hit = named(n); if (!hit) ts.forEachChild(n, (c: any) => { if (!hit && mentions(c)) hit = true; }); return hit; };
  const visit = (n: any): void => {
    if (DECL.includes(n.kind) && named(n.name)) decls.push(n);
    if (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment && mentions(n.left)) writes.push(n.getText(sf).slice(0, 80));
    if ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken) && named(n.operand)) writes.push(n.getText(sf));
    if ((ts.isForInStatement(n) || ts.isForOfStatement(n)) && !ts.isVariableDeclarationList(n.initializer) && mentions(n.initializer)) writes.push(n.initializer.getText(sf));
    if (ts.isWithStatement(n)) withs.push(n.getText(sf).slice(0, 80));
    ts.forEachChild(n, visit);
  };
  visit(sf);
  if (withs.length) return "a `with` statement, which can rebind the name: " + withs.join("; ");
  if (writes.length) return "a write to windowSender: " + writes.join("; ");
  if (decls.length !== 1) return decls.length + " bindings of windowSender, not the one: " + decls.map((d) => ts.SyntaxKind[d.kind] + " `" + d.getText(sf).slice(0, 60) + "`").join("; ");
  const d = decls[0];
  if (isJs) {
    const stmt = d.parent && d.parent.parent;
    if (!ts.isVariableDeclaration(d) || !stmt || !ts.isVariableStatement(stmt) || stmt.parent !== sf || stmt.getText(sf) !== GEAR_BINDING) {
      return "the binding is not `" + GEAR_BINDING + "` at the file's top level: `" + (stmt ? stmt.getText(sf) : d.getText(sf)).slice(0, 100) + "`";
    }
    return null;
  }
  const decl = ts.isImportSpecifier(d) ? d.parent.parent.parent : null;
  if (!decl || d.propertyName || !ts.isImportDeclaration(decl) || decl.getText(sf) !== TS_BINDING) {
    return "the binding is not `" + TS_BINDING + "`: `" + (decl ? decl.getText(sf) : d.getText(sf)).slice(0, 100) + "`";
  }
  return null;
}
/** Every ui/ source file whose code names windowSender (read by the parser), window-sender.ts itself aside. */
function senderFiles(): string[] {
  return uiSources().filter((f) => f !== "webview/window-sender.ts").filter((f) => {
    const src = fs.readFileSync(path.join(UI, f), "utf8");
    if (!src.includes("windowSender")) return false;
    const sf = ts.createSourceFile(f, src, ts.ScriptTarget.Latest, true, f.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
    let hit = false;
    const visit = (n: any): void => { if (hit) return; if (ts.isIdentifier(n) && n.text === "windowSender") hit = true; else ts.forEachChild(n, visit); };
    visit(sf);
    return hit;
  });
}

test("census: in every ui/ file that calls the check, the name windowSender is bound once, to the helper, and never written", () => {
  const files = senderFiles();
  const gated = GATED.map(([f]) => f);
  assert.deepEqual(gated.filter((f) => !files.includes(f)), [], "every gated site's file names windowSender");
  assert.ok(files.includes("webview/render.ts"), "the chat's frame handler, the first check, is in the population");
  const bad = files.map((f) => [f, senderBinding(f, fs.readFileSync(path.join(UI, f), "utf8"))] as const).filter(([, why]) => why !== null)
    .map(([f, why]) => f + ": " + why);
  assert.deepEqual(bad, [], "a file's windowSender is not certainly the helper:\n" + bad.join("\n"));
});

test("the binding census reads what it claims: a local, a parameter, an aliased import, a wrapper in gear.js, a write or a `with` is refused; the helper's own import and require are accepted", () => {
  const imp = TS_BINDING + "\n";
  assert.equal(senderBinding("webview/probe.ts", imp + 'window.addEventListener("message", (e) => { if (windowSender(e) === "foreign") return; });'), null);
  assert.equal(senderBinding("webview/probe.js", "var x = 1;\n" + GEAR_BINDING + "\nfunction f(e) { return windowSender(e); }"), null);
  const refused: Array<[string, string, RegExp]> = [
    ["webview/probe.ts", 'import { windowSender as senderOf } from "./window-sender";\nconst windowSender = (e: MessageEvent) => (e.origin === "null" ? "peer" : senderOf(e));', /not `import/],
    ["webview/probe.ts", imp + "function f() { const windowSender = (e: unknown) => \"peer\"; return windowSender; }", /2 bindings/],
    ["webview/probe.ts", imp + "function f(windowSender: (e: unknown) => string) { return windowSender; }", /2 bindings/],
    ["webview/probe.ts", imp + "const { windowSender: w2 } = { windowSender: 1 }; function g({ windowSender }: any) { return windowSender; }", /2 bindings/],
    ["webview/probe.ts", imp + "function windowSender2() { return 1; } class C { m() { function windowSender() { return 'peer'; } return windowSender; } }", /2 bindings/],
    ["webview/probe.ts", 'import { windowSender } from "./window-sender.ts";', /not `import/],
    ["webview/probe.ts", 'import { windowSender } from "./some-other-module";', /not `import/],
    ["webview/probe.ts", 'import windowSender from "./window-sender";', /not `import/],
    ["webview/probe.ts", 'import * as windowSender from "./window-sender";', /not `import/],
    ["webview/probe.ts", "const windowSender = require(\"./window-sender\").windowSender;", /not `import/],
    ["webview/probe.js", "var windowSender = function (e) { var c = require('./window-sender.ts').windowSender(e); return (c === 'foreign' && e && e.origin === 'null') ? 'peer' : c; };", /not `var windowSender = require/],
    ["webview/probe.js", "(function () { " + GEAR_BINDING + " })();", /top level/],
    ["webview/probe.js", GEAR_BINDING + "\nwindowSender = function () { return 'peer'; };", /a write/],
    ["webview/probe.js", GEAR_BINDING + "\n[windowSender] = [function () { return 'peer'; }];", /a write/],
    ["webview/probe.js", GEAR_BINDING + "\nwith ({ windowSender: function () { return 'peer'; } }) { windowSender(e); }", /with/],
    ["webview/probe.js", "var a = 1;", /0 bindings/],
  ];
  for (const [file, src, why] of refused) assert.match(String(senderBinding(file, src)), why, file + ": " + src);
});

// ── the census: every addEventListener in ui/ is one the census above can read ──
//
// The census above reads a registration spelled addEventListener("message", fn), its event type a string literal. A
// registration that reaches the method any other way escapes it: through .call or .apply
// (EventTarget.prototype.addEventListener.call(window, "message", f)), an alias or a bound copy
// (const add = window.addEventListener.bind(window); add("message", f)), a destructured name, or a call whose event type
// is not a literal (window.addEventListener(type, f)). tests/test_shell_source_check.py refuses those in kernel.py
// (_loose_add_tokens); this is the same rule for ui/, read by the TypeScript parser, so a spelling in a comment or inside
// a longer string is none. Every addEventListener in a ui/ source file (tests excluded) must be one of:
//   - the method called directly with a string literal for its event type (the census above reads the "message" ones);
//   - the method called directly with an event type the parser resolves to strings, none of them "message": a const
//     initialised to a string, in the file or exported so by the ui/ module it is imported from (`export const`); the
//     const variable of a for...of over a list of strings; or the one parameter, never written, of a callback handed
//     to such a list's forEach that has no way to reach the list (forEach's only argument, one parameter, and neither
//     `arguments` nor `this` in a function that has its own: sealedForEach). A list is an array literal of strings,
//     inline or held by a const that is not exported and whose every other mention is a for...of's list or such a
//     forEach's receiver;
//   - a read whose value is only tested (typeof x.addEventListener === "function", if (x.addEventListener) ...), which
//     registers nothing;
//   - the name of a member declared in a type or on an object or class (a stand-in's method), which registers nothing.
// Anything else fails, with where it is and why.

/** The expression under any parentheses, casts and non-null marks. */
const unwrap = (n: any): any => {
  while (ts.isParenthesizedExpression(n) || ts.isAsExpression(n) || ts.isTypeAssertionExpression(n) || ts.isNonNullExpression(n)
         || (ts.isSatisfiesExpression && ts.isSatisfiesExpression(n))) n = n.expression;
  return n;
};
/** `n` with every parenthesis, cast and non-null mark around it: the node whose parent uses its value. */
const outer = (n: any): any => {
  while (n.parent && (ts.isParenthesizedExpression(n.parent) || ts.isAsExpression(n.parent) || ts.isTypeAssertionExpression(n.parent)
         || ts.isNonNullExpression(n.parent) || (ts.isSatisfiesExpression && ts.isSatisfiesExpression(n.parent)))) n = n.parent;
  return n;
};
const MEMBER_NAMES = [ts.SyntaxKind.MethodSignature, ts.SyntaxKind.PropertySignature, ts.SyntaxKind.MethodDeclaration,
  ts.SyntaxKind.PropertyDeclaration, ts.SyntaxKind.PropertyAssignment, ts.SyntaxKind.GetAccessor, ts.SyntaxKind.SetAccessor];
const COMPARISONS = [ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken, ts.SyntaxKind.EqualsEqualsToken,
  ts.SyntaxKind.ExclamationEqualsToken];
/** True when the value of `n` is only tested: a typeof's or a !'s operand, a side of a comparison, a condition, or the left
 *  of an && (which passes on only a falsy value). The right of an &&, and either side of an || or a ??, pass the value on,
 *  so they are tested only when that whole expression is. */
function onlyTested(n: any): boolean {
  const m = outer(n), p = m.parent;
  if (!p) return false;
  if (ts.isTypeOfExpression(p)) return true;
  if (ts.isPrefixUnaryExpression(p) && p.operator === ts.SyntaxKind.ExclamationToken) return true;
  if ((ts.isIfStatement(p) || ts.isWhileStatement(p) || ts.isDoStatement(p)) && p.expression === m) return true;
  if ((ts.isForStatement(p) || ts.isConditionalExpression(p)) && p.condition === m) return true;
  if (ts.isBinaryExpression(p)) {
    const op = p.operatorToken.kind;
    if (COMPARISONS.includes(op)) return true;
    if (op === ts.SyntaxKind.AmpersandAmpersandToken && p.left === m) return true;
    if (op === ts.SyntaxKind.AmpersandAmpersandToken || op === ts.SyntaxKind.BarBarToken || op === ts.SyntaxKind.QuestionQuestionToken) return onlyTested(p);
  }
  return false;
}
/** Whether the binding name `b` (an identifier or a destructuring pattern) binds `name`. */
const bindsName = (b: any, name: string): boolean => !!b && (ts.isIdentifier(b) ? b.text === name
  : (ts.isObjectBindingPattern(b) || ts.isArrayBindingPattern(b)) && b.elements.some((e: any) => !ts.isOmittedExpression(e) && bindsName(e.name, name)));
/** Whether `n` is a scope a `var` is hoisted to: a function, a class static block, a namespace body or the file. */
const isVarScope = (n: any): boolean => ts.isFunctionLike(n) || ts.isClassStaticBlockDeclaration(n) || ts.isModuleDeclaration(n) || ts.isSourceFile(n);
/** A declaration of `name` that is hoisted to the var scope `scope` from anywhere inside it, not inside a nested var scope:
 *  a `var` in any block or loop head (it binds the name for the whole function, whatever block it sits in), or a function
 *  declared inside a block (a script hoists it to the function too, as a var). Null when there is none. */
function hoistedDecl(scope: any, name: string): any {
  let hit: any = null;
  const visit = (n: any): void => {
    if (hit) return;
    if (ts.isFunctionDeclaration(n) && n.name && n.name.text === name && !(n.parent === scope || n.parent === scope.body)) { hit = n; return; }
    if (n !== scope && isVarScope(n)) return;   // a nested function's vars are its own
    if (ts.isVariableDeclarationList(n) && (n.flags & ts.NodeFlags.BlockScoped) === 0) {
      const d = n.declarations.find((x: any) => bindsName(x.name, name));
      if (d) { hit = d; return; }
    }
    ts.forEachChild(n, visit);
  };
  ts.forEachChild(scope, visit);
  return hit;
}
/** The declaration the identifier `id` refers to, found by walking out through the scopes around it, or null. A
 *  destructured declaration is found too, and resolves to no string below. A `var` binds its whole function, so on the way
 *  out through a function (or the file) a `var` of the name anywhere in it is the binding, ahead of the function's
 *  parameters, which such a var redeclares. A `with` statement between the identifier and its declaration can answer the
 *  name from its object instead, so an identifier inside one resolves to nothing. */
function declOf(id: any): any {
  const name = id.text;
  const binds = (d: any) => !!d && bindsName(d.name, name);
  for (let s = id.parent, from = id; s; from = s, s = s.parent) {
    if (ts.isWithStatement(s) && s.statement === from) return null;
    if ((ts.isForOfStatement(s) || ts.isForInStatement(s) || ts.isForStatement(s)) && s.initializer && ts.isVariableDeclarationList(s.initializer)) {
      const d = s.initializer.declarations.find(binds);
      if (d) return d;
    }
    if (isVarScope(s)) {
      const h = hoistedDecl(s, name);
      if (h) return h;
    }
    if (ts.isFunctionLike(s)) {
      const p = (s.parameters || []).find(binds);
      if (p) return p;
      if (ts.isFunctionExpression(s) && s.name && s.name.text === name) return s;
    }
    if (ts.isCatchClause(s) && binds(s.variableDeclaration)) return s.variableDeclaration;
    if (ts.isBlock(s) || ts.isSourceFile(s) || ts.isModuleBlock(s) || ts.isCaseClause(s) || ts.isDefaultClause(s)) {
      for (const st of s.statements) {
        if (ts.isVariableStatement(st)) { const d = st.declarationList.declarations.find(binds); if (d) return d; }
        if ((ts.isFunctionDeclaration(st) || ts.isClassDeclaration(st) || ts.isEnumDeclaration(st)) && st.name && st.name.text === name) return st;
        if (ts.isImportDeclaration(st) && st.importClause) {
          const c = st.importClause, nb = c.namedBindings;
          if (c.name && c.name.text === name) return c;
          if (nb && ts.isNamespaceImport(nb) && nb.name.text === name) return nb;
          if (nb && ts.isNamedImports(nb)) { const sp = nb.elements.find((e: any) => e.name.text === name); if (sp) return sp; }
        }
      }
    }
  }
  return null;
}
const isConstDecl = (d: any): boolean => ts.isVariableDeclaration(d) && ts.isVariableDeclarationList(d.parent) && (d.parent.flags & ts.NodeFlags.Const) !== 0;
const isExported = (st: any): boolean => !!st && !!st.modifiers && st.modifiers.some((m: any) => m.kind === ts.SyntaxKind.ExportKeyword);
/** Whether the identifier `name` appears anywhere inside `n`. */
function mentionsName(n: any, name: string): boolean {
  let hit = false;
  const visit = (c: any): void => { if (hit) return; if (ts.isIdentifier(c) && c.text === name) hit = true; else ts.forEachChild(c, visit); };
  visit(n);
  return hit;
}
/** Whether `this` appears anywhere inside `n`. */
function mentionsThis(n: any): boolean {
  let hit = false;
  const visit = (c: any): void => { if (hit) return; if (c.kind === ts.SyntaxKind.ThisKeyword) hit = true; else ts.forEachChild(c, visit); };
  visit(n);
  return hit;
}
/** Whether a forEach call leaves its callback no way to reach the list it walks. forEach hands the callback the list
 *  itself as its third argument (and as `this` when forEach is given a second argument), and reads each element only when
 *  it reaches it, so a callback that can reach the list can rewrite a later element before its pass:
 *  ["click", "keydown"].forEach((k, i, a) => { a[1] = "message"; window.addEventListener(k, f); }) registers a message
 *  listener. Sealed: the callback is forEach's one argument, a function written in place that declares at most one
 *  parameter, a plain name with no default; and, unless it is an arrow function, it mentions neither `arguments` (which
 *  aliases its parameters in a sloppy-mode script and holds the list as arguments[2]) nor `this`. An arrow function has
 *  no arguments object and no `this` of its own: both are its enclosing function's, which a list the census reads never
 *  reaches (an array literal written at the call, or a const whose every mention is a loop's list or a sealed forEach's
 *  receiver, listOf). */
function sealedForEach(call: any): boolean {
  if (!ts.isCallExpression(call) || call.arguments.length !== 1) return false;
  const fn = unwrap(call.arguments[0]);
  if (!ts.isArrowFunction(fn) && !ts.isFunctionExpression(fn)) return false;
  if (fn.parameters.length > 1 || fn.parameters.some((q: any) => q.initializer || q.dotDotDotToken || !ts.isIdentifier(q.name))) return false;
  return ts.isArrowFunction(fn) || !(mentionsName(fn, "arguments") || mentionsThis(fn));
}
/** Whether anything inside `scope` writes the name `name`: an assignment whose target mentions it, a ++ or --, or a
 *  for...in or for...of that assigns it on each pass. */
function writesName(scope: any, name: string): boolean {
  const mentions = (n: any): boolean => { let hit = ts.isIdentifier(n) && n.text === name; if (!hit) ts.forEachChild(n, (c: any) => { if (!hit && mentions(c)) hit = true; }); return hit; };
  let hit = false;
  const visit = (n: any): void => {
    if (hit) return;
    if (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment && mentions(n.left)) hit = true;
    if ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken) && mentions(n.operand)) hit = true;
    if ((ts.isForInStatement(n) || ts.isForOfStatement(n)) && !ts.isVariableDeclarationList(n.initializer) && mentions(n.initializer)) hit = true;
    ts.forEachChild(n, visit);
  };
  visit(scope);
  return hit;
}
/** The strings a list holds: an array literal of string literals, or a const initialised to one that is not exported and
 *  whose every other mention in the file is a for...of's list or the receiver of a forEach whose callback cannot reach
 *  the list (sealedForEach); else null. */
function listOf(e: any, sf: any): string[] | null {
  e = unwrap(e);
  if (ts.isArrayLiteralExpression(e)) return e.elements.every((x: any) => ts.isStringLiteralLike(x)) ? e.elements.map((x: any) => x.text) : null;
  if (!ts.isIdentifier(e)) return null;
  const d = declOf(e);
  if (!d || !isConstDecl(d) || !ts.isIdentifier(d.name) || isExported(d.parent.parent) || !d.initializer || !ts.isArrayLiteralExpression(unwrap(d.initializer))) return null;
  let onlyAsList = true;
  const visit = (n: any): void => {
    if (!onlyAsList) return;
    if (ts.isIdentifier(n) && n.text === d.name.text && n !== d.name && declOf(n) === d) {
      const m = outer(n), p = m.parent;
      const call = ts.isPropertyAccessExpression(p) ? outer(p).parent : null;
      onlyAsList = (ts.isForOfStatement(p) && p.expression === m)
        || (ts.isPropertyAccessExpression(p) && p.expression === m && p.name.text === "forEach" && !!call && ts.isCallExpression(call) && call.expression === outer(p)
            && sealedForEach(call));
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return onlyAsList ? listOf(d.initializer, sf) : null;
}
/** The string a ui/ module exports under `name` as `export const name = "..."`, or null. */
function exportedString(mod: string, name: string): string[] | null {
  for (const ext of [".ts", ".js"]) {
    const p = path.join(UI, mod + ext);
    if (!fs.existsSync(p)) continue;
    const sf = ts.createSourceFile(p, fs.readFileSync(p, "utf8"), ts.ScriptTarget.Latest, true, ext === ".ts" ? ts.ScriptKind.TS : ts.ScriptKind.JS);
    for (const st of sf.statements) {
      if (!ts.isVariableStatement(st) || !isExported(st) || !(st.declarationList.flags & ts.NodeFlags.Const)) continue;
      const d = st.declarationList.declarations.find((x: any) => ts.isIdentifier(x.name) && x.name.text === name);
      if (d && d.initializer && ts.isStringLiteralLike(unwrap(d.initializer))) return [unwrap(d.initializer).text];
    }
    return null;
  }
  return null;
}
/** The event types a registration's type argument can be, read by the parser (the shapes the comment above lists), or null. */
function eventTypes(e: any, sf: any, file: string, depth = 0): string[] | null {
  e = unwrap(e);
  if (ts.isStringLiteralLike(e)) return [e.text];
  if (!ts.isIdentifier(e) || depth > 4) return null;
  const d = declOf(e);
  if (!d) return null;
  if (isConstDecl(d) && ts.isIdentifier(d.name)) {
    const loop = d.parent.parent;
    if (ts.isForOfStatement(loop) && loop.initializer === d.parent) return listOf(loop.expression, sf);
    return d.initializer ? eventTypes(d.initializer, sf, file, depth + 1) : null;
  }
  if (ts.isParameter(d) && ts.isIdentifier(d.name)) {
    const fn = d.parent, call = outer(fn).parent;
    if (fn.parameters[0] !== d || writesName(fn, d.name.text)) return null;
    // the callback must have no way to reach the list (sealedForEach): one that can rewrites an element before its pass
    if (!call || !ts.isCallExpression(call) || call.arguments[0] !== outer(fn) || !sealedForEach(call)) return null;
    const callee = unwrap(call.expression);
    return ts.isPropertyAccessExpression(callee) && callee.name.text === "forEach" ? listOf(callee.expression, sf) : null;
  }
  if (ts.isImportSpecifier(d)) {
    const from = d.parent.parent.parent.moduleSpecifier.text;
    return from.startsWith("./") ? exportedString(path.posix.join(path.posix.dirname(file), from), (d.propertyName || d.name).text) : null;
  }
  return null;
}
type LooseAdd = { file: string; line: number; why: string; text: string };
/** Every addEventListener in `src` that is none of the shapes the comment above lists, and how many it read. */
function looseAddTokens(file: string, src: string): { read: number; loose: LooseAdd[] } {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, file.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
  const loose: LooseAdd[] = [];
  let read = 0;
  const refuse = (n: any, why: string): void => {
    loose.push({ file, line: sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1, why,
                 text: src.slice(Math.max(0, n.getStart(sf) - 30), Math.min(src.length, n.getEnd() + 40)).replace(/\s+/g, " ") });
  };
  const check = (tok: any): void => {
    const p = tok.parent;
    if (MEMBER_NAMES.includes(p.kind) && p.name === tok) return;   // a member's name
    if (ts.isStringLiteralLike(tok) && ts.isBinaryExpression(p) && p.operatorToken.kind === ts.SyntaxKind.InKeyword && p.left === tok) return;   // "addEventListener" in x
    let acc: any = null;
    if (ts.isPropertyAccessExpression(p) && p.name === tok) acc = p;
    else if (ts.isElementAccessExpression(p) && p.argumentExpression === tok) acc = p;
    else if (ts.isIdentifier(tok) && ts.isCallExpression(outer(tok).parent) && outer(tok).parent.expression === outer(tok)) acc = tok;   // a bare call
    if (!acc) return refuse(tok, "not the method called or tested: in a " + ts.SyntaxKind[p.kind]);
    const m = outer(acc), call = m.parent;
    if (ts.isCallExpression(call) && call.expression === m) {
      const arg = call.arguments[0];
      if (arg && ts.isStringLiteralLike(arg)) return;
      const types = arg ? eventTypes(arg, sf, file) : null;
      if (!types) return refuse(acc, "a call whose event type the census cannot read");
      if (types.includes("message")) return refuse(acc, "a message listener whose event type is not a string literal");
      return;
    }
    if (onlyTested(acc)) return;
    refuse(acc, "the method reached, not called with its event type: in a " + ts.SyntaxKind[call.kind]);
  };
  const visit = (n: any): void => {
    if ((ts.isIdentifier(n) || ts.isStringLiteralLike(n)) && n.text === "addEventListener") { read++; check(n); }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return { read, loose };
}

test("census: every addEventListener in ui/ is a direct call the census reads (its event type a literal, or strings that are not \"message\"), a read that is only tested, or a member's name", () => {
  const bad: string[] = [];
  const readIn = new Map<string, number>();
  for (const f of uiSources()) {
    const src = fs.readFileSync(path.join(UI, f), "utf8");
    if (!src.includes("addEventListener")) continue;
    const { read, loose } = looseAddTokens(f, src);
    readIn.set(f, read);
    for (const l of loose) bad.push(l.file + ":" + l.line + ": " + l.why + ": " + l.text);
  }
  // the census read the files the shapes above come from: every gated site's, a for...of over a const list (actions.ts), a
  // forEach callback (gear.js), imported event names (palette-main.ts), member names (test-dom-shim.ts), a tested read
  // ahead of a call (romp-timeline-view.js)
  for (const f of [...GATED.map(([g]) => g), "webview/actions.ts", "webview/render.ts", "test-dom-shim.ts", "romp-timeline-view.js"]) {
    assert.ok((readIn.get(f) || 0) > 0, "the census read the addEventListener mentions in " + f);
  }
  assert.deepEqual(bad, [], "an addEventListener in ui/ that the message census cannot read (a call or apply, an alias or a bound copy, " +
    "a destructured name, or an event type it cannot resolve): register with a string literal, or with a type the parser resolves\n" + bad.join("\n"));
});

test("the addEventListener census reads what it claims: every way around the literal is refused, and the resolved shapes and tested reads are accepted", () => {
  const loose = (src: string) => looseAddTokens("webview/probe.ts", src).loose.map((l) => l.why);
  const refused = [
    "EventTarget.prototype.addEventListener.call(window, \"message\", f);",
    "window.addEventListener.apply(window, [\"message\", f]);",
    "const add = window.addEventListener.bind(window); add(\"message\", f);",
    "const add = window.addEventListener; add(\"message\", f);",
    "const { addEventListener } = window; addEventListener(\"message\", f);",
    "(0, window.addEventListener)(\"message\", f);",
    "Reflect.apply(window.addEventListener, window, [\"message\", f]);",
    "window[\"addEventListener\"].call(window, \"message\", f);",
    "const k = \"addEventListener\"; (window as any)[k](\"message\", f);",
    "const on = x && x.addEventListener; on(\"message\", f);",
    "let T = \"message\"; window.addEventListener(T, f);",
    "const T = \"message\"; window.addEventListener(T, f);",
    "window.addEventListener((\"message\" as any), f);",
    "window.addEventListener(type, f);",
    "for (const t of [\"click\", \"message\"]) window.addEventListener(t, f);",
    "for (let t of [\"click\"]) { t = \"message\"; window.addEventListener(t, f); }",
    "const L = [\"click\"]; L.push(\"message\"); for (const t of L) window.addEventListener(t, f);",
    "export const L = [\"click\"]; for (const t of L) window.addEventListener(t, f);",
    "[\"click\"].forEach(function (k) { k = \"message\"; window.addEventListener(k, f); });",
    "[\"click\"].forEach(function (a, k) { window.addEventListener(k, f); });",
    "import { NOT_EXPORTED_HERE } from \"./keybindings\"; window.addEventListener(NOT_EXPORTED_HERE, f);",
    // a var anywhere in the enclosing function binds the name for the whole function, over an outer const
    "const EV7 = \"click\"; function g7(x: boolean) { if (x) { var EV7 = \"message\"; } window.addEventListener(EV7, f); } g7(true);",
    "const T = \"click\"; function g() { for (var T of [\"message\"]) { /* */ } window.addEventListener(T, f); }",
    "const T = \"click\"; function g() { if (f) { function T() { /* */ } } window.addEventListener(T, f); }",
    // a forEach callback's parameter rewritten through its arguments object, a for...in, or a redeclaring var
    "[\"click\"].forEach(function (k) { arguments[0] = \"message\"; window.addEventListener(k, f); });",
    "[\"click\"].forEach(function (k) { var a = arguments; a[0] = \"message\"; window.addEventListener(k, f); });",
    "[\"click\"].forEach(function (k) { for (k in { message: 1 }) window.addEventListener(k, f); });",
    "[\"click\"].forEach(function (k) { if (f) { var k = \"message\"; } window.addEventListener(k, f); });",
    // forEach hands its callback the list (third argument, arguments[2], or `this` when named), and reads each element
    // only on its pass, so a callback that reaches the list rewrites a later element first
    "[\"click\", \"keydown\"].forEach((k, i, a) => { a[1] = \"message\"; window.addEventListener(k, f); });",
    "[\"click\", \"keydown\"].forEach(function (k, i) { window.addEventListener(k, f); });",
    "const L = [\"click\", \"keydown\"]; [\"click\", \"keydown\"].forEach(function (k) { this[1] = \"message\"; window.addEventListener(k, f); }, L);",
    "[\"click\", \"keydown\"].forEach(function (k) { use(this); window.addEventListener(k, f); });",
    "[\"click\", \"keydown\"].forEach((k) => { window.addEventListener(k, f); }, other);",
    "[\"click\", \"keydown\"].forEach((k = \"message\") => { window.addEventListener(k, f); });",
    "[\"click\", \"keydown\"].forEach(cb); function cb(k: string) { window.addEventListener(k, f); }",
    // a const list walked by another forEach whose callback reaches it, and then read by a loop
    "const L = [\"click\", \"keydown\"]; L.forEach((x, i, a) => { a[1] = \"message\"; }); for (const t of L) window.addEventListener(t, f);",
    "const L = [\"click\", \"keydown\"]; L.forEach(function (x) { arguments[2][1] = \"message\"; }); L.forEach((t) => window.addEventListener(t, f));",
  ];
  for (const src of refused) assert.ok(loose(src).length >= 1, "refused: " + src);
  // a with statement answers a name from its object (a script's, so read as one)
  const looseJs = (src: string) => looseAddTokens("webview/probe.js", src).loose.map((l) => l.why);
  for (const src of ["const T = 'click'; with ({ T: 'message' }) window.addEventListener(T, f);",
                     "['click'].forEach(function (k) { with ({ k: 'message' }) { window.addEventListener(k, f); } });"]) {
    assert.ok(looseJs(src).length >= 1, "refused: " + src);
  }
  assert.deepEqual(looseJs("const T = 'click'; with (o) { g(); } window.addEventListener(T, f);"), [], "a with statement elsewhere changes nothing");
  const accepted = [
    "window.addEventListener(\"message\", f); el.addEventListener('click', f); window[\"addEventListener\"](`resize`, f);",
    "x.addEventListener?.(\"load\", f);",
    "for (const ev of [\"mousedown\", \"touchstart\"]) document.addEventListener(ev, f, true);",
    "const R = [\"pointerup\", \"pointercancel\"]; for (const t of R) el.addEventListener(t, f); for (const t of R) el.removeEventListener(t, f);",
    "['wheel', 'keydown'].forEach(function (k) { window.addEventListener(k, f); });",
    "import { KEYS_EVENT } from \"./keybindings\"; window.addEventListener(KEYS_EVENT, f);",
    "const T = \"romp:local\"; window.addEventListener(T, f);",
    "if (typeof x.addEventListener === \"function\") x.addEventListener(\"load\", f);",
    "if (doc && doc.addEventListener) doc.addEventListener(\"visibilitychange\", f);",
    "const ok = !!(x && x.addEventListener); const has = \"addEventListener\" in x;",
    "const o = { addEventListener(t: string, g: unknown) { return [t, g]; } }; type T = { addEventListener(type: string): void };",
    "const s = \"call addEventListener here\"; // addEventListener in a comment",
    // a var in a nested function is that function's own; an arrow callback has no arguments object of its own
    "const T = \"click\"; function g() { function h() { var T = \"message\"; return T; } window.addEventListener(T, f); return h; }",
    "function g() { [\"click\"].forEach((k) => { use(arguments); window.addEventListener(k, f); }); }",
    "class C { m() { [\"click\"].forEach((k) => { use(this); window.addEventListener(k, f); }); } }",
    "const L = [\"pointerup\", \"pointercancel\"]; L.forEach((t) => el.addEventListener(t, f)); for (const t of L) el.removeEventListener(t, f);",
    "const T = \"click\"; function g() { { const T = \"keydown\"; window.addEventListener(T, f); } }",
  ];
  for (const src of accepted) assert.deepEqual(loose(src), [], "accepted: " + src);
});

// ── the census: no other road to a window listener ──
//
// The censuses above read what the source spells: an addEventListener call, an onmessage assignment, the names they
// reach. More roads reach a window listener without spelling either, and this census refuses each in a ui/ source file
// (tests excluded), read by the TypeScript parser:
//   - a method of the window read by a name computed at run time. The window (windowRef) is window, self, globalThis and
//     the windows a script can name (frames, which is the window itself; top; parent; opener), unshadowed, and any of them
//     reached through another (window.frames, parent.top); a document's defaultView and a frame's contentWindow, whatever
//     holds them; a local initialised to any of these, or destructured from one (const { frames: w } = window); and
//     `this` where it is the global object (a plain function's or the file's own `this`, outside any class or method). A
//     prototype holds the same methods (protoRef): every DOM interface's chain ends at EventTarget.prototype, which holds
//     addEventListener, so X.prototype for any X, any __proto__, and what Object.getPrototypeOf or Reflect.getPrototypeOf
//     returns count with the window. Refused on either: a member read by a computed name (window["add" + "EventListener"],
//     a template, a variable key), whether called, assigned or read; Reflect.get, Reflect.getOwnPropertyDescriptor or
//     Object.getOwnPropertyDescriptor with a key that is not a literal, and Object.getOwnPropertyDescriptors, which hands
//     on every member under its name; a destructuring pattern with a computed key (const { [k]: add } = window); and a
//     reflective write whose key or keys are computed (Reflect.set, Reflect.defineProperty, Object.defineProperty or
//     __defineSetter__ with a key that is not a literal; Object.assign or Object.defineProperties from an object literal
//     with a computed key or a spread; a new prototype for the window);
//   - a function run with the window as its `this`, however the function was reached: .call, .apply or .bind with the
//     window named as the first argument (or the second, on a .call or .apply of .call or .apply), and Reflect.apply with
//     the window as its second. A method of any other EventTarget (an element, the document) read by a computed name
//     registers on the window this way, or with no receiver at all (below). `this` does not count as the window here:
//     a wrapper passes its own `this` on (md-block-start.ts's, which marked calls with its lexer), and that is disclosed;
//   - an onmessage handler set any way but a plain assignment the census above reads: the name onmessage may be an
//     assignment's target (x.onmessage = f; on the window that is a census site), a member of a type, or a read that is
//     only tested, and nothing else (Object.assign(window, { onmessage: f }), Reflect.set(window, "onmessage", f),
//     window.onmessage ??= f are refused);
//   - code run from a string: eval, the Function constructor (by name, or reached through a function's .constructor),
//     and setTimeout or setInterval handed a string.
// ui/ has none of these today, so the rules cost nothing. What they cannot see, disclosed:
//   - the window held where no initialiser shows it: in a parameter, in a let or var assigned later, behind a comma,
//     conditional, || or ?? expression, in a Proxy, in an object or array it was put in, or returned by a function;
//   - a method of another EventTarget (an element, the document) read by a computed name and called with no receiver:
//     WebIDL runs an operation called with no `this` on the global object, so `const add = document.body[k];
//     add("message", f)` registers on the window; and such a method run on `this` where `this` is the window;
//   - a reflective function under another name (const R = Reflect; R.get(window, k)), and a Function.prototype.call
//     reached any way but by name;
//   - an object built elsewhere with a computed key and copied onto the window (Object.assign(window, make()) is read as
//     its call only), and a key computed in another module and passed to a reflective read or write through a helper;
//   - code handed to the DOM as markup or a URL (a script element, an inline handler attribute, a javascript: URL),
//     which is no JavaScript the parser reads.

/** The names a script reaches a window by: its own (window, self, globalThis) and the windows it can name (frames, which
 *  is the window itself; top; parent; opener). */
const WINDOW_GLOBALS = new Set(["window", "self", "globalThis", "frames", "top", "parent", "opener"]);
/** The members that are a window whatever holds them: a document's window and a frame's. */
const WINDOW_MEMBERS = new Set(["defaultView", "contentWindow"]);
/** The name of `x.name`, or of `x["name"]` with a literal key; else null. */
const memberName = (n: any): string | null => ts.isPropertyAccessExpression(n) ? n.name.text
  : ts.isElementAccessExpression(n) && n.argumentExpression && ts.isStringLiteralLike(n.argumentExpression) ? n.argumentExpression.text : null;
/** Whether `n` is a window: one of WINDOW_GLOBALS unshadowed, one of them reached through another (window.frames,
 *  parent.top), a WINDOW_MEMBERS member of anything (document.defaultView), a local initialised to any of these or
 *  destructured from one (const { frames: w } = window; const { defaultView } = document), or, unless `noThis`, `this`
 *  where it is the global object. */
function windowRef(n: any, depth = 0, noThis = false): boolean {
  n = unwrap(n);
  if (depth > 4) return false;
  if (n.kind === ts.SyntaxKind.ThisKeyword) {
    if (noThis) return false;
    for (let s = n.parent; s; s = s.parent) {
      if (ts.isArrowFunction(s)) continue;
      if (ts.isClassLike(s) || ts.isMethodDeclaration(s) || ts.isConstructorDeclaration(s) || ts.isGetAccessor(s) || ts.isSetAccessor(s)
          || ts.isClassStaticBlockDeclaration(s) || ts.isPropertyDeclaration(s)) return false;
      if (ts.isFunctionDeclaration(s) || ts.isFunctionExpression(s)) return !(ts.isPropertyAssignment(outer(s).parent) || ts.isObjectLiteralExpression(outer(s).parent));
      if (ts.isSourceFile(s)) return true;
    }
    return false;
  }
  const name = memberName(n);
  if (name !== null) return WINDOW_MEMBERS.has(name) || (WINDOW_GLOBALS.has(name) && windowRef(n.expression, depth + 1, noThis));
  if (!ts.isIdentifier(n)) return false;
  const d = declOf(n);
  if (!d) return WINDOW_GLOBALS.has(n.text);
  if (!ts.isVariableDeclaration(d) || !d.initializer) return false;
  if (ts.isIdentifier(d.name)) return windowRef(d.initializer, depth + 1, noThis);
  return windowFromPattern(d.name, n.text, windowRef(d.initializer, depth + 1, noThis));
}
/** Whether destructuring `pattern` (from a window, when `fromWindow`) binds `name` to a window: under a WINDOW_GLOBALS key
 *  of a window, or a WINDOW_MEMBERS key of anything, at any depth. */
function windowFromPattern(pattern: any, name: string, fromWindow: boolean): boolean {
  if (!ts.isObjectBindingPattern(pattern)) return false;
  for (const e of pattern.elements) {
    const key = e.propertyName ? (ts.isIdentifier(e.propertyName) || ts.isStringLiteralLike(e.propertyName) ? e.propertyName.text : null)
      : (ts.isIdentifier(e.name) ? e.name.text : null);
    const isWindow = key !== null && (WINDOW_MEMBERS.has(key) || (fromWindow && WINDOW_GLOBALS.has(key)));
    if (ts.isIdentifier(e.name)) { if (e.name.text === name) return isWindow; }
    else if (bindsName(e.name, name)) return windowFromPattern(e.name, name, isWindow);
  }
  return false;
}
/** The dotted name of a callee (Reflect.set, setTimeout, window.setTimeout, Reflect["get"]), or "". */
const calleeName = (c: any): string => {
  c = unwrap(c);
  if (ts.isIdentifier(c)) return c.text;
  const m = memberName(c);
  if (m !== null) { const r = calleeName(c.expression); return r ? r + "." + m : ""; }
  return "";
};
/** A callee's dotted name with any leading window, self or globalThis taken off: window.Reflect.get is Reflect.get. */
const globalName = (c: any): string => calleeName(c).replace(/^((window|self|globalThis)\.)+/, "");
const PROTO_READS = new Set(["Object.getPrototypeOf", "Reflect.getPrototypeOf"]);
/** Whether `n` is a prototype, which holds the methods its objects share: X.prototype for any X, any __proto__, or what
 *  Object.getPrototypeOf or Reflect.getPrototypeOf returns. Every DOM interface's chain ends at EventTarget.prototype,
 *  which holds addEventListener, and a method read off it runs on the window as well as on the object it came from. */
function protoRef(n: any): boolean {
  n = unwrap(n);
  const name = memberName(n);
  if (name === "prototype" || name === "__proto__") return true;
  return ts.isCallExpression(n) && PROTO_READS.has(globalName(n.expression));
}
/** Whether a member read off `n` can be a window's method: `n` is a window or a prototype. */
const holdsWindowMethods = (n: any): boolean => windowRef(n) || protoRef(n);
const isLiteralKey = (k: any): boolean => !!k && (ts.isStringLiteralLike(unwrap(k)) || ts.isNumericLiteral(unwrap(k)));
/** Whether a destructuring pattern (a binding pattern, or an object literal an assignment destructures into) names a key
 *  computed at run time anywhere inside it. */
function computedKeyIn(pattern: any): boolean {
  let hit = false;
  const visit = (c: any): void => { if (hit) return; if (ts.isComputedPropertyName(c) && !isLiteralKey(c.expression)) hit = true; else ts.forEachChild(c, visit); };
  visit(pattern);
  return hit;
}
const REFLECT_READ = new Set(["Reflect.get", "Reflect.getOwnPropertyDescriptor", "Object.getOwnPropertyDescriptor"]);
const REFLECT_READ_ALL = new Set(["Object.getOwnPropertyDescriptors"]);
const REFLECT_KEYED = new Set(["Reflect.set", "Reflect.defineProperty", "Object.defineProperty"]);
const REFLECT_SPREAD = new Set(["Object.assign", "Object.defineProperties"]);
const REFLECT_PROTO = new Set(["Object.setPrototypeOf", "Reflect.setPrototypeOf"]);
const RUN_ON = new Set(["call", "apply", "bind"]);
/** Every road in `src` the comment above lists, with where it is and why, and how many onmessage names it read. */
function looseRoads(file: string, src: string): { onmessage: number; loose: LooseAdd[] } {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, file.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
  const loose: LooseAdd[] = [];
  let onmessage = 0;
  const refuse = (n: any, why: string): void => {
    loose.push({ file, line: sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1, why,
                 text: src.slice(Math.max(0, n.getStart(sf) - 30), Math.min(src.length, n.getEnd() + 40)).replace(/\s+/g, " ") });
  };
  const inType = (n: any): boolean => { for (let s = n.parent; s; s = s.parent) { if (ts.isTypeNode(s) || ts.isHeritageClause(s) && ts.isInterfaceDeclaration(s.parent)) return true; if (ts.isStatement(s) || ts.isExpression(s) && !ts.isIdentifier(s)) return false; } return false; };
  const onmessageToken = (tok: any): void => {
    const p = tok.parent;
    if ((ts.isPropertySignature(p) || ts.isMethodSignature(p)) && p.name === tok) return;   // a member of a type
    if (ts.isStringLiteralLike(tok) && ts.isBinaryExpression(p) && p.operatorToken.kind === ts.SyntaxKind.InKeyword && p.left === tok) return;
    let acc: any = null;
    if (ts.isPropertyAccessExpression(p) && p.name === tok) acc = p;
    else if (ts.isElementAccessExpression(p) && p.argumentExpression === tok) acc = p;
    else if (ts.isIdentifier(tok) && !ts.isPropertyAccessExpression(p)) acc = tok;   // the bare global
    if (acc) {
      const m = outer(acc), q = m.parent;
      if (ts.isBinaryExpression(q) && q.operatorToken.kind === ts.SyntaxKind.EqualsToken && q.left === m) return;   // x.onmessage = f
      if (onlyTested(acc)) return;
    }
    refuse(tok, "an onmessage handler set some way other than an assignment the census reads");
  };
  const visit = (n: any): void => {
    if ((ts.isIdentifier(n) || ts.isStringLiteralLike(n)) && n.text === "onmessage") { onmessage++; onmessageToken(n); }
    if (ts.isElementAccessExpression(n) && !isLiteralKey(n.argumentExpression) && holdsWindowMethods(n.expression)) {
      refuse(n, "a member of the window or of a prototype reached by a computed name, which the censuses cannot read");
    }
    if ((ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isBindingElement(n)) && n.initializer && ts.isObjectBindingPattern(n.name)
        && holdsWindowMethods(n.initializer) && computedKeyIn(n.name)) {
      refuse(n, "a member of the window or of a prototype destructured by a computed key, which the censuses cannot read");
    }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isObjectLiteralExpression(unwrap(n.left))
        && holdsWindowMethods(n.right) && computedKeyIn(unwrap(n.left))) {
      refuse(n, "a member of the window or of a prototype destructured by a computed key, which the censuses cannot read");
    }
    if (ts.isIdentifier(n) && n.text === "eval" && !inType(n)) refuse(n, "eval, which runs code from a string");
    if (ts.isStringLiteralLike(n) && (n.text === "eval" || n.text === "Function") && ts.isElementAccessExpression(n.parent) && n.parent.argumentExpression === n) {
      refuse(n, "eval or the Function constructor by a computed member, which runs code from a string");
    }
    if (ts.isIdentifier(n) && n.text === "Function" && !inType(n)) refuse(n, "the Function constructor, which runs code from a string");
    if ((ts.isIdentifier(n) || ts.isStringLiteralLike(n)) && n.text === "constructor") {
      const acc = ts.isPropertyAccessExpression(n.parent) && n.parent.name === n ? n.parent
        : ts.isElementAccessExpression(n.parent) && n.parent.argumentExpression === n ? n.parent : null;
      if (acc) {
        const m = outer(acc), q = m.parent;
        const readsName = ts.isPropertyAccessExpression(q) && q.expression === m && q.name.text === "name";
        if (!readsName && !onlyTested(acc)) refuse(n, "a function's constructor reached, which is the Function constructor and runs code from a string");
      }
    }
    if (ts.isCallExpression(n) || ts.isNewExpression(n)) {
      const base = globalName(n.expression), args = n.arguments || [];
      if ((base === "setTimeout" || base === "setInterval") && args[0]) {
        const a = unwrap(args[0]);
        const stringy = (x: any): boolean => ts.isStringLiteralLike(x) || ts.isTemplateExpression(x) || ts.isBinaryExpression(x) && x.operatorToken.kind === ts.SyntaxKind.PlusToken;
        const strings = stringy(a) || ts.isIdentifier(a) && (() => { const d = declOf(a); return !!d && ts.isVariableDeclaration(d) && !!d.initializer && stringy(unwrap(d.initializer)); })();
        if (strings) refuse(n, base + " handed a string, which it runs as code");
      }
      if (args[0] && holdsWindowMethods(args[0])) {
        if (REFLECT_READ.has(base) && !isLiteralKey(args[1])) refuse(n, base + " of the window or of a prototype with a computed key, which the censuses cannot read");
        if (REFLECT_READ_ALL.has(base)) refuse(n, base + " of the window or of a prototype, which hands on every member under its name");
        if (REFLECT_KEYED.has(base) && !isLiteralKey(args[1])) refuse(n, base + " onto the window or a prototype with a computed key, which the censuses cannot read");
        if (REFLECT_SPREAD.has(base)) {
          for (const a of args.slice(1)) {
            const o = unwrap(a);
            if (ts.isObjectLiteralExpression(o) && o.properties.some((pr: any) => ts.isSpreadAssignment(pr) || pr.name && ts.isComputedPropertyName(pr.name) && !isLiteralKey(pr.name.expression))) {
              refuse(n, base + " onto the window or a prototype from an object with a computed key or a spread, which the censuses cannot read");
            }
          }
        }
        if (REFLECT_PROTO.has(base)) refuse(n, base + " on the window or a prototype, which replaces what its methods are");
      }
      const c = unwrap(n.expression), run = memberName(c);
      if (ts.isCallExpression(n) && run !== null && RUN_ON.has(run)) {
        // f.call(window, ...), f.apply(window, [...]), f.bind(window); and f.call.call(g, window, ...), which runs g on it
        const onCall = RUN_ON.has(memberName(unwrap(c.expression)) || "");
        if ((args[0] && windowRef(args[0], 0, true)) || (onCall && args[1] && windowRef(args[1], 0, true))) {
          refuse(n, "a function run with the window as its this (." + run + "), which the censuses cannot read");
        }
      }
      if (base === "Reflect.apply" && args[1] && windowRef(args[1], 0, true)) refuse(n, "Reflect.apply with the window as its this, which the censuses cannot read");
      if ((run === "__defineSetter__" || run === "__defineGetter__") && holdsWindowMethods(c.expression) && !isLiteralKey(args[0])) {
        refuse(n, run + " on the window or a prototype with a computed key, which the censuses cannot read");
      }
    }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      const l = unwrap(n.left);
      if (memberName(l) === "__proto__" && windowRef(l.expression)) refuse(n, "a new prototype for the window, which replaces what its methods are");
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return { onmessage, loose };
}

test("census: no ui/ source reaches a window listener by a computed name, runs a function with the window as its this, sets an onmessage handler other than by an assignment the census reads, or runs code from a string", () => {
  const bad: string[] = [];
  const readIn = new Map<string, number>();
  for (const f of uiSources()) {
    const { onmessage, loose } = looseRoads(f, fs.readFileSync(path.join(UI, f), "utf8"));
    readIn.set(f, onmessage);
    for (const l of loose) bad.push(l.file + ":" + l.line + ": " + l.why + ": " + l.text);
  }
  assert.ok((readIn.get("webview/federation.ts") || 0) >= 2, "the census read federation.ts, whose sockets' onmessage handlers are assignments it accepts");
  assert.deepEqual(bad, [], "a road to a window listener the censuses cannot read: spell the registration so they can\n" + bad.join("\n"));
});

test("the road census reads what it claims: every road around the spelled registration is refused, and a socket's handler, a literal member and code that is no road are accepted", () => {
  const roads = (src: string, file = "webview/probe.ts") => looseRoads(file, src).loose.map((l) => l.why);
  const refused: Array<[string, string?]> = [
    ["window[\"add\" + \"EventListener\"](\"message\", f);"],
    ["window[`add${\"Event\"}Listener`](\"message\", f);"],
    ["const k = pick(); (window as any)[k](\"message\", f);"],
    ["self[name](\"message\", f);"],
    ["const w = window as any; w[\"on\" + \"message\"] = f;"],
    ["globalThis.window[k] = f;"],
    ["(function () { this[k](\"message\", f); })();", "webview/probe.js"],
    ["this[\"on\" + \"message\"] = f;", "webview/probe.js"],
    ["Object.assign(window, { onmessage: f });"],
    ["Reflect.set(window, \"onmessage\", f);"],
    ["Object.defineProperty(window, \"onmessage\", { value: f });"],
    ["window.onmessage ??= f;"],
    ["window.onmessage ||= f;"],
    ["[window.onmessage] = [f];"],
    ["const h = { onmessage: f }; Object.assign(window, h);"],
    ["Reflect.set(window, key, f);"],
    ["Reflect.defineProperty(self, \"on\" + \"message\", { value: f });"],
    ["Object.defineProperty(window, k, { value: f });"],
    ["Object.assign(window, { [k]: f });"],
    ["Object.defineProperties(window, { ...defs });"],
    ["Object.setPrototypeOf(window, proto);"],
    ["(window as any).__proto__ = proto;"],
    ["(window as any).__defineSetter__(k, f);"],
    ["eval(\"window.onmessage = f\");"],
    ["(0, eval)(code);"],
    ["window.eval(code);"],
    ["const run = eval; run(code);"],
    ["new Function(\"e\", code);"],
    ["Function(code)();"],
    ["window[\"Function\"](code)();"],
    ["(function () { /* */ }).constructor(code)();"],
    ["const F = (async () => 0).constructor; new F(code);"],
    ["setTimeout(\"window.onmessage = f\", 0);"],
    ["window.setInterval(`go(${x})`, 10);"],
    ["setTimeout(\"go(\" + x + \")\", 0);"],
    ["const code = \"go()\"; setTimeout(code, 0);"],
    // a window method read by a computed name without element access: Reflect.get, a destructuring pattern, a descriptor
    // off the prototype that holds it (k is ["add", "Event", "Listener"].join(""))
    ["Reflect.get(window, k).call(window, \"message\", f);"],
    ["const reg = Reflect.get(window, k); reg(\"message\", f);"],
    ["const { [k]: reg } = window; reg.call(window, \"message\", f);"],
    ["const { [k]: reg } = window; reg(\"message\", f);"],
    ["let reg; ({ [k]: reg } = window); reg(\"message\", f);"],
    ["function g({ [k]: reg }: any = window) { reg(\"message\", f); }"],
    ["const { document: { defaultView: { [k]: reg } } } = window; reg(\"message\", f);"],
    ["Object.getOwnPropertyDescriptor(EventTarget.prototype, k).value.call(window, \"message\", f);"],
    ["const add = Object.getOwnPropertyDescriptor(EventTarget.prototype, k)!.value; add(\"message\", f);"],
    ["Reflect.getOwnPropertyDescriptor(Window.prototype, k);"],
    ["Object.getOwnPropertyDescriptors(EventTarget.prototype)[k].value(\"message\", f);"],
    ["Reflect.get(Object.getPrototypeOf(window), k);"],
    ["Reflect[\"get\"](window, k);"],
    ["window.Reflect.get(self, k);"],
    // element access on another name for the window, or on a prototype
    ["frames[k](\"message\", f);"],
    ["document.defaultView[k](\"message\", f);"],
    ["el.ownerDocument.defaultView[k](\"message\", f);"],
    ["frame.contentWindow[k](\"message\", f);"],
    ["window.frames[k](\"message\", f);"],
    ["parent[k](\"message\", f);"],
    ["top[k](\"message\", f);"],
    ["window.parent.top[k](\"message\", f);"],
    ["opener[k](\"message\", f);"],
    ["const { frames: w } = window; w[k](\"message\", f);"],
    ["const { defaultView } = document; defaultView[k](\"message\", f);"],
    ["EventTarget.prototype[k].call(window, \"message\", f);"],
    ["const add = Node.prototype[k]; add(\"message\", f);"],
    ["Object.getPrototypeOf(document.body)[k](\"message\", f);"],
    ["document.body.__proto__[k](\"message\", f);"],
    ["Reflect.set(EventTarget.prototype, k, f);"],
    ["Object.defineProperty(Window.prototype, k, { value: f });"],
    // any function run with the window as its this, however it was reached
    ["document.body[k].call(window, \"message\", f);"],
    ["el[k].apply(self, [\"message\", f]);"],
    ["const add = document[k].bind(globalThis); add(\"message\", f);"],
    ["Reflect.apply(document[k], window, [\"message\", f]);"],
    ["g.call.call(document[k], window, \"message\", f);"],
    ["g.apply.call(document[k], window, [\"message\", f]);"],
    ["const w = window; g.call(w, \"message\", f);"],
  ];
  for (const [src, file] of refused) assert.ok(roads(src, file).length >= 1, "refused: " + src);
  const accepted: Array<[string, string?]> = [
    ["ws.onmessage = (ev: MessageEvent) => { go(ev.data); }; dead.onopen = dead.onmessage = dead.onclose = null;"],
    ["window.onmessage = f; self[\"onmessage\"] = g; onmessage = h;"],
    ["if (port.onmessage) go(); const has = \"onmessage\" in window; type T = { onmessage: ((e: unknown) => void) | null };"],
    ["window[\"addEventListener\"](\"resize\", f); const y = list[k]; w[k] = 1;"],
    ["function f(frames: any[], k: number) { return frames[k]; } const window2 = { a: 1 }; window2[k] = 1;"],
    ["class C { m() { return this[k]; } } const o = { m() { return this[k]; }, n: function () { return this[k]; } };"],
    ["Object.assign(window, bridgeFunctions(post)); Object.assign(window, { a: 1, \"b\": 2 });"],
    ["Object.defineProperty(window, \"__rompX\", { value: 1 }); Reflect.set(obj, k, v); Object.assign(target, { [k]: v });"],
    ["const tag = (o.constructor && o.constructor.name) || \"object\";"],
    ["setTimeout(() => go(), 0); setTimeout(tick, 10); window.setInterval(function () { go(); }, 5); const t = make(); setTimeout(t, 0);"],
    ["function g(f: Function) { return f; } interface I extends Function { x: 1 } // eval in a comment, and \"eval\" in a string"],
    ["const s = \"new Function\"; const evaluate = 1; const r = evaluate + 1;"],
    // a descriptor read off an object that is no window and no prototype (ui/test-dom-shim.ts), a local named frames or
    // parent, a class's own this, a wrapper passing its own this on (ui/webview/md-block-start.ts), a call on another object
    ["function h(n: object, k: string) { return Object.getOwnPropertyDescriptor(n, k); } const d = Reflect.get(obj, k);"],
    ["function p(parent: any, top: any[], k: number) { return [parent[k], top[k]]; } const frames: number[] = []; frames[k] = 1;"],
    ["const o = { defaultView: 1 }; const { [k]: v } = obj; ({ [k]: v } = other);"],
    ["const wrapped = function (this: object, ...a: unknown[]) { return orig.apply(this, a); };"],
    ["Object.prototype.hasOwnProperty.call(n, \"_nid\"); Array.prototype.forEach.call(nodes, g); g.bind(obj); frames[0].focus();"],
  ];
  for (const [src, file] of accepted) assert.deepEqual(roads(src, file), [], "accepted: " + src);
});

test("census: every gated site has an executed leg in this file (installed, or lifted by its marker)", () => {
  const legs = new Set<string>();
  const runs: string[] = [];                      // each leg's listener, with its arm when it names one
  const arms = new Map<string, boolean[]>();      // per listener: whether each of its legs names its arm
  const add = (s: Site, arm: string | undefined): void => {
    const k = s.file + ":" + s.line;
    legs.add(k);
    runs.push(arm ? k + " (" + arm + ")" : k);
    arms.set(k, [...(arms.get(k) || []), !!arm]);
  };
  for (const leg of INSTALLED) {
    if (leg.marker) { add(siteOf(leg.site, leg.marker), undefined); continue; }
    const ss = messageSites(leg.site);
    assert.equal(ss.length, 1, leg.site + " has one window message listener, or its installed leg names a marker");
    add(ss[0], undefined);
  }
  for (const leg of LIFTED) add(siteOf(leg.file, leg.marker), leg.arm);
  const sites = uiSources().flatMap(messageSites).map((s) => s.file + ":" + s.line);
  assert.deepEqual(sites.filter((s) => !legs.has(s)), [], "a window message listener with no executed leg here");
  assert.equal(runs.length, INSTALLED.length + LIFTED.length);
  assert.equal(new Set(runs).size, runs.length, "no two legs run the same arm of one listener: " + runs.join(", "));
  const unnamed = [...arms].filter(([, named]) => named.length > 1 && named.some((x) => !x)).map(([k]) => k);
  assert.deepEqual(unnamed, [], "a listener with more than one leg names each leg's arm");
});

test("the census rule reads what it claims: a listener that acts before the check, or has none, is refused; the check after reads of the message is accepted", () => {
  const probe = (text: string) => {
    const sf = ts.createSourceFile("probe.ts", "window.addEventListener(\"message\", " + text + ");", ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const call = (sf.statements[0] as any).expression;
    return headCheck({ file: "probe.ts", line: 1, receiver: "window", fn: call.arguments[1], text, kind: "addEventListener" });
  };
  assert.equal(probe('(e) => { if (windowSender(e) === "foreign") return; go(e.data); }'), null);
  assert.equal(probe('(e) => { const m = e.data; if (!m || m.type !== "x") return; if (windowSender(e) === "foreign") return; go(m); }'), null);
  assert.equal(probe("function (e) { if (windowSender(e) === 'foreign') return; var m = e.data; go(m); }"), null);
  assert.match(String(probe('(e) => { const m = e.data; go(m); if (windowSender(e) === "foreign") return; }')), /runs before the foreign-sender check/);
  assert.match(String(probe('(e) => { if (!e.data || note(e.data)) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "a call in an early return's condition is an arm");
  assert.match(String(probe('(e) => { const m = e.data; if (m) seen = m; if (windowSender(e) === "foreign") return; }')), /runs before/);
  assert.match(String(probe('(e) => { if (windowSender(e) !== "foreign") go(e.data); }')), /runs before|no `if/);
  assert.match(String(probe('(e) => { if (windowSender(other) === "foreign") return; go(e.data); }')), /runs before|no `if/, "the check reads this listener's event");
  assert.match(String(probe("(e) => go(e.data)")), /not a function with a body/);
  // a parameter's default runs before the body, the check included
  assert.match(String(probe('(e, early = go(e.data)) => { if (windowSender(e) === "foreign") return; }')), /more than its one event parameter/);
  assert.match(String(probe('(e: MessageEvent, _x = (e.data && e.data.on ? (seen = e.data.on) : 0)) => { if (windowSender(e) === "foreign") return; }')), /more than its one event parameter/);
  assert.match(String(probe('(e = go()) => { if (windowSender(e) === "foreign") return; }')), /gives it a default/);
  assert.match(String(probe('function (e, f) { if (windowSender(e) === "foreign") return; go(f); }')), /more than its one event parameter/);
  assert.match(String(probe('(...e) => { if (windowSender(e[0]) === "foreign") return; }')), /names no event parameter|more than/);
  assert.equal(probe('(e: MessageEvent) => { if (windowSender(e) === "foreign") return; go(e.data); }'), null, "a type on the one parameter is no default");
  // a listener handed over by name (sitesIn reads it at the function its const holds): the check at that function's head
  // passes; an arm ahead of it, or a name the census cannot read as such a const, is refused
  const byName = (src: string) => sitesIn("webview/probe.ts", src).map(headCheck);
  assert.deepEqual(byName('const h = (e: MessageEvent): void => { if (windowSender(e) === "foreign") return; go(e.data); }; window.addEventListener("message", h);'), [null]);
  assert.match(String(byName('const h = (e: MessageEvent): void => { const m = e.data; if (m.type === "hostUp") { up(); return; } if (windowSender(e) === "foreign") return; }; window.addEventListener("message", h);')[0]),
    /runs before/, "an arm ahead of the check in a named listener");
  assert.match(String(byName('const h = (e) => { if (windowSender(e) === "foreign") return; }; function f() { const h = (e) => { go(e.data); }; window.addEventListener("message", h); }')[0]),
    /runs before|no `if/, "the const the name binds at the call is the inner one, which has no check");
  assert.match(String(byName('const h = (e) => { go(e.data); }; { const h = (e) => { if (windowSender(e) === "foreign") return; }; } window.addEventListener("message", h);')[0]),
    /runs before|no `if/, "the const the name binds at the call is the outer one, which has no check");
  for (const src of [
    'let h = (e) => { if (windowSender(e) === "foreign") return; }; h = (e) => { go(e.data); }; window.addEventListener("message", h);',
    'var h = (e) => { if (windowSender(e) === "foreign") return; }; window.addEventListener("message", h);',
    'function h(e) { if (windowSender(e) === "foreign") return; } window.addEventListener("message", h);',
    'const h = wrap((e) => { if (windowSender(e) === "foreign") return; }); window.addEventListener("message", h);',
    'function f(h) { window.addEventListener("message", h); }',
    'const { h } = handlers; window.addEventListener("message", h);',
    'window.addEventListener("message", h);',
  ]) assert.match(String(byName(src)[0]), /a name no const holding a function written in place binds/, src);
});
