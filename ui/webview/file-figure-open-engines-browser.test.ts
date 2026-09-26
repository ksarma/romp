// The one gate's tap cells in WebKit and Firefox, for the link-navigation follow-on of plans/markdown-viewer.md (the file review's
// round 17, tests-1 with regression-1, and the coordinator's decisions 1 to 3 on it): the cells are file-figure-open-taps.ts's, the
// set file-figure-open-browser.test.ts runs in Chromium, each engine launched through real-viewer-leg.ts's inBrowser with the engine
// named. WebKit runs them on a phone's pages and on a hybrid page (hasTouch with a mouse), on the chat modal and the Files pane, and
// Firefox on the hybrid page alone, since Playwright's Firefox takes no isMobile. The WebKit engine is Playwright's on Linux under
// touch emulation, a stand-in for WebKitGTK, and presumably WPE, on a touchscreen; no cell claims iOS Safari or the iPhone, a cell
// run under a phone's pages included (WebKit's iOS source gives an iPhone tap's click the touch's own pointerId, so the gate's own
// record serves there, read and not run on a device). In that WebKit a tap's click carries pointerId 1 of type mouse while its press
// carried the touch's, each tap cell asserting that shape as its precondition, and the click finds its press in the gate's one-click
// slot; red at 0ab74924c, where the gate matched a click to its press by pointerId alone, so every tap on a loaded web picture or its
// control opened nothing, the double tap too, and the stale-record cells are red there as well, their reads a private witness kept
// out of the tree. Firefox gives a tap's click its press's pointerId (0), so its cells read the same at that head as at the fix, by
// design, recorded beside WebKit's; its double tap and WebKit's each assert their engine's own details (1 and 1), the second tap read
// at its own start and opening once after the first tap's reveal.
// This leg stays off the shared roster of browser legs that PR 887 brings: that roster's job installs Chromium alone, so a WebKit or
// Firefox test in a rostered file would not run there, and under that convention this leg is an exclusions line, with that reason.
// Skips LOUDLY without a playwright browser (in CI the Test step runs before the job's Chromium install, and no job installs Firefox
// or WebKit, so the leg skips there; the launch is real-viewer-leg.ts's inBrowser, the shared helper); file-view-outline.test.ts
// drives WebKit's order, the stale records and the clicks by no pointer over the stand-in in CI. Synthetic values only: the
// notes-api world, a placeholder session id, example.test addresses, /repo/notes-api paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inBrowser } from "./real-viewer-leg";
import { tapCells, type TapDevice, type TapEngine, type TapSurface } from "./file-figure-open-taps";

const ON: Record<TapDevice, string> = { phone: "a phone's pages (hasTouch and isMobile at a device scale of 1, the kernel's viewport meta)", hybrid: "a hybrid page (hasTouch with a mouse)" };
for (const [engine, devices] of [["webkit", ["phone", "hybrid"]], ["firefox", ["hybrid"]]] as Array<[TapEngine, TapDevice[]]>) for (const device of devices) for (const surface of ["chat", "pane"] as TapSurface[]) {
  const named = engine === "webkit" ? "WebKit (Playwright's, on Linux under touch emulation)" : "Firefox";
  const red = engine === "webkit"
    ? "red at 0ab74924c, whose gate matched a click to its press by pointerId alone: every tap opened nothing, the double tap too, and " + (device === "hybrid" ? "the right press's and the drag's cells red there too, their reads a private witness kept out of the tree; " : "") + "the key cells green there by design"
    : "every cell reading the same at 0ab74924c as at the fix, by design, Firefox's tap click carrying its press's pointerId";
  test("in " + named + " on " + ON[device] + ", the " + (surface === "chat" ? "chat modal" : "Files pane") + ": the one gate's tap cells (the file review's round 17, tests-1 with regression-1): a tap on a loaded remote picture with its control in view opens once, on its control once, on a remote picture that wears the mark once; with the control out of view the first tap opens nothing and reveals it and the next opens once; a double tap there opens once, " + (engine === "webkit" ? "WebKit's" : "Firefox's") + " two clicks each of detail 1; under the text-size flyout or the Outline popover a tap opens nothing and closes it and the next opens once; " + (device === "hybrid" ? "after a right press of the mouse, or a mouse drag of the picture, with the control shown, then the flyout over the control, a tap opens nothing and the next opens once; " : "") + "Enter on the control opens once, after a refused tap too; a press with no click (a script's pointerdown and pointerup, standing in) begun out of view then Enter in view opens once, and one begun shown then the flyout over the control then a script's click opens nothing (" + red + "; the Enter cells red under a gate that reads a key's click as a pointer's, the press cells under one that lets a key's or a script's click read the slot with the keydown's clear dropped)", { timeout: 300000 }, async (t) => {
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
