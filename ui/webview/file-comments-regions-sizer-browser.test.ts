// The overlay follows a picture whose column changes width, in a real layout engine (plans/file-review.md, Slice 3:
// the rectangle re-paints correctly at any viewer width; the 2026-09-06 review of the slice). The layer's
// ResizeObserver is the exact event for "the drawn size changed" — the aside opening narrows the body with no window
// resize — and it observes the picture AND its wrapper. Only a browser can show what the second observation is for:
// a `width="100%"` figure capped by `max-width: 300px` with a `margin-top: 10%` gets a wrapper that carries the
// percentage (the whole column) while the picture stays 300px wide, so narrowing the column moves the picture up
// inside the wrapper WITHOUT changing its size — the picture's observation stays silent, the wrapper's fires, and
// place()'s pixel offsets against the wrapper follow. The stand-in (file-comments-regions-sizer.test.ts) drives a
// fake observer with the numbers measured here; this leg measures them. A control constructs the layer under an
// observer that drops the wrapper (what deleting `observe(this.wrap)` does) and requires the overlay to be left
// behind, so the leg is known to see the defect it guards.
// Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: a picture painted on a canvas.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The layer, bundled as the webview build bundles it (in memory), handed to the page as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { RegionLayer } from "./file-comments-regions";\n(window as any).__romp = { RegionLayer };\n',
      resolveDir: UI, loader: "ts", sourcefile: "regions-sizer-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the figure lives under: the viewer's rendered-markdown pictures and paragraphs, and the whole
 *  file-comments block (the wrapper, the overlay). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [rule(".fileview-md img"), rule(".fileview-md p"), FEED.slice(a, b)].join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 20px; font: 16px/1.5 sans-serif; } .fileview-md { width: 600px; }
