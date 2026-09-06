// THE SECTION SNAPSHOT, VIEW HELPERS (tab-snapshot-view.ts; the round-2 review of the tabsnapshot branch):
// the pane-side rules render.ts applies to the snapshot, pure so they execute here without a DOM. The
// model and its words are tab-snapshot.ts; the render.ts pins are tab-snapshot-pane.test.ts. Synthetic
// only: the notes-api demo world (web / api / tests), placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { rowStillOpen } from "./tab-snapshot-view";

test("a row whose session left the strip mid-press opens nothing (round 2): a frame's row needs its session, a placeholder's row its meta, and a closing tab is neither", () => {
  // click safety keeps the pressed row in the DOM until the release, so a session dismissed between mousedown
  // and mouseup (the kernel's closed frame, a tabOrder push without it) is still under the click. setActive on
  // that id found tabMeta still holding it (dismissSession leaves tabMeta to the next tabOrder frame) and put
  // up an "opening…" loader, composer enabled, for a session that never arrives.
  const frame = { loading: false }, placeholder = { loading: true };
  assert.equal(rowStillOpen(frame, true, true, false), true, "a live row with its session: opens");
  assert.equal(rowStillOpen(frame, false, true, false), false, "its session gone, its meta lingering (closed frame before the next tabOrder push): nothing opens");
  assert.equal(rowStillOpen(frame, false, false, false), false, "session and meta gone (a tabOrder push without it): nothing opens");
  assert.equal(rowStillOpen(placeholder, false, true, false), true, "a placeholder row (no frame yet) with its meta: opens, the loading branch is its state");
  assert.equal(rowStillOpen(placeholder, false, false, false), false, "a placeholder whose meta left: nothing opens");
  assert.equal(rowStillOpen(placeholder, true, false, false), true, "a placeholder whose frame landed mid-press: the session is there, it opens");
  assert.equal(rowStillOpen(frame, true, true, true), false, "the user closed it (closingTabs): nothing opens, whatever the maps still hold");
  assert.equal(rowStillOpen(undefined, true, true, false), true, "no model row for the id (never expected): the session decides");
  assert.equal(rowStillOpen(undefined, false, true, false), false);
});
