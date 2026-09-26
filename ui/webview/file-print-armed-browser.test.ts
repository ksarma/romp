// The armed line under a repaint, and under the controls that own their Escape (file-print.ts; the print follow-on to
// plans/markdown-viewer.md's Slice 3, item 12), for what the second review of the follow-on found (2026-09-19):
// (A) a body repainted under the armed line (the changed-on-disk bar's Reload landing, a Rendered or Raw pick) is counted
//     again: the line's words and the with-button's title follow the new body in place (the same row, so the keyboard
//     stays where it is), and "Print with them" loads the hosts the title names, never a host the title never named; a body
//     with no placeholder disarms, and the next press prints. Before this the line and the title stood as the press left
//     them while the click read the hosts from the new body, so a Reload that brought a placeholder on a new host had the
//     click fetch from a host the person was never shown; and (the review's consolidation) a placeholder the person
//     activates by hand under the armed line, by its click or by Enter on it, is counted again the same way: the line and
//     the title follow the one just loaded, and the last one gone disarms;
// (B) Escape while the bar is armed is left to a control that owns it: the text-size flyout (a role=group under a trigger
//     with aria-haspopup, whose dismiss is a document listener that stopPropagation does not keep from the flow's listener
//     on the same node) closes on one Escape with the bar still armed, from the trigger and from inside the menu; the
//     Comments composer's Escape cancels the draft with the bar still armed; the next Escape disarms; and a pending
//     re-place of a region comment (the panel's own capture listener on the document, registered at the open ahead of the
//     flow's per-open one) is cancelled by one Escape with the bar still armed, the next Escape disarming (the round-2
//     review's tests-6, landed 2026-09-20: before this the outcome was held by a source-text census alone);
// (C) only a placeholder that reaches the paper is counted, named and loaded (the third review, 2026-09-19): five gated
//     pictures on five hosts, one in the open body, one in a typed <details> that is closed, one in a folded callout
//     (`> [!note]-`, md-config.ts: a closed details), one under a `hidden` attribute and one under `style="display:none"`,
//     which the sanitizer strips (md-sanitize.ts colorOnlyStyle keeps colour declarations alone), so that picture prints.
//     The armed line counts two, the title names their two hosts, a fold opened under the armed line is counted again
//     (the details' toggle event) and closed again is not, "Print with them" asks exactly those two hosts, the three hosts
//     whose pictures never reach the paper are never asked, and the PDF Chromium prints holds exactly two pictures.
//     Before this every placeholder in the body was counted and every host it named was asked, so "with them" fetched
//     from three hosts for pictures that were not on the paper.
// (D) the printable rule's UNKNOWN side, a census (the round-2 review, 2026-09-19): the walk knows two hidings, a closed
//     <details> and the `hidden` attribute, and before this answered printable for every other, so a placeholder the
//     browser never renders (inside a ruby's <rp>, a <canvas>'s fallback content, a `popover` not shown, all kept by the
//     sanitizer) or one whose figure it never renders (an <img hidden> inside the placeholder, an svg with display none,
//     visibility hidden or opacity 0) was counted, named and, on "Print with them", fetched for a print that never shows
//     it. Now the walk's answer is joined by the browser's own (checkVisibility and a client rect) on the placeholder, and
//     by the figure half (figurePrintable: `hidden` and `popover` on an HTML element, the author's own display, and the
//     visibility and opacity the browser computes, over every element of the figure that paints; the round-3 review,
//     2026-09-20, before which the opacity was matched against one spelling of zero and the first element child alone
//     was read), so the unknown side falls to NOT printable. The census renders one gated picture per wrapper over every
//     tag of DOMPurify's html profile the sanitizer keeps (the void elements aside), the svg containers inside an svg,
//     the kept attributes that hide (`popover`, `inert`, `hidden` in both spellings, `open`, an svg's `display`,
//     `visibility` and `opacity`, the spellings of zero among them), a picture whose img is hidden and an svg whose
//     image is, and beside EVERY gated figure an ungated TWIN of the same markup at a local URL, the browser's own answer
//     for the shape (checkVisibility and a client rect over the twin's painting elements). It presses Print, reads which
//     hosts the title names, and holds that a host is named exactly when the browser renders its placeholder AND paints
//     its twin, that the shapes named below are not named, and that "Print with them" then asks exactly the named hosts.
//     Each shape's row is printed as a diagnostic.
// Under node first: the machine's `recount` event, the ownership predicate over stand-ins, and the printable predicate over
// stand-in trees. Then headless Chromium over the real viewer through real-viewer-leg.ts, the way
// file-print-driver-browser.test.ts drives it. Skips loudly without a browser. Synthetic values only: an invented note,
// /repo/notes-api paths, invented hosts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as zlib from "node:zlib";
import { hideEdges } from "../test-dom-shim";
import { inBrowser, openViewer, openPanel, frames, REPORT, ORIGIN, MT2, type Mode } from "./real-viewer-leg";
import { step, RESTING, DISABLED, ownsEscape, printable, OWN_ESCAPE_SEL, OPEN_POPUP_SEL, WITHOUT_TITLE, PAINTS_SEL, type PrintState, type PrintableNode } from "./file-print";
import { MD_FORBID_TAGS } from "./md-sanitize";

const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
const QUICK = "fig.svg";                       // a local picture the route answers at once
const HOST_A = "other.test";                   // not in the gear's default list, not the page's origin: a placeholder
const HOST_B = "another.test";
const REMOTE_HOSTS = [HOST_A, HOST_B];
const ONE_A = "# Figures\n\nA local picture ![](" + QUICK + ") and a remote one ![](https://" + HOST_A + "/o.svg).\n\nLast line.\n";
const ONE_B = "# Figures\n\nA local picture ![](" + QUICK + ") and a remote one ![](https://" + HOST_B + "/b.svg).\n\nA session swapped the figure.\n";
const TWO = "# Two placeholders\n\nOne ![](https://" + HOST_A + "/o.svg) and two ![](https://" + HOST_B + "/a.svg).\n\nLast line.\n";
const PLAIN = "# Plain\n\nOne local picture ![](" + QUICK + ") and text.\n\nLast line.\n";
// (C): five hosts, one gated picture each, and where each stands in the body
const HOST_OPEN = "open.test", HOST_TYPED = "typed.test", HOST_CALLOUT = "callout.test", HOST_HIDDEN = "hidden.test", HOST_STYLED = "styled.test";
const FIVE_HOSTS = [HOST_OPEN, HOST_TYPED, HOST_CALLOUT, HOST_HIDDEN, HOST_STYLED];
const FIVE = "# Five\n\nOpen ![](https://" + HOST_OPEN + "/o.png)\n\n"
  + "<details><summary>Typed fold</summary><img src=\"https://" + HOST_TYPED + "/t.png\" alt=\"\"></details>\n\n"
  + "> [!note]- Folded callout\n> ![](https://" + HOST_CALLOUT + "/c.png)\n\n"
  + "<div hidden><img src=\"https://" + HOST_HIDDEN + "/h.png\" alt=\"\"></div>\n\n"
  + "<div style=\"display:none\"><img src=\"https://" + HOST_STYLED + "/s.png\" alt=\"\"></div>\n\nLast line.\n";
/** A w by h PNG of one solid colour: a raster, which Chromium's PDF names as an image object (an svg prints as paths and is
 *  not countable there); one colour per host, so the PDF does not fold two pictures into one object. */
