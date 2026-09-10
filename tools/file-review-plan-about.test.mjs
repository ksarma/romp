// The about follow-on's paragraph and decisions 45 and 46 (plans/file-review.md, under Slice 2 and in Decisions) held to
// the code, the host, the model, the kernel, the sheets and the modules they name.
//
// The paragraph records the user's answers of 2026-09-10 to the decoupling assessment: a comment names the changes it is
// about by stored ids of their own pick (decision 45), one list with the filter, nothing resolves a comment but them,
// singly or all the answered ones at once (decision 46), and a comment made inside a change stays an ordinary comment.
// A record that names a function the panel no longer has, a field the host no longer writes, or a module that is not in
// the tree costs the next reader the search it was meant to save, so every identifier the paragraph carries in backticks
// is checked against the panel, the model, the kernel, the host and the sheets; the decisions' claims against the code
// that makes them true; and the modules they name against the tree and the Tests section. Synthetic: only the repo's
// own text. Run: node --test tools/file-review-plan-about.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const panel = read('ui', 'webview', 'file-comments.ts');
const model = read('ui', 'webview', 'file-comments-model.ts');
const kernel = read('kernel', 'kernel.py');
const host = read('tools', 'file-comments-host.mjs');
const adr = read('docs', 'adr', '0002-file-comments-in-the-track-changents-sidecar.md');
const context = read('CONTEXT.md');
const sheets = { 'styles.css': read('ui', 'webview', 'styles.css'), 'feed.css': read('ui', 'webview', 'feed.css') };

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const LABEL = 'The about follow-on (2026-09-10):';
const note = between(plan, LABEL, '### Slice 3: region comments on images');
const tests = between(plan, '\n## Tests', '\n## Docs');
const docs = between(plan, '\n## Docs', '\n## Deliberately not in v1');
const contract = between(plan, '## The contract: the track-changents sidecar', 'Four properties of the contract shape the design');
const d45 = between(plan, '45. **A comment names the changes it is about by stored ids the person picks', '46. **');
const d46 = between(plan, '46. **Resolve answered', '\n## Open questions');

test('the paragraph stands under Slice 2 after the arrivals note, and the two decisions follow 44, each paraphrasing the user', () => {
  const slice2 = between(plan, '### Slice 2: the session', '### Slice 3: region comments on images');
  assert.ok(slice2.includes(LABEL));
  assert.ok(slice2.indexOf('The arrivals follow-on (2026-09-09):') < slice2.indexOf(LABEL), 'after the arrivals note');
  assert.ok(note.includes('a comment should say which changes it is about, by the user\'s own pick, not by the session\'s stamp'));
  assert.ok(note.includes('one list with the All / Comments / Changes filter, no tabs and no second section'));
  assert.ok(note.includes('nothing resolves a comment except the user, with a bulk action for the comments the session has answered'));
  assert.ok(note.includes('a comment inside a tracked change is an ordinary comment, never turned into a reply on the change'));
  for (const text of [note, d45, d46]) {
    assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(text.replace(/"about [^"]*"/g, '').replace(/"Resolve the N comments[^"]*"/g, '')), 'no quoted utterance of the user\'s');
  }
  const decisions = between(plan, '\n## Decisions', '\n## Open questions');
  const nums = Array.from(decisions.matchAll(/(?:^| )(\d+)\. \*\*/g), (m) => Number(m[1]));
  assert.deepEqual(nums.slice(-4), [43, 44, 45, 46], 'the list stays consecutive and ends at 46');
  assert.ok(d45.includes('(2026-09-10)') && d46.includes('(2026-09-10)'));
});

