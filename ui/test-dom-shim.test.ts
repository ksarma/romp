// The shared fake-DOM shim's PROJECTION RULE, pinned on its own (ui/test-dom-shim.ts; ui/timeline-tags-scale.test.ts
// pins it over a live dialog at scale), and a RATCHET over the other UI test files: a test file that fakes a DOM with
// enumerable edges (parentNode, parent, childNodes, children, a child or sibling pointer, ownerDocument or host as a
// plain enumerable property) either builds its nodes with the shared shim or is named on the allowlist below, which
// may not grow past ALLOWLIST_MAX (lowered as files migrate): a renamed file replaces its entry, a new file may not
// join. The rule hides the edges at CREATION: a property product code hangs on a node later enumerates, whatever its
// type, and a node-valued one re-opens a path for a failing dump to walk; the projection pins here and in the
// tags-scale test, plus the runner's cgroup cap, are the backstop for that. Source pins over ui/**/*.test.ts, the
// repo convention. Why both: on 2026-09-09 a failing strict assertion with a fake node on one side allocated tens of
// GB (node's assert dumps both sides at depth 1000 with getters on, then diffs the dumps with a Myers trace that
// costs 8N^2 bytes outside the V8 heap); the projection is what stops it, and every other enumerable-edge shim in
// the tree can still do it (a feed card in ui/webview/feed-keynav-covered.test.ts dumps as 318,835 lines).
// Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inspect } from "node:util";
import { nodeFactory, hideEdges, staysEnumerable, FLAT_RECT } from "./test-dom-shim";

// node's assert inspects the two sides of a failed strict assertion with these options
// (lib/internal/assert/assertion_error.js, inspectValue) before it diffs them line by line
const ASSERT_INSPECT = { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true };
const makeNode = nodeFactory();
const same = (a: any, b: any, msg = "the same node") => assert.ok(a === b, msg);
const lines = (s: string) => s.split("\n").length;

// ── the rule ─────────────────────────────────────────────────────────────────────────────────────────

test("a fresh node enumerates its primitives alone; the edges, records, methods and accessors are non-enumerable and still reachable", () => {
  const n = makeNode("div");
  for (const k of Object.keys(n)) assert.ok(staysEnumerable(n[k]), k + " is enumerable and holds a " + typeof n[k]);
  assert.deepEqual(Object.keys(n).sort(), ["_scrollTop", "_text", "selectionEnd", "selectionStart", "tag", "value"], "the projection");
  for (const k of ["children", "parentNode", "_attrs", "style", "dataset", "classList", "_listeners", "_stacks", "appendChild", "getBoundingClientRect", "firstChild", "textContent", "scrollTop"]) {
    const d = Object.getOwnPropertyDescriptor(n, k);
    assert.ok(d && d.enumerable === false, k + " is an own, non-enumerable property");
  }
  // reachable as before: the tree, the text, the classes, the attributes
  const c = n.createDiv({ cls: "row", text: "alpha" });
  same(c.parentNode, n); same(n.firstChild, c); same(n.children[0], c);
  assert.equal(c.textContent, "alpha"); assert.ok(c.classList.contains("row"));
  c.setAttribute("role", "button"); assert.equal(c.getAttribute("role"), "button"); assert.equal(c._attrs.role, "button");
  // a parentNode assigned AFTER construction keeps the attribute: an assignment to an existing property changes its value only
  assert.equal(Object.getOwnPropertyDescriptor(c, "parentNode")!.enumerable, false);
  assert.ok(!inspect(c, ASSERT_INSPECT).includes("parentNode"), "a child's dump does not climb to its parent");
});

test("the rule on a bare object: objects, arrays, functions, null, undefined and accessors hide; strings, numbers, booleans stay; twice is the same", () => {
  const o: any = { s: "x", i: 1, b: true, z: null, u: undefined, r: {}, l: [], f() { return 1; }, get acc() { return 2; } };
  hideEdges(o);
  assert.deepEqual(Object.keys(o).sort(), ["b", "i", "s"]);
  hideEdges(o);
  assert.deepEqual(Object.keys(o).sort(), ["b", "i", "s"], "idempotent");
  assert.equal(o.f(), 1); assert.equal(o.acc, 2); assert.deepEqual(o.l, []); assert.equal(o.z, null);
  assert.deepEqual([staysEnumerable("a"), staysEnumerable(0), staysEnumerable(false), staysEnumerable(10n), staysEnumerable(Symbol("s"))], [true, true, true, true, true]);
  assert.deepEqual([staysEnumerable(null), staysEnumerable(undefined), staysEnumerable({}), staysEnumerable([]), staysEnumerable(() => 0)], [false, false, false, false, false]);
});

