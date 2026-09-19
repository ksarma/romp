// Print a file from the viewer, with its pictures (the print follow-on to plans/markdown-viewer.md's Slice 3, item 12; the
// contract of 2026-09-19, parts P1, P2 and P6). The @media print block in the sheets prints the open file alone, black on
// white, but nothing awaited the pictures: the browser's own print (its menu; Ctrl/Cmd+P on a page without the dashboard's
// command palette, whose dispatcher holds that chord there) printed a gated figure as its placeholder and a picture still
// loading as the browser had it at that instant. This module is the flow in front of window.print():
//   1. A press (the bar's Print glyph button, Download's shape, or Ctrl/Cmd+P while a file is open and no text field holds the keyboard)
//      counts the gated placeholders in the body (figure-gate.ts, found by their data-act as the gate finds them: an
//      author can type the class, never the data attribute) that REACH THE PAPER (`printable`: not inside a closed
//      <details>, a typed one or a folded callout, outside its summary, and not under a `hidden` attribute; the third
//      review, 2026-09-19: before this every placeholder was counted and every host it named was loaded, so "with them"
//      fetched from hosts for pictures the print never showed). With any, the bar ARMS instead of printing: one line under
//      the title bar names the count and offers "Print with them" and "Print without them"; Escape or a second press
//      disarms (the update banner's two-click shape: the gate is a privacy choice, so a print never fetches from an
//      unlisted host unless the person chose it). "With them" loads every host the placeholders name through
//      loadGatedHost, the function the placeholder's own click runs, so the requests are the ones a click on each makes;
//      its title names those hosts (the line counts pictures, by contract, and a placeholder naming two hosts says "and 1
//      more host" in its own label, so the title is where the hosts a press grants are read together). The hosts are read
//      at the arm and kept: "with them" loads that list and no other, so the title and the loads are one list by
//      construction. The gate loads by HOST, so a host one printable placeholder and one folded placeholder share is
//      restored in both by that one load; a host only folded or hidden placeholders name is never loaded by a print. A
//      fold the person opens or closes under the armed line (the details' toggle event, heard on the card) is counted
//      again like a repaint. A body repainted under the armed line (the host's `body` report: the changed-on-disk bar's Reload
//      landing, a Rendered or Raw pick) is counted again (the driver's `recount`): over placeholders the line stands with
//      the new count and the title with the new hosts, in place; over none the line goes, since the question it asked is
//      moot, and the next press prints. Before this the line and the title stood as the press left them while "with
//      them" read the hosts at the click, so a Reload that brought a placeholder on a new host had the click fetch from a
//      host the title never named (the second review, 2026-09-19). A placeholder the person activates by hand under the
//      armed line (its click, or Enter or Space on it: the viewer's own gate handlers on the body, file-view.ts loadGate)
//      is counted again the same way, heard on the card after the body's handler ran, so the count and the title follow
//      the one just loaded and the last one gone disarms (the review's consolidation, 2026-09-19: before this the count
//      stood as the press left it until a repaint).
//   2. Then the wait: every <img> in the body reaches complete (its load or its error), and a <video poster> or an svg
//      <image> is awaited through a probe Image at the same URL (neither element reports completeness; the probe asks the
//      browser for the URL the element itself fetched, so no other host is reached), bounded by PRINT_SETTLE_MS, 8 s,
//      after which the print runs anyway: a picture still loading prints as the browser has it, a failed one as its
//      label. The line reads "Preparing N pictures…" meanwhile, beside the viewer's loader (the swirl, the wordmark and the
//      three dots, .fileview-load inline in the row: ui/CLAUDE.md's loading-state rule, which puts the romp loader on every
//      wait; the first build showed the words alone). With no gated placeholder and every picture complete the press
//      prints at once, in the click's own task. The wait is AIMED at the body as it stands, and re-aimed when the
//      body is repainted under it (the host's `body` report: a reload's landing, a format pick, the editor's exit; the
//      pictures listened on were the old body's, detached by the swap) and again at the settle (a picture that entered or
//      was re-aimed since the collection, a heal's retry of a failed figure among them, is awaited too), always under the
//      deadline the press set, never past it: the print fires with every picture in the body complete, or at the deadline.
//   3. window.print(). On afterprint, or at once when print returns, the bar rests.
// The machine is `step`, a pure function over PrintState and PrintEvent returning the next state and the act the driver
// performs; settlePictures takes any objects with `complete` and the two event methods, and timers a test injects
// (file-print.test.ts runs both under node with fake pictures and a fake clock). installFilePrint is the DOM driver both
// viewers call (file-view.ts openFileView and openUrlView): the button, the line, the wait, the print. It registers ONE
// document keydown listener per open, in the capture phase, so an Escape while armed is stopped before the viewer's own
// Escape (a bubble listener on the document, which closes the card) and the chord is prevented before the browser's raw
// print runs; the host's close hook removes it with the viewer. Nothing else is registered on the document (the card carries
// the placeholder listener, onGateAct, which goes with the card). Three keys are left alone by
// that listener: an Escape that is some control's own (a key a listener ahead of this one already stopped, read through
// the event's stop flag: the viewer's text-size flyout is dismissed by a document listener wired before this per-open one,
// which closes the flyout and stops the key; ownsEscape: the keyboard inside a menu, a listbox or a dialog, the WAI-ARIA
// patterns whose Escape closes the widget, the viewer's Outline popover among them, or a popup standing open in the card
// by its trigger's aria-haspopup with aria-expanded true, one whose own handler runs after this listener; or a text field,
// whose own Escape is the field's, the Comments composer's cancel among them), which acts on that control and leaves the
// bar armed for the next Escape; a chord a listener before this one already prevented (the dashboard shell's
// command palette dispatcher, palette-main.ts, which claims Mod+P on every pane document from the frame's load, so in the
// shell the chord is the palette's and the button prints); and a text field's chord. A held chord's repeats are prevented
// too, since the browser's default for each is its own print, but only the first keydown is a press (one per repeat would
// arm and disarm on alternate repeats). The line is a row of the card in the notice bar's dress (.fileview-err, with
// .fileview-btn.fileview-err-act word buttons: the changed-on-disk bar's shape, file-view.ts raiseDiskBar), so it needs no
// rule of its own and the print block, which hides every `.fileview > .fileview-err`, leaves it off the paper; a word
// button of the line that holds the keyboard when the line goes hands it back to the Print button (the zoom flyout's and
// the Outline's Escape do the same for their trigger), never to the document's body. No kernel route, no server-side
// render (P6).
// The file's KIND switches the flow at the press (P3 and P4; the host's `kind` reads it then, since the kernel's Content-Type
// decides it when the bytes land, after the bar is built). A rendered note, code, text and a picture opened directly are
// the page: the wait and window.print() above, and the print block in the sheets fits `img.fileview-img` to the page (the
// screen rule's 82vh cap, radius and shadow undone). A PDF is a frame at a blob URL (file-view.ts pdfBlock), and a printed
// frame shows one viewport at most, so the flow prints the document itself: the frame's own window, contentWindow.print(),
// when the frame holds the PDF (pdfFrameWindow: the window reachable, its document the PDF's, print a function; in
// Chromium the blob frame's document is the PDF viewer's, content type application/pdf, and the parent may call its print;
// a browser without a PDF viewer, headless Chromium's shell and headless Firefox among them, downloads the bytes instead
// and leaves the frame's window at about:blank, whose print is a function too and would print a blank page). When the
// frame cannot print, the kernel's /file URL opens in a new tab through the host's opener, the modified click's
// (preview.ts openFileTab), and the line reads "Print from the tab that opened." until the next press or the close; a tab
// the browser did not open is said the same way. The Comments panel's PDF pages (the pdf.js canvases, up while the panel is
// open, with no frame in the body) are not printed: Print prints the PDF, through the tab then.
// The button is DISABLED until the body is in (P7): the flow starts in the `disabled` phase, the button wearing the disabled
// attribute, aria-disabled and the sheets' disabled dress, and the host reports the body through the installer's `bodyIn`:
// true at every paint that seats the file's content (file-view.ts renderBody's media and text paints, so a reload's landing
// passes through it; the editor's mount and its plain fallback; openUrlView's paint), false where the loader or a failure
// pane takes the body (the editor's chunk wait, the fetch's failure pane, a picture that would not decode, the URL viewer's
// failure; the open's own loader stands from the build, the phase the flow starts in). A press there changes nothing, and
// the chord is still prevented, so the browser's raw print does not run over the loader either; the body going out while
// the bar is armed or the wait runs disarms (the line goes, the wait is cancelled) and disables.
import { GATE_ACT, loadGatedHost } from "./figure-gate";
import { ICON_PRINT } from "./icons";

