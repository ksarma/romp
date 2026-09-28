// The one gate's tap cells, one set for every engine (the file review's round 17, tests-1 with regression-1, and the coordinator's
// decisions 1 to 3 on it; its round 18, extra5-1, extra5-2 and correctness-1, with the coordinator's decisions on them and the
// closing check after those fixes; and the closing check at 142ade155 after the fixes for the file review's round 18), for the
// link-navigation follow-on of plans/markdown-viewer.md: file-figure-open-browser.test.ts runs them in Chromium, and
// file-figure-open-engines-browser.test.ts in WebKit and Firefox, a leg of its own that stays off the shared roster of browser
// legs, since the job that runs the roster installs Chromium alone. The gate (file-view.ts webGestureShown and the recorder
// above it, keyed on thirteen events of the window's capture phase: pointerdown, mousedown, mouseup, pointerup, pointercancel,
// keydown, dragstart, touchend, touchcancel, pointerout, mouseout, blur and click) records a press's verdict at the window's
// pointerdown and fills a one-click slot at the pointerup, and a click by a pointer refuses where a record still stands under
// its own pointerId, a press whose pointerup the viewer never heard, and with none reads the press the slot handed it, only
// right after a primary mouseup whose detail is above 0 and only under the slot's own pointerId when the click is typed as the
// slot's pointerup was; a record ends at its own pointerup, which hands it to the slot, at its own pointercancel and at the
// next primary press, every record ends at a dragstart and at a mousedown with no pointerdown of a mouse or a pen before it,
// which empties the slot too unless it is the compatibility mousedown of the one-finger tap, or of the touch-order pen, whose
// pointerup filled the slot, a mouseup other than a primary one of detail above 0 empties the slot and clears the tap's flag,
// and so does a mouseout to no element while a tap's compatibility mousedown is due, a touchend or a touchcancel marks every
// touch record refused, and a mouse's or a pen's pointerout with a button down and no relatedTarget, its pointer leaving the
// viewer's window, marks every mouse and pen record refused, and so does the mouse's pointerout with no button down and no
// relatedTarget, a release the viewer did not hear, and the record stands; a blur of the viewer's window itself, the focus
// leaving its document, marks every mouse and pen record refused the same way and, while a tap's compatibility mousedown is
// due, empties the slot and clears the tap's flag (the file review's round 19, extra5-1, extra8-1 and extra8-2, with the
// coordinator's decisions on them). The engines differ in what a tap's click
// carries, read off the page as each cell's precondition:
// Chromium gives the click the touch's own pointerId and type, Firefox its press's (0, a mouse's and a touch's alike), and
// Playwright's headless WebKit on Linux (WPE's MiniBrowser) under touch emulation, a stand-in for WPE and WebKitGTK browsers on a
// touchscreen (the file review's round 19, extra7-4; no cell claims iOS Safari, whose click WebKit's iOS source gives the
// touch's own pointerId, read and not run on a device), pointerId 1 of type mouse while its press carried the touch's; in each the click finds its press in the slot, in Chromium and Firefox under the
// slot's own pointerId and type, and in WebKit under another type. The cells, on the chat modal and the Files pane at 900 by 700,
// on a phone's pages (hasTouch and isMobile at a device scale of 1 with the kernel's viewport meta, which WebKit's mobile layout
// needs: without it a tap on the control lands off target) and on a hybrid page (hasTouch with a mouse), Firefox on the hybrid
// page alone since its engine takes no isMobile, each a count of [popups, document requests] taken by the gate's own window.open
// calls (file-figure-open-stacking.ts opensCounter; the file review's round 18, extra6-2), the pictures from the web routed at
// the context and every value synthetic:
// - a tap on a loaded remote picture with its control in view and uncovered opens once, and so does a tap on the control, and a
//   tap on a remote picture under the floor that wears the mark and no control;
// - the control out of view: the first tap opens nothing and leaves the control in view, and the next tap opens once;
// - a double tap 90 ms apart on that picture: in Chromium its second click carries detail 2 and opens nothing, the second click of
//   a refused run; in Firefox and WebKit each tap's click carries detail 1, so the second tap is read at its own start, after the
//   first tap's reveal, and opens once (the coordinator's decision 1);
// - the covered sign: with the text-size flyout, or the Outline popover, over the control, a tap on the picture opens nothing and
//   closes what covered it, and the next tap opens once;
// - the stale records, on the hybrid page: a right press of the mouse on the picture with the control shown, or a mouse drag of the
//   picture, then the flyout opened over the control by a script's click on its button, with no press of the mouse, then a tap on
//   the picture: it opens nothing, the mouse's record having ended (the right press's at its own pointerup, the drag's at its
//   dragstart, and either at the tap's own primary press), so the tap's click reads its own press, and the next tap opens once;
// - the mouse's clicks after its drag of a picture, on the hybrid page and on a plain page (a mouse and no touchscreen): with the
//   control shown, a drag, then the flyout or the Outline popover opened over the control by a script's click, then a click of the
//   mouse on the picture opens nothing, and the next click opens once; and the cost cells, a drag, then a click of the mouse on the
//   same picture with its control shown and uncovered, or on another picture whose control is shown and uncovered: in WebKit the
//   first click opens nothing and the next opens once, and in Chromium and Firefox the first click opens once. Chromium and Firefox
//   end the drag's press with a pointercancel and send the next press's pointerdown; WebKit sends neither, and the next press
//   arrives as a mousedown with no pointerdown before it, each cell asserting its engine's shape as its precondition. The gate ends
//   every record at the drag's dragstart and at that mousedown, so WebKit's first click after the drag finds no press;
// - a drag in another pane, on the hybrid page and on a plain page: the dashboard's panes are same-origin frames, and a same-origin
//   frame put into the page, with a link dragged inside it, stands in for one, the viewer's window hearing nothing of the drag. A
//   right click on the picture with the control shown (F1, F2), or a press on the control released beside the picture (F3), then the
//   drag, then the text-size flyout over the control, opened by a script's click (F1, F3) or by Enter on its focused button (F2),
//   then a click of the mouse on the picture: it opens nothing, and the next click opens once; and the cost cells, no earlier press
//   (F5) or a right click (F6), then the drag, then a click with the control shown and uncovered: in WebKit the first click opens
//   nothing and the next opens once, and in Chromium and Firefox the first click opens once. WebKit keeps the button's pressed state
//   across the frames and sends the mouse's next press in the viewer as a mousedown with no pointerdown before it; Chromium and
//   Firefox end the frame's drag with a pointercancel and send that press's pointerdown;
// - Firefox's chord, on the hybrid page and on a plain page, in Firefox alone (Chromium and WebKit send no click after it): a left
//   press on the picture under the flyout or the Outline popover, each closed by that press, or begun with the control out of view
//   and the control then scrolled into view, then a middle or a right press chorded into it, whose mousedown comes with no
//   pointerdown of its own: the left press's click opens nothing, and the next click opens once, the mousedown's clear refusing
//   it; with the control shown the same chord opens nothing too, a cost of that clear in the three engines (the costs below);
// - a finger beside the mouse, in Chromium on the hybrid page (CDP touch): a finger held on the picture with the control shown, the
//   mouse's click beside it, the finger lifted, then the mouse's press on the picture with the control out of view or under the
//   flyout, a finger's swipe beside it while the mouse is held, and the release: its click opens nothing, with the finger's steps
//   before it or without them;
// - a tap on another document's element, on the hybrid page in the dashboard's shape (the viewer's page in a same-origin frame of a
//   top page, as the dashboard frames its chat, Files and feed panes): an element of the top page over the control and the picture
//   beside it, gone at its own pointerup, so the tap's press and release go to the top page and its compatibility mousedown, mouseup
//   and click land in the viewer's window with no pointerdown or pointerup, the mousedown, the trusted click and that absence a
//   precondition each cell asserts. After nothing, a right click or a middle click on the
//   picture with the control shown, and in Chromium a two-finger touch on it, the tap opens nothing and the next click of the mouse
//   opens once; so does the tap after a right click with the control above the top page's window at the tap's start, the frame
//   moved back at the element's pointerup; and in Firefox alone, a tap on a hover tooltip of the top page over the control, hidden
//   as the tap moves the mouse off its cell (Chromium and WebKit send that tap's mouse events to the tooltip);
// - the chain rule's cells (chainCells; the closing check at 142ade155 after the fixes for the file review's round 18), in the
//   dashboard's shape with the viewer's frame beside another pane's frame over a bar of the top page, each covered click wanted
//   opening nothing and the next click opening once: in Firefox, on the hybrid page, the lone click Firefox sends after another
//   document cancels a tap's pointerdown, after a right or a middle click, after the viewer's own tap whose compatibility events or
//   click went to another document, and after the mouse held on the control or pressed there and released on the top page's bar or
//   in the other pane; in Firefox and WebKit, another document's tap that cancels nothing, after the viewer's own tap whose
//   compatibility mousedown an element of the top page appearing at its pointerup took and hid at, so the viewer heard that tap's
//   mouseup of detail 0 and no click; in Chromium, on the hybrid page, another document's tap whose click carries another touch's
//   pointerId, after the viewer's own tap with a second finger resting on the bar or in the other pane, or with an element of the
//   top page appearing over the picture; in WebKit, on the hybrid page and on a phone's pages, another document's tap after the
//   viewer's own tap whose pointerup that document took, so the viewer heard its touchend and no pointerup, and the cost cell,
//   the viewer's own tap whose pointerup an element of the top page takes, which opens nothing and reveals the control, the
//   gate's cost, the same at 142ade155, and the next tap opens once; and in Firefox, on the hybrid page, and in WebKit, on the
//   hybrid page and on a phone's pages, another document's tap on an element over the control that hides at that tap's
//   compatibility mousedown, after a mouse's press whose pointerup the viewer never heard, in WebKit the mouse held on the
//   control or on the picture and in Firefox the mouse pressed on the control and released in the other pane, so the viewer hears
//   that tap's mouseup of detail 1 and its click alone, the click under the mouse's own pointerId in WebKit (1, typed mouse) and
//   under Firefox's 0 typed touch. The residual, an element of another document shown over the picture during the viewer's own
//   tap and then a tap on that element, has no cell (the closing check at 142ade155 measured the class's element shapes its
//   probe drove, Firefox 16 of 16 in the shape the mouseout's rule now closes, the element first hit at the compatibility
//   mousedown, WebKit 7 of 7, the residual, and Chromium 0 of 36 under a candidate of this gate with the slot's pointerId
//   test): in WebKit, and in Firefox where that element is laid out before the tap's compatibility mousemove and no mouse rests
//   in the viewer, each where no blur of the viewer's window comes while that tap's compatibility mousedown is due (the element
//   cancels that mousedown, the viewer's window did not hold the focus, the focus sat in a nested frame of the viewer's own
//   document, or, in WebKit, the element listens for no mouse event), no input or focus event the viewer hears tells it from
//   the viewer's own tap (where that tap's compatibility events start in the viewer, Firefox's mouseout to no element empties
//   the slot, the cells below, and where the viewer's window held the focus and the element takes the tap's mousedown without
//   cancelling it, the gate's blur rule empties it, measured in a probe kept out of the tree: Firefox's laid-out shape 0 of 36
//   where the gate without that rule opened 36 of 36, WebKit's shapes with an element that listens for the mouse 0 of 56 where
//   56 of 56 opened), and whether to accept it is the owner's decision; under the gate at ddb446fae the same check's probe read
//   Firefox 16 of 16, WebKit 7 of 7 and Chromium 0 of 51, and every other order of the class it drives opened nothing, and a
//   probe of the file review's round 19 under this gate's rules but the blur's read Firefox's laid-out shape with no mouse in
//   the viewer 12 of 12 with the element hidden at the covered tap's pointerup (0 of 12 hidden at its pointerdown) and the
//   shapes whose compatibility events start in the viewer 0 of 48, WebKit 24 of 24 with an element listening for no mouse event
//   and Chromium 0 of 16; a check of these fixes drove orders that probe does not and found two more of the class outside the
//   residual, open at 142ade155, at 1a6470e72 and at 09f58bec6 (file-view.ts's gate comment states them): the first, the cells
//   of a mouse's press whose pointerup the viewer never heard above, whose click read the mouse's record (WebKit 22 of 22,
//   Firefox 7 of 7), is closed by the gate's refusal of a record still standing at a click; the second, in Firefox, after that
//   release, a mouse click on such an element, whose pointerup handed the mouse's record to the slot and opened (10 of 10,
//   again at 343ee2eb5), is closed by the gate's refusal of a mouse's or a pen's record whose pointer left the viewer's window
//   with a button down (0 of 10 under this gate), its cells in Firefox, on the hybrid page, the element hiding at that click's
//   mousedown or its pointerdown, red at 343ee2eb5 and at 09f58bec6, with its cost cell; Chromium opened neither order. That
//   refusal costs one class of press: a press whose pointer left the viewer's window with a button down, by the events the
//   viewer heard, is refused once, its click opening nothing and revealing the control, and the next click opens. Its first
//   cost, the cost cell's, measured in Firefox: the viewer's own press on the control dragged out of its frame and back (8 of 8
//   in a probe of these fixes, where 343ee2eb5's gate opened all 8; Chromium and WebKit keep a held left press in the frame it
//   began in and opened it). Its second, measured in Chromium, found by a later check and with no cell: a press on the control
//   or the picture held while the top page hides the viewer's frame and shows it again, then released there, refused only when
//   the frame's next redraw came while it was hidden and opened otherwise (168 of 168 such presses refused and none of the 232
//   others in a later probe of these fixes that stamped that redraw, and all 11 of that check's own probe refused, where
//   343ee2eb5's gate opened all 11). The later check found a third order of the class outside the residual, open in WebKit and
//   in one shape in Chromium in the timings measured under this gate's rules but the blur's and, in WebKit, at 142ade155, at
//   09f58bec6 and at 343ee2eb5, which the gate's blur rule closes where the viewer's window held the focus and the element
//   takes that click's mousedown without cancelling it, what is left for the owner (file-view.ts's gate comment states it): the
//   mouse held on the control while the top page hides the viewer's frame and shows it again, then another document's mouse
//   click on an element over the control that hides at that click's mousedown or its pointerdown, whose pointerup hands the
//   held press's record to the slot (WebKit, which sends no pointerout there, opening it at every timing under this gate's
//   rules but the blur's, 3,700 of 3,700 in a later probe of these fixes and 60 of 60 in that check's probe, with no cell, and
//   under the blur's rule 0 of 3,700 where the viewer's window held the focus and the element does not cancel its mousedown and
//   3,700 of 3,700 where it does; Chromium, after such a release of a mouse or a pen, sending the mouse's pointerout with no
//   button down when a redraw finds the frame hidden or when a redraw or a pointer move comes between the element's appearing
//   and the click, which the gate reads as a release it did not hear, the cells below, 1,526 of 3,700 in the later probe under
//   the gate at ddb446fae and 0 of 3,700 under this gate's rules but the blur's, and opening it, in the timings measured, only
//   in its still shape, the frame shown again before any redraw finds it hidden, the pointer still and the click in the frame
//   the element appeared, 85 of 225 still clicks of a mouse and 64 of 180 of a pen with the frame shown at the release under
//   the gate without the blur's rule, with no cell, the blur's rule closing that shape where the viewer's window held the focus
//   and the element does not cancel its mousedown (0 of 225 where 72 of 225 opened without it, a pen's 0 of 30 where 18 of 30
//   opened), runs of several short hides with the pointer still not measured under these rules; and Firefox never, 0 of 2,600
//   on the Files pane and the chat). The chain rule's other costs, stated by reading, none measured, each a refusal that
//   reveals the control: on a Firefox touchscreen whose tap's click came typed touch under a pointerId other than its
//   pointerup's every tap, the tab then opening only from the mouse or the keyboard; every tap of a pen in the touch order
//   whose click comes typed mouse, as WebKit types a touch's click (WPE as measured, and WebKitGTK by analogy), the tab still
//   opening from a finger, the mouse or the keyboard; a tap during which another finger that touched the viewer lifts, in an
//   engine that clicks after such a tap; every tap in an engine whose touchend came before its pointerup (none of the three
//   measured); and a pointer's click with no primary mouseup of detail above 0 before it, an assistive technology's or an
//   eraser's, while Enter or Space on the control still opens, a pointer's click after whose pointerup a mouseup other than a
//   primary one of detail above 0 came, an order none of the three engines measured sends before a click, and a pointer's click
//   that finds a record still standing under its own pointerId, which no gesture of the viewer's own that the legs drive
//   leaves. The measured costs, each a refusal once that reveals the control, the next click opening: the refusal of a press
//   whose pointer left, its two above; the refusal of a standing record's, in WebKit alone, a left click chorded into a held
//   right press, whose pointerup WebKit holds until the last button's release, refused whatever covers or shows the control, 12
//   of 12 in the road probe, where 09f58bec6's gate opened all 12; the mousedown's clear's, in the three engines, a left click
//   with another mouse button held, the other pressed before it or during it (Chromium 16 of 16, Firefox 28 of 28, WebKit 12 of
//   12 and its chord of a left click into a held right press 4 of 4; the file review's round 19, extra7-1), WebKit's chord of a
//   left click into a held right press the one member the refusal of a standing record added; the two rules of the file
//   review's round 19 on input events, the leave's arm for no button and the mouseout's clear while a tap's mousedown is due,
//   none measured, no tap or chain cell of either leg and no own gesture of the probes changing under them; and the blur's
//   rule, one class of press: a focus move out of the viewer's window during the viewer's own press, or between a tap's
//   pointerup and its compatibility mousedown, whether the page, a peer frame, a nested frame of the viewer's own document,
//   another tab brought to the front or a modal dialog moves it, refuses that press once, measured in the three engines in a
//   probe kept out of the tree, no tap or chain cell of either leg changing under it (file-view.ts's gate comment states them);
// - the cells of a release the viewer did not hear and of a tap whose compatibility events went to another document (the file
//   review's round 19, extra5-1, extra8-1 and extra8-2), in chainCells's shape, each covered click wanted opening nothing and the
//   next click opening once: in Chromium, on the hybrid page's Files pane, a press on the control held while the top page hides the
//   viewer's frame, released at once on the top page, the frame shown again at once or 300 ms later, then another document's click on
//   an element over the control that hides at that click's mousedown, the mouse's click moved onto the control or a pen's still click
//   (CDP), each cell asserting that the viewer heard the mouse's pointerout with no relatedTarget and no button down before that
//   click; and in Firefox, on the hybrid page, the viewer's own tap on the picture with an element of the top page appearing over it
//   at the tap's pointerup, with no layout read and the mouse off the viewer, or laid out with a mouse resting in the viewer, then a
//   tap on that element over the control, each cell asserting the mouseout to no element Firefox sent the viewer after the tap's
//   pointerup, with a button down or with none;
// - the clicks by no pointer: Enter on the control in view opens once, and so does Enter after a refused tap; a press with no click
//   after it begun with the control out of view, the control then scrolled into view with no pointer or key event, then Enter on it
//   opens once; the same press begun with the control shown, the flyout then shown over the control with no event, then a script's
//   click on the picture opens nothing. In Chromium that press is a real two-finger touch; in Firefox and WebKit no input
//   Playwright drives leaves a pointerup with no click on a picture, so there a script's pointerdown and pointerup stand in, which
//   the recorder hears as it hears a press, and the cell's name says so.
// Red at 0ab74924c in WebKit: the taps (every cell but the key cells opening nothing), the double tap there, the stale records and
// the clicks after a drag, whose reads there are a private witness kept out of the tree; the tap cells of Chromium and Firefox read
// the same at that head as at the fix, by design. The key cells are green at both heads by design, red under a gate that reads a
// key's click as a pointer's (the Enter cells) and under one that lets a key's or a script's click read the slot with the keydown's
// clear dropped (the press cells). The covered drag cells are red under A18-R in WebKit, the gate with the rule the file review's
// round 18 found reverted and no clear put in its place, whose click read the drag's record; WebKit's cost cells after a drag are
// red at ef686b029, whose gate took a verdict at the mousedown with no pointerdown before it, as they record the cost and guard no
// defect; the other pane's covered cells are red in WebKit at X, the gate with a dragstart clear and records ended at no pointerup,
// whose click read the record the right click or the released press left; Firefox's chord cells and Chromium's cells of a finger
// beside the mouse are red at ef686b029 and under A18-M, that gate restored; the other-document cells after a right click, a middle
// click or a two-finger touch are red at 0f998a3b9 in the engines that run them, whose gate left the slot alone at the tap's
// mousedown, so the tap's click took the slot that pointerup with no click had filled, and the cell after nothing reads the same
// there, by design; the chain rule's cells are red at 142ade155, where each covered click opened, and on the chat and the Files
// pane under a gate without the rules that close each (in Firefox the tail and the mouseup's clear, for the lone click after the
// mouse held on the control the refusal of a record still standing at a click too, after the mouse released on the top page's bar
// the refusal of a record whose pointer left the viewer's window with a button down too, and after the mouse released in the other
// pane both refusals too, four cells a surface under a gate without the tail alone, those after the viewer's tap whose compatibility
// events or click went elsewhere; the slot's pointerId test in Chromium; the touch records' refusal in WebKit; for the cells of the
// mouseup that ended the chain, in Firefox and WebKit, the mouseup's clear, the gate at 1a6470e72 having none; for the cells of a
// mouse's press whose pointerup the viewer never heard, the refusal of a record still standing at a click in WebKit, and in Firefox
// both refusals, the gates at 1a6470e72 and at 09f58bec6 having neither; and for Firefox's cells of another document's mouse click
// after a press that left the viewer's frame, the refusal of a record whose pointer left, the gates at 343ee2eb5 and at 09f58bec6
// having none), while WebKit's cost cell reads the same there, by design, and Firefox's reads the press dragged out and back opening
// there, as at 343ee2eb5, recording its cost; Chromium's frame-hide cells are red at ddb446fae, whose gate read no pointerout
// with no button down, and under a gate without that arm and without the blur's rule, the pen's cell also under one whose arm
// marks the mouse's records alone and that reads no blur, and Firefox's cells of a tap whose compatibility events went to
// another document are red at ddb446fae, whose gate heard no mouseout, and under a gate without the mouseout listener and
// without the blur's rule, the cell with no button down also under one whose mouseout needs a button down and that reads no
// blur; the blur's rule refuses both sets of cells too, the viewer's window holding the focus in them and hearing a blur, both
// asserted, so they read the same under a gate without the arm or without the mouseout listener alone, while each set's shapes
// run again with an element that cancels its mousedown, where no blur comes (asserted), are red under a gate without the arm or
// without the mouseout listener alone, the pen's cell also under one whose arm marks the mouse's records alone and the cells
// with no button down also under one whose mouseout needs a button down, and so are the node guards' rows; the reads of each of
// these reds are a private witness kept out of the tree. file-view-outline.test.ts drives the same orders over the
// stand-in in CI, where these legs launch no browser.
import * as assert from "node:assert/strict";
import { openViewer, frames, pageHtml, PARA, REPORT, ORIGIN, SID } from "./real-viewer-leg";
import { RECORD_OPENS, opensCounter } from "./file-figure-open-stacking";

