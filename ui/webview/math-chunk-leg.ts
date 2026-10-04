// The KaTeX chunk's loading paths in a real page, for the two legs that run them (math-chunk-load-browser.test.ts in
// Chromium, through the shared launcher, and math-chunk-load-webkit-browser.test.ts in WebKit): a probe bundle of the chat's
// markdown path (marked with the one grammar, then sanitizeMd, whose registered post-pass is math.ts's fill) built from this
// tree WITHOUT KaTeX, served by src as /dist/render.js?v=7 the way the kernel serves the chat's bundle, and the real chunk
// (math-chunk.ts, built with the shipped webview config) at /dist/math-chunk.js, answered as a scene asks: served, held until
// the scene lets it go, a 404, or a script that registers nothing. The page carries katex.min.css with its fonts answered
// from the package (or held), and the real styles.css less its KaTeX import, so the pending dress is the sheet's own. Every
// request is logged. A scene that needs the 60 s backstop installs Playwright's clock before the page loads and fast-forwards
// past MATH_CHUNK_BACKSTOP_MS (math.ts), so the backstop's end runs in a real page in seconds. A scene builds message bodies through `window.__md(src)` (the probe's md(): sanitizeMd over marked.parse,
// as render.ts md() composes them less the PR-reference walk) into `#out`, a `.md` box like a chat message's. Test-only: no
// webview bundle imports it. Synthetic values only.
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { MATH_CHUNK_BACKSTOP_MS } from "./math";

