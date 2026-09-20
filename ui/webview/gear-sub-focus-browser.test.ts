// The per-setting description opens on FOCUS as it opens on hover (2026-09-20; review round 3 of the wsBytesByHost field,
// ui-1: the share switch's description under Debug > Diagnostics, the consent text for the phone's timing rows with the
// per-machine socket-byte sentence round 1 of that review ruled in, rendered for a pointer alone, so a keyboard, a screen
// reader or a Chromium touch browser never saw it). Two pins over the sources for every runner, and a browser leg over the
// REAL gear module and its stylesheet, the gear-judge-fast-browser.test.ts pattern (a fake kernel behind page.route; skips
// with a stated reason without a playwright browser, which CI installs none of): the share row's checkbox is FOCUSED with
// the row parked at the card's bottom edge, and the description must be shown (display block) with the per-machine sentence
// in it and PLACED by placeSub (rs-up, since a popover below would run past the card's bottom, the T408 clip); parked at the
// card's top edge it shows below (no rs-up); a Tab into a Fast mode box shows ONE description in its row, the BOX's own,
// the row's standing down, as while the box is hovered (round 4's twins pass: until then the row's showed on that focus,
// and the box's, what Fast mode is and costs, reached a pointer alone); and with that row parked just above the card's
// bottom in a shorter window the BOX is what placeSub places (rs-up on the box, its description above the row: the box is
// static, so its popover's containing block is the row), the host rule the pointer road uses. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const GEAR = fs.readFileSync(path.join(UI, "gear.js"), "utf8");
const GEAR_CSS = fs.readFileSync(path.join(UI, "gear.css"), "utf8");

test("the sheet shows a description while its row holds the focus: :focus-within beside :hover on the show rule and the up rule, and the Fast mode box's nested description stands down while its row holds the focus as it does while the row is hovered", () => {
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:hover \.rs-sub, #rsettings \.rs-row:focus-within \.rs-sub, #rsettings \.rs-widget:hover \.rs-sub, #rsettings \.rs-widget:focus-within \.rs-sub \{ display: block; position: absolute;/m,
    "the show rule: the row's and the widget's hover selectors each with a focus-within twin");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row\.rs-up:focus-within \.rs-sub, #rsettings \.rs-widget\.rs-up:focus-within \.rs-sub \{ top: auto; bottom: 100%; margin-top: 0; margin-bottom: 2px; \}/m,
    "the up rule's focus twin, the same declarations as the hover rule beside it");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:focus-within \.rs-fastin \.rs-sub \{ display: none; \}/m,
    "the Fast mode box's description stands down while its row holds the focus (the :hover rule's twin), or a Tab into the box stacks two");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:has\(\.rs-fastin:focus-within\) > \.rs-sub \{ display: none; \}\n#rsettings \.rs-row:has\(\.rs-fastin:focus-within\) \.rs-fastin \.rs-sub \{ display: block; \}/m,
    "the box's hover pair's focus twins: while the focus is inside the box the row's description stands down and the box's own shows, so a keyboard reads on the box what a pointer reads on it");
  assert.match(GEAR_CSS, /^#rsettings \.rs-row:focus-within \.rs-fastin\.rs-up \.rs-sub \{ top: auto; bottom: 100%; margin-top: 0; margin-bottom: 2px; \}/m,
    "the box's up rule's focus twin: a box wearing rs-up opens its description above the row on the keyboard as on hover");
});

test("placeSub runs on focusin as on mouseover, on the pointer road's host (the box for a focus inside a Fast mode box), and the class goes with the focus as with the pointer", () => {
  assert.match(GEAR, /pcard\.addEventListener\('focusin', function \(e\) \{ var host = hostOf\(e\.target\); if \(host\) placeSub\(host\); \}\);/,
    "the selector shows the popover; only placeSub measures and flips it above a row near the card's bottom; the host is hostOf's, as on mouseover");
  assert.match(GEAR, /pcard\.addEventListener\('focusout', function \(e\) \{ var host = hostOf\(e\.target\); if \(host && !\(e\.relatedTarget && host\.contains\(e\.relatedTarget\)\)\) host\.classList\.remove\('rs-up'\); \}\);/,
    "the mouseout twin: the next focus measures afresh");
  assert.doesNotMatch(GEAR, /focusHostOf/,
    "no climb from a Fast mode box to its row on the focus road: the sheet shows the box's own description on that focus (its hover pair's focus twins), so the box is the host on both roads and its popover has a height to place");
});

const ENTRY = `
const { initGear } = require("./gear.js");
(window as any).__posts = [];
initGear((m: any) => { (window as any).__posts.push(m); });
`;

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: ENTRY, resolveDir: UI, loader: "ts", sourcefile: "gear-sub-focus-entry.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