/** The wait's deadline: the print runs after this however many pictures are still loading. */
export const PRINT_SETTLE_MS = 8000;
let settleMs = PRINT_SETTLE_MS;
/** The test seam: a browser leg that stalls a picture sets a shorter deadline; null restores the constant. Nothing in the
 *  product calls it, and the constant is what the driver reads until it does. */
export function setPrintSettleMs(ms: number | null): void { settleMs = ms === null ? PRINT_SETTLE_MS : ms; }
export function printSettleMs(): number { return settleMs; }

// ── the machine ─────────────────────────────────────────────────────────────────────────────────────
export type PrintPhase = "disabled" | "resting" | "armed" | "preparing" | "printing";
/** `gated`: the placeholders counted at the press that armed; `pending`: the pictures still loading when the wait began. */
export type PrintState = { phase: PrintPhase; gated: number; pending: number };
export const RESTING: PrintState = { phase: "resting", gated: 0, pending: 0 };
/** The body is not in (the loader, or a failure pane, holds it): the button is disabled and a press changes nothing. The
 *  driver starts here and leaves on the host's `body` event (P7). */
export const DISABLED: PrintState = { phase: "disabled", gated: 0, pending: 0 };
/** The file's kind at a press: `document` prints the page (a note, code, text, a picture opened directly); `pdf` prints the
 *  document itself through its frame, or the /file tab. */
export type PrintKind = "document" | "pdf";
export type PrintEvent =
  | { kind: "press"; gated: number; pending: number; file?: PrintKind }   // Print, or the chord: the counts as the body stands; the kind, a document when absent
  | { kind: "escape" }
  | { kind: "choose"; withGated: boolean }               // one of the armed line's two buttons
  | { kind: "prepare"; pending: number }                 // the driver, after the choice: the pictures still loading
  | { kind: "ready" }                                    // every picture settled, or the deadline
  | { kind: "printed" }                                  // afterprint, or print returned
  | { kind: "body"; in: boolean }                        // the host: the body holds the file's content (true), or the loader or a failure pane took it (false)
  | { kind: "recount"; gated: number };                  // the driver, after a repaint under the armed line: the placeholders the body holds now
