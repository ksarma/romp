// Two ways a `#` link's landing went wrong once Slice 4's constructs reached the Files bundle (plans/markdown-viewer.md,
// "one markdown configuration, Obsidian constructs included"; the acceptance is "a `#section` click scrolls
// .fileview-body"), over the REAL Files bundle in headless Chromium:
//   1. A target inside a FOLDED callout (`> [!type]-` renders a closed <details>, new in this slice: before it only an
//      author's own <details> HTML could hold a heading). scrollIntoView reveals nothing (the browser's fragment
//      navigation runs the HTML spec's ancestor revealing steps first; scrollIntoView does not), so a `[..](#inner)`,
//      a `[[#Inner]]` wikilink and a footnote reference whose definition sits in the fold all did nothing: no scroll, the
//      fold shut, no feedback. scrollToFragment now opens every closed <details> on the target's ancestor path and drops a
//      `hidden="until-found"` (md-sanitize.ts revealFragmentTarget, the same steps the chat's `#` delegate runs) before it
//      scrolls. The leg clicks all three shapes with the fold shut each time and reads the details' `open` and the body's
//      scroll; a control click into an OPEN (`[!type]+`) callout shows the click path itself was never the problem.
//   2. A heading with MATH. The viewer mints heading ids from the heading's text (GitHub's slug, `md-` prefixed), and
//      since this slice the math fill runs inside sanitizeMd in the Files and feed bundles too, so a slug read from the
//      sanitized DOM after the fill read KaTeX's glyph text: layout order (a fraction's denominator before its numerator),
//      a U+200B strut, the TeX gone. `# Ratio $\frac{a}{b}$` minted `md-ratio-ba` where the base minted (and GitHub mints)
//      `md-ratio-fracab`, so the note's own `[see](#ratio-fracab)` and a `[[#Ratio $\frac{a}{b}$]]` wikilink rendered dead.
//      The ids are minted BEFORE the fill now (file-view.ts mintHeadingIds, handed to sanitizeMd as the caller's own pass,
//      which runs ahead of the registered ones), from the placeholder's text, which is the TeX as written. The leg reads
//      the id, both links' classes and data-frag, that KaTeX still filled the heading's two formulas, and the click.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an
// invented note, TESTHOST paths, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const DIR = "/tmp/TESTHOST/notes-api/docs/";
const FILE_PATH = DIR + "report.md";

const filler = (n: number, tag: string) => Array.from({ length: n }, (_, i) => `Filler paragraph ${tag} ${i + 1} with enough words to take a line of its own.`).join("\n\n");
/** A note whose `#` links point into a folded callout (a heading, a footnote definition) and into an open one (the control). */
const FOLD_NOTE = [
  "# Top", "",
  "Links: [the inner heading](#inner-heading), [[#Inner Heading]] and a ref[^1]. Also [open callout heading](#open-heading).", "",
  filler(30, "A"), "",
  "> [!note]- Folded section",
  "> ## Inner Heading",
  "> Body inside the fold.",
  ">",
  "> [^1]: The footnote definition text.", "",
  filler(10, "B"), "",
  "> [!note]+ Open section",
  "> ## Open Heading",
  "> Body inside the open callout.", "",
  filler(30, "C"), "",
].join("\n");
/** A note whose first heading holds two formulas and whose own links spell GitHub's slug of it (the TeX as written). */
const MATH_NOTE = [
  "# Ratio $\\frac{a}{b}$ and energy $E=mc^2$", "",
  "Intro paragraph.", "",
  "[see](#ratio-fracab-and-energy-emc2)", "",
  "[[#Ratio $\\frac{a}{b}$ and energy $E=mc^2$]]", "",
  "## Plain heading", "",
  "[plain](#plain-heading)", "",
  filler(40, "M"), "",
].join("\n");

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function filesBundle(): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, "files.ts")] });
  return r.outputFiles[0].text;
}
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

type Opened = { page: any; errors: string[]; newPages: () => number };
/** The Files pane with `note` open as a file document (the pane's relay), the first paint awaited. A short viewport, so every
 *  target sits below the fold and a landing has to scroll. */