function png(w: number, h: number, rgb: [number, number, number]): Buffer {
  const chunk = (type: string, data: Buffer): Buffer => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const body = Buffer.concat([Buffer.from(type, "ascii"), data]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(zlib.crc32(body));
    return Buffer.concat([len, body, crc]);
  };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;   // 8-bit RGB, no alpha (an alpha channel would add a soft-mask image object per picture)
  const row = Buffer.concat([Buffer.from([0]), Buffer.from(Array.from({ length: w }, () => rgb).flat())]);
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(Buffer.concat(Array.from({ length: h }, () => row)))), chunk("IEND", Buffer.alloc(0))]);
}
/** The pictures a PDF holds: its image objects (the media leg counts pages the same way). */
const picturesOf = (pdf: Buffer): number => (pdf.toString("latin1").match(/\/Subtype\s*\/Image\b/g) || []).length;

type Bar = { phase: string | null; line: string | null; buttons: string[]; titles: string[]; cardUp: boolean; lines: number; probe: boolean };
/** The page's record of the print stub's calls, and the bar as it stands (`probe`: the line carries the mark a leg set on it
 *  before a repaint, so a line rewritten in place can be told from one rebuilt). */
const PAGE_PROBES = () => {
  const w = window as any;
  w.__prints = [];
  w.print = () => { w.__prints.push({ gates: document.querySelectorAll('[data-act="fv-load"]').length, incomplete: (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).filter((i) => !i.complete).length }); };
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const line = document.getElementById("fileview-print-line");
    const btns = line ? Array.from(line.querySelectorAll("button")) : [];
    return { phase: b ? (b.dataset.print || null) : null, line: line ? (line.firstChild && line.firstChild.nodeType === 3 ? (line.firstChild.textContent || "") : line.textContent) : null,
      buttons: btns.map((x) => x.textContent || ""), titles: btns.map((x) => x.title), cardUp: !!document.getElementById("romp-fileview"),
      lines: document.querySelectorAll("#romp-fileview .fileview-print-line").length, probe: !!line && line.getAttribute("data-probe") === "1" };
  };
};
const bar = (page: any): Promise<Bar> => page.evaluate(() => (window as any).__bar());
const prints = (page: any): Promise<Array<{ gates: number; incomplete: number }>> => page.evaluate(() => (window as any).__prints);
const printsReach = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => (window as any).__prints.length >= k, n, { timeout: 10000 });
const markLine = (page: any): Promise<void> => page.evaluate(() => { document.getElementById("fileview-print-line")!.setAttribute("data-probe", "1"); });
const waitGates = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => document.querySelectorAll('[data-act="fv-load"]').length === k, n, { timeout: 10000 });
const active = (page: any): Promise<string> => page.evaluate(() => { const a = document.activeElement; return a ? a.tagName + "." + String(a.className || "").split(" ").filter((c) => c && c !== "romp-acted" && c !== "on").join(".") : "null"; });   // the tag and the classes, the click's press pulse and the trigger's open mark aside
const PRINT_BTN = "#romp-fileview .fileview-print";
const WITH_BTN = '#fileview-print-line button:has-text("Print with them")';
const ZOOM_BTN = "#romp-fileview .fileview-zoom-btn";
const hostsAsked = (requests: string[]): string[] => Array.from(new Set(requests.filter((u) => !u.startsWith(ORIGIN)).map((u) => new URL(u).host))).sort();

type Scene = { page: any; errors: string[]; requests: string[] };
/** The viewer over `note` in `mode`: the quick picture answered from the origin's route, every remote host answered after a
 *  short delay (the two svg hosts, and the five PNG hosts of (C), each with a colour of its own), every request recorded,
 *  the probes installed before the open. */
async function scene(browser: any, mode: Mode, note: string): Promise<Scene> {
  const requests: string[] = [];
  const { page, errors } = await openViewer(browser, mode, 900, 700, {
    docs: { [REPORT]: note },
    serve: (u) => { const p = u.searchParams.get("path") || ""; return u.pathname === "/file" && p.endsWith(QUICK) ? { status: 200, type: "image/svg+xml", body: SVG } : null; },
    before: async (pg: any) => {
      pg.on("request", (r: any) => { requests.push(r.url()); });
      for (const h of REMOTE_HOSTS) await pg.route("https://" + h + "/**", async (route: any) => { await new Promise((r) => setTimeout(r, 100)); await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); });
      FIVE_HOSTS.forEach((h, i) => { void pg.route("https://" + h + "/**", async (route: any) => { await new Promise((r) => setTimeout(r, 100)); await route.fulfill({ status: 200, contentType: "image/png", body: png(16, 16, [40 * i, 255 - 40 * i, 90]) }); }); });
      await pg.evaluate(PAGE_PROBES);
    },
  });
  await frames(page, 2);
  return { page, errors, requests };
}
/** Change the file on disk and raise the changed-on-disk bar through the viewer's own probe (a window focus runs one HEAD, whose
 *  moved mtime raises the bar), then click its Reload: the landing repaints the body under whatever the print flow holds. */
async function reloadTo(page: any, note: string): Promise<void> {
  await page.evaluate(([p, n, mt]: [string, string, string]) => { const w = window as any; w.__docs[p] = n; w.__mtime = mt; }, [REPORT, note, MT2]);
  await page.evaluate(() => { window.dispatchEvent(new Event("focus")); });
  await page.waitForFunction(() => { const b = document.querySelector("#fileview-save-err button") as HTMLButtonElement | null; return !!b && b.textContent === "Reload"; }, null, { timeout: 10000 });
  await page.click("#fileview-save-err button");
  await page.waitForFunction(() => !document.getElementById("fileview-save-err"), null, { timeout: 10000 });   // the landing took the bar
  await frames(page, 2);
}

// ── under node: the machine and the predicate ──────────────────────────────────────────────────────

test("recount while armed arms again over the new count and disarms over none; the body's own arrival holds the line; a recount in any other phase changes nothing", () => {
  const armed = step(RESTING, { kind: "press", gated: 1, pending: 0 }).state;
  assert.equal(step(armed, { kind: "body", in: true }).act, "none", "the body's arrival by itself moves nothing: the driver's recount carries the new count");
  const more = step(armed, { kind: "recount", gated: 2 });
  assert.equal(more.act, "arm", "a repaint that brought a second placeholder: armed again, the driver rewriting the line");
  assert.deepEqual(more.state, { phase: "armed", gated: 2, pending: 0 });
  const same = step(armed, { kind: "recount", gated: 1 });
  assert.equal(same.act, "arm", "the same count is armed again too: the hosts may differ, and the driver re-reads them");
  assert.deepEqual(same.state, armed);
  const none = step(armed, { kind: "recount", gated: 0 });
  assert.equal(none.act, "disarm", "no placeholder left: the question is moot and the line goes");
  assert.equal(none.state.phase, "resting");
  assert.equal(step(none.state, { kind: "press", gated: 0, pending: 0 }).act, "print", "the next press prints");
  const preparing: PrintState = { phase: "preparing", gated: 0, pending: 2 };
  const printing: PrintState = { phase: "printing", gated: 0, pending: 0 };
  for (const [s, name] of [[RESTING, "rest"], [DISABLED, "disabled"], [preparing, "the wait"], [printing, "the print"]] as const) {
    const r = step(s, { kind: "recount", gated: 3 });
    assert.equal(r.act, "none", "a recount during " + name + " changes nothing");
    assert.equal(r.state, s);
  }
});

