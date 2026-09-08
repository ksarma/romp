// A note's links in the rendered file view, over the REAL files bundle in headless Chromium (plans/markdown-viewer.md,
// Slice 1: sanitize as GitHub does; the 2026-09-07 review). The sanitizer's svg profile keeps an inline SVG <a> (spelled
// `href` or `xlink:href`), and its html profile kept an image map's <area> until the slice forbade map, area and usemap
// (md-sanitize.ts: a prefixed map name can never bind, and GitHub drops image maps). mdBlock stamped target=_blank on
// `a[href]` only, and wrote it as a property, which an SVGAElement drops, so a click on an <area href> or an SVG anchor
// replaced the Files document with the URL, in the same frame: the defect class the slice closes for <form>. The leg
// clicks each shape as a person would and checks the document stays: an absolute link of every surviving shape opens a
// new tab and location.href is unchanged; the picture whose map was dropped is inert; an SVG anchor's `#fragment`
// scrolls to its heading; an SVG anchor's relative `sibling.md` opens the sibling in this viewer, through the same path
// link a relative <a> becomes (file-view-links.ts linkMarkdownAnchors walks every `a`, the SVG one included). Skips
// LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an
// invented note, TESTHOST paths, a placeholder sid, example.invalid URLs.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const DIR = "/tmp/TESTHOST/notes-api/";
const PATH = DIR + "report.md";
const SIBLING = DIR + "sibling.md";
const XLINK = "http://www.w3.org/1999/xlink";
// a valid 1x1 transparent PNG: a picture that decodes, so a map that DID survive would be live (a broken image shows its
// alt text and binds no map, which would pass the image case for the wrong reason; the precondition below checks it decoded)
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";

// each shape in its own <p> HTML block (marked passes a block opened by <p> through verbatim); the image map is spelled
// as an author spells it, the bare `usemap="#m"` against `<map name="m">`
const NOTE = [
  "# Figure",
  "",
  '<p>A <a href="https://example.invalid/ctl" class="fx-a">plain link</a> in prose.</p>',
  "",
  `<p><img src="${PNG}" width="240" height="40" usemap="#m" alt="map" class="fx-img"><map name="m"><area shape="rect" coords="0,0,240,40" href="https://example.invalid/area" alt="go"></map></p>`,
  "",
  '<p><svg width="240" height="40" class="fx-svg-href"><a href="https://example.invalid/svg"><text x="4" y="30" font-size="24">svg href</text></a></svg></p>',
  "",
  `<p><svg width="240" height="40" class="fx-svg-xlink" xmlns:xlink="${XLINK}"><a xlink:href="https://example.invalid/xlink"><text x="4" y="30" font-size="24">svg xlink</text></a></svg></p>`,
  "",
  `<p><svg width="240" height="40" class="fx-svg-frag" xmlns:xlink="${XLINK}"><a xlink:href="#tail"><text x="4" y="30" font-size="24">to the tail</text></a></svg></p>`,
  "",
  '<p><svg width="240" height="40" class="fx-svg-rel"><a href="sibling.md"><text x="4" y="30" font-size="24">to the sibling</text></a></svg></p>',
  "",
  ...Array.from({ length: 60 }, (_, i) => "Paragraph " + (i + 1) + " of the tail, so the fragment link has somewhere to go.\n"),
  "",
  "## Tail",
  "",
  // enough below the heading that it can reach the top of the body (a heading at the very end stops short of it)
  ...Array.from({ length: 40 }, (_, i) => "Tail paragraph " + (i + 1) + ".\n"),
  "",
  "The end.",
  "",
].join("\n");
const SIBLING_NOTE = "# Sibling\n\nOpened in the viewer.\n";

function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the Files page as the kernel serves it (_files_page): the chat's styles.css for the viewer's dress, files-pane.css
// after it for the pane layout, a fake acquireVsCodeApi (the shim's role), then the files bundle
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Watch = { errors: string[]; navs: string[]; popups: string[]; fileRequests: string[] };