${sheet()}</style></head><body><div class="fileview-body" id="row"><div class="fileview-md" id="md"></div></div><script src="/dist/regions.js"></script></body></html>`;

type Box = { left: number; top: number; width: number; height: number };
type Scene = { plot: Box; wrap: Box | null; overlay: Box | null; overlayStyle: string | null; events: string[] };

/** The README: one figure, a 300×150 picture written `width="100%"` with a pixel max-width and a percentage top margin. */
async function mount(page: any): Promise<void> {
  await page.evaluate(async () => {
    const md = document.getElementById("md")!;
    md.style.width = "600px";
    md.replaceChildren();
    const c = document.createElement("canvas"); c.width = 300; c.height = 150;
    const cx = c.getContext("2d")!; cx.fillStyle = "#336699"; cx.fillRect(0, 0, 300, 150); cx.fillStyle = "#ffcc00"; cx.fillRect(0, 0, 150, 75);
    md.innerHTML = '<p id="p-plot"><img id="plot" width="100%" style="max-width:300px;margin-top:10%"></p><p id="after">After the figure.</p>';
    const img = document.getElementById("plot") as HTMLImageElement;
    img.src = c.toDataURL("image/png");
    await img.decode();
  });
}
/** Wrap the figure the way paintRegions does with the panel open, under an observer that records which element each
 *  callback was for — and, for the control, one that drops the wrapper from what it observes. */
const wrap = (page: any, control: boolean): Promise<void> => page.evaluate((control: boolean) => {
  const w = window as any;
  const Real = window.ResizeObserver;
  w.__events = [] as string[];
  class Recording extends Real {
    constructor(cb: ResizeObserverCallback) {
      super((entries, o) => { for (const e of entries) w.__events.push((e.target as Element).tagName + "." + (e.target as Element).className); cb(entries, o); });
    }
    observe(t: Element): void { if (control && t.classList.contains("fc-imgwrap")) return; super.observe(t); }
  }
  (window as any).ResizeObserver = Recording;
  try {
    w.__layer = new w.__romp.RegionLayer(document.getElementById("plot"), { onDraw: () => {}, onClick: () => {} });
    w.__layer.setActive(true);
    w.__layer.paint([], null, false);
  } finally { (window as any).ResizeObserver = Real; }
}, control);
/** Set the column's width — the body narrowing under an aside, with no window resize — and let the observers run. */
const column = (page: any, px: number): Promise<void> => page.evaluate(async (px: number) => {
  document.getElementById("md")!.style.width = px + "px";
  // observations are delivered in the rendering steps after layout: two frames are past them
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
}, px);
const measure = (page: any): Promise<Scene> => page.evaluate(() => {
  const w = window as any;
  const box = (el: Element | null): Box | null => { if (!el) return null; const b = el.getBoundingClientRect(); return { left: b.left, top: b.top, width: b.width, height: b.height }; };
  const l = w.__layer;
  return { plot: box(document.getElementById("plot"))!, wrap: l ? box(l.wrap) : null, overlay: l ? box(l.overlay) : null, overlayStyle: l ? l.overlay.getAttribute("style") : null, events: (w.__events || []).splice(0) };
});
const dispose = (page: any): Promise<void> => page.evaluate(() => { const w = window as any; if (w.__layer) { w.__layer.dispose(); w.__layer = null; } });

const sameBox = (a: Box | null, b: Box | null, msg: string) => {
  assert.ok(a && b, msg + " (a box each)");
  for (const k of ["left", "top", "width", "height"] as const) assert.ok(Math.abs(a![k] - b![k]) < 0.5, msg + " (" + k + ": " + a![k] + " vs " + b![k] + ")");
};

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box — the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const page = await browser.newPage({ viewport: { width: 1000, height: 1400 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/regions.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await mount(page);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

test("in a browser, narrowing the column under a figure whose wrapper outgrows it moves the picture without resizing it, and the overlay follows through the wrapper's own observation; the control that drops it leaves the overlay behind", async (t) => {
  await inBrowser(t, async (page) => {
    const before = (await measure(page)).plot;
    sameBox(before, { left: 20, top: 88, width: 300, height: 150 }, "the figure: 300px (capped), 60px down (10% of the 600px column) under the paragraph's margin");
    // the layer: the wrapper carries width="100%" (the whole column), the picture stays 300px inside it
    await wrap(page, false);
    await column(page, 600);
    let s = await measure(page);
    sameBox(s.plot, before, "wrapping moved nothing");
    sameBox(s.wrap, { left: 20, top: 28, width: 600, height: 210 }, "the wrapper outgrows the picture: the column's width, the margin and the picture tall");
    sameBox(s.overlay, s.plot, "the overlay is the picture");
    assert.equal(s.overlayStyle, "left: 0px; top: 60px; width: 300px; height: 150px;", "pixel offsets against the wrapper");
    // the aside opens: the column narrows to 400px with no window resize. The picture is the same 300×150, 40px down now
    await column(page, 400);
    s = await measure(page);
    sameBox(s.plot, { left: 20, top: 68, width: 300, height: 150 }, "the picture moved up 20px, its size unchanged");
    sameBox(s.wrap, { left: 20, top: 28, width: 400, height: 190 }, "the wrapper narrowed with the column");
    assert.deepEqual(s.events, ["SPAN.fc-imgwrap"], "only the wrapper's observation fired: the picture's had no size change to report");
    sameBox(s.overlay, s.plot, "the overlay followed the picture");
    assert.equal(s.overlayStyle, "left: 0px; top: 40px; width: 300px; height: 150px;");
    // narrower than the picture: the picture itself shrinks, and its own observation fires too
    await column(page, 200);
    s = await measure(page);
    sameBox(s.plot, { left: 20, top: 48, width: 200, height: 100 }, "the picture shrinks with the column");
    assert.ok(s.events.includes("IMG.") && s.events.includes("SPAN.fc-imgwrap"), "both observations fired: " + JSON.stringify(s.events));
    sameBox(s.overlay, s.plot, "the overlay is the smaller picture");
    assert.equal(s.overlayStyle, "left: 0px; top: 20px; width: 200px; height: 100px;");
    // back to the full column, then dispose: the picture where it was, and nothing left standing over it
    await column(page, 600);
    s = await measure(page);
    sameBox(s.overlay, s.plot, "the overlay is the picture again at the full width");
    await dispose(page);
    await column(page, 400);
    await column(page, 600);
    sameBox((await measure(page)).plot, before, "the picture as it was, the layer gone");
    assert.equal(await page.evaluate(() => document.querySelectorAll(".fc-imgwrap").length), 0);
    // the control: an observer that never watches the wrapper — the overlay stays where the picture was
    await wrap(page, true);
    await column(page, 600);
    s = await measure(page);
    sameBox(s.overlay, s.plot, "control: placed right at first");
    await column(page, 400);
    s = await measure(page);
    sameBox(s.plot, { left: 20, top: 68, width: 300, height: 150 }, "control: the picture moved up");
    assert.deepEqual(s.events, [], "control: nothing fired — the picture's size did not change and the wrapper is not observed");
    assert.equal(s.overlayStyle, "left: 0px; top: 60px; width: 300px; height: 150px;", "control: the offsets went stale");
    sameBox(s.overlay, { left: 20, top: 88, width: 300, height: 150 }, "control: the overlay is 20px below the picture — rectangles drawn over pixels that hold no picture");
    await dispose(page);
    await column(page, 600);
  });
});
