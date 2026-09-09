// Printing a note (Slice 3 of plans/markdown-viewer.md: "a long note prints multi-page in black"). The audit's defect:
// print gave one clipped grey page on every surface, because the viewer is a fixed overlay over a body that does not
// scroll (the pane's html and body are height 100% and overflow hidden; the modal's card is 95% of a fixed inset-0
// backdrop) and the body row scrolls inside itself, so the printer saw one viewport of dark card and nothing past it.
// The @media print blocks (styles.css and feed.css byte-equal, files-pane.css for the pane's own overrides) make the
// overlay and the card static and unclipped, open the body's scroll box, hide the title bar, the Comments aside, the
// Comment float, the notice bar and the Copy buttons, leave everything else on the page out, and print black on white,
// code included. Measured here first as an A4 PDF of the screen layout, the defect's rendering, asserted to be one page
// (page.pdf renders under print media by default, so the screen layout is asked for with `page.emulateMedia({ media:
// "screen" })`; without the ask that PDF is the print count over again, and the review's round 2 found the count
// reported in a message and pinned nowhere, so a screen ask that stopped taking effect passed), then under
// `page.emulateMedia({ media: "print" })` as computed styles and as a real A4 PDF whose page count for a 120-paragraph
// note is more than one, then back under screen media, where the screen values return. The note's paragraphs are
// separated by blank lines and their count is pinned first, so the fixture is the 120 blocks the messages describe (the
// review, round 2: joined with one newline they rendered as a single <p>, one block with no paragraph margins or block
// boundaries for the pages to break at). The pane and the chat modal (the feed shares feed.css's block, pinned
// byte-equal to styles.css's by the node test below). The page carries the kernel's THEME_CSS after the sheet, as the
// kernel's pages do (review round 3): it paints the root with `html,body{background:...}`, a bare type selector, and the
// block's head was `html, body.fileview-open`, the same specificity later in the cascade, so on the chat and the feed pages
// the root printed the editor's dark grey below the note's end and wherever the body did not cover the page, while the
// harness page, which had no THEME_CSS, printed white and this leg passed; the head is `:root` now, which outranks a type
// selector wherever the theme's rule sits. The same round found a fence's line numbers printing at the screen's 0.32
// opacity (2.24:1 on white, black ink or not); the block sets them, and the Raw view's, to full ink, measured here on the
// fence. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, openPanel, frames, REPORT, UI, EXT, PARA, type Mode } from "./real-viewer-leg";

const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
// The kernel's inlined theme sheet, read from the page builder itself (the browse-route and files legs' idiom): the pages
// put it in a <style> after the sheet's <link>, so its rules come later in the cascade than anything the sheet declares.
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const THEME_CSS = (/\nTHEME_CSS = """([\s\S]*?)"""/.exec(KERNEL) || [])[1] || "";
const F = "```";
const NOTE = ["# Print me", "", "A paragraph with `inline code` and a [link](https://example.test/).", "", F + "python", "# a comment", "def f(x):", "    return x", F, "",
  "| a | b |", "|---|---|", "| 1 | 2 |", "| 3 | 4 |", "",
  Array.from({ length: 120 }, (_, i) => PARA(i + 1)).join("\n\n"), ""].join("\n");   // a blank line between paragraphs: joined with one newline they are one <p> (marked runs with breaks: false)
const PARAGRAPHS = 121;   // the 120 and the one under the heading; pinned below so the fixture stays the note the messages describe

// ── the sheets: one block, byte-equal, and the pane's own ──────────────────────────────────────────

