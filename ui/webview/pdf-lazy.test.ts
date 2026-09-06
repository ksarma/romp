// The PDF renderer chunk (plans/file-review.md, Slice 4): pdf.js as its OWN on-demand bundle plus a worker
// asset beside it, in the editor chunk's pattern (editor-lazy.test.ts is the model). The load-bearing
// constraints: the main bundles stay byte-stable (no main-bundle source imports the chunk or pdfjs-dist —
// lazy discipline), the worker rides the chunk's own URL (same directory, same ?v= token), the size cap
// refuses BY NAME before pdf.js sees a byte, and each page's shell is a positioned, numbered element a
// later overlay can attach to. Pure units run the real helpers and render()'s two refusals; the shells and the
// draws are pinned at source here and EXECUTED in pdf-lazy-render.test.ts (makeRender over pdf.js's legacy build
// under Node, the built chunk in a browser). pdf.js loads lazily below, so a Node under its floor fails one named
// test here instead of killing the file at import.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { PDF_MAX_BYTES, pdfCapMessage } from "./pdf-cap";   // pure; file-view.ts imports the same two (pinned below)

// pdf.js, and the chunk whose module imports it, load on first use rather than at import: pdfjs-dist 6 reads
// `Iterator.prototype` while its module initialises and calls Promise.withResolvers, so a top-level import on a
// Node below its floor killed this whole file with a ReferenceError before any test ran (the 2026-09-06 review).
// Now the pins run on any Node, the floor test names the floor, and the tests that execute pdf.js skip by name.
const chunk = () => require("./pdf-chunk") as typeof import("./pdf-chunk");
const pdfjs = () => require("pdfjs-dist") as typeof import("pdfjs-dist");
const PDFJS_PKG = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), "node_modules", "pdfjs-dist", "package.json"), "utf8"));
/** Whether `version` satisfies an engines.node range of `>=a.b.c` bounds joined by `||` (pdfjs-dist's shape; any other is loud). */
function meetsFloor(version: string, range: string): boolean {
  const v = version.split(".").map(Number);
  return range.split("||").some((clause) => {
    const m = /^\s*>=\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?\s*$/.exec(clause);
    if (!m) throw new Error(`engines.node clause ${JSON.stringify(clause.trim())} is not a >= bound — extend meetsFloor`);
    const floor = [Number(m[1]), Number(m[2] || 0), Number(m[3] || 0)];
    for (let i = 0; i < 3; i++) if (v[i] !== floor[i]) return v[i] > floor[i];
    return true;
  });
}
const FLOOR = String(PDFJS_PKG.engines?.node || "");
const FLOOR_OK = !!FLOOR && meetsFloor(process.versions.node, FLOOR);
/** A test that executes pdf.js (directly, or through the chunk's module): below the floor it skips by name, so the
 *  floor test is the one failure to read. */
const pdfjsTest = (name: string, fn: () => void | Promise<void>) =>
  test(name, FLOOR_OK ? {} : { skip: `pdf.js cannot load on Node ${process.versions.node} (pdfjs-dist needs ${FLOOR}) — see the floor test` }, fn);

const ROOT = path.resolve(process.cwd(), "..");
const W = (f: string) => fs.readFileSync(path.join(ROOT, "ui", "webview", f), "utf8");
const CHUNK = W("pdf-chunk.ts");
const VIEW = W("file-view.ts");
const ESBUILD = fs.readFileSync(path.resolve(process.cwd(), "esbuild.js"), "utf8");
const PKG = JSON.parse(fs.readFileSync(path.resolve(process.cwd(), "package.json"), "utf8"));
const CI = fs.readFileSync(path.join(ROOT, ".github", "workflows", "ci.yml"), "utf8");
const INSTALL = fs.readFileSync(path.join(ROOT, "docs", "install.md"), "utf8");

/** Code lines only: a comment may NAME the dependency (the header does); an import may not. */
const code = (s: string) => s.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
/** A container render() must never reach for: every property read throws. */
const untouchable = () => new Proxy({}, {
  get(_t, k) { throw new Error("render() touched the container (" + String(k) + ") for bytes it should have refused"); },
}) as unknown as HTMLElement;

// ── the Node floor: pdf.js's, and with the chunk in the suite, the extension tests' ─────────────────

