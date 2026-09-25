// A census of the fetch calls the dashboard's page bundles make, so a fetch that does not carry the page key is judged when
// it is written rather than refused at run time.
//
// The kernel puts one script first in the head of every page document (kernel.py _PAGE_KEY_JS, placed by Handler._send). It
// replaces the page's window.fetch with a wrapper that adds this origin's page key, as X-Romp-Key, to every request whose URL
// resolves to this origin, and leaves a request to any other origin as it was. Every bundle runs after that script, so a
// fetch a bundle makes through the page's own global fetch carries the key, and the kernel answers it. A fetch made any other
// way carries no key: another window's fetch (a frame made by script has a window.fetch of its own, which nothing wrapped), a
// local binding named fetch that stands in for the global, a fetch passed around as a value the census cannot follow, or a
// fetch written into a string as script for some other document to run. Such a request is refused with a 403, and nothing
// flags it at test time.
//
// So this census reads every reference to `fetch` in the sources the shipped page bundles contain, with the TypeScript
// compiler's parser (comments and strings are what the language says they are). The population is DERIVED, not listed:
// it is the first-party input list of esbuild's own metafile, from an in-memory build of vscode-extension/esbuild.js's
// `webview` config (nothing is written), so a module a bundle starts to import is read from the day it is imported. Each
// reference must be one of three shapes: a call of the global fetch by its bare name, in a file that declares no binding
// of that name; a call through window, globalThis or self; or a `typeof fetch` feature test. Every other reference, and
// every string literal that holds a fetch call as text, is red until it is listed below with the reason it still reaches
// the wrapper.
//
// Two neighbours finish the picture. The kernel's own inline scripts are checked over the documents the kernel serves
// (tests/test_fetch_wrapper_census.py: each fetch call there is served inside a page document after the wrapper, and each
// page document opens with it). The other request primitives (XMLHttpRequest, EventSource, sendBeacon, sockets, workers,
// forms) are client-request-census.test.ts's. What the wrapper does with each request form is executed in a browser by
// tests/test_page_key_dashboard_browser.py.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import * as ts from "typescript";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const ROOT = path.resolve(EXT, "..");
const pkgRequire = createRequire(path.resolve(EXT, "package.json"));

