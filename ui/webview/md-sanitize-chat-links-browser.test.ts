// The chat's link delegate over the REAL render.ts bundle in headless Chromium, at an http: origin (the web
// dashboard). Every navigating href a sanitized message can carry must go the way a plain `<a href>` goes: the
// document-level click handler (render.ts) opens it in the user's own browser and cancels the default action,
// so the chat document never leaves. Two shapes the old `closest("a[href]")` missed (the 2026-09-07 review of
// plans/markdown-viewer.md Slice 1): an image map's `<area href>` (not an anchor) and an SVG `<a xlink:href>`
// (`[href]` matches only the null-namespace attribute, and the XLink spelling is namespaced). Both survived the
// sanitizer's html + svg profiles, and a click on either took the chat page to the attacker's URL, losing the
// pane until a reload. Since the round-1 fold the sanitizer forbids map, area and usemap outright (GitHub's rule;
// a prefixed map name could never bind), so the area is a second guard in the delegate's selector. Two legs: the
// delegate's contract over raw markup (what it must do with each shape, whatever a profile lets through), and the
// chat's own markdown pipeline (marked + sanitizeMd, as md() runs it) end to end: whatever survives, a click never
// navigates the document, and the image map is gone. Skips LOUDLY without a playwright browser (CI installs none),
// as the other browser legs do. Synthetic values only: example.invalid URLs.
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

// a valid 1x1 transparent PNG: a picture that decodes, so its image map is live (a broken image shows its alt
// text and binds no map, which would pass the area case for the wrong reason; the precondition below checks)
const PNG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=";
const XLINK = "http://www.w3.org/1999/xlink";

