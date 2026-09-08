// A MODIFIED click on a message's own `#` link, over the REAL render.ts bundle in headless Chromium at an http: origin
// (the web dashboard). The chat's link delegate resolves a footnote's back link or a `[section](#install)` itself
// (render.ts; md-sanitize.ts userContentTarget), because the sanitizer prefixes every author id and name user-content-
// and the browser's default lookup reads the bare fragment. It stands aside for the click the browser answers with a
// tab or window of its own, and that is a PLATFORM question: Shift everywhere, Cmd on macOS, Ctrl elsewhere
// (md-links.ts browserTabClick). The first cut stood aside for any of Ctrl, Meta and Shift, so on Linux and Windows a
// Super-click, a plain click to the browser, ran the default: the hash was written, the bare id was not found, and
// the transcript stayed put where the base had scrolled (the round-2 review of plans/markdown-viewer.md Slice 1).
// This leg clicks the back link with each key: the platform's tab key and Shift give the browser's tab and move
// nothing; the other key scrolls the footnote mark to the top, hash untouched, no tab. On a Mac the other key is
// Ctrl, whose press is the context menu and dispatches no click, so that row runs only off macOS (the defect's home).
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { chatBody, ATTACH_TITLE_WEB } from "../../vscode-extension/src/page-skeleton";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
function bundle(entry: string): string {
  const r = requireCjs("esbuild").buildSync({ ...BUILD, entryPoints: [path.join(UI, entry)] });
  return r.outputFiles[0].text;
}
// md() as render.ts runs it, minus the PR-ref linkifier: marked with the chat's options and extensions, then sanitizeMd
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { chatMdExtensions } from "./chat-md";',
    "marked.setOptions({ gfm: true, breaks: false });",
    "marked.use(...chatMdExtensions);",
    "(window as any).__mdProbe = (s: string) => sanitizeMd(marked.parse(s) as string).innerHTML;",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, sourcefile: "md-probe.ts", loader: "ts" } });
  return r.outputFiles[0].text;
}
// the chat page as the web dashboard serves it: the shared skeleton, the chat's sheet, a fake acquireVsCodeApi (the
// kernel's shim's role), window.open recorded instead of opened (a tab the BROWSER opens is a real popup, seen on the
// context), then the chat bundle and the probe
const CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/render.js></script><script src=/dist/probe.js></script></body></html>`;

// a reply with a footnote: the mark near the top, the note and its back link at the end of a transcript that scrolls
const FILLER = Array.from({ length: 80 }, (_, i) => "Filler paragraph " + (i + 1) + " so the transcript scrolls.").join("\n\n");
const FOOTNOTES = [
  'Claim.<sup id="fn1"><a href="#fnref1" class="fx-fwd">1</a></sup>',
  FILLER,
  '<p id="fnref1">1. a note <a href="#fn1" class="fx-back">back</a>.</p>',
].join("\n\n");

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Popups = { urls: string[]; close(): Promise<void> };

async function inBrowser(t: any, body: (page: any, popups: Popups, errors: string[], navs: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [], navs: string[] = [];
  try {
    const renderJs = bundle("render.ts"), probeJs = probeBundle();
    const context = await browser.newContext({ viewport: { width: 900, height: 700 } });
    // every page in the context is served from memory, the tab the browser opens on a Ctrl- or Shift-click included
    await context.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: CHAT_HTML });
      if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: renderJs });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      return route.fulfill({ status: 404, body: "" });
    });
    const page = await context.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) navs.push(f.url()); });
    const opened: any[] = [];
    context.on("page", (p: any) => { if (p !== page) opened.push(p); });
    const popups: Popups = {
      urls: [],
      async close() {
        for (const p of opened.splice(0)) {
          // the tab's URL is about:blank until its navigation commits: awaited on the frame's own URL event, bounded at
          // 10 s (3 s was not enough under the full suite's load, where the row read about:blank), then whatever it reads
          await p.waitForURL((u: URL) => u.hostname === "romp.test", { timeout: 10000 }).catch(() => undefined);
          popups.urls.push(p.url());
          await p.close();
        }
      },
    };
    await page.goto("http://romp.test/chat");
    await body(page, popups, errors, navs);
  } finally {
    await browser.close();
  }
}

test("a modified click on a footnote's back link: the platform's tab key and Shift give the browser's tab; the other key (Super on Linux and Windows) scrolls the transcript like a plain click", { timeout: 90000 }, async (t) => {
  await inBrowser(t, async (page, popups, errors, navs) => {
    // the message through the chat's own pipeline (marked + sanitizeMd, as md() runs them), inserted as render.ts does
    const shape = await page.evaluate((src: string) => {
      const content = document.getElementById("content") as HTMLElement;
      const turn = document.createElement("div"); turn.className = "turn turn-assistant fx-turn";
      const body = document.createElement("div"); body.className = "assistant md fx-body";
      body.innerHTML = (window as any).__mdProbe(src);
      turn.appendChild(body); content.appendChild(turn);
      const cs = getComputedStyle(content);
      return {
        ids: Array.from(content.querySelectorAll(".fx-turn [id]")).map((e) => e.getAttribute("id")),
        hrefs: Array.from(content.querySelectorAll(".fx-body a[href]")).map((a) => a.getAttribute("href")),
        scrollable: content.scrollHeight > content.clientHeight, overflowY: cs.overflowY,
        mac: /Mac|iP(?:hone|ad|od)/.test(navigator.platform || ""),
      };
    }, FOOTNOTES);
    assert.deepEqual(shape.ids, ["user-content-fn1", "user-content-fnref1"], "precondition: the author's ids reached the DOM prefixed (SANITIZE_NAMED_PROPS)");
    assert.deepEqual(shape.hrefs, ["#fnref1", "#fn1"], "precondition: the hrefs are as written, unprefixed");
    assert.ok(shape.scrollable && /auto|scroll/.test(shape.overflowY), "precondition: the transcript scrolls (" + shape.overflowY + ")");
    const mac: boolean = shape.mac;

    const state = () => page.evaluate(() => {
      const content = document.getElementById("content") as HTMLElement;
      const mark = document.querySelector("#user-content-fn1");
      return { scrollTop: content.scrollTop, hash: location.hash, opens: (window as any).__opens.length,
        fn1: mark ? Math.round(mark.getBoundingClientRect().top - content.getBoundingClientRect().top) : null };
    });
    // one real click at the back link's centre with the key held, from the bottom of the transcript. A tab the browser opens is
    // awaited as the context's `page` event, armed before the click (under the full suite's load it arrived after a 400 ms
    // sleep had run out, and the row read no tab); a row that expects none keeps a bounded wait, the only shape a negative
    // check can take.
    const clickWith = async (mod: "Control" | "Meta" | "Shift", expectTab: boolean): Promise<{ before: any; after: any; popups: string[] }> => {
      await page.evaluate(() => { history.replaceState(null, "", "/chat"); const c = document.getElementById("content") as HTMLElement; c.scrollTop = c.scrollHeight; });
      const before = await state();
      assert.ok(before.scrollTop > 0 && before.fn1! < 0 && before.hash === "", mod + ": the footnote mark is scrolled away above: " + JSON.stringify(before));
      const box = await page.locator(".fx-back").boundingBox();
      assert.ok(box, mod + ": the back link has a box");
      const x = box.x + box.width / 2, y = box.y + box.height / 2;
      const hit = await page.evaluate(([px, py]: [number, number]) => document.elementFromPoint(px, py)?.tagName ?? null, [x, y] as [number, number]);
      assert.equal(hit, "A", mod + ": precondition, the click lands on the link (elementFromPoint)");
      // the locator's click holds the key through the press (page.mouse.click takes no modifiers and would click plain)
      const tabP = page.context().waitForEvent("page", { timeout: expectTab ? 10000 : 400 }).then(() => true, () => false);
      await page.locator(".fx-back").click({ modifiers: [mod] });
      const sawTab: boolean = await tabP;                        // the event, or the bounded wait run out (a scroll has landed by then)
      if (expectTab) assert.ok(sawTab, mod + ": the browser opened a tab within 10 s of the click");
      const after = await state();
      popups.urls.length = 0;
      await popups.close();                                       // drains every tab the context saw, the awaited one included
      return { before, after, popups: popups.urls.slice() };
    };

    // 1. the browser's own gestures: Shift (a window everywhere) and the platform's tab key (Cmd on a Mac, Ctrl elsewhere).
    //    The delegate stands aside: a tab opens at the page's URL with the fragment, and the transcript does not move.
    for (const mod of ["Shift", mac ? "Meta" : "Control"] as const) {
      const r = await clickWith(mod, true);
      assert.equal(r.after.scrollTop, r.before.scrollTop, mod + ": the transcript did not move (the browser's gesture): " + JSON.stringify(r));
      assert.equal(r.after.hash, "", mod + ": the page's own hash is untouched");
      assert.equal(r.after.opens, 0, mod + ": window.open was not called (the tab is the browser's, not the delegate's)");
      assert.deepEqual(r.popups, ["http://romp.test/chat#fn1"], mod + ": the browser opened its tab at the page's URL with the fragment");
    }

    // 2. the other key. On Linux and Windows that is Super (Meta), a plain click to the browser: the delegate resolves it
    //    under the prefix and scrolls the mark to the top, hash untouched, no tab. Before the fix the delegate stood aside
    //    and the browser's default wrote #fn1 and found nothing: scrollTop unchanged, hash "#fn1", no tab.
    if (mac) {
      t.diagnostic("macOS: the other key is Ctrl, whose press is the context menu and dispatches no click; that row is skipped here");
    } else {
      const r = await clickWith("Meta", false);
      assert.ok(r.after.scrollTop < r.before.scrollTop && r.after.fn1! >= -1 && r.after.fn1! < 40,
        "Meta (Super) off macOS: the transcript scrolled the footnote mark to its top like a plain click: " + JSON.stringify(r));
      assert.equal(r.after.hash, "", "Meta off macOS: the default was cancelled, no #fn1 on the page's location");
      assert.deepEqual(r.popups, [], "Meta off macOS: no tab (the browser opens none for Super, and the delegate opened none)");
      assert.equal(r.after.opens, 0, "Meta off macOS: window.open was not called");
    }

    // 3. a plain click still scrolls (the control for the rows above)
    await page.evaluate(() => { const c = document.getElementById("content") as HTMLElement; c.scrollTop = c.scrollHeight; });
    await page.locator(".fx-back").click();
    await page.waitForTimeout(200);
    const plain = await state();
    assert.ok(plain.fn1! >= -1 && plain.fn1! < 40 && plain.hash === "", "a plain click scrolls the mark to the top, hash untouched: " + JSON.stringify(plain));
    await popups.close();
    assert.deepEqual(popups.urls, [], "a plain click opened no tab");

    assert.deepEqual(navs.filter((u) => !u.startsWith("http://romp.test/")), [], "the main frame never navigated off the dashboard");
    assert.deepEqual(errors, [], "no page errors");
  });
});