async function inBrowser(t: any, body: (page: any, w: Watch) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box: the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const w: Watch = { errors: [], navs: [], popups: [], fileRequests: [] };
  try {
    const filesJs = bundle("files.ts");
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { w.errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) w.navs.push(f.url()); });
    page.context().on("page", (p: any) => { w.popups.push(p.url()); });
    // the whole context, so a new tab's request is answered from memory too and nothing reaches the network; a host other
    // than the dashboard's answers with a marker page, so a same-frame navigation (the defect) is unmistakable in the body
    await page.context().route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname !== "romp.test") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: "EXTERNAL " + u.href });
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/file") {
        const p = u.searchParams.get("path") || "";
        w.fileRequests.push(p);
        const text = p === PATH ? NOTE : p === SIBLING ? SIBLING_NOTE : null;
        if (text !== null) return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: text });
      }
      return route.fulfill({ status: 404, contentType: "text/html; charset=utf-8", body: "NOTFOUND " + u.href });
    });
    await page.goto("http://romp.test/files");
    await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 10000 });
    await body(page, w);
  } finally {
    await browser.close();
  }
}

/** Scroll `sel` (inside the rendered note) into view and click its centre with the mouse, as a person would. */
async function clickOn(page: any, sel: string): Promise<void> {
  const box = await page.evaluate((s: string) => {
    const e = document.querySelector("#romp-fileview .fileview-md " + s);
    if (!e) return null;
    e.scrollIntoView({ block: "center" });
    const r = e.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height };
  }, sel);
  assert.ok(box && box.w > 0 && box.h > 0, sel + " is laid out in the note: " + JSON.stringify(box));
  await page.mouse.click(box.x, box.y);
  await page.waitForTimeout(500);
}

