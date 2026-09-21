#!/usr/bin/env python3
"""THE WRITERS CENSUS: every call that CREATES an entry under the state root, derived from the code, pinned to the
owner-only creators (kernel/state_root_mode.py, part 4).

Round 4d of the state-root review (2026-09-21) found that the kernel, the bus and the session host made their entries
under the root at the process umask: under a umask that leaves an other write bit, or a group write bit under a shared
primary group, the guarded readers (tests/test_state_root_readers.py) quarantine the process's OWN fresh entries at the
next read. romp-manager's ruling: "Entries born owner-only BY CODE. Derive every writer that creates an entry under the
root (a bare mkdir, a write_text, an open for write, a tempfile, anything) and make each set its mode explicitly, rather
than fixing the four you noticed." This module is that derivation and that pin; tests/test_state_root_mode.py's
EntriesAreBornOwnerOnlyUnderAPermissiveUmask is the behavioural pin (the creation roads under umask 0022 and 0000 in
child processes).

WHAT IT DOES. The same AST census as the readers': the eleven modules (test_state_root_readers.MODULES), the same seeds,
the same derivation of every expression that is a path under the root (module_facts, reused from the readers module's
per-process cache, so the derivation of kernel/kernel.py's 79k lines runs once for both censuses in one process). Which
census PAYS that derivation is a property of collection order, not of the design: under pytest's alphabetical collection
the readers census runs first and this one finds a warm cache (about 0.4 s for this module on a box, against about 7.8 s
cold); under a -k that deselects the readers' census, under an xdist distribution that puts the two files on different
workers or this one first, or after a rename, this census derives cold, and test_the_census_reuses_the_readers_derivation
asserts the SHARING, not the warmth (it holds whichever census ran first). Over those expressions it lists every CREATION: Path.mkdir, os.mkdir, os.makedirs; Path.write_text, Path.write_bytes,
Path.touch; open, Path.open, io.open and gzip.open in a write or append mode (a mode the census cannot read is listed
as "open:?"); os.open with O_CREAT; tempfile.* with its directory under the root; shutil.copy, copy2, copyfile, copytree
and move onto a path under the root; os.rename, os.replace, os.link, os.symlink, Path.rename, Path.replace,
Path.hardlink_to and Path.symlink_to whose DESTINATION is under the root. A json.dump onto a file object is not a
creation of its own: the open that made the object is the one listed.

WHAT IT ASSERTS. Every creation is born owner-only BY CODE, in one of four ways, or sits on ALLOWLIST with a one-line
reason. (1) THE CREATORS: a call of the shared module's make_dir, write_text, write_bytes, open_private or touch (the
receiver is the module: `srm`, `_srm`, `jd.srm`), each of which makes the entry 0700 or 0600 before its first byte
under any umask and tightens an existing one of ours. (2) THE INODE: a rename, replace or hard link whose SOURCE is
itself a path under the root carries its source's mode (the mode travels with the inode; the source's own creation is
censused where it happens), so an atomic publish through a temp born by a creator is owner-only. (3) THE LIBRARY:
tempfile.mkstemp and NamedTemporaryFile make their file 0600, mkdtemp and TemporaryDirectory their directory 0700,
whatever the umask. (4) THE ALLOWLIST: a site that sets its mode by code AT THAT SITE (an os.open with O_CREAT and a
0600 mode, a mkdir with mode=0o700 followed by its own tightening), each with its reason; a stale entry reds. A new bare
creator anywhere in the eleven modules reds this module (test_the_census_reds_on_a_planted_bare_creator proves the pin
can red by planting six shapes in a copy of the kernel and shows their owner-only twins come out clean). A copy onto the
root (shutil.copy*) and a symlink under the root are never owner-only by construction (a copy carries the umask's or the
source's mode; a symlink is what the readers quarantine) and are listed unguarded until allowlisted.

HOW TO RE-RUN IT BY HAND. `python3 tests/test_state_root_writers.py --list` prints the population (file:line, function,
kind, target, how it is owner-only) and exits 1 when an unaccounted creator exists. plans/state-root-mode.md records
the method beside the readers'.

WHAT IT DOES NOT SEE, AND WHAT STANDS FOR IT THERE. What the readers census does not see (a path through a name the
derivation cannot follow), and a creator called with a path outside the root (not the root's). Four shapes are named
here because they exist in the tree (round 4f's review). (a) A creation by a RELATIVE NAME under a directory descriptor:
kernel/host_transport.py makes hosts/<sid>/spawn.json and host.stderr through `os.open(name, ..., 0o600, dir_fd=dirs.dir)`
with an fchmod on the descriptor, so this census lists that module at 0 creations; those roads are pinned by
tests/test_hosts_path_census.py (PR 814's descriptor census). (b) A path derived from a process ARGUMENT: the session
host's main() derives its root and its host.log from `Path(argv[0])`, a seed of the readers module, so its
state-root-refused row is listed here (through open_private). (c) An entry a CHILD PROCESS makes under the root: the
codex judge's -o reply (kernel/judge.py) is created by the vendor's CLI at the child's umask, which the site sets to 077
(`subprocess.run(..., umask=0o077)`), and pip's runtime tree under codex-runtime/ keeps pip's modes (the plan's residual);
no AST census sees a creation another program performs. (d) romp's processes OUTSIDE the eleven modules: the CLI
(bin/romp: judge-engine, default-backend, debug-mode.json, the down-by-romp marker's temp, restart-audit.jsonl), the
manager (bin/romp-manager: restart-audit.jsonl) and the shell the kernel runs on a far host over ssh (kernel/kernel.py's
three command strings: restart-audit.jsonl, kernel.log and update.log on the far root) each write a few entries a kernel
reads back through its guarded readers; no derivation runs over bash or JavaScript, so each site is held to set its mode
by code where it writes (`umask 077` on the writing command or a subshell around it; appendFileSync's `mode: 0o600`) by
test_the_writers_outside_the_eleven_modules_set_their_mode_at_the_site, a text pin with its own red checks. Two Python
tools the CLI delegates to write under the root as well, stdlib-only and outside the eleven modules (cli/spend_rebuild.py: spend.json and a temp;
cli/spend_repair.py: spend.json, turns.jsonl, spend-repair.jsonl and temps; the .bak copies each makes carry their
source's mode), and the kernel reads spend.json back through a guarded reader: each sets `os.umask(0o077)` as the FIRST statement
of main, so everything it makes is born owner-only, and the same test holds that by AST (the review of round 4f's
preparation for round 3, 2026-09-21). THE REACH of the bin/romp rule is narrower than the census's over Python, and is
stated rather than assumed: ONE LEVEL of binding by assignment (an underscore-led name assigned from `$(_romp_state_dir)`
or the XDG expression), REDIRECTS ONLY for the umask judgment, underscore-led names only (ROMP_NAMES_DIR is the one root
binding the rule does not match; its one use is a read). What the rule does not judge is pinned BY EQUALITY instead, by
test_the_clis_non_redirect_creations_are_the_roots_own_mkdirs_and_the_markers_move, in the shapes its regexes read (a
command word at a command position: a line start, `;`, `&&`, `|`, `(`, `)`, `{`, `!`, then/do/else/if/elif/while/until,
exec/command/env/nohup/time/nice, with assignment prefixes scanned; its arguments to the next unquoted separator, a
backslash-continued command read as one line; a root
spelling in `$name`, `${name}` or expression form, by argument or by environment prefix): no name is bound from a
root-bound name by assignment; the functions handed a root path are exactly two (_romp_down_release removes the marker,
_romp_split_record reads a names record) and their bodies carry no redirect or creating verb on a positional parameter;
the creations under a root-bound name that are not redirects (mkdir, cp, mv, tee, touch, install, ln, truncate, dd,
rsync) are exactly five `mkdir -p` of the root itself, each inside a `( umask 077; ...)` group so the root is BORN 0700
under any umask (the gate's creation exemption is for a root EMPTY at its read, and each of these commands fills the root
in the same breath: judge-engine, debug-mode.json, the marker, the audit row; until this review the five made the root at
the umask's mode, so a first `romp engine codex` under a permissive umask before any boot would have met the import
refusal at that boot), and the down-by-romp marker's `mv` of a temp born under umask 077 (the inode carries its mode);
the programs handed a root path (CLI_PROGRAMS) are exactly three, two readers by argument (the client-diag histogram,
the down-marker time) and the down-refusal helper, handed the token path by environment and formatting it into its
remedy sentence, never opening it (that a program handed a path only reads is what no text census can decide, so the
three were read by hand on 2026-09-21 and the LIST is what the pin holds); the four inline uses of the root expression
outside a binding carry no redirect and no creating verb; and every logical line that carries both a root spelling and a
creating verb, program or extra word (chmod among them), whatever its position, is one of a listed sixteen (the coarse
backstop for a shape the finer regexes do not read). A new site of any of those kinds reds. Beyond these regexes: a
parameter re-bound to a local before a write inside a function, a creating program outside the word lists, and a helper
called at module level in the Python tools. The root's own creation elsewhere (the manager's
mkdirSync, a harness's makedirs) is a creation default the gates exempt and tighten.
"""
import ast
import collections
import os
import re
import sys
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
if __package__:
    from . import test_state_root_readers as R   # under pytest tests/ is a package: THE SAME module object as the readers' run,
