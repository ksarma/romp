// The plan's print follow-on (plans/markdown-viewer.md, "## Follow-on: Print (2026-09-19)") records what the print
// build did, and its review rounds changed the flow after the record was written: the chord yields to a key the
// dashboard's command palette already claimed, a held chord's repeats are prevented and not pressed, four Escapes are
// left to the control they belong to while the bar is armed, the machine gained the disabled phase and the body and
// recount events, the wait is re-aimed at a repainted body under the press's deadline, the armed line is recounted at a
// repaint and at a placeholder the person activates by hand and its "Print with them" loads the hosts its title named,
// the line's word buttons hand the keyboard back to the Print button, the wait's line carries the viewer's loader, and
// two browser legs joined the follow-on; the third review (2026-09-19) made the probes one per URL for a press's wait,
// set a lazy picture eager, carried the wait's verdict as `ready` with `why`, derived the body's readiness from the body
// itself (bodyReady, the viewers reporting nothing), dropped the button's `disabled` property for the bar's aria-disabled
// rule with the keyboard handed through the host at a body-out disarm, and pinned the repaint re-aim's deadline by an
// executed case; the fourth review (2026-09-19) gave the settle re-aim's deadline its own executed case.
// tools/markdown-viewer-plan-print.test.mjs holds the first
// build's sentences; this module holds the rounds' sentences to the tree the same way, each read from its source, with
// one difference: the TypeScript sources are read with their comments removed, so a pin here is met by a statement and
// never by a comment that names the same string. Where the section states a count a command produces (the `ls` listing)
// the count is recomputed. Synthetic: only the repo's own text.
// Run: node --test tools/markdown-viewer-plan-print-record.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));
/** A TypeScript source without its comments: a block comment that opens a line, a full-line `//` comment and a trailing
 *  `//` comment that a space precedes (a `//` inside a URL literal follows a colon and stays; a `/*` inside a regex or a
 *  string is mid-line and stays). */
const code = (src) => src.replace(/^[ \t]*\/\*[\s\S]*?\*\//gm, '').replace(/^\s*\/\/[^\n]*$/gm, '').replace(/[ \t]\/\/[^\n]*/g, '');
/** `text` from `start` up to the `end` that follows it; a missing mark fails, which is the failure wanted. */
function between(text, start, end) {
  const a = text.indexOf(start);
  assert.ok(a >= 0, JSON.stringify(start) + ' is in the source');
  const b = text.indexOf(end, a + start.length);
  assert.ok(b > a, JSON.stringify(end) + ' follows it');
  return text.slice(a, b);
}
/** Each of `marks` is in `text`, each after the one before. */
function inOrder(text, marks, what) {
  let last = -1;
  for (const m of marks) {
    const at = text.indexOf(m, last + 1);
    assert.ok(at > last, what + ': ' + JSON.stringify(m) + ' follows the mark before it');
    last = at;
  }
}

const plan = read('plans', 'markdown-viewer.md');
const flow = code(read('ui', 'webview', 'file-print.ts'));
const viewer = code(read('ui', 'webview', 'file-view.ts'));
const guide = read('docs', 'guide.md');

// The section, hard wraps collapsed so an assertion survives a rewrap.
const HEAD = '## Follow-on: Print (2026-09-19)';
const headAt = plan.indexOf('\n' + HEAD + '\n');
assert.ok(headAt >= 0, 'the follow-on section is in the plan');
const section = plan.slice(headAt).replace(/\s+/g, ' ');
const part = (from, to) => {
  const a = section.indexOf(from);
  assert.ok(a >= 0, JSON.stringify(from) + ' heads a part of the section');
  const b = to ? section.indexOf(to, a) : section.length;
  assert.ok(b > a, JSON.stringify(to) + ' follows it');
  return section.slice(a, b);
};
const P1 = part('P1. **', 'P2. **');
const P2 = part('P2. **', 'P3. **');
const P5 = part('P5. **', 'P6. **');
const TESTS = part('**Tests.**', '**Open points for the owner.**');
const OPEN = part('**Open points for the owner.**');
// the flow's keydown handler alone
const onKey = between(flow, 'const onKey = (e: KeyboardEvent): void => {', 'doc.addEventListener("keydown", onKey, true);');
// the machine's event union
const events = between(flow, 'export type PrintEvent =', ';\n');

// ── P1: the chord's fourth condition, the palette ──────────────────────────────────────────────────

test('P1: the chord has a fourth condition, a key no earlier listener prevented; the dashboard\'s palette is that listener, by its binding, its wiring and the shell page that loads it', () => {
  assert.ok(P1.includes('is prevented and treated as a press only while four conditions hold: `body.fileview-open` stands, the card is connected, no text field in the document holds the keyboard (`typingHere`, beside isTypingTarget in file-view.ts), and no listener ahead of this one has prevented the key'));
  assert.ok(P1.includes('the flow stands down on the prevented key (`e.defaultPrevented`), so one keystroke does not open the palette and print too, nothing prints, and the bar\'s Print button prints'));
  // the handler: the three conditions, then the stand-down, then the repeats, then the chord's prevent and the press
  inOrder(onKey, ['if (!doc.body.classList.contains("fileview-open") || !host.card.isConnected || host.typing()) return;',
    'if (e.defaultPrevented) return;', 'if (isPrintKeys(e) && e.repeat === true) { e.preventDefault(); return; }',
    'if (!isPrintChord(e)) return;', 'e.preventDefault();', 'press();'], 'the flow\'s keydown handler');
  assert.equal(onKey.split('press();').length - 1, 1, 'one press in the handler');
  // the palette: Mod+P by default, a capture-phase listener on the shell document and every pane document at each load,
  // preventing and stopping the chord it maps; the shell page the kernel serves loads it
  assert.ok(code(read('ui', 'webview', 'commands.ts')).includes('"palette.toggle": "Mod+P",'), 'the palette\'s default binding');
  const pm = code(read('ui', 'webview', 'palette-main.ts'));
  assert.ok(pm.includes('document.addEventListener("keydown", onKey, true);'), 'the shell document, capture phase');
  assert.ok(pm.includes('if (f.contentDocument) f.contentDocument.addEventListener("keydown", onKey, true);'), 'every pane document');
  assert.ok(pm.includes('f.addEventListener("load", wire);'), 'at each frame\'s load, so ahead of a viewer opened in the pane later');
  assert.ok(between(pm, 'function onKey(e: KeyboardEvent): void {', '\n  }').includes('e.preventDefault(); e.stopPropagation();'), 'the dispatcher prevents and stops the chord it maps');
  const dispatchable = between(code(read('ui', 'webview', 'keybindings.ts')), 'export function dispatchable(', '\n}');
  assert.ok(dispatchable.includes('if (e.repeat) return false;'), 'a key repeat aside');
  assert.ok(dispatchable.includes('if (typing && !e.ctrlKey && !e.altKey && !e.metaKey) return false;') && dispatchable.includes('return true;'), 'a chord with a modifier, whatever holds the keyboard');
  assert.ok(P1.includes('key repeats aside (keybindings.ts, `dispatchable`)'));
  assert.ok(read('kernel', 'kernel.py').includes('<script src=/dist/palette-main.js?v='), 'the shell page the kernel serves loads the dispatcher');
  assert.ok(P1.includes('the shell page loads the command palette\'s dispatcher (palette-main.ts'));
  assert.ok(P1.includes('The fourth condition is the build\'s departure from the contract'), 'recorded as a departure, as the section\'s preamble promises');
  assert.ok(OPEN.includes('4. The chord on the dashboard.'), 'and the alternative is the owner\'s ruling');
  // the driver leg pins the stand-down by execution and the real dispatcher's wiring from its source
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driver.includes('(2) a listener before the flow\'s that already prevented the chord'), 'the driver leg\'s case (2)');
  assert.ok(driver.includes('import { DEFAULT_CHORDS } from "./commands";'), 'the stand-in reads the real binding');
});

