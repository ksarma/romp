// The house fake DOM for the timeline tests: one node factory, shared by the fifteen ui/timeline-*.test.ts that build
// the panel on a fake DOM and by ui/webview/tab-color-picker.test.ts (sixteen files at 2026-09-10; the other fourteen
// ui/timeline-*.test.ts fake no DOM), in place of the sixteen near-copies those files carried (the fifteen siblings'
// and the tags-scale test's own: nine textual variants of one shape, unified 2026-09-10). A node is a plain object the
// real TimelinePanel drives: children, parentNode, attributes, classList, style, dataset, text, listeners, geometry,
// focus and the caret. A test installs its own fake `document` and window on globalThis around it, as before.
//
// A NODE INSPECTS AS ITS OWN PROJECTION, never as the tree. At creation, hideEdges makes every own property that holds
// an object (children, parentNode, the listener tables, classList, the attribute, style and dataset records, every
// method) and every accessor (firstChild, textContent, scrollTop) non-enumerable, so a fresh node enumerates as its
// primitives alone: the tag, its text, value, caret and scroll offsets. The rule is STRUCTURAL, not a key list: an
// edge the shim grows later (upstream's copy of the tags-scale test gives every node an enumerable _ownerDoc and an
// ownerDocument accessor) is hidden by the same rule, where a key list missed it. null counts as an object here,
// because parentNode starts null and holds a node later, and an assignment to an existing property keeps its
// enumerability. The rule runs once, at creation, so a property hung on a node AFTERWARDS enumerates, whatever its
// type: the shim's own later write (_sel, from select and setSelectionRange) is defined non-enumerable, but product
// code's are not, and the timeline hangs strings (_key, _tname, _sid), a function (a menu's _build), records (a menu's
// _session, a popover's _anchorAt) and a node (the meta menu's _sub) on nodes it builds. A function inspects as one
// line and a record carries no DOM edge, but a node-valued property re-opens a path for a failing dump to walk; the
// projection pins (ui/test-dom-shim.test.ts, and ui/timeline-tags-scale.test.ts over a live dialog) and the runner's
// cgroup cap are the backstop for that, not this rule. The price is that a failing assertion's dump of a node no
// longer shows its attributes, style or classes; the message the assertion carries is where those belong.
//
// Why: on 2026-09-09 the review's mutation runs of ui/timeline-tags-scale.test.ts grew to 100 GB five times
// before earlyoom killed them. assert/strict's equal and deepEqual build a diff on failure even when given a
// message, inspecting both sides at depth 1000 with getters on; an enumerable parentNode carried that walk up to
// the body and across the whole dialog, the enumerable firstChild getter re-expanded children[0] at every level
// (2^depth), and the diff then ran node's Myers algorithm over the two dumps' lines, which clones an Int32Array
// of 2(N+M)+1 entries per edit-distance level: a 71k-line dump against `null` costs 8N^2 bytes, some 40 GB,
// allocated outside the V8 heap where --max-old-space-size cannot see it. With the projection the same failing
// assertion returns at once with a message of a few lines. ui/timeline-tags-scale.test.ts pins the projection
// over a live dialog at scale; ui/test-dom-shim.test.ts pins the rule itself and keeps a ratchet over the other
// test files' node factories. Compare node IDENTITY with `a === b` behind a message (the tests' `same()`
// helper), never assert.equal: a deepEqual of two nodes compares projections now, not trees.

export type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };

/** The rect a node reports when nothing else places it: 200 by 20 at the origin. */
export const FLAT_RECT: Rect = { width: 200, height: 20, left: 0, top: 0, right: 200, bottom: 20 };

const g: any = globalThis;

/** True when a value may stay enumerable on a node: a string, number, boolean, bigint or symbol. null and
 *  undefined are placeholders for objects (parentNode starts null), so they hide with the objects. */
export const staysEnumerable = (v: unknown): boolean => v != null && typeof v !== "object" && typeof v !== "function";

/** Every own enumerable property of `n` that holds an object, an array, a function, null or undefined, and
 *  every accessor, becomes non-enumerable; primitives stay. Idempotent. Returns `n`. */
export function hideEdges<T extends object>(n: T): T {
  for (const k of Object.keys(n)) {
    const d = Object.getOwnPropertyDescriptor(n, k)!;
    if (!("value" in d) || !staysEnumerable(d.value)) Object.defineProperty(n, k, { enumerable: false });
  }
  return n;
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
