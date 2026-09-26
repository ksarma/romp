// A census of the request primitives the dashboard's pages use, so a new kind of request is judged when it is written
// rather than found at run time.
//
// Every request a kernel page makes to its kernel authenticates by one of three roads: a page document or a static
// bundle rides the session cookie alone; a fetch carries the page key as X-Romp-Key (the kernel's fetch wrapper, first in
// every page's head); a socket dial carries it as k= (window.__rompKeyQ); a header-less /file load carries a per-file cap
// (file-cap.ts). A request made any other way (an XMLHttpRequest, an EventSource, a sendBeacon, a fetchLater, a
// WebTransport, a form POST, an <object> or <embed> of a kernel route, a fetch from a worker, where the wrapper does not
// run, or a socket dialed without the key) carries none of them and is refused with a 403 that nothing flags at test
// time. A service worker is a worker context too: the page-key script does not run there, so its fetches carry no key,
// and a registration is a site like a Worker. So this census reads every such primitive in the non-test sources under ui/
// (with the TypeScript compiler's parser, so comments and strings are what the language says they are) and in
// kernel/kernel.py, where the inline pages live as Python strings, and holds each against the list below at the number
// of times the tree holds it. A new site, or a second primitive inside a listed function, is red until it is listed with
// the road it takes, and a listed site that went away is stale.
//
// What counts as a site under ui/: a construction (`new WebSocket(...)`, `new Worker(...)`), whether its callee is a
// name, a member (`new window.WebSocket(...)`), a string key (`new (globalThis as any)["WebSocket"](...)`) or any of
// those in parentheses or under a type or non-null assertion; a read of a member that makes a request
// (`navigator.sendBeacon(...)`, `form.requestSubmit()`, `x.submit()`, `navigator.serviceWorker`), by name, by a string
// key (`navigator["sendBeacon"]`) or by destructuring (`const { serviceWorker } = navigator`), where a bare local of the
// same name (a `submit` handler) is not one; a value reference to a primitive that is none of those nor a feature test
// (`typeof WebSocket`) nor a constant read (`WebSocket.OPEN`), since an alias passes the primitive around under another
// name; a string literal holding markup for a form, an object or an embed, or naming a primitive, which is how script for
// some other document to run (a frame's srcdoc) is written; and a form, an object or an embed made by createElement, by
// createElementNS, or by a helper whose parameter reaches either (the pages' el(tag, cls) helpers, found to a fixed point
// and matched by name, so el("form") reads like createElement("form")). A type annotation is not a site.
//
// The kernel's inline pages are read as text, pattern by pattern, over kernel.py, where a quote inside a page's script
// may be written escaped in its Python literal. The names a pattern cannot follow (an alias of WebSocket or Worker,
// either read as a member or by a string key, a registration or a submit reached through an alias, createElement read by
// a string key) are counted over every str constant of kernel.py that is not a docstring, read with Python's own parser
// so that comments and docstrings are not counted. That population is wider than the inline scripts, which are Python
// string constants like any other: nothing in the parse tells a string of JavaScript from a string of Python, so the
// scripts alone cannot be derived. The wider read errs on one side only. A Python string that names one of these names
// raises its count, a false red that its wording or the list settles, and no script is left out, so it gives no false
// green. That read runs python3, as the kernel does, and a machine where it cannot is red, not skipped.
//
// Stated limits, on the precondition that the sources are written in good faith: a primitive reached through a name
// assembled at run time (`window["Web" + "Socket"]`) or through a value that never names it (a socket's own
// `constructor`); an element whose tag is computed at run time, or reaches createElement other than as a helper's own
// parameter (a property of an options object); and createElement reached through an alias of itself
// (`document.createElement.bind(document)`). None of these is read. Each is a witness in the shapes tests below (the
// "stated limit" cases), which pin that the census does not see it, so a change that widens or closes one shows there.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import * as ts from "typescript";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI_ROOT = path.resolve(EXT, "..", "ui");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");

/** The globals that make a request, read wherever the name is used as a value; and the methods that do, read as a member
 *  (`navigator.sendBeacon`, `form.submit()`, `navigator.serviceWorker`), where a bare local of the same name (a `submit`
 *  handler) is not one. */
const GLOBALS = new Set(["XMLHttpRequest", "EventSource", "WebSocket", "Worker", "SharedWorker", "importScripts", "fetchLater", "WebTransport"]);
const METHODS = new Set(["sendBeacon", "requestSubmit", "submit", "serviceWorker", ...GLOBALS]);
const MARKUP = /<\s*(form|object|embed)\b/i;
/** A primitive named in a string, as script for some other document to run. */
const SCRIPT_TEXT = /(?<![\w$-])(XMLHttpRequest|EventSource|WebSocket|SharedWorker|Worker|importScripts|fetchLater|WebTransport|sendBeacon|serviceWorker|requestSubmit)|\.\s*(submit)\s*\(/;
const ELEMENTS = new Set(["form", "object", "embed"]);

/** Every site under ui/ by `file:function:primitive:how`, with the number of times the tree holds it and the road it
 *  takes to the kernel. */
const UI_SITES: Record<string, { count: number; road: string }> = {
  "webview/federation.ts:connect:WebSocket:new": { count: 1, road:
    "the relay dial to /remote/<host>/ws: its URL is the one remoteDialUrl returned, which appends __rompKeyQ() (checked below)" },
  "webview/pdf-chunk.ts:ownWorker:Worker:value": { count: 1, road:
    "the default Worker constructor handed to ownWorker (a test injects a stand-in); see the construction below" },
  "webview/pdf-chunk.ts:ownWorker:WorkerCtor:new": { count: 1, road:
    "pdf.js's module Worker, loaded from /dist/pdf-worker.js (the static class, on the cookie); getDocument is handed the " +
    "PDF's bytes, which the page fetched through the wrapper, so the worker fetches nothing from the kernel" },
};

/** The functions a listed socket dial's URL comes from, each of which must append the page key. */
const DIAL_BUILDERS: Record<string, string> = { "webview/federation.ts:connect": "remoteDialUrl" };

function sources(): string[] {
  const out: string[] = [];
  const walk = (dir: string) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { if (e.name !== "node_modules") walk(p); continue; }
      if (/\.(ts|js|mjs)$/.test(e.name) && !/\.test\.(ts|js|mjs)$/.test(e.name) && !/\.d\.ts$/.test(e.name)) out.push(p);
    }
  };
  walk(UI_ROOT);
  return out.map((p) => path.relative(UI_ROOT, p).split(path.sep).join("/")).sort();
}