test("after construction: a property product code hangs on a node enumerates whatever its type, and stays bounded on its own; the shim's own later write (_sel) does not", () => {
  const n = makeNode("div"), other = makeNode("span");
  n._key = "k"; n._build = () => 0; n._session = { name: "web", tags: ["a", "b"] }; n._sub = other;
  for (const k of ["_key", "_build", "_session", "_sub"]) assert.equal(Object.getOwnPropertyDescriptor(n, k)!.enumerable, true, k + " enumerates: the rule ran at creation, not on this write");
  // bounded on their own: a function is one line, the record carries no DOM edge, the hung node is its own projection
  const dump = inspect(n, ASSERT_INSPECT);
  assert.ok(lines(dump) <= 40, "the node with four hung properties inspects in " + lines(dump) + " lines");
  assert.ok(!dump.includes("parentNode") && !dump.includes("children"), "the hung node brought no edge into the dump");
  // the caret: select() and setSelectionRange() write _sel after construction, in either order, and it never enumerates
  for (const order of [["select", "range"], ["range", "select"]]) {
    const m = makeNode("input"); m.value = "hello";
    for (const step of order) step === "select" ? m.select() : m.setSelectionRange(1, 2);
    const d = Object.getOwnPropertyDescriptor(m, "_sel")!;
    assert.ok(d && d.enumerable === false && d.writable && d.configurable, order.join(" then ") + ": _sel is an own, non-enumerable, writable property");
    assert.deepEqual(Object.keys(m).sort(), ["_scrollTop", "_text", "selectionEnd", "selectionStart", "tag", "value"], order.join(" then ") + ": the projection is unchanged");
  }
});

test("a failing assertion on a node in a deep chain-first tree returns a short message; a deepEqual of two nodes compares projections", () => {
  // depth 24 along first children with five siblings at every level: the shape whose dump passed util.inspect's
  // 2^27-character budget at depth 17 before the rule (the first-child getter re-expanded children[0] per level)
  const root = makeNode("div"); let cur = root;
  for (let d = 0; d < 24; d++) { const next = cur.createDiv({}); for (let i = 0; i < 5; i++) cur.createSpan({ text: "s" + i }); cur = next; }
  const leaf = cur;
  for (const [what, n] of [["the root", root], ["the leaf", leaf]] as const) assert.ok(lines(inspect(n, ASSERT_INSPECT)) <= 20, what + " inspects in " + lines(inspect(n, ASSERT_INSPECT)) + " lines");
  // node's failing diff carries the whole dump in its message, so the message's line count bounds the work the diff
  // did; time follows from size, and no clock is asserted
  for (const [what, n] of [["the root", root], ["the leaf", leaf]] as const) {
    let msg = ""; try { assert.equal(n, null, "a node against null"); } catch (e: any) { msg = String(e.message); }
    assert.ok(msg && lines(msg) <= 40, what + " against null: a short message, got " + lines(msg) + " lines");
  }
  // two fresh nodes are deepEqual, their projections agree: node identity is compared with ===, behind a message
  assert.deepEqual(makeNode("div"), makeNode("div"));
  assert.ok(makeNode("div") !== makeNode("div"));
});

