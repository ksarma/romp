// The shared leg page (real-viewer-leg.ts) inlines the file table into a <script> element, and an HTML tokenizer ends
// script data at the first `</script` whatever the JavaScript around it: JSON.stringify leaves `<` alone, so a fixture
// note holding `</script>` used to cut the harness script off at that point (review of the slice, round 2, 2026-09-08).
// The bundle in the first script element still defined FV (esbuild writes its own output as `<\/script`), the second
// element died with a SyntaxError before the fetch stub, the poster and topBlock were defined, the viewer's fetch of
// /file went to the browser and page.route answered it with the harness page itself, and openViewer returned normally
// over the wrong document; every message a leg then produced pointed away from the fixture. The page now writes every
// inlined value with `<` as `\u003c` (scriptLiteral). Two checks: the page text itself, in node (CI has no browser; the
// second script element holds no `<` outside its own code, and the table reads back through JSON.parse unchanged), and
// the scene in headless Chromium over the real viewer: a note with a script block, a closing tag in a code span and a
// comment opener opens over the page's own fetch stub, topBlock answers, the table holds the fixture's bytes, no script
// error. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only:
// an invented report, /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, pageHtml, topBlock, REPORT, LONG } from "./real-viewer-leg";

/** A note a sanitizer leg would put in the table: a script block, a closing tag inside a code span, a comment opener. */
const SCRIPTED = "# Report\n\nA paragraph before the script.\n\n<script>alert(1)</script>\n\n`</script>` inside a code span, and `<!--` before it.\n\nAfter the script.\n";

const count = (s: string, re: RegExp): number => (s.match(re) || []).length;

test("pageHtml over a note holding </script>: the script elements stay balanced and the table reads back unchanged", () => {
  const control = pageHtml("pane", { [REPORT]: LONG });
  const html = pageHtml("pane", { [REPORT]: SCRIPTED });
  assert.equal(count(control, /<script[\s>]/g), 2, "the control page: the bundle and the harness");
  assert.equal(count(html, /<script[\s>]/g), count(control, /<script[\s>]/g), "the fixture opens no script element of its own");
  assert.equal(count(html, /<\/script/g), count(control, /<\/script/g), "and closes none");
  const m = /window\.__docs = (\{.*?\}); window\.__urls/.exec(html);
  assert.ok(m, "the table is on its line");
  assert.ok(!/<|-->/.test(m![1]), "the inlined table holds no `<` (written \\u003c) and no comment closer");
  assert.deepEqual(JSON.parse(m![1]), { [REPORT]: SCRIPTED }, "and reads back as the fixture, byte for byte");
});

test("in a browser, the real viewer over a note holding </script>: the page's own fetch answers, topBlock works, the table holds the bytes", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openViewer(browser, "pane", 900, 600, { docs: { [REPORT]: SCRIPTED } });
    const facts = await page.evaluate((p: string) => {
      const md = document.querySelector(".fileview-md")!;
      return {
        fetches: (window as any).__fetches, stubbed: String(window.fetch).indexOf("__fetches") >= 0,
        topBlock: typeof (window as any).topBlock, doc: (window as any).__docs[p],
        firstP: (md.querySelector("p")!.textContent || "").trim(), scripts: md.querySelectorAll("script").length,
      };
    }, REPORT);
    assert.equal(facts.stubbed, true, "the page's fetch stub is installed (the harness script ran to its end)");
    assert.equal(facts.fetches, 1, "and it answered the viewer's one fetch");
    assert.equal(facts.topBlock, "function", "topBlock is defined");
    assert.equal(facts.doc, SCRIPTED, "the table holds the fixture's bytes");
    assert.equal(facts.firstP, "A paragraph before the script.", "the note on screen is the fixture, not the harness page");
    assert.equal(facts.scripts, 0, "the sanitizer dropped the script block");
    const top = await topBlock(page);
    assert.equal(top && top.text, "Report", "the top block reads");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
