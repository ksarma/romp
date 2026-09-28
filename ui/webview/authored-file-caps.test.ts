// Every renderer of authored markdown caps the /file URLs its author wrote, or the list says why it need not
// (authored-file-caps.ts). A header-less load of an uncapped /file URL is refused (file-cap.ts), so a renderer that
// skipped the pass would show a broken image or a dead download link where the author wrote a working one.
//
// THE CENSUS. The population is DERIVED: every call of sanitizeMd (md-sanitize.ts, the one sanitizer every authored
// markdown surface shares) in the non-test sources under ui/, read with the TypeScript compiler's parser, keyed by its
// file and the named function that holds it. The census must equal RENDERERS both ways, so a new sanitizeMd call site is
// red here until it is judged, and a listed one that went away is stale. A "capped" renderer's function passes the very
// variable it holds the sanitized body in to capAuthoredFileUrls, AFTER the sanitize. A "disclosed" one names the passes
// its reason rests on, and the census checks the function calls them. sanitizeMd reached any other way (a property access,
// another name) is a failure naming the site, since a call by another route would count nothing.
//
// THE ANCHOR CENSUS. A /file URL can also reach the page as an anchor that no markdown renderer made: a URL typed into a
// todo's or a note's text, a todo's link chip, a code span holding one URL. The population is DERIVED: every call that
// creates an anchor element (`createElement("a")` on any document, or the viewer's `el("a", ...)` helper) in the non-test
// sources under ui/, keyed by its file and the named function that holds it, equal to ANCHORS both ways. An anchor whose
// href is typed text runs it through withFileCap (file-cap.ts) in that function; one whose href fileUrl builds calls
// fileUrl there; one that sets no href sets none there; any other says where its href comes from. Anchors minted from a
// markup string are not read here: the markdown renderers above are that population.
//
// THE PASS, in a real browser (headless Chromium through the extension's playwright; skips loudly without one, as the other
// browser legs do): markdown with every attribute the pass reads, through marked and the real sanitizeMd, then
// capAuthoredFileUrls under a page key. Each /file and /remote/<host>/file URL comes back with the cap file-cap.ts computes
// for it; every other URL is untouched; with no key nothing changes. Synthetic values only: keys minted at run time,
// placeholder uuids, host TESTHOST, example.invalid.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { randomBytes } from "node:crypto";
import * as ts from "typescript";
import { capFor } from "./file-cap";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI_ROOT = path.resolve(EXT, "..", "ui");
const UI = path.join(UI_ROOT, "webview");

type Renderer = { kind: "capped" } | { kind: "disclosed"; why: string; calls: string[] };
/** Every function that sanitizes authored markdown, by `file:function`. */
const RENDERERS: Record<string, Renderer> = {
  "webview/render.ts:md": { kind: "capped" },                     // an assistant's, a subagent's or a peer's message
  "webview/render.ts:userMd": { kind: "capped" },                 // the user's own message
  "webview/render.ts:renderFilePreview": { kind: "capped" },      // a hover card's provider HTML
  "webview/render.ts:previewMdClean": { kind: "capped" },         // a hover card's rendered markdown file
  "webview/feed.ts:noticeBodyNodes": { kind: "capped" },          // a notice card's body
  "webview/file-view.ts:mdBlock": { kind: "capped" },            // the viewer's markdown: a /file URL written with a scheme (fileUrl caps the rest)
};

