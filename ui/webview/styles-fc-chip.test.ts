// The author's chip beside a Raw change mark (plans/file-review.md, UX: in Raw, insertions tint, deletions render
// struck at their point, "each with the author's session chip in the session's color" — the `▍web` beside the marked
// text in the sketch). anchor-map.ts's paintChangesRaw puts the chip's LABEL on the last element of each change as
// `data-fc-chip` for the sheet's `::after` to draw as generated content (no node, so no walk or selection sees it);
// the Slice 2 review found that neither sheet had a rule reading the attribute, so the label was set and nothing
// drew it — the tint and the underline showed, the session's name did not (anchor-map-change-marks.test.ts pins
// the attribute alone, and a bare attribute renders nothing in any engine).
//
// Two legs. The source leg reads both sheets (the feed page loads only feed.css) and pins WHAT the chip draws: the
// attribute anchor-map sets, on the classes anchor-map paints, in the mark's own author colour under the surface's
// ink. The rule's shape, its place after the panel block and its size are styles-fc-inline-chip.test.ts's: the dress
// hangs on the marks' classes with `content: none`, the attribute rule turns the content on. The browser leg paints
// changes with the REAL painter over the viewer's own Raw rows under headless Chromium and reads what the engine
// draws: the chip's text, its colour, the width it takes, that it enters no selection and grows no row, and that
// unpaint leaves no residue. It skips LOUDLY without a playwright browser (CI installs none), the
// waiting-pane-browser.test.ts idiom.
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
const SHEETS = [["styles.css", read("styles.css")], ["feed.css", read("feed.css")]] as const;

const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, "");
/** the panel block (its header to its end marker) and the tail of the sheet after the marker, comments stripped */
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
  return css.slice(at + head.length + 2, css.indexOf("}", at));
}
const decl = (body: string, prop: string): string | null => {
  const m = new RegExp("(?:^|;)\\s*" + prop.replace(/-/g, "\\-") + ":\\s*([^;]+)").exec(body);
  return m ? m[1].trim() : null;
};

// ── what the painter writes, read from its source so the sheet cannot outlive it ──────────────────
const CHIP_ATTR = (() => { const m = /const CHIP_ATTR = "([\w-]+)";/.exec(MAP); assert.ok(m, "anchor-map names the chip attribute"); return m![1]; })();
const RAW_CLASSES = (() => {
  const del = /paintRawPoint\(codeRoot, source, c\.curFrom, "([\w-]+)", data, deletionLabel\(c\.oldText\), styles\)/.exec(MAP);
  const ins = /paintRaw\(codeRoot, source, \{ start: c\.curFrom, end: c\.curTo \}, "([\w-]+)", data\)/.exec(MAP);
  assert.ok(del && ins, "paintChangesRaw paints a point class and a wrap class");
  return { del: del![1], ins: ins![1] };
})();

test("the painter puts the chip label on a change's last Raw element, as an attribute, for the sheet to draw", () => {
  assert.equal(CHIP_ATTR, "data-fc-chip");
  assert.match(MAP, /if \(mine\.length\) \(mine\[mine\.length - 1\] as unknown as DElement\)\.setAttribute\(CHIP_ATTR, chipLabel\(c\)\);/,
    "one chip per change, on its last element");
  assert.deepEqual(RAW_CLASSES, { del: "fc-del", ins: "fc-ins" });
});

