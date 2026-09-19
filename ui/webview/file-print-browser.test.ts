// Print from the viewer with its pictures loaded (file-print.ts; the print follow-on to plans/markdown-viewer.md's Slice 3,
// item 12), over the real viewer in headless Chromium the way file-view-print-browser.test.ts drives the pane and the chat
// modal. Before this the sheets printed the open file, but nothing awaited its pictures: the browser's own Ctrl/Cmd+P ran
// with a gated figure's placeholder standing and a picture still loading, and printed both as they were. The contract's
// cases: (1) a note with a local picture the test's route answers, a local picture whose route is HELD (incomplete until
// the test releases it) and a picture on a host the gear's list does not name (a placeholder): the chord and the Print
// button arm with "1 picture from another host is not loaded." and the two word buttons; Escape and a second press disarm
// and leave the card up; "Print without them" leaves the placeholder and prints once the held picture lands; "Print with
// them" restores the placeholder (the host's request appears) and prints only after that picture settled; window.print,
// stubbed on the page to record the call, fires only with every <img> complete. (2) Ctrl+P with a file open runs the
// flow and the browser's raw print is prevented (a window keydown listener reads defaultPrevented after the viewer's
// capture-phase listener); with no file open, or with a text field focused, the key is untouched and nothing prints. (3)
// a note with no placeholder and its pictures complete prints on one click, in the click's own task, with no line shown;
// the Raw view (a code view, no pictures) the same. (4) the deadline: a picture whose route never answers prints after
// the deadline, shortened through the module's test seam (FV.setPrintSettleMs), with the picture still incomplete. (5) the
// URL kind: a document from a link with a picture on another host arms the same way. FAILS BEFORE: the first assertion
// of case 1, at the unchanged viewer (no button, no listener): the chord is not prevented while a placeholder stands and an
// <img> is incomplete, so the browser's raw print is what runs. Skips loudly without a browser. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, REPORT, ROOT, ORIGIN, type Mode } from "./real-viewer-leg";

const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
const QUICK = "fig.svg";                       // a local picture the route answers at once
const SLOW = "slow.svg";                       // a local picture whose route is held until the test releases it
const REMOTE_HOST = "other.test";              // not in the gear's default list, not the page's origin: a placeholder
const REMOTE = "https://" + REMOTE_HOST + "/o.svg";
const GATED_NOTE = "# Figures\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nA remote one ![](" + REMOTE + ").\n\nLast line.\n";
const PLAIN_NOTE = "# Plain\n\nOne local picture ![](" + QUICK + ") and text.\n\nLast line.\n";
const URL_DOC = "/notes/note.md";
const URL_NOTE = "# Linked\n\nA remote picture ![](" + REMOTE + ") alone.\n";

type Print = { t: number; gates: number; incomplete: number; line: boolean; remoteReady: boolean | null };
type Key = { key: string; ctrl: boolean; prevented: boolean; open: boolean; gates: number; incomplete: number };
type Bar = { present: boolean; text: string | null; title: string | null; on: boolean; busy: boolean; expanded: string | null; phase: string | null; line: string | null; buttons: string[]; cardUp: boolean };

/** The page's record of the print stub's calls, the window's keydowns, and the bar as it stands. */
const PAGE_PROBES = () => {
  const w = window as any;
  w.__prints = []; w.__keys = [];
  const imgs = () => Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
  const gates = () => document.querySelectorAll('[data-act="fv-load"]').length;
  w.print = () => {
    const remote = imgs().find((i) => i.src.indexOf("https://other.test/") === 0);
    w.__prints.push({ t: performance.now(), gates: gates(), incomplete: imgs().filter((i) => !i.complete).length, line: !!document.getElementById("fileview-print-line"), remoteReady: remote ? remote.complete && remote.naturalWidth > 0 : null });
  };
  window.addEventListener("keydown", (e) => { w.__keys.push({ key: e.key, ctrl: e.ctrlKey || e.metaKey, prevented: e.defaultPrevented, open: document.body.classList.contains("fileview-open"), gates: gates(), incomplete: imgs().filter((i) => !i.complete).length }); });
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const line = document.getElementById("fileview-print-line");
    return { present: !!b, text: b ? b.textContent : null, title: b ? b.title : null, on: !!b && b.classList.contains("on"), busy: !!b && b.classList.contains("fileview-busy"), expanded: b ? b.getAttribute("aria-expanded") : null, phase: b ? (b.dataset.print || null) : null,
      line: line ? (line.firstChild && line.firstChild.nodeType === 3 ? (line.firstChild.textContent || "") : line.textContent) : null, buttons: line ? Array.from(line.querySelectorAll("button")).map((x) => x.textContent || "") : [], cardUp: !!document.getElementById("romp-fileview") };
  };
};
const bar = (page: any): Promise<Bar> => page.evaluate(() => (window as any).__bar());
const prints = (page: any): Promise<Print[]> => page.evaluate(() => (window as any).__prints);
const keys = (page: any): Promise<Key[]> => page.evaluate(() => (window as any).__keys);
/** The chords among the window's keydowns: the P with Ctrl or Cmd held (the modifier's own keydown is recorded too). */
const chords = (page: any): Promise<Key[]> => keys(page).then((ks) => ks.filter((x) => x.key.toLowerCase() === "p" && x.ctrl));
const imgFacts = (page: any): Promise<{ total: number; incomplete: number; gates: number }> => page.evaluate(() => {
  const imgs = Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
  return { total: imgs.length, incomplete: imgs.filter((i) => !i.complete).length, gates: document.querySelectorAll('[data-act="fv-load"]').length };
});
const printsReach = (page: any, n: number, timeout = 10000): Promise<unknown> => page.waitForFunction((k: number) => (window as any).__prints.length >= k, n, { timeout });