type AnchorSite = { href: "typed" | "fileUrl" | "none" | "other"; why: string };
/** Every function that creates an anchor element, by `file:function`, with where its href comes from. */
const ANCHORS: Record<string, AnchorSite> = {
  "webview/url-links.ts:linkifyUrls": { href: "typed", why: "a URL typed into a todo's or a note's text, or a file's prose in the viewer" },
  "webview/url-links.ts:urlChip": { href: "typed", why: "a todo's own link, as its author gave it" },
  "webview/render.ts:linkifyFileUris": { href: "typed", why: "a code span in a message whose whole text is one URL" },
  "webview/preview.ts:openLightbox": { href: "fileUrl", why: "the lightbox's Download control" },
  "webview/file-browse.ts:startDownload": { href: "fileUrl", why: "the file browser's download of a row" },
  "webview/file-view.ts:startDownload": { href: "other", why: "the URL its callers hand it: the viewer's download address, which fileUrl builds with the cap" },
  "webview/file-view.ts:apply": { href: "other", why: "the kernel's GitHub address for the open file (fileGitLink), on github.com and never this origin" },
  "webview/file-view.ts:linkOut": { href: "other", why: "a URL document's own address, opened as it is; a document on this origin is a .md address, which names no kernel route" },
  "webview/gear.js:lgRender": { href: "other", why: "the login flow's sign-in page, on the provider's own origin" },
  "webview/pr-links.ts:linkifyTextNode": { href: "other", why: "a GitHub pull request or issue address, on github.com and never this origin" },
  "webview/feed.ts:makeAskCard": { href: "none", why: "the card's session name, origin, blocked badge and todo mark: click targets" },
  "webview/feed.ts:updateAskCard": { href: "none", why: "a delegation's name: a click target" },
  "webview/feed.ts:makeGroupCard": { href: "none", why: "the group's session name: a click target" },
  "webview/feed.ts:renderTreeNode": { href: "none", why: "a tree row's session name: a click target" },
  "webview/feed.ts:renderModalNow": { href: "none", why: "the modal's agent name: a click target" },
  "webview/feed.ts:makeSessHead": { href: "none", why: "a session header's name: a click target" },
  "webview/feed.ts:ensureFocusSection": { href: "none", why: "the focus section's session name: a click target" },
};

/** The non-test TypeScript and JavaScript sources under ui/ (the webview's and the timeline's), by path from ui/. */
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
  if (p && ts.isPropertyAssignment(p)) return p.name.getText();
  return null;
};
const enclosingFn = (n: ts.Node): ts.FunctionLikeDeclaration | null => {
  for (let x = n.parent; x; x = x.parent) if (ts.isFunctionLike(x) && (x as any).body) return x as ts.FunctionLikeDeclaration;
  return null;
};

type Site = { key: string; line: number; target: string | null; fn: ts.FunctionLikeDeclaration | null; sf: ts.SourceFile };
/** Every sanitizeMd call under ui/, and every other reference to the name (a failure). */
function census(): { sites: Site[]; failures: string[] } {
  const sites: Site[] = [], failures: string[] = [];
  for (const rel of sources()) {
    const text = fs.readFileSync(path.join(UI_ROOT, rel), "utf8");
    if (!text.includes("sanitizeMd")) continue;
    const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, rel.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
    const lineOf = (n: ts.Node) => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
    const visit = (n: ts.Node): void => {
      if (ts.isIdentifier(n) && n.text === "sanitizeMd") {
        const p = n.parent;
        const declared = (ts.isFunctionDeclaration(p) && p.name === n) || ts.isImportSpecifier(p) || ts.isExportSpecifier(p);
        if (ts.isCallExpression(p) && p.expression === n) {
          const fn = enclosingFn(p);
          const name = fn ? nameOf(fn) : null;
          // the variable the sanitized body lands in: `const clean = sanitizeMd(...)` or `clean = sanitizeMd(...)`
          const holder = p.parent;
          const target = ts.isVariableDeclaration(holder) && ts.isIdentifier(holder.name) ? holder.name.text
            : ts.isBinaryExpression(holder) && holder.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isIdentifier(holder.left) ? holder.left.text : null;
          sites.push({ key: rel + ":" + (name || "<anonymous at " + lineOf(p) + ">"), line: lineOf(p), target, fn, sf });
        } else if (!declared) {
          failures.push(rel + ":" + lineOf(n) + ": sanitizeMd referenced other than by a direct call (" + p.getText(sf).slice(0, 80) + ")");
        }
      } else if (ts.isPropertyAccessExpression(n) && n.name.text === "sanitizeMd") {
        failures.push(rel + ":" + lineOf(n) + ": sanitizeMd called through a property access");
      }
      ts.forEachChild(n, visit);
    };
    visit(sf);
  }
  return { sites, failures };
}