export type TapEngine = "chromium" | "firefox" | "webkit";
export type TapDevice = "phone" | "hybrid";
export type TapSurface = "chat" | "pane";
/** One cell's reading: its name, the wanted value and the value read. */
export type TapCell = [string, unknown, unknown];

const WEB = "http://example.test";
const SIZES: Record<string, [number, number]> = { "/tall.svg": [300, 1400], "/w490.svg": [490, 900], "/tiny.svg": [20, 20] };
const sized = (w: number, h: number, fill: string): string => '<svg xmlns="http://www.w3.org/2000/svg" width="' + w + '" height="' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + fill + '"/></svg>';
const paras = (from: number, n: number): string => Array.from({ length: n }, (_, i) => PARA(from + i)).join("\n\n");
/** A remote picture taller than the body, then a remote badge under the floor, which wears the mark and no control. */
const TALL_TEXT = "# Report\n\n" + PARA(1) + "\n\n![tall](" + WEB + "/tall.svg)\n\n" + paras(2, 8) + "\n\nA badge ![tiny](" + WEB + "/tiny.svg) in words.\n\n" + paras(10, 16) + "\n";
/** Two remote pictures above the floor, one after the other, each wearing its control in view at once. */
const TWO_TEXT = "# Report\n\n" + PARA(1) + "\n\n![first](" + WEB + "/first.svg)\n\n" + PARA(2) + "\n\n![second](" + WEB + "/second.svg)\n\n" + paras(3, 12) + "\n";
/** A remote picture 490 wide under three headings, so the Outline popover lists them and it and the text-size flyout can stand over its control. */
const COVER_TEXT = "# Report\n\n## Alpha\n\n" + PARA(1) + "\n\n![w490](" + WEB + "/w490.svg)\n\n## Beta\n\n" + paras(3, 12) + "\n\n## Gamma\n\n" + PARA(20) + "\n";

/** A browser whose pages are a phone's: hasTouch and isMobile at a device scale of 1 (hover none, a coarse pointer, touch events),
 *  the served page carrying the kernel pages' own viewport meta (`width=device-width, initial-scale=1`, which kernel.py writes on
 *  every dashboard page), so the layout viewport is the 900 px window at scale 1 and a screenshot pixel is a CSS pixel. The meta goes
 *  in after the page's `<meta charset=utf-8>`, and a page without that tag throws rather than open at the mobile default of a 980 px
 *  viewport scaled down. */
export function phonePages(browser: any): any {
  const META = '<meta name="viewport" content="width=device-width, initial-scale=1">';
  return {
    newPage: async (o: any) => {
      const pg = await browser.newPage({ ...o, hasTouch: true, isMobile: true, deviceScaleFactor: 1 });
      const route = pg.route.bind(pg);
      pg.route = (match: any, handler: any) => route(match, (r: any, req: any) => handler({
        request: () => r.request(),
        fulfill: (f: any) => {
          if (!(f && f.contentType === "text/html" && typeof f.body === "string")) return r.fulfill(f);
          assert.ok(f.body.includes("<meta charset=utf-8>"), "the served page carries <meta charset=utf-8>, after which the phone's viewport meta goes");
          return r.fulfill({ ...f, body: f.body.replace("<meta charset=utf-8>", "<meta charset=utf-8>" + META) });
        },
        continue: (...a: any[]) => r.continue(...a), fallback: (...a: any[]) => r.fallback(...a), abort: (...a: any[]) => r.abort(...a),
      }, req));
      return pg;
    },
  };
}
/** A browser whose pages have a touchscreen beside the mouse (hasTouch, no isMobile): the hybrid page. */
const hybridPages = (browser: any): any => ({ newPage: (o: any) => browser.newPage({ ...o, hasTouch: true }) });

/** In the viewer's document: the picture of an alt, its control, its sign (the control, else the picture wearing the mark), a window
 *  capture record of every pointerdown, mousedown, pointerup, pointercancel, dragstart and click (pointerId, pointerType, detail,
 *  trusted), `__tread` (whether the sign is in
 *  view in the body's padding box and the window or wholly outside the body, two points on the picture's visible part with what each
 *  hit-tests to, the control's centre and whether the picture wears the mark or a control) and `__tplace`, which puts the sign's top
 *  `dy` px below the body's padding top by the body's scrollTop, no pointer or key event. */
const INSTALL = (): void => {
  const w = window as any;
  w.__timg = (alt: string) => Array.from(document.querySelectorAll(".fileview-md img")).find((i) => i.getAttribute("alt") === alt) as HTMLElement;
  w.__tctl = (alt: string) => { const n = w.__timg(alt).nextElementSibling; return n && n.hasAttribute("data-fv-figopen") ? n as HTMLElement : null; };
  w.__tsign = (alt: string) => w.__tctl(alt) || (w.__timg(alt).hasAttribute("data-fv-figweb") ? w.__timg(alt) : null);
  w.__tev = [];
  for (const type of ["pointerdown", "mousedown", "pointerup", "pointercancel", "dragstart", "click"]) window.addEventListener(type, (e: any) => { w.__tev.push({ type: e.type, pid: e.pointerId, ptype: e.pointerType, detail: e.detail, trusted: e.isTrusted }); }, true);
  w.__tread = (alt: string) => {
    const s = w.__tsign(alt) as HTMLElement, img = w.__timg(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement;
    const sr = s.getBoundingClientRect(), ir = img.getBoundingClientRect(), br = b.getBoundingClientRect();
    const pl = br.left + b.clientLeft, pt = br.top + b.clientTop, pr = pl + b.clientWidth, pb = pt + b.clientHeight;
    const inView = sr.right > Math.max(pl, 0) && sr.left < Math.min(pr, innerWidth) && sr.bottom > Math.max(pt, 0) && sr.top < Math.min(pb, innerHeight);
    const top = Math.max(ir.top, pt), bottom = Math.min(ir.bottom, pb, innerHeight);
    const p1 = { x: Math.round(ir.left + Math.min(40, ir.width / 2)), y: Math.round(Math.max(top + 1, bottom - 30)) };
    const p2 = { x: Math.round(ir.left + Math.min(150, ir.width / 2)), y: Math.round(Math.min(top + 140, (top + bottom) / 2)) };
    const hit = (p: { x: number; y: number }) => { const e = document.elementFromPoint(p.x, p.y); return !e ? "null" : e === img ? "the picture" : s.contains(e) ? "the sign" : e.localName + (typeof e.className === "string" && e.className ? "." + e.className.trim().split(/\s+/).join(".") : ""); };
    const c = w.__tctl(alt) as HTMLElement | null, cr = c ? c.getBoundingClientRect() : null;
    return { inView, outside: sr.bottom <= pt || sr.top >= pb, pt: p1, pt2: p2, hit: hit(p1), hit2: hit(p2), ctl: cr ? { x: (cr.left + cr.right) / 2, y: (cr.top + cr.bottom) / 2 } : null, mark: img.hasAttribute("data-fv-figweb"), control: !!c };
  };
  w.__tplace = (alt: string, dy: number) => { const s = w.__tsign(alt) as HTMLElement, b = document.querySelector(".fileview-body") as HTMLElement; b.scrollTop += s.getBoundingClientRect().top - (b.getBoundingClientRect().top + b.clientTop) - dy; };
};
type Read = { inView: boolean; outside: boolean; pt: { x: number; y: number }; pt2: { x: number; y: number }; hit: string; hit2: string; ctl: { x: number; y: number } | null; mark: boolean; control: boolean };
type PtrEv = { type: string; pid: number; ptype: string; detail: number; trusted: boolean };
type Scene = {
  page: any;
  /** The opens since the last read, as [popups, document requests], counted by the gate's own window.open calls, each call's popup and
   *  request awaited with a failure bound (file-figure-open-stacking.ts opensCounter, whose scene end reads after the last cell). */
  opens: () => Promise<[number, number]>;
  read: (alt: string) => Promise<Read>;
  place: (alt: string, dy: number) => Promise<Read>;
  /** A finger's tap at a point, and the pointer events and clicks it sent at the window. */
  tap: (x: number, y: number) => Promise<PtrEv[]>;
  events: () => Promise<PtrEv[]>;
  /** A press with no click after it on the picture `alt` at two points: Chromium's real two-finger touch, else a script's pointerdown and pointerup. */
  pressNoClick: (alt: string, a: { x: number; y: number }, b: { x: number; y: number }) => Promise<string>;
  flyout: () => Promise<{ open: boolean; overCentre: boolean }>;
};
/** `text` open on the surface in a page of the device's, the remote pictures routed and loaded through the gate, the helpers
 *  installed, and `body` run with the scene; the page errors asserted empty after it. */
async function tapScene(browser: any, engine: TapEngine, device: TapDevice, surface: TapSurface, text: string, name: string, body: (s: Scene) => Promise<void>, mouseOnly = false): Promise<void> {
  const docReqs: string[] = [], popups: any[] = [];
  let wake = (): void => { /* no counter yet */ };
  const before = async (pg: any): Promise<void> => {
    await pg.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const req = route.request();
      if (req.resourceType() === "document") { docReqs.push(req.url()); wake(); return route.fulfill({ status: 200, contentType: "text/html", body: "<p>third party</p>" }); }
      const sz = SIZES[new URL(req.url()).pathname] || [300, 200];
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: sized(sz[0], sz[1], "#6a3d9a") });
    });
  };
  const host = mouseOnly ? browser : device === "phone" ? phonePages(browser) : hybridPages(browser);   // mouseOnly: a plain page, a mouse and no touchscreen
  const { page, errors } = await openViewer(host, surface, 900, 700, { docs: { [REPORT]: text }, before });
  try {
    for (let i = 0; i < 20 && await page.evaluate(() => !!document.querySelector('.fileview-md [data-act="fv-load"]')); i++) { await page.evaluate(() => { (document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement).click(); }); await frames(page, 3); }
    await page.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 15000 });
    await frames(page, 4);
    await page.evaluate(INSTALL);
    await page.evaluate(RECORD_OPENS);
    const counter = opensCounter(page, popups, docReqs, engine + ", " + (mouseOnly ? "a plain page" : device) + ", " + surface + ", the scene " + name);
    wake = counter.wake;
    page.context().on("page", (p: any) => { popups.push(p); wake(); });
    const cdp = engine === "chromium" ? await page.context().newCDPSession(page) : null;
    const read = (alt: string): Promise<Read> => page.evaluate((a: string) => (window as any).__tread(a), alt);
    const events = (): Promise<PtrEv[]> => page.evaluate(() => (window as any).__tev.splice(0));
    const scene: Scene = {
      page, read, events,
      opens: counter.opens,
      place: async (alt, dy) => { await page.evaluate(([a, d]: [string, number]) => (window as any).__tplace(a, d), [alt, dy]); await frames(page, 3); return read(alt); },
      tap: async (x, y) => { await events(); await page.touchscreen.tap(x, y); await frames(page, 2); return events(); },
      pressNoClick: async (alt, a, b) => {
        if (cdp) {
          await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a.x, y: a.y, id: 1 }] });
          await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a.x, y: a.y, id: 1 }, { x: b.x, y: b.y, id: 2 }] });
          await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
          await frames(page, 3);
          return "a two-finger touch";
        }
        await page.evaluate(([al, x, y]: [string, number, number]) => {
          const img = (window as any).__timg(al) as HTMLElement;
          const o = { bubbles: true, cancelable: true, composed: true, pointerId: 9, pointerType: "touch", isPrimary: true, clientX: x, clientY: y, button: 0 };
          img.dispatchEvent(new PointerEvent("pointerdown", o));
          img.dispatchEvent(new PointerEvent("pointerup", o));
        }, [alt, a.x, a.y]);
        await frames(page, 3);
        return "a script's pointerdown and pointerup, standing in";
      },
      flyout: () => page.evaluate(() => { const w = window as any; const c = w.__tctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); const m = document.querySelector(".fileview-zoom-menu") as HTMLElement; return { open: !m.hidden, overCentre: !!e && (!!e.closest(".fileview-zoom-menu") || !!e.closest(".fileview-size-reset")) }; }),
    };
    await body(scene);
    await counter.end();
  } finally {
    await page.close();
  }
  assert.deepEqual(errors, [], engine + ", " + (mouseOnly ? "a plain page" : device) + ", " + surface + ": no page errors");
}

/** Every cell for an engine on a device and a surface, run in `browser`, each reading returned beside its wanted value; `note`
 *  receives each scene's record. The preconditions are asserted as they are read. */
