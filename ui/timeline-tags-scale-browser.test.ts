// THE SESSIONS & TAGS DIALOG'S LAYOUT WITH MANY TAGS, MEASURED (the user 2026-09-09: with ten tags the tag
// rows and the pane-filter matrix filled the dialog and "the sessions" showed two rows under the fold).
// timeline-tags-scale.test.ts executes the behaviour over the fake DOM; nothing there measures a pixel. This
// module mounts the worktree's real view in a browser with thirty (or ten) tags and forty sessions, opens the
// dialog and measures, in three legs per browser:
//  1. the layout across pages: at 1300, 800 and 700px tall every tag row is one line (at most 32px), the tag
//     table scrolls within itself under its 30vh cap, [+ New tag] sits under the table (never under its fold),
//     the card never scrolls or clips as a whole, and the working area (the search box, "tag all", the session
//     rows) stays on screen both folded and with the filter matrix open, whose cell scrolls within itself when
//     the page is short; on a phone held sideways (844x390, touch) the card scrolls as a whole instead of clipping;
//  2. the colour popover and the table at 1300px: the pill of the tag the dialog was opened for keeps its ring
//     inside the table's clip, Enter on a dot opens the popover with the current swatch focused (the browser's
//     focus ring; the inner ring says "current"), Tab closes it back onto the dot, a table scroll that moves the
//     dot closes it, a window resize closes it, the table's scroll survives a repaint (and clamps to 0 when the
//     table no longer scrolls), and a repaint that pushes the rows down re-places the popover on its dot;
//  3. framed shells: with the view in an iframe (offset into the page, or a 200px band at the page's foot) the
//     dialog is adopted into the top document and the popover is placed by the dot's rect there, on screen,
//     untranslated.
// Skips LOUDLY without a playwright browser (CI installs none). Synthetic names and ids only.
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
// two web-shell stand-ins hosting the view as an iframe: one offset into the page, one a 200px band at the
// foot of a 1300px page (the shell's f-timeline band, where a popover translated twice fell off the bottom)
const SHELL_OFFSET = `<!DOCTYPE html><html><body style="margin:0;background:#111"><iframe id=f-timeline src="/timeline" style="position:absolute;left:300px;top:400px;width:1000px;height:600px;border:0"></iframe></body></html>`;
const SHELL_BAND = `<!DOCTYPE html><html><body style="margin:0;background:#111"><div style="height:1100px"></div><iframe id=f-timeline src="/timeline" style="display:block;width:100%;height:200px;border:0"></iframe></body></html>`;

const PALETTE = ["#1EA1EB", "#54B204", "#4EA8A9", "#DD42FF", "#E87221", "#4EC9B0", "#E0AF68", "#F7768E", "#7AA2F7", "#9ECE6A", "#BB9AF7", "#FF9E64"];
const now = 1_781_000_000;
// the panel's data with `nTags` tags (tag-01, tag-02, ...) and forty live sessions
const dataFor = (nTags: number) => {
  const names = Array.from({ length: nTags }, (_, i) => "tag-" + String(i + 1).padStart(2, "0"));
  return {
    now, turns: {}, messages: [], judging: [], palette: PALETTE,
    sessions: Array.from({ length: 40 }, (_, i) => ({
      id: "s" + (i + 1), name: "job-" + String(i + 1).padStart(2, "0"), color: PALETTE[i % 12], state: "working", live: true, model: "Opus", effort: "high",
      context: 40, since: now - 60, awaiting: [], compacting: [], pendingMail: 0, compactions: [], faded: false, stale: false,
    })),
    views: {
      active: "all", at: 100, seq: 1000,
      actives: { chat: { tags: names.slice(0, 12) }, timeline: { all: true }, outline: { none: true } },
      tags: names.map((name, i) => ({ id: "g" + (i + 1), name, color: PALETTE[i % 12], members: i < 20 ? ["s" + (i + 1)] : [], mtime: 100 })),
    },
  };
};
const DATA = dataFor(30);

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
// a scroll event is delivered asynchronously: two frames let it land before the next read
const twoFrames = (page: any) => page.evaluate(() => new Promise<void>((res) => requestAnimationFrame(() => requestAnimationFrame(() => res()))));

type MountOpts = { width?: number; height?: number; mobile?: boolean; nTags?: number };
async function mount(browser: any, opts: MountOpts = {}) {
  const { width = 1600, height = 1300, mobile = false, nTags = 30 } = opts;
  const errors: string[] = [];
  // `mobile`: a phone held sideways. Touch, and the mobile layout viewport: both browsers lay a page without a
  // viewport meta out at 980px wide and scale it to the screen, the way a phone renders it
  const page = await browser.newPage(Object.assign({ viewport: { width, height } }, mobile ? { hasTouch: true, isMobile: true } : {}));
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE }));
  await page.goto("http://romp.test/timeline");
  await page.evaluate((data: any) => {
    const p = (window as any).panel;
    p.update(data);
    p.setCaps({ type: "caps", caps: ["tagEdit"], viewsSeq: 1000 });
    p._openViewsDialog(null);
  }, dataFor(nTags));
  return { page, errors };
}

