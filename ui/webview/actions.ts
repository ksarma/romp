// Click-safe, always-acknowledged actions for the romp dashboard.
//
// WHY THIS EXISTS — the "I had to click it several times" bug.
// The dashboard re-renders on every kernel push: a 0.5–3s backstop poll, PLUS an
// immediate push on each SDK stream event and on every hook /tick (turn ended,
// prompt landed, postal message). Surfaces that rebuild their DOM wholesale
// (renderTabs()'s `#tabs`.replaceChildren(), the sessions list's
// `#fleet-list`.replaceChildren()) DESTROY and recreate the very node you are
// clicking. A native `click` fires on the nearest common ancestor of the mousedown
// and mouseup targets, and a pressed node that a rebuild removed before the mouseup
// has none, so the click is silently dropped. While a session works the pushes are
// frequent, so the drop is frequent: the button feels dead until you happen to
// click in a gap between rebuilds.
//
// THE RULE (see ui/CLAUDE.md, "Buttons must stay click-safe across re-renders…"):
//   1. Never hang an action on a node you rebuild. Put the action on a STABLE
//      ancestor (the container fetched by id survives replaceChildren(); only its
//      children are swapped) and key it off a `data-act` attribute. The listener
//      then survives every rebuild BETWEEN clicks, and a press released over a
//      sibling of the pressed node still dispatches a click, to their nearest common
//      ancestor, which routes to a control only when that ancestor is inside one
//      (the ✕ inside a tab released over the tab's label). What it does not cover: a
//      pressed node REMOVED or replaced before the mouseup dispatches no click that
//      names a control (none at all in most shapes; at most one targeted at the
//      container itself; probed with real input events in headless Chromium 151 and
//      Firefox 153, 2026-09-08), so a rebuild that can land DURING a press needs the
//      technique below (pressHold) as well.
//   2. Every activation gives IMMEDIATE feedback (a press flash), independent of
//      the kernel round-trip, so the user always sees the click registered — then
//      any dialog / error / result follows. A button that "does nothing visible
//      yet" is the other half of the multi-click problem: the user re-clicks
//      because nothing told them the first one took.
//
// delegate() does both: one listener per stable root, `data-act` dispatch, and an
// automatic feedback flash on every matched activation.
//
// For full-canvas redraw surfaces (the SVG timeline) where threading every action
// param through data-attrs is impractical, and for a surface whose children an
// event with no gesture behind it replaces (the file viewer's body under a reload),
// the sibling technique is to hold the rebuild while a pointer is pressed over the
// surface, flushing it on release, so the pressed element survives until the click
// completes: the timeline's `_pointerHeld` guard (ui/romp-timeline-view.js), and
// pressHold below for the TypeScript surfaces.

export type ActionHandler = (el: HTMLElement, ev: Event) => void;

// Mark the activated control so the user sees the press took, even before the
// kernel responds. CSS animates `.romp-acted` (a brief press pulse). Safe if the
// node is rebuilt before the timer fires — removing a class off a detached node is
// a no-op. Re-triggered cleanly on a rapid re-click via a forced reflow.
export function flash(el: HTMLElement): void {
  el.classList.remove("romp-acted");
  void el.offsetWidth; // reflow so the animation restarts on a fast second click
  el.classList.add("romp-acted");
  setTimeout(() => el.classList.remove("romp-acted"), 280);
}

// Install ONE delegated click listener on a stable root. `handlers` maps a
// `data-act` value to its action. Children carry `data-act="<name>"` plus whatever
// data-* the handler needs (data-id, data-sid, …); they may be freely rebuilt. The
// nearest ancestor WITH a data-act wins, so a control nested inside a larger
// clickable row (e.g. a ✕ inside a tab) routes to its own action without needing
// stopPropagation. Call once per root — never inside a render loop.
export function delegate(root: HTMLElement | Document, handlers: Record<string, ActionHandler>): void {
  root.addEventListener("click", (ev) => {
    const start = ev.target as Element | null;
    const el = start && typeof start.closest === "function"
      ? (start.closest("[data-act]") as HTMLElement | null)
      : null;
    if (!el) return;
    const within = root === document ? document.contains(el) : (root as HTMLElement).contains(el);
    if (!within) return;
    const act = el.dataset.act;
    if (!act) return;
    const h = handlers[act];
    if (!h) return;
    flash(el);
    h(el, ev);
  });
}

