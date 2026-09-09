// The Copy button's label is not the note's text to the anchor map, in headless Chromium over the real viewer (Slice 3 of
// plans/markdown-viewer.md; the slice's review, round 1). mdBlock parks a `<button class="code-copy">Copy</button>` inside every
// fence's <pre> (code-block.ts addCopyBtn), and anchor-map.ts pairs each source block with its rendered element by comparing the
// element's whole text with the block's emitted characters: with the button's "Copy" in that text, every block holding a fence
// (the fence's own, a list or a quote with one anywhere in it) missed the comparison and was refused as "a block whose rendered
// text does not match the file". Three consequences, each measured here against the base commit's behaviour: prose in a list
// or a quote that holds a fence maps again (it was refused from Rendered, the Raw view the only way to comment on it); a
// selection inside a top-level fence is refused as "a code block", the refusal the design names, not one that blames a stale
// render; and paintRendered's fallback no longer counts the word Copy in the fence's hay, so a comment on `print("Copy")`'s Copy
// paints. The fix is anchor-map.ts's: its text walks skip the button. Synthetic note, the harness's paths and sid; skips loudly
// without a browser, as the other legs do.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { inBrowser, openViewer, requireCjs, UI, EXT, REPORT, type Mode } from "./real-viewer-leg";

const F = "```";
const NOTE = ["# Handler notes", "",
  "- item one has **bold** text", "", "  " + F + "python", "  in_list = 1", "  " + F, "", "- item two is plain prose", "",
  "> quote line before", ">", "> " + F, "> code", "> " + F, ">", "> quote line after", "",
  F + "python", 'print("Copy")', F, "",
  "After paragraph.", ""].join("\n");

/** anchor-map's mapping and paint, bundled from this tree, as window.AM. */
function anchorMapBundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import { mapRenderedSelection, paintRendered } from "./anchor-map"; (window as any).AM = { mapRenderedSelection, paintRendered };', resolveDir: UI, loader: "ts", sourcefile: "am-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

for (const mode of ["pane", "chat"] as Mode[]) {
  test(`in a browser, the real viewer, ${mode}: prose beside a fence in a list or a quote maps from Rendered; a fence refuses as a code block; the word Copy paints inside a fence`, { timeout: 90000 }, async (t) => {
    await inBrowser(t, async (browser) => {
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE } });
      await page.addScriptTag({ content: anchorMapBundle() });
      const out = await page.evaluate((src: string) => {
        const AM = (window as any).AM;
        const root = document.querySelector(".fileview-md")!;
        const select = (needle: string, scope: Element = root) => {
          const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
          for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) {
            const i = n.data.indexOf(needle);
            if (i >= 0) return AM.mapRenderedSelection({ anchorNode: n, anchorOffset: i, focusNode: n, focusOffset: i + needle.length, isCollapsed: false }, root, src);
          }
          return { ok: false, reason: "needle not in the DOM: " + needle };
        };
        const pres = Array.from(root.querySelectorAll("pre"));
        const copyButtons = root.querySelectorAll(".code-copy").length;
        const itemTwo = select("item two");
        const itemOne = select("item one");
        const quoteBefore = select("quote line before");
        const quoteAfter = select("quote line after");
        const inFence = select("print", pres[pres.length - 1]);
        const after = select("After paragraph");
        const at = src.indexOf('"Copy"') + 1;
        const marks = AM.paintRendered(root, src, { start: at, end: at + 4 }, "fc-probe");
        const painted = Array.from(root.querySelectorAll(".fc-probe")).map((m) => ((m.closest("pre") ? "pre:" : "") + m.textContent));
        return { copyButtons, itemTwo, itemOne, quoteBefore, quoteAfter, inFence, after, paint: { returned: marks ? marks.length : null, painted } };
      }, NOTE);
      assert.deepEqual(errors, [], mode + ": no script error");
      assert.equal(out.copyButtons, 3, mode + ": every fence has Copy (the shape under test)");
      for (const [name, r, quote] of [["item two", out.itemTwo, "item two"], ["item one", out.itemOne, "item one"], ["quote line before", out.quoteBefore, "quote line before"], ["quote line after", out.quoteAfter, "quote line after"], ["After paragraph", out.after, "After paragraph"]] as [string, any, string][]) {
        assert.equal(r.ok, true, `${mode}: "${name}" maps from Rendered (before the fix: ${r.reason || "refused"})`);
        assert.equal(r.quote, quote, `${mode}: "${name}" quotes its own words`);
      }
      assert.equal(out.inFence.ok, false, mode + ": a selection inside a fence is refused");
      assert.match(out.inFence.reason, /touches a code block;/, mode + ": ...as a code block, with the Raw offer (before the fix: a block whose rendered text does not match the file)");
      assert.equal(out.inFence.rawHasQuote, true, mode + ": ...and the Raw view is offered");
      assert.equal(out.paint.returned, 1, mode + ": the word Copy inside a fence paints one mark (before the fix: null, the button's Copy counted in the hay)");
      assert.deepEqual(out.paint.painted, ["pre:Copy"], mode + ": ...inside the fence");
      await page.close();
    });
  });
}