else:                                             # so its _PARSED and _FACTS caches are this census's too (one derivation per process)
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import test_state_root_readers as R           # `python3 tests/test_state_root_writers.py --list`: a script, the module by name

ROOT = R.ROOT
MODULES = R.MODULES

CREATORS = {"make_dir": "dir", "write_text": "file", "write_bytes": "file", "open_private": "file", "touch": "file"}
RENAME_FUNCS = {"os.rename", "os.replace", "os.link", "shutil.move"}     # (source, destination): owner-only when the source is
COPY_FUNCS = {"shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree"}   # a new inode at the umask's or the source's mode
TEMPFILE_FUNCS = {"tempfile.mkstemp", "tempfile.mkdtemp", "tempfile.NamedTemporaryFile", "tempfile.TemporaryDirectory",
                  "tempfile.TemporaryFile", "tempfile.SpooledTemporaryFile"}   # each born 0600 or 0700 by the library
CREATE_FLAG = "O_CREAT"

# THE WRITERS OUTSIDE THE ELEVEN MODULES (round 4f's review): romp's CLI, its manager and the shell the kernel runs on a far
# host each create a few entries under a state root that a kernel reads back through its guarded readers. No derivation
# runs over bash or JavaScript; the helpers below hold each site to set its mode by code where it writes.
CLI_ROOT_BINDING = re.compile(r'^\s*(?:local\s+)?(_[A-Za-z_]+)="?(?:\$\(_romp_state_dir\)|\$\{ROMP_STATE_DIR:-\$\{XDG_STATE_HOME:-\$HOME/\.local/state\}/romp\})')
REMOTE_APPEND = re.compile(r'>>?"\$LOGDIR/([^"]+)"')
# THE CLI'S NON-REDIRECT CREATIONS (romp-manager's round-3 preparation, 2026-09-21, widened by its adversarial review the same
# day): what cli_redirects does not judge, pinned by equality. A binding of ANY name to the root expression (CLI_ROOT_BINDING
# takes the underscore-led ones), the root expression itself, the verbs that create an entry by a path argument, the programs
# a path may be handed to, a command position and its arguments, and the lists as of 2026-09-21.
CLI_ANY_ROOT_BINDING = re.compile(r'^\s*(?:local\s+)?([A-Za-z_][A-Za-z0-9_]*)="?(?:\$\(_romp_state_dir\)|\$\{ROMP_STATE_DIR:-\$\{XDG_STATE_HOME:-\$HOME/\.local/state\}/romp\})(.*)$')
CLI_ROOT_EXPR = r'\$\(_romp_state_dir\)|\$\{ROMP_STATE_DIR:-\$\{XDG_STATE_HOME:-\$HOME/\.local/state\}/romp\}'
CLI_CREATING_VERBS = ("mkdir", "cp", "mv", "tee", "touch", "install", "ln", "truncate", "dd", "rsync")
CLI_PROGRAMS = ("python3", "python", "node", "jq", "bash", "sh")
CLI_POSITION = r'(?:^|[;&|(){]|!|\b(?:then|do|else|if|elif|while|until|exec|command|env|nohup|time|nice)\b)'
CLI_ASSIGNS = r'((?:[A-Za-z_][A-Za-z0-9_]*=(?:"[^"]*"|\'[^\']*\'|[^\s;&|]*)\s+)*)'   # an environment prefix, kept: a path may travel in it
CLI_ARGS = r'((?:\$\([^)]*\)|\'[^\']*\'|"[^"]*"|[^;&|()\'"#])*)'                      # to the next unquoted separator, group end or comment
CLI_FUNC_DEF = re.compile(r'^(\s*)(?:function\s+)?(_[a-z0-9_]+)\s*(?:\(\))?\s*\{', re.M)   # at any indentation, either form
CLI_BACKSTOP_EXTRAS = ("chmod", "mktemp", "tar", "unzip", "git", "sed", "curl", "wget", "sqlite3")   # words the backstop reads beyond the
                                                                                                     # verbs and programs: a mode change or an
                                                                                                     # archive/tool that can create by a path
CLI_NON_REDIRECT_CREATIONS = [                       # sorted; each admitted by cli_admitted
    'mkdir -p "$(dirname "$_dbg_conf")"',             # romp debug on: debug-mode.json's parent, the root itself, born 0700
    'mkdir -p "$_dn_state"',                          # romp down: the root itself, born 0700
    'mkdir -p "$_eng_state"',                         # romp engine claude: the root itself, born 0700
    'mkdir -p "$_eng_state"',                         # romp engine codex: the root itself, born 0700
    'mkdir -p "$_ra_dir"',                            # the restart audit: the root itself, born 0700
    'mv -f "$_dn_state/down-by-romp.tmp" "$_dn_state/down-by-romp"',   # the marker's publish: the temp was born under umask 077
]
CLI_PROGRAMS_HANDED_A_ROOT_PATH = [                  # sorted; what each does with the path was read by hand on 2026-09-21
    '_dn_mref="$(DN_OUT="$_dn_mout" DN_TOK="$(_romp_state_dir)/serve-token" DN_ENV="${ROMP_SERVE_TOKEN:+1}" python3 -',
                                                     # romp down's refusal remedy: the token PATH as a string in a sentence, never opened
    'python3 - "$_cfile" "$_cmin" "$_cjson"',         # romp perf client: reads client-diag.jsonl and its .1
    'python3 - "$_st_marker" 2>/dev/null',            # romp status: reads the marker's time
]
CLI_FUNCTIONS_HANDED_A_ROOT_PATH = ["_romp_down_release", "_romp_split_record"]   # rm -f of the marker; a read of a names record
CLI_INLINE_ROOT_USES = 4                             # the root expression outside a binding: two `cat` reads, a hint string, the token path
                                                     # in the down-refusal helper's environment (a string in its remedy); none a redirect
                                                     # onto it or a creating verb
