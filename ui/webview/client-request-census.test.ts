// A census of the request primitives the dashboard's pages use, so a new kind of request is judged when it is written
// rather than found at run time.
//
// Every request a kernel page makes to its kernel authenticates by one of three roads: a page document or a static
// bundle rides the session cookie alone; a fetch carries the page key as X-Romp-Key (the kernel's fetch wrapper, first in
// every page's head); a socket dial carries it as k= (window.__rompKeyQ); a header-less /file load carries a per-file cap
// (file-cap.ts). A request made any other way (an XMLHttpRequest, an EventSource, a sendBeacon, a form POST, an <object>
// or <embed> of a kernel route, a fetch from a worker, where the wrapper does not run, or a socket dialed without the key)
// carries none of them and is refused with a 403 that nothing flags at test time. So this census reads every such
// primitive in the non-test sources under ui/ (with the TypeScript compiler's parser, so comments and strings are what the
// language says they are) and in kernel/kernel.py, where the inline pages live as Python strings (read as text, pattern by
// pattern), and holds each against the list below. A new site is red until it is listed with the road it takes, and a
// listed site that went away is stale.
//
// What counts as a site under ui/: a construction (`new WebSocket(...)`, `new Worker(...)`), a call through a member
// (`navigator.sendBeacon(...)`, `form.requestSubmit()`, `x.submit()`), a value reference to a primitive that is neither of
// those nor a feature test (`typeof WebSocket`) nor a constant read (`WebSocket.OPEN`), since an alias passes the
// primitive around under another name, a string literal holding markup for a form, an object or an embed, and a
// createElement of one of those three. A type annotation is not a site.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as ts from "typescript";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI_ROOT = path.resolve(EXT, "..", "ui");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");

/** The globals that make a request, read wherever the name is used as a value; and the methods that do, read as a member
 *  (`navigator.sendBeacon`, `form.submit()`), where a bare local of the same name (a `submit` handler) is not one. */
const GLOBALS = new Set(["XMLHttpRequest", "EventSource", "WebSocket", "Worker", "SharedWorker", "importScripts"]);
const METHODS = new Set(["sendBeacon", "requestSubmit", "submit", ...GLOBALS]);
const MARKUP = /<\s*(form|object|embed)\b/i;
const ELEMENTS = new Set(["form", "object", "embed"]);

/** Every site under ui/ by `file:function:primitive:how`, with the road it takes to the kernel. */
const UI_SITES: Record<string, string> = {
  "webview/federation.ts:connect:WebSocket:new":
    "the relay dial to /remote/<host>/ws: its URL is remoteDialUrl's, which appends __rompKeyQ() (checked below)",
  "webview/pdf-chunk.ts:ownWorker:Worker:value":
    "the default Worker constructor handed to ownWorker (a test injects a stand-in); see the construction below",
  "webview/pdf-chunk.ts:ownWorker:WorkerCtor:new":
    "pdf.js's module Worker, loaded from /dist/pdf-worker.js (the static class, on the cookie); getDocument is handed the " +
    "PDF's bytes, which the page fetched through the wrapper, so the worker fetches nothing from the kernel",
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

type Census = { sites: Map<string, number>; fns: Map<string, { node: ts.Node; sf: ts.SourceFile }> };
let censusMemo: Census | null = null;
function uiCensus(): Census {
  if (censusMemo) return censusMemo;
  const sites = new Map<string, number>(), fns = new Map<string, { node: ts.Node; sf: ts.SourceFile }>();
  const add = (k: string) => sites.set(k, (sites.get(k) || 0) + 1);
  for (const rel of sources()) {
    const text = fs.readFileSync(path.join(UI_ROOT, rel), "utf8");
    const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, rel.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
    const visit = (n: ts.Node): void => {
      if (ts.isFunctionLike(n)) { const nm = nameOf(n); if (nm) fns.set(rel + ":" + nm, { node: n, sf }); }
      if (ts.isNewExpression(n)) {
        const c = n.expression;
        const name = ts.isIdentifier(c) ? c.text : ts.isPropertyAccessExpression(c) ? c.name.text : null;
        // every construction whose callee NAMES a primitive or ends in a primitive's name (WorkerCtor, a WebSocket alias)
        if (name && (GLOBALS.has(name) || /(WebSocket|Worker|XMLHttpRequest|EventSource)/.test(name))) add(rel + ":" + holder(n) + ":" + name + ":new");
      } else if (ts.isIdentifier(n) && METHODS.has(n.text) && !inType(n)) {
        const p = n.parent;
        const isNewCallee = ts.isNewExpression(p) && p.expression === n;
        const isTypeof = ts.isTypeOfExpression(p);
        const isConstRead = ts.isPropertyAccessExpression(p) && p.expression === n && /^[A-Z_]+$/.test(p.name.text);
        const isMemberName = ts.isPropertyAccessExpression(p) && p.name === n;
        const isDecl = (ts.isVariableDeclaration(p) || ts.isParameter(p) || ts.isPropertyAssignment(p) || ts.isMethodDeclaration(p) || ts.isFunctionDeclaration(p) || ts.isPropertyDeclaration(p)) && (p as any).name === n;
        if (isMemberName) {
          const call = p.parent;
          const newWrapped = ts.isNewExpression(call) && call.expression === p;
          if (!newWrapped) add(rel + ":" + holder(n) + ":" + n.text + (ts.isCallExpression(call) && call.expression === p ? ":call" : ":member"));
        } else if (GLOBALS.has(n.text) && !isNewCallee && !isTypeof && !isConstRead && !isDecl) add(rel + ":" + holder(n) + ":" + n.text + ":value");
      } else if ((ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n)) && MARKUP.test(n.text)) {
        add(rel + ":" + holder(n) + ":" + MARKUP.exec(n.text)![1].toLowerCase() + ":markup");
      } else if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && n.expression.name.text === "createElement"
                 && n.arguments[0] && ts.isStringLiteralLike(n.arguments[0]) && ELEMENTS.has(n.arguments[0].text.toLowerCase())) {
        add(rel + ":" + holder(n) + ":" + n.arguments[0].text.toLowerCase() + ":createElement");
      }
      ts.forEachChild(n, visit);
    };
    visit(sf);
  }
  censusMemo = { sites, fns };
  return censusMemo;
}

