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
// Playwright's headless WebKit on Linux (WPE's MiniBrowser), under touch emulation for the cells on a phone's pages and on the
// hybrid page and for the stacking cells, a stand-in for WPE and WebKitGTK browsers on a touchscreen (the file review's round 19,
// extra7-4), and with no touchscreen for the plain page's cells and the window-error cases (its round 18, tests-3); no cell claims iOS Safari or the iPhone, a cell
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
// The chain rule's cells (the closing check at 142ade155 after the fixes for the file review's round 18), the gate's own listeners
// and its chain listener hearing the window's capture phase, the chain listener on every type of file-view.ts's CHAIN_TYPES (the
// file review's round 20), each red under a gate without the rules that close it as bef9ff8fc measured it, before that
// round retired every one of those rules but the refusal of a record still standing at a click and the slot's pointerId test for
// the own-chain allowlist, which reads each cell's chain in their place (which cells it
// refuses alone was not driven in the browser at this build), in the dashboard's shape with the viewer's frame beside another
// pane's frame over a bar of the top page: in Firefox, on the hybrid page, the lone click Firefox sends after another document
// cancels a tap's pointerdown, with no mousedown and no mouseup before it, after a right or a middle click on the picture,
// after the viewer's own tap whose compatibility events or click went to another document, and after the mouse held on the
// control or pressed there and released on the top page's bar or in the other pane, opens nothing and the next click opens
// once, red at 142ade155 and, on the chat and the Files pane, under a gate without the tail (which took a press for a
// pointer's click only right after a primary mouseup of detail above 0) and without the mouseup's clear (a mouseup other than a
// primary one of detail above 0 emptied the slot and cleared the tap's flag), but for the mouse held on the control, which the
// refusal of a record still standing at a click closes as well, the mouse released on the top page's bar, which the refusal of
// a record whose pointer left the viewer's window with a button down closes as well, and the mouse released in the other pane,
// which both refusals close as well, and after the viewer's tap whose compatibility events went elsewhere, which the mouseout's
// rule and the blur's rule close as well (at bef9ff8fc 16 of the 28 lone-click cells red under that gate, 18 with the refusal
// of a standing record dropped too, 22 with both refusals dropped and all 28 with the mouseout listener and the blur's rule
// dropped too), and under a gate without the tail alone the two cells a surface of the viewer's tap whose mouseup or click went
// elsewhere, the mouseup's clear closing the twelve after a mouseup of another button or of detail 0 as well; in WebKit, on the
// hybrid page and on a phone's pages, another document's tap after
// the viewer's own tap whose pointerup that document took, so the viewer heard the touch's touchend and no pointerup, opens
// nothing and the next tap opens once, red at 142ade155 and, on the chat and the Files pane, under bef9ff8fc's gate without its
// touchend's marking; and in Firefox, on the hybrid page, and in WebKit, on the hybrid page and on a phone's pages,
// another document's tap that cancels nothing, after the viewer's own tap whose compatibility mousedown an element of the top
// page took, so the viewer heard that tap's mouseup of detail 0 and no click, opens nothing and the next click opens once, red
// at 142ade155 and, on the chat and the Files pane, at 1a6470e72, whose gate had no mouseup's clear, and at bef9ff8fc under a
// gate without that clear and without the blur's rule, in Firefox without the mouseout listener too, since the element takes
// the focus at that tap's compatibility mousedown where the viewer's window held it; and in Firefox, on the
// hybrid page, and in WebKit, on the hybrid page and on a phone's pages, another document's tap on an element over the control
// that hides at that tap's compatibility mousedown, after a mouse's press whose pointerup the viewer never heard (in WebKit the
// mouse held on the control or on the picture, in Firefox the mouse pressed on the control and released in the other pane), so
// the viewer hears that tap's mouseup of detail 1 and its click alone, opens nothing and the next click opens once, the gate
// refusing a pointer's click that finds a record still standing under its own pointerId, red at 142ade155, at 1a6470e72 and at
// 09f58bec6, whose click read the mouse's record, and at bef9ff8fc under a gate whose click reads its own standing record and
// without the blur's rule, in Firefox without the refusal of a record whose pointer left too, since the element takes the focus
// at that tap's compatibility mousedown where the viewer's window held it, while WebKit's cells run again with an element that
// cancels that mousedown, where no blur comes (asserted), red under a gate whose click reads its own standing record alone; the
// reads of these reds a private witness kept out of the tree. In Firefox,
// on the hybrid page, the viewer's own tap with an element of the top page appearing over the picture at its pointerup and
// taking its compatibility events, unflushed with the mouse off the viewer or laid out with a mouse resting in the viewer, then
// another document's tap on that element over the control: the viewer hears a mouseout to no element after its tap's pointerup,
// with a button down or with none, each cell's precondition, which lands in the tap's chain, so the allowlist refuses it (the
// retired mouseout's rule emptied the slot there) and that tap opens nothing and the next click opens once, red at ddb446fae, whose gate heard no mouseout, and under a gate without the mouseout listener and
// without the blur's rule, the cell with no button down also under one whose mouseout needs a button down and that reads no
// blur, since the blur's rule refused these cells too, the viewer's window holding the focus in them and hearing a blur, both
// asserted (they read the same under a gate without the mouseout listener alone and opened under one without both), while each
// shape run again with an element that cancels its mousedown, so the focus stays in the viewer and no blur comes (asserted), is
// red under a gate without the mouseout listener alone, the cell with no button down also under one whose mouseout needs a
// button down, all as bef9ff8fc measured them (the file review's round 19, extra8-2), the reads a private witness kept out of the
// tree. The own-chain allowlist's cells (file-figure-open-taps.ts allowlistCells; the file review's round 20, extra5-2, extra6-1
// and extra7-1), on the hybrid page's Files pane, each run three times: in WebKit, extra7-1's moved click under an element that
// cancels its mousedown and its held-move form, and extra6-1's hover update, and in Firefox extra5-2's unflushed hide, each
// covered click opening nothing and the next click opening once, each opened in every run at bef9ff8fc. The residual, the covered clicks whose chain the own-chain allowlist
// admits, has no cell: an element of another same-origin document shown over the picture during the viewer's own tap, then a
// tap on that element over the control, which goes away during the press and reaches the viewer as that tap's compatibility
// events, a mouseup of detail 1 and a click, where the chain from the viewer's tap's pointerdown to that click is one the
// viewer's own tap makes, so the tab opens with the control covered at that tap's start. The round's recorded rows replayed
// through the gate (the file review's round 20) read 69 such clicks in Firefox, where that element is laid out and hidden with
// a layout flush before the tap's compatibility mousemove, 33 with the own tap's chain and 36 with a compatibility mouseover
// from no element and the focus arriving, 255 in WebKit, 167 and 88, 38 of the 88 with that mouseover, and none in Chromium;
// each measured shape's chain is a measured own gesture's, the 74 with that mouseover and the focus arriving carrying the chain
// of the viewer's own tap with the mouse last outside the viewer and the focus in a nested frame, the other pane or the top page
// (the coordinator's decision 10), and whether to accept it is the owner's decision. The allowlist refuses of the class, each
// covered click opening nothing and revealing the control and the next click opening: Firefox's unflushed hide, a
// compatibility mousedown with no mousemove (extra5-2, 42 covered clicks open at bef9ff8fc), WebKit's delayed hover update after
// a scroll under a resting mouse (extra6-1, 81), and what the retired rules of the file review's round 19 refused, Firefox's
// mouseout to no element where the tap's compatibility events start in the viewer, the cells above, and the blur of the viewer's
// window where it held the focus and the element takes the tap's mousedown without cancelling it. The earlier measurements
// stand as they were taken: the closing check at 142ade155 measured the class's element shapes its probe drove, Firefox 16 of
// 16 in the shape the retired mouseout's rule closed, the element first hit at the compatibility mousedown, and WebKit 7 of 7,
// and under the gate at ddb446fae Firefox 16 of 16, WebKit 7 of 7 and Chromium 0 of 51, every other order of the class it
// drives opening nothing; a probe of the file review's round 19 under bef9ff8fc's rules but the blur's read Firefox's laid-out
// shape with no mouse in the viewer 12 of 12 with the element hidden at the covered tap's pointerup (0 of 12 hidden at its
// pointerdown) and the shapes whose compatibility events start in the viewer 0 of 48, WebKit 24 of 24 with an element
// listening for no mouse event and Chromium 0 of 16; and the retired blur's rule, in a probe kept out of the tree, read
// Firefox's laid-out shape 0 of 36 where the gate without it opened 36 of 36 and WebKit's shapes with an element listening for
// the mouse 0 of 56 where 56 of 56 opened. A check of these fixes drove orders that probe does not and found two more of the
// class outside the residual, open at 142ade155, at 1a6470e72 and at 09f58bec6 (file-view.ts's gate comment states them): the
// first, the cells of a mouse's press whose pointerup the viewer never heard above, whose click read the mouse's record (WebKit
// 22 of 22, Firefox 7 of 7), is closed by the gate's refusal of a record still standing at a click; the second, in Firefox,
// after that release, a mouse click on such an element, whose pointerup handed the mouse's record to the slot and opened (10 of
// 10, again at 343ee2eb5), is refused by the allowlist, since the pointerout with no relatedTarget and a button down that
// Firefox sent as that press left its frame lands in the press's chain (the retired held arm refused it by marking the
// record, 0 of 10 at bef9ff8fc): its cells in Firefox, on the hybrid page, the element hiding at that click's mousedown or its
// pointerdown, open nothing and the next click opens once, red at 343ee2eb5 and at 09f58bec6, and at bef9ff8fc under a gate
// without the held arm and without the blur's rule, while the same cells run again with an element that cancels that
// mousedown, where no blur comes (asserted), were red there under a gate without the held arm alone; Chromium opened neither.
// A press whose pointer left the viewer's window with a button down, by the events the viewer heard, is refused once so, its
// click opening nothing and revealing the control, and the next click opens once: the retired held arm's cost, which the
// allowlist pays the same. Its first cost, measured in Firefox under the held arm: the viewer's own press on the control
// dragged out of its frame and back, released on the control (its cost cell, where 343ee2eb5's gate opened that click; 8 of 8
// in a probe of these fixes), while Chromium and WebKit, which keep a held left press in the frame it began in, opened it. Its
// second, measured in Chromium under the held arm, found by a later check and with no cell: a press on the control or the
// picture held while the top page hides the viewer's frame and shows it again, then released there, refused when the frame's
// next redraw came while it was hidden, which alone brings that pointerout with the button down (168 of 168 such presses
// refused and none of the 232 others in a later probe of these fixes that stamped that redraw, and all 11 of that check's own
// probe refused, where 343ee2eb5's gate opened all 11), the allowlist refusing those by the same pointerout and some of the
// others by the focus fixup's blur with the focus not back, its own cost below, while WebKit sends no such pointerout there. The
// later check found a third order of the class outside the residual, open in WebKit and in one shape in Chromium in the
// timings measured under bef9ff8fc's rules but the blur's and, in WebKit, at 142ade155, 09f58bec6 and 343ee2eb5, with no cell
// here (file-view.ts's gate comment states it): the mouse held on the control while the top page hides the viewer's frame and
// shows it again, then another document's mouse click on an element over the control that hides at that click's mousedown or
// its pointerdown, whose pointerup hands the held press's record to the slot. As measured before the allowlist: WebKit, which
// sends no pointerout there, opened it at every timing under bef9ff8fc's rules but the blur's, 3,700 of 3,700 in a later probe
// of these fixes and 60 of 60 in that check's probe, and under the blur's rule 0 of 3,700 where the viewer's window held the
// focus and the element does not cancel its mousedown and 3,700 of 3,700 where it does; Chromium, which after such a release
// sends the mouse's pointerout with no button down when a redraw finds the frame hidden or when a redraw or a pointer move
// comes between the element's appearing and the click, the Chromium leg's frame-hide cells, 1,526 of 3,700 in the later probe
// under the gate at ddb446fae and 0 of 3,700 under bef9ff8fc's rules but the blur's, opened it, in the timings measured, only in
// its still shape, 85 of 225 still clicks of a mouse and 64 of 180 of a pen with the frame shown at the release under the gate
// without the blur's rule, the blur's rule closing that shape where the viewer's window held the focus and the element does
// not cancel its mousedown, runs of several short hides with the pointer still not measured under these rules; Firefox never,
// 0 of 2,600 on the Files pane and the chat. Under the allowlist (the round's replay), what is left of that order is the
// covered clicks whose chain it admits: WebKit's still pointer, 679, whose chain is the viewer's own click's; Chromium's still
// pointer, 286 of a mouse and 15 of a pen; and Chromium's still pointer with the focus fixup's element blur and the focus back
// before the covered pointerup, 119, whose chain the viewer's own press held across the same hide makes, and so does a plain
// click on the picture while a text input of the viewer holds the focus (the coordinator's decision 2); there the tab opens
// with the control covered. It refuses, each open at bef9ff8fc, the covered click opening nothing and revealing the control
// and the next click opening: WebKit's moved click, a mouse's pointermove with no button down inside the held press or, after
// a held move, a pointerout with no button down to an element and its pointerover (extra7-1, 2,536 covered clicks, the allowlist's
// WebKit cells above); Chromium's focus fixup's element blur with the focus not back (extra5-1, 43 of a mouse and 9 of a pen); and
// a pen's press with the mouse's pointerout with no button down to an element (44). So the residual in all, over the round's rows:
// Chromium 420, Firefox 69, WebKit 934. The gate's cost measured in WebKit, the same at 142ade155: WebKit's cost cell, the viewer's
// own tap whose pointerup an element of the top page takes, shown at the tap's pointerdown and hidden at its pointerup, opens
// nothing and reveals the control, and the next tap opens once, the tap's click carrying pointerId 1 and finding its press only in
// the slot, which no pointerup of that tap filled. The chain rule's other costs, stated by reading, none measured, each a refusal
// that reveals the control: a Firefox touchscreen whose tap's click came typed touch under a pointerId other than its pointerup's
// would refuse every tap there, the tab opening only from the mouse or the keyboard; a pen in the touch order whose click comes
// typed mouse, as WebKit types a touch's click (WPE as measured, and WebKitGTK by analogy), would refuse every tap of that pen,
// the tab still opening from a finger, the mouse or the keyboard; a tap during which another finger that touched the viewer lifts,
// in an engine that clicks after such a tap, opens nothing and reveals the control, the next tap opening once; an engine whose
// touchend came before its pointerup would refuse every tap (none of the three measured); and a pointer's click with no primary
// mouseup of detail above 0 before it, an assistive technology's trusted click with a pointerId and no mouseup or an eraser's tap
// whose mouseup does not carry the primary button, opens nothing and reveals the control, while Enter or Space on the control still
// opens, and so does a pointer's click after whose pointerup a mouseup other than a primary one of detail above 0 came, an order
// none of the three engines measured sends before a click, and a pointer's click that finds a record still standing under its own
// pointerId, which no gesture of the viewer's own that the legs drive leaves. The refusal's cost measured in WebKit alone: a left
// click chorded into a held right press, whose pointerup WebKit holds until the last button's release, opens nothing and reveals
// the control whatever covers or shows it, and the next click opens, 12 of 12 in the road probe, where 09f58bec6's gate opened all
// 12 (file-view.ts's gate comment states it). The mousedown's clear's cost, measured in the three engines: a left click with
// another mouse button held, the other pressed before it or during it, opens nothing and reveals the control, and the next
// click opens (Chromium 16 of 16, Firefox 28 of 28, WebKit 12 of 12 and its chord of a left click into a held right press 4 of
// 4; the file review's round 19, extra7-1), WebKit's chord of a left click into a held right press the one member the refusal
// of a standing record added; Firefox's chord cells above hold that clear's refusal under the text-size flyout, the Outline
// popover and a control out of view. The own-chain allowlist's costs, measured (the file review's round 20: the rulings
// pass's census and the execution check's, Playwright's engines on Linux, touch emulated), each a refusal once that reveals
// the control, the next click opening: the viewer's own press held across a short hide of its frame with the focus not back
// at the release (Chromium, 60 of 360 mouse presses and 36 of 72 pen presses of the check's grid), a 2,000 px block inserted
// above the picture during a held press and removed (WebKit, 3 of 3), and on a device with a mouse and a pen, a pen's press
// during which the mouse moves in the viewer (Chromium, pen emulated, 3 of 3 at d9fb76da0, open at bef9ff8fc), a cost the
// incremental reads pay too; four own gestures the allowlist refused before its read-outs, which bef9ff8fc's gate opened,
// open since: the focus leaving this window, and nothing else, between a mouse click's pointerup and its mouseup, and a
// finger held while the focus leaves this window once, each in one of the three orders the read-outs take, an element's
// blur, the document's or both, then the window's (round 19's measurement of the blur's rule, its recorded rows replayed,
// Chromium 18 and 14, Firefox 14 and WebKit 18, with Firefox's 2 taps whose own pointerdown took the focus out of the viewer's
// window, 66 in all), and a finger's tap during which the mouse moves in the viewer and a mouse click during which a finger
// resting on the viewer moves (Chromium, touch emulated); and by reading any event the grammar does not name that a real
// gesture brings into a press or a tap, among them the places below where the incremental reads would open, 24 families of which
// are measured since, and the device's gestures in Firefox and WebKit. The retired blur's rule's own cost, a focus move out of the
// viewer's window during the viewer's own press or between a tap's pointerup and its compatibility mousedown, refused once
// in the three engines in a probe kept out of the tree, the allowlist pays the same, and the retired leave's arm for no
// button and mouseout's clear cost nothing measured, no tap or chain cell of this leg changing under them (file-view.ts's
// gate comment states the figures). The read-outs (the coordinator's ruling on the allowlist's build) add no covered click:
// each takes events out only where the viewer's own gesture puts them (the focus-leaving ones the focus leaving this window
// only as the whole of what comes between a mouse's pointerup and its mouseup or as one run before a finger's pointerup,
// each in one of three orders, an element's blur, the document's or both, then the window's), where a covered chain of the
// recorded rows carries the focus leaving the viewer's window it leaves before the covered pointerup, at the press another
// document's element takes, and none carries the mouse's moves in a finger's contact or a finger's move in a mouse's press,
// so of the 19,325 covered clicks of every recorded row that reach the allowlist the read-outs change no chain, and the
// covered grid read 0 covered clicks added in each engine at 5288151dd, which brought them, and again at 180f96d2a, the
// landing merge of the fork's main at 6dd80a6e7, whose gate is the retirement's byte for byte; they have no cell here, the
// outline suite's admit rows and narrowness rows pinning them. That round also retired five rules with no measured effect
// under the allowlist (the coordinator's ruling on its build): the tail, the mouseup's clear of the slot and the tap's flag,
// the dragstart's clear of every record, the touchend's and the touchcancel's marking of every touch record and the pointercancel's
// clear of the slot, each event they read landing in the chain of the press or the tap it acted on, which the allowlist
// refuses, or leaving a record standing that refuses its own pointer's click, all five gone changing no click over every
// recorded row, the cells above that were red under a gate without one of them standing as the allowlist refusing their
// orders. The allowlist's three measured costs above are the incremental reads' too, the reads the round drafted in its place. It
// costs more than they do at 24 families of the viewer's own gesture measured in the browser at ff255168f or at 7186e10ab, whose
// gates compile to the same code (at 7186e10ab alone for an element's blur that no focus follows in a tap, the mouse moving with
// its button held during a finger's tap, the focus leaving after a pen's click's mouseup, the mouse's paths into and out of
// the viewer during a finger's tap that cross an element's edge, and the chat), by a probe of these fixes kept out of the tree
// (Playwright's engines on Linux, the Files pane, touch emulated in each engine and pen in Chromium, five of each gesture per
// engine: each refused 5 of 5 in each engine named, opened 5 of 5 by bef9ff8fc's gate, and opened by those reads replayed over its
// recorded chain), since they act on a few named events alone: the window's blur alone, with no element's or document's blur before
// it, at a mouse click's release and in a finger's contact (Chromium and WebKit; Firefox sends the document's blur first there,
// which the read-outs take, and opens), the focus leaving at a pen's click's release or after its mouseup (Chromium),
// and in Chromium, Firefox and WebKit the focus leaving after a click's mouseup, between a tap's compatibility
// mousedown and its mouseup or after a tap's mouseup, leaving and coming back at a click's release, leaving twice in a
// finger's contact, arriving at a click's release, after its mouseup, between a tap's pointerup and its compatibility
// mousedown or after a tap's mouseup, or moving inside the viewer at a click's release or between a tap's touchend
// and its compatibility mousedown, and an element's blur that no focus follows at a click's release, between a
// tap's compatibility mousedown and its mouseup, or at an instant tap's touchstart or its touchend, with the frame shown;
// on a device with more than one pointer (Chromium), a resting finger's touch cancelled during a mouse click,
// as Chromium cancels a resting finger that moves far enough to scroll, a finger moving during a pen's press,
// the mouse crossing an element's edge in the viewer during a finger's tap, whether or not it also enters or leaves
// the viewer, the mouse moving with its button held during a finger's tap, and a pen hovering during a mouse click
// or during a finger's tap; and a press past the cap of 1,024 tokens (the three engines). Eight of the 24 were also
// measured in the chat, refused there in the same engines: the window's blur alone at a mouse click's release and
// in a finger's contact (Chromium and WebKit, Firefox opening), the focus leaving after a mouse click's mouseup and
// leaving and coming back at a click's release (Chromium, Firefox and WebKit), and the focus leaving at a pen's click's
// release or after its mouseup, a finger moving during a pen's press, the mouse crossing an element's edge in the viewer during
// a finger's tap and a pen hovering during a mouse click (Chromium). Measured in Chromium and not costs: a resting
// finger that leaves the viewer or crosses an element's edge within the touch slop during a mouse click, and the mouse entering or
// leaving the viewer during a finger's contact on a path that crosses no element's edge in the viewer, open under
// both, and a finger lifted during a mouse click opens nothing under either. By reading: the device's gestures
// in Firefox and WebKit, WebKit's hover update between elements inside a finger's slow tap, a touch-order pen's
// double tap's second tap, and perhaps a capture handler's focus move that no census drove (file-view.ts's gate
// comment says why for each). At each the click or the tap opens nothing and reveals the control, the next click opening, and the
// ruling after the focused re-check at ff255168f keeps the allowlist, leaving the choice between it and those reads to the user.
// The cells of a figure at this origin's file routes (the coordinator's ruling on the same-origin figure after the file review's
// round 19, read over the route's other forms by a check of that build) run in Chromium, Firefox and WebKit, each form in a
// page of its own under a page key, on the chat modal: a figure written with this origin's /file address, in the plain
// spelling, an escaped route (/%66ile), a .. segment or a . segment, and, with a cap the author copied, respelled with a double
// slash or params the kernel drops (//file, /file;x), wears the local words, and its control opens the file the query names in
// the viewer, in the session it names (another than the report's), through the viewer's own capped /file URL, with Back to the
// report and no tab; a figure at the relay's route (/remote/gpu1/file) opens the same way in that host's session, through the
// viewer's own capped relay URL; a host-prefixed sid at the /file route and a pin beside the path wear no control and open
// nothing on a click or a Cmd/Ctrl-click. A name the route does not read, a cache-buster v or a t, and a download of 0 leave
// the file to open, at the /file route and the relay's, while a download of 1, which the route answers as an attachment,
// wears no control and opens nothing (the file review's round 20, regression-2, with the coordinator's decision 7 on it).
// For the file and relay forms, after the control's open and Back, a Cmd/Ctrl-click on the picture, its ctrlKey read back at the
// document, opens one tab at the viewer's own capped URL, the whole prefix with the session the address names, and the viewer
// stays on the report (the file review's round 20, tests-2): red at dcaa80ec4 in the three engines, where it opened a tab at the
// address as written, and, alone of the forms' reads, under a gate that sends that modified click to the web arm, by the key
// test or by the event's own modifier fields, or that opens the tab in the shown file's session.
// The first four forms red at dcaa80ec4, where each opened a tab at the address as
// written, which carries no cap, so the kernel's cap rule refuses it; the next five red at d140285a4, where the respelled
// forms opened a tab whose address kept the author's cap, the relay's route and the host-prefixed sid a tab at the address as
// written, and the pin the live file in the viewer; the four forms naming what the route does not read red at bef9ff8fc,
// where each wore no control and opened nothing, and the download of 1 reds under a rule that leaves the download out of the
// three it refuses. A /file address on another origin, or on this host at another port,
// still opens a web tab at its address. The cap pass leaves the escaped route's src and the respelled forms' as written, and
// the escaped route loads here only because the harness answers it (file-view.ts ownFileRoute says when it loads at the
// kernel); file-figure-open.test.ts runs the classifier over these forms and more in CI.
// This leg stays off the shared roster of browser legs that PR 887 landed, vscode-extension/ci-browser-legs.txt, since
// that roster's job installs Chromium alone, so a WebKit or Firefox test in a rostered file would not run there.
// Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, and no job installs Firefox
// or WebKit, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper); file-view-outline.test.ts
// drives WebKit's order, the stale records and the clicks by no pointer over the stand-in in CI. Synthetic values only: the
// notes-api world, a placeholder session id, example.test and other.test addresses, /repo/notes-api paths, a page key minted at
// run time.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser, openViewer, openPanel, frames, PARA, REPORT, ROOT, ORIGIN, type Served } from "./real-viewer-leg";
import { tapCells, allowlistCells, type TapDevice, type TapEngine, type TapSurface } from "./file-figure-open-taps";
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
    ? "; the chain rule's cell of the lost pointerup red at 142ade155 and under a gate whose touchend marks no touch record refused, its cell of the mouseup that ended the chain red at 142ade155 and at 1a6470e72, whose gate had no mouseup's clear, its cells of the held mouse red at 142ade155, at 1a6470e72 and at 09f58bec6, whose click read the mouse's record, and those with an element that cancels its mousedown, where no blur comes, under a gate whose click reads its own standing record, the cost cell reading the same at 142ade155 by design, the reds under a gate without a rule as bef9ff8fc measured them, before the file review's round 20 retired every one of those rules but the refusal of a record still standing at a click for the own-chain allowlist"
    : "; the chain rule's cells red at 142ade155, the lone click's under a gate without the tail and the mouseup's clear but after the mouse held on the control, which the refusal of a record still standing at a click closes too, after the mouse released on the top page's bar, which the refusal of a record whose pointer left the viewer's window with a button down closes too, and after the mouse released in the other pane, which both refusals close too, two of them under a gate without the tail alone and three more under one without the tail, the mouseout listener and the blur's rule, one of those with the mouseup's clear dropped too, its cell of the mouseup that ended the chain at 1a6470e72, whose gate had no mouseup's clear, and its cell of the mouse released in the other pane before another document's tap at 1a6470e72 and at 09f58bec6, whose click read the mouse's record, and under a gate without both refusals and the blur's rule, its cells of that release before another document's mouse click red at 343ee2eb5 and at 09f58bec6, whose pointerup handed the slot the mouse's shown record, and those with an element that cancels its mousedown, where no blur comes, under a gate without the refusal of a record whose pointer left, and its cost cell reading an open there and at 142ade155, recording the cost, and its cells of a tap whose compatibility events went to another document red at ddb446fae, whose gate heard no mouseout, and under a gate without the mouseout listener and without the blur's rule, the cell with no button down also under one whose mouseout needs a button down and that reads no blur, those with an element that cancels its mousedown, where no blur comes, under a gate without the mouseout listener alone, the cell with no button down also under one whose mouseout needs a button down, each red under a gate without a rule as bef9ff8fc measured it, before the file review's round 20 retired every one of those rules but the refusal of a record still standing at a click, the own-chain allowlist refusing those orders since";
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
for (const engine of ["webkit", "firefox"] as TapEngine[]) {
  const named = engine === "webkit" ? "WebKit (Playwright's, on Linux under touch emulation)" : "Firefox";
  const orders = engine === "webkit"
    ? "extra7-1's moved click, the mouse held on the control while the top page hides and shows the viewer's frame, released on the top page, then a click moved onto an element over the control that cancels its mousedown, whose chain carries a mouse's pointermove with no button down in the held press, and its held-move form, whose chain carries a mouse's pointerout with no button down to an element and its pointerover in its place; and extra6-1's delayed hover update, the viewer's tap with the mouse resting in the viewer after the body scrolled under it and an element appearing at its pointerup, then a tap on that element, whose chain carries the mouse's pointer events with no button down between the first tap's pointerup and the second's compatibility mousedown"
    : "extra5-2's unflushed hide, the viewer's body box focused and the mouse off the viewer, the viewer's tap on the control with an element appearing and laid out at its pointerup that cancels its mousedown, then a tap on it that hides it at its own pointerup with no layout read, whose compatibility mousemove Firefox sends to the hidden element, so the chain carries a compatibility mousedown with no mousemove";
  test("in " + named + " on a hybrid page in the dashboard's shape, the Files pane: the own-chain allowlist's cells (the file review's round 20, extra5-1, extra5-2, extra6-1 and extra7-1, with the coordinator's decisions on them): " + orders + ": each covered click opens nothing and the next click opens once, in each of three runs, each run's shape asserted as its precondition (property pins over window.open's calls read off the page; each cell opened its covered click in every run at bef9ff8fc, whose gate read none of those events, the reads a private witness kept out of the tree)", { timeout: 300000 }, async (t) => {
    let cells: Array<[string, unknown, unknown]> = [];
    let ran = false;
    await inBrowser(t, async (browser) => {
      ran = true;
      cells = await allowlistCells(browser, engine, 3, (m) => t.diagnostic(m));
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

// ── a figure at this origin's file routes, in the three engines (the coordinator's ruling on the same-origin figure after the
// file review's round 19) ── Each form in a page of its own under a page key, the chat modal at 900 by 700, window.open recorded.
const OWN_PIC = ROOT + "/docs/figs/b.svg";
const OWN_SID = "22222222-3333-4444-5555-666666666666";   // the session the figure's address names, another than the report's, so the open is seen to take the address's
const OWN_Q = "?path=" + encodeURIComponent(OWN_PIC) + "&sid=" + OWN_SID;
const OWN_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200"><rect width="300" height="200" fill="#1f78b4"/></svg>';
const AUTHORED_CAP = "&cap=" + "A".repeat(22);   // a cap the author copied into the address, assembled at run time (no credential-shaped literal)
const OWN_FORMS: Array<[string, string, "file" | "relay" | "none" | "web"]> = [
  ["the plain spelling", ORIGIN + "/file" + OWN_Q, "file"],
  ["an escaped route", ORIGIN + "/%66ile" + OWN_Q, "file"],
  ["a .. segment", ORIGIN + "/x/../file" + OWN_Q, "file"],
  ["a . segment", ORIGIN + "/./file" + OWN_Q, "file"],
  ["a double slash before the route, with a cap the author copied", ORIGIN + "//file" + OWN_Q + AUTHORED_CAP, "file"],
  ["params on the route, with a cap the author copied", ORIGIN + "/file;x" + OWN_Q + AUTHORED_CAP, "file"],
  ["the relay's route", ORIGIN + "/remote/gpu1/file" + OWN_Q, "relay"],
  ["a host-prefixed sid at the /file route", ORIGIN + "/file?path=" + encodeURIComponent(OWN_PIC) + "&sid=gpu1:" + OWN_SID, "none"],
  ["a pin beside the path", ORIGIN + "/file" + OWN_Q + "&pin=" + "0".repeat(32), "none"],
  ["a cache-buster the route does not read", ORIGIN + "/file" + OWN_Q + "&v=2", "file"],
  ["a t the route does not read", ORIGIN + "/file" + OWN_Q + "&t=1727580000", "file"],
  ["a download of 0, which the route does not answer as one", ORIGIN + "/file" + OWN_Q + "&download=0", "file"],
  ["the relay's route with a cache-buster the route does not read", ORIGIN + "/remote/gpu1/file" + OWN_Q + "&v=2", "relay"],
  ["a download of 1, answered as an attachment", ORIGIN + "/file" + OWN_Q + "&download=1", "none"],
  ["another origin", "http://other.test/file" + OWN_Q, "web"],
  ["this host at another port", "http://notes-api.test:8080/file" + OWN_Q, "web"],
];
/** Every figure request answered with the picture when it names OWN_PIC, whatever route spelling asked (the escaped route's
 *  src is left uncapped as written, and the harness has no kernel to refuse it). */
const ownServe = (u: URL): Served | null => (u.searchParams.get("path") === OWN_PIC ? { status: 200, type: "image/svg+xml", body: OWN_SVG } : null);
/** The Cmd/Ctrl-click on the picture after the control's open and Back, for the file and relay forms (the file review's round 20,
 *  tests-2): each click's ctrlKey read back at the document, the tabs window.open was asked for, and the file the bar names after
 *  it. */
type OwnCtrl = { ctrl: boolean[]; tab: string[]; stayed: string | null };
type OwnRead = { gated: boolean; capped: boolean; words: string | null; opened: string[]; base: string | null; shown: string | null; back: string | null; ctrlClick: OwnCtrl | null };
async function ownFormScene(browser: any, dest: string, key: string, kind: "file" | "relay" | "none" | "web"): Promise<{ read: OwnRead; errors: string[] }> {
  const note = "# Report\n\n![the figure](" + dest + ")\n\n" + PARA(1) + "\n";
  const { page, errors } = await openViewer(browser, "chat", 900, 700, {
    docs: { [REPORT]: note, [OWN_PIC]: OWN_SVG }, serve: ownServe,
    before: async (pg: any) => {
      await pg.evaluate((k: string) => { (window as any).__rompPageKey = () => k; }, key);   // as the kernel's page-key script installs it
      await pg.route((u: URL) => u.href.startsWith("http://other.test/"), (route: any) => route.fulfill({ status: 200, contentType: "image/svg+xml", body: OWN_SVG }));
    },
  });
  try {
    await page.evaluate(() => { const w = window as any; w.__opened = []; window.open = ((u: unknown) => { w.__opened.push(String(u)); return { opener: null }; }) as unknown as typeof window.open; });
    const gated = await page.evaluate(() => { const g = document.querySelector('.fileview-md [data-act="fv-load"]') as HTMLElement | null; if (g) g.click(); return !!g; });   // another host's figure waits behind its box: loaded first
    await page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
    await frames(page, 3);   // the control's decision runs at the load (armFigureControls), so three frames after it every form wears its control or none
    const pre = await page.evaluate(() => { const i = document.querySelector(".fileview-md img")!; const c = i.nextElementSibling && i.nextElementSibling.hasAttribute("data-fv-figopen") ? i.nextElementSibling : null; return { src: i.getAttribute("src") || "", words: c ? c.getAttribute("title") : null }; });
    await page.locator(".fileview-md img").hover();
    await frames(page, 2);
    if (pre.words !== null) {
      await page.locator(".fileview-md [data-fv-figopen]").click();
      await page.waitForFunction(() => (window as any).__opened.length > 0 || /b\.svg/.test((document.querySelector(".fileview-base") || { textContent: "" }).textContent || ""), null, { timeout: 10000 });
      await page.waitForFunction(() => (window as any).__opened.length > 0 || !!document.querySelector("img.fileview-img"), null, { timeout: 10000 });
    } else {
      await page.locator(".fileview-md img").click();   // a form with no control: the plain click on the picture, which opens its target where it has one
      await page.locator(".fileview-md img").click({ modifiers: ["ControlOrMeta"] });   // and the Cmd/Ctrl-click, its own tab's gesture
      await frames(page, 5);   // nothing is due: the reads below find no tab, the report still shown
    }
    await frames(page, 3);
    const after = await page.evaluate(() => { const i = document.querySelector("img.fileview-img"); const b = document.querySelector(".fileview-nav-back") as HTMLElement | null; const shown = !!b && !b.closest("[hidden]") && b.getAttribute("aria-disabled") !== "true"; return { opened: ((window as any).__opened as string[]).slice(), base: (document.querySelector(".fileview-base") || { textContent: null }).textContent, shown: i ? i.getAttribute("src") : null, back: shown ? b!.title : null }; });
    let ctrlClick: OwnCtrl | null = null;
    if (kind === "file" || kind === "relay") {
      // the figure's own-tab gesture, a Cmd/Ctrl-click on the picture, after the control's open and Back: Back only where the viewer
      // moved (at a head whose control opened a tab the viewer stayed and Back is disabled), then the click with the key held, its
      // ctrlKey read back off a capture listener at the document, so the gesture cannot pass as a plain click
      if (after.back !== null) {
        await page.locator(".fileview-nav-back").click();
        await page.waitForFunction(() => /report\.md/.test((document.querySelector(".fileview-base") || { textContent: "" }).textContent || ""), null, { timeout: 10000 });
        await page.waitForFunction(() => { const i = document.querySelector(".fileview-md img") as HTMLImageElement | null; return !!i && i.complete && i.naturalWidth > 0; }, null, { timeout: 10000 });
        await frames(page, 3);
      }
      const n0 = await page.evaluate(() => { const w = window as any; w.__ctrl = []; document.addEventListener("click", (ev) => { w.__ctrl.push((ev as MouseEvent).ctrlKey); }, { capture: true }); return ((w.__opened as string[]) || []).length; });
      await page.locator(".fileview-md img").hover();
      await frames(page, 2);
      await page.locator(".fileview-md img").click({ modifiers: ["ControlOrMeta"] });
      await page.waitForFunction((n: number) => (window as any).__opened.length > n, n0, { timeout: 10000 }).catch(() => undefined);   // the tab is due; its absence is read below
      await frames(page, 3);
      ctrlClick = await page.evaluate((n: number) => ({ ctrl: ((window as any).__ctrl as boolean[]).slice(), tab: ((window as any).__opened as string[]).slice(n), stayed: (document.querySelector(".fileview-base") || { textContent: null }).textContent }), n0);
    }
    return { read: { gated, capped: /[?&]cap=/.test(pre.src), words: pre.words, ...after, ctrlClick }, errors };
  } finally { await page.close(); }
}
for (const engine of ["chromium", "firefox", "webkit"] as const) {
  const named = engine === "chromium" ? "Chromium" : engine === "firefox" ? "Firefox" : "WebKit (Playwright's, on Linux)";
  test("in " + named + ", under a page key, a figure written with this origin's /file address opens in the viewer and no tab, in the plain spelling, an escaped route, a .. segment and a . segment, and, with a cap the author copied, respelled with a double slash or params the kernel drops, as a local picture opens: the control wears the local words, the viewer shows the file the query names, in the session it names, through its own capped /file URL, and Back returns to the report; a figure at the relay's route opens the same way in its host's session, through the viewer's own capped relay URL; a host-prefixed sid at the /file route and a pin beside the path, which the viewer cannot open as the picture shown, wear no control and open nothing on a click or a Cmd/Ctrl-click; a name the route does not read (a cache-buster v, a t) and a download of 0 leave the file to open, at the /file route and the relay's, and a download of 1, which the route answers as an attachment, wears no control and opens nothing; a /file address on another origin, or on this host at another port, still opens a web tab at its address; and for the file and relay forms, after the control's open and Back, a Cmd/Ctrl-click on the picture opens one tab at the viewer's own capped URL, the whole prefix with the session the address names, and the viewer stays on the report (the coordinator's ruling on the same-origin figure after the file review's round 19, read over the route's other forms by a check of that build, and the file review's round 20, regression-2, with the coordinator's decision 7 on it, and tests-2; the first four forms red at dcaa80ec4, where each opened a tab at the address as written, which carries no cap, the next five red at d140285a4, where the two respelled forms opened a tab whose address kept the author's cap, the relay's route and the host-prefixed sid a tab at the address as written, and the pin the live file in the viewer, and the four forms naming what the route does not read red at bef9ff8fc, where each wore no control and opened nothing)", async (t) => {
    const key = "k" + Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);   // a page key minted at run time
    const got: Array<[string, OwnRead]> = [];
    const errs: string[] = [];
    let ran = false;
    await inBrowser(t, async (browser) => {
      ran = true;
      for (const [what, dest, kind] of OWN_FORMS) { const { read, errors } = await ownFormScene(browser, dest, key, kind); got.push([what, read]); errs.push(...errors); }
    }, { engine });
    if (!ran) return;   // no browser: inBrowser skipped the case loudly
    t.diagnostic("record " + JSON.stringify(got));
    const viewerSrc = "/file?path=" + encodeURIComponent(OWN_PIC) + "&sid=" + OWN_SID + "&cap=";
    const relaySrc = "/remote/gpu1/file?path=" + encodeURIComponent(OWN_PIC) + "&sid=" + OWN_SID + "&cap=";
    const own = (kind0: string): string => kind0 === "file" ? "the viewer's own capped /file URL" : "the viewer's own capped relay URL";
    const want = OWN_FORMS.map(([what, dest, kind]): [string, unknown] => [what, kind === "file" || kind === "relay"
      ? { gated: false, capped: what !== "an escaped route", words: "Open the picture", opened: [], base: "b.svg", shown: own(kind), back: "Back to report.md", ctrlClick: { ctrl: [true], tab: [own(kind)], stayed: "report.md" } }
      : kind === "none"
        ? { gated: false, capped: true, words: null, opened: [], base: "report.md", shown: null, back: null, ctrlClick: null }
        : { gated: true, capped: false, words: "Open the picture in a new tab at " + new URL(dest).host, opened: [new URL(dest).href], base: "report.md", shown: null, back: null, ctrlClick: null }]);
    // a tab's address read at this origin by its route and query, the whole prefix with the sid the address names, so a tab in the
    // shown file's session or at the address as written, which carries no cap, reads as itself
    const asOwn = (u: string): string => { let p = u; try { const x = new URL(u, ORIGIN); if (x.origin === new URL(ORIGIN).origin) p = x.pathname + x.search; } catch { /* read as written */ } return p.startsWith(viewerSrc) ? "the viewer's own capped /file URL" : p.startsWith(relaySrc) ? "the viewer's own capped relay URL" : u; };
    const seen = got.map(([what, r]): [string, unknown] => [what, { ...r, shown: r.shown !== null && r.shown.startsWith(viewerSrc) ? "the viewer's own capped /file URL" : r.shown !== null && r.shown.startsWith(relaySrc) ? "the viewer's own capped relay URL" : r.shown, ctrlClick: r.ctrlClick === null ? null : { ...r.ctrlClick, tab: r.ctrlClick.tab.map(asOwn) } }]);
    assert.deepEqual(seen, want, "each form: whether it waited behind its host's box (a precondition: another host's figure does, this origin's does not), whether its src carries a cap (a precondition: the cap pass caps the /file route and the relay's, leaves the escaped route's as written, and keeps the cap an author copied into a respelled route), the control's words (none for a form the viewer cannot open as shown), the tabs opened, the file the bar names, the viewer's picture and Back, and for the file and relay forms the Cmd/Ctrl-click on the picture after Back, its ctrlKey read back, one tab at the viewer's own capped URL in the session the address names and the viewer still on the report (a property pin over window.open's calls and the viewer's own DOM)");
    assert.deepEqual(errs, [], "no page errors");
  });
}
