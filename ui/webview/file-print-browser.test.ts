// Print from the viewer with its pictures loaded (file-print.ts; the print follow-on to plans/markdown-viewer.md's Slice 3,
// item 12), over the real viewer in headless Chromium the way file-view-print-browser.test.ts drives the pane and the chat
// modal. Before this the sheets printed the open file, but nothing awaited its pictures: the browser's own Ctrl/Cmd+P ran
// with a gated figure's placeholder standing and a picture still loading, and printed both as they were. The contract's
// cases: (1) a note with a local picture the test's route answers, a local picture whose route is HELD (incomplete until
// the test releases it) and a picture on a host the gear's list does not name (a placeholder): the chord and the Print
// button arm with "1 picture from another host is not loaded." and the two word buttons; Escape and a second press disarm
// and leave the card up; "Print without them" leaves the placeholder and prints once the held picture lands; "Print with
// them" restores the placeholder (the host's request appears) and prints only after that picture settled; window.print,
// stubbed on the page to record the call, fires only with every <img> complete; the wait's line carries the viewer's loader
// after its words (the swirl, the wordmark and the three dots, inline on the words' row at the row's size, every part
// animating, hidden from the status's announcement: the loading-state rule; the first build showed the words alone).
// (2) Ctrl+P with a file open runs the
// flow and the browser's raw print is prevented (a window keydown listener reads defaultPrevented after the viewer's
// capture-phase listener); with no file open, or with a text field focused, the key is untouched and nothing prints. (3)
// a note with no placeholder and its pictures complete prints on one click, in the click's own task, with no line shown;
// the Raw view (a code view, no pictures) the same. (4) the deadline asks: a picture whose route never answers brings, at
// the deadline (shortened through the module's test seam, FV.setPrintSettleMs), a line saying it has not loaded with
// "Print anyway" and "Keep waiting", and no print; the line's last sentence says what Print anyway does ("Print anyway
// leaves out any picture still loading."), read from the line before the press at both sites (the round-4 review's ruling,
// 2026-09-20; count-free since the round-5 review's ui-1: a counted picture can land while the line stands, and then prints);
// "Print anyway" prints once without the picture still loading (a markdown picture with no declared size prints as a 0
// by 0 box, nothing where it was: measured under print media in file-print-driver-browser.test.ts case (15a));
// "Keep waiting" waits on the load and error events alone, with no timer, its line reading "Waiting for 1 picture… Print
// anyway leaves out any picture still loading." with one word button, "Print anyway" (romp-manager's ruling, 2026-09-20;
// file-print-driver-browser.test.ts case (15) presses it), and prints once the picture lands, every <img>
// complete; Escape or a second press under the ask, and Escape during that open-ended wait, print nothing and leave the
// card up (the third review, 2026-09-19: before this the print ran at the deadline and the picture, a markdown picture
// with no declared size, printed as nothing where it stood, with nothing said). (5) the
// URL kind: a document from a link with a picture on another host arms the same way. (6) the body not in (P7): a file
// whose answer is parked (the page's fetch stub wrapped to hold the report's GET until the test releases it) shows the
// loader, and Print is disabled over it, by aria-disabled and the sheets' disabled dress and never the `disabled` property
// (the bar's own rule, file-view.ts textSizeControl: a button that disables under keyboard focus drops it on the document's
// body; the third review, 2026-09-19), so the button keeps the keyboard and the tab order while disabled: focused, a forced
// click, a programmatic click and the chord print nothing and leave the keyboard on the button, the chord still prevented
// (the browser's raw print would print the loader page); the answer released and the text seated, the button is live and
// the next press prints. FAILS BEFORE: the first assertion of case 1, at the unchanged viewer (no button, no listener): the
// chord is not prevented while a placeholder stands and an <img> is incomplete, so the browser's raw print is what runs;
// case 6 at the first build, whose button was live from the bar's build (the aria-disabled assertion), and at the second,
// whose button took the `disabled` property (the property and the keyboard assertions). Skips loudly without a browser.
// Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, REPORT, ROOT, ORIGIN, type Mode } from "./real-viewer-leg";
import { stalledWords, waitingWords, anywayWords } from "./file-print";

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
type Bar = { present: boolean; label: string | null; title: string | null; glyph: boolean; disabled: boolean; ariaDisabled: string | null; on: boolean; busy: boolean; expanded: string | null; phase: string | null; line: string | null; buttons: string[]; cardUp: boolean; active: string };

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
  const describe = (a: Element | null): string => (a ? a.tagName + (a.className ? "." + String(a.className).split(" ").filter((c) => c && c !== "romp-acted").join(".") : "") : "null");   // the keyboard's holder: the tag and its classes (the click's press pulse aside)
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const line = document.getElementById("fileview-print-line");
    return { present: !!b, label: b ? b.getAttribute("aria-label") : null, title: b ? b.title : null, glyph: !!b && !!b.querySelector("svg") && (b.textContent || "").trim() === "", disabled: !!b && b.disabled, ariaDisabled: b ? b.getAttribute("aria-disabled") : null, on: !!b && b.classList.contains("on"), busy: !!b && b.classList.contains("fileview-busy"), expanded: b ? b.getAttribute("aria-expanded") : null, phase: b ? (b.dataset.print || null) : null,
      line: line ? (line.firstChild && line.firstChild.nodeType === 3 ? (line.firstChild.textContent || "") : line.textContent) : null, buttons: line ? Array.from(line.querySelectorAll("button")).map((x) => x.textContent || "") : [], cardUp: !!document.getElementById("romp-fileview"), active: describe(document.activeElement) };
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
/** The line's height on screen, for the one-row check below. */
const lineHeight = (page: any): Promise<number> => page.evaluate(() => document.getElementById("fileview-print-line")!.getBoundingClientRect().height);
type Loader = { present: boolean; after?: boolean; hidden?: string | null; parts?: string[]; wordmark?: string | null; swirl?: boolean; display?: string; padding?: string; fontSize?: string; rowFontSize?: string; running?: number[]; rowHeight?: number };
/** The wait's loader as the line holds it: after the words (the line's first node stays the text, so the words above read as
 *  before), hidden from the status's announcement, the viewer's markup (the swirl, the wordmark, three dots), an inline flex
 *  box on the words' row with no padding of its own at the row's font size, every part's animation running, and the row's
 *  height (the loader's own rule would add 60px of padding and a row of its own). */
