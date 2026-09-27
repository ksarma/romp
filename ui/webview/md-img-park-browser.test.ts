// The markdown-image heal (preview.ts installMdImgHeal) in headless Chromium over the real modules: the browser twin of
// md-img-park.test.ts, for the one question its stand-in cannot answer, which markup the heal leaves alone. It leaves the file
// viewer's own picture to the viewer, and the chat preview box's own imgs to the preview machinery, and knows each box by the
// data mark on it (VIEWER_PICTURE_MARK, set by file-view.ts imgBlock; PREVIEW_BOX_MARK, set by preview.ts previewFull), never
// by the box's class, which an author can type. Two surfaces render an author's markdown under
// the heal: a chat message (marked with the one grammar, then sanitizeMd and the chat's post-pass, as render.ts md() composes
// them, less the PR-reference walk) and a markdown file the viewer renders in the chat modal (real-viewer-leg.ts, with the
// heal and render.ts's romp:wsup line installed before the open). Each carries seven figures whose addresses answer 404 at
// first: for each box, one inside a wrapper wearing its class (fileview-imgbox, path-full), one wearing that class itself and
// one inside a wrapper carrying its data mark as an author wrote it, and a plain markdown figure. The sanitizer keeps the
// classes and strips the marks; every figure parks at its failure (no src, md-img-failed, the URL in data-md-src) and, once the
// addresses answer, heals on romp:wsup (the probes load and the picture lands on each img). With the heal's skip keyed on a
// class, the figures wearing it kept their src and the broken-image glyph and never healed. A third case builds the chat's own
// preview box (previewFull) in a message, a picture whose bytes do not decode: its swirl, whose address fails here, and the
// picture it shows from the fetched bytes listen to nothing, and the heal parks neither. That the viewer's own picture stays
// the viewer's is file-view-svg-reask-browser.test.ts's claim (the chat modal's probes per kernel message) and
// md-img-park.test.ts's. Waits are for the figures' own error and load events, never a timer. Skips LOUDLY without a
// playwright browser (CI's Test step runs before its Chromium install, so it skips there). Synthetic values only: /repo/notes-api paths, the placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { inBrowser, openViewer, requireCjs, UI, EXT, ROOT, REPORT, SID, type Served } from "./real-viewer-leg";

const SITE = "http://notes-api.test";
const FIGS = ROOT + "/docs/figs/";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><rect width="40" height="20" fill="#336699"/></svg>';
/** The kernel's /file answer for a figure: 404 until `served`, then the svg. */
let served = false;
const answer = (u: URL): Served | null => {
  if (u.pathname !== "/file" || !(u.searchParams.get("path") || "").startsWith(FIGS)) return null;
  return served ? { status: 200, type: "image/svg+xml", body: SVG } : { status: 404, type: "text/plain; charset=utf-8", body: "not found" };
};
/** A figure's /file address as a chat message spells it: the kernel's route for a path, with the sid. */
const fileAt = (leaf: string): string => "/file?path=" + encodeURIComponent(FIGS + leaf) + "&sid=" + SID;
/** The seven figures, as an author writes them, with the address maker of the surface. */
const figures = (src: (leaf: string) => string): string => [
  '<div class="fileview-imgbox"><img src="' + src("wrapped.svg") + '" alt="wrapped"></div>', "",
  '<img class="fileview-imgbox" src="' + src("classed.svg") + '" alt="classed">', "",
  '<div data-fv-picture=""><img src="' + src("marked.svg") + '" alt="marked"></div>', "",
  '<div class="path-full"><img src="' + src("pf-wrapped.svg") + '" alt="pf-wrapped"></div>', "",
  '<img class="path-full" src="' + src("pf-classed.svg") + '" alt="pf-classed">', "",
  '<div data-preview-full=""><img src="' + src("pf-marked.svg") + '" alt="pf-marked"></div>', "",
  "Plain: ![plain](" + src("plain.svg") + ") here.", "",
].join("\n");
const LEAVES = ["wrapped.svg", "classed.svg", "marked.svg", "pf-wrapped.svg", "pf-classed.svg", "pf-marked.svg", "plain.svg"];
const ALTS = ["wrapped", "classed", "marked", "pf-wrapped", "pf-classed", "pf-marked", "plain"];

/** The chat's renderer, minus the PR-reference walk: the singleton under md-config.ts, then sanitizeMd and the post-pass that
 *  parks a known-failed figure; with the heal and its two drivers, as the chat page has them. */
function chatBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { applyMdConfig } from "./md-config";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { installMdImgHeal, mdImgPostPass, retryFailedPreviews, refreshSettledPreviews, previewFull } from "./preview";',
    "applyMdConfig();",
    "(window as any).__preview = previewFull;",
    "(window as any).__md = (s: string) => { const clean = sanitizeMd(marked.parse(s) as string); mdImgPostPass(clean); return clean.innerHTML; };",
    "(window as any).__heal = () => { installMdImgHeal(); window.addEventListener(\"romp:wsup\", () => { retryFailedPreviews(); refreshSettledPreviews(); }); };",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
    stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "md-img-park-probe.ts" } });
  return r.outputFiles[0].text;
}