export async function tapCells(browser: any, engine: TapEngine, device: TapDevice, surface: TapSurface, note: (m: string) => void): Promise<TapCell[]> {
  const cells: TapCell[] = [];
  const cell = (what: string, want: unknown, got: unknown): void => { cells.push([what, want, got]); };
  /** The engine as a message names it: WebKit under touch emulation on a page with a touchscreen, and with none on a plain page. */
  const named = (touch: boolean): string => (engine === "webkit" ? "WebKit (Playwright's, on Linux" + (touch ? " under touch emulation" : "") + ")" : engine);
  const at = named(true) + ", " + (device === "phone" ? "a phone's pages" : "a hybrid page") + ", " + surface + ": ";
  const own = engine !== "webkit";   // Chromium's and Firefox's tap click carries its press's pointerId; WebKit's carries the mouse's
  /** The tap's shape, asserted as the cell's precondition: one pointerdown and one click, trusted, the click's pointerId its press's in
   *  Chromium and Firefox and another in WebKit (1, of type mouse, where the press carried the touch's). */
  const shape = (evs: PtrEv[], what: string): PtrEv => {
    const downs = evs.filter((e) => e.type === "pointerdown"), clicks = evs.filter((e) => e.type === "click");
    assert.ok(downs.length === 1 && clicks.length === 1 && clicks[0].trusted, at + what + ": the tap sends one pointerdown and one trusted click (a precondition): " + JSON.stringify(evs));
    if (own) assert.equal(clicks[0].pid, downs[0].pid, at + what + ": the tap's click carries its press's pointerId in " + engine + " (a precondition): " + JSON.stringify(evs));
    else assert.ok(clicks[0].pid !== downs[0].pid && clicks[0].ptype === "mouse" && downs[0].ptype === "touch", at + what + ": the tap's click carries a pointerId other than its press's in Playwright's WebKit on Linux under touch emulation, of type mouse where the press's is touch (a precondition): " + JSON.stringify(evs));
    return clicks[0];
  };
  await tapScene(browser, engine, device, surface, TALL_TEXT, "tall", async (s) => {
    const rec: Record<string, unknown> = {};
    const r = await s.place("tall", 120);
    rec.inView = r;
    assert.ok(r.inView && r.hit === "the picture" && r.ctl, at + "the control in view and the tap's point on the picture (a precondition): " + JSON.stringify(r));
    shape(await s.tap(r.pt.x, r.pt.y), "a tap on the picture");
    cell("a tap on the picture, its control in view: opens", [1, 1], await s.opens());
    const c = (await s.read("tall")).ctl!;
    shape(await s.tap(c.x, c.y), "a tap on the control");
    cell("a tap on the control: opens", [1, 1], await s.opens());
    const m = await s.place("tiny", 120);
    rec.mark = m;
    assert.ok(m.mark && !m.control && m.inView, at + "the badge under the floor wears the mark and no control, in view (a precondition): " + JSON.stringify(m));
    const mp = await s.page.evaluate(() => { const b = (window as any).__timg("tiny").getBoundingClientRect(); return { x: (b.left + b.right) / 2, y: (b.top + b.bottom) / 2 }; });
    shape(await s.tap(mp.x, mp.y), "a tap on the mark");
    cell("a tap on the picture that wears the mark: opens", [1, 1], await s.opens());
    const out = await s.place("tall", -60);
    rec.out = out;
    assert.ok(out.outside && out.hit === "the picture", at + "the control out of view above the body and the tap's point on the picture (a precondition): " + JSON.stringify(out));
    shape(await s.tap(out.pt.x, out.pt.y), "the first tap, the control out of view");
    const o1 = await s.opens();
    const after = await s.read("tall");
    cell("the control out of view: the first tap's opens, and the control in view after it", [[0, 0], true], [o1, after.inView]);
    assert.equal(after.hit2, "the picture", at + "the next tap's point, read after the reveal, on the picture (a precondition): " + JSON.stringify(after));
    const next = shape(await s.tap(after.pt2.x, after.pt2.y), "the next tap");
    assert.equal(next.detail, 1, at + "the next tap's click carries detail 1, a new run (a precondition)");
    cell("the control out of view: the next tap's opens", [1, 1], await s.opens());
    const out2 = await s.place("tall", -60);
    assert.ok(out2.outside && out2.hit === "the picture", at + "the control out of view again (a precondition): " + JSON.stringify(out2));
    await s.events();
    await s.page.touchscreen.tap(out2.pt.x, out2.pt.y);
    await new Promise((res) => setTimeout(res, 90));
    await s.page.touchscreen.tap(out2.pt.x, out2.pt.y);
    await frames(s.page, 2);
    const dbl = (await s.events()).filter((e) => e.type === "click").map((e) => e.detail);
    rec.doubleTap = dbl;
    assert.deepEqual(dbl, engine === "chromium" ? [1, 2] : [1, 1], at + "a double tap 90 ms apart: two clicks, of detail " + (engine === "chromium" ? "1 and 2 in Chromium" : "1 and 1 in " + engine) + " (a precondition)");
    cell("a double tap on the picture, its control out of view: opens (" + (engine === "chromium" ? "the second click, of detail 2, a later click of the refused run" : "the second tap's click of detail 1, read at its own start after the first tap's reveal") + ")", engine === "chromium" ? [0, 0] : [1, 1], await s.opens());
    await s.place("tall", 120);
    await s.page.evaluate(() => (window as any).__tctl("tall").focus());
    await s.page.keyboard.press("Enter");
    cell("Enter on the control in view: opens", [1, 1], await s.opens());
    const out3 = await s.place("tall", -60);
    assert.ok(out3.outside, at + "the control out of view for the press with no click (a precondition): " + JSON.stringify(out3));
    await s.events();
    const how = await s.pressNoClick("tall", out3.pt, out3.pt2);
    const pressEvs = await s.events();
    rec.k1 = { how, pressEvs };
    assert.ok(pressEvs.some((e) => e.type === "pointerup") && !pressEvs.some((e) => e.type === "click"), at + "the press sends a pointerup and no click (a precondition): " + JSON.stringify(pressEvs));
    const k1press = await s.opens();
    const back = await s.place("tall", 120);
    assert.ok(back.inView, at + "the control scrolled into view with no pointer or key event (a precondition)");
    await s.page.evaluate(() => (window as any).__tctl("tall").focus());
    await s.page.keyboard.press("Enter");
    cell("a press with no click begun with the control out of view (" + how + "), the control then in view, then Enter on it: [the press's opens, Enter's]", [[0, 0], [1, 1]], [k1press, await s.opens()]);
    note("record " + JSON.stringify({ engine, device, surface, scene: "tall", ...rec }));
  });
  await tapScene(browser, engine, device, surface, COVER_TEXT, "cover", async (s) => {
    const rec: Record<string, unknown> = {};
    const openFlyout = async (): Promise<void> => { await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-btn") as HTMLElement).click(); }); await frames(s.page, 3); };
    const covered = async (what: string, open: () => Promise<void>, dy: number, pre: () => Promise<{ open: boolean; overCentre: boolean }>, closed: () => Promise<boolean>): Promise<void> => {
      await s.place("w490", dy);
      await open();
      const p = await pre(), r = await s.read("w490");
      rec[what] = { ...p, read: r };
      assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + what + " open over the control's centre, the control in view, the tap's point on the picture (a precondition): " + JSON.stringify(rec[what]));
      shape(await s.tap(r.pt.x, r.pt.y), "a tap under " + what);
      cell(what + " over the control, then a tap on the picture: [the tap's opens, " + what + " closed after it]", [[0, 0], true], [await s.opens(), await closed()]);
      const r2 = await s.read("w490");
      shape(await s.tap(r2.pt2.x, r2.pt2.y), "the next tap after " + what);
      cell(what + " over the control, then the refused tap: the next tap's opens", [1, 1], await s.opens());
    };
    await covered("the text-size flyout", openFlyout, 3, s.flyout, () => s.page.evaluate(() => (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden));
    await covered("the Outline popover", async () => { await s.page.evaluate(() => { (document.querySelector(".fileview-outline-btn") as HTMLElement).click(); }); await frames(s.page, 3); }, 42,
      () => s.page.evaluate(() => { const w = window as any; const c = w.__tctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); return { open: !!document.querySelector(".fileview-outline"), overCentre: !!e && !!e.closest(".fileview-outline") }; }),
      () => s.page.evaluate(() => !document.querySelector(".fileview-outline")));
    await s.place("w490", 3);
    await openFlyout();
    const fr = await s.read("w490");
    assert.ok((await s.flyout()).overCentre && fr.hit === "the picture", at + "the flyout over the control before the refused tap (a precondition)");
    shape(await s.tap(fr.pt.x, fr.pt.y), "the refused tap before Enter");
    const refused = await s.opens();
    await s.page.evaluate(() => (window as any).__tctl("w490").focus());
    await s.page.keyboard.press("Enter");
    cell("a tap refused under the flyout, then Enter on the control: [the tap's opens, Enter's]", [[0, 0], [1, 1]], [refused, await s.opens()]);
    const k2 = await s.place("w490", 3);
    assert.ok(k2.inView && !(await s.flyout()).open && k2.hit === "the picture", at + "the control shown before the press with no click (a precondition): " + JSON.stringify(k2));
    await s.events();
    const how = await s.pressNoClick("w490", k2.pt, k2.pt2);
    const pressEvs = await s.events();
    rec.k2 = { how, pressEvs };
    const k2press = await s.opens();
    await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden = false; });
    await frames(s.page, 3);
    assert.ok((await s.flyout()).overCentre, at + "the flyout shown over the control with no event (a precondition)");
    await s.page.evaluate(() => (window as any).__timg("w490").click());
    cell("a press with no click begun with the control shown (" + how + "), the flyout then over the control, then a script's click on the picture: [the press's opens, the click's]", [[0, 0], [0, 0]], [k2press, await s.opens()]);
    await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden = true; });
    if (device === "hybrid") {
      const stale = async (what: string, press: (r: Read) => Promise<void>): Promise<void> => {
        const r0 = await s.place("w490", 3);
        assert.ok(r0.inView && !(await s.flyout()).open && r0.hit === "the picture", at + "the control shown before " + what + " (a precondition): " + JSON.stringify(r0));
        await s.events();
        await press(r0);
        await frames(s.page, 3);
        const pressEvs = await s.events();
        const pressOpens = await s.opens();
        await s.place("w490", 3);
        await openFlyout();
        const p = await s.flyout(), r = await s.read("w490");
        rec[what] = { pressEvs, pressOpens, flyout: p, read: r };
        assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + "after " + what + ", the flyout opened by a script's click over the control's centre, the tap's point on the picture (a precondition): " + JSON.stringify(rec[what]));
        shape(await s.tap(r.pt.x, r.pt.y), "the tap after " + what);
        cell(what + " with the control shown, then the flyout over the control, then a tap on the picture: [the press's opens, the tap's, the flyout closed after the tap]", [[0, 0], [0, 0], true], [pressOpens, await s.opens(), await s.page.evaluate(() => (document.querySelector(".fileview-zoom-menu") as HTMLElement).hidden)]);
        const r2 = await s.read("w490");
        shape(await s.tap(r2.pt2.x, r2.pt2.y), "the next tap after " + what);
        cell(what + ", then the flyout, then the refused tap: the next tap's opens", [1, 1], await s.opens());
      };
      await stale("a right press of the mouse on the picture", async (r) => { await s.page.mouse.move(r.pt.x, r.pt.y); await s.page.mouse.down({ button: "right" }); await s.page.mouse.up({ button: "right" }); });
      await stale("a mouse drag of the picture", async (r) => { await s.page.mouse.move(r.pt.x, r.pt.y); await s.page.mouse.down(); await s.page.mouse.move(r.pt.x + 40, r.pt.y - 40, { steps: 5 }); await s.page.mouse.move(850, 650, { steps: 10 }); await s.page.mouse.up(); });
    }
    note("record " + JSON.stringify({ engine, device, surface, scene: "cover", ...rec }));
  });
  if (device === "hybrid") for (const mouseOnly of [false, true]) {
    const on = named(!mouseOnly) + ", " + (mouseOnly ? "a plain page" : "a hybrid page") + ", " + surface + ": ";   // a plain page has no touchscreen, so no touch emulation in its messages (the file review's round 18, tests-3)
    await dragThenClick(browser, engine, surface, mouseOnly, on, cell, note);
    await otherPane(browser, engine, surface, mouseOnly, on, cell, note);
    if (engine === "firefox") await chordCells(browser, engine, surface, mouseOnly, on, cell, note);
  }
  if (engine === "chromium" && device === "hybrid") await touchBesideMouse(browser, surface, at, cell, note);
  if (device === "hybrid") await otherDocumentTap(browser, engine, surface, named(true) + ", a hybrid page in a frame, " + surface + ": ", cell, note);
  if (device === "hybrid" || engine === "webkit") await chainCells(browser, engine, device, surface, named(true) + ", " + (device === "phone" ? "a phone's pages" : "a hybrid page") + " in a frame beside another pane, " + surface + ": ", cell, note);
  return cells;
}

type CellFn = (what: string, want: unknown, got: unknown) => void;
/** The events a gesture sent at the window, one word each: type(pointerId,pointerType,detail). */
const fmt = (evs: PtrEv[]): string => evs.map((e) => e.type + "(" + e.pid + "," + e.ptype + "," + e.detail + ")").join(" ");
/** A click of the mouse at `p`, and the events it sent; `after` names the press's shape the engine sends: "own", its pointerdown
 *  and its mousedown, or "lost", the mousedown alone, as WebKit sends the mouse's next press after a press whose pointerup never
 *  came, asserted as the cell's precondition. */
async function mouseClickAt(s: Pick<Scene, "page" | "events">, p: { x: number; y: number }, after: "own" | "lost", what: string): Promise<PtrEv[]> {
  await s.events();
  await s.page.mouse.click(p.x, p.y);
  await frames(s.page, 2);
  const evs = await s.events();
  const downs = evs.filter((e) => e.type === "pointerdown").length, mdowns = evs.filter((e) => e.type === "mousedown").length;
  assert.ok(evs.some((e) => e.type === "click") && mdowns === 1 && downs === (after === "lost" ? 0 : 1), what + ": the click's press sends " + (after === "lost" ? "a mousedown and no pointerdown" : "its pointerdown and its mousedown") + " (a precondition): " + fmt(evs));
  return evs;
}
const outlineOver = (s: Scene): Promise<{ open: boolean; overCentre: boolean }> => s.page.evaluate(() => { const w = window as any; const c = w.__tctl("w490").getBoundingClientRect(); const e = document.elementFromPoint((c.left + c.right) / 2, (c.top + c.bottom) / 2); return { open: !!document.querySelector(".fileview-outline"), overCentre: !!e && !!e.closest(".fileview-outline") }; });
const openFlyoutBy = async (s: Scene, how: "script" | "key"): Promise<void> => {
  if (how === "script") await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-btn") as HTMLElement).click(); });
  else { await s.page.evaluate(() => { (document.querySelector(".fileview-zoom-btn") as HTMLElement).focus(); }); await s.page.keyboard.press("Enter"); }
  await frames(s.page, 3);
};
const openOutline = async (s: Scene): Promise<void> => { await s.page.evaluate(() => { (document.querySelector(".fileview-outline-btn") as HTMLElement).click(); }); await frames(s.page, 3); };
/** The flyout and the Outline popover closed, whichever stands. */
const closeCovers = async (s: Scene): Promise<void> => {
  await s.page.evaluate(() => { const m = document.querySelector(".fileview-zoom-menu") as HTMLElement | null; if (m && !m.hidden) (document.querySelector(".fileview-zoom-btn") as HTMLElement).click(); });
  await frames(s.page, 2);
  await s.page.evaluate(() => { if (document.querySelector(".fileview-outline")) (document.querySelector(".fileview-outline-btn") as HTMLElement).click(); });
  await frames(s.page, 2);
};

/** A mouse drag of a picture, then clicks of the mouse: on the hybrid page, and on a plain page (a mouse and no touchscreen). The
 *  drag ends in a dragstart and no click; in Chromium and Firefox it ends the press with a pointercancel and the next press sends its
 *  pointerdown, while WebKit sends neither, and sends the mouse's next press as a mousedown with no pointerdown before it, a
 *  precondition each cell asserts by engine. The gate (file-view.ts, the recorder above webGestureShown) ends every record at the
 *  drag's dragstart and at that mousedown, so in WebKit the mouse's first click after the drag finds no press and opens nothing,
 *  whatever covers or shows the control, and the click after it opens: the covered cells guard the closed direction, and the cells
 *  with the control shown record the cost, WebKit's first click refused where Chromium's and Firefox's open. */
async function dragThenClick(browser: any, engine: TapEngine, surface: TapSurface, mouseOnly: boolean, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  const on = mouseOnly ? " (a plain page)" : " (the hybrid page)";
  const lost = engine === "webkit";   // WebKit sends the mouse's next press after its drag with no pointerdown
  const drag = async (s: Scene, p: { x: number; y: number }): Promise<PtrEv[]> => {
    await s.events();
    await s.page.mouse.move(p.x, p.y); await s.page.mouse.down(); await s.page.mouse.move(p.x + 40, p.y - 40, { steps: 5 }); await s.page.mouse.move(850, 650, { steps: 10 }); await s.page.mouse.up();
    await frames(s.page, 3);
    const evs = await s.events();
    assert.ok(evs.some((e) => e.type === "dragstart") && !evs.some((e) => e.type === "click"), at + "the drag starts a drag and clicks nothing (a precondition): " + fmt(evs));
    if (engine === "webkit") assert.ok(!evs.some((e) => e.type === "pointerup" || e.type === "pointercancel"), at + "WebKit's drag of the picture ends with no pointerup and no pointercancel (a precondition): " + fmt(evs));
    else assert.ok(evs.some((e) => e.type === "pointercancel"), at + engine + "'s drag of the picture ends its press with a pointercancel (a precondition): " + fmt(evs));
    return evs;
  };
  /** The first click after a drag with the control shown and uncovered: WebKit's opens nothing, the stated cost, and Chromium's and Firefox's open once. */
  const shownWant = lost ? [0, 0] : [1, 1];
  await tapScene(browser, engine, "hybrid", surface, COVER_TEXT, "drag-cover", async (s) => {
    const rec: Record<string, unknown> = {};
    const covers: Array<[string, () => Promise<void>, number, () => Promise<{ open: boolean; overCentre: boolean }>]> = [
      ["the text-size flyout", () => openFlyoutBy(s, "script"), 3, s.flyout],
      ["the Outline popover", () => openOutline(s), 42, () => outlineOver(s)],
    ];
    for (const [what, open, dy, pre] of covers) {
      const r0 = await s.place("w490", dy);
      assert.ok(r0.inView && r0.hit === "the picture" && !(await pre()).open, at + "the control shown before the drag" + on + " (a precondition): " + JSON.stringify(r0));
      const dragEvs = await drag(s, r0.pt);
      const dragOpens = await s.opens();
      await s.place("w490", dy);
      await open();
      const p = await pre(), r = await s.read("w490");
      rec[what] = { dragEvs: fmt(dragEvs), flyout: p, read: r };
      assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + "after the drag" + on + ", " + what + " opened by a script's click over the control's centre, the click's point on the picture (a precondition): " + JSON.stringify(rec[what]));
      await mouseClickAt(s, r.pt, lost ? "lost" : "own", at + "the click under " + what + " after the drag");
      cell("a mouse drag of the picture with the control shown" + on + ", then " + what + " over the control, then a click of the mouse on the picture: [the drag's opens, the click's]", [[0, 0], [0, 0]], [dragOpens, await s.opens()]);
      const r2 = await s.read("w490");
      rec[what + " after"] = { cover: await pre(), read: r2 };
      assert.ok(!(await pre()).overCentre && r2.inView && r2.hit2 === "the picture", at + "after the refused click" + on + ", nothing over the control, in view, the next click's point on the picture (a precondition): " + JSON.stringify(rec[what + " after"]));
      await mouseClickAt(s, r2.pt2, "own", at + "the next click after " + what);
      cell("a mouse drag" + on + ", then " + what + ", then the refused click: the next click's opens", [1, 1], await s.opens());
    }
    const r0 = await s.place("w490", 3);
    assert.ok(r0.inView && r0.hit === "the picture" && !(await s.flyout()).open, at + "the control shown before the drag with no cover after it" + on + " (a precondition): " + JSON.stringify(r0));
    const dragEvs = await drag(s, r0.pt);
    const dragOpens = await s.opens();
    const r1 = await s.place("w490", 3);
    assert.ok(r1.inView && r1.hit === "the picture" && !(await s.flyout()).open, at + "after the drag" + on + ", the control shown and uncovered (a precondition): " + JSON.stringify(r1));
    await mouseClickAt(s, r1.pt, lost ? "lost" : "own", at + "the first click after the drag, the control shown");
    const first = await s.opens();
    const r2 = await s.read("w490");
    assert.ok(r2.inView && r2.hit2 === "the picture", at + "the next click's point on the picture" + on + " (a precondition): " + JSON.stringify(r2));
    await mouseClickAt(s, r2.pt2, "own", at + "the click after it");
    cell("a mouse drag of the picture with the control shown" + on + ", then a click of the mouse on the same picture, the control shown and uncovered, a stated cost in WebKit: [the drag's opens, the click's, the next click's]", [[0, 0], shownWant, [1, 1]], [dragOpens, first, await s.opens()]);
    note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "drag-cover", ...rec, shown: fmt(dragEvs) }));
  }, mouseOnly);
  await tapScene(browser, engine, "hybrid", surface, TWO_TEXT, "drag-other", async (s) => {
    const a = await s.place("first", 60);
    const b = await s.read("second");
    assert.ok(a.inView && a.hit === "the picture" && b.inView && b.hit === "the picture", at + "both pictures' controls in view, each point on its picture" + on + " (a precondition): " + JSON.stringify([a, b]));
    const dragEvs = await drag(s, a.pt);
    const dragOpens = await s.opens();
    const b2 = await s.read("second");
    const clickEvs = await mouseClickAt(s, b2.pt, lost ? "lost" : "own", at + "the click on the second picture");
    const first = await s.opens();
    const b3 = await s.read("second");
    assert.ok(b3.inView && b3.hit2 === "the picture", at + "the next click's point on the second picture" + on + " (a precondition): " + JSON.stringify(b3));
    await mouseClickAt(s, b3.pt2, "own", at + "the click after it");
    cell("a mouse drag of one picture" + on + ", then a click of the mouse on another whose control is shown and uncovered, a stated cost in WebKit: [the drag's opens, the click's, the next click's]", [[0, 0], shownWant, [1, 1]], [dragOpens, first, await s.opens()]);
    note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "drag-other", dragEvs: fmt(dragEvs), clickEvs: fmt(clickEvs) }));
  }, mouseOnly);
}