test("ownsEscape: the keyboard inside a menu or a dialog; an open popup's trigger anywhere in the scope, whatever the target; not an aria-expanded alone (the Print button's own), not a scope with none", () => {
  assert.equal(OPEN_POPUP_SEL, '[aria-haspopup][aria-expanded="true"]');
  const inMenu = { closest: (sel: string) => (sel === OWN_ESCAPE_SEL ? {} : null) } as unknown as Element;
  const outside = { closest: () => null } as unknown as Element;
  const withPopup = { querySelector: (sel: string) => (sel === OPEN_POPUP_SEL ? {} : null) } as unknown as ParentNode;
  const without = { querySelector: () => null } as unknown as ParentNode;
  assert.equal(ownsEscape(inMenu), true, "inside a menu, no scope asked");
  assert.equal(ownsEscape(inMenu, without), true);
  assert.equal(ownsEscape(outside), false);
  assert.equal(ownsEscape(outside, without), false, "a scope with no open popup: the Escape is the bar's");
  assert.equal(ownsEscape(outside, withPopup), true, "an open popup in the scope owns the Escape whatever the target");
  assert.equal(ownsEscape(null, withPopup), true, "…even from the document's body");
  assert.equal(ownsEscape(null), false);
  assert.equal(ownsEscape(null, null), false);
  assert.ok(!OPEN_POPUP_SEL.startsWith('[aria-expanded'), "the trigger is known by aria-haspopup: the Print button wears aria-expanded alone while armed and must not match");
});

/** A stand-in node: its name, its attributes and its parent. */
const node = (localName: string, attrs: string[] = [], parent: PrintableNode | null = null): PrintableNode => hideEdges({ localName, parentElement: parent, hasAttribute: (n) => attrs.includes(n) });   // hideEdges: the stand-in's parent edge is non-enumerable, as the shared module's rule asks of every fake node (ui/test-dom-shim.test.ts's ratchet)

test("printable: a placeholder reaches the paper unless a closed details holds it outside its own summary, or an ancestor (or it) carries hidden, whatever its value", () => {
  const body = node("div");
  assert.equal(printable(node("span", [], node("p", [], body))), true, "in the open body");
  const closed = node("details", [], body);
  assert.equal(printable(node("span", [], node("p", [], closed))), false, "under a closed details: the fold's content is not rendered");
  assert.equal(printable(node("span", [], node("summary", [], closed))), true, "inside the closed details' own summary, which is shown while the fold is closed");
  assert.equal(printable(node("span", [], node("em", [], node("summary", [], closed)))), true, "…however deep in the summary");
  const open = node("details", ["open"], body);
  assert.equal(printable(node("span", [], node("p", [], open))), true, "under an open details");
  assert.equal(printable(node("span", [], node("p", [], node("details", [], open)))), false, "a closed details inside an open one folds what it holds");
  assert.equal(printable(node("span", [], node("p", [], node("details", ["open"], closed)))), false, "an open details inside a closed one is folded with it");
  assert.equal(printable(node("span", [], node("div", ["hidden"], body))), false, "under a hidden attribute");
  assert.equal(printable(node("span", [], node("div", ["hidden"], open))), false, "hidden inside an open details");
  assert.equal(printable(node("span", ["hidden"], body)), false, "hidden on the element itself");
  assert.equal(printable(node("span", [], node("section", ["hidden"], node("div", [], body)))), false, "hidden two levels up (hidden=until-found among its values: the browser skips the content until a find or a fragment reveals it)");
  assert.equal(printable(node("span", [], null)), true, "a detached node walks to nothing and counts as printable: the caller reads the body, whose nodes are attached");
});

// ── (A) a repaint under the armed line ─────────────────────────────────────────────────────────────

test("(A) a Reload landing under the armed line is counted again: the same line reads the new count and the title names the new hosts, and Print with them loads those hosts; a landing on a new host alone names it alone and the old host is never asked; a landing with no placeholder disarms and the next press prints", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a: one placeholder on A, then two on A and B
    let s = await scene(browser, "pane", ONE_A);
    let { page } = s;
    await waitGates(page, 1);
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.line, "1 picture from another host is not loaded.");
    assert.deepEqual(b.titles, ["Load the pictures from " + HOST_A + ", then print", WITHOUT_TITLE]);
    await markLine(page);
    await reloadTo(page, TWO);
    await waitGates(page, 2);
    b = await bar(page);
    assert.equal(b.phase, "armed", "still armed over the new body"); assert.equal(b.lines, 1, "one line");
    assert.equal(b.probe, true, "the same row: the words were rewritten in place, not the line rebuilt");
    assert.equal(b.line, "2 pictures from other hosts are not loaded.", "the count follows the repainted body");
    assert.deepEqual(b.buttons, ["Print with them", "Print without them"]);
    assert.deepEqual(b.titles, ["Load the pictures from " + HOST_A + " and " + HOST_B + ", then print", WITHOUT_TITLE], "the title names both hosts the click would grant");
    assert.deepEqual(hostsAsked(s.requests), [], "nothing fetched from either host before the choice");
    await page.click(WITH_BTN);
    await printsReach(page, 1);
    let p = await prints(page);
    assert.equal(p.length, 1); assert.equal(p[0].gates, 0); assert.equal(p[0].incomplete, 0);
    assert.deepEqual(hostsAsked(s.requests), [HOST_A, HOST_B].sort(), "the two hosts the title named were asked, as a click on each placeholder asks");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // b: one placeholder on A, then one on B: the same count, another host
    s = await scene(browser, "pane", ONE_A);
    page = s.page;
    await waitGates(page, 1);
    await page.click(PRINT_BTN);
    assert.deepEqual((await bar(page)).titles, ["Load the pictures from " + HOST_A + ", then print", WITHOUT_TITLE]);
    await reloadTo(page, ONE_B);
    await page.waitForFunction((h: string) => { const gate = document.querySelector('[data-act="fv-load"]'); return !!gate && (gate.getAttribute("data-fv-hosts") || "") === h; }, HOST_B, { timeout: 10000 });
    b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.line, "1 picture from another host is not loaded.", "the count is the same");
    assert.deepEqual(b.titles, ["Load the pictures from " + HOST_B + ", then print", WITHOUT_TITLE], "the title names the new host alone");
    await page.click(WITH_BTN);
    await printsReach(page, 1);
    p = await prints(page);
    assert.equal(p.length, 1); assert.equal(p[0].gates, 0);
    assert.deepEqual(hostsAsked(s.requests), [HOST_B], "the new host was asked and the old one, no longer in the body or the title, was not");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // c: one placeholder, then none: disarmed; the next press prints at once with no request to the host
    s = await scene(browser, "pane", ONE_A);
    page = s.page;
    await waitGates(page, 1);
    await page.click(PRINT_BTN);
    assert.equal((await bar(page)).phase, "armed");
    await reloadTo(page, PLAIN);
    await waitGates(page, 0);
    await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview img")).every((i: any) => i.complete), null, { timeout: 10000 });
    b = await bar(page);
    assert.equal(b.phase, null, "no placeholder in the new body: the line went"); assert.equal(b.line, null); assert.equal(b.cardUp, true);
    assert.equal((await prints(page)).length, 0, "nothing printed by the landing itself");
    await page.click(PRINT_BTN);
    p = await prints(page);
    assert.equal(p.length, 1, "the next press prints at once"); assert.equal(p[0].gates, 0); assert.equal(p[0].incomplete, 0);
    assert.deepEqual(hostsAsked(s.requests), [], "no request reached the host");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

