// The KaTeX chunk's loading paths in a real page, for the two legs that run them (math-chunk-load-browser.test.ts in
// Chromium, through the shared launcher, and math-chunk-load-webkit-browser.test.ts in WebKit): a probe bundle of the chat's
// markdown path (marked with the one grammar, then sanitizeMd, whose registered post-pass is math.ts's fill) built from this
// tree WITHOUT KaTeX, served by src as /dist/render.js?v=7 the way the kernel serves the chat's bundle, and the real chunk
// (math-chunk.ts, built with the shipped webview config) at /dist/math-chunk.js, answered as a scene asks: served, held until
// the scene lets it go, a 404, or a script that registers nothing. The page carries katex.min.css with its fonts answered
// from the package (or held), and the real styles.css less its KaTeX import, so the pending dress is the sheet's own. Every
// request is logged. A scene builds message bodies through `window.__md(src)` (the probe's md(): sanitizeMd over marked.parse,
// as render.ts md() composes them less the PR-reference walk) into `#out`, a `.md` box like a chat message's. Test-only: no
// webview bundle imports it. Synthetic values only.
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

export const EXT = process.cwd();                                       // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_DIST = path.join(EXT, "node_modules", "katex", "dist");
const KATEX_CSS = fs.readFileSync(path.join(KATEX_DIST, "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', "");
export const ORIGIN = "http://romp.test";

const PROBE = `
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { sanitizeMd } from "./md-sanitize";
applyMdConfig();   // the one grammar on the singleton; importing md-config.ts registers the math fill as sanitizeMd's post-pass
(window as any).__md = (src: string): string => sanitizeMd(marked.parse(src) as string).innerHTML;
`;

let probe: string | null = null;
/** The probe bundle: the chat's markdown path from this tree, no KaTeX in it (the main bundles carry none). */
export function probeBundle(): string {
  if (probe) return probe;
  const r = requireCjs("esbuild").buildSync({
    stdin: { contents: PROBE, resolveDir: UI, loader: "ts", sourcefile: "math-chunk-leg-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  probe = r.outputFiles[0].text as string;
  return probe;
}

let chunk: { js: string } | { error: string } | null = null;
/** The chunk as the shipped webview build builds it (esbuild.js's exported config, the one entry), or the build's error: a tree
 *  without math-chunk.ts answers the chunk's URL with a 404, so a scene's own assertions say what is missing. */
export function chunkBundle(): { js: string } | { error: string } {
  if (chunk) return chunk;
  try {
    const { webview } = requireCjs("./esbuild.js") as { webview: Record<string, unknown> };
    const r = requireCjs("esbuild").buildSync({ ...(webview as object), entryPoints: ["../ui/webview/math-chunk.ts"], write: false, sourcemap: false, logLevel: "silent" });
    chunk = { js: r.outputFiles.find((f: { path: string }) => f.path.endsWith(".js")).text as string };
  } catch (e) {
    chunk = { error: String((e as Error).message).split("\n")[0] };
  }
  return chunk;
}

/** A promise a scene settles by hand: the chunk's or the fonts' answer held until `open()`. */
export type Gate = { promise: Promise<void>; open: () => void };
export function gate(): Gate {
  let open = (): void => {};
  const promise = new Promise<void>((r) => { open = r; });
  return { promise, open };
}

export type ChunkMode = "serve" | "404" | "empty";
export type PageOpts = {
  /** how the chunk's URL is answered */
  chunk?: ChunkMode;
  /** held: the chunk's answer waits for it */
  chunkGate?: Gate | null;
  /** held: every KaTeX font's answer waits for it */
  fontGate?: Gate | null;
  /** the bundle inlined into the page instead of loaded by src (a page with no bundle tag to derive the chunk's URL from) */
  inline?: boolean;
  /** the VS Code webview's shape: buildHtml's Content-Security-Policy (script-src by nonce alone) and the nonce on the tag */
  webview?: boolean;
};
/** consoleErrors: every console error but the browser's own line for a missing resource (the sheet's media fonts, which the leg
 *  does not serve); a failed chunk shows in the box and in math.ts's own line, which is kept. */
export type Scene = { page: any; requests: string[]; consoleErrors: string[]; pageErrors: string[]; chunkRequests: () => number };

export const NONCE = "legnonce1";
/** extension.ts buildHtml's policy with the leg's origin as the webview's cspSource (the leg pins the source's shape). */
export const WEBVIEW_CSP = `default-src 'none'; img-src ${ORIGIN} data:; style-src ${ORIGIN} 'unsafe-inline'; font-src ${ORIGIN}; connect-src ${ORIGIN}; script-src 'nonce-${NONCE}'`;

function pageHtml(o: PageOpts): string {
  const csp = o.webview ? `<meta http-equiv="Content-Security-Policy" content="${WEBVIEW_CSP}">` : "";
  const nonce = o.webview ? ` nonce="${NONCE}"` : "";
  const script = o.inline ? `<script${nonce}>${probeBundle()}</script>` : `<script${nonce} src="/dist/render.js?v=7"></script>`;
  // the sheets as the chat page has them, KaTeX's first (the chat's styles.css imports it at its top); a dim probe to read the tier off
  return `<!DOCTYPE html><html><head><meta charset=utf-8>${csp}<style>${KATEX_CSS}\n${STYLES}\nbody{font-size:16px}</style></head>
<body><div id=out class=md></div><span id=dim style="color: var(--dim)">dim</span>${script}</body></html>`;
}

/** Open the page in `browser` under `o`, wait for the probe, and hand the scene to `body`. */
export async function withPage(browser: any, o: PageOpts, body: (s: Scene) => Promise<void>): Promise<void> {
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
  const requests: string[] = [], consoleErrors: string[] = [], pageErrors: string[] = [];
  page.on("console", (m: any) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) consoleErrors.push(m.text()); });
  page.on("pageerror", (e: Error) => { pageErrors.push(e.message); });
  const html = pageHtml(o);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), async (route: any) => {
    const u = new URL(route.request().url());
    requests.push(u.pathname + u.search);
    if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: html });
    if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "text/javascript", body: probeBundle() });
    if (u.pathname === "/sentinel") return route.fulfill({ status: 200, contentType: "text/plain", body: "ok" });
    if (u.pathname === "/dist/math-chunk.js") {
      if (o.chunkGate) await o.chunkGate.promise;
      const c = chunkBundle();
      if ((o.chunk || "serve") === "404" || "error" in c) return route.fulfill({ status: 404, contentType: "text/plain", body: "not found" });
      return route.fulfill({ status: 200, contentType: "text/javascript", body: (o.chunk || "serve") === "empty" ? "/* registers nothing */" : c.js });
    }
    if (u.pathname.startsWith("/fonts/")) {
      if (o.fontGate) await o.fontGate.promise;
      const f = path.join(KATEX_DIST, "fonts", path.basename(u.pathname));
      if (fs.existsSync(f)) return route.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) });
    }
    return route.fulfill({ status: 404, contentType: "text/plain", body: "" });
  });
  try {
    await page.goto(ORIGIN + "/page");
    await page.waitForFunction(() => typeof (window as any).__md === "function", null, { timeout: 10000 });
    await body({ page, requests, consoleErrors, pageErrors, chunkRequests: () => requests.filter((r) => r.startsWith("/dist/math-chunk.js")).length });
    assert.deepEqual(pageErrors, [], "no page errors");
  } finally {
    await page.close();
  }
}

