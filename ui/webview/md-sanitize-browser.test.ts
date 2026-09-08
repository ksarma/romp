// A note's own HTML in the file viewer, over the REAL files bundle in headless Chromium (plans/markdown-viewer.md,
// Slice 1: sanitize as GitHub does). The audit's two High defects are the fixture: a `<style>` block that blanks
// the page and a fixed div that covers the close button; a `<form action=…><button>` that navigates the Files
// document away. The leg proves what the sanitizer's rules (md-sanitize.ts), the body's submit backstop
// (file-view.ts) and `contain: layout` on .fileview-md (both sheets) do together, as the browser lays them out:
// no <style>/<form>/<button>/<select>/<dialog>/<textarea> in the rendered note; a coloured span keeps its colour
// and nothing else; an author's id and name are prefixed user-content-; an author's data-* attributes are gone
// and the span that wore them stays; the task checkbox survives, inert; a text input and a select do not; table
// alignment and an image's width/height survive; the point where the form's text landed is prose, and a click
// there leaves location.href alone, as does a real submit; an element wearing one of the page's fixed classes
// stays inside the note, and even an injected `position:fixed; inset:0` box cannot reach the close button; the
// body still scrolls to the end of a long note; and over the whole leg, read from the page's own events rather
// than waited for, the document never navigated after its load and no request left the page's host. Skips
// LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only:
// an invented note, TESTHOST paths, a placeholder sid.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const PANE = fs.readFileSync(path.join(UI, "files-pane.css"), "utf8");

const SID = "11111111-2222-3333-4444-555555555555";
const PATH = "/tmp/TESTHOST/notes-api/report.md";

// the fixture note: every construct the slice rules on, the hostile ones first so they sit in view without a scroll
const NOTE = [
  "# Report",
  "",
  "<style>.fileview, #romp-fileview { display: none !important; } body { background: red; }</style>",
  "",
  '<div class="fx-fixed" style="position:fixed;inset:0;background:red">cover</div>',
  "",
  'A <span class="fx-span" style="color: rgb(200, 0, 0); font-size: 80px">x</span> in prose.',
  "",
  'A <span class="fx-tagged" data-act="stopRetrying" data-fx="1">tagged</span> span.',
  "",
  '<form action="https://example.invalid/go"><button>Go</button></form>',
  "",
  '<p id="top">Top paragraph.</p>',
  "",
  '<a name="install"></a>',
  "",
  "- [x] done",
  "- [ ] later",
  "",
  '<input type="text" value="typed">',
  "",
  "<select><option>a</option></select>",
  "",
  "<dialog open>hi</dialog>",
  "",
  "<textarea>notes</textarea>",
  "",
  "| Left | Centre | Right |",
  "|:-----|:------:|------:|",
  "| a    |   b    |     c |",
  "",
  '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" width=120 height=40 alt="dot">',
  "",
  '<div class="cite-preview fx-classed">a box wearing one of the page\'s fixed classes</div>',
  "",
  ...Array.from({ length: 120 }, (_, i) => "Paragraph " + (i + 1) + " of the long tail, so the body has to scroll.\n"),
  "",
  "Last line.",
  "",
].join("\n");

function bundle(entry: string): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    entryPoints: [path.join(UI, entry)], bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the Files page as the kernel serves it (_files_page): the chat's styles.css for the viewer's dress, files-pane.css
// after it for the pane layout, a fake acquireVsCodeApi (the shim's role), then the files bundle
const FILES_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}\n${PANE}</style></head><body class=fileview-pane>
<div id=files-empty></div>
<script>window.__posts=[];window.acquireVsCodeApi=function(){return{postMessage:function(m){window.__posts.push(m);}}};</script>
<script src=/dist/files.js></script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

// What the page's own events say happened over the whole leg: every main-frame navigation (the load is one), and
// every request whose host is not the page's (a submitted `<form action=https://example.invalid/go>` would be one).
type Seen = { navigations: string[]; foreignRequests: string[] };

