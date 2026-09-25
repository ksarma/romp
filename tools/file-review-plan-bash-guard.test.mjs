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
// since round 3's mutation pass (2026-09-19) inverted each and nothing went red. Synthetic: only the repo's own text, and, for the
// census of the README pin's signal names, the signal names the shells present print and take, the system's <signal.h> and one scratch
// project under the temp directory, where the hook's evaluate judges a trap set on each name.
// Run: node --test tools/file-review-plan-bash-guard.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
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
  assert.ok(hook.includes('const r = readScript(sh.script, `\\`${name} -c\\` script`);') && hook.includes('for (const t of r.texts) recurse(t, name, undefined,') && hook.includes("recurse(body, name, undefined, '', [])") && hook.includes('const lexOpts = ifsNamed ? { ifsNamed: true } : {};') && hook.includes('let lexed = lex(command, shell, lexOpts);') && hook.includes("const ANSI_C_SHELLS = new Set(['bash', 'zsh']);"), 'a script handed to a shell is lexed as that shell reads `$\'...\'` (the lexer takes the IFS mark since round 6\'s fourth commit)');
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
  // round 7's twenty-fourth commit (the reviewer's round-6 ruling on extra6-1): the option grammar is per shell, stated as the hook reads it (the
  // behaviour: the twenty-fourth commit's rows in tools/romp-track-bash-guard.test.mjs, C-o-glued-nad, C-emu-sh-nad, B-bash-oc-nad, S-sh-oglued,
  // X-bash-plus-c-nad, X-dash-o-stdin-pipe-nad, X-dash-sc-pipe-nad)
  assert.ok(d47.replace(/\s+/g, ' ').includes("while zsh reads the letters after a cluster's first `o` as that option's name and takes the next word after `--emulate`; the names `sh` and `ksh` are read under all three grammars, and an option's value word that may become no word or several is an option word the hook reads or refuses; a `c` counts with either sign and so does bash's `s`, a lone `+` or `+-` ends zsh's options, zsh reads a digit in a cluster as a letter, a blank as the end of the word, a trailing `-` as the end of the options and `+-emulate` as `--emulate`, an option that reads the script from the standard input by name (dash's `stdin`, zsh's SHIN_STDIN or STDIN, in any spelling zsh takes) counts as `s`, an option name dash or zsh may read so is an option word, and dash's `-sc` is read as its `-c` text and then its standard input") && hook.includes("const SHELL_GRAMMARS = { bash: ['bash'], dash: ['dash'], zsh: ['zsh'] };") && hook.includes("else if ((shell === 'bash' && (t === '-O' || t === '+O')) || (shell === 'zsh' && (t === '--emulate' || t === '+-emulate'))) take(false);") && hook.includes("else if (ch === 'o') { if (i === t.length - 1) take(true); else byName(t.slice(i + 1), sign); break; }") && hook.includes("const takeS = (sign) => { s = shell === 'bash' || sign === '-'; };") && hook.includes("if (shell === 'dash' && name === 'stdin') s = sign === '-';") && hook.includes("if (c) return done(shell === 'dash' && s ? { script: operand || null, stdin: true, fd: null, argsAt: operand ? at(operand) + 1 : args.length } : { script: operand || null, argsAt: operand ? at(operand) + 1 : args.length });"), 'decision 47 states the per-shell option grammar the hook reads');
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
  assert.ok(d47.includes('a process substitution\'s command is read like a `$(...)`') && hook.includes("if (testGrammar && (c === '>' || c === '<') && src[i + 1] === '(') {"));
  assert.ok(d47.includes('`cd` moving the working directory for what follows, inside `( ... )` only up to the `)`'));
  assert.ok(hook.includes("frames.push({ kind: 'subshell', dir, unknownDir, unknownWhy, stdinFrom: pipedFrom(), stdinText: closerStdin(idx, 'subshell') });"));   // stdinFrom and stdinText since the third fix-up
  assert.ok(hook.includes("case 'xargs': sawOpaqueCommand = true; break;") && hook.includes("case 'eval': case 'trap': {") && hook.includes("if (name === 'eval' && !read.held) sawOpaqueCommand = true;") && hook.includes("const door = name === 'eval' ? frameText(seg, idx, cmd, '`eval`') : trapText(seg, idx, cmd, sigs);"), 'xargs is opaque; since round 6\'s second commit eval and trap with text the resolver reads are scripts of this shell, and eval with text it does not read stays opaque (its bind of the list to values not read goes through THE BIND\'S FRAME since round 7\'s nineteenth commit, and through THE UNHELD ROAD\'s one reader, readInPlace, since the twenty-third)');
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

// THE SIGNAL NAMES the README pin reads (round 7 of fork PR #780 review, thirty-eighth commit; the thirty-ninth derives them from what a trap
// takes): a signal's name is a word of a closed list, unlike a paraphrase, so the pin reads every one. The list is every name a trap takes in
// a present shell, and a trap takes names no list prints: zsh's trap takes CLD, the System V name for CHLD, which neither its `$signals` nor
// its `kill -l` prints, so the thirty-eighth commit, which took the list from the printed lists alone, missed it (the reviewer's verifier).
// The names, the SIG prefix taken off: the signals (RTMIN and RTMAX with their offsets, `RTMIN+3`, `RTMAX-2`, which the pattern reads); EMT
// and INFO, which the BSD list adds and no Linux shell takes, so the census checks them only on a runner whose shells take them (the CI shell
// job's weekly macOS cell); and the names a trap takes that are not signals, EXIT in every shell, ERR and DEBUG in bash and zsh, RETURN in
// bash, ZERR in zsh, each named in its shell's manual under trap. The census test after the pin runs `trap : NAME` in each present shell over
// every candidate it derives (the names each shell prints, the SIG names the system's <signal.h> defines as the C preprocessor reads it, CLD
// among them, node's os.constants.signals, and this list), each bare and with SIG, as spelled, in lower case and in title case, and reds on a
// spelling a shell takes that the pin does not read; a name a trap takes that no source there holds is beyond it. SIGNAL_WORD reads each name bare or
// with the SIG prefix, in any case (bash takes `int` and `sigint`, dash takes `int`: EV-trap-lower and EV-trap-sigint-lower in
// tools/romp-track-bash-guard.test.mjs; the case witness in the pin below runs every mix of upper and lower case), and inflected as English inflects a word (SIGNAL_INFLECTION: INTs, BUSes, EXITed, piped, EXITing,
// piping, STOPped, QUITting, a plural or verb ending with the last letter doubled or a final e dropped before it), as the eval and trap stems
// are read inflected; its boundaries are the ASCII letters alone, so a name joined to any other character is read, a digit, an underscore,
// punctuation, a tab or a character outside ASCII (sigint_handler, on_exit, sigint2, SigInt_handler: the fortieth commit, after the reviewer's
// verifier found those forms unread by boundaries that also stopped at a digit or an underscore; the boundary witness in the pin below runs
// every name in lower case beside every UTF-16 code unit, the unit the pattern reads, and each name in each of the six spellings
// SIGNAL_SPELLINGS makes beside each printable ASCII character that is not a letter: the forty-first commit, after the verifier found the
// fortieth commit's witness, printable ASCII alone, green with U+2026, U+2019 or the tab read as a letter; and the premise pin there holds
// that the pattern reads a unit outside its match through those two boundaries alone, so a form read beside a space is read beside every unit
// that is not a letter: the forty-second commit, after the verifier found a SIG spelling, an inflected form and a boundary reading two units,
// each conditioned on a unit the witnesses never put beside that form). SIGNAL_UPPER reads a name in upper case, or SIG and an upper-case run (a
// name another system's list adds), anywhere in a word (nonINT, INThandlers, unSIGTHR). A name in lower or mixed case glued to letters beyond
// an inflection is not read, since in lower case a name opens or ends many English words (print, still, interrupt, terminal, pipeline): the
// third boundary the README pin states. signalNamesIn's text, the union of the two runs and nothing else, is the one reader every witness and
// the README pin run, and THE READER pin in the test below holds that text.
const SIGNAL_NAMES = ['HUP', 'INT', 'QUIT', 'ILL', 'TRAP', 'ABRT', 'IOT', 'BUS', 'FPE', 'KILL', 'USR1', 'SEGV', 'USR2', 'PIPE', 'ALRM', 'TERM',
  'STKFLT', 'CHLD', 'CLD', 'CONT', 'STOP', 'TSTP', 'TTIN', 'TTOU', 'URG', 'XCPU', 'XFSZ', 'VTALRM', 'PROF', 'WINCH', 'IO', 'POLL', 'PWR', 'SYS',
  'RTMIN', 'RTMAX', 'EMT', 'INFO', 'EXIT', 'ERR', 'DEBUG', 'RETURN', 'ZERR'];
const SIGNAL_SPELLINGS = (bare) => { const title = bare[0] + bare.slice(1).toLowerCase(); return [bare, `SIG${bare}`, bare.toLowerCase(), `sig${bare.toLowerCase()}`, title, `Sig${title}`]; };
const SIGNAL_INFLECTION = '(?:e?s|e?d|ing|(?<=([A-Za-z]))\\1(?:es|ed|ing))?';   // the group captures the name's last letter, so only that letter doubles
const SIGNAL_WORD = new RegExp(`(?<![A-Za-z])(?:sig)?(?:${SIGNAL_NAMES.map((n) => (n.endsWith('E') ? `${n}|${n.slice(0, -1)}(?=ing)` : n)).join('|')})(?:[+-]\\d+)?${SIGNAL_INFLECTION}(?![A-Za-z])`, 'gi');
const SIGNAL_UPPER = new RegExp(`[A-Za-z0-9_]*(?:SIG[A-Z0-9]+|${SIGNAL_NAMES.join('|')})[A-Za-z0-9_]*`, 'g');
const signalNamesIn = (text) => [...new Set([...(text.match(SIGNAL_WORD) || []), ...(text.match(SIGNAL_UPPER) || [])])];

