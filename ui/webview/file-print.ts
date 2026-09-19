// Print a file from the viewer, with its pictures (the print follow-on to plans/markdown-viewer.md's Slice 3, item 12; the
// contract of 2026-09-19, parts P1, P2 and P6). The @media print block in the sheets prints the open file alone, black on
// white, but nothing awaited the pictures: the browser's own Ctrl/Cmd+P printed a gated figure as its placeholder and a
// picture still loading as the browser had it at that instant. This module is the flow in front of window.print():
//   1. A press (the bar's Print glyph button, Download's shape, or Ctrl/Cmd+P while a file is open and no text field holds the keyboard)
//      counts the gated placeholders in the body (figure-gate.ts, found by their data-act as the gate finds them: an
//      author can type the class, never the data attribute). With any, the bar ARMS instead of printing: one line under
//      the title bar names the count and offers "Print with them" and "Print without them"; Escape or a second press
//      disarms (the update banner's two-click shape: the gate is a privacy choice, so a print never fetches from an
//      unlisted host unless the person chose it). "With them" loads every host the placeholders name through
//      loadGatedHost, the function the placeholder's own click runs, so the requests are the ones a click on each makes.
//   2. Then the wait: every <img> in the body reaches complete (its load or its error), and a <video poster> or an svg
//      <image> is awaited through a probe Image at the same URL (neither element reports completeness; the probe asks the
//      browser for the URL the element itself fetched, so no other host is reached), bounded by PRINT_SETTLE_MS, 8 s,
//      after which the print runs anyway: a picture still loading prints as the browser has it, a failed one as its
//      label. The line reads "Preparing N pictures…" meanwhile. With no gated placeholder and every picture complete the
//      press prints at once, in the click's own task.
//   3. window.print(). On afterprint, or at once when print returns, the bar rests.
// The machine is `step`, a pure function over PrintState and PrintEvent returning the next state and the act the driver
// performs; settlePictures takes any objects with `complete` and the two event methods, and timers a test injects
// (file-print.test.ts runs both under node with fake pictures and a fake clock). installFilePrint is the DOM driver both
// viewers call (file-view.ts openFileView and openUrlView): the button, the line, the wait, the print. It registers ONE
// document keydown listener per open, in the capture phase, so an Escape while armed is stopped before the viewer's own
// Escape (a bubble listener on the document, which closes the card) and the chord is prevented before the browser's raw
// print runs; the host's close hook removes it with the viewer. Nothing else is registered. The line is a row of the card
// in the notice bar's dress (.fileview-err, with .fileview-btn.fileview-err-act word buttons: the changed-on-disk bar's
// shape, file-view.ts raiseDiskBar), so it needs no rule of its own and the print block, which hides every
// `.fileview > .fileview-err`, leaves it off the paper. No kernel route, no server-side render (P6).
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
  | { kind: "body"; in: boolean };                       // the host: the body holds the file's content (true), or the loader or a failure pane took it (false)
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
 *  elsewhere. Then, by phase: while disabled every other event changes nothing. A press while resting over a PDF prints the
 *  PDF itself (`printPdf`), whatever the counts (a frame holds no placeholder and no picture); over a document it arms over
 *  any gated placeholder and otherwise begins the wait (or prints at once with nothing pending); while armed a press or
 *  Escape disarms and a choice activates or skips, the driver's `prepare` then beginning the wait; `ready` prints; `printed`
 *  rests. Every other pairing changes nothing: a press or an Escape during the wait or the print, an Escape at rest, a late
 *  `ready` after a rest, a `printed` after the body went out (the button stays disabled). */
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
/** The PDF flow's line when the frame could not print and the /file URL opened in a new tab. */
export const TAB_WORDS = "Print from the tab that opened.";
/** ...and when the browser did not open that tab (a blocked pop-up, or a host that cannot open one). */
export const NO_TAB_WORDS = "The browser did not open a tab for this PDF.";