const loaderFacts = (page: any): Promise<Loader> => page.evaluate(() => {
  const line = document.getElementById("fileview-print-line");
  const load = line ? line.querySelector(".fileview-load") as HTMLElement | null : null;
  if (!line || !load) return { present: false };
  const cs = getComputedStyle(load);
  return { present: true, after: !!line.firstChild && line.firstChild.nodeType === 3 && line.lastChild === load, hidden: load.getAttribute("aria-hidden"),
    parts: Array.from(load.children).map((c) => c.tagName), wordmark: (load.querySelector("span") as HTMLElement | null)?.textContent ?? null,
    swirl: ((load.querySelector("img") as HTMLImageElement | null)?.getAttribute("src") || "") === "/media/romp-swirl-glyph.svg",
    display: cs.display, padding: cs.padding, fontSize: cs.fontSize, rowFontSize: getComputedStyle(line).fontSize,
    running: Array.from(load.querySelectorAll("img, .fileview-dot")).map((el) => (el as HTMLElement).getAnimations().filter((a) => a.playState === "running").length),
    rowHeight: line.getBoundingClientRect().height };
});

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

test("case 1: a gated note. The chord arms (FAILS BEFORE: the raw print runs unprevented with a placeholder standing and an <img> incomplete); Escape and a second press disarm; without them prints once the held picture lands, the placeholder kept; with them restores the placeholder and prints after that picture settled; every print fires with every <img> complete", { timeout: 120000 }, async (t) => {
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
    assert.equal(b.present, true, "the Print glyph button is in the bar");
    assert.equal(b.label, "Print"); assert.equal(b.title, "Print"); assert.equal(b.glyph, true, "a glyph in Download's shape: an svg and no text, the words in the title and aria-label");
    assert.equal(b.disabled, false, "the text is in: the button is live"); assert.equal(b.phase, "armed"); assert.equal(b.on, true); assert.equal(b.expanded, "true");
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
    assert.equal((await loaderFacts(page)).present, false, "the armed line carries no loader: nothing is loading yet");
    const armedHeight = await lineHeight(page);
    await page.click('#fileview-print-line button:has-text("Print without them")');
    b = await bar(page);
    assert.equal(b.phase, "preparing"); assert.equal(b.busy, true);
    assert.equal(b.line, "Preparing 1 picture…", "the slow picture is the one still loading");
    assert.deepEqual(b.buttons, [], "the wait's line has no buttons");
    const load = await loaderFacts(page);
    assert.equal(load.present, true, "the wait's line carries the viewer's loader (the loading-state rule)");
    assert.equal(load.after, true, "after the words: the line's first node is still the text");
    assert.equal(load.hidden, "true", "hidden from the status's announcement, which reads the words alone");
    assert.deepEqual(load.parts, ["IMG", "SPAN", "I", "I", "I"], "the swirl, the wordmark and three dots");
    assert.equal(load.wordmark, "romp"); assert.equal(load.swirl, true, "the swirl glyph at its media path");
    assert.equal(load.display, "inline-flex", "inline on the words' row"); assert.equal(load.padding, "0px", "none of the loader's own 30px paddings");
    assert.equal(load.fontSize, load.rowFontSize, "at the row's size: the loader's 0.86em does not compound under the line's");
    assert.deepEqual(load.running, [1, 1, 1, 1], "the swirl's spin and each dot's pulse are running");
    assert.ok(load.rowHeight! <= armedHeight + 2, "one row: the wait's line is no taller than the armed line was (" + load.rowHeight + " vs " + armedHeight + ")");
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
    assert.equal((await imgFacts(page)).gates, 0, "the placeholder is restored at once (loadGatedFigure: this placeholder alone, and its host granted nothing for the page)");
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

const STALLED_ONE = stalledWords(1);            // "1 picture has not loaded. Print anyway leaves out any picture still loading."
const WAITING_ONE = waitingWords(1);            // "Waiting for 1 picture… Print anyway leaves out any picture still loading."
const PRINT_BTN = "#romp-fileview .fileview-print";
const WITHOUT_BTN = '#fileview-print-line button:has-text("Print without them")';
const ANYWAY_BTN = '#fileview-print-line button:has-text("Print anyway")';
const KEEP_BTN = '#fileview-print-line button:has-text("Keep waiting")';
/** The line's words (its first text node) read `words`. */
const lineReads = (page: any, words: string): Promise<unknown> => page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, words, { timeout: 5000 });
/** A shortened deadline, a press and "Print without them" over the parked picture, and the ask at the deadline. */
async function askAtDeadline(s: Scene): Promise<number> {
  await s.page.evaluate(() => { (window as any).FV.setPrintSettleMs(300); });
  await s.page.click(PRINT_BTN);
  const t0 = await s.page.evaluate(() => performance.now());
  await s.page.click(WITHOUT_BTN);
  assert.equal((await bar(s.page)).line, "Preparing 1 picture…", "the wait over the parked picture");
  await s.page.waitForFunction((w: string) => (window as any).__prints.length > 0 || (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, STALLED_ONE, { timeout: 5000 });   // the deadline: the ask, or (before the fix) the print
  assert.equal((await prints(s.page)).length, 0, "FAILS BEFORE: window.print ran at the deadline with the picture incomplete; the bar asks instead");
  await lineReads(s.page, STALLED_ONE);
  return t0;
}

test("case 4: the deadline asks. A picture whose route never answers: at the deadline (shortened through the test seam) the line says it has not loaded, with Print anyway and Keep waiting, and window.print is NOT called (FAILS BEFORE: the print ran at the deadline, the picture incomplete); Print anyway prints once with the picture still loading and left off the paper; Keep waiting sets no timer, its line reading " + JSON.stringify(waitingWords(1)) + " with Print anyway alone, and prints once the picture lands, every <img> complete; Escape or a second press under the ask, and Escape during the open-ended wait, print nothing and leave the card up; the seam restored, the constant is 8 s", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a: the ask, then Print anyway
    let s = await scene(browser, "pane", GATED_NOTE);
    let { page } = s;
    await gatedSettled(s);
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the deadline in the product");
    const t0 = await askAtDeadline(s);
    const t1 = await page.evaluate(() => performance.now());
    assert.ok(t1 - t0 >= 280 && t1 - t0 < 4000, "the ask came at the shortened deadline (" + Math.round(t1 - t0) + " ms after the choice)");
    let b = await bar(page);
    assert.equal(b.phase, "stalled", "FAILS BEFORE: the bar rested after printing at the deadline");
    assert.equal(b.busy, false, "nothing is awaited under the ask"); assert.equal(b.on, true); assert.equal(b.expanded, "true", "the button opened the line, as while armed");
    assert.deepEqual(b.buttons, ["Print anyway", "Keep waiting"], "the two choices");
    assert.equal(b.line, "1 picture has not loaded. Print anyway leaves out any picture still loading.", "the ask's line, read before the press: the count, then the button's own sentence (FAILS BEFORE: the line ended at the count, and the press dropped the picture with nothing said)");
    assert.ok(b.line!.endsWith(" " + anywayWords()), "the sentence is the line's last words, beside the button");
    assert.equal((await loaderFacts(page)).present, false, "no loader under the ask");
    assert.equal((await prints(page)).length, 0, "FAILS BEFORE: window.print ran at the deadline; nothing prints until the person answers");
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "…and nothing later: no timer stands under the ask");
    await page.click(ANYWAY_BTN);
    let p = await prints(page);
    assert.equal(p.length, 1, "Print anyway printed at once, in the click's own task");
    assert.equal(p[0].incomplete, 1, "the held picture is still loading at the print: it is left off the paper, as the line said and the person chose");
    assert.equal(p[0].gates, 1); assert.equal(p[0].line, false, "the ask went before the print");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "the bar rested"); assert.equal(b.line, null); assert.equal(b.on, false);
    assert.equal(s.heldCount(), 1, "the held request is still parked: nothing released it");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // b: Keep waiting: the wait's line and loader are back, no timer, the print at the picture's load
    s = await scene(browser, "pane", GATED_NOTE);
    page = s.page;
    await gatedSettled(s);
    await askAtDeadline(s);
    await page.click(KEEP_BTN);
    b = await bar(page);
    assert.equal(b.phase, "preparing", "Keep waiting: the wait again"); assert.equal(b.line, "Waiting for 1 picture… Print anyway leaves out any picture still loading.", "the open-ended wait's words, read before any press: the count, then the button's own sentence (FAILS BEFORE: the line ended at the count)"); assert.equal(b.line, WAITING_ONE); assert.equal(b.busy, true); assert.deepEqual(b.buttons, ["Print anyway"], "one word button, the way through the open-ended wait (romp-manager's ruling, 2026-09-20; the driver leg's case (15) presses it)");
    assert.equal((await loaderFacts(page)).present, true, "the wait's loader is back on the line");
    await page.evaluate((k: number) => new Promise<void>((r) => setTimeout(r, k)), 1000);   // a timer, since the absence of one is what is measured: three of the seam's deadlines
    assert.equal((await prints(page)).length, 0, "no print 1 s past the answer: Keep waiting set no deadline");
    b = await bar(page);
    assert.equal(b.phase, "preparing", "still waiting"); assert.equal(b.line, WAITING_ONE);
    await s.release();
    await printsReach(page, 1);
    p = await prints(page);
    assert.equal(p.length, 1, "one print, at the picture's load");
    assert.equal(p[0].incomplete, 0, "window.print fired with every <img> complete"); assert.equal(p[0].gates, 1); assert.equal(p[0].line, false);
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // c: Escape under the ask; a second press under the ask; Escape during the open-ended wait: nothing prints, the card stays up
    s = await scene(browser, "pane", GATED_NOTE);
    page = s.page;
    await gatedSettled(s);
    await askAtDeadline(s);
    await page.keyboard.press("Escape");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "Escape under the ask disarmed"); assert.equal(b.line, null); assert.equal(b.cardUp, true, "…and the card stays up");
    assert.equal((await prints(page)).length, 0);
    await askAtDeadline(s);
    await page.click(PRINT_BTN);
    b = await bar(page);
    assert.equal(b.phase, null, "a second press under the ask disarmed"); assert.equal(b.line, null); assert.equal(b.cardUp, true);
    assert.equal((await prints(page)).length, 0);
    await askAtDeadline(s);
    await page.click(KEEP_BTN);
    assert.equal((await bar(page)).phase, "preparing");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "Escape during the open-ended wait cancelled it"); assert.equal(b.line, null); assert.equal(b.cardUp, true, "…and the card stays up: the wait was the bar's to cancel");
    assert.equal(s.heldCount(), 1, "the picture's request is still parked");
    await s.release();
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "the picture landing after the cancel prints nothing");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
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