const nameOf = (fn: ts.Node): string | null => {
  if ((ts.isFunctionDeclaration(fn) || ts.isMethodDeclaration(fn)) && fn.name) return fn.name.getText();
  const p = fn.parent;
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
  if (p && (ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p))) return p.name.getText();
  return null;
};
function holder(n: ts.Node): string {
  for (let x = n.parent; x; x = x.parent) if (ts.isFunctionLike(x)) { const nm = nameOf(x); if (nm) return nm; }
  return "<module>";
}
const inType = (n: ts.Node): boolean => { for (let x = n.parent; x; x = x.parent) { if (ts.isTypeNode(x)) return true; if (ts.isExpression(x) || ts.isStatement(x)) return false; } return false; };

const isWrapper = (n: ts.Node): n is ts.ParenthesizedExpression | ts.AsExpression | ts.TypeAssertion | ts.NonNullExpression | ts.SatisfiesExpression =>
  ts.isParenthesizedExpression(n) || ts.isAsExpression(n) || ts.isTypeAssertionExpression(n) || ts.isNonNullExpression(n) || ts.isSatisfiesExpression(n);
/** The expression under any parentheses, type assertion or non-null assertion, which is what ts.skipOuterExpressions
 *  returns (that function is not in the compiler's public typings): `new (globalThis as any)["WebSocket"](u)` names its
 *  callee through it. */
function bare(e: ts.Expression): ts.Expression { while (isWrapper(e)) e = e.expression; return e; }
/** The outermost such wrapper around an expression, so a caller can ask what the expression is the operand of. */
function outermost(n: ts.Node): ts.Node { let x = n; while (x.parent && isWrapper(x.parent)) x = x.parent; return x; }
/** The text of a string key: a string literal or a template with no substitution. */
const keyText = (e: ts.Node | undefined): string | null => {
  if (!e) return null;
  const b = ts.isExpression(e) ? bare(e) : e;
  return ts.isStringLiteral(b) || ts.isNoSubstitutionTemplateLiteral(b) ? b.text : null;
};
/** The name a member access reads: `x.name`, or `x["name"]` with a string key. */
const memberName = (e: ts.Node): string | null =>
  ts.isPropertyAccessExpression(e) ? e.name.text : ts.isElementAccessExpression(e) ? keyText(e.argumentExpression) : null;
/** The name a callee goes by: an identifier's, or the member it reads, under any wrapper. */
const calleeName = (e: ts.Expression): string | null => { const b = bare(e); return ts.isIdentifier(b) ? b.text : memberName(b); };
/** The key a destructuring element reads: `{ serviceWorker }`, `{ serviceWorker: c }`, `{ "serviceWorker": c }`. */
const bindingKey = (b: ts.BindingElement): string | null => {
  const k = b.propertyName;
  if (!k) return ts.isIdentifier(b.name) ? b.name.text : null;
  if (ts.isComputedPropertyName(k)) return keyText(k.expression);
  return ts.isIdentifier(k) || ts.isStringLiteral(k) ? k.text : null;
};
/** Is this string the key of a member read or a destructuring element (read there, as the member it names)? */
const isKey = (n: ts.Node): boolean => {
  const w = outermost(n), p = w.parent;
  return (ts.isElementAccessExpression(p) && p.argumentExpression === w) || (ts.isBindingElement(p) && p.propertyName === w)
    || (ts.isComputedPropertyName(p) && ts.isBindingElement(p.parent));
};
/** The name a function goes by for the element-making helpers: its declared name, or the member it is assigned to
 *  (`P.createEl = function (tag, o) {...}`). */
const makerName = (f: ts.Node): string | null => {
  const nm = nameOf(f);
  if (nm) return nm;
  const w = outermost(f), p = w.parent;
  if (p && ts.isBinaryExpression(p) && p.right === w && p.operatorToken.kind === ts.SyntaxKind.EqualsToken)
    return ts.isIdentifier(bare(p.left)) ? (bare(p.left) as ts.Identifier).text : memberName(bare(p.left));
  return null;
};

/** Where a call names the element it makes, by the callee's name and the argument's place: createElement's first,
 *  createElementNS's second, and each helper's parameter that reaches one of those, to a fixed point (a helper of a
 *  helper is one too). */