/** What the driver does for a step: `arm` shows the line with its two buttons, `disarm` (a second press, Escape, or the body
 *  going out, when the driver cancels a running wait too) and `rest` remove the line and restore the button, `activate` loads
 *  every gated host and then prepares, `skip` prepares over the placeholders as they stand, `wait` shows the preparing line,
 *  `print` calls window.print, `printPdf` prints the PDF itself (the frame's window, or the /file tab). The button's disabled
 *  dress follows the phase, not an act: the driver syncs it after every step. */
export type PrintAct = "none" | "arm" | "disarm" | "activate" | "skip" | "wait" | "print" | "printPdf" | "rest";

const begin = (pending: number): { state: PrintState; act: PrintAct } =>
  pending > 0 ? { state: { phase: "preparing", gated: 0, pending }, act: "wait" } : { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };

/** The next state and the act for it. The host's `body` event comes first: the body going out disables from every phase
 *  and disarms (the line goes, and the driver cancels a wait), and its arrival rests a disabled flow and changes nothing
 *  elsewhere by itself (the driver then reads the repainted body: during the wait it re-aims the wait at it, the phase
 *  holding; under the armed line it feeds `recount` with the placeholders the body holds now). Then, by phase:
 *  while disabled every other event changes nothing. A press while resting over a PDF prints the PDF itself (`printPdf`),
 *  whatever the counts (a frame holds no placeholder and no picture); over a document it arms over any gated placeholder
 *  and otherwise begins the wait (or prints at once with nothing pending); while armed a press or Escape disarms, a
 *  choice activates or skips, the driver's `prepare` then beginning the wait, and a `recount` arms again over the new count
 *  (`arm`: the driver rewrites the line and the title in place) or disarms over none (the placeholders the line asked about
 *  are gone, so the question is moot; the next press prints); `ready` prints; `printed` rests. Every other
 *  pairing changes nothing: a press or an Escape during the wait or the print, an Escape at rest, a late `ready` after a
 *  rest, a `printed` after the body went out (the button stays disabled), a `recount` in any phase but armed. */
export function step(s: PrintState, ev: PrintEvent): { state: PrintState; act: PrintAct } {
  if (ev.kind === "body") {
    if (!ev.in) return s.phase === "disabled" ? { state: s, act: "none" } : { state: DISABLED, act: "disarm" };
    return s.phase === "disabled" ? { state: RESTING, act: "none" } : { state: s, act: "none" };
  }
  switch (s.phase) {
    case "disabled": break;
    case "resting":
      if (ev.kind !== "press") break;
      if (ev.file === "pdf") return { state: { phase: "printing", gated: 0, pending: 0 }, act: "printPdf" };
      if (ev.gated > 0) return { state: { phase: "armed", gated: ev.gated, pending: 0 }, act: "arm" };
      return begin(ev.pending);
    case "armed":
      if (ev.kind === "press" || ev.kind === "escape") return { state: RESTING, act: "disarm" };
      if (ev.kind === "choose") return { state: s, act: ev.withGated ? "activate" : "skip" };
      if (ev.kind === "prepare") return begin(ev.pending);
      if (ev.kind === "recount") return ev.gated > 0 ? { state: { phase: "armed", gated: ev.gated, pending: 0 }, act: "arm" } : { state: RESTING, act: "disarm" };
      break;
    case "preparing":
      if (ev.kind === "ready") return { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };
      break;
    case "printing":
      if (ev.kind === "printed") return { state: RESTING, act: "rest" };
      break;
  }
  return { state: s, act: "none" };
}

/** The armed line's words for `n` placeholders. */
export function armedWords(n: number): string {
  return n === 1 ? "1 picture from another host is not loaded." : n + " pictures from other hosts are not loaded.";
}
/** The wait's words for `n` pictures still loading. */
export function preparingWords(n: number): string {
  return n === 1 ? "Preparing 1 picture…" : "Preparing " + n + " pictures…";
}
export const WITH_WORDS = "Print with them";
export const WITHOUT_WORDS = "Print without them";
/** "Print with them"'s title: the hosts the placeholders name, in the order they appear, so the hosts one press grants for
 *  the rest of the page (loadGatedHost, decision 8's page-life ruling) can be read together before the press; the line itself
 *  counts pictures, by contract. With none known (a stand-in body) the words name them generically. */
export function withTitle(hosts: string[]): string {
  const list = hosts.length === 0 ? "those hosts" : hosts.length === 1 ? hosts[0] : hosts.slice(0, -1).join(", ") + " and " + hosts[hosts.length - 1];
  return "Load the pictures from " + list + ", then print";
}
/** "Print without them"'s title. */
export const WITHOUT_TITLE = "Print with their placeholders as they are";
/** The PDF flow's line when the frame could not print and the /file URL opened in a new tab. */
export const TAB_WORDS = "Print from the tab that opened.";
/** ...and when the browser did not open that tab (a blocked pop-up, or a host that cannot open one). */
export const NO_TAB_WORDS = "The browser did not open a tab for this PDF.";