test('the install guide, the hook\'s README row and the ledger entry say a name built from $RANDOM or $SECONDS is refused inside a tracked project, in every shell, and the hook\'s numeric set is the process id alone; the README row states what passes unread as the residual property does', () => {
  assert.ok(installDoc.includes('A temp file named only by the shell\'s process id (`$$`), at an absolute path where no tracked file could land'), 'docs/install.md: the exception, as the code allows it');
  assert.ok(installDoc.includes('still runs; a name built from `$RANDOM` or `$SECONDS` is refused, since a script can reassign those'), 'docs/install.md: the refused names, with the reason');
  const row = hooksReadme.split('\n').find((l) => l.startsWith('| `romp-track-bash-guard.mjs` |'));
  assert.ok(row, 'the hook has a row in hooks/README.md');
  assert.ok(row.includes('a target whose only expansions are `$$` or `${$}`, the shell\'s process id, at an absolute path outside every project in play is allowed, and nothing else is'), 'hooks/README.md: the exception');
  assert.ok(row.includes('since `$RANDOM`, `$SECONDS` and every other name can be unset or shadowed by the command and then hold a path, so a `log.$RANDOM` inside a tracked project is refused in every shell, a deliberate false refusal recoverable in one step'), 'hooks/README.md: the refused names, with the reason');
  // round 7 of fork PR #780 review, thirty-fifth commit (the reviewer's regression-1): the row's clause on a command it cannot read states the
  // property, a text the guard cannot read, and names neither eval nor trap as unreadable, since both are scripts of this shell when their text
  // is one the guard reads (the round-5 row listed `eval` and 'a script held in a variable' as passing). This pin holds the README's WORDS to the
  // residual property; what the hook does is executed elsewhere: the refusals by EV-eval, EV-eval-var and EV-trap in tools/romp-track-bash-guard.test.mjs
  // (the round 6, second commit test of THE ALIAS ROAD and THE HEAD SPLICE) and the passes by RT-read-var-head and RT-xargs in THE RESIDUAL TABLE
  const CLAUSE = 'A read passes; a command whose text it cannot read (a script held in a name it cannot read, an eval of such a name, xargs) passes, except that such a name or eval whose literal operand names a tracked file is refused (THE RESIDUAL PROPERTY, later in this row);';
  assert.ok(row.includes(CLAUSE), 'hooks/README.md: the clause on a command whose text the guard cannot read states the residual property (its executed rows: EV-eval, EV-eval-var and EV-trap refused, RT-read-var-head and RT-xargs allowed, in tools/romp-track-bash-guard.test.mjs)');
  assert.ok(!row.includes('(eval, xargs, a script held in a variable)'), 'hooks/README.md: the round-5 parenthetical is gone');
  // keyed on the names' stems, not on whole words (round 7 of fork PR #780 review, thirty-seventh commit; the reviewer's verifier appended
  // ' a text set by traps passes;' and ' evals of such a text pass;' after CLAUSE, and the thirty-sixth commit's patterns, which matched eval and
  // trap as whole words only, stayed green), and on every signal's name (the thirty-eighth commit; the verifier appended ' a handler set for
  // SIGINT passes;', ' a handler the shell runs on EXIT passes;' and ' a handler for SIGTERM, SIGHUP or ERR passes;', and the thirty-seventh
  // commit's pattern, which read the word signal and no signal's name, stayed green), including every name a present shell's trap takes and
  // inflected or glued forms (the thirty-ninth commit; the verifier's ' a handler set for CLD passes;', a name zsh's trap takes that no list
  // prints, and ' handlers for INTs pass;' and ' handlers run on EXITs pass;', read by neither pattern, stayed green), and a name joined to a
  // digit or an underscore (the fortieth commit; the verifier's ' a sigint_handler function passes;', ' a handler set in a function named
  // on_exit passes;', ' an exit_handler set by the command passes;' and ' handlers for sigint2 pass;' stayed green, since SIGNAL_WORD's
  // boundaries also stopped at a digit or an underscore, while ' an int-handler passes;' went red): with THE RESIDUAL PROPERTY's statement
  // (whose classes name eval as a script the class holds and as a producer's consumer; the developer-surface pin below holds it identical) and
  // CLAUSE set aside, and each phrase below set aside where it stands exactly once (the B2 clause's names set by an eval, which keep the
  // working directory's verdict, node's `--eval=` option, the exit status among the kinds of shell option the guard takes as inert, and piped
  // in its ordinary sense, a text or a group fed through a pipe, four places, none a claim that a command passes), the row holds neither stem,
  // eval or trap, in any case, at a word's start or inside a word, no word signal, and no signal's name (SIGNAL_NAMES, bare or with SIG, in any
  // case, inflected, joined to any character that is not an ASCII letter, or in upper case anywhere in a word); an inflected form
  // (evals, evaled, traps, trapped), a prefixed form (untrapped, reevaluated) or a handler named by its signal (SIGINT, int, EXIT, RTMIN+3,
  // CLD, INTs, EXITed, nonINT, sigint_handler, on_exit, sigint2) as passing reds here, and the witness assertions below red when either
  // pattern stops reading an inflected or glued form, or SIGNAL_WORD stops reading a name beside any character that is not an ASCII
  // letter, starts reading a name in lower case glued to one, or stops reading a name in a mix of upper and lower case. Three spellings are beyond a pin on words, stated here and not read: a signal given by its number, since the row holds numbers
  // from 0 to 64 in other senses (the witness assertion below reds when it no longer does, and the number can join the pin then); a name in
  // lower or mixed case glued to letters beyond an inflection (unint, Intx), since the row holds lower-case words a name opens or ends
  // (pipeline, into, error: the witness assertion below reds when none stands, and the reading can widen then); and a paraphrase that uses
  // none of these words (on interrupt, when the shell ends). The behaviour is held by execution, not here: a trap's action is refused where it
  // names a tracked file for the signal word each executed row the message names carries, and, by the signal census below, for each spelling
  // a present shell's trap takes among the names and the six spellings the census derives
  const propStart = row.indexOf('THE RESIDUAL PROPERTY. The guard refuses a write only when');
  const propEndText = 'A shape outside these classes that reaches a tracked file is a rule to state, not a residual.';
  const propEnd = row.indexOf(propEndText, propStart);
  assert.ok(propStart >= 0 && propEnd > propStart, 'hooks/README.md: the row carries THE RESIDUAL PROPERTY, opening and closing sentences found');
  let rest = row.slice(0, propStart) + row.slice(propEnd + propEndText.length);
  assert.equal(rest.split(CLAUSE).length, 2, 'hooks/README.md: CLAUSE stands once outside the property');
  rest = rest.split(CLAUSE).join(' ');
  for (const phrase of ['by a `read`, a loop, an eval, a sourced file or a function call', "and node's `--eval=` with its code", 'the inert allowlist (exit status, tracing, history recording',
    'a literal echo or printf piped into a shell reading stdin', 'reads what was piped or redirected to it', 'a pipeline or a piped group', 'pipeline, piped group or body scope']) {
    assert.equal(rest.split(phrase).length, 2, `hooks/README.md: the phrase set aside stands exactly once: ${phrase}`);
    rest = rest.split(phrase).join(' ');
  }
  assert.deepEqual(rest.match(/[a-z]*(?:eval|trap|signal)[a-z]*/gi) || [], [], 'hooks/README.md: outside THE RESIDUAL PROPERTY and CLAUSE no clause names eval, trap or a signal in any spelling, an inflected or prefixed form included (a text the guard reads in either is refused where it names a tracked file: EV-eval, EV-eval-var, EV-trap; a text it cannot read passes only as CLAUSE says: RT-read-var-head, RT-xargs)');
  // THE READER (the forty-third commit, after the reviewer's verifier found two rewrites placed in signalNamesIn, U+00A0 before sig and
  // U+2026 after ts each turned into a letter, green with the premise pin): signalNamesIn's text is READER, the union of the two runs and
  // nothing else, so a statement placed before, between or after them reds here, and the two patterns carry the flags stated. What the
  // witnesses and the premise pin hold of the two patterns is then what the README pin reads
  const READER = '(text) => [...new Set([...(text.match(SIGNAL_WORD) || []), ...(text.match(SIGNAL_UPPER) || [])])]';
  assert.deepEqual({ signalNamesIn: Function.prototype.toString.call(signalNamesIn), flags: [SIGNAL_WORD.flags, SIGNAL_UPPER.flags] }, { signalNamesIn: READER, flags: ['gi', 'g'] },
    'THE READER: signalNamesIn is the union of SIGNAL_WORD\'s and SIGNAL_UPPER\'s matches, in that order, and nothing else, and the two patterns carry the flags stated, so what the witnesses and the premise pin hold of the two patterns is what the README pin reads; a rewrite of the text before or between the two runs, or of the names after them, reds here');
  // the witnesses of the two patterns' reach (the thirty-ninth commit): every name in each inflected form, bare and with SIG, as spelled and in
  // lower case, is read by SIGNAL_WORD, and every name glued to letters on either side in upper case by SIGNAL_UPPER, so a mutation that drops
  // an ending, the doubled letter, the dropped e or the glued reading reds here even while the committed row holds no such word
  for (const n of SIGNAL_NAMES) {
    const last = /[A-Z]$/.test(n) ? n.slice(-1).toLowerCase() : '';
    const forms = [...['s', 'es', 'd', 'ed', 'ing', ...(last ? [`${last}es`, `${last}ed`, `${last}ing`] : [])].map((end) => n + end), ...(n.endsWith('E') ? [`${n.slice(0, -1)}ing`] : [])];
    for (const f of forms.flatMap((x) => [x, x.toLowerCase(), `SIG${x}`, `sig${x.toLowerCase()}`])) assert.ok(signalNamesIn(` handlers for ${f} pass; `).includes(f), `the README pin reads ${f}, the name ${n} inflected (SIGNAL_WORD, SIGNAL_INFLECTION)`);
    for (const f of [`non${n}`, `${n}handlers`, `re${n}ed`, `unSIG${n}`]) assert.ok(signalNamesIn(` handlers for ${f} pass; `).includes(f), `the README pin reads ${f}, the name ${n} in upper case glued to letters (SIGNAL_UPPER)`);
  }
  assert.ok(signalNamesIn(' a handler for unSIGTHR passes; ').includes('unSIGTHR'), 'the README pin reads SIG and an upper-case run glued to letters, a name another system adds (SIGNAL_UPPER)');
  // the boundary witness (the fortieth commit; the forty-first derives its population from the rule it pins, after the reviewer's verifier
  // found the fortieth commit's, the printable ASCII characters that are not letters, green with U+2026, the one character outside ASCII the
  // row holds, U+2019 or the tab read as a letter). The rule: a letter is [A-Za-z], and any other character beside a name is a boundary.
  // SIGNAL_WORD has no u or v flag, so it reads a string as UTF-16 code units and each boundary looks at the one unit beside the match, whatever
  // the spelling (the i flag folds no unit outside ASCII into [A-Za-z]; the premise pin after the flag assertion holds that nothing else in
  // either pattern looks outside the match); so the population is every unit from 0x0000 to 0xFFFF, split by the
  // rule into JOINERS, the 65484 units that are not ASCII letters (the controls, a tab and a newline among them, every character outside ASCII
  // up to U+FFFF, and each half of a surrogate pair, which is how a character above U+FFFF stands beside a name), and the 52 letters. Every name
  // in lower case, a spelling SIGNAL_UPPER cannot read, is read with each joiner on both sides (a boundary that stops at that unit on either
  // side leaves it unread) and is not read with a letter before it or after it (the third boundary, each side on its own); and every name in
  // each of the six spellings SIGNAL_SPELLINGS makes, with each printable joiner (a space, a digit, an underscore, punctuation) before it, after
  // it and on both sides, is read as that spelling (on_exit, sigint_handler, sigint2, SigInt_handler). A boundary class that stops at any unit
  // that is not an ASCII letter, or reads a name in lower case glued to one, reds here even while the committed row holds no such word, a
  // condition on a unit outside the match placed anywhere else in either pattern reds the premise pin, and one placed in signalNamesIn's
  // body reds THE READER pin. THE REALM (the reviewer's ruling on the forty-fourth commit): the boundary witness runs in an unmodified
  // JavaScript realm, its built-ins as shipped, and so does every witness and pin in this test and in the signal census after it; no
  // assertion here checks that. signalNamesIn relies on String.prototype.match, RegExp.prototype[Symbol.match], RegExp.prototype.exec, the
  // RegExp global, unicode and unicodeSets getters, the Set constructor, Set.prototype.add, Set.prototype[Symbol.iterator] and the set
  // iterator's next, and Array.prototype[Symbol.iterator] and the array iterator's next; each witness reads its result with
  // Array.prototype.includes; the premise pin reads each pattern's source through the RegExp source getter; the flag assertion reads the
  // RegExp unicode and unicodeSets getters; and THE READER reads signalNamesIn's text through Function.prototype.call and
  // Function.prototype.toString, and the flags through the RegExp flags getter and the eight flag getters it calls (hasIndices, global,
  // ignoreCase, multiline, dotAll, unicode, unicodeSets, sticky). Out of scope, as one limit: a test that rewrites what a reading is handed
  // (the row, or rest cut from it), that replaces a built-in or an accessor (where it stands, or for a pattern alone by an own property, a
  // subclass or a proxy), or that rebinds a name the reading resolves (signalNamesIn at a call site, or SIGNAL_WORD, SIGNAL_UPPER or Set
  // around signalNamesIn), before, between or after the readings; each changes the test itself, as an edit to an assertion's expected side
  // does
  assert.ok(!SIGNAL_WORD.unicode && !SIGNAL_WORD.unicodeSets, 'the boundary witness runs every UTF-16 code unit, the units SIGNAL_WORD reads while it has no u or v flag; with either flag it reads a character above U+FFFF as one unit, and the witness must run those');
  // THE PREMISE the witnesses rely on for every form but the lower-case name (the forty-second commit, after the reviewer's verifier found
  // the forty-first commit's witnesses green under three mutants that each leave a README word unread: a SIG spelling unread after U+00A0, an
  // inflected form unread before U+2026, and a lookahead that reads two units. The six spellings run beside printable ASCII alone and the
  // inflected, offset, mixed-case and glued forms beside a space alone, and no set of flanks closes a condition on two units). A pattern
  // reads a unit outside its match only through an assertion, and ECMAScript's Assertion production has eight: ^, $, \b, \B, (?=, (?!, (?<=
  // and (?<!. SIGNAL_WORD holds a leading (?<! and a trailing (?!, each over one character class, which with neither u nor v reads the one
  // unit beside the match; inside the match it holds the E-dropped stems' (?=ing), whose three units only the inflection's ing can then
  // consume, and the inflection's (?<=([A-Za-z])), which looks back at the name's last unit; SIGNAL_UPPER holds none. While that holds, a
  // form read beside a space is read beside any unit the two classes answer for as they answer for a space, since the path that matched it
  // reads nothing else outside it, and any match over one of its units makes the pin's reading non-empty. So each form a witness runs beside
  // a space is read beside each joiner, and the full-unit witness below fixes what the two classes admit, unit by unit, on each side. The pin
  // keys on the spelling of the assertions inside the match (a new or reworded one reds it until the argument is made here) and on the ends'
  // shape, one class each, not on the classes' contents, which the witness holds by execution. The reader's own fixture holds each of the
  // eight forms and the places one is not (a character class, an escaped parenthesis, a named group, an escaped backslash)
  const assertionsIn = (src) => {
    const found = [];
    for (let i = 0, inClass = false; i < src.length; i++) {
      const ch = src[i];
      if (ch === '\\') { if (!inClass && (src[i + 1] === 'b' || src[i + 1] === 'B')) found.push({ at: i, text: src.slice(i, i + 2) }); i++; }
      else if (inClass) inClass = ch !== ']';
      else if (ch === '[') inClass = true;
      else if (ch === '^' || ch === '$') found.push({ at: i, text: ch });
      else if (/^\(\?<?[=!]/.test(src.slice(i, i + 4))) {
        let j = i;
        for (let depth = 0, cls = false; j < src.length; j++) {
          if (src[j] === '\\') j++;
          else if (cls) cls = src[j] !== ']';
          else if (src[j] === '[') cls = true;
          else if (src[j] === '(') depth++;
          else if (src[j] === ')' && --depth === 0) break;
        }
        found.push({ at: i, text: src.slice(i, j + 1) });
      }
    }
    return found;
  };
  const READER_FIXTURE = '^a$\\bb\\B(?=c)(?!d)(?<=e)(?<!f)[\\b^$(?=]\\(?=g\\)(?<n>h)(?:i)\\\\b';
  assert.ok(new RegExp(READER_FIXTURE), 'the reader\'s fixture is a pattern');
  assert.deepEqual(assertionsIn(READER_FIXTURE).map((a) => a.text), ['^', '$', '\\b', '\\B', '(?=c)', '(?!d)', '(?<=e)', '(?<!f)'], 'the assertion reader finds each of the eight assertions ECMAScript has, and none in a character class, after an escaped parenthesis, in a named or non-capturing group, or after an escaped backslash');
  const wordAssertions = assertionsIn(SIGNAL_WORD.source);
  const [lead, trail] = [wordAssertions[0], wordAssertions[wordAssertions.length - 1]];
  const endsHold = wordAssertions.length >= 2 && lead.at === 0 && /^\(\?<!\[(?:[^\\\]]|\\.)*\]\)$/.test(lead.text)
    && trail.at + trail.text.length === SIGNAL_WORD.source.length && /^\(\?!\[(?:[^\\\]]|\\.)*\]\)$/.test(trail.text);
  const ENDS = 'a (?<! at the start and a (?! at the end, each over one character class';
  assert.deepEqual({ ends: endsHold ? ENDS : [lead, trail], inside: wordAssertions.slice(1, -1).map((a) => a.text), upper: assertionsIn(SIGNAL_UPPER.source).map((a) => a.text) },
    { ends: ENDS, inside: [...SIGNAL_NAMES.filter((n) => n.endsWith('E')).map(() => '(?=ing)'), '(?<=([A-Za-z]))'], upper: [] },
    'THE PREMISE: SIGNAL_WORD reads a unit outside its match only through its leading (?<! and trailing (?!, each over one character class whose units the full-unit witness holds, and SIGNAL_UPPER through none; every other assertion in either source (^, $, \\b, \\B or a lookaround) looks inside the match, the E-dropped stems\' (?=ing) and the inflection\'s (?<=([A-Za-z])), as the comment argues; a form the witnesses run beside a space or printable ASCII alone is read beside every joiner only while this holds');
  const UNITS = Array.from({ length: 0x10000 }, (_, u) => String.fromCharCode(u));
  const JOINERS = UNITS.filter((c) => !/[A-Za-z]/.test(c));
  const LETTERS = UNITS.filter((c) => /[A-Za-z]/.test(c));
  assert.ok(UNITS.length === 0x10000 && UNITS.every((c, u) => c.charCodeAt(0) === u) && LETTERS.length === 52 && JOINERS.length === 0x10000 - 52
    && ['_', ' ', '-', ...'0123456789', '\t', '\n', '\u00a0', '\u2019', '\u2026', '\ud83d', '\ude00', '\uffff'].every((c) => JOINERS.includes(c)),
    'the boundary witness runs every code unit from 0x0000 to 0xFFFF that is not one of the 52 ASCII letters, the underscore, each digit, the space, the hyphen, the tab, the newline, U+00A0, U+2019, U+2026, both halves of a surrogate pair and U+FFFF among them');
  const unit = (c) => `U+${c.charCodeAt(0).toString(16).toUpperCase().padStart(4, '0')}`;
  const offRule = [];
  let ran = 0;
  for (const n of SIGNAL_NAMES) {
    const s = n.toLowerCase();
    for (const c of JOINERS) { ran++; if (!signalNamesIn(` handlers for x${c}${s}${c}x pass; `).includes(s)) offRule.push(`${s} unread with ${unit(c)} on both sides`); }
    for (const c of LETTERS) for (const f of [`x${c}${s}`, `${s}${c}x`]) { ran++; if (signalNamesIn(` handlers for ${f} pass; `).includes(s)) offRule.push(`${s} read in ${f}`); }
  }
  assert.equal(ran, SIGNAL_NAMES.length * (JOINERS.length + 2 * LETTERS.length), 'the boundary witness ran every name against every code unit, each joiner once and each letter on each side');
  assert.deepEqual(offRule.slice(0, 12), [], `the README pin reads every name in lower case beside each of the ${JOINERS.length} code units that are not ASCII letters, and none glued to an ASCII letter (SIGNAL_WORD's boundaries: ${offRule.length} readings off the rule, the first listed)`);
  const PRINTABLE = JOINERS.filter((c) => c >= ' ' && c <= '~');
  assert.ok(PRINTABLE.length === 0x7f - 0x20 - 52 && ['_', ' ', '-', ...'0123456789'].every((c) => PRINTABLE.includes(c)), 'the spelling witness runs every printable ASCII character that is not a letter, the underscore, each digit, the space and the hyphen among them');
  for (const n of SIGNAL_NAMES) for (const s of SIGNAL_SPELLINGS(n)) for (const c of PRINTABLE) for (const f of [`x${c}${s}`, `${s}${c}x`, `x${c}${s}${c}x`]) {
    assert.ok(signalNamesIn(` handlers for ${f} pass; `).includes(s), `the README pin reads ${s} in ${JSON.stringify(f)}, the name ${n} joined to ${JSON.stringify(c)}, a character that is not a letter (SIGNAL_WORD's boundaries)`);
  }
  // the case witness (the fortieth commit): every name in every mix of upper and lower case, bare and after SIG in every mix, is read as
  // spelled, so a pattern that reads the six spellings and not every mix reds here
  const caseMixes = (w) => [...new Set(Array.from({ length: 2 ** w.length }, (_, m) => [...w].map((ch, i) => ((m >> i) & 1 ? ch.toLowerCase() : ch.toUpperCase())).join('')))];
  assert.ok(caseMixes('int').includes('iNt') && caseMixes('SIG').length === 8, 'the case witness runs every mix, iNt among them');
  for (const n of SIGNAL_NAMES) for (const s of [...caseMixes(n), ...caseMixes('SIG').flatMap((p) => caseMixes(n).map((b) => p + b))]) {
    assert.ok(signalNamesIn(` handlers for ${s} pass; `).includes(s), `the README pin reads ${s}, the name ${n} in a mix of upper and lower case (SIGNAL_WORD ignores case)`);
  }
  const TRAP_ROWS = ['EV-trap', 'EV-trap-INT', 'EV-trap-SIGTERM', 'EV-trap-lower', 'EV-trap-sigint-lower', 'EV-trap-num', 'EV-trap-zero', 'EV-trap-ERR', 'EV-trap-ZERR', 'EV-trap-DEBUG', 'EV-trap-RETURN', 'EV-trap-SIGEXIT', 'EV-trap-CLD'];
  assert.deepEqual(signalNamesIn(rest), [], `hooks/README.md: outside THE RESIDUAL PROPERTY and CLAUSE no clause names a signal by its name, bare or with SIG, in any case, inflected, joined to any character that is not an ASCII letter, or in upper case anywhere in a word (a trap's action the guard reads is refused where it names a tracked file, for the signal word each of ${TRAP_ROWS.join(', ')} in tools/romp-track-bash-guard.test.mjs carries, and for each spelling a present shell's trap takes among the names and spellings the signal census in this file derives; a word used in another sense joins the phrases set aside above with its context)`);
  assert.ok(/(?<![\w.-])(?:6[0-4]|[1-5]?[0-9])(?![\w.])/.test(rest), 'hooks/README.md: the witness of the number boundary, a number a trap takes (0 to 64) standing in the row in another sense, so a pin on numbers would red the committed row; with none left, a signal given by its number can join the pin');
  const lowerGlued = (rest.match(/[A-Za-z0-9_]+/g) || []).filter((t) => !signalNamesIn(` ${t} `).length && SIGNAL_NAMES.some((n) => t.toLowerCase().includes(n.toLowerCase())));
  assert.ok(lowerGlued.length > 0, 'hooks/README.md: the witness of the glued boundary, a word in lower or mixed case holding a name glued to letters beyond an inflection (pipeline, into, error) standing in the row, so a pin reading a name in any case inside a word would red the committed row; with none left, that reading can join the pin');
  const guardTestSrc = read('tools', 'romp-track-bash-guard.test.mjs');
  for (const id of ['EV-eval', 'EV-eval-var', ...TRAP_ROWS]) assert.ok(guardTestSrc.includes(`['${id}', 'nad', `), `the executed row ${id} the clause's message points at stands in the guard's test`);
  for (const id of ['RT-read-var-head', 'RT-xargs']) assert.ok(guardTestSrc.includes(`['${id}', '`), `the residual row ${id} the clause's message points at stands in THE RESIDUAL TABLE`);
  assert.ok(ledger.includes('a target whose only expansions are `$$` or `${$}`, the shell\'s process id, at an absolute path outside every project in play is allowed, and no other expansion is numeric'), 'the ledger entry: the exception (round 5: no other expansion is numeric; a name the guard resolves is allowed by the path it names, which the old "nothing else is" denied)');
  assert.ok(ledger.includes('the process id is the one OPAQUE expansion allowed inside a tracked project'), 'the ledger entry says what the exception is the one of');
  assert.ok(ledger.includes('so a `log.$RANDOM` inside a tracked project is refused in every shell, a deliberate false refusal recoverable in one step'), 'the ledger entry: the refused names');
  assert.ok(hook.includes("const NUMERIC_EXPANSIONS = ['$$', '${$}'];"), 'the set every clause describes');
});

