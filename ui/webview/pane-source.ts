// [fork] THE SHELL BUNDLE'S SOURCE CHECK (2026-09-29): paneSourceOk, the five code lines below, is ADOPTED from the
// romp project's repository, github.com/romp-on/romp, at commit f4a57200894ede72a4d4469570490aa64fbf9e94, where the
// same five lines make up ui/webview/pane-source.ts under six comment lines of its own. They are that commit's text
// byte for byte: tests/test_shell_source_check.py NoOtherWriter pins them by sha256. The project's six comment lines
// are left out here because they name a plan and a test file the fork does not have, so a later fold of the project's
// file resolves the code lines as IDENTICAL and keeps this header in place of those six lines.
// What it reads: the shell's first inline script defines window.__rompPaneSourceOk (kernel.py _LANDING_BOOT_JS, adopted
// from the same commit), which counts a message only when its immediate source is an iframe of the shell's document and
// its origin is the shell's location.origin. The shell's bundled palette (palette-main.ts, the shell page's
// palette-main.js) reads it through here and FAILS CLOSED: with no check on the page, no message is acted on, and a
// check that throws or answers anything but true refuses too. ui/webview/foreign-sender-listeners.test.ts runs the
// palette's two window listeners through this helper and takes their census; tests/test_shell_source_check.py takes the
// census of the shell's inline listeners.
export function paneSourceOk(e: MessageEvent, w: Window = window): boolean {
  const f = (w as unknown as { __rompPaneSourceOk?: unknown }).__rompPaneSourceOk;
  if (typeof f !== "function") return false;
  try { return (f as (ev: MessageEvent) => unknown)(e) === true; } catch { return false; }
}