test('P1: a held chord\'s repeats are prevented and none is a press', () => {
  assert.ok(P1.includes('The press is the chord\'s first keydown, not a key repeat, since a held chord would arm and disarm on alternate repeats; a held chord\'s later keydowns are prevented too under those conditions'));
  assert.ok(between(flow, 'export function isPrintKeys(e: KeyLike): boolean {', '\n}').includes('return (e.ctrlKey === true || e.metaKey === true) && e.altKey !== true && e.shiftKey !== true && typeof e.key === "string" && e.key.toLowerCase() === "p";'), 'the keys, a repeat or not');
  assert.ok(between(flow, 'export function isPrintChord(e: KeyLike): boolean {', '\n}').includes('return isPrintKeys(e) && e.repeat !== true;'), 'the press: the keys and no repeat');
  assert.ok(onKey.includes('if (isPrintKeys(e) && e.repeat === true) { e.preventDefault(); return; }'), 'a repeat is prevented and nothing more');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('(1) a held Ctrl/Cmd+P: every repeat is prevented while a file is open'), 'the driver leg\'s case (1)');
});

// ── P1: the three Escapes the armed bar leaves alone ───────────────────────────────────────────────

test('P1: while armed a key a listener ahead already stopped, an Escape from a control that owns it, under an open popup in the card, or from a text field is left to that control and the bar stays armed', () => {
  assert.ok(P1.includes('Four Escapes are exceptions, each some control\'s own: the flow leaves it to that control and the bar stays armed for the next Escape.'));
  const escape = between(onKey, 'if (e.key === "Escape") {', 'return;\n    }');
  assert.ok(escape.includes('if (e.cancelBubble) return;'), 'the stopped key first');
  assert.ok(escape.includes('if (!escapable() || ownsEscape(e.target, host.card) || host.typing()) return;'), 'then the phase and the two gates, before the disarm');
  assert.ok(flow.includes('const escapable = (): boolean => state.phase === "armed" || state.phase === "stalled" || (state.phase === "preparing" && state.untimed === true);'), 'the armed line, the deadline\'s ask and the open-ended wait take Escape; the timed wait and the print leave it to the viewer');
  inOrder(escape, ['if (e.cancelBubble) return;', 'ownsEscape(e.target, host.card) || host.typing()) return;', 'e.preventDefault(); e.stopPropagation();', 'feed({ kind: "escape" });'], 'the Escape branch');
  // (0) the stopped key: the flyout's dismiss, a capture-phase document listener wired at the viewer's init, closes the flyout and stops the key
  assert.ok(P1.includes('They are a key a listener ahead of this one already stopped, read through the event\'s stop flag (`e.cancelBubble`'));
  assert.ok(viewer.includes('document.addEventListener("keydown", (e) => { const z = live(); if (e.key === "Escape" && z) { z.close(); e.stopPropagation(); } }, true);'), 'the flyout\'s dismiss closes it and stops the key');
  assert.ok(between(viewer, 'function wireZoomDismiss(): void {', '\n}').includes('document.addEventListener("keydown"'), 'inside wireZoomDismiss');
  assert.ok(viewer.indexOf('wireZoomDismiss();') < viewer.indexOf('export function openFileView('), 'wired at the viewer\'s init, ahead of any per-open listener');
  // (1) the roles: the section names the five and the selector holds them
  assert.ok(flow.includes('export const OWN_ESCAPE_SEL = \'[role="menu"], [role="menubar"], [role="listbox"], [role="dialog"], [role="alertdialog"]\';'));
  assert.ok(P1.includes('(`OWN_ESCAPE_SEL`: role menu, menubar, listbox, dialog or alertdialog; the viewer\'s Outline popover is a role=menu whose Escape closes it and puts the keyboard back on its button'));
  assert.ok(viewer.includes('pop.setAttribute("role", "menu");'), 'the Outline popover is a role=menu');
  assert.ok(viewer.includes('if (e.key === "Escape") { take(); closeOutlineKeeping(false); outlineBtn.focus({ preventScroll: true }); }'), 'whose Escape closes it and puts the keyboard back on its button');
  // (2) an open popup in the card, by its trigger
  assert.ok(flow.includes('export const OPEN_POPUP_SEL = \'[aria-haspopup][aria-expanded="true"]\';'));
  const owns = between(flow, 'export function ownsEscape(target: EventTarget | null, scope?: ParentNode | null): boolean {', '\n}');
  assert.ok(owns.includes('t.closest(OWN_ESCAPE_SEL) !== null) return true;') && owns.includes('scope.querySelector(OPEN_POPUP_SEL) !== null;'), 'the target\'s ancestors, then the scope\'s open popup');
  assert.ok(P1.includes('while a popup stands open in the card, found by its trigger\'s aria-haspopup with aria-expanded true (`OPEN_POPUP_SEL`: a popup whose own handler runs after this listener'));
  assert.ok(P1.includes('the flyout is closed by its dismiss before the flow reads the card, so this selector never finds it open'), 'the flyout is the stop flag\'s, not the selector\'s');
  assert.ok(!P1.includes('(`OPEN_POPUP_SEL`: the text-size flyout'), 'the second review\'s attribution is gone');
  assert.ok(viewer.includes('trigger.setAttribute("aria-haspopup", "true"); trigger.setAttribute("aria-expanded", "false");'), 'the text-size trigger');
  assert.ok(viewer.includes('outlineBtn.setAttribute("aria-haspopup", "menu"); outlineBtn.setAttribute("aria-expanded", "false");'), 'the Outline button');
  assert.ok(!flow.includes('btn.setAttribute("aria-haspopup"'), 'the Print button carries no aria-haspopup, so its own aria-expanded while armed is not matched');
  assert.ok(P1.includes('the Print button\'s own aria-expanded while armed has no aria-haspopup and is not matched'));
  // (3) a text field: the host's typing predicate
  assert.ok(P1.includes('and an Escape from a text field holding the keyboard (`typingHere` again; the Comments composer, whose Escape cancels the draft)'));
  assert.ok(viewer.includes('typing: typingHere,'), 'the viewer hands the flow its typing predicate');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('(7) Escape from inside the Outline popover while the bar is armed closes the popover'), 'the driver leg\'s case (7)');
  assert.ok(read('ui', 'webview', 'file-print-armed-browser.test.ts').includes('(B) Escape while the bar is armed is left to a control that owns it: the text-size flyout'), 'the armed leg\'s case (B): the flyout and the composer');
});

