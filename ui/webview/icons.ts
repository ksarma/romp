// The stroke-family glyphs the bars share: a 24-unit viewBox, currentColor strokes, round caps (the composer
// buttons' family). ONE drawing per meaning, so a download reads the same in the lightbox's tray and in the file
// viewer's title bar (T367, the user 2026-09-12: the viewer's word buttons became icons, and the tray's glyph is
// reused, not redrawn). Inline SVG literals — no sanitize; aria-hidden, the button's title and aria-label carry
// the words (progressive disclosure: the meaning one hover away).
const svg = (paths: string): string =>
  '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"'
  + ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths + '</svg>';
/** the tray: an arrow down onto a bar (the image lightbox's download control since 2026-08-19) */
export const ICON_DOWNLOAD = svg('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
  + '<polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>');
/** two offset sheets (the lightbox's copy-image control since 2026-08-31) */
export const ICON_COPY = svg('<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>'
  + '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>');
/** a pencil over a baseline */
export const ICON_EDIT = svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>');
/** a magnifier with a plus: the text-size control's one glyph */
export const ICON_ZOOM = svg('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'
  + '<line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>');
/** a fork: one line in from the left that branches into two, up-right and down-right, running on to the right
 *  edge; no arrowheads (the user 2026-09-12, describing the chat's fork control) */
export const ICON_FORK = svg('<polyline points="2 12 9 12 15 7 22 7"/><polyline points="9 12 15 17 22 17"/>');
/** the viewer's Back and Forward (plans/markdown-viewer.md, "Follow-on: Link navigation", L2): an arrow left, an arrow right */
export const ICON_BACK = svg('<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>');
export const ICON_FORWARD = svg('<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>');
/** a figure's "Open the picture" (the same follow-on, L3): two arrows out of opposite corners */
export const ICON_EXPAND = svg('<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>');
/** the same control on a picture from the web (the file review's round 11, ui-1 with extra8-1): a box with an arrow leaving
 *  its top-right corner, the open that leaves for another host in a new tab; keyed on the figure's target, never on its state */
export const ICON_OUTBOUND = svg('<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>');
/** the acknowledgements a glyph button swaps to: done, and failed */
export const ICON_CHECK = svg('<polyline points="20 6 9 17 4 12"/>');
export const ICON_CROSS = svg('<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>');

// (THE PADLOCK the chat strip wore for the tab lock, T395, left with T415: the lock is a switch in the settings card, and the
// Sessions pane's lock-to-now toggle draws its own padlock in ui/romp-timeline-view.js _drawLockToggle, the one drawing now.)
/** THE settings gear, one glyph from one source (T405, the user 2026-09-13): the gear-without-hub character the shell's rail
 *  wears at the bottom right of every romp page. The chat strip's tab-widgets gear renders this constant, and the kernel
 *  reads it FROM this file when it builds the rail (kernel.py _gear_glyph), so the two cannot drift. A character, not a
 *  drawing: each host sizes it to its row. */
export const GEAR_GLYPH = "\u26ED";
