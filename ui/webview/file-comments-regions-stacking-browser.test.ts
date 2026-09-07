// A rectangle inside another can be clicked (plans/file-review.md, Slice 3; the 2026-09-06 review of the slice):
// headless Chromium drives the worktree's file-comments-regions.ts and actions.ts, bundled the way the webview is
// built, under the sheet's own rules. The rectangles are absolutely positioned siblings with no z-index, so the
// browser hits the one appended LAST first; painted in card order, a whole-plot comment made after a detail comment
// covered the detail's rectangle, and a click at the detail's centre opened the plot's card — with the panel closed
// (the browser's own hit test resolved the click) and open (the layer handed the press on to the rectangle it
// began on) alike. paint() now appends the rectangles largest first. This is the leg a stand-in cannot stand in
// for: the browser's hit test. A control re-creates card order in the page and shows the leg sees the defect it
// guards. Skips LOUDLY without a playwright browser (CI installs none), as file-comments-regions-browser.test.ts
// does. Synthetic values only: a picture painted on a canvas, placeholder ids, the notes-api world's session name.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The layer and the delegate, bundled as the webview build bundles them (in memory), handed to the page as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { RegionLayer } from "./file-comments-regions";\nimport { delegate } from "./actions";\n(window as any).__romp = { RegionLayer, delegate };\n',
      resolveDir: UI, loader: "ts", sourcefile: "regions-stacking-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layer lives under: the media body's picture, and the whole file-comments block. */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [rule(".fileview-imgbox"), rule(".fileview-img"), FEED.slice(a, b)].join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 20px; }
${sheet()}</style></head><body><div class="fileview-body" id="row"></div><script src="/dist/regions.js"></script></body></html>`;

type Box = { left: number; top: number; width: number; height: number };
type Scene = { img: Box; rects: Record<string, Box>; order: string[] };
/** Card order is creation order: the axis label was commented first, the whole plot around it after. */
const MARKS = [
  { id: "c1", region: { x: 0.4, y: 0.4, w: 0.1, h: 0.1 }, label: "you", state: "current" },
  { id: "c2", region: { x: 0.1, y: 0.1, w: 0.8, h: 0.8 }, label: "api", state: "current" },
];

/** Mount the media body's picture (a 400×300 canvas) in the viewer's body row, put the layer over it with the marks
 *  painted, wire the panel's delegate on the row (once), and report where everything is. */
function setup(page: any, marks: unknown[], active: boolean): Promise<Scene> {
  return page.evaluate(async ([marks, active]: [unknown[], boolean]) => {
    const w = window as any;
    if (w.__layer) w.__layer.dispose();
    const row = document.getElementById("row")!;
    row.replaceChildren();
    const c = document.createElement("canvas"); c.width = 400; c.height = 300;
    const cx = c.getContext("2d")!; cx.fillStyle = "#336699"; cx.fillRect(0, 0, 400, 300); cx.fillStyle = "#ffcc00"; cx.fillRect(0, 0, 200, 150);
    const box = document.createElement("div"); box.className = "fileview-imgbox"; box.style.width = "400px"; box.style.height = "300px";
    const img = document.createElement("img"); img.className = "fileview-img"; box.appendChild(img); row.appendChild(box);
    img.src = c.toDataURL("image/png");
    await img.decode();
    const calls: string[] = []; w.__calls = calls;
    if (!w.__wired) {
      w.__romp.delegate(row, { fcopen: (el: HTMLElement) => { w.__calls.push("fcopen:" + el.dataset.id); } });
      w.__wired = true;
    }
    const layer = new w.__romp.RegionLayer(img, {
      onDraw: () => { w.__calls.push("onDraw"); },
      onClick: () => { w.__calls.push("onClick"); },
      onPress: () => { w.__calls.push("press"); },
    });
    w.__layer = layer;
    layer.setActive(active);
    layer.paint(marks, null, false);
    const r = (el: Element) => { const b = el.getBoundingClientRect(); return { left: b.left, top: b.top, width: b.width, height: b.height }; };
    const rects: Record<string, { left: number; top: number; width: number; height: number }> = {};
    const order: string[] = [];
    for (const el of Array.from(layer.overlay.querySelectorAll(".fc-region")) as HTMLElement[]) { rects[el.dataset.id!] = r(el); order.push(el.dataset.id!); }
    return { img: r(img), rects, order };
  }, [marks, active]);
}
const calls = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__calls.splice(0));
const at = (b: Box, fx: number, fy: number): [number, number] => [b.left + b.width * fx, b.top + b.height * fy];
/** What the browser's hit test finds at a point: the rectangle's comment id, or the element's class. */
const hit = (page: any, p: [number, number]): Promise<string> => page.evaluate(([x, y]: [number, number]) => {
  const el = document.elementFromPoint(x, y) as HTMLElement | null;
  const r = el ? (el.closest(".fc-region") as HTMLElement | null) : null;
  return r ? "rect:" + r.dataset.id : el ? el.className || el.tagName : "(nothing)";
}, p);

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
    const page = await browser.newPage({ viewport: { width: 1000, height: 900 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/regions.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

test("in a browser, panel closed and open: the browser hits the rectangle inside the other at its centre, and a real click there opens ITS card; the enclosing rectangle still opens from the part it has to itself", async (t) => {
  await inBrowser(t, async (page) => {
    for (const active of [false, true]) {
      const s = await setup(page, MARKS, active);
      const state = active ? "panel open" : "panel closed";
      assert.deepEqual(s.order, ["c2", "c1"], state + ": the whole plot's rectangle goes down first, the detail's over it");
      const inner = at(s.rects.c1, 0.5, 0.5);            // the detail's centre: inside both rectangles
      const outer = at(s.rects.c2, 0.1, 0.1);            // inside the plot's rectangle, outside the detail's
      assert.equal(await hit(page, inner), "rect:c1", state + ": the hit test at the detail's centre is the detail");
      assert.equal(await hit(page, outer), "rect:c2", state + ": the plot's rectangle where the detail does not cover it");
      const prefix = active ? ["press"] : [];            // armed, the layer's onPress runs first and the press is handed on
      await page.mouse.click(...inner);
      assert.deepEqual(await calls(page), [...prefix, "fcopen:c1"], state + ": the click at the detail's centre opens the detail's card");
      await page.mouse.click(...outer);
      assert.deepEqual(await calls(page), [...prefix, "fcopen:c2"], state + ": the plot's card from its own part");
      // the control: card order in the page (the plot's rectangle appended after the detail's), as paint() had it —
      // the enclosing rectangle takes the detail's centre, so this leg sees the defect it guards
      await page.evaluate(() => {
        const o = (window as any).__layer.overlay as HTMLElement;
        o.appendChild(o.querySelector('.fc-region[data-id="c2"]')!);
      });
      assert.equal(await hit(page, inner), "rect:c2", state + ": in card order the detail is unreachable from the mouse");
      await page.mouse.click(...inner);
      assert.deepEqual(await calls(page), [...prefix, "fcopen:c2"], state + ": and its centre opened the wrong card");
    }
  });
});
