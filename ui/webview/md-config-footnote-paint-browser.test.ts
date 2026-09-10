// A footnote definition's body is a paragraph inside its div (md-config.ts footnoteDef, the Slice 4 review, round 10), over the
// REAL bundle in headless Chromium: marked with the one configuration, the sanitizer and paintRendered, the DOM built as the
// viewer's mdBlock builds it, the page under the whole feed sheet. Before this the body rendered as inline content directly under
// `div.md-footnote`, and the Rendered paint (anchor-map.ts skipBlockWs) skipped each whitespace-only text node under the DIV as
// white space between blocks: a highlight from the paragraph before `[^1]: **a** *b*` to the paragraph after painted `a` and `b`
// and left the rendered space between them bare, a 4 px gap between two ring ends (4.09 x 15 px on this page), two links or two
// code spans in a definition likewise, where main, which rendered the line as a plain paragraph, painted the space (8 px wide).
// The same round retired that container reading in anchor-map.ts, so the paragraph stands on GitHub's shape (`li > p`) and the
// legs hold it whichever way the paint reads a DIV.
// Two legs: the gaps are gone and the spaces are marks of their own width, the layout unmoved by the paint; and the inner
// paragraph adds no spacing of its own (`.md .md-footnote p, .fileview-md .md-footnote p { margin: 0 }` in both sheets), so the
// footnote's box is the paragraph's, as the div's box was. Skips LOUDLY without a playwright browser (CI installs none).
// Synthetic prose, hosts under .test.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8").replace(/@import[^;]*;/g, "");   // the KaTeX import: fonts the page does not need

/** marked with the viewer's grammar, the sanitizer and the paint, bundled as the webview build bundles them. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { marked } from "marked";\nimport { applyMdConfig } from "./md-config";\nimport { sanitizeMd } from "./md-sanitize";\n'
        + 'import { paintRendered } from "./anchor-map";\napplyMdConfig();\n(window as any).__romp = { marked, sanitizeMd, paintRendered };\n',
      resolveDir: UI, loader: "ts", sourcefile: "footnote-paint-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${FEED}
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; }
#md { width: 800px; }</style></head><body><div class="fileview-md" id="md"></div><script src="/dist/probe.js"></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** The page's own helpers: the viewer's render (mdBlock's shape: the sanitized body's children adopted), the whitespace-only text
 *  nodes with their rendered boxes and whether a mark holds them, the top-level layout, the footnote's box against its
 *  paragraph's, and the paint from the paragraph before to the paragraph after (the panel's gesture). */
const HELPERS = `
window.__render = (src) => { const md = document.getElementById("md"); md.replaceChildren(...Array.from(window.__romp.sanitizeMd(window.__romp.marked.parse(src)).childNodes)); return md.innerHTML; };
window.__ws = (under) => { const root = under ? document.querySelector(under) : document.getElementById("md"); const out = []; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { if (!n.data.length || n.data.trim() !== "") continue; const r = document.createRange(); r.selectNodeContents(n); const b = r.getBoundingClientRect(); const p = n.parentElement;
    out.push({ parent: p.tagName + (p.className ? "." + p.className : ""), data: n.data, w: Math.round(b.width * 100) / 100, h: Math.round(b.height * 100) / 100, inMark: !!p.closest("mark") }); }
  return out; };
window.__layout = () => { const md = document.getElementById("md"); return Array.from(md.children).map((c) => { const b = c.getBoundingClientRect(); return [c.tagName, Math.round(b.top * 100) / 100, Math.round(b.height * 100) / 100]; }); };
window.__footnote = () => { const fn = document.querySelector("#md .md-footnote"); if (!fn) return null; const p = fn.firstElementChild; const cs = getComputedStyle(p);
  return { children: Array.from(fn.childNodes).map((n) => n.nodeType === 1 ? n.tagName : JSON.stringify(n.data)), divH: Math.round(fn.getBoundingClientRect().height * 100) / 100, pH: Math.round(p.getBoundingClientRect().height * 100) / 100,
    pMargin: [cs.marginTop, cs.marginBottom], divMargin: [getComputedStyle(fn).marginTop, getComputedStyle(fn).marginBottom], divFont: getComputedStyle(fn).fontSize, pFont: cs.fontSize }; };
window.__paint = (src) => { const md = document.getElementById("md"); const range = { start: src.indexOf("Intro para."), end: src.indexOf("After para.") + "After para.".length };
  const marks = window.__romp.paintRendered(md, src, range, "fc-hl", { id: "c1" }) || [];
  return marks.map((m) => { const b = m.getBoundingClientRect(); const p = m.parentElement; return { parent: p.tagName + (p.className ? "." + p.className : ""), text: m.textContent, w: Math.round(b.width * 100) / 100, h: Math.round(b.height * 100) / 100 }; }); };
`;

async function inBrowser(t: any, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle() + "\n" + HELPERS;
    const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
    page.on("pageerror", (e: Error) => errors.push(String(e.message || e)));
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__paint);
    await body(page);
    assert.deepEqual(errors, [], "no page errors");
  } finally { await browser.close(); }
}

