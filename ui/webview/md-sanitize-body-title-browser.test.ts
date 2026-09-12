// The body title's drop over the REAL DOMPurify (the vendored 3.4.10) in headless Chromium: what the hook writes, and what
// it does not. DOMPurify hands an uponSanitizeElement hook its live per-call ALLOWED_TAGS as `allowedTags` (purify.es.mjs
// `_sanitizeElements`: the variable itself, no copy), so a hook that sets a tag off there sets it off for every later element
// of the same call, and, under `setConfig`, for every later call until `clearConfig`. The first cut of dropBodyTitle
// (md-sanitize.ts) did exactly that for a body `<title>`, and a hook reading the set after it saw `title` false on the
// paragraphs after one (the PR's review, round 1). The hook now moves the element into a fresh fragment of its document and
// writes nothing in the set. Three tests, the first two with a recorder hook registered after the sanitizer's own, logging
// `allowedTags.title` and the set's identity at every node: the first sanitizes through sanitizeMd, as the chat and the viewer
// do, and reads the set unchanged behind a body title, the svg's title kept, the body titles gone with their text, and a title
// whose text reads as markup dropped without a throw (DOMPurify goes on to judge the moved node, and its `_forceRemove` throws
// on a parentless one: under the fragment the title has a parent for every branch after the hook); the second makes two
// consecutive calls with ONE config, the way the finding framed the hazard, and pins that the second call inherits nothing
// from the first: under a config argument, because DOMPurify rebuilds the set per call (the two calls' sets are different
// objects), and under `setConfig`, the one mode that keeps a set across calls (romp uses it nowhere; md-sanitize.test.ts pins
// the single sanitize call), because the hook no longer writes there. The third sanitizes under the html profile alone and
// under FORBID_TAGS with `title`, the two configs whose disallowed-tag branch force-removes the title after the hook, and
// reads no throw and the title gone with its text (the PR's review, round 2: the node's own remove(), the hook's second cut,
// had left the title parentless there, and 3.4.10's `_forceRemove` threw a TypeError over it). Skips with a stated reason when
// no playwright browser is installed (CI installs none). Synthetic markup only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");

// the sanitizer as its callers see it, and the module-global DOMPurify instance it installs its hooks on
const ENTRY = `
import DOMPurify from "dompurify";
import { MD_PURIFY, sanitizeMd, installMdSanitizeHooks } from "./md-sanitize";
(window as any).__romp = { DOMPurify, MD_PURIFY, sanitizeMd, installMdSanitizeHooks };
`;

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: ENTRY, resolveDir: UI, loader: "ts", sourcefile: "md-sanitize-body-title-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body><script src=/dist/sanitize.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** One recorder entry: the hook's lower-cased tagName, `allowedTags.title` as the recorder saw it, and which set object it was
 *  (an index into the sets seen so far, so two entries with one index shared one object). */
type Entry = { tag: string; title: boolean; set: number };
type Run = { out: string; log: Entry[] };

