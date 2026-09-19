// What leaves the page on every road through the print flow (file-print.ts; the print follow-on to plans/markdown-viewer.md's
// Slice 3, item 12), counted under a Chromium request intercept over the real viewer through real-viewer-leg.ts. The flow
// is a privacy surface: a gated placeholder (figure-gate.ts) stands for a picture on a host the gear's list does not name,
// and a print may fetch from such a host only when the person chose "Print with them", and then only for a placeholder
// that reaches the paper. The third review of the follow-on (2026-09-19) found one press asking a host hundreds of times
// for one URL, so this leg does not assert that nothing unwanted leaves; it COUNTS what leaves, road by road, and holds
// each count exactly. Every request Playwright reports for the page (page.on("request"), installed before the file opens,
// so the page's own document is not counted) goes into one ledger per page, and each road is the ledger's delta between
// two marks: a road is an act (a press, a choice, a key, a landing, a release) followed by six animation frames and a
// 250 ms settle, so a request the act causes has been issued when the delta is read (the remote routes answer after
// 150 ms, and the request is reported when it is issued, not when it is answered). A request is classed by its URL: LOCAL
// is the page's origin (a /file request keyed by the picture's path under the root, docs/fig.svg; any other path by its
// pathname: the viewer's loader glyph and the sheet's font, one request each per page), THIRD-PARTY is any other http or
// https host, keyed by host and path, and OTHER is any other scheme, keyed by scheme and host (a blob: URL by the origin
// it belongs to; a chrome-extension: URL by the extension's id). Each road's row (the road,
// the third-party URLs and their counts, the local URLs and their counts, the other URLs, and what printed: window.print's
// calls, the PDF frame's print or the /file tab through window.open, all stubbed on the page) is asserted as plain strings
// and numbers and printed as one diagnostic line of a fixed shape ("egress | road | third-party: ... | local: ... |
// other: ... | printed: ..."), so the table the report carries is the lines a run prints (grep the run's output for
// "egress |"). At each page's end a tail read finds nothing after the last road, and the rows' counts sum to the ledger,
// so every request the page made is in some row. The harness answers the file's own GET and HEAD inside the page (real-viewer-leg.ts replaces window.fetch), so
// those never reach the intercept and are not rows; in the product they go to the kernel, the page's own origin. The
// pictures, the probes and the frame go through the browser's network stack and are what the intercept sees.
// The roads: (1) a gated note with five placeholders on five hosts, two in the open body and three that never reach the
// paper (a typed <details> that is closed, a folded callout, a `hidden` div): the render; a press then Escape; a press then
// a second press (the chord); a press then "Print without them"; a press then "Print with them", which asks the two
// printable hosts once each and the three others never. (2) two placeholders: a press, one placeholder activated by hand
// under the armed line (its host asked once, the recount narrowing the line and the title), then "Print with them" over
// the one left (its host once). (3) the wait: a Reload landing during the wait (the landing's pictures requested once,
// the print at the landing's picture's release); the deadline into the ask, then "Print anyway"; the ask, then "Keep
// waiting" and the parked route released. (4) a <video poster> and an svg <image href> whose routes answer 404: one probe
// per URL per press, over two presses; an <img loading="lazy"> far below the fold: no request before the press, one at
// it. (5) a picture opened directly: its bytes come through the page's fetch and its <img> is a blob: URL, for which the
// intercept reports no request; a PDF under the two launches the media leg uses: the headless shell reports the frame's
// blob: navigation and takes the /file tab through the stubbed window.open; the full Chromium build's PDF viewer loads its
// own files in place of that navigation (9 under its chrome-extension:// id and 8 under chrome://resources in the build
// Playwright ships here, the URLs printed in full beside the count; a browser update moves these two numbers and nothing
// else in this leg) and prints through the frame's own window, then takes the tab once print is taken from that window.
// (6) a host two placeholders share, one in the open body and one inside a closed <details>, the folded picture's route
// parked: "Print with them" restores the printable placeholder alone (the gate's one-placeholder restore, loadGatedFigure)
// and asks the host for its URL once; the folded placeholder stands and its URL is never asked, so its parked route holds
// nothing; the wait counts the open picture and prints at its load, under the deadline, with no ask. (7) the same page
// with both routes answering, the per-host and the per-placeholder counts read apart: the host is asked once, for one of
// its two placeholders; the folded placeholder stands at the print; and a Reload of the same note afterwards shows both
// placeholders again with nothing asked, since a print grants a host nothing for the page (a click does: decision 8).
// Before the round-2 review (2026-09-19) "with them" loaded by HOST through the click's road, so on such a page the folded
// URL was asked too, for a picture the print never shows, and every page in this leg gave each placeholder a host of its
// own, so no road could see it; the shared-host probe before that found the wait counting the folded picture as well
// (the line read two, the deadline asked about the folded one, nothing printed until the person answered).
// The counts this leg holds are the third review's target: one request per URL per press, and none for a host the
// person did not choose, nor for a placeholder that does not reach the paper. Skips loudly without a browser. Synthetic
// values only: an invented note, /repo/notes-api paths, invented hosts under .test.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, frames, requireCjs, REPORT, ROOT, ORIGIN, SID, MT2, type Mode } from "./real-viewer-leg";
import { fileUrl } from "./preview";
import { WITH_WORDS, WITHOUT_WORDS, ANYWAY_WORDS, KEEP_WORDS, TAB_WORDS } from "./file-print";