test("the factory: the rect (the node's own, then the module hook, then the factory's), the scroll clamp, focus, the caret, the listener stack, the DOM's move and replace semantics", () => {
  const g: any = globalThis;
  const wide = { width: 1400, height: 420, left: 0, top: 0, right: 1400, bottom: 420 };
  const mk = nodeFactory({ rect: wide });
  const n = mk("div");
  assert.deepEqual(n.getBoundingClientRect(), wide); assert.ok(n.getBoundingClientRect() !== wide, "a copy per call");
  assert.deepEqual(makeNode("div").getBoundingClientRect(), FLAT_RECT, "the default factory: the flat rect");
  n._rect = { width: 10, height: 10, left: 1, top: 1, right: 11, bottom: 11 }; assert.deepEqual(n.getBoundingClientRect(), n._rect, "the node's own rect first");
  const m = mk("div");
  g.__rectOf = (x: any) => (x === m ? { width: 5, height: 5, left: 0, top: 0, right: 5, bottom: 5 } : null);
  try {
    assert.equal(m.getBoundingClientRect().width, 5, "the module hook answers for a node");
    assert.equal(mk("div").getBoundingClientRect().width, 1400, "...and the factory's rect stands where it does not");
  } finally { g.__rectOf = null; }
  // the scroll clamp
  n.scrollTop = 500; assert.equal(n.scrollTop, 500); n.scrollTop = -3; assert.equal(n.scrollTop, 0);
  g.__scrollMax = 50; try { n.scrollTop = 500; assert.equal(n.scrollTop, 50, "clamped to the box"); } finally { g.__scrollMax = null; }
  // focus records on the fake document once a test has installed one; without one it is a no-op
  const had = g.document; delete g.document;
  try {
    n.focus();
    const doc: any = { activeElement: null }; g.document = doc; n.focus(); same(doc.activeElement, n, "focus is observable");
  } finally { if (had === undefined) delete g.document; else g.document = had; }
  // the caret
  n.value = "hello"; n.select(); assert.equal(n._sel, "all"); assert.deepEqual([n.selectionStart, n.selectionEnd], [0, 5]);
  n.setSelectionRange(2, 3); assert.deepEqual(n._sel, [2, 3]); assert.deepEqual([n.selectionStart, n.selectionEnd], [2, 3]);
  assert.equal(Object.getOwnPropertyDescriptor(n, "_sel")!.enumerable, false, "_sel, the shim's own write after construction, is non-enumerable");
  // listeners: the last one registered holds the slot, and the one under it takes it back when the top comes down
  const a = () => 0, b = () => 1;
  n.addEventListener("scroll", a); n.addEventListener("scroll", b); same(n._listeners.scroll, b); assert.deepEqual(n._stacks.scroll, [a, b]);
  n.removeEventListener("scroll", b); same(n._listeners.scroll, a); n.removeEventListener("scroll", a); assert.equal(n._listeners.scroll, undefined);
  // appendChild MOVES an attached node; the textContent setter REPLACES the children; removeChild detaches
  const p = mk("div"), q = mk("div"); const c = p.createSpan({ text: "x" });
  q.appendChild(c); same(c.parentNode, q); assert.equal(p.children.length, 0); assert.equal(q.children.length, 1);
  q.textContent = "gone"; assert.equal(q.children.length, 0); assert.equal(c.parentNode, null); assert.equal(q.textContent, "gone");
  const r = q.createSpan({}); q.removeChild(r); assert.equal(r.parentNode, null); assert.equal(q.children.length, 0);
  const s = q.createSpan({}); s.remove(); assert.equal(s.parentNode, null); assert.equal(q.children.length, 0);
});

// ── the ratchet ──────────────────────────────────────────────────────────────────────────────────────

const UI = path.resolve(process.cwd(), "..", "ui");   // npm test runs in vscode-extension/
const testFiles = (): string[] => {
  const out: string[] = [];
  for (const d of ["", "webview"]) for (const f of fs.readdirSync(path.join(UI, d)).sort()) if (f.endsWith(".test.ts")) out.push(d ? d + "/" + f : f);
  return out;
};
const src = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
/** A file FAKES A DOM WITH ENUMERABLE EDGES when it initialises an edge (parentNode, parent, childNodes, children,
 *  firstChild, lastChild, nextSibling, previousSibling, ownerDocument or host) as an own enumerable property in any of
 *  these shapes, with null, undefined, [], this or a bare identifier as the value, and fakes a DOM at all (appendChild,
 *  nodeType or tagName somewhere in it): a goal tree's empty children list is a data fixture, not a node, and a list
 *  model with no DOM vocabulary is not one either. EDGE stands for an edge name below, so this file's own text
 *  initialises none:
 *  - an object-literal key (`{ EDGE: null, EDGE: [] }`, `{ EDGE: kid }`). With an identifier value the key host is
 *    left out: an object-literal `host:` in this tree is the payload field naming a machine, which the source pins
 *    over the renderer quote;
 *  - a class field, with any modifier or none (public, private, protected, readonly, declare, override), typed or
 *    not, anywhere on a line (`tag = "x"; private EDGE: N | null = null;`);
 *  - a constructor parameter property (`constructor(public EDGE: N[] = [])`, with or without a default);
 *  - an assignment through any name (`this.EDGE = null`, `n.EDGE = []`, `c.EDGE = p`).
 *  Out of scope, by design: an edge under another name (a `kids` list), a field declared without an initialiser
 *  (`EDGE?: N;` is no own property until assigned, which the assignment shape then sees), a shorthand key
 *  (`{ EDGE }`), and a value that is a member expression, a call or a `new` (`c.EDGE = this.host`). The class-field
 *  shape cannot tell a field from a statement assigning a same-named local at line start; the DOM-vocabulary condition
 *  and the allowlist are the check on that. */