async function inBrowser(t: any, body: (page: any, errors: string[], seen: Seen) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const seen: Seen = { navigations: [], foreignRequests: [] };
  try {
    const filesJs = bundle("files.ts");
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("framenavigated", (f: any) => { if (f === page.mainFrame()) seen.navigations.push(f.url()); });
    page.on("request", (r: any) => { const u = new URL(r.url()); if (u.protocol !== "data:" && u.host !== "romp.test") seen.foreignRequests.push(r.url()); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/files") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: FILES_HTML });
      if (u.pathname === "/dist/files.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: filesJs });
      if (u.pathname === "/file" && u.searchParams.get("path") === PATH) {
        return route.fulfill({ status: 200, contentType: "text/plain; charset=utf-8", headers: { "X-Romp-Mtime-Ns": "1", "X-Romp-Text-Utf8": "1" }, body: NOTE });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/files");
    await page.evaluate(([p, sid]: [string, string]) => { window.postMessage({ romp: "viewFile", path: p, sid }, "*"); }, [PATH, SID] as [string, string]);
    await page.waitForSelector("#romp-fileview .fileview-body .fileview-md", { timeout: 10000 });
    await body(page, errors, seen);
  } finally {
    await browser.close();
  }
}

// The legs of this family (md-sanitize*-browser and the file-view-links leg they run beside) resolve playwright and esbuild
// from the extension's package.json, never from the bundle's own path: npm test writes the bundle under
// vscode-extension/out-tests, where a walk-up finds node_modules, but the single-file recipe writes it under TMPDIR, where
// nothing is above it, and a require created from the bundle's own filename then reports playwright missing while it is
// installed, so the leg skips with a false diagnosis (review round 2, 2026-09-08: seven legs skipped that way while two
// ran). Node-side: no browser. The forbidden form is matched by pattern so this file's own text does not trip it.
test("every md-sanitize browser leg resolves its runtime requires from the extension, not from the bundle's path", () => {
  const legs = fs.readdirSync(UI).filter((n) => /^md-sanitize.*-browser\.test\.ts$/.test(n) || n === "file-view-links-browser.test.ts").sort();
  assert.ok(legs.includes("md-sanitize-browser.test.ts"), "the family was found under ui/webview: " + legs.join(", "));
  const fromBundlePath = /createRequire\(\s*__filename\s*\)/;
  const fromExtension = 'createRequire(path.join(EXT, "package.json"))';
  for (const leg of legs) {
    const src = fs.readFileSync(path.join(UI, leg), "utf8");
    assert.ok(!fromBundlePath.test(src), leg + ": the require is created from the bundle's own path, so the leg skips when it is bundled outside vscode-extension");
    assert.ok(src.includes(fromExtension), leg + ": resolve playwright and esbuild through the extension's package.json");
  }
});

type Rect = { left: number; top: number; right: number; bottom: number; width: number; height: number };
const near = (a: number, b: number, msg: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);

test("a note's own HTML in the rendered file view: GitHub's rules, as the browser lays them out", { timeout: 60000 }, async (t) => {
  await inBrowser(t, async (page, errors, seen) => {
    // 1. the forbidden elements are gone, the page is not blanked, and the sanitizer's other verdicts hold
    const facts = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const count = (sel: string) => md.querySelectorAll(sel).length;
      const span = md.querySelector(".fx-span") as HTMLElement;
      const fixed = md.querySelector(".fx-fixed") as HTMLElement;
      const card = document.querySelector("#romp-fileview .fileview") as HTMLElement;
      return {
        forbidden: count("style, form, button, select, option, dialog, textarea"),
        stylesAnywhere: document.querySelectorAll("#romp-fileview style").length,
        cardDisplay: getComputedStyle(card).display,
        bodyBackground: getComputedStyle(document.body).backgroundColor,
        spanStyleAttr: span.getAttribute("style"),
        spanColor: getComputedStyle(span).color,
        spanFontSize: getComputedStyle(span).fontSize,
        proseFontSize: getComputedStyle(span.parentElement as HTMLElement).fontSize,
        fixedStyleAttr: fixed.getAttribute("style"),
        fixedPosition: getComputedStyle(fixed).position,
        fixedText: fixed.textContent,
        goText: (md.textContent || "").includes("Go"),
        userContentTop: count('p#user-content-top'),
        rawTop: count("#top"),
        userContentInstall: count('a[name="user-content-install"]'),
        rawInstall: count('a[name="install"]'),
        heading: count("h1#md-report"),
        prefixedHeadings: count('h1[id^="user-content-"], h2[id^="user-content-"]'),
        checkboxes: count('input[type="checkbox"][disabled]'),
        checked: count('input[type="checkbox"]:checked'),
        otherInputs: count('input:not([type="checkbox"])'),
        textInputs: count('input[type="text"]'),
        alignedCells: count('td[align="center"]'),
        alignedHeads: count('th[align="center"]'),
        sizedImg: count('img[width="120"][height="40"]'),
        dialogText: (md.textContent || "").includes("hi"),
        taggedSpans: count(".fx-tagged"),
        taggedText: (md.querySelector(".fx-tagged") as HTMLElement | null)?.textContent ?? null,
        // keyed on the AUTHOR's attributes: mdBlock stamps data-act on links after the sanitize (fv-open, fv-anchor)
        authorDataAttrs: count("[data-fx], .fx-tagged[data-act]"),
      };
    });
    assert.equal(facts.forbidden, 0, "no style, form, button, select, option, dialog or textarea in the rendered note");
    assert.equal(facts.stylesAnywhere, 0);
    assert.notEqual(facts.cardDisplay, "none", "the note's <style> did not blank the viewer");
    assert.notEqual(facts.bodyBackground, "rgb(255, 0, 0)", "…nor restyle the page");
    assert.equal(facts.spanStyleAttr, "color: rgb(200, 0, 0)", "the span keeps only its colour declaration");
    assert.equal(facts.spanColor, "rgb(200, 0, 0)");
    assert.equal(facts.spanFontSize, facts.proseFontSize, "font-size: 80px was dropped: the span reads at the prose size");
    assert.equal(facts.fixedStyleAttr, null, "position/inset/background all dropped: the attribute goes");
    assert.equal(facts.fixedPosition, "static");
    assert.equal(facts.fixedText, "cover", "the div's text stays (it is prose); its styling does not");
    assert.ok(facts.goText, "the form's text landed as prose");
    assert.equal(facts.userContentTop, 1, "GitHub's rule: an author's id is prefixed user-content-");
    assert.equal(facts.rawTop, 0);
    assert.equal(facts.userContentInstall, 1, "…and so is an author's name");
    assert.equal(facts.rawInstall, 0);
    assert.equal(facts.heading, 1, "the viewer's own heading ids are minted after the sanitize and never prefixed");
    assert.equal(facts.prefixedHeadings, 0);
    assert.equal(facts.checkboxes, 2, "both task checkboxes survive, disabled");
    assert.equal(facts.checked, 1, "…and the ticked one is still ticked");
    assert.equal(facts.otherInputs, 0, "no other input survives");
    assert.equal(facts.textInputs, 0);
    assert.equal(facts.alignedCells, 1, "table alignment (the align attribute) survives");
    assert.equal(facts.alignedHeads, 1);
    assert.equal(facts.sizedImg, 1, "an image's width/height survive");
    assert.equal(facts.taggedSpans, 1, "the span that wore data-* is still there");
    assert.equal(facts.taggedText, "tagged");
    assert.equal(facts.authorDataAttrs, 0, "an author's data-fx / data-act never ride in (ALLOW_DATA_ATTR: false): the page's delegates key off data-act");

    // 2. the point where the form's text landed is prose (elementFromPoint, no control above it: a fact about the rendered
    //    DOM that holds or fails on its own), and a click there navigates nowhere (the plan's acceptance; the bounded wait
    //    gives a navigation time to commit, and step 6 reads the same over the whole leg from the page's events)
    const before = page.url();
    const goAt = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const walker = document.createTreeWalker(md, NodeFilter.SHOW_TEXT);
      let node: Node | null;
      while ((node = walker.nextNode())) {
        if ((node.textContent || "").trim() === "Go") {
          const range = document.createRange(); range.selectNodeContents(node);
          const r = range.getBoundingClientRect();
          const x = r.left + r.width / 2, y = r.top + r.height / 2;
          const e = document.elementFromPoint(x, y);
          return { x, y, w: r.width, h: r.height, hit: e ? e.tagName + "." + e.className : "nothing", inControl: !!(e && e.closest("form, button, input, select, textarea")) };
        }
      }
      return null;
    });
    assert.ok(goAt && goAt.w > 0 && goAt.h > 0, "the form's text is laid out in the note: " + JSON.stringify(goAt));
    assert.equal(goAt!.inControl, false, "the point to click is prose, not a form or a control: " + goAt!.hit);
    await page.mouse.click(goAt!.x, goAt!.y);
    await page.waitForTimeout(150);
    assert.equal(page.url(), before, "location.href is unchanged after clicking the form's text");
    assert.equal(await page.evaluate(() => location.href), before);

    // 3. the submit backstop itself: a REAL form put into the note after render (the sanitizer never lets one through, so this
    //    is the only way to exercise the listener) submits nowhere, and the event reaches the document defaultPrevented
    const submit = await page.evaluate(() => new Promise<{ prevented: boolean | null; href: string }>((resolve) => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const form = document.createElement("form"); form.action = "https://example.invalid/go"; form.className = "fx-real-form";
      const btn = document.createElement("button"); btn.type = "submit"; btn.textContent = "Submit"; form.appendChild(btn);
      md.insertBefore(form, md.firstChild);
      let prevented: boolean | null = null;
      document.addEventListener("submit", (ev) => { prevented = ev.defaultPrevented; }, { once: true });
      btn.click();
      setTimeout(() => { form.remove(); resolve({ prevented, href: location.href }); }, 100);
    }));
    assert.equal(submit.prevented, true, "the body's submit listener called preventDefault before the event reached the document");
    assert.equal(submit.href, before);
    assert.equal(page.url(), before, "a real submit navigated nowhere");

    // 4. containment: an element wearing one of the page's fixed classes stays inside the note and scrolls with it; even an
    //    injected fixed box with inset: 0 (a style no author can write past the hook) covers the note, never the close button
    const contained = await page.evaluate(() => {
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
      const close = document.querySelector("#romp-fileview .fileview-close") as HTMLElement;
      const rect = (e: Element) => { const b = e.getBoundingClientRect(); return { left: b.left, top: b.top, right: b.right, bottom: b.bottom, width: b.width, height: b.height }; };
      const centre = (r: { left: number; top: number; width: number; height: number }): [number, number] => [r.left + r.width / 2, r.top + r.height / 2];
      const hitClose = () => { const c = centre(rect(close)); const e = document.elementFromPoint(c[0], c[1]); return e === close ? "close" : (e ? e.tagName + "." + e.className : "nothing"); };
      body.scrollTop = 0;
      const classed = md.querySelector(".fx-classed") as HTMLElement;
      const classedPosition = getComputedStyle(classed).position;
      const classedAt0 = rect(classed), mdAt0 = rect(md);
      // inside a paragraph, not a direct child: `.fileview-md > :where(:not(table))` caps a direct child at the prose measure
      const inject = document.createElement("div"); inject.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:red;"; (md.querySelector("p") as HTMLElement).appendChild(inject);
      const injectAt0 = rect(inject);
      const hitAt0 = hitClose();
      body.scrollTop = 300;
      const scrolled = body.scrollTop;
      const hitScrolled = hitClose();
      const classedScrolled = rect(classed);
      inject.remove();
      body.scrollTop = 0;
      return { mdContain: getComputedStyle(md).contain, classedPosition, classedAt0, mdAt0, injectAt0, hitAt0, scrolled, hitScrolled, classedScrolled, closeRect: rect(close) };
    });
    assert.equal(contained.mdContain, "layout", ".fileview-md is layout-contained under the real sheet");
    assert.equal(contained.classedPosition, "fixed", "precondition: the fixture class (.cite-preview) still gives position: fixed in styles.css; pick another class if not");
    assert.ok(contained.classedAt0.top >= contained.mdAt0.top - 1 && contained.classedAt0.bottom <= contained.mdAt0.bottom + 1
              && contained.classedAt0.left >= contained.mdAt0.left - 1 && contained.classedAt0.right <= contained.mdAt0.right + 1,
      "the fixed-class element is laid out inside the note's box: " + JSON.stringify([contained.classedAt0, contained.mdAt0]));
    assert.ok(contained.scrolled >= 299, "the body scrolled: " + contained.scrolled);
    near(contained.classedAt0.top - contained.classedScrolled.top, contained.scrolled, "the fixed-class element moved WITH the note when the body scrolled (its containing block is the note, not the viewport)");
    for (const k of ["left", "top", "right", "bottom"] as const) near(contained.injectAt0[k], contained.mdAt0[k], "an injected inset:0 fixed box spans exactly the note's box (" + k + ")");
    assert.equal(contained.hitAt0, "close", "elementFromPoint at the close button's centre is the close button, with a full-inset fixed box in the note");
    assert.equal(contained.hitScrolled, "close", "…and still after the body scrolled under it (the box is clipped by the body's overflow)");

    // 5. the body still scrolls to the end of a long note: layout containment does not eat vertical overflow
    const scroll = await page.evaluate(() => {
      const body = document.querySelector("#romp-fileview .fileview-body") as HTMLElement;
      const md = document.querySelector("#romp-fileview .fileview-md") as HTMLElement;
      const last = Array.from(md.querySelectorAll("p")).pop() as HTMLElement;
      body.scrollTop = body.scrollHeight;
      const b = body.getBoundingClientRect(), l = last.getBoundingClientRect();
      return { scrollable: body.scrollHeight > body.clientHeight + 50, atEnd: body.scrollTop + body.clientHeight >= body.scrollHeight - 1,
               lastVisible: l.bottom <= b.bottom + 1 && l.top >= b.top - 1, lastText: last.textContent, tableScroll: getComputedStyle(md.querySelector("table") as HTMLElement).overflowX };
    });
    assert.ok(scroll.scrollable, "the fixture is longer than the body");
    assert.ok(scroll.atEnd, "the body scrolled to its end");
    assert.ok(scroll.lastVisible, "the last paragraph is in view at the end");
    assert.equal(scroll.lastText, "Last line.");
    assert.equal(scroll.tableScroll, "auto", "a table keeps its own horizontal scroll under containment");

    // 6. over the whole leg, from the page's own events: the document navigated once (its load) and no request left its host
    assert.deepEqual(seen.navigations, [before], "the Files document navigated exactly once, at its load");
    assert.deepEqual(seen.foreignRequests, [], "no request left romp.test (a submitted form would have asked example.invalid)");
    assert.deepEqual(errors, [], "no page errors");
  });
});
