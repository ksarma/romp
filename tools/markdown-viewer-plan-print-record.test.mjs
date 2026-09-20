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
// executed case; the fourth review (2026-09-19) gave the settle re-aim's deadline its own executed case; the shared-host
// probe (2026-09-19) had the wait's collection read the printable rule the placeholders are counted by, and guarded
// bodyReady's fallthrough with a census of the roots the viewer seats in the body; the round-2 review (2026-09-19) had
// "Print with them" restore one placeholder at a time with no grant for the page, made a repaint under the ask a disarm
// and never a print, closed bodyReady's lists with the unknown child not in and the PDF kind's loader in, joined the
// browser's own answer and the figure's attributes to the printable rule, and guarded the observer's construction; the
// round-4 fixes (2026-09-20, after the round-3 review) read the figure's hiding from the browser's computed values over every
// painting element, dropped a press's finished probes before a repaint's re-aim, wrote the ask into the wait's row, made the
// seating census derive its population and refuse its unknown, and stated the redirect caveat where the title's contract is.
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
import { createRequire } from 'node:module';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));
/** The TypeScript compiler the UI builds with, for reading a test module's syntax rather than matching its text, and for
 *  running a table a leg builds. */
const tsc = createRequire(path.join(REPO, 'vscode-extension', 'package.json'))('typescript');
/** The figure leg's table, BUILT: `shapes()` and the helpers it reads (`svgOf`, `image`, `HIDE_RULE`), cut from the leg's
 *  source, transpiled with the compiler and run, so a count here is of the rows the leg builds (rows come from loops, so a
 *  `name:` grep undercounts them). A cut that misses either mark fails, which is the failure wanted. */
function figureRows() {
  const src = read('ui', 'webview', 'file-print-figure-browser.test.ts');
  const start = src.indexOf('const svgOf = ');
  const fnAt = src.indexOf('function shapes(): Shape[] {', start);
  const end = src.indexOf('\n}\n', fnAt);
  assert.ok(start >= 0 && fnAt > start && end > fnAt, 'the leg declares svgOf, then shapes()');
  const js = tsc.transpileModule(src.slice(start, end + 2) + '\nreturn shapes();', { compilerOptions: { target: tsc.ScriptTarget.ES2020, module: tsc.ModuleKind.None } }).outputText;
  const rows = new Function(js)();
  assert.ok(Array.isArray(rows) && rows.length > 0 && rows.every((r) => typeof r.name === 'string' && typeof r.html === 'function'), 'the built table: rows with a name and an html builder');
  return rows;
}
/** A count in the section's words, for a pin that derives the number and reads the sentence. */
const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];
const ORDINALS = ['', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth'];
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
/** file-print.ts with its comments, for a pin over its header. */
const flowRaw0 = () => read('ui', 'webview', 'file-print.ts');
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

test('P2: the deadline asks instead of printing, Print anyway prints, Keep waiting is an open-ended wait Escape cancels and whose line offers Print anyway (the ruling of 2026-09-20), and a repaint under the ask counts again', () => {
  assert.ok(P2.includes('after which the bar asks instead of printing (the third review, 2026-09-19): with a picture still loading the flow enters the `stalled` phase and the line reads "1 picture has not loaded." or "N pictures have not loaded." then the button\'s own sentence, "Print anyway leaves out any picture still loading." (`stalledWords`, the count then `anywayWords`) with **Print anyway** and **Keep waiting**'));
  // the words and the titles are the module\'s
  assert.ok(flow.includes('return (n === 1 ? "1 picture has not loaded." : n + " pictures have not loaded.") + " " + anywayWords();'), 'the ask\'s words: the count, then the button\'s own sentence (round 5: the round-4 review\'s HIGH 1)');
  assert.ok(flow.includes('export function anywayWords(): string {\n  return "Print anyway leaves out any picture still loading.";'), 'the button\'s own sentence, anywayWords, takes no count (round 6: the round-5 review\'s ui-1)');
  assert.ok(flow.includes('export const ANYWAY_TITLE = "Print now; a picture still loading is left out";'), 'and its title says the same');
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
  assert.ok(flow.includes('const ask = (pending: number): { state: PrintState; act: PrintAct } => ({ state: { phase: "stalled", gated: 0, pending }, act: "stall" });'), 'the ask helper has no print arm: the deadline\'s zero case prints through the ready branch above, and the repaint\'s zero case disarms');
  assert.equal(flow.split('if (ev.kind === "stalled") return ev.pending > 0 ? ask(ev.pending) : { state: RESTING, act: "disarm" };').length - 1, 1, 'stalled is read under the ask alone (the repaint\'s recount): over a count the ask again, over none a disarm, never a print; the deadline arrives as ready');
  assert.ok(!/"stalled"[^\n]*act: "print"/.test(flow), 'no stalled arm prints');
  assert.ok(flow.includes('if (ev.kind === "escape" && s.untimed === true) return { state: RESTING, act: "disarm" };'), 'Escape cancels the open-ended wait alone');
  const stalled = between(flow, 'case "stalled":', 'break;');
  inOrder(stalled, ['if (ev.kind === "press" || ev.kind === "escape") return { state: RESTING, act: "disarm" };', 'if (ev.kind === "anyway") return { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };', 'if (ev.kind === "keep") return { state: s, act: "resume" };', 'if (ev.kind === "prepare") return begin(ev.pending, true);'], 'the stalled phase');
  assert.ok(flow.includes('case "resume": feed({ kind: "prepare", pending: aimWait(null) }); return;'), 'Keep waiting aims an open-ended wait at the body as it stands');
  assert.ok(P2.includes('The ask is written into the wait\'s standing row (`stall`: the words rewritten, the loader and whatever followed the words removed, the two word buttons appended), so the live region that announced the wait announces the ask'), 'round 4 (the round-2 review\'s ui-2)');
  assert.ok(P2.includes('the armed-to-wait transition and the resume after Keep waiting still build a fresh row, outside that ruling'), 'the narrowing is stated');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('test("(5b) the deadline\'s ask is written into the wait\'s line: the row marked during the wait is the row the ask stands in'), 'the driver leg\'s case (5b)');
  assert.ok(TESTS.includes('the ask written into the wait\'s row (the row marked during the wait is the row the ask stands in'), 'the Tests list names it');
  assert.ok(P2.includes('"Keep waiting" waits on the load and error events alone, with no timer (`settlePictures` under a null deadline; the state carries `untimed`), until every pending picture settles, then prints; Escape cancels that open-ended wait, where the timed wait\'s Escape stays the viewer\'s, which closes the card.'));
  assert.ok(P2.includes('Nothing listens under the ask: "Keep waiting" reads the body as it stands then, so a picture that landed meanwhile is not waited on again, and with none left loading the print runs at once.'));
  // the open-ended wait's line: the waiting words, one word button, and the machine's anyway under untimed alone (romp-manager's
  // ruling, 2026-09-20: not an exit control, since Escape already left the wait, established by execution; no timer)
  assert.ok(flow.includes('return (n === 1 ? "Waiting for 1 picture…" : "Waiting for " + n + " pictures…") + " " + anywayWords();'), 'the open-ended wait\'s words: the count, then the button\'s own sentence');
  assert.ok(P2.includes('While that open-ended wait stands the line reads "Waiting for 1 picture…" or "Waiting for N pictures…" then the same sentence (`waitingWords`, the count then `anywayWords`) beside the loader, with one word button, **Print anyway** (`ANYWAY_WORDS` and `ANYWAY_TITLE`, the ask\'s), which prints at once with what has loaded'));
  assert.ok(flow.includes('if (ev.kind === "anyway" && s.untimed === true) return { state: { phase: "printing", gated: 0, pending: 0 }, act: "print" };'), 'anyway prints under the open-ended wait alone');
  inOrder(between(flow, 'case "preparing":', 'break;'), ['if (ev.kind === "ready")', 'if (ev.kind === "escape" && s.untimed === true)', 'if (ev.kind === "anyway" && s.untimed === true)'], 'the preparing phase: the verdict, then Escape and anyway under the mark');
  assert.equal([...flow.matchAll(/ev\.kind === "anyway"/g)].length, 2, 'anyway is read twice: under the ask, and under the open-ended wait');
  assert.ok(flow.includes('const waitWords = (n: number): string => (state.phase === "preparing" && state.untimed === true ? waitingWords(n) : preparingWords(n));'), 'the wait\'s words by the mark');
  inOrder(between(flow, 'const waitLine = (n: number): void => {', '\n  };'), ['const row = showLine(waitWords(n), true);', 'if (state.phase !== "preparing" || state.untimed !== true) return;', 'b.textContent = ANYWAY_WORDS;', 'b.className = "fileview-btn fileview-err-act";', 'b.title = ANYWAY_TITLE;', 'feed({ kind: "anyway" });', 'row.appendChild(b);'], 'the wait\'s line: the words and the loader, then under the mark alone the one button');
  assert.ok(flow.includes('case "wait": waitLine(state.pending); break;'), 'the wait act builds it');
  assert.ok(P2.includes('not an exit control, since Escape already left the wait; no timer, since a timer would print with a chosen picture missing and nothing said, the defect the ask closed'), 'the ruling\'s two exclusions');
  assert.ok(P2.includes('Escape\'s role there was established by execution in Chromium on the code before the button (2026-09-20): after Keep waiting, Escape rested the bar with the card up and the line gone, nothing printed, the parked request still parked and its release printing nothing; so the person had an exit and lacked a way through.'), 'Escape established, and the reading of it');
  const driverLeg = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driverLeg.includes('test("(15) Keep waiting\'s open-ended wait carries one word button, Print anyway:'), 'the driver leg\'s case (15)');
  inOrder(between(driverLeg, 'test("(15) Keep waiting\'s open-ended wait', '\n});'), ['await page.click(KEEP_BTN);', '{ phase: "preparing", line: WAITING_ONE, buttons: [ANYWAY_WORDS], titles: [ANYWAY_TITLE], loader: true, lines: 1, busy: true }', 'await pause(page, 1000);', 'await page.click(ANYWAY_BTN);', '{ gates: 1, incomplete: 1, line: false }', 'await reloadTo(page, TWO_SLOW_NOTE);', 'await lineReads(page, WAITING_TWO);', '{ marked: true, buttons: [ANYWAY_WORDS], titles: [ANYWAY_TITLE], lines: 1, phase: "preparing", loader: true, prints: 0 }', 'await page.keyboard.press("Escape");', '{ phase: null, line: null, cardUp: true, busy: false, prints: 0, parked: 1 }'], 'case (15): the line after Keep waiting, no print on a timer, the button\'s print, the landing in the same row, then Escape');
  assert.ok(read('ui', 'webview', 'file-print-browser.test.ts').includes('assert.deepEqual(b.buttons, ["Print anyway"], "one word button, the way through the open-ended wait'), 'the gated leg\'s case 4 reads the one button');
  assert.ok(read('ui', 'webview', 'file-print-egress-browser.test.ts').includes('await road(s, "Keep waiting, then Print anyway from the open-ended wait\'s line", { printed: "window.print x1" }'), 'the egress road: one print, nothing asked');
  assert.ok(TESTS.includes('Escape cancels the open-ended wait and Print anyway prints under it, FAILS BEFORE: the event changed nothing during any wait') && TESTS.includes('Since the ruling of 2026-09-20: Keep waiting\'s open-ended wait with its one button') && TESTS.includes('the ask then Keep waiting then Print anyway from the open-ended wait\'s line, nothing asked and one print'), 'the Tests list names the node case, the driver case and the egress road');
  // the driver: the ask in the armed line\'s shape, rewritten in place under a repaint; the recount under the ask
  const stall = between(flow, 'case "stall": {', '\n      }');
  inOrder(stall, ['const words = stalledWords(state.pending);', 'if (line && asked) { line.firstChild!.textContent = words; break; }', 'const row = line || showLine(words);', 'row.firstChild!.textContent = words;', 'while (row.firstChild!.nextSibling) row.firstChild!.nextSibling!.remove();', 'b.className = "fileview-btn fileview-err-act";', 'asked = true;'], 'the ask\'s line: the wait\'s row when one stands, its words rewritten and what followed them removed (round 4: the round-2 review\'s ui-2; file-print-driver-browser.test.ts case (5b) executes the same row)');
  assert.ok(flow.includes('const recountAsk = (): void => { dropDone(); const n = aimWait(null); dropSettle(); feed({ kind: "stalled", pending: n }); };'), 'a repaint under the ask: the complete probes dropped, counted through the wait\'s collection, the listeners off again');
  assert.ok(flow.includes('const dropDone = (): void => { for (const [u, p] of probes) if (p.complete) probes.delete(u); };') && between(flow, 'const reaim = (): void => {', '\n  };').includes('dropDone();'), 'a repaint\'s re-aim drops the complete probes first, under the wait and under the ask (round 4: the round-2 review\'s extra7-1; file-print-driver-browser.test.ts cases (3d) and (13c) execute both)');
  assert.ok(!between(flow, 'const aimWait = (deadlineMs: number | null): number => {', '\n  };').includes('dropDone'), 'never from the settle\'s own re-aim, which would probe a failed URL again at every settle');
  assert.ok(P2.includes('A repaint under the ask counts the new body\'s pictures still loading again (`recountAsk`, through the wait\'s own collection, the listeners taken off again, then the machine\'s `stalled` with the count): over any the line\'s count follows in place; over none the question is moot and the flow rests, the line gone, so the person may press again. A repaint under the ask NEVER prints, since it is no answer to the ask'));
  assert.ok(!P2.includes('none loading prints, as a re-aim does'), 'the print over none is gone from the record');
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('a repaint under the ask counts again or rests over none, and never prints'), 'the node case\'s title says so, and its body asserts the disarm');
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('const moot = step(asked.state, { kind: "stalled", pending: 0 });\n  assert.equal(moot.act, "disarm",'), 'stalled over none: a disarm, executed');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('test("(13) a repaint under the deadline\'s ask never prints:'), 'the driver leg\'s case (13) in Chromium');
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
  assert.ok(flow.includes('const preparingLine = (n: number): void => {') && flow.includes('if (line && line.querySelector(".fileview-print-load")) { line.firstChild!.textContent = waitWords(n); return; }'), 'the standing wait line\'s words change in place (the open-ended wait\'s words under the mark, and its button stays)');
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

