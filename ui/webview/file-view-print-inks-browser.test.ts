// What the print block still missed after round 1 (Slice 3 of plans/markdown-viewer.md, review round 2), measured under print
// media over the real bundle and sheets. The block whitens the page and the card for every file kind but coloured only
// `.fileview-md` descendants, so (1) the Raw view of a note and every code file kept the dark theme's light inks on the white
// page: `.hljs { color: var(--hl-fg) }` and the token rules beat the inherited black (1.67:1 for the code, 1.69:1 for the row
// numbers); (2) hljs writes a function name as
// `class="hljs-title function_"`, two classes, which outranked the block's `.fileview-md pre code span`, so one token per
// fence printed in the screen's title colour while every other token printed black; (3) a region comment's rectangle and
// author chip printed amber, and with backgrounds off (the browser's default) Chromium repaints a box that has a background
// as solid white, so the rectangle blanked the part of the figure the comment was about; (4) a pending insertion printed
// under a 2px accent underline (1.61:1 in the dark theme) over a green wash, a deletion's struck label in the dim ink over a
// red wash, and the Raw view's author chip in the dim ink on an accent wash. Now: code, tokens and row numbers print black
// wherever they are in the body; the region overlay is left out (the comments it belongs to are, and the figure is the
// content); the change marks print in black (a black underline, a black struck label, a black-ringed chip) with no wash, so a
// reader who printed with changes shown sees them as a redline (Show changes inline turns every mark off, for a print without
// them). And (5) a wide table was squeezed into the 80ch column on paper wide enough for it (A4 landscape: 761 of 1123px)
// and its words broken at arbitrary characters; in print the table keeps the screen's room, the body less the root's inset,
// and grows out of the column into both gutters as it does on screen (the cqi cap and translate restated in the print block,
// where paper has no scrollbar and no script runs). Round 3: the row numbers, black since round 2, kept the screen's opacity
// (0.55 on a Raw row, 0.32 in a fence: the fence's 2.24:1 on white), so the block sets both gutters to full ink; the Raw
// row's and a source file's are asserted here, the fence's in file-view-print-browser.test.ts. Each value returns under
// screen media. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, openPanel, pageHtml, frames, REPORT, ROOT, SID, MT, ORIGIN, UI, type Mode } from "./real-viewer-leg";

const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const F = "```";
const PARAS = Array.from({ length: 6 }, (_, i) => "Paragraph " + (i + 1) + ": lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor.");
const NOTE = ["# Print me", "", "![Figure](figure.png)", "", "A paragraph with `inline code` and a [link](https://example.test/).", "",
  F + "python", "# a comment", "class Foo:", "    def bar(self, n):", "        return 'str' + str(n * 2)", F, "", ...PARAS.flatMap((p) => [p, ""])].join("\n");
const PY = ROOT + "/app/main.py";
const PYSRC = ["# the app's entry point", "import os", "", "def main(argv):", "    name = 'notes-api'", "    return len(argv) + 42", ""].join("\n");
const T0 = 1757145600000;
const HASH = "1".repeat(64);
// one insertion (paragraph 2's opening words) and one deletion (a word of paragraph 4), the shape the kernel's status carries
const insFrom = NOTE.indexOf(PARAS[1]) + PARAS[1].indexOf("lorem ipsum"), delAt = NOTE.indexOf(PARAS[3]) + PARAS[3].indexOf("sit amet");
const HUNKS = [
  { id: "h-ins", author: "api", ts: T0 - 30000, kind: "ins", curFrom: insFrom, curTo: insFrom + 11, baseFrom: insFrom, baseTo: insFrom, oldText: "", newText: "lorem ipsum", anchor: null },
  { id: "h-del", author: "api", ts: T0 - 20000, kind: "del", curFrom: delAt, curTo: delAt, baseFrom: delAt, baseTo: delAt + 6, oldText: "dolor ", newText: "", anchor: null },
];
// a region comment on the figure (the hash is not the picture's, so the rectangle is the dotted `fc-unknown` one; a region all the same)
const REGION = { id: T0 + "-0", author: "you", ts: T0, body: "Crop this band.", replies: [], resolved: false,
  anchor: { quote: "![Figure](figure.png)", prefix: "# Print me\n\n", suffix: "\n\nA paragraph" }, target: { kind: "image", region: { x: 0.1, y: 0.2, w: 0.3, h: 0.5 }, hash: HASH, src: "figure.png" } };
