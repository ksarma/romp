// A paint of the panel's landing in the GAP between a person's keyboard change of the selection and the browser's selectionchange for
// it, in headless Chromium over the REAL viewer and panel (file-comments.ts noteSelectionAtHead, pendingChange, lastDelivered, passLeft, afterPaint, offeredFor;
// real-viewer-leg.ts: the Files pane under styles.css and files-pane.css). Chromium posts selectionchange as a normal-priority task,
// 0.7 to 14.3 ms after the keydown over 20 measured presses (found 2026-09-19 while a keyboard-offer wait of the paint-offer file was
// under investigation). afterPaint read the LIVE selection at the end of every pass into the record the listener compares with
// (offeredFor: the rule that the paint's own move of the selection is no offer), so a pass landing in that gap found the person's
// change already in the live selection and recorded it as the offer's, and the person's own event then read the selection as already
// answered (the same ends, the same text) and offered nothing. What the person saw depends on the geometry: on a one-line selection the
// pass leaves intact, the grown (or shrunk) selection's right edge had moved a glyph from under the button, so afterPaint's subject test
// read the passage as moved, the text as not the record's, and hid the float, which the coming event did not re-offer: the Comment button
// vanished on Shift+ArrowRight. Now every pass reads the selection at its head, before its writes, against the two notes the events
// themselves write: the selection the last delivered selectionchange found (lastDelivered, the listener's first read) and the one the
// last pass left (passLeft, afterPaint's last read); a selection at neither is the person's change with its event still to come, a
// latch the event lowers, and afterPaint drops the record instead of reading it from a selection that holds their change and leaves
// the float to that event, which compares the selection as the pass left it with no record and offers beside it as for any change of
// theirs; a subject the pass left gone or with no box goes with the pass, as it does with no change pending (the review of the fix,
// 2026-09-20: the event refuses a boxless remnant without hiding, and the button stood beside a bare line break). The first version of
// the latch compared the live selection with the RECORD and inferred a pending event from a mismatch, which was wrong three ways (the
// review's round 1): true after the event had run (a press ended by the window's blur), true of a stale record, and false with no record,
// the ordinary state of an open panel, where a pass in the gap of a keyboard or assistive-technology selection recorded it as its own
// and the person's event offered nothing; the fourth and fifth tests below drive those roads. The pass is forced into the gap
// deterministically through a road the product exposes to its host: a settings pick from
// another pane (settings.ts onExternalSettingsChange: the window's storage event for the settings key, which file-comments.ts answers
// with paintAll at once), fired from a one-shot keyup listener the leg installs, since the ArrowRight keyup is a separate input task
// Chromium runs ahead of the posted selectionchange; each scene asserts that premise (at the hook the selection already holds the
// change and the event count is at its baseline) and fails loudly where a browser orders them otherwise. The first test's scenes are
// the paint-offer file's control (a peer's mark AFTER the selection on its line, so the pass moves nothing on the line and the float's
// place is a sound witness), the change a Shift+ArrowRight and a Shift+ArrowLeft, each its own subtest so each records its own red;
// then the same pick with no change of the person's, the pinned rule: the paint's own event is no offer and the float stands. The
// second test lands the same pass over the paint-offer file's CUT geometries, where the pass's writes change the pending selection
// itself: the ON cut (the anchor inside a mark at the paragraph's head, the remnant standing under the button), the lone-child
// collapse (round 2), the boxless remnant (round 5: a bare line break between two blocks) and the moved remnant (round 6: a line
// below the offer's); a remnant with a box is the person's event's to offer beside, as it stands, and a subject gone or boxless is
// hidden by the pass. The third test is the same pass landing inside another gesture of the person's: a DRAG of the selected text
// (file-comments.ts pointerHeld, dragBegan). The press flag the listener reads is cleared at the drag's end, a dragend at the drag's
// SOURCE, the text node under the press, which the document's own listener hears by propagation alone; a pass mid-drag that unwraps
// the mark the text sits in (the unpaint's normalize merges the node away) detaches that node, and Chromium then dispatches the
// dragend at the detached node, where nothing of the document's runs (the probe of 2026-09-20): the flag stood past the drop, and every
// change of the selection after it (a passage selected by caret browsing or assistive technology, then Shift+ArrowRight) offered nothing
// until the next primary press. Now the press's end is heard at the source itself, hooked at the document's capture dragstart. The leg
// asserts its premise too: the source detached by the pass and no dragend at the document. The fourth test is the ordinary state, NO
// record (a real click's caret, which the listener drops the record for), and the person's selection with the pass in its gap on three
// roads, each its own subtest: the keyboard (Shift+ArrowRight from the caret, the pass at the keyup) and the selection API with no key
// event (setBaseAndExtent, and Selection.modify by a word: the closest a test comes to a screen reader's or caret browser's move through
// the accessibility layer, the pass fired in the same task, so it is in the gap by construction), each offering beside the selection.
// The fifth is the change whose event ALREADY RAN over a stale record: a second press inside the highlight dragged and ended by the
// window's blur (no mouseup, so the seam never offered and the record names the first passage), then the pick, whose own event must
// offer nothing. The sixth is the third refusal with the change pending, in a 500 by 400 px pane: the pick's writes push the pending
// passage below the body's bottom edge, and no button stands over the body's last visible line. The seventh is a change of the person's
// that RETURNS the selection to the ends the last pass left (the review's round 2): a quiet pick over the offered selection, Shift+ArrowRight
// delivered and offered, then Shift+ArrowLeft back to the drag's ends with the pick in its gap; the last pass's note (passLeft) was kept
// until the next pass, so the head read the return as that pass's own move, recorded it, hid the button the change had moved a glyph from
// under, and the event offered nothing; every delivered selectionchange retires the note now. Legs await the DOM's own states and frames,
// never a timer. Skips LOUDLY without a playwright browser (CI installs none). Synthetic values only: an invented report, /repo/notes-api
// paths, the placeholder sid, invented comment ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, PARA, REPORT, SID, STATUS } from "./real-viewer-leg";

const T0 = 1757145600000;
const NOTE = "# Report\n\nParagraph 1: alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.\n\n"
  + "Paragraph 2: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore.\n\n"
  + "Paragraph 3: after words closing the report with a few more words so the line wraps somewhere.\n\n"
  + Array.from({ length: 40 }, (_, i) => `Filler ${i + 1}: more text so the body scrolls in a 700 px pane, long enough to wrap once or twice.`).join("\n\n") + "\n";
const P2 = "Paragraph 2: lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore.";
const P3 = "Paragraph 3: after words closing the report with a few more words so the line wraps somewhere.";
const commentOn = (id: string, ts: number, quote: string, prefix: string, suffix: string) =>
  ({ id, author: "you", ts, body: `Note ${id}.`, anchor: { quote, prefix, suffix }, replies: [], resolved: false });
// the peer's comment AFTER the words the drag selects, on their line: its mark's padding moves nothing of the selection (the paint-offer
// file's control scene), so a pass over the line leaves the selection whole and where it was
const E = commentOn("eeee-5", T0 + 5, P2.slice(40, 57), P2.slice(20, 40), P2.slice(57, 77));
// the peer's comment ON the words the third test drags from: its mark's text is the drag's source, which the pass mid-drag detaches
const ON = commentOn("bbbb-2", T0 + 2, "lorem ipsum dolor sit amet", "Paragraph 2: ", " consectetur adipiscing");
const MARK_ON = '.fileview-body mark.fc-hl[data-id="bbbb-2"]';
// the paint-offer file's cut geometries: a peer's comment at paragraph 2's head (a prefix of it, plain text after the mark), and one on
// the whole of paragraph 2, whose mark is the <p>'s only child
const A = commentOn("aaaa-1", T0 + 1, "Paragraph 2: lorem", "sigma tau.\n\n", " ipsum dolor sit amet");
const W = commentOn("wwww-2", T0 + 2, P2, "sigma tau.\n\n", "\n\nParagraph 3");
const MARK_A = '.fileview-body mark.fc-hl[data-id="aaaa-1"]', MARK_W = '.fileview-body mark.fc-hl[data-id="wwww-2"]';
const STORE_MT = "1757145600000000002";
const withComments = (comments: unknown[], storeMtimeNs: string) => ({ ...STATUS, storeMtimeNs, store: { ...STATUS.store, comments }, unsent: { ...STATUS.unsent, comments: comments.map((c: any) => c.id) } });
const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

