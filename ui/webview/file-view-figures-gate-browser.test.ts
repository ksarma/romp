// Decision 8 of plans/markdown-viewer.md over the REAL Files bundle in headless Chromium (figure-gate.ts; ruling 2026-09-07):
// a figure whose source is on a host the gear's list does not name makes NO request when the file opens, and shows a
// placeholder naming the host; one click on the placeholder loads it and every other figure of that host in the document,
// and the host stays loaded for the page; a figure on github.com loads on open, and so does a file's own attachment
// through /file. The page's own request events are the record (md-sanitize-background-browser.test.ts's shape), over the
// whole set the gap analysis measured fetching on open: an `<img src>`, an `<img srcset>` candidate beside a local src, a
// `<video poster>`, a `<picture><source srcset>`, an `<svg><image href>`, and a second picture of the same host. Then the
// parts no stand-in can stand in for: the comments panel's region layer wraps THE picture inside the placeholder and the
// click leaves it standing around the loaded picture; Enter on a focused placeholder loads it; a re-open of the file keeps
// a loaded host loaded; a change to the gear's list in another tab (the storage event, here the same-document event)
// re-judges the open document's placeholders in place; an emptied list gates github.com too; and a URL document allows its own host
// beside the list, which shows on a figure of that hostname under another scheme or port (another origin, so only the
// arm lets it through). Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented note, TESTHOST paths, a placeholder sid, .test hosts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { FIGURE_HOSTS_DEFAULT } from "./settings";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/tmp/TESTHOST/notes-api";
const DIR = ROOT + "/docs/";
const FILE_PATH = DIR + "figures.md";
const NOTE = [
  "# Figures", "",
  "Local ![](fig.png) and remote ![](https://other.test/o.png) end.", "",
  '<p><img class="fx-remote" src="https://remote.test/img.png" alt="r" width="120" height="80"></p>', "",
  '<p><img class="fx-gh" src="https://github.com/u/r/raw/main/gh.png" alt="g"></p>', "",
  '<p><img class="fx-srcset" src="local.png" srcset="https://remote.test/sr.png 2x" alt="s"></p>', "",
  '<video class="fx-video" src="clip.mp4" poster="https://remote.test/poster.png" width="160" height="90"></video>', "",
  '<picture class="fx-picture"><source srcset="https://remote.test/pic.png"><img src="pic-fallback.png" alt="p"></picture>', "",
  '<svg class="fx-svg" width="50" height="50"><image href="https://remote.test/svg.png" width="50" height="50"/></svg>', "",
  '<p><img class="fx-remote2" src="https://remote.test/img2.png" alt="r2"></p>', "",
  '<p><img class="fx-data" src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" alt="d"></p>', "",
  "Last para.", "",
].join("\n");
// a URL document is same-origin by the viewer's own fetch mode (file-view.ts openUrlView, `mode: "same-origin"`), so its HOSTNAME is
// the page's, and a figure on the page's own origin (fx-own, the relative one) passes remoteHost without the arm. The arm
// (file-view.ts mdBlock, `gateRemoteFigures(box, document.baseURI, [own])`) decides for a figure on that hostname under another
// scheme or port: another ORIGIN, which remoteHost reports as the host "romp.test", and which only the arm's entry in the
// allowed set lets load on open (fx-alt, fx-port). The list gates the rest (fx-far). Without the arm, fx-alt and fx-port are
// placeholders naming romp.test.
const URL_DOC = "http://romp.test/notes/note.md";
const URL_NOTE = '# Note\n\n<p><img class="fx-own" src="http://romp.test/own.png" alt="o"> <img class="fx-alt" src="https://romp.test/alt.png" alt="a"> <img class="fx-port" src="http://romp.test:8080/port.png" alt="pt"> <img class="fx-far" src="https://remote2.test/x.png" alt="f"></p>\n\n![](rel.png)\n';
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the URL viewer and the anchor map, for the URL-kind scene and the mapping around a placeholder. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { openUrlView } from "./file-view";\nimport { mapRenderedSelection } from "./anchor-map";\n(window as any).__rompProbe = { openUrlView, mapRenderedSelection };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
// the pane's poster answers the comments panel's status asks with an empty status, so the real panel can open (file-view-links-browser.test.ts's shape)
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>
window.__posts = [];
window.acquireVsCodeApi = function () { return { postMessage: function (m) {
  window.__posts.push(m);
  if (m.type === "fileComments") {
    var root = ${JSON.stringify(ROOT)};
    var s = { verb: "status", root: root, storePath: root + "/.trackchanges/" + m.path.slice(root.length + 1) + ".json", trackedBy: null, agentTooling: "present",
      fileMtimeNs: "1", storeMtimeNs: null, configMtimeNs: null, store: null, hunks: [], unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null }, log: [] };
    setTimeout(function () { window.postMessage(Object.assign({ type: "fileCommentsResult", reqId: m.reqId }, s), "*"); }, 0);
  }
} }; };
</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type H = { page: any; errors: string[]; requests: string[]; open: () => Promise<void>; settle: () => Promise<void>; foreign: () => string[]; files: () => string[] };
/** A Files page with every request logged; `open` posts the relay and awaits the rendered box plus every picture's load or error. */
async function inBrowser(t: any, body: (h: H) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const requests: string[] = [];
  try {
    const js = filesBundle();
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { requests.push(r.url()); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.host !== "romp.test") return route.fulfill({ status: 200, contentType: "image/png", body: PNG });   // recorded above (romp.test:8080 included: host carries the port); a picture, so a load settles
      if (u.pathname === "/notes/note.md") return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: URL_NOTE });
      if (u.pathname === "/own.png" || u.pathname === "/alt.png" || u.pathname === "/notes/rel.png") return route.fulfill({ status: 200, contentType: "image/png", body: PNG });
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/file") {
        const p = u.searchParams.get("path") || "";
        if (p === FILE_PATH) return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
        if (/\.png$/.test(p)) return route.fulfill({ status: 200, contentType: "image/png", body: PNG });
        return route.fulfill({ status: 404, body: "" });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    const settle = () => page.evaluate(async () => {
      await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
      const imgs = Array.from(document.querySelectorAll("#romp-fileview img[src]")) as HTMLImageElement[];
      await Promise.all(imgs.map((i) => i.complete ? null : new Promise<void>((d) => { i.onload = () => d(); i.onerror = () => d(); })));
      await new Promise<void>((r) => requestAnimationFrame(() => setTimeout(r, 40)));
    });
    const open = async () => {
      await page.evaluate(() => { const md = document.querySelector("#romp-fileview .fileview-md"); if (md) (md as any).__old = true; });
      await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
      await page.waitForFunction(() => { const md = document.querySelector("#romp-fileview .fileview-body .fileview-md"); return !!md && !(md as any).__old; }, null, { timeout: 15000 });
      await settle();
    };
    const foreign = () => requests.filter((u) => !u.startsWith("http://romp.test/") && !u.startsWith("data:")).sort();
    const files = () => requests.filter((u) => u.startsWith("http://romp.test/file?")).map((u) => decodeURIComponent(new URL(u).searchParams.get("path") || "")).sort();
    await body({ page, errors, requests, open, settle, foreign, files });
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
}

