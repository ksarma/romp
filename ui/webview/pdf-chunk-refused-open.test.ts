// The PDF chunk's REFUSED OPEN releases pdf.js's Worker (plans/file-review.md, Slice 4; the review of 2026-09-06).
// pdf.js's getDocument starts a Worker per call (the chunk sets workerSrc, never a shared port), and its own failure
// path only rejects the loading task — nothing terminates the Worker but PDFDocumentLoadingTask.destroy(). render()
// awaited `task.promise` with no handler, so a file pdf.js will not open (corrupt bytes, a password) rejected render()
// and left that Worker running; the caller gets only the rejection's message and has no handle to release it with,
// and it renders again on every opening of the Comments panel, so N openings of the panel on such a file held N
// Workers (several MB each) for the tab's life. The page-cap, first-page-failure and dispose paths already destroyed
// the task; this one now does too.
//
// Three legs. STAND-IN: makeRender over a fake pdf.js whose getDocument rejects — render() rejects with pdf.js's
// message, the task is destroyed exactly once, the container is never touched, nothing is created. LEGACY pdf.js
// (the build it supports under Node) over garbage bytes: the loading task pdf.js hands back is destroyed and its
// worker released once render() has rejected. CHROMIUM (skips by name without playwright's chromium): the built
// chunk as shipped; three refused opens leave the page with no live Worker, a valid open holds one and dispose()
// releases it, a page-count refusal holds none. Fixtures are synthetic: invented bytes, blank pages, TESTHOST.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { makeRender, DEFAULT_MAX_PAGES, pageCapMessage, type PdfLib } from "./pdf-chunk";

// ── a fake pdf.js whose document does not open ──────────────────────────────────────────────────

interface FakeLib { lib: PdfLib; calls: { getDocument: number; destroyed: number; destroyedAfterReject: boolean } }
function refusingLib(message: string): FakeLib {
  const calls = { getDocument: 0, destroyed: 0, destroyedAfterReject: false };
  let rejected = false;
  class Cancelled extends Error {}
  const lib = {
    GlobalWorkerOptions: { workerSrc: "http://TESTHOST:29855/dist/pdf-worker.js" },
    RenderingCancelledException: Cancelled,
    getDocument: () => {
      calls.getDocument++;
      return {
        // the refusal arrives a tick later, as a worker's answer does
        promise: new Promise<never>((_res, rej) => setTimeout(() => { rejected = true; rej(new Error(message)); }, 1)),
        destroy: async () => { calls.destroyed++; calls.destroyedAfterReject = rejected; },
      };
    },
  };
  return { lib: lib as unknown as PdfLib, calls };
}
let created = 0;
const el = (tag: string) => { created++; return { tagName: tag.toUpperCase(), style: {}, dataset: {}, children: [], appendChild() {}, remove() {} }; };
/** A container render() must never reach for on a document it refuses: every property read throws. */
const untouchable = () => new Proxy({}, {
  get(_t, k) { throw new Error("render() touched the container (" + String(k) + ") for a document pdf.js refused"); },
}) as unknown as HTMLElement;
async function until(cond: () => boolean, what: string): Promise<void> {
  for (let i = 0; i < 2000; i++) { if (cond()) return; await new Promise((r) => setTimeout(r, 1)); }
  assert.fail("timed out waiting for " + what);
}

beforeEach(() => {
  (globalThis as any).document = { createElement: el };
  delete (globalThis as any).IntersectionObserver;
  delete (globalThis as any).ResizeObserver;
  created = 0;
});

test("a document pdf.js will not open rejects render() with pdf.js's message, and the loading task — the Worker's only owner — is destroyed once, after the refusal, with nothing created and the container untouched", async () => {
  for (const message of ["Invalid PDF structure.", "No password given"]) {
    created = 0;
    const { lib, calls } = refusingLib(message);
    await assert.rejects(makeRender(lib)(new ArrayBuffer(16), untouchable()), (e: unknown) => e instanceof Error && e.message === message, "pdf.js's own words reach the caller");
    assert.equal(calls.getDocument, 1);
    await until(() => calls.destroyed >= 1, "the loading task's destroy");
    assert.equal(calls.destroyed, 1, "destroyed exactly once: the Worker pdf.js started for this open is released (nothing else ever terminates it)");
    assert.ok(calls.destroyedAfterReject, "destroyed in response to the refusal, not before it");
    assert.equal(created, 0, "no root, no shell");
  }
});