test('every identifier the paragraph names in backticks is in the panel, the model, the kernel, the host, the sheets or the tree', () => {
  const names = Array.from(note.matchAll(/`([^`]+)`/g), (m) => m[1]);
  assert.ok(names.length >= 30, 'the paragraph names its code: ' + names.length);
  const sources = [panel, model, kernel, host, ...Object.values(sheets)];
  for (const n of names) {
    if (/\.(test\.ts|py|mjs)$/.test(n)) {
      const rel = n.includes('/') ? n : path.join('ui', 'webview', n);
      assert.ok(fs.existsSync(path.join(REPO, rel)), `${n} is in the tree`);
    } else if (n === 'no-change') {
      assert.ok(host.includes("return { error: 'no-change', ids: missing };"), 'the host\'s refusal for a missing change');
    } else if (n === 'input[data-opt="about"]') {
      assert.ok(panel.includes('cb.dataset.opt = "about";'), 'the option\'s control');
    } else if (n === 'changeIds: [id]') {
      assert.ok(panel.includes('about: { ids: [id], on: true, only: false }') && panel.includes('if (c.about && c.about.on) args.changeIds = c.about.ids;'), 'the change card\'s comment names the change');
    } else if (n === '.fc-lit' || n === '.fc-hosted') {
      for (const [name, css] of Object.entries(sheets)) {
        if (n === '.fc-lit') assert.ok(css.includes('.fc-ins.fc-lit, .fc-del.fc-lit::before'), name + ': the ring rule');
        else assert.ok(!css.includes(n), name + ': the hosted rule is gone');
      }
    } else if (n === 'changeIds' || n === 'suggestionId' || n === 'target' || n === 'anchorAt' || n === 'refs' || n === 'hunk') {
      assert.ok((n === 'hunk' ? !/\n\s*hunk: Hunk \| null;/.test(model) : true), 'Card has no hunk');
      assert.ok(n === 'hunk' || host.includes(n) || model.includes(n), `${n} is a field the host or the model reads`);
    } else if (n === 'on "<quote>", about your change "<old>" to "<new>"') {
      assert.ok(model.includes('if (head && about) return head + ", " + about;'), 'the passage, then the about clause');
      assert.ok(model.includes("return 'on your change \"' + h.oldText + '\" to \"' + h.newText + '\"';"));
    } else if (n === 'CardKind' || n === 'Card' || n === 'About.on' || n === 'renderHosted') {
      if (n === 'renderHosted') assert.ok(!panel.includes('renderHosted'), 'renderHosted is gone');
      else if (n === 'About.on') assert.ok(panel.includes('type About = { ids: string[]; on: boolean; only: boolean };'));
      else assert.ok(model.includes('export type ' + n + ' ='), n);
    } else {
      assert.ok(sources.some((src) => src.includes(n + '(') || src.includes(n + ' ') || src.includes(n + ';') || src.includes(n + ',') || src.includes(n + ':') || src.includes(n + '"') || src.includes(n + "'")),
        `${n} is a function, a field, an action or a class of the panel, the model, the kernel, the host or the sheets`);
    }
  }
});

test('decision 45 as built: the host stores changeIds and never suggestionId, the model reads both, the card and the message name the changes, no comment inside a change card', () => {
  assert.ok(host.includes("if (args.suggestionId != null) {\n    throw new BadRequest('suggestionId is not accepted: a comment names the changes it is about with changeIds');"), 'the request branch is a caller bug');
  assert.ok(host.includes('const about = ids ? { changeIds: ids } : {};'), 'the field, in its slot before the body');
  assert.ok(!/suggestionId: /.test(host), 'the host writes no suggestionId');
  assert.ok(!/suggestionId: /.test(panel), 'and neither does the panel');
  assert.ok(host.includes('for (const id of Array.isArray(c.changeIds) ? c.changeIds : []) {'), 'decidedFor collects the about ids');
  assert.ok(model.includes('export function refIds(c: Pick<StoreComment, "changeIds" | "suggestionId">): Array<{ id: string; source: RefSource }> {'));
  assert.ok(model.includes('export type CardKind = "passage" | "file" | "region";'), 'no kind change');
  assert.ok(model.includes('comments: commentsAbout(cards, h.id).length, detached: false,'), 'the change card counts, never hosts');
  assert.ok(model.includes('export function aboutClause(refs: CardRef[], logTruncated = false): string | null {'));
  assert.ok(kernel.includes('and after the passage or alone, the changes the comment is about, `about your change "<old>"'), 'the kernel\'s docstring names the form it prints verbatim');
  assert.ok(panel.includes('fcchangecomment: (x, ev) => { ev.stopPropagation(); this.startChangeComment(x.dataset.id!); },'));
  assert.ok(panel.includes('cardKey(commentId: string): string {\n    return commentId;\n  }'), 'a comment\'s card is its own');
  assert.ok(d45.includes('Comment on this change (the change card\'s Reply until now)'));
  assert.ok(d45.includes('a deletion, whose text is not in the file'));
  assert.ok(d45.includes('Stored ids over a derived overlap'));
  assert.ok(adr.includes('`changeIds` (the changes the comment is about, by id, the person\'s own pick; the\n  about follow-on, 2026-09-10)'), 'the ADR names the third field');
  assert.ok(context.includes('**About (a comment about a change)**:'), 'CONTEXT.md has the term');
  assert.ok(context.includes('_Avoid_: bound to, linked to (the old binding the session\'s edit made)'));
});