function elementMakers(sfs: ts.SourceFile[]): Map<string, Set<number>> {
  const makers = new Map<string, Set<number>>([["createElement", new Set([0])], ["createElementNS", new Set([1])]]);
  for (let grew = true; grew;) {
    grew = false;
    const visit = (n: ts.Node): void => {
      const at = ts.isCallExpression(n) ? makers.get(calleeName(n.expression) || "") : undefined;
      if (at && ts.isCallExpression(n)) {
        for (const i of at) {
          const a = n.arguments[i] ? bare(n.arguments[i]) : null;
          if (!a || !ts.isIdentifier(a)) continue;
          for (let f: ts.Node | undefined = n.parent; f; f = f.parent) {
            if (!ts.isFunctionLike(f)) continue;
            const idx = f.parameters.findIndex((p) => ts.isIdentifier(p.name) && p.name.text === a.text);
            if (idx < 0) continue;                                  // a closure over an outer function's parameter
            const nm = makerName(f);
            if (nm) { const s = makers.get(nm) || new Set<number>(); if (!s.has(idx)) { s.add(idx); makers.set(nm, s); grew = true; } }
            break;
          }
        }
      }
      ts.forEachChild(n, visit);
    };
    for (const sf of sfs) visit(sf);
  }
  return makers;
}

type Census = { sites: Map<string, number>; fns: Map<string, { node: ts.Node; sf: ts.SourceFile }> };
/** The census of a set of sources, `[rel, text]`: every site by `file:function:primitive:how` with the times it occurs,
 *  and every named function (for the dial check). */
function censusOf(files: [string, string][]): Census {
  const sites = new Map<string, number>(), fns = new Map<string, { node: ts.Node; sf: ts.SourceFile }>();
  const sfs = files.map(([rel, text]) => ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, rel.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS));
  const makers = elementMakers(sfs);
  for (const sf of sfs) {
    const rel = sf.fileName;
    const add = (n: ts.Node, what: string) => { const k = rel + ":" + holder(n) + ":" + what; sites.set(k, (sites.get(k) || 0) + 1); };
    /** A member read of a primitive: a call, a read, or nothing here when it is a construction's callee (the
     *  construction is the site). */
    const member = (access: ts.Node, name: string) => {
      const w = outermost(access), p = w.parent;
      if (ts.isNewExpression(p) && p.expression === w) return;
      add(access, name + (ts.isCallExpression(p) && p.expression === w ? ":call" : ":member"));
    };
    const visit = (n: ts.Node): void => {
      if (ts.isFunctionLike(n)) { const nm = nameOf(n); if (nm) fns.set(rel + ":" + nm, { node: n, sf }); }
      if (ts.isNewExpression(n)) {
        const name = calleeName(n.expression);
        // every construction whose callee NAMES a primitive or ends in a primitive's name (WorkerCtor, a WebSocket alias)
        if (name && (GLOBALS.has(name) || /(WebSocket|Worker|XMLHttpRequest|EventSource)/.test(name))) add(n, name + ":new");
      } else if (ts.isIdentifier(n) && METHODS.has(n.text) && !inType(n)) {
        const p = n.parent;
        if (ts.isBindingElement(p) && (p.propertyName === n || (!p.propertyName && p.name === n))) { /* the element is the site */ }
        else if (ts.isPropertyAccessExpression(p) && p.name === n) member(p, n.text);
        else if (GLOBALS.has(n.text)) {
          const w = outermost(n), wp = w.parent;
          const isNewCallee = ts.isNewExpression(wp) && wp.expression === w;
          const isTypeof = ts.isTypeOfExpression(wp);
          const isConstRead = ts.isPropertyAccessExpression(wp) && wp.expression === w && /^[A-Z_]+$/.test(wp.name.text);
          const isDecl = (ts.isVariableDeclaration(p) || ts.isParameter(p) || ts.isPropertyAssignment(p) || ts.isMethodDeclaration(p) || ts.isFunctionDeclaration(p) || ts.isPropertyDeclaration(p)) && (p as any).name === n;
          if (!isNewCallee && !isTypeof && !isConstRead && !isDecl) add(n, n.text + ":value");
        }
      } else if (ts.isElementAccessExpression(n)) {
        const k = keyText(n.argumentExpression);
        if (k && METHODS.has(k)) member(n, k);
      } else if (ts.isBindingElement(n) && ts.isObjectBindingPattern(n.parent)) {
        const k = bindingKey(n);
        if (k && METHODS.has(k)) add(n, k + ":member");
      } else if ((ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n)) && !isKey(n)) {
        const m = MARKUP.exec(n.text), s = m ? null : SCRIPT_TEXT.exec(n.text);
        if (m) add(n, m[1].toLowerCase() + ":markup");
        else if (s) add(n, (s[1] || s[2]) + ":string");
      } else if (ts.isCallExpression(n)) {
        const at = makers.get(calleeName(n.expression) || "");
        if (at) for (const i of at) {
          const tag = keyText(n.arguments[i]);
          if (tag && ELEMENTS.has(tag.toLowerCase())) add(n, tag.toLowerCase() + ":createElement");
        }
      }
      ts.forEachChild(n, visit);
    };
    visit(sf);
  }
  return { sites, fns };
}

