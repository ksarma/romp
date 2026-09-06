// SPDX-License-Identifier: MIT
//
// Derived from track-changents, `obsidian/src/track-snapshot.js`, the inline-overlay decorations block (lines
// 442-790 at the pinned upstream commit 320cd25fda6fe218481fbf08fa5cfb4670404c96). The source is vendored
// pristine at vendor/track-changents/obsidian/src/track-snapshot.js as the citation; its LICENSE (MIT) sits
// beside it. Copyright the track-changents authors; the adaptation is romp's, under the same license.
//
// What this is: the CodeMirror 6 decorations for a tracked file's pending changes while the person edits it —
// an insertion's new text under a mark, a deletion's struck old text as an inline widget, a substitution as
// both — with the click handling (a mouse click accepts, a modifier-click rejects; a touch or pen press places
// the caret and decides nothing) and the hover cue that pairs a change's two halves. The record list the marks
// read is the vendored track-cm.js field, unchanged; the engine and the display planning are the vendored
// modules too. Everything the block needed from Obsidian is a parameter here (the five host callbacks) or gone.
// The chunk (editor-chunk.ts) is this module's only importer; the main bundles never see it (editor-lazy.test.ts
// pins both).
//
// Departures from the source, each deliberate:
//  1. FIX: the mouseover handler takes the EditorView as its second parameter. Upstream's `mouseover: (event) =>
//     {… view.dom.ownerDocument}` resolves `view` to an unrelated module-level import (its host-badges module),
//     so the hover cue queried the wrong document.
//  2. FIX: the Obsidian live-preview read (`editorLivePreviewField`) is the constant false. romp's editor is a
//     source editor, so the frontmatter skip that hid widgets under Obsidian's Properties UI never applies, and
//     `fmEnd` is always 0.
//  3. Click policy (romp's, in place of logic.diffClickAction): the primary button accepts; Alt on every
//     platform, Cmd on macOS and Ctrl elsewhere reject; a macOS Ctrl-click (the context-menu gesture) and any
//     other button are left to the browser. Upstream's Ctrl = "jump to the panel card" has no target in this
//     editor, and upstream let any button accept. The contextmenu suppression that served the Ctrl gesture goes
//     with it.
//  4. Class names are romp's: tc-diff-ins on inserted text, tc-diff-del on struck old text shown in place,
//     tc-diff-sub added to both halves of a substitution, tc-diff-del-block on the whole-paragraph form (with
//     tc-diff-del-line rows). Each element carries the author's session colour as `--fc-author` when the mount
//     supplies one, as the read view's fc-ins / fc-del marks do (styles.css, the fc block, which owns the CSS).
//  5. The field instances are closed over per extension set instead of module-level refs, so two editors on
//     one page cannot read each other's field.
//  6. Only a MOUSE press decides (romp's; upstream ran on desktop Obsidian and never asked). A finger or a pen
//     carries no modifier, so a tap could only accept, with reject unreachable and no undo chord to hand — and
//     a tap on tinted text is the ordinary gesture for placing the caret there. The browser fires a
//     compatibility mousedown after a tap, before CodeMirror's own touch guard can run (plugin handlers run
//     first), so both mousedown paths ask PointerTracker which pointer pressed and leave a touch or pen press to
//     the browser: the caret lands, the change stays pending, and the panel's cards accept or reject it.
//  7. A decision focuses the editor (romp's). Both mousedown paths preventDefault and stop CodeMirror's own
//     handler — the one that would have focused — and a prevented mousedown moves no focus natively, so an
//     editor that had lost focus to the toolbar or the panel stayed unfocused after an accept, and the undo the
//     guide promises went nowhere until the person clicked plain text.
//  8. FIX: the hover cue survives the editor's own DOM work (PointerTracker). Upstream's module-level lastHoverKey
//     is cleared only by mouseout, which cannot fire once the view's DOM is gone, so an editor destroyed under the
//     pointer (a save, a cancel) left the cache naming a change of a document that no longer showed one;
//     re-mounted, the first mouseover on that change short-circuited and lit nothing. The tracker's destroy
//     releases the cache. And CodeMirror rewrites a mark's class attribute whenever it re-syncs the mark's
//     attributes (Tile.sync → setAttrs, on the first measure after a mount and on every redraw of the line), which
//     drops the cue from the mark while the widget half, whose DOM is reused, keeps it; the tracker's
//     docViewUpdate re-lights the cached change after each redraw.
// Omitted as dead code (upstream no longer emits them): DelWidget's 'above' mode, the inlineDelLayout
// ViewPlugin, logic.layoutInlineRemovals, and the .tc-diff-del-inline vocabulary that only they used.
import { StateField, type Extension, type EditorState } from "@codemirror/state";
import { EditorView, Decoration, WidgetType, ViewPlugin, type DecorationSet, type DOMEventHandlers } from "@codemirror/view";
import { setSuggestions, setTrackMeta } from "../../vendor/track-changents/obsidian/src/track-cm.js";
import * as track from "../../vendor/track-changents/engine.js";
import * as logic from "../../vendor/track-changents/obsidian/src/track-logic.js";
import type { TrackRecord, TrackHunk } from "../../vendor/track-changents/engine.js";

