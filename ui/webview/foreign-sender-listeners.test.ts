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
// A representative arm per listener reaches its effect once from every heard sender and never from a foreign one; the
// head check sits before every arm, which the census below pins at source for every listener in ui/. A listener declared
// in ARMS (the way back) has a leg per declared arm (hostUp, and the probe), which the executed-leg census holds to exactly
// one each; each of those legs counts its own arm's effect once and the other arm's twice, so a heard sender that reaches
// the wrong arm fails as well as a foreign one that reaches either.
//
// The census reads the population instead of a list: every addEventListener("message", …) or
// addEventListener("messageerror", …) call in a ui/ source file (tests excluded; uiSources lists the files), the method
// named or a computed member, whatever its receiver, and every onmessage or onmessageerror handler assigned to this page's
// own window, the receiver resolved by its binding (window, self, globalThis, the bare global, this page's
// document.defaultView, a local initialised to one of them, the global `this`), must take the event as its one parameter,
// with no default, open with the check, preceded by nothing but reads of the message, and be one of the gated sites below,
// each with an executed leg here. A messageerror event carries the sender's origin and source as a message does, and a
// sender causes one by posting what the page cannot deserialize, so it is counted as a message. A
// listener handed over by name is read at the function written in place that a const of that name holds, found by the
// name's binding; any other name fails. A new
// window listener anywhere in ui/ fails it until it is gated and given a leg. A second census reads what the name
// windowSender is bound to: in every ui/ file that calls the check, it is the helper's own import (gear.js: its require),
// bound once and never written, so a local helper of the same name that lets one more sender through cannot stand in for
// it. The first census reads the listeners the source spells, so two more hold the source to spellings it can read: a
// third holds that every addEventListener in ui/ is a call the first can read, and a fourth refuses the roads that spell
// neither (a method of the window, of the body element or of a prototype read by a computed name, a function run with
// the window as its `this`, an onmessage handler set other than by an assignment the fourth accepts, a handler or a
// message listener on a window other than this page's own, code run from a string, a `with` statement, and the name
// WebSocket anywhere but a `new`). What those cannot see is listed at the fourth. Synthetic world only: the notes-api
// demo, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
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
 *  sandboxed one (frameIn 0) and one on its origin (frameIn 1); the shell's page holds a sandboxed frame (frameIn 0). */
function receiver(ctx: Ctx): Receiver {
  if (ctx === "pane") {
    const w = new Receiver("a pane in the romp shell", SHELL, ORIGIN, SHELL);
    w.holdFrames([sandboxed(w, SHELL), hideEdges({ name: "a frame on the pane's origin", parent: w, top: SHELL })]);
    return w;
  }
  if (ctx === "shell") {
    const w = new Receiver("the romp shell's page", null, ORIGIN);
    w.parent = w;
    w.top = w;
    w.holdFrames([sandboxed(w, w)]);
    return w;
  }
  if (ctx === "vscode") { const w = new Receiver("a VS Code webview frame", null, VSCODE_ORIGIN); w.parent = w; return w; }
  return new Receiver("a VS Code webview frame, window.parent deleted", undefined, VSCODE_ORIGIN);
}
const SECOND_COLUMN = hideEdges({ name: "a second chat column" });
const CHILD_PANE = hideEdges({ name: "a pane of the shell" });
const VSCODE_HOST = hideEdges({ name: "the VS Code webview host" });
const OTHER_PAGE = hideEdges({ name: "a page on another origin" });
const OTHER_WEBVIEW = hideEdges({ name: "a window on another VS Code webview's origin" });
const sandboxed = (parent: unknown, top?: unknown) => hideEdges({ name: "a sandboxed frame", parent, top });

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
  { who: "a frame inside the pane on its origin, sharing its top and listed in its frames", ctx: "pane", source: (w) => frameIn(w, 1), origin: ORIGIN },
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

// ── the stand-ins stay small in a dump ──

