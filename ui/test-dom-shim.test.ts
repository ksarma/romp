// The shared fake-DOM shim's PROJECTION RULE, pinned on its own (ui/test-dom-shim.ts; ui/timeline-tags-scale.test.ts
// pins it over a live dialog at scale), and a RATCHET over the other UI test files, one rule for every file under
// ui/: a test file whose CODE initialises an edge-named property (parentNode, parentElement, parent, childNodes,
// children, firstChild, lastChild, nextSibling, previousSibling, ownerDocument or host) as a plain enumerable own
// property, in any shape the detector below reads (comments and the contents of string, template and regex literals
// are blanked first, so a source pin or a comment is not code), either CALLS hideEdges( or nodeFactory( imported from
// the shared shim (a named or a namespace import, either quote style on the specifier, with or without .js; an import
// without a call in code is not switched) or is named on the allowlist below, the files that predate the rule, whose
// length ALLOWLIST_MAX pins exactly: a renamed file replaces its entry, a file that comes off lowers the constant in
// the same commit, a new file may not join. There is no vocabulary gate: a window stand-in's parent, a goal
// fixture's children and a class's parentNode are the same kind of property, a failing dump walks each, and the
// cure for a fake is the same one-line call. The rule hides the edges at CREATION: a property product code hangs on a node
// later enumerates, whatever its type, and a node-valued one re-opens a path for a failing dump to walk; the
// projection pins here and in the tags-scale test, plus the runner's cgroup cap, are the backstop for that. Source
// pins over ui/**/*.test.ts, the repo convention. Why both: on 2026-09-09 a failing strict assertion with a fake
// node on one side allocated tens of GB (node's assert dumps both sides at depth 1000 with getters on, then diffs
// the dumps with a Myers trace that costs 8N^2 bytes outside the V8 heap); the projection is what stops it, and the
// class-based shims still can do it (a feed card in ui/webview/feed-keynav-covered.test.ts dumps as 318,835 lines).
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
/** A file INITIALISES AN EDGE when it makes one of the eleven edge names (parentNode, parentElement, parent, childNodes,
 *  children, firstChild, lastChild, nextSibling, previousSibling, ownerDocument or host) an own enumerable property in
 *  any of these shapes, with null, undefined, [], this, a this.-rooted member or call, or a bare identifier as the
 *  value. What the property belongs to does not matter: a fake node, a window stand-in, a goal tree's fixture or a list
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
 *    declared field is an own enumerable property once the constructor assigns it), anywhere on a line (`tag = "x";
 *    private EDGE: N | null = null;`). A field typed as a primitive (string, number, boolean) is no edge and is
 *    skipped. In the declared-only form the key host is left out too, and a value that starts with a quote, a digit
 *    or a boolean, or that contains a parenthesis other than a parenthesised type right after the colon
 *    (`EDGE!: (N | Txt | string)[];` is read; `host: hostOf(sid)` is not), is skipped: the last line of a multi-line
 *    object literal without a trailing comma (`host: "x"`, `EDGE: 3`, `EDGE: count(kids)`) reads as a declared
 *    field, and those lines are payload, not edges;
 *  - a constructor parameter property (`constructor(public EDGE: N[] = [])`, with or without a default);
 *  - an assignment through any name (`this.EDGE = null`, `n.EDGE = []`, `c.EDGE = p`, `c.EDGE = this.host`).
 *  Out of scope, by design: an edge under another name (a `kids` list), a shorthand key (`{ EDGE }`, or `EDGE,` alone
 *  on a line), a value that is a member expression, a call or a `new` not rooted at this (`up.EDGE = g.document`,
 *  `EDGE = new Doc()`), an object literal or a non-empty array literal as the value (`win.EDGE = {}`,
 *  `EDGE: [kidA, kidB]`, `n.EDGE = [a, b]`), an Object.defineProperty of an edge whatever its enumerable flag (a
 *  descriptor holding a getter defeats a regex), and a declared field whose type carries a comma (`EDGE:
 *  Record<string, N>;`). A regex reads shape, not meaning, and some code that initialises no edge reads as a shape:
 *  a destructuring default at line start (`function mk({\n  EDGE = [],\n})`) reads as a class field, where the
 *  one-line forms do not (a brace after `(`, `=`, `,`, let, const or var opens no class body, and a `;` inside such a
 *  one-line brace group separates type members, not class members, so `type N = { tag: string; EDGE: N | null }` is
 *  told apart; a brace after a name or a colon is a class brace to the regex, so a one-line `interface N { tag:
 *  string; EDGE: N | null; }` or `o: { tag: string; EDGE: N | null; }` reads as a class field); a type literal's
 *  member on its own line (`type N = {\n  EDGE: N | null;\n}`), or comma-separated on one line (`type N = { EDGE: N,
 *  tag: string }`), reads as a class field or an object-literal key; a type literal's readonly member after a comma
 *  reads as a parameter property; a typed parameter after a comma whose type is a bare name (not a union, an array
 *  or a generic), in code (`function mk(a: El, EDGE: El)`), reads as an object-literal key; a statement reassigning a
 *  local of an edge name at line start or after `;` or `{` (`EDGE = el;`, with null, undefined, [], this or a bare
 *  identifier on the right) reads as a class field, since a class body and a function body are the same brace to a
 *  regex, so the remedy is to rename the local; a class whose first member is an edge getter reads as an
 *  object-literal accessor. INDISTINGUISHABLE below pins each; a file that carries one renames the local or the
 *  parameter, or is carried on the documented non-DOM list (the newcomer paths in the ratchet's first message). */
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
 *  bracket, the second character of a postfix `++` or `--` (`x++ / 2`), or a name is a division, a name excepted
 *  after return, typeof, case and the like. A regex that does not close on its line is read as a division, since a
 *  regex literal cannot span lines. One paren the lexer cannot tell apart: a regex right after a condition's closing
 *  paren (`if (x) /re/.test(y)`) is read as a division, so its text stays code (INDISTINGUISHABLE below pins the
 *  shape it trips as), and a quote or a backtick inside it opens a string to the line end or a template to the next
 *  backtick in the file, hiding an edge init there: a false negative the ratchet accepts (ACCEPTED_MISREADS below
 *  pins it; the tree holds none, measured against a TypeScript-AST blanking of every UI test file). A light lexer,
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
/** The credential: an import of hideEdges or nodeFactory from the shared module AND a call of one of them, in code.
 *  The import is a statement in code at line start (its text up to the specifier reads the same once every literal
 *  is blanked: an import line quoted inside a template or a backslash-continued string is not one), either quote
 *  style on the specifier, with or without a .js suffix, as a named import (`import { hideEdges } from
 *  "./test-dom-shim"`) or a namespace import (`import * as shim from "../test-dom-shim"`, the alias any identifier,
 *  dollar signs included); the call is `hideEdges(` or `nodeFactory(` for a named import and `shim.hideEdges(` or
 *  `shim.nodeFactory(` under the namespace's own alias, not under a longer name that ends in it. An import alone
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

// The test files whose code initialised an edge on 2026-09-10 without calling the shared module, each named: the
// files that predate the rule, for the stacked migration PR to switch. ALLOWLIST_MAX is the list's exact length: a
// file that switches (a hideEdges call on its object, at the end of each constructor for a class, or nodeFactory for
// its nodes, plus a projection test) comes off and the constant comes down in the same commit; a renamed file
// replaces its entry; a new file may not join. Most are class-based webview shims (El and Txt, FakeNode, E, FakeEl,
// Elm) with a prototype firstChild, so no 2^depth term, but the whole-tree walk through parentNode or parentElement
// (parent in several, an ownerDocument beside it in the two track-decorations files) remains, and feed.ts hangs node
// references on cards. Others hold a window stand-in (a parent that is the stand-in itself, or a record) or a goal
// fixture with a children list: dumps of a few lines today, listed because the rule is uniform and the cure is the
// same call on the object.
const ALLOWLIST = [
  "webview/actions.test.ts",
  "webview/anchor-map-block-edges.test.ts",
  "webview/anchor-map-boundary-points.test.ts",
  "webview/anchor-map-change-marks.test.ts",
  "webview/anchor-map-fallback-markup.test.ts",
  "webview/anchor-map-rendered-points.test.ts",
  "webview/anchor-map-wrapped-code.test.ts",
  "webview/anchor-map.test.ts",
  "webview/card-subgoals.test.ts",
  "webview/chat-exact-tail-exec.test.ts",
  "webview/codex-meta-choices.test.ts",
  "webview/feed-keynav-click-focus.test.ts",
  "webview/feed-keynav-covered.test.ts",
  "webview/feed-keynav-tabscope-covered.test.ts",
  "webview/feed-keynav-typing.test.ts",
  "webview/feed-render-incremental.test.ts",
  "webview/federation-hidden-hold.test.ts",   // a conditional-valued window parent, read since the sixth review round
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
  "webview/file-comments-markclick-controls.test.ts",
  "webview/file-comments-markclick.test.ts",
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
  "webview/file-comments-seen-fixes.test.ts",
  "webview/file-comments-seen-review2.test.ts",
  "webview/file-comments-seen-review3.test.ts",
  "webview/file-comments-send-note.test.ts",
  "webview/file-comments-send-resolves.test.ts",
  "webview/file-comments-send-seen.test.ts",
  "webview/file-comments-todo-choices-review.test.ts",
  "webview/file-comments-todo-choices.test.ts",
  "webview/file-comments-todopick-focus.test.ts",
  "webview/file-comments.test.ts",
  "webview/file-view-edit-events.test.ts",
  "webview/file-view-edit-races.test.ts",
  "webview/file-view-figures-absolute.test.ts",
  "webview/file-view-links.test.ts",
  "webview/file-view-notice.test.ts",
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
  "webview/perf-telemetry.test.ts",
  "webview/pinned-notes.test.ts",
  "webview/pr-links.test.ts",
  "webview/render-todo-file-chip.test.ts",
  "webview/setting-stale-fold.test.ts",
  "webview/shell-perf.test.ts",
  "webview/strip.test.ts",
  "webview/tab-row-keep.test.ts",
  "webview/tab-snapshot-view.test.ts",
  "webview/tab-strip-skip-exec.test.ts",
  "webview/thread-selection-scope.test.ts",
  "webview/timeline-boot.test.ts",
  "webview/timeline-rehover.test.ts",
  "webview/track-decorations-guards.test.ts",
  "webview/track-decorations-hover-cost.test.ts",
  "webview/track-decorations-kept-embed.test.ts",
  "webview/track-decorations.test.ts",
  "webview/url-links.test.ts",
  "webview/user-todo-links.test.ts",
  "webview/user-todo-title-links.test.ts",
  "webview/waiting-detail-link.test.ts",
  "webview/waiting-file-chip-unframed.test.ts",
  "webview/waiting-file-chip.test.ts",
];
// The list's exact length on 2026-09-10, after the detector's fourth round: the 148 files whose code initialised an
// edge when the rule was written, plus the eight class fakes main added between this branch's base and its landing
// (actions, file-comments-markclick, file-comments-markclick-controls, file-comments-seen-fixes, -seen-review2,
// -seen-review3, file-comments-send-seen, file-view-notice), listed at the final rebase because they predate the rule,
// plus federation-hidden-hold, whose conditional-valued window parent the sixth review round's detector reads.
// The ratchet pins it by equality, so a file that comes off lowers this in the same commit, a renamed file leaves it
// alone, and a new file may not join: neither the list nor this number goes up. A same-commit swap (one off, one on)
// is the one move no count pin sees; the first assertion's allowlist-versus-detected diff is what names the newcomer.
const ALLOWLIST_MAX = 157;
// the sixteen files on the shared module (2026-09-10): the fifteen whose near-copies of the shim it replaced, and the
// tags-scale test whose shim it grew from
const SWITCHED = [
  "timeline-hidden-hold.test.ts", "timeline-hidden-stub.test.ts", "timeline-kernel-post.test.ts", "timeline-live-tick.test.ts",
  "timeline-nan-window.test.ts", "timeline-open-interval.test.ts", "timeline-pending-hosts.test.ts", "timeline-render.test.ts",
  "timeline-tagbtn-click.test.ts", "timeline-tagorder-drag.test.ts", "timeline-tags-scale.test.ts", "timeline-theme-light.test.ts",
  "timeline-transform-tick.test.ts", "timeline-views-ack.test.ts", "timeline-zoom-anchor.test.ts", "webview/tab-color-picker.test.ts",
];

test("ratchet: every UI test file that initialises an edge calls the shared module or is on the allowlist, every allowlisted file still needs it, and the list's length is its pinned count", () => {
  const files = testFiles();
  assert.ok(files.includes("test-dom-shim.test.ts") && files.includes("webview/tab-color-picker.test.ts"), "the sweep covers ui/ and ui/webview/");
  const matching = files.filter((f) => needsListing(src(f)));
  assert.deepEqual(matching.filter((f) => !ALLOWLIST.includes(f)), [],
    "a UI test file's code initialises an edge-named property (parentNode, parentElement, parent, children, childNodes, a child or sibling pointer, " +
    "ownerDocument or host) without calling the shared module; a failing assertion on such an object can allocate tens of GB. Three paths, one import and " +
    "one line each: (1) a fake DOM: build its nodes with nodeFactory(, or call hideEdges(this) at the end of the class's constructor (hideEdges(obj) on an " +
    "object literal), imported from ui/test-dom-shim.ts as a named import or a namespace import (shim.hideEdges(); a .js suffix on the specifier is read " +
    "too). The import alone is not enough, and a call token in a comment or a string is not a call: the call in code is what counts. (2) A non-DOM use of an " +
    "edge name (a local reassigned at line start, a typed parameter after a comma, a type literal's member, a fixture's field): rename it, or carry the file " +
    "on the documented non-DOM list with its reason (that list lands with the stacked migration PR; until then ask the reviewer). (3) The allowlist below is " +
    "closed: it names the files that predate the rule, a renamed listed file replaces its entry, and neither the list nor ALLOWLIST_MAX goes up");
  assert.deepEqual(ALLOWLIST.filter((f) => !matching.includes(f)), [],
    "an allowlisted file no longer initialises an edge in code, calls the shared module now, is gone, or was renamed (its new name replaces this entry and " +
    "ALLOWLIST_MAX stands); otherwise take it off the list and set ALLOWLIST_MAX to the list's new length in the same commit");
  assert.equal(ALLOWLIST.length, ALLOWLIST_MAX,
    "the allowlist holds " + ALLOWLIST.length + " files, not its pinned count of " + ALLOWLIST_MAX + ". ALLOWLIST_MAX is the list's exact length: a renamed file " +
    "replaces its entry and the count stands; a file that comes off lowers the constant in the same commit; a new file may not join, so neither the list nor the constant goes up");
  assert.deepEqual(ALLOWLIST, ALLOWLIST.slice().sort(), "the allowlist is sorted, so a change to it reads as one line");
  assert.equal(new Set(ALLOWLIST).size, ALLOWLIST.length, "no name twice");
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
  ["a type literal's member, semicolon-separated on one line, as the first member", "type N = { EDGE: N | null; tagName: string };", "parent"],
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
  ["a conditional with a member-expression head whose final operand is an object literal (out of scope)", "win.EDGE = opts.framed ? win : {};", "parent"],
  ["a conditional with a member-expression head whose final operand is a member expression (out of scope)", "win.EDGE = opts.framed ? win : g.top;", "parent"],
  ["a conditional carrying a call (out of scope)", "n.EDGE = mk(x ? y : kid);", "firstChild"],
  ["a comparison inside a conditional, not an assignment", "const same = n.EDGE === x ? a : kid;", "parentNode"],
  ["a logical value (out of scope)", "n.EDGE = p || null; m.EDGE = p && q;", "parentNode"],
];
const INDISTINGUISHABLE: Array<[string, string, string, string]> = [   // [what it is, the shape it reads as, scratch source, edge name]
  // the forms a line start reaches: a destructuring default or a type literal's member on its own line
  ["a destructuring pattern with a default, wrapped over lines", "class field", "function mk({\n  EDGE = [],\n  tag,\n}) { return tag; }", "children"],
  ["a type literal's member, semicolon-separated, on its own line", "class field", "type N = {\n  EDGE: N | null;\n  tagName: string;\n};", "parent"],
  ["a type literal's member, comma-separated (an object-literal key to the regex)", "object-literal key, identifier value", "type N = { EDGE: N, tagName: string };", "parent"],
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
// it, HIDING a shape (a false negative, never a false positive). Each is pinned so a lexer that starts reading the write
// moves the case to POSITIVE and the docstring's account with it.
const ACCEPTED_MISREADS: Array<[string, string, string]> = [   // [what it is, scratch source, edge name]
  ["a quote inside a regex right after a condition's closing paren opens a string to the line end", "if (x) /'/.test(y); const n = { EDGE: null };", "parentNode"],
  ["a backtick inside such a regex opens a template to the next backtick in the file", "if (x) /`/.test(y);\nconst n = { EDGE: null };\nconst t = `z`;", "parentNode"],
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