// the dialog's geometry, read off the live nodes: the card, the tag table, the open matrix's cell (null when
// folded), the sessions box, the search box, "tag all", [+ New tag], the tag rows' pill cells and the session
// rows' name cells
const measure = (page: any) => page.evaluate(() => {
  const p = (window as any).panel;
  const back = p._viewsDialog as HTMLElement;
  const card = back.firstElementChild as HTMLElement;
  const all = Array.from(card.querySelectorAll("*")) as HTMLElement[];
  const byStyle = (pre: string) => all.find((n) => (n.getAttribute("style") || "").startsWith(pre));
  const tgrid = byStyle("display:grid;grid-template-columns:max-content max-content max-content 1fr;")!;
  const mbox = byStyle("flex:0 1 auto;min-height:52px;") || null;
  const gridBox = all.find((n) => n.getAttribute("style") === "flex:1 1000 auto;min-height:96px;overflow-y:auto;")!;
  const search = card.querySelector("input[placeholder]") as HTMLElement;
  const tagAll = all.find((n) => n.textContent === "tag all" && n.tagName === "SPAN")!;
  const newTag = all.find((n) => n.textContent === "+ New tag" && n.tagName === "SPAN")!;
  const r = (n: HTMLElement) => { const b = n.getBoundingClientRect(); return { top: b.top, bottom: b.bottom, left: b.left, right: b.right, height: b.height, width: b.width }; };
  const inside = (n: HTMLElement, box: HTMLElement) => { const a = n.getBoundingClientRect(), b = box.getBoundingClientRect(); return a.top >= b.top - 0.5 && a.bottom <= b.bottom + 0.5 && a.height > 0; };
  const pillCells = all.filter((n) => (n as any)._tname);
  const nameCells = all.filter((n) => (n as any)._sid);
  const dots = all.filter((n) => n.dataset.tagDot);
  return {
    viewport: { w: window.innerWidth, h: window.innerHeight },
    card: Object.assign(r(card), { scrollHeight: card.scrollHeight, clientHeight: card.clientHeight, scrollWidth: card.scrollWidth, clientWidth: card.clientWidth }),
    tgrid: Object.assign(r(tgrid), { scrollHeight: tgrid.scrollHeight, clientHeight: tgrid.clientHeight, overflowY: getComputedStyle(tgrid).overflowY }),
    mbox: mbox ? Object.assign(r(mbox), { scrollHeight: mbox.scrollHeight, clientHeight: mbox.clientHeight }) : null,
    gridBox: Object.assign(r(gridBox), { scrollHeight: gridBox.scrollHeight, clientHeight: gridBox.clientHeight }),
    search: Object.assign(r(search), { visible: inside(search, card) }),
    tagAll: Object.assign(r(tagAll), { visible: inside(tagAll, card) }),
    newTag: Object.assign(r(newTag), { visible: inside(newTag, card), underTable: newTag.getBoundingClientRect().top >= tgrid.getBoundingClientRect().bottom - 0.5 }),
    tagRows: pillCells.length,
    tagRowHeights: pillCells.map((n) => Math.round(n.getBoundingClientRect().height)),
    tagRowsVisible: pillCells.filter((n) => inside(n, tgrid)).length,
    dots: dots.length, swatches: card.querySelectorAll("[role=radio]").length,
    sessionRows: nameCells.length,
    sessionRowsVisible: nameCells.filter((n) => inside(n, gridBox)).length,
    sessionRowHeights: nameCells.slice(0, 3).map((n) => Math.round(n.getBoundingClientRect().height)),
  };
});

// click the "pane filters" caption (folded opens the matrix, open folds it; the choice holds for the page) and
// return the caret it shows afterwards
const toggleFilters = (page: any) => page.evaluate(() => {
  const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
  const cap = () => Array.from(card.querySelectorAll("span")).find((n) => (n.textContent || "").startsWith("pane filters"))!;
  cap().click();
  return (cap().textContent || "").slice(-1);
});
// the open matrix: its chips, whether every chip lies inside the card's width, the number of chip lines
const matrix = (page: any) => page.evaluate(() => {
  const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
  const chips = Array.from(card.querySelectorAll("span")).filter((n) => (n.getAttribute("style") || "").startsWith("cursor:pointer;padding:1px 8px;border-radius:9px;"));
  const cb = card.getBoundingClientRect();
  const rows = new Set(chips.map((n) => Math.round(n.getBoundingClientRect().top)));
  return { chips: chips.length, withinWidth: chips.every((n) => { const b = n.getBoundingClientRect(); return b.left >= cb.left && b.right <= cb.right + 0.5; }), lines: rows.size };
});

