// The feed document's focus-return policy under the viewer and the browser, in headless Chromium over the REAL feed bundle
// (plans/markdown-viewer.md Slice 6, item 1; the review's round 1, the PLAUSIBLE finding on feed.ts's click listener). The feed
// is mouse-driven, so after any click in it the listener hands the page's focus back to the chat iframe on a zero timer,
// unless feedWantsKeys says the feed needs the keys (the card cursor armed, a feed modal up, a click in a text field). The
// viewer and the file browser mount in the feed document too (initFileView, initFileBrowse), and neither is excepted, so the
// finding read: a click inside the feed's viewer hands the page's focus to the chat frame right after takeKeyboard gave the
// body the keyboard, and with the composer as the chat frame's last-focused element the restore lands in a typing target,
// which every later landing yields to. MEASURED here and found inert in the dashboard: returnFocusToChat looks the chat frame
// up by an id the served shell does not carry (the shell's chat and feed iframes are f-chat and f-feed, kernel.py's landing
// page; the lookup names another id), so the hand-back finds no frame and moves nothing; the standalone /feed page has no
// parent and the VS Code webview's parent is another origin, the two no-op cases the listener's own comment names.
// The scenes run the real feed bundle (feed.ts and, through it, file-view.ts and file-browse.ts) in a shell stand-in with the
// served ids, a chat iframe holding a textarea composer beside it, the composer typed in before each gesture so that a
// hand-back that did reach the chat frame would restore a typing target: a relayed open (the shell's viewFile post into the
// feed frame) leaves the composer holding the keyboard, as the frames rule has it, and a relayed open over a plain holder
// lands the keyboard on the body; then a click on the note's text, a click on the Raw toggle, a click on the Outline button
// and a click on a file row of the browser each register the listener's timer (counted by the page: the timer is the
// feed's own, waited for by its firing, never a sleep), and after it fires the feed document still holds the page's focus,
// the body (or the popover) still holds the keyboard, PageDown scrolls the note, and the composer takes no letter. A control
// closes the text-click scene: the hand-back's own call, made by hand at the top window against the served id, does move the
// page's focus into the chat frame, after which PageDown scrolls no note, so the reads here would catch a live hand-back; it
// lands on the chat's BODY, not the composer, since Chromium clears a frame's focused element when the page's focus moves
// into another frame (read right after the click), so the finding's second half, a restored composer that every later
// landing yields to, does not hold either. GREEN over a git archive of 3e433ceee (the round's head) and at the fix head: a
// record of the refutation, not a fails-before. If the lookup ever resolves (the id corrected, or the shell renamed to
// match), the four post-timer reads go red, and the fix is to except the viewer and the browser in feedWantsKeys while they
// are up (boardCovered, the gate the card cursor already reads), never a timer. Skips LOUDLY without a playwright browser
// (CI installs none), as the other legs do. Synthetic values only: the notes-api world, the placeholder sid, hostname
// TESTHOST, an invented origin.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, frames, scriptLiteral, requireCjs, UI, EXT, ORIGIN, ROOT, REPORT, SID, MT, LONG } from "./real-viewer-leg";

const web = (f: string) => fs.readFileSync(path.join(UI, f), "utf8").replace('@import "katex/dist/katex.min.css";', "");

let feedBundle: string | null = null;
/** The feed page's bundle as the webview build bundles it (esbuild.js's feed.ts entry), in memory. */
function bundleFeed(): string {
  if (feedBundle) return feedBundle;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, "feed.ts")], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  assert.equal(r.outputFiles.length, 1, "the feed entry bundles to one output (feed.ts imports no sheet; feed.css is the build's own entry)");
  feedBundle = r.outputFiles[0].text as string;
  return feedBundle;
}

const DOCS_DIR = ROOT + "/docs";
const LISTING = { [DOCS_DIR]: [{ name: "report.md", isDir: false, isLink: false, size: LONG.length, mtime: 1757145600, viewable: true }] };
/** One card on the board behind the viewer: what a feed page shows. */
function frameWithOneCard(): Record<string, unknown> {
  const now = Math.floor(Date.now() / 1000);
  const text = "Wire the notes-api health route";
  const color = { bg: "#3366cc", fg: "#ffffff" };
  const card = { itemId: "g1", sid: SID, name: "web", color, text, t: now - 240, live: true, turnId: "turn-g1", column: "working", summary: null, blockSummary: null,
    tree: [{ id: "g1", kind: "ask", text, who: "web", whoSid: SID, whoColor: null, status: "open", t: now - 240, last: now - 240, children: [] }] };
  return { type: "feed", now, nowAt: now * 1000, buildId: 1, asks: [card], working: [], awaiting: [], stateUnknown: [], order: [SID], selfHost: "TESTHOST",
    sessions: [{ sid: SID, name: "web", color }], userTodos: {}, bgServices: {} };
}