const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
const QUICK = "fig.svg";                       // a local picture the route answers at once
const SLOW = "slow.svg";                       // a local picture whose route is parked until the test releases it
const SLOW2 = "slow2.svg";                     // a second one, brought by a reload
const POSTER = "clip.svg";                     // a <video poster>, answered 404
const IMAGE = "d.svg";                         // an svg <image href>, answered 404
const LAZY = "lazy.svg";                       // an <img loading="lazy"> far below the fold, parked
const SWIRL = "/media/romp-swirl-glyph.svg";   // the viewer's loader glyph: a local request of the open's loader
const FONT = "/media/InterVariable.woff2";      // the sheet's font (its @font-face): a local request of the first text paint
/** The two requests every page's render makes of its origin besides its pictures. */
const PAGE_LOCAL = { [SWIRL]: 1, [FONT]: 1 };
// (1) five hosts, one gated picture each: two in the open body, three that never reach the paper
const HOST_ONE = "open-one.test", HOST_TWO = "open-two.test", HOST_TYPED = "typed.test", HOST_CALLOUT = "callout.test", HOST_HIDDEN = "hidden.test";
const NEVER_HOSTS = [HOST_TYPED, HOST_CALLOUT, HOST_HIDDEN];
const FOLDS_NOTE = "# Figures\n\nA local picture ![](" + QUICK + ").\n\n"
  + "Open one ![](https://" + HOST_ONE + "/o1.svg) and open two ![](https://" + HOST_TWO + "/o2.svg).\n\n"
  + "<details><summary>Typed fold</summary><img src=\"https://" + HOST_TYPED + "/t.svg\" alt=\"\"></details>\n\n"
  + "> [!note]- Folded callout\n> ![](https://" + HOST_CALLOUT + "/c.svg)\n\n"
  + "<div hidden><img src=\"https://" + HOST_HIDDEN + "/h.svg\" alt=\"\"></div>\n\nLast line.\n";
// (2) two placeholders on two hosts
const HOST_FIRST = "first.test", HOST_SECOND = "second.test";
const TWO_NOTE = "# Two placeholders\n\nOne ![](https://" + HOST_FIRST + "/a.svg) and two ![](https://" + HOST_SECOND + "/b.svg).\n\nLast line.\n";
// (3) the wait
const SLOW_NOTE = "# Slow\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nLast line.\n";
const SLOW2_NOTE = "# Slow\n\nA local picture ![](" + QUICK + ") and a slower one ![](" + SLOW2 + ").\n\nA session appended a figure.\n";
const HOST_GATED = "other.test";
const GATED_SLOW_NOTE = "# Figures\n\nA local picture ![](" + QUICK + ") and a slow one ![](" + SLOW + ").\n\nA remote one ![](https://" + HOST_GATED + "/o.svg).\n\nLast line.\n";
// (4) the probes and the lazy picture
const MEDIA_NOTE = "# Media\n\nA clip:\n\n<video poster=\"" + POSTER + "\" controls></video>\n\nA diagram:\n\n<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"8\" height=\"8\"><image href=\"" + IMAGE + "\" width=\"8\" height=\"8\"/></svg>\n\nLast line.\n";
const LAZY_NOTE = "# Long\n\n" + Array.from({ length: 300 }, (_, i) => "Paragraph " + (i + 1) + ": lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor lorem ipsum dolor sit amet consectetur adipiscing elit.").join("\n\n") + "\n\n<img loading=\"lazy\" src=\"" + LAZY + "\" alt=\"\">\n\nLast line.\n";
// (6) a host two placeholders share: one in the open body, one inside a closed <details>, whose picture's route is parked
const HOST_SHARED = "shared.test";
const SHARED_OPEN = "/open.svg", SHARED_FOLDED = "/folded.svg";
const SHARED_NOTE = "# Shared host\n\nOpen ![](https://" + HOST_SHARED + SHARED_OPEN + ")\n\n<details><summary>Fold</summary><img src=\"https://" + HOST_SHARED + SHARED_FOLDED + "\" alt=\"\"></details>\n\nLast line.\n";
// (5) the media kinds
const SHORT = "# A short note\n\nOne paragraph, and that is all.\n";
const PNG = ROOT + "/docs/figure.png";
const PDF = ROOT + "/docs/paper.pdf";
const PDF_BYTES = "%PDF-1.4\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n";

const PRINT_BTN = "#romp-fileview .fileview-print";
const WITH_BTN = '#fileview-print-line button:has-text("' + WITH_WORDS + '")';
const WITHOUT_BTN = '#fileview-print-line button:has-text("' + WITHOUT_WORDS + '")';
const ANYWAY_BTN = '#fileview-print-line button:has-text("' + ANYWAY_WORDS + '")';
const KEEP_BTN = '#fileview-print-line button:has-text("' + KEEP_WORDS + '")';
const ARMED_TWO = "2 pictures from other hosts are not loaded.";
const ARMED_ONE = "1 picture from another host is not loaded.";
const PREPARING_ONE = "Preparing 1 picture…";
const STALLED_ONE = "1 picture has not loaded.";

// ── the page's stubs and probes ────────────────────────────────────────────────────────────────────
type Print = { gates: number; incomplete: string[]; line: boolean; at: number };   // `at`: the page's performance.now() at the stub's call, for a bound on when a road printed
type Counts = { prints: number; opens: number; framePrints: number };
type Bar = { phase: string | null; line: string | null; buttons: string[]; titles: string[]; cardUp: boolean };
/** window.print, window.open and the bar as it stands; the PDF frame's print is stubbed on the frame's window when a road
 *  reaches it (stubFramePrint). */
const PAGE_PROBES = () => {
  const w = window as any;
  w.__prints = []; w.__opens = []; w.__framePrints = [];
  const imgs = () => Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[];
  w.print = () => { w.__prints.push({ gates: document.querySelectorAll('[data-act="fv-load"]').length, incomplete: imgs().filter((i) => !i.complete).map((i) => decodeURIComponent(i.src)), line: !!document.getElementById("fileview-print-line"), at: performance.now() }); };
  w.open = (url: unknown, target: unknown) => { w.__opens.push({ url: String(url), target: String(target) }); return { opener: {} }; };
  w.__counts = (): Counts => ({ prints: w.__prints.length, opens: w.__opens.length, framePrints: w.__framePrints.length });
  w.__bar = (): Bar => {
    const b = document.querySelector("#romp-fileview .fileview-bar .fileview-print") as HTMLButtonElement | null;
    const line = document.getElementById("fileview-print-line");
    const btns = line ? Array.from(line.querySelectorAll("button")) : [];
    return { phase: b ? (b.dataset.print || null) : null, line: line ? (line.firstChild && line.firstChild.nodeType === 3 ? (line.firstChild.textContent || "") : line.textContent) : null,
      buttons: btns.map((x) => x.textContent || ""), titles: btns.map((x) => x.title), cardUp: !!document.getElementById("romp-fileview") };
  };
};
const bar = (page: any): Promise<Bar> => page.evaluate(() => (window as any).__bar());
const prints = (page: any): Promise<Print[]> => page.evaluate(() => (window as any).__prints);
const opens = (page: any): Promise<Array<{ url: string; target: string }>> => page.evaluate(() => (window as any).__opens);
const counts = (page: any): Promise<Counts> => page.evaluate(() => (window as any).__counts());
const printsReach = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => (window as any).__prints.length >= k, n, { timeout: 10000 });
const lineReads = (page: any, words: string): Promise<unknown> => page.waitForFunction((w: string) => (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, words, { timeout: 8000 });
const waitGates = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => document.querySelectorAll('[data-act="fv-load"]').length === k, n, { timeout: 10000 });
const pause = (page: any, ms: number): Promise<void> => page.evaluate((k: number) => new Promise<void>((r) => setTimeout(r, k)), ms);
/** Click Print and, in the same task, read what fired before the handler returned. */
const clickPrint = (page: any): Promise<Counts> => page.evaluate(() => { (document.querySelector("#romp-fileview .fileview-print") as HTMLButtonElement).click(); return (window as any).__counts(); });

