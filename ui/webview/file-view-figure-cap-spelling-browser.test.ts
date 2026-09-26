// A figure a note writes with its scheme, naming this origin's /file route, keeps the spelling its author wrote under a page
// key, in headless Chromium over the REAL viewer (real-viewer-leg.ts). The viewer's rewrite (rewriteFigureSrcs) leaves a URL
// with a scheme as written, and the cap pass after it (capAuthoredFileUrls, authored-file-caps.ts) adds this page's cap to one
// that names this origin's /file route. So mdBlock keeps the authored spelling just before that pass (keepAuthoredSpellings):
// the img's `src` in `data-fv-src`, and a srcset in `data-fv-srcset` unless the rewrite already stamped one. The comments panel
// pairs a picture with its embed by that spelling (file-comments.ts pictureDest, embedFor, imgForRange), and a figure that
// fails to load names it in its label (armFigureLabels). Without the stamp the capped URL stood in the img's `src` as its only
// spelling: the picture paired with no embed, no embed's range found the picture, and the label named the capped URL.
// The pairing functions run from a second bundle of file-comments.ts (they read the DOM and the note's text, and keep no state).
// Scenes: under a page key, the scheme figure (missing on disk, so it fails) keeps its spelling, pairs both ways and names it in
// its label, while its src carries the cap and stays absolute; a relative figure pairs as before, and one whose src the cap pass
// writes back in its own query form keeps the spelling the rewrite stamped; a srcset of scheme URLs gets its authored
// candidates stamped; a srcset mixing a path candidate and a scheme candidate keeps the rewrite's stamp, the author's spelling
// of both. With no page key nothing is capped and nothing is stamped, and the scheme figure pairs by its src.
// Skips LOUDLY without a playwright browser (CI installs none), as the other legs do. Synthetic values only: the notes-api
// world, /repo/notes-api paths, the placeholder sid, a page key minted at run time.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { randomBytes } from "node:crypto";
import { inBrowser, openViewer, frames, requireCjs, EXT, UI, ORIGIN, ROOT, REPORT, SID, type Served } from "./real-viewer-leg";

const FIGS = ROOT + "/docs/figs/";
/** Every figure's bytes: a small vector picture under its own type (the figures' names end in .png; nothing here reads the suffix). */
const PICTURE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20" width="40" height="20"><rect width="40" height="20" fill="#888"/></svg>';
const at = (p: string): string => ORIGIN + "/file?path=" + encodeURIComponent(p) + "&sid=" + SID;
const SCHEME = at(FIGS + "missing.png");
const SET_A = at(FIGS + "c.png"), SET_B = at(FIGS + "c2.png"), MIXED_B = at(FIGS + "f.png");
const SCHEME_SET = SET_A + " 1x, " + SET_B + " 2x";
const MIXED_SET = "figs/e.png 1x, " + MIXED_B + " 2x";
const attr = (s: string): string => s.replace(/&/g, "&amp;");
/** The note: a scheme figure whose file is missing, a relative figure that loads, a relative figure whose name holds a space and
 *  parentheses, a srcset of scheme URLs and a mixed srcset. */
const NOTE = "# Report\n\nThe scheme figure: ![scheme figure](" + SCHEME + ") above the week.\n\n"
  + "The relative figure: ![relative figure](figs/b.png) loads.\n\n"
  + "The spaced figure: ![spaced figure](<figs/two words (1).png>) loads.\n\n"
  + '<img alt="scheme srcset" srcset="' + attr(SCHEME_SET) + '">\n\n'
  + '<img alt="mixed srcset" srcset="' + attr(MIXED_SET) + '">\n';
/** The kernel's /file answers, as the browser asks for them: the missing figure's 404, the picture for every other figure. */
const serve = (u: URL): Served | null => {
  if (u.pathname !== "/file") return null;
  const p = u.searchParams.get("path") || "";
  if (p === FIGS + "missing.png") return { status: 404, type: "text/plain; charset=utf-8", body: "not found: " + p };
  return { status: 200, type: "image/svg+xml", body: PICTURE };
};

