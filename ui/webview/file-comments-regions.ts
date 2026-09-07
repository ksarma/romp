// Region comments on images — the OVERLAY (plans/file-review.md: "Slice 3: region comments on images", and the
// "Images and PDFs" paragraph under "UX").
//
// A person reading a figure wants to point at a part of it — the axis label that is wrong, the bar that
// should not be there — and until now the only comment an image took was on the file as a whole. This
// module puts a drawing surface over every rendered image the viewer shows (the standalone image body,
// or each figure in rendered markdown): a `position: relative` wrapper around the <img>, an absolutely
// positioned overlay the size of the DRAWN image, and on it one rectangle per region comment, placed by
// CSS percentages from the stored fractions, so it is right at any viewer width by construction, and
// appended largest first, so a rectangle inside another stays above it and can be clicked (paint). A drag
// on the overlay becomes a region (region-geometry.ts does the arithmetic); the panel (file-comments.ts)
// decides what a drawn region means — a new comment's composer, or the re-placement of an existing one.
//
// A PDF page (Slice 4) is a picture too: the chunk draws each page into a canvas inside a wrapper that is
// already `position: relative` (div.fileview-pdf-page, data-page 1-based), so the layer takes that wrapper
// as its ANCHOR instead of wrapping the canvas — the canvas stays where the chunk put it, the overlay joins
// it — and the picture's natural size is the canvas's backing store (the page's own aspect). A region on a
// page is a fraction of the page as drawn, which is why it is width-independent there too (the plan's
// "Slice 4: PDFs rendered in the viewer, with page and region comments").
//
// The overlay draws only while the panel is OPEN and the primary pointer is fine (`active`): the
// rectangles are the file's marks and show whenever the highlights do (the probe's status paints both),
// but a closed panel must not turn every picture into a drawing surface — the cursor, the native image
// drag and the context menu stay the browser's. Desktop only (decision 26): with a coarse primary
// pointer (`(pointer: coarse)`) the overlay never takes pointer events, so the picture behaves as before
// and the whole-file comment stands in; the rectangles stay clickable in both cases, since they open cards.
//
// While the overlay is armed it stands over everything the picture used to offer a click: the rectangles,
// and the picture itself when an embed-line comment's frame made it a control. A press on the PICTURE is
// captured (so a drag that leaves it stays alive), and a captured pointer's click is dispatched to the
// CAPTURING element (Pointer Events, event dispatch) — the overlay, which carries no action, so the delegate
// root would drop it: a press there that does not move is handed on by the layer, which clicks the control
// the press began on (handOn) and swallows the browser's own click after it. A press on a RECTANGLE is not
// captured until a drag's band appears, so the browser's own click lands on the rectangle and opens its card
// (arm); handOn steps in only where that click cannot reach it (a slip, a node rebuilt mid-press).
//
// The wrapper stands in the AUTHOR's flow where the picture stood, so it takes over the picture's own place there
// (carriedLayout): a percentage width or max-width the author wrote resolves against the paragraph, not against a
// wrapper that hugs the picture (a width="100%" plot collapsed to its natural width); a float (align="right") applies
// to the wrapper, so the prose flows beside it as before; an inline display: block with auto margins keeps the figure
// centered; a vertical-align keeps a badge on its line. The picture's own inline style is snapshotted and put back on
// dispose, so opening and closing the panel leaves the page as the browser laid it out (the 2026-09-06 review).
//
// Nothing here adds a TEXT node under the image: the rendered-markdown mapper aligns each block's text
// against the source, and a chip's label as a text node would misalign the paragraph holding the figure.
// The author chip is drawn from `data-label` by the sheet (`content: attr(data-label)`), the way the
// deletion mark's struck text is (.fc-del::before).
//
// Every control the overlay makes carries data-act="fcopen" and data-id, and is handed back to the panel
// so it can register them as its own (owns): the delegate root is the viewer's body row, which also holds
// the file's markup (ui/CLAUDE.md, click-safe; file-comments.ts, provenance).
import {
  drawnBox, overlayOffsets, regionFromPoints, regionStyle, dragIsClick, cropRect, cropSize, regionDesc,
  type Region, type Box, type Point, type Size, type Staleness,
} from "./region-geometry";

/** One rectangle to paint: the comment it opens, where, whose, and whether the image changed under it. */
export type RegionMark = {
  id: string;
  region: Region;
  /** the author chip's text: "you", the session's name, or the sidecar's own label */
  label: string;
  state: Staleness;
  /** `--fc-author` / `--fc-author-fg` from the session colour map; absent for the sheet's fallback */
  style?: Record<string, string>;
};
/** What a layer sits on: the viewer's <img> (a standalone image, a figure in rendered markdown), or a PDF page's
 *  canvas as the chunk drew it (Slice 4). */
