// The spacers' measurement, lifted from render.ts and executed (PR E, 2026-09-19): sizeSpacers writes the spacers from the
// view's figures and reads no layout property; measureUnits reads the unit observer's heights (v.uh) at frame end and parks
// the figures on the view; the next paint takes them (applyMeasure) and re-draws the gap units. Two defects this pins shut:
// the ORDER (build one drew the head gap at the 120 px default, the same call measured the window's whole height over its
// one user row, and build two drew the gap at that figure: 24k to 1.43M px in one second on the phone), and the FORCED
// LAYOUT (sizeSpacers read offsetHeight for every child right after the rebuild, and the scroller's scrollHeight for the
// diag row, inside the render task). A recording fake counts every layout read; the old code's count is the red before.
// The models-rev.test.ts / chat-exact-tail-exec.test.ts pattern: the span is transpiled with esbuild at run time.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { DEFAULT_TURN_PX, MAX_TURN_PX, gapHeight } from "./chat-regions";
import { spacerRow, unitChanges } from "./scroll-write";
import { meanRowHeight, perTurnEstimate, rowsFor } from "./turn-estimate";
import type { DisplayItem } from "./compact";
import { hideEdges } from "../test-dom-shim";
import { WRITER_WRAPPERS } from "./landing-settle";
import * as ts from "typescript";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
// the compiler's syntax tree of render.ts, parsed once for the censuses below, and the owner rule they share: the nearest NAMED enclosing
// function (a declaration, a method or a named function expression, else the variable or property an anonymous function is assigned to),
// walking out past anonymous callbacks, the rule writer-census.ts reads writeScroll's callers by
const SF = ts.createSourceFile("render.ts", RENDER, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
const nameOf = (fn: ts.SignatureDeclaration): string | null => {
  if ((ts.isFunctionDeclaration(fn) || ts.isMethodDeclaration(fn) || ts.isFunctionExpression(fn)) && fn.name) return fn.name.getText(SF);
  const p = fn.parent;
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
  if (p && (ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p))) return p.name.getText(SF);
  return null;
};
const ownerOf = (n: ts.Node): string => { for (let p: ts.Node | undefined = n.parent; p; p = p.parent) { if (ts.isFunctionLike(p)) { const nm = nameOf(p); if (nm) return nm; } } return "<module>"; };

/** The take state: the fields of the view the take writes (applyMeasure), the untake restores (untakeMeasure) and the parked figures are
 *  read from before a take (figuresBefore): `measured`, the figures parked since the last paint; `avgTurnH` and `pxPerTurn`, the figures the
 *  spacers and gap units are drawn from. Stated once, here; the ordering window test derives the same three from render.ts's tree and asserts
 *  them equal, and land-active-keep.test.ts's world traces a write of any of them (the maintainer's round 4 ruling, ordering-1: both halves
 *  keyed on the field NAME `measured` alone, narrower than the state the site's exception rests on). Outside the set, by the same derivation:
 *  `measureDue`, which arms the park and is read by measureUnits alone (a write to it in a window takes nothing), and `gapUnits`, the per-unit
 *  heights redrawGapUnits derives from pxPerTurn (redrawGapUnits is a taker by the seed list). */
const TAKE_STATE: ReadonlySet<string> = new Set(["measured", "avgTurnH", "pxPerTurn"]);
/** The targets an assignment's left side writes: itself, or, for an object or array pattern, each of the pattern's targets (a property's
 *  value, a shorthand's name, a spread's expression, an element, a default's left side), so a destructuring assignment writes every field
 *  its pattern names. */
const targetsOf = (e: ts.Expression): ts.Expression[] => {
  if (ts.isParenthesizedExpression(e)) return targetsOf(e.expression);
  if (ts.isObjectLiteralExpression(e)) return e.properties.flatMap((q) => ts.isPropertyAssignment(q) ? targetsOf(q.initializer) : ts.isShorthandPropertyAssignment(q) ? [q.name] : ts.isSpreadAssignment(q) ? targetsOf(q.expression) : []);
  if (ts.isArrayLiteralExpression(e)) return e.elements.flatMap((x) => ts.isOmittedExpression(x) ? [] : ts.isSpreadElement(x) ? targetsOf(x.expression) : targetsOf(x));
  if (ts.isBinaryExpression(e) && e.operatorToken.kind === ts.SyntaxKind.EqualsToken) return targetsOf(e.left);
  return [e];
};
/** The field of `fields` a node names at its end: a property access or a string element access on one; else null. */
const namesField = (e: ts.Node, fields: ReadonlySet<string>): string | null =>
  (ts.isPropertyAccessExpression(e) && fields.has(e.name.text)) ? e.name.text : (ts.isElementAccessExpression(e) && ts.isStringLiteralLike(e.argumentExpression) && fields.has(e.argumentExpression.text)) ? e.argumentExpression.text : null;
/** The field of `fields` a write to `e` reaches: the one `e` names at its end, or one anywhere up its receiver chain (`v.measured.avg`, a
 *  write THROUGH the field into the parked object; `(x as any).measured` through a parenthesis or an assertion), so the census keys on the
 *  field written to, not on the spelling at the target's end. */
const fieldOf = (e: ts.Node | undefined, fields: ReadonlySet<string>): string | null => {
  for (let x: ts.Node | undefined = e; x;) {
    const f = namesField(x, fields); if (f) return f;
    if (ts.isParenthesizedExpression(x) || ts.isNonNullExpression(x) || ts.isAsExpression(x) || ts.isTypeAssertionExpression(x) || ts.isPropertyAccessExpression(x) || ts.isElementAccessExpression(x)) { x = x.expression; continue; }
    return null;
  }
  return null;
};
/** `node` is the write's form (the statement or expression the census describes); `at` is WHERE the write happens, the node itself for
 *  every form but a for-of or for-in, whose target is assigned on each iteration while the statement's own span runs to the end of its body. */
type FieldWrite = { node: ts.Node; at: ts.Node; owner: string; field: string; describe: string };
/** Every WRITE to a field of `fields` under `root`, keyed on the PROPERTY (the field written) and not on the assignment's form (the
 *  maintainer's round 4 ruling, plants-1: a set that counted a simple or compound assignment or a delete whose left side was syntactically
 *  the member let a writer of another form escape with the module green): an assignment of any operator (the compiler's FirstAssignment to
 *  LastAssignment: `=`, `??=`, `||=`, `+=` and the rest), a destructuring assignment whose pattern holds the field as a target
 *  (`({ avg: v.avgTurnH } = m)`, `[v.measured] = [x]`), a for-of or for-in over the field, an increment or a decrement, a delete, and a call
 *  of `Object.assign`, `Object.defineProperty`, `Object.defineProperties`, `Reflect.set`, `Reflect.defineProperty` or `Reflect.deleteProperty`
 *  whose receiver names the field or whose literal source, map or key does (`Object.assign(v, { measured: x })`, `Reflect.set(v, "measured",
 *  x)`, `Object.defineProperties(v, { pxPerTurn: { value: 5 } })`, a literal key under a spread of a literal; a literal's member of any kind,
 *  a property, a shorthand, a method or an accessor, under an identifier, a string or a computed name whose expression is a string literal).
 *  Outside this census by construction, because the tree reads spellings and resolves no binding: a non-literal source's or map's keys and a
 *  computed key of any expression but a string literal (`Object.assign(v, src)`, `v[k] = x`, `{ [k]: x }`), a call through an alias of the
 *  callee (`const oa = Object.assign; oa(v, ...)`), and a write through an alias of the parked object (`const pm = v.measured; pm.avg = x`).
 *  Who holds those depends on WHERE
 *  the write is: inside the span land-active-keep.test.ts lifts (landActive, captureScrollAnchor, restoreScrollAnchor) every form but the
 *  alias of the parked object reaches the world's accessors at run time and is named there (the world's stubbed take parks no object, so a
 *  write through its alias moves nothing the world traces); by an owner outside that span (another function of render.ts) they are outside
 *  both halves, a residual the body names (the author's fixer pass over the pass after the maintainer's round 4 ruling, VT8: until then
 *  this docstring and the closed set's message said every such write reaches the accessors, true of the window alone; the closing fixer
 *  over that fixer pass, CL-6: the two texts then said "the first two" of a list that named four forms in three items, which read as
 *  excluding the alias of the callee, and that alias does reach the accessors). Each
 *  write is named by its owner (ownerOf) and described in the census's words (the right side of a plain assignment, else the whole form),
 *  and placed (`at`) where it happens: the node itself, or a for-of or for-in's TARGET, because the statement's span runs to the end of its
 *  body, so a window check that read the statement's span missed a loop whose block enclosed the write it was checking and reddened on the
 *  closed set alone, the site unnamed (the author's fixer pass over the pass after the maintainer's round 4 ruling, VT7b).
 *  Provenance of the forms: the closing pass over the author's fixer pass (`v.avgTurnH ??= 5` planted in showActive escaped a count of `=`
 *  alone) and the second closing lens (the pattern's `=` has an object literal on its left and the count read the left alone). */
/** One write under `root` in one of the forms the census names, before any field is matched: `targets`, the expressions written (a plain
 *  assignment's left side; every target of a destructuring pattern or of a for-of's or for-in's initializer; an increment's operand; a
 *  delete's expression; the receiver of an Object.assign, Object.defineProperty or Reflect call), `keys`, the literal keys the call's source
 *  or key argument names, `at`, where the write happens, `plain`, the assignment when the form is one (its right side is the census's word for
 *  it), and `describe`, the census's word for a form that is not the node's own text (a for-of's or for-in's head). The two consumers: writesOf,
 *  which matches a set of fields; fieldsWrittenOn, which derives the fields a function writes on its parameter (the take state). */
type WriteSite = { node: ts.Node; at: ts.Node; targets: ts.Node[]; keys: string[]; plain: ts.BinaryExpression | null; describe: string | null };
function writeSites(root: ts.Node): WriteSite[] {
  const out: WriteSite[] = [];
  const site = (node: ts.Node, targets: Array<ts.Node | undefined>, keys: string[] = [], at: ts.Node = node, plain: ts.BinaryExpression | null = null, describe: string | null = null): void => { out.push({ node, at, targets: targets.filter((t): t is ts.Node => !!t), keys, plain, describe }); };
  const isAssign = (n: ts.Node): n is ts.BinaryExpression => ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment;
  const calleeOf = (n: ts.CallExpression): string | null => ts.isPropertyAccessExpression(n.expression) && ts.isIdentifier(n.expression.expression) ? n.expression.expression.text + "." + n.expression.name.text : null;
  // the literal keys of an object literal: every member whose name the tree can read, whatever the member's kind (a property, a shorthand, a
  // method, a getter or a setter: Object.assign reads a member's value and sets it, and a defineProperties map defines each key), under an
  // identifier, a string, or a computed name whose expression is a string literal (`{ ["measured"]: x }`); through a spread of another
  // literal (`{ ...{ measured: x } }` names `measured`: the author's fixer pass over the pass after the maintainer's round 4 ruling, VT20). A
  // spread of anything else, and a computed name of any other expression, name nothing the tree can read. Until the closing fixer over the
  // author's fixer pass over pass 5 (CL-2) a property or a shorthand under an identifier or a string was the whole census, so a computed
  // literal name, an accessor or a method member passed the tree, and an Object.defineProperties call was no write to it.
  const memberKey = (n: ts.PropertyName | undefined): string[] => !n ? [] : ts.isIdentifier(n) || ts.isStringLiteralLike(n) ? [n.text] : ts.isComputedPropertyName(n) && ts.isStringLiteralLike(n.expression) ? [n.expression.text] : [];
  const literalKeys = (a: ts.Node): string[] => ts.isObjectLiteralExpression(a) ? a.properties.flatMap((p) => ts.isSpreadAssignment(p) ? literalKeys(p.expression) : memberKey(p.name)) : [];
  const go = (n: ts.Node): void => {
    if (isAssign(n)) {
      if (ts.isObjectLiteralExpression(n.left) || ts.isArrayLiteralExpression(n.left)) site(n, targetsOf(n.left));
      else site(n, [n.left], [], n, n);
    }
    if ((ts.isForOfStatement(n) || ts.isForInStatement(n)) && !ts.isVariableDeclarationList(n.initializer)) for (const t of targetsOf(n.initializer)) site(n, [t], [], t, null, "for (" + n.initializer.getText(SF) + (ts.isForOfStatement(n) ? " of " : " in ") + n.expression.getText(SF) + ")");
    if ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken)) site(n, [n.operand]);
    if (ts.isDeleteExpression(n)) site(n, [n.expression]);
    if (ts.isCallExpression(n)) {
      const callee = calleeOf(n);
      if (callee === "Object.assign") site(n, [n.arguments[0]], n.arguments.slice(1).flatMap(literalKeys));
      else if (callee === "Object.defineProperties") site(n, [n.arguments[0]], n.arguments[1] ? literalKeys(n.arguments[1]) : []);   // the map's keys are the fields defined
      else if (callee === "Object.defineProperty" || callee === "Reflect.set" || callee === "Reflect.defineProperty" || callee === "Reflect.deleteProperty") { const k = n.arguments[1]; site(n, [n.arguments[0]], k && ts.isStringLiteralLike(k) ? [k.text] : []); }
    }
    ts.forEachChild(n, go);
  };
  go(root);
  return out;
}
function writesOf(fields: ReadonlySet<string>, root: ts.Node): FieldWrite[] {
  const out: FieldWrite[] = [];
  const add = (s: WriteSite, field: string | null, describe: string): void => { if (field) out.push({ node: s.node, at: s.at, owner: ownerOf(s.node), field, describe }); };
  for (const s of writeSites(root)) {
    for (const t of s.targets) { const f = fieldOf(t, fields); add(s, f, s.plain && f && namesField(s.plain.left, fields) === f ? (s.plain.operatorToken.kind === ts.SyntaxKind.EqualsToken ? "" : s.plain.operatorToken.getText(SF) + " ") + s.plain.right.getText(SF) : s.describe ?? s.node.getText(SF)); }
    for (const k of s.keys) if (fields.has(k)) add(s, k, s.describe ?? s.node.getText(SF));
  }
  return out;
}
/** The expression under any parentheses, non-null assertions and type assertions. */
const bare = (e: ts.Node): ts.Node => { let x = e; while (ts.isParenthesizedExpression(x) || ts.isNonNullExpression(x) || ts.isAsExpression(x) || ts.isTypeAssertionExpression(x)) x = x.expression; return x; };
/** The field of the parameter `param` an expression names: at the access whose receiver (bare) is the parameter itself, anywhere down the
 *  chain (`v.measured.avg`, `(v as any).measured` and `v["measured"]` each name `measured`); null when the chain does not bottom at the
 *  parameter or the key is computed. */
const fieldOnParam = (e: ts.Node, param: string): string | null => {
  for (let x = bare(e); ts.isPropertyAccessExpression(x) || ts.isElementAccessExpression(x); x = bare(x.expression)) {
    const recv = bare(x.expression);
    if (ts.isIdentifier(recv) && recv.text === param) return ts.isPropertyAccessExpression(x) ? x.name.text : ts.isStringLiteralLike(x.argumentExpression) ? x.argumentExpression.text : null;
  }
  return null;
};
/** The fields of the parameter `param` written under `root`, in every form writeSites names (a plain or compound assignment, a destructuring
 *  pattern, a for-of or for-in, an increment, a delete, an Object.assign, defineProperty, defineProperties or Reflect call with a literal key,
 *  source or map),
 *  through a parenthesis or an assertion on the receiver. The derivation of the take state (the ordering pin) reads the take's and the
 *  untake's writes through this and the parked figures' reads through fieldsReadOn, so it keys on the PROPERTY, the field of the view written
 *  or read, not on the spelling `v.<field>` (until the author's fixer pass over the pass after the maintainer's round 4 ruling, VT14, the
 *  derivation read bare `v.<name>` assignments and reads alone while its message said a field the take grows into is added). Outside it: a
 *  computed key of any expression but a string literal and a non-literal source or map, as they are outside writesOf, and a write through an
 *  alias of the parameter (`const w = v as any; w.spare = 1`), because the tree resolves no binding (the closing fixer over the author's
 *  fixer pass over pass 5, CL-3, named the alias; until then it was outside without being named). */
function fieldsWrittenOn(param: string, root: ts.Node): Set<string> {
  const out = new Set<string>();
  for (const s of writeSites(root)) for (const t of s.targets) {
    const f = fieldOnParam(t, param); if (f) out.add(f);
    else { const b = bare(t); if (ts.isIdentifier(b) && b.text === param) for (const k of s.keys) out.add(k); }
  }
  return out;
}
/** The fields of the parameter `param` read under `root`: every property or string-keyed element access whose receiver (bare) is the parameter,
 *  and every field a binding pattern or an assignment pattern takes from it (`const { measured } = v`, `({ avg: a } = v)`, `let m; ({ m } = v)`:
 *  the property's name, or the shorthand's, under an identifier, a string or a computed name whose expression is a string literal; a rest
 *  element names no field). Outside it, because the tree resolves no binding: a read through an alias of the parameter (`const w = v;
 *  w.measured`), as a write through an alias (`const w = v as any; w.spare = 1`) is outside fieldsWrittenOn and the census's alias forms are
 *  outside writesOf. Until the closing fixer over the author's fixer pass over pass 5 (CL-3) the pattern forms were outside it too, and
 *  the alias of the parameter was outside both derivations without being named. */
function fieldsReadOn(param: string, root: ts.Node): Set<string> {
  const out = new Set<string>();
  const isParam = (e: ts.Node): boolean => { const b = bare(e); return ts.isIdentifier(b) && b.text === param; };
  const keyOf = (n: ts.PropertyName | ts.BindingName): string | null => ts.isIdentifier(n) || ts.isStringLiteralLike(n) ? n.text : ts.isComputedPropertyName(n) && ts.isStringLiteralLike(n.expression) ? n.expression.text : null;
  const go = (n: ts.Node): void => {
    if (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) { const f = fieldOnParam(n, param); if (f && isParam(n.expression)) out.add(f); }
    if (ts.isVariableDeclaration(n) && ts.isObjectBindingPattern(n.name) && n.initializer && isParam(n.initializer)) for (const el of n.name.elements) { if (el.dotDotDotToken) continue; const k = keyOf(el.propertyName ?? el.name); if (k) out.add(k); }
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isObjectLiteralExpression(n.left) && isParam(n.right)) for (const p of n.left.properties) { const nm = p.name; if (ts.isSpreadAssignment(p) || !nm) continue; const k = keyOf(nm); if (k) out.add(k); }
    ts.forEachChild(n, go);
  };
  go(root);
  return out;
}

/** The source with its comments removed and nothing else: the comment ranges are the compiler's own (every token's leading and trailing
 *  trivia over the parsed file), so a `//` or a `/*` inside a string, a template or a regular expression is text, never a comment. The
 *  regex stripper this replaces (the author's fixer pass over pass 3) cut a line at the `//` of a quoted URL, which hid an alias written after it on the same
 *  line from the bare-reference census below, opened a block comment at a quoted glob (`"image/*"`) and swallowed the code to the next
 *  `*\/`, and cut `u.replace(/^file:\/\//, "")` at the regular expression's slashes. The writer census (writer-census.ts) reads render.ts
 *  the same way for the same reason. */
