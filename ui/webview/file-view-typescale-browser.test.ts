// The document type scale in headless Chromium over the REAL viewer (Slice 3 of plans/markdown-viewer.md: "a document
// type scale"; decisions 3, 4 and 5), on the three surfaces the viewer mounts in (the Files pane under styles.css and
// files-pane.css, the chat modal under styles.css, the feed modal under feed.css; real-viewer-leg.ts is the page), at
// 100% and after one A+ press (115%), dark and light. Every acceptance line of the slice is a computed style or a
// laid-out box here, never a match on CSS text:
//   - the headings compute 2 / 1.5 / 1.25 / 1em of the prose, h5 and h6 1em in the dim tier, a rule under h1 and h2,
//     weight 600, and the prose is 1.15 times the page's size (14.95px at the 13px default) in the sans face in BOTH
//     themes (decision 3; the light theme's mono prose face was the audit's Medium defect);
//   - the column is 80ch of the root's own zero glyph (at most two pixels over, the padding rounded down), centred in
//     the body to the pixel, at 900 and 1400px, at 100% and 115%, and pane-capped at 380px; a picture and the figure
//     layer's wrapper take the column;
//   - a table no wider than the column sits at the column's left edge with the prose; one wider than the column grows
//     out of it evenly, centred in the body, up to the body's 18px inset; one wider than that is the body less 36px and
//     scrolls in its own box; the Comments aside open or closed, since the cap reads the BODY (a size container), not
//     the card (decision 4 kept beside fork PR #348's pane-wide table);
//   - a task item computes list-style none with its checkbox drawn for the theme's colour scheme at the prose's font size
//     (no accent-color: the sanitizer keeps every box disabled, and Chromium paints a disabled box grey whatever accent is
//     declared, so the declaration was inert and is gone; review 2026-09-08); th weight 600
//     on the --overlay-05 fill, even rows striped, `:---:` and `---:` columns centred and right-aligned; kbd dressed;
//   - every fence, registered or not, carries the per-line rows and a Copy button, its counter reset on the code element
//     and tab-size 4, the Raw view's; decision 5's rust fence is highlighted; the code comment measures 4.5:1 or more
//     over the code block's composited background in both themes (theme-parity.test.ts holds the token pair; this is
//     the pixel).
// Skips loudly without a browser. Synthetic values only: an invented note, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, closePanel, frames, REPORT, type Mode } from "./real-viewer-leg";

const F = "```";
const LONGLINE = "x = " + Array.from({ length: 30 }, (_, i) => "argument_" + i).join(" + ");
/** The note: every construct the scale dresses, then enough paragraphs to scroll. */
export const NOTE = [
  "# Heading one", "", "## Heading two", "", "### Heading three", "", "#### Heading four", "", "##### Heading five", "", "###### Heading six", "",
  "A paragraph with **strong text** and `inline code` and <kbd>Ctrl</kbd>+<kbd>C</kbd> in it. " + "The quick brown fox jumps over the lazy dog. ".repeat(6),
  "", "- [ ] an open task", "- [x] a done task", "- a plain item", "",
  "1. [ ] a numbered task", "", "   with a second paragraph", "", "2. a plain numbered item", "",
  // three tables: narrower than the column; wider than the column but narrower than the body less 36px at 1400 and 1060
  // (the aside open); wider than any body
  "| Left | Center | Right |", "|:-----|:------:|------:|", "| a | b | c |", "| d | e | f |", "| g | h | i |", "",
  "| " + Array.from({ length: 6 }, (_, i) => "column " + (i + 1) + " header text").join(" | ") + " |", "|" + Array.from({ length: 6 }, () => "---").join("|") + "|",
  ...Array.from({ length: 3 }, (_, r) => "| " + Array.from({ length: 6 }, (_, i) => "row " + r + " cell " + (i + 1) + " words").join(" | ") + " |"), "",
  "| " + Array.from({ length: 14 }, (_, i) => "wide_column_" + (i + 1) + "_header").join(" | ") + " |", "|" + Array.from({ length: 14 }, () => "---").join("|") + "|",
  "| " + Array.from({ length: 14 }, (_, i) => "cell_" + (i + 1)).join(" | ") + " |", "",
  F + "python", "# a comment line", "def f(x):", "\treturn x  # tab-indented", LONGLINE, F, "",
  F + "rust", "fn main() { // rust is registered now", "}", F, "",
  F + "zig", "const x = 1; // no zig grammar: plain, wrapped, Copy", "const y = 2;", F, "",
  F, "no language at all", "second line", F, "",
  "> a quote", "",
  '<img src="data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="200"><rect width="1600" height="200" fill="#369"/></svg>') + '" width="1600" height="200">', "",
  ...Array.from({ length: 40 }, (_, i) => "Paragraph " + (i + 1) + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + "."),
  "",
].join("\n");