// ── the ledger and its rows ────────────────────────────────────────────────────────────────────────
type Tally = Record<string, number>;
type Row = { road: string; third: Tally; local: Tally; other: Tally; printed: string };
/** One request's class and key (the header's rule). */
function keyOf(url: string): { cls: "local" | "third" | "other"; key: string } {
  if (url.startsWith(ORIGIN)) {
    const u = new URL(url);
    if (u.pathname === "/file") { const p = u.searchParams.get("path") || ""; return { cls: "local", key: "/file " + (p.startsWith(ROOT + "/") ? p.slice(ROOT.length + 1) : p) }; }
    return { cls: "local", key: u.pathname };
  }
  if (/^https?:/.test(url)) { const u = new URL(url); return { cls: "third", key: u.host + u.pathname }; }
  const u = new URL(url);
  return { cls: "other", key: u.protocol === "blob:" ? "blob:" + u.origin : u.protocol + "//" + u.host };
}
function tally(urls: string[]): { third: Tally; local: Tally; other: Tally } {
  const out = { third: {} as Tally, local: {} as Tally, other: {} as Tally };
  for (const u of urls) { const { cls, key } = keyOf(u); out[cls][key] = (out[cls][key] || 0) + 1; }
  return out;
}
/** What printed during a road, from the stubs' counters before and after. */
function printedWords(before: Counts, after: Counts): string {
  const parts: string[] = [];
  if (after.prints > before.prints) parts.push("window.print x" + (after.prints - before.prints));
  if (after.framePrints > before.framePrints) parts.push("frame print x" + (after.framePrints - before.framePrints));
  if (after.opens > before.opens) parts.push("tab x" + (after.opens - before.opens));
  return parts.length ? parts.join(", ") : "none";
}
const tallyWords = (t: Tally): string => { const ks = Object.keys(t).sort(); return ks.length ? ks.map((k) => k + " x" + t[k]).join(", ") : "none"; };
/** The row as one diagnostic line, the shape the report's table is read from. */
const rowLine = (r: Row): string => "egress | " + r.road + " | third-party: " + tallyWords(r.third) + " | local: " + tallyWords(r.local) + " | other: " + tallyWords(r.other) + " | printed: " + r.printed;

type Scene = { page: any; errors: string[]; requests: string[]; rows: Row[]; mark: number; t: any; release: (names?: string[]) => Promise<void>; heldCount: (name?: string) => number };
/** Six frames and a 250 ms settle: the window in which a road's requests are read (the header). */
async function settle(page: any): Promise<void> { await frames(page, 6); await pause(page, 250); }
/** Run `act` as one road: the ledger's delta from the last mark, what printed, the row asserted against `want` (a plain object
 *  of strings and numbers), the row printed as a diagnostic, and the OTHER class's URLs printed in full on a second line when
 *  there are any (the row counts them by scheme). `want.printed` names the stubs' calls; each tally names URLs and counts.
 *  Returns the row. */
async function road(s: Scene, name: string, want: { third?: Tally; local?: Tally; other?: Tally; printed: string }, act: () => Promise<void>): Promise<Row> {
  const before = await counts(s.page);
  await act();
  await settle(s.page);
  const after = await counts(s.page);
  const delta = s.requests.slice(s.mark);
  s.mark = s.requests.length;
  const row: Row = { road: name, ...tally(delta), printed: printedWords(before, after) };
  s.rows.push(row);
  s.t.diagnostic(rowLine(row));
  const others = delta.filter((u) => keyOf(u).cls === "other");
  if (others.length) s.t.diagnostic("egress-other | " + name + " | " + others.slice().sort().join(" "));   // the set the row's count summarizes, in full, sorted (the browser's issue order varies)
  assert.deepEqual({ third: row.third, local: row.local, other: row.other, printed: row.printed }, { third: want.third || {}, local: want.local || {}, other: want.other || {}, printed: want.printed }, "road: " + name);
  return row;
}
/** The page's end: nothing after the last road, the rows sum to the ledger, no script error, the page closed. */
async function tail(s: Scene, label: string): Promise<void> {
  await settle(s.page);
  const late = s.requests.slice(s.mark);
  assert.deepEqual(late, [], label + ": nothing left the page after the last road");
  const summed = s.rows.reduce((n, r) => n + Object.values(r.third).concat(Object.values(r.local), Object.values(r.other)).reduce((a, b) => a + b, 0), 0);
  assert.equal(summed, s.requests.length, label + ": every request the page made is in some row");
  assert.deepEqual(s.errors, [], label + ": no script error");
  await s.page.close();
}
/** The hosts the page asked, over its whole life. */
const hostsAsked = (s: Scene): string[] => Array.from(new Set(s.requests.filter((u) => /^https?:/.test(u) && !u.startsWith(ORIGIN)).map((u) => new URL(u).host))).sort();

/** The viewer over `note` in `mode`, the ledger installed before the open: the quick picture and the loader glyph answered from
 *  the origin, each of `held` parked (its route held until release()), each of `missing` answered 404, every host under .test
 *  other than the origin answered after 150 ms with the svg, except a URL whose path ends in one of `heldThird`, parked the
 *  same way under that suffix as its name; the probes installed. The first road, the render, is read here. */
