// The print flow's DOM driver (file-print.ts installFilePrint) over the real viewer in headless Chromium, the way
// file-print-browser.test.ts drives it, for what the first review of the print follow-on (plans/markdown-viewer.md,
// "Follow-on: Print (2026-09-19)") found held by the machine's node tests or by a string pin alone, or not at all:
// (1) a held Ctrl/Cmd+P: every repeat is prevented while a file is open (the browser's default for each is its own print)
//     and none is a press (the bar neither flaps nor prints); a synthetic repeat at rest is prevented and changes nothing;
// (2) a listener before the flow's that already prevented the chord (the dashboard shell's command palette dispatcher,
//     palette-main.ts, which claims Mod+P on every pane document at the frame's load, ahead of the flow's per-open listener):
//     the flow stands down, so one keystroke does not open the palette AND print; a stand-in mirrors that dispatcher with
//     keybindings.ts's own predicates and commands.ts's own binding, and the real module's wiring is pinned from its source;
// (3) a repaint during the wait (the changed-on-disk bar's Reload landing a new body under the wait): the wait is re-aimed
//     at the new body, so a picture the landing brought is awaited and the old body's detached picture prints nothing
//     when it lands; a landing with every picture complete prints at once; the deadline is the press's, not restarted;
// (4) a close during the wait prints nothing when the parked picture then lands; a close while armed leaks no listener
//     (the reopened card's first Escape closes it, which a leaked armed listener would swallow), and the chord after
//     several opens presses once;
// (5) a press and the chord during the wait change nothing over the driver, and the deadline stays the press's (a driver
//     that restarted the wait at the second press would ask later): at the deadline the bar asks, with the parked picture
//     still loading, and "Print anyway" prints once;
// (6) a <video poster> and an svg <image href> in the real DOM (the sanitizer's profile, rewriteFigureSrcs's attributes):
//     the press waits on both through the probes and prints once after both land, with no request to another host;
// (7) Escape from inside the Outline popover while the bar is armed closes the popover and puts the keyboard back on its
//     button, the bar still armed; the next Escape disarms; at rest the popover's Escape is untouched;
// (8) Escape or Enter on the armed line's word buttons hands the keyboard to the Print button, never to the document's body;
// (9) "Print with them"'s title names the hosts the press grants: one placeholder naming two hosts (a <picture> whose source
//     and img are on different hosts), and two placeholders on two hosts;
// (10) a <video poster> and an svg <image href> whose routes answer 404 (the third review's correctness-1, tests-1 and
//     extra5-1, one defect): one press asks the host ONCE for each URL and prints at once when both probes have failed,
//     well inside the deadline. Before the fix the wait's re-aim at every settle minted a fresh probe Image per URL, a
//     failed URL is never complete on a fresh Image, and the driver looped until the deadline: the press asked the host
//     hundreds of times for each URL (the review measured 337 in 8 s) and the bar asked at the deadline instead of printing;
// (11) an <img loading="lazy"> far below the fold (the third review's fresh-2): the browser has not started its fetch, so
//     nothing would fire load or error; the press sets it eager, the fetch starts, and the print follows its load. Before
//     the fix the wait ran to its deadline over it and the bar asked, the picture blank;
// (12) the settle's re-aim under the press's deadline (the fourth review's correction of tests-2, 2026-09-19): a second
//     parked picture inserted inside the rendered root mid-wait, a grandchild of the body, so the observer of the body's
//     children is silent and no repaint re-aim runs; the first picture released settles the wait, and the settle's re-aim
//     finds the second; the ask comes at the PRESS's deadline, not one restarted at the settle;
// (13) a repaint under the deadline's ask (the round-2 review's regression-1 and tests-1, 2026-09-19): a Reload landing a
//     body with nothing loading, or a Raw pick, is no answer to the ask, so it never prints: with nothing left loading the
//     question is moot and the flow rests (the line goes, and the next press prints at once); with pictures still loading
//     the ask stands and its count follows in place. Before this the driver's recount fed the machine a zero count that
//     was read as the print act, and window.print ran with neither button pressed, over the Raw view in one case;
// (14) the press-time read of the body (the round-2 review's tests-5): a press reads the body's children itself before it
//     acts, so a swap in the press's own task, before the observer has run, is seen: the loader swapped in and a press in
//     one task prints nothing and disables; content swapped in over the open's loader and a press in one task prints.
// (3d) a Reload landing during the wait that names a URL the press already probed to its end (an svg <image href> whose
//     route answered 404: the probe is complete): the finished probe is dropped and the URL probed again against the
//     landing (file-print.ts dropDone), a request the browser folds into the landing element's own, still in flight, so no
//     request beyond the landing's leaves the page and the print waits on that fetch and comes at its release; a probe
//     still in flight is kept. Before this (the round-2 review's extra7-1, landed 2026-09-20) the wait answered from the old
//     document's failed probe and window.print ran with the landing's fetch still in flight. (13c) the same landing under
//     the deadline's ask: the count reads one, the ask stands and its line is the same row; before this the count read none
//     and the question was called moot, the line gone with the landing's fetch in flight.
// (5b) the deadline's ask is written INTO the wait's line: the same row (marked before the deadline, still marked after), the
//     loader gone, the two word buttons in it (the round-2 review's ui-2, landed 2026-09-20: before this the ask was a fresh
//     row, so the accessibility tree lost the wait's live region and gained another at the transition).
// (15) Keep waiting's open-ended wait carries one word button, "Print anyway" (romp-manager's ruling, 2026-09-20, on the
//     round-2 review's fresh-2 and the round-3 review's tests-4, ui-2 and extra5-3): after Keep waiting the line reads
//     "Waiting for 1 picture… " and then anywayWords() beside the loader with Print anyway alone, which prints at once with what has loaded, the
//     parked picture incomplete and the placeholder on the paper, the request still parked; a Reload landing under that
//     wait rewrites the count in the same row with the button staying, and the landing's pictures released print as
//     before; no timer. Before this the line read "Preparing 1 picture…" with no button, so the wait had no way through
//     but the load. Escape during that wait was established by execution on the code before the button (2026-09-20): the
//     bar rested with the card up and the line gone, nothing printed, and the release after it printed nothing; so the
//     person had an exit and lacked a way through, and the button is the way through, not a second exit. The case
//     executes both.
// Each re-aim's deadline is executed by its own case: the repaint's in case (3c), a Reload landing mid-wait whose picture
// is parked too, and the ask at the PRESS's deadline, not one restarted at the landing (the third review's tests-2: the
// record's claim was pinned by a source-text census alone, and a re-aim restarting the full deadline left every leg
// green); the settle's in case (12) (the fourth review: case (3c) drives the repaint's re-aim alone, and a settle re-aim
// restarting the full deadline left every leg green, case (3c) included).
// Skips loudly without a browser. Synthetic values only: an invented note, /repo/notes-api paths, invented hosts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { inBrowser, openViewer, frames, REPORT, ROOT, ORIGIN, SID, MT2, UI, requireCjs, type Mode } from "./real-viewer-leg";
import { isPrintKeys, isPrintChord, withTitle, WITHOUT_TITLE, OWN_ESCAPE_SEL, ANYWAY_WORDS, KEEP_WORDS, ANYWAY_TITLE, KEEP_TITLE, waitingWords, stalledWords, anywayWords } from "./file-print";
import { DEFAULT_CHORDS } from "./commands";

const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
const QUICK = "fig.svg";                       // a local picture the route answers at once
const SLOW = "slow.svg";                       // a local picture whose route is parked until the test releases it
const SLOW2 = "slow2.svg";                     // a second one, brought by a reload
const SLOW3 = "slow3.svg";                     // a third, brought beside the second by a reload under the ask (case 13)
const POSTER = "clip.svg";                     // a <video poster>, parked
const IMAGE = "d.svg";                         // an svg <image href>, parked
const LAZY = "lazy.svg";                       // an <img loading="lazy"> far below the fold, parked
const REMOTE_HOST = "other.test";              // not in the gear's default list, not the page's origin: a placeholder
const REMOTE2_HOST = "another.test";
const REMOTE = "https://" + REMOTE_HOST + "/o.svg";
const GATED_NOTE = "# Figures\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nA remote one ![](" + REMOTE + ").\n\nLast line.\n";
const PLAIN_NOTE = "# Plain\n\nOne local picture ![](" + QUICK + ") and text.\n\nLast line.\n";
const SLOW_NOTE = "# Slow\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nLast line.\n";
const SLOW2_NOTE = "# Slow\n\nA local picture ![](" + QUICK + ") and a slower one ![](" + SLOW2 + ").\n\nA session appended a figure.\n";
const NOPIC_NOTE = "# Plain\n\nText alone, no picture.\n\nLast line.\n";
const TWO_SLOW_NOTE = "# Slow\n\nTwo slow ones ![](" + SLOW2 + ") and ![](" + SLOW3 + ").\n\nA session appended two figures.\n";
const MEDIA_NOTE = "# Media\n\nA clip:\n\n<video poster=\"" + POSTER + "\" controls></video>\n\nA diagram:\n\n<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"8\" height=\"8\"><image href=\"" + IMAGE + "\" width=\"8\" height=\"8\"/></svg>\n\nLast line.\n";
const HEADED_GATED = "# Title\n\n## One\n\nA remote picture ![](" + REMOTE + ").\n\n## Two\n\nMore text.\n\n## Three\n\nLast line.\n";
const DIAGRAM = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"8\" height=\"8\"><image href=\"" + IMAGE + "\" width=\"8\" height=\"8\"/></svg>";
const SLOW_DIAGRAM_NOTE = "# Diagram\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nA diagram:\n\n" + DIAGRAM + "\n\nLast line.\n";   // (3d), (13c): the diagram's route answers 404 to the render and to the press's probe
const DIAGRAM_ONLY_NOTE = "# Diagram\n\nA diagram:\n\n" + DIAGRAM + "\n\nA session replaced the pictures.\n";   // the landing: the same svg image URL, its route parked from here on
const TWO_HOST_NOTE = "# Two hosts\n\n<picture><source srcset=\"https://a.test/p.svg\" type=\"image/svg+xml\"><img src=\"https://b.test/p.svg\" alt=\"\"></picture>\n\nLast line.\n";
const TWO_GATES_NOTE = "# Two placeholders\n\nOne ![](" + REMOTE + ") and two ![](https://" + REMOTE2_HOST + "/a.svg).\n\nLast line.\n";
/** Three hundred paragraphs, then a lazy picture: at 900 by 700 the picture stands far past every distance at which the browser
 *  would start a lazy fetch, so it is not requested until something makes it eager. */
const LAZY_NOTE = "# Long\n\n" + Array.from({ length: 300 }, (_, i) => "Paragraph " + (i + 1) + ": lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor lorem ipsum dolor sit amet consectetur adipiscing elit.").join("\n\n") + "\n\n<img loading=\"lazy\" src=\"" + LAZY + "\" alt=\"\">\n\nLast line.\n";
const REMOTE_HOSTS = [REMOTE_HOST, REMOTE2_HOST, "a.test", "b.test"];

type Print = { t: number; gates: number; incomplete: string[]; line: boolean; cardUp: boolean; active: string };
type Key = { key: string; ctrl: boolean; repeat: boolean; prevented: boolean; open: boolean };
type Bar = { present: boolean; disabled: boolean; on: boolean; busy: boolean; phase: string | null; line: string | null; buttons: string[]; titles: string[]; cardUp: boolean; lines: number };

/** The page's record of the print stub's calls (with the incomplete pictures' URLs and the keyboard's holder), the window's
 *  keydowns, the bar as it stands, and the keyboard's holder. */
