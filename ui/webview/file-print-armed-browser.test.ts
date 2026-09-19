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
//     Comments composer's Escape cancels the draft with the bar still armed; the next Escape disarms.
// Under node first: the machine's `recount` event and the ownership predicate over stand-ins. Then headless Chromium over
// the real viewer through real-viewer-leg.ts, the way file-print-driver-browser.test.ts drives it. Skips loudly without a
// browser. Synthetic values only: an invented note, /repo/notes-api paths, invented hosts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, REPORT, ORIGIN, MT2, type Mode } from "./real-viewer-leg";
import { step, RESTING, DISABLED, ownsEscape, OWN_ESCAPE_SEL, OPEN_POPUP_SEL, WITHOUT_TITLE, type PrintState } from "./file-print";

const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
const QUICK = "fig.svg";                       // a local picture the route answers at once
const HOST_A = "other.test";                   // not in the gear's default list, not the page's origin: a placeholder
const HOST_B = "another.test";
const REMOTE_HOSTS = [HOST_A, HOST_B];
const ONE_A = "# Figures\n\nA local picture ![](" + QUICK + ") and a remote one ![](https://" + HOST_A + "/o.svg).\n\nLast line.\n";
const ONE_B = "# Figures\n\nA local picture ![](" + QUICK + ") and a remote one ![](https://" + HOST_B + "/b.svg).\n\nA session swapped the figure.\n";
const TWO = "# Two placeholders\n\nOne ![](https://" + HOST_A + "/o.svg) and two ![](https://" + HOST_B + "/a.svg).\n\nLast line.\n";
const PLAIN = "# Plain\n\nOne local picture ![](" + QUICK + ") and text.\n\nLast line.\n";

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
 *  short delay, every request recorded, the probes installed before the open. */
async function scene(browser: any, mode: Mode, note: string): Promise<Scene> {
  const requests: string[] = [];
  const { page, errors } = await openViewer(browser, mode, 900, 700, {
    docs: { [REPORT]: note },
    serve: (u) => { const p = u.searchParams.get("path") || ""; return u.pathname === "/file" && p.endsWith(QUICK) ? { status: 200, type: "image/svg+xml", body: SVG } : null; },
    before: async (pg: any) => {
      pg.on("request", (r: any) => { requests.push(r.url()); });
      for (const h of REMOTE_HOSTS) await pg.route("https://" + h + "/**", async (route: any) => { await new Promise((r) => setTimeout(r, 100)); await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); });
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
