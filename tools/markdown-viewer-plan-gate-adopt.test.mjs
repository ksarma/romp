// The section "Fix: the gate before adoption (2026-09-20)" of plans/markdown-viewer.md records a privacy hole found by
// the review of the link-navigation follow-on: mdBlock adopted the sanitized nodes into the live document before the
// figure chain ran, and WebKit fetched a gated figure while the gate's placeholder stood. This module holds that
// section's sentences to what the code does: the adoption line in file-view.ts comes after the chain and its comment
// says so; the browser leg the section names exists and reads real servers' request logs through a proxy, never a route;
// the scope facts (the VS Code panes' CSP, the kernel's Referrer-Policy) stand in the files they cite; and the two
// pointers, at Slice 1's fetch-on-render paragraph and the Slice 4 record's item 9, name the section as the one after
// "Out of scope". The section is read from its heading to the next `## ` heading or the end of the plan, and it is held
// to follow "## Out of scope", not to be the plan's last: the link-navigation and print follow-ons (branches
// filereview-linknav and filereview-print, in flight) land at the same place, and the print pin holds that one last, so
// a "last" assertion here would turn red on main whichever of the two landed second (found by the review of this fix,
// 2026-09-20). Synthetic: the repo's own text only. Run: node --test tools/markdown-viewer-plan-gate-adopt.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const flat = (s) => s.replace(/\s+/g, ' ');
/** A run of `//` comment lines as one line of prose: the prefixes go, then the whitespace folds. */
const prose = (s) => flat(s.replace(/\n\s*\/\/ ?/g, ' '));

const HEADING = '## Fix: the gate before adoption (2026-09-20)';
const TITLE = '"Fix: the gate before adoption (2026-09-20)"';
const LEG = 'file-view-figures-gate-adopt-browser.test.ts';
const SVG_LEG = 'file-view-figures-gate-adopt-svg-browser.test.ts';
/** The seam test's guard for the premise where CI runs, as the plan's Tests paragraph quotes it. */
const SEAM_GUARD = '"the inertness premise, held where CI runs"';

const plan = read('plans', 'markdown-viewer.md');
const view = read('ui', 'webview', 'file-view.ts');
const legPath = path.join(REPO, 'ui', 'webview', LEG);

function between(text, from, to) {
  const a = text.indexOf(from);
  assert.ok(a >= 0, `${from} not found`);
  const b = text.indexOf(to, a);
  assert.ok(b > a, `${to} not found after ${from}`);
  return text.slice(a, b);
}
/** The section's text: from its heading line to the next `## ` heading, or the end of the plan when none follows. */
function section() {
  const start = plan.indexOf('\n' + HEADING + '\n') + 1;
  assert.ok(start > 0, 'the fix section is in the plan');
  const next = plan.indexOf('\n## ', start);
  return plan.slice(start, next < 0 ? plan.length : next);
}

