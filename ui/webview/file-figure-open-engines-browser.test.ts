// The one gate's tap cells and stacking cells in WebKit and Firefox, for the link-navigation follow-on of plans/markdown-viewer.md (the
// file review's round 17, tests-1 with regression-1, and the coordinator's decisions 1 to 3 on it; its extra9-1, and the coordinator's
// decision 4 on it; its round 18, extra5-1, extra5-2 and correctness-1, with the coordinator's decisions on them and the closing check
// after those fixes; and the closing check at 142ade155 after the fixes for the file review's round 18): the cells are file-figure-open-taps.ts's and file-figure-open-stacking.ts's, the sets
// file-figure-open-browser.test.ts runs in Chromium, each engine launched through real-viewer-leg.ts's inBrowser with the engine
// named. The stacking cells run in both engines on a page with a touchscreen beside the mouse, on the chat modal and the Files pane:
// a picture in a top-level table, inside author elements of page classes that would make a stacking context around it and inside an
// author's marquee, each scene red at 0ab74924c, its header naming each cell. The tap cells: WebKit runs them on a phone's pages and
// on a hybrid page (hasTouch with a mouse), on the chat modal and the Files pane, and Firefox on the hybrid page alone, since
// Playwright's Firefox takes no isMobile, the clicks after a drag of a picture and after a drag in another pane, and Firefox's chord,
// on a plain page too. Two more cases, WebKit's alone, read window errors: the Files pane's as its Comments aside opens beside a
// document of top-level tables (the table's own width written with its cap: file-view.ts watchBodyWidth), and the chat modal's, the
// Files pane's and the feed modal's as remote pictures in top-level tables load, one of them under the floor (the figures' decision
// at the next animation frame: file-view.ts watchFigureBoxes; the file review's round 18, extra6-3). The WebKit engine is
// Playwright's on Linux, under touch emulation for the cells on a phone's pages and on the hybrid page and for the stacking cells, a
// stand-in for WebKitGTK, and presumably WPE, on a touchscreen, and with no touchscreen for the plain page's cells and the
// window-error cases (the file review's round 18, tests-3); no cell claims iOS Safari or the iPhone, a cell
// run under a phone's pages included (WebKit's iOS source gives an iPhone tap's click the touch's own pointerId, read and not run on
// a device). In that WebKit a tap's click carries pointerId 1 of type mouse while its press carried the touch's, each tap cell
// asserting that shape as its precondition, and the click finds its press in the gate's one-click slot, as it does in every engine,
// a record ending at its own pointerup, which hands it to the slot, the click typed mouse where the slot's pointerup was typed touch,
// so the slot's pointerId test, which reads a click typed as the slot's pointerup was, leaves it alone; red at 0ab74924c, where the gate matched a click to its press by pointerId alone, so every tap on a loaded web picture or its
// control opened nothing, the double tap too, and the stale-record cells are red there as well, their reads a private witness kept
// out of the tree. Firefox gives a tap's click its press's pointerId (0), so its tap cells read the same at that head as at the fix, by
// design, recorded beside WebKit's; its double tap and WebKit's each assert their engine's own details (1 and 1), the second tap read
// at its own start and opening once after the first tap's reveal. The clicks after a drag (the file review's round 18, with the
// coordinator's decisions on open item 1): after a drag of a picture, and after a drag in another pane (a same-origin frame put into
// the page stands in for one), WebKit sends the mouse's next press as a mousedown with no pointerdown, and the gate ends every record
// there, so the mouse's first click on a web picture opens nothing and reveals its sign, whatever covers or shows it, and the click
// after it opens: the covered cells red under A18-R (the drag's) and at X (the other pane's), the cost cells with the control shown
// red at ef686b029 by design, recording the cost; Firefox, which ends such a drag with a pointercancel, opens at the first click where
// the control is shown. Firefox's chord cells (its extra5-1), a left press chorded by a middle or a right press, whose mousedown comes
// with no pointerdown of its own: the chord's click opens nothing, red at ef686b029 and under A18-M, whose gate took a verdict at that
// mousedown; the reads of these reds are a private witness kept out of the tree. The other-document cells (the closing check after
// the fixes for the file review's round 18), on the hybrid page in the dashboard's shape, the viewer's page in a same-origin frame of
// a top page: a tap on an element of the top page over the control, gone at its own pointerup, so the viewer's window hears the tap's
// compatibility mousedown, mouseup and click with no pointerdown or pointerup, opens nothing and the next click opens once, after
// nothing, after a right or a middle click on the picture with the control shown, and with the control above the top page's window at
// the tap's start, and in Firefox a tap on a hover tooltip of the top page over the control; the cells after a right or a middle
// click red at 0f998a3b9 in both engines, whose gate left the slot alone at the tap's mousedown, the reads a private witness kept out
// of the tree.
// The chain rule's cells (the closing check at 142ade155 after the fixes for the file review's round 18), the gate keyed on twelve
// events of the window's capture phase (pointerdown, mousedown, mouseup, pointerup, pointercancel, keydown, dragstart, touchend,
// touchcancel, pointerout, mouseout and click), in the dashboard's shape with the viewer's frame beside another pane's frame over a bar of the
// top page: in Firefox, on the hybrid page, the lone click Firefox sends after another document cancels a tap's pointerdown, with no
// mousedown and no mouseup before it, after a right or a middle click on the picture, after the viewer's own tap whose compatibility
// events or click went to another document, and after the mouse held on the control or pressed there and released on the top page's
// bar or in the other pane, opens nothing and the next click opens once, red at 142ade155 and, on the chat and the Files pane, under
// a gate without the tail (the gate takes a press for a pointer's click only right after a primary mouseup of detail above 0) and
// without the mouseup's clear (a mouseup other than a primary one of detail above 0 empties the slot and clears the tap's flag), but
// for the mouse held on the control, which the refusal of a record still standing at a click closes as well, the mouse released on
// the top page's bar, which the refusal of a record whose pointer left the viewer's window with a button down closes as well, and
// the mouse released in the other pane, which both refusals close as well (22 of the 28 lone-click cells red under that gate, 24
// with the refusal of a standing record dropped too and all 28 with both refusals dropped), and under a gate without the tail alone
// the four cells a surface of the viewer's tap whose compatibility events or click went elsewhere, the mouseup's clear closing the
// eight after a mouseup of another button or of detail 0 as well; in WebKit, on the hybrid page and on a phone's pages, another
// document's tap after the viewer's own tap whose pointerup that document took, so the viewer heard the touch's touchend and no
// pointerup, opens nothing and the next tap opens once, red at 142ade155 and, on the chat and the Files pane, under a gate whose
// touchend marks no touch record refused; and in Firefox, on the hybrid page, and in WebKit, on the hybrid page and on a phone's
// pages, another document's tap that cancels nothing, after the viewer's own tap whose compatibility mousedown an element of the top
// page took, so the viewer heard that tap's mouseup of detail 0 and no click, opens nothing and the next click opens once, red at
// 142ade155 and, on the chat and the Files pane, at 1a6470e72, whose gate had no mouseup's clear; and in Firefox, on the hybrid
// page, and in WebKit, on the hybrid page and on a phone's pages, another document's tap on an element over the control that hides
// at that tap's compatibility mousedown, after a mouse's press whose pointerup the viewer never heard (in WebKit the mouse held on
// the control or on the picture, in Firefox the mouse pressed on the control and released in the other pane), so the viewer hears
// that tap's mouseup of detail 1 and its click alone, opens nothing and the next click opens once, the gate refusing a pointer's
// click that finds a record still standing under its own pointerId, red at 142ade155, at 1a6470e72 and at 09f58bec6, whose click
// read the mouse's record; the reads of these reds a private witness kept out of the tree. The residual, an element of another
// same-origin document shown over the picture during the viewer's own tap and then a tap on that element, which opens in both
// engines (the closing check at 142ade155 measured Firefox 16 of 16 and WebKit 7 of 7), has no cell: no event the viewer hears tells
// that tap from the viewer's own, and whether to accept it is the owner's decision; under this gate the same check's probe read
// Firefox 16 of 16, WebKit 7 of 7 and Chromium 0 of 51, and every other order of the class it drives opened nothing; a check of
// these fixes drove orders that probe does not and found two more of the class outside the residual, open at 142ade155, at 1a6470e72
// and at 09f58bec6 (file-view.ts's gate comment states them): the first, the cells of a mouse's press whose pointerup the viewer
// never heard above, whose click read the mouse's record (WebKit 22 of 22, Firefox 7 of 7), is closed by the gate's refusal of a
// record still standing at a click; the second, in Firefox, after that release, a mouse click on such an element, whose pointerup
// handed the mouse's record to the slot and opened (10 of 10, again at 343ee2eb5), is closed by the gate's refusal of a mouse's or a
// pen's record whose pointer left the viewer's window with a button down, Firefox sending the viewer a pointerout with no
// relatedTarget as the press left its frame (0 of 10 under this gate): its cells in Firefox, on the hybrid page, the element hiding
// at that click's mousedown or its pointerdown, open nothing and the next click opens once, red at 343ee2eb5 and at 09f58bec6;
// Chromium opened neither. That refusal costs one class of press: a press whose pointer left the viewer's window with a button
// down, by the events the viewer heard, is refused once, its click opening nothing and revealing the control, and the next click
// opens once. Its first cost, measured in Firefox: the viewer's own press on the control dragged out of its frame and back,
// released on the control (its cost cell, where 343ee2eb5's gate opened that click; 8 of 8 in a probe of these fixes), while
// Chromium and WebKit, which keep a held left press in the frame it began in, opened it. Its second cost, measured in Chromium,
// found by a later check and with no cell: a press on the control or the picture held while the top page hides the viewer's frame
// and shows it again, then released there, refused only when the frame's next redraw came while it was hidden, which alone brings
// that pointerout with the button down, and opened otherwise (168 of 168 such presses refused and none of the 232 others in a
// later probe of these fixes that stamped that redraw, and all 11 of that check's own probe refused, where 343ee2eb5's gate opened
// all 11), while WebKit sends no such pointerout there and opens it. The later check found a third order of the class outside the
// residual, in
// WebKit and in Chromium, open at this head and, in WebKit, at 142ade155, 09f58bec6 and 343ee2eb5, with no cell, for the owner
// (file-view.ts's gate comment states it): the mouse held on the control while the top page hides the viewer's frame and shows it
// again, then another document's mouse click on an element over the control that hides at that click's mousedown or its
// pointerdown, whose pointerup hands the held press's record to the slot (WebKit opening it at every timing, 3,700 of 3,700 in a
// later probe of these fixes and 60 of 60 in that check's probe; Chromium whenever the release comes before the first redraw to
// start after the hide, 1,526 of 3,700 in the later probe; Firefox never, 0 of 2,600 on the Files pane and the chat). The gate's
// cost measured in WebKit, the same at 142ade155: WebKit's
// cost cell, the viewer's own tap whose pointerup an
// element of the top page takes, shown at the tap's pointerdown and hidden at its pointerup, opens nothing and reveals the
// control, and the next tap opens once, the tap's click carrying pointerId 1 and finding its press only in the slot, which no
// pointerup of that tap filled. The chain rule's costs, none measured, each a refusal that reveals the control: a Firefox
// touchscreen whose tap's click came typed touch under a pointerId other than its pointerup's would refuse every tap there, the
// tab opening only from the mouse or the keyboard; a pen in the touch order whose click comes typed mouse, as WebKitGTK would
// type it by analogy with a touch's, would refuse every tap of that pen, the tab still opening from a finger, the mouse or the
// keyboard; a tap during which another finger that touched the viewer lifts, in an engine that clicks after such a tap, opens
// nothing and reveals the control, the next tap opening once; an engine whose touchend came before its pointerup would refuse
// every tap (none of the three measured); and a pointer's click with no primary mouseup of detail above 0 before it, an assistive
// technology's trusted click with a pointerId and no mouseup or an eraser's tap whose mouseup does not carry the primary button,
// opens nothing and reveals the control, while Enter or Space on the control still opens, and so does a pointer's click after
// whose pointerup a mouseup other than a primary one of detail above 0 came, an order none of the three engines measured sends
// before a click, and a pointer's click that finds a record still standing under its own pointerId, which no gesture of the
// viewer's own that the legs drive leaves. The refusal's cost measured in WebKit alone: a left click chorded into a held right
// press, whose pointerup WebKit holds until the last button's release, opens nothing and reveals the control whatever covers or
// shows it, and the next click opens, 12 of 12 in the road probe, where 09f58bec6's gate opened all 12 (file-view.ts's gate
// comment states it).
// This leg stays off the shared roster of browser legs that PR 887 brings: that roster's job installs Chromium alone, so a WebKit or
// Firefox test in a rostered file would not run there.
// Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, and no job installs Firefox
// or WebKit, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper); file-view-outline.test.ts
// drives WebKit's order, the stale records and the clicks by no pointer over the stand-in in CI. Synthetic values only: the
// notes-api world, a placeholder session id, example.test addresses, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, PARA, REPORT } from "./real-viewer-leg";
import { tapCells, type TapDevice, type TapEngine, type TapSurface } from "./file-figure-open-taps";
import { stackCells, type StackEngine, type StackSurface } from "./file-figure-open-stacking";

