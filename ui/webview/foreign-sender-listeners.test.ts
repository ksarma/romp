// Every window "message" listener in the webview bundles ignores a message from a foreign sender (window-sender.ts): a
// window that is not this document, not its embedder (the romp shell), not on this page's location.origin (the origin
// of its URL), and not this document's own dispatch of a kernel frame. The chat's frame handler got that check first
// (chat-foreign-frame.test.ts); this file holds it for the rest of the population:
//   - frame-listener.ts listenForFrames, the one window install every pane's frame handler shares (the feed, the Outline,
//     Waiting on you, the chat and the VS Code timeline): the window path hands the handler no message from a foreign
//     sender. The federation registry path is unchanged: only federation.js calls it, with a MessageEvent it built.
//   - every other window listener, each with its own check at its head: windowSender's in the Waiting pane's panes
//     cache, the VS Code settings sync, the shared file viewer's two (its viewFile relay, and the way back from a failed
//     svg picture, which runs the fetch again on hostUp and sends a probe of the picture's address on any other kernel
//     message), the file browser, the file-comments panel's replies, the gear's six listeners and the VS Code strip's;
//     and the shell's own check in the shell palette's two, read through pane-source.ts (paneSourceOk, which reads the
//     shell's window.__rompPaneSourceOk and fails closed), since the palette runs only on the shell page.
// Each windowSender listener hears every class windowSender does not name foreign, which covers each one's real
// senders: the shell (the embedder of a pane; to the shell's own page, its panes are windows on its location.origin),
// this document (self), a window on this page's location.origin (a second chat column, a pane posting up to the shell,
// the VS Code webview host, which posts from its own window on the webview's origin) and this document's dispatch (the
// pane shim's and federation.js's kernel frames). The palette's two hear only a pane of the shell, an iframe of the
// shell's document on its location.origin (the chat pane and a split column, whose tab menu posts hotkeyConfigure, and
// the settings frame, whose gear posts openKeys), and refuse every other window: the shell's own page, its own dispatch,
// a sourceless post, a frame nested in a pane and a tab a pane opened among them, and every foreign sender.
//
// Executed legs: every windowSender listener is run against the same senders (HEARD, FOREIGN), and the palette's two
// against the shell's panes (PANE_HEARD) and every other sender (PANE_REFUSED: every FOREIGN row, the shell's own page,
// its dispatch, a sourceless post on its location.origin, a frame nested in a pane, a tab a pane opened, and a pane of
// a shell page that defines no check), over a page whose check is the adopted one, run from its kernel.py text (the
// no-check row aside). Four run as installed, over a stand-in window: the real listenForFrames, installSettingsSync,
// initFileView and initFileBrowse, each with that stand-in as the global window (which is also the window windowSender
// reads by default). The rest live inside modules that boot a page on import (the Waiting pane, the shell palette),
// behind module state (the comments panel's live panel) or inside a closure (the gear, the strip, the file viewer's way
// back), so each is lifted out of its file by the TypeScript parser, from its function to its closing brace, transpiled
// and run over stubs: every free identifier it reads is an inert stub except the effect it is tested for, which counts,
// windowSender and paneSourceOk, which are the real helpers, and window, which is the stand-in the helpers read. A
// representative arm per listener reaches its effect once from every heard sender and never from a refused one; the
// head check sits before every arm, which the census below pins at source for every listener in ui/. A listener
// declared in ARMS (the way back) has a leg per declared arm (hostUp, and the probe), which the executed-leg census
// holds to exactly one each; each of those legs counts its own arm's effect once and the other arm's twice, so a heard
// sender that reaches the wrong arm fails as well as a foreign one that reaches either.
//
// The census reads the population instead of a list: every addEventListener("message", …) or
// addEventListener("messageerror", …) call in a ui/ source file (test and types files excluded; uiSources lists the
// files), the method named or a computed member, whatever its receiver, and every onmessage or onmessageerror handler
// assigned to this page's own window, the receiver decided by the road census's window rule (the binder's identity with
// window, self, globalThis or frames, and a module-local ambient shadow of one that the build drops, read as the raw
// global; a chain of member reads and initialisers the checker follows, this page's document.defaultView and a local
// initialised to or destructured from one among them, a binding whose initialiser is not its value at every use read
// fail-closed as the first kind any of its declarations binds; global `this`; the bare global), must take the event as
// its one parameter, with no default, have the check (the pane check in palette-main.ts, the shell's bundle, and
// windowSender's in every other file), preceded by nothing but reads of the message and early returns whose condition
// the census judges to run no code, none holding a destructuring default or a computed key (headCheck's docstring lists
// the forms), judged by form, not by what runs, and be one of the gated sites below, each with an executed leg here. A
// messageerror event carries the sender's origin and source as a message does, and a sender causes one by posting what
// the page cannot deserialize, so it is counted as a message. A listener handed over by name is read at the function
// written in place that a const of that name holds, found by the name's binding; any other name fails. A new window
// listener anywhere in ui/ fails it until it is gated and given a leg. A second census reads what the names
// windowSender and paneSourceOk are bound to: in every ui/ file that calls either check, the name is the helper's own
// import (gear.js: windowSender's require), bound once and never written, so a local helper of the same name that lets
// one more sender through cannot stand in for it. The first census reads the listeners the source spells, so two more
// hold the source to spellings it can read: a third holds that every addEventListener in ui/ is a call the first can
// read, and a fourth refuses the roads that spell neither (a method of the window, of the body element, of a document
// the census cannot tell is this page's or of a prototype read by a computed name, a function run with the window as
// its `this`, an onmessage handler set other than by an assignment the fourth accepts (one on this page's own window,
// one that sets no handler, or one on a socket the fourth proves through TypeScript's checker), a handler or a message
// listener on a window other than this page's own, code run from a string (a module imported from a data: URL or from a
// URL built at run time among it, and a timer, a callee named setTimeout or setInterval on any receiver, handed a
// string literal, a template, a + expression, an array or object literal or a variable whose initialiser is one, or
// used as a template's tag), a test or types file imported as a module, a module specifier holding a ? or a # or ending
// in / or /. (which esbuild rewrites before it resolves), a require() whose specifier is no string literal (which
// esbuild bundles as every file its pattern can match), a `with` statement, and the name WebSocket anywhere but as the
// constructor a `new` calls, or in a type). A test of its own holds the repo root to no package.json, tsconfig.json or
// jsconfig.json, which esbuild would read to resolve a ui/ module's specifier. What those cannot see is disclosed at
// the fourth.
// Synthetic world only: the notes-api demo, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as crypto from "node:crypto";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { createRequire } from "node:module";
import { hideEdges, staysEnumerable, defineHidden } from "../test-dom-shim";
import { windowSender } from "./window-sender";
import { paneSourceOk } from "./pane-source";
import { listenForFrames } from "./frame-listener";
import { installSettingsSync } from "./settings";
import { initFileView } from "./file-view";
import { initFileBrowse } from "./file-browse";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));   // esbuild and typescript from the extension
const UI = path.resolve(EXT, "..", "ui");
/** TypeScript, from the extension's node_modules. Every census here parses with it, and the socket proof
 *  (socketRefusal) reads its checker, with no fallback of any kind: TypeScript that cannot be loaded, or that lacks the
 *  language service the proof reads, stops this file with a message saying so. `id` is the module asked for (a test
 *  names one no node_modules holds). */
function loadTypeScript(req: (id: string) => any, id = "typescript"): any {
  let mod: any;
  try { mod = req(id); }
  catch (e) { throw new Error("the census cannot load TypeScript (" + id + " from vscode-extension's node_modules: " + (e as Error).message.split("\n")[0] + "), and it has no fallback without it: its parser reads every census and its checker the socket proof"); }
  if (!mod || typeof mod.createLanguageService !== "function" || typeof mod.createDocumentRegistry !== "function") {
    throw new Error("the census loaded " + id + " but it has no language service (createLanguageService, createDocumentRegistry), which the socket proof reads, and the census has no fallback without it");
  }
  return mod;
}
const ts = loadTypeScript(requireCjs);

const SID = "11111111-2222-3333-4444-555555555555";
const ORIGIN = "http://127.0.0.1:1";
const VSCODE_ORIGIN = "vscode-webview://11111111-2222-3333-4444-555555555555";
// another webview's origin: VS Code gives each webview its own, and only this webview's is the host's
const OTHER_VSCODE_ORIGIN = "vscode-webview://aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
const OTHER_ORIGIN = "https://example.invalid";

type Listener = (e: unknown) => void;
/** A receiving window: what windowSender reads (its parent, its location's origin), the target a listener under test is
 *  added to, and the methods those listeners call on window. It also carries the two edges a browser gives a window that
 *  relate it to the other frames in its tab: top, and frames, which is the window itself, whose length and indexes list
 *  the frames inside it (holdFrames). Its edges and every object it holds are non-enumerable (hideEdges, and defineHidden
 *  for the frames listed later), so a dump of it is its name, serial and frame count. A browser makes window[i] enumerable
 *  (Object.keys(window) lists "0"), so a check that enumerated the frames instead of indexing them would find none here;
 *  the grids that list their frames enumerably are window-sender.test.ts, chat-foreign-frame.test.ts and
 *  timeline-boot-senders.test.ts. */
class Receiver {
  parent: unknown;
  top: unknown;
  frames: unknown;
  length = 0;
  location: { origin: string };
  listeners: Array<[string, Listener]> = [];
  dispatched: string[] = [];
  constructor(public name: string, parent: unknown, origin: string, top?: unknown) {
    this.parent = parent;
    this.top = top;
    this.frames = this;
    this.location = { origin };
    hideEdges(this);
  }
  addEventListener(type: string, fn: Listener): void { this.listeners.push([type, fn]); }
  dispatchEvent(ev: { type: string }): boolean { this.dispatched.push(ev.type); return true; }
  messageListeners(): Listener[] { return this.listeners.filter(([t]) => t === "message").map(([, f]) => f); }
  /** Lists `kids` as the frames inside this window: frames[i] (this[i], hidden) and frames.length. */
  holdFrames(kids: unknown[]): void { kids.forEach((k, i) => defineHidden(this, String(i), k)); this.length = kids.length; }
}
/** The frame listed at index `i` of `w`'s frames. */
const frameIn = (w: Receiver, i: number): unknown => (w as unknown as Record<number, unknown>)[i];
type Ctx = "pane" | "shell" | "vscode" | "vscode, older";
const SHELL = hideEdges({ name: "the romp shell" });
/** A fresh receiving window of each kind: a pane in the romp shell (its parent and its top are the shell), the shell's
 *  own top-level page (its parent and its top are itself), and VS Code's webview frame, whose script sets window.parent
 *  to the frame itself (1.103 on) or deletes it (1.88 to 1.102). The pane holds two frames, each sharing its top: a
 *  sandboxed one (frameIn 0) and one on its location.origin (frameIn 1); the shell's page holds a sandboxed frame
 *  (frameIn 0) and its three panes, each a frame on its location.origin: the chat pane (CHILD_PANE, frameIn 1), a split
 *  chat column (SECOND_COLUMN, frameIn 2) and the settings frame, whose gear posts openKeys (SETTINGS_PANE, frameIn 3). */
function receiver(ctx: Ctx): Receiver {
  if (ctx === "pane") {
    const w = new Receiver("a pane in the romp shell", SHELL, ORIGIN, SHELL);
    w.holdFrames([sandboxed(w, SHELL), hideEdges({ name: "a frame on the pane's location.origin", parent: w, top: SHELL })]);
    return w;
  }
  if (ctx === "shell") {
    const w = new Receiver("the romp shell's page", null, ORIGIN);
    w.parent = w;
    w.top = w;
    w.holdFrames([sandboxed(w, w), CHILD_PANE, SECOND_COLUMN, SETTINGS_PANE]);
    return w;
  }
  if (ctx === "vscode") { const w = new Receiver("a VS Code webview frame", null, VSCODE_ORIGIN); w.parent = w; return w; }
  return new Receiver("a VS Code webview frame, window.parent deleted", undefined, VSCODE_ORIGIN);
}
const SECOND_COLUMN = hideEdges({ name: "a second chat column" });
const CHILD_PANE = hideEdges({ name: "a pane of the shell" });
const SETTINGS_PANE = hideEdges({ name: "the shell's settings frame" });
const VSCODE_HOST = hideEdges({ name: "the VS Code webview host" });
const OTHER_PAGE = hideEdges({ name: "a page on another origin" });
const OTHER_WEBVIEW = hideEdges({ name: "a window on another VS Code webview's origin" });
const sandboxed = (parent: unknown, top?: unknown) => hideEdges({ name: "a sandboxed frame", parent, top });

type Row = { who: string; ctx: Ctx; source: (w: Receiver) => unknown; origin: string;
             noCheck?: true };   // the palette's legs only: the row's page defines no window.__rompPaneSourceOk
const HEARD: Row[] = [
  { who: "this document", ctx: "pane", source: (w) => w, origin: ORIGIN },
  { who: "its embedder, the romp shell", ctx: "pane", source: (w) => w.parent, origin: ORIGIN },
  { who: "a second chat column on this page's location.origin", ctx: "pane", source: () => SECOND_COLUMN, origin: ORIGIN },
  { who: "a pane posting up to the shell's page", ctx: "shell", source: () => CHILD_PANE, origin: ORIGIN },
  { who: "the shell's page itself", ctx: "shell", source: (w) => w, origin: ORIGIN },
  { who: "the VS Code webview host (the frame's window.parent replaced)", ctx: "vscode", source: () => VSCODE_HOST, origin: VSCODE_ORIGIN },
  { who: "the VS Code webview host (the frame's window.parent deleted)", ctx: "vscode, older", source: () => VSCODE_HOST, origin: VSCODE_ORIGIN },
  { who: "this document's own dispatch of a kernel frame (no source, no origin)", ctx: "pane", source: () => null, origin: "" },
  { who: "a sourceless post on this page's location.origin", ctx: "pane", source: () => null, origin: ORIGIN },
  { who: "a frame inside the pane on its location.origin, sharing its top and listed in its frames", ctx: "pane", source: (w) => frameIn(w, 1), origin: ORIGIN },
];
const FOREIGN: Row[] = [
  { who: "a sandboxed frame beside the pane in the shell (opaque origin)", ctx: "pane", source: (w) => sandboxed(w.parent), origin: "null" },
  { who: "a sandboxed frame inside the shell's page (opaque origin)", ctx: "shell", source: (w) => sandboxed(w), origin: "null" },
  { who: "a sandboxed frame beside the pane in the shell, sharing its top (opaque origin)", ctx: "pane", source: (w) => sandboxed(w.parent, w.top), origin: "null" },
  { who: "a sandboxed frame inside the pane, sharing its top and listed in its frames (opaque origin)", ctx: "pane", source: (w) => frameIn(w, 0), origin: "null" },
  { who: "a sandboxed frame inside the shell's page, sharing its top and listed in its frames (opaque origin)", ctx: "shell", source: (w) => frameIn(w, 0), origin: "null" },
  { who: "a page on another origin that opened the pane", ctx: "pane", source: () => OTHER_PAGE, origin: OTHER_ORIGIN },
  { who: "a page on another origin that opened the shell", ctx: "shell", source: () => OTHER_PAGE, origin: OTHER_ORIGIN },
  { who: "a sandboxed frame inside the VS Code webview", ctx: "vscode", source: (w) => sandboxed(w), origin: "null" },
  { who: "a sandboxed frame that is gone (no source, opaque origin)", ctx: "pane", source: () => null, origin: "null" },
  { who: "a page on another origin that is gone (no source)", ctx: "shell", source: () => null, origin: OTHER_ORIGIN },
  { who: "a window on another VS Code webview's origin (the frame's window.parent replaced)", ctx: "vscode", source: () => OTHER_WEBVIEW, origin: OTHER_VSCODE_ORIGIN },
  { who: "a window on another VS Code webview's origin (the frame's window.parent deleted)", ctx: "vscode, older", source: () => OTHER_WEBVIEW, origin: OTHER_VSCODE_ORIGIN },
  { who: "a sourceless post from another VS Code webview's origin", ctx: "vscode", source: () => null, origin: OTHER_VSCODE_ORIGIN },
];
/** The senders the shell palette's two listeners hear: the shell's panes, each an iframe of the shell's document on its
 *  location.origin, the frames receiver("shell") lists after its sandboxed one. Run over a shell page whose check is the
 *  adopted one (installPaneCheck). */
const PANE_HEARD: Row[] = [
  { who: "the chat pane, an iframe of the shell's document (#f-chat)", ctx: "shell", source: () => CHILD_PANE, origin: ORIGIN },
  { who: "a split chat column, another iframe of the shell's document", ctx: "shell", source: () => SECOND_COLUMN, origin: ORIGIN },
  { who: "the settings frame, the gear's iframe of the shell's document (#f-settings)", ctx: "shell", source: () => SETTINGS_PANE, origin: ORIGIN },
];
/** Every other sender, which the palette's two refuse: every FOREIGN row, each over a page that carries the adopted check
 *  (its document's iframes are the frames its window lists), so each is refused by the check's own clauses and not by its
 *  absence; the senders windowSender hears that are no pane of the shell, the shell's own page, its own dispatch, a
 *  sourceless post on its location.origin, and a window on its location.origin that is no iframe of its document (a frame
 *  nested in a pane, a tab a pane opened); and a pane of a shell page that defines no check, which the palette's
 *  fail-closed read refuses. */
const PANE_REFUSED: Row[] = [
  ...FOREIGN,
  { who: "the shell's page itself", ctx: "shell", source: (w) => w, origin: ORIGIN },
  { who: "the shell page's own dispatch (no source, no origin)", ctx: "shell", source: () => null, origin: "" },
  { who: "a sourceless post on the shell's location.origin", ctx: "shell", source: () => null, origin: ORIGIN },
  { who: "a frame nested in the chat pane, on the shell's location.origin", ctx: "shell",
    source: (w) => hideEdges({ name: "a frame nested in the chat pane", parent: CHILD_PANE, top: w }), origin: ORIGIN },
  { who: "a tab the chat pane opened, on the shell's location.origin", ctx: "shell",
    source: () => hideEdges({ name: "a tab the chat pane opened", opener: CHILD_PANE }), origin: ORIGIN },
  { who: "the chat pane, on a shell page that defines no check", ctx: "shell", source: () => CHILD_PANE, origin: ORIGIN, noCheck: true },
];

// ── the shell's own check, which the palette's two read ──

/** kernel.py, whose served JavaScript holds the shell's check. */
const KERNEL_PY = path.resolve(EXT, "..", "kernel", "kernel.py");
/** The first and last characters of the adopted region that opens kernel.py's _LANDING_BOOT_JS, and the sha256 of its
 *  text: the digest tests/test_shell_source_check.py AdoptedCheck pins (ADOPTED_SHA256 there), recomputed from the
 *  project's commit f4a57200894ede72a4d4469570490aa64fbf9e94, never from the fork's copy. */
const CHECK_HEAD = "window.__rompPaneSourceOk=function(e){";
const CHECK_TAIL = "return false;}catch(x){return false;}};";
const CHECK_SHA256 = "97e0342292b56cf7b1df96a91d40c7bf8db3ee3a0949abc681c0e3457908f7bb";
let adopted: string | null = null;
/** The shell's check as kernel.py serves it: the region from CHECK_HEAD through CHECK_TAIL, read from kernel.py's text,
 *  once, and held to CHECK_SHA256, so the palette's legs run the check the shell defines, not a copy of it. */
function adoptedCheck(): string {
  if (adopted !== null) return adopted;
  const src = fs.readFileSync(KERNEL_PY, "utf8");
  const i = src.indexOf(CHECK_HEAD);
  assert.ok(i >= 0 && src.indexOf(CHECK_HEAD, i + 1) < 0, "kernel.py defines the shell's check once (" + CHECK_HEAD + ")");
  const j = src.indexOf(CHECK_TAIL, i);
  assert.ok(j > i, "and its region ends at " + CHECK_TAIL);
  const region = src.slice(i, j + CHECK_TAIL.length);
  assert.equal(crypto.createHash("sha256").update(region, "utf8").digest("hex"), CHECK_SHA256,
    "kernel.py's check is not the adopted region tests/test_shell_source_check.py AdoptedCheck pins");
  return (adopted = region);
}
/** Gives `w` a document whose iframes are the frames `w` lists, each an iframe element holding that frame's window and no
 *  data-protocol attribute, and runs the adopted check over it with `w` as its window and `w.location` as its location,
 *  so w.__rompPaneSourceOk is the shell's check on this page (hidden, as every other object `w` holds). */
function installPaneCheck(w: Receiver): void {
  const iframes = Array.from({ length: w.length }, (_, i) => hideEdges({ contentWindow: frameIn(w, i), getAttribute: (_a: string): null => null }));
  const doc = hideEdges({ querySelectorAll: (sel: string) => (sel === "iframe" ? iframes : []) });
  defineHidden(w, "document", doc);
  new Function("window", "document", "location", adoptedCheck())(w, doc, w.location);
  hideEdges(w);
}

// ── the stand-ins stay small in a dump ──

test("the stand-ins inspect as their primitives: every enumerable key of a receiving window and of each sending window holds a primitive", () => {
  const pane = receiver("pane"), shell = receiver("shell");
  const all: object[] = [SHELL, SECOND_COLUMN, CHILD_PANE, SETTINGS_PANE, VSCODE_HOST, OTHER_PAGE, OTHER_WEBVIEW, sandboxed(SHELL), sandboxed(SHELL, SHELL),
    pane, shell, receiver("vscode"), receiver("vscode, older"), frameIn(pane, 0) as object, frameIn(pane, 1) as object, frameIn(shell, 0) as object];
  for (const o of all) {
    for (const k of Object.keys(o)) assert.ok(staysEnumerable((o as any)[k]), k + " is enumerable and holds a " + typeof (o as any)[k]);
  }
  assert.ok(windowSender({ source: SHELL, origin: ORIGIN }, receiver("pane")) === "embedder", "a hidden parent is still read");
  // the frames edges are there for a check to read, hidden or not: each receiver's frames is itself, listing its frames
  assert.ok(pane.frames === pane && pane.length === 2 && pane.top === SHELL && (frameIn(pane, 0) as { parent: unknown }).parent === pane,
    "the pane's frames list its two frames, and its top is the shell");
  assert.ok(shell.frames === shell && shell.length === 4 && shell.top === shell && frameIn(shell, 1) === CHILD_PANE
    && frameIn(shell, 2) === SECOND_COLUMN && frameIn(shell, 3) === SETTINGS_PANE,
    "the shell's page lists its sandboxed frame and its three panes, and it is its own top");
  // a page given the adopted check keeps it hidden, as it keeps every other object it holds
  const checked = receiver("shell");
  installPaneCheck(checked);
  assert.equal(typeof (checked as any).__rompPaneSourceOk, "function", "the adopted check is defined on the page");
  for (const k of Object.keys(checked)) assert.ok(staysEnumerable((checked as any)[k]), k + " is enumerable and holds a " + typeof (checked as any)[k]);
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

type Site = { file: string; line: number; receiver: string; fn: any; text: string; kind: "addEventListener" | "onmessage";
               event?: string };   // the event it hears, "message" or "messageerror" (an onmessage kind: its handler's name less "on")
const parsed = new Map<string, Site[]>();
/** The names a script reaches its own window by: window, self, globalThis and frames (which a browser answers with the
 *  window itself; an indexed frames[i] is a frame's window, another). Whether a receiver is this page's own window is
 *  decided by the road census's window rule (refKind, stated at the road census below), not by spelling. By its first
 *  clause an identifier is one when its checker symbol IS the global table's symbol for one of these names (an
 *  augmented global still counts, by identity; globalThis by its symbol name, since the library gives it no declaration
 *  to anchor identity), so a local that shadows the name with a run-time binding is not the window. Neither is a
 *  declaration of the name at the top level of a script (a file TypeScript calls no module), which the checker merges
 *  with the global or resolves a use past to it (in a JavaScript file it binds as CommonJS, one with require or
 *  module.exports for example, it resolves the use to the file's own local): in the page bundle esbuild keeps a
 *  run-time declaration the file's own local, so where a script has a declaration of the name that is not ambient (a
 *  type-only one, which esbuild erases, among them), identity decides no use of the name in that file, the road census
 *  refuses the file outright, and the rule reads a use the checker resolves to the global fail-closed. A shadow whose
 *  every declaration is ambient (a module-local `declare var window` esbuild drops) or in a declaration file binds
 *  nothing at run time and is the raw global window, which refKind reads as one. A shadow the source binds at run time
 *  anywhere but at a script's top level (in a module, in a function or in a block of a script, for example) that
 *  esbuild drops as statically dead code is the raw global too, but the census models only the ambient and
 *  declaration-file drop (bindsNothingAtRuntime) and reads such a shadow through its declaration, a value outside the
 *  rule it discloses (the road census comment's "cannot see" list). A
 *  receiver the rule reads as a window other than this page's own, or does not read as a window, is no census site.
 *  The road census refuses a handler assigned on another window whatever its value, and one assigned on any other
 *  receiver the rule does not read as this page's own window (the body element and a document among them) unless the
 *  value sets no handler (null, an unshadowed undefined) or the receiver is a name socketRefusal proves, through the
 *  same checker, a WebSocket. */
const WINDOW_NAMES = new Set(["window", "self", "globalThis", "frames"]);
/** The events a window listener hears a sender's post as: a message, and a messageerror, which carries the sender's origin
 *  and source too and which a sender causes by posting what the page cannot deserialize. */
const MESSAGE_EVENTS = new Set(["message", "messageerror"]);
/** The handler properties of those events. */
const MESSAGE_HANDLERS = new Set(["onmessage", "onmessageerror"]);
/** The ScriptKind a ui/ file parses under, by its suffix (spacer-measure.test.ts kindOf's rule): a .tsx or .jsx under its
 *  own kind, a .js, .mjs or .cjs under JS, the rest under TS. Every parse site and compile()'s loader read it. */
const kindOfUi = (m: string): any => /\.tsx$/.test(m) ? ts.ScriptKind.TSX : /\.jsx$/.test(m) ? ts.ScriptKind.JSX
  : /\.[mc]?js$/.test(m) ? ts.ScriptKind.JS : ts.ScriptKind.TS;
/** Every window message listener in `src`, read by the TypeScript parser (so a spelling in a comment or a string is no
 *  listener): each addEventListener("message", fn) or addEventListener("messageerror", fn) call, on any receiver, whether
 *  the method is named (x.addEventListener, a bare addEventListener) or a computed member (x["addEventListener"]), and
 *  each assignment of an onmessage or onmessageerror handler whose receiver the road census's window rule (refKind)
 *  reads as this page's own window, or with no receiver (the bare global). Where it is, what it is on, and the
 *  listener's node and text. A listener handed to addEventListener by a plain name (the file viewer's onKernelMessage,
 *  which its close removes by that name) is read at the function the name holds, when a const of that name, found by
 *  the checker (res.declC), is initialised to a function written in place: a const is never rebound, and the binding,
 *  not the spelling, picks it, so another declaration of the name elsewhere in the file is not the one read. Any other
 *  name (a let or a var, which can be rebound; a parameter; a function declaration, which can be assigned to; a const
 *  holding a call's result) stays the name, which the head census refuses. */
function sitesIn(file: string, src: string, checked: () => Checked = () => fixtureChecked(file, src)): Site[] {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kindOfUi(file));
  const res = resolver(sf, checked);
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
    const d = res.declC(u);
    const init = d && isConstDecl(d) && ts.isIdentifier(d.name) && d.initializer ? bare(d.initializer) : null;
    return init && (ts.isArrowFunction(init) || ts.isFunctionExpression(init)) ? init : a;
  };
  const visit = (n: any): void => {
    if (ts.isCallExpression(n) && n.arguments.length >= 2 && ts.isStringLiteralLike(n.arguments[0]) && MESSAGE_EVENTS.has(n.arguments[0].text)) {
      const m = member(n.expression);
      if (m && m.name === "addEventListener") {
        const fn = listenerOf(n.arguments[1]);
        out.push({ file, line: line(n), receiver: m.receiver, fn, text: fn.getText(sf), kind: "addEventListener", event: n.arguments[0].text });
      }
    }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      const m = member(n.left);
      const l = bare(n.left);
      const recv = ts.isPropertyAccessExpression(l) || ts.isElementAccessExpression(l) ? l.expression : null;   // null: the bare global
      if (m && MESSAGE_HANDLERS.has(m.name) && (recv === null || ownWindowRef(recv, res))) {
        out.push({ file, line: line(n), receiver: m.receiver, fn: n.right, text: n.right.getText(sf), kind: "onmessage", event: m.name.slice(2) });
      }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}
/** Every window message listener in a ui/ file (sitesIn), read in the program `checked` gives (the census's shared one
 *  when a caller iterating ui/ passes it; a per-file program otherwise). One parse per file, cached by file. */
function messageSites(file: string, checked?: () => Checked): Site[] {
  const had = parsed.get(file);
  if (had) return had;
  const src = fs.readFileSync(path.join(UI, file), "utf8");
  const out = sitesIn(file, src, checked || (() => fixtureChecked(file, src)));
  parsed.set(file, out);
  return out;
}
/** The one message listener in `file` whose text holds `marker`. */
function siteOf(file: string, marker: string, checked?: () => Checked): Site {
  const hits = messageSites(file, checked).filter((s) => s.text.includes(marker));
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
                // the effect's binding, counting through hit; arm is the leg's own arm, for a scope with more than one effect
                named: (hit: () => void, w: Receiver, arm: string | undefined) => Record<string, unknown>;
                writes?: string;   // or: the effect is a write to this free name
                arm?: string;      // a leg of a listener declared in ARMS names the declared arm it runs
                senders?: "panes" };   // the shell palette's: heard from the shell's panes only (PANE_HEARD, PANE_REFUSED)
/** The file viewer's way back (openFileView's onKernelMessage) over a pane that waits, with the probes' budget full, for the
 *  leg that runs `arm`. Both of its effects count: the way back (wayBackEvent, which runs the fetch again), the hostUp arm's,
 *  and a probe of the picture's address (probeServed, which sends one), the probe arm's. The leg's own arm's effect counts
 *  once and the other arm's twice, so a foreign sender that reaches either arm counts, and a heard sender counts exactly
 *  once only when it reaches its own arm's effect and not the other's. An arm the way back does not have is refused. */
const wayBackScope = (hit: () => void, arm: string | undefined): Record<string, unknown> => {
  if (arm !== "hostUp" && arm !== "probe") throw new Error("the way back has no arm " + JSON.stringify(arm) + ": its arms are hostUp and probe");
  const other = (): void => { hit(); hit(); };
  const [wayBack, probe] = arm === "hostUp" ? [hit, other] : [other, hit];
  return {
    wayBackEvent: wayBack, probeServed: () => { probe(); return true; }, paneWaits: () => true,
    wayBackProbing: false, wayBackProbes: 3, wayBackSeq: 0, objUrl: "/file?path=docs%2Ffigure.svg&sid=" + SID + "&v=1",
  };
};
const LIFTED: Lifted[] = [
  { file: "webview/file-view.ts", marker: '"hostUp"', arm: "hostUp",
    what: "the viewer's way back from a failed svg picture on hostUp (federation.js's own dispatch), which runs the fetch again",
    data: { type: "hostUp", hosts: ["TESTHOST"] }, named: (hit, _w, arm) => wayBackScope(hit, arm) },
  { file: "webview/file-view.ts", marker: "probeServed(", arm: "probe",
    what: "the viewer's way back from a failed svg picture on any other kernel message, which sends a probe of the picture's address",
    data: { type: "sessions", sessions: [] }, named: (hit, _w, arm) => wayBackScope(hit, arm) },
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
  { file: "webview/palette-main.ts", marker: '"openKeys"', what: "the shell's openKeys ask, which opens the shortcuts dialog", senders: "panes",
    data: { romp: "openKeys" }, named: (hit) => ({ keys: { open: hit } }) },
  { file: "webview/palette-main.ts", marker: '"hotkeyConfigure"', what: "the shell's hotkeyConfigure ask, which binds a tab's hot key", senders: "panes",
    data: { romp: "hotkeyConfigure", sid: SID, name: "web" }, named: (hit) => ({ configureHotkey: hit }) },
  { file: "webview/strip.ts", marker: '"stripShow"', what: "the VS Code strip's usage push, which repaints the bars",
    data: { type: "usage", usage: { fiveHour: { pct: 10 } } }, named: (hit) => ({ render: hit }) },
];
/** The listeners owed a leg per arm, by file, the marker that picks the listener (siteOf) and its arms: the executed-leg
 *  census holds each to exactly one leg per declared arm, each naming it, and each leg's scope counts its own arm's effect
 *  once and every other arm's twice (wayBackScope), which the crossed-message test below holds. Every other listener has
 *  one leg, which names no arm: a representative arm, since the head census pins the check ahead of every arm.
 *  Residual (low, disclosed): this table is hand-written, not derived from the way back's source, so a coordinated test-side
 *  edit that empties it, drops the probe leg, and removes the hostUp leg's arm while pinning its scope to the hostUp arm
 *  would leave one leg and still pass here (the pin is needed because wayBackScope refuses a scope for no arm). The
 *  product stays guarded regardless: the head census refuses onKernelMessage acting before its check, and
 *  file-view-seam.test.ts reds a foreign hostUp or probe. Deriving the arms from source is listener-specific (the probe arm
 *  is a fallthrough, named by no literal) and not worth the fragility for this; recorded rather than fixed. */
const ARMS: Array<[string, string, string[]]> = [["webview/file-view.ts", "probeServed(", ["hostUp", "probe"]]];

const compiled = new Map<string, (scope: unknown) => Listener>();
/** The lifted listener as a function of its scope (compiled once per site): sloppy-mode code, which `with` needs
 *  (esbuild's transform adds no strict prologue, and a .js listener is used as written). */
function compile(site: Site): (scope: unknown) => Listener {
  const key = site.file + ":" + site.line;
  const hit = compiled.get(key);
  if (hit) return hit;
  const src = "const __listener = " + site.text + ";\n";
  const kind = kindOfUi(site.file);   // a .js, .mjs or .cjs listener is used as written; every other kind is transformed by its own loader
  const code = kind === ts.ScriptKind.JS ? src : requireCjs("esbuild").transformSync(src, {
    loader: kind === ts.ScriptKind.TSX ? "tsx" : kind === ts.ScriptKind.JSX ? "jsx" : "ts", target: "es2020" }).code;
  const make = new Function("__scope", "with (__scope) {\n" + code + "\nreturn __listener;\n}") as (s: unknown) => Listener;
  compiled.set(key, make);
  return make;
}
/** Runs the lifted listener once, over a fresh receiving window of the row's kind, on the message from the row's sender,
 *  and returns the effect's count. A palette leg's window carries the adopted check (installPaneCheck) unless the row's
 *  page defines none; paneSourceOk is the real helper reading that window, as windowSender is the real helper reading it. */
function runLifted(leg: Lifted, row: Row): number {
  const site = siteOf(leg.file, leg.marker);
  const w = receiver(row.ctx);
  if (leg.senders === "panes" && !row.noCheck) installPaneCheck(w);
  let n = 0;
  const hit = () => { n++; };
  const named: Record<string, unknown> = {
    windowSender: (e: { source?: unknown; origin?: unknown }) => windowSender(e, w),
    paneSourceOk: (e: unknown) => paneSourceOk(e as MessageEvent, w as unknown as Window),
    window: w,
    location: w.location,
    ...leg.named(hit, w, leg.arm),
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
  if (leg.senders === "panes") {
    test(label + ": " + leg.what + " from any window that is not a pane of the shell, and on a page with no check, reaches nothing", () => {
      const reached = PANE_REFUSED.filter((row) => runLifted(leg, row) !== 0).map((row) => row.who);
      assert.deepEqual(reached, [], label + ": a sender that is no pane of the shell reached the effect: " + reached.join("; "));
    });
    test(label + ": " + leg.what + " from each pane of the shell reaches the effect once", () => {
      const missed = PANE_HEARD.map((row) => [row.who, runLifted(leg, row)] as const).filter(([, n]) => n !== 1).map(([who, n]) => who + " (" + n + ")");
      assert.deepEqual(missed, [], label + ": a pane of the shell did not reach the effect once: " + missed.join("; "));
    });
    continue;
  }
  test(label + ": " + leg.what + " from a foreign sender reaches nothing", () => {
    const reached = FOREIGN.filter((row) => runLifted(leg, row) !== 0).map((row) => row.who);
    assert.deepEqual(reached, [], label + ": a foreign sender reached the effect: " + reached.join("; "));
  });
  test(label + ": " + leg.what + " from every sender that is not foreign reaches the effect once", () => {
    const missed = HEARD.map((row) => [row.who, runLifted(leg, row)] as const).filter(([, n]) => n !== 1).map(([who, n]) => who + " (" + n + ")");
    assert.deepEqual(missed, [], label + ": a heard sender did not reach the effect once: " + missed.join("; "));
  });
}

test("the legs of a listener declared in ARMS tell its arms apart: in each leg's scope, a heard sender's message for another leg's arm counts that arm's effect twice", () => {
  for (const [file, marker, arms] of ARMS) {
    const site = siteOf(file, marker);
    const legs = LIFTED.filter((l) => siteOf(l.file, l.marker) === site);
    assert.deepEqual(legs.map((l) => l.arm).sort(), arms.slice().sort(), file + ": a lifted leg per declared arm");
    for (const leg of legs) {
      for (const other of legs.filter((l) => l !== leg)) {
        const crossed: Lifted = { ...leg, data: other.data };
        const off = HEARD.map((row) => [row.who, runLifted(crossed, row)] as const).filter(([, n]) => n !== 2).map(([who, n]) => who + " (" + n + ")");
        assert.deepEqual(off, [], file + ": the " + leg.arm + " leg's scope, on the " + other.arm + " leg's message, did not count the other arm twice: " + off.join("; "));
      }
    }
  }
});

// ── the census: every window message listener in ui/ ──

/** The classes every file under ui/ falls into, by its path relative to ui/ (forward slashes), tried in this order, the
 *  first whose test matches taking the file: tests and types (a `.test.` file of any module suffix, and a .d.ts, .d.mts
 *  or .d.cts file; a .d.tsx is a module, since TypeScript reads it as no declaration file and esbuild bundles it);
 *  modules, every suffix esbuild 0.21.5's default loaders read as code (.ts .tsx .mts .cts .js .jsx .mjs .cjs) in any
 *  directory, the files every census here reads; and the files no census reads, each class named: stylesheets, the
 *  anchor map's fixtures (its directory's data: markdown, json, a python file, an html page with no script, a csv, an
 *  svg, a .gitattributes; never a package.json, tsconfig.json or jsconfig.json, which esbuild reads to resolve a
 *  specifier, a package.json's main or browser field and a tsconfig's or jsconfig's paths, so such a file there has no
 *  class, as it has none anywhere else under ui/) and the markdown at ui/'s own top (its README and CLAUDE.md). The
 *  repo root, above ui/, is held to none of the three by its own test (RESOLVER_CONFIGS). No census reads a test or types
 *  file, and esbuild bundles either like any module when a module imports it, so the road census refuses that import (a
 *  file the build puts in a page by an entry point or an alias is on the road census's list of what it cannot see). A
 *  file no class takes reds uiPartition, named with its suffix, so a file of a kind no class names is loud, never
 *  dropped. Every directory is walked, one named node_modules or dist included: a module there is one a ui/ module can
 *  import and esbuild bundles, so it is read like any other; a stylesheet, a test or a types file there takes its class
 *  as it does anywhere; and any other file there (a package.json, a README) has no class, since the fixtures and the
 *  markdown are named by where they sit. */
const UI_CLASSES: Array<[string, RegExp]> = [
  ["tests and types", /\.test\.([mc]?[tj]s|[tj]sx)$|\.d\.[mc]?ts$/],
  ["modules", /\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)$/],
  ["stylesheets", /\.css$/],
  ["the anchor map's fixtures", /^webview\/anchor-map-fixtures\/(?!(package|tsconfig|jsconfig)\.json$)[^/]+$/],
  ["ui's own markdown", /^[^/]+\.md$/],
];
/** The class of the file at `rel` (relative to ui/): the first of UI_CLASSES whose test matches it, or null. */
const uiClassOf = (rel: string): string | null => { const c = UI_CLASSES.find(([, re]) => re.test(rel)); return c ? c[0] : null; };
let uiParts: Record<string, string[]> | null = null;
/** Every file under `root` (ui/ unless a test hands another), in every directory, relative to it, partitioned into
 *  UI_CLASSES by uiClassOf; a file no class takes is a red naming it. ui/ is walked once per run. */
function uiPartition(root: string = UI): Record<string, string[]> {
  if (root === UI && uiParts) return uiParts;
  const out: Record<string, string[]> = {};
  for (const [k] of UI_CLASSES) out[k] = [];
  const rest: string[] = [];
  const walk = (rel: string): void => {
    for (const d of fs.readdirSync(path.join(root, rel), { withFileTypes: true })) {
      const r = rel ? rel + "/" + d.name : d.name;
      if (d.isDirectory()) { walk(r); continue; }
      const c = uiClassOf(r);
      if (c) out[c].push(r); else rest.push(r);
    }
  };
  walk("");
  assert.deepEqual(rest, [], "every file under ui/ is in one of the named classes (" + UI_CLASSES.map(([k]) => k).join(", ") +
    "); a file none takes is given a class in UI_CLASSES, never dropped: " + rest.map((f) => f + " (" + (path.extname(f) || "no suffix") + ")").join(", "));
  for (const k of Object.keys(out)) out[k].sort();
  if (root === UI) uiParts = out;
  return out;
}
/** Every ui/ source file the parser should read: uiPartition's modules. */
function uiSources(): string[] {
  return uiPartition()["modules"];
}
/** ui/'s declaration files (.d.ts, .d.mts, .d.cts), which no census reads as code; the socket proof's program holds
 *  them, since they type the vendored modules the editor chunk imports. */
function uiDeclarationFiles(): string[] {
  return uiPartition()["tests and types"].filter((f) => /\.d\.[mc]?ts$/.test(f));
}
/** The files whose window listeners take the shell's own check, not windowSender's: palette-main.ts, bundled as
 *  palette-main.js, which only the shell page loads (the test "the shell's bundle is loaded by the shell page alone"
 *  holds that), so its two listeners hear only the shell's panes. Their gate is `if (!paneSourceOk(<its event>)) return;`, paneSourceOk being pane-source.ts's
 *  fail-closed reader of the shell's window.__rompPaneSourceOk. headCheck refuses a windowSender gate in such a file, and
 *  the pane gate in any other: a pane's listeners hear their embedder, their own dispatch and the VS Code host, which the
 *  shell's check admits none of, and no pane page defines it. */
const PANE_GATED_FILES = new Set(["webview/palette-main.ts"]);
/** Where the listener's check is among its body's statements, `if (windowSender(<its event>) === "foreign") return;`, or
 *  in a file of PANE_GATED_FILES `if (!paneSourceOk(<its event>)) return;` (the other file kind's gate refused), or why
 *  it does not count: the listener takes one parameter, the event, a plain name with no default (a parameter's default
 *  runs before the body, so a default on it or on a second parameter would run ahead of the check, and a destructured
 *  parameter, where a default or a computed key could sit, is no plain name), and every statement before the check must
 *  hold no destructuring default and no computed key (defaultOrComputed: a default runs its expression when the value
 *  it binds is undefined, and a computed key, in brackets in a pattern, an object literal or a class, runs its
 *  expression and converts the result to a key, so either can run page code whatever it spells), and must be a read of
 *  the message (a declaration initialised to <event>.data) or an early return whose condition inert accepts: no call,
 *  construct, tagged or substituted template, delete, await, yield, ++/--, assignment, or binary operator but &&, ||,
 *  ??, ===, !== and the comma (every other one can run page code: ==, !=, <, >, <=, >=, + and the rest convert an
 *  operand, in converts its key and can hit a Proxy trap, and instanceof runs Symbol.hasInstance), and every property
 *  or element access reads off the event or a message read: off the event, its data at any depth (a structured clone,
 *  whose own members are plain data) or, one level and no deeper, its own origin, source, ports or lastEventId; off a
 *  name a message read bound to <event>.data, any depth. A read any further through the event can run a getter the page
 *  defined: its target, currentTarget and srcElement are the receiving window, its view is a window where the event has
 *  one, and a member of its source is a member of the sending window, so e.target.x, e.view and e.source.parent are
 *  refused, as is a member read off any other name. The rule is judged by form, not by what runs, and some forms it
 *  accepts can still run page code ahead of the check: a read of the event's own data, origin, source, ports or
 *  lastEventId, whose getters on MessageEvent.prototype the page can replace (the check reads source and origin the
 *  same way); a read of a member the message's data does not hold itself, which comes from its prototype, where the
 *  page can define a getter; in a message read, an array pattern, which runs the array iterator; and in an early
 *  return's condition, a read of a global name the page defines as a getter, a unary +, - or ~ and an element key, each
 *  of which converts an object, a spread (an iterator, or an object's getters), a class expression (its heritage reads
 *  the superclass's prototype, and a decorator is a call) and a JSX element, a call once compiled. */
function headCheck(site: Site): string | null {
  const fn = site.fn;
  const pane = PANE_GATED_FILES.has(site.file);
  const which = pane ? "the pane check" : "the foreign-sender check";
  if (ts.isIdentifier(fn)) return "the listener is a name no const holding a function written in place binds (sitesIn): " + fn.text;
  if (!(ts.isArrowFunction(fn) || ts.isFunctionExpression(fn)) || !fn.body || !ts.isBlock(fn.body)) return "the listener is not a function with a body";
  if (!fn.parameters.length || !ts.isIdentifier(fn.parameters[0].name)) return "the listener names no event parameter";
  if (fn.parameters.length !== 1 || fn.parameters[0].initializer || fn.parameters[0].dotDotDotToken) {
    return "the listener takes more than its one event parameter, or gives it a default, and a parameter's default runs before the check: " + fn.parameters.map((q: any) => q.getText()).join(", ").slice(0, 80);
  }
  const ev = fn.parameters[0].name.text;
  const isReturn = (s: any) => ts.isReturnStatement(s) && !s.expression;
  const senderGate = (s: any) => ts.isIfStatement(s) && !s.elseStatement && isReturn(s.thenStatement)
    && ts.isBinaryExpression(s.expression) && s.expression.operatorToken.kind === ts.SyntaxKind.EqualsEqualsEqualsToken
    && ts.isCallExpression(s.expression.left) && ts.isIdentifier(s.expression.left.expression) && s.expression.left.expression.text === "windowSender"
    && s.expression.left.arguments.length === 1 && ts.isIdentifier(s.expression.left.arguments[0]) && s.expression.left.arguments[0].text === ev
    && ts.isStringLiteralLike(s.expression.right) && s.expression.right.text === "foreign";
  const paneGate = (s: any) => ts.isIfStatement(s) && !s.elseStatement && isReturn(s.thenStatement)
    && ts.isPrefixUnaryExpression(s.expression) && s.expression.operator === ts.SyntaxKind.ExclamationToken
    && ts.isCallExpression(s.expression.operand) && ts.isIdentifier(s.expression.operand.expression) && s.expression.operand.expression.text === "paneSourceOk"
    && s.expression.operand.arguments.length === 1 && ts.isIdentifier(s.expression.operand.arguments[0]) && s.expression.operand.arguments[0].text === ev;
  const [isGate, otherGate] = pane ? [paneGate, senderGate] : [senderGate, paneGate];
  // the binary operators that coerce no operand: the logical connectives, strict equality and the comma. Every other binary
  // operator runs valueOf/toString/Symbol.toPrimitive (==, !=, the relational operators, +, and the rest) or Symbol.hasInstance
  // (instanceof) or a Proxy trap (in) on an operand, so it can run an arm; assignments run an arm too. All are not inert.
  const NON_COERCING = new Set<number>([ts.SyntaxKind.AmpersandAmpersandToken, ts.SyntaxKind.BarBarToken,
    ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken,
    ts.SyntaxKind.CommaToken]);
  /** The event's own attributes a pre-check may read one level deep. A member of any of them is refused, since reading
   *  it can run page code (a member of its source is a member of the sending window); a read of one of them runs its
   *  getter on MessageEvent.prototype, which the page can replace, as headCheck's docstring says. */
  const EVENT_OWN = new Set(["origin", "source", "ports", "lastEventId"]);
  /** The leftmost node of a property or element access chain, casts and parentheses removed. */
  const accessRoot = (n: any): any => { n = unwrap(n); while (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) n = unwrap(n.expression); return n; };
  /** Whether `n` runs no code, judged by its form (headCheck's docstring names the accepted forms that can still run page
   *  code). `allowed` is the names a property or element access may read off: the event (its data at any depth, or one of
   *  EVENT_OWN one level deep) and every name a message read has bound to <event>.data so far (any depth: a structured
   *  clone's own members are plain data). */
  const inert = (n: any, allowed: Set<string>): boolean => {
    if (ts.isCallExpression(n) || ts.isNewExpression(n) || ts.isTaggedTemplateExpression(n) || ts.isTemplateExpression(n)
        || ts.isDeleteExpression(n) || ts.isAwaitExpression(n) || ts.isYieldExpression(n)
        || ts.isPrefixUnaryExpression(n) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken)
        || ts.isPostfixUnaryExpression(n) || ts.isBinaryExpression(n) && !NON_COERCING.has(n.operatorToken.kind)) return false;
    if (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) {
      for (let c: any = n; ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c); c = unwrap(c.expression)) {
        if (ts.isElementAccessExpression(c) && c.argumentExpression && !inert(c.argumentExpression, allowed)) return false;
      }
      const root = accessRoot(n);
      if (!ts.isIdentifier(root) || !allowed.has(root.text)) return false;
      if (root.text !== ev) return true;   // a name a message read bound to <event>.data: a structured clone, any depth
      const links: any[] = [];   // the chain's accesses from the event outward: links[0] reads the event's own member
      for (let c: any = unwrap(n); ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c); c = unwrap(c.expression)) links.unshift(c);
      const first = memberName(links[0]);
      if (first === "data") return true;   // under the message's data, any depth
      return links.length === 1 && first !== null && EVENT_OWN.has(first);
    }
    let ok = true;
    ts.forEachChild(n, (c: any) => { if (ok && !inert(c, allowed)) ok = false; });
    return ok;
  };
  /** The first destructuring default (a binding element with an initialiser) or computed key (a computed property name)
   *  anywhere in `n`, or null: the one syntactic check that refuses both ahead of the check, in a message read's pattern
   *  and anywhere in an early return's condition alike. */
  const defaultOrComputed = (n: any): any => {
    if (ts.isComputedPropertyName(n) || (ts.isBindingElement(n) && n.initializer)) return n;
    let hit: any = null;
    ts.forEachChild(n, (c: any) => { if (!hit) hit = defaultOrComputed(c); });
    return hit;
  };
  const readsMessage = (s: any) => ts.isVariableStatement(s) && s.declarationList.declarations.every((d: any) =>
    d.initializer && ts.isPropertyAccessExpression(d.initializer) && ts.isIdentifier(d.initializer.expression)
    && d.initializer.expression.text === ev && d.initializer.name.text === "data");
  const earlyReturn = (s: any, allowed: Set<string>) => ts.isIfStatement(s) && !s.elseStatement && isReturn(s.thenStatement) && inert(s.expression, allowed);
  const body = fn.body.statements;
  const allowed = new Set<string>([ev]);   // the event, plus each name a message read binds to <event>.data, in body order
  for (let i = 0; i < body.length; i++) {
    if (isGate(body[i])) return null;
    if (otherGate(body[i])) return "statement " + (i + 1) + (pane
      ? " is windowSender's gate, and a listener in the shell's bundle (PANE_GATED_FILES) takes the pane check, `if (!paneSourceOk(" + ev + ")) return;`"
      : " is the pane check, which only the shell's bundle (PANE_GATED_FILES) takes; a pane's listener takes windowSender's gate");
    const dc = defaultOrComputed(body[i]);
    if (dc) return "statement " + (i + 1) + " holds a " + (ts.isComputedPropertyName(dc) ? "computed key" : "destructuring default")
      + " ahead of " + which + ": " + dc.getText().slice(0, 80);
    if (readsMessage(body[i])) {
      for (const d of (body[i] as any).declarationList.declarations) if (ts.isIdentifier(d.name)) allowed.add(d.name.text);
      continue;
    }
    if (!earlyReturn(body[i], allowed)) return "statement " + (i + 1) + " runs before " + which + ": " + body[i].getText().slice(0, 80);
  }
  return pane ? "no `if (!paneSourceOk(" + ev + ")) return;` in the listener's body (a listener in the shell's bundle takes the pane check)"
    : "no `if (windowSender(" + ev + ") === \"foreign\") return;` in the listener's body";
}
// The gated sites, by file and count. EXEMPT is for a site the census counts that no other page can post to (an
// addEventListener("message", …) on something that is not a window), listed with its reason; there is none in ui/
// today. A listed site is left out of the per-file count and the head check only: the spelling assertion in the census
// test and the leg census still read every site, so such a listener also needs those two to leave it out before the
// census passes. An onmessage handler on something other than this page's window is no census site: the road census
// accepts a WebSocket's own handler (federation.ts's socket, a name whose one declaration TypeScript's checker resolves
// it to and whose every write the language service finds bind it to the built-in `new WebSocket(...)` and to nothing
// else, socketRefusal) and refuses every other receiver it cannot resolve, so a MessagePort's, a worker's, a
// BroadcastChannel's or an EventSource's handler is refused, fail-closed.
const GATED: Array<[string, number]> = [
  ["webview/file-browse.ts", 1], ["webview/file-comments.ts", 1], ["webview/file-view.ts", 2], ["webview/frame-listener.ts", 1],
  ["webview/gear.js", 6], ["webview/palette-main.ts", 2], ["webview/settings.ts", 1], ["webview/strip.ts", 1], ["webview/waiting.ts", 1],
];
const EXEMPT: Array<[string, number, string]> = [];
/** Whether a census site is spelled as every gated site is, window.addEventListener("message" or "messageerror", …): the
 *  census holds every site to it, so an onmessage handler on any receiver, and a listener added to any receiver but the
 *  text `window`, keeps the census red whatever else it carries. */
const spelledAsGated = (s: Site): boolean => s.receiver === "window" && s.kind === "addEventListener";

test("census: every window message listener in ui/ has its check (windowSender's foreign-sender check, or the pane check in the shell's bundle), preceded by nothing but reads of the message and early returns the census judges to run no code, and is one of the gated sites", () => {
  const sites = uiSources().flatMap((f) => messageSites(f));
  const exempt = new Set(EXEMPT.map(([f, line]) => f + ":" + line));
  const counted = new Map<string, number>();
  for (const s of sites) if (!exempt.has(s.file + ":" + s.line)) counted.set(s.file, (counted.get(s.file) || 0) + 1);
  assert.deepEqual([...counted.entries()].sort(), GATED.slice().sort(),
    "the window message listeners in ui/ are not the gated sites: a new one is gated at its head, given an executed leg in this file and added to GATED");
  const bad = sites.filter((s) => !exempt.has(s.file + ":" + s.line)).map((s) => [s, headCheck(s)] as const).filter(([, why]) => why !== null)
    .map(([s, why]) => s.file + ":" + s.line + " (" + s.receiver + "): " + why);
  assert.deepEqual(bad, [], "a window message listener acts before its check (windowSender's foreign-sender check, or the pane check in the shell's bundle):\n" + bad.join("\n"));
  assert.ok(sites.every(spelledAsGated),
    "every census site is window.addEventListener(\"message\", ...), the one spelling the gated sites use");
});

test("the census reads every spelling of a window message listener: addEventListener named or computed on any receiver, for a message or a messageerror, and an onmessage or onmessageerror handler on a receiver the window rule reads as this page's own window, each failing the gated spelling; a handler on another window, a socket or a receiver the rule does not resolve is no site", () => {
  const found = (src: string) => sitesIn("webview/probe.ts", src).map((s) => (s.kind === "onmessage" ? "on" + s.event : s.kind) + " on " + (s.receiver || "(bare)"));
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
  // a messageerror is heard as a message (it carries the sender's origin and source): its listener and its handler are sites
  assert.deepEqual(sitesIn("webview/probe.ts", "window.addEventListener(\"messageerror\", " + listener + ");").map((s) => s.kind + " " + s.event + " on " + s.receiver),
    ["addEventListener messageerror on window"]);
  assert.deepEqual(found("window.onmessageerror = " + listener + ";"), ["onmessageerror on window"]);
  assert.deepEqual(found("parent.addEventListener(\"message\", " + listener + ");"), ["addEventListener on parent"], "a listener on any receiver is a site, held off the gated spelling");
  // frames is this page's own window: a listener on it is a census site the road census leaves to the census above, which
  // holds it off the gated spelling; a frame, frames[0], is another window, whose listener the road census refuses
  assert.deepEqual(found("frames.addEventListener(\"message\", " + listener + ");"), ["addEventListener on frames"]);
  assert.deepEqual(looseRoads("webview/probe.ts", "frames.addEventListener(\"message\", " + listener + "); window.frames.addEventListener(\"messageerror\", " + listener + ");").loose, [],
    "a listener on frames, this page's own window, is no refused road");
  assert.ok(looseRoads("webview/probe.ts", "frames[0].addEventListener(\"message\", " + listener + ");").loose.some((r) => /listener added to a window other than this page's own/.test(r.why)),
    "a listener on frames[0], a frame's window, is refused");
  // an onmessage or onmessageerror handler on a receiver the window rule reads as this page's own window is exactly one
  // census site, and the census's spelling predicate (spelledAsGated) fails it, so it keeps the census red
  const OWN_WINDOW: Array<[string, string?]> = [
    ["window.window.onmessage = f;"], ["self.self.onmessage = f;"], ["globalThis.window.onmessage = f;"],
    ["window[\"window\"][\"onmessage\"] = f;"], ["(window as any).self.onmessage = f;"], ["window!.onmessageerror = f;"],
    ["document.defaultView.onmessage = f;"], ["window.document.defaultView.onmessage = f;"], ["self.document.defaultView.onmessage = f;"],
    ["const w = window; w.onmessage = f;"], ["const w = window, x = w; x.onmessage = f;"], ["let w = window; w.onmessage = f;"],
    ["for (var w = window; ;) { w.onmessage = f; break; }"], ["const d = document; d.defaultView.onmessage = f;"],
    ["const { defaultView } = document; defaultView.onmessage = f;"], ["const { document: { defaultView: dv } } = window; dv.onmessage = f;"],
    ["const { window: w } = self; w.onmessage = f;"],
    ["w\\u0069ndow.onmessage = f;"], ["document.def\\u0061ultView.onmessage = f;"],
    // frames is the window itself (a frame is frames[i], below): each of its names is this page's own window
    ["frames.onmessage = f;"], ["window.frames.onmessage = f;"], ["self.frames[\"onmessage\"] = f;"], ["var w = frames; w.onmessage = f;"],
    ["const { frames: w } = window; w.onmessage = f;"], ["fr\\u0061mes.onmessageerror = f;"],
    ["this.onmessage = f;", "webview/probe.js"], ["(function () { this.onmessage = f; })();", "webview/probe.js"],
  ];
  const notOneSite: string[] = [], spelled: string[] = [];
  for (const [src, file] of OWN_WINDOW) {
    const s = sitesIn(file || "webview/probe.ts", src);
    if (s.filter((x) => x.kind === "onmessage").length !== 1) notOneSite.push(src);
    if (s.some(spelledAsGated)) spelled.push(src);
  }
  assert.deepEqual(notOneSite, [], "not one onmessage site on this page's own window");
  assert.deepEqual(spelled, [], "the census's spelling predicate (spelledAsGated) passes it");
  // a handler on a window other than this page's own, on a socket, or on a receiver the census cannot resolve is no site
  // (the road census refuses all but the socket's)
  const sited = ["parent.onmessage = f;", "top[\"onmessage\"] = f;", "opener.onmessage = f;", "frames[0].onmessage = f;",
    "window[0].onmessage = f;", "frame.contentWindow.onmessage = f;", "el.ownerDocument.defaultView.onmessage = f;", "e.target.onmessage = f;",
    "document.body.onmessage = f;", "getWin().onmessage = f;", "const ws = new WebSocket(u); ws.onmessage = f;"].filter((src) => found(src).length !== 0);
  assert.deepEqual(sited, [], "a site on a receiver that is not this page's own window");
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
// The lifted legs hand each listener the real windowSender and paneSourceOk under those names, and the head census
// accepts a call by those names, so neither reads what the names are bound to in the listener's file. This census does:
// in every ui/ source file that names windowSender (the gated sites but the palette's, the chat's render.ts and any file
// that joins them), or paneSourceOk (the palette's palette-main.ts and any file that joins it), the name has exactly one
// binding, its helper, and nothing writes to it. In a TypeScript file the binding is
// `import { windowSender } from "./window-sender"` or `import { paneSourceOk } from "./pane-source"`, unaliased; in
// gear.js, a CommonJS script, windowSender's is `var windowSender = require('./window-sender.ts').windowSender;` at the
// file's top level, and no script may bind paneSourceOk. A second binding anywhere in the file (a local, a parameter, a
// function, a destructured name, an import aliased so that another binding takes the name), an assignment to the name,
// or a `with` statement, which can rebind any name, fails it.

const TS_BINDING = 'import { windowSender } from "./window-sender";';
const GEAR_BINDING = "var windowSender = require('./window-sender.ts').windowSender;";
const PANE_BINDING = 'import { paneSourceOk } from "./pane-source";';
/** The helpers the checks call, by name: the one binding a TypeScript file may give the name, the one a CommonJS script
 *  may (none for paneSourceOk), and the helper's own file, which the census leaves out. */
const HELPERS: Record<string, { ts: string; js: string | null; home: string }> = {
  windowSender: { ts: TS_BINDING, js: GEAR_BINDING, home: "webview/window-sender.ts" },
  paneSourceOk: { ts: PANE_BINDING, js: null, home: "webview/pane-source.ts" },
};
/** Why `name` (windowSender unless given) in this source does not certainly name its helper, or null when it does: its
 *  declarations, the writes to it and any `with` statement, read by the TypeScript parser (so a spelling in a comment or
 *  a string is none). */
function senderBinding(file: string, src: string, name = "windowSender"): string | null {
  const helper = HELPERS[name];
  const kind = kindOfUi(file), isJs = kind === ts.ScriptKind.JS || kind === ts.ScriptKind.JSX;
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kind);
  const decls: any[] = [], writes: string[] = [], withs: string[] = [];
  const DECL = [ts.SyntaxKind.VariableDeclaration, ts.SyntaxKind.Parameter, ts.SyntaxKind.BindingElement, ts.SyntaxKind.FunctionDeclaration,
    ts.SyntaxKind.FunctionExpression, ts.SyntaxKind.ClassDeclaration, ts.SyntaxKind.ClassExpression, ts.SyntaxKind.ImportSpecifier,
    ts.SyntaxKind.ImportClause, ts.SyntaxKind.NamespaceImport, ts.SyntaxKind.ImportEqualsDeclaration, ts.SyntaxKind.EnumDeclaration,
    ts.SyntaxKind.ModuleDeclaration];
  const named = (n: any): boolean => !!n && ts.isIdentifier(n) && n.text === name;
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
  if (writes.length) return "a write to " + name + ": " + writes.join("; ");
  if (decls.length !== 1) return decls.length + " bindings of " + name + ", not the one: " + decls.map((d) => ts.SyntaxKind[d.kind] + " `" + d.getText(sf).slice(0, 60) + "`").join("; ");
  const d = decls[0];
  if (isJs) {
    if (helper.js === null) return "a script binds " + name + ", which only `" + helper.ts + "` in a TypeScript module may bind";
    const stmt = d.parent && d.parent.parent;
    if (!ts.isVariableDeclaration(d) || !stmt || !ts.isVariableStatement(stmt) || stmt.parent !== sf || stmt.getText(sf) !== helper.js) {
      return "the binding is not `" + helper.js + "` at the file's top level: `" + (stmt ? stmt.getText(sf) : d.getText(sf)).slice(0, 100) + "`";
    }
    return null;
  }
  const decl = ts.isImportSpecifier(d) ? d.parent.parent.parent : null;
  if (!decl || d.propertyName || !ts.isImportDeclaration(decl) || decl.getText(sf) !== helper.ts) {
    return "the binding is not `" + helper.ts + "`: `" + (decl ? decl.getText(sf) : d.getText(sf)).slice(0, 100) + "`";
  }
  return null;
}
/** Every ui/ source file whose code names `name` (windowSender unless given; read by the parser), its helper's own file
 *  aside. */
function senderFiles(name = "windowSender"): string[] {
  return uiSources().filter((f) => f !== HELPERS[name].home).filter((f) => {
    const src = fs.readFileSync(path.join(UI, f), "utf8");
    if (!src.includes(name)) return false;
    const sf = ts.createSourceFile(f, src, ts.ScriptTarget.Latest, true, kindOfUi(f));
    let hit = false;
    const visit = (n: any): void => { if (hit) return; if (ts.isIdentifier(n) && n.text === name) hit = true; else ts.forEachChild(n, visit); };
    visit(sf);
    return hit;
  });
}

test("census: in every ui/ file that calls a check, the name windowSender or paneSourceOk is bound once, to its helper, and never written", () => {
  const files = senderFiles(), paneFiles = senderFiles("paneSourceOk");
  const gated = GATED.map(([f]) => f);
  assert.deepEqual(gated.filter((f) => !PANE_GATED_FILES.has(f) && !files.includes(f)), [], "every gated site's file but the shell's bundle names windowSender");
  assert.deepEqual([...PANE_GATED_FILES].filter((f) => !paneFiles.includes(f)), [], "the shell's bundle names paneSourceOk");
  assert.ok(files.includes("webview/render.ts"), "the chat's frame handler, the first check, is in the population");
  const bad = [...files.map((f) => [f, "windowSender"]), ...paneFiles.map((f) => [f, "paneSourceOk"])]
    .map(([f, name]) => [f, name, senderBinding(f, fs.readFileSync(path.join(UI, f), "utf8"), name)] as const).filter(([, , why]) => why !== null)
    .map(([f, name, why]) => f + " (" + name + "): " + why);
  assert.deepEqual(bad, [], "a file's windowSender or paneSourceOk is not certainly its helper:\n" + bad.join("\n"));
});

test("the binding census reads what it claims: a local, a parameter, an aliased import, a wrapper in gear.js, a write or a `with` is refused, for windowSender and for paneSourceOk; each helper's own import, and windowSender's require, are accepted", () => {
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
  // paneSourceOk, the palette's: its own import is the one binding; every other shape is refused, a script's among them
  const pimp = PANE_BINDING + "\n";
  assert.equal(senderBinding("webview/probe.ts", pimp + 'window.addEventListener("message", (e) => { if (!paneSourceOk(e)) return; });', "paneSourceOk"), null);
  const paneRefused: Array<[string, string, RegExp]> = [
    ["webview/probe.ts", 'import { paneSourceOk as ok } from "./pane-source";\nconst paneSourceOk = (e: MessageEvent) => e.origin === "null" || ok(e);', /not `import/],
    ["webview/probe.ts", pimp + "function f() { const paneSourceOk = (e: unknown) => true; return paneSourceOk; }", /2 bindings/],
    ["webview/probe.ts", pimp + "function f(paneSourceOk: (e: unknown) => boolean) { return paneSourceOk; }", /2 bindings/],
    ["webview/probe.ts", 'import { paneSourceOk } from "./pane-source.ts";', /not `import/],
    ["webview/probe.ts", 'import { paneSourceOk } from "./window-sender";', /not `import/],
    ["webview/probe.ts", 'import * as paneSourceOk from "./pane-source";', /not `import/],
    ["webview/probe.ts", "const paneSourceOk = (e: unknown) => true;", /not `import/],
    ["webview/probe.ts", pimp + "paneSourceOk = () => true;", /a write/],
    ["webview/probe.js", "var paneSourceOk = require('./pane-source.ts').paneSourceOk;", /a script binds paneSourceOk/],
    ["webview/probe.ts", pimp + "with ({ paneSourceOk: () => true }) { paneSourceOk(e); }", /with/],
    ["webview/probe.ts", "const a = 1;", /0 bindings/],
  ];
  for (const [file, src, why] of paneRefused) assert.match(String(senderBinding(file, src, "paneSourceOk")), why, file + ": " + src);
});

// ── the census: every addEventListener in ui/ is one the census above can read ──
//
// The census above reads a registration spelled addEventListener("message", fn), its event type a string literal. A
// registration that reaches the method any other way escapes it: through .call or .apply
// (EventTarget.prototype.addEventListener.call(window, "message", f)), an alias or a bound copy
// (const add = window.addEventListener.bind(window); add("message", f)), a destructured name, or a call whose event type
// is not a literal (window.addEventListener(type, f)). tests/test_shell_source_check.py refuses those in kernel.py
// (_loose_add_tokens); this is the same rule for ui/, read by the TypeScript parser, so a spelling in a comment or inside
// a longer string is none. Every addEventListener in a ui/ source file (test and types files excluded) must be one of:
//   - the method called directly with a string literal for its event type (the census above reads the "message" and
//     "messageerror" ones);
//   - the method called directly with an event type the parser resolves to strings, none of them "message" or
//     "messageerror": a const initialised to a string, in the file or exported so by the ui/ module it is imported from
//     (`export const`, read from the one file esbuild bundles for the import); the const variable of a for...of over a
//     list of strings; or the one parameter, never written, of a callback handed
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
/** Whether the identifier `n`, a reference the language service lists for a variable, writes the variable, by its
 *  position: through every parenthesis, cast, satisfies, non-null mark and type argument around it, which esbuild
 *  erases (so `(d as any) = w`, `(<any>d) = w`, `(d satisfies any) = w` and `d! = w` run as `d = w`), and through the
 *  array and object literals a destructuring assignment writes into (an element, a rest element, a property's value, a
 *  shorthand property, an object rest), it is an assignment's target (of any operator), the operand of ++ or --, or a
 *  for...in or for...of head. A pattern under a cast (([d] as any) = [w]) esbuild refuses to build, as an invalid
 *  assignment target, and this counts it a write all the same, fail-closed. The language service's isWriteAccess reads a
 *  reference inside a cast, satisfies, non-null mark or type argument, and a rest element's target, as a read, so the
 *  window rule's initIsValue and the socket proof count a reference a write when either says so. It reads no scope:
 *  which references are the variable's is the checker's answer, through findReferences and the walk that must agree
 *  with it. */
function writesBinding(n: any): boolean {
  let m = n;
  for (let p = m.parent; p; p = m.parent) {
    if (ts.isParenthesizedExpression(p) || ts.isAsExpression(p) || ts.isTypeAssertionExpression(p) || ts.isNonNullExpression(p)
        || (ts.isSatisfiesExpression && ts.isSatisfiesExpression(p)) || ts.isExpressionWithTypeArguments(p)
        || ts.isArrayLiteralExpression(p) || ts.isSpreadElement(p)) m = p;
    // an object literal's member: a property's value (its name is never a reference to a variable), a shorthand
    // property's name (not its default), an object rest
    else if (ts.isSpreadAssignment(p) || (ts.isShorthandPropertyAssignment(p) && p.name === m) || ts.isPropertyAssignment(p)) m = p.parent;
    else if (ts.isBinaryExpression(p)) {
      return p.left === m && p.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && p.operatorToken.kind <= ts.SyntaxKind.LastAssignment;
    } else if (ts.isPrefixUnaryExpression(p) || ts.isPostfixUnaryExpression(p)) {
      return p.operator === ts.SyntaxKind.PlusPlusToken || p.operator === ts.SyntaxKind.MinusMinusToken;
    } else return (ts.isForInStatement(p) || ts.isForOfStatement(p)) && p.initializer === m;
  }
  return false;
}
/** The identifier `text` that starts at `start` in `sf` (a language service reference's file and span), or null. The
 *  walk goes by ts.forEachChild, which does not enter JSDoc, so a reference the service lists inside a JSDoc comment
 *  (an @type tag's {typeof d}, a {@link d}) is not found and answers null, and the window rule leaves the binding
 *  undecided. */
function identAt(sf: any, start: number, text: string): any {
  let hit: any = null;
  const walk = (n: any): void => {
    if (hit || start < n.pos || start >= n.end) return;
    if (ts.isIdentifier(n) && n.text === text && n.getStart(sf) === start) hit = n;
    else ts.forEachChild(n, walk);
  };
  walk(sf);
  return hit;
}
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
/** Whether anything inside `scope` writes the name `name`: an assignment whose target mentions it, a ++ or --, a
 *  for...in or for...of that assigns it on each pass, or a `var name = value` that redeclares it with a value (a var of a
 *  parameter's name merges with the parameter in the checker, so a var initialiser is a write to the parameter the event
 *  arm reads). */
function writesName(scope: any, name: string): boolean {
  const mentions = (n: any): boolean => { let hit = ts.isIdentifier(n) && n.text === name; if (!hit) ts.forEachChild(n, (c: any) => { if (!hit && mentions(c)) hit = true; }); return hit; };
  let hit = false;
  const visit = (n: any): void => {
    if (hit) return;
    if (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment && mentions(n.left)) hit = true;
    if ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken) && mentions(n.operand)) hit = true;
    if ((ts.isForInStatement(n) || ts.isForOfStatement(n)) && !ts.isVariableDeclarationList(n.initializer) && mentions(n.initializer)) hit = true;
    if (ts.isVariableDeclaration(n) && n.initializer && bindsName(n.name, name) && (n.parent.flags & ts.NodeFlags.BlockScoped) === 0) hit = true;
    ts.forEachChild(n, visit);
  };
  visit(scope);
  return hit;
}
/** The strings a list holds: an array literal of string literals, or a const initialised to one that is not exported and
 *  whose every other mention in the file is a for...of's list or the receiver of a forEach whose callback cannot reach
 *  the list (sealedForEach); else null. */
function listOf(e: any, sf: any, res: Res): string[] | null {
  e = unwrap(e);
  if (ts.isArrayLiteralExpression(e)) return e.elements.every((x: any) => ts.isStringLiteralLike(x)) ? e.elements.map((x: any) => x.text) : null;
  if (!ts.isIdentifier(e)) return null;
  const d = res.declC(e);
  if (!d || !isConstDecl(d) || !ts.isIdentifier(d.name) || isExported(d.parent.parent) || !d.initializer || !ts.isArrayLiteralExpression(unwrap(d.initializer))) return null;
  let onlyAsList = true;
  const visit = (n: any): void => {
    if (!onlyAsList) return;
    // d and d.name are program nodes; n iterates the census's own parse, so skip the declaration's own name by mapping n
    // to the program (res.toProg), not by object identity, and count only the other references.
    if (ts.isIdentifier(n) && n.text === d.name.text && res.toProg(n) !== d.name && res.declC(n) === d) {
      const m = outer(n), p = m.parent;
      const call = ts.isPropertyAccessExpression(p) ? outer(p).parent : null;
      onlyAsList = (ts.isForOfStatement(p) && p.expression === m)
        || (ts.isPropertyAccessExpression(p) && p.expression === m && p.name.text === "forEach" && !!call && ts.isCallExpression(call) && call.expression === outer(p)
            && sealedForEach(call));
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return onlyAsList ? listOf(d.initializer, sf, res) : null;
}
/** The suffixes esbuild 0.21.5 tries, in its default order, for an import that names none (vscode-extension/esbuild.js sets
 *  no resolveExtensions), the code ones: a .tsx sibling is picked before a .ts one, a .jsx before a .js. */
const RESOLVE_ORDER = [".tsx", ".ts", ".jsx", ".js"];
/** The string the module at base `mod` under `root` (ui/ unless a test hands another) exports under `name` as
 *  `export const name = "..."`, or null. The module is the one file of RESOLVE_ORDER's suffixes the base has; a base with
 *  two or more such siblings is refused (null), so no reading of it can differ from the file esbuild bundles. */
function exportedString(mod: string, name: string, root: string = UI): string[] | null {
  const siblings = RESOLVE_ORDER.map((ext) => path.join(root, mod + ext)).filter((p) => fs.existsSync(p));
  if (siblings.length !== 1) return null;
  const p = siblings[0];
  const sf = ts.createSourceFile(p, fs.readFileSync(p, "utf8"), ts.ScriptTarget.Latest, true, kindOfUi(p));
  for (const st of sf.statements) {
    if (!ts.isVariableStatement(st) || !isExported(st) || !(st.declarationList.flags & ts.NodeFlags.Const)) continue;
    const d = st.declarationList.declarations.find((x: any) => ts.isIdentifier(x.name) && x.name.text === name);
    if (d && d.initializer && ts.isStringLiteralLike(unwrap(d.initializer))) return [unwrap(d.initializer).text];
  }
  return null;
}
/** The event types a registration's type argument can be, read by the parser (the shapes the comment above lists), or null. */
function eventTypes(e: any, sf: any, file: string, res: Res, depth = 0): string[] | null {
  e = unwrap(e);
  if (ts.isStringLiteralLike(e)) return [e.text];
  if (!ts.isIdentifier(e) || depth > 4) return null;
  const d = res.declC(e);
  if (!d) return null;
  if (isConstDecl(d) && ts.isIdentifier(d.name)) {
    const loop = d.parent.parent;
    if (ts.isForOfStatement(loop) && loop.initializer === d.parent) return listOf(loop.expression, sf, res);
    return d.initializer ? eventTypes(d.initializer, sf, file, res, depth + 1) : null;
  }
  if (ts.isParameter(d) && ts.isIdentifier(d.name)) {
    const fn = d.parent, call = outer(fn).parent;
    if (fn.parameters[0] !== d || writesName(fn, d.name.text)) return null;
    // the callback must have no way to reach the list (sealedForEach): one that can rewrites an element before its pass
    if (!call || !ts.isCallExpression(call) || call.arguments[0] !== outer(fn) || !sealedForEach(call)) return null;
    const callee = unwrap(call.expression);
    return ts.isPropertyAccessExpression(callee) && callee.name.text === "forEach" ? listOf(callee.expression, sf, res) : null;
  }
  if (ts.isImportSpecifier(d)) {
    const from = d.parent.parent.parent.moduleSpecifier.text;
    return from.startsWith("./") ? exportedString(path.posix.join(path.posix.dirname(file), from), (d.propertyName || d.name).text) : null;
  }
  return null;
}
type LooseAdd = { file: string; line: number; why: string; text: string };
/** Every addEventListener in `src` that is none of the shapes the comment above lists, and how many it read. */
function looseAddTokens(file: string, src: string, checked: () => Checked = () => fixtureChecked(file, src)): { read: number; loose: LooseAdd[] } {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kindOfUi(file));
  const res = resolver(sf, checked);
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
      const types = arg ? eventTypes(arg, sf, file, res) : null;
      if (!types) return refuse(acc, "a call whose event type the census cannot read");
      if (types.some((t) => MESSAGE_EVENTS.has(t))) return refuse(acc, "a message listener whose event type is not a string literal");
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

test("census: every addEventListener in ui/ is a direct call the census reads (its event type a literal, or strings that are not \"message\" or \"messageerror\"), a read that is only tested, or a member's name", () => {
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
    // PR 923: an ambient const binds nothing at run time (esbuild drops the declare), so its value cannot be read as
    // the event type; at run time the name is whatever global of that name holds, so a message listener can register
    // with no check. declC returns null for it, and eventTypes cannot resolve it. 1d9a9d631 read its value
    "declare const EV = \"click\"; window.addEventListener(EV, f);",
    // a var anywhere in the enclosing function binds the name for the whole function, over an outer const
    "const EV7 = \"click\"; function g7(x: boolean) { if (x) { var EV7 = \"message\"; } window.addEventListener(EV7, f); } g7(true);",
    "const T = \"click\"; function g() { for (var T of [\"message\"]) { /* */ } window.addEventListener(T, f); }",
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
    // the event name is no message type either way: the census reads T as the outer const "click" (strict: true binds
    // every file strictly, so the block function does not bind T at the call), and the bundle hoists the block function
    // (Annex B) so at run time T is a function object. (This row has no handler and no socket, so the socket proof's clause 0
    // does not run on it; esbuild does build the block function.)
    "const T = \"click\"; function g() { if (f) { function T() { /* */ } } window.addEventListener(T, f); }",
  ];
  for (const src of accepted) assert.deepEqual(loose(src), [], "accepted: " + src);
});

test("census: every file under ui/ is in a named class, and the censuses read the modules class, every gated site's file among them", () => {
  const parts = uiPartition();
  assert.ok(parts["modules"].length > 100, "the censuses read ui/'s modules: " + parts["modules"].length);
  for (const [f] of GATED) assert.ok(parts["modules"].includes(f), "a gated site's file is a module the censuses read: " + f);
  assert.deepEqual(uiSources(), parts["modules"], "the censuses walk the modules class");
});

/** The resolver configurations esbuild reads in a module's directory and in every directory above it: a package.json
 *  (its main or browser field can map a specifier to another file) and a tsconfig.json or jsconfig.json (its paths). Under
 *  ui/ such a file has no class and reds uiPartition; at the repo root, ui/'s parent, the test below refuses it; a
 *  directory above the repo root is on the road census's list of what it cannot see. */
const RESOLVER_CONFIGS = ["package.json", "tsconfig.json", "jsconfig.json"];
test("census: the repo root holds no package.json, tsconfig.json or jsconfig.json, whose browser field or paths esbuild would read to resolve a ui/ module's specifier", () => {
  const root = path.resolve(UI, "..");
  const found = RESOLVER_CONFIGS.filter((f) => fs.existsSync(path.join(root, f)));
  assert.deepEqual(found, [], "a resolver configuration at the repo root, which esbuild reads for every ui/ module and no census reads: " + found.join(", "));
});

test("the file classes read what they claim: a module of every suffix esbuild reads as code is read by the censuses in any directory, a .d.tsx among them; a test file of each suffix and a .d.ts, .d.mts or .d.cts file is not; a stylesheet, test or types file under node_modules or dist takes its class; and a file of any other kind outside the named classes has no class, nor does a package.json, tsconfig.json or jsconfig.json among the fixtures", () => {
  // synthetic names only: uiClassOf reads a name, and no fixture file may sit in ui/
  const NAMES: Array<[string, string | null]> = [
    ["webview/probe.ts", "modules"], ["webview/probe.tsx", "modules"], ["webview/probe.mts", "modules"], ["webview/probe.cts", "modules"],
    ["webview/probe.js", "modules"], ["webview/probe.jsx", "modules"], ["webview/probe.mjs", "modules"], ["webview/probe.cjs", "modules"],
    ["probe.ts", "modules"], ["webview/deep/er/probe.tsx", "modules"], ["webview/anchor-map-fixtures/probe.js", "modules"],
    // a .d.tsx is no declaration file to TypeScript, and esbuild bundles it (import "./probe.d" finds it): a module
    ["webview/probe.d.tsx", "modules"],
    ["webview/probe.test.ts", "tests and types"], ["webview/probe.test.tsx", "tests and types"], ["webview/probe.test.mjs", "tests and types"],
    ["webview/probe.test.cjs", "tests and types"], ["webview/probe.test.jsx", "tests and types"], ["webview/probe.test.mts", "tests and types"],
    ["webview/probe.test.cts", "tests and types"], ["webview/probe.d.ts", "tests and types"],
    ["webview/probe.d.mts", "tests and types"], ["webview/probe.d.cts", "tests and types"],
    ["webview/probe.css", "stylesheets"], ["webview/anchor-map-fixtures/probe.json", "the anchor map's fixtures"],
    ["webview/anchor-map-fixtures/.gitattributes", "the anchor map's fixtures"], ["README.md", "ui's own markdown"],
    // a resolver configuration esbuild reads (a package.json's main or browser field, a tsconfig's or jsconfig's paths) is
    // no fixture: among the fixtures it has no class, as it has none anywhere else under ui/
    ["webview/anchor-map-fixtures/package.json", null], ["webview/anchor-map-fixtures/tsconfig.json", null],
    ["webview/anchor-map-fixtures/jsconfig.json", null], ["webview/anchor-map-fixtures/probe.package.json", "the anchor map's fixtures"],
    // under node_modules or dist a stylesheet, a test or a types file takes its class as anywhere; nothing else does
    ["webview/node_modules/pkg/index.d.ts", "tests and types"], ["webview/node_modules/pkg/style.css", "stylesheets"],
    ["webview/dist/a.test.js", "tests and types"], ["webview/node_modules/pkg/package.json", null], ["dist/README.md", null],
    ["webview/probe.html", null], ["webview/probe.json", null], ["webview/probe.md", null], ["webview/probe.vue", null],
    ["webview/probe", null], ["webview/anchor-map-fixtures/deeper/probe.md", null],
  ];
  const wrong = NAMES.filter(([n, want]) => uiClassOf(n) !== want).map(([n, want]) => n + ": " + uiClassOf(n) + ", not " + want);
  assert.deepEqual(wrong, [], "each synthetic name's class (UI_CLASSES, tried in order)");
});

test("the partition fails on a file no class takes, naming it, and walks every directory, node_modules and dist included", () => {
  // a synthetic tree in a temporary root outside ui/ (uiPartition reads the root it is handed)
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fsl-partition-"));
  try {
    for (const d of ["webview/deep", "webview/node_modules/pkg", "webview/dist", "dist"]) fs.mkdirSync(path.join(root, d), { recursive: true });
    for (const f of ["README.md", "webview/a.ts", "webview/deep/b.tsx", "webview/a.test.ts", "webview/s.css",
      "webview/node_modules/pkg/x.js", "webview/dist/zz.ts", "dist/y.mjs"]) {
      fs.writeFileSync(path.join(root, f), "");
    }
    assert.deepEqual(uiPartition(root)["modules"], ["dist/y.mjs", "webview/a.ts", "webview/deep/b.tsx", "webview/dist/zz.ts", "webview/node_modules/pkg/x.js"],
      "the modules, at any depth, under a directory named node_modules or dist too");
    for (const stray of ["webview/stray.vue", "webview/node_modules/pkg/package.json", "dist/y.html"]) {
      fs.writeFileSync(path.join(root, stray), "");
      const esc = stray.replace(/[.*+?^${}()|[\]\\/]/g, "\\$&");
      assert.throws(() => uiPartition(root), new RegExp("every file under ui\\/ is in one of the named classes[^]*" + esc), stray + " has no class, and reds");
      fs.rmSync(path.join(root, stray));
    }
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("every parse site reads a file under its own suffix's kind: a .tsx or .jsx module's JSX element hides no listener and no road after it", () => {
  assert.deepEqual([".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"].map((x) => ts.ScriptKind[kindOfUi("webview/probe" + x)]),
    ["TS", "TSX", "TS", "TS", "JS", "JSX", "JS", "JS"]);
  const jsx = "const v = <div a={1}>{\"x\"}</div>; ";
  for (const file of ["webview/probe.tsx", "webview/probe.jsx"]) {
    assert.deepEqual(sitesIn(file, jsx + "window.addEventListener(\"message\", (e) => { go(e.data); });").map((x) => x.receiver), ["window"], file + ": the listener after the element");
    assert.notDeepEqual(looseRoads(file, jsx + "frames[0][k] = f;").loose, [], file + ": the road after the element");
  }
});

test("an imported event name is read from the one file esbuild bundles for its base: a lone .tsx, .ts or .jsx is read, and a base with two code siblings is refused", () => {
  // a synthetic pair in a temporary root outside ui/ (exportedString reads the root it is handed)
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fsl-resolve-"));
  try {
    fs.mkdirSync(path.join(root, "webview"));
    const put = (name: string, v: string) => fs.writeFileSync(path.join(root, "webview", name), "export const EV = \"" + v + "\";\n");
    put("lone-tsx.tsx", "romp:from-tsx"); put("lone-ts.ts", "romp:from-ts"); put("lone-jsx.jsx", "romp:from-jsx");
    put("pair.tsx", "message"); put("pair.ts", "click");
    put("pair2.jsx", "message"); put("pair2.js", "click");
    assert.deepEqual(exportedString("webview/lone-tsx", "EV", root), ["romp:from-tsx"], "a .tsx is a module esbuild resolves");
    assert.deepEqual(exportedString("webview/lone-ts", "EV", root), ["romp:from-ts"]);
    assert.deepEqual(exportedString("webview/lone-jsx", "EV", root), ["romp:from-jsx"]);
    assert.equal(exportedString("webview/pair", "EV", root), null, "a .tsx and a .ts on one base are refused (esbuild bundles the .tsx)");
    assert.equal(exportedString("webview/pair2", "EV", root), null, "a .jsx and a .js on one base are refused (esbuild bundles the .jsx)");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

// ── the census: no other road to a window listener ──
//
// The censuses above read what the source spells: an addEventListener call, an onmessage assignment, the names they
// reach. More roads reach a window listener without spelling either, and this census refuses each in a ui/ source file
// (test and types files excluded), read by the TypeScript parser. Whether a receiver is a window it decides by one
// rule, the window rule (refKind), never by spelling. A receiver is a window, this page's own or another, only:
//   (a) by the binder's identity: an identifier whose checker symbol IS the global table's symbol for window, self,
//       globalThis or frames is this page's own window, for top, parent or opener another window, and for document this
//       page's document. An augmented global still counts, and a window-name global the source augmented with a
//       declaration outside the default lib is refused outright; globalThis is held by its symbol name, since the
//       library gives it no declaration to anchor identity. A local that shadows the name with a run-time binding is
//       not the global, and neither is a declaration of the name at the top level of a file TypeScript calls no module
//       (a script), though the checker merges it with the global or resolves a use past it to the global (in a
//       JavaScript file it binds as CommonJS, one with require or module.exports for example, it resolves the use to the
//       file's own local, which (b) reads): esbuild bundles each page into one function, where a run-time declaration is
//       the file's own local (renamed apart where another file of the bundle reads the global), so a use in that file
//       holds it (var document = window; document[k] = f sets the window's handler), and where esbuild drops it as dead
//       code the use is the raw global. Identity decides no use of the name in a script with a declaration of the name
//       that is not ambient (topShadow reads the file's own symbol for the name from the binder's table for the file,
//       SourceFile.locals; a type-only declaration, which esbuild erases, counts too): the census refuses the file
//       outright (the refused list below), and the rule reads a use the checker resolves to the global fail-closed, as
//       (b) reads a binding it does not decide, taking the first kind in (b)'s order among the global's kind and the
//       kinds the file's declarations of the name bind (the example is this page's window read fail-closed). A use in
//       any other file is the global, since the declaration stays in its own file. A shadow whose every declaration is
//       ambient, a module-local `declare var window` (or `declare var document`) esbuild drops, or in a declaration
//       file, binds nothing at run time and is the raw global, read as one. A shadow the source binds at run time that
//       esbuild drops as statically dead code, anywhere but at a script's top level (in a module, in a function or in a
//       block of a script, for example; a script's top-level one refuses, above), binds nothing at run time too, but
//       the census models only the ambient and declaration-file drop (bindsNothingAtRuntime) and reads such a shadow
//       through its declaration; that value is outside this rule and disclosed below;
//   (b) through a chain the checker follows, of at most four steps from the receiver (five names, the window and each
//       local counted: const a = window; a.self.self.self is read, a.self.self.self.self is not). A step is a member
//       read by a literal name, which memberKind reads by its table (the members listed below): x.name, or x[key] with
//       a string literal or a template with no substitution for its key, under any parentheses, casts, satisfies and
//       non-null marks (window["self"], window[("self")], window["self" as string]); an index on a window (frames[0],
//       window["0"]); or a variable the checker resolves a name to, followed through the initialiser of its let, const
//       or var declaration (const w = window) or, for a name destructured in such a declaration, through its object
//       pattern's keys, which cost no step, each key read as the member read or index it names would be (keyKind: const
//       { parent: p } = window, const { ["self"]: w } = window, const { 0: f } = window); a parameter, a catch clause's
//       binding and an import have no such declaration and are not followed. The rule decides a binding by its
//       initialiser only where that initialiser is the binding's value at every use (initIsValue): the checker gives
//       the name one declaration, a let, const or var declaration's own with an initialiser, the name plain or
//       destructured, so no parameter, catch clause's binding or second declaration of the name (a JavaScript expando,
//       the declaration the checker records for a top-level member write such as a[k] = f, writes a member of the
//       value, not the name, and is not counted); the name is no namespace's export and no var of a script's top-level
//       scope, each of which code can set as a property (N.x = w, Reflect.set(window, "x", w)) before or after the
//       initialiser runs; and no reference to it but the initialiser writes it, in a closure or a nested function too.
//       The language service lists the references, and one writes where its isWriteAccess says so (the service's own
//       reading, which marks some reads as writes too, among them a shorthand property naming the binding in an object
//       literal, const o = { d }, and an export specifier, export { d }; either leaves the binding undecided) or where
//       writesBinding finds it the target of a write (an assignment of any operator, ++ or --, a destructuring
//       assignment, a rest element's among them, a for...in or for...of head), read through the parentheses around it
//       and through the casts, satisfies, non-null marks and type arguments around it, which esbuild erases and the
//       service reads as a read ((d as any) = w and d! = w write d); a listed reference that is no identifier of the
//       name, and one inside a JSDoc comment (an @type tag's {typeof d}, a {@link d}), where identAt's walk does not
//       look, leave the binding undecided. A use that runs before the initialiser then finds a let or const in its temporal dead zone, which
//       throws, or a var still undefined, never another value, unless esbuild drops the declaration as dead code (the
//       release build, and the default build for some forms; disclosed below). The rule does not decide any other
//       binding, for example one of more than one declaration (a redeclared var; a parameter a var of the name
//       redeclares, function h(x) { x[k] = f; var x = document }, where the write runs before the var's initialiser and
//       x still holds the argument), one written other than by its initialiser (var x = document; x = window, or (x as
//       any) = window), a namespace's export or a var of a script's top-level scope. Which value such a binding holds
//       at a use is outside the rule, which reads it fail-closed: as the first, in the order this page's window,
//       another window, the body element, a document the census cannot tell is this page's, that any of its
//       declarations binds, this page's own window read as a window whose document the census cannot tell is this
//       page's and this page's own document as a document the census cannot tell is this page's (var w = 0; var w =
//       window is this page's window; var d = document; d = w is such a document). Each of those kinds refuses a
//       computed member, and a handler on the first is a census site. The other kinds are dropped, so a member that
//       only a dropped kind has reads as nothing (var x = window; var x = document; x.body is not read as the body);
//   (c) as `this` where the census's global-this test (thisIsGlobal) reads it as the global object, by position:
//       walking out from it past any arrow functions, it reaches a plain function (a function declaration or expression
//       that is not an object literal's property) or the file before any class, method, constructor, accessor, static
//       block or property declaration. The rule reads that `this` fail-closed, as this page's window whose document the
//       census cannot tell is this page's: a plain function's depends on the call (o.m() runs m with o as its `this`),
//       and the file's own, with no function but an arrow function between, need not be the window either: in a page
//       bundle esbuild rewrites a file's top-level `this` to the file's exports object, wrapping the file as CommonJS,
//       where the file has no ES export statement (an export of a type or an interface is one; TypeScript's export = is
//       CommonJS, and a file whose export is one is wrapped), no import.meta and no .mjs or .mts suffix, whether or not
//       it imports (this.document = window; this.document[k] = f then sets the window's handler), and to undefined in
//       any other file, where that code throws; a file with a top-level await the page build (target es2020) refuses to
//       build at all.
// A window value reached any other way is outside the census: this rule discloses every such value, and the list of
// what the rules cannot see, below, gives examples. A binding or `this` the rule reads fail-closed it decides no
// further than that reading: which value it holds is outside the rule. The census states the rule instead of deciding
// by the checker's types: a type-based form, refusing a computed access on any receiver typed any, unknown, object,
// Window or typeof globalThis (or a union or intersection holding one) or typed by a type parameter bounded by object,
// would refuse 201 of the 1,686 computed accesses live in ui/ (measured at b3eb94f8a): 198 of them through any (129 in
// JavaScript files, 69 in TypeScript) and 3 through a type parameter bounded by object, in two helpers of one file.
// Adding every other type a Window can be assigned to ({}, Record<string, any> and the like) would refuse 91 more, 292
// in all (289 by assignability alone, plus the same 3 bounded type parameters, to which the checker assigns no Window).
// What the rule reads as each kind:
//   - this page's own window: window, self, globalThis and frames (which a browser answers with the window itself),
//     where (a) decides the name; any of them reached through another (window.self, window.frames); this page's
//     document's defaultView (document, or this window's document, or a local initialised to one); a local initialised
//     to any of these or destructured from one (const { defaultView } = document), where the rule decides the local by
//     its initialiser. Read fail-closed as this page's window whose document the census cannot tell is this page's: a
//     binding the rule does not decide that one of its declarations binds to this page's window, a name (a) does not
//     decide because its file declares it at its top level, where the global or one of those declarations is this
//     page's window (var document = window in a script), a `this` (c) reads as the global object (the file's own or a
//     plain function's), and any of those reached through another (w.self, this.window);
//   - a window other than this page's own: top, parent and opener (where (a) does not decide the name, because its file
//     declares it at its top level, it is read so unless one of those declarations binds this page's window); any of
//     those reached through a window (window.parent, parent.top); another window's own names for itself (parent.self,
//     top.window, parent.frames) and its document's defaultView (top.document.defaultView); an indexed window
//     (frames[0], window[0], parent.frames[0]); a frame's contentWindow; the defaultView of any document the census
//     cannot tell is this page's (el.ownerDocument.defaultView); and an event's view, target, currentTarget or
//     srcElement, each of which can hold a window; and a local initialised to any of these or destructured from one
//     (const { parent: p } = window);
//   - the body element, whose onmessage is its window's: the body of any document (this page's, a window's, any
//     ownerDocument or contentDocument, a local initialised to one) and a local initialised to it or destructured from a
//     document (const { body } = document).
//   - a document the census cannot tell is this page's (otherDocument): any ownerDocument or contentDocument, whatever
//     holds it (memberKind reads the member name, since an ordinary object can hold a window under it); a document
//     reached through a window other than this page's own (top.document) or through this page's window read fail-closed
//     (w.document, for a w the rule does not decide, and this.document); this page's own document in a binding the rule
//     does not decide, read fail-closed (var d = document; d = w); document where (a) does not decide it because its file
//     declares it at its top level, and none of those declarations binds this page's window, another window or the body
//     (var document; document = w in a script); and a local initialised to one or destructured from another window
//     (const { document: d } = parent);
//   - this page's own document: the bare document where (a) decides it, this page's window's document (window.document,
//     self.document) and a local the rule decides initialised to one or destructured from this page's window (const d =
//     document, const { document: d } = window). It is the one kind whose computed member the census does not refuse,
//     since the document's own handlers are not the window's; what such a member holds (its body or its defaultView:
//     document[k1][k2] = f sets the window's handler) is outside the rule, disclosed below.
// Refused:
//   - a method of a window (this page's or another), of a document the census cannot tell is this page's, of the body
//     element or of a prototype read by a name computed at run time. A document the census cannot tell is this page's
//     is read fail-closed, as a window is: an ordinary object holds a window under a property named ownerDocument or
//     contentDocument, so memberKind reads that member as such a document whatever the base, and a binding the rule
//     does not decide can hold any value, so at run time the receiver can be the window (holdsWindowMethods; this
//     page's own document, as the rule decides it, is trusted and left). A prototype holds the same methods (protoRef):
//     every DOM interface's chain ends at EventTarget.prototype, which holds addEventListener, so X.prototype for any
//     X, any __proto__, and what Object.getPrototypeOf or Reflect.getPrototypeOf returns count with the window. Refused
//     on any of them: a member read by a computed name (window["add" + "EventListener"], a template with a
//     substitution, a variable key), whether called, assigned or read; Reflect.get, Reflect.getOwnPropertyDescriptor or
//     Object.getOwnPropertyDescriptor with a key that is not a literal, and Object.getOwnPropertyDescriptors, which
//     hands on every member under its name; a destructuring pattern with a key computed at run time (const { [k]: add }
//     = window); and a reflective write whose key or keys are computed (Reflect.set, Reflect.defineProperty,
//     Object.defineProperty or __defineSetter__ with a key that is not a literal; Object.assign or
//     Object.defineProperties from an object literal with a computed key or a spread; a new prototype for the window).
//     A string or numeric literal key, quoted, in brackets or under a cast (window[("self")], const { ["self"]: w } =
//     window), is no computed name: it is a literal name (or index), read by rule (b). A bigint key is refused as a
//     computed key wherever isLiteralKey gates the refusal, since isLiteralKey takes no bigint: an element access on
//     any of these receivers, read, called or written (window[0n], window[0n].focus(), window[0n] = f), a key in
//     brackets in a pattern (const { [0n]: w } = window) and a reflective key (Reflect.get(window, 0n),
//     window.__defineSetter__(0n, f)). keyKind reads a bigint as an index only where refKind resolves a receiver
//     through it (window[0n].onmessage = f is another window's handler, refused as that too) and in a bare pattern key
//     (const { 0n: w } = window, a frame's window, rule (b)). A literal key naming addEventListener or onmessage under
//     parentheses or a cast (window[("addEventListener")], window[("onmessage")] = f) is a spelling the head censuses
//     do not read: the addEventListener form is refused by the addEventListener census, and window[("onmessage")] = f
//     by this census's handler arm, not resolved by rule (b);
//   - a function run with a window as its `this`, however the function was reached: .call, .apply or .bind with the
//     window named as the first argument (or the second, on a .call or .apply of .call or .apply), and Reflect.apply with
//     the window as its second. A method of any other EventTarget (an element, the document) read by a computed name
//     registers on the window this way, or with no receiver at all (below). `this` does not count as the window here:
//     a wrapper passes its own `this` on (md-block-start.ts's, which marked calls with its lexer), and that is disclosed;
//   - an onmessage or onmessageerror handler set any way but a plain assignment this census accepts. The name may be an
//     assignment's target, a member of a type, or a read that is only tested, and nothing else (Object.assign(window,
//     { onmessage: f }), Reflect.set(window, "onmessage", f), window.onmessage ??= f are refused). The assignment is
//     accepted in three cases only: on this page's own window or the bare global, where it is a census site above; on
//     any other receiver but another window, when the value sets no handler (null, or an unshadowed undefined, at the
//     end of an assignment chain: dead.onopen = dead.onmessage = null); and on a name socketRefusal proves a WebSocket.
//     The proof reads TypeScript's binder, through the checker of one program over the files the census reads (under
//     vscode-extension/tsconfig.json's options; the section above socketRefusal says why that program), and fails
//     closed. The checker's symbol for the name has one declaration, a let, const or var statement's own, neither
//     ambient (`declare`) nor a namespace's export; it is bound by an initialiser new WebSocket(...) and written
//     nowhere else, or has no initialiser and one write, `name = new WebSocket(...);`, a statement of its own directly
//     in the try block of a try that follows the declaration in its statement list, has no finally, and whose catch
//     ends in a return and holds no break, continue or label, with every read after that try, inside the declaration's
//     statement list and not inside a function declaration there (federation.ts's connect(); socketRefusal's clause 2
//     states the shape); every write is found through the language service's findReferences, in closures, nested
//     functions and destructuring targets too, a reference writing where its isWriteAccess says so or where
//     writesBinding finds it a write's target through the casts, satisfies, non-null marks and type arguments esbuild
//     erases ((ws as any) = w), and a walk over every identifier of the name, each resolved by the checker, agrees with
//     it (a name the checker cannot resolve refuses); and the WebSocket that new calls resolves to a library global,
//     every declaration of it in a TypeScript default lib or under node_modules/@types, a project .d.ts declaration
//     refusing. Where the checker's scopes may not be the page's the
//     proof refuses: a syntax or binder error in the file; in any file, a function declaration of ANY name declared in a
//     block, refused by its position (a plain one a sloppy-mode file hoists into its enclosing function past the checker's
//     block scope; an async, generator or async-generator one, which Annex B never hoists, refused all the same so the rule
//     needs no case on the kind: a file TypeScript calls a module can run as sloppy code, esbuild bundling a .cjs or .cts
//     file with no import or export statement, and a TypeScript file whose only module syntax is import x = require(...) or
//     export =, as CommonJS);
//     and, in a file TypeScript calls no module, a top-level declaration of a name the new expression reads (its
//     WebSocket, and in new window.WebSocket(...) the window), which the checker merges with the library's declarations
//     or sets apart.
//     The refusal names the site. Its one precondition: the page's global WebSocket is the browser's own. The name
//     WebSocket is refused below, and a global WebSocket replaced through an object built elsewhere with a computed key
//     and copied onto the window is on the list of what the rules cannot see; through it a socket the census accepts
//     can be the window. A window other than this page's own is refused whatever the value. On every other receiver the
//     census resolves to neither this page's window nor a socket (the body element, a parameter, a call's result, an
//     object's property, a MessagePort, a worker, a channel), a value that sets a handler is refused;
//   - a message or messageerror listener added to a window other than this page's own (parent.addEventListener(...)),
//     where a check at its head could not be about this page's senders;
//   - code run from a string: eval, the Function constructor (by name, or reached through a function's .constructor),
//     a timer handed a string, an import() whose specifier is not a string literal (the URL it builds at run time can be
//     a data: or blob: URL holding code), and a module specifier that is a data: URL (in an import, an export ... from,
//     an import() or a require; esbuild bundles the URL's text as code). The timer arm reads a callee named setTimeout
//     or setInterval, as a name or as a member on any receiver (w.setTimeout, document.defaultView["setTimeout"]), after
//     parentheses and a comma expression's last operand ((0, setTimeout)), handed a string literal, a template, a +
//     expression, an array or object literal (a timer turns what is no function into a string) or a variable (const, let
//     or var) whose initialiser is one of those; and such a callee used as a template's tag (setTimeout`go()`), which
//     hands it the template's strings as an array;
//   - a module specifier naming a test or types file (one UI_CLASSES' first class takes, as written or with a suffix
//     esbuild adds or swaps: ./x.d finds x.d.ts, ./x.test.js finds x.test.ts), which esbuild bundles like any module and
//     no census reads; a type-only import is erased, and left;
//   - a module specifier holding a ? or a #, or ending in / or /., whatever it names: esbuild strips the query or the
//     hash, and normalizes the trailing / or /., before it resolves, so the census cannot tell what the specifier names
//     (./zz.test.ts?v=1 and ./zz.test/ bundle a test file);
//   - a require() whose specifier is not a string literal (a concatenation, a template with a substitution, (require)(...)
//     among them), which esbuild bundles as every file its pattern can match, test and types files among them; an alias
//     of require and window.require are no pattern esbuild reads, and left;
//   - a `with` statement, which answers any name inside it from an object the census cannot read (a write to a socket's
//     binding, the WebSocket constructor, undefined; the socket proof refuses a file that holds one too, as a binder
//     error of strict code);
//   - the name WebSocket, as a name or a string, anywhere but as the constructor a `new` calls (bare or as a member)
//     and in a type: a replaced global WebSocket (window.WebSocket = f, Object.defineProperty(window, "WebSocket",
//     ...), a class of that name) would make the socket the census accepts any object. This refusal is how the census
//     holds the socket proof's precondition, that the global WebSocket is the browser's own, in the source it reads;
//     the copied-object road listed below, which the rules cannot see, can still replace the constructor;
//   - a file TypeScript calls no module that declares window, self, globalThis, frames, top, parent, opener or document
//     at its top level (in the file's own scope, which a var in a block there joins; a let, const or class in a block
//     is the block's own), with a declaration that is not ambient (rule (a), topShadow): in the page bundle a use of
//     the name in that file holds the file's own local where esbuild keeps the declaration, and the raw global where it
//     drops it as dead code (if (false) { var document = window } document.body[k] = f sets the window's handler
//     through the body in the release build), and the census reads neither, so it refuses the file, one refusal per
//     name, at the name's first declaration. The test reads TypeScript's isExternalModule and whether a declaration is
//     ambient, so it also refuses files where that reason does not arise: one whose only declaration of the name is
//     type-only (an interface, a type alias or a namespace holding only types, for example), which esbuild erases,
//     leaving the use the raw global; and a JavaScript file TypeScript binds as CommonJS (one with require or
//     module.exports, for example), where the checker resolves a use to the file's own local. A module's top-level
//     declaration the checker keeps apart from the global, and rule (b) reads it.
// ui/ has none of these today, so the rules cost nothing. What they cannot see, disclosed:
//   - a window value the window rule above does not decide, however the source reaches it. The rule is the census's
//     whole reading of which receivers are a window, so this entry covers every value outside it, and each value named
//     here is an example: a window held in a parameter, a catch clause's binding or a for...of head; in a let or var
//     assigned later whose declarations bind none of the rule's kinds (let w; w = window); behind a comma, conditional,
//     || or ?? expression; in a Proxy; in an object or array it was put in (a namespace's exported member among them),
//     or taken out of an array by an array pattern; as a destructuring default (const { x: w = window } = {}, whose key
//     alone the rule reads); returned by a function (Object(window) among them); imported from another module (refKind
//     does not follow an import); reached in more steps than the rule's chain takes (const a = window;
//     a.self.self.self.self); read off this page's own document by a computed key (document[k1][k2] = f, through its
//     body or its defaultView); held by a name whose window initialiser the checker split into a symbol of its own (var
//     w = window beside function w in a JavaScript script, where the use resolves to the function symbol) or whose
//     window is a call's result (var w = 0; var w = getWin()); a member only a kind the rule dropped has, on a name it
//     reads fail-closed, which takes its first kind alone (var x = window; var x = document; x.body, the body at run
//     time), and a member of a value it reads fail-closed that the kind it takes does not reach (var d = document; d =
//     o; d.self, the window when o holds one there); and a `this` the global-this test reads as not the global object,
//     such as that of an object literal's function or method called without a receiver, which runs with the window as
//     its `this` when the function is defined as sloppy code (every ui/ source but romp-timeline-view.js has no `use
//     strict` directive, so a function defined at its top level is sloppy; a function defined in a class body is strict
//     in any file, so its `this` called with no receiver is undefined, not the window; the definition site decides, not
//     where the call is). An onmessage handler set on such a receiver is refused (a receiver the census cannot resolve
//     to this page's window or to a socket). A method read off it, or a member written on it, under a computed key is
//     not, unless the rule reads the receiver as a kind whose computed member it refuses: a window held under a
//     property named ownerDocument or contentDocument, read as a document the census cannot tell is this page's, and a
//     binding the rule does not decide one of whose declarations binds a window, the body element or a document, read
//     fail-closed (function h(x) { x[k] = f; var x = document });
//   - a window or document name the source shadows with a declaration esbuild drops as statically dead code, anywhere
//     but at a script's top level (in a module, in a function or in a block of a script, for example; a script's
//     top-level declaration of the name refuses, in the list above), where a use of the name is the raw global at run
//     time. Measured with the page's own build options (vscode-extension/esbuild.js's webview), the declarations it
//     drops include, among others: a var at a module's top level whose only declaration sits in if (false) { ... } (or
//     if (0), if (!1), if (void 0)), in the else of an if (true) or after a break out of a labelled block, dropped by
//     the release build (--production, the vscode:prepublish path), or in the catch of a try whose block has no side
//     effect (an empty try, try { 1; }), dropped by the default build too; and a let, const or class after a return in
//     a function (or after if (true) return; or a nested { return; }), after a break or continue in a loop's body or
//     after a break out of a labelled block, dropped by the release build in a module or a script, so that a use before
//     it reads the global instead of throwing in its temporal dead zone (L: { frames[k] = h; break L; let frames = 0; }
//     in a script sets the window's handler in the release build). esbuild keeps, for example, a dead var inside a
//     function (in a dead branch, or after a return or a throw), in a namespace body or in a class static block, a
//     let, const or class after a throw, and a function declaration after a return; a let, const or class in a dead
//     braced branch is block-scoped, so a use outside it is the global in every build, which the census reads,
//     refusing a computed member written on it. The census reads the name through the declaration the checker
//     resolves it to: a class, or an initialiser refKind reads as nothing (var frames = 0), gives null, and a
//     document-valued initialiser gives that document, so a computed member written on the name is not refused; a
//     window-valued initialiser gives the window, whose computed member is refused but whose body the census reads as
//     nothing (L: { document.body[k] = h; break L; let document = window; } in a script sets the body's handler in the
//     release build). It reads a handler on the name as the declared value's, not the raw global's. It models only the
//     ambient and declaration-file drop (bindsNothingAtRuntime), not esbuild's dead-code elimination of a live
//     declaration. Witnessed by the unseen rows below, each in a module: zz-deadvar-null-drop (an initialiser refKind
//     reads as nothing, var frames = 0), zz-deadvar-document-drop (a document initialiser), zz-deadtry-catch-drop (an
//     empty try's catch) and zz-deadlet-return-drop (a let after a return); no row there witnesses a block of a script;
//   - the body element reached other than as the window rule reads it (a document's body), for example by a query for
//     it, a frameset or document.documentElement.lastElementChild. A member written on it under a computed key sets its
//     window's handler;
//   - an event's source under a computed key (e.source[k] = f): source cannot join the event members above, since two
//     live reads index an object's `source` string;
//   - a method of another EventTarget (an element, the document) read by a computed name and called with no receiver:
//     WebIDL runs an operation called with no `this` on the global object, so `const add = document.documentElement[k];
//     add("message", f)` registers on the window; and such a method run on `this` where `this` is the window;
//   - a reflective or prototype function reached any way but by its Reflect. or Object. spelling (globalName takes only
//     a leading window., self. or globalThis. off): under another name (const R = Reflect; R.get(window, k)); through
//     frames (this page's own window), another window or a comma expression (frames.Reflect.set(window, k, f),
//     parent.Reflect.set(window, k, f), (0, Reflect.set)(window, k, f), and a prototype read the same way,
//     frames.Object.getPrototypeOf(window)[k] = f); or run with the window among its arguments through .call, .apply or
//     Reflect.apply (Reflect.set.call(null, window, k, f), Reflect.apply(Reflect.set, null, [window, k, f])); and a
//     Function.prototype.call reached any way but by name;
//   - an object built elsewhere with a computed key and copied onto the window (Object.assign(window, make()) is read as
//     its call only), which can also replace the global WebSocket, so a socket the census accepts is the window (the
//     road census's test holds such rows accepted, in its `unseen` rows); and a key computed in another module and
//     passed to a reflective read or write through a helper;
//   - a top-level var of a classic script rebound through the global object by a call (Reflect.set(window, "ws", w),
//     Object.assign(window, { ws: w })): the socket proof's checker reads window.ws, this.ws and window["ws"] as the
//     var and refuses them, but not a string a call is handed (the `unseen` rows hold both calls accepted). No ui/
//     source runs as a classic script today: esbuild bundles each, and the kernel inlines romp-timeline-view.js inside
//     a function;
//   - a test or types file the build puts in a page other than through a module specifier: a bundle's entry point or an
//     alias in vscode-extension/esbuild.js or its tsconfig.json, which no census reads;
//   - a resolver configuration in a directory above the repo root (a package.json's browser field, a tsconfig.json's or
//     jsconfig.json's paths), which esbuild reads on its way up from a ui/ module and no census reads; ui/ and the repo
//     root are held to none;
//   - a string that reaches a timer other than as the timer arm reads it: through a parameter, a later assignment, a
//     call's result, a member or an import; and a timer handed on before it is called (setTimeout.call or .apply, an
//     alias, a binding destructured from a window, Reflect.apply);
//   - code the build takes from outside ui/: vendor/track-changents and npm packages (marked, dompurify, highlight.js
//     and katex in the page bundles, CodeMirror in the editor chunk, pdfjs-dist in the pdf chunk), and the pdf worker, an
//     entry point built from node_modules/pdfjs-dist. Measured at 11ed4313c through the built bundles' source maps, every
//     window message listener in them is one of the 16 gated ui/ sites, and pdfjs-dist listens only on a Worker, a port
//     or the worker's own scope, never on a window;
//   - the inline scripts vscode-extension/src/extension.ts writes into the VS Code webview documents (mediaBaseTag's, and
//     the kernel-base script in buildHtml and buildFeedHtml), which run in the same frame as the bundles. At 11ed4313c
//     none of the three adds a message listener, and no file of vscode-extension/src but its tests holds one;
//   - code handed to the DOM as markup or a URL (a script element, an inline handler attribute, a javascript: URL),
//     which is no JavaScript the parser reads.

/** The windows a script can name that are not its own (WINDOW_NAMES are its own): top, parent and opener. */
const OTHER_WINDOW_NAMES = new Set(["top", "parent", "opener"]);
/** Every name a script reaches a window by: its own and the others. */
const WINDOW_GLOBALS = new Set([...WINDOW_NAMES, ...OTHER_WINDOW_NAMES]);
/** The members the census treats as a window whatever holds them: a document's window (defaultView), a frame's
 *  (contentWindow), and view, target, currentTarget and srcElement, which on an event can each hold a window. They are
 *  read so on every holder, fail-closed, though on most they hold no window (an anchor's target is a string, a click's an
 *  element). A defaultView is this page's own window when its document is this page's (memberKind); every other one of
 *  these is a window the census cannot tell from another. ownerDocument and contentDocument (memberKind) are the document
 *  members read fail-closed the same way: each is a document the census cannot tell is this page's (otherDocument) on
 *  every holder, since an ordinary object can hold a window under either name, and a computed member on such a document is
 *  refused (holdsWindowMethods) as it is on a window. */
const WINDOW_MEMBERS = new Set(["defaultView", "contentWindow", "view", "target", "currentTarget", "srcElement"]);
/** The name a literal key reads as: a string literal or a template with no substitution, under any parentheses, casts,
 *  satisfies and non-null marks ("self", ("self"), "self" as string), the census's literal key (isLiteralKey) when it
 *  is a string; else null. */
const keyName = (k: any): string | null => { const u = k && unwrap(k); return u && ts.isStringLiteralLike(u) ? u.text : null; };
/** The name of `x.name`, or of `x[key]` with a literal key (keyName: x["name"], x[("name")], x["name" as string]); else
 *  null. */
const memberName = (n: any): string | null => ts.isPropertyAccessExpression(n) ? n.name.text
  : ts.isElementAccessExpression(n) ? keyName(n.argumentExpression) : null;
/** What a receiver is, by the road census's window rule (refKind): this page's own window, a window other than this
 *  page's own (or one the census cannot tell from another), this page's document, a document the census cannot tell is
 *  this page's, or a document's body element, which reflects its window's event handlers. */
type RefKind = "window" | "otherWindow" | "document" | "otherDocument" | "body";
/** What the rule reads a receiver as while it walks a chain (ruleKind): a RefKind, or this page's own window read
 *  fail-closed (failClosedWindow), from a value the rule does not decide: a binding whose initialiser is not its value
 *  at every use, and a `this` rule (c) reads as the global object, a plain function's, which a call can give another
 *  value, or the file's own, which esbuild rewrites in a page bundle to the file's exports object or to undefined.
 *  refKind answers it as this page's own window, so a computed member of it is refused and a handler on it is a census
 *  site, but its document is one the census cannot tell is this page's (memberKind), since the value can be an object
 *  that holds a window there. */
type RuleKind = RefKind | "failClosedWindow";
/** The kind of member `key` of something of kind `from` (null: resolved to nothing), or null. A window read fail-closed
 *  has a window's members, but its document is one the census cannot tell is this page's. */
function memberKind(from: RuleKind | null, key: string): RuleKind | null {
  if (WINDOW_MEMBERS.has(key)) return key === "defaultView" && from === "document" ? "window" : "otherWindow";
  // read fail-closed whatever the base: an ordinary object can hold a window under either name, so a computed member on
  // the result is refused (holdsWindowMethods reads otherDocument as it does a window)
  if (key === "ownerDocument" || key === "contentDocument") return "otherDocument";
  if (from === "window" || from === "failClosedWindow" || from === "otherWindow") {
    if (WINDOW_NAMES.has(key)) return from;
    if (OTHER_WINDOW_NAMES.has(key)) return "otherWindow";
    if (key === "document") return from === "window" ? "document" : "otherDocument";
  }
  if ((from === "document" || from === "otherDocument") && key === "body") return "body";
  return null;
}
/** Whether a key is an index: a numeric or bigint literal or an all-digit string, under any parentheses, casts and
 *  non-null marks (frames[0], window["0"], and the pattern keys of const { 0: w } = window). */
const isIndexKey = (k: any): boolean => {
  const u = k && unwrap(k);
  return !!u && (ts.isNumericLiteral(u) || ts.isBigIntLiteral(u) || (ts.isStringLiteralLike(u) && /^\d+$/.test(u.text)));
};
/** The kind the key `k` reads off something of kind `from`, one step of rule (b): an index (isIndexKey) on a window is
 *  a frame's window, another; a literal name (keyName) by memberKind; any other key null. An element access's key and a
 *  destructuring pattern's key (patternKind) are both read here, so a key reads the same written plain, quoted, in
 *  brackets or under a cast (window.self, window[("self")], const { ["self"]: w } = window). */
function keyKind(from: RuleKind | null, k: any): RuleKind | null {
  if (isIndexKey(k)) return from === "window" || from === "failClosedWindow" || from === "otherWindow" ? "otherWindow" : null;
  const name = keyName(k);
  return name === null ? null : memberKind(from, name);
}
/** Rule (c) of the road census's window rule: whether `this` at `n` is read as the global object, by position alone.
 *  Walking out from `n` past any arrow functions, the first of these it reaches decides: a class (anything inside the
 *  class's node), a method, a constructor, an accessor, a static block or a property declaration, not the global; a
 *  function declaration or expression, the global unless it is the value of an object literal's property; the file, the
 *  global. It reads no call: a plain function called as a method is read as the global (fail closed), and an object
 *  literal's function or method called without a receiver, which runs with the window as its `this` when it is defined as
 *  sloppy code (defined outside a class body, in a file with no `use strict` directive; the definition site decides the
 *  strictness, not where the call is), is not, a window value outside the rule that the road census discloses by it. */
function thisIsGlobal(n: any): boolean {
  for (let s = n.parent; s; s = s.parent) {
    if (ts.isArrowFunction(s)) continue;
    if (ts.isClassLike(s) || ts.isMethodDeclaration(s) || ts.isConstructorDeclaration(s) || ts.isGetAccessor(s) || ts.isSetAccessor(s)
        || ts.isClassStaticBlockDeclaration(s) || ts.isPropertyDeclaration(s)) return false;
    if (ts.isFunctionDeclaration(s) || ts.isFunctionExpression(s)) return !(ts.isPropertyAssignment(outer(s).parent) || ts.isObjectLiteralExpression(outer(s).parent));
    if (ts.isSourceFile(s)) return true;
  }
  return false;
}
/** How the rule reads a binding it does not decide by its initialiser (ruleKind): each declaration's kind read
 *  fail-closed (failClosed), and the first of these that any declaration binds: this page's window read fail-closed,
 *  another window, the body element, a document the census cannot tell is this page's. Each refuses a computed member,
 *  and this page's own window comes first, so a handler on a name any declaration makes this page's window is a census
 *  site. The kinds after the first are dropped: a member only one of them has reads as nothing (var x = window; var x =
 *  document; x.body), a window value outside the rule that the road census discloses by it. */
const MULTI_ORDER: RuleKind[] = ["failClosedWindow", "otherWindow", "body", "otherDocument"];
/** A kind read fail-closed, for a value the rule does not decide: this page's own window as a window read fail-closed,
 *  and this page's own document as a document the census cannot tell is this page's; each other kind already refuses a
 *  computed member and stays as it is. */
const failClosed = (k: RuleKind | null): RuleKind | null => k === "window" ? "failClosedWindow" : k === "document" ? "otherDocument" : k;
/** Whether the declaration `d` is a JavaScript expando: the name in a top-level member assignment (a.x = v, a[k] = v),
 *  which TypeScript records as a declaration of the name's symbol though it writes a member of the value. */
const isExpandoDecl = (d: any): boolean => ts.isIdentifier(d) && (ts.isPropertyAccessExpression(d.parent) || ts.isElementAccessExpression(d.parent))
  && d.parent.expression === d;
/** The kind `n` has by the road census's window rule (ruleKind), or null, a window read fail-closed answered as this
 *  page's own window. */
function refKind(n: any, res: Res, depth = 0, noThis = false): RefKind | null {
  const k = ruleKind(n, res, depth, noThis);
  return k === "failClosedWindow" ? "window" : k;
}
/** The kind `n` has by the road census's window rule, or null. This function is the rule, stated in the road census's
 *  comment; a window value it answers null for is outside the census and disclosed by the rule there:
 *  (a) identity: a name whose checker symbol IS the global window, self, globalThis or frames is this page's own
 *      window; top, parent or opener another; document this page's document (res.windowKind, by identity, so an
 *      augmented window global still counts, and ruleKind records the augmentation for looseRoads to refuse). Identity
 *      decides no use of the name in a file that declares it at its top level as a script, with a declaration that is
 *      not ambient, a type-only one included (res.topShadow: the checker merges that declaration with the global or
 *      resolves the use past it, while esbuild keeps a run-time one the file's own local in the page bundle; in a
 *      JavaScript file the checker binds as CommonJS the use resolves to the local, which (b) reads): looseRoads refuses
 *      the file, and this reads a use that resolves to the global fail-closed, the first of MULTI_ORDER among the
 *      global's kind and the kinds the file's declarations of the name bind, each read fail-closed (var document =
 *      window: this page's window read fail-closed). A window name whose symbol is a shadow the source added but that
 *      binds nothing at run time (its every declaration ambient, a module-local `declare var window` esbuild drops, or
 *      in a declaration file) is the raw global at run time, read as this page's own window or another by name. A
 *      shadow the source binds at run time anywhere but at a script's top level (in a module, in a function or in a
 *      block of a script, for example) that esbuild drops as statically dead code is the raw global too, but this reads
 *      it through its declaration, not as the global: that value is outside the rule and disclosed in the road census's
 *      "cannot see" list;
 *  (b) a chain of at most four steps from `n`, each one level deeper, null at a fifth (const a = window;
 *      a.self.self.self is a window, a.self.self.self.self null): a member read by a literal name, x.name by memberKind
 *      and x[key] by keyKind (a literal key under any parentheses, casts, satisfies and non-null marks:
 *      window[("self")]); an index on a window (frames[0], window[0]), a frame's, another; a local variable the checker
 *      resolves the name to, read by declKind: through the initialiser of its let, const or var declaration (const w =
 *      window hops to window) or, for a name destructured in one, through its object pattern's keys (patternKind, each
 *      key by keyKind as the element access with that key reads: const { ["self"]: w } = window; the keys cost no
 *      step). It decides a binding by its initialiser only where that initialiser is the binding's value at every use
 *      (res.initIsValue): the checker gives the name one declaration (a JavaScript expando aside), a let, const or var
 *      declaration's own with an initialiser, the name plain or destructured, so no parameter, catch clause's binding
 *      or other declaration beside it; it is no namespace's export and no var of a script's top-level scope, either of
 *      which code can set as a property; and no reference writes the name but that initialiser (a reference the
 *      language service's isWriteAccess or writesBinding reads as a write, the latter through every cast, satisfies,
 *      non-null mark and type argument esbuild erases: (x as any) = window, x! = window). A use that runs before the
 *      initialiser then finds a let or const in its temporal dead zone, which throws, or a var undefined, never another
 *      value (esbuild's drop of a dead declaration aside, disclosed in the road census). The rule does not decide any
 *      other binding (for example a parameter a var redeclares, function h(x) { x[k] = f; var x = document }; a var
 *      written later, var x = document; x = window): it reads the kind each declaration binds fail-closed and takes the
 *      first in MULTI_ORDER any of them binds, and drops the rest (var x = window; var x = document; x.body is null);
 *  (c) `this`, where thisIsGlobal reads it as the global object (and never under noThis), is a window read fail-closed:
 *      a plain function's depends on the call (o.m() runs m with o as its `this`), and the file's own need not be the
 *      window: in a page bundle esbuild rewrites it to the file's exports object, wrapping the file as CommonJS, where
 *      the file has no ES export statement (an export of a type or an interface is one; TypeScript's export = is
 *      CommonJS, and a file whose export is one is wrapped), no import.meta and no .mjs or .mts suffix, whether or not
 *      it imports, and to undefined in any other file (the page build, target es2020, refuses a top-level await).
 *  A value the rule does not decide is read fail-closed, so no road from it reaches a kind the census trusts: this
 *  page's window as a window whose document the census cannot tell is this page's (failClosedWindow, which refKind
 *  answers as this page's own window), and this page's document as a document the census cannot tell is this page's.
 *  Anything else is null, for example: an import (not followed), a parameter, a catch clause's binding, a call's
 *  result, a name none of whose declarations binds one of these kinds, a window a declaration the checker split off
 *  holds (var w = window beside function w in a JavaScript script, the variable a symbol of its own), and a name the
 *  checker cannot resolve. */
function ruleKind(n: any, res: Res, depth = 0, noThis = false): RuleKind | null {
  n = unwrap(n);
  if (depth > 4) return null;
  if (n.kind === ts.SyntaxKind.ThisKeyword) return noThis || !thisIsGlobal(n) ? null : "failClosedWindow";
  // a member read by a literal key or an index (frames[0], a frame's window; window[("self")]), by keyKind
  if (ts.isElementAccessExpression(n) && (isIndexKey(n.argumentExpression) || keyName(n.argumentExpression) !== null)) {
    return keyKind(ruleKind(n.expression, res, depth + 1, noThis), n.argumentExpression);
  }
  if (ts.isPropertyAccessExpression(n)) return memberKind(ruleKind(n.expression, res, depth + 1, noThis), n.name.text);
  if (!ts.isIdentifier(n)) return null;
  const s = res.symAt(n);
  if (!s) return null;
  const fam = res.windowKind(s, n.text);
  if (fam !== null) {
    // a window-name global with a declaration the source added, outside the default lib, is one the census cannot trust
    // is the browser's own: record it, and looseRoads refuses outright (extraDecl is 0 live)
    if (WINDOW_GLOBALS.has(n.text) && res.extraDecl(s)) res.augmented.push({ name: n.text, node: n, sym: s });
    // a use in a file that declares the name at its top level, with a declaration that is not ambient (topShadow; a
    // type-only one counts too): in a script the checker merges that declaration with the global or resolves the use
    // past it to the global, which is how the use reached this branch, but esbuild bundles the file into a function of
    // the page bundle, where a run-time declaration is the file's own local and the use holds it (var document = window;
    // document[k] = f sets the window's handler). Identity does not decide such a use of the name: it is read
    // fail-closed, as the first of MULTI_ORDER among the global's kind and the kind each of the file's declarations of
    // the name binds, every one read fail-closed (0 live: no ui/ script declares a window name or document at its top
    // level)
    const own = res.topShadow(n);
    if (!own) return fam;
    const fc = [fam, ...(own.declarations || []).map((d: any) => declKind(d, n.text, res, depth, noThis))].map(failClosed);
    return MULTI_ORDER.find((k) => fc.includes(k)) || null;
  }
  // a window name whose symbol is a shadow the source added but that binds nothing at run time (its every declaration
  // ambient, a module-local `declare var window: any` esbuild drops) is the untouched global at run time: the identity
  // test above answers "not the global" because the shadow is a separate symbol, but nothing binds the name at run time,
  // so it falls through to the raw global, this page's own window (window, self, globalThis, frames) or another (top,
  // parent, opener). Every road then reads it as that window, the same as a use with no shadow: a computed write on it is
  // refused (the receiver is a window), a literal onmessage on this page's own is a census site. 0 live.
  if (bindsNothingAtRuntime(s)) {
    if (WINDOW_NAMES.has(n.text)) return "window";
    if (OTHER_WINDOW_NAMES.has(n.text)) return "otherWindow";
    if (n.text === "document") return "document";
  }
  if (s.flags & ts.SymbolFlags.Alias) return null;   // an import: a window imported from another module is unseen
  const ds = s.declarations || [];
  const kinds: Array<RuleKind | null> = ds.map((d: any) => declKind(d, n.text, res, depth, noThis));
  // a kind the census trusts (this page's own window, whose handler is a census site, or this page's own document,
  // whose computed member is left) is read through the initialiser only where that is the binding's value at every use;
  // every other kind already refuses, read the same either way, so the write search runs only where it can change the
  // answer
  const trusted = kinds.some((k) => k === "window" || k === "document");
  if (!trusted && ds.length === 1) return kinds[0];
  if (trusted && res.initIsValue(s)) return kinds[ds.findIndex((d: any) => !isExpandoDecl(d))];
  // any other binding: more than one declaration (a redeclared var w = window; var w = window; a decoy beside a window,
  // var w = 0; var w = window; a parameter a var of the name redeclares; and a JavaScript file's top-level name that a
  // top-level expression statement assigns a member of, which the checker records a second, expando declaration for:
  // const b = document.body; b[k] = f), or one whose initialiser is not its value at every use (written elsewhere, a
  // namespace's export, a var of a script's top-level scope, among them). The rule does not decide which value it
  // holds, so it reads each declaration's kind fail-closed and takes the first of MULTI_ORDER that any of them binds,
  // since at run time any of them can be the value at a use: this page's window read fail-closed first, then another
  // window, the body element and a document the census cannot tell is this page's (this page's own document read so),
  // and drops the rest (var x = window; var x = document; x.body reads null, a value outside the rule). declKind reads
  // each declaration as the single-declaration case does, a destructured name included, so a second declaration the
  // checker adds cannot hide the kind the other binds. A name none of whose declarations binds one of these (a socket
  // beside a socket, var ws = new WebSocket; var ws = new WebSocket) is left unresolved for the socket proof; a decoy
  // that only fails to bind a window (var ws = new WebSocket; var ws = window) is read as the window it can be at run
  // time. A declaration whose initialiser binds another value shows nothing on its own, and so does one declKind reads
  // as null (var w; with no initialiser, a parameter, a function, the expando itself). Live: no name of more than one
  // declaration takes this path with a kind; two written bindings do, the loops for (let w = window; ...; w = w.parent)
  // at ui/romp-timeline-view.js:3150 and 3414 (12 identifiers: the two declarations of w and 10 uses), each read as
  // this page's window read fail-closed, which refKind answers as this page's own window.
  const fc = kinds.map(failClosed);
  return MULTI_ORDER.find((k) => fc.includes(k)) || null;
}
/** The kind one declaration `d` binds the name `name` to, rule (b) of the road census's window rule: a let, const or
 *  var declaration's initialiser, read by ruleKind one step deeper (const w = window); a name destructured in such a
 *  declaration, through its object pattern's keys (patternKind: const { parent: p } = window); any other declaration
 *  null (a parameter, a catch clause's binding, a for...of or for...in head's, a function, a class, an import, a
 *  JavaScript expando). Whether the rule reads the binding through it is ruleKind's call (res.initIsValue). */
function declKind(d: any, name: string, res: Res, depth: number, noThis: boolean): RuleKind | null {
  if (ts.isBindingElement(d)) {   // destructured: const { frames: w } = window
    let r: any = d;
    while (ts.isBindingElement(r) || ts.isObjectBindingPattern(r) || ts.isArrayBindingPattern(r)) r = r.parent;
    if (!ts.isVariableDeclaration(r) || !r.initializer) return null;
    return patternKind(r.name, name, ruleKind(r.initializer, res, depth + 1, noThis));
  }
  if (!ts.isVariableDeclaration(d) || !d.initializer) return null;
  return ruleKind(d.initializer, res, depth + 1, noThis);
}
/** The kind destructuring `pattern` from something of kind `from` binds `name` to, at any depth: an identifier key or a
 *  shorthand by memberKind, and a string, a number or a key in brackets by keyKind, as the element access with that key
 *  reads (const { parent: p } = window; const { document: { body } } = window; const { ["self"]: w } = window; const {
 *  0: f } = window, a frame's window). An array pattern, a rest element and a key computed at run time read as null
 *  (looseRoads refuses the last off a window, the body element, a document the census cannot tell is this page's or a
 *  prototype); a default is not read, the key alone deciding (const { x: w = window } = {}: null). */
function patternKind(pattern: any, name: string, from: RuleKind | null): RuleKind | null {
  if (!ts.isObjectBindingPattern(pattern)) return null;
  for (const e of pattern.elements) {
    // the key: a shorthand's or an identifier's name by memberKind; a string, a number or a key in brackets by keyKind,
    // as the element access with that key reads (a key computed at run time reads null, and looseRoads refuses it)
    const pn = e.propertyName;
    const k = e.dotDotDotToken ? null
      : !pn ? (ts.isIdentifier(e.name) ? memberKind(from, e.name.text) : null)
      : ts.isIdentifier(pn) ? memberKind(from, pn.text)
      : keyKind(from, ts.isComputedPropertyName(pn) ? pn.expression : pn);
    if (ts.isIdentifier(e.name)) { if (e.name.text === name) return k; }
    else if (bindsName(e.name, name)) return patternKind(e.name, name, k);
  }
  return null;
}
/** Whether `n` is a window, this page's own or another, by the window rule (refKind). */
function windowRef(n: any, res: Res, depth = 0, noThis = false): boolean {
  const k = refKind(n, res, depth, noThis);
  return k === "window" || k === "otherWindow";
}
/** Whether `n` is this page's own window by the window rule (refKind): a handler set on it is a census site. */
const ownWindowRef = (n: any, res: Res): boolean => refKind(n, res) === "window";
/** Whether `n` is a window other than this page's own, or one the census cannot tell from another, by the window rule
 *  (refKind). */
const otherWindowRef = (n: any, res: Res): boolean => refKind(n, res) === "otherWindow";
/** Whether `n` is a document's body element by the window rule (refKind), which reflects its window's handlers. */
const bodyRef = (n: any, res: Res): boolean => refKind(n, res) === "body";
/** Whether `n` is a document the window rule (refKind) cannot tell is this page's (otherDocument): a member named
 *  ownerDocument or contentDocument on any holder, the document of a window other than this page's own or of a window
 *  the rule reads fail-closed, this page's own document in a binding the rule does not decide, or a local read from
 *  one. Read fail-closed for computed accesses (holdsWindowMethods), since an ordinary object can hold a window under
 *  either name and a binding the rule does not decide can hold any value, so at run time the receiver can be the
 *  window; this page's own document as the rule decides it (kind "document") is trusted and not read here. */
const otherDocumentRef = (n: any, res: Res): boolean => refKind(n, res) === "otherDocument";
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
/** Whether a member read off `n` can be a window's method or its handler: `n` is a window, the body element (whose
 *  onmessage is its window's) or a document the census cannot tell is this page's (otherDocumentRef, read fail-closed
 *  because an object can hold a window under an ownerDocument or contentDocument name and a binding the rule does not
 *  decide can hold any value) by the window rule, or a prototype (protoRef). A window value the rule does not decide is
 *  not read here: a computed member of it is outside the census, disclosed by the rule. */
const holdsWindowMethods = (n: any, res: Res): boolean => windowRef(n, res) || protoRef(n) || bodyRef(n, res) || otherDocumentRef(n, res);
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
const isAssignOp = (k: number): boolean => k >= ts.SyntaxKind.FirstAssignment && k <= ts.SyntaxKind.LastAssignment;
/** Whether an assignment's value, the last of a chain (a = b = null), sets no handler: null, or an unshadowed undefined
 *  (the checker resolves `undefined` to no run-time declaration of its own; a local named undefined refuses). */
function setsNoHandler(v: any, res: Res): boolean {
  v = unwrap(v);
  while (ts.isBinaryExpression(v) && v.operatorToken.kind === ts.SyntaxKind.EqualsToken) v = unwrap(v.right);
  return v.kind === ts.SyntaxKind.NullKeyword || (ts.isIdentifier(v) && v.text === "undefined" && !res.declC(v));
}
/** Whether `a` is `n` or one of its ancestors. */
const holds = (a: any, n: any): boolean => { for (let s = n; s; s = s.parent) if (s === a) return true; return false; };
const hasModifier = (n: any, k: number): boolean => !!n.modifiers && n.modifiers.some((m: any) => m.kind === k);
/** Whether the statement `st` is ambient: it, or a declaration around it, carries `declare`. esbuild drops an ambient
 *  declaration, so its name binds nothing at run time (an ambient var's name is a property of the global object). */
const isAmbient = (st: any): boolean => { for (let s = st; s; s = s.parent) if (hasModifier(s, ts.SyntaxKind.DeclareKeyword)) return true; return false; };
/** Whether the symbol `s` binds nothing at run time: it has at least one declaration and each is ambient (a `declare`,
 *  which esbuild drops) or in a declaration file. A window name that resolves to such a symbol is a module-local shadow
 *  esbuild erases, so at run time the name is the untouched global window (refKind reads it as one). */
const bindsNothingAtRuntime = (s: any): boolean => {
  const ds: any[] = (s && s.declarations) || [];
  return ds.length > 0 && ds.every((d: any) => isAmbient(d) || d.getSourceFile().isDeclarationFile);
};
/** Whether the statement `st` is an export of a namespace body. esbuild reads such a name as a property of the namespace
 *  object, which any code can set, and TypeScript puts it in scope in every block of that namespace, which merge. */
const isNamespaceExport = (st: any): boolean => !!st && ts.isModuleBlock(st.parent) && hasModifier(st, ts.SyntaxKind.ExportKeyword);
/** Whether the identifier `n` sits in a type, where it runs nothing. */
const inTypeNode = (n: any): boolean => {
  for (let s = n.parent; s; s = s.parent) {
    if (ts.isTypeNode(s) && !ts.isExpressionWithTypeArguments(s)) return true;
    if (ts.isStatement(s) || ts.isBlock(s)) break;
  }
  return false;
};
/** Whether the identifier `n` is no binding and no reference: a member or key name, a label, a type's name or a name in
 *  a type. The socket proof asks it only of an identifier the checker resolves to no symbol. */
function namesNoBinding(n: any): boolean {
  const p = n.parent;
  if (ts.isPropertyAccessExpression(p) && p.name === n) return true;
  if ((ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p) || ts.isPropertySignature(p) || ts.isMethodDeclaration(p) || ts.isMethodSignature(p)
       || ts.isGetAccessorDeclaration(p) || ts.isSetAccessorDeclaration(p) || ts.isEnumMember(p)) && p.name === n) return true;
  if (ts.isBindingElement(p) && p.propertyName === n) return true;
  if (ts.isImportSpecifier(p) && p.propertyName === n) return true;
  if (ts.isExportSpecifier(p) && p.propertyName && p.name === n) return true;
  if (ts.isQualifiedName(p) && p.right === n) return true;
  if ((ts.isLabeledStatement(p) || ts.isBreakStatement(p) || ts.isContinueStatement(p)) && p.label === n) return true;
  if ((ts.isTypeAliasDeclaration(p) || ts.isInterfaceDeclaration(p) || ts.isTypeParameterDeclaration(p)) && p.name === n) return true;
  return inTypeNode(n);
}

// ── the socket proof's program ──
//
// socketRefusal reads TypeScript's binder through the checker, so it needs a program. The road census builds ONE, over
// the files it reads: ui/'s modules (uiSources()) and ui/'s declaration files, which type the vendored modules the
// editor chunk imports (webview/vendor-track-changents.d.ts). Its compiler options are
// vscode-extension/tsconfig.json's, with four set here:
//   - allowJs, so the .js modules are in it (checkJs stays off, so for a JavaScript file TypeScript reports its syntax
//     errors and, of its binder's and checker's errors, only those on its list for plain JavaScript: most strict-mode
//     errors, and one type error, a === or !== whose operand is an object, array, regular-expression, function or class
//     literal (TS2839). A word strict code reserves used as a name is dropped in a JavaScript SCRIPT (TS1212) but kept in a
//     JavaScript MODULE outside a class (TS1214, on the list); inside a class body it is TS1213, off the list and dropped
//     even in a module; a duplicate identifier is dropped. The proof's clause 0 reads the binder's own list, so it sees the
//     reserved word wherever TypeScript's diagnostic drops it);
//   - target ESNext, so the checker scopes a parameter's default as the page runs it: under the tsconfig's ES2021,
//     TypeScript resolves a name in a parameter's default to a var of the function's body when a parameter holds a
//     class expression with a static field, for the sake of its own down-levelled output, and at ESNext it does not
//     (with useDefineForClassFields, which the tsconfig does not set, at its default, true from ES2022 on); the road
//     census's test holds such a default refused, a write to the socket in it and a receiver read in it;
//   - alwaysStrict, which the tsconfig's strict sets already, so the binder reads every file as strict code; and
//   - noEmit.
// An import that resolves to a JavaScript file is left unresolved, as tsc leaves it without allowJs, so the vendored
// modules are typed by their declarations and the checker never types a module from its JavaScript. Why this program,
// and not one per file with the lib files: its .ts files are the ones CI's typecheck (npm run typecheck, tsc over the
// same tsconfig) holds to no error, so an error in it is a real one, while a module alone does not resolve its imports,
// so a one-file program reports an error in every module that has any and an error check over it would mean nothing.
// The census fails, loudly, when TypeScript cannot be loaded (loadTypeScript) or the program has an error in a file it
// reads, the options' and the global diagnostics included (censusProgram; the loud-failure test below shows both). An
// error a // @ts-ignore, @ts-expect-error or @ts-nocheck comment hides is hidden here as it is from tsc; the proof's
// own read of the binder's errors (its clause 0) is not. Measured over ui/ at 7dcd705b9: 425 files in the program,
// 188 of them read by the census (187 modules and the one declaration file), about 7 s to build it and check every
// file the census reads and 4 s more for the road census's reads, on a loaded machine; the one socket the census reads,
// federation.ts's in connect(), is proved. A row of the road census's own test is read in a program of its own: the
// same options over that row's one file (fixtureChecked), served by one language service per row file name, each row a
// new version of the file, so the lib and @types files are read once. A row's errors are not checked: the rows hold
// names they never declare (u, f) and constructs TypeScript rejects on purpose, and the proof reads the binder, whose
// own errors clause 0 refuses.
/** A program the socket proof reads, and the file in it the census is at. */
type Checked = { service: any; program: any; checker: any; sf: any };
const TSCONFIG = path.join(EXT, "tsconfig.json");
let socketOptionsRead: any = null;
/** The program's compiler options: vscode-extension/tsconfig.json's, with allowJs, target ESNext, alwaysStrict and
 *  noEmit (the section comment above says why). An error reading them stops the census. */
function socketOptions(): any {
  if (socketOptionsRead) return socketOptionsRead;
  const read = ts.readConfigFile(TSCONFIG, ts.sys.readFile);
  if (read.error) throw new Error("the socket proof's program cannot read " + TSCONFIG + ": " + ts.flattenDiagnosticMessageText(read.error.messageText, " "));
  const parsed = ts.parseJsonConfigFileContent(read.config, ts.sys, EXT, { allowJs: true, target: ts.ScriptTarget.ESNext, alwaysStrict: true, noEmit: true }, TSCONFIG);
  if (parsed.errors.length) throw new Error("the socket proof's program cannot read " + TSCONFIG + ": " + parsed.errors.map((e: any) => ts.flattenDiagnosticMessageText(e.messageText, " ")).join("; "));
  return (socketOptionsRead = parsed.options);
}
/** One document registry for every program here, so each lib and @types file is parsed once. */
const documents = ts.createDocumentRegistry(true, EXT);
/** A language service over `roots` (absolute paths), reading each file in `mem` from there and every other file (the
 *  libs, @types, node_modules) from disk. A file in `mem` is versioned by its text, so a new text is a new document to
 *  the registry. An import that resolves to a JavaScript file resolves to none, as tsc resolves it without allowJs. */
function languageService(mem: Map<string, string>, roots: string[]): any {
  const options = socketOptions();
  const has = (f: string): boolean => mem.has(f) || ts.sys.fileExists(f);
  const read = (f: string): string | undefined => mem.has(f) ? mem.get(f) : ts.sys.readFile(f);
  const moduleHost = { fileExists: has, readFile: read, directoryExists: ts.sys.directoryExists, getDirectories: ts.sys.getDirectories, realpath: ts.sys.realpath };
  return ts.createLanguageService({
    ...moduleHost,
    useCaseSensitiveFileNames: () => ts.sys.useCaseSensitiveFileNames,
    getCompilationSettings: () => options,
    getScriptFileNames: () => roots,
    getScriptVersion: (f: string) => mem.has(f) ? crypto.createHash("sha256").update(mem.get(f) as string).digest("hex") : "disk",
    getScriptSnapshot: (f: string) => { const t = has(f) ? read(f) : undefined; return t === undefined ? undefined : ts.ScriptSnapshot.fromString(t); },
    getCurrentDirectory: () => EXT,
    getDefaultLibFileName: (o: any) => ts.getDefaultLibFilePath(o),
    resolveModuleNameLiterals: (lits: any[], containing: string, redirected: any, _o: any, file: any) => lits.map((l: any) => {
      const r = ts.resolveModuleName(l.text, containing, options, moduleHost, undefined, redirected, ts.getModeForUsageLocation(file, l, options));
      return r.resolvedModule && /^\.[mc]?jsx?$/.test(r.resolvedModule.extension) ? { ...r, resolvedModule: undefined } : r;
    }),
  }, documents);
}
/** Every error TypeScript reports in `program` for `files` (absolute paths), as file:line: TSnnnn message, with the
 *  options' and the global errors; a file missing from the program is one too. */
function programErrors(program: any, files: string[]): string[] {
  const out: string[] = [];
  const say = (d: any): void => {
    const where = d.file ? path.relative(UI, d.file.fileName) + ":" + (d.file.getLineAndCharacterOfPosition(d.start).line + 1) + ": " : "";
    out.push(where + "TS" + d.code + " " + ts.flattenDiagnosticMessageText(d.messageText, " "));
  };
  for (const d of [...program.getOptionsDiagnostics(), ...program.getGlobalDiagnostics()]) if (d.category === ts.DiagnosticCategory.Error) say(d);
  for (const f of files) {
    const sf = program.getSourceFile(f);
    if (!sf) { out.push(path.relative(UI, f) + ": not in the program"); continue; }
    for (const d of [...program.getSyntacticDiagnostics(sf), ...program.getSemanticDiagnostics(sf)]) if (d.category === ts.DiagnosticCategory.Error) say(d);
  }
  return out;
}
/** The census's program over `read` (each file relative to ui/, with the text the census read), as the file each site
 *  is in. It throws, naming every error, when the program has one in a file it reads: the census reads no program with
 *  errors, and has no fallback. */
function censusProgram(read: Array<[string, string]>): (file: string) => Checked {
  const mem = new Map(read.map(([f, text]) => [path.join(UI, f), text] as [string, string]));
  const service = languageService(mem, [...mem.keys()]);
  const program = service.getProgram();
  const errors = programErrors(program, [...mem.keys()]);
  if (errors.length) {
    throw new Error("the socket proof's program (the census's files, under vscode-extension/tsconfig.json's options) has errors in the files the census reads,"
      + " and the census reads no program with errors:\n" + errors.join("\n"));
  }
  const checker = program.getTypeChecker();
  return (file: string): Checked => {
    const abs = path.join(UI, file), sf = program.getSourceFile(abs);
    if (!sf || sf.text !== mem.get(abs)) throw new Error("the socket proof's program does not hold " + file + " as the census read it");
    return { service, program, checker, sf };
  };
}
const fixtureServices = new Map<string, { mem: Map<string, string>; service: any }>();
/** The program a row of the road census's test is read in: the census's options over the row's one file, at
 *  ui/<file>. */
function fixtureChecked(file: string, src: string): Checked {
  const abs = path.join(UI, file);
  let f = fixtureServices.get(abs);
  if (!f) { const mem = new Map<string, string>(); f = { mem, service: languageService(mem, [abs]) }; fixtureServices.set(abs, f); }
  f.mem.set(abs, src);
  const program = f.service.getProgram(), sf = program.getSourceFile(abs);
  if (!sf || sf.text !== src) throw new Error("the socket proof's program for a row does not hold the row, at " + file);
  return { service: f.service, program, checker: program.getTypeChecker(), sf };
}

// ── the checker's answers for the road census ──
//
// The road census resolves a name through TypeScript's binder, the same checker the socket proof reads, to answer "is
// this name the page's own window", "is it another window" and "what does this name bind to". The window rule (refKind)
// answers both window questions, by its clauses (a), the binder's identity, and (b), the declarations the checker
// resolves a chain's names to; its clause (c) goes by position, not by the binder: thisIsGlobal reads a plain
// function's or the file's own `this`, outside any class, method or object literal's function, as the global object.
// writesName gates the event-name forEach arm by spelling. Callee names are matched by spelling too, not resolved: the
// reflective arms' Reflect and Object methods (through globalName, which takes a leading window., self. or globalThis.
// off by spelling), protoRef's Object.getPrototypeOf and Reflect.getPrototypeOf, the timer arm's setTimeout and
// setInterval on any receiver, eval, Function and require, each read the same whether the name is the global or a local
// of that name. Reading a local of the name as the global errs on the refusing side. Reading only the spelling also
// misses a reflective or prototype arm reached another way than its bare Reflect. or Object. spelling: through frames
// (this page's own window), another window, or a comma expression (frames.Reflect.set(window, k, f), (0,
// Reflect.get)(window, k), frames.Object.getPrototypeOf(window)[k]), or run with the window among its arguments through
// .call, .apply or Reflect.apply (Reflect.set.call(null, window, k, f), Reflect.apply(Reflect.set, null, [window, k,
// f])); each direct spelling is refused. Those err on the accepting side and are disclosed in the "cannot see" list ("a
// reflective or prototype function reached any way but by its Reflect. or Object. spelling", whose examples cover the
// frames, other-window, comma, prototype-read and run-with-the-window-among-its-arguments forms). A resolver holds the
// program the census reads the file in (censusProgram for a ui/ file, fixtureChecked for a test row), maps a node of
// the census's own parse to that program by span, and answers five questions:
//   - windowKind(symbol, name): the name is the page's own window when the symbol the checker resolves the identifier to
//     IS the global table's symbol for that name (checker.resolveName over the program's globals), for window, self,
//     globalThis or frames; another window for top, parent or opener; this page's document for document. Deciding by
//     IDENTITY, not by "every declaration is in the default lib": a window-name global that a JavaScript expando
//     (a top-level window.foo = 1) or a `declare global` adds a declaration to still IS the window, and the literal rule
//     would answer "not the window" and let a computed write through (fail open). So the identity answer stands, and the
//     extra declaration is caught separately (extraDecl), fail closed. The library anchors identity by one lib.dom
//     declaration for window, self, frames, top, parent and opener; globalThis it gives no declaration, so gsym anchors
//     globalThis by its symbol name (escapedName), whatever its declarations. A declaration-count test ("no declaration,
//     and named globalThis") would fail open for globalThis too: a .js expando gives its symbol a declaration and no lib
//     one, dropping globalThis out of the count test and letting a computed write through. Name identity holds it.
//   - extraDecl(symbol): the window-name global carries a declaration outside TypeScript's default lib. A page whose
//     source augments a window global (an expando, a `declare global`) is one the census cannot trust is the browser's
//     own, as with the WebSocket precondition, so refKind records it and looseRoads refuses outright. Live cost 0:
//     window, self, frames, parent, top and opener each have one lib.dom.d.ts declaration and globalThis none, so an
//     augmentation of any of them is the source's and refuses. A JavaScript expando merges into globalThis's symbol too
//     (held by name identity), and refuses; a `declare global { var globalThis }` does not merge (kept apart, no program
//     error), so it adds no declaration to the global and records no augmentation.
//   - declC(node): the declaration the checker resolves an identifier to: null for a global the source does not declare or
//     a name that binds nothing at run time (bindsNothingAtRuntime: its every declaration ambient (`declare`) or in a
//     .d.ts, both of which esbuild drops), else the symbol's first declaration (the library's, where a script's top-level
//     var merged with a library global), a binding element climbed to its variable declaration's root. The listener,
//     event-name, timer and detach-value arms read it (sitesIn's listenerOf, eventTypes and listOf, the timer arm, and
//     setsNoHandler's undefined check); an ambient const in a .ts file resolves to nothing here, so its value is no event
//     name.
//   - initIsValue(symbol): whether the window rule's clause (b) decides the binding by its initialiser, which it does
//     only where that initialiser is the binding's value at every use: the checker gives the name one declaration (a
//     JavaScript expando, which writes a member, aside), a let, const or var declaration's own (plain or destructured)
//     with an initialiser; it is no namespace's export (esbuild reads that as a property of the namespace object, which
//     code can set under any spelling) and no var of a script's top-level scope (a property of the global object, which
//     a call can set under a string key, Reflect.set(window, "x", w), before or after the initialiser runs); and
//     nothing writes it but its initialiser. The writes are found as the socket proof finds them: the language
//     service's findReferences on the declaration lists the references, in every file of the program, and each is read
//     at its identifier, a write where its isWriteAccess says so (the service's reading, which counts some reads as
//     writes too, among them a shorthand property naming the binding, { d }, and an export specifier, export { d }) or
//     writesBinding does (an assignment's target of any operator, ++ or --, a destructuring target, a for...in or
//     for...of head, read through the parentheses and through the casts, satisfies, non-null marks and type arguments
//     esbuild erases, which the service reads as a read: (d as any) = w, d! = w; and a rest element's target), a listed
//     reference that is no identifier of the name, or one inside a JSDoc comment (identAt does not look there), making
//     the binding one the rule does not decide; and a walk over every identifier of the name in the declaring file,
//     each resolved by the checker, must agree (one it resolves to the declaration that the service does not list makes
//     the binding one the rule does not decide). A let or const of a script's top-level scope is shared with every
//     classic script of the page: a write in another ui/ file is found in the census's program, and one in a script the
//     census does not read is outside it. ruleKind asks only where the answer can change the kind: a binding whose
//     initialiser reads as this page's own window or document.
//   - topShadow(node): the symbol the identifier's own file declares its name by at the file's top level, where
//     TypeScript calls the file no module (isExternalModule, the predicate ctorRefusal reads) and a declaration of the
//     name there is not ambient (not bindsNothingAtRuntime; a type-only one counts), read from the binder's table for
//     the file (SourceFile.locals); else null. In such a file the checker merges the declaration with the global or
//     resolves a use past it to the global, while esbuild keeps a run-time one the file's own local in the page bundle,
//     so ruleKind does not decide a use of the name there by identity, and looseRoads refuses the file for each window
//     name or document it declares so. isExternalModule also calls a JavaScript file TypeScript binds as CommonJS (one
//     with require or module.exports, for example) no module: there the checker resolves a use to the file's own local,
//     which ruleKind reads by clause (b), and looseRoads refuses the file all the same.
type Res = {
  checked: () => Checked;
  toProg: (n: any) => any;
  symAt: (n: any) => any;
  windowKind: (s: any, name: string) => RefKind | null;
  extraDecl: (s: any) => boolean;
  firstNonLib: (s: any) => any;
  declC: (n: any) => any;
  initIsValue: (s: any) => boolean;
  topShadow: (n: any) => any;
  augmented: Array<{ name: string; node: any; sym: any }>;
};
/** A resolver over the program `checked` returns, mapping a node of `localSf` (the census's own parse) to it by span. */
function resolver(localSf: any, checked: () => Checked): Res {
  let c: Checked | null = null;
  let index: Map<string, any> | null = null;
  const prog = (): Checked => (c || (c = checked()));
  const idx = (): Map<string, any> => {
    if (!index) {
      index = new Map();
      const walk = (n: any): void => { index!.set(n.kind + ":" + n.pos + ":" + n.end, n); ts.forEachChild(n, walk); };
      walk(prog().sf);
    }
    return index;
  };
  const toProg = (n: any): any => {
    const sf = n.getSourceFile();
    if (sf === prog().sf) return n;   // already a program node
    return idx().get(n.kind + ":" + n.pos + ":" + n.end) || null;
  };
  const symAt = (n: any): any => { const p = toProg(n); return p ? prog().checker.getSymbolAtLocation(p) : null; };
  const gcache = new Map<string, any>();
  const isLib = (d: any): boolean => prog().program.isSourceFileDefaultLibrary(d.getSourceFile());
  // The global table's symbol for `name`, or null. It is the symbol resolveName finds at the global scope, but ONLY the
  // library's own: one with a default-lib declaration (window, self, frames, top, parent, opener, document, each one
  // lib.dom.d.ts declaration, augmented or not), or globalThis, which the library gives no declaration of its own and
  // which is recognised by its symbol name (escapedName "globalThis") whatever its declarations. A MODULE-scoped local
  // of the name (const frames = [] in a module) is a different symbol with no library declaration, so it is not the
  // global; a script's top-level local is not kept apart the same way (a .ts script's use of a top-level const frames
  // resolves to the library global, with a TS2451; in a .js script TypeScript does not bind as CommonJS, a top-level var
  // merges into the library symbol, and a let or const merges into it or yields to it, the use resolving to the library
  // symbol), so identity alone would read the use as the global, which it is not in the page bundle, where esbuild
  // keeps the declaration the file's own local: ruleKind asks topShadow, and a use of the name in such a file is read
  // fail-closed and the file refused (looseRoads). A
  // JavaScript expando MERGES into the library symbol (globalThis's included, which stays globalThis by name), and a `declare
  // global` merges for a name the library declares (self, window) but not for globalThis (kept apart, no program
  // error), so the global stays the global and extraDecl catches the expando augmentation. globalThis by its
  // declaration count would fail open: a .js expando gives its symbol a declaration and no lib declaration, so a count
  // test drops it out and a computed write on it passes; identity by name holds it and refuses the augmentation.
  const gsym = (name: string): any => {
    if (!gcache.has(name)) {
      const s = prog().checker.resolveName(name, undefined, ts.SymbolFlags.Value, false) || null;
      const ds: any[] = s && s.declarations ? s.declarations : [];
      gcache.set(name, s && (ds.some(isLib) || s.escapedName === "globalThis") ? s : null);
    }
    return gcache.get(name);
  };
  const windowKind = (s: any, name: string): RefKind | null => {
    if (!s || s !== gsym(name)) return null;
    return WINDOW_NAMES.has(name) ? "window" : OTHER_WINDOW_NAMES.has(name) ? "otherWindow" : name === "document" ? "document" : null;
  };
  const firstNonLib = (s: any): any => (s && s.declarations ? s.declarations.find((d: any) => !isLib(d)) : undefined) || null;
  const extraDecl = (s: any): boolean => !!firstNonLib(s);
  const declC = (n: any): any => {
    // the declaration the checker binds the identifier to: null when the name has no run-time binding of its own (a
    // global the source does not declare, or a name whose every declaration is ambient or in a .d.ts), else the symbol's
    // first declaration, a binding element climbed to its variable declaration's root. A script's top-level binding,
    // which resolveName finds in the global scope, has a declaration in a source file, so it is not treated as a global;
    // where it merged with a library global (a .js script's top-level var document), the symbol's first declaration is
    // the library's, and that is the one returned.
    const s = symAt(n);
    if (!s) return null;
    const ds = s.declarations || [];
    if (!ds.length || bindsNothingAtRuntime(s)) return null;
    let d = ds[0];
    while (ts.isBindingElement(d) || ts.isObjectBindingPattern(d) || ts.isArrayBindingPattern(d)) d = d.parent;
    return d;
  };
  // whether a var declaration list's scope is the file's own: walking out, the file is reached before any function,
  // static block or namespace body (a var in a block at the file's top level included)
  const varScopeIsFile = (list: any): boolean => {
    for (let s = list.parent; s; s = s.parent) {
      if (ts.isSourceFile(s)) return true;
      if (ts.isFunctionLike(s) || ts.isClassStaticBlockDeclaration(s) || ts.isModuleBlock(s)) return false;
    }
    return false;
  };
  const valueCache = new Map<any, boolean>();
  const initIsValueOf = (s: any): boolean => {
    const ds = (s.declarations || []).filter((x: any) => !isExpandoDecl(x));
    if (ds.length !== 1 || !ds[0].name || !ts.isIdentifier(ds[0].name)) return false;
    const d = ds[0];
    let root: any = d;
    while (ts.isBindingElement(root) || ts.isObjectBindingPattern(root) || ts.isArrayBindingPattern(root)) root = root.parent;
    if (!ts.isVariableDeclaration(root) || !root.initializer || !ts.isVariableDeclarationList(root.parent)) return false;
    const list = root.parent, stmt = list.parent, dsf = d.getSourceFile();
    if (ts.isVariableStatement(stmt) && isNamespaceExport(stmt)) return false;
    if ((list.flags & ts.NodeFlags.BlockScoped) === 0 && !ts.isExternalModule(dsf) && varScopeIsFile(list)) return false;
    const { service, checker, program } = prog();
    const key = (file: string, start: number): string => file + ":" + start;
    const at = d.name.getStart(dsf);
    const listed = new Map<string, any>();
    for (const r of service.findReferences(dsf.fileName, at) || []) for (const e of r.references) listed.set(key(e.fileName, e.textSpan.start), e);
    listed.delete(key(dsf.fileName, at));
    // each listed reference read at its identifier, in whatever file it is: a write by the service's isWriteAccess or
    // by writesBinding (a target under a cast, satisfies, non-null mark or type argument, which the service reads as a
    // read, or a rest element's), or a listed reference that is no identifier of the name, leaves the binding undecided
    for (const e of listed.values()) {
      if (e.isWriteAccess) return false;
      const rsf = program.getSourceFile(e.fileName);
      const id = rsf ? identAt(rsf, e.textSpan.start, d.name.text) : null;
      if (!id || writesBinding(id)) return false;
    }
    let unlisted = false;
    const walk = (n: any): void => {
      if (unlisted) return;
      if (ts.isIdentifier(n) && n.text === d.name.text && n !== d.name) {
        const p = n.parent;
        const r = ts.isShorthandPropertyAssignment(p) && p.name === n ? checker.getShorthandAssignmentValueSymbol(p)
          : ts.isExportSpecifier(p) && (p.propertyName || p.name) === n ? checker.getExportSpecifierLocalTargetSymbol(p)
          : checker.getSymbolAtLocation(n);
        if (r && (r.declarations || []).includes(d) && !listed.has(key(dsf.fileName, n.getStart(dsf)))) unlisted = true;
      }
      ts.forEachChild(n, walk);
    };
    walk(dsf);
    return !unlisted;
  };
  const initIsValue = (s: any): boolean => {
    if (!valueCache.has(s)) valueCache.set(s, initIsValueOf(s));
    return valueCache.get(s) as boolean;
  };
  // the symbol the identifier's own file declares its name by at the file's top level, when TypeScript calls the file
  // no module (isExternalModule, as ctorRefusal reads it) and a declaration of the name there is not ambient (a
  // type-only one counts): read from the binder's table for the file (SourceFile.locals, the table the socket proof
  // reads). Null for a module, whose top-level declaration the checker keeps apart from the global, and for a file that
  // declares no such name at its top level or only ambient ones (bindsNothingAtRuntime). isExternalModule calls a
  // JavaScript file TypeScript binds as CommonJS no module too, so that file's local is returned, though the checker
  // resolves a use to it
  const topShadow = (n: any): any => {
    const p = toProg(n);
    if (!p) return null;
    const sf = p.getSourceFile();
    if (!(sf.locals instanceof Map)) {
      throw new Error("TypeScript " + ts.version + " keeps its binder's table elsewhere than SourceFile.locals, which the window rule reads");
    }
    if (ts.isExternalModule(sf)) return null;
    const own = sf.locals.get(n.text);
    return own && !bindsNothingAtRuntime(own) ? own : null;
  };
  return { checked, toProg, symAt, windowKind, extraDecl, firstNonLib, declC, initIsValue, topShadow, augmented: [] };
}

// ── the socket proof ──
/** Whether every declaration of the symbol `s` is a library global: in a TypeScript default lib file
 *  (program.isSourceFileDefaultLibrary, lib.dom.d.ts's) or under node_modules/@types
 *  (program.isSourceFileFromExternalLibrary with an @types path, @types/node's). A project declaration, in ui/ or
 *  elsewhere in the repo, is neither, so the symbol refuses: the proof trusts only the library's own declaration of the
 *  constructor and of the object new X.WebSocket(...) reads. */
function libOrAtTypes(s: any, program: any): boolean {
  if (!s || !s.declarations || s.declarations.length === 0) return false;
  return s.declarations.every((d: any) => {
    const sf = d.getSourceFile();
    if (program.isSourceFileDefaultLibrary(sf)) return true;
    return program.isSourceFileFromExternalLibrary(sf) && /[\\/]node_modules[\\/]@types[\\/]/.test(sf.fileName);
  });
}
/** Why `v` is not a new of the built-in WebSocket (socketRefusal's clause 4), naming the site; null when it is. The
 *  constructor, and in new X.WebSocket(...) the object X, must resolve to a global every declaration of which is in a
 *  TypeScript default lib or under node_modules/@types (libOrAtTypes): a project .d.ts declaration, in ui/ or elsewhere,
 *  refuses. */
function ctorRefusal(v: any, c: Checked, at: (n: any) => string): string | null {
  v = unwrap(v);
  const callee = ts.isNewExpression(v) ? unwrap(v.expression) : null;
  const member = callee && ts.isPropertyAccessExpression(callee) && callee.name.text === "WebSocket" && ts.isIdentifier(callee.expression);
  if (!callee || !(member || (ts.isIdentifier(callee) && callee.text === "WebSocket"))) return "something other than new WebSocket(...)";
  // in a file that is no module, a top-level declaration of a name read here is a global the checker merges with the
  // built-in's declarations, or, where it cannot (a class, a let, a function beside the built-in var), sets apart and
  // resolves past
  const names = member ? [callee.expression, callee.name] : [callee];
  const top = names.find((n: any) => !ts.isExternalModule(c.sf) && c.sf.locals.has(n.text));
  if (top) return "new WebSocket(...) in a file that is no module and declares " + top.text + " at its top level, which the checker can resolve past to the built-in";
  const builtIn = (s: any): boolean => libOrAtTypes(s, c.program) && s.escapedName === "WebSocket";
  if (member && !libOrAtTypes(c.checker.getSymbolAtLocation(callee.expression), c.program)) return "new " + callee.expression.text + ".WebSocket(...) whose " + callee.expression.text + " at " + at(callee.expression) + " has a declaration outside the default lib and @types";
  const ctor = member ? callee.name : callee;
  if (!builtIn(c.checker.getSymbolAtLocation(ctor))) return "new WebSocket(...) whose WebSocket at " + at(ctor) + " the checker resolves to no library global (its declarations outside the default lib and @types)";
  return null;
}
/** Why the road census cannot prove `recv` (a node of `sfRead`, the census's parse of the file) a WebSocket, whose own
 *  onmessage handler only its server posts to, naming the site; null when it can. The proof reads TypeScript's binder,
 *  through the checker of the program `checked` returns, and fails closed: whatever the checker cannot answer refuses.
 *  Its precondition, stated here once and not checked: the page's global WebSocket (window.WebSocket, self.WebSocket)
 *  is the browser's own constructor; a page that replaces it is outside the proof. The road census refuses the name
 *  WebSocket in every file but as the constructor a new calls or in a type, and lists the copied-object road, which it
 *  cannot see and which can replace it. The clauses:
 *  0. The checker's scopes are the page's: the file has no syntax error, and no error from TypeScript's binder, which
 *     sets a duplicate declaration apart as a symbol of its own and reports sloppy-only code as strict code's errors (a
 *     with statement, a labelled function, delete of a name, eval or arguments declared or assigned, a word strict code
 *     reserves used as a name), and a label on any declaration statement too, though strict code allows one on a var
 *     statement; this clause refuses every one. And in any file, no function declaration of ANY name is declared in a
 *     block, that is anywhere but directly in a file, a module body or a function's body (so an if statement's clause, a
 *     case clause and a nested block are all refused). Refused by position, without casing on the kind: a sloppy-mode file
 *     hoists a PLAIN block function into its enclosing function (Annex B), past the checker's block scope; an async,
 *     generator or async-generator one Annex B never hoists, so it diverges from the checker in no file, but it is refused
 *     all the same. The proof does not decide which files the page runs as sloppy code, since a file TypeScript calls a
 *     module can be one (esbuild bundles a script, and the kernel inlines one, as sloppy code unless it opens with "use
 *     strict", and esbuild bundles as sloppy CommonJS a .cjs or .cts file with no import or export statement and a
 *     TypeScript file whose only module syntax is import x = require(...) or export =, each a module to TypeScript), so it
 *     refuses this in every file. An if statement's clause directly in a function body is a case where the checker binds
 *     the plain function in that function, as sloppy code does, so the two agree there; the guard refuses it all the same,
 *     by position, without casing on whether the bindings diverge.
 *  1. The checker's symbol for `recv` has exactly one declaration: a let, const or var statement's own, with a plain
 *     name (no loop head's, for head's or catch clause's, no parameter, no destructuring pattern), in this file,
 *     neither ambient (isAmbient) nor a namespace's export (isNamespaceExport), neither of which is a run-time binding
 *     of its own. A JavaScript file's property assignment on the name (ws.x = v), which TypeScript records as a
 *     declaration of the name's symbol, binds a member and is not counted.
 *  2. It is bound to a WebSocket in one of two shapes:
 *     A. an initialiser that is new WebSocket(...), and no other write; or
 *     B. no initialiser, and exactly one write, `name = new WebSocket(...);`, the assignment a statement of its own, in
 *        the try block of a try statement that follows the declaration in the declaration's own statement list, whose
 *        catch block ends in a return and holds no break, continue or label, and which has no finally block; with every
 *        read of the name after that try statement, inside the declaration's statement list, and no function
 *        declaration (hoisted, so callable before the try) between the read and that list. federation.ts's connect() is
 *        this shape: a throwing constructor schedules a retry and returns.
 *     A write in any other shape refuses, and so does a second write anywhere and, in shape B, a read that can run
 *     before the write. In shape A no read sees another value before the declaration runs: a let or const is in its
 *     temporal dead zone and a var is undefined, and setting a handler on either throws.
 *  3. Every write is found through the checker: the language service's findReferences on the declaration lists every
 *     reference to its symbol, in closures and nested functions too, and a reference writes where its isWriteAccess
 *     says so (the service's reading, which counts some reads as writes too, among them a shorthand property naming
 *     the socket, go({ ws }), and an export specifier, export { ws }, each refused as a write) or writesBinding does
 *     (an assignment of any operator, logical ones included, ++ or --, a destructuring target or a default in one, a
 *     for...in or for...of head; writesBinding reads the target through the parentheses and through the casts,
 *     satisfies, non-null marks and type arguments esbuild erases, which the service reads as a read, (ws as any) = w
 *     and ws! = w, and counts a rest element's). A walk over every identifier of the name in the file, each resolved by
 *     the checker, must agree: one it resolves to the declaration's symbol that the language service does not list, a
 *     listed reference that is no identifier of the name (a rename, a string key) or that sits inside a JSDoc comment
 *     (a {@link ws}, which the walk does not enter), one in another file, and one the checker resolves to no symbol
 *     (outside a member or key name, a label or a type, namesNoBinding) each refuse.
 *  4. The WebSocket that new calls is the library's own: the checker resolves `WebSocket` (in new window.WebSocket(...),
 *     the object and then its member) to a global symbol every declaration of which is in a TypeScript default lib
 *     (program.isSourceFileDefaultLibrary, lib.dom.d.ts's) or under node_modules/@types
 *     (program.isSourceFileFromExternalLibrary with an @types path, @types/node's), libOrAtTypes. A project .d.ts
 *     declaration, in ui/ or elsewhere in the repo, refuses. In a file that is no module, a top-level declaration of a
 *     name it reads refuses too: a global the checker could not merge with the library's it sets apart and resolves past. */
function socketRefusal(recv: any, sfRead: any, checked: () => Checked): string | null {
  recv = unwrap(recv);
  if (!ts.isIdentifier(recv)) return "the receiver is not a name";
  const c = checked(), { service, program, checker, sf } = c;
  const name = recv.text;
  const line = (pos: number): string => ":" + (sf.getLineAndCharacterOfPosition(pos).line + 1);
  const at = (n: any): string => {
    const f = n.getSourceFile();
    return (f === sf ? "" : path.relative(UI, f.fileName)) + ":" + (f.getLineAndCharacterOfPosition(n.getStart(f)).line + 1);
  };
  const named: any[] = [];   // every identifier of the name in the file
  const collect = (n: any): void => { if (ts.isIdentifier(n) && n.text === name) named.push(n); ts.forEachChild(n, collect); };
  collect(sf);
  const id = named.find((n) => n.getStart(sf) === recv.getStart(sfRead) && n.end === recv.end);
  if (!id) throw new Error("the socket proof's program holds no " + name + " where the census read the receiver, in " + sf.fileName);
  if (!Array.isArray(sf.bindDiagnostics) || !(sf.locals instanceof Map)) {
    throw new Error("TypeScript " + ts.version + " keeps its binder's diagnostics and table elsewhere than SourceFile.bindDiagnostics and .locals, which the socket proof reads");
  }
  // 0. the checker's scopes are the page's
  const parse = program.getSyntacticDiagnostics(sf).find((d: any) => d.category === ts.DiagnosticCategory.Error);
  if (parse) return "the file does not parse as TypeScript reads it (" + ts.flattenDiagnosticMessageText(parse.messageText, " ") + ", at " + line(parse.start) + ")";
  const bound = sf.bindDiagnostics.find((d: any) => d.category === ts.DiagnosticCategory.Error);
  if (bound) return "TypeScript's binder reports an error at " + line(bound.start) + " (" + ts.flattenDiagnosticMessageText(bound.messageText, " ") + "), where its scopes are not the page's";
  let blockFn: any = null;
  const blockFns = (n: any): void => {
    if (blockFn) return;
    // any function declaration, of any name and kind, that is not at a file's top level, in a module body, or directly in a
    // function body (so an if statement's clause, a case clause, a nested block): refused by its position. A sloppy-mode
    // file hoists a PLAIN block function into its enclosing function (Annex B) past the checker's block scope; an async,
    // generator or async-generator one Annex B never hoists, so it diverges in no file, but it is refused all the same, and
    // the proof does not decide which files the page runs as sloppy code, so this is refused in every file.
    if (ts.isFunctionDeclaration(n) && n.name
        && !(ts.isSourceFile(n.parent) || ts.isModuleBlock(n.parent) || (ts.isBlock(n.parent) && ts.isFunctionLike(n.parent.parent)))) blockFn = n;
    else ts.forEachChild(n, blockFns);
  };
  blockFns(sf);   // in every file: the proof does not decide which files the page runs as sloppy code
  if (blockFn) return "a function " + blockFn.name.text + " is declared in a block at " + at(blockFn) + ", not at a file's top level, in a module body or directly in a function body, where the proof refuses it in every file (a plain one a sloppy-mode file hoists into its enclosing function past the checker's block scope; an async or generator one by its position alone, Annex B not hoisting it)";
  // 1. one declaration, a let, const or var statement's own
  const sym = checker.getSymbolAtLocation(id);
  if (!sym) return name + " at " + at(id) + " resolves to no symbol";
  const decls = (sym.declarations || []).filter((x: any) => !(ts.isIdentifier(x) && (ts.isPropertyAccessExpression(x.parent) || ts.isElementAccessExpression(x.parent)) && x.parent.expression === x));
  if (decls.length === 0) return name + " at " + at(id) + " resolves to no declaration";
  if (decls.length > 1) return name + " has " + decls.length + " declarations (" + decls.map(at).join(", ") + "), and the proof takes one";
  const d = decls[0];
  if (!ts.isVariableDeclaration(d) || !ts.isIdentifier(d.name) || !ts.isVariableDeclarationList(d.parent) || !ts.isVariableStatement(d.parent.parent) || d.getSourceFile() !== sf) {
    return name + " is not declared by a let, const or var statement of its own (" + at(d) + ")";
  }
  const stmt = d.parent.parent, list = stmt.parent;
  if (isAmbient(stmt) || (d.flags & ts.NodeFlags.Ambient) !== 0) return name + " is declared at " + at(d) + " by an ambient declaration (declare), which binds nothing at run time";
  if (isNamespaceExport(stmt)) return name + " is declared at " + at(d) + " as a namespace's export, which is a property of the namespace object";
  // 3. every reference, listed by the language service and resolved by the checker
  const listed = new Map<number, any>();
  for (const s of service.findReferences(sf.fileName, d.name.getStart(sf)) || []) {
    for (const e of s.references) {
      if (e.fileName !== sf.fileName) return name + " has a reference in another file (" + path.relative(UI, e.fileName) + ")";
      listed.set(e.textSpan.start, e);
    }
  }
  listed.delete(d.name.getStart(sf));
  const writes: any[] = [], reads: any[] = [];
  for (const n of named) {
    if (n === d.name) continue;
    const p = n.parent;
    const s = ts.isShorthandPropertyAssignment(p) && p.name === n ? checker.getShorthandAssignmentValueSymbol(p)
      : ts.isExportSpecifier(p) && (p.propertyName || p.name) === n ? checker.getExportSpecifierLocalTargetSymbol(p)
      : checker.getSymbolAtLocation(n);
    if (!s) {
      if (namesNoBinding(n)) continue;
      return name + " at " + at(n) + " resolves to no symbol, which the proof cannot tell from its declaration's";
    }
    if (!(s.declarations || []).includes(d)) continue;
    const e = listed.get(n.getStart(sf));
    if (!e) return name + " at " + at(n) + " is its declaration's symbol to the checker and no reference to the language service";
    listed.delete(n.getStart(sf));
    if (inTypeNode(n)) continue;   // a name in a type, which runs nothing
    // a write by the service's isWriteAccess or by writesBinding, which reads a target under a cast, satisfies,
    // non-null mark or type argument ((ws as any) = w, ws! = w), and a rest element's, as the write esbuild leaves it
    (e.isWriteAccess || writesBinding(n) ? writes : reads).push(n);
  }
  const stray = [...listed.keys()][0];
  if (stray !== undefined) return name + " has a reference at " + line(stray) + " that is no identifier " + name + " (a rename, a string key, or a reference inside a JSDoc comment), which the proof does not read";
  // 2 and 4. bound to the built-in WebSocket, in shape A or shape B
  if (d.initializer) {
    const why = ctorRefusal(d.initializer, c, at);
    if (why !== null) return name + " is declared at " + at(d) + " bound to " + why;
    if (writes.length) return name + " is written at " + at(writes[0]) + ", and its declaration at " + at(d) + " binds it already";
    return null;
  }
  if (writes.length === 0) return name + " is never bound to new WebSocket(...)";
  if (writes.length > 1) return name + " is written at " + writes.map(at).join(", ") + ", and a declaration with no initialiser takes one write";
  const w = writes[0], asg = w.parent, own = asg.parent;
  if (!(ts.isBinaryExpression(asg) && asg.left === w && asg.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isExpressionStatement(own) && own.expression === asg)) {
    return name + " is written at " + at(w) + " by something other than a statement of its own assigning new WebSocket(...)";
  }
  const why = ctorRefusal(asg.right, c, at);
  if (why !== null) return name + " is written at " + at(w) + " with " + why;
  const tryStmt = own.parent.parent;
  const catchBody = ts.isBlock(own.parent) && ts.isTryStatement(tryStmt) && tryStmt.tryBlock === own.parent && tryStmt.catchClause ? tryStmt.catchClause.block.statements : [];
  let leaves = false;
  const jumps = (n: any): void => {
    if (leaves || ts.isFunctionLike(n) || ts.isClassLike(n)) return;
    if (ts.isBreakStatement(n) || ts.isContinueStatement(n) || ts.isLabeledStatement(n)) leaves = true; else ts.forEachChild(n, jumps);
  };
  catchBody.forEach(jumps);
  if (!catchBody.length || !ts.isReturnStatement(catchBody[catchBody.length - 1]) || leaves || tryStmt.finallyBlock || tryStmt.parent !== list
      || list.statements.indexOf(tryStmt) < list.statements.indexOf(stmt)) {
    return name + " is written at " + at(w) + " elsewhere than in the try block of a try beside its declaration and after it, whose catch ends in a return and which has no finally";
  }
  for (const r of reads) {
    let early = r.getStart(sf) < tryStmt.end || !holds(list, r);
    for (let s = r.parent; !early && s !== list; s = s.parent) if (ts.isFunctionDeclaration(s)) early = true;
    if (early) return name + " is read at " + at(r) + ", which can run before its one write at " + at(w);
  }
  return null;
}
/** Whether `n` is the constructor a `new` calls, bare (new WebSocket(u)) or as a member (new window.WebSocket(u)). */
const isNewCallee = (n: any): boolean => {
  const o = outer(n);
  if (ts.isNewExpression(o.parent) && o.parent.expression === o) return true;
  if (!ts.isPropertyAccessExpression(n.parent) || n.parent.name !== n) return false;
  const m = outer(n.parent);
  return ts.isNewExpression(m.parent) && m.parent.expression === m;
};
/** Whether a module specifier names a test or types file: UI_CLASSES' tests and types class takes it as written, with a
 *  suffix esbuild adds (RESOLVE_ORDER: ./x.d finds x.d.ts), or with the .ts esbuild tries for a .js, .mjs or .cjs one
 *  (./x.test.js finds x.test.ts). */
function namesTestOrTypes(spec: string): boolean {
  const testsAndTypes = UI_CLASSES.find(([k]) => k === "tests and types")![1];
  return [spec, spec.replace(/\.([mc]?)js$/, ".$1ts"), ...RESOLVE_ORDER.map((x) => spec + x)].some((c) => testsAndTypes.test(c));
}
/** The timers that run a string handed to them as code. */
const TIMERS = new Set(["setTimeout", "setInterval"]);
/** The name a timer's callee ends in, read on any receiver: after parentheses and a comma expression's last operand
 *  ((0, setTimeout)), a name, or a member of that name (w.setTimeout, document.defaultView["setTimeout"]); else "". */
function timerName(c: any): string {
  c = unwrap(c);
  while (ts.isBinaryExpression(c) && c.operatorToken.kind === ts.SyntaxKind.CommaToken) c = unwrap(c.right);
  if (ts.isIdentifier(c)) return c.text;
  if (ts.isPropertyAccessExpression(c)) return c.name.text;
  if (ts.isElementAccessExpression(c) && ts.isStringLiteralLike(unwrap(c.argumentExpression))) return unwrap(c.argumentExpression).text;
  return "";
}
/** Every road in `src` the comment above lists, with where it is and why, and how many onmessage and onmessageerror
 *  names it read. `checked` gives the program the socket proof reads the file in: the census's (censusProgram) for a
 *  ui/ file, a row's own (fixtureChecked) by default, built only when the proof runs. */
function looseRoads(file: string, src: string, checked: () => Checked = () => fixtureChecked(file, src)): { onmessage: number; loose: LooseAdd[] } {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kindOfUi(file));
  const res = resolver(sf, checked);
  const loose: LooseAdd[] = [];
  let onmessage = 0;
  const refuse = (n: any, why: string): void => {
    loose.push({ file, line: sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1, why,
                 text: src.slice(Math.max(0, n.getStart(sf) - 30), Math.min(src.length, n.getEnd() + 40)).replace(/\s+/g, " ") });
  };
  const inType = (n: any): boolean => { for (let s = n.parent; s; s = s.parent) { if (ts.isTypeNode(s) || ts.isHeritageClause(s) && ts.isInterfaceDeclaration(s.parent)) return true; if (ts.isStatement(s) || ts.isExpression(s) && !ts.isIdentifier(s)) return false; } return false; };
  const handlerToken = (tok: any): void => {
    const p = tok.parent;
    if ((ts.isPropertySignature(p) || ts.isMethodSignature(p)) && p.name === tok) return;   // a member of a type
    if (ts.isStringLiteralLike(tok) && ts.isBinaryExpression(p) && p.operatorToken.kind === ts.SyntaxKind.InKeyword && p.left === tok) return;
    let acc: any = null;
    if (ts.isPropertyAccessExpression(p) && p.name === tok) acc = p;
    else if (ts.isElementAccessExpression(p) && p.argumentExpression === tok) acc = p;
    else if (ts.isIdentifier(tok) && !ts.isPropertyAccessExpression(p)) acc = tok;   // the bare global
    if (acc) {
      const m = outer(acc), q = m.parent;
      if (ts.isBinaryExpression(q) && q.operatorToken.kind === ts.SyntaxKind.EqualsToken && q.left === m) {   // x.onmessage = v
        if (acc === tok || ownWindowRef(acc.expression, res)) return;   // the bare global, or this page's own window: a census site
        if (otherWindowRef(acc.expression, res)) return refuse(tok, "an " + tok.text + " handler on a window other than this page's own, which no check at its head can be about");
        if (setsNoHandler(q.right, res)) return;                    // null or undefined: it sets no handler
        const why = socketRefusal(acc.expression, sf, checked);
        if (why === null) return;                                   // a WebSocket's own handler
        return refuse(tok, "an " + tok.text + " handler on a receiver the census cannot resolve to this page's window or to a socket: " + why);
      }
      if (onlyTested(acc)) return;
    }
    refuse(tok, "an " + tok.text + " handler set some way other than an assignment the census reads");
  };
  const visit = (n: any): void => {
    if ((ts.isIdentifier(n) || ts.isStringLiteralLike(n)) && MESSAGE_HANDLERS.has(n.text)) { onmessage++; handlerToken(n); }
    if (ts.isCallExpression(n) && n.arguments.length >= 1 && ts.isStringLiteralLike(n.arguments[0]) && MESSAGE_EVENTS.has(n.arguments[0].text)) {
      const c = unwrap(n.expression);
      if (memberName(c) === "addEventListener" && otherWindowRef(c.expression, res)) {
        refuse(n, "a " + n.arguments[0].text + " listener added to a window other than this page's own, which no check at its head can be about");
      }
    }
    if (ts.isWithStatement(n)) refuse(n, "a with statement, which answers the names inside it from an object the census cannot read");
    if (ts.isTaggedTemplateExpression(n) && TIMERS.has(timerName(n.tag))) {
      refuse(n, timerName(n.tag) + " as a template's tag, which hands it the template's strings as an array it turns into a string and runs as code");
    }
    if ((ts.isIdentifier(n) || ts.isStringLiteralLike(n)) && n.text === "WebSocket" && !inType(n) && !isNewCallee(n)) {
      refuse(n, "the name WebSocket other than as the constructor a new calls, which could replace the socket the census accepts");
    }
    if (ts.isElementAccessExpression(n) && !isLiteralKey(n.argumentExpression) && holdsWindowMethods(n.expression, res)) {
      refuse(n, "a member of a window, a document the census cannot tell is this page's, the body element or a prototype reached by a computed name, which the censuses cannot read");
    }
    if ((ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isBindingElement(n)) && n.initializer && ts.isObjectBindingPattern(n.name)
        && holdsWindowMethods(n.initializer, res) && computedKeyIn(n.name)) {
      refuse(n, "a member of a window, a document the census cannot tell is this page's, the body element or a prototype destructured by a computed key, which the censuses cannot read");
    }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isObjectLiteralExpression(unwrap(n.left))
        && holdsWindowMethods(n.right, res) && computedKeyIn(unwrap(n.left))) {
      refuse(n, "a member of a window, a document the census cannot tell is this page's, the body element or a prototype destructured by a computed key, which the censuses cannot read");
    }
    // a module whose code no census reads: an import() of a URL built at run time, a data: URL's text, a test or types file,
    // a file a specifier esbuild rewrites names, and every file a require() of a computed specifier can reach
    const spec = ts.isImportDeclaration(n) || ts.isExportDeclaration(n) ? (n.moduleSpecifier ? unwrap(n.moduleSpecifier) : null)
      : ts.isExternalModuleReference(n) ? unwrap(n.expression)
      : ts.isCallExpression(n) && (n.expression.kind === ts.SyntaxKind.ImportKeyword || calleeName(n.expression) === "require") && n.arguments[0] ? unwrap(n.arguments[0])
      : null;
    if (ts.isCallExpression(n) && n.expression.kind === ts.SyntaxKind.ImportKeyword && !(spec && ts.isStringLiteralLike(spec))) {
      refuse(n, "an import() whose specifier is not a string literal, which can run code from a string as a module");
    }
    const typeOnly = (ts.isImportDeclaration(n) && !!n.importClause && n.importClause.isTypeOnly) || (ts.isExportDeclaration(n) && n.isTypeOnly);
    // esbuild strips a query or a hash off a specifier, and normalizes a trailing / or /., before it resolves it, so the
    // census cannot tell what such a specifier names (./zz.test.ts?v=1 bundles a test file): refused whatever it names
    if (spec && ts.isStringLiteralLike(spec) && /[?#]|(^|\/)\.?$/.test(spec.text)) {
      refuse(spec, "a module specifier holding a ? or a #, or ending in / or /., which esbuild strips or normalizes before it resolves, so the census cannot tell what it names");
    }
    if (ts.isCallExpression(n) && calleeName(n.expression) === "require" && n.arguments[0] && !ts.isStringLiteralLike(unwrap(n.arguments[0]))) {
      refuse(n, "a require() whose specifier is not a string literal, which esbuild bundles as every file its pattern can match, test and types files among them");
    }
    if (spec && ts.isStringLiteralLike(spec) && !typeOnly) {
      if (/^\s*data:/i.test(spec.text)) refuse(spec, "a module specifier that is a data: URL, whose text esbuild bundles as code no census reads");
      else if (namesTestOrTypes(spec.text)) refuse(spec, "a module specifier naming a test or types file, which esbuild bundles like any module and no census reads");
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
      const timer = timerName(n.expression);
      if (TIMERS.has(timer) && args[0]) {
        const a = unwrap(args[0]);
        // a timer turns what it is handed into a string when it is no function, so an array or object literal runs as code
        const stringy = (x: any): boolean => ts.isStringLiteralLike(x) || ts.isTemplateExpression(x) || ts.isBinaryExpression(x) && x.operatorToken.kind === ts.SyntaxKind.PlusToken
          || ts.isArrayLiteralExpression(x) || ts.isObjectLiteralExpression(x);
        const strings = stringy(a) || ts.isIdentifier(a) && (() => { const d = res.declC(a); return !!d && ts.isVariableDeclaration(d) && !!d.initializer && stringy(unwrap(d.initializer)); })();
        if (strings) refuse(n, timer + " handed a string, or an array or object literal it turns into one, which it runs as code");
      }
      if (args[0] && holdsWindowMethods(args[0], res)) {
        if (REFLECT_READ.has(base) && !isLiteralKey(args[1])) refuse(n, base + " of a window, a document the census cannot tell is this page's, the body element or a prototype with a computed key, which the censuses cannot read");
        if (REFLECT_READ_ALL.has(base)) refuse(n, base + " of a window, a document the census cannot tell is this page's, the body element or a prototype, which hands on every member under its name");
        if (REFLECT_KEYED.has(base) && !isLiteralKey(args[1])) refuse(n, base + " onto a window, a document the census cannot tell is this page's, the body element or a prototype with a computed key, which the censuses cannot read");
        if (REFLECT_SPREAD.has(base)) {
          for (const a of args.slice(1)) {
            const o = unwrap(a);
            if (ts.isObjectLiteralExpression(o) && o.properties.some((pr: any) => ts.isSpreadAssignment(pr) || pr.name && ts.isComputedPropertyName(pr.name) && !isLiteralKey(pr.name.expression))) {
              refuse(n, base + " onto a window, a document the census cannot tell is this page's, the body element or a prototype from an object with a computed key or a spread, which the censuses cannot read");
            }
          }
        }
        if (REFLECT_PROTO.has(base)) refuse(n, base + " on a window, a document the census cannot tell is this page's, the body element or a prototype, which replaces what its methods are");
      }
      const c = unwrap(n.expression), run = memberName(c);
      if (ts.isCallExpression(n) && run !== null && RUN_ON.has(run)) {
        // f.call(window, ...), f.apply(window, [...]), f.bind(window); and f.call.call(g, window, ...), which runs g on it
        const onCall = RUN_ON.has(memberName(unwrap(c.expression)) || "");
        if ((args[0] && windowRef(args[0], res, 0, true)) || (onCall && args[1] && windowRef(args[1], res, 0, true))) {
          refuse(n, "a function run with the window as its this (." + run + "), which the censuses cannot read");
        }
      }
      if (base === "Reflect.apply" && args[1] && windowRef(args[1], res, 0, true)) refuse(n, "Reflect.apply with the window as its this, which the censuses cannot read");
      if ((run === "__defineSetter__" || run === "__defineGetter__") && holdsWindowMethods(c.expression, res) && !isLiteralKey(args[0])) {
        refuse(n, run + " on a window, a document the census cannot tell is this page's, the body element or a prototype with a computed key, which the censuses cannot read");
      }
    }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      const l = unwrap(n.left);
      if (memberName(l) === "__proto__" && windowRef(l.expression, res)) refuse(n, "a new prototype for the window, which replaces what its methods are");
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  // a window-name global the source augmented with a declaration outside the default lib (an expando, a `declare global`),
  // recorded by refKind as it resolved a use of the name: the census cannot trust it is the browser's own window, so it
  // refuses outright (0 live). One refusal per name, naming the augmenting declaration's site.
  const seenAug = new Set<string>();
  for (const a of res.augmented) {
    if (seenAug.has(a.name)) continue;
    seenAug.add(a.name);
    const bad = res.firstNonLib(a.sym);
    const where = bad ? (bad.getSourceFile() === res.checked().sf ? "" : path.relative(UI, bad.getSourceFile().fileName))
      + ":" + (bad.getSourceFile().getLineAndCharacterOfPosition(bad.getStart(bad.getSourceFile())).line + 1) : "?";
    refuse(a.node, "the window name " + a.name + " has a declaration the source added outside TypeScript's default lib (at " + where
      + "), so the census cannot tell its global is the page's own window");
  }
  // a file TypeScript calls no module that declares a window name or document at its top level, with a declaration that
  // is not ambient (topShadow, rule (a)): in the page bundle a use of the name in the file holds the file's own local
  // where esbuild keeps the declaration, and the raw global where it drops it as dead code, and the census reads
  // neither, so it refuses outright (0 live). One refusal per name, at its first declaration. The test also takes a
  // file whose only declaration of the name is type-only and a JavaScript file TypeScript binds as CommonJS, where that
  // reason does not arise (the refused list in the road census comment)
  const named = new Map<string, any>();
  const nameIn = (n: any): void => {
    if (ts.isIdentifier(n) && (WINDOW_GLOBALS.has(n.text) || n.text === "document") && !named.has(n.text)) named.set(n.text, n);
    ts.forEachChild(n, nameIn);
  };
  nameIn(sf);
  for (const [name, n] of named) {
    const own = res.topShadow(n);
    if (!own) continue;
    const ds: any[] = own.declarations || [];
    const d = ds.find((x: any) => !isExpandoDecl(x)) || ds[0];
    refuse(d, "a file that is no module declares " + name + " at its top level (at :" + (d.getSourceFile().getLineAndCharacterOfPosition(d.getStart(d.getSourceFile())).line + 1)
      + "), which the checker merges with the global or resolves past to it, while the page bundle keeps it the file's own local or, dropped as dead code, leaves the raw global, so the census cannot tell what the name holds");
  }
  return { onmessage, loose };
}

test("census: no ui/ source reaches a window listener by a computed name, runs a function with the window as its this, sets an onmessage handler other than by an assignment the census accepts, adds a message listener to another window, runs code from a string, imports a test or types file, names a module by a specifier esbuild rewrites, requires a computed specifier, holds a with statement, names WebSocket but to construct one, augments a window-name global, or declares a window name or document at a script's top level", () => {
  const bad: string[] = [];
  const readIn = new Map<string, number>();
  // the socket proof's program, over every file read here and ui/'s declaration files; it throws on an error in any
  const read = uiSources().concat(uiDeclarationFiles()).map((f) => [f, fs.readFileSync(path.join(UI, f), "utf8")] as [string, string]);
  const checkedIn = censusProgram(read);
  for (const [f, src] of read.slice(0, uiSources().length)) {
    const { onmessage, loose } = looseRoads(f, src, () => checkedIn(f));
    readIn.set(f, onmessage);
    for (const l of loose) bad.push(l.file + ":" + l.line + ": " + l.why + ": " + l.text);
  }
  assert.ok((readIn.get("webview/federation.ts") || 0) >= 2, "the census read federation.ts, whose sockets' onmessage handlers are assignments it accepts");
  assert.deepEqual(bad, [], "a road to a window listener the censuses cannot read: spell the registration so they can\n" + bad.join("\n"));
});

test("the road census reads what it claims: every road around the spelled registration is refused, each road the byReason table keys by a reason for that reason, and a WebSocket's own handler, a handler cleared with null, a handler on this page's own window, a literal member and code that is no road are accepted, and so are the roads its list of what it cannot see names, witnesses of that list", () => {
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
    // a callee or member named through a literal key under parentheses or a cast: memberName reads the key through keyName
    // (which unwraps), so calleeName (built on memberName) spells the reflective and prototype arm, the run-with-this arm
    // reads memberName directly, and the other-window addEventListener and the __proto__/__defineSetter__ writes read the
    // member name, each refused as it is written plain (the timer arm has its own key-unwrap, timerName, not memberName).
    // Every one is accepted when memberName reads only a bare string-literal key (its form before this reading), so these
    // rows pin that memberName unwraps a paren or cast key, across the arms that share it
    ["Reflect[(\"set\")](window, k, f);"],
    ["Object[(\"defineProperty\")](window, k, { value: f });"],
    ["(Reflect as any)[\"set\" as string](window, k, f);"],
    ["const w = window; g[(\"call\")](w, \"message\", f);"],
    ["Reflect[(\"apply\")](document[k], window, [\"message\", f]);"],
    ["Reflect.set(HTMLBodyElement[(\"prototype\")], k, f, document.body);"],
    ["Object[(\"assign\")](window, { [k]: f });"],
    ["Object[(\"getOwnPropertyDescriptors\")](window);"],
    ["Object[(\"setPrototypeOf\")](window, {});"],
    ["window[(\"Reflect\")].set(window, k, f);"],
    ["(window as any)[(\"__proto__\")] = {};"],
    ["(window as any)[(\"__defineSetter__\")](k, f);"],
    ["parent[(\"addEventListener\")](\"message\", f);"],
  ];
  for (const [src, file] of refused) assert.ok(roads(src, file).length >= 1, "refused: " + src);
  const accepted: Array<[string, string?]> = [
    ["const ws = new WebSocket(u); ws.onmessage = (ev: MessageEvent) => { go(ev.data); }; const dead = c.ws; dead.onopen = dead.onmessage = dead.onclose = null;"],
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
    // parent, a class's own this, a wrapper passing its own this on (ui/webview/md-block-start.ts), a call on another object.
    // The frames row is a module (export {}), so its const frames is module-scoped, a symbol of its own the checker does not
    // resolve to the global frames
    ["function h(n: object, k: string) { return Object.getOwnPropertyDescriptor(n, k); } const d = Reflect.get(obj, k);"],
    ["export {}; function p(parent: any, top: any[], k: number) { return [parent[k], top[k]]; } const frames: number[] = []; frames[k] = 1;"],
    ["const o = { defaultView: 1 }; const { [k]: v } = obj; ({ [k]: v } = other);"],
    // a literal key in brackets or under a cast on a receiver that is no window: read as the key, and so no window
    ["const { [\"self\"]: a } = obj; a[k] = 1; const b = (obj as any)[(\"self\")]; b[k] = 1; const { 0: c } = list; c[k] = 1;"],
    ["const wrapped = function (this: object, ...a: unknown[]) { return orig.apply(this, a); };"],
    ["Object.prototype.hasOwnProperty.call(n, \"_nid\"); Array.prototype.forEach.call(nodes, g); g.bind(obj); frames[0].focus();"],
    // a module named by a string literal that is no data: URL and no test or types file and holds no ? or # and ends in
    // no / or /., a type-only import (erased), a .d.tsx (a module the censuses read), and a data: URL that is no module
    // specifier
    ["import { a } from \"./x\"; export { b } from \"../y\"; import(\"./lazy\"); import x = require(\"./z\"); const img = \"data:image/png;base64,AAAA\";"],
    ["import type { T } from \"./vendor-track-changents.d\"; export type { U } from \"./zz.d\"; import \"./zz.d.tsx\";"],
    ["const g = require(\"./gear.js\"); const h = require(\"./gesture-clock.js\");", "webview/probe.js"],
    // a require() esbuild does not read as a pattern (window.require, an alias), a specifier with no query, hash or
    // trailing slash, and a timer handed a function, a name bound to none of the strings the arm reads, or a number
    ["window.require(\"./d/\" + x); const r = require; r(\"./d/\" + x);", "webview/probe.js"],
    ["import \"./ok\"; require(\"./ok2\"); import \"../x/y\"; import \"./a.b\";"],
    ["setTimeout(() => go(), 0); req.setTimeout(1000); w.setTimeout(fn, 0);", "webview/probe.js"],
    // this page's own document, whose computed member the census leaves, reached through a binding the window rule
    // decides by its initialiser (a script's top-level const, a name destructured from this page's window, a module's
    // var, a function's let, a JavaScript file's const that a member write gives an expando declaration); a rule that
    // read every binding fail-closed would refuse each. The last reads the binding under a cast, satisfies, a non-null
    // mark and a type argument: passed on in an array, an object's property and a spread, as an assignment's value, a
    // shorthand's default and an argument, in a for...of's list, a comparison and a !, none of which writes it
    // (writesBinding reads only a write's target through them). It holds no shorthand property naming the binding, as
    // in { d }, which the language service's isWriteAccess reads as a write, so the rule would leave the binding
    // undecided
    ["const d = document; d[k] = f; const { document: e } = window; e[k] = f; window.document[k] = f;"],
    ["export {}; var d: any = document; d[k] = f;"],
    ["function g() { let d = document; d[k] = f; } g(); const e = document; e.title = \"x\"; e[k] = f;", "webview/probe.js"],
    ["export {}; const d = document; (d as any)[k] = f; (<any>d).title = \"x\"; const e = d!; const o = { x: [d], ...(d satisfies object) }; go(e, o, [...[d]]); let y: any; y = (d as any); ({ y = (d as any) } = {}); for (const x of [d as any]) go(x); if ((d as any) === document && !(d as any)) go(); go(d<any>); d[k] = f;"],
    // PR 923: this page's document in a file that declares no window name and no document at its top level (a
    // script's use of the global, a declaration of the name in a function), in one that declares document only
    // ambiently (declare var document, which binds nothing at run time), and a module's top-level declarations of top,
    // frames and document (a .ts module) and of frames (a .mjs file), which the checker keeps apart from the global:
    // rules (a) and (b) decide each use as before (a use of the global by identity; the module's locals, and the
    // function's, by their declarations) and no file refuses (the file-level refusal is for a script's top-level
    // declaration that is not ambient)
    ["document[k] = f; const d = document; d[k] = f;", "webview/probe.js"],
    ["function g() { var document = window; void document; }\ng();\ndocument[k] = f;", "webview/probe.js"],
    ["declare var document: any;\ndocument[k] = f;"],
    ["export {};\nconst top: number = 5;\nvoid top;\nconst document: any = {};\ndocument.title = \"x\";"],
    ["let frames = 0;\nvoid frames;", "webview/probe.mjs"],
  ];
  for (const [src, file] of accepted) assert.deepEqual(roads(src, file), [], "accepted: " + src);
  // an onmessage or onmessageerror handler is accepted on this page's own window (a census site the census above
  // holds), with a value that sets no handler, or on a name socketRefusal proves a WebSocket through TypeScript's
  // binder: the checker's symbol for the receiver has one declaration, a let, const or var statement's own, neither
  // ambient nor a namespace's export, bound by an initialiser new WebSocket(...) with no other write, or by one write
  // `ws = new WebSocket(...);`, a statement of its own directly in the try block of a try that follows the declaration
  // in its statement list, has no finally, and whose catch ends in a return and holds no break, continue or label,
  // with every read after that try, inside the declaration's statement list and not inside a function declaration
  // there (the live shape, in TypeScript and in JavaScript; socketRefusal's clause 2 states it); every write found by
  // the language service, and the constructor a library global. A binding of the name the checker keeps apart is no
  // write to the socket: a parameter or a var of the name in an unrelated function, an outer var the declaration
  // shadows, a namespace's own var, a parameter of the name beside a default that writes it, a body's var written in
  // its body, and a function declared directly in a function body (a function declared in a block refuses, clause 0,
  // in any file). A message listener on this page's own window is a census site, no road. Each row's last column is
  // how many onmessage census sites it holds: a handler on this page's own window is one, and every other accepted
  // handler (a socket, a detach, a tested read) is none
  const handlerOk: Array<[string, string | undefined, number]> = [
    ["const ws = new WebSocket(u); ws.onmessage = (ev: MessageEvent) => { go(ev.data); };", undefined, 0],
    ["function c(u: string) { let ws: WebSocket; try { ws = new WebSocket(u); } catch (e) { setTimeout(() => c(u), 2000); return; } const o: any = {}; o.ws = ws; ws.onopen = () => { ws.send(\"\"); }; ws.onmessage = (ev: MessageEvent) => { go(ev.data); }; }", undefined, 0],
    ["function c(u) { var ws; try { ws = new WebSocket(u); } catch (e) { return; } ws.onmessage = f; }", "webview/probe.js", 0],
    ["const ws = new window.WebSocket(u); ws.onmessage = f;", undefined, 0],
    ["const ws = new WebSocket(u); ws.onmessage = f; function g() { var ws = window; return ws; }", undefined, 0],
    ["const ws = new WebSocket(u); function g(ws) { return ws; } ws.onmessage = f;", "webview/probe.js", 0],
    ["const ws = new WebSocket(u); const o = { ws: 1 }; o.ws = 2; ws.onmessage = f;", "webview/probe.js", 0],
    ["var ws = window; function g() { const ws = new WebSocket(u); ws.onmessage = f; } g();", "webview/probe.js", 0],
    ["namespace N { var ws: any = new WebSocket(u); export function arm() { ws.onmessage = f; } } (N as any).ws = window; N.arm();", undefined, 0],
    ["const ws = new WebSocket(u); namespace N { var ws: any = window; } namespace N { ws.onmessage = f; }", undefined, 0],
    ["const ws = new WebSocket(u); namespace N { ws.onmessage = f; }", undefined, 0],
    ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: } arm();", "webview/probe.js", 0],
    ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { let ws; ws = window; } } arm();", "webview/probe.js", 0],
    ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: (function (ws) { ws = window; })(1); } arm();", "webview/probe.js", 0],
    ["let ws = new WebSocket(u); function h(ws, a = (ws = window)) { var ws; } h(); ws.onmessage = f;", "webview/probe.js", 0],
    ["let ws = new WebSocket(u); function h(a) { var ws; ws = window; } h(); ws.onmessage = f;", "webview/probe.js", 0],
    ["var ws = window; function h(a) { var ws = new WebSocket(u); ws.onmessage = f; } h();", "webview/probe.js", 0],
    ["let ws = new WebSocket(u); function h() { function ws() {} ws = window; } h(); ws.onmessage = f;", "webview/probe.js", 0],
    ["const dead = c.ws; dead.onopen = dead.onmessage = dead.onclose = dead.onerror = null;", undefined, 0],
    ["document.body.onmessage = null; x.onmessage = undefined; y.onmessageerror = z.onmessage = null;", undefined, 0],
    ["window.onmessageerror = f; document.defaultView.onmessage = g; const w = window; w.onmessage = h;", undefined, 3],
    ["frames.onmessage = f; window.frames.onmessageerror = g; var w = frames; w.onmessage = h; fr\\u0061mes[\"onmessage\"] = i;", undefined, 4],
    ["if (port.onmessage) go(); const has = \"onmessage\" in window; type T = { onmessage: ((e: unknown) => void) | null };", undefined, 0],
    ["let t: WebSocket | null = null; type K = typeof WebSocket; const label = \"WebSocket closed\";", undefined, 0],
    ["window.addEventListener(\"messageerror\", f); self.addEventListener(\"message\", g);", undefined, 0],
    // receivers the binder resolves to the page's own window through a scope the old hand-written resolver could not follow, so each is
    // one own-window site, not a road: a namespace export var or let initialised to window (merged blocks, a
    // namespace merged with a function or an enum, a dotted namespace), a switch case block's let, and a
    // receiver in a parameter's default whose name the parameters' scope resolves to the outer window
    ["let ws = new WebSocket(u); namespace N { export var ws: any = window; } namespace N { ws.onmessage = f; }", undefined, 1],
    ["const ws = new WebSocket(u); namespace N { export let ws: any = window; } namespace N { export function arm() { ws.onmessage = f; } } N.arm();", undefined, 1],
    ["namespace N { export var ws: any = window; } namespace N { var q = 1; } namespace N { let ws2 = 0; ws.onmessage = f; } var ws = new WebSocket(u);", undefined, 1],
    ["const ws = new WebSocket(u); function N() {} namespace N { export var ws: any = window; } namespace N { ws.onmessage = f; }", undefined, 1],
    ["const ws = new WebSocket(u); enum N { A } namespace N { export var ws: any = window; } namespace N { ws.onmessage = f; }", undefined, 1],
    ["const ws = new WebSocket(u); namespace A.B { export var ws: any = window; } namespace A.B { ws.onmessage = f; }", undefined, 1],
    ["switch (1) { case 0: let ws = window; case 1: ws = new WebSocket(u); ws.onmessage = f; }", "webview/probe.js", 1],
    ["var ws = window; function h(a = (ws.onmessage = f)) { var ws = new WebSocket(u); } h();", "webview/probe.js", 1],
    ["function h(a = (ws.onmessage = f)) { var ws = new WebSocket(u); } var ws = window; h();", "webview/probe.js", 1],
    ["var ws = window; ((a = (ws.onmessage = f)) => { var ws = new WebSocket(u); })();", "webview/probe.js", 1],
    ["let ws = window; function h(a = (ws.onmessage = f)) { var ws = new WebSocket(u); } h();", "webview/probe.js", 1],
    ["var ws = window; function h(k = class { static s = 1; }, a = (ws.onmessage = f)) { var ws = new WebSocket(u); } h();", "webview/probe.js", 1],
    ["var ws: any = window; function h(a: any = (ws.onmessage = f)) { var ws: any = new WebSocket(u); } h();", undefined, 1],
    // PR 923: an onmessage handler on a window named through a module-local ambient shadow (declare var frames) is set on
    // this page's own window at run time, because esbuild drops the declare and the name is the raw global window, so it is
    // one census site, not a road. b1bae88f7 read the shadow as an unresolved receiver and refused it as an unprovable
    // socket
    ["export {}; declare var frames: any;\nframes.onmessage = function (e: MessageEvent) { void e; };", undefined, 1],
    ["export {}; declare var self: any;\nself.onmessage = function (e: MessageEvent) { void e; };", undefined, 1],
    // PR 923: a name the checker gives more than one declaration, at least one of them a variable declaration whose
    // initialiser is a window (var ws = new WebSocket(u); var ws = window): at run time one of the initialisers runs
    // last, so the name can be the page's own window, and an onmessage handler on it is a census site, not an
    // unprovable socket. refKind reads the name as a window when ANY initialiser binds one, fail closed; the socket
    // proof (two declarations) never runs here. b1bae88f7 and 1d9a9d631 refused these as unprovable sockets, reading
    // the name as unresolved. In a block, a for head, a conditional block (fail closed when the window branch may not
    // run), a for's comma-list var, and a catch clause whose var of the name binds the window
    ["var ws = new WebSocket(u); var ws = window; ws.onmessage = f;", "webview/probe.js", 1],
    ["var ws = new WebSocket(u); var ws: any = window; ws.onmessage = f;", undefined, 1],
    ["var ws = new WebSocket(u); { var ws = window; } ws.onmessage = f;", "webview/probe.js", 1],
    ["function g() { var ws = new WebSocket(u); if (c) { var ws = window; } ws.onmessage = f; }", "webview/probe.js", 1],
    ["var ws = new WebSocket(u); for (var ws = window; false; ) {} ws.onmessage = f;", "webview/probe.js", 1],
    ["var ws = new WebSocket(u); try { throw 0; } catch (ws) { var ws = window; } ws.onmessage = f;", "webview/probe.js", 1],
    ["function g() { var ws = new WebSocket(u); for (var i = 0, ws = window; false;) {} ws.onmessage = f; } g();", "webview/probe.js", 1],
    // PR 923, the rule-stated window decision: a name destructured from this page's window in a JavaScript script,
    // whose top-level member write gives it a second, expando declaration, is that window (rule (b) through declKind),
    // so a handler on it is a census site; b3eb94f8a read it as nothing and refused it as an unprovable socket
    ["const { self: ws } = window;\nws.onmessage = function (e) { void e; };", "webview/probe.js", 1],
    // PR 923: this page's window reached through a literal key in brackets or under parentheses or a cast, a
    // destructured key or an element access (rule (b), keyKind), is that window, so a handler on it is a census site;
    // 31b90f0f9 read each key as nothing and refused the handler as an unprovable socket
    ["const { [\"self\"]: ws } = window;\nws.onmessage = function (e) { void e; };", "webview/probe.js", 1],
    ["export {};\nconst ws = (window as any)[(\"self\")];\nws.onmessage = function (e: unknown) { void e; };", undefined, 1],
  ];
  const missed: string[] = [];
  for (const [src, file, sites] of handlerOk) {
    const got = roads(src, file);
    if (got.length) missed.push("not accepted: " + src + " (refused for: " + JSON.stringify(got) + ")");
    const n = sitesIn(file || "webview/probe.ts", src).filter((x) => x.kind === "onmessage").length;
    if (n !== sites) missed.push("onmessage census sites " + n + ", not " + sites + ": " + src);
  }
  // roads on the list of what the rules cannot see, held accepted as that list's witnesses (a census that comes to see
  // one turns its row red, and the list's entry goes with it). The first four are ways a socket the census accepts is
  // the window at run time: a global WebSocket replaced through an object built with a computed key and copied onto the
  // window, and a classic script's top-level var rebound through the global object by a call, Reflect.set's and
  // Object.assign's. The next four are esbuild's dead-code drop: a window name shadowed by a var at a module's top
  // level whose only declaration sits in a statically-dead branch (if (false) {}, an empty try's catch), or by a let
  // after a return in a function, which esbuild drops (the release build, --production; the default build, which does
  // not minify, drops the empty try's catch too), leaving the name the raw global window at run time. The census reads
  // the shadow through its declaration (an initialiser refKind reads as nothing, var frames = 0, so refKind is null; a
  // document initialiser, so refKind is that document), so it does not refuse the computed handler write. It models
  // only the ambient and declaration-file drop (bindsNothingAtRuntime), not esbuild's dead-code elimination of a
  // live declaration, so these land window.onmessage in the shipped bundle and the census accepts them. Each is a
  // module (a .mjs file): the first three declare their var at the file's top level, which in a script would refuse (a
  // script's top-level declaration of a window name refuses), and the fourth's let is in a function, which a script
  // would not refuse either. No row here holds a let, const or class in a block of a script, which the list's entry
  // names too. The last five reach a reflective or prototype function another way than its Reflect. or Object.
  // spelling
  const unseen: Array<[string, string?]> = [
    ["const o: any = {}; o[[\"Web\", \"Socket\"].join(\"\")] = function () { return window; }; Object.assign(window, o); const ws = new WebSocket(u); ws.onmessage = f;"],
    ["Object.assign(window, make()); const ws = new WebSocket(u); ws.onmessage = f;"],
    ["var ws = new WebSocket(u); Reflect.set(window, \"ws\", window); ws.onmessage = f;", "webview/probe.js"],
    ["var ws = new WebSocket(u); Object.assign(window, { ws: window }); ws.onmessage = f;", "webview/probe.js"],
    // zz-deadvar-null-drop: a shadow with an initialiser refKind reads as nothing (var frames = 0) that esbuild drops (the release build), refKind null
    ["if (false) { var frames = 0; } var k = [\"on\", \"message\"].join(\"\"); function h(e){ void e; } frames[k] = h;", "webview/probe.mjs"],
    // zz-deadvar-document-drop: a document-initialised shadow that esbuild drops (the release build), refKind document
    ["if (false) { var frames = document; } var k = [\"on\", \"message\"].join(\"\"); function h(e){ void e; } frames[k] = h;", "webview/probe.mjs"],
    // zz-deadtry-catch-drop: a shadow declared only in an empty try's catch, which the default build drops too
    ["try {} catch { var frames = 0; } var k = [\"on\", \"message\"].join(\"\"); function h(e){ void e; } frames[k] = h;", "webview/probe.mjs"],
    // zz-deadlet-return-drop: a let after a return, which the release build drops, so the use before it is the global
    ["var k = [\"on\", \"message\"].join(\"\"); function h(e){ void e; } function g() { frames[k] = h; return; let frames = 0; } g();", "webview/probe.mjs"],
    // a reflective write onto the window reaching Reflect.set another way than its Reflect. or Object. spelling, which
    // globalName does not strip: through frames (this page's own window), a comma expression, or Function.prototype.call
    ["frames.Reflect.set(window, k, f);"],
    ["(0, Reflect.set)(window, k, f);"],
    ["Reflect.set.call(null, window, k, f);"],
    // through another window, and a prototype read through frames
    ["parent.Reflect.set(window, k, f);"],
    ["frames.Object.getPrototypeOf(window)[k] = f;"],
  ];
  for (const [src, file] of unseen) {
    const got = roads(src, file);
    if (got.length) missed.push("refused, though the list of what the rules cannot see names its road: " + src + " (refused for: " + JSON.stringify(got) + ")");
  }
  // every other road, each refused for the reason named. A handler assigned on a window other than this page's own,
  // whatever its value, or a value that sets a handler on a receiver the census resolves to neither this page's window
  // nor a socket, is refused and is no census site
  const OTHER_WINDOW = /handler on a window other than this page's own/;
  const UNRESOLVED = /handler on a receiver the census cannot resolve to this page's window or to a socket/;
  const COMPUTED = /reached by a computed name|destructured by a computed key|with a computed key|from an object with a computed key|run with the window as its this/;
  const byReason: Array<[RegExp, boolean, Array<[string, string?]>]> = [
    // a window other than this page's own, whatever the value
    [OTHER_WINDOW, true, [
      ["top.onmessage = f;"], ["parent.onmessage = f;"], ["opener.onmessage = f;"], ["self.parent.onmessage = f;"],
      ["globalThis.top.onmessage = f;"], ["parent.frames.onmessage = f;"], ["top.frames[\"onmessageerror\"] = f;"],
      ["(window as any).parent.onmessage = f;"], ["(window?.parent).onmessage = f;"],
      ["window!.parent!.onmessage = f;"], ["el.ownerDocument.defaultView.onmessage = f;"], ["frame.contentWindow.onmessage = f;"],
      ["top.document.defaultView.onmessage = f;"], ["const w = self.parent; w.onmessage = f;"], ["var w = frames[0]; w.onmessage = f;"],
      ["const { parent: p } = window; p.onmessage = f;"], ["const { frames: { top: t } } = window; t.onmessage = f;"],
      ["frames[0].onmessage = f;"], ["window[0].onmessage = f;"], ["window[\"1\"].onmessage = f;"], ["parent.frames[0].onmessage = f;"],
      ["window.frames.frames[0].onmessage = f;"], ["fr\\u0061mes[0].onmessage = f;"], ["top[\"onmessageerror\"] = f;"],
      ["e.target.onmessage = f;"], ["ev.view.onmessage = f;"], ["e.currentTarget.onmessage = f;"], ["e.srcElement.onmessage = f;"],
      ["parent.onmessage = null;"],
      // PR 923, the rule-stated window decision: a name destructured from a window in a JavaScript script, whose
      // top-level member write gives it a second, expando declaration; b3eb94f8a read it as nothing and refused it as
      // an unprovable socket
      ["const { parent: ws } = window;\nws.onmessage = function (e) { void e; };", "webview/probe.js"],
      // PR 923: another window reached through a literal key in brackets (rule (b), keyKind); 31b90f0f9 read the key as
      // nothing and refused the handler as an unprovable socket
      ["const { [\"parent\"]: ws } = window;\nws.onmessage = function (e) { void e; };", "webview/probe.js"],
    ]],
    [/listener added to a window other than this page's own/, false, [
      ["parent.addEventListener(\"message\", (e) => { go(e.data); });"], ["frames[0].addEventListener(\"message\", f);"],
      ["top.addEventListener(\"messageerror\", f);"], ["frame.contentWindow.addEventListener(\"message\", f);"],
      ["window.opener?.addEventListener(\"message\", f);"],
    ]],
    // a receiver the census cannot resolve to this page's window or to a socket
    [UNRESOLVED, true, [
      ["document.body.onmessage = f;"], ["document.body.onmessageerror = f;"], ["document.querySelector(\"body\").onmessage = f;"],
      ["document.getElementsByTagName(\"frameset\")[0].onmessage = f;"], ["function g(w) { w.onmessage = f; }"],
      ["let w; w = window; w.onmessage = f;"], ["const o = { w: window }; o.w.onmessage = f;"], ["getWin().onmessage = f;"],
      ["(x || window).onmessage = f;"], ["window.window.window.window.window.window.onmessage = f;"], ["let w; (w = window).onmessage = f;"],
      ["(0, window).onmessage = f;"], ["(c ? window : self).onmessage = f;"], ["const [w] = [window]; w.onmessage = f;"],
      ["const { x: w = window } = {}; w.onmessage = f;"], ["for (const w of [window]) w.onmessage = f;"],
      ["ws.onmessage = f;"], ["let ws = new WebSocket(u); ws = window; ws.onmessage = f;"],
      ["let ws = new WebSocket(u); [ws] = [window]; ws.onmessage = f;"], ["let ws = new WebSocket(u); ({ ws } = { ws: window }); ws.onmessage = f;"],
      ["let ws = new WebSocket(u); ({ x: ws = window } = {}); ws.onmessage = f;"], ["let ws = new WebSocket(u); [ws = window] = []; ws.onmessage = f;"],
      ["let ws = new WebSocket(u); (() => { ws = window; })(); ws.onmessage = f;"], ["let ws = new WebSocket(u); ws ||= window; ws.onmessage = f;"],
      ["const ws = new WebSocket(u); const ws2 = ws; ws2.onmessage = f;"], ["const ws = new Wrapper(u); ws.onmessage = f;"],
      ["function g(ws = new WebSocket(u)) { ws.onmessage = f; }"], ["const g = (ws = new WebSocket(u)) => { ws.onmessage = f; };"],
      ["let ws = new WebSocket(u); try { throw window; } catch (ws) { ws.onmessage = f; ws = new WebSocket(u); }"],
      ["for (let ws of [window]) { ws.onmessage = f; ws = new WebSocket(u); }"],
      ["const port = new MessageChannel().port1; port.onmessage = f;"], ["const wk = new Worker(u); wk.onmessage = f;"],
      ["const bc = new BroadcastChannel(\"notes-api\"); bc.onmessage = f;"], ["const es = new EventSource(u); es.onmessage = f;"],
      ["class C { m() { this.onmessage = f; } }"], ["const b = document.body; b[\"onmessage\"] = f;"],
      ["function h(undefined) { document.body.onmessage = undefined; }", "webview/probe.js"],
      ["x.onmessage = y = f;"],
      // a WebSocket the checker does not resolve to a library global makes no socket (clause 4; the name is refused
      // below too)
      ["class WebSocket { constructor() { return window; } } const ws = new WebSocket(u); ws.onmessage = f;"],
      ["function g(WebSocket: any) { const ws = new WebSocket(u); ws.onmessage = f; }"],
      // a var of the socket's name declared again in a for...in or for...of head, whose declaration has no initialiser to
      // bind a window (the receiver stays unresolved, the socket refused for its two declarations). A var redeclared with a
      // window initialiser (var ws = new WebSocket; var ws = window) is read as the window it becomes at run time and is a
      // census site, in handlerOk below.
      ["var ws = new WebSocket(u); for (var ws of [window]) {} ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); for (var ws in o) {} ws.onmessage = f;", "webview/probe.js"],
      // one declaration proves a socket: a second one bound to new WebSocket(...) refuses too, and a catch parameter
      // that holds the receiver is what the checker resolves it to
      ["var ws = new WebSocket(u); var ws = new WebSocket(u2); ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); try { throw window; } catch (ws) { var ws; ws.onmessage = f; }", "webview/probe.js"],
      // a destructuring target, in a declaration or in an assignment, a default included
      ["var ws = new WebSocket(u); var { x: ws = window } = {}; ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); var [ws] = [window]; ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); [ws = new WebSocket(u)] = [window]; ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); ({ a: ws = new WebSocket(u) } = { a: window }); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); ({ ws = new WebSocket(u) } = { ws: window }); ws.onmessage = f;", "webview/probe.js"],
      // a for...in or for...of head, declared or not, destructured or not, and a for head
      ["var ws = new WebSocket(u); for (var [ws] of [[window]]) {} ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); for (var { length: ws } in { ab: 1 }) {} ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); for (ws of [window]) {} ws.onmessage = f;", "webview/probe.js"],
      // a parameter, plain or destructured, and a catch parameter, whether the receiver is read before or after the
      // var: the checker's symbol is the parameter merged with the var, or the catch parameter
      ["function g(ws) { if (0) { var ws = new WebSocket(u); } ws.onmessage = f; } g(window);", "webview/probe.js"],
      ["function g(ws) { ws.onmessage = f; var ws = new WebSocket(u); } g(window);", "webview/probe.js"],
      ["function g({ w: ws }) { if (0) { var ws = new WebSocket(u); } ws.onmessage = f; } g({ w: window });", "webview/probe.js"],
      ["try { throw window; } catch (ws) { var ws = new WebSocket(u); ws.onmessage = f; }", "webview/probe.js"],
      ["try { throw window; } catch (ws) { ws.onmessage = f; var ws = new WebSocket(u); }", "webview/probe.js"],
      // an import, a function or class, an enum of the name
      ["import { ws } from \"./m\"; var ws = new WebSocket(u); ws.onmessage = f;"],
      ["var ws = new WebSocket(u); function ws() {} ws.onmessage = f;", "webview/probe.js"],
      ["function ws() {} if (0) { var ws = new WebSocket(u); } ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); enum ws { A } ws.onmessage = f;"],
      // an import alias of the name in a namespace block that holds the receiver but not the declaration: the checker
      // resolves the receiver to the alias, which is what it names at run time, and no let, const or var statement's
      // own
      ["const ws = new WebSocket(u); namespace W { export var w: any = window; } namespace N { import ws = W.w; ws.onmessage = f; }"],
      ["const ws = new WebSocket(u); namespace W { export var w: any = window; } namespace N { import ws = W.w; export function arm() { ws.onmessage = f; } } N.arm();"],
      // a write other than a statement of its own assigning new WebSocket(...), a declaration that is no let, const or var
      // statement's own (a for head's, or a catch clause's parameter, whichever side of the handler the assignment of
      // new WebSocket(...) sits), and a name never bound to a socket
      ["let ws; ws = new WebSocket(u), ws = window; ws.onmessage = f;", "webview/probe.js"],
      ["let ws, w2; ws = w2 = new WebSocket(u); w2 = window; ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); ws++; ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws; go(ws = new WebSocket(u)); ws.onmessage = f;", "webview/probe.js"],
      ["for (let ws = new WebSocket(u); ; ) { ws.onmessage = f; break; }", "webview/probe.js"],
      ["try { throw window; } catch (ws) { if (0) ws = new WebSocket(u); ws.onmessage = f; }", "webview/probe.js"],
      ["try { throw window; } catch (ws) { ws.onmessage = f; ws = new WebSocket(u); }", "webview/probe.js"],
      ["let ws = pick(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws; ws.onmessage = f;", "webview/probe.js"],
      // a write in another case clause of the switch whose case block holds the declaration: the checker resolves it to
      // the case block's let, a second write (clause 3), whatever binding of the name sits outside the switch (a var, a
      // parameter, an import, a function), a destructuring target's write included
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws: any = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();"],
      ["var ws; switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();", "webview/probe.js"],
      ["function g(ws) { switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm(); } g(1);", "webview/probe.js"],
      ["import { ws } from \"./m\"; switch (0) { case 0: let ws: any = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();"],
      ["function ws() {} switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();", "webview/probe.js"],
      ["var ws; switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: [ws] = [window]; } arm();", "webview/probe.js"],
      // and with a function of the name declared in a block inside the switch that does not hold the write (the block
      // in the write's clause, in the declaration's clause, in default:, or an if statement's; a destructuring write):
      // the block function refuses on its own (clause 0, in any file), and the checker binds it in its block and
      // resolves the write to the case block's let (clause 3). The last two are refused as binder errors of strict code,
      // not by clause 3: a function that is an if statement's clause, which the binder reports as a redeclaration of the
      // case block's let (TS2451), and a labelled function (a label on a declaration, which strict code forbids)
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { function ws() {} } ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws: any = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { function ws() {} } ws = window; } arm();"],
      ["switch (0) { case 0: let ws = new WebSocket(u); { function ws() {} } var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; default: { function ws() {} } ws = window; } arm();", "webview/probe.js"],
      ["function g() { switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: if (1) { function ws() {} } ws = window; } arm(); } g();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { function ws() {} } [ws] = [window]; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: if (1) function ws() {} ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { l: function ws() {} ws = window; } } arm();", "webview/probe.js"],
      // and a write inside a function, class static block or namespace nested in the declaration's scope, where that
      // scope declares a function of the name in a block the write is not in: the checker binds the function in its
      // block and resolves the write to the socket (clause 3), and the function refuses on its own (clause 0, in any
      // file): in a function, in a module with no let in between, the TypeScript form, in a namespace, a class static
      // block, an arrow function and a method, a destructuring write, and a function that is an if statement's clause
      // or a label's statement
      ["let ws = new WebSocket(u); function h() { { let ws; { function ws() {} } } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws = new WebSocket(u); function h() { { function ws() {} } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws: any = new WebSocket(u); function h() { { let ws; { function ws() {} } } ws = window; } h(); ws.onmessage = f;"],
      ["let ws: any = new WebSocket(u); namespace N { { let ws; { function ws() {} } } ws = window; } ws.onmessage = f;"],
      ["let ws = new WebSocket(u); class K { static { { let ws; { function ws() {} } } ws = window; } } ws.onmessage = f;", "webview/probe.js"],
      ["{ let ws = new WebSocket(u); (() => { { let ws; { function ws() {} } } ws = window; })(); ws.onmessage = f; }", "webview/probe.js"],
      ["let ws = new WebSocket(u); const o = { m() { { let ws; { function ws() {} } } ws = window; } }; o.m(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { { let ws; { function ws() {} } } [ws] = [window]; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { { let ws; if (1) function ws() {} } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { { let ws; { l: function ws() {} } } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      // an ambient declaration, which binds nothing at run time (an ambient var's name is a property of the global
      // object; clause 1)
      ["declare var ws: any = new WebSocket(u); (window as any).ws = window; ws.onmessage = f;"],
      ["declare let ws: any = new WebSocket(u); (window as any).ws = window; ws.onmessage = f;"],
      ["export declare var ws: any = new WebSocket(u); (window as any).ws = window; ws.onmessage = f;"],
      ["declare var ws: any; (window as any).ws = window; if (0) ws = new WebSocket(u); ws.onmessage = f;"],
      ["declare var ws: any; if (0) ws = new WebSocket(u); ws.onmessage = f;"],
      // a namespace's export as the declaration, a property of the namespace object any code can set (clause 1)
      ["namespace N { export var ws: any = new WebSocket(u); export function arm() { ws.onmessage = f; } } (N as any).ws = window; N.arm();"],
      ["namespace N { export let ws: any = new WebSocket(u); (N as any).ws = window; ws.onmessage = f; }"],
      ["namespace N { export const ws: any = new WebSocket(u); export function arm() { ws.onmessage = f; } } Object.defineProperty(N, \"ws\", { value: window }); N.arm();"],
      ["namespace N { export let ws: any; ws = new WebSocket(u); export function arm() { ws.onmessage = f; } } (N as any).ws = window; N.arm();"],
      ["export namespace N { export var ws: any = new WebSocket(u); export function arm() { ws.onmessage = f; } } (N as any).ws = window; N.arm();"],
      // a namespace's export of the name the checker resolves the receiver to, which is no let, const or var statement of
      // its own (clause 1): a destructured export var (the receiver's declaration is a binding element), and a name a
      // namespace re-exports through export import. (An export var initialised to a socket is refused as a namespace
      // export above; an export var or let initialised to window resolves to the window, an own site, and is in
      // handlerOk.)
      ["const ws = new WebSocket(u); namespace N { export var { ws } = { ws: window as any }; } namespace N { ws.onmessage = f; }"],
      ["const ws = new WebSocket(u); namespace W { export var w: any = window; } namespace N { export import ws = W.w; } namespace N { ws.onmessage = f; }"],
      // more writes in another case clause of the switch that holds the declaration: past an outer binding in
      // TypeScript, in a default clause beside an outer let, to a case block's const, and in a function the other
      // clause declares
      ["var ws: any; switch (0) { case 0: let ws: any = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();"],
      ["let ws = 0; { switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; default: ws = window; } } arm();", "webview/probe.js"],
      ["var ws; switch (0) { case 0: const ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: ws = window; } arm();", "webview/probe.js"],
      ["var ws; switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: function h() { ws = window; } h(); } arm();", "webview/probe.js"],
      // more declarations of the name in the other clause: a function as an if statement's clause in TypeScript, in
      // an else, behind a label, beside a write in a function the other clause declares, async, and an enum or a class
      // in a block; and a static block's write
      ["switch (0) { case 0: let ws: any = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: if (1) function ws() {} ws = window; } arm();"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: if (0) function ws() {} else ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: l: { function ws() {} } ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { l: function ws() {} } ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { function ws() {} } function h() { ws = window; } h(); } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws: any = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: class K { static { ws = window; } } } arm();"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { async function ws() {} } ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: l: function ws() {} ws = window; } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws: any = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { enum ws { A } } ws = window; } arm();"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { class ws {} } ws = window; } arm();", "webview/probe.js"],
      // more functions of the name in a block of a scope nested in the declaration's, the write outside that block:
      // with no let in between, under use strict, in a namespace and a static block with no let, beside a write of a
      // second socket, and async and generator functions
      ["let ws = new WebSocket(u); function h() { { function ws() {} } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["\"use strict\"; let ws = new WebSocket(u); function h() { { function ws() {} } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws: any = new WebSocket(u); namespace N { { function ws() {} } ws = window; } ws.onmessage = f;"],
      ["let ws = new WebSocket(u); class K { static { { function ws() {} } ws = window; } } ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { { let ws; { function ws() {} } } ws = new WebSocket(u2); } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { { let ws; { async function ws() {} } } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { { let ws; { function* ws() {} } } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      // in JavaScript, a second write, plain and logical, and a catch parameter beside a var of its name in a block;
      // and a class expression's and a function expression's own name, a block function beside a var, a labelled
      // function, writes from a default, a field and a static block, an if statement's function, an ambient function,
      // and an export list in a namespace
      ["let ws = new WebSocket(u); ws = window; ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); ws ||= window; ws.onmessage = f;", "webview/probe.js"],
      ["try { throw window; } catch (ws) { if (0) { var ws = new WebSocket(u); } ws.onmessage = f; }", "webview/probe.js"],
      ["const ws = new WebSocket(u); const C = class ws { static m() { ws.onmessage = f; } }; C.m();", "webview/probe.js"],
      ["const ws = new WebSocket(u); const g = function ws() { ws.onmessage = f; }; g();", "webview/probe.js"],
      ["function g() { var ws = new WebSocket(u); { function ws() {} } ws.onmessage = f; } g();", "webview/probe.js"],
      ["var ws = new WebSocket(u); lbl: function ws() {} ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h(a = (ws = window)) {} h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); class K { x = (ws = window); } new K(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); class K { static { ws = window; } } ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); if (1) function ws() {} ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); declare function ws(): void; ws.onmessage = f;"],
      ["namespace N { var ws: any = new WebSocket(u); export { ws }; export function arm() { ws.onmessage = f; } } (N as any).ws = window; N.arm();"],
      // a write in a parameter's default, which runs in the parameters' scope and sets the outer socket, beside a var
      // of the name in the body (a function, an arrow, a method, TypeScript, a destructured default, a for...of var, a
      // module, and beside a parameter that holds a class expression with a static field, in JavaScript and in
      // TypeScript): the checker, at target ESNext, resolves the default's name past the body's var to the socket
      // (clause 3). Under the tsconfig's ES2021 it resolves the name in the last two rows to the body's var, and they
      // would be accepted (the section above socketRefusal says why the program's target is ESNext)
      ["let ws = new WebSocket(u); function h(a = (ws = window)) { var ws; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); const k = (a = (ws = window)) => { var ws; }; k(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); const o = { m(a = (ws = window)) { var ws; } }; o.m(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws: any = new WebSocket(u); function h(a: any = (ws = window)) { var ws: any; } h(); ws.onmessage = f;"],
      ["let ws = new WebSocket(u); function h({ a = (ws = window) } = {}) { var ws; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h(a = (ws = window)) { for (var ws of []) {} } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws = new WebSocket(u); function h(a = (ws = window)) { var ws; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h(k = class { static s = 1; }, a = (ws = window)) { var ws; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws: any = new WebSocket(u); function h(k: any = class { static s = 1; }, a: any = (ws = window)) { var ws: any; } h(); ws.onmessage = f;"],
      // a receiver in a parameter's default with no outer binding of the name (window.ws is a member write, no binding),
      // and the body var not in scope in the default: the checker resolves the receiver to no symbol (clause 1). (When an
      // outer binding IS a window, the checker resolves the default's receiver to it, an own site, and it is in handlerOk.)
      ["window.ws = window; function h(a = (ws.onmessage = f)) { var ws = new WebSocket(u); } h();", "webview/probe.js"],
      // shape B (clause 2) takes one write, in the try block of a try beside the declaration and after it, whose catch
      // ends in a return and which has no finally, and every read after that try: a write with no try, a second write,
      // a catch that does not return (each accepted before this rule), a finally, a try in a loop whose catch can
      // break, the write not a statement of the try block, inside a label there, a read before the write, a read in a
      // hoisted function declaration, and a second write after the try
      ["let ws: WebSocket; ws = new WebSocket(u); ws.onmessage = (ev: MessageEvent) => { go(ev.data); };"],
      ["let ws = new WebSocket(u); ws = new WebSocket(u2); ws.onmessage = f;"],
      ["let ws; ws = new WebSocket(u); ws.onmessage = f;", "webview/probe.js"],
      ["let ws; try { ws = new WebSocket(u); } catch (e) { } ws.onmessage = f;", "webview/probe.js"],
      ["function c(u: string) { let ws: WebSocket; try { ws = new WebSocket(u); } catch (e) { } ws.onmessage = f; }"],
      ["function c(u: string) { let ws: WebSocket; try { ws = new WebSocket(u); } catch (e) { return; } finally { } ws.onmessage = f; }"],
      ["function c(u: string) { let ws: WebSocket; for (;;) { try { ws = new WebSocket(u); } catch (e) { if (u) break; return; } } ws.onmessage = f; }"],
      ["function c(u: string) { let ws: WebSocket; try { if (u) ws = new WebSocket(u); } catch (e) { return; } ws.onmessage = f; }"],
      ["function c(u: string) { let ws: WebSocket; try { l: { ws = new WebSocket(u); } } catch (e) { return; } ws.onmessage = f; }"],
      ["function c(u: string) { let ws: WebSocket; ws.onmessage = f; try { ws = new WebSocket(u); } catch (e) { return; } }"],
      ["function c(u: string) { let ws: WebSocket; try { ws = new WebSocket(u); } catch (e) { return; } g(); function g() { ws.onmessage = f; } }"],
      ["function c(u: string) { let ws: WebSocket; try { ws = new WebSocket(u); } catch (e) { return; } ws = new WebSocket(u); ws.onmessage = f; }"],
      // clause 0, in any file: a function declaration of ANY name and kind declared in a block, refused by its position (a
      // sloppy-mode file hoists a plain one into its enclosing function; an async or generator one Annex B never hoists,
      // refused all the same). In a script: five shapes, the fifth an Annex B
      // shape whose unbundled run copies the window into the function's var at the declaration, where the receiver reads
      // it; the fifth under use strict; and a block function WebSocket or window. In a module: the same five shapes,
      // whose writes the checker reads as writes to another binding than the socket's. In a file TypeScript calls a
      // module and esbuild bundles as sloppy CommonJS (a .cjs or .cts file with no import or export, a TypeScript file
      // whose only module syntax is import x = require(...) or export =): a function window given a WebSocket member
      // through an alias, which the bundle's new window.WebSocket(...) then calls, so the socket is the window (and a
      // function self, in a .cjs); and a function ws declared as an if statement's clause directly in a function body,
      // which clause 0 refuses by its position, though there the checker binds it in that function as sloppy code does
      // (no divergence), so the handler lands on the socket. In a file esbuild bundles as strict code (.mjs, .mts, a
      // TypeScript module with export {}): the function window, refused all the same, since the proof does not decide how
      // the page runs a file. And TypeScript's binder errors: a labelled function, which strict code does not allow, and
      // a duplicate declaration, which the binder sets apart as a symbol of its own
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { function ws() {} ws = window; } } arm();", "webview/probe.js"],
      ["switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: switch (0) { case 0: function ws() {} case 1: ws = window; } } arm();", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { { function ws() {} ws = window; } } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function h() { var ws; { function ws() {} } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); function g() { { ws = window; function ws() {} } ws.onmessage = f; } g();", "webview/probe.js"],
      ["\"use strict\"; let ws = new WebSocket(u); function g() { { ws = window; function ws() {} } ws.onmessage = f; } g();", "webview/probe.js"],
      ["{ function WebSocket() { return window; } } const ws = new WebSocket(u); ws.onmessage = f;", "webview/probe.js"],
      ["{ function window() {} } const ws = new window.WebSocket(u); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: { function ws() {} ws = window; } } arm();", "webview/probe.js"],
      ["export {}; switch (0) { case 0: let ws = new WebSocket(u); var arm = () => { ws.onmessage = f; }; case 1: switch (0) { case 0: function ws() {} case 1: ws = window; } } arm();", "webview/probe.js"],
      ["export {}; let ws = new WebSocket(u); function h() { { function ws() {} ws = window; } } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws = new WebSocket(u); function h() { var ws; { function ws() {} } ws = window; } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws = new WebSocket(u); function g() { { ws = window; function ws() {} } ws.onmessage = f; } g();", "webview/probe.js"],
      ["{ function window() {} const a = window; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new window.WebSocket(u); ws.onmessage = f;", "webview/probe.cjs"],
      ["{ function window() {} const a: any = window; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new window.WebSocket(u); ws.onmessage = f;", "webview/probe.cts"],
      ["import y = require(\"./y\"); { function window() {} const a: any = window; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new window.WebSocket(u); ws.onmessage = f;"],
      ["{ function window() {} const a: any = window; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new window.WebSocket(u); ws.onmessage = f; export = 0;"],
      ["{ function self() {} const a = self; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new self.WebSocket(u); ws.onmessage = f;", "webview/probe.cjs"],
      ["let ws = new WebSocket(u); function g() { { ws = window; function ws() {} } ws.onmessage = f; } g();", "webview/probe.cjs"],
      ["let ws: any = new WebSocket(u); function g() { { ws = window; function ws() {} } ws.onmessage = f; } g();", "webview/probe.cts"],
      ["import y = require(\"./y\"); let ws: any = new WebSocket(u); function g() { { ws = window; function ws() {} } ws.onmessage = f; } g();"],
      ["let ws: any = new WebSocket(u); function g() { { ws = window; function ws() {} } ws.onmessage = f; } g(); export = 0;"],
      ["import y = require(\"./y\"); let ws: any = new WebSocket(u); function h() { if (1) function ws() {} ws = window; } h(); ws.onmessage = f;"],
      ["{ function window() {} const a = window; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new window.WebSocket(u); ws.onmessage = f;", "webview/probe.mjs"],
      ["{ function window() {} const a: any = window; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new window.WebSocket(u); ws.onmessage = f;", "webview/probe.mts"],
      ["export {}; { function window() {} const a: any = window; a[[\"Web\", \"Socket\"].join(\"\")] = function () { return globalThis; }; } const ws = new window.WebSocket(u); ws.onmessage = f;"],
      ["var ws = new WebSocket(u); l: function ws() {} ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); declare function ws(): void; ws.onmessage = f;"],
      ["var ws = new WebSocket(u); class ws {} ws.onmessage = f;", "webview/probe.js"],
      // clause 0 broadened (PR 923): a block function of ANY name, async and generators included, refuses. Each row here
      // is a SOLE clause-0 refusal (the socket is otherwise proved, the block function's name resolves inside its block so
      // no computed arm fires): a plain, an async and a generator function named frames or globalThis, each in a strict
      // file (a TypeScript module, export {}) and a sloppy one (.js); and A1, a frames block hiding a computed write that
      // replaces WebSocket, whose alias resolves to the block function so only clause 0 fires. bd5cf71fd accepts every one
      // (its clause 0 listed only [receiver, WebSocket, window, self]).
      ["export {}; let ws: any = new WebSocket(u); function h() { { function frames() {} } } h(); ws.onmessage = f;"],
      ["let ws = new WebSocket(u); function h() { { function frames() {} } } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws: any = new WebSocket(u); function h() { { function globalThis() {} } } h(); ws.onmessage = f;"],
      ["let ws = new WebSocket(u); function h() { { function globalThis() {} } } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws: any = new WebSocket(u); function h() { { async function frames() {} } } h(); ws.onmessage = f;"],
      ["let ws = new WebSocket(u); function h() { { async function frames() {} } } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws: any = new WebSocket(u); function h() { { function* frames() {} } } h(); ws.onmessage = f;"],
      ["let ws = new WebSocket(u); function h() { { function* frames() {} } } h(); ws.onmessage = f;", "webview/probe.js"],
      ["export {}; let ws: any = new WebSocket(u); function h() { { function frames() {} const a: any = frames; a[[\"Web\", \"Socket\"].join(\"\")] = () => window; } } h(); ws.onmessage = f;"],
      ["let ws = new WebSocket(u); function h() { { function frames() {} const a = frames; a[[\"Web\", \"Socket\"].join(\"\")] = () => window; } } h(); ws.onmessage = f;", "webview/probe.js"],
      // clause 1: a second declaration that writes nothing, and a write through this at a script's top level, which
      // TypeScript records as a declaration of the var; clause 3: a reference that is no identifier of the name (a
      // string key on the global object, an export under another name) and a name the checker resolves to no symbol;
      // clause 4: a script's top-level let window or class WebSocket, which the checker sets apart from the built-in
      // and resolves past, a module's class WebSocket, a parameter WebSocket, and an imported window before .WebSocket
      ["declare var ws: any; var ws = new WebSocket(u); ws.onmessage = f;"],
      ["var ws = new WebSocket(u); var ws; ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); var ws: WebSocket; ws.onmessage = f;"],
      ["var ws = new WebSocket(u); window[\"ws\"] = window; ws.onmessage = f;", "webview/probe.js"],
      ["export let ws = new WebSocket(u); export { ws as w3 }; ws.onmessage = f;"],
      ["var ws = new WebSocket(u); this.ws = window; ws.onmessage = f;", "webview/probe.js"],
      ["let ws = new WebSocket(u); import w2 = ws; ws.onmessage = f;"],
      ["let window = { WebSocket: function () { return self; } }; const ws = new window.WebSocket(u); ws.onmessage = f;", "webview/probe.js"],
      ["class WebSocket { constructor() { return window; } } const ws = new WebSocket(u); ws.onmessage = f;"],
      ["export {}; class WebSocket { constructor() { return window; } } const ws = new WebSocket(u); ws.onmessage = f;"],
      ["function g(WebSocket: any) { const ws = new WebSocket(u); ws.onmessage = f; }"],
      ["import { window } from \"./m\"; const ws = new window.WebSocket(u); ws.onmessage = f;"],
    ]],
    // a with statement answers the names inside it from its object
    [/a with statement/, false, [
      ["var ws = new WebSocket(u); with (o) { ws = window; } ws.onmessage = f;", "webview/probe.js"],
      ["const o = { WebSocket: function () { return window; } }; with (o) { var ws = new WebSocket(u); } ws.onmessage = f;", "webview/probe.js"],
      ["with ({ undefined: f }) { document.body.onmessage = undefined; }", "webview/probe.js"],
      ["const o = { w: window }; with (o) { w.onmessage = f; }", "webview/probe.js"],
      ["with (document.body) { onmessage = f; }", "webview/probe.js"],
    ]],
    // a global WebSocket replaced makes `new WebSocket(...)` any object
    [/the name WebSocket other than as the constructor a new calls/, false, [
      ["window.WebSocket = function () { return window; } as any; const ws = new WebSocket(u); ws.onmessage = f;"],
      ["WebSocket = function () { return window; }; const ws = new WebSocket(u); ws.onmessage = f;", "webview/probe.js"],
      ["Object.defineProperty(window, \"WebSocket\", { value: function () { return window; } }); const ws = new WebSocket(u); ws.onmessage = f;"],
      ["globalThis.WebSocket = X; const ws = new window.WebSocket(u); ws.onmessage = f;"],
      ["class WebSocket { constructor() { return window; } } const ws = new WebSocket(u); ws.onmessage = f;"],
      ["Object.assign(window, { WebSocket: X }); const ws = new WebSocket(u); ws.onmessage = f;"],
      ["const W = WebSocket; const ws = new W(u);"], ["if (x instanceof WebSocket) go();"],
    ]],
    // a member read by a computed name off a receiver the window rule reads as a window, the body element or a document
    // the census cannot tell is this page's; the rows are examples of the ways the rule reads one
    [COMPUTED, false, [
      ["frames[0][k] = f;"], ["Reflect.set(frames[0], k, f);"], ["Object.assign(window[0], { [k]: f });"],
      ["Object.defineProperty(parent.frames[0], k, { value: f });"], ["Object.getOwnPropertyDescriptor(frames[0], k).set.call(frames[0], f);"],
      ["window.frames.frames[0][k] = f;"], ["frames[0][\"add\" + \"EventListener\"](\"message\", f);"],
      ["document.body[k] = f;"], ["const b = document.body; b[\"on\" + \"message\"] = f;"], ["window.document.body[k] = f;"],
      ["Reflect.set(document.body, k, f);"], ["Object.assign(document.body, { [k]: f });"], ["document[\"body\"][k] = f;"],
      ["const doc = document; doc.body[k] = f;"], ["const doc = document; Reflect.set(doc.body, k, f);"],
      ["const { body } = document; body[k] = f;"], ["const { body: b } = document; b[k] = f;"], ["el.ownerDocument.body[k] = f;"],
      ["const { document: { body } } = window; body[k] = f;"], ["frame.contentDocument.body[k] = f;"],
      ["Reflect.set(HTMLBodyElement.prototype, k, f, document.body);"],
      // PR 923: a module-local `declare var document: any` shadows document for the checker only; esbuild drops it, so
      // at run time document is the raw global, and a computed write on its body sets the window's handler.
      // bindsNothingAtRuntime reads that the shadow's declarations are all ambient, so refKind reads document as this
      // page's document (memberKind gives its body), and the body arm sees the write. b1bae88f7 and 1d9a9d631 read the
      // shadow as unresolved and missed it
      ["export {}; declare var document: any;\ndocument.body[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["export {}; declare var document: any;\ndocument.body[\"on\" + \"message\"] = function (e: MessageEvent) { void e; };"],
      ["e.view[k] = f;"], ["Reflect.set(e.view, k, f);"], ["Object.assign(ev.view, { [k]: f });"], ["e.target[k] = f;"],
      ["ev.currentTarget[k] = f;"], ["e.srcElement[k] = f;"],
      // A2 (PR 923): an async or generator function named frames in a block, then a computed onmessage write on the
      // top-level frames. The checker resolves that frames to the global window (the block function is block-scoped, and
      // Annex B never hoists an async or generator function), so the write lands on the window and the computed-name arm
      // sees it; bd5cf71fd resolved frames to the block function and missed the write. It accepts every one.
      ["{ async function frames() {} } frames[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["{ function* frames() {} } frames[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {}; { async function frames() {} } frames[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["export {}; { function* frames() {} } frames[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      // PR 923: a module-local `declare var <name>: any` shadows a window name for the checker only; esbuild drops it, so
      // at run time the name is the raw global (this page's own window for window, self, globalThis, frames; another for
      // top, parent, opener), and a computed write on it lands on that window. windowKind answers "not the global" for the
      // shadow's own symbol, and bindsNothingAtRuntime reads that its declarations are all ambient, so refKind reads the
      // name as the window it is at run time and the computed-name arm sees the write. b1bae88f7 read the shadow as an
      // unresolved local (a variable declaration with no initialiser) and missed it. Each is a module (export {}), so its
      // declare is a symbol of its own, not merged into the global.
      ["export {}; declare var frames: any;\nframes[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["export {}; declare var self: any;\nself[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["export {}; declare var window: any;\nwindow[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["export {}; declare var globalThis: any;\nglobalThis[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["export {}; declare var top: any;\ntop[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["export {}; declare var parent: any;\nparent[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["export {}; declare var opener: any;\nopener[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      // PR 923: a name declared more than once, at least one variable declaration's initialiser a window (a redeclared
      // var w = window; var w = window; and a JavaScript file's top-level var that a top-level expression statement
      // assigns a member of by a plain = assignment (a[k] = f; a compound assignment a[k] ||= f, += or ??= gets no
      // expando), which the checker records a second, expando declaration for): refKind reads it as the window when
      // ANY initialiser binds one, so a computed write on it is seen. b1bae88f7 returned null for any name with more
      // than one declaration and missed it.
      ["export {}; var w: any = window;\nvar w: any = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["var w = self;\nvar w = self;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var w = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      // PR 923: a decoy that is not a window (0) sits beside a window initialiser under the same name. b1bae88f7 and
      // 1d9a9d631 read the name as a window only when EVERY initialiser bound one, so the decoy made it unresolved and
      // the computed write went unrefused (escapes a review found); the last initialiser to run at run time is the
      // window, so refKind now reads the name as a window when ANY initialiser binds one and refuses the write. Also a
      // name a window initialiser aliases to itself (var w = window; var w = w), which recurses to the depth cap on the
      // second initialiser but is a window through the first
      ["export {}; var frames: any = 0;\nvar frames: any = window;\n(frames as any)[[\"on\", \"message\"].join(\"\")] = function (e: MessageEvent) { void e; };"],
      ["var w = 0;\nvar w = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {}; var w: any = 0;\nvar w: any = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["var w = window;\nvar w = w;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      // PR 923: globalThis carries no lib.dom declaration, so its identity is by symbol name, not by a declaration count; a
      // .js file's computed write is its own expando declaration, and the write is seen. A count test would drop globalThis
      // out once it has any declaration and let the write through. b1bae88f7's count test accepted it.
      ["function onMsg(ev) { void ev.data; }\nglobalThis[[\"on\", \"message\"].join(\"\")] = onMsg;", "webview/probe.js"],
      // PR 923, the rule-stated window decision: rule (b) reads a name destructured from a window or a document, and a
      // local initialised to the body or to a document, in a JavaScript file too, where a top-level member write on the
      // name gives it a second, expando declaration (const { self: a } = window; a[k] = f). The multi-declaration
      // reading read only variable declarations, dropping a destructured one, and kept only window kinds, so b3eb94f8a
      // read each of these as nothing and accepted the write. declKind now reads every declaration as the
      // single-declaration case does, and the name takes the first kind in MULTI_ORDER that any of them binds. The
      // second row is a JavaScript module, whose top-level name the checker gives the expando declaration too. Last, a
      // var redeclared with the body or a document, in TypeScript
      ["const { self: a } = window;\na[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {};\nconst { self: a } = window;\na[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { parent: a } = window;\na[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let { frames: a } = window;\na[\"on\" + \"message\"] = function (e) { void e; };", "webview/probe.js"],
      ["var { self: w } = window;\nvar w = 0;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { body: b } = document;\nb[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const b = document.body;\nb[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const d = document;\nd.body[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {};\nvar b: any = document.body;\nvar b: any = document.body;\nb[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["export {};\nvar d: any = document;\nvar d: any = document;\nd.body[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      // PR 923: a key rule (b) reads, written as a literal in brackets, a template with no substitution, or under
      // parentheses, a cast, satisfies or a non-null mark, in a destructuring pattern or an element access, and an
      // index key in a pattern: keyKind reads each as the plain key (const { ["self"]: a } = window is window.self;
      // const { 0: w } = window, a frame's window). 31b90f0f9 read a pattern's key in brackets and an element access's
      // key under a parenthesis or a cast as nothing, and a pattern's index key by name, so the computed write went
      // unrefused
      ["const { [\"self\"]: a } = window;\na[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {};\nconst { [\"self\"]: w } = window as any; (w as any)[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["export {};\nconst { [\"parent\"]: w } = window as any; (w as any)[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["export {};\nconst { [\"self\"]: { [\"self\"]: w } } = window as any; (w as any)[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["const { [`self`]: a } = window;\na[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { [(\"self\")]: a } = window;\na[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { [\"defaultView\"]: v } = document;\nv[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { document: { [\"defaultView\"]: v } } = window;\nv[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { [\"body\"]: b } = document;\nb[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const a = window[(\"self\")];\na[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {};\n(window as any)[(\"self\")][[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["const v = document[(\"defaultView\")];\nv[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {};\nconst f = (): void => {};\n((window as any)[\"self\" as string] as Record<string, unknown>)[[\"on\", \"message\"].join(\"\")] = f;"],
      ["export {};\nconst f = (): void => {};\n((window as any)[\"self\"!] as Record<string, unknown>)[[\"on\", \"message\"].join(\"\")] = f;"],
      ["export {};\nconst f = (): void => {};\n((window as any)[\"self\" satisfies string] as Record<string, unknown>)[[\"on\", \"message\"].join(\"\")] = f;"],
      ["export {};\nconst f = (): void => {};\n((window as any)[<string>\"self\"] as Record<string, unknown>)[[\"on\", \"message\"].join(\"\")] = f;"],
      ["const { 0: w } = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { \"0\": w } = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { [0]: w } = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { 0n: w } = window;\nw[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      // PR 923: a window put under a property named ownerDocument or contentDocument, on a base the census resolves to
      // nothing (an object literal, an unknown local), is read as a document the census cannot tell is this page's
      // (memberKind reads the name whatever the base). A computed member on it now refuses fail-closed, as on a window,
      // the body element or a prototype: an ordinary object holds the window under that name, so at run time the receiver
      // is the window and the write lands window.onmessage. 84eba73c6 read otherDocument as safe (holdsWindowMethods
      // false) and accepted the write. Reached by a member (o.contentDocument), an element access (o["contentDocument"]),
      // a one-hop chain, and a destructuring key (patternKind), in TypeScript and JavaScript, for onmessage and
      // onmessageerror
      ["const o: any = { contentDocument: window }; o.contentDocument[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; }; export {};"],
      ["var o = { ownerDocument: window }; o.ownerDocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const o: any = { contentDocument: window }; o[\"contentDocument\"][[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; }; export {};"],
      ["const o: any = { ownerDocument: window }; o.ownerDocument[[\"on\", \"messageerror\"].join(\"\")] = function (e: unknown) { void e; }; export {};"],
      ["const o: any = { contentDocument: window }; const x: any = o.contentDocument; x[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; }; export {};"],
      ["const { contentDocument: x } = { contentDocument: window } as any; x[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; }; export {};"],
      ["const { ownerDocument } = { ownerDocument: window } as any; ownerDocument[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; }; export {};"],
      ["var { contentDocument: x } = { contentDocument: window }; x[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["const { a: { contentDocument: x } } = { a: { contentDocument: window } } as any; x[[\"on\", \"messageerror\"].join(\"\")] = function (e: unknown) { void e; }; export {};"],
      // PR 923: a binding the window rule does not decide by its initialiser, whose initialiser names this page's
      // document: a parameter a var redeclares, the write running before the var's initialiser while x still holds the
      // argument (function h(x) { x[k] = f; var x = document } h(window)), in TypeScript and JavaScript; a var or let
      // written after its initialiser (an assignment, through Reflect.set too; a closure's assignment; an array
      // pattern; a for...of head; a shorthand pattern target; a logical assignment); a var of a classic script's
      // top-level scope that a call sets through the global object, before the initialiser runs or after it; a
      // namespace's export set through the namespace object; and a name declared twice, as this page's document and as
      // a document the census cannot tell is this page's. 984f56d6e read each through its initialiser as this page's
      // document, which it trusts with a computed member, and accepted the write; at run time the receiver is the
      // window (the classic-script rows when the file runs as one, which esbuild's bundle does not do). The rule now
      // decides a binding by its initialiser only where that initialiser is its value at every use (initIsValue) and
      // reads any other fail-closed, this page's document as a document the census cannot tell is this page's
      ["export {};\nfunction h(x: any) { x[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; }; var x: any = document; }\nh(window);"],
      ["function h(x) { x[[\"on\", \"message\"].join(\"\")] = function (e) { void e; }; var x = document; }\nh(window);", "webview/probe.js"],
      ["var x: any = document; x = window; Reflect.set(x, [\"on\", \"message\"].join(\"\"), function (e: unknown) { void e; }); export {};"],
      ["var x = document; x = window; x[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let d = document; function g() { d = window; } g(); d[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let d = document; [d] = [window]; d[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let d = document; for (d of [window]) {} d[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let { document: d } = window; ({ d } = { d: window }); d[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let d = document; d &&= window; d[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["Reflect.set(window, \"x\", window); x[[\"on\", \"message\"].join(\"\")] = function (e) { void e; }; var x = document;", "webview/probe.js"],
      ["var x = document; Object.assign(window, { x: window }); x[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["namespace N { export var d: any = document; export function g() { d[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; }; } }\n(N as any).d = window;\nN.g();"],
      ["var o = { contentDocument: window };\nvar d = document;\nvar d = o.contentDocument;\nd[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["export {};\nconst o: any = { ownerDocument: window };\nvar d: any = document;\nvar d: any = o.ownerDocument;\nd[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      // PR 923: this page's window read fail-closed, from a binding the rule does not decide (written after its
      // initialiser, or declared twice) or from a plain function's `this`, which a call can give another value (o.m()):
      // its document is one the census cannot tell is this page's, since the value can be an object that holds the
      // window under that name. 984f56d6e read it as this page's own window, whose document it trusts, and accepted the
      // computed write on that document; at run time the write lands on the window
      ["var w = window; w = { document: window }; w.document[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["function g() { var w = window; var w = { document: window }; var d = w.document; d[[\"on\", \"message\"].join(\"\")] = function (e) { void e; }; } g();", "webview/probe.js"],
      ["function m() { this.document[[\"on\", \"message\"].join(\"\")] = function (e) { void e; }; }\nvar o = { document: window, m: m };\no.m();", "webview/probe.js"],
      // PR 923: a write to a binding the rule decided by its document initialiser, spelled so the language service's
      // isWriteAccess lists it as a read: a cast, an angle-bracket cast, satisfies or a non-null mark around the target
      // ((d as any) = window, (<any>d) = window, (d satisfies any) = window, d! = window), which esbuild erases, so d
      // is the window when the computed write runs and it lands window.onmessage; the same through a destructuring
      // target, a for...of head, a logical assignment, a closure and a type argument; an array pattern under a cast,
      // ([d] as any) = [window], which esbuild refuses to build (an invalid assignment target) and writesBinding counts
      // as a write all the same, fail-closed; and ++ and a rest element's target (which make the binding a number, an
      // array or a plain object, no window, but are writes all the same). ab6a0585a read each through its initialiser
      // as this page's document and accepted the write; writesBinding now reads the target through what esbuild
      // erases, and the binding is one the rule does not decide
      ["let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d as any) = window;\n(d as any)[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(<any>d) = window;\n(d as any)[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d satisfies any) = window;\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d as unknown) = window;\n(d as any)[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d = document;\nconst k = [\"on\", \"messageerror\"].join(\"\");\n(d as any) = window;\n(d as any)[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d as any) = window;\n(d as any)[k] = function (e: unknown) { void e; };"],
      ["let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d as any) = window;\nReflect.set(d, k, function (e: unknown) { void e; });\nexport {};"],
      ["var d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\nd! = window;\n(d as any)[k] = function (e: unknown) { void e; };\nexport {};"],
      ["var d: Document = document;\nconst k = [\"on\", \"message\"].join(\"\");\nd! = window as any;\n(d as any)[k] = function (e: unknown) { void e; };\nexport {};"],
      ["var d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d!) = window;\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["var d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\nd!! = window;\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n[(d as any)] = [window];\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n({ x: d! } = { x: window });\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\nfor ((d as any) of [window]) {}\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d as any) ||= window;\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\nconst g = () => { (d as any) = window; }; g();\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n([d] as any) = [window];\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d<any>) = window;\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d: any = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d as any)++;\nd[k] = function (e: unknown) { void e; };\nexport {};"],
      ["let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n[...d] = [window];\nd[k] = function (e) { void e; };", "webview/probe.js"],
      ["let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n({ ...d } = window);\nd[k] = function (e) { void e; };", "webview/probe.js"],
      // PR 923: the file's own this, which ab6a0585a read as this page's window, whose document it trusts: in a page
      // bundle esbuild rewrites it to the file's exports object, wrapping the file as CommonJS, where the file has no ES
      // export statement (an export of a type or an interface is one; TypeScript's export = is CommonJS, and a file
      // whose export is one is wrapped), no import.meta and no .mjs or .mts suffix, whether or not it imports (the last
      // row imports and has no export), so this.document can hold the window and the computed write lands
      // window.onmessage; in any other file it is undefined and the code throws (the page build, target es2020, refuses
      // a top-level await). The rule now reads every this rule (c)
      // reads as the global object fail-closed, its document one the census cannot tell is this page's
      ["var k = [\"on\", \"message\"].join(\"\"); function h(e) { void e; }\nthis.document = window; this.document[k] = h;", "webview/probe.js"],
      ["var k = [\"on\", \"message\"].join(\"\"); function h(e) { void e; }\nthis.document = window; this.document[k] = h;", "webview/probe.cjs"],
      ["var k = [\"on\", \"message\"].join(\"\"); function h(e: unknown) { void e; }\nthis.document = window; this.document[k] = h;"],
      ["var k = [\"on\", \"message\"].join(\"\"); function h(e) { void e; }\nthis.document = window; const d = this.document; d[k] = h;", "webview/probe.js"],
      ["var k = [\"on\", \"message\"].join(\"\"); function h(e) { void e; }\n(() => { this.document = window; this.document[k] = h; })();", "webview/probe.js"],
      ["var k = [\"on\", \"message\"].join(\"\"); function h(e) { void e; }\nexports.document = window; this.document[k] = h;", "webview/probe.js"],
      ["import \"./side\";\nvar k = [\"on\", \"message\"].join(\"\"); function h(e: unknown) { void e; }\nthis.document = window; this.document[k] = h;"],
      // PR 923: a use of document in a file that declares document at its top level, a file TypeScript calls no module.
      // The checker merges the declaration with the global document, or resolves the use past it to the global, so
      // rule (a) read the use as this page's document, whose computed member it trusts, and ea4135223 accepted every
      // row here. esbuild keeps the declaration the file's own local in the page bundle, so where the local holds the
      // window, document is the window when the computed write runs, and every row but one sets a handler on it: a
      // var, a let and a const, in JavaScript, JSX and TypeScript; for onmessage and onmessageerror; directly, through a
      // chain (const d = document), through Reflect.set, through Object.assign and through a destructuring target; with
      // self, globalThis or window.self on the right; the addEventListener method by a computed name (a message
      // listener on the window); a var in a top-level block, a var written later, a use in a function, and a window's
      // own member (document.self). The row with a function declaration of the name sets no handler: esbuild keeps the
      // function, and the write sets a member of it, so that row is held as a fail-closed reading, not as a road that
      // lands. Identity now decides no use of the declared name in such a file: the rule reads it fail-closed, as the
      // first, in the order this page's window, another window, the body element, a document the census cannot tell is
      // this page's, among the global's kind and the kinds the file's declarations of the name bind. A declaration that
      // binds this page's window makes the use that window read fail-closed (a window's own member, self or parent, is
      // read too), and declarations that bind none of these kinds (the function declaration, and var document; written
      // later by document = window) leave the global's kind, a document the census cannot tell is this page's; each
      // refuses a computed member
      ["var document = window;\ndocument[[\"on\",\"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = window;\nconst d = document;\nd[[\"on\",\"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = window;\nReflect.set(document, [\"on\",\"message\"].join(\"\"), function (e) { void e; });", "webview/probe.js"],
      ["var document = window;\ndocument[[\"on\",\"messageerror\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let document = window;\ndocument[[\"on\",\"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = window;\ndocument[[\"on\",\"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.jsx"],
      ["var document = window;\ndocument[\"on\" + \"message\"] = function (e) { void e; };", "webview/probe.js"],
      ["var document: Document = window as any;\n(document as any)[\"on\" + \"message\"] = function (e: any) { void e; };"],
      ["var document = window;\nObject.assign(document, { [\"on\" + \"message\"]: function (e) { void e; } });", "webview/probe.js"],
      ["var document = window;\nvar kk = \"on\" + \"message\";\n({ p: document[kk] } = { p: function (e) { void e; } });", "webview/probe.js"],
      ["const document = window;\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = self;\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = globalThis;\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = window.self;\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let document: any = window;\ndocument[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["const document: any = window;\ndocument[[\"on\", \"message\"].join(\"\")] = function (e: unknown) { void e; };"],
      ["var document = window;\ndocument[[\"add\", \"Event\", \"Listener\"].join(\"\")](\"message\", function (e) { void e; });", "webview/probe.js"],
      ["function document() {}\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["{ var document = window; }\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document;\ndocument = window;\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = window;\nfunction g() { document[[\"on\", \"message\"].join(\"\")] = function (e) { void e; }; }\ng();", "webview/probe.js"],
      ["var document = window;\ndocument.self[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      // PR 923: this page's document in a binding the rule leaves undecided although no code writes it: the language
      // service's isWriteAccess reads a shorthand property naming it and an export specifier as writes, and identAt does
      // not look inside a JSDoc comment, where the service lists a reference; each is read fail-closed, as the rule's
      // clause (b) says, and a computed member of it refuses
      ["const d = document;\nconst o = { d }; go(o);\nd[k] = f;"],
      ["const d = document;\nexport { d };\nd[k] = f;"],
      ["const d = document;\n/** @type {typeof d} */\nvar x = null; void x;\nd[k] = f;", "webview/probe.js"],
    ]],
    // a window-name global the source augmented with a declaration outside the default lib (an expando, a `declare
    // global`): the census resolves the name to the window by IDENTITY (so a computed write on it is still seen) and
    // refuses outright, because it cannot tell the augmented global is the page's own window. The declare global self row
    // also refuses for its computed name; the window.foo expando row is a plain onmessage on the own window, an accepted
    // site but for the augmentation, so the augmentation refusal is its only one
    [/has a declaration the source added outside TypeScript's default lib/, false, [
      ["window.foo = 1;\nwindow.onmessage = function (e) { void e; };", "webview/probe.js"],
      ["export {}; declare global { var self: Window & typeof globalThis; } const k = \"on\" + \"message\"; (self as any)[k] = function (e: unknown) { void e; };"],
    ]],
    // PR 923: a file TypeScript calls no module that declares a window name or document at its top level, with a
    // declaration that is not ambient, is refused outright (topShadow). In the page bundle a use of the name in that
    // file holds the file's own local where esbuild keeps the declaration, and the raw global where esbuild drops it as
    // dead code. The release build drops a var in if (false) at a file's top level, so the first two rows set the
    // window's handler through the raw document's body and its defaultView. Only this refusal refuses the first: the
    // rule's fail-closed reading of the declaration (this page's window, which has no body) reads document.body as
    // nothing. The second is refused by the member rule as well, since a defaultView on any holder but this page's
    // document is read as another window, whose computed member refuses. The rest: the kept declaration's body
    // (undefined on the window, so that write throws), a class of the name, a declaration of top, self or frames that
    // nothing uses as a window, and a handler on a document the declaration makes the window (a census site as well)
    [/a file that is no module declares (window|self|globalThis|frames|top|parent|opener|document) at its top level/, false, [
      ["if (false) { var document = window; }\ndocument.body[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["if (false) { var document = window; }\ndocument.defaultView[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["var document = window;\ndocument.body[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["class document {}\ndocument[[\"on\", \"message\"].join(\"\")] = function (e) { void e; };", "webview/probe.js"],
      ["let top = 0;\nvoid top;", "webview/probe.js"],
      ["function self() {}\nvoid self;"],
      ["const frames: number[] = [];\nvoid frames;"],
      ["var document = window;\ndocument.onmessage = function (e) { void e; };", "webview/probe.js"],
    ]],
    // a module whose code no census reads: one imported from a URL built at run time, from a data: URL, or a test or types
    // file, and (below) one named by a specifier esbuild rewrites or reached by a require() of a computed specifier
    [/an import\(\) whose specifier is not a string literal/, false, [
      ["import(\"data:text/javascript,\" + encodeURIComponent(code));"], ["import(URL.createObjectURL(new Blob([code], { type: \"text/javascript\" })));"],
      ["const u = \"data:text/javascript,go()\"; import(u);"], ["import(`data:text/javascript,${code}`);"], ["(async () => { await import((spec)); })();"],
    ]],
    [/a module specifier that is a data: URL/, false, [
      ["import(\"data:text/javascript,window.onmessage%3Df\");"], ["import(`data:text/javascript,go()`);"], ["import(\"DATA:text/javascript,go()\");"],
      ["import \"data:text/javascript,window.onmessage=f\";"], ["import { a } from \"data:text/javascript,export const a = 1\";"],
      ["export * from \"data:text/javascript,export const a = 1\";"], ["import x = require(\"data:text/javascript,go()\");"],
      ["require(\"data:text/javascript,window.onmessage=f\");", "webview/probe.js"],
    ]],
    [/a module specifier naming a test or types file/, false, [
      ["import \"./zz.d\";"], ["import { X } from \"./zz.d.ts\";"], ["export { X } from \"./zz.d.mts\";"], ["import { type X, Y } from \"./zz.d.cts\";"],
      ["import \"./zz.test\";"], ["import(\"./zz.test.js\");"], ["import \"./zz.d.js\";"], ["import x = require(\"./zz.d\");"],
      ["require(\"./zz.test.ts\");", "webview/probe.js"],
    ]],
    // a specifier esbuild rewrites before it resolves: a query or a hash stripped, a trailing / or /. normalized
    [/a module specifier holding a \? or a #, or ending in \/ or \/\., which esbuild strips or normalizes before it resolves/, false, [
      ["import \"./zz?x\";"], ["import \"./zz#x\";"], ["import \"./zz/\";"], ["import \"./zz/.\";"], ["import \"./zz.test.ts?v=1\";"],
      ["export * from \"./zz?x\";"], ["const m = require(\"./zz#x\");", "webview/probe.js"], ["import(\"./zz/\");"], ["import \"./zz.test/\";"],
      ["import { X } from \"./zz.d.ts?x\";"],
    ]],
    // a require() of a specifier that is no string literal, which esbuild bundles as every file its pattern can match
    [/a require\(\) whose specifier is not a string literal/, false, [
      ["declare const x: string; require(\"./d/\" + x);"], ["declare const x: string; require(`./d/${x}`);"],
      ["declare const x: string; (require)(\"./d/\" + x);"], ["require(\"./d/\" + x);", "webview/probe.js"],
      ["require(\"./d/a\" + \".test.ts\");", "webview/probe.js"],
    ]],
    // a timer, read on any receiver or behind a comma, handed a string or an array or object literal, or used as a tag
    [/(setTimeout|setInterval) (handed a string|as a template's tag)/, false, [
      ["const w = window; w.setTimeout(\"go()\", 0);"], ["document.defaultView.setTimeout(\"go()\", 0);"], ["frames.setTimeout(\"go()\", 0);"],
      ["(0, setTimeout)(\"go()\", 0);"], ["w.setTimeout(\"go()\", 0);", "webview/probe.js"], ["(0, setTimeout)(\"go()\");", "webview/probe.js"],
      ["req.setInterval(`go()`);", "webview/probe.js"], ["d[\"setTimeout\"](\"go()\");", "webview/probe.js"],
      ["(0, window.setTimeout)(\"go()\");", "webview/probe.js"],
      ["setTimeout([\"go()\"]);", "webview/probe.js"], ["setTimeout({ toString() { return \"go()\"; } });", "webview/probe.js"],
      ["setTimeout`go()`;", "webview/probe.js"], ["window.setTimeout`go()`;", "webview/probe.js"],
    ]],
    // a messageerror handler set another way
    [/an onmessageerror handler set some way other than an assignment the census reads/, false, [
      ["Object.assign(window, { onmessageerror: f });"], ["Reflect.set(window, \"onmessageerror\", f);"], ["window.onmessageerror ??= f;"],
    ]],
  ];
  for (const [why, noSite, rows] of byReason) {
    for (const [src, file] of rows) {
      const got = roads(src, file);
      if (!got.some((w) => why.test(w))) missed.push("not refused for " + why + ": " + src + " (refused for: " + JSON.stringify(got) + ")");
      if (noSite && sitesIn(file || "webview/probe.ts", src).some((x) => x.kind === "onmessage")) missed.push("an onmessage site: " + src);
    }
  }
  // a refusal on a receiver the census cannot prove a socket names the site: the clause that refused it, and where, one
  // row per message socketRefusal gives (a reference in another file, which only the census's program can hold, and a
  // reference the checker resolves to the declaration that the language service does not list, each have a test of
  // their own below)
  const UNPROVED = "an onmessage handler on a receiver the census cannot resolve to this page's window or to a socket: ";
  const named: Array<[string, string, string?]> = [
    // clause 0: a syntax error, a binder error, a function declared in a block, in a script, in a .cjs file and in a
    // TypeScript module whose only module syntax is import x = require(...)
    ["let ws: WebSocket =\n  new WebSocket(u);\nws.onmessage = f;", "the file does not parse as TypeScript reads it (Type annotations can only be used in TypeScript files., at :1)", "webview/probe.js"],
    ["var ws = new WebSocket(u);\nclass ws {}\nws.onmessage = f;", "TypeScript's binder reports an error at :1 (Duplicate identifier 'ws'.), where its scopes are not the page's", "webview/probe.js"],
    ["let ws = new WebSocket(u);\nfunction g() { { ws = window; function ws() {} } ws.onmessage = f; }\ng();", "a function ws is declared in a block at :2, not at a file's top level, in a module body or directly in a function body, where the proof refuses it in every file (a plain one a sloppy-mode file hoists into its enclosing function past the checker's block scope; an async or generator one by its position alone, Annex B not hoisting it)", "webview/probe.js"],
    ["{\n  function window() {}\n}\nconst ws = new window.WebSocket(u);\nws.onmessage = f;", "a function window is declared in a block at :2, not at a file's top level, in a module body or directly in a function body, where the proof refuses it in every file (a plain one a sloppy-mode file hoists into its enclosing function past the checker's block scope; an async or generator one by its position alone, Annex B not hoisting it)", "webview/probe.cjs"],
    ["import y = require(\"./y\");\nlet ws: any = new WebSocket(u);\nfunction h() { if (1) function ws() {} ws = window; }\nh(); ws.onmessage = f;", "a function ws is declared in a block at :3, not at a file's top level, in a module body or directly in a function body, where the proof refuses it in every file (a plain one a sloppy-mode file hoists into its enclosing function past the checker's block scope; an async or generator one by its position alone, Annex B not hoisting it)"],
    // clause 1: no symbol, no declaration, two declarations, a declaration that is no let, const or var statement's own
    // (a for head's, a catch clause's parameter), an ambient one, a namespace's export
    ["ws.onmessage = f;", "ws at :1 resolves to no symbol"],
    ["\nws.onmessage = f;", "ws at :2 resolves to no declaration", "webview/probe.js"],
    ["var ws = new WebSocket(u);\nvar ws;\nws.onmessage = f;", "ws has 2 declarations (:1, :2), and the proof takes one", "webview/probe.js"],
    ["function g(ws) {\n  ws.onmessage = f;\n  var ws = new WebSocket(u);\n}", "ws has 2 declarations (:1, :3), and the proof takes one", "webview/probe.js"],
    ["\nfor (let ws = new WebSocket(u); ; ) {\n  ws.onmessage = f; break;\n}", "ws is not declared by a let, const or var statement of its own (:2)", "webview/probe.js"],
    ["try { throw window; }\ncatch (ws) { if (0) ws = new WebSocket(u); ws.onmessage = f; }", "ws is not declared by a let, const or var statement of its own (:2)", "webview/probe.js"],
    ["\ndeclare var ws: any;\nif (0) ws = new WebSocket(u); ws.onmessage = f;", "ws is declared at :2 by an ambient declaration (declare), which binds nothing at run time"],
    ["namespace N {\n  export var ws: any = new WebSocket(u);\n  export function arm() { ws.onmessage = f; }\n}", "ws is declared at :2 as a namespace's export, which is a property of the namespace object"],
    // clauses 2 and 4, shape A: an initialiser that is no new WebSocket(...), one whose WebSocket or window is not the
    // built-in, a script's top-level WebSocket, and a write beside the initialiser
    ["\nlet ws = pick();\nws.onmessage = f;", "ws is declared at :2 bound to something other than new WebSocket(...)", "webview/probe.js"],
    ["function g(WebSocket: any) {\n  const ws =\n    new WebSocket(u);\n  ws.onmessage = f;\n}", "ws is declared at :2 bound to new WebSocket(...) whose WebSocket at :3 the checker resolves to no library global (its declarations outside the default lib and @types)"],
    ["import { window } from \"./m\";\nconst ws =\n  new window.WebSocket(u);\nws.onmessage = f;", "ws is declared at :2 bound to new window.WebSocket(...) whose window at :3 has a declaration outside the default lib and @types"],
    ["class WebSocket { constructor() { return window; } }\nconst ws = new WebSocket(u);\nws.onmessage = f;", "ws is declared at :2 bound to new WebSocket(...) in a file that is no module and declares WebSocket at its top level, which the checker can resolve past to the built-in"],
    ["let ws = new WebSocket(u);\nws = window;\nws.onmessage = f;", "ws is written at :2, and its declaration at :1 binds it already", "webview/probe.js"],
    // shape B: never bound, two writes, a write that is no statement of its own, one of something else, one outside the
    // try, a read before the write
    ["let ws;\nws.onmessage = f;", "ws is never bound to new WebSocket(...)", "webview/probe.js"],
    ["let ws;\nws = new WebSocket(u);\nws = new WebSocket(u2);\nws.onmessage = f;", "ws is written at :2, :3, and a declaration with no initialiser takes one write", "webview/probe.js"],
    ["let ws;\ngo(ws = new WebSocket(u));\nws.onmessage = f;", "ws is written at :2 by something other than a statement of its own assigning new WebSocket(...)", "webview/probe.js"],
    ["let ws;\nws = window;\nws.onmessage = f;", "ws is written at :2 with something other than new WebSocket(...)", "webview/probe.js"],
    // a write to the socket's name under a cast or a non-null mark, which the language service lists as a read and
    // esbuild erases (writesBinding): ab6a0585a counted each as a read and proved the socket, the window at run time
    ["let ws = new WebSocket(u);\n(ws as any) = window;\nws.onmessage = f;", "ws is written at :2, and its declaration at :1 binds it already"],
    ["let ws: any = new WebSocket(u);\nws! = window;\nws.onmessage = f;", "ws is written at :2, and its declaration at :1 binds it already"],
    ["let ws: any = new WebSocket(u);\n[(ws as any)] = [window];\nws.onmessage = f;", "ws is written at :2, and its declaration at :1 binds it already"],
    ["let ws: any = new WebSocket(u);\nfor ((ws as any) of [window]) {}\nws.onmessage = f;", "ws is written at :2, and its declaration at :1 binds it already"],
    ["function c(u: string) {\n  let ws: any;\n  try { ws = new WebSocket(u); } catch (e) { return; }\n  (ws as any) = window;\n  ws.onmessage = f;\n}", "ws is written at :3, :4, and a declaration with no initialiser takes one write"],
    ["function c(u) {\n  let ws;\n  ws = new WebSocket(u);\n  ws.onmessage = f;\n}", "ws is written at :3 elsewhere than in the try block of a try beside its declaration and after it, whose catch ends in a return and which has no finally", "webview/probe.js"],
    ["function c(u) {\n  let ws;\n  ws.onmessage = f;\n  try { ws = new WebSocket(u); } catch (e) { return; }\n}", "ws is read at :3, which can run before its one write at :4", "webview/probe.js"],
    // clause 3: a name the checker resolves to no symbol, and a reference that is no identifier of the name
    ["let ws = new WebSocket(u);\nimport w2 = ws;\nws.onmessage = f;", "ws at :2 resolves to no symbol, which the proof cannot tell from its declaration's"],
    ["var ws = new WebSocket(u);\nwindow[\"ws\"] = window;\nws.onmessage = f;", "ws has a reference at :2 that is no identifier ws (a rename, a string key, or a reference inside a JSDoc comment), which the proof does not read", "webview/probe.js"],
    ["export {};\nlet ws = new WebSocket(u);\n/** {@link ws} */\nfunction g() {}\ng();\nws.onmessage = f;", "ws has a reference at :3 that is no identifier ws (a rename, a string key, or a reference inside a JSDoc comment), which the proof does not read"],
    // the language service's isWriteAccess reads a shorthand property naming the socket, and an export specifier, as a
    // write, and the proof refuses either as one
    ["let ws = new WebSocket(u);\ngo({ ws });\nws.onmessage = f;", "ws is written at :2, and its declaration at :1 binds it already"],
    ["let ws = new WebSocket(u);\nexport { ws };\nws.onmessage = f;", "ws is written at :2, and its declaration at :1 binds it already"],
    ["document.body.onmessage = f;", "the receiver is not a name"],
  ];
  for (const [src, want, file] of named) {
    const got = roads(src, file);
    if (!got.includes(UNPROVED + want)) missed.push("not refused naming the site (" + want + "): " + JSON.stringify(src) + " (refused for: " + JSON.stringify(got) + ")");
  }
  assert.deepEqual(missed, [], "a handler the census accepts refused, a road not refused for its reason, a refused handler that is a census site, or a refusal on an unproved socket that does not name its site:\n" + missed.join("\n"));
});

test("the socket proof's program fails loudly: TypeScript that cannot be loaded, or an error in a file the census reads, stops the census with a message of its own", () => {
  // TypeScript unavailable: a module name no node_modules holds, through the extension's own require, and a module
  // without the language service
  assert.throws(() => loadTypeScript(requireCjs, "typescript-not-installed-" + crypto.randomUUID()),
    /^Error: the census cannot load TypeScript \(typescript-not-installed-[0-9a-f-]+ from vscode-extension's node_modules: Cannot find module .*\), and it has no fallback without it/);
  assert.throws(() => loadTypeScript(() => ({ version: "0" })),
    /^Error: the census loaded typescript but it has no language service \(createLanguageService, createDocumentRegistry\), which the socket proof reads/);
  // an error in a file the census reads, planted as the census's own files (a type error, and a module that does not
  // parse), named with its file and line; a clean plant builds
  assert.throws(() => censusProgram([["webview/zz-plant-clean.ts", "export const n: number = 1;\n"], ["webview/zz-plant-type-error.ts", "export const m = 1;\nexport const n: number = \"s\";\n"]]),
    (e: Error) => /^the socket proof's program \(the census's files, under vscode-extension\/tsconfig.json's options\) has errors in the files the census reads, and the census reads no program with errors:\nwebview\/zz-plant-type-error.ts:2: TS2322 Type 'string' is not assignable to type 'number'.$/.test(e.message));
  assert.throws(() => censusProgram([["webview/zz-plant-syntax.js", "var x = ;\n"]]), (e: Error) => /\nwebview\/zz-plant-syntax.js:1: TS1109 Expression expected.$/.test(e.message));
  const clean = censusProgram([["webview/zz-plant-clean.ts", "export const ws = new WebSocket(\"ws://x\");\nws.onmessage = () => {};\n"]]);
  assert.equal(clean("webview/zz-plant-clean.ts").sf.text, "export const ws = new WebSocket(\"ws://x\");\nws.onmessage = () => {};\n");
});

test("the socket proof in the census's program refuses a socket with a reference in another file, and accepts the same socket read only in its own", () => {
  // clause 3's other-file refusal: only a program of more than one file can hold such a reference, so it is planted as
  // the census's own files (typed, so the program has no error) and read with the census's program
  const own = "export const ws = new WebSocket(\"ws://x\");\nws.onmessage = () => {};\n";
  const other = "import { ws } from \"./zz-plant-socket\";\nexport const state = ws.readyState;\n";
  const both = censusProgram([["webview/zz-plant-socket.ts", own], ["webview/zz-plant-reader.ts", other]]);
  assert.deepEqual(looseRoads("webview/zz-plant-socket.ts", own, () => both("webview/zz-plant-socket.ts")).loose.map((l) => l.why),
    ["an onmessage handler on a receiver the census cannot resolve to this page's window or to a socket: ws has a reference in another file (webview/zz-plant-reader.ts)"]);
  const alone = censusProgram([["webview/zz-plant-socket.ts", own]]);
  assert.deepEqual(looseRoads("webview/zz-plant-socket.ts", own, () => alone("webview/zz-plant-socket.ts")).loose, []);
});

test("the socket proof refuses a reference the checker resolves to the declaration that the language service does not list", () => {
  // clause 3's agreement: the two read the same checker, so on every real file they agree; a service that lists no
  // reference stands for one that parts from the checker, and the proof refuses rather than read the writes it lists
  const src = "const ws = new WebSocket(u);\nws.onmessage = f;";
  const c = fixtureChecked("webview/probe.ts", src);
  assert.deepEqual(looseRoads("webview/probe.ts", src, () => c).loose, [], "the real service lists the reference, and the socket is proved");
  const silent = { ...c, service: { findReferences: () => [] } };
  assert.deepEqual(looseRoads("webview/probe.ts", src, () => silent).loose.map((l) => l.why),
    ["an onmessage handler on a receiver the census cannot resolve to this page's window or to a socket: ws at :2 is its declaration's symbol to the checker and no reference to the language service"]);
});

test("the window rule decides a binding by its initialiser only where the language service lists every reference in the declaring file that the checker resolves to it, and no reference writes it: a reference it does not list, a listed reference that is no identifier of the name, or a write, in this file or another, the service's or writesBinding's, leaves this page's document to the fail-closed reading", () => {
  // initIsValue's agreement, as the socket proof's: the two read the same checker, so on every real file they agree; a
  // service that lists no reference stands for one that parts from the checker, and the rule reads the binding
  // fail-closed rather than trust the writes it lists. The walk that must agree reads the declaring file; a reference
  // in another file is the service's alone. With the real service the binding is decided, this page's document, whose
  // computed member the census leaves; a write anywhere but the initialiser (here in a closure the service finds) makes
  // it one the rule does not decide
  const COMPUTED_WHY = "a member of a window, a document the census cannot tell is this page's, the body element or a prototype reached by a computed name, which the censuses cannot read";
  const src = "const d = document;\nd[k] = f;";
  const c = fixtureChecked("webview/probe.ts", src);
  assert.deepEqual(looseRoads("webview/probe.ts", src, () => c).loose, [], "the real service lists the reference, and d is this page's document");
  const silent = { ...c, service: { findReferences: () => [] } };
  assert.deepEqual(looseRoads("webview/probe.ts", src, () => silent).loose.map((l) => l.why), [COMPUTED_WHY]);
  // a listed reference that is no identifier of the name (here the service's list plus one at the f of `= f`): the rule
  // does not read what it cannot find, and leaves the binding undecided
  const stray = { ...c, service: { findReferences: (file: string, at: number) => c.service.findReferences(file, at).map((r: any) => ({
    ...r, references: [...r.references, { fileName: file, textSpan: { start: src.lastIndexOf("f"), length: 1 }, isWriteAccess: false }] })) } };
  assert.deepEqual(looseRoads("webview/probe.ts", src, () => stray).loose.map((l) => l.why), [COMPUTED_WHY]);
  const written = "let d = document;\nconst g = () => { d = window; };\nd[k] = f;";
  assert.deepEqual(looseRoads("webview/probe.ts", written).loose.map((l) => l.why), [COMPUTED_WHY]);
  // a write under a cast, which the service lists as a read (its isWriteAccess false) and esbuild erases: writesBinding
  // reads it as the write it is (ab6a0585a accepted it as this page's document)
  const cast = "let d = document;\n(d as any) = window;\n(d as any)[k] = f;";
  const cc = fixtureChecked("webview/probe-cast.ts", cast);
  const castRefs = cc.service.findReferences(cc.sf.fileName, cast.indexOf("d =")).flatMap((r: any) => r.references);
  assert.deepEqual(castRefs.filter((e: any) => e.textSpan.start === cast.indexOf("(d as") + 1).map((e: any) => e.isWriteAccess), [false],
    "the service lists the write under the cast as a read");
  assert.deepEqual(looseRoads("webview/probe-cast.ts", cast, () => cc).loose.map((l) => l.why), [COMPUTED_WHY]);
  // a write under a cast in another file, a classic script that shares the declaring script's top-level let: the
  // service lists it, and it is read at its identifier there. Alone, the declaring file's binding is decided
  const own = "let d = document;\nconst k = [\"on\", \"message\"].join(\"\");\n(d as any)[k] = function (e: unknown) { void e; };\n";
  const other = "(d as any) = window;\n";
  const both = censusProgram([["webview/zz-plant-d.ts", own], ["webview/zz-plant-w.ts", other]]);
  assert.deepEqual(looseRoads("webview/zz-plant-d.ts", own, () => both("webview/zz-plant-d.ts")).loose.map((l) => l.why), [COMPUTED_WHY]);
  const alone = censusProgram([["webview/zz-plant-d.ts", own]]);
  assert.deepEqual(looseRoads("webview/zz-plant-d.ts", own, () => alone("webview/zz-plant-d.ts")).loose, []);
});

test("the window rule decides no use of the name by identity in a script that declares it at its top level: it reads the use fail-closed and refuses the script, while a use in another file stays the global", () => {
  // In a file TypeScript calls no module and does not bind as CommonJS, the checker merges a top-level declaration of
  // document with the global document (or resolves a use past it to the global), so identity alone would read the use
  // as this page's document; esbuild keeps the declaration the file's own local in the page bundle, the window here, so
  // the rule reads the use fail-closed (topShadow), this page's window as refKind answers it, and looseRoads refuses
  // the file. A use of
  // document in another file of the same program is the global at run time, since the declaration stays in its own
  // file, and rule (a) still decides it as this page's document: a check keyed on any file's declaration would refuse
  // it. Both files are scripts, in one census program
  const own = "var document = window;\ndocument;\n";
  const other = "const k = [\"on\", \"message\"].join(\"\");\ndocument[k] = function (e) { void e; };\ndocument;\n";
  const both = censusProgram([["webview/zz-shadow-own.js", own], ["webview/zz-shadow-other.js", other]]);
  const lastUse = (file: string, src: string): RefKind | null => {
    const lsf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kindOfUi(file));
    return refKind((lsf.statements[lsf.statements.length - 1] as any).expression, resolver(lsf, () => both(file)));
  };
  assert.equal(lastUse("webview/zz-shadow-own.js", own), "window", "a use in the declaring script is this page's window read fail-closed, not this page's document");
  assert.equal(lastUse("webview/zz-shadow-other.js", other), "document", "a use in another script is the global, this page's document");
  assert.deepEqual(looseRoads("webview/zz-shadow-other.js", other, () => both("webview/zz-shadow-other.js")).loose, [],
    "the other script's computed member of this page's document is left, as with no declaration anywhere");
  assert.deepEqual(looseRoads("webview/zz-shadow-own.js", own, () => both("webview/zz-shadow-own.js")).loose.map((l) => l.why),
    ["a file that is no module declares document at its top level (at :1), which the checker merges with the global or resolves past to it, while the page bundle keeps it the file's own local or, dropped as dead code, leaves the raw global, so the census cannot tell what the name holds"]);
});

test("writesBinding reads a reference as a write by its position, through the parentheses, casts, satisfies, non-null marks and type arguments esbuild erases and the literals a destructuring assignment writes into, and reads every other position as a read", () => {
  // each row holds one identifier d; the first half are writes (an assignment's target of any operator, ++ or --, a
  // destructuring target, a rest element's, a shorthand property's name, a for...in or for...of head, under what esbuild
  // erases; and two patterns under a cast, ({ d } as any) = o and ([d] as any) = [w], which esbuild refuses to build and
  // writesBinding counts as writes all the same, fail-closed), the second half reads (a member's base, an assignment's
  // value, a shorthand's default, a comparison's side, a unary operand, a for...of's list, a computed key, a default in
  // a pattern, an argument, a spread in a call)
  const rows: Array<[string, boolean]> = [
    ["(d as any) = w;", true], ["(<any>d) = w;", true], ["(d satisfies any) = w;", true], ["d! = w;", true], ["(d!) = w;", true],
    ["(d<any>) = w;", true], ["d += 1;", true], ["(d as any) ??= w;", true], ["d++;", true], ["--(d as any);", true],
    ["[(d as any)] = [w];", true], ["[...d] = a;", true], ["({ x: d! } = o);", true], ["({ d } as any) = o;", true], ["({ ...d } = o);", true],
    ["({ x: [d] } = o);", true], ["for ((d as any) of a) {}", true], ["for (d in o) {}", true], ["([d] as any) = [w];", true],
    ["(d as any)[k] = f;", false], ["(d as any).x = f;", false], ["x = (d as any);", false], ["go(d!);", false], ["const e = d!;", false],
    ["({ y = (d as any) } = o);", false], ["({ x: d });", false], ["[d];", false], ["go(...[d]);", false], ["for (const x of [d as any]) {}", false],
    ["(d as any) === w;", false], ["!(d as any);", false], ["typeof d;", false], ["[x = d] = a;", false], ["({ [d]: x } = o);", false], ["d.x++;", false],
  ];
  for (const [src, want] of rows) {
    const sf = ts.createSourceFile("probe.ts", src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const ids: any[] = [];
    const walk = (n: any): void => { if (ts.isIdentifier(n) && n.text === "d") ids.push(n); ts.forEachChild(n, walk); };
    walk(sf);
    assert.equal(ids.length, 1, "one d in " + src);
    assert.equal(writesBinding(ids[0]), want, (want ? "a write: " : "a read: ") + src);
  }
});

test("the socket proof refuses a constructor or a new X.WebSocket base a project .d.ts declares (B1, B2, which bd5cf71fd accepts), and a computed write on a window or on globalThis a JavaScript expando augments (the window write bd5cf71fd refuses for its computed name too, and b1bae88f7 added the augmentation refusal; the globalThis write, which b1bae88f7's declaration-count identity let through, b1bae88f7 accepted and 1d9a9d631 refuses by name identity)", () => {
  // B1: a ui/ .d.ts augments interface Window with a WebSocket member, so frames.WebSocket carries a project declaration
  // beside lib.dom's; the constructor is no library global (clause 4).
  const b1 = censusProgram([
    ["webview/zz-b1.d.ts", "interface Window { WebSocket: typeof WebSocket; }\n"],
    ["webview/zz-b1-use.ts", "export const u = \"ws://x\";\nexport const ws = new frames.WebSocket(u);\nws.onmessage = () => {};\n"],
  ]);
  assert.ok(looseRoads("webview/zz-b1-use.ts", "export const u = \"ws://x\";\nexport const ws = new frames.WebSocket(u);\nws.onmessage = () => {};\n", () => b1("webview/zz-b1-use.ts")).loose
    .some((l) => /the checker resolves to no library global/.test(l.why)), "B1: the WebSocket member is a project declaration, so no library global");
  // B2: a ui/ .d.ts declares a global `win`; new win.WebSocket reads WebSocket through it, and win's declaration is a
  // project one, no library global (clause 4's X base).
  const b2use = "export const u = \"ws://x\";\nexport const ws = new win.WebSocket(u);\nws.onmessage = () => {};\n";
  const b2 = censusProgram([
    ["webview/zz-b2.d.ts", "declare var win: Window & typeof globalThis;\n"],
    ["webview/zz-b2-use.ts", b2use],
  ]);
  assert.ok(looseRoads("webview/zz-b2-use.ts", b2use, () => b2("webview/zz-b2-use.ts")).loose
    .some((l) => /whose win at .* has a declaration outside the default lib and @types/.test(l.why)), "B2: win is a project declaration, so its .WebSocket is not the library's");
  // the window expando: a top-level window.foo = 1 in a .js file adds a JavaScript expando declaration to the global
  // window, program-wide. A .ts file's computed write on window is seen by identity (the augmented global is still the
  // window): it is refused for its computed name (bd5cf71fd, which reads window by spelling, refuses it too) and outright
  // for the augmentation. The write is refused for its computed name at bd5cf71fd and b1bae88f7 both; b1bae88f7 added the
  // augmentation refusal (with extraDecl), so it stands here unchanged.
  const expUse = "export const k = \"on\" + \"message\";\nexport const f = function (e: unknown) { void e; };\n(window as any)[k] = f;\n";
  const exp = censusProgram([
    ["webview/zz-exp.js", "window.foo = 1;\n"],
    ["webview/zz-exp-use.ts", expUse],
  ]);
  const expLoose = looseRoads("webview/zz-exp-use.ts", expUse, () => exp("webview/zz-exp-use.ts")).loose.map((l) => l.why);
  assert.ok(expLoose.some((w) => /reached by a computed name/.test(w)), "the window expando: the computed write on the augmented window is seen by identity");
  assert.ok(expLoose.some((w) => /has a declaration the source added outside TypeScript's default lib/.test(w)), "the window expando: the augmented window refuses outright");
  // the globalThis expando (PR 923): globalThis carries no lib.dom declaration, so a declaration-count identity drops it
  // out once a .js expando gives its symbol a declaration, and the .ts computed write on it passes (b1bae88f7 accepted
  // this; bd5cf71fd, which reads globalThis by spelling, refused it). Name identity holds globalThis whatever its
  // declarations: the write is refused for its computed name and the augmentation refuses outright.
  const gtUse = "export const k = \"on\" + \"message\";\nexport const f = function (e: unknown) { void e; };\n(globalThis as any)[k] = f;\n";
  const gt = censusProgram([
    ["webview/zz-gt.js", "globalThis.foo = 1;\n"],
    ["webview/zz-gt-use.ts", gtUse],
  ]);
  const gtLoose = looseRoads("webview/zz-gt-use.ts", gtUse, () => gt("webview/zz-gt-use.ts")).loose.map((l) => l.why);
  assert.ok(gtLoose.some((w) => /reached by a computed name/.test(w)), "the globalThis expando: the computed write on augmented globalThis is seen by name identity");
  assert.ok(gtLoose.some((w) => /has a declaration the source added outside TypeScript's default lib/.test(w)), "the globalThis expando: augmented globalThis refuses outright");
});

type Leg = { site: string; arm?: string };   // a leg's listener (file:line) and the arm it names, if any
/** Why the legs do not cover the listeners, one line per refusal, or none when they do. `sites` are the listeners, `arms` the
 *  declared arms (ARMS) by listener. Every listener has a leg. A listener with declared arms (two or more, distinct, declared
 *  once) has exactly one leg per declared arm, each naming it, and no other leg: none that names no arm, two that run one
 *  arm, or one that runs an arm not declared. Any other listener has exactly one leg, which names no arm. A leg or a
 *  declaration on no listener is refused too. */
function legRefusals(sites: string[], legs: Leg[], arms: Array<[string, string[]]>): string[] {
  const out: string[] = [];
  const declared = new Map<string, string[]>();
  for (const [s, a] of arms) {
    if (declared.has(s)) out.push(s + ": arms declared twice");
    if (!sites.includes(s)) out.push(s + ": arms declared for no window message listener");
    if (a.length < 2 || new Set(a).size !== a.length) out.push(s + ": the declared arms are not two or more distinct names: " + JSON.stringify(a));
    declared.set(s, a);
  }
  const by = new Map<string, Array<string | undefined>>();
  for (const l of legs) {
    if (!sites.includes(l.site)) { out.push(l.site + ": a leg on no window message listener"); continue; }
    by.set(l.site, [...(by.get(l.site) || []), l.arm]);
  }
  for (const s of sites) {
    const named = by.get(s) || [];
    if (!named.length) { out.push(s + ": a window message listener with no executed leg here"); continue; }
    const want = declared.get(s);
    if (!want) {
      if (named.length > 1) out.push(s + ": " + named.length + " legs on a listener with no declared arms (declare its arms in ARMS)");
      for (const a of named) if (a !== undefined) out.push(s + ": a leg names the arm " + JSON.stringify(a) + " of a listener with no declared arms");
      continue;
    }
    if (named.some((a) => a === undefined)) out.push(s + ": a leg of a listener with declared arms names no arm");
    for (const a of new Set(named)) if (a !== undefined && named.filter((b) => b === a).length > 1) out.push(s + ": two legs run the " + JSON.stringify(a) + " arm");
    for (const a of want) if (!named.includes(a)) out.push(s + ": no leg runs the declared arm " + JSON.stringify(a));
    for (const a of new Set(named)) if (a !== undefined && !want.includes(a)) out.push(s + ": a leg runs the arm " + JSON.stringify(a) + ", which is not declared");
  }
  return out;
}

test("census: every gated site has an executed leg in this file (installed, or lifted by its marker), and a listener declared in ARMS one per declared arm", () => {
  const key = (s: Site) => s.file + ":" + s.line;
  const legs: Leg[] = [];
  for (const leg of INSTALLED) {
    if (leg.marker) { legs.push({ site: key(siteOf(leg.site, leg.marker)) }); continue; }
    const ss = messageSites(leg.site);
    assert.equal(ss.length, 1, leg.site + " has one window message listener, or its installed leg names a marker");
    legs.push({ site: key(ss[0]) });
  }
  for (const leg of LIFTED) legs.push({ site: key(siteOf(leg.file, leg.marker)), arm: leg.arm });
  const arms = ARMS.map(([f, marker, a]) => [key(siteOf(f, marker)), a] as [string, string[]]);
  const refused = legRefusals(uiSources().flatMap((f) => messageSites(f)).map(key), legs, arms);
  assert.deepEqual(refused, [], "the executed legs do not cover the window message listeners:\n" + refused.join("\n"));
});

test("the leg census reads what it claims: a listener with no leg, a second leg or an arm on an undeclared listener, a declared arm with no leg, twice or undeclared, a leg naming no arm on a declared listener, and a bad declaration are each refused", () => {
  const A = "webview/a.ts:1", B = "webview/b.ts:2", C = "webview/c.ts:3";
  const sites = [A, B];
  const ok: Leg[] = [{ site: A }, { site: B, arm: "hostUp" }, { site: B, arm: "probe" }];
  const way: Array<[string, string[]]> = [[B, ["hostUp", "probe"]]];
  assert.deepEqual(legRefusals(sites, ok, way), [], "one leg on A, a leg per declared arm on B");
  const cases: Array<[string, Leg[], Array<[string, string[]]>, RegExp[]]> = [
    ["a listener with no leg", [ok[1], ok[2]], way, [/^webview\/a\.ts:1: a window message listener with no executed leg here$/]],
    ["a declared listener with no leg", [ok[0]], way, [/^webview\/b\.ts:2: a window message listener with no executed leg here$/]],
    ["a second leg on an undeclared listener", [...ok, { site: A }], way, [/^webview\/a\.ts:1: 2 legs on a listener with no declared arms/]],
    ["an arm named on an undeclared listener", [{ site: A, arm: "probe" }, ok[1], ok[2]], way, [/^webview\/a\.ts:1: a leg names the arm "probe" of a listener with no declared arms$/]],
    ["the hostUp leg dropped", [ok[0], ok[2]], way, [/^webview\/b\.ts:2: no leg runs the declared arm "hostUp"$/]],
    ["the probe leg dropped", [ok[0], ok[1]], way, [/^webview\/b\.ts:2: no leg runs the declared arm "probe"$/]],
    ["the probe leg names no arm", [ok[0], ok[1], { site: B }], way,
      [/^webview\/b\.ts:2: a leg of a listener with declared arms names no arm$/, /^webview\/b\.ts:2: no leg runs the declared arm "probe"$/]],
    ["both legs run hostUp", [ok[0], ok[1], ok[1]], way,
      [/^webview\/b\.ts:2: two legs run the "hostUp" arm$/, /^webview\/b\.ts:2: no leg runs the declared arm "probe"$/]],
    ["a leg runs an arm not declared", [...ok, { site: B, arm: "relay" }], way, [/^webview\/b\.ts:2: a leg runs the arm "relay", which is not declared$/]],
    ["the declaration removed", ok, [],
      [/^webview\/b\.ts:2: 2 legs on a listener with no declared arms/, /^webview\/b\.ts:2: a leg names the arm "hostUp"/, /^webview\/b\.ts:2: a leg names the arm "probe"/]],
    ["a declaration on no listener", ok, [...way, [C, ["x", "y"]]], [/^webview\/c\.ts:3: arms declared for no window message listener$/]],
    ["a listener declared twice", ok, [...way, [B, ["hostUp", "probe"]]], [/^webview\/b\.ts:2: arms declared twice$/]],
    ["one declared arm", [ok[0], ok[1]], [[B, ["hostUp"]]], [/^webview\/b\.ts:2: the declared arms are not two or more distinct names/]],
    ["a declared arm repeated", ok, [[B, ["hostUp", "probe", "probe"]]], [/^webview\/b\.ts:2: the declared arms are not two or more distinct names/]],
    ["a leg on no listener", [...ok, { site: C }], way, [/^webview\/c\.ts:3: a leg on no window message listener$/]],
  ];
  for (const [what, legs, arms, want] of cases) {
    const got = legRefusals(sites, legs, arms);
    assert.equal(got.length, want.length, what + ": " + JSON.stringify(got));
    want.forEach((re, i) => assert.match(got[i], re, what));
  }
  // the way back's scope runs only the arms the way back has
  assert.throws(() => wayBackScope(() => { /* no count */ }, undefined), /the way back has no arm undefined/);
  assert.throws(() => wayBackScope(() => { /* no count */ }, "relay"), /the way back has no arm "relay"/);
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
  // a getter read, or a value coerced by a loose or relational operator, in an early return's condition runs an arm before
  // the check: a property or element access reads nothing but the event's data (any depth: a structured clone with no
  // accessors), one level of the event's own origin, source, ports or lastEventId, or a message read (any depth), and ==,
  // !=, <, >, <=, >=, in, instanceof and a substituted template are refused (the strict === and !== stay). Every
  // listener's real pre-check still passes.
  assert.match(String(probe('(e) => { const m = e.data; if (m && m.type === "hostUp" && !kick.go) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "a getter read off a free object");
  assert.match(String(probe('(e) => { if (kick.go) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "a getter read off a free object, no message read");
  assert.match(String(probe('(e) => { const m = e.data; if (m[go()]) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "a call in an element-access index of a message read");
  assert.match(String(probe('(e) => { const m = e.data; if (m.type == kick) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "== coerces its operand");
  assert.match(String(probe('(e) => { const m = e.data; if (m.type > kick) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "a relational operator coerces its operand");
  assert.match(String(probe('(e) => { const m = e.data; if (m.type instanceof Kick) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "instanceof runs Symbol.hasInstance");
  assert.match(String(probe('(e) => { const m = e.data; if (`${kick}`) return; if (windowSender(e) === "foreign") return; }')), /runs before/, "a substituted template coerces its expression");
  // the event's target, currentTarget and srcElement are the receiving window, its view, where the event has one, is a
  // window, and a member of its source is a member of the sending window: a read through any of them can run a getter the
  // page defined
  const preCheck = (c: string) => probe("(e) => { if (" + c + ") return; if (windowSender(e) === \"foreign\") return; }");
  assert.deepEqual(["e.target.x.y", "e.currentTarget.x.y", "e.srcElement.x.y", "e.source.parent.x.y", "e.target.x", "e.source.top", "e.view",
                    "e.ports.length", "e[\"source\"][\"opener\"]", "e[k]"].filter((c) => !/runs before/.test(String(preCheck(c)))), [],
    "a read through the event beyond its own attributes, accepted ahead of the check");
  assert.deepEqual(["e.origin === \"null\"", "!e.source", "e.data && e.data.type === \"x\"", "!e.ports", "e.lastEventId === \"\"", "e[\"data\"].a.b.c",
                    "!e[\"origin\"]"].filter((c) => preCheck(c) !== null), [],
    "one level of the event's own attributes, or its data at any depth, refused ahead of the check");
  assert.equal(probe('(e) => { const m = e.data; if (!m) return; if (windowSender(e) === "foreign") return; }'), null, "the file browser's pre-check");
  assert.equal(probe('(e) => { const m = e.data; if (!m || !live) return; if (windowSender(e) === "foreign") return; }'), null, "the comments panel's pre-check reads a bare closure name");
  assert.equal(probe('(e) => { const m = e.data; if (!m || m.type !== "settingsSync" || !m.settings) return; if (windowSender(e) === "foreign") return; }'), null, "the settings sync's pre-check reads only the message");
  assert.equal(probe('(e) => { const m = e.data; if (!m || typeof m.type !== "string") return; if (windowSender(e) === "foreign") return; }'), null, "the way back's own pre-check on the data var");
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
  // a destructuring default or a computed key ahead of the check runs an expression, so one syntactic check refuses both
  // in every statement before it: in a message read's pattern, at any depth and in an array pattern, and anywhere in an
  // early return's condition (an object literal's key, a class member's). In the parameters both are refused already: the
  // one parameter is a plain name with no default. What the check leaves: a pattern with neither (a rename, a nested
  // pattern, a rest element), an element key (m[k]), and every form after the check
  const gated = (pre: string) => probe("(e) => { " + pre + " if (windowSender(e) === \"foreign\") return; go(e.data); }");
  const DEFAULT = /holds a destructuring default ahead of the foreign-sender check/, COMPUTED_KEY = /holds a computed key ahead of the foreign-sender check/;
  for (const [pre, why] of [
    ["const { a = go() } = e.data;", DEFAULT], ["const { a: { b = kick } } = e.data;", DEFAULT], ["const [a = go()] = e.data;", DEFAULT],
    ["const m = e.data, { t = 0 } = e.data;", DEFAULT], ["const { [k()]: v } = e.data;", COMPUTED_KEY], ["const { [kick]: v } = e.data;", COMPUTED_KEY],
    ["const { a: { [\"t\" + kick]: v } } = e.data;", COMPUTED_KEY], ["if ({ [kick]: 1 }) return;", COMPUTED_KEY],
    ["if (class { static [kick] = 1 }) return;", COMPUTED_KEY], ["const m = e.data; if (!m || ({ [m.k]: 1 })) return;", COMPUTED_KEY],
  ] as Array<[string, RegExp]>) assert.match(String(gated(pre)), why, pre);
  for (const pre of ["const { type: t, nested: { a } } = e.data;", "const { ...rest } = e.data;", "const m = e.data; if (!m || m[m.k]) return;", ""])
    assert.equal(gated(pre), null, "neither a default nor a computed key: " + pre);
  assert.equal(probe('(e) => { if (windowSender(e) === "foreign") return; const { a = go(), [k()]: v } = e.data; go(a, v); }'), null, "after the check, anything");
  assert.match(String(probe('({ data: { a = go() } }) => { if (windowSender(arguments[0]) === "foreign") return; }')), /names no event parameter/, "a destructured parameter");
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

test("the pane gate reads what it claims: in the shell's bundle a listener takes `if (!paneSourceOk(e)) return;` and no other gate, and no other file takes it", () => {
  const at = (file: string, text: string) => {
    const sf = ts.createSourceFile(file, "window.addEventListener(\"message\", " + text + ");", ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const call = (sf.statements[0] as any).expression;
    return headCheck({ file, line: 1, receiver: "window", fn: call.arguments[1], text, kind: "addEventListener" });
  };
  const PALETTE = "webview/palette-main.ts";
  assert.ok(PANE_GATED_FILES.has(PALETTE) && PANE_GATED_FILES.size === 1, "the palette is the one file that takes the pane gate");
  assert.equal(at(PALETTE, '(e) => { if (!paneSourceOk(e)) return; if (e.data && e.data.romp === "openKeys") keys.open(); }'), null, "the openKeys listener");
  assert.equal(at(PALETTE, '(e) => { const m = e.data; if (!m) return; if (!paneSourceOk(e)) return; go(m); }'), null, "a message read and an early return may come first");
  assert.match(String(at(PALETTE, '(e) => { if (windowSender(e) === "foreign") return; go(e.data); }')), /statement 1 is windowSender's gate, and a listener in the shell's bundle/);
  assert.match(String(at(PALETTE, '(e) => { go(e.data); if (!paneSourceOk(e)) return; }')), /statement 1 runs before the pane check/);
  assert.match(String(at(PALETTE, "(e) => { const m = e.data; }")), /no `if \(!paneSourceOk\(e\)\) return;`/);
  for (const text of ['(e) => { if (!paneSourceOk(other)) return; go(e.data); }', '(e) => { if (!paneSourceOk(e, w)) return; go(e.data); }',
                      '(e) => { if (paneSourceOk(e) === false) return; go(e.data); }', '(e) => { if (!paneSourceOk(e)) {} go(e.data); }',
                      '(e) => { if (!paneSourceOk(e)) return; else go(e.data); }'])
    assert.notEqual(at(PALETTE, text), null, "not the pane gate: " + text);
  assert.match(String(at("webview/probe.ts", '(e) => { if (!paneSourceOk(e)) return; go(e.data); }')), /statement 1 is the pane check, which only the shell's bundle/);
  assert.match(String(at("webview/gear.js", '(e) => { if (!paneSourceOk(e)) return; go(e.data); }')), /is the pane check/, "a pane's own file");
  assert.equal(at("webview/probe.ts", '(e) => { if (windowSender(e) === "foreign") return; go(e.data); }'), null, "windowSender's gate everywhere else");
});

test("the shell's bundle is loaded by the shell page alone: kernel.py's landing page loads each file of PANE_GATED_FILES as its bundle, once, and no other page or VS Code webview does", () => {
  const kernel = fs.readFileSync(KERNEL_PY, "utf8");
  const extSrc = fs.readdirSync(path.join(EXT, "src")).filter((f) => /\.ts$/.test(f) && !/\.test\.ts$/.test(f))
    .map((f) => fs.readFileSync(path.join(EXT, "src", f), "utf8")).join("\n");
  for (const file of PANE_GATED_FILES) {
    const bundle = path.basename(file).replace(/\.ts$/, ".js");
    const tag = "<script src=/dist/" + bundle;
    const at = kernel.indexOf(tag);
    assert.ok(at >= 0 && kernel.indexOf(tag, at + 1) < 0, "kernel.py loads " + bundle + " once: " + tag);
    assert.equal(kernel.split("/dist/" + bundle).length - 1, 1, "and names its URL nowhere else");
    const def = kernel.lastIndexOf("\ndef ", at);
    assert.ok(kernel.startsWith("\ndef _landing(", def), bundle + " is loaded inside _landing, the shell page's builder");
    assert.ok(!extSrc.includes(bundle), "no VS Code webview document the extension writes loads " + bundle);
  }
});

test("SECURITY.md's hardened list says what the sender checks and the opener policy guarantee, and where the policy applies", () => {
  // SECURITY.md is the document the repo points security readers at (the precedents: security-pdf.test.ts and
  // md-sanitize.test.ts hold their bullets the same way). This test holds the bullet's words; the claims are held by
  // execution elsewhere: this file's census and legs for ui/ (every window message listener checks its sender, the
  // palette's two hear only the shell's panes, and tests/test_palette_senders_browser.py runs those two in real browsers),
  // tests/test_shell_source_check.py for the shell's inline listeners, and tests/test_kernel_auth_hardening.py
  // OpenerIsolation for the opener policy (every page carries it once, a reply in HTTP/0.9's shape aside). The residual
  // names where browsers enforce the policy: secure contexts, which include localhost and 127.0.0.1 over http, the
  // kernel's default address, so a reader on the default setup is not told it lacks the policy.
  const security = fs.readFileSync(path.resolve(EXT, "..", "SECURITY.md"), "utf8");
  const start = security.indexOf("\n## What is already hardened\n");
  assert.ok(start >= 0, "SECURITY.md has its What is already hardened section");
  const rest = security.slice(start + 1);
  const hardened = rest.slice(0, rest.indexOf("\n## ", 1) === -1 ? rest.length : rest.indexOf("\n## ", 1));
  const lead = "- **Window messages and the opener policy.**";
  const at = hardened.indexOf(lead);
  assert.ok(at >= 0, "the hardened list has the bullet: " + lead);
  const tail = hardened.slice(at);
  const bullet = tail.slice(0, tail.indexOf("\n- ", 1) === -1 ? tail.length : tail.indexOf("\n- ", 1)).replace(/\s+/g, " ").trim();
  const escapeRe = (x: string) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const prose = (words: string) => new RegExp(words.trim().split(/\s+/).map(escapeRe).join("\\s+"));
  for (const claim of [
    "Every window message listener romp serves checks a message's sender before acting on it",
    "the shell's window listeners act only on messages from its own panes",
    "Every page the kernel serves carries `Cross-Origin-Opener-Policy: same-origin`, except a reply in HTTP/0.9's shape, which carries no headers and answers only a request line no browser sends",
    "The opener policy applies only in secure contexts (https, and localhost or 127.0.0.1 over http); on any other plain-http address, the sender checks are the protection.",
  ]) assert.match(bullet, prose(claim), "the bullet says: " + claim);
  assert.doesNotMatch(bullet, /\u2014/, "no em dash");
});
