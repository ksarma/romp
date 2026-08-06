// Build-drift banner + one-click self-update in VS Code (the user 2026-07-13, who wanted a banner when anything gets out of
// sync; 2026-07-14, who wanted a button that does it for them, like the web view
// has). The VS Code panes run VSIX-BUNDLED webview code — no kernel-served page, no ?v= token, so the
// browser pages' shim check never runs here, and a pane's wsStale posts go to a parent that doesn't
// handle them. Instead the EXTENSION compares the `dv` (kernel dist token) riding every keepalive
// against its own bundled build stamp (__ROMP_BUILD__, baked by esbuild.js) and prompts ONCE when the
// installed bundle predates a rebuild. Unlike the browser (whose fix is a reload), a VS Code reload
// can't help — the code is baked into the on-disk VSIX — so the prompt offers a real "Update extension"
// that rebuilds + reinstalls the VSIX via vscode-extension/install.sh. Source pins (the extension host
// needs the vscode module, so the wiring can't run under node --test).
import { test } from "node:test";
import assert from "node:assert";
import * as fs from "fs";
import * as path from "path";

const EXT = fs.readFileSync(path.resolve(process.cwd(), "src", "extension.ts"), "utf8");
const ESBUILD = fs.readFileSync(path.resolve(process.cwd(), "esbuild.js"), "utf8");

// The body of updateExtension()..runInstall — where any reload lives — used to pin "reload is
// user-gated" without matching the whole file.
function slice(start: string, end: string): string {
  const a = EXT.indexOf(start);
  const b = EXT.indexOf(end, a + 1);
  assert.ok(a >= 0 && b > a, `could not slice ${start}..${end}`);
  return EXT.slice(a, b);
}

test("esbuild bakes a build stamp into the extension bundle", () => {
  // epoch SECONDS — the same clock as the kernel's dist token (newest dist/*.js mtime), so the two
  // compare directly with no unit conversion.
  assert.match(ESBUILD, /define:\s*\{\s*__ROMP_BUILD__:\s*String\(Math\.floor\(Date\.now\(\) \/ 1000\)\)\s*\}/);
});

test("the extension compares keepalive dv against the stamp and prompts once", () => {
  assert.ok(EXT.includes("declare const __ROMP_BUILD__: number;"), "the define is declared for tsc");
  assert.ok(EXT.includes("function maybeBuildNotice(dv: unknown)"), "the drift check exists");
  assert.ok(EXT.includes("if (buildNotified || !BUILD_STAMP || typeof dv !== \"number\" || dv <= BUILD_STAMP) return;"),
    "latched (one prompt per window), guarded when the stamp is absent, and only NEWER dv fires");
});

test("the drift prompt is ACTIONABLE — but only with actions that can work on THIS host", () => {
  const notice = slice("function maybeBuildNotice(dv: unknown)", "async function updateExtension");
  // The buttons are chosen from a live resolution, never hardcoded: an installed-from-VSIX copy has
  // no checkout to rebuild from, and an Update button there could only ever produce an error toast
  // (the review of the /version-rompDir fix, 2026-08-05). driftNotice owns that choice and is tested
  // in update-target.test.ts; this pins the WIRING.
  assert.ok(notice.includes("driftNotice(resolveInstallTarget())"), "the notice is built from a live resolution");
  assert.ok(notice.includes("showInformationMessage(notice.message, ...notice.actions)"),
    "the toast shows exactly the actions the notice allows — no extra literal button");
  assert.ok(!/"Update extension"/.test(notice), "no hardcoded Update button that ignores the resolution");
  assert.ok(notice.includes("choice === UPDATE_ACTION") && notice.includes("void updateExtension()"),
    "the update action runs the self-update");
  assert.ok(notice.includes("choice === COPY_ACTION") && notice.includes("void copyInstallCommand()"),
    "the fallback action puts the command on the clipboard");
  // The notice itself must NOT reload — the drift toast never auto-anything (the reload is gated later).
  assert.ok(!notice.includes("reloadWindow"), "maybeBuildNotice must not reload the window");
});