export type { TrackRecord, TrackHunk };

/** The class vocabulary, exported so the sheet's owner and the tests read it from one place. */
export const CLS = {
  ins: "tc-diff-ins",          // a mark over inserted text (an insertion, or a substitution's new run)
  del: "tc-diff-del",          // a widget: struck old text in place (a deletion, or a substitution's old text)
  sub: "tc-diff-sub",          // added to both halves of a substitution
  block: "tc-diff-del-block",  // the whole-paragraph form of the struck text (a real block widget)
  line: "tc-diff-del-line",    // one row of that block
  hover: "tc-diff-hover",      // both halves of the change under the pointer
} as const;

/** Every clickable change element, both halves. */
export const CHANGE_SEL = `.${CLS.ins}[data-hk-from], .${CLS.del}[data-hk-from]`;

/** What the block needs from its host. editor-chunk.ts supplies all five. */
export interface TrackHost {
  /** A click on a comment mark: `'id:<commentId>'`, or a position when the mark has no id. */
  onOpenPanel(target: number | string, focusReply: boolean | undefined, view: EditorView): void;
  /** Accept (or, with `reject`, reject) the change whose display item starts at `from` in `view`'s document. */
  resolveInline(from: number, reject: boolean, view: EditorView): void;
  /** Whether any record resolves at `from` in `view`'s CURRENT document; false lets the click fall through. */
  hasResolvableAt(view: EditorView, from: number): boolean;
  /** The records changed: a keystroke mapped through them, or (`deliberate`) an accept or reject. */
  onOpsChanged(view: EditorView, deliberate: boolean): void;
  /** The view mounted; upstream loads its store here. */
  hydrateView(view: EditorView): void;
}

export interface TrackDecorationOpts {
  /** The author's session colour, or null for none; rides `--fc-author` on the change's elements. */
  authorColor?: (author: string) => string | null;
  /** Whether the modifier rule is macOS's (Cmd rejects, Ctrl is the context menu). Defaults to the platform. */
  mac?: boolean;
}

const IS_MAC = typeof navigator !== "undefined" && /Mac|iP(?:hone|ad|od)/.test(navigator.platform || "");

export type TrackClick = "accept" | "reject" | null;

/** The click policy (departure 3), pure: what a mousedown on a change means. `null` = not ours; let it through. */
export function trackClickAction(e: { button?: number; altKey?: boolean; metaKey?: boolean; ctrlKey?: boolean }, mac: boolean): TrackClick {
  if ((e.button ?? 0) !== 0) return null;                    // only the primary button decides anything
  if (e.altKey || (mac ? e.metaKey : e.ctrlKey)) return "reject";
  if (mac && e.ctrlKey) return null;                         // the macOS context-menu gesture stays the browser's
  return "accept";
}

/** The pointer policy (departure 6), pure: whether a press from `pointerType` (a pointerdown's, or nothing when
 *  the browser sent none or could not name the device) can decide a change. Only a mouse can; an unknown pointer
 *  counts as one, so a browser without pointer events keeps the mouse rule. */
export function pointerDecides(pointerType: string | null | undefined): boolean {
  return !pointerType || pointerType === "mouse";
}

/** What the pointer is doing in ONE editor — a ViewPlugin, so each editor has its own. `pressType` is the pointer
 *  type of the current press, from the pointerdown the browser fires before the mousedown that stands for it (a
 *  mouse's own, or the compatibility mousedown a tap produces). It listens on the editor root in the capture
 *  phase because CodeMirror's handler chain skips a press on a widget that ignores events (DelWidget does), and
 *  that press must count too. It also keeps the hover cue honest across the editor's own DOM work (departure 8):
 *  after each redraw it re-lights the cached change, and its destroy releases the cache while the DOM is still
 *  attached. */