/** A drag in another pane, then clicks of the mouse in the viewer (the file review's round 18, with the coordinator's decisions on
 *  open item 1). The dashboard's chat, Files and feed panes are same-origin frames, and a drag in one sends the viewer's window
 *  nothing, so a same-origin frame put into the page, with a link dragged inside it, stands in for another pane. WebKit keeps the
 *  button's pressed state across the frames and sends the mouse's next press in the viewer as a mousedown with no pointerdown before
 *  it; Chromium and Firefox end the frame's drag with a pointercancel and send that press's pointerdown; each cell asserts its
 *  engine's shape as its precondition. Before the drag, with the control shown: a right click on the picture (F1, F2, F6), a press
 *  on the control released off it, beside the picture (F3), or nothing (F5); after it, the text-size flyout over the control, opened by a
 *  script's click (F1, F3) or by Enter on its focused button (F2), or no cover (F5, F6); then a click of the mouse on the picture,
 *  and the click after it. The covered cells refuse the first click in every engine; the uncovered ones record the cost, WebKit's
 *  first click refused where Chromium's and Firefox's open. */
async function otherPane(browser: any, engine: TapEngine, surface: TapSurface, mouseOnly: boolean, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  const on = mouseOnly ? " (a plain page)" : " (the hybrid page)";
  const lost = engine === "webkit";
  await tapScene(browser, engine, "hybrid", surface, COVER_TEXT, "other-pane", async (s) => {
    const rec: Record<string, unknown> = {};
    const frame = await s.page.evaluate(async () => {
      const f = document.createElement("iframe");
      f.id = "tpane";
      f.style.cssText = "position:fixed;left:" + (innerWidth - 170) + "px;top:" + (innerHeight - 150) + "px;width:160px;height:140px;z-index:2147483647;border:1px solid #888;background:#fff";
      f.srcdoc = "<!doctype html><html><body style='margin:0'><a id=l href='http://drag.invalid/pane' style='display:block;font:18px sans-serif;padding:10px'>a link to drag</a><p style='font:14px sans-serif;padding:6px'>another pane</p></body></html>";
      document.body.appendChild(f);
      await new Promise((r) => { const ok = () => f.contentDocument && f.contentDocument.getElementById("l"); if (ok()) r(null); else f.addEventListener("load", () => r(null), { once: true }); });
      const d = f.contentDocument!, w = f.contentWindow as any;
      d.addEventListener("dragover", (e) => e.preventDefault()); d.addEventListener("drop", (e) => e.preventDefault());
      w.__fev = [];
      for (const type of ["pointerdown", "mousedown", "pointerup", "pointercancel", "dragstart", "click"]) w.addEventListener(type, (e: any) => { w.__fev.push(e.type); }, true);
      const r = f.getBoundingClientRect(), lr = (d.getElementById("l") as HTMLElement).getBoundingClientRect();
      return { x: Math.round(r.left + lr.left + 40), y: Math.round(r.top + lr.top + lr.height / 2), fx: Math.round(r.left), fy: Math.round(r.top) };
    });
    const frameDrag = async (): Promise<{ viewer: PtrEv[]; frame: string[] }> => {
      await s.events();
      await s.page.evaluate(() => { ((document.getElementById("tpane") as HTMLIFrameElement).contentWindow as any).__fev = []; });
      await s.page.mouse.move(frame.x, frame.y); await s.page.mouse.down();
      await s.page.mouse.move(frame.x + 20, frame.y + 20, { steps: 5 }); await s.page.mouse.move(frame.fx + 130, frame.fy + 110, { steps: 8 }); await s.page.mouse.up();
      await frames(s.page, 3);
      const fe = await s.page.evaluate(() => ((document.getElementById("tpane") as HTMLIFrameElement).contentWindow as any).__fev.splice(0));
      return { viewer: await s.events(), frame: fe };
    };
    const rightClick = async (r0: Read): Promise<string> => { await s.events(); await s.page.mouse.click(r0.pt.x, r0.pt.y, { button: "right" }); await frames(s.page, 2); return fmt(await s.events()); };
    const pressOff = async (r0: Read): Promise<string> => {
      await s.events();
      const c = r0.ctl!, q = { x: Math.round(c.x + 150), y: Math.round(c.y + 120) };
      const there = await s.page.evaluate(([x, y]: [number, number]) => { const e = document.elementFromPoint(x, y); return !!e && !e.closest("img, [data-fv-figopen]"); }, [q.x, q.y]);
      assert.ok(there, at + "the release point beside the picture, off the picture and the control" + on + " (a precondition): " + JSON.stringify(q));
      await s.page.mouse.move(c.x, c.y); await s.page.mouse.down(); await s.page.mouse.move(q.x, q.y, { steps: 8 }); await s.page.mouse.up();
      await frames(s.page, 3);
      return fmt(await s.events());
    };
    const nothing = async (): Promise<string> => "none";
    const chains: Array<[string, string, (r0: Read) => Promise<string>, "script" | "key" | null]> = [
      ["F1", "a right click on the picture", rightClick, "script"],
      ["F2", "a right click on the picture", rightClick, "key"],
      ["F3", "a press on the control released beside the picture", pressOff, "script"],
      ["F5", "no earlier press", nothing, null],
      ["F6", "a right click on the picture", rightClick, null],
    ];
    for (const [id, before, step, cover] of chains) {
      await closeCovers(s);
      const r0 = await s.place("w490", 3);
      assert.ok(r0.inView && r0.hit === "the picture" && r0.ctl && !(await s.flyout()).open, at + id + ": the control shown before the steps" + on + " (a precondition): " + JSON.stringify(r0));
      const stepEvs = await step(r0);
      const stepOpens = await s.opens();
      const fd = await frameDrag();
      assert.ok(fd.viewer.length === 0 && fd.frame.includes("dragstart"), at + id + ": the drag in the other frame starts a drag there and sends the viewer's window nothing (a precondition): " + JSON.stringify({ viewer: fmt(fd.viewer), frame: fd.frame }));
      if (!lost) assert.ok(fd.frame.includes("pointercancel"), at + id + ": " + engine + " ends the other frame's drag with a pointercancel (a precondition): " + JSON.stringify(fd.frame));
      const dragOpens = await s.opens();
      await s.place("w490", 3);
      if (cover) await openFlyoutBy(s, cover);
      const p = await s.flyout(), r1 = await s.read("w490");
      rec[id] = { stepEvs, frame: fd.frame, flyout: p, read: r1 };
      assert.ok((cover ? p.open && p.overCentre : !p.open) && r1.inView && r1.hit === "the picture", at + id + ": " + (cover ? "the flyout over the control's centre" : "nothing over the control") + ", the click's point on the picture (a precondition): " + JSON.stringify(rec[id]));
      const c1 = await mouseClickAt(s, r1.pt, lost ? "lost" : "own", at + id + ": the first click after the drag in the other frame");
      const first = await s.opens();
      const r2 = await s.read("w490");
      assert.ok(!(await s.flyout()).overCentre && r2.inView && r2.hit2 === "the picture", at + id + ": nothing over the control before the next click, its point on the picture (a precondition): " + JSON.stringify(r2));
      await mouseClickAt(s, r2.pt2, "own", at + id + ": the next click");
      const next = await s.opens();
      (rec[id] as Record<string, unknown>).click = fmt(c1);
      cell(id + ": with the control shown, " + before + on + ", then a drag in another pane, then " + (cover ? "the text-size flyout over the control, opened by " + (cover === "script" ? "a script's click" : "Enter on its focused button") : "no cover, a stated cost in WebKit") + ", then a click of the mouse on the picture: [the step's opens, the drag's, the click's, the next click's]", [[0, 0], [0, 0], cover ? [0, 0] : lost ? [0, 0] : [1, 1], [1, 1]], [stepOpens, dragOpens, first, next]);
    }
    note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "other-pane", ...rec }));
  }, mouseOnly);
}

/** Firefox's chord (the file review's round 18, extra5-1): a left press on the picture, a middle or a right press chorded into it,
 *  then the chorded button's release and the left's. Firefox sends the chorded button's mousedown with no pointerdown of its own and
 *  then the left press's pointerup and click, a precondition each cell asserts (Chromium and WebKit send no click after such a chord,
 *  so the cells run in Firefox alone). Under the text-size flyout or the Outline popover over the control, each closed by the left
 *  press, and with the control out of view at the left press and scrolled into view by a script before the chord: the chord's click
 *  opens nothing, and the next click opens once. */
async function chordCells(browser: any, engine: TapEngine, surface: TapSurface, mouseOnly: boolean, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  const on = mouseOnly ? " (a plain page)" : " (the hybrid page)";
  const chord = async (s: Scene, p: { x: number; y: number }, button: "middle" | "right", between: () => Promise<void>): Promise<PtrEv[]> => {
    await s.events();
    await s.page.mouse.move(p.x, p.y); await s.page.mouse.down({ button: "left" });
    await between();
    await s.page.mouse.down({ button }); await s.page.mouse.up({ button }); await s.page.mouse.up({ button: "left" });
    await frames(s.page, 3);
    const evs = await s.events();
    const n = (t: string) => evs.filter((e) => e.type === t).length;
    assert.ok(n("pointerdown") === 1 && n("mousedown") === 2 && n("click") === 1, at + "Firefox's chord sends one pointerdown, two mousedowns and the left press's click (a precondition): " + fmt(evs));
    return evs;
  };
  const rec: Record<string, unknown> = {};
  await tapScene(browser, engine, "hybrid", surface, COVER_TEXT, "chord", async (s) => {
    const covers: Array<[string, () => Promise<void>, number, () => Promise<{ open: boolean; overCentre: boolean }>]> = [
      ["the text-size flyout", () => openFlyoutBy(s, "script"), 3, s.flyout],
      ["the Outline popover", () => openOutline(s), 42, () => outlineOver(s)],
    ];
    for (const [what, open, dy, pre] of covers) for (const button of ["middle", "right"] as const) {
      await closeCovers(s);
      await s.place("w490", dy);
      await open();
      const p = await pre(), r = await s.read("w490");
      assert.ok(p.open && p.overCentre && r.inView && r.hit === "the picture", at + what + " open over the control's centre, the press's point on the picture" + on + " (a precondition): " + JSON.stringify({ p, r }));
      const evs = await chord(s, r.pt, button, async () => {});
      const first = await s.opens();
      const r2 = await s.read("w490");
      assert.ok(!(await pre()).overCentre && r2.inView && r2.hit2 === "the picture", at + "after the chord, nothing over the control, its next point on the picture" + on + " (a precondition): " + JSON.stringify(r2));
      await mouseClickAt(s, r2.pt2, "own", at + "the click after the chord");
      rec[what + " " + button] = fmt(evs);
      cell(what + " over the control" + on + ", then a left press on the picture chorded by a " + button + " press: [the chord's click's opens, the next click's]", [[0, 0], [1, 1]], [first, await s.opens()]);
    }
  }, mouseOnly);
  await tapScene(browser, engine, "hybrid", surface, TALL_TEXT, "chord-out-of-view", async (s) => {
    for (const button of ["middle", "right"] as const) {
      const out = await s.place("tall", -60);
      assert.ok(out.outside && out.hit === "the picture", at + "the control out of view above the body, the press's point on the picture" + on + " (a precondition): " + JSON.stringify(out));
      const evs = await chord(s, out.pt, button, async () => { await s.page.evaluate(() => (window as any).__tplace("tall", 120)); await frames(s.page, 3); });
      const first = await s.opens();
      const r2 = await s.read("tall");
      assert.ok(r2.inView && r2.hit2 === "the picture", at + "after the chord, the control in view, its next point on the picture" + on + " (a precondition): " + JSON.stringify(r2));
      await mouseClickAt(s, r2.pt2, "own", at + "the click after the chord");
      rec["out of view " + button] = fmt(evs);
      cell("the control out of view at a left press on the picture" + on + ", the control then scrolled into view, then a " + button + " press chorded into it: [the chord's click's opens, the next click's]", [[0, 0], [1, 1]], [first, await s.opens()]);
    }
  }, mouseOnly);
  note("record " + JSON.stringify({ engine, surface, page: mouseOnly ? "plain" : "hybrid", scene: "chord", ...rec }));
}

/** Chromium's order on the hybrid page (the file review's round 18, extra5-2), a finger in CDP touch beside the mouse: a finger held
 *  on the picture with the control shown, the mouse's click on the body beside it, then the finger lifted (its compatibility
 *  mousedown and its click come after its pointerup); then the mouse's press on the picture with the control out of view, or under
 *  the text-size flyout, which its press closes, a finger's swipe beside the picture while the mouse is held (a touch's pointerdown
 *  and pointercancel, the swipe scrolling the control into view), then the mouse's release: its click opens nothing; and each of the
 *  two scenes with no finger and mouse click before it. */
async function touchBesideMouse(browser: any, surface: TapSurface, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  await tapScene(browser, "chromium", "hybrid", surface, COVER_TEXT, "touch-beside-mouse", async (s) => {
    const cdp = await s.page.context().newCDPSession(s.page);
    const rec: Record<string, unknown> = {};
    const beside = (): Promise<{ x: number; y: number }> => s.page.evaluate(() => { const w = window as any; const ir = w.__timg("w490").getBoundingClientRect(); return { x: Math.round(Math.min(ir.right + 80, innerWidth - 30)), y: Math.round(Math.max(ir.top, 80) + 60) }; });
    const touchEv = (type: string, pts: Array<{ x: number; y: number }>) => cdp.send("Input.dispatchTouchEvent", { type, touchPoints: pts.map((p, i) => ({ x: p.x, y: p.y, id: 7 + i })) });
    const heldFinger = async (): Promise<[number, number]> => {
      const r = await s.place("w490", 3), q = await beside();
      assert.ok(r.inView && r.hit === "the picture", at + "the control shown before the finger (a precondition): " + JSON.stringify(r));
      await s.events();
      await touchEv("touchStart", [r.pt]);
      await s.page.mouse.click(q.x, q.y);
      await touchEv("touchEnd", []);
      await frames(s.page, 3);
      const evs = await s.events();
      rec.finger = fmt(evs);
      assert.ok(evs.some((e) => e.type === "pointerup" && e.ptype === "touch") && evs.filter((e) => e.type === "mousedown").length === 2, at + "the finger's pointerup, then its compatibility mousedown after the mouse's (a precondition): " + fmt(evs));
      return s.opens();
    };
    const swipe = async (x: number, y0: number, dy: number): Promise<void> => {
      await touchEv("touchStart", [{ x, y: y0 }]);
      for (let i = 1; i <= 10; i++) { await touchEv("touchMove", [{ x, y: Math.round(y0 + (dy * i) / 10) }]); await frames(s.page, 1); }
      await touchEv("touchEnd", []);
      await frames(s.page, 4);
    };
    const press = async (covered: boolean): Promise<[number, number]> => {
      let p: { x: number; y: number };
      if (covered) {
        await s.place("w490", 3);
        await openFlyoutBy(s, "script");
        const fl = await s.flyout(), r = await s.read("w490");
        assert.ok(fl.open && fl.overCentre && r.hit === "the picture", at + "the flyout over the control's centre at the mouse's press (a precondition): " + JSON.stringify({ fl, r }));
        p = r.pt;
      } else {
        const out = await s.place("w490", -60);
        assert.ok(out.outside && out.hit === "the picture", at + "the control out of view at the mouse's press (a precondition): " + JSON.stringify(out));
        p = out.pt;
      }
      await s.events();
      await s.page.mouse.move(p.x, p.y); await s.page.mouse.down();
      const b = await beside();
      await swipe(b.x, covered ? 300 : 150, covered ? 40 : 260);
      await s.page.mouse.up();
      await frames(s.page, 3);
      const evs = await s.events();
      assert.ok(evs.some((e) => e.type === "pointercancel" && e.ptype === "touch") && evs.some((e) => e.type === "click" && e.ptype === "mouse"), at + "the swipe's touch ends in a pointercancel while the mouse is held, and the mouse's release clicks (a precondition): " + fmt(evs));
      if (!covered) assert.ok((await s.read("w490")).inView, at + "the swipe scrolled the control into view before the release (a precondition)");
      rec[(covered ? "covered" : "out of view")] = fmt(evs);
      const o = await s.opens();
      await closeCovers(s);
      return o;
    };
    for (const covered of [false, true]) {
      const where = covered ? "under the text-size flyout" : "with the control out of view";
      cell("the mouse's press on the picture " + where + ", a finger's swipe beside it while the mouse is held, the release: the click's opens", [0, 0], await press(covered));
      const fingerOpens = await heldFinger();
      cell("a finger held on the picture with the control shown, the mouse's click beside it, the finger lifted, then the mouse's press on the picture " + where + ", a swipe while it is held, the release: [the finger's opens, the click's]", [[0, 0], [0, 0]], [fingerOpens, await press(covered)]);
    }
    note("record " + JSON.stringify({ engine: "chromium", surface, scene: "touch-beside-mouse", ...rec }));
  });
}

