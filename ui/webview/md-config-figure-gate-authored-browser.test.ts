// The figure gate (figure-gate.ts; decision 8 of plans/markdown-viewer.md) against a note's author-written srcset shapes and
// class names, over the REAL Files bundle in headless Chromium: the review of Slice 4 (round 1) found four ways a note's own
// markup parted the gate from the browser. Two are bypasses: a srcset URL holding a non-ASCII space (`&nbsp;`, `&#11;`,
// `&#8195;`, `&#65279;`) read as the allowed host github.com to a parse that stopped at any JS `\s`, while the browser, which
// stops at ASCII whitespace only, fetched the host after the `@`; and a descriptor `((,) 1x` hid a second candidate from a
// parse that counted paren depth, while the browser, whose in-parens state ends at the first `)`, dropped the first candidate
// and fetched the second. Two are the viewer's class names typed by the author: an element with class `fv-gate-label` inside a
// gated figure took the placeholder's text (the real label stayed empty, and on a `<video>` the text replaced its sources),
// and a `<span class="fv-gate">` around prose was unwrapped by the re-judge on any click or settings change, its text dropped.
// The page's own request events are the record (file-view-figures-gate-browser.test.ts's shape): on open no request event
// names an unlisted host, whichever way the srcset is spelled, and a placeholder names it; the viewer's own label carries the
// text whatever class the author used; the author's prose survives a click and a settings event. Skips LOUDLY without a
// playwright browser (CI installs none). Synthetic values only: an invented note, TESTHOST paths, a placeholder sid, .test
// hosts; the non-ASCII code points are written as HTML entities so this source stays ASCII.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/tmp/TESTHOST/notes-api";
const DIR = ROOT + "/docs/";
const FILE_PATH = DIR + "authored.md";
const NOTE = [
  "# Authored", "",
  // the srcset shapes: a non-ASCII space inside the URL (the host after the `@` is the one the browser fetches from)
  '<p><img class="fx-nbsp" srcset="https://github.com&nbsp;@ws1.test/x.png" alt="n"></p>', "",
  '<p><img class="fx-vt" srcset="https://github.com&#11;@ws2.test/x.png" alt="v"></p>', "",
  '<p><img class="fx-emsp" srcset="https://github.com&#8195;@ws3.test/x.png" alt="e"></p>', "",
  '<p><img class="fx-bom" srcset="https://github.com&#65279;@ws4.test/x.png" alt="b"></p>', "",
  // a descriptor whose parens do not nest: the browser drops the first candidate and takes the second
  '<p><img class="fx-nested" srcset="https://github.com/a.png ((,) 1x, https://ws5.test/b.png" alt="p"></p>', "",
  '<p><img class="fx-rewrite" srcset="a.png ((,) 1x, https://ws6.test/b.png" alt="w"></p>', "",
  '<picture class="fx-pic"><source srcset="https://github.com&nbsp;@ws7.test/p.png"><img src="pf.png" alt="pf"></picture>', "",
  // an allowed srcset spelled without the space after the comma: loads on open, read back in the canonical spelling
  '<p><img class="fx-canon" srcset="https://github.com/c1.png 1x,https://github.com/c2.png 2x" alt="c"></p>', "",
  // the viewer's class names, typed by the author
  '<svg class="fx-lsvg" width="50" height="50"><text class="fv-gate-label">author</text><image href="https://lab1.test/i.png" width="50" height="50"/></svg>', "",
  '<p><img class="fv-gate-label fx-limg" alt="Image from github.com. Click to load." src="https://lab2.test/k.png"></p>', "",
  '<video class="fv-gate-label fx-lvid" width="160" height="90"><source src="https://lab3.test/a.mp4" type="video/mp4"></video>', "",
  '<p id="pr1"><span class="fv-gate">visible prose <b>bold</b></span> tail</p>', "",
  '<p id="pr2"><span class="fv-gate">only text</span> tail2</p>', "",
  '<p><img class="fx-remote" src="https://remote.test/img.png" alt="r"></p>', "",
  "Last para.", "",
].join("\n");
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function filesBundle(): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents: 'import "./files";\n', resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
  return r.outputFiles[0].text;
}
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

type H = { page: any; errors: string[]; open: () => Promise<void>; settle: () => Promise<void>; foreign: () => string[]; files: () => string[] };
/** A Files page with every request event logged (a request Chromium refuses before the network still raises one, which is
 *  the point: the record is what the page TRIED to fetch); `open` posts the relay and awaits the rendered box. */
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
      if (u.host !== "romp.test") return route.fulfill({ status: 200, contentType: "image/png", body: PNG });
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
      const imgs = Array.from(document.querySelectorAll("#romp-fileview img[src], #romp-fileview img[srcset]")) as HTMLImageElement[];
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
    await body({ page, errors, open, settle, foreign, files });
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
}