test("(A) a Raw pick under the armed line disarms (the rows hold no placeholder); Rendered again re-arms nothing until the next press", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "chat", ONE_A);
    const { page } = s;
    await waitGates(page, 1);
    await page.click(PRINT_BTN);
    assert.equal((await bar(page)).phase, "armed");
    await page.click('#romp-fileview .fileview-seg button:has-text("Raw")');
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fv-cl") && document.querySelectorAll('[data-act="fv-load"]').length === 0, null, { timeout: 10000 });
    let b = await bar(page);
    assert.equal(b.phase, null, "the Raw view holds no placeholder: the line went"); assert.equal(b.line, null); assert.equal(b.cardUp, true);
    await page.click('#romp-fileview .fileview-seg button:has-text("Rendered")');
    await waitGates(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "back in Rendered the placeholder is there again, and nothing arms without a press"); assert.equal(b.line, null);
    await page.click(PRINT_BTN);
    b = await bar(page);
    assert.equal(b.phase, "armed", "a press arms over it"); assert.equal(b.line, "1 picture from another host is not loaded.");
    assert.deepEqual(b.titles, ["Load the pictures from " + HOST_A + ", then print", WITHOUT_TITLE]);
    await page.keyboard.press("Escape");
    assert.equal((await bar(page)).phase, null);
    assert.equal((await prints(page)).length, 0);
    assert.deepEqual(hostsAsked(s.requests), [], "no request reached the host");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

