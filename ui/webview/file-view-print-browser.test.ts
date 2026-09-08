// Printing a note (Slice 3 of plans/markdown-viewer.md: "a long note prints multi-page in black"). The audit's defect:
// print gave one clipped grey page on every surface, because the viewer is a fixed overlay over a body that does not
// scroll (the pane's html and body are height 100% and overflow hidden; the modal's card is 95% of a fixed inset-0
// backdrop) and the body row scrolls inside itself, so the printer saw one viewport of dark card and nothing past it.
// The @media print blocks (styles.css and feed.css byte-equal, files-pane.css for the pane's own overrides) make the
// overlay and the card static and unclipped, open the body's scroll box, hide the title bar, the Comments aside, the
// Comment float, the notice bar and the Copy buttons, leave everything else on the page out, and print black on white,
// code included. Measured here first as an A4 PDF of the screen layout, the defect's rendering, one page (page.pdf
// renders under print media by default, so the screen layout is asked for with `page.emulateMedia({ media: "screen"
// })`; without the ask that PDF is the print count over again), then under `page.emulateMedia({ media: "print" })` as
// computed styles and as a real A4 PDF whose page count for a 120-paragraph note is more than one, then back under
// screen media, where the screen values return. The pane and the chat modal (the feed shares feed.css's block, pinned
// byte-equal to styles.css's by the node test below). Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, openPanel, frames, REPORT, UI, type Mode } from "./real-viewer-leg";

const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const F = "```";
const NOTE = ["# Print me", "", "A paragraph with `inline code` and a [link](https://example.test/).", "", F + "python", "# a comment", "def f(x):", "    return x", F, "",
  "| a | b |", "|---|---|", "| 1 | 2 |", "| 3 | 4 |", "",
  ...Array.from({ length: 120 }, (_, i) => "Paragraph " + (i + 1) + ": " + "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor ".repeat(3).trim() + "."), ""].join("\n");

// ── the sheets: one block, byte-equal, and the pane's own ──────────────────────────────────────────

