// Decisions 47 and 48 (plans/file-review.md) and the Vendoring paragraph's guard sentences held to the
// Bash-side track guard, the installer, the uninstaller, the vendored patch series and the tests they name.
//
// Decision 47 records the guard on the Bash tool: why (the dry run's compound command), what it reads (the
// grammar: the verbs, the redirections, the interpreters), what it lets through, and where it is registered.
// Decision 48 records that sessions are asked to commit the comments folder and where the ask lives. A record
// that names a verb the hook no longer reads, a matcher the installer no longer writes, or a module that is
// not in the tree costs the next reader the search it was meant to save, so every such claim is checked
// against the source. The three prose surfaces beside the plan that state the numeric exception's boundary
// (docs/install.md, the hook's row in hooks/README.md, the ledger entry) are held to the hook's set here too,
// since round 3's mutation pass (2026-09-19) inverted each and nothing went red. Synthetic: only the repo's own text.
// Run: node --test tools/file-review-plan-bash-guard.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { CENSUS, census } from './romp-track-bash-guard-census.mjs';

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
  // the fifth commit (2026-09-19, M2): zsh's clobber-override suffixes and `>>&` are write redirections under their own operator
  assert.ok(/const WRITE_REDIRECTS = new Set\(\['>', '>>', '>\|', '&>', '&>>', '>&', '<>', '>!', '>>!', '>>\|', '>&!', '>&\|', '>>&', '>>&!', '>>&\|', '&>!', '&>\|', '&>>!', '&>>\|'\]\)/.test(hook));
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
  assert.ok(hook.includes('function trackingRootAt(dir, memo)') && hook.includes('function inPlayFor(u, cwd, memo)') && hook.includes('const cannotRead = (w, how, why = null) => {'));
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
  // review round 3 (2026-09-19): the numeric set is the process id alone, in every shell, and the decision says why;
  // the per-shell table is gone from the hook with the names it trusted
  assert.ok(d47.includes('a target whose only expansions are `$$` and `${$}`, the shell\'s process id, and whose text is an absolute path outside every project in play is allowed'));
  assert.ok(d47.includes('The numeric set is those two spellings and nothing else, in every shell: every other candidate can be unset or shadowed by the command and then hold a path'));
  assert.ok(!d47.includes('read-only integers in bash and in zsh'), 'the round-2 premise is gone from the decision');
  assert.ok(hook.includes("const NUMERIC_EXPANSIONS = ['$$', '${$}'];"), 'the numeric set is the two spellings of the process id');
  assert.ok(!/NUMERIC_EXPANSIONS = \[[^\]]*(RANDOM|SECONDS|BASHPID)/.test(hook) && !/['"](RANDOM|SECONDS|BASHPID)['"]/.test(hook), 'no other name is in the set, and no code names one');
  assert.ok(!hook.includes('KEEPS_NUMERIC_SPECIALS') && !hook.includes('POSIX_SH_NUMERIC') && !hook.includes('numericSetFor'), 'the per-shell table is gone');
  assert.ok(hook.includes('recurse(sh.script.text, name)') && hook.includes('recurse(body, name)') && hook.includes('lex(command, shell)') && hook.includes("const ANSI_C_SHELLS = new Set(['bash', 'zsh']);"), 'a script handed to a shell is lexed as that shell reads `$\'...\'`');
  assert.ok(d47.includes('`$\'...\'` is ANSI-C quoting in bash and zsh, a literal word') && hook.includes('function ansiC(body)') && hook.includes("if (e.kind === 'ansi') {"), 'ANSI-C quoting');
  // the target's own project, asked first for every target the hook can place (round 2 for a numeric one, round 3 for
  // every unreadable word and for a relative spelling), and the fold judged as the kernel opens the path
  assert.ok(d47.includes('the project the target\'s own literal directory part sits in is asked first, from any cwd, for every target the hook cannot read that it can place, absolute or relative to a write-time directory it knows'));
  assert.ok(hook.includes('function ownProjectFor(u, memo)') && hook.includes('const own = trackingRootAt(v.dir, memo);') && hook.includes('if (own && landingInPlay(own, memo)) return v.folder'));
  assert.ok(d47.includes('a fold that leaves no expansion handed to the literal rule') && hook.includes('function foldSegments(segs)') && hook.includes('if (v.literal != null && isGuardedPath(v.literal, memo.closures)) return { literal: v.literal };'));
  assert.ok(d47.includes('a `..` after a directory that exists climbs from that directory\'s real path, as the kernel does') && hook.includes('function resolveLiteral(text, dir)'));
  assert.ok(d47.includes('each entry of that directory that exists now and whose name the process id could spell') && hook.includes('function spelledCandidates(segs, idx, dir, memo, budget)') && hook.includes('function couldSpell(seg, name)'));
  // review round 2's addendum (2026-09-18) and round 3: the numeric folder name is a deliberate false refusal wherever
  // the landing gate on the literal directory part holds, not in the first segment only, and the refusal names the
  // unknown folder with a remedy the person can take
  assert.ok(d47.includes('the landing gate on that literal directory part is folder-granular, so a numeric name in any folder where a tracked file could land is refused from any cwd while its literal spelling may pass'));
  assert.ok(d47.includes('a deliberate false refusal ruled correct in round 2\'s addendum (2026-09-18) for the first segment (the folder\'s name does not exist at check time and is not derivable from the text'));
  assert.ok(d47.includes('names the unknown folder when the expansion names one, at any depth, and offers a literal folder name or a write outside the project, never the name the shell would give it'));
  assert.ok(!d47.includes('only the first segment behaves so') && !d47.includes('the class is the first segment only'), 'the first-segment boundary is gone');
  assert.ok(hook.includes('unknownFolder: v.folder') && hook.includes('unknownFolder: view.folder') && hook.includes('if (hit.unknownFolder) {'), 'the hook routes the case at any depth');
  assert.ok(hook.includes('I cannot tell which folder the write lands in') && hook.includes('Spell the folder out with a literal name of your own, or write outside that project') && !hook.includes('the name the shell would give it'), 'a refusal that names the folder and a remedy the person can take');
  assert.ok(hook.includes('function numericOutside(view, root)') && hook.includes('function numericView(u, memo)'));
  // round 3's other classes: a literal relative target after a cd the hook cannot follow, a landing folder no project
  // claims, the option clusters bash takes a word for, and the recursion caps
  assert.ok(d47.includes('a literal relative target after a `cd` the hook cannot follow') && hook.includes("{ kind: 'unknownDir', text: unknownWhy }") && hook.includes('function enterable(dir)'));
  assert.ok(d47.includes('a landing folder no project claims counts when an entry of it is or leads to a tracked file') && hook.includes('function guardedEntryIn(dir, memo)'));
  assert.ok(d47.includes('an entry named by the process id in a folder outside every project that holds more than 2000 entries, which is not listed') && hook.includes('if (!names || names.length > LANDING_SCAN_CAP) return out;'), 'the open scan is stated');
  assert.ok(d47.includes('`bash -O extglob -c') && hook.includes("(shell === 'bash' && (t === '-O' || t === '+O'))"));
  assert.ok(d47.includes('nested past 64 substitutions or brace lists') && hook.includes('const RECURSION_CAP = 64;') && hook.includes('const BRACE_DEPTH_CAP = 64;'));
  assert.ok(d47.includes('a `$(date)` in a log\'s name among them, a cost stated to the user rather than solved'), 'the residual false refusal is stated, not claimed solved');
  assert.ok(d47.includes('the hook reads no variable of the ENVIRONMENT named in the command to') && d47.includes('since B2, below, it does read a name the command\'s OWN TEXT sets to a plain string'), 'the privacy sentence, corrected in round 5 to what B2 made true');
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
  assert.ok(d47.includes('a brace list is expanded before the operands are read') && hook.includes('function braceExpand(text, marks, depth = 0)'));
  assert.ok(d47.includes('a here-string is scanned like a heredoc') && hook.includes("expect = { kind: 'herestring' }"));
  assert.ok(d47.includes('a process substitution\'s command is read like a `$(...)`') && hook.includes("if ((c === '>' || c === '<') && src[i + 1] === '(') {"));
  assert.ok(d47.includes('`cd` moving the working directory for what follows, inside `( ... )` only up to the `)`'));
  assert.ok(hook.includes("frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy });"));
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

// ── the three prose surfaces beside the plan that state the numeric exception's boundary ──
//
// docs/install.md, the hook's row in hooks/README.md and the ledger entry for the offer each say, since round 3
// (2026-09-19), that a name built from `$RANDOM` or `$SECONDS` inside a tracked project is refused, in every shell, and
// why. The mutation pass over that round inverted each clause and nothing went red: the plan and the skill were pinned,
// these three were not. Held here to the hook's set, as decision 47's sentence is above; the shapes themselves are run
// in tools/romp-track-bash-guard.test.mjs (the numeric-set test).
const installDoc = read('docs', 'install.md').replace(/\s+/g, ' ');
const ledger = read('upstream', '2026-09-18-track-guard-non-literal-targets.md').replace(/\s+/g, ' ');

test('the install guide, the hook\'s README row and the ledger entry say a name built from $RANDOM or $SECONDS is refused inside a tracked project, in every shell, and the hook\'s numeric set is the process id alone', () => {
  assert.ok(installDoc.includes('A temp file named only by the shell\'s process id (`$$`), at an absolute path where no tracked file could land'), 'docs/install.md: the exception, as the code allows it');
  assert.ok(installDoc.includes('still runs; a name built from `$RANDOM` or `$SECONDS` is refused, since a script can reassign those'), 'docs/install.md: the refused names, with the reason');
  const row = hooksReadme.split('\n').find((l) => l.startsWith('| `romp-track-bash-guard.mjs` |'));
  assert.ok(row, 'the hook has a row in hooks/README.md');
  assert.ok(row.includes('a target whose only expansions are `$$` or `${$}`, the shell\'s process id, at an absolute path outside every project in play is allowed, and nothing else is'), 'hooks/README.md: the exception');
  assert.ok(row.includes('since `$RANDOM`, `$SECONDS` and every other name can be unset or shadowed by the command and then hold a path, so a `log.$RANDOM` inside a tracked project is refused in every shell, a deliberate false refusal recoverable in one step'), 'hooks/README.md: the refused names, with the reason');
  assert.ok(ledger.includes('a target whose only expansions are `$$` or `${$}`, the shell\'s process id, at an absolute path outside every project in play is allowed, and no other expansion is numeric'), 'the ledger entry: the exception (round 5: no other expansion is numeric; a name the guard resolves is allowed by the path it names, which the old "nothing else is" denied)');
  assert.ok(ledger.includes('the process id is the one OPAQUE expansion allowed inside a tracked project'), 'the ledger entry says what the exception is the one of');
  assert.ok(ledger.includes('so a `log.$RANDOM` inside a tracked project is refused in every shell, a deliberate false refusal recoverable in one step'), 'the ledger entry: the refused names');
  assert.ok(hook.includes("const NUMERIC_EXPANSIONS = ['$$', '${$}'];"), 'the set every clause describes');
});

// Round 4's contract paragraph (2026-09-19): the guard is best-effort against known write forms, its default on an
// unrecognised form is allow, and the unmodelled writers that pass are listed. The same paragraph and the SAME
// writer list sit on all four surfaces a user meets, so a user who knows the boundary can work with it; this test
// reads each file whitespace-normalised and fails if any lacks it or if the lists differ.
test('decision 47 records round 4 and each class is tied to the hook function that implements it', () => {
  assert.ok(d47.includes('Round 4 (2026-09-19, a walk-around lens) closed eight more in-model roads'));
  assert.ok(d47.includes('read a per-writer option table (`COPY_OPT`)') && hook.includes('const COPY_OPT = {') && hook.includes('function parseCopyOptions(args, verb)'));
  // since the third pass `commandOf` returns the chdirs in order (a nested `env -C` composes) and the wrapper tables live in WRAPPER_OPT
  assert.ok(d47.includes('`commandOf` returns its `chdir`') && hook.includes('return { name, args: words.slice(k + 1), chdirs, writes, wrapped, wrappers };'));
  assert.ok(d47.includes('the `PREFIXES` set gained `setsid`, `flock`, `taskset`, `chrt` and `numactl`') && hook.includes("'setsid', 'flock', 'taskset', 'chrt', 'numactl'") && hook.includes('const WRAPPER_OPT = {'));
  assert.ok(d47.includes('the lexer marks a home expansion \'h\' and `extract` computes `homeAssigned`'));
  assert.ok(hook.includes("const home = (t) => { buf += t; marks += 'h'.repeat(t.length); };") && hook.includes('const homeAssigned = ctx.homeAssigned'));
  assert.ok(d47.includes('`parentTrackedRoots`') && hook.includes('function parentTrackedRoots(dir, segPrefix, memo)'));
  assert.ok(d47.includes('`foldSegments` folds a `..`') && hook.includes('const st = lstatOrNull(prefix);') && hook.includes('class UnknownPath extends Error'));
  assert.ok(d47.includes('`recordSymlink`, `applyInCommandLinks`') && hook.includes('function applyInCommandLinks(abs, links)') && hook.includes('const recordSymlink = (args, cwd) => {'));
  assert.ok(d47.includes('best-effort against known write forms, its default on an unrecognised form is allow'));
});

test('the best-effort contract and its unmodelled-writer list are stated identically on the hook header, the vendored SKILL.md, hooks/README.md and docs/install.md', () => {
  // strip the source's line-comment markers (`//` in the hook) so the paragraph reads the same whether it is a
  // comment, a markdown paragraph or a table cell, then collapse whitespace and case
  const norm = (s) => s.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  // the whole paragraph, since the third pass (2026-09-19): the contract sentence, the allow-by-default sentence, the
  // sentence that says what IS refused, and the writer list (which gained the unlisted wrappers, shuf -o, the scripts the
  // shell reads from elsewhere and a cd through CDPATH the three passes found; the fifth commit added the variable name
  // the shell fills in, the template path and the alias to the refused sentence, and the interpreter's computed forms,
  // the unbounded wrapper class and a link made by an unmodelled writer to the list; B2 as ruled added the resolution
  // sentence and restated the residual with its boundary, an opaque expansion from a cwd outside every project)
  const CONTRACT_PARAGRAPH = 'this guard is best-effort against known write forms: it refuses the shell writes it models and, by design, allows anything it does not recognise, so it never blocks ordinary work it cannot read; it is a backstop, not a complete boundary. the allow-by-default for an unmodelled writer is deliberately not flipped, since flipping it would refuse almost all normal work. what it does refuse, while a tracked project is in play, is a write it reads but cannot place: a target it cannot read, a path it cannot check (a stat error other than not-found), an option on a modelled writer or wrapper it does not parse in full, an env -s string, a shell option it does not know to be inert for paths, a link whose source it cannot read, a `~` or `$home` write beside a mention of home or beside a variable name the shell fills in, a template or format string as an interpreter\'s write path, and, from any working directory, a write through an alias the command makes (a hard link, `cp -l`, `cp -s`, `link`, a link whose source it cannot read) whose source lies in a tracked project or is one it cannot read. a value it can read is resolved first and the real path judged. a name is readable only when every write to it in the command is a plain top-level `name=plain-string` the shell performs as spelled: no tilde opening the value, no declaration flag at all, no `declare`, `typeset` or `local` (dash has none of the three; `export` and `readonly` with no option word are the two declarations every shell performs), no nameref reaching it, no name the shell fills in, no subshell, pipeline, piped group or body scope, no `{ }` group opened after `&&`, `||` or `|`, no wrapper argument, no call of a function the command defines in any spelling, no subscript; any other construct that can write the name, listed here or not, leaves it unreadable, the doctrine a `read` and a loop variable already had. home, pwd, oldpwd, `~+` and `~-` are read the same way: home after a plain top-level `home=<path>` assignment of its own, and none of the three once the command names or may fill in the name in any other form. ';
  const LIST = 'these write forms are not modelled and still reach a tracked file: rsync; awk with a redirect inside its program; ed; ex; make; find with -delete or -exec; a git subcommand that writes the working tree (checkout, stash, apply, reset, rm, clean, mv); a computed or escaped path inside an interpreter (a name, sys.argv, os.environ or process.env, a concatenation that does not open with a string literal, or an escape sequence in the string, in python3 -c or node -e); a script the shell reads from elsewhere (eval, xargs, a sourced file, trap, a command whose name is an expansion, a script held in a variable); a command that runs another command and is outside the guard\'s wrapper set (unshare, nsenter, script, setarch, setpriv, strace and their kin); a link made by a writer outside the model (python, tar, rsync) that a later modelled write follows; shuf -o; a cd through cdpath; and an opaque expansion from a cwd outside every project, leading or after a literal head outside every project (a `..` inside the value could climb into a project; from a cwd in a tracked project the same word is refused as not literal).';
  const CONTRACT = 'best-effort against known write forms';
  const surfaces = {
    'hook header': read('hooks', 'romp-track-bash-guard.mjs'),
    'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md'),
    'hooks/README.md': read('hooks', 'README.md'),
    'docs/install.md': read('docs', 'install.md'),
  };
  for (const [name, text] of Object.entries(surfaces)) {
    const n = norm(text);
    assert.ok(n.includes(CONTRACT), `${name} states the check is best-effort against known forms`);
    assert.ok(n.includes(LIST), `${name} carries the identical unmodelled-writer list (a differing list fails here)`);
    assert.ok(n.includes('allows anything it does not recognise') || n.includes('allow') , `${name} says the default is allow`);
    // the third pass (2026-09-19): the WHOLE paragraph is identical on the four surfaces, the two sentences the hook
    // header alone carried (the allow-by-default is not flipped; what is refused) included
    assert.ok(n.includes(CONTRACT_PARAGRAPH + LIST), `${name} carries the identical contract paragraph, the allow-by-default sentence and the refused-class sentence included`);
  }
});

// The walk-around lens second pass (2026-09-19): decision 47 records the six families and each is tied to the hook
// function that implements it, so a family dropped from the code fails here by name.
test('decision 47 records the walk-around lens second pass, each family tied to its hook function', () => {
  assert.ok(d47.includes('The\n    walk-around lens second pass (2026-09-19) then closed six families') || d47.includes('walk-around lens second pass (2026-09-19) then closed six families'));
  // (1) option tables and env -S
  assert.ok(d47.includes('a glued short form\n    (`sort -oFILE`)') || d47.includes('a glued short form (`sort -oFILE`)'));
  // since the third pass env -S is refused outright (WRAPPER_OPT's `refuse`), never read as a shell string
  assert.ok(d47.includes('`env -S`/`--split-string` runs a shell string') && hook.includes("refuse: { short: 'S', long: ['split-string'] }"));
  assert.ok(/else if \(\/\^-o\.\/\.test\(t\)\) add\(sliceWord\(args\[k\], 2\), 'sort -o'\)/.test(hook), 'sort reads a glued -o');
  // (2) assignment forms, since the third pass the bare identifier anywhere (bareExpandedNames)
  assert.ok(d47.includes('as an lvalue in any form the shells offer') && hook.includes('function bareExpandedNames(segments)'));
  // (3) in-command prefix mutations
  assert.ok(d47.includes('IN-COMMAND PREFIX MUTATIONS') && hook.includes('const recordMutations = (name, args, cwd) =>') && hook.includes('const mutated = ctx.mutated || [];'));
  // (4) stat errors refuse
  assert.ok(d47.includes('STAT ERRORS\n    REFUSE') || d47.includes('STAT ERRORS REFUSE'));
  assert.ok(hook.includes('class UnknownPath extends Error') && hook.includes('function statErrorRefusal(how, raw, e)') && hook.includes('function readConfigChecked(root)'));
  // (5) nested markers
  assert.ok(d47.includes('NESTED MARKERS') && hook.includes('function outerTrackingRoot(inner, file, closures)'));
  // (6) a cd the guard cannot know
  assert.ok(d47.includes('A cd THE GUARD CANNOT KNOW') && hook.includes('function commandOf(words)') && hook.includes('const cdFunctions = ctx.cdFunctions || new Set();'));
  assert.ok(d47.includes('`env -C DIR` resolves its operand\n    physically') || d47.includes('`env -C DIR` resolves its operand physically'));
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// The fifth commit (2026-09-19): decision 47 records the fourth pass's misses closed as rules on visible constructs, each
// tied to the hook function that implements it, so a rule dropped from the code fails here by name.
test('decision 47 records the fifth commit, each item tied to its hook function', () => {
  assert.ok(d47.includes('The fifth commit (2026-09-19)'));
  assert.ok(d47.includes('`trackEditLine`') && hook.includes('const shellQuote = (s) =>') && hook.includes('const trackEditLine = (file) =>'), 'M6: the remedy line is single-quoted');
  assert.ok(d47.includes('`assembledNameOperand`') && hook.includes('function assembledNameOperand(segments)') && hook.includes('function homeUnreadableWhy(segments)'), 'M1: a variable name the shell fills in');
  assert.ok(d47.includes('`clobberSuffix`') && hook.includes('const clobberSuffix = (op) =>'), "M2: zsh's clobber-override suffixes");
  assert.ok(d47.includes('`aliasSourceInPlay`') && hook.includes('function aliasSourceInPlay(why, memo)') && hook.includes('return { targets, opaque: opaque || sawOpaqueCommand, unresolved, links };'), 'M3 and B1: the links returned, the alias source asked');
  assert.ok(d47.includes('`scriptTemplateTargets`') && hook.includes('export function scriptTemplateTargets(kind, text)') && hook.includes("kind: 'templatePath'"), 'M4: a template path is unreadable');
  assert.ok(!hook.includes("!/[{}$]/.test(p)"), 'M4: the literal-path filter is gone');
  assert.ok(d47.includes('THE CRITERION') && hook.includes('export const INERT_OPTIONS = ') && hook.includes('const INERT_SET_LETTERS_WHY = {') && hook.includes('function setsKeywordMode(name, args)'), 'M5: the inert tables carry their criterion');
  // B2 as ruled (the fifth pass's second commit, option (c)): the values the guard can read are resolved, valueOf reads no expanded
  // name the command names or may fill in, and the opaque-head refusal (the dropped half) is not built
  // since the seventh pass the recorder is the readability rule's predicate in two parts (recordPlainWord, recordSegment)
  assert.ok(d47.includes('B2 (the second commit') && hook.includes('const resolveWord = (w) =>') && hook.includes('const recordPlainWord = (w, seg, idx, seq) =>') && hook.includes('const recordSegment = (seg, idx, cmd, preWords) =>') && hook.includes('const valueOf = (name) =>'), 'B2 as ruled: the values the guard can read are resolved');
  assert.ok(d47.includes('`unreadableExpandedNames`') && hook.includes('function unreadableExpandedNames(segments, homeWrites = new Set())') && hook.includes("unreadableNames.has('PWD')") && hook.includes("unreadableNames.has('OLDPWD')") && hook.includes("kind: 'namedExpansion'"), 'B2 as ruled: an expanded name the command names or may fill in is not read, and the refusal says why');
  assert.ok(!hook.includes('opaqueSpelling') && !hook.includes('is a value I cannot read') && d47.includes('THE RESIDUAL, with its boundary'), 'B2 as ruled: the opaque-head refusal is not built, and decision 47 states the residual with its boundary');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// The pin addendum (2026-09-19): decision 47 records the fifth pass's misses closed as stated rules applied to constructs
// the guard could see, each tied to the hook function that implements it, so a fix dropped from the code fails here by name.
test('decision 47 records the pin addendum, each fix tied to its hook function', () => {
  assert.ok(d47.includes('The pin addendum (2026-09-19;'));
  assert.ok(d47.includes('`cp --parents`') && hook.includes("nameL === 'parents'") && hook.includes('const under = (dirText, s) => {'), 'cp --parents lands the whole spelling');
  assert.ok(hook.includes("if (ch === 'c') { inline = j < a.text.length - 1 ? sliceWord(a, j + 1) : (args[k + 1] || null);") && !hook.includes('/^-[A-Za-z]*c$/'), "python's option cluster is walked; the end-of-word match is gone");
  assert.ok(hook.includes('/^--eval=/.test(a.text)'), "node's --eval= is its code (the --print= behaviour is executed in tools/romp-track-bash-guard.test.mjs; round 5 dropped an absence pin here that no head had ever matched)");
  assert.ok(d47.includes('`pyStringArg`') && hook.includes('([\\s\\S]*?)\\2([\\s\\S]*)$/);') && hook.includes("('''|"), 'a triple-quoted python string is a plain string: the delimiter is three quotes or one');
  assert.ok(d47.includes('`nodeStr`') && hook.includes('const nodeStr = (g) =>') && hook.includes("take(nodeStringArg(m[3], m[4], m[5] || ''))"), 'a JS string body runs to the next quote of its own kind (round 5: the continuation after the literal is the third argument)');
  assert.ok(!d47.includes(String.fromCharCode(0x2014)), 'no em dash in decision 47');
});

// The walk-around lens third pass (2026-09-19): decision 47 records the six rules re-keyed on what the guard can see,
// each tied to the hook function or table that implements it, and the hook header carries the audit of the lists that
// remain with the side each list's gap falls on; a rule dropped from the code, or a list added without its gap stated,
// fails here by name.
test('decision 47 records the walk-around lens third pass, each rule tied to its hook function, and the hook header audits the lists that remain', () => {
  assert.ok(d47.includes('The walk-around lens third pass (2026-09-19) re-keyed six rules on what the guard can see'));
  // (a) the bare identifier
  assert.ok(d47.includes('BARE IDENTIFIER') && hook.includes('function bareExpandedNames(segments)') && hook.includes("const EXPANDED_NAMES = ['HOME', 'PWD', 'OLDPWD'];"));
  assert.ok(!hook.includes('function assignsHome(') && !hook.includes('HOME_DECLARERS'), 'the enumeration of assignment forms is gone');
  // (b) fully parsed or refused
  assert.ok(d47.includes('FULLY PARSED OR REFUSED') && hook.includes('const WRAPPER_OPT = {') && hook.includes('({ unknown: { option, wrapper: name, value, rest: words.slice(k + 1) } })'));
  assert.ok(hook.includes("refuse: { short: 'S', long: ['split-string'] }") && hook.includes("kind: 'opaqueScript'"), 'env -S is refused outright');
  assert.ok(hook.includes('for (const c of cmd.chdirs) {'), 'a nested chdir composes');
  assert.ok(!hook.includes('PREFIX_OPERANDS') && !hook.includes('PREFIX_LEAD_OPERANDS'), 'the operand lists are gone with the tables');
  // (c) the non-literal link source
  assert.ok(d47.includes('NON-LITERAL LINK SOURCE') && hook.includes("markMutated(dstAbs, 'ln -s', { alias: true })"), 'a non-literal link source marks the name, and since the fifth commit records that it aliases a source the guard cannot read (B1)');
  // (d) the shell-option allowlist
  assert.ok(d47.includes('SHELL OPTIONS, AN ALLOWLIST') && hook.includes('function shellOptionChange(name, args)') && hook.includes('const INERT_SET_LETTERS = ') && hook.includes('const INERT_SET_OPTIONS = new Set([') && hook.includes('const INERT_SHOPT = new Set(['));
  assert.ok(!hook.includes('physicalMode'), 'the physical-option enumeration is gone');
  // (e) any depth
  assert.ok(d47.includes('ANY DEPTH') && hook.includes('const PARENT_SCAN_BUDGET = ') && hook.includes('function parentTrackedRoots(dir, segPrefix, memo)'));
  // (f) the unknown option refuses everywhere
  assert.ok(d47.includes('UNKNOWN OPTION REFUSES EVERYWHERE') && hook.includes('function optionCandidates(args)') && hook.includes("if (parsed.unknown) { markAllCandidates('mv'); return; }"));
  // the corpus and the lists audit
  assert.ok(d47.includes('`tools/romp-track-bash-guard-corpus.json`') && fs.existsSync(path.join(REPO, 'tools', 'romp-track-bash-guard-corpus.json')));
  // round 5 (2026-09-20): the census is derived from the source at test time (tools/romp-track-bash-guard-census.mjs), the header
  // points at it, and the lists the third pass named are classified there with a side and a consumer line that exists
  assert.ok(hook.includes('THE LISTS THAT REMAIN are not written here') && hook.includes('tools/romp-track-bash-guard-census.mjs'), 'the hook header points at the derived census');
  assert.ok(!hook.includes('THE LISTS THAT REMAIN, each with the side its GAP falls on'), 'the hand-written census is gone');
  const c = census(hook);
  assert.deepEqual([c.unnamed, c.stale, c.unclassified, c.missingConsumer], [[], [], [], []], `the census holds over the hook: ${JSON.stringify(c)}`);
  for (const list of ['PREFIXES', 'WRAPPER_OPT', 'COPY_OPT', 'INERT_SET_LETTERS_WHY', 'EXPANDED_NAMES', 'NUMERIC_EXPANSIONS', 'ANSI_C_SHELLS', 'BODY_CLOSER', 'CLOSERS']) {
    assert.ok(CENSUS[list] && ['WRITE', 'REFUSE', 'NONE'].includes(CENSUS[list].side) && hook.includes(CENSUS[list].consumer), `the census names ${list} with its gap side and its consumer line`);
  }
  assert.equal(CENSUS.BODY_CLOSER.side, 'WRITE'); assert.equal(CENSUS.CLOSERS.side, 'WRITE'); assert.equal(CENSUS.PREFIXES.side, 'WRITE');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// The sixth pass (2026-09-19): decision 47 records the mutation lens's unpinned claims pinned and the unreachable poison
// line removed from recordAssignments; the poison that runs stays in extract's own branches, and the poison left for a
// ruling is disclosed on the hook header and in the decision rather than claimed pinned.
test('decision 47 records the sixth pass: the unreachable poison line is gone, the poison that runs sits in extract, and the unpinned poison is disclosed on both surfaces', () => {
  assert.ok(d47.includes('The sixth pass (2026-09-19;') && hook.includes('THE SIXTH PASS (2026-09-19;'), 'both surfaces record the pass');
  assert.ok(!hook.includes("if (cmd.unknown || cmd.opaque || 'script' in cmd) { varsPoisoned = true; return; }"), 'the unreachable poison line in recordAssignments is gone');
  assert.ok(hook.includes('varsPoisoned = true;   // B2: what the wrapper ran is not known') && hook.includes('varsPoisoned = true;   // B2\n'), 'the poison of an unknown wrapper option and of an env -S string is set in its own branch of extract');
  assert.ok(hook.includes('if (cmd.script && cmd.script.literal) recurse(cmd.script.text, shell, true);') && hook.includes('const moveUnknown = (why) => { oldDir = null; setUnknown(why); };'), 'a flock -c string is read in a fresh scope and poisons nothing; a cd the guard cannot follow clears OLDPWD');
  assert.ok(d47.includes('is not pinned, disclosed for a ruling') && hook.includes('is not pinned, disclosed for a ruling') && d47.includes('Not pinned, for a ruling:'), 'the poison left for a ruling is disclosed, not claimed pinned');
  assert.ok(!d47.includes(String.fromCharCode(0x2014)), 'no em dash in decision 47');
});

// The seventh pass (2026-09-19): the sixth pass's attacker's finding closed as the readability rule, one predicate keyed on the
// shape of a construct; decision 47 and the hook header record it, the addendum's four items are tied to their hook functions,
// and the text that said a cd under a wrapper never moves the shell is gone.
test('decision 47 and the hook header record the seventh pass: the readability rule as one predicate, the HOME write the addendum reads, the wrapped-cd text, and no claim that the attacker filed nothing', () => {
  assert.ok(d47.includes('The seventh pass (2026-09-19;') && hook.includes('THE SEVENTH PASS (2026-09-19;'), 'both surfaces record the pass');
  assert.ok(d47.includes('THE READABILITY RULE') && hook.includes('THE READABILITY RULE (the sixth pass\'s attacker'), 'the rule is stated on both');
  for (const fn of ['plainSequence', 'plainValue', 'recordPlainWord', 'recordSegment', 'taintWord', 'identifierTokens', 'readableHomeWrites', 'ATTRIBUTE_ONLY_FLAGS', 'WRAPPED_CD_WHY', 'refTargets', 'homeUnreadableNow']) {
    assert.ok(d47.includes(`\`${fn}\``), `decision 47 names ${fn}`);
    assert.ok(new RegExp(`(const|function) ${fn}\\b`).test(hook), `the hook defines ${fn}`);
  }
  assert.ok(hook.includes("const ATTRIBUTE_ONLY_FLAGS = new Set(['g', 'x', 'r']);") && !hook.includes('INERT_DECLARATION_FLAGS'), 'the attribute-only letters are the three and the inert-flags name is gone (round 5\'s addendum: no declaration flag keeps a name readable; the table picks the refusal\'s text)');
  assert.ok(!hook.includes('const recordAssignments = '), 'the list-shaped recorder is gone');
  // the hook's text sits in a template literal, so its backticks are escaped in the source: a needle with bare backticks matched
  // nothing at any head (the seventh pass's mutation lens found the earlier spelling vacuous); the current text is asserted
  // present in the same escaping first, which proves the form, then the old text absent
  assert.ok(hook.includes('an external \\`${name}\\` that moves nothing in this shell'), 'the wrapped-cd text, read in the escaping the source uses');
  assert.ok(!hook.includes('an external \\`${name}\\` that does not exist, so the shell does not move'), 'the wrapped-cd text no longer says the shell does not move');
  assert.ok(hook.includes("builtin: 'runs the shell\\'s own cd in bash and zsh, which moves the shell") && hook.includes("command: 'runs the shell\\'s own cd in bash and dash, which moves the shell"), 'the wrapped-cd table says which shells move');
  // 93bb93b68: the bare pushd, one sentence on each surface
  assert.ok(hook.includes('a bare `pushd` is no such move: bash and dash stay, zsh goes home'), 'the hook header records the bare pushd');
  assert.ok(d47.includes('a bare `pushd`, which bash and dash fail and zsh takes home, leaves the directory unknown'), 'decision 47 records the bare pushd');
  assert.ok(hook.includes("kind: 'homePrefix'") && hook.includes('function readableHomeWrites(segments)'), 'the prefix form has its own reason and the plain HOME= write its pre-pass');
  // round 5 (tests-3): the correction that landed is pinned PRESENT on both surfaces first (the hook wraps the sentence across a
  // comment line, so the needles are the two phrases that fit inside one); the absence conjunct alone had matched at every head
  const hookFlat = hook.replace(/\n\/\/ ?/g, ' ').replace(/\s+/g, ' ');
  for (const needle of ['read as no finding', 'said the attacker filed none']) assert.ok(hookFlat.includes(needle) && d47.includes(needle), `both surfaces carry the correction: ${needle}`);
  assert.ok(!hook.includes('the attacker filed no finding') && !d47.includes('the attacker filed no finding'), 'neither surface repeats the false sentence');
  // round 5 (extra7-4): the addendum's item 4 is pinned on both prose surfaces like items 1 to 3, and tied to the reported text
  const ITEM4 = 'through one probe that reports a shell that is missing or too old with a `NOT RUN` line per leg, never a silent pass';
  assert.ok(d47.includes(ITEM4), 'decision 47 carries the item-4 sentence');
  assert.ok(hook.replace(/\n\/\/ ?/g, ' ').includes(ITEM4), 'the hook header carries the item-4 sentence');
  const guardTest = read('tools', 'romp-track-bash-guard.test.mjs');
  assert.ok(guardTest.includes('`NOT RUN: real ${sh} ${probeWhy(present, sh)}, so its evidence leg did not run') && guardTest.includes("why: 'is not on this runner'"), 'the test file reports the line the two sentences describe');
  // round 5 (correctness-4, tests-5): the rule's canonical statement names the live predicate, five parts, and no function that is gone
  const statement = hook.slice(hook.indexOf('// THE READABILITY RULE (the sixth pass\'s attacker'), hook.indexOf('const RESOLVED_NAME = '));
  assert.ok(statement.length > 1000, 'the statement is where it was');
  assert.ok(statement.includes('plainSequence, plainValue, recordPlainWord, recordSegment, taintWord'), 'the statement names the five parts');
  assert.ok(!statement.includes('recordAssignments'), 'the statement no longer points at the function befa93b3f removed');
  assert.ok(hook.includes('(resolveWord, valueOf, and since the\n// seventh pass recordPlainWord and recordSegment)') && hook.includes('and recordSegment (taintWord) reads each as a write it does not follow'), 'the two other present-tense mentions name the live parts');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 5 of the review (2026-09-20): decision 47 records the two root causes and the riders, each tied to the hook function
// or table that implements it, so a mechanism dropped from the code fails here by name.
test('decision 47 and the hook header record round 5: the frame on parsed structure from one table, the freeze unwrapped, the catch-all refusing, the census derived, the draw widened, and the riders', () => {
  assert.ok(d47.includes('Round 5 of the review (2026-09-20;'), 'decision 47 records the round');
  for (const fn of ['peelIndex', 'compoundHeadOf', 'FRAME_PEEL', 'TIME_OPTIONS', 'BODY_CLOSER', 'judge', 'internalErrorRefusal', 'nodeStringArg', 'pyStringArg']) {
    assert.ok(d47.includes(`\`${fn}\``), `decision 47 names ${fn}`);
    assert.ok(new RegExp(`(const|function) ${fn}\\b`).test(hook), `the hook defines ${fn}`);
  }
  assert.ok(hook.includes("const BODY_CLOSER = {\n  if: { opener: 'then', closer: 'fi' }, while: { opener: 'do', closer: 'done' }, until: { opener: 'do', closer: 'done' },\n  for: { opener: 'do', closer: 'done', list: true }, case: { opener: 'in', closer: 'esac', list: true }, select: { opener: 'do', closer: 'done', list: true },\n  repeat: { opener: 'do', closer: 'done', list: true }, foreach: { opener: ')', closer: 'end', list: true },\n};"), 'the one table, select in it, each head with its opener and closer, zsh\'s repeat and foreach in it since round 5\'s addendum');
  assert.ok(hook.includes("const COMPOUND_HEADS = new Set([...Object.keys(BODY_CLOSER), 'function']);") && hook.includes('for (const [head, { closer }] of Object.entries(BODY_CLOSER)) (CLOSERS[closer] = CLOSERS[closer] || []).push(head);'), 'CLOSERS and COMPOUND_HEADS read the table');
  assert.ok(!hook.includes("const CLOSERS = { fi: ['if'], done: ['while', 'until', 'for'], esac: ['case'] };") && !hook.includes("head === 'if' || head === 'while' || head === 'until' || head === 'for' || head === 'case'"), 'no restated subset of the heads remains');
  assert.ok(hook.includes('if (head != null && Object.hasOwn(CLOSERS, head)) closeCompound(CLOSERS[head]);') && hook.includes('else if (head != null && Object.hasOwn(BODY_CLOSER, head)) {') && hook.includes('compoundBody(seg, peelIndex(seg.words) + 1, pushCompound(head0));') && !hook.includes('if (head in CLOSERS)'), 'the lookups are own-property lookups on the peeled head, at both head reads');
  assert.ok(hook.includes("const frozen = !cmd.wrapped && seq.ok && cmd.name === 'readonly' && plainOptions;") && hook.includes('PEEL FOR THE FRAME, NOT FOR THE FREEZE'), 'the freeze needs the segment\'s own unwrapped readonly with no option word in plain sequence (round 5\'s addendum), the reason beside it');
  assert.ok(hook.includes('if (cmd.wrapped) { taint(name, wroteThrough(name, `a \\`${cmd.name}\\` behind the wrapper'), 'a declaration behind a wrapper taints its names');
  assert.ok(hook.includes('try { return judge(command, cwd); }') && hook.includes('catch (e) { return internalErrorRefusal(e, cwd); }') && !hook.includes(": statErrorRefusal(e.why && e.why.how ? e.why.how : 'write', e.why && e.why.raw ? e.why.raw : 'the path', e) : null; }") && !hook.includes('statErrorRefusal(u.how, u.raw, e); hit = null; }'), 'the catch-all refuses and the two allows that swallowed a throw are gone');
  assert.ok(hook.includes("const dup = op === '>' ? (src.slice(i).match(/^(?:[0-9]+|-)(?=$|[\\s;&|()<>])/) || [null])[0] : null;"), 'the dup rule: a digit run or a dash before a delimiter, never for >>&');
  assert.ok(hook.includes("if (rest !== '') return { template: s };") && hook.includes("const nodeStringArg = (quote, body, after = '') =>"), 'a literal that goes on is a template in both interpreters');
  assert.ok(d47.includes('`tools/romp-track-bash-guard-census.mjs`') && fs.existsSync(path.join(REPO, 'tools', 'romp-track-bash-guard-census.mjs')), 'decision 47 names the census module and it exists');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 5's addendum (2026-09-20): the five lenses' findings closed, each tied to the hook function or table that implements it,
// and the sentences the mutation lens found unpinned pinned on the surface that carries them.
test("decision 47, the hook header and the ledger record round 5's addendum: the conditional and timed groups, the compound body's opener, brace body and one-command body, the coproc frame, the freeze narrowed to an unwrapped plain-sequence readonly with no option word, the declarations dash lacks, and the census's stated reach", () => {
  assert.ok(d47.includes("Round 5's addendum (2026-09-20;"), 'decision 47 records the addendum');
  for (const fn of ['compoundBody', 'pushCompound', 'closeCompoundAt', 'closeOneSegment', 'afterChildClosed', 'popFunction', 'ATTRIBUTE_ONLY_FLAGS']) {
    assert.ok(d47.includes(`\`${fn}\``), `decision 47 names ${fn}`);
    assert.ok(new RegExp(`(const|function) ${fn}\\b`).test(hook), `the hook defines ${fn}`);
  }
  assert.ok(hook.includes("const openGroup = (conditional = null, timed = false) =>") && hook.includes('const cond = frames.find((f) => f.conditional);') && hook.includes('if (frames.some((f) => f.timed)) return { ok: false'), 'a group opened after &&, || or | and a group behind time are not plain sequence');
  assert.ok(hook.includes("else if (frames.some((f) => f.kind === 'group' && f.conditional)) {"), 'the cd handler reads the conditional group');
  assert.ok(hook.includes("if (seg.words.length > p && plainWord(seg.words[p]) && seg.words[p].text === 'coproc') {") && hook.includes("frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy, coproc: true, oneSegment: true });"), 'coproc opens a frame that keeps no name and restores the directory');
  assert.ok(hook.includes("seg.words[k].text === 'always' && brace(seg.words[k + 1]) === '{') { closes--; seg.words.splice(k, 1);"), "zsh's always continues the group");
  assert.ok(hook.includes("if (f.depth === 0 && !(seg.words.length && seg.words[0].text === '{')) { f.oneSegment = true; return 0; }"), 'a function body without braces is one segment, not the enclosing scope');
  assert.ok(hook.includes('if (!portable) { taint(name, wroteThrough(name, `a \\`${cmd.name}\\`, which dash has no command for') && hook.includes('if (!plainOptions) { taint(name, wroteThrough(name, `an option word on \\`${cmd.name}\\`'), 'declare, typeset and an option word on export or readonly taint the name');
  assert.ok(hook.includes("for (const nm of g.names) { readonlyNames.delete(nm); taint(nm, wroteThrough(nm, how, '{ ... }')); }"), 'a freeze inside a piped or backgrounded group is undone at its brace');
  // the census's reach is stated as a qualified sentence on the header (the census lens: the unqualified one was false for twelve planted shapes);
  // the header wraps its sentences across comment lines, so they are read flat
  const hookFlat = hook.replace(/\n\/\/ ?/g, ' ').replace(/\s+/g, ' ');
  assert.ok(hookFlat.includes('a list planted in a scratch copy in one of the shapes the census reads reds it') && !hookFlat.includes('a list planted in a scratch copy reds it (measured with the change)'), 'the header claims the census\'s reach for the shapes it reads and no other');
  assert.ok(hookFlat.includes('every column-0 `const`, `let` or `var` whose initializer opens a Set, an array, an object table, an `Object.fromEntries(` or a `new RegExp(`') && d47.includes('every column-0 `const`, `let` or `var` whose initializer opens a Set, an array, an object table, an `Object.fromEntries(` or a `new RegExp(`'), 'the header and decision 47 name the five initializer forms the census reads');
  assert.ok(d47.includes('two of the three catches that allowed rethrow to the one catch-all, and the process-level catch refuses in place'), 'decision 47 counts the catches as the hook has them (the documents lens: it said all three rethrow)');
  // the sentences the mutation lens found unpinned (M58, M65c, M65d, M71, M72)
  assert.ok(hookFlat.includes('zsh rejects the scalar value and stops the command list, writing nothing; dash copies onto scratch/report.md'), 'the header\'s priced-cost sentence says zsh writes nothing for -a and -A');
  assert.ok(hookFlat.includes('a value the command\'s own text set can appear too, as the path it resolved to (round 5 of the review, 2026-09-20, correcting a sentence B2 had made false)'), 'the header\'s privacy sentence carries the round-5 correction');
  const ledger = read('upstream', '2026-09-18-track-guard-non-literal-targets.md').replace(/\s+/g, ' ');
  assert.ok(ledger.includes('What it reads to resolve a word (since B2, 2026-09-19, and the readability rule that followed; the clause here said until round 5 that it read no variable the command names, and that only HOME\'s value could appear in a refusal, both false since B2)'), 'the ledger\'s resolution clause');
  // round 5's second addendum (2026-09-20): the brace body's closer read after the segment's command, the trailing brace never a
  // writer's operand, the freeze sentence's dated narrowing, the census's spacing, and the vendored README row the right way round
  assert.ok(d47.includes("Round 5's second addendum (2026-09-20;") && d47.includes('a `}` that shares a segment with the command before it'), 'decision 47 records the second addendum');
  assert.ok(hook.includes('if (body) { f.oneSegment = true; seg.words.splice(i, 1); return i; }'), 'a closing brace that shares its segment with the body\'s last command closes the frame after it');
  assert.ok(hook.includes("const closer = (w) => plainWord(w) && w.text === '}';") && hook.includes('variants = [cut, ...variants];'), 'a writer is judged with and without its trailing braces');
  assert.ok(d47.includes("round 5's addendum, 2026-09-20, narrowed this further, below: the freeze is an unwrapped `readonly` with no option word in plain sequence alone"), 'the round-5 freeze sentence carries the dated narrowing beside it (d47 is read flat)');
  const censusSrc = fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-census.mjs'), 'utf8');
  assert.ok(censusSrc.includes('(?:const|let|var)\\s+([A-Za-z_$][\\w$]*)\\s*=\\s*(new Set\\(') && censusSrc.includes('any spacing after the keyword and around the `=`'), 'the census reads any spacing after the keyword and says so');
  const vendorReadme = read('vendor', 'track-changents', 'README.md');
  assert.ok(vendorReadme.includes('says that no declaration flag, and no `declare`, `typeset` or `local` (dash has none of the three; `export` and `readonly` with no option word are the two declarations every shell performs), keeps a name readable, that a `{ }` group opened after `&&`, `||` or `|` does not either (each of those leaves the name unreadable)') && !vendorReadme.includes('keep a name readable'), 'the vendored README states the declaration rule the way the contract does');
  assert.ok(ledger.includes('Round 4 of the review (2026-09-20) found the frame decision keyed on the segment\'s first word') && ledger.includes('derives the census of the hook\'s lists from its source at test time'), 'the ledger\'s round-4 and round-5 paragraph with the census mention');
  assert.ok(ledger.includes("round 5's addendum (2026-09-20)") && ledger.includes('tools/romp-track-bash-guard-census.mjs'), 'the ledger records the addendum and names the census module in its where line');
  assert.ok(hook.includes("u: { bash: 'nounset', zsh: 'nounset', why: 'an unset variable is an error that stops the command; the guard reads no value from the environment beyond HOME' },"), 'the u letter\'s why');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// The seventh pass's attacker (2026-09-19): decision 47 and the hook header record the two misses and the readonly sibling, each
// tied to the hook function that closes it, and the wrapper list on the three prose surfaces names zsh's modifiers.
test("decision 47 and the hook header record the seventh pass's attacker: nesting-aware group frames, zsh's precommand modifiers in the wrapper set and on every prose surface, the readonly value kept, and the shadowed poison gone", () => {
  assert.ok(d47.includes("The seventh pass's attacker (2026-09-19;") && hook.includes("THE SEVENTH PASS'S ATTACKER (2026-09-19;"), 'both surfaces record the pass');
  for (const fn of ['openGroup', 'closeGroups', 'pendingClose', 'noteGroupName', 'ZSH_MODIFIERS', 'readonlyNames', 'WRAPPED_CD_WHY']) {
    assert.ok(d47.includes(`\`${fn}\``), `decision 47 names ${fn}`);
    assert.ok(new RegExp(`(const|let) ${fn}\\b`).test(hook), `the hook defines ${fn}`);
  }
  assert.ok(hook.includes("const ZSH_MODIFIERS = new Set(['noglob', 'nocorrect', '-']);") && hook.includes("'chrt', 'numactl', ...ZSH_MODIFIERS]);"), 'the three modifiers, and they are in PREFIXES');
  for (const m of ['noglob', 'nocorrect', "'-'"]) assert.ok(new RegExp(`^  ${m}: \\{ argShort: '', flagShort: '', argLong: \\[\\], flagLong: \\[\\] \\},$`, 'm').test(hook), `${m} has an empty option table`);
  for (const m of ['noglob', 'nocorrect', "'-'"]) assert.ok(hook.includes(`  ${m}: 'is a zsh precommand modifier, so in zsh the shell\\'s own cd runs and moves it, and no command in bash and dash, which stay',`), `${m} has its wrapped-cd text`);
  const prose = { 'hooks/README.md': hooksReadme, 'docs/install.md': read('docs', 'install.md'), 'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md') };
  for (const [name, text] of Object.entries(prose)) assert.ok(/`exec`, and since the seventh pass zsh's precommand modifiers `noglob`, `nocorrect` and `-`, which hid the writer behind them\)/.test(text.replace(/\s+/g, ' ')), `${name} names the modifiers in the wrapper list`);
  assert.ok(!hook.includes('carries an option the shell fills in ('), 'the poison M1\'s per-segment detector shadowed is gone');
  assert.ok(hook.includes("if (readonlyNames.has(name)) return;") && hook.includes("if (readonlyNames.has(name)) continue;"), 'a readonly name keeps its value in both recording paths');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});
