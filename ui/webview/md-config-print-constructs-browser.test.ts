// The Slice 4 constructs under PRINT media (plans/markdown-viewer.md, "one markdown configuration, Obsidian constructs
// included", over Slice 3's print block: "a long note prints multi-page in black"). The slice's review round 4 found the
// construct rules outranking the print block: `.md .md-footnote, .fileview-md .md-footnote { color: var(--dim) }`, the
// front matter's and the gate placeholder's like it, are two classes deep, where the block blacks the ink with
// `.fileview-md { color: black }` alone (one class) and names the plain quote but none of the three, so under the default
// theme a footnote definition, the fold's "Front matter" label, its YAML and a placeholder's "Image from host" printed in
// the dim grey at 2.81:1 on the white page while the paragraph and the plain quote beside them printed black; and the
// rails and the boxes kept their screen tokens where the block blacks every other border (a note callout's rail the accent
// at 1.61:1, a custom type's, the footnote's and the front matter's the hairline, white on white on the feed page). The
// block names the three now (ink and border black, the placeholder's wash off) and sets a callout's `--callout` to black,
// the variable its rail and wash ride, so a callout prints a black rail over a faint grey wash beside the plain quote's
// black rail. Measured here over the real viewer bundle, the kernel's THEME_CSS after the sheet as the pages have it, on
// the pane, the chat modal and the feed page, default theme and light: the screen values first (the dim tier, the tints),
// then under `page.emulateMedia({ media: "print" })`, then back under screen media, where each value returns. Round 5 found
// two constructs the line had missed: the embed chip `![[Other]]` renders in a file document, `a.fv-embed`, kept its
// hairline box (rgba(255, 255, 255, 0.12) on the feed page's dark themes, white on the white paper, where its text printed
// black through `.fileview-md a`), and the ==mark== kept its screen wash, 35% of the theme's --warn, so the same note printed
// two tints from two themes (rgb(241, 223, 186) from the dark page, rgb(220, 203, 166) from the light one); the block names
// the chip on the construct line and gives the mark one print wash, 15% black, read here on every cell and held to one value
// across the themes. Skips loudly without a browser. Synthetic values only: hosts under .test, no real note.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, frames, REPORT, UI, EXT, type Mode } from "./real-viewer-leg";

const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
// the kernel's inlined theme sheet, after the sheet in the cascade as the kernel's pages put it (file-view-print-browser's idiom)
const KERNEL = fs.readFileSync(path.resolve(EXT, "..", "kernel", "kernel.py"), "utf8");
const THEME_CSS = (/\nTHEME_CSS = """([\s\S]*?)"""/.exec(KERNEL) || [])[1] || "";
const NOTE = ["---", "title: Print me", "tags: [a, b]", "---", "", "# Print me", "",
  "A paragraph with a footnote[^1] and a [link](https://example.test/).", "",
  "[^1]: The footnote definition text.", "",
  "> A plain quote, for comparison.", "",
  "> [!NOTE] A note", "> Its body.", "",
  "> [!custom] A type the sheet does not map", "> Its body.", "",
  "> [!TIP]- A folded tip", "> Its body.", "",
  "A remote picture: ![remote](https://figures.example.test/pic.png)", "",
  "A ==highlighted run== beside an embed ![[Other]] of another note.", "",
  "The last paragraph.", ""].join("\n");
const BLACK = "rgb(0, 0, 0)", WHITE = "rgb(255, 255, 255)", CLEAR = "rgba(0, 0, 0, 0)";

// ── the sheets: the block names the constructs, byte-equal ─────────────────────────────────────────