// ── P2: the machine, the wait and the armed line ───────────────────────────────────────────────────

test('P2: the machine\'s phases and events are the record\'s: six phases with disabled and stalled, and the body, recount, stalled, anyway and keep events beside the six', () => {
  assert.ok(flow.includes('export type PrintPhase = "disabled" | "resting" | "armed" | "preparing" | "stalled" | "printing";'));
  assert.ok(P2.includes('a pure function over a state (disabled, resting, armed, preparing, stalled, printing; the first is P7\'s, the fifth the deadline\'s ask) and an event (press, escape, choose, prepare, ready, printed, the host\'s body report, P7\'s `body`, the driver\'s `recount` after a repaint under the armed line, and the ask\'s `stalled`, `anyway` and `keep`)'));
  for (const k of ['press', 'escape', 'choose', 'prepare', 'ready', 'stalled', 'anyway', 'keep', 'printed', 'body', 'recount']) assert.ok(events.includes('{ kind: "' + k + '"'), 'the event ' + k);
  assert.equal([...events.matchAll(/\{ kind: "/g)].length, 11, 'and no other');
});

test('P2: the deadline asks instead of printing, Print anyway prints, Keep waiting is an open-ended wait Escape cancels, and a repaint under the ask counts again', () => {
  assert.ok(P2.includes('after which the bar asks instead of printing (the third review, 2026-09-19): with a picture still loading the flow enters the `stalled` phase and the line reads "1 picture has not loaded." or "N pictures have not loaded." with **Print anyway** and **Keep waiting**'));
  // the words and the titles are the module\'s
  assert.ok(flow.includes('return n === 1 ? "1 picture has not loaded." : n + " pictures have not loaded.";'), 'the ask\'s words');
  assert.ok(flow.includes('export const ANYWAY_WORDS = "Print anyway";') && flow.includes('export const KEEP_WORDS = "Keep waiting";'));
  assert.ok(flow.includes('export const ANYWAY_TITLE = ') && flow.includes('export const KEEP_TITLE = '), 'the titles the section names');
  // the wait: a null deadline sets no timer; the deadline feeds stalled with the count still loading, never ready
  assert.ok(flow.includes('export function settlePictures(pics: Picture[], deadlineMs: number | null, timers: Timers = REAL_TIMERS): Settle {'));
  assert.ok(flow.includes('else if (deadlineMs !== null) timer = timers.setTimeout(() => end("deadline"), deadlineMs);'), 'no timer under a null deadline');
  const aim = between(flow, 'const aimWait = (deadlineMs: number | null): number => {', '\n  };');
  // the wait's verdict is one event, ready, carrying why and the count still loading (the third review's extra6-1 root: the
  // first build fed one bare ready for both ends, and the second wired the ask off a separate stalled event from the resolver)
  assert.ok(events.includes('{ kind: "ready"; why: "settled" | "deadline"; pending: number }'), 'the verdict\'s datum, in the type');
  assert.ok(aim.includes('if (why === "deadline") { feed({ kind: "ready", why, pending: s.pending() }); return; }'), 'the deadline feeds ready with why and the count');
  assert.ok(!aim.includes('feed({ kind: "stalled"'), 'the resolver feeds no stalled: that event is the driver\'s, after a repaint under the ask');
  assert.ok(!aim.includes('feed({ kind: "ready" });'), 'and no bare ready');
  inOrder(aim, ['if (why === "deadline") { feed({ kind: "ready", why, pending: s.pending() }); return; }', 'const left = timeLeft();', 'if (left === null || left > 0) {', 'feed({ kind: "ready", why: "settled", pending: 0 });'], 'the settle handler');
  assert.ok(flow.includes('if (ev.kind === "ready") return ev.why === "deadline" && ev.pending > 0 ? ask(ev.pending) : { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };'), 'the machine: a deadline with a count asks, a settle or a deadline with none prints');
  assert.ok(P2.includes('The wait\'s verdict reaches the machine as one event, `ready`, carrying `why` (`settled`, or `deadline`) and the count still loading: a settle prints, a deadline with a count asks, and a deadline that finds none loading is a settle in effect and prints'));
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('the wait\'s verdict carries why and the count still loading'), 'the node test of the three verdicts');
  assert.ok(flow.includes('const timeLeft = (): number | null => (state.phase === "preparing" && state.untimed === true ? null : Math.max(0, waitEnds - Date.now()));'), 'the open-ended wait has no deadline');
  // the machine: the ask over a count, the print over none; the two answers; Escape in the open-ended wait alone
  assert.ok(flow.includes('pending > 0 ? { state: { phase: "stalled", gated: 0, pending }, act: "stall" } : { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };'), 'the ask, or the print over none');
  assert.equal(flow.split('if (ev.kind === "stalled") return ask(ev.pending);').length - 1, 1, 'stalled is read under the ask alone (the repaint\'s recount); the deadline arrives as ready');
  assert.ok(flow.includes('if (ev.kind === "escape" && s.untimed === true) return { state: RESTING, act: "disarm" };'), 'Escape cancels the open-ended wait alone');
  const stalled = between(flow, 'case "stalled":', 'break;');
  inOrder(stalled, ['if (ev.kind === "press" || ev.kind === "escape") return { state: RESTING, act: "disarm" };', 'if (ev.kind === "anyway") return { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };', 'if (ev.kind === "keep") return { state: s, act: "resume" };', 'if (ev.kind === "prepare") return begin(ev.pending, true);'], 'the stalled phase');
  assert.ok(flow.includes('case "resume": feed({ kind: "prepare", pending: aimWait(null) }); return;'), 'Keep waiting aims an open-ended wait at the body as it stands');
  assert.ok(P2.includes('"Keep waiting" waits on the load and error events alone, with no timer (`settlePictures` under a null deadline; the state carries `untimed`), until every pending picture settles, then prints; Escape cancels that open-ended wait, where the timed wait\'s Escape stays the viewer\'s, which closes the card.'));
  assert.ok(P2.includes('Nothing listens under the ask: "Keep waiting" reads the body as it stands then, so a picture that landed meanwhile is not waited on again, and with none left loading the print runs at once.'));
  // the driver: the ask in the armed line\'s shape, rewritten in place under a repaint; the recount under the ask
  const stall = between(flow, 'case "stall": {', '\n      }');
  inOrder(stall, ['const words = stalledWords(state.pending);', 'if (line && asked) { line.firstChild!.textContent = words; break; }', 'const row = showLine(words);', 'b.className = "fileview-btn fileview-err-act";', 'asked = true;'], 'the ask\'s line');
  assert.ok(flow.includes('const recountAsk = (): void => { const n = aimWait(null); dropSettle(); feed({ kind: "stalled", pending: n }); };'), 'a repaint under the ask: counted through the wait\'s collection, the listeners off again');
  assert.ok(P2.includes('A repaint under the ask counts the new body\'s pictures still loading again (`recountAsk`, through the wait\'s own collection, the listeners taken off again): the line\'s count follows in place, and none loading prints, as a re-aim does.'));
  assert.ok(flow.includes('const asks = state.phase === "armed" || state.phase === "stalled";') && flow.includes('btn.classList.toggle("on", asks);'), 'the button\'s dress under the ask is the armed one');
  assert.ok(P2.includes('`.on` and aria-expanded while armed and under the ask'));
  // the legs
  assert.ok(read('ui', 'webview', 'file-print-browser.test.ts').includes('(4) the deadline asks: a picture whose route never answers brings'), 'the gated leg\'s case 4');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('at the deadline the bar asks, with the parked picture'), 'the driver leg\'s case (5)');
  assert.ok(TESTS.includes('the deadline\'s ask over a picture whose route never answers'));
});

test('P2: the wait is re-aimed at a repaint and at each settle under the press\'s deadline, each bound held by its own executed case, and the armed line is recounted at a repaint', () => {
  assert.ok(P2.includes('The wait is aimed at the body as it stands and re-aimed in two cases'));
  assert.ok(P2.includes('Both re-aims run under the deadline the press set, never past it'));
  assert.ok(flow.includes('const n = aimWait(timeLeft());') && flow.includes('Math.max(0, waitEnds - Date.now())'), 'a re-aim reads the time left (or none for Keep waiting\'s wait)');
  assert.ok(flow.includes('const more = aimWait(left);'), 'the settle reads the body again under the time left');
  // each bound is a claim about time, so each is held by its own executed case of the driver leg and the record names both:
  // case (3c) the repaint's re-aim, case (12) the settle's. The second review's census of the deadline's writers in the source
  // is gone (the third review's tests-2: a repaint re-aim restarting the full deadline left every leg green, so a grep was no
  // pin), and the third review's one case pinned the repaint's re-aim alone (the fourth review: a settle re-aim restarting the
  // full deadline left every leg green, case (3c) included)
  assert.ok(P2.includes('each re-aim\'s bound is executed by its own case of file-print-driver-browser.test.ts'));
  assert.ok(!P2.includes('the bound is executed by file-print-driver-browser.test.ts case (3c)'), 'the one-case wording is gone');
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  // the repaint's re-aim: case (3c)
  assert.ok(P2.includes('The repaint\'s bound is case (3c):'));
  assert.ok(driver.includes('the re-aim runs under the press\'s deadline, never a restarted one: with the landing\'s picture parked too the ask comes at the press\'s deadline'), 'the driver leg\'s case (3), sub-case c, in its title');
  const c3 = between(driver, 'test("(3) a Reload landing during the wait re-aims it', '\n});');
  inOrder(c3, ['await reloadTo(page, SLOW2_NOTE);', 'assert.ok(t2 - t0 >= 1900 && t2 - t0 < 3000,', 'assert.ok(t2 - tLand < 1600,'], 'sub-case c: the landing, then the two bounds the record states');
  assert.ok(P2.includes('the ask is asserted between 1900 and 3000 ms after the press and under 1600 ms after the landing'));
  // the settle's re-aim: case (12), an insertion the body's observer does not see, then the release that settles the wait
  assert.ok(P2.includes('The settle\'s bound is case (12):'));
  assert.ok(driver.includes('(12) the settle\'s re-aim runs under the press\'s deadline, never a restarted one: a second parked picture inserted inside the rendered root mid-wait'), 'the driver leg\'s case (12), in its title');
  const c12 = between(driver, 'test("(12) the settle\'s re-aim runs under the press\'s deadline', '\n});');
  inOrder(c12, ['md.appendChild(img);', 'assert.equal(ins.grandchild, true,', 'assert.equal(b.line, "Preparing 1 picture…", "the observer was silent', 'await s.release([SLOW]);', 'const tSettle = await nowOnPage(page);', 'assert.equal((await prints(page)).length, 0, "no print at the settle', 'assert.ok(t2 - t0 >= 1900 && t2 - t0 < 3000,', 'assert.ok(t2 - tSettle < 1600,'], 'case (12): the insertion inside the root, the silent observer, the release, no print at the settle, then the two bounds the record states');
  assert.ok(P2.includes('the ask is asserted between 1900 and 3000 ms after the press and under 1600 ms after the release'));
  assert.ok(flow.includes('observer.observe(host.body, { childList: true });'), 'the observer reads the body\'s children alone, which is why the insertion inside the root is silent');
  assert.ok(TESTS.includes('and the settle\'s re-aim under the press\'s deadline (a second parked picture inserted inside the rendered root mid-wait'), 'the Tests list names case (12)');
  // the wait's line is rewritten in place at a re-aim
  assert.ok(flow.includes('const preparingLine = (n: number): void => {') && flow.includes('if (line && line.querySelector(".fileview-print-load")) { line.firstChild!.textContent = preparingWords(n); return; }'), 'the standing wait line\'s words change in place');
  assert.ok(flow.includes('if (more > 0) { preparingLine(more); return; }') && between(flow, 'const reaim = (): void => {', '\n  };').includes('preparingLine(n);'), 'both re-aims go through it');
  assert.ok(P2.includes('rewritten in place when the wait\'s line stands (`preparingLine`'));
  // the repaint reaches the driver through its observer of the body (P7), not a report
  const onBody = between(flow, 'const onBody = (): void => {', '\n  };');
  inOrder(onBody, ['const present = ready();', 'feed({ kind: "body", in: present });', 'if (!present) return;', 'if (state.phase === "armed") feed({ kind: "recount", gated: gates().length });', 'else if (state.phase === "preparing") reaim();', 'else if (state.phase === "stalled") recountAsk();'], 'the body\'s change: the machine, then the phase\'s re-read');
  assert.ok(P2.includes('when P7\'s observer sees a repaint under it'));
  assert.ok(P2.includes('has its placeholders counted again (the driver\'s `recount`): over placeholders the line stands with the new count and the title with the new hosts, rewritten in place, the keyboard where it was; over none the line goes, since the question it asked is moot, and the next press prints'));
  assert.ok(flow.includes('if (ev.kind === "recount") return ev.gated > 0 ? { state: { phase: "armed", gated: ev.gated, pending: 0 }, act: "arm" } : { state: RESTING, act: "disarm" };'), 'the machine: arm again over a count, disarm over none');
  assert.ok(flow.includes('if (line && withBtn) { line.firstChild!.textContent = words; withBtn.title = withWords; break; }'), 'the driver rewrites the standing line in place');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('(3) a repaint during the wait'), 'the driver leg\'s case (3)');
  assert.ok(read('ui', 'webview', 'file-print-armed-browser.test.ts').includes('(A) a body repainted under the armed line'), 'the armed leg\'s case (A): the recount');
});

test('P2: a placeholder the person activates by hand under the armed line is counted again, heard on the card after the body\'s gate handler', () => {
  assert.ok(P2.includes('A placeholder the person activates by hand under the armed line (its click, or Enter or Space on it: the viewer\'s own gate handlers on the body, `loadGate` and `gateKeys`) is counted again the same way: the driver hears the activation on the card in the bubble phase (`onGateAct`), after the body\'s handler restored the picture'));
  const act = between(flow, 'const onGateAct = (e: Event): void => {', '\n  };');
  inOrder(act, ['if (state.phase !== "armed") return;', 'if (k !== "Enter" && k !== " ") return;', 't.closest(\'[data-act="\' + GATE_ACT + \'"]\') === null) return;', 'feed({ kind: "recount", gated: gates().length });'], 'the card\'s listener: armed, the key, the placeholder, the recount');
  assert.ok(flow.includes('host.card.addEventListener("click", onGateAct);') && flow.includes('host.card.addEventListener("keydown", onGateAct);'), 'on the card, bubble phase');
  assert.ok(!flow.includes('doc.addEventListener("click"'), 'not on the document');
  // the viewer's gate handlers stand on the body, the card's descendant, so they run first whatever the registration order
  assert.ok(viewer.includes('function loadGate(g: HTMLElement): void { loadGatedHost(g.dataset.fvHost || "", document); }'));
  assert.ok(between(viewer, 'function gateKeys(body: HTMLElement): void {', '\n}').includes('body.addEventListener("keydown", (ev) => {'), 'the keys on the body');
  assert.ok(/body\.addEventListener\("click", \(ev\) => \{\n\s+const t = ev\.target as Element \| null;\n\s+const g = gateOf\(t, body\);/.test(viewer), 'the local viewer\'s click on the body');
  assert.ok(viewer.includes('delegate(body, {'), 'the URL viewer\'s delegate on the body');
  assert.ok(read('ui', 'webview', 'file-print-armed-browser.test.ts').includes('(A) a placeholder the person activates by hand under the armed line is counted again'), 'the armed leg\'s case');
});

test('P2: only a placeholder that reaches the paper is counted, named and loaded, a fold toggled under the armed line is counted again, and the gate loads by host for the rest of the page', () => {
  assert.ok(P2.includes('Only a placeholder that reaches the paper is counted, named and loaded (`printable`, the third review, 2026-09-19): one inside a closed `<details>`, a typed one or a folded callout (`> [!type]-`, md-config.ts), outside that details\' own summary, or under a `hidden` attribute whatever its value, is left out of the count, of the title and of the hosts "with them" loads'));
  // the predicate: the ancestor walk, hidden on any node, a closed details holding the node outside its summary
  const pred = between(flow, 'export function printable(el: PrintableNode): boolean {', '\n}');
  assert.ok(pred.includes('if (n.hasAttribute("hidden")) return false;'), 'hidden, whatever its value');
  assert.ok(pred.includes('if (p && p.localName === "details" && n.localName !== "summary" && !p.hasAttribute("open")) return false;'), 'a closed details, its summary excepted');
  assert.ok(pred.includes('for (let n: PrintableNode | null = el; n; n = n.parentElement) {'), 'walked to the root');
  // the driver reads the body\'s placeholders through it, and every count, title and load goes through gates()
  assert.ok(flow.includes('const gates = (): HTMLElement[] => (Array.from(host.body.querySelectorAll(\'[data-act="\' + GATE_ACT + \'"]\')) as HTMLElement[]).filter(printable);'), 'the placeholders the flow reads are the printable ones');
  assert.equal([...flow.matchAll(/querySelectorAll\('\[data-act="' \+ GATE_ACT/g)].length, 1, 'one read of the body\'s placeholders, so no count, title or load bypasses the filter');
  assert.ok(flow.includes('for (const g of gates()) for (const h of (g.getAttribute("data-fv-hosts") || "").split(" ")) if (h) hosts.add(h);'), 'the hosts come from those placeholders');
  // the sanitizer keeps details and hidden (both shapes come from the author) and strips an inline display: none
  const sanitize = code(read('ui', 'webview', 'md-sanitize.ts'));
  assert.ok(sanitize.includes('export const MD_FORBID_ATTR: readonly string[] = ["background", "usemap"];'), 'hidden is not forbidden');
  assert.ok(!between(sanitize, 'export const MD_FORBID_TAGS: readonly string[] = [', '];').includes('"details"'), 'details is not forbidden');
  assert.ok(sanitize.includes('const KEPT_PROPERTIES = new Set(["color", "background-color"]);'), 'a style keeps colour declarations alone: display: none goes');
  assert.ok(P2.includes('a picture under an inline `display: none` is printable, since the sanitizer strips that style (md-sanitize.ts `colorOnlyStyle` keeps colour declarations alone) and the picture prints'));
  // a fold toggled under the armed line: the details\' toggle event, capture phase on the card, a recount while armed
  assert.ok(P2.includes('A fold the person opens or closes under the armed line is counted again (the details\' `toggle` event, which does not bubble, heard on the card in the capture phase), as a repaint is.'));
  assert.ok(flow.includes('const onToggle = (): void => { if (state.phase === "armed") feed({ kind: "recount", gated: gates().length }); };'), 'the toggle recounts while armed');
  assert.ok(flow.includes('host.card.addEventListener("toggle", onToggle, true);'), 'on the card, capture phase');
  // the gate loads by host and for the page: the document\'s loaded set, read into the allowed set at every gating
  const gate = code(read('ui', 'webview', 'figure-gate.ts'));
  const load = between(gate, 'export function loadGatedHost(host: string, doc: ParentNode = document): void {', '\n}');
  assert.ok(load.includes('loadedHosts.add(host.toLowerCase());') && load.includes('regateFigures(doc);'), 'the host joins the loaded set and every placeholder waiting on it is re-judged');
  assert.ok(between(gate, 'export function regateFigures(doc: ParentNode): void {', '\n}').includes('if (!hosts.length) restore(wrap);'), 'a placeholder whose hosts are all loaded is restored, printable or not');
  assert.ok(between(gate, 'export function allowedFigureHosts(extra: Iterable<string> = []): Set<string> {', '\n}').includes('for (const h of loadedHosts) s.add(h);'), 'the loaded hosts are allowed for the rest of the document');
  assert.ok(P2.includes('The gate loads by host: `loadGatedHost` adds the host to the document\'s `loadedHosts` and `regateFigures` restores every placeholder waiting on it, so a host one printable placeholder and one folded placeholder share is restored in both by the one load, while a host only folded or hidden placeholders name is never loaded by a print.'));
  assert.ok(P2.includes('a host "with them" loads is granted for the rest of the page exactly as a click on the placeholder grants it: `loadedHosts` is per document'));
  // P6 carries the clause, and the armed leg executes the five-host case
  assert.ok(part('P6. **', 'P7. **').includes('and only for a placeholder that reaches the paper (P2\'s printable rule): a host only a folded or hidden placeholder names is not asked'));
  assert.ok(read('ui', 'webview', 'file-print-armed-browser.test.ts').includes('(C) only a placeholder that reaches the paper is counted, named and loaded'), 'the armed leg\'s case (C)');
  assert.ok(OPEN.includes('6. The wait and the pictures that never reach the paper.'), 'the wait\'s reading of every picture is the owner\'s ruling');
});

test('P2: the wait\'s line carries the viewer\'s loader after its words, under one rule byte-equal in both sheets and pinned by the parity test', () => {
  assert.ok(P2.includes('Beside the words the line carries the viewer\'s loader, the swirl, the wordmark and the three pulsing dots (`.fileview-load`, the markup file-view.ts\'s waits use, hidden from the status\'s announcement), inline on the words\' row under a rule of its own in both sheets, `.fileview-print-line .fileview-load`'));
  const show = between(flow, 'const showLine = (words: string, loading = false): HTMLElement => {', '\n  };');
  inOrder(show, ['row.textContent = words;', 'if (loading) {', 'load.className = "fileview-load fileview-print-load";', 'load.setAttribute("aria-hidden", "true");', '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>', '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>', 'row.appendChild(load);'], 'the words first, then the loader');
  assert.equal([...flow.matchAll(/showLine\(preparingWords\([^)]*\), true\)/g)].length, 2, 'every fresh preparing line loads: the wait act, and preparingLine\'s line when none stands (the re-aim and the settle\'s second look rewrite a standing one in place)');
  assert.equal([...flow.matchAll(/showLine\(preparingWords\(/g)].length, 2, 'and no preparing line without the loader');
  const RULE = '.fileview-print-line .fileview-load { display: inline-flex; padding: 0; margin-left: 10px; font-size: 1em; vertical-align: middle; }';
  for (const sheet of ['styles.css', 'feed.css']) {
    const css = read('ui', 'webview', sheet);
    assert.equal(css.split('\n' + RULE + '\n').length - 1, 1, sheet + ': the rule, once, on its own line');
    assert.ok(css.includes('.fileview-load { display: flex; align-items: center; justify-content: center; gap: 7px;\n  padding: 30px 0; color: var(--dim); font-size: 0.86em; }'), sheet + ': the loader\'s own rule the line\'s rule undoes (the padding, the size under .fileview-err\'s 0.86em)');
  }
  assert.ok(read('ui', 'webview', 'fileview-parity.test.ts').includes('".fileview-print-line .fileview-load {",'), 'the parity pin holds the rule byte-equal');
  assert.ok(read('ui', 'webview', 'file-print-browser.test.ts').includes('const loaderFacts = (page: any): Promise<Loader> => page.evaluate(() => {'), 'the gated leg reads the loader in Chromium');
});

test('P4: the window between the frame\'s insertion and its document is recorded, and the body is reported in at the media paint, before the frame loads', () => {
  const P4 = part('P4. **', 'P5. **');
  assert.ok(P4.includes('The frame being in is not the frame holding the document: the body reads as in (P7) once the media paint puts the frame\'s column in it'));
  assert.ok(P4.includes('The button is not held to the frame\'s load event, since a browser that downloads the PDF instead never fires it'));
  // the media paint puts pdfBlock's column in the body, and the flow reads that column as content (bodyReady counts any child
  // that is not a loader, the fallback textarea or a failure line); no paint reports anything
  assert.ok(viewer.includes('const shown = isPdf ? pdfBlock(objUrl, path) : imgBlock(objUrl, path, imgFailed);') && viewer.includes('body.replaceChildren(shown);'), 'the media paint');
  const pdfBlock = between(viewer, 'function pdfBlock(objUrl: string, path: string): HTMLElement {', '\n}');
  assert.ok(pdfBlock.includes('const col = el("div", "fileview-pdffall");') && pdfBlock.includes('col.appendChild(frame);') && pdfBlock.includes('return col;'), 'the frame comes in its column');
  assert.equal(viewer.split('print.bodyIn(').length - 1, 0, 'the viewer reports nothing');
  assert.ok(P4.includes('while the pages flow\'s loader alone holds the body, before page 1 is drawn, Print is disabled (P7), and over a kept frame under the attempt\'s loader it stays live'));
  assert.ok(read('ui', 'webview', 'file-view-print-takings-browser.test.ts').includes('case 5: the Comments panel\'s PDF pages flow.'), 'the takings leg\'s case 5 drives the pages flow');
  assert.ok(!viewer.includes('frame.addEventListener("load"') || !between(viewer, 'frame.addEventListener("load"', '\n').includes('bodyIn'), 'no report waits on the frame\'s load');
  assert.ok(read('ui', 'webview', 'file-print-media-browser.test.ts').includes('one tab opened, inside the click\'s own task'), 'the media leg\'s in-task assertion the section cites');
});

test('P2: the word buttons\' titles are the module\'s, the hosts are read at the arm and kept for the click, and a line button holding the keyboard hands it to the Print button', () => {
  const withTitle = between(flow, 'export function withTitle(hosts: string[]): string {', '\n}');
  assert.ok(withTitle.includes('hosts.slice(0, -1).join(", ") + " and " + hosts[hosts.length - 1]'), 'the hosts in order, the last after "and"');
  assert.ok(withTitle.includes('return "Load the pictures from " + list + ", then print";'));
  assert.ok(withTitle.includes('hosts.length === 0 ? "those hosts"'));
  assert.ok(P2.includes('(`withTitle`; "Load the pictures from a.test and b.test, then print" over two hosts, "those hosts" with none known)'), 'the section\'s example is the function\'s output over two hosts');
  assert.ok(flow.includes('export const WITHOUT_TITLE = "Print with their placeholders as they are";'));
  assert.ok(P2.includes('"Print without them"\'s is `WITHOUT_TITLE`, "Print with their placeholders as they are"'));
  assert.ok(flow.includes('b.title = withGated ? withWords : WITHOUT_TITLE;'), 'each button wears its title');
  // the hosts: one list for the title and the loads
  assert.ok(P2.includes('The hosts are read at the arm and kept (`armedHosts`): "with them" loads that list and no other, so the title and the loads are one list by construction'));
  assert.ok(flow.includes('armedHosts = gatedHosts();') && flow.includes('withTitle(armedHosts)'), 'read at the arm, named in the title');
  const activate = between(flow, 'case "activate": {', 'return;');
  assert.ok(activate.includes('const hosts = armedHosts;') && activate.includes('for (const h of hosts) loadGatedHost(h, doc);'), 'and loaded from that list, not the body at the click');
  assert.ok(!activate.includes('gatedHosts()'), 'the click reads no hosts of its own');
  // the focus hand-back
  assert.ok(P2.includes('A word button of the line that holds the keyboard when the line goes hands it to the Print button, the trigger'));
  const drop = between(flow, 'const dropLine = (bodyOut = false): void => {', '\n  };');
  assert.ok(drop.includes('const held = !closed && line.contains(doc.activeElement);'), 'who held it, read before the removal and not at the close');
  assert.ok(drop.includes('if (held) { if (bodyOut && host.takeKeyboard) host.takeKeyboard(); else btn.focus({ preventScroll: true }); }'), 'the hand-back to the button, or through the host when the body went out');
  assert.ok(flow.includes('case "disarm": dropSettle(); dropLine(ev.kind === "body"); break;'), 'the disarm names the body-out case');
  assert.ok(flow.includes('takeKeyboard?: () => void;'), 'the host hook, optional');
  assert.ok(viewer.includes('kind: () => (isPdf ? "pdf" : "document"), openTab: () => openFileTab(path, sid), takeKeyboard: () => takeKeyboard() });'), 'the local viewer passes its own hand-over');
  assert.equal(viewer.split('takeKeyboard: () => takeKeyboard()').length - 1, 1, 'the URL viewer passes none: its button takes the keyboard');
  assert.ok(between(viewer, 'const dropDiskBar = (): void => {', '\n  };').includes('if (held) takeKeyboard(ring);'), 'the changed-on-disk bar\'s own hand-over, the precedent');
  assert.ok(P2.includes('When the disarm is the body going out (P7) the button is not enabled, so the keyboard goes to the viewer\'s body through the host\'s `takeKeyboard`, the changed-on-disk bar\'s own hand-over (`dropDiskBar`)'));
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('(8) Escape or Enter on the armed line\'s word buttons hands the keyboard to the Print button'), 'the driver leg\'s case (8)');
  assert.ok(read('ui', 'webview', 'file-view-print-takings-browser.test.ts').includes('assert.equal(b.active, "DIV.fileview-body", "FAILS BEFORE: the keyboard went to the viewer\'s body through its own hand-over'), 'the takings leg\'s case 1 reads the keyboard on the viewer\'s body');
});

// ── P5: the guide's palette clause ─────────────────────────────────────────────────────────────────

test('P5: the guide says the key opens the palette instead in the dashboard, and the section says the guide says so', () => {
  const label = '**Opening a markdown document.**';
  const at = guide.indexOf(label);
  assert.ok(at >= 0, 'the paragraph the section names');
  const para = guide.slice(at, guide.indexOf('\n\n', at)).replace(/\s+/g, ' ');
  assert.ok(para.includes('in the dashboard that key opens the command palette instead (**Escape** closes it), so print from the bar there.'), 'the guide\'s clause');
  assert.ok(!para.includes('also opens the command palette'), 'not the round 1 wording, which read as a print too');
  assert.ok(P5.includes('that in the dashboard the key opens the command palette instead, which Escape closes, so one prints from the bar there'));
  assert.ok(P5.includes('tests/test_guide_print_palette_chord.py pins the clause') && exists('tests', 'test_guide_print_palette_chord.py'));
});

// ── the Tests list and the open points ─────────────────────────────────────────────────────────────

const NUMBER_WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };

test('Tests: the count the section gives for `ls ui/webview/file-print*.test.ts` is the listing\'s today, the takings leg outside that listing is named, and the modules the rounds added are named and exist', () => {
  const onDisk = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /^file-print.*\.test\.ts$/.test(f)).sort();
  const count = /`ls ui\/webview\/file-print\*\.test\.ts` lists the follow-on's (\w+) modules/.exec(TESTS);
  assert.ok(count, 'the section names the command and counts what it lists');
  assert.equal(NUMBER_WORDS[count[1]] ?? Number(count[1]), onDisk.length, 'the section says ' + count[1] + '; the listing produces ' + onDisk.length + ': ' + onDisk.join(', '));
  for (const f of onDisk) assert.ok(TESTS.includes('ui/webview/' + f), f + ' is named in the Tests list');
  const takings = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /^file-view-print-takings.*\.test\.ts$/.test(f));
  assert.ok(takings.length >= 1, 'the takings leg is on disk');
  for (const f of takings) assert.ok(TESTS.includes('ui/webview/' + f), f + ' is named in the Tests list, outside the file-print* listing');
  assert.ok(TESTS.includes('One module of the follow-on, ui/webview/file-view-print-takings-browser.test.ts, is outside that listing'));
  assert.ok(TESTS.includes('- ui/webview/file-print-armed-browser.test.ts, under node first') && exists('ui', 'webview', 'file-print-armed-browser.test.ts'), 'the second review\'s leg is named');
  assert.ok(TESTS.includes('- ui/webview/file-print-driver-browser.test.ts, headless Chromium over the real viewer') && exists('ui', 'webview', 'file-print-driver-browser.test.ts'));
  assert.ok(TESTS.includes('- ui/webview/file-print-egress-browser.test.ts, headless Chromium over the real viewer under a request intercept'), 'the third review\'s egress leg is named (the listing test above requires it on disk)');
  assert.ok(TESTS.includes('- tests/test_guide_print_palette_chord.py, Python:'));
  assert.ok(TESTS.includes(path.basename(fileURLToPath(import.meta.url)) + ' holds the review rounds\' sentences here to the tree'), 'the section names this pin');
});

test('Open point 1 records the two-host placeholder\'s wording, and open point 5 the re-place Escape\'s order: the panel\'s listener is registered at the viewer\'s open, ahead of the flow\'s, and the flow stands down on the stopped key', () => {
  assert.ok(OPEN.includes('1. Wording. A gated clip counts as a picture in the armed line, and one placeholder naming two hosts'));
  assert.ok(flow.includes('return n === 1 ? "1 picture from another host is not loaded." : n + " pictures from other hosts are not loaded.";'), 'the words count pictures');
  assert.ok(OPEN.includes('5. Escape with a re-place pending in the Comments panel while the bar is armed.'));
  assert.ok(OPEN.includes('a capture-phase document listener the panel\'s constructor registers when the viewer\'s action walk mounts the panel at the open, ahead of the flow\'s per-open listener, which installFilePrint registers after that walk'));
  assert.ok(!OPEN.includes('wired when the panel opens, so after the flow\'s'), 'the first record\'s order, false, is gone');
  const fc = code(read('ui', 'webview', 'file-comments.ts'));
  const reg = 'document.addEventListener("keydown", this.escapeReplace, true);';
  const ctor = fc.indexOf('constructor(readonly ctx: FileViewActionCtx, readonly button: HTMLButtonElement, readonly unit: HTMLElement) {');
  assert.ok(ctor >= 0, 'the panel\'s constructor');
  const ctorEnd = fc.indexOf('\n  }\n', ctor);
  const regAt = fc.indexOf(reg);
  assert.ok(regAt > ctor && regAt < ctorEnd, 'the listener is registered in the constructor, capture phase on the document');
  assert.ok(fc.includes('new Panel(ctx, b, unit).probe();'), 'which the action\'s mount runs');
  const openFileView = between(viewer, 'export function openFileView(', '\nexport function openUrlView(');
  const walk = openFileView.indexOf('for (const a of fileViewActions) {');
  const install = openFileView.indexOf('const print = installFilePrint({');
  assert.ok(walk >= 0 && install > walk, 'the viewer mounts the registered actions before it installs the print flow, so the panel\'s listener is ahead of the flow\'s on the same document in the same phase');
  const esc = between(fc, 'escapeReplace = (ev: KeyboardEvent) => {', '\n  };');
  assert.ok(esc.includes('ev.preventDefault(); ev.stopPropagation();') && esc.includes('this.closeComposer();'), 'cancels the re-place and stops the key');
  assert.ok(between(onKey, 'if (e.key === "Escape") {', 'return;\n    }').startsWith('if (e.key === "Escape") {\n      if (e.cancelBubble) return;'), 'the flow reads the stopped key first and stands down: one Escape cancels the re-place alone and the bar stays armed');
  assert.ok(OPEN.includes('so one Escape cancels the re-place alone and the bar stays armed for the next Escape, which disarms'));
});

test('P2: the probes are one per URL for a press\'s wait, cleared where the wait begins and never per re-aim, and a lazy picture is set eager as it is collected', () => {
  assert.ok(flow.includes('const probes = new Map<string, Picture>();'), 'the press\'s probes, by resolved URL');
  const probe = between(flow, 'const probe = (url: string): Picture => {', '\n  };');
  assert.ok(probe.includes('let p = probes.get(url);') && probe.includes('if (!p) { const im = new Image(); im.src = url; p = im; probes.set(url, p); }'), 'a URL already probed is not minted again');
  assert.equal(flow.split('new Image()').length - 1, 1, 'one minting site, inside the factory');
  assert.ok(flow.includes('const beginWait = (): number => { probes.clear(); waitEnds = Date.now() + settleMs; return aimWait(settleMs); };'), 'cleared where a press or a choice begins its wait, with the deadline');
  assert.equal(flow.split('probes.clear()').length - 1, 1, 'and nowhere else: a re-aim keeps them');
  assert.ok(flow.includes('settlePictures(collectPictures(host.body, doc.baseURI, probe), deadlineMs)'), 'the collection takes the factory');
  assert.ok(flow.includes('export function collectPictures(body: ParentNode, base: string, probe: (url: string) => Picture): Picture[] {'));
  assert.ok(P2.includes('The probes are one per resolved URL for the life of one press\'s wait (`probes`, a Map in the driver keyed by the resolved URL, filled by the driver\'s `probe` factory, which `collectPictures` takes, and cleared in `beginWait`, at a press or a choice, never per re-aim)'));
  assert.ok(P2.includes('the review measured one press asking the host 337 times over 8 s for one URL whose route answers 404'));
  // the lazy picture
  assert.ok(flow.includes('if (img.loading === "lazy") img.loading = "eager";'), 'set eager as it is collected');
  assert.ok(P2.includes('so `collectPictures` sets it eager before pushing it and the deferred fetch starts at once, for the same URL, and the attribute stays eager after the print'));
  // the legs
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driver.includes('(10) a <video poster> and an svg <image href> whose routes answer 404'), 'the driver leg\'s case (10)');
  assert.ok(driver.includes('assert.equal(asked.poster, 1,') && driver.includes('assert.equal(asked.image, 1,'), 'one request per URL, asserted');
  assert.ok(driver.includes('(11) an <img loading="lazy"> far below the fold (the third review\'s fresh-2)'), 'the driver leg\'s case (11)');
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('collectPictures sets a lazy img eager before the wait listens on it'), 'the node test');
  assert.ok(TESTS.includes('a <video poster> and an svg <image href> whose routes answer 404 (one request per URL after the press'));
});

