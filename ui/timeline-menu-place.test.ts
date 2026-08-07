// Drop-down placement for the lane gear / model / effort menus. The timeline often renders as a
// short bottom band (the web shell's f-timeline iframe), and the menus are position:fixed INSIDE
// that band — so hanging them unconditionally below the anchor pushed a bottom-lane menu straight
// past the iframe's viewport: it opened, but the user saw at most a sliver (2026-08-07). menuTop
// prefers below, flips above when below can't hold the menu, and clamps on-screen when neither fits.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const FILE = path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js");
const SRC = fs.readFileSync(FILE, "utf8");
const { menuTop } = require(FILE);

test("a menu that fits below the anchor opens below it", () => {
  // tall viewport, anchor near the top: the classic desktop case is unchanged
  assert.equal(menuTop({ top: 40, bottom: 56 }, 150, 800), 60);
});

test("a menu that would clip past the viewport bottom flips ABOVE the anchor", () => {
  // a 200px bottom band with the gear on its lowest lane: below has ~30px, above has room
  assert.equal(menuTop({ top: 170, bottom: 186 }, 140, 200), 170 - 4 - 140);
});

test("a band shorter than the menu clamps the top on-screen instead of vanishing", () => {
  // neither side fits a 150px menu in a 120px band: pin toward the bottom, never above y=6,
  // so the menu's top rows stay visible and reachable
  const top = menuTop({ top: 100, bottom: 116 }, 150, 120);
  assert.equal(top, 6);
  // and a band just big enough bottom-aligns rather than hiding the head of the menu
  assert.equal(menuTop({ top: 150, bottom: 166 }, 150, 170), 170 - 6 - 150);
});

test("both the lane gear menu and the model/effort menu place through menuTop", () => {
  // the fix must cover BOTH fixed-position drop-downs; a bare `r.bottom + 4` is the bug's signature
  const opens = SRC.match(/menu\.style\.top = Math\.round\(menuTop\(r, menu\.offsetHeight \|\| 0, window\.innerHeight \|\| 9999\)\)/g) || [];
  assert.equal(opens.length, 2, "expected _openMetaMenu and _openLaneMenu to both use menuTop");
  assert.doesNotMatch(SRC, /menu\.style\.top = Math\.round\(r\.bottom \+ 4\)/);
});