async function scene(t: any, browser: any, mode: Mode, note: string, opts: { held?: string[]; heldThird?: string[]; missing?: string[]; waitFor?: string; before?: (pg: any) => Promise<void>; open: { third?: Tally; local?: Tally; other?: Tally } }): Promise<Scene> {
  const heldNames = opts.held || [];
  const heldThird = opts.heldThird || [];
  const missing = opts.missing || [];
  const held: Array<{ name: string; route: any }> = [];
  const requests: string[] = [];
  const { page, errors } = await openViewer(browser, mode, 900, 700, {
    docs: { [REPORT]: note }, waitFor: opts.waitFor,
    serve: (u) => {
      if (u.pathname === SWIRL) return { status: 200, type: "image/svg+xml", body: SVG };
      const p = u.searchParams.get("path") || "";
      if (u.pathname !== "/file") return null;
      if (p.endsWith(QUICK)) return { status: 200, type: "image/svg+xml", body: SVG };
      if (missing.some((n) => p.endsWith(n))) return { status: 404, type: "text/plain", body: "no such file: " + p };
      return null;
    },
    before: async (pg: any) => {
      pg.on("request", (r: any) => { requests.push(r.url()); });
      await pg.route((u: URL) => u.origin === ORIGIN && u.pathname === "/file" && heldNames.some((n) => (u.searchParams.get("path") || "").endsWith(n)), (route: any) => {
        const p = new URL(route.request().url()).searchParams.get("path") || "";
        held.push({ name: heldNames.find((n) => p.endsWith(n))!, route });
      });
      await pg.route((u: URL) => u.origin !== ORIGIN && u.hostname.endsWith(".test"), async (route: any) => {
        const parked = heldThird.find((n) => new URL(route.request().url()).pathname.endsWith(n));
        if (parked) { held.push({ name: parked, route }); return; }
        await new Promise((r) => setTimeout(r, 150)); await route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG });
      });
      await pg.evaluate(PAGE_PROBES);
      if (opts.before) await opts.before(pg);
    },
  });
  const s: Scene = {
    page, errors, requests, rows: [], mark: 0, t,
    heldCount: (name?: string) => held.filter((h) => !name || h.name === name).length,
    release: async (names?: string[]) => {
      const out = held.filter((h) => !names || names.includes(h.name));
      for (const h of out) { held.splice(held.indexOf(h), 1); await h.route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); }
    },
  };
  for (let i = 0; i < 100 && heldNames.some((n) => s.heldCount(n) === 0 && note.includes(n) && n !== LAZY); i++) await frames(page, 1);   // the parked requests of the pictures the note draws (a lazy one is deferred by design)
  await road(s, "open: the render", { ...opts.open, printed: "none" }, async () => {});
  return s;
}
/** Change the file on disk and raise the changed-on-disk bar through the viewer's own probe (a window focus runs one HEAD, whose
 *  moved mtime raises the bar), then click its Reload. */
async function reloadTo(page: any, note: string): Promise<void> {
  await page.evaluate(([p, n, mt]: [string, string, string]) => { const w = window as any; w.__docs[p] = n; w.__mtime = mt; }, [REPORT, note, MT2]);
  await page.evaluate(() => { window.dispatchEvent(new Event("focus")); });
  await page.waitForFunction(() => { const b = document.querySelector("#fileview-save-err button") as HTMLButtonElement | null; return !!b && b.textContent === "Reload"; }, null, { timeout: 10000 });
  await page.click("#fileview-save-err button");
}

// ── (1) the gated note: Escape, a second press, without them, with them ─────────────────────────────

test("(1) a gated note with five placeholders on five hosts, two printable: the render asks the origin alone; a press then Escape, a press then a second press and a press then Print without them ask nothing; Print with them asks the two printable hosts once each and the typed fold's, the folded callout's and the hidden div's hosts never", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(t, browser, "pane", FOLDS_NOTE, { open: { local: { ["/file docs/" + QUICK]: 1, ...PAGE_LOCAL } } });
    const { page } = s;
    await waitGates(page, 5);
    const placed = await page.evaluate(() => Array.from(document.querySelectorAll('#romp-fileview [data-act="fv-load"]')).map((g) => { const d = g.closest("details"); return (g.getAttribute("data-fv-hosts") || "") + ":" + (g.closest("[hidden]") ? "hidden" : d ? (d.hasAttribute("open") ? "open-details" : "closed-details") : "body"); }));
    assert.deepEqual(placed, [HOST_ONE + ":body", HOST_TWO + ":body", HOST_TYPED + ":closed-details", HOST_CALLOUT + ":closed-details", HOST_HIDDEN + ":hidden"], "five placeholders: two in the open body, two in closed details (the typed fold and the folded callout), one under hidden");
    await road(s, "press over the placeholders, then Escape", { printed: "none" }, async () => {
      await page.click(PRINT_BTN);
      const b = await bar(page);
      assert.equal(b.phase, "armed"); assert.equal(b.line, ARMED_TWO, "the two printable placeholders are counted");
      assert.deepEqual(b.titles.slice(0, 1), ["Load the pictures from " + HOST_ONE + " and " + HOST_TWO + ", then print"], "the title names the two printable hosts alone");
      await page.keyboard.press("Escape");
      await frames(page, 1);
      assert.equal((await bar(page)).phase, null, "Escape disarmed");
    });
    await road(s, "press, then a second press (the chord)", { printed: "none" }, async () => {
      await page.click(PRINT_BTN);
      assert.equal((await bar(page)).phase, "armed");
      await page.keyboard.press("Control+p");
      await frames(page, 1);
      const b = await bar(page);
      assert.equal(b.phase, null, "the second press disarmed"); assert.equal(b.cardUp, true);
    });
    await road(s, "press, then Print without them", { printed: "window.print x1" }, async () => {
      await page.click(PRINT_BTN);
      await page.click(WITHOUT_BTN);
      await printsReach(page, 1);
      const p = await prints(page);
      assert.equal(p[0].gates, 5, "every placeholder kept"); assert.deepEqual(p[0].incomplete, [], "every <img> complete at the print");
    });
    await road(s, "press, then Print with them", { third: { [HOST_ONE + "/o1.svg"]: 1, [HOST_TWO + "/o2.svg"]: 1 }, printed: "window.print x1" }, async () => {
      await page.click(PRINT_BTN);
      assert.equal((await bar(page)).line, ARMED_TWO);
      await page.click(WITH_BTN);
      await printsReach(page, 2);
      const p = await prints(page);
      assert.equal(p[1].gates, 3, "the three placeholders that never reach the paper still stand"); assert.deepEqual(p[1].incomplete, [], "every <img> complete at the print");
    });
    assert.deepEqual(hostsAsked(s), [HOST_ONE, HOST_TWO].sort(), "over the page's life exactly the two printable hosts were asked");
    for (const h of NEVER_HOSTS) assert.equal(s.requests.some((u) => u.includes("//" + h + "/")), false, h + " was never asked");
    await tail(s, "(1)");
  });
});