const ON: Record<TapDevice, string> = { phone: "a phone's pages (hasTouch and isMobile at a device scale of 1, the kernel's viewport meta)", hybrid: "a hybrid page (hasTouch with a mouse)" };
for (const [engine, devices] of [["webkit", ["phone", "hybrid"]], ["firefox", ["hybrid"]]] as Array<[TapEngine, TapDevice[]]>) for (const device of devices) for (const surface of ["chat", "pane"] as TapSurface[]) {
  const named = engine === "webkit" ? "WebKit (Playwright's, on Linux under touch emulation)" : "Firefox";
  const red = engine === "webkit"
    ? "red at 0ab74924c, whose gate matched a click to its press by pointerId alone: every tap opened nothing, the double tap too, and " + (device === "hybrid" ? "the right press's and the drag's cells and the clicks after a drag red there too; the covered clicks after a drag red under A18-R, the gate with the rule the file review's round 18 found reverted and no clear put in its place, the other pane's covered clicks red at X, the gate with a dragstart clear and records ended at no pointerup, the cost cells red at ef686b029 by design, recording the cost, and the other-document cells after a right click or a middle click red at 0f998a3b9, whose gate left the slot alone at the tap's mousedown; their reads a private witness kept out of the tree; " : "") + "the key cells green there by design"
    : "every tap cell but the other-document cells reading the same at 0ab74924c as at the fix, by design, Firefox's tap click carrying its press's pointerId; the chord cells red at ef686b029 and under A18-M, whose gate took a verdict at the chord's mousedown, and the other-document cells after a right click or a middle click red at 0f998a3b9, whose gate left the slot alone at the tap's mousedown, their reads a private witness kept out of the tree";
  const afterDrag = engine === "webkit"
    ? "after a drag of the picture, or of one picture, a click of the mouse on that picture or on another, its control shown and uncovered, opens nothing and the next opens once, a stated cost; after a right click on the picture or a press on the control released beside the picture, with the control shown, then a drag in another pane, then the flyout over the control, opened by a script's click or by Enter on its button, a click of the mouse on the picture opens nothing and the next opens once, and with no cover, after no earlier press or after a right click, the first click opens nothing and the next opens once, a stated cost; "
    : "after a drag of the picture, or of one picture, a click of the mouse on that picture or on another, its control shown and uncovered, opens once; after a right click on the picture or a press on the control released beside the picture, with the control shown, then a drag in another pane, then the flyout over the control, opened by a script's click or by Enter on its button, a click of the mouse on the picture opens nothing and the next opens once, and with no cover the first click opens once; a left press on the picture under the flyout or the Outline popover, or begun with the control out of view, chorded by a middle or a right press, opens nothing and the next click opens once; ";
  const chained = device === "hybrid" || engine === "webkit";
  const chain = !chained ? "" : engine === "webkit"
    ? "in the dashboard's shape beside another pane, another document's tap after the viewer's own tap whose pointerup that document took, the viewer hearing its touchend and no pointerup, opens nothing and the next tap opens once, another document's tap that cancels nothing after the viewer's own tap whose compatibility mousedown an element of the top page took, the viewer hearing that tap's mouseup of detail 0 and no click, opens nothing and the next click opens once, another document's tap on an element over the control that hides at that tap's compatibility mousedown after the mouse held on the control or on the picture, the viewer hearing that tap's mouseup of detail 1 and its click alone, opens nothing and the next click opens once, and the viewer's own tap whose pointerup an element of the top page takes opens nothing and reveals the control and the next tap opens once, a stated cost; "
    : "in the dashboard's shape beside another pane, the lone click Firefox sends after another document cancels a tap's pointerdown opens nothing and the next click opens once, after a right or a middle click on the picture, after the viewer's own tap whose compatibility events or click went to another document, and after the mouse held on the control or pressed there and released on the top page's bar or in the other pane, and another document's tap that cancels nothing after the viewer's own tap whose compatibility mousedown an element of the top page took, the viewer hearing that tap's mouseup of detail 0 and no click, opens nothing and the next click opens once, and so does another document's tap on an element over the control that hides at that tap's compatibility mousedown after the mouse pressed on the control and released in the other pane, the viewer hearing that tap's mouseup of detail 1 and its click alone, and so does another document's mouse click on an element over the control that hides at that click's mousedown or its pointerdown after that press, whose pointer left the viewer's frame with the button down, the viewer hearing that click's pointerup, its mouseup of detail 1 and its click; and so does a tap on an element of the top page that appeared over the picture at the viewer's own tap's pointerup, with no layout read and the mouse off the viewer or laid out with a mouse resting in the viewer, the viewer hearing a mouseout to no element after its tap's pointerup, with a button down or with none; the viewer's own press on the control dragged out of its frame and back, released on the control, opens nothing and reveals the control and the next click opens once, a stated cost; ";
  const chainRed = !chained ? "" : engine === "webkit"
    ? "; the chain rule's cell of the lost pointerup red at 142ade155 and under a gate whose touchend marks no touch record refused, its cell of the mouseup that ended the chain red at 142ade155 and at 1a6470e72, whose gate had no mouseup's clear, its cells of the held mouse red at 142ade155, at 1a6470e72 and at 09f58bec6, whose click read the mouse's record, the cost cell reading the same at 142ade155 by design"
    : "; the chain rule's cells red at 142ade155, the lone click's under a gate without the tail and the mouseup's clear but after the mouse held on the control, which the refusal of a record still standing at a click closes too, after the mouse released on the top page's bar, which the refusal of a record whose pointer left the viewer's window with a button down closes too, and after the mouse released in the other pane, which both refusals close too, four of them under a gate without the tail alone, its cell of the mouseup that ended the chain at 1a6470e72, whose gate had no mouseup's clear, and its cell of the mouse released in the other pane before another document's tap at 1a6470e72 and at 09f58bec6, whose click read the mouse's record, and under a gate without both refusals, its cells of that release before another document's mouse click red at 343ee2eb5 and at 09f58bec6, whose pointerup handed the slot the mouse's shown record, and its cost cell reading an open there and at 142ade155, recording the cost, and its cells of a tap whose compatibility events went to another document red at ddb446fae, whose gate heard no mouseout, and under a gate without the mouseout listener, the cell with no button down also under one whose mouseout needs a button down";
  test("in " + named + " on " + ON[device] + ", the " + (surface === "chat" ? "chat modal" : "Files pane") + ": the one gate's tap cells (the file review's round 17, tests-1 with regression-1; its round 18, " + (engine === "webkit" ? "correctness-1" : "extra5-1") + ", with the coordinator's decisions" + (chained ? "; the closing check at 142ade155 after the fixes for the file review's round 18" : "") + (engine === "firefox" ? "; and the file review's round 19, extra8-2, with the coordinator's decisions on it" : "") + "): a tap on a loaded remote picture with its control in view opens once, on its control once, on a remote picture that wears the mark once; with the control out of view the first tap opens nothing and reveals it and the next opens once; a double tap there opens once, " + (engine === "webkit" ? "WebKit's" : "Firefox's") + " two clicks each of detail 1; under the text-size flyout or the Outline popover a tap opens nothing and closes it and the next opens once; " + (device === "hybrid" ? "after a right press of the mouse, or a mouse drag of the picture, with the control shown, then the flyout over the control, a tap opens nothing and the next opens once; on this page and on a plain page with no touchscreen, after a mouse drag of the picture with the control shown, then the flyout or the Outline popover over the control, a click of the mouse on the picture opens nothing and the next opens once; " + afterDrag + "in the dashboard's shape, a tap on another document's element over the control, gone at its pointerup, opens nothing and the next click opens once, after nothing, after a right or a middle click on the picture with the control shown, and with the control above the top page's window at the tap's start" + (engine === "firefox" ? ", and so does a tap on a hover tooltip of the top page over the control" : "") + "; " : "") + chain + "Enter on the control opens once, after a refused tap too; a press with no click (a script's pointerdown and pointerup, standing in) begun out of view then Enter in view opens once, and one begun shown then the flyout over the control then a script's click opens nothing (" + red + chainRed + "; the Enter cells red under a gate that reads a key's click as a pointer's, the press cells under one that lets a key's or a script's click read the slot with the keydown's clear dropped)", { timeout: 900000 }, async (t) => {
    let cells: Array<[string, unknown, unknown]> = [];
    let ran = false;
    await inBrowser(t, async (browser) => {
      ran = true;
      cells = await tapCells(browser, engine, device, surface, (m) => t.diagnostic(m));
    }, { engine });
    if (!ran) return;   // no browser: inBrowser skipped the case loudly
    for (const [what, , got] of cells) t.diagnostic("cell " + what + ": " + JSON.stringify(got));
    assert.ok(cells.length > 0, "the case ran its cells");
    assert.deepEqual(cells.map(([what, , got]) => [what, got]), cells.map(([what, want]) => [what, want]), "each cell's reading, [cell, reading] (property pins read off the page)");
  });
}
for (const engine of ["webkit", "firefox"] as StackEngine[]) for (const surface of ["chat", "pane"] as StackSurface[]) {
  const named = engine === "webkit" ? "WebKit (Playwright's, on Linux under touch emulation)" : "Firefox";
  test("in " + named + " on a page with a touchscreen beside the mouse, the " + (surface === "chat" ? "chat modal" : "Files pane") + ": the one gate's stacking cells (the file review's round 17, extra9-1, and the coordinator's decision 4 on it): a remote picture in a top-level table, the table positioned with no translate, then a positioned author element: the control takes the press at its centre, and a click, a tap, Enter and Space on it each open once; the same with the picture inside an author's div of romp-lightbox-img, and inside a span of path-full-wait inside a div of rail-hit, each element holding neither class after the paint; the table, then an svg's shadow placed over the control, and the same with the picture inside a div of meta-held-mark: no red pixel inside the control's box, and a click and Enter open once; the picture inside a div of ask-btn, then the shadow: no red pixel inside the control's box with the mouse held on it, and the release opens once; the picture inside an author's marquee, before the positioned element and before the shadow: no marquee after the paint, and the cells read as the table's; in each scene with the positioned element a click on the picture's own body, which the element takes, opens nothing, a stated cost (each scene red at 0ab74924c)", { timeout: 420000 }, async (t) => {
    let cells: Array<[string, unknown, unknown]> = [];
    let ran = false;
    await inBrowser(t, async (browser) => {
      ran = true;
      cells = await stackCells(browser, engine, surface, (m) => t.diagnostic(m));
    }, { engine });
    if (!ran) return;   // no browser: inBrowser skipped the case loudly
    for (const [what, , got] of cells) t.diagnostic("cell " + what + ": " + JSON.stringify(got));
    assert.ok(cells.length > 0, "the case ran its cells");
    assert.deepEqual(cells.map(([what, , got]) => [what, got]), cells.map(([what, want]) => [what, want]), "each cell's reading, [cell, reading] (property pins read off the page)");
  });
}

