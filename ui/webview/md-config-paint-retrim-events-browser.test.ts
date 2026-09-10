// The Comments panel's re-trim on the layout changes that are not a width reflow, and its filing of a change whose every mark the
// pass's trim removed (file-comments.ts scheduleRetrim, layoutPass and paintAll; the Slice 4 review's round 13), in headless
// Chromium over the REAL viewer and panel (real-viewer-leg.ts: file-view.ts bundled as the webview build bundles it, the Files
// pane under styles.css and files-pane.css, the kernel's status answered from the page; the two Inter faces served from the
// extension's media directory, as the kernel serves them, so the sheet's font loads as it does in the pane).
// 1. A figure's bytes landing after the paint (its /file route held until the panel has painted, then a 300 x 20 svg): the image
//    grows from nothing to its size, the item's lines re-wrap, and the space at each new wrap point is a blank mark of zero width
//    with a box of its own (the sheet's 4 px of padding around nothing, a ringed 4 x 18 px box at the end of a line). The seam
//    reports no reflow for it (the body's width did not move, and the width observer's report is the only source of "reflow"), so
//    the panel hears the body's `load` (captured) and re-trims in the next frame: no padding-only mark after the load, fewer blank
//    marks than before it (the new wrap points' unwrapped), the paint and reflow counts unmoved. A gated figure's restored media
//    loads through the same event.
// 2. A font face arriving after the paint (Inter's regular woff2 held until the panel has painted; the sheet's `font-display: swap`
//    shows the fallback face first): every glyph's width changes, the lines re-wrap, the same shape; the panel hears the document's
//    FontFaceSet `loadingdone` and re-trims in the next frame. The leg's theme CSS names a monospace fallback for the note's text so
//    the swap moves every wrap point on any box, whatever its own sans-serif; the mechanism is the sheet's swap and the FontFaceSet's
//    event, not the faces.
// 3. A change whose every mark the pass's trim removed (an insertion of one zero-width space, U+200B, between two inline elements:
//    indexed as a character, painted, laid out at zero width) is filed as not shown: its card wears the "not shown" tag and offers
//    Reveal, its reference is no link, as the unbatched paint (paintRendered returning null) files it; a control insertion of a
//    word paints and links. Before the fix the batched pass filed the id as painted before the trim ran, and the card claimed a mark
//    the body did not hold. A whitespace insertion cannot reach the shape: the index records non-whitespace characters alone, so a
//    `\s`-only insertion is filed unpainted in both call shapes.
// 4. A paint pass made while the pane is hidden (the Files pane in a display:none iframe, the phone shell's every tab switch; a
//    status landing meanwhile repaints the highlights inside it) keeps every blank mark, since each measures no width and no box
//    of its own (the trim's hidden-ancestor guard), and shown again the wrap points' marks would be the sheet's padding around
//    nothing. Two paths re-trim the show, by whether a lifecycle update ran in the hidden frame between the hide and the show. One
//    did (a hide that outlasts a frame): the body's ResizeObserver reports the hide, contentRect 0, and the show after it, so the
//    seam's width observer reports each as a reflow and the reflow hook re-trims on the show. None did (the hide and the show in
//    one task): no observer reports either, the body's size stays the one last observed, and the frame the panel asked for when a
//    trim found the body without a box (trimBlanks, scheduleRetrim) is the first after the show and re-trims there; a frame that
//    still finds no box re-arms nothing. A hidden frame is not frameless: headless Chromium runs a display:none same-origin frame's
//    requestAnimationFrame at full rate (round 14's probes: 26 callbacks in 400 ms hidden, and the observer reported every hide that
//    outlasted a frame, 10 of 10), so in the first case the frame the hide's trim armed runs hidden, keeps every mark and re-arms
//    nothing, and the reflow report does the show's work; round 13 recorded that frame as the first after the show, which holds in
//    the second case alone. The leg pins the second case: the shell hides the pane, runs the panel's paint pass inside it (the
//    inline toggle: toggleInline runs paintAll) and shows it again in ONE task, so no lifecycle update can run in the hidden frame
//    between; after the show no padding-only mark stands, the wrap points' blanks are unwrapped, and the seam reported no reflow.
// 5. The first case, and the re-arm's price: the pane hidden until the seam reports the hide (a reflow at no width), frames run in
//    the hidden pane, the panel's paint pass runs inside it, more frames run, the pane is shown and the seam reports the show. The
//    trim calls are counted off anchor-map.ts TRIM_STATS (every trimCollapsedMarks call resets its pass count, so the page counts the
//    resets): while hidden, two per event (the event's own trim, which finds no box and arms a frame, and that frame's, which re-arms
//    nothing), fewer than the frames that ran, so never per frame; on the show one per reflow report, none from the frame the hidden
//    trims armed, which was spent hidden; after the show no padding-only mark stands and the wrap points' blanks are unwrapped.
// The Comments panel polls every 2.5 s and HEADs the sidecar and the config through fetch; the harness's stub answers those paths
// 404, a move against the status's mtimes, so every tick would refresh and repaint the marks, a repaint the legs must not mistake
// for their re-trim: the page answers those two HEADs with the status's own mtimes, as the kernel would (quietPoll).
// Every scene keeps the body scrolling (filler paragraphs), so no scrollbar comes or goes with the load and the body's width holds:
// a reflow would re-trim too and hide the path under test, and the legs assert the reflow count unmoved. Legs await the events' own
// counts and frames, never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an
// invented report, /repo/notes-api paths, the placeholder sid.
import * as fs from "node:fs";
import * as path from "node:path";
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openPanel, pageHtml, frames, REPORT, SID, MT, ORIGIN, STATUS, EXT } from "./real-viewer-leg";