// THE SIGNAL CENSUS (round 7 of fork PR #780 review, thirty-eighth commit; the thirty-ninth reads what a trap takes): SIGNAL_NAMES is typed
// above, so this test holds it to the shells present, each started as the guard's test starts it (bash --norc --noprofile, zsh -f, dash, the
// environment PATH alone), so no startup file of the account's runs. Two reads per shell. The names it prints (bash's `trap -l`, zsh's
// `$signals`, dash's `kill -l`), each read in the six spellings SIGNAL_SPELLINGS makes (bare and with SIG, each as printed, in lower case and
// in title case, since bash takes a name in any case: `int`, `Int`, `SigInt`). And the spellings its trap TAKES, `trap : NAME` in a subshell
// per spelling, over the candidates: every name a shell printed, the SIG names the system's <signal.h> defines as the C preprocessor reads it
// (`cpp -dM`, which holds CLD, IOT and POLL beside the signals' own names), node's os.constants.signals and SIGNAL_NAMES, each in the six
// spellings; a mixed case beyond those six is not measured or judged one by one here. The
// pin must read every name printed and every spelling taken: a trap takes names no list prints
// (zsh's CLD), which the thirty-eighth commit's census, reading the printed lists alone, could not see. A shell or a preprocessor that does
// not start, exits other than 0 or gives no name is reported NOT RUN with the reason on stderr and read no further (CI's runner has no zsh; a
// program present but refusing is the same case as one absent), and the test reds when no shell printed a list or no shell's trap was
// measured, so it never passes on nothing read. A number (dash prints one for a signal it has no name for) is not a name: a signal given by
// its number is the boundary the README pin states. Then each spelling a present shell's trap takes, of those measured, sets a trap whose action the hook
// refuses where it names a tracked file: evaluate, the function the hook runs on its payload, judges `trap 'cp ../base/report.md report.md'
// SPELLING` from the docs/ folder of a scratch project tracking docs/report.md and must refuse it by the tracked file's name through `trap`,
// so the README pin's message (a trap's action is refused for each spelling a present shell's trap takes among the names and spellings this
// census derives) holds for each spelling measured as taken, where the executed
// rows in tools/romp-track-bash-guard.test.mjs carry one spelling each (a hook that skipped a trap's action on CLD passed the thirty-eighth
// commit's rows while zsh wrote: the verifier).
const SIGNAL_LISTS = { bash: ['--norc', '--noprofile', '-c', 'trap -l'], zsh: ['-f', '-c', 'print -r -- $signals'], dash: ['-c', 'kill -l'] };
const SIGNAL_SHELL_C = { bash: ['--norc', '--noprofile', '-c'], zsh: ['-f', '-c'], dash: ['-c'] };
const TRAP_TAKES = 'for n in "$@"; do (trap : "$n") 2>/dev/null && printf \'%s\\n\' "$n"; done; true';   // prints each spelling this shell's trap takes
const notRunWhy = (r, none) => (r.error ? `did not start (${r.error.code})` : r.status !== 0 ? `exited ${r.status ?? r.signal}` : none);

test('round 7, thirty-eighth and thirty-ninth commits: the signal names the README pin reads include every name each present shell prints for its trap and each spelling its trap takes of the candidate names the census derives, bare and with SIG, as printed, in lower case and in title case, and the hook refuses a trap set with each spelling taken whose action names a tracked file', async () => {
  const listed = [];
  const candidates = new Set([...SIGNAL_NAMES, ...Object.keys(os.constants.signals).map((k) => k.replace(/^SIG/, ''))]);
  for (const [sh, argv] of Object.entries(SIGNAL_LISTS)) {
    const r = spawnSync(sh, argv, { encoding: 'utf8', env: { PATH: process.env.PATH }, input: '', timeout: 20000 });
    const names = r.status === 0 ? String(r.stdout).split(/\s+/).filter((w) => w && !/^\d+\)?$/.test(w)) : [];
    if (!names.length) {
      console.error(`NOT RUN: real ${sh} ${notRunWhy(r, 'printed no signal name')}, so its signal list was not read: the README pin's signal census`);
      continue;
    }
    listed.push(sh);
    for (const name of names) {
      const bare = name.replace(/^SIG/, '');
      candidates.add(bare);
      for (const s of SIGNAL_SPELLINGS(bare)) assert.ok(signalNamesIn(` ${s} `).includes(s), `${sh} prints ${name} for its trap, and the README pin reads ${s} (a name SIGNAL_NAMES lacks)`);
    }
  }
  assert.ok(listed.length > 0, 'no shell printed its signal list, so the census read nothing');
  const cpp = spawnSync('cpp', ['-dM', '-'], { encoding: 'utf8', env: { PATH: process.env.PATH }, input: '#include <signal.h>\n', timeout: 20000 });
  const defined = cpp.status === 0 ? [...String(cpp.stdout).matchAll(/^#define SIG([A-Z0-9]+)\s/gm)].map((m) => m[1]) : [];
  if (!defined.length) console.error(`NOT RUN: the C preprocessor cpp ${notRunWhy(cpp, 'defined no SIG name')}, so the names <signal.h> defines were not among the candidates: the README pin's signal census`);
  for (const n of defined) candidates.add(n);
  const spellings = [...candidates].flatMap(SIGNAL_SPELLINGS);
  const taken = new Set();
  const measured = [];
  for (const [sh, argv] of Object.entries(SIGNAL_SHELL_C)) {
    const r = spawnSync(sh, [...argv, TRAP_TAKES, sh, ...spellings], { encoding: 'utf8', env: { PATH: process.env.PATH }, input: '', timeout: 60000 });
    const took = r.status === 0 ? String(r.stdout).split('\n').filter(Boolean) : [];
    if (!took.length) {
      console.error(`NOT RUN: real ${sh} ${notRunWhy(r, 'took no spelling')}, so what its trap takes was not measured: the README pin's signal census`);
      continue;
    }
    measured.push(sh);
    for (const s of took) {
      assert.ok(signalNamesIn(` ${s} `).includes(s), `${sh}'s trap takes ${s}, and the README pin does not read it (a name SIGNAL_NAMES lacks)`);
      taken.add(s);
    }
  }
  assert.ok(measured.length > 0, "no shell's trap was measured, so the census read nothing a trap takes");
  const { evaluate } = await import('../hooks/romp-track-bash-guard.mjs');
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'plan-trap-')));
  const savedRoot = process.env.TRACKCHANGES_ROOT;
  delete process.env.TRACKCHANGES_ROOT;
  try {
    for (const d of ['.trackchanges', 'docs', 'base']) fs.mkdirSync(path.join(root, d));
    fs.writeFileSync(path.join(root, '.trackchanges', 'config.json'), JSON.stringify({ v: 2, tracked: ['docs/report.md'] }));
    fs.writeFileSync(path.join(root, 'docs', 'report.md'), 'NA-ORIG\n');
    fs.writeFileSync(path.join(root, 'base', 'report.md'), 'NA-BASE-POISON\n');
    const tracked = path.join(root, 'docs', 'report.md');
    for (const s of taken) {
      const cmd = `trap 'cp ../base/report.md report.md' ${s}`;
      const why = evaluate(JSON.stringify({ tool_name: 'Bash', tool_input: { command: cmd }, cwd: path.join(root, 'docs') }));
      assert.ok(typeof why === 'string' && why.includes(tracked) && why.includes('through `trap`'), `a trap set on ${s}, a spelling a present shell's trap takes, is refused by the tracked file's name through \`trap\`: ${cmd}: ${why}`);
    }
  } finally {
    if (savedRoot === undefined) delete process.env.TRACKCHANGES_ROOT; else process.env.TRACKCHANGES_ROOT = savedRoot;
    fs.rmSync(root, { recursive: true, force: true });
  }
});

