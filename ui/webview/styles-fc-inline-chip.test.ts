// The author's chip beside a Raw change mark: its SHAPE, its PLACE in the sheet, and its SIZE (plans/file-review.md,
// UX: in Raw each change wears "the author's session chip in the session's color"; styles-fc-chip.test.ts covers what
// the chip draws). The Slice 2 review found the chip's first rule, `[data-fc-chip]::after { … font-size: 0.72em … }`
// inside the panel block, wrong three ways. (1) The sheets' two cascade resolvers (styles-fc-computed-sizes.test.ts
// over the panel block, styles-fileview-err-sizes.test.ts over the whole sheet) model class and pseudo-element
// selectors, not attribute ones, and ABORT on a font-size rule they cannot parse — the whole-sheet one at module load,
// taking every button check with it. (2) The rule sat in the panel block, whose resolver speaks panel em, while the
// chip's chain runs through .fileview-pre's ABSOLUTE 12px. (3) So 0.72em there computed to 8.64px beside the 9.36px
// card chip (.fc-chip: 0.72em of the panel's inherited base, var(--fs)) — the same author label at two sizes on one
// surface (ui/CLAUDE.md, font sizes: labels match labels; nested em compounds, compensate explicitly).
//
// The shape now: the pill's dress hangs on the marks' own classes (`.fc-ins::after, .fc-del::after`) with
// `content: none`, and the painter's attribute alone turns it on (`.fc-ins[data-fc-chip]::after, …` sets content only —
// no size, so no resolver reads it). The size is `calc(<the card chip's factor> * var(--fs))`: the card chip's share of
// the same page base, written against --fs as the composer's buttons are, whatever the code face is. Both rules sit
// AFTER the panel block's end marker. Two legs. The source leg pins the shape and the place in both sheets (the feed
// page loads only feed.css) and the resolvers' grammar as a sheet-wide invariant. The browser leg paints changes with
// the REAL painter over the viewer's Raw rows, beside a card chip on the real aside chain, under headless Chromium and
// reads the two chips' computed sizes at two page bases. It skips LOUDLY without a playwright browser (CI installs none),
// the waiting-pane-browser.test.ts idiom.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const MAP = read("anchor-map.ts");
const VIEW = read("file-view.ts");
const PANEL = read("file-comments.ts");
const SHEETS = [["styles.css", read("styles.css")], ["feed.css", read("feed.css")]] as const;

const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");
/** the panel block (its header to its end marker) and the tail of the sheet after the marker */
function split(css: string, sheet: string): { block: string; tail: string } {
  const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const marker = "/* ── end file comments panel ── */";
  const b = css.indexOf(marker);
  assert.ok(a >= 0 && b > a, sheet + ": the block and its end marker");
  return { block: stripComments(css.slice(a, b)), tail: stripComments(css.slice(b + marker.length)) };
}
/** the one rule whose prelude is `head` (the text up to `{`), body only */
function ruleBody(css: string, head: string, sheet: string): string {
  const at = css.indexOf(head + " {");
  assert.ok(at >= 0, sheet + ": a rule " + JSON.stringify(head));
  assert.equal(css.indexOf(head + " {", at + 1), -1, sheet + ": one rule " + JSON.stringify(head));
  return css.slice(at + head.length + 2, css.indexOf("}", at));
}
const decl = (body: string, prop: string): string | null => {
  const m = new RegExp("(?:^|;)\\s*" + prop.replace(/-/g, "\\-") + ":\\s*([^;]+)").exec(body);
  return m ? m[1].trim() : null;
};
/** every innermost `prelude { body }` in the sheet (an at-rule's own head is never a prelude: its body holds braces) */
const rules = (css: string): { head: string; body: string }[] =>
  [...stripComments(css).matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ head: m[1].trim(), body: m[2] }));

// ── what the painter writes, read from its source so the sheet cannot outlive it ──────────────────
const CHIP_ATTR = (() => { const m = /const CHIP_ATTR = "([\w-]+)";/.exec(MAP); assert.ok(m, "anchor-map names the chip attribute"); return m![1]; })();
const MARKS = (() => {
  const del = /paintRawPoint\(codeRoot, source, c\.curFrom, "([\w-]+)", data, deletionLabel\(c\.oldText\), styles\)/.exec(MAP);
  const ins = /paintRaw\(codeRoot, source, \{ start: c\.curFrom, end: c\.curTo \}, "([\w-]+)", data\)/.exec(MAP);
  assert.ok(del && ins, "paintChangesRaw paints a point class and a wrap class");
  return { del: del![1], ins: ins![1] };
})();
// the two rules, in the marks' own vocabulary: the dress on the classes, the switch on the attribute
const DRESS = `.${MARKS.ins}::after, .${MARKS.del}::after`;
const SWITCH = `.${MARKS.ins}[${CHIP_ATTR}]::after, .${MARKS.del}[${CHIP_ATTR}]::after`;

