// A MODIFIED click on a message's own `#` link, over the REAL render.ts bundle in headless Chromium at an http: origin
// (the web dashboard). The chat's link delegate resolves a footnote's back link or a `[section](#install)` itself
// (render.ts; md-sanitize.ts userContentTarget), because the sanitizer prefixes every author id and name user-content-
// and the browser's default lookup reads the bare fragment. It stands aside for the click the browser answers with a
// tab or window of its own, and that is a PLATFORM question: Shift everywhere, Cmd on macOS, Ctrl elsewhere
// (md-links.ts browserTabClick). The first cut stood aside for any of Ctrl, Meta and Shift, so on Linux and Windows a
// Super-click, a plain click to the browser, ran the default: the hash was written, the bare id was not found, and
// the transcript stayed put where the base had scrolled (the round-2 review of plans/markdown-viewer.md Slice 1).
// This leg clicks the back link with each key. The platform's tab key and Shift are left to the browser: the click's
// default action stays uncancelled, nothing scrolls, the hash and window.open are untouched. The other key scrolls the
// footnote mark to the top with the default cancelled, hash untouched. On a Mac the other key is Ctrl, whose press is
// the context menu and dispatches no click, so that row runs only off macOS (the defect's home). A plain click is the
// control.
// What is read is each click's own record (the recorder below: its defaultPrevented flag as dispatch ends, the keys it
// carried), with the transcript's scroll offset, the hash and the window.open log; never the tab the browser opens.
// Opening that tab is Chromium's disposition rule for an uncancelled click with the key held, and under the full
// suite's load it came late or not at all (the round-2 wait on the context's page event ran out at 10 s; a 60 s probe
// saw no tab while the same click's flag read false within the click: the review after the merge of main into Slice
// 1), so a wait on it measured the browser, not the delegate. The flag says what the browser WILL do the moment
// dispatch ends; the tab is its business, and one that does open is closed on arrival. Skips LOUDLY without a
// playwright browser (CI installs none), as the other browser legs do. Synthetic values only.
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
// context), then the chat bundle, a click recorder and the probe.
// The recorder reads each click's own defaultPrevented flag and modifier keys as dispatch ends: the browser's default
// action (its tab or window for the platform's gesture, a fragment navigation for a plain click) runs exactly when that
// flag is still false, so the flag says what the browser will do without waiting to see it done. Two listeners write
// it: one at the document's capture phase, registered after render.js so it runs right after the delegate on the same
// node, and one at the window's bubble phase, the last stop of a click the delegate let through; the later one to run
// has the final word (the same recorder as md-sanitize-chat-links-browser.test.ts).
const CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/render.js></script>
<script>(function(){window.__lastClick=null;function rec(e){window.__lastClick={prevented:e.defaultPrevented,tag:e.target&&e.target.tagName,shift:e.shiftKey,ctrl:e.ctrlKey,meta:e.metaKey};}
document.addEventListener("click",rec,true);window.addEventListener("click",rec);})();</script>
<script src=/dist/probe.js></script></body></html>`;

// a reply with a footnote: the mark near the top, the note and its back link at the end of a transcript that scrolls
const FILLER = Array.from({ length: 80 }, (_, i) => "Filler paragraph " + (i + 1) + " so the transcript scrolls.").join("\n\n");
const FOOTNOTES = [
  'Claim.<sup id="fn1"><a href="#fnref1" class="fx-fwd">1</a></sup>',
  FILLER,
  '<p id="fnref1">1. a note <a href="#fn1" class="fx-back">back</a>.</p>',
].join("\n\n");

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

type Click = { prevented: boolean; tag: string | null; shift: boolean; ctrl: boolean; meta: boolean } | null;
type Tabs = { count: number };

async function inBrowser(t: any, body: (page: any, tabs: Tabs, errors: string[], navs: string[]) => Promise<void>): Promise<void> {
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
    // a tab the browser opens of its own for a gesture is counted and closed as it arrives, whenever that is: nothing
    // below waits on it (see the header), and left open it would boot the chat bundle a second time under load
    const tabs: Tabs = { count: 0 };
    context.on("page", (p: any) => { if (p !== page) { tabs.count++; p.close().catch(() => undefined); } });
    await page.goto("http://romp.test/chat");
    await body(page, tabs, errors, navs);
  } finally {
    await browser.close();
  }
}

test("a modified click on a footnote's back link: the platform's tab key and Shift are left to the browser; the other key (Super on Linux and Windows) scrolls the transcript like a plain click", { timeout: 90000 }, async (t) => {
  await inBrowser(t, async (page, tabs, errors, navs) => {
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

    // the transcript's scroll offset, the page's hash, the window.open log, where the footnote mark stands, and the
    // last click's record (null until a click reaches the document)
    const state = () => page.evaluate(() => {
      const content = document.getElementById("content") as HTMLElement;
      const mark = document.querySelector("#user-content-fn1");
      return { scrollTop: content.scrollTop, hash: location.hash, opens: (window as any).__opens.length,
        fn1: mark ? Math.round(mark.getBoundingClientRect().top - content.getBoundingClientRect().top) : null,
        click: (window as any).__lastClick as Click };
    });
    // one real click at the back link's centre with the key held (or none), from the bottom of the transcript. The
    // locator's click resolves once the renderer has dispatched the click, so the record and the flag are final when
    // the state after is read: no wait, on a tab or a timer. Each row checks that its click reached the link with the
    // key it asked for (the locator holds the key through the press; page.mouse.click takes no modifiers).
    const clickWith = async (mod: "Control" | "Meta" | "Shift" | null): Promise<{ before: any; after: any }> => {
      const label = mod ?? "plain";
      await page.evaluate(() => { history.replaceState(null, "", "/chat"); (window as any).__lastClick = null; const c = document.getElementById("content") as HTMLElement; c.scrollTop = c.scrollHeight; });
      const before = await state();
      assert.ok(before.scrollTop > 0 && before.fn1! < 0 && before.hash === "", label + ": the footnote mark is scrolled away above: " + JSON.stringify(before));
      const box = await page.locator(".fx-back").boundingBox();
      assert.ok(box, label + ": the back link has a box");
      const x = box.x + box.width / 2, y = box.y + box.height / 2;
      const hit = await page.evaluate(([px, py]: [number, number]) => document.elementFromPoint(px, py)?.tagName ?? null, [x, y] as [number, number]);
      assert.equal(hit, "A", label + ": precondition, the click lands on the link (elementFromPoint)");
      await page.locator(".fx-back").click(mod ? { modifiers: [mod] } : {});
      const after = await state();
      const c: Click = after.click;
      assert.ok(c && c.tag === "A", label + ": precondition, the click reached the document's listeners on the link: " + JSON.stringify(c));
      const held = { shift: mod === "Shift", ctrl: mod === "Control", meta: mod === "Meta" };
      assert.deepEqual({ shift: c!.shift, ctrl: c!.ctrl, meta: c!.meta }, held, label + ": precondition, the click carried the key it was asked for");
      return { before, after };
    };

    // 1. the browser's own gestures: Shift (a window everywhere) and the platform's tab key (Cmd on a Mac, Ctrl elsewhere).
    //    The delegate stands aside: the click's default action, the browser's tab at the page's URL with the fragment,
    //    is not cancelled, and the transcript does not move.
    for (const mod of ["Shift", mac ? "Meta" : "Control"] as const) {
      const r = await clickWith(mod);
      assert.equal(r.after.click.prevented, false, mod + ": left to the browser: the delegate did not cancel the click's default action, which with this key held is the browser's own tab or window: " + JSON.stringify(r));
      assert.equal(r.after.scrollTop, r.before.scrollTop, mod + ": the transcript did not move (the browser's gesture): " + JSON.stringify(r));
      assert.equal(r.after.hash, "", mod + ": the page's own hash is untouched");
      assert.equal(r.after.opens, 0, mod + ": window.open was not called (a tab here is the browser's, not the delegate's)");
    }

    // 2. the other key. On Linux and Windows that is Super (Meta), a plain click to the browser: the delegate resolves it
    //    under the prefix, cancels the default and scrolls the mark to the top, hash untouched, no tab. Before the fix the
    //    delegate stood aside and the browser's default wrote #fn1 and found nothing: flag false, scrollTop unchanged, hash "#fn1".
    if (mac) {
      t.diagnostic("macOS: the other key is Ctrl, whose press is the context menu and dispatches no click; that row is skipped here");
    } else {
      const r = await clickWith("Meta");
      assert.equal(r.after.click.prevented, true, "Meta (Super) off macOS: the delegate resolved the click like a plain one and cancelled its default action: " + JSON.stringify(r));
      assert.ok(r.after.scrollTop < r.before.scrollTop && r.after.fn1! >= -1 && r.after.fn1! < 40,
        "Meta (Super) off macOS: the transcript scrolled the footnote mark to its top like a plain click: " + JSON.stringify(r));
      assert.equal(r.after.hash, "", "Meta off macOS: the default was cancelled, no #fn1 on the page's location");
      assert.equal(r.after.opens, 0, "Meta off macOS: window.open was not called (the browser opens no tab for Super, and the delegate opened none)");
    }

    // 3. a plain click still scrolls (the control for the rows above)
    const plain = await clickWith(null);
    assert.equal(plain.after.click.prevented, true, "a plain click: the delegate found the target and cancelled the default action: " + JSON.stringify(plain));
    assert.ok(plain.after.fn1! >= -1 && plain.after.fn1! < 40 && plain.after.hash === "", "a plain click scrolls the mark to the top, hash untouched: " + JSON.stringify(plain.after));
    assert.equal(plain.after.opens, 0, "a plain click: window.open was not called");

    assert.deepEqual(navs.filter((u) => !u.startsWith("http://romp.test/")), [], "the main frame never navigated off the dashboard");
    assert.deepEqual(errors, [], "no page errors");
    t.diagnostic("tabs the browser opened of its own for the two gestures, closed on arrival (Chromium's behaviour, not asserted): " + tabs.count);
  });
});
