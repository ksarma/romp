// The region layer's SHEET behaviour a real engine has to confirm (plans/file-review.md, Slice 3; the 2026-09-06
// review). Two defects the sheet pin tests could not see, since both read declared literals:
//
// 1. A rectangle was a scroll-dead zone on the phone. `.fc-overlay { touch-action: none }` is for the ARMED layer,
//    where a drag draws; on a coarse pointer the layer is always disarmed (`.fc-overlay-off`: pointer-events: none, the
//    rectangles opt back in), yet touch-action composes by INTERSECTION from the touched element up to the scroll
//    container, so a swipe that started on a rectangle found `none` on the overlay and never panned `.fileview-body`.
//    The disarmed layer now gives the pan back; a rectangle cannot do it on its own (a touch-action there is dead).
// 2. The author chip compounded with the rendered markdown's heading sizes: 0.72em of a layer sitting inside an h1
//    (1.3em) rendered at 0.94em — the same chip a third larger than on a paragraph figure, on the standalone image, or
//    in the aside (the README banner pattern, <h1><img></h1>; ui/CLAUDE.md, font sizes: nested em compounds). In the
//    light theme it also wore the prose face (mono) where every other chip wears the body's. The layer in rendered
//    markdown now wears the body's own size and face (--fs, --sans), so the chip lands where the aside's does.
//
// The source leg pins the rules as written, in BOTH sheets (the feed page loads only feed.css). The browser leg
// drives headless Chromium with a touch context over the real RegionLayer (file-comments-regions.ts, bundled here)
// and the real sheet: a CDP touch swipe from the rectangle scrolls the body, computed chip sizes agree across the
// heading figure, the paragraph figure, the standalone image and the aside — and each half is checked against a
// CONTROL sheet with the fix stripped, so the leg is known to see the defect it guards. It skips LOUDLY without
// playwright or the browser (CI installs none); the source leg runs everywhere.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const read = (f: string) => fs.readFileSync(path.join(UI, f), "utf8");
const SHEETS = [["styles.css", read("styles.css")], ["feed.css", read("feed.css")]] as const;
const LAYER = read("file-comments-regions.ts");

const BLOCK_HEAD = "/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)";
const BLOCK_END = "/* ── end file comments panel ── */";
const RESET_RULE = ".fileview-md .fc-overlay { font-size: var(--fs); font-family: var(--sans); }";

function panelBlock(css: string): string {
  const a = css.indexOf(BLOCK_HEAD), b = css.indexOf(BLOCK_END);
  assert.ok(a >= 0 && b > a, "the block and its end marker");
  return css.slice(a, b);
}
/** [selector, body] for every plain rule of a css text, comments stripped, at-rules skipped whole */
function rulesOf(css: string): Array<[string, string]> {
  const text = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const out: Array<[string, string]> = [];
  let i = 0;
  while (i < text.length) {
    if (/\s/.test(text[i])) { i++; continue; }
    if (text[i] === "@") {
      let depth = 0, j = text.indexOf("{", i);
      for (; j < text.length; j++) { if (text[j] === "{") depth++; else if (text[j] === "}" && --depth === 0) break; }
      i = j + 1; continue;
    }
    const open = text.indexOf("{", i), close = text.indexOf("}", open);
    assert.ok(open > i && close > open, "a rule without braces at " + text.slice(i, i + 40));
    out.push([text.slice(i, open).trim().replace(/\s+/g, " "), text.slice(open + 1, close).trim()]);
    i = close + 1;
  }
  return out;
}
const declares = (body: string, decl: string) => body.split(";").map((d) => d.trim().replace(/\s+/g, " ")).includes(decl);

// ── the control sheets: the fix stripped, so the browser leg is known to see each defect ──
/** every `touch-action: auto` off every .fc-overlay-off rule (whichever rule of that selector carries it) */
const withoutPan = (css: string) => css.replace(/(\.fc-overlay-off\s*\{[^}]*?)touch-action:\s*auto;?\s*/g, "$1");
const withoutReset = (css: string) => css.replace(RESET_RULE, "");

// ── the source leg ────────────────────────────────────────────────────────────────────────────────
test("the layer's DOM: the chip sits in the rectangle, the rectangle in the overlay — so a size on the overlay reaches the chip", () => {
  assert.match(LAYER, /this\.overlay = mk\(doc, "div", "fc-overlay fc-overlay-off"\);/, "a layer starts disarmed");
  assert.match(LAYER, /this\.overlay\.classList\.toggle\("fc-overlay-off", !on\);/, "setActive arms and disarms through the one class");
  assert.match(LAYER, /const chip = mk\(doc, "span", "fc-region-chip"\);\n[^\n]*\n\s*r\.appendChild\(chip\);\n\s*o\.appendChild\(r\);/, "chip in rectangle, rectangle in overlay");
});

