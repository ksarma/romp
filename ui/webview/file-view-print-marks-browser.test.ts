// What the print block missed (Slice 3 of plans/markdown-viewer.md, review round 1), measured under print media over the real
// bundle and sheets: (1) a task box kept `color-scheme: dark` on the white page, and Chromium paints a dark-scheme
// UNCHECKED box as a near-black filled square, so an open task printed as done; the box prints in the light scheme now. (2) A
// Markdown link that names a file (`[note](docs/other.md)`, marked `a.file-uri-link` by file-view-links.ts) outranked the
// block's `.fileview-md a` at one class more, and printed in the screen's link ink (2.48:1 pale blue on white in the dark
// theme) with no underline; the block names the class now. (3) A table wider than the paper kept its screen box (`display:
// block; overflow-x: auto`, the cqi cap and the translate), and paper cannot scroll: columns past the page edge were lost;
// in print a table is a table again, its cells wrapping to fit the column. (4) The comment marks (`.fc-hl`, the context
// and preselection rings) kept their amber ring while the comments themselves were hidden; the marks print bare. Each
// value returns under screen media. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT, type Mode } from "./real-viewer-leg";

const COLS = Array.from({ length: 14 }, (_, i) => "column_head_" + (i + 1));
const WIDE = ["| " + COLS.join(" | ") + " |", "|" + COLS.map(() => "---").join("|") + "|",
  ...Array.from({ length: 3 }, (_, r) => "| " + COLS.map((_, c) => "wide_cell_r" + (r + 1) + "c" + (c + 1)).join(" | ") + " |")].join("\n");
const NOTE = ["# Print me", "", "See [the other note](docs/other.md) and [a plain link](https://example.test/x) here.", "",
  "- [ ] open task", "- [x] done task", "- plain item", "", WIDE, "",
  ...Array.from({ length: 12 }, (_, i) => "Paragraph " + (i + 1) + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + "."), ""].join("\n");
const T0 = 1757145600000;
const COMMENT = { id: (T0 + 1) + "-3", author: "you", ts: T0 + 1, body: "Note on paragraph 3.", anchor: { quote: "Paragraph 3: lorem ipsum", prefix: "", suffix: " dolor sit amet" }, replies: [], resolved: false };

type Facts = Record<string, any>;
function facts(): Facts {
  const md = document.querySelector(".fileview-md") as HTMLElement; const cs = (e: Element) => getComputedStyle(e);
  const boxes = Array.from(md.querySelectorAll('li.task-list-item input[type="checkbox"]')) as HTMLInputElement[];
  const anchors = Array.from(md.querySelectorAll("a")) as HTMLAnchorElement[];
  const fileA = anchors.find((a) => a.textContent === "the other note")!, plainA = anchors.find((a) => a.textContent === "a plain link")!;
  const table = md.querySelector(":scope > table") as HTMLElement; const tr = table.getBoundingClientRect(), mr = md.getBoundingClientRect();
  const mark = md.querySelector(".fc-hl") as HTMLElement | null; const aside = document.querySelector(".fileview-aside") as HTMLElement | null;
  const padL = parseFloat(cs(md).paddingLeft), padR = parseFloat(cs(md).paddingRight);
  return { matchesPrint: matchMedia("print").matches, mdColor: cs(md).color,
    boxes: boxes.map((b) => ({ checked: b.checked, disabled: b.disabled, scheme: cs(b).colorScheme })),
    fileA: { cls: fileA.className, color: cs(fileA).color, deco: cs(fileA).textDecorationLine }, plainA: { color: cs(plainA).color, deco: cs(plainA).textDecorationLine },
    table: { display: cs(table).display, overflowX: cs(table).overflowX, translate: cs(table).translate, client: table.clientWidth, scroll: table.scrollWidth, width: tr.width, columnWidth: mr.width - padL - padR, inColumn: tr.left >= mr.left + padL - 0.5 && tr.right <= mr.right - padR + 0.5, cells: table.querySelectorAll("td, th").length, lastCellText: (table.querySelector("tbody tr:last-child td:last-child") as HTMLElement).textContent },
    mark: mark ? { text: mark.textContent, bg: cs(mark).backgroundColor, shadow: cs(mark).boxShadow, outline: cs(mark).outlineStyle } : null, aside: aside ? cs(aside).display : "(none mounted)" };
}