/** The calls of `callee` inside `fn`, each with its first argument's text and its position. */
function callsIn(fn: ts.Node, sf: ts.SourceFile, callee: string): { arg: string; pos: number }[] {
  const out: { arg: string; pos: number }[] = [];
  const visit = (n: ts.Node): void => {
    if (ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === callee) out.push({ arg: n.arguments[0] ? n.arguments[0].getText(sf) : "", pos: n.getStart(sf) });
    ts.forEachChild(n, visit);
  };
  visit(fn);
  return out;
}

test("the sanitizeMd census is derived from the tree and equals the renderer list both ways", () => {
  const { sites, failures } = census();
  assert.deepEqual(failures, [], "sanitizeMd is only ever called directly");
  assert.ok(sites.length >= Object.keys(RENDERERS).length, "the census found the call sites (a census that finds nothing proves nothing): " + sites.length);
  const derived = Array.from(new Set(sites.map((s) => s.key))).sort();
  assert.deepEqual(derived, Object.keys(RENDERERS).sort(),
    "every function that sanitizes authored markdown is listed in RENDERERS (a new one: cap its /file URLs with capAuthoredFileUrls, or disclose why not), and every listed one still does");
});

test("every capped renderer passes its sanitized body to capAuthoredFileUrls after the sanitize; every disclosed one makes the calls its reason names", () => {
  const { sites } = census();
  for (const s of sites) {
    const r = RENDERERS[s.key];
    assert.ok(r, s.key + " is listed");
    assert.ok(s.fn, s.key + ": the call sits in a function");
    if (r.kind === "capped") {
      assert.ok(s.target, s.key + ":" + s.line + ": the sanitized body is held in a variable the cap pass can be handed");
      const caps = callsIn(s.fn!, s.sf, "capAuthoredFileUrls").filter((c) => c.arg === s.target);
      const sanitizePos = callsIn(s.fn!, s.sf, "sanitizeMd").map((c) => c.pos);
      assert.ok(caps.length > 0, s.key + ":" + s.line + ": capAuthoredFileUrls(" + s.target + ") is called on the sanitized body");
      assert.ok(caps.some((c) => sanitizePos.some((p) => p < c.pos)), s.key + ": and after the sanitize, so the pass reads the sanitized DOM");
    } else {
      assert.ok(r.why.length > 40, s.key + ": the disclosure says why");
      for (const c of r.calls) assert.ok(callsIn(s.fn!, s.sf, c).length > 0, s.key + ": the disclosure rests on " + c + ", which the function calls");
      assert.equal(callsIn(s.fn!, s.sf, "capAuthoredFileUrls").length, 0, s.key + ": a disclosed renderer that now caps belongs in the capped rows");
    }
  }
});

/** Every anchor-creating call under ui/, by `file:function`, with the function's node. */
function anchorCensus(): { key: string; fn: ts.FunctionLikeDeclaration | null; sf: ts.SourceFile; line: number }[] {
  const out: { key: string; fn: ts.FunctionLikeDeclaration | null; sf: ts.SourceFile; line: number }[] = [];
  for (const rel of sources()) {
    const text = fs.readFileSync(path.join(UI_ROOT, rel), "utf8");
    if (!/createElement|\bel\(/.test(text)) continue;
    const sf = ts.createSourceFile(rel, text, ts.ScriptTarget.Latest, true, rel.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
    const visit = (n: ts.Node): void => {
      if (ts.isCallExpression(n) && n.arguments.length && ts.isStringLiteralLike(n.arguments[0]) && n.arguments[0].text.toLowerCase() === "a") {
        const e = n.expression;
        if ((ts.isPropertyAccessExpression(e) && e.name.text === "createElement") || (ts.isIdentifier(e) && e.text === "el")) {
          const fn = enclosingFn(n);
          const line = sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
          out.push({ key: rel + ":" + ((fn && nameOf(fn)) || "<anonymous at " + line + ">"), fn, sf, line });
        }
      }
      ts.forEachChild(n, visit);
    };
    visit(sf);
  }
  return out;
}

/** Whether `fn` writes an href: an `.href =` assignment or a setAttribute / setAttributeNS of an href. */
function setsHref(fn: ts.Node, sf: ts.SourceFile): boolean {
  let found = false;
  const visit = (n: ts.Node): void => {
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isPropertyAccessExpression(n.left) && n.left.name.text === "href") found = true;
    if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && /^setAttribute(NS)?$/.test(n.expression.name.text)
        && n.arguments.some((a) => ts.isStringLiteralLike(a) && /(^|:)href$/.test(a.text))) found = true;
    ts.forEachChild(n, visit);
  };
  visit(fn);
  return found;
}