test("the print block is byte-equal in styles.css and feed.css, names every piece of chrome it hides, and files-pane.css carries the pane's overrides with no bare hex", () => {
  const slice = (css: string) => { const at = css.indexOf("/* ── print (Slice 3 of plans/markdown-viewer.md)"); assert.ok(at > 0, "the print block"); return css.slice(at); };
  const chat = slice(read("styles.css")), feed = slice(read("feed.css"));
  assert.equal(chat, feed, "the block mirrors exactly (fileview-parity's ruleOf cannot read a nested block, so the slice is pinned whole)");
  assert.match(chat, /^@media print \{/m);
  assert.equal((chat.match(/@media print/g) || []).length, 1, "one print block per sheet, at its end");
  for (const sel of [".fileview-bar", ".fileview-aside", ".fileview-fc", ".fileview > .fileview-err", ".fc-float", ".fileview-md .code-copy"]) assert.ok(chat.includes(sel), "hidden in print: " + sel);
  assert.match(chat, /^  :root, body\.fileview-open \{ height: auto; overflow: visible; background: white; color: black; \}$/m, "the page prints white at a specificity above a type selector (the kernel's THEME_CSS paints html after the sheet)");
  assert.doesNotMatch(chat, /^\s*html[,\s{]/m, "no bare html head in the block: THEME_CSS's html rule, later in the cascade, would win the tie");
  assert.match(chat, /#romp-fileview \{ position: static; inset: auto; z-index: auto; display: block; background: none; \}/, "the overlay joins the flow");
  assert.match(chat, /\.fileview \{ width: auto; height: auto; display: block; overflow: visible; background: white; color: black;/, "the card is unclipped, white, black text");
  assert.match(chat, /\.fileview-body \{ overflow: visible; container-type: inline-size; \}/, "the body's scroll box opens, and the body is the size container the print table's cqi cap reads (the screen's body is none since round 2: --fv-body-w there)");
  assert.match(chat, /body\.fileview-open > :not\(#romp-fileview\) \{ display: none; \}/, "the rest of the page is left out while a note is open");
  assert.match(chat, /\.fileview-md pre code span,\s*\n?\s*\.fileview-md pre code \.cl::before, \.fileview-md code\.md-math-src \{ color: black; \}/, "code tokens and line numbers print black");
  assert.ok(chat.includes(".fileview-md pre code .cl::before, .fileview-body .fv-cl::before { opacity: 1; }"), "the line numbers print at full ink: the screen rules' 0.32 and 0.55 would stand otherwise, black or not");
  assert.doesNotMatch(chat.replace(/\/\*[\s\S]*?\*\//g, ""), /#[0-9a-fA-F]{3,8}\b(?!-)/, "keywords, no hex");
  const pane = read("files-pane.css");
  const pb = pane.slice(pane.indexOf("@media print{"));
  assert.ok(pb.length > 0, "files-pane.css has its print block");
  assert.match(pb, /html,body\{height:auto;overflow:visible;display:block;background:white;color:black\}/, "the pane's page grows to the note and prints white");
  assert.doesNotMatch(pb, /position:static/, "the pane viewer keeps its position:relative in print too (files.test.ts pins the sheet free of static: the z-index it keeps); in flow it prints as a block");
  assert.match(pb, /body\.fileview-pane \.fileview\{width:auto;height:auto\}/, "the pane's 100% card undone");
  assert.doesNotMatch(pb.replace(/\/\*[\s\S]*?\*\//g, ""), /#[0-9a-fA-F]{3,8}\b(?!-)/, "no bare hex (css-census.test.ts pins the sheet at 0)");
});

test("the kernel's THEME_CSS, which the leg's page inlines after the sheet as the kernel's pages do, paints the root with a type selector", () => {
  assert.ok(THEME_CSS.length > 100, "THEME_CSS read out of kernel/kernel.py (a triple-quoted string; the builder moved or was renamed if this fails)");
  assert.match(THEME_CSS, /(^|[}\s,])html[^{}]*\{[^}]*background:/, "the theme paints html's background: the rule the print block's :root head must outrank (a head of `html` tied with it and lost on the chat and feed pages)");
  assert.doesNotMatch(THEME_CSS, /@media print/, "the theme has no print rules of its own (the leg would have to model them too)");
});

// ── the browser leg ────────────────────────────────────────────────────────────────────────────────

type P = Record<string, any>;
function printFacts(): P {
  const q = (s: string) => document.querySelector(s) as HTMLElement | null; const cs = (e: Element) => getComputedStyle(e);
  const ov = q("#romp-fileview")!, card = q(".fileview")!, body = q(".fileview-body")!, md = q(".fileview-md")!, bar = q(".fileview-bar")!;
  const cmt = md.querySelector(".hljs-comment"), kw = md.querySelector(".hljs-keyword"), copy = md.querySelector(".code-copy"), aside = q(".fileview-aside"), fc = q(".fileview-fc");
  const row = md.querySelector("pre code .cl")!, ln = getComputedStyle(row, "::before");   // the fence's first line number
  return { matchesPrint: matchMedia("print").matches, paras: md.querySelectorAll(":scope > p").length, htmlBg: cs(document.documentElement).backgroundColor, bodyBg: cs(document.body).backgroundColor, bodyOverflow: cs(document.body).overflow, bodyH: document.body.getBoundingClientRect().height,
    ln: { color: ln.color, opacity: ln.opacity },
    ov: { position: cs(ov).position, display: cs(ov).display, bg: cs(ov).backgroundColor }, card: { width: cs(card).width, height: card.getBoundingClientRect().height, bg: cs(card).backgroundColor, color: cs(card).color, overflow: cs(card).overflow, border: cs(card).borderTopWidth },
    body: { overflow: cs(body).overflow, clientH: body.clientHeight, scrollH: body.scrollHeight }, md: { color: cs(md).color, height: md.getBoundingClientRect().height }, bar: cs(bar).display, aside: aside ? cs(aside).display : "(none mounted)", fc: fc ? cs(fc).display : "(none mounted)",
    copy: copy ? cs(copy).display : "(none)", cmt: cmt ? cs(cmt).color : null, kw: kw ? cs(kw).color : null, code: cs(md.querySelector("pre code")!).whiteSpace, link: cs(md.querySelector("a")!).color, th: cs(md.querySelector("th")!).backgroundColor,
    siblingsShown: Array.from(document.body.children).filter((c) => c !== ov && cs(c).display !== "none").map((c) => c.tagName + (c.className ? "." + c.className : "")) };
}
const pagesOf = (pdf: Buffer): number => (pdf.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) || []).length;

test("under print media the note is a static, unclipped, black-on-white document with its chrome hidden; the A4 PDF of a 120-paragraph note runs to several pages; screen media restores the viewer", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE }, theme: THEME_CSS });   // the kernel's theme after the sheet, as the served pages have it
      await openPanel(page);   // the aside mounted, so its hiding is measured
      const screen0 = await page.evaluate(printFacts);
      assert.equal(screen0.matchesPrint, false);
      assert.ok(screen0.htmlBg !== "rgba(0, 0, 0, 0)" && screen0.htmlBg !== "rgb(255, 255, 255)", mode + ": on screen the theme paints the root (" + screen0.htmlBg + "); the page carries THEME_CSS");
      assert.ok(parseFloat(screen0.ln.opacity) < 1, mode + ": on screen the fence's line numbers are dimmed by opacity (" + screen0.ln.opacity + ")");
      assert.equal(screen0.paras, PARAGRAPHS, mode + ": the note is " + PARAGRAPHS + " paragraphs, each its own block (one newline between them would fold the 120 into one <p>)");
      assert.equal(screen0.bar, "flex", mode + ": on screen the title bar shows"); assert.notEqual(screen0.aside, "none", mode + ": ...and the aside");
      assert.equal(screen0.ov.position, mode === "pane" ? "relative" : "fixed", mode + ": the overlay's screen position");
      assert.ok(screen0.body.scrollH > screen0.body.clientH * 3, mode + ": on screen the body scrolls its 120 paragraphs (" + screen0.body.scrollH + " in " + screen0.body.clientH + ")");
      // the defect's rendering, the screen layout on paper: one page. page.pdf renders under print media by default,
      // so screen media is asked for; without the ask this count is the print count over again, not a baseline
      await page.emulateMedia({ media: "screen" }); await frames(page, 2);
      const before = pagesOf(await page.pdf({ format: "A4", printBackground: true }));
      assert.equal(before, 1, mode + ": the screen layout on paper is the defect's one page (" + before + "; the print count over again means the screen ask did not take)");
      await page.emulateMedia({ media: "print" }); await frames(page, 2);
      const pr = await page.evaluate(printFacts);
      assert.equal(pr.matchesPrint, true);
      assert.equal(pr.htmlBg, "rgb(255, 255, 255)", mode + ": the page prints white (the root: THEME_CSS's html rule, later in the cascade, painted it " + screen0.htmlBg + " on the chat and feed pages under a head of the same specificity)"); assert.equal(pr.bodyBg, "rgb(255, 255, 255)");
      assert.equal(pr.bodyOverflow, "visible", mode + ": the page's overflow is visible");
      assert.equal(pr.ov.position, mode === "pane" ? "relative" : "static", mode + ": the overlay is in flow (the modal's fixed goes static; the pane's relative stands, its z-index kept)"); assert.equal(pr.ov.display, "block"); assert.equal(pr.ov.bg, "rgba(0, 0, 0, 0)", mode + ": no dim");
      assert.equal(pr.card.bg, "rgb(255, 255, 255)", mode + ": the card is white"); assert.equal(pr.card.color, "rgb(0, 0, 0)", mode + ": ...with black text"); assert.equal(pr.card.overflow, "visible"); assert.equal(pr.card.border, "0px");
      assert.equal(pr.body.overflow, "visible", mode + ": the body's scroll box is open");
      assert.ok(pr.card.height >= pr.md.height - 1 && pr.body.clientH >= pr.body.scrollH - 1, mode + ": the card and the body are as tall as the note (" + pr.card.height + ", " + pr.md.height + ")");
      assert.ok(pr.bodyH > 5000, mode + ": the document is thousands of pixels tall (" + pr.bodyH + ")");
      assert.equal(pr.md.color, "rgb(0, 0, 0)", mode + ": the prose is black"); assert.equal(pr.link, "rgb(0, 0, 0)", mode + ": links black");
      assert.equal(pr.cmt, "rgb(0, 0, 0)", mode + ": a code comment prints black"); assert.equal(pr.kw, "rgb(0, 0, 0)", mode + ": a keyword too"); assert.equal(pr.code, "pre-wrap", mode + ": code keeps wrapping");
      assert.equal(pr.ln.color, "rgb(0, 0, 0)", mode + ": the fence's line numbers print black"); assert.equal(pr.ln.opacity, "1", mode + ": ...at full ink (the screen's " + screen0.ln.opacity + " would print them as 32% black, 2.24:1)");
      assert.equal(pr.th, "rgba(0, 0, 0, 0)", mode + ": no grey fill on paper");
      assert.equal(pr.bar, "none", mode + ": the title bar is hidden"); assert.equal(pr.aside, "none", mode + ": the aside is hidden"); assert.equal(pr.copy, "none", mode + ": the Copy buttons are hidden");
      assert.deepEqual(pr.siblingsShown, [], mode + ": nothing else on the page prints (the Comment float, scripts, the pane's empty state): " + pr.siblingsShown.join(", "));
      const pdf = await page.pdf({ format: "A4", printBackground: true });
      const pages = pagesOf(pdf);
      assert.ok(pages > 1, mode + ": the A4 PDF runs to several pages (" + pages + "; the screen layout put on paper, the defect's rendering, gives " + before + ")");
      assert.ok(pages >= 5, mode + ": 120 paragraphs are at least five A4 pages (" + pages + ")");
      const noBg = pagesOf(await page.pdf({ format: "A4", printBackground: false }));
      assert.equal(noBg, pages, mode + ": the page count does not depend on backgrounds");
      // back to the screen
      await page.emulateMedia({ media: "screen" }); await frames(page, 2);
      const screen1 = await page.evaluate(printFacts);
      assert.equal(screen1.matchesPrint, false);
      assert.equal(screen1.bar, "flex", mode + ": the title bar is back"); assert.equal(screen1.ov.position, screen0.ov.position, mode + ": the overlay's position is back");
      assert.equal(screen1.body.overflow, "auto", mode + ": the body scrolls again"); assert.equal(screen1.md.color, screen0.md.color, mode + ": the prose colour is back");
      assert.equal(screen1.htmlBg, screen0.htmlBg, mode + ": the theme's root paint is back"); assert.equal(screen1.ln.opacity, screen0.ln.opacity, mode + ": the gutter's dim is back");
      assert.notEqual(screen1.aside, "none", mode + ": the aside shows again");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});