CLI_COOCCURRENCES = [                                # every line carrying a root spelling AND a creating verb or program word, sorted
    '( umask 077; DN_CMD="$_dn_cmd" python3 -c \'import json,os,time; print(json.dumps({"t": int(time.time()), "cmd": os.environ["DN_CMD"]}))\' > "$_dn_state/down-by-romp.tmp" ) && mv -f "$_dn_state/down-by-romp.tmp" "$_dn_state/down-by-romp"',
    '( umask 077; mkdir -p "$(dirname "$_dbg_conf")" )',
    '( umask 077; mkdir -p "$_dn_state" )',
    '( umask 077; mkdir -p "$_eng_state" )',
    '( umask 077; mkdir -p "$_eng_state" )',
    '( umask 077; mkdir -p "$_ra_dir" )',
    '( umask 077; printf \'claude\\n\' > "$_eng_state/judge-engine" && chmod 600 "$_eng_state/judge-engine" )',
    '( umask 077; printf \'codex\\n\' > "$_eng_state/default-backend" && chmod 600 "$_eng_state/default-backend" )',
    '( umask 077; printf \'codex\\n\' > "$_eng_state/judge-engine" && chmod 600 "$_eng_state/judge-engine" )',
    '( umask 077; printf \'sdk\\n\' > "$_eng_state/default-backend" && chmod 600 "$_eng_state/default-backend" )',
    '( umask 077; printf \'{"on": true}\\n\' > "$_dbg_conf" && chmod 600 "$_dbg_conf" )',
    '[ -z "$_cx" ] && _cx="$(ls -d "$_eng_state"/codexvenv/lib/python3.*/site-packages/codex_cli_bin/bin/codex 2>/dev/null | head -n1 || true)"',
    '_dn_mref="$(DN_OUT="$_dn_mout" DN_TOK="$(_romp_state_dir)/serve-token" DN_ENV="${ROMP_SERVE_TOKEN:+1}" python3 - <<\'PYEOF\'',
    '_st_when="$(python3 - "$_st_marker" 2>/dev/null <<\'PYEOF\' || true',
    'python3 - "$_cfile" "$_cmin" "$_cjson" <<\'PY\'',
    'umask 077; RA_ACTION="${1:-}" RA_WHEN="${2:-}" RA_REASON="${3:-}" RA_SHA="$_ra_sha" RA_PPID="$PPID" RA_PARENT="$(ps -o command= -p "$PPID" 2>/dev/null | head -1)" RA_TTY="$(tty 2>/dev/null || true)" RA_SID="$_ra_sid" RA_NAME="$_ra_name" python3 - >> "$_ra_dir/restart-audit.jsonl" <<\'PYEOF\'',
]
CLI_UMASK_TOOLS = ("cli/spend_rebuild.py", "cli/spend_repair.py")   # os.umask(0o077) is the first statement of each main()
MANAGER_WRITE = re.compile(r"(?:appendFileSync|writeFileSync)\((?:[^;]|\n)*?\);")


def cli_redirects(text):
    """Every `>` or `>>` redirect in a bash text onto a path under a name the text binds to the state root (a name assigned
    from `$(_romp_state_dir)` or the XDG expression, a directory or a file under it), in the `"$name`, `${name}` and unquoted
    forms: (line number, name, the redirect's command as one text: its line and the backslash-continued lines above it)."""
    lines = text.splitlines()
    names = {m.group(1) for m in (CLI_ROOT_BINDING.match(line) for line in lines) if m}
    out = []
    for i, line in enumerate(lines):
        for name in sorted(names):
            if re.search(r'>>?\s*"?\$\{?%s\}?(?:/|"|\s|$)' % re.escape(name), line):
                j = i
                while j > 0 and lines[j - 1].rstrip().endswith("\\"):
                    j -= 1
                out.append((i + 1, name, "\n".join(lines[j:i + 1])))
    return out


def in_umask_group(text, i):
    """Whether position `i` of a shell text lies inside a `( umask 077; ...)` subshell: scanning back over balanced
    parentheses, the first unmatched `(` is followed by `umask 077;`."""
    depth = 0
    for j in range(i - 1, -1, -1):
        c = text[j]
        if c == ")":
            depth += 1
        elif c == "(":
            if depth == 0:
                return text[j + 1:].lstrip().startswith("umask 077;")
            depth -= 1
    return False


def remote_appends_unguarded(text):
    """The `>>"$LOGDIR/<name>"` writes of one ssh command string that are neither inside a `( umask 077; ...)` subshell nor
    onto a file the string made empty that way earlier (`( umask 077; : >>"$LOGDIR/<name>" )`, the pre-creation a command
    that must keep its own umask, the kernel's nohup, takes)."""
    bad = []
    for m in REMOTE_APPEND.finditer(text):
        pre = '( umask 077; : >>"$LOGDIR/%s" )' % m.group(1)
        if not (in_umask_group(text, m.start()) or pre in text[:m.start()]):
            bad.append(m.group(0))
    return bad

# THE ALLOWLIST: (file, function, kind, target text) -> the one-line reason the site is owner-only without a creator: its
# mode is set by code at that site. Every entry must match a creation the census finds (test_the_allowlist_carries_no_stale_entry).
ALLOWLIST = {
    # the serve-token loader, the one copy the repo keeps on purpose (kernel/kernel.py and postal/postal_service.py held
    # equal by tests/test_kernel_serve_token_mode.py's ServeTokenLoadersMatch): the mint's temp is created O_EXCL at 0600
    # and the lock O_CREAT at 0600; the root it makes on a box with none is mkdir(mode=0o700), a creation default the gate
    # then reads (the root itself is never tightened by a writer)
    ("kernel/kernel.py", "_serve_token_read_or_mint.mint", "os.open", "str(tmp)"):
        "the serve-token mint's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 (never wider under any umask), then published by os.replace",
    ("kernel/kernel.py", "_serve_token_read_or_mint", "mkdir", "f.parent"):
        "the state root itself, made mkdir(mode=0o700) when a box has none (a creation default; the gate reads it next and a writer never tightens the root)",
    ("kernel/kernel.py", "_serve_token_read_or_mint", "os.open", "str(lock)"):
        "serve-token.lock, opened O_RDWR|O_CREAT|O_NOFOLLOW at 0600 by the loader's own guards (round 3's correctness-2)",
    ("postal/postal_service.py", "_serve_token_read_or_mint.mint", "os.open", "str(tmp)"):
        "the bus's copy of the mint's temp, created O_EXCL at 0600 (held equal to the kernel's by ServeTokenLoadersMatch)",
    ("postal/postal_service.py", "_serve_token_read_or_mint", "mkdir", "f.parent"):
        "the bus's copy of the root's mkdir(mode=0o700) on a box with none (a creation default the gate reads next)",
    ("postal/postal_service.py", "_serve_token_read_or_mint", "os.open", "str(lock)"):
        "the bus's copy of the lock's O_RDWR|O_CREAT|O_NOFOLLOW open at 0600",
    ("kernel/kernel.py", "_persist_repo_root", "os.open", "str(tmp)"):
        "repo-root's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 and published by os.replace (the token mint's shape, round 2's fresh-1)",
    ("kernel/kernel.py", "_atomic_write", "os.open", "str(tmp)"):
        "the atomic publisher's mode road: O_WRONLY|O_CREAT|O_TRUNC at the caller's mode with an fchmod on the descriptor before "
        "the first write (PR 789; tests/test_kernel_remotes_perms.py pins the shape); the mode-less road takes the creator write_text",
    ("kernel/kernel.py", "_minted_host_id", "os.open", "str(_HOST_ID_FILE)"):
        "host-id, created O_WRONLY|O_CREAT|O_EXCL at 0600 (0644 until round 4f: nothing but this uid reads under a 0700 root)",
    ("postal/postal_service.py", "_minted_host_id", "os.open", "str(_HOST_ID_FILE)"):
        "the bus's copy of the host-id mint, O_EXCL at 0600 (0644 until round 4f)",
    ("postal/postal_service.py", "serve", "mkdir", "STATE.parent"):
        "the state root itself, made mkdir(mode=0o700) by the bus's serve() when the import gate found none (a creation default, "
        "then read by the start gate; a writer never tightens the root)",
    ("postal/postal_service.py", "serve", "os.open", "str(_pid_tmp)"):
        "server.pid's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 after the guard and published by os.replace (round 4)",
    ("kernel/judge.py", "<module>", "mkdir", "STATE"):
        "the judge module's own mkdir of the state root at import, mode=0o700 and without exist_ok so a creation is recorded "
        "(_STATE_ROOT_CREATED_AT_IMPORT) and a pre-existing root's EEXIST is the import-read rule's input; the chmod that follows "
        "is the import's repair, read before it runs",
    ("kernel/judge.py", "_rebind_state", "mkdir", "Path(STATE)"):
        "the test seam's root (make=True), made mode=0o700 and floored by the chmod two lines below; never a production road",
    ("kernel/judge.py", "_ensure_judge_scratch", "os.makedirs", "d"):
        "the judge scratch cwd: os.makedirs(mode=0o700) and then its own lstat, owner and tightening checks, a refusal for a symlink "
        "or another uid's directory (tests/test_judge_scratch_private.py, OwnerOnlyParity with the host's owner_only_dir)",
    ("kernel/session_host.py", "owner_only_dir", "mkdir", "d"):
        "PR 814's helper for hosts/ and hosts/<sid>/: mkdir(mode=0o700) and then its own lstat, owner and tightening checks, a "
        "refusal for a symlink or another uid's directory (tests/test_session_host.py; its census tests/test_hosts_path_census.py)",
    ("kernel/session_host.py", "SessionHost._serve_socket", "os.rename", "self.sock_path"):
        "the host's socket publish: the bound temp is chmod'ed 0600 at the site two lines above the rename (PR 814's socket mode), "
        "and the rename carries the inode's mode onto the published name",
    ("kernel/codex_runtime.py", "install_runtime", "Path.rename", "target"):
        "the Codex runtime's staging directory, pip's under a 0700 mkdtemp, is tightened to 0700 by make_dir at the site right before "
        "the rename publishes it (the mode travels with the inode; the tree inside keeps pip's modes, a residual named in the notes)",
    ("kernel/logins.py", "write_record", "os.open", "str(tmp)"):
        "a login record's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 in a logins/ directory chmod'ed 0700 at the site, then "
        "chmod'ed 0600 again after the rename (kernel/logins.py write_record)",
    ("kernel/sdk_backend.py", "ApiHealth.salt", "os.open", "str(tmp)"):
        "the API-health salt's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 and hard-linked into place (the inode keeps it)",
    ("kernel/sdk_backend.py", "write_reg", "os.open", "str(tmp)"):
        "a session reg's temp, O_WRONLY|O_CREAT|O_TRUNC at 0600 with the fchmod on the descriptor (PR 789's shape), published by os.replace",
    ("kernel/sdk_backend.py", "write_lease", "os.open", "str(tmp)"):
        "a lease's temp, O_WRONLY|O_CREAT|O_TRUNC at 0600 with the fchmod on the descriptor (round 4d), published by os.replace",
    ("kernel/sdk_backend.py", "flag_settings_path", "os.open", "p"):
        "the per-session settings file, O_WRONLY|O_CREAT|O_TRUNC at 0600 with the fchmod on the descriptor (it carries the environment overlay)",
    ("kernel/codex_backend.py", "CodexBackend._write_registry_locked", "os.open", "str(tmp)"):
        "the Codex registry's temp, created O_WRONLY|O_CREAT|O_EXCL at 0600 and published by os.replace",
    ("kernel/codex_backend.py", "CodexBackend._save_registry", "os.open", "str(self._reg_lock_path())"):
        "the Codex registry's lock, O_RDWR|O_CREAT at 0600 with an fchmod on the descriptor",
}