/** The feed page: the feed's sheets, the pane's three divs, the kernel shim stood in (posts recorded, a listDir answered), the
 *  viewer's fetch answered from a table, the zero-delay timers counted, then the real bundle. */
function feedPage(): string {
  return `<!DOCTYPE html><html><head><meta charset=utf-8><style>${web("feed.css")}\n${web("gear.css")}</style></head>
<body><div id="feed-head"></div><div id="feed-list"></div><div id="feed-foot"></div><script>
// every zero-delay timer of this document: registered (__t0Set), and pending until it fires or is cleared (__t0Pending), so a
// leg can wait for the click listener's own timer to have run, on the timer's firing and never on a sleep
(function () {
  var st = window.setTimeout, ct = window.clearTimeout, pending = new Set(); window.__t0Set = 0;
  window.setTimeout = function (cb, ms) {
    var rest = Array.prototype.slice.call(arguments, 2);
    if (typeof cb !== "function" || (ms !== undefined && ms !== 0 && ms !== "0")) return st.apply(window, arguments);
    window.__t0Set++;
    var id = st.call(window, function () { pending.delete(id); cb.apply(null, rest); }, 0);
    pending.add(id); return id;
  };
  window.clearTimeout = function (id) { pending.delete(id); return ct.call(window, id); };
  window.__t0Pending = function () { return pending.size; };
})();
window.__docs = ${scriptLiteral({ [REPORT]: LONG })}; window.__mtime = ${scriptLiteral(MT)}; window.__posted = []; window.__listing = ${scriptLiteral(LISTING)};
// the kernel page's shim, stood in: the bundle's posts are recorded, and the browser's listDir is answered as the kernel's socket answers it
window.acquireVsCodeApi = function () { return { postMessage: function (m) {
  window.__posted.push(m);
  if (m && m.type === "listDir") {
    var entries = window.__listing[m.path] || [];
    var reply = { type: "dirListing", reqId: m.reqId, base: m.path, parent: null, entries: entries, total: entries.length, truncated: false };
    Promise.resolve().then(function () { window.dispatchEvent(new MessageEvent("message", { data: reply })); });
  }
} }; };
// the viewer's fetch: the kernel's file route answered from the table (a HEAD with the GET's headers and no body)
window.fetch = async function (url, init) {
  url = String(url); var head = !!(init && init.method === "HEAD");
  if (url.indexOf("/version") === 0) return new Response(JSON.stringify({ fileEditing: true }), { headers: { "Content-Type": "application/json" } });
  if (url.indexOf("/sessions") === 0) return new Response("[]", { headers: { "Content-Type": "application/json" } });
  var m = /[?&]path=([^&]*)/.exec(url); var p = m ? decodeURIComponent(m[1]) : "";
  var text = window.__docs[p];
  if (text === undefined) return new Response(head ? null : "no such file: " + p, { status: 404 });
  return new Response(head ? null : text, { status: 200, headers: { "Content-Type": "text/plain; charset=utf-8", "X-Romp-Mtime-Ns": window.__mtime, "X-Romp-Text-Utf8": "1" } });
};
</script><script>${bundleFeed()}</script></body></html>`;
}
const CHAT = '<!DOCTYPE html><html><body style="margin:8px"><textarea id="composer-input" style="width:260px;height:80px"></textarea><p id="plain">chat pane stand-in</p></body></html>';
// the served shell's ids for the two frames (kernel.py's landing page; file-view-keyboard-frames-browser.test.ts stands the chat and Files frames in the same way)
const SHELL = `<!DOCTYPE html><html><body style="margin:0"><div style="height:20px">shell stand-in</div><iframe id="f-chat" src="${ORIGIN}/chat" style="width:300px;height:560px"></iframe><iframe id="f-feed" src="${ORIGIN}/feed" style="width:660px;height:560px"></iframe></body></html>`;

