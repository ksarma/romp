// The shared fake-DOM shim's PROJECTION RULE, pinned on its own (ui/test-dom-shim.ts; ui/timeline-tags-scale.test.ts
// pins it over a live dialog at scale) with the SERIAL that tells two projections apart and sameNodes, the assertion
// over a node list, and a RATCHET over the other UI test files, one rule for every file under ui/: a test file whose
// CODE initialises an edge-named property (parentNode, parentElement, parent, childNodes, children, firstChild,
// lastChild, nextSibling, previousSibling, ownerDocument or host) as a plain enumerable own property, in any shape
// the detector below reads (comments and the contents of string, template and regex literals are blanked first, so a
// source pin or a comment is not code), either CALLS hideEdges( or nodeFactory( imported from the shared shim (a named
// or a namespace import, either quote style on the specifier, with or without .js; an import without a call in code
// is not switched), or is named on one of the two lists below, each pinned to its exact length by a constant:
// ALLOWLIST, the unmigrated fakes, empty since 2026-09-10 and never to grow (a file that comes off lowers the constant
// in the same commit, a new file may not join), and NON_DOM_EDGES, the files whose edge-named key is a documented
// non-DOM use (a data fixture, a list model), each with its reason and the count of edge-initialising lines the
// detector reads in it, pinned so a fake that grows in a listed file trips. There is no
// vocabulary gate: a window stand-in's parent, a goal fixture's children and a class's parentNode are the same kind
// of property to a regex, a failing dump walks each, and the cure for a fake is the same one-line call. The rule hides
// the edges at CREATION: a property product code hangs on a node later enumerates, whatever its type, and a
// node-valued one re-opens a path for a failing dump to walk; the projection pins here and in the tags-scale test,
// plus the runner's cgroup cap, are the backstop for that. Source pins over ui/**/*.test.ts, the repo convention. Why
// both: on 2026-09-09 a failing strict assertion with a fake node on one side allocated tens of GB (node's assert
// dumps both sides at depth 1000 with getters on, then diffs the dumps with a Myers trace that costs 8N^2 bytes
// outside the V8 heap); the projection is what stops it, and until 2026-09-10 every other enumerable-edge fake in the
// tree could still do it (a feed card in ui/webview/feed-keynav-covered.test.ts dumped as 318,835 lines; at this head
// it dumps in about 1,300, bounded by feed.ts's hung references, and the five feed tests pin the bound under 3,000).
// The paragraph above ALLOWLIST is the one account of the migration.
// Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inspect } from "node:util";
import { nodeFactory, hideEdges, staysEnumerable, sameNodes, describeNode, FLAT_RECT } from "./test-dom-shim";

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
  assert.deepEqual(Object.keys(n).sort(), ["_nid", "_scrollTop", "_text", "selectionEnd", "selectionStart", "tag", "value"], "the projection");
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
  assert.deepEqual(Object.keys(o).sort(), ["_nid", "b", "i", "s"], "the primitives, and the serial the call stamped");
  const nid = o._nid;
  hideEdges(o);
  assert.deepEqual(Object.keys(o).sort(), ["_nid", "b", "i", "s"], "idempotent");
  assert.equal(o._nid, nid, "the second call keeps the serial");
  assert.equal(o.f(), 1); assert.equal(o.acc, 2); assert.deepEqual(o.l, []); assert.equal(o.z, null);
  assert.deepEqual([staysEnumerable("a"), staysEnumerable(0), staysEnumerable(false), staysEnumerable(10n), staysEnumerable(Symbol("s"))], [true, true, true, true, true]);
  assert.deepEqual([staysEnumerable(null), staysEnumerable(undefined), staysEnumerable({}), staysEnumerable([]), staysEnumerable(() => 0)], [false, false, false, false, false]);
});

test("an event-shaped object: hideEdges hides target and currentTarget (null at construction, nodes after dispatch), the primitives stay, and a dump of the event names no node", () => {
  // the shape the webview tests' Ev classes take: target and currentTarget start null, and dispatch assigns nodes later
  class Ev { target: any = null; currentTarget: any = null; defaultPrevented = false; key: string; constructor(public type: string, init: { key?: string } = {}) { this.key = init.key || ""; hideEdges(this); } }
  const ev = new Ev("keydown", { key: "Enter" });
  assert.deepEqual(Object.keys(ev).sort(), ["_nid", "defaultPrevented", "key", "type"], "the primitives and the serial");
  const root = makeNode("div"), n = root.createDiv({ text: "x" });
  ev.target = n; ev.currentTarget = root;   // dispatch's later writes to existing properties keep them non-enumerable
  for (const k of ["target", "currentTarget"]) assert.equal(Object.getOwnPropertyDescriptor(ev, k)!.enumerable, false, k + " is an own, non-enumerable property");
  same(ev.target, n); same(ev.currentTarget, root);
  const dump = inspect(ev, ASSERT_INSPECT);
  assert.ok(!dump.includes("target") && !dump.includes("tag:") && lines(dump) <= 12, "the event dumps its own primitives alone, got:\n" + dump);
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
    assert.deepEqual(Object.keys(m).sort(), ["_nid", "_scrollTop", "_text", "selectionEnd", "selectionStart", "tag", "value"], order.join(" then ") + ": the projection is unchanged");
  }
});

test("a failing assertion on a node in a deep chain-first tree returns a short message; a deepEqual of two nodes compares projections, which the serial tells apart", () => {
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
  // two fresh nodes are NOT deepEqual: their projections differ in the serial (until 2026-09-10 they agreed, and a
  // deepEqual meant as identity passed for any node of the tag). A node is deepEqual to itself; identity is still ===
  const a = makeNode("div"), b = makeNode("div");
  assert.notDeepEqual(a, b, "two fresh nodes of one tag project differently");
  assert.deepEqual(a, a);
  assert.ok(a !== b);
  let msg = ""; try { assert.deepEqual(a, b); } catch (e: any) { msg = String(e.message); }
  assert.ok(msg.includes("_nid") && lines(msg) <= 40, "the failing deepEqual names the serial in a short diff, got " + lines(msg) + " lines");
});

