// The figure gate (figure-gate.ts; decision 8 of plans/markdown-viewer.md) against an inline svg's PAINT references, over
// the REAL Files bundle in headless Chromium. Review of Slice 4, round 2: `fill`, `stroke`, `filter`, `clip-path`, `mask`,
// `marker-start`, `marker-mid` and `marker-end` are presentation attributes whose value is CSS, DOMPurify's svg profile
// keeps all eight and its URI check passes `url(`, and a `url(https://host/p.svg#p)` in any of them made the browser request
// that host the moment the file rendered, with no placeholder and no click, in the file kind and the URL kind alike (the
// gate read `src`, `srcset`, `poster` and `href` alone). The page's own request events are the record
// (file-view-figures-gate-browser.test.ts's shape): on open, the one request that leaves the page is a paint reference to
// github.com (the positive control: the recorder sees a paint fetch, and the allowed host loads), each svg naming another
// host is a placeholder with the reference moved to `data-fv-gated-<name>`, in every spelling the browser reads (an escaped
// function name, an escaped `@`, quotes, whitespace, upper case, a fallback colour, a filter list, a mask's image-set), on the
// `<svg>` itself or on an element inside it; a local `url(#id)` is never gated and the same attributes on an HTML element are
// left alone; one click restores the reference as written and the request follows, the other hosts still waiting; and a URL
// document is gated the same. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an invented
// note, TESTHOST paths, a placeholder sid, .test hosts.
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
const FILE_PATH = DIR + "paint.md";
const SQ = (s: string) => '<svg class="' + s + '" width="40" height="40">';
// the non-ASCII code point of the escape tests is written with a CSS escape, so this source stays ASCII; `\40 ` is `@` to the browser
const NOTE = [
  "# Paint", "",
  '<p><img class="px-gh" src="https://github.com/u/r/raw/main/gh.png" alt="g"></p>', "",
  SQ("px-ghfill") + '<rect width="40" height="40" fill="url(https://github.com/u/r/p.svg#p)"/></svg>', "",
  SQ("px-fill") + '<rect width="40" height="40" fill="url(https://fill.test/p.svg#p)"/></svg>', "",
  SQ("px-stroke") + '<rect width="40" height="40" fill="none" stroke="url(https://stroke.test/p.svg#p)" stroke-width="4"/></svg>', "",
  SQ("px-filter") + '<rect width="40" height="40" fill="red" filter="blur(2px) url(https://filter.test/p.svg#f)"/></svg>', "",
  SQ("px-clip") + '<rect width="40" height="40" fill="red" clip-path="url(https://clip.test/p.svg#c)"/></svg>', "",
  SQ("px-mask") + '<rect width="40" height="40" fill="red" mask="image-set(&quot;https://mask.test/a.png&quot; 1x)"/></svg>', "",
  SQ("px-marker") + '<path d="M5 5 L20 20 L35 35" stroke="red" fill="none" marker-start="url(https://marker.test/p.svg#a)" marker-mid="url(https://marker.test/p.svg#b)" marker-end="url(https://marker2.test/p.svg#c)"/></svg>', "",
  '<svg class="px-root" width="40" height="40" filter="url(https://root.test/p.svg#f)"><rect width="40" height="40" fill="red"/></svg>', "",
  SQ("px-group") + '<g fill="url(https://group.test/p.svg#p)"><rect width="40" height="40"/></g></svg>', "",
  SQ("px-escfn") + '<rect width="40" height="40" fill="\\75 rl(https://escfn.test/p.svg#p)"/></svg>', "",
  SQ("px-escat") + '<rect width="40" height="40" fill="url(https://github.com\\40 escat.test/p.svg#p)"/></svg>', "",
  SQ("px-quoted") + '<rect width="40" height="40" fill="url(&quot;https://quoted.test/p.svg#p&quot;)"/></svg>', "",
  SQ("px-spaces") + '<rect width="40" height="40" fill="URL(   https://spaces.test/p.svg#p   ) red"/></svg>', "",
  SQ("px-protorel") + '<rect width="40" height="40" fill="url(//protorel.test/p.svg#p)"/></svg>', "",
  SQ("px-fill2") + '<rect width="40" height="40" fill="url(https://fill.test/q.svg#p)"/></svg>', "",
  SQ("px-local") + '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/></linearGradient></defs><rect width="40" height="40" fill="url(#g)" stroke="red"/></svg>', "",
  '<p><span class="px-span" fill="url(https://htmlfill.test/p.svg#p)" mask="url(https://htmlmask.test/p.svg#m)">span</span></p>', "",
  "Last para.", "",
].join("\n");
const URL_DOC = "http://romp.test/notes/paint.md";
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==", "base64");
const TINY_SVG = '<svg xmlns="http://www.w3.org/2000/svg"><defs><pattern id="p" width="1" height="1"><rect width="1" height="1" fill="blue"/></pattern></defs></svg>';

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The Files pane's bundle plus the URL viewer, for the URL-kind scene. */
function filesBundle(): string {
  const contents = 'import "./files";\nimport { openUrlView } from "./file-view";\n(window as any).__rompProbe = { openUrlView };\n';
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "files-probe.ts" } });
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