const BLACK = "rgb(0, 0, 0)", CLEAR = "rgba(0, 0, 0, 0)";

// ── the sheet: the block names the Raw and code views, the region overlay and the change marks ─────────────────

test("the print block colours code wherever it is in the body, hides the region overlay, prints the change marks and chips black, and gives a wide table the body's room", () => {
  const css = read("styles.css"); const block = css.slice(css.indexOf("@media print {"));
  assert.ok(block.includes('.fileview-body code.hljs, .fileview-body code.hljs span, .fileview-body .fv-cl::before { color: black; }'), "the Raw and code views' ink, and a two-class token's (code.hljs span outranks .hljs-title.function_)");
  assert.ok(block.includes(".fileview-body .fc-overlay { display: none; }"), "the region overlay is left out");
  assert.ok(block.includes(".fileview-body .fc-ins, .fileview-body .fc-del { border-bottom-color: black; background: none; }"), "the change marks' underline prints black, no wash");
  assert.ok(block.includes(".fileview-body .fc-del::before { color: black; background: none; }"), "the struck label prints black");
  assert.ok(block.includes(".fileview-body .fc-ins::after, .fileview-body .fc-del::after { color: black; background: none; box-shadow: inset 0 0 0 1px black; }"), "the author chip prints black in a black ring");
  assert.ok(block.includes(".fileview-md table { display: table; width: max-content; overflow: visible; overflow-wrap: anywhere; }"), "a table is a table again, at its own width");
  assert.ok(block.includes(".fileview-md > table { max-width: calc(100cqi - 36px); translate:"), "a table of the page's own keeps the body's room and the screen's shift");
  assert.doesNotMatch(block, /\.fileview-md > table \{[^}]*translate: none/, "the shift into the gutters stands in print");
});

// ── the browser legs ──────────────────────────────────────────────────────────────────────────────

type Facts = Record<string, any>;
function codeFacts(): Facts {
  const q = (s: string) => document.querySelector(s) as HTMLElement | null; const cs = (e: Element, p?: string) => getComputedStyle(e, p);
  const body = q(".fileview-body")!, code = body.querySelector("code.hljs")!;
  const toks = Array.from(code.querySelectorAll("span")).filter((s) => /\bhljs-/.test(s.className));
  const fn = toks.find((s) => s.classList.contains("hljs-title") && s.classList.contains("function_")) || null;
  const row = body.querySelector(".fv-cl"), ins = body.querySelector(".fc-ins"), del = body.querySelector(".fc-del"), chip = body.querySelector(".fc-ins[data-fc-chip]");
  return { matchesPrint: matchMedia("print").matches, cardColor: cs(q(".fileview")!).color, codeColor: cs(code).color, tokens: toks.length,
    notBlack: toks.filter((s) => cs(s).color !== "rgb(0, 0, 0)").map((s) => s.className + " " + JSON.stringify((s.textContent || "").slice(0, 12))),
    fn: fn ? { text: fn.textContent, color: cs(fn).color } : null, str: (() => { const s = code.querySelector(".hljs-string"); return s ? cs(s).color : null; })(),
    row: row ? { color: cs(row, "::before").color, opacity: cs(row, "::before").opacity } : null,
    ins: ins ? { text: ins.textContent, color: cs(ins).color, border: cs(ins).borderBottomColor, borderW: cs(ins).borderBottomWidth, bg: cs(ins).backgroundColor } : null,
    del: del ? { label: cs(del, "::before").content, color: cs(del, "::before").color, bg: cs(del, "::before").backgroundColor, deco: cs(del, "::before").textDecorationLine, border: cs(del).borderBottomColor } : null,
    chip: chip ? { text: cs(chip, "::after").content, color: cs(chip, "::after").color, bg: cs(chip, "::after").backgroundColor, ring: cs(chip, "::after").boxShadow } : null };
}

