#!/usr/bin/env python3
"""The differential: the unit oracle in tests/romp-service.bats (`_sd`) against the real systemd, offline.

The oracle is a second implementation of systemd's unit parser, and the only thing that can say whether it or the
reader in bin/romp-service is wrong is running both against the real one. Round 4 of fork PR #778's review ran this
once as a lens over 684 synthetic units and found 125 disagreements in 11 classes (A to K below), so the fold that
followed checked the comparison in here, as a recipe the next round runs instead of re-deriving it.

What it does: generates the lens's fixture set (every specifier letter on the Environment, ExecStart-path and
ExecStart-argument surfaces, the unit-name specifiers also as template instances, %%, a trailing %, unknown letters
and digits, the deprecated %c %r %R, % before eleven non-alphanumerical characters, eight EnvironmentFile forms, 61
escape tokens on six surfaces plus two single-quoted ones, eight stray-backslash forms, 97 ExecStart forms), plus a
small batch the fold added (raw noncharacters, the plane-1 noncharacter escapes, a last-line continuation on an
Environment line, a backslash at the end of a quoted argument) and its addendum added to (the accepted side of each
refused Unicode range, the last plane's noncharacters raw and escaped, a 255-byte name and path component, and the
continuation shapes a comment line, a blank line or a whitespace-only line follows; the round-5 preface added the EnvironmentFile
forms path_simplify changes, a doubled slash, a . component, a trailing slash, a .. component; round 6 added the UTF-8 byte order
mark's shapes, both sides of systemd's one latch per file, and Restart= beside Type=oneshot, both sides of service_verify's rule),
reported separately so the 684 stay comparable with the lens's numbers. Each fixture is written as a synthetic user unit under a scratch root and loaded by
`systemd-analyze --user --man=no verify` with `env -i`, HOME and XDG_RUNTIME_DIR under that root, SYSTEMD_UNIT_PATH
pointing at the fixtures (stub basic, shutdown and default targets beside them; nothing of the live user
configuration is read) and SYSTEMD_LOG_LEVEL=debug, which makes verify dump the loaded unit (its Environment:,
EnvironmentFile: and Command Line: lines, the last undone from quote_command_line's escaping), print the resolved
exec->path of the first ExecStart command in its "Command X is not executable" check (every fixture path is under
/nx, which does not exist) and say "has a bad unit file setting" when the unit fails to load. The oracle is
extracted verbatim from tests/romp-service.bats and run through its CLI in `dump` mode with the same HOME.

Verdicts per fixture: agree; agree (both refuse); REFUSES (the oracle raises NotImplementedError, its documented
not-modelled path, or a comparison this harness cannot make: systemd prints the resolved exec->path of its FIRST command
alone, and only in the executable check, which the - prefix's error downgrade skips, so for a first command under - the
field is uncompared and the row says so, never agree; round 6 of fork PR #778, extra6-1: six fixtures agreed with the
field skipped in silence; its addendum prints those rows with the reason under their own heading, where the report had
listed DISAGREE rows alone, and keeps the note on a row a DISAGREE elsewhere wins); DISAGREE. The direction that matters
most is counted on its own, the dangerous column: a
disagreement where the oracle reports what systemd does not set, run or read. Its shapes: a value systemd leaves unset or
sets to something else (both set and different is the oracle, and a reader following it, reporting a value systemd will
not set, the direction's worst member since it is confidently wrong), a unit systemd fails to load reported as loaded, a
command systemd does not run (as many commands as systemd's or more with a difference among them, fewer with one that is
not among systemd's, or a FIRST command that is not systemd's first: the reader's identity check reads the first
command, so an oracle that drops it and reports the second names a manager the service does not start first; round 6,
extra6-2, where the exec->path branch counted this shape by accident and the prose placed it on the unmarked side),
another exec->path for the first command (positional, since that is the one path systemd prints), and a file systemd
does not read (as many EnvironmentFile paths or more with a difference, or fewer with one not among systemd's). The
other direction is a DISAGREE without the mark, and it is two things where the reader in bin/romp-service follows the
oracle: the oracle REFUSING (a fatal) what systemd loads is a false refusal, which the operator sees and cannot work
around; the oracle leaving UNSET what systemd sets (a variable, an EnvironmentFile), or listing fewer commands every one
among systemd's with the first command kept, or fewer files every one among systemd's (the first-kept rule is the argv
branch's alone: the reader's identity check reads the first command and no first file, so a dropped first file with a
later one kept is this class too), is the D4 class, since the reader does not refuse on an absence: it
writes this clone's value (ExecStart, ROMP_DIR, the service.env default) or omits the line (PATH, an instance variable)
at exit 0. That half stays unmarked on purpose: the column means the ORACLE reporting what systemd does not do, a
confident wrong report, and marking a silence too would make every DISAGREE dangerous and the column say nothing; every
such row is a DISAGREE printed in full, and this paragraph is what a reader triaging one must hold (round 6,
correctness-2: the prose called that half a false refusal). Until fork PR #778's round-5 preface the column marked
systemd-unset-oracle-set, more commands and more files alone, so a both-set mismatch and a same-count argv difference
went unmarked; until that commit's addendum a shorter list carrying a command or a file systemd does not run or read
went unmarked too. Round 6 gave the mark a table of synthetic pairs on both sides of every shape (MARK_CASES,
self_check), run before the sweep and exiting nonzero on a mismatch, since no real fixture at an agreeing head can
show the mark fires: until then a dead mark printed the same 0 dangerous and the same rows, the tag alone missing.

Run:  python3 tests/romp-service-differential.py            (about ten seconds; four verify runs at a time)
      python3 tests/romp-service-differential.py --list    (the fixture ids and their [Service] lines, no runs; a mark shows as <BOM>)
It needs systemd-analyze on PATH and exits 2 saying so when there is none: it is a documented command, not a test
that skips, since its counts are a claim about one systemd build; the mark's self-check needs no systemd and runs first,
exiting 1 on a mismatch (tests/test_romp_service_differential_mark.py pins the same table in the suite, so an edit to
compare() is caught where the recipe is not run). Every class is a reading of that build:

  WRITTEN AGAINST: systemd 255 (255.4-1ubuntu8.17)
  EXPECTED AT THE FOLD HEAD (2026-09-19): see tests/README.md, which carries the pasted totals and the per-class
  table from the run at that head, and the fold batch's count after the addendum and the round-5 preface. 256 may move any class; a
  different version prints a notice beside the counts.

Classes (the round-4 lens's ids; assignment by fixture id, every disagreement in exactly one class):
  A  % before a non-alphanumerical character (systemd keeps both characters)    B  the deprecated %c %r %R
  C  \\u escapes naming a noncharacter (systemd drops the assignment)             D  \\U escapes naming a surrogate or
  E  a trailing backslash on the file's last line                                   a noncharacter (systemd refuses)
  F  the @ prefix's argv shape                 G  repeated or conflicting prefixes     H  a quoted or escaped ; argument
  I  filename_is_valid / path_is_valid         J  path_simplify on exec->path          K  the - prefix downgrading errors
"""
import json, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BATS = os.path.join(HERE, "romp-service.bats")
WRITTEN_AGAINST = "systemd 255 (255.4-1ubuntu8.17)"
NX = "/nx/bin/x"