type Anat = { anchor: string; focus: string; box: number[] | null };
type Scene = { hidden: boolean; left: number; top: number; selected: string; collapsed: boolean; expectedLeft: number; expectedTop: number; selChanges: number; marks: number; composer: boolean; boxless: boolean; inBody: boolean; anat: Anat };
/** The float's state and inline place, the selection's text and whether it is collapsed, where showFloat would put the button for the
 *  selection's last range now, the count of selectionchange events since the counter was armed, the count of highlight marks on the body,
 *  whether a composer stands,
 *  whether its last range has no box (no width and no height: the offer's own refusal), whether both its ends lie in the body, and its
 *  anatomy for the diagnostics (each end as node name and offset, the last range's width, height, top and right). */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; const body = document.querySelector(".fileview-body");
  const r = sel.rangeCount ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  const nm = (n: Node | null) => (n ? (n.nodeName === "#text" ? "text" : n.nodeName) : "none");
  const anat = { anchor: nm(sel.anchorNode) + "@" + sel.anchorOffset, focus: nm(sel.focusNode) + "@" + sel.focusOffset, box: r ? [r.width, r.height, r.top, r.right].map((v) => Math.round(v * 1000) / 1000) : null };
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top), selected: String(sel), collapsed: sel.isCollapsed, anat,
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    selChanges: w.__selChanges as number, marks: document.querySelectorAll(".fileview-body mark.fc-hl").length,
    composer: !!document.querySelector(".fileview-aside .fc-composer .fc-input"),
    boxless: !r || (!r.width && !r.height),
    inBody: !!body && !!sel.anchorNode && !!sel.focusNode && body.contains(sel.anchorNode) && body.contains(sel.focusNode) };
});
const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 0.01, what + ": " + a + " against " + b);

/** The page with the peer's comment `c` on the note and the panel open, awaited on its mark: the store's and the config's HEADs answered
 *  with the status's own mtimes, so the poll is quiet and no pass but the leg's own lands; a selectionchange counter and the pick. */
async function openWith(browser: any, c: { id: string }): Promise<{ page: any; errors: string[] }> {
  const { page, errors } = await openViewer(browser, "pane", 900, 700, { docs: { [REPORT]: NOTE } });
  await page.evaluate(([st, configMt]: [unknown, string]) => {
    const w = window as any; w.__status = st;
    const real = w.fetch;
    w.fetch = async function (url: string, init?: RequestInit) {
      if (init && init.method === "HEAD") {
        const m = /[?&]path=([^&]*)/.exec(String(url)); const p = m ? decodeURIComponent(m[1]) : "";
        if (p.endsWith(".json")) return new Response("", { status: 200, headers: { "X-Romp-Mtime-Ns": p.endsWith("/config.json") ? configMt : (st as any).storeMtimeNs } });
      }
      return real(url, init);
    };
    w.__selChanges = 0; document.addEventListener("selectionchange", () => { w.__selChanges++; });
    // the settings pick from another pane, as the browser delivers it to this document: the shared store written with Show changes
    // inline flipped, then the window's storage event for the settings key (settings.ts onExternalSettingsChange re-reads the store on
    // it; file-comments.ts answers a changed flag with paintAll at once)
    w.__pick = () => {
      const KEY = "romp:settings"; const raw = localStorage.getItem(KEY); const cur = raw ? JSON.parse(raw) : {};
      const next = { ...cur, changesInline: cur.changesInline === false };
      localStorage.setItem(KEY, JSON.stringify(next));
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, oldValue: raw, newValue: JSON.stringify(next), storageArea: localStorage, url: location.href }));
    };
  }, [withComments([c], STORE_MT), STATUS.configMtimeNs]);
  await openPanel(page);
  await page.waitForFunction((s: string) => !!document.querySelector(s), `.fileview-body mark.fc-hl[data-id="${c.id}"]`, { timeout: 10000 });
  await frames(page, 3);
  return { page, errors };
}
type Ends = { x1: number; y1: number; x2: number; y2: number };
/** A real mouse drag between two points; the seam's mouseup offers the float, awaited. */
async function drag(page: any, r: Ends): Promise<void> {
  await page.mouse.move(r.x1, r.y1); await page.mouse.down(); await page.mouse.move(r.x2, r.y2, { steps: 6 }); await page.mouse.up();
  await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement | null; return !!f && !f.hidden; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** A real mouse drag over paragraph 2's plain text (its first text node, before the peer's mark), from its character `from` to its
 *  character `to`. */
