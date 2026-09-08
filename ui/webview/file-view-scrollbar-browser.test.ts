// The pane-wide table's cap under a VISIBLE scrollbar, and the body's width where nothing scrolls (Slice 3 of
// plans/markdown-viewer.md, review rounds 1 and 2). The body is the scroller; the column is the root's own `100%` padding, which
// resolves against the body's content box AFTER an `overflow: auto` scrollbar takes its space. Round 1 read the cap as `100cqi`
// of the body, which resolves BEFORE the scrollbar, so on every note that scrolled the table was laid out `scrollbar` pixels
// wider than the body less 36, sat 18px from the left inset and 8px from the scrollbar (the pane's classic 10px one, styles.css
// `::-webkit-scrollbar`), and ran past the column's right edge wherever the column was at its 18px floor; round 1 reserved the
// gutter (`scrollbar-gutter: stable`) to make the two agree. Round 2 found that reservation a blank strip on every body that
// never scrolls: a three-paragraph note and a picture 5px off the card's centre (7.5 on the feed's 15px platform scrollbar), a
// PDF frame 10px short of the body's edge with the dark card showing in the strip, the editor the same beside its own scrollbar.
// The fix takes the reservation out and keys the cap on the body's content width as the viewer's ResizeObserver reports it,
// written on the body as `--fv-body-w` (file-view.ts; the observer's report is the layout's own event, one write per report,
// so a scrollbar appearing or leaving moves the cap in the same frame). The other legs never saw any of it: playwright launches
// headless Chromium with `--hide-scrollbars`, so this one launches WITHOUT that flag (`ignoreDefaultArgs`) and measures the real
// geometry, the scrollbar present. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { requireCjs, openViewer, openPanel, frames, REPORT, SID, LONG, type Mode } from "./real-viewer-leg";

const COLS = (n: number) => Array.from({ length: n }, (_, i) => "column_" + (i + 1) + "_header");
const table = (n: number, rows: number) => ["| " + COLS(n).join(" | ") + " |", "|" + COLS(n).map(() => "---").join("|") + "|",
  ...Array.from({ length: rows }, (_, r) => "| " + COLS(n).map((_, c) => "cell_r" + (r + 1) + "c" + (c + 1)).join(" | ") + " |")].join("\n");
const NOTE = ["# Heading one", "", "A paragraph. " + "The quick brown fox jumps over the lazy dog. ".repeat(6), "",
  table(3, 2), "", table(6, 3), "", table(14, 1), "",
  ...Array.from({ length: 40 }, (_, i) => "Paragraph " + (i + 1) + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + "."), ""].join("\n");
const SHORT = "# A short note\n\nFirst paragraph of a short note in a synthetic repo.\n\nSecond paragraph, still short.\n\nThird paragraph, and that is all.\n";
const IMG = "/repo/notes-api/docs/figure.png", PDF = "/repo/notes-api/docs/paper.pdf";