test("this Node meets pdfjs-dist's declared floor — the extension suite's floor since the PDF chunk (CI pins Node 22)", () => {
  assert.ok(FLOOR, "pdfjs-dist declares engines.node");
  assert.ok(FLOOR_OK,
    `Node ${process.versions.node} is below pdfjs-dist ${PDFJS_PKG.version}'s floor (engines.node ${JSON.stringify(FLOOR)}): pdf.js 6 reads ` +
    "Iterator.prototype at import and calls Promise.withResolvers, so its tests here, pdf-lazy-render.test.ts's node leg and " +
    "tools/pdf-smoke.test.mjs cannot run on it. CI runs Node 22 (.github/workflows/ci.yml).");
  // the check itself, against the range's shape: at the bound, under it, on the next major, on the second clause
  assert.equal(meetsFloor("22.13.0", ">=22.13.0 || >=24"), true);
  assert.equal(meetsFloor("22.12.9", ">=22.13.0 || >=24"), false);
  assert.equal(meetsFloor("23.0.0", ">=22.13.0 || >=24"), true);
  assert.equal(meetsFloor("24.0.0", ">=22.13.0 || >=24"), true);
  assert.equal(meetsFloor("20.19.0", ">=22.13.0 || >=24"), false);
  assert.throws(() => meetsFloor("22.0.0", "^22"), /not a >= bound/, "a range shape the check does not read is loud, not a pass");
});

// ── lazy discipline: two entries of their own, reached only through the window global ────────────

test("the chunk and its worker are esbuild entries; the worker is emitted as .js for the kernel's suffix-typed /dist route", () => {
  assert.match(ESBUILD, /"\.\.\/ui\/webview\/pdf-chunk\.ts"/);
  assert.match(ESBUILD, /\{ in: "node_modules\/pdfjs-dist\/build\/pdf\.worker\.mjs", out: "pdf-worker" \}/,
    "the worker is its own entry with a .js output name — a .mjs would be served as text/plain and refused by the module Worker");
  // the dependency those entries resolve, in the 6.x line the chunk is written against
  assert.match(PKG.devDependencies["pdfjs-dist"], /^\^6\./);
});

test("no main-bundle source imports pdfjs-dist or the chunk — the contract is the window global", () => {
  assert.match(CHUNK, /if \(typeof window !== "undefined"\) \(window as any\)\.__rompPdf = \{ render, DEFAULT_MAX_BYTES \};/);
  const dir = path.join(ROOT, "ui", "webview");
  const sources = fs.readdirSync(dir).filter((f) => /\.(ts|js)$/.test(f) && !f.endsWith(".test.ts") && f !== "pdf-chunk.ts");
  for (const must of ["file-view.ts", "file-comments.ts", "render.ts", "feed.ts", "files.ts", "preview.ts", "editor-chunk.ts"]) {
    assert.ok(sources.includes(must), must + " is among the scanned sources");
  }
  for (const f of sources) {
    assert.doesNotMatch(code(W(f)), /pdfjs-dist|from "\.\/pdf-chunk"|require\("\.\/pdf-chunk"\)/,
      f + " must not import pdf.js or the chunk — an import would drag pdf.js into a main bundle");
  }
  // the extension host neither
  const src = path.resolve(process.cwd(), "src");
  for (const f of fs.readdirSync(src).filter((f) => f.endsWith(".ts") && !f.endsWith(".test.ts"))) {
    assert.doesNotMatch(code(fs.readFileSync(path.join(src, f), "utf8")), /pdfjs-dist/, "src/" + f);
  }
  // …and this test's own imports are fine: tests bundle to out-tests, never to dist.
});

// ── the worker's URL: the chunk's own, with the worker's name — same dir, same ?v= ────────────────

pdfjsTest("the worker's URL is the chunk's own script src with pdf-worker.js for pdf-chunk.js, token and all", () => {
  const { workerUrlFor } = chunk();
  const K = "http://TESTHOST:29855/dist/", V = "?v=1725300000";
  assert.equal(workerUrlFor(K + "pdf-chunk.js" + V), K + "pdf-worker.js" + V);
  const R = "https://file+.vscode-resource.vscode-cdn.net/ext/dist/";
  assert.equal(workerUrlFor(R + "pdf-chunk.js"), R + "pdf-worker.js");
  assert.equal(workerUrlFor(K + "files.js" + V), null, "another bundle's tag is no basis for the worker's URL");
  assert.equal(workerUrlFor(""), null);
  // set at LOAD from the chunk's own tag: document.currentScript while the classic script runs, else the
  // tag whose src names the chunk; then pdf.js is told once, before any render()
  assert.match(CHUNK, /const cur = document\.currentScript as HTMLScriptElement \| null;/);
  assert.match(CHUNK, /\.find\(\(u\) => \/\\\/pdf-chunk\\\.js\/\.test\(u\)\) \|\| null;/);
  assert.match(CHUNK, /if \(url\) pdfjsLib\.GlobalWorkerOptions\.workerSrc = url;/);
});

