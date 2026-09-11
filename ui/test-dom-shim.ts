// The house fake DOM for the UI tests. One node factory, shared by the sixteen ui/timeline-*.test.ts that build the
// panel on a fake DOM and by ui/webview/tab-color-picker.test.ts (seventeen files at 2026-09-10; the other fourteen
// ui/timeline-*.test.ts fake no DOM), in place of the seventeen near-copies those files carried (the sixteen siblings'
// and the tags-scale test's own: textual variants of one shape, unified 2026-09-10), and taken outright by
// ui/webview/timeline-boot.test.ts. Every other file that fakes a DOM (the 163 ui/webview test files that call
// hideEdges at 2026-09-10, every one in the ratchet's detector's view, which ui/test-dom-shim.test.ts pins) keeps its
// own node classes, window stand-ins or node literals and reaches this module through hideEdges and staysEnumerable,
// so one rule covers them all, through assertHiddenEvent for the pin on its event class where it has one, and through
// sameNodes for its assertions over node lists; this module's own test pins the rule on factory nodes and scratch
// objects, and the two files the ratchet's NON_DOM_EDGES lists reach it through nothing. A factory node is a plain
// object the real TimelinePanel drives:
// children, parentNode, attributes, classList, style, dataset, text, listeners, geometry, focus and the caret. A test
// installs its own fake `document` and window on globalThis around it, as before.
//
// A NODE INSPECTS AS ITS OWN PROJECTION, never as the tree. At creation, hideEdges makes every own property that holds
// an object (children, parentNode, the listener tables, classList, the attribute, style and dataset records, every
// method) and every accessor (firstChild, textContent, scrollTop) non-enumerable, so a fresh node enumerates as its
// primitives alone: the tag, its text, value, caret and scroll offsets, and the serial below. The rule is STRUCTURAL,
// not a key list: an edge the shim grows later (upstream's copy of the tags-scale test gives every node an enumerable
// _ownerDoc and an ownerDocument accessor) is hidden by the same rule, where a key list missed it. null counts as an
// object here, because parentNode starts null and holds a node later, and an assignment to an existing property keeps
// its enumerability. The price is that a failing assertion's dump of a node no longer shows its attributes, style or
// classes; the message the assertion carries is where those belong.
//
// THE SERIAL. hideEdges stamps every node it hides with _nid, an enumerable per-process serial, once: a second call on
// the same node keeps the first. Two projections therefore agree only for the same node, so a deepEqual meant as
// identity FAILS for the wrong node instead of passing on a look-alike (until 2026-09-10 two fresh nodes of one tag were
// deepEqual, and nine assertions across seven webview tests had stopped telling WHICH node came back); a deepEqual of a
// node with itself still passes, and a failing dump grows by one short line. Assert a node list with sameNodes(actual,
// expected, message): the same length and the same node at every index, or one line naming the index and both tags.
//
// WHAT THE RULE DOES NOT REACH. It runs once, at creation, so a property hung on a node AFTERWARDS enumerates, whatever
// its type: the shim's own later write (_sel, from select and setSelectionRange) is defined non-enumerable, but product
// code's are not, and the timeline hangs strings (_key, _tname, _sid), a function (a menu's _build), records (a menu's
// _session, a popover's _anchorAt) and a node (the meta menu's _sub) on nodes it builds. A function inspects as one
// line and a record carries no DOM edge. A node the product decorated dumps its own primitives plus the product's
// references, each of which is itself a node whose edges are hidden, so the dump is bounded by the count of hung
// references (and of theirs, in turn), never by the tree: feed.ts hangs some fifty node references on each card it
// renders (its title, rows, bell and the rest), so a rendered card dumps in about 1.3k lines where a bare node dumps
// in about 25, and the five feed tests pin that bound over a rendered card (under 3,000 lines, no parentNode or
// childNodes key). The projection pins (ui/test-dom-shim.test.ts, and ui/timeline-tags-scale.test.ts over a live
// dialog) and the runner's cgroup cap are the backstop for anything past that, not this rule.
//
// Why: on 2026-09-09 the review's mutation runs of ui/timeline-tags-scale.test.ts grew to 100 GB five times
// before earlyoom killed them. assert/strict's equal and deepEqual build a diff on failure even when given a
// message, inspecting both sides at depth 1000 with getters on; an enumerable parentNode carried that walk up to
// the body and across the whole dialog, the enumerable firstChild getter re-expanded children[0] at every level
// (2^depth), and the diff then ran node's Myers algorithm over the two dumps' lines, which clones an Int32Array
// of 2(N+M)+1 entries per edit-distance level: a 71k-line dump against `null` costs 8N^2 bytes, some 40 GB,
// allocated outside the V8 heap where --max-old-space-size cannot see it. With the projection the same failing
// assertion returns at once with a message of a few lines. ui/timeline-tags-scale.test.ts pins the projection
// over a live dialog at scale; ui/test-dom-shim.test.ts pins the rule, the serial and sameNodes, and keeps a ratchet
// over the other test files' node factories. Compare one node's identity with `a === b` behind a message (the tests'
// `same()` helper) and a node list with sameNodes, never assert.equal or deepEqual: a deepEqual of two nodes compares
// projections, which the serial makes unequal for distinct nodes, but its failure is a diff of two projections;
// sameNodes names the index and both tags and serials instead.
import * as assert from "node:assert/strict";
import { inspect } from "node:util";