type Scene = { page: any; errors: string[]; requests: string[]; release: () => Promise<void>; heldCount: () => number };
/** The viewer over `note`: the local pictures answered from the origin's route (the held one parked in `held` until
 *  release()), the remote host answered after `remoteDelayMs` so a print that waited can be told from one that did not,
 *  the probes installed before the open. `url` opens the URL viewer on URL_DOC instead. */
async function scene(browser: any, mode: Mode, note: string, opts: { raw?: boolean; url?: boolean; remoteDelayMs?: number } = {}): Promise<Scene> {
  const held: any[] = [];
  const requests: string[] = [];
  const { page, errors } = await openViewer(browser, mode, 900, 700, {
    docs: { [REPORT]: note }, raw: opts.raw,
    url: opts.url ? URL_DOC : undefined, urls: opts.url ? { [ORIGIN + URL_DOC]: note } : undefined,
    serve: (u) => { const p = u.searchParams.get("path") || ""; return u.pathname === "/file" && p.endsWith(QUICK) ? { status: 200, type: "image/svg+xml", body: SVG } : null; },
    before: async (pg: any) => {
      pg.on("request", (r: any) => { requests.push(r.url()); });
      await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/file" && (u.searchParams.get("path") || "").endsWith(SLOW), (route: any) => { held.push(route); });   // parked: the <img> stays incomplete
      await pg.route("https://" + REMOTE_HOST + "/**", async (route: any) => { await new Promise((r) => setTimeout(r, opts.remoteDelayMs ?? 400)); await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); });
      await pg.evaluate(PAGE_PROBES);
    },
  });
  await frames(page, 2);
  return { page, errors, requests, heldCount: () => held.length, release: async () => { for (const r of held.splice(0)) await r.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); } };
}
const SLOW_PATH = ROOT + "/docs/" + SLOW;
/** Wait until the note's placeholder stands, its quick picture is complete and its slow picture's request is parked. */
async function gatedSettled(s: Scene): Promise<void> {
  await s.page.waitForFunction(() => {
    const imgs = Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
    return document.querySelectorAll('[data-act="fv-load"]').length === 1 && imgs.some((i) => i.complete && i.naturalWidth > 0);
  }, null, { timeout: 10000 });
  for (let i = 0; i < 50 && s.heldCount() === 0; i++) await frames(s.page, 1);   // the parked request: the layout's frames, until the browser has asked for the slow picture
  assert.equal(s.heldCount(), 1, "the slow picture's request is parked (" + SLOW_PATH + ")");
}