async function openNote(browser: any, js: string, note: string): Promise<Opened> {
  const ctx = await browser.newContext({ viewport: { width: 900, height: 300 } });
  let pages = 0;
  ctx.on("page", () => { pages++; });
  const page = await ctx.newPage();
  pages = 0;
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  await ctx.route("**/*", (route: any) => {
    const u = new URL(route.request().url());
    if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });
    if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
    if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
    if (u.pathname === "/file" && u.searchParams.get("path") === FILE_PATH) {
      return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: note });
    }
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/files");
  await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
  await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
  await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
  return { page, errors, newPages: () => pages };
}

/** Where `sel` sits relative to the body's box, and the body's scroll: read in the page. */
function placeOf(sel: string) {
  const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
  const e = document.querySelector("#romp-fileview .fileview-md " + sel) as HTMLElement | null;
  const b = body.getBoundingClientRect();
  const r = e ? e.getBoundingClientRect() : null;
  return { found: !!e, top: r ? Math.round(r.top - b.top) : null, inside: !!r && r.top >= b.top - 1 && r.bottom <= b.bottom, scrollTop: Math.round(body.scrollTop) };
}
type Place = ReturnType<typeof placeOf>;

test("a `#` link, a `[[#Heading]]` wikilink and a footnote reference whose target sits in a FOLDED callout open the fold and scroll the body to it (the fold shut again before each click); the page's location stands and no tab opens", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, newPages } = await openNote(browser, filesBundle(), FOLD_NOTE);
    const url0: string = await page.evaluate(() => location.href);
    const links = await page.evaluate(() => Array.from(document.querySelectorAll("#romp-fileview .fileview-md a")).slice(0, 4).map((a) => [a.getAttribute("href"), a.getAttribute("class"), a.getAttribute("data-frag")]));
    // the three links into the fold and the control are live section links: the targets exist, closed details or not
    assert.deepEqual(links, [["#inner-heading", "fv-frag", "inner-heading"], ["#Inner%20Heading", "fv-frag", "Inner Heading"], ["#fn-1", "fv-frag", "fn-1"], ["#open-heading", "fv-frag", "open-heading"]]);
    const foldState = () => page.evaluate(() => {
      const d = document.querySelector("#romp-fileview .fileview-md details.md-callout") as HTMLElement;
      return { open: d.hasAttribute("open"), heading: !!d.querySelector("#md-inner-heading"), def: !!d.querySelector("#user-content-fn-1") };
    });
    assert.deepEqual(await foldState(), { open: false, heading: true, def: true }, "the fixture: a closed details holding the heading and the definition");
    /** The fold shut and the body at its top, then the click, then where the target sits. */
    const clickInto = async (linkSel: string, targetSel: string): Promise<{ open: boolean; at: Place }> => {
      await page.evaluate(() => {
        (document.querySelector("#romp-fileview .fileview-md details.md-callout") as HTMLElement).removeAttribute("open");
        (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).scrollTop = 0;
      });
      await page.click("#romp-fileview .fileview-md " + linkSel);
      await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
      const open = (await foldState()).open;
      return { open, at: await page.evaluate(placeOf, targetSel) };
    };
    const h = await clickInto('a[href="#inner-heading"]', "#md-inner-heading");
    assert.ok(h.open, "the `#inner-heading` click opened the fold");
    assert.ok(h.at.inside && h.at.top !== null && h.at.top <= 12 && h.at.scrollTop > 0, "the inner heading sits at the body's top edge after the click: " + JSON.stringify(h.at));
    const w = await clickInto('a[href="#Inner%20Heading"]', "#md-inner-heading");
    assert.ok(w.open, "the `[[#Inner Heading]]` click opened the fold");
    assert.ok(w.at.inside && w.at.top !== null && w.at.top <= 12 && w.at.scrollTop > 0, "the wikilink lands the same way: " + JSON.stringify(w.at));
    const f = await clickInto("sup.md-fnref a", "#user-content-fn-1");
    assert.ok(f.open, "the footnote reference's click opened the fold its definition sits in");
    assert.ok(f.at.inside && f.at.scrollTop > 0, "the definition is in view: " + JSON.stringify(f.at));
    // the control: a target inside an OPEN callout landed before this fix and lands still
    const o = await clickInto('a[href="#open-heading"]', "#md-open-heading");
    assert.ok(o.at.inside && o.at.top !== null && o.at.top <= 12 && o.at.scrollTop > 0, "the open callout's heading lands: " + JSON.stringify(o.at));
    assert.equal(await page.evaluate(() => location.href), url0, "the page's location never changed");
    assert.equal(newPages(), 0, "no tab opened");
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});