test('decision 46 as built: the header action, the confirm line, one resolve per comment, Reopen all until the next gesture; nothing else resolves', () => {
  assert.ok(model.includes('export function answeredComments('), 'the model picks the answered comments');
  assert.ok(model.includes('return "Resolve answered (" + n + ")";') && panel.includes('resolveAnsweredLabel(answered.length)'), 'the header action names the count');
  assert.ok(panel.includes('fcresolveanswered'), 'its action');
  assert.ok(model.includes('return "Resolve the " + plural(n, "comment", "comments") + " the session has answered?";') && panel.includes('resolveAnsweredAsk(answered.length)'), 'the confirm line');
  assert.ok(panel.includes('btn("Reopen all", "fcreopenall"'), 'the undo in the acknowledgment\'s position');
  assert.ok(panel.includes('this.reopenAll = null;'), 'ended at a gesture');
  assert.ok(/\.resolved\s*=(?!=)/.test(host) && host.match(/\.resolved\s*=(?!=)/g).length === 1, 'the host writes resolved in doResolve alone');
  assert.ok(d46.includes('a reply of kind edit counts as an answer'));
  assert.ok(d46.includes('"Resolve the N comments the session has answered?"'));
  assert.ok(d46.includes('one request each'));
});

test('the Tests bullet and the Docs sentence name the modules, and every module named is in the tree', () => {
  const bullet = tests.slice(tests.indexOf('- The about follow-on (2026-09-10, decisions 45 and 46):'));
  const names = Array.from(bullet.matchAll(/`([^`]+\.(?:test\.ts|test\.mjs|py))`/g), (m) => m[1]);
  assert.ok(names.length >= 7, 'the bullet names its modules: ' + names.length);
  for (const n of names) {
    const rel = n.includes('/') ? n : path.join('ui', 'webview', n);
    assert.ok(fs.existsSync(path.join(REPO, rel)), `${n} is in the tree`);
  }
  assert.ok(docs.includes('With the about follow-on (2026-09-10), that Comment on this change opens the box over the change\'s text with "about this change" checked'));
  assert.ok(docs.includes('`tests/test_guide_files_about.py` holds the sentences to the panel'));
  assert.ok(fs.existsSync(path.join(REPO, 'tests', 'test_guide_files_about.py')));
});

test('the contract paragraph names both fields and who writes which', () => {
  assert.ok(contract.includes('romp\'s own optional `changeIds[]`, the changes the comment is ABOUT by id, the person\'s pick'));
  assert.ok(contract.includes('romp never writes `suggestionId` (decision 45) and reads one it finds as the change that ANSWERED the comment'));
  assert.ok(contract.includes('a comment written by the CLIs has at most one of `anchor` and `suggestionId`'));
});
