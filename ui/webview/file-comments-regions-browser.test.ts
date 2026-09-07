// The region layer under a REAL pointer (plans/file-review.md, Slice 3; the 2026-09-06 review of the slice):
// headless Chromium drives the worktree's file-comments-regions.ts and actions.ts, bundled the way the webview is
// built, under the sheet's own rules for the wrapper, the overlay, the rectangles and the viewer's pictures. This
// is the leg no stand-in can stand in for: the browser decides where a captured pointer's click goes — to the
// CAPTURING element, the overlay, which is how a click on a rectangle or on a framed picture opened nothing while
// the panel was open — and the browser lays the picture out: a rendered-markdown figure with width and height
// attributes is drawn under whatever `object-fit` the sheet gives `.fileview-md img`, and the overlay must sit where
// the picture's pixels are either way. Skips LOUDLY without a playwright browser (CI installs none), as
// waiting-link-focus.test.ts does. Synthetic values only: a picture painted on a canvas, placeholder ids.
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
      resolveDir: UI, loader: "ts", sourcefile: "regions-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layer lives under: the viewer's pictures, and the whole file-comments block. */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [rule(".fileview-md img"), rule(".fileview-imgbox"), rule(".fileview-img"), FEED.slice(a, b)].join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 20px; } .fileview-md { width: 600px; } p { margin: 0; }