// ── the same against pdf.js's legacy build: the task it hands back is destroyed and its worker released ──

const NODE_MODULES = path.resolve(process.cwd(), "node_modules");
const LEGACY = path.join(NODE_MODULES, "pdfjs-dist", "legacy", "build", "pdf.mjs");
const LEGACY_WORKER = path.join(NODE_MODULES, "pdfjs-dist", "legacy", "build", "pdf.worker.mjs");
const SKIP_LEGACY = fs.existsSync(LEGACY) && fs.existsSync(LEGACY_WORKER)
  ? false
  : "pdfjs-dist's legacy build is not installed under vscode-extension/node_modules (run `npm ci` there); the real-pdf.js refused-open test did not run";

/** Bytes that are not a PDF: no header, no object, no trailer — pdf.js refuses them as an invalid structure. */
const notAPdf = () => {
  const b = Buffer.from("these bytes are a text file someone renamed to .pdf, and there is no object in them\n".repeat(8), "latin1");
  return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength);
};

test("pdf.js (legacy build) refuses bytes that are not a PDF: render() rejects with pdf.js's message, and the loading task is destroyed and its worker released", { skip: SKIP_LEGACY }, async () => {
  const legacy = (await import(pathToFileURL(LEGACY).href)) as unknown as PdfLib;
  legacy.GlobalWorkerOptions.workerSrc = pathToFileURL(LEGACY_WORKER).href;   // node: pdf.js runs its parser on the main thread from this file
  // the same pdf.js, with every loading task it hands render() kept, so the test can read what became of it
  const tasks: Array<{ destroyed: boolean; _worker: unknown }> = [];
  const spy: PdfLib = {
    GlobalWorkerOptions: legacy.GlobalWorkerOptions,
    RenderingCancelledException: legacy.RenderingCancelledException,
    getDocument: ((src: unknown) => { const t = (legacy.getDocument as (s: unknown) => unknown)(src); tasks.push(t as { destroyed: boolean; _worker: unknown }); return t; }) as PdfLib["getDocument"],
  };
  const warn = console.warn;
  console.warn = () => {};
  try {
    await assert.rejects(makeRender(spy)(notAPdf(), untouchable()), (e: unknown) => {
      assert.match(String((e as Error).message), /Invalid PDF structure/, "pdf.js's InvalidPDFException text; if pdf.js reworded it, re-anchor this pin — the release below is the point");
      return true;
    });
    assert.equal(tasks.length, 1, "one loading task for the one open");
    assert.equal(created, 0, "nothing of the chunk's was made");
    await until(() => tasks[0].destroyed && tasks[0]._worker === null, "the loading task's destroy to finish (it terminates the worker last)");
    assert.equal(tasks[0].destroyed, true, "pdf.js's own flag: the task was destroyed");
    assert.equal(tasks[0]._worker, null, "…and released its worker; before the fix this held a live PDFWorker for the tab's life");
  } finally { console.warn = warn; }
});

// ── in Chromium: the built chunk, refused opens, and the page's live Workers ────────────────────

const PKG = process.cwd();                                   // vscode-extension, where npm test runs
const ROOT = path.resolve(PKG, "..");
const OUT = path.join(PKG, "out-tests", "pdf-chunk-refused-open");
const req = createRequire(path.join(PKG, "package.json"));   // runtime requires: esbuild must not bundle playwright
let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the refused-open browser test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the refused-open browser test did not run";
}

