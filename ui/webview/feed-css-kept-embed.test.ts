// The kept-embed rule in feed.css: the feed page's twin of styles-kept-embed.test.ts (the 2026-09-06 review of Slice 5,
// round 3). The feed page loads feed.css ALONE (the kernel's feed page and the VS Code feed webview each link one sheet,
// never styles.css), and it hosts the same viewer, panel and editor chunk as the chat page (feed.ts mounts initFileView), so
// every tc-diff rule the editor's marks wear has to be declared in both sheets. Round 2 added the kept-embed rule to
// styles.css only: on the feed page the span track-decorations.ts emits over an `![[embed]]` token the current text still
// holds (departure 4) had no rule, so the struck block wrapper's line-through propagated into it and the token read as
// "the picture is being deleted" — the very misread the rule exists to prevent — with no " still in the file" tag. The panel
// block's byte-equal pin (file-comments.test.ts) caught the drift, but fileview-parity.test.ts's head list did not name the
// two kept-embed heads and styles-kept-embed.test.ts reads styles.css alone, so nothing named the FEED sheet's copy. This
// file does: the static leg holds the rule and its tag in feed.css byte-equal to styles.css's, with the inline-block
// mechanism in its text; the browser legs mount the real chunk under feed.css alone over the kept-embed fixture and read
// the pixels — the removed runs struck, the kept token not, and the same span forced back to `display: inline` struck
// again, which is what proves the probe sees a strike where there is one. The pixel probe matters here: the span's computed
// textDecorationLine reads `none` whether or not the propagated strike paints through it. Skips LOUDLY without playwright
// or the browser (CI installs none), as the other browser legs do.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import * as zlib from "node:zlib";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");
const CHAT = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

function ruleOf(css: string, head: string): string {
  const at = css.indexOf(head);
  assert.ok(at >= 0, head + " present");
  return css.slice(at, css.indexOf("}", at) + 1);
}

// ── the static leg: the rule is in feed.css, once, byte-equal to the chat sheet's, with the mechanism in its text ─────

test("feed.css carries the kept-embed rule and its tag, byte-equal to styles.css — the feed page loads feed.css alone", () => {
  for (const head of [".tc-diff-del-kept-embed {", ".tc-diff-del-kept-embed::after {"]) {
    assert.equal(FEED.split(head).length - 1, 1, "one " + head + " rule in feed.css");
    assert.equal(ruleOf(FEED, head), ruleOf(CHAT, head), head + " mirrors styles.css exactly");
  }
  const kept = ruleOf(FEED, ".tc-diff-del-kept-embed {");
  assert.match(kept, /display:\s*inline-block/, "an inline-block is what a propagated line-through does not enter");
  assert.match(kept, /text-decoration:\s*none/);
  assert.match(kept, /border:\s*1px dashed/, "the dashed ring: the read view's cue for a passage that moved (fc-hl-context)");
  const tag = ruleOf(FEED, ".tc-diff-del-kept-embed::after {");
  assert.match(tag, /content:\s*" still in the file"/, "the tag says why the token is not struck");
  assert.doesNotMatch(tag, /font-size/, "no new size: the tag wears the row's (ui/CLAUDE.md, font sizes)");
  assert.match(ruleOf(FEED, ".tc-diff-del {"), /text-decoration:\s*line-through/, "the wrapper still strikes the rows");
  assert.match(FEED, /tc-diff-del-seg over each\s+removed run/, "feed.css's comment names the seg spans and says why they carry no rule");
  // the rule sits inside the panel block both sheets hold byte-equal (file-comments.test.ts), so a later edit to one
  // sheet's copy trips that pin as well as this one
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  const at = FEED.indexOf(".tc-diff-del-kept-embed {");
  assert.ok(a >= 0 && a < at && at < b, "the kept-embed rule is inside feed.css's file comments panel block");
});

// ── the browser legs: the real chunk under feed.css alone, read from the pixels ───────────────────

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

/** The editor chunk bundled with the shipped webview options (esbuild.js exports them without building). */
function chunkJs(): string {
  const { webview } = requireCjs(path.join(EXT, "esbuild.js")) as { webview: Record<string, unknown> };
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({ ...webview, entryPoints: [path.join(UI, "editor-chunk.ts")], write: false, sourcemap: false, logLevel: "silent" });
  const js = r.outputFiles.find((f: { path: string }) => f.path.endsWith(".js"));
  assert.ok(js, "the chunk bundle");
  return js.text;
}