${sheet()}</style></head><body><div class="fileview-body" id="row"></div><script src="/dist/regions.js"></script></body></html>`;

type Box = { left: number; top: number; width: number; height: number };
type Scene = { img: Box; overlay: Box; rect: Box | null; style: string | null; fit: string; natural: number[] };
type Kind = "md" | "md-sized" | "media" | "media-square";
const MARK = { id: "c1", region: { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 }, label: "you", state: "current" };

/** Mount one picture in the viewer's body row — a figure in rendered markdown (plain, or with the width/height pair
 *  an author wrote), or the media body's picture (auto-sized, or forced square) — put the layer over it, wire the
 *  panel's listeners on the row (once), and report where everything is. */
function setup(page: any, kind: Kind, marks: unknown[], active: boolean): Promise<Scene> {
  return page.evaluate(async ([kind, marks, active]: [Kind, unknown[], boolean]) => {
    const w = window as any;
    if (w.__layer) w.__layer.dispose();
    const row = document.getElementById("row")!;
    row.replaceChildren();
    const c = document.createElement("canvas"); c.width = 600; c.height = 400;   // a 600×400 picture, painted here
    const cx = c.getContext("2d")!; cx.fillStyle = "#336699"; cx.fillRect(0, 0, 600, 400); cx.fillStyle = "#ffcc00"; cx.fillRect(0, 0, 300, 200);
    const img = document.createElement("img");
    if (kind === "md" || kind === "md-sized") {
      const md = document.createElement("div"); md.className = "fileview-md";
      const p = document.createElement("p"); md.appendChild(p); p.appendChild(img); row.appendChild(md);
      if (kind === "md-sized") { img.setAttribute("width", "1200"); img.setAttribute("height", "800"); }   // the README figure: DOMPurify keeps both
    } else {
      const box = document.createElement("div"); box.className = "fileview-imgbox"; box.style.width = "400px"; box.style.height = "400px";
      img.className = "fileview-img"; box.appendChild(img); row.appendChild(box);
      if (kind === "media-square") { img.style.width = "300px"; img.style.height = "300px"; }
    }
    img.src = c.toDataURL("image/png");
    await img.decode();
    const calls: string[] = []; w.__calls = calls;
    if (!w.__wired) {   // the panel's wiring on the body row, in its order: the delegate first, the picture listener after it
      w.__romp.delegate(row, { fcopen: (el: HTMLElement) => { w.__calls.push("fcopen:" + el.dataset.id + ":" + el.tagName); } });
      row.addEventListener("click", (ev) => { const t = ev.target as HTMLElement; if (t.tagName === "IMG") w.__calls.push("imgclick"); });
      w.__wired = true;
    }
    const layer = new w.__romp.RegionLayer(img, {
      onDraw: (_i: unknown, r: unknown) => { w.__calls.push("onDraw:" + JSON.stringify(r)); },
      onClick: () => { w.__calls.push("onClick"); },
      onPress: () => { w.__calls.push("press"); },
    });
    w.__layer = layer; w.__img = img;
    layer.setActive(active);
    layer.paint(marks, null, false);
    const r = (el: Element) => { const b = el.getBoundingClientRect(); return { left: b.left, top: b.top, width: b.width, height: b.height }; };
    const rect = layer.overlay.querySelector(".fc-region");
    return { img: r(img), overlay: r(layer.overlay), rect: rect ? r(rect) : null, style: layer.overlay.getAttribute("style"), fit: getComputedStyle(img).objectFit, natural: [img.naturalWidth, img.naturalHeight] };
  }, [kind, marks, active]);
}
const calls = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__calls.splice(0));
const at = (b: Box, fx: number, fy: number): [number, number] => [b.left + b.width * fx, b.top + b.height * fy];
async function drag(page: any, from: [number, number], to: [number, number]): Promise<void> {
  await page.mouse.move(from[0], from[1]); await page.mouse.down(); await page.mouse.move(to[0], to[1], { steps: 4 }); await page.mouse.up();
}
const drawn = (c: string[]): { x: number; y: number; w: number; h: number } => {
  const s = c.find((x) => x.startsWith("onDraw:"));
  assert.ok(s, "a region was drawn: " + JSON.stringify(c));
  return JSON.parse(s!.slice("onDraw:".length));
};
const near = (a: number, b: number, msg: string) => assert.ok(Math.abs(a - b) < 0.011, msg + ": " + a + " vs " + b);
const sameBox = (a: Box, b: Box, msg: string) => { for (const k of ["left", "top", "width", "height"] as const) assert.ok(Math.abs(a[k] - b[k]) < 0.5, msg + " (" + k + ": " + a[k] + " vs " + b[k] + ")"); };

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

test("in a browser, panel open: a real click on a rectangle opens its card; a click on a framed picture opens its card and offers Comment; a plain picture's click is the panel's; a drag draws", async (t) => {
  await inBrowser(t, async (page) => {
    const s = await setup(page, "md", [MARK], true);
    assert.deepEqual(s.natural, [600, 400]);
    sameBox(s.img, { left: 20, top: 20, width: 600, height: 400 }, "the figure at its own size in a 600px column");
    assert.equal(s.style, null, "the picture fills its element: the sheet's inset: 0 places the overlay");
    sameBox(s.overlay, s.img, "the overlay is the picture");
    assert.ok(s.rect, "the region is painted");
    // the rectangle: the press is captured by the overlay, so the browser's click goes there — the layer clicks the rectangle
    await page.mouse.click(...at(s.rect!, 0.5, 0.5));
    assert.deepEqual(await calls(page), ["press", "fcopen:c1:DIV"], "the card opens through the delegate root, once; no picture click, no Comment offer");
    // the framed picture (an embed-line comment's mark): the click it had before the overlay — the card, then the Comment offer
    await page.evaluate(() => { const i = (window as any).__img as HTMLElement; i.dataset.act = "fcopen"; i.dataset.id = "c9"; });
    await page.mouse.click(...at(s.img, 0.8, 0.8));
    assert.deepEqual(await calls(page), ["press", "fcopen:c9:IMG", "imgclick"]);
    // the frame off: the picture's click goes to the panel through onClick, and nothing else fires
    await page.evaluate(() => { const i = (window as any).__img as HTMLElement; delete i.dataset.act; delete i.dataset.id; });
    await page.mouse.click(...at(s.img, 0.8, 0.8));
    assert.deepEqual(await calls(page), ["press", "onClick"]);
    // a drag: the region in fractions of the picture, the click after it swallowed
    await drag(page, at(s.img, 0.6, 0.6), at(s.img, 0.9, 0.9));
    const c = await calls(page);
    assert.equal(c[0], "press"); assert.equal(c.length, 2, JSON.stringify(c));
    const r = drawn(c);
    near(r.x, 0.6, "x"); near(r.y, 0.6, "y"); near(r.w, 0.3, "w"); near(r.h, 0.3, "h");
    // a drag that begins on the rectangle draws too, and opens nothing
    await drag(page, at(s.rect!, 0.5, 0.5), at(s.img, 0.9, 0.9));
    const c2 = await calls(page);
    assert.deepEqual(c2.filter((x) => !x.startsWith("onDraw:")), ["press"], JSON.stringify(c2));
  });
});

test("in a browser, panel closed: the overlay takes no events, so the browser's own click reaches the rectangle and the picture", async (t) => {
  await inBrowser(t, async (page) => {
    const s = await setup(page, "md", [MARK], false);
    await page.mouse.click(...at(s.rect!, 0.5, 0.5));
    assert.deepEqual(await calls(page), ["fcopen:c1:DIV"], "no press hook: the delegate root resolved the rectangle's own click");
    await page.mouse.click(...at(s.img, 0.8, 0.8));
    assert.deepEqual(await calls(page), ["imgclick"], "the picture's own click, through the overlay (pointer-events: none)");
  });
});

test("in a browser, the overlay sits where the picture's pixels are: a markdown figure with width and height attributes under the sheet's own object-fit, the media body's letterbox under contain", async (t) => {
  await inBrowser(t, async (page) => {
    // the README figure: <img width=1200 height=800> for a 600×400 picture in a 600px column — the element is 600×800
    const md = await setup(page, "md-sized", [], true);
    sameBox(md.img, { left: 20, top: 20, width: 600, height: 800 }, "the width caps at the column, the height attribute holds");
    if (md.fit === "fill") {
      // .fileview-md img has no object-fit rule: the picture is STRETCHED over the element, so the overlay is the element
      assert.equal(md.style, null, "no letterbox offsets for a stretched picture");
      sameBox(md.overlay, md.img, "the overlay covers the whole element");
      await drag(page, [md.img.left + 150, md.img.top + 1], [md.img.left + 450, md.img.top + 200]);
      const r = drawn(await calls(page));
      near(r.y, 0, "the top of the element is the top of the picture"); near(r.h, 0.25, "a quarter of the element is a quarter of the picture");
    } else {
      // the sheet letterboxes rendered-markdown figures too: the overlay is the 600×400 picture drawn 200px down
      assert.equal(md.fit, "contain", "the only other fit a romp sheet gives a picture");
      assert.equal(md.style, "left: 0px; top: 200px; width: 600px; height: 400px;");
      sameBox(md.overlay, { left: md.img.left, top: md.img.top + 200, width: 600, height: 400 }, "the overlay is the drawn picture");
    }
    // the media body's picture forced square: object-fit contain letterboxes the 600×400 picture to 300×200, 50px down
    const sq = await setup(page, "media-square", [], true);
    assert.equal(sq.fit, "contain", ".fileview-img's rule");
    sameBox(sq.img, { ...sq.img, width: 300, height: 300 }, "the square element");
    assert.equal(sq.style, "left: 0px; top: 50px; width: 300px; height: 200px;", "pixel offsets: the overlay is the drawn picture, not the element");
    sameBox(sq.overlay, { left: sq.img.left, top: sq.img.top + 50, width: 300, height: 200 }, "where it stands");
    // the band above the picture is the element's, not the overlay's: a press there starts nothing
    await drag(page, [sq.img.left + 30, sq.img.top + 10], [sq.img.left + 150, sq.img.top + 150]);
    assert.deepEqual(await calls(page), [], "no press, no region: the band holds no picture to comment on");
    // a drag that begins on the picture and leaves into the band (the captured pointer) is clamped to the picture's edge
    await drag(page, [sq.img.left + 150, sq.img.top + 150], [sq.img.left + 30, sq.img.top + 10]);
    const r = drawn(await calls(page));
    near(r.x, 0.1, "x"); near(r.y, 0, "clamped to the picture's top edge"); near(r.w, 0.4, "w"); near(r.h, 0.5, "h");
    // the media body's picture as the viewer sizes it (max constraints, auto size): its own aspect, no offsets
    const media = await setup(page, "media", [], true);
    assert.equal(media.fit, "contain");
    assert.equal(media.style, null, "the element has the picture's aspect: the sheet's inset: 0 places the overlay");
    sameBox(media.overlay, media.img, "the overlay is the picture");
    near(media.img.width / media.img.height, 1.5, "the natural aspect held");
  });
});
