// The plan's print follow-on (plans/markdown-viewer.md, "## Follow-on: Print (2026-09-19)") records what the print
// build did, and this module holds the record to the tree. The follow-on put a Print glyph button and Ctrl/Cmd+P in
// front of window.print (ui/webview/file-print.ts, called by both viewers in ui/webview/file-view.ts), a rule for a
// picture opened directly in the print block of both sheets, a PDF path through the frame's own print or the /file tab,
// and a disabled state until the body is in; the record names each decision's key sentence, the words the bar shows, the
// two sheet rules, the guide's printing sentence and the test modules. Each of those is read here from its source: the
// section is present once and last, and carries the seven decision heads, the ask, the tests and the open points; the
// flow module exists and both viewers call it where the section says; the words quoted in the section are the module's
// literals; both sheets carry the two rules right after the `.fileview-body` line inside byte-equal print blocks; the
// button starts disabled, wears aria-disabled and never the property, and the flow reads the body's readiness off the body
// itself, the viewers reporting nothing (the third review, 2026-09-19); the guide's
// sentence is the one the section describes, carries the palette clause the reviews settled on, agrees with the Python
// pin of that clause (tests/test_guide_print_palette_chord.py, whose SENTENCE literal is read here, so the two pins cannot
// pull the guide two ways again), and the old sentence is gone; and the module list is two-way (every
// ui/webview/file-print*.test.ts the section's `ls` produces is named in the section and the count the section gives is
// the listing's, read from its sentence rather than fixed here; every test module that claims the follow-on in its own
// text, under ui/webview, tools or tests, is named too; and every module the section names exists, this one included).
// Synthetic: only the repo's own text.
// Run: node --test tools/markdown-viewer-plan-print.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const exists = (...parts) => fs.existsSync(path.join(REPO, ...parts));

const plan = read('plans', 'markdown-viewer.md');
const guide = read('docs', 'guide.md');
const flow = read('ui', 'webview', 'file-print.ts');
const viewer = read('ui', 'webview', 'file-view.ts');
const sheets = { 'styles.css': read('ui', 'webview', 'styles.css'), 'feed.css': read('ui', 'webview', 'feed.css') };