test("the serial: every node hideEdges touches carries an enumerable, distinct, increasing _nid, stamped once; sameNodes asserts a node list by identity with a one-line message", () => {
  const nodes = [makeNode("div"), makeNode("span"), makeNode("div")];
  for (const n of nodes) assert.ok(typeof n._nid === "number" && Object.getOwnPropertyDescriptor(n, "_nid")!.enumerable, "an enumerable number");
  assert.ok(nodes[0]._nid < nodes[1]._nid && nodes[1]._nid < nodes[2]._nid, "increasing in creation order");
  assert.equal(new Set(nodes.map((n) => n._nid)).size, 3, "distinct");
  const kid = nodes[0].createDiv({}); assert.ok(kid._nid > nodes[2]._nid, "a child made later has a later serial");
  // the class idiom the webview tests use: a constructor that defines its edges non-enumerable and ends in hideEdges(this),
  // and a subclass constructor that calls it again; the node gets one serial, from the first call. The edges here are
  // named up and kids, not by their DOM names, so this file does not trip its own ratchet (the scratch sources use EDGE)
  class El { up!: El | null; kids: El[]; tagName: string; constructor(tag: string) { this.tagName = tag; this.kids = []; Object.defineProperty(this, "up", { value: null, writable: true, enumerable: false, configurable: true }); hideEdges(this); } }
  class Txt extends El { data: string; constructor(d: string) { super("#text"); this.data = d; hideEdges(this); } }
  const t = new Txt("x"), e = new El("div");
  assert.deepEqual(Object.keys(t).sort(), ["_nid", "data", "tagName"], "the subclass's own field stays, its edges hide, one serial");
  assert.ok((t as any)._nid !== undefined && (t as any)._nid < (e as any)._nid, "stamped in the base constructor's call, kept by the subclass's");
  assert.notDeepEqual(new El("div"), new El("div"), "two class nodes of one tag are not deepEqual either");
  // describeNode: tag and serial, for messages
  assert.equal(describeNode(e), "div#" + (e as any)._nid); assert.equal(describeNode(nodes[1]), "span#" + nodes[1]._nid);
  assert.equal(describeNode(null), "null"); assert.equal(describeNode(undefined), "undefined"); assert.equal(describeNode(3), "3");
  assert.equal(describeNode({}), "Object", "a plain object with no tag: its class name");
  // sameNodes: the same nodes in the same order pass; a wrong node, a wrong order, a missing node, a foreign node and no
  // list fail with `message` and one line naming the index and both tags, never a dump
  const [d1, s1, d2] = nodes;
  sameNodes([d1, s1, d2], [d1, s1, d2], "the same list"); sameNodes([], [], "two empty lists");
  const fails = (actual: any, expected: any[]) => { try { sameNodes(actual, expected, "the rows"); } catch (e: any) { return String(e.message); } return ""; };
  let m = fails([d1, s1, d2], [d1, s1, makeNode("div")]);
  assert.ok(m.startsWith("the rows: index 2 is another node: got div#" + d2._nid + ", expected div#"), "a different node of the same tag, by index and serial: " + m);
  m = fails([d1, s1, d2], [d1, d2, s1]); assert.ok(m.startsWith("the rows: index 1 is another node: got span#" + s1._nid + ", expected div#" + d2._nid), "a reorder: " + m);
  m = fails([d1, s1], [d1, s1, d2]); assert.equal(m, "the rows: 2 nodes where 3 were expected", "a missing node");
  m = fails([d1, s1, d2, kid], [d1, s1, d2]); assert.equal(m, "the rows: 4 nodes where 3 were expected", "an extra node");
  m = fails(null, [d1]); assert.equal(m, "the rows: no node list, got null where 1 nodes were expected", "no list at all");
  m = fails([null], [d1]); assert.ok(m.startsWith("the rows: index 0 is another node: got null, expected div#"), "a null in the list: " + m);
  for (const bad of [fails([d1, s1, d2], [d1, s1, makeNode("div")]), fails([d1, s1], [d1, s1, d2])]) assert.ok(lines(bad) === 1, "one line, got " + lines(bad));
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
/** A file INITIALISES AN EDGE when it makes one of the eleven edge names (parentNode, parentElement, parent, childNodes,
 *  children, firstChild, lastChild, nextSibling, previousSibling, ownerDocument or host) an own enumerable property in
 *  any of these shapes, with null, undefined, [], this, a this.-rooted member or call, a bare identifier, or a
 *  conditional whose final operand is one of those, as the value. What the property belongs to does not matter: a fake node, a window stand-in, a goal tree's fixture or a list
 *  model, since a failing dump walks each of them and the cure for each is the same call on that object. The detector
 *  reads CODE: line and block comments and the contents of string, template and regex literals are blanked first
 *  (`blank` below), so a source pin quoting a shape, a shape in a comment and a call token in a comment or a string
 *  count for nothing. EDGE stands for an edge name below, so this file's own text initialises none:
 *  - an object-literal key (`{ EDGE: null, EDGE: [] }`, `{ EDGE: kid }`, `{ EDGE: this.doc }`, `{ EDGE: BODY }`: any
 *    identifier, capitalised or not). With an identifier value the key host is left out: an object-literal `host:`
 *    in this tree is the payload field naming a machine;
 *  - an object-literal accessor (`{ get EDGE() { ... } }`), the incident's own shape: an own accessor enumerates and
 *    node's assert reads getters. A class accessor lives on the prototype and is no edge, but one that opens a class
 *    body reads as this shape (INDISTINGUISHABLE below);
 *  - a class field, with any modifier or none (public, private, protected, readonly, declare, override), plain,
 *    definite (`EDGE!: N | null;`) or optional (`EDGE?: N[]`), typed or not, with an initializer or without one (a
 *    declared field is an own enumerable property once the constructor assigns it), after a line start, a member
 *    semicolon or the class brace (`tag = "x"; private EDGE: N | null = null;`). In the declared-only form a field
 *    whose type STARTS with a primitive (string, number, boolean, bigint, symbol, undefined, void, never) is no edge
 *    and is skipped, whatever follows (`EDGE: string | null;` is skipped; `EDGE: null | string;` is read, and so is
 *    a primitive-typed field with an initializer, `EDGE: string | null = null`). In the declared-only form the key
 *    host is left out too, and a value that starts with a quote, a digit
 *    or a boolean, or that contains a parenthesis other than a parenthesised type right after the colon
 *    (`EDGE!: (N | Txt | string)[];` is read; `host: hostOf(sid)` is not), is skipped: the last line of a multi-line
 *    object literal without a trailing comma (`host: "x"`, `EDGE: 3`, `EDGE: count(kids)`) reads as a declared
 *    field, and those lines are payload, not edges;
 *  - a constructor parameter property (`constructor(public EDGE: N[] = [])`, with or without a default);
 *  - an assignment through any name (`this.EDGE = null`, `n.EDGE = []`, `c.EDGE = p`, `c.EDGE = this.host`).
 *  Out of scope, by design: an edge under another name (a `kids` list), a shorthand key (`{ EDGE }`, or `EDGE,` alone
 *  on a line), a computed key (`{ ["EDGE"]: null }`: the lexer blanks the string; `{ [k]: null }`: the identifier
 *  carries no edge name), a spread of an object built elsewhere (`{ tag, ...base }`, `{ ...edges }` with edges from
 *  Object.fromEntries, a helper or an import: the name is in another expression or file; a spread of a same-file
 *  literal is read through that literal's own key), a bracket-notation write (`c["EDGE"] = this`: the lexer blanks the
 *  key, and the assignment shape needs a dot), a compound assignment (`c.EDGE ??= this`, `c.EDGE ||= []`: the
 *  assignment shape matches a bare equals sign), a class field whose type starts on the line after the colon (`EDGE:`
 *  ending a line, `N | null = null;` or `N | null;` on the next: the field shape's type runs to the end of its own
 *  line), a value that is a member expression, a call or a `new` not rooted at this (`up.EDGE = g.document`, `EDGE =
 *  new Doc()`), a logical value (`n.EDGE = p || null`), an object literal or a non-empty array literal as the value
 *  (`win.EDGE = {}`, `EDGE: [kidA, kidB]`, `n.EDGE = [a, b]`), an Object.defineProperty of an edge whatever its
 *  enumerable flag (a descriptor holding a getter defeats a regex), a declared field whose type carries a comma
 *  (`EDGE: Record<string, N>;`), and a class field right after a `}` on the same line (a one-line method's body, a
 *  `{}` constructor, a static block: `constructor(public t: string) {} EDGE: N | null = null;`). A value is read by
 *  its first operand, a bare name whatever follows it other than a type continuation, a member or a call (`framed ?
 *  win : {}` is read through `framed`), or, for a conditional, by its final operand after the last colon (`win.EDGE =
 *  opts.framed ? {} : win`), the head and the middle operand free of parentheses; a conditional with a
 *  member-expression head whose final operand is an object literal, a member or a call (`win.EDGE = opts.framed ? win
 *  : {}`) is not read. Checked in the tree at this head (2026-09-10; a TypeScript-AST walk over the 786 test
 *  files under ui/ and ui/webview/ and a grep agree): no computed key, bracket write or wrapped field names an
 *  edge; no object literal that spreads is a node (none carries tagName, nodeType, nodeName, tag or appendChild); and
 *  the one compound write, ui/webview/timeline-boot.test.ts's `this.children ??= []` on a helper prototype whose
 *  children are nodeFactory nodes, is in a file that calls nodeFactory. So no fake reaches the ratchet through these
 *  shapes today; a new one in any of them is the reviewer's to catch, with the callers pin below for the files that
 *  call hideEdges. A regex reads shape, not meaning, and some code that initialises no edge reads as a shape:
 *  a destructuring default at line start (`function mk({\n  EDGE = [],\n})`) reads as a class field, where the
 *  one-line forms do not (a brace after `(`, `=`, `,`, let, const or var opens no class body, and a `;` inside such a
 *  one-line brace group separates type members, not class members, so `type N = { tag: string; EDGE: N | null }` is
 *  told apart; a brace after a name or a colon is a class brace to the regex, so a one-line `interface N { tag:
 *  string; EDGE: N | null; }` or `o: { tag: string; EDGE: N | null; }` reads as a class field); a type literal's
 *  member on its own line (`type N = {\n  EDGE: N | null;\n}`), or comma-separated on one line (`type N = { EDGE: N,
 *  tag: string }`), reads as a class field or an object-literal key, and its FIRST member with a bare-name type reads
 *  as an object-literal key whichever separator follows (`type N = { EDGE: El; tag: string }`; the `;` rule above
 *  tells the class-field reading apart, not this one); a type literal's readonly member after a comma
 *  reads as a parameter property; a typed parameter after a comma whose type is a bare name (not a union, an array
 *  or a generic), in code (`function mk(a: El, EDGE: El)`), reads as an object-literal key; a statement reassigning a
 *  local of an edge name at line start or after `;` or `{` (`EDGE = el;`, with null, undefined, [], this or a bare
 *  identifier on the right) reads as a class field, since a class body and a function body are the same brace to a
 *  regex, so the remedy is to rename the local; a class whose first member is an edge getter reads as an
 *  object-literal accessor. INDISTINGUISHABLE below pins each; a file that carries one renames the local or the
 *  parameter, or is carried on NON_DOM_EDGES with its reason (the newcomer paths in the ratchet's first message). */
const KEY = "(parentNode|parentElement|parent|childNodes|children|firstChild|lastChild|nextSibling|previousSibling|ownerDocument|host)";
const KEY_NOT_HOST = KEY.replace("|host", "");
const MODS = "(?:(?:public|private|protected|readonly|declare|override)\\s+)";
const NOT_KEYWORD = "(?!(?:string|number|boolean|any|unknown|never|void|object|symbol|bigint|true|false|new|typeof|await|function|async|class|yield|delete|in|instanceof)\\b)";   // a type name, a boolean or a keyword is no identifier value
const NOT_CONTINUED = "\\b(?!\\s*[\\[<|&.(])";   // not a type continuation (Kid[], Map<, | null, & X) and not a member or call
const IDENT = NOT_KEYWORD + "[A-Za-z_$][\\w$]*" + NOT_CONTINUED;   // a bare name as a value, capitalised or not
const VALUE_BASE = "(?:null\\b|undefined\\b|\\[\\]|this\\b|" + IDENT + ")";   // this\b admits this.host and this.f() too: an edge write whatever it holds
// a conditional whose final operand is such a value and ends the statement, read after its last colon (`framed ? {} : win`,
// `opts.framed ? {} : win`, `c ? { a: 1 } : kid`); the head and the middle operand carry no parenthesis, and the head does
// not start with `=` (a comparison, not an assignment)
const CONDITIONAL = "(?!=)[^;\\n()]*?\\?[^;\\n()]*:\\s*" + VALUE_BASE + "(?=[ \\t]*(?:[;,)\\n]|$))";
const VALUE = "(?:" + VALUE_BASE + "|" + CONDITIONAL + ")";
const NOT_PRIM = "(?!\\s*(?:string|number|boolean|bigint|symbol|undefined|void|never)\\b)";   // a field typed as a primitive is no edge
const NOT_LITERAL = "(?!\\s*(?:[\"'`\\-\\d]|(?:true|false)\\b))";   // a declared-only value that is a string, number or boolean is a payload line
// a declared-only field's type: a parenthesised type right after the colon (`(N | Txt | string)[]`) or a run with no
// parenthesis, either ending the statement or the line; `count(kids)` and `hostOf(sid)` carry a name before the paren
const DECLARED_TYPE = "(?:\\s*\\([^()=;\\n]*\\)[^=;,{}()\\n]*?|[^=;,{}()\\n]+?)\\s*(?:;|$)";
// a class body opens after a name, `>` or `)` (`class N {`, `extends B<T> {`, `constructor() {`), never after `(`, `=`,
// `,`, let, const or var: those braces open a destructuring pattern, a type literal or an object literal
const OPENS_NO_CLASS = "[(=,]\\s*|\\b(?:let|const|var)\\s+";
const CLASS_BRACE = "(?<!" + OPENS_NO_CLASS + ")\\{";
// a `;` anchors a member unless it sits inside a one-line brace group such a brace opened: there it separates a type
// literal's members (`type N = { tag: string; EDGE: N | null }`), where the same `;` after a class brace separates fields
const MEMBER_SEMI = "(?<!(?:" + OPENS_NO_CLASS + ")\\{[^{}\\n]*);";
const EDGE_INIT: Record<string, RegExp> = {
  "object-literal key": new RegExp("[{,]\\s*" + KEY + "\\s*:\\s*(?:null\\b|undefined\\b|\\[\\])"),
  "object-literal key, identifier value": new RegExp("[{,]\\s*" + KEY_NOT_HOST + "\\s*:\\s*(?:this\\b|" + IDENT + ")"),
  "accessor": new RegExp("[{,]\\s*get\\s+" + KEY + "\\s*\\("),
  // with an initializer (typed or not): `EDGE = null`, `private EDGE: N | null = null`; or declared only, where the key
  // host is left out and the value may not be a literal or carry a call's parenthesis: `EDGE!: N | null;`, `EDGE?: N[]`,
  // `EDGE: N | null` ending the line, `EDGE!: (N | Txt | string)[];`
  "class field": new RegExp("(?:^|" + MEMBER_SEMI + "|" + CLASS_BRACE + ")\\s*" + MODS + "*(?:" + KEY + "\\s*[?!]?\\s*(?::[^=;\\n]+)?=\\s*" + VALUE
    + "|" + KEY_NOT_HOST + "\\s*[?!]?\\s*:" + NOT_PRIM + NOT_LITERAL + DECLARED_TYPE + ")", "m"),
  "parameter property": new RegExp("[(,]\\s*" + MODS + "+" + KEY + "\\b"),
  "assignment": new RegExp("\\b[A-Za-z_$][\\w$]*\\." + KEY + "\\s*=\\s*" + VALUE),
};
/** Blanks what is not code, to spaces of the same length (newlines kept, so a line-anchored shape reads the same
 *  lines): every line and block comment, and with `literals` the contents of every string, template and regex literal
 *  too. Delimiters stay, so a blanked string is still a quoted value to NOT_LITERAL and an import's specifier still
 *  reads when only comments go. A template's `${ }` holes are code and are lexed as such, braces nested. A `/` opens a
 *  regex when the code before it ends no operand and a division otherwise. The operand test reads the BLANKED text,
 *  never the source, so a comment between the operand and the slash is skipped like whitespace (a regex pin on the
 *  line after a trailing comment is a regex; a division after a block comment is a division). The previous
 *  significant character decides: an operator, an opener, a separator or nothing opens a regex; a closing paren or
 *  bracket, a closing quote, double quote or backtick (a string or template literal is an operand: `'10' / 2`), the
 *  second character of a postfix `++` or `--` (`x++ / 2`), or a name is a division, a name excepted after return,
 *  typeof, case and the like. A regex that does not close on its line is read as a division, since a regex literal
 *  cannot span lines. Two shapes the lexer cannot tell apart: a regex right after a condition's closing paren (`if
 *  (x) /re/.test(y)`) is read as a division, so its text stays code (INDISTINGUISHABLE below pins the shape it trips
 *  as), and a quote or a backtick inside it opens a string to the line end or a template to the next backtick in the
 *  file, hiding an edge init there; and a closing brace before a slash opens a regex (`{} / 2`, a block or an object
 *  literal followed by a division), so the code up to the next slash on the line is blanked, hiding an edge init
 *  there. Both are false negatives the ratchet accepts (ACCEPTED_MISREADS below pins them; the tree holds neither,
 *  measured against a TypeScript-AST blanking of every UI test file). A light lexer,
 *  not a parser: it knows the token kinds that hide shapes, not the grammar around them. */
const REGEX_AFTER = new Set(["return", "typeof", "case", "do", "else", "in", "instanceof", "new", "throw", "void", "delete", "yield", "await", "of"]);
function blank(s: string, literals: boolean): string {
  const out = s.split("");
  const wipe = (a: number, b: number) => { for (let k = a; k < b && k < out.length; k++) if (out[k] !== "\n") out[k] = " "; };
  const regexStarts = (i: number): boolean => {   // reads `out`: everything before i is lexed, so a comment there is spaces
    let j = i - 1;
    while (j >= 0 && /\s/.test(out[j])) j--;
    if (j < 0) return true;
    if (out[j] === ")" || out[j] === "]") return false;
    if (out[j] === "\"" || out[j] === "'" || out[j] === "`") return false;   // a closing quote or backtick: a string or template literal is an operand
    if (j >= 1 && ((out[j] === "+" && out[j - 1] === "+") || (out[j] === "-" && out[j - 1] === "-"))) return false;   // a postfix ++ or --
    if (!/[\w$]/.test(out[j])) return true;
    let k = j; while (k >= 0 && /[\w$]/.test(out[k])) k--;
    return REGEX_AFTER.has(out.slice(k + 1, j + 1).join(""));
  };
  const regexEnd = (i: number): number => {   // the index after the closing slash, or -1 when the line ends first
    let inClass = false;
    for (let k = i + 1; k < s.length && s[k] !== "\n"; k++) {
      if (s[k] === "\\") { k++; continue; }
      if (inClass) { if (s[k] === "]") inClass = false; continue; }
      if (s[k] === "[") inClass = true; else if (s[k] === "/") return k + 1;
    }
    return -1;
  };
  const stringEnd = (i: number): number => {   // the index after the closing quote; an unterminated string ends with its line
    for (let k = i + 1; k < s.length; k++) {
      if (s[k] === "\\") { k++; continue; }
      if (s[k] === s[i]) return k + 1;
      if (s[k] === "\n") return k;
    }
    return s.length;
  };
  // code from i to the end, or to the `}` that closes a template hole when `inHole`; returns the index after it
  function code(i: number, inHole: boolean): number {
    let depth = 0;
    while (i < s.length) {
      const c = s[i], d = s[i + 1];
      if (c === "/" && d === "/") { let e = s.indexOf("\n", i); if (e < 0) e = s.length; wipe(i, e); i = e; continue; }
      if (c === "/" && d === "*") { let e = s.indexOf("*/", i + 2); e = e < 0 ? s.length : e + 2; wipe(i, e); i = e; continue; }
      if (c === '"' || c === "'") { const e = stringEnd(i); if (literals) wipe(i + 1, s[e - 1] === c && e - 1 > i ? e - 1 : e); i = e; continue; }
      if (c === "`") { i = template(i); continue; }
      if (c === "/" && regexStarts(i)) { const e = regexEnd(i); if (e > 0) { if (literals) wipe(i + 1, e - 1); i = e; continue; } }
      if (inHole) { if (c === "{") depth++; else if (c === "}") { if (depth === 0) return i + 1; depth--; } }
      i++;
    }
    return i;
  }
  function template(i: number): number {   // i at the opening backtick; returns the index after the closing one
    let k = i + 1;
    while (k < s.length) {
      const c = s[k];
      if (c === "\\") { if (literals) wipe(k, k + 2); k += 2; continue; }
      if (c === "`") return k + 1;
      if (c === "$" && s[k + 1] === "{") { k = code(k + 2, true); continue; }
      if (literals) wipe(k, k + 1);
      k++;
    }
    return k;
  }
  code(0, false);
  return out.join("");
}
/** The names of the shapes the code of `s` initialises an edge in; empty when none. */
const edgeShapes = (s: string): string[] => { const c = blank(s, true); return Object.keys(EDGE_INIT).filter((k) => EDGE_INIT[k].test(c)); };
const initsEdge = (s: string) => edgeShapes(s).length > 0;
/** The lines (1-based) on which the code of `s` initialises an edge: for every shape's every match over the blanked
 *  code, the line of the first edge name inside the match. NON_DOM_EDGES pins each listed file's count, so a fake that
 *  grows in a listed file, in any shape, on any new line, changes the number the ratchet checks. */
const edgeLines = (s: string): number[] => {
  const code = blank(s, true), edge = new RegExp("\\b" + KEY + "\\b"), out = new Set<number>();
  for (const k of Object.keys(EDGE_INIT)) {
    for (const m of code.matchAll(new RegExp(EDGE_INIT[k].source, EDGE_INIT[k].flags + "g"))) {
      const at = m[0].search(edge);
      out.add(code.slice(0, m.index! + (at < 0 ? 0 : at)).split("\n").length);
    }
  }
  return [...out].sort((a, b) => a - b);
};
/** The credential: an import of hideEdges or nodeFactory from the shared module AND a call of one of them, in code.
 *  The import is a statement in code at line start (its text up to the specifier reads the same once every literal
 *  is blanked: an import line quoted inside a template or a backslash-continued string is not one), either quote
 *  style on the specifier, with or without a .js suffix, as a named import (`import { hideEdges } from
 *  "./test-dom-shim"`) or a namespace import (`import * as shim from "../test-dom-shim"`, the alias any ASCII
 *  identifier: letters, digits, underscore, dollar); the call is any `hideEdges(` or `nodeFactory(` token in code at a
 *  word boundary for a named import (a preceding `.` or `$` included, so `other.hideEdges(` counts) and
 *  `shim.hideEdges(` or `shim.nodeFactory(` under the namespace's alias or a member path ending in it
 *  (`helpers.shim.hideEdges(`), not under a longer identifier that ends in it (`myshim.`, `$shim.`). An import alone
 *  hides nothing; a call under an alias (`import { hideEdges as hide }`), a reference passed as a callback
 *  (`nodes.forEach(hideEdges)`), a local helper of the same name without the import, or a call token in a comment or
 *  a string is not read: import it and write the call. What
 *  no regex can see is whether the call covers every object in the file that declares an edge: a second class, or an
 *  object literal beside the nodeFactory nodes (ui/timeline-transform-tick.test.ts's hover target held an enumerable
 *  parentNode that way until round 4 wrapped it in hideEdges), stays unhidden. That gap is real and is closed per
 *  file, by reading each edge-bearing object a switched file builds and wrapping it (hideEdges on a literal,
 *  hideEdges(this) at the end of a constructor), with a projection assertion where the object is a node; this file
 *  and the tags-scale test carry one, and the runner's cgroup cap is the backstop. */
const SHIM_SPECIFIER = "(?:\\.\\.\\/|\\.\\/)test-dom-shim(?:\\.js)?";
const IMPORTS_SHIM = new RegExp("^\\s*import\\s*\\{[^}]*\\b(?:hideEdges|nodeFactory)\\b[^}]*\\}\\s*from\\s*([\"'])" + SHIM_SPECIFIER + "\\1", "gm");
const IMPORTS_SHIM_NS = new RegExp("^\\s*import\\s*\\*\\s*as\\s+([A-Za-z_$][\\w$]*)\\s+from\\s*([\"'])" + SHIM_SPECIFIER + "\\2", "gm");
const CALLS_SHIM = /\b(?:hideEdges|nodeFactory)\(/;
const escapeRegExp = (t: string) => t.replace(/[\\^$.*+?()[\]{}|]/g, "\\$&");
const switched = (s: string): boolean => {
  const imports = blank(s, false), code = blank(s, true);   // the specifier is a string, so the import reads the comment-free text
  // a statement in code reads the same in both texts up to the specifier's quote; an import line quoted inside a
  // template or a backslash-continued string is spaces in the fully blanked one
  const inCode = (m: RegExpExecArray, quote: string) => { const q = m[0].indexOf(quote); return code.slice(m.index, m.index + q) === m[0].slice(0, q); };
  for (const m of imports.matchAll(IMPORTS_SHIM)) if (inCode(m, m[1]) && CALLS_SHIM.test(code)) return true;
  for (const m of imports.matchAll(IMPORTS_SHIM_NS)) if (inCode(m, m[2]) && new RegExp("(?<![\\w$])" + escapeRegExp(m[1]) + "\\.(?:hideEdges|nodeFactory)\\(").test(code)) return true;
  return false;
};
/** True when `s` must be on the allowlist: it initialises an edge and is not switched. */
const needsListing = (s: string) => initsEdge(s) && !switched(s);

// ALLOWLIST: the test files whose code initialises an edge-named property without calling the shared module and are
// not a documented non-DOM use below, each named, so a newcomer has a rule to read and a place it may not go.
// ALLOWLIST_MAX is the list's exact length: a file that switches (a hideEdges call on its object, at the end of each
// constructor for a class, or nodeFactory for its nodes, plus a projection test) comes off and the constant comes down
// in the same commit; a renamed file replaces its entry; a new file may not join. On 2026-09-10 the list held 150
// ui/webview test files: from the detector's first two rounds, 135 class-based fake DOMs (El and Txt, FakeNode, E,
// FakeEl, Elm, with a prototype firstChild, so no 2^depth term, but the whole-tree walk through parentNode, parent or
// ownerDocument remained, and feed.ts hangs node references on cards), four literal node factories
// (anchor-map-wrapped-code, pdf-chunk-refused-open, setting-stale-fold, timeline-boot; the last now takes nodeFactory
// outright) and two window stand-ins whose parent is another stand-in (file-view, pdf-new-tab); from its third, once
// the vocabulary gate came off, nine more: two window stand-ins whose parent is the stand-in itself (perf-telemetry,
// shell-perf), element and node literals (thread-selection-scope, timeline-rehover), one more class
// (track-decorations-hover-cost), the two non-DOM uses listed below and two source pins (feed-absorb, setting-stale)
// whose quoted product text the fourth round's lexer blanks, so they read as nothing now. The same day every fake hid
// its edges (a non-enumerable define of the edge fields in the constructors, hideEdges from the shared module at the
// end of each or on the literal, plus a projection test; the file-comments Ev classes end in hideEdges too, so an
// event's target and currentTarget hide with the nodes). The eight class fakes main added between this branch's base
// and its landing (actions, file-comments-markclick, file-comments-markclick-controls, file-comments-seen-fixes,
// -seen-review2, -seen-review3, file-comments-send-seen, file-view-notice) were migrated the same way, and so were the
// eleven PR 523 listed at its final rebase onto main: the seven file-comments-about and file-comments-resolve-answered
// class fakes (six of them already defined parentNode and childNodes non-enumerable through a local helper; the shared
// module's call replaces it and their Ev classes end in it too), the tab-hide and preview-retry-pace class fakes,
// federation-hidden-hold's window stand-in (hideEdges on the literal after its conditional-valued parent) and the
// fold's timeline-tag-chips node literal, which takes nodeFactory outright and joins SWITCHED. The list is empty.
const ALLOWLIST: string[] = [];
// The list's exact length: 0 since 2026-09-10, when the last of the 167 came off or moved to NON_DOM_EDGES. The ratchet
// pins it by equality, so neither the list nor this number goes up.
const ALLOWLIST_MAX = 0;
// NON_DOM_EDGES: the test files whose edge-named key the detector reads but which fake no DOM, each with its reason
// and the count of lines on which the detector reads an edge init in it. An entry documents the use AS IT READS TODAY:
// the detector reads shape, not meaning, and a goal fixture's children or a list model's children initialise no edge
// a failing dump could walk (a dump of each is the fixture's own few lines). The count is what the pin enforces: a
// fake DOM that later grows in a listed file, in any shape, adds a line the detector reads and the count changes,
// where the list alone would have stayed green (a rewrite of the documented line itself, one for one, is the move the
// count cannot see; the reason is the reviewer's check on that). A listed file has no projection test, so the runner's
// cgroup cap is its backstop. NON_DOM_EDGES_MAX is this list's exact length too: a file that joins raises it in the
// same commit, with its reason and count; one that stops reading as a shape, calls the module or is gone comes off and
// lowers it.
const NON_DOM_EDGES: Array<[string, string, number]> = [   // [file, why its edge-named key is no DOM edge, edge-initialising lines the detector reads]
  ["webview/card-subgoals.test.ts", "a goal fixture's children array holds ids (strings): a data tree the card renders, not a DOM", 1],
  ["webview/tab-snapshot-view.test.ts", "a list model's children are plain rows of an id and a text with no edge back, so a dump is the rows", 1],
];
const NON_DOM_EDGES_MAX = 2;
const NON_DOM = NON_DOM_EDGES.map(([f]) => f);
// SWITCHED: the seventeen files whose own copies of the node factory the shared module REPLACED (2026-09-10): the sixteen
// near-copies (fifteen ui/timeline-*.test.ts siblings, the fold's timeline-tag-chips among them, and
// ui/webview/tab-color-picker.test.ts) and the tags-scale test the shim grew from. They keep no makeNode of their own. The other ui/webview test files that fake a DOM are not listed
// here: each keeps its own node classes, window stand-ins or literals and hides their edges through hideEdges
// (ui/webview/timeline-boot.test.ts takes nodeFactory outright); the call is the credential the ratchet reads, and each
// file's projection test is the executed check on its edges.
const SWITCHED = [
  "timeline-hidden-hold.test.ts", "timeline-hidden-stub.test.ts", "timeline-kernel-post.test.ts", "timeline-live-tick.test.ts",
  "timeline-nan-window.test.ts", "timeline-open-interval.test.ts", "timeline-pending-hosts.test.ts", "timeline-render.test.ts",
  "timeline-tag-chips.test.ts", "timeline-tagbtn-click.test.ts", "timeline-tagorder-drag.test.ts", "timeline-tags-scale.test.ts", "timeline-theme-light.test.ts",
  "timeline-transform-tick.test.ts", "timeline-views-ack.test.ts", "timeline-zoom-anchor.test.ts", "webview/tab-color-picker.test.ts",
];

test("ratchet: every UI test file that initialises an edge calls the shared module, is on the allowlist or is a documented non-DOM use; every listed file still reads as one; each list's length is its pinned count, and each non-DOM entry's edge-line count holds", () => {
  const files = testFiles();
  assert.ok(files.includes("test-dom-shim.test.ts") && files.includes("webview/tab-color-picker.test.ts"), "the sweep covers ui/ and ui/webview/");
  const matching = files.filter((f) => needsListing(src(f)));
  assert.deepEqual(matching.filter((f) => !ALLOWLIST.includes(f) && !NON_DOM.includes(f)), [],
    "a UI test file's code initialises an edge-named property (parentNode, parentElement, parent, children, childNodes, a child or sibling pointer, " +
    "ownerDocument or host) without calling the shared module; a failing assertion on such an object can allocate tens of GB. Three paths: (1) a fake DOM: " +
    "build its nodes with nodeFactory(, or call hideEdges(this) at the end of the class's constructor (hideEdges(obj) on an object literal), imported from " +
    "ui/test-dom-shim.ts as a named import or a namespace import (shim.hideEdges(); a .js suffix on the specifier is read too), and add a projection test: " +
    "one import and one line. The import alone is not enough, and a call token in a comment or a string is not a call: the call in code is what counts. " +
    "(2) A non-DOM use of an edge name (a local reassigned at line start, a typed parameter after a comma, a type literal's member, a fixture's field): " +
    "rename it, or add the file to NON_DOM_EDGES with its reason and its count of edge-initialising lines and raise NON_DOM_EDGES_MAX in the same commit. " +
    "(3) Neither fits: ask the reviewer. ALLOWLIST, the unmigrated fakes, is empty since 2026-09-10 and closed: no file joins it and ALLOWLIST_MAX stays 0");
  assert.deepEqual(ALLOWLIST.filter((f) => !matching.includes(f)), [],
    "an allowlisted file no longer initialises an edge in code, calls the shared module now, or is gone: take it off the list and set ALLOWLIST_MAX to the " +
    "list's new length in the same commit");
  assert.deepEqual(NON_DOM.filter((f) => !matching.includes(f)), [],
    "a file listed in NON_DOM_EDGES no longer initialises an edge-named key in code, calls the shared module now, or is gone: take it off and lower NON_DOM_EDGES_MAX to the new length in the same commit");
  assert.equal(ALLOWLIST.length, ALLOWLIST_MAX,
    "the allowlist holds " + ALLOWLIST.length + " files, not its pinned count of " + ALLOWLIST_MAX + ". ALLOWLIST_MAX is the list's exact length: a renamed file " +
    "replaces its entry and the count stands; a file that comes off lowers the constant in the same commit; a new file may not join, so neither the list nor the constant goes up");
  assert.equal(NON_DOM_EDGES.length, NON_DOM_EDGES_MAX,
    "NON_DOM_EDGES holds " + NON_DOM_EDGES.length + " files, not its pinned count of " + NON_DOM_EDGES_MAX + ": a file that joins or leaves moves the constant in the same commit");
  for (const [f, why, n] of NON_DOM_EDGES) {
    assert.ok(why.trim().length >= 40, f + " carries a one-line reason its edge-named key is no DOM edge");
    const found = edgeLines(src(f));
    assert.equal(found.length, n, f + " initialises an edge-named key on " + found.length + " line(s) (" + found.join(", ") + "), not the " + n + " its NON_DOM_EDGES entry " +
      "pins: the file changed under its documented non-DOM use, so re-examine it. A fake DOM that grew there migrates onto the shim (hideEdges at the end of each constructor " +
      "or on the literal, plus a projection test) and the file comes off this list; a non-DOM use that grew or shrank is re-documented, reason and count, in the same commit");
  }
  assert.deepEqual(ALLOWLIST, ALLOWLIST.slice().sort(), "the allowlist is sorted, so a change to it reads as one line");
  assert.deepEqual(NON_DOM, NON_DOM.slice().sort(), "NON_DOM_EDGES is sorted by file, so a change to it reads as one line");
  assert.equal(new Set([...ALLOWLIST, ...NON_DOM]).size, ALLOWLIST.length + NON_DOM.length, "no name twice, within or across the two lists");
});

test("the NON_DOM_EDGES count pin: a listed file's copy with one more edge-initialising line, in either shape, counts one more, so the pin goes red on growth; edgeLines counts lines, not matches", () => {
  for (const [f, , n] of NON_DOM_EDGES) {
    const s = src(f);
    assert.equal(edgeLines(s).length, n, f + " counts its pinned lines");
    assert.equal(edgeLines(s + "\n" + scratch("const extra = { tagName: 'DIV', EDGE: null, appendChild() {} };\n", "parentNode")).length, n + 1, f + ": an appended node literal adds one line");
    assert.equal(edgeLines(s + "\n" + scratch("class Extra {\n  EDGE: Extra | null = null;\n  appendChild(c: Extra) { c.EDGE = this; }\n}\n", "parentNode")).length, n + 2, f + ": an appended class fake adds its field line and its assignment line");
  }
  assert.deepEqual(edgeLines(scratch("const n = { EDGE: null, x: 1 };\nclass N { EDGE = []; }\nn.EDGE = kid;\n", "children")), [1, 2, 3], "one entry per line, across shapes");
  assert.deepEqual(edgeLines(scratch("const n = { EDGE: null, kids: [] }; n.EDGE = other;\n", "parentNode")), [1], "two inits on one line count once");
  assert.deepEqual(edgeLines(scratch("// EDGE: null\nconst s = 'EDGE: []'; /* n.EDGE = kid */\n", "parentNode")), [], "comments and strings count for nothing");
});

test("every ui/webview test file whose code calls hideEdges( initialises an edge the detector reads: a caller the detector cannot see is a shape drift, the credential read but the rule not", () => {
  // ui/test-dom-shim.test.ts (its text uses EDGE) and ui/timeline-tags-scale.test.ts (nodeFactory nodes, hideEdges on a variant-shape
  // node it builds) are the two callers outside ui/webview/ that the detector does not read, by design; the webview files are the rule's
  // scope, so every hideEdges( caller there must initialise an edge the detector reads
  const callers = testFiles().filter((f) => f.startsWith("webview/") && /\bhideEdges\(/.test(blank(src(f), true)));
  assert.ok(callers.length >= 100, "the sweep found " + callers.length + " webview callers");
  assert.deepEqual(callers.filter((f) => !initsEdge(src(f))), [],
    "a ui/webview test file calls hideEdges( on an object whose edge the detector does not read (the docstring's out-of-scope list: a shorthand key, a " +
    "computed key, a spread of an object built elsewhere, a bracket-notation write, a compound assignment, a class field whose type starts on the line after " +
    "the colon; the docstring records the tree check that found no fake in any of them on 2026-09-10), so the ratchet would stay green if the call came off. " +
    "Write the edge in a shape it reads (a declared field, `EDGE: [] as any[]` on a literal), or add the shape to the detector with a POSITIVE case");
});

test("the files that carried the shim's copies import nodeFactory or hideEdges, call it, and keep no node factory of their own; this file's own code initialises no edge", () => {
  for (const f of SWITCHED) {
    const s = src(f);
    assert.ok(switched(s), f + " imports nodeFactory or hideEdges from test-dom-shim and calls it");
    assert.ok(!/^function makeNode\(/m.test(s), f + " defines no makeNode of its own");
  }
  const own = src("test-dom-shim.test.ts");
  assert.ok(!initsEdge(own), "this file does not trip its own rule; matched " + JSON.stringify(edgeShapes(own)));
});

// ── the detector, on scratch sources ────────────────────────────────────────────────────────────────
// Each shape the rule names, as positives (trip) and near-miss negatives (do not), plus the code this detector does
// not tell from a shape (trips, and the docstring says so). EDGE stands in for an edge name so this file's own text
// initialises none.
const scratch = (s: string, edge: string) => s.replace(/EDGE/g, edge);
const POSITIVE: Array<[string, string, string]> = [   // [the shape it must trip, scratch source, edge name]
  ["object-literal key", "const n = { tagName: 'DIV', EDGE: null, x: 1 };", "parentNode"],
  ["object-literal key", "const n = { EDGE: [], appendChild() {} };", "children"],
  ["object-literal key", "const n = {\n  nodeType: 1,\n  EDGE: undefined,\n};", "nextSibling"],
  ["object-literal key", "const goal = { title: 'x', EDGE: [] };", "children"],   // a data fixture: no vocabulary gate, the rule is uniform
  ["object-literal key, identifier value", "const n = { EDGE: kid, nodeType: 1 };", "firstChild"],
  ["object-literal key, identifier value", "const n = { tagName: 'DIV', EDGE: doc };", "ownerDocument"],
  ["object-literal key, identifier value", "const n = { EDGE: BODY, appendChild() {} };", "parentNode"],   // a capitalised identifier
  ["object-literal key, identifier value", "function mk(p) { return { EDGE: p, appendChild() {} }; }", "parent"],
  ["object-literal key, identifier value", "class N { child() { return { EDGE: this, nodeType: 1 }; } }", "parentNode"],
  ["object-literal key, identifier value", "class N { child() { return { EDGE: this.doc, nodeType: 1 }; } }", "ownerDocument"],   // a this.-rooted member
  ["object-literal key, identifier value", "const win = { EDGE: shell, postMessage() {} };", "parent"],   // a window stand-in
  ["class field", "class N {\n  EDGE: N[] = [];\n  appendChild() {}\n}", "children"],
  ["class field", "class N { tag = 'x'; private EDGE: N | null = null; appendChild() {} }", "parentNode"],
  ["class field", "class N {\n  public readonly EDGE: N[] = [];\n  nodeType = 1;\n}", "childNodes"],
  ["class field", "class N {\n  protected EDGE: N | null = null;\n  tagName = 'DIV';\n}", "parent"],
  ["class field", "class N {\n  override EDGE: N | null = null;\n  appendChild() {}\n}", "lastChild"],
  ["class field", "class N {\n  EDGE: N | null = BODY;\n  appendChild() {}\n}", "previousSibling"],
  ["class field", "class N {\n  EDGE = null;\n  appendChild() {}\n}", "host"],
  ["class field", "class N {\n  EDGE = this.root;\n  appendChild() {}\n}", "parent"],   // a this.-rooted member
  ["class field", "class N {\n  EDGE!: N | null;\n  constructor() { hideEdges(this); }\n  appendChild() {}\n}", "parentNode"],
  ["class field", "class N {\n  EDGE?: N[];\n  appendChild() {}\n}", "children"],
  ["class field", "class N {\n  EDGE: N | null;\n  appendChild() {}\n}", "parent"],
  ["class field", "class N { tag = 'x'; private EDGE!: Doc | null; nodeType = 1; }", "ownerDocument"],
  ["class field", "class N {\n  public readonly EDGE?: N[] = [];\n  appendChild() {}\n}", "childNodes"],
  ["class field", "const o = {\n  tag: 'div',\n  EDGE: kids\n};", "children"],   // an object literal's last line without a trailing comma: an edge init, read as a declared field
  ["parameter property", "class N { constructor(private EDGE: N[] = []) {} appendChild() {} }", "children"],
  ["parameter property", "class N {\n  constructor(public readonly EDGE: N | null, m: Map<string, N> = new Map()) {}\n  appendChild() {}\n}", "parentNode"],
  ["parameter property", "class N { constructor(readonly EDGE: N) {} nodeType = 1; }", "ownerDocument"],
  ["assignment", "class N { constructor() { this.EDGE = null; } appendChild() {} }", "parentNode"],
  ["assignment", "function N(p) { this.EDGE = p; this.appendChild = () => 0; }", "parent"],
  ["assignment", "function mk() { const n: any = {}; n.EDGE = []; n.appendChild = () => 0; return n; }", "children"],
  ["assignment", "const attach = (c, p) => { c.EDGE = p; p.kids.push(c); c.nodeType = 1; };", "parentNode"],
  ["assignment", "root.EDGE = doc; root.tagName = 'HTML';", "ownerDocument"],
  ["assignment", "shadow.EDGE = el; shadow.appendChild(el);", "host"],
  ["assignment", "c.EDGE = this.host; c.appendChild(x);", "parentNode"],   // a this.-rooted member: an edge write, whatever it holds
  ["assignment", "const self: any = { postMessage() {} }; self.EDGE = self;", "parent"],   // a window stand-in that is its own parent
  // the eleventh name, in three shapes
  ["object-literal key", "const n = { tagName: 'DIV', EDGE: null };", "parentElement"],
  ["class field", "class N {\n  EDGE: N | null = null;\n  appendChild() {}\n}", "parentElement"],
  ["assignment", "c.EDGE = p; c.appendChild(x);", "parentElement"],
  // a parenthesised type right after the colon is a type, not a call
  ["class field", "class N {\n  EDGE!: (N | Txt | string)[];\n  appendChild() {}\n}", "childNodes"],
  ["class field", "class N { tag = 'x'; EDGE: (N | null)[] = []; nodeType = 1; }", "children"],
  // an object-literal accessor: the incident's own shape
  ["accessor", "const n = { tag: 'div', get EDGE() { return n.kids[0] || null; } };", "firstChild"],
  ["accessor", "const n = {\n  get EDGE() { return doc; },\n  tag: 'div',\n};", "ownerDocument"],
  ["accessor", "function mk() { return { get EDGE() { return null; }, appendChild() {} }; }", "parentNode"],
  // the lexer blanks literals and comments, not the code around them
  ["assignment", "const s = 'x'; n.EDGE = null;", "parentNode"],   // code after a string
  ["assignment", "const q = a / b; n.EDGE = null; const r = c / d;", "children"],   // two divisions are not a regex literal
  ["assignment", "const u = \"http://x\"; n.EDGE = null;", "parentNode"],   // a slash pair inside a string is not a comment
  ["assignment", "const e = 'it\\'s'; n.EDGE = null;", "parent"],   // an escaped quote does not end the string
  ["assignment", "const t = `a ${'}'} b`; n.EDGE = null;", "parentNode"],   // a template hole holding a brace
  ["object-literal key", "/* a fake */ const n = { EDGE: null }; // attached later", "parentNode"],   // code between comments
  ["object-literal key", "const n = { re: /x\\/y/g, EDGE: null };", "parentNode"],   // an escaped slash inside a regex
  ["object-literal key", "const n = { re: /[/]/, EDGE: [] };", "children"],   // a slash inside a regex's character class
  ["assignment", "const v = x ? `${a}` : `${b}`; n.EDGE = null;", "parentNode"],   // two templates on a line
  // the operand test reads the blanked text: a comment before the slash is skipped, not read as an operand
  ["assignment", "x = 1; // note\n/it's/.test(s); n.EDGE = null;", "parentNode"],   // a line-leading regex after a trailing comment: a regex, whose quote opens no string
  ["assignment", "const q = x /* c */ / 2; n.EDGE = null; const r = y / 3;", "children"],   // a block comment between the operand and a division
  // a slash after a postfix ++ or -- is a division: the code up to the next slash stays code
  ["assignment", "const v = x++ / 2; n.EDGE = null; const w = y / 3;", "parentNode"],
  ["assignment", "const v = x-- / 2; n.EDGE = null; const w = y / 3;", "nextSibling"],
  // a slash after a closing quote or backtick is a division: a string or template literal is an operand
  ["assignment", "const x = '10' / 2; n.EDGE = null; const y = a / b;", "parentNode"],
  ["assignment", "const x = \"10\" / 2; n.EDGE = null; const y = a / b;", "children"],
  ["assignment", "const x = `10` / 2; n.EDGE = null; const y = a / b;", "parent"],
  // a conditional whose final operand is an admitted value, read after its last colon
  ["assignment", "win.EDGE = opts.framed ? {} : win;", "parent"],   // the window stand-in of a framed-pane test
  ["assignment", "win.EDGE = framed ? {} : win;\nwin.postMessage = post;", "parent"],
  ["assignment", "n.EDGE = x ? { a: 1 } : kid;", "firstChild"],   // a colon inside the middle operand
  ["class field", "class N {\n  EDGE = flag ? null : this;\n  appendChild() {}\n}", "parentNode"],
];
const NEGATIVE: Array<[string, string, string]> = [   // [what it is, scratch source, edge name]
  ["a comparison, not an assignment", "if (n.EDGE === null) n.appendChild(c); if (m.EDGE == null) return;", "parentNode"],
  ["a field typed as a primitive", "class N {\n  EDGE: string;\n  appendChild() {}\n}", "host"],
  ["a field typed as a primitive union", "class N { EDGE!: string | null; nodeType = 1; }", "parent"],
  ["a type literal keyed on a primitive", "type Row = { EDGE: string; nodeType: number };", "host"],
  ["a plain parameter default, no modifier", "function mk(EDGE = [], tagName = 'div') { return { tagName }; }", "children"],
  ["an arrow parameter", "const f = (EDGE) => EDGE.appendChild(x);", "children"],
  ["a static field", "class N { static EDGE: N[] = []; appendChild() {} }", "children"],
  ["a member-expression value not rooted at this (out of scope)", "up.EDGE = g.document; up.appendChild(x);", "ownerDocument"],
  ["a constructed value (out of scope)", "class N { EDGE = new Doc(); appendChild() {} }", "ownerDocument"],
  ["an object literal as the value (out of scope)", "win.EDGE = {}; win.postMessage = post;", "parent"],
  ["a hidden define", "Object.defineProperty(this, 'EDGE', { value: null, enumerable: false }); this.appendChild(c);", "parentNode"],
  ["a length reset", "n.EDGE.length = 0; n.appendChild(c);", "children"],
  ["a caller of the shared module that initialises no edge of its own (no shape, whatever it imports)", "import { nodeFactory } from './test-dom-shim';\nconst makeNode = nodeFactory();\nmakeNode('div').appendChild(makeNode('span'));", "parentNode"],
  ["a source pin quoting the payload field", "assert.match(RENDER, /openThing\\(\\{ name, host: hostOf\\(sid\\) \\}\\)/); el.appendChild(c);", "host"],
  ["a payload literal naming a machine", "const lane = { host: h, sid, appendChild: 0 };", "host"],
  ["a payload literal's last line, an identifier (host is left out of the declared-only form)", "const lane = {\n  sid,\n  EDGE: h\n};", "host"],
  ["a declared-only host field (left out with the payload lines)", "class N {\n  EDGE: H;\n  appendChild() {}\n}", "host"],
  ["an object literal's last line, a string value", "const o = {\n  tag: 'div',\n  EDGE: 'none'\n};", "parent"],
  ["an object literal's last line, a number", "const o = {\n  tag: 'div',\n  EDGE: 3\n};", "children"],
  ["an object literal's last line, a boolean", "const o = {\n  tag: 'div',\n  EDGE: true\n};", "parent"],
  ["an object literal's last line, a call", "const o = {\n  tag: 'div',\n  EDGE: count(kids)\n};", "children"],
  ["a declared field with a default after a parenthesised type", "class N {\n  EDGE: (N | null)[] = mk();\n}", "children"],   // the value is a call, not a bare identifier
  ["a class accessor after another member (on the prototype, no edge)", "class N {\n  tag = 'x';\n  get EDGE() { return this.kids[0] || null; }\n}", "firstChild"],
  ["a setter alone (no getter to read)", "const n = { tag: 'x', set EDGE(v) { n._p = v; } };", "parentNode"],
  // one-line destructuring and type-literal forms: the brace follows `(`, `=`, `,`, let, const or var, so it opens no class
  // body, and a `;` inside that one-line brace group anchors no member either
  ["a destructuring pattern with a default, on one line", "function mk({ EDGE = [], tag }) { return tag; }", "children"],
  ["a destructuring declaration with a default", "let { EDGE = null } = o;", "parent"],
  ["a destructuring declaration with a default, const", "const { EDGE = null, tag } = o;", "parent"],
  ["a destructuring default after a comma", "function mk(a, { EDGE = [] }) { return a; }", "children"],
  ["a type literal's member, semicolon-separated on one line, as the first member, with a union type (a bare-name type there reads as an object-literal key, INDISTINGUISHABLE below)", "type N = { EDGE: N | null; tagName: string };", "parent"],
  ["a type literal's member, semicolon-separated on one line, after another member", "type N = { tag: string; EDGE: N | null; id: string };", "parent"],
  // literals and comments are blanked before the shapes are read: each kind, holding a shape
  ["a line comment holding a shape", "// the fake keeps EDGE: null until attached\nconst n = { tag: 'div' };", "parentNode"],
  ["a block comment holding a shape", "/* class N { EDGE = null; } */\nconst n = { tag: 'div' };", "parentNode"],
  ["a doc comment holding a shape", "/** `{ EDGE: [] }` is the shape */\nconst n = { tag: 'div' };", "children"],
  ["a trailing comment holding an assignment", "n.tag = 'div'; // then n.EDGE = null", "parentNode"],
  ["a double-quoted string holding a shape", "const src = \"class N { EDGE = null; }\";", "parent"],
  ["a single-quoted string holding an assignment (a source pin quoting a product line)", "assert.ok(FED.includes('if (out.type === \"x\") out.EDGE = EDGE;'));", "host"],
  ["a template literal holding a shape", "const src = `class N { EDGE: N | null = null; }`;", "parent"],
  ["a template literal's text is not code, its hole is", "const src = `n.EDGE = ${JSON.stringify(v)}`;", "children"],
  ["a regex literal holding a typed parameter (a source pin quoting a signature)", "assert.match(FEED, /absorb\\(card: HTMLElement, EDGE: HTMLElement\\)/);", "parent"],
  ["a regex literal after return", "function f() { return /EDGE: null/.test(s); }", "parentNode"],
  ["a regex literal with a character class holding a slash", "const re = /[/]EDGE: null/; n.appendChild(c);", "parentNode"],
  ["a string holding a slash pair, then a shape in a comment", "const u = \"http://x\"; // n.EDGE = null", "parentNode"],
  // the operand test reads the blanked text, so a comment's last word before a line-leading regex is no operand
  ["a regex pin on the line after a trailing line comment", "const pins = [\n  /a/,   // one\n  /\\{ EDGE: null \\}/,   // two\n];", "parentNode"],
  ["a cascade of regex pins, one per line, each with a trailing comment", "const pins = [\n  /x/,   // note\n  /class N { EDGE = []; }/,   // a class\n  /\\{ EDGE: undefined \\}/,   // a literal\n];", "children"],
  ["a regex after the semicolon that follows a postfix increment (the ++ rule reads the two characters before the slash)", "i++; /\\{ EDGE: null \\}/.test(s);", "parentNode"],
  ["a division after a string, then a regex pin: the pin is a regex, not code", "const a = 'x' / 2; const s = /{ EDGE: null }/;", "parentNode"],
  ["a division after a template, then a regex pin", "const a = `x` / 2; const s = /class N { EDGE = []; }/;", "children"],
  ["a conditional with a member-expression head whose final operand is an object literal (out of scope)", "win.EDGE = opts.framed ? win : {};", "parent"],
  ["a conditional with a member-expression head whose final operand is a member expression (out of scope)", "win.EDGE = opts.framed ? win : g.top;", "parent"],
  ["a conditional carrying a call (out of scope)", "n.EDGE = mk(x ? y : kid);", "firstChild"],
  ["a comparison inside a conditional, not an assignment", "const same = n.EDGE === x ? a : kid;", "parentNode"],
  ["a logical value (out of scope)", "n.EDGE = p || null; m.EDGE = p && q;", "parentNode"],
  // the shapes the docstring names out of scope by design, one case each, so a detector that starts reading one of
  // them moves its case to POSITIVE and the docstring's account (and the callers-pin message) with it
  ["a shorthand key, inline or alone on a line (out of scope)", "const n = { tag: 'div', EDGE, appendChild() {} };\nconst m = {\n  tag: 'span',\n  EDGE,\n};", "children"],
  ["a computed key, a string or an identifier (out of scope)", "const n = { ['EDGE']: null, tag: 'div' }; const m = { [k]: null, tag: 'span' };", "parentNode"],
  ["a spread of an object built elsewhere (out of scope)", "const edges = Object.fromEntries([['EDGE', null]]);\nconst n = { tag: 'div', ...edges, appendChild() {} };", "parentNode"],
  ["a bracket-notation write (out of scope)", "c['EDGE'] = this; c.appendChild(x);", "parentNode"],
  ["a compound assignment (out of scope)", "c.EDGE ??= this; d.EDGE ||= this; c.appendChild(x);", "parentNode"],
  ["a class field whose type starts on the line after the colon, with an initializer or declared only (out of scope)", "class N {\n  tag = 'x';\n  EDGE:\n    N | null = null;\n  appendChild() {}\n}\nclass M {\n  tag = 'y';\n  EDGE:\n    M | null;\n}", "parentNode"],
];
const INDISTINGUISHABLE: Array<[string, string, string, string]> = [   // [what it is, the shape it reads as, scratch source, edge name]
  // the forms a line start reaches: a destructuring default or a type literal's member on its own line
  ["a destructuring pattern with a default, wrapped over lines", "class field", "function mk({\n  EDGE = [],\n  tag,\n}) { return tag; }", "children"],
  ["a type literal's member, semicolon-separated, on its own line", "class field", "type N = {\n  EDGE: N | null;\n  tagName: string;\n};", "parent"],
  ["a type literal's member, comma-separated (an object-literal key to the regex)", "object-literal key, identifier value", "type N = { EDGE: N, tagName: string };", "parent"],
  ["a type literal's first member with a bare-name type, semicolon-separated on one line", "object-literal key, identifier value", "type N = { EDGE: El; tagName: string };", "parent"],
  ["a type literal's readonly member after a comma", "parameter property", "type N = { a: 1, readonly EDGE: N[] };", "children"],
  ["a typed parameter after a comma, in code", "object-literal key, identifier value", "function mk(a: El, EDGE: El) {}", "parent"],
  // a class body and a function body are the same brace to a regex
  ["a statement reassigning a local of an edge name at line start", "class field", "let EDGE: N | null = null;\nfunction reset(other) {\n  EDGE = other;\n}", "parent"],
  ["a statement reassigning a local of an edge name after a semicolon", "class field", "x(); EDGE = []; y();", "children"],
  ["a class whose first member is an edge getter (on the prototype, no edge)", "accessor", "class N { get EDGE() { return this.kids[0] || null; } appendChild() {} }", "firstChild"],
  // a brace after a name or a colon is a class brace to the regex, so a one-line interface or annotation reads as a class
  ["an interface's member, semicolon-separated on one line, after another member", "class field", "interface N { tagName: string; EDGE: N | null; }", "parent"],
  ["a type literal in an annotation, semicolon-separated on one line, after another member", "class field", "let o: { tag: string; EDGE: N | null; };", "parent"],
  // a condition's closing paren and an expression's are the same token to the lexer, so the regex is read as a division
  ["a regex literal right after a condition's closing paren (read as a division: its text stays code)", "class field", "if (x) /class N { EDGE = null; }/.test(y);", "parentNode"],
];
// the misreads the lexer docstring accepts: a literal read as code whose quote or backtick then swallows the code after
// it, or a division after a closing brace read as a regex that runs to the next slash on the line, HIDING a shape (a
// false negative, never a false positive). Each is pinned so a lexer that starts reading the write moves the case to
// POSITIVE and the docstring's account with it.
const ACCEPTED_MISREADS: Array<[string, string, string]> = [   // [what it is, scratch source, edge name]
  ["a quote inside a regex right after a condition's closing paren opens a string to the line end", "if (x) /'/.test(y); const n = { EDGE: null };", "parentNode"],
  ["a backtick inside such a regex opens a template to the next backtick in the file", "if (x) /`/.test(y);\nconst n = { EDGE: null };\nconst t = `z`;", "parentNode"],
  ["a division after a closing brace opens a regex to the next slash on the line", "const q = {} / 2; n.EDGE = null; const r = y / 3;", "parentNode"],
];
test("the detector: each shape trips on a scratch source, its near-misses do not, and the code this detector does not tell from a shape trips as the docstring says", () => {
  for (const [shape, src, edge] of POSITIVE) {
    const shapes = edgeShapes(scratch(src, edge));
    assert.ok(shapes.includes(shape), shape + " (" + edge + ") trips on " + JSON.stringify(src) + "; got " + JSON.stringify(shapes));
    assert.ok(needsListing(scratch(src, edge)), shape + " (" + edge + "): the source initialises an edge and, without the credential, needs listing");
  }
  for (const [what, src, edge] of NEGATIVE) assert.ok(!initsEdge(scratch(src, edge)), what + " does not trip: " + JSON.stringify(src) + "; matched " + JSON.stringify(edgeShapes(scratch(src, edge))));
  for (const [what, shape, src, edge] of INDISTINGUISHABLE) {
    const shapes = edgeShapes(scratch(src, edge));
    assert.ok(shapes.includes(shape), what + " reads as " + JSON.stringify(shape) + ": " + JSON.stringify(src) + "; got " + JSON.stringify(shapes) + " (if the detector now tells it apart, move the case to NEGATIVE and the docstring's account with it)");
  }
  for (const [what, src, edge] of ACCEPTED_MISREADS) assert.ok(!initsEdge(scratch(src, edge)), what + ", a false negative the docstring names: " + JSON.stringify(src) + "; matched " + JSON.stringify(edgeShapes(scratch(src, edge))) + " (if the lexer now reads the write, move the case to POSITIVE and the docstring's account with it)");
  assert.equal(Object.keys(EDGE_INIT).length, 6, "six shapes, each with a positive above");
  for (const shape of Object.keys(EDGE_INIT)) assert.ok(POSITIVE.some(([s]) => s === shape), shape + " has a positive case");
});

test("the credential: an import of nodeFactory or hideEdges from the shared module (named or namespace, either quote style, .js or not) plus a call in code; an import alone, an alias, a callback reference, a type import, a local helper or a call token in a comment or a string is not it", () => {
  const cls = scratch("class N {\n  EDGE!: N | null;\n  constructor() { hideEdges(this); }\n  appendChild() {}\n}\n", "parentNode");
  const bare = scratch("class N {\n  EDGE!: N | null;\n  appendChild() {}\n}\n", "parentNode");
  assert.ok(initsEdge(bare) && needsListing(bare), "the class alone is detected and must be listed");
  assert.ok(needsListing(cls), "a hideEdges( call without the import (a local helper of that name) is not the credential");
  const imports = [
    'import { hideEdges } from "./test-dom-shim";\n', "import { hideEdges } from './test-dom-shim';\n",
    'import { nodeFactory, hideEdges } from "../test-dom-shim";\n', "import { nodeFactory, hideEdges } from '../test-dom-shim';\n",
  ];
  for (const imp of imports) {
    assert.ok(initsEdge(imp + cls) && !needsListing(imp + cls), "with " + JSON.stringify(imp.trim()) + " and a call: detected, switched, not listed");
    assert.ok(needsListing(imp + bare), "with " + JSON.stringify(imp.trim()) + " and no call: the import alone is not switching");
  }
  const factory = scratch("import { nodeFactory } from './test-dom-shim';\nconst makeNode = nodeFactory();\nconst n = makeNode('div'); n.EDGE = null;\n", "parentNode");
  assert.ok(initsEdge(factory) && !needsListing(factory), "a nodeFactory( call behind a single-quoted specifier is switching");
  assert.ok(needsListing('import { FLAT_RECT } from "./test-dom-shim";\n' + cls), "importing a constant alone is not switching, whatever the file calls");
  assert.ok(needsListing('import { hideEdges as hide } from "./test-dom-shim";\n' + scratch("class N {\n  EDGE!: N | null;\n  constructor() { hide(this); }\n}\n", "parentNode")), "a call under an alias is not read: call it by its own name");
  assert.ok(needsListing('import { hideEdges } from "./test-dom-shim";\n' + scratch("class N {\n  EDGE!: N | null;\n}\n[new N()].forEach(hideEdges);\n", "parentNode")), "a reference passed as a callback is not a call");
  assert.ok(needsListing('// import { hideEdges } from "./test-dom-shim";\n' + cls), "a commented-out import is not an import");
  assert.ok(needsListing('/* import { hideEdges } from "./test-dom-shim"; */\n' + cls), "an import inside a block comment is not an import");
  assert.ok(needsListing('import type { ShimOptions } from "./test-dom-shim";\n' + cls), "a type import is not one");
  // the .js suffix on the specifier, named and namespace
  assert.ok(!needsListing('import { hideEdges } from "./test-dom-shim.js";\n' + cls), "a .js-suffixed specifier on a named import is read");
  const ns = scratch("class N {\n  EDGE!: N | null;\n  constructor() { shim.hideEdges(this); }\n  appendChild() {}\n}\n", "parentNode");
  for (const imp of ['import * as shim from "./test-dom-shim";\n', "import * as shim from '../test-dom-shim';\n", 'import * as shim from "../test-dom-shim.js";\n']) {
    assert.ok(initsEdge(imp + ns) && !needsListing(imp + ns), "with " + JSON.stringify(imp.trim()) + " and shim.hideEdges(: detected, switched, not listed");
    assert.ok(needsListing(imp + bare), "with " + JSON.stringify(imp.trim()) + " and no call: the namespace import alone is not switching");
  }
  assert.ok(needsListing('import * as shim from "./test-dom-shim";\n' + cls), "a namespace import with a bare hideEdges(this) call: the call is under no such name, not read");
  assert.ok(needsListing('import * as other from "./test-dom-shim";\n' + ns), "a namespace import under another alias than the call's is not it");
  const factoryNs = scratch("import * as dom from './test-dom-shim';\nconst makeNode = dom.nodeFactory();\nconst n = makeNode('div'); n.EDGE = null;\n", "parentNode");
  assert.ok(initsEdge(factoryNs) && !needsListing(factoryNs), "dom.nodeFactory( under a namespace import is switching");
  // the alias may carry a dollar sign, first or twice, and the call is read under the alias alone, not under a longer name that ends in it
  for (const alias of ["$dom", "a$b$c", "_$s"]) {
    const call = scratch("class N {\n  EDGE!: N | null;\n  constructor() { ALIAS.hideEdges(this); }\n  appendChild() {}\n}\n".replace(/ALIAS/g, alias), "parentNode");
    assert.ok(initsEdge(call) && !needsListing("import * as " + alias + " from \"./test-dom-shim\";\n" + call), "alias " + alias + ": the call under it is switching");
  }
  assert.ok(needsListing('import * as $s from "./test-dom-shim";\n' + scratch("class N {\n  EDGE!: N | null;\n  constructor() { x$s.hideEdges(this); }\n}\n", "parentNode")), "a call under a longer name that ends in the alias (x$s for $s) is not it");
  assert.ok(needsListing('import * as shim from "./test-dom-shim";\n' + scratch("class N {\n  EDGE!: N | null;\n  constructor() { $shim.hideEdges(this); }\n}\n", "parentNode")), "a call under a longer name that ends in the alias ($shim for shim) is not it");
  // the import is a statement in code: the shim's import line quoted inside a template or a backslash-continued string, beside a local helper of the name, is not one
  const local = "function hideEdges(o: any) { return o; }\n";
  assert.ok(needsListing("const SRC = `\nimport { hideEdges } from \"./test-dom-shim\";\n`;\n" + local + cls), "an import line quoted inside a multi-line template is not an import");
  assert.ok(needsListing("const SRC = `\n  import * as shim from './test-dom-shim';\n`;\n" + scratch("const shim = { hideEdges(o: any) { return o; } };\nclass N {\n  EDGE!: N | null;\n  constructor() { shim.hideEdges(this); }\n}\n", "parentNode")), "a namespace import line quoted inside a template is not an import");
  assert.ok(needsListing("const SRC = \"a\\\nimport { hideEdges } from './test-dom-shim';\\\nb\";\n" + local + cls), "an import line inside a backslash-continued string is not an import");
  // a call token that is not code: in a line comment, a doc comment, a string, a template
  const imp = 'import { hideEdges } from "./test-dom-shim";\n';
  assert.ok(needsListing(imp + bare + "// TODO: hideEdges(this) in the constructor\n"), "a call token in a line comment is not a call");
  assert.ok(needsListing(imp + "/** every node goes through hideEdges( */\n" + bare), "a call token in a doc comment is not a call");
  assert.ok(needsListing(imp + bare + "const note = 'hideEdges(this)';\n"), "a call token in a string is not a call");
  assert.ok(needsListing(imp + bare + "const note = `nodeFactory()`;\n"), "a call token in a template is not a call");
  assert.ok(!needsListing(imp + bare + "const note = 'x'; hideEdges(new N()); // hideEdges(this)\n"), "a call in code beside a string and a comment is a call");
  for (const f of SWITCHED) assert.ok(switched(src(f)), f + " imports nodeFactory or hideEdges and calls it");
});
