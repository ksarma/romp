// The passage-comment mapping over the REAL shared sanitizer in headless Chromium (plans/markdown-viewer.md,
// Slice 1). The node suite (anchor-map.test.ts) drives anchor-map.ts over marked's output with no DOMPurify, on
// the ground that the mapping reads only text nodes and the sanitizer keeps them; this leg pins the one exception,
// which that suite cannot model. DOMPurify removes an element in its FORBID_CONTENTS set (script, style, iframe,
// noscript, the MathML family) together with its text; every other tag MD_PURIFY forbids (textarea, button, the
// rest of the form family) is unwrapped and its text stays. marked lexes a mid-line `<style>` or `<script>` body as
// inline text, so the mapping's rebuilt paragraph has that text and the viewer's DOM does not: mapRenderedSelection
// must refuse it as a rendered-text mismatch (fail closed, pointing at the Raw view), never anchor it to the wrong
// offsets. A `<textarea>` written mid-line and a plain paragraph are the controls: both map, so the refusal is the
// text drop's and nothing else's. Adopted exactly as mdBlock adopts it (file-view.ts: the sanitized body's children
// replace the box's). Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented note.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MD_FORBID_TAGS } from "./md-sanitize";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");

// Four paragraphs; the word "hidden" is selected in each of the first three, "Plain" in the last.
const NOTE = [
  "# Report",
  "",
  "The <style>.x{}</style> hidden style para.",
  "",
  "The <script>1</script> hidden script para.",
  "",
  "The <textarea>typed</textarea> hidden textarea para.",
  "",
  "Plain para.",
  "",
].join("\n");
const WORDS = ["hidden style", "hidden script", "hidden textarea", "Plain"];

test("the profile forbids style and textarea; the difference in what happens to their text is DOMPurify's FORBID_CONTENTS, not the profile", () => {
  assert.ok(MD_FORBID_TAGS.includes("style"));
  assert.ok(MD_FORBID_TAGS.includes("textarea"));
  assert.ok(!MD_FORBID_TAGS.includes("script"), "script is not in the profile at all: the html profile never allowed it, and its text went before this slice");
});

/** marked with the viewer's options (file-view.ts; the fixture has no strikethrough, so its del tokenizer plays no part),
 *  the real md-sanitize.ts and the real anchor-map.ts, bundled for a page. */
function bundleProbe(): string {
  const esbuild = requireCjs("esbuild");
  const contents = [
    'import { marked } from "marked";',
    'import { applyMdConfig } from "./md-config";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { mapRenderedSelection } from "./anchor-map";',
    "applyMdConfig();",
    "(window as any).__probe = (source: string, words: string[]) => {",
    "  const body = document.createElement('div');",
    "  const before = document.createElement('div'); before.textContent = 'Rendered · Raw';",
    "  const box = document.createElement('div'); box.className = 'fileview-md';",
    "  box.replaceChildren(...Array.from(sanitizeMd(marked.parse(source) as string).childNodes));",   // mdBlock, file-view.ts
    "  body.append(before, box); document.body.append(body);",
    "  const paras = Array.from(box.querySelectorAll('p'));",
    "  return paras.map((p, i) => {",
    "    const word = words[i].split(' ')[0];",
    "    const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);",
    "    let tn: Text | null = null, at = -1;",
    "    for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) { at = n.data.indexOf(word); if (at >= 0) { tn = n; break; } }",
    "    const sel = { anchorNode: tn, anchorOffset: at, focusNode: tn, focusOffset: at + word.length, isCollapsed: false };",
    "    return { html: p.outerHTML, text: p.textContent, map: mapRenderedSelection(sel, box, source) };",
    "  });",
    "};",
  ].join("\n");
  const r = esbuild.buildSync({
    stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "md-sanitize-anchor-map-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body><script src=/probe.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("a mid-line <style> or <script> loses its text under the sanitizer and the mapping refuses the paragraph as a rendered-text mismatch; a mid-line <textarea> keeps its text and maps, as does a plain paragraph", { timeout: 60000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const probeJs = bundleProbe();
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/");

    type Row = { html: string; text: string; map: any };
    const rows: Row[] = await page.evaluate(([source, words]: [string, string[]]) => (window as any).__probe(source, words), [NOTE, WORDS] as [string, string[]]);
    assert.equal(rows.length, 4, "four paragraphs rendered: " + JSON.stringify(rows.map((r) => r.html)));
    const [style, script, textarea, plain] = rows;
    const MISMATCH = /a block whose rendered text does not match the file/;

    // 1. style: the element and its text are gone (FORBID_CONTENTS), and the mapping refuses rather than anchoring
    assert.equal(style.html, "<p>The  hidden style para.</p>", "the <style> went with its text");
    assert.equal(style.map.ok, false, "refused: " + JSON.stringify(style.map));
    assert.match(style.map.reason, MISMATCH);
    assert.match(style.map.reason, /Raw view/, "the refusal points at the Raw view");
    assert.equal(style.map.rawHasQuote, true, "the selected word is in the source, so Raw can preselect it");
    assert.deepEqual(style.map.rawRange, { start: NOTE.indexOf("hidden style"), end: NOTE.indexOf("hidden style") + "hidden".length });
    assert.equal(style.map.blockStartOffset, NOTE.indexOf("The <style>"));
    assert.equal(style.map.blockStartLine, 2);

    // 2. script: the same drop and the same refusal (this one predates the slice: the html profile never had script)
    assert.equal(script.html, "<p>The  hidden script para.</p>", "the <script> went with its text");
    assert.equal(script.map.ok, false, "refused: " + JSON.stringify(script.map));
    assert.match(script.map.reason, MISMATCH);
    assert.equal(script.map.blockStartOffset, NOTE.indexOf("The <script>"));

    // 3. textarea: forbidden but not FORBID_CONTENTS, so its text is unwrapped into the paragraph and the mapping
    //    sees exactly the text marked lexed; the word maps to its own offsets
    assert.equal(textarea.html, "<p>The typed hidden textarea para.</p>", "the <textarea> was unwrapped, its text kept");
    assert.equal(textarea.map.ok, true, "mapped: " + JSON.stringify(textarea.map));
    assert.equal(textarea.map.quote, "hidden");
    assert.deepEqual(textarea.map.range, { start: NOTE.indexOf("hidden textarea"), end: NOTE.indexOf("hidden textarea") + "hidden".length });

    // 4. the plain control
    assert.equal(plain.html, "<p>Plain para.</p>");
    assert.equal(plain.map.ok, true, "mapped: " + JSON.stringify(plain.map));
    assert.equal(plain.map.quote, "Plain");
    assert.deepEqual(plain.map.range, { start: NOTE.indexOf("Plain"), end: NOTE.indexOf("Plain") + "Plain".length });

    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
});