// Round 4's contract paragraph (2026-09-19): the guard is best-effort against known write forms, its default on an
// unrecognised form is allow, and the unmodelled writers that pass are listed. The same paragraph and the SAME
// writer list sit on all four surfaces a user meets, so a user who knows the boundary can work with it; this test
// reads each file whitespace-normalised and fails if any lacks it or if the lists differ.
test('decision 47 records round 4 and each class is tied to the hook function that implements it', () => {
  assert.ok(d47.includes('Round 4 (2026-09-19, a walk-around lens) closed eight more in-model roads'));
  assert.ok(d47.includes('read a per-writer option table (`COPY_OPT`)') && hook.includes('const COPY_OPT = {') && hook.includes('function parseCopyOptions(args, verb)'));
  // since the third pass `commandOf` returns the chdirs in order (a nested `env -C` composes) and the wrapper tables live in WRAPPER_OPT
  assert.ok(d47.includes('`commandOf` returns its `chdir`') && hook.includes('return { name, args: words.slice(k + 1), chdirs, writes, wrapped, wrappers, wrapperIdx };'));
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
  const CONTRACT_PARAGRAPH = 'this guard is best-effort against known write forms: it refuses the shell writes it models and, by design, allows anything it does not recognise, so it never blocks ordinary work it cannot read; it is a backstop, not a complete boundary. the allow-by-default for an unmodelled writer is deliberately not flipped, since flipping it would refuse almost all normal work. what it does refuse, while a tracked project is in play, is a write it reads but cannot place: a target it cannot read, a path it cannot check (a stat error other than not-found), an option on a modelled writer or wrapper it does not parse in full, an env -s string, a shell option it does not know to be inert for paths, a link whose source it cannot read, a `~` or `$home` write beside a mention of home or beside a variable name the shell fills in, a template or format string as an interpreter\'s write path, and, from any working directory, a write through an alias the command makes (a hard link, `cp -l`, `cp -s`, `link`, a link whose source it cannot read) whose source lies in a tracked project or is one it cannot read. deleting or moving a tracked file away (`rm`, `unlink`, `mv` to another name, `find -delete`) is not a write it refuses: the contract is the write that lands on a tracked file, and whether the tracked set shrinking is such a write is a scope question raised with the round\'s review and not decided here. a value it can read is resolved first and the real path judged. a name is readable only when every write to it in the command is a plain top-level `name=plain-string` the shell performs as spelled: no tilde opening the value, no declaration flag at all, no `declare`, `typeset` or `local` (dash has none of the three; `export` and `readonly` with no option word are the two declarations every shell performs), no nameref reaching it, no name the shell fills in, no subshell, pipeline, piped group or body scope, no `{ }` group opened after `&&`, `||` or `|`, no wrapper argument, no call of a function the command defines in any spelling, no subscript; any other construct that can write the name, listed here or not, leaves it unreadable, the doctrine a `read` and a loop variable already had. home, pwd, oldpwd, `~+` and `~-` are read the same way: home after a plain top-level `home=<path>` assignment of its own, and none of the three once the command names or may fill in the name in any other form. ';
  // since round 6's second commit (2026-09-21) the closing list is THE RESIDUAL PROPERTY, whose classes are the ones RESIDUAL_TABLE in
  // tools/romp-track-bash-guard.test.mjs measures (the developer-surface pin below holds the same text on decision 47 and the ledger too); since round 7
  // of fork PR #780 review, thirty-fifth commit (the reviewer's extra7-3), the vendored SKILL.md carries the contract paragraph and, in the
  // property's place, a statement of its classes in the reader's words, held to RESIDUAL_CLASSES by name in the guard's test
  const LIST = 'the residual property. the guard refuses a write only when it resolves the command to a writer it models (the writer cases of extract\'s switch, a write redirection, an interpreter\'s write call it scans) reached through a road it reads (the wrapper set, the shells\' script roads, the readings of the resolver, the alias and hash roads), with a target it can place or cannot read, or when a command whose name, script or piped script it does not read names a tracked file as a literal operand. every write that still reaches a tracked file is one the guard does not resolve to such a writer through such a road, whether or not its text stands in the command, and falls in one of these classes, each measured by execution in tools/romp-track-bash-guard.test.mjs (the residual table, whose rows are the population this statement is over): a writer outside the model, a program, or a write form of a program the hook models, that writes the file by its own nature and is not among the write forms the hook reads (rsync, patch, tar -x, ed, ex, vim, make, shuf -o, gawk -i inplace, awk\'s print redirect, uniq, scp, openssl -out, shred, curl -o, wget -o, find -exec, a git alias or a subcommand that writes the tree, bash\'s history -w, zsh\'s sysopen and mapfile modules, sed\'s e command and a w command in a sed script the resolver cannot read, busybox\'s applets); a reader outside the roads, a program that runs a command or a script the hook does not follow into it (xargs, an interpreter\'s system, exec or subprocess call, a wrapper outside the set, a shell outside shells, a file the command writes and then runs or sources, a function\'s call of itself, which the replay does not follow again); a command name the resolver never reads, a command whose name is an expansion of a kind the resolver does not read ("${a[@]}", a loop variable, a name read or filled by getopts, printf -v or a nameref, a name the shell itself sets (${shell}, $0, $bash, $zsh_argzero, $_ after a command), a substitution outside the output model such as $(which cp), a ${...} operator form the resolver does not read, a positional parameter of a script handed to a fresh shell with arguments of its own; "$@", $1 and $* stand for the operands of a called function or of a `set` this shell ran since round 6\'s sixth commit), handed no literal operand that names a tracked file (the operand a directory, or a word the resolver does not read): since round 7\'s twenty-fifth commit a command so named, or a script or piped script the resolver does not read, whose literal operand names a tracked file is refused by name (the reviewer\'s q1: the target known, the writer not); a script held in a variable, a value the command gives a name through a construct the resolver does not read (`read`, `printf -v`, a positional parameter of a fresh shell\'s script), run as a command or handed to a shell (`$c` after `read c`, `eval "$1"` inside a `bash -c` given arguments, `bash -c "$c"` after `printf -v c`; a value an assignment word gives, whitespace included, is read through the head candidates since round 6\'s fourth commit, and a `${name:=word}` gives word since the sixth); a producer outside the output model, a pipe into a shell, or a write redirection into a process substitution running one, from anything but a literal echo or printf, alone or in a subshell or group of such commands, or a plain cat passing such a text through, or a command substitution over such a producer handed to a shell, an eval or a here-string (a call of a function the command defines, a tee or a pipe through another command, a cat of a file, an eval or a shell -c inside the substitution); zsh\'s glob grouping, a `(..)` inside a word handed to zsh, read as a subshell by the lexer\'s zsh grammar while zsh globs it (a lexer gap, stated since the first commit of this round); zsh\'s hook functions, a function the command defines under a name zsh calls on its own (chpwd, precmd, preexec, periodic, zshexit, and the names in chpwd_functions and its kin), whose body runs when the shell moves, prompts or exits, from the directory the shell is in then, while the guard judges the definition where it stands; an opaque expansion from a cwd outside every project, a leading opaque expansion, or one after a literal head outside every project, from a cwd in no project (b2 as ruled, with its boundary). a shape outside these classes that reaches a tracked file is a rule to state, not a residual.';
  const CONTRACT = 'best-effort against known write forms';
  const surfaces = {
    'hook header': read('hooks', 'romp-track-bash-guard.mjs'),
    'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md'),
    'hooks/README.md': read('hooks', 'README.md'),
    'docs/install.md': read('docs', 'install.md'),
  };
  const READER = 'the guard refuses a write only when it recognises the command as a writer it knows';   // the skill's statement opens so
  for (const [name, text] of Object.entries(surfaces)) {
    const n = norm(text);
    const skill = name === 'the vendored SKILL.md';
    assert.ok(n.includes(CONTRACT), `${name} states the check is best-effort against known forms`);
    assert.ok(skill ? !n.includes(LIST) : n.includes(LIST), skill ? `${name} no longer carries the developer paragraph of the residual property (review provenance and the hook's internal names included)` : `${name} carries the identical unmodelled-writer list (a differing list fails here)`);
    assert.ok(n.includes('allows anything it does not recognise') || n.includes('allow') , `${name} says the default is allow`);
    // the third pass (2026-09-19): the WHOLE paragraph is identical on the four surfaces, the two sentences the hook
    // header alone carried (the allow-by-default is not flipped; what is refused) included
    assert.ok(n.includes(CONTRACT_PARAGRAPH + (skill ? READER : LIST)), `${name} carries the identical contract paragraph, the allow-by-default sentence and the refused-class sentence included, then ${skill ? 'the reader\'s statement of the classes' : 'the residual property'}`);
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
  assert.ok(hook.includes('function sortTargets(args)') && hook.includes('if (j < t.length - 1) targets.push(sliceWord(a, j + 1));'), 'sort reads a glued -o (and the -uo cluster: the reviewer\'s extra4-1, round 7\'s twenty-sixth commit)');
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
  assert.ok(d47.includes('`aliasSourceInPlay`') && hook.includes('function aliasSourceInPlay(why, memo)') && hook.includes('return { targets, opaque: opaque || sawOpaqueCommand, unresolved, q1Targets, q1Unresolved, links, dir, unknownDir, unknownWhy, oldDir, moved: movedAny || dir !== ctx.dir || unknownDir !== !!ctx.unknownDir, positionals, positionalsWhy, rebound };'), 'M3 and B1: the links returned, the alias source asked');
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
  assert.ok(d47.includes('FULLY PARSED OR REFUSED') && hook.includes('const WRAPPER_OPT = {') && hook.includes('({ unknown: { option, wrapper: name, value, rest: words.slice(k + 1), at: k } })'));
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
  assert.ok(hook.includes("for (const t of scriptTexts(cmd.script, `\\`${cmd.scriptFlag || 'flock -c'}\\` script`)) recurse(t, shell, true,") && hook.includes('const moveUnknown = (why) => { oldDir = null; setUnknown(why); };'), 'a flock -c string is read in a fresh scope and poisons nothing; a cd the guard cannot follow clears OLDPWD');
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
  assert.ok(hook.includes('if (head != null && Object.hasOwn(CLOSERS, head)) closeCompound(CLOSERS[head]);') && hook.includes('else if (head != null && Object.hasOwn(BODY_CLOSER, head)) {') && hook.includes('compoundBody(seg, peelIndex(seg.words) + 1, pushCompound(head0), true);') && !hook.includes('if (head in CLOSERS)'), 'the lookups are own-property lookups on the peeled head, at both head reads');
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
  assert.ok(hook.includes("brace(words[0]) === '}' && plainWord(words[1]) && words[1].text === 'always' && brace(words[2]) === '{') {"), "zsh's always continues the group (dropped at the lexer since the third addendum, one group)");
  assert.ok(hook.includes("if (f.depth === 0 && from === 0 && !(seg.words.length && plainWord(seg.words[0]) && seg.words[0].text === '{')) { f.oneSegment = true; return 0; }"), 'a function body without braces is one segment, not the enclosing scope (a quoted `{` heading it is such a body\'s command, round 5\'s fourth addendum)');
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
  // round 5's second addendum (2026-09-20): the freeze sentence's dated narrowing, the census's spacing, and the vendored README row
  // the right way round; its brace fix was superseded by the third addendum's rule, pinned below
  assert.ok(d47.includes("Round 5's second addendum (2026-09-20;") && d47.includes('a `}` that shares a segment with the command before it'), 'decision 47 records the second addendum');
  // round 5's third addendum (2026-09-20): the closing-brace rule, stated once at the lexer and on decision 47 in the same words,
  // every frame kind reading through the cut; the second addendum's per-frame readings and the seventh pass's pendingClose gone
  const RULE = "an unquoted `}` that follows other words in its segment ends its construct only after those words are read as the construct's own command, and every word after it begins a new command";
  assert.ok(d47.includes("Round 5's third addendum (2026-09-20;") && d47.includes(RULE), 'decision 47 records the third addendum and states the rule');
  assert.ok(hookFlat.includes(RULE) && hook.includes('function splitAtClosers(segments) {') && hook.includes('return { segments: splitAtClosers(segments), opaque, patternParen:'), 'the lexer states the rule and cuts every segment through it');
  for (const fn of ['splitAtClosers', 'closedConstruct', 'addRedirects', 'arithAt', 'closerTail']) assert.ok(d47.includes(`\`${fn}\``) && hook.includes(fn), `decision 47 names ${fn} and the hook has it`);
  assert.ok(hook.includes('if (seg.closerTail && seg.closerTail.length) variants = [...variants, ...variants.map((v) => [...v, ...seg.closerTail])];'), 'a writer is judged as cut and with the cut braces back as operands');
  assert.ok(hook.includes("if (f.kind === 'if' && plainWord(next) && (next.text === 'else' || next.text === 'elif')) { f.opened = false;") && hook.includes("if (headSegment && i === start && !list && !f.afterParen && !arithBefore(i)) { f.condition = true; f.braces = 1;"), 'compoundBody keeps the frame open across else and elif and reads a condition group');
  assert.ok(hook.includes("if (head === 'repeat' && seg.words.length > at + 2) { seg.words = seg.words.slice(at + 2); preWords = preWords.slice(at + 2); compoundBody(seg, 0, f, true, preWords); }"), "repeat N is dropped before either body form");
  assert.ok(hook.includes("if (plainWord(w) && Object.hasOwn(BODY_CLOSER, w.text)) break;   // a compound inside the body: its own frame counts its braces"), 'the function body\'s count stops at a compound head inside it');
  assert.ok(!/let pendingClose|pendingClose = \{|closeGroups\(pendingClose/.test(hook) && !hook.includes('f.oneSegment = true; seg.words.splice(i, 1); return i;') && !hook.includes('variants = [cut, ...variants];'), 'the per-frame readings the rule replaces are gone (pendingClose survives in the history comments alone)');
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

// Round 5's fifth addendum (2026-09-20): the two-grammar rule, stated once at the lexer's closeTest and on decision 47 in the same words,
// the shell facts in their table, the four prose surfaces corrected, the census naming the two new tables, and the fixture stating its population.
test("decision 47, the hook and the prose surfaces record round 5's fifth addendum: the two-grammar rule in the same words at the lexer and on the decision, the shell facts in TEST_ARITH_SHELLS and CONSTRUCT_HEADS, the functions that carry it, the construct matrix's fixture with its population, and the README, install and skill surfaces saying what dash makes of `[[` and `((`; and the addendum's fix-up: the test's boundaries in the same words on both, the two lexer reads in their order, the fixture's placement dimension, and the three surfaces naming the process substitution and the glued operator", () => {
  const RULE = 'a construct the hook reads under bash and zsh grammar (`[[ ... ]]`, `(( ... ))`, a `$(( ... ))`) contributes, in addition, its dash reading to the write set: where dash reads the construct as a plain command (`[[`), the words after the head are its operands and every redirection operator among them a redirection dash performs before the command is looked up, and the words after a `&&` or `||` among them a further command; where dash reads it as a subshell (`((`, two nested `(`), its body is a command list dash runs; and each target so found is judged exactly as any redirection or writer the hook already judges';
  const SUB = 'a substitution inside an arithmetic body (`$(...)`, a backtick) runs in every shell and is read as a command, and a `$((` whose first `(` closes before the last is a command substitution in bash and zsh and is read as one';
  // the fix-up (2026-09-20): the test's boundaries, stated beside the rule at the lexer and on decision 47 in the same words
  const BOUNDS = "the test's grammar covers the words between `[[` and the unquoted `]]` that closes it and only the test's own operators among them; an expansion among the operands (a `$(...)`, a backtick, a `<(...)` or `>(...)`) is performed by the shell before the test reads a word and is read as the command it runs, where it is lexed; and an operator glued to the closing `]]` is outside the test, the redirection or list operator it is anywhere else, read after the test has closed";
  const hookFlat = hook.replace(/\n\s*\/\/ ?/g, ' ').replace(/\s+/g, ' ');   // the rule's home comment sits inside lex, indented, so the comment lines are joined whatever their indentation
  const d47Flat = d47.replace(/\s+/g, ' ');
  assert.ok(d47Flat.includes("Round 5's fifth addendum (2026-09-20;"), 'decision 47 records the fifth addendum');
  assert.ok(hookFlat.includes(RULE) && d47Flat.includes(RULE), 'the rule is stated at the lexer and on decision 47 in the same words');
  assert.ok(hookFlat.includes(SUB) && d47Flat.includes(SUB), 'the substitution and $(( sentence, on both');
  assert.ok(hookFlat.includes(BOUNDS) && d47Flat.includes(BOUNDS), "the test's boundaries (the fix-up), stated at the lexer and on decision 47 in the same words");
  assert.ok(d47Flat.includes("THE FIX-UP (2026-09-20; the addendum's verifier, on its head)"), 'decision 47 records the fix-up');
  const gluedRead = "if (inTest && inWord && raw === ']]') endWord();";
  const procsubRead = "if (testGrammar && (c === '>' || c === '<') && src[i + 1] === '(') {";
  const testRead = "if (inTest && (c === '<' || c === '>')) { bareWord(c); i++; continue; }";
  assert.ok(hook.includes(gluedRead) && hook.includes(procsubRead) && hook.includes(testRead), 'the two boundary reads and the test\'s own operator read are in the lexer');
  assert.ok(hook.indexOf(gluedRead) < hook.indexOf(procsubRead) && hook.indexOf(procsubRead) < hook.indexOf(testRead), 'the ]] under way ends the test first, the process substitution is read next, and the test\'s own < and > last: the order is the fix');
  for (const fn of ['closeTest', 'skipArithmetic', 'expansionsOf', 'parenCloseAt', 'withDashPieces', 'viaSubs', 'TEST_ARITH_SHELLS', 'CONSTRUCT_HEADS']) {
    assert.ok(d47.includes(`\`${fn}\``), `decision 47 names ${fn}`);
    assert.ok(hook.includes(fn), `the hook has ${fn}`);
  }
  assert.ok(hook.includes("const TEST_ARITH_SHELLS = new Set(['bash', 'zsh', 'ksh']);") && hook.includes("const testGrammar = shell == null || shell === 'sh' || TEST_ARITH_SHELLS.has(shell);") && hook.includes("const dashGrammar = shell == null || shell === 'sh' || !TEST_ARITH_SHELLS.has(shell);"), 'the shell table and the two grammars read from it');
  assert.ok(hook.includes("export const CONSTRUCT_HEADS = {") && hook.includes("'[[': { closer: ']]',") && hook.includes("'((': { closer: '))',") && hook.includes("'$((': { closer: '))', expansion: true,"), 'the construct table carries the three constructs');
  assert.ok(hook.includes("if (testGrammar && raw === '[[' && seg.words.every((w) => plainWord(w) && RESERVED.has(w.text))) { inTest = true; testStart = i; }") && hook.includes("else if (raw === ']]' && inTest) closeTest(i - 2, true);"), 'the test keyword opens and closes the dash reading');
  assert.ok(hook.includes("if (dashGrammar && seg.words.every((w) => plainWord(w) && RESERVED.has(w.text))) seg.viaSubs.push({ text: body, via: CONSTRUCT_HEADS['(('].via });"), 'the (( )) body is a command list in the dash reading, in command position alone');
  assert.ok(hook.includes("if (inner.startsWith('(') && parenCloseAt(inner) === inner.length - 1) { opaqueExpansion(); const body = inner.slice(1, -1); seg.arith.push(body); expansionsOf(body, CONSTRUCT_HEADS['$(('].expandVia); }"), 'a balanced $(( is arithmetic in every shell and its substitutions are read');
  assert.ok(hook.includes("if (dash.opaque || dash.segments.some((s) => s.paren)) return;"), 'a parenthesis inside the test: a syntax error in dash, no dash reading');
  assert.ok(hook.includes("add(r.target, r.how || `${r.op} redirection`)"), 'a dash-reading redirect carries its how');
  assert.ok(hook.includes("const compare = u.how.includes(CONSTRUCT_HEADS['[['].via) ?"), 'the not-literal refusal carries the comparison remedy for a [[ target');
  const censusSrc = fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-census.mjs'), 'utf8');
  assert.ok(censusSrc.includes("TEST_ARITH_SHELLS: { side: 'REFUSE'") && censusSrc.includes("CONSTRUCT_HEADS: { side: 'WRITE'"), 'the census names the two tables with their sides');
  const fixture = JSON.parse(fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-construct-matrix.json'), 'utf8'));
  assert.ok(fixture.rows > 0 && typeof fixture.population === 'string' && fixture.population.includes('CONSTRUCT_HEADS') && fixture.note.includes('NOT exhaustive'), 'the construct fixture states its population and that it is not exhaustive');
  assert.deepEqual(fixture.placements, ['operand', 'sub', 'procsub', 'closer-glued', 'closer-spaced'], 'the construct fixture names the placements of the write it was generated over (the fix-up)');
  assert.ok(fixture.population.includes('placement of the write against the construct'), 'and its population statement carries the dimension');
  const brace = JSON.parse(fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-brace-matrix.json'), 'utf8'));
  assert.ok(brace.note.includes('POPULATION (stated since round 5\'s fifth addendum'), 'the brace fixture states its population');
  const prose = { 'hooks/README.md': hooksReadme, 'docs/install.md': read('docs', 'install.md'), 'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md') };
  for (const [name, text] of Object.entries(prose)) {
    const flat = text.replace(/\s+/g, ' ');
    assert.ok(flat.includes("`[[ a > f ]]` and `(( a > f ))` compare in bash and zsh and are read in dash's grammar too since round 5's fifth addendum"), `${name} states the two-grammar reading`);
    assert.ok(flat.includes("judged in bash's and zsh's readings (dash reads `>! f` as bash does") && !flat.includes("judged in both shells' readings"), `${name} names dash's reading of the clobber forms`);
    assert.ok(flat.includes("a process substitution among the test's operands runs in bash (`[[ -f <(echo x > f) ]]` writes f) and an operator glued to the closing `]]` is a redirection or list operator (`[[ a ]]>f` writes f in every shell), each judged as anywhere since the addendum's fix-up (2026-09-20)"), `${name} names the two boundary reads of the fix-up`);
  }
  assert.ok(!hook.includes("records BOTH shells' readings"), 'the header names the three shells for the clobber forms');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 5's fifth addendum's second fix-up (2026-09-20): the nested-expansion rule and the piped-script rule, each stated once at its home
// in the hook and on decision 47 in the same words, the functions that carry them, the two fixtures with their populations, the residual
// (a producer the guard cannot see; a shell outside SHELLS, busybox among them) named on the header, the decision and hooks/README.md,
// and the three prose surfaces carrying the same sentence.
test("decision 47, the hook and the prose surfaces record the fifth addendum's second fix-up: the nested-expansion rule at the lexer and the piped-script rule at extract, each on decision 47 in the same words, the functions, the two matrix fixtures with their populations and residual rows, the residual named with busybox on the header, the decision and the README, and the three surfaces' sentence", () => {
  const RULE_NESTED = 'an expansion nested inside a parameter-expansion word is read as the command it runs, recursively, in every position (an operand, inside `[[ ]]`, inside `(( ))`, a redirection target, a quoted word), exactly as an expansion among plain operands is read; the `${` read descends';
  const RULE_PIPED = 'when a pipeline\'s last command is a shell of SHELLS reading its script from stdin (no `-c`, no script operand: `bash`, `bash -s`, `sh -`, dash) and the command piped into it is an echo or a printf, the words echo or printf would print are the script, read as the here-string form already is, under the grammar the shell named uses (dash\'s for `sh` and `dash`, TEST_ARITH_SHELLS)';
  const hookFlat = hook.replace(/\n\s*\/\/ ?/g, ' ').replace(/\s+/g, ' ');
  const d47Flat = d47.replace(/\s+/g, ' ');
  assert.ok(d47Flat.includes("THE SECOND FIX-UP (2026-09-20; the fix-up's verifiers, on its head)"), 'decision 47 records the second fix-up');
  assert.ok(hookFlat.includes(RULE_NESTED) && d47Flat.includes(RULE_NESTED), 'the nested-expansion rule is stated at the lexer and on decision 47 in the same words');
  assert.ok(hookFlat.includes(RULE_PIPED) && d47Flat.includes(RULE_PIPED), 'the piped-script rule is stated at extract and on decision 47 in the same words');
  for (const fn of ['nestedExpansions', 'skipNested', 'BRACE_WORD_VIA', 'stdinBodies', 'pipedScripts', 'echoOutput', 'printfOutput', 'shellEscapes']) {
    assert.ok(d47.includes(`\`${fn}\``), `decision 47 names ${fn}`);
    assert.ok(hook.includes(fn), `the hook has ${fn}`);
  }
  // the descent's home and the reads that make it: the `${` read descends in both quotings, comments are off inside, a single quote is a
  // character in a double-quoted word, and the piped script joins the stdin bodies
  assert.ok(hook.includes("const nested = nestedExpansions(inner, dq, !!op);") && hook.includes("const placed = defaultReading(inner, op[0].length, nested, { name: op[1], op: op[2] });"), 'the ${ read descends (once, and reads the default word from the same descent since the third fix-up, with its name and operator since round 6\'s fifth commit)');
  assert.ok(hook.includes("if (e.kind === 'brace') { braceParameter(true); continue; }") && hook.includes("if (e.kind === 'brace') { braceParameter(dqInner || hdInner); continue; }"), 'in double quotes and unquoted (and in a here-document body, the third fix-up)');
  assert.ok(hook.includes("const nested = lex(inner, shell, { comments: false, quotes: dq ? 'double' : 'plain', depth: nestDepth + 1, braceWord: true, oneWord: true, noSplit: true, ifsNamed });"), 'the inner text is lexed with no comment, in its quoting, one level deeper (as one brace word, unsplit, with the IFS fact, since the third fix-up)');
  assert.ok(hook.includes("if (c === '#' && !inWord && comments) {") && hook.includes("if (c === \"'\" && !dqInner) {"), 'a # opens no comment inside the word; a single quote is a character in a double-quoted one');
  assert.ok(hook.includes("for (const t of s.subs) seg.viaSubs.push({ text: t, via: BRACE_WORD_VIA });"), 'the nested substitutions join the segment with the word named');
  assert.ok(hook.includes("out.push(...pipedScripts(p));") && hook.includes("if (segments[p].printed) return scriptTexts(segments[p].printed, 'piped script', 'file');") && hook.includes("return cmd.name === 'echo' ? echoOutput(cmd.args) : printfOutput(cmd.args);"), 'the piped script joins the stdin bodies, from an echo or a printf alone (round 6: the producer\'s printed text is placed on the segment by the lexer and read through scriptTexts)');
  assert.ok(hook.includes("if (segments[p].printed) return scriptTexts(") && hook.includes("if (idx > 0 && segments[idx - 1].op === '|') return idx - 1;"), 'the producer is the segment directly before the pipe (or, since the third fix-up, before the compound holding the consumer: producerAt); since round 6\'s second commit a subshell or group producer carries its list\'s printed text on its closer (THE OUTPUT MODEL), and a producer with no printed text is outside the model');
  // the residual, named with busybox on the header, the decision and the README
  for (const [name, text] of [['the hook header', hook], ['decision 47', d47], ['hooks/README.md', hooksReadme]]) {
    const flat = text.replace(/\n\s*\/\/ ?/g, ' ').replace(/\s+/g, ' ');
    assert.ok(/busybox `?sh`? or `?ash`?/.test(flat), `${name} names busybox sh and ash as shells outside the set the guard reads`);
    assert.ok(flat.includes('cat f | bash'), `${name} names a producer the guard cannot see`);
  }
  // the fixtures state their populations and the piped fixture its residual rows
  const pw = JSON.parse(fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-param-word-matrix.json'), 'utf8'));
  assert.ok(pw.rows > 0 && pw.population.includes('operator form of the ${...} word') && pw.note.includes('NOT exhaustive') && Array.isArray(pw.forms) && Array.isArray(pw.positions), 'the param-word fixture states its population and that it is not exhaustive');
  const ps = JSON.parse(fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-piped-script-matrix.json'), 'utf8'));
  assert.ok(ps.rows > 0 && ps.residualRows > 0 && ps.population.includes("every shell of the hook's SHELLS") && ps.note.includes('The residual rows are expected ALLOWED') && ps.note.includes('busybox'), 'the piped-script fixture states its population, its residual rows and the consumer outside SHELLS');
  assert.ok(ps.rows > ps.residualRows, 'the literal rows outnumber the residual ones');
  // the three prose surfaces carry the second fix-up's sentence
  const SENT = "since its second fix-up the same day an expansion nested in a `${...}` word (`${x:-$(cp a b)}`, a backtick, a `<(...)`) is read as the command it runs in every position, and a literal echo or printf piped into a shell reading stdin is that shell's script (a producer the guard cannot see, `cat f | bash`, stays unread, as does a script handed to a shell outside the set it reads, busybox sh or ash among them)";
  const prose = { 'hooks/README.md': hooksReadme, 'docs/install.md': read('docs', 'install.md'), 'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md') };
  for (const [name, text] of Object.entries(prose)) assert.ok(text.replace(/\s+/g, ' ').includes(SENT), `${name} carries the second fix-up's sentence`);
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// The seventh pass's attacker (2026-09-19): decision 47 and the hook header record the two misses and the readonly sibling, each
// tied to the hook function that closes it, and the wrapper list on the three prose surfaces names zsh's modifiers.
test("decision 47 and the hook header record the seventh pass's attacker: nesting-aware group frames, zsh's precommand modifiers in the wrapper set and on every prose surface, the readonly value kept, and the shadowed poison gone", () => {
  assert.ok(d47.includes("The seventh pass's attacker (2026-09-19;") && hook.includes("THE SEVENTH PASS'S ATTACKER (2026-09-19;"), 'both surfaces record the pass');
  for (const fn of ['openGroup', 'closeGroups', 'pendingClose', 'noteGroupName', 'ZSH_MODIFIERS', 'readonlyNames', 'WRAPPED_CD_WHY']) {
    assert.ok(d47.includes(`\`${fn}\``), `decision 47 names ${fn}`);
    if (fn === 'pendingClose') { assert.ok(!/let pendingClose|pendingClose = \{|closeGroups\(pendingClose/.test(hook), 'pendingClose is gone from the hook since the third addendum (its history stays in the comments), and decision 47 says so'); continue; }
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

// Round 5's fifth addendum's third fix-up (2026-09-20): six rules, each stated once at its home in the hook and on decision 47 in the
// same words, the functions that carry them, the two fixtures with their populations, the residuals named on the header, the decision
// and the README, and the three prose surfaces' sentence
test("decision 47, the hook and the prose surfaces record the fifth addendum's third fix-up: the six rules (the unquoted body, the resolved substitution, the default word, zsh's `=(cmd)`, the consumer's stdin, the split operand) at their homes and on decision 47 in the same words, the functions, the two matrix fixtures with their populations, the residuals named with the brace-body closer on the header, the decision and the README, and the three surfaces' sentence", () => {
  const RULES = {
    'the unquoted body': "a here-document whose delimiter has no quoted character has its body expanded by the shell before the command reads it, so a `$(...)`, a backtick, a `${...}` and a `$name` in the body are read as they are anywhere else and the body the consumer reads is the text after those expansions; a delimiter with any quoted character keeps the body as written and runs nothing",
    'the resolved substitution': "a `$(...)` or a backtick whose command is one echo or printf with literal operands and no redirection prints text the guard can see, and that text stands in the word where the shell puts it, whole where no shell splits an expansion's result (inside double quotes, as a here-string, in a here-document body, as the word of a `${...}` operator), split at blanks into the words the shell makes among unquoted operands, and at a redirection target both, the whole text as dash opens it and each blank-separated field as zsh opens it (bash opens the one field, or none of several), each a redirection of its own, so the word is literal and a script it forms is read as the here-string form already is; when echo's two readings differ, a word that is the substitution alone keeps both texts and a script formed from it is read under each",   // the redirection target moved out of the no-split list in round 6's third commit (THE SPLIT TARGET)
    'the default word': "`${name:-word}`, `${name-word}`, `${name:=word}` and `${name=word}` stand for word when the name is unset, and `${name:+word}` and `${name+word}` when it is set, so when word lexes to one literal text under the word's quoting that text is a reading of the word, read as a script where the word is one (a `-c` operand, a here-string, a here-document body fed to a shell), in every position, since zsh splits no expansion's result",
    "zsh's =(cmd)": "zsh performs `=(cmd)` where a word begins, unquoted (an operand, an assignment's value, the word of a `${...}` operator, a replacement part), and nowhere else, so it is read as `<(cmd)` is, cmd running and read like a `$(...)`, for the Bash tool's command and for a script handed to zsh",
    "the consumer's stdin": "a compound command's standard input is the pipeline's, and so is what a redirection on its closer feeds it, so every command inside it that reads its script from stdin reads what was piped into the compound or redirected onto its closer; a `<` into the standard input feeds the command what it names, read when it is a process substitution whose command is a literal echo or printf, as a script operand that is one is read; a script operand naming the standard input (`-`, `/dev/stdin`, `/dev/fd/0`, `/proc/self/fd/0`) reads it; and a `-c` script, a `$(...)` and a script the shell reads from a file run with their caller's standard input",
    'the split operand': "when a copying writer (cp, mv, install, ln) has fewer operands than its two and one of them is an unquoted expansion the guard did not resolve, the shell may split it into the operands the writer needs, so that operand is a target the hook cannot read",
  };
  const d47Flat = d47.replace(/\s+/g, ' ');
  assert.ok(d47Flat.includes("THE THIRD FIX-UP (2026-09-20; the second fix-up's two verifiers, on its head)"), 'decision 47 records the third fix-up');
  assert.ok(hook.includes("ROUND 5'S FIFTH ADDENDUM, THIRD FIX-UP (2026-09-20; the second fix-up's two verifiers, on its head)"), 'the hook header records it');
  for (const [name, rule] of Object.entries(RULES)) {
    assert.ok(hook.includes(rule), `the hook states the rule of ${name}`);
    assert.ok(d47Flat.includes(rule), `decision 47 states the rule of ${name} in the same words`);
  }
  for (const fn of ['literalOutput', 'procsubOf', 'resolvedSub', 'defaultReading', 'readHeredocBodies', 'producerAt', 'pipedFrom', 'closerStdin', 'eqProcsubStart', 'STDIN_NAMES', 'HEREDOC_BODY_VIA', 'READING_VIA', 'isGlobMark', 'splitOperand', 'inheritedStdin']) {
    assert.ok(hook.includes(fn), `the hook has ${fn}`);
  }
  // the homes: the lexer resolves through literalOutput, the ${ read reads the default word from the one descent, the body is expanded
  // through the lexer in its own mode, =( is zsh's alone, the stdin names are read by shellScript and the interpreter walk, the
  // compounds carry the producer and the closer's text, a -c script inherits its caller's stdin, and the copying writers' one operand
  assert.ok(hook.includes("return placeReading(literalOutput(inner, shell, nestDepth), spelling, 'text');") && hook.includes("else { const r = resolvedSub('$(' + inner + ')', inner); if (r !== true) { if (!r) { opaqueExpansion(hdInner ? '$(' + inner + ')' : undefined); wordMayReadStdin = '$(' + inner + ')'; } seg.subs.push(inner); } }"), 'a $(...) is resolved before it is read as a command (round 6\'s second commit: an UNRESOLVABLE reading marks the word and the commands are read all the same; the fourth commit marks a list the resolver does not read as one that may read the standard input)');
  assert.ok(hook.includes("const placed = defaultReading(inner, op[0].length, nested, { name: op[1], op: op[2] });"), 'the default word from the one descent (with its name and operator since round 6\'s fifth commit)');
  assert.ok(hook.includes("const x = lex(body, shell, { quotes: 'heredoc', comments: false, depth: nestDepth + 1, ifsNamed });") && hook.includes("if (q || !/[$`]/.test(body) || nestDepth >= NESTED_DEPTH_CAP) { owner.heredocs.push(body); continue; }"), 'an unquoted body is expanded through the lexer, a quoted one kept');
  assert.ok(hook.includes("const zshGrammar = shell == null || shell === 'zsh';") && hook.includes("if (zshGrammar && c === '(' && eqProcsubStart()) {"), "=( is read under zsh's grammar");
  assert.ok(hook.includes("if (s || !operand || (operand.literal && isStdinName(operand.text))) return done({ stdin: true, fd: operand && operand.literal ? fdOfName(operand.text) : null, argsAt: !operand ? args.length : s ? at(operand) : at(operand) + 1 });") && hook.includes("if (a.literal && isStdinName(a.text)) { stdinFd = fdOfName(a.text); break; }") && hook.includes("const isStdinName = (text) => STDIN_NAMES.has(text) || /^\\/(?:dev|proc\\/self)\\/fd\\/[0-9]+$/.test(text);"), 'a script operand naming stdin, or a numbered descriptor (round 6\'s third commit), reads it, for a shell and for an interpreter; the behaviour is pinned by execution in tools/romp-track-bash-guard.test.mjs (the third commit\'s rows: `bash /dev/fd/3 3<<EOF`, `. /dev/fd/3 3<<< ..`)');
  assert.ok(hook.includes("stdinFrom: pipedFrom(), stdinText: closerStdin(idx, 'subshell')") && hook.includes("stdinFrom: pipedFrom(), stdinText: closerStdin(walkIdx, 'group')") && hook.includes("stdinFrom: pipedFrom(), stdinText: closerStdin(walkIdx, head)"), 'every compound frame carries the producer piped into it and the text redirected onto its closer');
  assert.ok(hook.includes("stdin: stdin != null ? stdin : (walkIdx >= 0 ? stdinBodies(walkIdx) : inheritedStdin),") && hook.includes("const f = readFeed(idx, sh.fd);") && hook.includes("for (const body of f.bodies) recurse(body, name, undefined, '', []);"), 'a -c script inherits its caller\'s stdin; a script fed on stdin passes nothing on (the descriptor the operand names is read too since round 6\'s fourth commit)');
  assert.ok(hook.includes("if (operandsAsSpelled.length < 2 && operandsAsSpelled.some(maySplit)) cannotRead(operandsAsSpelled.find(maySplit), name, { kind: 'splitOperand' });"), 'the split operand');
  // the two fixtures and their populations
  for (const [file, key] of [['romp-track-bash-guard-stdin-script-matrix.json', 'shells'], ['romp-track-bash-guard-heredoc-body-matrix.json', 'consumers']]) {
    const f = JSON.parse(fs.readFileSync(path.join(REPO, 'tools', file), 'utf8'));
    assert.ok(f.rows > 0 && typeof f.population === 'string' && f.population.includes('produced by') && f.note.includes('NOT exhaustive') && Array.isArray(f[key]), `${file} states its population and that it is not exhaustive`);
    assert.ok(d47Flat.includes('`tools/' + file + '`'), `decision 47 names ${file}`);
  }
  // the residuals, named with the brace-body closer on the header, the decision and the README
  for (const [name, text] of [['the hook header', hook], ['decision 47', d47], ['hooks/README.md', hooksReadme]]) assert.ok(text.replace(/\s+/g, ' ').includes("zsh's brace-body compound"), `${name} names the brace-body closer residual`);
  // the three prose surfaces carry the third fix-up's sentence
  const SENT3 = "and since its third fix-up the same day an unquoted here-document body's expansions are read as the commands they run and the expanded body is the consumer's script (a quoted delimiter keeps the body as written), a `$(echo '...')` or a backtick with literal operands is the text it prints where the shell puts it (so `bash -c \"$(echo 'cp a b')\"` and `$(echo cp) a b` copy), a `${x:-word}` alone is read as a script under its default word, zsh's `=(cmd)` runs its command, a shell fed through a subshell, a group, an if or loop body, a `/dev/stdin` operand, a `<(echo '...')` script, a redirection on the compound's closer or a `-c` script's inner shell reads what was piped or redirected to it, and a copying writer whose one unquoted operand the shell may split into two refuses while a project is in play (a `${...}` word the guard cannot read as a script, a producer outside its output model (since round 6's second commit, 2026-09-21, the model reads a subshell or a group of echo, printf and silent commands as what it prints), a redirection on the closing brace of zsh's brace-body compound and a command whose name is an expansion the resolver never reads stay unread and are named)";
  const prose = { 'hooks/README.md': hooksReadme, 'docs/install.md': read('docs', 'install.md'), 'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md') };
  for (const [name, text] of Object.entries(prose)) assert.ok(text.replace(/\s+/g, ' ').includes(SENT3), `${name} carries the third fix-up's sentence`);
  const censusSrc = fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-census.mjs'), 'utf8');
  assert.ok(censusSrc.includes("STDIN_NAMES: { side: 'WRITE'"), 'the census names the stdin names with their side');
});

// Round 6's second commit (2026-09-21; round 5's ruling C): THE RESIDUAL PROPERTY is one paragraph, identical (whitespace and case
// aside) on the surfaces that describe the guard, and its classes are exactly the ones the residual table in
// tools/romp-track-bash-guard.test.mjs measures (RESIDUAL_CLASSES there carries the same class names and glosses, asserted against the
// hook header by that test), so a class added to the table without the sentence, or a surface that drifts, fails here by name. Since round 7
// of fork PR #780 review, thirty-fifth commit (the reviewer's regression-2 and extra7-3), the identical text stands on the developer
// surfaces only (their count derived below from the surfaces the test holds, never typed; the thirty-sixth commit dropped the typed one): the vendored SKILL.md states the classes in its reader's words (held to RESIDUAL_CLASSES by name in the guard's test) and
// docs/guide.md points at docs/install.md (tests/test_guide_files_bash_guard.py), and neither carries the developer paragraph.
test("round 6, second commit: THE RESIDUAL PROPERTY is stated identically on the developer surfaces (the hook header, decision 47, hooks/README.md, docs/install.md and the ledger entry) and on no user-facing one, the count stated on the hook header and decision 47, and the alias road, the head splice and the output model are recorded on decision 47 and the hook header", () => {
  const norm = (s) => s.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  const PROPERTY = 'the residual property. the guard refuses a write only when it resolves the command to a writer it models (the writer cases of extract\'s switch, a write redirection, an interpreter\'s write call it scans) reached through a road it reads (the wrapper set, the shells\' script roads, the readings of the resolver, the alias and hash roads), with a target it can place or cannot read, or when a command whose name, script or piped script it does not read names a tracked file as a literal operand. every write that still reaches a tracked file is one the guard does not resolve to such a writer through such a road, whether or not its text stands in the command, and falls in one of these classes, each measured by execution in tools/romp-track-bash-guard.test.mjs (the residual table, whose rows are the population this statement is over): a writer outside the model, a program, or a write form of a program the hook models, that writes the file by its own nature and is not among the write forms the hook reads (rsync, patch, tar -x, ed, ex, vim, make, shuf -o, gawk -i inplace, awk\'s print redirect, uniq, scp, openssl -out, shred, curl -o, wget -o, find -exec, a git alias or a subcommand that writes the tree, bash\'s history -w, zsh\'s sysopen and mapfile modules, sed\'s e command and a w command in a sed script the resolver cannot read, busybox\'s applets); a reader outside the roads, a program that runs a command or a script the hook does not follow into it (xargs, an interpreter\'s system, exec or subprocess call, a wrapper outside the set, a shell outside shells, a file the command writes and then runs or sources, a function\'s call of itself, which the replay does not follow again); a command name the resolver never reads, a command whose name is an expansion of a kind the resolver does not read ("${a[@]}", a loop variable, a name read or filled by getopts, printf -v or a nameref, a name the shell itself sets (${shell}, $0, $bash, $zsh_argzero, $_ after a command), a substitution outside the output model such as $(which cp), a ${...} operator form the resolver does not read, a positional parameter of a script handed to a fresh shell with arguments of its own; "$@", $1 and $* stand for the operands of a called function or of a `set` this shell ran since round 6\'s sixth commit), handed no literal operand that names a tracked file (the operand a directory, or a word the resolver does not read): since round 7\'s twenty-fifth commit a command so named, or a script or piped script the resolver does not read, whose literal operand names a tracked file is refused by name (the reviewer\'s q1: the target known, the writer not); a script held in a variable, a value the command gives a name through a construct the resolver does not read (`read`, `printf -v`, a positional parameter of a fresh shell\'s script), run as a command or handed to a shell (`$c` after `read c`, `eval "$1"` inside a `bash -c` given arguments, `bash -c "$c"` after `printf -v c`; a value an assignment word gives, whitespace included, is read through the head candidates since round 6\'s fourth commit, and a `${name:=word}` gives word since the sixth); a producer outside the output model, a pipe into a shell, or a write redirection into a process substitution running one, from anything but a literal echo or printf, alone or in a subshell or group of such commands, or a plain cat passing such a text through, or a command substitution over such a producer handed to a shell, an eval or a here-string (a call of a function the command defines, a tee or a pipe through another command, a cat of a file, an eval or a shell -c inside the substitution); zsh\'s glob grouping, a `(..)` inside a word handed to zsh, read as a subshell by the lexer\'s zsh grammar while zsh globs it (a lexer gap, stated since the first commit of this round); zsh\'s hook functions, a function the command defines under a name zsh calls on its own (chpwd, precmd, preexec, periodic, zshexit, and the names in chpwd_functions and its kin), whose body runs when the shell moves, prompts or exits, from the directory the shell is in then, while the guard judges the definition where it stands; an opaque expansion from a cwd outside every project, a leading opaque expansion, or one after a literal head outside every project, from a cwd in no project (b2 as ruled, with its boundary). a shape outside these classes that reaches a tracked file is a rule to state, not a residual.';
  const surfaces = {
    'hook header': hook,
    'decision 47': d47,
    'hooks/README.md': hooksReadme,
    'docs/install.md': read('docs', 'install.md'),
    'the ledger entry': read('upstream', '2026-09-18-track-guard-non-literal-targets.md'),
  };
  const body = PROPERTY.slice(PROPERTY.indexOf('the guard refuses a write only when'));
  for (const [name, text] of Object.entries(surfaces)) assert.ok(norm(text).includes(body), `${name} carries THE RESIDUAL PROPERTY identical`);
  // the user-facing surfaces carry none of the developer paragraph: not its statement, not its label, not a clause of its provenance
  const userFacing = { 'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md'), 'docs/guide.md': read('docs', 'guide.md') };
  for (const [name, text] of Object.entries(userFacing)) {
    const n = norm(text);
    assert.ok(!n.includes(body.slice(0, 200)) && !n.includes('the residual property') && !n.includes("stated since the first commit of this round") && !n.includes('b2 as ruled, with its boundary'), `${name} carries no part of the developer paragraph of THE RESIDUAL PROPERTY`);
  }
  // the count, derived from the surfaces this test holds identical, stated with them on the hook header and decision 47
  const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];
  const count = WORDS[Object.keys(surfaces).length];
  assert.ok(norm(hook).includes(`the residual property stands identical on ${count} surfaces, the developer ones: this header, decision 47, hooks/readme.md, docs/install.md and the ledger entry`), `the hook header states the ${count} surfaces the property is pinned identical on, and names them`);
  assert.ok(norm(d47).includes(`the residual property stands identical on ${count} surfaces, the developer ones: this decision, the hook header, hooks/readme.md, docs/install.md and the ledger entry`), `decision 47 states the ${count} surfaces, and names them`);
  assert.ok(!norm(hook).includes('the property is on decision 47, docs/guide.md and the ledger entry too'), 'the hook header no longer states the guide as a surface of the property');
  assert.ok(norm(surfaces['the ledger entry']).includes(`keeps that text identical on the ${count} developer surfaces (the hook header, decision 47, hooks/readme.md, docs/install.md and this entry)`), `the ledger entry states the ${count} surfaces, and names them`);
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = norm(text);
    for (const phrase of ['round 6, second commit (2026-09-21', 'the alias road', 'the head splice', 'the output model', 'the evidence a row needs', 'pins the key set of construct_heads by kind']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['listOutput', 'catOfHeredoc', 'SILENT_COMMANDS', 'aliases', 'hashes', 'aliasState', 'bound', 'aliasChain', 'lineOf', 'headTexts']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's third commit (2026-09-21; the round's three verifiers on the second commit's head): every finding a write a shell performed
// while the guard allowed it, each closed by refusing, recorded on decision 47 and the hook header, with the functions that carry it.
test("round 6, third commit: decision 47 and the hook header record zsh's unbraced flags, the split target, the alias road into a text parsed later, a descriptor as the script, the sed script, a glob in the command name and a cat of the standard input, the hook has the functions that carry them, and the property's writer class covers a write form of a modelled program", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, third commit (2026-09-21', "zsh's unbraced flags", 'the split target', 'the alias road into a text parsed later', 'a descriptor as the script', 'the sed script', 'a glob in the command name', 'a cat of the standard input']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['expandedFields', 'isStdinName', 'sedWriteFiles', 'sedScriptWrites', 'lineBase', 'lineStep']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  assert.ok(hook.includes("if (zsh && next != null && '=^~'.includes(next)) {"), "expansionAt reads zsh's unbraced flags under zsh's grammar (pinned by execution in the shapes test and the rows test)");
  assert.ok(hook.includes("if (/[ \\t\\n]/.test(buf)) for (const [t, m] of expandedFields(buf, marks)) seg.redirects.push({ op: expect.op, target: mk(t, m) });"), 'endWord records each field of a split target (pinned by execution in the shapes test and the rows test)');
  assert.ok(hook.includes("for (const w of sw.targets) add(w, 'sed w');"), "sed's w files are targets (pinned by execution in the rows test)");
  const flat = hook.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  assert.ok(flat.includes('a writer outside the model, a program, or a write form of a program the hook models, that writes the file by its own nature and is not among the write forms the hook reads'), 'the writer class covers a write form of a modelled program (sed\'s w in a script the resolver cannot read is a member, not a shape outside every class)');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's fourth commit (2026-09-21; the round's three verifiers on the third commit's head): every finding a write a shell performed
// while the guard allowed it, each closed by refusing under a rule keyed on the shells' grammars, recorded on decision 47 and the hook
// header with the functions and tables that carry it; the property's fourth class restated to the names a construct the resolver does
// not read fills in, since a plain-string value is read through THE HEAD CANDIDATES.
test("round 6, fourth commit: decision 47 and the hook header record the descriptor feed, the exec feed, the alias body, the bound path, the compound producer, the option terminator, the head candidates, the IFS rule, the fed substitution, the sed file, the valued names and env's operand, the hook has the functions and tables that carry them, and the property's fourth class names the head candidates", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, fourth commit (2026-09-21', 'the descriptor feed', 'the exec feed', 'the alias body', 'the bound path', 'the compound producer', 'the option terminator', 'the head candidates', 'the ifs rule', 'the fed substitution', 'the sed file', 'the valued names', "env's operand"]) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['fdOfName', 'execFeeds', 'fedTexts', 'noteCandidate', 'candidateTexts', 'readValuedWords', 'SCRIPT_VALUED_NAMES', 'STARTUP_FILE_NAMES', 'sedFileBodies', 'mayReadStdin', 'ifsNamed']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  assert.ok(hook.includes("if (s.fd != null && fds && !fds.has(s.fd)) continue;"), 'textsOf reads a `<` on the descriptors the operand names and the dups reach (pinned by execution in the rows tests of the fourth and fifth commits)');
  assert.ok(hook.includes("if (!(inWord && buf)) endWord();"), 'a glued process substitution stays in its word (pinned by execution in the rows test)');
  const flat = hook.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  assert.ok(flat.includes('a script held in a variable, a value the command gives a name through a construct the resolver does not read'), "the property's fourth class is restated (its members are RESIDUAL_TABLE's `read`, positional and `printf -v` rows)");
  const censusSrc = fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-census.mjs'), 'utf8');
  assert.ok(censusSrc.includes("SCRIPT_VALUED_NAMES: { side: 'WRITE'") && censusSrc.includes("STARTUP_FILE_NAMES: { side: 'WRITE'"), 'the census names the two tables with their side');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's fifth commit (2026-09-21; the round's three verifiers on the fourth commit's head): every finding a write a shell performed
// while the guard allowed it, each closed by a rule fitted to its class, recorded on decision 47 and the hook header with the functions
// that carry it; the contract paragraph gains the sentence on deleting or moving a tracked file (the four-surface pin above holds it), and
// the property's classes name getopts and the plain cat the output model now passes through (the property's surface pin holds those).
test("round 6, fifth commit: decision 47 and the hook header record the parameter's value, the moved shell, the duplicated descriptor, the passed-through text, the startup feed, the exported function, the spliced definition, the called body and the assignment value, the hook has the functions that carry them, the contract paragraph says a deletion or a move away is not a write it refuses, and no committed line names the reviewer's session", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, fifth commit (2026-09-21', "the parameter's value", 'the moved shell', 'the duplicated descriptor', 'the passed-through text', 'the startup feed', 'the exported function', 'the spliced definition', 'the called body', 'the assignment value', 'deleting or moving a tracked file away']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['fdsFor', 'passthroughCat', 'defLineOf', 'functionBodies', 'fnChain', 'readingParams', 'assignmentValue', 'glueOf', 'paramsOf', 'unreadValues', 'candidateTexts', 'movedAny', 'runFunction', 'callArgs']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  assert.ok(hook.includes("if (src[i + 1] === '&') { i += 2; expect = { kind: 'dup', fd: fdDigits }; continue; }"), 'the lexer records a `<&` dup (pinned by execution in the fifth commit\'s rows test)');
  assert.ok(hook.includes("if (sub.moved && opts.adopt) {"), 'recurse adopts the directory state of a text this shell ran (pinned by execution in the fifth commit\'s rows test)');
  for (const [name, text] of [['the hook header', hook], ['the vendored SKILL.md', read('vendor', 'track-changents', 'skill', 'SKILL.md')], ['hooks/README.md', hooksReadme], ['docs/install.md', read('docs', 'install.md')]]) assert.ok(text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').includes('is not a write it refuses: the contract is the write that lands on a tracked file'), `${name} says a deletion or a move away is not a write the guard refuses`);
  // (D) the round's rule for committed text: the reviewer is "the reviewer", never a session name, on the files the offer changes
  const sessionName = new RegExp(['romp', 'manager'].join('-') + "'s");   // the reviewer's session name, assembled so this file does not spell it either
  for (const rel of ['hooks/romp-track-bash-guard.mjs', 'plans/file-review.md', 'tools/romp-track-bash-guard.test.mjs']) assert.ok(!sessionName.test(read(...rel.split('/'))), `${rel} names the reviewer, not a session`);
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's sixth commit (2026-09-21; the round's three verifiers on the fifth commit's head): three passes had each found roads by which a
// text the hook could not establish reached an allow through a null, so the mechanism is fixed once (THE APPLIED RESOLVER) and the rows follow;
// with it the unread script word, the special parameter, the assigned default, the shell's option word, the positional value and the empty
// alternative, each recorded on decision 47 and the hook header in the same words with the functions that carry it, and the property's second,
// third and fourth classes restated for the members the table gained (the property's surface pin above holds the paragraph).
test("round 6, sixth commit: decision 47 and the hook header record the applied resolver, the unread script word, the special parameter, the assigned default, the shell's option word, the positional value and the empty alternative, the hook has the functions that carry them, and the property's classes name a function's call of itself and a fresh shell's positional parameters", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, sixth commit (2026-09-21', 'the applied resolver', 'the unread script word', 'the special parameter', 'the assigned default', "the shell's option word", 'the positional value', 'the empty alternative', 'null is reserved for a segment whose head is no printer at all']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['printerOf', 'shapeOnPrinter', 'closerOutput', 'paramAssigns', 'optionWord', 'readShell', 'bindPositionals', 'positionalWords', 'expandPositionals', 'setOperands', 'positionalsApply', 'functionLines', 'braceEmpty', 'shellOptionWord', 'UNKNOWN_POSITIONALS']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  assert.ok(hook.includes("if (k < args.length - 1) return done({ optionWord: args[k], at: k });"), "shellScript hands an expansion in option position back to the walk (pinned by execution in the sixth commit's rows test)");
  assert.ok(hook.includes("if (fnName != null && !fnChain.has(fnName)) for (const callArgs of callVariants) recurse(functionBodies.get(fnName), shell, false,"), 'the called body replays for every call (pinned by execution in the rows test)');
  const flat = hook.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  assert.ok(flat.includes("a function's call of itself, which the replay does not follow again"), "the property's second class names the self-call");
  assert.ok(flat.includes('a positional parameter of a script handed to a fresh shell with arguments of its own'), "the property's third class names a fresh shell's positional parameters");
  assert.ok(flat.includes('and a `${name:=word}` gives word since the sixth'), "the property's fourth class names the assigned default");
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's eighth commit (2026-09-22; the round's three verifiers on the seventh commit's head): the regression left open through the wrappers,
// the vanishing operand and the case pattern's paren, each fixed at the mechanism and recorded on decision 47 and the hook header in the same
// words with the functions that carry it; the property's third class names the shell-set names and an eighth class zsh's hook functions (the
// property's surface pin above holds the paragraph); the piped-script fixture names its allowed rows without writer evidence in a field of its own.
test("round 6, eighth commit: decision 47 and the hook header record the wrapped printer, the vanishing operand and the paren rule, the hook has the functions that carry them and asks the paren rule from the walk and the lexer alike, the property's third class names the shell-set names and its eighth class zsh's hook functions, and the piped-script fixture names its allowed rows without writer evidence", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, eighth commit (2026-09-22', 'the wrapped printer', 'the vanishing operand', 'the paren rule', 'one road for the printer', 'the operand count', 'one home', 'a shell no box running the matrix has']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['parenCloses', 'mayVanish', 'vanishVariants', 'droppedHow', 'NEVER_EMPTY_EXPANSION', 'VANISH_CAP', 'lexScopes', 'patternParen']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  // the paren rule has one home: the walk's closeSubshell and the lexer's marker both ask parenCloses (the behaviour is pinned by execution in the eighth commit's rows test)
  assert.ok(hook.includes('const j = parenCloses(frames.map((f) => f.kind));'), 'the walk asks the paren rule over its frames');
  assert.ok(hook.includes("else { const j = parenCloses(lexScopes); if (j >= 0) lexScopes.length = j; else if (lexScopes.includes('case')) marker.pattern = true; }"), "the lexer asks it over the scopes it tracks and marks a pattern's `)`");
  assert.ok(hook.includes("return w && !w.literal && w.marks && w.marks.includes('x') ? splicedPrinter(s, at) : null;"), 'printerOf splices an expansion where the wrapper walk stopped (pinned by execution in the rows test)');
  const flat = hook.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  assert.ok(flat.includes('a name the shell itself sets (${shell}, $0, $bash, $zsh_argzero, $_ after a command)'), "the property's third class names the shell-set names");
  assert.ok(flat.includes("zsh's hook functions, a function the command defines under a name zsh calls on its own"), "the property's eighth class names zsh's hook functions");
  const pin = JSON.parse(fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-piped-script-matrix.json'), 'utf8'));
  assert.ok(Array.isArray(pin.allowedWithoutWriterEvidence.ksh) && pin.allowedWithoutWriterEvidence.ksh.length > 0 && pin.allowedWithoutWriterEvidence.why.includes('measured for them nowhere'), 'the piped-script fixture names its allowed rows without writer evidence in a field (the matrix test derives the list)');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's ninth commit (2026-09-22; the round's three verifiers on the eighth commit's head): the positional target, the peeled name, the
// vanished text and the written process substitution, each fixed at the mechanism and recorded on decision 47 and the hook header in the same
// words with the functions that carry it; the property's fifth class names the write redirection into a process substitution (the property's surface
// pin above holds the paragraph); the eighth commit's records date it the day of its commit.
test("round 6, ninth commit: decision 47 and the hook header record the positional target, the peeled name, the vanished text and the written process substitution, the hook has the functions that carry them and consumes the stream reading through placeReading alone, the property's fifth class names the write redirection into a process substitution, and the eighth commit's records date it 2026-09-22", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, ninth commit (2026-09-22', 'the positional target', 'the peeled name', 'the vanished text', 'the written process substitution', 'one redirection per word', 'asked the three roads', 'a pipe into cmd', 'round 6, eighth commit (2026-09-22']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
    assert.ok(!flat.includes('eighth commit (2026-09-21'), `${name} no longer dates the eighth commit a day early`);
  }
  for (const fn of ['streamSite', 'streamOutput', 'procsubFeeds', 'outDups', 'recurseSubs', 'inheritedTexts', 'nameRoads', 'boundRoad', 'wrapperIdx', 'NEVER_EMPTY_RUN']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  // the roads are asked of every peeled word, the stream reading is consumed through placeReading alone (THE RESOLVER'S CONTRACT is structural), the
  // positional list has a target mode, and the vanished reading is candidateTexts' own; each pinned by execution in the ninth commit's rows test
  assert.ok(hook.includes('for (const j of peeledIdx) if (j !== headIdx) nameRoads(seg.words[j], j);'), 'the alias and hash roads are asked of every peeled word');
  assert.ok(hook.includes('for (const j of peeledIdx) if (j !== headIdx) boundRoad(seg.words[j], j);'), 'and the bound-path road');
  assert.ok(hook.includes("if (site) placeReading(streamOutput(site, view), site.spelling, 'segment', holder);"), 'the written substitution\'s reading is placed through placeReading');
  assert.ok(hook.includes("if (oneWord === 'target') {"), 'positionalWords has a target mode');
  assert.ok(hook.includes('const v = candidateTexts(w, true);'), 'scriptTexts asks the vanished reading');
  const flat = hook.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
  assert.ok(flat.includes('a pipe into a shell, or a write redirection into a process substitution running one, from anything but a literal echo or printf'), "the property's fifth class names the write redirection into a process substitution");
  const pin = JSON.parse(fs.readFileSync(path.join(REPO, 'tools', 'romp-track-bash-guard-piped-script-matrix.json'), 'utf8'));
  assert.ok(pin.allowedWithoutWriterEvidence.why.includes("round 6's eighth commit, 2026-09-22"), 'the piped-script fixture dates the eighth commit the day of its commit');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's tenth and eleventh commits (2026-09-22): the tenth commit's record was missing on decision 47 and the hook header while the hook's
// inline comments named it (the round's record verifier on the tenth's head), so beside the phrase pins the record list is DERIVED: every
// ordinal the hook's own text names as "round 6's Nth commit" has a ROUND 6, NTH COMMIT record on the header and on decision 47, dated alike,
// the records run from the second to the latest with no gap, and the latest record is the latest commit the hook names. A missing record for
// the newest commit reds here before anyone reads the header.
test("round 6, tenth and eleventh commits: decision 47 and the hook header record the ifs rule, the multi-digit positional, the alternate value, the vanishing head, the routed standard output, the counted slice, the bound name and the keyword dash runs; every commit the hook names has a record on both, dated alike, with no gap to the latest; the hook has the functions that carry the eleventh commit's fixes and asks the roads at the three keyword sites", () => {
  const ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth', 'seventeenth', 'eighteenth', 'nineteenth', 'twentieth'];
  const named = new Set([...hook.matchAll(/round 6's (\w+) commit/g)].map((m) => m[1].toLowerCase()).filter((o) => ORDINALS.includes(o)));
  assert.ok(named.size >= 2, `the hook's own text names round 6's commits (${named.size})`);
  // the hook is read raw (a record heads a `//` line); decision 47 comes through `between`, whitespace collapsed to one line, so its records are matched unanchored
  const records = (text, re) => new Map([...text.matchAll(re)].map((m) => [m[1].toLowerCase(), m[2]]));
  const headerRecords = records(hook, /^\/\/ ROUND 6, (\w+) COMMIT \((\d{4}-\d{2}-\d{2})/gm);
  const planRecords = records(d47, /ROUND 6, (\w+) COMMIT \((\d{4}-\d{2}-\d{2})/g);
  const firstHeader = hook.match(/^\/\/ ROUND 6 \((\d{4}-\d{2}-\d{2})/m);
  const firstPlan = d47.match(/ROUND 6 \((\d{4}-\d{2}-\d{2})/);
  assert.ok(firstHeader && firstPlan && firstHeader[1] === firstPlan[1], "the first commit's record stands on both, dated alike");
  for (const o of named) if (o !== 'first') {
    assert.ok(headerRecords.has(o), `the hook header records round 6's ${o} commit (the hook's own text names it)`);
    assert.ok(planRecords.has(o), `decision 47 records round 6's ${o} commit`);
    assert.equal(planRecords.get(o), headerRecords.get(o), `the ${o} commit's two records date it alike`);
  }
  const latest = Math.max(...[...headerRecords.keys()].map((o) => ORDINALS.indexOf(o)));
  for (let i = 1; i <= latest; i++) assert.ok(headerRecords.has(ORDINALS[i]) && planRecords.has(ORDINALS[i]), `no gap: round 6's ${ORDINALS[i]} commit is recorded on both`);
  assert.equal(ORDINALS[latest], [...named].sort((a, b) => ORDINALS.indexOf(b) - ORDINALS.indexOf(a))[0], 'the latest record is the latest commit the hook names');
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, tenth commit (2026-09-22', 'round 6, eleventh commit (2026-09-22', 'the ifs rule', 'the multi-digit positional', 'the alternate value', 'the vanishing head', 'the routed standard output', 'the counted slice', 'the bound name', 'the keyword dash runs', 'one home']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['headMayVanish', 'vanishedHeadTexts', 'dashCommandRoads', 'runHeadSplices', 'absSpelled', 'rereadForVanish']) assert.ok(hook.includes(fn), `the hook has ${fn}`);
  // where the code lives; what it does is pinned by execution in the eleventh commit's rows test (tools/romp-track-bash-guard.test.mjs, the S11 rows)
  assert.equal((hook.match(/dashCommandRoads\(seg\.words\[(p|at)\], (p|at)\);/g) || []).length, 3, "the three keyword sites (function, coproc, repeat) ask the roads under dash's grammar");
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's twelfth commit (2026-09-22): the record on both surfaces, the rules it names, the constants and functions that carry its fixes
// (what they do is pinned by execution in the twelfth commit's rows test, tools/romp-track-bash-guard.test.mjs, the S12 rows), and the fifth
// class's gloss naming the command substitution conduit on every surface the property stands on.
test("round 6, twelfth commit: decision 47 and the hook header record the subscripted positional, the vanished head text, the stale positional candidate, the body's own list and the option flags; the hook has the constants and functions that carry them; the fifth class names the command substitution conduit on every surface", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, twelfth commit (2026-09-22', 'the subscripted positional', 'the vanished head text', 'the stale positional candidate', "the body's own list", 'the option flags', '268 rows over the same 8 classes']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  for (const fn of ['const ZSH_POSITIONAL_SUBSCRIPT = ', 'const NEVER_EMPTY = ', 'const vanishedHeadTexts = (w) => {', "const posEl = (k) => positionals[k] && positionals[k].literal", "if (name === 'set' && positionalsApply())"]) assert.ok(hook.includes(fn), `the hook has ${fn.trim()}`);
  const CONDUIT = 'or a command substitution over such a producer handed to a shell, an eval or a here-string';
  // the developer surfaces since round 7 of fork PR #780 review, thirty-fifth commit; the vendored SKILL.md names the conduit in its reader's words
  const surfaces = { 'the hook header': hook, 'decision 47': d47, 'hooks/README.md': hooksReadme, 'docs/install.md': installDoc, 'the ledger entry': read('upstream', '2026-09-18-track-guard-non-literal-targets.md') };
  for (const [name, text] of Object.entries(surfaces)) assert.ok(text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').includes(CONDUIT), `${name} names the conduit in the fifth class`);
  assert.ok(read('vendor', 'track-changents', 'skill', 'SKILL.md').replace(/\s+/g, ' ').includes('or a command substitution over such a producer handed to a shell, an eval or a here-string'), 'the vendored SKILL.md names the conduit in its statement of the fifth class');
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 6's thirteenth commit (2026-09-22; the round's two verifiers on the twelfth commit's head): three populations measured allowing while a shell
// writes, each pre-existing at the round-5 head, filed on the residual table under one class named for the mechanism with no change to the hook, for
// the round's ruling (fixed at the mechanism, or accepted as allow-by-default). The record on both surfaces, the class on every surface the property
// stands on (and as a key of RESIDUAL_CLASSES, whose gloss the table's own test holds equal to the header's), the rows under it counted from the
// table's source, and the three members of stated classes filed beside their witness rows.
test("round 6, thirteenth commit: decision 47 and the hook header record the empty positional, the stale positional candidate, the known set and the subscripted positional beyond one numeric index as rows under the positional-model class with the table's count; the class is gone from every surface the property stands on and from RESIDUAL_CLASSES since round 7's twenty-fifth commit, its rows refused; and the three witnessed members", () => {
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook]]) {
    const flat = text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase();
    for (const phrase of ['round 6, thirteenth commit (2026-09-22', 'the empty positional', 'the stale positional candidate', 'the known set', 'the subscripted positional beyond one numeric index', 'a positional the resolver reads at the word by a model the shell does not keep', '423 rows over 9 classes']) assert.ok(flat.includes(phrase), `${name} records: ${phrase}`);
  }
  // round 7's twenty-fifth commit (the reviewer's extra5-2 as ruled, option (a)): the four readings are sound or unresolvable, every row of the class is
  // refused and pinned in the guard's test ("round 7, twenty-fifth commit, the rows"), and the class is gone from every surface the property stands on
  // and from RESIDUAL_CLASSES; the records above keep the thirteenth commit's filing as history, and each surface's record of the deletion is read here
  const CLASS = "a positional the resolver reads at the word by a model the shell does not keep, an element's emptiness, a binding a later shift or unset removed, zsh's subscript grammar beyond one index";
  const surfaces = { 'the hook header': hook, 'decision 47': d47, 'the vendored SKILL.md': read('vendor', 'track-changents', 'skill', 'SKILL.md'), 'hooks/README.md': hooksReadme, 'docs/install.md': read('docs', 'install.md'), 'docs/guide.md': read('docs', 'guide.md'), 'the ledger entry': read('upstream', '2026-09-18-track-guard-non-literal-targets.md') };
  for (const [name, text] of Object.entries(surfaces)) assert.ok(!text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').includes(CLASS), `${name} no longer states the ninth class`);
  for (const [name, text] of [['decision 47', d47], ['the hook header', hook], ['the ledger entry', surfaces['the ledger entry']]]) assert.ok(text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').toLowerCase().includes("round 7's twenty-fifth commit") || text.replace(/\/\//g, ' ').replace(/\s+/g, ' ').includes('ROUND 7 OF FORK PR #780 REVIEW, TWENTY-FIFTH COMMIT (2026-09-23'), `${name} records the deletion`);
  const guardTest = read('tools', 'romp-track-bash-guard.test.mjs');
  assert.ok(!guardTest.includes("  'a positional the resolver reads at the word by a model the shell does not keep': '"), 'RESIDUAL_CLASSES carries no ninth class');
  const under = (guardTest.match(/^\s*\['RT-(ep|sp|sb|zs)-[^']+', /gm) || []);
  assert.equal(under.length, 0, `no residual row of the class stands in the table (${under.length})`);
  assert.equal((guardTest.match(/^\s*\["S25-RT-(ep|sp|sb|zs)-[^"]+", /gm) || []).length, 137, 'the 137 rows the table held stand as refusals in the twenty-fifth commit\'s rows (the other 15 in the nineteenth\'s)');
  // round 7's twentieth commit derived the ledger's count of the stale-candidate and known-set rows here; with the class gone the entry states no count
  assert.ok(!/\d+ rows since round 7's nineteenth commit/.test(surfaces['the ledger entry']), 'the ledger entry states no count of the deleted class\'s rows');
  for (const id of ['RT-printf-v-unset-head', 'RT-cat-procsub-pipe', 'RT-procsub-function-cat']) assert.ok(guardTest.includes(`['${id}', `), `the witnessed member ${id} is a row`);
  assert.ok(!/\u2014/.test(d47), 'no em dash in decision 47');
});

// Round 7 of fork PR #780 review, thirty-fifth commit (the reviewer's tests-3, as its refuter corrected it): the ledger entry's `where:` line is
// the output of the notes' ledger-where.sh, derived from the PR's whole diff against its merge base with main, and no test held it (round 6's
// fifteenth commit said a plan pin did; none did, and a seventh matrix fixture added with the line untouched left this module green). The file
// list below is `git diff --name-only 01434a45b..HEAD` at the head, recorded verbatim in git's order, the shape of
// tools/upstream-ledger-figure-gate-before-adoption.test.mjs: this module reads no git (a pin that shelled out would have to skip where git or the
// base is absent, and report green having checked nothing), so a file the PR adds later is caught by re-running the command, or ledger-where.sh,
// which prints this same block beside the line, and re-recording both in the same commit; a file re-recorded here and not named in the line reds
// by name, and the self-check holds the block to the command's shape, which a hand edit tends to break. 01434a45b is the merge base with main.
const DIFF_OUTPUT = `
docs/batching.md
docs/guide.md
docs/install.md
hooks/README.md
hooks/romp-track-bash-guard.mjs
plans/file-review.md
tests/test_batch_tool.py
tests/test_guide_files_bash_guard.py
tools/file-review-plan-bash-guard-review.test.mjs
tools/file-review-plan-bash-guard.test.mjs
tools/romp-track-bash-guard-brace-matrix.json
tools/romp-track-bash-guard-census.mjs
tools/romp-track-bash-guard-construct-matrix.json
tools/romp-track-bash-guard-corpus.json
tools/romp-track-bash-guard-heredoc-body-matrix.json
tools/romp-track-bash-guard-param-word-matrix.json
tools/romp-track-bash-guard-piped-script-matrix.json
tools/romp-track-bash-guard-shapes.test.mjs
tools/romp-track-bash-guard-stdin-script-matrix.json
tools/romp-track-bash-guard.test.mjs
tools/vendor-drift.test.mjs
tools/vendor-patches.test.mjs
upstream/2026-09-18-track-guard-non-literal-targets.md
vendor/track-changents/README.md
vendor/track-changents/patches/0009-skill-non-literal-target-refused.patch
vendor/track-changents/skill/SKILL.md
`;
const DIFF_FILES = DIFF_OUTPUT.trim().split('\n');
test("round 7, thirty-fifth commit: every file of the PR's diff against its merge base, recorded verbatim, is named in the ledger entry's where: line, which names nothing else, and the record keeps the command's shape", () => {
  const entry = read('upstream', '2026-09-18-track-guard-non-literal-targets.md');
  const whereLine = entry.split('\n').find((l) => l.startsWith('where: '));
  assert.ok(whereLine, 'the entry has a where: line');
  // an entry is a path, then optionally the definitions the hunks name in parentheses (ledger-where.sh's form); entries are joined by '; '
  const named = whereLine.slice('where: '.length).split('; ').map((e) => e.replace(/ \([^()]*\)$/, ''));
  const unnamed = DIFF_FILES.filter((f) => !named.includes(f));
  assert.deepEqual(unnamed, [], 'every recorded path is named in the where: line (re-run ledger-where.sh: it prints the line and this block together)');
  assert.deepEqual(named.filter((f) => !DIFF_FILES.includes(f)), [], 'and the line names no file the diff lacks');
  assert.deepEqual(DIFF_FILES.filter((f) => !fs.existsSync(path.join(REPO, f))), [], 'every recorded file exists in the tree (the PR deletes none)');
  // the command's shape: byte-sorted as git prints, one plain path per line, no duplicate and no blank
  assert.ok(DIFF_FILES.length > 0, 'the record is not empty');
  assert.deepEqual(DIFF_FILES, [...DIFF_FILES].sort(), 'byte-sorted, as `git diff --name-only` prints (a hand-appended path lands out of order)');
  assert.equal(new Set(DIFF_FILES).size, DIFF_FILES.length, 'no path twice');
  assert.ok(DIFF_FILES.every((f) => /^[A-Za-z0-9._\/-]+$/.test(f)), 'one plain path per line, no blank and no stray text');
  for (const f of ['hooks/romp-track-bash-guard.mjs', 'tools/file-review-plan-bash-guard.test.mjs', 'upstream/2026-09-18-track-guard-non-literal-targets.md']) assert.ok(DIFF_FILES.includes(f), `the record holds ${f}`);
});