// Hold a rebuild while a pointer is pressed over `surface`, and run it on the release (the second technique above, as
// a helper; the timeline's `_pointerHeld` guard, 2026-09-08). For a surface whose children are REPLACED by an event
// that is not the person's own gesture while a press may be under way on one of them: the file viewer's body when a
// reload the Comments panel's poll asked for lands (a session wrote the note being read) and renderBody swaps every
// fence and its Copy button. Delegation does not cover that case (header): the pressed node has to survive until the
// press ends, so the swap waits.
//   - pointerdown on the surface, in the capture phase (a child that stops propagation cannot hide the press), marks
//     it held, for the PRIMARY button only (`button === 0`: a mouse's left button, a pen or a finger). A right or middle
//     press yields no click, so nothing needs holding, and a right press often yields no pointerup either: Chromium on
//     Linux and macOS opens the native context menu on the mousedown and the menu takes the release, so a hold taken
//     on one stood until the reader's next click anywhere, a landing parked under it (the Slice 3 review, round 2).
//   - The release: pointerup, pointercancel or contextmenu on `release` (the window, in the capture phase: a press
//     begun inside a surface commonly ends outside it, and a child that stops the pointerup's propagation cannot hide
//     the release; a contextmenu means the browser ended the press itself, ctrl+click on macOS and a long press on a
//     touch screen among the primary-button ways there, and no click follows it), and the window's blur (a release in
//     another frame never reaches this one; the timeline's lesson, 2026-06-25), at the target only: a capture-phase blur
//     listener would fire for the focus that every press moves. The release listeners are installed at the press and
//     removed at the release, so a surface that comes and goes (a viewer per open) leaves nothing behind.
//   - defer(run) runs `run` at once when nothing is pressed, else parks it for the release. A later defer under the
//     same press REPLACES the parked run: a landing the next one overtook paints nothing, the newest is what shows.
//     The promise it returns settles with the run: resolved once it has returned (or was replaced), rejected with what
//     it threw, so a caller's chain (the viewer's fetch, whose catch paints the failure in the body) sees a throw from
//     a run that ran at the release as it sees one from a run that ran at once; a failure never ends in a timer.
//   - The parked run goes on a zero timer at the release rather than running inside the pointerup listener: the
//     click dispatches synchronously after the pointerup (pointerup, mouseup, click, one input task), and the run
//     must come after it, as the timeline's draw does. The timer reads the hold again: a press that begins before it
//     fires (Chromium runs a pending input before a due timer, so a second press inside a busy stretch lands first)
//     parks the run again, unless a newer one is parked under the new press already, rather than swapping the surface
//     under that press and losing ITS click. Event-based (the press's own events); no time heuristic.
export type PressHold = { held(): boolean; defer(run: () => void): Promise<void> };
type Parked = { run: () => void; resolve: () => void; reject: (err: unknown) => void };
const POINTER_RELEASE = ["pointerup", "pointercancel", "contextmenu"];   // in the capture phase on `release`; blur at the target
// The options object for both the install and the removal: node's EventTarget (v22) does not match a boolean `true` on
// removal against a listener installed with one, so the helper's node tests would see the listener stay; browsers take both.
const CAPTURE = { capture: true };
export function pressHold(surface: EventTarget, release: EventTarget = window): PressHold {
  let held = false;
  let parked: Parked | null = null;
  const settle = (p: Parked): void => {
    try { p.run(); } catch (err) { p.reject(err); return; }
    p.resolve();
  };
  const onRelease = (): void => {
    for (const t of POINTER_RELEASE) release.removeEventListener(t, onRelease, CAPTURE);
    release.removeEventListener("blur", onRelease);
    held = false;
    const p = parked; parked = null;
    if (p) setTimeout(() => {
      if (!held) settle(p);
      else if (parked) p.resolve();   // a newer run is parked under the new press: this one paints nothing
      else parked = p;                // parked again, for the new press's release
    }, 0);
  };
  surface.addEventListener("pointerdown", (ev) => {
    if (held || (ev as PointerEvent).button !== 0) return;
    held = true;
    for (const t of POINTER_RELEASE) release.addEventListener(t, onRelease, CAPTURE);
    release.addEventListener("blur", onRelease);
  }, true);
  return {
    held: () => held,
    defer: (run) => new Promise<void>((resolve, reject) => {
      const p = { run, resolve, reject };
      if (!held) { settle(p); return; }
      if (parked) parked.resolve();   // replaced: the landing the next one overtook paints nothing
      parked = p;
    }),
  };
}