type KeyLike = { key?: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean; shiftKey?: boolean; repeat?: boolean };
/** The print chord's keys: Ctrl+P or Cmd+P, unshifted, without Alt, a key repeat or not. The key is read case-insensitively:
 *  Caps Lock reports "P" with no Shift. The driver prevents every keydown this names while a file is open, since the
 *  browser's default for each, a held chord's repeats included, is its own print, the one the flow replaces. */
export function isPrintKeys(e: KeyLike): boolean {
  return (e.ctrlKey === true || e.metaKey === true) && e.altKey !== true && e.shiftKey !== true && typeof e.key === "string" && e.key.toLowerCase() === "p";
}
/** The chord as a PRESS: the keys, and not a key repeat (a held chord would arm and disarm on alternate repeats; its
 *  repeats are prevented and nothing more). */
export function isPrintChord(e: KeyLike): boolean {
  return isPrintKeys(e) && e.repeat !== true;
}
/** The controls that own their Escape: the WAI-ARIA patterns whose Escape closes the widget and returns the keyboard itself
 *  (a menu, the viewer's Outline popover among them; a listbox; a dialog). While the bar is armed an Escape from inside one
 *  is left to it, and the next Escape disarms. */
export const OWN_ESCAPE_SEL = '[role="menu"], [role="menubar"], [role="listbox"], [role="dialog"], [role="alertdialog"]';
/** An open popup's trigger: aria-haspopup with aria-expanded true, the menu-button and disclosure patterns (the viewer's
 *  text-size flyout, a role=group under a trigger, and its Outline button). Such a popup's Escape closes it from wherever
 *  the keyboard is, so while one stands open in the card the Escape is its, whatever the target. The rule reads the state
 *  as the flow's listener finds it: a popup whose own Escape handler runs after that listener (a listener on the popup, or
 *  one wired after the viewer's bar) is still open then; the flyout's dismiss runs ahead of it and has closed the flyout by
 *  then, so that one is read through the stopped event instead (the driver's onKey). The Print button's own aria-expanded
 *  while armed has no aria-haspopup and is not matched. */
export const OPEN_POPUP_SEL = '[aria-haspopup][aria-expanded="true"]';
/** `target` is inside a control that owns its Escape (OWN_ESCAPE_SEL), or `scope` (the card) holds an open popup
 *  (OPEN_POPUP_SEL): the Escape is that control's, and the armed bar leaves it alone. A text field's Escape is the field's
 *  too, but that is the host's `typing` predicate, read beside this. */
export function ownsEscape(target: EventTarget | null, scope?: ParentNode | null): boolean {
  const t = target as Element | null;
  if (!!t && typeof t.closest === "function" && t.closest(OWN_ESCAPE_SEL) !== null) return true;
  return !!scope && typeof scope.querySelector === "function" && scope.querySelector(OPEN_POPUP_SEL) !== null;
}

// ── the placeholders that reach the paper ───────────────────────────────────────────────────────────
/** What the printable test reads of a node: its name, its attributes and its parent (an Element, or a stand-in in a test). */
export type PrintableNode = { localName: string; parentElement: PrintableNode | null; hasAttribute(name: string): boolean };
/** Whether `el` reaches the paper: nothing from it up to the root is a closed <details> holding it outside that details'
 *  own <summary> (the fold's content is not rendered; its summary is), and nothing carries the `hidden` attribute, whatever
 *  its value (`until-found` included: the browser skips such content until a find or a fragment reveals it). The same
 *  ancestor walk md-sanitize.ts revealFragmentTarget runs, read rather than applied. Both shapes come from the author: a
 *  typed <details>, a folded callout (`> [!type]-`, md-config.ts) and `hidden` all pass the sanitizer, where an inline
 *  `display: none` does not (colorOnlyStyle keeps colour declarations alone), so a picture under that style prints and is
 *  printable here. A placeholder the flow counts, names in the with-button's title or loads a host for must pass this
 *  (gates, in the driver): a host is a privacy choice, and a print fetches from one only for a picture that is on the paper. */
export function printable(el: PrintableNode): boolean {
  for (let n: PrintableNode | null = el; n; n = n.parentElement) {
    if (n.hasAttribute("hidden")) return false;
    const p = n.parentElement;
    if (p && p.localName === "details" && n.localName !== "summary" && !p.hasAttribute("open")) return false;
  }
  return true;
}

// ── the pictures and the wait ────────────────────────────────────────────────────────────────────────
/** What the wait needs of a picture: an <img>, or a probe Image standing in for a poster or an svg <image>. */
export type Picture = {
  complete: boolean;
  addEventListener(type: string, cb: () => void): void;
  removeEventListener(type: string, cb: () => void): void;
};
export type Timers = { setTimeout: (fn: () => void, ms: number) => unknown; clearTimeout: (handle: unknown) => void };
const REAL_TIMERS: Timers = { setTimeout: (fn, ms) => setTimeout(fn, ms), clearTimeout: (h) => clearTimeout(h as ReturnType<typeof setTimeout>) };