test('P2: only a placeholder that reaches the paper is counted, named and restored, by the walk, the browser\'s own answer and the figure\'s attributes; a fold toggled under the armed line is counted again; the print restores one placeholder at a time with no grant for the page, where a click grants the host', () => {
  assert.ok(P2.includes('Only a placeholder that reaches the paper is counted, named and restored (`figurePrintable`: `printable` on the placeholder and, on the figure it wraps, a painting element that shows; the third review and the round-2 review, 2026-09-19, and the round-3 review, 2026-09-20).'));
  // the walk: hidden on any node, a closed details holding the node outside its summary; then the browser's own answer
  const pred = between(flow, 'export function printable(el: PrintableNode): boolean {', '\n}');
  assert.ok(pred.includes('if (n.hasAttribute("hidden")) return false;'), 'hidden, whatever its value');
  assert.ok(pred.includes('if (p && p.localName === "details" && n.localName !== "summary" && !p.hasAttribute("open")) return false;'), 'a closed details, its summary excepted');
  assert.ok(pred.includes('for (let n: PrintableNode | null = el; n; n = n.parentElement) {'), 'walked to the root');
  assert.ok(pred.includes('return rendered(el) !== false;'), 'then the browser\'s own answer: null (no API) leaves the walk\'s answer, false is not printable');
  const rend = between(flow, 'export function rendered(el: PrintableNode): boolean | null {', '\n}');
  assert.ok(rend.includes('if (typeof el.checkVisibility !== "function" || typeof el.getClientRects !== "function") return null;'), 'null where the browser cannot be asked');
  assert.ok(rend.includes('return el.checkVisibility({ visibilityProperty: true, opacityProperty: true }) && el.getClientRects().length > 0;'), 'checkVisibility with visibility and opacity, and a client rect');
  assert.ok(P2.includes('Then the browser\'s own answer, where it can be asked (`rendered`: `checkVisibility` with visibility and opacity read, and at least one client rect; null on a stand-in under node or an engine without the API, where the walk alone decides)'));
  assert.ok(P2.includes('falls to NOT printable, the unknown side answered against the fetch'));
  // the figure's own hiding: hidden and popover on an HTML element, the author's display, and the computed visibility and opacity (round 4: the round-3 review's correctness-1 and regression-1)
  assert.ok(flow.includes('export function figureHidden(el: FigureNode): boolean { return offPaper(el, true); }'), 'figureHidden reads the element as the one that paints');
  const off = between(flow, 'function offPaper(el: FigureNode, self: boolean, root: FigureNode = el): boolean {', '\n}');
  // round 5 (the round-4 review's extra8-3): the display is the computed one below the root and the author's declaration at the root or where nothing computes
  inOrder(off, ['if (isHtml(el) && (el.hasAttribute("hidden") || el.hasAttribute("popover"))) return true;', 'const cs = computedOf(el);', 'const authored = el === root || cs === null;', 'const display = authored ? authorDisplay(el) : cs.display;', 'if (display === "none" || (authored && display === "contents" && el.namespaceURI === SVG_NS && !contentsRenders(el))) return true;', 'if (cs === null) return false;', 'if (Number(cs.opacity) === 0) return true;', 'return self && (cs.visibility === "hidden" || cs.visibility === "collapse");'], 'offPaper: the HTML attributes, the computed display below the root or the author\'s at it, the contents hand-decide on the authored road alone (round 6: the round-5 review\'s correctness-2), then the computed opacity and, for the painting element, the computed visibility; no pattern over the attribute\'s text');
  assert.ok(flow.includes('function computedOf(el: FigureNode): { visibility: string; opacity: string; display: string } | null {'), 'computedOf returns the display too');
  assert.ok(flow.includes('if (offPaper(paint, true, root)) return false;') && flow.includes('if (offPaper(a, false, root)) return false;'), 'shows passes the root down, so offPaper knows which element is the root');
  assert.ok(P2.includes('`display` none, read as the browser COMPUTES it on every element below the figure\'s root (the gate\'s sheet sets none on the root alone, and display does not inherit, so each descendant\'s computed display is its own; a sheet rule on an author\'s class is read this way, which the author\'s declaration alone missed: the round-4 review\'s extra8-3, 2026-09-20) and, for the root itself and wherever nothing computes, from the author\'s own declaration'));
  assert.ok(read('ui', 'webview', 'file-print.ts').includes('on a link the engines differ: Chromium and WebKit compute it to none, Firefox keeps it and paints the\n *  image inside (file-print-figure-browser.test.ts in the three engines, 2026-09-20'), 'contentsRenders\' docstring names the measured direction per engine (a comment, read as one; round 6: the round-5 review\'s correctness-2, which found the earlier docstring naming the unmeasured direction alone)');
  assert.ok(!read('ui', 'webview', 'file-print.ts').includes('none of the three is measured to'), 'the round-5 docstring\'s unmeasured direction is gone');
  assert.ok(P2.includes('`contentsRenders`, on the root and where nothing computes alone; below the root a computed `contents` is the browser\'s own and is trusted as rendering, the engines differing on a link, as the docstring states per engine'));
  const leg = read('ui', 'webview', 'file-print-figure-browser.test.ts');
  assert.ok(leg.includes('for (const engine of ENGINES) test("figureHidden and figurePrintable over real gated figures in " + engine + ":'), 'the figure leg runs once per engine');
  assert.ok(leg.includes('paints: { chromium: false, firefox: true, webkit: false } });') && leg.includes('type PerEngine = Record<Engine, boolean>;'), 'the link row carries each engine\'s own answer (round 6: the round-5 review\'s correctness-2 and regression-1)');
  assert.ok(read('ui', 'webview', 'real-viewer-leg.ts').includes('export async function inBrowser(t: any, body: (browser: any) => Promise<void>, engine: Engine = "chromium"): Promise<void> {'), 'inBrowser takes the engine, Chromium unless named');
  // round 6, the divergences that predate the fix: where an engine's twin oracle reads other than the paint, the row records it and the flow is held to the paint
  assert.ok(leg.includes('twinReads?: Partial<PerEngine> };') && leg.includes('assert.deepEqual(offRecord, [], "where the twin oracle is recorded to read other than the paint, the flow answers the paint");') && leg.includes('const wrongPaper = paperMismatches(rows, all.map((s) => oracleReads(s, engine)));'), 'the twin oracle\'s recorded per-engine readings, the flow held to the paint and the oracle to the reading');
  assert.ok(P2.includes('where an engine\'s twin oracle reads other than the paint the row records that engine\'s reading and the flow is held to the paint, the twin oracle to the reading'), 'the record says so');
  assert.ok(read('ui', 'webview', 'file-print.ts').includes('`1e-9` is the engine\'s own: Chromium and Firefox keep it,\n *  WebKit computes it to 0'), 'the opacity docstring names WebKit\'s reading of 1e-9');
  assert.ok(!/parseFloat|\/\^/.test(off), 'no parse of the attribute\'s text and no pattern: the computed value is read');
  const join = between(flow, 'export function figurePrintable(', '\n}');
  assert.ok(join.includes('if (!printable(g)) return false;') && join.includes('if (!root) return true;') && join.includes('return paintsOf(root).some((p) => shows(p, root));'), 'figurePrintable joins the two over every painting element of the figure; a placeholder with no figure answers for itself (round 4: the round-3 review\'s regression-3)');
  assert.ok(!P2.includes('), an enumeration, since the sheet hides every child of a placeholder'), 'the round-2 enumeration sentence is gone (round 4: the round-3 review\'s correctness-1, regression-1, regression-3)');
  assert.ok(P2.includes('`hidden` whatever its value and `popover` on an HTML element, which the browser ignores on an SVG element') && P2.includes('the `opacity` the browser COMPUTES, zero in any spelling') && P2.includes('and, on the painting element itself, the `visibility` the browser computes, hidden or collapse'), 'the record states the computed read');
  assert.ok(P2.includes('The gate\'s sheet sets `display: none` on the gated root and nothing else, so the computed visibility and opacity of a gated figure are the restored figure\'s and are read'), 'and why the computed values can be read of a gated figure');
  for (const sheet of ['styles.css', 'feed.css']) assert.ok(read('ui', 'webview', sheet).includes('.fv-gate[data-act="fv-load"] > :not([data-fv-label]) { display: none; }'), sheet + ': the gate rule sets display none alone (file-print-figure-browser.test.ts holds it in Chromium)');
  assert.ok(flow.includes('const isHtml = (el: FigureNode): boolean => el.namespaceURI === undefined || el.namespaceURI === null || el.namespaceURI === HTML_NS;'), 'an HTML element by its namespace');
  assert.ok(flow.includes('const view = el.ownerDocument ? el.ownerDocument.defaultView : null;') && flow.includes('const cs = view.getComputedStyle(el);'), 'the computed style through the element\'s own window');
  assert.ok(flow.includes('export const PAINTS_SEL = "img, video, audio, circle, ellipse, image, line, path, polygon, polyline, rect, text, use, foreignObject";') && flow.includes('const SVG_RENDERS: readonly string[] = ["svg", "g", "a", "switch"];'), 'the painting elements and the SVG containers that render, as P2 names them');
  assert.ok(P2.includes('`paintsOf`: the root when it is an `<img>`, a `<video>` or an `<audio>` with `controls`, and the descendants `PAINTS_SEL` names') && P2.includes('and any SVG container `SVG_RENDERS` does not name, takes its paint off, the safe side'));
  assert.ok(P2.includes('every other kept attribute leaves the figure on the paper as far as the flow reads, an svg\'s `transform`, `clip-path`, `mask` and `filter` among them (open point 8)'));
  // the round-3 history and the legs that hold it
  assert.ok(P2.includes('before the round-3 review (2026-09-20) the opacity was matched against one spelling of zero by a pattern and the placeholder\'s first element child alone was read'));
  assert.ok(P2.includes('file-print-figure-browser.test.ts, in Chromium, Firefox and WebKit since the round-5 review: every one of 83 gated shapes built twice on one page, 74 at the round-3 review and nine more since the round-4 review'));
  assert.ok(read('ui', 'webview', 'file-print-egress-browser.test.ts').includes('test("(12) a gated svg at opacity 0e0 and a <picture> whose <img> is hidden, beside a plain placeholder, on three hosts, and a gated svg at opacity 0 on the plain placeholder\'s host:'), 'the egress leg\'s case (12), with the shared-host shape (round 5: the round-4 review\'s tests-4)');
  assert.ok(P2.includes('and since the round-4 review\'s tests-4 (2026-09-20) a gated svg at `opacity="0"` on the plain placeholder\'s own host'));
  assert.ok(P2.includes('file-print-egress-browser.test.ts case (12): a gated svg at `opacity="0e0"` and a `<picture>` whose `<img>` carries `hidden`'));
  assert.ok(P2.includes('with an ungated twin beside it: the title names a host exactly when the browser renders the placeholder and paints the twin'), 'the (D) census carries twins');
  // the driver reads the body's placeholders through figurePrintable, and every count, title and restore goes through gates()
  assert.ok(flow.includes('const gates = (): HTMLElement[] => (Array.from(host.body.querySelectorAll(\'[data-act="\' + GATE_ACT + \'"]\')) as HTMLElement[]).filter(figurePrintable);'), 'the placeholders the flow reads are the printable ones, the figure read too');
  assert.equal([...flow.matchAll(/querySelectorAll\('\[data-act="' \+ GATE_ACT/g)].length, 1, 'one read of the body\'s placeholders, so no count, title or restore bypasses the filter');
  assert.ok(flow.includes('for (const g of list) for (const h of (g.getAttribute("data-fv-hosts") || "").split(" ")) if (h) hosts.add(h);'), 'the hosts come from those placeholders (hostsOf over the kept list)');
  // the sanitizer keeps details and hidden (both shapes come from the author) and strips an inline display: none
  const sanitize = code(read('ui', 'webview', 'md-sanitize.ts'));
  assert.ok(sanitize.includes('export const MD_FORBID_ATTR: readonly string[] = ["background", "usemap"];'), 'hidden is not forbidden');
  assert.ok(!between(sanitize, 'export const MD_FORBID_TAGS: readonly string[] = [', '];').includes('"details"'), 'details is not forbidden');
  assert.ok(sanitize.includes('const KEPT_PROPERTIES = new Set(["color", "background-color"]);'), 'a style keeps colour declarations alone: display: none goes');
  assert.ok(P2.includes('a picture under an inline `display: none` is printable, since the sanitizer strips that style (md-sanitize.ts `colorOnlyStyle` keeps colour declarations alone) and the picture prints'));
  // a fold toggled under the armed line: the details' toggle event, capture phase on the card, a recount while armed
  assert.ok(P2.includes('A fold the person opens or closes under the armed line is counted again (the details\' `toggle` event, which does not bubble, heard on the card in the capture phase), as a repaint is.'));
  assert.ok(flow.includes('const onToggle = (): void => { if (state.phase === "armed") feed({ kind: "recount", gated: gates().length }); };'), 'the toggle recounts while armed');
  assert.ok(flow.includes('host.card.addEventListener("toggle", onToggle, true);'), 'on the card, capture phase');
  // the two roads: the print's one-placeholder restore grants nothing; the click's loadGatedHost grants the host for the page
  const gate = code(read('ui', 'webview', 'figure-gate.ts'));
  const one = between(gate, 'export function loadGatedFigure(wrap: Element): boolean {', '\n}');
  assert.ok(one.includes('if (wrap.getAttribute("data-act") !== GATE_ACT) return false;') && one.includes('restore(wrap);') && one.includes('return true;'), 'one placeholder, found by the mark, restored');
  assert.ok(!one.includes('loadedHosts'), 'and no host joins the loaded set');
  const load = between(gate, 'export function loadGatedHost(host: string, doc: ParentNode = document): void {', '\n}');
  assert.ok(load.includes('loadedHosts.add(host.toLowerCase());') && load.includes('regateFigures(doc);'), 'the click: the host joins the loaded set and every placeholder waiting on it is re-judged');
  assert.ok(between(gate, 'export function regateFigures(doc: ParentNode): void {', '\n}').includes('if (!hosts.length) restore(wrap);'), 'a placeholder whose hosts are all loaded is restored, printable or not: the click\'s road');
  assert.ok(between(gate, 'export function allowedFigureHosts(extra: Iterable<string> = []): Set<string> {', '\n}').includes('for (const h of loadedHosts) s.add(h);'), 'the loaded hosts are allowed for the rest of the document');
  assert.ok(flow.includes('import { GATE_ACT, loadGatedFigure } from "./figure-gate";') && !flow.includes('loadGatedHost('), 'the flow imports the one-placeholder restore and calls the click\'s road nowhere');
  assert.ok(P2.includes('"With them" restores exactly the placeholders it counted, each through `loadGatedFigure` (figure-gate.ts), the gate\'s restore of ONE placeholder'));
  assert.ok(P2.includes('WITHOUT adding the host to the document\'s `loadedHosts`'));
  assert.ok(P2.includes('The two roads are kept apart on purpose: the print\'s restore is per placeholder and for this print alone (above), where a click\'s `loadGatedHost` grants the host for the rest of the page, since `loadedHosts` is per document'));
  assert.ok(!P2.includes('The gate loads by host:'), 'the by-host sentence is gone');
  assert.ok(!P2.includes('a host "with them" loads is granted for the rest of the page'), 'and the page-life grant of a print with it');
  // P6 carries the clause; the legs execute the shapes
  const P6 = part('P6. **', 'P7. **');
  assert.ok(P6.includes('and only for a placeholder that reaches the paper (P2\'s `figurePrintable` rule): a placeholder that does not reach the paper is not restored and its URL is not asked, whether its host is shared with a printable placeholder or named by it alone; and the print grants no host for the page'));
  assert.ok(!P2.includes('one fetch per restored placeholder') && !P6.includes('one per restored placeholder'), 'the requests are the ones the figures make, not one per placeholder (round 4: the round-3 review\'s extra7-4; a placeholder naming two hosts fetches from both)');
  assert.ok(P2.includes('So the requests are the ones those figures make, and the grant is this print\'s alone') && P6.includes('so the requests are the fetches those figures make, and only for a placeholder that reaches the paper'));
  assert.ok(read('ui', 'webview', 'figure-gate.test.ts').includes('test("loadGatedFigure restores ONE placeholder and grants nothing for the page:'), 'the gate\'s node case');
  const armed = read('ui', 'webview', 'file-print-armed-browser.test.ts');
  assert.ok(armed.includes('(C) only a placeholder that reaches the paper is counted, named and loaded'), 'the armed leg\'s case (C)');
  assert.ok(armed.includes('test("(D) the census of the printable rule\'s unknown side:'), 'the armed leg\'s case (D): the browser\'s answer and the figure\'s attributes in Chromium');
  assert.ok(read('ui', 'webview', 'file-print-egress-browser.test.ts').includes('test("(7) two placeholders on one host, one in the open body and one inside a closed <details>, both routes answering:'), 'the egress leg\'s case (7): per host and per placeholder');
  assert.ok(P2.includes('file-print-egress-browser.test.ts case (7) reads the two counts apart over one host named by an open and a folded placeholder, both routes answering: per host, one host asked and one request; per placeholder, the open one\'s URL once and the folded one\'s never'));
  assert.ok(!OPEN.includes('6. The wait and the pictures that never reach the paper.'), 'the fourth review\'s open point 6 is gone: the wait reads the rule now (the test below)');
  assert.ok(P2.includes('the fourth review\'s open point 6, whether the wait should read the same rule, is taken by this one'), 'and P2 says where it went');
  assert.ok(OPEN.includes('8. The figure half of the printable rule answers on the permissive side.'), 'the enumeration\'s permissive side is the owner\'s point');
});

test('P2: the wait, its count, the eager flip and the ask cover the pictures that reach the paper: each of the three collections is filtered by printable, the browser\'s answer included, the egress leg executes the shared-host fold with the folded route parked and with both routes answering, and the node test executes the three collections', () => {
  assert.ok(P2.includes('The wait, its count on the line, the eager flip and the deadline\'s ask cover the pictures that reach the paper alone: `collectPictures` filters each of its three collections by `printable`, the rule the placeholders are counted by (the `<img>` itself; the `<video>` for its poster; the svg `<image>` element)'));
  const collect = between(flow, 'export function collectPictures(body: ParentNode, base: string, probe: (url: string) => Picture): Picture[] {', '\n}');
  assert.ok(collect.includes('body.querySelectorAll("img").forEach((el) => { if (!printable(el)) return; const img = el as HTMLImageElement; if (img.loading === "lazy") img.loading = "eager"; out.push(img); });'), 'the img itself, before the eager flip');
  assert.ok(collect.includes('body.querySelectorAll("video[poster]").forEach((v) => { if (!printable(v)) return;'), 'the video for its poster');
  assert.ok(collect.includes('body.querySelectorAll("image").forEach((im) => { if (!printable(im)) return;'), 'the svg image element');
  assert.equal([...collect.matchAll(/querySelectorAll\(/g)].length, 3, 'three collections, no fourth outside the rule');
  assert.equal([...collect.matchAll(/if \(!printable\(\w+\)\) return;/g)].length, 3, 'each filtered');
  // why a folded picture can still be loading: the browser fetched it at the render when its host was allowed; the print's
  // one-placeholder restore does not touch it (the test above holds the two roads apart)
  assert.ok(P2.includes('Such a picture can still be loading during the wait when its host is allowed (the gear\'s list, or a host a click loaded for the page), since the browser fetches an `<img>` the fold hides at the render; "with them" does not restore it (the per-placeholder restore above).'));
  assert.ok(!P2.includes('since the gate restores by host'), 'the by-host reason is gone');
  assert.ok(P2.includes('and the browser\'s answer is read through it too, so a picture the browser does not render'));
  // the legs (the egress leg is named by its cases' titles alone: its rows are the report's, read from a run)
  const egress = read('ui', 'webview', 'file-print-egress-browser.test.ts');
  assert.ok(egress.includes('test("(6) two placeholders on one host, one in the open body and one inside a closed <details>, the folded picture\'s route parked:'), 'the egress leg\'s case (6)');
  assert.ok(egress.includes('test("(7) two placeholders on one host, one in the open body and one inside a closed <details>, both routes answering:'), 'and its case (7)');
  for (const head of ['test("(8) one host, four placeholders (the open body; a closed typed <details>; a folded callout; a hidden div), every route answering:', 'test("(9) one host, four placeholders, the open picture\'s route parked.', 'test("(10) a printable and a folded placeholder on one host, and a second host with a folded placeholder alone:', 'test("(11) two hosts, each with a printable placeholder and one that never reaches the paper:']) assert.ok(egress.includes(head), 'the egress leg\'s case ' + head.slice(6, 10));
  assert.ok(egress.includes('"egress | road | hosts: ... | per-url: ... | placeholders: printable'), 'the row shape the Tests list quotes');
  assert.ok(TESTS.includes('("egress | road | hosts: ... | per-url: ... | placeholders: printable ... / not ... | grant: ... | printed: ... | local: ... | other: ...")'));
  for (const n of ['(8) one host, four placeholders', '(9) the same page with the open picture\'s route parked', '(10) a printable and a folded placeholder on one host and a second host with a folded placeholder alone', '(11) two hosts, each with a printable placeholder and one that never reaches the paper']) assert.ok(TESTS.includes(n), 'the Tests list names case ' + n.slice(0, 4));
  assert.ok(P2.includes('file-print-egress-browser.test.ts case (6) executes that shape with the folded picture\'s route parked: after "with them" the line reads one picture, the print fires at the open picture\'s load, under the deadline, with the folded placeholder standing, its URL never asked (the parked route holds nothing) and every `<img>` in the body complete, no ask, and the host asked once, for the open placeholder\'s URL'));
  assert.ok(!P2.includes('both placeholders restored by the host\'s load'), 'the by-host outcome is gone from the record');
  const unit = read('ui', 'webview', 'file-print.test.ts');
  assert.ok(unit.includes('test("collectPictures reads the printable rule the placeholders are counted by (FAILS BEFORE:'), 'the node test');
  assert.ok(unit.includes('test("collectPictures reads the browser\'s answer through printable too:'), 'and the browser\'s answer through it');
  assert.ok(TESTS.includes('the printable rule over each of the three collections: a picture under hidden or inside a closed details left out and a lazy one among them not set eager, a summary\'s picture and an open details\' collected'));
  assert.ok(TESTS.includes('(6) a host two placeholders share, one in the open body and one inside a closed `<details>`, the folded picture\'s route parked'));
  assert.ok(TESTS.includes('(7) the same page with both routes answering, the per-host and the per-placeholder counts read apart'));
});

test('P7: bodyReady classes each child against three closed lists and answers not in for an unknown child, the PDF kind excepting the loader; the node census derives the seated roots from file-view.ts by the command the section names and holds the unknown side; the nine roots the section names are the lists\' union', () => {
  const P7 = part('P7. **', '**Derivations and their unknown cases.**');
  assert.ok(P7.includes('The unknown child answers NOT in, the safe side'));
  assert.ok(!P7.includes('reads as content on purpose'), 'the permissive fallthrough is gone from the record');
  assert.ok(P7.includes('The lists are guarded by a census, so a root the viewer gains is classed on purpose or not at all'));
  const lists = {};
  for (const name of ['READY_ROOTS', 'NOT_READY_ROOTS', 'LINE_ROOTS']) {
    const lit = between(flow, 'export const ' + name + ': readonly string[] = [', '];');
    lists[name] = [...lit.matchAll(/"([\w.-]+)"/g)].map((m) => m[1]);
    assert.ok(lists[name].length >= 1, name + ' names a root');
  }
  const union = Object.values(lists).flat().sort();
  assert.equal(new Set(union).size, union.length, 'no root in two lists');
  const named = /Today the census derives (\w+) roots: (.*?`)\./.exec(P7);
  assert.ok(named, 'the section counts and names the roots the census derives');
  const inPlan = [...named[2].matchAll(/`([^`]+)`/g)].map((m) => m[1]).sort();
  assert.deepEqual(inPlan, union, 'the roots the section names are the three lists\' union');
  assert.equal(NUMBER_WORDS[named[1]] ?? Number(named[1]), union.length, 'the section says ' + named[1] + '; the lists hold ' + union.length);
  // bodyReady reads the lists through rootKind: unknown is not in, a wait root is not in but the PDF kind's loader, a content root makes the body in
  const ready = between(flow, 'export function bodyReady(body: BodyLike, kind: PrintKind = "document"): boolean {', '\n}');
  inOrder(ready, ['const k = rootKind(c);', 'if (k === "unknown") return false;', 'if (k === "wait") {', 'if (kind === "pdf" && isRoot(c, [PDF_LOADER_ROOT])) { content = true; continue; }', 'return false;', 'if (k === "content") content = true;', 'return content;'], 'bodyReady: unknown out, a wait root out unless the PDF kind\'s loader, content in');
  const kind = between(flow, 'export function rootKind(c: BodyChild): RootKind {', '\n}');
  inOrder(kind, ['if (isRoot(c, READY_ROOTS)) return "content";', 'if (isRoot(c, NOT_READY_ROOTS)) return "wait";', 'if (isRoot(c, LINE_ROOTS)) return "line";', 'return "unknown";'], 'rootKind: the three lists, else unknown');
  assert.ok(flow.includes('export const PDF_LOADER_ROOT = "div.fileview-load";'), 'the one exception, named');
  assert.ok(lists.NOT_READY_ROOTS.includes('div.fileview-load'), 'and it is one of the wait roots');
  assert.ok(P7.includes('The PDF kind is the one exception, for the loader: `bodyReady` takes the file\'s kind'));
  // the census: the derivation command is the one the section names, and the test reads the viewer rather than a list
  const census = read('ui', 'webview', 'file-print.test.ts');
  // round 4 (the round-3 review's tests-3): the census collects every use of `body`, classes each, and refuses what it cannot
  // round 5 (the round-4 review's correctness-2, tests-2, regression-1): every member access, in every spelling, and the rest refused
  // round 5 (the round-4 review's verifiers): every `body` token, a member access classed by its tail and a bare token by its context
  assert.ok(P7.includes('classes every `body` token in it. A token a member access follows (`body.<member>`, `body?.<member>`, `body[...]` and `body?.[...]`, across any whitespace and a non-null `!`, with `document.body` and any other receiver\'s `.body` set aside) is classed by what follows the member'));
  assert.ok(census.includes('const tokens = [...src.matchAll(/(?<![\\w$.])body(?![\\w$])/g)].map((m) => m.index!).filter((i) => !inLiteral(i));'), 'every body token outside a literal');
  assert.ok(census.includes('const access = /^\\s*!?\\s*(\\?\\.\\s*\\[|\\[|\\?\\.|\\.)\\s*(\\w+)?/.exec(src.slice(at + 4));'), 'a member access: the dot, the optional dot, the computed access, across whitespace');
  assert.ok(census.includes('const why = bareContext(src, at, openerAt, parentOf);') && census.includes('const HANDED_OUT = "body is written bare where the census cannot class it";') && census.includes('a callee the census does not list: read it by hand for a seat in the body and list it in BODY_HANDED_TO'), 'a bare token is classed by its context and refused with its line otherwise');
  assert.ok(census.includes('const BODY_HANDED_TO: Array<{ callee: string; own?: true; why: string }> = [') && census.includes('as reading the body under its own parameter named body, and the source declares no such parameter: read it by hand again'), 'the callees handed the body are listed with a reason each, and an own-parameter claim is held to the source');
  assert.ok(P7.includes('and EVERY OTHER `body` TOKEN FAILS the census with its line: an alias (`const b = body`), a return, an arrow\'s value, an array element, a ternary or logical operand, a parenthesised or cast receiver (`(body).append(x)`), an argument to a callee it does not list'));
  assert.ok(P7.includes('Before the round-5 fix (2026-09-20) the census read member accesses on the `body` token alone'));
  assert.ok(census.includes('reaches a member by a computed name the census cannot read'), 'a computed name is refused');
  assert.ok(census.includes('reaches the seating method through a further access (call, bind, apply, a computed name), which seats where the census cannot read the arguments'), 'call, bind and apply on a seating method are refused');
  assert.ok(census.includes('is read bare, and a member the census does not know as a scalar or a non-seating method, handed out, could seat where the census cannot follow'), 'a bare read of an unlisted member is refused');
  assert.ok(census.includes('is a further access on a member the census does not know'), 'a further access on an unlisted member is refused');
  assert.ok(census.includes('ts.createSourceFile("file-view.ts", src, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS)') && census.includes('ts.getLeadingCommentRanges(src, n.getFullStart())') && census.includes('ts.getTrailingCommentRanges(src, n.getEnd())') && !census.includes('[ \\t]\\/\\/[^\\n]*'), 'comments are blanked by the compiler\'s read of them, wherever they stand (round 5: the pattern that keyed on a space before // is gone)');
  assert.ok(P7.includes('reads file-view.ts with its comments blanked by the TypeScript compiler\'s own read of them (every comment range the parser reports, a `//` at the start of a line or after a `;` among them; string, template and regular-expression literals kept, and a `body` inside one skipped as text)'));
  assert.ok(census.includes('replaceChildren: (a) => a, prepend: (a) => a, append: (a) => a,') && census.includes('appendChild: (a) => a.slice(0, 1), insertBefore: (a) => a.slice(0, 1), insertAdjacentElement: (a) => a.slice(1, 2),'), 'the seating methods and the arguments each seats, as P7 says');
  assert.ok(P7.includes('(`replaceChildren`, `prepend` and `append` seat every argument; `appendChild` and `insertBefore` their first; `insertAdjacentElement` its second)'));
  assert.ok(census.includes('refused.push("line " + line + ": " + use + "(...) is a call the census does not know");') && census.includes('is an assignment the census does not know (innerHTML and its kin seat what no resolver reads)') && census.includes('hands out a node and a further access on it could seat where the census cannot follow'), 'the unknown call, assignment and child access are refused with the line');
  // round 6 (the round-5 review's cluster 1): the default refuses; every seat on any receiver is read by the compiler's tree and passes only as a site the table lists
  assert.ok(!census.includes('src.matchAll(/\\.(replaceWith|after|before|replaceChild|insertAdjacentElement|insertAdjacentHTML)\\(/g)'), 'the six-name child-level read, a closed list of dangerous forms, is gone (round 6)');
  assert.ok(census.includes('const { sites, computed } = seatSites(src);') && census.includes('if (s.body) continue;') && census.includes('const entry = table.find((e) => e.in === s.fn && e.on === s.on && e.via === s.via);') && census.includes('a receiver the census has not read by hand: read the site for what'), 'every seat on a receiver other than the body token passes only as a site the table lists, else is refused with its line');
  assert.ok(census.includes('const SEAT_CALLS = [...Object.keys(SEATING), "replaceWith", "after", "before", "replaceChild", "insertAdjacentHTML"];') && census.includes('const SEAT_ASSIGNS = ["innerHTML", "outerHTML"];'), 'the seating forms the second read covers: the six the body read resolves, the five child-level names, and the two HTML assignments');
  assert.ok(census.includes('const SEATS_READ_BY_HAND: SeatRead[] = [') && census.includes('type SeatRead = { in: string; on: string; via: string; is: string };'), 'the table: a site is its function, receiver and form, with what the receiver is');
  assert.ok(census.includes('and the source has no such seat: the entry is stale, remove it or read the site again') && census.includes('calls through a computed name the census cannot read'), 'a stale entry and a computed-name call are refused');
  assert.ok(census.includes('const withoutEntry = census(VIEWER_SRC, SEATS_READ_BY_HAND.filter((e) => e !== dropped));') && census.includes('const stale = census(VIEWER_SRC, [...SEATS_READ_BY_HAND, {'), 'the table is read, not decorative: a removed entry reds the live site and a stale entry reds');
  assert.ok(P7.includes('The file is then read a SECOND time, by the compiler\'s tree, for every seat on ANY receiver') && P7.includes('every other seat passes only as a site the census lists by hand (`SEATS_READ_BY_HAND`') && P7.includes('a seat on any other receiver the census has not read by hand fails it with the line'), 'the record states the second read and the inverted default');
  assert.ok(P7.includes('The ruling inverted the default (a guard whose gap passes certifies the cases it failed to consider)'), 'and why');
  assert.ok(!P7.includes('The file is read once\nmore for a child-level seat anywhere'), 'the six-name read is gone from the record');
  // round 6 (tests-1, extra8-2): the node-member exemption directly inside the body call's own arguments; the accessor at its declared site
  assert.ok(census.includes('at > open && at < close && openerAt.get(at) === open') && P7.includes('a bare read of a node member passes directly inside a `body` call\'s own argument list alone'), 'the node-member exemption is held to the body call\'s own argument list');
  assert.ok(census.includes('const ACTION_CTX_DECL = "const ctx: FileViewActionCtx =";') && P7.includes('passes at its one declared site, inside the object literal `const ctx: FileViewActionCtx = {`, which the census holds the source to declaring, and the spelling anywhere else fails'), 'the accessor is keyed on its site');
  assert.ok(census.includes('assert.deepEqual(refused, [], "every use of the body is one the census knows how to read'), 'the census fails on any refusal');
  assert.ok(P7.includes('a call of a method that seats nothing passes AS A CALL (`addEventListener`, `querySelector`, `focus`, `contains`, the geometry reads and their kin, a closed list; what is done with the call\'s value is the second read\'s, below, so a seat on `body.querySelector(...)!.parentElement` fails there)'), 'the non-seating call passes as a call alone: its value\'s seat is the second read\'s (round 6; the round-5 review measured the universal false for a seat through a query result)');
  assert.ok(P7.includes('and EVERY OTHER MEMBER ACCESS ON `body` FAILS the census with its line: a computed name (`body["append"]`), a call it does not know, an assignment it does not know (`innerHTML` and its kin seat what no resolver reads), a further access on a member that hands out a child node, on a seating method (`.call`, `.bind`, `.apply`) or on a member it does not list, and a bare read of a member it does not list (a seating method handed out)'));
  assert.ok(!P7.includes('EVERY OTHER USE FAILS'), 'the round-3 universal, which the round-4 review measured false for five forms, is gone from the record');
  assert.ok(P7.includes('Before the round-4 review (2026-09-20) the collect pattern read `body.<member>` alone, so `body?.append(x)` and `body["append"](x)` were outside it, `body.append?.(x)` was refused only for a member that hands out a node, and `body.append.call(body, x)`, `.bind`, `.apply` and a bare `body.append` passed'));
  const mutant = between(census, 'test("the census refuses its unknown and derives its population, executed over mutants of file-view.ts\'s source:', '", () => {');
  for (const form of ['body?.append(x)', 'body[\\"append\\"](x)', 'body.append?.(x)', 'body.append.call(body, x), .bind and .apply', 'a bare body.append', 'body.classList.add(...) still passes', '(body).append(x)', '(body as HTMLElement).append(x)', 'an alias const b = body', '[body].forEach(...)', 'Element.prototype.append.call(body, x)', 'a helper handed the body', 'a column-0 // comment or after ;//', 'a listed root\'s seat moved into one kept the census green',
    'a seat through body.querySelector(...)!.parentElement', 'a stored query result', 'md.parentElement!.append(x)', 'a parent held in a variable', 'body.closest(...) and body.getRootNode()', 'a node read inside a listener\'s callback or a nested call within a body call\'s arguments and then seated', 'the accessor body: () => body written anywhere but its declared site', 'a live site whose entry is removed, a stale entry and the ctx declaration renamed']) assert.ok(mutant.includes(form), 'the mutant case names the planted form ' + form);
  const rootsDoc = between(read('ui', 'webview', 'file-print.ts'), '/** The roots file-view.ts seats in the body, as `<tag>.<class>`', 'export const READY_ROOTS');
  const rootsOne = rootsDoc.replace(/\n\s*\*\s*/g, ' ').replace(/\s+/g, ' ');
  assert.ok(!/replaceChildren.*prepend.*appendChild/.test(rootsDoc) && rootsOne.includes('every seat in the viewer\'s source, read by file-print.test.ts\'s census with its default refusing (the rule, not a roster of method names; the round-5 review, 2026-09-20)'), 'the READY_ROOTS comment states the rule, not the round-2 roster (round 5: the round-4 review\'s regression-2; round 6: the default refuses; a comment, read as one, its hard wraps collapsed)');
  assert.ok(rootsOne.includes('a seat on ANY OTHER receiver (a seating call, an innerHTML or outerHTML assignment) passes only as a site the census lists by hand (its function, receiver and form, with what the receiver is), and every other seat fails the census with its line, whatever produced the receiver') && rootsOne.includes('the action-context accessor at its one declared site (`body: () => body` inside `const ctx: FileViewActionCtx = {`)'), 'the READY_ROOTS comment states the second read and the accessor\'s site (round 6)');
  const install = read('ui', 'webview', 'file-view.ts').replace(/\n\s*\/\/\s*/g, ' ');
  assert.ok(install.includes('Its default refuses: it reads every `body` token in this file, resolves a seating call\'s roots and refuses every token it cannot class (a computed name, a bare read of a seating method, a call, bind or apply on one, a member it has not seen, an alias, a parenthesised or cast receiver, a helper handed the body that its BODY_HANDED_TO list does not name), and it reads every seat in this file on any other receiver (a seating call, an innerHTML or outerHTML assignment) and refuses each whose site (function, receiver, form) its SEATS_READ_BY_HAND table does not list, whatever produced the receiver.'), 'the viewer\'s install comment states the same rule, both reads (a comment, read as one, its hard wraps collapsed)');
  assert.ok(install.includes('its census reads every seat in this file, refusing what it has not read by hand; the local viewer\'s install comment says how'), 'and the URL viewer\'s install comment points at it');
  assert.ok(P7.includes('Before the round-3 review the sites were found by a closed list of three method names, `replaceChildren`, `prepend` and `appendChild`, and the census\'s unknown passed'));
  assert.ok(!P7.includes('grep -nP'), 'the three-name command is gone from the record');
  assert.ok(!census.includes('(replaceChildren|prepend|appendChild)'), 'and from the census');
  assert.ok(census.includes('test("the census refuses its unknown and derives its population, executed over mutants of file-view.ts\'s source:'), 'the mutant case, FAILS BEFORE in its title');
  assert.ok(P7.includes('What the census cannot see is what a listed callee does with the body it is handed: that is read by hand when the callee is listed, never derived'), 'and what it cannot see is stated');
  assert.ok(!P7.includes('What the census cannot see is a seat through another name for the body'), 'the round-4 disclosure of the body under another name is history now: an alias and an unlisted callee are refused');
  assert.ok(census.includes('fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-view.ts"), "utf8")'), 'read from the viewer\'s source');
  assert.ok(census.includes('assert.deepEqual(roots, listed, "the roots the viewer seats in the body are the roots the flow lists, no more and no fewer");'), 'held equal to the lists');
  assert.ok(census.includes('assert.equal(bodyReady(bodyOf("div.fileview-unlisted")), false,'), 'the unknown side executed');
  assert.ok(census.includes('for (const c of READY_ROOTS) assert.equal(bodyReady(bodyOf(c, "div.fileview-unlisted")), false,'), 'and beside every content root');
  assert.ok(census.includes('for (const r of NOT_READY_ROOTS) assert.equal(bodyReady(bodyOf(r), "pdf"), r === PDF_LOADER_ROOT,'), 'the PDF kind over each wait root: the loader alone in');
  assert.ok(!census.includes('assert.equal(bodyReady(bodyOf("div.fileview-unlisted")), true,'), 'no case asserts the old fallthrough');
  const viewerText = read('ui', 'webview', 'file-view.ts');
  assert.ok(viewerText.includes("must join the flow's lists (file-print.ts READY_ROOTS, NOT_READY_ROOTS, LINE_ROOTS)") && viewerText.includes("census over this file's seats fails. Its default refuses"), 'the viewer\'s own comment at the install says so (a comment, read as one; round 6: the default refuses)');
  assert.ok(P7.includes('and file-view.ts\'s own comment at the install says so'));
  assert.ok(TESTS.includes('and the census of the body\'s roots (P7: the viewer\'s seating sites read from file-view.ts and resolved to their roots, the set held equal to the flow\'s three lists, `bodyReady` executed over each root as its list says, over an unlisted child alone and beside every content root, not in, and under the PDF kind over each wait and line root, the loader alone in)'));
});

test('Open points 6 and 7 record two pre-existing gate observations, each against the gate\'s source: the origin judgment with the hostname key, and a redirect the gate never reads', () => {
  const gate = code(read('ui', 'webview', 'figure-gate.ts'));
  assert.ok(OPEN.includes('6. The gate judges by origin and keys by hostname (figure-gate.ts `remoteHost`: a URL whose origin is the page\'s own is nobody\'s host, and any other http or https URL is its hostname).'));
  const remote = between(gate, 'export function remoteHost(value: string, base: string): string | null {', '\n}');
  assert.ok(remote.includes('if (own && u.origin === own) return null;'), 'judged by origin');
  assert.ok(remote.includes('return u.hostname.toLowerCase();'), 'keyed by hostname');
  assert.ok(between(gate, 'export function allowedFigureHosts(extra: Iterable<string> = []): Set<string> {', '\n}').includes('for (const h of loadedHosts) s.add(h);'), 'the allowed set is keyed by hostname too');
  assert.ok(OPEN.includes('Loading that host allows every origin on it for the page, since the allowed set is keyed by hostname too (`allowedFigureHosts`).'));
  assert.ok(OPEN.includes('7. A gated host that redirects to a second host. The gate names the host of the URL as written and nothing reads the response'));
  assert.ok(!/\bfetch\(|currentSrc|responseURL|\bResponse\b/.test(gate), 'nothing in the gate reads a response');
  for (const n of ['6.', '7.']) assert.ok(OPEN.includes(n + ' ') && OPEN.includes('Recorded, not fixed.'), 'open point ' + n + ' is recorded, not fixed');
  inOrder(OPEN, ['1. Wording.', '5. Escape with a re-place pending', '6. The gate judges by origin', '7. A gated host that redirects', '8. The figure half of the printable rule', '9. The wait and a figure reached through a paint reference'], 'the open points\' order');
  // round 4: the redirect is counted on both roads and the caveat is stated where the title's contract is (the round-2 review's tests-3 and correctness-4)
  const egress = read('ui', 'webview', 'file-print-egress-browser.test.ts');
  assert.ok(egress.includes('test("(13) a gated host that answers 302 to a second host: Print with them over its placeholder fetches both hosts, one request each'), 'the egress leg\'s case (13)');
  assert.ok(OPEN.includes('file-print-egress-browser.test.ts case (13) counts it since the round-4 fixes (2026-09-20), the same host answering 302 to `https://elsewhere.test/from/r.svg`'));
  assert.ok(OPEN.includes('`withTitle`\'s doc, figure-gate.ts\'s header and the egress leg\'s header state the same.'));
  for (const [file, clause] of [[['ui', 'webview', 'file-print.ts'], 'a host one of them answers with a\n *  redirect to is reached too, as the placeholder\'s own click reaches it'], [['ui', 'webview', 'figure-gate.ts'], 'A host that answers a figure\'s request with a\n// redirect to a second host is reached by the browser'], [['ui', 'webview', 'file-print-egress-browser.test.ts'], 'none for a host the person did not choose BY ITS URL (a host a granted host\'s answer redirects to is reached, on\n// the print and on the click alike, and is named nowhere'],
    // the fourth site, the activate case's comment (round 5: the round-4 review's extra6-1, the one statement of that fetch left without the clause)
    [['ui', 'webview', 'file-print.ts'], 'the figure\'s own fetch and no other, a placeholder naming two hosts fetching from both as its\n        // title said, and no page-life grant for any host (a click\'s meaning, kept for the click: loadGatedHost);\n        // a host one of them answers with a redirect to is reached too, as the placeholder\'s own click reaches it (open point 7;'],
    // the fifth site, the module header's two egress sentences (round 6: the round-5 review's tests-3 and extra5-3), in the pointer form: they name where the
    // requests go and point at loadGatedFigure's doc, the one full statement, rather than carrying a fifth copy of the clause
    [['ui', 'webview', 'file-print.ts'], 'unlisted host unless the person chose it; where a chosen figure\'s requests then go, a redirect its host answers\n//      among them, is stated once, in loadGatedFigure\'s doc, figure-gate.ts)'],
    [['ui', 'webview', 'file-print.ts'], 'so the requests are the ones those figures make and no\n//      other, going where those figures\' URLs point (loadGatedFigure\'s doc, the one full statement of it']]) assert.ok(read(...file).includes(clause), file.join('/') + ' carries the redirect clause (a comment, read as one)');
  // the pointed-at statement, in full, in the one place (a doc comment, read as one)
  assert.ok(read('ui', 'webview', 'figure-gate.ts').replace(/\n \*  /g, ' ').includes('The figure\'s requests go where its URLs point, a redirect followed to a host the print\'s title never names and this never grants (the header).'), 'loadGatedFigure\'s doc states the caveat in full');
  // the plan's twins point at it too (the round-5 review's tests-3: P2\'s reason sentence and P6\'s one-list sentence stood without the caveat, and are pinned)
  assert.ok(P2.includes('so a print never fetches from a host outside the list unless the person chose it (where a chosen figure\'s requests then go, a redirect its host answers among them: `loadGatedFigure`\'s doc, figure-gate.ts, the one full statement, which this sentence and P6\'s point at rather than restate'), 'P2\'s reason sentence points at the full statement');
  assert.ok(P2.includes('so the title and the restores are one list by construction (where those restores\' requests go, a redirect among them: `loadGatedFigure`\'s doc, figure-gate.ts, as in P2)'), 'the one-list sentence points at it');
  assert.ok(!/redirect followed to a host the print\'s title never names/.test(flowRaw0()), 'the header carries the pointer, not a fifth copy of the caveat');
  assert.ok(P2.includes('which `withTitle`\'s doc, figure-gate.ts\'s header and the egress leg\'s header state and file-print-egress-browser.test.ts case (13) counts on both roads: open point 7'));
  // round 4: open point 9, the wait over a paint reference (the round-3 review's extra7-3, not ruled): the three collections and no fourth
  assert.ok(OPEN.includes('9. The wait and a figure reached through a paint reference. `collectPictures` (P2) awaits an `<img>`, a `<video poster>` and an svg `<image>` alone'));
  const collect = between(flow, 'export function collectPictures(body: ParentNode, base: string, probe: (url: string) => Picture): Picture[] {', '\n}');
  assert.ok(!/fill|stroke|filter|clip-path|mask|marker|paintRefs|cssUrls/.test(collect), 'the collection reads no paint reference');
  assert.ok(code(read('ui', 'webview', 'figure-gate.ts')).includes('const PAINT_ATTRS') || code(read('ui', 'webview', 'figure-gate.ts')).includes('paintRefs'), 'the gate has the paint references the open point names');
  assert.ok(OPEN.includes('9. ') && OPEN.slice(OPEN.indexOf('9. The wait')).includes('Recorded, not fixed.'), 'open point 9 is recorded, not fixed');
});

test('P2: the wait\'s line carries the viewer\'s loader after its words, under one rule byte-equal in both sheets and pinned by the parity test', () => {
  assert.ok(P2.includes('Beside the words the line carries the viewer\'s loader, the swirl, the wordmark and the three pulsing dots (`.fileview-load`, the markup file-view.ts\'s waits use, hidden from the status\'s announcement), inline on the words\' row under a rule of its own in both sheets, `.fileview-print-line .fileview-load`'));
  const show = between(flow, 'const showLine = (words: string, loading = false): HTMLElement => {', '\n  };');
  inOrder(show, ['row.textContent = words;', 'if (loading) {', 'load.className = "fileview-load fileview-print-load";', 'load.setAttribute("aria-hidden", "true");', '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>', '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>', 'row.appendChild(load);'], 'the words first, then the loader');
  assert.equal([...flow.matchAll(/showLine\(waitWords\(n\), true\)/g)].length, 1, 'every fresh wait line loads: waitLine\'s one showLine, reached from the wait act and from preparingLine when none stands (the re-aim and the settle\'s second look rewrite a standing one in place)');
  assert.equal([...flow.matchAll(/showLine\((preparingWords|waitingWords|waitWords)\(/g)].length, 1, 'and no wait line without the loader');
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
  // the media paint puts pdfBlock's column in the body, and the flow reads that column as content (div.fileview-pdffall is
  // one of READY_ROOTS); no paint reports anything
  assert.ok(viewer.includes('const shown = isPdf ? pdfBlock(objUrl, path) : imgBlock(objUrl, path, imgFailed);') && viewer.includes('body.replaceChildren(shown);'), 'the media paint');
  const pdfBlock = between(viewer, 'function pdfBlock(objUrl: string, path: string): HTMLElement {', '\n}');
  assert.ok(pdfBlock.includes('const col = el("div", "fileview-pdffall");') && pdfBlock.includes('col.appendChild(frame);') && pdfBlock.includes('return col;'), 'the frame comes in its column');
  assert.equal(viewer.split('print.bodyIn(').length - 1, 0, 'the viewer reports nothing');
  assert.ok(P4.includes('while the pages flow\'s loader alone holds the body, before page 1 is drawn, Print stays live too, since the kind is known to be a PDF (P7\'s one exception) and this road reads nothing from the body, so a press or the chord opens the /file tab at once; over a kept frame under the attempt\'s loader it is live'));
  assert.ok(!P4.includes('Print is disabled (P7)'), 'the disabled pages loader is gone from the record');
  assert.ok(flow.includes('export const READY_ROOTS: readonly string[] = ["div.fileview-md", "div.fileview-code", "div.fileview-imgbox", "div.fileview-pdffall", "div.fileview-pdfhost", "div.fileview-cm"];'), 'the column is a content root');
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
  assert.ok(P2.includes('The placeholders are read at the arm and kept (`armedGates`, re-read at each recount), with the hosts they name (`armedHosts`, `hostsOf`): "with them" restores that list and no other (one no longer in the body is skipped, `host.body.contains`), so the title and the restores are one list by construction'));
  assert.ok(flow.includes('armedGates = gates(); armedHosts = hostsOf(armedGates);') && flow.includes('withTitle(armedHosts)'), 'read at the arm, named in the title');
  const activate = between(flow, 'case "activate": {', 'return;');
  assert.ok(activate.includes('for (const g of armedGates) if (host.body.contains(g)) loadGatedFigure(g);'), 'and restored from that list, one placeholder at a time, a detached one skipped, not the body at the click');
  assert.ok(!activate.includes('gates()') && !activate.includes('hostsOf('), 'the click reads no placeholders or hosts of its own');
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
  assert.ok(TESTS.includes('- ui/webview/file-print-figure-browser.test.ts, headless Chromium, Firefox and WebKit (the round-3 review, 2026-09-20; one case per engine since the round-5 review)') && exists('ui', 'webview', 'file-print-figure-browser.test.ts'), 'the round-4 figure leg is named, in the three engines');
  assert.ok(TESTS.includes('(12) a gated svg at `opacity="0e0"` and a `<picture>` whose `<img>` carries `hidden`, beside a plain placeholder, on three hosts') && TESTS.includes('(13) a gated host that answers 302 to a second host, on two pages'), 'the egress leg\'s cases (12) and (13) are named');
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
  // round 4 (the round-2 review's tests-6): the composition is driven in Chromium, and the record says so
  const armed = read('ui', 'webview', 'file-print-armed-browser.test.ts');
  assert.ok(armed.includes('test("(B) Escape during a pending re-place of a region comment while the bar is armed cancels the re-place alone:'), 'the armed leg\'s re-place case');
  assert.ok(armed.includes('FAILS BEFORE under the lazy-panel mutation (the panel built at its first click, after installFilePrint)'), 'its FAILS BEFORE names the mutation');
  assert.ok(armed.includes('button[data-act="fcreplace"]'), 'over the panel\'s own Re-place control');
  assert.ok(OPEN.includes('Since the round-4 fixes (2026-09-20) file-print-armed-browser.test.ts section (B) drives the composition in Chromium'));
  assert.ok(TESTS.includes('Escape during a pending re-place of a region comment while the bar is armed cancels the re-place alone'), 'the Tests list names it');
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
  // round 4 (the round-2 review's extra7-1): a repaint's re-aim drops the finished probes first, the settle's never
  assert.ok(P2.includes('A REPAINT\'s re-aim (`reaim` under the wait, `recountAsk` under the ask) first drops this press\'s probes already complete (`dropDone`)'));
  assert.ok(P2.includes('never from the settle\'s own re-aim, which would probe a failed URL again at every settle'));
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('test("(3d) a Reload landing during the wait names an svg image URL the press already probed to its end') && read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('test("(13c) the same landing under the deadline\'s ask: the finished probe is dropped and the URL probed again'), 'the driver leg\'s cases (3d) and (13c)');
  assert.ok(TESTS.includes('a Reload landing during the wait that names an svg image URL the press already probed to its end') && TESTS.includes('the same landing under the ask (the count reading one and the ask standing'), 'the Tests list names both');
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

test('P7: the body\'s readiness is derived by the flow from the body\'s children, read through children or childNodes, under an observer constructed only where the document has one, the viewers report nothing, and the button wears aria-disabled and never the property, the bar\'s own rule', () => {
  const ready = between(flow, 'export function bodyReady(body: BodyLike, kind: PrintKind = "document"): boolean {', '\n}');
  assert.ok(ready.includes('for (const c of elementChildren(body)) {'), 'over the element children');
  const kids = between(flow, 'function elementChildren(body: BodyLike): BodyChild[] {', '\n}');
  inOrder(kids, ['if (body.children) return Array.from(body.children);', 'if (body.childNodes) return Array.from(body.childNodes).filter((n) => n.nodeType === 1) as unknown as BodyChild[];', 'return [];'], 'children, else childNodes filtered to elements, else none');
  assert.ok(flow.includes('const ready = (): boolean => bodyReady(host.body, kindNow());'), 'the driver reads its host\'s body through it, under the file\'s kind');
  assert.ok(flow.includes('const kindNow = (): PrintKind => (host.kind ? host.kind() : "document");'), 'the kind as the host reads it now, a document with no host kind');
  assert.ok(flow.includes('const observer = typeof MutationObserver === "function" ? new MutationObserver(onBody) : null;') && flow.includes('if (observer) observer.observe(host.body, { childList: true });'), 'after every paint, through an observer of the body\'s children, constructed only where the document has the API');
  assert.ok(!flow.includes('const observer = new MutationObserver(onBody);'), 'the bare construction is gone');
  assert.ok(viewer.includes('if (typeof ResizeObserver === "function") {'), 'the guard\'s precedent, watchBodyWidth');
  assert.ok(flow.includes('if (ready() !== (state.phase !== "disabled")) onBody();'), 'and at each press, first');
  assert.ok(flow.includes('if (observer) observer.disconnect();'), 'dropped at the close');
  assert.ok(flow.includes('return { button: btn };'), 'the installer hands the host the button alone: no report');
  assert.ok(!flow.includes('bodyIn'), 'the report is gone from the flow');
  assert.equal(viewer.split('print.bodyIn(').length - 1, 0, 'and from the viewer: no paint reports');
  const P7 = part('P7. **', '**Derivations and their unknown cases.**');
  assert.ok(P7.includes('Whether the body is in is DERIVED, read off the body\'s element children by the flow itself (`bodyReady`, exported: a MutationObserver on the body\'s child list feeds the machine\'s `body` event after every paint, and a press reads the body again first'));
  assert.ok(P7.includes('The element children are read through `children`, else through `childNodes` filtered to element nodes'));
  assert.ok(P7.includes('the observer is constructed only where the document has the API (`typeof MutationObserver === "function"`, the guard `watchBodyWidth` puts on ResizeObserver)'));
  assert.ok(P7.includes('Not in: while a `.fileview-load` is a child of the body') && P7.includes('and the kind is a document\'s') && P7.includes('while `textarea.fileview-editor` is a child') && P7.includes('while `.fileview-err` is all the body holds') && P7.includes('or while a child none of the three lists names stands, whatever else does'));
  assert.ok(!P7.includes('The host reports the body through the installer\'s `bodyIn`'), 'the reported design is gone from the record');
  // the press-time read and the PDF exception, each executed by a leg
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driver.includes('test("(14) a press reads the body\'s children before it acts, so a swap in the press\'s own task is seen before the observer runs:'), 'the driver leg\'s case (14)');
  assert.ok(P7.includes('file-print-driver-browser.test.ts case (14) executes the press-time read in both directions'));
  assert.ok(read('ui', 'webview', 'file-view-print-takings-browser.test.ts').includes('a reload with the pages up puts the loader alone in the body with the kind known to be a PDF: the button stays live, and a press and the chord each open the tab at once'), 'the takings leg\'s case 5, its reload leg under the PDF kind');
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('test("bodyReady reads the element children through `children`, else through `childNodes` filtered to elements'), 'the node case for the children read');
  // aria-disabled and never the property: the bar's precedent, textSizeControl's atEnd, whose reason the flow's own comment carries
  const sync = between(flow, 'const syncButton = (): void => {', '\n  };');
  assert.ok(sync.includes('if (off) btn.setAttribute("aria-disabled", "true"); else btn.removeAttribute("aria-disabled");'), 'aria-disabled follows the disabled phase');
  assert.ok(!flow.includes('btn.disabled'), 'the property is never set');
  assert.ok(viewer.includes('const atEnd = (b: HTMLButtonElement, end: boolean) => { if (end) b.setAttribute("aria-disabled", "true"); else b.removeAttribute("aria-disabled"); };'), 'the bar\'s precedent');
  assert.ok(read('ui', 'webview', 'file-view.ts').includes('aria-disabled, not `disabled`: a button that disables under keyboard focus drops it'), 'the precedent\'s stated reason (the source with its comments, since the reason is a comment)');
  assert.ok(P7.includes('and never the `disabled` property: the bar\'s own rule, `textSizeControl`\'s, copied whole with its reason'));
  // the legs
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('test("bodyReady reads the body\'s element children against three closed lists:'), 'the node shapes');
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
  assert.ok(read('ui', 'webview', 'real-viewer-leg.ts').includes('try { browser = await pw[engine].launch(); }') && read('ui', 'webview', 'real-viewer-leg.ts').includes('engine: Engine = "chromium"'), 'in Chromium unless a leg names another engine (round 6)');
});

// ── the derivations' unknown cases, and the population the round ran ──────────────────────────────

test('Derivations and their unknown cases: the paragraph stands between P7 and the Tests, each answer it gives is the source\'s, and each case it names exists', () => {
  const D = part('**Derivations and their unknown cases.**', '**Tests.**');
  const unit = read('ui', 'webview', 'file-print.test.ts');
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  // bodyReady and rootKind: unknown is not in; a stand-in without localName is unknown (isRoot reads localName === tag)
  assert.ok(D.includes('a child none of the three lists names is unknown, and the body is not in over it, whatever stands beside it'));
  assert.ok(between(flow, 'export function bodyReady(', '\n}').includes('if (k === "unknown") return false;'));
  assert.ok(between(flow, 'export function rootKind(', '\n}').includes('return "unknown";'));
  assert.ok(flow.includes('const isRoot = (c: BodyChild, roots: readonly string[]): boolean => roots.some((r) => { const [tag, cls] = r.split("."); return c.localName === tag && c.classList.contains(cls); });'), 'the tag and the class both read: no localName matches no root');
  assert.ok(unit.includes('test("rootKind classes one child by its `<tag>.<class>` against the three lists: content, wait, line, else unknown;'), 'the rootKind case');
  assert.ok(unit.includes('assert.equal(rootKind({ localName: undefined as unknown as string, classList: { contains: () => true } }), "unknown",'), 'the stand-in without localName');
  // the children: neither list, none
  assert.ok(D.includes('a body that reports neither `children` nor `childNodes` has no children the flow can read and is not in'));
  assert.ok(between(flow, 'function elementChildren(', '\n}').includes('return [];'));
  assert.ok(unit.includes('assert.equal(bodyReady(bodyLike({})), false,'), 'the childNodes case executes a body with neither');
  // the observer
  assert.ok(D.includes('a document without `MutationObserver` gets none, and the press\'s own read of the body is what the button\'s dress follows'));
  assert.ok(flow.includes('const observer = typeof MutationObserver === "function" ? new MutationObserver(onBody) : null;'));
  // printable and rendered
  assert.ok(D.includes('where the browser cannot be asked (no `checkVisibility` or `getClientRects`: a stand-in under node, an engine without the API) the walk alone decides, the permissive side there'));
  assert.ok(D.includes('where it can, a placeholder it does not render is not printable, so a hiding the walk does not know falls to not printable, the side against the fetch'));
  assert.ok(between(flow, 'export function rendered(', '\n}').includes('return null;') && between(flow, 'export function printable(', '\n}').includes('return rendered(el) !== false;'));
  assert.ok(unit.includes('test("rendered: the browser\'s own answer where it can be asked (checkVisibility with visibility and opacity read, and at least one client rect), null where it cannot'), 'the rendered case');
  assert.ok(read('ui', 'webview', 'file-print-armed-browser.test.ts').includes('test("(D) the census of the printable rule\'s unknown side:'), 'the armed leg\'s case (D)');
  // figureHidden: the permissive side, named as such
  assert.ok(D.includes('`hidden` and `popover` are read on an HTML element alone, `display` from the value the browser COMPUTES on every element below the figure\'s root and from the author\'s declaration the browser parses for the root and where nothing computes (the round-4 review\'s extra8-3, 2026-09-20), and opacity and visibility from the values the browser COMPUTES, which the gate\'s sheet leaves alone'));
  assert.ok(D.includes('every other kept attribute or value leaves the figure on the paper as far as the flow reads, the PERMISSIVE side'));
  assert.ok(!D.includes('the browser cannot be asked about the figure'), 'the round-2 reason is gone: the computed visibility and opacity are asked');
  const hid = between(flow, 'function offPaper(el: FigureNode, self: boolean, root: FigureNode = el): boolean {', '\n}');
  assert.ok(D.includes('`display` from the value the browser COMPUTES on every element below the figure\'s root and from the author\'s declaration the browser parses for the root and where nothing computes (the round-4 review\'s extra8-3, 2026-09-20)'));
  assert.ok(hid.includes('if (cs === null) return false;'), 'no browser to compute a style (a stand-in): the attributes alone, on the paper otherwise');
  assert.ok(!/transform|clip-path|mask|filter/.test(hid), 'transform, clip-path, mask and filter are not read');
  assert.ok(unit.includes('test("figureHidden under node, where no browser computes a style:'), 'the figureHidden case under node');
  assert.ok(exists('ui', 'webview', 'file-print-figure-browser.test.ts') && read('ui', 'webview', 'file-print-figure-browser.test.ts').includes('for every shape the flow\'s answer equals the browser\'s own answer for the shape\'s ungated twin'), 'the figure leg in Chromium, the computed half');
  // the shape count, ONE pin (the round-5 review's correctness-4 and regression-3: the number stood in five places and a
  // delta updated two): the count is of the rows the leg builds, read here by running its table; one regex over the P2, D
  // and Tests slices finds every copy, and each must be that count. D carries none (it says "every gated shape"), the
  // ledger entry carries none (it points here), so the copies are P2's and the Tests list's, and a row added to the leg
  // reds both at once.
  const rows = figureRows();
  const counts = (slice) => [...slice.matchAll(/\b(\d+) gated shapes?\b/g)].map((m) => Number(m[1]));
  assert.deepEqual({ P2: counts(P2), D: counts(D), TESTS: counts(TESTS) }, { P2: [rows.length], D: [], TESTS: [rows.length] }, 'the shape count, in P2 and the Tests list once each and nowhere else in the section\'s derivations, is the number of rows the leg builds (' + rows.length + ')');
  assert.ok(D.includes('the flow\'s answer equal to the browser\'s for the ungated twin of every gated shape, the spellings of zero among them'), 'D states the rule over every shape and counts none');
  // the history clause beside each copy (the count at the round-3 review, and how many joined since) adds up to the same number
  for (const [name, slice, added] of [['P2', P2, 'more'], ['TESTS', TESTS, 'added']]) {
    const m = slice.match(new RegExp('(\\d+) at the round-3 review(?:,| and) (\\w+) ' + added + ' since the round-4 review'));
    assert.ok(m, name + ' carries the round-3 count and the number added since');
    assert.equal(m[2], WORDS[rows.length - Number(m[1])], name + ': the round-3 count plus the number added since is the count the leg builds');
  }
  assert.ok(unit.includes('assert.equal(figureHidden(media("img", { display: "none" })), false,') && unit.includes('assert.equal(figureHidden(media("picture", { inert: "" })), false,') && unit.includes('assert.equal(figureHidden(media("svg", { opacity: "0.5" })), false,'), 'the permissive answers executed');
  assert.ok(OPEN.includes('8. The figure half of the printable rule answers on the permissive side.'));
  // figurePrintable, collectPictures
  assert.ok(D.includes('both must hold, over every painting element of the figure (`paintsOf`), each with its ancestors up to the root (`shows`)') && D.includes('and a placeholder with no figure inside answers for itself'));
  assert.ok(D.includes('a use of `body` in file-view.ts the census cannot class is refused with its line, never passed (the census\'s mutant case)'), 'the census\'s unknown is in the paragraph');
  assert.ok(unit.includes('test("the census refuses its unknown and derives its population, executed over mutants of file-view.ts\'s source:'), 'the mutant case');
  assert.ok(between(flow, 'export function figurePrintable(', '\n}').includes('return paintsOf(root).some((p) => shows(p, root));'));
  assert.ok(unit.includes('test("figurePrintable under node: a placeholder reaches the paper when it does (printable: the walk and the browser) and a painting element of the figure it wraps shows'), 'the figurePrintable case');
  assert.ok(unit.includes('test("collectPictures reads the browser\'s answer through printable too:'), 'the collectPictures case over the browser\'s answer');
  // step under the ask
  assert.ok(D.includes('a `stalled` with nothing loading disarms and rests, never prints'));
  assert.ok(flow.includes('if (ev.kind === "stalled") return ev.pending > 0 ? ask(ev.pending) : { state: RESTING, act: "disarm" };'));
  assert.ok(driver.includes('test("(13) a repaint under the deadline\'s ask never prints:'), 'the driver leg\'s case (13)');
  // isPrintKeys
  assert.ok(D.includes('every key or modifier set it does not name is not the chord and is left to the browser, so the flow prevents no key it does not know'));
  assert.ok(unit.includes('test("isPrintKeys enumerates the chord\'s keys and answers false for every other key or modifier set'), 'the isPrintKeys case');
  // pdfFrameWindow and the kind
  assert.ok(D.includes('no frame, a withheld window, a window left at about:blank, a `print` that is no function or a window that throws answer null, and the press takes the tab road'));
  const pdf = between(flow, 'export function pdfFrameWindow(body: ParentNode): FrameWindow | null {', '\n}');
  assert.ok(pdf.includes('if (!frame) return null;') && pdf.includes('if (!w || typeof w.print !== "function") return null;') && pdf.includes('return holds ? w : null;') && pdf.includes('} catch { return null; }'), 'null on every unknown');
  assert.ok(unit.includes('test("pdfFrameWindow: the frame\'s window when it holds the PDF and can print; null with no frame, a withheld window, a window left at about:blank, a print that is no function, or a window that throws"'), 'the pdfFrameWindow case');
  assert.ok(D.includes('a press with no kind, the URL viewer\'s, is a document\'s'));
  assert.ok(flow.includes('const kindNow = (): PrintKind => (host.kind ? host.kind() : "document");'));
  assert.ok(unit.includes('assert.equal(step(RESTING, { kind: "press", gated: 0, pending: 0 }).act, "print", "a press with no kind is a document\'s");'), 'the PDF kind case executes the absent kind');
  // withTitle over none
  assert.ok(D.includes('with no host known the title names "those hosts"'));
  assert.ok(driver.includes('assert.equal(withTitle([]), "Load the pictures from those hosts, then print");'), 'the driver module\'s node case');
});

test('Tests: the population of node modules that drive the real viewer over the stand-ins is the listing the section names, recomputed here, and the run\'s readings name the head they were read at', () => {
  const m = /the (\d+) that `grep -l 'openFileView\\\|openUrlView' ui\/webview\/\*\.test\.ts \| grep -v browser` lists/.exec(TESTS);
  assert.ok(m, 'the section names the listing and counts it');
  const pop = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /\.test\.ts$/.test(f) && !f.includes('browser') && /openFileView|openUrlView/.test(read('ui', 'webview', f)));
  assert.equal(Number(m[1]), pop.length, 'the section says ' + m[1] + '; the listing produces ' + pop.length);
  assert.ok(TESTS.includes('at be1db1ba7, the head before the round\'s fixes, 24 modules and 210 of their 560 cases were red'), 'the run\'s readings, at the head they were read at');
  assert.ok(TESTS.includes('after the guard and the `childNodes` read, 560 of 560'));
  // round 4 (the round-3 review's extra8-1 and extra8-2): the break's class is narrowed, the two text-only suites are not cited as support, and the second red of the same push is named
  assert.ok(TESTS.includes('A construction-time break that reads a browser API the stand-ins lack shows only in a module that opens the viewer over such a stand-in'));
  assert.ok(!TESTS.includes('the standing suites named above that name the viewer, file-view.test.ts and pdf-new-tab.test.ts, were green in the same run'), 'the two suites are not cited as support');
  for (const f of ['file-view.test.ts', 'pdf-new-tab.test.ts']) assert.ok(!/import[^;]*from "\.\/file-view";/.test(read('ui', 'webview', f)) && !read('ui', 'webview', f).includes('installFilePrint('), f + ' constructs no viewer: it imports nothing from file-view and reads its source as text');
  assert.ok(TESTS.includes('ui/test-dom-shim.test.ts\'s edge ratchet, tripped by this slice\'s own `node` stand-in in file-print-armed-browser.test.ts, added at ee9cd84fa with an enumerable `parentElement` edge and closed at 7eb22aeff with `hideEdges`'));
  assert.ok(read('ui', 'webview', 'file-print-armed-browser.test.ts').includes('hideEdges({ localName, parentElement: parent, hasAttribute: (n) => attrs.includes(n) })'), 'the stand-in is built through hideEdges');
  assert.ok(read('ui', 'test-dom-shim.test.ts').includes('ratchet:'), 'the ratchet the paragraph names');
});

// ── round 4: the editor's exit reaches neither the wait nor the ask (the round-3 review's correctness-5) ─────────────

test('P2: entering the editor seats the viewer\'s loader before the editor is up, which takes the body out and disarms, so the editor\'s exit is no repaint under the wait or the ask, and the record no longer names it as one', () => {
  const enter = between(viewer, 'const enterEdit = () => {', 'editorChunk().then((ed) => {');
  inOrder(enter, ['editing = true; dirty = false;', 'const wait = el("div", "fileview-load");', 'body.replaceChildren(wait);'], 'enterEdit: the loader seated in the body before the chunk is awaited');
  assert.ok(flow.includes('export const NOT_READY_ROOTS: readonly string[] = ["div.fileview-load", "textarea.fileview-editor"];'), 'the loader is a wait root: the body is not in over it');
  assert.ok(flow.includes('if (!ev.in) return s.phase === "disabled" ? { state: s, act: "none" } : { state: DISABLED, act: "disarm" };'), 'and the body going out disarms from every phase');
  assert.ok(P2.includes('entering the editor seats the viewer\'s loader, `enterEdit`\'s `.fileview-load`, which takes the body out and disarms first, so the editor\'s exit lands under no wait'));
  assert.ok(P2.includes('never the editor\'s exit: `enterEdit` seats a `.fileview-load` loader before the editor is up, which takes the body out and disarms the ask, so the exit lands under no ask'));
  assert.ok(!P2.includes('or the editor\'s exit under the ask ran window.print') && !P2.includes('a format pick, the editor\'s exit;'), 'the third road is gone from both lists');
  assert.ok(read('ui', 'webview', 'file-view-print-takings-browser.test.ts').includes('case 2: Edit while armed'), 'the takings leg executes Edit while armed disarming');
});

// ── round 5 (the round-4 review's rulings, 2026-09-20): the button's line, the consent text, the aim's count ──────────

test('P2: the ask\'s line and the open-ended wait\'s line end with the button\'s own sentence, what Print anyway does, and the record says what a still-loading picture prints as, scoped to the shape measured (the round-4 review\'s HIGH 1)', () => {
  assert.ok(P2.includes('"Print anyway" prints at once WITHOUT the pictures still loading: a markdown picture with no declared size prints as a 0 by 0 box, nothing where it was, no gap and no label, and one with width and height as an empty box of that size (measured in Chromium under print media, file-print-driver-browser.test.ts case (15a)'));
  assert.ok(P2.includes('The second sentence of both lines is the button\'s own (`anywayWords`): it stands beside "Print anyway" from the moment the line appears, so the person reads what the press does before pressing, one press and no second click'));
  assert.ok(!P2.includes('the picture as the browser has it') && !P2.includes('as the browser has them'), 'the phrase the measurement refuted is gone from P2');
  assert.ok(P2.includes('a chosen picture still loading printed as nothing where it stood (a markdown picture with no declared size; one with width and height as an empty box of that size), no gap and no label'));
  const raw = read('ui', 'webview', 'file-print.ts');
  assert.ok(!/\(in Chromium an empty box\)/.test(raw), 'the header\'s parenthetical, refuted by measurement, is gone');
  assert.ok(raw.includes('a markdown\n//      picture with no declared size prints as a 0 by 0 box, nothing where it was, no gap and no label; one with width\n//      and height as an empty box of that size'), 'the header says what prints, scoped to the shape measured (a comment, read as one)');
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driver.includes('test("(15a) what reaches the paper: under the deadline\'s ask and under Keep waiting\'s open-ended wait, with print media emulated, the parked markdown picture with no declared size has a 0 by 0 box'), 'the driver leg\'s case (15a)');
  assert.ok(driver.includes('await page.emulateMedia({ media });') && driver.includes('assert.deepEqual(p.parked, { w: 0, h: 0 }, site + ", print media: the parked picture with no declared size is a 0 by 0 box'), 'the rect is read under emulated print media');
  assert.ok(driver.includes('pressing it prints once with the parked picture still incomplete and the placeholder on the paper'), 'case (15)\'s title stands: the placeholder\'s box is on the paper (the gated box, not the picture)');
  assert.ok(TESTS.includes('Print anyway printing once with the parked picture incomplete and the placeholder on the paper, the request still parked'), 'and so does the record\'s sentence about it');
  assert.ok(TESTS.includes('case (15a), what reaches the paper: under the deadline\'s ask and under Keep waiting\'s open-ended wait both lines read, before any press, the count then the button\'s own sentence'));
  assert.ok(read('ui', 'webview', 'file-print-browser.test.ts').includes('assert.equal(b.line, "1 picture has not loaded. Print anyway leaves out any picture still loading.", "the ask\'s line, read before the press'), 'the gated leg reads the ask\'s line before the press');
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('the ask\'s line and the open-ended wait\'s line each end with the button\'s own sentence, what Print anyway does (FAILS BEFORE:'), 'the node test pins the words');
  // the guide says it as the person reads it
  const label = '**Opening a markdown document.**';
  const para = guide.slice(guide.indexOf(label), guide.indexOf('\n\n', guide.indexOf(label))).replace(/\s+/g, ' ');
  assert.ok(para.includes('you are asked whether to print anyway, without the pictures still loading, or keep waiting'), 'the guide\'s ask clause says what Print anyway does');
  assert.ok(P5.includes('print anyway, without the pictures still loading, or keep waiting (P2\'s ask, the third review; the button\'s sentence, the round-4 review\'s HIGH 1)'));
});

// ── round 6 (the round-5 review's ui-1, 2026-09-20): the button's sentence takes no count ─────────────────────────────

test('P2: the sentence beside Print anyway takes no count and names no picture, since a counted picture that lands while the line stands prints; the driver leg\'s case (15b) releases pictures under both lines and reads what prints, and the Tests list names it (the round-5 review\'s ui-1)', () => {
  assert.ok(flow.includes('export function anywayWords(): string {'), 'anywayWords takes no argument');
  assert.ok(!flow.includes('anywayWords(n)') && !flow.includes('export function anywayWords(n: number)'), 'and no caller hands it the count');
  assert.equal([...flow.matchAll(/\+ " " \+ anywayWords\(\)/g)].length, 2, 'the ask\'s line and the open-ended wait\'s line end with it, and no other line does');
  assert.ok(!flow.includes('"Print anyway prints without it."') && !flow.includes('"Print anyway prints without them."'), 'the round-5 sentence is gone from the module');
  assert.ok(P2.includes('The sentence takes no count and names no picture (the round-5 review\'s ui-1, 2026-09-20): the line\'s count is the aim\'s and does not fall as pictures land, and a picture that lands while the line stands prints, so the round-5 wording, "Print anyway prints without them.", was false from that landing on; file-print-driver-browser.test.ts case (15b) releases pictures under both lines and reads what prints.'));
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driver.includes('test("(15b) a picture that lands while the line stands prints, and the line\'s last sentence stays true of it:'), 'the driver leg\'s case (15b)');
  inOrder(between(driver, 'test("(15b) a picture that lands while the line stands prints', '\n});'), ['await s.release([SLOW, SLOW2]);', '{ phase: "stalled", line: STALLED_TWO, buttons: [ANYWAY_WORDS, KEEP_WORDS], prints: 0 }', 'const askLine = b.line!;', 'await page.click(ANYWAY_BTN);', 'assert.deepEqual(p[0].incomplete, [], "every <img> complete at the print', 'assert.ok(askLine.endsWith(" " + SENTENCE)', 'await page.click(KEEP_BTN);', 'await s.release([SLOW]);', '{ phase: "preparing", line: waitingWords(2), buttons: [ANYWAY_WORDS], prints: 0 }', 'assert.equal(p[0].incomplete.length, 1', 'assert.ok(waitLine.endsWith(" " + SENTENCE)', 'await s.release([SLOW, SLOW2]);', 'await printsReach(page, 1);'], 'case (15b): both released under the ask, the line read before the press and held against a print with every picture complete; one released under Keep waiting, the print with one still loading; both released under Keep waiting, the settle\'s print');
  assert.ok(TESTS.includes('Since the round-5 review (2026-09-20), case (15b), a picture that lands while the line stands prints, and the sentence stays true of it'), 'the Tests list names case (15b)');
  assert.ok(read('ui', 'webview', 'file-print.test.ts').includes('assert.equal(anywayWords.length, 0, "the sentence takes no count'), 'the node test pins the arity');
});

test('P2, P6, open point 8 and the guide carry the figure-level grant sentence: the restore is the whole figure\'s, so a remote URL inside a non-painting element of a painting figure is counted, named and fetched (the round-4 review\'s HIGH 2, a consent-text correction), and the code road is recorded as needing an owner', () => {
  assert.ok(P2.replace(/\n/g, ' ').includes('The restore is the WHOLE figure\'s: the browser may fetch any URL the figure names, a remote URL inside a non-painting element of a figure that paints among them'), 'P2 (read with its wraps collapsed)');
  assert.ok(P2.replace(/\n/g, ' ').includes('which of them the browser fetches is its own (the round-5 fix, 2026-09-20: "every URL is fetched" over-promised the egress, since a `<picture>` fetches one of its two)'), 'P2 says which URLs are fetched is the browser\'s own');
  assert.ok(!P2.includes('every URL the figure names is fetched'), 'the round-5 over-promise is gone from P2');
  assert.ok(P2.includes('A placeholder is counted, named and restored only when its figure paints (`figurePrintable`, below), and that is what the grant covers (the round-4 review\'s HIGH 2, 2026-09-20, a consent-text correction'));
  const P6 = part('P6. **', 'P7. **');
  assert.ok(P6.replace(/\n/g, ' ').includes('The restore is the whole figure\'s, so a placeholder whose figure paints may have any URL the figure names fetched, a remote URL inside a non-painting element among them, for something never on the paper; which the browser fetches is its own, measured per shape in file-print-figure-browser.test.ts (P2; the round-4 review\'s HIGH 2, 2026-09-20; open point 8)'), 'P6 (read with its wraps collapsed)');
  assert.ok(!P6.includes('every URL the figure names fetched'), 'the round-5 over-promise is gone from P6');
  assert.ok(OPEN.includes('And the answer is the FIGURE\'s: when one painting element shows, `loadGatedFigure` restores every moved attribute of the root and of its descendants, so a remote URL inside a non-painting element of a painting figure'));
  assert.ok(OPEN.includes('is counted, its host named in the title and its URL fetched, for something never on the paper (the round-4 review\'s HIGH 2, 2026-09-20, a consent-text correction'));
  assert.ok(OPEN.includes('give `loadGatedFigure` the paint predicate and restore only the refs whose owning element passes `shows()`, with the video row moved to NOT_ON_PAPER as the fails-before') && OPEN.includes('Not this PR\'s work. Recorded, not fixed.'), 'the code road, recorded as the better shape needing an owner');
  // the code says the same where the grant is described, and its behaviour is the figure-level one
  const gateRaw = read('ui', 'webview', 'figure-gate.ts');
  assert.ok(gateRaw.includes('The restore is the FIGURE\'s, not a painting element\'s:') && gateRaw.includes('is fetched for something that is never on the paper'), 'loadGatedFigure\'s docstring (a comment, read as one)');
  const one = between(code(gateRaw), 'export function loadGatedFigure(wrap: Element): boolean {', '\n}');
  assert.ok(one.includes('restore(wrap);') && !/shows|offPaper|paints/.test(one), 'the restore is the whole figure\'s: no paint predicate in loadGatedFigure (the code road is deferred by the ruling)');
  const flowRaw = read('ui', 'webview', 'file-print.ts');
  const flowOneLine = flowRaw.replace(/\n\/\/\s+/g, ' ');   // the header, its hard wraps collapsed, so a rewrap cannot red a sentence that stands (round 5)
  assert.ok(flowOneLine.includes('The restore is the WHOLE figure\'s: the browser may fetch any URL the figure names, a remote URL inside a non-painting element of a figure that paints among them') && flowOneLine.includes('which of them it fetches is the browser\'s own (a <picture> fetches the <source> it picks and not its <img>\'s src), measured per shape in file-print-figure-browser.test.ts'), 'the header (a comment, read as one)');
  assert.ok(!flowOneLine.includes('every URL the figure names is fetched'), 'the round-5 over-promise is gone from the header');
  assert.ok(!flowRaw.includes('a print fetches from one only for a picture that is on the paper'), 'the sentence that promised less than the code performs is gone');
  assert.ok(read('ui', 'webview', 'figure-gate.test.ts').includes('test("loadGatedFigure restores the FIGURE, painting or not: an svg <image> under <defs> beside one that paints gets its href back too'), 'the gate\'s node case pins the behaviour and the sentences');
  const fig = read('ui', 'webview', 'file-print-figure-browser.test.ts');
  assert.ok(fig.includes('name: "svg>image[a]+defs>image[b]"') && fig.includes('fetches: ["a", "b"]') && fig.includes('name: "picture>source[a]+img[b]"') && fig.includes('fetches: ["a"]'), 'the figure leg holds the fetched URLs per shape, two hosts among them');
  assert.ok(TESTS.includes('a second oracle keyed on the URL, every placeholder whose figure paints restored the way "Print with them" restores it (`loadGatedFigure`, one at a time) and the remote URLs the page then asks for held per shape equal to the table\'s `fetches` column'));
  assert.ok(TESTS.includes('every one of 83 gated shapes built twice on one page (74 at the round-3 review, nine added since the round-4 review, below)'));
  // the two-URL qualifier (the round-5 review's regression-5 and extra6-4): the number of added shapes with two URLs is
  // derived from the rows the leg builds whose html takes the second URL, not spelled by hand (the `fetches:` column no
  // longer marks them alone: since the round-6 Firefox fix two one-URL rows carry it per engine), and the ninth is the
  // display read below the root, the one added row with one URL
  const twoUrl = figureRows().filter((r) => r.html('URL', 'URL2').includes('URL2'));
  assert.ok(twoUrl.length >= 2 && twoUrl.length < WORDS.length, 'two-URL rows exist and their count has a word: ' + twoUrl.length);
  assert.ok(twoUrl.every((r) => r.fetches !== undefined), 'every two-URL row carries a measured `fetches` column');
  assert.ok(TESTS.includes('over ' + WORDS[twoUrl.length] + ' added shapes with two URLs on two hosts, and a ' + ORDINALS[twoUrl.length + 1] + ' for the display read below the root: an svg image beside an image, beside one at opacity zero, beside one under `<defs>`, beside one at display none, and a sheet-hidden group over an image beside an image'), 'the Tests list counts the two-URL shapes as the leg builds them (' + twoUrl.length + ') and the one-URL addition as the next');
  assert.ok(!TESTS.includes('over nine added shapes with two URLs'), 'the count that enumerated eight and said nine is gone');
  assert.ok(TESTS.includes('A node case in the same module holds `paperMismatches`, the leg\'s disagreement message, to name each disagreeing shape with its own expected value'));
  assert.ok(fig.includes('function paperMismatches(rows: Array<{ name: string; twinPaints: boolean | null }>, expected: boolean[]): string[] {'), 'the message carries the expectation with the row');
  // the guide's consent clause
  const label = '**Opening a markdown document.**';
  const para = guide.slice(guide.indexOf(label), guide.indexOf('\n\n', guide.indexOf(label))).replace(/\s+/g, ' ');
  assert.ok(para.includes('when you choose **Print with them**, which loads each of those figures whole, hidden parts included;'), 'the guide\'s consent clause carries the figure-level rule');
  assert.ok(P5.includes('which loads each of those figures whole, hidden parts included (P2\'s figure-level rule, the round-4 review\'s HIGH 2, 2026-09-20)'));
  // the egress leg drives the figure-off class on a host shared with a printable placeholder (tests-4)
  const egress = read('ui', 'webview', 'file-print-egress-browser.test.ts');
  const offNote = between(egress, 'const OFF_NOTE = ', 'Last line.');
  assert.ok(offNote.includes('opacity=\\"0\\"') && offNote.includes('href=\\"https://" + HOST_PLAIN + PLAIN_OFF'), 'OFF_NOTE carries a zero-opacity svg on the plain host');
  assert.ok(!egress.includes('each on a host of its own:'), 'the header no longer says each shape stands on a host of its own');
  assert.ok(TESTS.includes('and since the round-4 review\'s tests-4 (2026-09-20) a gated svg at `opacity="0"` on the plain placeholder\'s own host'));
});

test('P2: the wait\'s count is the aim\'s and does not fall as pictures settle, stated for the timed and the open-ended line (the round-4 review\'s extra7-2), and no per-settle callback was added', () => {
  assert.ok(P2.includes('N is the count at the aim (the press, a choice, or a re-aim after a repaint or a settle) and does not fall as pictures settle, since the wait\'s promise resolves once, when every picture it listened on has settled, so a line over three pictures reads three until the last lands, and Keep waiting\'s open-ended line has the same property'));
  const settle = between(flow, 'export function settlePictures(', '\n}');
  assert.ok(!/onSettle|onEach|progress/.test(settle), 'settlePictures reports no per-settle event');
  assert.ok(read('ui', 'webview', 'file-print.ts').includes('N is the count at the AIM (the press, a choice, or a re-aim after a\n//      repaint or a settle), not a count that falls as each picture settles'), 'the header states the property (a comment, read as one)');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('"one of two pictures landed: the count is the aim\'s and does not fall per settle; nothing printed"'), 'the driver leg reads the count after one of two settles');
});