// the shapes, each with the element the click lands on and the URL the delegate must hand to window.open
const SHAPES: { name: string; html: string; sel: string; hit: string; href: string }[] = [
  { name: "a plain anchor (control)", sel: ".fx-body a", hit: "A", href: "https://example.invalid/ctl",
    html: '<p>A <a href="https://example.invalid/ctl">plain link</a> in prose.</p>' },
  { name: "an image map's area", sel: ".fx-body img", hit: "AREA", href: "https://example.invalid/area",
    html: `<p><img src="${PNG}" width="200" height="200" usemap="#user-content-m" alt="pic"><map name="user-content-m"><area href="https://example.invalid/area" shape="default" alt="a"></map></p>` },
  { name: "an SVG anchor spelled xlink:href", sel: ".fx-body svg text", hit: "text", href: "https://example.invalid/xlink",
    html: `<p><svg width="300" height="60" xmlns:xlink="${XLINK}"><a xlink:href="https://example.invalid/xlink"><text x="5" y="40" font-size="30">xlink text</text></a></svg></p>` },
  { name: "an SVG anchor with a plain href (contrast)", sel: ".fx-body svg text", hit: "text", href: "https://example.invalid/svghref",
    html: '<p><svg width="300" height="60"><a href="https://example.invalid/svghref"><text x="5" y="40" font-size="30">svg href text</text></a></svg></p>' },
];
// the same two hostile shapes as a message's own HTML, for the pipeline leg: the image map, spelled as an author spells it,
// is dropped whole by the sanitizer (map, area and usemap are forbidden, md-sanitize.ts: GitHub's rule, and the prefixed
// map name could never bind), so the picture is inert and the click opens nothing; the SVG anchor survives and opens
const MESSAGES: { name: string; md: string; sel: string; hit: string; opens: "link" | "none"; dropped: RegExp | null }[] = [
  { name: "an image map", sel: ".fx-body img", hit: "IMG", opens: "none", dropped: /<map|<area|usemap/,
    md: `<img src="${PNG}" width="200" height="200" usemap="#m" alt="pic"><map name="m"><area href="https://example.invalid/area" shape="default" alt="a"></map>\n\nafter` },
  { name: "an SVG xlink anchor", sel: ".fx-body svg text", hit: "text", opens: "link", dropped: null,
    md: `<svg width="300" height="60" xmlns:xlink="${XLINK}"><a xlink:href="https://example.invalid/xlink"><text x="5" y="40" font-size="30">xlink text</text></a></svg>\n\nafter` },
];

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
// kernel's shim's role), window.open recorded instead of opened, then the chat bundle, a click recorder and the probe.
// The recorder reads each click's own defaultPrevented flag as dispatch ends: following the link is the click's default
// action, and the browser runs it exactly when that flag is still false, so the flag says whether the document WILL
// navigate without waiting to see whether it did (an earlier draft slept 1.2 s per click on a bounded waitForURL and
// spent 12 s of the leg on ten timeouts). Two listeners write it: one at the document's capture phase, registered
// after render.js so it runs right after the delegate on the same node (the delegate stops propagation for a scheme
// link, which stops other nodes' listeners, not a later one on the same node), and one at the window's bubble
// phase, the last stop of a click the delegate let through; the later one to run has the final word.
const CHAT_HTML = `<!DOCTYPE html><html lang=en><head><meta charset=utf-8><style>${STYLES}</style></head><body>
${chatBody(ATTACH_TITLE_WEB)}
<script>window.__opens=[];window.open=function(u,t,f){window.__opens.push([u,t,f]);return null;};
window.acquireVsCodeApi=function(){return{postMessage:function(){}}};</script>
<script src=/dist/render.js></script>
<script>(function(){window.__lastClick=null;function rec(e){window.__lastClick={prevented:e.defaultPrevented,tag:e.target&&e.target.tagName};}
document.addEventListener("click",rec,true);window.addEventListener("click",rec);})();</script>
<script src=/dist/probe.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (page: any, errors: string[], navs: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [], navs: string[] = [];
  try {
    const renderJs = bundle("render.ts"), probeJs = probeBundle();
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) navs.push(f.url()); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      // the attacker's host answers, so a navigation that does happen commits and is seen
      if (u.hostname === "example.invalid") return route.fulfill({ status: 200, contentType: "text/html", body: "<title>elsewhere</title>elsewhere" });
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/chat") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: CHAT_HTML });
      if (u.pathname === "/dist/render.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: renderJs });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/chat");
    await body(page, errors, navs);
  } finally {
    await browser.close();
  }
}

// fill a message body the way render.ts does (body.innerHTML = md(text)), alone in the transcript
async function show(page: any, html: string, throughMd: boolean): Promise<string> {
  return page.evaluate(([h, viaMd]: [string, boolean]) => {
    document.querySelectorAll(".fx-turn").forEach((n) => n.remove());
    const content = document.getElementById("content") as HTMLElement;
    const turn = document.createElement("div"); turn.className = "turn turn-assistant fx-turn";
    const body = document.createElement("div"); body.className = "assistant md fx-body";
    body.innerHTML = viaMd ? (window as any).__mdProbe(h) : h;
    turn.appendChild(body); content.appendChild(turn);
    (window as any).__opens.length = 0;
    return body.innerHTML;
  }, [html, throughMd] as [string, boolean]);
}
// one real click at the element's centre; what elementFromPoint names there, whether the click's default action was
// cancelled (the recorder above; null when no click reached the document, or when the page was gone by the time it
// was read: an uncancelled navigation that committed first destroys the context, and `gone` carries that message),
// and what the delegate opened. page.mouse.click resolves after the renderer has dispatched the click, so the flag
// is final when it is read: no wait.
async function clickCentre(page: any, sel: string): Promise<{ hit: string | null; prevented: boolean | null; opens: unknown[]; gone?: string }> {
  const box = await page.locator(sel).first().boundingBox();
  if (!box) return { hit: null, prevented: null, opens: [] };
  const x = box.x + box.width / 2, y = box.y + box.height / 2;
  const hit = await page.evaluate(([px, py]: [number, number]) => {
    (window as any).__lastClick = null; (window as any).__opens.length = 0;
    const e = document.elementFromPoint(px, py); return e ? e.tagName : null;
  }, [x, y] as [number, number]);
  await page.mouse.click(x, y);
  try {
    const r = await page.evaluate(() => { const c = (window as any).__lastClick; return { prevented: c ? c.prevented as boolean : null, opens: (window as any).__opens as unknown[] }; });
    return { hit, prevented: r.prevented, opens: r.opens };
  } catch (e) {
    return { hit, prevented: null, opens: [], gone: String((e as Error).message).split("\n")[0] };
  }
}
// the tail of an assertion message about r.prevented: what a null means
const why = (r: { prevented: boolean | null; gone?: string }): string =>
  r.gone ? " (the page was gone: " + r.gone + ")" : r.prevented === null ? " (no click reached the document's listeners)" : "";

test("the chat's link delegate: an image map's area and an SVG xlink:href anchor open like a plain link, and the chat document never leaves", { timeout: 90000 }, async (t) => {
  await inBrowser(t, async (page, errors, navs) => {
    // 1. the delegate's contract, shape by shape, over raw markup
    for (const s of SHAPES) {
      await show(page, s.html, false);
      const r = await clickCentre(page, s.sel);
      assert.equal(r.hit, s.hit, s.name + ": precondition, the click lands on the element (elementFromPoint)");
      assert.equal(r.prevented, true, s.name + ": the delegate cancelled the click's default action, so the chat document does not follow the link" + why(r));
      assert.deepEqual(r.opens, [[s.href, "_blank", "noopener,noreferrer"]], s.name + ": the delegate opened the link in the user's browser");
      assert.equal(page.url(), "http://romp.test/chat", s.name + ": the chat page is where it was");
    }
    // 2. the chat's own pipeline: a message carrying either shape, through marked and sanitizeMd as md() runs
    //    them; whatever the sanitizer lets through, a click never moves the document, and what it drops is gone
    for (const m of MESSAGES) {
      const html = await show(page, m.md, true);
      if (m.dropped) assert.doesNotMatch(html, m.dropped, m.name + " in a message: the sanitizer drops the image map whole (map, area, usemap): " + html);
      const r = await clickCentre(page, m.sel);
      assert.equal(r.hit, m.hit, m.name + " in a message: precondition, the click lands on the element (elementFromPoint)");
      // a surviving link is cancelled by the delegate; the picture whose map is gone carries no link, so its click has
      // no default action to cancel and none is (a click on a picture in a message stays the browser's)
      assert.equal(r.prevented, m.opens === "link", m.name + " in a message: the click's default action was " + (m.opens === "link" ? "cancelled by the delegate, so the document does not follow the link" : "left alone: nothing to cancel") + "; sanitized as " + html + why(r));
      if (m.opens === "none") assert.deepEqual(r.opens, [], m.name + " in a message: the picture is inert, nothing opens");
      else assert.deepEqual(r.opens, [["https://example.invalid/xlink", "_blank", "noopener,noreferrer"]], m.name + " in a message: the link opened in the user's browser");
      assert.equal(page.url(), "http://romp.test/chat", m.name + " in a message: the chat page is where it was");
    }
    // the belt: whatever the flag said, no main-frame navigation was seen over the whole leg
    assert.deepEqual(navs.filter((u) => !u.startsWith("http://romp.test/")), [], "the main frame never navigated off the dashboard");
    assert.deepEqual(errors, [], "no page errors");
  });
});

// ── in-page anchors in a message ─────────────────────────────────────────────────────────────────────
// A reply's own `<sup id="fn1">` and `<a href="#fn1">` (a footnote's back link), or `[install](#install)` over its own
// `<a name="install">`: the sanitizer prefixes the id and the name user-content- and leaves the href alone, so the
// browser's default lookup finds nothing and the click died where the base scrolled (the 2026-09-07 review of Slice 1).
// The delegate resolves the fragment itself now (render.ts; md-sanitize.ts userContentTarget): the message's own body
// first, then the document; found, scrollIntoView and preventDefault (the hash stays); not found, the browser's click.
const FILLER = Array.from({ length: 80 }, (_, i) => "Filler paragraph " + (i + 1) + " so the transcript scrolls.").join("\n\n");
const FOOTNOTES = [
  '<a name="install"></a>Claim.<sup id="fn1"><a href="#fnref1" class="fx-fwd">1</a></sup> <a href="#nowhere" class="fx-none">missing</a> <a href="#dup" class="fx-dup">dup</a>',
  '<p id="dup" class="fx-dup-here">this message\'s dup</p>',
  FILLER,
  '<p id="fnref1">1. a note <a href="#fn1" class="fx-back">back</a>, and <a href="#install" class="fx-install">the install anchor</a>.</p>',
].join("\n\n");
// an OLDER message carrying the same id: the click in the newer one must land in its own body, not here
const OLDER = '<p id="dup" class="fx-dup-older">the older dup</p>\n\nolder text';

test("a footnote's back link and a link over the reply's own <a name> land again: resolved under the prefix, in the message first, hash untouched; a fragment with no target is left to the browser", { timeout: 90000 }, async (t) => {
  await inBrowser(t, async (page, errors, navs) => {
    // two messages through the chat's own pipeline (marked + sanitizeMd, as md() runs them): the older one first
    const shape = await page.evaluate(([older, newer]: [string, string]) => {
      document.querySelectorAll(".fx-turn").forEach((n) => n.remove());
      const content = document.getElementById("content") as HTMLElement;
      for (const [cls, src] of [["fx-older", older], ["fx-newer", newer]] as const) {
        const turn = document.createElement("div"); turn.className = "turn turn-assistant fx-turn";
        const body = document.createElement("div"); body.className = "assistant md " + cls;
        body.innerHTML = (window as any).__mdProbe(src);
        turn.appendChild(body); content.appendChild(turn);
      }
      const ids = Array.from(content.querySelectorAll(".fx-turn [id], .fx-turn a[name]")).map((e) => e.getAttribute("id") || ("name=" + e.getAttribute("name")));   // the two messages' own; the chat's chrome wears ids too
      const cs = getComputedStyle(content);
      return { ids, scrollable: content.scrollHeight > content.clientHeight, overflowY: cs.overflowY, hrefs: Array.from(content.querySelectorAll(".fx-newer a[href]")).map((a) => a.getAttribute("href")) };
    }, [OLDER, FOOTNOTES] as [string, string]);
    assert.deepEqual(shape.ids, ["user-content-dup", "name=user-content-install", "user-content-fn1", "user-content-dup", "user-content-fnref1"], "precondition: every author id and name reached the DOM prefixed (SANITIZE_NAMED_PROPS)");
    assert.deepEqual(shape.hrefs, ["#fnref1", "#nowhere", "#dup", "#fn1", "#install"], "precondition: the hrefs are as written, unprefixed");
    assert.ok(shape.scrollable && /auto|scroll/.test(shape.overflowY), "precondition: the transcript scrolls (" + shape.overflowY + ")");

    const state = () => page.evaluate(() => {
      const content = document.getElementById("content") as HTMLElement;
      const top = (sel: string) => { const e = document.querySelector(sel); return e ? Math.round(e.getBoundingClientRect().top - content.getBoundingClientRect().top) : null; };
      return { scrollTop: content.scrollTop, hash: location.hash, fn1: top("#user-content-fn1"), install: top('a[name="user-content-install"]'), dupHere: top(".fx-dup-here"), dupOlder: top(".fx-dup-older") };
    });
    // 1. scrolled to the bottom, the back link is clicked: the claim's footnote mark comes to the top of the transcript
    await page.evaluate(() => { const c = document.getElementById("content") as HTMLElement; c.scrollTop = c.scrollHeight; });
    const before = await state();
    assert.ok(before.scrollTop > 0 && before.fn1! < 0, "the footnote mark is scrolled away above: " + JSON.stringify(before));
    let r = await clickCentre(page, ".fx-back");
    assert.equal(r.hit, "A", "the click lands on the back link");
    assert.equal(r.prevented, true, "the delegate found the target and cancelled the click's default action" + why(r));
    let after = await state();
    assert.ok(after.scrollTop < before.scrollTop && after.fn1! >= -1 && after.fn1! < 40, "the transcript scrolled the footnote mark to its top: " + JSON.stringify(after));
    assert.equal(after.hash, "", "the default was cancelled: no #fn1 on the page's location");
    assert.deepEqual(r.opens, [], "nothing opened");

    // 2. from the bottom again, the link over the reply's own <a name>: the named anchor comes to the top
    await page.evaluate(() => { const c = document.getElementById("content") as HTMLElement; c.scrollTop = c.scrollHeight; });
    r = await clickCentre(page, ".fx-install");
    assert.equal(r.prevented, true, "the delegate found the named anchor and cancelled the click's default action" + why(r));
    after = await state();
    assert.ok(after.install! >= -1 && after.install! < 40, "the named anchor is at the top: " + JSON.stringify(after));
    assert.equal(after.hash, "", "hash untouched");

    // 3. the message's own body first: `#dup` from the newer message lands on ITS <p id="dup">, not the older message's
    await page.evaluate(() => { const c = document.getElementById("content") as HTMLElement; c.scrollTop = c.scrollHeight; });
    await page.evaluate(() => { (document.querySelector(".fx-dup") as HTMLElement).scrollIntoView({ block: "center" }); });
    r = await clickCentre(page, ".fx-dup");
    assert.equal(r.prevented, true, "the delegate found the message's own element and cancelled the click's default action" + why(r));
    after = await state();
    assert.ok(after.dupHere! >= -1 && after.dupHere! < 40, "the newer message's own element is at the top: " + JSON.stringify(after));
    assert.ok(after.dupOlder! < after.dupHere!, "the older message's same-named element stayed above, unchosen");

    // 4. a fragment with no target anywhere: the click is the browser's (its default sets the hash), the transcript does not move
    await page.evaluate(() => { (document.querySelector(".fx-none") as HTMLElement).scrollIntoView({ block: "center" }); });
    const mid = await state();
    r = await clickCentre(page, ".fx-none");
    assert.equal(r.hit, "A", "the click lands on the link");
    assert.equal(r.prevented, false, "left to the browser: the delegate did not cancel the click");
    after = await state();
    assert.equal(after.hash, "#nowhere", "left to the browser: its default action set the hash");
    assert.equal(after.scrollTop, mid.scrollTop, "and nothing scrolled");
    // the same-document navigation as playwright sees it: keyed on the frame's URL event, not a sleep
    await page.waitForURL("http://romp.test/chat#nowhere", { timeout: 5000 });
    assert.equal(page.url(), "http://romp.test/chat#nowhere", "the chat page is where it was, hash aside");

    // the belt: whatever the flag said, no main-frame navigation was seen over the whole leg
    assert.deepEqual(navs.filter((u) => !u.startsWith("http://romp.test/")), [], "the main frame never navigated off the dashboard");
    assert.deepEqual(errors, [], "no page errors");
  });
});

// ── a comment thread's agent reply ───────────────────────────────────────────────────────────────────
// The comment popover (renderCommentPopover, render.ts) renders an agent's reply in its msgs projection through md() into
// `div.cmt-msg.agent` (commentMsgEl), the one md() body that wears no `.md`: the render a thread shows until its events
// arrive, and the whole render under a kernel that sends none. The popover stands on document.body, so no `.md` ancestor
// exists either. The delegate's body scope read `.md` alone, so a reply's own `#` link there was left to the browser's bare
// lookup, which the prefixed id defeats (nothing moved, where the base scrolled the list), and a scheme-less link there was
// left to the default action, which navigated the chat document in the same frame (the round-4 review of Slice 1). The scope
// is `.md, .cmt-msg.agent` now (chat-link-open.test.ts pins it against commentMsgEl). The reply is mounted here
// the way the popover mounts it: `div#cmt-pop.cmt-pop` on document.body, sized inline as at open (70% by 60% of the window),
// a `.cmt-msgs` list inside, the reply filled from the chat's own pipeline (marked + sanitizeMd, as md() runs them).
const REPLY = [
  '<a href="#tgt" class="fx-cmt-hash">to the target</a> and <a href="/x" class="fx-cmt-rel">a root-relative link</a>',
  FILLER,
  '<p id="tgt" class="fx-cmt-tgt">the target</p>',
  FILLER,   // text below the target too, so the list can bring the target to its top (a last element stops at the bottom edge)
].join("\n\n");

test("a comment thread's agent reply (div.cmt-msg.agent, no .md): its own # link scrolls the thread's list, a scheme-less link opens as a link, and the chat document never leaves", { timeout: 90000 }, async (t) => {
  await inBrowser(t, async (page, errors, navs) => {
    const shape = await page.evaluate((src: string) => {
      document.getElementById("cmt-pop")?.remove();
      const pop = document.createElement("div"); pop.className = "cmt-pop"; pop.id = "cmt-pop";
      const head = document.createElement("div"); head.className = "cmt-head"; head.textContent = "a thread"; pop.appendChild(head);
      const list = document.createElement("div"); list.className = "cmt-msgs"; pop.appendChild(list);
      const reply = document.createElement("div"); reply.className = "cmt-msg agent";   // commentMsgEl's class list, as written
      reply.innerHTML = (window as any).__mdProbe(src);
      list.appendChild(reply);
      document.body.appendChild(pop);
      pop.style.width = Math.round(window.innerWidth * 0.7) + "px"; pop.style.height = Math.round(window.innerHeight * 0.6) + "px";
      pop.style.left = "8px"; pop.style.top = "40px";
      list.scrollTop = 0;
      const a = reply.querySelector(".fx-cmt-hash") as HTMLElement;
      const cs = getComputedStyle(list);
      return { ids: Array.from(reply.querySelectorAll("[id]")).map((e) => e.id), hrefs: Array.from(reply.querySelectorAll("a[href]")).map((x) => x.getAttribute("href")),
        inMd: !!a.closest(".md"), scrollable: list.scrollHeight > list.clientHeight, overflowY: cs.overflowY };
    }, REPLY);
    assert.deepEqual(shape.ids, ["user-content-tgt"], "precondition: the reply's id reached the DOM prefixed (SANITIZE_NAMED_PROPS)");
    assert.deepEqual(shape.hrefs, ["#tgt", "/x"], "precondition: the hrefs are as written");
    assert.equal(shape.inMd, false, "precondition: the reply wears no .md and has no .md ancestor (the popover stands on document.body)");
    assert.ok(shape.scrollable && /auto|scroll/.test(shape.overflowY), "precondition: the thread's list scrolls (" + shape.overflowY + ")");

    const state = () => page.evaluate(() => {
      const list = document.querySelector("#cmt-pop .cmt-msgs") as HTMLElement;
      const tgt = document.querySelector(".fx-cmt-tgt") as HTMLElement;
      return { scrollTop: list.scrollTop, hash: location.hash, tgt: Math.round(tgt.getBoundingClientRect().top - list.getBoundingClientRect().top), listH: list.clientHeight };
    });
    const before = await state();
    assert.ok(before.scrollTop === 0 && before.tgt > before.listH, "precondition: the target is below the list's bottom edge: " + JSON.stringify(before));

    // 1. the reply's own # link: resolved under the prefix, the list scrolls the target to its top, the hash stays
    let r = await clickCentre(page, ".fx-cmt-hash");
    assert.equal(r.hit, "A", "the click lands on the link");
    assert.equal(r.prevented, true, "the delegate found the target in the reply and cancelled the click's default action" + why(r));
    const after = await state();
    assert.ok(after.scrollTop > 0 && after.tgt >= -1 && after.tgt < 40, "the thread's list scrolled the target to its top: " + JSON.stringify(after));
    assert.equal(after.hash, "", "the default was cancelled: no #tgt on the page's location");
    assert.deepEqual(r.opens, [], "nothing opened");

    // 2. a scheme-less link in the reply: opened at the resolved address in the user's browser, the document kept
    await page.evaluate(() => { (document.querySelector("#cmt-pop .cmt-msgs") as HTMLElement).scrollTop = 0; });
    r = await clickCentre(page, ".fx-cmt-rel");
    assert.equal(r.hit, "A", "the click lands on the link");
    assert.equal(r.prevented, true, "the delegate cancelled the click's default action, so the chat document does not follow the link" + why(r));
    assert.deepEqual(r.opens, [["http://romp.test/x", "_blank", "noopener,noreferrer"]], "the delegate opened the link at the address the browser would have resolved");
    assert.equal(page.url(), "http://romp.test/chat", "the chat page is where it was");

    // the belt: the main frame saw the load and nothing after it (no #tgt, no /x)
    assert.deepEqual(navs, ["http://romp.test/chat"], "the main frame never navigated after the load");
    assert.deepEqual(errors, [], "no page errors");
  });
});
