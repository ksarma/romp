// The chat's math arrival and the queued group's cached node (render.ts onMathSettled and renderPendingGroup), executed in node:
// the group's node is cached per session and rebuilt only when its signature changes, so a node built while a formula in it
// waited for the math renderer, and DETACHED when the renderer landed, kept the waiting formula: the fill over the document
// never reaches a detached node, and its next render found the same signature. The arrival handler clears the signature of
// every cached node that holds a waiting formula, or the source a failed load left (math.ts mathPendingIn, mathFailedIn), so the
// next render rebuilds its children with the renderer in. An attached node is filled in place by the fill over the document and
// passes without that line, which is why the node here is detached (the review of iOS item 6, round 1, tests-5: no test reached
// the line). The two functions are lifted from render.ts's source and run over a stand-in node; the predicates are math.ts's own.
// Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { mathPendingIn, mathFailedIn } from "./math";
import { hideEdges, staysEnumerable } from "../test-dom-shim";

const EXT = process.cwd();                                               // npm test runs in vscode-extension
const RENDER = fs.readFileSync(path.resolve(EXT, "..", "ui", "webview", "render.ts"), "utf8");
const requireCjs = createRequire(path.join(EXT, "package.json"));

/** render.ts from `start` through the first `end` after it, both included. */
function lift(start: string, end: string): string {
  const a = RENDER.indexOf(start);
  const b = a < 0 ? -1 : RENDER.indexOf(end, a);
  assert.ok(a >= 0 && b > a, "render.ts no longer holds " + JSON.stringify(start.slice(0, 60)) + " (re-anchor the lift)");
  return RENDER.slice(a, b + end.length);
}
const GROUP = lift("const pendingGroupNode = new Map<string, { sig: string; node: HTMLElement }>();", "\n  return fresh;\n}\n");
const HANDLER = lift('onMathSettled(() => {\n  const content = document.getElementById("content");', "\n  };\n});\n");

/** A stand-in for the group's node: its children are kinds ("waiting", a placeholder; "failed", a failed load's fallback; "laid",
 *  KaTeX's layout), and querySelector answers the two selectors math.ts's predicates ask. Never connected: the case under test. */
type Kid = { kind: "waiting" | "failed" | "laid" };
function node(kind: Kid["kind"]): { className: string; isConnected: boolean; childNodes: Kid[]; replaceChildren: (...k: Kid[]) => void; querySelector: (sel: string) => Kid | null; querySelectorAll: (sel: string) => Kid[] } {
  return hideEdges({   // the edges hide (ui/test-dom-shim.ts): a failing assertion dumps the node's primitives, never its children
    className: "turn turn-queued", isConnected: false, childNodes: [{ kind }],
    replaceChildren(...k: Kid[]) { this.childNodes = k; },
    querySelector(sel: string) {
      const want = sel.includes("md-math-inline") ? "waiting" : sel.includes("data-math-failed") ? "failed" : null;
      return this.childNodes.find((c) => c.kind === want) || null;
    },
    querySelectorAll() { return []; },   // no comment mark and no source block for the after-callback's two passes to visit
  });
}

/** The lifted pair over a prelude standing in for the chat state they read: the chat views `views` (none by default: the scene is
 *  the group's node alone), no #content (so no view is on screen), and renderQueued building a node of the kind the renderer's
 *  state gives; `marked()` lists the sessions the after-callback ran the comment marks pass for. */
function harness(views: Map<string, { el: unknown; lineMoved?: boolean }> = new Map()) {
  const prelude = `
    let renderingSid = "web"; let activeId = "web";
    const views = env.views;
    const document = { getElementById: () => null };
    const atBottom = () => false, captureReadingAnchor = () => null, restoreReadingLine = () => false, restoreScrollAnchor = () => {}, writeScroll = () => {};
    const marked = []; const applyCommentMarks = (sid) => { marked.push(sid); }, unwrapCommentMark = () => {}, addCopyBtn = () => {};
    let handler = null; const onMathSettled = (h) => { handler = h; return () => {}; };
    let kind = "waiting"; const renderQueued = () => env.node(kind);
    const mathPendingIn = env.mathPendingIn, mathFailedIn = env.mathFailedIn;
  `;
  const tail = `
    return { renderPendingGroup, pendingGroupNode, setKind: (k) => { kind = k; }, settle: () => { const after = handler(); if (typeof after === "function") after(); }, marked: () => marked.slice() };
  `;
  const js = requireCjs("esbuild").transformSync(prelude + GROUP + HANDLER + tail, { loader: "ts", target: "es2020" }).code;
  return new Function("env", js)({ node, mathPendingIn, mathFailedIn, views }) as {
    renderPendingGroup: (ev: unknown) => ReturnType<typeof node>; pendingGroupNode: Map<string, { sig: string }>;
    setKind: (k: Kid["kind"]) => void; settle: () => void; marked: () => string[];
  };
}