function codeOf(src: string): string {
  const sf = ts.createSourceFile("render.ts", src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const cut: Array<[number, number]> = [];
  const walk = (n: ts.Node): void => {
    for (const r of ts.getLeadingCommentRanges(src, n.getFullStart()) ?? []) cut.push([r.pos, r.end]);
    for (const r of ts.getTrailingCommentRanges(src, n.getEnd()) ?? []) cut.push([r.pos, r.end]);
    for (const c of n.getChildren(sf)) walk(c);
  };
  walk(sf);
  cut.sort((a, b) => a[0] - b[0]);
  let out = "", at = 0;
  for (const [p, e] of cut) { if (p < at) continue; out += src.slice(at, p); at = e; }
  return out + src.slice(at);
}

function liftBetween(startAnchor: string, endAnchor: string): string {
  const a = RENDER.indexOf(startAnchor), b = RENDER.indexOf(endAnchor, a);
  assert.ok(a > 0 && b > a, `anchors not found: ${startAnchor.slice(0, 40)} or ${endAnchor.slice(0, 40)} moved; re-anchor`);
  return requireCjs("esbuild").transformSync(RENDER.slice(a, b), { loader: "ts" }).code;
}

/** The layout reads a paint must not make: every offsetHeight of a row, every scrollHeight / clientHeight of the scroller. */
type Reads = { offsetHeight: number; scrollHeight: number; clientHeight: number };

/** Enough of an element for the spacer code: a class list, data-*, inline style, children and the selectors it uses; offsetHeight
 *  is a RECORDING getter (the read counts, the value is the row's real height). */
class FakeEl {
  children!: FakeEl[]; parent: FakeEl | null = null; dataset: Record<string, string> = {}; style: Record<string, string> = { display: "" };
  constructor(public tag: string, public className = "", public realH = 0, private reads: Reads | null = null) {
    Object.defineProperty(this, "children", { value: [], writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  get offsetHeight(): number { if (this.reads) this.reads.offsetHeight++; return this.realH; }
  get classList() { const cls = this.className.split(/\s+/); return { contains: (c: string) => cls.includes(c) }; }
  get firstChild(): FakeEl | null { return this.children[0] ?? null; }
  get lastChild(): FakeEl | null { return this.children[this.children.length - 1] ?? null; }
  get nextSibling(): FakeEl | null { const p = this.parent; if (!p) return null; const i = p.children.indexOf(this); return i >= 0 ? p.children[i + 1] ?? null : null; }
  appendChild(c: FakeEl): FakeEl { c.parent?.removeChild(c); c.parent = this; this.children.push(c); return c; }
  insertBefore(c: FakeEl, ref: FakeEl | null): FakeEl { c.parent?.removeChild(c); c.parent = this; const i = ref ? this.children.indexOf(ref) : -1; if (i < 0) this.children.push(c); else this.children.splice(i, 0, c); return c; }
  removeChild(c: FakeEl): void { this.children = this.children.filter((x) => x !== c); c.parent = null; }
  private match(sel: string): FakeEl[] { const m = /^(?::scope > )?\.([\w-]+)$/.exec(sel); if (!m) throw new Error("unsupported selector " + sel); return this.children.filter((c) => c.classList.contains(m[1])); }
  querySelector(sel: string): FakeEl | null { return this.match(sel)[0] ?? null; }
  querySelectorAll(sel: string): FakeEl[] { return this.match(sel); }
}

type Diag = Array<{ kind: string; data: any }>;
type Writes = Array<{ top: number; writer: string; stick: boolean }>;
type World = {
  reads: Reads; diag: Diag; rafs: Array<() => void>; views: Map<string, any>; activeId: string | null; writes: Writes; content: { scrollTop: number; ch: number }; paints: number;
  sizeSpacers: (v: any) => void; measureUnits: (v: any) => void; applyMeasure: (v: any) => boolean; redrawGapUnits: (v: any) => void; takeMeasureAtBottom: (v: any) => void; forgetAverage: (v: any) => void;
  figuresBefore: (v: any) => { avg: number | undefined; per: number | undefined; measured: any }; untakeMeasure: (v: any, before: any) => boolean;
  setActive: (id: string | null) => void;   // the lifted span's own activeId (a tab switch between a queued spacer row and its frame)
  gapUnitsOf: (items: DisplayItem[], per: number | undefined) => Map<number, number> | undefined; entryBoxHeight: (e: any) => number;
  cancelled: number[];                       // the frame ids cancelAnimationFrame was handed (a cancelled callback leaves `rafs`)
  visibilityDrop: (() => void) | null;       // the span's visibilitychange handler (dropSpacerRowsOnVisibility), null where the span has none
  hide: () => void; show: () => void;        // document.hidden flipped as the browser flips it, then the handler, as the listener outside the span calls it
};
/** The scroller: 9,114 px tall in a 902 px viewport; `scrollTop` starts at the bottom unless a world says otherwise. Every layout read counts.
 *  `paints` counts the appendActive paints the frame-end take asks for (scheduleAppendActive). */
function lift(activeId: string | null, scrollTop = 9114 - 902): World {
  const js = liftBetween("function gapUnitsOf(", "function unitAtScroll(");
  const reads: Reads = { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 };
  const diag: Diag = []; const rafs: Array<() => void> = []; const views = new Map<string, any>(); const writes: Writes = [];
  const content = { scrollTop, ch: 902, get scrollHeight() { reads.scrollHeight++; return 9114; }, get clientHeight() { reads.clientHeight++; return this.ch; } };
  const cancelled: number[] = []; const rafIds = new Map<number, () => void>(); let rafSeq = 0;   // frame ids, so a cancel takes its callback out of `rafs`
  const doc = { getElementById: (id: string) => (id === "content" ? content : null), hidden: false };
  const world: any = { reads, diag, rafs, views, activeId, writes, content, paints: 0, cancelled };
  const hooks = { FakeEl, views, activeId, document: doc,
                  raf: (cb: () => void) => { rafs.push(cb); rafIds.set(++rafSeq, cb); return rafSeq; },
                  caf: (id: number) => { cancelled.push(id); const cb = rafIds.get(id); const i = cb ? rafs.indexOf(cb) : -1; if (i >= 0) rafs.splice(i, 1); },
                  diag: (kind: string, data: any) => diag.push({ kind, data }),
                  spacerRow, gapHeight, rowsFor, meanRowHeight, perTurnEstimate,
                  atBottom: (c: any) => c.scrollHeight - c.scrollTop - c.clientHeight <= 2,
                  writeScroll: (c: any, top: number, writer: string, stick = false) => { writes.push({ top, writer, stick }); c.scrollTop = Math.min(top, c.scrollHeight - c.clientHeight); },
                  scheduleAppendActive: () => { world.paints++; } };
  const prelude = `
    const H = HOOKS;
    const HTMLElement = H.FakeEl;
    const el = (tag, cls) => new H.FakeEl(tag, cls || "");
    const views = H.views; let activeId = H.activeId; const document = H.document;
    const setActive = (id) => { activeId = id; };
    const requestAnimationFrame = H.raf; const cancelAnimationFrame = H.caf; const scrollDiagRow = H.diag; const spacerRow = H.spacerRow; const gapHeight = H.gapHeight;
    const rowsFor = H.rowsFor, meanRowHeight = H.meanRowHeight, perTurnEstimate = H.perTurnEstimate;
    const atBottom = H.atBottom, writeScroll = H.writeScroll, scheduleAppendActive = H.scheduleAppendActive;
  `;
  // the visibility handler is read by name where the span has one, so a world over a span without it still lifts (the red-before of the
  // hidden-page cells ran against such a span: the rows filed with the later frame's figures, the property, not a ReferenceError)
  const api = new Function("HOOKS", prelude + js + "\nreturn { sizeSpacers, measureUnits, applyMeasure, redrawGapUnits, gapUnitsOf, entryBoxHeight, takeMeasureAtBottom, forgetAverage, setActive, figuresBefore, untakeMeasure, visibilityDrop: typeof dropSpacerRowsOnVisibility === \"function\" ? dropSpacerRowsOnVisibility : null };")(hooks);
  world.hide = () => { doc.hidden = true; api.visibilityDrop?.(); };
  world.show = () => { doc.hidden = false; api.visibilityDrop?.(); };
  return Object.assign(world, api) as World;
}
/** The unit observer's callback, lifted from ensureView (the `const view3 = v;` span) over a world's measure and take: a fake
 *  ResizeObserver hands the callback back, and `deliver` runs it with entries shaped as the browser's (border box + contentRect). */
function liftObserver(w: World, v: any, id: string) {
  const js = liftBetween("      const view3 = v;", "      const view2 = v;");
  let cb: ((entries: any[]) => void) | null = null;
  const hooks = { v, id, w, unitChanges, ResizeObserver: class { constructor(f: (entries: any[]) => void) { cb = f; } observe() {} unobserve() {} disconnect() {} } };
  const prelude = `
    const H = HOOKS;
    const v = H.v, id = H.id, activeId = H.w.activeId, document = { getElementById: (x) => (x === "content" ? H.w.content : null) };
    const ResizeObserver = H.ResizeObserver, unitChanges = H.unitChanges, entryBoxHeight = H.w.entryBoxHeight;
    const measureUnits = H.w.measureUnits, takeMeasureAtBottom = H.w.takeMeasureAtBottom;
    const atBottom = (c) => c.scrollHeight - c.scrollTop - c.clientHeight <= 2;
    const scrollDiagRow = (kind, data) => H.w.diag.push({ kind, data }); const unitChangeRow = (...a) => ({ row: a });
  `;
  new Function("HOOKS", prelude + js)(hooks);
  assert.ok(cb, "the unit observer was constructed");
  const deliver = (rows: FakeEl[], h: (r: FakeEl) => number) => cb!(rows.map((r) => ({ target: r, borderBoxSize: [{ blockSize: h(r), inlineSize: 400 }], contentRect: { height: h(r) } })));
  return { deliver, heights: v.uh as WeakMap<object, number> };
}

/** A view over `items` (a head gap as unit 0, then event units) rendered as the window [winStart, total): a top spacer, then one row per
 *  unit with the class and real height given by `rowOf(u)`. The observer's map (v.uh) starts EMPTY, as it is at build time. */
function viewOver(w: World, gapTurns: number, total: number, winStart: number, rowOf: (u: number) => [string, number]) {
  const items: DisplayItem[] = [{ kind: "gap", lo: 0, hi: gapTurns, before: 0 }];
  for (let u = 1; u < total; u++) items.push({ kind: "event", index: u - 1 });
  const host = new FakeEl("div");
  host.appendChild(new FakeEl("div", "tx-spacer tx-spacer-top", 0, w.reads));
  const rows: FakeEl[] = [];
  for (let u = winStart; u < total; u++) { const [cls, h] = rowOf(u); const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(u); host.appendChild(n); rows.push(n); }
  const v: any = { el: host, winStart, winEnd: total, spacerCount: winStart, spacerCountBot: 0, unitTotal: total, units: items, uh: new WeakMap<object, number>(), stick: true };
  return { v, items, rows, top: host.children[0] };
}
/** Build one, as renderWindowItems ends: the gap units at the current figure, then the spacers. */
const buildOne = (w: World, v: any, items: DisplayItem[]) => { w.applyMeasure(v); v.gapUnits = w.gapUnitsOf(items, v.pxPerTurn); w.sizeSpacers(v); v.measureDue = true; };
/** The observer's delivery: every row's border-box height lands in the map, then the measure. */
const observe = (w: World, v: any, rows: FakeEl[]) => { for (const r of rows) v.uh.set(r, r.realH); w.measureUnits(v); };
/** The next paint, as syncViewInner takes the figures. */
const paintTwo = (w: World, v: any) => { if (w.applyMeasure(v)) { w.redrawGapUnits(v); w.sizeSpacers(v); } };
const topPx = (v: any) => parseFloat(v.el.children[0].style.height);

// ── T3: the order ────────────────────────────────────────────────────────────────────────────────

test("the phone's window (one user row, 79 dense rows) over a 200-turn head gap: build two keeps build one's gap; the old formula drew it 60x", () => {
  const w = lift(null);
  const { v, items, rows } = viewOver(w, 200, 301, 221, (u) => (u === 221 ? ["turn turn-user", 40] : ["turn turn-assistant", 90]));
  buildOne(w, v, items);
  const gapOne = v.gapUnits.get(0), topOne = topPx(v);
  assert.equal(gapOne, 200 * DEFAULT_TURN_PX, "build one: the default per turn (24k px)");
  assert.equal(topOne, gapOne + 220 * 60, "…plus the hidden run units at the default average");
  observe(w, v, rows);
  assert.equal(v.pxPerTurn, undefined, "the figure waits for the paint");
  paintTwo(w, v);
  const gapTwo = v.gapUnits.get(0), topTwo = topPx(v);
  assert.equal(gapTwo, gapOne, "no complete turn in the window: the gap keeps the default, it is not measured off one user row");
  assert.equal(v.pxPerTurn, undefined, "…and nothing is cached");
  assert.equal(v.avgTurnH, (40 + 79 * 90) / 80, "the rows' average is taken (once per view)");
  assert.ok(topTwo / topOne < 2, "the spacer moved with the average alone: " + topOne + " -> " + topTwo);
  const oldFigure = (40 + 79 * 90) / 1;   // the whole window over its one user row
  assert.ok(gapHeight({ lo: 0, hi: 200 }, oldFigure) / gapOne >= 20, "the old figure would have drawn the gap at least 20x (the clamp's edge): " + gapHeight({ lo: 0, hi: 200 }, oldFigure));
  assert.ok(200 * oldFigure / gapOne > 55, "…and without the cap about 60x: " + (200 * oldFigure / gapOne));
});

test("a window with two complete turns measures their median; the gap units and the rendered gap element take it on the next paint", () => {
  const w = lift(null);
  // rows: a partial leading reply (500), then user 30 / reply 70, user 30 / reply 90, then the streaming turn user 30 / reply 900
  const shape: Array<[string, number]> = [["turn turn-assistant", 500], ["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 90], ["turn turn-user", 30], ["turn turn-assistant", 900]];
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + shape.length, 101, (u) => shape[u - 101]);
  // a second gap, rendered inside the window, follows the rows (T386: a mid-transcript gap)
  const g = new FakeEl("div", "tx-gap", 0, w.reads); g.dataset.lo = "300"; g.dataset.hi = "310"; g.dataset.unit = String(items.length); v.el.appendChild(g);
  items.push({ kind: "gap", lo: 300, hi: 310, before: items.length - 1 }); v.unitTotal = items.length; v.winEnd = items.length;
  buildOne(w, v, items);
  g.style.height = gapHeight({ lo: 300, hi: 310 }, v.pxPerTurn) + "px";   // as gapElement draws it at build
  assert.equal(v.gapUnits.get(0), 200 * DEFAULT_TURN_PX); assert.equal(g.style.height, 10 * DEFAULT_TURN_PX + "px");
  observe(w, v, rows); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 100, "the median of 100 and 120: the lower of the two (a height a turn has)");
  assert.equal(v.gapUnits.get(0), 200 * 100, "the head gap at the measured figure");
  assert.equal(v.gapUnits.get(items.length - 1), 10 * 100, "the mid-transcript gap too");
  assert.equal(g.style.height, 10 * 100 + "px", "the rendered gap element follows without a rebuild");
  assert.equal(topPx(v), Math.round(200 * 100 + 100 * v.avgTurnH), "the spacer: the gap plus the hidden run units at the average");
});

test("a later build re-measures (not once): the figure follows the window's complete turns; a window with fewer than two keeps the last figure", () => {
  const w = lift(null);
  const two = (a: number, b: number): Array<[string, number]> => [["turn turn-user", 30], ["turn turn-assistant", a - 30], ["turn turn-user", 30], ["turn turn-assistant", b - 30], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  const first = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two(100, 120)[u - 101]);
  buildOne(w, first.v, first.items); observe(w, first.v, first.rows); paintTwo(w, first.v);
  assert.equal(first.v.pxPerTurn, 100);
  const avgFirst = first.v.avgTurnH;
  assert.ok(avgFirst! > 0, "the average was taken on the first build");
  // the same view, re-windowed over taller turns (a browse, a fill): build, observe, paint
  const v = first.v;
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows2: FakeEl[] = [];
  two(200, 220).forEach(([cls, h], i) => { const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows2.push(n); });
  buildOne(w, v, first.items); observe(w, v, rows2); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 200, "re-measured on the later build");
  assert.equal(v.gapUnits.get(0), 200 * 200);
  assert.equal(v.avgTurnH, avgFirst, "the average is taken once per view: the taller rows did not move it");
  // …and a window with one complete turn leaves the figure where it was
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows3: FakeEl[] = [];
  ([["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 900]] as Array<[string, number]>).forEach(([cls, h], i) => { const n = new FakeEl("div", cls, h, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows3.push(n); });
  buildOne(w, v, first.items); observe(w, v, rows3); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 200, "one complete turn: the figure stands");
  assert.equal(v.measured, undefined, "nothing waits");
});

test("the clamp is a backstop under the measured figure: turns of 5,000 px draw the gap at MAX_TURN_PX per turn", () => {
  const w = lift(null);
  const tall: Array<[string, number]> = [["turn turn-user", 200], ["turn turn-assistant", 4800], ["turn turn-user", 200], ["turn turn-assistant", 4800], ["turn turn-user", 200]];
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + tall.length, 101, (u) => tall[u - 101]);
  buildOne(w, v, items); observe(w, v, rows); paintTwo(w, v);
  assert.equal(v.pxPerTurn, 5000, "the measured figure is kept as measured");
  assert.equal(v.gapUnits.get(0), 200 * MAX_TURN_PX, "…and drawn under the cap");
  assert.equal(MAX_TURN_PX, 20 * DEFAULT_TURN_PX);
});

// ── T4: no forced layout in the render task ──────────────────────────────────────────────────────

test("sizeSpacers and the measure read no layout property: zero offsetHeight, scrollHeight and clientHeight reads in the paint; the spacer row reads the scroller a frame later", () => {
  const w = lift("A");
  const { v, items, rows } = viewOver(w, 200, 301, 221, (u) => (u % 3 === 0 ? ["turn turn-user", 40] : ["turn turn-assistant", 90]));
  w.views.set("A", v);
  buildOne(w, v, items);
  const topOne = topPx(v);
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "build one's spacer write read nothing");
  assert.equal(w.diag.length, 0, "the spacer row is not filed inside the paint");
  assert.equal(w.rafs.length, 1, "…it waits for the next animation frame");
  observe(w, v, rows); paintTwo(w, v);
  const topTwo = topPx(v);
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "the measure read the observer's map, the paint wrote the spacers: still nothing");
  assert.ok(v.pxPerTurn! > 0 && v.avgTurnH! > 0, "…and the figures were taken from the map: " + v.pxPerTurn + " / " + v.avgTurnH);
  const before = w.diag.length;
  w.rafs.shift()!();
  assert.equal(w.diag.length, before + 2, "the two writes' rows, filed together");
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 1, clientHeight: 1 }, "the scroller was read once, in the frame, for both rows");
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data.sid, d.data.sh, d.data.ch, "view" in d.data]), [["spacer", "A", 9114, 902, false], ["spacer", "A", 9114, 902, false]], "the active view's rows: the frame's figures and no `view` key (the marker is the switched-away row's alone, held here by execution and not by the frame's spelling alone; the test below reads it on that row)");
  // each row carries its own before/after, in that order (the tuple queueSpacerRow pushes and the frame drains): the T262j diagnosis reads
  // which way the head spacer moved, so an inverted pair would read backwards (the author's pass 0: the old assertion here compared a value with itself)
  assert.deepEqual(w.diag[0].data.top, [0, topOne], "build one's row: from nothing to the first spacer");
  assert.deepEqual(w.diag[1].data.top, [topOne, topTwo], "the paint's row: from the first spacer to the measured one");
  assert.deepEqual(w.diag[0].data.bot, [0, 0], "no bottom spacer in this window");
  assert.equal(w.diag[1].data.dTop, topTwo - topOne, "the delta follows the pair's order");
  assert.ok(topOne !== topTwo, "the second write moved the spacer again (the measured figures)");
});