async function dragOver(page: any, from: number, to: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r: Ends = await page.evaluate(([a, b]: [number, number]) => {
    const t = document.querySelectorAll(".fileview-md > p")[1].firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(t, b - 1); rb.setEnd(t, b); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [from, to]);
  await drag(page, r);
}
/** A real mouse drag inside the peer's mark's text, from its character `from` to its character `to`, so both ends lie in the mark's text node. */
async function dragInside(page: any, markSel: string, from: number, to: number): Promise<Ends> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r: Ends = await page.evaluate(([s, a, b]: [string, number, number]) => {
    const t = (document.querySelector(s) as HTMLElement).firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(t, b - 1); rb.setEnd(t, b); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [markSel, from, to]);
  await drag(page, r);
  return r;
}
/** A real mouse drag from the mark's first character to `n` characters into the text node right after it (the paint-offer file's
 *  dragAcross): the anchor in the mark's text, the focus in the plain text. */
async function dragAcross(page: any, markSel: string, n: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r: Ends = await page.evaluate(([s, k]: [string, number]) => {
    const m = document.querySelector(s) as HTMLElement; const t0 = m.firstChild as Text; const after = m.nextSibling as Text;
    const a = document.createRange(); a.setStart(t0, 0); a.setEnd(t0, 1); const ra = a.getBoundingClientRect();
    const b = document.createRange(); b.setStart(after, k - 1); b.setEnd(after, k); const rb = b.getBoundingClientRect();
    return { x1: ra.left + 1, y1: ra.top + ra.height / 2, x2: rb.right - 1, y2: rb.top + rb.height / 2 };
  }, [markSel, n]);
  await drag(page, r);
}
/** A real mouse drag from character `from` inside the mark's text to character `n` of the NEXT paragraph's text (the paint-offer file's
 *  dragIntoMiddle): the anchor in the mark's text, the focus in the middle of the next block. */
async function dragIntoMiddle(page: any, markSel: string, from: number, n: number): Promise<void> {
  await page.evaluate(() => getSelection()!.removeAllRanges());
  const r: Ends = await page.evaluate(([s, a, k]: [string, number, number]) => {
    const m = document.querySelector(s) as HTMLElement; const t = m.firstChild as Text; const next = (m.parentElement as HTMLElement).nextElementSibling!.firstChild as Text;
    const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
    const rb = document.createRange(); rb.setStart(next, k - 1); rb.setEnd(next, k); const y = rb.getBoundingClientRect();
    return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
  }, [markSel, from, n]);
  await drag(page, r);
}
type Gap = { key: string; before: { selected: string; selChanges: number; hidden: boolean; left: number }; after: { selected: string; collapsed: boolean; selChanges: number; hidden: boolean; left: number; marks: number; anat: Anat } };
/** Arm the gap: a one-shot capture keyup listener that reads the scene, fires the settings pick (the pass, window.__pick), and reads the
 *  scene again, into window.__gap; the ArrowRight or ArrowLeft keyup is the first keyup after Shift goes down, a separate input task
 *  Chromium runs before the selectionchange task the key's own change posted. */
const armGap = (page: any): Promise<void> => page.evaluate(() => {
  const w = window as any; w.__gap = null;
  const read = () => { const f = document.querySelector(".fc-float") as HTMLElement; return { selected: String(getSelection()), selChanges: w.__selChanges as number, hidden: f.hidden, left: parseFloat(f.style.left) }; };
  document.addEventListener("keyup", (ev) => {
    const before = read();
    w.__pick();
    const sel = getSelection()!; const r = sel.rangeCount ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
    const nm = (n: Node | null) => (n ? (n.nodeName === "#text" ? "text" : n.nodeName) : "none");
    const anat = { anchor: nm(sel.anchorNode) + "@" + sel.anchorOffset, focus: nm(sel.focusNode) + "@" + sel.focusOffset, box: r ? [r.width, r.height, r.top, r.right].map((v) => Math.round(v * 1000) / 1000) : null };
    w.__gap = { key: (ev as KeyboardEvent).key, before, after: { ...read(), collapsed: sel.isCollapsed, marks: document.querySelectorAll(".fileview-body mark.fc-hl").length, anat } };
  }, { once: true, capture: true });
});
/** Shift with the arrow `key`, the pass armed in its gap: awaited on the hook having run and on the key's selectionchange (the count past
 *  `baseline`), then frames; the hook's record. */
async function pressInGap(page: any, key: string, baseline: number): Promise<Gap> {
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await armGap(page);
  await page.keyboard.down("Shift"); await page.keyboard.press(key); await page.keyboard.up("Shift");
  await page.waitForFunction(() => (window as any).__gap !== null, null, { timeout: 5000 });
  await page.waitForFunction((n: number) => (window as any).__selChanges > n, baseline, { timeout: 5000 });
  await frames(page, 2);
  const gap: Gap | null = await page.evaluate(() => (window as any).__gap);
  assert.ok(gap, "the keyup hook ran");
  assert.equal(gap!.key, key, "...at the arrow's keyup");
  return gap!;
}
/** The leg's premise: at the keyup the selection already held the person's change (`grown`) and no selectionchange had fired for it, so
 *  the pass ran inside the gap; a browser that dispatches the event before the keyup makes the leg no test of the gap, and this says so. */
function premise(gap: Gap, grown: string | RegExp, baseline: number, offeredLeft: number, what: string): void {
  if (typeof grown === "string") assert.equal(gap.before.selected, grown, what + ": the premise: at the keyup the selection holds the change (the pass lands in the gap)");
  else assert.match(gap.before.selected, grown, what + ": the premise: at the keyup the selection holds the change (the pass lands in the gap)");
  assert.equal(gap.before.selChanges, baseline, what + ": ...and its selectionchange is still to come");
  assert.deepEqual([gap.before.hidden, gap.before.left], [false, offeredLeft], what + ": ...the float still standing where the drag offered it");
  assert.equal(gap.after.selChanges, baseline, what + ": the pass fired nothing of its own yet (its move rides the key's posted event)");
}

const CHANGES: Array<{ name: string; key: string; text: string }> = [
  { name: "grown by Shift+ArrowRight", key: "ArrowRight", text: P2.slice(13, 31) },
  { name: "shrunk by Shift+ArrowLeft", key: "ArrowLeft", text: P2.slice(13, 29) },
];

test("in a browser, the real viewer and panel: a real drag over a plain paragraph's words beside a peer's mark, then Shift+ArrowRight (and, in its own subtest, Shift+ArrowLeft) with a settings pick from another pane repainting the marks INSIDE the gap before the key's selectionchange: the person's change offers the float beside the changed selection (before: the pass recorded the changed selection as the offer's, the event offered nothing, and afterPaint hid the button the pass had moved a glyph from under); then the same pick with no change of the person's moves nothing and its event offers nothing", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const c of CHANGES) await t.test(c.name, { timeout: 120000 }, async (st) => {
      const { page, errors } = await openWith(browser, E);
      await dragOver(page, 13, 30);
      let s = await scene(page);
      assert.equal(s.selected, P2.slice(13, 30), "the drag selected the passage");
      assert.deepEqual([s.hidden, s.marks], [false, 1], "the drag's mouseup offers the float; the peer's mark stands after the passage on its line");
      const offered = { left: s.left, top: s.top, selChanges: s.selChanges };
      // the person's change, with the pass forced into the gap at the key's keyup
      const gap = await pressInGap(page, c.key, offered.selChanges);
      premise(gap, c.text, offered.selChanges, offered.left, c.name);
      assert.deepEqual([gap.after.selected, gap.after.marks], [c.text, 1], "the pass left the changed selection whole and the peer's mark standing");
      st.diagnostic("at the keyup the pass found the float " + (gap.after.hidden ? "and hid it" : "and left it standing") + " at " + gap.after.left + " px");
      // the outcome, after the event: offered beside the changed selection
      s = await scene(page);
      assert.equal(s.selected, c.text, "the keyboard changed the selection by one character");
      assert.equal(s.hidden, false, "the person's change offers the float (before: the pass in the gap recorded the changed selection as the offer's, its event compared equal and offered nothing, and afterPaint had hidden the button the change moved a glyph from under)");
      near(s.left, s.expectedLeft, "...beside the changed selection's end, showFloat's arithmetic for the live range"); near(s.top, s.expectedTop, "...on its line");
      assert.notEqual(s.left, offered.left, "...a place the change moved (the one-line scene's premise: the float's place is a witness here)");
      assert.equal(s.composer, false, "no composer opened on its own");
      // the pinned rule stands: the same pick with NO change of the person's is the paint's own move alone; the mark after the selection
      // moves nothing, the float stays where the offer put it, and the pass's own selectionchange, where it fires one, offers nothing
      const standing = { left: s.left, top: s.top, selChanges: s.selChanges };
      await page.evaluate(() => { (window as any).__pick(); });
      await frames(page, 4);
      s = await scene(page);
      assert.deepEqual([s.selected, s.hidden, s.marks], [c.text, false, 1], "a pick with no change of the person's leaves the selection whole and the float shown");
      assert.deepEqual([s.left, s.top], [standing.left, standing.top], "...where the offer put it: the paint's own move is no offer");
      st.diagnostic("the pick with no change fired " + (s.selChanges - standing.selChanges) + " selectionchange event(s) of its own");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    });
  });
});

type Cut = { name: string; comment: { id: string }; mark: string; drag: (page: any) => Promise<unknown>; dragged: string | RegExp; grown: string | RegExp; cut: RegExp; left: "collapsed" | "no box" | "a box"; outcome: "offered" | "hidden"; before: string };
/** The paint-offer file's cut geometries with the person's Shift+ArrowRight pending at the pass: what the drag selects, what the key
 *  grows it to (the premise at the keyup), what the pass cuts it to and what it left the remnant with (the premise after the pass, read as
 *  the pass's own subject test reads it: collapsed, a range with no width and no height, or a box), and the outcome once the event runs.
 *  The remnant's anatomy (its ends, its box) is a diagnostic, not a pin: Chromium reports a selection the writes moved by its DOM positions
 *  where a read of it preceded the writes (the pass's head read) and by canonical positions inside the text otherwise, so a tree with no
 *  head read (the base) reads the same remnant with other ends and, for the bare line break, a box. */
const CUTS: Cut[] = [
  { name: "the ON cut: the anchor inside a peer's mark at the paragraph's head, the drag from its first character into the plain text after it; the pass moves the anchor out of the mark and leaves the plain text's part, a remnant with a box under the button",
    comment: A, mark: MARK_A, drag: (page) => dragAcross(page, MARK_A, 8), dragged: P2.slice(0, 26), grown: P2.slice(0, 27), cut: new RegExp("^" + esc(P2.slice(18, 27)) + "$"), left: "a box", outcome: "offered",
    before: "the pass hid the float (the subject moved a glyph, the text not the record's) and the event compared equal" },
  { name: "the lone-child collapse (round 2): a mark that is its paragraph's whole text, the drag inside it; the pass collapses the selection to the paragraph, with no selectionchange of its own",
    comment: W, mark: MARK_W, drag: (page) => dragInside(page, MARK_W, 3, 11), dragged: P2.slice(3, 11), grown: P2.slice(3, 12), cut: /^$/, left: "collapsed", outcome: "hidden",
    before: "hidden on both trees: the pass's own hide, or the event's collapsed-selection guard" },
  { name: "the boxless remnant (round 5): the drag inside the whole-paragraph mark to its last character, the key carrying the focus into the next block; the pass moves the anchor to the paragraph's end and leaves a bare line break, in the body, not collapsed, with no box",
    comment: W, mark: MARK_W, drag: (page) => dragInside(page, MARK_W, P2.length - 8, P2.length), dragged: P2.slice(P2.length - 8), grown: new RegExp("^" + esc(P2.slice(P2.length - 8)) + "\\n+$"), cut: /^\n+$/, left: "no box", outcome: "hidden",
    before: "the pending branch returned before the boxless hide, the event refused the remnant without hiding, and the Comment button stood beside text nobody can see" },
  { name: "the moved remnant (round 6): the drag from inside the whole-paragraph mark into the next paragraph's middle; the pass moves the anchor to the paragraph's end and leaves the line break and that paragraph's first half, a remnant with a box a line or more below the offer's",
    comment: W, mark: MARK_W, drag: (page) => dragIntoMiddle(page, MARK_W, 20, 60), dragged: new RegExp("^" + esc(P2.slice(20)) + "\\n+" + esc(P3.slice(0, 60)) + "$"), grown: new RegExp("^" + esc(P2.slice(20)) + "\\n+" + esc(P3.slice(0, 61)) + "$"), cut: new RegExp("^\\n+" + esc(P3.slice(0, 61)) + "$"), left: "a box", outcome: "offered",
    before: "the pass hid the float by the scroll's test (the remnant moved from under it) and the event compared equal" },
];