// The section, hard wraps collapsed so an assertion survives a rewrap; it is the last section of the plan.
const HEAD = '## Follow-on: Print (2026-09-19)';
const headAt = plan.indexOf('\n' + HEAD + '\n');
assert.ok(headAt >= 0, 'the follow-on section is in the plan');
assert.equal(plan.indexOf('\n' + HEAD + '\n', headAt + 1), -1, 'the section appears once');
assert.equal(plan.indexOf('\n## ', headAt + 1), -1, 'the follow-on is the last section of the plan');
const section = plan.slice(headAt).replace(/\s+/g, ' ');
// The section's prose alone: code spans are names.
const prose = section.replace(/`[^`]*`/g, '');

/** A string literal's text from the source: the first `"..."` after `marker`. */
function literalAfter(src, marker) {
  const at = src.indexOf(marker);
  assert.ok(at >= 0, marker + ' is in the source');
  const m = /"((?:[^"\\]|\\.)*)"/.exec(src.slice(at + marker.length));
  assert.ok(m, 'a string literal follows ' + marker);
  return m[1];
}
/** A block at-rule, whole: from its head to the first close brace at a line start. */
function blockOf(css, head) {
  const a = css.indexOf(head);
  assert.ok(a >= 0, head + ' is in the sheet');
  const b = css.indexOf('\n}', a);
  assert.ok(b > a, head + ' closes');
  return css.slice(a, b + 2);
}
const PRINT_HEAD = '@media print {';
const RULE_BODY = '.fileview-body { overflow: visible; container-type: inline-size; }';
const RULE_BOX = '.fileview-imgbox { padding: 0; }';
const RULE_IMG = '.fileview-img { max-width: 100%; max-height: 100vh; border-radius: 0; box-shadow: none; }';

// ── the section's shape ─────────────────────────────────────────────────────────────────────────────

test('the section states the ask, what existed, seven decisions, the tests and the open points, in that order, with no em dash', () => {
  const marks = ['The user asked (2026-09-19) for a print from the viewer that carries the file\'s pictures', '**What existed.**', '**Decisions.**',
    'P1. **A Print glyph button in the viewer bar, beside Download and in its shape, and Ctrl/Cmd+P runs the same flow.**',
    'P2. **Over gated placeholders the bar arms instead of printing; then every picture that reaches the paper is awaited, with an ask after 8 s if one is still loading; then window.print.**',
    'P3. **A picture opened directly prints fitted to the page.**',
    'P4. **A PDF prints itself: the frame\'s own print when the frame holds the document, else the /file URL in a new tab and a line saying so.**',
    'P5. **The guide\'s printing sentence.**',
    'P6. **Nothing leaves the machine that did not before.**',
    'P7. **Print is disabled until the body is in.**',
    '**Tests.**', '**Open points for the owner.**'];
  let last = -1;
  for (const m of marks) {
    const at = section.indexOf(m);
    assert.ok(at > last, JSON.stringify(m) + ' follows the mark before it');
    last = at;
  }
  assert.ok(section.includes('this follow-on extends Slice 3\'s item 12, the print sheet'), 'the section names the sheet it extends');
  assert.ok(plan.includes('\n12. *Print.* An `@media print` block at the end of styles.css and feed.css, byte-equal'), 'and item 12 is that sheet');
  assert.ok(section.includes('with the build\'s deliberate departures from that contract recorded as the decisions'));
  assert.ok(!section.includes(String.fromCharCode(0x2014)), 'no em dash (U+2014) in the section');
});

// ── P1: the button and the chord, as the viewers wire them ─────────────────────────────────────────

test('P1: the flow module builds a Print glyph button in Download\'s shape with a capture-phase document keydown listener, and both viewers place it where the section says', () => {
  assert.ok(section.includes('`installFilePrint` in ui/webview/file-print.ts builds the button (`.fileview-btn.fileview-icon.fileview-print`, the printer glyph `ICON_PRINT` in icons.ts drawn in the bar\'s stroke family as Download\'s tray is, the title and aria-label "Print", the bar\'s `data-icon` mark)'));
  assert.ok(flow.includes('btn.innerHTML = ICON_PRINT;'), 'the glyph');
  assert.ok(flow.includes('import { ICON_PRINT } from "./icons";'));
  const icons = read('ui', 'webview', 'icons.ts');
  assert.match(icons, /^export const ICON_PRINT = svg\('/m, 'drawn through the family\'s svg(), as Download\'s tray is');
  assert.match(icons, /^export const ICON_DOWNLOAD = svg\('/m);
  assert.equal(literalAfter(flow, 'btn.className = '), 'fileview-btn fileview-icon fileview-print');
  assert.equal(literalAfter(flow, 'btn.title = '), 'Print');
  assert.ok(flow.includes('btn.setAttribute("aria-label", "Print");'));
  assert.ok(flow.includes('btn.dataset.icon = "1";'), 'the bar\'s glyph mark, as Download carries it');
  assert.ok(viewer.includes('dl.innerHTML = ICON_DOWNLOAD; dl.classList.add("fileview-icon"); dl.dataset.icon = "1";'), 'Download\'s shape, which the section names');
  assert.ok(!/btn\.textContent = /.test(flow), 'no words in the button');
  assert.ok(section.includes('the word widened the bar\'s wrapped action row past the chat modal\'s card at 380px'));
  assert.ok(flow.includes('doc.addEventListener("keydown", onKey, true);'), 'one document keydown listener, capture phase');
  assert.ok(flow.includes('doc.removeEventListener("keydown", onKey, true);'), 'removed by the close hook');
  assert.ok(section.includes('openFileView appends it to the file group right after Download, and openUrlView inserts it before Copy URL'));
  assert.ok(viewer.includes('import { installFilePrint } from "./file-print";'), 'the viewer imports the installer');
  const dl = viewer.indexOf('fileGroup.appendChild(dl);');
  const local = viewer.indexOf('const print = installFilePrint({ card: box, bar, body, typing: typingHere, onClose: (cb) => { closeHooks.push(cb); },', dl);
  const placed = viewer.indexOf('fileGroup.appendChild(print.button);', local);
  assert.ok(dl >= 0 && local > dl && placed > local, 'the local viewer builds the Print button after Download and appends it to the file group');
  assert.ok(!viewer.slice(dl + 'fileGroup.appendChild(dl);'.length, placed).includes('appendChild('), 'and nothing appended between Download and Print');
  assert.ok(viewer.includes('const print = installFilePrint({ card: box, bar, body, typing: typingHere, onClose: (cb) => { closeHooks.push(cb); } });\n  acts.insertBefore(print.button, copy);'), 'the URL viewer inserts it before Copy URL');
  assert.ok(viewer.includes('function typingHere(): boolean {'), 'the typing predicate the section names');
  assert.ok(section.includes('(`typingHere`, beside isTypingTarget in file-view.ts)'));
  assert.ok(flow.includes('if (!doc.body.classList.contains("fileview-open") || !host.card.isConnected || host.typing()) return;'), 'the chord runs only with a file open and no text field focused');
  assert.ok(flow.includes('e.repeat !== true'), 'a key repeat is no chord');
  assert.ok(section.includes('not a key repeat, since a held chord would arm and disarm on alternate repeats'));
});

// ── P2: the words, the wait and the deadline ───────────────────────────────────────────────────────

test('P2: the words the section quotes are the module\'s literals, the deadline is 8 s, the placeholders are restored one by one through loadGatedFigure, and the line is a hidden .fileview-err row', () => {
  const one = literalAfter(flow, 'return n === 1 ? ');
  assert.equal(one, '1 picture from another host is not loaded.');
  assert.ok(section.includes('reading "' + one + '" or "N pictures from other hosts are not loaded."'));
  assert.ok(flow.includes('n + " pictures from other hosts are not loaded."'));
  const withWords = literalAfter(flow, 'export const WITH_WORDS = ');
  const withoutWords = literalAfter(flow, 'export const WITHOUT_WORDS = ');
  assert.ok(section.includes('with **' + withWords + '** and **' + withoutWords + '**; a second press or Escape disarms'));
  assert.ok(flow.includes('return n === 1 ? "Preparing 1 picture…" : "Preparing " + n + " pictures…";'), 'the wait\'s words');
  assert.ok(section.includes('The line reads "Preparing 1 picture…" or "Preparing N pictures…" meanwhile.'));
  assert.ok(flow.includes('export const PRINT_SETTLE_MS = 8000;'), 'the deadline constant');
  assert.ok(section.includes('or at `PRINT_SETTLE_MS`, 8 s, after which the bar asks instead of printing'));
  assert.ok(section.includes('"With them" restores exactly the placeholders it counted, each through `loadGatedFigure` (figure-gate.ts), the gate\'s restore of ONE placeholder'));
  assert.ok(flow.includes('for (const g of armedGates) if (host.body.contains(g)) loadGatedFigure(g);'), 'activate restores each kept placeholder through the gate\'s one-placeholder restore');
  assert.ok(!flow.includes('loadGatedHost('), 'and calls the click\'s host-wide road nowhere (the round-2 review, 2026-09-19)');
  assert.ok(section.includes('the gate is a privacy choice, so a print never fetches from a host outside the list unless the person chose it'));
  assert.ok(flow.includes('row.className = "fileview-err " + PRINT_LINE_CLASS;'), 'the line is a .fileview-err row');
  assert.ok(flow.includes('host.card.insertBefore(row, host.bar.nextSibling);'), 'right under the title bar');
  for (const [name, css] of Object.entries(sheets)) {
    const block = blockOf(css, PRINT_HEAD);
    assert.match(block, /^  [^\n]*\.fileview > \.fileview-err[^\n]* \{ display: none; \}$/m, name + ': the print block hides every .fileview > .fileview-err, the line among them');
  }
  assert.ok(section.includes('which hides every `.fileview > .fileview-err`, keeps the line off the paper'));
  assert.ok(flow.includes('export function setPrintSettleMs(ms: number | null): void'), 'the seam');
  assert.ok(section.includes('`setPrintSettleMs` and `printSettleMs` are the deadline\'s test seam; nothing in the product calls them'));
  assert.ok(!viewer.includes('setPrintSettleMs'), 'the viewer does not call the seam');
  assert.ok(read('ui', 'webview', 'real-viewer-leg.ts').includes('export { setPrintSettleMs, printSettleMs } from "./file-print";'), 'the leg\'s bundle exports it');
});

// ── P3: the picture rule, in both sheets' byte-equal print blocks ──────────────────────────────────

test('P3: both sheets carry the two rules right after the .fileview-body line inside byte-equal print blocks, and the section quotes them as written', () => {
  const blocks = Object.entries(sheets).map(([name, css]) => [name, blockOf(css, PRINT_HEAD)]);
  assert.equal(blocks[0][1], blocks[1][1], 'the print block is byte-equal in styles.css and feed.css (fileview-parity.test.ts pins it too)');
  for (const [name, block] of blocks) {
    assert.ok(block.includes('\n  ' + RULE_BODY + '\n  ' + RULE_BOX + '\n  ' + RULE_IMG + '\n'), name + ': the body line, then the box reset, then the picture cap, each on its own line');
    assert.equal((block.match(/\.fileview-img \{/g) || []).length, 1, name + ': one .fileview-img rule in the block');
  }
  assert.ok(section.includes('right after the `.fileview-body` line: `' + RULE_BOX + '` and `' + RULE_IMG + '`'), 'the section quotes both rules');
  assert.ok(section.includes('The contract asked for the width and height caps; the padding reset, the square corners and the dropped shadow were added by the build.'));
  assert.ok(section.includes('the computed max-height under print media is 700px where the screen reads 574px, and a 400 by 3000 PNG prints as one A4 page'));
  const media = read('ui', 'webview', 'file-print-media-browser.test.ts');
  assert.ok(media.includes('assert.equal(pr.maxHeight, "700px"') && media.includes('assert.equal(s0.maxHeight, "574px"'), 'the browser leg reads those two values');
  assert.ok(media.includes('const PNG_W = 400, PNG_H = 3000;'), 'over a 400 by 3000 picture');
  assert.ok(media.includes('assert.equal(pages, 1,'), 'and counts one page');
});

// ── P4: the PDF path ───────────────────────────────────────────────────────────────────────────────

test('P4: the frame detector reads the document type or the frame\'s own URL and refuses about:blank, the local viewer passes the kind and the opener and the URL viewer neither, and the two lines are the module\'s', () => {
  assert.ok(flow.includes('export function pdfFrameWindow(body: ParentNode): FrameWindow | null {'));
  assert.ok(flow.includes('const holds = (w.document !== null && w.document.contentType === "application/pdf") || (href !== "about:blank" && href === bare(frame.src));'), 'the tightened test');
  assert.ok(section.includes('its document\'s content type `application/pdf` (what Chromium\'s PDF viewer document reports) or the window\'s location the frame\'s own blob URL with any `#page=N` fragment set aside, and `print` a function'));
  assert.ok(section.includes('leaves the window at about:blank, where print is a function too and would print a blank page'));
  assert.ok(viewer.includes('kind: () => (isPdf ? "pdf" : "document"), openTab: () => openFileTab(path, sid), takeKeyboard: () => takeKeyboard() });'), 'the local viewer passes the kind, the opener and its keyboard hand-over');
  assert.equal(viewer.split('installFilePrint(').length - 1, 2, 'two callers');
  assert.equal(viewer.split('kind: () => (isPdf').length - 1, 1, 'one of them passes a kind: the local viewer (the URL viewer\'s call, quoted whole under P1, has none)');
  assert.ok(section.includes('openUrlView passes neither, so the URL viewer\'s flow is a document\'s'));
  const tab = literalAfter(flow, 'export const TAB_WORDS = ');
  const noTab = literalAfter(flow, 'export const NO_TAB_WORDS = ');
  assert.equal(tab, 'Print from the tab that opened.');
  assert.ok(section.includes('a line under the bar reads "' + tab + '", or "' + noTab + '" when the opener answered false'));
  assert.ok(flow.includes('showLine(opened ? TAB_WORDS : NO_TAB_WORDS);'), 'the driver shows one of the two');
  assert.ok(section.includes('The page\'s own window.print never runs for a PDF.'));
  assert.ok(flow.includes('if (ev.file === "pdf") return { state: { phase: "printing", gated: 0, pending: 0 }, act: "printPdf" };'), 'a PDF press is printPdf, never print');
  assert.ok(section.includes('The Comments panel\'s PDF pages are out of scope: with the panel open the body holds the pdf.js canvases and no frame, so Print opens the /file tab'));
  assert.ok(read('ui', 'webview', 'preview.ts').includes('export function openFileTab(path: string, sid?: string | null): boolean {'), 'the opener the section names');
});

