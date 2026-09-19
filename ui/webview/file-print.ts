// Print a file from the viewer, with its pictures (the print follow-on to plans/markdown-viewer.md's Slice 3, item 12; the
// contract of 2026-09-19, parts P1, P2 and P6). The @media print block in the sheets prints the open file alone, black on
// white, but nothing awaited the pictures: the browser's own print (its menu; Ctrl/Cmd+P on a page without the dashboard's
// command palette, whose dispatcher holds that chord there) printed a gated figure as its placeholder and a picture still
// loading as the browser had it at that instant. This module is the flow in front of window.print():
//   1. A press (the bar's Print glyph button, Download's shape, or Ctrl/Cmd+P while a file is open and no text field holds the keyboard)
//      counts the gated placeholders in the body (figure-gate.ts, found by their data-act as the gate finds them: an
//      author can type the class, never the data attribute) that REACH THE PAPER (`figurePrintable`: the placeholder
//      is not inside a closed <details>, a typed one or a folded callout, outside its summary, and not under a `hidden`
//      attribute, the two hidings the walk knows; where the browser can be asked it renders the placeholder too, by its
//      own checkVisibility and a client rect, so a hiding the walk does not know, a `popover` not shown, a ruby's <rp>, a
//      <canvas>'s fallback content, an author's class a sheet rule hides, falls to NOT printable; and the figure the placeholder wraps carries
//      none of the kept attributes that would hide it once restored, `hidden`, `popover`, an svg's display none,
//      visibility hidden or opacity 0, an enumeration, since the sheet hides every child of a placeholder but its label
//      and the browser cannot be asked about the figure while it is gated; the third review, 2026-09-19: before this every
//      placeholder was counted and every host it named was loaded, so "with them" fetched from hosts for pictures the
//      print never showed; the round-2 review: the walk alone counted a placeholder the browser never renders). With any,
//      the bar ARMS instead of printing: one line under
//      the title bar names the count and offers "Print with them" and "Print without them"; Escape or a second press
//      disarms (the update banner's two-click shape: the gate is a privacy choice, so a print never fetches from an
//      unlisted host unless the person chose it). "With them" restores exactly the placeholders it counted, each through
//      the gate's restore of ONE placeholder (figure-gate.ts loadGatedFigure: the moved attributes back, the figure back in
//      its place), so the requests are the ones those figures make and no other: a placeholder inside a closed fold or
//      under hidden that names the same host stands as it is (the round-2 review, 2026-09-19: before this "with them"
//      loaded by HOST through loadGatedHost, the click's road, so a host one printable and one folded placeholder shared
//      had both restored and the folded picture fetched for a print that never shows it). A print is a one-time act: the
//      host is not added to the document's loaded set, so the next paint of the page gates its figures again; a click on
//      a placeholder keeps its host-wide, page-life meaning (loadGatedHost, decision 8). Its title names the hosts those
//      placeholders name (the line counts pictures, by contract, and a placeholder naming two hosts says "and 1 more host"
//      in its own label, so the title is where the hosts a press grants are read together). The placeholders are read at
//      the arm and kept: "with them" restores that list and no other, so the title and the restores are one list by
//      construction. A
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
//   2. Then the wait: every <img> in the body THAT REACHES THE PAPER (`printable`, the rule the placeholders are counted
//      by; the shared-host probe, 2026-09-19: before this every picture in the body was awaited, so a host two placeholders
//      shared, one open and one folded, had "with them" restore both and the wait count two, ask at the deadline about the
//      folded one, which the print never shows, and print nothing until the person answered) reaches complete (its load or
//      its error), and a <video poster> or an svg <image> under the same rule is awaited through a probe Image at the
//      same URL (neither element reports completeness; the probe asks the browser for the URL the element itself
//      fetched, so no other host is reached). The probes are ONE PER URL FOR THE
//      LIFE OF ONE PRESS'S WAIT (a Map keyed by the resolved URL, cleared when a press or a choice begins its wait, handed to
//      the collection as its probe factory): a re-aim finds the probe it already made, so a URL whose picture failed settles
//      for good with that one probe complete. Before this every re-aim minted a fresh Image per URL, a failed URL is never
//      complete on a fresh Image, and the driver looped, probe, request, error, settle, re-aim, until the deadline: one press
//      asked the host hundreds of times for one URL (the third review, 2026-09-19, measured 337 requests in 8 s), a request
//      storm from one keystroke. An <img loading="lazy"> the browser has not started fetching (far below the fold) fires
//      neither event, so the collection sets it eager first, which starts the deferred fetch at once (the same URL, so no
//      other host is reached; a gated img has no src and fetches nothing); the attribute stays eager after the print. The
//      wait is bounded by PRINT_SETTLE_MS, 8 s. Its VERDICT reaches the machine as one event, `ready`, carrying why it ended
//      (`settled`, or `deadline`) and the count still loading, so the machine, and any reader of its events, can tell a
//      settle from a deadline: a settle prints, a deadline with a picture still loading ASKS instead of printing (the
//      `stalled` phase), and a deadline that finds nothing loading is a settle in effect and prints (the third review: the
//      first build fed one bare `ready` for both ends, and the deadline's print said nothing). The ask (the third review,
//      2026-09-19): the line reads "N pictures have not loaded." with two word buttons in the armed line's shape, "Print
//      anyway", which prints at once with the picture as the browser has it (in Chromium an empty box), and "Keep
//      waiting", which waits on the load and error events alone, with no timer, until every picture settles, then prints;
//      Escape or a second press under the ask disarms as under the armed line, and Escape during that open-ended wait
//      cancels it (the timed wait's Escape stays the viewer's, which closes the card: that wait ends by itself). Nothing
//      listens under the ask; Keep waiting reads the body as it stands then, so a picture that landed meanwhile is not
//      waited on again and with none left loading the print runs at once. Before this the print ran at the deadline and a
//      picture still loading printed as an empty box with nothing said: a route that never answers raises no error event,
//      so no label stood in for it either (a failed picture, its error event, settles and prints as its label, then as now).
//      The line reads "Preparing N pictures…" meanwhile, beside the viewer's loader (the swirl, the wordmark and the
//      three dots, .fileview-load inline in the row: ui/CLAUDE.md's loading-state rule, which puts the romp loader on every
//      wait; the first build showed the words alone). With no gated placeholder and every picture complete the press
//      prints at once, in the click's own task. The wait is AIMED at the body as it stands, and re-aimed when the
//      body is repainted under it (the host's `body` report: a reload's landing, a format pick, the editor's exit; the
//      pictures listened on were the old body's, detached by the swap) and again at the settle (a picture that entered or
//      was re-aimed since the collection, a heal's retry of a failed figure among them, is awaited too; a URL the retry
//      changed is a new key and is probed once), always under the deadline the press set, never past it (each re-aim's
//      bound executed by its own case of file-print-driver-browser.test.ts: case 3c lands a parked picture by a Reload
//      mid-wait, the repaint's re-aim, and case 12 inserts one inside the rendered root, unseen by the body's observer, and
//      releases the first, the settle's re-aim; each reads the ask at the press's deadline, under 1600 ms after the landing
//      or the release, where a re-aim that restarted the deadline would read about 2000): the print fires with every
//      picture in the body complete, or the deadline asks. A repaint under the ask (a Reload landing, a Rendered or Raw
//      pick, the editor's exit) NEVER prints: it is no answer to the ask. The new body's pictures still loading are counted
//      the same way; over any the line's count follows in place, and over none the question is moot and the flow returns
//      to rest, the line gone, so the person may press again. Before this the count of none was read as the print act and
//      window.print ran with neither button pressed, over the Raw view in one case (the round-2 review, 2026-09-19).
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
// the Outline's Escape do the same for their trigger), or, at a disarm the body going out causes, to the viewer's body
// through the host's takeKeyboard (the changed-on-disk bar's hand-over, file-view.ts dropDiskBar), since the Print button
// is not enabled then; never to the document's body. No kernel route, no server-side render (P6).
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
// The button is DISABLED until the body is in (P7): the flow starts in the `disabled` phase, the button wearing aria-disabled
// and the sheets' disabled dress, and never the `disabled` property (the bar's own rule, file-view.ts textSizeControl: a
// button that disables under keyboard focus drops it on the document's body and leaves the tab order; the third review,
// 2026-09-19). Whether the body is in is READ OFF THE BODY (bodyReady, over the body's element children, each classed by
// its root, `<tag>.<class>`, against three CLOSED lists: READY_ROOTS, NOT_READY_ROOTS and LINE_ROOTS): a MutationObserver
// on them, where the document has one (a DOM stand-in under node has none, and the press's own read below serves alone),
// feeds the machine's `body` event after every paint, and a press reads them again first, so a swap in the press's own task
// is seen before the observer runs. In while a content root stands (a rendered note, code or text, a picture's box, a PDF
// frame's column, under the pages attempt's loader inside it too, the pages' host once drawn, the CodeMirror mount, which
// prints the whole file) and no wait root does; not in while a wait root stands (the viewer's loader: the open's, the
// editor's chunk wait, the Comments panel's PDF pages before page 1 is drawn; the plain fallback editor's textarea, of which
// a print shows one clipped page) or a line root is all it holds (a failure pane: the fetch's, a picture that would not
// decode, the URL viewer's); and NOT in over a child none of the lists names, whatever stands beside it (the round-2
// review, 2026-09-19: the first derivation classed every child it had not seen as content, so an unwired pane would have
// had a live button and a silent print of whatever stood; the safe side is the dead button, and file-print.test.ts's census
// over file-view.ts's seating sites makes a root the viewer gains fail a test until it is listed here). The PDF kind is the
// one exception, for the loader: a body whose kind is known to be a PDF (the host's `kind`, set when the bytes landed) is
// in over the pages attempt's loader too (the Comments panel's pages before page 1 is drawn with no frame kept), since the
// PDF road reads nothing from the body: the press prints through the frame or opens the /file tab, as it did before the
// derivation (the round-2 review: the gate had closed that road, disabling Print and swallowing the chord); a failure pane
// alone stays not in for a PDF too (a reload of it that failed). Before this each viewer paint reported the body in or out
// by hand, and the roads nobody wired were wrong: the plain fallback reported in and printed one clipped page. A press over
// a body not in changes nothing, and the chord is still prevented, so the browser's raw print does not run over the loader
// either; the body going out while the bar is armed or the wait runs disarms (the line goes, the wait is cancelled) and
// disables.
import { GATE_ACT, loadGatedFigure } from "./figure-gate";
import { ICON_PRINT } from "./icons";