type Gate = { host: string | null; hosts: string | null; act: string | null; role: string | null; tabindex: string | null; title: string | null; label: string | null; style: string | null; inner: string; parent: string };
/** Every placeholder in the rendered box, in order, with what it wraps. */
function readGates(): Gate[] {
  return Array.from(document.querySelectorAll("#romp-fileview .fileview-md .fv-gate")).map((g) => {
    const media = g.firstElementChild as HTMLElement;
    const kids = [media, ...Array.from(media.querySelectorAll("*"))];
    const inner = kids.map((k) => k.tagName.toLowerCase() + "[" + Array.from(k.attributes).filter((a) => /^(src|srcset|poster|href|data-fv-|class|width|height)/.test(a.name)).map((a) => a.name + "=" + a.value).sort().join(" ") + "]").join(" ");
    return { host: g.getAttribute("data-fv-host"), hosts: g.getAttribute("data-fv-hosts"), act: g.getAttribute("data-act"), role: g.getAttribute("role"), tabindex: g.getAttribute("tabindex"), title: g.getAttribute("title"),
      label: g.querySelector(".fv-gate-label")?.textContent || null, style: g.getAttribute("style"), inner, parent: g.parentElement!.tagName };
  });
}
const FILE_URL = (name: string) => "/file?path=" + encodeURIComponent(DIR + name).replace(/%2F/g, "%2F") + "&sid=" + SID;