test("a spacer row whose view was switched away before the frame carries no geometry and says so: the scroller is the active view's alone, and it is not read when no queued row is that view's (the maintainer's round 1 addendum)", () => {
  const w = lift("A");
  const { v, items } = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w.views.set("A", v);
  buildOne(w, v, items);                       // A is active: its spacer write queues a row for the next frame
  assert.equal(w.diag.length, 0); assert.equal(w.rafs.length, 1);
  w.setActive("B");   // the reader switched tabs before the frame ran
  w.rafs.shift()!();
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "no queued row is the active view's: the scroller is not read at all");
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data.sid, d.data.sh, d.data.ch, d.data.view]), [["spacer", "A", null, null, "inactive"]], "A's row: no geometry and the marker, never B's 9114 / 902 (the `view` key, one fixed word, inactive, and no host name, on the owner's approval: the owner 2026-09-21, who approved the field)");
});

test("a frame holding one row of the active view and one of a view switched away before it files each row with its own view's figures: the active view's with the frame's heights and no marker, the switched-away view's with nulls and the marker, never another view's figures (the maintainer's round 1 addendum; the owner 2026-09-21, who approved the field)", () => {
  // the two frame tests above take one arm each: the active view's rows with the frame's figures, and a switched-away row in a frame with no
  // active row, where the frame reads nothing and its figures are null whichever arm builds the row. This frame holds both, so a post that
  // hands the frame's figures to the switched-away row (one call with a conditional marker, say) reds here by execution and not only at the
  // census cell's source spelling and scroll-movers' regex.
  const w = lift("A");
  const A = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  const B = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w.views.set("A", A.v); w.views.set("B", B.v);
  buildOne(w, A.v, A.items);            // A is active: its spacer write queues A's row for the next frame
  w.setActive("B");                     // the reader switched tabs before the frame ran
  buildOne(w, B.v, B.items);            // B is active: its write queues B's row into the same frame
  assert.equal(w.rafs.length, 1, "one frame for both rows");
  w.rafs.shift()!();
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 1, clientHeight: 1 }, "the scroller was read once, for B's row");
  assert.deepEqual(w.diag.map((d) => [d.data.sid, d.data.sh, d.data.ch, "view" in d.data ? d.data.view : "<none>"]), [["A", null, null, "inactive"], ["B", 9114, 902, "<none>"]], "A's row: nulls and the marker, never B's 9114 / 902; B's row: the frame's figures and no marker");
});

test("a frame whose live view is hidden by the section-at-a-glance view files its row with nulls and the marker and does not read the scroller: #content holds the section list there, not the view (the maintainer's round 5 ruling, extra10-1; the owner 2026-09-21, who approved the field)", () => {
  // showActive's section branch sets every view element's display to none and leaves activeId as it was (the kernel's active hint, the MRU
  // and the drafts still point at the session being read), and the section list is a child of #content: the scroller's heights there are
  // the LIST's. At the head the maintainer's round 5 ruled on, the frame keyed its read on activeId alone and filed this row with 9114 and
  // 902 and no marker, the corruption the marker exists to name. The frame's predicate is the view element's display, the property (#content
  // measures the live view only while its element is shown), not snapView, which is one cause of it; the FakeEl's style is a plain object,
  // so the test sets the display as showActive does.
  const w = lift("A");
  const { v, items } = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w.views.set("A", v);
  buildOne(w, v, items);                       // A is active and shown: its spacer write queues a row for the next frame
  assert.equal(w.diag.length, 0); assert.equal(w.rafs.length, 1);
  v.el.style.display = "none";                 // the reader opened a section at a glance before the frame ran: every view hidden, activeId untouched
  w.rafs.shift()!();
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "the live view is not what #content measures: the scroller is not read");
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data.sid, d.data.sh, d.data.ch, d.data.view]), [["spacer", "A", null, null, "inactive"]], "A's row: nulls and the marker, never the section list's 9114 / 902 (the `view` key, one fixed word, no host name, on the owner's approval)");
  // back to the transcript before the next frame: the view shown again, a spacer write of it reads the scroller as before
  v.el.style.display = "";
  v.avgTurnH = (v.avgTurnH ?? 60) + 10; w.sizeSpacers(v);
  assert.equal(w.rafs.length, 1, "a spacer write with the view shown again queues a row");
  w.rafs.shift()!();
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 1, clientHeight: 1 }, "…and its frame reads the scroller once");
  assert.deepEqual(w.diag.slice(1).map((d) => [d.data.sid, d.data.sh, d.data.ch, "view" in d.data]), [["A", 9114, 902, false]], "the shown view's row: the frame's figures and no marker");
});

test("rows queued and the page hidden before their frame (visibilitychange): the rows are dropped, their frame cancelled, and one row names the drop, the count, the kind and the edge; a frame that ran anyway files nothing; a row queued once the page shows again files as before (the maintainer's round 5 ruling, kernel-1)", () => {
  // an animation frame does not run while the document is hidden, so at the head the maintainer's round 5 ruled on, the rows queued before
  // the page hid waited, and the frame that came once it showed again filed them with THAT frame's scroller heights and the kernel's
  // arrival time: another frame's figures on a row about an earlier write. The bound is the event, not a timer or a cap: the hidden edge
  // drops what is pending, cancels the frame and files one row about it (spacer-dropped: sid, n, kind, why; the chat allowlist's keys and
  // no `view`), through scrollDiagRow like every diag row. The harness flips document.hidden as the browser does and calls the span's
  // handler as the listener outside the span does.
  const w = lift("A");
  const { v, items } = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w.views.set("A", v);
  buildOne(w, v, items);                       // one row queued
  v.avgTurnH = 70; w.sizeSpacers(v);           // a second write in the same task: the same frame
  assert.equal(w.rafs.length, 1, "one frame armed for the two rows");
  const frame = w.rafs[0];
  w.hide();                                    // visibilitychange to hidden before the frame ran
  frame();                                     // the frame that came later (once the page showed again, in the browser)
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data]), [["spacer-dropped", { sid: "A", n: 2, kind: "spacer", why: "hidden" }]], "the two queued rows are not filed with the later frame's figures; one row names the drop: the count, the kind, the edge");
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "the scroller was not read for them");
  assert.deepEqual(w.cancelled, [1], "the armed frame was cancelled on the hidden edge");
  assert.equal(w.rafs.length, 0, "…so no frame is pending");
  // the page shows again with nothing pending: the shown edge files nothing; a write then queues and files as before
  w.show();
  assert.equal(w.diag.length, 1, "nothing pending at the shown edge: no row");
  v.avgTurnH = 80; w.sizeSpacers(v);
  assert.equal(w.rafs.length, 1, "a write while visible arms a frame"); w.rafs.shift()!();
  assert.deepEqual(w.diag.slice(1).map((d) => [d.kind, d.data.sid, d.data.sh, d.data.ch, "view" in d.data]), [["spacer", "A", 9114, 902, false]], "a row queued and framed while visible files with its frame's figures, as before");
});

test("rows of TWO views pending at the hidden edge (A's row queued, the reader switched to B, B's row queued into the same frame, then to C, which queued none): one drop row counts every pending row, n 2, and names the live view at the edge, sid C, never a count over the live view's rows alone, the first pending row's view or the last pending row's (the maintainer's round 6 ruling, extra6-2; the handler's rule: n over every pending row whichever view queued it, sid the live view's id at the edge)", () => {
  // the mixed-frame pattern of the two-view row test above, hidden before the frame, with one more switch to a view that queued nothing: the
  // hidden-page cells before and after this one hold one view's rows, so a count restricted to the live view's rows, or a sid taken from the
  // first pending row, left both green and only the frame census's source regex red; and while the live view at the edge was B, the view
  // that queued the LAST row, a sid taken from the last pending row left this cell green too (the author's fixer pass over the pass after
  // the maintainer's round 6, its verifier (a)), so the reader switches once more, to C: this cell reds by execution on each of the three
  const w = lift("A");
  const A = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  const B = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  const C = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w.views.set("A", A.v); w.views.set("B", B.v); w.views.set("C", C.v);
  buildOne(w, A.v, A.items);            // A is active: its spacer write queues A's row for the next frame
  w.setActive("B");                     // the reader switched tabs before the frame ran
  buildOne(w, B.v, B.items);            // B is active: its write queues B's row into the same frame
  w.setActive("C");                     // then switched again, to a view with no write pending: the live view at the edge queued no row
  assert.equal(w.rafs.length, 1, "one frame armed for the two views' rows");
  const frame = w.rafs[0];
  w.hide();                             // visibilitychange to hidden before the frame ran
  frame();                              // the frame that came later (once the page showed again, in the browser)
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data]), [["spacer-dropped", { sid: "C", n: 2, kind: "spacer", why: "hidden" }]], "one drop row: n counts A's row and B's (2), sid is the live view's at the edge (C), never the first pending row's view (A), the last pending row's (B) or the live view's rows alone (0)");
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "the scroller was not read for either row");
  assert.deepEqual(w.cancelled, [1], "the armed frame was cancelled on the hidden edge");
  assert.equal(w.rafs.length, 0, "…so no frame is pending");
});

test("rows queued while the page is hidden (a paint runs there) wait for a frame that does not come: the shown edge drops them, cancels the frame and files one row naming the drop, never the first visible frame's heights (the maintainer's round 5 ruling, kernel-1)", () => {
  // the other side of the edge: a paint while hidden (a streamed frame's append) writes the spacers and queues its row; the frame it asks
  // for runs only once the page shows, with every paint since in the scroller's heights. The shown edge drops the pending rows the same way.
  const w = lift("A");
  const { v, items } = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w.views.set("A", v);
  w.hide();
  assert.equal(w.diag.length, 0, "nothing pending at the hidden edge: no row");
  buildOne(w, v, items);                       // a paint while hidden queues its row
  assert.equal(w.rafs.length, 1, "the row is queued and a frame asked for, which the hidden page never runs");
  const frame = w.rafs[0];
  w.show();                                    // visibilitychange to visible: the frame it would now run has another frame's figures
  frame();
  assert.deepEqual(w.diag.map((d) => [d.kind, d.data]), [["spacer-dropped", { sid: "A", n: 1, kind: "spacer", why: "shown" }]], "the row queued while hidden is dropped at the shown edge and named, never filed with the first visible frame's heights");
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "the scroller was not read");
  assert.equal(w.rafs.length, 0, "its frame was cancelled");
});

test("spacerRow mints the `view` marker only when handed one, and only the one word (the owner 2026-09-21, who approved the field)", () => {
  // the marker is spread only when handed the one word: the shown view's row carries none, a null row handed nothing carries none, the
  // switched-away view's row carries the word, and a value the parameter's type does not name, handed past the type, mints nothing (the
  // type is gone at run time; the builder's guard holds the word there, and the kernel bounds the value to the same word, CLIENT_DIAG_VALUES, so the guard is
  // the page's hold on the word and the kernel's refusal is the store's). The three foreign values below are a SAMPLE of what the type does not name, not the population: another word
  // answers a guard on truthiness, a case variant of the word answers a guard that lowers before comparing (that guard left every leg and
  // tsc green before the case variant was asserted), a truthy non-string answers a guard that holds strings to the word and lets a non-string
  // through; the guard's equality with the one word is what holds the rest. scroll-movers.test.ts and scroll-journal-audit.test.ts read the
  // unmarked numeric shape; the frame's post hands the marker on the switched-away arm alone, the census cell below pins that spelling and
  // the three frame tests above run it through the frame.
  assert.ok(!("view" in spacerRow("A", 1, 2, 0, 0, 9114, 902)), "no marker on the active view's row");
  assert.deepEqual(spacerRow("A", 1, 2, 0, 0, null, null), { sid: "A", top: [1, 2], bot: [0, 0], dTop: 1, dBot: 0, sh: null, ch: null }, "a null row handed no marker carries no `view` key");
  assert.deepEqual(spacerRow("A", 1, 2, 0, 0, null, null, "inactive"), { sid: "A", top: [1, 2], bot: [0, 0], dTop: 1, dBot: 0, sh: null, ch: null, view: "inactive" }, "the switched-away view's row: nulls and the marker, minted by the builder on the owner's approval of 2026-09-21");
  assert.ok(!("view" in (spacerRow as any)("A", 1, 2, 0, 0, null, null, "away")), "a value the type does not name is not minted: the marker is the one word or nothing");
  assert.ok(!("view" in (spacerRow as any)("A", 1, 2, 0, 0, null, null, "Inactive")), "a case variant of the word is not minted: the guard is the word's exact spelling, not a lowered comparison");
  assert.ok(!("view" in (spacerRow as any)("A", 1, 2, 0, 0, null, null, true)), "a truthy non-string is not minted: the guard is equality with the word, not truthiness or a string test");
});

test("an inactive view's spacer write files no row, and a write that changes nothing files none", () => {
  const w = lift("B");   // the active view is another one
  const { v, items } = viewOver(w, 200, 301, 221, () => ["turn turn-assistant", 90]);
  buildOne(w, v, items);
  assert.equal(w.rafs.length, 0, "nothing queued for an inactive view");
  const w2 = lift("A");
  const world2 = viewOver(w2, 200, 301, 221, () => ["turn turn-assistant", 90]);
  w2.views.set("A", world2.v);
  buildOne(w2, world2.v, world2.items);
  w2.sizeSpacers(world2.v);
  assert.equal(w2.rafs.length, 1); w2.rafs[0]();
  assert.equal(w2.diag.length, 1, "the same height written twice files one row");
});

test("the observer's entry height is the border box (the height offsetHeight reports); contentRect is the fallback", () => {
  const w = lift(null);
  assert.equal(w.entryBoxHeight({ borderBoxSize: [{ blockSize: 33, inlineSize: 400 }], contentRect: { height: 19 } }), 33, "the array shape (the spec)");
  assert.equal(w.entryBoxHeight({ borderBoxSize: { blockSize: 33, inlineSize: 400 }, contentRect: { height: 19 } }), 33, "the object shape (older engines)");
  assert.equal(w.entryBoxHeight({ contentRect: { height: 19 } }), 19, "no box sizes: the content box");
  assert.equal(w.entryBoxHeight({}), 0);
});

// ── the follow-mode take at frame end ────────────────────────────────────────────────────────────