test("the print block blacks the footnote, the front matter, the gate placeholder and the embed chip (ink and border), takes the placeholder's wash off, sets a callout's --callout to black and gives the ==mark== one neutral wash, in both sheets", () => {
  for (const f of ["styles.css", "feed.css"]) {
    const css = read(f); const block = css.slice(css.indexOf("@media print {"));
    assert.ok(block.includes(".fileview-md .md-footnote, .fileview-md details.md-frontmatter, .fileview-md .fv-gate, .fileview-md a.fv-embed { color: black; border-color: black; }"), f + ": the four construct rules, two classes deep, outranked `.fileview-md { color: black }` and the border list (the embed chip joined in round 5)");
    assert.ok(block.includes(".fileview-md .fv-gate { background: none; }"), f + ": the placeholder's wash goes, as every other wash in the block");
    assert.ok(block.includes(".fileview-md .md-callout { --callout: black; }"), f + ": the rail and the wash ride --callout, so the variable is what the block sets");
    assert.ok(block.includes(".fileview-md mark.md-mark { background: color-mix(in srgb, black 15%, transparent); }"), f + ": the ==mark== prints one neutral wash whatever the theme (round 5: it kept 35% of the theme's --warn)");
  }
  const at = (css: string) => css.slice(css.indexOf("@media print {"));
  assert.equal(at(read("styles.css")), at(read("feed.css")), "the block mirrors exactly (file-view-print-browser.test.ts pins the slice from its comment on)");
});

// ── colour arithmetic: a computed colour as rgb(), rgba() or color(srgb r g b / a) ─────────────────
type RGBA = [number, number, number, number];
function parse(s: string): RGBA {
  let m = /^rgba?\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\s*\)$/.exec(s);
  if (m) return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
  m = /^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\s*\)$/.exec(s);
  if (m) return [+m[1] * 255, +m[2] * 255, +m[3] * 255, m[4] === undefined ? 1 : +m[4]];
  throw new Error("a colour this test cannot read: " + s);
}

// ── the browser leg ────────────────────────────────────────────────────────────────────────────────

type Callout = { cls: string; tag: string; rail: string; railW: string; wash: string; ink: string; title: string };
type Facts = { matchesPrint: boolean; page: string; body: string; quote: { ink: string; rail: string }; frontMatter: { open: boolean; ink: string; label: string; yaml: string; border: string; borderW: string } | null;
  footnote: { ink: string; rail: string; railW: string; back: string } | null; callouts: Callout[]; gate: { ink: string; label: string; border: string; style: string; wash: string; text: string } | null;
  embed: { ink: string; border: string; style: string; borderW: string; text: string } | null; mark: { ink: string; wash: string; text: string } | null };
function facts(): Facts {
  const md = document.querySelector(".fileview-md")!; const cs = (e: Element) => getComputedStyle(e); const q = (s: string) => md.querySelector(s);
  const fm = q("details.md-frontmatter") as HTMLDetailsElement | null, fn = q(".md-footnote"), gate = q('.fv-gate[data-act="fv-load"]'), quote = q(":scope > blockquote:not(.md-callout)")!;
  const embed = q("a.fv-embed"), mark = q("mark.md-mark");
  return {
    embed: embed ? { ink: cs(embed).color, border: cs(embed).borderTopColor, style: cs(embed).borderTopStyle, borderW: cs(embed).borderTopWidth, text: (embed.textContent || "").trim() } : null,
    mark: mark ? { ink: cs(mark).color, wash: cs(mark).backgroundColor, text: (mark.textContent || "").trim() } : null,
    matchesPrint: matchMedia("print").matches, page: cs(document.body).backgroundColor, body: cs(q(":scope > p")!).color,
    quote: { ink: cs(quote).color, rail: cs(quote).borderLeftColor },
    frontMatter: fm ? { open: fm.open, ink: cs(fm).color, label: cs(fm.querySelector("summary")!).color, yaml: cs(fm.querySelector("pre")!).color, border: cs(fm).borderTopColor, borderW: cs(fm).borderTopWidth } : null,
    footnote: fn ? { ink: cs(fn).color, rail: cs(fn).borderLeftColor, railW: cs(fn).borderLeftWidth, back: cs(fn.querySelector(".md-fnback")!).color } : null,
    callouts: Array.from(md.querySelectorAll(".md-callout")).map((el) => ({ cls: el.className, tag: el.tagName.toLowerCase(), rail: cs(el).borderLeftColor, railW: cs(el).borderLeftWidth, wash: cs(el).backgroundColor, ink: cs(el).color, title: cs(el.querySelector(".md-callout-title")!).color })),
    gate: gate ? { ink: cs(gate).color, label: cs(gate.querySelector("[data-fv-label]")!).color, border: cs(gate).borderTopColor, style: cs(gate).borderTopStyle, wash: cs(gate).backgroundColor, text: (gate.textContent || "").trim() } : null,
  };
}