test("on open: no request leaves the page for a figure on an unlisted host, in any of the six shapes; github.com and the file's own attachment load; each gated figure is a placeholder naming its host with the sources moved aside; the paragraph around a placeholder still maps", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    await h.open();
    assert.deepEqual(h.foreign(), ["https://github.com/u/r/raw/main/gh.png"], "the one request that left the page is github.com's (the positive control: the recorder sees requests that leave)");
    assert.deepEqual(h.files(), [DIR + "fig.png", FILE_PATH], "the file and its own attachment through /file; local.png, clip.mp4 and pic-fallback.png wait inside their gated figures");
    const gates: Gate[] = await h.page.evaluate(readGates);
    assert.deepEqual(gates.map((g) => [g.host, g.act, g.role, g.tabindex, g.title, g.label, g.parent]), [
      ["other.test", "fv-load", "button", "0", "Load from other.test", "Image from other.test. Click to load.", "P"],
      ["remote.test", "fv-load", "button", "0", "Load from remote.test", "Image from remote.test. Click to load.", "P"],
      ["remote.test", "fv-load", "button", "0", "Load from remote.test", "Image from remote.test. Click to load.", "P"],
      ["remote.test", "fv-load", "button", "0", "Load from remote.test", "Video from remote.test. Click to load.", "P"],
      ["remote.test", "fv-load", "button", "0", "Load from remote.test", "Image from remote.test. Click to load.", "P"],
      ["remote.test", "fv-load", "button", "0", "Load from remote.test", "Image from remote.test. Click to load.", "P"],
      ["remote.test", "fv-load", "button", "0", "Load from remote.test", "Image from remote.test. Click to load.", "P"],
    ], "seven placeholders, each inside the parent the figure had (marked keeps a one-line <video>, <picture> or <svg> inline in its paragraph; a paragraph stays one element), so the block pairing holds");
    // what each wraps: every fetching attribute moved to data-fv-gated-*, data-fv-src moved aside too (no embed pairing while gated)
    assert.equal(gates[0].inner, 'img[data-fv-gated-src=https://other.test/o.png]');
    assert.equal(gates[1].inner, 'img[class=fx-remote data-fv-gated-src=https://remote.test/img.png height=80 width=120]');
    assert.equal(gates[1].style, "width: 120px; aspect-ratio: 120 / 80;", "the author's size keeps the page's shape while the figure waits");
    assert.equal(gates[2].inner, `img[class=fx-srcset data-fv-gated-fv-src=local.png data-fv-gated-src=${FILE_URL("local.png")} data-fv-gated-srcset=https://remote.test/sr.png 2x]`, "the local src was rewritten through /file first, then moved aside with the remote srcset");
    assert.equal(gates[3].inner, `video[class=fx-video data-fv-gated-poster=https://remote.test/poster.png data-fv-gated-src=${FILE_URL("clip.mp4")} height=90 width=160]`);
    assert.equal(gates[3].style, "width: 160px; aspect-ratio: 160 / 90;");
    assert.equal(gates[4].inner, `picture[class=fx-picture] source[data-fv-gated-srcset=https://remote.test/pic.png] img[data-fv-gated-fv-src=pic-fallback.png data-fv-gated-src=${FILE_URL("pic-fallback.png")}]`, "a picture is gated whole: its remote source and its local fallback both wait");
    assert.equal(gates[5].inner, "svg[class=fx-svg height=50 width=50] image[data-fv-gated-href=https://remote.test/svg.png height=50 width=50]");
    assert.equal(gates[6].inner, "img[class=fx-remote2 data-fv-gated-src=https://remote.test/img2.png]");
    // the ungated ones stand as they were
    const plain = await h.page.evaluate(() => ({
      gh: (document.querySelector("#romp-fileview img.fx-gh") as HTMLImageElement).getAttribute("src"), ghGated: !!document.querySelector("#romp-fileview img.fx-gh")!.closest(".fv-gate"),
      data: (document.querySelector("#romp-fileview img.fx-data") as HTMLImageElement).getAttribute("src")!.slice(0, 15), dataGated: !!document.querySelector("#romp-fileview img.fx-data")!.closest(".fv-gate"),
      fig: document.querySelector('#romp-fileview img[data-fv-src="fig.png"]') ? (document.querySelector('#romp-fileview img[data-fv-src="fig.png"]') as HTMLImageElement).getAttribute("src")!.startsWith("/file?path=") : null,
      figGated: !!document.querySelector('#romp-fileview img[data-fv-src="fig.png"]')?.closest(".fv-gate"),
      hidden: getComputedStyle(document.querySelector("#romp-fileview .fv-gate img")!).display,
      labelShown: getComputedStyle(document.querySelector("#romp-fileview .fv-gate .fv-gate-label")!).display !== "none",   // a flex item reads "block"; what matters is that it shows
    }));
    assert.deepEqual(plain, { gh: "https://github.com/u/r/raw/main/gh.png", ghGated: false, data: "data:image/gif;", dataGated: false, fig: true, figGated: false, hidden: "none", labelShown: true });
    // the anchor map around a placeholder: its label is the viewer's text, skipped as a control, so the paragraph maps
    const m = await h.page.evaluate((src: string) => {
      const probe = (window as any).__rompProbe;
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const p = Array.from(md.querySelectorAll(":scope > p")).find((e) => (e.textContent || "").startsWith("Local"))!;
      const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      const nodes: Text[] = []; for (let n = walker.nextNode() as Text | null; n; n = walker.nextNode() as Text | null) nodes.push(n);
      const first = nodes.find((n) => n.data.includes("Local"))!, last = nodes.find((n) => n.data.includes("end."))!;
      return probe.mapRenderedSelection({ anchorNode: first, anchorOffset: first.data.indexOf("Local"), focusNode: last, focusOffset: last.data.indexOf("end.") + 4, isCollapsed: false }, md, src);
    }, NOTE);
    assert.equal(m.ok, true, JSON.stringify(m));
    assert.equal(m.quote, "Local ![](fig.png) and remote ![](https://other.test/o.png) end.", "the whole line, the two pictures' source inside it");
  });
});