type Mounted = { page: any; fa: any; fb: any; errors: string[] };
/** The shell stand-in with the chat frame and the feed frame loaded, the feed bundle booted (its ready post) and one card painted. */
async function mount(browser: any): Promise<Mounted> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 600 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const feedHtml = feedPage();
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
    const p = new URL(route.request().url()).pathname;
    if (p === "/") return route.fulfill({ status: 200, contentType: "text/html", body: SHELL });
    if (p === "/chat") return route.fulfill({ status: 200, contentType: "text/html", body: CHAT });
    if (p === "/feed") return route.fulfill({ status: 200, contentType: "text/html", body: feedHtml });
    if (p.startsWith("/media/")) return route.fulfill({ status: 200, contentType: "image/svg+xml", body: "<svg xmlns='http://www.w3.org/2000/svg'></svg>" });
    return route.fulfill({ status: 404, contentType: "text/plain", body: "" });
  });
  await page.goto(ORIGIN + "/");
  const fa = page.frames().find((f: any) => f.url() === ORIGIN + "/chat"), fb = page.frames().find((f: any) => f.url() === ORIGIN + "/feed");
  assert.ok(fa && fb, "both iframes loaded");
  await fb.waitForFunction(() => (window as any).__posted.some((m: any) => m && m.type === "ready"), null, { timeout: 10000 });
  await fb.evaluate((f: Record<string, unknown>) => { window.dispatchEvent(new MessageEvent("message", { data: f })); }, frameWithOneCard());
  await fb.waitForFunction(() => document.querySelectorAll(".feed-cols .fitem").length === 1, null, { timeout: 10000 });
  await frames(fb, 2);
  return { page, fa, fb, errors };
}
type Holder = { active: string; hasFocus: boolean };
/** A frame's active element (tag, id, classes) and whether its document holds the page's focus. */
const holder = (frame: any): Promise<Holder> => frame.evaluate(() => { const a = document.activeElement as HTMLElement | null; return { active: a ? a.tagName + (a.id ? "#" + a.id : "") + (a.className ? "." + String(a.className).split(/\s+/).filter(Boolean).join(".") : "") : "none", hasFocus: document.hasFocus() }; });
const topActive = (page: any): Promise<string> => page.evaluate(() => { const a = document.activeElement; return a ? a.tagName + "#" + a.id : "none"; });
const composer = (fa: any): Promise<string> => fa.evaluate(() => (document.getElementById("composer-input") as HTMLTextAreaElement).value);
const timersSet = (fb: any): Promise<number> => fb.evaluate(() => (window as any).__t0Set as number);
/** Wait until every zero-delay timer the feed document registered has fired (or was cleared): the click listener's among them. */
const timersFired = (fb: any): Promise<unknown> => fb.waitForFunction(() => (window as any).__t0Pending() === 0, null, { timeout: 10000 });
const scrollTopOf = (fb: any): Promise<number> => fb.evaluate(() => (document.querySelector(".fileview-body") as HTMLElement).scrollTop);
/** The shell's relay into the feed frame, as kernel.py's landing page posts it (viewFile, browseFiles). */
const relay = (page: any, m: Record<string, unknown>): Promise<void> => page.evaluate((msg: Record<string, unknown>) => { (document.getElementById("f-feed") as HTMLIFrameElement).contentWindow!.postMessage(msg, "*"); }, m);
async function openReport(page: any, fb: any): Promise<void> {
  await relay(page, { romp: "viewFile", path: REPORT, sid: SID, at: null });
  await fb.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-md > p"), null, { timeout: 10000 });
  await frames(fb, 3);
}
/** The composer in the chat frame clicked and typed in: the chat frame's last-focused element is a typing target. */
async function typeInComposer(page: any, fa: any): Promise<void> {
  await fa.click("#composer-input"); await page.keyboard.type("ab");
  assert.equal((await holder(fa)).active, COMPOSER, "the composer holds the keyboard before the gesture");
}
/** After a click in the feed document: the listener registered its timer, and it has fired. */
async function clickTimerRan(fb: any, set0: number, what: string): Promise<void> {
  assert.ok((await timersSet(fb)) > set0, what + ": the feed's click listener registered its focus-return timer (the real listener ran on the click)");
  await timersFired(fb);
}
/** The feed document holds the page's focus with `active` holding the keyboard, the chat frame does not, and a typed letter reaches no composer. */
async function feedHolds(page: any, fa: any, fb: any, active: string, what: string): Promise<void> {
  const b = await holder(fb), a = await holder(fa);
  assert.equal(b.active, active, what + ": after the timer fired, " + active + " holds the keyboard in the feed document (a hand-back that reached the chat frame would have restored its composer)");
  assert.equal(b.hasFocus, true, what + ": the feed document holds the page's focus after the timer");
  assert.equal(a.hasFocus, false, what + ": the chat document does not");
  assert.equal(await topActive(page), "IFRAME#f-feed", what + ": the top window's active frame is the feed");
  await page.keyboard.type("z");
  assert.equal(await composer(fa), "ab", what + ": the typed letter reached no composer");
}
/** The note's scroll has settled: its scrollTop unchanged over three consecutive animation frames (Chromium animates a keyboard
 *  scroll; a read mid-animation would move under a later assertion). The frames are the event, never a sleep. */