test("the painter: one chip attribute, on the last of the two mark classes it paints", () => {
  assert.equal(CHIP_ATTR, "data-fc-chip");
  assert.deepEqual(MARKS, { del: "fc-del", ins: "fc-ins" });
  assert.match(MAP, /if \(mine\.length\) \(mine\[mine\.length - 1\] as unknown as DElement\)\.setAttribute\(CHIP_ATTR, chipLabel\(c\)\);/);
});

test("both sheets: the chip's rules sit AFTER the panel block, the dress on the marks' classes, the attribute setting content only", () => {
  for (const [sheet, css] of SHEETS) {
    const { block, tail } = split(css, sheet);
    // the panel block is the panel's: the resolver over it speaks panel em, and the chip's chain is not a panel chain
    assert.ok(!block.includes(CHIP_ATTR), sheet + ": the panel block names no " + CHIP_ATTR);
    assert.ok(!block.includes("::after"), sheet + ": the panel block dresses no ::after");
    // the dress: everything but the content, with content: none, so an unchipped mark generates no box
    const dress = ruleBody(tail, DRESS, sheet);
    assert.equal(decl(dress, "content"), "none", sheet + ": the dress alone draws nothing");
    assert.equal(decl(dress, "display"), "inline-block", sheet);
    assert.equal(decl(dress, "vertical-align"), "middle", sheet + ": middle, not baseline, on a clipping inline-block");
    assert.equal(decl(dress, "overflow"), "hidden", sheet);
    assert.equal(decl(dress, "white-space"), "nowrap", sheet + ": a two-word session name stays one chip");
    assert.equal(decl(dress, "border-radius"), "var(--radius-pill)", sheet + ": a pill through the token");
    assert.equal(decl(dress, "color"), "var(--fg)", sheet + ": the ink is the surface's — a session colour as ink fails against one theme");
    const author = "var(--fc-author, var(--accent))";
    assert.ok(decl(dress, "background")!.includes(author), sheet + ": the wash mixes the author colour: " + decl(dress, "background"));
    assert.ok(decl(dress, "box-shadow")!.includes(author), sheet + ": the hairline is the author colour: " + decl(dress, "box-shadow"));
    // the card chip's weight and cap (ui/CLAUDE.md: labels match labels) — read from .fc-chip, not restated
    const card = ruleBody(block, ".fc-chip", sheet);
    assert.equal(decl(dress, "font-weight"), decl(card, "font-weight"), sheet + ": the card chip's weight");
    assert.equal(decl(dress, "max-width"), decl(card, "max-width"), sheet + ": the card chip's cap");
    // the switch: the painter's attribute turns the content on and sets NOTHING else — no size, so no resolver reads it
    const sw = ruleBody(tail, SWITCH, sheet);
    assert.equal(sw.trim(), `content: attr(${CHIP_ATTR});`, sheet + ": the attribute rule sets content only");
    // no OTHER rule in the sheet gives these marks an ::after that would fight the pair
    const afters = rules(css).map((r) => r.head).filter((p) => p.includes("::after") && (/fc-(ins|del)/.test(p) || p.includes(CHIP_ATTR)));
    assert.deepEqual(afters, [DRESS, SWITCH], sheet + ": the marks' two ::after rules and no other");
  }
});

test("both sheets: no font-size rule carries an attribute selector — the grammar the two cascade resolvers read, sheet-wide", () => {
  // styles-fc-computed-sizes.test.ts and styles-fileview-err-sizes.test.ts parse tag / .class / #id / ::pseudo / :not()
  // and assert.fail on anything else; the whole-sheet one parses at module load, so one `[attr]` on a font-size rule
  // loses every test in that module. The invariant is stated here in the sheet's own terms so the failure names the rule.
  for (const [sheet, css] of SHEETS) {
    const sized = rules(css).filter((r) => /(?:^|;)\s*font-size\s*:/.test(r.body));
    assert.ok(sized.length > 20, sheet + ": the sheet's font-size rules were found (" + sized.length + ")");
    const attr = sized.filter((r) => r.head.includes("["));
    assert.deepEqual(attr.map((r) => r.head), [], sheet + ": a font-size rule with an attribute selector");
  }
});