test("with the comments panel open the region layer wraps the picture inside its placeholder; one click restores every figure of that host, the layer's wrapper standing around the loaded picture, and the requests follow; Enter loads a focused one; a re-open keeps both hosts loaded", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    const { page } = h;
    await h.open();
    // the real panel: the status auto-reply reveals the unit, a click on its button opens the aside
    await page.waitForFunction(() => { const u = document.querySelector("#romp-fileview .fileview-fc"); return !!u && !(u as HTMLElement).hidden; }, null, { timeout: 5000 });
    await page.click("#romp-fileview .fileview-fc button");
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-aside"), null, { timeout: 5000 });
    await h.settle();
    const wrapped = await page.evaluate(() => {
      const img = document.querySelector("#romp-fileview img.fx-remote") as HTMLElement;
      return { parent: img.parentElement!.className, grand: img.parentElement!.parentElement!.className, gh: (document.querySelector("#romp-fileview img.fx-gh") as HTMLElement).parentElement!.className, gates: document.querySelectorAll("#romp-fileview .fv-gate").length };
    });
    assert.deepEqual(wrapped, { parent: "fc-imgwrap", grand: "fv-gate", gh: "fc-imgwrap", gates: 7 }, "the layer wraps THE img, inside the placeholder for a gated one and in the paragraph for a loaded one");
    // the click on one remote.test placeholder
    const before = h.foreign().length;
    await page.locator("#romp-fileview .fv-gate[data-fv-host='remote.test']").first().click();
    await page.waitForFunction(() => (document.querySelector("#romp-fileview img.fx-remote") as HTMLImageElement).getAttribute("src") === "https://remote.test/img.png", null, { timeout: 5000 });
    await h.settle();
    const after = await page.evaluate(() => {
      const q = (s: string) => document.querySelector("#romp-fileview " + s) as HTMLElement;
      const a = (s: string, n: string) => q(s).getAttribute(n);
      return {
        remoteGates: document.querySelectorAll("#romp-fileview .fv-gate[data-fv-host='remote.test']").length, otherGates: document.querySelectorAll("#romp-fileview .fv-gate[data-fv-host='other.test']").length,
        gatedAttrs: document.querySelectorAll("#romp-fileview [data-fv-gated-src], #romp-fileview [data-fv-gated-srcset], #romp-fileview [data-fv-gated-poster], #romp-fileview [data-fv-gated-href], #romp-fileview [data-fv-gated-fv-src]").length,
        remote: { parent: q("img.fx-remote").parentElement!.className, grand: q("img.fx-remote").parentElement!.parentElement!.tagName, complete: (q("img.fx-remote") as HTMLImageElement).complete, w: (q("img.fx-remote") as HTMLImageElement).naturalWidth },
        srcset: { src: a("img.fx-srcset", "src"), srcset: a("img.fx-srcset", "srcset"), fv: a("img.fx-srcset", "data-fv-src") },
        video: { src: a("video.fx-video", "src"), poster: a("video.fx-video", "poster") },
        picture: { srcset: a("picture.fx-picture source", "srcset"), src: a("picture.fx-picture img", "src"), fv: a("picture.fx-picture img", "data-fv-src") },
        svg: a("svg.fx-svg image", "href"), remote2: a("img.fx-remote2", "src"),
      };
    });
    assert.equal(after.remoteGates, 0, "every remote.test placeholder is gone after one click");
    assert.equal(after.otherGates, 1, "the other host's stays");
    assert.equal(after.gatedAttrs, 1, "one gated source left in the document: the other host's");
    assert.deepEqual(after.remote, { parent: "fc-imgwrap", grand: "P", complete: true, w: 1 }, "the picture loaded inside the layer's wrapper, which stands where the placeholder was");
    assert.deepEqual(after.srcset, { src: FILE_URL("local.png"), srcset: "https://remote.test/sr.png 2x", fv: "local.png" }, "the img's src and srcset back, and data-fv-src back under its own name (the embed pairs again)");
    assert.deepEqual(after.video, { src: FILE_URL("clip.mp4"), poster: "https://remote.test/poster.png" });
    assert.deepEqual(after.picture, { srcset: "https://remote.test/pic.png", src: FILE_URL("pic-fallback.png"), fv: "pic-fallback.png" });
    assert.deepEqual([after.svg, after.remote2], ["https://remote.test/svg.png", "https://remote.test/img2.png"]);
    const remoteReqs = h.foreign().filter((u) => u.startsWith("https://remote.test/") && u !== "https://remote.test/pic.png");
    assert.deepEqual(remoteReqs, ["https://remote.test/img.png", "https://remote.test/img2.png", "https://remote.test/poster.png", "https://remote.test/svg.png"], "the host's figures fetched after the click (sr.png is a 2x candidate beside a local src: not picked at DPR 1)");
    assert.ok(h.foreign().includes("https://remote.test/pic.png") || h.files().includes(DIR + "pic-fallback.png"), "the picture loaded from one of its two sources once both came back (which one is the browser's choice: measured, Chromium takes the fallback img when the source's srcset is restored on a picture already in the document): " + JSON.stringify(h.files()));
    assert.ok(h.foreign().length > before, "…and none before it");
    assert.ok(!h.foreign().some((u) => u.startsWith("https://other.test/")), "the other host is still gated: no request");
    assert.ok(h.files().includes(DIR + "local.png"), "the local src inside the restored srcset figure fetched through /file: " + JSON.stringify(h.files()));
    // Enter on the focused placeholder loads the other host
    await page.focus("#romp-fileview .fv-gate[data-fv-host='other.test']");
    await page.keyboard.press("Enter");
    await page.waitForFunction(() => !document.querySelector("#romp-fileview .fv-gate"), null, { timeout: 5000 });
    await h.settle();
    assert.ok(h.foreign().includes("https://other.test/o.png"), "Enter loaded it: " + JSON.stringify(h.foreign()));
    assert.equal(await page.evaluate(() => location.href), "http://romp.test/files", "the location stands");
    // a re-open of the file: a fresh paint, and both hosts load on open now (the ruling: a host the person allowed stays allowed)
    await h.open();
    assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview .fv-gate").length), 0, "no placeholder on the re-open");
    assert.equal(await page.evaluate(() => (document.querySelector("#romp-fileview img.fx-remote") as HTMLElement).getAttribute("src")), "https://remote.test/img.png");
  });
});