export class PointerTracker {
  pressType: string | null = null;
  private readonly note = (e: PointerEvent) => { this.pressType = e.pointerType || null; };
  constructor(readonly view: EditorView) {
    view.dom.addEventListener("pointerdown", this.note, { capture: true, passive: true });
  }
  docViewUpdate(): void { relightHover(this.view); }
  destroy(): void {
    this.view.dom.removeEventListener("pointerdown", this.note, true);
    releaseHover(this.view);
  }
}
const pointerTracker = ViewPlugin.fromClass(PointerTracker);

/** Departure 6, for a mousedown in `view`: whether the press behind it came from a mouse. A view without the
 *  tracker (it crashed, or a test's stand-in) counts as one. */
function pressDecides(view: EditorView): boolean {
  return pointerDecides(view.plugin(pointerTracker)?.pressType);
}

/** The display items for a record list over `current`: the SAME planning the marks are built from, so a
 *  clicked mark's data-hk-from finds its item here. */
export function displayItems(ops: TrackRecord[], current: string): logic.DisplayItem[] {
  return logic.planDiffDisplay(track.toHunks(ops), track.baselineOf(current, ops), current);
}

/** The record ids the display item starting at `curFrom` stands for (a merged paragraph covers several; a plain
 *  item, one); [] when nothing starts there. Ported from upstream's idsAtPosition (track-snapshot.js:2322-2335):
 *  it asks the display layer (`idsOf`) rather than sweeping positions, which once swept in a zero-width
 *  deletion at the item's end and accepted it unreviewed. */
export function idsAtPosition(ops: TrackRecord[], current: string, curFrom: number): string[] {
  const h = displayItems(ops, current).find((x) => x.curFrom === curFrom);
  return h ? logic.idsOf(h).map(String) : [];
}

// The struck old text of a deletion or substitution: no longer in the document, so it must be a widget. Every
// side of a change is clickable ("click the version you want"). `mode`:
//   'block'   — the whole old paragraph struck above its all-new form (a dense whole-paragraph collapse)
//   'place'   — the struck old text in place, inline (a pure deletion)
//   'replace' — like 'place' but tinted as a substitution: the struck old text right before the new run
class DelWidget extends WidgetType {
  constructor(
    readonly text: string,
    readonly offset: number,
    readonly host: TrackHost,
    readonly mode: "block" | "place" | "replace",
    readonly keptTokens: string[],
    readonly color: string | null,
    readonly mac: boolean,
  ) { super(); }

  eq(other: WidgetType): boolean {
    return other instanceof DelWidget && other.text === this.text
      && other.offset === this.offset && other.mode === this.mode && other.color === this.color
      && other.keptTokens.join(",") === this.keptTokens.join(",");
  }

  toDOM(): HTMLElement {
    const wire = (el: HTMLElement) => {
      el.setAttribute("data-hk-from", String(this.offset));
      el.setAttribute("data-hk-side", "old");
      if (this.color) el.style.setProperty("--fc-author", this.color);
      el.addEventListener("mousedown", (e) => {
        // The view the widget lives in, from the DOM: the press's pointer and the position lookup are both ITS.
        const view = EditorView.findFromDOM(el);
        if (view && !pressDecides(view)) return;             // departure 6: a touch or pen press places the caret
        const action = trackClickAction(e, this.mac);
        if (!action) return;                                 // departure 3: not ours; the browser keeps it
        e.preventDefault();
        e.stopPropagation();
        if (view) this.host.resolveInline(this.offset, action === "reject", view);
        if (view && !view.hasFocus) view.focus();            // departure 7: the undo chord needs the editor focused
      });
      el.addEventListener("mouseenter", () => hoverPair(String(this.offset), el.ownerDocument));
      el.addEventListener("mouseleave", () => hoverPair(null, el.ownerDocument));
    };
    if (this.mode === "place" || this.mode === "replace") {
      const span = document.createElement("span");
      span.className = this.mode === "replace" ? `${CLS.del} ${CLS.sub}` : CLS.del;
      span.textContent = this.text;
      wire(span);
      return span;
    }
    const wrap = document.createElement("div");
    wrap.className = `${CLS.del} ${CLS.block}`;
    for (const ln of this.text.split("\n")) {
      const row = document.createElement("div");
      row.className = CLS.line;
      const segs = logic.segmentsByKeptTokens(ln, this.keptTokens);
      if (segs.length === 1 && !segs[0].kept) {
        row.textContent = ln.length ? ln : "​";         // zero-width so an empty removed line still has height
      } else {
        for (const seg of segs) {
          if (!seg.text) continue;
          const span = document.createElement("span");
          span.className = seg.kept ? "tc-diff-del-kept-embed" : "tc-diff-del-seg";
          span.textContent = seg.text;
          row.appendChild(span);
        }
      }
      wrap.appendChild(row);
    }
    wire(wrap);
    return wrap;
  }

