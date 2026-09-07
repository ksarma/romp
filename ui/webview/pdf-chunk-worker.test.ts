// The PDF chunk OWNS its Worker (plans/file-review.md, Slice 4; the 2026-09-06 review, second pass). pdf.js spawns a
// module Worker from `GlobalWorkerOptions.workerSrc` for each getDocument, and when that Worker fails to load (the
// script 404s, arrives as a login page's HTML on a lapsed cookie, or is cut short mid-rewrite) it sets a static
// "worker disabled" flag nothing clears and routes every LATER document through a main-thread stand-in, whose import
// of the IIFE-built worker yields no handler: the first attempt rejected with pdf.js's internal text about a "fake
// worker", and so did every attempt after it in that tab, in 0 ms and without another fetch, until the page was
// reloaded. The chunk's fallback contract (a line saying why; a latch that clears so the next open retries) covered the
// chunk script alone. Now the chunk starts the Worker itself and hands pdf.js the port for the one getDocument call, so
// the flag is never reached; watches the Worker's `error` before the document opens and rejects render() by name,
// terminating it; and terminates the Worker once pdf.js's destroy of the loading task settles, since pdf.js terminates
// only a Worker it spawned. Three legs. PURE: the message, the script URL rule (same-origin direct, cross-origin through
// a blob module, as pdf.js does), no constructor means no owned Worker. STAND-IN: a fake Worker constructor and a fake
// pdf.js drive render(): the port set for the call and cleared after it, a load failure a named rejection at once (pdf.js's
// promise hangs) with the Worker terminated, the next render() a fresh Worker, and a released document terminating its
// Worker only after pdf.js's destroy settles. CHROMIUM (skips by name without playwright's chromium): the built chunk as
// shipped, with the worker's first two fetches failing (a 401 login page, a truncated script) and the third served: two
// named refusals, no fake-worker text, no Worker left behind, then pages drawn. Fixtures are synthetic: TESTHOST, blank
// pages, invented bytes.
import { test, beforeEach } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { resolveObjectURL } from "node:buffer";
import { makeRender, ownWorker, workerFailedMessage, workerScriptUrl, type PdfLib } from "./pdf-chunk";

const SRC = "http://TESTHOST:29855/dist/pdf-worker.js?v=1725300000";
const PAGE = "http://TESTHOST:29855/files";

// ── pure: the message and the script URL rule ────────────────────────────────────────────────────

test("the refusal names the worker and its file, and carries the browser's reason when there is one", () => {
  assert.equal(workerFailedMessage(), "the PDF renderer's worker failed to load (pdf-worker.js)");
  assert.equal(workerFailedMessage(null), "the PDF renderer's worker failed to load (pdf-worker.js)");
  assert.equal(workerFailedMessage(""), "the PDF renderer's worker failed to load (pdf-worker.js)");
  assert.equal(workerFailedMessage("Uncaught SyntaxError: Unexpected end of input"),
    "the PDF renderer's worker failed to load (pdf-worker.js): Uncaught SyntaxError: Unexpected end of input");
  assert.doesNotMatch(workerFailedMessage(), /fake worker|romp|chunk/i, "the person's words, not pdf.js's internals or the build's");
});

test("a same-origin worker URL is used as is; a cross-origin or opaque-origin page gets a same-origin blob module that imports it (pdf.js's own rule)", async () => {
  assert.deepEqual(workerScriptUrl(SRC, PAGE), { url: SRC, blob: false }, "the kernel's pages: same origin, same URL, token and all");
  assert.deepEqual(workerScriptUrl(SRC, null), { url: SRC, blob: false }, "no page location (Node): as is");
  const cdn = "https://file+.vscode-resource.vscode-cdn.net/ext/dist/pdf-worker.js";
  for (const href of ["vscode-webview://11111111-2222-3333-4444-555555555555/index.html", "https://other.example/view"]) {
    const r = workerScriptUrl(cdn, href);
    assert.equal(r.blob, true, href + ": a Worker's script must be same-origin with its page, so a blob module stands in");
    assert.match(r.url, /^blob:/);
    const text = await resolveObjectURL(r.url)!.text();
    assert.equal(text, `await import(${JSON.stringify(cdn)});`, "the blob module imports the real worker, and nothing else");
    URL.revokeObjectURL(r.url);
  }
  assert.equal(ownWorker(SRC, null, PAGE), null, "no Worker constructor, no owned Worker: pdf.js keeps its own path (Node)");
});

