// Click-safe, always-acknowledged actions for the romp dashboard.
//
// WHY THIS EXISTS — the "I had to click it several times" bug.
// The dashboard re-renders on every kernel push: a 0.5–3s backstop poll, PLUS an
// immediate push on each SDK stream event and on every hook /tick (turn ended,
// prompt landed, postal message). Surfaces that rebuild their DOM wholesale —
// renderTabs()'s `#tabs`.replaceChildren(), Fleet's `#fleet-list`.replaceChildren()
// — DESTROY and recreate the very node you are clicking. A native `click` only
// fires when the mousedown and the mouseup land on the same element; when a
// rebuild slips between them the click is silently dropped. While a session works
// the pushes are frequent, so the drop is frequent: the button feels dead until
// you happen to click in a gap between rebuilds.
//
// THE RULE (see CLAUDE.md ## Design → "Buttons must stay click-safe…"):
//   1. Never hang an action on a node you rebuild. Put the action on a STABLE
//      ancestor (the container fetched by id survives replaceChildren(); only its
//      children are swapped) and key it off a `data-act` attribute. The listener
//      then survives every rebuild BETWEEN clicks, and a press released over a
//      sibling of the pressed node still lands (the browser dispatches `click` to
//      their nearest common ancestor). What it does not cover: a pressed node
//      REMOVED before the mouseup dispatches no click at all, to the node or to any
//      ancestor (Chromium, in step with Firefox and Safari; probed in headless
//      Chromium 151, 2026-09-08), so a rebuild that can land DURING a press needs
//      the technique below (pressHold) as well.
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
//     it held. pointerup or pointercancel on `release` (the window: a press begun inside a surface commonly ends
//     outside it) and the window's blur (a release in another frame never reaches this one; the timeline's lesson,
//     2026-06-25) release it. The release listeners are installed at the press and removed at the release, so a
//     surface that comes and goes (a viewer per open) leaves nothing behind.
//   - defer(run) runs `run` at once when nothing is pressed, else parks it for the release. A later defer under the
//     same press REPLACES the parked run: a landing the next one overtook paints nothing, the newest is what shows.
//   - The parked run goes on a zero timer at the release rather than running inside the pointerup listener: the
//     click dispatches synchronously after the pointerup (pointerup, mouseup, click, one input task), and the run
//     must come after it, as the timeline's draw does. Event-based (the press's own events); no time heuristic.
export type PressHold = { held(): boolean; defer(run: () => void): void };
const RELEASE_EVENTS = ["pointerup", "pointercancel", "blur"];
export function pressHold(surface: EventTarget, release: EventTarget = window): PressHold {
  let held = false;
  let parked: (() => void) | null = null;
  const onRelease = (): void => {
    for (const t of RELEASE_EVENTS) release.removeEventListener(t, onRelease);
    held = false;
    const run = parked; parked = null;
    if (run) setTimeout(run, 0);
  };
  surface.addEventListener("pointerdown", () => {
    if (held) return;
    held = true;
    for (const t of RELEASE_EVENTS) release.addEventListener(t, onRelease);
  }, true);
  return { held: () => held, defer: (run) => { if (held) parked = run; else run(); } };
}