test("the print block is byte-equal in styles.css and feed.css, names every piece of chrome it hides, and files-pane.css carries the pane's overrides with no bare hex", () => {
  const slice = (css: string) => { const at = css.indexOf("/* ── print (Slice 3 of plans/markdown-viewer.md)"); assert.ok(at > 0, "the print block"); return css.slice(at); };
  const chat = slice(read("styles.css")), feed = slice(read("feed.css"));
  assert.equal(chat, feed, "the block mirrors exactly (fileview-parity's ruleOf cannot read a nested block, so the slice is pinned whole)");
  assert.match(chat, /^@media print \{/m);
  assert.equal((chat.match(/@media print/g) || []).length, 1, "one print block per sheet, at its end");
  for (const sel of [".fileview-bar", ".fileview-aside", ".fileview-fc", ".fileview > .fileview-err", ".fc-float", ".fileview-md .code-copy"]) assert.ok(chat.includes(sel), "hidden in print: " + sel);
  assert.match(chat, /#romp-fileview \{ position: static; inset: auto; z-index: auto; display: block; background: none; \}/, "the overlay joins the flow");
  assert.match(chat, /\.fileview \{ width: auto; height: auto; display: block; overflow: visible; background: white; color: black;/, "the card is unclipped, white, black text");
  assert.match(chat, /\.fileview-body \{ overflow: visible; \}/, "the body's scroll box opens");
  assert.match(chat, /body\.fileview-open > :not\(#romp-fileview\) \{ display: none; \}/, "the rest of the page is left out while a note is open");
  assert.match(chat, /\.fileview-md pre code span,\s*\n?\s*\.fileview-md pre code \.cl::before, \.fileview-md code\.md-math-src \{ color: black; \}/, "code tokens and line numbers print black");
  assert.doesNotMatch(chat.replace(/\/\*[\s\S]*?\*\//g, ""), /#[0-9a-fA-F]{3,8}\b(?!-)/, "keywords, no hex");
  const pane = read("files-pane.css");
  const pb = pane.slice(pane.indexOf("@media print{"));
  assert.ok(pb.length > 0, "files-pane.css has its print block");
  assert.match(pb, /html,body\{height:auto;overflow:visible;display:block;background:white;color:black\}/, "the pane's page grows to the note and prints white");
  assert.doesNotMatch(pb, /position:static/, "the pane viewer keeps its position:relative in print too (files.test.ts pins the sheet free of static: the z-index it keeps); in flow it prints as a block");
  assert.match(pb, /body\.fileview-pane \.fileview\{width:auto;height:auto\}/, "the pane's 100% card undone");
  assert.doesNotMatch(pb.replace(/\/\*[\s\S]*?\*\//g, ""), /#[0-9a-fA-F]{3,8}\b(?!-)/, "no bare hex (css-census.test.ts pins the sheet at 0)");
});

// ── the browser leg ────────────────────────────────────────────────────────────────────────────────

type P = Record<string, any>;
function printFacts(): P {
  const q = (s: string) => document.querySelector(s) as HTMLElement | null; const cs = (e: Element) => getComputedStyle(e);
  const ov = q("#romp-fileview")!, card = q(".fileview")!, body = q(".fileview-body")!, md = q(".fileview-md")!, bar = q(".fileview-bar")!;
  const cmt = md.querySelector(".hljs-comment"), kw = md.querySelector(".hljs-keyword"), copy = md.querySelector(".code-copy"), aside = q(".fileview-aside"), fc = q(".fileview-fc");
  return { matchesPrint: matchMedia("print").matches, htmlBg: cs(document.documentElement).backgroundColor, bodyBg: cs(document.body).backgroundColor, bodyOverflow: cs(document.body).overflow, bodyH: document.body.getBoundingClientRect().height,
    ov: { position: cs(ov).position, display: cs(ov).display, bg: cs(ov).backgroundColor }, card: { width: cs(card).width, height: card.getBoundingClientRect().height, bg: cs(card).backgroundColor, color: cs(card).color, overflow: cs(card).overflow, border: cs(card).borderTopWidth },
    body: { overflow: cs(body).overflow, clientH: body.clientHeight, scrollH: body.scrollHeight }, md: { color: cs(md).color, height: md.getBoundingClientRect().height }, bar: cs(bar).display, aside: aside ? cs(aside).display : "(none mounted)", fc: fc ? cs(fc).display : "(none mounted)",
    copy: copy ? cs(copy).display : "(none)", cmt: cmt ? cs(cmt).color : null, kw: kw ? cs(kw).color : null, code: cs(md.querySelector("pre code")!).whiteSpace, link: cs(md.querySelector("a")!).color, th: cs(md.querySelector("th")!).backgroundColor,
    siblingsShown: Array.from(document.body.children).filter((c) => c !== ov && cs(c).display !== "none").map((c) => c.tagName + (c.className ? "." + c.className : "")) };
}
const pagesOf = (pdf: Buffer): number => (pdf.toString("latin1").match(/\/Type\s*\/Page(?![s\w])/g) || []).length;

test("under print media the note is a static, unclipped, black-on-white document with its chrome hidden; the A4 PDF of a 120-paragraph note runs to several pages; screen media restores the viewer", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as Mode[]) {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE } });
      await openPanel(page);   // the aside mounted, so its hiding is measured
      const screen0 = await page.evaluate(printFacts);
      assert.equal(screen0.matchesPrint, false);
      assert.equal(screen0.bar, "flex", mode + ": on screen the title bar shows"); assert.notEqual(screen0.aside, "none", mode + ": ...and the aside");
      assert.equal(screen0.ov.position, mode === "pane" ? "relative" : "fixed", mode + ": the overlay's screen position");
      assert.ok(screen0.body.scrollH > screen0.body.clientH * 3, mode + ": on screen the body scrolls its 120 paragraphs (" + screen0.body.scrollH + " in " + screen0.body.clientH + ")");
      // the defect's rendering, the screen layout on paper: one page. page.pdf renders under print media by default,
      // so screen media is asked for; without the ask this count is the print count over again, not a baseline
      await page.emulateMedia({ media: "screen" }); await frames(page, 2);
      const before = pagesOf(await page.pdf({ format: "A4", printBackground: true }));
      await page.emulateMedia({ media: "print" }); await frames(page, 2);
      const pr = await page.evaluate(printFacts);
      assert.equal(pr.matchesPrint, true);
      assert.equal(pr.htmlBg, "rgb(255, 255, 255)", mode + ": the page prints white"); assert.equal(pr.bodyBg, "rgb(255, 255, 255)");
      assert.equal(pr.bodyOverflow, "visible", mode + ": the page's overflow is visible");
      assert.equal(pr.ov.position, mode === "pane" ? "relative" : "static", mode + ": the overlay is in flow (the modal's fixed goes static; the pane's relative stands, its z-index kept)"); assert.equal(pr.ov.display, "block"); assert.equal(pr.ov.bg, "rgba(0, 0, 0, 0)", mode + ": no dim");
      assert.equal(pr.card.bg, "rgb(255, 255, 255)", mode + ": the card is white"); assert.equal(pr.card.color, "rgb(0, 0, 0)", mode + ": ...with black text"); assert.equal(pr.card.overflow, "visible"); assert.equal(pr.card.border, "0px");
      assert.equal(pr.body.overflow, "visible", mode + ": the body's scroll box is open");
      assert.ok(pr.card.height >= pr.md.height - 1 && pr.body.clientH >= pr.body.scrollH - 1, mode + ": the card and the body are as tall as the note (" + pr.card.height + ", " + pr.md.height + ")");
      assert.ok(pr.bodyH > 5000, mode + ": the document is thousands of pixels tall (" + pr.bodyH + ")");
      assert.equal(pr.md.color, "rgb(0, 0, 0)", mode + ": the prose is black"); assert.equal(pr.link, "rgb(0, 0, 0)", mode + ": links black");
      assert.equal(pr.cmt, "rgb(0, 0, 0)", mode + ": a code comment prints black"); assert.equal(pr.kw, "rgb(0, 0, 0)", mode + ": a keyword too"); assert.equal(pr.code, "pre-wrap", mode + ": code keeps wrapping");
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
      assert.notEqual(screen1.aside, "none", mode + ": the aside shows again");
      assert.deepEqual(errors, [], mode + ": no script error");
      await page.close();
    }
  });
});