/** Render `src` through the probe's md() into #out (appended as a message of its own) and return what the box holds then. */
export const show = (page: any, src: string): Promise<void> => page.evaluate((s: string) => {
  const m = document.createElement("div"); m.className = "msg"; m.innerHTML = (window as any).__md(s); document.getElementById("out")!.appendChild(m);
}, src);

/** One round trip to the page's origin and two frames: a request the page issued before it has reached the log. */
export const drain = async (page: any): Promise<void> => {
  await page.evaluate(() => fetch("/sentinel", { cache: "no-store" }).then(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))));
};

/** What the box holds: formulas still waiting (their text and call stamp), KaTeX roots, source fallbacks (their titles). */
export type Box = { pending: { text: string; call: string | null; display: boolean; color: string; block: string; margin: string; align: string }[]; katex: number; src: { text: string; title: string }[]; dim: string };
export const box = (page: any): Promise<Box> => page.evaluate(() => {
  const out = document.getElementById("out")!;
  const pending = Array.from(out.querySelectorAll(".md-math-inline, .md-math-display")).map((n) => {
    const e = n as HTMLElement; const cs = getComputedStyle(e);
    return { text: e.textContent || "", call: e.getAttribute("data-math-call"), display: e.classList.contains("md-math-display"), color: cs.color, block: cs.display, margin: cs.marginTop + " " + cs.marginBottom, align: cs.textAlign };
  });
  const src = Array.from(out.querySelectorAll("code.md-math-src")).map((c) => ({ text: c.textContent || "", title: ((c.closest("pre") || c) as HTMLElement).getAttribute("title") || "" }));
  return { pending, katex: out.querySelectorAll(".katex").length, src, dim: getComputedStyle(document.getElementById("dim")!).color };
});