def cli_root_names(text):
    """Every name a bash text binds to the state root expression, underscore-led or not: name -> what follows the expression
    on its binding line ('' or '"' for the bare root, '/x"' for one level below it)."""
    out = {}
    for line in text.splitlines():
        m = CLI_ANY_ROOT_BINDING.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def _root_spellings(names):
    """The regexes that spell the root in a bash text: `$name`, `${name}` for each bound name, and the expression itself."""
    return [re.compile(r'\$\{?%s\b' % re.escape(n)) for n in sorted(names)] + [re.compile(CLI_ROOT_EXPR)]


def _handed(text, names):
    """Whether `text` (a command's prefix and arguments) carries a root spelling that is NOT a redirect's target."""
    for rx in _root_spellings(names):
        for m in rx.finditer(text):
            if not re.search(r'>>?\s*"?$', text[:m.start()]):
                return True
    return False


def cli_second_level_bindings(text):
    """Names bound by assignment from a root-bound name (`_x="$_root/..."`, `_x="${_root}/..."`): the level cli_redirects does
    not follow, held empty. An environment prefix at a line start (`X="$_root/f" cmd`) reads as one too, and is caught."""
    names = cli_root_names(text)
    out = []
    for line in text.splitlines():
        for n in sorted(names):
            m = re.match(r'^\s*(?:local\s+)?([A-Za-z_][A-Za-z0-9_]*)="?\$\{?%s\}?(?:/|"|$)' % re.escape(n), line)
            if m and m.group(1) not in names:
                out.append(m.group(1))
    return out


def _logical_lines(text):
    """(first line number, the line with its backslash continuations joined by one space): a command that continues over
    lines is read as one."""
    out, cur, start = [], None, 0
    for i, line in enumerate(text.splitlines(), 1):
        if cur is None:
            cur, start = "", i
        if line.rstrip().endswith("\\"):
            cur += line.rstrip()[:-1].rstrip() + " "
            continue
        out.append((start, cur + line.lstrip() if cur else line))
        cur = None
    if cur:
        out.append((start, cur.rstrip()))
    return out


def _cli_commands(text, words):
    """(line number, command text, the word, the logical line, the word's offset in it) for every command word in `words` at a
    command position whose environment prefix or arguments carry a root spelling not behind a redirect operator (a redirect
    is cli_redirects's); the text is prefix, word and arguments to the next unquoted separator or here-document, whitespace
    collapsed. The logical line is the command's own line with its backslash continuations; in_umask_group over it says
    whether the word sits inside a `( umask 077; ...)` group on that line."""
    if not words:
        return []
    rx = re.compile(CLI_POSITION + r'\s*' + CLI_ASSIGNS + r'(' + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r')\b' + CLI_ARGS)
    names = cli_root_names(text)
    out = []
    for i, logical in _logical_lines(text):
        for m in rx.finditer(logical):
            pre, word, args = m.group(1), m.group(2), m.group(3).split("<<")[0]
            if _handed(pre + " " + args, names):
                out.append((i, re.sub(r"\s+", " ", pre + word + args).strip(), word, logical, m.start(2)))
    return out


def cli_non_redirect_creations(text):
    return _cli_commands(text, set(CLI_CREATING_VERBS))


def cli_programs_handed_a_root_path(text):
    return _cli_commands(text, set(CLI_PROGRAMS))


def cli_functions_handed_a_root_path(text):
    """The bash functions of the text called with a root spelling among their arguments (the parameter road, which no
    assignment scan sees)."""
    return sorted({w for _l, _c, w, _g, _o in _cli_commands(text, {m.group(2) for m in CLI_FUNC_DEF.finditer(text)})})


def cli_function_parameter_misuse(text, name):
    """In the body of function `name` (closed by a brace at the definition's own indentation): a redirect onto a positional
    parameter, or a creating verb or program with one. A parameter re-bound to a local before the write is beyond this scan."""
    m = re.search(r'^(\s*)(?:function\s+)?%s\s*(?:\(\))?\s*\{(.*?)^\1\}' % re.escape(name), text, re.M | re.S)
    body = m.group(2) if m else ""
    return ([x for x in re.findall(r'>>?\s*"?\$\{?[0-9@*]', body)]
            + [x for x in re.findall(r'\b(?:%s)\b[^\n;&|]*\$\{?[0-9@*]' % "|".join(CLI_CREATING_VERBS + CLI_PROGRAMS), body)])


def cli_admitted(cmd, names, in_group):
    """Why a non-redirect creation is owner-only by construction, or None: a `mkdir -p` of the root itself (a name bound to the
    bare root, or the dirname of a name bound one level below) INSIDE a `( umask 077; ...)` group, so the root is born 0700;
    or a `mv` whose source is under the root (the inode carries the mode its creator gave it)."""
    bare = {n for n, rest in names.items() if rest.strip('"') == ""}
    below = {n for n, rest in names.items() if re.fullmatch(r'/[^/"]+"?', rest)}
    m = re.fullmatch(r'mkdir -p "\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?"', cmd)
    if m and m.group(1) in bare and in_group:
        return "the root born 0700"
    m = re.fullmatch(r'mkdir -p "\$\(dirname "\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?"\)"', cmd)
    if m and m.group(1) in below and in_group:
        return "the root born 0700 (the parent of an entry one level below it)"
    m = re.fullmatch(r'mv -f "\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?/[^" ]+" "\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?/[^" ]+"', cmd)
    if m and m.group(1) in names and m.group(2) in names:
        return "a rename from under the root: the inode carries its mode"
    return None


def cli_names_dir_misuse(text):
    """Lines using $ROMP_NAMES_DIR outside its binding that redirect onto it or hand it to a creating verb or program."""
    return [l.strip() for l in text.splitlines() if "$ROMP_NAMES_DIR" in l and not CLI_ANY_ROOT_BINDING.match(l)
            and (re.search(r'>>?\s*"?\$\{?ROMP_NAMES_DIR', l)
                 or re.search(r'\b(?:%s)\b' % "|".join(CLI_CREATING_VERBS + CLI_PROGRAMS), l))]