/** The wait's deadline: after this, with a picture still loading, the bar asks (the stalled phase) instead of printing. */
export const PRINT_SETTLE_MS = 8000;
let settleMs = PRINT_SETTLE_MS;
/** The test seam: a browser leg that stalls a picture sets a shorter deadline; null restores the constant. Nothing in the
 *  product calls it, and the constant is what the driver reads until it does. */
export function setPrintSettleMs(ms: number | null): void { settleMs = ms === null ? PRINT_SETTLE_MS : ms; }
export function printSettleMs(): number { return settleMs; }

// ── the machine ─────────────────────────────────────────────────────────────────────────────────────
export type PrintPhase = "disabled" | "resting" | "armed" | "preparing" | "stalled" | "printing";
/** `gated`: the placeholders counted at the press that armed; `pending`: the pictures still loading when the wait began, or
 *  when the deadline fell (the ask); `untimed`, on a preparing state alone: Keep waiting's wait, which has no deadline and
 *  which Escape cancels (the press's and the armed line's waits carry the deadline and no mark). */
export type PrintState = { phase: PrintPhase; gated: number; pending: number; untimed?: true };
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
  | { kind: "ready"; why: "settled" | "deadline"; pending: number }   // the wait's verdict: every picture settled (why settled, pending 0), or the deadline fell with `pending` still loading (a deadline with pending 0 is a settle in effect)
  | { kind: "stalled"; pending: number }                 // the driver, after a repaint under the ask: the new body's pictures still loading (none: the ask is moot and the flow rests; never a print)
  | { kind: "anyway" }                                   // the ask's "Print anyway"
  | { kind: "keep" }                                     // the ask's "Keep waiting"
  | { kind: "printed" }                                  // afterprint, or print returned
  | { kind: "body"; in: boolean }                        // the host: the body holds the file's content (true), or the loader or a failure pane took it (false)
  | { kind: "recount"; gated: number };                  // the driver, after a repaint under the armed line: the placeholders the body holds now