let censusMemo: Census | null = null;
function uiCensus(): Census {
  if (!censusMemo) censusMemo = censusOf(sources().map((rel) => [rel, fs.readFileSync(path.join(UI_ROOT, rel), "utf8")]));
  return censusMemo;
}
const sorted = (m: Iterable<[string, number]>) => Object.fromEntries(Array.from(m).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
/** Every site whose count in the tree differs from its count in the list: a new site (listed at 0), a second primitive
 *  inside a listed function, and a listed site that went away (found 0). */
function unlisted(sites: Map<string, number>, listed: Record<string, { count: number }>): string[] {
  const keys = new Set([...sites.keys(), ...Object.keys(listed)]);
  return Array.from(keys).sort().filter((k) => (sites.get(k) || 0) !== (listed[k] ? listed[k].count : 0))
    .map((k) => k + ": " + (sites.get(k) || 0) + " in the tree, " + (listed[k] ? listed[k].count : 0) + " listed");
}

test("every request primitive under ui/ is a listed site with its road to the kernel, at the count the tree holds, and every listed site still exists", () => {
  const { sites } = uiCensus();
  assert.ok(sources().length > 100, "the census read the ui/ tree (a census of nothing proves nothing)");
  assert.deepEqual(unlisted(sites, UI_SITES), [],
    "a new request primitive under ui/, or a second one inside a listed function, carries no page key or cap unless it is written to: list it in UI_SITES with its count and the road it takes, or use fetch (the wrapper adds the key), fileUrl (the cap) or a dial that appends __rompKeyQ()");
});

test("pdf.js is handed the PDF's bytes, never an address it would fetch in its worker", () => {
  // The one worker the pages start is pdf.js's (UI_SITES above). A fetch inside a worker runs without the page-key script,
  // and the fetch census (fetch-wrapper-census.test.ts) reads a bare fetch as the wrapped global, so what keeps the worker
  // from requesting anything of the kernel is what getDocument is given: the bytes the page already fetched through the
  // wrapper, and no url, cMapUrl, standardFontDataUrl, wasmUrl or iccUrl that would send pdf.js to fetch on its own.
  const calls: string[] = [];
  for (const rel of sources()) {
    const text = fs.readFileSync(path.join(UI_ROOT, rel), "utf8");
    if (!text.includes("getDocument")) continue;
    const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, rel.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
    const visit = (n: ts.Node): void => {
      if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === "getDocument") {
        const arg = n.arguments[0];
        const where = rel + ":" + holder(n);
        assert.ok(arg && ts.isObjectLiteralExpression(arg), where + ": getDocument is handed an options object, not an address");
        const keys = (arg as ts.ObjectLiteralExpression).properties.map((p) => (p.name ? p.name.getText(sf) : "<spread>"));
        assert.ok(keys.includes("data"), where + ": it is handed the bytes (data)");
        for (const k of keys) assert.ok(!/url$|^<spread>$/i.test(k), where + ": no address and no spread options pdf.js could fetch from: " + k);
        calls.push(where);
      }
      ts.forEachChild(n, visit);
    };
    visit(sf);
  }
  assert.deepEqual(calls, ["webview/pdf-chunk.ts:makeRender"], "the one getDocument call, in the renderer makeRender returns (a new one is judged here)");
});

/** What is wrong with a listed dial's URL, if anything. Every socket the dialer constructs must take, as its first
 *  argument, a plain reference (a name or a member chain, `conn.url`) that the dialer writes only with what the builder
 *  returns, and writes before the construction. A URL built in the call, a reference also written from anything else
 *  (a replaced or amended URL), and a construction ahead of the write are each named. */
function dialProblems(dialer: ts.Node, sf: ts.SourceFile, builder: string): string[] {
  const text = (e: ts.Node) => e.getText(sf).replace(/\s+/g, "");
  const fromBuilder = (e: ts.Expression | undefined) => { const b = e && bare(e); return !!b && ts.isCallExpression(b) && calleeName(b.expression) === builder; };
  const isChain = (e: ts.Expression): boolean => ts.isIdentifier(e) || e.kind === ts.SyntaxKind.ThisKeyword || (ts.isPropertyAccessExpression(e) && isChain(e.expression));
  const dials: ts.NewExpression[] = [], writes: { at: number; target: string; ok: boolean }[] = [];
  const visit = (n: ts.Node): void => {
    if (ts.isNewExpression(n) && /WebSocket/.test(calleeName(n.expression) || "")) dials.push(n);
    else if (ts.isBinaryExpression(n) && n.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && n.operatorToken.kind <= ts.SyntaxKind.LastAssignment)
      writes.push({ at: n.getStart(sf), target: text(bare(n.left)), ok: n.operatorToken.kind === ts.SyntaxKind.EqualsToken && fromBuilder(n.right) });
    else if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name))
      writes.push({ at: n.getStart(sf), target: n.name.text, ok: fromBuilder(n.initializer) });
    ts.forEachChild(n, visit);
  };
  visit(dialer);
  const out: string[] = [];
  if (!dials.length) out.push("constructs no socket");
  for (const d of dials) {
    const where = "the socket at line " + (sf.getLineAndCharacterOfPosition(d.getStart(sf)).line + 1);
    const a = d.arguments && d.arguments[0] ? bare(d.arguments[0]) : null;
    if (!a || !isChain(a)) { out.push(where + " takes a URL built in the call: " + (a ? text(a) : "none")); continue; }
    const t = text(a), mine = writes.filter((w) => w.target === t);
    if (!mine.length || !mine.every((w) => w.ok)) out.push(where + " takes " + t + ", which the dialer writes other than with what " + builder + "() returns");
    else if (!mine.some((w) => w.at < d.getStart(sf))) out.push(where + " takes " + t + " before it is written with what " + builder + "() returns");
  }
  return out;
}

test("every listed socket dial takes the URL its builder returned, and the builder appends the page key", () => {
  const { fns } = uiCensus();
  for (const [site, builder] of Object.entries(DIAL_BUILDERS)) {
    const dialer = fns.get(site);
    assert.ok(dialer, site + " exists");
    const file = site.split(":")[0];
    const b = fns.get(file + ":" + builder);
    assert.ok(b, file + " defines " + builder);
    assert.deepEqual(dialProblems(dialer!.node, dialer!.sf, builder), [], site + " dials only the URL " + builder + " returned");
    assert.ok(b!.node.getText(b!.sf).includes("__rompKeyQ"), builder + " appends the page key (__rompKeyQ)");
  }
});

