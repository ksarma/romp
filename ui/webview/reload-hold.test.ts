// The chat page's hold on the reload core (reload-hold.ts): pure, so the word's truth table runs executably, and
// the wiring is pinned at the source level the way the other webview tests pin render.ts (no jsdom harness): the
// three places pendingShips changes publish it, the load-time publish, and the core's read of the word. The
// core's own deferral (the re-check timer, the deadline) runs in node in tests/test_dashboard_auto_reload.py;
// the served order (the heal, then the reload) is tests/test_ship_reship.py ServedWedge. Synthetic only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { publishReloadHold, type ReloadHoldHost } from "./reload-hold";

const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the word is true while any ship awaits its ack and false otherwise, and it exists once published", () => {
  const w: ReloadHoldHost = {};
  assert.equal("__rompReloadHold" in w, false, "nothing published yet");
  assert.equal(publishReloadHold(0, w), false);
  assert.equal(w.__rompReloadHold, false, "published as false, not left unset: the core's read is a strict === true");
  assert.equal(publishReloadHold(1, w), true);
  assert.equal(w.__rompReloadHold, true);
  assert.equal(publishReloadHold(3, w), true, "more ships, still one hold");
  assert.equal(publishReloadHold(0, w), false, "the last ack clears it");
  assert.equal(w.__rompReloadHold, false);
});

test("render.ts publishes it at every change to pendingShips and once at load", () => {
  // a ship starts
  assert.match(RENDER, /pendingShips\.set\(id, list\);\n\s*publishReloadHold\(pendingShips\.size\);/);
  // an ack, a nack or a FileReader failure retires one
  assert.match(RENDER, /if \(!list\.length\) pendingShips\.delete\(id\);\n\s*publishReloadHold\(pendingShips\.size\);/);
  // the user dismisses a pending chip
  assert.match(RENDER, /if \(!list\.length && id\) pendingShips\.delete\(id\);\n\s*publishReloadHold\(pendingShips\.size\);/);
  // the load-time publish follows the loss toast's block, so a ship the page lost never holds a reload owed at startup
  assert.match(RENDER, /shipsInFlight: \[\] \}\);\n\s*\}\n\s*\}\n\} catch \{ \/\* ignore \*\/ \}\n(\/\/.*\n)*publishReloadHold\(pendingShips\.size\);/);
  assert.equal((RENDER.match(/publishReloadHold\(/g) || []).length, 4, "four publishes: three changes and the load");
});

test("the reload core reads the word as its 'ships' hold, after the gesture holds, and defers instead of reloading", () => {
  const core = KERNEL.slice(KERNEL.indexOf("/*reload-core*/"), KERNEL.indexOf("/*end-reload-core*/"));
  assert.ok(core.length > 0, "the core's anchors exist");
  assert.match(core, /return 'composer';\}catch\(e\)\{\}\ntry\{if\(window\.__rompReloadHold===true\)return 'ships';\}catch\(e\)\{\}/);
  assert.match(core, /if\(b==='ships'\)b=shipsHold\(\);/, "tryFire defers on the hold instead of reloading now");
  assert.match(core, /HOLD_MAX=60000/, "the bounded wait");
});