const PAGE_HTML = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${GEAR_CSS}</style></head><body>
<script src=/dist/gear.js></script></body></html>`;
const MODELS = { models: [{ value: "opus", label: "Opus", versions: [] }, { value: "sonnet", label: "Sonnet", versions: [] }], efforts: [{ value: "", label: "Default" }] };
const VERSION = { judgeModel: "opus", judgeEffort: "", indexModel: "opus", indexEffort: "", distillModel: "triage", distillEffort: "triage",
  judgeConcurrency: "", commentModel: "session", commentEffort: "session", commentFast: "session",
  judgeFast: "on", distillFast: "on", indexFast: "on", fastRefused: {}, autoNudge: true, settingsGt: {}, updateMode: "off" };

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function withGear(t: any, tab: string, body: (page: any, errors: string[]) => Promise<void>, height = 320): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this machine; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    // a short window: the card (max-height 88vh) is shorter than the Debug pane, so the card scrolls, and the share row sits
    // low enough in it at scrollTop 0 that a popover below would run past the card (the T408 clip placeSub exists for) and
    // high enough at the card's end that one fits (the rig asserts both readings before it reads placeSub's answer)
    const page = await browser.newPage({ viewport: { width: 1000, height } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      const json = (o: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(o) });
      if (u.hostname !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/gear") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE_HTML });
      if (u.pathname === "/dist/gear.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/models") return json(MODELS);
      if (u.pathname === "/version") return json(VERSION);
      if (u.pathname === "/tunnels") return json({ tunnels: [] });
      return json({});
    });
    await page.goto("http://romp.test/gear");
    await page.waitForFunction(() => Array.isArray((window as any).__posts) && !!document.getElementById("rs-perfshare"), null, { timeout: 10000 });
    await page.evaluate((tb: string) => { window.postMessage({ romp: "openSettings", tab: tb }, "*"); }, tab);
    await page.waitForFunction(() => !(document.getElementById("rsettings") as HTMLElement).hidden, null, { timeout: 10000 });
    await body(page, errors);
  } finally {
    await browser.close();
  }
}

/** Scroll the card (the modal's scroll box) so the row that owns `id` sits as LOW as the card allows ("bottom": scrollTop 0),
 *  as HIGH as it allows ("top": the card's end), or just above the card's bottom edge wherever the row is in the card ("low":
 *  the scroll that puts the row's bottom 4 px above the card's), focus the control without a scroll (so the geometry the focus
 *  met is the one read), and read what the sheet and placeSub did. The HOST is gear.js's hostOf rule (the closest of a Fast
 *  mode box, a row or a widget row), so `own` is the box's description for a control inside a box and the row's otherwise,
 *  and `up` is the class on that host. The short window makes the positions differ in whether a popover below the row fits
 *  inside the card (fitsBelow), which is the one thing placeSub decides on. */
const focusParked = (page: any, id: string, edge: "bottom" | "top" | "low") => page.evaluate(([cid, where]: [string, string]) => {
  const box = document.getElementById(cid) as HTMLInputElement;
  const row = box.closest("#rsettings .rs-row") as HTMLElement;
  const card = document.querySelector("#rsettings .rs-card") as HTMLElement;
  const host = box.closest("#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget") as HTMLElement;
  (document.activeElement as HTMLElement | null)?.blur?.();
  row.classList.remove("rs-up"); host.classList.remove("rs-up");
  card.scrollTop = where === "top" ? card.scrollHeight : 0;
  if (where === "low") {
    const rr0 = row.getBoundingClientRect(), cr0 = card.getBoundingClientRect();
    card.scrollTop = Math.max(0, (rr0.top - cr0.top) - (cr0.height - rr0.height - 4));
  }
  box.focus({ preventScroll: true });
  const subs = Array.from(row.querySelectorAll(".rs-sub")) as HTMLElement[];
  const hostOfSub = (el: HTMLElement) => el.closest("#rsettings .rs-fastin, #rsettings .rs-row, #rsettings .rs-widget");
  const own = subs.find((el) => hostOfSub(el) === host)!;
  const rowOwn = subs.find((el) => hostOfSub(el) === row)!;
  const sr = own.getBoundingClientRect(), cr = card.getBoundingClientRect(), rr = row.getBoundingClientRect();
  return {
    geom: { row: [rr.top, rr.bottom], card: [cr.top, cr.bottom], sub: [sr.top, sr.bottom, sr.height], scroll: [card.scrollTop, card.scrollHeight, card.clientHeight] },
    focused: document.activeElement === box,
    hostIsBox: host !== row && host.classList.contains("rs-fastin"),
    display: getComputedStyle(own).display,
    rowDisplay: getComputedStyle(rowOwn).display,
    text: own.textContent || "",
    up: host.classList.contains("rs-up"),
    rowUp: row.classList.contains("rs-up"),
    shownInRow: subs.filter((el) => getComputedStyle(el).display !== "none").length,
    // the popover's own bottom against the card's, as placeSub measured it: above the row when rs-up placed it, else below
    subBelowRow: sr.top >= rr.bottom - 1, subAboveRow: sr.bottom <= rr.top + 1,
    fitsBelow: rr.bottom + sr.height + 2 <= cr.bottom,
  };
}, [id, edge]);

test("the share switch's description opens on focus and is placed: at the card's bottom edge it opens above the row (rs-up), at the top edge below it, and it carries the per-machine sentence", { timeout: 90000 }, async (t) => {
  await withGear(t, "debug", async (page, errors) => {
    const low = await focusParked(page, "rs-perfshare", "bottom");
    assert.equal(low.focused, true, "the checkbox took the focus");
    assert.equal(low.display, "block", "the description is shown while the row holds the focus (it rendered for a pointer alone before)");
    assert.match(low.text, /once per attached machine, by position rather than by name/, "the per-machine socket-byte sentence is in the shown text");
    assert.match(low.text, /Numbers and fixed names only, never text\./);
    assert.equal(low.fitsBelow, false, "the rig: with the row as low as the card allows, a popover below it would run past the card " + JSON.stringify(low.geom));
    assert.equal(low.up, true, "placeSub ran on the focus and flipped it above (the selector alone would leave it clipped below)");
    assert.equal(low.subAboveRow, true, "and the sheet placed it above the row");
    // the class goes with the focus: blur, and the next focus measures afresh
    await page.evaluate(() => (document.activeElement as HTMLElement).blur());
    assert.equal(await page.evaluate(() => (document.getElementById("rs-perfshare") as HTMLElement).closest(".rs-row")!.classList.contains("rs-up")), false, "focusout drops the class");
    const high = await focusParked(page, "rs-perfshare", "top");
    assert.equal(high.display, "block");
    assert.equal(high.fitsBelow, true, "the rig: with the row as high as the card allows, a popover below it fits " + JSON.stringify(high.geom));
    assert.equal(high.up, false, "so placeSub leaves the default");
    assert.equal(high.subBelowRow, true, "and it shows below the row");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("a Tab into a Fast mode box shows one description in its row, the BOX's own, the row's standing down, as a hover on the box does", { timeout: 90000 }, async (t) => {
  await withGear(t, "tasks", async (page, errors) => {
    await page.waitForFunction(() => (document.getElementById("rs-judgefast") as HTMLInputElement).checked === true, null, { timeout: 10000 });
    const r = await focusParked(page, "rs-judgefast", "top");
    assert.equal(r.focused, true);
    assert.equal(r.hostIsBox, true, "the rig: the host of a focus inside the box is the box (hostOf's rule)");
    assert.equal(r.shownInRow, 1, "one description shown in the row while the box holds the focus");
    assert.equal(r.display, "block", "the box's own: what a pointer reads on the box, a keyboard reads on its checkbox");
    assert.match(r.text, /fast mode \(an Opus-only research preview/, "and it is the Fast mode text, not the row's");
    assert.equal(r.rowDisplay, "none", "the row's stands down, as it does while the box is hovered");
    assert.equal(await page.evaluate(() => getComputedStyle(document.getElementById("rs-judgefast-sub")!).display), "block");
    assert.deepEqual(errors, [], "no page error");
  });
});

test("a Tab into a Fast mode box with its row just above the card's bottom places the BOX's description above the row: placeSub runs on the box, the host whose popover the sheet shows, and the box's up rule's focus twin opens it above", { timeout: 90000 }, async (t) => {
  await withGear(t, "tasks", async (page, errors) => {
    await page.waitForFunction(() => (document.getElementById("rs-judgefast") as HTMLInputElement).checked === true, null, { timeout: 10000 });
    const r = await focusParked(page, "rs-judgefast", "low");
    assert.equal(r.focused, true, "the box's checkbox took the focus");
    assert.equal(r.hostIsBox, true, "the rig: the host is the box");
    assert.equal(r.fitsBelow, false, "the rig: with the row just above the card's bottom in a 260 px window, a popover below it would run past the card " + JSON.stringify(r.geom));
    assert.equal(r.shownInRow, 1, "one description shown in the row, the box's");
    assert.equal(r.display, "block", "the box's own is the shown one");
    assert.equal(r.up, true, "the BOX wears rs-up: placeSub measured the box's popover, the one the sheet shows on this focus (a climb to the row would measure the row's, hidden, and place nothing)");
    assert.equal(r.rowUp, false, "and the row was not placed: the focus road's host is the pointer road's");
    assert.equal(r.subAboveRow, true, "and the sheet opened the box's description above the row (the box's up rule's focus twin; the box is static, so the row is its containing block)");
    await page.evaluate(() => (document.activeElement as HTMLElement).blur());
    assert.equal(await page.evaluate(() => (document.getElementById("rs-judgefast") as HTMLElement).closest(".rs-fastin")!.classList.contains("rs-up")), false, "focusout drops the class from the box");
    assert.deepEqual(errors, [], "no page error");
  }, 260);
});