/** The scene of a framed viewer: the top page, the viewer's frame, the frame's reads and the opens, and an element of the top document
 *  laid over the frame. */
type Framed = Pick<Scene, "opens" | "read" | "place" | "events"> & {
  page: any;
  fr: any;
  /** An element of the top document at `box` (top-page pixels), which at its own pointerup hides itself and, where `moveBack`, puts the
   *  viewer's frame back at the top page's top; what the top page hits at each of `pts`, true where the element. */
  cover: (box: { x: number; y: number; w: number; h: number }, pts: Array<{ x: number; y: number }>, moveBack?: boolean) => Promise<boolean[]>;
  /** The pointer and touch events the top document heard since the cover went up, and the cover's display now; the cover removed. */
  dropCover: () => Promise<{ events: string[]; display: string | null }>;
  /** The viewer's frame moved to `top` px in the top page. */
  frameTop: (top: number) => Promise<void>;
  /** The control's box in the viewer's frame, and the frame's top in the top page. */
  ctlBox: () => Promise<{ l: number; t: number; w: number; h: number; frameTop: number }>;
};
/** `text` open on the surface in the dashboard's shape: the viewer's page inside a same-origin frame of a top page (the dashboard's chat,
 *  Files and feed panes are same-origin frames), the frame at the top page's top left at 900 by 700, on the hybrid page (hasTouch with
 *  a mouse) or, with `opts.device` "phone", on a phone's pages (phonePages); with `opts.wide`, the top page 1300 by 700, another pane's
 *  same-origin frame beside the viewer's (at 900, 0, 400 by 600) and a bar of the top page under it (at 900, 600, 400 by 100), the
 *  shape the closing check at 142ade155 after the fixes for the file review's round 18 measured its roads in; the remote pictures
 *  routed and loaded through the gate, the helpers installed in the viewer's frame, the opens counted by the gate's own window.open
 *  calls there (opensCounter, reading the frame's record), and `body` run with the scene; the page errors asserted empty after it. */
async function framedScene(browser: any, engine: TapEngine, surface: TapSurface, text: string, name: string, body: (s: Framed) => Promise<void>, opts: { device?: TapDevice; wide?: boolean } = {}): Promise<void> {
  const docReqs: string[] = [], popups: any[] = [];
  let wake = (): void => { /* no counter yet */ };
  const device: TapDevice = opts.device || "hybrid";
  const on = (device === "phone" ? "a phone's pages" : "a hybrid page") + " in a frame" + (opts.wide ? " beside another pane" : "");
  const page = await (device === "phone" ? phonePages(browser) : hybridPages(browser)).newPage({ viewport: { width: opts.wide ? 1300 : 900, height: 700 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => { errors.push(e.message); });
  try {
    await page.context().route((u: URL) => u.href.startsWith(WEB + "/"), async (route: any) => {
      const req = route.request();
      if (req.resourceType() === "document") { docReqs.push(req.url()); wake(); return route.fulfill({ status: 200, contentType: "text/html", body: "<p>third party</p>" }); }
      const sz = SIZES[new URL(req.url()).pathname] || [300, 200];
      return route.fulfill({ status: 200, contentType: "image/svg+xml", body: sized(sz[0], sz[1], "#6a3d9a") });
    });
    const viewer = pageHtml(surface, { [REPORT]: text });
    const beside = opts.wide ? "<iframe id=tother src='/other' style='position:absolute;left:900px;top:0;width:400px;height:600px;border:0'></iframe><div id=tbar style='position:absolute;left:900px;top:600px;width:400px;height:100px;background:#dde'>a bar of the top page</div>" : "";
    const top = "<!doctype html><html><head><meta charset=utf-8></head><body style='margin:0'><iframe id=tview src='/viewer' style='position:absolute;left:0;top:0;width:900px;height:700px;border:0'></iframe>" + beside + "</body></html>";
    const other = "<!doctype html><html><head><meta charset=utf-8></head><body style='margin:0;font:16px sans-serif'><p style='padding:10px;height:500px;background:#eef'>another pane</p></body></html>";
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => { const at = new URL(route.request().url()).pathname; return route.fulfill({ status: 200, contentType: "text/html", body: at === "/viewer" ? viewer : at === "/other" ? other : top }); });
    await page.goto(ORIGIN + "/");
    await page.waitForFunction(() => { const f = document.getElementById("tview") as HTMLIFrameElement | null; return !!f && !!f.contentWindow && !!(f.contentWindow as any).FV; }, null, { timeout: 15000 });
    const fr = page.frames().find((f: any) => f.url() === ORIGIN + "/viewer");
    assert.ok(fr, engine + ", " + surface + ": the viewer's frame in the top page (a precondition)");
    await fr.evaluate(([p, sid]: [string, string]) => { (window as any).FV.openFileView(p, sid, null); }, [REPORT, SID]);
    await fr.waitForFunction(() => !!document.querySelector(".fileview-md > p"), null, { timeout: 10000 });
    for (let i = 0; i < 20 && await fr.evaluate(() => !!document.querySelector('.fileview-md [data-act="fv-load"]')); i++) { await fr.evaluate(() => { (document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement).click(); }); await frames(fr, 3); }
    await fr.waitForFunction(() => Array.from(document.querySelectorAll(".fileview-md img")).every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0), null, { timeout: 15000 });
    await frames(fr, 4);
    await fr.evaluate(INSTALL);
    await fr.evaluate(RECORD_OPENS);
    const counter = opensCounter({ evaluate: (f: any, a?: any) => fr.evaluate(f, a), bringToFront: () => page.bringToFront() }, popups, docReqs, engine + ", " + on + ", " + surface + ", the scene " + name);
    wake = counter.wake;
    page.context().on("page", (p: any) => { popups.push(p); wake(); });
    const read = (alt: string): Promise<Read> => fr.evaluate((a: string) => (window as any).__tread(a), alt);
    const scene: Framed = {
      page, fr, read,
      events: () => fr.evaluate(() => (window as any).__tev.splice(0)),
      opens: counter.opens,
      place: async (alt, dy) => { await fr.evaluate(([a, d]: [string, number]) => (window as any).__tplace(a, d), [alt, dy]); await frames(fr, 3); return read(alt); },
      cover: (box, pts, moveBack = false) => page.evaluate(([b, ps, back]: [{ x: number; y: number; w: number; h: number }, Array<{ x: number; y: number }>, boolean]) => {
        const w = window as any;
        const d = document.createElement("div");
        d.id = "tcover";
        d.style.cssText = "position:fixed;left:" + b.x + "px;top:" + b.y + "px;width:" + b.w + "px;height:" + b.h + "px;z-index:10;background:#eee;font:16px sans-serif";
        d.textContent = "a menu item of the top page";
        w.__cev = [];
        if (!w.__cevOn) { w.__cevOn = true; for (const type of ["pointerdown", "pointerup", "pointercancel", "touchstart", "touchend", "mousedown", "click"]) window.addEventListener(type, (e: any) => { w.__cev.push(e.type); }, true); }
        d.addEventListener("pointerup", () => { d.style.display = "none"; if (back) (document.getElementById("tview") as HTMLElement).style.top = "0px"; });
        document.body.appendChild(d);
        return ps.map((p) => document.elementFromPoint(p.x, p.y) === d);
      }, [box, pts, moveBack]),
      dropCover: () => page.evaluate(() => { const w = window as any; const d = document.getElementById("tcover"); const display = d ? getComputedStyle(d).display : null; if (d) d.remove(); const t = document.getElementById("ttip"); if (t) t.remove(); const c = document.getElementById("tcell"); if (c) c.remove(); return { events: (w.__cev || []).splice(0), display }; }),
      frameTop: async (y) => { await page.evaluate((v: number) => { (document.getElementById("tview") as HTMLElement).style.top = v + "px"; }, y); await frames(fr, 3); },
      ctlBox: () => fr.evaluate(() => { const c = (window as any).__tctl("w490").getBoundingClientRect(); const f = (window.frameElement as HTMLElement).getBoundingClientRect(); return { l: c.left, t: c.top, w: c.width, h: c.height, frameTop: f.top }; }),
    };
    await body(scene);
    await counter.end();
  } finally {
    await page.close();
  }
  assert.deepEqual(errors, [], engine + ", " + on + ", " + surface + ": no page errors");
}

/** A tap on another document's element over the picture that goes away during the press (the closing check after the fixes for the
 *  file review's round 18), in the dashboard's shape (framedScene): an element of the top document over the viewer's frame where the
 *  picture's control stands, a menu item or a backdrop of the top page, which hides itself at its own pointerup. The tap's press and
 *  release go to the top document, and its compatibility mousedown, mouseup and click, which the browser sends after that pointerup,
 *  hit-test into the viewer's frame, whose window hears them and no pointerdown or pointerup (in the three engines a road probe
 *  read a mousedown, a mouseup of detail 1 and a click there), the mousedown, the trusted click and that absence a precondition
 *  each cell asserts. Before the tap, with the control shown: nothing, a right click on the picture or a middle click on it (a pointerup of the
 *  viewer's window with no click after it), and in Chromium a two-finger touch on it (the same, CDP touch); the tap on the element
 *  over the picture beside the control, which covers the control at the tap's start: it opens nothing, and the next click of the
 *  mouse on the picture, the element gone, opens once. And the control out of view at the tap: after a right click with the control
 *  shown, the viewer's frame moved up until the control stands above the top page's window, a small element of the top page at the
 *  tap's point over the picture, which at its pointerup hides itself and moves the frame back, so the click lands on the picture with
 *  the control in view: it opens nothing, and the next click opens once. In Firefox alone, a hover tooltip of the top page over the
 *  control, shown while the mouse rests on a cell of the top page and hidden at that cell's mouseleave, after a right click with the
 *  control shown: a finger's tap on the tooltip moves the mouse off the cell before its compatibility mousedown, which lands in the
 *  viewer with its click (Chromium and WebKit send that tap's mouse events to the tooltip); it opens nothing, and the next click opens
 *  once. The gate empties the slot at a mousedown with no pointerdown of a mouse or a pen before it unless that mousedown is the
 *  compatibility mousedown of the one-finger tap, or of the touch-order pen, whose pointerup filled the slot, so after a pointerup
 *  of the viewer's with no click after it such a click finds no press. A click with no mousedown and no mouseup before it, as Firefox
 *  sends after another document cancels a tap's pointerdown, and a tap after the viewer's own tap whose compatibility events and
 *  click went elsewhere are chainCells's (the closing check at 142ade155 after the fixes for the file review's round 18). */
async function otherDocumentTap(browser: any, engine: TapEngine, surface: TapSurface, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  await framedScene(browser, engine, surface, COVER_TEXT, "other-document", async (s) => {
    const rec: Record<string, unknown> = {};
    /** No cover, the frame at the top page's top, and a click on the report's first paragraph, the body scrolled to its top: its
     *  primary press ends every record and empties the slot, and its pointerup fills the slot with nothing, before each cell. */
    const settle = async (): Promise<void> => {
      await s.dropCover();
      await s.frameTop(0);
      await s.fr.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 0; });
      await frames(s.fr, 3);
      const q = await s.fr.evaluate(() => { const p = document.querySelector(".fileview-md p") as HTMLElement; const r = p.getBoundingClientRect(); const x = Math.round(r.left + 20), y = Math.round(r.top + r.height / 2); const e = document.elementFromPoint(x, y); return e && p.contains(e) ? { x, y } : null; });
      assert.ok(q, at + "the first paragraph's point in view for the settling click (a precondition)");
      await mouseClickAt(s, q!, "own", at + "the settling click on the first paragraph");
      await s.opens();
    };
    const button = (b: "right" | "middle") => async (r: Read): Promise<PtrEv[]> => { await s.events(); await s.page.mouse.click(r.pt.x, r.pt.y, { button: b }); await frames(s.fr, 2); return s.events(); };
    const twoFinger = async (r: Read): Promise<PtrEv[]> => {
      await s.events();
      const cdp = await s.page.context().newCDPSession(s.page);
      await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: r.pt.x, y: r.pt.y, id: 1 }] });
      await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: r.pt.x, y: r.pt.y, id: 1 }, { x: r.pt2.x, y: r.pt2.y, id: 2 }] });
      await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      await frames(s.fr, 3);
      await cdp.detach();
      return s.events();
    };
    const leftovers: Array<[string, string, ((r: Read) => Promise<PtrEv[]>) | null]> = [["nothing before it", "", null], ["a right click on the picture", "the right click's", button("right")], ["a middle click on the picture", "the middle click's", button("middle")]];
    if (engine === "chromium") leftovers.push(["a two-finger touch on the picture", "the two-finger touch's", twoFinger]);
    /** The leftover's events, asserted: a pointerup of the viewer's window and no click after it. */
    const leftover = async (before: string, step: ((r: Read) => Promise<PtrEv[]>) | null, r0: Read): Promise<[number, number]> => {
      if (step) {
        const evs = await step(r0);
        assert.ok(evs.some((e) => e.type === "pointerup") && !evs.some((e) => e.type === "click"), at + before + " with the control shown sends the viewer's window a pointerup and no click (a precondition): " + fmt(evs));
        rec[before] = fmt(evs);
      }
      return s.opens();
    };
    /** The tap's events in the viewer's window, asserted: a mousedown and a trusted click, and no pointerdown or pointerup. */
    const foreign = (evs: PtrEv[], what: string): void => {
      const n = (t: string) => evs.filter((e) => e.type === t).length;
      assert.ok(n("pointerdown") === 0 && n("pointerup") === 0 && n("mousedown") === 1 && n("click") === 1 && evs.some((e) => e.type === "click" && e.trusted), at + what + ": the viewer's window hears the tap's mousedown and its trusted click and no pointerdown or pointerup (a precondition): " + fmt(evs));
    };
    const next = async (what: string): Promise<[number, number]> => {
      const r2 = await s.read("w490");
      assert.ok(r2.inView && r2.hit2 === "the picture", at + what + ": the control in view and the next click's point on the picture (a precondition): " + JSON.stringify(r2));
      await mouseClickAt(s, r2.pt2, "own", at + what + ": the next click");
      return s.opens();
    };
    for (const [before, its, step] of leftovers) {
      await settle();
      const r0 = await s.place("w490", 3);
      assert.ok(r0.inView && r0.hit === "the picture" && r0.ctl, at + before + ": the control shown, the point on the picture (a precondition): " + JSON.stringify(r0));
      const stepOpens = await leftover(before, step, r0);
      await s.place("w490", 3);
      const c = await s.ctlBox();
      const tapAt = { x: Math.round(c.l - 50), y: Math.round(c.t + c.h / 2 + 30) };
      const over = await s.cover({ x: Math.round(c.l - 120), y: Math.round(c.t - 10), w: Math.round(c.w + 140), h: Math.round(c.h + 90) }, [{ x: c.l + c.w / 2, y: c.t + c.h / 2 }, tapAt]);
      const hit = await s.fr.evaluate(([x, y]: [number, number]) => document.elementFromPoint(x, y) === (window as any).__timg("w490"), [tapAt.x, tapAt.y]);
      assert.ok(over[0] && over[1] && hit, at + before + ": the top page's element over the control's centre and over the tap's point, which in the viewer is on the picture (a precondition): " + JSON.stringify({ over, hit, c, tapAt }));
      await s.events();
      await s.page.touchscreen.tap(tapAt.x, tapAt.y);
      await frames(s.fr, 3);
      const evs = await s.events();
      const top = await s.dropCover();
      rec[before + " tap"] = { viewer: fmt(evs), top };
      foreign(evs, before);
      assert.ok(top.events.includes("pointerdown") && top.events.includes("pointerup") && top.display === "none", at + before + ": the tap's press and release went to the top page's element, hidden at its pointerup (a precondition): " + JSON.stringify(top));
      const tapOpens = await s.opens();
      cell("a tap on another document's element over the control, gone at its pointerup, " + (step ? "after " + before + " with the control shown: [" + its + " opens, the tap's, the next click's]" : "with " + before + ", the control shown: [the tap's opens, the next click's]"), step ? [[0, 0], [0, 0], [1, 1]] : [[0, 0], [1, 1]], step ? [stepOpens, tapOpens, await next(before)] : [tapOpens, await next(before)]);
    }
    {
      const what = "the control out of view at the tap";
      await settle();
      const r0 = await s.place("w490", 3);
      assert.ok(r0.inView && r0.hit === "the picture", at + what + ": the control shown before the right click (a precondition): " + JSON.stringify(r0));
      const stepOpens = await leftover("a right click on the picture (" + what + ")", button("right"), r0);
      const r1 = await s.place("w490", 3);
      const SHIFT = 90;
      await s.frameTop(-SHIFT);
      const c = await s.ctlBox();
      const tapAt = { x: r1.pt.x, y: r1.pt.y - SHIFT };
      const over = await s.cover({ x: tapAt.x - 40, y: tapAt.y - 30, w: 80, h: 60 }, [tapAt], true);
      assert.ok(c.frameTop + c.t + c.h <= 0 && over[0], at + what + ": the control above the top page's window at the tap's start, the top page's element at the tap's point (a precondition): " + JSON.stringify({ c, over, tapAt }));
      await s.events();
      await s.page.touchscreen.tap(tapAt.x, tapAt.y);
      await frames(s.fr, 3);
      const evs = await s.events();
      const top = await s.dropCover();
      const back = await s.ctlBox();
      rec[what] = { viewer: fmt(evs), top, back };
      foreign(evs, what);
      assert.ok(back.frameTop === 0 && top.display === "none", at + what + ": the element hidden and the frame moved back at its pointerup, the control in view at the click (a precondition): " + JSON.stringify({ top, back }));
      const tapOpens = await s.opens();
      cell("a tap on another document's element over the picture, the control above the top page's window at the tap's start and the frame moved back at the element's pointerup, after a right click with the control shown: [the right click's opens, the tap's, the next click's]", [[0, 0], [0, 0], [1, 1]], [stepOpens, tapOpens, await next(what)]);
    }
    if (engine === "firefox") {
      const what = "a hover tooltip of the top page";
      await settle();
      const r0 = await s.place("w490", 3);
      assert.ok(r0.inView && r0.hit === "the picture", at + what + ": the control shown before the right click (a precondition): " + JSON.stringify(r0));
      const stepOpens = await leftover("a right click on the picture (" + what + ")", button("right"), r0);
      await s.place("w490", 3);
      const c = await s.ctlBox();
      const tapAt = { x: Math.round(c.l - 50), y: Math.round(c.t + c.h / 2 + 30) };
      await s.page.evaluate((b: { x: number; y: number; w: number; h: number }) => {
        const w = window as any;
        const cellEl = document.createElement("div"), tip = document.createElement("div");
        cellEl.id = "tcell"; tip.id = "ttip";
        cellEl.style.cssText = "position:fixed;left:20px;bottom:10px;width:120px;height:30px;z-index:10;background:#ccd;font:13px sans-serif";
        cellEl.textContent = "a rail cell";
        tip.style.cssText = "position:fixed;left:" + b.x + "px;top:" + b.y + "px;width:" + b.w + "px;height:" + b.h + "px;z-index:11;background:#ffd;font:13px sans-serif;display:none";
        tip.textContent = "a hover tooltip of the top page";
        cellEl.addEventListener("mouseenter", () => { tip.style.display = "block"; });
        cellEl.addEventListener("mouseleave", () => { tip.style.display = "none"; });
        w.__cev = [];
        if (!w.__cevOn) { w.__cevOn = true; for (const type of ["pointerdown", "pointerup", "pointercancel", "touchstart", "touchend", "mousedown", "click"]) window.addEventListener(type, (e: any) => { w.__cev.push(e.type); }, true); }
        document.body.appendChild(cellEl); document.body.appendChild(tip);
      }, { x: Math.round(c.l - 120), y: Math.round(c.t - 10), w: Math.round(c.w + 140), h: Math.round(c.h + 90) });
      await s.page.mouse.move(80, 675, { steps: 4 });
      await frames(s.fr, 2);
      const shown = await s.page.evaluate(([cx, cy, tx, ty]: [number, number, number, number]) => { const t = document.getElementById("ttip"); return !!t && document.elementFromPoint(cx, cy) === t && document.elementFromPoint(tx, ty) === t; }, [c.l + c.w / 2, c.t + c.h / 2, tapAt.x, tapAt.y]);
      assert.ok(shown, at + what + ": the tooltip shown over the control's centre and the tap's point while the mouse rests on the cell (a precondition)");
      await s.events();
      await s.page.touchscreen.tap(tapAt.x, tapAt.y);
      await frames(s.fr, 3);
      const evs = await s.events();
      const hidden = await s.page.evaluate(() => getComputedStyle(document.getElementById("ttip") as HTMLElement).display);
      const top = await s.dropCover();
      rec[what] = { viewer: fmt(evs), top, hidden };
      foreign(evs, what);
      assert.ok(hidden === "none", at + what + ": the tooltip hidden at the cell's mouseleave by the tap (a precondition): " + hidden);
      const tapOpens = await s.opens();
      cell("a finger's tap on a hover tooltip of the top page over the control, hidden as the tap moves the mouse off its cell, after a right click with the control shown: [the right click's opens, the tap's, the next click's]", [[0, 0], [0, 0], [1, 1]], [stepOpens, tapOpens, await next(what)]);
    }
    note("record " + JSON.stringify({ engine, surface, page: "hybrid in a frame", scene: "other-document", ...rec }));
  });
}

