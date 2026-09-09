// A URL document's figures resolve against the DOCUMENT through every attribute a figure fetches through, over the REAL
// Files bundle in headless Chromium (file-view.ts resolveFigureRefs, the URL kind's arm of mdBlock; figure-gate.ts
// figureRefs names the attributes). The arm resolved `img[src]` alone: a relative `srcset` candidate, a video's `src` and
// `poster`, an audio's `src`, a `source`'s `src` or `srcset` and a track's `src` stayed as written, and the browser
// resolved each against the PAGE, so a document at /notes/note.md had its clip and poster fetched from the dashboard's
// root, where nothing is (the Slice 4 review, round 2; rewriteFigureSrcs had closed the same gap for a file on disk in
// this slice). The leg opens a URL document holding every shape from a page at another path, reads each attribute as
// written into the DOM and as the browser resolved it, and reads the page's own request log: every fetch for the
// document's media goes under the document's directory, none to the page's, an absolute figure on an unlisted host is
// gated as before and a data: URL stands as written. Skips LOUDLY without a playwright browser (CI installs none), as the
// other browser legs do. Synthetic values only: an invented note, .test hosts.
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

const PAGE = "http://romp.test/files";
const DOC_DIR = "http://romp.test/notes/";
const URL_DOC = DOC_DIR + "note.md";
const DATA_GIF = "data:image/gif;base64,R0lGODlhAQABAAAAACw=";
// one figure per fetching attribute, each relative to the document; then an absolute one on an unlisted host and a data: one
const NOTE = [
  "# Note", "",
  '<p><img class="fx-img" src="rel.png" alt="i"></p>', "",
  '<p><img class="fx-srcset" src="rel2.png" srcset="rel-1x.png 1x, rel-2x.png 2x" alt="s"></p>', "",
  '<video class="fx-video" src="clip.mp4" poster="poster.png" width="160" height="90"></video>', "",
  '<audio class="fx-audio" src="a.mp3"></audio>', "",
  '<video class="fx-vsrc" width="160" height="90"><source class="fx-source" src="s.mp4" type="video/mp4"><track class="fx-track" src="t.vtt" kind="subtitles" srclang="en" default></video>', "",
  '<picture class="fx-picture"><source class="fx-picsrc" srcset="pic.png 1x"><img class="fx-picimg" src="pic-fb.png" alt="p"></picture>', "",
  '<p><svg class="fx-svg" width="20" height="20"><image class="fx-svgimg" xlink:href="vec.png" width="20" height="20"/></svg></p>', "",
  '<p><img class="fx-abs" src="https://cdn.test/abs.png" alt="a" width="20" height="20"></p>', "",
  '<p><img class="fx-data" src="' + DATA_GIF + '" alt="d"></p>', "",
  "End.", "",
].join("\n");
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the URL viewer, which the pane's page does not otherwise reach. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { openUrlView } from "./file-view";\n(window as any).__rompProbe = { openUrlView };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
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

/** Each figure's attributes as written into the DOM by the viewer, and what the browser resolved them to. */
function readFigures() {
  const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
  const q = (s: string) => md.querySelector(s) as any;
  const gated = (e: Element) => e.closest(".fv-gate") !== null;
  const img = q("img.fx-img"), ss = q("img.fx-srcset"), video = q("video.fx-video"), audio = q("audio.fx-audio");
  const source = q("source.fx-source"), track = q("track.fx-track"), picsrc = q("source.fx-picsrc"), picimg = q("img.fx-picimg");
  const svgimg = q(".fx-svgimg"), abs = q("img.fx-abs"), data = q("img.fx-data");
  const cands = (s: string | null) => (s || "").split(",").map((c) => c.trim().split(/\s+/)).map(([u, d]) => [u, d || ""]);
  return {
    img: { attr: img.getAttribute("src"), resolved: img.currentSrc || img.src, gated: gated(img) },
    srcset: { src: ss.getAttribute("src"), cands: cands(ss.getAttribute("srcset")), resolved: ss.currentSrc, gated: gated(ss) },
    video: { src: video.getAttribute("src"), poster: video.getAttribute("poster"), resolvedSrc: video.currentSrc || video.src, resolvedPoster: video.poster, gated: gated(video) },
    audio: { src: audio.getAttribute("src"), resolvedSrc: audio.currentSrc || audio.src, gated: gated(audio) },
    source: { src: source.getAttribute("src"), resolvedSrc: source.src },
    track: { src: track.getAttribute("src"), resolvedSrc: track.src },
    picture: { cands: cands(picsrc.getAttribute("srcset")), img: picimg.getAttribute("src"), resolved: picimg.currentSrc, gated: gated(picimg) },
    svgimg: { href: svgimg.getAttribute("href"), xlink: svgimg.getAttributeNS("http://www.w3.org/1999/xlink", "href"), gated: gated(svgimg) },
    abs: { src: abs.getAttribute("src"), gatedSrc: abs.getAttribute("data-fv-gated-src"), gated: gated(abs), host: abs.closest(".fv-gate")?.getAttribute("data-fv-host") || null },
    data: { src: data.getAttribute("src"), gated: gated(data) },
    dataFvSrc: md.querySelectorAll("[data-fv-src]").length,
  };
}

