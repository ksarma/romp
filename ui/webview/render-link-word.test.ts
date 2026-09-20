// The shell's link word in a split chat column's frame handler (D3, review round 2, 2026-09-18). The shell posts
// {romp:'link', link:'up'|'down', mob} to every iframe outside the six pane frames on its socket's open, close and abandon
// (the tests here drive the link alone; the layout term, mob, is the link block's layout-word arm's, review round 4, kernel-3)
// (kernel.py _LANDING_COLLAPSE_JS tellLink), so a split column's pane shim can end its return await on it. The shim reads
// the word on window itself; render.ts's chat frame handler (the one listenForFrames installs) has nothing to do with it,
// and it is not a kernel message. Before this round the handler had no branch for it, so the word fell through to the
// unconditional retryFailedPreviews() call, and a link-DOWN word made each split column re-fetch its failed previews on a
// path the shell had just declared down. The handler is lifted out of render.ts verbatim, transpiled and executed over
// stubs: every free identifier it reaches resolves to an inert stub except the three heal functions, which count.
// hostUp, the message the heal exists for, still heals once; the panes word (the shell's other post) never did.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

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

type Counts = Record<string, number>;
/** The lifted handler over stubs. Every identifier the handler reaches that is not a real global resolves, through a
 *  `with` scope, to a stub that is callable, has any property (itself) and swallows assignments; the three heal functions
 *  count their calls instead. The handler is sloppy-mode code here (esbuild's transform adds no strict prologue), which
 *  `with` needs. Returns the handler and the counts. */
function handlerOverStubs(): { handle: (m: unknown) => void; calls: Counts } {
  const calls: Counts = { retryFailedPreviews: 0, refreshSettledPreviews: 0, healPathImgs: 0 };
  const stub: any = new Proxy(function () { /* inert */ }, {
    get: (_t, k) => (k === Symbol.toPrimitive ? () => "" : stub),
    apply: () => undefined,
    set: () => true,
  });
  const named: Record<string, unknown> = {
    retryFailedPreviews: () => { calls.retryFailedPreviews++; },
    refreshSettledPreviews: () => { calls.refreshSettledPreviews++; },
    healPathImgs: () => { calls.healPathImgs++; },
  };
  const scope = new Proxy(named, {
    has: (_t, k) => typeof k === "string" && !(k in globalThis),   // real globals (JSON, Object, Map, Array...) stay real
    get: (t, k) => (typeof k !== "string" ? undefined : (k in t ? t[k] : stub)),   // Symbol.unscopables reads undefined, so no name is skipped
    set: (t, k, v) => { if (typeof k === "string") t[k] = v; return true; },
  });
  const code = transpile("const __handler = " + liftHandler() + ";\n");
  const make = new Function("__scope", "with (__scope) {\n" + code + "\nreturn __handler;\n}") as (s: unknown) => (e: { data: unknown }) => void;
  const handler = make(scope);
  return { handle: (m: unknown) => handler({ data: m }), calls };
}

test("the shell's link word, up or down, reaches the chat frame handler and heals nothing: retryFailedPreviews is not called", () => {
  for (const link of ["down", "up"]) {
    const h = handlerOverStubs();
    h.handle({ romp: "link", link });
    assert.equal(h.calls.retryFailedPreviews, 0, "a link-" + link + " word is not a kernel message: no preview retry (before this round it fell through to the heal)");
    assert.equal(h.calls.refreshSettledPreviews, 0);
    assert.equal(h.calls.healPathImgs, 0);
  }
});

test("hostUp still heals once: the per-message retry, the settled chips and the parked path images", () => {
  const h = handlerOverStubs();
  h.handle({ type: "hostUp", hosts: ["TESTHOST"] });
  assert.deepEqual(h.calls, { retryFailedPreviews: 1, refreshSettledPreviews: 1, healPathImgs: 1 });
});

test("the shell's panes word, the other post it makes, heals nothing either (its branch returned before this round too)", () => {
  const h = handlerOverStubs();
  h.handle({ romp: "panes", on: { files: true }, avail: { files: true }, link: "down" });
  assert.equal(h.calls.retryFailedPreviews, 0);
});

test("at source: the link branch sits right after the panes branch and before the heal, and returns after the layout word alone", () => {
  const at = RENDER.indexOf(HEAD);
  const panes = RENDER.indexOf('if (m.romp === "panes") {', at);
  const link = RENDER.indexOf('if (m.romp === "link") {', at);
  const heal = RENDER.indexOf("retryFailedPreviews();", at);
  assert.ok(panes > 0 && link > panes && heal > link, "panes branch, then the link block, then the heal");
  assert.equal(RENDER.slice(at, heal).split('m.romp === "link"').length, 2, "one link branch in the handler");
  const block = RENDER.slice(link, RENDER.indexOf("\n  }\n", link));
  // anchored at BOTH ends (review round 5, tests-3): `block` starts at the `if` keyword itself, so `^` lands on the opening line, and `$`
  // (no m flag) pins `return;` as the last statement; a tail anchor alone let a statement inserted at the block's head pass (a
  // console.log, a try/catch-wrapped parent post in render.ts's own idiom). The same shape file-view.test.ts uses on the panes block.
  assert.match(block, /^if \(m\.romp === "link"\) \{\n\s*if \(typeof m\.mob === "boolean" && onLayoutWord\(skeletonTabs, m\.mob\)[^\n]*schedulePrebuild\(\);[^\n]*\n\s*return;$/, "the block opens on the layout-word arm (review round 4, kernel-3: a split column's hold follows the layout) and returns; nothing else in it, at either end");
});