/** The chain rule's cells (the closing check at 142ade155 after the fixes for the file review's round 18): a verdict moves from a press
 *  to a click only along that gesture's own chain of events as the viewer's window hears them, the last link before a pointer's click
 *  a primary mouseup of detail above 0. Each cell is one of the check's roads in the shape it was measured in (framedScene's wide
 *  layout: the viewer's frame, another pane's frame beside it and a bar of the top page under that pane), its engine's order asserted
 *  as the cell's precondition from a window capture record of the viewer's pointer, mouse and touch events, and read as the opens of
 *  each step, of the covered click and of the next click, each wanted at [0, 0] but the next click's, [1, 1]. The road's element is an
 *  element of the top page over the control and over the point of the tap, which covers the control at the tap's start.
 *  - In Firefox, on the hybrid page: another document cancels the tap's pointerdown, and Firefox sends that tap's click alone into the
 *    viewer, with no mousedown and no mouseup before it (the lone click). Before it, a right click or a middle click on the picture
 *    with the control shown, the element cancelling its pointerdown and hiding at its pointerup, or hiding at its pointerdown, or taking
 *    pointer-events none at its pointerdown; the viewer's own tap on the picture during which the element appears at its pointerup or
 *    its pointerdown, cancelling its own pointerdown, so the viewer's tap sends its compatibility events and click there; that tap
 *    whose compatibility mousedown lands in the viewer and an element appearing at it takes its mouseup and click, or hides at its
 *    click; that tap whose compatibility mousedown an element appearing at the tap's pointerup takes and hides at, so the mouseup, of
 *    detail 0, lands in the viewer and no click follows; the mouse held on the control, released after the lone click; and the mouse
 *    pressed on the control and dragged out of the viewer's frame, released on the top page's bar (the viewer hears the pointerup and a
 *    mouseup of detail 0 and no click) or in the other pane (the viewer hears no release).
 *  - In Firefox, on the hybrid page, and in WebKit, on the hybrid page and on a phone's pages: the mouseup that ends the chain. The
 *    viewer's own tap on the picture whose compatibility mousedown an element appearing at its pointerup takes and hides at, so the
 *    viewer hears the tap's pointerdown, pointerup and touchend and then its mouseup of detail 0 and no click; another document's tap
 *    on an element over the control that hides at its own pointerup and cancels nothing then sends the viewer its compatibility
 *    mousedown, a mouseup of detail 1 and a click, under pointerId 0 typed touch in Firefox and pointerId 1 typed mouse in WebKit. Red
 *    at 142ade155 and at 1a6470e72, whose tap's flag kept the slot at that mousedown, so the click took it.
 *  - In Chromium, on the hybrid page: Chromium gives each touch a pointerId of its own and a tap's click the touch's own, so the viewer's
 *    own tap on the picture with a second finger resting on the top page's bar or in the other pane (CDP touch; Chromium sends no click
 *    after a two-finger touch), or with an element appearing over the picture at its pointerdown or its pointerup (hiding at its own
 *    pointerup or pointerdown, or cancelling its pointerdown), or whose compatibility mousedown an element takes and hides at, fills the
 *    slot under its pointerId; another document's tap then sends the viewer its compatibility mousedown, mouseup and click alone, the
 *    click under another touch's pointerId.
 *  - In WebKit (Playwright's, on Linux under touch emulation), on the hybrid page and on a phone's pages: WebKit gives every touch
 *    pointerId 2 and sends a tap's pointerup to the element the release hits, so the viewer's own tap on the picture with an element
 *    appearing at its pointerdown that hides at its own pointerdown reaches the viewer as a pointerdown, a touchstart and a touchend
 *    with no pointerup; another document's tap on that element then sends the viewer a pointerup under pointerId 2, a compatibility
 *    mousedown, a mouseup and a click under pointerId 1 of type mouse. And the cost cell: the element appearing at the viewer's pointerdown and hiding at its own pointerup, which the tap's pointerup hits,
 *    so the viewer hears the tap's pointerdown, touchend, compatibility mousedown, mouseup and click and no pointerup: that tap opens
 *    nothing and reveals the control, at 142ade155 as at the fix, a stated cost, and the next tap opens once.
 *  - In Firefox, on the hybrid page, and in WebKit, on the hybrid page and on a phone's pages: a mouse's press whose pointerup the
 *    viewer never hears, in WebKit the mouse held on the control or on the picture with the control shown, and in Firefox the mouse
 *    pressed on the control and released in the other pane, so the viewer hears the press's pointerdown and mousedown and no
 *    pointerup; another document's tap on an element over the control that hides at that tap's compatibility mousedown then sends the
 *    viewer that tap's mouseup of detail 1 and its click alone, WebKit's click under pointerId 1 typed mouse, the held mouse's own,
 *    and Firefox's under pointerId 0 typed touch. The mouse's record still stands at that click, which refuses; in WebKit the held
 *    mouse is then released on the top page's bar. Red at 142ade155, at 1a6470e72 and at 09f58bec6, whose click read the mouse's
 *    record and opened.
 *  - In Firefox, on the hybrid page: the mouse pressed on the control and released in the other pane, its pointer leaving the
 *    viewer's frame with the button down, so the viewer hears a pointerout with no relatedTarget and buttons 1 as it leaves; then
 *    another document's mouse click on an element over the control that hides at that click's mousedown, or at its pointerdown,
 *    reaches the viewer as a pointerup, a mouseup of detail 1 and a trusted click under pointerId 0 typed mouse. The mouse's
 *    record, marked refused at that pointerout, goes to the slot at that pointerup, and the click refuses. Red at 343ee2eb5 and at
 *    09f58bec6, whose pointerup handed the slot the mouse's shown record, so the click opened. And its cost cell: the viewer's own
 *    press on the control dragged out into the other pane and back, released on the control, whose click opens nothing and reveals
 *    the control, and the next click opens once, where 343ee2eb5's gate opened that click.
 *  Red at 142ade155, where each covered click opened, and Firefox's cost cell there reads the press dragged out and back opening, as
 *  at 1a6470e72, at 09f58bec6 and at 343ee2eb5, recording the cost, while WebKit's cost cell alone reads the same there, by design;
 *  and on the chat and the Files pane under a gate without
 *  the rules that close each; the reads of the reds are a private witness kept out of the tree.
 *  file-view-outline.test.ts drives the same orders over the stand-in in CI. */