type Cell = Record<string, any>;
/** Everything the leg reads, in one evaluate. */
function measure(): Cell {
  const q = (s: string, r: ParentNode = document) => r.querySelector(s) as HTMLElement;
  const cs = (el: Element, ps?: string) => getComputedStyle(el, ps);
  const root = q(".fileview-md"), body = q(".fileview-body");
  const px = (el: Element) => parseFloat(cs(el).fontSize);
  const p = q("p", root);
  const heads: Cell = {};
  for (const t of ["h1", "h2", "h3", "h4", "h5", "h6"]) { const e = q(t, root); heads[t] = { size: px(e), weight: cs(e).fontWeight, color: cs(e).color, rule: cs(e).borderBottomStyle + " " + cs(e).borderBottomWidth, marginTop: parseFloat(cs(e).marginTop), marginBottom: parseFloat(cs(e).marginBottom) }; }
  // the column: the root's content box; ch from forty zero glyphs in the root's own font
  const sp = document.createElement("span"); sp.style.whiteSpace = "nowrap"; sp.textContent = "0".repeat(40); root.appendChild(sp); const ch = sp.getBoundingClientRect().width / 40;
  sp.style.backgroundColor = "var(--overlay-05)"; const overlayRgb = cs(sp).backgroundColor; sp.remove();   // the wash as resolved (Chromium quantizes the alpha: 0.045 reads back 0.043)
  const br = body.getBoundingClientRect(), pr = p.getBoundingClientRect();
  const scrollbar = body.offsetWidth - body.clientWidth;
  const measureBox = { pWidth: pr.width, ch, chars: pr.width / ch, leftGap: pr.left - br.left, rightGap: br.right - scrollbar - pr.right, bodyClient: body.clientWidth, bodyScroll: body.scrollWidth, padL: parseFloat(cs(root).paddingLeft), padR: parseFloat(cs(root).paddingRight) };
  const tables = (Array.from(root.querySelectorAll("table")) as HTMLElement[]).map((t) => { const r = t.getBoundingClientRect(); return { left: r.left - br.left, right: br.right - scrollbar - r.right, width: r.width, client: t.clientWidth, scroll: t.scrollWidth, pLeft: pr.left - br.left }; });
  const t0 = root.querySelector("table")!; const ths = Array.from(t0.querySelectorAll("th")); const rows = Array.from(t0.querySelectorAll("tbody tr"));
  const table = { thWeight: cs(ths[0]).fontWeight, thBg: cs(ths[0]).backgroundColor, thCenter: cs(ths[1]).textAlign, thRight: cs(ths[2]).textAlign, tdLeft: cs(rows[0].children[0]).textAlign, tdCenter: cs(rows[0].children[1]).textAlign, tdRight: cs(rows[0].children[2]).textAlign, oddBg: cs(rows[0]).backgroundColor, evenBg: cs(rows[1]).backgroundColor, alignAttr: rows[0].children[1].getAttribute("align"), style: rows[0].children[1].getAttribute("style") };
  const lis = Array.from(root.querySelectorAll("li")) as HTMLElement[];
  const task = lis.find((l) => l.querySelector('input[type="checkbox"]'))!, plain = lis.find((l) => !l.querySelector('input[type="checkbox"]') && l.closest("ul"))!;
  const loose = (Array.from(root.querySelectorAll("ol > li")) as HTMLElement[]).find((l) => l.querySelector("p > input"))!;
  const input = task.querySelector("input")!;
  const tasks = { cls: task.className, listStyle: cs(task).listStyleType, plainListStyle: cs(plain).listStyleType, accent: cs(input).accentColor, scheme: cs(input).colorScheme, fontSize: cs(input).fontSize, proseFontSize: cs(p).fontSize, disabled: (input as HTMLInputElement).disabled, marginLeft: parseFloat(cs(input).marginLeft), ulPad: parseFloat(cs(task.parentElement!).paddingLeft) / px(task.parentElement!), loose: { cls: loose ? loose.className : null, listStyle: loose ? cs(loose).listStyleType : null } };
  const kbd = q("kbd", root);
  const kbdBox = { bg: cs(kbd).backgroundColor, border: cs(kbd).borderTopWidth + " " + cs(kbd).borderTopStyle, radius: cs(kbd).borderRadius, size: px(kbd) / px(p), shadow: cs(kbd).boxShadow, mono: cs(kbd).fontFamily !== cs(p).fontFamily };
  // a fence without rows reads null for its gutter rather than throwing inside this evaluate (getComputedStyle(null) is a
  // TypeError that would hide the named "fence N has its rows" assertion below behind a harness crash)
  const code = (Array.from(root.querySelectorAll("pre")) as HTMLElement[]).map((pre) => { const c = pre.querySelector("code")!; const cmt = c.querySelector(".hljs-comment"); const cl = c.querySelector(":scope > .cl"); return { cls: c.className, rows: c.querySelectorAll(":scope > .cl").length, copy: !!pre.querySelector(":scope > .code-copy"), hasCopy: pre.classList.contains("has-copy"), tabSize: cs(c).tabSize, counterReset: cs(c).counterReset, size: px(c), width: pre.getBoundingClientRect().width, wraps: pre.scrollWidth <= pre.clientWidth + 1, cmt: cmt ? cs(cmt).color : null, preBg: cs(pre).backgroundColor, gutterSelect: cl ? cs(cl, "::before").userSelect : null, gutterContent: cl ? cs(cl, "::before").content : null }; });
  // the bare picture line: a direct child of the root, or, once the real Comments panel's figure layer has mounted (a race
  // with this measure), the picture inside its .fc-imgwrap; both take the column
  const img = q("img", root);
  return { prose: { size: px(p), family: cs(p).fontFamily, color: cs(p).color, fontDoc: cs(root).getPropertyValue("--font-doc").trim(), fontProse: cs(root).getPropertyValue("--font-prose").trim(), sans: cs(root).getPropertyValue("--sans").trim(), mono: cs(root).getPropertyValue("--mono").trim(), scale: cs(root).getPropertyValue("--fv-scale").trim() || "1", base: px(document.body) },
    heads, strong: { size: px(q("strong", root)), weight: cs(q("strong", root)).fontWeight }, measure: measureBox, tables, table, tasks, kbd: kbdBox, code, img: { width: img.getBoundingClientRect().width, parent: img.parentElement!.className }, overlayRgb,
    bg: { card: cs(q(".fileview")).backgroundColor, page: cs(document.body).backgroundColor }, quoteColor: cs(q("blockquote", root)).color, dim: cs(root).getPropertyValue("--dim").trim() };
}