// ── the post-filter index: the population, derived, not recalled ──────────────────────────────────

/** The print follow-on's test modules under ui/webview: the `ls ui/webview/file-print*.test.ts` listing the Tests paragraph
 *  names, the gate's node module, the takings leg and the legs' shared harness. Read from the directory, so a module added
 *  under the pattern joins the census on its own. */
const printTestModules = () => [...fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /^file-print.*\.test\.ts$/.test(f)), 'figure-gate.test.ts', 'file-view-print-takings-browser.test.ts', 'real-viewer-leg.ts'].sort();
/** Every `.filter(...).map((row, i) => ...)` chain in `src` by its syntax: a map whose callback declares an index, over a
 *  filter's result (a `!` or parentheses between them unwrapped), so `i` counts the rows the filter KEPT and no longer names
 *  the row of any table the callback indexes. Each as `line: text`. */
function postFilterIndexChains(name, src) {
  const sf = tsc.createSourceFile(name, src, tsc.ScriptTarget.Latest, true, tsc.ScriptKind.TS);
  const out = [];
  const unwrap = (n) => { while (tsc.isNonNullExpression(n) || tsc.isParenthesizedExpression(n)) n = n.expression; return n; };
  const walk = (n) => {
    if (tsc.isCallExpression(n) && tsc.isPropertyAccessExpression(n.expression) && n.expression.name.text === 'map') {
      const fn = n.arguments[0];
      const recv = unwrap(n.expression.expression);
      const indexed = fn !== undefined && (tsc.isArrowFunction(fn) || tsc.isFunctionExpression(fn)) && fn.parameters.length >= 2;
      const afterFilter = tsc.isCallExpression(recv) && tsc.isPropertyAccessExpression(recv.expression) && recv.expression.name.text === 'filter';
      if (indexed && afterFilter) out.push((sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1) + ': ' + n.getText(sf));
    }
    tsc.forEachChild(n, walk);
  };
  walk(sf);
  return out;
}
/** The chains sanctioned by hand, each the executed record of the defect inside the node case that holds the helper
 *  replacing it, keyed by module and by the chain's exact text (a line number would move). */
