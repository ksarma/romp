// Decisions 47 and 48 (plans/file-review.md) and the Vendoring paragraph's guard sentences held to the
// Bash-side track guard, the installer, the uninstaller, the vendored patch series and the tests they name.
//
// Decision 47 records the guard on the Bash tool: why (the dry run's compound command), what it reads (the
// grammar: the verbs, the redirections, the interpreters), what it lets through, and where it is registered.
// Decision 48 records that sessions are asked to commit the comments folder and where the ask lives. A record
// that names a verb the hook no longer reads, a matcher the installer no longer writes, or a module that is
// not in the tree costs the next reader the search it was meant to save, so every such claim is checked
// against the source. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-bash-guard.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');

const plan = read('plans', 'file-review.md');
const hook = read('hooks', 'romp-track-bash-guard.mjs');
const install = read('install.sh');
const uninstall = read('bin', 'romp-uninstall');
const hooksReadme = read('hooks', 'README.md');
const guide = read('docs', 'guide.md').replace(/\s+/g, ' ');
const prompt = read('claude', 'romp-session-prompt.md').replace(/\s+/g, ' ');

function between(doc, from, to) {
  const a = doc.indexOf(from);
  assert.ok(a >= 0, `${JSON.stringify(from)} not found`);
  const b = doc.indexOf(to, a + from.length);
  assert.ok(b > a, `${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return doc.slice(a, b).replace(/\s+/g, ' ');
}
const d47 = between(plan, '47. **A guard on the Bash tool too**', '48. **');
const d48 = between(plan, '48. **Sessions commit the comments folder**', '\n## Open questions');
const vendoring = between(plan, '### Vendoring', '### The comments log');
const tests = between(plan, '\n## Tests', '\n## Docs');
const docs = between(plan, '\n## Docs', '\n## Deliberately not in v1');

test('decision 47 paraphrases the dry run, dates itself, and quotes no one', () => {
  assert.ok(d47.includes('(2026-09-10)'));
  assert.ok(d47.includes('track-config and cp in a single compound command on a tracked file'), 'the finding, paraphrased');
  assert.ok(d47.includes('the copy landed raw'));
  assert.ok(d47.includes('recovered from its own base copy'));
  for (const text of [d47, d48]) assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(text), 'no quoted utterance of the user\'s');
  assert.ok(!/\u2014/.test(d47) && !/\u2014/.test(d48), 'no em dash in the new decisions');
});

test('decision 47 names the hook, and the hook reads every verb, redirection and interpreter the decision says it reads', () => {
  assert.ok(d47.includes('`hooks/romp-track-bash-guard.mjs`'));
  assert.ok(fs.existsSync(path.join(REPO, 'hooks', 'romp-track-bash-guard.mjs')));
  for (const verb of ['cp', 'mv', 'install', 'ln', 'tee', 'sponge', 'truncate', 'dd', 'sort', 'sed', 'perl', 'python', 'node', 'cd']) {
    assert.ok(d47.includes(verb), `decision 47 names ${verb}`);
    assert.ok(new RegExp(`case '${verb}'`).test(hook), `the hook has a case for ${verb}`);
  }
  for (const op of ['>', '>>', '>|', '&>']) {
    assert.ok(d47.includes(`\`${op}\``), `decision 47 names the ${op} redirection`);
    assert.ok(hook.includes(`'${op}'`), `WRITE_REDIRECTS holds ${op}`);
  }
  assert.ok(/const WRITE_REDIRECTS = new Set\(\['>', '>>', '>\|', '&>', '&>>', '>&', '<>'\]\)/.test(hook));
  assert.ok(d47.includes('descriptor-prefixed redirection'));
  assert.ok(/\/\^\[0-9\]\+\$\/\.test\(buf\)/.test(hook), 'the lexer drops a digits-only word glued to < or > as the descriptor');
  assert.ok(d47.includes('a literal path a python or node inline script opens with a write mode'));
  assert.ok(hook.includes('export function scriptWriteTargets(kind, text)'));
  // the verdict: store-io's findVaultRoot, then isTrackedFile's three steps run by the hook's own trackedIn so the
  // closure is built once per call (the review's consolidation, 2026-09-10: the decision had said the hook called
  // isTrackedFile itself), and the real path judged beside the name given
  assert.ok(d47.includes('store-io\'s `findVaultRoot` and the three steps of its `isTrackedFile` (the veto list, the explicit list by name, then the link closure), which the hook runs itself as `trackedIn`'));
  assert.ok(hook.includes("import { findVaultRoot, isTrackedFile, isNonTextPath, hasNulBytes } from '../vendor/track-changents/store-io.mjs'"));
  assert.ok(hook.includes('function trackedIn(root, file, closures)') && hook.includes('const root = rootOf(file);') && hook.includes('const root = findVaultRoot(file);'));
  assert.ok(d47.includes('judged under the name given and under the real path the kernel opens, so a symlink to a tracked file carries no write past it'));
  assert.ok(hook.includes('function realPathOf(file') && hook.includes('return real != null && real !== file && guardedByName(real, closures);'));
  // a link is one entry: ln names its link and walks no source
  assert.ok(d47.includes('a directory source walked to the files it carries, a link one entry whatever it points at'));
  assert.ok(hook.includes("const land = (s, d) => (verb === 'ln' ? [d] : landing(s, d, cwd));"));
});