const KEY = "(parentNode|parent|childNodes|children|firstChild|lastChild|nextSibling|previousSibling|ownerDocument|host)";
const KEY_NOT_HOST = KEY.replace("|host", "");
const MODS = "(?:(?:public|private|protected|readonly|declare|override)\\s+)";
const NOT_KEYWORD = "(?!(?:string|number|boolean|any|unknown|never|void|object|symbol|bigint|new|typeof|await|function|async|class|yield|delete|in|instanceof)\\b)";
const NOT_CONTINUED = "\\b(?!\\s*[\\[<|&.(])";   // not a type continuation (Kid[], Map<, | null, & X) and not a member or call
const IDENT = NOT_KEYWORD + "[A-Za-z_$][\\w$]*" + NOT_CONTINUED;                  // a bare name as a value, after =
const IDENT_LOWER = NOT_KEYWORD + "[a-z_$][\\w$]*" + NOT_CONTINUED;               // as an object-literal value, where a capitalised name reads as a type in a type literal
const VALUE = "(?:null\\b|undefined\\b|\\[\\]|this\\b|" + IDENT + ")";
const EDGE_INIT: Record<string, RegExp> = {
  "object-literal key": new RegExp("[{,]\\s*" + KEY + "\\s*:\\s*(?:null\\b|undefined\\b|\\[\\])"),
  "object-literal key, identifier value": new RegExp("[{,]\\s*" + KEY_NOT_HOST + "\\s*:\\s*(?:this\\b|" + IDENT_LOWER + ")"),
  "class field": new RegExp("(?:^|[;{])\\s*" + MODS + "*" + KEY + "\\s*(?::[^=;\\n]+)?=\\s*" + VALUE, "m"),
  "parameter property": new RegExp("[(,]\\s*" + MODS + "+" + KEY + "\\b"),
  "assignment": new RegExp("\\b[A-Za-z_$][\\w$]*\\." + KEY + "\\s*=\\s*" + VALUE),
};
const FAKES_DOM = /appendChild|nodeType|tagName/;
const USES_SHIM = /from "(\.\.\/|\.\/)test-dom-shim"/;
/** The names of the shapes `s` initialises an edge in; empty when none. */
const edgeShapes = (s: string): string[] => Object.keys(EDGE_INIT).filter((k) => EDGE_INIT[k].test(s));
const fakesEdges = (s: string) => FAKES_DOM.test(s) && edgeShapes(s).length > 0;