const PAGE_PROBES = () => {
  const w = window as any;
  w.__prints = []; w.__keys = [];
  const imgs = () => Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
  const gates = () => document.querySelectorAll('[data-act="fv-load"]').length;
  const describe = (a: Element | null): string => {   // the tag, the classes (the click's .romp-acted press pulse aside) and a button's words
    if (!a) return "null";
    const classes = String(a.className || "").split(" ").filter((c) => c && c !== "romp-acted");
    return a.tagName + (classes.length ? "." + classes.join(".") : "") + (a.textContent && a.tagName === "BUTTON" ? "[" + a.textContent.trim() + "]" : "");
  };
  w.__active = () => describe(document.activeElement);
  w.print = () => {
    w.__prints.push({ t: performance.now(), gates: gates(), incomplete: imgs().filter((i) => !i.complete).map((i) => decodeURIComponent(i.src)), line: !!document.getElementById("fileview-print-line"), cardUp: !!document.getElementById("romp-fileview"), active: w.__active() });
  };
  window.addEventListener("keydown", (e) => { w.__keys.push({ key: e.key, ctrl: e.ctrlKey || e.metaKey, repeat: e.repeat, prevented: e.defaultPrevented, open: document.body.classList.contains("fileview-open") }); });
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const line = document.getElementById("fileview-print-line");
    const btns = line ? Array.from(line.querySelectorAll("button")) : [];
    return { present: !!b, disabled: !!b && b.disabled, on: !!b && b.classList.contains("on"), busy: !!b && b.classList.contains("fileview-busy"), phase: b ? (b.dataset.print || null) : null,
      line: line ? (line.firstChild && line.firstChild.nodeType === 3 ? (line.firstChild.textContent || "") : line.textContent) : null, buttons: btns.map((x) => x.textContent || ""), titles: btns.map((x) => x.title),
      cardUp: !!document.getElementById("romp-fileview"), lines: document.querySelectorAll("#romp-fileview .fileview-print-line").length };
  };
};
const bar = (page: any): Promise<Bar> => page.evaluate(() => (window as any).__bar());
const prints = (page: any): Promise<Print[]> => page.evaluate(() => (window as any).__prints);
const keys = (page: any): Promise<Key[]> => page.evaluate(() => (window as any).__keys);
const chords = (page: any): Promise<Key[]> => keys(page).then((ks) => ks.filter((x) => x.key.toLowerCase() === "p" && x.ctrl));
const active = (page: any): Promise<string> => page.evaluate(() => (window as any).__active());
const printsReach = (page: any, n: number, timeout = 10000): Promise<unknown> => page.waitForFunction((k: number) => (window as any).__prints.length >= k, n, { timeout });
const nowOnPage = (page: any): Promise<number> => page.evaluate(() => performance.now());
const pause = (page: any, ms: number): Promise<void> => page.evaluate((k: number) => new Promise<void>((r) => setTimeout(r, k)), ms);   // a timer, where the timing itself is what is measured
const PRINT_BTN = "#romp-fileview .fileview-print";
const WITHOUT_BTN = '#fileview-print-line button:has-text("Print without them")';
const WITH_BTN = '#fileview-print-line button:has-text("Print with them")';

type Scene = { page: any; errors: string[]; requests: string[]; release: (names?: string[]) => Promise<void>; heldCount: (name?: string) => number; requestsFor: (name: string) => number };
/** The viewer over `note`: the quick picture answered from the origin's route, each of `held` parked (its route held until
 *  release()), each of `missing` answered 404 (a picture the kernel does not have), every remote host answered after a short
 *  delay so a print that waited can be told from one that did not, and the probes installed before the open. `before` runs
 *  before the open too, after the probes. `requestsFor(name)` counts the requests the page made for the picture so far. */
async function scene(browser: any, mode: Mode, note: string, opts: { held?: string[]; missing?: string[]; before?: (pg: any) => Promise<void>; waitFor?: string } = {}): Promise<Scene> {
  const heldNames = opts.held || [];
  const missing = opts.missing || [];
  const held: Array<{ name: string; route: any }> = [];
  const requests: string[] = [];
  const { page, errors } = await openViewer(browser, mode, 900, 700, {
    docs: { [REPORT]: note }, waitFor: opts.waitFor,
    serve: (u) => {
      const p = u.searchParams.get("path") || "";
      if (u.pathname !== "/file") return null;
      if (p.endsWith(QUICK)) return { status: 200, type: "image/svg+xml", body: SVG };
      if (missing.some((n) => p.endsWith(n))) return { status: 404, type: "text/plain", body: "no such file: " + p };   // the kernel's 404 for a picture it does not have
      return null;
    },
    before: async (pg: any) => {
      pg.on("request", (r: any) => { requests.push(r.url()); });
      await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/file" && heldNames.some((n) => (u.searchParams.get("path") || "").endsWith(n)), (route: any) => {
        const p = new URL(route.request().url()).searchParams.get("path") || "";
        held.push({ name: heldNames.find((n) => p.endsWith(n))!, route });
      });
      for (const h of REMOTE_HOSTS) await pg.route("https://" + h + "/**", async (route: any) => { await new Promise((r) => setTimeout(r, 200)); await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); });
      await pg.evaluate(PAGE_PROBES);
      if (opts.before) await opts.before(pg);
    },
  });
  await frames(page, 2);
  return {
    page, errors, requests,
    heldCount: (name?: string) => held.filter((h) => !name || h.name === name).length,
    requestsFor: (name: string) => requests.filter((u) => u.startsWith(ORIGIN) && decodeURIComponent(u).includes("/docs/" + name)).length,
    release: async (names?: string[]) => {
      const out = held.filter((h) => !names || names.includes(h.name));
      for (const h of out) { held.splice(held.indexOf(h), 1); await h.route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); }
    },
  };
}
/** Wait until every named picture's request is parked and the quick picture is complete. */
async function parked(s: Scene, names: string[]): Promise<void> {
  await s.page.waitForFunction(() => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).some((i) => i.complete && i.naturalWidth > 0) || document.querySelectorAll("#romp-fileview img").length === 0, null, { timeout: 10000 });
  for (let i = 0; i < 100 && names.some((n) => s.heldCount(n) === 0); i++) await frames(s.page, 1);
  for (const n of names) assert.equal(s.heldCount(n), 1, "the request for " + n + " is parked");
}
const gatesOnPage = (page: any): Promise<number> => page.evaluate(() => document.querySelectorAll('[data-act="fv-load"]').length);
const waitGates = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => document.querySelectorAll('[data-act="fv-load"]').length === k, n, { timeout: 10000 });

// ── under node: the predicates and the words ───────────────────────────────────────────────────────

test("the chord's keys and the chord as a press: a repeat is the keys and not a press; the with-button's title lists the hosts", () => {
  assert.equal(isPrintKeys({ key: "p", ctrlKey: true, repeat: true }), true, "a held chord's repeat is still the chord's keys: the driver prevents it");
  assert.equal(isPrintKeys({ key: "P", metaKey: true }), true);
  assert.equal(isPrintKeys({ key: "p", ctrlKey: true, shiftKey: true }), false);
  assert.equal(isPrintKeys({ key: "p", ctrlKey: true, altKey: true }), false);
  assert.equal(isPrintKeys({ key: "p" }), false);
  assert.equal(isPrintChord({ key: "p", ctrlKey: true, repeat: true }), false, "…and is not a press");
  assert.equal(isPrintChord({ key: "p", ctrlKey: true }), true);
  assert.equal(withTitle([]), "Load the pictures from those hosts, then print");
  assert.equal(withTitle(["other.test"]), "Load the pictures from other.test, then print");
  assert.equal(withTitle(["a.test", "b.test"]), "Load the pictures from a.test and b.test, then print");
  assert.equal(withTitle(["a.test", "b.test", "c.test"]), "Load the pictures from a.test, b.test and c.test, then print");
  assert.equal(WITHOUT_TITLE, "Print with their placeholders as they are");
  assert.ok(OWN_ESCAPE_SEL.includes('[role="menu"]') && OWN_ESCAPE_SEL.includes('[role="dialog"]'), "a menu and a dialog own their Escape");
});

test("the shell's palette claims Mod+P on every pane document ahead of the flow: the binding and the dispatcher's wiring, read from their sources (the stand-in below mirrors them)", () => {
  assert.equal(DEFAULT_CHORDS["palette.toggle"], "Mod+P", "the binding the palette owns");
  const src = fs.readFileSync(path.join(UI, "palette-main.ts"), "utf8");
  assert.ok(src.includes('document.addEventListener("keydown", onKey, true);'), "a capture-phase listener on the shell document");
  assert.ok(src.includes('f.contentDocument.addEventListener("keydown", onKey, true);'), "…and on every pane document");
  assert.ok(src.includes('"f-files"') && src.includes('"f-chat"'), "the Files and chat panes among them");
  const onKey = src.slice(src.indexOf("function onKey(e: KeyboardEvent): void {"));
  assert.ok(onKey.slice(0, onKey.indexOf("\n  }")).includes("e.preventDefault(); e.stopPropagation();"), "the dispatcher prevents the chord it runs, which is what the flow reads (defaultPrevented)");
  assert.ok(onKey.includes("if (!dispatchable(e, isTyping(e.target))) return;") && onKey.includes("const ch = chordOf(e);"), "through keybindings.ts's dispatchable and chordOf, the predicates the stand-in uses");
});

// ── (1) the held chord ─────────────────────────────────────────────────────────────────────────────

test("(1) a held Ctrl+P: the first keydown is prevented and arms, every repeat is prevented and is not a press (the bar stays armed, nothing prints); a synthetic repeat at rest is prevented and changes nothing", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", GATED_NOTE, { held: [SLOW] });
    const { page } = s;
    await waitGates(page, 1); await parked(s, [SLOW]);
    // a repeat at rest, dispatched as the browser dispatches it (repeat true, cancelable): prevented, no press
    const rest = await page.evaluate(() => {
      const ev = new KeyboardEvent("keydown", { key: "p", ctrlKey: true, repeat: true, bubbles: true, cancelable: true });
      const prevented = !document.body.dispatchEvent(ev);
      const meta = new KeyboardEvent("keydown", { key: "p", metaKey: true, repeat: true, bubbles: true, cancelable: true });
      const preventedMeta = !document.body.dispatchEvent(meta);
      return { prevented, preventedMeta, bar: (window as any).__bar() };
    });
    assert.equal(rest.prevented, true, "a Ctrl+P repeat with a file open is prevented (the browser's default for it is its own print)");
    assert.equal(rest.preventedMeta, true, "a Cmd+P repeat too");
    assert.equal(rest.bar.phase, null, "…and is not a press: the bar stays at rest"); assert.equal(rest.bar.line, null);
    assert.equal((await prints(page)).length, 0);
    // a held chord: Playwright marks the later downs of a pressed key as repeats
    await page.keyboard.down("Control");
    await page.keyboard.down("p"); await page.keyboard.down("p"); await page.keyboard.down("p");
    await page.keyboard.up("p"); await page.keyboard.up("Control");
    await frames(page, 1);
    const k = (await chords(page)).slice(2);   // after the two synthetic repeats dispatched above, which the window heard too
    assert.equal(k.length, 3, "the window heard three keydowns of P with Control held");
    assert.deepEqual(k.map((x) => x.repeat), [false, true, true], "the second and third are repeats");
    assert.deepEqual(k.map((x) => x.prevented), [true, true, true], "every one is prevented: the browser's own print never runs from a held chord");
    let b = await bar(page);
    assert.equal(b.phase, "armed", "the first keydown armed; the repeats did not disarm (no flapping)");
    assert.equal(b.lines, 1); assert.equal(b.line, "1 picture from another host is not loaded.");
    assert.equal((await prints(page)).length, 0, "nothing printed");
    // released and pressed again: a press, which disarms
    await page.keyboard.press("Control+p");
    b = await bar(page);
    assert.equal(b.phase, null, "a fresh chord is a press: the second press disarms"); assert.equal(b.cardUp, true);
    assert.ok(!s.requests.some((u) => u.indexOf("https://" + REMOTE_HOST + "/") === 0), "no request reached the other host");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (2) a claimant ahead of the flow ───────────────────────────────────────────────────────────────

let kbBundle: string | null = null;
/** keybindings.ts and commands.ts as the palette reads them, bundled for the page as window.KB. */
function keybindingsBundle(): string {
  if (kbBundle) return kbBundle;
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'export { chordOf, dispatchable, resolveChord } from "./keybindings"; export { DEFAULT_CHORDS } from "./commands";', resolveDir: UI, loader: "ts", sourcefile: "file-print-driver-browser.test.ts" },
    bundle: true, write: false, format: "iife", globalName: "KB", platform: "browser", target: "es2020", logLevel: "silent",
  });
  kbBundle = r.outputFiles[0].text as string;
  return kbBundle;
}
/** The palette dispatcher's stand-in on this document: palette-main.ts onKey's decision (dispatchable, chordOf against the
 *  palette's binding) and its two calls, on a capture-phase listener registered BEFORE the viewer opens, as the shell wires
 *  the real one at the frame's load. `stop` false leaves out the dispatcher's stopPropagation, so the window's recorder hears
 *  the key and the flow's stand-down is shown to read defaultPrevented alone. Counts its claims in window.__palette (which the
 *  record keeps across stand-ins) and what it saw in window.__seen; window.__unclaim removes it. */