// ── (2) a placeholder activated by hand under the armed line ───────────────────────────────────────

test("(2) two placeholders: a press arms over both; the first activated by hand under the armed line asks its host once and the recount narrows the line and the title to the second; Print with them then asks the second host once", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(t, browser, "chat", TWO_NOTE, { open: { local: { ...PAGE_LOCAL } } });
    const { page } = s;
    await waitGates(page, 2);
    await road(s, "press (armed over two), the first placeholder activated by hand, the recount", { third: { [HOST_FIRST + "/a.svg"]: 1 }, printed: "none" }, async () => {
      await page.click(PRINT_BTN);
      let b = await bar(page);
      assert.equal(b.phase, "armed"); assert.equal(b.line, ARMED_TWO);
      assert.deepEqual(b.titles.slice(0, 1), ["Load the pictures from " + HOST_FIRST + " and " + HOST_SECOND + ", then print"]);
      await page.click('#romp-fileview [data-act="fv-load"]');
      await waitGates(page, 1);
      b = await bar(page);
      assert.equal(b.phase, "armed", "still armed over the one left"); assert.equal(b.line, ARMED_ONE, "the recount");
      assert.deepEqual(b.titles.slice(0, 1), ["Load the pictures from " + HOST_SECOND + ", then print"], "the title names the host left alone");
    });
    await road(s, "then Print with them over the one left", { third: { [HOST_SECOND + "/b.svg"]: 1 }, printed: "window.print x1" }, async () => {
      await page.click(WITH_BTN);
      await printsReach(page, 1);
      const p = await prints(page);
      assert.equal(p[0].gates, 0); assert.deepEqual(p[0].incomplete, []);
    });
    assert.deepEqual(hostsAsked(s), [HOST_FIRST, HOST_SECOND].sort());
    await tail(s, "(2)");
  });
});

// ── (3) the wait: a landing, the deadline's ask, Print anyway, Keep waiting ────────────────────────

test("(3) the wait. A Reload landing during the wait requests the landing's pictures once and the print comes at the landing's picture's release; the deadline into the ask then Print anyway, and the ask then Keep waiting and the route released, each print once and ask nothing more", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    // a: the landing
    let s = await scene(t, browser, "pane", SLOW_NOTE, { held: [SLOW, SLOW2], open: { local: { ["/file docs/" + QUICK]: 1, ["/file docs/" + SLOW]: 1, ...PAGE_LOCAL } } });
    let page = s.page;
    assert.equal(s.heldCount(SLOW), 1, "the slow picture's request is parked");
    await road(s, "press: the wait over the parked picture", { printed: "none" }, async () => {
      await page.click(PRINT_BTN);
      const b = await bar(page);
      assert.equal(b.phase, "preparing"); assert.equal(b.line, PREPARING_ONE);
    });
    await road(s, "a Reload landing during the wait", { local: { ["/file docs/" + SLOW2]: 1 }, printed: "none" }, async () => {
      await reloadTo(page, SLOW2_NOTE);
      await page.waitForFunction((n: string) => (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).some((i) => decodeURIComponent(i.src).includes("/docs/" + n)), SLOW2, { timeout: 10000 });
      for (let i = 0; i < 100 && s.heldCount(SLOW2) === 0; i++) await frames(page, 1);
      assert.equal(s.heldCount(SLOW2), 1, "the landing's picture is requested and parked");
      const b = await bar(page);
      assert.equal(b.phase, "preparing", "the wait goes on over the new body"); assert.equal(b.line, PREPARING_ONE);
    });
    await road(s, "the old body's picture released (detached: no print), then the landing's picture released", { printed: "window.print x1" }, async () => {
      await s.release([SLOW]);
      await frames(page, 6);
      assert.equal((await prints(page)).length, 0, "the detached picture's landing prints nothing");
      await s.release([SLOW2]);
      await printsReach(page, 1);
      assert.deepEqual((await prints(page))[0].incomplete, [], "every <img> of the body complete at the print");
    });
    await tail(s, "(3a)");
    // b: the deadline's ask, then Print anyway
    s = await scene(t, browser, "pane", GATED_SLOW_NOTE, { held: [SLOW], open: { local: { ["/file docs/" + QUICK]: 1, ["/file docs/" + SLOW]: 1, ...PAGE_LOCAL } } });
    page = s.page;
    await waitGates(page, 1);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(300); });
    await road(s, "press, Print without them, the deadline into the ask", { printed: "none" }, async () => {
      await page.click(PRINT_BTN);
      await page.click(WITHOUT_BTN);
      assert.equal((await bar(page)).line, PREPARING_ONE);
      await lineReads(page, STALLED_ONE);
      const b = await bar(page);
      assert.equal(b.phase, "stalled"); assert.deepEqual(b.buttons, [ANYWAY_WORDS, KEEP_WORDS]);
    });
    await road(s, "Print anyway", { printed: "window.print x1" }, async () => {
      await page.click(ANYWAY_BTN);
      const p = await prints(page);
      assert.equal(p.length, 1); assert.equal(p[0].incomplete.length, 1, "the parked picture prints as the browser has it"); assert.equal(p[0].gates, 1, "the placeholder kept");
      assert.equal(s.heldCount(SLOW), 1, "its request is still parked");
    });
    assert.deepEqual(hostsAsked(s), [], "the gated host was never asked");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    await tail(s, "(3b)");
    // c: the ask, then Keep waiting and the release
    s = await scene(t, browser, "pane", GATED_SLOW_NOTE, { held: [SLOW], open: { local: { ["/file docs/" + QUICK]: 1, ["/file docs/" + SLOW]: 1, ...PAGE_LOCAL } } });
    page = s.page;
    await waitGates(page, 1);
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(300); });
    await road(s, "press, Print without them, the deadline into the ask (again)", { printed: "none" }, async () => {
      await page.click(PRINT_BTN);
      await page.click(WITHOUT_BTN);
      await lineReads(page, STALLED_ONE);
    });
    await road(s, "Keep waiting, then the parked route released", { printed: "window.print x1" }, async () => {
      await page.click(KEEP_BTN);
      let b = await bar(page);
      assert.equal(b.phase, "preparing"); assert.equal(b.line, PREPARING_ONE);
      await pause(page, 700);
      assert.equal((await prints(page)).length, 0, "no print past the seam's deadline: Keep waiting set no timer");
      await s.release([SLOW]);
      await printsReach(page, 1);
      const p = await prints(page);
      assert.deepEqual(p[0].incomplete, [], "every <img> complete at the print"); assert.equal(p[0].gates, 1);
      await frames(page, 1);
      b = await bar(page);
      assert.equal(b.phase, null, "the bar rested");
    });
    assert.deepEqual(hostsAsked(s), [], "the gated host was never asked");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    await tail(s, "(3c)");
  });
});