export type Pictured = HTMLImageElement | HTMLCanvasElement;
export type LayerHooks = {
  /** a completed drag: the region in fractions of the natural size */
  onDraw: (img: Pictured, region: Region) => void;
  /** a press that did not move (and did not start on a rectangle): the picture click the viewer already had */
  onClick: (img: Pictured) => void;
  /** every press on the overlay, before anything else: the overlay cancels the compat mousedown, so a listener
   *  waiting on mousedown (the panel's float hides on one) never hears of it otherwise */
  onPress?: () => void;
};

/** The thumbnail's bounds in CSS pixels; the crop keeps its own aspect inside them. */
export const THUMB_MAX: Size = { width: 240, height: 140 };

/** Whether the primary pointer is a finger (a phone or tablet): region drawing is off there (plans/file-review.md,
 *  Slice 3: desktop only in v1; decision 26). */
export function isCoarsePointer(): boolean {
  try { return window.matchMedia("(pointer: coarse)").matches; } catch { return false; }
}

/** A PDF page's canvas, as against an <img> (by tag, so a DOM stand-in without the constructors can answer). */
export function isCanvas(el: Element | null | undefined): el is HTMLCanvasElement {
  return !!el && typeof el.tagName === "string" && el.tagName.toUpperCase() === "CANVAS";
}
/** The picture's natural size: an <img>'s intrinsic pixels; a canvas's backing store (0×0 for a page the chunk
 *  has evicted, which then reads as unknown: no crop, and the overlay falls back to the element's own box). */
export function naturalSizeOf(el: Pictured): Size {
  if (isCanvas(el)) return { width: el.width || 0, height: el.height || 0 };
  return { width: el.naturalWidth || 0, height: el.naturalHeight || 0 };
}
/** The word for what changed under a stale region: the image's bytes, or the PDF's. */
const nounFor = (el: Pictured): string => (isCanvas(el) ? "PDF" : "image");

/** One `style` attribute from position percentages and custom properties — no CSSOM, as anchor-map's
 *  applyStyles: a name that is not a property name, or a value that could end the declaration, is skipped. */
function styleAttr(decls: Record<string, string>): string {
  const out: string[] = [];
  for (const k of Object.keys(decls)) {
    const v = decls[k];
    if (!/^-{0,2}[A-Za-z_][\w-]*$/.test(k) || typeof v !== "string" || /[;{}\r\n]/.test(v)) continue;
    out.push(k + ": " + v);
  }
  return out.join("; ") + (out.length ? ";" : "");
}
/** A CSS percentage (`50%`, ` 100% `), as the HTML `width` attribute's dimension parse and the CSSOM both yield it;
 *  null for anything else (a pixel count, a keyword, an empty value). */
export function pctOf(v: string | null | undefined): string | null {
  const m = typeof v === "string" ? /^\s*(\d+(?:\.\d+)?|\.\d+)%\s*$/.exec(v) : null;
  return m ? m[1] + "%" : null;
}
/** What the picture's layout reads as before it is wrapped: the `width` attribute, its inline style, its computed style. */
export type ImgLayout = {
  attrWidth: string | null;
  inline: { width?: string; maxWidth?: string; display?: string; float?: string; verticalAlign?: string; marginLeft?: string; marginRight?: string };
  computed: { float?: string; verticalAlign?: string; marginLeft?: string; marginRight?: string };
};
/** The declarations the wrapper takes over from the picture, and the ones the picture gives up in return. */
export type CarriedLayout = { wrap: Record<string, string>; img: Record<string, string> };