test("a follow-mode reader at the bottom is given the figures on the next paint: the frame-end take asks for it and writes nothing itself; anyone else's figures wait for the tail paint", () => {
  const two: Array<[string, number]> = [["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 90], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  // the active, shown, follow-mode view with the reader at the bottom: the observer's delivery parks the figures and asks for the paint
  const w = lift("A");
  const world = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  w.views.set("A", world.v); world.v.shown = true; world.v.stick = true;
  buildOne(w, world.v, world.items); observe(w, world.v, world.rows);
  assert.ok(world.v.measured, "the figures are parked by the measure");
  const topBefore = topPx(world.v);
  w.takeMeasureAtBottom(world.v);
  assert.equal(w.paints, 1, "one paint asked for (scheduleAppendActive)");
  assert.ok(world.v.measured, "…the figures still parked for it");
  assert.equal(world.v.pxPerTurn, undefined); assert.equal(topPx(world.v), topBefore, "no spacer written inside the observer's callback (a write there re-sizes the view under its own observer: the ResizeObserver loop error)");
  assert.deepEqual(w.writes, [], "…and no scroll written");
  // the paint (appendActive's sync, the one that passes atBottom) takes them; its own follow writes the bottom (append-stick, scroll-keep.ts followTail)
  paintTwo(w, world.v);
  assert.equal(world.v.measured, undefined, "taken by the paint");
  assert.equal(world.v.pxPerTurn, 100); assert.equal(world.v.gapUnits.get(0), 200 * 100, "the gap units follow");
  assert.notEqual(topPx(world.v), topBefore, "the spacer moved in the paint");
  w.takeMeasureAtBottom(world.v);
  assert.equal(w.paints, 1, "nothing parked: no paint asked for");
  // the same reader scrolled up: no paint asked for, the figures wait for the tail paint (appendActive restores their anchor there)
  const up = lift("A", 1000);
  const w2 = viewOver(up, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  up.views.set("A", w2.v); w2.v.shown = true; w2.v.stick = false;
  buildOne(up, w2.v, w2.items); observe(up, w2.v, w2.rows); up.takeMeasureAtBottom(w2.v);
  assert.ok(w2.v.measured, "parked"); assert.equal(w2.v.pxPerTurn, undefined); assert.deepEqual(up.writes, []); assert.equal(up.paints, 0);
  // follow mode recorded but the reader not at the bottom (a stale flag): nothing either
  const stale = lift("A", 1000);
  const w3 = viewOver(stale, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  stale.views.set("A", w3.v); w3.v.shown = true; w3.v.stick = true;
  buildOne(stale, w3.v, w3.items); observe(stale, w3.v, w3.rows); stale.takeMeasureAtBottom(w3.v);
  assert.ok(w3.v.measured, "the recorded follow mode alone does not move a reader who is not at the bottom"); assert.deepEqual(stale.writes, []); assert.equal(stale.paints, 0);
  // an inactive or hidden view: nothing
  const other = lift("B");
  const w4 = viewOver(other, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  other.views.set("A", w4.v); w4.v.shown = true; w4.v.stick = true;
  buildOne(other, w4.v, w4.items); observe(other, w4.v, w4.rows); other.takeMeasureAtBottom(w4.v);
  assert.ok(w4.v.measured); assert.deepEqual(other.writes, []); assert.equal(other.paints, 0);
  // a scroller with no box (the pane hidden: 0 - 0 - 0 reads as the bottom) is asked for nothing (the author's pass 0, high)
  const hidden = lift("A", 0);
  const w5 = viewOver(hidden, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  hidden.views.set("A", w5.v); w5.v.shown = true; w5.v.stick = true;
  buildOne(hidden, w5.v, w5.items); observe(hidden, w5.v, w5.rows);
  hidden.content.ch = 0; Object.defineProperty(hidden.content, "scrollHeight", { get() { return 0; } }); hidden.content.scrollTop = 0;
  hidden.takeMeasureAtBottom(w5.v);
  assert.ok(w5.v.measured, "parked"); assert.equal(hidden.paints, 0, "an emptied scroller reads as the bottom and asks for nothing");
});

// ── the take undone: a paint that finds no row to put back gives the figures back (the maintainer's round 3 ruling B) ─────────────────

test("figuresBefore then untakeMeasure: a take undone parks the figures again and puts the spacers and gap units back where the raw scrollTop was measured, with no layout read; a paint that took nothing gives nothing back; the next anchoring paint takes them", () => {
  const two: Array<[string, number]> = [["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 90], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  const w = lift(null);
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  buildOne(w, v, items); observe(w, v, rows);
  const parked = v.measured; assert.ok(parked, "the figures are parked by the observer's measure");
  const topOne = topPx(v), gapOne = v.gapUnits.get(0);
  const before = w.figuresBefore(v);   // what a paint reads before its take
  assert.deepEqual(before, { avg: undefined, per: undefined, measured: parked }, "the view's figures and the parked ones, as the paint finds them");
  assert.equal(w.untakeMeasure(v, before), false, "nothing taken yet: nothing to give back (what was parked is still parked)");
  assert.equal(topPx(v), topOne, "…and nothing moved");
  paintTwo(w, v);   // the paint takes (syncViewInner under the flag, or a flagged build)
  assert.equal(v.pxPerTurn, 100); assert.equal(v.measured, undefined); assert.notEqual(topPx(v), topOne, "the paint took: the spacer moved");
  assert.equal(w.untakeMeasure(v, before), true, "the restore found no row to put back: the take is given back");
  assert.deepEqual(v.measured, parked, "the figures are parked again, as they were");
  assert.equal(v.pxPerTurn, undefined); assert.equal(v.avgTurnH, undefined);
  assert.equal(topPx(v), topOne, "the head spacer is back where it stood when the raw scrollTop was measured"); assert.equal(v.gapUnits.get(0), gapOne, "the gap units too");
  assert.equal(w.untakeMeasure(v, before), false, "given back once: a second call finds what was parked still parked");
  paintTwo(w, v);
  assert.equal(v.pxPerTurn, 100, "the next anchoring paint takes them"); assert.equal(v.measured, undefined); assert.notEqual(topPx(v), topOne);
  // a paint with no take of its own gives nothing back whatever an earlier paint did: its own `before` saw nothing parked
  const later = w.figuresBefore(v);
  assert.equal(later.measured, undefined);
  assert.equal(w.untakeMeasure(v, later), false, "nothing was parked for this paint: the earlier take stands");
  assert.equal(v.pxPerTurn, 100);
  assert.deepEqual(w.reads, { offsetHeight: 0, scrollHeight: 0, clientHeight: 0 }, "no layout read in any of it");
});

// ── the unit observer's callback: a view with no width is the hidden case (the author's pass 0, high) ─

test("an observer delivery with the view at width 0 (an ancestor hid it) forgets the baselines and measures nothing: no 0 enters the heights map, nothing is parked, no paint is asked for; the re-show measures", () => {
  const two: Array<[string, number]> = [["turn turn-user", 30], ["turn turn-assistant", 70], ["turn turn-user", 30], ["turn turn-assistant", 90], ["turn turn-user", 30], ["turn turn-assistant", 500]];
  const w = lift("A");
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + 6, 101, (u) => two[u - 101]);
  w.views.set("A", v); v.shown = true; v.stick = true; (v.el as any).clientWidth = 800;
  buildOne(w, v, items);
  const { deliver, heights } = liftObserver(w, v, "A");
  // the first delivery at a real width: baselines, the measure, the paint asked for
  deliver(rows, (r) => r.realH);
  assert.equal(heights.get(rows[1]), 70, "the border boxes are the baselines");
  assert.deepEqual(v.measured, { avg: (30 + 70 + 30 + 90 + 30 + 500) / 6, per: 100 }, "the window measured");
  assert.equal(w.paints, 1, "a bottom reader's paint asked for");
  paintTwo(w, v);
  assert.equal(v.pxPerTurn, 100); const gapAfter = v.gapUnits.get(0), topAfter = topPx(v);
  // the ancestor hides the pane: every unit arrives at 0 with the view at width 0, its own display still ""
  (v.el as any).clientWidth = 0; v.measureDue = true;
  deliver(rows, () => 0);
  assert.equal(heights.get(rows[1]), undefined, "the baselines are forgotten, as on the view's own hide");
  assert.equal(v.measured, undefined, "nothing parked"); assert.equal(v.pxPerTurn, 100, "the figure stands"); assert.equal(v.gapUnits.get(0), gapAfter); assert.equal(topPx(v), topAfter);
  assert.equal(w.paints, 1, "no paint asked for");
  assert.equal(v.measureDue, true, "the measure still owed: the re-show pays it");
  // the re-show at the same width: real sizes again, baselines recorded, the owed measure runs off them (nothing changed: no new figure parked)
  (v.el as any).clientWidth = 800;
  deliver(rows, (r) => r.realH);
  assert.equal(heights.get(rows[1]), 70, "fresh baselines");
  assert.equal(v.measureDue, false, "measured on the re-show"); assert.equal(v.measured, undefined, "the same figures: nothing new parked");
  // …and what the zeros would have done, read as heights: the estimator refuses them (turn-estimate.test.ts), the map never holds them
  assert.equal(perTurnEstimate(rowsFor(rows, (r) => r.className, () => false, () => 0)), null, "the estimator hands out no 0");
});

test("a delivery on a view whose only child is the empty transcript's placeholder, or the deferred build's loading hint (the view's only child: render.ts appends it to an EMPTY view, never under a spacer), survives: the callback returns, measures nothing and files no unitchange row (the maintainer's round 3 ruling A: the unit-aware tail scan left tail at -1 and the pane's unitOf threw on children[-1] inside the observer's callback)", () => {
  // the two views the pane shows with no unit-carrying child: syncViewInner's tx-empty placeholder for a zero-event session (its swirl
  // removes itself on error, a height change), and showActive's tx-loading hint, the only child of a non-empty session's view for the frame
  // its heavy build is deferred to. The mutation observer hands every added element to this observer, so the first observation of either
  // is a baseline and a later height change an entry; the callback is the lifted one (the 13441 closure's dataset reach-in included)
  for (const [label, kids] of [["the placeholder", [["tx-empty", 120]]], ["the loading hint alone", [["tx-loading", 40]]]] as Array<[string, Array<[string, number]>]>) {
    const w = lift("A");
    const host = new FakeEl("div"); (host as any).clientWidth = 800;
    const rows = kids.map(([cls, h]) => host.appendChild(new FakeEl("div", cls, h, w.reads)));
    const v: any = { el: host, uh: new WeakMap<object, number>(), stick: true, shown: true, winStart: 0, winEnd: 0, unitTotal: 0 };
    w.views.set("A", v);
    const { deliver, heights } = liftObserver(w, v, "A");
    deliver(rows, (r) => r.realH);   // the first observation: the baselines
    const last = rows[rows.length - 1];
    assert.doesNotThrow(() => deliver([last], () => last.realH - 24), label + ": the callback survives a height change of the unit-less child (at the head: TypeError, reading dataset of undefined)");
    assert.equal(heights.get(last), last.realH - 24, label + ": the baseline moved on");
    assert.deepEqual(w.diag.filter((d) => d.kind === "unitchange"), [], label + ": no unitchange row (the parent's behaviour: the view's own change is the rail's tailchange row, which names it, tail-change-row.test.ts)");
    assert.equal(v.measured, undefined, label + ": nothing measured, there being no unit rows"); assert.equal(w.paints, 0, label + ": no paint asked for");
  }
});

// ── the resets that clear the average (the author's pass 0, low) ──────────────────────────────────────

test("forgetAverage drops a parked average with the figure, so a reset's build measures the new rows instead of taking the old rows' average", () => {
  const w = lift(null);
  // build one over dense rows; the observer parks the average; nothing takes it (the reader landed off the bottom, the session is idle)
  const dense = viewOver(w, 200, 1 + 100 + 4, 101, () => ["turn turn-assistant", 400]);
  buildOne(w, dense.v, dense.items); observe(w, dense.v, dense.rows);
  assert.equal(dense.v.measured?.avg, 400, "parked over the old rows, untaken");
  // the reset (the compact toggle, a re-collapse, the older-history re-anchor): the figure AND the parked one go
  w.forgetAverage(dense.v);
  assert.equal(dense.v.avgTurnH, undefined); assert.equal(dense.v.measured, undefined);
  // the rebuild over the new mode's rows: build (takes nothing), observe (measures the new rows), paint (takes the new average)
  const v = dense.v;
  while (v.el.children.length > 1) v.el.removeChild(v.el.lastChild!);
  const rows2: FakeEl[] = [];
  for (let i = 0; i < 4; i++) { const n = new FakeEl("div", "turn turn-assistant", 40, w.reads); n.dataset.unit = String(101 + i); v.el.appendChild(n); rows2.push(n); }
  buildOne(w, v, dense.items);
  assert.equal(v.avgTurnH, undefined, "the build took no parked figure");
  observe(w, v, rows2); paintTwo(w, v);
  assert.equal(v.avgTurnH, 40, "the new rows' average");
  // the counter-example the reset used to produce: clearing the figure alone leaves the parked one for the build to take
  const w2 = lift(null);
  const d2 = viewOver(w2, 200, 1 + 100 + 4, 101, () => ["turn turn-assistant", 400]);
  buildOne(w2, d2.v, d2.items); observe(w2, d2.v, d2.rows);
  d2.v.avgTurnH = undefined;   // the bare reset
  buildOne(w2, d2.v, d2.items);
  assert.equal(d2.v.avgTurnH, 400, "the old rows' average, taken by the build, would stand for the view's life");
  assert.equal(w.reads.offsetHeight, 0, "no layout read anywhere in this");
});

// ── the measure's population is the units (the maintainer's round 1 ruling) ───────────────────────────────────────

test("a hover's rail band among the view's children is not a row: the rows' average is over the children that carry a unit alone", () => {
  // drawRailBand appends the band to the thread with a class and no data-unit; the unit observer observes every added element, so the
  // band has a height in v.uh, and measureUnits' population was every child of the thread, band included (the maintainer's round 1 ruling, with the trim)
  const w = lift(null);
  const heights = [40, 90, 90, 30, 90, 90];
  const { v, items, rows } = viewOver(w, 200, 1 + 100 + heights.length, 101, (u) => [u === 101 || u === 104 ? "turn turn-user" : "turn turn-assistant", heights[u - 101]]);
  const band = new FakeEl("div", "rail-band rail-band-local", 4, w.reads);
  v.el.appendChild(band);
  buildOne(w, v, items);
  assert.ok(rows.length > 0, "the population is derived from the fixture's rows and must not be empty");
  const expected = rows.reduce((a, r) => a + r.realH, 0) / rows.length;
  assert.ok(expected > 0);
  v.uh.set(band, band.realH);   // the observer reported the band too (it observes every added element)
  observe(w, v, rows);
  assert.equal(v.measured?.avg, expected, "the mean over the unit rows: " + expected + " (the band's 4 px would pull it to " + (expected * rows.length + 4) / (rows.length + 1) + ")");
  assert.equal(v.measured?.per, undefined, "one complete turn in this window: no per-turn figure (the band is no turn row either)");
});

// ── source pins on what the harness does not lift ────────────────────────────────────────────────

test("render.ts: the render task's spacer code holds no layout read; the unit observer records border-box heights and measures in both of its branches", () => {
  const code = codeOf;   // the code alone (the compiler's comment ranges): the comments name the reads that are gone
  // the compiler's syntax tree of render.ts, for every count and census below (the maintainer's round 3 ruling E and its extra8-4 class: a raw
  // text count read a doc comment naming a call as a call; here a call, an assignment or a string literal is a node and a comment is not, so
  // the stripper stays for the text scans alone: the author's fixer pass over pass 4 moved the applyMeasure, forgetAverage and avgTurnH counts
  // and the spacer-follow check onto the tree after a planted comment naming the two calls turned the raw counts red)
  const sf = SF;   // parsed once at module level, with the owner rule (nameOf, ownerOf) the ordering window test below shares
  const NAMES = new Set(["renderWindowItems", "syncView", "untakeMeasure"]);
  const allCalls: ts.CallExpression[] = [], refs: ts.Identifier[] = [], strings = new Set<string>();
  const visit = (n: ts.Node): void => {
    if (ts.isCallExpression(n) && ts.isIdentifier(n.expression)) allCalls.push(n);
    if (ts.isIdentifier(n) && NAMES.has(n.text) && !(ts.isCallExpression(n.parent) && n.parent.expression === n) && !(ts.isFunctionDeclaration(n.parent) && n.parent.name === n)) refs.push(n);
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) strings.add(n.text);
    ts.forEachChild(n, visit);
  };
  visit(sf);
  // every WRITE to the average, in every form the tree can name, by owner (writesOf at module level, where the forms and their provenance
  // are documented; the ordering window test below reads the take state's writers through the same census)
  const avgWrites = writesOf(new Set(["avgTurnH"]), sf).map((w) => w.owner + ": " + w.describe);
  const callsTo = (name: string): ts.CallExpression[] => allCalls.filter((c) => (c.expression as ts.Identifier).text === name);
  const byOwner = (name: string): string[] => callsTo(name).map((c) => ownerOf(c) + "(" + c.arguments.map((a) => a.getText(sf)).join(", ") + ")").sort();
  const censusCalls = allCalls.filter((c) => NAMES.has((c.expression as ts.Identifier).text));
  // the stripper's own pin (the author's fixer pass over pass 3): a `//` in a quoted URL leaves the alias after it standing for the census, a quoted glob opens
  // no block comment, a regular expression's slashes are not a comment, and the comments themselves go
  assert.equal(code('const u = "http://h"; const rwi = renderWindowItems; // c\nz("image/*"); y(); /* c */ q(/^file:\\/\\//, ""); // d\n'),
    'const u = "http://h"; const rwi = renderWindowItems; \nz("image/*"); y();  q(/^file:\\/\\//, ""); \n', "the stripper keeps string, template and regular-expression literals whole and drops comments alone");
  const span = RENDER.slice(RENDER.indexOf("function gapUnitsOf("), RENDER.indexOf("function unitAtScroll("));
  const inFrame = span.slice(span.indexOf("function queueSpacerRow("), span.indexOf("// The window's two figures"));
  const paintSide = code(span.replace(inFrame, ""));
  assert.ok(paintSide.includes("function sizeSpacers(v") && paintSide.includes("function measureUnits(v") && paintSide.includes("function applyMeasure(v"), "the span holds the paint-side functions");
  assert.doesNotMatch(paintSide, /offsetHeight|scrollHeight|clientHeight|getBoundingClientRect|offsetTop/, "sizeSpacers, the trim, the eviction, the measure and the apply read no layout property");
  // the frame's read is per row, not per batch (the maintainer's round 1 addendum): once, only when a queued row is the shown view's. A row of a
  // view switched away since it was queued, or of the live view while its element is hidden (the section-at-a-glance view, where #content holds
  // the section list: the maintainer's round 5 ruling, extra10-1; the frame reads the element's display, the property, not snapView, its cause),
  // is filed with no geometry (sh and ch null) and the marker that says so, `view: "inactive"` (one fixed
  // word, no host name), admitted to the kernel's chat allowlist on the owner's approval (the owner 2026-09-21, who approved the field); the
  // shown view's row always carries numbers (a scroller with no box reads 0, an honest figure), so a null pair is built only for a view that was
  // not the live one in its frame, never with another view's figures. The two assertions after the frame's regex pin the marker on the frame's
  // SOURCE SPELLING (the call's two arms, the marker on the switched-away arm alone; the marker's word in the frame's code once, at that post);
  // the property by execution is the four row tests above (the switched-away row carries the marker, through the builder as built; the live
  // view hidden by the section view files nulls and the marker with no read; the active
  // view's two rows carry no `view` key, so a marker handed on the active arm reds there and not only here; the mixed frame files the
  // switched-away row with nulls beside the active view's row with the frame's figures, so a post handing the figures to both arms reds there
  // and not only here) and tests/test_client_diag_allowlist.py's presence cell (the chat entry names the key; the marked row is stored whole).
  assert.match(inFrame, /requestAnimationFrame\(\(\) => \{[\s\S]*?const liveView = activeId \? views\.get\(activeId\) : undefined;\s*\n\s*const live = liveView && liveView\.el\.style\.display !== "none" \? activeId : null;\s*\n\s*let sh: number \| null = null, ch: number \| null = null;\s*\n\s*if \(live && content && rows\.some\(\(\[rsid\]\) => rsid === live\)\) \{ sh = content\.scrollHeight; ch = content\.clientHeight; \}/, "the diag row's scroller read rides a frame, once, for the SHOWN live view's rows alone: the live id counts as live only while its element is not display none (the section-at-a-glance view hides every view and #content holds the list; the maintainer's round 5 ruling, extra10-1)");
  assert.match(inFrame, /rsid === live \? spacerRow\(rsid, a, b, c, d, sh, ch\) : spacerRow\(rsid, a, b, c, d, null, null, "inactive"\)\)/, "a switched-away view's row: no geometry and the `view` marker, on the owner's approval of 2026-09-21; keyed on the call's source spelling, so a marker reached another way is for the executed pins: the three row tests above (the switched-away row marked, the active view's rows unmarked, the mixed frame's two rows each with their own view's figures) and tests/test_client_diag_allowlist.py's presence cell");
  assert.equal((code(inFrame).match(/"inactive"/g) || []).length, 1, "the marker's word is in the frame's code once, as the switched-away arm's string literal (the comment names it too; the code alone is counted)");
  // the deferral is bounded on the visibility EVENT (the maintainer's round 5 ruling, kernel-1): the handler inside the span drops the
  // pending rows, cancels their frame and files one row through scrollDiagRow (the budget) with the allowlist's keys and no `view`; the
  // listener stands outside the span, beside the prebuild's, because a module-level statement inside it would run at lift time in the
  // harnesses that slice this region (the hidden-page cells above execute the handler through the harness's hide and show)
  assert.match(inFrame, /function dropSpacerRowsOnVisibility\(\): void \{\s*\n\s*const rows = spacerRowsPending;\s*\n\s*if \(rows\.length === 0\) return;\s*\n\s*spacerRowsPending = \[\];\s*\n\s*if \(spacerRowsRaf != null\) \{ cancelAnimationFrame\(spacerRowsRaf\); spacerRowsRaf = null; \}\s*\n\s*scrollDiagRow\("spacer-dropped", \{ sid: activeId \|\| "", n: rows\.length, kind: "spacer", why: document\.hidden \? "hidden" : "shown" \}\);/, "the visibility handler drops the pending rows, cancels their frame and files one budgeted row naming the count, the kind and the edge");
  assert.match(RENDER, /\ndocument\.addEventListener\("visibilitychange", dropSpacerRowsOnVisibility\);/, "the visibilitychange listener hands both edges to the span's handler, from outside the span");
  assert.doesNotMatch(inFrame, /const sh = content \? content\.scrollHeight : 0/, "the batch read is gone");
  const uo = RENDER.slice(RENDER.indexOf("v.uo = new ResizeObserver((entries) => {"), RENDER.indexOf("v.mo = new MutationObserver("));
  assert.match(uo, /unitHeights\.set\(e\.target, entryBoxHeight\(e\)\); view3\.measureDue = true; measureUnits\(view3\); takeMeasureAtBottom\(view3\); return; \}/, "a reflow records border boxes, re-measures and asks for a bottom reader's paint");
  assert.match(uo, /height: entryBoxHeight\(e\) \}\)\), view3\.el\.children, unitHeights, unitOf\);\s*\n\s*measureUnits\(view3\); takeMeasureAtBottom\(view3\);/, "…and so does every delivery");
  assert.match(uo, /if \(view3\.el\.style\.display === "none" \|\| w === 0\) \{ for \(const e of entries\) unitHeights\.delete\(e\.target\); return; \}/, "a view with no width is the hidden case: no zero enters the map");
  // the frame-end take decides and asks for the paint; it writes nothing inside the observer's callback (a spacer written there re-sizes the
  // view element under v.ro, delivered earlier in the same frame: the ResizeObserver loop error, the tab-row sentinel's precedent)
  const take = inFrame.slice(inFrame.indexOf("function takeMeasureAtBottom(v: View): void {"));
  assert.match(take, /if \(!content \|\| content\.clientHeight <= 0 \|\| !atBottom\(content\)\) return;\s*\n\s*scheduleAppendActive\(\);\s*\n\}/, "the take: a scroller with a box, at the bottom, then the paint asked for");
  assert.doesNotMatch(code(take), /writeScroll|sizeSpacers|redrawGapUnits|applyMeasure|style\./, "…and no write of its own");
  assert.ok(!strings.has("spacer-follow"), "the writer is gone with it (landing-settle.ts's census): no string literal names it");
  assert.doesNotMatch(code(uo), /writeScroll|style\.height|sizeSpacers|redrawGapUnits/, "nothing in the unit observer's callback writes the DOM");
  // the parked figures reach the DOM under one rule (the maintainer's round 1 addendum): a figure is taken ONLY by a paint that anchors the reader, and EVERY
  // anchoring paint takes one. The takers: syncViewInner under the `anchored` flag (appendActive's follow or the anchor its restore holds,
  // `stick || !!anchor`; the toggle's keep when it captured a row, `!!anchor`), a window build under the same flag from its caller (a deep
  // link's or a moment's land, the re-window, a fill with a row or a point to put back), landActive on every road but the nothing-armed
  // re-show (land-saved, the raw write; an ARMED land that misses takes and puts the saved place's row back, anchor-restore, and writes
  // raw only when that restore finds no row to put back: the maintainer's round 2 ruling, the third such road named by the author's own verifiers after pass 3, executed in
  // land-active-keep.test.ts), and keepPlaceAcrossWindow over its restore. A switch's, a landing's or a hidden prebuild's sync passes no flag and applies
  // nothing (a 55 px move of a bottom reader in the landing lab), a fill that can only restore its raw top passes false, and a paint whose
  // only restore is a raw scrollTop (appendActive with no capturable row, the toggle for a bottom or row-less reader) passes false too.
  // The rule's OUTCOME half (the maintainer's round 3 ruling B): a paint that took and then found no row to put back gives the figures
  // back before its raw write (untakeMeasure: parked again, the spacers and gap units re-drawn), so, net, it took nothing; the mechanism is
  // executed above, and each reader's road in its harness (land-active-keep, toolgroup-toggle-keep, append-active-keep, fill-in-place,
  // scroll-to-anchor-roads). The reload restore's raw write keeps its take: its scrollTop was measured against the figures the take re-derives.
  assert.match(RENDER, /function syncViewInner\(id: string, atBottom\?: boolean, anchored: boolean = atBottom !== undefined\): View \{/, "the flag defaults to 'atBottom was passed'");
  assert.match(RENDER, /if \(anchored && applyMeasure\(v\)\) \{ redrawGapUnits\(v\); sizeSpacers\(v\); \}/, "syncViewInner takes the figures inside an anchoring paint alone");
  assert.match(RENDER, /function renderWindowItems\([^\n]*anchored = false\): void \{\n(?:\s*\/\/[^\n]*\n)*\s*if \(anchored\) applyMeasure\(v\);/, "a window build takes them only when its caller anchors");
  const land = RENDER.slice(RENDER.indexOf("function landActive(content: HTMLElement | null, v: View): void {"), RENDER.indexOf("\n}\n", RENDER.indexOf("function landActive(content: HTMLElement | null, v: View): void {")));
  assert.match(land, /const saved = !pendingAnchor && pendingAnchorT == null && !\(seek && seek\.sid === activeId\) && v\.shown && !v\.stick && takeReloadScroll\(pendingReloadScroll, activeId\) == null;\s*\n\s*const held = !saved && v\.shown && !v\.stick \? captureScrollAnchor\(content, v, v\.scrollTop\) : null;[^\n]*\n\s*const figures = figuresBefore\(v\);[^\n]*\n\s*if \(!saved && applyMeasure\(v\)\) redrawGapUnits\(v\);\s*\n\s*sizeSpacers\(v\);/,
    "landActive takes on every road but the nothing-armed re-show, BEFORE its landing attempt (the gate reads what is armed), captures the row at the saved place and reads the figures first, and sizes the spacers after the take; the outcome decides what stands (the fallback below, executed in land-active-keep.test.ts)");
  assert.match(land, /else if \(!\(held && restoreScrollAnchor\(content, v, held\)\)\) \{ untakeMeasure\(v, figures\); writeScroll\(content, v\.scrollTop, "land-saved"\); \}/, "the saved-place fallback restores the captured row; where that restore finds no row to put back the take is given back and the raw write follows, exact in the layout it was saved in: nothing armed (nothing taken, nothing given back), no row at the saved place, or the captured row gone with the attempt's window build (land-active-keep.test.ts executes the three)");
  const keep = RENDER.slice(RENDER.indexOf("function keepPlaceAcrossWindow("), RENDER.indexOf("\n}\n", RENDER.indexOf("function keepPlaceAcrossWindow(")));
  assert.match(keep, /const under = captureScrollAnchor\(content, v\);\s*\n\s*const figures = figuresBefore\(v\);[^\n]*\n\s*if \(applyMeasure\(v\)\) \{ redrawGapUnits\(v\); sizeSpacers\(v\); \}\s*\n\s*if \(restoreScrollAnchor\(content, v, keep\)\) return true;/,
    "keepPlaceAcrossWindow captures the row under the viewport top and reads the figures, then takes over its restore, spacers and gap units first (the take stays above the restores, which read the re-sized layout; land-active-keep.test.ts executes the roads and the double miss)");
  assert.match(keep, /if \(!landed && !\(under && restoreScrollAnchor\(content, v, under\)\)\) untakeMeasure\(v, figures\);/, "the double miss puts the captured row back over the take instead of writing nothing (the maintainer's round 2 ruling), and with that row gone too gives the take back (the maintainer's round 3 ruling B)");
  assert.deepEqual(byOwner("applyMeasure"), ["keepPlaceAcrossWindow(v)", "landActive(v)", "renderWindowItems(v)", "syncViewInner(v)"], "four takers, by owner from the syntax tree: syncViewInner, the window build, landActive (once) and keepPlaceAcrossWindow; the frame-end take asks for the first");
  // The censuses over the take rule's callers, each keyed on the PROPERTY it guards and read from the compiler's syntax tree, never from a
  // list of spellings (the maintainer's round 3 ruling E: the round-2 censuses read raw text, keyed a build's flag on membership in a
  // three-spelling set, attributed a call to the nearest preceding `function name(` by textual position, and stripped comments from one
  // scan of three). The axis of each, with the thing it refuses and the spelling it is indifferent to (the mutations note executes both):
  // 1. the anchoring flag per caller: every renderWindowItems and syncView call, paired as (owner, flag kind). The owner is the nearest
  //    NAMED enclosing function (a declaration, a method or a named function expression, else the variable or property an anonymous
  //    function is assigned to), walking out past anonymous callbacks, the rule writer-census.ts reads writeScroll's callers by. The flag
  //    kind is a constant (`true`, `false`, absent or `undefined`), the paint's own parameter handed on (`anchored`), or the caller's own
  //    predicate (any other expression), whose SEMANTICS the caller's harness executes (fill-in-place, append-active-keep,
  //    toolgroup-toggle-keep, scroll-to-anchor-roads). Refuses a constant where the road owes a predicate (`true` at the fill's build lies
  //    about a road that does not always anchor; `false` at its fallback takes nothing where a row is put back) and a build or sync added
  //    anywhere, syncViewInner included (a multiset); indifferent to the predicate's spelling (`pointBefore != null || keepVisible` is the
  //    same kind) and to layout (a call split across lines or moved into a callback of the same owner).
  // 2. the owner by lexical scope: a build moved into an arrow assigned to `plantedFill` inside fillInPlace's text is plantedFill's, not
  //    fillInPlace's (the textual walk said fillInPlace); a wrapper function is a call the census reads, under the wrapper's name.
  // 3. no bare reference: an identifier that is not a callee and not the definition's name (`const rwi = renderWindowItems`) would hand the
  //    function to a caller neither census reads; a comment or a string naming a call is not an identifier, so a doc comment quoting a call
  //    is not a call (the raw scans counted one).
  // 4. the untake sites by owner: every reader of the take state whose road can end unanchored gives the take back before its raw write
  //    (the maintainer's round 3 ruling B), a multiset over the same owners; a site removed, or added to a reader not on the list, reds.
  // appendActive's sync line is pinned by text as well: the flag's spelling is what its harness models.
  assert.match(RENDER, /const anchor = !stick && v \? captureScrollAnchor\(content, v\) : null;\n\s*const figures = v \? figuresBefore\(v\) : null;[^\n]*\n(?:\s*\/\/[^\n]*\n)*\s*syncView\(activeId, stick, stick \|\| !!anchor\);/, "appendActive's sync is flagged by its follow or the anchor it captured, never by atBottom alone, and the figures are read before it for the raw road's untake (append-active-keep.test.ts executes the roads)");
  const flagKind = (arg: ts.Expression | undefined): string => {
    if (!arg) return "absent";
    if (arg.kind === ts.SyntaxKind.TrueKeyword) return "true";
    if (arg.kind === ts.SyntaxKind.FalseKeyword) return "false";
    if (ts.isIdentifier(arg) && arg.text === "undefined") return "absent";
    if (ts.isIdentifier(arg) && arg.text === "anchored") return "handed on";
    return "predicate";
  };
  const pairs = (name: string, argAt: number): string[] => censusCalls.filter((c) => (c.expression as ts.Identifier).text === name).map((c) => ownerOf(c) + ": " + flagKind(c.arguments[argAt])).sort();
  assert.ok(censusCalls.length >= 24, "the censuses are not empty: " + censusCalls.length + " calls");
  assert.deepEqual(pairs("renderWindowItems", 6), [
    "fillInPlace: predicate",          // the fill's land: a row or a point to put back (fill-in-place.test.ts executes the three roads and the raw roads' untake)
    "fillInPlace: true",               // the re-window around the point: the point is put back by its turn, or the take is given back
    "landNearestMoment: true",         // the moment's row is landed below; its one caller, landActive, took before it
    "scrollToAnchor: true",            // landOn or the keep-offset re-land puts the target under the reader, or the take is given back on a miss (scroll-to-anchor-roads.test.ts)
    "syncViewInner: handed on",        // the first build or rewind: the paint's own flag, from its caller
    "syncViewInner: handed on",        // the rebuild: the same
    "virtualizeToViewport: true",      // the bottom or the focus unit's offset is written, or the take is given back
  ].sort(), "the window builds by owner and the kind of flag each hands: a constant where the road owes a predicate, an owner not on the list, or a build added anywhere reds");
  assert.deepEqual(pairs("syncView", 2), [
    "appendActive: predicate",         // its follow or the anchor its restore holds (append-active-keep.test.ts)
    "fillInPlace: predicate",          // the no-unit fallback: the same predicate as the fill's build (fill-in-place.test.ts)
    "reviveFailedLocal: absent",       // the placeholder re-render anchors nothing
    "runPrebuild: absent",             // the hidden prebuild anchors nothing
    "showActive: absent",              // the switch's build: landActive and keepPlaceAcrossWindow land it
    "showActive: absent",              // the deferred build: the same
    "toggleToolGroup: predicate",      // whether a row was captured (toolgroup-toggle-keep.test.ts)
  ].sort(), "the syncView calls by owner and the kind of flag each hands");
  assert.deepEqual(refs.map((r) => r.text + " in " + ownerOf(r)), [], "neither renderWindowItems, syncView nor untakeMeasure is handed on as a bare reference (an identifier that is not a callee; comments and strings are not identifiers)");
  assert.deepEqual(censusCalls.filter((c) => (c.expression as ts.Identifier).text === "untakeMeasure").map((c) => ownerOf(c)).sort(),
    ["appendActive", "fillInPlace", "fillInPlace", "keepPlaceAcrossWindow", "landActive", "landNearestMoment", "scrollToAnchor", "scrollToAnchor", "toggleToolGroup", "virtualizeToViewport"].sort(),
    "the take is given back at every road that can end unanchored: appendActive's raw write, the fill's two raw roads, the keep's double miss, landActive's land-saved after a take, the moment's miss, scrollToAnchor's two misses, the toggle's raw write, the re-window's lost focus unit");
  // 5. the writes by reader (the author's fixer pass over pass 4, its own finding, narrowed by the closing pass over it and widened one hop
  //    by the author's pass over the second closing lens): axis 4 pins the untake SITES and the harnesses drive the roads they name, so a
  //    raw write added inside a listed reader after its take, with no untake, was caught by nothing when it reused a writer name the family
  //    already has (`writeScroll(content, 12345, "land-saved")` planted in landActive ran green through spacer-measure, land-active-keep and
  //    landing-settle before this census); a write under a NEW name (`"planted-raw"`) was refused by landing-settle.test.ts's writer census,
  //    an unclassified writer, before this census existed, so that shape is caught twice. Every call of the write family (writeScroll and the
  //    wrappers landing-settle.ts registers, WRITER_WRAPPERS, the writer read at each one's registered position) outside the wrappers' own
  //    bodies (writeScroll inside scrollContentBy, scrollElInto inside landOn's local `land`: a wrapper's body is what its calls stand for)
  //    that runs under a reader on the untake list, as (reader, writer), a closed multiset: a write added under one of these readers reds
  //    here and owes its road a harness case (the six harnesses are the executed guard on the raw roads). Two attributions:
  //    - DIRECT: the reader is the first function on the call's lexical chain, innermost outward, that is on the list, so a write inside a
  //      named inner function of a reader is the reader's and is named with its inner owner (the closing pass: attributed to the nearest
  //      name and filtered by the list, `const later = () => writeScroll(...); later();` planted in landActive fell out of the census and
  //      passed every leg, where the same write in an anonymous callback was counted).
  //    - ONE HOP: a family call in another render.ts function F (the outermost named function on the call's chain) is attributed to every
  //      call of F whose own chain holds a reader, the conduit named (`landActive: anchor-restore via restoreScrollAnchor`), F on the list
  //      or not (scrollToAnchor's keep-offset is landActive's too, through landActive's call of scrollToAnchor); a reader's call of itself
  //      adds nothing (landActive's retry when the chat becomes visible: its writes are its own at zero hops). Before this hop (the second
  //      closing lens over the closing pass) a module-level helper calling writeScroll, called from landActive after its take, and a second
  //      write inside restoreScrollAnchor, which keepPlaceAcrossWindow and landActive call under their takes, were attributed to nobody and
  //      passed every leg.
  //    Outside the census, by construction: a write two hops away (a helper's helper), a write at module level (an anonymous handler, no
  //    name to be called by) and a conduit called through a property access; a write outside these readers is outside the take rule and
  //    outside this census.
  const UNTAKERS = new Set(["appendActive", "fillInPlace", "keepPlaceAcrossWindow", "landActive", "landNearestMoment", "scrollToAnchor", "toggleToolGroup", "virtualizeToViewport"]);
  const FAMILY: Readonly<Record<string, number>> = WRITER_WRAPPERS;   // the write family and the writer's position in each call (writeScroll 2, scrollContentBy 2, scrollElInto 3, land 0, settleLand 1), the table landing-settle.test.ts's writer census reads and pins
  const inFamilyName = (name: string): boolean => Object.prototype.hasOwnProperty.call(FAMILY, name);
  const inFamily = (c: ts.CallExpression): boolean => inFamilyName((c.expression as ts.Identifier).text);
  const readerOf = (n: ts.Node): string | null => { for (let p: ts.Node | undefined = n.parent; p; p = p.parent) { if (ts.isFunctionLike(p)) { const nm = nameOf(p); if (nm && UNTAKERS.has(nm)) return nm; } } return null; };
  const topOwnerOf = (n: ts.Node): string => { let top = "<module>"; for (let p: ts.Node | undefined = n.parent; p; p = p.parent) { if (ts.isFunctionLike(p)) { const nm = nameOf(p); if (nm) top = nm; } } return top; };
  const writerOf = (c: ts.CallExpression): string => { const a = c.arguments[FAMILY[(c.expression as ts.Identifier).text]]; return !a ? "absent" : ts.isStringLiteral(a) ? a.text : a.getText(sf); };
  const familyCalls = allCalls.filter(inFamily);
  assert.ok(familyCalls.length > 12, "the write family is called across render.ts, inside the readers and out: " + familyCalls.length + " calls");
  const familyWrites = familyCalls.filter((c) => !inFamilyName(ownerOf(c)));   // outside the wrappers' own bodies
  const pairOf = (reader: string, owner: string, c: ts.CallExpression, via: string | null): string => { const fn = (c.expression as ts.Identifier).text; return reader + (owner === reader ? "" : " (inside " + owner + ")") + ": " + writerOf(c) + (fn === "writeScroll" ? "" : " via " + fn) + (via ? " via " + via : ""); };
  const direct = familyWrites.flatMap((c) => { const r = readerOf(c); return r ? [pairOf(r, ownerOf(c), c, null)] : []; });
  const oneHop = familyWrites.flatMap((c) => { const F = topOwnerOf(c); if (F === "<module>") return []; return allCalls.filter((k) => (k.expression as ts.Identifier).text === F).flatMap((k) => { const r = readerOf(k); return r && r !== F ? [pairOf(r, ownerOf(k), c, F)] : []; }); });
  assert.deepEqual([...direct, ...oneHop].sort(), [
    "appendActive: append-raw", "appendActive: append-stick",                                                        // the raw road (the untake before it) and the follow
    "fillInPlace: gap-fill", "fillInPlace: gap-fill",                                                                // the two raw roads, each with its untake
    "landActive: land-bottom", "landActive: land-saved", "landActive: reload-restore", "landActive: reload-restore",   // the bottom land; the saved place (the untake before it); the reload restore's two shapes (the take stands there, by measurement)
    "scrollToAnchor: keep-offset",                                                                                   // the keep-offset re-land; the two misses write nothing after their untake
    "toggleToolGroup: toolgroup-toggle",                                                                             // the raw road (the untake before it)
    "virtualizeToViewport: rewindow", "virtualizeToViewport: rewindow",                                              // the bottom, and the focus unit's offset (the untake when the unit is gone)
    // one hop, the conduit named: restoreScrollAnchor's write under every reader that puts a captured row back after its take
    "appendActive: anchor-restore via restoreScrollAnchor",                                                          // the scrolled-up reader's anchor
    "keepPlaceAcrossWindow: anchor-restore via restoreScrollAnchor", "keepPlaceAcrossWindow: anchor-restore via restoreScrollAnchor",   // the kept row; the row under the viewport top on the miss
    "landActive: anchor-restore via restoreScrollAnchor", "landActive: anchor-restore via restoreScrollAnchor",     // the reload restore's anchor; the saved place's captured row
    "toggleToolGroup: anchor-restore via restoreScrollAnchor",                                                       // the toggle's captured row
    // one hop through a reader: scrollToAnchor's own write under the readers that land through it, and landOn's landing under the two that land on a turn
    "keepPlaceAcrossWindow: keep-offset via scrollToAnchor",                                                         // the kept row re-landed by uuid
    "landActive: keep-offset via scrollToAnchor", "landActive: keep-offset via scrollToAnchor",                      // the armed anchor; the reload restore's anchor re-landed
    "landNearestMoment: land-on via land via landOn", "scrollToAnchor: land-on via land via landOn",                // the landing itself, through landOn's local wrapper
  ].sort(), "every write of the family that runs under a reader of the take state, by reader and writer, direct or one hop through a named conduit (an inner owner, a wrapper and the conduit named where they apply): a write added under one of these readers, under any writer name, inside any inner function, through any registered wrapper or through a helper a reader calls, reds here and owes a harness case for its road");
  // every reset that clears the average clears the parked figures with it (forgetAverage), and none clears the figure bare
  assert.match(RENDER, /function forgetAverage\(v: View\): void \{\s*\n\s*v\.avgTurnH = undefined; v\.measured = undefined;\s*\n\}/);
  assert.deepEqual(avgWrites.sort(), ["applyMeasure: m.avg", "forgetAverage: undefined", "untakeMeasure: before.avg"], "the average is written by the take, the untake and the one bare clear, the helper's (by owner from the syntax tree, in every form the tree can name: every assignment operator, an increment, a delete, a destructuring pattern that names the field, a for-of or for-in over it, or an Object.assign, defineProperty, defineProperties or Reflect call whose receiver or literal key names it: writesOf)");
  assert.deepEqual(byOwner("forgetAverage"), ["chatHead(v)", "rerenderAll(v)", "runPrebuild(v)", "showActive(v)"], "four resets, by owner from the syntax tree: the older-history re-anchor, the compact toggle's rerender, the prebuild's and the switch's re-collapse");
  assert.match(RENDER, /import \{ rowsFor, meanRowHeight, perTurnEstimate \} from "\.\/turn-estimate";/);
  assert.match(RENDER, /interface View \{[^\n]*measured\?: \{ avg\?: number; per\?: number \};/, "the parked figures live on the view");
});

// ── the `view` key's minters across the modules the page bundles LOAD, by the PROPERTY (the maintainer's round 5 ruling, tests-1, adopting the census refuted extra7-2 proposed; the population derived from the bundles since the maintainer's round 6 ruling, correctness-1 and extra8-2) ──

const pkgRequire = createRequire(path.resolve(process.cwd(), "package.json"));   // vscode-extension/: esbuild.js and its esbuild, as editor-lazy.test.ts requires them
const ROOT = path.resolve(process.cwd(), "..");
const MODULE_SUFFIX = /\.(ts|mts|cts|tsx|js|mjs|cjs|jsx)$/;   // the partitions' module class: every suffix the compiler parses (a .tsx or .jsx under its own ScriptKind)
const TEST_OR_TYPES = /\.test\.([mc]?[tj]s|[tj]sx)$|\.d\.([mc]?ts|tsx)$/;   // the listing's tests-and-types class: a `.test.` file of any module suffix (`.ts`, `.mts`, `.cts`, `.tsx`, `.js`, `.mjs`, `.cjs`, `.jsx`) or a `.d.` file of a TypeScript one (`.d.ts`, `.d.mts`, `.d.cts`, `.d.tsx`), so a test of a JavaScript suffix is a test, not a module the unloaded equality below names (the maintainer's round 8 ruling, correctness-1); a disclosed residual: vscode-extension/esbuild.js's testBuild bundles `.test.ts` alone, so a test of any other suffix under ui/webview is a test no leg runs
const STYLE_SUFFIX = /\.css$/;                                   // the styles class: the page stylesheets among the bundles' inputs, not modules
const FIXTURE_DIR = /^ui\/webview\/anchor-map-fixtures\//;      // the listing's one non-module directory, the anchor map's fixtures (.md, .json, .py, .html, .csv, .svg, .css and a .gitattributes today); the listing tries it before every suffix class, so a file of a module or a stylesheet suffix under it is a fixture (the maintainer's round 8 ruling, correctness-1)
/** A PARTITION, never a filter (the maintainer's round 7 ruling, extra7-1): every file goes to the first class whose test matches it, and a
 *  file no class takes is a red naming it and its suffix, so a file of a kind the census has not named (a `.tsx` module a page bundle loads,
 *  a stylesheet of a new suffix, a stray file in the directory) is loud where a suffix filter dropped it in silence. */
function partition(files: string[], classes: Array<[string, RegExp]>, where: string): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const [k] of classes) out[k] = [];
  const rest: string[] = [];
  for (const f of files) { const c = classes.find(([, re]) => re.test(f)); if (c) out[c[0]].push(f); else rest.push(f); }
  assert.deepEqual(rest, [], where + ": every file is in one of the named classes (" + classes.map(([k]) => k).join(", ") + "); a file none takes is named here with its suffix and is given a class or excluded by name, never dropped: " + rest.map((f) => f + " (" + (path.extname(f) || "no suffix") + ")").join(", "));
  return out;
}
/** The modules the page bundles load: esbuild's metafile of the shipped `webview` config (vscode-extension/esbuild.js exports the config and
 *  emits no metafile of its own; its entry list is taken in any of the three forms esbuild documents, the guard below) built in memory,
 *  nothing written, the shape ui/webview/editor-lazy.test.ts builds the editor chunk with; every input keyed by its path relative to
 *  vscode-extension/, made repo-relative here with forward slashes. Inputs under node_modules are third-party and left out; the rest are
 *  partitioned into modules and styles (the `.css` inputs), the remainder asserted empty. Built once, in the census cell, its one caller (the
 *  memo below holds that build, so a failed build rejects the promise the census awaits and reds that cell with esbuild's message); the
 *  witness cell runs synthetic sources through the walker (censusViewWrites) and needs no build. */
let bundledP: Promise<string[]> | null = null;
function bundledModules(): Promise<string[]> {
  if (!bundledP) bundledP = (async () => {
    const { webview } = pkgRequire("./esbuild.js") as { webview?: import("esbuild").BuildOptions };
    // the config is checked before it is spread (a spread of undefined is legal) and the build's metafile before it is read: esbuild resolves
    // an undefined config or an empty entry list with zero inputs and zero errors, and the census would then red three assertions later
    // blaming modules that stopped being loaded, with the figure 0 loaded in a parenthesis (the maintainer's round 7 ruling, extra7-2). The
    // entry list is taken in each of the three forms esbuild documents, an array of paths, an array of in-and-out objects (the shipped list
    // mixes the two: the pdf worker's entry is an object among strings) and a record of output names to paths, which builds the same inputs
    // as the array; it is refused when empty in any form or of another type, the message naming the form found (the maintainer's round 8
    // ruling, correctness-2)
    const ep: unknown = webview && typeof webview === "object" ? webview.entryPoints : undefined;
    const form = Array.isArray(ep) ? "an array of " + ep.length + " entries" : ep !== null && typeof ep === "object" ? "a record of " + Object.keys(ep).length + " names" : ep === undefined ? "undefined" : "a " + typeof ep + ", " + JSON.stringify(ep);
    const filled = Array.isArray(ep) ? ep.length > 0 : ep !== null && typeof ep === "object" && Object.keys(ep).length > 0;
    assert.ok(webview && typeof webview === "object" && filled, "vscode-extension/esbuild.js's `webview` export, the shipped page config this census builds in memory, is an object whose entryPoints is non-empty in one of the three forms esbuild documents (an array of paths, an array of in-and-out objects, or a record of output names to paths; a renamed export, an emptied array or an emptied record builds nothing): got " + (webview && typeof webview === "object" ? "an object whose entryPoints is " + form : String(webview)));
    const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
    const r = await esbuild.build({ ...webview, write: false, metafile: true, logLevel: "silent" });
    const inputs = Object.keys(r.metafile!.inputs);
    assert.ok(inputs.length > 0, "the in-memory build of the shipped webview config produced nothing: esbuild's metafile lists no input (" + Object.keys(r.metafile!.outputs).length + " outputs, " + r.errors.length + " errors), so there is no loaded set to census");
    const own = inputs.filter((k) => !k.includes("node_modules/")).map((k) => path.relative(ROOT, path.resolve(process.cwd(), k)).split(path.sep).join("/"));
    const parts = partition(own, [["modules", MODULE_SUFFIX], ["styles", STYLE_SUFFIX]], "the page bundles' inputs outside node_modules");
    // the module class is checked too: an entry list that names only a third-party file or only a stylesheet builds inputs and no module,
    // so the metafile guard above passes, and the census would again red at the directory equality blaming the modules, 0 loaded
    assert.ok(parts.modules.length > 0, "the in-memory build of the shipped webview config reached no module outside node_modules (esbuild's metafile: inputs " + inputs.length + ", under node_modules " + (inputs.length - own.length) + ", stylesheets " + parts.styles.length + ", outputs " + Object.keys(r.metafile!.outputs).length + "), so there is no loaded set to census");
    return parts.modules.sort();
  })();
  return bundledP;
}
/** Every file under `dir`, recursively, repo-relative with forward slashes. */
function filesUnder(dir: string): string[] {
  const out: string[] = [];
  const walk = (d: string): void => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); if (e.isDirectory()) walk(p); else if (e.isFile()) out.push(path.relative(ROOT, p).split(path.sep).join("/")); } };
  walk(dir);
  return out.sort();
}
type Site = { module: string; owner: string; form: string; node: ts.Node; sf: ts.SourceFile };
type ViewCensus = { sites: Site[]; builders: Set<string>; dataLiterals: Array<{ sf: ts.SourceFile; node: ts.Node }>; posts: number; opaque: number };
const newViewCensus = (): ViewCensus => ({ sites: [], builders: new Set<string>(), dataLiterals: [], posts: 0, opaque: 0 });
const describeSite = (s: Site): string => s.module + " " + s.owner + ": " + s.form;
const inDataLiteral = (c: ViewCensus, s: Site): boolean => c.dataLiterals.some((d) => d.sf === s.sf && s.node.getStart(s.sf) >= d.node.getStart(d.sf) && s.node.getEnd() <= d.node.getEnd());
/** One module's tree walked for the `view` census (the cell below says what is keyed on and what reaches a post); `module` is the repo-relative
 *  path, the key of the closed multiset, and render.ts's scrollDiagRow calls are read when the module is render.ts. Module-level so the witness
 *  cell runs a synthetic source through the same walker the census runs. */
