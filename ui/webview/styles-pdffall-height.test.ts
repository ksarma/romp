// The PDF frame's COLUMN carries the frame's height (plans/file-review.md Slice 4, decision 12: the browser's
// frame is the PDF body with the Comments panel closed — every PDF open's first state — and what every failed
// pages attempt leaves showing). pdfBlock (file-view.ts) mounts div.fileview-pdffall > iframe.fileview-frame as the
// body's child, and the sheets size the frame with `height: 100%`. That percentage resolves against the COLUMN, and
// the column sits in .fileview-body, a plain overflow block, not a flex container (its own comment in the sheet; the
// .fileview-editor precedent of 2026-08-17, file-edit.test.ts) — so the column needs a height of its own,
// `.fileview-pdffall { height: 100% }`, or it is auto-height, the frame's percentage has nothing to resolve against,
// and the frame renders at the UA's default of 150px inside a 700px body. Round 1 of the Slice 4 review widened the
// column from the fallback-only case to every PDF open without a pin on that rule: dropping `height: 100%` from BOTH
// sheets left every test green (fileview-parity.test.ts pins the two sheets byte-equal, so a symmetric deletion
// passes it; file-view.test.ts pins the FRAME's `height: 100%`, which stays true while the frame collapses).
//
// Two legs. The source leg resolves `height` along the chain file-view.ts actually builds, in each sheet on its own
// (the chat page loads styles.css alone and the feed page feed.css alone), and pins the shape the collapse turns on.
// The chromium leg loads each FULL sheet around the real chain and MEASURES: the column fills the body, the frame
// fills the column less any notice above it, and the notice never pushes the frame past the body — with the Comments
// panel closed, under the fallback's notice, and with the panel's aside beside the body. It skips BY NAME without
// playwright's chromium (CI installs none; `npx playwright install chromium` in vscode-extension). Static layout only:
// no timers, no chunk, no bytes — a blank frame in the viewer's own chrome.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const PKG = process.cwd();                                   // vscode-extension, where npm test runs
const read = (f: string) => fs.readFileSync(path.resolve(PKG, "..", "ui", "webview", f), "utf8");
const VIEW = read("file-view.ts");
const SHEETS: Array<[string, string]> = [["styles.css", read("styles.css")], ["feed.css", read("feed.css")]];
const UA_IFRAME_DEFAULT = 150;   // the height an iframe takes when its percentage has nothing to resolve against

// ── the chain, as file-view.ts builds it (pinned so the model cannot outlive the DOM) ──
const COLUMN = "div#romp-fileview > div.fileview > div.fileview-main > div.fileview-body > div.fileview-pdffall";
const FRAME = COLUMN + " > iframe.fileview-frame";
const BODY = "div#romp-fileview > div.fileview > div.fileview-main > div.fileview-body";
const CHAIN_CLASSES = ["fileview", "fileview-main", "fileview-body", "fileview-pdffall", "fileview-frame"];

test("file-view.ts mounts the frame in its column as the body's child, and the fallback's notice goes INTO the column, above the frame", () => {
  const pdfFn = VIEW.split("function pdfBlock")[1].split("/** Bind the pane's WS poster")[0];
  assert.match(pdfFn, /const col = el\("div", "fileview-pdffall"\);\n\s*const frame = el\("iframe", "fileview-frame"\) as HTMLIFrameElement;/);
  assert.match(pdfFn, /col\.appendChild\(frame\);\n\s*return col;/, "the column is what pdfBlock returns");
  // the panel-closed arm: the column is the body's only child — the state every PDF open starts in
  assert.match(VIEW, /const shown = isPdf \? pdfBlock\(objUrl, path\) : imgBlock\(objUrl, path, imgFailed\);\n\s*body\.replaceChildren\(shown\);/);
  // the pages attempt's fallback: the notice is prepended INTO the column (a kept frame's, or a fresh one's), never
  // beside it in the body — so the column's own layout is what keeps the frame inside the body under a notice
  assert.match(VIEW, /col\.prepend\(note\);/);
  assert.match(VIEW, /const fall = pdfBlock\(url, path\);[^\n]*\n\s*fall\.prepend\(note\);/);
  assert.match(VIEW, /body\.replaceChildren\(fall\);/);
});