const PARKED_NOTE = "# Parked\n\nText alone, no picture.\n\nLast line.\n";
const PRINT_ACTIVE = "BUTTON.fileview-btn.fileview-icon.fileview-print";
test("case 6: the body not in. A file whose answer is parked: Print is disabled over the loader by aria-disabled alone (never the property, so the button keeps the keyboard and the tab order), and with the keyboard on it a forced click, a programmatic click and the chord print nothing and leave the keyboard on the button, the chord still prevented; the answer released, the button enables and the next press prints", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // the file's own answer goes through the page's fetch stub (real-viewer-leg.ts pageHtml), so the park wraps the stub: the
    // report's GET waits on a promise the test resolves through window.__release; a HEAD (the changed-on-disk probe) does not
    const { page, errors } = await openViewer(browser, "pane", 900, 700, {
      docs: { [REPORT]: PARKED_NOTE },
      waitFor: "#romp-fileview .fileview-body .fileview-load",   // the first paint awaited is the loader's
      before: async (pg: any) => {
        await pg.evaluate(() => {
          const w = window as any; const prev = w.fetch;
          const gate = new Promise<void>((r) => { w.__release = r; });
          w.fetch = async function (url: unknown, init: any) {
            const m = /[?&]path=([^&]*)/.exec(String(url));
            if (m && /\/report\.md$/.test(decodeURIComponent(m[1])) && !(init && init.method === "HEAD")) await gate;
            return prev(url, init);
          };
        });
        await pg.evaluate(PAGE_PROBES);
      },
    });
    let b = await bar(page);
    assert.equal(b.present, true, "the button is in the bar from the build");
    assert.equal(b.ariaDisabled, "true", "FAILS BEFORE the first build's fix: aria-disabled while the loader holds the body");
    assert.equal(b.disabled, false, "FAILS BEFORE: the `disabled` property is never set (the bar's rule: a disabled button drops the keyboard and leaves the tab order)");
    assert.equal(b.phase, "disabled");
    assert.equal(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-body .fileview-load")), true, "the loader holds the body");
    // the keyboard on the disabled button: it stays there through every press that changes nothing
    await page.focus("#romp-fileview .fileview-print");
    assert.equal((await bar(page)).active, PRINT_ACTIVE, "FAILS BEFORE: the disabled button takes the keyboard (a button with the property refuses it)");
    await page.click("#romp-fileview .fileview-print", { force: true });   // forced: the click reaches the driver, whose disabled phase ignores the press
    await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click(); });   // a programmatic click reaches it too
    await page.keyboard.press("Control+p");
    await frames(page, 1);
    const k = await chords(page);
    assert.equal(k.length, 1, "the window heard one Ctrl+P"); assert.equal(k[0].open, true);
    assert.equal(k[0].prevented, true, "the chord is prevented over the loader: the browser's raw print would print the loader page");
    assert.equal((await prints(page)).length, 0, "nothing printed: the clicks and the chord over the loader change nothing");
    b = await bar(page);
    assert.equal(b.ariaDisabled, "true", "still disabled"); assert.equal(b.disabled, false); assert.equal(b.line, null, "no line"); assert.equal(b.phase, "disabled");
    assert.equal(b.active, PRINT_ACTIVE, "the keyboard is still on the button, never dropped on the document's body");
    await page.evaluate(() => { (window as any).__release(); });
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-md > p"), null, { timeout: 10000 });
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.ariaDisabled, null, "the text seated: the button is live"); assert.equal(b.disabled, false); assert.equal(b.phase, null);
    assert.notEqual(b.active, "BODY", "the keyboard did not land on the document's body at the seating: " + b.active);
    const printed = await page.evaluate(() => {   // the click and the read in one task
      (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click();
      return (window as any).__prints.length;
    });
    assert.equal(printed, 1, "the next press printed at once: no picture, no placeholder");
    assert.equal((await prints(page))[0].incomplete, 0); assert.equal((await prints(page))[0].gates, 0);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