const EV = { kind: "queued", texts: [{ md: "the ratio $\\frac{a}{b}$ again", lost: false, qts: 1 }], held: null };

for (const before of ["waiting", "failed"] as const) {
  test(`a queued group's cached node that held ${before === "waiting" ? "a formula waiting for the renderer" : "the source a failed load left"}, detached when the renderer landed, is rebuilt at its next render with the formula laid out`, () => {
    const h = harness();
    h.setKind(before);
    const first = h.renderPendingGroup(EV);
    assert.deepEqual(first.childNodes, [{ kind: before }], "built while the renderer was out");
    h.setKind("laid");                                   // the renderer is in: a fresh render lays the formula out
    h.settle();                                          // the arrival, with the node detached (no chat view holds it)
    assert.equal(h.pendingGroupNode.get("web")!.sig, "", "the arrival marked the group changed");
    const next = h.renderPendingGroup(EV);               // the same group, unchanged: the same signature as before
    assert.equal(next, first, "the cached node is kept (the one element the scroll geometry rests on)");
    assert.deepEqual(next.childNodes, [{ kind: "laid" }], "and its children rebuilt with the renderer in");
  });
}

test("the instrument: without an arrival the same group's next render keeps the cached children (the signature is unchanged)", () => {
  const h = harness();
  const first = h.renderPendingGroup(EV);
  h.setKind("laid");
  const next = h.renderPendingGroup(EV);
  assert.equal(next, first);
  assert.deepEqual(next.childNodes, [{ kind: "waiting" }], "an unchanged signature reuses the node's children: the arrival's mark is what rebuilds them");
});

test("a cached node with no formula of either kind is left alone by the arrival", () => {
  const h = harness();
  h.setKind("laid");
  h.renderPendingGroup(EV);
  const sig = h.pendingGroupNode.get("web")!.sig;
  h.settle();
  assert.equal(h.pendingGroupNode.get("web")!.sig, sig, "nothing to lay out: the signature stands");
});

test("a chat view holding only the source a failed load left counts, at a later success, as one that held a waiting formula: a view not on screen is marked to land its reader's line at its next show, and its comment marks go back over the laid-out text; a view with neither is left alone", () => {
  const views = new Map<string, { el: unknown; lineMoved?: boolean }>([["web", { el: node("failed"), lineMoved: false }], ["api", { el: node("laid"), lineMoved: false }]]);
  const h = harness(views);
  h.settle();
  assert.deepEqual([views.get("web")!.lineMoved, views.get("api")!.lineMoved], [true, false], "the success lays the failure's sources out in place, unseen in a hidden view: its next show lands the line (landActive)");
  assert.deepEqual(h.marked(), ["web"], "the marks pass runs for the view the arrival laid out, and only for it");
});

test("a tab left while it holds the source a failed load left keeps its reader's line, as one left while a formula waits does (render.ts setActive; a source pin: no node test executes setActive's capture half, and the served hidden-tab case runs it over waiting formulas)", () => {
  assert.match(RENDER, /cur\.leaveLine = !cur\.stick && content\.clientHeight > 0 && cur\.el\.style\.display !== "none" && \(mathPendingIn\(cur\.el\) \|\| mathFailedIn\(cur\.el\)\) \? captureReadingAnchor\(content, cur\) : null;/,
    "setActive captures the leaving tab's line over the failure's sources as well as over waiting formulas, so a success that lands while the tab is hidden is landed by the line at the next show");
});

test("the stand-in node enumerates its primitives alone: its children hide (ui/test-dom-shim.ts), so a failing assertion dumps a node, not the tree", () => {
  const n = node("waiting");
  assert.ok(Object.keys(n).every((k) => staysEnumerable((n as any)[k])), "every enumerable key holds a primitive: " + Object.keys(n).join(","));
  assert.ok(!Object.keys(n).includes("childNodes"), "the children are hidden");
  assert.deepEqual(n.childNodes, [{ kind: "waiting" }], "and still reachable");
});