// The table's own width written with its cap. A top-level table shifts into the gutters by half of what it exceeds the column by, a left
// over --fv-table-w, which file-view.ts watchBodyWidth writes; with that width left to the tables' ResizeObserver, whose delivery comes
// after the body's in the same round, WebKit raised a window error, a loop of undelivered notifications, when the Files pane's
// Comments aside opened at 1400 by 800 beside a document of top-level tables, where 0ab74924c's viewer, a translate and no such
// observer, raised none. The stamp now writes each table's width with its cap. Red at the head before that write, green at
// 0ab74924c by design (no tables' observer there).
const WEB = "http://example.test";
const row = (n: number, cell: (i: number) => string): string => "| " + Array.from({ length: n }, (_, i) => cell(i)).join(" | ") + " |";
const table = (n: number, head: string, body: (i: number) => string): string => [row(n, (i) => head + " " + (i + 1)), "|" + Array.from({ length: n }, () => "---").join("|") + "|", row(n, body)].join("\n");
const TABLES = ["# Tables", "", PARA(1), "", table(2, "narrow", (i) => "cell " + i), "", PARA(2), "", table(7, "wide column", (i) => "wide cell " + i), "", PARA(3), "",
  table(18, "much wider column header", (i) => "a cell of the widest table " + i), "", PARA(4), "", table(4, "picture col", (i) => (i === 0 ? "![tp](" + WEB + "/tp.svg)" : "text " + i)), "", PARA(5), "",
  "| " + "unbreakable_" + "x".repeat(120) + " |", "|---|", "| y |", "", PARA(7), ""].join("\n");