// The census's own reader, on synthetic sources: every form it reads, at its count, and each stated limit, so a change to
// the walker that stopped seeing a form shows here and not only when a real site appears.
test("the ui/ reader takes every form of a primitive at its count, and each stated limit stays unread", () => {
  const sitesOf = (src: string) => sorted(censusOf([["webview/synthetic.ts", src]]).sites);
  const one = (fn: string, what: string, n = 1) => ({ ["webview/synthetic.ts:" + fn + ":" + what]: n });
  // constructions, counted: the second one inside a function is a second site, and the list is held to the count
  assert.deepEqual(sitesOf("function f(u: string) { new WebSocket(u); new WebSocket(u); }"), one("f", "WebSocket:new", 2));
  const twice = censusOf([["webview/synthetic.ts", "function f(u: string) { new WebSocket(u); new WebSocket(u); }"]]).sites;
  assert.deepEqual(unlisted(twice, { "webview/synthetic.ts:f:WebSocket:new": { count: 1 } }), ["webview/synthetic.ts:f:WebSocket:new: 2 in the tree, 1 listed"]);
  assert.deepEqual(unlisted(twice, { "webview/synthetic.ts:f:WebSocket:new": { count: 2 }, "webview/synthetic.ts:g:Worker:new": { count: 1 } }),
    ["webview/synthetic.ts:g:Worker:new: 0 in the tree, 1 listed"]);
  assert.deepEqual(unlisted(twice, {}), ["webview/synthetic.ts:f:WebSocket:new: 2 in the tree, 0 listed"]);
  assert.deepEqual(sitesOf("function f(u: string) { return new window.WebSocket(u); }"), one("f", "WebSocket:new"));
  assert.deepEqual(sitesOf("function f(u: string) { return new (globalThis as any)['WebSocket'](u); }"), one("f", "WebSocket:new"));
  assert.deepEqual(sitesOf("function f(u: string) { return new (WebSocket as any)(u); }"), one("f", "WebSocket:new"));
  assert.deepEqual(sitesOf("function f(u: string) { new Worker(u); new SharedWorker(u); }"), { ...one("f", "Worker:new"), ...one("f", "SharedWorker:new") });
  assert.deepEqual(sitesOf("function f(u: string) { return new WebTransport(u); }"), one("f", "WebTransport:new"));
  // aliases and members of a global
  assert.deepEqual(sitesOf("function f() { const W = WebSocket; return W; }"), one("f", "WebSocket:value"));
  assert.deepEqual(sitesOf("function f() { const W = window.WebSocket; return W; }"), one("f", "WebSocket:member"));
  assert.deepEqual(sitesOf("function f() { const W = (window as any)['WebSocket']; return W; }"), one("f", "WebSocket:member"));
  assert.deepEqual(sitesOf("function f() { const { WebSocket: W } = window as any; return W; }"), one("f", "WebSocket:member"));
  assert.deepEqual(sitesOf("function f() { fetchLater('/a'); }"), one("f", "fetchLater:value"));
  // a service worker registration, direct, through an alias, by destructuring and by a string key
  assert.deepEqual(sitesOf("function f() { navigator.serviceWorker.register('/x.js'); }"), one("f", "serviceWorker:member"));
  assert.deepEqual(sitesOf("function f() { const c = navigator.serviceWorker; c.register('/x.js'); }"), one("f", "serviceWorker:member"));
  assert.deepEqual(sitesOf("function f() { const { serviceWorker } = navigator; serviceWorker.register('/x.js'); }"), one("f", "serviceWorker:member"));
  assert.deepEqual(sitesOf("function f() { (navigator as any)['serviceWorker'].register('/x.js'); }"), one("f", "serviceWorker:member"));
  // members that make a request, by name and by a string key
  assert.deepEqual(sitesOf("function f() { navigator.sendBeacon('/a'); (navigator as any)['sendBeacon']('/b'); }"), one("f", "sendBeacon:call", 2));
  assert.deepEqual(sitesOf("function f(x: HTMLFormElement) { x.requestSubmit(); x['submit'](); }"), { ...one("f", "requestSubmit:call"), ...one("f", "submit:call") });
  // markup, and script for some other document to run
  assert.deepEqual(sitesOf("function f(d: HTMLElement) { d.innerHTML = '<form method=post>'; }"), one("f", "form:markup"));
  assert.deepEqual(sitesOf("function f(fr: HTMLIFrameElement) { fr.srcdoc = '<script>new XMLHttpRequest()</script>'; }"), one("f", "XMLHttpRequest:string"));
  assert.deepEqual(sitesOf("function f(fr: HTMLIFrameElement) { fr.srcdoc = `<script>document.forms[0].submit()</script>`; }"), one("f", "submit:string"));
  // elements made directly, by namespace, and through helpers to a fixed point
  assert.deepEqual(sitesOf("function f() { document.createElement('FORM'); document.createElementNS('http://www.w3.org/1999/xhtml', 'object'); }"),
    { ...one("f", "form:createElement"), ...one("f", "object:createElement") });
  assert.deepEqual(sitesOf("function el(tag: string, cls: string) { const e = document.createElement(tag); e.className = cls; return e; }\nfunction g() { el('embed', 'x'); el('div', 'y'); }"),
    one("g", "embed:createElement"));
  // the outer helper written ahead of the one it calls, so reading it takes a second pass
  assert.deepEqual(sitesOf("function wrap(x: string) { return mk(document, x); }\nconst mk = (d: Document, t: string) => d.createElement(t);\nfunction g() { wrap('form'); }"),
    one("g", "form:createElement"));
  assert.deepEqual(sitesOf("const P: any = {};\nP.createEl = function (tag: string) { return document.createElement(tag); };\nfunction g(n: any) { n.createEl('object'); }"),
    one("g", "object:createElement"));
  // what is not a site: a feature test, a constant read, a type, a local named like a method, a string that names nothing
  assert.deepEqual(sitesOf("function f(s: WebSocket) { if (typeof WebSocket !== 'undefined' && s.readyState === WebSocket.OPEN) {} const submit = () => 1; submit(); addEventListener('submit', submit); }"), {});
  // stated limits: a name assembled at run time, a value that never names the primitive, a tag computed at run time
  assert.deepEqual(sitesOf("function f(u: string) { return new (window as any)['Web' + 'Socket'](u); }"), {}, "stated limit: a name assembled at run time is not read");
  assert.deepEqual(sitesOf("function f(ws: any, u: string) { return new ws.constructor(u); }"), {}, "stated limit: a value that never names the primitive is not read");
  assert.deepEqual(sitesOf("function f(kind: string) { return document.createElement(kind + 'm'); }"), {}, "stated limit: a tag computed at run time is not read");
  assert.deepEqual(sitesOf("function h(o: { tag: string }) { return document.createElement(o.tag); }\nfunction g() { h({ tag: 'form' }); }"), {},
    "stated limit: a tag that reaches createElement as a property of an options object is not read");
  assert.deepEqual(sitesOf("function g() { const mk = document.createElement.bind(document); return mk('form'); }"), {},
    "stated limit: createElement reached through an alias of itself is not read");
});