export const EXT = process.cwd();                                       // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_DIST = path.join(EXT, "node_modules", "katex", "dist");
const KATEX_CSS = fs.readFileSync(path.join(KATEX_DIST, "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', "");
export const ORIGIN = "http://romp.test";

/** render.ts's mention chips (markMentions and what it calls), the block composer-mention-pane.test.ts lifts the same way: from the
 *  roster signature to setupComposer's banner, run in a closure holding the module names it reads. */
function chipBlock(): string {
  const render = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
  const a = render.indexOf('let mentionRosterSig = "";');
  const b = render.indexOf("// Composer: Enter sends the message");
  assert.ok(a > 0 && b > a, "the chip functions sit just before setupComposer (re-anchor the lift)");
  return render.slice(a, b);
}

// The chat's markdown path, plus the two passes that walk a message's text after it, so a scene can run them over a formula still
// waiting for the renderer: glossary-links.ts's term linker (render.ts linkTerms dresses its spans) and render.ts's mention chips.
const PROBE = (): string => `
import { marked } from "marked";
import { applyMdConfig } from "./md-config";
import { sanitizeMd } from "./md-sanitize";
import { onMathSettled } from "./math";
import { linkifyTerms, buildMatcher } from "./glossary-links";
import { mentionSegments } from "./composer-mention";
import { hostNameNodes, hostPartsNodes } from "./host-prefix";
applyMdConfig();   // the one grammar on the singleton; importing md-config.ts registers the math fill as sanitizeMd's post-pass
(window as any).__md = (src: string): string => sanitizeMd(marked.parse(src) as string).innerHTML;
onMathSettled(() => { (window as any).__settles = ((window as any).__settles || 0) + 1; });   // each arrival, either way, counted for the scenes
(window as any).__terms = (root: HTMLElement, ix: any): number =>
  linkifyTerms(root, buildMatcher(ix)!, (_e: unknown, text: string) => { const t = document.createElement("span"); t.className = "term-link"; t.textContent = text; return t; });
const CHIP_LABEL: any = { working: "Working", ready: "Ready", idle: "Idle", closed: "Closed", needsInput: "Blocked" };
const el = (tag: string, cls?: string) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };
const isProvisionalId = (id: string) => id.startsWith("prov:");
void mentionSegments; void hostNameNodes; void hostPartsNodes; void CHIP_LABEL; void el; void isProvisionalId;
(window as any).__chips = (env: any) => {
  const sessions: Map<string, any> = env.sessions, tabMeta: Map<string, any> = new Map(), views: Map<string, any> = new Map();
  let refreshMentionCard: any = null;
  void tabMeta; void views; void refreshMentionCard;
${chipBlock()}
  return { markMentions };
};
`;

let probe: string | null = null;
/** The probe bundle: the chat's markdown path from this tree, no KaTeX in it (the main bundles carry none). */
export function probeBundle(): string {
  if (probe) return probe;
  const r = requireCjs("esbuild").buildSync({
    stdin: { contents: PROBE(), resolveDir: UI, loader: "ts", sourcefile: "math-chunk-leg-probe.ts" },
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
  /** how the chunk's URL is answered: one mode for every request, or one per request in order (the last repeats) */
  chunk?: ChunkMode | ChunkMode[];
  /** held: the chunk's answer waits for it */
  chunkGate?: Gate | null;
  /** held, per request in order: the n-th request's answer waits for the n-th gate (null or absent: not held) */
  chunkGates?: (Gate | null)[];
  /** held: every KaTeX font's answer waits for it */
  fontGate?: Gate | null;
  /** the bundle inlined into the page instead of loaded by src (a page with no bundle tag to derive the chunk's URL from) */
  inline?: boolean;
  /** the VS Code webview's shape: buildHtml's Content-Security-Policy (script-src by nonce alone) and the nonce on the tag */
  webview?: boolean;
  /** Playwright's clock installed before the page loads, so a scene can fast-forward past MATH_CHUNK_BACKSTOP_MS */
  clock?: boolean;
  /** held: the page carries a picture whose answer waits for it, so the document's load event waits too (the page is opened at
   *  DOMContentLoaded, the bundle having run) */
  loadGate?: Gate | null;
  /** `#out` inside the user's own bubble (`.user-bubble.md`, styles.css's rule for YOUR messages) */
  bubble?: boolean;
  /** the light theme (body.theme-light, styles.css's second theme block); the dark theme otherwise */
  light?: boolean;
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
<body class="${o.light ? "theme-light" : ""}">${o.bubble ? '<div class="user-bubble md" id=bubble><div id=out class=md></div></div>' : "<div id=out class=md></div>"}<span id=dim style="color: var(--dim)">dim</span>${o.loadGate ? '<img src="/held.png" alt="">' : ""}${script}</body></html>`;
}

/** Open the page in `browser` under `o`, wait for the probe, and hand the scene to `body`. */
export async function withPage(browser: any, o: PageOpts, body: (s: Scene) => Promise<void>): Promise<void> {
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
  const requests: string[] = [], consoleErrors: string[] = [], pageErrors: string[] = [];
  page.on("console", (m: any) => { if (m.type() === "error" && !/^Failed to load resource/.test(m.text())) consoleErrors.push(m.text()); });
  page.on("pageerror", (e: Error) => { pageErrors.push(e.message); });
  const html = pageHtml(o);
  let chunkAsked = 0;
  await page.route((u: URL) => u.href.startsWith(ORIGIN), async (route: any) => {
    const u = new URL(route.request().url());
    requests.push(u.pathname + u.search);
    if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: html });
    if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "text/javascript", body: probeBundle() });
    if (u.pathname === "/sentinel") return route.fulfill({ status: 200, contentType: "text/plain", body: "ok" });
    if (u.pathname === "/held.png") { if (o.loadGate) await o.loadGate.promise; return route.fulfill({ status: 404, contentType: "text/plain", body: "" }); }
    if (u.pathname === "/dist/math-chunk.js") {
      const n = chunkAsked++;
      const mode: ChunkMode = Array.isArray(o.chunk) ? o.chunk[Math.min(n, o.chunk.length - 1)] : o.chunk || "serve";
      if (o.chunkGate) await o.chunkGate.promise;
      const held = o.chunkGates && o.chunkGates[n];
      if (held) await held.promise;
      const c = chunkBundle();
      if (mode === "404" || "error" in c) return route.fulfill({ status: 404, contentType: "text/plain", body: "not found" });
      return route.fulfill({ status: 200, contentType: "text/javascript", body: mode === "empty" ? "/* registers nothing */" : c.js });
    }
    if (u.pathname.startsWith("/fonts/")) {
      if (o.fontGate) await o.fontGate.promise;
      const f = path.join(KATEX_DIST, "fonts", path.basename(u.pathname));
      if (fs.existsSync(f)) return route.fulfill({ status: 200, contentType: "font/woff2", body: fs.readFileSync(f) });
    }
    return route.fulfill({ status: 404, contentType: "text/plain", body: "" });
  });
  try {
    if (o.clock) await page.clock.install();
    await page.goto(ORIGIN + "/page", o.loadGate ? { waitUntil: "domcontentloaded" } : undefined);
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

/** Whether every formula in the box is laid out within `timeout` (no placeholder, no source fallback, at least one KaTeX root):
 *  false, not a throw, when the time runs out, so the scene's own assertion on the box says what stands instead. */
export const allLaidOut = (page: any, timeout = 15000): Promise<boolean> =>
  page.waitForFunction(() => !document.querySelector("#out .md-math-inline, #out .md-math-display, #out code.md-math-src") && !!document.querySelector("#out .katex"), null, { timeout })
    .then(() => true, () => false);

/** math.ts's own console lines (every one starts "math: "). */
export const said = (s: Scene): string[] => s.consoleErrors.filter((e) => e.startsWith("math: "));

/** The backstop's title, whatever the rest of the title says. */
const BACKSTOP_TITLE = new RegExp("^Not rendered: the math renderer did not load within " + MATH_CHUNK_BACKSTOP_MS / 1000 + " seconds[.;]");

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
    name: "a chunk that fails to load leaves every waiting formula as its source with the failure in its title and says so once; the failure's own fill asks for nothing; the next formula asks again, its fallback shown at once while the retry is out, and the retry, served, lays out every formula, the failure's fallbacks included",
    timeout: 60000,
    run: async (browser) => {
      const retry = gate();
      await withPage(browser, { chunk: ["404", "serve"], chunkGates: [null, retry] }, async (s) => {
        await show(s.page, "a $\\frac{1}{2}$ half\n\n$$e^{i\\pi}$$\n");
        await settled(s.page);
        let b = await box(s.page);
        assert.equal(b.katex, 0);
        assert.deepEqual(b.src.map((x) => x.text), ["\\frac{1}{2}", "e^{i\\pi}"], "each formula's TeX, never a blank");
        for (const x of b.src) assert.equal(x.title, "Not rendered: the math renderer failed to load.");
        await drain(s.page);
        await drain(s.page);
        assert.equal(s.chunkRequests(), 1, "the failure's own fill over the document uses no retry");
        assert.deepEqual(said(s), ["math: the math renderer failed to load; formulas are shown as their TeX source; the next formula asks for the renderer again"], "said once");
        await show(s.page, "later $z$ and\n\n$$w^2$$\n");
        b = await box(s.page);
        assert.deepEqual([b.src.length, b.pending.length], [4, 0], "the later formulas are source in the call that meets them: nothing waits on the retry");
        await drain(s.page);
        assert.equal(s.chunkRequests(), 2, "that fill used the retry the failure armed");
        await show(s.page, "and $v$ while it is out");
        await drain(s.page);
        assert.equal(s.chunkRequests(), 2, "one retry, used once");
        retry.open();
        const laid = await allLaidOut(s.page);
        b = await box(s.page);
        assert.ok(laid, "the served retry lays out every formula: " + JSON.stringify(b));
        assert.deepEqual([b.katex, b.src.length, b.pending.length], [5, 0, 0], "five formulas, none left as source, the failure's two included");
        assert.equal(await s.page.evaluate(() => document.querySelectorAll("#out [data-math-call], #out [data-math-failed]").length), 0, "no group stamp or failure mark is left");
        await show(s.page, "now $y_1$ at once");
        b = await box(s.page);
        assert.deepEqual([b.katex, b.pending.length], [6, 0], "with the engine in, a formula renders in the call that meets it");
        assert.equal(said(s).length, 1, "the success says nothing");
      });
    },
  },
  {
    name: "a failed load's fallbacks keep each message's group, so the retry's success charges the per-message budget per message: two messages each under it, shown as source by the failure, are laid out whole by the served retry",
    timeout: 120000,
    run: async (browser) => {
      const first = gate();
      await withPage(browser, { chunk: ["404", "serve"], chunkGates: [first] }, async (s) => {
        await show(s.page, message(3));
        await show(s.page, message(3));
        let b = await box(s.page);
        assert.deepEqual([b.pending.length, new Set(b.pending.map((p) => p.call)).size], [6, 2], "two messages of three formulas wait, each message under the budget, two groups");
        first.open();
        await settled(s.page);
        b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length], [0, 6], "the failure shows all six as source");
        // read now, asserted after the layout below, so a fallback that lost its group reds on what the reader sees first
        const groups: (string | null)[] = await s.page.evaluate(() => Array.from(document.querySelectorAll("#out [data-math-failed]")).map((e) => e.getAttribute("data-math-call")));
        await show(s.page, "then $z$");   // the next formula uses the retry the failure armed; served, its success lays out every formula
        const laid = await allLaidOut(s.page, 90000);
        b = await box(s.page);
        assert.ok(laid, "the served retry lays out every formula of both messages: " + JSON.stringify(b.src.map((x) => x.title)));
        assert.deepEqual([b.katex, b.src.length, b.pending.length, s.chunkRequests()], [7, 0, 0, 2],
          "seven formulas laid out, none left as source: each message is charged its own 56,997 characters, not the two together's 113,994");
        assert.equal(groups.length, 6, "the failure marked all six");
        assert.ok(groups.every((g) => !!g), "each fallback the failure made carries its call's group: " + JSON.stringify(groups));
        assert.equal(new Set(groups).size, 2, "the two messages' groups, one per message: " + JSON.stringify(groups));
      });
    },
  },
  {
    name: "a chunk that 404s for good costs two requests at any render rate, then one per online or reconnect event, each of the two arming on its own, and events before a formula arm one retry between them",
    timeout: 60000,
    run: async (browser) => {
      await withPage(browser, { chunk: "404" }, async (s) => {
        const renders = async (from: number, n: number) => {   // fills meeting formulas, as a streaming message re-renders at every delta
          for (let i = from; i < from + n; i++) await show(s.page, "render " + i + " $x_{" + i + "}$ and\n\n$$y_{" + i + "}$$\n");
          await drain(s.page);
          await drain(s.page);
        };
        await show(s.page, "first $a$");
        await settled(s.page);
        await renders(0, 6);
        assert.equal(s.chunkRequests(), 2, "the first request and the one retry its failure armed, at six renders");
        assert.equal(said(s).length, 2, "one line per failed attempt");
        assert.match(said(s)[1], /^math: the math renderer failed to load; formulas are shown as their TeX source; a formula after the connection comes back asks for it again$/);
        await s.page.evaluate(() => { window.dispatchEvent(new Event("online")); window.dispatchEvent(new Event("romp:wsup")); window.dispatchEvent(new Event("online")); });
        await drain(s.page);
        assert.equal(s.chunkRequests(), 2, "an event asks for nothing itself: the next fill that meets a formula does");
        await renders(6, 4);
        assert.equal(s.chunkRequests(), 3, "three events before the formula armed one retry, not three");
        // each event on its own, so neither stands in for the other: the window's online alone, then the shim's reconnect alone
        await s.page.evaluate(() => { window.dispatchEvent(new Event("online")); });
        await renders(10, 3);
        assert.equal(s.chunkRequests(), 4, "the window's online alone arms one");
        await s.page.evaluate(() => { window.dispatchEvent(new Event("romp:wsup")); });
        await renders(13, 3);
        assert.equal(s.chunkRequests(), 5, "the shim's reconnect alone arms one");
        await renders(16, 5);
        assert.equal(s.chunkRequests(), 5, "and no more without another event");
        const b = await box(s.page);
        assert.deepEqual([b.katex, b.pending.length, b.src.length], [0, 0, 43], "every formula is its source, none waits");
        assert.ok(b.src.every((x) => x.title === "Not rendered: the math renderer failed to load."), "each titled with the failure");
        assert.equal(said(s).length, 5, "one line per failed attempt: " + JSON.stringify(said(s)));
      });
    },
  },
  {
    name: "a retry while the first attempt is still out (stalled past its backstop) adds a fresh tag at once, the formula shown as its source; when the held answer lands every formula is laid out by one arrival, and the other tag's success is a no-op",
    timeout: 60000,
    run: async (browser, t) => {
      const first = gate();
      await withPage(browser, { chunkGate: first, clock: true }, async (s) => {
        const tags = (): Promise<number> => s.page.evaluate(() => document.querySelectorAll('script[src*="math-chunk.js"]').length);
        await show(s.page, "a $\\frac{1}{2}$ half");
        await drain(s.page);
        await s.page.clock.fastForward(MATH_CHUNK_BACKSTOP_MS + 1000);
        await settled(s.page);
        let b = await box(s.page);
        assert.deepEqual([b.src.length, s.chunkRequests(), await tags()], [1, 1, 1], "the backstop showed it as source; the first attempt's one tag and its request are still out");
        // the next formula uses the retry the backstop's failure armed, in the same task as the read below: a second tag, the formula
        // its source at once. The tags are what math.ts adds, and they are asserted. Whether the second tag is a second request is the
        // engine's: Chromium serves it from the fetch already in flight, WebKit and Firefox ask again (math.ts attempt), so the
        // count is reported below and not asserted, and a browser that changes how it reuses a fetch in flight cannot turn this red
        const r = await s.page.evaluate((src: string) => {
          const m = document.createElement("div"); m.className = "msg"; m.innerHTML = (window as any).__md(src); document.getElementById("out")!.appendChild(m);
          return { tags: document.querySelectorAll('script[src*="math-chunk.js"]').length, src: document.querySelectorAll("#out code.md-math-src").length,
            pending: document.querySelectorAll("#out .md-math-inline, #out .md-math-display").length };
        }, "then $z^2$");
        assert.deepEqual(r, { tags: 2, src: 2, pending: 0 }, "a fresh tag though the first attempt is out, and nothing waits on it: " + JSON.stringify(r));
        await drain(s.page);
        await drain(s.page);
        const held = s.chunkRequests();
        first.open();
        const laid = await allLaidOut(s.page);
        b = await box(s.page);
        assert.ok(laid, "the answer, once it lands, lays every formula out: " + JSON.stringify(b));
        await s.page.waitForFunction(() => (window as any).__settles >= 2, null, { timeout: 10000 });
        await drain(s.page);
        await drain(s.page);
        assert.equal(await s.page.evaluate(() => (window as any).__settles), 2, "two arrivals in all, the backstop's failure and one success: the second tag's success ran none");
        assert.deepEqual([b.katex, b.src.length], [2, 0]);
        assert.equal(await tags(), 2, "two tags in all, the first attempt's and the one retry's: the success adds none");
        assert.equal(said(s).length, 1, "and the success said nothing");
        t.diagnostic(browser.browserType().name() + ": chunk requests for the two tags, reported and not asserted: " + held + " while the first answer was held, " + s.chunkRequests() + " after it landed");
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
        assert.deepEqual(b.src.map((x) => x.title), ["Not rendered: the math renderer loaded but registered nothing."]);
        assert.equal(s.chunkRequests(), 1);
      });
    },
  },
  {
    name: "a page whose bundle ran from no tag with a src has no URL to derive the chunk's from: the formula falls back with the reason, nothing is requested, and the one attempt arms no retry, an online event included",
    timeout: 60000,
    run: async (browser) => {
      await withPage(browser, { inline: true }, async (s) => {
        await show(s.page, "a $q$ formula");
        await settled(s.page);
        let b = await box(s.page);
        assert.deepEqual(b.src.map((x) => x.title), ["Not rendered: no bundle script on this page to derive the math renderer's URL from."]);
        assert.deepEqual(said(s), ["math: no bundle script on this page to derive the math renderer's URL from; formulas are shown as their TeX source"], "said once, with no retry promised");
        await show(s.page, "then $r$");
        await s.page.evaluate(() => { window.dispatchEvent(new Event("online")); window.dispatchEvent(new Event("romp:wsup")); });
        await show(s.page, "and $t$");
        await drain(s.page);
        b = await box(s.page);
        assert.deepEqual([b.src.length, b.pending.length], [3, 0], "every formula falls back at once");
        assert.equal(said(s).length, 1, "one attempt, no second: " + JSON.stringify(said(s)));
        assert.equal(s.chunkRequests(), 0);
        assert.equal(await s.page.evaluate(() => document.querySelectorAll('script[src*="math-chunk"]').length), 0, "no script tag either");
      });
    },
  },
  {
    name: "with the chunk in and its faces still loading, a formula met then waits too: nothing is laid out before the faces, and the arrival lays out both",
    timeout: 60000,
    run: async (browser) => {
      const fg = gate();
      await withPage(browser, { fontGate: fg }, async (s) => {
        await show(s.page, "first $a^2$ here");
        await s.page.waitForFunction(() => !!(window as any).__rompKatex, null, { timeout: 10000 });
        await drain(s.page);
        await show(s.page, "then $b^2$ and\n\n$$c^2 + d^2$$\n");
        await drain(s.page);
        let b = await box(s.page);
        assert.deepEqual([b.katex, b.pending.length], [0, 3], "the chunk has registered and the faces have not: the later formulas wait with the first, none laid out early: " + JSON.stringify(b));
        fg.open();
        await settled(s.page);
        b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length, s.chunkRequests()], [3, 0, 1], "the arrival lays out all three");
      });
    },
  },
  {
    name: "a chunk that stalls past the backstop (MATH_CHUNK_BACKSTOP_MS) leaves each waiting formula as its source, the backstop's reason in its title, said once on the console; the held answer, a 404 at last, comes from an attempt that has already failed and is silent",
    timeout: 60000,
    run: async (browser) => {
      const g = gate();   // held past the backstop, then answered with a 404: the attempt's second failure end
      await withPage(browser, { chunk: "404", chunkGate: g, clock: true }, async (s) => {
        await show(s.page, "a $\\frac{1}{2}$ half\n\n$$e^{i\\pi}$$\n");
        await drain(s.page);
        let b = await box(s.page);
        assert.deepEqual([b.pending.length, b.katex, s.chunkRequests()], [2, 0, 1], "both wait while the chunk is out");
        await s.page.clock.fastForward(MATH_CHUNK_BACKSTOP_MS + 1000);
        await settled(s.page);
        b = await box(s.page);
        assert.equal(b.katex, 0);
        assert.deepEqual(b.src.map((x) => x.text), ["\\frac{1}{2}", "e^{i\\pi}"], "each formula's TeX, never a blank");
        for (const x of b.src) assert.match(x.title, BACKSTOP_TITLE);
        assert.equal(said(s).length, 1, "said once: " + JSON.stringify(s.consoleErrors));
        assert.match(said(s)[0], /^math: the math renderer did not load within 60 seconds; /);
        // the held answer now lands as a 404, the error end of an attempt its backstop already failed (math.ts attempt: a later failure
        // end is silent). The scene's own error listener on the tag was added after math.ts set the tag's onerror, so it runs after
        // that handler in the same dispatch: once it has counted the error, math.ts has handled it
        await s.page.evaluate(() => {
          const w = window as any; w.__lateErrors = 0;
          document.querySelector('script[src*="math-chunk.js"]')!.addEventListener("error", () => { w.__lateErrors++; });
        });
        g.open();
        await s.page.waitForFunction(() => (window as any).__lateErrors === 1, null, { timeout: 10000 });
        await drain(s.page);
        b = await box(s.page);
        assert.equal(said(s).length, 1, "the late 404 says nothing: the backstop's line stays the attempt's one line: " + JSON.stringify(said(s)));
        assert.equal(s.chunkRequests(), 1, "one request: no formula has met the retry the backstop armed");
        assert.ok(b.src.length === 2 && b.src.every((x) => BACKSTOP_TITLE.test(x.title)), "each fallback keeps the backstop's title: " + JSON.stringify(b.src));
      });
    },
  },
  {
    name: "faces that stall past the backstop with the chunk in: each formula is its source, said once; when the faces land after all, every formula is laid out, the backstop's fallbacks included",
    timeout: 60000,
    run: async (browser) => {
      const fg = gate();
      await withPage(browser, { fontGate: fg, clock: true }, async (s) => {
        await show(s.page, "a formula $\\alpha + \\beta$ here\n\n$$\\sum_{i=0}^{n} i^2$$\n");
        await s.page.waitForFunction(() => !!(window as any).__rompKatex, null, { timeout: 10000 });
        await drain(s.page);
        let b = await box(s.page);
        assert.deepEqual([b.katex, b.pending.length], [0, 2], "the chunk is in and the faces are not: both wait");
        await s.page.clock.fastForward(MATH_CHUNK_BACKSTOP_MS + 1000);
        await settled(s.page);
        b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length], [0, 2], "the backstop's failure shows each formula as its source, though the chunk had registered: " + JSON.stringify(b));
        for (const x of b.src) assert.match(x.title, BACKSTOP_TITLE);
        assert.equal(said(s).length, 1, "said once: " + JSON.stringify(s.consoleErrors));
        fg.open();
        const laid = await allLaidOut(s.page);
        b = await box(s.page);
        assert.ok(laid, "the faces landing after the backstop is a success: " + JSON.stringify(b));
        assert.deepEqual([b.katex, b.src.length, b.pending.length, s.chunkRequests()], [2, 0, 0, 1], "every formula laid out, the fallbacks included, with the one request");
        assert.equal(said(s).length, 1, "and nothing more said");
      });
    },
  },
  {
    name: "a chunk that lands after the backstop is a success: every formula is laid out, the backstop's fallbacks included",
    timeout: 60000,
    run: async (browser) => {
      const g = gate();
      await withPage(browser, { chunkGate: g, clock: true }, async (s) => {
        await show(s.page, "a $\\frac{1}{2}$ half\n\n$$e^{i\\pi}$$\n");
        await drain(s.page);
        await s.page.clock.fastForward(MATH_CHUNK_BACKSTOP_MS + 1000);
        await settled(s.page);
        let b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length], [0, 2], "the backstop showed both as source");
        g.open();
        const laid = await allLaidOut(s.page);
        b = await box(s.page);
        assert.ok(laid, "the late chunk lays out the backstop's fallbacks: " + JSON.stringify(b));
        assert.deepEqual([b.katex, b.src.length, s.chunkRequests()], [2, 0, 1], "both laid out, one request");
        assert.equal(said(s).length, 1, "the late success says nothing more");
      });
    },
  },
  {
    name: "a formula met before the page's own load event waits for it: no chunk script is added or requested until the document has loaded, and the backstop does not count that wait (past MATH_CHUNK_BACKSTOP_MS with the load held, the formula still waits); then the chunk is fetched and the formula laid out",
    timeout: 60000,
    run: async (browser) => {
      const lg = gate();
      await withPage(browser, { loadGate: lg, clock: true }, async (s) => {
        await show(s.page, "early $\\frac{a}{b}$ here");
        // read at once, with no wait: the fill appends a chunk tag synchronously, so one would be in the DOM by now; and while the page's
        // load is held WebKit runs no animation frame and defers a fetch, so a frame or a round trip (drain) would wait for that very load
        const st = await s.page.evaluate(() => ({ ready: document.readyState, scripts: document.querySelectorAll('script[src*="math-chunk"]').length }));
        let b = await box(s.page);
        assert.notEqual(st.ready, "complete", "the page's load is still held: " + JSON.stringify(st));
        assert.deepEqual([st.scripts, s.chunkRequests(), b.pending.length], [0, 0, 1], "no chunk script and no request before the load, the formula waiting: " + JSON.stringify([st, s.chunkRequests(), b]));
        // the backstop is armed in the deferred request step (math.ts attempt), so its 60 s count from the request: past them with the
        // load still held, no timer has run out. The clock's jump runs every timer due inside the evaluate it makes, and the reads after
        // it are evaluates too, so this holds in WebKit, which runs no frame while the load is held
        await s.page.clock.fastForward(MATH_CHUNK_BACKSTOP_MS + 5000);
        const late = await s.page.evaluate(() => ({ ready: document.readyState, scripts: document.querySelectorAll('script[src*="math-chunk"]').length }));
        b = await box(s.page);
        assert.notEqual(late.ready, "complete", "the load is held still: " + JSON.stringify(late));
        assert.deepEqual([late.scripts, b.pending.length, b.src.length], [0, 1, 0], "past the backstop's time with the load held: no tag, and the formula still waits, not shown as its source: " + JSON.stringify([late, b]));
        lg.open();
        await s.page.waitForFunction(() => document.readyState === "complete", null, { timeout: 10000, polling: 100 });   // a timed poll: no frame runs until the load (WebKit)
        await settled(s.page);
        b = await box(s.page);
        assert.deepEqual([b.katex, b.src.length, s.chunkRequests()], [1, 0, 1], "at the load the chunk is fetched and the formula laid out");
        assert.deepEqual(said(s), [], "and no failure was said");
      });
    },
  },
  {
    name: "a first-mode glossary term inside a formula still waiting for the renderer leaves the message's one link to the prose: the term pass skips a waiting formula as it skips a laid-out one, and the link outlasts the arrival",
    timeout: 60000,
    run: async (browser) => {
      const g = gate();
      await withPage(browser, { chunkGate: g }, async (s) => {
        const IX = { group: "notes-api", path: "~/.claude/glossaries/notes-api.md", skip: [], terms: [{ term: "quill", slug: "quill", definition: "", plainWords: "",
          also: [], scope: "", status: "active", registered: { date: "", by: "" }, link: "first" }] };
        const links = (): Promise<{ text: string; inFormula: boolean }[]> => s.page.evaluate(() => Array.from(document.querySelectorAll("#out .term-link"))
          .map((l) => ({ text: l.textContent || "", inFormula: !!l.closest(".md-math-inline, .md-math-display, .katex") })));
        const n = await s.page.evaluate(([src, ix]: [string, unknown]) => {
          const m = document.createElement("div"); m.className = "msg"; m.innerHTML = (window as any).__md(src); document.getElementById("out")!.appendChild(m);
          return (window as any).__terms(m, ix);
        }, ["The $quill + 1$ bound, and the quill in prose.", IX]);
        assert.equal(n, 1, "the message's one first-mode link");
        assert.deepEqual(await links(), [{ text: "quill", inFormula: false }], "made in the prose, not inside the waiting formula's TeX");
        g.open();
        await settled(s.page);
        assert.equal((await box(s.page)).katex, 1);
        assert.deepEqual(await links(), [{ text: "quill", inFormula: false }], "and still there once the formula is laid out");
      });
    },
  },
  {
    name: "an @name inside a formula still waiting for the renderer keeps its @ through the arrival: the mention pass (render.ts markMentions) skips a waiting formula as it skips code, and chips the same name in the prose",
    timeout: 60000,
    run: async (browser) => {
      const g = gate();
      await withPage(browser, { chunkGate: g }, async (s) => {
        const r0 = await s.page.evaluate((src: string) => {
          const m = document.createElement("div"); m.className = "msg"; m.innerHTML = (window as any).__md(src); document.getElementById("out")!.appendChild(m);
          const chips = (window as any).__chips({ sessions: new Map([["sid-api", { id: "sid-api", name: "api", status: { state: "ready" } }]]) });
          chips.markMentions(m);
          const ph = m.querySelector(".md-math-inline");
          return { tex: ph ? ph.textContent : null, chips: m.querySelectorAll(".mention-chip").length, inFormula: m.querySelectorAll(".md-math-inline .mention-chip").length };
        }, "ask @api about $a @api b$ today");
        assert.deepEqual(r0, { tex: "a @api b", chips: 1, inFormula: 0 }, "the prose @api is a chip; the waiting formula's TeX keeps its @: " + JSON.stringify(r0));
        g.open();
        await settled(s.page);
        const r1 = await s.page.evaluate(() => { const k = document.querySelector("#out .katex"); return { text: k ? k.textContent : null, chips: document.querySelectorAll("#out .mention-chip").length }; });
        assert.ok(r1.text !== null && r1.text.includes("@"), "the laid-out formula still reads its @: " + JSON.stringify(r1));
        assert.equal(r1.chips, 1);
      });
    },
  },
  {
    name: "in the user's own bubble a waiting formula, inline and display, wears the bubble's white tint, not the page's dim tier, and reads at 3:1 or better on the bubble's fill, in both themes",
    timeout: 60000,
    run: async (browser) => {
      for (const light of [false, true]) {
        const g = gate();
        await withPage(browser, { chunkGate: g, bubble: true, light }, async (s) => {
          await show(s.page, "you asked about $\\frac{a}{b}$ and\n\n$$\\sum_{i=1}^{n} i$$\n");
          const r: { display: boolean; color: string; ratio: number }[] = await s.page.evaluate(() => {
            const rgba = (c: string): number[] => { const v = (c.match(/[\d.]+/g) || []).map(Number); return [v[0], v[1], v[2], v.length > 3 ? v[3] : 1]; };
            const lum = (c: number[]): number => { const f = (x: number) => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
            const fill = rgba(getComputedStyle(document.getElementById("bubble")!).backgroundColor);
            return Array.from(document.querySelectorAll("#out .md-math-inline, #out .md-math-display")).map((e) => {
              const color = getComputedStyle(e).color;
              const c = rgba(color);
              const seen = [0, 1, 2].map((i) => c[3] * c[i] + (1 - c[3]) * fill[i]);   // the tint over the fill, as it is seen
              const [hi, lo] = [lum(seen), lum(fill)].sort((x, y) => y - x);
              return { display: e.classList.contains("md-math-display"), color, ratio: Math.round(((hi + 0.05) / (lo + 0.05)) * 100) / 100 };
            });
          });
          const dim = (await box(s.page)).dim;
          const theme = light ? "light" : "dark";
          assert.deepEqual(r.map((x) => x.display), [false, true], theme + ": both waiting, inline and display: " + JSON.stringify(r));
          for (const x of r) {
            assert.equal(x.color, "rgba(255, 255, 255, 0.88)", theme + ": the bubble's tint (styles.css .user-bubble .md-math-inline, .md-math-display): " + JSON.stringify(x));
            assert.notEqual(x.color, dim, theme + ": not the page's dim tier, which sits near 1.5:1 on the fill");
            assert.ok(x.ratio >= 3, theme + ": at least 3:1 on the bubble's fill: " + JSON.stringify(x));
          }
          g.open();
          await settled(s.page);
        });
      }
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