async function seedChanges(page: any): Promise<void> {
  await page.evaluate((h: unknown) => { (window as any).__status = Object.assign({}, (window as any).__status, { hunks: h }); }, HUNKS);
  await openPanel(page);
  await page.waitForFunction(() => !!document.querySelector(".fileview-body .fc-ins") && !!document.querySelector(".fileview-body .fc-del"), null, { timeout: 10000 });
  await frames(page, 2);
}

test("under print media the Raw view's code, tokens, row numbers, change marks and author chips print black; a source file's code and rows too; screen media restores each", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, light] of [["pane", false], ["chat", false], ["pane", true]] as [Mode, boolean][]) {
      const cell = `${mode}${light ? " light" : " dark"} raw`;
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE, [PY]: PYSRC }, raw: true });
      if (light) { await page.evaluate(() => { document.body.classList.add("theme-light"); }); await frames(page, 2); }
      await seedChanges(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-body .fc-ins[data-fc-chip]"), null, { timeout: 10000 });
      const screen = await page.evaluate(codeFacts);
      assert.equal(screen.matchesPrint, false);
      assert.ok(screen.tokens > 5, cell + ": the Raw view is highlighted as markdown (" + screen.tokens + " tokens)"); assert.notEqual(screen.codeColor, BLACK, cell + ": on screen the code wears the highlight's ink");
      assert.ok(screen.row && screen.row.color !== BLACK, cell + ": ...and the row numbers the dim tier"); assert.ok(screen.chip, cell + ": the Raw view carries the author chip"); assert.equal(screen.chip.text, '"api"');
      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const pr = await page.evaluate(codeFacts);
      assert.equal(pr.matchesPrint, true); assert.equal(pr.cardColor, BLACK);
      assert.equal(pr.codeColor, BLACK, cell + ": the Raw view's code prints black (before: " + screen.codeColor + ", 1.67:1 on white in the dark theme)");
      assert.deepEqual(pr.notBlack, [], cell + ": every token prints black: " + pr.notBlack.join("; "));
      assert.equal(pr.row.color, BLACK, cell + ": the row numbers print black (before: " + screen.row.color + " at " + screen.row.opacity + ")");
      assert.equal(pr.row.opacity, "1", cell + ": ...at full ink (the screen's " + screen.row.opacity + " stood in print before round 3)");
      assert.ok(pr.ins, cell + ": the insertion's mark stands"); assert.equal(pr.ins.border, BLACK, cell + ": ...its underline prints black (before: " + screen.ins.border + ")"); assert.equal(pr.ins.borderW, "2px"); assert.equal(pr.ins.bg, CLEAR, cell + ": ...with no wash"); assert.equal(pr.ins.color, BLACK);
      assert.ok(pr.del, cell + ": the deletion's point stands"); assert.equal(pr.del.label, '"dolor "', cell + ": the struck label is generated"); assert.equal(pr.del.color, BLACK, cell + ": ...and prints black (before: " + screen.del.color + ")"); assert.equal(pr.del.bg, CLEAR); assert.equal(pr.del.deco, "line-through"); assert.equal(pr.del.border, BLACK);
      assert.equal(pr.chip.text, '"api"', cell + ": the author chip prints"); assert.equal(pr.chip.color, BLACK, cell + ": ...in black (before: " + screen.chip.color + ")"); assert.equal(pr.chip.bg, CLEAR, cell + ": ...with no wash"); assert.match(pr.chip.ring, /rgb\(0, 0, 0\)/, cell + ": ...in a black ring");
      // the code view of a source file (the same rows: long lines always soft-wrap, so codeBlock builds the numbered rows)
      await page.emulateMedia({ media: "screen" }); await frames(page, 2);
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [PY, SID]);
      await page.waitForFunction(() => !!document.querySelector(".fileview-pre code.hljs .fv-cl .hljs-keyword"), null, { timeout: 10000 }); await frames(page, 2);
      const screenPy = await page.evaluate(codeFacts);
      assert.ok(screenPy.fn, cell + ": the .py file has a function name token (hljs-title function_)"); assert.equal(screenPy.fn.text, "main"); assert.notEqual(screenPy.codeColor, BLACK); assert.notEqual(screenPy.row.color, BLACK);
      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const prPy = await page.evaluate(codeFacts);
      assert.equal(prPy.codeColor, BLACK, cell + ": a .py file's code prints black (before: " + screenPy.codeColor + ")"); assert.deepEqual(prPy.notBlack, [], cell + ": every token of the .py file prints black: " + prPy.notBlack.join("; "));
      assert.equal(prPy.fn.color, BLACK, cell + ": the function name too (before: " + screenPy.fn.color + ")");
      assert.equal(prPy.row.color, BLACK, cell + ": the .py file's row numbers print black (before: " + screenPy.row.color + ")"); assert.equal(prPy.row.opacity, "1", cell + ": ...at full ink");
      await page.emulateMedia({ media: "screen" }); await frames(page, 3);
      const back = await page.evaluate(codeFacts);
      assert.equal(back.matchesPrint, false); assert.equal(back.codeColor, screenPy.codeColor, cell + ": the code's ink returns"); assert.equal(back.row.color, screenPy.row.color, cell + ": the row numbers' ink returns"); assert.equal(back.row.opacity, screenPy.row.opacity, cell + ": ...and their dim");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