let fcBundle: string | null = null;
/** file-comments.ts's pairing functions as window.FC, bundled as the webview build bundles the module (in memory). */
function pairingBundle(): string {
  if (fcBundle) return fcBundle;
  const r = requireCjs("esbuild").buildSync({
    stdin: { contents: 'export { embedFor, imgForRange, imageEmbeds, pictureDest } from "./file-comments";', resolveDir: UI, loader: "ts", sourcefile: "pairing-probe.ts" },
    bundle: true, write: false, format: "iife", globalName: "FC", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  fcBundle = r.outputFiles[0].text as string;
  return fcBundle;
}

type Fig = { alt: string; src: string | null; kept: string | null; keptSet: string | null; srcset: string | null; embed: string | null; byRange: boolean; label: string | null };
/** Every figure of the Rendered box by its alt: its src, the kept spellings, the embed the panel pairs it with and whether that
 *  embed's range finds this picture again, and the failure label after it. */
const read = (page: any): Promise<Record<string, Fig>> => page.evaluate(([note, file]: [string, string]) => {
  const w = window as any;
  const md = document.querySelector(".fileview-md") as HTMLElement;
  const out: Record<string, Fig> = {};
  for (const img of Array.from(md.querySelectorAll("img")) as HTMLImageElement[]) {
    const e = w.FC.embedFor(img, md, note, file);
    const n = img.nextSibling as Element | null;
    const lab = n && n.nodeType === 1 && n.hasAttribute("data-fv-figerr") ? n.textContent : null;
    out[img.getAttribute("alt") || ""] = { alt: img.getAttribute("alt") || "", src: img.getAttribute("src"), kept: img.getAttribute("data-fv-src"),
      keptSet: img.getAttribute("data-fv-srcset"), srcset: img.getAttribute("srcset"), embed: e ? e.dest : null,
      byRange: !!e && w.FC.imgForRange(md, note, { start: e.start, end: e.end }, file) === img, label: lab };
  }
  return out;
}, [NOTE, REPORT]);

async function scene(browser: any, key: string | null): Promise<{ figs: Record<string, Fig>; errors: string[] }> {
  const { page, errors } = await openViewer(browser, "pane", 1100, 800, {
    docs: { [REPORT]: NOTE }, serve,
    before: async (pg: any) => {
      if (key) await pg.evaluate((k: string) => { (window as any).__rompPageKey = () => k; }, key);   // as the kernel's page-key script installs it
      await pg.addScriptTag({ content: pairingBundle() });
    },
  });
  await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete), null, { timeout: 10000 });
  await frames(page, 2);
  const figs = await read(page);
  await page.close();
  return { figs, errors };
}

test("a figure written with its scheme keeps its authored spelling under a page key: it pairs with its embed both ways and its failure label names it, while its src carries the cap", async (t) => {
  await inBrowser(t, async (browser) => {
    const key = randomBytes(32).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    const { figs, errors } = await scene(browser, key);
    const s = figs["scheme figure"];
    assert.ok(s, "the viewer rendered the scheme figure: " + JSON.stringify(Object.keys(figs)));
    assert.ok(s.src !== null && s.src.startsWith(ORIGIN + "/file?") && /[?&]cap=/.test(s.src), "the cap pass ran: the src carries this page's cap and stays absolute: " + s.src);
    assert.equal(s.kept, SCHEME, "the authored spelling is kept in data-fv-src, where the comments panel reads it");
    assert.equal(s.embed, SCHEME, "the picture pairs with its embed (embedFor)");
    assert.ok(s.byRange, "and the embed's range finds the picture again (imgForRange)");
    assert.ok(s.label !== null && s.label.includes(SCHEME) && !/cap=/.test(s.label), "the failure label names the authored source, not the capped URL: " + s.label);
    const r = figs["relative figure"];
    assert.equal(r.kept, "figs/b.png", "a relative figure keeps its spelling from the rewrite, as before");
    assert.ok(r.embed === "figs/b.png" && r.byRange, "and pairs both ways: " + JSON.stringify(r));
    // the cap pass writes a query back in its own form (a space as `+`, a parenthesis escaped), so it changes the src the rewrite
    // built for this figure; the spelling the rewrite kept must stand, not the src the rewrite built
    const sp = figs["spaced figure"];
    assert.ok(sp.src !== null && /[?&]cap=/.test(sp.src) && /\+|%28/.test(sp.src), "the cap pass rewrote this figure's src (the precondition of the next check): " + sp.src);
    assert.ok(sp.kept !== null && !sp.kept.includes("/file?") && sp.kept.includes("two"), "the rewrite's data-fv-src stands, the author's spelling: " + sp.kept);
    assert.ok(sp.embed !== null && sp.byRange, "and the figure pairs both ways: " + JSON.stringify(sp));
    const a = figs["scheme srcset"];
    assert.ok(a.srcset !== null && /[?&]cap=/.test(a.srcset), "the cap pass capped the srcset of scheme URLs: " + a.srcset);
    assert.equal(a.keptSet, SCHEME_SET, "and its authored candidates are kept in data-fv-srcset");
    assert.equal(a.kept, null, "a srcset keeps no data-fv-src (an img's src alone does)");
    const m = figs["mixed srcset"];
    assert.ok(m.srcset !== null && m.srcset.split(",").every((c) => /[?&]cap=/.test(c)), "the mixed srcset's two candidates are capped, the path one by the rewrite and the scheme one by the cap pass: " + m.srcset);
    assert.equal(m.keptSet, MIXED_SET, "the rewrite's stamp stands: the author's spelling of both candidates, not the rewritten path candidate");
    assert.deepEqual(errors, [], "no page errors");
  });
});

test("with no page key nothing is capped and nothing is stamped, and a figure written with its scheme pairs by its src", async (t) => {
  await inBrowser(t, async (browser) => {
    const { figs, errors } = await scene(browser, null);
    const s = figs["scheme figure"];
    assert.equal(s.src, SCHEME, "no key: the src stays as written");
    assert.equal(s.kept, null, "and nothing is stamped: data-fv-src means this viewer changed the src");
    assert.ok(s.embed === SCHEME && s.byRange, "the picture pairs by its src: " + JSON.stringify(s));
    assert.equal(figs["scheme srcset"].keptSet, null, "a srcset the cap pass leaves alone gets no data-fv-srcset");
    assert.equal(figs["scheme srcset"].srcset, SCHEME_SET, "and stays as written");
    assert.deepEqual(errors, [], "no page errors");
  });
});