test("under print media a footnote definition, the front matter, a gated figure's placeholder, the embed chip and every callout print black ink and black rails on the white page, and the ==mark== one neutral wash from every theme, on the pane, the chat modal and the feed page; screen media restores each", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const markWashes = new Map<string, string>();   // the mark's print wash per cell: one value from every theme and surface
    for (const [mode, light] of [["pane", false], ["chat", false], ["feed", false], ["pane", true], ["feed", true]] as [Mode, boolean][]) {
      const cell = `${mode} ${light ? "light" : "dark"}`;
      const { page, errors } = await openViewer(browser, mode, 900, 700, { docs: { [REPORT]: NOTE }, theme: THEME_CSS });
      if (light) { await page.evaluate(() => { document.body.classList.add("theme-light"); }); await frames(page, 2); }
      await page.waitForFunction(() => document.querySelectorAll(".fileview-md .md-callout").length >= 3 && !!document.querySelector('.fileview-md .fv-gate[data-act="fv-load"]') && !!document.querySelector(".fileview-md .md-footnote")
        && !!document.querySelector(".fileview-md a.fv-embed") && !!document.querySelector(".fileview-md mark.md-mark"), null, { timeout: 10000 });
      // the fold open, so its YAML is laid out and reads a colour (a closed details hides its body in print too; the label prints always)
      await page.evaluate(() => { (document.querySelector(".fileview-md details.md-frontmatter") as HTMLDetailsElement).open = true; }); await frames(page, 2);
      const screen = await page.evaluate(facts) as Facts;
      assert.equal(screen.matchesPrint, false, cell + ": screen media first");
      assert.ok(screen.frontMatter && screen.footnote && screen.gate, cell + ": the note renders its front matter, its footnote and a gated figure");
      assert.equal(screen.frontMatter!.open, true);
      assert.equal(screen.callouts.length, 3, cell + ": three callouts (a note, a custom type, a folded tip)");
      assert.ok(screen.callouts.some((c) => c.tag === "details"), cell + ": one of them folded");
      assert.match(screen.gate!.text, /^Image from figures\.example\.test\./, cell + ": the placeholder names the host");
      // the screen's dress, the state the review measured: the dim tier and the tints, none of it black
      assert.notEqual(screen.footnote!.ink, BLACK, cell + ": on screen the footnote reads dim"); assert.equal(screen.footnote!.ink, screen.quote.ink, cell + ": ...the plain quote's tier");
      assert.equal(screen.frontMatter!.ink, screen.quote.ink, cell + ": ...the front matter too"); assert.equal(screen.gate!.ink, screen.quote.ink, cell + ": ...and the placeholder");
      assert.notEqual(screen.callouts[0].rail, screen.quote.rail, cell + ": on screen the note callout's rail is its tint, not the quote's hairline");
      assert.ok(screen.embed && screen.mark, cell + ": the note renders the embed chip and the ==mark==");
      assert.equal(screen.embed!.text, "Other", cell + ": ![[Other]] is the chip naming the note"); assert.equal(screen.mark!.text, "highlighted run");
      assert.equal(screen.embed!.border, screen.footnote!.rail, cell + ": on screen the chip's box is the hairline, the footnote rail's token"); assert.notEqual(screen.embed!.border, BLACK);
      assert.notEqual(screen.mark!.wash, CLEAR, cell + ": on screen the mark wears its wash"); assert.notDeepEqual(parse(screen.mark!.wash).slice(0, 3).map(Math.round), [0, 0, 0], cell + ": ...the theme's amber, not a neutral (" + screen.mark!.wash + ")");
      await page.emulateMedia({ media: "print" }); await frames(page, 3);
      const pr = await page.evaluate(facts) as Facts;
      assert.equal(pr.matchesPrint, true, cell + ": print media");
      assert.equal(pr.page, WHITE, cell + ": the page prints white"); assert.equal(pr.body, BLACK, cell + ": the paragraph prints black");
      assert.equal(pr.quote.ink, BLACK, cell + ": the plain quote prints black (the control the block always named)"); assert.equal(pr.quote.rail, BLACK, cell + ": ...with a black rail");
      const fm = pr.frontMatter!, fn = pr.footnote!, gate = pr.gate!;
      assert.equal(fm.ink, BLACK, cell + ": the front matter prints black (before: " + screen.frontMatter!.ink + ", the dim tier, under 3:1 on white in the default theme)");
      assert.equal(fm.label, BLACK, cell + ": ...its fold label"); assert.equal(fm.yaml, BLACK, cell + ": ...and its YAML");
      assert.equal(fm.border, BLACK, cell + ": the front matter's box prints black (before: " + screen.frontMatter!.border + ")"); assert.equal(fm.borderW, "1px");
      assert.equal(fn.ink, BLACK, cell + ": the footnote definition prints black (before: " + screen.footnote!.ink + ")"); assert.equal(fn.back, BLACK, cell + ": ...its back link too");
      assert.equal(fn.rail, BLACK, cell + ": the footnote's rail prints black (before: " + screen.footnote!.rail + ")"); assert.equal(fn.railW, "2px");
      for (const c of pr.callouts) {
        const who = cell + ": " + c.tag + "." + c.cls.split(" ").pop();
        assert.equal(c.rail, BLACK, who + ": the callout's rail prints black (before: " + screen.callouts.find((s) => s.cls === c.cls)!.rail + ")"); assert.equal(c.railW, "3px", who + ": ...at the callout's 3px");
        assert.equal(c.ink, BLACK, who + ": the callout's body prints black"); assert.equal(c.title, BLACK, who + ": ...and its title");
        const wash = parse(c.wash);
        assert.deepEqual(wash.slice(0, 3).map(Math.round), [0, 0, 0], who + ": the wash is 8% of black, a neutral grey, not the tint (" + c.wash + "; before: " + screen.callouts.find((s) => s.cls === c.cls)!.wash + ")");
        assert.ok(wash[3] > 0.05 && wash[3] < 0.12, who + ": ...at the rule's 8% (" + c.wash + ")");
      }
      assert.equal(gate.ink, BLACK, cell + ": the placeholder prints black (before: " + screen.gate!.ink + ")"); assert.equal(gate.label, BLACK, cell + ": ...its label too");
      assert.equal(gate.border, BLACK, cell + ": the placeholder's dashed box prints black (before: " + screen.gate!.border + ")"); assert.equal(gate.style, "dashed", cell + ": ...still dashed");
      assert.equal(gate.wash, CLEAR, cell + ": the placeholder's wash is off (before: " + screen.gate!.wash + ")");
      // round 5: the embed chip's box and the mark's wash
      const embed = pr.embed!, mark = pr.mark!;
      assert.equal(embed.border, BLACK, cell + ": the embed chip's box prints black (before: " + screen.embed!.border + ", the screen token: white on white on the feed page)");
      assert.equal(embed.style, "solid", cell + ": ...still drawn"); assert.equal(embed.borderW, "1px"); assert.equal(embed.ink, BLACK, cell + ": ...its text black");
      assert.equal(mark.ink, BLACK, cell + ": the mark's text prints black");
      const wash = parse(mark.wash);
      assert.deepEqual(wash.slice(0, 3).map(Math.round), [0, 0, 0], cell + ": the mark's print wash is neutral, not the theme's amber (" + mark.wash + "; before: " + screen.mark!.wash + ")");
      assert.ok(wash[3] > 0.12 && wash[3] < 0.18, cell + ": ...at the rule's 15% (" + mark.wash + ")");
      markWashes.set(cell, mark.wash);
      await page.emulateMedia({ media: "screen" }); await frames(page, 3);
      const back = await page.evaluate(facts) as Facts;
      assert.deepEqual(back, screen, cell + ": every screen value returns");
      assert.deepEqual(errors, [], cell + ": no script error");
      await page.close();
    }
    assert.equal(new Set(markWashes.values()).size, 1, "one print wash for the mark from every theme and surface (before: two tints, one per theme): " + JSON.stringify(Object.fromEntries(markWashes)));
  });
});
