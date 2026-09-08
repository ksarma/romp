// The body's end padding over a standalone picture, in a REAL engine (plans/file-review.md, "The margin-layout
// follow-on (2026-09-07)", its third review round): the worktree's file-comments.ts bundled the way the webview is
// built, mounted over the viewer's image body — `.fileview > .fileview-main > .fileview-body > .fileview-imgbox >
// img.fileview-img`, as file-view.ts builds it — under feed.css's own rules. What only an engine can show: the sheet's
// `.fileview-imgbox { min-height: 100% }` resolves against the body's CONTENT box, so the footer's padding the pass
// writes shrank the box by the padding and moved the picture it centers up by half of it, while the body gained no
// scroll range — a layout shift at every open of the Comments panel, undone at the close. The pass now takes the padding
// back the same pass where it bought no range, and keeps it where it did (a picture nearly the box's height, whose own
// box outgrows the padded content box: the body scrolls then, and the padding lets it reach a card at the picture's
// foot). Runs in Chromium and Firefox; skips LOUDLY without a playwright browser (CI installs none), as the other
// browser legs do. The stand-in twin is file-comments-margin-image-pad.test.ts. Synthetic values only: a painted
// canvas for the picture, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\n(window as any).__romp = { fileCommentsAction };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-image-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the viewer's card, its body and its picture box, and the whole file-comments block. */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  assert.match(rule(".fileview-imgbox"), /min-height: 100%/, "the box's min-height is the rule the padding runs into");
  return [rule("*"), rule(".fileview"), rule(".fileview-body"), rule(".fileview-imgbox"), rule(".fileview-img"), rule(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; --shadow-modal: none; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-imgbox" id="box"></div></div></div></div><script src="/dist/margin-image.js"></script></body></html>`;

// ── the picture and its comment (synthetic) ─────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const PNG = ROOT + "/docs/figure.png";
const T0 = 1757145600000;
const H1 = "1111111111111111111111111111111111111111111111111111111111111111";
const REGION = { x: 0.1667, y: 0.2, w: 0.3333, h: 0.3 };
const RID = T0 + "-0";
const COMMENT = { id: RID, author: "you", ts: T0, body: "Crop the header.", replies: [], resolved: false, target: { kind: "image", region: REGION, hash: H1 } };
const status = (comments: Array<Record<string, unknown>>): Record<string, unknown> => ({
  verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Ffigure.png.json", trackedBy: null, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: null,
  store: { v: 3, path: "docs/figure.png", suggestions: [], comments }, hunks: [], log: [],
  unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
  fileHash: H1,
});

type Scene = { margin: boolean; pad: string; imgTop: number; boxHeight: number; scrollHeight: number; clientHeight: number; rectTop: number | null; cardTop: number | null; trackTop: number | null };

/** Paint a `w`×`h` picture into the viewer's box, mount the panel over the body with a media seam, and answer its probe. */
function mount(page: any, w: number, h: number, s: Record<string, unknown>): Promise<void> {
  return page.evaluate(async ([w, h, status, abs, sid]: [number, number, Record<string, unknown>, string, string]) => {
    const win = window as any;
    const body = document.getElementById("body")!, box = document.getElementById("box")!;
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const cx = c.getContext("2d")!; cx.fillStyle = "#336699"; cx.fillRect(0, 0, w, h); cx.fillStyle = "#ffcc00"; cx.fillRect(0, 0, w / 2, h / 2);
    const img = document.createElement("img"); img.className = "fileview-img";
    box.appendChild(img);
    img.src = c.toDataURL("image/png");
    await img.decode();
    const posted: any[] = []; win.__posted = posted;
    const rendered: Array<() => void> = []; win.__rendered = rendered;
    const ctx = {
      path: abs, sid, todoId: null,
      body: () => body, mode: () => "media", text: () => null, mtimeNs: () => "1757145600000000001", media: () => "image", mediaElement: () => img,
      renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
      onRendered: (cb: () => void) => { rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: () => { /* inert */ }, onClose: () => { /* inert */ },
      post: (m: any) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ },
      aside: (node: HTMLElement | null) => { const main = document.getElementById("main")!; main.querySelector(".fileview-aside")?.remove(); if (node) { node.classList.add("fileview-aside"); main.appendChild(node); } },
      setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ }, reload: () => { /* inert */ },
    };
    const unit = win.__romp.fileCommentsAction.mount(ctx) as HTMLElement;
    document.body.appendChild(unit);
    win.__unit = unit; win.__status = status;
    const settle = () => new Promise<void>((r) => setTimeout(r, 0));
    win.__reply = async () => { const last = posted[posted.length - 1]; window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last.reqId, ...win.__status } })); await settle(); await settle(); };
    await win.__reply();                                           // the probe's status
  }, [w, h, s, PNG, SID]);
}
/** The Comments toggle: open (the panel re-asks, the reply is answered) or close. Then the paint and the pass. */
const toggle = (page: any, opening: boolean): Promise<void> => page.evaluate(async (opening: boolean) => {
  const win = window as any;
  (win.__unit.querySelector("button") as HTMLButtonElement).click();
  if (opening) { await win.__reply(); for (const cb of win.__rendered) cb(); }
  await new Promise<void>((r) => setTimeout(r, 0));
  await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
}, opening);
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const scene = (page: any): Promise<Scene> => page.evaluate((rid: string) => {
  const body = document.getElementById("body")!, box = document.getElementById("box")!;
  const img = box.querySelector("img.fileview-img")!;
  const b = body.getBoundingClientRect();
  const aside = document.querySelector(".fileview-aside");
  const rect = body.querySelector('.fc-region[data-id="' + rid + '"]');
  const card = aside ? aside.querySelector('.fc-card[data-id="' + rid + '"]') : null;
  const track = aside ? aside.querySelector(".fc-sec-cards") : null;
  return {
    margin: !!aside && aside.classList.contains("fc-margin"), pad: body.style.paddingBottom,
    imgTop: img.getBoundingClientRect().top - b.top, boxHeight: box.getBoundingClientRect().height,
    scrollHeight: body.scrollHeight, clientHeight: body.clientHeight,
    rectTop: rect ? rect.getBoundingClientRect().top - b.top : null, cardTop: card ? card.getBoundingClientRect().top - b.top : null,
    trackTop: track ? track.getBoundingClientRect().top - b.top : null,
  };
}, RID);
const near = (a: number, b: number, msg: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: string, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const page = await browser.newPage({ viewport: { width: 1100, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/margin-image.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: a picture shorter than the body's box — opening the Comments panel leaves the picture where the box centered it (the footer's padding, which bought no scroll range, is taken back), with its card level with the rectangle; closing changes nothing`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page, 300, 200, status([COMMENT]));
      const before = await scene(page);
      assert.equal(before.margin, false, "the panel is closed");
      assert.equal(before.scrollHeight, before.clientHeight, "the body does not scroll: the picture is shorter than the box");
      near(before.boxHeight, before.clientHeight, "the box fills the body", 0.5);
      near(before.imgTop, (before.clientHeight - 200) / 2, "the picture is centered in the body's box", 0.5);
      await toggle(page, true);
      let s = await scene(page);
      assert.equal(s.margin, true, "the margin layout is on over the media body");
      assert.equal(s.pad, "", "the padding bought no range and was taken back");
      assert.equal(s.scrollHeight, s.clientHeight, "still no range");
      near(s.boxHeight, before.boxHeight, "the picture's box is whole", 0.5);
      near(s.imgTop, before.imgTop, "the picture did not move", 0.5);
      assert.ok(s.rectTop !== null && s.cardTop !== null, "the rectangle is painted and its card placed");
      near(s.cardTop!, s.rectTop!, "the card is level with the rectangle");
      await frames(page, 4);                                       // more passes (observers, a frame): it converges, it does not flap
      s = await scene(page);
      assert.equal(s.pad, ""); near(s.imgTop, before.imgTop, "still where it was", 0.5);
      await toggle(page, false);
      s = await scene(page);
      assert.equal(s.margin, false); assert.equal(s.pad, "");
      near(s.imgTop, before.imgTop, "the close moved nothing either", 0.5);
    });
  });

  test(`in ${name}: a picture nearly the body's height — the footer's padding lengthens the body (its own box outgrows the padded content box), so it stays and the body scrolls; the close gives the picture its centered place back`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page, 400, 440, status([COMMENT]));
      const before = await scene(page);
      assert.equal(before.scrollHeight, before.clientHeight, "the body does not scroll before the panel opens");
      near(before.boxHeight, before.clientHeight, "the box fills the body", 0.5);
      await toggle(page, true);
      let s = await scene(page);
      assert.equal(s.margin, true);
      const pad = parseFloat(s.pad);
      assert.ok(pad > 0, "the footer's padding is kept: " + JSON.stringify(s.pad));
      assert.ok(s.scrollHeight > s.clientHeight, "the body scrolls now: " + s.scrollHeight + " vs " + s.clientHeight);
      near(s.scrollHeight - s.clientHeight, s.boxHeight + pad - s.clientHeight, "by what the padding added past the box", 1);
      assert.ok(s.rectTop !== null && s.cardTop !== null, "the rectangle is painted and its card placed");
      near(s.cardTop!, Math.max(s.rectTop!, s.trackTop! + 8), "the card is level with the rectangle (or at the track's inset, when the mark is under the header)", 1);
      await frames(page, 4);
      const again = await scene(page);
      assert.equal(again.pad, s.pad, "a later pass keeps the padding: no flap");
      await toggle(page, false);
      s = await scene(page);
      assert.equal(s.pad, "", "the padding goes with the layout");
      near(s.imgTop, before.imgTop, "the picture is centered in the body's box again", 0.5);
      near(s.boxHeight, before.boxHeight, "its box fills the body again", 0.5);
    });
  });
}