  ignoreEvent(): boolean { return true; }
}

// Box a change AND the removal it replaces together (they share data-hk-from). `root` is the editor's own
// document. `lastHoverKey` short-circuits the common case: mouseover fires on every element boundary the pointer
// crosses, so without it, dragging across ordinary prose ran two document-wide queries per crossing. The cache is
// module-level (one pointer, one cue) and remembers which editor holds the cue, so departure 8 can release it when
// that editor is destroyed under the pointer and re-light it after that editor's redraws, and no other's.
let lastHoverKey: string | null = null;
let lastHoverRoot: Document | null = null;
let lastHoverEditor: Element | null = null;                  // the .cm-editor holding the cue: two editors on one page stay apart
const halvesOf = (key: string) => `.${CLS.ins}[data-hk-from="${key}"], .${CLS.del}[data-hk-from="${key}"]`;
function hoverPair(key: string | null, root: Document | null): void {
  const scope = root || document;
  if (key === lastHoverKey && scope === lastHoverRoot) return;
  const prev = lastHoverRoot || scope;                       // nothing cued before: only this document to sweep
  prev.querySelectorAll(`.${CLS.hover}`).forEach((e) => e.classList.remove(CLS.hover));
  if (scope !== prev) scope.querySelectorAll(`.${CLS.hover}`).forEach((e) => e.classList.remove(CLS.hover));
  lastHoverKey = key;
  lastHoverRoot = key == null ? null : scope;
  lastHoverEditor = null;
  if (key == null) return;
  const halves = scope.querySelectorAll(halvesOf(key));
  halves.forEach((e) => e.classList.add(CLS.hover));
  lastHoverEditor = halves[0]?.closest(".cm-editor") ?? null;
}

/** Whether the cached cue is `view`'s: same document, and the editor that holds it (when known) is this one. */
function hoverIsOf(view: Pick<EditorView, "dom">): boolean {
  return lastHoverKey != null && lastHoverRoot === view.dom.ownerDocument && (!lastHoverEditor || lastHoverEditor === view.dom);
}

/** Departure 8: drop the hover cache when `view` is destroyed, if the cache is its. A cue lit in another editor
 *  of the same document is left alone; a cache whose lit elements are already gone (this editor's, rebuilt) is
 *  cleared, since nothing else can clear it. */
export function releaseHover(view: Pick<EditorView, "dom">): void {
  if (hoverIsOf(view)) hoverPair(null, view.dom.ownerDocument);
}

/** Departure 8: after CodeMirror redrew `view`'s content, put the cue back on the cached change's halves in it.
 *  A redraw re-syncs a mark's attributes from the decoration (its class attribute included), so the mark half
 *  lost the cue while the pointer never left it; no event follows, so the redraw hook is the moment. Idempotent,
 *  one query scoped to this editor, and only while a change of its is cached. */
export function relightHover(view: Pick<EditorView, "dom">): void {
  if (!hoverIsOf(view)) return;
  view.dom.querySelectorAll(halvesOf(lastHoverKey!)).forEach((e) => e.classList.add(CLS.hover));
}

type TrackMeta = { trackingOn: boolean; comments: Array<{ id: string; kind?: string; anchor?: unknown }> };