/** The picture's own place in the author's flow, carried onto the wrapper that now stands there (the module header).
 *  A percentage width or max-width resolves against the containing block, which the wrap changes from the paragraph
 *  to the wrapper: the wrapper takes the percentage and the picture fills it (100%), else the two would compound. A
 *  float goes to the wrapper (the picture's own is cleared: a float inside a wrapper that hugs it floats nothing). An
 *  inline `display: block` makes the wrapper a block too, sized to its content so auto margins can center it; then,
 *  and whenever a percentage width is carried, the picture's horizontal margins (an author's `margin: 0 auto`, an
 *  hspace) go to the wrapper too. A LENGTH (an hspace's pixels) leaves the picture, since inside a wrapper the picture
 *  fills it would push the picture out; an `auto` margin stays on the picture as well, since auto never overflows (it
 *  resolves to the free space, or to zero) and the picture does not always fill the wrapper: a `width="100%"` figure
 *  capped by a pixel `max-width` fills the paragraph-wide wrapper only up to the cap, and with its auto margins moved
 *  off it sat at the wrapper's left edge while the wrapper's own resolved to zero — a centered plot jumped left the
 *  moment the panel opened, and a `margin-left: auto` one lost its right edge (the 2026-09-06 review). Auto on both
 *  centers the wrapper in the paragraph and the picture in the wrapper, whichever is the narrower. The wrapper is not
 *  narrowed to the cap instead, because a percentage VERTICAL margin on the picture resolves against its containing
 *  block's width, and that block must stay as wide as the paragraph was. Vertical margins stay on the picture (a block
 *  wrapper lets them collapse through, an inline one contains them, as the paragraph did). A vertical-align other than
 *  baseline goes to an inline wrapper, so the wrapper sits on the line as the picture did. The specified inline value
 *  is read first (it may be `auto`, or a percentage), the computed one after it (an `align` attribute's float, an
 *  hspace's pixels). Nothing carried: both records are empty. */
export function carriedLayout(l: ImgLayout): CarriedLayout {
  const wrap: Record<string, string> = {}, img: Record<string, string> = {};
  const inl = l.inline, cs = l.computed;
  const w = inl.width ? pctOf(inl.width) : pctOf(l.attrWidth);
  if (w !== null) { wrap.width = w; img.width = "100%"; }
  const mw = pctOf(inl.maxWidth);
  if (mw !== null) { wrap["max-width"] = mw; img["max-width"] = "100%"; }
  const f = cs.float || inl.float || "";
  const floated = f !== "" && f !== "none";
  if (floated) { wrap.float = f; img.float = "none"; }
  const block = inl.display === "block";
  if (block) { wrap.display = "block"; if (w === null) wrap.width = "fit-content"; }
  if (block || w !== null) {
    for (const side of ["left", "right"] as const) {
      const k = side === "left" ? "marginLeft" : "marginRight";
      const v = inl[k] || cs[k] || "";
      if (v && v !== "0px" && v !== "0") { wrap["margin-" + side] = v; if (v !== "auto") img["margin-" + side] = "0"; }
    }
  }
  const va = inl.verticalAlign || cs.verticalAlign || "";
  if (va && va !== "baseline" && !block && !floated) wrap["vertical-align"] = va;
  return { wrap, img };
}
/** The picture's layout as the DOM reports it: the attribute, the inline style (a CSSOM read; a stand-in with no
 *  `style` object reads as unstyled), and the computed style where the document has one to read. */
function readImgLayout(img: Pictured): ImgLayout {
  const st = (img.style || {}) as unknown as Partial<Record<string, unknown>>;
  const s = (k: string): string => { const v = st[k]; return typeof v === "string" ? v : ""; };
  const w = typeof window !== "undefined" ? window : null;
  let cs: Partial<Record<string, unknown>> = {};
  if (w && typeof w.getComputedStyle === "function") { try { cs = (w.getComputedStyle(img) || {}) as unknown as Partial<Record<string, unknown>>; } catch { cs = {}; } }
  const c = (k: string): string => { const v = cs[k]; return typeof v === "string" ? v : ""; };
  return {
    attrWidth: img.getAttribute("width"),
    inline: { width: s("width"), maxWidth: s("maxWidth"), display: s("display"), float: s("cssFloat") || s("float"), verticalAlign: s("verticalAlign"), marginLeft: s("marginLeft"), marginRight: s("marginRight") },
    computed: { float: c("cssFloat") || c("float"), verticalAlign: c("verticalAlign"), marginLeft: c("marginLeft"), marginRight: c("marginRight") },
  };
}
/** An element's `style` attribute with declarations appended: the later declaration of a property wins, so the
 *  picture's own `width: 50%` yields to the `width: 100%` written after it, and the rest of what the author wrote
 *  stands. Text, not CSSOM, as styleAttr. */
function appendStyle(prior: string | null, add: string): string {
  const p = prior ? prior.trim().replace(/;+\s*$/, "") : "";
  return p ? p + "; " + add : add;
}
const mk = (doc: Document, tag: string, cls: string): HTMLElement => { const e = doc.createElement(tag); e.className = cls; return e; };
/** An element's client rect as a plain box. A DOMRect's fields are prototype getters, so a spread of one is an empty
 *  object — and the geometry returns `{ ...rect }` where the box is the element (a picture drawn `fill`, a natural size
 *  not known yet): passed the DOMRect itself, that came back as a box of undefineds and a NaN style on the overlay. */