pdfjsTest("no worker URL is a named refusal of render(), not pdf.js's later error", async () => {
  const { GlobalWorkerOptions } = pdfjs();
  const { render } = chunk();
  const before = GlobalWorkerOptions.workerSrc;      // under node pdf.js points it at its own worker file
  GlobalWorkerOptions.workerSrc = "";
  try {
    await assert.rejects(render(new ArrayBuffer(8), untouchable()), /could not locate its worker/);
  } finally {
    GlobalWorkerOptions.workerSrc = before;
  }
});

// ── the loader the wiring copies: executed against each hosting page's script tags ───────────────

pdfjsTest("the loader in the API doc derives the chunk URL from every hosting page's bundle, with the editor loader's own literal", () => {
  const { workerUrlFor } = chunk();
  const find = CHUNK.match(/^\/\/\s+\.map\(\(n\) => \(n as HTMLScriptElement\)\.src\)\.find\(\(u\) => (\/[^\n]+?\/)\.test\(u\)\);$/m);
  const repl = CHUNK.match(/^\/\/\s+sc\.src = self\.replace\((\/[^\n]+?\/), "\/pdf-chunk\.js"\);$/m);
  assert.ok(find && repl, "the doc's loader carries the find and replace literals");
  const findRe = new Function("return " + find![1])() as RegExp;
  const replRe = new Function("return " + repl![1])() as RegExp;
  assert.equal(String(findRe), String(replRe), "one pattern finds the bundle and rewrites it");
  // the literal file-view's editor loader uses, so the two loaders cannot drift apart
  const viewFind = VIEW.match(/\.find\(\(u\) => (\/[^\n]+?\/)\.test\(u\)\)/);
  assert.ok(viewFind, "file-view's editor loader is where this pattern comes from");
  assert.equal(find![1], viewFind![1]);
  const derive = (srcs: string[]) => { const self = srcs.find((u) => findRe.test(u)); return self ? self.replace(replRe, "/pdf-chunk.js") : null; };
  const K = "http://TESTHOST:29855/dist/", V = "?v=1725300000";
  assert.equal(derive([K + "federation.js" + V, K + "files.js" + V]), K + "pdf-chunk.js" + V, "the Files pane (_files_page)");
  assert.equal(derive([K + "federation.js" + V, K + "feed.js" + V]), K + "pdf-chunk.js" + V, "the feed (_feed_page)");
  assert.equal(derive([K + "federation.js" + V, K + "palette-main.js" + V, K + "render.js" + V]), K + "pdf-chunk.js" + V, "the chat (_chat_page)");
  assert.equal(derive([K + "federation.js" + V]), null, "federation.js alone is no hosting bundle");
  // the derived chunk URL then yields the worker's: one ?v= token reaches the page, the chunk and the worker
  assert.equal(workerUrlFor(derive([K + "files.js" + V])!), K + "pdf-worker.js" + V);
  // the snippet resolves through the global, and a failed load clears the latch so a later open retries
  assert.match(CHUNK, /^\/\/\s+if \(w\.__rompPdf\) return res\(w\.__rompPdf\);$/m);
  assert.match(CHUNK, /^\/\/\s+sc\.onerror = \(\) => \{ pdfChunk = null; rej\(/m);
});

// ── the wiring (file-view.ts, Slice 4): the doc's loader, copied — same derivation as the editor's ─

test("file-view loads the PDF chunk exactly as it loads the editor chunk: the same find literal, /pdf-chunk.js in place of /editor-chunk.js, the global first, the latch cleared on failure", () => {
  const code = (src: string) => src.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
  const live = code(VIEW);
  // two loaders, one derivation: the editor's literal and the PDF's are the same regex, so the Files pane, the feed and
  // the chat (and a rebuilt kernel's ?v=) reach both chunks or neither
  const finds = live.match(/\.find\(\(u\) => (\/[^\n]+?\/)\.test\(u\)\)/g) || [];
  assert.equal(finds.length, 2, "the editor loader's derivation and the PDF loader's");
  assert.equal(finds[0], finds[1]);
  assert.match(live, /sc\.src = self\.replace\(\/\\\/\(render\|feed\|files\)\\\.js\/, "\/editor-chunk\.js"\);/);
  assert.match(live, /sc\.src = self\.replace\(\/\\\/\(render\|feed\|files\)\\\.js\/, "\/pdf-chunk\.js"\);/);
  assert.match(live, /if \(w\.__rompPdf\) return res\(w\.__rompPdf\);/, "the global first: a chunk already on the page is not fetched twice");
  assert.match(live, /sc\.onerror = \(\) => \{ pdfChunk = null; rej\(new Error\("the PDF renderer failed to load"\)\); \};/, "a failed load clears the latch so the next open retries");
  assert.match(live, /if \(!self\) return rej\(new Error\("no bundle script tag to derive the PDF chunk URL from"\)\);/);
  assert.match(live, /p \? res\(p\) : rej\(new Error\("PDF chunk loaded but did not register"\)\)/);
  // the structural type is inline: `import type` from the chunk would still be an import for the discipline pin above
  assert.match(live, /let pdfChunk: Promise<\{ render: \(bytes: ArrayBuffer, container: HTMLElement, opts\?: object\) =>\n\s*Promise<\{ pages: number; dispose\(\): void \}> \}> \| null = null;/);
  // the branch: pages only while the Comments panel is open (the seam's aside() is the event), the frame otherwise
  assert.match(live, /if \(isPdf && asideOpen\) \{ showPdfPages\(\); return; \}/);
  assert.match(live, /if \(isPdf && objUrl !== null && asideOpen !== was\) renderBody\(\);/);
  // the bytes are the fetch's own blob, handed to render() with the cap; the loader precedes the pages; both exits dispose
  assert.match(live, /Promise\.all\(\[pdfChunkLoad\(\), blob\.arrayBuffer\(\)\]\)/);
  assert.match(live, /maxBytes: PDF_MAX_BYTES,/);
  assert.match(live, /body\.replaceChildren\(wait, host\);/, "the loader and the chunk's host, the host laid out before render() fits pages to it");
  assert.match(live, /closeHooks\.push\(dropPdf\);/);
  // the fallbacks, all through one function, all the frame with a notice in the error dress ABOVE it. A frame already
  // showing these bytes is kept in place and the notice heads its column (a rebuilt frame reloads the document and
  // loses the reader's place — the round-2 review); with no frame to keep, a fresh one is built with the notice first.
  assert.match(live, /if \(blob\.size > PDF_MAX_BYTES\) \{ fallback\(pdfCapMessage\(blob\.size, PDF_MAX_BYTES\)\); return; \}/, "the cap refuses before the chunk is fetched");
  assert.match(live, /\.catch\(\(err\) => fallback\(String\(err && \(err as Error\)\.message \|\| err\)\)\);/, "a chunk load failure or a render rejection");
  assert.match(live, /if \(h\.pages === 0\) \{ h\.dispose\(\); fallback\("this PDF has no pages"\); return; \}/, "a page-less document is a refusal too, never a blank root");
  assert.match(live, /note\.textContent = why \+ " — showing the browser's PDF viewer instead; comments on the whole file still work\.";/);
  assert.match(live, /const note = el\("div", "fileview-err"\);/);
  assert.match(live, /col\.prepend\(note\);/, "a kept frame takes the notice above it, in place");
  assert.match(live, /const fall = pdfBlock\(url, path\);[^\n]*\n\s*fall\.prepend\(note\);[^\n]*\n\s*aimFrame\(fall\);[^\n]*\n\s*body\.replaceChildren\(fall\);/,
    "no frame to keep: a fresh frame, the notice first, aimed at the reader's page before it joins the document");
});

pdfjsTest("file-view's cap is the chunk's default, and its refusal is the chunk's capMessage word for word", () => {
  const { DEFAULT_MAX_BYTES, capMessage } = chunk();
  assert.match(VIEW, /import \{ PDF_MAX_BYTES, pdfCapMessage \} from "\.\/pdf-cap";/, "file-view reads the cap from the pure module, not from the chunk");
  assert.equal(PDF_MAX_BYTES, DEFAULT_MAX_BYTES);
  assert.equal(pdfCapMessage(26 * 1024 * 1024, PDF_MAX_BYTES), capMessage(26 * 1024 * 1024, DEFAULT_MAX_BYTES));
  assert.equal(pdfCapMessage(40.5 * 1024 * 1024, PDF_MAX_BYTES), "this PDF is 40.5 MB, over the 25.0 MB cap for rendering pages in the viewer");
});

// ── the cap: refused by name, before pdf.js or the container sees anything ───────────────────────

pdfjsTest("bytes over the cap are refused with the size AND the cap in the message, before anything is touched", async () => {
  const { render, capMessage, fmtBytes, DEFAULT_MAX_BYTES } = chunk();
  assert.equal(DEFAULT_MAX_BYTES, 25 * 1024 * 1024);
  await assert.rejects(render(new ArrayBuffer(101), untouchable(), { maxBytes: 100 }),
    (e: unknown) => e instanceof Error && /101 bytes/.test(e.message) && /100 bytes/.test(e.message));
  await assert.rejects(render(new ArrayBuffer(26 * 1024 * 1024), untouchable()), /26\.0 MB, over the 25\.0 MB cap/);
  assert.equal(capMessage(26 * 1024 * 1024, DEFAULT_MAX_BYTES),
    "this PDF is 26.0 MB, over the 25.0 MB cap for rendering pages in the viewer");
  assert.equal(fmtBytes(512), "512 bytes");
  assert.equal(fmtBytes(2048), "2 KB");
  assert.equal(fmtBytes(1.5 * 1024 * 1024), "1.5 MB");
  // strictly over: a file exactly at the cap renders. The check precedes the worker check and getDocument.
  assert.match(CHUNK, /if \(bytes\.byteLength > cap\) throw new Error\(capMessage\(bytes\.byteLength, cap\)\);\n\s*if \(!pdfjsLib\.GlobalWorkerOptions\.workerSrc\) \{/);
  assert.match(CHUNK, /pdfjsLib\.getDocument\(\{ data: new Uint8Array\(bytes\.slice\(0\)\) \}\)/,
    "a copy goes to pdf.js — it transfers the buffer to the worker, which would detach the caller's");
});

pdfjsTest("the backing store follows the display's pixel ratio until a page would exceed the canvas budget", () => {
  const { backingScale, MAX_CANVAS_PIXELS } = chunk();
  assert.equal(backingScale(800, 1000, 2), 2);
  assert.equal(backingScale(800, 1000, 1), 1);
  assert.equal(backingScale(800, 1000, 0), 1, "a missing ratio is 1");
  const s = backingScale(8000, 10000, 2);
  assert.ok(s < 1, "a poster page draws under the budget, softer rather than not at all");
  assert.ok(Math.abs(8000 * s * 10000 * s - MAX_CANVAS_PIXELS) < 1);
  assert.equal(MAX_CANVAS_PIXELS, 16 * 1024 * 1024);
});

// ── the page shells: a positioned, numbered wrapper per page around one canvas, drawn lazily ─────

test("each page is a positioned, 1-based-numbered wrapper (the overlay's anchor) around one width-fit canvas", () => {
  assert.match(CHUNK, /root\.className = "fileview-pdf";/);
  assert.match(CHUNK, /wrap\.className = "fileview-pdf-page";/);
  assert.match(CHUNK, /wrap\.dataset\.page = String\(i\);/);
  assert.match(CHUNK, /wrap\.style\.position = "relative";/, "load-bearing, so inline rather than the sheet's");
  assert.match(CHUNK, /wrap\.style\.aspectRatio = aspect;/, "the shell has the page's extent before any pixel is drawn");
  assert.match(CHUNK, /canvas\.className = "fileview-pdf-canvas";/);
  assert.match(CHUNK, /canvas\.dataset\.page = String\(i\);/);
  assert.match(CHUNK, /canvas\.style\.width = "100%";/);
  // the tree, not just the names: the canvas INSIDE its wrapper, the wrapper in the root — file-comments' regionImages()
  // looks for the canvas in each wrapper pdfPages() finds, and a canvas hung on the root (or a wrapper never attached)
  // leaves every page without an overlay and no error. Named here; executed with the panel's own lookups, on real
  // pages, in pdf-lazy-render.test.ts.
  assert.match(CHUNK, /wrap\.appendChild\(canvas\);\n\s*root\.appendChild\(wrap\);/,
    "canvas into wrapper, wrapper into root — the shape regionImages() reads");
  assert.match(CHUNK, /for \(let i = 1; i <= n; i\+\+\) \{/, "pages are numbered from 1, as PDFs and the wire's target.page do");
  assert.match(CHUNK, /const vp = proxy\.getViewport\(\{ scale: cssW \/ base\.width \}\);/,
    "width-fit: the scale is the root's width over the page's natural width");
  // the draw is STAGED: pdf.js draws into a canvas off the DOM and the page's canvas takes the finished bitmap in one step
  // (pdf-chunk-staged-draw.test.ts executes it); the viewport and the ratio transform are the same as ever
  assert.match(CHUNK, /proxy\.render\(\{ canvas: stage, viewport: vp, transform: dpr === 1 \? undefined : \[dpr, 0, 0, dpr, 0, 0\] \}\)/);
  assert.match(CHUNK, /opts\.onPage\?\.\(\{ index: p\.index, canvas: p\.canvas, width: vp\.width, height: vp\.height \}\);/,
    "onPage: the 1-based index, the page's own canvas, and its CSS size after every draw");
});

test("pages draw lazily through an IntersectionObserver, eagerly without one, and a far page gives its bitmap back", () => {
  assert.match(CHUNK, /if \(typeof IntersectionObserver !== "undefined"\) \{/);
  assert.match(CHUNK, /\} else \{\n\s*for \(const p of pages\) p\.visible = true;\n\s*\}/, "no observer: every page is visible, so every page draws");
  assert.match(CHUNK, /if \(io\) for \(const p of pages\) io\.observe\(p\.wrap\);\n\s*else for \(const p of pages\) want\(p\);/);
  assert.match(CHUNK, /if \(p\.visible\) want\(p\); else drop\(p\);/, "leaving the observer's window releases the bitmap; the wrapper keeps the extent");
  assert.match(CHUNK, /rootMargin: "100% 0px"/, "a viewport of margin: the next page is drawn before it shows");
  // one draw at a time, and a cancelled draw is not an error
  assert.match(CHUNK, /const p = queue\.shift\(\)!;/);
  assert.match(CHUNK, /e instanceof pdfjsLib\.RenderingCancelledException/);
  // the first page is drawn before the promise resolves, so the caller removes its loader over a drawn page — and a
  // first page pdf.js cannot draw rejects with nothing left in the container and no live worker
  assert.match(CHUNK, /pages\[0\]\.visible = true;\n\s*try \{ await paint\(pages\[0\]\); \} catch \(e\) \{ io\?\.disconnect\(\); ro\?\.disconnect\(\); void task\.destroy\(\); root\.remove\(\); throw e; \}/);
  assert.match(CHUNK, /\} catch \(e\) \{ void task\.destroy\(\); throw e; \}/, "a document whose first page cannot be read releases the worker too");
  assert.match(CHUNK, /byEl\.set\(wrap, p\);\n\s*\}\n\s*container\.appendChild\(root\);/,
    "the root joins the container once the shells exist, before the first draw reads its width");
  // dispose releases everything the render made
  assert.match(CHUNK, /io\?\.disconnect\(\); ro\?\.disconnect\(\);/);
  assert.match(CHUNK, /void task\.destroy\(\);[^\n]*\n\s*root\.remove\(\);/,
    "the loading task's destroy releases the document and its worker (pdf.js 6 has none on the document proxy)");
});

// ── the dependency's license and smoke test: named in the install doc, run where it is installed ─

test("the license is named beside romp's own, and CI runs the smoke test in the job that installs the dependency", () => {
  assert.match(INSTALL, /pdf\.js[^\n]*\n?[^\n]*Apache-2\.0/, "docs/install.md names pdf.js and its Apache-2.0 license");
  assert.match(INSTALL, /Romp is \[Apache-2\.0\]/);
  assert.match(CI, /run: node --test tools\/pdf-smoke\.test\.mjs/);
  assert.ok(fs.existsSync(path.join(ROOT, "tools", "pdf-smoke.test.mjs")));
  // the smoke test skips by name where node_modules is absent (the shell job) rather than failing
  const SMOKE = fs.readFileSync(path.join(ROOT, "tools", "pdf-smoke.test.mjs"), "utf8");
  assert.match(SMOKE, /\{ skip: SKIP \}/);
  assert.match(SMOKE, /run `npm ci` in vscode-extension/);
});
