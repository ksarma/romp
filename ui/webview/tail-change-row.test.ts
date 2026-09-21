// The transcript's tail names itself when it changes height (T262f, the user 2026-09-08). Chrome keeps a bottom reader
// at the bottom by itself when ANY element is appended at the end of #content and clamps them back when it is removed
// (measured: a plain 95 px div, scrollTop +95/-95 with no pane write), so a tail element that toggles under a bottom
// reader flaps the text by its height with no scrollwrite row at all — the shape of the user's laptop rows. The
// scroll rows cannot say WHICH element flapped; this breadcrumb, filed by the active view's ResizeObserver and by
// the live-ask host's, names it (class list or "live-ask") with the height delta and the recorded follow mode.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { tailChangeRow, tailLabel } from "./scroll-write";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const SID = "11111111-2222-4333-8444-000000000201";

test("the row names the tail element, the delta and the follow mode; the label is bounded", () => {
  assert.deepEqual(tailChangeRow(SID, -95, "turn turn-thinking", true, 5000, 600),
                   { sid: SID, dh: -95, last: "turn turn-thinking", stick: true, sh: 5000, ch: 600 });
  assert.equal(tailChangeRow(SID, 12, "x".repeat(200), false).last.length, 60);
  assert.deepEqual(tailChangeRow(SID, 3, "live-ask", false), { sid: SID, dh: 3, last: "live-ask", stick: false, sh: 0, ch: 0 });
});

test("the tail label is the last child that is not a virtualization spacer", () => {
  assert.equal(tailLabel([{ className: "turn turn-user" }, { className: "turn turn-assistant" }, { className: "tx-spacer tx-spacer-bot" }]), "turn turn-assistant");
  assert.equal(tailLabel([{ className: "tx-spacer tx-spacer-top" }]), "");
  assert.equal(tailLabel([]), "");
});

test("with a unit predicate the tail is the last child that carries a unit: a hover's rail band, the thread's last child with none, is not the tail (PR E, the maintainer's round 2 ruling; the spacer rule stands for callers that pass none)", () => {
  // drawRailBand appends the band to the thread as its last child with no data-unit; the pane passes render.ts unitOfNode's predicate
  type C = { className: string; unit?: number };
  const isUnit = (c: C) => c.unit != null;
  const children: C[] = [{ className: "tx-spacer tx-spacer-top" }, { className: "turn turn-user", unit: 5 }, { className: "turn turn-assistant", unit: 6 }, { className: "rail-band rail-band-local" }];
  assert.equal(tailLabel(children, isUnit), "turn turn-assistant", "the band is passed over: the tail is the last unit");
  assert.equal(tailLabel(children), "rail-band rail-band-local", "the spacer rule alone would name the band (the old reading, kept for callers with no predicate)");
  assert.equal(tailLabel(children.concat([{ className: "tx-spacer tx-spacer-bot" }]), isUnit), "turn turn-assistant", "a bottom spacer is passed over too");
  // a view with NO unit-carrying child: the spacer rule stands in for the whole scan (a second pass after the unit pass, never a per-child
  // OR, which would name a band beside units and undo the case above), so the row names the placeholder or the loader as it did before the
  // predicate (the maintainer's round 3 ruling C: with the predicate alone the label was "" exactly where a transcript-less view can report);
  // a band as the only non-spacer child of a unit-less view is then the answer too, re-ruled from the round-2 pin that read "" for it.
  // One more shape empties a view and is outside this pin by construction: a view with no top spacer is empty between trimUnitsFrom's last
  // removal and the same task's appendItem (the tail paint re-rendering every unit of a short transcript), a same-task transient that no read
  // observes (showActive's read of an empty view runs in its own task, and an observer delivers between tasks), so the loader is never
  // appended for it and no row can name it; inferred from the code, not executed (the second closing lens over the closing pass)
  assert.equal(tailLabel([{ className: "tx-empty" }], isUnit), "tx-empty", "the empty transcript's placeholder (its swirl removing itself on error is a height change)");
  assert.equal(tailLabel([{ className: "tx-loading" }], isUnit), "tx-loading", "the deferred build's loading hint, the only child of a non-empty session's view for one frame (render.ts appends it to an EMPTY view, never under a spacer); a row can name it after a rerender of every view (rerenderAll, whose callers are an external settings change of any kind, the compact toggle among them, and a self-host name adopted after views were built), which empties every view with `shown` kept, while a first visit's view is not yet shown and files no tailchange row");
  assert.equal(tailLabel([{ className: "tx-spacer tx-spacer-top" }, { className: "rail-band" }], isUnit), "rail-band", "no unit anywhere: the last child that is not a spacer, whatever it is");
  assert.equal(tailLabel([{ className: "tx-spacer tx-spacer-top" }], isUnit), "", "spacers alone: no tail under either rule");
});

test("render.ts files the row from both tail observers, beside the tail-shrink rule, through the capped diag path", () => {
  assert.match(RENDER, /import \{ ScrollDiagBudget, classifyScroll, scrollWriteRow, tailChangeRow, tailLabel, spacerRow, readScrollDiagCap, summarizeTailMutations, tailMutRow, unitChangeRow, unitChanges, boxChanges, boxLabel, BOX_FROM_TAIL \} from "\.\/scroll-write";/);   // + spacerRow, readScrollDiagCap (T262j)
  assert.match(RENDER, /function scrollDiagRow\(kind: "scrollwrite" \| "scrollgesture" \| "tailchange" \| "spacer" \| "tailmut" \| "unitchange" \| "regionask" \| "landmiss", data: any\): void \{/);   // + spacer (T262j)
  // the view's tail by the one unit predicate (render.ts unitOfNode, the trim's and the measure's): a hover's band as the last child is not
  // the tail this row names (PR E, the maintainer's round 2 ruling)
  assert.match(RENDER, /if \(content && lastH >= 0 && activeId === id && view\.shown && h !== lastH\)\s*\n\s*scrollDiagRow\("tailchange", tailChangeRow\(id, h - lastH, tailLabel\(view\.el\.children, \(c\) => unitOfNode\(c\) >= 0\), view\.stick, content\.scrollHeight, content\.clientHeight\)\);/);
  assert.match(RENDER, /if \(content && tailLastH >= 0 && v && v\.shown && h !== tailLastH\)\s*\n\s*scrollDiagRow\("tailchange", tailChangeRow\(activeId \|\| "", h - tailLastH, "live-ask", v\.stick, content\.scrollHeight, content\.clientHeight\)\);/);
  assert.equal((RENDER.match(/"tailchange"/g) || []).length, 3, "the kind in the router's union and the two filings");
});