test("copying the install command is client-side, so the offered action cannot fail", () => {
  const copy = slice("function copyInstallCommand", "// Ports are CONFIGURABLE");
  assert.ok(copy.includes("vscode.env.clipboard.writeText(INSTALL_COMMAND)"), "the clipboard, not a shell-out");
  assert.ok(!/execFile|runInstall/.test(copy), "nothing is executed on this path");
  assert.ok(copy.includes("setStatusBarMessage"), "the click is acknowledged");
});

test("updateExtension rebuilds+reinstalls the VSIX, then offers a USER-gated reload", () => {
  const upd = slice("async function updateExtension", "function runInstall");
  // The script it runs is resolved from THIS host — the VSIX's own path, else our own ROMP_DIR —
  // never from a kernel response: /version is auth-exempt, so a rompDir off the wire would let
  // whatever answers the port pick the directory a shell command runs from (update-target.ts).
  assert.ok(EXT.includes("resolveInstallScript(ctx?.extensionPath || \"\", process.env.ROMP_DIR"),
    "the exec target is resolved locally from the extension's own installed path");
  // Re-resolved at CLICK time, not read off whatever the toast decided: this entry point is also the
  // palette command and the menu's Update row (neither preceded by a toast), and a toast can sit on
  // screen while the checkout it named moves.
  assert.ok(upd.includes("resolveInstallTarget()"), "the click re-resolves rather than trusting a stale check");
  // Scan the RESOLVER too, not just updateExtension. This delta moved resolution out into
  // resolveInstallTarget(), and a guard that still slices only updateExtension stopped covering the
  // very thing it exists for: a kernel-supplied rompDir reintroduced inside the helper passed this
  // assertion untouched. The exec target may come from no network-supplied value, wherever it is
  // computed.
  const resolver = slice("function resolveInstallTarget", "// Build-drift banner");
  assert.ok(!/rompDir|fetchJson|homedir/.test(resolver),
    "the resolver takes nothing off the wire either — /version is unauthenticated");
  assert.ok(!/rompDir|fetchJson|homedir/.test(upd),
    "nothing the kernel reports (and no $HOME expansion of it) reaches the exec target");
  assert.ok(upd.includes("runInstall(script, extDir)") && upd.includes("target.script"),
    "runs vscode-extension/install.sh");
  assert.ok(upd.includes("packaged romp-chat-view\\.vsix") && upd.includes("install into:"),
    "a clean exit is not enough — require the packaged + installed markers (install.sh skips gracefully)");
  // Reload is behind an explicit button click, never automatic (prefer-reload-banner-not-auto).
  assert.ok(upd.includes('"Reload window"') && upd.includes('choice === "Reload window"') &&
    upd.includes('executeCommand("workbench.action.reloadWindow")'),
    "reload only fires when the user clicks Reload window");
  assert.ok(upd.includes("showErrorMessage") && upd.includes("MANUAL_REMEDY"),
    "a failed/skipped update fails loudly with the manual remedy");
  // A copy that can't rebuild itself (installed from a .vsix, no ROMP_DIR) says so and stops —
  // it never falls back to running some other directory's install.sh. Same words as the toast, and
  // the same clipboard action, so the two ways of reaching it read as one thing.
  assert.ok(upd.includes("if (!target)") && upd.includes("CANT_REBUILD") && upd.includes("return;"),
    "no resolvable checkout → a plain error and no shell-out");
  assert.ok(upd.includes("COPY_ACTION"), "the dead end still hands over the command to run");
});

test("runInstall shells out with the host's resolved env so node/npm/code resolve", () => {
  const run = slice("function runInstall", "function updateHint");
  assert.ok(run.includes('execFile("bash"') && run.includes("env: process.env"),
    "install.sh runs under bash with the extension host's PATH");
});

test("a palette command exposes the update anytime a faded toast can't be clicked", () => {
  assert.ok(EXT.includes('registerCommand("rompChat.updateExtension", updateExtension)'),
    "the command is registered");
  const pkg = fs.readFileSync(path.resolve(process.cwd(), "package.json"), "utf8");
  assert.ok(pkg.includes('"rompChat.updateExtension"') && pkg.includes('"romp: Update Extension"'),
    "declared in package.json so it shows in the command palette");
});

test("only panel pipes check drift — the passive status pipe never toasts", () => {
  assert.ok(EXT.includes('if (m && m.type === "ka" && !this.passive) maybeBuildNotice(m.dv);'),
    "the ka hook rides the pipe message handler, gated off the passive (status) pipe");
});