test("under print media: an open task box is drawn in the light scheme, a link naming a file prints black and underlined, a 14-column table is a table that fits the column with every cell on the page, and a comment's mark prints bare; screen media restores each", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const [mode, light] of [["pane", false], ["chat", false], ["feed", false], ["pane", true]] as [Mode, boolean][]) {
      const cell = `${mode}${light ? " light" : " dark"}`;
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE } });
      if (light) { await page.evaluate(() => { document.body.classList.add("theme-light"); }); await frames(page, 2); }
      // one stored comment on paragraph 3: the real panel paints its mark once it opens (the status auto-reply carries the store)
      await page.evaluate((c: unknown) => { const s = (window as any).__status; s.store.comments = [c]; s.unsent.comments = [(c as any).id]; }, COMMENT);
      await openPanel(page);
      await page.waitForFunction(() => document.querySelectorAll(".fileview-md .fc-hl").length > 0, null, { timeout: 10000 }); await frames(page, 2);
      const screen = await page.evaluate(facts);
      assert.equal(screen.matchesPrint, false);
      assert.equal(screen.boxes.length, 2, cell + ": two task boxes"); assert.deepEqual(screen.boxes.map((b: any) => b.checked), [false, true]); assert.deepEqual(screen.boxes.map((b: any) => b.disabled), [true, true], cell + ": the sanitizer's inert boxes");
      assert.deepEqual(screen.boxes.map((b: any) => b.scheme), light ? ["light", "light"] : ["dark", "dark"], cell + ": on screen the boxes are drawn for the theme");
      assert.match(screen.fileA.cls, /\bfile-uri-link\b/, cell + ": the link naming a file carries the class"); assert.equal(screen.fileA.deco, "none", cell + ": ...un-underlined on screen"); assert.notEqual(screen.fileA.color, "rgb(0, 0, 0)");
      assert.equal(screen.table.display, "block", cell + ": on screen the table is a scrolling block"); assert.ok(screen.table.scroll > screen.table.client, cell + ": ...scrolling its 14 columns");
      assert.ok(screen.mark, cell + ": the comment's mark is painted"); assert.equal(screen.mark.text, "Paragraph 3: lorem ipsum"); assert.notEqual(screen.mark.shadow, "none", cell + ": ...ringed on screen");
      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const pr = await page.evaluate(facts);
      assert.equal(pr.matchesPrint, true); assert.equal(pr.mdColor, "rgb(0, 0, 0)", cell + ": the prose prints black"); assert.equal(pr.aside, "none", cell + ": the aside is hidden");
      assert.deepEqual(pr.boxes.map((b: any) => b.scheme), ["light", "light"], cell + ": the task boxes print in the light scheme (a dark-scheme unchecked box prints as a filled dark square)");
      assert.equal(pr.fileA.color, "rgb(0, 0, 0)", cell + ": the link naming a file prints black (before: the screen's link ink, " + screen.fileA.color + ")");
      assert.equal(pr.fileA.deco, "underline", cell + ": ...underlined"); assert.equal(pr.plainA.color, "rgb(0, 0, 0)"); assert.equal(pr.plainA.deco, "underline", cell + ": as the plain link does");
      assert.equal(pr.table.display, "table", cell + ": in print the table is a table again (before: a block scrolling " + screen.table.scroll + "px inside " + screen.table.client + ")");
      assert.equal(pr.table.overflowX, "visible", cell + ": ...nothing to scroll"); assert.equal(pr.table.translate, "none", cell + ": ...not moved");
      assert.ok(pr.table.scroll <= pr.table.client + 1, cell + ": ...no hidden columns (" + pr.table.scroll + " in " + pr.table.client + ")");
      assert.ok(pr.table.width <= pr.table.columnWidth + 0.5, cell + ": ...no wider than the column (" + pr.table.width + " in " + pr.table.columnWidth + ")"); assert.ok(pr.table.inColumn, cell + ": ...inside it");
      assert.equal(pr.table.cells, 56, cell + ": all 56 cells are laid out"); assert.equal(pr.table.lastCellText, "wide_cell_r3c14");
      assert.ok(pr.mark, cell + ": the mark's element stands (the text is printed)");
      assert.equal(pr.mark.bg, "rgba(0, 0, 0, 0)", cell + ": the mark prints with no wash"); assert.equal(pr.mark.shadow, "none", cell + ": ...and no ring (before: the warn ring, printed even without backgrounds)"); assert.equal(pr.mark.outline, "none");
      await page.emulateMedia({ media: "screen" }); await frames(page, 3);
      const back = await page.evaluate(facts);
      assert.equal(back.matchesPrint, false);
      assert.deepEqual(back.boxes.map((b: any) => b.scheme), screen.boxes.map((b: any) => b.scheme), cell + ": the boxes return to the theme's scheme");
      assert.equal(back.fileA.color, screen.fileA.color, cell + ": the file link's ink returns"); assert.equal(back.fileA.deco, "none");
      assert.equal(back.table.display, "block", cell + ": the table scrolls again"); assert.equal(back.table.scroll, screen.table.scroll);
      assert.equal(back.mark.shadow, screen.mark.shadow, cell + ": the mark's ring returns");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  });
});