// ── (4) the probes and the lazy picture ────────────────────────────────────────────────────────────

test("(4) a <video poster> and an svg <image href> whose routes answer 404: the render asks once each, a press asks once more each and prints, a second press the same; an <img loading=\"lazy\"> far below the fold: not requested by the render, requested once at the press, the print at its release", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    let s = await scene(t, browser, "pane", MEDIA_NOTE, { missing: [POSTER, IMAGE], open: { local: { ["/file docs/" + POSTER]: 1, ["/file docs/" + IMAGE]: 1, ...PAGE_LOCAL } } });
    let page = s.page;
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the product's deadline: nothing shortened it here");
    for (const name of ["press: one probe per URL, the print at once", "a second press: one probe per URL again"]) {
      await road(s, name, { local: { ["/file docs/" + POSTER]: 1, ["/file docs/" + IMAGE]: 1 }, printed: "window.print x1" }, async () => {
        const n = (await prints(page)).length;
        await page.click(PRINT_BTN);
        await printsReach(page, n + 1);
      });
    }
    await tail(s, "(4a)");
    s = await scene(t, browser, "pane", LAZY_NOTE, { held: [LAZY], open: { local: { ...PAGE_LOCAL } } });
    page = s.page;
    const lazyFacts = (): Promise<{ loading: string | null; complete: boolean }> => page.evaluate((n: string) => {
      const img = (Array.from(document.querySelectorAll("#romp-fileview img")) as HTMLImageElement[]).find((i) => decodeURIComponent(i.src).includes("/docs/" + n)) || null;
      return { loading: img ? img.getAttribute("loading") : null, complete: !!img && img.complete };
    }, LAZY);
    assert.deepEqual(await lazyFacts(), { loading: "lazy", complete: false }, "the lazy picture stands unfetched after the render");
    await road(s, "press: the lazy picture set eager, its fetch started (parked)", { local: { ["/file docs/" + LAZY]: 1 }, printed: "none" }, async () => {
      await page.click(PRINT_BTN);
      for (let i = 0; i < 120 && s.heldCount(LAZY) === 0; i++) await frames(page, 1);
      assert.equal(s.heldCount(LAZY), 1, "the press started the deferred fetch");
      assert.equal((await lazyFacts()).loading, "eager");
      assert.equal((await bar(page)).line, PREPARING_ONE);
    });
    await road(s, "the lazy picture's route released", { printed: "window.print x1" }, async () => {
      await s.release([LAZY]);
      await printsReach(page, 1);
      assert.deepEqual((await prints(page))[0].incomplete, []);
    });
    await tail(s, "(4b)");
  });
});

// ── (5) the media kinds: a picture opened directly, a PDF under two launches ───────────────────────

/** Open a binary file through the harness (the media leg's idiom): the page's fetch answers the path with the blob, a PNG
 *  drawn on a canvas or the one-page PDF, under the kernel's Content-Type; the viewer's media branch paints the picture or
 *  the frame. */
async function openMedia(page: any, path: string, kind: "png" | "pdf"): Promise<void> {
  await page.evaluate(async ([p, sid, k, pdf]: [string, string, string, string]) => {
    const w = window as any; let blob: Blob;
    if (k === "png") { const c = document.createElement("canvas"); c.width = 40; c.height = 30; const g = c.getContext("2d")!; g.fillStyle = "#3a7bd5"; g.fillRect(0, 0, 40, 30); blob = await new Promise<Blob>((r) => c.toBlob((b) => r(b!), "image/png")); }
    else blob = new Blob([pdf], { type: "application/pdf" });
    const prev = w.fetch;
    w.fetch = async function (url: any, init: any) { const m = /[?&]path=([^&]*)/.exec(String(url)); if (m && decodeURIComponent(m[1]) === p && !(init && init.method === "HEAD")) return new Response(blob, { status: 200, headers: { "Content-Type": k === "png" ? "image/png" : "application/pdf", "X-Romp-Mtime-Ns": w.__mtime } }); return prev(url, init); };
    w.FV.openFileView(p, sid, null);
  }, [path, SID, kind, PDF_BYTES]);
  if (kind === "png") await page.waitForFunction(() => { const i = document.querySelector("#romp-fileview img.fileview-img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
  else await page.waitForFunction(() => !!document.querySelector("#romp-fileview iframe.fileview-frame"), null, { timeout: 10000 });
  await frames(page, 3);
}

test("(5a) a picture opened directly: its bytes come through the page's fetch and its <img> is a blob: URL, for which the intercept reports no request, so the open asks for nothing; a press prints at once and asks nothing", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(t, browser, "pane", SHORT, { open: { local: { ...PAGE_LOCAL } } });
    const { page } = s;
    await road(s, "open a picture directly (a replace-open over the note)", { printed: "none" }, async () => { await openMedia(page, PNG, "png"); });
    assert.equal(await page.evaluate(() => (document.querySelector("#romp-fileview img.fileview-img") as HTMLImageElement).src.startsWith("blob:")), true, "the picture's <img> is at a blob: URL");
    await road(s, "press over the picture", { printed: "window.print x1" }, async () => {
      const fired = await clickPrint(page);
      assert.equal(fired.prints, 1, "one click printed the page at once, before the handler returned");
      assert.deepEqual((await prints(page))[0].incomplete, []);
    });
    await tail(s, "(5a)");
  });
});

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }
type Variant = "shell" | "chromium";
/** Run `body` in each launch this box has: Playwright's default headless shell and the full Chromium build (channel
 *  "chromium"); a launch that fails is noted and skipped, and the test skips loudly when neither launches. */