// ── stand-ins: a Worker constructor the test controls, and a pdf.js that records the port it was handed ──

class FakeWorker {
  static made: FakeWorker[] = [];
  listeners = new Map<string, Array<(e: unknown) => void>>();
  terminated = 0;
  constructor(public url: string, public opts: { type: string }) { FakeWorker.made.push(this); }
  addEventListener(type: string, cb: (e: unknown) => void): void {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type)!.push(cb);
  }
  fire(type: string, e: unknown): void { for (const cb of this.listeners.get(type) || []) cb(e); }
  terminate(): void { this.terminated++; }
}
interface Deferred { promise: Promise<void>; resolve(): void }
const deferred = (): Deferred => { let resolve!: () => void; const promise = new Promise<void>((r) => { resolve = r; }); return { promise, resolve }; };
interface Fake { lib: PdfLib; opts: { workerSrc: string; workerPort: unknown }; ports: unknown[]; destroys: Deferred[]; destroyCalls: number }
/** A pdf.js whose getDocument records `GlobalWorkerOptions.workerPort` at the call and answers as told: `open` is
 *  the document (numPages 0: no page, no canvas, the smallest render), or null for a document that never answers (a
 *  Worker that did not load). Each destroy() settles when the test says. */
function fakeLib(open: { numPages: number } | null): Fake {
  const opts = { workerSrc: SRC, workerPort: null as unknown };
  const f: Fake = { lib: null as unknown as PdfLib, opts, ports: [], destroys: [], destroyCalls: 0 };
  f.lib = {
    GlobalWorkerOptions: opts,
    RenderingCancelledException: class extends Error {},
    getDocument: () => {
      f.ports.push(opts.workerPort);
      const d = deferred(); f.destroys.push(d);
      return {
        promise: open ? Promise.resolve(open) : new Promise<never>(() => {}),
        destroy: () => { f.destroyCalls++; return d.promise; },
      };
    },
  } as unknown as PdfLib;
  return f;
}
/** A container render() must never reach for on a document that did not open: every property read throws. */
const untouchable = () => new Proxy({}, {
  get(_t, k) { throw new Error("render() touched the container (" + String(k) + ") for a document that never opened"); },
}) as unknown as HTMLElement;
const g = globalThis as any;
beforeEach(() => {
  FakeWorker.made = [];
  g.Worker = FakeWorker;
  g.document = { createElement: () => ({ className: "", style: {}, dataset: {}, appendChild() {}, remove() {} }) };
  delete g.IntersectionObserver;
  delete g.ResizeObserver;
});

test("render() starts the Worker from pdf.js's worker URL, hands pdf.js the port for the one getDocument call, and clears it after", async () => {
  const f = fakeLib({ numPages: 0 });
  const host = { className: "", style: {}, appendChild() {}, remove() {} } as unknown as HTMLElement;
  const h = await makeRender(f.lib)(new ArrayBuffer(8), host);
  assert.equal(h.pages, 0);
  assert.equal(FakeWorker.made.length, 1, "one Worker for one render()");
  assert.equal(FakeWorker.made[0].url, SRC, "from GlobalWorkerOptions.workerSrc: the chunk's own directory and ?v= token");
  assert.deepEqual(FakeWorker.made[0].opts, { type: "module" }, "a module Worker, as pdf.js's is");
  assert.deepEqual(f.ports, [FakeWorker.made[0]], "pdf.js saw the Worker as workerPort when getDocument ran…");
  assert.equal(f.opts.workerPort, null, "…and the slot is cleared after it: nothing shared between renders");
  assert.equal(FakeWorker.made[0].terminated, 0, "the Worker lives while the document does");
  // dispose: pdf.js's destroy first (it releases fonts and bitmaps through a reply from the worker), the Worker after
  h.dispose();
  assert.equal(f.destroyCalls, 1);
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(FakeWorker.made[0].terminated, 0, "not terminated while pdf.js's destroy is unsettled: its reply is still to come");
  f.destroys[0].resolve();
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(FakeWorker.made[0].terminated, 1, "terminated once pdf.js's destroy settled (pdf.js terminates only a Worker it spawned)");
  h.dispose();
  assert.equal(FakeWorker.made[0].terminated, 1, "a second dispose is inert");
});

