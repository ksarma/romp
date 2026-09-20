---
title: The pre-push hook fails closed on a read whose failure is indistinguishable from an empty result
status: candidate
where: .githooks/pre-push: unscanned() and its callers; the tag fields (tag_unread, f3); the tip content grep, its symlink listing, each link target and the tag TYPE read (type_unread, f4); each new commit added lines (added_lines), addresses (stamped_addresses) and message (f5); tests/pre-push-hook.bats, tests/pre-push-identity.bats and tests/pre-push-message.bats, the git_refusing shim cases
added: 2026-09-20
pr:
tier: fix
offered:
closed:
---
The class, found by execution on the text upstream landed from the fork's offer 1847: a git read whose output the hook greps fails (a non-zero status, or an error line) and the hook reads the failure as an empty result, so a part-scanned push passes as a clean one. The fork's fix routes every such read through one helper (unscanned: one stderr line naming the ref or the commit and the read, failed_scan=1, the push refused on that flag alone; failed_creds gates the gitleaks advice) or lets the read's own status end the hook; an ABSENT value (an empty target, a tag with no tagger or message, a lightweight tag, a blob or tree tag, a gitlink, a binary file, a commit whose diff or message is empty) still reads as empty and passes, and every hit path prints the same text and line numbers as before (the round f4 audit's contract run: byte-identical stderr on both texts). Seven roads were found one at a time (round f3 the tag fields; round f4 the tip's content grep, its symlink listing, each link's target and the tag TYPE read; round f5 the per-commit added lines, addresses and message); the population was then DERIVED over the whole fixed text with the command below, which found an eighth road, open, in the credential scan. One offer for the class with the harness; the eighth road goes to a follow-up offer. It waits on the user's decision whether to report it upstream.

The property in one sentence: no read the hook makes of the pushed objects can fail in a way the hook cannot tell from an empty result, because each read's status is captured before its output is judged and a non-zero status refuses the push as unscanned.

The derivation. Run from the repo root; it lists every statement of the hook that names an external read (git, cat, command -v, the gitleaks binary, a helper wrapping one), a judge grep, a file test or the denylist redirect, joined across backslash continuations with comments stripped, and tags each with its syntactic shape (a suppressed, b a substitution with no arm, c the left side of a pipe, d inside a test, s a status read or a refusing arm, R a read, j a judge grep, f a file test, i the input redirect, p report text). The tags are a first cut, not the verdict: a helper's pipeline shows c at the helper and its closure shows s at the caller.

```bash
awk '
{ line = $0
  if (buf != "") line = buf " " line
  if (line ~ /\\$/) { sub(/[ \t]*\\$/, "", line); buf = line; if (!start) start = NR; next }
  n = start ? start : NR; start = 0; buf = ""
  code = line; sub(/^[ \t]*#.*$/, "", code); sub(/[ \t]#[ \t].*$/, "", code)
  reads = "(^|[^A-Za-z0-9_$.-])(git|cat|command -v|\"\\$gl\"|rev_range|added_lines|chosen_emails|is_chosen|stamped_addresses|tag_field|tag_message)([ \t)]|$)"
  judge = "(^|[^A-Za-z0-9_$.-])grep([ \t)]|$)"
  if (code !~ reads && code !~ judge && code !~ /\[ (! )?-[fx] / && code !~ /done < /) next
  shape = ""
  if (code ~ /2>\/dev\/null|>\/dev\/null 2>&1|\|\| *true|\|\| *:( |$)|\|\| *\{ *[a-z_]+=""/) shape = shape "a:suppressed "
  if (code ~ /=\$\(|="\$\(/ && code !~ /\|\|/ && code !~ /^[ \t]*(if|while|elif) /) shape = shape "b:subst-no-arm "
  if (code ~ /(git|cat|added_lines|stamped_addresses|tag_field|tag_message|chosen_emails)[^|]*\| *(grep|awk|while|cut|sed|sort|tr)/) shape = shape "c:pipe-left "
  if (code ~ /^[ \t]*(if|while|elif|case) / || code ~ /\[ "\$\(/ || code ~ /\) *&& *\[/) shape = shape "d:test "
  if (code ~ /\|\| *rc=\$\?|\|\| *return \$\?|\|\| *\{ *[a-z_]*=?"?"?;? *(unscanned|tag_unread|type_unread)|\|\| *\{ *$/) shape = shape "s:status-read "
  if (code ~ reads) shape = shape "R "
  if (code ~ judge && code !~ /git grep/) shape = shape "j "
  if (code ~ /\[ (! )?-[fx] /) shape = shape "f:file-test "
  if (code ~ /done < /) shape = shape "i:input-redirect "
  if (code ~ /^[ \t]*(echo|unscanned) / || code ~ /^[ \t]*\[ "\$rc" -eq 0 \] \|\| unscanned/) shape = shape "p:report-text "
  gsub(/^[ \t]+/, "", line)
  printf "%d\t%s\t%s\n", n, shape, line }
' .githooks/pre-push
```