test("the gear's list reaches an open document in place: a host added to figureHosts restores its placeholders without a repaint, and an emptied list gates github.com on the next open", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    const { page } = h;
    await h.open();
    assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview .fv-gate").length), 7);
    await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-md") as any).__same = true; });
    // the gear saves in another tab of this browser (the storage event) or in this document (the romp:settings event); the same listener
    await page.evaluate((hosts: string[]) => {
      localStorage.setItem("romp:settings", JSON.stringify({ figureHosts: hosts.concat(["Remote.TEST"]) }));
      window.dispatchEvent(new Event("romp:settings"));
    }, [...FIGURE_HOSTS_DEFAULT]);
    await h.settle();
    const regated = await page.evaluate(() => ({
      same: !!(document.querySelector("#romp-fileview .fileview-md") as any).__same,
      remote: document.querySelectorAll("#romp-fileview .fv-gate[data-fv-host='remote.test']").length, other: document.querySelectorAll("#romp-fileview .fv-gate[data-fv-host='other.test']").length,
      src: (document.querySelector("#romp-fileview img.fx-remote") as HTMLElement).getAttribute("src"),
    }));
    assert.deepEqual(regated, { same: true, remote: 0, other: 1, src: "https://remote.test/img.png" }, "re-judged in place: the same rendered box, the added host's placeholders restored, the other host's kept");
    assert.ok(h.foreign().includes("https://remote.test/img.png"));
    // an emptied list is a choice: only the kernel's own origin loads, github.com included in the gate
    await page.evaluate(() => { localStorage.setItem("romp:settings", JSON.stringify({ figureHosts: [] })); window.dispatchEvent(new Event("romp:settings")); });
    await h.open();
    const emptied = await page.evaluate(() => ({
      gh: (document.querySelector("#romp-fileview img.fx-gh") as HTMLElement).closest(".fv-gate")?.getAttribute("data-fv-host") || null,
      remote: (document.querySelector("#romp-fileview img.fx-remote") as HTMLElement).closest(".fv-gate")?.getAttribute("data-fv-host") || null,
      fig: !!document.querySelector('#romp-fileview img[data-fv-src="fig.png"]')?.closest(".fv-gate"),
    }));
    assert.deepEqual(emptied, { gh: "github.com", remote: "remote.test", fig: false }, "github.com is gated under an empty list, and so is remote.test again: the setting allowed it, not a click, and the loaded set holds only the hosts the person clicked; the file's own attachment is never gated");
  });
});

