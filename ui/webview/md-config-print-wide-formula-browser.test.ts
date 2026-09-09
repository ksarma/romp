// A display formula wider than the column, under PRINT media (plans/markdown-viewer.md, Slice 4: math in every bundle,
// decision 1, over Slice 3's print block). On screen a wide formula scrolls inside its own box (`.katex-display {
// overflow-x: auto }` in both sheets); paper has no scrollbar, so the box clipped the formula at the column's edge: a
// 60-term sum measured 2309px in a 762px box on the pane, the chat modal and the feed page, about two thirds of it not on
// the paper, where a wide table beside it broke out into the gutters (the slice's review, round 5). The block opens the
// box as it opens the table's, and a formula of the page's own takes the table's room and shift: its box grows to its
// content, at least the column (`min-width: 100%`, so a narrow formula keeps the column box and an equation tag its place
// at the column's edge), at most the body less the root's inset, and the translate centres a box wider than the column in
// the body. A formula between the column and the body prints whole across both gutters; one wider than the paper starts
// at the gutter and is cut at the paper's edge (KaTeX's `white-space: nowrap`: a formula never wraps, and no sheet rule
// can scale it to fit), the most the sheet can do. Measured here over the real viewer bundle with KaTeX's layout sheet
// and the kernel's THEME_CSS on the pane and the feed page: several sums of growing length are rendered and the leg picks
// the one in the band at run time, since the fallback face the harness page draws math in has other metrics on another
// box (the file-comments regions leg's lesson); the narrow one, the tagged one and the widest are read too, first under
// screen media, then print, then screen again, where every value returns. Skips loudly without a browser. Synthetic text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, frames, REPORT, UI, EXT, type Mode } from "./real-viewer-leg";

const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const THEME_CSS = (/\nTHEME_CSS = """([\s\S]*?)"""/.exec(KERNEL) || [])[1] || "";
// KaTeX's layout sheet (the leg's page strips the sheet's @import): the display rules are what matter here (a block, centred,
// nowrap); the font urls are neutralised so nothing is fetched and the glyphs fall to the page's face
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8").replace(/url\([^)]*\)/g, "url(about:blank)");
const OPEN = ".fileview-md .katex-display { overflow: visible; }";
const ROOM = ".fileview-md > .katex-display { width: max-content; min-width: 100%; max-width: calc(100cqi - 36px); translate: min(0px, round(calc(50cqi - max(18px, round(down, (100cqi - 80ch) / 2, 1px)) - 50%), 1px)); }";

const terms = (n: number) => Array.from({ length: n }, (_, i) => `x_{${i}}`).join(" + ");
const CANDIDATES = Array.from({ length: 14 }, (_, i) => 14 + 2 * i);   // 14 to 40 terms, about 36px apart at the pane's size: one lands in the band whatever the face
const NOTE = ["# Print me", "", "A paragraph before the formulas.", "",
  "$$", "x", "$$", "",
  ...CANDIDATES.flatMap((n) => ["$$", terms(n), "$$", ""]),
  "$$", terms(60), "$$", "",
  "$$", "E = mc^2 \\tag{1}", "$$", "",
  "The last paragraph.", ""].join("\n");
const FORMULAS = CANDIDATES.length + 3;

// ── the sheets: the two rules, byte-equal ──────────────────────────────────────────────────────────

test("the print block opens a display formula's scroll box in both sheets and gives a formula of the page's own the table's room and shift", () => {
  for (const f of ["styles.css", "feed.css"]) {
    const css = read(f); const block = css.slice(css.indexOf("@media print {"));
    assert.ok(block.includes(OPEN), f + ": the box opens (overflow-x: auto clipped the formula at the column's edge on paper)");
    assert.ok(block.includes(ROOM), f + ": a formula of the page's own grows to its content, at least the column, at most the body less the inset, centred in the body");
    assert.ok(css.includes(".katex-display { overflow-x: auto; overflow-y: hidden; }"), f + ": the screen's scroll box stands (the print rule is the override)");
  }
  const at = (css: string) => css.slice(css.indexOf("@media print {"));
  assert.equal(at(read("styles.css")), at(read("feed.css")), "the block mirrors exactly");
});

// ── the browser leg ────────────────────────────────────────────────────────────────────────────────

type Formula = { text: string; overflowX: string; box: [number, number]; ink: [number, number]; tag: [number, number] | null };
type Facts = { matchesPrint: boolean; body: [number, number]; column: [number, number]; formulas: Formula[] };
function facts(): Facts {
  const md = document.querySelector(".fileview-md")!; const body = document.querySelector(".fileview-body")!; const cs = (e: Element) => getComputedStyle(e);
  const br = body.getBoundingClientRect(), mr = md.getBoundingClientRect();
  const r1 = (x: number) => Math.round(x * 10) / 10;
  return {
    matchesPrint: matchMedia("print").matches,
    body: [r1(br.left), r1(br.right)],
    column: [r1(mr.left + parseFloat(cs(md).paddingLeft)), r1(mr.right - parseFloat(cs(md).paddingRight))],
    formulas: Array.from(md.querySelectorAll(":scope > .katex-display")).map((kd) => {
      const r = kd.getBoundingClientRect(); const html = kd.querySelector(".katex-html")!;
      let left = Infinity, right = -Infinity;   // the formula's ink: the extent of every laid-out box under .katex-html
      for (const el of Array.from(html.querySelectorAll("*"))) { const er = el.getBoundingClientRect(); if (er.width > 0) { left = Math.min(left, er.left); right = Math.max(right, er.right); } }
      const tag = kd.querySelector(".katex-tag"); const tr = tag ? tag.getBoundingClientRect() : null;
      return { text: (kd.textContent || "").replace(/\s+/g, "").slice(0, 10), overflowX: cs(kd).overflowX, box: [r1(r.left), r1(r.right)], ink: [r1(left), r1(right)], tag: tr ? [r1(tr.left), r1(tr.right)] : null };
    }),
  };
}
const width = (f: Formula) => f.ink[1] - f.ink[0];
const near = (a: number, b: number, tol: number) => Math.abs(a - b) <= tol;