const FILE_URL = (name: string) => "/file?path=" + encodeURIComponent(DIR + name) + "&sid=" + SID;
/** The placeholders the viewer made (by the delegated action, the one mark an author cannot write), in order: the hosts each
 *  waits on and the srcset it holds aside. */
type GateRow = { hosts: string | null; media: string; srcset: string | null };
function readGates(): GateRow[] {
  return Array.from(document.querySelectorAll('#romp-fileview .fileview-md [data-act="fv-load"]')).map((g) => {
    const media = g.firstElementChild as HTMLElement;
    const holder = media.hasAttribute("data-fv-gated-srcset") ? media : media.querySelector("[data-fv-gated-srcset]");
    return { hosts: g.getAttribute("data-fv-hosts"), media: media.tagName.toLowerCase() + "." + (media.getAttribute("class") || "").split(/\s+/).filter((c) => c.startsWith("fx-")).join("."), srcset: holder ? holder.getAttribute("data-fv-gated-srcset") : null };
  });
}

test("srcset spelled the browser's way: a URL through a non-ASCII space (nbsp, VT, em space, BOM) and a candidate after a `((,)` descriptor are the hosts the browser would fetch, so each is a placeholder and no request event names it on open; an allowed srcset reads back canonical; the click fetches what the gate judged", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    await h.open();
    const leaked = h.foreign().filter((u) => /ws[1-7]\.test/.test(u));
    assert.deepEqual(leaked, [], "no request event for a host the srcset hides from a JS-flavoured parse");
    assert.deepEqual(h.foreign().filter((u) => u.includes("github.com")), ["https://github.com/c1.png"], "the allowed srcset's 1x candidate is the one github.com fetch (the recorder sees requests that leave); the gated srcsets' github.com candidates wait with their unlisted ones");
    assert.deepEqual(h.files(), [FILE_PATH], "a.png and pf.png wait inside their gated figures");
    const gates: GateRow[] = await h.page.evaluate(readGates);
    const bySrcset = gates.filter((g) => g.srcset !== null);
    assert.deepEqual(bySrcset.map((g) => [g.hosts, g.media]), [
      ["ws1.test", "img.fx-nbsp"], ["ws2.test", "img.fx-vt"], ["ws3.test", "img.fx-emsp"], ["ws4.test", "img.fx-bom"],
      ["ws5.test", "img.fx-nested"], ["ws6.test", "img.fx-rewrite"], ["ws7.test", "picture.fx-pic"],
    ], "seven placeholders, each naming the host the browser reads; github.com is not a host of any (it is the userinfo, or an allowed sibling candidate)");
    assert.equal(bySrcset[0].srcset, "https://github.com\u00a0@ws1.test/x.png", "the attribute held aside is the URL whole, as written");
    assert.equal(bySrcset[4].srcset, "https://github.com/a.png ((,) 1x, https://ws5.test/b.png");
    assert.equal(bySrcset[5].srcset, FILE_URL("a.png") + " ((,) 1x, https://ws6.test/b.png", "the relative candidate through /file, the unlisted one as written, the odd descriptor kept");
    const canon = await h.page.evaluate(() => {
      const c = document.querySelector("#romp-fileview img.fx-canon") as HTMLImageElement;
      return { srcset: c.getAttribute("srcset"), gated: !!c.closest('[data-act="fv-load"]') };
    });
    assert.deepEqual(canon, { srcset: "https://github.com/c1.png 1x, https://github.com/c2.png 2x", gated: false }, "an allowed srcset is written back in the spelling the gate parsed, so the browser reads exactly the candidates the gate judged");
    // the click on the nested-paren placeholder: the srcset goes back whole, and the browser, dropping the first candidate for its unknown descriptor, fetches the second (ws5.test), the one the gate named
    await h.page.locator('#romp-fileview [data-act="fv-load"][data-fv-host="ws5.test"]').click();
    await h.page.waitForFunction(() => { const i = document.querySelector("#romp-fileview img.fx-nested"); return !!i && i.getAttribute("srcset") === "https://github.com/a.png ((,) 1x, https://ws5.test/b.png"; }, null, { timeout: 5000 });
    await h.settle();
    assert.ok(h.foreign().includes("https://ws5.test/b.png"), "after the click the second candidate is fetched: " + JSON.stringify(h.foreign()));
    assert.deepEqual(h.foreign().filter((u) => /ws[1-4,6-7]\.test/.test(u)), [], "the other placeholders still hold theirs");
  });
});