test("the stand-ins inspect as their primitives: every enumerable key of a receiving window and of each sending window holds a primitive", () => {
  const pane = receiver("pane"), shell = receiver("shell");
  const all: object[] = [SHELL, SECOND_COLUMN, CHILD_PANE, VSCODE_HOST, OTHER_PAGE, OTHER_WEBVIEW, sandboxed(SHELL), sandboxed(SHELL, SHELL),
    pane, shell, receiver("vscode"), receiver("vscode, older"), frameIn(pane, 0) as object, frameIn(pane, 1) as object, frameIn(shell, 0) as object];
  for (const o of all) {
    for (const k of Object.keys(o)) assert.ok(staysEnumerable((o as any)[k]), k + " is enumerable and holds a " + typeof (o as any)[k]);
  }
  assert.ok(windowSender({ source: SHELL, origin: ORIGIN }, receiver("pane")) === "embedder", "a hidden parent is still read");
  // the frames edges are there for a check to read, hidden or not: each receiver's frames is itself, listing its frames
  assert.ok(pane.frames === pane && pane.length === 2 && pane.top === SHELL && (frameIn(pane, 0) as { parent: unknown }).parent === pane,
    "the pane's frames list its two frames, and its top is the shell");
  assert.ok(shell.frames === shell && shell.length === 1 && shell.top === shell, "the shell's page lists its one frame, and it is its own top");
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
/** The names a script reaches its own window by: window, self and globalThis, unshadowed. With the bare global they are
 *  where refKind (at the road census below) starts this page's own window; a receiver it resolves to a window other than
 *  this page's own, or cannot resolve, is no census site, and the road census refuses the handler set on it. */
const WINDOW_NAMES = new Set(["window", "self", "globalThis"]);
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
 *  each assignment of an onmessage or onmessageerror handler whose receiver refKind resolves by binding to this page's own
 *  window, or with no receiver (the bare global). Where it is, what it is on, and the listener's node and text. A listener handed to
 *  addEventListener by a plain name (the file viewer's onKernelMessage, which its close removes by that name) is read at
 *  the function the name holds, when a const of that name, found by the name's binding (declOf), is initialised to a
 *  function written in place: a const is never rebound, and the binding, not the spelling, picks it, so another
 *  declaration of the name elsewhere in the file is not the one read. Any other name (a let or a var, which can be
 *  rebound; a parameter; a function declaration, which can be assigned to; a const holding a call's result) stays the
 *  name, which the head census refuses. */
function sitesIn(file: string, src: string): Site[] {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kindOfUi(file));
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
      if (m && MESSAGE_HANDLERS.has(m.name) && (recv === null || ownWindowRef(recv))) {
        out.push({ file, line: line(n), receiver: m.receiver, fn: n.right, text: n.right.getText(sf), kind: "onmessage", event: m.name.slice(2) });
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
                // the effect's binding, counting through hit; arm is the leg's own arm, for a scope with more than one effect
                named: (hit: () => void, w: Receiver, arm: string | undefined) => Record<string, unknown>;
                writes?: string;   // or: the effect is a write to this free name
                arm?: string };    // a leg of a listener declared in ARMS names the declared arm it runs
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
  { file: "webview/palette-main.ts", marker: '"openKeys"', what: "the shell's openKeys ask, which opens the shortcuts dialog",
    data: { romp: "openKeys" }, named: (hit) => ({ keys: { open: hit } }) },
  { file: "webview/palette-main.ts", marker: '"hotkeyConfigure"', what: "the shell's hotkeyConfigure ask, which binds a tab's hot key",
    data: { romp: "hotkeyConfigure", sid: SID, name: "web" }, named: (hit) => ({ configureHotkey: hit }) },
  { file: "webview/strip.ts", marker: '"stripShow"', what: "the VS Code strip's usage push, which repaints the bars",
    data: { type: "usage", usage: { fiveHour: { pct: 10 } } }, named: (hit) => ({ render: hit }) },
];
/** The listeners owed a leg per arm, by file, the marker that picks the listener (siteOf) and its arms: the executed-leg
 *  census holds each to exactly one leg per declared arm, each naming it, and each leg's scope counts its own arm's effect
 *  once and every other arm's twice (wayBackScope), which the crossed-message test below holds. Every other listener has
 *  one leg, which names no arm: a representative arm, since the head census pins the check ahead of every arm.
 *  Residual (low, disclosed): this table is hand-written, not derived from the way back's source, so a coordinated test-side
 *  edit that empties it, drops the probe leg and unarms the hostUp leg would leave one unarmed leg and still pass here. The
 *  product stays guarded regardless: the head census refuses onKernelMessage acting before its check, and file-view-seam.ts
 *  reds a foreign hostUp or probe. Deriving the arms from source is listener-specific (the probe arm is a fallthrough, named
 *  by no literal) and not worth the fragility for this; recorded rather than fixed. */
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
 *  first whose test matches taking the file: tests and types (a `.test.` file of any module suffix, a `.d.` file of a
 *  TypeScript one); modules, every suffix esbuild 0.21.5's default loaders read as code (.ts .tsx .mts .cts .js .jsx .mjs
 *  .cjs) in any directory, the files every census here reads; and the files no census reads, each class named:
 *  stylesheets, the anchor map's fixtures (its directory's data: markdown, json, a python file, an html page with no
 *  script, a csv, an svg, a .gitattributes) and the markdown at ui/'s own top (its README and CLAUDE.md). A file no class
 *  takes reds uiPartition, named with its suffix, so a file of a kind no class names is loud, never dropped. A directory
 *  named node_modules or dist is not walked: installed packages and build output, no source. */
const UI_CLASSES: Array<[string, RegExp]> = [
  ["tests and types", /\.test\.([mc]?[tj]s|[tj]sx)$|\.d\.([mc]?ts|tsx)$/],
  ["modules", /\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)$/],
  ["stylesheets", /\.css$/],
  ["the anchor map's fixtures", /^webview\/anchor-map-fixtures\/[^/]+$/],
  ["ui's own markdown", /^[^/]+\.md$/],
];
/** The class of the file at `rel` (relative to ui/): the first of UI_CLASSES whose test matches it, or null. */
const uiClassOf = (rel: string): string | null => { const c = UI_CLASSES.find(([, re]) => re.test(rel)); return c ? c[0] : null; };
let uiParts: Record<string, string[]> | null = null;
/** Every file under `root` (ui/ unless a test hands another; a directory named node_modules or dist aside), relative to it,
 *  partitioned into UI_CLASSES by uiClassOf; a file no class takes is a red naming it. ui/ is walked once per run. */