// The test files still faking a DOM with enumerable edges on 2026-09-10, each named, so the list can only shrink: a
// file that moves to the shared shim (or hides its edges the same way) comes off it and ALLOWLIST_MAX comes down with
// it; a renamed file replaces its entry; a new file may not join. The webview shims are class-based (El and Txt,
// FakeNode, E, FakeEl, Elm) with a prototype firstChild, so no 2^depth term, but the whole-tree walk through parentNode
// (parent in codex-meta-choices and track-decorations, the latter with an ownerDocument too) remains, and feed.ts hangs
// node references on cards. file-view and pdf-new-tab stand in a window whose parent is another window stand-in, the
// same walk one level up. Their fix is Object.defineProperty(this, "parentNode", { enumerable: false }) (and the other
// edges) in the constructors, or hideEdges from the shared module at the end of each, plus a projection test.
const ALLOWLIST = [
  "webview/anchor-map-block-edges.test.ts",
  "webview/anchor-map-boundary-points.test.ts",
  "webview/anchor-map-change-marks.test.ts",
  "webview/anchor-map-fallback-markup.test.ts",
  "webview/anchor-map-rendered-points.test.ts",
  "webview/anchor-map-wrapped-code.test.ts",
  "webview/anchor-map.test.ts",
  "webview/chat-exact-tail-exec.test.ts",
  "webview/codex-meta-choices.test.ts",
  "webview/feed-keynav-click-focus.test.ts",
  "webview/feed-keynav-covered.test.ts",
  "webview/feed-keynav-tabscope-covered.test.ts",
  "webview/feed-keynav-typing.test.ts",
  "webview/feed-render-incremental.test.ts",
  "webview/file-comments-anchors-unsure-rendered.test.ts",
  "webview/file-comments-anchors-unsure.test.ts",
  "webview/file-comments-anchors.test.ts",
  "webview/file-comments-arrivals-fixes.test.ts",
  "webview/file-comments-arrivals-review2.test.ts",
  "webview/file-comments-arrivals.test.ts",
  "webview/file-comments-behavior.test.ts",
  "webview/file-comments-changes-review.test.ts",
  "webview/file-comments-changes-review2.test.ts",
  "webview/file-comments-changes-review3.test.ts",
  "webview/file-comments-changes.test.ts",
  "webview/file-comments-composer-chat-nav-chord.test.ts",
  "webview/file-comments-composer-fixes.test.ts",
  "webview/file-comments-composer-review.test.ts",
  "webview/file-comments-composer-shell-chord.test.ts",
  "webview/file-comments-composer.test.ts",
  "webview/file-comments-crop-keep.test.ts",
  "webview/file-comments-crop-wait.test.ts",
  "webview/file-comments-editing-cards.test.ts",
  "webview/file-comments-editing-landed.test.ts",
  "webview/file-comments-editing-moved-latch.test.ts",
  "webview/file-comments-editing-races.test.ts",
  "webview/file-comments-editing-round3.test.ts",
  "webview/file-comments-figure-page.test.ts",
  "webview/file-comments-filter-fixes.test.ts",
  "webview/file-comments-filter-review.test.ts",
  "webview/file-comments-filter-saved-line.test.ts",
  "webview/file-comments-filter.test.ts",
  "webview/file-comments-focus-audit.test.ts",
  "webview/file-comments-focus-review.test.ts",
  "webview/file-comments-focus-verify-2.test.ts",
  "webview/file-comments-focus-verify.test.ts",
  "webview/file-comments-focus.test.ts",
  "webview/file-comments-follow.test.ts",
  "webview/file-comments-inline-review.test.ts",
  "webview/file-comments-inline-toggle.test.ts",
  "webview/file-comments-margin-fixes.test.ts",
  "webview/file-comments-margin-image-pad.test.ts",
  "webview/file-comments-margin-review.test.ts",
  "webview/file-comments-margin.test.ts",
  "webview/file-comments-page-states.test.ts",
  "webview/file-comments-pages.test.ts",
  "webview/file-comments-panel.test.ts",
  "webview/file-comments-pdf-pictures.test.ts",
  "webview/file-comments-region-tied.test.ts",
  "webview/file-comments-regions-click.test.ts",
  "webview/file-comments-regions-guards.test.ts",
  "webview/file-comments-regions-press-scroll.test.ts",
  "webview/file-comments-regions-press.test.ts",
  "webview/file-comments-regions-repaint.test.ts",
  "webview/file-comments-regions-review-2.test.ts",
  "webview/file-comments-regions-review-3.test.ts",
  "webview/file-comments-regions-review-4.test.ts",
  "webview/file-comments-regions-review.test.ts",
  "webview/file-comments-regions-sizer.test.ts",
  "webview/file-comments-regions-stacking.test.ts",
  "webview/file-comments-regions.test.ts",
  "webview/file-comments-reply-keep.test.ts",
  "webview/file-comments-reply-move.test.ts",
  "webview/file-comments-reply-place.test.ts",
  "webview/file-comments-reply-review2.test.ts",
  "webview/file-comments-reveal-arms-focus.test.ts",
  "webview/file-comments-reveal-landing.test.ts",
  "webview/file-comments-reveal-one-pass.test.ts",
  "webview/file-comments-reveal-title.test.ts",
  "webview/file-comments-review-fixes-3.test.ts",
  "webview/file-comments-review-fixes.test.ts",
  "webview/file-comments-send-note.test.ts",
  "webview/file-comments-send-resolves.test.ts",
  "webview/file-comments-todo-choices-review.test.ts",
  "webview/file-comments-todo-choices.test.ts",
  "webview/file-comments-todopick-focus.test.ts",
  "webview/file-comments.test.ts",
  "webview/file-view-edit-events.test.ts",
  "webview/file-view-edit-races.test.ts",
  "webview/file-view-figures-absolute.test.ts",
  "webview/file-view-links.test.ts",
  "webview/file-view-pdf-backstop.test.ts",
  "webview/file-view-pdf-chunk-latch.test.ts",
  "webview/file-view-pdf-frame.test.ts",
  "webview/file-view-pdf-lifecycle.test.ts",
  "webview/file-view-pdf-page-error.test.ts",
  "webview/file-view-pdf.test.ts",
  "webview/file-view-place-blocks.test.ts",
  "webview/file-view-place-comment-blocks.test.ts",
  "webview/file-view-place-source-cache.test.ts",
  "webview/file-view-place.test.ts",
  "webview/file-view-reload.test.ts",
  "webview/file-view-seam.test.ts",
  "webview/file-view-text-size.test.ts",
  "webview/file-view-tracked-edit.test.ts",
  "webview/file-view-undo-landed-ack.test.ts",
  "webview/file-view-undo-landed.test.ts",
  "webview/file-view.test.ts",
  "webview/fileview-chip.test.ts",
  "webview/fleet-live-clock.test.ts",
  "webview/github-link.test.ts",
  "webview/path-links-pointer-focus.test.ts",
  "webview/path-links.test.ts",
  "webview/pdf-chunk-abort.test.ts",
  "webview/pdf-chunk-dropped-images.test.ts",
  "webview/pdf-chunk-evict-inflight.test.ts",
  "webview/pdf-chunk-page-cap.test.ts",
  "webview/pdf-chunk-page-cue.test.ts",
  "webview/pdf-chunk-refused-open.test.ts",
  "webview/pdf-chunk-resize.test.ts",
  "webview/pdf-chunk-staged-draw.test.ts",
  "webview/pdf-chunk.test.ts",
  "webview/pdf-lazy-render.test.ts",
  "webview/pdf-new-tab.test.ts",
  "webview/pinned-notes.test.ts",
  "webview/pr-links.test.ts",
  "webview/render-todo-file-chip.test.ts",
  "webview/setting-stale-fold.test.ts",
  "webview/strip.test.ts",
  "webview/tab-row-keep.test.ts",
  "webview/tab-strip-skip-exec.test.ts",
  "webview/timeline-boot.test.ts",
  "webview/track-decorations-guards.test.ts",
  "webview/track-decorations-kept-embed.test.ts",
  "webview/track-decorations.test.ts",
  "webview/url-links.test.ts",
  "webview/user-todo-links.test.ts",
  "webview/user-todo-title-links.test.ts",
  "webview/waiting-detail-link.test.ts",
  "webview/waiting-file-chip-unframed.test.ts",
  "webview/waiting-file-chip.test.ts",
];
// The list's ceiling: its length on 2026-09-10, after the detector's second round. Lower it when a file comes off; the
// ratchet refuses a longer list, so from here the list can only shrink.
const ALLOWLIST_MAX = 141;
// the sixteen files on the shared module (2026-09-10): the fifteen whose near-copies of the shim it replaced, and the
// tags-scale test whose shim it grew from
const SWITCHED = [
  "timeline-hidden-hold.test.ts", "timeline-hidden-stub.test.ts", "timeline-kernel-post.test.ts", "timeline-live-tick.test.ts",
  "timeline-nan-window.test.ts", "timeline-open-interval.test.ts", "timeline-pending-hosts.test.ts", "timeline-render.test.ts",
  "timeline-tagbtn-click.test.ts", "timeline-tagorder-drag.test.ts", "timeline-tags-scale.test.ts", "timeline-theme-light.test.ts",
  "timeline-transform-tick.test.ts", "timeline-views-ack.test.ts", "timeline-zoom-anchor.test.ts", "webview/tab-color-picker.test.ts",
];