/** Wait until the box holds no formula still waiting. */
export const settled = (page: any, timeout = 20000): Promise<unknown> =>
  page.waitForFunction(() => !document.querySelector("#out .md-math-inline, #out .md-math-display"), null, { timeout });

// ── the scenes: each opens its own page; the Chromium leg runs them through the shared launcher, the WebKit leg in WebKit ──

/** A formula of `n` characters of TeX that lays out as `x^2 + y`: the rest is a TeX comment (KaTeX reads `%` to the end of the
 *  formula and lays out nothing for it). The budget counts TeX as written, which is what the budget scene exercises, and the
 *  padding costs no layout, so the scene's eleven formulas render in seconds in WebKit too (a flat sum of the same length, the
 *  cheapest shape KaTeX lays out, took over two minutes there on a loaded box). */
const padded = (n: number): string => { const head = "x^2 + y % "; return head + "p".repeat(n - head.length); };
const FORMULA = 18999;                                                   // under MATH_TEX_MAX_CHARS (20,000): one formula is never refused for its length
const message = (k: number): string => Array.from({ length: k }, () => "$$" + padded(FORMULA) + "$$").join("\n\n") + "\n";

export type SceneDef = { name: string; timeout: number; run: (browser: any, t: any) => Promise<void> };
export const SCENES: SceneDef[] = [
  {
    name: "a page that shows no math fetches no chunk; the first formula fetches it once and shows its TeX in the pending dress until it lands; then KaTeX stands in its place, and a later formula renders in its own call with no request",
    timeout: 60000,
    run: async (browser) => {
      const g = gate();
      await withPage(browser, { chunkGate: g }, async (s) => {
        await show(s.page, "Prices run $5-$10, and $HOME/$USER stays literal, as does `$x$` in code.");
        await drain(s.page);
        let b = await box(s.page);
        assert.equal(s.chunkRequests(), 0, "a message with no formula asks for no chunk");
        assert.deepEqual([b.pending.length, b.katex, b.src.length], [0, 0, 0], "and holds no formula of any kind");
        await show(s.page, "The ratio $\\frac{a}{b}$ grows.\n\n$$\\sum_{i=0}^{n} i^2$$\n");
        await drain(s.page);
        b = await box(s.page);
        assert.equal(s.chunkRequests(), 1, "the first formula asks for the chunk, once");
        assert.equal(b.katex, 0, "nothing is laid out before the chunk lands");
        assert.deepEqual(b.pending.map((p) => [p.text, p.display]), [["\\frac{a}{b}", false], ["\\sum_{i=0}^{n} i^2", true]], "each formula shows its TeX while it waits, never a blank");
        assert.ok(b.pending.every((p) => !!p.call && p.call === b.pending[0].call), "both carry the group of the one call that met them: " + JSON.stringify(b.pending));
        assert.ok(b.pending.every((p) => p.color === b.dim), "in the sheet's dim tier: " + JSON.stringify(b.pending.map((p) => p.color)) + " vs " + b.dim);
        const d = b.pending[1];
        assert.deepEqual([d.block, d.align], ["block", "center"], "the display formula waits in KaTeX's display box: a centred block");
        const [mt, mb] = d.margin.split(" ").map(parseFloat);
        assert.ok(mt > 0 && mt === mb, "with KaTeX's 1em margin above and below: " + d.margin);
        await show(s.page, "and $x^2$ too");
        await drain(s.page);
        assert.equal(s.chunkRequests(), 1, "a formula met while the chunk is out asks for nothing more");
        g.open();
        await settled(s.page);
        b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length], [3, 0], "the arrival lays out every waiting formula, none as source");
        assert.equal(await s.page.evaluate(() => document.querySelectorAll("#out [data-math-call]").length), 0, "no group stamp is left");
        await show(s.page, "now $y_1$ at once");
        b = await box(s.page);
        assert.deepEqual([b.katex, b.pending.length], [4, 0], "with the engine in, a formula renders in the call that meets it");
        await drain(s.page);
        assert.deepEqual(s.requests.filter((r) => r.startsWith("/dist/math-chunk.js")), ["/dist/math-chunk.js?v=7"], "one request, the bundle's own ?v= token on it");
        assert.deepEqual(s.consoleErrors, [], "no console error");
      });
    },
  },
  {
    name: "the swap waits for the two common KaTeX faces: with the chunk in and the fonts held, the formula keeps its TeX, and it is laid out once both have loaded",
    timeout: 60000,
    run: async (browser) => {
      const fg = gate();
      await withPage(browser, { fontGate: fg }, async (s) => {
        await s.page.evaluate(() => {
          (window as any).__atSwap = null;
          new MutationObserver(() => {
            if ((window as any).__atSwap === null && document.querySelector("#out .katex"))
              (window as any).__atSwap = { main: document.fonts.check("1em KaTeX_Main"), math: document.fonts.check("italic 1em KaTeX_Math") };
          }).observe(document.getElementById("out")!, { childList: true, subtree: true });
        });
        await show(s.page, "a formula $\\alpha + \\beta$ here");
        await s.page.waitForFunction(() => !!(window as any).__rompKatex, null, { timeout: 10000 });
        await drain(s.page);
        await drain(s.page);
        const b = await box(s.page);
        assert.deepEqual([b.katex, b.pending.length], [0, 1], "the chunk is in and the faces are not: the formula still shows its TeX");
        fg.open();
        await settled(s.page);
        assert.deepEqual(await s.page.evaluate(() => (window as any).__atSwap), { main: true, math: true }, "both faces had loaded when KaTeX's markup went in");
      });
    },
  },
  {
    name: "the per-message budget holds per message across the wait: two messages each under it render whole when the chunk lands, and a message over it shows its last formula as source at once",
    timeout: 120000,
    run: async (browser) => {
      const g = gate();
      await withPage(browser, { chunkGate: g }, async (s) => {
        await show(s.page, message(3));
        await show(s.page, message(3));
        let b = await box(s.page);
        assert.deepEqual([b.pending.length, b.src.length], [6, 0], "two messages of three formulas, each message under the budget: all six wait");
        const calls = new Set(b.pending.map((p) => p.call));
        assert.equal(calls.size, 2, "two calls, two groups");
        await show(s.page, message(6));
        b = await box(s.page);
        assert.equal(b.src.length, 1, "one message of six formulas passes the budget at its sixth: shown as source at once");
        assert.match(b.src[0].title, /^Not rendered: the formulas above already total 94995 characters of TeX; the limit for one message or note is 100000\.$/);
        assert.equal(b.pending.length, 11);
        g.open();
        await settled(s.page, 90000);
        b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length], [11, 1], "the arrival charges each formula to its own message: every one that waited renders, and the refusal stands");
      });
    },
  },
  {
    name: "a chunk that fails to load leaves every waiting formula as its source with the failure in its title, says so once, and later formulas take the fallback with no second request",
    timeout: 60000,
    run: async (browser) => {
      await withPage(browser, { chunk: "404" }, async (s) => {
        await show(s.page, "a $\\frac{1}{2}$ half\n\n$$e^{i\\pi}$$\n");
        await settled(s.page);
        let b = await box(s.page);
        assert.equal(b.katex, 0);
        assert.deepEqual(b.src.map((x) => x.text), ["\\frac{1}{2}", "e^{i\\pi}"], "each formula's TeX, never a blank");
        for (const x of b.src) assert.equal(x.title, "Not rendered: the math renderer failed to load; reload the page to try again.");
        const said = () => s.consoleErrors.filter((e) => e.startsWith("math: "));
        assert.equal(said().length, 1, "the console says it once: " + JSON.stringify(s.consoleErrors));
        await show(s.page, "later $z$");
        b = await box(s.page);
        assert.deepEqual([b.src.length, b.pending.length], [3, 0], "a later formula is source in the call that meets it, waiting for nothing");
        await drain(s.page);
        assert.equal(s.chunkRequests(), 1, "a failure is not retried by every render");
        assert.equal(said().length, 1);
      });
    },
  },
  {
    name: "a chunk that loads and registers nothing is a failure too, named as such",
    timeout: 60000,
    run: async (browser) => {
      await withPage(browser, { chunk: "empty" }, async (s) => {
        await show(s.page, "a $q$ formula");
        await settled(s.page);
        const b = await box(s.page);
        assert.deepEqual(b.src.map((x) => x.title), ["Not rendered: the math renderer loaded but registered nothing; reload the page to try again."]);
        assert.equal(s.chunkRequests(), 1);
      });
    },
  },
  {
    name: "a page whose bundle ran from no tag with a src has no URL to derive the chunk's from: the formula falls back with the reason and nothing is requested",
    timeout: 60000,
    run: async (browser) => {
      await withPage(browser, { inline: true }, async (s) => {
        await show(s.page, "a $q$ formula");
        await settled(s.page);
        const b = await box(s.page);
        assert.deepEqual(b.src.map((x) => x.title), ["Not rendered: no bundle script on this page to derive the math renderer's URL from; reload the page to try again."]);
        assert.equal(s.chunkRequests(), 0);
      });
    },
  },
  {
    name: "a page shaped like the VS Code webview (its Content-Security-Policy allows a script by nonce alone) loads the chunk: the tag carries the bundle tag's nonce",
    timeout: 60000,
    run: async (browser) => {
      await withPage(browser, { webview: true }, async (s) => {
        await show(s.page, "a $\\sqrt{2}$ root");
        await settled(s.page);
        const b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length], [1, 0], "rendered: " + JSON.stringify(b.src));
        assert.equal(s.chunkRequests(), 1);
        assert.equal(await s.page.evaluate(() => (document.querySelector('script[src*="math-chunk"]') as HTMLScriptElement | null)?.nonce || ""), NONCE, "the chunk's tag carries the nonce");
        assert.deepEqual(s.consoleErrors, [], "no CSP refusal and no failure on the console");
      });
    },
  },
  {
    name: "timing, reported not pinned: the wait from the first formula to its layout on this machine, the chunk and the faces served from memory",
    timeout: 60000,
    run: async (browser, t) => {
      await withPage(browser, {}, async (s) => {
        await s.page.evaluate(() => {
          (window as any).__t = { show: 0, swap: 0 };
          new MutationObserver(() => { const w = window as any; if (!w.__t.swap && document.querySelector("#out .katex")) w.__t.swap = performance.now(); })
            .observe(document.getElementById("out")!, { childList: true, subtree: true });
        });
        await s.page.evaluate(() => { (window as any).__t.show = performance.now(); });
        await show(s.page, "$$\\int_0^1 x\\,dx = \\tfrac{1}{2}$$\n");
        await settled(s.page);
        const tm = await s.page.evaluate(() => (window as any).__t);
        assert.ok(tm.swap > tm.show, "the layout came after the formula was shown");
        t.diagnostic("pending-to-swap ms: " + Math.round(tm.swap - tm.show));
      });
    },
  },
];