const boxOf = (el: Element): Box => { const r = el.getBoundingClientRect(); return { left: r.left, top: r.top, width: r.width, height: r.height }; };

export class RegionLayer {
  /** the positioned box the overlay sits in: the span this layer wrapped around an <img>, or the anchor it was given */
  readonly wrap: HTMLElement;
  readonly overlay: HTMLElement;
  /** whether `wrap` is this layer's own span (unwrapped on dispose) or a caller's anchor (left standing) */
  private readonly owned: boolean;
  /** the pointer held down on the overlay: its id, where it began, the rectangle it began on (with the comment id that
   *  rectangle carried, since a paint pass may rebuild it before the release), and whether the overlay holds its
   *  capture — not from a press on a rectangle, until a drag's band appears (arm) */
  private press: { id: number; start: Point; rect: HTMLElement | null; rectId: string | undefined; captured: boolean } | null = null;
  private band: HTMLElement | null = null;
  /** the press did its work here — a region drawn, or the click handed on to the control under the overlay — so
   *  the click the browser synthesizes after it is not an activation of its own and is swallowed (arm) */
  private drew = false;
  /** whether a drag draws here: the panel is open and the pointer is fine (setActive) */
  active = false;
  private readonly onResize = () => this.place();
  private readonly onLoad = () => this.place();
  private sizer: ResizeObserver | null = null;
  /** the picture's `style` attribute before the layer touched it (null: none), put back on dispose */
  private readonly imgStyle: string | null;
  /** whether the picture's style attribute was written (carriedLayout gave it something to give up) */
  private readonly carried: boolean;

  /** `anchor`: an already-positioned element holding the picture (a PDF page's wrapper), used as is; without one
   *  the layer wraps the <img> in a span of its own. */
  constructor(readonly img: Pictured, readonly hooks: LayerHooks, anchor?: HTMLElement | null) {
    const doc = img.ownerDocument;
    this.overlay = mk(doc, "div", "fc-overlay fc-overlay-off");
    this.owned = !anchor;
    // an <img> the layer wraps: the picture's place in the flow, read where the author put it, before the wrapper
    // stands there (carriedLayout). An anchor is the caller's own positioned box (a PDF page's shell) and carries nothing
    const carry: CarriedLayout = anchor ? { wrap: {}, img: {} } : carriedLayout(readImgLayout(img));
    this.imgStyle = img.getAttribute("style");
    if (anchor) {
      this.wrap = anchor;
    } else {
      this.wrap = mk(doc, "span", "fc-imgwrap");
      const parent = img.parentNode;
      if (parent) parent.insertBefore(this.wrap, img);
      this.wrap.appendChild(img);
    }
    this.wrap.appendChild(this.overlay);
    const wrapStyle = styleAttr(carry.wrap), imgStyle = styleAttr(carry.img);
    if (wrapStyle) this.wrap.setAttribute("style", wrapStyle);
    this.carried = imgStyle !== "";
    if (this.carried) img.setAttribute("style", appendStyle(this.imgStyle, imgStyle));
    img.addEventListener("load", this.onLoad);
    // the exact event for "the drawn size changed": the aside opening narrows the body with no window resize;
    // the window's resize stands in where the observer is missing. The wrapper is observed too, for the picture
    // whose wrapper outgrows it (a carried percentage width with the picture capped by a pixel max-width, a
    // percentage margin): there the picture moves inside the wrapper when the column changes while its own size
    // does not, and the pixel offsets place() measures against the wrapper go stale. A picture the wrapper hugs
    // needs neither: the sheet's inset: 0 follows it, and a move fires no observer at all
    // (file-comments-regions-sizer.test.ts, and the -browser leg beside it).
    if (typeof ResizeObserver !== "undefined") { this.sizer = new ResizeObserver(() => this.place()); this.sizer.observe(img); this.sizer.observe(this.wrap); }
    else window.addEventListener("resize", this.onResize);
    this.arm();
    this.place();
  }

  /** Arm or disarm the drag. Off, the overlay takes no pointer events (the sheet's .fc-overlay-off), so the
   *  picture is the browser's again; the rectangles keep their own pointer events and open their cards. */
  setActive(on: boolean): void {
    this.active = on;
    this.overlay.classList.toggle("fc-overlay-off", !on);
    if (on) this.overlay.setAttribute("aria-label", "Drag to comment on a region of the " + (isCanvas(this.img) ? "page" : "image"));
    else this.overlay.removeAttribute("aria-label");
  }