const T0 = 1757145600000;
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="20"><rect width="300" height="20" fill="gray"/></svg>';
const FILLER = Array.from({ length: 30 }, (_, i) => `Filler ${i + 1}: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt.`).join("\n\n");
/** Sixty links with no space inside a label, so a line can break only at the spaces between them, which the highlight marks. */
const LINKS = Array.from({ length: 60 }, (_, i) => "[Link" + i + "](#l" + i + ")").join(" ");
const ITEM = "Text before ![pic](pic.svg) " + LINKS;
const NOTE = "# Report\n\nIntro para. with a few words before the item.\n\n- " + ITEM + "\n\nAfter para. closing the report.\n\n" + FILLER + "\n";
const commentOn = (n: number, quote: string, prefix: string, suffix: string) => ({ id: `${T0 + n}-${n}`, author: "you", ts: T0 + n, body: `Note ${n}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });
const COMMENTS = [commentOn(1, ITEM, "- ", "\n\nAfter")];
const COMMENTED = { ...STATUS, store: { ...STATUS.store, comments: COMMENTS }, unsent: { ...STATUS.unsent, comments: COMMENTS.map((c) => c.id) } };
const media = (f: string): Buffer => fs.readFileSync(path.join(EXT, "media", f));
const INTER = media("InterVariable.woff2"), INTER_ITALIC = media("InterVariable-Italic.woff2");
/** The note's text on a monospace fallback until Inter lands (leg 2): the swap then moves every wrap point, on any box. */
const MONO_FALLBACK = '.fileview-md { font-family: "Inter", monospace; }';

type Hold = { release: () => void; requests: number };
/** Serve the harness page, the note's picture and the two Inter faces; the picture or the regular face waits for release() when
 *  `hold` names it. */
async function serve(page: any, html: string, hold: "pic" | "font" | null): Promise<Hold> {
  let release: () => void = () => {};
  const gate = new Promise<void>((r) => { release = r; });
  const h: Hold = { release, requests: 0 };
  await page.route((u: URL) => u.href.startsWith(ORIGIN), async (route: any) => {
    const u = new URL(route.request().url());
    const p = u.pathname === "/file" ? decodeURIComponent(u.searchParams.get("path") || "") : "";
    if (p.endsWith("/pic.svg")) { if (hold === "pic") { h.requests++; await gate; } return route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG }); }
    if (u.pathname === "/media/InterVariable.woff2") { if (hold === "font") { h.requests++; await gate; } return route.fulfill({ status: 200, contentType: "font/woff2", body: INTER }); }
    if (u.pathname === "/media/InterVariable-Italic.woff2") return route.fulfill({ status: 200, contentType: "font/woff2", body: INTER_ITALIC });
    return route.fulfill({ status: 200, contentType: "text/html", body: html });
  });
  return h;
}

type Read = { paints: number; reflows: number; marks: number; blankMarks: number; paddingOnly: string[]; loads: number; fontsDone: number; imgWidth: number; fontStatus: string };
/** The probe's counts, the marks, and the trim's oracle over the body: the blank marks of zero content width with a box of their
 *  own (padding-only); with them the page's event counts (the captured loads, the FontFaceSet's loadingdone), the picture's laid-out
 *  width and the regular Inter face's status. */
const read = (page: any): Promise<Read> => page.evaluate(() => {
  const w = window as any; const body = document.querySelector(".fileview-body") as HTMLElement;
  const BLANK = /^(?:[^\p{L}\p{N}\p{P}\p{S}]|[\u115f\u1160\u3164\uffa0])*$/u;
  const width = (n: Node) => { const r = document.createRange(); r.selectNodeContents(n); let x = 0; for (const b of Array.from(r.getClientRects())) x += b.width; return x; };
  const marks = Array.from(body.querySelectorAll("mark.fc-hl"));
  const blanks = marks.filter((k) => BLANK.test(k.textContent || ""));
  const paddingOnly = blanks.filter((k) => width(k) === 0 && k.getClientRects().length > 0).map((k) => k.parentElement!.tagName + " " + JSON.stringify(k.textContent));
  const img = body.querySelector(".fileview-md img") as HTMLImageElement | null;
  let fontStatus = "none";
  (document as any).fonts.forEach((f: any) => { if (f.family.replace(/"/g, "") === "Inter" && f.style === "normal") fontStatus = f.status; });
  return { paints: w.__paints, reflows: w.__reflows, marks: marks.length, blankMarks: blanks.length, paddingOnly, loads: w.__loads, fontsDone: w.__fontsDone, imgWidth: img ? img.getBoundingClientRect().width : -1, fontStatus };
});
/** Every card has its place (style.top written): the margin layout's pass ran. */
const placed = (page: any): Promise<unknown> => page.waitForFunction(() => {
  const cards = Array.from(document.querySelectorAll(".fc-sec-cards .fc-card[data-id]"));
  return cards.length > 0 && cards.every((c) => (c as HTMLElement).style.top !== "");
}, null, { timeout: 10000 });
/** The poll's HEAD of the sidecar and the config answered with the status's own mtimes (the header's last paragraph). */
const quietPoll = (target: any, status: any): Promise<void> => target.evaluate((st: any) => {
  const w = window as any; const real = w.fetch;
  w.fetch = async function (url: string, init?: RequestInit) {
    if (init && init.method === "HEAD") {
      const m = /[?&]path=([^&]*)/.exec(String(url)); const p = m ? decodeURIComponent(m[1]) : "";
      if (p.endsWith(".json")) return new Response("", { status: 200, headers: { "X-Romp-Mtime-Ns": p.endsWith("/config.json") ? st.configMtimeNs : st.storeMtimeNs } });
    }
    return real(url, init);
  };
}, status);

/** The pane at 1000 px with the report open, the page counting every captured `load` and every FontFaceSet `loadingdone`, the panel
 *  open and its cards placed. */
async function openReport(browser: any, note: string, status: unknown, hold: "pic" | "font" | null, theme = ""): Promise<{ page: any; errors: string[]; held: Hold }> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: note }, MT, theme);
  const held = await serve(page, html, hold);
  await page.goto(ORIGIN + "/");
  await quietPoll(page, status);
  await page.evaluate(() => {
    const w = window as any; w.__loads = 0; w.__fontsDone = 0;
    document.addEventListener("load", () => { w.__loads++; }, true);
    (document as any).fonts.addEventListener("loadingdone", () => { w.__fontsDone++; });
  });
  await page.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, status]);
  await page.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await openPanel(page);
  await placed(page);
  await frames(page, 2);
  return { page, errors, held };
}

test("in a browser, the real panel: a figure's bytes landing after the paint re-wrap the highlighted item, and the panel re-trims its marks on the body's load (no padding-only mark, the new wrap points' blanks unwrapped) with no paint pass and no reflow", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, held } = await openReport(browser, NOTE, COMMENTED, "pic");
    const r0 = await read(page);
    assert.equal(held.requests, 1, "the picture was asked for on open (a local attachment loads on open) and is held");
    assert.equal(r0.imgWidth, 0, "before its bytes land the picture lays out at no width");
    assert.ok(r0.blankMarks >= 40, "the spaces between the links carry marks: " + r0.blankMarks);
    assert.deepEqual(r0.paddingOnly, [], "the pass trimmed the wrap points' spaces");
    const scrolls0 = await page.evaluate(() => { const b = document.querySelector(".fileview-body") as HTMLElement; return b.scrollHeight > b.clientHeight; });
    assert.ok(scrolls0, "the body scrolls before the load (the filler), so no scrollbar can come with it");
    // the bytes land: the picture grows to 300 px, the item re-wraps, the body's `load` fires (captured), and the frame after it re-trims
    held.release();
    await page.waitForFunction(() => (window as any).__loads > 0 && (document.querySelector(".fileview-md img") as HTMLImageElement).complete, null, { timeout: 10000 });
    await frames(page, 3);
    const r1 = await read(page);
    assert.equal(r1.imgWidth, 300, "the picture landed at its width");
    assert.equal(r1.reflows, r0.reflows, "no reflow: the body's width did not move (the width observer is the only source of one)");
    assert.equal(r1.paints, r0.paints, "no paint pass either: the marks are the pass's own nodes");
    assert.deepEqual(r1.paddingOnly, [], "no blank mark of zero width stands after the load (the panel re-trimmed on the body's load)");
    assert.ok(r1.blankMarks < r0.blankMarks, "the new wrap points' blanks were unwrapped: " + r1.blankMarks + " blank marks against " + r0.blankMarks);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real panel: a font face arriving after the paint re-wraps the highlighted item, and the panel re-trims its marks on the FontFaceSet's loadingdone (no padding-only mark, the new wrap points' blanks unwrapped) with no paint pass and no reflow", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors, held } = await openReport(browser, NOTE, COMMENTED, "font", MONO_FALLBACK);
    const r0 = await read(page);
    assert.equal(held.requests, 1, "the regular face was asked for and is held");
    assert.equal(r0.fontStatus, "loading", "the face is still loading at the paint: the fallback face shows (font-display: swap)");
    assert.ok(r0.blankMarks >= 40, "the spaces between the links carry marks: " + r0.blankMarks);
    assert.deepEqual(r0.paddingOnly, [], "the pass trimmed the wrap points' spaces");
    // the face lands: every glyph's width changes, the item re-wraps, the FontFaceSet fires loadingdone, and the frame after it re-trims
    held.release();
    await page.waitForFunction(() => (window as any).__fontsDone > 0, null, { timeout: 10000 });
    await frames(page, 3);
    const r1 = await read(page);
    assert.equal(r1.fontStatus, "loaded", "the face landed");
    assert.equal(r1.reflows, r0.reflows, "no reflow: the body's width did not move");
    assert.equal(r1.paints, r0.paints, "no paint pass either");
    assert.deepEqual(r1.paddingOnly, [], "no blank mark of zero width stands after the swap (the panel re-trimmed on loadingdone)");
    assert.ok(r1.blankMarks < r0.blankMarks, "the new wrap points' blanks were unwrapped: " + r1.blankMarks + " blank marks against " + r0.blankMarks);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

const ZW = "\u200b";
const NOTE3 = "# Report\n\nIntro para. with a few words.\n\nSecond **one**" + ZW + "*two* three four.\n\nThird paragraph adds the word extra here for the control.\n\n" + FILLER + "\n";
const hunk = (id: string, at: number, text: string) => ({ id, author: "api", ts: T0 + 21000, kind: "ins", curFrom: at, curTo: at + text.length, baseFrom: at, baseTo: at, oldText: "", newText: text, anchor: null });
const HUNKS = [hunk("hZ", NOTE3.indexOf(ZW), ZW), hunk("hW", NOTE3.indexOf("extra"), "extra")];
const CHANGED = { ...STATUS, store: { ...STATUS.store, suggestions: HUNKS.map((h) => ({ id: h.id, authorId: SID })) }, hunks: HUNKS };
type CardRead = { marks: number; tags: string[]; buttons: string[]; refLink: boolean } | null;
const cardOf = (page: any, id: string): Promise<CardRead> => page.evaluate((cid: string) => {
  const body = document.querySelector(".fileview-body") as HTMLElement;
  const card = document.querySelector('.fc-card.fc-change[data-change="' + cid + '"]');
  if (!card) return null;
  const ref = card.querySelector(".fc-ref");
  return {
    marks: body.querySelectorAll('[data-act="fcchange"][data-id="' + cid + '"]').length,
    tags: Array.from(card.querySelectorAll(".fc-tag")).map((x) => x.textContent || ""),
    buttons: Array.from(card.querySelectorAll("button")).map((b) => b.textContent || ""),
    refLink: !!ref && ref.classList.contains("fc-link"),
  };
}, id);

test("in a browser, the real panel: a change whose every mark the pass's trim removed (one zero-width space inserted between two inline elements) is filed as not shown, its card wearing the tag and offering Reveal, where the control change paints and links", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openReport(browser, NOTE3, CHANGED, null);
    await page.waitForFunction(() => !!document.querySelector('.fc-card.fc-change[data-change="hW"]'), null, { timeout: 10000 });
    const zw = await cardOf(page, "hZ"), word = await cardOf(page, "hW");
    assert.ok(zw && word, "both change cards render");
    assert.equal(word!.marks, 1, "the control's word is marked in the body");
    assert.ok(!word!.tags.includes("not shown") && !word!.buttons.includes("Reveal") && word!.refLink, "the control's card claims its mark: no tag, no Reveal, the reference a link: " + JSON.stringify(word));
    assert.equal(zw!.marks, 0, "the zero-width space's one mark was trimmed: nothing of the change is marked in the body");
    assert.ok(zw!.tags.includes("not shown"), "the card says the view does not show the change: " + JSON.stringify(zw));
    assert.ok(zw!.buttons.includes("Reveal"), "and offers Reveal, the way to the passage: " + JSON.stringify(zw));
    assert.equal(zw!.refLink, false, "its reference is no link (nothing to scroll to)");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

/** The shell: the pane in an iframe the way the kernel's landing page frames it, sized to a phone's column. */
const SHELL = `<!DOCTYPE html><html><head><meta charset=utf-8><style>html, body { margin: 0; } #pane { width: 420px; height: 640px; border: 0; }</style></head>
<body><iframe id="pane" src="${ORIGIN}/pane"></iframe></body></html>`;
const NOTE4 = "# Report\n\nIntro para. with a few words before the item.\n\n- " + LINKS + "\n\nAfter para. closing the report.\n\n" + FILLER + "\n";
const COMMENTS4 = [commentOn(1, LINKS, "- ", "\n\nAfter")];
/** One change too, so the header offers the inline toggle (the panel shows it while the file has changes), the leg's paint trigger. */
const HUNKS4 = [hunk("hW", NOTE4.indexOf("words"), "words")];
const COMMENTED4 = { ...STATUS, store: { ...STATUS.store, comments: COMMENTS4, suggestions: HUNKS4.map((h) => ({ id: h.id, authorId: SID })) }, hunks: HUNKS4, unsent: { ...STATUS.unsent, comments: COMMENTS4.map((c) => c.id) } };

/** The shell page with the pane framed (legs 4 and 5): the report open in the pane, the panel open, its cards placed. */
async function openShell(browser: any): Promise<{ page: any; frame: any; errors: string[] }> {
  const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  const html = pageHtml("pane", { [REPORT]: NOTE4 }, MT);
  await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/shell") return route.fulfill({ status: 200, contentType: "text/html", body: SHELL });
    if (u.pathname === "/media/InterVariable.woff2") return route.fulfill({ status: 200, contentType: "font/woff2", body: INTER });
    if (u.pathname === "/media/InterVariable-Italic.woff2") return route.fulfill({ status: 200, contentType: "font/woff2", body: INTER_ITALIC });
    return route.fulfill({ status: 200, contentType: "text/html", body: html });
  });
  await page.goto(ORIGIN + "/shell");
  const frame = page.frames().find((f: any) => f !== page.mainFrame());
  assert.ok(frame, "the pane's frame");
  await frame.waitForFunction(() => !!(window as any).FV, null, { timeout: 10000 });
  await quietPoll(frame, COMMENTED4);
  await frame.evaluate(([p, sid, st]: [string, string, unknown]) => { (window as any).__status = st; (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID, COMMENTED4]);
  await frame.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
  await openPanel(frame);
  await frames(frame, 4);
  return { page, frame, errors };
}
/** The pane's counters, for leg 5: the panel's trim calls (__trims, the page's count of TRIM_STATS.passes resets), the pane's own
 *  frames (__ticks) and the seam's reflows and paints. */
type Counts = { trims: number; ticks: number; reflows: number; paints: number };
const counts = (frame: any): Promise<Counts> => frame.evaluate(() => { const w = window as any; return { trims: w.__trims, ticks: w.__ticks, reflows: w.__reflows, paints: w.__paints }; });
/** The pane's reflow count reaching `n`, awaited from the SHELL page, whose frames run whatever the hidden pane's do. */
const reflowsReach = (page: any, n: number): Promise<unknown> => page.waitForFunction((k: number) => ((document.getElementById("pane") as HTMLIFrameElement).contentWindow as any).__reflows >= k, n, { timeout: 10000 });
test("in a browser, the real panel in a display:none iframe: a paint pass made while the pane is hidden keeps every blank mark, and the pane shown again (in the same task, so no observer reports either) re-trims them in its first frame: no padding-only mark at the wrap points, no reflow", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, frame, errors } = await openShell(browser);
    const r0 = await read(frame);
    assert.ok(r0.blankMarks >= 40, "the spaces between the links carry marks: " + r0.blankMarks);
    assert.deepEqual(r0.paddingOnly, [], "the pass trimmed the wrap points' spaces while the pane showed");
    // one task: the shell hides the pane, the panel's pass runs inside it (a forced layout finds no box: every blank mark kept), the shell shows it
    const mid = await page.evaluate(() => {
      const pane = document.getElementById("pane") as HTMLIFrameElement;
      pane.style.display = "none";
      const doc = pane.contentWindow!.document;
      const hidden = (doc.querySelector(".fileview-body") as HTMLElement).getClientRects().length === 0;
      (doc.querySelector('[data-act="fcinline"]') as HTMLElement).click();
      const marks = Array.from(doc.querySelectorAll(".fileview-body mark.fc-hl"));
      const kept = marks.filter((k) => /^\s*$/.test(k.textContent || "")).length;
      pane.style.display = "";
      return { hidden, kept };
    });
    assert.ok(mid.hidden, "the body has no box while the pane is hidden");
    assert.ok(mid.kept > r0.blankMarks, "the hidden pass kept the wrap points' blanks (no width and no box to measure): " + mid.kept + " blank marks against " + r0.blankMarks);
    // the show: the pane's first frame runs the re-trim the hidden pass asked for
    await frames(frame, 3);
    const r2 = await read(frame);
    assert.equal(r2.reflows, r0.reflows, "no reflow: no lifecycle update ran in the hidden frame, so the body's width is the one the seam's observer last observed");
    assert.equal(r2.paints, r0.paints, "no paint proper through the seam (the hidden pass was the panel's own)");
    assert.deepEqual(r2.paddingOnly, [], "no blank mark of zero width stands after the show (the hidden pass asked for the frame that re-trims)");
    assert.ok(r2.blankMarks < mid.kept, "the wrap points' blanks were unwrapped on the show: " + r2.blankMarks + " blank marks against " + mid.kept);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

test("in a browser, the real panel in a display:none iframe hidden across frames: the seam reports the hide and the show as reflows (Chromium runs the hidden frame's requestAnimationFrame), the trim runs twice per event while hidden and never per frame, and the show's reflow re-trims: no padding-only mark at the wrap points", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, frame, errors } = await openShell(browser);
    // the trim's call counter (TRIM_STATS.passes is reset at the start of every trimCollapsedMarks call; anchor-map.ts) and the
    // pane's own frame counter, a requestAnimationFrame loop that runs for as long as the engine gives the pane frames
    await frame.evaluate(() => {
      const w = window as any; const stats = w.FV.TRIM_STATS; let passes = stats.passes; w.__trims = 0; w.__ticks = 0;
      Object.defineProperty(stats, "passes", { configurable: true, get: () => passes, set: (x: number) => { if (x === 0) w.__trims++; passes = x; } });
      const tick = () => { w.__ticks++; requestAnimationFrame(tick); }; requestAnimationFrame(tick);
    });
    const r0 = await read(frame);
    assert.ok(r0.blankMarks >= 40, "the spaces between the links carry marks: " + r0.blankMarks);
    assert.deepEqual(r0.paddingOnly, [], "the pass trimmed the wrap points' spaces while the pane showed");
    const c0 = await counts(frame);
    // the hide, and the seam's report of it: the body's width observer sees contentRect 0 in the hidden frame's lifecycle update and
    // the seam fires a reflow (awaited from the shell: its frames run whatever the pane's do); then frames pass with the pane hidden
    await page.evaluate(() => { (document.getElementById("pane") as HTMLElement).style.display = "none"; });
    await reflowsReach(page, c0.reflows + 1);
    await frames(page, 6);
    // the panel's paint pass while hidden (the inline toggle): a forced layout finds no box, every blank mark kept; more frames pass
    const mid = await frame.evaluate(() => {
      const hidden = (document.querySelector(".fileview-body") as HTMLElement).getClientRects().length === 0;
      (document.querySelector('[data-act="fcinline"]') as HTMLElement).click();
      const marks = Array.from(document.querySelectorAll(".fileview-body mark.fc-hl"));
      const kept = marks.filter((k) => /^\s*$/.test(k.textContent || "")).length;
      return { hidden, kept };
    });
    assert.ok(mid.hidden, "the body has no box while the pane is hidden");
    assert.ok(mid.kept > r0.blankMarks, "the hidden pass kept the wrap points' blanks (no width and no box to measure): " + mid.kept + " blank marks against " + r0.blankMarks);
    await frames(page, 6);
    const c1 = await counts(frame);
    const hid = { trims: c1.trims - c0.trims, ticks: c1.ticks - c0.ticks, reflows: c1.reflows - c0.reflows };
    assert.equal(hid.reflows, 1, "the seam reported the hide as one reflow (the width observer's contentRect 0) and nothing else while hidden: " + hid.reflows);
    assert.equal(c1.paints - c1.reflows, c0.paints - c0.reflows, "no paint proper through the seam while hidden (the pass was the panel's own)");
    assert.ok(hid.ticks >= 6, "the hidden pane's frames ran (Chromium services a display:none frame's requestAnimationFrame): " + hid.ticks + " against the shell's 12");
    assert.equal(hid.trims, 4, "two trims per event while hidden (the hide's reflow, the paint pass): the event's own, which finds no box and arms a frame, and that frame's, which re-arms nothing: " + hid.trims);
    assert.ok(hid.trims < hid.ticks, "never a trim per frame: " + hid.trims + " trims across " + hid.ticks + " hidden frames");
    // the show, and the seam's report of it: the observer sees the width back, the seam fires a reflow and its hook re-trims the marks
    await page.evaluate(() => { (document.getElementById("pane") as HTMLElement).style.display = ""; });
    await reflowsReach(page, c1.reflows + 1);
    await frames(frame, 3);
    const c2 = await counts(frame); const r2 = await read(frame);
    const shown = { trims: c2.trims - c1.trims, reflows: c2.reflows - c1.reflows };
    assert.equal(shown.trims, shown.reflows, "the show's trims are the reflow hook's, one per report; the frame the hidden trims armed was spent hidden and adds none: " + JSON.stringify(shown));
    assert.equal(c2.paints - c2.reflows, c0.paints - c0.reflows, "no paint proper through the seam");
    assert.deepEqual(r2.paddingOnly, [], "no blank mark of zero width stands after the show (the reflow hook re-trimmed)");
    assert.ok(r2.blankMarks < mid.kept, "the wrap points' blanks were unwrapped on the show: " + r2.blankMarks + " blank marks against " + mid.kept);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