test("ratchet: every UI test file that fakes a DOM with enumerable edges is on the allowlist, every allowlisted file still does, and the list has not grown", () => {
  const files = testFiles();
  assert.ok(files.includes("test-dom-shim.test.ts") && files.includes("webview/tab-color-picker.test.ts"), "the sweep covers ui/ and ui/webview/");
  const matching = files.filter((f) => fakesEdges(src(f)));
  assert.deepEqual(matching.filter((f) => !ALLOWLIST.includes(f)), [],
    "a UI test file fakes a DOM with an enumerable edge (parentNode, parent, children, childNodes, a child or sibling pointer, ownerDocument or host): " +
    "build its nodes with ui/test-dom-shim.ts (nodeFactory), or hide the edges the same way (hideEdges); the allowlist may not grow. A renamed file " +
    "that was on the list replaces its old entry; a new file may not join (a failing assertion on such a node can allocate tens of GB)");
  assert.deepEqual(ALLOWLIST.filter((f) => !matching.includes(f)), [], "an allowlisted file no longer fakes a DOM with enumerable edges, or is gone: take it off the list and lower ALLOWLIST_MAX");
  assert.ok(ALLOWLIST.length <= ALLOWLIST_MAX, "the allowlist holds " + ALLOWLIST.length + " files, above its ceiling of " + ALLOWLIST_MAX + ": the list may not grow");
  assert.deepEqual(ALLOWLIST, ALLOWLIST.slice().sort(), "the allowlist is sorted, so a change to it reads as one line");
  assert.equal(new Set(ALLOWLIST).size, ALLOWLIST.length, "no name twice");
});