  private natural(): Size { return naturalSizeOf(this.img); }
  /** How the picture is fitted into its element: the COMPUTED `object-fit`, read rather than assumed. The media
   *  body's `.fileview-img` has `contain` (a letterbox when the aspects differ); a figure in rendered markdown has
   *  no rule, so CSS's initial `fill` stretches it over a `width`/`height` pair the author wrote (the sanitizer keeps
   *  both), and a letterbox computed for THAT figure put the overlay over the middle of the element while the picture
   *  filled all of it. A PDF page's canvas has no rule either: `fill`, the element itself. A document with no computed
   *  style to read (a stand-in) reads as `fill`, the initial value. */
  private fit(): string {
    const w = typeof window !== "undefined" ? window : null;
    if (!w || typeof w.getComputedStyle !== "function") return "fill";
    const v = w.getComputedStyle(this.img).objectFit;
    return typeof v === "string" && v ? v : "fill";
  }
  /** The drawn image's box in client coordinates: the element's rect, adjusted for how its `object-fit` draws the
   *  picture in it (drawnBox: the letterbox under `contain`, the element itself under `fill`). */
  box(): Box { return drawnBox(boxOf(this.img), this.natural(), this.fit()); }

  /** Size the overlay to the drawn image. The wrapper hugs the <img>, so the sheet's `inset: 0` is right
   *  whenever the picture fills its element (`fill`, or `contain` at the picture's own aspect); a picture drawn
   *  smaller than its element (the `contain` letterbox), or than its wrapper (a wrapper that outgrows it), gets pixel
   *  offsets, re-measured on the image's load and on every resize of the picture or the wrapper. A wrapper with no
   *  size yet (not laid out) claims nothing. */
  place(): void {
    const w = boxOf(this.wrap);
    const off = w.width > 0 && w.height > 0 ? overlayOffsets(w, this.box()) : null;
    if (!off) { this.overlay.removeAttribute("style"); return; }
    this.overlay.setAttribute("style", styleAttr({ left: off.left + "px", top: off.top + "px", width: off.width + "px", height: off.height + "px" }));
  }