function censusViewWrites(module: string, sf: ts.SourceFile, c: ViewCensus): void {
  const KEY = "view";
  const nameIn = (fn: ts.SignatureDeclaration): string | null => {
    if (ts.isConstructorDeclaration(fn)) { const k = fn.parent; return "constructor of " + (ts.isClassLike(k) && k.name ? k.name.text : "<class>"); }
    if ((ts.isFunctionDeclaration(fn) || ts.isMethodDeclaration(fn) || ts.isFunctionExpression(fn)) && fn.name) return ts.isIdentifier(fn.name) ? fn.name.text : fn.name.getText(sf);
    const p = fn.parent;
    if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
    if (p && (ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p))) return p.name.getText(sf);
    return null;
  };
  const ownerIn = (n: ts.Node): string => { for (let p: ts.Node | undefined = n.parent; p; p = p.parent) { if (ts.isFunctionLike(p)) { const nm = nameIn(p); if (nm) return nm; } if (ts.isClassLike(p) && p.name) return "class " + p.name.text; } return "<module>"; };
  const memberKey = (n: ts.PropertyName | undefined): string | null => !n ? null : ts.isIdentifier(n) || ts.isStringLiteralLike(n) ? n.text : ts.isComputedPropertyName(n) && ts.isStringLiteralLike(n.expression) ? n.expression.text : null;
  const namesKey = (e: ts.Node): boolean => (ts.isPropertyAccessExpression(e) && e.name.text === KEY) || (ts.isElementAccessExpression(e) && ts.isStringLiteralLike(e.argumentExpression) && e.argumentExpression.text === KEY);
  const isAssign = (n: ts.Node): n is ts.BinaryExpression => ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment;
  const site = (node: ts.Node, form: string): void => { c.sites.push({ module, owner: ownerIn(node), form, node, sf }); };
  const memberNamed = (o: ts.ObjectLiteralExpression, k: string): ts.ObjectLiteralElementLike | undefined => o.properties.find((p) => !ts.isSpreadAssignment(p) && memberKey(p.name) === k);
  // a post's or a call's data: a literal is read directly (and its spreads' calls are builders), a named function called is a builder, a
  // conditional's arms, a parenthesis and Object.assign's arguments are walked; anything else (an identifier bound elsewhere, a parameter, a
  // key built from a string VALUE: Object.fromEntries over a literal pair list, JSON.parse of a literal) is outside the attributable population
  // AND outside the closed multiset, since the tree names no property write in it: it is counted as opaque and held by the kernel's allowlist
  // and value bound alone (the maintainer's round 6 ruling, extra8-3; the witness cell below)
  const dataOf = (e: ts.Node | undefined): void => {
    if (!e) return;
    if (ts.isParenthesizedExpression(e) || ts.isAsExpression(e)) return dataOf(e.expression);
    if (ts.isConditionalExpression(e)) { dataOf(e.whenTrue); dataOf(e.whenFalse); return; }
    if (ts.isObjectLiteralExpression(e)) { c.dataLiterals.push({ sf, node: e }); for (const p of e.properties) if (ts.isSpreadAssignment(p)) dataOf(p.expression); return; }
    if (ts.isCallExpression(e) && ts.isIdentifier(e.expression)) { c.builders.add(e.expression.text); return; }
    if (ts.isCallExpression(e) && ts.isPropertyAccessExpression(e.expression) && e.expression.getText(sf) === "Object.assign") { for (const a of e.arguments) dataOf(a); return; }
    c.opaque++;
  };
  const go = (n: ts.Node): void => {
    if (ts.isObjectLiteralElementLike(n) && !ts.isSpreadAssignment(n) && memberKey(n.name) === KEY) site(n, ts.isShorthandPropertyAssignment(n) ? "a literal shorthand" : ts.isPropertyAssignment(n) ? "a literal property" : ts.isMethodDeclaration(n) ? "a method" : "an accessor");
    if (ts.isPropertyDeclaration(n) && memberKey(n.name) === KEY) site(n, "a class field");
    if (ts.isParameter(n) && ts.isIdentifier(n.name) && n.name.text === KEY && (ts.getModifiers(n) || []).length > 0 && ts.isConstructorDeclaration(n.parent)) site(n, "a parameter property");
    if (isAssign(n)) for (const t of targetsOf(n.left)) if (namesKey(t)) site(n, "an assignment");
    if ((ts.isForOfStatement(n) || ts.isForInStatement(n)) && !ts.isVariableDeclarationList(n.initializer)) for (const t of targetsOf(n.initializer)) if (namesKey(t)) site(n, "a for target");
    if ((ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) && (n.operator === ts.SyntaxKind.PlusPlusToken || n.operator === ts.SyntaxKind.MinusMinusToken) && namesKey(n.operand)) site(n, "an increment");
    if (ts.isDeleteExpression(n) && namesKey(n.expression)) site(n, "a delete");
    if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && ts.isIdentifier(n.expression.expression)) {
      const callee = n.expression.expression.text + "." + n.expression.name.text, k = n.arguments[1];
      if (["Object.defineProperty", "Reflect.set", "Reflect.defineProperty", "Reflect.deleteProperty"].includes(callee) && k && ts.isStringLiteralLike(k) && k.text === KEY) site(n, callee);
    }
    if (ts.isObjectLiteralExpression(n)) {
      const t = memberNamed(n, "type");
      if (t && ts.isPropertyAssignment(t) && ts.isStringLiteralLike(t.initializer) && t.initializer.text === "clientDiag") { c.posts++; const d = memberNamed(n, "data"); if (d && ts.isPropertyAssignment(d)) dataOf(d.initializer); else c.opaque++; }
    }
    if (module === "ui/webview/render.ts" && ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === "scrollDiagRow") dataOf(n.arguments[1]);
    ts.forEachChild(n, go);
  };
  go(sf);
}