const CLAIMANT = (stop: boolean) => {
  const w = window as any; const KB = w.KB;
  w.__palette = w.__palette || 0;
  const isTyping = (t: EventTarget | null): boolean => { const el = t as HTMLElement | null; return !!el && !!el.closest && !!el.closest("input, textarea, select, [contenteditable=true]"); };
  const want = KB.resolveChord(KB.DEFAULT_CHORDS["palette.toggle"], false);
  w.__seen = [];
  const onKey = (e: KeyboardEvent): void => {
    const d = KB.dispatchable(e, isTyping(e.target)), ch = KB.chordOf(e);
    w.__seen.push({ key: e.key, repeat: e.repeat, d, ch, want, target: (e.target as Element | null)?.tagName || null });
    if (!d || ch !== want) return;
    e.preventDefault(); if (stop) e.stopPropagation();
    w.__palette++;
  };
  document.addEventListener("keydown", onKey, true);
  w.__unclaim = () => { document.removeEventListener("keydown", onKey, true); };
};

test("(2) with the palette's dispatcher ahead of it on the document, Ctrl+P with a file open is the palette's alone: the flow stands down on the prevented key and nothing prints, whether or not the claimant also stops the event; the claimant removed, the same chord prints", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", PLAIN_NOTE, { before: async (pg: any) => { await pg.addScriptTag({ content: keybindingsBundle() }); await pg.evaluate(CLAIMANT, true); } });
    const { page } = s;
    await page.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview img")).every((i: any) => i.complete), null, { timeout: 10000 });
    const seen = (): Promise<string> => page.evaluate(() => JSON.stringify((window as any).__seen));
    // the dispatcher's own shape: preventDefault and stopPropagation at the document's capture phase
    await page.keyboard.press("Control+p");
    await frames(page, 1);
    let claims = await page.evaluate(() => (window as any).__palette);
    assert.equal(claims, 1, "the palette's stand-in claimed the chord (it saw: " + await seen() + ")");
    let k = await chords(page);
    assert.equal(k.length, 0, "the claimant stopped the event at the document's capture phase, as the palette's dispatcher does, so the window's recorder never heard it");
    assert.equal((await prints(page)).length, 0, "the flow stood down: one keystroke does not open the palette and print");
    let b = await bar(page);
    assert.equal(b.phase, null, "the bar is at rest"); assert.equal(b.line, null);
    // the button is the way to print in the shell
    await page.click(PRINT_BTN);
    assert.equal((await prints(page)).length, 1, "the Print button prints under the palette's claim");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // preventDefault alone (no stopPropagation), wired before the open as the shell wires its dispatcher at the frame's load
    // (same-target listeners run in registration order, so a claimant installed after the open would run after the flow's):
    // the window hears the key, prevented, and the flow stands down on defaultPrevented alone
    const s2 = await scene(browser, "pane", PLAIN_NOTE, { before: async (pg: any) => { await pg.addScriptTag({ content: keybindingsBundle() }); await pg.evaluate(CLAIMANT, false); } });
    const page2 = s2.page;
    await page2.waitForFunction(() => Array.from(document.querySelectorAll("#romp-fileview img")).every((i: any) => i.complete), null, { timeout: 10000 });
    await page2.keyboard.press("Control+p");
    await frames(page2, 1);
    claims = await page2.evaluate(() => (window as any).__palette);
    assert.equal(claims, 1, "the stand-in claimed the chord (it saw: " + await page2.evaluate(() => JSON.stringify((window as any).__seen)) + ")");
    k = await chords(page2);
    assert.equal(k.length, 1, "the window heard this one: nothing stopped it"); assert.equal(k[0].prevented, true, "prevented by the claimant"); assert.equal(k[0].open, true);
    assert.equal((await prints(page2)).length, 0, "the flow stood down on defaultPrevented alone: nothing printed");
    assert.equal((await bar(page2)).phase, null);
    // the claimant gone, the chord is the flow's again
    await page2.evaluate(() => { (window as any).__unclaim(); });
    await page2.keyboard.press("Control+p");
    await frames(page2, 1);
    claims = await page2.evaluate(() => (window as any).__palette);
    assert.equal(claims, 1, "no further claim");
    k = await chords(page2);
    assert.equal(k.length, 2); assert.equal(k[1].prevented, true, "prevented by the flow");
    assert.equal((await prints(page2)).length, 1, "…which printed");
    assert.equal((await bar(page2)).phase, null);
    assert.deepEqual(s2.errors, [], "no script error");
    await page2.close();
  });
});

// ── (3) a repaint during the wait ──────────────────────────────────────────────────────────────────

/** Change the file on disk and raise the changed-on-disk bar through the viewer's own probe (a window focus runs one HEAD, whose
 *  moved mtime raises the bar), then click its Reload. */
async function reloadTo(page: any, note: string): Promise<void> {
  await page.evaluate(([p, n, mt]: [string, string, string]) => { const w = window as any; w.__docs[p] = n; w.__mtime = mt; }, [REPORT, note, MT2]);
  await page.evaluate(() => { window.dispatchEvent(new Event("focus")); });
  await page.waitForFunction(() => { const b = document.querySelector("#fileview-save-err button") as HTMLButtonElement | null; return !!b && b.textContent === "Reload"; }, null, { timeout: 10000 });
  assert.equal(await page.evaluate(() => (document.getElementById("fileview-save-err")!.firstChild!.textContent || "")), "Changed on disk.", "the bar says the file moved");
  await page.click("#fileview-save-err button");
}

test("(3) a Reload landing during the wait re-aims it: a picture the new body brings is awaited (the old body's picture landing prints nothing), the line's count follows, and the print fires with every picture of the body complete; a landing with nothing loading prints at once; the re-aim runs under the press's deadline, never a restarted one: with the landing's picture parked too the ask comes at the press's deadline", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a: the landing brings a new slow picture
    let s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW, SLOW2] });
    let { page } = s;
    await parked(s, [SLOW]);
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "preparing"); assert.equal(b.line, "Preparing 1 picture…", "the slow picture is loading");
    await reloadTo(page, SLOW2_NOTE);
    await page.waitForFunction((n: string) => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).some((i) => decodeURIComponent(i.src).includes("/docs/" + n)), SLOW2, { timeout: 10000 });   // the rewritten src carries the sid after the path
    for (let i = 0; i < 100 && s.heldCount(SLOW2) === 0; i++) await frames(page, 1);
    assert.equal(s.heldCount(SLOW2), 1, "the new body's slow picture is requested and parked");
    assert.equal(s.heldCount(SLOW), 1, "the old body's slow picture is still parked too");
    await frames(page, 2);
    b = await bar(page);
    assert.equal(b.phase, "preparing", "the wait goes on over the new body"); assert.equal(b.line, "Preparing 1 picture…", "one picture loading in the new body");
    assert.equal((await prints(page)).length, 0);
    // the OLD body's picture lands: its element is detached, and the re-aimed wait does not listen on it
    await s.release([SLOW]);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "no print: the picture that landed is not in the body, and the one in the body is still loading");
    assert.equal((await bar(page)).phase, "preparing");
    // the new body's picture lands: the print
    await s.release([SLOW2]);
    await printsReach(page, 1);
    let p = await prints(page);
    assert.equal(p.length, 1);
    assert.deepEqual(p[0].incomplete, [], "window.print fired with every <img> of the body complete");
    assert.equal(p[0].line, false);
    assert.equal(await page.evaluate(() => !!document.getElementById("fileview-save-err")), false, "the changed-on-disk bar went at the landing");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // b: the landing brings a body with nothing loading: the print runs at the landing, the old picture still parked
    s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW] });
    page = s.page;
    await parked(s, [SLOW]);
    await page.click(PRINT_BTN);
    assert.equal((await bar(page)).phase, "preparing");
    await reloadTo(page, PLAIN_NOTE);
    await printsReach(page, 1);
    p = await prints(page);
    assert.equal(p.length, 1, "the landing left nothing to wait on: the print ran at once");
    assert.deepEqual(p[0].incomplete, []);
    assert.equal(s.heldCount(SLOW), 1, "the old body's picture never landed: nothing waited for it");
    assert.equal(await page.evaluate(() => document.querySelectorAll("#romp-fileview img").length), 1, "the new body's one picture");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null);
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // c: the landing's picture is parked too, so the re-aimed wait runs to the deadline: the ask comes at the PRESS's deadline
    // (the seam's 2000 ms from the press), not at one restarted at the landing (which would read about 2000 ms after it)
    s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW, SLOW2] });
    page = s.page;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(2000); });
    await page.click(PRINT_BTN);
    const t0 = await nowOnPage(page);
    assert.equal((await bar(page)).phase, "preparing");
    await pause(page, 600);
    await reloadTo(page, SLOW2_NOTE);
    await page.waitForFunction((n: string) => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).some((i) => decodeURIComponent(i.src).includes("/docs/" + n)), SLOW2, { timeout: 10000 });
    for (let i = 0; i < 100 && s.heldCount(SLOW2) === 0; i++) await frames(page, 1);
    const tLand = await nowOnPage(page);
    assert.equal(s.heldCount(SLOW2), 1, "the landing's picture is parked");
    assert.ok(tLand - t0 >= 550 && tLand - t0 < 1500, "the landing came mid-wait (" + Math.round(tLand - t0) + " ms after the press)");
    b = await bar(page);
    assert.equal(b.phase, "preparing", "the wait goes on over the landing's picture"); assert.equal(b.line, "Preparing 1 picture…");
    assert.equal((await prints(page)).length, 0);
    await page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, stalledWords(1), { timeout: 6000 });
    const t2 = await nowOnPage(page);
    assert.ok(t2 - t0 >= 1900 && t2 - t0 < 3000, "the ask came at the press's deadline (" + Math.round(t2 - t0) + " ms after the press)");
    assert.ok(t2 - tLand < 1600, "…not at a deadline restarted at the landing (" + Math.round(t2 - tLand) + " ms after it; a restart would read about 2000)");
    t.diagnostic("case 3c: the landing " + Math.round(tLand - t0) + " ms after the press; the ask " + Math.round(t2 - t0) + " ms after the press and " + Math.round(t2 - tLand) + " ms after the landing (seam 2000 ms)");
    b = await bar(page);
    assert.equal(b.phase, "stalled"); assert.deepEqual(b.buttons, [ANYWAY_WORDS, KEEP_WORDS]);
    assert.equal((await prints(page)).length, 0, "nothing printed at the deadline: the bar asked");
    await page.click('#fileview-print-line button:has-text("' + ANYWAY_WORDS + '")');
    p = await prints(page);
    assert.equal(p.length, 1, "Print anyway printed once");
    assert.equal(p[0].incomplete.length, 1, "the landing's picture is the one still loading at the print");
    assert.ok(decodeURIComponent(p[0].incomplete[0]).includes("/docs/" + SLOW2));
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (4) the close ──────────────────────────────────────────────────────────────────────────────────

test("(4) a close during the wait: the parked picture landing after it prints nothing; a close while armed leaks no listener (the reopened card's first Escape closes it); the chord after several opens presses once", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", GATED_NOTE, { held: [SLOW] });
    const { page } = s;
    await waitGates(page, 1); await parked(s, [SLOW]);
    await page.click(PRINT_BTN);
    await page.click(WITHOUT_BTN);
    assert.equal((await bar(page)).phase, "preparing");
    // Escape during the wait: the flow leaves it alone (only the armed line takes Escape) and the viewer closes the card
    await page.keyboard.press("Escape");
    await frames(page, 1);
    assert.equal((await bar(page)).cardUp, false, "the viewer closed on Escape during the wait");
    await s.release([SLOW]);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "the picture landed after the close and nothing printed");
    // reopen, arm, close while armed, reopen: the first Escape closes the card (a leaked armed listener would stop it)
    const reopen = async (): Promise<void> => {
      await page.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
      await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-md > p") && !!document.querySelector('[data-act="fv-load"]'), null, { timeout: 10000 });
      await frames(page, 2);
    };
    await reopen();
    await page.click(PRINT_BTN);
    assert.equal((await bar(page)).phase, "armed");
    await page.evaluate(() => { (window as any).FV.closeFileView(); });
    await frames(page, 1);
    assert.equal((await bar(page)).cardUp, false);
    await reopen();
    assert.equal((await bar(page)).phase, null, "the reopened card's flow starts at rest");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    assert.equal((await bar(page)).cardUp, false, "the first Escape closed the reopened card: no listener leaked from the close while armed");
    // three more opens and closes, then the chord: one press (one line, armed once), and one disarm
    for (let i = 0; i < 3; i++) { await reopen(); await page.evaluate(() => { (window as any).FV.closeFileView(); }); await frames(page, 1); }
    await reopen();
    await page.keyboard.press("Control+p");
    let b = await bar(page);
    assert.equal(b.phase, "armed"); assert.equal(b.lines, 1, "one line: one listener pressed");
    await page.keyboard.press("Control+p");
    b = await bar(page);
    assert.equal(b.phase, null, "the second chord disarmed"); assert.equal(b.cardUp, true);
    assert.equal((await prints(page)).length, 0);
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (5) a press during the wait ────────────────────────────────────────────────────────────────────