test('decision 47 states what passes, and the hook agrees: reads, opaque commands, non-text files, no ROMP_SID', () => {
  assert.ok(d47.includes('a read (cat, grep, diff, git, sed without -i) names no target'));
  assert.ok(d47.includes('a command behind eval, xargs or a shell -c it cannot read is unresolvable and passes'));
  // since 2026-09-18 a write target the hook cannot read (a variable, a substitution, a glob or brace list it cannot
  // expand) is refused while a project that tracks anything is in play, and the decision says so
  assert.ok(d47.includes('a write whose target the hook cannot read') && d47.includes('is refused while a project that tracks anything is in play'));
  assert.ok(hook.includes('function trackingRootAt(dir, memo)') && hook.includes('function inPlayFor(u, cwd, memo)') && hook.includes('const cannotRead = (w, how) => {'));
  assert.ok(hook.includes('which is not a literal path'), 'the refusal says the target is not literal');
  // the round-1 review (2026-09-18) bounded the rule in four places and named two residuals, and the decision
  // records each against the hook's own function
  assert.ok(d47.includes('holds an entry the literal rule could refuse') && hook.includes('function tracksRefusable(root, memo)'));
  assert.ok(d47.includes('the directory judged under its real path and its name') && hook.includes('for (const d of real && real !== dir ? [real, dir] : [dir]) {'));
  assert.ok(d47.includes('the landing folder counting only when a tracked file could land there') && hook.includes('function landingInPlay(hit, memo)'));
  // review round 2 (2026-09-18): the landing cap is recorded as the deliberate false refusal it is, the numeric
  // set is per shell with BASHPID out of it, the target's own prefix is asked and a fold still resolves, and the
  // environment clause says which value can reach a refusal
  assert.ok(d47.includes('or when it holds more than 2000 entries, past which the hook does not scan it and takes it as in play (`LANDING_SCAN_CAP`, a deliberate false refusal'));
  assert.ok(hook.includes('const LANDING_SCAN_CAP = 2000;') && hook.includes('if (names.length > LANDING_SCAN_CAP) return true;'), 'the cap the decision names');
  assert.ok(d47.includes('a target whose only expansions the shell running it will not let it assign (`$$` and `${$}` in every shell; `$RANDOM` and `$SECONDS`, their brace forms too, read-only integers in bash and in zsh'));
  assert.ok(d47.includes('not inside a script the command hands to `sh` or `dash`, where they are ordinary variables; `$BASHPID`, which round 1 listed as numeric by construction, is unset and assignable in zsh and is out of the set) and whose text is an absolute path outside every project in play is allowed'));
  assert.ok(hook.includes("const NUMERIC_EXPANSIONS = new Set(['RANDOM', 'SECONDS']);") && hook.includes('const POSIX_SH_NUMERIC = new Set();') && hook.includes("const KEEPS_NUMERIC_SPECIALS = new Set(['bash', 'zsh']);"), 'the per-shell sets');
  assert.ok(!/NUMERIC_EXPANSIONS = new Set\(\[[^\]]*BASHPID/.test(hook), 'BASHPID is in no numeric set');
  assert.ok(hook.includes('recurse(sh.script.text, name)') && hook.includes('recurse(body, name)') && hook.includes('lex(command, numericSetFor(shell))'), 'a script handed to a shell is lexed with that shell\'s set');
  assert.ok(d47.includes('the project the target\'s own literal prefix sits in being asked first') && hook.includes('const { cut, dir } = literalDirOf(norm);') && hook.includes('const own = trackingRootAt(dir, memo);') && hook.includes('if (own && landingInPlay(own, memo)) {'));   // the own step keeps the cut since round 2's addendum (unknownFolderOf reads it)
  assert.ok(d47.includes('a `..` that folds every expansion away still resolving the literal directory part') && hook.includes("const cut = dollar < 0 ? norm.lastIndexOf('/') : norm.lastIndexOf('/', dollar);"));
  // review round 2's addendum (2026-09-18): the numeric folder in the first segment under a tracked root is the
  // second deliberate false refusal the decision states, with the ruling's reason, and the hook routes that case
  // to a refusal that names the unknown folder rather than the project and asks for it spelled out
  assert.ok(d47.includes('when the expansion names a folder in the first segment under that root, `<root>/x-$$/y.md`, the literal prefix is the root itself'));
  assert.ok(d47.includes('a deliberate false refusal ruled correct in round 2\'s addendum, 2026-09-18: the folder\'s name does not exist at check time and is not derivable from the text'));
  assert.ok(d47.includes('naming the unknown folder rather than the project and asking for the folder spelled out'));
  assert.ok(d47.includes('`<root>/sub/x-$$/y.md` resolves its literal prefix to `<root>/sub` and an untracked `sub` falls through to the cwd rule'), 'the class is the first segment only');
  assert.ok(hook.includes('function unknownFolderOf(hit, norm, cut)') && hook.includes('return folder == null ? own : { ...own, unknownFolder: folder };') && hook.includes('if (hit.unknownFolder) {'), 'the hook routes the case');
  assert.ok(hook.includes('I cannot tell which folder the write lands in') && hook.includes('Spell the folder out'), 'to a refusal that names the folder and asks for it spelled out');
  assert.ok(hook.includes('function numericOutside(text, root)') && hook.includes('function literalDirOf(norm)'));
  assert.ok(d47.includes('a `$(date)` in a log\'s name among them, a cost stated to the user rather than solved'), 'the residual false refusal is stated, not claimed solved');
  assert.ok(d47.includes('the hook reads no variable named in the command to resolve the word'));
  assert.ok(d47.includes('TRACKCHANGES_ROOT, which stands in for the root search only for a directory under it') && hook.includes('const fromEnv = !!env && !outside(d, env);'));
  assert.ok(d47.includes('of those only HOME\'s value can appear in a refusal, and only as a path the hook resolved through it') && d47.includes('TRACKCHANGES_ROOT is named by the variable, never by its value, and ROMP_SID is never printed') && hook.includes("hit.fromEnv ? 'the project TRACKCHANGES_ROOT names' : hit.root"));
  assert.ok(!d47.includes('no value read there reaches a refusal'), 'the round-1 clause, false for a `$HOME` target, is gone');
  assert.ok(d47.includes('a python or node one-liner whose write path is computed') && d47.includes('the interpreter scan reads a literal path only'), 'the interpreter residual is named');
  assert.ok(hook.includes('function installDirOnly(t)'), 'install -d writes no file');
  // a glob is no longer unresolvable: it is expanded as the shell expands it (the review's second round), as are a
  // brace list, a here-string and a process substitution, and the decision says so of each
  assert.ok(!d47.includes('a path built from a variable or a glob'), 'a glob is not listed among the unresolvable');
  assert.ok(d47.includes('or a glob that matches nothing or names more than the hook will list) is refused'));
  assert.ok(d47.includes('a glob is otherwise expanded against the filesystem as the shell expands it (a redirection onto several matches or brace alternatives names each, as zsh\'s multios writes them; bash writes none)'));
  assert.ok(hook.includes('function expandGlob(w, cwd)') && hook.includes('const GLOB_MATCH_CAP = ') && hook.includes('const GLOB_READ_CAP = '));
  assert.ok(d47.includes('a brace list is expanded before the operands are read') && hook.includes('function braceExpand(text, marks)'));
  assert.ok(d47.includes('a here-string is scanned like a heredoc') && hook.includes("expect = { kind: 'herestring' }"));
  assert.ok(d47.includes('a process substitution\'s command is read like a `$(...)`') && hook.includes("if ((c === '>' || c === '<') && src[i + 1] === '(') {"));
  assert.ok(d47.includes('`cd` moving the working directory for what follows, inside `( ... )` only up to the `)`'));
  assert.ok(hook.includes("frames.push({ kind: 'subshell', dir, unknownDir });"));
  assert.ok(hook.includes("case 'eval': case 'xargs': sawOpaqueCommand = true; break;"));
  assert.ok(d47.includes('a tracked image or PDF passes by name'));
  assert.ok(hook.includes('if (isNonTextPath(file)) return false;'));
  assert.ok(d47.includes('a source copied out of a tracked file is a read'));
  assert.ok(d47.includes('rm, a mv of the tracked file elsewhere'), 'what the hook does not read is named as such');
  assert.ok(d47.includes('Without ROMP_SID it exits 0 before reading stdin (decision 24)'));
  assert.ok(hook.includes('if (!process.env.ROMP_SID) process.exit(0);'));
  assert.ok(d47.includes('exit 2 with one line naming the file and the track-edit command'));
  assert.ok(hook.includes("process.exit(2)") && hook.includes('node ~/.claude/hooks/track-edit.mjs --file'));
});

test('decision 47 says where the hook is registered, and install.sh and romp-uninstall do it so', () => {
  assert.ok(d47.includes('registered by the same installer merge on the `Bash` matcher (synchronous, timeout 10'));
  assert.ok(install.includes('("romp-track-bash-guard.mjs", 10, False, "Bash")'));
  assert.ok(/for h in [^;]*romp-track-bash-guard\.mjs; do\n\s+ln -sf "\$ROMP_DIR\/hooks\/\$h"/.test(install), 'linked from hooks/ with romp\'s own hooks');
  assert.ok(d47.includes('removed by the uninstaller with romp\'s hooks'));
  assert.ok(/for h in [^;]*romp-track-bash-guard\.mjs; do\n\s+rm -f "\$HOME\/\.claude\/hooks\/\$h"/.test(uninstall));
  assert.ok(uninstall.includes('"romp-track-bash-guard.mjs"}'), 'in the uninstaller\'s OURS set');
  assert.ok(hooksReadme.includes('| `romp-track-bash-guard.mjs` | PreToolUse on `Bash` |'), 'the hooks README table row');
});

test('the Vendoring paragraph on the guard gains the Bash hook, pointing at decision 47', () => {
  assert.ok(vendoring.includes('Anything a romp session itself spawns also carries the variable'), 'the paragraph as it stood');
  assert.ok(vendoring.includes('A second PreToolUse hook, romp\'s own (`hooks/romp-track-bash-guard.mjs`, on the `Bash` matcher'));
  assert.ok(vendoring.includes('decision 47'));
});

test('decision 48 records the finding, keeps decision 25, and names the places the ask lives', () => {
  assert.ok(d48.includes('(2026-09-10)'));
  assert.ok(d48.includes('never added `.trackchanges/` to git'));
  assert.ok(d48.includes('Decision 25 is unchanged'));
  assert.ok(d48.includes('`vendor/track-changents/patches/0007'));
  assert.ok(fs.existsSync(path.join(REPO, 'vendor', 'track-changents', 'patches', '0007-skill-no-bash-writes-commit-the-folder.patch')));
  assert.ok(d48.includes('`claude/romp-session-prompt.md`'));
  assert.ok(prompt.includes('include that folder in the commit'), 'the prompt carries the sentence');
  assert.ok(d48.includes('the user did not choose staging'));
  for (const text of [d47, d48]) assert.ok(!/\b(he|his|him|owner)\b/.test(text), 'the plan speaks of the user, they; never a gendered pronoun or the owner');
  assert.ok(guide.includes('Sessions are asked to include the folder when they commit their own work'));
});

test('the Tests and Docs sections name the modules and the doc sentences this slice adds', () => {
  for (const mod of ['tools/romp-track-bash-guard.test.mjs', 'tools/file-review-plan-bash-guard.test.mjs',
    'tests/test_guide_files_commit_folder.py', 'tests/test_guide_files_bash_guard.py']) {
    assert.ok(tests.includes(`\`${mod}\``), `the Tests section names ${mod}`);
    assert.ok(fs.existsSync(path.join(REPO, mod)), `${mod} exists`);
  }
  assert.ok(tests.includes('`tests/install-sh.bats`') && tests.includes('the Bash-side guard'));
  assert.ok(docs.includes('With the Bash guard follow-on (2026-09-10)'));
  assert.ok(docs.includes('`tests/test_guide_files_bash_guard.py`') && docs.includes('`tests/test_guide_files_commit_folder.py`'));
});