async function inBrowsers(t: any, body: (browser: any, variant: Variant) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let ran = 0;
  for (const [variant, launch] of [["shell", () => pw.chromium.launch()], ["chromium", () => pw.chromium.launch({ channel: "chromium" })]] as Array<[Variant, () => Promise<any>]>) {
    let browser: any;
    try { browser = await launch(); }
    catch (e) { t.diagnostic(variant + ": no such browser on this box (CI installs none): " + String((e as Error).message).split("\n")[0]); continue; }
    try { await body(browser, variant); ran++; } finally { await browser.close(); }
  }
  if (ran === 0) t.skip("no playwright browser on this box; the browser leg needs one (CI installs none)");
}
const frameHolds = (page: any): Promise<boolean> => page.evaluate(() => { const f = document.querySelector("#romp-fileview iframe.fileview-frame") as HTMLIFrameElement | null; try { return !!f && (f.contentWindow as any).document.contentType === "application/pdf"; } catch { return false; } });
/** Stub the frame window's print to record its calls (the parent may set it on a same-origin blob frame). */
const stubFramePrint = (page: any): Promise<void> => page.evaluate(() => { const w = (document.querySelector("#romp-fileview iframe.fileview-frame") as HTMLIFrameElement).contentWindow as any; w.print = () => { (window as any).__framePrints.push(1); }; });
const unprintableFrame = (page: any): Promise<void> => page.evaluate(() => { const w = (document.querySelector("#romp-fileview iframe.fileview-frame") as HTMLIFrameElement).contentWindow as any; w.print = undefined; });

test("(5b) a PDF under the two launches: the open asks the origin for nothing (the shell reports the frame's blob: navigation, the full Chromium build its PDF viewer's own files); the frame's own print (the full build) asks nothing; the /file tab through the stubbed window.open (the shell of itself, the full build once print is taken from the frame) asks nothing", { timeout: 180000 }, async (t) => {
  await inBrowsers(t, async (browser, variant) => {
    const downloads: string[] = [];
    const s = await scene(t, browser, "pane", SHORT, { open: { local: { ...PAGE_LOCAL } }, before: async (pg: any) => { pg.on("download", (d: any) => { downloads.push(d.suggestedFilename()); }); } });
    const { page } = s;
    let holds = false;
    const opened = variant === "chromium" ? { "chrome-extension://mhjfbmdgcfjbbpaeojofohoefgiehjai": 9, "chrome://resources": 8 } : { ["blob:" + ORIGIN]: 1 };   // the full build's PDF viewer loads its own files in place of the blob: navigation the shell reports (the header)
    await road(s, variant + ": open a PDF (a replace-open over the note)", { other: opened, printed: "none" }, async () => {
      await openMedia(page, PDF, "pdf");
      holds = await frameHolds(page);
      for (let i = 0; i < 50 && !holds && downloads.length === 0; i++) { await pause(page, 100); holds = await frameHolds(page); }
    });
    if (variant === "chromium") assert.equal(holds, true, "the full build's PDF viewer holds the document in the frame");
    else assert.equal(holds, false, "the headless shell has no PDF viewer: the frame's navigation became a download (" + downloads.join(", ") + ")");
    if (holds) {
      await stubFramePrint(page);
      await road(s, variant + ": press, the frame prints the document", { printed: "frame print x1" }, async () => {
        const fired = await clickPrint(page);
        assert.equal(fired.framePrints, 1, "the frame's print was called once, inside the click's own task"); assert.equal(fired.prints, 0); assert.equal(fired.opens, 0);
        assert.equal((await bar(page)).line, null, "no line: the frame printed");
      });
      await unprintableFrame(page);
    }
    await road(s, variant + ": press, the /file tab (window.open stubbed)" + (holds ? ", print taken from the frame's window" : ""), { printed: "tab x1" }, async () => {
      const fired = await clickPrint(page);
      assert.equal(fired.opens, 1, "one tab opened, inside the click's own task"); assert.equal(fired.prints, 0, "the page's print never fires for a PDF");
      assert.deepEqual((await opens(page))[0], { url: fileUrl(PDF, SID), target: "_blank" }, "the kernel's /file URL in a new tab");
      assert.equal((await bar(page)).line, TAB_WORDS);
    });
    await tail(s, "(5b " + variant + ")");
  });
});

// ── (6) a host two placeholders share, the folded picture's route parked ───────────────────────────