test("(5) a press and the chord during the wait change nothing over the driver: the phase and the line stand, the chord is prevented, and the ask comes at the press's deadline, not a deadline restarted at the second press; Print anyway then prints once, the parked picture still loading", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", GATED_NOTE, { held: [SLOW] });
    const { page } = s;
    await waitGates(page, 1); await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(1500); });
    await page.click(PRINT_BTN);
    const t0 = await nowOnPage(page);
    await page.click(WITHOUT_BTN);
    assert.equal((await bar(page)).phase, "preparing");
    await pause(page, 700);
    await page.click(PRINT_BTN);
    await page.keyboard.press("Control+p");
    const t1 = await nowOnPage(page);
    assert.ok(t1 - t0 >= 650 && t1 - t0 < 1300, "the second press came mid-wait (" + Math.round(t1 - t0) + " ms after the choice)");
    let b = await bar(page);
    assert.equal(b.phase, "preparing", "the press during the wait changed nothing"); assert.equal(b.line, "Preparing 1 picture…"); assert.equal(b.lines, 1);
    const k = await chords(page);
    assert.equal(k.length, 1); assert.equal(k[0].prevented, true, "the chord during the wait is still prevented");
    assert.equal((await prints(page)).length, 0, "no print before the deadline");
    await page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, stalledWords(1), { timeout: 5000 });
    const t2 = await nowOnPage(page);
    assert.ok(t2 - t0 >= 1400 && t2 - t0 < 2400, "the ask came at the press's deadline (" + Math.round(t2 - t0) + " ms after the choice)");
    assert.ok(t2 - t1 < 1300, "…not at a deadline restarted at the second press (" + Math.round(t2 - t1) + " ms after it; a restart would read about 1500)");
    b = await bar(page);
    assert.equal(b.phase, "stalled"); assert.equal(b.lines, 1);
    assert.deepEqual(b.buttons, [ANYWAY_WORDS, KEEP_WORDS], "the ask's two choices"); assert.deepEqual(b.titles, [ANYWAY_TITLE, KEEP_TITLE], "each with its title");
    assert.equal((await prints(page)).length, 0, "nothing printed at the deadline: the bar asked");
    await page.click('#fileview-print-line button:has-text("' + ANYWAY_WORDS + '")');
    const p = await prints(page);
    assert.equal(p.length, 1, "exactly one print, at the answer");
    assert.equal(p[0].gates, 1); assert.equal(p[0].incomplete.length, 1, "the parked picture is still loading at the print: the press leaves it out, as its line said");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "the bar rested");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (6) the poster and the svg image in the real DOM ───────────────────────────────────────────────

test("(6) a <video poster> and an svg <image href> in the real DOM: the press waits on both through the probes and prints once after both land; no request to another host", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", MEDIA_NOTE, { held: [POSTER, IMAGE] });
    const { page } = s;
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview video[poster]") && !!document.querySelector("#romp-fileview image"), null, { timeout: 10000 });
    await parked(s, [POSTER, IMAGE]);
    const attrs = await page.evaluate(() => ({ poster: decodeURIComponent(document.querySelector("#romp-fileview video")!.getAttribute("poster") || ""), href: decodeURIComponent(document.querySelector("#romp-fileview image")!.getAttribute("href") || ""), imgs: document.querySelectorAll("#romp-fileview img").length }));
    assert.ok(attrs.poster.includes("/file?path=" + ROOT + "/docs/" + POSTER), "the viewer left the poster's URL in `poster`, at the kernel's /file route: " + attrs.poster);
    assert.ok(attrs.href.includes("/file?path=" + ROOT + "/docs/" + IMAGE), "…and the svg image's in `href`: " + attrs.href);
    assert.equal(attrs.imgs, 0, "no <img> in this body: the two probes are the whole wait");
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "preparing", "the press waits"); assert.equal(b.line, "Preparing 2 pictures…", "both probes are loading");
    await frames(page, 3);
    assert.equal((await prints(page)).length, 0, "no print while they load");
    const heldBefore = s.heldCount();
    assert.ok(heldBefore >= 2, "the two parked requests (the probes join them, or are parked beside them): " + heldBefore);
    await s.release();
    await printsReach(page, 1);
    const p = await prints(page);
    assert.equal(p.length, 1, "one print after both landed");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null); assert.equal(b.line, null);
    const foreign = s.requests.filter((u) => !u.startsWith(ORIGIN));
    assert.deepEqual(foreign, [], "every request went to the page's origin");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (7) Escape inside the Outline popover ──────────────────────────────────────────────────────────

test("(7) Escape from inside the Outline popover while the bar is armed closes the popover and puts the keyboard back on its button, the bar still armed; the next Escape disarms; at rest the popover's Escape is untouched", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const mode of ["chat", "pane"] as Mode[]) {
      const s = await scene(browser, mode, HEADED_GATED);
      const { page } = s;
      await waitGates(page, 1);
      await page.waitForFunction(() => { const b = document.querySelector("#romp-fileview .fileview-outline-btn") as HTMLElement | null; return !!b && !b.hidden; }, null, { timeout: 10000 });
      // control, at rest: the popover's own Escape
      await page.click("#romp-fileview .fileview-outline-btn");
      await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-outline"), null, { timeout: 5000 });
      assert.equal(await active(page), "DIV.fileview-outline", mode + ": the popover holds the keyboard");
      await page.keyboard.press("Escape");
      await frames(page, 1);
      assert.equal(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-outline")), false, mode + ": at rest, Escape closed the popover");
      assert.equal(await active(page), "BUTTON.fileview-btn.fileview-outline-btn[Outline]", mode + ": …and the keyboard is back on the Outline button");
      assert.equal((await bar(page)).cardUp, true, mode + ": the card stays up (the popover stopped the Escape)");
      // armed, then the popover
      await page.click(PRINT_BTN);
      let b = await bar(page);
      assert.equal(b.phase, "armed", mode + ": armed over the placeholder");
      await page.click("#romp-fileview .fileview-outline-btn");
      await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-outline"), null, { timeout: 5000 });
      assert.equal(await active(page), "DIV.fileview-outline", mode + ": the popover holds the keyboard while the bar is armed");
      assert.equal(await page.evaluate(() => document.querySelector("#romp-fileview .fileview-outline-btn")!.getAttribute("aria-expanded")), "true");
      await page.keyboard.press("Escape");
      await frames(page, 1);
      assert.equal(await page.evaluate(() => !!document.querySelector("#romp-fileview .fileview-outline")), false, mode + ": Escape closed the popover, the control that held the keyboard");
      assert.equal(await page.evaluate(() => document.querySelector("#romp-fileview .fileview-outline-btn")!.getAttribute("aria-expanded")), "false");
      assert.equal(await active(page), "BUTTON.fileview-btn.fileview-outline-btn[Outline]", mode + ": the keyboard is back on the Outline button, the menu-button pattern");
      b = await bar(page);
      assert.equal(b.phase, "armed", mode + ": the bar is still armed"); assert.equal(b.line, "1 picture from another host is not loaded."); assert.equal(b.cardUp, true);
      await page.keyboard.press("Escape");
      await frames(page, 1);
      b = await bar(page);
      assert.equal(b.phase, null, mode + ": the next Escape disarmed"); assert.equal(b.line, null); assert.equal(b.cardUp, true, mode + ": …and the card stays up");
      assert.equal((await prints(page)).length, 0);
      assert.ok(!s.requests.some((u) => u.indexOf("https://" + REMOTE_HOST + "/") === 0), mode + ": no request reached the other host");
      assert.deepEqual(s.errors, [], mode + ": no script error");
      await page.close();
    }
  });
});

// ── (8) the keyboard after the line goes ───────────────────────────────────────────────────────────

test("(8) Escape or Enter on the armed line's word buttons hands the keyboard to the Print button: after Escape, after Enter on Print without them (the wait, then the print) and after Enter on Print with them", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "chat", GATED_NOTE, { held: [SLOW] });
    const { page } = s;
    await waitGates(page, 1); await parked(s, [SLOW]);
    const PRINT_ACTIVE = "BUTTON.fileview-btn.fileview-icon.fileview-print";
    // Escape with a word button focused
    await page.click(PRINT_BTN);
    await page.focus(WITHOUT_BTN);
    assert.equal(await active(page), "BUTTON.fileview-btn.fileview-err-act[Print without them]", "the word button holds the keyboard");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    let b = await bar(page);
    assert.equal(b.phase, null, "disarmed"); assert.equal(b.cardUp, true);
    assert.ok((await active(page)).startsWith(PRINT_ACTIVE), "the keyboard went to the Print button, not the document's body: " + await active(page));
    // Enter on Print without them: the wait begins, the line is replaced, the keyboard is on the button; then the print
    await page.click(PRINT_BTN);
    await page.focus(WITHOUT_BTN);
    await page.keyboard.press("Enter");
    b = await bar(page);
    assert.equal(b.phase, "preparing", "Enter chose: the wait over the slow picture");
    assert.ok((await active(page)).startsWith(PRINT_ACTIVE), "the keyboard is on the Print button through the wait: " + await active(page));
    await s.release([SLOW]);
    await printsReach(page, 1);
    let p = await prints(page);
    assert.ok(p[0].active.startsWith(PRINT_ACTIVE), "…and at the print: " + p[0].active);
    await frames(page, 1);
    assert.ok((await active(page)).startsWith(PRINT_ACTIVE), "…and after it");
    // Enter on Print with them
    await page.click(PRINT_BTN);
    assert.equal((await bar(page)).phase, "armed");
    await page.focus(WITH_BTN);
    await page.keyboard.press("Enter");
    b = await bar(page);
    assert.equal(b.phase, "preparing", "the remote picture is loading");
    assert.ok((await active(page)).startsWith(PRINT_ACTIVE), "the keyboard is on the Print button: " + await active(page));
    await printsReach(page, 2);
    p = await prints(page);
    assert.equal(p.length, 2); assert.deepEqual(p[1].incomplete, []);
    assert.ok(p[1].active.startsWith(PRINT_ACTIVE));
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (9) the hosts in the with-button's title ───────────────────────────────────────────────────────

test("(9) Print with them's title names the hosts the press grants: both hosts of one placeholder (a picture whose source and img are on different hosts), and the hosts of two placeholders; the line counts pictures as before", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    let s = await scene(browser, "chat", TWO_HOST_NOTE);
    let { page } = s;
    await waitGates(page, 1);
    const gate = await page.evaluate(() => { const g = document.querySelector('[data-act="fv-load"]')!; return { hosts: g.getAttribute("data-fv-hosts"), label: (g.querySelector("[data-fv-label]") as HTMLElement).textContent }; });
    assert.equal(gate.hosts, "a.test b.test", "one placeholder naming two hosts");
    assert.equal(gate.label, "Image from a.test and 1 more host. Click to load.", "the placeholder's own label names the first and counts the rest");
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "armed");
    assert.equal(b.line, "1 picture from another host is not loaded.", "the line counts the picture (the contract's words)");
    assert.deepEqual(b.buttons, ["Print with them", "Print without them"]);
    assert.deepEqual(b.titles, ["Load the pictures from a.test and b.test, then print", WITHOUT_TITLE], "the with-button's title names both hosts the press would grant");
    await page.keyboard.press("Escape");
    assert.equal((await bar(page)).phase, null);
    assert.equal(s.requests.filter((u) => !u.startsWith(ORIGIN)).length, 0, "nothing fetched from either host");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    s = await scene(browser, "pane", TWO_GATES_NOTE);
    page = s.page;
    await waitGates(page, 2);
    await page.click(PRINT_BTN);
    b = await bar(page);
    assert.equal(b.line, "2 pictures from other hosts are not loaded.");
    assert.deepEqual(b.titles, ["Load the pictures from " + REMOTE_HOST + " and " + REMOTE2_HOST + ", then print", WITHOUT_TITLE], "the two placeholders' hosts, in the order they appear");
    // and with them grants both: two requests, one print
    await page.click(WITH_BTN);
    assert.equal(await gatesOnPage(page), 0, "both placeholders restored");
    await printsReach(page, 1);
    const p = await prints(page);
    assert.equal(p.length, 1); assert.deepEqual(p[0].incomplete, []);
    const hosts = new Set(s.requests.filter((u) => !u.startsWith(ORIGIN)).map((u) => new URL(u).host));
    assert.deepEqual(Array.from(hosts).sort(), [REMOTE2_HOST, REMOTE_HOST].sort(), "the two hosts were asked, as a click on each placeholder asks");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (10) a poster and an svg image whose routes answer 404: one probe per URL per press ────────────