for (const [name, css] of SHEETS) {
  test(name + ": the armed layer refuses the pan (a drag draws), the disarmed layer gives it back, and no rectangle tries on its own", () => {
    const rules = rulesOf(panelBlock(css));
    const overlay = rules.find(([sel]) => sel === ".fc-overlay");
    assert.ok(overlay && declares(overlay[1], "touch-action: none"), "the armed overlay: touch-action: none, so a drag draws instead of panning");
    const off = rules.filter(([sel]) => sel === ".fc-overlay-off");
    assert.ok(off.some(([, body]) => declares(body, "touch-action: auto")),
      "a .fc-overlay-off rule declares touch-action: auto — the disarmed layer pans; a swipe that starts on a rectangle scrolls the viewer");
    assert.ok(off.some(([, body]) => declares(body, "pointer-events: none")), "and still takes no pointer events");
    for (const [sel, body] of rules) {
      if (!/\.fc-region/.test(sel)) continue;
      assert.doesNotMatch(body, /touch-action/, sel + ": a touch-action on a rectangle is dead — the effective value is the intersection up the chain, and the overlay's wins");
    }
    assert.notEqual(withoutPan(css), css, "the control strip finds the declaration");
  });

  test(name + ": a figure's layer in rendered markdown wears the body's own size and face, declared OUTSIDE the panel block", () => {
    const at = css.indexOf(RESET_RULE);
    assert.ok(at >= 0, "the reset rule, byte for byte: " + RESET_RULE);
    assert.ok(at < css.indexOf(BLOCK_HEAD), "outside the panel block: the block speaks em (styles-fc-computed-sizes.test.ts multiplies its every font-size), and this is the .fileview-md typography's own stop");
    const base = rulesOf(css).find(([sel]) => sel === "html, body");
    assert.ok(base && declares(base[1], "font-size: var(--fs)") && declares(base[1], "font-family: var(--sans)"),
      "--fs and --sans are the body's own size and face, so the reset lands the chip where the aside's is");
    const headings = rulesOf(css).filter(([sel]) => /^\.fileview-md h[123]$/.test(sel) || sel === ".fileview-md");
    assert.ok(headings.some(([, body]) => /font-size: 1\.3em/.test(body)), "the compounding source is still there (h1 at 1.3em); drop the reset only with it");
    assert.ok(headings.some(([, body]) => /font-family: var\(--font-prose\)/.test(body)), "the prose face the reset stops");
  });
}

// ── the browser leg ───────────────────────────────────────────────────────────────────────────────
let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** the real RegionLayer, bundled for the page */
function layerBundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'import { RegionLayer } from "./file-comments-regions"; (window as any).__RegionLayer = RegionLayer;', resolveDir: UI, loader: "ts", sourcefile: "layer-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020", logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
const svg = (w: number, h: number) => "data:image/svg+xml," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="100%" height="100%" fill="#4a5a6a"/></svg>`);
// the synthetic file: the notes-api README with the banner pattern (<h1><img></h1>) and a body figure; or a standalone image
function pageHtml(css: string, layerJs: string, body: "md" | "media"): string {
  const inner = body === "md"
    ? `<div class=fileview-md>
<h1 align=center><img id=banner src="${svg(300, 1400)}" width=300 height=1400 alt=""></h1>
<p>The notes API keeps one file per note; the banner above is the project's logo.</p>
<p><img id=plot src="${svg(300, 200)}" width=300 height=200 alt=""></p>
<p>A second paragraph, so there is prose below the figure as well.</p>
</div>`
    : `<div class=fileview-imgbox><img id=banner class=fileview-img src="${svg(300, 1400)}" width=300 height=1400 alt=""></div>`;
  return `<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width, initial-scale=1">
<style>${css}</style></head><body class=fileview-open>
<div id=romp-fileview><div class=fileview><div class=fileview-bar></div><div class=fileview-main>
<div class=fileview-body>${inner}</div>
<div class=fileview-aside><div class=fc-panel><div class=fc-sec-cards><div class=fc-cards><div class=fc-card><div class=fc-card-head>
<span class="fc-chip fc-chip-you">you</span><span class=fc-ref>banner.png</span></div></div></div></div></div></div>
</div></div></div>
<script>${layerJs}</script>
<script>
  window.__layers = [];
  for (const img of document.querySelectorAll("img")) {
    const L = new window.__RegionLayer(img, { onDraw() {}, onClick() {} });
    L.paint([{ id: "c1", region: { x: 0.05, y: 0.05, w: 0.9, h: 0.6 }, label: "you", state: "current" }], null, false);
    window.__layers.push(L);
  }
