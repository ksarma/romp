// The region layer must not move the author's figures (plans/file-review.md, Slice 3; the 2026-09-06 review of the
// slice). Wrapping a picture puts a `span.fc-imgwrap` (inline-block, hugging a block picture) where the picture
// stood, and until carriedLayout (file-comments-regions.ts) the wrapper carried none of the picture's own place in
// the flow: a width="100%" plot resolved its percentage against the shrink-wrapped span and collapsed to its natural
// width, a right-aligned logo floated INSIDE the span and the prose stopped flowing beside it, a centered block
// figure jumped to the left. Opening the panel reflowed every figure in a README, and a figure with one region
// comment stayed reflowed with the panel closed. Only a layout engine can show this, so headless Chromium lays out
// a 600px `.fileview-md` column under feed.css's own rules, measures every figure and paragraph, wraps them the way
// paintRegions does, and requires the same numbers — then the numbers the finding measured from a CONTROL wrap
// with nothing carried, so the leg is known to see the defect it guards. Two guards the stand-in also pins are
// driven with a real pointer here: the rubber band across a mid-drag paint pass, and the non-primary buttons.
// Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: pictures painted on a canvas,
// placeholder ids.
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
      resolveDir: UI, loader: "ts", sourcefile: "regions-layout-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the figures live under: the viewer's rendered-markdown pictures and paragraphs, and the whole
 *  file-comments block (the wrapper, the overlay, the rectangles). */
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
type Scene = Record<string, Box>;
const FIGURES = ["plot", "logo", "centered", "half", "badge"];
const BOXES = [...FIGURES, "p-plot", "p-logo", "p-centered", "p-half", "p-badge", "after"];

/** The README: a full-width plot, a right-aligned logo with prose beside it, a centered block figure, a centered
 *  half-width one, a badge on a text line, and a paragraph after them all. Every picture is 300×150. */
async function mount(page: any): Promise<void> {
  await page.evaluate(async () => {
    const md = document.getElementById("md")!;
    md.replaceChildren();
    const c = document.createElement("canvas"); c.width = 300; c.height = 150;
    const cx = c.getContext("2d")!; cx.fillStyle = "#336699"; cx.fillRect(0, 0, 300, 150); cx.fillStyle = "#ffcc00"; cx.fillRect(0, 0, 150, 75);
    const src = c.toDataURL("image/png");
    const prose = "The notes API keeps every note in one place and serves it back in the order it was written, so the web session and the tests session read the same story. ".repeat(3);
    md.innerHTML = [
      '<p id="p-plot"><img id="plot" width="100%"></p>',
      '<p id="p-logo"><img id="logo" align="right" width="120"> ' + prose + "</p>",
      '<p id="p-centered"><img id="centered" style="display:block;margin:0 auto"></p>',
      '<p id="p-half"><img id="half" style="display:block;margin:0 auto" width="50%"></p>',
      '<p id="p-badge">Build: <img id="badge" align="middle" width="60"> passing, on every push.</p>',
      '<p id="after">After the figures.</p>',
    ].join("\n");
    const imgs = Array.from(md.querySelectorAll("img")) as HTMLImageElement[];
    for (const i of imgs) i.src = src;
    await Promise.all(imgs.map((i) => i.decode()));
    (window as any).__calls = [];
  });
}
const measure = (page: any): Promise<Scene> => page.evaluate((ids: string[]) => {
  const out: Record<string, Box> = {};
  for (const id of ids) { const b = document.getElementById(id)!.getBoundingClientRect(); out[id] = { left: b.left, top: b.top, width: b.width, height: b.height }; }
  return out;
}, BOXES);
/** Wrap every figure the way paintRegions does with the panel open: a layer each, armed, painted with nothing. */
const wrapAll = (page: any): Promise<Array<{ overlay: Box; wrapStyle: string | null; imgStyle: string | null }>> => page.evaluate((ids: string[]) => {
  const w = window as any;
  w.__layers = ids.map((id) => {
    const img = document.getElementById(id) as HTMLImageElement;
    const layer = new w.__romp.RegionLayer(img, {
      onDraw: (_i: unknown, r: unknown) => { w.__calls.push("onDraw:" + JSON.stringify(r)); },
      onClick: () => { w.__calls.push("onClick"); },
      onPress: () => { w.__calls.push("press"); },
    });
    layer.setActive(true);
    layer.paint([], null, false);
    return layer;
  });
  return w.__layers.map((l: any) => {
    const b = l.overlay.getBoundingClientRect();
    return { overlay: { left: b.left, top: b.top, width: b.width, height: b.height }, wrapStyle: l.wrap.getAttribute("style"), imgStyle: l.img.getAttribute("style") };
  });
}, FIGURES);
const disposeAll = (page: any): Promise<Array<string | null>> => page.evaluate((ids: string[]) => {
  const w = window as any;
  for (const l of w.__layers) l.dispose();
  w.__layers = [];
  return ids.map((id) => document.getElementById(id)!.getAttribute("style"));
}, FIGURES);
/** The control: the wrap as it was before carriedLayout — a bare span.fc-imgwrap around the picture, nothing carried. */
const controlWrap = (page: any, on: boolean): Promise<void> => page.evaluate(([ids, on]: [string[], boolean]) => {
  for (const id of ids) {
    const img = document.getElementById(id)!;
    if (on) { const s = document.createElement("span"); s.className = "fc-imgwrap"; img.parentNode!.insertBefore(s, img); s.appendChild(img); }
    else { const s = img.parentNode as HTMLElement; s.parentNode!.insertBefore(img, s); s.remove(); }
  }
}, [FIGURES, on]);
const calls = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__calls.splice(0));