// Build the decoration set for one editor from the live records + comments. The records are turned into hunks
// (track.toHunks) against the derived baseline (track.baselineOf), then grouped for display
// (logic.planDiffDisplay), the same planning idsAtPosition uses for a click.
function buildDecorations(
  state: EditorState, ops: TrackRecord[], meta: TrackMeta, host: TrackHost, opts: TrackDecorationOpts, mac: boolean,
): DecorationSet {
  const doc = state.doc;
  const comments = meta.comments || [];
  // Check FIRST, materialize after: a document copy per keystroke is only worth it when something shows.
  const enabled = logic.shouldShowTrackUI(!!meta.trackingOn, ops.length, comments.length);
  if (!enabled) return Decoration.none;
  const current = doc.toString();
  const hunks = displayItems(ops, current);
  // Departure 2: no live preview here, so the frontmatter skip is inert (fmEnd stays 0).
  const livePreview = false;
  const fmEnd = livePreview ? logic.frontmatterEnd(current) : 0;
  const insideFm = (from: number, to: number) => fmEnd > 0 && from < fmEnd && Math.max(to, from) <= fmEnd;
  const colorOf = (author: string) => (opts.authorColor ? opts.authorColor(author) : null);
  const ranges = [];
  for (const h of hunks) {
    if (insideFm(h.curFrom, h.curTo)) continue;
    const color = colorOf(h.author || "");
    if (h.oldText) {
      const at = Math.min(h.curFrom, doc.length);
      if (h.display === "paragraph") {
        // A dense whole-paragraph collapse: the new text IS the paragraph, so a real block widget at the
        // paragraph top sits directly above its all-new form.
        ranges.push(Decoration.widget({
          widget: new DelWidget(h.oldText, h.curFrom, host, "block", logic.keptEmbedTokens(h.oldText, current), color, mac),
          block: true,
          side: -1,
        }).range(doc.lineAt(at).from));
      } else {
        // Every other case (a substitution of any length, or a pure deletion) renders the struck OLD text inline
        // right before the new run, so it reads with the change and opens no vertical space.
        ranges.push(Decoration.widget({
          widget: new DelWidget(h.oldText, h.curFrom, host, h.newText ? "replace" : "place",
            logic.keptEmbedTokens(h.oldText, current), color, mac),
          side: -1,
        }).range(at));
      }
    }
    if (h.newText) {
      const attributes: Record<string, string> = { "data-hk-from": String(h.curFrom), "data-hk-side": "new" };
      if (color) attributes.style = `--fc-author:${color}`;
      ranges.push(Decoration.mark({
        class: h.oldText ? `${CLS.ins} ${CLS.sub}` : CLS.ins,
        attributes,
      }).range(h.curFrom, h.curTo));
    }
  }
  // Anchored comment highlights: a comment is tc-hl-anchor; a pending message (kind 'message') is tc-hl-pending
  // while its anchored text is unchanged. Nothing feeds comments through the mount option in Slice 5; the loop
  // stays so a later slice can, through setTrackMeta.
  for (const c of comments) {
    const isMsg = c.kind === "message";
    if (isMsg && !track.messageStillPending(current, c.anchor)) continue;
    const loc = track.locateAnchor(current, c.anchor);
    if (!loc) continue;
    if (insideFm(loc.from, loc.to)) continue;
    if (loc.from === loc.to) {
      // A zero-width anchor cannot carry a mark; a pending message tints its whole line instead.
      if (isMsg) {
        ranges.push(Decoration.line({
          class: "tc-hl-pending-line",
          attributes: { "data-hk-message": String(c.id), "data-hk-from": String(loc.from) },
        }).range(doc.lineAt(loc.from).from));
      }
      continue;
    }
    const attributes: Record<string, string> = isMsg
      ? { "data-hk-message": String(c.id), "data-hk-from": String(loc.from) }
      : { "data-hk-comment": String(c.id), "data-hk-from": String(loc.from) };
    ranges.push(Decoration.mark({ class: isMsg ? "tc-hl-pending" : "tc-hl-anchor", attributes }).range(loc.from, loc.to));
  }
  return Decoration.set(ranges, true);
}

/** The decorations, the click handlers and the hover cue over `field` (the vendored record-list field the caller
 *  created), as an extension set. Returns the meta field (fed by setTrackMeta), the decoration field, the
 *  change-notification listener, the DOM handlers, and the mount hook. */