/** A URL `value` names against `base`, or null for an empty or unparseable value. */
function resolved(value: string | null, base: string): string | null {
  if (!value) return null;
  try { return new URL(value, base).href; } catch { return null; }
}
/** Every picture under `body` the print waits on: each <img> as itself, and a probe (`probe(url)`: a new Image aimed at
 *  the URL, in the driver) for each <video poster> and each svg <image href>, whose elements report no completeness. A
 *  gated element has its poster or href moved aside (figure-gate.ts) and is not probed; a gated img has no src, and an img
 *  with no src is complete by HTML's definition, so "Print without them" waits on nothing for a placeholder. */
export function collectPictures(body: ParentNode, base: string, probe: (url: string) => Picture): Picture[] {
  const out: Picture[] = [];
  body.querySelectorAll("img").forEach((img) => { out.push(img as HTMLImageElement); });
  body.querySelectorAll("video[poster]").forEach((v) => { const u = resolved(v.getAttribute("poster"), base); if (u) out.push(probe(u)); });
  body.querySelectorAll("image").forEach((im) => { const u = resolved(im.getAttribute("href"), base); if (u) out.push(probe(u)); });
  return out;
}

export type SettleWhy = "settled" | "deadline" | "cancelled";
export type Settle = {
  /** resolves once every pending picture fired load or error (`settled`), at the deadline (`deadline`), or on cancel */
  done: Promise<SettleWhy>;
  /** the pictures not yet complete */
  pending(): number;
  /** stop listening and clear the timer: the viewer closed, or nothing was pending */
  cancel(): void;
};
/** Wait for every picture in `pics` that is not complete to fire load or error, or for `deadlineMs` to pass, whichever
 *  first. The listeners come off at the end whichever way it ends, and the timer is cleared. With nothing pending the
 *  promise resolves `settled` and no timer is set. */
export function settlePictures(pics: Picture[], deadlineMs: number, timers: Timers = REAL_TIMERS): Settle {
  const waiting = new Set<Picture>(pics.filter((p) => !p.complete));
  const listeners = new Map<Picture, () => void>();
  let finish: (why: SettleWhy) => void = () => {};
  const done = new Promise<SettleWhy>((resolve) => { finish = resolve; });
  let over = false;
  let timer: unknown = null;
  const end = (why: SettleWhy): void => {
    if (over) return;
    over = true;
    if (timer !== null) { timers.clearTimeout(timer); timer = null; }
    for (const [p, cb] of listeners) { p.removeEventListener("load", cb); p.removeEventListener("error", cb); }
    listeners.clear();
    finish(why);
  };
  for (const p of waiting) {
    const cb = (): void => {
      waiting.delete(p);
      listeners.delete(p);
      p.removeEventListener("load", cb); p.removeEventListener("error", cb);
      if (waiting.size === 0) end("settled");
    };
    listeners.set(p, cb);
    p.addEventListener("load", cb);
    p.addEventListener("error", cb);
  }
  if (waiting.size === 0) end("settled");
  else timer = timers.setTimeout(() => end("deadline"), deadlineMs);
  return { done, pending: () => waiting.size, cancel: () => end("cancelled") };
}

// ── the PDF's frame ─────────────────────────────────────────────────────────────────────────────────
/** What the PDF flow needs of the frame's window: its print. */
export type FrameWindow = { print: () => void };
/** The window of the PDF frame in `body` when it holds the PDF and can print it: `iframe.fileview-frame` (file-view.ts
 *  pdfBlock), its contentWindow reachable, its document the PDF (content type application/pdf, as Chromium's viewer
 *  document reports, or the window's location the frame's own src with any fragment aside: the blob URL the frame was
 *  aimed at, `#page=N` included), and print a function. Null otherwise: no frame (the Comments panel's pages are up), a
 *  window the browser withholds, or a frame that did not load the PDF (a browser without a PDF viewer downloads the bytes
 *  and leaves the window at about:blank, whose print would print a blank page). */
