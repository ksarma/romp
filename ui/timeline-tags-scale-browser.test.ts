// THE SESSIONS & TAGS DIALOG'S LAYOUT WITH MANY TAGS, MEASURED (the user 2026-09-09: with ten tags the tag
// rows and the pane-filter matrix filled the dialog and "the sessions" showed two rows under the fold).
// timeline-tags-scale.test.ts executes the behaviour over the fake DOM; nothing there measures a pixel. This
// module mounts the worktree's real view in a browser at the size the user asked about, a 1300px-tall page,
// with thirty tags and forty sessions, opens the dialog and measures: every tag row one line (at most 32px),
// the tag table scrolling within itself, the card never scrolling or clipping as a whole, and the working
// area (the search box, "tag all" and at least eight session rows) on screen without scrolling the dialog;
// then, with the filter matrix open, thirty-two chips per row wrapping inside the card's width. Skips LOUDLY
// without a playwright browser (CI installs none). Synthetic names and ids only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const VIEW = fs.readFileSync(path.resolve(EXT, "..", "ui", "romp-timeline-view.js"), "utf8");
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// the kernel's timeline page, reduced to the view: the three Obsidian DOM helpers the panel expects on every
// element (timeline-boot.ts installDomHelpers) and the module shim the page wraps the file in (kernel.py _timeline_body)
const HELPERS = `var P=HTMLElement.prototype;
if(!P.createEl)P.createEl=function(tag,o){var e=document.createElement(tag);if(o&&o.cls)e.className=o.cls;if(o&&o.text)e.textContent=o.text;this.appendChild(e);return e;};
if(!P.createDiv)P.createDiv=function(o){return this.createEl('div',o);};if(!P.createSpan)P.createSpan=function(o){return this.createEl('span',o);};`;
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>html,body{margin:0;background:#1e1e1e;color:#ccc;font:13px sans-serif}</style></head>
<body><div id=host></div><script>${HELPERS}</script><script>var module={exports:{}};(function(module,exports){\n${VIEW}\n})(module,module.exports);
var TimelinePanel=module.exports.TimelinePanel; window.panel = new TimelinePanel(document.getElementById('host'));</script></body></html>`;

const PALETTE = ["#1EA1EB", "#54B204", "#4EA8A9", "#DD42FF", "#E87221", "#4EC9B0", "#E0AF68", "#F7768E", "#7AA2F7", "#9ECE6A", "#BB9AF7", "#FF9E64"];
const NAMES30 = Array.from({ length: 30 }, (_, i) => "tag-" + String(i + 1).padStart(2, "0"));
const now = 1_781_000_000;
const DATA = {
  now, turns: {}, messages: [], judging: [], palette: PALETTE,
  sessions: Array.from({ length: 40 }, (_, i) => ({
    id: "s" + (i + 1), name: "job-" + String(i + 1).padStart(2, "0"), color: PALETTE[i % 12], state: "working", live: true, model: "Opus", effort: "high",
    context: 40, since: now - 60, awaiting: [], compacting: [], pendingMail: 0, compactions: [], faded: false, stale: false,
  })),
  views: {
    active: "all", at: 100, seq: 1000,
    actives: { chat: { tags: NAMES30.slice(0, 12) }, timeline: { all: true }, outline: { none: true } },
    tags: NAMES30.map((name, i) => ({ id: "g" + (i + 1), name, color: PALETTE[i % 12], members: i < 20 ? ["s" + (i + 1)] : [], mtime: 100 })),
  },
};

async function mount(browser: any) {
  const errors: string[] = [];
  const page = await browser.newPage({ viewport: { width: 1600, height: 1300 } });
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE }));
  await page.goto("http://romp.test/timeline");
  await page.evaluate((data: any) => {
    const p = (window as any).panel;
    p.update(data);
    p.setCaps({ type: "caps", caps: ["tagEdit"], viewsSeq: 1000 });
    p._openViewsDialog(null);
  }, DATA);
  return { page, errors };
}

// the dialog's geometry, read off the live nodes: the card, the tag table, the sessions box, the search
// box, "tag all", the tag rows' pill cells and the session rows' name cells
const measure = (page: any) => page.evaluate(() => {
  const p = (window as any).panel;
  const back = p._viewsDialog as HTMLElement;
  const card = back.firstElementChild as HTMLElement;
  const all = Array.from(card.querySelectorAll("*")) as HTMLElement[];
  const byStyle = (pre: string) => all.find((n) => (n.getAttribute("style") || "").startsWith(pre))!;
  const tgrid = byStyle("display:grid;grid-template-columns:max-content max-content max-content 1fr;");
  const gridBox = all.find((n) => n.getAttribute("style") === "flex:1 1 auto;min-height:0;overflow-y:auto;")!;
  const search = card.querySelector("input[placeholder]") as HTMLElement;
  const tagAll = all.find((n) => n.textContent === "tag all" && n.tagName === "SPAN")!;
  const r = (n: HTMLElement) => { const b = n.getBoundingClientRect(); return { top: b.top, bottom: b.bottom, left: b.left, right: b.right, height: b.height, width: b.width }; };
  const inside = (n: HTMLElement, box: HTMLElement) => { const a = n.getBoundingClientRect(), b = box.getBoundingClientRect(); return a.top >= b.top - 0.5 && a.bottom <= b.bottom + 0.5 && a.height > 0; };
  const pillCells = all.filter((n) => (n as any)._tname);
  const nameCells = all.filter((n) => (n as any)._sid);
  const dots = all.filter((n) => n.dataset.tagDot);
  return {
    viewport: { w: window.innerWidth, h: window.innerHeight },
    card: Object.assign(r(card), { scrollHeight: card.scrollHeight, clientHeight: card.clientHeight, scrollWidth: card.scrollWidth, clientWidth: card.clientWidth }),
    tgrid: Object.assign(r(tgrid), { scrollHeight: tgrid.scrollHeight, clientHeight: tgrid.clientHeight, overflowY: getComputedStyle(tgrid).overflowY }),
    gridBox: Object.assign(r(gridBox), { scrollHeight: gridBox.scrollHeight, clientHeight: gridBox.clientHeight }),
    search: Object.assign(r(search), { visible: inside(search, card) }),
    tagAll: Object.assign(r(tagAll), { visible: inside(tagAll, card) }),
    tagRows: pillCells.length,
    tagRowHeights: pillCells.map((n) => Math.round(n.getBoundingClientRect().height)),
    tagRowsVisible: pillCells.filter((n) => inside(n, tgrid)).length,
    dots: dots.length, swatches: card.querySelectorAll("[role=radio]").length,
    sessionRows: nameCells.length,
    sessionRowsVisible: nameCells.filter((n) => inside(n, gridBox)).length,
    sessionRowHeights: nameCells.slice(0, 3).map((n) => Math.round(n.getBoundingClientRect().height)),
  };
});

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}, 1300px tall, thirty tags and forty sessions: one-line tag rows, the table scrolls within itself, the sessions keep the space`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { page, errors } = await mount(browser);
      const m = await measure(page);
      assert.deepEqual(errors, [], "the view mounted and the dialog opened without a page error");
      assert.equal(m.viewport.h, 1300);
      // the tag rows: thirty, one line each
      assert.equal(m.tagRows, 30); assert.equal(m.dots, 30); assert.equal(m.swatches, 0, "no inline swatch");
      assert.ok(m.tagRowHeights.every((h: number) => h <= 32), "every tag row is one line (at most 32px): " + m.tagRowHeights.join(","));
      // the tag table scrolls within itself and stays within its viewport share
      assert.equal(m.tgrid.overflowY, "auto");
      assert.ok(m.tgrid.scrollHeight > m.tgrid.clientHeight + 100, "thirty rows overflow the capped table, which scrolls them: " + m.tgrid.scrollHeight + " in " + m.tgrid.clientHeight);
      assert.ok(m.tgrid.height <= 0.35 * m.viewport.h + 1, "the table takes at most 35vh: " + m.tgrid.height);
      assert.ok(m.tagRowsVisible >= 8, "a useful number of tag rows shows before scrolling: " + m.tagRowsVisible);
      // the card never scrolls or clips as a whole: its content fits its box
      assert.ok(m.card.scrollHeight <= m.card.clientHeight + 1, "the card holds its content without scroll: " + m.card.scrollHeight + " vs " + m.card.clientHeight);
      assert.ok(m.card.scrollWidth <= m.card.clientWidth + 1, "…and nothing overflows it sideways");
      assert.ok(m.card.height <= 0.9 * m.viewport.h + 1, "the card keeps the 90vh ceiling");
      // the working area: search, tag all and at least eight session rows on screen without scrolling the dialog
      assert.ok(m.search.visible, "the search box is on screen");
      assert.ok(m.tagAll.visible, "tag all is on screen");
      assert.equal(m.sessionRows, 40);
      assert.ok(m.sessionRowsVisible >= 8, "at least eight session rows show without scrolling the dialog: " + m.sessionRowsVisible + " (box " + Math.round(m.gridBox.height) + "px, rows " + m.sessionRowHeights.join("/") + "px)");
      assert.ok(m.gridBox.bottom <= m.card.bottom + 0.5, "the sessions table ends inside the card; it scrolls the rest");
      // the filter matrix open: five rows of thirty-two chips wrap inside the card's width, and the card still fits
      const opened = await page.evaluate(() => {
        const p = (window as any).panel;
        const card = (p._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const cap = Array.from(card.querySelectorAll("span")).find((n) => (n.textContent || "").startsWith("pane filters"))!;
        cap.click();
        const chips = Array.from(card.querySelectorAll("span")).filter((n) => (n.getAttribute("style") || "").startsWith("cursor:pointer;padding:1px 8px;border-radius:9px;"));
        const cb = card.getBoundingClientRect();
        const rows = new Set(chips.map((n) => Math.round(n.getBoundingClientRect().top)));
        return { chips: chips.length, withinWidth: chips.every((n) => { const b = n.getBoundingClientRect(); return b.left >= cb.left && b.right <= cb.right + 0.5; }),
          lines: rows.size, scrollHeight: card.scrollHeight, clientHeight: card.clientHeight,
          caret: (Array.from(card.querySelectorAll("span")).find((n) => (n.textContent || "").startsWith("pane filters"))!.textContent || "").slice(-1) };
      });
      assert.equal(opened.chips, 5 * 32, "All, no tags and thirty tags on each of five rows");
      assert.equal(opened.caret, "▾");
      assert.ok(opened.withinWidth, "every chip lies inside the card's width (the rows wrap)");
      assert.ok(opened.lines > 5, "thirty-two chips per row wrap onto more than one line at this width: " + opened.lines);
      assert.ok(opened.scrollHeight <= opened.clientHeight + 1, "the card still holds its content without scroll with the matrix open");
      const after = await measure(page);
      assert.ok(after.sessionRowsVisible >= 3, "the sessions keep rows on screen even with the matrix open: " + after.sessionRowsVisible);
      // the colour popover: opened from the last row's dot, placed on screen, one layer above the backdrop
      await page.evaluate(() => {
        const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const dot = card.querySelector("[data-tag-dot='g30']") as HTMLElement;
        dot.scrollIntoView();
        dot.click();
      });
      await new Promise((r) => setTimeout(r, 30));   // the popover focuses its current swatch a tick after opening
      const popm = await page.evaluate(() => {
        const p = (window as any).panel;
        const card = (p._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const dot = card.querySelector("[data-tag-dot='g30']") as HTMLElement;
        const pop = p._tagColorPop as HTMLElement;
        const b = pop.getBoundingClientRect();
        const d = dot.getBoundingClientRect();
        return { open: !!pop, swatches: pop.querySelectorAll("[role=radio]").length, onScreen: b.top >= 0 && b.bottom <= window.innerHeight && b.left >= 0 && b.right <= window.innerWidth,
          nearDot: Math.abs(b.top - d.bottom) <= 6 || Math.abs(d.top - b.bottom) <= 6, z: getComputedStyle(pop).zIndex, focused: document.activeElement === pop.querySelector("[aria-checked=true]") };
      });
      assert.ok(popm.open); assert.equal(popm.swatches, 12);
      assert.ok(popm.onScreen, "the popover is on screen");
      assert.ok(popm.nearDot, "…anchored to its dot (below it, or above when below cannot hold it)");
      assert.equal(popm.z, "1003");
      assert.ok(popm.focused, "the current swatch took focus");
    } finally { await browser.close(); }
  });
}