/** What the driver does for a step: `arm` shows the line with its two buttons, `disarm` (a second press, Escape, or the body
 *  going out, when the driver cancels a running wait too) and `rest` remove the line and restore the button, `activate` loads
 *  every gated host and then prepares, `skip` prepares over the placeholders as they stand, `wait` shows the preparing line,
 *  `stall` shows the ask (the line with "Print anyway" and "Keep waiting", rewritten in place when it stands), `resume` aims
 *  an open-ended wait at the body and then prepares, `print` calls window.print, `printPdf` prints the PDF itself (the frame's
 *  window, or the /file tab). The button's disabled dress follows the phase, not an act: the driver syncs it after every step. */
export type PrintAct = "none" | "arm" | "disarm" | "activate" | "skip" | "wait" | "stall" | "resume" | "print" | "printPdf" | "rest";

/** The wait begins over `pending` pictures (`wait`), or the print runs at once over none. `untimed` marks Keep waiting's wait. */
const begin = (pending: number, untimed = false): { state: PrintState; act: PrintAct } =>
  pending > 0 ? { state: untimed ? { phase: "preparing", gated: 0, pending, untimed: true } : { phase: "preparing", gated: 0, pending }, act: "wait" } : { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };
/** The ask over `pending` pictures still loading (`stall`): at the deadline, or rewritten in place after a repaint under it. */
const ask = (pending: number): { state: PrintState; act: PrintAct } => ({ state: { phase: "stalled", gated: 0, pending }, act: "stall" });

/** The next state and the act for it. The host's `body` event comes first: the body going out disables from every phase
 *  and disarms (the line goes, and the driver cancels a wait), and its arrival rests a disabled flow and changes nothing
 *  elsewhere by itself (the driver then reads the repainted body: during the wait it re-aims the wait at it, the phase
 *  holding; under the armed line it feeds `recount` with the placeholders the body holds now). Then, by phase:
 *  while disabled every other event changes nothing. A press while resting over a PDF prints the PDF itself (`printPdf`),
 *  whatever the counts (a frame holds no placeholder and no picture); over a document it arms over any gated placeholder
 *  and otherwise begins the wait (or prints at once with nothing pending); while armed a press or Escape disarms, a
 *  choice activates or skips, the driver's `prepare` then beginning the wait, and a `recount` arms again over the new count
 *  (`arm`: the driver rewrites the line and the title in place) or disarms over none (the placeholders the line asked about
 *  are gone, so the question is moot; the next press prints); while preparing the wait's verdict `ready` prints when it
 *  settled, asks when the deadline fell with a count still loading, and prints when the deadline found none loading (a
 *  settle in effect), and Escape cancels Keep waiting's open-ended wait (`untimed`) and nothing else; while
 *  stalled a press or Escape disarms, `anyway` prints, `keep` resumes (the driver aims the open-ended wait and its `prepare`
 *  begins it, or prints with nothing left loading), and a `stalled` from a repaint asks again over the new count or, over
 *  none, DISARMS (the question is moot, and a repaint is no answer to it: the round-2 review, 2026-09-19, before which the
 *  count of none was read as the print act and window.print ran with neither button pressed); `printed` rests. Every other pairing changes nothing: a press during the wait or the print, an Escape during
 *  the timed wait or the print, an Escape at rest, a late `ready` after a rest, a `printed` after the body went out (the
 *  button stays disabled), a `recount` in any phase but armed, a `stalled` in any phase but the ask (no timer feeds it: the
 *  deadline is the verdict's), a `ready` or a choice under the ask. */
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
      if (ev.kind === "ready") return ev.why === "deadline" && ev.pending > 0 ? ask(ev.pending) : { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };
      if (ev.kind === "escape" && s.untimed === true) return { state: RESTING, act: "disarm" };
      break;
    case "stalled":
      if (ev.kind === "press" || ev.kind === "escape") return { state: RESTING, act: "disarm" };
      if (ev.kind === "anyway") return { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };
      if (ev.kind === "keep") return { state: s, act: "resume" };
      if (ev.kind === "prepare") return begin(ev.pending, true);
      if (ev.kind === "stalled") return ev.pending > 0 ? ask(ev.pending) : { state: RESTING, act: "disarm" };   // a repaint under the ask never prints: the line follows the count, or goes with the last picture
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
/** The ask's words at the deadline: `n` pictures still loading. */
export function stalledWords(n: number): string {
  return n === 1 ? "1 picture has not loaded." : n + " pictures have not loaded.";
}
export const WITH_WORDS = "Print with them";
export const WITHOUT_WORDS = "Print without them";
/** The ask's two word buttons and their titles. */
export const ANYWAY_WORDS = "Print anyway";
export const KEEP_WORDS = "Keep waiting";
export const ANYWAY_TITLE = "Print now; a picture still loading prints as the browser has it";
export const KEEP_TITLE = "Wait for every picture to load, then print";
/** "Print with them"'s title: the hosts the placeholders name, in the order they appear, so the hosts one press fetches from
 *  can be read together before the press (for this print alone: loadGatedFigure grants a host nothing for the page, which a
 *  click does, decision 8); the line itself counts pictures, by contract. With none known (a stand-in body) the words name
 *  them generically. */
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
/** What the printable test reads of a node: its name, its attributes and its parent (an Element, or a stand-in in a test),
 *  and, where the browser can be asked, its own rendering (checkVisibility and getClientRects; absent on a stand-in). */
export type PrintableNode = { localName: string; parentElement: PrintableNode | null; hasAttribute(name: string): boolean;
  checkVisibility?(options?: { visibilityProperty?: boolean; opacityProperty?: boolean }): boolean; getClientRects?(): ArrayLike<unknown> };