type H = { page: any; errors: string[]; requests: string[]; open: () => Promise<void>; settle: () => Promise<void>; foreign: () => string[] };
/** A Files page with every request logged; `open` posts the relay and awaits the rendered box, the github.com paint fetch
 *  (the positive control, issued in the same paint as any other paint fetch would be) and every picture's load or error. */
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
      if (u.host !== "romp.test") {                                   // recorded above; a document answers, so a paint reference resolves
        if (/\.svg$/.test(u.pathname)) return route.fulfill({ status: 200, contentType: "image/svg+xml", body: TINY_SVG });
        return route.fulfill({ status: 200, contentType: "image/png", body: PNG });
      }
      if (u.pathname === "/notes/paint.md") return route.fulfill({ status: 200, contentType: "text/markdown; charset=utf-8", body: NOTE });
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/file") {
        const p = u.searchParams.get("path") || "";
        if (p === FILE_PATH) return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
        return route.fulfill({ status: 404, body: "" });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.evaluate("window.__paints = " + paintsOf.toString() + ";");   // the reader of standing paint attributes, for the scenes' own evaluates
    const settle = () => page.evaluate(async () => {
      await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
      const imgs = Array.from(document.querySelectorAll("#romp-fileview img[src]")) as HTMLImageElement[];
      await Promise.all(imgs.map((i) => i.complete ? null : new Promise<void>((d) => { i.onload = () => d(); i.onerror = () => d(); })));
      await new Promise<void>((r) => requestAnimationFrame(() => setTimeout(r, 40)));
    });
    const open = async () => {
      const control = page.waitForRequest("https://github.com/u/r/p.svg", { timeout: 15000 });
      await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
      await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-md"), null, { timeout: 15000 });
      await control;
      await settle();
    };
    const foreign = () => requests.filter((u) => !u.startsWith("http://romp.test/") && !u.startsWith("data:")).sort();
    await body({ page, errors, requests, open, settle, foreign });
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
}

type Gate = { host: string | null; hosts: string | null; label: string | null; tag: string; cls: string | null; gated: string; display: string };
/** Every placeholder in the rendered box, in order: its host, its label, the element it wraps and every attribute moved aside under it. */
function readGates(): Gate[] {
  return Array.from(document.querySelectorAll('#romp-fileview .fileview-md [data-act="fv-load"]')).map((g) => {
    const media = g.firstElementChild as HTMLElement;
    const kids = [media, ...Array.from(media.querySelectorAll("*"))];
    const gated = kids.flatMap((k) => Array.from(k.attributes).filter((a) => a.name.startsWith("data-fv-gated-")).map((a) => k.tagName.toLowerCase() + " " + a.name.slice("data-fv-gated-".length) + "=" + a.value));
    return { host: g.getAttribute("data-fv-host"), hosts: g.getAttribute("data-fv-hosts"), label: g.querySelector("[data-fv-label]")?.textContent || null,
      tag: media.tagName.toLowerCase(), cls: media.getAttribute("class"), gated: gated.join("; "), display: getComputedStyle(media).display };
  });
}
/** The paint attributes still standing (under their own names) on an element and its descendants. */
function paintsOf(sel: string): string[] {
  const el = document.querySelector("#romp-fileview " + sel) as Element;
  const kids = [el, ...Array.from(el.querySelectorAll("*"))];
  return kids.flatMap((k) => Array.from(k.attributes).filter((a) => /^(fill|stroke|filter|clip-path|mask|marker-start|marker-mid|marker-end)$/.test(a.name)).map((a) => k.tagName.toLowerCase() + " " + a.name + "=" + a.value));
}

