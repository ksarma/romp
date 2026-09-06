// A stood-down settings gesture must be visible to the dashboard that made it (2026-08-29).
// The kernel's gesture-time ordering (tests/test_setting_gesture_order.py) stands a stale
// gesture down at the store — but the only output used to be one kernel stderr line: the open
// gear kept displaying the refused pick as applied (fill() runs only on openSettings), and since
// the mesh then AGREES on the kept value, the mixed marks show nothing either. Event-keyed fix,
// no polling: the WS branch that stands a gesture down answers the DELIVERING socket with a
// small {type:"settingStale", setting, storedGt, kept, gesture} frame (the same targeted _reply
// idiom the saveFile acks use), and the gear — the shared module both hosts load — toasts it in
// plain words and re-fills itself if it is open. The toast (PR #879 follow-up) learns the stamp
// it lost to, says the pick was not applied WITHOUT claiming another device acted (the kernel
// knows only that it holds a larger stamp), and offers Apply anyway: the frame's echoed gesture
// re-issued with a fresh stamp above everything this page has seen. The kernel-side semantics are
// behavior-tested in test_setting_gesture_order.py; no jsdom harness for these renderers, so the
// wiring is pinned at the source (the repo convention).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const read = (...p: string[]) => fs.readFileSync(path.resolve(process.cwd(), "..", ...p), "utf8");
const GEAR = read("ui", "webview", "gear.js");
const GEAR_CSS = read("ui", "webview", "gear.css");
const KERNEL = read("kernel", "kernel.py");