function renderedFacts(): Facts {
  const q = (s: string) => document.querySelector(s) as HTMLElement | null; const cs = (e: Element, p?: string) => getComputedStyle(e, p);
  const md = q(".fileview-md")!; const img = md.querySelector("img") as HTMLImageElement | null;
  const overlay = md.querySelector(".fc-overlay"), region = md.querySelector(".fc-region"), chip = md.querySelector(".fc-region-chip");
  const toks = Array.from(md.querySelectorAll("pre code span")).filter((s) => /\bhljs-/.test(s.className));
  const fn = toks.find((s) => s.classList.contains("hljs-title") && s.classList.contains("function_")) || null;
  const ins = md.querySelector(".fc-ins"), del = md.querySelector(".fc-del");
  return { matchesPrint: matchMedia("print").matches, mdColor: cs(md).color, img: img ? { complete: img.complete, natural: img.naturalWidth, width: img.getBoundingClientRect().width } : null,
    overlay: overlay ? cs(overlay).display : "(none)", region: region ? { display: cs(region).display, border: cs(region).borderTopColor, bg: cs(region).backgroundColor, painted: region.getClientRects().length > 0 } : null,
    chip: chip ? { display: cs(chip).display, bg: cs(chip).backgroundColor, painted: chip.getClientRects().length > 0 } : null,
    tokens: toks.length, notBlack: toks.filter((s) => cs(s).color !== "rgb(0, 0, 0)").map((s) => s.className + " " + JSON.stringify((s.textContent || "").slice(0, 12))),
    fn: fn ? { text: fn.textContent, color: cs(fn).color } : null,
    ins: ins ? { border: cs(ins).borderBottomColor, bg: cs(ins).backgroundColor, chip: cs(ins, "::after").content } : null,
    del: del ? { label: cs(del, "::before").content, color: cs(del, "::before").color, bg: cs(del, "::before").backgroundColor, border: cs(del).borderBottomColor } : null };
}

/** A 600x300 PNG, drawn in a page, for the figure the note embeds (the kernel's /file route is answered with it). */
async function figurePng(browser: any): Promise<Buffer> {
  const p = await browser.newPage();
  const url: string = await p.evaluate(() => { const c = document.createElement("canvas"); c.width = 600; c.height = 300; const cx = c.getContext("2d")!; cx.fillStyle = "rgb(100,120,110)"; cx.fillRect(0, 0, 600, 300); return c.toDataURL("image/png"); });
  await p.close();
  return Buffer.from(url.slice(url.indexOf(",") + 1), "base64");
}