test("the files that carried the shim's copies import the shared module and keep no node factory of their own; no importer fakes edges beside it", () => {
  for (const f of SWITCHED) {
    const s = src(f);
    assert.ok(USES_SHIM.test(s), f + " imports test-dom-shim");
    assert.ok(!/^function makeNode\(/m.test(s), f + " defines no makeNode of its own");
    assert.ok(!fakesEdges(s), f + " initialises no enumerable edge");
  }
  for (const f of testFiles()) if (USES_SHIM.test(src(f))) assert.ok(!fakesEdges(src(f)), f + " imports the shim and still fakes a DOM with enumerable edges");
  assert.ok(!fakesEdges(src("test-dom-shim.test.ts")), "this file does not trip its own rule");
});

// ── the detector, on scratch sources ────────────────────────────────────────────────────────────────
// Each shape the rule names, as positives (trip) and near-miss negatives (do not). EDGE stands in for an edge name so
// this file's own text initialises none; every scratch source carries DOM vocabulary unless the case is about that.
const scratch = (s: string, edge: string) => s.replace(/EDGE/g, edge);
const POSITIVE: Array<[string, string, string]> = [   // [the shape it must trip, scratch source, edge name]
  ["object-literal key", "const n = { tagName: 'DIV', EDGE: null, x: 1 };", "parentNode"],
  ["object-literal key", "const n = { EDGE: [], appendChild() {} };", "children"],
  ["object-literal key", "const n = {\n  nodeType: 1,\n  EDGE: undefined,\n};", "nextSibling"],
  ["object-literal key, identifier value", "const n = { EDGE: kid, nodeType: 1 };", "firstChild"],
  ["object-literal key, identifier value", "const n = { tagName: 'DIV', EDGE: doc };", "ownerDocument"],
  ["object-literal key, identifier value", "function mk(p) { return { EDGE: p, appendChild() {} }; }", "parent"],
  ["object-literal key, identifier value", "class N { child() { return { EDGE: this, nodeType: 1 }; } }", "parentNode"],
  ["class field", "class N {\n  EDGE: N[] = [];\n  appendChild() {}\n}", "children"],
  ["class field", "class N { tag = 'x'; private EDGE: N | null = null; appendChild() {} }", "parentNode"],
  ["class field", "class N {\n  public readonly EDGE: N[] = [];\n  nodeType = 1;\n}", "childNodes"],
  ["class field", "class N {\n  protected EDGE: N | null = null;\n  tagName = 'DIV';\n}", "parent"],
  ["class field", "class N {\n  override EDGE: N | null = null;\n  appendChild() {}\n}", "lastChild"],
  ["class field", "class N {\n  EDGE: N | null = BODY;\n  appendChild() {}\n}", "previousSibling"],
  ["class field", "class N {\n  EDGE = null;\n  appendChild() {}\n}", "host"],
  ["parameter property", "class N { constructor(private EDGE: N[] = []) {} appendChild() {} }", "children"],
  ["parameter property", "class N {\n  constructor(public readonly EDGE: N | null, m: Map<string, N> = new Map()) {}\n  appendChild() {}\n}", "parentNode"],
  ["parameter property", "class N { constructor(readonly EDGE: N) {} nodeType = 1; }", "ownerDocument"],
  ["assignment", "class N { constructor() { this.EDGE = null; } appendChild() {} }", "parentNode"],
  ["assignment", "function N(p) { this.EDGE = p; this.appendChild = () => 0; }", "parent"],
  ["assignment", "function mk() { const n: any = {}; n.EDGE = []; n.appendChild = () => 0; return n; }", "children"],
  ["assignment", "const attach = (c, p) => { c.EDGE = p; p.kids.push(c); c.nodeType = 1; };", "parentNode"],
  ["assignment", "root.EDGE = doc; root.tagName = 'HTML';", "ownerDocument"],
  ["assignment", "shadow.EDGE = el; shadow.appendChild(el);", "host"],
];
const NEGATIVE: Array<[string, string, string]> = [   // [what it is, scratch source, edge name]
  ["a data fixture with no DOM vocabulary", "const goal = { title: 'x', EDGE: [] };", "children"],
  ["a comparison, not an assignment", "if (n.EDGE === null) n.appendChild(c); if (m.EDGE == null) return;", "parentNode"],
  ["a type literal", "type N = { EDGE: N | null; kids: N[] };\nconst tagName = 'DIV';", "parent"],
  ["a type literal with comma separators", "type N = { EDGE: N, tagName: string };", "parent"],
  ["a type literal keyed on a primitive", "type Row = { EDGE: string; nodeType: number };", "host"],
  ["a plain parameter default, no modifier", "function mk(EDGE = [], tagName = 'div') { return { tagName }; }", "children"],
  ["an arrow parameter", "const f = (EDGE) => EDGE.appendChild(x);", "children"],
  ["a static field", "class N { static EDGE: N[] = []; appendChild() {} }", "children"],
  ["a member-expression value (out of scope)", "up.EDGE = g.document; up.appendChild(x);", "ownerDocument"],
  ["a constructed value (out of scope)", "class N { EDGE = new Doc(); appendChild() {} }", "ownerDocument"],
  ["a hidden define", "Object.defineProperty(this, 'EDGE', { value: null, enumerable: false }); this.appendChild(c);", "parentNode"],
  ["a length reset", "n.EDGE.length = 0; n.appendChild(c);", "children"],
  ["the shared shim", "import { nodeFactory } from './test-dom-shim';\nconst makeNode = nodeFactory();\nmakeNode('div').appendChild(makeNode('span'));", "parentNode"],
  ["a source pin quoting the payload field", "assert.match(RENDER, /openThing\\(\\{ name, host: hostOf\\(sid\\) \\}\\)/); el.appendChild(c);", "host"],
  ["a payload literal naming a machine", "const lane = { host: h, sid, appendChild: 0 };", "host"],
];
test("the detector: each shape trips on a scratch source, and its near-misses do not", () => {
  for (const [shape, src, edge] of POSITIVE) {
    const shapes = edgeShapes(scratch(src, edge));
    assert.ok(shapes.includes(shape), shape + " (" + edge + ") trips on " + JSON.stringify(src) + "; got " + JSON.stringify(shapes));
    assert.ok(fakesEdges(scratch(src, edge)), shape + " (" + edge + "): the source fakes a DOM with enumerable edges");
  }
  for (const [what, src, edge] of NEGATIVE) assert.ok(!fakesEdges(scratch(src, edge)), what + " does not trip: " + JSON.stringify(src) + "; matched " + JSON.stringify(edgeShapes(scratch(src, edge))));
  const fixture = scratch("const goal = { title: 'x', EDGE: [] };", "children");
  assert.deepEqual(edgeShapes(fixture), ["object-literal key"], "the data fixture initialises an edge; the DOM-vocabulary condition is what spares it");
  assert.equal(Object.keys(EDGE_INIT).length, 5, "five shapes, each with a positive above");
  for (const shape of Object.keys(EDGE_INIT)) assert.ok(POSITIVE.some(([s]) => s === shape), shape + " has a positive case");
});