test("(A) a placeholder the person activates by hand under the armed line is counted again: the same line reads the count left and the title names the host left, the clicked host asked as its click asks it; Enter on the last one disarms, and the next press prints at once", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["pane", "chat"] as Mode[]) {
      const s = await scene(browser, mode, TWO);
      const { page } = s;
      await waitGates(page, 2);
      await page.click(PRINT_BTN);
      let b = await bar(page);
      assert.equal(b.phase, "armed", mode + ": armed over the two placeholders"); assert.equal(b.line, "2 pictures from other hosts are not loaded.");
      assert.deepEqual(b.titles, ["Load the pictures from " + HOST_A + " and " + HOST_B + ", then print", WITHOUT_TITLE]);
      await markLine(page);
      // by the mouse: the first placeholder, on A
      await page.click('#romp-fileview [data-act="fv-load"]');
      await waitGates(page, 1);
      b = await bar(page);
      assert.equal(b.phase, "armed", mode + ": still armed over the one left"); assert.equal(b.lines, 1);
      assert.equal(b.probe, true, mode + ": the same row, its words rewritten in place");
      assert.equal(b.line, "1 picture from another host is not loaded.", mode + ": the count follows the placeholder the click loaded (FAILS BEFORE: the count stood at 2 until a repaint)");
      assert.deepEqual(b.titles, ["Load the pictures from " + HOST_B + ", then print", WITHOUT_TITLE], mode + ": the title names the host left alone");
      assert.deepEqual(hostsAsked(s.requests), [HOST_A], mode + ": the clicked host was asked, as its click asks it, and no other");
      assert.equal((await prints(page)).length, 0, mode + ": nothing printed by the click");
      // by the keyboard: Enter on the last one, on B
      await page.focus('#romp-fileview [data-act="fv-load"]');
      await page.keyboard.press("Enter");
      await waitGates(page, 0);
      b = await bar(page);
      assert.equal(b.phase, null, mode + ": no placeholder left: the line went"); assert.equal(b.line, null); assert.equal(b.cardUp, true, mode + ": the card stays up");
      assert.deepEqual(hostsAsked(s.requests), [HOST_A, HOST_B].sort(), mode + ": the second host was asked by the key");
      assert.equal((await prints(page)).length, 0, mode + ": nothing printed by the activations");
      await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview img")).every((i: any) => i.complete), null, { timeout: 10000 });
      await page.click(PRINT_BTN);
      const p = await prints(page);
      assert.equal(p.length, 1, mode + ": the next press prints at once"); assert.equal(p[0].gates, 0); assert.equal(p[0].incomplete, 0);
      assert.deepEqual(s.errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

// ── (C) placeholders that never reach the paper ────────────────────────────────────────────────────

test("(C) five gated pictures on five hosts: only the two that reach the paper are counted and named; a fold opened under the armed line is counted again and closed again is not; Print with them asks exactly their hosts (FAILS BEFORE: all five hosts were asked), the folded and hidden hosts are never asked, and the PDF holds exactly the two pictures", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", FIVE);
    const { page } = s;
    await waitGates(page, 5);
    const placed = await page.evaluate(() => Array.from(document.querySelectorAll('#romp-fileview [data-act="fv-load"]')).map((g) => {
      const d = g.closest("details"); return (g.getAttribute("data-fv-hosts") || "") + ":" + (g.closest("[hidden]") ? "hidden" : d ? (d.hasAttribute("open") ? "open-details" : "closed-details") : "body") + ":" + ((g.closest("[style]") as HTMLElement | null)?.getAttribute("style") || "-");
    }));
    assert.deepEqual(placed, [HOST_OPEN + ":body:-", HOST_TYPED + ":closed-details:-", HOST_CALLOUT + ":closed-details:-", HOST_HIDDEN + ":hidden:-", HOST_STYLED + ":body:-"],
      "five placeholders: the open one, two in closed details (the typed fold and the folded callout), one under hidden, and one whose display:none the sanitizer stripped (no style attribute survives)");
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "armed");
    assert.equal(b.line, "2 pictures from other hosts are not loaded.", "FAILS BEFORE: the line counted all five placeholders; two reach the paper");
    assert.deepEqual(b.titles, ["Load the pictures from " + HOST_OPEN + " and " + HOST_STYLED + ", then print", WITHOUT_TITLE], "the title names the two hosts whose pictures print, in the order the body names them");
    assert.deepEqual(hostsAsked(s.requests), [], "nothing fetched from any host before the choice");
    // the typed fold opened under the armed line: its placeholder reaches the paper now, so it is counted and its host named; closed again, it is not
    await markLine(page);
    await page.click("#romp-fileview .fileview-md details:not(.md-callout) > summary");
    await page.waitForFunction(() => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === "3 pictures from other hosts are not loaded.", null, { timeout: 5000 });
    b = await bar(page);
    assert.equal(b.probe, true, "the same row, its words rewritten in place");
    assert.deepEqual(b.titles, ["Load the pictures from " + HOST_OPEN + ", " + HOST_TYPED + " and " + HOST_STYLED + ", then print", WITHOUT_TITLE], "the opened fold's host joins the title, in the body's order");
    await page.click("#romp-fileview .fileview-md details:not(.md-callout) > summary");
    await page.waitForFunction(() => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === "2 pictures from other hosts are not loaded.", null, { timeout: 5000 });
    b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.lines, 1);
    assert.deepEqual(b.titles, ["Load the pictures from " + HOST_OPEN + " and " + HOST_STYLED + ", then print", WITHOUT_TITLE], "closed again, the fold's host leaves the title");
    assert.deepEqual(hostsAsked(s.requests), [], "the fold's toggling fetched nothing");
    // with them: the two hosts, and no other
    await page.click(WITH_BTN);
    await printsReach(page, 1);
    const p = await prints(page);
    assert.equal(p.length, 1); assert.equal(p[0].incomplete, 0, "window.print fired with every <img> complete");
    assert.equal(p[0].gates, 3, "the three placeholders that never reach the paper still stand: their hosts were not loaded");
    assert.deepEqual(hostsAsked(s.requests), [HOST_OPEN, HOST_STYLED].sort(), "FAILS BEFORE: all five hosts were asked; exactly the two hosts the title named are");
    await frames(page, 6);
    assert.deepEqual(hostsAsked(s.requests), [HOST_OPEN, HOST_STYLED].sort(), "…and nothing reached the folded or hidden hosts afterwards either");
    assert.equal(picturesOf(await page.pdf({ format: "A4" })), 2, "the PDF holds exactly the two pictures that reach the paper: the open one and the one whose display:none was stripped");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (D) the printable rule's unknown side: a census over the sanitizer's kept tags and hiding attributes ───────────────

/** DOMPurify's html profile (its `html` tag list, dompurify 3.x) less the void elements, which hold no picture. The sanitizer's
 *  own forbid list (MD_FORBID_TAGS) is taken off below, so the census renders the tags a note keeps; a tag the sanitizer drops
 *  anyway leaves its picture in the open body, which the row records by the wrapper the placeholder ends up in. */
const HTML_TAGS = ["a", "abbr", "acronym", "address", "article", "aside", "audio", "b", "bdi", "bdo", "big", "blink", "blockquote", "button", "canvas", "caption", "center", "cite", "code", "colgroup", "content", "data", "datalist", "dd", "decorator", "del", "details", "dfn", "dialog", "dir", "div", "dl", "dt", "element", "em", "fieldset", "figcaption", "figure", "font", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "i", "ins", "kbd", "label", "legend", "li", "main", "mark", "marquee", "menu", "meter", "nav", "nobr", "ol", "optgroup", "option", "output", "p", "picture", "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp", "search", "section", "select", "shadow", "slot", "small", "spacer", "span", "strike", "strong", "sub", "summary", "sup", "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead", "time", "tr", "tt", "u", "ul", "var", "video"];
/** The svg containers of DOMPurify's svg profile that can hold an <image>, each wrapped in an svg of its own. */
const SVG_TAGS = ["a", "clipPath", "defs", "desc", "filter", "g", "linearGradient", "marker", "mask", "metadata", "pattern", "radialGradient", "switch", "symbol", "text", "textPath", "title", "tspan", "view"];
type Shape = { name: string; block: (host: string) => string };
/** The gated picture of a shape and, beside it, its ungated twin: the same markup at the local picture's URL, inside a span
 *  the sanitizer keeps by class (`twin`), so the browser's own answer for the shape stands next to the flow's. A wrapper tag
 *  is put around the twin as around the gated picture (`wrap`), outside the placeholder: a wrapper that is itself a media
 *  root (audio, video, picture) would otherwise take the twin into the placeholder, where the sheet hides it. */
const twinned = (figure: (url: string) => string, wrap: (inner: string) => string = (x) => x) => (h: string): string => wrap(figure("https://" + h + "/p.svg")) + '<span class="twin">' + wrap(figure(QUICK)) + "</span>";
const IMG = (url: string): string => '<img src="' + url + '" alt="">';
const SVG_IMAGE = (attrs: string, inner: (url: string) => string = (u) => '<image href="' + u + '" width="8" height="8"/>') => (url: string): string => '<svg xmlns="http://www.w3.org/2000/svg" ' + attrs + ' width="8" height="8">' + inner(url) + "</svg>";
/** Every shape the census renders: a wrapper tag around a gated <img>, the kept hiding attributes on a wrapper or on the picture
 *  itself, an svg with each kept attribute that hides it (the spellings of zero the round-3 review named among them), and the
 *  structures whose painting element is not the figure's root; each with its twin. */
function censusShapes(): Shape[] {
  const out: Shape[] = [];
  for (const tag of HTML_TAGS) if (!MD_FORBID_TAGS.includes(tag)) out.push({ name: "tag:" + tag, block: twinned(IMG, (x) => "<" + tag + ">" + x + "</" + tag + ">") });
  for (const tag of SVG_TAGS) out.push({ name: "svg:" + tag, block: twinned(SVG_IMAGE("", (u) => "<" + tag + '><image href="' + u + '" width="8" height="8"/></' + tag + ">")) });
  const attr = (name: string, open: string): Shape => ({ name, block: (h) => "<div " + open + ">" + twinned(IMG)(h) + "</div>" });
  out.push(attr("attr:popover", "popover"), attr("attr:inert", "inert"), attr("attr:hidden", "hidden"), attr("attr:hidden-until-found", "hidden=\"until-found\""));
  out.push({ name: "attr:details-closed", block: (h) => "<details><summary>s</summary>" + twinned(IMG)(h) + "</details>" });
  out.push({ name: "attr:details-open", block: (h) => "<details open><summary>s</summary>" + twinned(IMG)(h) + "</details>" });
  out.push({ name: "img:hidden", block: twinned((u) => '<img hidden src="' + u + '" alt="">') });
  out.push({ name: "img:hidden-until-found", block: twinned((u) => '<img hidden="until-found" src="' + u + '" alt="">') });
  out.push({ name: "img:plain", block: twinned(IMG) });
  out.push({ name: "picture:img-hidden", block: twinned((u) => '<picture><img hidden src="' + u + '" alt=""></picture>') });
  out.push({ name: "picture:img-plain", block: twinned((u) => '<picture><img src="' + u + '" alt=""></picture>') });
  for (const [name, a] of [["svg:display-none", 'display="none"'], ["svg:display-NONE", 'display="NONE"'], ["svg:visibility-hidden", 'visibility="hidden"'], ["svg:opacity-0", 'opacity="0"'],
    ["svg:opacity--0", 'opacity="-0"'], ["svg:opacity-+0", 'opacity="+0"'], ["svg:opacity-0e0", 'opacity="0e0"'], ["svg:opacity-0pct", 'opacity="0%"'], ["svg:opacity-spaced-0", 'opacity=" 0 "'],
    ["svg:opacity-0.0.0", 'opacity="0.0.0"'], ["svg:opacity-1e-9", 'opacity="1e-9"'], ["svg:opacity-50pct", 'opacity="50%"'], ["svg:hidden", "hidden"], ["svg:plain", ""]]) {
    out.push({ name, block: twinned(SVG_IMAGE(a)) });
  }
  out.push({ name: "svg:image-display-none", block: twinned(SVG_IMAGE("", (u) => '<image href="' + u + '" display="none" width="8" height="8"/>')) });
  out.push({ name: "svg:image-opacity-0", block: twinned(SVG_IMAGE("", (u) => '<image href="' + u + '" opacity="0" width="8" height="8"/>')) });
  return out;
}
/** The shapes the browser renders no placeholder or paints no figure for: not counted, not named, never asked by Print with
 *  them. FAILS BEFORE the round-2 review for those the walk did not know: rp, canvas, popover (the placeholder has no box),
 *  img:hidden and img:hidden-until-found (the picture inside the placeholder carries hidden), and the three svg attributes;
 *  FAILS BEFORE the round-3 review for the spellings of zero (-0, +0, 0e0, 0%, a spaced 0), the hidden picture inside a
 *  <picture>, an svg image inside a container that never renders (defs, symbol, clipPath, mask, pattern, marker, a gradient,
 *  a filter, metadata; an svg title or desc is an HTML integration point of the parser, whose <image> becomes an HTML <img
 *  href> that fetches nothing, so no placeholder stands there and neither is listed) and an svg image with display none or
 *  opacity 0 of its own. */
const NOT_ON_PAPER = ["tag:rp", "tag:canvas", "attr:popover", "attr:hidden", "attr:hidden-until-found", "attr:details-closed", "img:hidden", "img:hidden-until-found", "svg:display-none", "svg:display-NONE", "svg:visibility-hidden", "svg:opacity-0",
  "svg:opacity--0", "svg:opacity-+0", "svg:opacity-0e0", "svg:opacity-0pct", "svg:opacity-spaced-0", "picture:img-hidden", "svg:image-display-none", "svg:image-opacity-0",
  "svg:defs", "svg:symbol", "svg:clipPath", "svg:mask", "svg:pattern", "svg:marker", "svg:linearGradient", "svg:radialGradient", "svg:filter", "svg:metadata"];
/** The shapes whose figure the browser paints though an attribute on it might read as hiding: named, and asked by Print with
 *  them. FAILS BEFORE the round-3 review: 0.0.0, which the browser refuses and paints at 1, read as hidden, and <svg hidden>,
 *  which the browser paints (hidden is HTML's attribute), read as hidden too. */
const ON_PAPER_DESPITE = ["svg:opacity-0.0.0", "svg:opacity-1e-9", "svg:opacity-50pct", "svg:hidden", "picture:img-plain"];
/** The hosts the with-button's title names, read back from its words. */
function titleHosts(title: string): string[] {
  const m = /^Load the pictures from (.*), then print$/.exec(title);
  if (!m) return [];
  if (m[1] === "those hosts") return [];
  return m[1].split(/, | and /).filter(Boolean);
}
type Row = { name: string; host: string; placeholders: number; wrapper: string; rendered: boolean | null; figure: string; twinPaints: boolean | null; askedAtRender: number };
/** The attributes the census lists for each figure, for the diagnostic line: what the figure carries, beside what the browser
 *  says of its twin. */
const FIGURE_ATTRS = ["hidden", "popover", "display", "visibility", "opacity"];

test("(D) the census of the printable rule's unknown side: over every kept tag of the sanitizer's profile, every kept attribute that hides and the spellings of zero, Print's title names a host exactly when the browser renders its placeholder AND paints an ungated twin of its figure; a placeholder inside a ruby's rp, a canvas's fallback content or a popover, an <img hidden> inside its placeholder or inside a <picture>, an svg with display none, visibility hidden or opacity 0 in any spelling, and an svg image inside defs or with display none or opacity 0 of its own are not named (FAILS BEFORE: the walk alone named the first three, the round-2 pattern named -0, +0, 0e0, 0%, the hidden img inside a picture and the image inside defs); 0.0.0, 1e-9 and <svg hidden>, which the browser paints, are named (FAILS BEFORE: read as hidden); and Print with them asks exactly the named hosts", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const shapes = censusShapes();
    const hostOf = (i: number): string => "c" + i + "-" + shapes[i].name.replace(/[^a-z0-9]+/gi, "-").toLowerCase() + ".test";
    const note = "# Census\n\n" + shapes.map((s, i) => s.block(hostOf(i))).join("\n\n") + "\n\nLast line.\n";
    const requests: string[] = [];
    const { page, errors } = await openViewer(browser, "pane", 900, 700, {
      docs: { [REPORT]: note },
      serve: (u) => { const p = u.searchParams.get("path") || ""; return u.pathname === "/file" && p.endsWith(QUICK) ? { status: 200, type: "image/svg+xml", body: SVG } : null; },   // the twins' picture
      before: async (pg: any) => {
        pg.on("request", (r: any) => { requests.push(r.url()); });
        await pg.route((u: URL) => u.origin !== ORIGIN && u.hostname.endsWith(".test"), async (route: any) => { await new Promise((r) => setTimeout(r, 60)); await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); });
        await pg.evaluate(PAGE_PROBES);
      },
    });
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-md") && (document.querySelector("#romp-fileview .fileview-md")!.textContent || "").includes("Last line."), null, { timeout: 15000 });
    await frames(page, 3);
    await page.evaluate(() => Promise.all(Array.from(document.querySelectorAll("#romp-fileview .twin img")).map((i) => (i as HTMLImageElement).complete ? null : new Promise<void>((r) => { i.addEventListener("load", () => r()); i.addEventListener("error", () => r()); }))));   // every twin's picture settled, so each has its box
    await frames(page, 2);
    const hostsBefore = hostsAsked(requests);
    const askedAtRender = (h: string): number => requests.filter((u) => u.startsWith("https://" + h + "/")).length;
    // every placeholder's host, wrapper, the browser's own rendering of it, what its figure carries, and whether the browser paints the twin beside it
    const seen: Array<{ host: string; wrapper: string; rendered: boolean; figure: string; twinPaints: boolean | null }> = await page.evaluate(([attrs, paintsSel]: [string[], string]) => {
      const renders = (e: Element): boolean => (e as any).checkVisibility({ visibilityProperty: true, opacityProperty: true }) && e.getClientRects().length > 0;
      const paintsEl = (e: Element): boolean => renders(e) && (getComputedStyle(e) as any).contentVisibility !== "hidden";   // content-visibility hidden (hidden=until-found on the element itself) keeps its box and paints nothing of its content
      const carries = (e: Element | null): string => e === null ? "-" : attrs.filter((k) => e.hasAttribute(k)).map((k) => k + "=" + e.getAttribute(k)).join(",");
      // the twin span follows the placeholder or the wrapper around it, after any sibling the parser moved between them (a table's
      // picture is foster-parented before the table, so the table stands between); a following placeholder is the next shape's
      const twinOf = (g: Element): Element | null => { for (let n: Element | null = g; n; n = n.parentElement) { for (let t = n.nextElementSibling; t; t = t.nextElementSibling) { if (t.classList.contains("twin")) return t; if (t.matches('[data-act="fv-load"]') || t.querySelector('[data-act="fv-load"]')) return null; } } return null; };
      const paints = (twin: Element | null): boolean | null => { if (!twin) return null; const els = Array.from(twin.querySelectorAll(paintsSel)); return els.length > 0 && els.some(paintsEl); };
      return Array.from(document.querySelectorAll('#romp-fileview .fileview-md [data-act="fv-load"]')).map((g) => ({ host: g.getAttribute("data-fv-hosts") || "", wrapper: g.parentElement ? g.parentElement.localName : "-", rendered: renders(g), figure: carries(g.firstElementChild), twinPaints: paints(twinOf(g)) }));
    }, [FIGURE_ATTRS, PAINTS_SEL]);
    const byHost = new Map<string, typeof seen>();
    for (const s of seen) byHost.set(s.host, [...(byHost.get(s.host) || []), s]);
    await page.click(PRINT_BTN);
    const b = await bar(page);
    assert.equal(b.phase, "armed", "the press armed over the census's placeholders");
    const named = titleHosts(b.titles[0]);
    assert.ok(named.length > 50, "the title names the rendered placeholders' hosts (" + named.length + ")");
    const rows: Row[] = shapes.map((s, i) => { const h = hostOf(i); const g = byHost.get(h) || []; return { name: s.name, host: h, placeholders: g.length, wrapper: g.map((x) => x.wrapper).join("+") || "-", rendered: g.length ? g.every((x) => x.rendered) : null, figure: g.map((x) => x.figure).join("+"), twinPaints: g.length ? g.every((x) => x.twinPaints === true) : null, askedAtRender: askedAtRender(h) }; });
    for (const r of rows) t.diagnostic("census | " + r.name + " | placeholders=" + r.placeholders + " | wrapper=" + r.wrapper + " | rendered=" + r.rendered + " | figure=" + (r.figure || "-") + " | twin paints=" + r.twinPaints + " | counted=" + named.includes(r.host) + " | askedAtRender=" + r.askedAtRender);
    // (a) a host is named exactly when the browser renders its placeholder and paints the twin of its figure: the browser's answer on both halves
    const misjudged = rows.filter((r) => r.placeholders > 0 && named.includes(r.host) !== (r.rendered === true && r.twinPaints === true)).map((r) => r.name + (r.figure ? "[" + r.figure + "]" : "") + ": named " + named.includes(r.host) + ", placeholder rendered " + r.rendered + ", twin paints " + r.twinPaints);
    assert.deepEqual(misjudged, [], "FAILS BEFORE: a host named for a placeholder the browser does not render or a figure it paints nothing of (the zero spellings, the hidden img inside a picture, the image inside defs), or a host not named for a figure it paints (0.0.0, the hidden svg)");
    // (b) the shapes that never reach the paper are not named
    const namedOffPaper = rows.filter((r) => NOT_ON_PAPER.includes(r.name) && named.includes(r.host)).map((r) => r.name);
    assert.deepEqual(namedOffPaper, [], "FAILS BEFORE: rp, canvas, popover, the hidden picture inside its placeholder, the hidden svgs, the zero spellings, the hidden img inside a picture and the images inside containers that never render were named");
    for (const name of NOT_ON_PAPER) assert.equal(rows.find((r) => r.name === name)!.placeholders, 1, name + " renders one placeholder (the shape is in the census, gated)");
    for (const name of NOT_ON_PAPER) assert.equal(rows.find((r) => r.name === name)!.twinPaints, false, name + ": the browser paints nothing of the twin (the answer the flow must give)");
    // (c) the shapes in the open body are named: a plain picture, an open details, an inert wrapper, the tags that render inline or as blocks, and the figures the browser paints though an attribute on them might read as hiding
    for (const name of ["img:plain", "attr:details-open", "attr:inert", "svg:plain", "tag:div", "tag:p", "tag:span", "tag:marquee", "tag:table", "tag:rt", "tag:summary", "tag:figure", ...ON_PAPER_DESPITE]) assert.ok(named.includes(rows.find((r) => r.name === name)!.host), name + " is named");
    for (const name of ON_PAPER_DESPITE) assert.equal(rows.find((r) => r.name === name)!.twinPaints, true, name + ": the browser paints the twin (FAILS BEFORE: the flow read the figure as hidden)");
    // (d) a template's picture is inert content the DOM never reaches: no placeholder, nothing asked at the render
    const tpl = rows.find((r) => r.name === "tag:template")!;
    assert.equal(tpl.placeholders, 0, "no placeholder inside a template"); assert.equal(tpl.askedAtRender, 0, "and nothing fetched");
    // (e) Print with them asks exactly the named hosts, once each, and none of the others
    const mark = requests.length;
    await page.click(WITH_BTN);
    await printsReach(page, 1);
    await frames(page, 6);
    await new Promise((r) => setTimeout(r, 300));
    const asked = requests.slice(mark).filter((u) => !u.startsWith(ORIGIN)).map((u) => new URL(u).host);
    assert.deepEqual(Array.from(new Set(asked)).sort(), named.slice().sort(), "FAILS BEFORE: the hosts asked by Print with them are exactly the hosts the title named");
    for (const h of named) assert.equal(asked.filter((x) => x === h).length, 1, h + " asked once");
    for (const name of NOT_ON_PAPER) assert.equal(asked.includes(rows.find((r) => r.name === name)!.host), false, name + "'s host never asked");
    const p = await prints(page);
    assert.equal(p.length, 1, "one print");
    t.diagnostic("census | named " + named.length + " of " + seen.length + " placeholders over " + shapes.length + " shapes; hosts asked at the render (the gate's own, before any press): " + (hostsBefore.length ? hostsBefore.join(" ") : "none"));
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── (B) the controls that own their Escape ─────────────────────────────────────────────────────────

test("(B) Escape with the text-size flyout open while the bar is armed closes the flyout alone, from the trigger and from inside the menu, the bar still armed; the next Escape disarms and the card stays up", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["chat", "pane"] as Mode[]) {
      const s = await scene(browser, mode, ONE_A);
      const { page } = s;
      await waitGates(page, 1);
      const flyout = (): Promise<{ open: boolean; expanded: string | null }> => page.evaluate(() => { const m = document.querySelector("#romp-fileview .fileview-zoom-menu") as HTMLElement | null; const tr = document.querySelector("#romp-fileview .fileview-zoom-btn"); return { open: !!m && !m.hidden, expanded: tr ? tr.getAttribute("aria-expanded") : null }; });
      await page.click(PRINT_BTN);
      assert.equal((await bar(page)).phase, "armed", mode + ": armed over the placeholder");
      // from the trigger: the click leaves the keyboard on the glyph, outside the menu
      await page.click(ZOOM_BTN);
      assert.deepEqual(await flyout(), { open: true, expanded: "true" }, mode + ": the flyout is open");
      assert.equal(await active(page), "BUTTON.fileview-btn.fileview-icon.fileview-zoom-btn", mode + ": the keyboard is on the trigger");
      await page.keyboard.press("Escape");
      await frames(page, 1);
      assert.deepEqual(await flyout(), { open: false, expanded: "false" }, mode + ": one Escape closed the flyout");
      let b = await bar(page);
      assert.equal(b.phase, "armed", mode + ": …and the bar is still armed"); assert.equal(b.line, "1 picture from another host is not loaded."); assert.equal(b.cardUp, true);
      // from inside the menu
      await page.click(ZOOM_BTN);
      await page.focus("#romp-fileview .fileview-zoom-menu button");
      assert.deepEqual(await flyout(), { open: true, expanded: "true" });
      assert.ok((await active(page)).startsWith("BUTTON.fileview-btn") && !(await active(page)).includes("zoom-btn"), mode + ": the keyboard is on a size button inside the menu: " + await active(page));
      await page.keyboard.press("Escape");
      await frames(page, 1);
      assert.deepEqual(await flyout(), { open: false, expanded: "false" }, mode + ": Escape from inside the menu closed the flyout");
      assert.equal(await active(page), "BUTTON.fileview-btn.fileview-icon.fileview-zoom-btn", mode + ": the keyboard went back to the glyph, the flyout's own rule");
      b = await bar(page);
      assert.equal(b.phase, "armed", mode + ": the bar is still armed"); assert.equal(b.lines, 1);
      // the next Escape is the bar's
      await page.keyboard.press("Escape");
      await frames(page, 1);
      b = await bar(page);
      assert.equal(b.phase, null, mode + ": the next Escape disarmed"); assert.equal(b.line, null); assert.equal(b.cardUp, true, mode + ": …and the card stays up");
      assert.equal((await prints(page)).length, 0);
      assert.deepEqual(hostsAsked(s.requests), [], mode + ": no request reached the host");
      assert.deepEqual(s.errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

test("(B) Escape in the Comments composer while the bar is armed cancels the draft, the composer's own rule, the bar still armed; the next Escape disarms; at rest the composer's Escape is untouched", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", ONE_A);
    const { page } = s;
    await waitGates(page, 1);
    await openPanel(page);
    const composer = (): Promise<{ open: boolean; value: string; focused: boolean }> => page.evaluate(() => { const box = document.querySelector("#romp-fileview .fc-composer") as HTMLElement | null; const ta = box ? box.querySelector("textarea.fc-input") as HTMLTextAreaElement | null : null; return { open: !!box && !box.hidden, value: ta ? ta.value : "", focused: !!ta && document.activeElement === ta }; });
    const startDraft = async (): Promise<void> => {
      await page.click('#romp-fileview .fileview-aside [data-act="fcfile"]');
      await page.waitForFunction(() => { const box = document.querySelector("#romp-fileview .fc-composer") as HTMLElement | null; return !!box && !box.hidden && document.activeElement === box.querySelector("textarea.fc-input"); }, null, { timeout: 5000 });
      await page.keyboard.type("a draft");
      assert.deepEqual(await composer(), { open: true, value: "a draft", focused: true }, "the composer holds the draft and the keyboard");
    };
    // control, at rest: the composer's own Escape cancels the draft and the card stays up
    await startDraft();
    await page.keyboard.press("Escape");
    await frames(page, 1);
    assert.deepEqual(await composer(), { open: false, value: "", focused: false }, "at rest, Escape cancelled the draft");
    assert.equal((await bar(page)).cardUp, true, "the card stays up (the box stopped the Escape)");
    // armed, then the draft
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "armed", "armed over the placeholder");
    await startDraft();
    assert.equal((await bar(page)).phase, "armed", "opening the composer left the bar armed");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    assert.deepEqual(await composer(), { open: false, value: "", focused: false }, "one Escape cancelled the draft, the field's own rule");
    b = await bar(page);
    assert.equal(b.phase, "armed", "…and the bar is still armed"); assert.equal(b.line, "1 picture from another host is not loaded."); assert.equal(b.cardUp, true);
    assert.ok(!(await active(page)).startsWith("TEXTAREA"), "the keyboard left the field: " + await active(page));
    // the next Escape is the bar's
    await page.keyboard.press("Escape");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "the next Escape disarmed"); assert.equal(b.line, null); assert.equal(b.cardUp, true, "…and the card stays up");
    assert.equal((await prints(page)).length, 0);
    assert.deepEqual(hostsAsked(s.requests), [], "no request reached the host");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (B) a pending re-place of a region comment: the panel's Escape ahead of the flow's ─────────────

const BIG_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300"><rect width="600" height="300" fill="#336699"/></svg>';
const FIG_NOTE = "# Print me\n\n![Figure](" + QUICK + ")\n\nA paragraph after the figure.\n\nA remote one ![](https://" + HOST_A + "/o.svg).\n\nLast line.\n";
const T0 = 1757145600000;
const HASH = "1".repeat(64);
/** A region comment on the figure: its anchor the embed line, its target a region of the picture (the hash is not the
 *  picture's, so the rectangle is the dotted unknown one; a region all the same, and its card offers Re-place while the
 *  picture is in view under a fine pointer). Synthetic values. */
const REGION = { id: T0 + "-0", author: "you", ts: T0, body: "Crop this band.", replies: [], resolved: false,
  anchor: { quote: "![Figure](" + QUICK + ")", prefix: "# Print me\n\n", suffix: "\n\nA paragraph" }, target: { kind: "image", region: { x: 0.1, y: 0.2, w: 0.3, h: 0.5 }, hash: HASH, src: QUICK } };

test("(B) Escape during a pending re-place of a region comment while the bar is armed cancels the re-place alone: the panel's capture listener on the document, registered when the viewer's action walk mounted the panel at the open, ahead of the flow's per-open listener, stops the key, and the flow reads the stop and stands down, the bar still armed and nothing printed; the next Escape disarms and the card stays up. FAILS BEFORE under the lazy-panel mutation (the panel built at its first click, after installFilePrint): its listener then follows the flow's on the same node and phase, so one Escape reaches the flow first, which disarms and stops the event, and the panel's listener still runs (stopPropagation stops no listener on the same node), the re-place cancelling and the bar disarming together, which reds the still-armed assertion below; the source-text pin in tools/markdown-viewer-plan-print-record.test.mjs stays green under that mutation (round 3's refuter measured it 22/22)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const requests: string[] = [];
    const { page, errors } = await openViewer(browser, "pane", 900, 700, {
      docs: { [REPORT]: FIG_NOTE },
      serve: (u) => { const p = u.searchParams.get("path") || ""; return u.pathname === "/file" && p.endsWith(QUICK) ? { status: 200, type: "image/svg+xml", body: BIG_SVG } : null; },
      before: async (pg: any) => {
        pg.on("request", (r: any) => { requests.push(r.url()); });
        await pg.route("https://" + HOST_A + "/**", async (route: any) => { await new Promise((r) => setTimeout(r, 100)); await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); });
        await pg.evaluate(PAGE_PROBES);
        await pg.evaluate(([c, h]: [unknown, string]) => { const st = (window as any).__status; st.store.comments = [c]; st.unsent.comments = [(c as any).id]; st.fileHash = h; }, [REGION, HASH]);
      },
    });
    await waitGates(page, 1);
    await page.waitForFunction(() => { const i = document.querySelector("#romp-fileview .fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth === 600; }, null, { timeout: 10000 });
    await openPanel(page);
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-aside .fc-card"), null, { timeout: 10000 });
    // the card's Re-place control (the actions render in the open card: a click on the card opens it when it is not)
    const replaceBtn = '#romp-fileview .fileview-aside button[data-act="fcreplace"]';
    if (await page.evaluate((sel: string) => !document.querySelector(sel), replaceBtn)) await page.click('#romp-fileview .fileview-aside [data-act="fccard"]');
    await page.waitForFunction((sel: string) => !!document.querySelector(sel), replaceBtn, { timeout: 10000 });
    const replacing = (): Promise<{ composer: boolean; note: string; input: boolean }> => page.evaluate(() => {
      const box = document.querySelector("#romp-fileview .fc-composer") as HTMLElement | null;
      const ta = box ? box.querySelector("textarea.fc-input") as HTMLTextAreaElement | null : null;
      return { composer: !!box && !box.hidden && box.isConnected, note: box ? Array.from(box.querySelectorAll(".fc-note")).map((n) => n.textContent || "").join(" ") : "", input: !!ta && !ta.hidden };
    });
    // armed, then the re-place
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "armed", "armed over the placeholder"); assert.equal(b.line, "1 picture from another host is not loaded.");
    await page.click(replaceBtn);
    await frames(page, 2);
    let r = await replacing();
    assert.equal(r.composer, true, "the re-place composer stands"); assert.ok(r.note.includes("Drag the comment's new place on the image"), "asking for the drag: " + r.note); assert.equal(r.input, false, "a re-place takes a drag, not words: the input is hidden, so no text field holds the keyboard");
    assert.equal((await bar(page)).phase, "armed", "opening the re-place left the bar armed");
    await page.keyboard.press("Escape");
    await frames(page, 2);
    r = await replacing();
    assert.equal(r.composer, false, "one Escape cancelled the re-place (the panel's own capture listener)");
    b = await bar(page);
    assert.equal(b.phase, "armed", "FAILS BEFORE under the lazy-panel mutation: the bar is still armed after the first Escape"); assert.equal(b.line, "1 picture from another host is not loaded."); assert.equal(b.cardUp, true);
    assert.equal((await prints(page)).length, 0, "nothing printed");
    // the next Escape is the bar's
    await page.keyboard.press("Escape");
    await frames(page, 2);
    b = await bar(page);
    assert.equal(b.phase, null, "the next Escape disarmed"); assert.equal(b.line, null); assert.equal(b.cardUp, true, "the card stays up");
    assert.equal((await prints(page)).length, 0);
    assert.deepEqual(hostsAsked(requests), [], "no request reached the host");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