test("(10) a <video poster> and an svg <image href> whose routes answer 404: one press asks the host for each URL exactly once more and prints at once when both probes have failed, well inside the deadline (FAILS BEFORE: a fresh probe per settle asked hundreds of times per URL over the full 8 s and the bar asked at the deadline); no request to another host", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", MEDIA_NOTE, { missing: [POSTER, IMAGE] });
    const { page } = s;
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview video[poster]") && !!document.querySelector("#romp-fileview image"), null, { timeout: 10000 });
    // the elements' own fetches (the browser asks for a poster and an svg image as it renders them), answered 404
    for (let i = 0; i < 200 && (s.requestsFor(POSTER) === 0 || s.requestsFor(IMAGE) === 0); i++) await frames(page, 1);
    await frames(page, 6);
    const before = { poster: s.requestsFor(POSTER), image: s.requestsFor(IMAGE) };
    assert.ok(before.poster >= 1 && before.image >= 1, "the elements asked for their pictures before the press: " + JSON.stringify(before));
    await frames(page, 6);
    assert.deepEqual({ poster: s.requestsFor(POSTER), image: s.requestsFor(IMAGE) }, before, "…and nothing asks again without a press");
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the product's deadline: nothing shortened it here");
    await page.click(PRINT_BTN);
    const t0 = await nowOnPage(page);
    // the print, or (before the fix) the ask at the deadline
    await page.waitForFunction(() => (window as any).__prints.length >= 1 || /has not loaded|have not loaded/.test(document.getElementById("fileview-print-line")?.firstChild?.textContent || ""), null, { timeout: 20000 });
    const t1 = await nowOnPage(page);
    const asked = { poster: s.requestsFor(POSTER) - before.poster, image: s.requestsFor(IMAGE) - before.image };
    assert.equal(asked.poster, 1, "FAILS BEFORE: the press asked the host for the poster " + asked.poster + " times over " + Math.round(t1 - t0) + " ms (one probe per URL for the life of the press)");
    assert.equal(asked.image, 1, "FAILS BEFORE: the press asked the host for the svg image " + asked.image + " times over " + Math.round(t1 - t0) + " ms");
    const p = await prints(page);
    assert.equal(p.length, 1, "FAILS BEFORE: the bar asked at the deadline instead of printing (line: " + (await bar(page)).line + ")");
    assert.ok(t1 - t0 < 2000, "the print came " + Math.round(t1 - t0) + " ms after the press, well inside the 8 s deadline");
    t.diagnostic("case 10: requests after the press: poster " + asked.poster + ", svg image " + asked.image + "; the print " + Math.round(t1 - t0) + " ms after the press");
    assert.equal(p[0].line, false, "the preparing line went before the print");
    await frames(page, 6);
    assert.deepEqual({ poster: s.requestsFor(POSTER) - before.poster, image: s.requestsFor(IMAGE) - before.image }, { poster: 1, image: 1 }, "nothing asked again after the print");
    assert.equal((await bar(page)).phase, null, "the bar rested");
    // a second press asks once more per URL: the probes are the press's, and the next press reads the body afresh
    await page.click(PRINT_BTN);
    await printsReach(page, 2);
    await frames(page, 6);
    assert.deepEqual({ poster: s.requestsFor(POSTER) - before.poster, image: s.requestsFor(IMAGE) - before.image }, { poster: 2, image: 2 }, "the second press probed each URL once more");
    const foreign = s.requests.filter((u) => !u.startsWith(ORIGIN));
    assert.deepEqual(foreign, [], "every request went to the page's origin");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (11) a lazy picture far below the fold ─────────────────────────────────────────────────────────

test("(11) an <img loading=\"lazy\"> far below the fold is not requested until the press, which sets it eager: its fetch starts at once, the wait runs over it and the print follows its load (FAILS BEFORE: nothing started the deferred fetch, the wait ran to its deadline and the bar asked); the attribute reads eager after; no request to another host", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", LAZY_NOTE, { held: [LAZY] });
    const { page } = s;
    const lazy = (): Promise<{ present: boolean; loading: string | null; complete: boolean; below: number }> => page.evaluate((n: string) => {
      const img = (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).find((i) => decodeURIComponent(i.src).includes("/docs/" + n)) || null;
      const body = document.querySelector("#romp-fileview .fileview-body")!;
      return { present: !!img, loading: img ? img.getAttribute("loading") : null, complete: !!img && img.complete, below: img ? Math.round(img.getBoundingClientRect().top - body.getBoundingClientRect().bottom) : -1 };
    }, LAZY);
    await page.waitForFunction((n: string) => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).some((i) => decodeURIComponent(i.src).includes("/docs/" + n)), LAZY, { timeout: 10000 });
    await frames(page, 10);
    let l = await lazy();
    assert.equal(l.loading, "lazy", "the sanitizer kept the attribute");
    assert.ok(l.below > 5000, "the picture stands far below the body's bottom edge (" + l.below + " px)");
    assert.equal(l.complete, false, "the browser has not started its fetch");
    assert.equal(s.heldCount(LAZY), 0, "no request for the lazy picture before the press: the browser deferred it");
    await page.click(PRINT_BTN);
    const t0 = await nowOnPage(page);
    let b = await bar(page);
    assert.equal(b.phase, "preparing", "the press waits on the picture"); assert.equal(b.line, "Preparing 1 picture…");
    for (let i = 0; i < 120 && s.heldCount(LAZY) === 0; i++) await frames(page, 1);
    const t1 = await nowOnPage(page);
    assert.equal(s.heldCount(LAZY), 1, "FAILS BEFORE: the press started the deferred fetch (" + Math.round(t1 - t0) + " ms after it); before, nothing did and the wait ran to its deadline");
    l = await lazy();
    assert.equal(l.loading, "eager", "the picture reads eager now");
    assert.equal((await prints(page)).length, 0, "no print while it loads");
    await s.release([LAZY]);
    await printsReach(page, 1);
    const t2 = await nowOnPage(page);
    const p = await prints(page);
    assert.equal(p.length, 1, "one print, at the picture's load");
    assert.deepEqual(p[0].incomplete, [], "window.print fired with every <img> of the body complete");
    assert.ok(t2 - t0 < 4000, "the print came " + Math.round(t2 - t0) + " ms after the press, inside the 8 s deadline");
    t.diagnostic("case 11: the deferred fetch started " + Math.round(t1 - t0) + " ms after the press; the print " + Math.round(t2 - t0) + " ms after it");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "the bar rested");
    assert.equal((await lazy()).loading, "eager", "the attribute stays eager after the print");
    assert.deepEqual(s.requests.filter((u) => !u.startsWith(ORIGIN)), [], "every request went to the page's origin");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (12) the settle's re-aim under the press's deadline ────────────────────────────────────────────

test("(12) the settle's re-aim runs under the press's deadline, never a restarted one: a second parked picture inserted inside the rendered root mid-wait (a grandchild of the body, so the observer of the body's children is silent and no repaint re-aim runs), then the first released, which settles the wait and the settle's re-aim finds the second; the line still reads one picture with no print, and the ask comes at the press's deadline under a 2000 ms seam, not one restarted at the settle; Print anyway then prints once with the inserted picture still loading", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW, SLOW2] });
    const { page } = s;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(2000); });
    await page.click(PRINT_BTN);
    const t0 = await nowOnPage(page);
    let b = await bar(page);
    assert.equal(b.phase, "preparing"); assert.equal(b.line, "Preparing 1 picture…", "the slow picture is loading");
    await pause(page, 600);
    // a second parked picture, inserted inside the rendered root: a child of `.fileview-md`, a grandchild of the body, so the
    // flow's observer of the body's CHILDREN (P7) does not see it and no repaint re-aim runs; the settle's re-aim is the one
    // that finds it. Its URL is the one the viewer's rewrite gave the first picture, the name changed: the same route and shape
    const ins = await page.evaluate(([a, c]: [string, string]) => {
      const body = document.querySelector("#romp-fileview .fileview-body")!;
      const md = body.querySelector(".fileview-md")!;
      const first = (Array.from(md.querySelectorAll("img")) as HTMLImageElement[]).find((i) => decodeURIComponent(i.src).includes("/docs/" + a))!;
      const img = document.createElement("img");
      img.src = first.src.replace(a, c); img.alt = "";
      md.appendChild(img);
      return { grandchild: img.parentElement === md && md.parentElement === body, src: decodeURIComponent(img.src), imgs: body.querySelectorAll("img").length };
    }, [SLOW, SLOW2]);
    assert.equal(ins.grandchild, true, "the inserted picture is a child of the rendered root and a grandchild of the body");
    assert.ok(ins.src.includes("/docs/" + SLOW2), "at the kernel's /file route: " + ins.src);
    assert.equal(ins.imgs, 3, "the body's pictures: the quick one, the slow one and the inserted one (the wait line's loader glyph stands in the card, outside the body)");
    for (let i = 0; i < 100 && s.heldCount(SLOW2) === 0; i++) await frames(page, 1);
    const tIns = await nowOnPage(page);
    assert.equal(s.heldCount(SLOW2), 1, "the inserted picture is requested and parked");
    assert.equal(s.heldCount(SLOW), 1, "the first is still parked");
    assert.ok(tIns - t0 >= 550 && tIns - t0 < 1500, "the insertion came mid-wait (" + Math.round(tIns - t0) + " ms after the press)");
    await frames(page, 2);
    b = await bar(page);
    assert.equal(b.phase, "preparing");
    assert.equal(b.line, "Preparing 1 picture…", "the observer was silent: the line still counts the first picture alone (a repaint re-aim would have counted both)"); assert.equal(b.lines, 1);
    assert.equal((await prints(page)).length, 0);
    // the first picture lands: the wait settles, and the settle's re-aim finds the inserted picture still loading
    await s.release([SLOW]);
    const tSettle = await nowOnPage(page);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "no print at the settle: the settle's re-aim found the inserted picture loading");
    b = await bar(page);
    assert.equal(b.phase, "preparing", "the wait goes on over the inserted picture"); assert.equal(b.line, "Preparing 1 picture…"); assert.equal(b.lines, 1, "the line rewritten in place");
    await page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, stalledWords(1), { timeout: 6000 });
    const t2 = await nowOnPage(page);
    assert.ok(t2 - t0 >= 1900 && t2 - t0 < 3000, "the ask came at the press's deadline (" + Math.round(t2 - t0) + " ms after the press)");
    assert.ok(t2 - tSettle < 1600, "…not at a deadline restarted at the settle (" + Math.round(t2 - tSettle) + " ms after it; a restart would read about 2000)");
    t.diagnostic("case 12: the insertion " + Math.round(tIns - t0) + " ms after the press; the settle " + Math.round(tSettle - t0) + " ms after the press; the ask " + Math.round(t2 - t0) + " ms after the press and " + Math.round(t2 - tSettle) + " ms after the settle (seam 2000 ms)");
    b = await bar(page);
    assert.equal(b.phase, "stalled"); assert.deepEqual(b.buttons, [ANYWAY_WORDS, KEEP_WORDS]);
    assert.equal((await prints(page)).length, 0, "nothing printed at the deadline: the bar asked");
    await page.click('#fileview-print-line button:has-text("' + ANYWAY_WORDS + '")');
    const p = await prints(page);
    assert.equal(p.length, 1, "Print anyway printed once");
    assert.equal(p[0].incomplete.length, 1, "the inserted picture is the one still loading at the print");
    assert.ok(decodeURIComponent(p[0].incomplete[0]).includes("/docs/" + SLOW2));
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (13) a repaint under the deadline's ask ────────────────────────────────────────────────────────

const STALLED_ONE = stalledWords(1);   // "1 picture has not loaded. " and then anywayWords(): the count sentence, then the button's own
const STALLED_TWO = stalledWords(2);
const askReached = (page: any): Promise<unknown> => page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, STALLED_ONE, { timeout: 6000 });
const markLine = (page: any): Promise<void> => page.evaluate(() => { document.getElementById("fileview-print-line")!.setAttribute("data-probe", "1"); });
const lineMarked = (page: any): Promise<boolean> => page.evaluate(() => document.getElementById("fileview-print-line")?.getAttribute("data-probe") === "1");