/** A PDF from its objects, with a correct xref (the generator the other chunk tests copy). */
function pdfOf(objs: string[]): Buffer {
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((body, i) => { offsets.push(Buffer.byteLength(out, "latin1")); out += `${i + 1} 0 obj\n${body}\nendobj\n`; });
  const xref = Buffer.byteLength(out, "latin1");
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offsets) out += `${String(o).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, "latin1");
}
const PAGE = (parent: number) => `<< /Type /Page /Parent ${parent} 0 R /MediaBox [0 0 612 792] >>`;
/** Two blank US-letter pages. */
const twoPages = () => pdfOf(["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>", PAGE(2), PAGE(2)]);
/** Two real pages under a page tree declaring `count` (pdf-chunk-page-cap.test.ts's hostile tree): opens, then the cap refuses it. */
const hostilePdf = (count: number) => pdfOf([
  "<< /Type /Catalog /Pages 2 0 R >>",
  `<< /Type /Pages /Kids [3 0 R 4 0 R] /Count ${count} >>`,
  `<< /Type /Pages /Parent 2 0 R /Kids [5 0 R] /Count ${count - 1} >>`,
  PAGE(2),
  PAGE(3),
]);

async function buildChunk(): Promise<void> {
  await req("esbuild").build({
    entryPoints: [
      path.join(ROOT, "ui", "webview", "pdf-chunk.ts"),
      { in: path.join(PKG, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"), out: "pdf-worker" },
    ],
    nodePaths: [path.join(PKG, "node_modules")],
    bundle: true, format: "iife", platform: "browser", target: "es2020", outdir: OUT, logLevel: "silent",
  });
}
const HTML = `<!doctype html><html><head><meta charset="utf-8"></head><body>
<div class="fileview"><div class="fileview-body" id="body" style="overflow:auto;height:600px;width:700px"><div class="fileview-pdfhost" id="host"></div></div></div>
<script src="/dist/pdf-chunk.js?v=1725300000"></script>
</body></html>`;

test("in Chromium: a refused open leaves no live Worker behind — three in a row leave none; a valid open holds one and dispose() releases it; a page-count refusal holds none", { skip: SKIP }, async () => {
  await buildChunk();
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => errors.push("pageerror: " + e.message));
    await page.route("http://TESTHOST/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: HTML });
      const f = path.join(OUT, path.basename(u.pathname));
      if (u.pathname.startsWith("/dist/") && fs.existsSync(f)) return route.fulfill({ contentType: "application/javascript", body: fs.readFileSync(f) });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://TESTHOST/view.html");
    await page.waitForFunction(() => !!(window as any).__rompPdf, null, { timeout: 10000 });
    assert.equal(page.workers().length, 0, "no Worker before any open");

    /** render() in the page; resolves to the page count, or to the rejection's message prefixed "rejected: ". */
    const open = (b64: string) => page.evaluate(async (b64: string) => {
      const bin = atob(b64); const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const w = window as any;
      try {
        const h = await w.__rompPdf.render(u8.buffer, document.getElementById("host"));
        w.__h = h;
        return "pages: " + h.pages;
      } catch (e) { return "rejected: " + (e as Error).message; }
    }, b64);
    /** The Worker count settling at `n` (pdf.js terminates its Worker at the end of an async destroy). */
    const workersSettleAt = async (n: number, what: string) => {
      for (let i = 0; i < 500; i++) { if (page.workers().length === n) return; await new Promise((r) => setTimeout(r, 10)); }
      assert.fail(`${what}: expected ${n} live Worker(s), the page has ${page.workers().length}`);
    };
    const hostChildren = () => page.evaluate(() => document.getElementById("host")!.children.length);

    // ── three refused opens of bytes that are not a PDF: each rejects with pdf.js's message and holds no Worker
    const garbage = Buffer.from("not a PDF at all, whatever the extension says\n".repeat(8), "latin1").toString("base64");
    for (let i = 1; i <= 3; i++) {
      const r = await open(garbage);
      assert.match(r, /^rejected: .*Invalid PDF structure/, `open ${i} is refused in pdf.js's words (${r})`);
      await workersSettleAt(0, `after refused open ${i}`);
      assert.equal(await hostChildren(), 0, "nothing of the chunk's in the host");
    }

    // ── a valid open holds exactly one Worker, and dispose() releases it: the count tracks the Worker's life
    assert.equal(await open(twoPages().toString("base64")), "pages: 2");
    await workersSettleAt(1, "after a valid open");
    await page.evaluate(() => (window as any).__h.dispose());
    await workersSettleAt(0, "after dispose()");

    // ── a page-count refusal (the document opens, then the cap refuses it) holds none either
    const r = await open(hostilePdf(2000000).toString("base64"));
    assert.equal(r, "rejected: " + pageCapMessage(2000000, DEFAULT_MAX_PAGES));
    await workersSettleAt(0, "after a page-count refusal");
    assert.deepEqual(errors, [], errors.join("\n"));
  } finally {
    await browser.close();
  }
});
