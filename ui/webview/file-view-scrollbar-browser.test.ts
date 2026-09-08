// The pane-wide table's cap under a VISIBLE scrollbar (Slice 3 of plans/markdown-viewer.md, review round 1). The body is
// the scroller AND the size container the table's `100cqi` reads; the column is the root's own `100%` padding. A container
// query unit resolves against the container's box BEFORE an `overflow: auto` scrollbar takes its space, while a child's
// percentage resolves against the content box after it, so on every note that scrolls the two disagreed by the scrollbar's
// width: the table was laid out `scrollbar` pixels wider than the body less 36, sat 18px from the left inset and 8px from
// the scrollbar (the pane's classic 10px one, styles.css `::-webkit-scrollbar`), and ran 10px past the column's right edge
// wherever the column was at its 18px floor. `scrollbar-gutter: stable` on the body reserves the scrollbar's space before
// layout, so the container's inline size is the content box and the cap agrees with the column to the pixel. The other legs
// never saw it: playwright launches headless Chromium with `--hide-scrollbars`, so this one launches WITHOUT that flag
// (`ignoreDefaultArgs`) and measures the real geometry, the scrollbar present. Skips loudly without a browser. Synthetic values.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { requireCjs, openViewer, openPanel, frames, REPORT, type Mode } from "./real-viewer-leg";

const COLS = (n: number) => Array.from({ length: n }, (_, i) => "column_" + (i + 1) + "_header");
const table = (n: number, rows: number) => ["| " + COLS(n).join(" | ") + " |", "|" + COLS(n).map(() => "---").join("|") + "|",
  ...Array.from({ length: rows }, (_, r) => "| " + COLS(n).map((_, c) => "cell_r" + (r + 1) + "c" + (c + 1)).join(" | ") + " |")].join("\n");
const NOTE = ["# Heading one", "", "A paragraph. " + "The quick brown fox jumps over the lazy dog. ".repeat(6), "",
  table(3, 2), "", table(6, 3), "", table(14, 1), "",
  ...Array.from({ length: 40 }, (_, i) => "Paragraph " + (i + 1) + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + "."), ""].join("\n");

type Facts = Record<string, any>;
function measure(): Facts {
  const body = document.querySelector(".fileview-body") as HTMLElement, root = document.querySelector(".fileview-md") as HTMLElement;
  const p = root.querySelector("p") as HTMLElement; const tables = Array.from(root.querySelectorAll(":scope > table")) as HTMLElement[];
  // 100cqi as the browser resolves it inside the root: a probe box one container-inline-unit wide
  const cq = document.createElement("div"); cq.style.cssText = "width: 100cqi; height: 1px; padding: 0; margin: 0; border: 0; translate: none"; root.appendChild(cq);
  const cqi = cq.getBoundingClientRect().width; cq.remove();
  const br = body.getBoundingClientRect(), pr = p.getBoundingClientRect(); const scrollbar = body.offsetWidth - body.clientWidth; const cs = getComputedStyle(root);
  const at = (t: HTMLElement) => { const r = t.getBoundingClientRect(); return { width: r.width, bodyL: r.left - br.left, bodyR: br.right - scrollbar - r.right, pastColR: r.right - pr.right, client: t.clientWidth, scroll: t.scrollWidth }; };
  return { bodyOffset: body.offsetWidth, bodyClient: body.clientWidth, scrollbar, scrolls: body.scrollHeight > body.clientHeight, sidewaysScroll: body.scrollWidth > body.clientWidth, cqi, gutter: getComputedStyle(body).scrollbarGutter,
    padL: parseFloat(cs.paddingLeft), padR: parseFloat(cs.paddingRight), column: pr.width, colL: pr.left - br.left, colR: br.right - scrollbar - pr.right, narrow: at(tables[0]), mid: at(tables[1]), wide: at(tables[2]) };
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("with the scrollbar visible, a table wider than the pane sits 18px inside the body on BOTH sides and never past the column's edge at its floor: the cap's 100cqi is the body's content box (pane 380, pane 900 with the aside, chat 900, feed 380, pane 1400)", { timeout: 180000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch({ ignoreDefaultArgs: ["--hide-scrollbars"] }); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    for (const [mode, width, aside] of [["pane", 380, false], ["pane", 900, true], ["chat", 900, false], ["feed", 380, false], ["pane", 1400, false]] as [Mode, number, boolean][]) {
      const cell = `${mode} ${width}px${aside ? " with the aside" : ""}`;
      const { page, errors } = await openViewer(browser, mode, width, 600, { docs: { [REPORT]: NOTE } });
      if (aside) await openPanel(page);
      const m = await page.evaluate(measure);
      assert.ok(m.scrolls, cell + ": the note scrolls (the premise: an auto scrollbar is up)");
      // the pane and the chat style their scrollbar (styles.css ::-webkit-scrollbar, a classic 10px one on every platform); the feed
      // takes the platform's, which may be an overlay of no width: then the cell measures the same geometry with nothing to reserve
      if (mode !== "feed") assert.equal(m.scrollbar, 10, cell + ": the classic 10px scrollbar is present (this leg launches without --hide-scrollbars)");
      assert.equal(m.cqi, m.bodyClient, cell + ": 100cqi is the body's content box, the scrollbar's " + m.scrollbar + "px taken (before the gutter: the box before the scrollbar, " + m.bodyOffset + ")");
      assert.equal(m.gutter, "stable", cell + ": ...because the body reserves the scrollbar's gutter before layout");
      assert.equal(m.padL, m.padR, cell + ": the column's two gaps are equal"); assert.ok(m.padL >= 18, cell + ": at least the 18px inset");
      assert.ok(Math.abs(m.colL - m.colR) <= 1, cell + ": the column is centred in the content box (" + m.colL + " / " + m.colR + ")");
      // the wide table: from inset to inset, both 18, and never past the column's edge where the column is at its floor
      assert.ok(Math.abs(m.wide.bodyL - 18) <= 0.5, cell + ": the wide table starts at the body's 18px inset (" + m.wide.bodyL + ")");
      assert.ok(Math.abs(m.wide.bodyR - 18) <= 0.5, cell + ": ...and ends 18px before the scrollbar (" + m.wide.bodyR + "; before the gutter it was 18 - " + m.scrollbar + ")");
      assert.ok(m.wide.width <= m.bodyClient - 36 + 0.5, cell + ": ...no wider than the content box less 36 (" + m.wide.width + " in " + m.bodyClient + ")");
      if (m.padL <= 18.5) assert.ok(m.wide.pastColR <= 0.5, cell + ": at the column's floor the table's right edge is the column's (" + m.wide.pastColR + " past it)");
      assert.ok(m.wide.scroll > m.wide.client, cell + ": the 14 columns scroll inside the table");
      // the six-column table: centred in the content box when it leaves the column, else the column's
      if (m.mid.width > m.column + 1) assert.ok(Math.abs(m.mid.bodyL - m.mid.bodyR) <= 1, cell + ": the six-column table is centred between the inset and the scrollbar (" + m.mid.bodyL.toFixed(1) + " / " + m.mid.bodyR.toFixed(1) + ")");
      else assert.ok(Math.abs(m.mid.bodyL - m.colL) <= 0.5, cell + ": the six-column table sits at the column's left edge");
      assert.ok(Math.abs(m.narrow.bodyL - m.colL) <= 0.5, cell + ": the narrow table sits at the column's left edge with the prose");
      assert.equal(m.sidewaysScroll, false, cell + ": the body never scrolls sideways");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
  } finally { await browser.close(); }
});