/** Where a bare `fetch` call is the page's own global: the three names a page's scripts reach their window by. */
const GLOBAL_OBJECTS = new Set(["window", "globalThis", "self"]);
const MODULE_SUFFIX = /\.(ts|mts|cts|tsx|js|mjs|cjs|jsx)$/;
/** A fetch call written as text: the name, not preceded by a name character or a dot, before an opening parenthesis. */
const CALL_TEXT = /(?<![\w$.])fetch\s*\(/;
const MEMBER_TEXT = /\.\s*fetch\b/;

/** Sites that are none of the three shapes, by `file:line-free key`, with the reason each still reaches the wrapper. None
 *  today: a site listed here must say why its request carries the key anyway. */
const LISTED: Record<string, string> = {};

let bundledP: Promise<string[]> | null = null;
/** The first-party modules the shipped page bundles contain: esbuild's metafile of the `webview` config built in memory
 *  (esbuild.js exports the config and builds only when run as a script), repo-relative with forward slashes. Inputs
 *  under node_modules are third-party and are not read here; the one that fetches is pdf.js, whose document is handed
 *  the bytes the page already fetched (client-request-census.test.ts lists its worker). */
function bundledModules(): Promise<string[]> {
  if (!bundledP) bundledP = (async () => {
    const { webview } = pkgRequire("./esbuild.js") as { webview?: import("esbuild").BuildOptions };
    assert.ok(webview && typeof webview === "object" && webview.entryPoints, "vscode-extension/esbuild.js exports the page bundles' `webview` config with its entry points");
    const esbuild = pkgRequire("esbuild") as typeof import("esbuild");
    const r = await esbuild.build({ ...webview, write: false, metafile: true, logLevel: "silent" });
    const inputs = Object.keys(r.metafile!.inputs).filter((k) => !k.includes("node_modules/"));
    return inputs.map((k) => path.relative(ROOT, path.resolve(EXT, k)).split(path.sep).join("/"))
      .filter((k) => MODULE_SUFFIX.test(k)).sort();
  })();
  return bundledP;
}

type Site = { key: string; where: string; shape: string };

/** Every reference to the name `fetch` in one source, by shape; and every string literal holding a fetch call as text. */
export function censusOf(rel: string, text: string): { sites: Site[]; declares: string[] } {
  const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true,
    /\.[mc]?tsx?$/.test(rel) ? (rel.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS) : (rel.endsWith("x") ? ts.ScriptKind.JSX : ts.ScriptKind.JS));
  const sites: Site[] = [], declares: string[] = [];
  const at = (n: ts.Node) => rel + ":" + (sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1);
  const holder = (n: ts.Node): string => {
    for (let x = n.parent; x; x = x.parent) {
      if (ts.isFunctionLike(x)) {
        if ((ts.isFunctionDeclaration(x) || ts.isMethodDeclaration(x)) && x.name) return x.name.getText(sf);
        const p = x.parent;
        if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
        if (p && (ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p))) return p.name.getText(sf);
      }
    }
    return "<module>";
  };
  const add = (n: ts.Node, shape: string) => sites.push({ key: rel + ":" + holder(n) + ":" + shape, where: at(n), shape });
  const isDeclName = (n: ts.Identifier): boolean => {
    const p = n.parent;
    return (ts.isVariableDeclaration(p) || ts.isParameter(p) || ts.isFunctionDeclaration(p) || ts.isFunctionExpression(p)
      || ts.isClassDeclaration(p) || ts.isBindingElement(p) || ts.isImportSpecifier(p) || ts.isImportClause(p)
      || ts.isNamespaceImport(p) || ts.isImportEqualsDeclaration(p) || ts.isEnumDeclaration(p)) && (p as any).name === n;
  };
  const visit = (n: ts.Node): void => {
    if (ts.isIdentifier(n) && n.text === "fetch") {
      const p = n.parent;
      if (isDeclName(n)) { declares.push(at(n)); add(n, "declaration"); }
      else if (ts.isCallExpression(p) && p.expression === n) add(n, "call");
      else if (ts.isTypeOfExpression(p) && p.expression === n) add(n, "typeof");
      else if (ts.isPropertyAccessExpression(p) && p.name === n) {
        const obj = p.expression, called = ts.isCallExpression(p.parent) && p.parent.expression === p;
        if (called && ts.isIdentifier(obj) && GLOBAL_OBJECTS.has(obj.text)) add(n, "global-call");
        else add(n, "member:" + obj.getText(sf).replace(/\s+/g, " ").slice(0, 60) + (called ? ":call" : ""));
      }
      else if ((ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p) || ts.isMethodDeclaration(p) || ts.isPropertySignature(p)
                || ts.isMethodSignature(p) || ts.isGetAccessor(p) || ts.isSetAccessor(p)) && p.name === n) add(n, "member-definition");
      else if (ts.isTypeReferenceNode(p) || ts.isTypeQueryNode(p) || ts.isQualifiedName(p)) { /* a type, which makes no request */ }
      else add(n, "value:" + ts.SyntaxKind[p.kind]);
    } else if ((ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n)
                || ts.isTemplateTail(n)) && (CALL_TEXT.test(n.text) || MEMBER_TEXT.test(n.text))) {
      add(n, "string");
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return { sites, declares };
}

/** Is this site one of the three shapes that reach the page's wrapped global fetch? A bare call is one only in a file that
 *  declares no binding named fetch (the census does not resolve scopes: any such binding makes every bare call in its file
 *  a listed site). */
function reachesTheWrapper(s: Site, fileDeclares: boolean): boolean {
  if (s.shape === "typeof" || s.shape === "global-call") return true;
  return s.shape === "call" && !fileDeclares;
}

let censusP: Promise<{ files: string[]; sites: Site[]; declaring: Set<string> }> | null = null;
function census() {
  if (!censusP) censusP = (async () => {
    const files = await bundledModules();
    const sites: Site[] = [], declaring = new Set<string>();
    for (const rel of files) {
      const r = censusOf(rel, fs.readFileSync(path.join(ROOT, rel), "utf8"));
      sites.push(...r.sites);
      if (r.declares.length) declaring.add(rel);
    }
    return { files, sites, declaring };
  })();
  return censusP;
}