const scrollSettled = (fb: any): Promise<null> => fb.evaluate(() => new Promise<null>((r) => {
  const b = document.querySelector(".fileview-body") as HTMLElement; let last = b.scrollTop, same = 0;
  const f = () => { if (b.scrollTop === last) { if (++same >= 3) return r(null); } else { same = 0; last = b.scrollTop; } requestAnimationFrame(f); }; f();
}));
/** PageDown, pressed with no focus call of the leg's own, scrolls the note (the acceptance: the body has the keyboard). */
async function pageDownScrolls(page: any, fb: any, what: string): Promise<void> {
  const st0 = await scrollTopOf(fb);
  await page.keyboard.press("PageDown");
  const moved = await fb.waitForFunction((v: number) => (document.querySelector(".fileview-body") as HTMLElement).scrollTop > v, st0, { timeout: 4000 }).then(() => true, () => false);
  assert.ok(moved, what + ": PageDown scrolled the note (read " + (await scrollTopOf(fb)) + " from " + st0 + "; a key landing in the chat frame scrolls nothing here)");
  await scrollSettled(fb);
}
const COMPOSER = "TEXTAREA#composer-input", BODY = "DIV.fileview-body", POPOVER = "DIV.fileview-outline";

test("in a browser, the real feed bundle in the served shell's frame arrangement: a relayed open over a plain holder lands the keyboard on the body; with the composer typed in, the relayed open leaves the composer holding it, and then a click on the note's text and a click on the Raw toggle each fire the feed's focus-return timer with the body still holding the keyboard after it (the hand-back's lookup finds no frame under the served ids), PageDown scrolling the note and the composer taking no letter; the hand-back's own call made by hand at the top window does move the page's focus into the chat frame, onto its body and not the composer, after which PageDown scrolls no note, so the reads would catch a live one", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a plain holder in the chat frame (a click on its text, the pill click's stand-in): the relay's landing takes the keyboard for the body
    {
      const { page, fa, fb, errors } = await mount(browser);
      await fa.click("#plain");
      assert.equal((await holder(fa)).active, "BODY", "the chat's body holds the focus after a plain click");
      await openReport(page, fb);
      const b = await holder(fb);
      assert.equal(b.active, BODY, "the relayed open landed the keyboard on the body (a plain holder in the chat frame yields)");
      assert.equal(b.hasFocus, true, "the feed document holds the page's focus");
      await pageDownScrolls(page, fb, "the plain-holder relay");
      assert.deepEqual(errors, [], "no page errors (the plain-holder scene)");
      await page.close();
    }
    // the composer typed in, the relayed open, then a click on the note's text
    {
      const { page, fa, fb, errors } = await mount(browser);
      await typeInComposer(page, fa);
      await openReport(page, fb);
      const a0 = await holder(fa), b0 = await holder(fb);
      assert.equal(a0.active, COMPOSER, "the relayed open leaves the composer holding the keyboard (the frames rule, in the feed document)");
      assert.equal(a0.hasFocus, true, "the chat document holds the page's focus after the relay"); assert.equal(b0.hasFocus, false, "the feed document does not");
      const set0 = await timersSet(fb);
      await fb.click(".fileview-body", { position: { x: 30, y: 60 } });
      assert.equal((await holder(fa)).active, "BODY", "the click into the feed frame cleared the chat document's focused element to its body (Chromium: a frame that loses the page's focus to another frame keeps no focused element), so no hand-back could restore the composer");
      await clickTimerRan(fb, set0, "the text click");
      await feedHolds(page, fa, fb, BODY, "the text click");
      await pageDownScrolls(page, fb, "the text click");
      // the control: the hand-back's call, made by hand against the served id, moves the page's focus into the chat frame, onto its
      // body (the composer is not restored, the read above), and the note no longer takes the keys
      await page.evaluate(() => { (document.getElementById("f-chat") as HTMLIFrameElement).contentWindow!.focus(); });
      await frames(fa, 1);
      const a1 = await holder(fa), b1 = await holder(fb);
      assert.equal(await topActive(page), "IFRAME#f-chat", "the control: the top window's active frame is the chat after the hand-back's call");
      assert.equal(a1.hasFocus, true, "the control: the chat document holds the page's focus"); assert.equal(b1.hasFocus, false, "the control: the feed document lost it");
      assert.deepEqual({ chat: a1.active, feedTag: b1.active.split(".")[0] }, { chat: "BODY", feedTag: "BODY" }, "the control: the chat's body holds the keyboard (a non-typing holder, not the composer), and the feed document's focused element was cleared to its body (the document's, wearing the viewer's fileview-open class, not the viewer's)");
      await scrollSettled(fb);
      const st1 = await scrollTopOf(fb);
      await page.keyboard.press("PageDown"); await frames(fb, 3); await scrollSettled(fb);
      assert.equal(await scrollTopOf(fb), st1, "the control: PageDown scrolls no note once the chat frame holds the page's focus (what a live hand-back would cost the reader)");
      await page.keyboard.type("z");
      assert.equal(await composer(fa), "ab", "the control: the letter reaches no composer either");
      assert.deepEqual(errors, [], "no page errors (the text-click scene)");
      await page.close();
    }
    // the composer typed in, the relayed open, then a click on the Raw toggle (the paint hands the keyboard from the button to the body)
    {
      const { page, fa, fb, errors } = await mount(browser);
      await typeInComposer(page, fa);
      await openReport(page, fb);
      const set0 = await timersSet(fb);
      await fb.locator(".fileview-acts button", { hasText: /^Raw$/ }).click();
      await fb.waitForFunction(() => !!document.querySelector(".fileview-body code.hljs .fv-cl"), null, { timeout: 10000 });
      await frames(fb, 2);
      await clickTimerRan(fb, set0, "the Raw toggle");
      await feedHolds(page, fa, fb, BODY, "the Raw toggle");
      await pageDownScrolls(page, fb, "the Raw toggle");
      assert.deepEqual(errors, [], "no page errors (the Raw scene)");
      await page.close();
    }
  });
});