const POST_FILTER_INDEX_RECORDS = [
  { file: 'file-print-figure-browser.test.ts', text: 'rows.filter((r, i) => r.twinPaints !== expected[i]).map((r, i) => r.name + ": the browser paints the twin " + r.twinPaints + ", the leg expected " + expected[i])', why: 'paperMismatches\' fails-before record (the round-4 review\'s correctness-4)' },
  { file: 'file-print-figure-browser.test.ts', text: 'restored.filter(holds).map((_, i) => names[i])', why: 'namesWhere\'s fails-before record (the round-5 review\'s correctness-3)' },
];

test('the post-filter index (the round-4 review\'s correctness-4, tests-7 and regression-3; the round-5 review\'s correctness-3, tests-2, regression-2 and extra7-1, one defect filed seven times): a census over the print test modules by syntax finds every filter-then-map-by-index chain, passes the two fails-before records by their exact text and refuses any other with its module and line; a named helper stands at each site the records replaced', () => {
  const modules = printTestModules();
  assert.ok(modules.length >= 9 && modules.includes('file-print-figure-browser.test.ts'), 'the listing is the follow-on\'s: ' + modules.join(', '));
  const refused = [], found = [];
  for (const file of modules) {
    for (const chain of postFilterIndexChains(file, read('ui', 'webview', file))) {
      const text = chain.slice(chain.indexOf(': ') + 2);
      const record = POST_FILTER_INDEX_RECORDS.find((r) => r.file === file && r.text === text);
      if (record) found.push(record); else refused.push(file + ':' + chain);
    }
  }
  assert.deepEqual(refused, [], 'a filter-then-map-by-index chain the census has not read by hand: a message built from it names a row other than the one that failed (namesWhere or paperMismatches carry the row with its name)');
  assert.deepEqual(found.map((r) => r.text).sort(), POST_FILTER_INDEX_RECORDS.map((r) => r.text).sort(), 'each sanctioned record stands once, none stale');
  assert.equal(found.length, 2, 'the population of the class at the round-6 head: the two records, no live chain');
  // the two records are executed as FAILS BEFORE inside the node cases that hold the helpers
  const fig = read('ui', 'webview', 'file-print-figure-browser.test.ts');
  assert.ok(fig.includes('function namesWhere<T>(rows: readonly T[], names: readonly string[], holds: (row: T) => boolean): string[] {'), 'the helper carries the name and the row through the filter');
  assert.ok(fig.includes('return rows.map((r, i) => ({ r, name: names[i] })).filter((x) => holds(x.r)).map((x) => x.name + " " + JSON.stringify(x.r));'), 'the row is paired with its name BEFORE the filter');
  assert.ok(fig.includes('assert.deepEqual(namesWhere(restored, rows.map((r) => r.name), (r) => r.printableAtRestore === true && r.restored !== true), [], "every placeholder whose figure paints was restored (each named with what the restore read)");'), 'the restore assert reads through the helper');
  assert.ok(!fig.includes('.map((_, i) => rows[i].name)'), 'the chain that named the first shape for any failure is gone');
  for (const r of POST_FILTER_INDEX_RECORDS) assert.ok(fig.slice(fig.indexOf(r.text)).slice(0, 600).includes('FAILS BEFORE, kept as the record of the defect'), r.why + ' is followed by its FAILS BEFORE assertion');
  assert.ok(TESTS.includes('A second node case holds `namesWhere`, the restore assert\'s message, the same way'), 'the Tests list names the second helper');
  assert.ok(TESTS.includes('the record test\'s census over the print test modules refuses every filter-then-map-by-index chain but the two cases\' fails-before records'), 'and the census');
});

