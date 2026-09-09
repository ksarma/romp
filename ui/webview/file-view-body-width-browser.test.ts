// Where the body's width lives for the pane-wide table's cap (M4 of the 2026-09-09 viewer-resize measurements). The cap
// (`.fileview-md > table`, styles.css and feed.css) reads --fv-body-w, the body's content width as the viewer's ResizeObserver
// reports it. Until 2026-09-09 the viewer wrote it on the BODY as an ordinary custom property: inherited, so it reached every
// node under the body, and on every width change Chromium recomputed every node's style (27 ms a step at 24k nodes, 138 at 79k,
// 259 at 134k, measured with CDP Performance.getMetrics on the real viewer), the largest per-step term left once the panel's
// paint pass had stopped running on a reflow. Now the property is registered non-inherited (`@property --fv-body-w { syntax: "*";
// inherits: false }`) and written on each top-level table (file-view.ts stampBodyWidth): the tables read it, nothing inherits
// it, and a write restyles the tables alone. This leg holds the shape in the real viewer on both sheets: the body and the
// prose carry no --fv-body-w, every top-level table carries the body's content width, a nested table none; the tables follow
// a width change (the pane narrower, the aside open), a re-render (Raw and back: mdBlock rebuilds the root, no report follows,
// renderBody stamps), and the URL viewer, which has no width observer, leaves the property unset so the sheet's fallback holds
// (the cap is the column). The first leg is the regression guard: at the commit before the change the body carried the
// property and it fails there. The URL-viewer leg pins the fallback that already held before the change (that viewer never
// had a width observer), so it passes on both sides and guards the invariant, not the change. The geometry itself (18px
// insets, the cap under a visible scrollbar) is file-view-scrollbar-browser.test.ts's and
// file-view-typescale-browser.test.ts's. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, paintsReach, REPORT, ORIGIN, type Mode } from "./real-viewer-leg";

const COLS = (n: number, tag: string) => Array.from({ length: n }, (_, i) => tag + "_column_" + (i + 1) + "_header");
const table = (n: number, rows: number, tag: string) => ["| " + COLS(n, tag).join(" | ") + " |", "|" + COLS(n, tag).map(() => "---").join("|") + "|",
  ...Array.from({ length: rows }, (_, r) => "| " + COLS(n, tag).map((_, c) => tag + "_r" + (r + 1) + "c" + (c + 1)).join(" | ") + " |")].join("\n");
const PARA = (i: number) => "Paragraph " + i + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + ".";
/** Three top-level tables (narrow, six columns, fourteen), a table nested in a quote, and prose enough to scroll. */
const NOTE = ["# Heading one", "", PARA(0), "", table(3, 2, "narrow"), "", table(6, 3, "mid"), "", table(14, 1, "wide"), "",
  "> a quoted table:", ">", ...table(4, 2, "nested").split("\n").map((l) => "> " + l), "",
  ...Array.from({ length: 40 }, (_, i) => PARA(i + 1)), ""].join("\n");