async function chainCells(browser: any, engine: TapEngine, device: TapDevice, surface: TapSurface, at: string, cell: CellFn, note: (m: string) => void): Promise<void> {
  await framedScene(browser, engine, surface, COVER_TEXT, "chain", async (s) => {
    const rec: Record<string, unknown> = {};
    type Heard = { type: string; pid?: number; ptype?: string; button?: number; detail?: number; trusted: boolean };
    await s.fr.evaluate(() => {
      const w = window as any; w.__tch = [];
      for (const type of ["pointerdown", "pointerup", "pointercancel", "mousedown", "mouseup", "click", "touchstart", "touchend", "touchcancel"]) window.addEventListener(type, (e: any) => { w.__tch.push({ type: e.type, pid: e.pointerId, ptype: e.pointerType, button: e.button, detail: e.detail, trusted: e.isTrusted }); }, true);
      w.__tblur = 0; w.__tblurAtClick = -1;
      window.addEventListener("blur", (e: Event) => { if (e.target === window) w.__tblur++; }, true);   // the blurs of the viewer's window, read by the cells of round 19's two rules
      window.addEventListener("click", () => { w.__tblurAtClick = w.__tblur; }, true);   // and their count at the last click here, before any tab an open brings to the front blurs it
    });
    await s.page.evaluate(() => {
      const w = window as any; w.__tcv = [];
      for (const type of ["pointerdown", "pointerup", "mousedown", "mouseup", "click", "touchstart", "touchend"]) window.addEventListener(type, (e: any) => { w.__tcv.push(e.type); }, true);
    });
    const heard = (): Promise<Heard[]> => s.fr.evaluate(() => (window as any).__tch.splice(0));
    const topHeard = (): Promise<string[]> => s.page.evaluate(() => (window as any).__tcv.splice(0));
    const word = (evs: Heard[]): string => evs.map((e) => e.type + (e.type.startsWith("touch") ? "" : "(" + [e.pid, e.ptype, e.button, e.detail, e.trusted ? "" : "U"].join(",") + ")")).join(" ");
    const n = (evs: Heard[], type: string): number => evs.filter((e) => e.type === type).length;
    const cdp = engine === "chromium" ? await s.page.context().newCDPSession(s.page) : null;
    const tap = async (p: { x: number; y: number }): Promise<void> => { await s.page.touchscreen.tap(p.x, p.y); await frames(s.fr, 4); };
    /** The top page's element (#tcover) and the viewer's element (#tstep), if any, removed; the frame at the top page's top. */
    const drop = (): Promise<string | null> => s.page.evaluate(() => { const out: string[] = []; for (const id of ["tcover", "tstep"]) { const d = document.getElementById(id); if (d) { out.push(id + ":" + getComputedStyle(d).display); d.remove(); } } return out.join(" ") || null; });
    /** No element, the body at its top, and a click on the report's first paragraph (a tap on a phone's pages): its primary press ends
     *  every record and empties the slot before each cell. */
    const settle = async (): Promise<void> => {
      await drop();
      await s.frameTop(0);
      await s.fr.evaluate(() => { (document.querySelector(".fileview-body") as HTMLElement).scrollTop = 0; });
      await frames(s.fr, 3);
      const q = await s.fr.evaluate(() => { const p = document.querySelector(".fileview-md p") as HTMLElement; const r = p.getBoundingClientRect(); const x = Math.round(r.left + 20), y = Math.round(r.top + r.height / 2); const e = document.elementFromPoint(x, y); return e && p.contains(e) ? { x, y } : null; });
      assert.ok(q, at + "the first paragraph's point in view for the settling press (a precondition)");
      if (device === "phone") await tap(q!); else { await s.page.mouse.click(q!.x, q!.y); await frames(s.fr, 3); }
      await heard(); await topHeard(); await s.events(); await s.opens();
    };
    /** The control shown and the geometry of a cell: the point of the tap on the picture beside the control, and the element's box over
     *  the control and that point (top-page pixels, the frame at the top page's top left). */
    const shown = async (what: string): Promise<{ r: Read; tapAt: { x: number; y: number }; box: { x: number; y: number; w: number; h: number }; ctl: { x: number; y: number } }> => {
      const r = await s.place("w490", 3);
      const c = await s.ctlBox();
      const tapAt = { x: Math.round(c.l - 50), y: Math.round(c.t + c.h / 2 + 30) };
      const onPic = await s.fr.evaluate(([x, y]: [number, number]) => document.elementFromPoint(x, y) === (window as any).__timg("w490"), [tapAt.x, tapAt.y]);
      assert.ok(r.inView && r.hit === "the picture" && r.ctl && c.frameTop === 0 && onPic, at + what + ": the control shown, the points on the picture (a precondition): " + JSON.stringify({ r, c, tapAt, onPic }));
      return { r, tapAt, box: { x: Math.round(c.l - 120), y: Math.round(c.t - 10), w: Math.round(c.w + 140), h: Math.round(c.h + 90) }, ctl: { x: c.l + c.w / 2, y: c.t + c.h / 2 } };
    };
    /** The top page's element at `box` now, its behaviour `how` (`event:action[+action]` parts, comma-separated: prevent, hide, pevnone),
     *  and whether the top page hits it at each of `pts`. */
    const element = (box: { x: number; y: number; w: number; h: number }, pts: Array<{ x: number; y: number }>, how: string): Promise<boolean[]> => s.page.evaluate(([b, ps, h]: [{ x: number; y: number; w: number; h: number }, Array<{ x: number; y: number }>, string]) => {
      const d = document.createElement("div");
      d.id = "tcover";
      d.style.cssText = "position:fixed;left:" + b.x + "px;top:" + b.y + "px;width:" + b.w + "px;height:" + b.h + "px;z-index:10;background:#eee;font:16px sans-serif";
      d.textContent = "an element of the top page";
      for (const part of h.split(",")) {
        const [ev, act] = part.split(":");
        d.addEventListener(ev, (e: Event) => { if (act.includes("prevent")) e.preventDefault(); if (act.includes("hide")) d.style.display = "none"; if (act.includes("pevnone")) d.style.pointerEvents = "none"; }, { passive: false });
      }
      document.body.appendChild(d);
      return ps.map((p) => document.elementFromPoint(p.x, p.y) === d);
    }, [box, pts, how]);
    /** The same element, `id` #tcover or #tstep, put up by a one-time capture listener on the viewer's window at the viewer's `on`, and
     *  laid out there where `flush` (a read of its offsetHeight and of the body's box). */
    const appear = (on: string, box: { x: number; y: number; w: number; h: number }, how: string, id = "tcover", flush = false): Promise<void> => s.page.evaluate(([b, o, h, i, fl]: [{ x: number; y: number; w: number; h: number }, string, string, string, boolean]) => {
      const vw = (document.getElementById("tview") as HTMLIFrameElement).contentWindow as Window;
      const f = (): void => {
        vw.removeEventListener(o, f, true);
        const d = document.createElement("div");
        d.id = i;
        d.style.cssText = "position:fixed;left:" + b.x + "px;top:" + b.y + "px;width:" + b.w + "px;height:" + b.h + "px;z-index:10;background:#eee;font:16px sans-serif";
        d.textContent = "an element of the top page";
        for (const part of h.split(",")) {
          if (!part) continue;
          const [ev, act] = part.split(":");
          d.addEventListener(ev, (e: Event) => { if (act.includes("prevent")) e.preventDefault(); if (act.includes("hide")) d.style.display = "none"; }, { passive: false });
        }
        document.body.appendChild(d);
        if (fl) { void d.offsetHeight; void document.body.getBoundingClientRect(); }
      };
      vw.addEventListener(o, f, true);
    }, [box, on, how, id, flush]);
    const upOver = (pts: Array<{ x: number; y: number }>): Promise<boolean[]> => s.page.evaluate((ps: Array<{ x: number; y: number }>) => { const d = document.getElementById("tcover"); return ps.map((p) => !!d && document.elementFromPoint(p.x, p.y) === d); }, pts);
    /** The keyboard focus in the viewer's document after the settling click, asserted, and the count of the viewer's window's blurs
     *  started from there: an element that cancels nothing takes the focus at the mousedown it takes, so the viewer's window hears a
     *  blur and the blur's rule refuses that cell too, while one that cancels its mousedown takes no focus, so no blur comes and the
     *  blur's rule refuses nothing in that cell (the file review's round 19, with the blur's rule built). */
    const focusKept = async (what: string): Promise<void> => {
      await s.fr.evaluate(() => { (window as any).__tblur = 0; (window as any).__tblurAtClick = -1; });
      const f = await s.fr.evaluate(() => document.hasFocus());
      assert.ok(f, at + what + ": the keyboard focus in the viewer's document after the settling click (a precondition)");
    };
    /** The blurs of the viewer's window between focusKept and the covered click here, recorded, and asserted: one or more where the
     *  element cancels nothing, none where it cancels its mousedown (a tab the click opens, under a gate that lets it, blurs the
     *  window after the click, which this count leaves out). */
    const blurs = async (what: string, cancels: boolean, rec0: Record<string, unknown>): Promise<void> => {
      const b = await s.fr.evaluate(() => (window as any).__tblurAtClick);
      rec0.blurs = b;
      assert.ok(cancels ? b === 0 : b > 0, at + what + ": " + (cancels ? "no blur of the viewer's window came before the covered click" : "the viewer's window heard a blur before the covered click") + " (a precondition): " + b);
    };
    /** The next click of the mouse on the picture (a tap on a phone's pages, or where `byTap`), the element gone: its opens. */
    const next = async (what: string, byTap = device === "phone"): Promise<[number, number]> => {
      const r2 = await s.read("w490");
      assert.ok(r2.inView && r2.hit2 === "the picture", at + what + ": the control in view and the next click's point on the picture (a precondition): " + JSON.stringify(r2));
      if (byTap) await tap(r2.pt2); else { await s.page.mouse.click(r2.pt2.x, r2.pt2.y); await frames(s.fr, 3); }
      await heard();
      return s.opens();
    };
    /** The covered click's shape, asserted: the lone click (Firefox), or a compatibility mousedown, a mouseup and a click with no
     *  pointerdown, of `own` pointerId or another, and a pointerup where `up`. */
    const lone = (evs: Heard[], what: string): void => { assert.ok(n(evs, "click") === 1 && evs.some((e) => e.type === "click" && e.trusted) && n(evs, "pointerdown") + n(evs, "pointerup") + n(evs, "mousedown") + n(evs, "mouseup") === 0, at + what + ": the viewer hears the tap's trusted click alone, no pointerdown, pointerup, mousedown or mouseup before it (a precondition): " + word(evs)); };
    const foreign = (evs: Heard[], what: string, stepId: number | undefined, up: boolean): void => {
      const c = evs.find((e) => e.type === "click");
      assert.ok(c && c.trusted && n(evs, "click") === 1 && n(evs, "mousedown") === 1 && n(evs, "mouseup") === 1 && n(evs, "pointerdown") === 0 && n(evs, "pointerup") === (up ? 1 : 0), at + what + ": the viewer hears another document's tap as " + (up ? "a pointerup, " : "") + "a mousedown, a mouseup and a trusted click, no pointerdown (a precondition): " + word(evs));
      if (engine === "chromium") assert.ok(c!.ptype === "touch" && c!.pid !== stepId, at + what + ": that click carries another touch's pointerId, typed touch (a precondition): " + word(evs));
      if (engine === "webkit") assert.ok(c!.ptype === "mouse" && c!.pid === 1, at + what + ": that click carries pointerId 1, typed mouse (a precondition): " + word(evs));
    };
    const want3 = [[0, 0], [0, 0], [1, 1]];
    /** The mouseup that ends the chain (Firefox and WebKit): the viewer's own tap on the picture whose compatibility mousedown an
     *  element appearing at its pointerup takes and hides at, so the viewer hears the tap's pointerdown, pointerup and touchend and
     *  then its mouseup of detail 0 and no click; then another document's tap on an element over the control that hides at its own
     *  pointerup and cancels nothing, whose compatibility mousedown, mouseup of detail 1 and click land in the viewer, the click
     *  under pointerId 0 typed touch in Firefox and under pointerId 1 typed mouse in WebKit. */
    const mouseupEnds = async (pre: string): Promise<void> => {
      const what = "the viewer's own tap on the picture, its compatibility mousedown taken by an element appearing at its pointerup that hides at that mousedown, then another document's tap that cancels nothing";
      await settle();
      const g = await shown(what);
      await appear("pointerup", g.box, "mousedown:hide", "tstep");
      await tap(g.tapAt);
      const st = await heard();
      assert.ok(n(st, "pointerdown") === 1 && n(st, "pointerup") === 1 && n(st, "touchend") === 1 && n(st, "mousedown") === 0 && n(st, "mouseup") === 1 && st.some((e) => e.type === "mouseup" && e.button === 0 && e.detail === 0) && n(st, "click") === 0, at + what + ": the viewer hears its tap's pointerdown, pointerup and touchend and then a mouseup of detail 0, no mousedown and no click (a precondition): " + word(st));
      const stepOpens = await s.opens();
      await drop();
      const over = await element(g.box, [g.ctl, g.tapAt], "pointerup:hide");
      assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over));
      await topHeard();
      await tap(g.tapAt);
      const evs = await heard();
      rec[what] = { step: word(st), tap: word(evs), top: await topHeard(), el: await drop() };
      foreign(evs, what, 2, false);
      const c = evs.find((e) => e.type === "click");
      assert.ok(evs.some((e) => e.type === "mouseup" && e.button === 0 && (e.detail ?? 0) > 0) && (engine !== "firefox" || (c!.ptype === "touch" && c!.pid === 0)), at + what + ": that tap's mouseup is the primary button's of detail above 0" + (engine === "firefox" ? ", and its click carries pointerId 0, typed touch" : "") + " (a precondition): " + word(evs));
      const tapOpens = await s.opens();
      cell(pre + what + ": [the viewer's tap's opens, the other document's click's, the next click's]", want3, [stepOpens, tapOpens, await next(what)]);
    };
    /** A mouse's press whose pointerup the viewer never hears (Firefox and WebKit): in WebKit the mouse held on the control, or on the
     *  picture with the control shown, and in Firefox the mouse pressed on the control and released in the other pane, so the viewer
     *  hears the press's pointerdown and mousedown and no pointerup; then another document's tap on an element over the control that
     *  hides at that tap's compatibility mousedown, whose mouseup of detail 1 and click alone land in the viewer, WebKit's click under
     *  pointerId 1 typed mouse, the held mouse's own, and Firefox's under pointerId 0 typed touch; in WebKit the held mouse is then
     *  released on the top page's bar. */
    const lostUp = async (pre: string, on: "control" | "picture", released: boolean): Promise<void> => {
      const what = (released ? "the mouse pressed on the control and released in the other pane" : "the mouse held on the " + on) + ", then another document's tap on an element over the control that hides at that tap's compatibility mousedown";
      await settle();
      const g = await shown(what);
      const from = on === "control" ? g.ctl : g.r.pt;
      const tapAt = on === "control" ? { x: Math.round(g.ctl.x), y: Math.round(g.ctl.y) } : g.tapAt;
      await s.page.mouse.move(Math.round(from.x), Math.round(from.y));
      await s.page.mouse.down();
      if (released) { await s.page.mouse.move(1100, 300, { steps: 6 }); await s.page.mouse.up(); }
      await frames(s.fr, 4);
      const st = await heard();
      assert.ok(n(st, "pointerdown") === 1 && st.some((e) => e.type === "pointerdown" && e.ptype === "mouse") && n(st, "mousedown") === 1 && n(st, "pointerup") === 0 && n(st, "click") === 0, at + what + ": the viewer hears the mouse's pointerdown and mousedown and no pointerup or click (a precondition): " + word(st));
      const stepOpens = await s.opens();
      const over = await element(g.box, [g.ctl, tapAt], "mousedown:hide");
      assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over));
      await topHeard();
      await tap(tapAt);
      const evs = await heard();
      const top = await topHeard();
      const el = await drop();
      rec[what] = { step: word(st), tap: word(evs), top, el };
      const c = evs.find((e) => e.type === "click");
      assert.ok(c && c.trusted && n(evs, "click") === 1 && n(evs, "mouseup") === 1 && evs.some((e) => e.type === "mouseup" && e.button === 0 && (e.detail ?? 0) > 0) && n(evs, "mousedown") + n(evs, "pointerdown") + n(evs, "pointerup") === 0 && (engine === "webkit" ? c.pid === 1 && c.ptype === "mouse" : c.pid === 0 && c.ptype === "touch"), at + what + ": the viewer hears that tap's mouseup of detail 1 and its trusted click alone, the click under " + (engine === "webkit" ? "pointerId 1 typed mouse" : "pointerId 0 typed touch") + " (a precondition): " + word(evs));
      assert.ok(top.includes("mousedown") && el === "tcover:none", at + what + ": the tap's compatibility mousedown went to the top page's element, hidden at it (a precondition): " + JSON.stringify({ top, el }));
      const tapOpens = await s.opens();
      const read: unknown[] = [stepOpens, tapOpens];
      if (!released) { await s.page.mouse.move(1100, 650, { steps: 3 }); await s.page.mouse.up(); await frames(s.fr, 3); const up = await heard(); assert.ok(n(up, "click") === 0, at + what + ": the release sends no click (a precondition): " + word(up)); read.push(await s.opens()); }
      read.push(await next(what));
      cell(pre + what + ": [the press's opens, the other document's click's, " + (released ? "" : "the release's, ") + "the next click's]", released ? want3 : [[0, 0], [0, 0], [0, 0], [1, 1]], read);
    };
    if (engine === "firefox" && device === "hybrid") {
      for (const [button, bname] of [["right", "a right click"], ["middle", "a middle click"]] as Array<["right" | "middle", string]>) for (const [how, hname] of [["pointerdown:prevent,pointerup:hide", "cancelling its pointerdown and hiding at its pointerup"], ["pointerdown:prevent+hide", "cancelling its pointerdown and hiding at it"], ["pointerdown:prevent+pevnone", "cancelling its pointerdown and taking pointer-events none at it"]]) {
        const what = bname + " on the picture, then the lone click, the element " + hname;
        await settle();
        const g = await shown(what);
        await s.page.mouse.click(g.r.pt.x, g.r.pt.y, { button });
        await frames(s.fr, 3);
        const lo = await heard();
        assert.ok(n(lo, "pointerup") === 1 && n(lo, "click") === 0, at + what + ": " + bname + " sends the viewer a pointerup and no click (a precondition): " + word(lo));
        const loOpens = await s.opens();
        const over = await element(g.box, [g.ctl, g.tapAt], how);
        assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over));
        await heard(); await topHeard();
        await tap(g.tapAt);
        const evs = await heard();
        rec[what] = { lo: word(lo), tap: word(evs), top: await topHeard(), el: await drop() };
        lone(evs, what);
        const tapOpens = await s.opens();
        cell("in Firefox, " + what + ": [" + bname + "'s opens, the lone click's, the next click's]", want3, [loOpens, tapOpens, await next(what)]);
      }
      for (const on of ["pointerup", "pointerdown"]) {
        const what = "the viewer's own tap on the picture, an element appearing at its " + on + " and cancelling its own pointerdown, then the lone click";
        await settle();
        const g = await shown(what);
        await appear(on, g.box, "pointerdown:prevent,pointerup:hide");
        await tap(g.tapAt);
        const step = await heard();
        assert.ok(n(step, "pointerdown") === 1 && n(step, "pointerup") === 1 && n(step, "click") === 0, at + what + ": the viewer hears its tap's pointerdown and pointerup and no click (a precondition): " + word(step));
        const stepOpens = await s.opens();
        const over = await upOver([g.ctl, g.tapAt]);
        assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over));
        await topHeard();
        await tap(g.tapAt);
        const evs = await heard();
        rec[what] = { step: word(step), tap: word(evs), top: await topHeard(), el: await drop() };
        lone(evs, what);
        const tapOpens = await s.opens();
        cell("in Firefox, " + what + ": [the viewer's tap's opens, the lone click's, the next click's]", want3, [stepOpens, tapOpens, await next(what)]);
      }
      const hsteps: Array<[string, (g: { r: Read; tapAt: { x: number; y: number }; box: { x: number; y: number; w: number; h: number }; ctl: { x: number; y: number } }) => Promise<void>, (step: Heard[]) => boolean]> = [
        ["the viewer's own tap on the picture, its compatibility mousedown heard and its mouseup and click taken by an element appearing at that mousedown", async (g) => { await appear("mousedown", g.box, "", "tstep"); await tap(g.tapAt); }, (st) => n(st, "pointerup") === 1 && n(st, "mousedown") === 1 && n(st, "mouseup") === 0 && n(st, "click") === 0],
        ["the viewer's own tap on the picture, its compatibility mousedown heard and an element appearing at it that hides at its click", async (g) => { await appear("mousedown", g.box, "click:hide", "tstep"); await tap(g.tapAt); }, (st) => n(st, "pointerup") === 1 && n(st, "mousedown") === 1 && n(st, "click") === 0],
        ["the viewer's own tap on the picture, its compatibility mousedown taken by an element appearing at its pointerup that hides at that mousedown", async (g) => { await appear("pointerup", g.box, "mousedown:hide", "tstep"); await tap(g.tapAt); }, (st) => n(st, "pointerup") === 1 && n(st, "mousedown") === 0 && st.some((e) => e.type === "mouseup" && e.detail === 0) && n(st, "click") === 0],
        ["the mouse held on the control", async (g) => { await s.page.mouse.move(Math.round(g.ctl.x), Math.round(g.ctl.y)); await s.page.mouse.down(); }, (st) => n(st, "pointerdown") === 1 && n(st, "mousedown") === 1 && n(st, "pointerup") === 0],
        ["the mouse pressed on the control and released on the top page's bar", async (g) => { await s.page.mouse.move(Math.round(g.ctl.x), Math.round(g.ctl.y)); await s.page.mouse.down(); await s.page.mouse.move(1100, 650, { steps: 6 }); await s.page.mouse.up(); }, (st) => n(st, "pointerup") === 1 && st.some((e) => e.type === "mouseup" && e.button === 0 && e.detail === 0) && n(st, "click") === 0],
        ["the mouse pressed on the control and released in the other pane", async (g) => { await s.page.mouse.move(Math.round(g.ctl.x), Math.round(g.ctl.y)); await s.page.mouse.down(); await s.page.mouse.move(1100, 300, { steps: 6 }); await s.page.mouse.up(); }, (st) => n(st, "pointerdown") === 1 && n(st, "pointerup") === 0 && n(st, "click") === 0],
      ];
      for (const [name, step, shape] of hsteps) {
        const what = name + ", then the lone click";
        const held = name === "the mouse held on the control";
        await settle();
        const g = await shown(what);
        await step(g);
        await frames(s.fr, 4);
        const st = await heard();
        assert.ok(shape(st), at + what + ": the step's events in the viewer (a precondition): " + word(st));
        const stepOpens = await s.opens();
        await drop();
        const over = await element(g.box, [g.ctl, g.tapAt], "pointerdown:prevent,pointerup:hide");
        assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over));
        await topHeard();
        await tap(g.tapAt);
        const evs = await heard();
        rec[what] = { step: word(st), tap: word(evs), top: await topHeard(), el: await drop() };
        lone(evs, what);
        const tapOpens = await s.opens();
        const read: unknown[] = [stepOpens, tapOpens];
        if (held) { await s.page.mouse.up(); await frames(s.fr, 3); const up = await heard(); assert.ok(n(up, "click") === 0, at + what + ": the release sends no click (a precondition): " + word(up)); read.push(await s.opens()); }
        read.push(await next(what));
        cell("in Firefox, " + what + ": [the step's opens, the lone click's, " + (held ? "the release's, " : "") + "the next click's]", held ? [[0, 0], [0, 0], [0, 0], [1, 1]] : want3, read);
      }
      await mouseupEnds("in Firefox, ");
      await lostUp("in Firefox, ", "control", true);
      await s.fr.evaluate(() => {
        const w = window as any; w.__tlv = 0;
        window.addEventListener("pointerout", (e: any) => { if (e.relatedTarget === null && e.buttons > 0 && e.pointerType === "mouse") w.__tlv++; }, true);
      });
      const leaves = (): Promise<number> => s.fr.evaluate(() => { const w = window as any; const k = w.__tlv; w.__tlv = 0; return k; });
      for (const hideOn of ["mousedown", "pointerdown"]) {
        const what = "the mouse pressed on the control and released in the other pane, then another document's mouse click on an element over the control that hides at that click's " + hideOn;
        await settle();
        const g = await shown(what);
        const pt = { x: Math.round(g.ctl.x), y: Math.round(g.ctl.y) };
        await leaves();
        await s.page.mouse.move(pt.x, pt.y);
        await s.page.mouse.down();
        await s.page.mouse.move(1100, 300, { steps: 6 });
        await s.page.mouse.up();
        await frames(s.fr, 4);
        const st = await heard();
        const left = await leaves();
        assert.ok(n(st, "pointerdown") === 1 && n(st, "mousedown") === 1 && n(st, "pointerup") === 0 && n(st, "click") === 0 && left > 0, at + what + ": the viewer hears the mouse's pointerdown and mousedown, a pointerout with no relatedTarget and a button down as the press leaves its frame, and no pointerup or click (a precondition): " + word(st) + ", pointerouts " + left);
        const stepOpens = await s.opens();
        const over = await element(g.box, [g.ctl, pt], hideOn + ":hide");
        assert.ok(over[0] && over[1], at + what + ": the element over the control and the click's point (a precondition): " + JSON.stringify(over));
        await topHeard();
        await s.page.mouse.click(pt.x, pt.y);
        await frames(s.fr, 4);
        const evs = await heard();
        const top = await topHeard();
        const el = await drop();
        rec[what] = { step: word(st), click: word(evs), top, el };
        const c = evs.find((e) => e.type === "click");
        assert.ok(c && c.trusted && c.pid === 0 && c.ptype === "mouse" && n(evs, "click") === 1 && n(evs, "pointerup") === 1 && n(evs, "mouseup") === 1 && evs.some((e) => e.type === "mouseup" && e.button === 0 && (e.detail ?? 0) > 0) && n(evs, "pointerdown") + n(evs, "mousedown") === 0, at + what + ": the viewer hears that click's pointerup, its mouseup of detail 1 and its trusted click under pointerId 0 typed mouse, and no pointerdown or mousedown (a precondition): " + word(evs));
        assert.ok(top.includes(hideOn) && el === "tcover:none", at + what + ": that click's " + hideOn + " went to the top page's element, hidden at it (a precondition): " + JSON.stringify({ top, el }));
        const clickOpens = await s.opens();
        cell("in Firefox, " + what + ": [the press's opens, the other document's click's, the next click's]", want3, [stepOpens, clickOpens, await next(what)]);
      }
      {
        const what = "the cost: the viewer's own press on the control dragged out of its frame into the other pane and back, released on the control";
        await settle();
        const g = await shown(what);
        const pt = { x: Math.round(g.ctl.x), y: Math.round(g.ctl.y) };
        await leaves();
        await s.page.mouse.move(pt.x, pt.y);
        await s.page.mouse.down();
        await s.page.mouse.move(1100, 300, { steps: 6 });
        await frames(s.fr, 1);
        await s.page.mouse.move(pt.x, pt.y, { steps: 6 });
        await frames(s.fr, 1);
        await s.page.mouse.up();
        await frames(s.fr, 4);
        const st = await heard();
        const left = await leaves();
        const c = st.find((e) => e.type === "click");
        assert.ok(n(st, "pointerdown") === 1 && n(st, "mousedown") === 1 && n(st, "pointerup") === 1 && c && c.trusted && c.pid === 0 && c.ptype === "mouse" && left > 0, at + what + ": the viewer hears the press's pointerdown and mousedown, a pointerout with no relatedTarget and a button down as it leaves the frame, and its pointerup, mouseup and trusted click back on the control (a precondition): " + word(st) + ", pointerouts " + left);
        rec[what] = { step: word(st) };
        const stepOpens = await s.opens();
        cell("in Firefox, " + what + ": [that click's opens, the next click's]", [[0, 0], [1, 1]], [stepOpens, await next(what)]);
      }
      /* A tap whose compatibility events went to another document (the file review's round 19, extra8-2): the viewer's own tap on the
       * picture, an element of the top page appearing over the picture and the control at that tap's pointerup, which takes the tap's
       * compatibility mousedown, mouseup and click and hides at its own pointerup, then a tap on that element over the control, whose
       * compatibility mousedown, mouseup and click land in the viewer. Firefox sends the viewer a mouseout to no element after the first
       * tap's pointerup, before that click: with a button down where the element is first hit at the compatibility mousedown (appended
       * with no layout read, the mouse off the viewer), and with none where a mouse rests in the viewer and the element is laid out at
       * its append, each cell's precondition. The gate empties the slot there, so the click opens nothing and reveals the control. Each
       * shape runs twice: with an element that cancels nothing, which takes the focus at that tap's compatibility mousedown, so the
       * viewer's window, focused by the settling click, hears a blur (asserted), and with an element that cancels its mousedown, so
       * the focus stays in the viewer and no blur of the viewer's window comes (asserted), and the mouseout's rule alone refuses. */
      await s.fr.evaluate(() => {
        const w = window as any; w.__tmo = [];
        window.addEventListener("mouseout", (e: any) => { if (e.relatedTarget === null) w.__tmo.push(e.buttons); }, true);
      });
      const mouseouts = (): Promise<number[]> => s.fr.evaluate(() => (window as any).__tmo.splice(0));
      for (const [flush, buttons, cancels] of [[false, 1, false], [true, 0, false], [false, 1, true], [true, 0, true]] as Array<[boolean, number, boolean]>) {
        const what = "the viewer's own tap on the picture, an element appearing at its pointerup " + (flush ? "and laid out there, a mouse resting in the viewer" : "with no layout read, the mouse off the viewer") + ", then a tap on that element over the control, which hides at its own pointerup" + (cancels ? ", the element cancelling its mousedown, so the focus stays in the viewer and no blur of the viewer's window comes" : "");
        await settle();
        if (!flush) { await s.page.mouse.move(1100, 650); await frames(s.fr, 2); }
        const g = await shown(what);
        await focusKept(what);
        await appear("pointerup", g.box, cancels ? "pointerup:hide,mousedown:prevent" : "pointerup:hide", "tcover", flush);
        await mouseouts();
        await tap(g.tapAt);
        await new Promise((r) => setTimeout(r, 100));
        const st = await heard();
        const mo = await mouseouts();
        assert.ok(n(st, "pointerdown") === 1 && n(st, "pointerup") === 1 && n(st, "touchend") === 1 && n(st, "mousedown") === 0 && n(st, "click") === 0 && mo.includes(buttons), at + what + ": the viewer hears its tap's pointerdown, pointerup and touchend, no mousedown and no click, and a mouseout to no element with " + (buttons ? "a button" : "no button") + " down (a precondition): " + word(st) + ", mouseouts to no element with buttons " + JSON.stringify(mo));
        const stepOpens = await s.opens();
        const over = await upOver([g.ctl, g.tapAt]);
        assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over));
        await topHeard();
        await tap(g.tapAt);
        await new Promise((r) => setTimeout(r, 100));
        const evs = await heard();
        rec[what] = { step: word(st), mouseouts: mo, tap: word(evs), top: await topHeard(), el: await drop() };
        foreign(evs, what, 0, false);
        const c = evs.find((e) => e.type === "click");
        assert.ok(c!.pid === 0 && c!.ptype === "touch" && evs.some((e) => e.type === "mouseup" && e.button === 0 && (e.detail ?? 0) > 0), at + what + ": that tap's mouseup is the primary button's of detail above 0 and its click carries pointerId 0, typed touch (a precondition): " + word(evs));
        const tapOpens = await s.opens();
        await blurs(what, cancels, rec[what] as Record<string, unknown>);
        cell("in Firefox, " + what + ": [the viewer's tap's opens, the other document's click's, the next click's]", want3, [stepOpens, tapOpens, await next(what)]);
      }
    }
    if (engine === "chromium" && device === "hybrid") {
      const touches = async (pts: Array<[number, number, number]>): Promise<void> => { await cdp!.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: pts.map(([x, y, id]) => ({ x, y, id })) }); };
      const csteps: Array<[string, string, (g: { tapAt: { x: number; y: number }; box: { x: number; y: number; w: number; h: number } }) => Promise<void>]> = [
        ["a second finger resting on the top page's bar", "pointerup:hide", async (g) => { await touches([[g.tapAt.x, g.tapAt.y, 1]]); await touches([[g.tapAt.x, g.tapAt.y, 1], [1100, 650, 2]]); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [{ x: 1100, y: 650, id: 2 }] }); await new Promise((r) => setTimeout(r, 50)); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); }],
        ["a second finger resting in the other pane", "pointerup:hide", async (g) => { await touches([[g.tapAt.x, g.tapAt.y, 1]]); await touches([[g.tapAt.x, g.tapAt.y, 1], [1100, 300, 2]]); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [{ x: 1100, y: 300, id: 2 }] }); await new Promise((r) => setTimeout(r, 50)); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); }],
        ["a second finger resting on the top page's bar, that finger lifted first", "pointerup:hide", async (g) => { await touches([[g.tapAt.x, g.tapAt.y, 1]]); await touches([[g.tapAt.x, g.tapAt.y, 1], [1100, 650, 2]]); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [{ x: g.tapAt.x, y: g.tapAt.y, id: 1 }] }); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); }],
        ["a second finger resting on the top page's bar, the element hiding at its pointerdown", "pointerdown:hide", async (g) => { await touches([[g.tapAt.x, g.tapAt.y, 1]]); await touches([[g.tapAt.x, g.tapAt.y, 1], [1100, 650, 2]]); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [{ x: 1100, y: 650, id: 2 }] }); await new Promise((r) => setTimeout(r, 50)); await cdp!.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); }],
        ["an element appearing at its pointerdown", "", async (g) => { await appear("pointerdown", g.box, "pointerup:hide"); await tap(g.tapAt); }],
        ["an element appearing at its pointerup", "", async (g) => { await appear("pointerup", g.box, "pointerup:hide"); await tap(g.tapAt); }],
        ["an element appearing at its pointerdown that hides at its own pointerdown", "", async (g) => { await appear("pointerdown", g.box, "pointerdown:hide"); await tap(g.tapAt); }],
        ["an element appearing at its pointerup that cancels its own pointerdown", "", async (g) => { await appear("pointerup", g.box, "pointerdown:prevent,pointerup:hide"); await tap(g.tapAt); }],
        ["its compatibility mousedown taken by an element appearing at its pointerup that hides at that mousedown", "pointerdown:prevent,pointerup:hide", async (g) => { await appear("pointerup", g.box, "mousedown:hide", "tstep"); await tap(g.tapAt); }],
      ];
      for (const [name, how, step] of csteps) {
        const what = "the viewer's own tap on the picture with " + name + ", then another document's tap";
        await settle();
        const g = await shown(what);
        await step(g);
        await frames(s.fr, 4);
        await new Promise((r) => setTimeout(r, 100));
        const st = await heard();
        const down = st.find((e) => e.type === "pointerdown");
        assert.ok(down && down.ptype === "touch" && n(st, "pointerup") === 1 && n(st, "click") === 0, at + what + ": the viewer hears its tap's pointerdown and pointerup, typed touch, and no click (a precondition): " + word(st));
        const stepOpens = await s.opens();
        if (how) { await drop(); const over = await element(g.box, [g.ctl, g.tapAt], how); assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over)); }
        else { const over = await upOver([g.ctl, g.tapAt]); assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over)); }
        await topHeard();
        await tap(g.tapAt);
        const evs = await heard();
        rec[what] = { step: word(st), tap: word(evs), top: await topHeard(), el: await drop() };
        foreign(evs, what, down!.pid, false);
        const tapOpens = await s.opens();
        cell("in Chromium, " + what + ": [the viewer's tap's opens, the other document's click's, the next click's]", want3, [stepOpens, tapOpens, await next(what)]);
      }
      if (surface === "pane") {
        /* The frame-hide road (the file review's round 19, extra5-1 and extra8-1), on the Files pane: a press on the control with the
         * control shown, held while the top page hides the viewer's frame (display none, inside the top page's next requestAnimationFrame
         * callback, which asks for one more), released at once on the top page, the frame shown again at once or 300 ms later, then
         * another document's click on an element over the control that hides at that click's mousedown: the mouse's click moved onto
         * the control (Playwright's click moves the pointer first), or a pen's still click where its press was (CDP). This window hears
         * the press's pointerdown and mousedown and then that click's pointerup, mouseup and click, and before that click Chromium sends
         * it the mouse's pointerout with no relatedTarget and no button down, each cell's precondition, which the gate reads as a
         * release it did not hear. Each shape runs twice: with an element that cancels nothing, which takes the focus at that click's
         * mousedown, so the viewer's window, focused by the settling click, hears a blur (asserted), and with an element that cancels
         * its mousedown, so the focus stays in the viewer and no blur of the viewer's window comes (asserted), and the leave's arm for
         * no button alone refuses. */
        await s.fr.evaluate(() => {
          const w = window as any; w.__tlo = [];
          window.addEventListener("pointerout", (e: any) => { if (e.relatedTarget === null) w.__tlo.push(e.pointerType + " " + e.pointerId + " buttons " + e.buttons); }, true);
        });
        const outs = (): Promise<string[]> => s.fr.evaluate(() => (window as any).__tlo.splice(0));
        const pen = (type: string, x: number, y: number, buttons: number): Promise<unknown> => cdp!.send("Input.dispatchMouseEvent", { type, x, y, button: type === "mouseMoved" && !buttons ? "none" : "left", buttons, clickCount: 1, pointerType: "pen" });
        for (const [by, showMs, cancels] of [["mouse", 0, false], ["mouse", 300, false], ["pen", 300, false], ["mouse", 0, true], ["mouse", 300, true], ["pen", 300, true]] as Array<["mouse" | "pen", number, boolean]>) {
          const what = (by === "mouse" ? "the mouse" : "a pen") + " pressed on the control and held while the top page hides the viewer's frame, released at once on the top page, the frame shown again " + (showMs ? showMs + " ms later" : "at once") + ", then another document's " + (by === "mouse" ? "mouse click moved onto" : "still pen click on") + " an element over the control that hides at that click's mousedown" + (cancels ? " and cancels it, so the focus stays in the viewer and no blur of the viewer's window comes" : "");
          await settle();
          const g = await shown(what);
          const at0 = { x: Math.round(g.ctl.x), y: Math.round(g.ctl.y) };
          await focusKept(what);
          await heard(); await topHeard(); await outs(); await s.opens();
          if (by === "mouse") { await s.page.mouse.move(at0.x, at0.y); await s.page.mouse.down(); }
          else { await pen("mouseMoved", at0.x, at0.y, 0); await pen("mousePressed", at0.x, at0.y, 1); }
          await frames(s.fr, 2);
          await s.page.evaluate(() => new Promise<void>((res) => { requestAnimationFrame(() => { (document.getElementById("tview") as HTMLElement).style.display = "none"; requestAnimationFrame(() => { /* one more rendering update asked for, as the measurement did */ }); res(); }); }));
          if (by === "mouse") await s.page.mouse.up(); else await pen("mouseReleased", at0.x, at0.y, 0);
          if (showMs) await new Promise((r) => setTimeout(r, showMs));
          await s.page.evaluate(() => { (document.getElementById("tview") as HTMLElement).style.display = "block"; });
          const c2 = await s.ctlBox();
          const at2 = { x: Math.round(c2.l + c2.w / 2), y: Math.round(c2.t + c2.h / 2) };
          const over = await element({ x: Math.round(c2.l - 120), y: Math.round(c2.t - 10), w: Math.round(c2.w + 140), h: Math.round(c2.h + 90) }, [at2], cancels ? "mousedown:hide+prevent" : "mousedown:hide");
          assert.ok(over[0] && (by === "mouse" || (at2.x === at0.x && at2.y === at0.y)), at + what + ": the element over the control" + (by === "pen" ? ", the control where the press was" : "") + " (a precondition): " + JSON.stringify({ over, at0, at2 }));
          if (by === "mouse") await s.page.mouse.click(at2.x, at2.y); else { await pen("mousePressed", at2.x, at2.y, 1); await pen("mouseReleased", at2.x, at2.y, 0); }
          await new Promise((r) => setTimeout(r, 150));
          await frames(s.fr, 4);
          const evs = await heard();
          const lo = await outs();
          const top = await topHeard();
          const el = await drop();
          rec[what] = { heard: word(evs), outs: lo, top, el };
          const c = evs.find((e) => e.type === "click");
          assert.ok(n(evs, "pointerdown") === 1 && evs[0].type === "pointerdown" && evs[0].ptype === by && n(evs, "mousedown") === 1 && n(evs, "pointerup") === 1 && evs.some((e) => e.type === "pointerup" && e.ptype === by) && n(evs, "mouseup") === 1 && evs.some((e) => e.type === "mouseup" && e.button === 0 && (e.detail ?? 0) > 0) && n(evs, "click") === 1 && !!c && c.trusted && c.ptype === by, at + what + ": the viewer hears the press's pointerdown and mousedown, no pointerup of its release, and that click's pointerup, a mouseup of detail above 0 and a trusted click, typed " + by + " (a precondition): " + word(evs));
          assert.ok(top.includes("pointerup") && top.includes("mousedown") && el === "tcover:none", at + what + ": the release's pointerup and that click's mousedown went to the top page, the element hidden at it (a precondition): " + JSON.stringify({ top, el }));
          assert.ok(lo.includes("mouse 1 buttons 0"), at + what + ": Chromium sent the viewer the mouse's pointerout with no relatedTarget and no button down before that click (a precondition): " + JSON.stringify(lo));
          const clickOpens = await s.opens();
          await blurs(what, cancels, rec[what] as Record<string, unknown>);
          cell("in Chromium, " + what + ": [that click's opens, the next click's]", [[0, 0], [1, 1]], [clickOpens, await next(what)]);
        }
      }
    }
    if (engine === "webkit") {
      {
        const what = "the viewer's own tap on the picture, an element appearing at its pointerdown that hides at its own pointerdown, then another document's tap on it";
        await settle();
        const g = await shown(what);
        await appear("pointerdown", g.box, "pointerdown:hide");
        await tap(g.tapAt);
        const st = await heard();
        assert.ok(n(st, "pointerdown") === 1 && n(st, "pointerup") === 0 && n(st, "touchend") === 1 && n(st, "click") === 0, at + what + ": the viewer hears its tap's pointerdown and touchend, no pointerup and no click (a precondition): " + word(st));
        const stepOpens = await s.opens();
        const over = await upOver([g.ctl, g.tapAt]);
        assert.ok(over[0] && over[1], at + what + ": the element over the control and the tap's point (a precondition): " + JSON.stringify(over));
        await topHeard();
        await tap(g.tapAt);
        const evs = await heard();
        rec[what] = { step: word(st), tap: word(evs), top: await topHeard(), el: await drop() };
        foreign(evs, what, 2, true);
        const tapOpens = await s.opens();
        cell("in WebKit, " + what + ": [the viewer's tap's opens, the other document's click's, the next click's]", want3, [stepOpens, tapOpens, await next(what)]);
      }
      await mouseupEnds("in WebKit, ");
      await lostUp("in WebKit, ", "control", false);
      await lostUp("in WebKit, ", "picture", false);
      {
        const what = "the cost: the viewer's own tap on the picture, an element appearing at its pointerdown that takes the tap's pointerup and hides at it";
        await settle();
        const g = await shown(what);
        await appear("pointerdown", g.box, "pointerup:hide");
        await tap(g.tapAt);
        const st = await heard();
        const c = st.find((e) => e.type === "click");
        assert.ok(n(st, "pointerdown") === 1 && n(st, "pointerup") === 0 && n(st, "touchend") === 1 && n(st, "mousedown") === 1 && n(st, "mouseup") === 1 && c && c.trusted, at + what + ": the viewer hears its tap's pointerdown, touchend, compatibility mousedown, mouseup and trusted click and no pointerup (a precondition): " + word(st));
        rec[what] = { step: word(st), el: await drop() };
        const stepOpens = await s.opens();
        cell("in WebKit, " + what + ": [that tap's opens, the next tap's]", [[0, 0], [1, 1]], [stepOpens, await next(what, true)]);
      }
    }
    if (cdp) await cdp.detach();
    note("record " + JSON.stringify({ engine, device, surface, page: "in a frame beside another pane", scene: "chain", ...rec }));
  }, { device, wide: true });
}