test("in a browser, the real viewer and panel: the same settings pick landing in the gap of a Shift+ArrowRight over the paint-offer file's CUT geometries, where the pass's writes change the pending selection itself: a remnant with a box (the ON cut, a moved remnant) is the person's event's to offer beside, as it stands (before the fix: the pass hid the float and the event offered nothing); a subject the pass left gone (the lone-child collapse) or with no box (a bare line break between two blocks) is hidden by the pass, as it is with no change pending (before the review's amendment: the boxless remnant kept its Comment button, which the event refused without hiding)", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    for (const c of CUTS) await t.test(c.name, { timeout: 120000 }, async (st) => {
      const { page, errors } = await openWith(browser, c.comment);
      if (c.comment === W) {
        const only = await page.evaluate((s: string) => { const m = document.querySelector(s)!; return Array.from(m.parentNode!.childNodes).map((n) => n.nodeName).join(","); }, MARK_W);
        assert.equal(only, "MARK", "the whole paragraph's mark is the <p>'s only child");
      }
      await c.drag(page);
      let s = await scene(page);
      if (typeof c.dragged === "string") assert.equal(s.selected, c.dragged, "the drag selected the passage"); else assert.match(s.selected, c.dragged, "the drag selected the passage");
      assert.deepEqual([s.hidden, s.marks, s.boxless], [false, 1, false], "the drag's mouseup offers the float beside a selection with a box; the peer's mark stands");
      const offered = { left: s.left, top: s.top, selChanges: s.selChanges };
      // the person's Shift+ArrowRight, with the pass forced into its gap
      const gap = await pressInGap(page, "ArrowRight", offered.selChanges);
      premise(gap, c.grown, offered.selChanges, offered.left, "the cut");
      assert.match(gap.after.selected, c.cut, "the pass cut the pending selection (the scene's premise: the geometry is the paint-offer file's)");
      assert.equal(gap.after.marks, 1, "...and painted the peer's mark anew");
      st.diagnostic("at the keyup the pass found the float " + (gap.after.hidden ? "and hid it" : "and left it standing") + " at " + gap.after.left + " px; the selection read " + JSON.stringify(gap.after.selected) + " as " + JSON.stringify(gap.after.anat));
      // ...and what it left the remnant with, as the pass's own subject test reads it right after the writes (floatSubjectRect: a range
      // with no width and no height is no box); a browser that reports the bare line break with a box here makes the boxless scene a
      // remnant-with-a-box scene, and this says so instead of passing under the other rule
      const box = gap.after.anat.box;
      const leftWith = gap.after.collapsed ? "collapsed" : box && (box[0] || box[1]) ? "a box" : "no box";
      assert.equal(leftWith, c.left, "the pass left the remnant " + c.left + " (the scene's premise; it read " + JSON.stringify(gap.after.anat) + ")");
      // the outcome, after the event
      s = await scene(page);
      st.diagnostic("after the event the selection reads " + JSON.stringify(s.selected) + " as " + JSON.stringify(s.anat) + "; the float is " + (s.hidden ? "hidden" : "shown") + " at " + s.left + "/" + s.top);
      assert.match(s.selected, c.cut, "the selection stands as the pass cut it (the event moved nothing)");
      if (c.outcome === "offered") {
        assert.deepEqual([s.collapsed, s.inBody, s.boxless], [false, true, false], "a remnant in the body, not collapsed, with a box");
        assert.equal(s.hidden, false, "the person's event offers the float beside the remnant as it stands (before: " + c.before + ")");
        near(s.left, s.expectedLeft, "...at showFloat's arithmetic for the remnant's last range"); near(s.top, s.expectedTop, "...on its line");
        assert.ok(s.left !== offered.left || s.top !== offered.top, "...a place the cut moved (offered at " + offered.left + "/" + offered.top + ", now " + s.left + "/" + s.top + ")");
        st.diagnostic("the float moved from " + offered.left + "/" + offered.top + " to " + s.left + "/" + s.top + " px beside the remnant");
      } else {
        assert.equal(s.hidden, true, "the float is hidden: the pass left it beside a subject gone or with no box (before: " + c.before + ")");
        assert.deepEqual([s.left, s.top], [offered.left, offered.top], "...hidden where it stood: no re-offer");
        // a further pick over the standing remnant hides nothing and shows nothing: no record, no latch, and the float hidden already
        const count = s.selChanges;
        await page.evaluate(() => { (window as any).__pick(); });
        await frames(page, 4);
        s = await scene(page);
        assert.deepEqual([s.hidden, s.marks], [true, 1], "a further pick leaves it hidden");
        st.diagnostic("the further pick fired " + (s.selChanges - count) + " selectionchange event(s) of its own");
      }
      assert.equal(s.composer, false, "no composer opened on its own");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    });
  });
});

type Drag = { started: number; srcName: string | null; srcConnectedAtPass: boolean | null; srcConnected: boolean | null; docDragend: number; marks: number; picked: number };
/** What the drag left: the count of dragstart events the document heard and the source's node name, whether the source was still in the
 *  document when the pass ran and whether it is now, the count of dragend events the document heard, the marks on the body, and whether
 *  the pass ran. */
const dragScene = (page: any): Promise<Drag> => page.evaluate(() => { const w = window as any; return { started: w.__dragStarts as number, srcName: w.__src ? (w.__src as Node).nodeName : null, srcConnectedAtPass: w.__srcConnectedAtPass ?? null, srcConnected: w.__src ? (w.__src as Node).isConnected : null, docDragend: w.__docDragend as number, marks: document.querySelectorAll(".fileview-body mark.fc-hl").length, picked: w.__picked as number }; });