test("under print media a display formula between the column and the paper prints whole, centred across both gutters, a wider one starts at the gutter, and a narrow one and an equation tag keep their column places, on the pane and the feed page; screen media restores each", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE }, theme: KATEX_CSS + "\n" + THEME_CSS });
      await page.waitForFunction((n: number) => document.querySelectorAll(".fileview-md > .katex-display .katex-html").length >= n, FORMULAS, { timeout: 10000 }); await frames(page, 2);
      const screen = await page.evaluate(facts) as Facts;
      assert.equal(screen.matchesPrint, false, mode + ": screen media first");
      assert.equal(screen.formulas.length, FORMULAS, mode + ": every formula rendered");
      const [colL, colR] = screen.column, colW = colR - colL, bodyW = screen.body[1] - screen.body[0], room = bodyW - 36;
      assert.ok(colW > 0 && room > colW + 20, mode + ": the column (" + colW + ") sits inside the body less the inset (" + room + ") with gutters to print into");
      // the shapes, picked by the screen's ink widths (the face's metrics decide them, not a term count)
      const narrow = screen.formulas[0], tagged = screen.formulas[screen.formulas.length - 1], widest = screen.formulas[screen.formulas.length - 2];
      const bandAt = screen.formulas.findIndex((f) => width(f) > colW && width(f) <= room);
      assert.ok(bandAt > 0, mode + ": a candidate sum lies between the column and the body less the inset (" + colW + ", " + room + "]; widths: " + screen.formulas.map((f) => Math.round(width(f))).join(" "));
      assert.ok(width(widest) > bodyW, mode + ": the 60-term sum is wider than the paper (" + width(widest) + " in " + bodyW + ")");
      assert.ok(tagged.tag && width(narrow) < colW / 4, mode + ": the tagged formula carries its tag and the narrow one is narrow");
      for (const f of screen.formulas) { assert.equal(f.overflowX, "auto", mode + ": on screen every formula scrolls in its box"); assert.deepEqual(f.box, [colL, colR], mode + ": ...the column's box (" + f.text + ")"); }
      assert.ok(screen.formulas[bandAt].ink[1] > colR, mode + ": on screen the band formula's ink runs past the column's edge, hidden by the scroll box");
      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const pr = await page.evaluate(facts) as Facts;
      assert.equal(pr.matchesPrint, true, mode + ": print media");
      const [bL, bR] = pr.body, mid = (bL + bR) / 2, pcol = pr.column;
      for (const f of pr.formulas) assert.equal(f.overflowX, "visible", mode + ": in print the box is open (" + f.text + ")");
      // narrow: the column's box, ink inside it; the tag at the column's right edge, as on screen
      const pn = pr.formulas[0], pt = pr.formulas[pr.formulas.length - 1];
      assert.deepEqual(pn.box, pcol, mode + ": a narrow formula keeps the column's box in print");
      assert.ok(pn.ink[0] >= pcol[0] && pn.ink[1] <= pcol[1], mode + ": ...its ink inside the column");
      assert.deepEqual(pt.box, pcol, mode + ": the tagged formula keeps the column's box");
      assert.ok(near(pt.tag![1], pcol[1], 1), mode + ": ...and its tag the column's right edge (" + pt.tag + " against " + pcol + "), as on screen (" + tagged.tag + ")");
      // the band: whole on the paper, centred in the body (before: the box the column's width, the ink cut at its edge)
      const pb = pr.formulas[bandAt];
      assert.ok(pb.ink[0] >= bL - 0.5 && pb.ink[1] <= bR + 0.5, mode + ": a formula between the column and the paper prints whole (" + pb.ink + " in the body " + pr.body + "; before: the box " + screen.formulas[bandAt].box + " cut it at " + colR + ")");
      assert.ok(pb.ink[1] > pcol[1] && pb.ink[0] < pcol[0], mode + ": ...across both gutters (" + pb.ink + " over the column " + pcol + ")");
      assert.ok(near((pb.ink[0] + pb.ink[1]) / 2, mid, 3), mode + ": ...centred in the body (its middle " + (pb.ink[0] + pb.ink[1]) / 2 + " against " + mid + ")");
      // the widest: starts at the gutter, cut at the paper's edge (recorded: a formula never wraps)
      const pw = pr.formulas[pr.formulas.length - 2];
      assert.ok(near(pw.box[0], bL + 18, 1) && near(pw.box[1], bR - 18, 1), mode + ": a formula wider than the paper takes the body less the inset (" + pw.box + ")");
      assert.ok(near(pw.ink[0], bL + 18, 1), mode + ": ...its ink starting at the gutter, not the column (" + pw.ink[0] + "; before: " + screen.formulas[screen.formulas.length - 2].ink[0] + ")");
      assert.ok(pw.ink[1] > bR, mode + ": ...and cut at the paper's edge (" + pw.ink[1] + " past " + bR + "), the recorded limit");
      await page.emulateMedia({ media: "screen" }); await frames(page, 3);
      const back = await page.evaluate(facts) as Facts;
      assert.deepEqual(back, screen, mode + ": every screen value returns");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});