test("in a browser, the real feed bundle in the served shell's frame arrangement, the composer typed in: a click on the Outline button leaves the popover holding the keyboard after the feed's focus-return timer fires (a hand-back into the chat frame would have closed it through its focusout closer); the shell's browseFiles relay lists a directory and a click on a file row opens the viewer with the body holding the keyboard after the timer, PageDown scrolling and the composer taking no letter", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // the Outline button
    {
      const { page, fa, fb, errors } = await mount(browser);
      await typeInComposer(page, fa);
      await openReport(page, fb);
      const set0 = await timersSet(fb);
      await fb.click(".fileview-acts .fileview-outline-btn");
      await fb.waitForFunction(() => !!document.querySelector(".fileview-outline"), null, { timeout: 10000 });
      await frames(fb, 1);
      await clickTimerRan(fb, set0, "the Outline button");
      await feedHolds(page, fa, fb, POPOVER, "the Outline button");
      const st = await fb.evaluate(() => ({ popover: !!document.querySelector(".fileview-outline"), expanded: (document.querySelector(".fileview-outline-btn") as HTMLElement).getAttribute("aria-expanded") }));
      assert.deepEqual(st, { popover: true, expanded: "true" }, "the popover stands open after the timer (a focus move into another frame would have closed it: the closer's null relatedTarget branch)");
      assert.deepEqual(errors, [], "no page errors (the Outline scene)");
      await page.close();
    }
    // the file browser: the shell's browseFiles relay, the listing answered, a click on the file row opens the viewer
    {
      const { page, fa, fb, errors } = await mount(browser);
      await typeInComposer(page, fa);
      await relay(page, { romp: "browseFiles", path: DOCS_DIR, sid: SID });
      await fb.waitForFunction(() => !!document.querySelector('#romp-filebrowse .fb-row[data-act="file"]'), null, { timeout: 10000 });
      await frames(fb, 1);
      assert.equal((await holder(fa)).active, COMPOSER, "the browser's open leaves the composer holding the keyboard (its rows take none)");
      const set0 = await timersSet(fb);
      await fb.click('#romp-filebrowse .fb-row[data-act="file"]');
      await fb.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-md > p"), null, { timeout: 10000 });
      await frames(fb, 3);
      await clickTimerRan(fb, set0, "the browser's row click");
      await feedHolds(page, fa, fb, BODY, "the browser's row click");
      await pageDownScrolls(page, fb, "the browser's row click");
      assert.deepEqual(errors, [], "no page errors (the browser scene)");
      await page.close();
    }
  });
});