test("both sheets draw the chip: the marks' ::after reads the painter's attribute, in the author colour under the surface's ink", () => {
  for (const [sheet, css] of SHEETS) {
    const { block, tail } = split(css, sheet);
    // the dress on the marks' own classes, the content switched on by the attribute the painter alone sets
    // (styles-fc-inline-chip.test.ts pins the pair's shape, place and size; here, what they draw)
    const dress = ruleBody(tail, `.${RAW_CLASSES.ins}::after, .${RAW_CLASSES.del}::after`, sheet);
    const sw = ruleBody(tail, `.${RAW_CLASSES.ins}[${CHIP_ATTR}]::after, .${RAW_CLASSES.del}[${CHIP_ATTR}]::after`, sheet);
    assert.equal(decl(sw, "content"), `attr(${CHIP_ATTR})`, sheet + ": the label is generated content — no node enters a row");
    assert.equal(decl(dress, "content"), "none", sheet + ": an unchipped mark draws nothing");
    // the card chip's weight and pill (ui/CLAUDE.md: labels match labels) — read from .fc-chip, not restated
    const card = ruleBody(block, ".fc-chip", sheet);
    assert.equal(decl(dress, "font-weight"), decl(card, "font-weight"), sheet + ": the card chip's weight");
    assert.equal(decl(dress, "border-radius"), "var(--radius-pill)", sheet + ": a pill through the token");
    // the session's colour is the mark's own --fc-author, with the mark's own fallback (anchor-map.test.ts pins the
    // underline as `var(--fc-author, var(--accent))`): chip and underline can never disagree about the author
    const author = "var(--fc-author, var(--accent))";
    assert.ok(decl(dress, "background")!.includes(author), sheet + ": the wash mixes the author colour: " + decl(dress, "background"));
    assert.ok(decl(dress, "box-shadow")!.includes(author), sheet + ": the hairline is the author colour: " + decl(dress, "box-shadow"));
    assert.equal(decl(dress, "color"), "var(--fg)", sheet + ": the ink is the surface's — a session colour as ink fails against one theme");
    // a box that clips its overflow puts its baseline on its bottom edge; middle keeps the pill on the x-height
    assert.equal(decl(dress, "display"), "inline-block", sheet);
    assert.equal(decl(dress, "overflow"), "hidden", sheet);
    assert.equal(decl(dress, "vertical-align"), "middle", sheet + ": middle, not baseline, on a clipping inline-block");
    assert.equal(decl(dress, "white-space"), "nowrap", sheet + ": a two-word session name stays one chip");
    // the panel block itself dresses no chip: the block speaks panel em and its resolver reads no attribute selector
    assert.ok(!block.includes(CHIP_ATTR), sheet + ": the panel block names no " + CHIP_ATTR);
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
      resolveDir: UI, loader: "ts", sourcefile: "fc-chip-probe.ts" },
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

// synthetic world: the notes-api report; web has a live colour, tests has none (the plan's neutral fallback)
const SOURCE = "# Findings\nThe api session cut p95 latency\nby 40% and kept the cache warm\nWe recommend shipping the cache in v1.2.\n";
const WEB_COLOR = "rgb(10, 20, 30)";
const ACCENT = "rgb(156, 210, 255)";   // --accent #9cd2ff, both sheets' dark :root
type Chip = { id: string | null; cls: string; label: string | null; content: string; shadow: string; fontSize: string; display: string };
const at = (s: string, from = 0) => { const i = SOURCE.indexOf(s, from); assert.ok(i >= 0, "source has " + JSON.stringify(s)); return i; };
const CHANGES = [
  // an insertion across two rows: the first row's slice carries no chip, the last does
  { id: "c-ins", kind: "ins", curFrom: at("latency"), curTo: at("40%") + 3, oldText: "", author: "web" },
  // a deletion: a point whose struck label is "reduced ", chipped, no live colour
  { id: "c-del", kind: "del", curFrom: at("shipping"), curTo: at("shipping"), oldText: "reduced ", author: "tests" },
  // a substitution: the point, then the wrap; the chip sits on the wrap
  { id: "c-sub", kind: "sub", curFrom: at("kept"), curTo: at("kept") + 4, oldText: "held", author: "web" },
];

for (const [sheet, css] of SHEETS) {
  test(`in Chromium under ${sheet}: the session's name is drawn beside each change in Raw, in its colour, with no node, no selection text and no row growth`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw.chromium.launch(); }
    catch (e) { t.skip("no playwright chromium on this box — the browser leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
      const errors: string[] = [];
      page.on("pageerror", (e: Error) => { errors.push(e.message); });
      // the sheet inline (its @import of KaTeX is a font sheet the probe does not need); the viewer's Raw shape
      const html = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${css.replace(/@import [^;]+;/g, "")}</style></head>
<body><div class="fileview"><div class="fileview-body"><div class="fileview-code"><pre class="fileview-pre fileview-wrap"><code class="hljs">${rawRows(SOURCE)}</code></pre></div></div></div>
<span id="probe" style="color: var(--fg)">fg</span><script>${painterBundle()}</script></body></html>`;
      await page.setContent(html);
      const r = await page.evaluate(([source, changes, webColor]: [string, typeof CHANGES, string]) => {
        const code = document.querySelector("code.hljs")!;
        const rows = [...code.querySelectorAll(".fv-cl")];
        const heightsBefore = rows.map((el) => el.getBoundingClientRect().height);
        const nodesBefore = code.querySelectorAll("*").length;
        const stylesFor = (c: { author: string }) => (c.author === "web" ? { "--fc-author": webColor } : {});
        const painted = (window as any).__fc.paintChangesRaw(code, source, changes, stylesFor) as Element[];
        const after = (el: Element) => getComputedStyle(el, "::after");
        const chipped = painted.filter((el) => el.hasAttribute("data-fc-chip"));
        const plain = painted.filter((el) => !el.hasAttribute("data-fc-chip"));
        const ink = (theme: boolean) => {
          document.body.classList.toggle("theme-light", theme);
          const fg = getComputedStyle(document.getElementById("probe")!).color;
          return { fg, chips: chipped.map((el) => after(el).color) };
        };
        const dark = ink(false), light = ink(true); ink(false);
        const widths = chipped.map((el) => {
          const w1 = el.getBoundingClientRect().width, v = el.getAttribute("data-fc-chip")!;
          el.removeAttribute("data-fc-chip");
          const w0 = el.getBoundingClientRect().width;
          el.setAttribute("data-fc-chip", v);
          return [w1, w0];
        });
        const s = getSelection()!; s.removeAllRanges();
        const range = document.createRange(); range.selectNodeContents(code); s.addRange(range);
        const selection = s.toString(); s.removeAllRanges();
        const out = {
          painted: painted.length, nodesAdded: code.querySelectorAll("*").length - nodesBefore - painted.length,
          chips: chipped.map((el) => ({ id: el.getAttribute("data-id"), cls: el.className, label: el.getAttribute("data-fc-chip"), content: after(el).content,
            shadow: after(el).boxShadow, fontSize: after(el).fontSize, display: after(el).display })),
          plainContent: plain.map((el) => after(el).content),
          dark, light, widths, selection,
          heightsBefore, heightsAfter: rows.map((el) => el.getBoundingClientRect().height),
          rowFont: getComputedStyle(rows[0]).fontSize, baseFont: getComputedStyle(document.body).fontSize,
        };
        (window as any).__fc.unpaintChanges(code);
        const residue = [...code.querySelectorAll("*")].filter((el) => after(el).content !== "none").length;
        return { ...out, residue, nodesAfterUnpaint: code.querySelectorAll("*").length - nodesBefore };
      }, [SOURCE, CHANGES, WEB_COLOR] as [string, typeof CHANGES, string]);
      assert.deepEqual(errors, [], "no script error");
      assert.equal(r.painted, 5, "two ins slices, a del point, a sub point and its wrap");
      assert.equal(r.nodesAdded, 0, "the painter added the marks and nothing else — the chip is no node");
      // the chip: one per change, on its last element, the engine draws the label
      const chips = r.chips as Chip[];
      assert.deepEqual(chips.map((c) => [c.id, c.cls, c.label, c.content]), [
        ["c-ins", "fc-ins", "web", '"web"'],
        ["c-del", "fc-del", "tests", '"tests"'],
        ["c-sub", "fc-ins", "web", '"web"'],
      ], sheet + ": the session's name is drawn beside each change");
      assert.deepEqual(r.plainContent, ["none", "none"], "the insertion's first-row slice and the substitution's point draw no chip");
      for (const c of chips) {
        assert.equal(c.display, "inline-block", String(c.id));
        // the card chip's 0.72 of the PAGE base (calc(0.72 * var(--fs))), not of the 12px code face the mark sits in —
        // labels match labels (ui/CLAUDE.md); styles-fc-inline-chip.test.ts reads the two chips side by side
        assert.equal(c.fontSize, String(Math.round(parseFloat(r.baseFont) * 0.72 * 100) / 100) + "px", c.id + ": the card chip's 0.72 of the page base " + r.baseFont);
        assert.notEqual(r.baseFont, r.rowFont, "the probe's code face differs from the page base, so the two readings are distinguishable");
      }
      // the session's colour: web's own; the accent for an author with no live match, as the mark's underline does
      assert.ok(chips[0].shadow.includes(WEB_COLOR) && chips[2].shadow.includes(WEB_COLOR), "web's chips wear web's colour: " + chips[0].shadow);
      assert.ok(chips[1].shadow.includes(ACCENT), "no live match: the mark's accent fallback: " + chips[1].shadow);
      // the ink is the surface's fg in either theme — never the session colour, which fails against one of them
      assert.deepEqual(r.dark.chips, [r.dark.fg, r.dark.fg, r.dark.fg], "dark: the chip's ink is --fg");
      assert.deepEqual(r.light.chips, [r.light.fg, r.light.fg, r.light.fg], "light: the chip's ink is the light --fg");
      assert.notEqual(r.dark.fg, r.light.fg, "the probe saw both themes");
      // it takes room beside the text (the review's measurement: 0.00px added, before the rule existed)
      for (const [w1, w0] of r.widths) assert.ok(w1 - w0 > 10, "the chip widens its element: " + w1 + " vs " + w0);
      // generated content: never in a selection (the labels are not in the file), and no row grows for it
      assert.ok(r.selection.includes("cut p95 latency") && r.selection.includes("shipping the cache"), "the file's text selects");
      for (const label of ["web", "tests", "reduced"]) assert.ok(!r.selection.includes(label), "the selection never holds the " + label + " label: " + JSON.stringify(r.selection));
      assert.deepEqual(r.heightsAfter, r.heightsBefore, "no row grew for the chip — the pill fits the row's line box");
      // unpaint: no ::after content anywhere, the DOM is what it was
      assert.equal(r.residue, 0, "no chip survives unpaint");
      assert.equal(r.nodesAfterUnpaint, 0);
    } finally { await browser.close(); }
  });
}