  /** Pointer events on the overlay (while active): a press that moves past the click threshold draws
   *  a rubber band and, on release, becomes a region; a press that does not move is a click on what the
   *  overlay covers — the rectangle it began on, a picture that is itself a control, or the picture click the
   *  viewer already had (onClick: the embed-line Comment offer) — handed on by handOn wherever the browser's own
   *  click cannot land there. Pointer capture keeps a drag that leaves the picture alive; the region is clamped
   *  to the image.
   *
   *  A press that begins on a RECTANGLE is not captured at the press: the browser fires the click it
   *  synthesizes at the pointer's capture target, so capturing here sent that click to the overlay, where the
   *  delegate root finds no data-act, and the card never opened while the panel was open (2026-09-06; with the
   *  panel closed the handler returns before capturing, so the same click worked). Left alone, the click
   *  targets the rectangle, whose data-act="fcopen" the row's delegate routes; that click is the activation, and
   *  handOn adds none unless it cannot reach the rectangle. Capture then waits for the
   *  drag, if one comes: it is taken when the band appears, so a drag begun on a rectangle still survives
   *  leaving the picture. The press's default is still cancelled (no selection starts behind the overlay),
   *  and with it the focus the mousedown would have given the rectangle — so the rectangle is focused here,
   *  without a scroll: a mouse-initiated focus never scrolls, but a scripted focus() brings the element into
   *  view, and a rectangle straddling the body's edge (a PDF page or a tall image is taller than .fileview-body)
   *  jumped the content under the held pointer on every first press (2026-09-06). preventScroll keeps the
   *  emulation faithful, as the panel's refocusBody already does. */
  private arm(): void {
    const o = this.overlay;
    const capture = (ev: PointerEvent) => {
      try { o.setPointerCapture(ev.pointerId); } catch { /* a pointer the browser will not capture: leaving the picture ends the drag */ }
    };
    const end = (ev: PointerEvent, cancelled: boolean) => {
      const p = this.press;
      if (!p || ev.pointerId !== p.id) return;
      this.press = null;
      try { o.releasePointerCapture(ev.pointerId); } catch { /* not captured */ }
      if (this.band) { this.band.remove(); this.band = null; }
      if (cancelled) return;
      const cur = { x: ev.clientX, y: ev.clientY };
      if (dragIsClick(p.start, cur)) { this.handOn(p, ev.target as Element | null); return; }
      const r = regionFromPoints(this.box(), p.start, cur);
      if (!r) return;
      this.drew = true;
      this.hooks.onDraw(this.img, r);
    };
    o.addEventListener("pointerdown", (ev: PointerEvent) => {
      if (!this.active || (ev.button || 0) !== 0) return;
      if (this.hooks.onPress) this.hooks.onPress();
      this.drew = false;
      const t = ev.target as Element | null;
      const rect = t && typeof t.closest === "function" ? (t.closest(".fc-region") as HTMLElement | null) : null;
      this.press = { id: ev.pointerId, start: { x: ev.clientX, y: ev.clientY }, rect, rectId: rect ? rect.dataset.id : undefined, captured: !rect };
      if (!rect) capture(ev);
      ev.preventDefault();                               // no native image drag, no selection behind the overlay
      if (rect && typeof rect.focus === "function") rect.focus({ preventScroll: true });   // the focus the cancelled mousedown would have given it, and not the scroll it would not
    });
    o.addEventListener("pointermove", (ev: PointerEvent) => {
      const p = this.press;
      if (!p || ev.pointerId !== p.id) return;
      // an uncaptured press whose release landed elsewhere (the pointer left the picture in one move): the button
      // is up by the time the pointer is back, and the press is over
      if (!p.captured && ev.buttons === 0) { end(ev, true); return; }
      const cur = { x: ev.clientX, y: ev.clientY };
      if (!this.band && dragIsClick(p.start, cur)) return;
      const r = regionFromPoints(this.box(), p.start, cur);
      if (!r) return;
      if (!this.band) {
        this.band = mk(o.ownerDocument, "div", "fc-region fc-region-pending fc-draw"); o.appendChild(this.band);
        if (!p.captured) { capture(ev); p.captured = true; }   // the drag is on: keep it alive past the picture's edge
      }
      this.band.setAttribute("style", styleAttr(regionStyle(r)));
    });
    o.addEventListener("pointerup", (ev: PointerEvent) => end(ev, false));
    o.addEventListener("pointercancel", (ev: PointerEvent) => end(ev, true));
    // the click a browser synthesizes after the drag, or after a click the layer handed on, must not reach the
    // delegate root as an activation
    o.addEventListener("click", (ev: Event) => { if (this.drew) { this.drew = false; ev.stopPropagation(); ev.preventDefault(); } });
  }

  /** A press that did not move is a click on what the overlay covers, and the layer hands it on wherever the browser's
   *  own click cannot land there. Began on a RECTANGLE: the press was not captured (arm), so the browser's click goes to
   *  the rectangle when the release is on it too, and that click is the activation — nothing is added here. Released
   *  off it (a slip within the click threshold), or with the node a paint pass rebuilt mid-press (its mark left and came
   *  back), the browser's click lands on the nearest common ancestor instead, so the rectangle is clicked here — the one
   *  now carrying the same comment id (click-safe across re-renders, ui/CLAUDE.md); a pending region carries no id and
   *  opens nothing. Began on the PICTURE: the pointer was captured, so the browser's click goes to the overlay (the
   *  capturing element), where the delegate root finds no action. A picture that is itself a control (the frame an
   *  embed-line comment wears, data-act="fcopen") is clicked, so the delegate root opens its card and the panel's own
   *  picture listener hears the click it heard before the overlay stood there — the Comment offer follows as before. A
   *  plain picture's click reaches no control, and goes to the panel through onClick. A click dispatched here IS the
   *  activation, so the browser's own is swallowed after it (drew). */
  private handOn(p: { rect: HTMLElement | null; rectId: string | undefined }, released: Element | null): void {
    if (p.rect) {
      if (p.rectId === undefined) return;
      const o = this.overlay;
      const now = o.contains(p.rect) ? p.rect
        : (Array.from(o.querySelectorAll(".fc-region")) as HTMLElement[]).find((r) => r.dataset.id === p.rectId) || null;
      if (!now) return;                                  // gone with its comment mid-press: nothing left to open
      if (now === p.rect && released && now.contains(released)) return;   // the browser's own click lands on it
      this.activate(now);
      return;
    }
    if (this.img.dataset.act) { this.activate(this.img); return; }
    this.hooks.onClick(this.img);
  }
  /** Click a control the overlay covered, the way Enter on a focused highlight does (the panel's KEY_ACTS path):
   *  a synthetic click bubbles to the delegate root with the control as its target. An element with no click()
   *  (a DOM stand-in) cannot be activated from here, and then the click the browser dispatches is left alone. */
  private activate(el: HTMLElement): void {
    if (typeof el.click !== "function") return;
    el.click();
    this.drew = true;
  }