const sameBox = (a: Box, b: Box, msg: string) => { for (const k of ["left", "top", "width", "height"] as const) assert.ok(Math.abs(a[k] - b[k]) < 0.5, msg + " (" + k + ": " + a[k] + " vs " + b[k] + ")"); };
const sameScene = (a: Scene, b: Scene, msg: string) => { for (const id of BOXES) sameBox(a[id], b[id], msg + ": " + id); };
const near = (a: number, b: number, msg: string) => assert.ok(Math.abs(a - b) < 0.011, msg + ": " + a + " vs " + b);

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

test("in a browser, wrapping every figure of a README leaves the page as the browser laid it out, the overlay is each picture, and dispose restores the pictures' own style; a bare wrapper (the control) reflows it", async (t) => {
  await inBrowser(t, async (page) => {
    const before = await measure(page);
    // the scene is the one the finding describes
    sameBox(before.plot, { left: 20, top: before.plot.top, width: 600, height: 300 }, "the plot fills the column: width=\"100%\" of 600px, its aspect held");
    assert.ok(Math.abs(before.logo.left - 500) < 0.5, "the logo floats right: left 500 (= 20 + 600 - 120), got " + before.logo.left);
    assert.ok(Math.abs(before.logo.top - before["p-logo"].top) < 0.5, "the logo floats at the paragraph's top, the prose beside it (the control below shows the paragraph grow when it stops)");
    assert.ok(Math.abs(before.centered.left - 170) < 0.5, "the block figure is centered: left 170 (= 20 + (600 - 300) / 2), got " + before.centered.left);
    sameBox(before.half, { left: 170, top: before.half.top, width: 300, height: 150 }, "the half-width block figure: 300px, centered");
    assert.ok(before.badge.top >= before["p-badge"].top - 0.5 && before.badge.top + before.badge.height <= before["p-badge"].top + before["p-badge"].height + 0.5,
      "the badge sits on its text line: badge " + JSON.stringify(before.badge) + " in " + JSON.stringify(before["p-badge"]));
    // the control: the wrap as it was, nothing carried — the finding's numbers
    await controlWrap(page, true);
    const control = await measure(page);
    assert.ok(Math.abs(control.plot.width - 300) < 0.5, "control: the plot collapses to its natural width (" + control.plot.width + ")");
    assert.ok(Math.abs(control.logo.left - 20) < 0.5, "control: the logo jumps to the left edge (" + control.logo.left + ")");
    assert.ok(control["p-logo"].height > before["p-logo"].height + 20, "control: the prose is pushed below the logo (" + control["p-logo"].height + " vs " + before["p-logo"].height + ")");
    assert.ok(Math.abs(control.centered.left - 20) < 0.5, "control: the centered figure jumps left (" + control.centered.left + ")");
    await controlWrap(page, false);
    sameScene(await measure(page), before, "the control undone");
    // the layer: every figure wrapped as paintRegions wraps them with the panel open
    const layers = await wrapAll(page);
    const after = await measure(page);
    sameScene(after, before, "every figure and paragraph where it was, the panel open");
    for (let i = 0; i < FIGURES.length; i++) sameBox(layers[i].overlay, after[FIGURES[i]], "the overlay is the picture: " + FIGURES[i]);
    assert.equal(layers[0].wrapStyle, "width: 100%;", "the plot's wrapper takes the percentage"); assert.equal(layers[0].imgStyle, "width: 100%;", "and the plot fills it");
    assert.equal(layers[1].wrapStyle, "float: right;", "the logo's wrapper takes the float"); assert.equal(layers[1].imgStyle, "float: none;");
    assert.equal(layers[2].imgStyle, "display:block;margin:0 auto; margin-left: 0; margin-right: 0;", "the author's declarations kept, the layer's after them");
    // dispose: the pictures back, their style attributes as the author wrote them
    const styles = await disposeAll(page);
    assert.deepEqual(styles, [null, null, "display:block;margin:0 auto", "display:block;margin:0 auto", null], "each picture's style attribute is what the author wrote — or absent, as it was");
    sameScene(await measure(page), before, "the layers gone");
    assert.equal(await page.evaluate(() => document.querySelectorAll(".fc-imgwrap").length), 0);
    // the closed-panel state a region comment leaves: one figure wrapped, disarmed, with its rectangle — still in place
    await page.evaluate(() => {
      const w = window as any;
      const l = new w.__romp.RegionLayer(document.getElementById("logo"), { onDraw: () => {}, onClick: () => {} });
      l.setActive(false); l.paint([{ id: "c1", region: { x: 0.1, y: 0.1, w: 0.5, h: 0.5 }, label: "you", state: "current" }], null, false);
      w.__layers = [l];
    });
    sameScene(await measure(page), before, "a README whose logo carries a region comment, panel closed");
    await disposeAll(page);
  });
});