type Facts = Record<string, any>;
function measure(): Facts {
  const body = document.querySelector(".fileview-body") as HTMLElement, root = document.querySelector(".fileview-md") as HTMLElement;
  const p = root.querySelector("p") as HTMLElement, tables = Array.from(root.querySelectorAll(":scope > table")) as HTMLElement[];
  const nested = root.querySelector("blockquote table") as HTMLElement | null;
  const bw = (el: Element) => getComputedStyle(el).getPropertyValue("--fv-body-w").trim();
  const br = body.getBoundingClientRect(), pr = p.getBoundingClientRect(); const scrollbar = body.offsetWidth - body.clientWidth;
  return { bodyClient: body.clientWidth, body: bw(body), root: bw(root), prose: bw(p), tables: tables.map(bw), nested: nested ? bw(nested) : null, nTables: tables.length,
    column: pr.width, wide: tables.length ? tables[tables.length - 1].getBoundingClientRect().width : null,
    wideR: tables.length ? br.right - scrollbar - tables[tables.length - 1].getBoundingClientRect().right : null };
}
/** The body, the root and the prose carry nothing; every top-level table carries the body's content width; the nested table none. */
function holds(m: Facts, at: string): void {
  assert.equal(m.nTables, 3, at + ": the three top-level tables are there");
  assert.equal(m.body, "", at + ": the body carries no --fv-body-w (written there until 2026-09-09, every node under it restyled per write)");
  assert.equal(m.root, "", at + ": the root inherits none"); assert.equal(m.prose, "", at + ": the prose inherits none (the property is registered non-inherited)");
  assert.deepEqual(m.tables, [m.bodyClient + "px", m.bodyClient + "px", m.bodyClient + "px"], at + ": each top-level table carries the body's content width");
  assert.equal(m.nested, "", at + ": a nested table carries none (only a table of the page's own reads the cap)");
  assert.ok(Math.abs(m.wide - (m.bodyClient - 36)) <= 0.5, at + ": the wide table is the body less 36px (" + m.wide + " in " + m.bodyClient + ")");
  assert.ok(Math.abs(m.wideR - 18) <= 0.5, at + ": ...ending 18px before the body's edge (" + m.wideR + ")");
}
const paints = (page: any): Promise<number> => page.evaluate(() => (window as any).__paints as number);

test("--fv-body-w sits on each top-level table and nowhere else, and follows a width change, the aside and a re-render (pane and feed)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "feed"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 1400, 700, { docs: { [REPORT]: NOTE } });
      let m = await page.evaluate(measure);
      holds(m, mode + " 1400");
      const w0 = m.bodyClient;
      // the pane narrower: the observer's report, the reflow's frame, the tables' value moves with the body
      let n = await paints(page);
      await page.setViewportSize({ width: 1000, height: 700 }); await paintsReach(page, n + 1); await frames(page, 2);
      m = await page.evaluate(measure);
      assert.ok(m.bodyClient < w0, mode + " 1000: the body narrowed (" + w0 + " to " + m.bodyClient + ")");
      holds(m, mode + " 1000");
      // the aside open: the body loses 340px, the tables follow
      n = await paints(page);
      await openPanel(page); await frames(page, 2);
      const open = await page.evaluate(measure);
      assert.ok(open.bodyClient < m.bodyClient, mode + " aside: the body narrowed again (" + m.bodyClient + " to " + open.bodyClient + ")");
      holds(open, mode + " 1000 aside open");
      // a re-render: Raw, then Rendered again; mdBlock builds a fresh root and no report follows, so renderBody stamps the tables
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Raw$/ }).click();
      await page.waitForFunction(() => !document.querySelector(".fileview-md"), null, { timeout: 10000 });
      await page.locator("#romp-fileview .fileview-btn", { hasText: /^Rendered$/ }).click();
      await page.waitForFunction(() => !!document.querySelector(".fileview-md > table"), null, { timeout: 10000 }); await frames(page, 2);
      const again = await page.evaluate(measure);
      assert.equal(again.bodyClient, open.bodyClient, mode + " re-render: the body did not move (no report, so the stamp is renderBody's own)");
      holds(again, mode + " 1000 aside open, rendered again");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("the URL viewer has no width observer: the property stays unset and the sheet's fallback caps a table at the column", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 1400, 700, { url: "/notes/report.md", urls: { [ORIGIN + "/notes/report.md"]: NOTE } });
    const m = await page.evaluate(measure);
    assert.equal(m.nTables, 3); assert.equal(m.body, ""); assert.equal(m.prose, "");
    assert.deepEqual(m.tables, ["", "", ""], "no observer, no write: every table's --fv-body-w is unset");
    assert.ok(Math.abs(m.wide - m.column) <= 0.5, "the fallback (the column) caps the wide table (" + m.wide + " in a " + m.column + " column)");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
