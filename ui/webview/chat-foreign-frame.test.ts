// The chat's frame handler ignores a window message from a foreign sender (window-sender.ts): a window that is not this
// document, not its embedder (the romp shell), not on this document's origin, and not this document's own dispatch of a
// kernel frame. A message with no source that carries an origin is not dispatch: a frame removed right after it posts
// can leave its message sourceless, so such a message is judged by its origin alone. Every other sender is heard as
// before: the shell's split-column adopt, the file viewer's editorSelection, a sibling column's forwarded frames, the
// kernel's frames, and every message the VS Code webview host forwards from the extension. VS Code's script in the
// webview's frame replaces window.parent with the frame itself (older releases delete it), so the host is heard as a
// window on the webview's origin, a peer, and never as the embedder; the legs below model that frame both ways.
// The handler is lifted out of render.ts verbatim, transpiled and executed over stubs: every free identifier it reaches
// resolves to an inert stub except the effect functions below, which count, windowSender, which is the real helper, and
// window and location (node has neither), which are the receiving window the leg models and its location: W for a chat
// in the romp shell, or one of the two VS Code frames. windowSender reads that same window, so a check the handler
// spells with window or location sees the window the helper sees. Any other name read on those stand-ins is the stub.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { windowSender } from "./window-sender";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));   // esbuild from the extension, wherever this bundle was written
const UI = path.resolve(EXT, "..", "ui", "webview");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const HEAD = 'listenForFrames(perfFrameHandler("chat", (m) => vscodeApi?.postMessage(m), ';

function transpile(src: string): string { return requireCjs("esbuild").transformSync(src, { loader: "ts", target: "es2020" }).code; }

/** The chat's frame handler as render.ts spells it: the arrow function listenForFrames installs, from its parameter list to
 *  its closing brace. */
function liftHandler(): string {
  const at = RENDER.indexOf(HEAD);
  assert.ok(at > 0, "anchor not found: render.ts's chat frame listener moved; re-anchor");
  const start = at + HEAD.length;
  const end = RENDER.indexOf("\n}));\n", start);
  assert.ok(end > start, "the listener's closing `}));` not found");
  return RENDER.slice(start, end + 2);
}

const SID = "11111111-2222-3333-4444-555555555555";
const ORIGIN = "http://127.0.0.1:1";
/** The inert stub every unbound free identifier of the lifted handler resolves to: any read on it is the stub again, a
 *  call returns undefined, a write is dropped. */
const stub: any = new Proxy(function () { /* inert */ }, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => "" : stub),
  apply: () => undefined,
  set: () => true,
});
/** A stand-in built on a Proxy: the keys it is given are real, and any other name read on it is the stub, so the handler
 *  can call window.requestAnimationFrame on a receiving window while its parent and location stay the modelled ones. */
function standIn<T extends object>(o: T): T {
  return new Proxy(o, { get: (t, k) => (typeof k === "string" && !(k in t) ? stub : Reflect.get(t, k)) });
}
const SHELL = standIn({ name: "the shell" });
type Win = { parent?: unknown; location: { origin: string } };
const W: Win = standIn({ parent: SHELL, location: standIn({ origin: ORIGIN }) });
// VS Code's webview frame: its origin is the webview's, and VS Code's script there sets window.parent to the frame
// itself, or deletes it in older releases (then window.parent reads undefined). The host forwards the extension's
// messages from its own window on that origin.
const VSCODE_ORIGIN = "vscode-webview://11111111-2222-3333-4444-555555555555";
const VSCODE_HOST = { name: "the VS Code webview host" };
const W_VSCODE: Win = standIn({ location: standIn({ origin: VSCODE_ORIGIN }) });
W_VSCODE.parent = W_VSCODE;
const W_VSCODE_OLDER: Win = standIn({ parent: undefined, location: standIn({ origin: VSCODE_ORIGIN }) });
type Sent = { source: unknown; origin: string; to?: Win };   // to: the receiving window, W when absent
const HEARD: Record<string, Sent> = {
  self: { source: W, origin: ORIGIN },
  "the embedder (the romp shell)": { source: SHELL, origin: ORIGIN },
  "a peer (a second chat column)": { source: { name: "a second chat column" }, origin: ORIGIN },
  "a peer (the VS Code webview host, the frame's window.parent replaced)": { source: VSCODE_HOST, origin: VSCODE_ORIGIN, to: W_VSCODE },
  "a peer (the VS Code webview host, the frame's window.parent deleted)": { source: VSCODE_HOST, origin: VSCODE_ORIGIN, to: W_VSCODE_OLDER },
  "a peer (a sourceless post on this document's origin)": { source: null, origin: ORIGIN },
  dispatch: { source: null, origin: "" },
};
const FOREIGN: Record<string, Sent> = {
  // a sandboxed pane beside the chat in the romp shell: its parent is the chat's parent
  "a sandboxed frame (opaque origin)": { source: { name: "a sandboxed frame", parent: SHELL }, origin: "null" },
  "a page on another origin": { source: { name: "another page" }, origin: "https://example.invalid" },
  "a sandboxed frame inside the VS Code webview": { source: { name: "a sandboxed frame" }, origin: "null", to: W_VSCODE },
  // a frame removed right after it posts can leave its message with no source; its origin is still set
  "a sandboxed frame that is gone (no source, opaque origin)": { source: null, origin: "null" },
  "a page on another origin that is gone (no source)": { source: null, origin: "https://example.invalid" },
  "a sandboxed frame inside the VS Code webview that is gone (no source)": { source: null, origin: "null", to: W_VSCODE },
};

