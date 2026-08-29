// A stood-down settings gesture must be visible to the dashboard that made it (2026-08-29).
// The kernel's gesture-time ordering (tests/test_setting_gesture_order.py) stands a stale
// gesture down at the store — but the only output used to be one kernel stderr line: the open
// gear kept displaying the refused pick as applied (fill() runs only on openSettings), and since
// the mesh then AGREES on the kept value, the mixed marks show nothing either. Event-keyed fix,
// no polling: the WS branch that stands a gesture down answers the DELIVERING socket with a
// small {type:"settingStale", setting, storedGt, kept} frame (the same targeted _reply idiom the
// saveFile acks use), and the gear — the shared module both hosts load — toasts it in plain
// words and re-fills itself if it is open. The kernel-side semantics are behavior-tested in
// test_setting_gesture_order.py; no jsdom harness for these renderers, so the wiring is pinned
// at the source (the repo convention).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", ...p), "utf8");
const GEAR = read("ui", "webview", "gear.js");
const GEAR_CSS = read("ui", "webview", "gear.css");
const KERNEL = read("kernel", "kernel.py");

test("the kernel answers the delivering socket with a settingStale frame — the _reply idiom", () => {
  assert.match(KERNEL, /def _tell_stale_gesture\(client\)/, "the reply helper exists");
  assert.ok(KERNEL.includes('"type": "settingStale"'), "the frame is the settingStale type");
  const helper = KERNEL.slice(KERNEL.indexOf("def _tell_stale_gesture"), KERNEL.indexOf("def _tell_stale_gesture") + 2000);
  assert.match(helper, /_reply\(client,/, "targeted reply on ONE socket — never a broadcast");
  // every queued-class WS branch answers on its stand-down path (9 = autoNudge, fileEditing,
  // updateMode + the six judge tiers)
  const sites = KERNEL.match(/_tell_stale_gesture\(client\)/g) || [];
  assert.ok(sites.length >= 9, `every gt-gated branch tells the delivering socket (got ${sites.length})`);
});

test("the gear hears the frame: a plain-words toast, and a re-fill only while the modal is open", () => {
  assert.ok(GEAR.includes("'settingStale'"), "the gear listens for the frame");
  // re-engagement is event-keyed: the frame triggers the re-fill; no timer, no polling
  const seg = GEAR.slice(GEAR.indexOf("'settingStale'") - 600, GEAR.indexOf("'settingStale'") + 1600);
  assert.match(seg, /if \(!p\.hidden\) fill\(\);/, "an OPEN gear re-reads the kernel's actual values; a closed one fills on its next open anyway");
  assert.doesNotMatch(seg, /setInterval|setTimeout\(fill/, "no polling — the frame IS the event");
  assert.ok(GEAR.includes("changed more recently"), "the toast says what happened in plain words");
  assert.ok(GEAR.includes("staleToast"), "the dropWarn-style toast renderer exists");
});

test("the toast is click-safe and self-clearing, styled by the gear's own sheet (both hosts load it)", () => {
  // container created once, dismissal delegated to it (the standing click-safe rule); each toast
  // auto-retires so a wall of stale notices can never accrete
  assert.ok(GEAR.includes("rs-stale-toasts"), "one stable container");
  assert.ok(GEAR.includes("rs-stale-toast'"), "per-notice toast node");
  assert.match(GEAR, /box\.addEventListener\('click'/, "dismissal rides the stable container, not the rebuilt child");
  for (const sel of ["#rs-stale-toasts", ".rs-stale-toast"])
    assert.ok(GEAR_CSS.includes(sel), `gear.css styles ${sel} — the chat pane loads gear.css, not feed.css`);
});

test("the toast wears the family dismissal: a visible ✕ in the chip-✕ dress, Escape clears, fade", () => {
  // The family's dismissal standard (the user 2026-08-25, after a notice with no visible way out;
  // warn-toast.test.ts pins the family home, render.ts warnToast + styles.css .warn-toast-x): a
  // visible ✕, Escape clears the stack, and the fade before the auto-remove. This toast's mint
  // site is a frozen tab flushing on recovery — touch devices, exactly where an invisible
  // whole-toast click and hoverless ✕-less copy help least. gear.js is its own document (panes
  // that load only this sheet), so the treatment is COPIED from the family home; these pins keep
  // the copy in step with it.
  assert.match(GEAR, /x\.className = 'rs-stale-toast-x'/, "a visible ✕ button rides every toast");
  assert.match(GEAR, /x\.setAttribute\('aria-label', 'Dismiss'\)/, "the ✕ is named for assistive tech");
  assert.match(GEAR, /x\.title = 'dismiss \(Esc\)'/, "the ✕ teaches the keyboard way out");
  // Escape clears the stack, additively — no stopPropagation, so no other surface loses the key
  assert.ok(GEAR.includes("e2.key === 'Escape'"), "Escape clears the stack");
  const esc = GEAR.slice(GEAR.indexOf("e2.key === 'Escape'"), GEAR.indexOf("e2.key === 'Escape'") + 200);
  assert.doesNotMatch(esc, /stopPropagation/, "clearing toasts is additive noise-removal");
  // the fade precedes the auto-remove, on the family's timings
  assert.match(GEAR, /t\.classList\.add\('fade'\); \}, 11000\)/, "the fade arms first");
  assert.match(GEAR, /t\.remove\(\); \}, 12000\)/, "the self-clearing backstop stays");
  // the ✕ wears the chip-✕ dress in gear.css's own literal palette (the gear's hosts don't load
  // styles.css, so var(--dim)/var(--fg) don't resolve here)
  assert.match(GEAR_CSS, /\.rs-stale-toast-x \{ flex: 0 0 auto; border: none; background: none; cursor: pointer; color: #9aa0a6;/);
  assert.match(GEAR_CSS, /\.rs-stale-toast-x:hover \{ color: #fff; background: rgba\(255, 255, 255, 0\.08\); \}/);
  assert.match(GEAR_CSS, /\.rs-stale-toast\.fade \{ opacity: 0; \}/, "the fade class actually fades");
  assert.match(GEAR_CSS, /\.rs-stale-toast \{[^}]*transition: opacity/, "…through a real transition");
});

test("the kept value rides when cheap, and reads as words (booleans become on/off)", () => {
  assert.match(KERNEL, /def _setting_kept_value\(name\)/, "one cheap store read at reply time, never on the apply path");
  assert.ok(GEAR.includes("m.kept === true ? 'on'"), "a boolean setting's kept value reads as on/off in the toast");
});