test("the census reads the modules the page bundles contain, and finds their fetch calls", async () => {
  const { files, sites } = await census();
  for (const f of ["ui/webview/render.ts", "ui/webview/feed.ts", "ui/webview/strip.ts", "ui/webview/gear.js", "ui/romp-timeline-view.js"])
    assert.ok(files.includes(f), "the bundles' inputs include " + f + " (the build the census reads is the shipped one): " + files.length + " modules");
  assert.ok(sites.filter((s) => s.shape === "call").length > 20, "the census found the bundles' fetch calls (a census of nothing proves nothing): " + sites.length + " references");
});

test("every fetch in the page bundles is a call of the page's own global fetch, which the page-key script wrapped", async () => {
  const { sites, declaring } = await census();
  const off = sites.filter((s) => !reachesTheWrapper(s, declaring.has(s.key.split(":")[0])) && !(s.key in LISTED));
  assert.deepEqual(off.map((s) => s.where + " " + s.shape), [],
    "a fetch that is not a call of the page's global fetch carries no page key and is refused: call fetch(...) by its bare name "
    + "(or through window, globalThis or self), or list the site in LISTED with the reason its request still carries the key");
});

test("no module in the page bundles declares a binding named fetch", async () => {
  const { declaring } = await census();
  assert.deepEqual(Array.from(declaring).sort(), [],
    "a binding named fetch stands in for the page's global in its scope, so a bare call there may not reach the wrapper");
});

test("every listed site still exists", async () => {
  const { sites } = await census();
  const keys = new Set(sites.map((s) => s.key));
  assert.deepEqual(Object.keys(LISTED).filter((k) => !keys.has(k)), [], "a listed site that went away is stale");
});

// The census's own classifier, on synthetic sources: every shape it lets through, and every shape it holds, so a change to
// the walker that stopped seeing one shows here and not only when a real site appears.
test("the classifier admits the global call shapes and holds every other reference", () => {
  const shapes = (src: string) => censusOf("synthetic.ts", src).sites.map((s) => s.shape);
  assert.deepEqual(shapes("fetch('/sessions').then((r) => r.json());"), ["call"]);
  assert.deepEqual(shapes("window.fetch('/a'); globalThis.fetch('/b'); self.fetch('/c');"), ["global-call", "global-call", "global-call"]);
  assert.deepEqual(shapes("if (typeof fetch !== 'undefined') {}"), ["typeof"]);
  assert.deepEqual(shapes("const f = document.createElement('iframe'); (f.contentWindow as any).fetch('/sessions');"), ["member:(f.contentWindow as any):call"]);
  assert.deepEqual(shapes("parent.fetch('/sessions');"), ["member:parent:call"]);
  assert.deepEqual(shapes("const g = fetch; g('/sessions');"), ["value:VariableDeclaration"]);
  assert.deepEqual(shapes("run(fetch);"), ["value:CallExpression"]);
  assert.deepEqual(shapes("function load(fetch: (u: string) => Promise<Response>) { return fetch('/sessions'); }"), ["declaration", "call"]);
  assert.deepEqual(shapes("const opts = { fetch: myFetch };"), ["member-definition"]);
  assert.deepEqual(shapes("frame.srcdoc = \"<script>fetch('/sessions')</script>\";"), ["string"]);
  assert.deepEqual(shapes("frame.srcdoc = `<script>top.fetch('/sessions')</script>`;"), ["string"]);
  assert.deepEqual(shapes("// a fetch in a comment\nconst note = 'the fetch failed';"), [], "a comment, and prose that is not a call, are not sites");
  assert.deepEqual(shapes("let r: typeof fetch;"), [], "a type makes no request");
  const decl = censusOf("synthetic.ts", "const fetch = window.fetch; fetch('/sessions');");
  assert.equal(decl.declares.length, 1, "a declaration of the name is seen");
  assert.equal(reachesTheWrapper(decl.sites.find((s) => s.shape === "call")!, true), false, "and a bare call in its file is held");
});