test("every module the page bundles load, read with the compiler: the only write of a `view` property onto an object that reaches a clientDiag post is spacerRow's shorthand under a spread of a literal conditioned on equality with the one word, and every other write of a `view` property in the modules is enumerated with the object it writes and why no post reads it (the maintainer's round 5 ruling, tests-1; the population derived from what the bundles load and tied to the directory by equality both ways, the maintainer's round 6 ruling, correctness-1 and extra8-2; the owner 2026-09-21, who approved the field)", async () => {
  // WHAT IS READ: every module the page bundles LOAD, derived from esbuild's metafile of the shipped `webview` config built in memory
  // (bundledModules above), each parsed with the compiler, as the hover-class ownership census parses render.ts's bundle
  // (compact-seam-exec.test.ts) and the censuses above parse render.ts. The metafile, and not a directory listing or the compiler's file list
  // under vscode-extension/tsconfig.json: it is literally the import closure the pages run, recursive by construction and of every suffix,
  // PARTITIONED (never filtered) into modules, every suffix the compiler parses (`.ts`, `.mts`, `.cts`, `.tsx`, `.js`, `.mjs`, `.cjs`,
  // `.jsx`; a .tsx or .jsx parsed under its own ScriptKind), and styles (the `.css` inputs), the remainder asserted empty naming any other
  // suffix (the maintainer's round 7 ruling, extra7-1), so it reaches the two `.js` modules in ui/webview and the five modules outside it named
  // below, which tsconfig's file list (no allowJs; the test helpers under ui/ included) misses, and it leaves out the seven modules in the
  // directory no page loads, which a listing counts. The directory is read too, recursively and through the same partition (the anchor map's
  // fixture directory first, then tests and types, modules and styles, the remainder asserted empty), and the two are tied by EQUALITY both ways,
  // never a floor: the directory's modules no page bundle loads are exactly the seven named below (reached from tests, from one another and
  // from the viewer bench under tools/, never from a page entry), and the loaded modules outside the directory are exactly the five named
  // below (the timeline panel's prebuilt bundle and four vendored track-changents modules, display.js reached from track-logic.js through
  // the vendored package's own exports map), so a module that starts or stops being loaded, appears outside the directory or leaves it, is
  // named here or reds, and a module in the directory that a page bundle loads but the listing's partition files under the anchor map's
  // fixtures or under tests and types (a module-suffix file under the fixture directory, a test of any module suffix, a `.d.ts`) reds too.
  // The walk is the loaded set: a module no page runs mints nothing the kernel receives. The tests are excluded because a test's literal is
  // not a minter the page runs (the bundles are built from the production modules alone), and because this census's own reverse plants and
  // the fixture rows in this file would red it.
  // WHAT IS KEYED ON: the PROPERTY NAME `view` written onto an object, in every form the field census above reads (writeSites) and two
  // of a class's: a literal's member of any kind (a property, a shorthand, a method, an accessor) under an identifier, a string or a computed
  // string-literal name, a spread of a literal read through its literal; an assignment of any operator whose target names the property at
  // its end (`row.view = x`, `row["view"] = x`) or a destructuring pattern that does; a for-of or for-in target; ++/--; delete;
  // Object.defineProperty, Reflect.set, Reflect.defineProperty and Reflect.deleteProperty with the literal key (Object.assign's and
  // Object.defineProperties' literal sources are literals, read by the first form); a class field and a constructor's parameter property
  // named `view`. Not the string "view" as a VALUE (tailMutRow's `where: "view"` names where a tail mutation happened), not a parameter, a
  // type member or a variable so named. Outside by construction, as for the field census: a computed key of a non-literal expression, a
  // non-literal spread or source, a call through an alias of Object or Reflect; and a fourth class, a `view` key built from a string VALUE
  // (Object.fromEntries over a literal pair list, JSON.parse of a literal) inside a post's data, which the tree cannot name as a property
  // write at all: it is in neither the diag population nor the closed multiset; as the post's data itself it raises the opaque count below,
  // and returned by a builder the data calls it is filed under the builder and counted nowhere; either way it is held by the kernel's value
  // bound alone (CLIENT_DIAG_VALUES refuses every word but the one: tests/test_client_diag_allowlist.py); the witness cell after this one
  // runs those shapes through the same walker and asserts none is named, so this sentence cannot outlive the behaviour
  // (the maintainer's round 6 ruling, extra8-3). WHAT REACHES A POST, from every module's tree: the clientDiag posts (an object literal
  // with `type: "clientDiag"`, its `data` member a literal, read directly, or a call of a named function, a builder) and scrollDiagRow's calls in
  // render.ts (its data argument's literals and the named functions it calls, through a conditional, a parenthesis or an Object.assign); a
  // write is in the diag population when its owner is a builder or it lies inside a post's or a call's data literal. Every write in the
  // modules is then a closed multiset by (module, owner, form), the module its repo-relative path so a module outside ui/webview cannot
  // collide with one inside by its bare name: the diag population holds exactly spacerRow's, and each other member is named below with the
  // object it writes and why no post reads it, so a `view` written on any other row kind, by any form the tree reads, in any module a page
  // loads, is named or reds.
  const loaded = await bundledModules();
  const loadedSet = new Set(loaded);
  // the directory's listing through the same partition, the classes tried in this order: the anchor map's fixture directory first (a file
  // under it is a fixture whatever its suffix: a module-suffix file there is not a module and its stylesheet is not a page stylesheet), then
  // tests and types (a `.test.ts` is a module by suffix and is not listed), then modules, then styles; a file in none of the four reds naming
  // its suffix. The fixture directory came after modules before the maintainer's round 8 ruling (correctness-1), which filed a `.ts` under it
  // as an unloaded module.
  const parts = partition(filesUnder(path.resolve(ROOT, "ui", "webview")), [["the anchor map's fixtures", FIXTURE_DIR], ["tests and types", TEST_OR_TYPES], ["modules", MODULE_SUFFIX], ["styles", STYLE_SUFFIX]], "the files under ui/webview (recursive)");
  const listed = parts.modules;
  const UNLOADED = [   // under ui/webview, loaded by no page bundle: reached from tests, from one another and from the viewer bench under tools/, never from a page entry
    "ui/webview/feed-flip.ts",                   // the feed's FLIP-pass predicate, executed by feed-flip.test.ts
    "ui/webview/file-view-outline-fixture.ts",   // the Outline's synthetic fixture, shared by file-view-outline.test.ts and its browser leg
    "ui/webview/md-wiki.ts",                     // wikilink and callout extensions to the markdown grammar, executed by md-wiki.test.ts
    "ui/webview/real-viewer-leg.ts",             // the real viewer mounted in a served page for the browser legs (*-browser.test.ts), shell-drag-leg and the bench
    "ui/webview/scroll-journal-audit.ts",        // the scroll journal's reader, executed by scroll-journal-audit.test.ts
    "ui/webview/shell-drag-leg.ts",              // the dashboard shell's pane-row drag mounted in a page of its own, for its browser leg and the bench
    "ui/webview/writer-census.ts",               // the scroll-write census over a source's tree, executed by writer-census.test.ts and landing-settle.test.ts
  ];
  const OUTSIDE = [   // loaded by a page bundle from outside ui/webview
    "ui/romp-timeline-view.js",                              // the timeline panel's prebuilt bundle, required by timeline-main.ts
    "vendor/track-changents/display.js",                     // required by track-logic.js through the vendored package's exports map
    "vendor/track-changents/engine.js",                      // imported by anchor-map.ts, editor-chunk.ts and track-decorations.ts, and required by track-cm.js through the package's exports map
    "vendor/track-changents/obsidian/src/track-cm.js",       // imported by editor-chunk.ts and track-decorations.ts
    "vendor/track-changents/obsidian/src/track-logic.js",    // imported by track-decorations.ts
  ];
  assert.deepEqual(listed.filter((m) => !loadedSet.has(m)), UNLOADED, "the modules under ui/webview (recursive; the listing's module class, every suffix the compiler parses, the anchor map's fixture directory and tests and types apart) that no page bundle loads are exactly the seven named, reached from tests, from one another and from the viewer bench under tools/ and never from a page entry: a module that stops being loaded, or a named one that starts, or leaves the directory, is named here or reds (" + listed.length + " listed, " + loaded.length + " loaded)");
  assert.deepEqual(loaded.filter((m) => !m.startsWith("ui/webview/")), OUTSIDE, "the modules a page bundle loads from outside ui/webview are exactly the five named: a sixth, or one gone from the bundles, reds here");
  const listedSet = new Set(listed);
  assert.deepEqual(loaded.filter((m) => m.startsWith("ui/webview/") && !listedSet.has(m)), [], "a module under ui/webview that a page bundle loads and the listing's partition files under the anchor map's fixtures or under tests and types (a module-suffix file under the fixture directory, a `.test.ts`, a `.test.tsx`, a `.test.js`, a `.d.ts`): the two equalities above compare the listed modules with the loaded ones, so a production import of a test module or of a fixture is named here or reds (the author's fixer pass over the pass after the maintainer's round 6, its verifier (a))");
  assert.ok(loadedSet.has("ui/webview/render.ts") && loadedSet.has("ui/webview/scroll-write.ts"), "render.ts and scroll-write.ts are among the loaded modules");
  const modules = loaded;   // the walk IS the derived set
  const c = newViewCensus();
  const kindOf = (m: string): ts.ScriptKind => /\.tsx$/.test(m) ? ts.ScriptKind.TSX : /\.jsx$/.test(m) ? ts.ScriptKind.JSX : /\.[mc]?js$/.test(m) ? ts.ScriptKind.JS : ts.ScriptKind.TS;   // an admitted .tsx or .jsx parses under its own kind: JSX under the TS kind misparses in silence (the maintainer's round 7 ruling, extra7-1)
  for (const m of modules) censusViewWrites(m, m === "ui/webview/render.ts" ? SF : ts.createSourceFile(m, fs.readFileSync(path.resolve(ROOT, m), "utf8"), ts.ScriptTarget.Latest, true, kindOf(m)), c);
  assert.ok(c.posts >= 20, "the clientDiag posts across the modules, from the trees (" + c.posts + "; " + c.opaque + " with a data the tree cannot attribute: an identifier bound elsewhere, a parameter, a key built from a string value; outside the census and held by the kernel's allowlist and value bound)");
  for (const b of ["scrollWriteRow", "spacerRow", "tailChangeRow", "tailMutRow", "unitChangeRow"]) assert.ok(c.builders.has(b), "a builder scrollDiagRow is handed, by name from render.ts's tree: " + b + " (all: " + [...c.builders].sort().join(", ") + ")");
  const diag = c.sites.filter((s) => c.builders.has(s.owner) || inDataLiteral(c, s));
  assert.deepEqual(diag.map(describeSite), ["ui/webview/scroll-write.ts spacerRow: a literal shorthand"], "one write of a `view` property reaches a post, spacerRow's shorthand; a second minter (another row kind's literal, a builder's return, an Object.assign or a Reflect.set onto a row, in any module a page loads) is named here");
  // the one mint's guard, on the tree: the shorthand's literal is the true arm of a conditional on the parameter's equality with the one
  // word, spread into the row, and the false arm spreads nothing (the builder cell above executes the guard; this is its shape)
  const m = diag[0], lit = m.node.parent;
  assert.ok(ts.isObjectLiteralExpression(lit) && ts.isConditionalExpression(lit.parent) && lit.parent.whenTrue === lit, "the shorthand's literal is the true arm of a conditional: " + lit.parent.getText(m.sf));
  let up: ts.Node = lit.parent.parent; while (ts.isParenthesizedExpression(up)) up = up.parent;   // the conditional is parenthesised under the spread
  assert.ok(ts.isSpreadAssignment(up), "…spread into the row: " + up.getText(m.sf));
  const cond = lit.parent as ts.ConditionalExpression, cc = cond.condition;
  assert.ok(ts.isBinaryExpression(cc) && cc.operatorToken.kind === ts.SyntaxKind.EqualsEqualsEqualsToken && ts.isIdentifier(cc.left) && cc.left.text === "view" && ts.isStringLiteral(cc.right) && cc.right.text === "inactive", "the spread is conditioned on `view === \"inactive\"`, the parameter's equality with the one word: " + cc.getText(m.sf));
  assert.ok(ts.isObjectLiteralExpression(cond.whenFalse) && cond.whenFalse.properties.length === 0, "…and spreads nothing otherwise");
  // every write of the property in the modules, a closed multiset by (module, owner, form), each with the object it writes and why no post
  // reads it: a new writer in any module a page loads is named here or reds (the five modules outside ui/webview hold none today)
  assert.deepEqual(c.sites.map(describeSite).sort(), [
    "ui/webview/federation.ts class FederationManager: a method",                       // the manager's reader of the tab order, a method on the class, not a row's key
    "ui/webview/file-view.ts placeFromRemembered: a literal property",                  // the viewer's Place from a remembered one (view: rendered or raw, the pane the reader was in), kept in storage, never posted
    "ui/webview/file-view.ts rememberedPlaceOf: a literal property",                    // the remembered place the viewer writes to storage
    "ui/webview/files-recent.ts asPlace: a literal property",                           // the recent-files pane's copy of a remembered place
    "ui/webview/preview.ts wirePinchZoom: a literal shorthand",                         // a pinch gesture's snapshot (the pinch-zoom view), no row
    "ui/webview/reader-place.ts placeOf: a literal shorthand",                          // the reader's place in a document (view: rendered or raw)
    "ui/webview/scroll-write.ts spacerRow: a literal shorthand",                        // THE mint: the spacer row's marker, guarded as pinned above
    "ui/webview/track-decorations.ts constructor of PointerTracker: a parameter property",   // the editor view the pointer tracker listens on
  ], "every write of a `view` property in the modules the page bundles load, by module (its repo-relative path), owner and form; one reaches a post (spacerRow's), the rest write the viewer's places, a gesture's snapshot, a class's method or field");
});