test("(13) a repaint under the deadline's ask never prints: a Reload landing a body with nothing to wait on makes the question moot and the flow rests, nothing printed (FAILS BEFORE: window.print ran with neither button pressed), and the next press prints at once; a landing with two pictures still loading keeps the ask, its count rewritten in place to two; a Raw pick under the ask rests too, nothing printed (FAILS BEFORE: it printed the Raw view)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a: the landing has no picture at all (a landing whose picture merely loads fast is still loading when the observer runs)
    let s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW] });
    let { page } = s;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await askReached(page);
    let b = await bar(page);
    assert.equal(b.phase, "stalled"); assert.deepEqual(b.buttons, [ANYWAY_WORDS, KEEP_WORDS]); assert.equal((await prints(page)).length, 0, "the ask stands, nothing printed");
    await reloadTo(page, NOPIC_NOTE);
    await page.waitForFunction(() => !document.getElementById("fileview-save-err") && !!document.querySelector("#romp-fileview .fileview-md > p") && document.querySelectorAll("#romp-fileview .fileview-body img").length === 0, null, { timeout: 10000 });
    await frames(page, 3);
    b = await bar(page);
    assert.equal((await prints(page)).length, 0, "FAILS BEFORE: the landing under the ask printed with neither button pressed; a repaint is no answer");
    assert.equal(b.phase, null, "the question is moot: the flow rests"); assert.equal(b.line, null, "the line went"); assert.equal(b.cardUp, true);
    const printed = await page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click(); return (window as any).__prints.length; });
    assert.equal(printed, 1, "the next press prints at once: nothing to wait on");
    await s.release([SLOW]);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 1, "the old body's picture landing prints nothing more");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // b: the landing brings two parked pictures: the ask stands with its count rewritten in place
    s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW, SLOW2, SLOW3] });
    page = s.page;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await askReached(page);
    await markLine(page);
    await reloadTo(page, TWO_SLOW_NOTE);
    for (let i = 0; i < 100 && (s.heldCount(SLOW2) === 0 || s.heldCount(SLOW3) === 0); i++) await frames(page, 1);
    assert.equal(s.heldCount(SLOW2) + s.heldCount(SLOW3), 2, "the landing's two pictures are requested and parked");
    await page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, STALLED_TWO, { timeout: 6000 });
    b = await bar(page);
    assert.equal(b.phase, "stalled", "the ask stands"); assert.equal(b.line, STALLED_TWO, "the count follows the landing"); assert.equal(b.lines, 1, "one line");
    assert.equal(await lineMarked(page), true, "the same row: the words rewritten in place, not the line rebuilt");
    assert.deepEqual(b.buttons, [ANYWAY_WORDS, KEEP_WORDS]);
    assert.equal((await prints(page)).length, 0, "nothing printed by the landing");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "Escape under the ask disarms"); assert.equal(b.line, null); assert.equal(b.cardUp, true, "the card stays up");
    await s.release([SLOW, SLOW2, SLOW3]);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "the pictures landing after the disarm print nothing: nothing waits");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // c: a Raw pick under the ask (the chat modal, whose bar carries the Rendered/Raw pair): the rows hold no picture, so the
    // question is moot and the flow rests; the Raw view is not printed
    s = await scene(browser, "chat", SLOW_NOTE, { held: [SLOW] });
    page = s.page;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await askReached(page);
    await page.click('#romp-fileview .fileview-seg button:has-text("Raw")');
    await page.waitForFunction(() => !!document.querySelector("#romp-fileview .fileview-body .fv-cl"), null, { timeout: 10000 });
    await frames(page, 3);
    b = await bar(page);
    assert.equal((await prints(page)).length, 0, "FAILS BEFORE: the Raw pick under the ask printed the Raw view with neither button pressed");
    assert.equal(b.phase, null, "the flow rests"); assert.equal(b.line, null); assert.equal(b.cardUp, true);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (14) the press reads the body itself ───────────────────────────────────────────────────────────

test("(14) a press reads the body's children before it acts, so a swap in the press's own task is seen before the observer runs: the loader swapped in and a press in one task prints nothing and the button reads disabled; the content put back and a press in one task prints; over the open's own loader, content swapped in and a press in one task prints", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a: content out, the loader in, and the press, in one task
    let s = await scene(browser, "pane", NOPIC_NOTE);
    let { page } = s;
    assert.equal((await bar(page)).phase, null, "live over the note");
    let r: { printed: number; phase: string | null; ariaDisabled: string | null } = await page.evaluate(() => {
      const body = document.querySelector("#romp-fileview .fileview-body")!;
      const kept = Array.from(body.children);
      const load = document.createElement("div"); load.className = "fileview-load";
      body.replaceChildren(load);
      (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click();
      const b = document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement;
      const out = { printed: (window as any).__prints.length, phase: b.dataset.print || null, ariaDisabled: b.getAttribute("aria-disabled") };
      body.replaceChildren(...kept);
      return out;
    });
    assert.deepEqual(r, { printed: 0, phase: "disabled", ariaDisabled: "true" }, "the press read the loader before the observer ran: nothing printed, the button disabled in the press's own task");
    await frames(page, 2);
    assert.equal((await bar(page)).phase, null, "the content back: live again once the observer ran");
    r = await page.evaluate(() => {
      const body = document.querySelector("#romp-fileview .fileview-body")!;
      const kept = Array.from(body.children);
      const load = document.createElement("div"); load.className = "fileview-load";
      body.replaceChildren(load);
      body.replaceChildren(...kept);   // out and back in one task: the observer sees one change list, the press sees content
      (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click();
      const b = document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement;
      return { printed: (window as any).__prints.length, phase: b.dataset.print || null, ariaDisabled: b.getAttribute("aria-disabled") };
    });
    assert.equal(r.printed, 1, "content in the body at the press: printed at once");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // b: the open's loader up (the report's answer parked), content swapped in by hand and the press, in one task
    const opened = await openViewer(browser, "pane", 900, 700, {
      docs: { [REPORT]: NOPIC_NOTE },
      waitFor: "#romp-fileview .fileview-body .fileview-load",
      before: async (pg: any) => {
        await pg.evaluate(() => {
          const w = window as any; const prev = w.fetch;
          const gate = new Promise<void>((r2) => { w.__release = r2; });
          w.fetch = async function (url: unknown, init: any) {
            const m = /[?&]path=([^&]*)/.exec(String(url));
            if (m && /\/report\.md$/.test(decodeURIComponent(m[1])) && !(init && init.method === "HEAD")) await gate;
            return prev(url, init);
          };
        });
        await pg.evaluate(PAGE_PROBES);
      },
    });
    page = opened.page;
    assert.equal((await bar(page)).phase, "disabled", "disabled over the open's loader");
    r = await page.evaluate(() => {
      const body = document.querySelector("#romp-fileview .fileview-body")!;
      const md = document.createElement("div"); md.className = "fileview-md"; md.innerHTML = "<p>seated by the test</p>";
      body.replaceChildren(md);
      (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click();
      const b = document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement;
      return { printed: (window as any).__prints.length, phase: b.dataset.print || null, ariaDisabled: b.getAttribute("aria-disabled") };
    });
    assert.deepEqual(r, { printed: 1, phase: null, ariaDisabled: null }, "the press read the content before the observer ran: printed in the press's own task, the button live");
    await page.evaluate(() => { (window as any).__release(); });
    await page.waitForFunction(() => (document.querySelector("#romp-fileview .fileview-md > p")?.textContent || "") === "Text alone, no picture.", null, { timeout: 10000 });
    await frames(page, 2);
    assert.equal((await bar(page)).phase, null, "the real paint landed: live");
    assert.deepEqual(opened.errors, [], "no script error");
    await page.close();
  });
});

// ── (3d) and (13c): a landing naming a URL whose probe is complete ─────────────────────────────────

/** The diagram's route: the render's own request and the press's probe answer 404 (the probe completes by its error), and
 *  every request after that is parked, so the landing's own fetch and the re-aim's fresh probe can be told from the two
 *  before and released by the test. Registered in the scene's `before`, after the scene's routes, so it is matched first. */
function diagramRoute(): { before: (pg: any) => Promise<void>; parked: () => number; release: () => Promise<void> } {
  const held: any[] = [];
  let seen = 0;
  return {
    before: async (pg: any) => {
      await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/file" && (u.searchParams.get("path") || "").endsWith(IMAGE), (route: any) => {
        seen++;
        if (seen <= 2) return route.fulfill({ status: 404, contentType: "text/plain", body: "no such file" });
        held.push(route);
      });
    },
    parked: () => held.length,
    release: async () => { for (const r of held.splice(0)) await r.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); },
  };
}
/** The diagram's element fetched (404) at the render and probed (404) at the press: two requests, both answered, and both
 *  answers delivered to the page (two resource timing entries for the URL: the probe is complete, by its error, once the
 *  second has landed; a picture completing rewrites no line, so the line cannot say). */
async function diagramProbed(s: Scene, diagram: ReturnType<typeof diagramRoute>): Promise<void> {
  for (let i = 0; i < 200 && s.requestsFor(IMAGE) < 2; i++) await frames(s.page, 1);
  assert.equal(s.requestsFor(IMAGE), 2, "the diagram's own request and the press's probe (" + s.requestsFor(IMAGE) + ")"); assert.equal(diagram.parked(), 0, "both answered 404");
  await s.page.waitForFunction((n: string) => performance.getEntriesByType("resource").filter((e) => decodeURIComponent(e.name).includes("/docs/" + n)).length >= 2, IMAGE, { timeout: 5000 });
}

test("(3d) a Reload landing during the wait names an svg image URL the press already probed to its end (its route answered 404, so the probe is complete): the finished probe is dropped and the URL probed again against the landing, a request the browser folds into the landing element's own, still parked, so the wait goes on and the print comes at that request's release (FAILS BEFORE: the wait answered from the old document's failed probe and window.print ran at the landing with its own fetch still in flight); the parked slow picture of the old body never printed anything", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const diagram = diagramRoute();
    const s = await scene(browser, "pane", SLOW_DIAGRAM_NOTE, { held: [SLOW], before: diagram.before });
    const { page } = s;
    await parked(s, [SLOW]);
    for (let i = 0; i < 200 && s.requestsFor(IMAGE) < 1; i++) await frames(page, 1);
    assert.equal(s.requestsFor(IMAGE), 1, "the diagram's element asked for its picture at the render (404)");
    await page.click(PRINT_BTN);
    await diagramProbed(s, diagram);
    let b = await bar(page);
    assert.equal(b.phase, "preparing", "the wait runs: the slow picture is loading and the diagram's probe has failed (a picture completing rewrites no line, so the line still counts both)");
    await reloadTo(page, DIAGRAM_ONLY_NOTE);
    await page.waitForFunction(() => !document.getElementById("fileview-save-err") && document.querySelectorAll("#romp-fileview .fileview-body img").length === 0 && !!document.querySelector("#romp-fileview .fileview-body image"), null, { timeout: 10000 });
    for (let i = 0; i < 100 && diagram.parked() < 1; i++) await frames(page, 1);
    await frames(page, 6);
    b = await bar(page);
    assert.deepEqual({ prints: (await prints(page)).length, requests: s.requestsFor(IMAGE), parked: diagram.parked(), phase: b.phase, line: b.line },
      { prints: 0, requests: 3, parked: 1, phase: "preparing", line: "Preparing 1 picture\u2026" },
      "FAILS BEFORE: the landing printed at once (prints 1, phase null) with the diagram's own request parked; now the finished probe is dropped, the fresh probe is folded by the browser into the landing element's request, still parked (three requests in all, nothing more left the page), and the wait goes on over it");
    await s.release([SLOW]);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "the old body's slow picture landing prints nothing: it is not in the body");
    await diagram.release();
    await printsReach(page, 1);
    const p = await prints(page);
    assert.equal(p.length, 1, "the print at the release of the landing's request, which answered the element and the probe"); assert.equal(p[0].line, false);
    await frames(page, 6);
    assert.equal(s.requestsFor(IMAGE), 3, "nothing asked again after the print");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

test("(13c) the same landing under the deadline's ask: the finished probe is dropped and the URL probed again, so the count reads one and the ask stands, its words rewritten in the same row (FAILS BEFORE: the old failed probe read as complete, the count read none, the question was called moot and the line went, with the landing's fetch still in flight); Escape disarms; the releases print nothing", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const diagram = diagramRoute();
    const s = await scene(browser, "pane", SLOW_DIAGRAM_NOTE, { held: [SLOW], before: diagram.before });
    const { page } = s;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await diagramProbed(s, diagram);
    await askReached(page);
    await markLine(page);
    await reloadTo(page, DIAGRAM_ONLY_NOTE);
    await page.waitForFunction(() => !document.getElementById("fileview-save-err") && document.querySelectorAll("#romp-fileview .fileview-body img").length === 0 && !!document.querySelector("#romp-fileview .fileview-body image"), null, { timeout: 10000 });
    for (let i = 0; i < 100 && diagram.parked() < 1; i++) await frames(page, 1);
    await frames(page, 6);
    const b = await bar(page);
    assert.deepEqual({ prints: (await prints(page)).length, requests: s.requestsFor(IMAGE), parked: diagram.parked(), phase: b.phase, line: b.line, marked: await lineMarked(page), buttons: b.buttons },
      { prints: 0, requests: 3, parked: 1, phase: "stalled", line: STALLED_ONE, marked: true, buttons: [ANYWAY_WORDS, KEEP_WORDS] },
      "FAILS BEFORE: the landing's count read none from the old failed probe, the flow rested and the line went (phase null, line null); now the URL is probed again, the probe folded into the landing element's parked request (three requests in all), the count reads one and the ask stands in the same row");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "Escape under the ask disarms");
    await s.release([SLOW]); await diagram.release();
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0, "nothing printed by the releases: the wait was disarmed");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (5b) the ask written into the wait's line ─────────────────────────────────────────────────────