type Counts = Record<string, number>;
const EFFECTS = ["adoptSessionState", "seedEditorQuote", "upsert", "retryFailedPreviews"];

/** The lifted handler over stubs, with a counter per effect function, receiving as window w: the handler's window and
 *  location are w and w.location, the objects windowSender reads. The handler is sloppy-mode code here (esbuild's
 *  transform adds no strict prologue), which `with` needs. */
function handlerOverStubs(w: Win = W): { handle: (data: unknown, from: Sent) => void; calls: Counts } {
  const calls: Counts = {};
  const named: Record<string, unknown> = {
    windowSender: (e: { source?: unknown; origin?: unknown }) => windowSender(e, w),
    window: w,
    location: w.location,
  };
  for (const f of EFFECTS) { calls[f] = 0; named[f] = () => { calls[f]++; }; }
  const scope = new Proxy(named, {
    has: (_t, k) => typeof k === "string" && !(k in globalThis),   // real globals (JSON, Object, Map, Array...) stay real
    get: (t, k) => (typeof k !== "string" ? undefined : (k in t ? t[k] : stub)),   // Symbol.unscopables reads undefined, so no name is skipped
    set: (t, k, v) => { if (typeof k === "string") t[k] = v; return true; },
  });
  const code = transpile("const __handler = " + liftHandler() + ";\n");
  const make = new Function("__scope", "with (__scope) {\n" + code + "\nreturn __handler;\n}") as (s: unknown) => (e: unknown) => void;
  const handler = make(scope);
  return { handle: (data: unknown, from: Sent) => handler({ data, source: from.source, origin: from.origin }), calls };
}

const LEGS: { what: string; data: Record<string, unknown>; effect: string }[] = [
  { what: "the shell's split-column adopt", data: { romp: "adopt", sid: SID, state: { draft: "a draft" } }, effect: "adoptSessionState" },
  { what: "an editor selection", data: { type: "editorSelection", sid: SID, text: "the auth check", src: "src/app.py:12" }, effect: "seedEditorQuote" },
  { what: "a kernel-shaped session frame", data: { type: "session", id: SID, host: "TESTHOST", name: "web" }, effect: "upsert" },
];

for (const leg of LEGS) {
  test(leg.what + " from a foreign sender is ignored: " + leg.effect + " is not called and nothing else in the handler runs", () => {
    for (const [who, from] of Object.entries(FOREIGN)) {
      const h = handlerOverStubs(from.to);
      h.handle(leg.data, from);
      assert.equal(h.calls[leg.effect], 0, leg.what + " from " + who + " reached " + leg.effect);
      assert.equal(h.calls.retryFailedPreviews, 0, "the handler returned at its head for " + who + ", before the preview heal");
    }
  });

  test(leg.what + " from this document, the romp shell, a same-origin window (a second chat column or the VS Code webview host) or this document's dispatch is heard: " + leg.effect + " is called once", () => {
    const missed: string[] = [];   // every heard sender that did not reach the effect once, so a narrowed floor names them all
    for (const [who, from] of Object.entries(HEARD)) {
      const h = handlerOverStubs(from.to);
      h.handle(leg.data, from);
      if (h.calls[leg.effect] !== 1) missed.push(who + " (" + h.calls[leg.effect] + " calls)");
    }
    assert.deepEqual(missed, [], leg.what + " must reach " + leg.effect + " once from each heard sender; it did not from: " + missed.join("; "));
  });
}

test("at source: the foreign-sender return is the handler's first check after the empty-message return", () => {
  // Where the line sits, not what it does: the executed legs above are the proof that a foreign sender reaches nothing.
  const at = RENDER.indexOf(HEAD);
  assert.ok(at > 0);
  const head = RENDER.slice(at + HEAD.length, at + HEAD.length + 200);
  assert.ok(head.startsWith('(e: MessageEvent) => {\n  const m = e.data;\n  if (!m) return;\n  if (windowSender(e) === "foreign") return;'),
    "the chat handler's head is: read e.data, return on an empty message, return on a foreign sender");
  assert.match(RENDER, /\nimport \{ windowSender \} from "\.\/window-sender";\n/);
});