test("case 1: a gated note. The chord arms (FAILS BEFORE: the raw print runs unprevented with a placeholder standing and an <img> incomplete); Escape and a second press disarm; without them prints once the held picture lands, the placeholder kept; with them loads the host and prints after that picture settled; every print fires with every <img> complete", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", GATED_NOTE);
    const { page } = s;
    await gatedSettled(s);
    const before = await imgFacts(page);
    assert.equal(before.gates, 1, "one placeholder: the remote picture");
    assert.equal(before.total, 3, "three <img> in the body: the quick one, the slow one, and the gated one inside its placeholder (no src, so complete by HTML's definition)");
    assert.equal(before.incomplete, 1, "the slow picture is incomplete while its request is parked");
    // the chord, with the placeholder standing and the slow picture incomplete
    await page.keyboard.press("Control+p");
    await frames(page, 1);
    const k = await chords(page);
    assert.equal(k.length, 1, "the window heard one Ctrl+P");
    assert.equal(k[0].open, true); assert.equal(k[0].gates, 1); assert.equal(k[0].incomplete, 1, "at the chord: a placeholder stands and an <img> is incomplete");
    assert.equal(k[0].prevented, true, "FAILS BEFORE: at the unchanged viewer the chord is not prevented, so the browser's own print runs over the placeholder and the half-loaded picture");
    assert.equal((await prints(page)).length, 0, "nothing printed yet: the bar armed instead");
    let b = await bar(page);
    assert.equal(b.present, true, "the Print word button is in the bar");
    assert.equal(b.text, "Print"); assert.equal(b.phase, "armed"); assert.equal(b.on, true); assert.equal(b.expanded, "true");
    assert.equal(b.line, "1 picture from another host is not loaded.");
    assert.deepEqual(b.buttons, ["Print with them", "Print without them"]);
    // Escape disarms and leaves the card up
    await page.keyboard.press("Escape");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.line, null, "Escape removed the line"); assert.equal(b.phase, null); assert.equal(b.on, false); assert.equal(b.cardUp, true, "the viewer stays open: Escape while armed disarms and does not close the card");
    // the button arms, and a second press disarms
    await page.click("#romp-fileview .fileview-print");
    b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.line, "1 picture from another host is not loaded.");
    await page.click("#romp-fileview .fileview-print");
    b = await bar(page);
    assert.equal(b.phase, null, "the second press disarmed"); assert.equal(b.line, null);
    assert.equal((await prints(page)).length, 0);
    // without them: the placeholder stays, the wait runs over the slow picture, the print fires when it lands
    await page.click("#romp-fileview .fileview-print");
    await page.click('#fileview-print-line button:has-text("Print without them")');
    b = await bar(page);
    assert.equal(b.phase, "preparing"); assert.equal(b.busy, true);
    assert.equal(b.line, "Preparing 1 picture…", "the slow picture is the one still loading");
    assert.deepEqual(b.buttons, [], "the wait's line has no buttons");
    assert.equal((await imgFacts(page)).gates, 1, "the placeholder stands: nothing fetched from the other host");
    await frames(page, 3);
    assert.equal((await prints(page)).length, 0, "no print while the picture is still loading");
    await s.release();
    await printsReach(page, 1);
    let p = await prints(page);
    assert.equal(p.length, 1);
    assert.equal(p[0].incomplete, 0, "window.print fired with every <img> complete");
    assert.equal(p[0].gates, 1, "…with the placeholder kept (Print without them)");
    assert.equal(p[0].line, false, "the preparing line is gone before the print");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "the bar rested when print returned"); assert.equal(b.busy, false); assert.equal(b.line, null);
    assert.ok(!s.requests.some((u) => u.indexOf("https://" + REMOTE_HOST + "/") === 0), "no request reached the other host");
    // with them: the placeholder is restored (the host's request appears), and the print waits for that picture
    await page.click("#romp-fileview .fileview-print");
    b = await bar(page);
    assert.equal(b.phase, "armed", "the placeholder still stands, so the press arms again");
    await page.click('#fileview-print-line button:has-text("Print with them")');
    b = await bar(page);
    assert.equal((await imgFacts(page)).gates, 0, "the placeholder is restored at once (loadGatedHost, the click's own path)");
    assert.equal(b.phase, "preparing"); assert.equal(b.line, "Preparing 1 picture…", "the remote picture is the one loading now");
    assert.equal((await prints(page)).length, 1, "no print before the remote picture settled");
    await printsReach(page, 2);
    p = await prints(page);
    assert.equal(p.length, 2);
    assert.equal(p[1].gates, 0); assert.equal(p[1].incomplete, 0, "window.print fired with every <img> complete");
    assert.equal(p[1].remoteReady, true, "the picture from the other host is loaded and decoded at the print");
    assert.ok(s.requests.some((u) => u === REMOTE), "the host was asked for the picture, as a click on the placeholder asks it");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

test("case 2: Ctrl+P with a file open runs the flow and the raw print is prevented; with no file open, or with a text field focused, the key is untouched and nothing prints", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "chat", PLAIN_NOTE);
    const { page } = s;
    await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview img")).every((i: any) => i.complete), null, { timeout: 10000 });
    await page.keyboard.press("Control+p");
    await frames(page, 1);
    let k = await chords(page);
    assert.equal(k.length, 1); assert.equal(k[0].prevented, true, "the chord is prevented"); assert.equal(k[0].open, true);
    let p = await prints(page);
    assert.equal(p.length, 1, "with no placeholder and the picture complete the chord printed at once");
    assert.equal(p[0].incomplete, 0); assert.equal(p[0].gates, 0);
    // a text field holds the keyboard: the browser's own chord
    await page.evaluate(() => { const i = document.createElement("input"); i.id = "probe-field"; document.body.appendChild(i); i.focus(); });
    await page.keyboard.press("Control+p");
    await frames(page, 1);
    k = await chords(page);
    assert.equal(k.length, 2); assert.equal(k[1].prevented, false, "a focused text field leaves the chord to the browser"); assert.equal(k[1].open, true);
    assert.equal((await prints(page)).length, 1, "nothing printed from the field");
    await page.evaluate(() => { const i = document.getElementById("probe-field") as HTMLInputElement; i.blur(); i.remove(); });
    // the viewer closed: no file open
    await page.evaluate(() => { (window as any).FV.closeFileView(); });
    await frames(page, 1);
    await page.keyboard.press("Control+p");
    await frames(page, 1);
    k = await chords(page);
    assert.equal(k.length, 3); assert.equal(k[2].open, false); assert.equal(k[2].prevented, false, "with no file open the key is untouched");
    assert.equal((await prints(page)).length, 1, "…and nothing printed");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