test("the dial check names a replaced, amended, rebuilt or early URL, and passes the builder's own", () => {
  const problems = (body: string) => {
    const sf = ts.createSourceFile("synthetic.ts", "class C {\n  connect(conn: any) {\n" + body + "\n  }\n}\n", ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
    const methods: ts.Node[] = [];
    const find = (n: ts.Node): void => { if (ts.isMethodDeclaration(n)) methods.push(n); ts.forEachChild(n, find); };
    find(sf);
    assert.equal(methods.length, 1, "the synthetic class has its one method");
    return dialProblems(methods[0], sf, "remoteDialUrl").length;
  };
  assert.equal(problems("conn.url = this.remoteDialUrl(conn, false);\nconst ws = new WebSocket(conn.url);"), 0, "the builder's URL, dialed");
  assert.equal(problems("const u = remoteDialUrl(conn);\nconst ws = new WebSocket(u);"), 0, "the builder's URL held in a local");
  assert.equal(problems("conn.url = this.remoteDialUrl(conn, false);\nconst ws = new WebSocket('ws://' + location.host + '/remote/h/ws');"), 1, "a replaced URL");
  assert.equal(problems("conn.url = this.remoteDialUrl(conn, false);\nconst ws = new WebSocket(conn.url.split('&k=')[0]);"), 1, "a URL rebuilt in the call");
  assert.equal(problems("conn.url = this.remoteDialUrl(conn, false);\nconn.url += '&x=1';\nconst ws = new WebSocket(conn.url);"), 1, "an amended URL");
  assert.equal(problems("conn.url = this.remoteDialUrl(conn, false);\nconn.url = conn.url.replace(/&k=[^&]*/, '');\nconst ws = new WebSocket(conn.url);"), 1, "a URL written again from elsewhere");
  assert.equal(problems("const ws = new WebSocket(conn.url);\nconn.url = this.remoteDialUrl(conn, false);"), 1, "a dial ahead of the write");
  assert.equal(problems("conn.url = this.remoteDialUrl(conn, false);\nconst ws = new window.WebSocket(conn.url), probe = new WebSocket('ws://h/ws');"), 1, "a second dial beside the listed one");
  assert.equal(problems("conn.url = this.remoteDialUrl(conn, false);"), 1, "no dial at all");
  assert.equal(problems("const a: string[] = [];\na[0] = this.remoteDialUrl(conn, false);\nconst ws = new WebSocket(a[0]);"), 1,
    "a URL read by an index, not a name or a member chain");
});

// ── the kernel's inline pages ────────────────────────────────────────────────────────────────────────────
/** A socket dial in an inline page, by every spelling the pattern reads: `new WebSocket(`, a space before the parenthesis,
 *  and the constructor read from window, self or globalThis. */
const DIAL = /new\s+(?:(?:window|self|globalThis)\s*\.\s*)?WebSocket\s*\(/g;
/** A quote in a page's script, as kernel.py's text holds it: its Python literal may escape it. */
const Q = String.raw`\\?['"` + "`]";
/** The inline pages' primitives, by pattern over kernel.py's text, with the count on the tree and the road each takes. */
const KERNEL_SITES: { name: string; re: RegExp; count: number; road: string }[] = [
  { name: "socket dial", re: DIAL, count: 2,
    road: "the pane shim's and the shell's /ws dials, each appending __rompKeyQ() in its own statement (checked below)" },
  { name: "XMLHttpRequest", re: /XMLHttpRequest/g, count: 0, road: "none" },
  { name: "EventSource", re: /EventSource/g, count: 0, road: "none" },
  { name: "sendBeacon", re: /sendBeacon/g, count: 0, road: "none" },
  { name: "fetchLater or WebTransport", re: /fetchLater|WebTransport/g, count: 0, road: "none" },
  { name: "worker construction", re: /new\s+(?:(?:window|self|globalThis)\s*\.\s*)?(?:Shared)?Worker\s*\(/g, count: 0, road: "none" },
  { name: "importScripts", re: /importScripts/g, count: 0, road: "none" },
  { name: "form markup", re: /<form\b/gi, count: 1,
    road: "the sign-in page's form, whose submit navigates to /?token= and returns false: it never posts (checked below)" },
  { name: "object or embed markup", re: /<(?:object|embed)\b/gi, count: 0, road: "none" },
  { name: "a form, an object or an embed made by createElement or createElementNS",
    re: new RegExp(String.raw`createElement(?:NS\s*\([^,)]*,|\s*\()\s*` + Q + String.raw`(?:form|object|embed)` + Q, "gi"), count: 0, road: "none" },
  { name: "createElement or createElementNS of a tag computed at run time",
    re: new RegExp(String.raw`createElement(?:NS\s*\([^,)]*,|\s*\()\s*(?!\s|` + Q + ")", "g"), count: 1,
    road: "the timeline's createEl helper (P.createEl), whose callers' tags the next pattern reads" },
  { name: "a form, an object or an embed made by the createEl helper",
    re: new RegExp(String.raw`createEl\s*\(\s*` + Q + String.raw`(?:form|object|embed)` + Q, "gi"), count: 0, road: "none" },
  { name: "form submission", re: new RegExp(String.raw`(?:\.\s*(?:request)?[sS]ubmit|\[\s*` + Q + String.raw`(?:request)?[sS]ubmit` + Q + String.raw`\s*\])\s*\(`, "g"), count: 0, road: "none" },
  { name: "service worker registration", re: /serviceWorker\s*\.\s*register\s*\(/g, count: 1,
    road: "register('/sw.js'): the worker script is the static class; its own requests are listed below" },
];

/** Names counted over every str constant of kernel.py that is not a docstring (bytes left out), so a name in a comment, a
 *  docstring or a Python header name (`Sec-WebSocket-Key`, a hyphen before the name) is not counted. The population is
 *  wider than the inline scripts, which are string constants like the Python ones: the parse cannot tell a string of
 *  JavaScript from a string of Python, so the scripts alone cannot be derived. A Python string that names one of these
 *  names raises its count, a false red and never a false green, since every script is among the strings read. Each
 *  catches what a pattern above cannot follow: an alias, a member or a string key of a global, a call through an alias.
 *  A renamed entry keeps its name's first words, which the tests below find it by. */
const KERNEL_NAMES: { name: string; re: RegExp; count: number; road: string }[] = [
  { name: "WebSocket named in a string constant of kernel.py", re: /(?<![\w$-])WebSocket/g, count: 2,
    road: "the two socket dials above; a third is an alias, a member or string-key read, a dial the pattern does not read, " +
      "or a Python string that names it" },
  { name: "Worker or SharedWorker named in a string constant of kernel.py", re: /(?<![\w$-])(?:Shared)?Worker/g, count: 0,
    road: "none; one here is a worker an inline script makes, or a Python string that names it" },
  { name: "a register call on any receiver", re: /\.\s*register\s*\(|\[\s*['"`]register['"`]\s*\]/g, count: 1,
    road: "the one service worker registration above; a second is a registration through an alias" },
  { name: "a submit member", re: /\.\s*(?:requestSubmit|submit)\b|\[\s*['"`](?:requestSubmit|submit)['"`]\s*\]/g, count: 0, road: "none" },
  { name: "createElement or createEl read by a string key", re: /\[\s*['"`]create(?:Element(?:NS)?|El)['"`]\s*\]/g, count: 0, road: "none" },
];

/** kernel.py's string constants (or any Python source's), read by python3's ast module: every str constant that is not
 *  a docstring, bytes left out. The kernel is Python, so python3 is on any machine that runs it; if it cannot run here the
 *  census is red, never skipped. */
function pyConstants(source: string): string[] {
  const script = [
    "import ast, json, sys",
    "tree = ast.parse(sys.stdin.read())",
    "docs = set()",
    "for n in ast.walk(tree):",
    "    if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:",
    "        f = n.body[0]",
    "        if isinstance(f, ast.Expr) and isinstance(f.value, ast.Constant) and isinstance(f.value.value, str):",
    "            docs.add(id(f.value))",
    "json.dump([n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs], sys.stdout)",
  ].join("\n");
  const r = spawnSync("python3", ["-c", script], { input: source, encoding: "utf8", timeout: 120000, maxBuffer: 256 * 1024 * 1024 });
  assert.equal(r.error, undefined, "python3 runs, to read the kernel's string constants: " + (r.error && r.error.message));
  assert.equal(r.status, 0, "python3 parsed the source: " + (r.stderr || "").slice(-400));
  return JSON.parse(r.stdout) as string[];
}
let kernelConstantsMemo: string[] | null = null;
const kernelConstants = (): string[] => (kernelConstantsMemo ??= pyConstants(KERNEL));
const dialCount = (): number => KERNEL_SITES.find((s) => s.re === DIAL)!.count;
const countIn = (re: RegExp, texts: string[]): number => texts.reduce((n, t) => n + (t.match(re) || []).length, 0);

/** The service worker's source (_SW_JS), the one worker the kernel serves. */
function swSource(): string {
  const m = /^_SW_JS = """([\s\S]*?)"""/m.exec(KERNEL);
  assert.ok(m, "kernel.py defines _SW_JS");
  return m![1];
}

test("every request primitive in the kernel's inline pages is a listed site, at the count the tree holds", () => {
  for (const s of KERNEL_SITES) {
    const n = (KERNEL.match(s.re) || []).length;
    assert.equal(n, s.count, s.name + ": " + n + " in kernel.py; list each with the road it takes to the kernel (" + s.road + ")");
  }
  const dials = Array.from(KERNEL.matchAll(DIAL));
  assert.equal(dials.length, dialCount(), "the dials the key check reads are the ones counted");
  const own = new RegExp("^" + DIAL.source + String.raw`[^;\n]*__rompKeyQ\(\)`);
  for (const m of dials) {
    const rest = KERNEL.slice(m.index!);
    assert.match(rest, own, "an inline socket dial appends the page key in its own statement: " + rest.slice(0, 100));
  }
  const form = /<form[\s\S]*?>/i.exec(KERNEL)![0];
  assert.match(form, /onsubmit="[\s\S]*location\.replace\('\/\?token='[\s\S]*return false"/, "the sign-in form navigates and returns false");
  assert.doesNotMatch(form, /method=|action=/i, "and names no method or action");
});

test("the names the patterns cannot follow are counted over every string constant of kernel.py that is not a docstring, at the count the tree holds", () => {
  const texts = kernelConstants();
  assert.ok(texts.length > 1000, "the kernel's string constants were read (a census of nothing proves nothing): " + texts.length);
  assert.ok(countIn(/<script\b/g, texts) > 0, "and they hold the inline pages' scripts");
  for (const s of KERNEL_NAMES) {
    const n = countIn(s.re, texts);
    assert.equal(n, s.count, s.name + ": " + n + " in kernel.py's string constants; list each with the road it takes to the kernel (" + s.road + ")");
  }
  assert.equal(KERNEL_NAMES.find((s) => s.name.startsWith("WebSocket"))!.count, dialCount(), "every WebSocket a string constant of kernel.py names is one of the dials the key check reads");
});

test("the kernel half's readers take every spelling they name, and each stated limit stays unread", () => {
  const site = (name: string) => KERNEL_SITES.find((s) => s.name.startsWith(name))!.re;
  const named = (name: string) => KERNEL_NAMES.find((s) => s.name.startsWith(name))!.re;
  const n = (re: RegExp, text: string) => (text.match(re) || []).length;
  for (const d of ["new WebSocket(u)", "new WebSocket (u)", "new window.WebSocket(u)", "new self.WebSocket(u)", "new globalThis . WebSocket(u)"])
    assert.equal(n(DIAL, d), 1, "a dial: " + d);
  for (const c of ["createElement('form')", "createElement(\"OBJECT\")", "createElement(\\\"embed\\\")", "createElement( `form` )",
                   "createElementNS('http://www.w3.org/1999/xhtml','form')"])
    assert.equal(n(site("a form, an object or an embed made by createElement"), c), 1, "an element: " + c);
  assert.equal(n(site("a form, an object or an embed made by createElement"), "createElement('div');createElementNS(ns,'line')"), 0);
  assert.equal(n(site("createElement or createElementNS of a tag"), "createElement(tag);createElementNS(ns, t);createElement('div');createElement( 'div');createElement(\\\"div\\\")"), 2);
  assert.equal(n(site("a form, an object or an embed made by the createEl"), "n.createEl('form');n.createEl(\\\"embed\\\")"), 2);
  for (const s of ["f.submit()", "f.submit ()", "f.requestSubmit()", "f['submit']()", "f[\\\"requestSubmit\\\"]()"])
    assert.equal(n(site("form submission"), s), 1, "a submission: " + s);
  assert.equal(n(site("service worker registration"), "navigator.serviceWorker . register('/sw.js')"), 1);
  // over string constants, read from a synthetic Python source: comments, docstrings and bytes are not counted
  const texts = pyConstants([
    "'''new WebSocket(u), a module docstring'''",
    "# var W=WebSocket, a comment",
    "H = \"Sec-WebSocket-Key\"",
    "B = b\"var X=WebSocket;\"",
    "A = \"var W=window.WebSocket;new W(u);\"",
    "C = \"var X=window['WebSocket'];var s=new WebSocketStream(u);\"",
    "M = \"the WebSocket relay closed\"",
    "R = \"var c=navigator.serviceWorker;c.register('/x.js');f.submit;new SharedWorker(u);d['createElement']('form');\"",
    "def f():",
    "    \"\"\"WebSocket, a docstring\"\"\"",
    "    return 1",
  ].join("\n"));
  assert.equal(countIn(named("WebSocket"), texts), 4,
    "the alias, the string key, the WebSocketStream and a Python message string, since every str constant is read; not the docstrings, the comment, the header name or the bytes");
  assert.equal(countIn(named("Worker"), texts), 1);
  assert.equal(countIn(named("a register call"), texts), 1);
  assert.equal(countIn(named("a submit member"), texts), 1);
  assert.equal(countIn(named("createElement or createEl read by a string key"), texts), 1);
  // stated limits: an alias that never names the primitive, a name assembled at run time
  const limits = pyConstants("L = \"var C=ws.constructor;new C(u);var W=window['Web'+'Socket'];new W(u);\"");
  assert.equal(countIn(named("WebSocket"), limits) + countIn(DIAL, limits), 0, "stated limit: a dial through a value that never names WebSocket is not read");
  const tags = "n.createEl(kind);var mk=document.createElement.bind(document);mk('form');";
  assert.equal(n(site("a form, an object or an embed made by"), tags) + n(site("createElement or createElementNS of a tag"), tags)
    + n(site("a form, an object or an embed made by the createEl"), tags), 0,
    "stated limit: a tag computed at run time and passed to the helper, and createElement through an alias of itself, are not read");
});

test("the service worker makes one kind of request, to the auth-exempt /push/ack, and opens windows only on page routes", () => {
  const sw = swSource();
  const fetches = sw.match(/fetch\([^,)]*/g) || [];
  assert.ok(fetches.length >= 1, "the worker's fetches were found");
  for (const f of fetches) assert.equal(f, "fetch('/push/ack'", "a worker has no fetch wrapper, so its one request goes to the route that needs no credential: " + f);
  assert.doesNotMatch(sw, /XMLHttpRequest|EventSource|sendBeacon|importScripts|new WebSocket|addEventListener\(['"]fetch['"]/, "no other request primitive, and no fetch handler");
  assert.match(sw, /clients\.openWindow\(url\)/, "a notification opens its deep link, a page route, which rides the cookie");
});