test("every request primitive under ui/ is a listed site with its road to the kernel, and every listed site still exists", () => {
  const { sites } = uiCensus();
  assert.ok(sources().length > 100, "the census read the ui/ tree (a census of nothing proves nothing)");
  assert.deepEqual(Array.from(sites.keys()).sort(), Object.keys(UI_SITES).sort(),
    "a new request primitive under ui/ carries no page key or cap unless it is written to: list it in UI_SITES with the road it takes, or use fetch (the wrapper adds the key), fileUrl (the cap) or a dial that appends __rompKeyQ()");
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

test("every listed socket dial builds its URL through a function that appends the page key", () => {
  const { fns } = uiCensus();
  for (const [site, builder] of Object.entries(DIAL_BUILDERS)) {
    const dialer = fns.get(site);
    assert.ok(dialer, site + " exists");
    const file = site.split(":")[0];
    const b = fns.get(file + ":" + builder);
    assert.ok(b, file + " defines " + builder);
    const dialText = dialer!.node.getText(dialer!.sf), builderText = b!.node.getText(b!.sf);
    assert.ok(dialText.includes(builder + "("), site + " takes its URL from " + builder);
    assert.ok(builderText.includes("__rompKeyQ"), builder + " appends the page key (__rompKeyQ)");
  }
});

// ── the kernel's inline pages ────────────────────────────────────────────────────────────────────────────
/** The inline pages' primitives, by pattern over kernel.py's text, with the count on the tree and the road each takes. */
const KERNEL_SITES: { name: string; re: RegExp; count: number; road: string }[] = [
  { name: "socket dial", re: /new WebSocket\(/g, count: 2,
    road: "the pane shim's and the shell's /ws dials, each appending __rompKeyQ() on its own line (checked below)" },
  { name: "XMLHttpRequest", re: /XMLHttpRequest/g, count: 0, road: "none" },
  { name: "EventSource", re: /EventSource/g, count: 0, road: "none" },
  { name: "sendBeacon", re: /sendBeacon/g, count: 0, road: "none" },
  { name: "worker construction", re: /new (?:Shared)?Worker\(/g, count: 0, road: "none" },
  { name: "importScripts", re: /importScripts/g, count: 0, road: "none" },
  { name: "form markup", re: /<form\b/gi, count: 1,
    road: "the sign-in page's form, whose submit navigates to /?token= and returns false: it never posts (checked below)" },
  { name: "object or embed markup", re: /<(?:object|embed)\b/gi, count: 0, road: "none" },
  { name: "form submission", re: /\.(?:request)?[sS]ubmit\(/g, count: 0, road: "none" },
  { name: "service worker registration", re: /serviceWorker\.register\(/g, count: 1,
    road: "register('/sw.js'): the worker script is the static class; its own requests are listed below" },
];

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
  for (const line of KERNEL.split("\n").filter((l) => /new WebSocket\(/.test(l)))
    assert.match(line.slice(line.indexOf("new WebSocket(")), /^new WebSocket\([^;]*__rompKeyQ\(\)/, "an inline socket dial appends the page key in its own statement: " + line.trim().slice(0, 100));
  const form = /<form[\s\S]*?>/i.exec(KERNEL)![0];
  assert.match(form, /onsubmit="[\s\S]*location\.replace\('\/\?token='[\s\S]*return false"/, "the sign-in form navigates and returns false");
  assert.doesNotMatch(form, /method=|action=/i, "and names no method or action");
});

test("the service worker makes one kind of request, to the auth-exempt /push/ack, and opens windows only on page routes", () => {
  const sw = swSource();
  const fetches = sw.match(/fetch\([^,)]*/g) || [];
  assert.ok(fetches.length >= 1, "the worker's fetches were found");
  for (const f of fetches) assert.equal(f, "fetch('/push/ack'", "a worker has no fetch wrapper, so its one request goes to the route that needs no credential: " + f);
  assert.doesNotMatch(sw, /XMLHttpRequest|EventSource|sendBeacon|importScripts|new WebSocket|addEventListener\(['"]fetch['"]/, "no other request primitive, and no fetch handler");
  assert.match(sw, /clients\.openWindow\(url\)/, "a notification opens its deep link, a page route, which rides the cookie");
});