</script></body></html>`;
}

type Swipe = { hit: string; scrolled: number };
/** a finger: down on `pick` (its visible bottom, or its top strip — the picture's own pixels above the rectangle),
 *  eight moves 200px upward, up — then the body's scrollTop once it has held still */
async function swipeFrom(page: any, cdp: any, pick: string, where: "low" | "top" = "low"): Promise<Swipe> {
  const p = await page.evaluate(([sel, w]: [string, string]) => {
    const body = document.querySelector(".fileview-body") as HTMLElement;
    const el = document.querySelector(sel) as HTMLElement;
    body.scrollTop = 0;
    el.scrollIntoView({ block: "nearest" });               // the prose below the banner: brought into the body first
    const b = body.getBoundingClientRect(), r = el.getBoundingClientRect();
    // inside the element AND inside the body's visible box
    const top = Math.max(r.top, b.top), bottom = Math.min(r.bottom, b.bottom);
    const x = r.left + r.width / 2, y = w === "top" ? top + 12 : bottom - 24;
    const hit = document.elementFromPoint(x, y);
    return { x, y, hit: hit ? hit.className || hit.tagName : "", inside: y > top + 4 && y < bottom - 4, from: body.scrollTop };
  }, [pick, where]);
  assert.ok(p.inside, pick + " is visible in the body");
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: p.x, y: p.y }] });
  for (let i = 1; i <= 8; i++) await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: p.x, y: p.y - (200 * i) / 8 }] });
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  const scrolled = await page.evaluate((from: number) => new Promise<number>((res) => {
    const body = document.querySelector(".fileview-body") as HTMLElement;
    let last = body.scrollTop, still = 0;
    const tick = () => {
      if (body.scrollTop === last) { if (++still >= 20) { res(body.scrollTop - from); return; } }
      else { still = 0; last = body.scrollTop; }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }), p.from);
  return { hit: p.hit, scrolled };
}

type Sizes = { base: number; h1chip: number; pchip: number; aside: number; h1face: string; asideface: string; bodyface: string; proseface: string };
const sizes = (page: any): Promise<Sizes> => page.evaluate(() => {
  const q = (s: string) => document.querySelector(s) as HTMLElement;
  const px = (el: HTMLElement) => parseFloat(getComputedStyle(el).fontSize);
  const face = (el: HTMLElement) => getComputedStyle(el).fontFamily;
  const h1chip = q("h1 .fc-region-chip"), pchip = q("p .fc-region-chip"), aside = q(".fc-chip");
  return { base: px(document.body), h1chip: px(h1chip), pchip: px(pchip), aside: px(aside),
    h1face: face(h1chip), asideface: face(aside), bodyface: face(document.body), proseface: face(q(".fileview-md")) };
});
const near = (a: number, b: number) => Math.abs(a - b) < 0.02;

for (const [name, css] of SHEETS) {
  test(name + " in Chromium (touch): a swipe from a rectangle scrolls the viewer; the chip is one size on every figure and in the aside", async (t) => {
    if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
    let browser: any;
    try { browser = await pw.chromium.launch(); }
    catch (e) { t.skip("no playwright chromium on this box — the browser leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
    const errors: string[] = [];
    try {
      const layerJs = layerBundle();
      const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
      const open = async (sheet: string, body: "md" | "media") => {
        const page = await context.newPage();
        page.on("pageerror", (e: Error) => { errors.push(e.message); });
        await page.route("http://romp.test/**", (route: any) => {
          const u = new URL(route.request().url());
          if (u.pathname === "/view") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: pageHtml(sheet, layerJs, body) });
          return route.fulfill({ status: 404, body: "" });   // the sheet's @import and fonts: nothing to serve, nothing to wait on
        });
        await page.goto("http://romp.test/view");
        await page.waitForFunction(() => Array.from(document.images).every((i) => i.complete && i.naturalWidth > 0) && document.querySelectorAll(".fc-region").length === document.images.length);
        await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));   // the layers' place() after load
        return page;
      };

      // ── 1. the pan ──
      const page = await open(css, "md");
      const cdp = await context.newCDPSession(page);
      let s = await swipeFrom(page, cdp, "h1 .fc-region");
      assert.match(s.hit, /\bfc-region\b/, "the finger lands on the rectangle (pointer-events: auto through the disarmed overlay)");
      assert.ok(s.scrolled > 100, "a swipe from the rectangle scrolls the body (got " + s.scrolled + "px)");
      s = await swipeFrom(page, cdp, ".fileview-md > p");
      assert.ok(s.scrolled > 100, "a swipe from the prose scrolls the body (got " + s.scrolled + "px)");
      s = await swipeFrom(page, cdp, "#banner", "top");   // the picture's own pixels: the strip above the rectangle (which starts at 5%)
      assert.equal(s.hit, "IMG", "the finger lands on the picture through the disarmed overlay (pointer-events: none)");
      assert.ok(s.scrolled > 100, "a swipe from the picture scrolls the body (got " + s.scrolled + "px)");
      // the ARMED layer (a fine pointer with the panel open) keeps the page still under a finger: the drag draws
      await page.evaluate(() => { (window as any).__layers[0].setActive(true); });
      s = await swipeFrom(page, cdp, "h1 .fc-overlay");
      assert.match(s.hit, /\bfc-(overlay|region)\b/, "the armed overlay takes the touch");
      assert.equal(s.scrolled, 0, "and touch-action: none holds the page while the drag draws");
      await page.evaluate(() => { (window as any).__layers[0].setActive(false); });
      s = await swipeFrom(page, cdp, "h1 .fc-region");
      assert.ok(s.scrolled > 100, "disarmed again, the rectangle pans again (got " + s.scrolled + "px)");
      // the control: the sheet as it shipped — the same swipe from the rectangle moved nothing
      const ctl = await open(withoutPan(css), "md");
      const ctlCdp = await context.newCDPSession(ctl);
      s = await swipeFrom(ctl, ctlCdp, "h1 .fc-region");
      assert.match(s.hit, /\bfc-region\b/);
      assert.equal(s.scrolled, 0, "the control sheet reproduces the dead zone, so this leg sees the defect");
      s = await swipeFrom(ctl, ctlCdp, ".fileview-md > p");
      assert.ok(s.scrolled > 100, "while its prose scrolls (got " + s.scrolled + "px) — the dead zone was the rectangle's footprint");
      await ctl.close();

      // ── 2. the chip's size and face ──
      for (const light of [false, true]) {
        await page.evaluate((on: boolean) => { document.body.classList.toggle("theme-light", on); }, light);
        const z = await sizes(page);
        const theme = light ? " (light)" : " (dark)";
        assert.equal(z.base, 13, "the body's base: --fs falls back to 13px" + theme);
        assert.ok(near(z.aside, 0.72 * z.base), "the aside chip is 0.72em of the base" + theme + " (" + z.aside + "px)");
        assert.ok(near(z.h1chip, z.aside), "the chip on the h1 banner is the aside chip's size" + theme + " (" + z.h1chip + "px vs " + z.aside + "px)");
        assert.ok(near(z.pchip, z.aside), "the chip on the paragraph figure is the aside chip's size" + theme + " (" + z.pchip + "px)");
        assert.equal(z.h1face, z.bodyface, "the chip wears the body's face" + theme);
        assert.equal(z.asideface, z.bodyface, "as the aside chip does" + theme);
        if (light) assert.notEqual(z.proseface, z.bodyface, "the light theme's prose face differs from the body's — the divergence the reset stops");
      }
      const media = await open(css, "media");
      const m = await media.evaluate(() => {
        const px = (el: Element) => parseFloat(getComputedStyle(el).fontSize);
        return { chip: px(document.querySelector(".fc-region-chip")!), aside: px(document.querySelector(".fc-chip")!),
          face: getComputedStyle(document.querySelector(".fc-region-chip")!).fontFamily, bodyface: getComputedStyle(document.body).fontFamily };
      });
      assert.ok(near(m.chip, m.aside) && near(m.chip, 0.72 * 13), "the standalone image's chip is the same size (" + m.chip + "px)");
      assert.equal(m.face, m.bodyface, "and the same face");
      await media.close();
      // the control: without the reset the h1 chip compounds to 1.3x, and in light wears the prose face
      const ctl2 = await open(withoutReset(css), "md");
      assert.notEqual(withoutReset(css), css, "the control strip finds the rule");
      await ctl2.evaluate(() => { document.body.classList.add("theme-light"); });
      const c = await sizes(ctl2);
      assert.ok(near(c.h1chip, 1.3 * c.aside), "the control sheet reproduces the compounding (" + c.h1chip + "px vs " + c.aside + "px), so this leg sees the defect");
      assert.ok(near(c.pchip, c.aside), "and the paragraph figure's chip was never the problem");
      assert.equal(c.h1face, c.proseface, "the control chip wears the prose face in light");
      assert.notEqual(c.h1face, c.bodyface);
      await ctl2.close();
      await page.close();
      assert.deepEqual(errors, [], "no script error in any page");
    } finally { await browser.close(); }
  });
}