test("a URL document (same-origin by the viewer's fetch mode) loads its own host's pictures on open: one on the page's origin, a relative one resolved against it, and one on the same hostname under another scheme or port (the own-host arm; the list does not name it); a picture on another host is gated and loads on the click through the URL viewer's own delegate", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    const { page } = h;
    await page.evaluate((u: string) => { (window as any).__rompProbe.openUrlView(u); }, URL_DOC);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
    await h.settle();
    const doc = await page.evaluate(() => {
      const q = (s: string) => document.querySelector("#romp-fileview " + s) as HTMLElement;
      const gate = (s: string) => q(s).closest(".fv-gate")?.getAttribute("data-fv-host") || null;   // the placeholder's host, or null for a figure that stands ungated
      return {
        own: q("img.fx-own").getAttribute("src"), ownGated: gate("img.fx-own"),
        rel: q('img[alt=""]').getAttribute("src"), relGated: gate('img[alt=""]'),
        alt: q("img.fx-alt").getAttribute("src"), altGated: gate("img.fx-alt"),
        port: q("img.fx-port").getAttribute("src"), portGated: gate("img.fx-port"),
        far: gate("img.fx-far"),
      };
    });
    assert.deepEqual(doc, {
      own: "http://romp.test/own.png", ownGated: null, rel: "http://romp.test/notes/rel.png", relGated: null,
      alt: "https://romp.test/alt.png", altGated: null, port: "http://romp.test:8080/port.png", portGated: null,
      far: "remote2.test",
    }, "the page's origin and the document's hostname under another scheme or port stand ungated; the other host is a placeholder naming it");
    const own = h.requests.filter((u) => u === "http://romp.test/own.png" || u === "http://romp.test/notes/rel.png").sort();
    assert.deepEqual(own, ["http://romp.test/notes/rel.png", "http://romp.test/own.png"], "the document's own origin loaded on open: " + JSON.stringify(h.requests));
    // the two other-origin figures of the document's hostname left the page's origin on open (the arm allowed them; remoteHost alone
    // would have gated both as "romp.test"), and nothing left for the other host
    assert.deepEqual(h.foreign(), ["http://romp.test:8080/port.png", "https://romp.test/alt.png"], "the own-host arm's figures fetched on open, and nothing for the other host: " + JSON.stringify(h.foreign()));
    await page.click("#romp-fileview .fv-gate[data-fv-host='remote2.test']");
    await page.waitForFunction(() => !document.querySelector("#romp-fileview .fv-gate"), null, { timeout: 5000 });
    await h.settle();
    assert.ok(h.foreign().includes("https://remote2.test/x.png"), "loaded on the click through the URL viewer's own delegate");
  });
});