def cli_inline_root_uses(text):
    """Lines that spell the root expression outside a binding of it (and outside the function that defines it)."""
    return [(i, l.strip()) for i, l in enumerate(text.splitlines(), 1)
            if re.search(CLI_ROOT_EXPR, l) and not CLI_ANY_ROOT_BINDING.match(l) and not l.startswith("_romp_state_dir()")]


def cli_inline_misuse(text):
    """Inline uses of the root expression that redirect onto it or carry a creating verb anywhere on the line."""
    return [l for _i, l in cli_inline_root_uses(text)
            if re.search(r'>>?\s*"?(?:%s)' % CLI_ROOT_EXPR, l) or re.search(r'\b(?:%s)\b' % "|".join(CLI_CREATING_VERBS), l)]


def cli_cooccurrences(text):
    """The coarse backstop: every logical line carrying a root spelling (bound name, brace form or the expression) AND a
    creating verb, program or extra word (CLI_BACKSTOP_EXTRAS), whatever its position; whitespace collapsed, a trailing
    unquoted comment dropped, sorted."""
    names = cli_root_names(text)
    words = re.compile(r'\b(?:%s)\b' % "|".join(CLI_CREATING_VERBS + CLI_PROGRAMS + CLI_BACKSTOP_EXTRAS))
    return sorted(re.sub(r"\s+#[^\"']*$", "", re.sub(r"\s+", " ", l).strip()) for _i, l in _logical_lines(text)
                  if words.search(l) and any(rx.search(l) for rx in _root_spellings(names)))


def tool_sets_umask_first(source):
    """Whether a Python tool's main() opens with `os.umask(0o077)` and nothing at module level creates a file (write_text,
    write_bytes, open, replace, rename, copy*, mkdir, makedirs; module-level if/try bodies included). A helper called at module
    level that creates inside its own body is beyond this scan; the two tools have none."""
    tree = ast.parse(source)
    mains = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
    if len(mains) != 1 or not mains[0].body:
        return False
    first = mains[0].body[0]
    ok = (isinstance(first, ast.Expr) and isinstance(first.value, ast.Call) and isinstance(first.value.func, ast.Attribute)
          and isinstance(first.value.func.value, ast.Name) and first.value.func.value.id == "os" and first.value.func.attr == "umask"
          and len(first.value.args) == 1 and isinstance(first.value.args[0], ast.Constant) and first.value.args[0].value == 0o077)
    creators = {"write_text", "write_bytes", "open", "replace", "rename", "copy", "copy2", "copyfile", "copytree", "mkdir", "makedirs"}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for c in ast.walk(node):
            if isinstance(c, ast.Call):
                f = c.func
                if (isinstance(f, ast.Attribute) and f.attr in creators) or (isinstance(f, ast.Name) and f.id in creators):
                    return False
    return ok


def _mode_arg(call, idx):
    """The mode of an open-like call: the constant string at positional `idx` or the `mode` keyword; None when absent
    (the primitive's default, a read); "?" when present and not a constant (the census cannot read it)."""
    for i, a in enumerate(call.args):
        if i == idx:
            return a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else "?"
    for kw in call.keywords:
        if kw.arg == "mode":
            return kw.value.value if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) else "?"
    return None


def _writes(mode):
    return mode == "?" or any(c in mode for c in "wax+")


def _is_creator_module(recv):
    """The receiver of a creator call is the shared module: a name or attribute whose text ends in `srm` (`srm`, `_srm`, `jd.srm`)."""
    return R.unparse(recv).split(".")[-1].endswith("srm")


def _flags_create(call):
    """Whether an os.open call's flags carry O_CREAT (the second positional, or the `flags` keyword)."""
    for i, a in enumerate(call.args):
        if i == 1:
            return CREATE_FLAG in R.unparse(a)
    for kw in call.keywords:
        if kw.arg == "flags":
            return CREATE_FLAG in R.unparse(kw.value)
    return False


def _entry(mf, rel, n, fn, kind, target, how, source=None):
    return {"file": rel, "func": R._qual(mf, fn), "line": n.lineno, "col": n.col_offset, "end_line": n.end_lineno,
            "end_col": n.end_col_offset, "kind": kind, "target": R._txt(mf, target) if target is not None else "",
            "source": R._txt(mf, source) if source is not None else "", "guarded": how is not None, "how": how or "UNGUARDED"}


def _classify(mf, n, fn):
    """(kind, target, how, source) for a call that creates an entry under the root, or None. `how` is "creator", "inode"
    or "library" when the site is owner-only by code, None when it is bare."""
    f = n.func
    ftxt = R._txt(mf, f)
    args = n.args
    if isinstance(f, ast.Attribute):
        recv = f.value
        # (1) THE CREATORS: the shared module's make_dir, write_text, write_bytes, open_private, touch on a root path
        if f.attr in CREATORS and args and _is_creator_module(recv) and R._is_root(mf, args[0], fn):
            return f.attr, args[0], "creator", None
        if f.attr in ("mkdir",) and R._is_root(mf, recv, fn):
            return "mkdir", recv, None, None
        if f.attr in ("write_text", "write_bytes", "touch") and R._is_root(mf, recv, fn):
            return f.attr, recv, None, None
        if f.attr == "open" and R._is_root(mf, recv, fn):
            mode = _mode_arg(n, 0)
            if mode is not None and _writes(mode):
                return "open:" + mode, recv, None, None
            return None
        if f.attr in ("rename", "replace") and len(args) == 1 and not n.keywords and R._is_root(mf, args[0], fn):
            return "Path." + f.attr, args[0], ("inode" if R._is_root(mf, recv, fn) else None), recv   # str.replace takes two
        if f.attr == "hardlink_to" and R._is_root(mf, recv, fn):
            return "Path.hardlink_to", recv, ("inode" if args and R._is_root(mf, args[0], fn) else None), (args[0] if args else None)
        if f.attr == "symlink_to" and R._is_root(mf, recv, fn):
            return "Path.symlink_to", recv, None, None
        if ftxt in ("os.mkdir", "os.makedirs") and args and R._is_root(mf, args[0], fn):
            return ftxt, args[0], None, None
        if ftxt == "os.open" and args and R._is_root(mf, args[0], fn) and _flags_create(n):
            return "os.open", args[0], None, None
        if ftxt == "os.symlink" and len(args) >= 2 and R._is_root(mf, args[1], fn):
            return ftxt, args[1], None, None
        if ftxt in RENAME_FUNCS and len(args) >= 2 and R._is_root(mf, args[1], fn):
            return ftxt, args[1], ("inode" if R._is_root(mf, args[0], fn) else None), args[0]
        if ftxt in COPY_FUNCS and len(args) >= 2 and R._is_root(mf, args[1], fn):
            return ftxt, args[1], None, args[0]
        if ftxt in ("io.open", "gzip.open") and args and R._is_root(mf, args[0], fn):
            mode = _mode_arg(n, 1)
            if mode is not None and _writes(mode):
                return ftxt + ":" + mode, args[0], None, None
            return None
        if ftxt in TEMPFILE_FUNCS:
            for kw in n.keywords:
                if kw.arg == "dir" and R._is_root(mf, kw.value, fn):
                    return ftxt, kw.value, "library", None
            for a in args:
                if R._is_root(mf, a, fn):
                    return ftxt, a, "library", None
            return None
        return None
    if isinstance(f, ast.Name) and f.id == "open" and args and R._is_root(mf, args[0], fn):
        mode = _mode_arg(n, 1)
        if mode is not None and _writes(mode):
            return "open:" + mode, args[0], None, None
    return None


def census(root, rels, sources=None):
    """Every creation of an entry under the state root in `rels` (files under `root`, or the texts `sources` maps them to):
    dicts with file, func, line, kind, target, source, guarded and how."""
    entries = []
    for rel in rels:
        src = (sources or {}).get(rel)
        mf = R.module_facts(root, rel, src)
        for n in mf.all_calls:
            fn = mf.enclosing.get(id(n))
            hit = _classify(mf, n, fn)
            if hit is None:
                continue
            kind, target, how, source = hit
            entries.append(_entry(mf, rel, n, fn, kind, target, how, source))
    return entries