async function inPage(t: any, body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this machine; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const page = await browser.newPage({ viewport: { width: 600, height: 400 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
      if (u.pathname === "/dist/sanitize.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/");
    await page.waitForFunction(() => typeof (window as any).__romp === "object", null, { timeout: 10000 });
    // the sanitizer's hooks first (sanitizeMd installs them on its first call; installed here so the recorder is registered
    // AFTER them and reads the set as the hook left it), then the recorder
    await page.evaluate(() => {
      const w = window as any;
      w.__romp.installMdSanitizeHooks();
      const sets: unknown[] = [], log: Entry[] = [];
      w.__romp.DOMPurify.addHook("uponSanitizeElement", (_n: unknown, data: { tagName: string; allowedTags: Record<string, boolean> }) => {
        let i = sets.indexOf(data.allowedTags);
        if (i < 0) i = sets.push(data.allowedTags) - 1;
        log.push({ tag: data.tagName, title: data.allowedTags.title, set: i });
      });
      // one call under the recorder: its output and the entries it logged
      w.__run = (fn: () => string): Run => { log.length = 0; const out = fn(); return { out, log: log.slice() }; };
    });
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

const SVG = '<svg><title>S</title></svg>';
// the author's elements in walk order: DOMPurify's walk starts at its root, the parsed body, and visits text nodes and comments
// too. Every input below opens with a paragraph: a `<title>` at the very START of the string is parsed into the document's
// head, which the walk never reaches (WHOLE_DOCUMENT is off, the body alone comes back), so it meets no hook (`leading` below).
const elements = (r: Run) => r.log.filter((e) => !e.tag.startsWith("#") && e.tag !== "body");

test("sanitizeMd: a body <title> goes with its text and the svg's stays, the set the hook is handed reads `title` true at every node of the call (the hook writes nothing there), and a title whose text reads as markup is dropped without a throw", { timeout: 60000 }, async (t) => {
  await inPage(t, async (page, errors) => {
    const r = await page.evaluate(([svg]: [string]) => {
      const w = window as any;
      const san = (html: string) => w.__romp.sanitizeMd(html).innerHTML as string;
      try {
        return {
          mixed: w.__run(() => san('<p>a</p><title>T1</title><p>b</p>' + svg + '<p>c</p><title>T2</title><p>d</p>')) as Run,
          markup: w.__run(() => san('<p>x</p><title>a <b> c &lt;y&gt; <!-- z --></title><p>z</p>')) as Run,
          nested: w.__run(() => san('<div><title>D</title><p>k</p></div><table><tr><td>a <title>t</title> b</td></tr></table>')) as Run,
          leading: w.__run(() => san('<title>H</title><p>a</p>')) as Run,
        };
      } catch (e) { return { error: String(e) }; }
    }, [SVG]);
    assert.equal((r as { error?: string }).error, undefined, "no sanitize threw: " + (r as { error?: string }).error);
    const { mixed, markup, nested, leading } = r as { mixed: Run; markup: Run; nested: Run; leading: Run };
    assert.equal(mixed.out, '<p>a</p><p>b</p>' + SVG + '<p>c</p><p>d</p>', "both body titles are gone with their text; the svg's title stays; the paragraphs around them stay");
    assert.deepEqual(elements(mixed).map((e) => e.tag), ["p", "title", "p", "svg", "title", "p", "title", "p"], "the hook chain ran for every element, the removed titles included (the recorder runs after the drop)");
    assert.deepEqual(elements(mixed).filter((e) => e.title !== true).map((e) => e.tag), [], "`title` reads true in the set at every element: the hook wrote nothing there (before: false at the first body title and on every element after it, until the svg's title set it back on, then false again from the second)");
    assert.deepEqual(new Set(mixed.log.map((e) => e.set)).size, 1, "one call, one set object");
    assert.equal(markup.out, '<p>x</p><p>z</p>', "a title whose text reads as markup goes with its text: the markup guard reads the escaped innerHTML and fires no force-remove, and one would detach from the fragment anyway");
    assert.equal(nested.out, '<div><p>k</p></div><table><tbody><tr><td>a  b</td></tr></tbody></table>', "a title inside a div and one inline in a cell go the same way, the text beside them kept");
    assert.equal(leading.out, '<p>a</p>', "a title at the very start of the string: gone too, by the parser (it lands in the head, which never comes back)");
    assert.deepEqual(elements(leading).map((e) => e.tag), ["p"], "and the walk never met it: no hook saw a title");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("two consecutive sanitize calls with ONE config: the second inherits nothing from the first's drop, with a config argument (DOMPurify rebuilds the set per call) and under setConfig (one set across calls: the hook no longer writes there)", { timeout: 60000 }, async (t) => {
  await inPage(t, async (page, errors) => {
    const r = await page.evaluate(([svg]: [string]) => {
      const w = window as any, D = w.__romp.DOMPurify;
      const cfg = { ...w.__romp.MD_PURIFY };
      const one = w.__run(() => D.sanitize('<p>a</p><title>T</title>', cfg)) as Run;
      const two = w.__run(() => D.sanitize('<p>b</p>' + svg, cfg)) as Run;
      const fresh = w.__run(() => D.sanitize('<p>b</p>' + svg, { ...w.__romp.MD_PURIFY })) as Run;
      let pinnedOne: Run, pinnedTwo: Run;
      try {
        D.setConfig({ ...w.__romp.MD_PURIFY });
        pinnedOne = w.__run(() => D.sanitize('<p>a</p><title>T</title>')) as Run;
        pinnedTwo = w.__run(() => D.sanitize('<p>b</p>' + svg)) as Run;
      } finally { D.clearConfig(); }
      const after = w.__run(() => D.sanitize('<p>b</p>' + svg, { ...w.__romp.MD_PURIFY })) as Run;
      return { one, two, fresh, pinnedOne, pinnedTwo, after };
    }, [SVG]);
    const kept = '<p>b</p>' + SVG;
    // a config argument: one object reused, two calls
    assert.equal(r.one.out, '<p>a</p>', "call 1 drops the body title");
    assert.deepEqual(elements(r.one).map((e) => e.tag), ["p", "title"], "and the hook met it, the last element of the walk");
    assert.equal(r.two.out, kept, "call 2, the same config object: the paragraph and the svg's title, as a fresh config gives them");
    assert.equal(r.fresh.out, kept);
    assert.deepEqual(elements(r.two).filter((e) => e.title !== true).map((e) => e.tag), [], "call 2 starts with `title` true and keeps it");
    assert.notEqual(r.one.log[0].set, r.two.log[0].set, "the two calls' sets are different objects: DOMPurify rebuilds ALLOWED_TAGS on every call that carries a config, which is why the first cut's write reached no later call");
    // setConfig: the one mode that keeps one set across calls
    assert.equal(r.pinnedOne.out, '<p>a</p>');
    assert.deepEqual(elements(r.pinnedOne).map((e) => e.tag), ["p", "title"]);
    assert.equal(r.pinnedTwo.out, kept);
    assert.equal(r.pinnedOne.log[0].set, r.pinnedTwo.log[0].set, "under setConfig the two calls share one set object");
    assert.deepEqual(elements(r.pinnedTwo).filter((e) => e.title !== true).map((e) => e.tag), [], "and the second call reads `title` true at every element: nothing inherited (before: false at its first element, the first call's write standing in the shared set)");
    assert.equal(r.after.out, kept, "clearConfig: a config argument is read again");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("under a profile where `title` is NOT allowed (html alone: `title` is in DOMPurify's svg list, not its html list) and under FORBID_TAGS with `title` added, the body title goes with its text and nothing throws: DOMPurify's own disallowed-tag branch force-removes the title the hook moved into a fragment (before: the hook's remove() left it parentless, and 3.4.10's _forceRemove threw a TypeError over it, so the hook was safe only while `title` stayed allowed)", { timeout: 60000 }, async (t) => {
  await inPage(t, async (page, errors) => {
    const r = await page.evaluate(([svg]: [string]) => {
      const w = window as any, D = w.__romp.DOMPurify, P = w.__romp.MD_PURIFY;
      const input = '<p>a</p><title>T</title><p>b</p>' + svg + '<p>c</p>';
      const run = (cfg: unknown): Run | { error: string } => { try { return w.__run(() => D.sanitize(input, cfg)) as Run; } catch (e) { return { error: String(e) }; } };
      return {
        htmlOnly: run({ ...P, USE_PROFILES: { html: true } }),
        forbidden: run({ ...P, FORBID_TAGS: [...P.FORBID_TAGS, "title"] }),
        markup: run({ ...P, USE_PROFILES: { html: true }, RETURN_DOM: false }),   // the same config over the same input: the string path
      };
    }, [SVG]);
    for (const [name, res] of Object.entries(r) as Array<[string, { error?: string }]>) assert.equal(res.error, undefined, name + ": the sanitize threw: " + res.error);
    const { htmlOnly, forbidden } = r as { htmlOnly: Run; forbidden: Run };
    assert.equal(htmlOnly.out, '<p>a</p><p>b</p><p>c</p>', "html alone: the body title is gone with its text (DOMPurify's own removal, from the fragment), and the svg goes whole with the profile");
    assert.deepEqual(elements(htmlOnly).map((e) => e.tag), ["p", "title", "p", "svg", "p"], "the walk went on past the moved title to every later element (the svg's own title went with the svg, unvisited)");
    assert.deepEqual(elements(htmlOnly).filter((e) => e.title).map((e) => e.tag), [], "`title` is off the allowed set at every element of the call: the config, not the hook, decides");
    assert.equal(forbidden.out, '<p>a</p><p>b</p><svg></svg><p>c</p>', "title forbidden: the body title is gone with its text, and the svg's title too, by FORBID_TAGS (title is in DOMPurify's FORBID_CONTENTS, so its text goes with it), the svg itself kept");
    assert.deepEqual(elements(forbidden).map((e) => e.tag), ["p", "title", "p", "svg", "title", "p"], "the walk met both titles and went on");
    assert.deepEqual(elements(forbidden).filter((e) => e.title !== true).map((e) => e.tag), [], "and `title` reads true in the allowed set throughout: FORBID_TAGS is a set the hook is never handed, which is why the hook cannot decide by allowedTags alone");
    assert.deepEqual(errors, [], "no page error");
  });
});