function uiPartition(root: string = UI): Record<string, string[]> {
  if (root === UI && uiParts) return uiParts;
  const out: Record<string, string[]> = {};
  for (const [k] of UI_CLASSES) out[k] = [];
  const rest: string[] = [];
  const walk = (rel: string): void => {
    for (const d of fs.readdirSync(path.join(root, rel), { withFileTypes: true })) {
      const r = rel ? rel + "/" + d.name : d.name;
      if (d.isDirectory()) { if (d.name !== "node_modules" && d.name !== "dist") walk(r); continue; }
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
/** Where the listener's `if (windowSender(<its event>) === "foreign") return;` is among its body's statements, or why it
 *  does not count: the listener takes one parameter, the event, a plain name with no default (a parameter's default runs
 *  before the body, so a default on it or on a second parameter would run ahead of the check), and every statement before
 *  the check must be a read of the message (a declaration initialised to <event>.data) or an early return whose condition
 *  runs no code (inert): no call, construct, tagged or substituted template, delete, await, yield, ++/--, assignment, or a
 *  binary operator that coerces an operand (==, !=, <, >, <=, >=, in, instanceof; the strict === and !== do not coerce and
 *  stay), and every property or element access reads what no page code produces: off the event, its data at any depth (a
 *  structured clone, with no accessors) or, one level and no deeper, its own origin, source, ports or lastEventId; off a
 *  name a message read bound to <event>.data, any depth. A read any further through the event can run a getter the page
 *  defined: its target, currentTarget and srcElement are the receiving window, its view is a window where the event has
 *  one, and a member of its source is a member of the sending window, so e.target.x, e.view and e.source.parent are not
 *  inert, nor is a getter read or a coercion off any other object. Each would run an arm for a foreign sender before the
 *  check. So no arm runs before the check. */
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
  // the binary operators that coerce no operand: the logical connectives, strict equality and the comma. Every other binary
  // operator runs valueOf/toString/Symbol.toPrimitive (==, !=, the relational operators, +, and the rest) or Symbol.hasInstance
  // (instanceof) or a Proxy trap (in) on an operand, so it can run an arm; assignments run an arm too. All are not inert.
  const NON_COERCING = new Set<number>([ts.SyntaxKind.AmpersandAmpersandToken, ts.SyntaxKind.BarBarToken,
    ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.EqualsEqualsEqualsToken, ts.SyntaxKind.ExclamationEqualsEqualsToken,
    ts.SyntaxKind.CommaToken]);
  /** The event's own attributes a pre-check may read one level deep: none runs page code, and a member of any of them could
   *  (a member of its source is a member of the sending window). */
  const EVENT_OWN = new Set(["origin", "source", "ports", "lastEventId"]);
  /** The leftmost node of a property or element access chain, casts and parentheses removed. */
  const accessRoot = (n: any): any => { n = unwrap(n); while (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) n = unwrap(n.expression); return n; };
  /** Whether `n` runs no code. `allowed` is the names a property or element access may read off: the event (its data at any
   *  depth, or one of EVENT_OWN one level deep) and every name a message read has bound to <event>.data so far (any depth; a
   *  getter cannot run on a MessageEvent's structured-clone data). */
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
  const readsMessage = (s: any) => ts.isVariableStatement(s) && s.declarationList.declarations.every((d: any) =>
    d.initializer && ts.isPropertyAccessExpression(d.initializer) && ts.isIdentifier(d.initializer.expression)
    && d.initializer.expression.text === ev && d.initializer.name.text === "data");
  const earlyReturn = (s: any, allowed: Set<string>) => ts.isIfStatement(s) && !s.elseStatement && isReturn(s.thenStatement) && inert(s.expression, allowed);
  const body = fn.body.statements;
  const allowed = new Set<string>([ev]);   // the event, plus each name a message read binds to <event>.data, in body order
  for (let i = 0; i < body.length; i++) {
    if (isGate(body[i])) return null;
    if (readsMessage(body[i])) {
      for (const d of (body[i] as any).declarationList.declarations) if (ts.isIdentifier(d.name)) allowed.add(d.name.text);
      continue;
    }
    if (!earlyReturn(body[i], allowed)) return "statement " + (i + 1) + " runs before the foreign-sender check: " + body[i].getText().slice(0, 80);
  }
  return "no `if (windowSender(" + ev + ") === \"foreign\") return;` in the listener's body";
}
// The gated sites, by file and count. An addEventListener("message", …) on something that is not a window, which no
// other page can post to, would be listed in EXEMPT with its reason; there is none in ui/ today. An onmessage handler on
// something other than this page's window is no census site: the road census accepts a WebSocket's own handler
// (federation.ts's sockets, a binding that only ever holds `new WebSocket(...)`) and refuses every other receiver it
// cannot resolve, so a MessagePort's, a worker's, a BroadcastChannel's or an EventSource's handler is refused, fail-closed.
const GATED: Array<[string, number]> = [
  ["webview/file-browse.ts", 1], ["webview/file-comments.ts", 1], ["webview/file-view.ts", 2], ["webview/frame-listener.ts", 1],
  ["webview/gear.js", 6], ["webview/palette-main.ts", 2], ["webview/settings.ts", 1], ["webview/strip.ts", 1], ["webview/waiting.ts", 1],
];
const EXEMPT: Array<[string, number, string]> = [];
/** Whether a census site is spelled as every gated site is, window.addEventListener("message" or "messageerror", …): the
 *  census holds every site to it, so an onmessage handler on any receiver, and a listener added to any receiver but the
 *  text `window`, keeps the census red whatever else it carries. */
const spelledAsGated = (s: Site): boolean => s.receiver === "window" && s.kind === "addEventListener";

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
  assert.ok(sites.every(spelledAsGated),
    "every census site is window.addEventListener(\"message\", ...), the one spelling the gated sites use");
});