test("the viewer's class names typed by the author: an element with class fv-gate-label inside a gated svg, on a gated img and on a gated video never takes the placeholder's text (the viewer's own label carries it, the author's nodes stand as written, the video keeps its source through the click); a span.fv-gate around prose survives a click and a settings event with its text", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    await h.open();
    assert.deepEqual(h.foreign().filter((u) => /lab[1-3]\.test|remote\.test/.test(u)), [], "nothing leaves for the gated figures on open");
    const read = () => h.page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const gate = (cls: string) => md.querySelector("." + cls)!.closest('[data-act="fv-load"]') as HTMLElement | null;
      // the viewer's label is the placeholder's LAST child: the media root goes in first, the label after it
      const ownLabel = (g: HTMLElement | null) => g ? (g.lastElementChild as HTMLElement).textContent : "(no placeholder)";
      const ownLabelTag = (g: HTMLElement | null) => g ? g.lastElementChild!.tagName.toLowerCase() : "(no placeholder)";
      const svg = gate("fx-lsvg"), img = gate("fx-limg"), vid = gate("fx-lvid");
      const p = (id: string) => (md.querySelector("#user-content-" + id) as HTMLElement).innerHTML;
      return {
        svg: { label: ownLabel(svg), labelTag: ownLabelTag(svg), visible: svg ? svg.innerText : null, authorText: md.querySelector(".fx-lsvg text")!.textContent },
        img: { label: ownLabel(img), labelTag: ownLabelTag(img), imgText: md.querySelector(".fx-limg")!.textContent },
        video: { label: ownLabel(vid), labelTag: ownLabelTag(vid), sources: Array.from(md.querySelectorAll(".fx-lvid source")).map((s) => s.getAttribute("src") + "|" + s.getAttribute("data-fv-gated-src")) },
        pr1: p("pr1"), pr2: p("pr2"),
        remoteGated: !!md.querySelector(".fx-remote")!.closest('[data-act="fv-load"]'),
      };
    });
    const before = await read();
    assert.deepEqual(before, {
      svg: { label: "Image from lab1.test. Click to load.", labelTag: "span", visible: "Image from lab1.test. Click to load.", authorText: "author" },
      img: { label: "Image from lab2.test. Click to load.", labelTag: "span", imgText: "" },
      video: { label: "Video from lab3.test. Click to load.", labelTag: "span", sources: ["null|https://lab3.test/a.mp4"] },
      pr1: '<span class="fv-gate">visible prose <b>bold</b></span> tail',
      pr2: '<span class="fv-gate">only text</span> tail2',
      remoteGated: true,
    }, "on open: the viewer's own span carries every label, the author's text and source stand, the prose is as written");
    // a click on another host's placeholder re-judges every placeholder: the author's spans are not placeholders
    await h.page.locator('#romp-fileview [data-act="fv-load"][data-fv-host="remote.test"]').click();
    await h.page.waitForFunction(() => { const i = document.querySelector("#romp-fileview img.fx-remote"); return !!i && i.getAttribute("src") === "https://remote.test/img.png"; }, null, { timeout: 5000 });
    await h.settle();
    const afterClick = await read();
    assert.equal(afterClick.pr1, before.pr1, "the prose span, with its text, after a click");
    assert.equal(afterClick.pr2, before.pr2);
    assert.equal(afterClick.remoteGated, false);
    // a settings event with the list unchanged re-judges too
    await h.page.evaluate(() => { window.dispatchEvent(new Event("romp:settings")); });
    await h.settle();
    const afterSettings = await read();
    assert.equal(afterSettings.pr1, before.pr1, "the prose span after a settings event");
    assert.equal(afterSettings.pr2, before.pr2);
    assert.deepEqual([afterSettings.svg, afterSettings.img, afterSettings.video], [before.svg, before.img, before.video], "the three placeholders still stand, labelled as before");
    // the video's click: its source comes back under its own name; nothing the author wrote was replaced
    await h.page.locator('#romp-fileview [data-act="fv-load"][data-fv-host="lab3.test"]').click();
    await h.page.waitForFunction(() => !!document.querySelector('#romp-fileview .fx-lvid source[src="https://lab3.test/a.mp4"]'), null, { timeout: 5000 });
    const video = await h.page.evaluate(() => {
      const v = document.querySelector("#romp-fileview .fx-lvid") as HTMLElement;
      const sources = Array.from(v.querySelectorAll("source")).map((x) => Array.from(x.attributes).map((a) => a.name + "=" + a.value).sort().join(" "));
      return { gated: !!v.closest('[data-act="fv-load"]'), children: v.children.length, sources, text: v.textContent };
    });
    assert.deepEqual(video, { gated: false, children: 1, sources: ["src=https://lab3.test/a.mp4 type=video/mp4"], text: "" }, "the video's one source, restored under its own name; no label text inside the video");
  });
});