// ── P5: the guide ──────────────────────────────────────────────────────────────────────────────────

test('P5: the guide\'s printing sentence is the one the section describes, inside the markdown paragraph, and the old sentence is gone', () => {
  const label = '**Opening a markdown document.**';
  const at = guide.indexOf(label);
  assert.ok(at >= 0, 'the paragraph the section names');
  const para = guide.slice(at, guide.indexOf('\n\n', at)).replace(/\s+/g, ' ');
  const withWords = literalAfter(flow, 'export const WITH_WORDS = ');
  // The first sentence, with the palette clause as the second review reworded it (the first review's "also opens the
  // command palette" read as if the key printed too; in the dashboard the key is the palette's and the bar's button prints);
  // then the gate's sentence with the module's own words; then the PDF's.
  const first = '**Print** in the file\'s bar, or **Cmd+P** on a Mac and **Ctrl+P** elsewhere while a file is open, prints the file alone, black on white, with its pictures loaded, across as many pages as it needs; in the dashboard that key opens the command palette instead (**Escape** closes it), so print from the bar there.';
  const rest = ' Pictures from other hosts are loaded for the print only when you choose **' + withWords + '**; if a picture has not loaded after a few seconds, you are asked whether to print anyway or keep waiting; a PDF prints itself, or opens in a new tab to print from when the browser cannot print it in place.';
  assert.ok(para.includes(first + rest), 'the guide\'s printing sentence, whole: ' + JSON.stringify(para));
  assert.ok(!para.includes('as many pages as it needs. Pictures'), 'the sentence before the palette clause is gone');
  assert.ok(!para.includes('also opens the command palette'), 'and the first review\'s wording, which read as a print too, is gone');
  // The Python pin of the palette clause holds the same first sentence: read its SENTENCE literal (adjacent string
  // pieces inside one pair of parentheses) so a rewording of the guide fails both pins or neither.
  const py = read('tests', 'test_guide_print_palette_chord.py');
  const lit = /\nSENTENCE = \(([\s\S]*?)\)\n/.exec(py);
  assert.ok(lit, 'the Python pin holds the sentence in a SENTENCE literal');
  const pySentence = [...lit[1].matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => m[1]).join('');
  assert.equal(pySentence, first, 'the Python pin and this pin hold the same first sentence');
  assert.ok(!guide.includes('Printing the page while a rendered file is open'), 'the old sentence, which described the browser\'s own print, is gone');
  assert.ok(section.includes('The one sentence in docs/guide.md\'s "Opening a markdown document" paragraph now says that Print in the file\'s bar, or the chord with a file open, prints the file alone, black on white, with its pictures loaded'));
  assert.ok(guide.includes('The printed page\nleaves out the title bar, the Comments panel and the Copy buttons.'), 'the Files chapter\'s sentence the section calls unchanged');
});