test("in WebKit (Playwright's, on Linux), the Files pane at 1400 by 800 over a document of top-level tables, three opens: the Comments aside opening raises no window error, a loop of the ResizeObservers' notifications among them (red at the head before the stamp wrote each table's width with its cap; green at 0ab74924c by design)", { timeout: 300000 }, async (t) => {
  const seen: string[][] = [];
  let ran = false;
  await inBrowser(t, async (browser) => {
    ran = true;
    for (let rep = 0; rep < 3; rep++) {
      const before = async (pg: any): Promise<void> => { await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => route.fulfill({ status: 200, contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120"><rect width="640" height="120" fill="#6a3d9a"/></svg>' })); };
      const { page, errors } = await openViewer(browser, "pane", 1400, 800, { docs: { [REPORT]: TABLES }, before });
      try {
        for (let i = 0; i < 10 && await page.evaluate(() => !!document.querySelector('.fileview-md [data-act="fv-load"]')); i++) { await page.evaluate(() => { (document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement).click(); }); await frames(page, 3); }
        await frames(page, 8);
        assert.deepEqual(errors, [], "no window error before the aside opens (a precondition)");
        await openPanel(page);
        await frames(page, 8);
        seen.push(errors.slice());
      } finally { await page.close(); }
    }
  }, { engine: "webkit" });
  if (!ran) return;   // no browser: inBrowser skipped the case loudly
  t.diagnostic("record " + JSON.stringify(seen));
  assert.deepEqual(seen, [[], [], []], "the window errors each open raised as the aside opened, one list an open (a property pin over the page's error events)");
});

// The pictures in top-level tables loading (the file review's round 18, extra6-3). A remote picture under the 48 px floor inside a
// top-level table, loading beside several others, can be reported by the figures' ResizeObserver before its load event, and that
// report's decision dresses it with the outbound mark, whose margin grows the table inside the same delivery of the observers, the
// tables' observer having been handed the table's old size; WebKit then raised a window error, a loop of undelivered notifications.
// The figures' decision now runs at the next animation frame (file-view.ts watchFigureBoxes), so the table's new size is the next
// frame's first report. Each open loads every picture of the document through the gate on the chat modal, the Files pane and the
// feed modal, 24 opens a surface; red at ef686b029, where some opens on each surface raised it (the counts are the checklist's), and
// green at 0ab74924c by design, which had no tables' observer. The finding's first probe, wide pictures in the tables, is green at
// both heads: the trigger needs the small picture, decided at its report before its load.
const FIGS: Record<string, [number, number]> = { "/t1.svg": [300, 200], "/t2.svg": [20, 20], "/t3.svg": [640, 120], "/n1.svg": [40, 40] };
const fig = (name: string): string => '<img src="' + WEB + "/" + name + '.svg" alt="' + name + '">';
const FULL = ["# Figures", "", PARA(1), "",
  "<details><summary>The first fold</summary>", "", "![d1](" + WEB + "/d1.svg)", "", "</details>", "", PARA(2), "",
  "<details open><summary>The second fold</summary>", "", "![d2](" + WEB + "/d2.svg)", "", "</details>", "", PARA(3), "",
  "<details><summary>The third fold</summary>", "", PARA(4), "", "</details>", "", PARA(5), "",
  "<table><tr><td>" + fig("t1") + "</td><td>words beside the first picture</td></tr></table>", "", PARA(6), "",
  "<table><caption>A caption</caption><tr><td>" + fig("t2") + "</td><td>words beside the small picture</td></tr></table>", "", PARA(7), "",
  "<table><thead><tr><th>A head</th></tr></thead><tbody><tr><td>" + fig("t3") + "</td></tr></tbody></table>", "", PARA(8), "",
  "<div><table><tr><td>" + fig("n1") + "</td><td>a table inside a div</td></tr></table></div>", "", PARA(9), "",
  "> ![q1](" + WEB + "/q1.svg) quoted", "", "- ![l1](" + WEB + "/l1.svg) listed", "- the second item", "", PARA(10), "",
  "<figure>" + fig("f1") + "<figcaption>A figure's caption</figcaption></figure>", "", "<picture>" + fig("p1") + "</picture>", "", PARA(11), ""].join("\n");
test("in WebKit (Playwright's, on Linux), the chat modal, the Files pane and the feed modal at 900 by 700 over a document of remote pictures in top-level tables and beside them, one of 20 by 20 in a table, 24 opens a surface, every picture loaded through the gate: no open raises a window error, a loop of the ResizeObservers' notifications among them (the file review's round 18, extra6-3: red at ef686b029, whose figures' decision ran inside the observers' delivery; green at 0ab74924c by design)", { timeout: 900000 }, async (t) => {
  const seen: Record<string, string[][]> = {};
  let ran = false;
  await inBrowser(t, async (browser) => {
    ran = true;
    for (const surface of ["chat", "pane", "feed"] as const) {
      seen[surface] = [];
      for (let rep = 0; rep < 24; rep++) {
        const before = async (pg: any): Promise<void> => {
          await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
            const [w, h] = FIGS[new URL(route.request().url()).pathname] || [300, 160];
            return route.fulfill({ status: 200, contentType: "image/svg+xml", body: '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="#6a3d9a"/></svg>' });
          });
        };
        const { page, errors } = await openViewer(browser, surface, 900, 700, { docs: { [REPORT]: FULL }, before });
        try {
          for (let i = 0; i < 20 && await page.evaluate(() => !!document.querySelector('.fileview-md [data-act="fv-load"]')); i++) { await page.evaluate(() => { (document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement).click(); }); await frames(page, 3); }
          await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).length >= 10 && Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 15000 });
          await frames(page, 8);
          const small = await page.evaluate(() => { const i = document.querySelector('.fileview-md img[alt="t2"]') as HTMLImageElement | null; const tb = i && i.closest("table"); return !!i && !!tb && tb.parentElement!.classList.contains("fileview-md") && i.hasAttribute("data-fv-figweb"); });
          assert.ok(small, surface + ": the 20 by 20 picture stands in a top-level table and wears the outbound mark (a precondition)");
          seen[surface].push(errors.slice());
        } finally { await page.close(); }
      }
    }
  }, { engine: "webkit" });
  if (!ran) return;   // no browser: inBrowser skipped the case loudly
  const errored = Object.fromEntries(Object.entries(seen).map(([s, e]) => [s, e.filter((x) => x.length > 0).length]));
  t.diagnostic("record " + JSON.stringify({ errored, errors: [...new Set(Object.values(seen).flat(2))] }));
  assert.deepEqual(Object.values(seen).map((e) => e.length), [24, 24, 24], "24 opens a surface ran (a precondition)");
  assert.deepEqual(errored, { chat: 0, pane: 0, feed: 0 }, "the opens on each surface that raised a window error (a property pin over the page's error events)");
});