test("in a browser, the real viewer and panel: a real drag inside a peer's highlight, then a drag of the selected text dropped on a later paragraph with a settings pick from another pane repainting the marks MID-DRAG (the drag's source, the mark's text node, detached by the pass): the press flag clears at the drag's end all the same, so a passage selected afterwards (caret browsing or assistive technology; Chromium's Shift+Arrow needs a selection, and the drop left none) offers the float, and Shift+ArrowRight on it offers beside the grown selection (before: the dragend fired at the detached node, out of the document's hearing, the flag stood, and every change of the selection offered nothing until the next click)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, ON);
    const r = await dragInside(page, MARK_ON, 3, 14);
    let s = await scene(page);
    assert.equal(s.selected, "lorem ipsum dolor sit amet".slice(3, 14), "the drag selected the passage inside the highlight");
    assert.deepEqual([s.hidden, s.marks], [false, 1], "the drag's mouseup offers the float; the peer's mark stands");
    // arm the drag's gap: the document's capture dragstart records the drag's source; the first dragover fires the settings pick (the pass);
    // the document's capture dragend counts what reaches the document
    await page.evaluate(() => {
      const w = window as any; w.__dragStarts = 0; w.__docDragend = 0; w.__picked = 0; w.__src = null; w.__srcConnectedAtPass = null;
      document.addEventListener("dragstart", (e) => { w.__dragStarts++; w.__src = e.target; }, true);
      document.addEventListener("dragend", () => { w.__docDragend++; }, true);
      document.addEventListener("dragover", () => { if (!w.__picked) { w.__picked = 1; w.__pick(); w.__srcConnectedAtPass = !!w.__src && (w.__src as Node).isConnected; } }, true);
    });
    // the drag of the selected text: a press on the selection's middle, a few steps, then over a later paragraph, and the release there
    const target = await page.evaluate(() => { const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((e) => (e.textContent || "").startsWith("Filler 3")) as HTMLElement; const b = p.getBoundingClientRect(); return { x: b.left + 40, y: b.top + b.height / 2 }; });
    const mid = { x: (r.x1 + r.x2) / 2, y: r.y1 };
    await page.mouse.move(mid.x, mid.y); await page.mouse.down();
    await page.mouse.move(mid.x + 30, mid.y + 10, { steps: 4 });
    await page.mouse.move(target.x, target.y, { steps: 6 });
    await page.mouse.up();
    await frames(page, 3);
    const d = await dragScene(page);
    // the leg's premise: a drag began at the mark's text node, the pass ran mid-drag and detached that node (the mark unwrapped and its text
    // merged away, then a new mark painted), and no dragend reached the document
    assert.deepEqual([d.started, d.srcName, d.picked], [1, "#text", 1], "the premise: one drag began, at the mark's text node, and the pass ran mid-drag");
    assert.deepEqual([d.srcConnectedAtPass, d.srcConnected, d.marks], [false, false, 1], "...the pass detached the drag's source (the mark's text merged away by the unpaint) and painted the mark anew");
    assert.equal(d.docDragend, 0, "...and the drag's end reached no listener of the document's (dispatched at the detached node)");
    s = await scene(page);
    t.diagnostic("after the drop the selection reads " + JSON.stringify(s.selected) + " and the float is " + (s.hidden ? "hidden" : "shown"));
    // the person's next selection, made without a press: caret browsing and assistive technology select this way, and Chromium's Shift+Arrow
    // widens only an existing selection (the keyboard-offer file's header); its selectionchange offers unless the press flag stands
    const before = s.selChanges;
    await page.evaluate(() => { const p = document.querySelectorAll(".fileview-md > p")[2].firstChild as Text; getSelection()!.setBaseAndExtent(p, 5, p, 20); });
    await page.waitForFunction((n: number) => (window as any).__selChanges > n, before, { timeout: 5000 });
    await frames(page, 2);
    s = await scene(page);
    assert.equal(s.selected, P3.slice(5, 20), "the passage is selected");
    assert.equal(s.hidden, false, "the selection offers the float: the press ended with the drag (before: the flag stood past the drop, its dragend heard by nothing of the document's, and the selection offered nothing)");
    near(s.left, s.expectedLeft, "...beside the passage's end"); near(s.top, s.expectedTop, "...on its line");
    // ...and the keyboard on it
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
    await page.waitForFunction((tx: string) => String(getSelection()) === tx, P3.slice(5, 21), { timeout: 5000 });
    await page.waitForFunction(() => { const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; if (f.hidden || !sel.rangeCount) return false;
      const r2 = sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect(); return Math.abs(parseFloat(f.style.left) - Math.min(Math.max(8, r2.right + 6), window.innerWidth - 90)) < 0.01; }, null, { timeout: 5000 });
    s = await scene(page);
    assert.deepEqual([s.selected, s.hidden], [P3.slice(5, 21), false], "Shift+ArrowRight grows the selection and offers beside it (before: ignored while the flag stood)");
    assert.equal(s.composer, false, "no composer opened on its own");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

type CaretGap = { before: { selected: string; collapsed: boolean; selChanges: number; hidden: boolean }; after: { selected: string; selChanges: number; hidden: boolean; marks: number } };
/** A real click in paragraph 3's plain text, at its sixth character: a collapsed caret in the body, the ORDINARY state of an open panel
 *  (the seam refuses a collapsed selection, and the listener hides a passage's float and drops its record for one), awaited on the
 *  selection itself. */
async function clickCaret(page: any): Promise<void> {
  const at = await page.evaluate(() => { const t = document.querySelectorAll(".fileview-md > p")[2].firstChild as Text; const r = document.createRange(); r.setStart(t, 5); r.setEnd(t, 6); const b = r.getBoundingClientRect(); return { x: b.left + 1, y: b.top + b.height / 2 }; });
  await page.mouse.click(at.x, at.y);
  await page.waitForFunction(() => { const s = getSelection()!; return s.rangeCount === 1 && s.isCollapsed; }, null, { timeout: 5000 });
  await frames(page, 2);
}
/** A change of the selection through the selection API, no key event at all (the closest a test comes to a screen reader's or a caret
 *  browser's move through the accessibility layer), with the pass fired in the same task right after it: the posted selectionchange
 *  cannot run before the script returns, so the pass is in its gap by construction. `kind` is the call: setBaseAndExtent over paragraph
 *  3's characters 5 to 20, or Selection.modify extending the caret forward by a word. Returns the scene at the call and after the pass,
 *  awaited on the change's selectionchange. */
async function apiChangeInGap(page: any, kind: "extent" | "modify"): Promise<CaretGap> {
  const baseline: number = await page.evaluate(() => (window as any).__selChanges as number);
  const gap: CaretGap = await page.evaluate((k: string) => {
    const w = window as any; const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!;
    const read = () => ({ selected: String(sel), collapsed: sel.isCollapsed, selChanges: w.__selChanges as number, hidden: f.hidden });
    if (k === "extent") { const t = document.querySelectorAll(".fileview-md > p")[2].firstChild as Text; sel.setBaseAndExtent(t, 5, t, 20); }
    else sel.modify("extend", "forward", "word");
    const before = read();
    w.__pick();
    return { before, after: { ...read(), marks: document.querySelectorAll(".fileview-body mark.fc-hl").length } };
  }, kind);
  await page.waitForFunction((n: number) => (window as any).__selChanges > n, baseline, { timeout: 5000 });
  await frames(page, 2);
  assert.equal(gap.before.selChanges, baseline, "the premise: the change's selectionchange is still to come when the pass runs (the pass is in its gap)");
  return gap;
}

const API_ROADS: Array<{ name: string; kind: "extent" | "modify"; text: string | RegExp }> = [
  { name: "the selection API from a click's caret: setBaseAndExtent over fifteen characters, no key event, the pass in the same task", kind: "extent", text: P3.slice(5, 20) },
  { name: "the selection API from a click's caret: Selection.modify extending the caret by a word, no key event, the pass in the same task", kind: "modify", text: /^raph ?$/ },
];
/** Shift with `key` once, awaited on the key's selectionchange (the count past its value before the press). */
async function shiftKey(page: any, key: string): Promise<void> {
  const n: number = await page.evaluate(() => (window as any).__selChanges as number);
  await page.keyboard.down("Shift"); await page.keyboard.press(key); await page.keyboard.up("Shift");
  await page.waitForFunction((k: number) => (window as any).__selChanges > k, n, { timeout: 5000 });
  await frames(page, 1);
}
const focusInBody = (page: any): Promise<boolean> => page.evaluate(() => { const s = getSelection()!; const b = document.querySelector(".fileview-body")!; return !!s.focusNode && b.contains(s.focusNode); });
/** The outcome every no-record road shares: the person's event offers the float beside the selection as the pass left it, and a further
 *  pick with no change of theirs moves nothing. */
async function offeredAfterGap(page: any, st: any, text: string | RegExp | null): Promise<void> {
  let s = await scene(page);
  if (typeof text === "string") assert.equal(s.selected, text, "the person's selection stands"); else if (text) assert.match(s.selected, text, "the person's selection stands");
  assert.deepEqual([s.collapsed, s.inBody, s.boxless], [false, true, false], "a passage in the body with a box");
  assert.equal(s.hidden, false, "the person's event offers the float (before: the pass in the gap, with no record to compare with, recorded their selection as its own, and the event compared equal and offered nothing)");
  near(s.left, s.expectedLeft, "...beside the selection's end, showFloat's arithmetic for the live range"); near(s.top, s.expectedTop, "...on its line");
  assert.equal(s.composer, false, "no composer opened on its own");
  // the pinned rule stands: the same pick with no change of the person's moves nothing and offers nothing new
  const standing = { left: s.left, top: s.top, selChanges: s.selChanges };
  await page.evaluate(() => { (window as any).__pick(); });
  await frames(page, 4);
  s = await scene(page);
  assert.deepEqual([s.hidden, s.left, s.top, s.marks], [false, standing.left, standing.top, 1], "a pick with no change of the person's leaves the float where the offer put it: the paint's own move is no offer");
  st.diagnostic("the pick with no change fired " + (s.selChanges - standing.selChanges) + " selectionchange event(s) of its own");
}

test("in a browser, the real viewer and panel: the ORDINARY state of an open panel, NO record, then the person's selection with a settings pick from another pane landing in its gap, on three roads, each its own subtest: the KEYBOARD (a real drag in the last paragraph, Shift+ArrowDown until the focus leaves the body for the aside, where the listener hides the float and drops the record, then Shift+ArrowUp bringing the selection back into the body with the pass at the arrow's keyup: the keyboard-offer leg's round-4 geometry, since Chromium extends no selection from a bare caret in plain text), and the SELECTION API from a real click's caret with no key event at all (setBaseAndExtent, and Selection.modify by a word: a screen reader or caret browser moves the selection through the accessibility layer and the page sees no key; the pass fired in the same task, so in the gap by construction); each offers the float beside the selection as the pass left it (before: the first latch was raised over a standing record alone, so with none the pass recorded the person's selection as its own, and their event compared equal and offered nothing, the PR's own defect still reachable on the road the feature exists for); then the same pick with no change of the person's offers nothing", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    await t.test("the keyboard: Shift+ArrowDown out of the body (the record dropped), Shift+ArrowUp back in with the pass at the arrow's keyup", { timeout: 120000 }, async (st) => {
      const { page, errors } = await openWith(browser, E);
      // the body at its end, a real drag over the last paragraph's first ten characters: offered
      await page.evaluate(() => { getSelection()!.removeAllRanges(); const b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop = b.scrollHeight; });
      await frames(page, 2);
      const r: Ends = await page.evaluate(() => { const ps = document.querySelectorAll(".fileview-md > p"); const p = ps[ps.length - 1] as HTMLElement; const range = document.createRange(); range.setStart(p.firstChild!, 0); range.setEnd(p.firstChild!, 10); const b = range.getBoundingClientRect(); return { x1: b.left + 1, y1: b.top + b.height / 2, x2: b.right - 1, y2: b.top + b.height / 2 }; });
      await drag(page, r);
      let s = await scene(page);
      assert.deepEqual([s.selected, s.hidden, s.marks], ["Filler 40:", false, 1], "the drag selected the last paragraph's first ten characters and the float is offered; the peer's mark stands on paragraph 2");
      await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
      // Shift+ArrowDown until the focus leaves the body for the aside: the float goes and the listener drops the record (round 4)
      let downs = 0;
      while (await focusInBody(page)) { await shiftKey(page, "ArrowDown"); downs++; assert.ok(downs < 12, "Shift+ArrowDown reaches the aside within twelve presses"); }
      s = await scene(page);
      assert.deepEqual([s.hidden, s.inBody], [true, false], "the focus out of the body after " + downs + " presses: the float goes, and the record with it (the ordinary state)");
      const baseline = s.selChanges;
      // Shift+ArrowUp with the pass in its gap: the selection back in the body, a passage over NO record
      const gap = await pressInGap(page, "ArrowUp", baseline);
      assert.equal(gap.before.selChanges, baseline, "the premise: at the keyup the key's selectionchange is still to come (the pass is in the gap)");
      assert.equal(gap.before.hidden, true, "...with no offer standing");
      assert.deepEqual([gap.after.collapsed, gap.after.marks], [false, 1], "the pass left the selection standing and the peer's mark painted anew");
      assert.equal(gap.after.selChanges, baseline, "the pass fired nothing of its own (its writes touch paragraph 2 alone)");
      st.diagnostic("at the keyup the selection read " + JSON.stringify(gap.after.selected.slice(0, 40)) + "; the float was " + (gap.after.hidden ? "hidden" : "shown"));
      await offeredAfterGap(page, st, null);
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    });
    for (const road of API_ROADS) await t.test(road.name, { timeout: 120000 }, async (st) => {
      const { page, errors } = await openWith(browser, E);
      await clickCaret(page);
      const s = await scene(page);
      assert.deepEqual([s.collapsed, s.inBody, s.hidden, s.marks], [true, true, true, 1], "the click's caret: a collapsed selection in the body, no offer standing, the peer's mark on paragraph 2");
      const baseline = s.selChanges;
      const { before, after } = await apiChangeInGap(page, road.kind);
      if (typeof road.text === "string") assert.equal(before.selected, road.text, "the premise: at the pass the selection holds the person's change"); else assert.match(before.selected, road.text, "the premise: at the pass the selection holds the person's change");
      assert.equal(before.selChanges, baseline, "...and its selectionchange is still to come");
      assert.equal(before.hidden, true, "...with no offer standing (no record: the ordinary state)");
      assert.deepEqual([after.selected, after.marks], [before.selected, 1], "the pass left the selection whole (paragraph 3 holds no mark) and the peer's mark standing");
      assert.equal(after.selChanges, baseline, "the pass fired nothing of its own (its writes touch paragraph 2 alone)");
      st.diagnostic("at the pass the float was " + (after.hidden ? "hidden" : "shown") + "; the selection read " + JSON.stringify(after.selected));
      await offeredAfterGap(page, st, road.text);
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    });
  });
});