test("(5b) the deadline's ask is written into the wait's line: the row marked during the wait is the row the ask stands in, the loader gone from it and the two word buttons in it, one line on the card (FAILS BEFORE: the ask was a fresh row, so the mark was gone with the wait's line); Escape disarms", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW] });
    const { page } = s;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    let b = await bar(page);
    assert.equal(b.phase, "preparing"); assert.equal(b.line, "Preparing 1 picture\u2026");
    assert.equal(await page.evaluate(() => !!document.querySelector("#fileview-print-line .fileview-print-load")), true, "the wait's line carries the loader");
    await markLine(page);
    await askReached(page);
    b = await bar(page);
    assert.deepEqual({ marked: await lineMarked(page), loader: await page.evaluate(() => !!document.querySelector("#fileview-print-line .fileview-print-load")), lines: b.lines, buttons: b.buttons, titles: b.titles, phase: b.phase },
      { marked: true, loader: false, lines: 1, buttons: [ANYWAY_WORDS, KEEP_WORDS], titles: [ANYWAY_TITLE, KEEP_TITLE], phase: "stalled" },
      "FAILS BEFORE: the mark was gone (the ask a fresh row); now the same row reads the ask, its loader gone and its two buttons in");
    assert.equal((await prints(page)).length, 0, "nothing printed at the deadline");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "Escape under the ask disarms");
    await s.release([SLOW]);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 0);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (15) Keep waiting's open-ended wait: Print anyway on its line, and Escape ──────────────────────

test("(15) Keep waiting's open-ended wait carries one word button, Print anyway: after Keep waiting the line reads " + JSON.stringify(waitingWords(1)) + " beside the loader with Print anyway alone (FAILS BEFORE: the line read \"Preparing 1 picture…\" with no button, so the wait had no way through but the load); pressing it prints once with the parked picture still incomplete and the placeholder on the paper, the request still parked, the keyboard on the Print button, and the bar rests; no print on any timer meanwhile; a Reload landing under that wait re-aims it and rewrites the count in the same row, the button staying, and the landing's pictures released print once with every picture complete; Escape during that wait rests the bar with the card up and nothing printed, and the release after it prints nothing (the exit the wait already had: established by execution on the code before the button, 2026-09-20)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const WAITING_ONE = waitingWords(1), WAITING_TWO = waitingWords(2);
    const ANYWAY_BTN = '#fileview-print-line button:has-text("' + ANYWAY_WORDS + '")';
    const KEEP_BTN = '#fileview-print-line button:has-text("' + KEEP_WORDS + '")';
    const loaderOn = (page: any): Promise<boolean> => page.evaluate(() => !!document.querySelector("#fileview-print-line .fileview-print-load"));
    const lineReads = (page: any, words: string): Promise<unknown> => page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, words, { timeout: 6000 });
    // a: the gated note, Print without them, the ask, Keep waiting: the line with its one button; Print anyway prints at once
    let s = await scene(browser, "pane", GATED_NOTE, { held: [SLOW] });
    let { page } = s;
    await waitGates(page, 1); await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await page.click(WITHOUT_BTN);
    await askReached(page);
    await page.click(KEEP_BTN);
    let b = await bar(page);
    assert.deepEqual({ phase: b.phase, line: b.line, buttons: b.buttons, titles: b.titles, loader: await loaderOn(page), lines: b.lines, busy: b.busy },
      { phase: "preparing", line: WAITING_ONE, buttons: [ANYWAY_WORDS], titles: [ANYWAY_TITLE], loader: true, lines: 1, busy: true },
      "FAILS BEFORE: the open-ended wait's line read \"Preparing 1 picture…\" with no button; now it reads the waiting words beside the loader with Print anyway alone");
    await pause(page, 1000);   // a timer, since the absence of one is what is measured
    assert.equal((await prints(page)).length, 0, "no print 1 s into the open-ended wait: no timer");
    assert.equal((await bar(page)).line, WAITING_ONE, "still waiting");
    await page.click(ANYWAY_BTN);
    let p = await prints(page);
    assert.equal(p.length, 1, "Print anyway printed once");
    assert.deepEqual({ gates: p[0].gates, incomplete: p[0].incomplete.length, line: p[0].line }, { gates: 1, incomplete: 1, line: false }, "the placeholder on the paper, the parked picture still loading and left off the paper, the line gone before the print");
    assert.ok(p[0].incomplete[0].includes("/docs/" + SLOW), "the parked picture is the incomplete one");
    assert.ok(p[0].active.startsWith("BUTTON.fileview-btn.fileview-icon.fileview-print"), "the keyboard went from the word button to the Print button: " + p[0].active);
    assert.equal(s.heldCount(SLOW), 1, "its request is still parked: nothing released it");
    await frames(page, 1);
    b = await bar(page);
    assert.equal(b.phase, null, "the bar rested"); assert.equal(b.line, null); assert.equal(b.cardUp, true);
    await s.release([SLOW]);
    await frames(page, 6);
    assert.equal((await prints(page)).length, 1, "the release after the print prints nothing more");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // b: a Reload landing under the open-ended wait (the repaint's re-aim, under no deadline): the count follows in the same
    // row and the button stays; the landing's two pictures released print once, the old body's picture still parked
    s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW, SLOW2, SLOW3] });
    page = s.page;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await askReached(page);
    await page.click(KEEP_BTN);
    await markLine(page);
    b = await bar(page);
    assert.deepEqual({ line: b.line, buttons: b.buttons }, { line: WAITING_ONE, buttons: [ANYWAY_WORDS] }, "the open-ended wait over one");
    await reloadTo(page, TWO_SLOW_NOTE);
    for (let i = 0; i < 100 && (s.heldCount(SLOW2) === 0 || s.heldCount(SLOW3) === 0); i++) await frames(page, 1);
    assert.equal(s.heldCount(SLOW2) + s.heldCount(SLOW3), 2, "the landing's two pictures are requested and parked");
    await lineReads(page, WAITING_TWO);
    b = await bar(page);
    assert.deepEqual({ marked: await lineMarked(page), buttons: b.buttons, titles: b.titles, lines: b.lines, phase: b.phase, loader: await loaderOn(page), prints: (await prints(page)).length },
      { marked: true, buttons: [ANYWAY_WORDS], titles: [ANYWAY_TITLE], lines: 1, phase: "preparing", loader: true, prints: 0 },
      "the landing: the count rewritten in the same row, the button and the loader staying, nothing printed");
    await pause(page, 800);
    assert.equal((await prints(page)).length, 0, "no print past the seam's deadline after the landing: the re-aim set no timer either");
    await s.release([SLOW2, SLOW3]);
    await printsReach(page, 1);
    p = await prints(page);
    assert.deepEqual({ n: p.length, incomplete: p[0].incomplete, line: p[0].line }, { n: 1, incomplete: [], line: false }, "the last settle prints as before, every <img> of the body complete");
    assert.equal(s.heldCount(SLOW), 1, "the old body's picture never landed: nothing waited for it");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // c: Escape during the open-ended wait: the exit the wait already had (the probe of 2026-09-20 read the same on the code before the button)
    s = await scene(browser, "pane", SLOW_NOTE, { held: [SLOW] });
    page = s.page;
    await parked(s, [SLOW]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await askReached(page);
    await page.click(KEEP_BTN);
    b = await bar(page);
    assert.deepEqual({ phase: b.phase, buttons: b.buttons }, { phase: "preparing", buttons: [ANYWAY_WORDS] });
    await page.keyboard.press("Escape");
    await frames(page, 2);
    b = await bar(page);
    assert.deepEqual({ phase: b.phase, line: b.line, cardUp: b.cardUp, busy: b.busy, prints: (await prints(page)).length, parked: s.heldCount(SLOW) }, { phase: null, line: null, cardUp: true, busy: false, prints: 0, parked: 1 }, "Escape: the bar at rest, the line gone, the card up, nothing printed, the request still parked");
    await s.release([SLOW]);
    await frames(page, 8);
    assert.equal((await prints(page)).length, 0, "the release after the Escape prints nothing: nothing waits");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (15a) what reaches the paper under the ask and the open-ended wait: the print-media boxes ──────────────────

/** A note with a placeholder, a parked markdown picture with no declared size, and a parked <img> with width and height. */
const SIZED_NOTE = "# Figures\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nA sized slow one <img src=\"" + SLOW2 + "\" width=\"120\" height=\"80\" alt=\"\">\n\nA remote one ![](" + REMOTE + ").\n\nLast line.\n";
type Box = { w: number; h: number };
type Paper = { media: string; parked: Box | null; sized: Box | null; gate: Box | null; line: Box | null; parkedComplete: boolean | null; sizedComplete: boolean | null };
/** The boxes of the parked picture, the sized parked picture, the placeholder and the line under `media` (the page's media
 *  emulated, then released), each as getBoundingClientRect's width and height, and the two pictures' `complete`. */
async function paper(page: any, media: "print" | "screen"): Promise<Paper> {
  await page.emulateMedia({ media });
  const read: Paper = await page.evaluate((m: string) => {
    const box = (el: Element | null): Box | null => { if (!el) return null; const r = el.getBoundingClientRect(); return { w: r.width, h: r.height }; };
    const imgs = Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
    const parked = imgs.find((i) => decodeURIComponent(i.src).includes("/docs/slow.svg")) || null;
    const sized = imgs.find((i) => decodeURIComponent(i.src).includes("/docs/slow2.svg")) || null;
    return { media: m, parked: box(parked), sized: box(sized), gate: box(document.querySelector('#romp-fileview [data-act="fv-load"]')), line: box(document.getElementById("fileview-print-line")), parkedComplete: parked ? parked.complete : null, sizedComplete: sized ? sized.complete : null };
  }, media);
  await page.emulateMedia({ media: null });
  return read;
}
test("(15a) what reaches the paper: under the deadline's ask and under Keep waiting's open-ended wait, with print media emulated, the parked markdown picture with no declared size has a 0 by 0 box (nothing where the picture was: no box, no gap, no label), the parked <img> with width and height a box of that size and nothing in it, and the gated placeholder a box with width and height (its dress prints); the line itself is off the paper; the same read on screen media beside it, and the picture's `complete` false at both reads (the round-4 review, 2026-09-20: case (15) pinned `complete`, which is not what reaches the paper)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const KEEP_BTN = '#fileview-print-line button:has-text("' + KEEP_WORDS + '")';
    const s = await scene(browser, "pane", SIZED_NOTE, { held: [SLOW, SLOW2] });
    const { page } = s;
    await waitGates(page, 1); await parked(s, [SLOW, SLOW2]);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
    await page.click(PRINT_BTN);
    await page.click(WITHOUT_BTN);
    await page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, STALLED_TWO, { timeout: 6000 });   // the ask over the two parked pictures
    let b = await bar(page);
    assert.deepEqual({ line: b.line, buttons: b.buttons, titles: b.titles }, { line: "2 pictures have not loaded. " + anywayWords(), buttons: [ANYWAY_WORDS, KEEP_WORDS], titles: [ANYWAY_TITLE, KEEP_TITLE] }, "the ask's line, read before any press: the count, then the button's own sentence, anywayWords() (FAILS BEFORE: the line ended at the count; the words themselves are pinned in file-print.test.ts, and this leg holds no copy)");
    assert.ok(b.line!.endsWith(" " + anywayWords()), "the sentence is the line's last words, beside the button");
    const askScreen = await paper(page, "screen"), askPrint = await paper(page, "print");
    for (const p of [askScreen, askPrint]) t.diagnostic("paper | ask | " + JSON.stringify(p));
    assert.equal((await bar(page)).phase, "stalled", "the ask stands after the reads");
    await page.click(KEEP_BTN);
    await page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, waitingWords(2), { timeout: 6000 });
    b = await bar(page);
    assert.deepEqual({ line: b.line, buttons: b.buttons, titles: b.titles }, { line: "Waiting for 2 pictures… " + anywayWords(), buttons: [ANYWAY_WORDS], titles: [ANYWAY_TITLE] }, "the open-ended wait's line, read before any press: the count, then the button's own sentence, anywayWords()");
    const waitScreen = await paper(page, "screen"), waitPrint = await paper(page, "print");
    for (const p of [waitScreen, waitPrint]) t.diagnostic("paper | open-ended wait | " + JSON.stringify(p));
    // the count is the aim's: one of the two pictures landing settles nothing, so the line still reads two (extra7-2: the
    // wait's promise resolves once, when every picture it listened on has settled)
    await s.release([SLOW]);
    await page.waitForFunction(() => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).filter((i) => !i.complete).length === 1, null, { timeout: 6000 });
    await frames(page, 3);
    assert.deepEqual({ line: (await bar(page)).line, prints: (await prints(page)).length, incomplete: await page.evaluate(() => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).filter((i) => !i.complete).length) }, { line: waitingWords(2), prints: 0, incomplete: 1 },
      "one of two pictures landed: the count is the aim's and does not fall per settle; nothing printed");
    for (const [site, p] of [["the ask", askPrint], ["the open-ended wait", waitPrint]] as Array<[string, Paper]>) {
      assert.equal(p.parkedComplete, false, site + ": the parked picture is still loading at the read");
      assert.deepEqual(p.parked, { w: 0, h: 0 }, site + ", print media: the parked picture with no declared size is a 0 by 0 box, nothing where the picture was");
      assert.ok(p.sized && p.sized.w === 120 && p.sized.h === 80, site + ", print media: the parked picture with width and height is a box of that size: " + JSON.stringify(p.sized));
      assert.ok(p.gate && p.gate.w > 0 && p.gate.h > 0, site + ", print media: the placeholder has a box: " + JSON.stringify(p.gate));
      assert.deepEqual(p.line, { w: 0, h: 0 }, site + ", print media: the line is off the paper (the sheets hide .fileview > .fileview-err in print)");
    }
    assert.equal((await prints(page)).length, 0, "nothing printed: the reads pressed nothing");
    await page.keyboard.press("Escape");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "Escape ended the open-ended wait");
    await s.release([SLOW2]);
    await frames(page, 4);
    assert.equal((await prints(page)).length, 0, "the last release after the Escape prints nothing: nothing waits");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});