For an older text replace the file argument with `<(git show <sha>:.githooks/pre-push)`. Its result on the fold's three texts: the fold 3 merge commit 51c8741d6 (before round f3) 39 statements, 33 of them reads or tests after the report-text rows; the pre-f5 head 0e18a885b 46 statements, 39 reads or tests; the fixed text 51 statements, 41 reads or tests. The count RISES across the fold because each fix splits one piped statement into a captured read plus a status test; the number that falls is the unclosed shapes (an R row tagged a, b, c or d without s): 24 on the merge, 18 on the head, 14 on the fixed text, and each of the 14 is classified below as fail-closed by construction, safe by assessment or the documented design. The vocabulary is complete by a cross-check: every external command name in the hook's code, on all three texts, is one of git, cat, command, the gitleaks binary, grep, awk, sed, cut, sort, tr, read, printf, echo; awk, sed, cut, sort and tr occur only right of a pipe or after a hit; read reads herestrings except at the denylist redirect; printf and echo write.

The population on the fixed text, one line per statement the command lists, with the line number there and the disposition (fixed in f3, f4 or f5 with the mechanism; fail-closed by construction; safe by assessment; the documented design; judge, the residual class below; OPEN, for the follow-up):

- 110, `refs="$(cat)"`, the ref list git hands the hook on stdin: fail-closed by construction (errexit: a failed cat ends the hook non-zero; an empty list is absent, git ran the hook with nothing to push).
- 164, added_lines, the parent count `git rev-list --parents -n 1 | awk ... || return $?`: FIXED in f5 (pipefail carries rev-list's status through awk; `|| return` makes it the function's; the caller at 363 reads rc and reports the ADDED LINES unscanned).
- 165, added_lines, `git diff-tree -p -r -M -c --root | awk`: FIXED in f5 (the pipeline's status is the function's return under pipefail; the caller at 363 reads it; verified by execution with the real git, the added file's blob gone from the store: `git diff-tree exited 128`, refused).
- 180, chosen_emails, `git config --get-all user.email 2>/dev/null || true`: safe by assessment (a failed read, or the unset key's exit 1, contributes no chosen address, so every stamped address is checked: the failure scans MORE).
- 186, is_chosen, `printf | grep -qixF -e`: safe by assessment (grep over two in-memory strings; a grep that cannot run reads as not chosen and the address is checked: MORE); also a judge site.
- 206, stamped_addresses, `stamped=$(git log -1 --no-show-signature --format='authored%x09%ae%ncommitted%x09%ce') || return $?`: FIXED in f5 (the log is captured before the loop so the function's status is the log's; at the head the log was piped into the loop through a process substitution, whose status reaches nothing).
- 209, the is_chosen call in stamped_addresses: safe by assessment (as 186).
- 219, tag_field, `git cat-file -p | awk`: FIXED in f3 (pipefail makes cat-file's failure the function's status; the callers at 414 and 433 read it in a `|| { ...; tag_unread }` arm).
- 224, tag_message, `git cat-file -p | awk`: FIXED in f3 (as 219; the caller at 425).
- 263, `[ -f "$strings_file" ] || return 0`: the documented design (an absent denylist is the contributor default the header describes: absent, not unreadable; a denylist under another XDG_CONFIG_HOME or behind a broken symlink also reads as absent, the design's boundary).
- 272, `done < "$strings_file"`, the denylist read: fail-closed by construction (a redirect that fails on an existing unreadable file fails the compound command and errexit ends the hook with 1; verified on bash 5.2.21 with a mode-000 file; an EMPTY denylist returns 0 at 273, absent).
- 274, `chosen="$(chosen_emails)"`: safe by assessment (the function ends in printf and exits 0; its only read is 180).
- 292, the tip's content, `out=$(git grep ... 2>&1) || rc=$?`: FIXED in f4 (status and stderr read apart from the hits; a status above 1 or any non-hit line refuses as unscanned; verified: `git grep exited 1` with unable-to-read lines, refused).
- 293, the hits filter `printf "$out" | grep -E ... || true`: judge (the `|| true` covers no-match and a grep that cannot run alike; not a read of the store).
- 294, the errs filter `... | grep -Ev ... | grep . || true`: judge (as 293; a failed `grep .` empties errs and the any-other-line-is-an-error arm is lost).
- 323, the tip's symlink listing `listing=$(git ls-tree -r ...) || {`: FIXED in f4 (the arm reports SYMLINKS unscanned unless the object peels to a blob; whatever was listed is still read).
- 324, the peel type inside that arm, `[ "$(git cat-file -t ^{} || true)" = blob ]`: fail-closed by construction, part of f4 (a failed type read is not-blob and falls to the refusing arm).
- 330, `if links=$(printf "$listing" | grep '^120000 ')`: judge (grep over the captured listing; a grep that cannot run reads as no links).
- 337, each link's target `target=$(git cat-file -p "$blob") || { target=""; unscanned }`: FIXED in f4 (the real-fault shape, a loose blob removed from the store, is pinned by the bats case that once asserted the fail-open).
- 339, `if printf "$target" | grep -qi -F`: judge.
- 360, the commit list `revs=$(git rev-list <range> 2>/dev/null || git rev-list "$local_sha")`: fail-closed by construction (the first read's failure falls to everything the tip reaches, MORE; the fallback's failure ends the hook by errexit, verified exit 1 and exit 128 with a commit object missing; `git rev-list` over a blob or tree exits 0 with no output, so blob and tree tags give an empty loop: absent). Not routed through unscanned: the refusal prints no hook line and sets no failed_scan; a follow-up may give it the `if ! revs=$(...)` shape with a line.
- 363, `out=$(added_lines "$rev") || rc=$?`: FIXED in f5 (364 reports the ADDED LINES of the commit unscanned with the status; 365 still judges whatever the diff printed, so a hit ahead of the failure is still named).
- 365, the added-lines judge `printf "$out" | grep | cut | sort`: judge.
- 376, `addrs=$(stamped_addresses ...) || rc=$?`: FIXED in f5 (377 reports the ADDRESSES unscanned; the loop reads a herestring so status and counter stay in this shell).
- 380, the address judge `printf "${email##*@}" | grep -qi -F`: judge.
- 391, `msg=$(git log -1 --no-show-signature --format=%B) || rc=$?`: FIXED in f5 (392 reports the MESSAGE unscanned; the numbering from the subject is unchanged, `on line 5 (line 1 is the subject)` verified byte for byte).
- 393, the message judge: judge.
- 412, the pushed object's type `kind="$(git cat-file -t)" || { kind=""; type_unread }`: FIXED in f4 (before it, `|| true` in the loop test turned every status into "not a tag" and the tag was never peeled or scanned).
- 414, the tagger `tag_field ... || { tagger=""; tag_unread TAGGER }`: FIXED in f3.
- 417, the tag address judge (is_chosen and grep -qi): judge (a failed is_chosen reads as not chosen, MORE).
- 425, the tag message `tag_message ... || { msg=""; tag_unread MESSAGE }`: FIXED in f3.
- 426, the tag message judge: judge.
- 433, the object field `tag_field ... object || { inner=""; tag_unread OBJECT "which ends the peel here" }`: FIXED in f3 (435 breaks on empty after the report).
- 436, the type after a peel: FIXED in f4.
- 471, `command -v gitleaks || true`: the documented design (a builtin that fails only when nothing is found; absence prints the three-line notice and stands down, the loud no-gitleaks road).
- 472, `[ -z "$gl" ] || [ ! -x "$gl" ]`: the documented design (as 471).
- 482, `root="$(git rev-parse --show-toplevel)"`: fail-closed by construction (errexit; a plain assignment in scan_credentials, called at top level).
- 488, `[ -f "$root/.gitleaks.toml" ]`: safe by assessment (an absent config scans under the default rules, documented; an unreadable one makes gitleaks exit 1, neither 0 nor 2, so failed_creds refuses).
- 498, `range="$(rev_range ...)"`: not a read (printf over its arguments).
- 500, `git rev-list $range >/dev/null 2>&1 || range="$local_sha"`: safe by assessment for what it probes (an unresolvable range falls to the tip's whole history, MORE); the fallback is NOT verified, unlike 360's: a tip whose walk fails hands gitleaks a range its git cannot read, which is 515's open road.
- 515, the credential scan `"$gl" git ... --log-opts="$range ..." || rc=$?`: OPEN, the eighth road. The hook reads gitleaks's status faithfully (0 clean, 2 a finding, anything else failed_scan and failed_creds), but gitleaks 8.30.1 reads its own `git log -p` failure as an empty scan: it logs `ERR [git] fatal: unable to read <blob>` (or `bad object`), `0 commits scanned`, `no leaks found`, and exits 0. The header names this property for an UNRESOLVABLE range and 500 probes resolvability; readability is not probed. By execution: the hook exited 0 on a clone with no denylist, and a REAL push through the installed fixed hook published a branch whose added file's blob was gone from the store, gitleaks's ERR line the only sign; on a clone WITH a denylist the identifier arm's ADDED LINES read (f5) refused the same push. So the road is open on every clone without a denylist (the contributor default) and masked, not closed, on the maintainer's. `gitleaks git --help` offers no flag that fails on a git error; no git on PATH does fail (exit 1, refused). Fix shapes for the follow-up: probe readability before the scan the way 500 probes resolvability (`git log -p --diff-merges=first-parent $range >/dev/null || unscanned`) and verify the fallback; or refuse on gitleaks's `ERR [git]` stderr; or compare its `N commits scanned` with `git rev-list --count`. The refusal belongs under failed_scan and failed_creds.
- 296, 364, 377, 392, 449, 450, 451, 454, 457, 543: report text that mentions git (unscanned callers and echo lines); not reads, set aside from the 41.

The tally on the fixed text: 17 fixed (f3: 219, 224, 414, 425, 433; f4: 292, 323, 324, 337, 412, 436; f5: 164, 165, 206, 363, 376, 391), 4 fail-closed by construction (110, 272, 360, 482), 9 safe by assessment or the documented design (180, 186, 209, 263, 274, 471, 472, 488, 500), 1 not a read (498), 9 judge, 1 OPEN (515).

The derivation found an eighth road, so the METHOD is the deliverable, not the count of seven: the population is what the command lists PLUS execution at every site the command tags as a status read of an external binary, since a read inside that binary (gitleaks's own git log) is visible only as the binary's invocation and only execution showed that its status does not carry the read. The eighth road goes to a follow-up offer of its own (the credential scan reads gitleaks's git failure as an empty scan; the entry for it is to be filed under upstream/ when this one is offered), not into this offer. The method's limits, for the next reader: the command sees statements, not reach (errexit closes a substitution only outside a condition context; the b tag excludes if and while heads, so each b row is judged by context); a helper's pipeline shows unclosed at the helper and closed at its caller; the tags are the first cut and the disposition column above is the verdict.

A residual of a separate class, recorded here so the follow-up can take it: the nine JUDGE sites (293, 294, 330, 339, 365, 380, 393, 417, 426) run grep over captured text and branch the same way on no-match (status 1) and on a grep that cannot run (status 2, or 127 off PATH); `|| true` at 293 and 294 swallows both, and elsewhere pipefail carries grep's failure to an `if` that reads it as no hit. By execution: a grep shim exiting 2 ahead of the real one, a leaking tip, the denylist armed: ten `grep: simulated failure` lines and hook exit 0, where the real-grep control refused. It is not a read of the store (git's own `git grep` at 292 is unaffected; the hits are read, then dropped by the failed filter), and its realism is low (GNU and BSD grep exit 2 only when they cannot run or are killed). It is not counted among the reads. The cheap fix either way: a startup self-test (`printf x | grep -q x || unscanned "grep cannot run"`) closes all nine, or each site reads grep's status and refuses on 2 or above.

The harness, in the upfold notes under fold3/: tagprobe.md (the round f3 probe: a scratch HOME carrying a synthetic denylist, a bare remote, the hook fed its stdin line directly and through a real push with GIT_EXEC_PATH pointing at a git shim that fails ONE subcommand shape and execs the real git otherwise); the round f4 probe logs agents/probe-grep244.md, probe-lstree259.md, probe-revlist274.md and probe-catfilet311.md with the fixer log agents/fix-f4-prepush.md and the audit agents/audit-f4.md (the 14-shape contract run); the round f5 probe agents/probe-seventh.md, the fixer log agents/fix-f5-prepush.md and the derivation agents/derive-population.md (the command's output on the three texts, the classified table, the eighth-road runs). In the repo, the bats files carry a generic run-time shim, `git_refusing <bash test over "$@"> <exit> <stderr line>`, with thin wrappers per read (fail_git_grep, fail_ls_tree, fail_cat_file_p, fail_diff_tree in tests/pre-push-hook.bats; fail_cat_file_t, fail_log_addresses in tests/pre-push-identity.bats; fail_log_message in tests/pre-push-message.bats); each fixed read has a case that fails on the text before its fix and a control that an absent value still passes.

The upstream shape: one follow-up offer covering the class, the fixed hook with its seven closed roads, the three bats files and the derivation command in the PR body so the reviewer can re-run it; the eighth road as a second offer stacked on it.