test("a Worker that fires error before the document opens rejects render() by name and at once, terminates it, and the next render() starts a fresh one", async () => {
  const dead = fakeLib(null);                    // pdf.js's promise never settles: no reply from a Worker that did not load
  const render = makeRender(dead.lib);
  const attempt = render(new ArrayBuffer(8), untouchable());
  const rejected = attempt.then(() => "resolved", (e: Error) => e.message);
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(FakeWorker.made.length, 1);
  const w = FakeWorker.made[0];
  assert.deepEqual(dead.ports, [w], "pdf.js was handed the port");
  // the browser's signal: the script 404ed, was cut short, or threw as it ran. With a reason, and without one.
  w.fire("error", { message: "Uncaught SyntaxError: Unexpected end of input" });
  assert.equal(await rejected, workerFailedMessage("Uncaught SyntaxError: Unexpected end of input"), "the refusal names the worker, the file and the browser's reason");
  await new Promise((r) => setTimeout(r, 5));    // the release rides the destroy's race, a microtask or two behind the rejection
  assert.equal(w.terminated, 1, "the dead Worker is terminated at once: pdf.js's destroy would wait on a reply it never sends");
  assert.equal(dead.destroyCalls, 1, "the loading task is destroyed all the same");
  assert.equal(dead.opts.workerPort, null);
  // nothing latched: the next render() starts its own Worker and fetches afresh — the failure was the attempt's, not the tab's
  const live = fakeLib({ numPages: 0 });
  const host = { className: "", style: {}, appendChild() {}, remove() {} } as unknown as HTMLElement;
  const h = await makeRender(live.lib)(new ArrayBuffer(8), host);
  assert.equal(h.pages, 0);
  assert.equal(FakeWorker.made.length, 2, "a second Worker for the second render()");
  assert.notEqual(FakeWorker.made[1], w);
  assert.equal(FakeWorker.made[1].url, SRC);
  h.dispose(); live.destroys[0].resolve();
  // a reason-less error event (a 404 in some engines) gets the bare refusal
  const dead2 = fakeLib(null);
  const r2 = makeRender(dead2.lib)(new ArrayBuffer(8), untouchable()).then(() => "resolved", (e: Error) => e.message);
  await new Promise((r) => setTimeout(r, 5));
  FakeWorker.made[2].fire("error", { message: "" });
  assert.equal(await r2, workerFailedMessage());
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(FakeWorker.made[2].terminated, 1);
});

test("a Worker that dies after the document opened is released by dispose() without waiting on pdf.js's destroy, which its reply would have settled", async () => {
  const f = fakeLib({ numPages: 0 });
  const host = { className: "", style: {}, appendChild() {}, remove() {} } as unknown as HTMLElement;
  const h = await makeRender(f.lib)(new ArrayBuffer(8), host);
  const w = FakeWorker.made[0];
  h.dispose();                                   // pdf.js's destroy is pending (f.destroys[0] unresolved)…
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(w.terminated, 0);
  w.fire("error", { message: "Uncaught Error: gone" });   // …and the Worker dies under it: no reply is coming
  await new Promise((r) => setTimeout(r, 5));
  assert.equal(w.terminated, 1, "released on the Worker's error rather than on a destroy that can no longer settle");
});

// ── the reason, pinned to the installed pdf.js: the latch is in the path the chunk avoids, and not in the one it takes ──

const EXT = process.cwd();
const PDF_MAIN = fs.readFileSync(path.join(EXT, "node_modules", "pdfjs-dist", "build", "pdf.mjs"), "utf8");
const CHUNK = fs.readFileSync(path.resolve(EXT, "..", "ui", "webview", "pdf-chunk.ts"), "utf8");
const code = (s: string) => s.split("\n").filter((l) => !l.trim().startsWith("//")).join("\n");
/** A class-body method from its first line to its closing brace at two-space indent. */
function method(src: string, head: string): string {
  const i = src.indexOf(head);
  assert.notEqual(i, -1, head.trim() + " is in pdf.mjs");
  const end = src.indexOf("\n  }\n", i);
  return src.slice(i, end);
}

