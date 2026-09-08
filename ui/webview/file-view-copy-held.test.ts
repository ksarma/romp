// pressHold (actions.ts): the hold that keeps a pressed control alive across a rebuild the press did not ask for
// (review of Slice 3 of plans/markdown-viewer.md, round 1, 2026-09-08: a fence's Copy in the viewer lost its click when
// a reload's fetch landing swapped the body between the mousedown and the mouseup; a removed pressed node dispatches no
// click at all, so the swap has to wait). The helper run in node over plain EventTargets, the surface and the release
// target both fakes: defer runs at once when nothing is pressed; a press parks it and the release runs it, after the
// click that follows the pointerup, once; the newest parked run replaces an older one; pointercancel, contextmenu and
// blur release too; the release listeners leave with the release; a second pointerdown under one press installs nothing
// twice. Round 2 of the same review: only the PRIMARY button holds (a right press's release commonly never reaches the
// page, the native menu takes it, so a hold taken on one parked the landing until the reader's next click); a press
// that begins before the release's zero timer fires parks the run again instead of swapping the surface under the new
// press; and defer's promise settles with the run, so a caller's chain sees a parked run's throw.
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
/** A pointerdown carrying its button, as a browser's PointerEvent does (0 the primary: left, pen, finger; 1 middle; 2 right). */
const press = (t: EventTarget, button = 0): boolean => t.dispatchEvent(Object.assign(new Event("pointerdown"), { button }));

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
  press(surface);
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
  press(surface);
  hold.defer(() => { ran.push("first"); });
  hold.defer(() => { ran.push("second"); });
  fire(release, "pointerup");
  await afterTimers();
  assert.deepEqual(ran, ["second"], "the landing the next one overtook paints nothing");
});

test("pointercancel, contextmenu and blur release the hold too", async () => {
  for (const type of ["pointercancel", "contextmenu", "blur"]) {
    const surface = new EventTarget(); const release = new Counting();
    const hold = pressHold(surface, release);
    let ran = 0;
    press(surface);
    hold.defer(() => { ran++; });
    fire(release, type);
    assert.equal(hold.held(), false, type + " releases");
    await afterTimers();
    assert.equal(ran, 1, "and the parked run ran after " + type);
  }
});

test("only the primary button holds: a right or middle press parks nothing, and defer runs at once under it", () => {
  for (const button of [2, 1]) {
    const surface = new EventTarget(); const release = new Counting();
    const hold = pressHold(surface, release);
    press(surface, button);
    assert.equal(hold.held(), false, "button " + button + " is no press to hold for (its release may never reach the page)");
    assert.equal(release.adds, 0, "and installs no release listener");
    let ran = 0;
    hold.defer(() => { ran++; });
    assert.equal(ran, 1, "the run happened in the call under button " + button);
  }
  // a pointerdown with no button at all (a synthetic Event) is not a press either
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  fire(surface, "pointerdown");
  assert.equal(hold.held(), false);
});

test("a press that begins before the release's zero timer fires parks the run again: it runs after THAT press's click", async () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  const order: string[] = [];
  surface.addEventListener("click", () => { order.push("click"); });
  press(surface);
  hold.defer(() => { order.push("run"); });
  fire(release, "pointerup"); fire(surface, "click");          // press 1 ends: the run is on the zero timer
  press(surface);                                              // press 2 begins before the timer fires
  assert.equal(hold.held(), true, "press 2 is held");
  await afterTimers();
  assert.deepEqual(order.slice(), ["click"], "the timer found the surface pressed again and did not swap it under press 2");
  fire(release, "pointerup"); fire(surface, "click");          // press 2 ends: its click lands on the surface it pressed
  assert.deepEqual(order.slice(), ["click", "click"], "press 2's click landed before the run");
  await afterTimers();
  assert.deepEqual(order.slice(), ["click", "click", "run"], "then the run, once");
  await afterTimers();
  assert.deepEqual(order, ["click", "click", "run"]);
});