test("URL viewer: every figure attribute of a document at /notes/ resolves under /notes/, and the browser fetches from there; an absolute figure is gated as before, a data: URL stands", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const js = filesBundle();
    const ctx = await browser.newContext({ viewport: { width: 900, height: 900 } });
    const page = await ctx.newPage();
    const errors: string[] = [];
    const requests: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { requests.push(r.url()); });
    await ctx.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.host !== "romp.test") return route.fulfill({ status: 200, contentType: "image/png", body: PNG });   // any other host: a picture, and the log has it
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (route.request().url() === URL_DOC) return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: NOTE });
      if (u.pathname.endsWith(".png")) return route.fulfill({ status: 200, contentType: "image/png", body: PNG });   // wherever it was asked for: the log says where
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto(PAGE);
    // the fetches the paint will make, awaited below: armed before the open, since a waiter armed after the paint misses a request already made
    const fetched = ["rel.png", "rel-1x.png", "poster.png", "vec.png"].map((name) => page.waitForRequest(DOC_DIR + name, { timeout: 15000 }));
    await page.evaluate((u: string) => { (window as any).__rompProbe.openUrlView(u); }, URL_DOC);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
    await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
    const f = await page.evaluate(readFigures);

    // the attributes, as the viewer wrote them: every relative reference is the document's, in every attribute
    assert.deepEqual(f.img, { attr: DOC_DIR + "rel.png", resolved: DOC_DIR + "rel.png", gated: false }, JSON.stringify(f.img));
    assert.deepEqual(f.srcset.cands, [[DOC_DIR + "rel-1x.png", "1x"], [DOC_DIR + "rel-2x.png", "2x"]], "each srcset candidate resolved, its descriptor kept: " + JSON.stringify(f.srcset));
    assert.deepEqual([f.srcset.src, f.srcset.resolved, f.srcset.gated], [DOC_DIR + "rel2.png", DOC_DIR + "rel-1x.png", false], "at DPR 1 the browser picked the 1x candidate, under the document: " + JSON.stringify(f.srcset));
    assert.deepEqual(f.video, { src: DOC_DIR + "clip.mp4", poster: DOC_DIR + "poster.png", resolvedSrc: DOC_DIR + "clip.mp4", resolvedPoster: DOC_DIR + "poster.png", gated: false }, JSON.stringify(f.video));
    assert.deepEqual(f.audio, { src: DOC_DIR + "a.mp3", resolvedSrc: DOC_DIR + "a.mp3", gated: false }, JSON.stringify(f.audio));
    assert.deepEqual(f.source, { src: DOC_DIR + "s.mp4", resolvedSrc: DOC_DIR + "s.mp4" }, JSON.stringify(f.source));
    assert.deepEqual(f.track, { src: DOC_DIR + "t.vtt", resolvedSrc: DOC_DIR + "t.vtt" }, JSON.stringify(f.track));
    assert.deepEqual([f.picture.cands, f.picture.img, f.picture.gated], [[[DOC_DIR + "pic.png", "1x"]], DOC_DIR + "pic-fb.png", false], JSON.stringify(f.picture));
    assert.ok(f.picture.resolved === DOC_DIR + "pic.png" || f.picture.resolved === DOC_DIR + "pic-fb.png", "the picture shows the source's or the fallback's file, either under the document: " + f.picture.resolved);
    assert.deepEqual(f.svgimg, { href: DOC_DIR + "vec.png", xlink: null, gated: false }, "the svg image's xlink:href is folded into a resolved href: " + JSON.stringify(f.svgimg));
    // an absolute figure on an unlisted host is untouched by the resolution and gated as before (decision 8); a data: URL stands as written
    assert.deepEqual(f.abs, { src: null, gatedSrc: "https://cdn.test/abs.png", gated: true, host: "cdn.test" }, JSON.stringify(f.abs));
    assert.deepEqual(f.data, { src: DATA_GIF, gated: false }, JSON.stringify(f.data));
    assert.equal(f.dataFvSrc, 0, "no data-fv-src stamp in a URL document (the comments panel's pairing key; there is no panel here)");

    // the fetches: the pictures the browser asked for came from under the document, and nothing was asked of the page's directory
    await Promise.all(fetched);
    const media = requests.filter((u) => u.startsWith("http://romp.test/") && !u.startsWith("http://romp.test/media/") && ![PAGE, "http://romp.test/dist/files.js", URL_DOC].includes(u));   // the page's own font and glyph aside
    assert.ok(media.length >= 4, "the document's media were requested: " + JSON.stringify(media));
    assert.deepEqual(media.filter((u) => !u.startsWith(DOC_DIR)), [], "no request for a figure went to the page's directory: " + JSON.stringify(media));
    assert.deepEqual(requests.filter((u) => !u.startsWith("http://romp.test/")), [], "nothing left the page: the absolute figure on cdn.test is gated");
    assert.deepEqual(errors, [], "no page errors");
    await ctx.close();
  });
});