test('P7: the body\'s readiness is derived by the flow from the body\'s children, the viewers report nothing, and the button wears aria-disabled and never the property, the bar\'s own rule', () => {
  const ready = between(flow, 'export function bodyReady(body: BodyLike): boolean {', '\n}');
  inOrder(ready, ['if (c.classList.contains("fileview-load")) return false;', 'if (c.localName === "textarea" && c.classList.contains("fileview-editor")) return false;', 'if (!c.classList.contains("fileview-err")) content = true;', 'return content;'], 'the loader, the fallback editor, a failure line alone');
  assert.ok(flow.includes('const ready = (): boolean => bodyReady(host.body);'), 'the driver reads its host\'s body through it');
  assert.ok(flow.includes('const observer = new MutationObserver(onBody);') && flow.includes('observer.observe(host.body, { childList: true });'), 'after every paint, through an observer of the body\'s children');
  assert.ok(flow.includes('if (ready() !== (state.phase !== "disabled")) onBody();'), 'and at each press, first');
  assert.ok(flow.includes('observer.disconnect();'), 'dropped at the close');
  assert.ok(flow.includes('return { button: btn };'), 'the installer hands the host the button alone: no report');
  assert.ok(!flow.includes('bodyIn'), 'the report is gone from the flow');
  assert.equal(viewer.split('print.bodyIn(').length - 1, 0, 'and from the viewer: no paint reports');
  const P7 = part('P7. **', '**Tests.**');
  assert.ok(P7.includes('Whether the body is in is DERIVED, read off the body\'s element children by the flow itself (`bodyReady`, exported: a MutationObserver on the body\'s child list feeds the machine\'s `body` event after every paint, and a press reads the body again first'));
  assert.ok(P7.includes('Not in: while a `.fileview-load` is a child of the body') && P7.includes('while `textarea.fileview-editor` is a child') && P7.includes('or while `.fileview-err` is all the body holds'));
  assert.ok(!P7.includes('The host reports the body through the installer\'s `bodyIn`'), 'the reported design is gone from the record');
  // aria-disabled and never the property: the bar's precedent, textSizeControl's atEnd, whose reason the flow's own comment carries
  const sync = between(flow, 'const syncButton = (): void => {', '\n  };');
  assert.ok(sync.includes('if (off) btn.setAttribute("aria-disabled", "true"); else btn.removeAttribute("aria-disabled");'), 'aria-disabled follows the disabled phase');
  assert.ok(!flow.includes('btn.disabled'), 'the property is never set');
  assert.ok(viewer.includes('const atEnd = (b: HTMLButtonElement, end: boolean) => { if (end) b.setAttribute("aria-disabled", "true"); else b.removeAttribute("aria-disabled"); };'), 'the bar\'s precedent');
  assert.ok(read('ui', 'webview', 'file-view.ts').includes('aria-disabled, not `disabled`: a button that disables under keyboard focus drops it'), 'the precedent\'s stated reason (the source with its comments, since the reason is a comment)');
  assert.ok(P7.includes('and never the `disabled` property: the bar\'s own rule, `textSizeControl`\'s, copied whole with its reason'));
  // the legs
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('bodyReady reads the body\'s children'), 'the node shapes');
  const takings = read('ui', 'webview', 'file-view-print-takings-browser.test.ts');
  assert.ok(takings.includes('case 2: Edit while armed') && takings.includes('the plain fallback takes the body and the button stays DISABLED'), 'the fallback editor road');
  assert.ok(takings.includes('case 5: the Comments panel\'s PDF pages flow.'), 'the pages flow road');
  assert.ok(read('ui', 'webview', 'file-print-browser.test.ts').includes('Print is disabled over the loader by aria-disabled alone (never the property, so the button keeps the keyboard and the tab order)'), 'the gated leg\'s case 6');
});

test('Open point 2 says the poster and svg probes run in Chromium too, and the driver leg does run them there', () => {
  assert.ok(OPEN.includes('The poster and svg probes run under node with fakes and, since round 1, in Chromium over the real DOM (file-print-driver-browser.test.ts'));
  assert.ok(!OPEN.includes('not in Chromium'), 'the first build\'s wording is gone');
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driver.includes('(6) a <video poster> and an svg <image href> in the real DOM'), 'the driver leg\'s case (6)');
  assert.ok(driver.includes('const POSTER = ') && driver.includes('const IMAGE = ') && driver.includes('<video poster='), 'over a poster and an svg image');
  assert.ok(read('ui', 'webview', 'real-viewer-leg.ts').includes('pw.chromium.launch('), 'in Chromium');
});