test("under print media a region comment's overlay is left out (the figure prints whole), a fence's function name prints black with the other tokens, and the Rendered change marks print black; screen media restores each", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const png = await figurePng(browser);
    for (const mode of ["pane", "feed"] as Mode[]) {
      const cell = mode + " dark rendered";
      const page = await browser.newPage({ viewport: { width: 900, height: 700 } }); const errors: string[] = []; page.on("pageerror", (e: Error) => { errors.push(e.message); });
      const html = pageHtml(mode, { [REPORT]: NOTE }, MT);
      await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => route.fulfill({ status: 200, contentType: "text/html", body: html }));
      await page.route((u: URL) => u.href.startsWith(ORIGIN) && u.pathname === "/file", (route: any) => route.fulfill({ status: 200, contentType: "image/png", body: png }));   // registered later, so matched first: the figure's bytes
      await page.goto(ORIGIN + "/");
      await page.evaluate(([c, h, hunks]: [unknown, string, unknown]) => { const s = (window as any).__status; s.store.comments = [c]; s.unsent.comments = [(c as any).id]; s.fileHash = h; s.hunks = hunks; }, [REGION, HASH, HUNKS]);
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth === 600; }, null, { timeout: 10000 });
      await openPanel(page);
      await page.waitForFunction(() => !!document.querySelector(".fileview-md .fc-region") && !!document.querySelector(".fileview-md .fc-ins") && !!document.querySelector(".fileview-md .fc-del"), null, { timeout: 10000 }); await frames(page, 2);
      const screen = await page.evaluate(renderedFacts);
      assert.equal(screen.matchesPrint, false);
      assert.ok(screen.region && screen.region.painted, cell + ": the region's rectangle is painted on screen"); assert.notEqual(screen.region.bg, CLEAR, cell + ": ...with its wash"); assert.ok(screen.chip && screen.chip.painted, cell + ": ...and its author chip");
      assert.ok(screen.fn, cell + ": the fence has a function name token (hljs-title function_)"); assert.equal(screen.fn.text, "bar"); assert.notEqual(screen.fn.color, BLACK);
      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const pr = await page.evaluate(renderedFacts);
      assert.equal(pr.matchesPrint, true); assert.equal(pr.mdColor, BLACK);
      assert.equal(pr.overlay, "none", cell + ": the region overlay is left out in print (before: an amber rectangle, and a solid white box over the figure with backgrounds off)");
      assert.ok(pr.region && !pr.region.painted, cell + ": ...so the rectangle paints nothing"); assert.ok(pr.chip && !pr.chip.painted, cell + ": ...nor the chip");
      assert.ok(pr.img && pr.img.width > 0, cell + ": the figure itself prints");
      assert.equal(pr.fn.color, BLACK, cell + ": the function name prints black (before: " + screen.fn.color + "; its two-class selector outranked the block's)"); assert.deepEqual(pr.notBlack, [], cell + ": every token prints black: " + pr.notBlack.join("; "));
      assert.ok(pr.ins, cell + ": the insertion's mark stands in Rendered"); assert.equal(pr.ins.border, BLACK, cell + ": ...black underline (before: " + screen.ins.border + ")"); assert.equal(pr.ins.bg, CLEAR); assert.equal(pr.ins.chip, "none", cell + ": Rendered marks carry no chip");
      assert.ok(pr.del, cell + ": the deletion's point stands"); assert.equal(pr.del.color, BLACK, cell + ": ...its struck label black (before: " + screen.del.color + ")"); assert.equal(pr.del.bg, CLEAR); assert.equal(pr.del.border, BLACK);
      await page.emulateMedia({ media: "screen" }); await frames(page, 3);
      const back = await page.evaluate(renderedFacts);
      assert.equal(back.matchesPrint, false); assert.equal(back.overlay, screen.overlay, cell + ": the overlay is back"); assert.ok(back.region.painted, cell + ": the rectangle paints again"); assert.equal(back.fn.color, screen.fn.color, cell + ": the token's ink returns"); assert.equal(back.ins.border, screen.ins.border);
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});

// ── the wide table on landscape paper ─────────────────────────────────────────────────────────────

const COLS = (n: number) => Array.from({ length: n }, (_, i) => "column_head_" + (i + 1));
const TABLE = (n: number) => ["| " + COLS(n).join(" | ") + " |", "|" + COLS(n).map(() => "---").join("|") + "|",
  ...Array.from({ length: 2 }, (_, r) => "| " + COLS(n).map((_, c) => "wide_cell_r" + (r + 1) + "c" + (c + 1)).join(" | ") + " |")].join("\n");
