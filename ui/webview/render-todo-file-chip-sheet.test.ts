// The chat's todo card wears the file chip as a pill (the review of the todo-file follow-on, 2026-09-07). render.ts's
// todoFileChip builds the chip — openPathLink's span with the class `ut-file` — inside the row's text span and after the
// Reply modal's quoted line (render-todo-file-chip.test.ts runs that), and the Waiting-on-you pane gives its own chip
// the `.wt-file` pill in waiting-pane.css. The chat page loads styles.css alone, and styles.css had no `.ut-file` rule,
// so on the card the same record rendered as a plain dotted path link: the class named a rule that did not exist.
//
// The rule is not .wt-file's copied over. That chip is a flex item of the row (display:block, its parent places it);
// this one sits INSIDE the text span, inline, so that it wraps as a word of the line does and a click on it reaches
// its own data-act before the span's uttoggle. Measured in Chromium against the row as render.ts builds it: a block
// put the chip on its own line with the "details" hint under it (a 42px row became 79px); an inline-block on the
// baseline sat ~5px under the text's centre and grew the row to 47px, because overflow:hidden moves an inline-block's
// baseline to its bottom edge — vertical-align: middle is load-bearing; and a flex container between the property and
// the text defeats text-overflow (waiting-pane-chip-ellipsis-browser.test.ts, the same review). In the Reply modal the
// chip trails the quoted line, whose width is the box's, so the row's 32% share is lifted there as the pane lifts it.
//
// The source leg runs everywhere and pins the rule. The browser legs (Chromium, and Firefox when the box has it; CI
// installs none, so they skip LOUDLY) load styles.css as the chat page does over the row and the modal built as
// render.ts builds them, and measure: a row with the chip is as tall as one without, the chip sits on the text's line,
// a long basename ends in an ellipsis that reaches the text, and the modal's chip fits its line whole. Synthetic
// fixtures only: the notes-api world, a placeholder sid, TESTHOST.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES_CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");

const rule = (sel: string): string => {
  const at = STYLES_CSS.indexOf(sel);
  assert.ok(at >= 0, sel + " is in the chat's sheet");
  return STYLES_CSS.slice(at, STYLES_CSS.indexOf("}", at));
};

// ── the source leg ────────────────────────────────────────────────────────────────────────────────
test("source: styles.css gives .ut-file the pill — an inline-block on the text's line, the accent, the ellipsis triple, no underline", () => {
  assert.match(RENDER, /chip\.classList\.add\("ut-file"\)/, "render.ts names the chip for this rule");
  const r = rule(".ut-file {");
  assert.match(r, /display: inline-block;/, "inline: a word of the line (a block puts the chip on its own line and the hint under it)");
  assert.doesNotMatch(r, /display: block/);
  assert.match(r, /vertical-align: middle;/, "load-bearing: overflow:hidden moves an inline-block's baseline to its bottom edge");
  assert.match(r, /overflow: hidden; white-space: nowrap; text-overflow: ellipsis;/, "the ellipsis triple");
  assert.doesNotMatch(r, /inline-flex|align-items/, "no flex container between the property and the text");
  assert.match(r, /border-radius: var\(--radius-pill\)/, "the pill");
  assert.match(r, /background: var\(--overlay-10\)/, "the pane's pill wash (.wt-file)");
  assert.match(r, /color: var\(--accent\)/, "a followable link keeps the accent");
  assert.match(r, /text-decoration: none;/, "the pill replaces the link's dotted underline");
  assert.match(r, /font-size: 11px;/, ".wt-file's size, flat: the modal quotes the line in .confirm-detail's 0.92em, where an em compounds");
  assert.match(r, /max-width: 32%;/, "the row's share, as the pane's row gives its chip");
  assert.match(rule(".ut-file.file-uri-link:hover {"), /text-decoration: none/, "the hover underline of .file-uri-link stays off the pill");
  assert.match(rule("#ut-reply-prompt .ut-file {"), /max-width: 100%/, "in the Reply modal the cap is the line, as the pane's modal rule has it");
});