test("every link shape in a note keeps the Files document: a new tab for an absolute href, a scroll for a fragment, the viewer for a sibling; an image map is dropped and its picture is inert", { timeout: 90000 }, async (t) => {
  await inBrowser(t, async (page, w) => {
    const START = page.url();
    // the image decoded: a map that survived WOULD be live, so the inert click below is the sanitizer's doing, not a broken image's
    await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview .fileview-md img")).every((i) => (i as HTMLImageElement).complete), null, { timeout: 5000 });

    // 1. an absolute href of every surviving shape: a click opens a new tab and the Files document stays where it was
    for (const c of [
      { name: "the HTML anchor (control)", sel: ".fx-a" },
      { name: "the SVG anchor with href", sel: ".fx-svg-href text" },
      { name: "the SVG anchor with xlink:href", sel: ".fx-svg-xlink text" },
    ]) {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      await clickOn(page, c.sel);
      assert.equal(page.url(), START, c.name + ": location.href is unchanged after the click");
      assert.deepEqual(w.navs.slice(navs0), [], c.name + ": no main-frame navigation");
      assert.equal(w.popups.length - popups0, 1, c.name + ": the link opened in exactly one new tab");
      assert.ok(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-md")), c.name + ": the note is still on screen");
    }
    // ...and the picture whose image map the sanitizer dropped: a click on it opens nothing and moves nothing
    {
      const popups0 = w.popups.length, navs0 = w.navs.length;
      await clickOn(page, ".fx-img");
      assert.equal(page.url(), START, "the mapped picture: location.href is unchanged after the click");
      assert.deepEqual(w.navs.slice(navs0), [], "the mapped picture: no main-frame navigation");
      assert.equal(w.popups.length, popups0, "the mapped picture: no new tab, the map is gone");
    }

    // 2. the SVG anchor's #fragment lands on its heading in this body: no tab, no navigation, a scroll
    const popups1 = w.popups.length, navs1 = w.navs.length;
    await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-body") as HTMLElement).scrollTop = 0; });
    await clickOn(page, ".fx-svg-frag text");
    const landed = await page.evaluate(() => {
      const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
      const tail = document.querySelector("#romp-fileview .fileview-md h2#md-tail") as HTMLElement;
      return { scrollTop: body.scrollTop, tailTop: tail.getBoundingClientRect().top - body.getBoundingClientRect().top, bodyHeight: body.clientHeight };
    });
    assert.equal(page.url(), START, "fragment: location.href is unchanged");
    assert.deepEqual(w.navs.slice(navs1), [], "fragment: no main-frame navigation");
    assert.equal(w.popups.length, popups1, "fragment: no new tab");
    assert.ok(landed.scrollTop > 0 && landed.tailTop >= -2 && landed.tailTop < 48, "the Tail heading is at the top of the body after the click: " + JSON.stringify(landed));

    // 3. what the sanitizer and mdBlock left (the stamps behind 1 and 2; read before 4 replaces the note)
    const facts = await page.evaluate((XL: string) => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const links = Array.from(md.querySelectorAll("a, area")).map((n) => {
        const a = n as HTMLElement | SVGElement;
        return { tag: a.tagName.toLowerCase(), ns: a.namespaceURI, href: a.getAttribute("href"), xlink: a.getAttributeNS(XL, "href"),
                 target: a.getAttribute("target"), rel: a.getAttribute("rel"), act: a.dataset.act ?? null, path: a.dataset.path ?? null, frag: a.dataset.frag ?? null,
                 cls: a.getAttribute("class") || "", title: a.getAttribute("title") };
      });
      const imgs = Array.from(md.querySelectorAll("img")).map((i) => ({ usemap: i.getAttribute("usemap"), decoded: i.complete && i.naturalWidth > 0 }));
      return { links, imgs, maps: md.querySelectorAll("map").length, areas: md.querySelectorAll("area").length };
    }, XLINK);
    const SVG = "http://www.w3.org/2000/svg", HTML = "http://www.w3.org/1999/xhtml";
    assert.deepEqual(facts.imgs, [{ usemap: null, decoded: true }], "the picture decoded, and its usemap is gone (FORBID_ATTR)");
    assert.equal(facts.maps + facts.areas, 0, "no <map> and no <area> survive the sanitizer (FORBID_TAGS): an image map is dropped as GitHub drops it");
    assert.equal(facts.links.length, 5, "five links in the note, every one an anchor: " + JSON.stringify(facts.links));
    const [ctl, svgHref, svgXlink, svgFrag, svgRel] = facts.links;
    assert.deepEqual([ctl.tag, ctl.ns, ctl.target, ctl.rel], ["a", HTML, "_blank", "noopener"], "control: the HTML anchor, as before");
    assert.deepEqual([svgHref.tag, svgHref.ns, svgHref.target, svgHref.rel], ["a", SVG, "_blank", "noopener"], "an SVG <a href> carries the target ATTRIBUTE (the property write was dropped)");
    assert.deepEqual([svgXlink.tag, svgXlink.ns, svgXlink.href, svgXlink.xlink, svgXlink.target, svgXlink.rel],
      ["a", SVG, "https://example.invalid/xlink", "https://example.invalid/xlink", "_blank", "noopener"], "an SVG <a xlink:href> gets a plain href copy, and the stamps");
    assert.deepEqual([svgFrag.tag, svgFrag.href, svgFrag.frag, /\bfv-frag\b/.test(svgFrag.cls), /\bfv-dead\b/.test(svgFrag.cls), svgFrag.target], ["a", "#tail", "tail", true, false, null],
      "an SVG fragment link is a section link of this document (file-view-links.ts): live, no tab");
    assert.deepEqual([svgRel.tag, svgRel.href, svgRel.act, svgRel.path, /\bfile-uri-link\b/.test(svgRel.cls), svgRel.title, svgRel.target], ["a", null, "openpath", SIBLING, true, "Open " + SIBLING, null],
      "an SVG anchor's relative href becomes the same path link a relative <a> does: the href off, the joined path and the title on it");

    // 4. the SVG anchor's relative `sibling.md` opens the sibling in THIS viewer, through the body's one click listener
    const popups2 = w.popups.length, navs2 = w.navs.length;
    await clickOn(page, ".fx-svg-rel text");
    await page.waitForSelector("#romp-fileview .fileview-md h1#md-sibling", { timeout: 10000 });
    assert.ok(w.fileRequests.includes(SIBLING), "the viewer fetched the sibling over /file: " + JSON.stringify(w.fileRequests));
    assert.equal(page.url(), START, "sibling: location.href is unchanged");
    assert.deepEqual(w.navs.slice(navs2), [], "sibling: no main-frame navigation");
    assert.equal(w.popups.length, popups2, "sibling: no new tab");

    assert.deepEqual(w.errors, [], "no page errors");
  });
});