test("in a browser, the real viewer and panel: a change whose selectionchange ALREADY RAN, over a STALE record (the review's round 1, extra6-1): a real drag inside a peer's highlight offers the float; a second press inside the highlight drags out another passage, its events delivered under the press (which the listener ignores), and the press ends at the window's blur, with no mouseup for the seam to offer at, so the record still names the first passage; a settings pick from another pane then repaints the marks, moving the selection's anchor out of the mark and firing an event of its own: no Comment button, since nobody selected the remnant (before: the head read the delivered change as one still to come over the stale record, dropped the record, and the pass's own event offered the float with no gesture)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, ON);
    await dragInside(page, MARK_ON, 3, 14);
    let s = await scene(page);
    assert.equal(s.selected, "lorem ipsum dolor sit amet".slice(3, 14), "the drag selected the passage inside the highlight");
    assert.deepEqual([s.hidden, s.marks], [false, 1], "the drag's mouseup offers the float; the peer's mark stands");
    // the second press inside the mark, on a character outside the first selection (a press inside a selection starts a drag of its
    // text instead), dragged into the plain text after the mark and HELD: the float goes at the press, the drag's events run, and the
    // pass to come moves the anchor out of the mark and leaves the plain text's part, a remnant with a box (the ON cut's geometry)
    const ends = await page.evaluate(([sel, a, k]: [string, number, number]) => {
      const m = document.querySelector(sel) as HTMLElement; const t = m.firstChild as Text; const after = m.nextSibling as Text;
      const ra = document.createRange(); ra.setStart(t, a); ra.setEnd(t, a + 1); const x = ra.getBoundingClientRect();
      const rb = document.createRange(); rb.setStart(after, k - 1); rb.setEnd(after, k); const y = rb.getBoundingClientRect();
      return { x1: x.left + 1, y1: x.top + x.height / 2, x2: y.right - 1, y2: y.top + y.height / 2 };
    }, [MARK_ON, 20, 8]);
    const dragged = "lorem ipsum dolor sit amet".slice(20) + P2.slice(P2.indexOf(" consectetur"), P2.indexOf(" consectetur") + 8);
    await page.mouse.move(ends.x1, ends.y1); await page.mouse.down(); await page.mouse.move(ends.x2, ends.y2, { steps: 6 });
    await page.waitForFunction((tx: string) => String(getSelection()) === tx, dragged, { timeout: 5000 });
    await frames(page, 4);
    const held = await scene(page);
    assert.deepEqual([held.selected, held.hidden], [dragged, true], "the drag's passage, from inside the mark into the plain text after it, stands selected and the press hid the float");
    const c1 = held.selChanges; await frames(page, 4); const c2 = (await scene(page)).selChanges;
    assert.equal(c2, c1, "the drag's every selectionchange has run: the count stands still (" + c1 + ")");
    // the window's blur ends the press (a release in another window never reaches this one): no mouseup, no offer, the record stale
    await page.evaluate(() => { window.dispatchEvent(new Event("blur")); });
    // the pass, from the test with no hook and nothing pending: a settings pick from another pane
    await page.evaluate(() => { (window as any).__pick(); });
    await frames(page, 4);
    s = await scene(page);
    t.diagnostic("after the pick the selection reads " + JSON.stringify(s.selected) + " as " + JSON.stringify(s.anat) + "; the pass fired " + (s.selChanges - c2) + " selectionchange event(s) of its own; the float is " + (s.hidden ? "hidden" : "shown at " + s.left + "/" + s.top));
    assert.ok(s.selChanges > c2, "the premise: the pass moved the selection (the mark's text merged away and wrapped anew) and fired an event of its own");
    assert.deepEqual([s.collapsed, s.inBody, s.boxless, s.marks], [false, true, false, 1], "...leaving a remnant with a box in the body (the plain text's part), the peer's mark painted anew: a remnant the event would offer beside over no record");
    assert.equal(s.hidden, true, "no Comment button with no gesture: the paint's own move of the selection is no offer (before: the pass read the delivered drag as a change still to come, dropped the record, and this event offered the float beside a remnant nobody selected)");
    assert.equal(s.composer, false, "no composer opened on its own");
    await page.mouse.up();
    await frames(page, 2);
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

// ── the third refusal in the gap: the paint-offer browser file's leg 7 (a tracked note whose struck label, shown inline, pushes a
// last-visible-line selection whole below the body's bottom edge) with the pass landing in the gap of the person's Shift+ArrowRight ──
const NOTE_TRACKED = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const P5_END = NOTE_TRACKED.indexOf(PARA(5)) + PARA(5).length;
const OLD = " Removed sentence: this text was cut from the end of the fifth paragraph and is long enough to add at least one line at the pane's width.";
const DEL = { id: "d1", author: "api", ts: T0 + 1000, kind: "del", curFrom: P5_END, curTo: P5_END, baseFrom: P5_END, baseTo: P5_END + OLD.length, oldText: OLD, newText: "", anchor: null };
const TRACKED = { ...STATUS, hunks: [DEL], store: { ...STATUS.store, suggestions: [{ id: "d1", authorId: SID }] } };
type ClipScene = { hidden: boolean; left: number; top: number; expectedLeft: number; expectedTop: number; selected: string; selBottom: number; bodyBottom: number; selInBody: boolean; selBelowBody: boolean; floatInBodyBand: boolean | null; dels: number; composer: boolean; selChanges: number };
/** The float, the selection's box against the body's, and whether the button's own box lies inside the body's band. */
const clipScene = (page: any): Promise<ClipScene> => page.evaluate(() => {
  const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!;
  const body = document.querySelector(".fileview-body") as HTMLElement; const b = body.getBoundingClientRect();
  const r = sel.rangeCount && !sel.isCollapsed ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
  const fr = f.hidden ? null : f.getBoundingClientRect();
  return { hidden: f.hidden, left: parseFloat(f.style.left), top: parseFloat(f.style.top),
    expectedLeft: r ? Math.min(Math.max(8, r.right + 6), window.innerWidth - 90) : NaN, expectedTop: r ? Math.min(Math.max(8, r.top - 30), window.innerHeight - 34) : NaN,
    selected: String(sel), selBottom: r ? r.bottom : NaN, bodyBottom: b.bottom,
    selInBody: !!r && r.bottom > b.top && r.top < b.bottom, selBelowBody: !!r && r.top >= b.bottom,
    floatInBodyBand: fr ? fr.bottom > b.top && fr.top < b.bottom : null,
    dels: document.querySelectorAll(".fileview-body .fc-del").length, composer: !!document.querySelector(".fileview-aside .fc-composer .fc-input"),
    selChanges: (window as any).__selChanges as number };
});
/** The 500 by 400 px pane on the tracked note, Show changes inline OFF, a real drag over paragraph 6's characters 5 to 20, then (`pushOut`)
 *  a scroll that leaves the selected line the body's LAST visible one (leg 7's scene: the scroll hides the float) or none (the control,
 *  the passage in the body's middle); then Shift+ArrowRight, the keyboard's offer beside the line, which is the record of it. */
async function upToClipOffer(browser: any, pushOut: boolean): Promise<{ page: any; errors: string[] }> {
  const { page, errors } = await openViewer(browser, "pane", 500, 400, { docs: { [REPORT]: NOTE_TRACKED } });
  await page.evaluate((st: unknown) => { (window as any).__status = st; }, TRACKED);
  await openPanel(page);
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body .fc-del").length === 1, null, { timeout: 10000 });
  await page.click('button[data-act="fcinline"]');
  await page.waitForFunction(() => document.querySelectorAll(".fileview-body .fc-del").length === 0, null, { timeout: 10000 });
  await frames(page, 2);
  await page.evaluate(() => {
    const w = window as any;
    w.__selChanges = 0; document.addEventListener("selectionchange", () => { w.__selChanges++; });
    w.__pick = () => {
      const KEY = "romp:settings"; const raw = localStorage.getItem(KEY); const cur = raw ? JSON.parse(raw) : {};
      const next = { ...cur, changesInline: cur.changesInline === false };
      localStorage.setItem(KEY, JSON.stringify(next));
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, oldValue: raw, newValue: JSON.stringify(next), storageArea: localStorage, url: location.href }));
    };
  });
  await page.evaluate(() => {
    const body = document.querySelector(".fileview-body") as HTMLElement;
    const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((e) => (e.textContent || "").startsWith("Paragraph 6:")) as HTMLElement;
    body.scrollTop += p.getBoundingClientRect().top - body.getBoundingClientRect().top - 40;
  });
  await frames(page, 2);
  const g = await page.evaluate(() => {
    const p = Array.from(document.querySelectorAll(".fileview-md > p")).find((e) => (e.textContent || "").startsWith("Paragraph 6:")) as HTMLElement;
    const range = document.createRange(); range.setStart(p.firstChild!, 5); range.setEnd(p.firstChild!, 20);
    const b = range.getBoundingClientRect(); return { x1: b.left + 1, x2: b.right - 1, y: b.top + b.height / 2 };
  });
  await page.mouse.move(g.x1, g.y); await page.mouse.down(); await page.mouse.move(g.x2, g.y, { steps: 4 }); await page.mouse.up();
  await page.waitForFunction(() => !(document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
  if (pushOut) {
    await page.evaluate(() => {
      const body = document.querySelector(".fileview-body") as HTMLElement; const sel = getSelection()!;
      const r = sel.getRangeAt(0).getBoundingClientRect(); const b = body.getBoundingClientRect();
      body.scrollTop -= (b.bottom - r.bottom) - 3;
    });
    await page.waitForFunction(() => (document.querySelector(".fc-float") as HTMLElement).hidden, null, { timeout: 5000 });
    await frames(page, 2);
  }
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
  await page.waitForFunction((n: number) => !(document.querySelector(".fc-float") as HTMLElement).hidden && String(getSelection()).length === n, 16, { timeout: 5000 });
  await frames(page, 2);
  return { page, errors };
}
type ClipGap = { key: string; selectedAtHook: string; selChangesAtHook: number; hiddenBefore: boolean; hiddenAfter: boolean; delsAfter: number; selTopAfter: number; bodyBottomAfter: number };
/** Shift+ArrowRight with the pass armed in its gap (a one-shot capture keyup listener reads the scene, fires the pick and reads it again),
 *  awaited on the key's selectionchange; the hook's record. */
async function clipPressInGap(page: any): Promise<ClipGap> {
  const baseline: number = await page.evaluate(() => (window as any).__selChanges as number);
  await page.evaluate(() => {
    const w = window as any; w.__gap = null;
    const read = () => {
      const f = document.querySelector(".fc-float") as HTMLElement; const sel = getSelection()!; const body = document.querySelector(".fileview-body") as HTMLElement;
      const r = sel.rangeCount && !sel.isCollapsed ? sel.getRangeAt(sel.rangeCount - 1).getBoundingClientRect() : null;
      return { hidden: f.hidden, selTop: r ? r.top : NaN, bodyBottom: body.getBoundingClientRect().bottom, dels: document.querySelectorAll(".fileview-body .fc-del").length };
    };
    document.addEventListener("keyup", (ev) => {
      const before = read(); const selectedAtHook = String(getSelection()); const selChangesAtHook = w.__selChanges as number;
      w.__pick();
      const after = read();
      w.__gap = { key: (ev as KeyboardEvent).key, selectedAtHook, selChangesAtHook, hiddenBefore: before.hidden, hiddenAfter: after.hidden, delsAfter: after.dels, selTopAfter: after.selTop, bodyBottomAfter: after.bodyBottom };
    }, { once: true, capture: true });
  });
  await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
  await page.waitForFunction(() => (window as any).__gap !== null, null, { timeout: 5000 });
  await page.waitForFunction((n: number) => (window as any).__selChanges > n, baseline, { timeout: 5000 });
  await frames(page, 3);
  const gap: ClipGap = await page.evaluate(() => (window as any).__gap);
  assert.ok(gap, "the keyup hook ran");
  assert.equal(gap.key, "ArrowRight", "...at the arrow's keyup");
  assert.equal(gap.selectedAtHook.length, 17, "the premise: the person's change is already in the live selection at the hook");
  assert.equal(gap.selChangesAtHook, baseline, "the premise: their selectionchange has not been delivered yet (the pass is in the gap)");
  assert.equal(gap.delsAfter, 1, "the pass painted the struck label above the line");
  return gap;
}

test("in a browser, the real Files pane at 500 by 400 px: the paint-offer browser file's leg 7 with the pass landing in the GAP (the review's round 1, ui-1 and extra6-2), each scene its own subtest: a tracked note with a deletion above the sixth paragraph, Show changes inline off, a real drag over that paragraph's words, a scroll that leaves the selected line the body's last visible one, Shift+ArrowRight (the keyboard's offer beside the line), then Shift+ArrowRight again with a settings pick from another pane in its gap, whose struck label pushes the whole passage below the body's bottom edge: the pass hides the float and the person's event refuses the clipped passage, so no Comment button stands over the body's last visible line beside text nobody selected (before: the pending branch left the float for the event, and the event seated the button inside the body's band while the passage was out of view, case (9) by the pending road); the control, the same pass in the same gap with the passage in the body's middle: the event offers beside it, inside the band", { timeout: 300000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    await t.test("the passage pushed below the body's bottom edge: hidden, and no button over the last visible line", { timeout: 120000 }, async (st) => {
      const { page, errors } = await upToClipOffer(browser, true);
      let s = await clipScene(page);
      assert.deepEqual([s.selected, s.selInBody, s.hidden], [PARA(6).slice(5, 21), true, false], "the keyboard's offer stands beside the passage, on the body's last visible line");
      assert.ok(s.bodyBottom - s.selBottom < 30, "the premise: the selected line is the body's last visible one (" + (s.bodyBottom - s.selBottom).toFixed(1) + " px above the body's bottom)");
      const gap = await clipPressInGap(page);
      st.diagnostic("at the hook the float was " + (gap.hiddenBefore ? "hidden" : "shown") + "; after the pass the passage sits at " + gap.selTopAfter.toFixed(1) + " against the body's bottom edge at " + gap.bodyBottomAfter.toFixed(1) + ", the float " + (gap.hiddenAfter ? "hidden" : "shown"));
      assert.ok(gap.selTopAfter >= gap.bodyBottomAfter, "the premise: the pass pushed the whole passage below the body's bottom edge, out of view");
      assert.equal(gap.hiddenAfter, true, "the pass hides the float: a passage pushed out of the body's box takes no button, the change pending or not (before: left standing for the event)");
      s = await clipScene(page);
      st.diagnostic("after the person's event: hidden " + s.hidden + ", the button at " + s.left + "," + s.top + ", the passage's bottom at " + s.selBottom.toFixed(1) + ", the body's at " + s.bodyBottom.toFixed(1) + ", inside the body's band " + s.floatInBodyBand);
      assert.equal(s.selected, PARA(6).slice(5, 22), "the person's change stands");
      assert.equal(s.selBelowBody, true, "the passage is still below the body's bottom edge, out of view");
      assert.equal(s.hidden, true, "the person's event refuses the clipped passage: no Comment button over the body's last visible line (before: seated inside the band, beside other text, while the passage it would comment on was out of view)");
      assert.equal(s.composer, false, "no composer opened on its own");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    });
    await t.test("the control: the passage in the body's middle, the same pass in the same gap: offered beside it, inside the band", { timeout: 120000 }, async (st) => {
      const { page, errors } = await upToClipOffer(browser, false);
      let s = await clipScene(page);
      assert.deepEqual([s.selected, s.selInBody, s.hidden], [PARA(6).slice(5, 21), true, false], "the keyboard's offer stands beside the passage, in the body's middle");
      const gap = await clipPressInGap(page);
      st.diagnostic("control: after the pass the passage sits at " + gap.selTopAfter.toFixed(1) + ", the body's bottom at " + gap.bodyBottomAfter.toFixed(1) + ", the float " + (gap.hiddenAfter ? "hidden" : "shown"));
      s = await clipScene(page);
      assert.equal(s.selInBody, true, "the passage is in view");
      assert.equal(s.hidden, false, "the person's event offers the float beside their change");
      near(s.left, s.expectedLeft, "...beside the selection as the pass left it"); near(s.top, s.expectedTop, "...on its line");
      assert.equal(s.floatInBodyBand, true, "...inside the body's band");
      assert.deepEqual(errors, [], "no script error");
      await page.close();
    });
  });
});