export type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };

/** The rect a node reports when nothing else places it: 200 by 20 at the origin. */
export const FLAT_RECT: Rect = { width: 200, height: 20, left: 0, top: 0, right: 200, bottom: 20 };

const g: any = globalThis;

/** True when a value may stay enumerable on a node: a string, number, boolean, bigint or symbol. null and
 *  undefined are placeholders for objects (parentNode starts null), so they hide with the objects. */
export const staysEnumerable = (v: unknown): boolean => v != null && typeof v !== "object" && typeof v !== "function";

let serial = 0;

/** Every own enumerable property of `n` that holds an object, an array, a function, null or undefined, and
 *  every accessor, becomes non-enumerable; primitives stay. First, `n` gets `_nid`, the serial, if it has none:
 *  an enumerable number that tells its projection from every other node's. Idempotent (a second call hides
 *  nothing new and keeps the serial). Returns `n`. */
export function hideEdges<T extends object>(n: T): T {
  if (!Object.prototype.hasOwnProperty.call(n, "_nid")) (n as any)._nid = ++serial;
  for (const k of Object.keys(n)) {
    const d = Object.getOwnPropertyDescriptor(n, k)!;
    if (!("value" in d) || !staysEnumerable(d.value)) Object.defineProperty(n, k, { enumerable: false });
  }
  return n;
}

/** A node's tag and serial for a message: `DIV#12` (tagName, tag or nodeName, else the class name), or the value
 *  itself when it is not an object. */
export function describeNode(n: unknown): string {
  if (n === null || typeof n !== "object") return String(n);
  const o = n as any;
  const tag = o.tagName ?? o.tag ?? o.nodeName ?? (o.constructor && o.constructor.name) ?? "object";
  return typeof o._nid === "number" ? String(tag) + "#" + o._nid : String(tag);
}

/** Asserts that `actual` holds the same nodes as `expected`, by identity and in order: the same length, and `===`
 *  at every index. On failure the AssertionError carries `message` and one line naming the index and both sides'
 *  tags and serials, never a dump of either list. This is the assertion for a node list where a deepEqual once
 *  stood: two distinct nodes are not deepEqual either (the serial), but that failure is a diff of two projections
 *  where this one says which node came back and where. */