export function pdfFrameWindow(body: ParentNode): FrameWindow | null {
  const frame = body.querySelector("iframe.fileview-frame") as HTMLIFrameElement | null;
  if (!frame) return null;
  try {
    const w = frame.contentWindow;
    if (!w || typeof w.print !== "function") return null;
    const bare = (u: string): string => u.replace(/#.*$/, "");
    const href = bare(w.location.href);
    const holds = (w.document !== null && w.document.contentType === "application/pdf") || (href !== "about:blank" && href === bare(frame.src));
    return holds ? w : null;
  } catch { return null; }                     // a cross-origin window withholds its document and its location
}

// ── the DOM driver ──────────────────────────────────────────────────────────────────────────────────
export type PrintHost = {
  /** the card (`.fileview`): the line is a row of it */
  card: HTMLElement;
  /** the title bar: the line goes right after it, above any notice the viewer raises */
  bar: HTMLElement;
  /** the body: its placeholders are counted and its pictures awaited */
  body: HTMLElement;
  /** a text field holds the keyboard now: the chord is left to the browser */
  typing: () => boolean;
  /** runs `cb` when this open ends (the viewer's close hooks): the listener and the wait leave with the card */
  onClose: (cb: () => void) => void;
  /** the file's kind as it stands at the press: `pdf` once a PDF's bytes landed (the frame prints itself, or the /file tab
   *  opens), else `document`; absent, every press is a document's (the URL viewer shows documents alone) */
  kind?: () => PrintKind;
  /** for a PDF whose frame cannot print: open the kernel's /file URL in a new tab, the modified click's opener (preview.ts
   *  openFileTab); true when a tab opened. Absent: no tab, and the line says the browser did not open one */
  openTab?: () => boolean;
};
export const PRINT_LINE_ID = "fileview-print-line";
export const PRINT_LINE_CLASS = "fileview-print-line";

/** Build the Print button for a viewer and wire the flow to it and to the document's keydown; the caller puts the button
 *  in its bar and reports the body through `bodyIn` (P7): true at a paint that seats the file's content, false where the
 *  loader or a failure pane takes the body; the button starts disabled. `data-print` on the button carries the phase while
 *  it is not resting (`disabled` included), for the sheets and the tests. */
export function installFilePrint(host: PrintHost): { button: HTMLButtonElement; bodyIn: (present: boolean) => void } {
  const doc = document;                        // the hosting document (the shims the node suites install give a fake element no ownerDocument)
  const btn = doc.createElement("button") as HTMLButtonElement;
  btn.type = "button";
  // a glyph in Download's shape (file-view.ts: the tray glyph, .fileview-icon, the words in the title and aria-label, the bar's
  // data-icon mark): the word button the first build placed here widened the bar's wrapped action row past the chat modal's
  // card at 380px (file-view-text-size.test.ts's browser leg)
  btn.innerHTML = ICON_PRINT;
  btn.className = "fileview-btn fileview-icon fileview-print";
  btn.dataset.icon = "1";
  btn.title = "Print"; btn.setAttribute("aria-label", "Print");
  let state: PrintState = DISABLED;            // the loader holds the body from the build: the host's bodyIn(true) at the first paint rests the flow
  let line: HTMLElement | null = null;
  let withBtn: HTMLButtonElement | null = null;   // the armed line's "Print with them", while the line stands: a re-arm rewrites its title in place
  let armedHosts: string[] = [];               // the hosts the armed line's press grants: read at the arm and at each re-arm, named in the with-button's title, and the list "with them" loads (one list, so the title names what the click fetches)
  let notice = false;                          // the line is the PDF flow's notice (the tab), standing at rest until the next press or the close
  let settle: Settle | null = null;
  let waitEnds = 0;                            // when the running wait's deadline falls (Date.now()): a re-aim keeps it and never extends it
  let closed = false;

  /** The body's placeholders that reach the paper (printable): the ones the press counts, the title names and "with them"
   *  loads a host for. One inside a closed fold or under hidden is left out, since the print never shows it. */
  const gates = (): HTMLElement[] => (Array.from(host.body.querySelectorAll('[data-act="' + GATE_ACT + '"]')) as HTMLElement[]).filter(printable);
  /** Every host every printable placeholder names, once each, in the order the placeholders name them. */
  const gatedHosts = (): string[] => {
    const hosts = new Set<string>();
    for (const g of gates()) for (const h of (g.getAttribute("data-fv-hosts") || "").split(" ")) if (h) hosts.add(h);
    return Array.from(hosts);
  };
  const probe = (url: string): Picture => { const im = new Image(); im.src = url; return im; };
  /** Remove the line. A word button of it holding the keyboard hands it back to the Print button, the trigger (the zoom
   *  flyout's and the Outline's Escape do the same for theirs); the browser's fixup would drop it on the document's body
   *  otherwise, where the next key scrolls nothing. Not at the close, where the card goes with the line. */
  const dropLine = (): void => {
    if (line) {
      const held = !closed && line.contains(doc.activeElement);
      line.remove(); line = null; withBtn = null;
      if (held) btn.focus({ preventScroll: true });
    }
    notice = false;
  };
  /** The line, a row of the card right under the bar: `words` as its first node (the armed line's buttons and the wait's
   *  loader follow it, so a recount can rewrite the words in place). `loading` adds the viewer's loader after the words
   *  (the swirl, the wordmark and the three pulsing dots, file-view.ts's markup, `.fileview-load` under the sheets'
   *  `.fileview-print-line .fileview-load` rule so it sits inline in the row; hidden from the status's announcement, which
   *  reads the words alone). */
  const showLine = (words: string, loading = false): HTMLElement => {
    dropLine();
    const row = doc.createElement("div");
    row.className = "fileview-err " + PRINT_LINE_CLASS;
    row.id = PRINT_LINE_ID;
    row.setAttribute("role", "status");
    row.textContent = words;
    if (loading) {
      const load = doc.createElement("div");
      load.className = "fileview-load fileview-print-load";
      load.setAttribute("aria-hidden", "true");
      load.innerHTML = '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>'
        + '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>';
      row.appendChild(load);
    }
    host.card.insertBefore(row, host.bar.nextSibling);
    line = row;
    return row;
  };
  const syncButton = (): void => {
    const off = state.phase === "disabled";
    const armed = state.phase === "armed";
    const busy = state.phase === "preparing" || state.phase === "printing";
    btn.disabled = off;                        // the attribute (no click reaches a disabled button) and aria-disabled both; the sheets' disabled dress reads either (.fileview-btn:disabled)
    if (off) btn.setAttribute("aria-disabled", "true"); else btn.removeAttribute("aria-disabled");
    btn.classList.toggle("on", armed);
    btn.classList.toggle("fileview-busy", busy);
    if (armed) btn.setAttribute("aria-expanded", "true"); else btn.removeAttribute("aria-expanded");
    if (busy) btn.setAttribute("aria-busy", "true"); else btn.removeAttribute("aria-busy");
    if (state.phase === "resting") delete btn.dataset.print; else btn.dataset.print = state.phase;
  };
  const dropSettle = (): void => { if (settle) { settle.cancel(); settle = null; } };
  /** Aim the wait at the body as it stands, `deadlineMs` from now: collect, listen, and at the settle read the body again
   *  (a picture that entered or was re-aimed since the collection is awaited too, under the time left) or feed `ready`; the
   *  deadline feeds `ready` whatever the body holds. The count still loading; 0 with nothing to wait on (no listener, no timer). */
  const aimWait = (deadlineMs: number): number => {
    dropSettle();
    const s = settlePictures(collectPictures(host.body, doc.baseURI, probe), deadlineMs);
    const n = s.pending();
    if (n === 0) { s.cancel(); return 0; }
    settle = s;
    void s.done.then((why) => {
      if (settle !== s) return;                 // cancelled, or replaced by a later wait
      settle = null;
      if (why === "cancelled" || closed || !host.card.isConnected) return;
      const left = waitEnds - Date.now();
      if (why === "settled" && left > 0) {
        const more = aimWait(left);             // the body as it stands now: something entered or was re-aimed since the collection
        if (more > 0) { showLine(preparingWords(more), true); return; }
      }
      feed({ kind: "ready" });
    });
    return n;
  };
  /** Begin the wait, at a press or a choice: the full deadline from now. */
  const beginWait = (): number => { waitEnds = Date.now() + settleMs; return aimWait(settleMs); };
  /** The body repainted during the wait (the host's `body` in: a reload's landing, a format pick, the editor's exit): the
   *  pictures listened on were the old body's, detached by the swap, so the wait is aimed at the new body under the time
   *  left; with nothing loading there the print runs at once, and the line's count follows. The machine holds the phase
   *  (its `body` in during the wait is `none`): the re-aim is the driver's, as the collection is. */
  const reaim = (): void => {
    const n = aimWait(Math.max(0, waitEnds - Date.now()));
    if (n === 0) { feed({ kind: "ready" }); return; }
    showLine(preparingWords(n), true);
  };
  const doPrint = (): void => {
    const done = (): void => { window.removeEventListener("afterprint", done); feed({ kind: "printed" }); };
    window.addEventListener("afterprint", done);
    try { window.print(); } finally { done(); }   // afterprint, or at once when print returns: the second call finds the state at rest and changes nothing
  };
  /** The PDF itself: the frame's own print when the frame holds the document, else the /file URL in a new tab and the line
   *  saying so (or that the browser opened none), shown after the rest so it stands until the next press or the close. */
  const doPrintPdf = (): void => {
    const w = pdfFrameWindow(host.body);
    if (w) { try { w.print(); } finally { feed({ kind: "printed" }); } return; }
    const opened = host.openTab ? host.openTab() : false;
    feed({ kind: "printed" });
    showLine(opened ? TAB_WORDS : NO_TAB_WORDS);
    notice = true;
  };
  const feed = (ev: PrintEvent): void => {
    if (closed) return;
    const r = step(state, ev);
    state = r.state;
    switch (r.act) {
      case "arm": {
        armedHosts = gatedHosts();               // the hosts the press would grant, read together (the header) and kept for the click
        const words = armedWords(state.gated), withWords = withTitle(armedHosts);
        if (line && withBtn) { line.firstChild!.textContent = words; withBtn.title = withWords; break; }   // a recount under a standing line: the words and the title follow the repainted body in place (the keyboard stays where it is, and the line moves no more than its words)
        const row = showLine(words);
        for (const [btnWords, withGated] of [[WITH_WORDS, true], [WITHOUT_WORDS, false]] as Array<[string, boolean]>) {
          const b = doc.createElement("button") as HTMLButtonElement;
          b.type = "button"; b.textContent = btnWords;
          b.className = "fileview-btn fileview-err-act";
          b.title = withGated ? withWords : WITHOUT_TITLE;
          b.addEventListener("click", () => { feed({ kind: "choose", withGated }); });
          row.appendChild(b);
          if (withGated) withBtn = b;
        }
        break;
      }
      case "disarm": dropSettle(); dropLine(); break;   // the body going out during the wait: no wait survives a disarm
      case "rest": dropLine(); break;
      case "activate": {
        // every host the armed line's title names, through the gate's own load path: loadGatedHost is what the placeholder's
        // click runs (file-view.ts loadGate), and a placeholder naming two hosts takes two clicks, so both hosts are loaded.
        // The list is the arm's (re-read at each recount), never the body's at the click: the title and the loads are one list.
        // The gate restores by host (regateFigures), so a folded placeholder naming a host a printable one also names is
        // restored by the same load; a host no printable placeholder names is not in the list and stays gated
        const hosts = armedHosts;
        for (const h of hosts) loadGatedHost(h, doc);
        feed({ kind: "prepare", pending: beginWait() });
        return;
      }
      case "skip": feed({ kind: "prepare", pending: beginWait() }); return;
      case "wait": showLine(preparingWords(state.pending), true); break;
      case "print": dropLine(); syncButton(); doPrint(); return;   // doPrint feeds `printed` itself, which syncs
      case "printPdf": dropLine(); syncButton(); doPrintPdf(); return;   // doPrintPdf feeds `printed` too
      case "none": break;
    }
    syncButton();
  };
  const press = (): void => {
    if (notice) dropLine();                    // the last press's notice (a PDF's tab) goes with this press
    if (state.phase !== "resting") { feed({ kind: "press", gated: 0, pending: 0 }); return; }   // disabled: nothing (the body is not in); armed: the second press disarms; busy: nothing
    const file: PrintKind = host.kind ? host.kind() : "document";
    if (file === "pdf") { feed({ kind: "press", gated: 0, pending: 0, file }); return; }   // the PDF prints itself: no placeholder, no picture to wait on
    const n = gates().length;
    feed({ kind: "press", gated: n, pending: n > 0 ? 0 : beginWait() });
  };
  btn.addEventListener("click", press);
  /** A placeholder the person activates by hand while the bar is armed (its click, or Enter or Space on it: the viewer's own
   *  gate handlers on the body, file-view.ts loadGate and gateKeys) loads its host at once, so the body's placeholders are
   *  counted again and the line's count and the hosts its title grants follow, as a repaint's do; the last one gone
   *  disarms. Heard on the card in the bubble phase: the body is the card's descendant, so its handlers run first whatever
   *  the registration order, and the restore has run when this reads the body. The placeholder is found by its mark on the
   *  event's target, which the restore detached from the body but left whole. A click on the line's own buttons names no
   *  placeholder and changes nothing here; the two viewers' gate handlers stand on the body, never on the card. */
  const onGateAct = (e: Event): void => {
    if (state.phase !== "armed") return;
    if (e.type === "keydown") { const k = (e as KeyboardEvent).key; if (k !== "Enter" && k !== " ") return; }
    const t = e.target as Element | null;
    if (!t || typeof t.closest !== "function" || t.closest('[data-act="' + GATE_ACT + '"]') === null) return;
    feed({ kind: "recount", gated: gates().length });
  };
  host.card.addEventListener("click", onGateAct);
  host.card.addEventListener("keydown", onGateAct);
  /** A fold opened or closed while the bar is armed (a typed <details>, a folded callout): the placeholders that reach the
   *  paper changed, so they are counted again, as after a repaint. The details' toggle event does not bubble, so the card
   *  hears it in the capture phase. */
  const onToggle = (): void => { if (state.phase === "armed") feed({ kind: "recount", gated: gates().length }); };
  host.card.addEventListener("toggle", onToggle, true);
  const onKey = (e: KeyboardEvent): void => {
    if (e.key === "Escape") {
      if (e.cancelBubble) return;                // a listener ahead of this one on the document stopped the key: it is that control's (the text-size flyout's dismiss, file-view.ts wireZoomDismiss, a capture listener wired before this per-open one, which closes the flyout and stops the event; stopPropagation stops no listener on the same node, and the flag, the DOM standard's alias for the stop propagation flag, is how a later one reads the claim). The bar stays armed for the next Escape
      if (state.phase !== "armed" || ownsEscape(e.target, host.card) || host.typing()) return;   // at rest the viewer's own Escape closes the card; from inside a menu or a dialog, with a popup open in the card (its own handler running after this listener) or from a text field (the Comments composer, whose Escape cancels the draft) the Escape is that control's, and the next one disarms
      e.preventDefault(); e.stopPropagation();   // disarm alone: the viewer's own Escape, a bubble listener on the document, would close the card
      feed({ kind: "escape" });
      return;
    }
    if (!doc.body.classList.contains("fileview-open") || !host.card.isConnected || host.typing()) return;   // no file open, the card gone, or a text field holding the keyboard: every key below is the browser's or the field's
    if (e.defaultPrevented) return;              // a listener before this one claimed the key: the dashboard shell's command palette dispatcher (palette-main.ts, a capture-phase listener on every pane document from the frame's load, ahead of this per-open one) prevents Mod+P and opens the palette, so in the shell the chord is the palette's and the button prints
    if (isPrintKeys(e) && e.repeat === true) { e.preventDefault(); return; }   // a held chord's later keydowns: prevented, since the browser's default for each is its own print over the body as it stands, but no press (one per repeat would arm and disarm on alternate repeats)
    if (!isPrintChord(e)) return;
    e.preventDefault();                          // the browser's raw print, which would print placeholders and half-loaded pictures, and over the loader the loader page: prevented before the press, which the disabled phase ignores, so the chord over the loader prints nothing at all
    press();
  };
  doc.addEventListener("keydown", onKey, true);
  host.onClose(() => {
    closed = true;
    doc.removeEventListener("keydown", onKey, true);
    dropSettle();
    dropLine();
  });
  syncButton();                                // the disabled dress from the build
  /** The host's word on the body (P7): true at a paint that seats the file's content, false where the loader or a failure
   *  pane takes it; the machine rests or disables, and a flow under way is disarmed. A paint under the armed line has the
   *  placeholders counted again (the line's words and the hosts its title grants follow the repainted body, or the line
   *  goes with the last placeholder); a paint under the wait re-aims it. */
  const bodyIn = (present: boolean): void => {
    feed({ kind: "body", in: present });
    if (!present) return;
    if (state.phase === "armed") feed({ kind: "recount", gated: gates().length });
    else if (state.phase === "preparing") reaim();
  };
  return { button: btn, bodyIn };
}