const TABLE_NOTE = (n: number) => ["# Print me", "", "A paragraph before the table.", "", TABLE(n), "", "A paragraph after the table.", ""].join("\n");

function tableFacts(): Facts {
  const cs = (e: Element) => getComputedStyle(e);
  const md = document.querySelector(".fileview-md") as HTMLElement, body = document.querySelector(".fileview-body") as HTMLElement;
  const padL = parseFloat(cs(md).paddingLeft), padR = parseFloat(cs(md).paddingRight); const mr = md.getBoundingClientRect(), br = body.getBoundingClientRect();
  const table = md.querySelector(":scope > table") as HTMLElement; const tr = table.getBoundingClientRect();
  const cells = Array.from(table.querySelectorAll("td, th")) as HTMLElement[];
  const lines = (c: HTMLElement) => { const r = document.createRange(); r.selectNodeContents(c); return r.getClientRects().length; };
  return { matchesPrint: matchMedia("print").matches, bodyW: br.width, room: br.width - 36, columnW: mr.width - padL - padR, display: cs(table).display, overflowX: cs(table).overflowX, translate: cs(table).translate,
    width: tr.width, scroll: table.scrollWidth, client: table.clientWidth, gapL: tr.left - br.left, gapR: br.right - tr.right, cells: cells.length, midWord: cells.filter((c) => lines(c) > 1).length };
}

test("on A4 landscape paper (1123px) a 6-column table that fits the paper but not the 80ch column prints at its own width, centred in the body's room, no cell broken; a 14-column one takes the whole room; screen media restores the scrolling block", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const n of [6, 14]) {
      const cell = n + "-col";
      const { page, errors } = await openViewer(browser, "pane", 1123, 794, { docs: { [REPORT]: TABLE_NOTE(n) } });
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > table"), null, { timeout: 10000 }); await frames(page, 2);
      const screen = await page.evaluate(tableFacts);
      assert.equal(screen.matchesPrint, false); assert.equal(screen.display, "block", cell + ": on screen the table is a block");
      assert.ok(screen.columnW < 800 && screen.columnW > 700, cell + ": the column is about 80ch (" + screen.columnW + ")"); assert.ok(screen.width > screen.columnW, cell + ": the table is wider than the column on screen (" + screen.width + ")");
      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const pr = await page.evaluate(tableFacts);
      assert.equal(pr.matchesPrint, true); assert.equal(pr.display, "table", cell + ": in print a table again"); assert.equal(pr.overflowX, "visible");
      assert.ok(pr.width > pr.columnW + 20, cell + ": the table grows out of the column (" + pr.width + " against a column of " + pr.columnW + "; before: squeezed to the column)");
      assert.ok(pr.width <= pr.room + 0.5, cell + ": ...no wider than the body's room (" + pr.width + " in " + pr.room + ")");
      assert.ok(pr.gapL >= 18 - 0.5 && pr.gapR >= 18 - 0.5, cell + ": ...inside the root's inset (" + pr.gapL + ", " + pr.gapR + ")");
      assert.ok(Math.abs(pr.gapL - pr.gapR) <= 1, cell + ": ...centred, as on screen (" + pr.gapL + " / " + pr.gapR + ")");
      assert.ok(pr.scroll <= pr.client + 1, cell + ": nothing hidden past an edge");
      if (n === 6) { assert.equal(pr.midWord, 0, cell + ": no cell breaks a word (before: every one of the 18 did)"); assert.ok(Math.abs(pr.width - screen.width) < 1, cell + ": the table is as wide as it needs (" + pr.width + ", screen " + screen.width + ")"); }
      else assert.ok(Math.abs(pr.width - pr.room) < 1, cell + ": a table wider than the paper takes the whole room (" + pr.width + " of " + pr.room + ")");
      const pdf = await page.pdf({ format: "A4", landscape: true });
      assert.ok(pdf.length > 1000, cell + ": the PDF renders");
      await page.emulateMedia({ media: "screen" }); await frames(page, 3);
      const back = await page.evaluate(tableFacts);
      assert.equal(back.display, "block", cell + ": the table scrolls again"); assert.equal(back.width, screen.width);
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});