test("pdf.js's port path never touches its worker-disabled flag, and its URL path does — the reason the chunk starts the Worker itself", () => {
  const cls = PDF_MAIN.slice(PDF_MAIN.indexOf("class PDFWorker {"), PDF_MAIN.indexOf("class WorkerTransport {"));
  assert.match(cls, /static #isWorkerDisabled = false;/, "the static flag exists in this build");
  const fromUrl = method(cls, "  #initialize() {");
  assert.match(fromUrl, /#setupFakeWorker\(\)/, "the URL path falls to the fake worker…");
  assert.match(method(cls, "  #setupFakeWorker() {"), /PDFWorker\.#isWorkerDisabled = true;/, "…which sets the flag for the tab's life (nothing in this build clears it)");
  assert.equal((cls.match(/#isWorkerDisabled = false/g) || []).length, 1, "the flag is set false at its declaration and nowhere else: nothing resets it");
  const fromPort = method(cls, "  #initializeFromPort(port) {");
  assert.doesNotMatch(fromPort, /isWorkerDisabled|setupFakeWorker|new Worker/, "the port path wraps the Worker it is given and reaches neither the flag nor the fake worker");
  assert.match(method(cls, "  constructor({"), /if \(port\) \{[\s\S]*?this\.#initializeFromPort\(port\);[\s\S]*?\} else \{[\s\S]*?this\.#initialize\(\);/, "a port takes the port path; none, the URL path");
  // the slot the chunk hands the port through, and getDocument reading it for a fresh PDFWorker
  assert.match(PDF_MAIN, /static set workerPort\(val\) \{[\s\S]*?instanceof Worker/, "GlobalWorkerOptions.workerPort takes a Worker");
  assert.match(PDF_MAIN, /worker = PDFWorker\.create\(\{\s*verbosity,\s*port: GlobalWorkerOptions\.workerPort\s*\}\);/, "getDocument wraps the port when no worker is passed");
  // pdf.js's destroy of a port-wrapped PDFWorker terminates no Worker: #webWorker is set on the URL path alone
  assert.match(method(cls, "  destroy() {"), /this\.#webWorker\?\.terminate\(\);/);
  assert.doesNotMatch(fromPort, /#webWorker/, "…so the chunk's release() is what terminates the Worker it started");
});

test("the chunk: the port set for the one getDocument call and cleared after, the open raced against the Worker's failure, the Worker released with the task", () => {
  const c = code(CHUNK);
  assert.match(c, /const owned = ownWorker\(pdfjsLib\.GlobalWorkerOptions\.workerSrc\);\n\s*if \(owned\) pdfjsLib\.GlobalWorkerOptions\.workerPort = owned\.port;/);
  assert.match(c, /finally \{ if \(owned\) pdfjsLib\.GlobalWorkerOptions\.workerPort = null; \}/, "cleared whether getDocument returned or threw");
  assert.match(c, /const task: Loading = owned \? adopt\(loading, owned\) : loading;/);
  assert.match(c, /doc = await race\(owned \? Promise\.race\(\[task\.promise, owned\.failed\]\) : task\.promise\);/,
    "a Worker that never loads is a refusal, not a hang (race() adds the caller's abort — pdf-chunk-abort.test.ts)");
  assert.match(c, /Promise\.race\(\[done, owned\.failed\]\)\.then\(owned\.release, owned\.release\);/, "released after pdf.js's destroy, or at once if the Worker is what failed");
  assert.match(c, /port\.addEventListener\("error", [^\n]*\{ once: true \}\);/);
  assert.match(c, /failed\.catch\(\(\) => \{\}\);/, "a rejection nobody races is not an unhandled one");
  assert.match(c, /if \(!pdfjsLib\.GlobalWorkerOptions\.workerSrc\) \{/, "the URL still lives in pdf.js's slot, and its absence is still the named refusal");
});

// ── in Chromium: the built chunk, a worker whose first two fetches fail, then one that loads ─────────

const OUT = path.join(EXT, "out-tests", "pdf-chunk-worker");
const req = createRequire(path.join(EXT, "package.json"));   // runtime requires: esbuild must not bundle playwright
let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the owned-worker browser test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the owned-worker browser test did not run";
}

/** A PDF of one blank US-letter page with a correct xref. */
function onePage(): Buffer {
  const objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>", "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"];
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objs.forEach((body, i) => { offsets.push(Buffer.byteLength(out, "latin1")); out += `${i + 1} 0 obj\n${body}\nendobj\n`; });
  const xref = Buffer.byteLength(out, "latin1");
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offsets) out += `${String(o).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  return Buffer.from(out, "latin1");
}

async function buildChunk(): Promise<void> {
  await req("esbuild").build({
    entryPoints: [
      path.join(EXT, "..", "ui", "webview", "pdf-chunk.ts"),
      { in: path.join(EXT, "node_modules", "pdfjs-dist", "build", "pdf.worker.mjs"), out: "pdf-worker" },
    ],
    nodePaths: [path.join(EXT, "node_modules")],
    bundle: true, format: "iife", platform: "browser", target: "es2020", outdir: OUT, logLevel: "silent",
  });
}
const HTML = `<!doctype html><html><head><meta charset="utf-8"></head><body>
<div class="fileview"><div class="fileview-body" id="body" style="overflow:auto;height:600px;width:700px"><div class="fileview-pdfhost" id="host"></div></div></div>
<script src="/dist/pdf-chunk.js?v=1725300000"></script>
</body></html>`;

test("in Chromium: a worker fetch that fails (a 401 login page, then a truncated script) is a named refusal each time, never pdf.js's fake worker, and the next open fetches the worker afresh and draws", { skip: SKIP }, async () => {
  await buildChunk();
  const workerJs = fs.readFileSync(path.join(OUT, "pdf-worker.js"));
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
    const logs: string[] = [];
    page.on("console", (m: any) => logs.push(m.type() + ": " + m.text()));
    page.on("pageerror", (e: Error) => logs.push("pageerror: " + e.message));
    let mode: "401" | "truncated" | "ok" = "401";
    const workerFetches: string[] = [];
    await page.route("http://TESTHOST/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/view.html") return route.fulfill({ contentType: "text/html", body: HTML });
      if (u.pathname === "/dist/pdf-worker.js") {
        workerFetches.push(mode);
        if (mode === "401") return route.fulfill({ status: 401, contentType: "text/html", body: "<!doctype html><title>sign in</title>" });
        if (mode === "truncated") return route.fulfill({ contentType: "application/javascript", body: workerJs.subarray(0, Math.floor(workerJs.length / 2)) });
        return route.fulfill({ contentType: "application/javascript", body: workerJs });
      }
      const f = path.join(OUT, path.basename(u.pathname));
      if (u.pathname.startsWith("/dist/") && fs.existsSync(f)) return route.fulfill({ contentType: "application/javascript", body: fs.readFileSync(f) });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://TESTHOST/view.html");
    await page.waitForFunction(() => !!(window as any).__rompPdf, null, { timeout: 10000 });
    const b64 = onePage().toString("base64");
    /** render() in the page: the page count, or the rejection's message prefixed "rejected: ", and how long it took. */
    const open = () => page.evaluate(async (b64: string) => {
      const bin = atob(b64); const u8 = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      const w = window as any; const t0 = performance.now();
      try {
        const h = await w.__rompPdf.render(u8.buffer, document.getElementById("host"));
        w.__h = h;
        return { result: "pages: " + h.pages, ms: performance.now() - t0 };
      } catch (e) { return { result: "rejected: " + (e as Error).message, ms: performance.now() - t0 }; }
    }, b64);
    const workersSettleAt = async (n: number, what: string) => {
      for (let i = 0; i < 500; i++) { if (page.workers().length === n) return; await new Promise((r) => setTimeout(r, 10)); }
      assert.fail(`${what}: expected ${n} live Worker(s), the page has ${page.workers().length}`);
    };

    // ── the first open: the worker comes back as a login page (a lapsed cookie's 401) — the refusal names the worker, not pdf.js's fake one
    const first = await open();
    assert.match(first.result, /^rejected: the PDF renderer's worker failed to load \(pdf-worker\.js\)/, first.result);
    assert.ok(first.ms < 5000, `refused at once (${Math.round(first.ms)} ms), not at a backstop`);
    await workersSettleAt(0, "after the 401");
    assert.equal(await page.evaluate(() => document.getElementById("host")!.children.length), 0, "nothing of the chunk's in the host");

    // ── the second: the worker arrives cut short (a file read mid-rewrite): the same named refusal, the browser's reason may ride along
    mode = "truncated";
    const second = await open();
    assert.match(second.result, /^rejected: the PDF renderer's worker failed to load \(pdf-worker\.js\)/, second.result);
    await workersSettleAt(0, "after the truncated script");

    // ── the third: the worker is served whole — fetched again (nothing latched), the page draws, dispose releases the Worker
    mode = "ok";
    const third = await open();
    assert.equal(third.result, "pages: 1", "the tab is not stuck: the same PDF opens once the worker loads");
    await workersSettleAt(1, "with a document open");
    assert.deepEqual(workerFetches, ["401", "truncated", "ok"], "each attempt fetched the worker afresh");
    await page.evaluate(() => (window as any).__h.dispose());
    await workersSettleAt(0, "after dispose()");
    // pdf.js's fake-worker path was never entered: its warning and its failure text appear nowhere
    assert.equal(logs.filter((l) => /fake worker/i.test(l)).length, 0, "no fake worker:\n" + logs.join("\n"));
  } finally {
    await browser.close();
  }
});
