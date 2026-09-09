// COMPACT TABS AND AGENTS (the gear's denseChrome setting; the user 2026-09-08, whose phone showed
// about three lines of transcript between the tab strip and the box of background work). Density
// only: ONE body class, `dense-chrome`, that styles.css's scoped block keys on for the strip's tabs
// and group headers and the #bg-tasks box's rows. The chat calls this beside applyTheme from
// applyChatScheme (render.ts), at startup and on every settings change, so a gear flip re-sizes the
// strip and the box at once through the cascade. The box is not rebuilt; the strip is, by the
// renderTabs() that follows (the setting is in its rebuild signature), so the per-row hairlines and
// keep breaks land under the re-heighted items (review round 2 of the keep-with-next change). Pure
// over the document it is handed, like theme.ts, so a test can run it against a fake body. Absent or
// off, the class is removed and the page renders exactly as before the setting existed.
import type { RompSettings } from "./settings";

export const DENSE_CHROME_CLASS = "dense-chrome";

export function applyDenseChrome(doc: Document, s: RompSettings): void {
  doc.body.classList.toggle(DENSE_CHROME_CLASS, s.denseChrome === true);
}