// ── the browser legs ──────────────────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const TEXT = "Pick the layout";                                 // short: the row under test has room on its line for the chip
const DETAIL = "the summary section reads as too confident";
const FILE = "/tmp/TESTHOST/notes-api/docs/report.md";
const FILE_LONG = "/tmp/TESTHOST/notes-api/docs/quarterly_report_layout_options_v3_final.md";
const base = (f: string) => f.split("/").pop()!;
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
// the chip as todoFileChip builds it: openPathLink's span (path-links.ts), the class, the full path as the title
const chipHtml = (file: string) =>
  `<span class="file-uri-link ut-file" title="${esc(file)}" tabindex="0" role="link" data-act="openpath" data-path="${esc(file)}" data-rel="1" data-sid="${SID}">${esc(base(file))}</span>`;
// a row as renderTodo builds it (render.ts): the text span with the hint, the two buttons, the detail fold
const rowHtml = (id: string, file: string | null) =>
  `<div class="ut-item" id="${id}"><div class="ut-line">` +
  `<span class="ut-text ut-has-detail" data-act="uttoggle" data-tid="${id}" title="has details — click to read">${esc(TEXT)}` +
  (file ? " " + chipHtml(file) : "") +
  `<span class="ut-more" title="has details — click to read" aria-label="has details — click to read">▸ details</span></span>` +
  `<button class="ut-btn ut-reply" data-act="utreply" data-tid="${id}" data-sid="${SID}">Reply</button>` +
  `<button class="ut-btn ut-dismiss" data-act="utdismiss" data-tid="${id}" data-sid="${SID}">Dismiss</button>` +
  `</div><div class="ut-detail">${esc(DETAIL)}</div></div>`;
// the chat page: the transcript's todo card in a 600px pane (room on the line: a chip that wraps the text is a taller row
// by design, as any word would be), and the Reply modal as showUserTodoReply builds it, open
const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><link href=/dist/styles.css rel=stylesheet></head><body>
<div id="content"><div class="turn turn-todo"><span class="dot ring"></span><div class="todo-card">
<div class="todo-head ut-head">Waiting on you · 3</div>
${rowHtml("plain", null)}${rowHtml("chip", FILE)}${rowHtml("long", FILE_LONG)}
</div></div></div>
<div class="picker-overlay confirm-overlay" id="ut-reply-prompt"><div class="picker-box confirm-box">
<div class="confirm-title">Reply</div>
<div class="confirm-detail ut-reply-quote">${esc(TEXT)} ${chipHtml(FILE_LONG)}</div>
<div class="ut-detail open">${esc(DETAIL)}</div>
<textarea class="ut-reply-input" rows="3" placeholder="Your answer — it goes straight to the session…"></textarea>
<div class="confirm-actions"><button class="picker-action confirm-btn">Cancel</button><button class="picker-action confirm-btn">Send</button></div>
</div></div></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Box = { top: number; height: number; clientWidth: number; scrollWidth: number; lineWidth: number; display: string; verticalAlign: string; textOverflow: string; maxWidth: string; text: string } | null;

