// The viewer's navigation trail (plans/markdown-viewer.md, "Follow-on: Link navigation", L1 and L2): the files a
// reader reached through links INSIDE the shown file, in order, so Back returns to the file a link was followed from
// and Forward retraces the step. A pure state and pure functions over it, plus the one live instance the viewer
// (file-view.ts) reads and writes; nothing here touches the DOM, so file-trail.test.ts runs the rules as they are.
//
// The state is three lists: `back`, the files behind the reader, oldest first; `current`, the file the viewer shows
// (null when the viewer is closed); `forward`, the files ahead, nearest first. An entry names a file as openFileView
// receives it (`path`, `sid`) and the view it was read in when the reader left it (`view`: Rendered or Raw; null before
// the reader has left it, or for a file with no text view, a picture or a PDF). No place rides here: the reader's place
// in a file is the viewer's RememberedPlace, keyed by the file, and a Back re-opens the entry with no target so that
// record re-seats it (file-view.ts pendingPlace); the entry carries only what that record cannot, the view to open in.
//
// What moves the trail (file-view.ts openFileView decides which, from the one tag the viewer's own openers set):
//   push     an open from INSIDE the viewer to another file: the shown file goes onto `back`, the opened file becomes
//            `current`, and `forward` is cleared (a new branch replaces the steps ahead, as a browser's history does)
//   back     the nearest `back` entry becomes `current`; the shown file goes to the front of `forward`
//   forward  the mirror
//   root     an open from OUTSIDE the viewer (the Files pane's rows and Recent list, a chat path pill, a Waiting pane
//            link, any openFileView the viewer's own openers did not call): a new trail with that file as its root
//   end      the viewer closed: the trail is dropped, since the person left the review. The alternative, keeping it
//            for the page's life so a reopen of the same file from Recent finds its Back again, is recorded in L1 as the
//            one not taken.
// The lists hold entries, never a cap: a trail is as long as the links a reader followed in one review.
export type TrailView = "rendered" | "raw";
export type TrailEntry = { path: string; sid: string | null; view: TrailView | null };
export type TrailState = { back: TrailEntry[]; current: TrailEntry | null; forward: TrailEntry[] };

/** No trail: the viewer is closed, or the page has never shown a file. */
export const EMPTY_TRAIL: TrailState = { back: [], current: null, forward: [] };

/** A new trail whose root is `entry` (an open from outside the viewer). */
export function trailRoot(entry: TrailEntry): TrailState {
  return { back: [], current: entry, forward: [] };
}

/** `entry` opened from inside the viewer: the current file goes behind it and the steps ahead are dropped. With no
 *  current file (no trail stood) the entry is the root. */
export function trailPush(s: TrailState, entry: TrailEntry): TrailState {
  return { back: s.current ? [...s.back, s.current] : s.back.slice(), current: entry, forward: [] };
}

/** One step back: the nearest entry behind becomes current, the current file goes ahead. Nothing behind: the state as it is. */
export function trailBack(s: TrailState): TrailState {
  if (!s.back.length) return s;
  const back = s.back.slice(0, -1);
  const current = s.back[s.back.length - 1];
  return { back, current, forward: s.current ? [s.current, ...s.forward] : s.forward.slice() };
}

/** One step forward: the mirror of trailBack. Nothing ahead: the state as it is. */
export function trailForward(s: TrailState): TrailState {
  if (!s.forward.length) return s;
  const [current, ...forward] = s.forward;
  return { back: s.current ? [...s.back, s.current] : s.back.slice(), current, forward };
}

/** The current entry with `view` recorded (the view the reader left the file in, read off its RememberedPlace at the
 *  leave); null leaves the entry's view as it was. No current entry: the state as it is. */
export function trailSetView(s: TrailState, view: TrailView | null): TrailState {
  if (!s.current || view === null) return s;
  return { ...s, current: { ...s.current, view } };
}

/** The viewer closed: no trail. */
export function trailEnd(): TrailState {
  return EMPTY_TRAIL;
}

/** The entry Back would open (the nearest behind), or null. */
export function trailBackTarget(s: TrailState): TrailEntry | null {
  return s.back.length ? s.back[s.back.length - 1] : null;
}
/** The entry Forward would open (the nearest ahead), or null. */
export function trailForwardTarget(s: TrailState): TrailEntry | null {
  return s.forward.length ? s.forward[0] : null;
}

/** The last path segment, for the buttons' titles ("Back to report.md"); a path ending in a slash or empty is given whole. */
export function fileNameOf(path: string): string {
  const cut = path.lastIndexOf("/");
  return cut >= 0 && cut < path.length - 1 ? path.slice(cut + 1) : path;
}

/** The title and aria-label of a Back or Forward button: the word and the target's file name, or the word alone when
 *  there is no target (the button then wears aria-disabled). */
export function navTitle(dir: "back" | "forward", target: TrailEntry | null): string {
  const word = dir === "back" ? "Back" : "Forward";
  return target ? word + " to " + fileNameOf(target.path) : word;
}

/** The step a keydown asks for: Alt+Left is back and Alt+Right forward, on every platform; on a Mac Cmd+[ and Cmd+] as
 *  well (the browser's own history chords, taken over while the viewer is open). Any other modifier held with them
 *  (Shift, Ctrl, or Alt beside Cmd) is another chord and asks nothing. Pure over the event's fields; the caller decides
 *  whether the viewer is open, whether the key was already prevented and whether a text field holds the keyboard. */
export function navChord(e: { key: string; altKey: boolean; metaKey: boolean; ctrlKey: boolean; shiftKey: boolean }, mac: boolean): "back" | "forward" | null {
  if (e.altKey && !e.metaKey && !e.ctrlKey && !e.shiftKey) {
    if (e.key === "ArrowLeft") return "back";
    if (e.key === "ArrowRight") return "forward";
  }
  if (mac && e.metaKey && !e.altKey && !e.ctrlKey && !e.shiftKey) {
    if (e.key === "[") return "back";
    if (e.key === "]") return "forward";
  }
  return null;
}

// ── the live instance ─────────────────────────────────────────────────────────────────────────────
// One trail per page, beside the viewer's other module-level memory (file-view.ts rememberedPlaces). The viewer reads
// it through liveTrail and moves it through setTrail; a test bundle exposes liveTrail to read the state after a step.
let live: TrailState = EMPTY_TRAIL;
export function liveTrail(): TrailState { return live; }
export function setTrail(s: TrailState): TrailState { live = s; return live; }