test("the census reads every spelling of a window message listener: addEventListener named or computed on any receiver, for a message or a messageerror, and an onmessage or onmessageerror handler on a receiver resolved by its binding to this page's own window, each failing the gated spelling; a handler on another window, a socket or a receiver the census cannot resolve is no site", () => {
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
  // an onmessage or onmessageerror handler on a receiver the census resolves by its binding to this page's own window is
  // exactly one census site, and the census's spelling predicate (spelledAsGated) fails it, so it keeps the census red
  const OWN_WINDOW: Array<[string, string?]> = [
    ["window.window.onmessage = f;"], ["self.self.onmessage = f;"], ["globalThis.window.onmessage = f;"],
    ["window[\"window\"][\"onmessage\"] = f;"], ["(window as any).self.onmessage = f;"], ["window!.onmessageerror = f;"],
    ["document.defaultView.onmessage = f;"], ["window.document.defaultView.onmessage = f;"], ["self.document.defaultView.onmessage = f;"],
    ["const w = window; w.onmessage = f;"], ["const w = window, x = w; x.onmessage = f;"], ["let w = window; w.onmessage = f;"],
    ["for (var w = window; ;) { w.onmessage = f; break; }"], ["const d = document; d.defaultView.onmessage = f;"],
    ["const { defaultView } = document; defaultView.onmessage = f;"], ["const { document: { defaultView: dv } } = window; dv.onmessage = f;"],
    ["const { window: w } = self; w.onmessage = f;"],
    ["w\\u0069ndow.onmessage = f;"], ["document.def\\u0061ultView.onmessage = f;"],
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
  const sited = ["frames.onmessage = f;", "parent.onmessage = f;", "top[\"onmessage\"] = f;", "opener.onmessage = f;", "frames[0].onmessage = f;",
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
  const kind = kindOfUi(file), isJs = kind === ts.ScriptKind.JS || kind === ts.ScriptKind.JSX;
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kind);
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
    const sf = ts.createSourceFile(f, src, ts.ScriptTarget.Latest, true, kindOfUi(f));
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
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kindOfUi(file));
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

test("census: every file under ui/ is in a named class, and the censuses read the modules class, every gated site's file among them", () => {
  const parts = uiPartition();
  assert.ok(parts["modules"].length > 100, "the censuses read ui/'s modules: " + parts["modules"].length);
  for (const [f] of GATED) assert.ok(parts["modules"].includes(f), "a gated site's file is a module the censuses read: " + f);
  assert.deepEqual(uiSources(), parts["modules"], "the censuses walk the modules class");
});

test("the file classes read what they claim: a module of every suffix esbuild reads as code is read by the censuses in any directory, a test or a types file of each is not, and a file of any other kind outside the named classes has no class", () => {
  // synthetic names only: uiClassOf reads a name, and no fixture file may sit in ui/
  const NAMES: Array<[string, string | null]> = [
    ["webview/probe.ts", "modules"], ["webview/probe.tsx", "modules"], ["webview/probe.mts", "modules"], ["webview/probe.cts", "modules"],
    ["webview/probe.js", "modules"], ["webview/probe.jsx", "modules"], ["webview/probe.mjs", "modules"], ["webview/probe.cjs", "modules"],
    ["probe.ts", "modules"], ["webview/deep/er/probe.tsx", "modules"], ["webview/anchor-map-fixtures/probe.js", "modules"],
    ["webview/probe.test.ts", "tests and types"], ["webview/probe.test.tsx", "tests and types"], ["webview/probe.test.mjs", "tests and types"],
    ["webview/probe.test.cjs", "tests and types"], ["webview/probe.test.jsx", "tests and types"], ["webview/probe.d.ts", "tests and types"],
    ["webview/probe.d.mts", "tests and types"], ["webview/probe.d.cts", "tests and types"],
    ["webview/probe.css", "stylesheets"], ["webview/anchor-map-fixtures/probe.json", "the anchor map's fixtures"],
    ["webview/anchor-map-fixtures/.gitattributes", "the anchor map's fixtures"], ["README.md", "ui's own markdown"],
    ["webview/probe.html", null], ["webview/probe.json", null], ["webview/probe.md", null], ["webview/probe.vue", null],
    ["webview/probe", null], ["webview/anchor-map-fixtures/deeper/probe.md", null],
  ];
  const wrong = NAMES.filter(([n, want]) => uiClassOf(n) !== want).map(([n, want]) => n + ": " + uiClassOf(n) + ", not " + want);
  assert.deepEqual(wrong, [], "each synthetic name's class (UI_CLASSES, tried in order)");
});

test("the partition fails on a file no class takes, naming it, and walks every directory but node_modules and dist", () => {
  // a synthetic tree in a temporary root outside ui/ (uiPartition reads the root it is handed)
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "fsl-partition-"));
  try {
    for (const d of ["webview/deep", "node_modules/pkg", "dist"]) fs.mkdirSync(path.join(root, d), { recursive: true });
    for (const f of ["README.md", "webview/a.ts", "webview/deep/b.tsx", "webview/a.test.ts", "webview/s.css", "node_modules/pkg/x.vue", "dist/y.html"]) {
      fs.writeFileSync(path.join(root, f), "");
    }
    assert.deepEqual(uiPartition(root)["modules"], ["webview/a.ts", "webview/deep/b.tsx"], "the modules, at any depth; node_modules and dist not walked");
    fs.writeFileSync(path.join(root, "webview", "stray.vue"), "");
    assert.throws(() => uiPartition(root), /every file under ui\/ is in one of the named classes[^]*webview\/stray\.vue \(\.vue\)/);
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
// (tests excluded), read by the TypeScript parser. It resolves what a receiver is by its binding (refKind):
//   - this page's own window: window, self and globalThis, unshadowed; any of them reached through another
//     (window.self); this page's document's defaultView (document unshadowed, or this window's document, or a local
//     initialised to one); a local initialised to any of these or destructured from one (const { defaultView } =
//     document); and `this` where it is the global object (a plain function's or the file's own, outside any class or
//     method);
//   - a window other than this page's own: frames (which a browser answers with the window itself; refused with the rest
//     here, so no reader has to know that), top, parent and opener, unshadowed; any of those reached through a window
//     (window.parent, parent.top), and anything reached through another window; an indexed window (frames[0], window[0],
//     a frame's); a frame's contentWindow; the defaultView of any document the census cannot tell is this page's
//     (el.ownerDocument.defaultView); and an event's view, target, currentTarget or srcElement, each of which can hold a
//     window; and a local initialised to any of these or destructured from one (const { parent: p } = window);
//   - the body element, whose onmessage is its window's: the body of any document (this page's, a window's, any
//     ownerDocument or contentDocument, a local initialised to one) and a local initialised to it or destructured from a
//     document (const { body } = document).
// Refused:
//   - a method of a window (this page's or another), of the body element or of a prototype read by a name computed at
//     run time. A prototype holds the same methods (protoRef): every DOM interface's chain ends at EventTarget.prototype,
//     which holds addEventListener, so X.prototype for any X, any __proto__, and what Object.getPrototypeOf or
//     Reflect.getPrototypeOf returns count with the window. Refused on any of them: a member read by a computed name
//     (window["add" + "EventListener"], a template, a variable key), whether called, assigned or read; Reflect.get,
//     Reflect.getOwnPropertyDescriptor or Object.getOwnPropertyDescriptor with a key that is not a literal, and
//     Object.getOwnPropertyDescriptors, which hands on every member under its name; a destructuring pattern with a
//     computed key (const { [k]: add } = window); and a reflective write whose key or keys are computed (Reflect.set,
//     Reflect.defineProperty, Object.defineProperty or __defineSetter__ with a key that is not a literal; Object.assign or
//     Object.defineProperties from an object literal with a computed key or a spread; a new prototype for the window);
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
//     end of an assignment chain: dead.onopen = dead.onmessage = null); and on a WebSocket, a const, let or var (never a
//     parameter, a catch clause's name or a for...in or for...of head's) whose initialiser, every plain assignment to it
//     and every other `var` of its name in its var scope is `new WebSocket(...)`, the constructor unshadowed, with no
//     other write to it (a compound assignment, ++ or --, destructuring, a for...in or for...of head). A window other than
//     this page's own is refused whatever the value, and so is every receiver the census resolves to neither this page's
//     window nor a socket: the body element, a parameter, a call's result, an object's property, a MessagePort, a
//     worker, a channel;
//   - a message or messageerror listener added to a window other than this page's own (parent.addEventListener(...)),
//     where a check at its head could not be about this page's senders;
//   - code run from a string: eval, the Function constructor (by name, or reached through a function's .constructor),
//     and setTimeout or setInterval handed a string;
//   - a `with` statement, which answers any name inside it from an object the census cannot read (a write to a socket's
//     binding, the WebSocket constructor, undefined);
//   - the name WebSocket, as a name or a string, anywhere but as the constructor a `new` calls (bare or as a member) and
//     in a type: a replaced global WebSocket (window.WebSocket = f, Object.defineProperty(window, "WebSocket", ...), a
//     class of that name) would make the socket the census accepts any object.
// ui/ has none of these today, so the rules cost nothing. What they cannot see, disclosed:
//   - a window held where no initialiser shows it: in a parameter, in a let or var assigned later, behind a comma,
//     conditional, || or ?? expression, in a Proxy, in an object or array it was put in, or returned by a function
//     (Object(window) among them), and nested more than four names deep. An onmessage handler set on such a receiver is
//     refused (the census resolves it to nothing); a method read off it by a computed name is not;
//   - the body element reached other than as a document's body: a query for it, a frameset,
//     document.documentElement.lastElementChild. A member written on it under a computed key sets its window's handler;
//   - an event's source under a computed key (e.source[k] = f): source cannot join the event members above, since two
//     live reads index an object's `source` string;
//   - a method of another EventTarget (an element, the document) read by a computed name and called with no receiver:
//     WebIDL runs an operation called with no `this` on the global object, so `const add = document.documentElement[k];
//     add("message", f)` registers on the window; and such a method run on `this` where `this` is the window;
//   - a reflective function under another name (const R = Reflect; R.get(window, k)), and a Function.prototype.call
//     reached any way but by name;
//   - an object built elsewhere with a computed key and copied onto the window (Object.assign(window, make()) is read as
//     its call only), and a key computed in another module and passed to a reflective read or write through a helper;
//   - a top-level var of a classic script rebound through the global object (this.ws = window, window.ws = window): the
//     census reads a var's writes by its name. No ui/ source runs as a classic script today: esbuild bundles each, and
//     the kernel inlines romp-timeline-view.js inside a function;
//   - code handed to the DOM as markup or a URL (a script element, an inline handler attribute, a javascript: URL),
//     which is no JavaScript the parser reads.

/** The windows a script can name that are not its own (WINDOW_NAMES are its own): frames, top, parent and opener. */
const OTHER_WINDOW_NAMES = new Set(["frames", "top", "parent", "opener"]);
/** Every name a script reaches a window by: its own and the others. */
const WINDOW_GLOBALS = new Set([...WINDOW_NAMES, ...OTHER_WINDOW_NAMES]);
/** The members that are a window whatever holds them: a document's window, a frame's, and an event's view, target,
 *  currentTarget and srcElement. A defaultView is this page's own window when its document is this page's (memberKind);
 *  every other one of these is a window the census cannot tell from another. */
const WINDOW_MEMBERS = new Set(["defaultView", "contentWindow", "view", "target", "currentTarget", "srcElement"]);
/** The name of `x.name`, or of `x["name"]` with a literal key; else null. */
const memberName = (n: any): string | null => ts.isPropertyAccessExpression(n) ? n.name.text
  : ts.isElementAccessExpression(n) && n.argumentExpression && ts.isStringLiteralLike(n.argumentExpression) ? n.argumentExpression.text : null;
/** What a receiver is, by binding: this page's own window, a window other than this page's own (or one the census cannot
 *  tell from another), this page's document, a document the census cannot tell is this page's, or a document's body
 *  element, which reflects its window's event handlers. */
type RefKind = "window" | "otherWindow" | "document" | "otherDocument" | "body";
/** The kind of member `key` of something of kind `from` (null: resolved to nothing), or null. */
function memberKind(from: RefKind | null, key: string): RefKind | null {
  if (WINDOW_MEMBERS.has(key)) return key === "defaultView" && from === "document" ? "window" : "otherWindow";
  if (key === "ownerDocument" || key === "contentDocument") return "otherDocument";
  if (from === "window" || from === "otherWindow") {
    if (WINDOW_NAMES.has(key)) return from;
    if (OTHER_WINDOW_NAMES.has(key)) return "otherWindow";
    if (key === "document") return from === "window" ? "document" : "otherDocument";
  }
  if ((from === "document" || from === "otherDocument") && key === "body") return "body";
  return null;
}
/** Whether an element access's key is an index: a numeric literal or an all-digit string (frames[0], window["0"]). */
const isIndexKey = (k: any): boolean => { const u = k && unwrap(k); return !!u && (ts.isNumericLiteral(u) || (ts.isStringLiteralLike(u) && /^\d+$/.test(u.text))); };
/** Whether `this` at `n` is the global object: in a plain function (not a method, a class's, or an object literal's
 *  function) or at the file's top, through any arrow functions. */
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
/** The kind `n` resolves to by its binding, or null: WINDOW_NAMES unshadowed are this page's own window,
 *  OTHER_WINDOW_NAMES another, `document` unshadowed this page's document; a member by memberKind; an indexed window
 *  (frames[0], window[0]) is a frame's, another; a local initialised to any of these, or destructured from one, the kind
 *  its initialiser gives (patternKind); and, unless `noThis`, `this` where it is the global object, this page's window.
 *  Nested more than four deep, null. */
function refKind(n: any, depth = 0, noThis = false): RefKind | null {
  n = unwrap(n);
  if (depth > 4) return null;
  if (n.kind === ts.SyntaxKind.ThisKeyword) return !noThis && thisIsGlobal(n) ? "window" : null;
  if (ts.isElementAccessExpression(n) && isIndexKey(n.argumentExpression)) {   // frames[0]: a frame's window
    const k = refKind(n.expression, depth + 1, noThis);
    return k === "window" || k === "otherWindow" ? "otherWindow" : null;
  }
  const name = memberName(n);
  if (name !== null) return memberKind(refKind(n.expression, depth + 1, noThis), name);
  if (!ts.isIdentifier(n)) return null;
  const d = declOf(n);
  if (!d) return WINDOW_NAMES.has(n.text) ? "window" : OTHER_WINDOW_NAMES.has(n.text) ? "otherWindow" : n.text === "document" ? "document" : null;
  if (!ts.isVariableDeclaration(d) || !d.initializer) return null;
  const from = refKind(d.initializer, depth + 1, noThis);
  return ts.isIdentifier(d.name) ? from : patternKind(d.name, n.text, from);
}
/** The kind destructuring `pattern` from something of kind `from` binds `name` to: each key by memberKind, at any depth
 *  (const { parent: p } = window; const { document: { body } } = window). */
function patternKind(pattern: any, name: string, from: RefKind | null): RefKind | null {
  if (!ts.isObjectBindingPattern(pattern)) return null;
  for (const e of pattern.elements) {
    const key = e.propertyName ? (ts.isIdentifier(e.propertyName) || ts.isStringLiteralLike(e.propertyName) ? e.propertyName.text : null)
      : (ts.isIdentifier(e.name) ? e.name.text : null);
    const k = key === null || e.dotDotDotToken ? null : memberKind(from, key);
    if (ts.isIdentifier(e.name)) { if (e.name.text === name) return k; }
    else if (bindsName(e.name, name)) return patternKind(e.name, name, k);
  }
  return null;
}
/** Whether `n` is a window, this page's own or another (refKind). */
function windowRef(n: any, depth = 0, noThis = false): boolean {
  const k = refKind(n, depth, noThis);
  return k === "window" || k === "otherWindow";
}
/** Whether `n` is this page's own window (refKind): a handler set on it is a census site. */
const ownWindowRef = (n: any): boolean => refKind(n) === "window";
/** Whether `n` is a window other than this page's own, or one the census cannot tell from another (refKind). */
const otherWindowRef = (n: any): boolean => refKind(n) === "otherWindow";
/** Whether `n` is a document's body element (refKind), which reflects its window's event handlers. */
const bodyRef = (n: any): boolean => refKind(n) === "body";
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
/** Whether a member read off `n` can be a window's method or its handler: `n` is a window, a prototype, or the body element
 *  (whose onmessage is its window's). */
const holdsWindowMethods = (n: any): boolean => windowRef(n) || protoRef(n) || bodyRef(n);
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
/** Whether an assignment's value, the last of a chain (a = b = null), sets no handler: null, or an unshadowed undefined. */
function setsNoHandler(v: any): boolean {
  v = unwrap(v);
  while (ts.isBinaryExpression(v) && v.operatorToken.kind === ts.SyntaxKind.EqualsToken) v = unwrap(v.right);
  return v.kind === ts.SyntaxKind.NullKeyword || (ts.isIdentifier(v) && v.text === "undefined" && !declOf(v));
}
/** The constructor whose instance's own onmessage handler the road census accepts: a WebSocket's, on which only its server
 *  posts. Every other object that carries messages (a MessagePort, a worker, a BroadcastChannel, an EventSource) is refused. */
const SOCKET_CTORS = new Set(["WebSocket"]);
/** Whether `v` is `new WebSocket(...)` (or new window.WebSocket(...)), its root name unshadowed. */
function isSocketNew(v: any): boolean {
  v = unwrap(v);
  if (!ts.isNewExpression(v)) return false;
  let root = unwrap(v.expression);
  while (ts.isPropertyAccessExpression(root)) root = unwrap(root.expression);
  return ts.isIdentifier(root) && !declOf(root) && SOCKET_CTORS.has(globalName(v.expression));
}
/** The var scope a declaration's name is hoisted to. */
const hoistedScope = (n: any): any => { let s = n.parent; while (s && !isVarScope(s)) s = s.parent; return s; };
/** Whether `recv` is a name whose binding only ever holds a WebSocket: a const, let or var (never a parameter, a catch
 *  clause's name, or a for...in or for...of head's, whose value comes from elsewhere) whose initialiser, every value a
 *  plain assignment writes to it, and the initialiser of every other `var` of its name in its var scope are
 *  new WebSocket(...) (isSocketNew). Any other write refuses: a compound assignment, ++ or --, destructuring, a for...in
 *  or for...of head, a `var` of its name in such a head. */
function socketBinding(recv: any, sf: any): boolean {
  recv = unwrap(recv);
  if (!ts.isIdentifier(recv)) return false;
  const d = declOf(recv);
  if (!d || !ts.isVariableDeclaration(d) || !ts.isIdentifier(d.name)) return false;
  const loop = d.parent && d.parent.parent;
  if (ts.isCatchClause(d.parent) || (loop && (ts.isForOfStatement(loop) || ts.isForInStatement(loop)))) return false;   // what was thrown, or the loop's value
  const name = d.name.text;
  const vals: any[] = d.initializer ? [d.initializer] : [];
  let other = false;
  const visit = (n: any): void => {
    if (other) return;
    if (ts.isIdentifier(n) && n.text === name && n !== d.name && ts.isVariableDeclaration(n.parent) && n.parent.name === n
        && (n.parent.parent.flags & ts.NodeFlags.BlockScoped) === 0 && hoistedScope(n) === hoistedScope(d.name)) {
      // another `var` of the name in the same var scope, matched by name (declOf resolves a for...in or for...of head's
      // to the loop's own declaration): its initialiser is a write, and a loop head's value is no socket
      if (n.parent.initializer) vals.push(n.parent.initializer);
      const h = n.parent.parent.parent;
      if (h && (ts.isForOfStatement(h) || ts.isForInStatement(h))) other = true;
    } else if (ts.isIdentifier(n) && n.text === name && n !== d.name && declOf(n) === d) {
      const m = outer(n), p = m.parent;
      if (ts.isBinaryExpression(p) && p.left === m && p.operatorToken.kind === ts.SyntaxKind.EqualsToken) vals.push(p.right);
      else if (ts.isBinaryExpression(p) && p.left === m && isAssignOp(p.operatorToken.kind)) other = true;
      else if ((ts.isPrefixUnaryExpression(p) || ts.isPostfixUnaryExpression(p))
               && (p.operator === ts.SyntaxKind.PlusPlusToken || p.operator === ts.SyntaxKind.MinusMinusToken)) other = true;
      else {
        for (let c: any = m, q: any = p; q; c = q, q = q.parent) {   // a destructuring target, or a loop head's
          if (ts.isArrayLiteralExpression(q) || ts.isObjectLiteralExpression(q) || ts.isPropertyAssignment(q) || ts.isShorthandPropertyAssignment(q)
              || ts.isSpreadElement(q) || ts.isSpreadAssignment(q) || ts.isParenthesizedExpression(q)) continue;
          if (ts.isBinaryExpression(q) && q.left === c && isAssignOp(q.operatorToken.kind)) other = true;
          if ((ts.isForOfStatement(q) || ts.isForInStatement(q)) && q.initializer === c) other = true;
          break;
        }
      }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return !other && vals.length > 0 && vals.every(isSocketNew);
}
/** Whether `n` is the constructor a `new` calls, bare (new WebSocket(u)) or as a member (new window.WebSocket(u)). */
const isNewCallee = (n: any): boolean => {
  const o = outer(n);
  if (ts.isNewExpression(o.parent) && o.parent.expression === o) return true;
  if (!ts.isPropertyAccessExpression(n.parent) || n.parent.name !== n) return false;
  const m = outer(n.parent);
  return ts.isNewExpression(m.parent) && m.parent.expression === m;
};
/** Every road in `src` the comment above lists, with where it is and why, and how many onmessage and onmessageerror names
 *  it read. */
function looseRoads(file: string, src: string): { onmessage: number; loose: LooseAdd[] } {
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true, kindOfUi(file));
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
        if (acc === tok || ownWindowRef(acc.expression)) return;   // the bare global, or this page's own window: a census site
        if (otherWindowRef(acc.expression)) return refuse(tok, "an " + tok.text + " handler on a window other than this page's own, which no check at its head can be about");
        if (setsNoHandler(q.right)) return;                         // null or undefined: it sets no handler
        if (socketBinding(acc.expression, sf)) return;              // a WebSocket's own handler
        return refuse(tok, "an " + tok.text + " handler on a receiver the census cannot resolve to this page's window or to a socket");
      }
      if (onlyTested(acc)) return;
    }
    refuse(tok, "an " + tok.text + " handler set some way other than an assignment the census reads");
  };
  const visit = (n: any): void => {
    if ((ts.isIdentifier(n) || ts.isStringLiteralLike(n)) && MESSAGE_HANDLERS.has(n.text)) { onmessage++; handlerToken(n); }
    if (ts.isCallExpression(n) && n.arguments.length >= 1 && ts.isStringLiteralLike(n.arguments[0]) && MESSAGE_EVENTS.has(n.arguments[0].text)) {
      const c = unwrap(n.expression);
      if (memberName(c) === "addEventListener" && otherWindowRef(c.expression)) {
        refuse(n, "a " + n.arguments[0].text + " listener added to a window other than this page's own, which no check at its head can be about");
      }
    }
    if (ts.isWithStatement(n)) refuse(n, "a with statement, which answers the names inside it from an object the census cannot read");
    if ((ts.isIdentifier(n) || ts.isStringLiteralLike(n)) && n.text === "WebSocket" && !inType(n) && !isNewCallee(n)) {
      refuse(n, "the name WebSocket other than as the constructor a new calls, which could replace the socket the census accepts");
    }
    if (ts.isElementAccessExpression(n) && !isLiteralKey(n.argumentExpression) && holdsWindowMethods(n.expression)) {
      refuse(n, "a member of a window, the body element or a prototype reached by a computed name, which the censuses cannot read");
    }
    if ((ts.isVariableDeclaration(n) || ts.isParameter(n) || ts.isBindingElement(n)) && n.initializer && ts.isObjectBindingPattern(n.name)
        && holdsWindowMethods(n.initializer) && computedKeyIn(n.name)) {
      refuse(n, "a member of a window, the body element or a prototype destructured by a computed key, which the censuses cannot read");
    }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isObjectLiteralExpression(unwrap(n.left))
        && holdsWindowMethods(n.right) && computedKeyIn(unwrap(n.left))) {
      refuse(n, "a member of a window, the body element or a prototype destructured by a computed key, which the censuses cannot read");
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
        if (REFLECT_READ.has(base) && !isLiteralKey(args[1])) refuse(n, base + " of a window, the body element or a prototype with a computed key, which the censuses cannot read");
        if (REFLECT_READ_ALL.has(base)) refuse(n, base + " of a window, the body element or a prototype, which hands on every member under its name");
        if (REFLECT_KEYED.has(base) && !isLiteralKey(args[1])) refuse(n, base + " onto a window, the body element or a prototype with a computed key, which the censuses cannot read");
        if (REFLECT_SPREAD.has(base)) {
          for (const a of args.slice(1)) {
            const o = unwrap(a);
            if (ts.isObjectLiteralExpression(o) && o.properties.some((pr: any) => ts.isSpreadAssignment(pr) || pr.name && ts.isComputedPropertyName(pr.name) && !isLiteralKey(pr.name.expression))) {
              refuse(n, base + " onto a window, the body element or a prototype from an object with a computed key or a spread, which the censuses cannot read");
            }
          }
        }
        if (REFLECT_PROTO.has(base)) refuse(n, base + " on a window, the body element or a prototype, which replaces what its methods are");
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
        refuse(n, run + " on a window, the body element or a prototype with a computed key, which the censuses cannot read");
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

test("census: no ui/ source reaches a window listener by a computed name, runs a function with the window as its this, sets an onmessage handler other than by an assignment the census accepts, adds a message listener to another window, runs code from a string, holds a with statement, or names WebSocket but to construct one", () => {
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

test("the road census reads what it claims: every road around the spelled registration is refused, each for its reason, and a WebSocket's own handler, a handler cleared with null, a handler on this page's own window, a literal member and code that is no road are accepted", () => {
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
    // parent, a class's own this, a wrapper passing its own this on (ui/webview/md-block-start.ts), a call on another object
    ["function h(n: object, k: string) { return Object.getOwnPropertyDescriptor(n, k); } const d = Reflect.get(obj, k);"],
    ["function p(parent: any, top: any[], k: number) { return [parent[k], top[k]]; } const frames: number[] = []; frames[k] = 1;"],
    ["const o = { defaultView: 1 }; const { [k]: v } = obj; ({ [k]: v } = other);"],
    ["const wrapped = function (this: object, ...a: unknown[]) { return orig.apply(this, a); };"],
    ["Object.prototype.hasOwnProperty.call(n, \"_nid\"); Array.prototype.forEach.call(nodes, g); g.bind(obj); frames[0].focus();"],
  ];
  for (const [src, file] of accepted) assert.deepEqual(roads(src, file), [], "accepted: " + src);
  // an onmessage or onmessageerror handler is accepted on this page's own window (a census site the census above holds),
  // with a value that sets no handler, or on a binding that only ever holds a WebSocket; a message listener on this page's
  // own window is a census site, no road
  const handlerOk: Array<[string, string?]> = [
    ["const ws = new WebSocket(u); ws.onmessage = (ev: MessageEvent) => { go(ev.data); };"],
    ["let ws: WebSocket; ws = new WebSocket(u); ws.onmessage = (ev: MessageEvent) => { go(ev.data); };"],
    ["let ws = new WebSocket(u); ws = new WebSocket(u2); ws.onmessage = f;"],
    ["const ws = new window.WebSocket(u); ws.onmessage = f;"],
    ["const ws = new WebSocket(u); ws.onmessage = f; function g() { var ws = window; return ws; }"],
    ["var ws = new WebSocket(u); var ws = new WebSocket(u2); ws.onmessage = f;", "webview/probe.js"],
    ["const dead = c.ws; dead.onopen = dead.onmessage = dead.onclose = dead.onerror = null;"],
    ["document.body.onmessage = null; x.onmessage = undefined; y.onmessageerror = z.onmessage = null;"],
    ["window.onmessageerror = f; document.defaultView.onmessage = g; const w = window; w.onmessage = h;"],
    ["if (port.onmessage) go(); const has = \"onmessage\" in window; type T = { onmessage: ((e: unknown) => void) | null };"],
    ["let t: WebSocket | null = null; type K = typeof WebSocket; const label = \"WebSocket closed\";"],
    ["window.addEventListener(\"messageerror\", f); self.addEventListener(\"message\", g);"],
  ];
  const missed: string[] = [];
  for (const [src, file] of handlerOk) { const got = roads(src, file); if (got.length) missed.push("not accepted: " + src + " (refused for: " + JSON.stringify(got) + ")"); }
  // every other road, each refused for the reason named. A handler on a window other than this page's own, or on a
  // receiver the census resolves to neither this page's window nor a socket, is refused and is no census site
  const OTHER_WINDOW = /handler on a window other than this page's own/;
  const UNRESOLVED = /handler on a receiver the census cannot resolve to this page's window or to a socket/;
  const COMPUTED = /reached by a computed name|destructured by a computed key|with a computed key|from an object with a computed key|run with the window as its this/;
  const byReason: Array<[RegExp, boolean, Array<[string, string?]>]> = [
    // a window other than this page's own, whatever the value
    [OTHER_WINDOW, true, [
      ["frames.onmessage = f;"], ["top.onmessage = f;"], ["parent.onmessage = f;"], ["opener.onmessage = f;"], ["self.parent.onmessage = f;"],
      ["window.frames.onmessage = f;"], ["globalThis.top.onmessage = f;"], ["(window as any).parent.onmessage = f;"], ["(window?.parent).onmessage = f;"],
      ["window!.parent!.onmessage = f;"], ["el.ownerDocument.defaultView.onmessage = f;"], ["frame.contentWindow.onmessage = f;"],
      ["top.document.defaultView.onmessage = f;"], ["const w = self.parent; w.onmessage = f;"], ["var w = frames; w.onmessage = f;"],
      ["const { parent: p } = window; p.onmessage = f;"], ["const { frames: { top: t } } = window; t.onmessage = f;"],
      ["frames[0].onmessage = f;"], ["window[0].onmessage = f;"], ["window[\"1\"].onmessage = f;"], ["parent.frames[0].onmessage = f;"],
      ["window.frames.frames[0].onmessage = f;"], ["fr\\u0061mes.onmessage = f;"], ["top[\"onmessageerror\"] = f;"],
      ["e.target.onmessage = f;"], ["ev.view.onmessage = f;"], ["e.currentTarget.onmessage = f;"], ["e.srcElement.onmessage = f;"],
      ["parent.onmessage = null;"],
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
      // a constructor of the name WebSocket that is not the global one makes no socket (the name is refused below too)
      ["class WebSocket { constructor() { return window; } } const ws = new WebSocket(u); ws.onmessage = f;"],
      ["function g(WebSocket: any) { const ws = new WebSocket(u); ws.onmessage = f; }"],
      // a var of the socket's name declared again in its var scope, or in a for...in or for...of head there
      ["var ws = new WebSocket(u); var ws = window; ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); var ws: any = window; ws.onmessage = f;"],
      ["var ws = new WebSocket(u); for (var ws of [window]) {} ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); for (var ws in o) {} ws.onmessage = f;", "webview/probe.js"],
      ["var ws = new WebSocket(u); { var ws = window; } ws.onmessage = f;", "webview/probe.js"],
      ["function g() { var ws = new WebSocket(u); if (c) { var ws = window; } ws.onmessage = f; }", "webview/probe.js"],
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
    // a member of an indexed window, of the body element or of an event's window member, by a computed name
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
      ["e.view[k] = f;"], ["Reflect.set(e.view, k, f);"], ["Object.assign(ev.view, { [k]: f });"], ["e.target[k] = f;"],
      ["ev.currentTarget[k] = f;"], ["e.srcElement[k] = f;"],
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
  assert.deepEqual(missed, [], "a handler the census accepts refused, a road not refused for its reason, or a refused handler that is a census site:\n" + missed.join("\n"));
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
  const refused = legRefusals(uiSources().flatMap(messageSites).map(key), legs, arms);
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
  // the event's target, currentTarget and srcElement are the receiving window, its view is a window, and a member of its
  // source is a member of the sending window: a read through any of them can run a getter the page defined
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