test("a heading with math is given GitHub's slug of its text as written (the TeX, not KaTeX's glyphs), so the note's own `#` link and a `[[#Heading]]` wikilink to it are live and land; KaTeX still fills the heading", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, newPages } = await openNote(browser, filesBundle(), MATH_NOTE);
    const r = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const h1 = md.querySelector("h1") as HTMLElement;
      const link = (sel: string) => { const a = md.querySelector(sel) as HTMLElement | null; return a ? [a.getAttribute("class"), a.getAttribute("data-frag"), a.getAttribute("title")] : null; };
      return {
        h1Id: h1.id, h1Katex: h1.querySelectorAll(".katex").length, h1Placeholders: h1.querySelectorAll(".md-math-inline").length, h1Dollars: (h1.textContent || "").includes("$"),
        h2Id: (md.querySelector("h2") as HTMLElement).id,
        see: link('a[href="#ratio-fracab-and-energy-emc2"]'), wiki: link('a[href^="#Ratio"]'), deadWiki: md.querySelectorAll("span.fv-wikilink").length, plain: link('a[href="#plain-heading"]'),
      };
    });
    assert.equal(r.h1Id, "md-ratio-fracab-and-energy-emc2", "the slug reads the heading as the author wrote it: `$`, `\\`, `{`, `}`, `^` and `=` dropped, the letters kept in source order (GitHub's id for this heading)");
    assert.deepEqual([r.h1Katex, r.h1Placeholders, r.h1Dollars], [2, 0, false], "the fill still ran over the heading after the id was minted: two KaTeX roots, no placeholder, no `$` left as text");
    assert.equal(r.h2Id, "md-plain-heading");
    assert.deepEqual(r.see, ["fv-frag", "ratio-fracab-and-energy-emc2", "Go to ratio-fracab-and-energy-emc2"], "the note's own link to the heading is live");
    assert.deepEqual(r.wiki, ["fv-frag", "Ratio $\\frac{a}{b}$ and energy $E=mc^2$", "Go to Ratio $\\frac{a}{b}$ and energy $E=mc^2$"], "the wikilink spelling the heading's source text is live too (fragmentTarget slugs the fragment the same way)");
    assert.equal(r.deadWiki, 0, "no dead span");
    assert.deepEqual(r.plain, ["fv-frag", "plain-heading", "Go to plain-heading"]);
    // the click lands: from the bottom of the note, the h1 comes to the body's top edge
    await page.evaluate(() => { const b = document.querySelector("#romp-fileview .fileview-body") as HTMLElement; b.scrollTop = b.scrollHeight; });
    const before: Place = await page.evaluate(placeOf, "h1");
    assert.ok(!before.inside && before.scrollTop > 0, "the h1 is scrolled out of view first: " + JSON.stringify(before));
    await page.click('#romp-fileview .fileview-md a[href="#ratio-fracab-and-energy-emc2"]');
    await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
    const after: Place = await page.evaluate(placeOf, "h1");
    assert.ok(after.inside && after.top !== null && after.top <= 12, "the `#ratio-fracab-and-energy-emc2` click brings the heading to the body's top: " + JSON.stringify(after));
    assert.equal(newPages(), 0, "no tab opened");
    assert.deepEqual(errors, [], "no page errors");
    await page.context().close();
  });
});