test("the fourth class the census cannot name, witnessed through its own walker: a `view` key built from a string VALUE (Object.fromEntries over a literal pair list, JSON.parse of a literal) inside a clientDiag post's data, or spread into it, or handed to scrollDiagRow, is NOT a site (in neither the diag population nor the closed multiset): as the post's data itself it raises the opaque count alone, and returned by a builder the data calls it is filed under the builder and counted nowhere; the same word as a literal property in the same post IS a site, so the shapes are what the census reads (the maintainer's round 6 ruling, extra8-3: the bound on that class is the kernel's value bound, CLIENT_DIAG_VALUES, and this cell keeps the census's sentence honest)", () => {
  // synthetic sources (no real data): the word is one the kernel refuses (tests/test_client_diag_allowlist.py drives that refusal), so a
  // page that built the key this way would post a value the kernel drops with its line, whichever module built it
  const run = (module: string, src: string): ViewCensus => { const c = newViewCensus(); censusViewWrites(module, ts.createSourceFile(module, src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS), c); return c; };
  // each shape with the opaque count it owes (1 as the post's data itself; 0 returned by a builder, where the call is filed under the
  // builder's name and the fromEntries inside its body is no property write) and the builder it is filed under, if any
  const shapes: Array<[string, string, string, number, string | null]> = [
    ["Object.fromEntries as a post's data", "ui/webview/synthetic.ts", 'export const p = { type: "clientDiag", data: Object.fromEntries([["view", "away"]]) };', 1, null],
    ["JSON.parse as a post's data", "ui/webview/synthetic.ts", 'export const p = { type: "clientDiag", data: JSON.parse(\'{"view":"away"}\') };', 1, null],
    ["Object.fromEntries spread into a post's data literal", "ui/webview/synthetic.ts", 'export const p = { type: "clientDiag", data: { ...Object.fromEntries([["view", "away"]]) } };', 1, null],
    ["Object.fromEntries as scrollDiagRow's data in render.ts", "ui/webview/render.ts", 'scrollDiagRow("spacer", Object.fromEntries([["view", "away"]]));', 1, null],
    ["Object.fromEntries returned by a builder the post's data calls", "ui/webview/synthetic.ts", 'function b() { return Object.fromEntries([["view", "away"]]); } export const p = { type: "clientDiag", data: b() };', 0, "b"],
  ];
  for (const [what, module, src, opaque, builder] of shapes) {
    const c = run(module, src);
    assert.deepEqual(c.sites.map(describeSite), [], what + ": a key built from a string value is no property write the tree can name, so the census does not name it: outside the census by construction, held by CLIENT_DIAG_VALUES alone (a walker that resolved this shape would red here, and the census's sentence would then be false)");
    assert.equal(c.opaque, opaque, what + (opaque ? ": the opaque count rises by one for the unattributable data" : ": the data is a builder's call, filed under the builder and counted nowhere, since the builder's body holds no property write the tree can name, so the opaque count stays 0 (the author's fixer pass over the pass after the maintainer's round 6, its verifier (a), which found the census's sentence claiming the count for this shape too)"));
    if (builder) assert.ok(c.builders.has(builder), what + ": the call is filed as a builder, by name: " + builder);
    assert.equal(c.posts, module === "ui/webview/render.ts" ? 0 : 1, what + ": the post is counted where there is one");
  }
  // the control: the same word as a literal property of the same post's data IS a site, inside the data literal, in the diag population
  const ctl = run("ui/webview/synthetic.ts", 'export const p = { type: "clientDiag", data: { view: "away" } };');
  assert.deepEqual(ctl.sites.map(describeSite), ["ui/webview/synthetic.ts <module>: a literal property"], "the literal property is a site, named by module, owner and form");
  assert.ok(ctl.sites.length === 1 && inDataLiteral(ctl, ctl.sites[0]), "…inside the post's data literal, so it would be in the diag population");
  assert.equal(ctl.opaque, 0, "…and nothing opaque");
});

/** The CLIENT_DIAG_VALUES table's body read by a BALANCED parse (the maintainer's round 6 ruling, extra8-1): the text tokenized over
 *  parentheses, brackets and braces and over double- and single-quoted strings (a `#` comment runs to its line's end and is dropped), split
 *  into entries at depth-0 commas; per entry the tuple before its top-level colon is read element by element, a string literal's text (any
 *  text, a hyphen included) or the label `<not a string literal>` for an element that is not one (a name, a call, a concatenation), as the
 *  surface and the key, so an entry keyed by a name is named by position and not by whichever literal follows; the string literals inside
 *  the frozenset(...) argument are its words, and `container` says what that argument opens with (a
 *  tuple, a set, a list, a single word in parentheses with no trailing comma, which Python reads as a string, or a bare string, whose
 *  frozenset is its letters too). `frozensets` counts
 *  `frozenset(` over the body with comments and string contents removed, the number of entries the parse must read. */