test("every site under ui/ that creates an anchor is listed with where its href comes from, and a typed href is capped where it is minted", () => {
  const sites = anchorCensus();
  assert.ok(sites.length >= Object.keys(ANCHORS).length, "the census found the anchor sites (a census that finds nothing proves nothing): " + sites.length);
  assert.deepEqual(Array.from(new Set(sites.map((s) => s.key))).sort(), Object.keys(ANCHORS).sort(),
    "every function that creates an anchor is listed in ANCHORS (a new one: say where its href comes from, and cap a typed /file URL with withFileCap), and every listed one still does");
  for (const s of sites) {
    const a = ANCHORS[s.key];
    assert.ok(s.fn, s.key + ": the anchor is made inside a function");
    if (a.href === "typed") assert.ok(callsIn(s.fn!, s.sf, "withFileCap").length > 0, s.key + ": a typed href is run through withFileCap, so this origin's /file URL carries the cap");
    else if (a.href === "fileUrl") assert.ok(callsIn(s.fn!, s.sf, "fileUrl").length > 0, s.key + ": the href is built by fileUrl, which adds the cap");
    else if (a.href === "none") assert.ok(!setsHref(s.fn!, s.sf), s.key + ": listed as setting no href, and it sets none (one that does is listed by where it comes from)");
    else assert.ok(a.why.length > 30, s.key + ": says where its href comes from");
  }
});

// ── the pass itself, in a real browser ──────────────────────────────────────────────────────────────────
const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { applyMdConfig } from "./md-config";',
    'import { capAuthoredFileUrls } from "./authored-file-caps";',
    "applyMdConfig();",
    "(window as any).__render = (s: string) => { const b = sanitizeMd(marked.parse(s) as string); const n = capAuthoredFileUrls(b); return { html: b.innerHTML, n }; };",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, sourcefile: "cap-probe.ts", loader: "ts" } });
  return r.outputFiles[0].text;
}