type Ws = { parent: string; data: string; w: number; h: number; inMark: boolean };
type Mark = { parent: string; text: string; w: number; h: number };
type Scene = { html: string; before: Array<[string, number, number]>; rendered: Ws[]; marks: Mark[]; after: Array<[string, number, number]>; gaps: Ws[] };
const doc = (body: string): string => "Intro para.\n\n" + body + "\n\nAfter para.\n";
/** Render, read the rendered whitespace-only nodes under the footnote, paint, read the layout on both sides and the gaps: the
 *  whitespace-only text nodes with a nonzero rendered width that no mark holds. */
const SCENE = ({ src, under }: { src: string; under: string }): Scene => {
  const w = window as any;
  const html = w.__render(src); const before = w.__layout(); const rendered = w.__ws(under).filter((n: Ws) => n.w > 0);
  const marks = w.__paint(src); const after = w.__layout(); const gaps = w.__ws(under).filter((n: Ws) => n.w > 0 && !n.inMark);
  return { html, before, rendered, marks, after, gaps };
};

test("a highlight across a footnote definition paints every rendered space between the body's inline elements as a mark of the space's own width, leaves no gap, and moves no block; a paragraph's space paints the same", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (page) => {
    const shapes: Array<[string, string, number]> = [
      ["strong and em", "x[^1]\n\n[^1]: **a** *b*", 2],
      ["two links", "x[^1]\n\n[^1]: See [the RFC](https://example.test/a) [and the spec](https://example.test/b).", 1],
      ["two code spans", "x[^1]\n\n[^1]: `foo` `bar`", 2],
      ["an orphan definition", "[^x]: **a** *b*", 2],
      ["inside a blockquote", "> x[^1]\n>\n> [^1]: **a** *b*", 2],
    ];
    for (const [name, body, spaces] of shapes) {
      const src = doc(body);
      const s: Scene = await page.evaluate(SCENE, { src, under: "#md .md-footnote" });
      assert.ok(s.html.includes('<div class="md-footnote"'), name + ": the definition rendered: " + s.html);
      assert.equal(s.rendered.length, spaces, name + ": the body's rendered spaces before the paint: " + JSON.stringify(s.rendered));
      assert.deepEqual(s.gaps, [], name + ": no rendered whitespace-only text node under the footnote is left outside a mark (marks: " + JSON.stringify(s.marks) + ")");
      const wsMarks = s.marks.filter((m) => m.text.length && !m.text.trim() && m.parent === "P");
      assert.equal(wsMarks.length, spaces, name + ": each space is a mark of its own under the footnote's paragraph: " + JSON.stringify(s.marks));
      for (const m of wsMarks) assert.ok(m.w >= 3 && m.w <= 16 && m.h >= 10, name + ": the space's mark has the width of a rendered space, not an empty box: " + JSON.stringify(m));
      assert.equal(s.marks.filter((m) => m.parent.startsWith("DIV")).length, 0, name + ": no mark stands directly under the div");
      assert.deepEqual(s.after, s.before, name + ": the paint moved no block");
    }
    // the control: the same body as a paragraph paints its space the same way
    const src = doc("**a** *b*");
    const c: Scene = await page.evaluate(SCENE, { src, under: "#md" });
    const ws = c.marks.filter((m) => !m.text.trim());
    assert.equal(ws.length, 1, "the paragraph's space is a mark: " + JSON.stringify(c.marks));
    assert.ok(ws[0].w >= 3 && ws[0].parent === "P");
    assert.deepEqual(c.gaps, []);
  });
});

test("the footnote's paragraph adds no spacing of its own: zero margins from both sheets' rule, the div's box the paragraph's, the div's own margin and the reduced size kept", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (page) => {
    for (const body of ["x[^1]\n\n[^1]: **a** *b*", "x[^1]\n\n[^1]: The footnote definition text.", "[^x]: an orphan"]) {
      const f = await page.evaluate((src: string) => { (window as any).__render(src); return (window as any).__footnote(); }, doc(body));
      assert.ok(f, "the definition rendered");
      assert.deepEqual(f.children, ["P"], "one paragraph and nothing else directly under the div");
      assert.deepEqual(f.pMargin, ["0px", "0px"], "the paragraph's margins are zero (the sheet's `.fileview-md p` gives 0.5em otherwise)");
      assert.equal(f.divH, f.pH, "the div's box is the paragraph's: no spacing added inside the rail");
      assert.notEqual(f.divMargin[0], "0px", "the div keeps the footnote's own spacing");
      assert.equal(f.pFont, f.divFont, "the paragraph inherits the footnote's reduced size");
    }
    // the sheets: the rule is byte-equal in both (fileview-parity.test.ts pins it too; this reads the text the page loaded)
    const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
    const rule = /\n\.md \.md-footnote p, \.fileview-md \.md-footnote p \{ margin: 0; \}/;
    assert.match(FEED, rule); assert.match(STYLES, rule);
  });
});