test("...unless a newer run is parked under the new press already: then the older one paints nothing", async () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  const ran: string[] = [];
  press(surface);
  hold.defer(() => { ran.push("first"); });
  fire(release, "pointerup");
  press(surface);
  hold.defer(() => { ran.push("second"); });                   // a newer landing, under press 2
  await afterTimers();
  assert.deepEqual(ran.slice(), [], "nothing ran under press 2");
  fire(release, "pointerup");
  await afterTimers();
  assert.deepEqual(ran, ["second"], "the newest is what shows; the overtaken one never ran");
});

test("defer's promise settles with the run: resolved once it ran, rejected with what it threw, at once or at the release", async () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  // nothing pressed: the run happens in the call, and the promise reports it
  await hold.defer(() => {});
  await assert.rejects(hold.defer(() => { throw new Error("paint failed at once"); }), /paint failed at once/);
  // pressed: the promise waits for the release, then reports the run
  press(surface);
  let ran = 0;
  const ok = hold.defer(() => { ran++; });
  const bad = hold.defer(() => { throw new Error("paint failed at the release"); });   // replaces `ok`, which resolves
  await ok;
  assert.equal(ran, 0, "the replaced run never ran, and its promise did not hang");
  let settled = false;
  void bad.catch(() => { settled = true; });
  await afterTimers();
  assert.equal(settled, false, "the parked run's promise is still pending under the press");
  fire(release, "pointerup");
  await assert.rejects(bad, /paint failed at the release/, "a caller's catch sees the throw from the release");
});

test("the release listeners are installed at the press and removed at the release; a second pointerdown installs nothing twice", () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  press(surface);
  assert.equal(release.adds, 4, "pointerup, pointercancel, contextmenu, blur");
  press(surface);   // a second pointer under the same press
  assert.equal(release.adds, 4, "installed once per press");
  assert.equal(hold.held(), true);
  fire(release, "pointerup");
  assert.equal(release.removes, 4, "all four leave with the release");
  fire(release, "pointerup");   // a stray release after the release: nothing to do, nothing thrown
  assert.equal(release.removes, 4);
  assert.equal(hold.held(), false);
});

test("a release with nothing parked runs nothing, and a defer after it runs at once again", async () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  press(surface);
  fire(release, "pointerup");
  await afterTimers();
  let ran = 0;
  hold.defer(() => { ran++; });
  assert.equal(ran, 1, "after the release, defer is immediate again");
});

test("the surface listens for the press in the capture phase, and the release target for the pointer's release; blur at the target only", () => {
  const surface = new EventTarget(); const release = new Counting();
  const hold = pressHold(surface, release);
  // a plain EventTarget has no tree, so the capture-phase claims are pinned at the source instead: a child that stops
  // a pointerdown or a pointerup from bubbling can hide neither the press nor the release, and the blur listener is
  // not in the capture phase (it would fire for the focus every press moves)
  const fs = require("node:fs") as typeof import("node:fs");
  const path = require("node:path") as typeof import("node:path");
  const src = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "actions.ts"), "utf8");
  assert.match(src, /surface\.addEventListener\("pointerdown", \(ev\) => \{[\s\S]*?\}, true\);/, "the press, capture phase");
  assert.match(src, /const POINTER_RELEASE = \["pointerup", "pointercancel", "contextmenu"\];/);
  assert.match(src, /const CAPTURE = \{ capture: true \};/);
  assert.match(src, /for \(const t of POINTER_RELEASE\) release\.addEventListener\(t, onRelease, CAPTURE\);/, "the pointer's release, capture phase");
  assert.match(src, /for \(const t of POINTER_RELEASE\) release\.removeEventListener\(t, onRelease, CAPTURE\);/, "removed with the same options");
  assert.match(src, /release\.addEventListener\("blur", onRelease\);/, "blur at the target");
  press(surface);
  assert.equal(hold.held(), true);
  fire(release, "pointerup");
});