test("both sheets: the inline chip is sized as the card chip's share of var(--fs), because the code face is absolute", () => {
  for (const [sheet, css] of SHEETS) {
    const { block, tail } = split(css, sheet);
    // the card chip's factor, read once from .fc-chip (0.72em: the block's ladder)
    const m = /^(\d*\.?\d+)em$/.exec(decl(ruleBody(block, ".fc-chip", sheet), "font-size") || "");
    assert.ok(m, sheet + ": .fc-chip sizes in plain em");
    const factor = m![1];
    // the inline chip: the SAME factor of the page base, not of its parent — its parent is the 12px code face
    assert.equal(decl(ruleBody(tail, DRESS, sheet), "font-size"), `calc(${factor} * var(--fs))`, sheet + ": the card chip's factor of var(--fs)");
    // the facts that make the two equal: the page base IS var(--fs), and the code face is an absolute 12px under it
    assert.equal(decl(ruleBody(css, "html, body", sheet), "font-size"), "var(--fs)", sheet + ": the page base is --fs");
    assert.match(css, /:root \{[^}]*--fs: var\(--vscode-chat-font-size, 13px\);/, sheet + ": --fs is the root's, 13px by default");
    assert.equal(decl(ruleBody(css, ".fileview-pre", sheet), "font-size"), "12px", sheet + ": the code face is absolute — an em under it cannot reach the page base");
    // the numbers the review measured, for the reader: at the 13px default the card chip is 0.72 × 13 = 9.36px; the
    // old 0.72em under the 12px pre was 8.64px. The browser leg below reads the engine's own.
    assert.ok(Math.abs(parseFloat(factor) * 13 - parseFloat(factor) * 12) > 0.5, "the compounding the calc compensates is visible at the default base");
  }
});

// ── the browser leg ───────────────────────────────────────────────────────────────────────────────
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** the painter, bundled for a page: paintChangesRaw / unpaintChanges on window.__fc */
function painterBundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import { paintChangesRaw, unpaintChanges } from "./anchor-map";\n(window as any).__fc = { paintChangesRaw, unpaintChanges };\n',
      resolveDir: UI, loader: "ts", sourcefile: "fc-inline-chip-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** the viewer's wrap-mode rows, exactly as file-view.ts's wrapNumberedHtml emits them (pinned to the source) */
function rawRows(text: string): string {
  assert.match(VIEW, /return `<span class="fv-cl"><span class="fv-ct">\$\{prefix\}\$\{ln\}\$\{suffix\}<\/span><\/span>`;/, "the row template moved — re-mirror");
  const lines = text.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return lines.map((ln) => `<span class="fv-cl"><span class="fv-ct">${esc(ln)}</span></span>`).join("");
}