  /** Bring the rectangles up to date: one per mark (a control: data-act="fcopen", data-id, a Tab stop), the
   *  composer's pending region when there is one, and the re-place cue on the overlay. Returns the controls
   *  so the panel can register them as its own. Called on every paint pass.
   *
   *  Keyed by the comment: a rectangle already up for a mark is UPDATED IN PLACE — its place, its state, its chip
   *  — never removed and made again. With a PDF this pass runs on every page draw, redraw and width change (the
   *  chunk's onPage, through the seam's onRendered), and a press on a rectangle is deliberately not captured (arm),
   *  so a rectangle remade under a held pointer took the click with it: mousedown and mouseup landed on different
   *  nodes, and no click reached a data-act — a card that took several clicks to open while the pages next to it
   *  were drawing (ui/CLAUDE.md, click-safe; 2026-09-06). A node that stays also keeps its keyboard focus. A move
   *  counts as a removal to the browser's click tracking too, so a rectangle that is up is not re-inserted while its
   *  place in the order below holds: a new mark's rectangle goes in right after the previous mark's, which keeps that
   *  order for every rectangle painted here without moving one. A rectangle whose mark is gone leaves; the pending
   *  region is one node, updated the same way; anything else on the overlay but the drag band is removed, so nothing
   *  is ever stacked.
   *
   *  The rectangles stand LARGEST FIRST (stackOrder). They are absolutely positioned siblings with no z-index,
   *  so the one later in the overlay paints over, and is hit before, the ones before it. In card
   *  order, a rectangle drawn later around a whole plot covered the detail rectangle drawn earlier inside it, and
   *  a click at the detail's centre opened the plot's card, with the panel closed (the browser's own hit test)
   *  and open alike — the 2026-09-06 review. Largest first, a
   *  rectangle inside another is always above it, so every rectangle can be reached from the mouse wherever no
   *  smaller one covers it; the Tab order follows, outer to inner. Two identical rectangles keep card order, the
   *  later above; the one under it is still a Tab stop and has its card in the panel. The pending region comes
   *  last, above them all, as before. A rectangle that is up but out of its place in that order (a re-place grew
   *  or shrank it against the others) is moved there — the one re-insertion, and handOn still opens it from a press.
   *
   *  A paint pass can land mid-drag (a peer's comment arriving, the colour map answering): the rubber band of the
   *  drag in progress is kept, and left above everything the pass drew, so the person keeps seeing what they
   *  are drawing until the release. */
  paint(marks: RegionMark[], pending: Region | null, replacing: boolean): HTMLElement[] {
    const o = this.overlay; const doc = o.ownerDocument;
    const hasClass = (n: Node, cls: string): boolean => {
      const cl = (n as HTMLElement).classList;
      return !!cl && typeof cl.contains === "function" && cl.contains(cls);
    };
    const isRegion = (n: Node): n is HTMLElement => hasClass(n, "fc-region");
    // what is up: the rectangles by the comment they open, and the pending region; a stray, or a second node for
    // the same comment, is removed here
    const have = new Map<string, HTMLElement>();
    let pend: HTMLElement | null = null;
    for (const n of Array.from(o.childNodes)) {
      if (n === this.band) continue;
      if (isRegion(n)) {
        if (n.classList.contains("fc-region-pending")) { if (!pend) { pend = n; continue; } }
        else { const id = n.dataset.id; if (id && !have.has(id)) { have.set(id, n); continue; } }
      }
      o.removeChild(n);
    }
    const out: HTMLElement[] = [];
    const noun = nounFor(this.img);
    let last: HTMLElement | null = null;                 // the previous mark's rectangle: a new one goes in right after it
    for (const m of stackOrder(marks)) {
      let r = have.get(m.id);
      let chip: HTMLElement | null = null;
      const kids = o.childNodes;
      const at: number = last ? Array.prototype.indexOf.call(kids, last) + 1 : 0;
      const ref: Node | null = (kids[at] as Node | undefined) || null;
      if (r) {
        have.delete(m.id);
        if (r !== ref) o.insertBefore(r, ref);          // up, but out of its place in the stacking order: moved there
        chip = (Array.from(r.childNodes) as HTMLElement[]).find((n) => hasClass(n, "fc-region-chip")) || null;
      } else {
        r = mk(doc, "div", "fc-region");
        r.dataset.act = "fcopen"; r.dataset.id = m.id;
        r.tabIndex = 0; r.setAttribute("role", "button");
        chip = mk(doc, "span", "fc-region-chip"); r.appendChild(chip);
        o.insertBefore(r, ref);
      }
      r.className = "fc-region" + (m.state === "stale" ? " fc-stale" : m.state === "unknown" ? " fc-unknown" : "");
      r.setAttribute("style", styleAttr({ ...regionStyle(m.region), ...(m.style || {}) }));
      r.title = "Open the comment on this region" + (m.state === "stale" ? " (the " + noun + " changed after it was drawn)" : m.state === "unknown" ? " (whether the " + noun + " changed could not be checked)" : "");
      if (!chip) { chip = mk(doc, "span", "fc-region-chip"); r.appendChild(chip); }   // a rectangle whose chip went (nothing here removes one)
      chip.dataset.label = m.label;                      // drawn by the sheet: no text node under the picture
      out.push(r); last = r;
    }
    for (const gone of have.values()) o.removeChild(gone);   // resolved, or moved to another picture
    if (pending) {
      const p = pend || mk(doc, "div", "fc-region fc-region-pending");
      p.setAttribute("style", styleAttr(regionStyle(pending)));
      if (!pend) o.appendChild(p);
    } else if (pend) o.removeChild(pend);
    const kids = o.childNodes;
    if (this.band && kids[kids.length - 1] !== this.band) o.appendChild(this.band);   // a drag in progress: its band stays on top
    o.classList.toggle("fc-replacing", replacing);
    return out;
  }

