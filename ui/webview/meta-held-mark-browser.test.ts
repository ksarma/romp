// The held mark as it RENDERS (review round 3, 2026-09-09): syncMetaControls draws a small accent glyph beside a
// badge's label while that kind's pick is held for the session's live work (effort-switch-pending.test.ts pins the
// source). Its dress had two defects only a browser shows: `vertical-align: super` is dead on a flex item (.meta-btn is
// inline-flex, so the mark is blockified and the dot drew on the label's centre line, reading as punctuation), and its
// own 0.66em compounded under .spinner-meta's 0.92em to 7.9px, below the caret. This leg lays the real badge DOM out
// under the whole of styles.css in headless Chromium, runs the mark-creation statements lifted from render.ts itself
// (so the aria-hidden claim is measured on the production lines), and measures: the mark's font size equals the
// badge's (.spinner-meta's, the label's), its box sits above the label's centre line yet within the badge, the badge's
// height is unchanged by the mark (the raise is a transform, not layout), and the badge's accessible text carries no
// bullet. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic
// values only: an invented label.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, UI } from "./real-viewer-leg";

const CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace(/^@import [^\n]*\n/m, "");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
// the statements syncMetaControls runs to draw the mark, as written in render.ts (plain statements: `el` and the
// badge `b` are their only free names)
const SLICE = (RENDER.match(/if \(held && !mark\) \{\n([\s\S]*?)\n\s*\} else if \(!held && mark\) \{/) || [])[1] || "";

type Measured = {
  fsMeta: string; fsLabel: string; fsMark: string; fsCaret: string; display: string;
  btnBefore: number; btnAfter: number;
  labelTop: number; labelCy: number; markTop: number; markCy: number; markBottom: number; btnTop: number; btnBottom: number;
  glyphLabelCy: number; glyphMarkCy: number; ariaHidden: string | null; markCount: number;
};

test("in a browser, the held mark wears the badge's size, sits raised above the label's centre inside the badge, adds no height, and is not read aloud", { timeout: 120000 }, async (t) => {
  assert.ok(SLICE.includes('el("span", "meta-held-mark")'), "the mark-creation slice was lifted from render.ts: " + JSON.stringify(SLICE));
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 300 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    // the statusline's badge cluster as updateStatusline mounts it: .statusline > .sl-right > #spinner-meta > .meta-btn,
    // the badge holding its label and caret (metaButton); the mark is drawn by the lifted slice below
    await page.setContent(`<!doctype html><html><head><style>${CSS}</style></head><body>
      <div class="statusline"><span class="sl-right"><span class="spinner-meta" id="spinner-meta">
        <span class="meta-btn" data-kind="effort"><span class="meta-label">high</span><span class="meta-caret">▾</span></span>
      </span></span></div></body></html>`);
    const m: Measured = await page.evaluate((slice: string) => {
      const btn = document.querySelector(".meta-btn") as HTMLElement;
      const label = document.querySelector(".meta-label") as HTMLElement;
      const caret = document.querySelector(".meta-caret") as HTMLElement;
      const meta = document.querySelector(".spinner-meta") as HTMLElement;
      const btnBefore = btn.getBoundingClientRect().height;
      const el = (tag: string, cls: string) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };
      new Function("el", "b", slice)(el, btn);   // render.ts's own statements draw the mark
      const mark = document.querySelector(".meta-held-mark") as HTMLElement;
      const glyph = (n: Element) => { const r = document.createRange(); r.selectNodeContents(n); return r.getBoundingClientRect(); };
      const cy = (r: DOMRect) => r.top + r.height / 2;
      const lb = label.getBoundingClientRect(), mb = mark.getBoundingClientRect(), bb = btn.getBoundingClientRect();
      return {
        fsMeta: getComputedStyle(meta).fontSize, fsLabel: getComputedStyle(label).fontSize, fsMark: getComputedStyle(mark).fontSize,
        fsCaret: getComputedStyle(caret).fontSize, display: getComputedStyle(mark).display,
        btnBefore, btnAfter: bb.height,
        labelTop: lb.top, labelCy: cy(lb), markTop: mb.top, markCy: cy(mb), markBottom: mb.bottom, btnTop: bb.top, btnBottom: bb.bottom,
        glyphLabelCy: cy(glyph(label)), glyphMarkCy: cy(glyph(mark)),
        ariaHidden: mark.getAttribute("aria-hidden"), markCount: document.querySelectorAll(".meta-held-mark").length,
      };
    }, SLICE);
    assert.deepEqual(errors, [], "no script error");
    assert.equal(m.markCount, 1, "the slice drew one mark");
    const px = parseFloat(m.fsMeta);
    assert.ok(px > 10 && px < 13, "the badge cluster's size at the 13px base is .spinner-meta's 0.92em: " + m.fsMeta);
    assert.equal(m.fsMark, m.fsMeta, "the mark inherits .spinner-meta's size (before: 0.66em compounded to 7.9px)");
    assert.equal(m.fsMark, m.fsLabel, "so it equals the label's");
    assert.ok(parseFloat(m.fsMark) > parseFloat(m.fsCaret), "and is not smaller than the caret");
    assert.equal(m.display, "block", "a flex item is blockified, which is why vertical-align could never raise it");
    const raise = m.labelCy - m.markCy;
    assert.ok(raise >= 0.25 * px, `the mark's box sits above the label's centre line: raised ${raise.toFixed(2)}px of ${px}px (before: 0)`);
    assert.ok(m.glyphLabelCy - m.glyphMarkCy >= 0.25 * px, "the glyph too, not only its box");
    assert.ok(m.markTop >= m.btnTop - 1 && m.markBottom <= m.btnBottom, `and within the badge (mark ${m.markTop}..${m.markBottom}, badge ${m.btnTop}..${m.btnBottom})`);
    assert.ok(Math.abs(m.btnAfter - m.btnBefore) < 0.01, `the badge's height is unchanged by the mark (${m.btnBefore} -> ${m.btnAfter}): the raise is a transform`);
    assert.equal(m.ariaHidden, "true", "the glyph is decoration to assistive tech");
    // the badge's accessible text: the label and the caret, no bullet (Chromium's accessibility tree, as
    // Playwright reads it)
    const aria: string = await page.locator(".meta-btn").ariaSnapshot();
    assert.ok(aria.includes("high"), "the label is read: " + aria);
    assert.ok(!aria.includes("•"), "the bullet is not: " + aria);
    await page.close();
  });
});