const GATED = [
  ["fill.test", "svg", "px-fill", "rect fill=url(https://fill.test/p.svg#p)"],
  ["stroke.test", "svg", "px-stroke", "rect stroke=url(https://stroke.test/p.svg#p)"],
  ["filter.test", "svg", "px-filter", "rect filter=blur(2px) url(https://filter.test/p.svg#f)"],
  ["clip.test", "svg", "px-clip", "rect clip-path=url(https://clip.test/p.svg#c)"],
  ["mask.test", "svg", "px-mask", 'rect mask=image-set("https://mask.test/a.png" 1x)'],
  ["marker.test marker2.test", "svg", "px-marker", "path marker-start=url(https://marker.test/p.svg#a); path marker-mid=url(https://marker.test/p.svg#b); path marker-end=url(https://marker2.test/p.svg#c)"],
  ["root.test", "svg", "px-root", "svg filter=url(https://root.test/p.svg#f)"],
  ["group.test", "svg", "px-group", "g fill=url(https://group.test/p.svg#p)"],
  ["escfn.test", "svg", "px-escfn", "rect fill=\\75 rl(https://escfn.test/p.svg#p)"],
  ["escat.test", "svg", "px-escat", "rect fill=url(https://github.com\\40 escat.test/p.svg#p)"],
  ["quoted.test", "svg", "px-quoted", 'rect fill=url("https://quoted.test/p.svg#p")'],
  ["spaces.test", "svg", "px-spaces", "rect fill=URL(   https://spaces.test/p.svg#p   ) red"],
  ["protorel.test", "svg", "px-protorel", "rect fill=url(//protorel.test/p.svg#p)"],
  ["fill.test", "svg", "px-fill2", "rect fill=url(https://fill.test/q.svg#p)"],
];

test("on open: no request leaves the page for an svg whose paint reference names an unlisted host, in any of the eight attributes and every spelling the browser reads, on the svg itself or inside it; github.com's reference and picture load; each gated svg is a placeholder naming its hosts with the reference moved aside as written; a local url(#id) and an HTML element's fill stand as they were", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    await h.open();
    assert.deepEqual(h.foreign(), ["https://github.com/u/r/p.svg", "https://github.com/u/r/raw/main/gh.png"], "the two requests that left the page are github.com's: the paint reference (the recorder sees a paint fetch) and the picture");
    const gates: Gate[] = await h.page.evaluate(readGates);
    assert.deepEqual(gates.map((g) => [g.hosts, g.tag, g.cls, g.gated]), GATED, "fourteen placeholders, one per svg naming another host, the paint attributes moved to data-fv-gated-<name> verbatim");
    for (const g of gates) {
      assert.equal(g.host, g.hosts!.split(" ")[0]);
      assert.equal(g.label, "Image from " + g.host + (g.hosts!.includes(" ") ? " and 1 more host" : "") + ". Click to load.");
      assert.equal(g.display, "none", "the svg is hidden inside its placeholder while it waits");
    }
    const plain = await h.page.evaluate(() => ({
      ghfill: (window as any).__paints('svg.px-ghfill'), ghfillGated: !!document.querySelector("#romp-fileview svg.px-ghfill")!.closest('[data-act="fv-load"]'),
      local: (window as any).__paints('svg.px-local'), localGated: !!document.querySelector("#romp-fileview svg.px-local")!.closest('[data-act="fv-load"]'),
      span: (window as any).__paints('span.px-span'), spanGated: !!document.querySelector("#romp-fileview span.px-span")!.closest('[data-act="fv-load"]'),
      spanText: document.querySelector("#romp-fileview span.px-span")!.textContent,
      placeholders: document.querySelectorAll('#romp-fileview [data-act="fv-load"]').length,
    }));
    assert.deepEqual(plain, {
      ghfill: ["rect fill=url(https://github.com/u/r/p.svg#p)"], ghfillGated: false,
      local: ["rect fill=url(#g)", "rect stroke=red"], localGated: false,
      span: ["span fill=url(https://htmlfill.test/p.svg#p)", "span mask=url(https://htmlmask.test/p.svg#m)"], spanGated: false, spanText: "span",
      placeholders: 14,
    }, "the allowed host's reference stands and loaded; a fragment reference is the page's own; an HTML element's paint attributes fetch nothing and are left alone (no request for htmlfill.test above)");
  });
});