async function boot(browser: any) {
  const errors: string[] = [];
  const page = await browser.newPage({ viewport: { width: 600, height: 640 } });
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
    if (u.pathname === "/dist/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: STYLES_CSS });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/chat");
  // an element's box and the computed values under test; lineWidth is its parent's content width
  const measure = (sel: string): Promise<Box> => page.evaluate((s: string) => {
    const e = document.querySelector(s) as HTMLElement | null;
    if (!e) return null;
    const cs = getComputedStyle(e);
    const p = e.parentElement as HTMLElement;
    const pcs = getComputedStyle(p);
    const r = e.getBoundingClientRect();
    return { top: r.top, height: r.height, clientWidth: e.clientWidth, scrollWidth: e.scrollWidth,
      lineWidth: p.clientWidth - parseFloat(pcs.paddingLeft) - parseFloat(pcs.paddingRight),
      display: cs.display, verticalAlign: cs.verticalAlign, textOverflow: cs.textOverflow, maxWidth: cs.maxWidth, text: e.textContent || "" };
  }, sel);
  // the vertical centre of the row's TEXT (its first text node's box), for the chip to sit on
  const textCentre = (sel: string): Promise<number> => page.evaluate((s: string) => {
    const t = (document.querySelector(s) as HTMLElement).firstChild as Text;
    const rg = document.createRange(); rg.selectNodeContents(t);
    const r = rg.getBoundingClientRect();
    return r.top + r.height / 2;
  }, sel);
  const setClip = (sel: string, on: boolean) => page.evaluate(([s, o]: [string, boolean]) => {
    const e = document.querySelector(s) as HTMLElement;
    if (o) e.style.textOverflow = "clip"; else e.style.removeProperty("text-overflow");
  }, [sel, on] as [string, boolean]);
  const shot = (sel: string) => page.locator(sel).first().screenshot({ animations: "disabled" }) as Promise<Buffer>;
  // does text-overflow reach the chip's text? two paints of the unchanged chip (the control), then one with clip set on
  // the chip itself: the ellipsis is the only thing that can change between them
  const paints = async (sel: string) => {
    const a = await shot(sel);
    const b = await shot(sel);
    await setClip(sel, true);
    const c = await shot(sel);
    await setClip(sel, false);
    return { control: a.equals(b), differs: !a.equals(c) };
  };
  return { page, measure, textCentre, paints, errors };
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: the chip is a pill on the text's line that leaves the row's height alone; a long basename ends in an ellipsis; the modal's chip fits its line`, async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser legs need it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw[name].launch(); }
    catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    try {
      const { measure, textCentre, paints, errors } = await boot(browser);
      const plain = (await measure("#plain .ut-line"))!, withChip = (await measure("#chip .ut-line"))!, withLong = (await measure("#long .ut-line"))!;
      assert.ok(plain.height > 0, "the rows laid out");
      assert.ok(Math.abs(withChip.height - plain.height) <= 2, `a row with the chip is as tall as one without (${withChip.height} vs ${plain.height}px): the chip is inline, on the line (on the baseline it grew the row by 5px, as a block by a line)`);
      assert.ok(Math.abs(withLong.height - plain.height) <= 2, `a long basename does not grow the row either (${withLong.height} vs ${plain.height}px)`);
      const chip = (await measure("#chip .ut-file"))!;
      assert.equal(chip.text, "report.md", "the basename is the label");
      assert.equal(chip.display, "inline-block");
      assert.equal(chip.verticalAlign, "middle");
      const centre = await textCentre("#chip .ut-text");
      assert.ok(Math.abs(chip.top + chip.height / 2 - centre) <= 2.5, `the chip sits on the text's line (chip centre ${(chip.top + chip.height / 2).toFixed(1)}, text centre ${centre.toFixed(1)})`);
      assert.ok(chip.scrollWidth <= chip.clientWidth, "a short basename is painted whole");
      // a long basename: capped at the row's share, cut with an ellipsis that reaches the text
      const long = (await measure("#long .ut-file"))!;
      assert.equal(long.text, base(FILE_LONG), "the whole label is in the text; the ellipsis is paint");
      assert.equal(long.textOverflow, "ellipsis");
      assert.ok(long.scrollWidth > long.clientWidth + 8, `the long basename overflows its cap (${long.clientWidth} of ${long.scrollWidth}px) — the case under test`);
      const p = await paints("#long .ut-file");
      assert.equal(p.control, true, "two paints of the unchanged chip are identical (the control)");
      assert.equal(p.differs, true, "setting text-overflow:clip on the chip changes the paint — the ellipsis was there, so the property reaches the text");
      // the Reply modal: the same chip after the quoted line, capped by the line rather than the row's share
      const modal = (await measure("#ut-reply-prompt .ut-file"))!;
      assert.equal(modal.text, base(FILE_LONG));
      assert.equal(modal.maxWidth, "100%", "the row's 32% share is lifted in the modal");
      assert.ok(modal.scrollWidth <= modal.clientWidth, `a 43-character basename fits on the modal's line (${modal.clientWidth} of ${modal.scrollWidth}px)`);
      assert.ok(modal.clientWidth > 0.32 * modal.lineWidth + 8, `the modal's chip is wider than the row's share of its line (${modal.clientWidth}px of ${modal.lineWidth}px)`);
      const mp = await paints("#ut-reply-prompt .ut-file");
      assert.equal(mp.control, true);
      assert.equal(mp.differs, false, "the whole basename is painted in the modal — clip changes nothing");
      assert.deepEqual(errors, [], "no script error on the page");
    } finally { await browser.close(); }
  });
}