/** The browser's own answer whether `el` is rendered: checkVisibility, with visibility and opacity read (an svg's
 *  `visibility="hidden"` or `opacity="0"`, kept attributes, leave nothing on the paper; content-visibility auto is left
 *  alone: the sheets use none, and a picture far below the fold is on the paper), AND at least one client rect (an svg
 *  <image> inside <defs>, a <symbol>, a <clipPath>, a <mask>, a <pattern> or a <marker> has a layout object and no rect,
 *  which checkVisibility alone reads as rendered; a closed fold's content and a `hidden="until-found"` ancestor's keep
 *  their rects and are skipped, which the rects alone read as rendered). Null where the browser cannot be asked (a stand-in
 *  under node, an engine without checkVisibility): the walk alone decides then. Measured in Chromium, 2026-09-19: a picture
 *  still loading, one with no src (a gated one) and one far below the fold each have a rect and are visible; one inside a
 *  ruby's <rp>, a <canvas>'s or a <video>'s fallback content or a `popover` not shown has none. */
export function rendered(el: PrintableNode): boolean | null {
  if (typeof el.checkVisibility !== "function" || typeof el.getClientRects !== "function") return null;
  return el.checkVisibility({ visibilityProperty: true, opacityProperty: true }) && el.getClientRects().length > 0;
}
/** Whether `el` reaches the paper. First the walk: nothing from it up to the root is a closed <details> holding it outside
 *  that details' own <summary> (the fold's content is not rendered; its summary is), and nothing carries the `hidden`
 *  attribute, whatever its value (`until-found` included: the browser skips such content until a find or a fragment reveals
 *  it). The same ancestor walk md-sanitize.ts revealFragmentTarget runs, read rather than applied. Both shapes come from the
 *  author: a typed <details>, a folded callout (`> [!type]-`, md-config.ts) and `hidden` all pass the sanitizer, where an
 *  inline `display: none` does not (colorOnlyStyle keeps colour declarations alone), so a picture under that style prints
 *  and is printable here. Then the browser's own answer (rendered), where it can be asked: the walk knows two hidings, and
 *  the sanitizer keeps others the walk does not (a `popover` attribute, whose element is shown by a call alone; a ruby's
 *  <rp>; a <canvas>'s fallback content; an svg's <defs>; an author's class a sheet rule hides), so the UNKNOWN side falls
 *  to NOT printable: printable is true only when both agree (the round-2 review, 2026-09-19: before this the walk alone
 *  answered, and every hiding it did not know read as printable, the permissive side for a fetch). A placeholder the flow
 *  counts, names in the with-button's title or restores must pass this and figurePrintable below (gates, in the driver): a
 *  host is a privacy choice, and a print fetches from one only for a picture that is on the paper. */
export function printable(el: PrintableNode): boolean {
  for (let n: PrintableNode | null = el; n; n = n.parentElement) {
    if (n.hasAttribute("hidden")) return false;
    const p = n.parentElement;
    if (p && p.localName === "details" && n.localName !== "summary" && !p.hasAttribute("open")) return false;
  }
  return rendered(el) !== false;
}
/** What figureHidden reads of a placeholder's figure: its name and its attributes. */
export type FigureNode = { localName: string; hasAttribute(name: string): boolean; getAttribute(name: string): string | null };
/** A CSS keyword attribute's value, trimmed and lower-cased (an svg presentation attribute is CSS: `NONE` and ` none ` are `none`). */
const keyword = (el: FigureNode, name: string): string => (el.getAttribute(name) || "").trim().toLowerCase();
/** Whether the figure a placeholder wraps carries, ITSELF, a kept attribute that leaves it off the paper once restored. An
 *  enumeration over the sanitizer's kept attributes (md-sanitize.ts MD_PURIFY: DOMPurify's html and svg attribute lists,
 *  `style` filtered to colour), since the browser cannot be asked here: the sheet hides every child of a placeholder but its
 *  label while it is gated, so checkVisibility on the figure says hidden for every one. On any element: `hidden`, whatever
 *  its value, and `popover` (shown by a call alone, which a note cannot make). On an svg, the presentation attributes that
 *  hide it whole: `display="none"`, `visibility="hidden"` or `"collapse"`, `opacity` zero (a number or a percentage).
 *  Every other kept attribute leaves the figure on the paper as far as the flow reads: a zero `width` or `height` is a
 *  degenerate picture the browser still draws and fetches; an svg's `transform`, `clip-path`, `mask` and `filter` can hide
 *  its paint and are not read (the placeholder's own rendering, above, is). Before this the walk started at the placeholder
 *  and never looked at the figure inside it, so `<img hidden src="https://host/p.svg">` had its placeholder counted, its
 *  host named and, on "Print with them", its picture fetched for a print that never shows it (the round-2 census). */
export function figureHidden(el: FigureNode): boolean {
  if (el.hasAttribute("hidden") || el.hasAttribute("popover")) return true;
  if (el.localName !== "svg") return false;
  if (keyword(el, "display") === "none") return true;
  const vis = keyword(el, "visibility");
  if (vis === "hidden" || vis === "collapse") return true;
  const op = keyword(el, "opacity");
  return op !== "" && /^[0.]+%?$/.test(op) && parseFloat(op) === 0;
}
/** Whether a placeholder reaches the paper AND the figure it stands for would once restored: printable on the placeholder
 *  (the walk, and the browser's own answer), and figureHidden false on the media element it wraps (its first element
 *  child; the label follows it). A placeholder with no figure inside answers for itself. */