type Fig = { alt: string | null; src: string | null; parked: boolean; mdPath: string | null; complete: boolean; width: number };
/** Every figure under `root` (a selector) in order: its src attribute, whether it wears md-img-failed, the path its data-md-src
 *  names, and whether it decoded. */
const figs = (page: any, root: string): Promise<Fig[]> => page.evaluate((sel: string) => (Array.from(document.querySelectorAll(sel + " img")) as HTMLImageElement[]).map((i) => {
  const u = i.getAttribute("data-md-src");
  let mdPath: string | null = null;
  if (u) { try { mdPath = new URL(u).searchParams.get("path"); } catch { mdPath = u; } }
  return { alt: i.getAttribute("alt"), src: i.getAttribute("src"), parked: i.classList.contains("md-img-failed"), mdPath, complete: i.complete, width: i.naturalWidth };
}), root);
/** The markup that holds the figures: how many elements wear each box's class, and how many carry either box's data mark. */
const markup = (page: any, root: string): Promise<{ classed: number; pfClassed: number; marked: number }> => page.evaluate((sel: string) => ({
  classed: document.querySelectorAll(sel + " .fileview-imgbox").length, pfClassed: document.querySelectorAll(sel + " .path-full").length,
  marked: document.querySelectorAll(sel + " [data-fv-picture], " + sel + " [data-preview-full]").length,
}), root);
/** Count every error event an img of the page fires, from here on. */
const countErrors = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any; w.__imgErrors = 0;
  document.addEventListener("error", (e) => { const t = e.target as Element | null; if (t && t.nodeType === 1 && t.tagName === "IMG") w.__imgErrors++; }, true);
});

/** The claims on one surface: the markup as the sanitizer left it, the park at the failures, the heal once the addresses answer. */
async function parksAndHeals(page: any, root: string, where: string): Promise<void> {
  await page.waitForFunction((n: number) => (window as any).__imgErrors >= n, LEAVES.length, { timeout: 15000 });   // each figure's own failure
  assert.deepEqual(await markup(page, root), { classed: 2, pfClassed: 2, marked: 0 }, where + ": the sanitizer kept each box's class on the wrapper and on the img, and stripped the data marks an author wrote");
  const failed = await figs(page, root);
  assert.deepEqual(failed.map((f) => f.alt), ALTS, where + ": the seven figures, in order");
  assert.deepEqual(failed.map((f) => f.src), ALTS.map(() => null), where + ": every figure is parked, the four wearing a box's class among them: no src, so the browser fetches nothing and shows the alt text");
  assert.deepEqual(failed.map((f) => f.parked), ALTS.map(() => true), where + ": each wears md-img-failed");
  assert.deepEqual(failed.map((f) => f.mdPath), LEAVES.map((l) => FIGS + l), where + ": and keeps the /file address it asked for, for the heal");
  served = true;                                                   // the figures' addresses answer from here on
  await page.evaluate(() => { window.dispatchEvent(new Event("romp:wsup")); });
  await page.waitForFunction((sel: string) => { const imgs = Array.from(document.querySelectorAll(sel + " img")) as HTMLImageElement[]; return imgs.length > 0 && imgs.every((i) => i.complete && i.naturalWidth > 0); }, root, { timeout: 15000 });
  const healed = await figs(page, root);
  assert.deepEqual(healed.map((f) => f.parked), ALTS.map(() => false), where + ": after romp:wsup every figure healed: none parked");
  assert.deepEqual(healed.map((f) => f.width), ALTS.map(() => 40), where + ": and each shows its picture");
  assert.deepEqual(healed.map((f) => { try { return f.src === null ? null : new URL(f.src, "http://x").searchParams.get("path"); } catch { return f.src; } }), LEAVES.map((l) => FIGS + l), where + ": each at its own address");
}