test("in a browser, a paint pass mid-drag keeps the rubber band the person is drawing, and a right or middle button neither draws nor offers Comment", async (t) => {
  await inBrowser(t, async (page) => {
    await wrapAll(page);
    const plot = (await measure(page)).plot;
    const at = (fx: number, fy: number): [number, number] => [plot.left + plot.width * fx, plot.top + plot.height * fy];
    // the mid-drag paint pass
    await page.mouse.move(...at(0.2, 0.2)); await page.mouse.down(); await page.mouse.move(...at(0.5, 0.5), { steps: 4 });
    const mid = await page.evaluate(() => {
      const l = (window as any).__layers[0];
      const band = l.overlay.querySelector(".fc-draw");
      const styled = band ? band.getAttribute("style") : null;
      l.paint([{ id: "c1", region: { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }, label: "you", state: "current" }], { x: 0.6, y: 0.6, w: 0.2, h: 0.2 }, false);
      const again = l.overlay.querySelector(".fc-draw");
      return { had: !!band, styled, same: again === band, attached: !!again && again.parentNode === l.overlay, last: !!again && l.overlay.lastElementChild === again, rects: l.overlay.querySelectorAll(".fc-region").length };
    });
    assert.ok(mid.had, "the band was drawn before the pass");
    assert.ok(mid.same && mid.attached, "the same band node is in the overlay after the pass");
    assert.ok(mid.last, "above the rectangle and the pending region the pass drew");
    assert.equal(mid.rects, 3);
    await page.mouse.move(...at(0.7, 0.8), { steps: 2 });
    const restyled = await page.evaluate(() => (window as any).__layers[0].overlay.querySelector(".fc-draw").getAttribute("style"));
    assert.notEqual(restyled, mid.styled, "the move after the pass styles the band the person sees");
    await page.mouse.up();
    const c = await calls(page);
    const s = c.find((x) => x.startsWith("onDraw:"));
    assert.ok(s, "the release draws: " + JSON.stringify(c));
    const r = JSON.parse(s!.slice("onDraw:".length));
    near(r.x, 0.2, "x"); near(r.y, 0.2, "y"); near(r.w, 0.5, "w"); near(r.h, 0.6, "h");
    assert.equal(await page.evaluate(() => (window as any).__layers[0].overlay.querySelectorAll(".fc-draw").length), 0, "the band is down after the release");
    // the non-primary buttons: the context menu's gesture over a plain picture offers nothing, a right or middle drag draws nothing
    await page.mouse.click(...at(0.8, 0.8), { button: "right" });
    assert.deepEqual(await calls(page), [], "a right click: no press, no Comment offer — the context menu is the browser's");
    await page.mouse.move(...at(0.6, 0.6)); await page.mouse.down({ button: "right" }); await page.mouse.move(...at(0.9, 0.9), { steps: 4 }); await page.mouse.up({ button: "right" });
    assert.deepEqual(await calls(page), [], "a right-button drag draws no region");
    await page.mouse.move(...at(0.6, 0.6)); await page.mouse.down({ button: "middle" }); await page.mouse.move(...at(0.9, 0.9), { steps: 4 }); await page.mouse.up({ button: "middle" });
    assert.deepEqual(await calls(page), [], "a middle-button drag draws no region");
    assert.equal(await page.evaluate(() => (window as any).__layers[0].overlay.querySelectorAll(".fc-draw").length), 0, "no band from either");
    // the primary button still does
    await page.mouse.click(...at(0.8, 0.8));
    assert.deepEqual(await calls(page), ["press", "onClick"], "a left click on the plain picture is the panel's");
    await disposeAll(page);
  });
});