function parseValuesTable(body: string): { entries: Array<{ surface: string; key: string; words: string[]; container: string }>; frozensets: number } {
  const strings = (s: string): string[] => [...s.matchAll(/"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'/g)].map((m) => m[1] ?? m[2]);
  const chunks: string[] = [], colons: number[] = []; let depth = 0, cur = "", stripped = "", q: string | null = null, colon = -1;
  for (let i = 0; i < body.length; i++) {
    const ch = body[i];
    if (q) { cur += ch; if (ch === "\\" && i + 1 < body.length) cur += body[++i]; else if (ch === q) { q = null; stripped += '""'; } continue; }   // a string's contents are dropped from `stripped`
    if (ch === '"' || ch === "'") { q = ch; cur += ch; continue; }
    if (ch === "#") { while (i < body.length && body[i] !== "\n") i++; cur += "\n"; stripped += "\n"; continue; }
    stripped += ch;
    if ("([{".includes(ch)) depth++; else if (")]}".includes(ch)) depth--;
    if (depth === 0 && ch === ":" && colon < 0) colon = cur.length;
    if (depth === 0 && ch === ",") { chunks.push(cur); colons.push(colon); cur = ""; colon = -1; continue; }
    cur += ch;
  }
  if (cur.trim()) { chunks.push(cur); colons.push(colon); }
  // the key tuple's elements at its own depth-0 commas (the outer parentheses dropped): a string literal's text, or the label for any other
  // expression, so the entry `(CHAT_SURFACE, "view")` reads as <not a string literal>/view, the name's position labelled, and not as
  // view/undefined, the one literal shifted into the surface's place
  const keyParts = (k: string): string[] => {
    let t = k.trim(); if (t.startsWith("(") && t.endsWith(")")) t = t.slice(1, -1);
    const parts: string[] = []; let d = 0, cur = "", qq: string | null = null;
    for (let i = 0; i < t.length; i++) {
      const c = t[i];
      if (qq) { cur += c; if (c === "\\" && i + 1 < t.length) cur += t[++i]; else if (c === qq) qq = null; continue; }
      if (c === '"' || c === "'") qq = c; else if ("([{".includes(c)) d++; else if (")]}".includes(c)) d--;
      if (d === 0 && c === ",") { parts.push(cur); cur = ""; continue; }
      cur += c;
    }
    if (cur.trim()) parts.push(cur);
    return parts.map((x) => /^\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')\s*$/.test(x) ? strings(x)[0] : "<not a string literal>");
  };
  const entries = chunks.map((e, i) => {
    const at = colons[i];
    assert.ok(at >= 0, "an entry of the table has a top-level colon: " + e.trim());
    const [surface = "<missing>", key = "<missing>"] = keyParts(e.slice(0, at));
    const value = e.slice(at + 1), m = /frozenset\s*\(/.exec(value);
    assert.ok(m, "an entry's value is a frozenset(...): " + e.trim());
    const argStart = m!.index + m![0].length;
    let d = 1, j = argStart, qq: string | null = null;   // the argument runs to the frozenset call's own closing parenthesis
    for (; j < value.length && d > 0; j++) { const c = value[j]; if (qq) { if (c === "\\") j++; else if (c === qq) qq = null; } else if (c === '"' || c === "'") qq = c; else if ("([{".includes(c)) d++; else if (")]}".includes(c)) d--; }
    const arg = value.slice(argStart, j - 1).trim(), words = strings(arg);
    const container = arg.startsWith("(") ? (words.length > 1 || /,\s*\)$/.test(arg) ? "a tuple" : "a single word in parentheses with no trailing comma (a string to Python; frozenset of a string is its letters)") : arg.startsWith("{") ? "a set" : arg.startsWith("[") ? "a list" : /^["']/.test(arg) ? "a bare string (a string to Python; frozenset of a string is its letters)" : "another expression";
    return { surface, key, words, container };
  });
  return { entries, frozensets: (stripped.match(/frozenset\s*\(/g) || []).length };
}

test("the page's guard literal is a member of the set the kernel admits for the marker, both read from their sources: kernel.py states the set once (CLIENT_DIAG_VALUES, one entry, chat's `view`, one word) and scroll-write.ts's spacerRow compares its `view` parameter with that word and types the parameter by it, so a change to either side alone reds here (the author's fixer pass over the pass after the maintainer's round 5, its verifier (b): until then the tie between the page's spelling and the kernel's set was two hand-written literals, the allowlist module's fixture row and the census's guard pin above)", () => {
  // WHAT IS READ: kernel.py's CLIENT_DIAG_VALUES table literal, by text (every `(surface, key): frozenset((words,))` entry between its
  // braces, the way the webview tests that read kernel.py read it), and scroll-write.ts's tree (the string literal spacerRow's guard
  // compares `view` with, and the parameter's literal type). Neither word is spelled here: the kernel's set is the one statement.
  const kernel = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");
  const table = /^CLIENT_DIAG_VALUES = \{\n([\s\S]*?)^\}/m.exec(kernel);
  assert.ok(table, "kernel.py states CLIENT_DIAG_VALUES as a table literal");
  const entries = [...table![1].matchAll(/^\s*\("(\w+)", "(\w+)"\): frozenset\(\(((?:\s*"[^"]*",)+)\s*\)\),/gm)].map((m) => ({ surface: m[1], key: m[2], words: [...m[3].matchAll(/"([^"]*)"/g)].map((x) => x[1]) }));
  // the same body read by the BALANCED parse beside the regex (the maintainer's round 6 ruling, extra8-1: a one-spelling regex over a table
  // that bounds a privacy value is a silent shape). The regex is kept as the strict form the table is written in (a `\w+` surface and key, a
  // tuple of double-quoted words each followed by a comma); the parse reads any spelling (parseValuesTable above), its entry count is the
  // count of `frozenset(` in the body, and the two reads must agree entry for entry, so an entry the regex cannot read (a hyphenated surface
  // or key, a surface or key that is not a string literal, named by position, a set or list literal, a single word in parentheses with no
  // trailing comma) is a red here NAMING the entry, never a silent miss
  // that leaves the one-entry assertion below green. tests/test_client_diag_allowlist.py reads the runtime object and reds on a second entry
  // whatever its spelling (its sorted-keys equality), on a value that is not a frozenset (its assertIsInstance) and on a frozenset of a bare
  // string, whose members are the string's letters, by its one-word length assertion; the spelling of a frozenset's argument (a tuple, a
  // list, a set) is the same runtime object and reds nowhere in Python, which is why this cell reads the text.
  const balanced = parseValuesTable(table![1]);
  assert.equal(balanced.entries.length, balanced.frozensets, "the balanced parse reads one entry per frozenset( in the table's body: " + JSON.stringify(balanced.entries));
  const entryName = (e: { surface: string; key: string }): string => e.surface + "/" + e.key;
  for (const nm of [...new Set([...entries.map(entryName), ...balanced.entries.map(entryName)])]) {
    const r = entries.find((e) => entryName(e) === nm), p = balanced.entries.find((e) => entryName(e) === nm);
    assert.ok(r && p, "the regex and the balanced parse disagree on the entry " + nm + ": the regex read " + (r ? JSON.stringify(r.words) : "nothing") + ", the parse read " + (p ? JSON.stringify(p.words) + " in " + p.container : "nothing") + " (a spelling one read cannot see: a hyphenated surface or key, a surface or key that is not a string literal, a set or list literal, a tuple with no trailing comma, a bare string)");
    assert.deepEqual(r!.words, p!.words, "the entry " + nm + ": the two reads agree on its words (" + p!.container + ")");
  }
  assert.deepEqual(entries.map((e) => e.surface + "/" + e.key), ["chat/view"], "one bounded key, chat's `view` (every entry of the table is read: a second is named here)");
  const words = entries[0].words;
  assert.equal(words.length, 1, "one fixed word, no host name (the owner 2026-09-21, who approved the field): " + JSON.stringify(words));
  const sw = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "scroll-write.ts"), "utf8");
  const swf = ts.createSourceFile("scroll-write.ts", sw, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const fn = swf.statements.find((st): st is ts.FunctionDeclaration => ts.isFunctionDeclaration(st) && st.name?.text === "spacerRow");
  assert.ok(fn && fn.body, "spacerRow is a function declaration in scroll-write.ts");
  const compared: string[] = [];
  const walk = (n: ts.Node): void => { if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsEqualsEqualsToken && ts.isIdentifier(n.left) && n.left.text === "view" && ts.isStringLiteral(n.right)) compared.push(n.right.text); ts.forEachChild(n, walk); };
  walk(fn!.body!);
  assert.deepEqual(compared, words, "spacerRow's guard compares `view` with the kernel's one word and with no other literal: the page's spelling, off the tree, against the kernel's set, off kernel.py");
  const p = fn!.parameters.find((q) => ts.isIdentifier(q.name) && q.name.text === "view");
  assert.ok(p && p.type && ts.isLiteralTypeNode(p.type) && ts.isStringLiteral(p.type.literal) && p.type.literal.text === words[0], "the parameter's type is the literal type of that word: " + (p && p.type ? p.type.getText(swf) : "<no view parameter>"));
});

test("the reload restore's raw write of the persisted rs.top, on the tree: from the record's binding (wider than the window ruled, which runs from the site's own read of `rs.top` to the write, one expression today, so strictly stronger, the maintainer's round 4 ruling on ordering-3; the persisted top's first read is earlier, in landActive's `saved` computation, where takeReloadScroll admits the record to decide the take) to the write, in landActive's statements, no taker is called and no field of the take state (`measured`, `avgTurnH`, `pxPerTurn`: the fields the take and the untake assign and the parked figures are read from, derived from render.ts and stated once at module level) is written, in any form the tree can name. The site needs no take-back because its value was measured in the state it lands in (the take before it re-derives the pre-reload page's figures), not because the site is special, and that holds only while this window stays closed. The takers are half derived and half listed: DERIVED, every function that writes a take-state field, by owner from the tree in every form it can name (writesOf), and the closure over render.ts's named functions of everything that calls a taker, to a fixpoint; LISTED, the seed set of the two spacer redraws (SPACER_REDRAWS: sizeSpacers, redrawGapUnits), each checked to name a function declaration in render.ts; so a take through a helper the site calls is named here, a redraw under a new name is a taker only once it is listed or called by one, and a take through a callee the tree cannot name is caught by land-active-keep.test.ts's trace (the reviewer's answer to the author's tail-2 question, 2026-09-21). This half keys on taker CALLS by name and on take-state WRITES in the forms the tree can name, and on nothing else: a geometry change in the window (a height written on a row or the view element, a child inserted, moved or removed, a query the model does not resolve) is not visible to it and is held by land-active-keep.test.ts's model, which records it on the trace and fails closed on what it cannot represent (the maintainer's round 4 ruling, closure-6, keyed there because geometry is observable by execution and not on the tree). The site's binding is pinned too: `rs` is a const bound once from takeReloadScroll, assigned nowhere in landActive in any form the census names, and takeReloadScroll is called exactly twice in landActive (the saved computation's call and the binding's), so the record cannot be rebound to a later admission on the tree, as land-active-keep.test.ts counts the admissions on the trace (the closing lens over the author's fixer pass over pass 5: a site that re-admitted the record into its own binding after a change moved the window's start past it with both halves green)", () => {
  const sf = SF;
  const line = (n: ts.Node): number => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const fnNamed = (name: string): ts.FunctionDeclaration | undefined => sf.statements.find((st): st is ts.FunctionDeclaration => ts.isFunctionDeclaration(st) && st.name?.text === name);
  // the take state, derived from render.ts: every field of the view parameter the take (applyMeasure) and the untake (untakeMeasure) write,
  // in every form the census names (fieldsWrittenOn), and every field of it the parked figures are read from (figuresBefore, fieldsReadOn);
  // asserted equal to the set stated once at module level (TAKE_STATE), so a field the take grows into, through a cast, a delete, a pattern or
  // an Object.assign as much as by a bare assignment, reds here and is added there, and to land-active-keep.test.ts's world, which traces a
  // write of each. The parameter is read from each declaration, not assumed to be spelled `v`.
  const viewFields = (name: string, written: boolean): string[] => {
    const fn = fnNamed(name); assert.ok(fn && fn.body, name + " is a function declaration at module level");
    const p = fn!.parameters[0]; assert.ok(p && ts.isIdentifier(p.name), name + " takes the view as its first parameter");
    const param = (p!.name as ts.Identifier).text;
    return [...(written ? fieldsWrittenOn(param, fn!.body!) : fieldsReadOn(param, fn!.body!))];
  };
  assert.deepEqual([...new Set([...viewFields("applyMeasure", true), ...viewFields("untakeMeasure", true), ...viewFields("figuresBefore", false)])].sort(), [...TAKE_STATE].sort(),
    "the take state derived from render.ts (the fields of the view the take and the untake write, in every form the census names, and the parked figures are read from, through a cast or a parenthesis, or through a binding or an assignment pattern, too) is the set stated once at module level; a field the take grows into, in any of those forms, is added there and traced in land-active-keep.test.ts's world (outside this derivation, as they are outside the census: a computed key of any expression but a string literal, a non-literal source or map, and a read or a write through an alias of the parameter)");
  // the takers: DERIVED, every function that writes a take-state field in any form the tree can name (writesOf), by owner; LISTED, the two
  // spacer redraws, each checked to name a function declaration (a misspelled seed would be a dead seed and an open window); then the closure
  // over render.ts's named functions of everything that calls a taker, to a fixpoint
  const writers = writesOf(TAKE_STATE, sf);
  const setters = new Set(writers.map((w) => w.owner));
  const SPACER_REDRAWS = ["sizeSpacers", "redrawGapUnits"];
  for (const s of SPACER_REDRAWS) assert.ok(fnNamed(s), s + ": a listed seed names a function declaration in render.ts (a rename here would leave a dead seed and the window open to the redraw)");
  const callsIn = new Map<string, Set<string>>();
  const walk = (n: ts.Node): void => {
    if (ts.isCallExpression(n) && ts.isIdentifier(n.expression)) { const o = ownerOf(n); if (!callsIn.has(o)) callsIn.set(o, new Set()); callsIn.get(o)!.add(n.expression.text); }
    ts.forEachChild(n, walk);
  };
  walk(sf);
  const takers = new Set<string>([...setters, ...SPACER_REDRAWS]);
  for (let grew = true; grew;) { grew = false; for (const [fn, callees] of callsIn) if (fn !== "<module>" && !takers.has(fn) && [...callees].some((c) => takers.has(c))) { takers.add(fn); grew = true; } }
  // the site: landActive's raw reload-restore write (the follow-mode shape writes the bottom with stick and is not it) and the binding of
  // `rs`, the record whose top it writes; the window is the statements from the binding to the write, inclusive, less the write call itself,
  // so a take on a branch the raw write's path does not run (the follow-mode write's) reds here too: the trace half is exact about the path
  // and this half names the site
  const landFn = fnNamed("landActive");
  assert.ok(landFn && landFn.body, "landActive is a function declaration at module level");
  const reads: ts.PropertyAccessExpression[] = [], calls: ts.CallExpression[] = [], bindings: ts.VariableDeclaration[] = [];
  const scan = (n: ts.Node): void => {
    if (ts.isPropertyAccessExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === "rs" && n.name.text === "top") reads.push(n);
    if (ts.isCallExpression(n) && ts.isIdentifier(n.expression)) calls.push(n);
    if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.name.text === "rs" && n.initializer && ts.isCallExpression(n.initializer) && ts.isIdentifier(n.initializer.expression) && n.initializer.expression.text === "takeReloadScroll") bindings.push(n);
    ts.forEachChild(n, scan);
  };
  scan(landFn!.body!);
  const stateWrites = writesOf(TAKE_STATE, landFn!.body!);
  const rawWrites = calls.filter((c) => (c.expression as ts.Identifier).text === "writeScroll" && c.arguments[2] && ts.isStringLiteral(c.arguments[2]) && c.arguments[2].text === "reload-restore" && !(c.arguments[3] && c.arguments[3].kind === ts.SyntaxKind.TrueKeyword));
  assert.equal(rawWrites.length, 1, "one raw reload-restore write in landActive: " + rawWrites.map((c) => c.getText(sf) + " at line " + line(c)).join("; "));
  assert.equal(bindings.length, 1, "one binding of rs from takeReloadScroll in landActive: " + bindings.map((b) => b.getText(sf) + " at line " + line(b)).join("; "));
  // the binding cannot be rebound (the closing lens over the author's fixer pass over pass 5): a const, assigned nowhere in landActive in any
  // form the census names, and the record admitted by exactly two calls, so a site that admits the record again after a take or a geometry
  // change and rebinds its value to the later record has no shape on the tree; land-active-keep.test.ts counts the admissions on the trace
  assert.ok((ts.getCombinedNodeFlags(bindings[0]) & ts.NodeFlags.Const) !== 0, "rs is a const (line " + line(bindings[0]) + "): a let would let the site rebind the record after a take or a geometry change, and the window, which follows the record whose top the write reads, would move its start with it");
  const rsAssigns = writeSites(landFn!.body!).filter((s) => !ts.isCallExpression(s.node) && s.targets.some((t) => { const b = bare(t); return ts.isIdentifier(b) && b.text === "rs"; })).map((s) => s.node.getText(sf) + " at line " + line(s.at));
  assert.deepEqual(rsAssigns, [], "nothing in landActive assigns rs after its binding, in any form the census names (an assignment operator, a destructuring pattern, a for-of or for-in head, an increment, a delete): the window's start is the binding's record and nothing moves it");
  const admissions = calls.filter((c) => (c.expression as ts.Identifier).text === "takeReloadScroll");
  assert.equal(admissions.length, 2, "takeReloadScroll is called exactly twice in landActive, in the saved computation (to decide the take) and at the binding of rs (for the restore); a third call admits the record again: " + admissions.map((c) => c.getText(sf) + " at line " + line(c)).join("; "));
  assert.ok(reads.length >= 1, "landActive reads rs.top");
  const write = rawWrites[0], read = reads.sort((a, b) => a.getStart(sf) - b.getStart(sf))[0];
  const stmtOf = (n: ts.Node): ts.Statement => { let p: ts.Node = n; while (!(ts.isStatement(p) && !ts.isBlock(p))) { assert.ok(p.parent, "a statement encloses the node"); p = p.parent; } return p as ts.Statement; };
  const sB = stmtOf(bindings[0]), sW = stmtOf(write);
  assert.ok(sB.getEnd() <= sW.getStart(sf), "the binding's statement comes before the write's (line " + line(sB) + " against line " + line(sW) + ")");
  const lo = sB.getStart(sf), hi = sW.getEnd();
  const within = (n: ts.Node): boolean => n.getStart(sf) >= lo && n.getEnd() <= hi;
  assert.ok(within(read) && read.getEnd() <= write.getEnd(), "the site's read of rs.top (line " + line(read) + ") lies in the window, no later than the write");
  const between = [
    ...calls.filter((c) => c !== write && within(c) && takers.has((c.expression as ts.Identifier).text)).map((c) => c.getText(sf) + " at line " + line(c) + " (a taker: it writes the take state or re-draws the spacers, or calls something that does)"),
    ...stateWrites.filter((w) => within(w.at)).map((w) => w.node.getText(sf) + " at line " + line(w.at) + " (a write of the take state: " + w.field + ")"),   // placed at the write (a for-of's target), not the form's span
  ];
  assert.deepEqual(between, [], "the reload restore's raw write: the window from the record's binding (line " + line(sB) + ") to the write (line " + line(write) + ") holds a take, so the persisted top, measured in the layout the take before it re-derives, would land in a layout it was not measured in; the site needs no take-back only while this window stays closed (this check keys on taker calls by name and take-state writes in the forms the tree can name; a geometry change in the window is held by land-active-keep.test.ts's model, which records it and fails closed)");
  // the derivation the window check rests on, pinned after it so a plant in the window is named by the window's message
  assert.deepEqual([...setters].sort(), ["applyMeasure", "forgetAverage", "measureUnits", "untakeMeasure"], "the take state's writers, by owner from the tree, of any of its three fields in any form the tree can name (writesOf): the take, the reset, the park and the untake; a fifth is a new writer of the take state and belongs with the censuses above (outside this census by construction, the tree reading spellings and resolving no binding: a write through a computed key of any expression but a string literal or a non-literal Object.assign source or defineProperties map, a call through an alias of the callee, a write through an alias of the parked object; inside the ordering window every form but the alias of the parked object reaches land-active-keep.test.ts's accessors at run time, and by an owner outside the span that test lifts they are outside both halves, a residual the body names)");
  assert.ok(takers.has("landActive") && takers.has("renderWindowItems") && takers.has("scrollToAnchor") && takers.has("syncViewInner"), "the closure reaches the takers one and two hops out (the walk is not empty): " + [...takers].sort().join(", "));
});
