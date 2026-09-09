// The click-safe opener for anchors a pane writes into rows it rebuilds on every push (pr-links.ts's PR links,
// url-links.ts's URL links), as ONE module either can install: a pane document hangs it once, on the capture
// phase, and the anchor's click never reaches the row or card handler beneath it (a link in a feed card must
// open its page, not also open the card's modal; one in a Waiting-on-you row must not also fold the row).
//
// Click-safe across re-renders (ui/CLAUDE.md): the action hangs on the STABLE document, keyed off the anchor's
// `href` attribute, never on the anchor node, which every push rebuilds. A native `click` needs the press and
// the release on one node, so a push mid-press would drop it (or hand it to the card underneath). So the press
// is followed by attribute: `pointerdown` remembers the href under the primary button, `pointerup` on an
// accepted anchor with the SAME href opens it (the rebuilt twin counts, the node's identity does not), and the
// native click that may follow is spent, so the card's own handler never sees it. That click can land only on
// the released node or one of its ancestors (the anchor itself, or the common ancestor when the pressed node is
// gone), so only a click there is spent: one arriving anywhere else with no press behind it (the browser fired
// none, then a programmatic .click() or an assistive-technology activation came) passes as the ordinary click
// it is (the flag ate one such click before; review find, 2026-09-06). The click path itself stays for a
// keyboard activation (Enter on a focused link fires click alone). Every flag clears on the next press, key or
// click: an event, never a timer.
//
// What opens: on the web dashboard the viewer's own browser opens a tab; in a VS Code webview the href goes to
// the host, which openExternal()s it (view-routing.ts routes `openLink` for every pane; extension.ts consumes
// it for every panel). `hrefAt` is the installer's: it names the anchors this opener serves (the module's own
// class, an href shape it wrote) and returns the href to open, or null for anything else. The chat pane
// installs none of these: its own document-level a[href] delegate already opens every absolute-scheme anchor.

export type HrefAt = (target: EventTarget | null) => string | null;
export interface OpenerEnv { protocol: () => string; open: (href: string) => void }
export type OpenerDoc = { addEventListener(type: string, fn: (e: Event) => void, capture?: boolean): void };
export type OpenerPost = ((msg: { type: string; href: string }) => void) | undefined;

export const browserEnv: OpenerEnv = {
  protocol: () => (typeof location !== "undefined" ? location.protocol : ""),
  open: (href) => { window.open(href, "_blank", "noopener,noreferrer"); },
};

/** The href of the anchor matching `sel` at or above `t`, when `accept` takes it; null otherwise. */
export function anchorHrefAt(t: EventTarget | null, sel: string, accept: (href: string) => boolean): string | null {
  const el = t as Element | null;
  const a = el && typeof el.closest === "function" ? (el.closest(sel) as HTMLAnchorElement | null) : null;
  const href = a ? a.getAttribute("href") || "" : "";
  return href && accept(href) ? href : null;
}

export function installLinkOpener(doc: OpenerDoc, post: OpenerPost, hrefAt: HrefAt, env: OpenerEnv = browserEnv): void {
  const open = (href: string): void => {
    const p = env.protocol();
    if (p === "http:" || p === "https:") env.open(href);
    else if (post) post({ type: "openLink", href });
  };
  const primary = (e: Event): boolean => {
    const pe = e as PointerEvent;
    return (pe.button === undefined || pe.button === 0) && pe.isPrimary !== false;
  };
  /** is `t` `node` or one of its ancestors: the only targets the click after a release on `node` can have */
  const inclusiveAncestor = (t: EventTarget | null, node: EventTarget): boolean =>
    t === node || (!!t && typeof (t as Node).contains === "function" && (t as Node).contains(node as Node));
  let pressed: string | null = null;        // the accepted href under the primary button since pointerdown
  let served: EventTarget | null = null;    // the node released on when pointerup opened a link: its click is already served
  doc.addEventListener("pointerdown", (e) => { served = null; pressed = primary(e) ? hrefAt(e.target) : null; }, true);
  doc.addEventListener("pointercancel", () => { pressed = null; }, true);
  doc.addEventListener("keydown", () => { served = null; pressed = null; }, true);
  doc.addEventListener("pointerup", (e) => {
    const was = pressed;
    pressed = null;
    if (!was || !primary(e) || hrefAt(e.target) !== was) return;   // released elsewhere: no click
    open(was);
    served = e.target;
  }, true);
  doc.addEventListener("click", (e) => {
    const node = served;
    served = null;
    if (node && inclusiveAncestor(e.target, node)) { e.preventDefault(); e.stopPropagation(); return; }
    const href = hrefAt(e.target);
    if (!href) return;
    e.preventDefault();
    e.stopPropagation();
    open(href);
  }, true);
}