// the working area on screen without scrolling the dialog: the card holds its content, the search box, "tag
// all" and [+ New tag] are inside it, and at least `sessions` session rows and `tagRows` tag rows show
function assertWorkingArea(m: any, label: string, want: { sessions: number; tagRows: number }) {
  assert.ok(m.card.scrollHeight <= m.card.clientHeight + 1, label + ": the card holds its content without scroll: " + m.card.scrollHeight + " vs " + m.card.clientHeight);
  assert.ok(m.search.visible, label + ": the search box is on screen (" + Math.round(m.search.top) + ".." + Math.round(m.search.bottom) + " in the card " + Math.round(m.card.top) + ".." + Math.round(m.card.bottom) + ")");
  assert.ok(m.tagAll.visible, label + ": tag all is on screen (" + Math.round(m.tagAll.top) + ".." + Math.round(m.tagAll.bottom) + ")");
  assert.ok(m.newTag.visible, label + ": New tag is on screen (" + Math.round(m.newTag.top) + ".." + Math.round(m.newTag.bottom) + ")");
  assert.ok(m.sessionRowsVisible >= want.sessions, label + ": at least " + want.sessions + " session rows show without scrolling the dialog: " + m.sessionRowsVisible + " (box " + Math.round(m.gridBox.height) + "px, rows " + m.sessionRowHeights.join("/") + "px)");
  assert.ok(m.tagRowsVisible >= want.tagRows, label + ": at least " + want.tagRows + " tag rows show before scrolling the table: " + m.tagRowsVisible + " (table " + Math.round(m.tgrid.height) + "px)");
}

// the tag table, re-found after a repaint (the build makes a new element)
const TGRID_PRE = "display:grid;grid-template-columns:max-content max-content max-content 1fr;";

