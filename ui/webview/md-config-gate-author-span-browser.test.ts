// An author's `<span class="fv-gate">` around prose, over the REAL Files bundle in headless Chromium (figure-gate.ts;
// decision 8 of plans/markdown-viewer.md). The sanitizer keeps an author's `class`, so a note can wear the placeholder's
// class name on a span of its own prose; the slice's review round 1 moved everything the gate FINDS off the class (the
// placeholder by `data-act="fv-load"`, its label by `data-fv-label`, marks the sanitizer never lets through), and round 3
// found the sheets' hide rule still keyed on the class: `.fileview-md .fv-gate > :not([data-fv-label]) { display: none }`
// hid every child ELEMENT of the author's span, so bold, a link and code inside it vanished from the page while its bare
// text stayed. The hide rule keys on the placeholder's own mark now. The page's record is the DOM the viewer painted: the
// author's span keeps every child element shown and its text reads whole, and a real placeholder beside it still hides
// its media behind the label and fetches nothing until the click. The chrome on the author-writable class (the dashed
// box, the pointer) is the recorded design call and is not read here. Skips LOUDLY without a playwright browser (CI
// installs none). Synthetic values only: an invented note, TESTHOST paths, a placeholder sid, .test hosts.
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
const FILE_PATH = ROOT + "/docs/gate-span.md";
const NOTE = [
  "# Gate span", "",
  // the author's span inside a Markdown paragraph, with an element child of each inline kind
  'Author span: <span class="fv-gate">gate text <b>bold child</b> <a href="https://example.test/">link child</a> <code>code child</code> tail</span> after.', "",
  // a real placeholder beside it: a figure on an unlisted host
  '<p><img class="fx-remote" src="https://remote.test/img.png" alt="r" width="120" height="80"></p>', "",
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

type H = { page: any; open: () => Promise<void>; foreign: () => string[] };
/** A Files page with every request event logged; `open` posts the relay and awaits the rendered box. */
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
      if (u.pathname === "/file" && (u.searchParams.get("path") || "") === FILE_PATH) {
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    const open = async () => {
      await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [FILE_PATH, SID] as [string, string]);
      await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-md"), null, { timeout: 15000 });
      await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
    };
    const foreign = () => requests.filter((u) => !u.startsWith("http://romp.test/") && !u.startsWith("data:")).sort();
    await body({ page, open, foreign });
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
}

test("an author's span.fv-gate around prose shows every child element (bold, link, code) and its whole text, while the viewer's own placeholder beside it still hides its media behind the label", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (h) => {
    await h.open();
    const seen = await h.page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const author = Array.from(md.querySelectorAll("span.fv-gate")).find((s) => !s.hasAttribute("data-act")) as HTMLElement | undefined;
      const placeholder = md.querySelector('[data-act="fv-load"]') as HTMLElement | null;
      const shown = (el: Element) => getComputedStyle(el).display !== "none";
      // innerText omits a display:none child, so it is the rendered text; the span's inline-flex chrome (the recorded design
      // call on the author-writable class) makes innerText break between its items, so whitespace is folded before reading
      const rendered = (el: HTMLElement) => el.innerText.replace(/\s+/g, " ").trim();
      return {
        authorFound: !!author,
        authorChildren: author ? Array.from(author.children).map((c) => c.tagName.toLowerCase() + ":" + (shown(c) ? "shown" : "hidden") + ":" + c.textContent) : [],
        authorText: author ? rendered(author) : null,
        paragraphText: author ? rendered(author.parentElement as HTMLElement) : null,
        placeholder: placeholder ? {
          host: placeholder.getAttribute("data-fv-host"),
          media: Array.from(placeholder.children).filter((c) => !c.hasAttribute("data-fv-label")).map((c) => c.tagName.toLowerCase() + ":" + (shown(c) ? "shown" : "hidden")),
          label: Array.from(placeholder.children).filter((c) => c.hasAttribute("data-fv-label")).map((c) => (shown(c) ? "shown" : "hidden") + ":" + c.textContent),
        } : null,
      };
    });
    assert.equal(seen.authorFound, true, "the author's span is on the page, its class kept by the sanitizer, with no placeholder mark");
    assert.deepEqual(seen.authorChildren, ["b:shown:bold child", "a:shown:link child", "code:shown:code child"], "every child element of the author's span is shown");
    assert.equal(seen.authorText, "gate text bold child link child code child tail", "the span's text reads whole");
    assert.equal(seen.paragraphText, "Author span: gate text bold child link child code child tail after.", "the paragraph reads whole");
    assert.deepEqual(seen.placeholder, { host: "remote.test", media: ["img:hidden"], label: ["shown:Image from remote.test. Click to load."] }, "the viewer's placeholder still hides its media and shows its label");
    assert.deepEqual(h.foreign().filter((u) => u.includes("remote.test")), [], "nothing left the page for the gated figure");
  });
});