test("in a browser, the real viewer and panel: a change of the person's that RETURNS the selection to the ends the last pass left (the review's round 2): a real drag over a plain paragraph's words offers the float; a settings pick from another pane over the offered selection moves nothing (a quiet pass); Shift+ArrowRight is delivered and offers beside the grown selection; then Shift+ArrowLeft back to the drag's ends with the pick in its gap: the pass leaves the float where the last offer put it and the person's event offers beside the shrunk selection (before: the quiet pass's note stood past the delivered event, the head read the return to its ends as the pass's own move, the pass recorded it and hid the button the change had moved a glyph from under, and the event compared equal and offered nothing); then the same pick with no change of the person's moves nothing and its event offers nothing", { timeout: 240000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const { page, errors } = await openWith(browser, E);
    await dragOver(page, 13, 30);
    let s = await scene(page);
    assert.deepEqual([s.selected, s.hidden, s.marks], [P2.slice(13, 30), false, 1], "the drag selected the passage, the mouseup offered the float, and the peer's mark stands after the passage on its line");
    const dragged = { left: s.left, top: s.top, selChanges: s.selChanges };
    // the quiet pass: a pick over the offered selection, which moves nothing on the line (the mark is after the passage) and notes what it left
    await page.evaluate(() => { (window as any).__pick(); });
    await frames(page, 4);
    s = await scene(page);
    assert.deepEqual([s.selected, s.hidden, s.left, s.top], [P2.slice(13, 30), false, dragged.left, dragged.top], "the quiet pass left the selection and the float as the drag's offer put them");
    t.diagnostic("the quiet pass fired " + (s.selChanges - dragged.selChanges) + " selectionchange event(s) of its own");
    // Shift+ArrowRight with no pass in its gap: delivered, and offered beside the grown selection
    const n1 = s.selChanges;
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
    await page.keyboard.down("Shift"); await page.keyboard.press("ArrowRight"); await page.keyboard.up("Shift");
    await page.waitForFunction((k: number) => (window as any).__selChanges > k, n1, { timeout: 5000 });
    await frames(page, 2);
    s = await scene(page);
    assert.deepEqual([s.selected, s.hidden], [P2.slice(13, 31), false], "Shift+ArrowRight, delivered: offered beside the grown selection");
    near(s.left, s.expectedLeft, "...beside the grown selection's end"); near(s.top, s.expectedTop, "...on its line");
    const grown = { left: s.left, top: s.top, selChanges: s.selChanges };
    // Shift+ArrowLeft back to the drag's ends, the ends the quiet pass left, with the pick forced into its gap at the arrow's keyup
    const gap = await pressInGap(page, "ArrowLeft", grown.selChanges);
    premise(gap, P2.slice(13, 30), grown.selChanges, grown.left, "the return");
    assert.deepEqual([gap.after.selected, gap.after.marks], [P2.slice(13, 30), 1], "the pass left the shrunk selection whole and the peer's mark standing");
    assert.deepEqual([gap.after.hidden, gap.after.left], [false, grown.left], "the pass in the gap leaves the float where the last offer put it: the change is the event's to answer (before: the head found the return at the last pass's note, read it as the pass's own move, recorded it, and hid the button the change had moved a glyph from under)");
    // the outcome, after the event: offered beside the shrunk selection
    s = await scene(page);
    assert.equal(s.selected, P2.slice(13, 30), "the keyboard shrank the selection back to the drag's ends");
    assert.equal(s.hidden, false, "the person's Shift+ArrowLeft offers the float beside the shrunk selection (before: the event compared equal with the record the pass wrote and offered nothing, the button gone)");
    near(s.left, s.expectedLeft, "...beside the selection's end, showFloat's arithmetic for the live range"); near(s.top, s.expectedTop, "...on its line");
    assert.notEqual(s.left, grown.left, "...a place the change moved (the float's place is a witness here)");
    assert.equal(s.composer, false, "no composer opened on its own");
    // the pinned rule stands: the same pick with NO change of the person's moves nothing, and its own event, where it fires one, offers nothing
    const standing = { left: s.left, top: s.top, selChanges: s.selChanges };
    await page.evaluate(() => { (window as any).__pick(); });
    await frames(page, 4);
    s = await scene(page);
    assert.deepEqual([s.selected, s.hidden, s.marks], [P2.slice(13, 30), false, 1], "a pick with no change of the person's leaves the selection whole and the float shown");
    assert.deepEqual([s.left, s.top], [standing.left, standing.top], "...where the offer put it: the paint's own move is no offer");
    t.diagnostic("the pick with no change fired " + (s.selChanges - standing.selChanges) + " selectionchange event(s) of its own");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});