test("the aside chain below is the real DOM: the viewer's root and main, the panel as the aside, a card head's .fc-chip", () => {
  // the same ancestry styles-fileview-err-sizes.test.ts resolves; here only what the probe's markup mirrors
  assert.match(VIEW, /wrap\.id = "romp-fileview";/);
  assert.match(VIEW, /const box = el\("div", "fileview"\);/);
  assert.match(VIEW, /const main = el\("div", "fileview-main"\);\n\s*const body = el\("div", "fileview-body"\);/);
  assert.match(VIEW, /if \(node\) \{ node\.classList\.add\("fileview-aside"\); main\.appendChild\(node\); \}/, "the panel's root IS the aside");
  assert.match(PANEL, /this\.root = el\("div", "fc-panel"\);/);
  assert.match(PANEL, /sections = \{ head: el\("div", "fc-sec-head"\), cards: el\("div", "fc-sec-cards"\),/);
  assert.match(PANEL, /const list = el\("div", "fc-cards"\);/);
  assert.match(PANEL, /const card = el\("div", "fc-card"/);
  assert.match(PANEL, /const head = el\("div", "fc-card-head"\);/);
  assert.match(PANEL, /const chip = el\("span", "fc-chip", c \? c\.name : author \|\| "unknown"\);/, "the card chip is a span.fc-chip in the card head");
});

// synthetic world: the notes-api report; web has a live colour, tests has none (the plan's neutral fallback)
const SOURCE = "# Findings\nThe api session cut p95 latency\nby 40% and kept the cache warm\nWe recommend shipping the cache in v1.2.\n";
const WEB_COLOR = "rgb(10, 20, 30)";
const at = (s: string, from = 0) => { const i = SOURCE.indexOf(s, from); assert.ok(i >= 0, "source has " + JSON.stringify(s)); return i; };
const CHANGES = [
  { id: "c-ins", kind: "ins", curFrom: at("latency"), curTo: at("40%") + 3, oldText: "", author: "web" },
  { id: "c-del", kind: "del", curFrom: at("shipping"), curTo: at("shipping"), oldText: "reduced ", author: "tests" },
  { id: "c-sub", kind: "sub", curFrom: at("kept"), curTo: at("kept") + 4, oldText: "held", author: "web" },
];
type Reading = { base: string; row: string; card: string; inline: string[]; heights: number[] };

for (const [sheet, css] of SHEETS) {
  test(`in Chromium under ${sheet}: the inline chip and the card chip compute to ONE size, at the default base and at a larger one, with no row growth`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw.chromium.launch(); }
    catch (e) { t.skip("no playwright chromium on this box — the browser leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      // the sheet inline (its @import of KaTeX is a font sheet the probe does not need); the viewer's real ancestry with
      // the Raw rows in the body and a card head's chip in the aside beside them
      const html = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css.replace(/@import [^;]+;/g, "")}</style></head>
<body class="fileview-open"><div id="romp-fileview"><div class="fileview"><div class="fileview-main">
<div class="fileview-body"><div class="fileview-code"><pre class="fileview-pre fileview-wrap"><code class="hljs">${rawRows(SOURCE)}</code></pre></div></div>
<div class="fc-panel fileview-aside"><div class="fc-sec-cards"><div class="fc-cards"><div class="fc-card"><div class="fc-card-head"><span class="fc-chip">web</span></div></div></div></div></div>
</div></div></div><script>${painterBundle()}</script></body></html>`;
      await page.setContent(html);
      const r = await page.evaluate(([source, changes, webColor]: [string, typeof CHANGES, string]) => {
        const code = document.querySelector("code.hljs")!;
        const rows = [...code.querySelectorAll(".fv-cl")];
        const cardChip = document.querySelector(".fc-chip")!;
        const after = (el: Element) => getComputedStyle(el, "::after");
        // the page base: the default, and a larger one set the way VS Code sets it (the var --fs reads)
        const setBase = (px: string | null) => { const root = document.documentElement; if (px) root.style.setProperty("--vscode-chat-font-size", px); else root.style.removeProperty("--vscode-chat-font-size"); };
        const BASES: (string | null)[] = [null, "16px"];
        const reading = (chipped: Element[]): Reading => ({
          base: getComputedStyle(document.body).fontSize, row: getComputedStyle(rows[0]).fontSize,
          card: getComputedStyle(cardChip).fontSize, inline: chipped.map((el) => after(el).fontSize),
          heights: rows.map((el) => el.getBoundingClientRect().height),
        });
        const before = BASES.map((b) => { setBase(b); return reading([]); });
        setBase(null);
        const stylesFor = (c: { author: string }) => (c.author === "web" ? { "--fc-author": webColor } : {});
        const painted = (window as any).__fc.paintChangesRaw(code, source, changes, stylesFor) as Element[];
        const chipped = painted.filter((el) => el.hasAttribute("data-fc-chip"));
        const plain = painted.filter((el) => !el.hasAttribute("data-fc-chip"));
        const drawn = chipped.map((el) => [el.getAttribute("data-id"), el.getAttribute("data-fc-chip"), after(el).content]);
        const plainContent = plain.map((el) => after(el).content);
        const painted2 = BASES.map((b) => { setBase(b); return reading(chipped); });
        setBase(null);
        (window as any).__fc.unpaintChanges(code);
        const residue = [...code.querySelectorAll("*")].filter((el) => after(el).content !== "none").length;
        return { painted: painted.length, drawn, plainContent, before, after: painted2, residue };
      }, [SOURCE, CHANGES, WEB_COLOR] as [string, typeof CHANGES, string]);
      assert.deepEqual(errors, [], "no script error");
      assert.equal(r.painted, 5, "two ins slices, a del point, a sub point and its wrap");
      assert.deepEqual(r.drawn, [["c-ins", "web", '"web"'], ["c-del", "tests", '"tests"'], ["c-sub", "web", '"web"']], sheet + ": the attribute alone turns the chip on, and the engine draws the label");
      assert.deepEqual(r.plainContent, ["none", "none"], sheet + ": the dress alone (content: none) draws nothing on an unchipped mark");
      const readings = r.after as Reading[], befores = r.before as Reading[];
      assert.equal(readings.length, 2);
      for (let i = 0; i < readings.length; i++) {
        const w = readings[i];
        // labels match labels: every inline chip is exactly the card chip's computed size, at this base
        for (const px of w.inline) assert.equal(px, w.card, sheet + " at base " + w.base + ": the inline chip (" + px + ") wears the card chip's size (" + w.card + ")");
        // the card chip is 0.72 of the page base; the code face stays its absolute 12px whatever the base — the
        // reason the inline chip is written against var(--fs) and not em
        assert.ok(Math.abs(parseFloat(w.card) - 0.72 * parseFloat(w.base)) < 0.02, sheet + ": the card chip is 0.72 of the base " + w.base + ": " + w.card);
        assert.equal(w.row, "12px", sheet + ": the code face is absolute at base " + w.base);
        assert.deepEqual(w.heights, befores[i].heights, sheet + " at base " + w.base + ": no row grew for the chip — the pill fits the row's line box");
      }
      assert.notEqual(readings[0].base, readings[1].base, "the probe saw two bases");
      assert.notEqual(readings[0].card, readings[1].card, "the card chip scaled with the base, and the inline chip with it");
      assert.equal(r.residue, 0, "no chip survives unpaint");
    } finally { await browser.close(); }
  });
}
