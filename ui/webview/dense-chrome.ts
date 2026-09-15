// COMPACT TABS AND AGENTS (the gear's denseChrome setting; the user 2026-09-08: on a phone, the tab strip
// and the background-work panel left about three lines of transcript in view). Density only: ONE body
// class, `dense-chrome`, that styles.css's scoped block keys on for the strip's tabs and group headers and
// the #bg-tasks panel's rows. The chat calls this beside applyTheme from applyChatScheme (render.ts), at
// startup and on every settings change, so a gear flip repaints the strip and the panel at once through
// the cascade. The panel is not rebuilt; the strip is, by the renderTabs() that follows (the setting is in
// its rebuild signature), so the per-row hairlines and keep breaks land under the re-heighted items
// (review round 2 of the keep-with-next change). Pure over the document it is handed, like theme.ts, so a
// test can run it against a fake body. Absent or off, the class is removed and the page renders exactly as
// before the setting existed.
import type { RompSettings } from "./settings";

export const DENSE_CHROME_CLASS = "dense-chrome";

export function applyDenseChrome(doc: Document, s: RompSettings): void {
  doc.body.classList.toggle(DENSE_CHROME_CLASS, s.denseChrome === true);
}