  /** Take the overlay down and put the picture back where it was, with the inline style it had; an anchor the layer
   *  was given keeps its picture. */
  dispose(): void {
    this.img.removeEventListener("load", this.onLoad);
    if (this.sizer) { this.sizer.disconnect(); this.sizer = null; }
    else window.removeEventListener("resize", this.onResize);
    if (!this.owned) { this.overlay.remove(); return; }
    const parent = this.wrap.parentNode;
    if (parent) { parent.insertBefore(this.img, this.wrap); parent.removeChild(this.wrap); }
    if (this.carried) { if (this.imgStyle === null) this.img.removeAttribute("style"); else this.img.setAttribute("style", this.imgStyle); }
  }
}

/** The order the rectangles are appended in, which is their stacking order: by area, largest first, so a
 *  rectangle inside another is above it; equal areas keep the given (card) order. The index breaks ties, so the
 *  result does not lean on the engine's sort being stable. */
export function stackOrder(marks: RegionMark[]): RegionMark[] {
  const area = (r: Region): number => r.w * r.h;
  return marks.map((m, i) => ({ m, i })).sort((a, b) => area(b.m.region) - area(a.m.region) || a.i - b.i).map((x) => x.m);
}

/** The card's thumbnail: the region cropped from the picture onto a canvas, drawn from the <img> itself
 *  (same origin through /file or a blob URL; a cross-origin picture taints the canvas, which only matters
 *  for reading pixels back, and nothing does) or from a PDF page's canvas. Null when the picture has not
 *  loaded, has no natural size (an SVG without one; a page the chunk evicted), or cannot be drawn — the card
 *  then stands without one, and the caller may ask again on the image's load. Drawn at the device's pixel
 *  ratio so it is sharp; sized in CSS pixels. */
export function cropThumb(img: Pictured, region: Region, max: Size = THUMB_MAX): HTMLCanvasElement | null {
  if (!isCanvas(img) && img.complete === false) return null;
  const crop = cropRect(region, naturalSizeOf(img));
  if (!crop) return null;
  const size = cropSize(crop, max);
  const canvas = img.ownerDocument.createElement("canvas") as HTMLCanvasElement;
  if (typeof canvas.getContext !== "function") return null;
  const dpr = (typeof window !== "undefined" && window.devicePixelRatio) || 1;
  canvas.width = Math.max(1, Math.round(size.width * dpr)); canvas.height = Math.max(1, Math.round(size.height * dpr));
  canvas.className = "fc-crop";
  canvas.setAttribute("style", styleAttr({ width: size.width + "px", height: size.height + "px" }));
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", regionDesc(region) + " of the " + (isCanvas(img) ? "page" : "image"));
  try {
    const cx = canvas.getContext("2d");
    if (!cx) return null;
    cx.drawImage(img, crop.sx, crop.sy, crop.sw, crop.sh, 0, 0, canvas.width, canvas.height);
  } catch { return null; }
  return canvas;
}