// ── P6: nothing new leaves the machine ─────────────────────────────────────────────────────────────

test('P6: the flow module imports the gate alone and fetches nothing itself', () => {
  const imports = [...flow.matchAll(/^import [^;]* from "([^"]+)";/gm)].map((m) => m[1]);
  assert.deepEqual(imports, ['./figure-gate', './icons'], 'two imports: the gate\'s load path and its mark, and the bar\'s glyph family; neither fetches');
  assert.ok(!/\bfetch\(/.test(flow), 'no fetch of its own');
  assert.ok(section.includes('No kernel change, no new route, no server-side render.'));
});

// ── P7: disabled until the body is in ──────────────────────────────────────────────────────────────

test('P7: the flow starts disabled and the body event moves it, the button wears aria-disabled under the sheets\' disabled dress and never the property, the chord is prevented before the press, a disarm cancels the wait, and the readiness is read off the body by the flow, the viewers reporting nothing', () => {
  assert.ok(flow.includes('export const DISABLED: PrintState = { phase: "disabled", gated: 0, pending: 0 };'));
  assert.ok(flow.includes('let state: PrintState = DISABLED;'), 'the driver starts there');
  assert.ok(flow.includes('| { kind: "body"; in: boolean }'), 'the body event');
  assert.ok(flow.includes('if (!ev.in) return s.phase === "disabled" ? { state: s, act: "none" } : { state: DISABLED, act: "disarm" };'), 'out: disabled from every phase, the line dropped');
  assert.ok(flow.includes('return s.phase === "disabled" ? { state: RESTING, act: "none" } : { state: s, act: "none" };'), 'in: rests a disabled flow, changes nothing elsewhere');
  assert.ok(flow.includes('if (off) btn.setAttribute("aria-disabled", "true"); else btn.removeAttribute("aria-disabled");'), 'aria-disabled');
  assert.ok(!flow.includes('btn.disabled'), 'never the property (the bar\'s rule: a button that disables under keyboard focus drops it on the document\'s body)');
  assert.ok(section.includes('The flow starts in a `disabled` phase and the button wears `aria-disabled` and the sheets\' disabled dress'));
  assert.ok(section.includes('and never the `disabled` property: the bar\'s own rule, `textSizeControl`\'s, copied whole with its reason'));
  for (const [name, css] of Object.entries(sheets)) assert.ok(css.includes('.fileview-btn:disabled, .fileview-btn[aria-disabled="true"] { opacity: 0.55; cursor: default; }'), name + ': the disabled dress the section names');
  const chord = flow.indexOf('if (!isPrintChord(e)) return;');
  const prevented = flow.indexOf('e.preventDefault();', chord);
  const pressed = flow.indexOf('press();', prevented);
  assert.ok(chord > 0 && prevented > chord && pressed > prevented, 'the chord is prevented, then pressed, and the disabled phase ignores the press');
  assert.ok(section.includes('a press there changes nothing, and the chord is still prevented, so the browser\'s raw print does not run over the loader either'));
  assert.ok(flow.includes('case "disarm": dropSettle(); dropLine(ev.kind === "body"); break;'), 'a disarm cancels a running wait');
  assert.ok(flow.includes('return { button: btn };'), 'the installer hands the host the button alone');
  // the readiness, read off the body's children by the flow: the observer and the press's own read; the viewers report nothing
  assert.ok(flow.includes('export function bodyReady(body: BodyLike, kind: PrintKind = "document"): boolean {'), 'the exported test of the body, under the file\'s kind');
  assert.ok(flow.includes('export const NOT_READY_ROOTS: readonly string[] = ["div.fileview-load", "textarea.fileview-editor"];') && flow.includes('export const LINE_ROOTS: readonly string[] = ["div.fileview-err"];') && flow.includes('if (k === "unknown") return false;'), 'the loader and the plain fallback editor are the wait roots, the failure line the line root, and a child none of the lists names is not in');
  assert.ok(flow.includes('const observer = typeof MutationObserver === "function" ? new MutationObserver(onBody) : null;') && flow.includes('if (observer) observer.observe(host.body, { childList: true });'), 'after every paint, where the document has the API');
  assert.ok(flow.includes('if (ready() !== (state.phase !== "disabled")) onBody();'), 'and at each press, first');
  assert.equal(viewer.split('print.bodyIn(').length - 1, 0, 'no paint in either viewer reports the body');
  assert.equal(viewer.split('installFilePrint(').length - 1, 2, 'both viewers still install the flow');
  assert.ok(section.includes('read off the body\'s element children by the flow itself (`bodyReady`'));
  assert.ok(section.includes('Not in: while a `.fileview-load` is a child of the body'));
  assert.ok(section.includes('The button is disabled until the body is in (P7).'), 'P1 hands the rule to P7');
});

// ── the tests the section names, two-way ───────────────────────────────────────────────────────────

const NUMBER_WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
/** The test modules under `dir` whose names match `re` and whose own text claims the print follow-on, by the section's
 *  head or by the phrase every leg's header uses; a module that says it tests the follow-on is one the record must name. */
const CLAIM = /print follow-on|Follow-on: Print \(2026-09-19\)/;
const claimants = (dir, re) => fs.readdirSync(path.join(REPO, ...dir)).filter((f) => re.test(f) && CLAIM.test(read(...dir, f))).sort();

test('every ui/webview/file-print*.test.ts is named in the section and the count the section gives is the listing\'s, every module the section names exists, and the section names this module', () => {
  const testsAt = section.indexOf('**Tests.**');
  const tests = section.slice(testsAt);
  const onDisk = fs.readdirSync(path.join(REPO, 'ui', 'webview')).filter((f) => /^file-print.*\.test\.ts$/.test(f)).sort();
  assert.ok(onDisk.length >= 3, 'the follow-on\'s modules are on disk: ' + onDisk.join(', '));
  for (const f of onDisk) assert.ok(tests.includes('ui/webview/' + f), f + ' is named in the Tests list');
  // The section names the command that produces the list and says how many modules it lists; the count is read from
  // the sentence and compared with the listing, so a module added without the sentence following fails here.
  const count = /`ls ui\/webview\/file-print\*\.test\.ts` lists the follow-on's (\w+) modules/.exec(section);
  assert.ok(count, 'the section names the command that produces the list and counts its modules');
  assert.equal(NUMBER_WORDS[count[1]] ?? Number(count[1]), onDisk.length, 'the section says the listing produces ' + count[1] + ' modules; today it produces ' + onDisk.length + ': ' + onDisk.join(', '));
  const named = [...new Set([...section.matchAll(/\b([\w-]+\.test\.(?:ts|mjs))\b/g)].map((m) => m[1]))];
  assert.ok(named.length >= onDisk.length + 9, 'the section names the follow-on\'s modules and the standing suites (' + named.length + ')');
  for (const f of named) {
    const where = f.endsWith('.mjs') ? ['tools', f] : ['ui', 'webview', f];
    assert.ok(exists(...where), f + ' exists under ' + where.slice(0, -1).join('/'));
  }
  for (const f of new Set([...section.matchAll(/\btests\/(test_\w+\.py)\b/g)].map((m) => m[1]))) assert.ok(exists('tests', f), f + ' exists under tests');
  assert.ok(named.includes(path.basename(fileURLToPath(import.meta.url))), 'the section names this pin');
  assert.ok(exists('ui', 'webview', 'file-view-text-size.test.ts'), 'the leg P1 names');
});

test('every test module that claims the print follow-on in its own text is named in the section\'s Tests list: the browser legs outside the file-print* stem and the Python pin among them', () => {
  const tests = section.slice(section.indexOf('**Tests.**'));
  const legs = claimants(['ui', 'webview'], /\.test\.ts$/);
  const pins = claimants(['tools'], /\.test\.mjs$/);
  const py = claimants(['tests'], /^test_\w+\.py$/);
  assert.ok(legs.length >= 4 && pins.length >= 1 && py.length >= 1, 'the claimants are on disk: ' + [...legs, ...pins, ...py].join(', '));
  assert.ok(legs.some((f) => !/^file-print/.test(f)), 'at least one leg lies outside the file-print* stem, which is why this test exists');
  for (const f of legs) assert.ok(tests.includes('ui/webview/' + f), 'ui/webview/' + f + ' claims the follow-on and is named in the Tests list');
  for (const f of pins) assert.ok(tests.includes('tools/' + f), 'tools/' + f + ' claims the follow-on and is named in the Tests list');
  for (const f of py) assert.ok(tests.includes('tests/' + f), 'tests/' + f + ' claims the follow-on and is named in the Tests list');
});