for (const name of ["chromium", "firefox"]) {
  const launch = async (t: any) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser legs need it (CI installs no browsers)"); return null; }
    try { return await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return null; }
  };

  test(`in ${name}, the dialog across pages: 1300, 800 and 700px tall and a phone held sideways, folded and with the matrix open`, async (t) => {
    const browser = await launch(t);
    if (!browser) return;
    try {
      // 1600x1300, thirty tags: the page the user asked about
      {
        const { page, errors } = await mount(browser, { width: 1600, height: 1300, nTags: 30 });
        const m = await measure(page);
        assert.deepEqual(errors, [], "the view mounted and the dialog opened without a page error");
        assert.equal(m.viewport.h, 1300);
        // the tag rows: thirty, one line each
        assert.equal(m.tagRows, 30); assert.equal(m.dots, 30); assert.equal(m.swatches, 0, "no inline swatch");
        assert.ok(m.tagRowHeights.every((h: number) => h <= 32), "every tag row is one line (at most 32px): " + m.tagRowHeights.join(","));
        // the tag table scrolls within itself and stays within its viewport share
        assert.equal(m.tgrid.overflowY, "auto");
        assert.ok(m.tgrid.scrollHeight > m.tgrid.clientHeight + 100, "thirty rows overflow the capped table, which scrolls them: " + m.tgrid.scrollHeight + " in " + m.tgrid.clientHeight);
        // the cap bounds the content box; the 8px of vertical padding (room for the pills' rings inside the clip) sits outside it
        assert.ok(m.tgrid.height <= 0.30 * m.viewport.h + 8 + 1, "the table takes at most 30vh plus its 8px padding: " + m.tgrid.height + " vs " + (0.30 * m.viewport.h + 8));
        assert.ok(m.tagRowsVisible >= 8, "a useful number of tag rows shows before scrolling: " + m.tagRowsVisible);
        // the card never scrolls or clips as a whole: its content fits its box
        assert.ok(m.card.scrollHeight <= m.card.clientHeight + 1, "the card holds its content without scroll: " + m.card.scrollHeight + " vs " + m.card.clientHeight);
        assert.ok(m.card.scrollWidth <= m.card.clientWidth + 1, "…and nothing overflows it sideways: " + m.card.scrollWidth + " vs " + m.card.clientWidth);
        assert.ok(m.card.height <= 0.9 * m.viewport.h + 1, "the card keeps the 90vh ceiling: " + m.card.height);
        // the working area: search, tag all and at least eight session rows on screen without scrolling the dialog
        assert.ok(m.search.visible, "the search box is on screen: " + Math.round(m.search.top) + ".." + Math.round(m.search.bottom) + " in the card " + Math.round(m.card.top) + ".." + Math.round(m.card.bottom));
        assert.ok(m.tagAll.visible, "tag all is on screen: " + Math.round(m.tagAll.top) + ".." + Math.round(m.tagAll.bottom));
        assert.equal(m.sessionRows, 40);
        assert.ok(m.sessionRowsVisible >= 8, "at least eight session rows show without scrolling the dialog: " + m.sessionRowsVisible + " (box " + Math.round(m.gridBox.height) + "px, rows " + m.sessionRowHeights.join("/") + "px)");
        assert.ok(m.gridBox.bottom <= m.card.bottom + 0.5, "the sessions table ends inside the card; it scrolls the rest: " + m.gridBox.bottom + " vs " + m.card.bottom);
        // [+ New tag]: on screen, and under the table rather than its last row (thirty rows would scroll it under the fold)
        assert.ok(m.newTag.visible, "New tag is on screen: " + Math.round(m.newTag.top) + ".." + Math.round(m.newTag.bottom) + " in the card " + Math.round(m.card.top) + ".." + Math.round(m.card.bottom));
        assert.ok(m.newTag.underTable, "New tag sits under the table, not inside it: its top " + m.newTag.top + " vs the table's bottom " + m.tgrid.bottom);
        // the filter matrix open: five rows of thirty-two chips wrap inside the card's width, and the card still fits
        assert.equal(await toggleFilters(page), "▾");
        const opened = await matrix(page);
        assert.equal(opened.chips, 5 * 32, "All, no tags and thirty tags on each of five rows");
        assert.ok(opened.withinWidth, "every chip lies inside the card's width (the rows wrap)");
        assert.ok(opened.lines > 5, "thirty-two chips per row wrap onto more than one line at this width: " + opened.lines);
        const after = await measure(page);
        assert.ok(after.mbox, "the open matrix lives in a cell of its own");
        assert.ok(after.card.scrollHeight <= after.card.clientHeight + 1, "the card still holds its content without scroll with the matrix open: " + after.card.scrollHeight + " vs " + after.card.clientHeight);
        assert.ok(after.sessionRowsVisible >= 8, "the sessions keep at least eight rows on screen with the matrix open: " + after.sessionRowsVisible + " (box " + Math.round(after.gridBox.height) + "px, matrix " + Math.round(after.mbox.height) + "px)");
        assert.ok(after.newTag.visible, "New tag stays on screen with the matrix open");
        assert.equal(await toggleFilters(page), "▸");
        assert.equal((await measure(page)).mbox, null, "folded again: no matrix cell");
        assert.deepEqual(errors, []);
        await page.close();
      }
      // 1600x800, thirty tags: the sessions give way first, down to their floor of four rows; the matrix's cell scrolls
      {
        const { page, errors } = await mount(browser, { width: 1600, height: 800, nTags: 30 });
        const m = await measure(page);
        assert.deepEqual(errors, []);
        assert.equal(m.viewport.h, 800);
        assertWorkingArea(m, "800px folded, thirty tags", { sessions: 4, tagRows: 5 });
        assert.equal(await toggleFilters(page), "▾");
        const o = await measure(page);
        assertWorkingArea(o, "800px open, thirty tags", { sessions: 4, tagRows: 3 });
        assert.ok(o.mbox, "800px open: the matrix cell exists");
        assert.ok(o.mbox.scrollHeight > o.mbox.clientHeight + 20, "800px open: the matrix's cell scrolls within itself: " + o.mbox.scrollHeight + " in " + o.mbox.clientHeight);
        assert.equal(await toggleFilters(page), "▸");
        assert.deepEqual(errors, []);
        await page.close();
      }
      // 1600x800, ten tags: the user's own count; the table's cap held exactly the ten rows and hid [+ New tag] as its last row
      {
        const { page, errors } = await mount(browser, { width: 1600, height: 800, nTags: 10 });
        const m = await measure(page);
        assert.deepEqual(errors, []);
        assert.equal(m.tagRows, 10);
        assertWorkingArea(m, "800px folded, ten tags", { sessions: 4, tagRows: 5 });
        assert.ok(m.newTag.underTable, "800px, ten tags: New tag sits under the table: " + m.newTag.top + " vs " + m.tgrid.bottom);
        assert.deepEqual(errors, []);
        await page.close();
      }
      // 1600x700, thirty tags: the table and the open matrix give way down to their floors; nothing clips
      {
        const { page, errors } = await mount(browser, { width: 1600, height: 700, nTags: 30 });
        const m = await measure(page);
        assert.deepEqual(errors, []);
        assert.equal(m.viewport.h, 700);
        assertWorkingArea(m, "700px folded, thirty tags", { sessions: 4, tagRows: 3 });
        assert.equal(await toggleFilters(page), "▾");
        const o = await measure(page);
        assertWorkingArea(o, "700px open, thirty tags", { sessions: 4, tagRows: 3 });
        assert.ok(o.mbox, "700px open: the matrix cell exists");
        assert.equal(await toggleFilters(page), "▸");
        assert.deepEqual(errors, []);
        await page.close();
      }
      // 844x390, a phone held sideways: the floors outgrow the card, which scrolls as a whole instead of clipping
      {
        const { page, errors } = await mount(browser, { width: 844, height: 390, mobile: true, nTags: 30 });
        const m = await measure(page);
        assert.deepEqual(errors, []);
        assert.ok(m.card.scrollHeight > m.card.clientHeight + 20, "phone: the card scrolls as a whole: " + m.card.scrollHeight + " vs " + m.card.clientHeight + " (viewport " + m.viewport.w + "x" + m.viewport.h + ")");
        assert.ok(m.search.visible, "phone: the search box is inside the card's box: " + Math.round(m.search.top) + ".." + Math.round(m.search.bottom) + " in " + Math.round(m.card.top) + ".." + Math.round(m.card.bottom));
        assert.ok(m.tagAll.visible, "phone: tag all is inside the card's box: " + Math.round(m.tagAll.top) + ".." + Math.round(m.tagAll.bottom));
        assert.ok(m.newTag.visible, "phone: New tag is inside the card's box: " + Math.round(m.newTag.top) + ".." + Math.round(m.newTag.bottom));
        assert.ok(m.tagRowsVisible >= 2, "phone: the table keeps at least two rows: " + m.tagRowsVisible + " (table " + Math.round(m.tgrid.height) + "px)");
        const scrolled = await page.evaluate(() => {
          const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
          card.scrollTop = card.scrollHeight;
          const gridBox = (Array.from(card.querySelectorAll("*")) as HTMLElement[]).find((n) => n.getAttribute("style") === "flex:1 1000 auto;min-height:96px;overflow-y:auto;")!;
          return { scrollTop: card.scrollTop, cardBottom: card.getBoundingClientRect().bottom, sessionsBottom: gridBox.getBoundingClientRect().bottom, sessionsHeight: gridBox.getBoundingClientRect().height };
        });
        assert.ok(scrolled.scrollTop > 0, "phone: the card took the scroll: " + scrolled.scrollTop);
        assert.ok(scrolled.sessionsBottom <= scrolled.cardBottom + 0.5, "phone: scrolled to the end, the sessions box is reachable inside the card: " + scrolled.sessionsBottom + " vs " + scrolled.cardBottom + " (box " + Math.round(scrolled.sessionsHeight) + "px)");
        assert.deepEqual(errors, []);
        await page.close();
      }
    } finally { await browser.close(); }
  });

  test(`in ${name}, the colour popover and the tag table at 1300px: the ring inside the clip, keyboard open and Tab, scroll, resize, scroll memory, repaint`, async (t) => {
    const browser = await launch(t);
    if (!browser) return;
    try {
      const { page, errors } = await mount(browser, { width: 1600, height: 1300, nTags: 30 });
      // opened FOR a tag, its pill wears a ring 3px outside its box; the table's clip must spare it
      const ring = await page.evaluate((pre: string) => {
        const p = (window as any).panel;
        p._openViewsDialog("g1");
        const card = (p._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const all = Array.from(card.querySelectorAll("*")) as HTMLElement[];
        const tgrid = all.find((n) => (n.getAttribute("style") || "").startsWith(pre))!;
        const cell = all.find((n) => (n as any)._tname === "tag-01")!;
        const pill = cell.firstElementChild as HTMLElement;
        const b = pill.getBoundingClientRect(), tb = tgrid.getBoundingClientRect();
        const out = { ringed: (pill.getAttribute("style") || "").indexOf("outline:1px solid") >= 0, offset: getComputedStyle(pill).outlineOffset, left: b.left - tb.left, top: b.top - tb.top };
        p._openViewsDialog(null);
        return out;
      }, TGRID_PRE);
      assert.ok(ring.ringed, "the pill of the tag the dialog was opened for wears the ring");
      assert.equal(ring.offset, "2px");
      assert.ok(ring.left >= 3, "the ringed pill sits at least 3px inside the table's left edge, so the clip spares its ring: " + ring.left);
      assert.ok(ring.top >= 3, "…and at least 3px under the table's top edge: " + ring.top);
      assert.deepEqual(errors, [], "the dialog opened for g1 and reopened plain without a page error");
      // keyboard: Enter on the focused dot opens the popover on the current swatch, which wears the inner ring
      // AND the browser's focus ring; Tab closes it and puts focus back on the dot
      await page.evaluate(() => {
        const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        (card.querySelector("[data-tag-dot='g1']") as HTMLElement).focus();
      });
      await page.keyboard.press("Enter");
      await sleep(40);   // the popover focuses its current swatch a tick after opening
      const kb = await page.evaluate(() => {
        const p = (window as any).panel;
        const pop = p._tagColorPop as HTMLElement | null;
        if (!pop) return { open: false, swatches: 0, focused: false, boxShadow: "", outlineStyle: "", inlineOutline: "", othersPlain: false };
        const sws = Array.from(pop.querySelectorAll("[role=radio]")) as HTMLElement[];
        const cur = pop.querySelector("[aria-checked=true]") as HTMLElement;
        const cs = getComputedStyle(cur);
        return { open: true, swatches: sws.length, focused: document.activeElement === cur, boxShadow: cs.boxShadow, outlineStyle: cs.outlineStyle, inlineOutline: cur.style.outline,
          othersPlain: sws.filter((s) => s !== cur).every((s) => getComputedStyle(s).boxShadow === "none" && s.style.outline === "") };
      });
      assert.ok(kb.open, "Enter on the focused dot opens the popover");
      assert.equal(kb.swatches, 12);
      assert.ok(kb.focused, "the current swatch took focus");
      assert.notEqual(kb.boxShadow, "none", "the current swatch wears the inner ring (two inset shadows): " + kb.boxShadow);
      assert.equal(kb.inlineOutline, "", "…and no inline outline, which would replace the browser's focus ring");
      assert.notEqual(kb.outlineStyle, "none", "the keyboard-focused swatch shows the browser's focus ring: outline-style " + JSON.stringify(kb.outlineStyle));
      assert.ok(kb.othersPlain, "every other swatch: no box-shadow, no inline outline");
      await page.keyboard.press("Tab");
      const tabbed = await page.evaluate(() => {
        const p = (window as any).panel;
        const card = (p._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        return { open: p._tagColorPop !== null, onDot: document.activeElement === card.querySelector("[data-tag-dot='g1']") };
      });
      assert.equal(tabbed.open, false, "Tab closes the popover");
      assert.ok(tabbed.onDot, "…and puts focus back on the dot");
      // the last row's dot: the popover placed on screen, one layer above the backdrop, the current swatch focused
      const openOn = (key: string) => page.evaluate((k: string) => {
        const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const dot = card.querySelector("[data-tag-dot='" + k + "']") as HTMLElement;
        dot.scrollIntoView();
        dot.click();
      }, key);
      await openOn("g30");
      await sleep(30);
      const popm = await page.evaluate(() => {
        const p = (window as any).panel;
        const card = (p._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const dot = card.querySelector("[data-tag-dot='g30']") as HTMLElement;
        const pop = p._tagColorPop as HTMLElement | null;
        if (!pop) return { open: false, swatches: 0, onScreen: false, nearDot: false, z: "", focused: false };
        const b = pop.getBoundingClientRect();
        const d = dot.getBoundingClientRect();
        return { open: true, swatches: pop.querySelectorAll("[role=radio]").length, onScreen: b.top >= 0 && b.bottom <= window.innerHeight && b.left >= 0 && b.right <= window.innerWidth,
          nearDot: Math.abs(b.top - d.bottom) <= 6 || Math.abs(d.top - b.bottom) <= 6, z: getComputedStyle(pop).zIndex, focused: document.activeElement === pop.querySelector("[aria-checked=true]") };
      });
      assert.ok(popm.open, "a click on the g30 dot opens the popover"); assert.equal(popm.swatches, 12);
      assert.ok(popm.onScreen, "the popover is on screen");
      assert.ok(popm.nearDot, "…anchored to its dot (below it, or above when below cannot hold it)");
      assert.equal(popm.z, "1003");
      assert.ok(popm.focused, "the current swatch took focus");
      // a table scroll that moves the dot closes it (the table sits at its end after scrolling the last row into
      // view, so the scroll goes up)
      const scrolled = await page.evaluate((pre: string) => {
        const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const tgrid = (Array.from(card.querySelectorAll("*")) as HTMLElement[]).find((n) => (n.getAttribute("style") || "").startsWith(pre))!;
        const before = tgrid.scrollTop;
        tgrid.scrollTop = before - 120;
        return { before, after: tgrid.scrollTop };
      }, TGRID_PRE);
      await twoFrames(page);
      assert.notEqual(scrolled.after, scrolled.before, "the table scrolled: " + scrolled.before + " to " + scrolled.after);
      assert.equal(await page.evaluate(() => (window as any).panel._tagColorPop === null), true, "a table scroll that moved the dot closed the popover");
      // the host window's resize closes it
      await openOn("g30");
      await sleep(30);
      assert.equal(await page.evaluate(() => (window as any).panel._tagColorPop !== null), true, "reopened on g30");
      await page.setViewportSize({ width: 1500, height: 1300 });
      await sleep(60);
      assert.equal(await page.evaluate(() => (window as any).panel._tagColorPop === null), true, "the host window's resize closed the popover");
      await page.setViewportSize({ width: 1600, height: 1300 });
      // scroll memory: the table's scroll survives a repaint; a table that no longer scrolls clamps it to 0
      const mem = await page.evaluate(({ data, pre }: { data: any; pre: string }) => {
        const p = (window as any).panel;
        const card = () => (p._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const find = () => (Array.from(card().querySelectorAll("*")) as HTMLElement[]).find((n) => (n.getAttribute("style") || "").startsWith(pre))!;
        const rows = () => (Array.from(card().querySelectorAll("*")) as HTMLElement[]).filter((n) => (n as any)._tname).length;
        const t1 = find();
        t1.scrollTop = 200;
        const got = t1.scrollTop;
        p._viewsDialogBuild();
        const t2 = find();
        const kept = { newTable: t2 !== t1, got, after: t2.scrollTop };
        p.update(Object.assign({}, data, { views: Object.assign({}, data.views, { seq: 1001, tags: data.views.tags.slice(0, 3) }) }));
        p._viewsDialogBuild();
        const t3 = find();
        const three = { rows: rows(), scrollTop: t3.scrollTop, scrollHeight: t3.scrollHeight, clientHeight: t3.clientHeight };
        p.update(Object.assign({}, data, { views: Object.assign({}, data.views, { seq: 1002 }) }));
        p._viewsDialogBuild();
        return { kept, three, rows30: rows() };
      }, { data: DATA, pre: TGRID_PRE });
      assert.ok(mem.kept.newTable, "the repaint built a new table");
      assert.ok(mem.kept.got > 0, "the table took the scroll: " + mem.kept.got);
      assert.ok(Math.abs(mem.kept.after - mem.kept.got) <= 1, "the table's scroll survives a repaint: " + mem.kept.got + " before, " + mem.kept.after + " after");
      assert.equal(mem.three.rows, 3, "the three-tag frame was adopted");
      assert.equal(mem.three.scrollTop, 0, "a table that no longer scrolls clamps its remembered scroll to 0: " + mem.three.scrollTop);
      assert.ok(mem.three.scrollHeight <= mem.three.clientHeight + 1, "three rows do not scroll: " + mem.three.scrollHeight + " in " + mem.three.clientHeight);
      assert.equal(mem.rows30, 30, "the thirty-tag frame was restored");
      // a repaint that pushes the rows down (a notice above the table) re-places the popover on its rebuilt dot
      await page.evaluate((pre: string) => {
        const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const tgrid = (Array.from(card.querySelectorAll("*")) as HTMLElement[]).find((n) => (n.getAttribute("style") || "").startsWith(pre))!;
        tgrid.scrollTop = 0;
      }, TGRID_PRE);
      await twoFrames(page);
      await page.evaluate(() => {
        const card = ((window as any).panel._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        (card.querySelector("[data-tag-dot='g3']") as HTMLElement).click();
      });
      await sleep(40);
      const re = await page.evaluate(() => {
        const p = (window as any).panel;
        const pop = p._tagColorPop as HTMLElement | null;
        if (!pop) return { wasOpen: false, open: false, before: 0, after: 0, notice: false, gap: 0, sameNode: false };
        const before = pop.getBoundingClientRect().top;
        p._tagEditErr = { host: "", name: "", error: "synthetic refusal" };
        p._viewsDialogBuild();
        const card = (p._viewsDialog as HTMLElement).firstElementChild as HTMLElement;
        const notice = Array.from(card.querySelectorAll("span")).some((n) => (n.textContent || "").indexOf("synthetic refusal") >= 0);
        const pop2 = p._tagColorPop as HTMLElement | null;
        if (!pop2) return { wasOpen: true, open: false, before, after: 0, notice, gap: 0, sameNode: false };
        const dot = card.querySelector("[data-tag-dot='g3']") as HTMLElement;
        const b = pop2.getBoundingClientRect(), d = dot.getBoundingClientRect();
        return { wasOpen: true, open: true, before, after: b.top, notice, gap: Math.min(Math.abs(b.top - d.bottom), Math.abs(d.top - b.bottom)), sameNode: pop2 === pop };
      });
      assert.ok(re.wasOpen, "a click on the g3 dot opened the popover");
      assert.ok(re.notice, "the repaint drew the notice above the table");
      assert.ok(re.open, "the popover survives a repaint that rebuilt its row");
      assert.ok(re.sameNode, "…the same popover, re-placed");
      assert.notEqual(re.after, re.before, "…moved with its dot: top " + re.before + " before the notice, " + re.after + " after");
      assert.ok(re.gap <= 6, "…and hangs within 6px of the rebuilt dot: " + re.gap);
      await page.evaluate(() => { const p = (window as any).panel; p._tagEditErr = null; p._viewsDialogBuild(); });
      assert.deepEqual(errors, [], "no page error across the popover legs");
    } finally { await browser.close(); }
  });

  test(`in ${name}, framed shells: the dialog is adopted into the top document and the popover hangs on the dot's rect there`, async (t) => {
    const browser = await launch(t);
    if (!browser) return;
    try {
      const shells: Array<[string, string, string]> = [
        ["/shell-offset", SHELL_OFFSET, "the frame offset 300x400 into the page"],
        ["/shell-band", SHELL_BAND, "the frame a 200px band at the foot of a 1300px page"],
      ];
      for (const [shellPath, html, label] of shells) {
        const errors: string[] = [];
        const page = await browser.newPage({ viewport: { width: 1600, height: 1300 } });
        page.on("pageerror", (e: Error) => { errors.push(e.message); });
        await page.route("http://romp.test/**", (route: any) => {
          const url = String(route.request().url());
          const body = url.endsWith("/timeline") ? PAGE : url.endsWith(shellPath) ? html : null;
          if (body === null) return route.fulfill({ status: 404, contentType: "text/plain", body: "not here" });
          return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body });
        });
        await page.goto("http://romp.test" + shellPath);
        const frame = page.frame({ url: /\/timeline$/ });
        assert.ok(frame, label + ": the shell hosts the timeline frame");
        await frame.waitForFunction(() => !!(window as any).panel);
        const hosted = await frame.evaluate((data: any) => {
          const p = (window as any).panel;
          p.update(data);
          p.setCaps({ type: "caps", caps: ["tagEdit"], viewsSeq: 1000 });
          p._openViewsDialog(null);
          return { framed: window !== window.top, inTop: (p._viewsDialog as HTMLElement).ownerDocument === (window.top as Window).document, frameH: window.innerHeight, topH: (window.top as Window).innerHeight };
        }, DATA);
        assert.ok(hosted.framed, label + ": the view runs in a child frame");
        assert.ok(hosted.inTop, label + ": the dialog is adopted into the shell's document (frame " + hosted.frameH + "px tall in a " + hosted.topH + "px page)");
        await frame.evaluate(() => {
          const p = (window as any).panel;
          ((p._viewsDialog as HTMLElement).querySelector("[data-tag-dot='g1']") as HTMLElement).click();
        });
        await sleep(40);
        const fm = await frame.evaluate(() => {
          const p = (window as any).panel;
          const top = window.top as Window;
          const pop = p._tagColorPop as HTMLElement | null;
          const dot = (p._viewsDialog as HTMLElement).querySelector("[data-tag-dot='g1']") as HTMLElement;
          const d = dot.getBoundingClientRect();
          const rect = (b: DOMRect) => ({ top: b.top, bottom: b.bottom, left: b.left, right: b.right });
          if (!pop) return { open: false, swatches: 0, pop: rect(d), dot: rect(d), view: { w: top.innerWidth, h: top.innerHeight }, inTop: false, focused: false };
          return { open: true, swatches: pop.querySelectorAll("[role=radio]").length, pop: rect(pop.getBoundingClientRect()), dot: rect(d), view: { w: top.innerWidth, h: top.innerHeight },
            inTop: pop.ownerDocument === top.document, focused: top.document.activeElement === pop.querySelector("[aria-checked=true]") };
        });
        assert.ok(fm.open, label + ": a click on the g1 dot opens the popover");
        assert.equal(fm.swatches, 12);
        const gap = Math.min(Math.abs(fm.pop.top - fm.dot.bottom), Math.abs(fm.dot.top - fm.pop.bottom));
        assert.ok(gap <= 6, label + ": the popover hangs on the dot in the top document's coordinates: popover " + Math.round(fm.pop.top) + ".." + Math.round(fm.pop.bottom) + ", dot " + Math.round(fm.dot.top) + ".." + Math.round(fm.dot.bottom) + " (gap " + gap + ")");
        assert.ok(fm.pop.top >= 0 && fm.pop.left >= 0 && fm.pop.bottom <= fm.view.h && fm.pop.right <= fm.view.w,
          label + ": the popover is inside the top viewport " + fm.view.w + "x" + fm.view.h + ": " + Math.round(fm.pop.left) + "," + Math.round(fm.pop.top) + " to " + Math.round(fm.pop.right) + "," + Math.round(fm.pop.bottom));
        assert.ok(fm.inTop, label + ": the popover lives in the top document");
        assert.ok(fm.focused, label + ": the current swatch took focus in the top document");
        assert.deepEqual(errors, [], label + ": no page error");
        await page.close();
      }
    } finally { await browser.close(); }
  });
}
