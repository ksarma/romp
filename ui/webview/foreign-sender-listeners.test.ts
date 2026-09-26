// Every window "message" listener in the webview bundles ignores a message from a foreign sender (window-sender.ts): a
// window that is not this document, not its embedder (the romp shell), not on this document's origin, and not this
// document's own dispatch of a kernel frame. The chat's frame handler got that check first (chat-foreign-frame.test.ts);
// this file holds it for the rest of the population:
//   - frame-listener.ts listenForFrames, the one window install every pane's frame handler shares (the feed, the Outline,
//     Waiting on you, the chat and the VS Code timeline): the window path hands the handler no message from a foreign
//     sender. The federation registry path is unchanged: only federation.js calls it, with a MessageEvent it built.
//   - every other window listener, each with its own check at its head: the Waiting pane's panes cache, the VS Code
//     settings sync, the shared file viewer, the file browser, the file-comments panel's replies, the gear's six
//     listeners, the shell palette's two, and the VS Code strip's.
// Each listener hears every class windowSender does not name foreign, which covers each one's real senders: the shell
// (the embedder of a pane; to the shell's own page, its panes are windows on its origin), this document (self), a window
// on the origin (a second chat column, a pane posting up to the shell, the VS Code webview host, which posts from its own
// window on the webview's origin) and this document's dispatch (the pane shim's and federation.js's kernel frames).
//
// Executed legs: every listener is run against the same senders. Four run as installed, over a stand-in window: the real
// listenForFrames, installSettingsSync, initFileView and initFileBrowse, each with that stand-in as the global window
// (which is also the window windowSender reads by default). The rest live inside modules that boot a page on import (the
// Waiting pane, the shell palette), behind module state (the comments panel's live panel) or inside a closure (the gear,
// the strip), so each is lifted out of its file by the TypeScript parser, from its function to its closing brace,
// transpiled and run over stubs: every free identifier it reads is an inert stub except the effect it is tested for, which
// counts, windowSender, which is the real helper, and window, which is the stand-in the helper reads. A representative arm
// per listener reaches its effect once from every heard sender and never from a foreign one; the head check sits before
// every arm, which the census below pins at source for every listener in ui/.
//
// The census reads the population instead of a list: every addEventListener("message", …) call in a ui/ source file
// (tests excluded), the method named or a computed member, and every onmessage handler assigned to the window (by window,
// self, globalThis or the bare global), must open with the check, preceded by nothing but reads of the message, and must
// be one of the gated sites below, each with an executed leg here. A new window listener anywhere in ui/ fails it until it
// is gated and given a leg. A second census reads what the name windowSender is bound to: in every ui/ file that calls the check, it is
// the helper's own import (gear.js: its require), bound once and never written, so a local helper of the same name that
// lets one more sender through cannot stand in for it. Synthetic world only: the notes-api demo, placeholder ids.
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
type Installed = { site: string; data: unknown; what: string; setup: (effect: () => void) => { globals?: Record<string, unknown>; install: () => void } };
const INSTALLED: Installed[] = [
  { site: "webview/frame-listener.ts", what: "a kernel-shaped feed frame reaching a pane's frame handler through listenForFrames",
    data: { type: "feed", ledgers: [{ id: SID, name: "api" }] },
    setup: (effect) => ({ install: () => { listenForFrames(() => effect()); } }) },
  { site: "webview/settings.ts", what: "a settingsSync that replaces the settings store (installSettingsSync)",
    data: { type: "settingsSync", settings: { theme: "classic", figureHosts: ["example.invalid"] } },
    setup: (effect) => ({ globals: { localStorage: { setItem: (k: string) => { if (k === "romp:settings") effect(); } } },
                          install: () => installSettingsSync() }) },
  { site: "webview/file-view.ts", what: "a viewFile relay that opens a file in the viewer (initFileView)",
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
 *  window by any of WINDOW_NAMES. Where it is, what it is on, and the listener's node and text. */
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
  const visit = (n: any): void => {
    if (ts.isCallExpression(n) && n.arguments.length >= 2 && ts.isStringLiteralLike(n.arguments[0]) && n.arguments[0].text === "message") {
      const m = member(n.expression);
      if (m && m.name === "addEventListener") {
        out.push({ file, line: line(n), receiver: m.receiver, fn: n.arguments[1], text: n.arguments[1].getText(sf), kind: "addEventListener" });
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
                writes?: string };   // or: the effect is a write to this free name
const LIFTED: Lifted[] = [
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
  const label = leg.file + " (" + leg.marker + ")";
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
 *  does not count: every statement before it must be a read of the message (a declaration initialised to <event>.data)
 *  or an early return on a condition that calls, constructs and assigns nothing, so no arm runs before the check. */
function headCheck(site: Site): string | null {
  const fn = site.fn;
  if (!(ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) || !fn.body || !ts.isBlock(fn.body)) return "the listener is not a function with a body";
  if (!fn.parameters.length || !ts.isIdentifier(fn.parameters[0].name)) return "the listener names no event parameter";
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
  ["webview/file-browse.ts", 1], ["webview/file-comments.ts", 1], ["webview/file-view.ts", 1], ["webview/frame-listener.ts", 1],
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
//     const variable of a for...of over a list of strings; or the first parameter, never written, of a callback handed
//     to such a list's forEach. A list is an array literal of strings, inline or held by a const that is not exported and
//     whose every other mention is a for...of's list or a forEach's receiver;
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
/** The declaration the identifier `id` refers to, found by walking out through the scopes around it, or null. A
 *  destructured declaration is found too, and resolves to no string below. */
function declOf(id: any): any {
  const name = id.text;
  const binds = (d: any) => !!d && bindsName(d.name, name);
  for (let s = id.parent; s; s = s.parent) {
    if ((ts.isForOfStatement(s) || ts.isForInStatement(s) || ts.isForStatement(s)) && s.initializer && ts.isVariableDeclarationList(s.initializer)) {
      const d = s.initializer.declarations.find(binds);
      if (d) return d;
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
/** Whether anything inside `scope` writes the name `name`: an assignment whose target mentions it, or a ++ or --. */
function writesName(scope: any, name: string): boolean {
  const mentions = (n: any): boolean => { let hit = ts.isIdentifier(n) && n.text === name; if (!hit) ts.forEachChild(n, (c: any) => { if (!hit && mentions(c)) hit = true; }); return hit; };
  let hit = false;
  const visit = (n: any): void => {
    if (hit) return;
    if (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment && mentions(n.left)) hit = true;
    if ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken) && mentions(n.operand)) hit = true;
    ts.forEachChild(n, visit);
  };
  visit(scope);
  return hit;
}
/** The strings a list holds: an array literal of string literals, or a const initialised to one that is not exported and
 *  whose every other mention in the file is a for...of's list or a forEach's receiver; else null. */
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
        || (ts.isPropertyAccessExpression(p) && p.expression === m && p.name.text === "forEach" && !!call && ts.isCallExpression(call) && call.expression === outer(p));
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
    if (!call || !ts.isCallExpression(call) || call.arguments[0] !== outer(fn)) return null;
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
  ];
  for (const src of refused) assert.ok(loose(src).length >= 1, "refused: " + src);
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
  ];
  for (const src of accepted) assert.deepEqual(loose(src), [], "accepted: " + src);
});

test("census: every gated site has an executed leg in this file (installed, or lifted by its marker)", () => {
  const legs = new Set<string>();
  for (const leg of INSTALLED) { const ss = messageSites(leg.site); assert.equal(ss.length, 1, leg.site + " has one window message listener"); legs.add(leg.site + ":" + ss[0].line); }
  for (const leg of LIFTED) { const s = siteOf(leg.file, leg.marker); legs.add(s.file + ":" + s.line); }
  const sites = uiSources().flatMap(messageSites).map((s) => s.file + ":" + s.line);
  assert.deepEqual(sites.filter((s) => !legs.has(s)), [], "a window message listener with no executed leg here");
  assert.equal(legs.size, INSTALLED.length + LIFTED.length, "no two legs run the same listener");
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
});
