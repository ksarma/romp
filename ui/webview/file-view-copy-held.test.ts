// pressHold (actions.ts): the hold that keeps a pressed control alive across a rebuild the press did not ask for
// (review of Slice 3 of plans/markdown-viewer.md, round 1, 2026-09-08: a fence's Copy in the viewer lost its click when
// a reload's fetch landing swapped the body between the mousedown and the mouseup; a removed pressed node dispatches no
// click at all, so the swap has to wait). The helper run in node over plain EventTargets, the surface and the release
// target both fakes: defer runs at once when nothing is pressed; a press parks it and the release runs it, after the
// click that follows the pointerup, once; the newest parked run replaces an older one; pointercancel and blur release
// too; the release listeners leave with the release; a second pointerdown under one press installs nothing twice.
// The browser leg (file-view-copy-held-browser.test.ts) has the viewer itself. The zero-timer waits below are ordering
// (the helper's own zero timer was queued first, so it has run), not sleeps. The arrays are compared through slice():
// node's deepEqual narrows the array it is given to never[] after a comparison with [], and the later pushes then
// fail to typecheck.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { pressHold } from "./actions";

/** An EventTarget that counts its listener installs and removals, so a leak shows. */
class Counting extends EventTarget {
  adds = 0; removes = 0;
  addEventListener(t: string, l: any, o?: any): void { this.adds++; super.addEventListener(t, l, o); }
  removeEventListener(t: string, l: any, o?: any): void { this.removes++; super.removeEventListener(t, l, o); }
}
const afterTimers = (): Promise<void> => new Promise((r) => setTimeout(r, 0));
const fire = (t: EventTarget, type: string): boolean => t.dispatchEvent(new Event(type));

test("nothing pressed: defer runs at once, synchronously", () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  let ran = 0;
  hold.defer(() => { ran++; });
  assert.equal(ran, 1, "the run happened in the call");
  assert.equal(hold.held(), false);
  assert.equal(release.adds, 0, "no release listener is installed while nothing is pressed");
});

test("a press parks the run; the release runs it once, after the click that follows the pointerup", async () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  const order: string[] = [];
  fire(surface, "pointerdown");
  assert.equal(hold.held(), true, "the press is held");
  hold.defer(() => { order.push("run"); });
  assert.deepEqual(order.slice(), [], "the run waits for the release");
  // the release: pointerup, then the click the browser dispatches right after it in the same task
  fire(release, "pointerup");
  assert.equal(hold.held(), false, "released");
  surface.addEventListener("click", () => { order.push("click"); });
  fire(surface, "click");
  assert.deepEqual(order.slice(), ["click"], "the click lands before the parked run (the run is on a zero timer)");
  await afterTimers();
  assert.deepEqual(order.slice(), ["click", "run"], "then the run, once");
  await afterTimers();
  assert.deepEqual(order, ["click", "run"], "and never again");
});

test("the newest parked run replaces an older one under the same press", async () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  const ran: string[] = [];
  fire(surface, "pointerdown");
  hold.defer(() => { ran.push("first"); });
  hold.defer(() => { ran.push("second"); });
  fire(release, "pointerup");
  await afterTimers();
  assert.deepEqual(ran, ["second"], "the landing the next one overtook paints nothing");
});

test("pointercancel and blur release the hold too", async () => {
  for (const type of ["pointercancel", "blur"]) {
    const surface = new EventTarget(); const release = new Counting();
    const hold = pressHold(surface, release);
    let ran = 0;
    fire(surface, "pointerdown");
    hold.defer(() => { ran++; });
    fire(release, type);
    assert.equal(hold.held(), false, type + " releases");
    await afterTimers();
    assert.equal(ran, 1, "and the parked run ran after " + type);
  }
});

test("the release listeners are installed at the press and removed at the release; a second pointerdown installs nothing twice", () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  fire(surface, "pointerdown");
  assert.equal(release.adds, 3, "pointerup, pointercancel, blur");
  fire(surface, "pointerdown");   // a second pointer under the same press
  assert.equal(release.adds, 3, "installed once per press");
  assert.equal(hold.held(), true);
  fire(release, "pointerup");
  assert.equal(release.removes, 3, "all three leave with the release");
  fire(release, "pointerup");   // a stray release after the release: nothing to do, nothing thrown
  assert.equal(release.removes, 3);
  assert.equal(hold.held(), false);
});

test("a release with nothing parked runs nothing, and a defer after it runs at once again", async () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  fire(surface, "pointerdown");
  fire(release, "pointerup");
  await afterTimers();
  let ran = 0;
  hold.defer(() => { ran++; });
  assert.equal(ran, 1, "after the release, defer is immediate again");
});

test("a pointerdown a child stopped from bubbling still marks the press (the surface listens in the capture phase)", () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  // a plain EventTarget has no tree, so the capture-phase claim is pinned at the source instead
  const fs = require("node:fs") as typeof import("node:fs");
  const path = require("node:path") as typeof import("node:path");
  const src = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "actions.ts"), "utf8");
  assert.match(src, /surface\.addEventListener\("pointerdown", \(\) => \{[\s\S]*?\}, true\);/, "capture phase");
  fire(surface, "pointerdown");
  assert.equal(hold.held(), true);
  fire(release, "pointerup");
});