test("case 3: no placeholder and every picture complete: one click prints at once in the click's own task, with no line shown; the Raw view (no pictures) the same", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const raw of [false, true]) {
      const s = await scene(browser, "pane", PLAIN_NOTE, { raw });
      const { page } = s;
      await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview img")).every((i: any) => i.complete), null, { timeout: 10000 });
      const facts = await imgFacts(page);
      assert.equal(facts.total, raw ? 0 : 1, raw ? "the Raw view draws no picture" : "the Rendered view's one picture");
      assert.equal(facts.incomplete, 0); assert.equal(facts.gates, 0);
      const printed = await page.evaluate(() => {   // the click and the read in one task: the print runs inside the click handler
        (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click();
        return (window as any).__prints.length;
      });
      assert.equal(printed, 1, (raw ? "Raw" : "Rendered") + ": one click printed at once, before the handler returned");
      const p = await prints(page);
      assert.equal(p[0].line, false, "no line was shown"); assert.equal(p[0].incomplete, 0); assert.equal(p[0].gates, 0);
      const b = await bar(page);
      assert.equal(b.phase, null, "the bar rests"); assert.equal(b.line, null);
      assert.deepEqual(s.errors, [], "no script error");
      await page.close();
    }
  });
});

test("case 4: the deadline. A picture whose route never answers prints after the deadline (shortened through the test seam), still incomplete; the seam restored, the constant is 8 s", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", GATED_NOTE);
    const { page } = s;
    await gatedSettled(s);
    const constant = await page.evaluate(() => (window as any).FV.printSettleMs());
    assert.equal(constant, 8000, "the deadline in the product");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(300); });
    await page.click("#romp-fileview .fileview-print");
    const t0 = await page.evaluate(() => performance.now());
    await page.click('#fileview-print-line button:has-text("Print without them")');
    assert.equal((await bar(page)).line, "Preparing 1 picture…");
    await printsReach(page, 1, 5000);
    const p = await prints(page);
    assert.equal(p.length, 1);
    assert.equal(p[0].incomplete, 1, "the held picture is still loading at the print: it prints as the browser has it");
    assert.equal(p[0].gates, 1);
    assert.ok(p[0].t - t0 >= 280, "the print came after the shortened deadline (" + Math.round(p[0].t - t0) + " ms after the choice)");
    assert.ok(p[0].t - t0 < 4000, "…and well before the product's 8 s (" + Math.round(p[0].t - t0) + " ms)");
    assert.equal((await bar(page)).phase, null, "the bar rested");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    assert.equal(s.heldCount(), 1, "the held request is still parked: nothing released it");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

test("case 5: the URL kind. A document from a link with a picture on another host arms on the chord with the same line, and without them prints at once (no other picture to wait on)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "chat", URL_NOTE, { url: true });
    const { page } = s;
    await page.waitForFunction(() => document.querySelectorAll('[data-act="fv-load"]').length === 1, null, { timeout: 10000 });
    await page.keyboard.press("Control+p");
    await frames(page, 1);
    const k = await chords(page);
    assert.equal(k.length, 1); assert.equal(k[0].prevented, true);
    let b = await bar(page);
    assert.equal(b.present, true, "the URL viewer's bar has the Print button");
    assert.equal(b.phase, "armed"); assert.equal(b.line, "1 picture from another host is not loaded.");
    assert.deepEqual(b.buttons, ["Print with them", "Print without them"]);
    await page.click('#fileview-print-line button:has-text("Print without them")');
    const p = await prints(page);
    assert.equal(p.length, 1, "the placeholder's img has no src and is complete: nothing to wait on, the print ran at once");
    assert.equal(p[0].gates, 1); assert.equal(p[0].incomplete, 0);
    b = await bar(page);
    assert.equal(b.phase, null); assert.equal(b.line, null);
    assert.ok(!s.requests.some((u) => u.indexOf("https://" + REMOTE_HOST + "/") === 0), "no request reached the other host");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});