test("(6) two placeholders on one host, one in the open body and one inside a closed <details>, the folded picture's route parked: Print with them restores the open placeholder alone and asks the host for its URL once; the folded placeholder stands, its URL never asked, so the parked route holds nothing; the wait counts the open picture and prints at its load, under the deadline, with no ask (FAILS BEFORE the per-placeholder restore: the host was loaded whole and the folded URL asked and parked; before the printable filter the line read two pictures, the deadline asked about the folded one, and nothing printed)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(t, browser, "pane", SHARED_NOTE, { heldThird: [SHARED_FOLDED], open: { local: { ...PAGE_LOCAL } } });
    const { page } = s;
    await waitGates(page, 2);
    const placed = await page.evaluate(() => Array.from(document.querySelectorAll('#romp-fileview [data-act="fv-load"]')).map((g) => { const d = g.closest("details"); return (g.getAttribute("data-fv-hosts") || "") + ":" + (d ? (d.hasAttribute("open") ? "open-details" : "closed-details") : "body"); }));
    assert.deepEqual(placed, [HOST_SHARED + ":body", HOST_SHARED + ":closed-details"], "two placeholders naming one host: one in the open body, one inside a closed details");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(2000); });   // a deadline the road can reach: the print is bound to come well before it, and the module before the printable filter asked at it
    await road(s, "press, then Print with them over the shared host (the folded picture's route parked)", { third: { [HOST_SHARED + SHARED_OPEN]: 1 }, printed: "window.print x1" }, async () => {
      await page.click(PRINT_BTN);
      const armed = await bar(page);
      assert.equal(armed.phase, "armed"); assert.equal(armed.line, ARMED_ONE, "the open placeholder alone is counted");
      assert.deepEqual(armed.titles.slice(0, 1), ["Load the pictures from " + HOST_SHARED + ", then print"], "the title names the one host");
      const clickAt: number = await page.evaluate(() => performance.now());
      await page.click(WITH_BTN);
      const afterClick = (await bar(page)).line;   // the wait's line as the click left it
      // the print, or the deadline's ask about the folded picture, whichever comes first
      await page.waitForFunction((w: string) => (window as any).__prints.length >= 1 || (document.getElementById("fileview-print-line")?.firstChild?.textContent || "") === w, STALLED_ONE, { timeout: 10000 });
      await frames(page, 1);
      const end = await bar(page);
      const p = await prints(page);
      const outcome = { afterClick, prints: p.length, phase: end.phase, line: end.line, foldedParked: s.heldCount(SHARED_FOLDED),
        printedUnderDeadline: p.length ? p[0].at - clickAt < 1500 : null, gates: p.length ? p[0].gates : null, incomplete: p.length ? p[0].incomplete : null };
      assert.deepEqual(outcome, { afterClick: PREPARING_ONE, prints: 1, phase: null, line: null, foldedParked: 0, printedUnderDeadline: true, gates: 1, incomplete: [] },
        "FAILS BEFORE: the wait counted the open picture alone and printed at its load under the deadline; the folded placeholder stands at the print (gates 1), its route was never asked (nothing parked), and every <img> in the body is complete");
    });
    assert.deepEqual(hostsAsked(s), [HOST_SHARED], "the one host was asked, once: for the open placeholder's URL");
    assert.equal(s.requests.filter((u) => u === "https://" + HOST_SHARED + SHARED_FOLDED).length, 0, "the folded placeholder's URL was never asked");
    await page.evaluate(() => { (window as any).FV.setPrintSettleMs(null); });
    assert.equal(await page.evaluate(() => (window as any).FV.printSettleMs()), 8000, "the seam restored");
    await tail(s, "(6)");
  });
});

test("(7) two placeholders on one host, one in the open body and one inside a closed <details>, both routes answering: Print with them asks the host ONCE, for the open placeholder's URL alone (per host: 1 host asked, 1 request; per placeholder: 1 of 2 restored), the folded placeholder standing at the print; a Reload of the same note then shows both placeholders again and asks nothing, since the print granted the host nothing for the page (FAILS BEFORE: the host was loaded whole, both URLs asked, and the Reload showed no placeholder)", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const s = await scene(t, browser, "pane", SHARED_NOTE, { open: { local: { ...PAGE_LOCAL } } });
    const { page } = s;
    await waitGates(page, 2);
    const gatesNow = (): Promise<string[]> => page.evaluate(() => Array.from(document.querySelectorAll('#romp-fileview [data-act="fv-load"]')).map((g) => (g.getAttribute("data-fv-hosts") || "") + ":" + (g.closest("details") ? "closed-details" : "body")));
    assert.deepEqual(await gatesNow(), [HOST_SHARED + ":body", HOST_SHARED + ":closed-details"], "two placeholders naming one host");
    await road(s, "press, then Print with them over the shared host (both routes answering)", { third: { [HOST_SHARED + SHARED_OPEN]: 1 }, printed: "window.print x1" }, async () => {
      await page.click(PRINT_BTN);
      const armed = await bar(page);
      assert.equal(armed.line, ARMED_ONE, "the open placeholder alone is counted");
      assert.deepEqual(armed.titles.slice(0, 1), ["Load the pictures from " + HOST_SHARED + ", then print"]);
      await page.click(WITH_BTN);
      await printsReach(page, 1);
      const p = await prints(page);
      assert.deepEqual({ gates: p[0].gates, incomplete: p[0].incomplete }, { gates: 1, incomplete: [] }, "FAILS BEFORE: the folded placeholder stands at the print (one of the two restored) and the open picture is complete");
      assert.deepEqual(await gatesNow(), [HOST_SHARED + ":closed-details"], "per placeholder: the open one restored, the folded one standing");
    });
    // per host and per placeholder, read apart over the page so far
    const perHost = { hosts: hostsAsked(s), requests: s.requests.filter((u) => u.startsWith("https://" + HOST_SHARED + "/")).length };
    const perPlaceholder = { open: s.requests.filter((u) => u === "https://" + HOST_SHARED + SHARED_OPEN).length, folded: s.requests.filter((u) => u === "https://" + HOST_SHARED + SHARED_FOLDED).length };
    assert.deepEqual(perHost, { hosts: [HOST_SHARED], requests: 1 }, "per host: one host asked, one request");
    assert.deepEqual(perPlaceholder, { open: 1, folded: 0 }, "FAILS BEFORE: per placeholder, the open one's URL once and the folded one's never");
    // a later render of the same host in the same page: no page-life grant, so both figures are gated again and nothing is asked
    await road(s, "a Reload of the same note after the print", { printed: "none" }, async () => {
      await reloadTo(page, SHARED_NOTE);
      await waitGates(page, 2);
      assert.deepEqual(await gatesNow(), [HOST_SHARED + ":body", HOST_SHARED + ":closed-details"], "FAILS BEFORE: both placeholders are back (the host was granted for the page, and the Reload showed the pictures)");
    });
    await tail(s, "(7)");
  });
});