// ── colour maths, the node side (theme-parity.test.ts's, over the browser's computed colours) ──────
const parse = (s: string): number[] | null => { const m = /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+))?\s*\)/.exec(s); return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null; };
const over = (top: number[], under: number[]): number[] => { const a = top[3]; return [0, 1, 2].map((i) => Math.round(top[i] * a + under[i] * (1 - a))); };
const lum = (c: number[]): number => { const f = (v: number) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
const ratio = (a: number[], b: number[]): number => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x); return (hi + 0.05) / (lo + 0.05); };
const near = (a: number, b: number, what: string, tol = 1) => assert.ok(Math.abs(a - b) < tol, what + ": " + a + " vs " + b);

const stepUp = async (page: any) => {
  await page.click('button[aria-label="Larger text"]');
  await page.waitForFunction(() => getComputedStyle(document.querySelector(".fileview-md")!).getPropertyValue("--fv-scale").trim() === "1.15", null, { timeout: 5000 });
  await frames(page, 2);
};
const setLight = async (page: any, on: boolean) => { await page.evaluate((v: boolean) => { document.body.classList.toggle("theme-light", v); }, on); await frames(page, 2); };

/** The scale, the faces, the lists, the table dress, kbd, the fences and the contrast: the same in every cell. */
function checkDress(m: Cell, at: string, light: boolean) {
  const p = m.prose.size;
  near(p, m.prose.base * 1.15 * parseFloat(m.prose.scale), at + ": the prose is 1.15 times the page's size, times the scale", 0.05);
  assert.match(m.prose.family, /^"?(Inter|Space Grotesk)/, at + ": the note's face is the sans (decision 3), in both themes: " + m.prose.family);
  // a custom property's computed value has its var() substituted, so the tokens are compared as the browser resolved them
  assert.equal(m.prose.fontDoc, m.prose.sans, at + ": --font-doc is the sans"); assert.equal(m.prose.fontProse, light ? m.prose.mono : m.prose.sans, at + ": --font-prose is the chat's and untouched (mono in light)");
  assert.notEqual(m.prose.sans, m.prose.mono);
  for (const [h, k] of [["h1", 2], ["h2", 1.5], ["h3", 1.25], ["h4", 1], ["h5", 1], ["h6", 1]] as const) {
    near(m.heads[h].size, k * p, at + ": " + h + " is " + k + "em of the prose", 0.05);
    assert.equal(m.heads[h].weight, "600", at + ": " + h + " weight 600");
    if (h === "h1") assert.equal(m.heads.h1.marginTop, 0, at + ": the h1 is the note's first child, flush with the top");
    else near(m.heads[h].marginTop, 1.5 * p, at + ": " + h + " sits 1.5 prose-em below what precedes it (GitHub's constant distance)", 0.1);
    near(m.heads[h].marginBottom, 0.5 * p, at + ": " + h + " and 0.5 above what follows", 0.1);
  }
  for (const h of ["h1", "h2"]) assert.equal(m.heads[h].rule, "solid 1px", at + ": a rule under " + h);
  for (const h of ["h3", "h4", "h5", "h6"]) assert.equal(m.heads[h].rule, "none 0px", at + ": no rule under " + h);
  assert.equal(m.heads.h4.color, m.prose.color, at + ": h4 in the prose colour");
  assert.notEqual(m.heads.h5.color, m.prose.color, at + ": h5 dimmed"); assert.equal(m.heads.h5.color, m.heads.h6.color, at + ": h6 too"); assert.equal(m.heads.h5.color, m.quoteColor, at + ": ...in the dim tier the quote wears");
  near(m.strong.size, p, at + ": strong is the prose size", 0.05); assert.equal(m.strong.weight, "600");
  // lists and tasks
  near(m.tasks.ulPad, 2, at + ": a 2em list gutter", 0.01);
  assert.equal(m.tasks.cls, "task-list-item", at + ": mdBlock stamped GitHub's class"); assert.equal(m.tasks.listStyle, "none", at + ": no bullet beside the box");
  assert.equal(m.tasks.plainListStyle, "disc", at + ": a plain item keeps its bullet");
  assert.equal(m.tasks.loose.cls, "task-list-item", at + ": a loose list's task (the box inside its paragraph) is stamped too"); assert.equal(m.tasks.loose.listStyle, "none");
  assert.equal(m.tasks.accent, "auto", at + ": no accent-color: the sanitizer keeps the box disabled and Chromium paints a disabled box grey whatever accent is declared"); assert.equal(m.tasks.scheme, light ? "light" : "dark", at + ": the box drawn for the theme");
  assert.equal(m.tasks.fontSize, m.tasks.proseFontSize, at + ": the box's em is the prose's (font-size: inherit), so its pull into the gutter scales with the text");
  assert.ok(m.tasks.marginLeft < 0, at + ": the box is pulled into the gutter (" + m.tasks.marginLeft + ")"); assert.equal(m.tasks.disabled, true);
  // the table dress
  assert.equal(m.table.thWeight, "600", at + ": th weight 600"); assert.equal(m.table.thBg, m.overlayRgb, at + ": th on --overlay-05 (" + m.overlayRgb + ")");
  assert.equal(m.table.thBg, light ? "rgba(0, 0, 0, 0.043)" : "rgba(255, 255, 255, 0.06)", at + ": ...the theme's wash as Chromium quantizes it");
  assert.equal(m.table.evenBg, m.table.thBg, at + ": even rows striped with the same wash"); assert.equal(m.table.oddBg, "rgba(0, 0, 0, 0)", at + ": odd rows bare");
  assert.equal(m.table.alignAttr, "center", at + ": marked wrote the align attribute and the sanitizer kept it"); assert.equal(m.table.style, null, at + ": ...as an attribute, not a style");
  assert.equal(m.table.thCenter, "center"); assert.equal(m.table.tdCenter, "center", at + ": a :---: column is centred"); assert.equal(m.table.thRight, "right"); assert.equal(m.table.tdRight, "right", at + ": a ---: column is right-aligned"); assert.equal(m.table.tdLeft, "left");
  // kbd
  assert.equal(m.kbd.bg, light ? "rgb(239, 231, 220)" : "rgb(28, 28, 31)", at + ": kbd on --kbd-bg"); assert.equal(m.kbd.border, "1px solid", at + ": a kbd border"); assert.equal(m.kbd.radius, "3px");
  near(m.kbd.size, 0.86, at + ": kbd at the ladder's 0.86em", 0.01); assert.notEqual(m.kbd.shadow, "none", at + ": the key's bottom shadow line"); assert.ok(m.kbd.mono, at + ": kbd in the mono face");
  // the fences: python (registered), rust (decision 5), zig (unregistered), none
  assert.equal(m.code.length, 4);
  assert.equal(m.code[0].cls, "language-python hljs"); assert.equal(m.code[1].cls, "language-rust hljs", at + ": rust is registered (decision 5)"); assert.equal(m.code[2].cls, "language-zig", at + ": an unregistered language stays plain, never guessed"); assert.equal(m.code[3].cls, "", at + ": an unnamed fence too");
  for (const [i, c] of m.code.entries()) {
    assert.ok(c.rows >= 2, at + ": fence " + i + " has its rows (" + c.rows + ")"); assert.ok(c.copy && c.hasCopy, at + ": fence " + i + " has Copy");
    assert.equal(c.tabSize, "4", at + ": fence " + i + " tab-size 4"); assert.equal(c.counterReset, "ln 0", at + ": fence " + i + " resets the line counter, hljs class or not");
    near(c.size, 12 * parseFloat(m.prose.scale), at + ": fenced code at 12px times the scale", 0.05); assert.ok(c.wraps, at + ": fence " + i + " wraps its long line");
    assert.equal(c.gutterSelect, "none", at + ": the line numbers never copy"); assert.equal(c.gutterContent, "counter(ln)");
  }
  assert.equal(m.code[0].rows, 4, at + ": four python lines"); assert.equal(m.code[2].rows, 2); assert.equal(m.code[3].rows, 2);
  // the code comment over the code block's composited background: 4.5:1 or more in both themes
  const page = parse(m.bg.page)!, card = parse(m.bg.card)!;
  const cardRgb = card[3] < 1 ? over(card, page) : card.slice(0, 3);
  const preBg = over(parse(m.code[0].preBg)!, cardRgb);
  const cmt = parse(m.code[0].cmt)!;
  const r = ratio(cmt.slice(0, 3), preBg);
  assert.ok(r >= 4.5, at + ": the code comment measures " + r.toFixed(2) + ":1 over the code block (" + m.code[0].cmt + " on rgb(" + preBg.join(",") + ")), 4.5 or more");
  assert.equal(m.code[1].cmt, m.code[0].cmt, at + ": the rust comment wears the same token");
}

/** The column and the tables: centred to the pixel, 80ch (or the pane), the three tables where the plan puts them. */
function checkColumn(m: Cell, at: string, asideOpen: boolean) {
  const { measure: c } = m;
  assert.equal(c.bodyScroll, c.bodyClient, at + ": the body never scrolls sideways");
  const wants80 = c.bodyClient - 36 >= 80 * c.ch;
  if (wants80) {
    assert.ok(c.pWidth >= 80 * c.ch - 0.5 && c.pWidth < 80 * c.ch + 2, at + ": the column is 80ch of the root's own glyph, at most two pixels over from the rounding (" + c.chars.toFixed(2) + "ch, " + c.pWidth + "px, ch " + c.ch.toFixed(3) + ")");
    assert.ok(Math.abs(c.leftGap - c.rightGap) <= 1, at + ": centred: the gaps are " + c.leftGap.toFixed(2) + " and " + c.rightGap.toFixed(2));
    assert.ok(c.padL >= 18 && Math.abs(c.padL - Math.floor(c.padL)) < 0.01, at + ": the padding is whole pixels: " + c.padL);
  } else {
    near(c.pWidth, c.bodyClient - 36, at + ": narrower than 80ch plus the inset, the column is the pane less 18px a side (" + c.chars.toFixed(1) + "ch)");
    near(c.padL, 18, at + ": the padding is its 18px floor");
  }
  near(c.padL, c.padR, at + ": both gaps alike");
  near(m.img.width, c.pWidth, at + ": a bare picture line takes the column");
  const [narrow, mid, wide] = m.tables;
  near(narrow.left, narrow.pLeft, at + ": a table no wider than the column sits at the column's left edge with the prose");
  assert.ok(narrow.width < c.pWidth, at + ": ...and is narrower than it (" + narrow.width + ")"); assert.ok(narrow.scroll <= narrow.client + 1, at + ": ...no scroll");
  const cap = c.bodyClient - 36;
  if (mid.width > c.pWidth + 1) {
    // wider than the column: centred in the body (the body, whatever the aside: the cap reads the size container)
    assert.ok(Math.abs(mid.left - mid.right) <= 1, at + ": the six-column table leaves the column evenly, centred in the body (" + mid.left.toFixed(1) + " / " + mid.right.toFixed(1) + ", " + mid.width + " wide in a " + c.pWidth + " column, aside " + (asideOpen ? "open" : "closed") + ")");
    assert.ok(mid.left >= 18 - 0.5, at + ": ...inside the body's 18px inset");
  } else {
    near(mid.width, Math.min(cap, c.pWidth), at + ": in a narrow body the six-column table is capped at the column");
  }
  near(wide.width, cap, at + ": the fourteen-column table is the body less 36px (" + wide.width + " in " + c.bodyClient + ")");
  assert.ok(Math.abs(wide.left - 18) <= 1 && Math.abs(wide.right - 18) <= 1, at + ": ...from inset to inset (" + wide.left.toFixed(1) + " / " + wide.right.toFixed(1) + ")");
  assert.ok(wide.scroll > wide.client + 100, at + ": ...and scrolls in its own box (" + wide.scroll + " in " + wide.client + ")");
}

test("the type scale, the faces, the lists, the table dress, kbd, the fences and the code-comment contrast, on the three surfaces at 100% and 115%, dark and light", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat", "feed"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 900, 800, { docs: { [REPORT]: NOTE } });
      let m = await page.evaluate(measure);
      checkDress(m, mode + " 900 100% dark", false); checkColumn(m, mode + " 900 100% dark", false);
      assert.equal(m.prose.size, 14.95, mode + ": 13px times 1.15, byte for byte"); assert.equal(m.heads.h1.size, 29.9); assert.equal(m.heads.h2.size, 22.425);
      await setLight(page, true);
      m = await page.evaluate(measure);
      checkDress(m, mode + " 900 100% light", true); checkColumn(m, mode + " 900 100% light", false);
      await setLight(page, false);
      await stepUp(page);
      m = await page.evaluate(measure);
      assert.equal(m.prose.scale, "1.15"); near(m.prose.size, 17.1925, mode + " @115%: the prose", 0.01); near(m.heads.h1.size, 34.385, mode + " @115%: h1", 0.01);
      checkDress(m, mode + " 900 115% dark", false); checkColumn(m, mode + " 900 115% dark", false);
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("the column and the pane-wide table at 380, 900 and 1400px, the Comments aside open and closed: the table's cap reads the body, not the card", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, width] of [["pane", 1400], ["pane", 900], ["pane", 380], ["chat", 1400], ["feed", 1400]] as [Mode, number][]) {
      const { page, errors } = await openViewer(browser, mode, width, 800, { docs: { [REPORT]: NOTE } });
      let m = await page.evaluate(measure);
      checkColumn(m, mode + " " + width + " closed", false);
      const closedBody = m.measure.bodyClient;
      await openPanel(page);
      m = await page.evaluate(measure);
      assert.ok(m.measure.bodyClient < closedBody || width <= 680, mode + " " + width + ": the aside took its width from the body (" + closedBody + " to " + m.measure.bodyClient + ")");
      checkColumn(m, mode + " " + width + " aside open", true);
      if (width === 1400) {
        assert.ok(m.tables[1].width > m.measure.pWidth + 100, mode + " 1400 open: the six-column table is still wider than the column and centred in the narrower body");
        near(m.tables[2].width, m.measure.bodyClient - 36, mode + " 1400 open: the wide table is the OPEN body less 36px, not the card's (" + m.tables[2].width + " vs card-based " + (closedBody - 36) + ")");
      }
      await closePanel(page);
      m = await page.evaluate(measure);
      assert.equal(m.measure.bodyClient, closedBody, mode + " " + width + ": the body is back");
      checkColumn(m, mode + " " + width + " closed again", false);
      if (width === 1400) { await stepUp(page); m = await page.evaluate(measure); checkColumn(m, mode + " 1400 115%", false); }
      assert.deepEqual(errors, [], mode + " " + width + ": no script error");
      await page.close();
    }
  });
});