const SID = "11111111-2222-3333-4444-555555555555";
const P = "/srv/notes-api/figs/a.png";
const Q = "path=" + encodeURIComponent(P) + "&amp;sid=" + SID;          // in an HTML attribute, & as the entity
const QM = "path=" + encodeURIComponent(P) + "&sid=" + SID;             // in a markdown destination
const XLINK = "http://www.w3.org/1999/xlink";
const MD = [
  "![md image](/file?" + QM + ")",
  "[md download](/file?" + QM + "&download=1)",
  '<img alt="html image" src="/file?' + Q + '">',
  '<img alt="srcset image" srcset="/file?' + Q + ' 1x, https://example.invalid/b.png 2x">',
  '<picture><source srcset="/remote/TESTHOST/file?' + Q + '"><img alt="picture fallback" src="/file?' + Q + '"></picture>',
  '<video poster="/file?' + Q + '" src="/file?path=%2Fsrv%2Fclip.mp4"><track src="/file?path=%2Fsrv%2Fcaps.vtt"></video>',
  '<audio src="/remote/TESTHOST/file?path=%2Fsrv%2Fa.mp3"></audio>',
  `<svg xmlns:xlink="${XLINK}" width="10" height="10"><image href="/file?${Q}"/><image xlink:href="/file?${Q}"/><a xlink:href="/file?${Q}&amp;download=1"><text>svg link</text></a></svg>`,
  '<a href="https://example.invalid/file?path=x">elsewhere</a> <a href="/files?path=x">files pane</a> <a href="/media/x.svg">media</a>',
  '<img alt="remote host" src="https://example.invalid/p.png">',
  "![absolute image](http://romp.test/file?" + QM + ")",
  "[absolute link](http://romp.test/file?" + QM + "&download=1)",
].join("\n\n");

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("capAuthoredFileUrls, in a browser, caps every /file URL an author wrote in every attribute it reads, and nothing else", async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    const probe = probeBundle();
    const key = randomBytes(32).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    const page = await browser.newPage();
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => errors.push(e.message));
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>chat</title><script src=/dist/probe.js></script>" });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probe });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/chat");
    type Ref = { where: string; url: string };
    const read = (withKey: boolean): Promise<{ n: number; refs: Ref[] }> => page.evaluate(([md, k, withK, xl]: [string, string, boolean, string]) => {
      (window as any).__rompPageKey = withK ? () => k : undefined;
      const r = (window as any).__render(md);
      const box = document.createElement("div"); box.innerHTML = r.html;
      const refs: { where: string; url: string }[] = [];
      box.querySelectorAll("*").forEach((el) => {
        for (const a of ["src", "srcset", "poster", "href"]) { const v = el.getAttribute(a); if (v) refs.push({ where: el.localName + "@" + a, url: v }); }
        const x = el.getAttributeNS(xl, "href"); if (x) refs.push({ where: el.localName + "@xlink:href", url: x });
      });
      return { n: r.n, refs };
    }, [MD, key, withKey, XLINK] as [string, string, boolean, string]);
    const bare = await read(false);
    assert.equal(bare.n, 0, "no key: nothing rewritten");
    assert.ok(bare.refs.every((r: Ref) => !/[?&]cap=/.test(r.url)), "no key: no cap anywhere");
    const got = await read(true);
    const urlsOf = (r: Ref) => r.where.endsWith("@srcset") ? r.url.split(",").map((c) => c.trim().split(/\s+/)[0]) : [r.url];
    let capped = 0;
    for (const r of got.refs) {
      for (const raw of urlsOf(r)) {
        const u = new URL(raw, "http://romp.test/chat");
        const m = /^\/remote\/([^/]+)\/file$/.exec(u.pathname);
        const isFile = u.origin === "http://romp.test" && (u.pathname === "/file" || !!m);
        if (!isFile) { assert.ok(!u.searchParams.has("cap"), r.where + ": not a /file URL, untouched: " + raw); continue; }
        const q = (n: string) => u.searchParams.getAll(n).find((v) => v !== "") || "";
        const want = capFor(key, m ? decodeURIComponent(m[1]) : "", q("path"), q("sid"));
        assert.equal(u.searchParams.get("cap"), want, r.where + ": the cap for the host, path and sid this URL names");
        capped++;
      }
    }
    const where = new Set(got.refs.filter((r: Ref) => /[?&]cap=/.test(r.url)).map((r: Ref) => r.where));
    for (const w of ["img@src", "a@href", "img@srcset", "source@srcset", "video@poster", "video@src", "track@src", "audio@src", "image@href", "image@xlink:href", "a@xlink:href"])
      assert.ok(where.has(w), "the pass capped a /file URL in " + w + ": " + JSON.stringify(Array.from(where)));
    assert.ok(capped >= 14, "all the authored /file URLs were capped: " + capped);
    const absolute = got.refs.filter((r: Ref) => r.url.startsWith("http://romp.test/file?") && /[?&]cap=/.test(r.url)).map((r: Ref) => r.where).sort();
    assert.deepEqual(absolute, ["a@href", "img@src"], "a /file URL written with its scheme is capped and stays absolute");
    assert.ok(got.refs.some((r: Ref) => r.url === "https://example.invalid/p.png"), "an image on another host is left as written");
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
});
