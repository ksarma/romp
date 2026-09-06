// Region comments on images — the OVERLAY (plans/file-review.md, Slice 3; contract E5).
//
// A person reading a figure wants to point at a part of it — the axis label that is wrong, the bar that
// should not be there — and until now the only comment an image took was on the file as a whole. This
// module puts a drawing surface over every rendered image the viewer shows (the standalone image body,
// or each figure in rendered markdown): a `position: relative` wrapper around the <img>, an absolutely
// positioned overlay the size of the DRAWN image, and on it one rectangle per region comment, placed by
// CSS percentages from the stored fractions, so it is right at any viewer width by construction. A drag
// on the overlay becomes a region (region-geometry.ts does the arithmetic); the panel (file-comments.ts)
// decides what a drawn region means — a new comment's composer, or the re-placement of an existing one.
//
// A PDF page (Slice 4) is a picture too: the chunk draws each page into a canvas inside a wrapper that is
// already `position: relative` (div.fileview-pdf-page, data-page 1-based), so the layer takes that wrapper
// as its ANCHOR instead of wrapping the canvas — the canvas stays where the chunk put it, the overlay joins
// it — and the picture's natural size is the canvas's backing store (the page's own aspect). A region on a
// page is a fraction of the page as drawn, which is why it is width-independent there too (contract F4).
//
// The overlay draws only while the panel is OPEN and the primary pointer is fine (`active`): the
// rectangles are the file's marks and show whenever the highlights do (the probe's status paints both),
// but a closed panel must not turn every picture into a drawing surface — the cursor, the native image
// drag and the context menu stay the browser's. Desktop only (decision 26): with a coarse primary
// pointer (`(pointer: coarse)`) the overlay never takes pointer events, so the picture behaves as before
// and the whole-file comment stands in; the rectangles stay clickable in both cases, since they open cards.
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

/** Whether the primary pointer is a finger (a phone or tablet): region drawing is off there (E5). */
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
const mk = (doc: Document, tag: string, cls: string): HTMLElement => { const e = doc.createElement(tag); e.className = cls; return e; };

export class RegionLayer {
  /** the positioned box the overlay sits in: the span this layer wrapped around an <img>, or the anchor it was given */
  readonly wrap: HTMLElement;
  readonly overlay: HTMLElement;
  /** whether `wrap` is this layer's own span (unwrapped on dispose) or a caller's anchor (left standing) */
  private readonly owned: boolean;
  private press: { id: number; start: Point; fromRegion: boolean; captured: boolean } | null = null;
  private band: HTMLElement | null = null;
  private drew = false;
  /** whether a drag draws here: the panel is open and the pointer is fine (setActive) */
  active = false;
  private readonly onResize = () => this.place();
  private readonly onLoad = () => this.place();
  private sizer: ResizeObserver | null = null;

