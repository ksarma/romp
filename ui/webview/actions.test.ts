// The delegate's press pulse and the handler that stands down (actions.ts delegate and flash; the acknowledgement rule
// of ui/CLAUDE.md). Every matched activation is pulsed BEFORE its handler runs (click-safe.test.ts and tab-hide.test.ts
// pin the order at the source), so a handler that declines the click it was routed — the second click of one gesture
// (render.ts `once`), the click that ends a drag-selection across a control that is also text — is where the pulse
// comes off: it removes `romp-acted` in the same task, and nothing the helper does afterwards puts it back (flash's
// timer only removes). Run in node over a DOM stand-in (there is no jsdom in this tree): a root whose click reaches
// its listeners with the pressed element as the target, elements with a class list, a data-act and closest(). The
// 300 ms waits are for flash's own 280 ms timer, the one time-based thing in the helper.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { inspect } from "node:util";
import { hideEdges, staysEnumerable } from "../test-dom-shim";
import { delegate } from "./actions";

type FakeEvent = { type: string; target: Elm; defaultPrevented: boolean; preventDefault(): void };
type Listener = (ev: FakeEvent) => void;
class Elm {
  parent!: Elm | null;
  classes = new Set<string>();
  dataset: Record<string, string | undefined> = {};
  listeners: Listener[] = [];
  offsetWidth = 0;                                   // flash reads it for the reflow that restarts the animation
  classList = {
    add: (c: string): void => { this.classes.add(c); },
    remove: (c: string): void => { this.classes.delete(c); },
    contains: (c: string): boolean => this.classes.has(c),
  };
  constructor() {
    // the up edge is non-enumerable, so an element inspects as its own projection and a failing assertion's dump stays
    // small (ui/test-dom-shim.ts says why); append's later write keeps it hidden
    Object.defineProperty(this, "parent", { value: null, writable: true, enumerable: false, configurable: true });
    hideEdges(this);
  }
  append(k: Elm): Elm { k.parent = this; return k; }
  contains(n: Elm | null): boolean { for (let p = n; p; p = p.parent) if (p === this) return true; return false; }
  closest(sel: string): Elm | null {
    assert.equal(sel, "[data-act]", "the delegate routes by data-act alone");
    for (let p: Elm | null = this; p; p = p.parent) if (p.dataset.act !== undefined) return p;
    return null;
  }
  addEventListener(type: string, cb: Listener): void { assert.equal(type, "click"); this.listeners.push(cb); }
  /** A click on this element: the target is this element and the event reaches every ancestor's listeners in turn, as a
   *  bubbling click does. */
  click(): FakeEvent {
    const ev: FakeEvent = { type: "click", target: this, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
    for (let p: Elm | null = this; p; p = p.parent) for (const cb of p.listeners) cb(ev);
    return ev;
  }
}
// delegate reads `root === document` to pick the containment check; the roots here are elements, so any object will do
(globalThis as any).document = { contains: (): boolean => false };
const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));
function control(): { root: Elm; btn: Elm } {
  const root = new Elm();
  const btn = root.append(new Elm());
  btn.dataset.act = "go";
  return { root, btn };
}

test("the pulse precedes the handler: an acting handler finds romp-acted on its element, and it stays until flash's timer", async () => {
  const { root, btn } = control();
  let seen: boolean | null = null;
  delegate(root as unknown as HTMLElement, { go: (el) => { seen = el.classList.contains("romp-acted"); } });
  btn.click();
  assert.equal(seen, true, "the pulse was on the control when the handler ran");
  assert.ok(btn.classList.contains("romp-acted"), "and stays on it after the handler returns, for the frame to paint");
  await sleep(300);
  assert.ok(!btn.classList.contains("romp-acted"), "flash's timer takes it off");
});

test("a handler that stands down takes the pulse back in the same task; the timer puts nothing back; the next click pulses as before", async () => {
  const { root, btn } = control();
  let acted = 0; let decline = true; let had: boolean | null = null;
  delegate(root as unknown as HTMLElement, { go: (el) => {
    if (decline) { had = el.classList.contains("romp-acted"); el.classList.remove("romp-acted"); return; }
    acted++;
  } });
  btn.click();
  assert.equal(acted, 0, "the handler declined");
  assert.equal(had, true, "it had a pulse to take back: the delegate added it before the handler ran");
  assert.ok(!btn.classList.contains("romp-acted"), "no pulse survives the handler's return, so no frame paints an acknowledgement of a press it ignored");
  await sleep(300);
  assert.ok(!btn.classList.contains("romp-acted"), "flash's timer only removes: nothing came back");
  decline = false;
  btn.click();
  assert.equal(acted, 1, "the next click is acted on");
  assert.ok(btn.classList.contains("romp-acted"), "and pulses as before: the stand-down cost the control nothing");
});

test("a click on nothing the map names pulses nothing: the pulse is the matched activation's alone", () => {
  const { root, btn } = control();
  const stray = root.append(new Elm());            // no data-act: closest finds none
  let acted = 0;
  delegate(root as unknown as HTMLElement, { go: () => { acted++; } });
  stray.click();
  assert.equal(acted, 0);
  assert.ok(!stray.classList.contains("romp-acted") && !btn.classList.contains("romp-acted"), "no control was activated, so none acknowledged");
  const other = root.append(new Elm()); other.dataset.act = "elsewhere";   // a data-act the map does not name
  other.click();
  assert.equal(acted, 0);
  assert.ok(!other.classList.contains("romp-acted"), "an act without a handler is not an activation: no pulse");
});

// The stand-in's elements inspect as their own projection, never as the tree: parent, the class set, dataset, the
// listener list and classList are non-enumerable, so a failing assertion's dump of an element is a few lines, not the
// root and everything under it (ui/test-dom-shim.ts says why; ui/test-dom-shim.test.ts keeps the ratchet).
test("stand-in: an element enumerates its primitives alone and inspects without its edges", () => {
  const { root, btn } = control();
  btn.classList.add("romp-acted");
  for (const n of [root, btn]) {
    const o = n as unknown as Record<string, unknown>;
    assert.ok(Object.keys(o).every((k) => staysEnumerable(o[k])), "only primitives enumerate: " + Object.keys(o).join(","));
    const dump = inspect(n, { compact: false, customInspect: false, depth: 1000, maxArrayLength: Infinity, showHidden: false, showProxy: false, sorted: true, getters: true });
    assert.ok(!dump.includes("parent") && !dump.includes("listeners"), "no edge in the dump");
  }
  assert.ok(btn.parent === root && root.contains(btn) && btn.closest("[data-act]") === btn, "the tree is reachable as before");
});