# ---- the fixture set ---------------------------------------------------------------------------------------------
TABLE = "aAbBCdEfgGhHiIjJlLmMnNopPqsStTuUvVwWyY"           # systemd.unit(5) Table 5 on 255
INST = "iIpPnNfjJyYh"                                        # the unit-name specifiers, also run on a template instance
UNK = "DcrRZxk10"                                            # letters and digits outside the table (c r R: deprecated, resolving)
NONALNUM = [("slash", "/"), ("dash", "-"), ("dot", "."), ("us", "_"), ("tilde", "~"), ("at", "@"), ("colon", ":"),
            ("plus", "+"), ("hash", "#")]
ESC = ["bsbs", "bsdq", "bssq", "bss", "bsn", "bst", "bsr", "bsa", "bsb", "bsf", "bsv", "bsx41", "bsx00", "bsx4", "bsxg1",
       "bsx4g", "bsxff", "bsx7f", "bsx1b", "bsX41", "bs101", "bs000", "bs377", "bs400", "bs777", "bs12", "bs8", "bs9",
       "bsu0041", "bsu0000", "bsud800", "bsu00e9", "bsu004", "bsuFFFE", "bsuFDD0", "bsU00000041", "bsU0000D800",
       "bsU0000DFFF", "bsU0000FFFF", "bsU0000FDEF", "bsU0000FDD5", "bsU0000E000", "bsU0000FDF0", "bsuFFFF", "bsuFDEF",
       "bsuE000", "bsuDFFF", "bsU0000FFFE", "bsU0000FDD0", "bsU00110000", "bsUFFFFFFFF", "bsU0001F600", "bsU0000004",
       "bsq", "bssp", "bssemi", "bspct", "bshash", "bse", "bs0", "bsQ"]
