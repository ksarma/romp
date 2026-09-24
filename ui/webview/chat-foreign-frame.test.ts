// The chat's frame handler ignores a window message from a foreign sender (window-sender.ts): a window that is not this
// document, not its embedder (the romp shell), not on this document's origin, and not this document's own dispatch of a
// kernel frame. Every other sender is heard as before: the shell's split-column adopt, the file viewer's editorSelection,
// a sibling column's forwarded frames, the kernel's frames, and every message the VS Code webview host forwards from the
// extension. VS Code's script in the webview's frame replaces window.parent with the frame itself (older releases delete
// it), so the host is heard as a window on the webview's origin, a peer, and never as the embedder; the legs below model
// that frame both ways.
// The handler is lifted out of render.ts verbatim, transpiled and executed over stubs: every free identifier it reaches
// resolves to an inert stub except the effect functions below, which count, and windowSender, which is the real helper
// over a stub receiving window (node has no window): W for a chat in the romp shell, or one of the two VS Code frames.
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
const SHELL = { name: "the shell" };
type Win = { parent?: unknown; location: { origin: string } };
const W: Win = { parent: SHELL, location: { origin: ORIGIN } };
// VS Code's webview frame: its origin is the webview's, and VS Code's script there sets window.parent to the frame
// itself, or deletes it in older releases. The host forwards the extension's messages from its own window on that origin.
const VSCODE_ORIGIN = "vscode-webview://11111111-2222-3333-4444-555555555555";
const VSCODE_HOST = { name: "the VS Code webview host" };
const W_VSCODE: Win = { location: { origin: VSCODE_ORIGIN } };
W_VSCODE.parent = W_VSCODE;
const W_VSCODE_OLDER: Win = { location: { origin: VSCODE_ORIGIN } };
type Sent = { source: unknown; origin: string; to?: Win };   // to: the receiving window, W when absent
const HEARD: Record<string, Sent> = {
  self: { source: W, origin: ORIGIN },
  "the embedder (the romp shell)": { source: SHELL, origin: ORIGIN },
  "a peer (a second chat column)": { source: { name: "a second chat column" }, origin: ORIGIN },
  "a peer (the VS Code webview host, the frame's window.parent replaced)": { source: VSCODE_HOST, origin: VSCODE_ORIGIN, to: W_VSCODE },
  "a peer (the VS Code webview host, the frame's window.parent deleted)": { source: VSCODE_HOST, origin: VSCODE_ORIGIN, to: W_VSCODE_OLDER },
  dispatch: { source: null, origin: "" },
};
const FOREIGN: Record<string, Sent> = {
  "a sandboxed frame (opaque origin)": { source: { name: "a sandboxed frame" }, origin: "null" },
  "a page on another origin": { source: { name: "another page" }, origin: "https://example.invalid" },
  "a sandboxed frame inside the VS Code webview": { source: { name: "a sandboxed frame" }, origin: "null", to: W_VSCODE },
};

type Counts = Record<string, number>;
const EFFECTS = ["adoptSessionState", "seedEditorQuote", "upsert", "retryFailedPreviews"];

/** The lifted handler over stubs, with a counter per effect function, receiving as window w. The handler is sloppy-mode
 *  code here (esbuild's transform adds no strict prologue), which `with` needs. */
function handlerOverStubs(w: Win = W): { handle: (data: unknown, from: Sent) => void; calls: Counts } {
  const calls: Counts = {};
  const stub: any = new Proxy(function () { /* inert */ }, {
    get: (_t, k) => (k === Symbol.toPrimitive ? () => "" : stub),
    apply: () => undefined,
    set: () => true,
  });
  const named: Record<string, unknown> = {
    windowSender: (e: { source?: unknown; origin?: unknown }) => windowSender(e, w),
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