// ── a small cascade resolver for one property along one chain: class/id/tag compounds joined by descendant or child
// combinators — the grammar the viewer's layout rules use. A selector using anything else is skipped when it names
// none of the chain's classes and FAILS LOUDLY when it does, so a :hover / :has / [attr] rule on the chain cannot
// slip past unmodelled. (The styles-pdf-page-err.test.ts resolver, with a word-boundary class match.) ──
type Node = { tag: string; id: string | null; classes: string[] };
type Compound = { tag: string | null; id: string | null; classes: string[] };
type Rule = { head: string; selector: string; parts: Compound[]; combinators: string[]; spec: number; order: number; value: string; conditional: string | null };
const strip = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");
const chainOf = (s: string): Node[] => s.split(">").map((p) => {
  const m = /^([a-z][\w-]*)(#[\w-]+)?((?:\.[\w-]+)*)$/.exec(p.trim());
  assert.ok(m, "a chain element this test cannot read: " + p);
  return { tag: m![1], id: m![2] ? m![2].slice(1) : null, classes: m![3] ? m![3].slice(1).split(".") : [] };
});
const SIMPLE = /^(?:[a-z][\w-]*)?(?:[.#][\w-]+)*$/i;
const namesClass = (selector: string, c: string) => new RegExp("\\." + c + "(?![\\w-])").test(selector);
function compoundOf(s: string): Compound {
  const c: Compound = { tag: null, id: null, classes: [] };
  const t = /^[a-z][\w-]*/i.exec(s);
  if (t) c.tag = t[0].toLowerCase();
  for (const m of s.matchAll(/([.#])([\w-]+)/g)) { if (m[1] === ".") c.classes.push(m[2]); else c.id = m[2]; }
  return c;
}
function splitList(sel: string): string[] {
  const out: string[] = []; let depth = 0, cur = "";
  for (const ch of sel) {
    if (ch === "(") depth++; else if (ch === ")") depth--;
    if (ch === "," && depth === 0) { out.push(cur); cur = ""; } else cur += ch;
  }
  out.push(cur);
  return out.map((x) => x.trim()).filter(Boolean);
}
/** every rule that sets `prop`, with the rules under @media/@container/@supports remembered as conditional */
function rulesFor(css: string, prop: string, chainClasses: string[]): Rule[] {
  const rules: Rule[] = []; let order = 0;
  const walk = (s: string, cond: string | null) => {
    let i = 0;
    while (i < s.length) {
      if (/\s/.test(s[i])) { i++; continue; }
      const open = s.indexOf("{", i);
      assert.ok(open > i, "a rule without braces at `" + s.slice(i, i + 40) + "`");
      const head = s.slice(i, open).trim();
      let depth = 0, j = open;
      for (; j < s.length; j++) { if (s[j] === "{") depth++; else if (s[j] === "}" && --depth === 0) break; }
      assert.ok(j < s.length, "unbalanced braces after `" + head + "`");
      const body = s.slice(open + 1, j); i = j + 1;
      if (head.startsWith("@")) {
        if (/^@(media|container|supports)\b/.test(head)) walk(body, cond ? cond + " " + head : head);
        continue;
      }
      order++;
      let value: string | null = null;
      for (const d of body.split(";")) {
        const colon = d.indexOf(":"); if (colon < 0) continue;
        if (d.slice(0, colon).trim().toLowerCase() !== prop) continue;
        value = d.slice(colon + 1).trim();
        assert.doesNotMatch(value, /!important/, "`" + head + "` sets " + prop + " !important; this resolver ranks by specificity");
      }
      if (value === null) continue;
      for (const selector of splitList(head)) {
        const toks = selector.replace(/\s*>\s*/g, " > ").split(/\s+/);
        const parts: Compound[] = []; const combinators: string[] = []; let pending: string | null = null; let simple = true;
        for (const tok of toks) {
          if (tok === ">") { pending = ">"; continue; }
          if (!SIMPLE.test(tok)) { simple = false; break; }
          if (parts.length) combinators.push(pending || " ");
          parts.push(compoundOf(tok)); pending = null;
        }
        if (!simple || pending !== null) {
          assert.ok(!chainClasses.some((c) => namesClass(selector, c)),
            "`" + selector + "` sets " + prop + " on a class of the chain with selector syntax this resolver does not model; extend it");
          continue;
        }
        const spec = parts.reduce((n, p) => n + (p.id ? 10000 : 0) + p.classes.length * 100 + (p.tag ? 1 : 0), 0);
        rules.push({ head, selector, parts, combinators, spec, order, value, conditional: cond });
      }
    }
  };
  walk(strip(css), null);
  return rules;
}
const matchCompound = (c: Compound, n: Node) => (c.tag === null || c.tag === n.tag) && (c.id === null || c.id === n.id) && c.classes.every((k) => n.classes.includes(k));
function matchAt(r: Rule, chain: Node[], i: number, k: number): boolean {
  if (!matchCompound(r.parts[k], chain[i])) return false;
  if (k === 0) return true;
  if (r.combinators[k - 1] === ">") return i > 0 && matchAt(r, chain, i - 1, k - 1);
  for (let j = i - 1; j >= 0; j--) if (matchAt(r, chain, j, k - 1)) return true;
  return false;
}
/** the rule that wins `prop` on the chain's leaf: highest specificity, then latest in source */
function winner(rules: Rule[], chain: Node[]): Rule | null {
  let best: Rule | null = null;
  for (const r of rules) {
    if (!matchAt(r, chain, chain.length - 1, r.parts.length - 1)) continue;
    assert.equal(r.conditional, null, "`" + r.selector + "` sizes the leaf under " + r.conditional + "; this resolver models at-rest rules only");
    if (!best || r.spec > best.spec || (r.spec === best.spec && r.order > best.order)) best = r;
  }
  return best;
}
function ruleOf(css: string, head: string): string {
  const at = css.indexOf(head);
  assert.ok(at >= 0, head + " present");
  return css.slice(at, css.indexOf("}", at) + 1);
}

for (const [name, css] of SHEETS) {
  test(name + ": the column's height, resolved along the viewer's chain, is 100% — the height the frame's own 100% resolves against", () => {
    const heights = rulesFor(css, "height", CHAIN_CLASSES);
    const col = winner(heights, chainOf(COLUMN));
    assert.ok(col, "some rule sizes the column; without one it is auto-height and the frame falls to the UA's " + UA_IFRAME_DEFAULT + "px");
    assert.equal(col!.selector, ".fileview-pdffall");
    assert.equal(col!.value, "100%");
    const frame = winner(heights, chainOf(FRAME));
    assert.ok(frame, "some rule sizes the frame");
    assert.equal(frame!.selector, ".fileview-frame");
    assert.equal(frame!.value, "100%", "the frame's percentage — inert against an auto-height column, which is why the column's own is pinned above");
  });

  test(name + ": the column is a flex column whose frame shrinks under a notice — so a notice above the frame never pushes it past the body", () => {
    const disp = winner(rulesFor(css, "display", CHAIN_CLASSES), chainOf(COLUMN));
    assert.ok(disp && disp.selector === ".fileview-pdffall" && disp.value === "flex", "the column is display: flex");
    const dir = winner(rulesFor(css, "flex-direction", CHAIN_CLASSES), chainOf(COLUMN));
    assert.ok(dir && dir.selector === ".fileview-pdffall" && dir.value === "column", "…a flex COLUMN: the notice stacks over the frame");
    const flex = winner(rulesFor(css, "flex", CHAIN_CLASSES), chainOf(FRAME));
    assert.ok(flex && flex.selector === ".fileview-pdffall .fileview-frame" && flex.value === "1 1 auto", "the frame in the column takes what is left and may shrink");
    const minH = winner(rulesFor(css, "min-height", CHAIN_CLASSES), chainOf(FRAME));
    assert.ok(minH && minH.selector === ".fileview-pdffall .fileview-frame" && minH.value === "0", "…below its content size (a flex item's min-height: auto would refuse to)");
  });

  test(name + ": the body is the plain overflow block the percentages rest on, not a flex container", () => {
    // the reason the column needs a height of its own; if the body ever becomes a flex container, re-derive the
    // chain here rather than deleting the column's rule (a stretched flex item resolves percentages too, but the
    // editor and the CodeMirror host above it were built on the block, file-edit.test.ts)
    const disp = winner(rulesFor(css, "display", CHAIN_CLASSES), chainOf(BODY));
    assert.equal(disp, null, "no rule sets display on .fileview-body");
    assert.match(ruleOf(css, ".fileview-body {"), /overflow: auto/, "the body is the scroller");
  });
}

// ── the chromium leg: each full sheet around the real chain, measured ──
const req = createRequire(path.join(PKG, "package.json"));   // runtime requires: esbuild must not bundle playwright
let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the PDF column layout test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the PDF column layout test did not run";
}

// the viewer as file-view.ts builds it: the overlay, the card, the bar, the main row, the body, the column, the
// frame (a blank one: layout is the question, not the document); body.fileview-open as openFileView sets it
const HTML = (css: string) => `<!doctype html><html><head><meta charset="utf-8"><style>
${css}
</style></head><body class="fileview-open">
<div id="romp-fileview"><div class="fileview">
  <div class="fileview-bar"><span class="fileview-name"><span class="fileview-dir">docs/</span><span class="fileview-base">spec.pdf</span></span></div>
  <div class="fileview-main">
    <div class="fileview-body"><div class="fileview-pdffall"><iframe class="fileview-frame" title="docs/spec.pdf"></iframe></div></div>
  </div>
</div></div>
</body></html>`;

interface Snap { body: number; bodyBottom: number; col: number; note: number; frame: number; frameBottom: number; aside: number; mainW: number; bodyW: number }
/** lays the case out (a notice in the column above the frame; the panel's aside beside the body) and measures it */
const MEASURE = `((withNote, withAside) => {
  const main = document.querySelector(".fileview-main"), body = document.querySelector(".fileview-body");
  const col = document.querySelector(".fileview-pdffall"), frame = document.querySelector(".fileview-frame");
  col.querySelector(".fileview-err")?.remove(); main.querySelector(".fileview-aside")?.remove();
  if (withNote) { const n = document.createElement("div"); n.className = "fileview-err"; n.textContent = "the page renderer did not load — showing the browser's viewer instead"; col.prepend(n); }
  if (withAside) { const a = document.createElement("aside"); a.className = "fileview-aside"; a.textContent = "comments"; main.appendChild(a); }
  const r = (el) => el ? el.getBoundingClientRect() : { height: 0, bottom: 0, width: 0 };
  const note = col.querySelector(".fileview-err"), aside = main.querySelector(".fileview-aside");
  return { body: r(body).height, bodyBottom: r(body).bottom, col: r(col).height, note: r(note).height, frame: r(frame).height,
    frameBottom: r(frame).bottom, aside: r(aside).height, mainW: r(main).width, bodyW: r(body).width };
})`;

test("in Chromium: the frame fills the body — the column takes the body's height and the frame the column's, less any notice above it, in both sheets", { skip: SKIP }, async () => {
  const browser = await chromium.launch();
  try {
    for (const [name, css] of SHEETS) {
      const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => errors.push(e.message));
      await page.route("http://TESTHOST/**", (route: any) => {
        const u = new URL(route.request().url());
        if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: HTML(css) });
        return route.fulfill({ status: 404, body: "" });   // the sheet's fonts and glyphs: absent here, irrelevant to the boxes
      });
      await page.goto("http://TESTHOST/view.html");
      const cases: Array<[string, boolean, boolean]> = [
        ["panel closed (every PDF open's first state)", false, false],
        ["the pages attempt's fallback: a notice above the frame", true, false],
        ["the panel's aside beside the body, under a notice", true, true],
      ];
      for (const [label, withNote, withAside] of cases) {
        const s: Snap = await page.evaluate(`${MEASURE}(${withNote}, ${withAside})`);
        const at = name + ", " + label + ": ";
        assert.ok(s.body > 400, at + "the body is a real pane height (" + s.body + "px), so the measurement means something");
        if (withNote) assert.ok(s.note > 0, at + "the notice has a box"); else assert.equal(s.note, 0);
        if (withAside) { assert.ok(s.aside > 0, at + "the aside has a box"); assert.ok(s.bodyW < s.mainW, at + "…beside the body, not below it, at this width"); }
        assert.ok(Math.abs(s.col - s.body) < 1, at + "the column fills the body (" + s.col + " vs " + s.body + ") — an auto-height column is the collapse");
        assert.ok(Math.abs(s.frame - (s.col - s.note)) < 1, at + "the frame takes the column less the notice (" + s.frame + " vs " + (s.col - s.note) + "), not the UA's " + UA_IFRAME_DEFAULT + "px default");
        assert.ok(s.frame > s.body / 2, at + "the frame is most of the body (" + s.frame + " of " + s.body + ")");
        assert.ok(s.frameBottom <= s.bodyBottom + 0.5, at + "the notice never pushes the frame past the body (" + s.frameBottom + " vs " + s.bodyBottom + ")");
      }
      assert.deepEqual(errors, [], name + ": no page errors");
      await page.close();
    }
  } finally {
    await browser.close();
  }
});