  /** `anchor`: an already-positioned element holding the picture (a PDF page's wrapper), used as is; without one
   *  the layer wraps the <img> in a span of its own. */
  constructor(readonly img: Pictured, readonly hooks: LayerHooks, anchor?: HTMLElement | null) {
    const doc = img.ownerDocument;
    this.overlay = mk(doc, "div", "fc-overlay fc-overlay-off");
    this.owned = !anchor;
    if (anchor) {
      this.wrap = anchor;
    } else {
      this.wrap = mk(doc, "span", "fc-imgwrap");
      const parent = img.parentNode;
      if (parent) parent.insertBefore(this.wrap, img);
      this.wrap.appendChild(img);
    }
    this.wrap.appendChild(this.overlay);
    img.addEventListener("load", this.onLoad);
    // the exact event for "the drawn size changed": the aside opening narrows the body with no window resize;
    // the window's resize stands in where the observer is missing
    if (typeof ResizeObserver !== "undefined") { this.sizer = new ResizeObserver(() => this.place()); this.sizer.observe(img); }
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
  /** The drawn image's box in client coordinates: the element's rect, less any letterbox `object-fit: contain` adds. */
  box(): Box { return drawnBox(this.img.getBoundingClientRect(), this.natural()); }

  /** Size the overlay to the drawn image. The wrapper hugs the <img>, so the sheet's `inset: 0` is right
   *  whenever the image fills its element; a letterboxed image gets pixel offsets, re-measured on the
   *  image's load and on every resize. A wrapper with no size yet (not laid out) claims nothing. */
  place(): void {
    const w = this.wrap.getBoundingClientRect();
    const off = w.width > 0 && w.height > 0 ? overlayOffsets(w, this.box()) : null;
    if (!off) { this.overlay.removeAttribute("style"); return; }
    this.overlay.setAttribute("style", styleAttr({ left: off.left + "px", top: off.top + "px", width: off.width + "px", height: off.height + "px" }));
  }

  /** Pointer events on the overlay (while active): a press that moves past the click threshold draws
   *  a rubber band and, on release, becomes a region; a press that does not move is the picture click the
   *  viewer already had (the embed-line Comment offer), unless it began on a rectangle — that click opens
   *  the card through the delegate root and needs nothing from here. Pointer capture keeps a drag that
   *  leaves the picture alive; the region is clamped to the image.
   *
   *  A press that begins on a RECTANGLE is not captured at the press: the browser fires the click it
   *  synthesizes at the pointer's capture target, so capturing here sent that click to the overlay, where the
   *  delegate root finds no data-act, and the card never opened while the panel was open (2026-09-06; with the
   *  panel closed the handler returns before capturing, so the same click worked). Left alone, the click
   *  targets the rectangle, whose data-act="fcopen" the row's delegate routes. Capture then waits for the
   *  drag, if one comes: it is taken when the band appears, so a drag begun on a rectangle still survives
   *  leaving the picture. The press's default is still cancelled (no selection starts behind the overlay),
   *  and with it the focus the mousedown would have given the rectangle — so the rectangle is focused here. */
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
      if (dragIsClick(p.start, cur)) { if (!p.fromRegion) this.hooks.onClick(this.img); return; }
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
      const region = t && typeof t.closest === "function" ? (t.closest(".fc-region") as HTMLElement | null) : null;
      const fromRegion = !!region;
      this.press = { id: ev.pointerId, start: { x: ev.clientX, y: ev.clientY }, fromRegion, captured: !fromRegion };
      if (!fromRegion) capture(ev);
      ev.preventDefault();                               // no native image drag, no selection behind the overlay
      if (region && typeof region.focus === "function") region.focus();   // the focus the cancelled mousedown would have given it
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
    // the click a browser synthesizes after the drag must not reach the delegate root as an activation
    o.addEventListener("click", (ev: Event) => { if (this.drew) { this.drew = false; ev.stopPropagation(); ev.preventDefault(); } });
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
   *  counts as a removal to the browser's click tracking too, so a rectangle that is up is never re-inserted: a new
   *  mark's rectangle goes in right after the previous mark's, which keeps the marks' order for every rectangle
   *  painted here without moving one. A rectangle whose mark is gone leaves; the pending region is one node,
   *  updated the same way; anything else on the overlay but the drag band is removed, so nothing is ever stacked. */
  paint(marks: RegionMark[], pending: Region | null, replacing: boolean): HTMLElement[] {
    const o = this.overlay; const doc = o.ownerDocument;
    const isRegion = (n: Node): n is HTMLElement => {
      const cl = (n as HTMLElement).classList;
      return !!cl && typeof cl.contains === "function" && cl.contains("fc-region");
    };
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
    for (const m of marks) {
      let r = have.get(m.id);
      if (r) have.delete(m.id);
      else {
        r = mk(doc, "div", "fc-region");
        r.dataset.act = "fcopen"; r.dataset.id = m.id;
        r.tabIndex = 0; r.setAttribute("role", "button");
        r.appendChild(mk(doc, "span", "fc-region-chip"));
        const kids = o.childNodes;
        const at = last ? Array.prototype.indexOf.call(kids, last) + 1 : 0;
        o.insertBefore(r, (kids[at] as Node | undefined) || null);
      }
      r.className = "fc-region" + (m.state === "stale" ? " fc-stale" : m.state === "unknown" ? " fc-unknown" : "");
      r.setAttribute("style", styleAttr({ ...regionStyle(m.region), ...(m.style || {}) }));
      r.title = "Open the comment on this region" + (m.state === "stale" ? " (the " + noun + " changed after it was drawn)" : m.state === "unknown" ? " (whether the " + noun + " changed could not be checked)" : "");
      let chip = r.querySelector(".fc-region-chip") as HTMLElement | null;
      if (!chip) { chip = mk(doc, "span", "fc-region-chip"); r.appendChild(chip); }
      chip.dataset.label = m.label;                      // drawn by the sheet: no text node under the picture
      out.push(r); last = r;
    }
    for (const gone of have.values()) o.removeChild(gone);   // resolved, or moved to another picture
    if (pending) {
      const p = pend || mk(doc, "div", "fc-region fc-region-pending");
      p.setAttribute("style", styleAttr(regionStyle(pending)));
      if (!pend) o.appendChild(p);
    } else if (pend) o.removeChild(pend);
    o.classList.toggle("fc-replacing", replacing);
    return out;
  }

  /** Take the overlay down and put the picture back where it was; an anchor the layer was given keeps its picture. */
  dispose(): void {
    this.img.removeEventListener("load", this.onLoad);
    if (this.sizer) { this.sizer.disconnect(); this.sizer = null; }
    else window.removeEventListener("resize", this.onResize);
    if (!this.owned) { this.overlay.remove(); return; }
    const parent = this.wrap.parentNode;
    if (parent) { parent.insertBefore(this.img, this.wrap); parent.removeChild(this.wrap); }
  }
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