def _key(e):
    return (e["file"], e["func"], e["kind"], e["target"])


def unaccounted(entries):
    """The creations that are neither owner-only by code nor allowlisted."""
    return [e for e in entries if not e["guarded"] and _key(e) not in ALLOWLIST]


def render(entries):
    lines = []
    for e in entries:
        how = e["how"] if e["guarded"] else ("allowlisted" if _key(e) in ALLOWLIST else "UNGUARDED")
        src = (" <- " + e["source"]) if e["source"] else ""
        lines.append("%s:%d %s [%s] %s%s: %s" % (e["file"], e["line"], e["func"], e["kind"], e["target"], src, how))
    return lines


def counts(entries):
    """Per-module counts: {file: (total, owner-only by code, allowlisted, unguarded)}."""
    out = {}
    for rel in MODULES:
        mine = [e for e in entries if e["file"] == rel]
        bad = unaccounted(mine)
        guarded = sum(e["guarded"] for e in mine)
        out[rel] = (len(mine), guarded, len(mine) - guarded - len(bad), len(bad))
    return out


class TheWritersCensus(unittest.TestCase):
    """The population of creations under the state root, derived by code and pinned to the owner-only creators."""

    # THE PLANT: one copy of kernel/logins.py (a handed-root module: its `state_dir` parameters are the root, and its shared
    # module is `_srm`) with six bare creators and their owner-only twins, derived once per class. A small module on
    # purpose: the derivation of a planted copy is not cached, and a copy of kernel/kernel.py costs five seconds where
    # this one costs a fraction of one (the CI budget the round-4e speed pass set).
    PLANT_MODULE = "kernel/logins.py"
    PLANT = ('\n\ndef _planted_mkdir(state_dir):\n    (Path(state_dir) / "planted").mkdir(parents=True, exist_ok=True)\n\n\n'
             'def _planted_write(state_dir):\n    (Path(state_dir) / "planted.json").write_text("x")\n\n\n'
             'def _planted_append(state_dir):\n    with open(Path(state_dir) / "planted.jsonl", "a") as f:\n        f.write("x")\n\n\n'
             'def _planted_os_open(state_dir):\n    fd = os.open(str(Path(state_dir) / "planted.bin"), os.O_WRONLY | os.O_CREAT)\n    os.close(fd)\n\n\n'
             'def _planted_move(state_dir, src):\n    shutil.move(src, Path(state_dir) / "planted-moved")\n\n\n'
             'def _planted_rename_in(state_dir, src):\n    os.replace(src, Path(state_dir) / "planted-renamed")\n\n\n'
             'def _planted_mkdir_ok(state_dir):\n    _srm.make_dir(Path(state_dir) / "planted", parents=True, root=state_dir)\n\n\n'
             'def _planted_write_ok(state_dir):\n    _srm.write_text(Path(state_dir) / "planted.json", "x")\n\n\n'
             'def _planted_append_ok(state_dir):\n    with _srm.open_private(Path(state_dir) / "planted.jsonl", "a") as f:\n        f.write("x")\n\n\n'
             'def _planted_publish_ok(state_dir):\n    tmp = Path(state_dir) / "planted.tmp"\n    _srm.write_text(tmp, "x")\n'
             '    os.replace(tmp, Path(state_dir) / "planted")\n\n\n'
             'def _planted_temp_ok(state_dir):\n    return tempfile.mkstemp(dir=str(state_dir))\n\n\n'
             'def _planted_touch_ok(state_dir):\n    _srm.touch(Path(state_dir) / "planted-marker")\n\n\n'
             # the comprehension shadow (round 4f's review): a generator that rebinds `p` over data rows does not hide the
             # def's own root-derived `p` from the republish on a later line (kernel/kernel.py's _compact_notices shape)
             'def _planted_shadow(state_dir, rows):\n    p = Path(state_dir) / "shadow.jsonl"\n'
             '    tgt = next((p for p in rows if p.get("op") == "post"), None)\n    tmp = p.with_name(p.name + ".tmp")\n'
             '    tmp.write_text("x")\n    os.replace(tmp, p)\n    return tgt\n\n\n'
             'def _planted_shadow_ok(state_dir, rows):\n    p = Path(state_dir) / "shadow.jsonl"\n'
             '    tgt = next((p for p in rows if p.get("op") == "post"), None)\n    tmp = p.with_name(p.name + ".tmp")\n'
             '    _srm.write_text(tmp, "x")\n    os.replace(tmp, p)\n    return tgt\n')
    PLANTED_BARE = [("_planted_append", "open:a"), ("_planted_mkdir", "mkdir"), ("_planted_move", "shutil.move"),
                    ("_planted_os_open", "os.open"), ("_planted_rename_in", "os.replace"), ("_planted_shadow", "write_text"),
                    ("_planted_write", "write_text")]
    PLANTED_OK = [("_planted_append_ok", "open_private", "creator"), ("_planted_mkdir_ok", "make_dir", "creator"),
                  ("_planted_publish_ok", "os.replace", "inode"), ("_planted_publish_ok", "write_text", "creator"),
                  ("_planted_shadow_ok", "os.replace", "inode"), ("_planted_shadow_ok", "write_text", "creator"),
                  ("_planted_temp_ok", "tempfile.mkstemp", "library"), ("_planted_touch_ok", "touch", "creator"),
                  ("_planted_write_ok", "write_text", "creator")]
    _planted = None

    @classmethod
    def setUpClass(cls):
        cls.entries = census(Path(ROOT), MODULES)

    @classmethod
    def planted_module(cls):
        if cls._planted is None:
            src, _tree = R.source_and_tree(os.path.join(ROOT, cls.PLANT_MODULE), cls.PLANT_MODULE)
            cls._planted = census(Path(ROOT), [cls.PLANT_MODULE], sources={cls.PLANT_MODULE: src + cls.PLANT})
        return cls._planted

    def test_every_creation_under_the_root_is_owner_only_by_code_or_allowlisted(self):
        """THE PIN. Every creation the census finds in the eleven modules is through a creator, a rename of an entry born
        under the root, a tempfile, or on ALLOWLIST with its reason. A new bare creator anywhere in them fails here,
        naming its file, line, function, kind and target."""
        bad = unaccounted(self.entries)
        self.assertEqual(bad, [], "creators under the state root that are not owner-only by code:\n" + "\n".join(render(bad)))
        guarded = [e for e in self.entries if e["guarded"]]
        self.assertGreater(len(guarded), 150, "the census sees the population (%d owner-only creations)" % len(guarded))
        by_file = collections.Counter(e["file"] for e in guarded)
        for rel in ("kernel/kernel.py", "kernel/judge.py", "kernel/event_model.py", "postal/postal_service.py",
                    "kernel/session_host.py", "kernel/sdk_backend.py", "kernel/codex_backend.py"):
            self.assertGreater(by_file[rel], 0, "%s has owner-only creations (%r)" % (rel, dict(by_file)))
        kinds = collections.Counter(e["kind"] for e in guarded)
        for kind in ("make_dir", "write_text", "open_private", "touch", "os.replace"):
            self.assertGreater(kinds[kind], 0, "the creators are in use (%r)" % dict(kinds))

    def test_the_allowlist_carries_no_stale_entry_and_every_entry_has_a_reason(self):
        found = {_key(e) for e in self.entries if not e["guarded"]}
        for key, reason in ALLOWLIST.items():
            self.assertIn(key, found, "a stale allowlist entry: %r no longer names a creation the census finds" % (key,))
            self.assertTrue(isinstance(reason, str) and len(reason.split()) >= 8, "a reason, not a label: %r" % (key,))

    def test_no_allowlisted_site_is_a_bare_primitive_without_a_mode(self):
        """Every allowlisted site sets its mode by code AT THAT SITE: the call's own lines, or the three around them, carry
        a mode literal (0o600, 0o700), an fchmod on the descriptor it opened, or a creator's tightening (make_dir); never a
        reason alone."""
        lines_by_file = {}
        for e in self.entries:
            if _key(e) in ALLOWLIST:
                text = lines_by_file.get(e["file"])
                if text is None:
                    text = lines_by_file[e["file"]] = R.source_and_tree(os.path.join(ROOT, e["file"]), e["file"])[0].splitlines()
                seg = "\n".join(text[max(0, e["line"] - 4):e["end_line"] + 3])
                self.assertTrue("0o600" in seg or "0o700" in seg or "make_dir(" in seg or "fchmod(" in seg,
                                "%s:%d %s: an allowlisted creator sets its mode at the site: %r" % (e["file"], e["line"], e["func"], seg))

    def test_the_census_reds_on_a_planted_bare_creator(self):
        """The pin can red: the planted copy of kernel/logins.py (PLANT) carries a bare mkdir, write_text, append open,
        os.open with O_CREAT, a shutil.move onto the root and an os.replace from outside it, each on a path built from a
        `state_dir` parameter; each comes out unguarded and unallowlisted, and nothing else in the copy does. The twins
        through the creators, a publish by a temp born under the root and a tempfile come out owner-only, each by its way."""
        entries = self.planted_module()
        bad = unaccounted(entries)
        self.assertEqual(sorted((e["func"], e["kind"]) for e in bad), self.PLANTED_BARE,
                         "the planted bare creators, and nothing else:\n" + "\n".join(render(bad)))
        ok = sorted((e["func"], e["kind"], e["how"]) for e in entries if e["func"].endswith("_ok"))
        self.assertEqual(ok, self.PLANTED_OK, "\n".join(render([e for e in entries if e["func"].endswith("_ok")])))

    def test_the_writers_outside_the_eleven_modules_set_their_mode_at_the_site(self):
        """THE CLI, THE MANAGER AND THE FAR SHELL (round 4f's review). bin/romp: every `>` or `>>` onto a path under a name
        the script binds to the state root runs under `umask 077` on the writing command (a subshell around it, or the
        function's own subshell), so judge-engine, default-backend, debug-mode.json, the down-by-romp marker's temp and
        restart-audit.jsonl are born 0600 under any umask (cli_redirects derives the names and the redirects; at least the
        six sites are found). bin/romp-manager: every appendFileSync and writeFileSync carries `mode: 0o600` (one writer,
        appendAudit). kernel/kernel.py: every `>>"$LOGDIR/<name>"` in the three ssh command strings is inside a
        `( umask 077; ...)` subshell or onto a file the string made empty that way first (remote_appends_unguarded). Each of
        the three checks reds on a planted bare shape."""
        text = open(os.path.join(ROOT, "bin", "romp"), encoding="utf-8").read()
        found = cli_redirects(text)
        self.assertGreaterEqual(len(found), 6, "the CLI's writers under the root are found: %r" % [(l, n) for l, n, _c in found])
        for ln, name, cmd in found:
            self.assertIn("umask 077", cmd, "bin/romp:%d writes under the root through $%s without umask 077 on its command:\n%s"
                          % (ln, name, cmd))
        planted = text + '\n_pl="$(_romp_state_dir)"\nprintf x > "$_pl/planted"\nprintf x > "${_pl}/planted"\nprintf x >$_pl/planted\n'
        self.assertEqual([c for _l, _n, c in cli_redirects(planted) if "umask 077" not in c],
                         ['printf x > "$_pl/planted"', 'printf x > "${_pl}/planted"', 'printf x >$_pl/planted'],
                         "the CLI check reds on a planted bare redirect in each spelling and on nothing else")
        mtext = open(os.path.join(ROOT, "bin", "romp-manager"), encoding="utf-8").read()
        sites = [m.group(0) for m in MANAGER_WRITE.finditer(mtext)]
        self.assertTrue(sites, "the manager appends its audit rows")
        for site in sites:
            self.assertIn("0o600", site, "bin/romp-manager writes under the root without a mode: %s" % site)
        self.assertEqual([s for s in MANAGER_WRITE.findall("x;\nfs.appendFileSync(path.join(root, 'planted.jsonl'), row + '\\n');\ny;")
                          if "0o600" not in s], ["appendFileSync(path.join(root, 'planted.jsonl'), row + '\\n');"],
                         "the manager check reds on a planted bare append")
        _src, tree = R.source_and_tree(os.path.join(ROOT, "kernel", "kernel.py"), "kernel/kernel.py")
        cmds = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and '"$LOGDIR/' in n.value
                and REMOTE_APPEND.search(n.value)]
        self.assertEqual(len(cmds), 3, "the three ssh command strings that write on a far root (%d found)" % len(cmds))
        self.assertGreaterEqual(sum(len(REMOTE_APPEND.findall(c)) for c in cmds), 10, "their appends are found")
        for c in cmds:
            self.assertEqual(remote_appends_unguarded(c), [], "a far-root write born at the login shell's umask in:\n%s" % c[:2500])
        self.assertEqual(remote_appends_unguarded('X=1; echo x >>"$LOGDIR/planted.log"; '), ['>>"$LOGDIR/planted.log"'],
                         "the far-shell check reds on a planted bare append")
        self.assertEqual(remote_appends_unguarded('A="$(cmd)"; ( umask 077; echo x >>"$LOGDIR/planted.log" ); '), [])
        self.assertEqual(remote_appends_unguarded('( umask 077; : >>"$LOGDIR/planted.log" ); nohup x >>"$LOGDIR/planted.log" & '), [])

    def test_the_clis_non_redirect_creations_are_the_roots_own_mkdirs_and_the_markers_move(self):
        """THE REACH OF THE CLI RULE, PINNED BY EQUALITY (romp-manager's round-3 preparation and its adversarial review,
        2026-09-21). cli_redirects judges redirects onto one level of underscore-led root binding; this test holds what it does
        not judge to the lists found on 2026-09-21, in the shapes its regexes read, so a new site of any kind reds: (1) no name
        is bound from a root-bound name by assignment; (2) the functions handed a root path are exactly
        CLI_FUNCTIONS_HANDED_A_ROOT_PATH and their bodies carry no redirect or creating verb on a positional parameter; (3) the
        non-redirect creations under a root spelling are exactly CLI_NON_REDIRECT_CREATIONS, five `mkdir -p` of the root itself
        inside a `( umask 077; ...)` group and the marker's `mv`, each admitted by cli_admitted; (4) the programs handed a root
        path, by argument or by environment prefix, are exactly CLI_PROGRAMS_HANDED_A_ROOT_PATH; (5) ROMP_NAMES_DIR is the only
        root binding CLI_ROOT_BINDING does not match, and its one use is a read; (6) the root expression appears outside a
        binding on CLI_INLINE_ROOT_USES lines, none a redirect onto it and none carrying a creating verb; (7) the coarse
        backstop: every line carrying both a root spelling and a creating verb or program word, whatever its position, is one
        of CLI_COOCCURRENCES; (8) the two Python tools the CLI delegates to (CLI_UMASK_TOOLS) open main() with os.umask(0o077)
        and create nothing at module level. Each check reds on a plant."""
        text = open(os.path.join(ROOT, "bin", "romp"), encoding="utf-8").read()
        names = cli_root_names(text)
        self.assertEqual(cli_second_level_bindings(text), [], "a name bound from a root-bound name: widen cli_redirects to follow it")
        self.assertEqual(cli_functions_handed_a_root_path(text), CLI_FUNCTIONS_HANDED_A_ROOT_PATH, "a function is handed a root path")
        for fn in CLI_FUNCTIONS_HANDED_A_ROOT_PATH:
            self.assertEqual(cli_function_parameter_misuse(text, fn), [], "%s writes through its parameter" % fn)
        found = cli_non_redirect_creations(text)
        self.assertEqual(sorted(c for _l, c, _w, _g, _o in found), CLI_NON_REDIRECT_CREATIONS,
                         "the CLI's non-redirect creations under the root changed: %r" % [(l, c) for l, c, _w, _g, _o in found])
        for ln, cmd, _w, logical, off in found:
            self.assertIsNotNone(cli_admitted(cmd, names, in_umask_group(logical, off)),
                                 "bin/romp:%d creates under the root by a path and is neither the root's own mkdir inside a "
                                 "`( umask 077; ...)` group on its line nor a rename from under the root: %s" % (ln, cmd))
        progs = cli_programs_handed_a_root_path(text)
        self.assertEqual(sorted(c for _l, c, _w, _g, _o in progs), CLI_PROGRAMS_HANDED_A_ROOT_PATH,
                         "a program is handed a path under the root: read what it does with it, then list it: %r" % [(l, c) for l, c, _w, _g, _o in progs])
        others = sorted(n for n in names if not CLI_ROOT_BINDING.match('%s="$(_romp_state_dir)"' % n))
        self.assertEqual(others, ["ROMP_NAMES_DIR"], "a root binding cli_redirects does not match: %r" % others)
        uses = [l.strip() for l in text.splitlines() if "$ROMP_NAMES_DIR" in l and not CLI_ANY_ROOT_BINDING.match(l)]
        self.assertEqual(len(uses), 1, "ROMP_NAMES_DIR's uses: %r" % uses)
        self.assertEqual(cli_names_dir_misuse(text), [])
        inline = cli_inline_root_uses(text)
        self.assertEqual(len(inline), CLI_INLINE_ROOT_USES, "the root expression outside a binding: %r" % inline)
        self.assertEqual(cli_inline_misuse(text), [])
        self.assertEqual(cli_cooccurrences(text), CLI_COOCCURRENCES, "a line with a root spelling and a creating verb or program changed")
        for rel in CLI_UMASK_TOOLS:
            self.assertTrue(tool_sets_umask_first(open(os.path.join(ROOT, rel), encoding="utf-8").read()),
                            "%s: os.umask(0o077) is not main()'s first statement, or the module creates a file at import" % rel)
        # THE RED SHAPES, one per check and per admitted branch, planted at the end of a copy of the CLI
        planted = text + "\n".join(["", '_pl="$(_romp_state_dir)"', '_pl3="$(_romp_state_dir)/one.json"', '_pl2="${_pl}/deeper"',
                                    'mkdir -p "$_pl/sub"', 'cp x "$_pl/y"', 'echo x | tee "${_pl}/z"', 'if mkdir "$_pl/lock"; then :; fi',
                                    'mv -f /elsewhere/x "$_pl/y"', 'mkdir -p "$_pl"', '( umask 077; mkdir -p "$_pl" )',
                                    '( umask 077; mkdir -p "$(dirname "$_pl3")" )', 'mv -f "$_pl/a.tmp" "$_pl/a"',
                                    'mkdir -p \\', '    "$_pl/cont"', "node - \"$_pl/r.json\" <<'JS'", 'X="$_pl/f" python3 -',
                                    "_pl_fn() {", '    : > "$1/x"', "}", '_pl_fn "$_pl"',
                                    "    function _pl_fn2 {", '        cp y "$1/z"', "    }", '    _pl_fn2 "$_pl"',
                                    'echo x > "$ROMP_NAMES_DIR/planted"', 'echo x | tee "$(_romp_state_dir)/y"',
                                    'printf x > "$(_romp_state_dir)/planted"', 'chmod 666 "$_pl/loose"', ""])
        pnames = cli_root_names(planted)
        self.assertEqual(cli_second_level_bindings(planted), ["_pl2", "X"], "an assignment and an environment prefix at a line start")
        self.assertEqual(cli_functions_handed_a_root_path(planted), sorted(CLI_FUNCTIONS_HANDED_A_ROOT_PATH + ["_pl_fn", "_pl_fn2"]),
                         "a function at column 0 and an indented one in the `function` form")
        self.assertEqual(cli_function_parameter_misuse(planted, "_pl_fn"), ['> "$1'])
        self.assertEqual(cli_function_parameter_misuse(planted, "_pl_fn2"), ['cp y "$1'])
        new = cli_non_redirect_creations(planted)[len(found):]
        self.assertEqual([c for _l, c, _w, _g, _o in new],
                         ['mkdir -p "$_pl/sub"', 'cp x "$_pl/y"', 'tee "${_pl}/z"', 'mkdir "$_pl/lock"', 'mv -f /elsewhere/x "$_pl/y"',
                          'mkdir -p "$_pl"', 'mkdir -p "$_pl"', 'mkdir -p "$(dirname "$_pl3")"', 'mv -f "$_pl/a.tmp" "$_pl/a"',
                          'mkdir -p "$_pl/cont"', 'tee "$(_romp_state_dir)/y"'], "the planted creations are found in order, the continued one joined")
        self.assertEqual([cli_admitted(c, pnames, in_umask_group(g, o)) for _l, c, _w, g, o in new],
                         [None, None, None, None, None, None, "the root born 0700", "the root born 0700 (the parent of an entry one level below it)",
                          "a rename from under the root: the inode carries its mode", None, None],
                         "the grouped mkdirs of the root and the rename from under it are admitted, nothing else")
        self.assertEqual([c for _l, c, _w, _g, _o in cli_programs_handed_a_root_path(planted)][len(progs):],
                         ['node - "$_pl/r.json"', 'X="$_pl/f" python3 -'], "a program handed a path by argument and by environment")
        self.assertEqual(cli_names_dir_misuse(planted), ['echo x > "$ROMP_NAMES_DIR/planted"'])
        self.assertEqual(len(cli_inline_root_uses(planted)), CLI_INLINE_ROOT_USES + 2, "the tee and the printf; the bindings are not uses")
        self.assertEqual(cli_inline_misuse(planted), ['echo x | tee "$(_romp_state_dir)/y"', 'printf x > "$(_romp_state_dir)/planted"'])
        self.assertEqual(sorted(set(cli_cooccurrences(planted)) - set(CLI_COOCCURRENCES)),
                         sorted(['mkdir -p "$_pl/sub"', 'cp x "$_pl/y"', 'echo x | tee "${_pl}/z"', 'if mkdir "$_pl/lock"; then :; fi',
                                 'mv -f /elsewhere/x "$_pl/y"', 'mkdir -p "$_pl"', '( umask 077; mkdir -p "$_pl" )',
                                 '( umask 077; mkdir -p "$(dirname "$_pl3")" )', 'mv -f "$_pl/a.tmp" "$_pl/a"', 'mkdir -p "$_pl/cont"',
                                 'node - "$_pl/r.json" <<\'JS\'', 'X="$_pl/f" python3 -', 'echo x | tee "$(_romp_state_dir)/y"',
                                 'chmod 666 "$_pl/loose"']), "the backstop lists every planted line with a root spelling and a word, the continued one joined")
        self.assertFalse(tool_sets_umask_first("import os\ndef main():\n    x = 1\n    os.umask(0o077)\n"), "umask not first")
        self.assertFalse(tool_sets_umask_first("import os\nopen('x', 'w')\ndef main():\n    os.umask(0o077)\n"), "a module-level creator")
        self.assertTrue(tool_sets_umask_first("import os\ndef main():\n    os.umask(0o077)\n    return 0\n"))

    def test_the_census_reuses_the_readers_derivation(self):
        """One derivation per module per process: the facts the readers census cached (module_facts, _FACTS) are the ones
        this census read, so the two censuses cost one parse and one derivation of each module between them. This asserts
        SHARING, not warmth: it holds whichever census ran first (see the module docstring on collection order)."""
        for rel in MODULES:
            path = os.path.join(ROOT, rel)
            st = os.stat(path)
            self.assertIn((path, (st.st_size, st.st_mtime_ns)), R._FACTS, "%s derived once and cached" % rel)
            self.assertIn(path, R._PARSED, "%s parsed once and cached" % rel)
        loaded = [m for name, m in sys.modules.items() if name.rsplit(".", 1)[-1] == "test_state_root_readers"]
        self.assertTrue(all(m is R for m in loaded), "one readers module object in this process, the one this census reads (%r)"
                        % [name for name in sys.modules if name.rsplit(".", 1)[-1] == "test_state_root_readers"])


def _main(argv):
    entries = census(Path(ROOT), MODULES)
    for line in render(entries):
        print(line)
    bad = unaccounted(entries)
    print()
    for rel, (total, guarded, allowed, unguarded) in counts(entries).items():
        print("%-28s %3d creations: %3d owner-only by code, %2d allowlisted, %2d UNGUARDED" % (rel, total, guarded, allowed, unguarded))
    print("\n%d creations under the state root: %d owner-only by code, %d allowlisted, %d UNGUARDED"
          % (len(entries), sum(e["guarded"] for e in entries), len(entries) - sum(e["guarded"] for e in entries) - len(bad), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--list" in sys.argv[1:]:
        sys.exit(_main(sys.argv[1:]))
    unittest.main()