ESC_TEXT = {"bs": "\\", "dq": '"', "sq": "'", "sp": " ", "semi": ";", "pct": "%", "hash": "#"}
FORMS = [  # (id, lines) for the ExecStart forms; `Type=oneshot` where two commands are meant to load
    ("bare", [f"ExecStart={NX}"]), ("dq", [f'ExecStart="{NX}"']), ("sq", [f"ExecStart='{NX}'"]),
    ("space-dq", ['ExecStart="/nx/bi n/x"']), ("space-sq", ["ExecStart='/nx/bi n/x'"]), ("space-bss", ["ExecStart=/nx/bi\\sn/x"]),
    ("space-bssp", ["ExecStart=/nx/bi\\ n/x"]), ("space-unq", ["ExecStart=/nx/bi n/x"]),
    ("space-dq-args", ['ExecStart="/nx/bi n/x" up "a b"']), ("dq-partial", ['ExecStart=/nx/"bi n"/x']),
    ("dq-adjacent", ['ExecStart="/nx/bin"/x']),
    ("pre-dash", [f"ExecStart=-{NX}"]), ("pre-at", [f"ExecStart=@{NX} name arg"]), ("pre-at-alone", [f"ExecStart=@{NX}"]),
    ("pre-colon", [f"ExecStart=:{NX}"]), ("pre-plus", [f"ExecStart=+{NX}"]), ("pre-bang", [f"ExecStart=!{NX}"]),
    ("pre-bangbang", [f"ExecStart=!!{NX}"]), ("pre-bangbangbang", [f"ExecStart=!!!{NX}"]), ("pre-dashdash", [f"ExecStart=--{NX}"]),
    ("pre-atat", [f"ExecStart=@@{NX} a"]), ("pre-plusbang", [f"ExecStart=+!{NX}"]), ("pre-bangplus", [f"ExecStart=!+{NX}"]),
    ("pre-dashat", [f"ExecStart=-@{NX} n"]), ("pre-atdash", [f"ExecStart=@-{NX} n"]), ("pre-dashbangbang", [f"ExecStart=-!!{NX}"]),
    ("pre-coloncolon", [f"ExecStart=::{NX}"]), ("pre-plusplus", [f"ExecStart=++{NX}"]), ("pre-all", [f"ExecStart=-@:+!{NX} n"]),
    ("pre-pipe", [f"ExecStart=\\|{NX}"]), ("pre-dash-alone", ["ExecStart=-"]), ("pre-dash-up", ["ExecStart=- up"]),
    ("pre-at-up", ["ExecStart=@ up"]), ("pre-dashat-alone", [f"ExecStart=-@{NX}"]), ("pre-dash-quoted", [f'ExecStart="-{NX}"']),
    ("pre-dash-dqpath", [f'ExecStart=-"{NX}"']),
    ("args-one", [f"ExecStart={NX} up"]), ("args-quoted", [f'ExecStart={NX} "a b" c']), ("args-empty-dq", [f'ExecStart={NX} "" c']),
    ("args-empty-sq", [f"ExecStart={NX} '' c"]), ("args-adjacent", [f'ExecStart={NX} a"b c"d']), ("args-tabs", [f"ExecStart={NX}\ta\t b"]),
    ("sep-semi-quoted", [f'ExecStart={NX} a ";" b']), ("sep-semi-sq", [f"ExecStart={NX} a ';' b"]), ("sep-semi-bs", [f"ExecStart={NX} a \\; b"]),
    ("sep-semi-bsbs", [f"ExecStart={NX} a \\\\; b"]), ("sep-semi-glued", [f"ExecStart={NX} a;b"]), ("sep-semi-lead", [f"ExecStart={NX} a ;b"]),
    ("sep-semi-trailtext", [f"ExecStart={NX} a; b"]), ("sep-semi-end", [f"ExecStart={NX} a ;"]), ("sep-semi-start", [f"ExecStart=; {NX} a"]),
    ("sep-semi-start-quoted", [f'ExecStart=";" {NX} a']), ("sep-semi-start-bs", [f"ExecStart=\\; {NX} a"]), ("sep-semi-only", ["ExecStart=;"]),
    ("sep-semi-double", [f"ExecStart={NX} a ; ; /nx/bin/y"]), ("sep-semi-tab", [f"ExecStart={NX} a ;\t/nx/bin/y"]),
    ("path-dot", ["ExecStart=."]), ("path-dotdot", ["ExecStart=.."]), ("path-name", ["ExecStart=x"]), ("path-rel", ["ExecStart=x/y"]),
    ("path-dslash", ["ExecStart=/nx//bin/x"]), ("path-dotseg", ["ExecStart=/nx/./bin/x"]), ("path-dir", [f"ExecStart={NX}/"]),
    ("path-root", ["ExecStart=/"]), ("path-droot", ["ExecStart=//"]), ("path-dslash-args", ["ExecStart=/nx//bin/x up"]),
    ("path-unbal-first", [f'ExecStart={NX}"']), ("path-unbal-arg", [f'ExecStart={NX} "a']), ("path-unbal-open", [f'ExecStart="{NX}']),
    ("path-tab", [f"ExecStart={NX}\\ty"]), ("path-del", [f"ExecStart={NX}\\x7f"]), ("path-ff", [f"ExecStart={NX}\\xff"]),
    ("path-dq-in", [f'ExecStart={NX}\\"y']), ("path-sq-in", [f"ExecStart={NX}\\'y"]), ("path-h", ["ExecStart=%h/bin/x"]),
    ("path-long-comp", ["ExecStart=/nx/" + "a" * 256 + "/x"]), ("path-name-long", ["ExecStart=" + "a" * 256]),
    ("path-name-dot-x", ["ExecStart=.x"]), ("path-empty-dq", ['ExecStart=""']), ("path-empty-dq-up", ['ExecStart="" up']),
    ("reset-then-cmd", ["ExecStart=/nx/bin/a", "ExecStart=", "ExecStart=/nx/bin/b"]), ("cmd-then-reset", ["ExecStart=/nx/bin/a", "ExecStart="]),
    ("two-simple", ["ExecStart=/nx/bin/a", "ExecStart=/nx/bin/b"]),
    ("two-oneshot", ["ExecStart=/nx/bin/a 1", "ExecStart=/nx/bin/b 2", "Type=oneshot"]),
    ("semi-two", ["ExecStart=/nx/bin/a 1 ; /nx/bin/b 2", "Type=oneshot"]),
    ("dash-badslot-then", ["ExecStart=-/nx/%1/x", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("dash-badslot-arg-then", [f"ExecStart=-{NX} %1 ; /nx/bin/c", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("dash-unsafe-then", ["ExecStart=-/nx/a\\\\b", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("dash-dir-then", ["ExecStart=-/nx/a/", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("dash-rel-then", ["ExecStart=-nx/a", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("dash-unbal-then", ['ExecStart=-/nx/a "b', "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("dash-at-alone-then", ["ExecStart=-@/nx/a", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("dash-empty-then", ["ExecStart=- up", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("semi-first-fails-second-stands", ["ExecStart=/nx/bin/a 1 ; -/nx/%1/x", "ExecStart=/nx/bin/b", "Type=oneshot"]),
    ("semi-dash-second", ["ExecStart=/nx/bin/a ; -/nx/bin/b", "Type=oneshot"]),
    ("at-semi", ["ExecStart=@/nx/bin/a n1 ; @/nx/bin/b n2 x", "Type=oneshot"]),
    ("dash-unknown-esc-path-then", ["ExecStart=-/nx/a\\qb", "ExecStart=/nx/bin/b", "Type=oneshot"]),
]

def esc_text(tok):
    t = tok[2:]
    return "\\" + ESC_TEXT.get(t, t)

def fixtures():
    """(id, kind, lines, layout): kind E (Environment), P (ExecStart path), A (ExecStart argument), F (EnvironmentFile), X (a form);
    layout is normal, template (a t-<id>@.service verified as its @inst instance), eof-nl or eof-nonl (the [Service] lines come
    last in the file, with and without a final newline)."""
    out = []
    for c in TABLE:
        out.append((f"spec-E-{c}", "E", [f"Environment=V=a%{c}b", f"ExecStart={NX}"], "normal"))
        out.append((f"spec-P-{c}", "P", [f"ExecStart=/nx/a%{c}b/bin"], "normal"))
        out.append((f"spec-A-{c}", "A", [f"ExecStart={NX} a%{c}b"], "normal"))
    for c in INST:
        out.append((f"spec-inst-E-{c}", "E", [f"Environment=V=a%{c}b", f"ExecStart={NX}"], "template"))
        out.append((f"spec-inst-P-{c}", "P", [f"ExecStart=/nx/a%{c}b/bin"], "template"))
    out += [("spec-E-pct", "E", ["Environment=V=a%%b", f"ExecStart={NX}"], "normal"), ("spec-P-pct", "P", ["ExecStart=/nx/a%%b/bin"], "normal"),
            ("spec-A-pct", "A", [f"ExecStart={NX} a%%b"], "normal"), ("spec-E-trail", "E", ["Environment=V=a%", f"ExecStart={NX}"], "normal"),
            ("spec-P-trail", "P", ["ExecStart=/nx/a%/bin"], "normal"), ("spec-P-trail2", "P", [f"ExecStart={NX}%"], "normal"),
            ("spec-A-trail", "A", [f"ExecStart={NX} a%"], "normal"), ("spec-E-pctpcth", "E", ["Environment=V=%%h", f"ExecStart={NX}"], "normal"),
            ("spec-E-hh", "E", ["Environment=V=%h%h", f"ExecStart={NX}"], "normal")]
    for c in UNK:
        out.append((f"spec-E-unk-{c}", "E", [f"Environment=A=1 V=a%{c}b C=3", f"ExecStart={NX}"], "normal"))
        out.append((f"spec-P-unk-{c}", "P", [f"ExecStart=/nx/a%{c}b/bin"], "normal"))
        out.append((f"spec-A-unk-{c}", "A", [f"ExecStart={NX} a%{c}b"], "normal"))
    for name, ch in NONALNUM:
        out.append((f"spec-E-nonalnum-{name}", "E", [f"Environment=V=a%{ch}b", f"ExecStart={NX}"], "normal"))
        out.append((f"spec-P-nonalnum-{name}", "P", [f"ExecStart=/nx/a%{ch}b/bin"], "normal"))
        out.append((f"spec-A-nonalnum-{name}", "A", [f"ExecStart={NX} a%{ch}b"], "normal"))
    out += [("spec-E-nonalnum-space", "E", ['Environment=V="a% b"', f"ExecStart={NX}"], "normal"),
            ("spec-E-nonalnum-eq", "E", ["Environment=V=a%=b", f"ExecStart={NX}"], "normal")]
    for fid, rv in [("h", "%h/env"), ("dash-h", "-%h/env"), ("pct", "/nx/%%/env"), ("t", "%t/env"), ("unk", "/nx/%1/env"),
                    ("nonalnum", "/nx/%-/env"), ("quoted", '"%h/env"'), ("trail", "/nx/env%")]:
        out.append((f"spec-F-{fid}", "F", [f"EnvironmentFile={rv}", f"ExecStart={NX}"], "normal"))
    for tok in ESC:
        e = esc_text(tok)
        out.append((f"esc-E-{tok}", "E", [f"Environment=A=1 V=x{e}y C=3", f"ExecStart={NX}"], "normal"))
        out.append((f"esc-Eq-{tok}", "E", [f'Environment=A=1 V="x{e}y" C=3', f"ExecStart={NX}"], "normal"))
        out.append((f"esc-A-{tok}", "A", [f"ExecStart={NX} a{e}b c"], "normal"))
        out.append((f"esc-Aq-{tok}", "A", [f'ExecStart={NX} "a{e}b" c'], "normal"))
        out.append((f"esc-P-{tok}", "P", [f"ExecStart=/nx/a{e}b/bin c"], "normal"))
        out.append((f"esc-Pq-{tok}", "P", [f'ExecStart="/nx/a{e}b/bin" c'], "normal"))
    out += [("esc-Esq-bssq", "E", ["Environment=V='x\\'y'", f"ExecStart={NX}"], "normal"),
            ("esc-Esq-bsdq", "E", ["Environment=V='x\\\"y'", f"ExecStart={NX}"], "normal")]
    out += [("stray-E-cont", "E", ["Environment=A=x\\", "Environment=B=y", f"ExecStart={NX}"], "normal"),
            ("stray-Eq-cont", "E", ['Environment=A="x\\', 'y"', f"ExecStart={NX}"], "normal"),
            ("stray-Eq-bsdq-end", "E", ['Environment=A=1 V="x\\"', f"ExecStart={NX}"], "normal"),
            ("stray-A-cont-install", "A", [f"ExecStart={NX} a\\"], "normal"),
            ("stray-A-eof-nl", "A", [f"ExecStart={NX} a\\"], "eof-nl"),
            ("stray-A-eof-nonl", "A", [f"ExecStart={NX} a\\"], "eof-nonl"),
            ("stray-A-bsbs-end", "A", [f"ExecStart={NX} a\\\\", "Environment=B=y"], "normal"),
            ("stray-P-cont", "P", [f"ExecStart={NX}\\", "up"], "normal")]
    for fid, lines in FORMS:
        out.append((f"form-{fid}", "X", lines, "normal"))
    return out

def fold_fixtures():
    """The fold's own batch (2026-09-19), beyond the lens's set; reported separately."""
    nc, pnc = "\xef\xbf\xbe", "\xf0\x9f\xbf\xbe"                       # U+FFFE and U+1FFFE, raw
    return [("fold-E-rawFFFE", "E", [f"Environment=A=1 V=x{nc}y C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-raw1FFFE", "E", [f"Environment=A=1 V=x{pnc}y C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-rawFDF0", "E", ["Environment=A=1 V=x\xef\xb7\xb0y C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-bsU0001FFFE", "E", ["Environment=A=1 V=x\\U0001FFFEy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-bsU0001FFFD", "E", ["Environment=A=1 V=x\\U0001FFFDy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-bsuFDF0", "E", ["Environment=A=1 V=x\\uFDF0y C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-pct-nonascii", "E", ["Environment=V=a%\xc3\xa9b", f"ExecStart={NX}"], "normal"),
            ("fold-E-eof-nl", "E", [f"ExecStart={NX}", "Environment=V=x\\"], "eof-nl"),
            ("fold-A-quoted-trailing-bs", "A", [f'ExecStart={NX} "a\\'], "normal"),
            ("fold-X-dash-quoted-trailing-bs-then", "X", [f'ExecStart=-{NX} "a\\', "ExecStart=/nx/bin/b", "Type=oneshot"], "normal"),
            # the fold's addendum (2026-09-19): the accepted side of each refused range, the last plane's noncharacters, the 255-byte
            # boundary from the accepted side, and the continuation shapes a comment, a blank or a whitespace-only line follows
            ("fold-E-raw10FFFE", "E", ["Environment=A=1 V=x\xf4\x8f\xbf\xbey C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-rawBFFFF", "E", ["Environment=A=1 V=x\xf2\xaf\xbf\xbfy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-raw10FFFD", "E", ["Environment=A=1 V=x\xf4\x8f\xbf\xbdy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-rawFDCF", "E", ["Environment=A=1 V=x\xef\xb7\x8fy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-bsuFDCF", "E", ["Environment=A=1 V=x\\uFDCFy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-bsuD7FF", "E", ["Environment=A=1 V=x\\uD7FFy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-bsU0010FFFE", "E", ["Environment=A=1 V=x\\U0010FFFEy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-bsU0010FFFD", "E", ["Environment=A=1 V=x\\U0010FFFDy C=3", f"ExecStart={NX}"], "normal"),
            ("fold-E-cont-comment-eof-nl", "E", [f"ExecStart={NX}", "Environment=V=x\\", "# c", "; d"], "eof-nl"),
            ("fold-E-cont-comment-eof-nonl", "E", [f"ExecStart={NX}", "Environment=V=x\\", "# c"], "eof-nonl"),
            ("fold-E-cont-blank-install", "E", [f"ExecStart={NX}", "Environment=V=x\\"], "normal"),
            ("fold-E-cont-ws-text", "E", [f"ExecStart={NX}", "Environment=V=x\\", " \t ", "Environment=W=y"], "normal"),
            ("fold-E-cont-comment-blank-text", "E", [f"ExecStart={NX}", "Environment=V=x\\", "# c", "", "Environment=W=y"], "normal"),
            ("fold-E-cont-comment-text", "E", [f"ExecStart={NX}", "Environment=V=x\\", "# c", "Environment=W=y"], "normal"),
            ("fold-E-cont-quoted-blank", "E", [f"ExecStart={NX}", 'Environment=V="x\\', "", "Environment=W=y"], "normal"),
            ("fold-X-path-name-255", "X", ["ExecStart=" + "a" * 255], "normal"),
            ("fold-X-path-comp-255", "X", ["ExecStart=/nx/" + "a" * 255 + "/x"], "normal"),
            # the round-5 preface (2026-09-19): the EnvironmentFile forms path_simplify_and_warn changes, which systemd reads as the
            # simplified path (the oracle raised on them as not modelled until it modelled the simplification), and a .. component left
            # after simplifying, which systemd ignores as not normalized (no file)
            ("fold-F-dslash", "F", ["EnvironmentFile=-/x//y/env", f"ExecStart={NX}"], "normal"),
            ("fold-F-dotseg", "F", ["EnvironmentFile=/x/./env", f"ExecStart={NX}"], "normal"),
            ("fold-F-trail", "F", ["EnvironmentFile=/x/env/", f"ExecStart={NX}"], "normal"),
            ("fold-F-trail-dash", "F", ["EnvironmentFile=-/x/env/", f"ExecStart={NX}"], "normal"),
            ("fold-F-dot-end", "F", ["EnvironmentFile=/x/env/.", f"ExecStart={NX}"], "normal"),
            ("fold-F-droot", "F", ["EnvironmentFile=//", f"ExecStart={NX}"], "normal"),
            ("fold-F-dotdot", "F", ["EnvironmentFile=/x/../env", f"ExecStart={NX}"], "normal"),
            ("fold-F-dotdot-mid", "F", ["EnvironmentFile=-/x/y/../env", f"ExecStart={NX}"], "normal"),
            # round 6 of fork PR #778 (correctness-1, extra5-1): the UTF-8 byte order mark. systemd's config_parse tests a line for a comment,
            # then strips the FIRST mark it meets at the raw start of a line, wherever in the file, and never another (one latch per file).
            # Both sides, each run against 255.4 by hand before it was written here: the mark before line 1, before [Service], before an
            # ExecStart line and before an Environment line load whole (four); a marked comment is no comment and spends the latch, so a
            # marked ExecStart after it keeps its mark (an unknown key name, no ExecStart, refused); a second mark, a mark alone before a
            # marked line and a mark after a tab are text (refused); a marked comment ending in a backslash joins the next line (refused);
            # a mark alone closes an open continuation as a blank does (loads); a mark after a blank on a comment-like line is text and
            # spends nothing (loads). The oracle and the reader in bin/romp-service stripped line 1's alone.
            ("fold-bom-first", "X", [f"ExecStart={NX}", "Environment=A=1"], "bom-first"),
            ("fold-bom-service", "X", [f"ExecStart={NX}", "Environment=A=1"], "bom-service"),
            ("fold-bom-exec", "X", [BOM + f"ExecStart={NX}", "Environment=A=1"], "normal"),
            ("fold-bom-env", "E", [f"ExecStart={NX}", BOM + "Environment=A=1"], "normal"),
            ("fold-bom-comment-then-exec", "X", [BOM + "# c", BOM + f"ExecStart={NX}"], "normal"),
            ("fold-bom-twice", "X", [BOM + f"ExecStart={NX}"], "bom-first"),
            ("fold-bom-alone-then-exec", "X", [BOM, BOM + f"ExecStart={NX}"], "normal"),
            ("fold-bom-after-tab", "X", ["\t" + BOM + f"ExecStart={NX}"], "normal"),
            ("fold-bom-comment-cont", "X", [BOM + "# c\\", f"ExecStart={NX}"], "normal"),
            ("fold-bom-cont-alone", "E", ["Environment=V=x\\", BOM, f"ExecStart={NX}"], "normal"),
            ("fold-bom-ws-comment", "X", [" " + BOM + "# c", f"ExecStart={NX}"], "normal"),
            # the round-6 addendum (the lens over the round-6 commit named the shapes it had run by hand and found unpinned): the mark
            # beside a CRLF line ending (before line 1, before a kept line, alone on a line closing a continuation, before [Service]); before
            # the lines the reader keeps or replays (PATH, EnvironmentFile, and Restart where the marked line decides the load: Type=oneshot
            # with Restart=always refused unless the marked Restart=on-failure is read, so the pair below has the latch free and spent);
            # before an indented, a quoted and a trailing-blank kept line; a marked empty Environment= reset; a marked whitespace-only line,
            # plain and closing a continuation; two marks on one line (the second is text: an unknown key); a marked second ExecStart with
            # the latch spent (text to systemd, the first stands); a marked empty ExecStart= reset before the real line; a mark in the
            # middle of a line (in a value, carried; before a name, no assignment; before the ExecStart path, not absolute, refused; inside
            # the [Service] name, an unknown section, so no ExecStart, refused); and a continuation closed by a line holding only a second
            # mark, the latch spent by line 1, which systemd joins (the mark a word it drops) and the reader in bin/romp-service refuses
            # under its refusal 3, the safe direction. Each run against 255.4 through this harness before it was written here.
            ("fold-bom-crlf-first", "X", [f"ExecStart={NX}", "Environment=A=1"], "crlf-bom-first"),
            ("fold-bom-crlf-env", "E", [f"ExecStart={NX}", BOM + "Environment=A=1"], "crlf"),
            ("fold-bom-crlf-cont-alone", "E", ["Environment=V=x\\", BOM, f"ExecStart={NX}"], "crlf"),
            ("fold-bom-crlf-service", "X", [f"ExecStart={NX}", "Environment=A=1"], "crlf-bom-service"),
            ("fold-bom-path", "E", [f"ExecStart={NX}", BOM + "Environment=PATH=/x/bin:/usr/bin"], "normal"),
            ("fold-bom-envfile", "F", [f"ExecStart={NX}", BOM + "EnvironmentFile=-/x/env"], "normal"),
            ("fold-bom-restart-read", "X", ["ExecStart=/nx/bin/a", "ExecStart=/nx/bin/b", "Type=oneshot", "Restart=always", BOM + "Restart=on-failure"], "normal"),
            ("fold-bom-restart-spent", "X", ["ExecStart=/nx/bin/a", "ExecStart=/nx/bin/b", "Type=oneshot", "Restart=always", BOM + "Restart=on-failure"], "bom-first"),
            ("fold-bom-indented", "E", [f"ExecStart={NX}", BOM + "  Environment=A=1"], "normal"),
            ("fold-bom-quoted", "E", [f"ExecStart={NX}", BOM + 'Environment="A=a b"'], "normal"),
            ("fold-bom-trailing-ws", "E", [f"ExecStart={NX}", BOM + "Environment=A=1  \t"], "normal"),
            ("fold-bom-env-reset", "E", [f"ExecStart={NX}", "Environment=A=1", BOM + "Environment="], "normal"),
            ("fold-bom-ws-only", "E", [f"ExecStart={NX}", BOM + "  \t", "Environment=A=1"], "normal"),
            ("fold-bom-ws-only-cont", "E", [f"ExecStart={NX}", "Environment=V=x\\", BOM + "  ", "Environment=W=y"], "normal"),
            ("fold-bom-double", "E", [BOM + BOM + "Environment=A=1", f"ExecStart={NX}"], "normal"),
            ("fold-bom-second-exec-spent", "X", ["ExecStart=/nx/bin/a", BOM + "ExecStart=/nx/bin/b"], "bom-first"),
            ("fold-bom-exec-reset-then", "X", [BOM + "ExecStart=", f"ExecStart={NX}"], "normal"),
            ("fold-bom-mid-value", "E", [f"ExecStart={NX}", "Environment=A=a" + BOM + "b"], "normal"),
            ("fold-bom-mid-name", "E", [f"ExecStart={NX}", "Environment=" + BOM + "A=1"], "normal"),
            ("fold-bom-mid-exec-path", "X", ["ExecStart=" + BOM + NX], "normal"),
            ("fold-bom-in-section", "X", [f"ExecStart={NX}", "Environment=A=1"], "bom-in-service"),
            ("fold-bom-cont-second-mark", "E", ["Environment=V=x\\", BOM, f"ExecStart={NX}"], "bom-first"),
            # round 6 (extra5-2): service_verify refuses Restart=always or on-success beside Type=oneshot; a later Restart= replaces an earlier
            # one when its value is in the table, and an empty or unknown value is Failed to parse service restart specifier, ignoring, so the
            # earlier value stands (verified on 255.4). The oracle read a command list from the refused shape until this commit.
            ("fold-restart-oneshot-always", "X", ["ExecStart=/nx/bin/a", "ExecStart=/nx/bin/b", "Type=oneshot", "Restart=always"], "normal"),
            ("fold-restart-oneshot-on-success", "X", ["ExecStart=/nx/bin/a", "Type=oneshot", "Restart=on-success"], "normal"),
            ("fold-restart-oneshot-on-failure", "X", ["ExecStart=/nx/bin/a", "ExecStart=/nx/bin/b", "Type=oneshot", "Restart=always", "Restart=on-failure"], "normal"),
            ("fold-restart-oneshot-empty", "X", ["ExecStart=/nx/bin/a", "Type=oneshot", "Restart=always", "Restart="], "normal"),
            ("fold-restart-oneshot-unknown", "X", ["ExecStart=/nx/bin/a", "Restart=always", "Restart=bogus", "Type=oneshot"], "normal"),
            ("fold-restart-simple-always", "X", ["ExecStart=/nx/bin/a", "Restart=always"], "normal")]

CLASSES = [
    ("A", re.compile(r"^spec-(E|P|A|F)-nonalnum|^spec-P-trail$")),
    ("B", re.compile(r"^spec-[EPA]-unk-[crR]$")),
    ("C", re.compile(r"^esc-Eq?-bsu(FFFE|FFFF|FDD0|FDEF)$")),
    ("D", re.compile(r"^esc-.*-bsU0000(D800|DFFF|FFFF|FDEF|FDD5|FFFE|FDD0)$")),
    ("E", re.compile(r"^stray-A-eof-")),
    ("F", re.compile(r"^form-(pre-at|pre-at-alone|pre-dashat|pre-atdash|pre-dashat-alone|dash-at-alone-then|at-semi)$")),
    ("G", re.compile(r"^form-pre-(bangbangbang|dashdash|atat|plusbang|bangplus|coloncolon|plusplus|all)$")),
    ("H", re.compile(r"^form-sep-semi-(quoted|sq|bs)$")),
    ("I", re.compile(r"^form-path-(dot|dotdot|long-comp|name-long)$")),
    ("J", re.compile(r"^form-path-(dslash|dotseg|dslash-args)$")),
    ("K", re.compile(r"^form-(dash-(badslot|badslot-arg|unsafe|dir|rel|unbal|unknown-esc-path)-then|semi-first-fails-second-stands)$")),
]
def klass(fid):
    for k, rx in CLASSES:
        if rx.search(fid): return k
    return "-"

# ---- systemd ------------------------------------------------------------------------------------------------------
BOM = "\xef\xbb\xbf"     # the UTF-8 byte order mark, as latin-1 text (the fixture files are written latin-1, byte for byte)

def unit_text(lines, layout):
    if layout == "crlf" or layout.startswith("crlf-"):                     # the whole file with CRLF line endings, over any layout below (the
        return unit_text(lines, layout[5:] or "normal").replace("\n", "\r\n")   # round-6 addendum of fork PR #778: a mark beside a CR)
    body = "\n".join(lines)
    if layout.startswith("eof"):
        t = "[Unit]\nDescription=f\n\n[Install]\nWantedBy=default.target\n\n[Service]\n" + body
        return t + ("\n" if layout == "eof-nl" else "")
    t = "[Unit]\nDescription=f\n\n[Service]\n" + body + "\n\n[Install]\nWantedBy=default.target\n"
    if layout == "bom-first": return BOM + t                              # the mark before line 1
    if layout == "bom-service": return t.replace("[Service]", BOM + "[Service]", 1)   # the mark before the [Service] header on a later line
    if layout == "bom-in-service": return t.replace("[Service]", "[Ser" + BOM + "vice]", 1)   # the mark inside the header's name
    return t

def unquote_cmdline(s):
    """quote_command_line(argv, SHELL_ESCAPE_EMPTY) undone: words on spaces; a word in double quotes carries \\a \\b \\f \\n \\r \\t
    \\v, \\NNN octal and a backslash before one of \" \\ $ `; an empty word is \"\"."""
    words, i, n = [], 0, len(s)
    esc = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
    while i < n:
        while i < n and s[i] == " ": i += 1
        if i >= n: break
        if s[i] == '"':
            i += 1; w = ""
            while i < n and s[i] != '"':
                c = s[i]
                if c == "\\" and i + 1 < n:
                    d = s[i + 1]
                    if d in esc: w += esc[d]; i += 2; continue
                    if re.fullmatch(r"[0-7]{3}", s[i + 1:i + 4]): w += chr(int(s[i + 1:i + 4], 8)); i += 4; continue
                    w += d; i += 2; continue
                w += c; i += 1
            i += 1; words.append(w)
        else:
            j = i
            while j < n and s[j] != " ": j += 1
            words.append(s[i:j]); i = j
    return words

LOGLINE = re.compile(r"^(\S+\.service: |/\S+:\d+: |Sent message|Got message|Found |Loaded |Skipping|Bus |Hostname|Bringing|Successfully|Installed|Unit \S+ was not|Configuration|Loading|Set up|Looking|\[)")

def run_systemd(root, path, verified_name):
    env = {"HOME": os.path.join(root, "home"), "XDG_RUNTIME_DIR": os.path.join(root, "rt"),
           "SYSTEMD_UNIT_PATH": os.path.join(root, "cases"), "SYSTEMD_LOG_LEVEL": "debug", "PATH": "/usr/bin:/bin"}
    r = subprocess.run(["systemd-analyze", "--user", "--man=no", "verify", verified_name], env=env, capture_output=True, cwd=root)
    text = (r.stdout + r.stderr).decode("latin-1")
    stem = os.path.basename(verified_name)[:-len(".service")]
    res = {"fatal": False, "env": {}, "envfiles": [], "cmds": [], "path": None, "notes": []}
    lines = text.split("\n"); i = 0
    while i < len(lines):
        l = lines[i]
        m = re.match(r"^\t\tEnvironment: (.*)$", l)
        if m:
            v = m.group(1); j = i + 1
            while j < len(lines) and not lines[j].startswith("\t") and not LOGLINE.match(lines[j]):   # a raw newline in the value
                v += "\n" + lines[j]; j += 1
            k, _, val = v.partition("=")
            res["env"][k] = val; i = j; continue
        m = re.match(r"^\t\tEnvironmentFile: (.*)$", l)
        if m: res["envfiles"].append(m.group(1))
        m = re.match(r"^\t\t\tCommand Line: (.*)$", l)
        if m: res["cmds"].append(unquote_cmdline(m.group(1)))
        i += 1
    m = re.search(re.escape(stem) + r"\.service: Command (.*?) is not executable: ", text)
    if m: res["path"] = m.group(1)
    for l in lines:
        m = re.match(r"^/\S+\.service:\d+: (.*)$", l) or re.match(r"^" + re.escape(stem) + r"\.service: ((?!Creating|Trying|Installed|Enqueued|Command ).*)$", l)
        if m and not m.group(1).startswith("Unknown key"): res["notes"].append(m.group(1))
    res["fatal"] = "has a bad unit file setting" in text or "Failed to load configuration" in text
    return res

# ---- the oracle ---------------------------------------------------------------------------------------------------
def extract_oracle(root):
    s = open(BATS, encoding="latin-1").read()
    start = s.index("cat > \"$py\" <<'PY'\n") + len("cat > \"$py\" <<'PY'\n")
    end = s.index("\nPY\n", start) + 1
    p = os.path.join(root, "sd.py")
    open(p, "w", encoding="latin-1").write(s[start:end])
    return p

def run_oracle(root, sd, path):
    env = {"HOME": os.path.join(root, "home"), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([sys.executable, sd, path, "dump"], env=env, capture_output=True)
    if r.returncode != 0:
        err = r.stderr.decode("latin-1").strip().splitlines()
        return {"refuses": err[-1] if err else "exit %d" % r.returncode}
    out = r.stdout.decode("latin-1").rstrip("\n")
    if out.startswith("ERROR: "): return {"fatal": out[7:]}
    d = json.loads(out)
    return {"fatal": None, "env": d["env"], "execs": d["execs"], "envfiles": [f["prefix"] + f["path"] for f in d["envfiles"]]}

# ---- the comparison -----------------------------------------------------------------------------------------------
def compare(kind, sd, orc):
    """(verdict, detail, dangerous): verdict in agree / agree (both refuse) / REFUSES / DISAGREE; dangerous when the oracle reports
    what systemd does not set, run or read: a value systemd leaves unset or sets to something else, a unit systemd fails to load, a
    command systemd does not run (as many commands as systemd's or more with a difference among them, fewer with one not among
    systemd's, or a first command that is not systemd's first), another exec->path for the first command (positional: systemd prints
    its first command's resolved path alone), a file systemd does not read (as many EnvironmentFile paths or more with a difference,
    or fewer with one not among systemd's). The oracle refusing what systemd loads, or leaving unset what systemd sets, or listing
    fewer commands or files, every one among systemd's with the first command kept, is unmarked (the module docstring says which of
    those is a false refusal and which the D4 class where the reader follows it). The round-5 preface of fork PR #778 added the
    both-set and same-count shapes; its addendum the shorter list carrying one systemd does not run or read (the lens's example: the
    oracle reporting one command with another argument where systemd runs two; the count test alone left it unmarked); round 6 the
    first-command shape by name (extra6-2: the exec->path branch marked it by accident, and the prose placed it on the unmarked side)
    and the loud skip: when systemd printed no exec->path (the executable check is skipped for a first command under the - prefix)
    the field is uncompared and the row is REFUSES with the reason, where it was agree (extra6-1); a DISAGREE elsewhere on the row
    still wins."""
    if "refuses" in orc: return "REFUSES", orc["refuses"], False
    if sd["fatal"] and orc["fatal"] is not None: return "agree (both refuse)", "", False
    if sd["fatal"]: return "DISAGREE", "systemd refuses the unit (%s); the oracle loads it" % "; ".join(sd["notes"])[:200], True
    if orc["fatal"] is not None: return "DISAGREE", "the oracle refuses (%s); systemd loads the unit" % orc["fatal"], False
    diffs, dangerous, unread = [], False, ""
    if sd["env"] != orc["env"]:
        for k in sorted(set(sd["env"]) | set(orc["env"])):
            a, b = sd["env"].get(k), orc["env"].get(k)
            if a != b:
                diffs.append("%s: systemd %s, oracle %s" % (k, "unset" if a is None else repr(a), "unset" if b is None else repr(b)))
                if b is not None: dangerous = True      # the oracle sets what systemd leaves unset, or sets another value
    sd_cmds, orc_cmds = sd["cmds"], [c["argv"] for c in orc["execs"]]
    if sd_cmds != orc_cmds:
        diffs.append("argv: systemd %r, oracle %r" % (sd_cmds, orc_cmds))
        # more commands than systemd runs, as many with other words, fewer with one systemd does not run, or a first command that is not
        # systemd's first (the reader's identity check reads the first command: an oracle that drops it names a manager the service does
        # not start first); a shorter list is unmarked only while every command is among systemd's AND the first is systemd's first
        if len(orc_cmds) >= len(sd_cmds) or any(c not in sd_cmds for c in orc_cmds) or (orc_cmds and orc_cmds[0] != sd_cmds[0]): dangerous = True
    if orc["execs"]:
        if sd["path"] is None:
            # systemd prints a resolved path only in verify's executable check, and only for the first command; the - prefix downgrades that
            # command's errors and the check is skipped, so nothing is there to compare: said, not agreed (a DISAGREE elsewhere on the row wins)
            unread = "exec->path uncompared: systemd printed no resolved path for its first command (%s), so the oracle's %r stands unchecked" % (
                "its errors are downgraded by the - prefix, which skips the executable check that prints it" if orc["execs"][0].get("ignore") else "the executable check printed none", orc["execs"][0]["path"])
        elif orc["execs"][0]["path"] != sd["path"]:
            diffs.append("exec->path: systemd %r, oracle %r" % (sd["path"], orc["execs"][0]["path"]))
            dangerous = True                                   # a path systemd does not run first (positional: the one path systemd prints)
    if sd["envfiles"] != orc["envfiles"]:
        diffs.append("EnvironmentFile: systemd %r, oracle %r" % (sd["envfiles"], orc["envfiles"]))
        if len(orc["envfiles"]) >= len(sd["envfiles"]) or any(f not in sd["envfiles"] for f in orc["envfiles"]): dangerous = True   # more files than systemd reads, as many with another path, or fewer with one systemd does not read
    if diffs: return "DISAGREE", "; ".join(diffs + ([unread] if unread else [])), dangerous   # the DISAGREE wins the verdict; the unread
                                                                                              # field is still said (the round-6 addendum)
    if unread: return "REFUSES", unread, False
    return "agree", "", False

# ---- the mark's self-check: synthetic pairs on both sides of every shape ------------------------------------------------------------
def _sd(fatal=False, env=None, cmds=None, path="/nx/bin/x", envfiles=None, notes=None):
    return {"fatal": fatal, "env": env or {}, "envfiles": envfiles or [], "cmds": [["/nx/bin/x"]] if cmds is None else cmds, "path": path, "notes": notes or []}
def _orc(fatal=None, env=None, execs=None, envfiles=None):
    if execs is None: execs = [{"path": "/nx/bin/x", "argv": ["/nx/bin/x"], "ignore": False}]
    return {"fatal": fatal, "env": env or {}, "execs": execs, "envfiles": envfiles or []}
def _ex(path, *argv, ignore=False):
    return {"path": path, "argv": list(argv) or [path], "ignore": ignore}
MARK_CASES = [   # (name, systemd's reading, the oracle's, the verdict, dangerous): one pair on each side of every shape the column marks, the
                 # fatal shapes, the not-modelled row and the loud skip (round 6 of fork PR #778, tests-2: no real fixture at an agreeing
                 # head reaches the mark, so a dead mark printed the same table; this table is what shows it fires, and where it must not)
    ("env both set and different", _sd(env={"A": "1"}), _orc(env={"A": "2"}), "DISAGREE", True),
    ("env set by the oracle alone", _sd(), _orc(env={"A": "1"}), "DISAGREE", True),
    ("env set by systemd alone (the D4 class where the reader follows it; unmarked, see the docstring)", _sd(env={"A": "1"}), _orc(), "DISAGREE", False),
    # the round-6 addendum: the per-key guard (a key equal on both sides beside one systemd alone sets stays unmarked; without the guard the
    # equal key's own compare would mark the row), and an agree with a nonempty env
    ("env systemd sets A and B, the oracle A alone (one key equal, one systemd-only; unmarked)", _sd(env={"A": "1", "B": "2"}), _orc(env={"A": "1"}), "DISAGREE", False),
    ("env both set and equal", _sd(env={"A": "1"}), _orc(env={"A": "1"}), "agree", False),
    ("argv same count, other words", _sd(cmds=[["/nx/bin/x", "up"]]), _orc(execs=[_ex("/nx/bin/x", "/nx/bin/x", "down")]), "DISAGREE", True),
    ("argv more commands than systemd runs", _sd(cmds=[["/nx/bin/a"]], path="/nx/bin/a"), _orc(execs=[_ex("/nx/bin/a"), _ex("/nx/bin/b")]), "DISAGREE", True),
    ("argv fewer, one systemd does not run", _sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path="/nx/bin/a"), _orc(execs=[_ex("/nx/bin/c")]), "DISAGREE", True),
    ("argv fewer, systemd's first dropped (the second reported first)", _sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path="/nx/bin/a"), _orc(execs=[_ex("/nx/bin/b")]), "DISAGREE", True),
    ("argv fewer, every one among systemd's, the first kept", _sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path="/nx/bin/a"), _orc(execs=[_ex("/nx/bin/a")]), "DISAGREE", False),
    # the round-6 addendum: the first-command clause on its own, where the exec->path branch cannot mark (the path uncompared under the -
    # prefix); the row above it is marked by that branch whether the clause exists or not
    ("argv fewer, systemd's first dropped, the path uncompared under -", _sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path=None), _orc(execs=[_ex("/nx/bin/b", "/nx/bin/b", ignore=True)]), "DISAGREE", True),
    ("exec->path another path, argv equal", _sd(), _orc(execs=[_ex("/nx//bin/x", "/nx/bin/x")]), "DISAGREE", True),
    # the round-6 addendum: the compare is positional, systemd's first command's path against the oracle's first; an identity compare (any
    # oracle command carrying systemd's path) would read this row as agree
    ("exec->path: the oracle's first resolves elsewhere while a later oracle command carries systemd's path (positional: marked)", _sd(cmds=[["/nx/bin/a"], ["/nx/bin/b"]], path="/nx/bin/b"), _orc(execs=[_ex("/nx/bin/a"), _ex("/nx/bin/b")]), "DISAGREE", True),
    ("exec->path equal", _sd(), _orc(), "agree", False),
    ("exec->path uncompared under the - prefix (the loud skip)", _sd(path=None), _orc(execs=[_ex("/nx/bin/x", "/nx/bin/x", ignore=True)]), "REFUSES", False),
    ("exec->path uncompared, but a DISAGREE elsewhere on the row wins", _sd(path=None, env={"A": "1"}), _orc(env={"A": "2"}, execs=[_ex("/nx/bin/x", "/nx/bin/x", ignore=True)]), "DISAGREE", True),
    ("EnvironmentFile same count, another path", _sd(envfiles=["/x/env"]), _orc(envfiles=["/y/env"]), "DISAGREE", True),
    ("EnvironmentFile more files than systemd reads", _sd(envfiles=["/x/env"]), _orc(envfiles=["/x/env", "/y/env"]), "DISAGREE", True),
    ("EnvironmentFile fewer, one systemd does not read", _sd(envfiles=["/x/env", "/y/env"]), _orc(envfiles=["/z/env"]), "DISAGREE", True),
    ("EnvironmentFile fewer, every one among systemd's (the D4 class where the reader follows it; unmarked)", _sd(envfiles=["/x/env", "/y/env"]), _orc(envfiles=["/x/env"]), "DISAGREE", False),
    # the round-6 addendum: the first-kept rule is the argv branch's alone (the reader's identity check reads the first command and no
    # first file), so a dropped FIRST file with a later one kept is the same unmarked D4 class; the prose says "first command" for that
    ("EnvironmentFile fewer, systemd's first file dropped, a later one kept (unmarked: no first-file rule)", _sd(envfiles=["/x/env", "/y/env"]), _orc(envfiles=["/y/env"]), "DISAGREE", False),
    ("systemd refuses, the oracle loads", _sd(fatal=True, notes=["bad"]), _orc(), "DISAGREE", True),
    ("the oracle refuses, systemd loads (a false refusal)", _sd(), _orc(fatal="Refusing"), "DISAGREE", False),
    ("both refuse", _sd(fatal=True), _orc(fatal="Refusing"), "agree (both refuse)", False),
    ("the oracle does not model the form", _sd(), {"refuses": "NotImplementedError: not modelled"}, "REFUSES", False),
]

def self_check(out=sys.stdout):
    """Every MARK_CASES pair against compare(): 0 and one printed line when all agree, 1 and the mismatches otherwise."""
    bad = []
    for name, sd, orc, verdict, dangerous in MARK_CASES:
        got = compare("X", sd, orc)
        if got[0] != verdict or got[2] != dangerous: bad.append("  %s: wanted (%s, dangerous=%s), got (%s, dangerous=%s)" % (name, verdict, dangerous, got[0], got[2]))
    marked = sum(1 for c in MARK_CASES if c[4]); unmarked = sum(1 for c in MARK_CASES if c[3] == "DISAGREE" and not c[4])
    print("mark self-check: %d of %d synthetic pairs as expected (%d on the dangerous side, %d DISAGREE unmarked, %d agree, refuse or unread)" % (
        len(MARK_CASES) - len(bad), len(MARK_CASES), marked, unmarked, len(MARK_CASES) - marked - unmarked), file=out)
    if bad:
        print("mark self-check FAILED: compare() does not mark as the table says", file=out)
        for b in bad: print(b, file=out)
        return 1
    return 0

def main():
    fx, fold = fixtures(), fold_fixtures()
    if "--list" in sys.argv:
        for fid, kind, lines, layout in fx + fold:
            print("%s\t%s\t%s\t%s" % (fid, kind, layout, " [nl] ".join(lines).replace(BOM, "<BOM>")))
        return 0
    if self_check() != 0: return 1                          # before the systemd check: the table needs no systemd, and a dead mark is a defect here
    if shutil.which("systemd-analyze") is None:
        print("romp-service-differential: systemd-analyze is not on PATH; this recipe compares the oracle against a real systemd and cannot run without one (it does not skip)", file=sys.stderr)
        return 2
    version = subprocess.run(["systemd-analyze", "--version"], capture_output=True, text=True).stdout.splitlines()[0].strip()
    root = tempfile.mkdtemp(prefix="romp-sd-diff-")
    try:
        cases = os.path.join(root, "cases")
        os.makedirs(cases); os.makedirs(os.path.join(root, "home")); os.makedirs(os.path.join(root, "rt"), mode=0o700)
        for stub in ("basic.target", "shutdown.target", "default.target"):
            open(os.path.join(cases, stub), "w").write("[Unit]\nDescription=stub\n")
        sd = extract_oracle(root)
        jobs = []
        for fid, kind, lines, layout in fx + fold:
            fname = ("t-%s@.service" % fid) if layout == "template" else ("%s.service" % fid)
            path = os.path.join(cases, fname)
            open(path, "w", encoding="latin-1").write(unit_text(lines, layout))
            verified = ("t-%s@inst.service" % fid) if layout == "template" else path
            jobs.append((fid, kind, path, verified))
        def one(job):
            fid, kind, path, verified = job
            return fid, kind, run_systemd(root, path, verified), run_oracle(root, sd, path)
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(one, jobs))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    per = {}
    rows = []
    lens_ids = {f[0] for f in fx}
    for fid, kind, sdr, orc in results:
        verdict, detail, dangerous = compare(kind, sdr, orc)
        rows.append((fid, verdict, detail, dangerous))
        bucket = klass(fid) if fid in lens_ids else "fold"
        c = per.setdefault(bucket, {"cases": 0, "agree": 0, "refuses": 0, "disagree": 0, "dangerous": 0})
        c["cases"] += 1
        c["agree" if verdict.startswith("agree") else "refuses" if verdict == "REFUSES" else "disagree"] += 1
        c["dangerous"] += int(dangerous)
    print("systemd-analyze on this box: %s" % version)
    print("recipe written against:      %s%s" % (WRITTEN_AGAINST, "" if version == WRITTEN_AGAINST else "   (a different build: the counts below are a reading of this box's systemd, not of the one the expected counts name)"))
    print("fixtures: %d (the round-4 oracle lens's set) + %d (the fold's batch, counted apart)" % (len(fx), len(fold)))
    print("%-6s %6s %6s %8s %9s %10s" % ("class", "cases", "agree", "REFUSES", "DISAGREE", "dangerous"))
    order = [k for k, _ in CLASSES] + ["-"]
    tot = {"cases": 0, "agree": 0, "refuses": 0, "disagree": 0, "dangerous": 0}
    for k in order:
        c = per.get(k)
        if not c: continue
        print("%-6s %6d %6d %8d %9d %10d" % ("(none)" if k == "-" else k, c["cases"], c["agree"], c["refuses"], c["disagree"], c["dangerous"]))
        for key in tot: tot[key] += c[key]
    print("%-6s %6d %6d %8d %9d %10d" % ("total", tot["cases"], tot["agree"], tot["refuses"], tot["disagree"], tot["dangerous"]))
    f = per.get("fold", {"cases": 0, "agree": 0, "refuses": 0, "disagree": 0, "dangerous": 0})
    print("fold batch: %d cases, %d agree, %d REFUSES, %d DISAGREE, %d dangerous" % (f["cases"], f["agree"], f["refuses"], f["disagree"], f["dangerous"]))
    print("dangerous = a disagreement where the oracle reports what systemd does not set, run or read (a value unset or other to systemd, a unit it fails to load, as many commands or files or more with a difference, fewer with one systemd does not run or read or with a first command that is not systemd's first, another exec->path for the first command); unmarked = the oracle refusing what systemd loads (a false refusal), or leaving unset or listing fewer commands with the first command kept or fewer files every one among systemd's (the D4 class where the reader follows it: it writes this clone's value or omits the line, at exit 0)")
    print_rows(rows)
    return 0

def print_rows(rows, out=sys.stdout):
    """The rows under the table, the ones an operator reads: every DISAGREE with its detail, then every REFUSES whose reason is an exec->path
    this harness could not compare, under its own heading with the reason (the round-6 addendum of fork PR #778: compare() said it and main
    printed DISAGREE rows alone, so the six uncompared fixtures sat in the REFUSES column beside the not-modelled rows with nothing in the
    output to tell them apart, and tests/README.md named them as listed from a run that listed none). The not-modelled REFUSES rows stay
    counted, not listed: their reason is one line of the oracle's, the same for all."""
    bad = [r for r in rows if r[1] == "DISAGREE"]
    if bad:
        print("disagreements:", file=out)
        for fid, verdict, detail, dangerous in bad:
            print("  %s%s: %s" % (fid, " [dangerous]" if dangerous else "", detail), file=out)
    unread = [r for r in rows if r[1] == "REFUSES" and r[2].startswith("exec->path uncompared")]
    if unread:
        print("uncompared (REFUSES with the reason, never agree: systemd printed no exec->path for the row's first command):", file=out)
        for fid, verdict, detail, dangerous in unread:
            print("  %s: %s" % (fid, detail), file=out)

if __name__ == "__main__":
    sys.exit(main())