test("in a browser, a chat message: figures an author wraps in markup wearing the file viewer's picture box class or the chat preview box's class, or wearing one themselves, park at their failure and heal when their addresses answer, as a plain markdown figure does; either box's data mark an author writes is stripped by the sanitizer, and that figure parks and heals too", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    served = false;
    const page = await browser.newPage();
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route((u: URL) => u.href.startsWith(SITE), (route: any) => {
      const a = answer(new URL(route.request().url()));
      return a ? route.fulfill({ status: a.status, contentType: a.type, body: a.body ?? "" }) : route.fulfill({ status: 200, contentType: "text/html", body: "<!DOCTYPE html><html><head><meta charset=utf-8></head><body></body></html>" });
    });
    await page.goto(SITE + "/");
    await page.evaluate(chatBundle());                             // the renderer and the heal, run in the page
    await countErrors(page);
    await page.evaluate((m: string) => {
      const w = window as any;
      w.__heal();                                                  // render.ts installs the heal once at load, and its romp:wsup line
      const msg = document.createElement("div"); msg.className = "md"; msg.id = "msg";
      msg.innerHTML = w.__md(m);                                   // render.ts sets md()'s string into the message body
      document.body.appendChild(msg);
    }, figures(fileAt));
    await parksAndHeals(page, "#msg", "a chat message");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, the chat modal: a markdown file the viewer renders, with figures an author wraps in markup wearing the picture box's class or the chat preview box's class, or wearing one themselves, and one inside each box's data mark as the author wrote it (stripped): each parks at its failure under the page's heal and heals when the addresses answer, as the plain markdown figure does", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    served = false;
    const before = async (page: any): Promise<void> => {
      await countErrors(page);
      await page.evaluate(() => {
        const w = window as any;
        w.FV.installMdImgHeal();                                   // render.ts installs it once at load
        window.addEventListener("romp:wsup", () => { w.FV.retryFailedPreviews(); w.FV.refreshSettledPreviews(); });   // render.ts's romp:wsup line, less the path-image heal
      });
    };
    const note = "# Report\n\n" + figures((leaf) => "figs/" + leaf);   // relative, as a note writes them: the viewer asks /file for each
    const { page, errors } = await openViewer(browser, "chat", 900, 700, { docs: { [REPORT]: note }, serve: answer, before });
    await parksAndHeals(page, ".fileview-md", "a rendered markdown file");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});

test("in a browser, a chat message: the chat's own preview box (previewFull) keeps its imgs from the heal, since the heal knows the box by its data mark: its swirl, whose address fails here, and the picture it shows from the fetched bytes of a figure that does not decode listen to nothing, and each keeps its src and is never parked", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const BAD = FIGS + "bad.png";
    const page = await browser.newPage();
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route((u: URL) => u.href.startsWith(SITE), (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/file" && u.searchParams.get("path") === BAD) return route.fulfill({ status: 200, contentType: "image/png", body: "not a png" });   // bytes that do not decode
      return route.fulfill({ status: 200, contentType: "text/html", body: "<!DOCTYPE html><html><head><meta charset=utf-8></head><body></body></html>" });   // the swirl's address included: no picture there
    });
    await page.goto(SITE + "/");
    await page.evaluate(chatBundle());
    await page.evaluate(([bad, sid]: [string, string]) => {
      const w = window as any;
      w.__heal();
      // every img error, read after the heal's listener has run (a capture listener added after it on the same node)
      w.__seen = [];
      document.addEventListener("error", (e) => {
        const i = e.target as HTMLImageElement | null;
        if (!i || i.nodeType !== 1 || i.tagName !== "IMG") return;
        const src = i.getAttribute("src");
        w.__seen.push({ cls: i.className, src, was: src ?? i.getAttribute("data-md-src"), parked: i.classList.contains("md-img-failed"), inBox: !!i.closest(".path-full") });   // the message holds the preview box alone; `was`: the address the img failed at, a parked one's included
      }, true);
      const msg = document.createElement("div"); msg.className = "md"; msg.id = "msg";
      document.body.appendChild(msg);
      const box = w.__preview(bad, sid, true);                   // a mention the kernel verified: its failure stays visible and retries
      msg.appendChild(box);
    }, [BAD, SID]);
    type Seen = { cls: string; src: string | null; was: string | null; parked: boolean; inBox: boolean };
    const seen = (): Promise<Seen[]> => page.evaluate(() => (window as any).__seen);
    // the first attempt's picture fails (the machinery listens to it); its swirl fails too, at an address that serves no picture here
    await page.waitForFunction(() => { const s = (window as any).__seen as Seen[]; return s.some((x) => x.cls.includes("path-full-img")) && s.some((x) => x.cls.includes("path-load-spin")); }, null, { timeout: 15000 });
    await page.evaluate(() => { window.dispatchEvent(new Event("romp:wsup")); });   // the retry: the managed fetch lands the bytes, shown from an object URL
    await page.waitForFunction(() => ((window as any).__seen as Seen[]).some((x) => (x.was || "").startsWith("blob:")), null, { timeout: 15000 });
    const all = await seen();
    assert.ok(all.length >= 3 && all.every((x) => x.inBox), "every error came from the preview box's imgs: " + JSON.stringify(all));
    assert.ok(all.some((x) => x.cls.includes("path-load-spin")) && all.some((x) => (x.was || "").startsWith("blob:")), "among them the swirl and the picture shown from the fetched bytes");
    assert.deepEqual(all.filter((x) => x.parked || x.src === null), [], "none is parked and each keeps its src: the heal leaves the preview box's imgs to its machinery");
    assert.equal(await page.evaluate(() => document.querySelectorAll("#msg .md-img-failed").length), 0, "and nothing in the message wears md-img-failed");
    assert.deepEqual(errors, [], "no page errors");
    await page.close();
  });
});