export function sameNodes(actual: ArrayLike<unknown> | null | undefined, expected: ArrayLike<unknown>, message: string): void {
  if (!actual) assert.fail(message + ": no node list, got " + String(actual) + " where " + expected.length + " nodes were expected");
  if (actual.length !== expected.length) assert.fail(message + ": " + actual.length + " nodes where " + expected.length + " were expected");
  for (let i = 0; i < expected.length; i++) {
    if (actual[i] !== expected[i]) assert.fail(message + ": index " + i + " is another node: got " + describeNode(actual[i]) + ", expected " + describeNode(expected[i]));
  }
}

// node's assert inspects the two sides of a failed strict assertion with these options (lib/internal/assert/
// assertion_error.js, inspectValue) before it diffs them line by line; assertHiddenEvent dumps with the same ones
const ASSERT_INSPECT = { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true };

/** Asserts that an event-shaped object hides its `target` and `currentTarget` the way a node hides its edges: assigns
 *  `target` and `currentTarget` (two nodes from the calling test's own tree), then requires each to be an own
 *  NON-ENUMERABLE property and the event's assert-style dump to name neither key. This is the executed check on an Ev
 *  class whose constructor ends in hideEdges(this): with the call removed, the two null-initialised fields enumerate,
 *  dispatch's later writes fill them with nodes, and a failing assertion over the event dumps the tree through them.
 *  Every assertion here carries a primitive-valued message, so the pin itself never dumps a node. */
export function assertHiddenEvent(ev: object, target: unknown, currentTarget: unknown): void {
  const e = ev as any;
  e.target = target; e.currentTarget = currentTarget;
  for (const k of ["target", "currentTarget"]) {
    const d = Object.getOwnPropertyDescriptor(e, k);
    assert.ok(d !== undefined && d.enumerable === false, k + " is an own, non-enumerable property of the event (hideEdges(this) at the end of the Ev constructor); enumerable: " + String(d ? d.enumerable : "no own property"));
  }
  const dump = inspect(e, ASSERT_INSPECT);
  assert.ok(!dump.includes("target"), "the event's dump names no target or currentTarget: " + dump.split("\n").length + " lines");
  assert.ok(e.target === target && e.currentTarget === currentTarget, "the two nodes are still reachable through the hidden properties");
}

/** Defines `k` on `n` as a non-enumerable own property, writable and configurable (so a later write or define still
 *  lands): the shim's own writes after construction go through here, so they do not re-open the projection. */
export function defineHidden<T extends object>(n: T, k: string, v: unknown): T {
  Object.defineProperty(n, k, { value: v, writable: true, configurable: true, enumerable: false });
  return n;
}

export interface ShimOptions {
  /** The rect every node reports from getBoundingClientRect unless the node carries its own `_rect` or the
   *  module-level `globalThis.__rectOf(node)` hook answers for it. Default FLAT_RECT. */
  rect?: Rect;
}