// ── (15b) a picture landing while the line stands: the print is read under print media, and the landed picture prints ──

test("(15b) a picture that lands while the line stands prints, and the line's last sentence stays true of it: the PRINT is read under print media while each line stands (the round-6 review's cluster D, 2026-09-20: the released picture complete with a non-zero box, the unreleased one still loading in the box case (15a) measured for it, 0 by 0 with no declared size and an empty box of the declared size otherwise; the landed sized picture measures 120 by 120, its declared width and the square picture's own height, where its parked box was 120 by 80), and the press then prints once with exactly the unreleased pictures incomplete; under the deadline's ask over two parked pictures, both released, the ask stands with its line unchanged (nothing listens under the ask; the count is the aim's, extra7-2), both pictures complete in non-zero boxes, and Print anyway prints once with every <img> complete; under Keep waiting's open-ended wait the picture with no declared size released alone leaves the line reading two, that picture complete with a non-zero box and the sized one still loading in its empty declared box while the line stands (read there, not inferred from the print's complete list; the branch's verification pass finding engines-1), and Print anyway prints once with the sized one the only <img> still loading; the sized one released alone leaves the picture with no declared size a 0 by 0 box, still loading, while the line stands, and Print anyway prints once with it the only one still loading; under Keep waiting both released print once on the settle, no press. The sentence beside the button is read off the line and held equal to the product's own, anywayWords(); this leg holds no copy of its words (the round-6 review's ui-1, correctness-4 and tests-1: until the round-7 fixes the case's only red at the round-5 wording, \"Print anyway prints without them.\", was a compare against a copy of the sentence spelled here; the print reads above are what the leg asserts, the round-6 wording fix changed no print, so those reads hold at either wording, and the words stand pinned in file-print.test.ts alone) (the round-5 review's ui-1, 2026-09-20)", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const KEEP_BTN = '#fileview-print-line button:has-text("' + KEEP_WORDS + '")';
    const ANYWAY_BTN = '#fileview-print-line button:has-text("' + ANYWAY_WORDS + '")';
    const lineIs = (page: any, words: string): Promise<unknown> => page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, words, { timeout: 6000 });
    const stillLoading = (page: any, k: number): Promise<unknown> => page.waitForFunction((n: number) => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).filter((i) => !i.complete).length === n, k, { timeout: 6000 });
    /** The print's incomplete pictures by the names paper() reads them under: `parked` the picture with no declared size
     *  (SLOW), `sized` the one with width and height (SLOW2); any other URL as itself. */
    const named = (urls: string[]): string[] => urls.map((u) => u.includes("/docs/" + SLOW2) ? "sized" : u.includes("/docs/" + SLOW) ? "parked" : u);
    /** SIZED_NOTE's two parked pictures under the deadline's ask. */
    const askOverTwo = async (): Promise<Scene> => {
      const sc = await scene(browser, "pane", SIZED_NOTE, { held: [SLOW, SLOW2] });
      await waitGates(sc.page, 1); await parked(sc, [SLOW, SLOW2]);
      await sc.page.evaluate(() => { (window as any).FV.setPrintSettleMs(600); });
      await sc.page.click(PRINT_BTN);
      await sc.page.click(WITHOUT_BTN);
      await lineIs(sc.page, STALLED_TWO);
      return sc;
    };
    // a: the ask; both pictures land under it; then Print anyway
    let s = await askOverTwo();
    let { page } = s;
    await s.release([SLOW, SLOW2]);
    await stillLoading(page, 0);
    await frames(page, 3);
    let b = await bar(page);
    assert.deepEqual({ phase: b.phase, line: b.line, buttons: b.buttons, prints: (await prints(page)).length }, { phase: "stalled", line: STALLED_TWO, buttons: [ANYWAY_WORDS, KEEP_WORDS], prints: 0 }, "both landed under the ask: the ask stands, its line unchanged (nothing listens under the ask, and the count is the aim's), nothing printed");
    const askLine = b.line!;   // read before the press, held against what the press prints below
    const askPrint = await paper(page, "print");
    t.diagnostic("paper | ask, both landed | " + JSON.stringify(askPrint));
    assert.deepEqual({ parkedComplete: askPrint.parkedComplete, sizedComplete: askPrint.sizedComplete, sized: askPrint.sized }, { parkedComplete: true, sizedComplete: true, sized: { w: 120, h: 120 } }, "print media, while the ask stands: both released pictures are complete, the sized one at its declared width and the square picture's own height (the sheet lets the height follow the picture once it lands; parked, it held the declared 120 by 80 box, case (15a))");
    assert.ok(askPrint.parked && askPrint.parked.w > 0 && askPrint.parked.h > 0, "print media: the landed picture with no declared size has a box where the parked one had a 0 by 0 box (case (15a)): " + JSON.stringify(askPrint.parked));
    assert.equal((await bar(page)).phase, "stalled", "the ask stands after the read");
    await page.click(ANYWAY_BTN);
    let p = await prints(page);
    assert.equal(p.length, 1, "Print anyway printed once, at the press");
    assert.deepEqual(named(p[0].incomplete), [], "every <img> complete at the print: nothing left out, the two pictures the line counted on the paper");
    assert.equal(p[0].gates, 1, "the placeholder stands");
    assert.ok(askLine.endsWith(" " + anywayWords()), "the sentence beside the button, read off the line before the press, is the product's own (anywayWords(); this leg holds no copy of the words): " + askLine);
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // b: Keep waiting; the picture with no declared size lands; then Print anyway
    s = await askOverTwo(); page = s.page;
    await page.click(KEEP_BTN);
    await lineIs(page, waitingWords(2));
    await s.release([SLOW]);
    await stillLoading(page, 1);
    await frames(page, 3);
    b = await bar(page);
    assert.deepEqual({ phase: b.phase, line: b.line, buttons: b.buttons, prints: (await prints(page)).length }, { phase: "preparing", line: waitingWords(2), buttons: [ANYWAY_WORDS], prints: 0 }, "one landed under the open-ended wait: the line still reads two (the aim's count) with the button, nothing printed");
    const waitLine = b.line!;
    // the branch's verification pass finding engines-1 (2026-09-20): what the released picture is on the paper is read under print media WHILE
    // the line stands, not inferred from the print stub's complete list (case (15a)'s ruling: complete is not what reaches the paper)
    const waitPrint = await paper(page, "print");
    t.diagnostic("paper | wait, the unsized one landed | " + JSON.stringify(waitPrint));
    assert.deepEqual({ parkedComplete: waitPrint.parkedComplete, sizedComplete: waitPrint.sizedComplete, sized: waitPrint.sized }, { parkedComplete: true, sizedComplete: false, sized: { w: 120, h: 80 } }, "print media, while the line reads two: the released picture is complete and the unreleased sized one is still loading in its empty declared box (case (15a)'s measure of a parked sized picture)");
    assert.ok(waitPrint.parked && waitPrint.parked.w > 0 && waitPrint.parked.h > 0, "print media: the released picture has a box where the parked one had a 0 by 0 box (case (15a)), while the line still reads two: " + JSON.stringify(waitPrint.parked));
    assert.deepEqual({ phase: (await bar(page)).phase, parked: s.heldCount(SLOW2) }, { phase: "preparing", parked: 1 }, "the wait stands after the read and the other picture's request is still parked");
    await page.click(ANYWAY_BTN);
    p = await prints(page);
    assert.equal(p.length, 1, "Print anyway printed once, at the press");
    assert.deepEqual(named(p[0].incomplete), ["sized"], "the print left out exactly the picture never released, the sized one, and carried the released one");
    assert.equal(p[0].gates, 1);
    assert.ok(waitLine.endsWith(" " + anywayWords()), "the sentence beside the button, read off the line before the press, is the product's own (anywayWords()): " + waitLine);
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    assert.equal(s.heldCount(SLOW2), 1, "the second request is still parked: nothing released it");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // c: Keep waiting; the sized picture lands alone; the unsized one is a 0 by 0 box while the line stands; then Print anyway
    s = await askOverTwo(); page = s.page;
    await page.click(KEEP_BTN);
    await lineIs(page, waitingWords(2));
    await s.release([SLOW2]);
    await stillLoading(page, 1);
    await frames(page, 3);
    b = await bar(page);
    assert.deepEqual({ phase: b.phase, line: b.line, buttons: b.buttons, prints: (await prints(page)).length }, { phase: "preparing", line: waitingWords(2), buttons: [ANYWAY_WORDS], prints: 0 }, "the sized picture landed under the open-ended wait: the line still reads two with the button, nothing printed");
    const sizedPrint = await paper(page, "print");
    t.diagnostic("paper | wait, the sized one landed | " + JSON.stringify(sizedPrint));
    assert.deepEqual({ parked: sizedPrint.parked, parkedComplete: sizedPrint.parkedComplete, sized: sizedPrint.sized, sizedComplete: sizedPrint.sizedComplete }, { parked: { w: 0, h: 0 }, parkedComplete: false, sized: { w: 120, h: 120 }, sizedComplete: true }, "print media, while the line reads two: the released sized picture is complete at its declared width and its own height (120 by 120 where the parked box was 120 by 80), and the unreleased picture with no declared size is a 0 by 0 box, still loading (the round-6 review's cluster D: the released picture's box non-zero and the unreleased one's 0 by 0, read while the line stands)");
    assert.deepEqual({ phase: (await bar(page)).phase, parked: s.heldCount(SLOW) }, { phase: "preparing", parked: 1 }, "the wait stands after the read and the unsized picture's request is still parked");
    await page.click(ANYWAY_BTN);
    p = await prints(page);
    assert.equal(p.length, 1, "Print anyway printed once, at the press");
    assert.deepEqual(named(p[0].incomplete), ["parked"], "the print left out exactly the picture never released, the one with no declared size, and carried the sized one");
    assert.equal(p[0].gates, 1);
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    assert.equal(s.heldCount(SLOW), 1, "the unsized picture's request is still parked: nothing released it");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
    // d: Keep waiting; both land; the settle prints with no press
    s = await askOverTwo(); page = s.page;
    await page.click(KEEP_BTN);
    await lineIs(page, waitingWords(2));
    await s.release([SLOW, SLOW2]);
    await printsReach(page, 1);
    p = await prints(page);
    assert.equal(p.length, 1, "one print, at the last picture's load");
    assert.deepEqual(p[0].incomplete, [], "with every <img> complete"); assert.equal(p[0].gates, 1); assert.equal(p[0].line, false, "the line went before the print");
    await frames(page, 1);
    assert.equal((await bar(page)).phase, null, "the bar rested");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.deepEqual(s.errors, [], "no script error");
    await page.close();
  });
});