type Facts = Record<string, any>;
function measure(): Facts {
  const body = document.querySelector(".fileview-body") as HTMLElement, root = document.querySelector(".fileview-md") as HTMLElement;
  const p = root.querySelector("p") as HTMLElement; const tables = Array.from(root.querySelectorAll(":scope > table")) as HTMLElement[];
  const br = body.getBoundingClientRect(), pr = p.getBoundingClientRect(); const scrollbar = body.offsetWidth - body.clientWidth; const cs = getComputedStyle(root);
  const at = (t: HTMLElement) => { const r = t.getBoundingClientRect(); return { width: r.width, bodyL: r.left - br.left, bodyR: br.right - scrollbar - r.right, pastColR: r.right - pr.right, client: t.clientWidth, scroll: t.scrollWidth }; };
  return { bodyOffset: body.offsetWidth, bodyClient: body.clientWidth, scrollbar, scrolls: body.scrollHeight > body.clientHeight, sidewaysScroll: body.scrollWidth > body.clientWidth,
    bodyW: getComputedStyle(body).getPropertyValue("--fv-body-w").trim(), gutter: getComputedStyle(body).scrollbarGutter,
    padL: parseFloat(cs.paddingLeft), padR: parseFloat(cs.paddingRight), column: pr.width, colL: pr.left - br.left, colR: br.right - scrollbar - pr.right, narrow: at(tables[0]), mid: at(tables[1]), wide: at(tables[2]) };
}
/** The body against the card and the title bar: what is reserved beside a body that does not scroll, and where its content sits. */
function strips(): Facts {
  const body = document.querySelector(".fileview-body") as HTMLElement, card = document.querySelector(".fileview") as HTMLElement, bar = document.querySelector(".fileview-bar") as HTMLElement;
  const br = body.getBoundingClientRect(), cr = card.getBoundingClientRect(), tr = bar.getBoundingClientRect(); const mid = (r: DOMRect) => (r.left + r.right) / 2;
  const out: Facts = { reserved: body.offsetWidth - body.clientWidth, scrolls: body.scrollHeight > body.clientHeight, bodyClient: body.clientWidth, first: (body.firstElementChild as HTMLElement | null)?.className || null };
  const p = body.querySelector(".fileview-md > p") as HTMLElement | null; if (p) { const r = p.getBoundingClientRect(); out.colOffCard = mid(r) - mid(cr); out.colOffBar = mid(r) - mid(tr); }
  const img = body.querySelector("img.fileview-img") as HTMLElement | null; if (img) { const r = img.getBoundingClientRect(); out.imgOffCard = mid(r) - mid(cr); out.imgboxW = (body.querySelector(".fileview-imgbox") as HTMLElement).getBoundingClientRect().width; }
  const frame = body.querySelector("iframe.fileview-frame") as HTMLElement | null; if (frame) { const r = frame.getBoundingClientRect(); out.frameW = r.width; out.frameStrip = br.right - r.right; }
  const ed = body.querySelector(".fileview-editor, .fileview-cm") as HTMLElement | null; if (ed) { const r = ed.getBoundingClientRect(); out.editorW = r.width; out.editorStrip = br.right - r.right; out.editorScrolls = ed.scrollHeight > ed.clientHeight; }
  return out;
}
/** Open a binary file through the harness: its fetch answers the path with the blob (a PNG drawn on a canvas, or a one-page PDF). */
async function openMedia(page: any, path: string, kind: "png" | "pdf"): Promise<void> {
  await page.evaluate(async ([p, sid, kind]: [string, string, string]) => {
    const w = window as any; let blob: Blob;
    if (kind === "png") { const c = document.createElement("canvas"); c.width = 400; c.height = 200; const g = c.getContext("2d")!; g.fillStyle = "#3a7bd5"; g.fillRect(0, 0, 400, 200); blob = await new Promise<Blob>((r) => c.toBlob((b) => r(b!), "image/png")); }
    else blob = new Blob(["%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"], { type: "application/pdf" });
    const prev = w.fetch;
    w.fetch = async function (url: any) { const m = /[?&]path=([^&]*)/.exec(String(url)); if (m && decodeURIComponent(m[1]) === p) return new Response(blob, { status: 200, headers: { "Content-Type": kind === "png" ? "image/png" : "application/pdf", "X-Romp-Mtime-Ns": w.__mtime } }); return prev(url); };
    w.FV.openFileView(p, sid, null);
  }, [path, SID, kind]);
  if (kind === "png") await page.waitForFunction(() => { const i = document.querySelector("img.fileview-img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
  else await page.waitForFunction(() => !!document.querySelector("iframe.fileview-frame"), null, { timeout: 10000 });
  await frames(page, 3);
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
async function withScrollbars(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch({ ignoreDefaultArgs: ["--hide-scrollbars"] }); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

test("with the scrollbar visible, a table wider than the pane sits 18px inside the body on BOTH sides and never past the column's edge at its floor: the cap reads the body's content width (pane 380, pane 900 with the aside, chat 900, feed 380, pane 1400)", { timeout: 180000 }, async (t) => {
  await withScrollbars(t, async (browser) => {
    for (const [mode, width, aside] of [["pane", 380, false], ["pane", 900, true], ["chat", 900, false], ["feed", 380, false], ["pane", 1400, false]] as [Mode, number, boolean][]) {
      const cell = `${mode} ${width}px${aside ? " with the aside" : ""}`;
      const { page, errors } = await openViewer(browser, mode, width, 600, { docs: { [REPORT]: NOTE } });
      if (aside) await openPanel(page);
      const m = await page.evaluate(measure);
      assert.ok(m.scrolls, cell + ": the note scrolls (the premise: an auto scrollbar is up)");
      // the pane and the chat style their scrollbar (styles.css ::-webkit-scrollbar, a classic 10px one on every platform); the feed
      // takes the platform's, which may be an overlay of no width: then the cell measures the same geometry with nothing taken
      if (mode !== "feed") assert.equal(m.scrollbar, 10, cell + ": the classic 10px scrollbar is present (this leg launches without --hide-scrollbars)");
      assert.equal(m.gutter, "auto", cell + ": the body reserves no gutter (round 1's `scrollbar-gutter: stable` is gone)");
      assert.equal(m.bodyW, m.bodyClient + "px", cell + ": --fv-body-w on the body is its content box, the scrollbar's " + m.scrollbar + "px taken (the ResizeObserver's report; the box before the scrollbar is " + m.bodyOffset + ")");
      assert.equal(m.padL, m.padR, cell + ": the column's two gaps are equal"); assert.ok(m.padL >= 18, cell + ": at least the 18px inset");
      assert.ok(Math.abs(m.colL - m.colR) <= 1, cell + ": the column is centred in the content box (" + m.colL + " / " + m.colR + ")");
      // the wide table: from inset to inset, both 18, and never past the column's edge where the column is at its floor
      assert.ok(Math.abs(m.wide.bodyL - 18) <= 0.5, cell + ": the wide table starts at the body's 18px inset (" + m.wide.bodyL + ")");
      assert.ok(Math.abs(m.wide.bodyR - 18) <= 0.5, cell + ": ...and ends 18px before the scrollbar (" + m.wide.bodyR + "; round 1's cqi cap put it at 18 - " + m.scrollbar + ")");
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
  });
});

test("with the scrollbar visible, a body that does not scroll reserves nothing: a short note and a picture centred on the card, a PDF frame and the editor the body's full width (pane 900, chat 900, feed 900, pane 380)", { timeout: 180000 }, async (t) => {
  await withScrollbars(t, async (browser) => {
    for (const [mode, width] of [["pane", 900], ["chat", 900], ["feed", 900], ["pane", 380]] as [Mode, number][]) {
      const cell = `${mode} ${width}px`;
      const { page, errors } = await openViewer(browser, mode, width, 600, { docs: { [REPORT]: SHORT } });
      const note = await page.evaluate(strips);
      assert.equal(note.scrolls, false, cell + ": the short note does not scroll (the premise)"); assert.equal(note.first, "fileview-md");
      assert.equal(note.reserved, 0, cell + ": nothing is reserved beside a note that does not scroll (round 1 reserved " + (mode === "feed" ? 15 : 10) + "px)");
      assert.ok(Math.abs(note.colOffCard) <= 0.5, cell + ": the column's centre is the card's (" + note.colOffCard.toFixed(2) + "px off; before: 5, feed 7.5)");
      assert.ok(Math.abs(note.colOffBar) <= 0.5, cell + ": ...and the title bar's (" + note.colOffBar.toFixed(2) + ")");
      await openMedia(page, IMG, "png"); const image = await page.evaluate(strips);
      assert.equal(image.first, "fileview-imgbox"); assert.equal(image.reserved, 0, cell + ": nothing reserved beside a picture");
      assert.equal(image.imgboxW, image.bodyClient, cell + ": the picture's box is the body's width");
      assert.ok(Math.abs(image.imgOffCard) <= 0.5, cell + ": the picture is centred on the card (" + image.imgOffCard.toFixed(2) + "px off; before: 5, feed 7.5)");
      await openMedia(page, PDF, "pdf"); const pdf = await page.evaluate(strips);
      assert.equal(pdf.reserved, 0, cell + ": nothing reserved beside the PDF frame");
      assert.equal(pdf.frameW, pdf.bodyClient, cell + ": the frame is the body's width (" + pdf.frameW + " in " + pdf.bodyClient + ")");
      assert.equal(pdf.frameStrip, 0, cell + ": no strip of the card between the frame and the body's edge (before: 10px, feed 15)");
      await page.close();
      // Edit mode on a long note: the editor (the fallback textarea here: no CodeMirror chunk is served) takes the body's width,
      // its own scrollbar inside it, and no dead strip beyond
      const o2 = await openViewer(browser, mode, width, 600, { docs: { [REPORT]: LONG } });
      await o2.page.locator("#romp-fileview .fileview-btn", { hasText: /^Edit$/ }).click();
      await o2.page.waitForFunction(() => !!document.querySelector(".fileview-editor, .fileview-cm"), null, { timeout: 10000 }); await frames(o2.page, 3);
      const edit = await o2.page.evaluate(strips);
      assert.equal(edit.scrolls, false, cell + ": the body does not scroll in Edit (the editor does)"); assert.ok(edit.editorScrolls, cell + ": the editor scrolls inside itself");
      assert.equal(edit.reserved, 0, cell + ": nothing reserved beside the editor"); assert.equal(edit.editorStrip, 0, cell + ": the editor reaches the body's edge (before: a " + (mode === "feed" ? 15 : 10) + "px strip beyond its own scrollbar)");
      assert.equal(edit.editorW, edit.bodyClient, cell + ": ...at the body's full width");
      assert.deepEqual(errors.concat(o2.errors), [], cell + ": no script error");
      await o2.page.close();
    }
  });
});