test("one click on a placeholder restores the reference as written, the request follows, and every svg of that host in the document loads with it; the other hosts stay gated with no request", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    const { page } = h;
    await h.open();
    const before = h.foreign();
    // both waiters before the click: the two svgs of the host are restored by the one regate, so both requests leave together
    const fetched = Promise.all([page.waitForRequest("https://fill.test/p.svg", { timeout: 10000 }), page.waitForRequest("https://fill.test/q.svg", { timeout: 10000 })]);
    await page.locator('#romp-fileview [data-act="fv-load"][data-fv-host="fill.test"]').first().click();
    await fetched;
    await h.settle();
    const after = await page.evaluate(() => ({
      fill: (window as any).__paints("svg.px-fill"), fillGated: !!document.querySelector("#romp-fileview svg.px-fill")!.closest('[data-act="fv-load"]'),
      fill2: (window as any).__paints("svg.px-fill2"), fill2Gated: !!document.querySelector("#romp-fileview svg.px-fill2")!.closest('[data-act="fv-load"]'),
      fillShown: getComputedStyle(document.querySelector("#romp-fileview svg.px-fill")!).display !== "none",
      placeholders: document.querySelectorAll('#romp-fileview [data-act="fv-load"]').length,
      gatedLeft: document.querySelectorAll('#romp-fileview [data-fv-gated-fill], #romp-fileview [data-fv-gated-stroke], #romp-fileview [data-fv-gated-filter], #romp-fileview [data-fv-gated-clip-path], #romp-fileview [data-fv-gated-mask], #romp-fileview [data-fv-gated-marker-start], #romp-fileview [data-fv-gated-marker-mid], #romp-fileview [data-fv-gated-marker-end]').length,
    }));
    assert.deepEqual(after, {
      fill: ["rect fill=url(https://fill.test/p.svg#p)"], fillGated: false, fill2: ["rect fill=url(https://fill.test/q.svg#p)"], fill2Gated: false, fillShown: true,
      placeholders: 12, gatedLeft: 12,
    }, "both fill.test svgs restored in place and shown; twelve placeholders left, one moved-aside element each");
    const gained = h.foreign().filter((u) => !before.includes(u));
    assert.deepEqual(gained, ["https://fill.test/p.svg", "https://fill.test/q.svg"], "the clicked host's two references fetched, and nothing else: " + JSON.stringify(gained));
  });
});

test("a URL document is gated the same: no paint reference to an unlisted host leaves the page on open, github.com's does, and the click through the URL viewer's own delegate loads the host", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    const { page } = h;
    const control = page.waitForRequest("https://github.com/u/r/p.svg", { timeout: 15000 });
    await page.evaluate((u: string) => { (window as any).__rompProbe.openUrlView(u); }, URL_DOC);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 15000 });
    await control;
    await h.settle();
    assert.deepEqual(h.foreign(), ["https://github.com/u/r/p.svg", "https://github.com/u/r/raw/main/gh.png"], "github.com alone left the page");
    const gates: Gate[] = await page.evaluate(readGates);
    assert.deepEqual(gates.map((g) => [g.hosts, g.cls]), GATED.map((g) => [g[0], g[2]]), "the same fourteen placeholders as the file kind");
    const fetched = page.waitForRequest("https://stroke.test/p.svg", { timeout: 10000 });
    await page.click('#romp-fileview [data-act="fv-load"][data-fv-host="stroke.test"]');
    await fetched;
    await h.settle();
    assert.deepEqual(await page.evaluate(() => (window as any).__paints("svg.px-stroke")), ["rect fill=none", "rect stroke=url(https://stroke.test/p.svg#p)"], "restored as written");
    assert.equal(await page.evaluate(() => document.querySelectorAll('#romp-fileview [data-act="fv-load"]').length), 13);
  });
});