// The kept-embed fixture (track-decorations-kept-embed.test.ts): six substitutions in one paragraph, dense enough for the
// paragraph form, around an embed token the current text still holds at 9..24. Synthetic: the notes-api world's `web` session.
const KEPT = "![[figure.png]]";
const DOC = `AA BB CC ${KEPT} DD EE FF gg`;
const sub = (id: string, from: number, newText: string, oldText: string) => ({ id, author: "web", ts: 1, kind: "sub", from, newText, oldText });
const RECORDS = [sub("p1", 0, "AA", "aa"), sub("p2", 3, "BB", "bb"), sub("p3", 6, "CC", "cc"),
  sub("p4", 25, "DD", "dd"), sub("p5", 28, "EE", "ee"), sub("p6", 31, "FF", "ff")];

// the page is the FEED page's dress for the editor: feed.css alone, as the kernel's feed page and the VS Code feed webview
// serve it (their font urls 404 here, harmlessly)
const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/feed.css>
<style>body{margin:0}#host{margin:24px 8px 8px;height:320px}</style></head>
<body><div id=host></div><script src=/dist/editor-chunk.js></script>
<script>
window.__mount = function (text, records) {
  var host = document.getElementById('host'); host.replaceChildren();
  window.__h = window.__rompEditor.mount(host, { text: text, ext: 'md', onChange: function () {}, onSave: function () {},
    track: { suggestions: records, onLedger: function () {} } });
};
window.__chain = function () {
  var kept = document.querySelector('.tc-diff-del-kept-embed');
  var seg = document.querySelector('.tc-diff-del-seg');
  var row = kept && kept.parentElement;
  var wrap = row && row.parentElement;
  return {
    text: kept ? kept.textContent : null,
    rowIsLine: !!row && row.classList.contains('tc-diff-del-line'),
    wrapIsBlock: !!wrap && wrap.classList.contains('tc-diff-del') && wrap.classList.contains('tc-diff-del-block'),
    wrapStrike: wrap ? getComputedStyle(wrap).textDecorationLine : null,
    keptDisplay: kept ? getComputedStyle(kept).display : null,
    keptStrike: kept ? getComputedStyle(kept).textDecorationLine : null,
    keptTag: kept ? getComputedStyle(kept, '::after').content : null,
    segDisplay: seg ? getComputedStyle(seg).display : null,
  };
};
</script></body></html>`;

/** A PNG (8-bit RGB or RGBA, non-interlaced: what a playwright screenshot is) decoded to raw rows. */
function decodePng(buf: Buffer): { width: number; height: number; bpp: number; data: Buffer } {
  assert.equal(buf.readUInt32BE(0), 0x89504e47, "a PNG");
  let pos = 8, width = 0, height = 0, bitDepth = 0, colorType = 0, interlace = 0;
  const idat: Buffer[] = [];
  while (pos + 8 <= buf.length) {
    const len = buf.readUInt32BE(pos);
    const type = buf.toString("ascii", pos + 4, pos + 8);
    const data = buf.subarray(pos + 8, pos + 8 + len);
    if (type === "IHDR") { width = data.readUInt32BE(0); height = data.readUInt32BE(4); bitDepth = data[8]; colorType = data[9]; interlace = data[12]; }
    else if (type === "IDAT") idat.push(data);
    else if (type === "IEND") break;
    pos += 12 + len;
  }
  assert.equal(bitDepth, 8); assert.equal(interlace, 0);
  const bpp = colorType === 6 ? 4 : colorType === 2 ? 3 : 0;
  assert.ok(bpp, "RGB or RGBA");
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const stride = width * bpp;
  const out = Buffer.alloc(stride * height);
  let p = 0;
  for (let y = 0; y < height; y++) {
    const f = raw[p++]; const row = y * stride; const prev = row - stride;
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? out[row + x - bpp] : 0;
      const b = y > 0 ? out[prev + x] : 0;
      const c = x >= bpp && y > 0 ? out[prev + x - bpp] : 0;
      const v = raw[p++];
      let r: number;
      switch (f) {
        case 0: r = v; break;
        case 1: r = v + a; break;
        case 2: r = v + b; break;
        case 3: r = v + ((a + b) >> 1); break;
        case 4: { const pa = Math.abs(b - c), pb = Math.abs(a - c), pc = Math.abs(a + b - 2 * c); r = v + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c); break; }
        default: throw new Error("png filter " + f);
      }
      out[row + x] = r & 255;
    }
  }
  return { width, height, bpp, data: out };
}

/** The largest fraction of one pixel row, in the box's middle band and away from its side edges, that is ink (not the
 *  background, the clip's most common colour). A strike is a row at 1.0; glyph rows never fill a row (the gaps between
 *  glyphs), and a dashed border sits at the box's edge rows, outside the band. */
function maxRowInk(png: { width: number; height: number; bpp: number; data: Buffer }): number {
  const { width, height, bpp, data } = png;
  const px = (x: number, y: number) => { const i = (y * width + x) * bpp; return [data[i], data[i + 1], data[i + 2]]; };
  const counts = new Map<number, number>();
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) { const [r, g, b] = px(x, y); const k = (r << 16) | (g << 8) | b; counts.set(k, (counts.get(k) || 0) + 1); }
  const bgKey = [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0];
  const bg = [(bgKey >> 16) & 255, (bgKey >> 8) & 255, bgKey & 255];
  const x0 = 3, x1 = width - 3, y0 = Math.floor(height * 0.2), y1 = Math.ceil(height * 0.8);
  assert.ok(x1 - x0 >= 20 && y1 > y0, `a box worth reading: ${width}x${height}`);
  let max = 0;
  for (let y = y0; y < y1; y++) {
    let ink = 0;
    for (let x = x0; x < x1; x++) { const [r, g, b] = px(x, y); if (Math.abs(r - bg[0]) + Math.abs(g - bg[1]) + Math.abs(b - bg[2]) > 48) ink++; }
    max = Math.max(max, ink / (x1 - x0));
  }
  return max;
}

async function probe(t: any, engine: "chromium" | "firefox") {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[engine].launch(); }
  catch (e) { t.skip(`no playwright ${engine} on this box — this leg needs it (CI installs none): ` + String((e as Error).message).split("\n")[0]); return; }
  try {
    const context = await browser.newContext({ viewport: { width: 900, height: 500 }, deviceScaleFactor: 1 });
    const errors: string[] = [];
    const page = await context.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const js = chunkJs();
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
      if (u.pathname === "/dist/editor-chunk.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/feed.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: FEED });
      // styles.css is NOT served: the leg is about what the feed sheet alone buys the page
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.evaluate(([d, r]: [string, unknown[]]) => (window as any).__mount(d, r), [DOC, RECORDS] as [string, unknown[]]);
    await page.waitForSelector(".tc-diff-del-kept-embed");
    const chain = await page.evaluate(() => (window as any).__chain());
    assert.equal(chain.text, KEPT, "the kept span holds the token");
    assert.ok(chain.rowIsLine && chain.wrapIsBlock, "span > .tc-diff-del-line > .tc-diff-del.tc-diff-del-block: the chain the rule is written for");
    assert.equal(chain.wrapStrike, "line-through", "the wrapper strikes its rows");
    assert.equal(chain.keptDisplay, "inline-block", "under feed.css the kept span is the inline-block that stops the propagation");
    assert.equal(chain.keptStrike, "none");
    assert.equal(chain.keptTag, '" still in the file"', "the tag is generated on the feed page too");
    assert.equal(chain.segDisplay, "inline", "a seg span stays inline, so the propagated strike reaches it");
    const shot = async (sel: string) => {
      const b = await page.locator(sel).first().boundingBox();
      assert.ok(b, sel + " has a box");
      const clip = { x: Math.floor(b.x), y: Math.floor(b.y), width: Math.ceil(b.width), height: Math.ceil(b.height) };
      return maxRowInk(decodePng(await page.screenshot({ clip })));
    };
    const seg = await shot(".tc-diff-del-seg");
    const kept = await shot(".tc-diff-del-kept-embed");
    assert.ok(seg >= 0.95, `a removed run is struck: one row of ink across its width (max row ink ${seg.toFixed(2)})`);
    assert.ok(kept <= 0.85, `the kept token is not struck: no row of ink across its width (max row ink ${kept.toFixed(2)})`);
    // the control: the same span forced back to display: inline, every other declaration of the rule intact, is struck again —
    // which is exactly how the feed page rendered it before feed.css carried the rule, and what proves the probe sees a strike
    await page.addStyleTag({ content: ".tc-diff-del-kept-embed { display: inline !important; }" });
    const inline = await shot(".tc-diff-del-kept-embed");
    assert.ok(inline >= 0.95, `as an inline, the wrapper's line-through paints through the token (max row ink ${inline.toFixed(2)})`);
    assert.deepEqual(errors, []);
    await context.close();
  } finally { await browser.close(); }
}

test("in Chromium: under feed.css alone the kept embed reads un-struck with its tag while the removed runs around it are struck", async (t) => {
  await probe(t, "chromium");
});

test("in Firefox: the same on the feed page's sheet — the propagation rule is the spec's, not one engine's", async (t) => {
  await probe(t, "firefox");
});