test('the fix section is in the plan once, after Out of scope, and its text stops at the next section', () => {
  assert.equal((plan.match(/^## Fix: the gate before adoption \(2026-09-20\)$/gm) || []).length, 1, 'one heading');
  const headAt = plan.indexOf('\n' + HEADING + '\n');
  const scopeAt = plan.indexOf('\n## Out of scope\n');
  assert.ok(scopeAt >= 0 && scopeAt < headAt, 'the section follows "## Out of scope"');
  // Not held to be the plan's last section: sibling follow-ons land at the same place (the header comment says which).
  const s = section();
  assert.ok(s.startsWith(HEADING + '\n'), 'the section opens with its heading');
  assert.equal(s.indexOf('\n## '), -1, 'the section holds no other ## heading, so a sibling section appended after it is not read as its own');
  assert.ok(s.includes('**Tests.**'), 'the section runs to its Tests paragraph');
});

test('Slice 1 points at the section with one dated sentence, at the paragraph about attributes that fetch on render', () => {
  const slice1 = between(plan, '### Slice 1: sanitize as GitHub does', '### Slice 2:');
  const para = flat(slice1);
  assert.ok(para.includes('also fetch on open and sit outside `img[src]`. The gate itself ran after the sanitized nodes were adopted into the live document until 2026-09-20, and WebKit fetches an img on that adoption, so its placeholder stood over a request already made; the hole, the fix and its measurement are in ' + TITLE + ', the section after "Out of scope".'),
    'the pointer sentence follows the paragraph\'s last sentence about fetch-on-open attributes');
  assert.equal((slice1.match(/Fix: the gate before adoption/g) || []).length, 1, 'one pointer in Slice 1');
});

test('the Slice 4 record\'s item 9, the gate, points at the section', () => {
  const slice4 = between(plan, '### Slice 4: one markdown configuration', '### Slice 5:');
  const item9 = between(slice4, '9. *Decision 8, the gate*', '\n10. ');
  assert.ok(flat(item9).includes('Since 2026-09-20 the chain runs on the sanitizer\'s own body, before the adoption into the live document: a chain after the adoption fetched a gated figure in WebKit while the placeholder stood (' + TITLE + ', the section after "Out of scope", records the hole, the fix, the instrument and the tests).'));
});

test('the section records the hole, the fix, the instrument, the measurement, the scope and the tests', () => {
  const s = flat(section());
  for (const sentence of [
    // the hole
    '`mdBlock` (file-view.ts) adopted the sanitized nodes into its live-document box first (`box.replaceChildren(...Array.from(sanitizeMd(dirty, mintHeadingIds).childNodes))`) and ran the figure chain after: resolveFigureRefs for a URL document, rewriteFigureSrcs for a file, gateRemoteFigures for both.',
    'Under WebKit a figure on an unlisted host was requested while the gate\'s placeholder, "Image from <host>. Click to load.", stood, so the placeholder was a false assurance.',
    'In Chromium and Firefox the servers\' logs held no line for either of those img figures before the chain ran, so for an HTML img only WebKit leaked; the engines\' scheduling of the fetch was not instrumented, the logs were read.',
    'For an inline svg\'s `<image>` the gate held in Chromium alone.',
    'WebKit requested the `xlink:href` spelling in every run and the `href` spelling in none.',
    // the fix
    'The whole figure chain now runs over that body and the adoption comes after: `const clean = sanitizeMd(dirty, mintHeadingIds)`, then resolveFigureRefs, rewriteFigureSrcs and gateRemoteFigures over `clean`, then `box.replaceChildren(...Array.from(clean.childNodes))`.',
    'no pass after the adoption sets, repoints or moves a fetching attribute.',
    // the instrument
    'The claim is about bytes leaving, so the test reads real servers\' request logs, never page.route or context.route,',
    LEG + ' runs three servers on 127.0.0.1:',
    'and an HTTP forward proxy that logs every request the browser hands it and forwards by hostname. Each engine is launched with that proxy,',
    // the measurement
    '**Measured.** In Playwright\'s Chromium, Firefox and WebKit, at the base 2d41e5c9b and after the fix. At the base, WebKit: the figure server logged `GET /fig.png` under Host `remote.test` while the placeholder stood,',
    'Chromium and Firefox: no such line in any of the three scenes. The second leg, copied to the base: Firefox, both svg figures requested while their placeholders stood; WebKit, the `xlink:href` figure requested, the `href` one not; Chromium, no line for either. After the fix, in all three engines: no line for a gated figure until its click, which makes exactly one request, `GET /fig.png` under Host `remote.test` with no Referer; for the svg figures, `GET /drawing-href.png` under Host `remote.test` and `GET /drawing-xlink.png` under Host `other.test`, one per click, the other figure unrequested between the clicks. The folder figure is requested once, through /file, and never as `/fig.png`; the URL document\'s folder figure once, as `/notes/rel.png`, and never as `/rel.png`.',
    // the scope, as the finding states it
    '**Scope.** Unreachable through the VS Code panes, whose CSP blocks remote figures (`img-src ${webview.cspSource} data:`, extension.ts). Reachable through the kernel-served dashboard and the iOS web app. What leaks is the IP address, the time, the user agent and the path; the kernel sends Referrer-Policy same-origin, so no referer. The engine measured is Playwright\'s WebKit build, not literal iOS Safari, so the iOS statement rests on shared engine behaviour and not on a device test.',
    // the tests
    '**Tests.** ' + LEG + ', above: red in WebKit at 2d41e5c9b in all three scenes, green in Chromium and Firefox there, green in all three engines after the fix.',
    SVG_LEG + ', the second leg: red in Firefox and in WebKit at 2d41e5c9b, green in Chromium there, green in all three after the fix.',
    'file-view-seam.test.ts pins the order in mdBlock (sanitize, rewrite, gate on `clean`, then the adoption, and no figure pass over `box`) and holds the premise where CI runs, since both legs skip where Playwright\'s engines are absent and CI\'s npm test runs before its one browser install: its test ' + SEAM_GUARD + ' pins',
    'tools/upstream-ledger-figure-gate-before-adoption.test.mjs holds the ledger entry\'s file list, its count and its engine statements to the tree and the legs;',
    'tools/markdown-viewer-plan-gate-adopt.test.mjs holds this section\'s sentences to the code, its comment and the leg.',
  ]) assert.ok(s.includes(sentence), 'the section says: ' + sentence);
});

test('mdBlock runs the chain on the sanitized body and adopts after, and the adoption line\'s comment says so', () => {
  const mdFn = view.split('function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {')[1].split('\n}\n')[0];
  const cleanAt = mdFn.indexOf('const clean = sanitizeMd(dirty, mintHeadingIds);');
  const adoptAt = mdFn.indexOf('\n  box.replaceChildren(...Array.from(clean.childNodes));\n');
  assert.ok(cleanAt >= 0 && adoptAt > cleanAt, 'the sanitizer\'s body is bound to `clean`, and adopted later');
  for (const call of ['resolveFigureRefs(clean, doc.href);', 'gateRemoteFigures(clean, document.baseURI, [own]);',
    'rewriteFigureSrcs(clean, doc.path.slice(0, doc.path.lastIndexOf("/") + 1), doc.sid);', 'gateRemoteFigures(clean, document.baseURI);']) {
    const at = mdFn.indexOf(call);
    assert.ok(at > cleanAt && at < adoptAt, call + ' runs on `clean`, between the sanitize and the adoption');
  }
  assert.doesNotMatch(mdFn, /(resolveFigureRefs|rewriteFigureSrcs|gateRemoteFigures)\(box/, 'no figure pass over the live document\'s box');
  // The adoption line's comment: the lines between the chain's closing brace and the adoption line, comment lines only, read
  // as prose so a re-wrap of the lines does not move the pin (the round-1 rewording of this comment turned a line-for-line
  // pin red; found by the review of this fix, 2026-09-20).
  const braceAt = mdFn.lastIndexOf('\n  }\n', adoptAt);
  assert.ok(braceAt >= 0 && braceAt > cleanAt, 'the chain\'s if/else closes before the adoption');
  const aboveLines = mdFn.slice(braceAt + '\n  }\n'.length, adoptAt).split('\n');
  assert.ok(aboveLines.length >= 1 && aboveLines.every((l) => l.startsWith('  // ')), 'only comment lines sit between the chain and the adoption line');
  const above = prose('\n' + aboveLines.join('\n'));
  assert.ok(above.includes('Adopted as they are, no re-parse, every fetching attribute gated or repointed above, so the adoption starts no fetch to an unlisted host and none at a pre-rewrite URL, in any engine; what it does start is the fetch of every figure left with a live attribute, the folder\'s through /file and an allowed host\'s as written (the legs\' logs: no line for a gated host, one line through /file for the folder\'s figure).'),
    'the adoption line\'s comment says what the adoption starts and what it does not');
  const block = prose(mdFn.slice(cleanAt, adoptAt));
  assert.ok(block.includes('The figure chain runs HERE, on the sanitizer\'s body, BEFORE its nodes are adopted into `box` (2026-09-20).'), 'the block\'s opening comment');
  // The observation per vector, as the legs measured it: the two <img> figures, then the inline svg image.
  assert.ok(block.includes('In Chromium and Firefox the servers\' logs held no line for either of those <img> figures before the chain ran (measured at the base, 2026-09-20, by the first leg named below).'), 'the comment states the <img> observation, not a scheduling mechanism');
  assert.ok(block.includes('An inline svg\'s <image> is loaded by another path, and there the gate held in Chromium alone:'), 'the comment states the svg observation');
  assert.ok(block.includes('measured at the base by the second leg named below'), 'the svg observation names its leg');
  assert.ok(!/microtask/.test(block), 'no scheduling claim the leg did not measure');
  // The two legs the comment names, in the order it names them, both under ui/webview.
  const firstAt = block.indexOf(LEG), secondAt = block.indexOf(SVG_LEG);
  assert.ok(firstAt >= 0 && secondAt > firstAt, 'the comment names the img leg first and the svg leg second');
  assert.ok(fs.existsSync(path.join(REPO, 'ui', 'webview', SVG_LEG)), SVG_LEG + ' exists under ui/webview');
  assert.ok(block.includes('the section ' + TITLE + ' of plans/markdown-viewer.md records the hole, the instrument and the scope'), 'the comment names the plan section');
});

test('the leg exists, the section names it, and it is what the section says: real servers, a proxy, three engines, no route', () => {
  assert.ok(fs.existsSync(legPath), LEG + ' exists under ui/webview');
  assert.ok(section().includes(LEG));
  const leg = fs.readFileSync(legPath, 'utf8');
  assert.doesNotMatch(leg, /\.route\(|\.unroute\(/, 'no page.route or context.route: the logs are the servers\' own');
  assert.ok(leg.includes('server.listen(0, "127.0.0.1", () => resolve((server.address() as AddressInfo).port));'), 'every server binds 127.0.0.1 on an ephemeral port');
  assert.ok(leg.includes('browser = await pw[engine].launch({ proxy: { server: "http://127.0.0.1:" + proxyPort } });'), 'the engine is launched through the proxy');
  assert.ok(leg.includes('for (const engine of ["chromium", "firefox", "webkit"] as const) {'), 'the three engines');
  assert.ok(leg.includes('"referrer-policy": "same-origin"'), 'the harness sends the kernel\'s Referrer-Policy');
  assert.ok(leg.includes('await Promise.all([shut(proxy), shut(harness), shut(figures)]);'), 'the servers close in the teardown');
  assert.ok(leg.includes('const FIGURE = "http://remote.test/fig.png";'), 'the unlisted host is a .test name');
});

test('the Tests paragraph\'s premise guard is a test in file-view-seam.test.ts, and CI runs npm test before its one browser install, so the legs skip there', () => {
  const seam = read('ui', 'webview', 'file-view-seam.test.ts');
  assert.ok(seam.includes('\ntest(' + SEAM_GUARD.replace(/"$/, ': ')), 'the seam test holds a test titled by the phrase the section quotes');
  for (const pin of ['Object.keys(MD_PURIFY)', 'RETURN_DOM', 'shadowroot', '\\w+\\(clean\\b']) assert.ok(seam.includes(pin), 'the guard reads ' + pin);
  const ci = read('.github', 'workflows', 'ci.yml');
  const testAt = ci.indexOf('run: npm test\n'), installAt = ci.indexOf('run: npx playwright install');
  assert.ok(testAt >= 0 && installAt > testAt, 'npm test runs before the one playwright install');
  assert.equal((ci.match(/npx playwright install/g) || []).length, 1, 'one browser install in CI');
  assert.ok(ci.slice(installAt).startsWith('run: npx playwright install chromium\n'), 'and it installs Chromium alone');
  for (const leg of [LEG, SVG_LEG]) assert.ok(read('ui', 'webview', leg).includes('t.skip("playwright is not installed under vscode-extension'), leg + ' skips, saying so, without playwright');
});

test('the scope facts stand in the code they cite: the panes\' CSP names no remote img-src, the kernel sends Referrer-Policy same-origin', () => {
  const ext = read('vscode-extension', 'src', 'extension.ts');
  const imgSrc = ext.match(/img-src[^`\n]*/g) || [];
  assert.ok(imgSrc.length >= 1, 'the extension writes an img-src directive');
  for (const d of imgSrc) assert.equal(d, 'img-src ${webview.cspSource} data:', 'the webview\'s own source and data: only, no http scheme');
  const kernel = read('kernel', 'kernel.py');
  assert.ok(kernel.includes('self.send_header("Referrer-Policy", "same-origin")'), 'the kernel\'s header');
});

test('plain prose: no em dash in the section, the pointers or the chain block\'s comments', () => {
  const mdFn = view.split('function mdBlock(text: string, doc?: MdDocLoc): HTMLElement {')[1].split('\n}\n')[0];
  const cleanAt = mdFn.indexOf('const clean = sanitizeMd(dirty, mintHeadingIds);');
  const adoptAt = mdFn.indexOf('\n  box.replaceChildren(...Array.from(clean.childNodes));\n');
  assert.ok(cleanAt >= 0 && adoptAt > cleanAt);
  for (const [name, text] of [['section', section()],
    ['Slice 1', between(plan, '### Slice 1: sanitize as GitHub does', '### Slice 2:')],
    ['the chain block', mdFn.slice(cleanAt, mdFn.indexOf('\n', adoptAt + 1))]]) {
    assert.ok(!text.includes('\u2014'), name + ': em dash');
  }
});