test("the kernel answers the delivering socket with a settingStale frame — the _reply idiom", () => {
  assert.match(KERNEL, /def _tell_stale_gesture\(client, msg\)/, "the reply helper exists and sees the refused message");
  assert.ok(KERNEL.includes('"type": "settingStale"'), "the frame is the settingStale type");
  const helper = KERNEL.slice(KERNEL.indexOf("def _tell_stale_gesture"), KERNEL.indexOf("def _tell_stale_gesture") + 2600);
  assert.match(helper, /_reply\(client,/, "targeted reply on ONE socket — never a broadcast");
  // the echo the toast's Apply anyway re-issues: the refused message minus its stamp (a re-issue
  // can never reuse the stale one)
  assert.match(helper, /"gesture": \{k: v for k, v in msg\.items\(\) if k != "gt"\}/, "the frame echoes the refused gesture without its gt");
  // every queued-class WS branch answers on its stand-down path (9 = autoNudge, fileEditing,
  // updateMode + the six judge tiers)
  const sites = KERNEL.match(/_tell_stale_gesture\(client, msg\)/g) || [];
  assert.ok(sites.length >= 9, `every gt-gated branch tells the delivering socket (got ${sites.length})`);
  assert.equal((KERNEL.match(/_tell_stale_gesture\(client\)/g) || []).length, 0, "no branch still calls the echo-less form");
});

test("/version reports every gt-gated store's last-applied stamp, and the gear stamps above them", () => {
  // the maintainer's follow-up on #879: gesture stamps were the device's bare wall clock, so a
  // laptop ten minutes ahead locked every correctly-clocked device out for ten minutes. The gear
  // already read /version on every open; now it learns each store's stamp there and mints every
  // gesture at max(Date.now(), seen + 1) (ui/webview/gesture-clock.js; gesture-clock.test.ts drives
  // the module). The kernel side is behavior-tested in test_setting_gesture_order.py.
  assert.match(KERNEL, /"settingsGt": _settings_gt\(\),/, "/version carries the stamps (ints only — the route is auth-exempt)");
  assert.match(KERNEL, /def _settings_gt\(\):/);
  assert.match(KERNEL, /def _setting_stored_gt\(name\):/, "one switch mirrors _setting_kept_value's");
  assert.match(GEAR, /var gclock = require\('\.\/gesture-clock\.js'\);/, "the gear loads the clock");
  const fill = GEAR.slice(GEAR.indexOf("function fill() {"), GEAR.indexOf("function fill() {") + 600);
  assert.match(fill, /gclock\.learnAll\(v\.settingsGt\);/, "every open teaches the clock the kernel's current stamps");
  assert.ok(!/gt: Date\.now\(\)/.test(GEAR), "no gear emitter stamps with the bare wall clock");
});

test("the gear hears the frame: a plain-words toast, and a re-fill only while the modal is open", () => {
  assert.ok(GEAR.includes("'settingStale'"), "the gear listens for the frame");
  // re-engagement is event-keyed: the frame triggers the re-fill; no timer, no polling
  const seg = GEAR.slice(GEAR.indexOf("'settingStale'") - 600, GEAR.indexOf("'settingStale'") + 1600);
  assert.match(seg, /if \(!p\.hidden\) fill\(\);/, "an OPEN gear re-reads the kernel's actual values; a closed one fills on its next open anyway");
  assert.doesNotMatch(seg, /setInterval|setTimeout\(fill/, "no polling — the frame IS the event");
  assert.ok(GEAR.includes("staleToast"), "the dropWarn-style toast renderer exists");
  // the frame is new information about that store's clock: learned BEFORE anything else, so the
  // toast's Apply anyway (and the next ordinary click) stamps above the stamp this gesture lost to
  assert.match(seg, /gclock\.learn\(m\.setting, m\.storedGt\);/, "the listener learns storedGt");
});

test("the toast's copy names the setting and the kept value and never claims another device acted", () => {
  // the kernel knows only that it holds a larger stamp — with device clocks minting the stamps,
  // "changed more recently somewhere else" asserted a fact it could not know (#879 review)
  assert.match(GEAR, /return label \+ ': not applied on ' \+ hosts\.join\(', '\) \+ '\. A later pick'\s*\n\s*\+ \(kept \? ' \(' \+ kept \+ '\)' : ''\) \+ ' is already in place\.';/,
    "the copy: what was not applied, on which kernels, and what is in force");
  const copy = GEAR.slice(GEAR.indexOf("function staleText("), GEAR.indexOf("if (!p.hidden) fill();"));
  assert.ok(copy.length > 0 && copy.length < 3000, "the copy helper and the listener located");
  for (const claim of ["somewhere else", "another device", "elsewhere", "changed more recently"])
    assert.ok(!copy.includes(claim), `the toast no longer says "${claim}"`);
  assert.ok(!GEAR.includes("changed more recently"), "the old copy is gone from the file");
});

test("Apply anyway re-issues the echoed gesture with a fresh stamp, and only for the setting the frame names", () => {
  // a new user gesture is legitimate new information — the event the ordering rule wants. The
  // stamp is minted through the clock, which has just learned storedGt, so the re-issue outranks
  // the stamp this pick lost to; the echo's type must match the frame's setting (STALE_TYPE), so a
  // frame from any linked kernel can re-issue that one setting and nothing else
  assert.match(GEAR, /STALE_TYPE\[m\.setting\] !== m\.gesture\.type\) return null;/, "the whitelist");
  assert.match(GEAR, /post\(Object\.assign\(\{\}, m\.gesture, \{ gt: gclock\.stamp\(m\.setting\) \}\)\)/, "the re-issue: the echo plus a fresh stamp");
  assert.ok(GEAR.includes("label: 'Apply anyway'"), "the action's label");
  assert.match(GEAR, /if \(!m\.gesture \|\| typeof m\.gesture !== 'object'/, "an older kernel sends no echo: the toast shows without the action");
  // the button: a real <button type=button>, appended before the ✕; its click bubbles to the
  // container's delegated dismiss (no stopPropagation), so applying also clears the toast
  assert.match(GEAR, /b\.type = 'button'; b\.className = 'rs-stale-toast-act'; b\.textContent = act\.label;/);
  assert.match(GEAR, /b\.addEventListener\('click', act\.run\);/);
  const toast = GEAR.slice(GEAR.indexOf("function staleToast(text, act)"), GEAR.indexOf("function staleText("));
  assert.ok(toast.length > 0, "staleToast(text, act) located");
  assert.doesNotMatch(toast, /\.stopPropagation\(/, "the action's click still dismisses the toast");
  assert.ok(toast.indexOf("rs-stale-toast-act") < toast.indexOf("x.className = 'rs-stale-toast-x'"), "the action sits before the ✕");
  assert.match(toast, /return t;\n  \}/, "the toast node is returned");
  assert.ok(GEAR_CSS.includes(".rs-stale-toast-act {"), "gear.css dresses the button (the gear's hosts load only this sheet)");
  assert.ok(GEAR_CSS.includes(".rs-stale-toast-act:hover {"), "…with a hover");
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
  // the ✕ wears the chip-✕ dress through gear.css's token-with-fallback idiom (the census sheet:
  // tokens resolve in a themed host; the literal fallbacks keep the standalone gear looking right)
  assert.match(GEAR_CSS, /\.rs-stale-toast-x \{ flex: 0 0 auto; border: none; background: none; cursor: pointer;\n\s*color: var\(--text-muted, #9aa0a6\);/);
  assert.match(GEAR_CSS, /\.rs-stale-toast-x:hover \{ color: var\(--fg, #fff\); background: rgba\(255, 255, 255, 0\.08\); \}/);
  assert.match(GEAR_CSS, /\.rs-stale-toast\.fade \{ opacity: 0; \}/, "the fade class actually fades");
  assert.match(GEAR_CSS, /\.rs-stale-toast \{[^}]*transition: opacity/, "…through a real transition");
});

test("one toast per refused gesture, naming the refusing hosts: the fold key is setting + the gesture's own gt", () => {
  // N kernels refusing one stale flush used to draw N identical toasts naming no host (#879
  // review). The frame now carries the refused gesture's own stamp, a remote kernel's frame arrives
  // host-stamped, and the gear folds by (setting, gt) — an event key, never a time window.
  // setting-stale-fold.test.ts drives the lifted block; these pin the three-file wiring.
  assert.match(KERNEL, /_stale_seen\.last = \{"setting": name, "storedGt": applied_gt, "gt": gt\}/, "the stand-down records the refused stamp");
  assert.ok(KERNEL.includes('"gt": st["gt"],'), "…and the frame carries it");
  const FED = read("ui", "webview", "federation.ts");
  assert.ok(FED.includes('if (out.type === "settingStale") out.host = host;'), "a remote kernel's frame is host-stamped on the way in");
  assert.match(GEAR, /var key = typeof m\.gt === 'number' \? m\.setting \+ ':' \+ m\.gt : '';/, "the fold key; no gt (an older kernel) → no fold");
  assert.match(GEAR, /staleOpen\[key\]\.t\.parentNode \? staleOpen\[key\] : null/, "liveness is the node's parentNode at lookup — no cleanup on the timers");
  assert.match(GEAR, /return \(typeof m\.host === 'string' && m\.host\) \? m\.host : 'this machine';/, "the local kernel's frame reads as this machine");
  assert.doesNotMatch(GEAR.slice(GEAR.indexOf("var staleOpen"), GEAR.indexOf("if (!p.hidden) fill();")), /Date\.now\(|setTimeout|setInterval/,
    "the fold keys on the gesture, never on a clock or a window");
});

test("the kept value rides when cheap, and reads as words (booleans become on/off)", () => {
  assert.match(KERNEL, /def _setting_kept_value\(name\)/, "one cheap store read at reply time, never on the apply path");
  assert.ok(GEAR.includes("m.kept === true ? 'on'"), "a boolean setting's kept value reads as on/off in the toast");
});
