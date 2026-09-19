// The plan's print follow-on (plans/markdown-viewer.md, "## Follow-on: Print (2026-09-19)") records what the print
// build did, and its review rounds changed the flow after the record was written: the chord yields to a key the
// dashboard's command palette already claimed, a held chord's repeats are prevented and not pressed, four Escapes are
// left to the control they belong to while the bar is armed, the machine gained the disabled phase and the body and
// recount events, the wait is re-aimed at a repainted body under the press's deadline, the armed line is recounted at a
// repaint and at a placeholder the person activates by hand and its "Print with them" loads the hosts its title named,
// the line's word buttons hand the keyboard back to the Print button, the wait's line carries the viewer's loader, and
// two browser legs joined the follow-on. tools/markdown-viewer-plan-print.test.mjs holds the first
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
  assert.ok(escape.includes('if (state.phase !== "armed" || ownsEscape(e.target, host.card) || host.typing()) return;'), 'then the three gates, before the disarm');
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

test('P2: the machine\'s phases and events are the record\'s: five phases with disabled, and the body and recount events beside the six', () => {
  assert.ok(flow.includes('export type PrintPhase = "disabled" | "resting" | "armed" | "preparing" | "printing";'));
  assert.ok(P2.includes('a pure function over a state (disabled, resting, armed, preparing, printing; the first is P7\'s) and an event (press, escape, choose, prepare, ready, printed, the host\'s body report, P7\'s `body`, and the driver\'s `recount` after a repaint under the armed line)'));
  const events = between(flow, 'export type PrintEvent =', ';\n');
  for (const k of ['press', 'escape', 'choose', 'prepare', 'ready', 'printed', 'body', 'recount']) assert.ok(events.includes('{ kind: "' + k + '"'), 'the event ' + k);
  assert.equal([...events.matchAll(/\{ kind: "/g)].length, 8, 'and no other');
});

test('P2: the wait is re-aimed at a repaint and at each settle under the press\'s deadline, and the armed line is recounted at a repaint', () => {
  assert.ok(P2.includes('The wait is aimed at the body as it stands and re-aimed in two cases'));
  assert.ok(P2.includes('Both re-aims run under the deadline the press set, never past it'));
  assert.ok(flow.includes('waitEnds = Date.now() + settleMs;'), 'the press sets the deadline');
  assert.ok(flow.includes('aimWait(Math.max(0, waitEnds - Date.now()))'), 'a re-aim keeps it');
  assert.ok(flow.includes('const more = aimWait(left);'), 'the settle reads the body again under the time left');
  assert.deepEqual([...flow.matchAll(/\bwaitEnds = [^;]*;/g)].map((m) => m[0]), ['waitEnds = 0;', 'waitEnds = Date.now() + settleMs;'], 'the declaration and one writer of the deadline: nothing extends it');
  const bodyIn = between(flow, 'const bodyIn = (present: boolean): void => {', '\n  };');
  inOrder(bodyIn, ['feed({ kind: "body", in: present });', 'if (!present) return;', 'if (state.phase === "armed") feed({ kind: "recount", gated: gates().length });', 'else if (state.phase === "preparing") reaim();'], 'the host\'s body report');
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

test('P2: the wait\'s line carries the viewer\'s loader after its words, under one rule byte-equal in both sheets and pinned by the parity test', () => {
  assert.ok(P2.includes('Beside the words the line carries the viewer\'s loader, the swirl, the wordmark and the three pulsing dots (`.fileview-load`, the markup file-view.ts\'s waits use, hidden from the status\'s announcement), inline on the words\' row under a rule of its own in both sheets, `.fileview-print-line .fileview-load`'));
  const show = between(flow, 'const showLine = (words: string, loading = false): HTMLElement => {', '\n  };');
  inOrder(show, ['row.textContent = words;', 'if (loading) {', 'load.className = "fileview-load fileview-print-load";', 'load.setAttribute("aria-hidden", "true");', '<img src="/media/romp-swirl-glyph.svg" alt=""><span>romp</span>', '<i class="fileview-dot"></i><i class="fileview-dot"></i><i class="fileview-dot"></i>', 'row.appendChild(load);'], 'the words first, then the loader');
  assert.equal([...flow.matchAll(/showLine\(preparingWords\([^)]*\), true\)/g)].length, 3, 'every preparing line loads: the wait act, the re-aim, the settle\'s second look');
  assert.equal([...flow.matchAll(/showLine\(preparingWords\(/g)].length, 3, 'and no preparing line without the loader');
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
  assert.ok(P4.includes('The frame being in is not the frame holding the document: the body is reported in (P7) at the media paint that inserts the frame'));
  assert.ok(P4.includes('The button is not held to the frame\'s load event, since a browser that downloads the PDF instead never fires it'));
  assert.ok(/if \(objUrl === null\) return;[ \t]*\n\s+viewError = null;[ \t]*\n\s+print\.bodyIn\(true\);/.test(viewer), 'the media paint reports the body in before any frame is built (a stripped trailing comment leaves its spaces)');
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
  const drop = between(flow, 'const dropLine = (): void => {', '\n  };');
  assert.ok(drop.includes('const held = !closed && line.contains(doc.activeElement);') && drop.includes('if (held) btn.focus({ preventScroll: true });'), 'the hand-back, not at the close');
  assert.ok(read('ui', 'webview', 'file-print-driver-browser.test.ts').includes('(8) Escape or Enter on the armed line\'s word buttons hands the keyboard to the Print button'), 'the driver leg\'s case (8)');
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
  assert.ok(TESTS.includes('- tests/test_guide_print_palette_chord.py, Python:'));
  assert.ok(TESTS.includes(path.basename(fileURLToPath(import.meta.url)) + ' holds the review rounds\' sentences here to the tree'), 'the section names this pin');
});

test('Open point 1 records the two-host placeholder\'s wording, and open point 5 the re-place Escape collision, which stands in the panel\'s listener', () => {
  assert.ok(OPEN.includes('1. Wording. A gated clip counts as a picture in the armed line, and one placeholder naming two hosts'));
  assert.ok(flow.includes('return n === 1 ? "1 picture from another host is not loaded." : n + " pictures from other hosts are not loaded.";'), 'the words count pictures');
  assert.ok(OPEN.includes('5. Escape with a re-place pending in the Comments panel while the bar is armed.'));
  const fc = code(read('ui', 'webview', 'file-comments.ts'));
  assert.ok(fc.includes('document.addEventListener("keydown", this.escapeReplace, true);'), 'the panel\'s listener, capture phase on the document');
  const esc = between(fc, 'escapeReplace = (ev: KeyboardEvent) => {', '\n  };');
  assert.ok(esc.includes('ev.preventDefault(); ev.stopPropagation();') && esc.includes('this.closeComposer();'), 'cancels the re-place and stops the key');
  assert.ok(!esc.includes('cancelBubble') && !esc.includes('defaultPrevented'), 'and reads no claim by the flow: the collision the open point records stands (a fix here closes the point)');
});

test('Open point 2 says the poster and svg probes run in Chromium too, and the driver leg does run them there', () => {
  assert.ok(OPEN.includes('The poster and svg probes run under node with fakes and, since round 1, in Chromium over the real DOM (file-print-driver-browser.test.ts'));
  assert.ok(!OPEN.includes('not in Chromium'), 'the first build\'s wording is gone');
  const driver = read('ui', 'webview', 'file-print-driver-browser.test.ts');
  assert.ok(driver.includes('(6) a <video poster> and an svg <image href> in the real DOM'), 'the driver leg\'s case (6)');
  assert.ok(driver.includes('const POSTER = ') && driver.includes('const IMAGE = ') && driver.includes('<video poster='), 'over a poster and an svg image');
  assert.ok(read('ui', 'webview', 'real-viewer-leg.ts').includes('pw.chromium.launch('), 'in Chromium');
});