export function figurePrintable(g: PrintableNode & { firstElementChild?: FigureNode | null }): boolean {
  if (!printable(g)) return false;
  const figure = g.firstElementChild;
  return !figure || !figureHidden(figure);
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
/** Every picture under `body` the print waits on: each <img> as itself, and a probe (`probe(url)`: the driver's, one Image
 *  per URL for the life of one press's wait) for each <video poster> and each svg <image href>, whose elements report no
 *  completeness. Each of the three collections is filtered by `printable`, the rule the placeholders are counted by (the
 *  <img> itself; the <video> for its poster; the svg <image> element): the wait, its count on the line, the eager flip and
 *  the deadline's ask cover the pictures that reach the paper alone. A picture inside a closed fold or under `hidden` can
 *  still be loading during the wait: the browser fetches an <img> the fold hides when its host is allowed, at the render;
 *  before this the wait read it too, so the line counted a picture the print never shows and, with that picture's route
 *  slow, the deadline asked about it and nothing printed until the person answered (the shared-host probe, 2026-09-19;
 *  "Print with them" then restored by host, so a folded placeholder sharing a host with a printable one was restored and
 *  fetched too, which the per-placeholder restore since the round-2 review no longer does). The browser's own answer is
 *  read through printable as well (rendered): a picture inside a ruby's <rp>, a <canvas>'s fallback content or a `popover`
 *  not shown, or an svg <image> inside <defs>, is not awaited, not set eager and not probed, so no request the render did
 *  not make is made for a picture the print never shows. An <img loading="lazy"> is set eager first: the browser has deliberately not started
 *  fetching one far below the fold, so it would fire neither load nor error and the wait would run to its deadline over
 *  it; eager starts the deferred fetch at once, for the same URL (no other host is reached; a gated img has no src and
 *  fetches nothing), and the attribute stays eager after the print; a hidden or folded lazy picture is left as it is, so
 *  no fetch is started for a picture that is not on the paper. A gated element has its poster or href moved aside
 *  (figure-gate.ts) and is not probed; a gated img has no src, and an img with no src is complete by HTML's definition, so
 *  "Print without them" waits on nothing for a placeholder. */
export function collectPictures(body: ParentNode, base: string, probe: (url: string) => Picture): Picture[] {
  const out: Picture[] = [];
  body.querySelectorAll("img").forEach((el) => { if (!printable(el)) return; const img = el as HTMLImageElement; if (img.loading === "lazy") img.loading = "eager"; out.push(img); });
  body.querySelectorAll("video[poster]").forEach((v) => { if (!printable(v)) return; const u = resolved(v.getAttribute("poster"), base); if (u) out.push(probe(u)); });
  body.querySelectorAll("image").forEach((im) => { if (!printable(im)) return; const u = resolved(im.getAttribute("href"), base); if (u) out.push(probe(u)); });
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
 *  first; with `deadlineMs` null (Keep waiting) no timer is set and the events alone end the wait. The listeners come off at
 *  the end whichever way it ends, and the timer is cleared. With nothing pending the promise resolves `settled` and no timer
 *  is set. */
export function settlePictures(pics: Picture[], deadlineMs: number | null, timers: Timers = REAL_TIMERS): Settle {
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
  else if (deadlineMs !== null) timer = timers.setTimeout(() => end("deadline"), deadlineMs);
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

// ── the body's readiness (P7) ────────────────────────────────────────────────────────────────────────
/** What the readiness test reads of one child of the body: its name and its class list (an Element, or a stand-in). */
export type BodyChild = { localName: string; classList: { contains(name: string): boolean } };
/** What the readiness test reads of the body: its element children, through `children` where the body has it (a DOM
 *  element always does), else through `childNodes` filtered to element nodes (the DOM stand-ins of the node suites, which
 *  drive the real viewer over bodies with childNodes alone; the round-2 review, 2026-09-19: a read of `children` alone threw
 *  at every open over fourteen of them). */
export type BodyLike = { children?: ArrayLike<BodyChild>; childNodes?: ArrayLike<{ nodeType: number }> };
/** The body's element children, as BodyLike says; none for a body that reports neither list (no DOM body does). */
function elementChildren(body: BodyLike): BodyChild[] {
  if (body.children) return Array.from(body.children);
  if (body.childNodes) return Array.from(body.childNodes).filter((n) => n.nodeType === 1) as unknown as BodyChild[];
  return [];
}
/** The roots file-view.ts seats in the body, as `<tag>.<class>`, by how bodyReady reads each: content (READY_ROOTS: the
 *  body is in with one standing and no wait root beside it), a wait (NOT_READY_ROOTS: not in while one stands, whatever
 *  else does, the PDF kind's loader aside) or a line (LINE_ROOTS: alone not in, over content a notice above it). The lists
 *  are CLOSED: a child matching none is unknown, and the body is not in over it (rootKind, bodyReady). The sites are the
 *  viewer's `body.replaceChildren`, `body.prepend` and `body.appendChild` calls, the seated element read down to the
 *  `el("<tag>", "<class>")` that builds it; file-print.test.ts's census derives that set from file-view.ts, holds it equal
 *  to these three lists, and executes bodyReady over each root as its list says, so a root the viewer gains fails that test
 *  until it is listed here, rather than being answered by a guess (the round-2 review, 2026-09-19: the first derivation
 *  answered content for every child it had not seen, the permissive side for a print button). */
export const READY_ROOTS: readonly string[] = ["div.fileview-md", "div.fileview-code", "div.fileview-imgbox", "div.fileview-pdffall", "div.fileview-pdfhost", "div.fileview-cm"];
export const NOT_READY_ROOTS: readonly string[] = ["div.fileview-load", "textarea.fileview-editor"];
export const LINE_ROOTS: readonly string[] = ["div.fileview-err"];
/** The one wait root the PDF kind reads as content: the pages attempt's loader (file-view.ts showPdfPages, with no frame
 *  kept), since the PDF road reads nothing from the body. */
export const PDF_LOADER_ROOT = "div.fileview-load";
export type RootKind = "content" | "wait" | "line" | "unknown";
/** Whether `c` is one of `roots`: its localName the tag and its class list holding the class (the element may carry more). */
const isRoot = (c: BodyChild, roots: readonly string[]): boolean => roots.some((r) => { const [tag, cls] = r.split("."); return c.localName === tag && c.classList.contains(cls); });
/** How bodyReady reads one child of the body: by which list its `<tag>.<class>` is on, else unknown. A stand-in without a
 *  localName is unknown, so a stand-in body is never in by accident. */
export function rootKind(c: BodyChild): RootKind {
  if (isRoot(c, READY_ROOTS)) return "content";
  if (isRoot(c, NOT_READY_ROOTS)) return "wait";
  if (isRoot(c, LINE_ROOTS)) return "line";
  return "unknown";
}
/** The body holds the file's content, read off its element children (P7; the driver reads it through a MutationObserver on
 *  them, where the document has one, and again at each press), each classed by rootKind. Not while a wait root stands
 *  (`div.fileview-load`, the viewer's loader as the body's content: the open's, the editor's chunk wait, the Comments
 *  panel's PDF pages before page 1 is drawn; the pages attempt over a KEPT frame puts its loader inside the frame's column,
 *  so the frame stays the content and the button stays live; `textarea.fileview-editor`, the plain fallback editor, a
 *  scrollable control of which the browser prints one clipped page), not while a line root is all the body holds
 *  (`div.fileview-err` and nothing else: the fetch's pane, a picture that would not decode, the URL viewer's failure), and
 *  NOT while a child none of the lists names stands, whatever else does: the flow cannot say what a press would print, so
 *  the button stays disabled (the safe side; the census in file-print.test.ts is what makes a new root a red test rather
 *  than a dead button). In when a content root stands and nothing above holds: the rendered root, the code block (a
 *  `div.fileview-err` line above either, an empty file's or a render that fell, is a line over content, not a pane), a
 *  picture's box, a PDF frame's column (the pages attempt's notice inside it included), the pages' host once the loader has
 *  gone, the CodeMirror mount (`div.fileview-cm`, which prints the whole file). An empty body is not in. `kind` is the file's
 *  (the host's `kind` at the read): for a PDF the loader (PDF_LOADER_ROOT) reads as content, since the PDF road reads nothing
 *  from the body and a press prints through the frame or opens the /file tab (the round-2 review, 2026-09-19: the derivation
 *  had disabled Print and swallowed the chord over the Comments panel's pages loader, where the build before it opened the
 *  tab); the editor's textarea, a line root alone and an unknown child stay not in for a PDF too. */
export function bodyReady(body: BodyLike, kind: PrintKind = "document"): boolean {
  let content = false;
  for (const c of elementChildren(body)) {
    const k = rootKind(c);
    if (k === "unknown") return false;
    if (k === "wait") {
      if (kind === "pdf" && isRoot(c, [PDF_LOADER_ROOT])) { content = true; continue; }
      return false;
    }
    if (k === "content") content = true;
  }
  return content;
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
  /** the viewer's own hand-over of the keyboard to its body (file-view.ts openFileView's takeKeyboard, which yields to a
   *  holder outside the bar): at a disarm the body going out causes, a word button of the line that held the keyboard hands
   *  it there, as the changed-on-disk bar's Reload does when its bar goes (dropDiskBar), since the Print button is not
   *  enabled then. Absent (the URL viewer), the button takes it */
  takeKeyboard?: () => void;
};
export const PRINT_LINE_ID = "fileview-print-line";
export const PRINT_LINE_CLASS = "fileview-print-line";

/** Build the Print button for a viewer and wire the flow to it and to the document's keydown; the caller puts the button
 *  in its bar and paints its body as it does: whether the body is in (P7) is read off the body's children here (bodyReady,
 *  through a MutationObserver on them and again at each press), so the caller reports nothing. The button starts disabled
 *  over an empty body or the caller's loader. `data-print` on the button carries the phase while it is not resting
 *  (`disabled` included), for the sheets and the tests. */
export function installFilePrint(host: PrintHost): { button: HTMLButtonElement } {
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
  let state: PrintState = DISABLED;            // the machine's start; onBody below reads the body as it stands at the install (the loader, or nothing yet) and at every paint after
  let line: HTMLElement | null = null;
  let withBtn: HTMLButtonElement | null = null;   // the armed line's "Print with them", while the line stands: a re-arm rewrites its title in place
  let asked = false;                           // the line standing is the deadline's ask: a repaint under it rewrites the count in place
  let armedGates: HTMLElement[] = [];          // the placeholders the armed line counted: read at the arm and at each re-arm, and the list "with them" restores (one list, so the title names what the click fetches)
  let armedHosts: string[] = [];               // the hosts those placeholders name, in the with-button's title
  let notice = false;                          // the line is the PDF flow's notice (the tab), standing at rest until the next press or the close
  let settle: Settle | null = null;
  let waitEnds = 0;                            // when the running wait's deadline falls (Date.now()): a re-aim keeps it and never extends it
  let closed = false;

  /** The body's placeholders that reach the paper (figurePrintable): the ones the press counts, the title names and "with
   *  them" restores. One inside a closed fold or under hidden, one the browser does not render, or one whose figure carries
   *  an attribute that hides it is left out, since the print never shows it. */
  const gates = (): HTMLElement[] => (Array.from(host.body.querySelectorAll('[data-act="' + GATE_ACT + '"]')) as HTMLElement[]).filter(figurePrintable);
  /** Every host the placeholders `list` name, once each, in the order the placeholders name them. */
  const hostsOf = (list: HTMLElement[]): string[] => {
    const hosts = new Set<string>();
    for (const g of list) for (const h of (g.getAttribute("data-fv-hosts") || "").split(" ")) if (h) hosts.add(h);
    return Array.from(hosts);
  };
  /** This press's probes by resolved URL, one Image each for the life of one press's wait: a re-aim (at a settle, at a
   *  repaint) finds the probe it already made instead of minting one, so a URL whose picture failed is asked for once and
   *  settles for good (a failed Image is complete; a fresh one never was). Cleared when a press or a choice begins its wait
   *  (beginWait), never per re-aim, so the next press probes the body afresh and a URL a heal retry changed is a new key. */
  const probes = new Map<string, Picture>();
  const probe = (url: string): Picture => {
    let p = probes.get(url);
    if (!p) { const im = new Image(); im.src = url; p = im; probes.set(url, p); }
    return p;
  };
  /** Remove the line. A word button of it holding the keyboard hands it back to the Print button, the trigger (the zoom
   *  flyout's and the Outline's Escape do the same for theirs), or, when the disarm is the body going out (`bodyOut`), to
   *  the viewer's body through the host's takeKeyboard (the changed-on-disk bar's hand-over, dropDiskBar: the button is not
   *  enabled then), read before the removal and handed after it, as that bar does; the browser's fixup would drop it on the
   *  document's body otherwise, where the next key scrolls nothing. Not at the close, where the card goes with the line. */
  const dropLine = (bodyOut = false): void => {
    if (line) {
      const held = !closed && line.contains(doc.activeElement);
      line.remove(); line = null; withBtn = null; asked = false;
      if (held) { if (bodyOut && host.takeKeyboard) host.takeKeyboard(); else btn.focus({ preventScroll: true }); }
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
    const asks = state.phase === "armed" || state.phase === "stalled";   // the line is a question with word buttons, opened by the button
    const busy = state.phase === "preparing" || state.phase === "printing";
    // aria-disabled, not `disabled` (the bar's own rule, file-view.ts textSizeControl, copied whole): a button that disables
    // under keyboard focus drops it (the ring would vanish on the press that reached the end; here, the body going out while
    // a word button of the line held the keyboard handed it to this button and the property then dropped it on the
    // document's body in the same tick), while an aria-disabled one keeps the focus, wears the sheet's disabled dress
    // (.fileview-btn[aria-disabled="true"], the same rule as :disabled in both sheets), and its press is the no-op the
    // disabled phase already makes of it (the machine ignores a press there, and the chord is prevented before it)
    if (off) btn.setAttribute("aria-disabled", "true"); else btn.removeAttribute("aria-disabled");
    btn.classList.toggle("on", asks);
    btn.classList.toggle("fileview-busy", busy);
    if (asks) btn.setAttribute("aria-expanded", "true"); else btn.removeAttribute("aria-expanded");
    if (busy) btn.setAttribute("aria-busy", "true"); else btn.removeAttribute("aria-busy");
    if (state.phase === "resting") delete btn.dataset.print; else btn.dataset.print = state.phase;
  };
  const dropSettle = (): void => { if (settle) { settle.cancel(); settle = null; } };
  /** The running wait's deadline: the time left to the press's, or null for Keep waiting's open-ended wait, which has none. */
  const timeLeft = (): number | null => (state.phase === "preparing" && state.untimed === true ? null : Math.max(0, waitEnds - Date.now()));
  /** The wait's line reads `n` pictures: rewritten in place when the wait's line stands (its loader marks it), so a re-aim
   *  moves nothing and restarts no animation; shown afresh otherwise (after the armed line, or the ask's). */
  const preparingLine = (n: number): void => {
    if (line && line.querySelector(".fileview-print-load")) { line.firstChild!.textContent = preparingWords(n); return; }
    showLine(preparingWords(n), true);
  };
  /** Aim the wait at the body as it stands, under `deadlineMs` (null: no deadline): collect, listen, and at the settle read
   *  the body again (a picture that entered or was re-aimed since the collection is awaited too, under the time left) or feed
   *  the verdict: `ready` settled with nothing loading, or `ready` deadline with the count still loading, on which the bar
   *  asks (or prints, when the deadline found none). The count still loading; 0 with nothing to wait on (no listener, no
   *  timer). */
  const aimWait = (deadlineMs: number | null): number => {
    dropSettle();
    const s = settlePictures(collectPictures(host.body, doc.baseURI, probe), deadlineMs);
    const n = s.pending();
    if (n === 0) { s.cancel(); return 0; }
    settle = s;
    void s.done.then((why) => {
      if (settle !== s) return;                 // cancelled, or replaced by a later wait
      settle = null;
      if (why === "cancelled" || closed || !host.card.isConnected) return;
      if (why === "deadline") { feed({ kind: "ready", why, pending: s.pending() }); return; }   // the deadline's verdict, with the count still loading: the bar asks over any (nothing listens under the ask), and prints over none
      const left = timeLeft();
      if (left === null || left > 0) {
        const more = aimWait(left);             // the body as it stands now: something entered or was re-aimed since the collection (the probes are this press's, so a URL already asked for is not asked for again)
        if (more > 0) { preparingLine(more); return; }
      }
      feed({ kind: "ready", why: "settled", pending: 0 });
    });
    return n;
  };
  /** Begin the wait, at a press or a choice: the full deadline from now, and this press's probes afresh. */
  const beginWait = (): number => { probes.clear(); waitEnds = Date.now() + settleMs; return aimWait(settleMs); };
  /** The body repainted during the wait (the observer: a reload's landing, a format pick, the editor's exit): the pictures
   *  listened on were the old body's, detached by the swap, so the wait is aimed at the new body under the time left (none
   *  for Keep waiting's wait); with nothing loading there the print runs at once, a settle in effect, and the line's count
   *  follows. The machine holds the phase (its `body` in during the wait is `none`): the re-aim is the driver's, as the
   *  collection is. */
  const reaim = (): void => {
    const n = aimWait(timeLeft());
    if (n === 0) { feed({ kind: "ready", why: "settled", pending: 0 }); return; }
    preparingLine(n);
  };
  /** The body repainted under the ask: the new body's pictures still loading are counted through the wait's own collection
   *  and the listeners come off again, since nothing is awaited under the ask; the machine's `stalled` then rewrites the
   *  count in place, or over none loading disarms (the question is moot; a repaint is no answer to it, so nothing prints and
   *  the person may press again). */
  const recountAsk = (): void => { const n = aimWait(null); dropSettle(); feed({ kind: "stalled", pending: n }); };
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
        armedGates = gates(); armedHosts = hostsOf(armedGates);   // the placeholders the press would restore and the hosts they name, read together (the header) and kept for the click
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
      case "disarm": dropSettle(); dropLine(ev.kind === "body"); break;   // the body going out during the wait: no wait survives a disarm; a word button of the line that held the keyboard hands it to the viewer's body then
      case "rest": dropLine(); break;
      case "activate": {
        // exactly the placeholders the armed line counted, each restored alone through the gate's one-placeholder restore
        // (loadGatedFigure): the figure's own fetch and no other, a placeholder naming two hosts fetching from both as its
        // title said, and no page-life grant for any host (a click's meaning, kept for the click: loadGatedHost). The list is
        // the arm's (re-read at each recount), never the body's at the click: the title and the restores are one list. A
        // placeholder inside a closed fold or under hidden that names the same host is not in the list and stands. One a
        // repaint detached meanwhile is skipped (a detached img fetches too once its src is back); the recount that repaint
        // ran has re-read the list, so none is expected
        for (const g of armedGates) if (host.body.contains(g)) loadGatedFigure(g);
        feed({ kind: "prepare", pending: beginWait() });
        return;
      }
      case "skip": feed({ kind: "prepare", pending: beginWait() }); return;
      case "wait": showLine(preparingWords(state.pending), true); break;
      case "stall": {
        // the deadline's ask, in the armed line's shape (the words, then two word buttons with titles); a repaint under a
        // standing ask rewrites the words in place, as a recount does the armed line's
        const words = stalledWords(state.pending);
        if (line && asked) { line.firstChild!.textContent = words; break; }
        const row = showLine(words);
        for (const [btnWords, title, answer] of [[ANYWAY_WORDS, ANYWAY_TITLE, { kind: "anyway" }], [KEEP_WORDS, KEEP_TITLE, { kind: "keep" }]] as Array<[string, string, PrintEvent]>) {
          const b = doc.createElement("button") as HTMLButtonElement;
          b.type = "button"; b.textContent = btnWords;
          b.className = "fileview-btn fileview-err-act";
          b.title = title;
          b.addEventListener("click", () => { feed(answer); });
          row.appendChild(b);
        }
        asked = true;
        break;
      }
      case "resume": feed({ kind: "prepare", pending: aimWait(null) }); return;   // Keep waiting: the body as it stands now, under no deadline; with nothing left loading the print runs at once
      case "print": dropLine(); syncButton(); doPrint(); return;   // doPrint feeds `printed` itself, which syncs
      case "printPdf": dropLine(); syncButton(); doPrintPdf(); return;   // doPrintPdf feeds `printed` too
      case "none": break;
    }
    syncButton();
  };
  const press = (): void => {
    if (notice) dropLine();                    // the last press's notice (a PDF's tab) goes with this press
    if (ready() !== (state.phase !== "disabled")) onBody();   // the body changed in this same task and the observer has not run yet: read it first, so the press acts on the body as it stands (P7)
    if (state.phase !== "resting") { feed({ kind: "press", gated: 0, pending: 0 }); return; }   // disabled: nothing (the body is not in); armed, or the ask: the second press disarms; busy: nothing
    const file = kindNow();
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
  /** The phases whose Escape is the bar's: the armed line and the deadline's ask (each a question with word buttons, which a
   *  second press disarms too), and Keep waiting's open-ended wait, which no deadline ends. The timed wait's Escape stays the
   *  viewer's, which closes the card (that wait ends within PRINT_SETTLE_MS by itself). */
  const escapable = (): boolean => state.phase === "armed" || state.phase === "stalled" || (state.phase === "preparing" && state.untimed === true);
  const onKey = (e: KeyboardEvent): void => {
    if (e.key === "Escape") {
      if (e.cancelBubble) return;                // a listener ahead of this one on the document stopped the key: it is that control's (the text-size flyout's dismiss, file-view.ts wireZoomDismiss, a capture listener wired before this per-open one, which closes the flyout and stops the event; stopPropagation stops no listener on the same node, and the flag, the DOM standard's alias for the stop propagation flag, is how a later one reads the claim). The bar stays armed for the next Escape
      if (!escapable() || ownsEscape(e.target, host.card) || host.typing()) return;   // at rest, during the timed wait and during the print the viewer's own Escape closes the card; from inside a menu or a dialog, with a popup open in the card (its own handler running after this listener) or from a text field (the Comments composer, whose Escape cancels the draft) the Escape is that control's, and the next one disarms
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
  /** The file's kind as the host reads it now: a PDF once its bytes landed, else a document (the URL viewer names none). */
  const kindNow = (): PrintKind => (host.kind ? host.kind() : "document");
  /** The body holds the file's content, as its children stand now (bodyReady, P7), under the file's kind. */
  const ready = (): boolean => bodyReady(host.body, kindNow());
  /** The body's children changed (the observer, after every paint of the host's; a press reads it first too): the machine
   *  rests or disables from what the body holds now, and a flow under way is disarmed when it went out. A paint under the
   *  armed line has the placeholders counted again (the line's words and the hosts its title grants follow the repainted
   *  body, or the line goes with the last placeholder); a paint under the wait re-aims it; a paint under the ask counts the
   *  new body's pictures still loading again. A change that leaves the body in and the phase at rest changes nothing. */
  const onBody = (): void => {
    if (closed) return;
    const present = ready();
    feed({ kind: "body", in: present });
    if (!present) return;
    if (state.phase === "armed") feed({ kind: "recount", gated: gates().length });
    else if (state.phase === "preparing") reaim();
    else if (state.phase === "stalled") recountAsk();
  };
  // the body's element children: every paint swaps them (replaceChildren, the loader's removal at page 1); the callback runs
  // after the task that painted, before any key or click. Guarded as watchBodyWidth guards ResizeObserver (file-view.ts): a
  // document without the API (the DOM stand-ins of the node suites, which drive the real viewer and construct this on every
  // open; the round-2 review, 2026-09-19, when the bare construction threw at openFileView in 24 of them) gets no observer,
  // and the press's own read of the body (press) is what the button's dress follows then
  const observer = typeof MutationObserver === "function" ? new MutationObserver(onBody) : null;
  if (observer) observer.observe(host.body, { childList: true });
  host.onClose(() => {
    closed = true;
    if (observer) observer.disconnect();
    doc.removeEventListener("keydown", onKey, true);
    dropSettle();
    dropLine();
  });
  onBody();                                    // the body as it stands at the install: the loader, or nothing yet (the disabled dress from the build)
  return { button: btn };
}