// ── the retired sentence: the population of both spellings, derived once ────────────────────────

/** The lines of the print test modules that still carry either spelling of the sentence the product retired (the round-5
 *  review's tests-4, regression-6, extra5-2, extra6-1 and extra6-2): "as the browser has it/them", which the round-4
 *  measurement refuted for a still-loading picture (it prints as nothing where it was, or an empty box of its declared size),
 *  and the bare quoted wait line `"Waiting for 1 picture…"` closing right after the ellipsis, the line before the button's
 *  own sentence joined it. Each as `file:line: text`. */
function retiredSpellings() {
  const out = [];
  for (const file of printTestModules()) {
    read('ui', 'webview', file).split('\n').forEach((text, i) => {
      if (/as the browser has (it|them)/.test(text) || /Waiting for 1 picture…\\?"/.test(text)) out.push({ file, line: i + 1, text });
    });
  }
  return out;
}
/** The sites sanctioned by hand, each keyed by module and by a fragment of its line, with the sense that keeps it. */
const RETIRED_SPELLING_KEEPS = [
  { file: 'file-print-egress-browser.test.ts', has: '"figure-off": in the open body with a figure the browser paints nothing of, read as the browser has it, the figure\'s', why: 'a different sense: how the flow reads the gated figure\'s computed state, not what a picture prints as' },
  { file: 'file-print.test.ts', has: 'assert.equal(s.pending(), 2, "both still loading: they print as the browser has them");', why: 'the machine\'s count case: at that instant both are still loading, and the round-5 ruling leaves it' },
  { file: 'file-print.test.ts', has: 'assert.ok(!ANYWAY_TITLE.includes("as the browser has it"),', why: 'the absence pin\'s own probe string' },
];

test('the retired sentence (the round-5 review\'s tests-4, regression-6, extra5-2, extra6-1 and extra6-2, one defect in five titles and messages): a census over the print test modules for both spellings finds exactly the three kept sites, each read by hand for its sense, and the five corrected sites quote or derive the current line', () => {
  const found = retiredSpellings();
  const kept = found.map((f) => RETIRED_SPELLING_KEEPS.find((k) => k.file === f.file && f.text.includes(k.has)) || null);
  assert.deepEqual(found.filter((f, i) => kept[i] === null).map((f) => f.file + ':' + f.line + ': ' + f.text.trim().slice(0, 120)), [], 'a title or a message quotes a sentence the product no longer produces, so a red would contradict the assertion that failed');
  assert.deepEqual(kept.filter((k) => k !== null).map((k) => k.has).sort(), RETIRED_SPELLING_KEEPS.map((k) => k.has).sort(), 'each kept site stands once, none stale');
  assert.equal(found.length, 3, 'the population at the round-6 head: the three kept sites (five live sites were corrected)');
  // the corrected sites: the two titles derive the wait line from waitingWords(1), so the ui-1 wording and any later one flow into them
  const gated = read('ui', 'webview', 'file-print-browser.test.ts');
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  const egress = read('ui', 'webview', 'file-print-egress-browser.test.ts');
  assert.ok(gated.includes('Print anyway prints once with the picture still loading and left off the paper; Keep waiting sets no timer, its line reading " + JSON.stringify(waitingWords(1)) + " with Print anyway alone'), 'case 4\'s title');
  assert.ok(driver.includes('after Keep waiting the line reads " + JSON.stringify(waitingWords(1)) + " beside the loader with Print anyway alone (FAILS BEFORE: the line read \\"Preparing 1 picture…\\" with no button'), 'case (15)\'s title, its FAILS BEFORE clause standing');
  assert.equal([...egress.matchAll(/"the parked picture prints still loading and left off the paper"/g)].length, 2, 'the two Print anyway roads\' messages');
  assert.ok(egress.includes('"the open picture prints still loading and left off the paper (incomplete), the three placeholders standing"'), 'the four-host road\'s message');
});