/** The print chord: Ctrl+P or Cmd+P, unshifted, without Alt, and not a key repeat (a held chord would arm and disarm on
 *  alternate repeats). The key is read case-insensitively: Caps Lock reports "P" with no Shift. */
export function isPrintChord(e: { key?: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean; shiftKey?: boolean; repeat?: boolean }): boolean {
  return (e.ctrlKey === true || e.metaKey === true) && e.altKey !== true && e.shiftKey !== true && e.repeat !== true && typeof e.key === "string" && e.key.toLowerCase() === "p";
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
  let notice = false;                          // the line is the PDF flow's notice (the tab), standing at rest until the next press or the close
  let settle: Settle | null = null;
  let closed = false;

  const gates = (): HTMLElement[] => Array.from(host.body.querySelectorAll('[data-act="' + GATE_ACT + '"]')) as HTMLElement[];
  const probe = (url: string): Picture => { const im = new Image(); im.src = url; return im; };
  const dropLine = (): void => { if (line) { line.remove(); line = null; } notice = false; };
  const showLine = (words: string): HTMLElement => {
    dropLine();
    const row = doc.createElement("div");
    row.className = "fileview-err " + PRINT_LINE_CLASS;
    row.id = PRINT_LINE_ID;
    row.setAttribute("role", "status");
    row.textContent = words;
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
  /** Collect the pictures and start the wait; the count still loading, 0 with the wait already over. */
  const beginWait = (): number => {
    dropSettle();
    const s = settlePictures(collectPictures(host.body, doc.baseURI, probe), settleMs);
    const n = s.pending();
    if (n === 0) { s.cancel(); return 0; }
    settle = s;
    void s.done.then((why) => {
      if (settle !== s) return;                 // cancelled, or replaced by a later wait
      settle = null;
      if (why === "cancelled" || closed || !host.card.isConnected) return;
      feed({ kind: "ready" });
    });
    return n;
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
        const row = showLine(armedWords(state.gated));
        for (const [words, withGated] of [[WITH_WORDS, true], [WITHOUT_WORDS, false]] as Array<[string, boolean]>) {
          const b = doc.createElement("button") as HTMLButtonElement;
          b.type = "button"; b.textContent = words;
          b.className = "fileview-btn fileview-err-act";
          b.title = withGated ? "Load the pictures from those hosts, then print" : "Print with their placeholders as they are";
          b.addEventListener("click", () => { feed({ kind: "choose", withGated }); });
          row.appendChild(b);
        }
        break;
      }
      case "disarm": dropSettle(); dropLine(); break;   // the body going out during the wait: no wait survives a disarm
      case "rest": dropLine(); break;
      case "activate": {
        // every host every placeholder names, through the gate's own load path: loadGatedHost is what the placeholder's
        // click runs (file-view.ts loadGate), and a placeholder naming two hosts takes two clicks, so both hosts are loaded
        const hosts = new Set<string>();
        for (const g of gates()) for (const h of (g.getAttribute("data-fv-hosts") || "").split(" ")) if (h) hosts.add(h);
        for (const h of hosts) loadGatedHost(h, doc);
        feed({ kind: "prepare", pending: beginWait() });
        return;
      }
      case "skip": feed({ kind: "prepare", pending: beginWait() }); return;
      case "wait": showLine(preparingWords(state.pending)); break;
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
  const onKey = (e: KeyboardEvent): void => {
    if (e.key === "Escape") {
      if (state.phase !== "armed") return;
      e.preventDefault(); e.stopPropagation();   // disarm alone: the viewer's own Escape, a bubble listener on the document, would close the card
      feed({ kind: "escape" });
      return;
    }
    if (!isPrintChord(e)) return;
    if (!doc.body.classList.contains("fileview-open") || !host.card.isConnected || host.typing()) return;
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
   *  pane takes it; the machine rests or disables, and a flow under way is disarmed. */
  const bodyIn = (present: boolean): void => { feed({ kind: "body", in: present }); };
  return { button: btn, bodyIn };
}