/** The node factory: `const makeNode = nodeFactory({ rect })`, then `makeNode("div")`. */
export function nodeFactory(opts: ShimOptions = {}): (tag: string) => any {
  const rect: Rect = opts.rect || FLAT_RECT;
  function makeNode(tag: string): any {
    const n: any = {
      tag, _attrs: {}, children: [] as any[], style: {}, dataset: {}, _text: "", parentNode: null, value: "",
      // the DOM's setter REPLACES the children: the builders clear a container with `textContent = ''` before
      // repainting it, and a fake that kept the children let post-rebuild assertions match stale nodes. The
      // getter is the node's OWN text; the tests' textOf helpers add the children's
      get textContent() { return n._text; },
      set textContent(v: any) { n._text = v == null ? "" : String(v); for (const c of n.children) c.parentNode = null; n.children.length = 0; },
      classList: { _s: new Set<string>(), add(...a: string[]) { a.forEach((c) => this._s.add(c)); },
        remove(...a: string[]) { a.forEach((c) => this._s.delete(c)); },
        toggle(c: string, f?: boolean) { f ? this._s.add(c) : this._s.delete(c); }, contains(c: string) { return this._s.has(c); } },
      setAttribute(k: string, v: any) { n._attrs[k] = v; }, getAttribute(k: string) { return n._attrs[k]; },
      setAttributeNS(_ns: any, k: string, v: any) { n._attrs[k] = v; }, removeAttribute(k: string) { delete n._attrs[k]; },
      // real-DOM semantics: appending an attached node MOVES it (a menu created on the body is re-appended to
      // its host; the dialog's popover moves between documents)
      appendChild(c: any) {
        if (c.parentNode) { const i = c.parentNode.children.indexOf(c); if (i >= 0) c.parentNode.children.splice(i, 1); }
        c.parentNode = n; n.children.push(c); return c;
      },
      insertBefore(c: any, ref: any) { c.parentNode = n; const i = n.children.indexOf(ref); i < 0 ? n.children.push(c) : n.children.splice(i, 0, c); return c; },
      removeChild(c: any) { const i = n.children.indexOf(c); if (i >= 0) { n.children.splice(i, 1); c.parentNode = null; } return c; },
      get firstChild() { return n.children[0] || null; },
      remove() { if (n.parentNode) n.parentNode.removeChild(n); },
      // `_listeners[t]` is the listener added LAST and still registered, `_stacks[t]` every one in order. Removal
      // is by function, so a listener hung under another for a while (the drag's scroll re-rank under the
      // popover's scroll closer) gives the slot back to the one that stays when it comes down
      _listeners: {} as any, _stacks: {} as any,
      addEventListener(t: string, fn: any) { (n._stacks[t] = n._stacks[t] || []).push(fn); n._listeners[t] = fn; },
      removeEventListener(t: string, fn?: any) {
        const a = n._stacks[t] || []; const i = fn ? a.indexOf(fn) : a.length - 1;
        if (i >= 0) a.splice(i, 1);
        if (a.length) n._listeners[t] = a[a.length - 1]; else delete n._listeners[t];
      },
      setPointerCapture() {}, releasePointerCapture() {},
      querySelector() { return null; }, querySelectorAll() { return []; }, closest() { return null; },
      // geometry is a test input: the node's own `_rect`, else the module-level `globalThis.__rectOf(node)` hook
      // (so a test can move a row without holding the node a rebuild replaces), else the factory's one rect
      getBoundingClientRect() { return n._rect || (g.__rectOf ? g.__rectOf(n) : null) || { ...rect }; },
      // scrollTop clamps to `globalThis.__scrollMax` (Infinity unless a test says the box no longer scrolls), as a
      // browser clamps a write on a box whose content fits
      _scrollTop: 0,
      get scrollTop() { return n._scrollTop; },
      set scrollTop(v: any) { const max = g.__scrollMax == null ? Infinity : g.__scrollMax; n._scrollTop = Math.max(0, Math.min(Number(v) || 0, max)); },
      // focus and the caret are OBSERVABLE: focus records the active element on the fake document, once a test
      // has installed one; select() and setSelectionRange() record the selection in _sel, the one property the shim
      // itself adds after construction, defined non-enumerable so the projection holds
      focus() { if (g.document) g.document.activeElement = n; },
      select() { defineHidden(n, "_sel", "all"); n.selectionStart = 0; n.selectionEnd = String(n.value || "").length; },
      setSelectionRange(a: number, b: number) { defineHidden(n, "_sel", [a, b]); n.selectionStart = a; n.selectionEnd = b; },
      selectionStart: 0, selectionEnd: 0,
      createEl(t: string, o: any) { const e = makeNode(t); if (o && o.cls) e.classList.add(o.cls); if (o && o.text) e.textContent = o.text; n.appendChild(e); return e; },
      createDiv(o: any) { return n.createEl("div", o); }, createSpan(o: any) { return n.createEl("span", o); },
    };
    return hideEdges(n);
  }
  return makeNode;
}