export function trackDecorations(field: StateField<TrackRecord[]>, host: TrackHost, opts: TrackDecorationOpts = {}): Extension[] {
  const mac = opts.mac ?? IS_MAC;
  const metaField = StateField.define<TrackMeta>({
    create: () => ({ trackingOn: false, comments: [] }),
    update(value, tr) {
      for (const e of tr.effects) if (e.is(setTrackMeta)) return e.value as TrackMeta;
      return value;
    },
  });
  // Departure 5: the two fields are read through this closure, never through module-level refs.
  const build = (state: EditorState) => buildDecorations(state, state.field(field), state.field(metaField), host, opts, mac);

  const decoField = StateField.define<DecorationSet>({
    create: (state) => build(state),
    update(value, tr) {
      const pushed = tr.effects.some((e) => e.is(setSuggestions) || e.is(setTrackMeta));
      if (tr.docChanged || pushed) return build(tr.state);
      return value;
    },
    provide: (f) => EditorView.decorations.from(f),
  });

  // Whenever the records changed (a keystroke mapped through, or an accept/reject), tell the host. `deliberate` =
  // an explicit setSuggestions landed, as opposed to a doc change the records were folded through.
  const persist = EditorView.updateListener.of((update) => {
    const opsEffect = update.transactions.some((t) => t.effects.some((e) => e.is(setSuggestions)));
    if (!update.docChanged && !opsEffect) return;
    host.onOpsChanged(update.view, opsEffect);
  });

  const clicks = EditorView.domEventHandlers(changeHandlers(host, mac));

  // Tell the host the editor mounted, after the constructor's own update has finished (a dispatch inside an
  // update is refused), so a host that loads its records here can.
  const hydrateOnMount = ViewPlugin.fromClass(class {
    constructor(view: EditorView) { Promise.resolve().then(() => host.hydrateView(view)); }
  });

  return [metaField, decoField, persist, clicks, pointerTracker, hydrateOnMount];
}

// Duck-typed rather than `instanceof Element`: the handlers then run under node against a stand-in target
// (track-decorations.test.ts), and a text node — no closest() — still yields null.
const closest = (t: EventTarget | null, sel: string): Element | null =>
  t && typeof (t as Element).closest === "function" ? (t as Element).closest(sel) : null;

/** The DOM handlers over a tracked editor, as the plain object EditorView.domEventHandlers wraps: mousedown
 *  decides (departures 3, 6 and 7), click is swallowed after a decision, mouseover and mouseout drive the hover
 *  cue. Exported so a test can drive them with a stand-in view and target. */
export function changeHandlers(host: TrackHost, mac: boolean): DOMEventHandlers<unknown> {
  return {
    mousedown: (event, view) => {
      const add = closest(event.target, `.${CLS.ins}[data-hk-from]`);
      if (add) {
        if (!pressDecides(view)) return false;               // departure 6: a touch or pen press places the caret
        const action = trackClickAction(event, mac);
        if (!action) return false;                           // departure 3: not ours
        const from = Number(add.getAttribute("data-hk-from"));
        // A mark whose position no longer resolves (records and document drifted) must NOT swallow the click:
        // that reads as "cannot edit the file". Let CodeMirror place the cursor.
        if (!host.hasResolvableAt(view, from)) return false;
        event.preventDefault();
        host.resolveInline(from, action === "reject", view);
        if (!view.hasFocus) view.focus();                    // departure 7: the undo chord needs the editor focused
        return true;
      }
      const com = closest(event.target, "[data-hk-comment], [data-hk-message]");
      if (com) {
        // By id, never by offset: mid-edit the text shifts between the mark's build and the panel's render.
        const cid = com.getAttribute("data-hk-comment") || com.getAttribute("data-hk-message");
        host.onOpenPanel(cid ? "id:" + cid : Number(com.getAttribute("data-hk-from")), undefined, view);
        return false;
      }
      return false;
    },
    // While a change is pending, a mouse click means accept/reject (handled on mousedown), never anything else
    // the text under it might do; the click is swallowed so nothing above the editor acts on it either. A tap
    // decided nothing (departure 6), so its click is left alone too.
    click: (event, view) => {
      const hit = closest(event.target, CHANGE_SEL);
      if (hit) {
        if (!pressDecides(view)) return false;
        const from = Number(hit.getAttribute("data-hk-from"));
        if (!host.hasResolvableAt(view, from)) return false; // the same drift guard as mousedown
        event.preventDefault();
        event.stopPropagation();
        return true;
      }
      return false;
    },
    // Departure 1: `view` is the handler's own parameter, so the cue queries this editor's document.
    mouseover: (event, view) => {
      const hit = closest(event.target, CHANGE_SEL);
      hoverPair(hit ? hit.getAttribute("data-hk-from") : null, view.dom.ownerDocument);
    },
    mouseout: (event, view) => {
      if (!(event.relatedTarget instanceof Node) || !view.dom.contains(event.relatedTarget)) hoverPair(null, view.dom.ownerDocument);
    },
  };
}
