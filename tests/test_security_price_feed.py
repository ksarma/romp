#!/usr/bin/env python3
"""SECURITY.md's Network access section names the price feed's off switch, and the code agrees (2026-09-20).

SECURITY.md is the document a reader checking what leaves the machine opens, and its Network access
section is the one place outside docs/reference.md that names the model-price fetch. The switch that
stops that fetch, ROMP_PRICE_FEED=off (kernel/kernel.py _price_feed_off, the first statement of
_refresh_remote_prices, the one place a fetch can start), was documented in the reference alone, so a
reader of SECURITY.md saw the request with no way to stop it. The section now names the switch, where
the service reads it, what the reader then sees (the Token usage modal's line and /version's priceFeed
block) and links the reference's subsection. Nothing but text ties the section to the code, so these
pins hold it there: the variable it names is the one the kernel reads, the /version key and the modal's
line are the ones the code emits, the link's target heading exists, and the section carries no em or en
dash and not the word the repo's CLAUDE.md bans.

The review of PR 878 (2026-09-21) found the section's first sentence, that romp makes one outbound request
by default, false by the code: with the price feed off and nothing configured the kernel's own Models API
catalog refresh and the release check's `git ls-remote` still run, so the switch hung under a promise the
section could not keep. The sentence is now the one a derivation over kernel/, cli/, postal/, bin/ and ui/
supports (one connection of the kernel's own to a host other than the model provider by default, the price
feed's), the section names the kernel's other default connections and the programs it runs with the switch
that gates each, the roads that open once set up, and that what a program the kernel starts sends is that
program's; the telemetry sentence is scoped to what the table supports (session text goes to the model
provider and, encrypted, to a subscribed phone's push service). TheSectionScopesItsClaimToWhatTheCodeDoes
pins that positively, phrase by phrase, and ties each named switch to the variable the kernel reads. Those
cases are red over a git archive of the reviewed head d1026b768 at their first SECURITY.md assertion (the
section there carries the old quantifier and none of the scoped phrases) and green at the tree.

The second round of that review (2026-09-21) found the rest of the section did not follow its first sentence: the
closing claim that session text goes ONLY to the model provider and a subscribed phone was contradicted by two
roads of the census (an attached machine over your own tunnels, the postal bus's exchange with its bus) and was
pinned against itself; the frame that every other connection opens once YOU set it up was false for a watch
predicate a session registers on its own and for a viewed file's pictures, which the gear's host list loads on
open as shipped; the trigger was stated as the table's age where the kernel keys on the last ATTEMPT; the
install sentence omitted bootstrap.pypa.io; the drift check's audience was one of the code's three disjuncts.
The section is now derived from the census's table (scripts/network-inventory.py --table): every sentence is
supported by a row or a code fact, the exhaustive quantifiers the table cannot support are gone, and the
section names the derivation and the four classes the scan cannot see. The pins below hold each rewritten
sentence to the code fact behind it (the TTL compare and the stamp before the thread start, the drift
verdict's three disjuncts and the two cadence constants, the gear's default host list, the watch route and
its constants, the get-pip line, the relay and peer-exchange functions), never to itself, and
TheSectionIsTheTables holds the section's road list equal to the table by execution: the script's --table
output is parsed and every road must be said in the section in words, so a new road is red here as well as in
the census. Over a git archive of the reviewed head every rewritten case is red at its first SECURITY.md
assertion (the old sentence); a phrase removed from a copy of the section at the tree reds the table case
naming the road, which the old pin, asserting the sentence against itself, could not do.

The third round of that review (2026-09-22) found two things in the section. The editor clause said the extension's
update prompt runs the same `install.sh` as the release update, the root script with pip and npm, where the click runs
vscode-extension/install.sh (`npm install`, `npx`) and never the root script or pip, and the pin behind it was the bare
substring `install.sh` in extension.ts, which that file's comments satisfy whichever script the code runs. The clause
now names the script the click runs and what it reaches (the npm registry, not PyPI), and
TheEditorPromptRunsTheExtensionsOwnInstallScript pins the target by the property: update-target.ts resolves the
script as `<dir>/install.sh` with the vscode-extension candidate, extension.ts hands that resolved script to
`runInstall` and `runInstall` runs it through `execFile("bash", [script])`, matched on code lines with the comments
stripped (and the comment-only text is checked NOT to satisfy the needles, as a control), the message naming
update-target.test.ts as the executed test; a negative pin holds extension.ts and vscode-extension/install.sh to no
`pip` and no `romp-sdk-setup`. The same round widened the census (a shell script's inline interpreter texts, the
manager's and the editor extension's child_process starts, a dynamic import of a computed module URL) and named a
fifth class the scan cannot see and does not count (a socket primitive on a receiver it cannot resolve); the section
states the widened class, the fifth class in the script's own sentence, the disclosure that the shell and browser sides
are matched by a named list with no completeness gate, and the condition under which vscode-extension/install.sh
fetches vsce with npx (an editor CLI present, or `ROMP_EXT_PACKAGE_ONLY` set). Those sentences are held to their
sources by execution: the class count in words is derived from the --table run (the counted class rows, the row whose
where cell reads not counted) and from the committed counts file, never typed here; the residual and the disclosure
sentences must appear in the section AND in the script's docstring, one source; the install condition is held to the
script's own gate lines (PACKAGE_ONLY, the editor-CLI list, the exit before npx) and to the table's install-ext and
self-update cells; the table's label for the external-program class is the section's phrase plus the kind suffix
every class row carries, read from the script's CLASS_ROWS by importing it in a child interpreter (the table had
labelled the class a program the kernel starts while the section, widened, said a program started whose far end its
arguments do not show), so the two wordings cannot drift apart. Over the archive of the round's reviewed head each
new or rewritten case is red at its first SECURITY.md assertion (the old editor clause; no fifth-class, residual,
disclosure or condition sentence) and the table case at its set equality (the archive's table has no fifth-class
row); the target pin, the negative pin, the figure pin, the one-source pin and the condition pin are each red under a
mutation of a scratch copy at the tree (the runInstall call repointed at a root install.sh, which the old substring pin
stayed green under; the executed lines replaced by a comment carrying the same words; `pip` planted in
vscode-extension/install.sh; the class count word altered; the residual sentence deleted from the docstring; the
PACKAGE_ONLY clause deleted from the gate), and the label pin with the old label restored in a scratch copy of the
script, naming both texts.

Text only: the behaviour is pinned in tests/test_price_feed_off.py (the kernel), the reference's prose in
tests/test_reference_price_feed.py. The documents and the sources are read as files; nothing loads romp
code, so no state root is minted (the table case runs scripts/network-inventory.py, a standard-library scan
of the tree, by subprocess). Every case asserts SECURITY.md's text FIRST, so a run over a tree without the
paragraph fails at that assertion and never at a missing symbol or a script that lacks the flag.
"""
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _flat(text):
    """Collapse hard wraps so a quote that spans a line break in the doc still compares."""
    return re.sub(r"\s+", " ", text).strip()


def _section(doc, heading):
    """The text under `## <heading>` up to the next heading of any level; "" when the heading is absent."""
    m = re.search(r"^## " + re.escape(heading) + r"\n(.*?)(?=^#{1,3} |\Z)", doc, re.S | re.M)
    return m.group(1) if m else ""


SECURITY = _read("SECURITY.md")
NETWORK = _section(SECURITY, "Network access")
REFERENCE = _read("docs", "reference.md")
KERNEL = _read("kernel", "kernel.py")
GEAR = _read("ui", "webview", "gear.js")

VAR = "ROMP_PRICE_FEED"
# the link the section carries, and the reference heading GitHub anchors as #the-price-feed
LINK = "[The price feed](docs/reference.md#the-price-feed)"
TARGET = "### The price feed"
# gear.js raPriceNote's reading under the switch: 'prices: built-in defaults' + '; ' + why
DEFAULTS_HEAD = "prices: built-in defaults"
WHY_OFF = "live feed off (%s=off)" % VAR
KERNEL_SDK = _read("kernel", "sdk_backend.py")
# the quantifier the review of PR 878 retired, and the scoped claim that replaced it (the derivation's sentence)
OLD_QUANTIFIER = "one outbound request by default"
OLD_TELEMETRY = "No telemetry or session data is sent anywhere"
SCOPED = "By default the kernel opens one connection of its own to a host other than the model provider"
PARSED = "The response is parsed strictly as numeric pricing"
# the other default roads the section names, each with the switch that gates it, and the kernel's read of that switch
CATALOG_SWITCH, CATALOG_READ = "`ROMP_MODEL_CATALOG=off`", 'os.environ.get("ROMP_MODEL_CATALOG")'
UPDATE_SWITCH, UPDATE_READ = "`ROMP_UPDATE_CHECK=off`", 'os.environ.get("ROMP_UPDATE_CHECK"'
RELEASE_ARGV = '"ls-remote", "--tags"'
VIEWER_ARGV = '"ls-remote", "--heads", "origin"'
NPM_ARGV = '["npm", "install"'
PICTURES = "Pictures from the web in files"
POSTAL = _read("postal", "postal_service.py")
SETTINGS = _read("ui", "webview", "settings.ts")
SDK_SETUP = _read("bin", "romp-sdk-setup")
ROMP_CLI = _read("bin", "romp")
EXTENSION = _read("vscode-extension", "src", "extension.ts")
INVENTORY = os.path.join("scripts", "network-inventory.py")
INVENTORY_SRC = _read(INVENTORY) if os.path.exists(os.path.join(ROOT, INVENTORY)) else ""
EXPECTED_COUNTS = os.path.join("scripts", "network-inventory-expected.json")
# the second round of the review of PR 878: the section derived from the census's table, each sentence anchored
TRIGGER = ("when the Token usage view opens and this kernel has made no fetch attempt yet, or its last attempt is more "
           "than six hours old, with no credential")
STAMPED = ("stamps the attempt before the fetch runs, so a fetch that fails or lands nothing holds the six hours like one "
           "that landed, and the first open of the view after a start always fetches")
OLD_TRIGGER = "the table it holds is more than six hours old"
TTL_CHECK = 'if now - _price_cache["t"] < PRICE_TTL:'
TTL_STAMP = '_price_cache["t"] = now'
THREAD_START = "threading.Thread(target=work"
CACHE_ZERO = '_price_cache = {"t": 0'
DERIVED = "The list is derived from the code by `python3 scripts/network-inventory.py`, run from the repository root"
REFUSES = ("exits 1 naming any site it cannot place, any count that differs, any HTTP or socket client it does not know and "
           "any row of its table that names no site")
SUITE_RUNS = "the test suite runs it (`tests/test_price_feed_census.py`)"
GATES = ("UNCLASSIFIED", "COUNTS", "IMPORT", "STALE ROW")   # the script's own gate words, one per refusal the sentence names
RELEASE_CLAUSE = ("`git ls-remote` against the release remote, at boot and then every six hours for the release check, on a "
                  "clone whose VERSION file names a release")
DRIFT_CLAUSE = ("every five minutes for the drift check, on a checkout on branch main, in update mode auto, or with a machine "
                "attached or remembered")
OLD_DRIFT = "for the drift check on a clone that tracks main"
VERDICT = 'return branch == "main" or mode == "auto" or bool(attached)'
MAIN_EVERY, RELEASE_EVERY = "_MAIN_CHECK_EVERY_S = 300", "_UPDATE_CHECK_EVERY_S = 6 * 3600"
PICTURES_DEFAULT = ("the pictures a viewed markdown file loads from the hosts on the gear's Pictures from the web in files list, "
                    "which starts as github.com, its image and asset hosts, localhost and 127.0.0.1")
IN_THE_BROWSER = "in the browser rather than the kernel"
FRAME = "The other connections open when something sets them up, you or a session you are running"
OLD_FRAME = "opens once you set it up"
WATCH_ITEM = "a watch predicate, which a session registers on its own (`romp watch`, POST `/watch`; no setting of yours gates it)"
WATCH_RUNS = "runs the registered text through `/bin/sh`"
WATCH_NOT_ROMPS = "what the command itself sends is not romp's"
PR_WATCH = "a PR watch (`gh pr view` on a cadence, registered with `romp watch-pr`, which asks `gh` for the repository's name when given no `--repo`)"
# the third round of the review of PR 878: the editor clause names the script the click runs and what it reaches; the release
# clause names the two scripts the root install.sh runs; the condition under which vscode-extension/install.sh fetches vsce
EDITOR_PROMPT = "the editor extension's update prompt runs `vscode-extension/install.sh` (`npm install` and `npx`) on your click"
EDITOR_NOT_ROOT = "not the root `install.sh`, so a click reaches the npm registry and not PyPI"
OLD_EDITOR_PROMPT = "runs the same `install.sh` on your click"
RELEASE_THROUGH = "then for a release `install.sh` with pip and npm, through `bin/romp-sdk-setup` and `vscode-extension/install.sh`"
EXT_GATE = ("only when an editor CLI is present (`code`, `code-insiders`, `cursor` or `codium` on PATH, or an editor bundle under "
            "`ROMP_EDITOR_APPS`) or `ROMP_EXT_PACKAGE_ONLY` is set")
EXT_CONDITION = ("`vscode-extension/install.sh` runs `npm install` against the npm registry on every run; `npx --yes @vscode/vsce package`, "
                 "a fetch of vsce from the same registry even when it is cached, runs " + EXT_GATE +
                 "; with neither the script exits after the build and sends nothing more")
SELF_UPDATE_GATE = "only when an editor CLI is present or `ROMP_EXT_PACKAGE_ONLY` is set"
UPDATE_TARGET = _read("vscode-extension", "src", "update-target.ts")
UPDATE_TARGET_TEST = _read("vscode-extension", "src", "update-target.test.ts")
EXT_INSTALL = _read("vscode-extension", "install.sh")
ROOT_INSTALL = _read("install.sh")
# the census's fifth class (named in the table and not counted) and its disclosure, in the script's own words: the section
# and the script's docstring must both carry each, so the sentence has one source (tests/test_price_feed_census.py holds the
# same two sentences in the docstring and the --table output)
RESIDUAL = ("a socket primitive called on a receiver the census cannot resolve (an attribute-held or parameter socket) is not a "
            "site here")
DISCLOSURE = ("The shell and browser sides are matched by a named list with no completeness gate: a tool or a client the lists "
              "do not name is no site and no line; the Python side's gate is module-granular: an import outside the allow-list "
              "fails the run, and a primitive of a known module outside NET and SUB is not a site.")
UNSEEN_LABEL = "a socket primitive on a receiver this scan cannot resolve (not derivable by this scan)"
NOT_COUNTED = "not counted:"   # how the table's where cell opens for a class row that is named and not counted
COUNTED_CLASSES = "classes of outbound activity the scan cannot derive are named and counted in its table rather than left out"
FIFTH = "is named in the table and not counted, since the scan cannot see it"
EXTERNAL_PROGRAM = "an external program started whose far end its arguments do not show"
OLD_EXTERNAL_PROGRAM = "an external program the kernel starts whose far end its arguments do not show"
# the table's label for the class: the section's phrase plus the kind suffix every class row carries, one text; the
# ROAD_PHRASES key is this constant and the label pin reads the script's CLASS_ROWS to hold the table to it
EXTERNAL_PROGRAM_LABEL = "%s (not derivable by this scan)" % EXTERNAL_PROGRAM
NUMBER_WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight"}
ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth"}
GET_PIP = "PyPI (and bootstrap.pypa.io for get-pip.py when the python lacks ensurepip; `ROMP_NO_GET_PIP=1` skips that fetch)"
GET_PIP_LINE = "https://bootstrap.pypa.io/get-pip.py"
CENSUS_LISTS = "the census lists such a site by the program it starts, never by where that program connects"
NO_TELEMETRY = ("romp sends no telemetry: the kernel's own requests to hosts other than the machines you attach are the four "
                "named above: the price table, the catalog refresh, the fast-mode probe and web push")
TEXT_PROVIDER = "Session text goes to the model provider the session or the judge call is billed to"
TEXT_ATTACHED = ("over your own ssh tunnels to a machine you attached (the text you send a session there, the session listings, "
                 "views and file bodies relayed back, and the postal mail between the two machines' buses)")
TEXT_PHONE = "encrypted end to end, to the push service of a phone you subscribed"
OLD_ONLY = "Session text goes only to"
# the table's road labels (the first cell of `--table`, the ROADS literal's second field) and the words of the section that
# say each road: a new road in the table is red here until it has a sentence and an entry; the local row owes no sentence
ROAD_PHRASES = {
    "price feed (kernel-request)": ("fetches a public model-pricing table",),
    "model catalog refresh (kernel-request)": ("Models API catalog refresh",),
    "fast-mode organisation probe (kernel-request)": ("fast-mode probe",),
    "web push (kernel-request)": ("a subscribed phone (web push, encrypted end to end)",),
    "release check (kernel-runs-a-command)": (RELEASE_CLAUSE,),
    "main drift check (kernel-runs-a-command)": (DRIFT_CLAUSE,),
    "self-update to a release (kernel-runs-a-command)": (
        "an update taken from the banner or by the auto mode (`git fetch`, then for a release `install.sh` with pip and npm",
        RELEASE_THROUGH),
    "main converge (kernel-runs-a-command)": ("an update taken from the banner or by the auto mode (`git fetch`",),
    "PR watch (kernel-runs-a-command)": ("a PR watch (`gh pr view` on a cadence, registered with `romp watch-pr`",),
    "watch-pr registration (a romp CLI verb a session or the user runs, not the kernel)": (
        "which asks `gh` for the repository's name when given no `--repo`",),
    "file viewer origin check (kernel-runs-a-command)": (
        "`git ls-remote --heads origin` in a viewed file's checkout when its branch has no local tracking ref",),
    "predicate watch (kernel-runs-a-command)": (WATCH_ITEM, WATCH_RUNS, WATCH_NOT_ROMPS),
    "ssh tunnels and everything over them (kernel-runs-a-command, and kernel-request over the forward)": (
        "an attached machine (ssh commands to it and tunnels to it, and everything over them", TEXT_ATTACHED),
    "one-shot ssh commands on an attached host (kernel-runs-a-command)": ("ssh commands to it",),
    "git fetch from an attached checkout (kernel-runs-a-command)": ("a Pull of its checkout included",),
    "npm install retry at boot (kernel-runs-a-command)": ("one `npm install` when a bundle rebuild fails at boot",),
    "the operator's own commands: the apiKeyHelper and a stored login's token command (kernel-runs-a-command)": (
        "the apiKeyHelper or stored-login command you configured",),
    "the session CLIs (session-or-judge-cli)": (
        "the session CLIs and the judge CLIs, which talk to their providers on the session's or the call's billing",),
    "the judges' CLI (session-or-judge-cli)": ("the judge CLIs",),
    "the postal bus to peer buses (bus-request)": ("the postal mail between the two machines' buses",),
    "a viewed file's pictures from the web (browser)": (IN_THE_BROWSER, PICTURES_DEFAULT),
    "bootstrap.sh (install-time-by-hand)": ("Installing by hand (`bootstrap.sh`, `install.sh`) fetches from GitHub",),
    "bin/romp-sdk-setup (install-time-by-hand; also run by the kernel's self-update through install.sh)": (GET_PIP,),
    "vscode-extension/install.sh (install-time-by-hand; also run by the kernel's self-update and by the editor extension's "
    "update prompt)": ("and the npm registry", EDITOR_PROMPT, EDITOR_NOT_ROOT, EXT_CONDITION),
    "bin/romp-codex-setup (install-time-by-hand)": (
        "`bin/romp-codex-setup`, run by hand for Codex sessions, fetches the Codex SDK from PyPI and the pinned Codex CLI from GitHub",),
    "local, set aside and counted (local)": (),          # nothing leaves the machine: no sentence owed
    EXTERNAL_PROGRAM_LABEL: (EXTERNAL_PROGRAM,),   # one text: the label is the phrase with the kind suffix (the label pin)
    "a program supplied at run time (not derivable by this scan)": ("a program whose text is supplied at run time",),
    "a browser request whose URL is computed at run time (not derivable by this scan)": (
        "a browser request whose URL is computed at run time (a fetch, or a dynamic import of a module)",),
    "the browser DOM's own loads (not derivable by this scan)": ("the loads the browser makes on its own for what a page inserts",),
    UNSEEN_LABEL: (RESIDUAL,),       # named and not counted: the where cell opens with NOT_COUNTED and carries RESIDUAL
}
KERNEL_REQUEST_ROWS = ("price feed", "model catalog refresh", "fast-mode organisation probe", "web push")
_TABLE = []


def _pydef(src, name):
    """The text of top-level `def name(...)` up to the next top-level def or class; "" when absent."""
    m = re.search(r"^def " + re.escape(name) + r"\(.*?(?=^(?:def|class) |\Z)", src, re.S | re.M)
    return m.group(0) if m else ""


def _table():
    """The rows of `python3 scripts/network-inventory.py --table`, run once over ROOT: a list of (label, kind, cells) with
    the label and its kind from the first cell and `cells` the other four (where, trigger and cadence, what is sent, off
    switch), header and separator dropped. Parsed from stdout whatever the exit status: the gates (a count that drifted,
    a site with no road) are tests/test_price_feed_census.py's finding, and this module's is the section."""
    if not _TABLE:
        p = subprocess.run([sys.executable, os.path.join(ROOT, INVENTORY), "--table", ROOT],
                           capture_output=True, text=True, timeout=120)
        rows = []
        for line in p.stdout.splitlines():
            if not line.startswith("| ") or line.startswith("| road |") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            label = cells[0]
            kind = label[label.rfind("(") + 1:-1] if label.endswith(")") else ""
            rows.append((label, kind, cells[1:]))
        _TABLE.append((rows, p.returncode, p.stderr[-2000:]))
    return _TABLE[0]


def _row(rows, label):
    """The cells of the table row labelled `label`, or None."""
    for lab, _, cells in rows:
        if lab == label:
            return cells
    return None


def _class_label(cls):
    """The label the script prints for the class row `cls`, CLASS_ROWS[cls][0], read from the script's own binding by
    importing it in a child interpreter, never from its text; a child and not this process because
    tests/test_state_isolation_order.py reads every in-process load call as a load of romp code, and this module loads none."""
    prog = ("import importlib.util, json, sys\n"
            "spec = importlib.util.spec_from_file_location('network_inventory', sys.argv[1])\n"
            "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
            "print(json.dumps(mod.CLASS_ROWS[sys.argv[2]][0]))\n")
    p = subprocess.run([sys.executable, "-c", prog, os.path.join(ROOT, INVENTORY), cls], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise AssertionError("%s could not be imported to read CLASS_ROWS[%r]: %s" % (INVENTORY, cls, p.stderr[-800:]))
    return json.loads(p.stdout)


def _code_lines(src):
    """`src` split into its code and its `//` comments: a line whose first non-blank text is `//` is a comment whole, and
    a `//` preceded by whitespace (never the `//` of a URL, which a colon precedes) starts a trailing comment. Returns
    (code, comments), each the joined text, so a needle can be asserted on what runs and denied on what does not."""
    code, comments = [], []
    for line in src.splitlines():
        if line.lstrip().startswith("//"):
            comments.append(line)
            continue
        m = re.search(r"(?:^|(?<=\s))//", line)
        if m:
            code.append(line[:m.start()])
            comments.append(line[m.start():])
        else:
            code.append(line)
    return "\n".join(code), "\n".join(comments)


def _ts_function(src, name):
    """The text of `function name(...) {` up to its closing brace at column zero; "" when absent."""
    m = re.search(r"^(?:export )?(?:async )?function " + re.escape(name) + r"\(.*?^\}", src, re.S | re.M)
    return m.group(0) if m else ""


class _Pins(unittest.TestCase):
    DOC = "SECURITY.md (Network access)"

    def assertQuoted(self, needle, haystack, where, msg=""):
        # a bare assertIn would print the whole file on a miss; name the missing text and the file instead
        self.assertTrue(needle in haystack, "%s does not carry %r%s" % (where, needle, (": " + msg) if msg else ""))

    def assertNetwork(self):
        self.assertTrue(NETWORK, "SECURITY.md has no `## Network access` section")


class TheNetworkSectionNamesTheSwitch(_Pins):
    def test_it_names_the_switch_and_where_the_service_reads_it(self):
        self.assertNetwork()
        self.assertQuoted("`%s=off`" % VAR, NETWORK, self.DOC)
        self.assertQuoted("`service.env`", NETWORK, self.DOC, "the service reads its env from service.env, then a restart")
        self.assertQuoted("restart", NETWORK, self.DOC)
        self.assertQuoted("stops that fetch", _flat(NETWORK), self.DOC, "the switch is described as stopping the fetch the section names")
        self.assertQuoted('os.environ.get("%s")' % VAR, KERNEL, "kernel/kernel.py", "the switch the doc names is the one the kernel reads")
        self.assertQuoted("def _price_feed_off():", KERNEL, "kernel/kernel.py")

    def test_it_says_what_the_reader_sees_and_the_code_emits_it(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("prices tokens from the built-in defaults and says so", flat, self.DOC)
        self.assertQuoted("`/version`", NETWORK, self.DOC)
        self.assertQuoted("`priceFeed`", NETWORK, self.DOC)
        self.assertQuoted('"priceFeed": _price_feed_status()', KERNEL, "kernel/kernel.py", "/version carries the block")
        src = "ui/webview/gear.js"
        self.assertQuoted("'%s'" % DEFAULTS_HEAD, GEAR, src, "the modal's line under the switch")
        self.assertQuoted("'%s'" % WHY_OFF, GEAR, src)

    def test_it_links_the_reference_subsection_and_the_link_resolves(self):
        self.assertNetwork()
        self.assertQuoted(LINK, _flat(NETWORK), self.DOC, "how to stop the fetch is one link away")
        self.assertQuoted(TARGET, REFERENCE, "docs/reference.md", "the heading the link's anchor resolves to")
        self.assertQuoted("`%s=off`" % VAR, REFERENCE, "docs/reference.md", "the target documents the same switch")


class TheSectionScopesItsClaimToWhatTheCodeDoes(_Pins):
    """The review of PR 878: the section's claim is the derivation's, stated positively, and (round 2) every sentence of it
    is held to the code fact or the table row behind it, never to itself. Each case asserts the section's text first, so
    over an archive of either reviewed head it is red at that assertion (the old sentence), and green at the tree."""

    def test_the_old_quantifier_is_gone_and_the_scoped_sentence_stands(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(SCOPED, flat, self.DOC, "the claim is scoped to the kernel's own connections, by the derivation")
        self.assertQuoted(PARSED, flat, self.DOC, "the section keeps saying what the response is")
        self.assertQuoted("`%s=off`" % VAR, NETWORK, self.DOC)
        self.assertNotIn(OLD_QUANTIFIER, flat,
                         "%s: 'romp makes one outbound request by default' was false with the feed off and nothing "
                         "configured (the catalog refresh and the release check's git ls-remote still run)" % self.DOC)
        refresh = _pydef(KERNEL, "_refresh_remote_prices")
        self.assertTrue(refresh, "kernel/kernel.py defines _refresh_remote_prices at the top level")
        self.assertQuoted('_price_rate_value(v["input_cost_per_token"])', refresh, "kernel/kernel.py _refresh_remote_prices",
                          "'parsed strictly as numeric pricing': the worker reads the four rates through the one strict read (round 3 "
                          "of the review of PR 878), a JSON number or a plain decimal in quotes, never a bare float() on a string; "
                          "executed in tests/test_price_feed_off.py LiveFeed")
        self.assertNotIn("float(v[", refresh, "kernel/kernel.py _refresh_remote_prices: no bare float() of a feed value (round 3)")
        helper = _pydef(KERNEL, "_price_rate_value")
        self.assertTrue(helper, "kernel/kernel.py defines _price_rate_value at the top level")
        self.assertQuoted("math.isfinite", helper, "kernel/kernel.py _price_rate_value",
                          "and rejects a rate that is not finite; executed in tests/test_price_feed_off.py")

    def test_the_trigger_is_the_last_attempt_stamped_before_the_fetch_and_both_documents_say_so(self):
        # regression-3 and extra7-3 of the second round: the section keyed the fetch on the age of the table the kernel
        # holds; the kernel keys it on _price_cache["t"], the clock of the last ATTEMPT, stamped before the worker thread
        # starts, so a fetch that fails or lands nothing holds the TTL like a landed one, and a fresh kernel (the stamp
        # starts at 0) fetches at the first open. The reference had it right; the two documents now move together.
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(TRIGGER, flat, self.DOC, "the trigger as the code has it: no attempt yet, or the last attempt stale")
        self.assertQuoted(STAMPED, flat, self.DOC, "the stamp is the attempt's, before the fetch runs")
        self.assertNotIn(OLD_TRIGGER, flat, "%s: the table's age is a different clock from the attempt's stamp" % self.DOC)
        self.assertQuoted("the last fetch attempt is more than six hours old, or there has been none", _flat(REFERENCE),
                          "docs/reference.md", "the reference states the same trigger")
        refresh = _pydef(KERNEL, "_refresh_remote_prices")
        self.assertTrue(refresh, "kernel/kernel.py defines _refresh_remote_prices at the top level")
        where = "kernel/kernel.py _refresh_remote_prices"
        for needle in (TTL_CHECK, TTL_STAMP, THREAD_START):
            self.assertQuoted(needle, refresh, where)
        self.assertLess(refresh.find(TTL_CHECK), refresh.find(TTL_STAMP), "%s: the check, then the stamp" % where)
        self.assertLess(refresh.find(TTL_STAMP), refresh.find(THREAD_START),
                        "%s: the attempt is stamped before the worker thread starts, so a failed or empty fetch has stamped it "
                        "(the doc's 'holds the six hours like one that landed'); executed in tests/test_price_feed_off.py "
                        "FailedFetch" % where)
        self.assertQuoted(CACHE_ZERO, KERNEL, "kernel/kernel.py", "the stamp starts at zero, so the first open of a fresh kernel "
                          "always fetches (the doc's 'no fetch attempt yet')")
        self.assertQuoted("PRICE_TTL = 6 * 3600", KERNEL, "kernel/kernel.py", "six hours is the kernel's TTL")

    def test_it_names_the_kernels_other_default_connections_and_the_switch_the_kernel_reads(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("The kernel's other connections of its own by default go to the model provider", flat, self.DOC)
        self.assertQuoted("Models API catalog refresh", flat, self.DOC)
        self.assertQuoted(CATALOG_SWITCH, flat, self.DOC, "the switch that gates the refresh, named beside it")
        self.assertQuoted("fast-mode probe", flat, self.DOC)
        self.assertQuoted(CATALOG_READ, KERNEL, "kernel/kernel.py", "the switch the section names is the one the kernel reads")
        self.assertQuoted("def _refresh_model_catalog(", KERNEL, "kernel/kernel.py", "the refresh the section names")
        self.assertQuoted("def _fetch_key_fast_org(", KERNEL_SDK, "kernel/sdk_backend.py", "the probe the section names")

    def test_it_names_the_programs_the_kernel_runs_by_default_and_the_switch_that_gates_the_checks(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("By default the kernel also runs programs that connect on their own", flat, self.DOC)
        self.assertQuoted(RELEASE_CLAUSE, flat, self.DOC, "the release check with its cadence and its condition")
        self.assertQuoted(DRIFT_CLAUSE, flat, self.DOC, "the drift check with its cadence and the code's three disjuncts")
        self.assertNotIn(OLD_DRIFT, flat, "%s: one disjunct of three, and no cadence (extra11-4)" % self.DOC)
        self.assertQuoted(UPDATE_SWITCH, flat, self.DOC, "the switch that gates both checks, named beside them")
        self.assertQuoted("update mode off", flat, self.DOC, "the gear's setting that gates them too")
        self.assertQuoted("`git ls-remote --heads origin` in a viewed file's checkout", flat, self.DOC,
                          "the file viewer's origin check runs with no switch on a viewer open")
        self.assertQuoted("the session CLIs and the judge CLIs", flat, self.DOC)
        self.assertQuoted("one `npm install` when a bundle rebuild fails at boot", flat, self.DOC)
        self.assertQuoted(UPDATE_READ, KERNEL, "kernel/kernel.py", "the switch the section names is the one the kernel reads")
        self.assertQuoted("def _update_checks_off():", KERNEL, "kernel/kernel.py")
        for argv, road in ((RELEASE_ARGV, "the release check's git ls-remote --tags"),
                           (VIEWER_ARGV, "the file viewer's git ls-remote --heads origin"),
                           (NPM_ARGV, "the boot rebuild's npm install")):
            self.assertQuoted(argv, KERNEL, "kernel/kernel.py", "%s is a program the kernel runs" % road)
        # the drift check's audience is _main_channel_verdict's three disjuncts, its cadence the loop's wait; the release
        # check's stride is the six-hour constant and its condition a VERSION that parses as a release
        verdict = _pydef(KERNEL, "_main_channel_verdict")
        self.assertQuoted(VERDICT, verdict, "kernel/kernel.py _main_channel_verdict",
                          "on branch main, OR update mode auto, OR a machine attached or remembered: the three the doc names")
        self.assertQuoted("_main_tracking()", _pydef(KERNEL, "_main_drift_check"), "kernel/kernel.py _main_drift_check",
                          "the drift check runs behind that verdict over the live inputs")
        self.assertQuoted(MAIN_EVERY, KERNEL, "kernel/kernel.py", "every five minutes")
        self.assertQuoted(RELEASE_EVERY, KERNEL, "kernel/kernel.py", "every six hours")
        loop = _pydef(KERNEL, "_update_check_loop")
        self.assertQuoted("_CHECK_LOOP_STOP.wait(_MAIN_CHECK_EVERY_S)", loop, "kernel/kernel.py _update_check_loop",
                          "the loop's stride is the drift check's cadence")
        self.assertQuoted(">= _UPDATE_CHECK_EVERY_S", loop, "kernel/kernel.py _update_check_loop", "the release check's stride")
        check = _pydef(KERNEL, "_update_check")
        self.assertQuoted('cur = _semver((_kernel_ver() or "").rstrip("+"))', check, "kernel/kernel.py _update_check",
                          "the release check reads VERSION as a release number and returns when it is none (the doc's 'on a "
                          "clone whose VERSION file names a release')")
        self.assertQuoted("if cur is None:", check, "kernel/kernel.py _update_check")
        # the viewer's web pictures are a by-default browser road (extra7-1): the gear's list ships non-empty, github.com
        # first, its image and asset hosts, localhost and 127.0.0.1, so a viewed file's GitHub picture loads on open with
        # nothing configured; the section says so in the by-default group, under the gear's own control
        self.assertQuoted(IN_THE_BROWSER, flat, self.DOC, "the browser's road, filed with the by-default connections")
        self.assertQuoted(PICTURES_DEFAULT, flat, self.DOC, "the pictures road names the list as shipped")
        m = re.search(r"export const FIGURE_HOSTS_DEFAULT: readonly string\[\] = \[(.*?)\];", SETTINGS, re.S)
        self.assertTrue(m, "ui/webview/settings.ts exports FIGURE_HOSTS_DEFAULT, the list the section describes")
        hosts = re.findall(r'"([^"]+)"', m.group(1))
        self.assertTrue(hosts, "the default list ships NON-EMPTY, which is why the road is by default")
        self.assertEqual(hosts[0], "github.com", "the section says the list starts as github.com")
        self.assertIn("localhost", hosts)
        self.assertIn("127.0.0.1", hosts)
        others = [h for h in hosts if h not in ("github.com", "localhost", "127.0.0.1")]
        self.assertTrue(others and all(h.endswith(("githubusercontent.com", "githubassets.com")) for h in others),
                        "the rest of the list is GitHub's image and asset hosts, which is what the section calls them: %r" % others)
        self.assertQuoted("### Pictures from the web in a viewed file", REFERENCE, "docs/reference.md",
                          "the setting the section names is documented under that heading")
        self.assertQuoted("**%s**" % PICTURES, REFERENCE, "docs/reference.md", "the gear's name for the setting")

    def test_it_names_the_roads_that_open_when_set_up_by_you_or_a_session_and_what_sets_each_up(self):
        # extra7-5 and extra6-8 of the second round: the frame is worded to the actor (a session arms a watch predicate
        # on its own, with no setting of yours), and the predicate item states the route, the shell, the cadence floor
        # and default, the bound and the boot re-arm, each read from the kernel below
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(FRAME, flat, self.DOC, "the frame names the actor, you or a session")
        self.assertNotIn(OLD_FRAME, flat, "%s: a watch predicate and a viewed file's pictures open with no act of yours" % self.DOC)
        for phrase in ("an attached machine", PR_WATCH, WATCH_ITEM, WATCH_RUNS, WATCH_NOT_ROMPS,
                       "a subscribed phone (web push, encrypted end to end)",
                       "the apiKeyHelper or stored-login command you configured",
                       "an update taken from the banner or by the auto mode", EDITOR_PROMPT,
                       "Installing by hand (`bootstrap.sh`, `install.sh`)", GET_PIP):
            self.assertQuoted(phrase, flat, self.DOC)
        self.assertNotIn(PICTURES, flat[flat.find(FRAME):flat.find("Installing by hand")],
                         "%s: the pictures road left the set-up list for the by-default group (extra7-1)" % self.DOC)
        # the watch predicate's actor and mechanics, by value: the route, the registration with no switch read, the
        # constants the section's numbers come from, and the shell
        self.assertQuoted('if u.path == "/watch":', KERNEL, "kernel/kernel.py", "POST /watch registers a predicate")
        add = _pydef(KERNEL, "add_watch")
        self.assertTrue(add, "kernel/kernel.py defines add_watch at the top level")
        self.assertNotIn("os.environ", add, "kernel/kernel.py add_watch reads no switch: no setting of yours gates it")
        self.assertNotIn("_update_mode", add, "kernel/kernel.py add_watch reads no gear setting either")
        consts = dict(re.findall(r"^(WATCH_MIN_EVERY|WATCH_DEFAULT_EVERY|WATCH_DEFAULT_TIMEOUT) = ([0-9* ]+)", KERNEL, re.M))
        self.assertEqual(set(consts), {"WATCH_MIN_EVERY", "WATCH_DEFAULT_EVERY", "WATCH_DEFAULT_TIMEOUT"},
                         "kernel/kernel.py defines the watch cadence floor, default and bound as module constants")
        floor, default, bound = (eval(consts[k], {}) for k in ("WATCH_MIN_EVERY", "WATCH_DEFAULT_EVERY", "WATCH_DEFAULT_TIMEOUT"))
        self.assertQuoted("no faster than every %d seconds, every %d by default" % (floor, default), flat, self.DOC,
                          "the cadence floor and default are the kernel's constants")
        self.assertQuoted("its bound (%d hours by default)" % (bound // 3600), flat, self.DOC, "the bound is the kernel's constant")
        self.assertQuoted("max(WATCH_MIN_EVERY, int(every)) if every else WATCH_DEFAULT_EVERY", add, "kernel/kernel.py add_watch",
                          "the registration floors the cadence and defaults it")
        self.assertQuoted('["/bin/sh", str(sp)]', _pydef(KERNEL, "_watch_run"), "kernel/kernel.py _watch_run",
                          "the registered text runs through /bin/sh, so what it sends is the command's")
        self.assertQuoted("re-armed at boot", flat, self.DOC)
        self.assertQuoted("def _watches_load():", KERNEL, "kernel/kernel.py", "the rows are re-read at boot from watches.json")
        # the PR watch's two gh calls, and the editor extension's prompt, by the code that runs them
        self.assertQuoted('"gh", "pr", "view"', KERNEL, "kernel/kernel.py", "the PR watch's poll")
        self.assertQuoted("gh repo view --json nameWithOwner", ROMP_CLI, "bin/romp", "the registration's own call when no --repo is given")
        self.assertQuoted("function runInstall(", EXTENSION, "vscode-extension/src/extension.ts", "the editor extension's update prompt")
        # which install.sh that function runs is TheEditorPromptRunsTheExtensionsOwnInstallScript's pin, by the property: a
        # bare `install.sh` substring here was satisfied by extension.ts's comments whichever script the code ran (round 3)
        # bootstrap.pypa.io (extra7-4): the get-pip fetch, its condition and its opt-out, in bin/romp-sdk-setup
        self.assertQuoted(GET_PIP_LINE, SDK_SETUP, "bin/romp-sdk-setup", "get-pip.py's default source")
        self.assertQuoted("import ensurepip", SDK_SETUP, "bin/romp-sdk-setup", "fetched only when the python lacks ensurepip")
        self.assertQuoted("ROMP_NO_GET_PIP", SDK_SETUP, "bin/romp-sdk-setup", "the opt-out the section names")
        for name in ("def _spawn_tunnel(", "def _pr_watch_read(", "def _watch_run(", "def _push_post(", "def _pull_remote("):
            self.assertQuoted(name, KERNEL, "kernel/kernel.py", "a road the section names, by the function that runs it")

    def test_what_a_program_the_kernel_starts_sends_is_that_programs_and_the_telemetry_claim_is_scoped(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("What those programs send is theirs, not the kernel's", flat, self.DOC)
        for name in ("a session's own CLI", "the judges' CLIs", "a watch predicate", "the API key helper",
                     "a login's token program", "`gh`, `git`, `ssh`, `npm` and the browser"):
            self.assertQuoted(name, flat, self.DOC, "a program that opens connections the kernel does not see")
        self.assertQuoted(CENSUS_LISTS, flat, self.DOC, "how the census files such a site")
        self.assertQuoted("RUNTIME-SUPPLIED", INVENTORY_SRC, INVENTORY, "the census marks a program it cannot read")
        self.assertQuoted(NO_TELEMETRY, flat, self.DOC, "the telemetry claim is scoped to the kernel's own requests, the table's "
                          "kernel-request rows (held equal to the table in TheSectionIsTheTables)")
        # extra6-7 and extra7-2 of the second round: the closing sentence names the three destinations the table supports
        # and no longer says 'only', which the table cannot support (a session's CLI and a registered predicate send what
        # they send); each destination is anchored to the function that carries the text
        self.assertQuoted(TEXT_PROVIDER, flat, self.DOC)
        self.assertQuoted(TEXT_ATTACHED, flat, self.DOC, "the attached machine, over your own tunnels: the relays and the bus")
        self.assertQuoted(TEXT_PHONE, flat, self.DOC)
        self.assertNotIn(OLD_ONLY, flat, "%s: 'only' was contradicted by two rows of the census (the relays to an attached "
                         "machine, the postal bus's peer exchange)" % self.DOC)
        self.assertNotIn(OLD_TELEMETRY, flat,
                         "%s: session text does reach the model provider (the sessions and the judges), an attached machine "
                         "and, encrypted, a subscribed phone's push service; the claim is scoped to what the code does" % self.DOC)
        for name in ("def _remote_control(", "def _remote_kernel_call(", "def _remote_file(", "def _poll_remote_sessions(",
                     "def _poll_remote_views("):
            self.assertQuoted(name, KERNEL, "kernel/kernel.py", "a relay that carries session text to or from an attached machine")
        self.assertQuoted("POST /remote/<host>/new and /remote/<host>/send", KERNEL, "kernel/kernel.py",
                          "the text you send a session there crosses the tunnel")
        self.assertQuoted("def _peer_exchange_once(", POSTAL, "postal/postal_service.py", "the bus's exchange with the peer bus")
        self.assertQuoted('"/peer-exchange"', POSTAL, "postal/postal_service.py")
        self.assertQuoted("def _push_post(", KERNEL, "kernel/kernel.py", "the encrypted push to the phone's service")

    def test_the_switch_paragraph_states_the_value_rule_the_kernel_applies(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("Only the value `off`, whitespace and case ignored, turns the feed off", flat, self.DOC)
        self.assertQuoted("any other value leaves it on, and the kernel says so on its stderr, on that line and in that block",
                          flat, self.DOC, "a misspelt switch fails open and is said, never silent")
        self.assertQuoted("def _price_feed_unrecognised():", KERNEL, "kernel/kernel.py",
                          "the read that says so; executed in tests/test_price_feed_off.py OffSwitch")
        self.assertQuoted('.strip().lower() == "off"', KERNEL, "kernel/kernel.py", "the rule: stripped and case-folded, equal to off")


class TheSectionIsTheTables(_Pins):
    """The section's road list is the census's table, held equal by execution (round 2 of the review of PR 878: the
    section made a completeness claim and named no derivation, and its pins asserted its sentences against themselves).
    Each case asserts the section's text first; the table comes from `python3 scripts/network-inventory.py --table`
    run over the tree, and a road it prints that the section does not say in words is red here, naming the road."""

    def test_the_section_names_the_derivation_and_what_the_run_refuses(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(DERIVED, flat, self.DOC, "the command a reader re-derives the list with, from the repository root")
        self.assertQuoted(REFUSES, flat, self.DOC, "what the run refuses, so a clean report means something")
        self.assertQuoted("`%s`" % EXPECTED_COUNTS, flat, self.DOC, "the committed counts the run is compared against")
        self.assertQuoted(SUITE_RUNS, flat, self.DOC, "the guarantee is the suite's, not a habit")
        self.assertTrue(INVENTORY_SRC, "%s exists: the derivation the section names" % INVENTORY)
        self.assertTrue(os.path.exists(os.path.join(ROOT, EXPECTED_COUNTS)), "%s exists: the counts the section names" % EXPECTED_COUNTS)
        for gate in GATES:
            self.assertQuoted(gate, INVENTORY_SRC, INVENTORY, "a refusal the section's sentence names, by the script's gate word")
        self.assertTrue(os.path.exists(os.path.join(ROOT, "tests", "test_price_feed_census.py")), "the module the section says runs it")
        self.assertQuoted("--table", _read("tests", "test_price_feed_census.py"), "tests/test_price_feed_census.py",
                          "the census module runs the script and compares its table")

    def test_every_road_of_the_table_is_said_in_the_section(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(DERIVED, flat, self.DOC)
        rows, rc, err = _table()
        labels = [label for label, _, _ in rows]
        self.assertGreaterEqual(len(labels), 25, "%s --table printed no table (exit %s): %s" % (INVENTORY, rc, err))
        self.assertEqual(len(labels), len(set(labels)), "one row per road")
        self.assertEqual(set(labels), set(ROAD_PHRASES),
                         "the table's roads and the section's are one set: a road in the table with no entry here needs a "
                         "sentence in the section and an entry in ROAD_PHRASES; an entry with no row is a road that is gone. "
                         "In the table only: %r; here only: %r" % (sorted(set(labels) - set(ROAD_PHRASES)),
                                                                     sorted(set(ROAD_PHRASES) - set(labels))))
        said = 0
        for label in labels:
            for phrase in ROAD_PHRASES[label]:
                self.assertQuoted(phrase, flat, self.DOC, "the words that say the road %r" % label)
                said += 1
        self.assertGreaterEqual(said, len(labels) - 1, "every road but the local row is said by at least one phrase")

    def test_the_kernel_request_rows_are_the_four_the_telemetry_sentence_names(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(NO_TELEMETRY, flat, self.DOC)
        rows, rc, err = _table()
        self.assertTrue(rows, "%s --table printed no table (exit %s): %s" % (INVENTORY, rc, err))
        kernel_request = [label[:label.rfind(" (")] for label, kind, _ in rows if kind == "kernel-request"]
        self.assertEqual(kernel_request, list(KERNEL_REQUEST_ROWS),
                         "the kernel's own requests to hosts other than an attached machine are the table's kernel-request "
                         "rows, and the telemetry sentence names those four; a fifth is a new sentence")
        for road in kernel_request:
            self.assertTrue(ROAD_PHRASES["%s (kernel-request)" % road], "the row %r has words in the section" % road)
        classes = [label for label, kind, _ in rows if kind == "not derivable by this scan"]
        with open(os.path.join(ROOT, EXPECTED_COUNTS), encoding="utf-8") as f:
            counted = set(json.load(f)["classes"])
        self.assertEqual(len([label for label, kind, cells in rows if kind == "not derivable by this scan"
                              and not cells[0].startswith(NOT_COUNTED)]), len(counted),
                         "the class rows the table counts are the classes the committed counts file carries (%r); a row "
                         "named and not counted opens its where cell with %r; the class sentence's number is "
                         "test_the_class_sentence_counts_the_counted_classes_and_names_the_uncounted_one_from_the_table's"
                         % (sorted(counted), NOT_COUNTED))
        self.assertTrue(classes, "the classes the scan cannot derive are rows of the table")
        for label in classes:
            for phrase in ROAD_PHRASES[label]:
                self.assertQuoted(phrase, flat, self.DOC, "a class the scan cannot see, named in the section")

    def test_the_class_sentence_counts_the_counted_classes_and_names_the_uncounted_one_from_the_table(self):
        # round 3 of the review of PR 878: the census names a fifth class it cannot see and does not count (a socket primitive
        # on a receiver it cannot resolve), so the section's "Four classes ... named and counted" and "A fifth is named ...
        # and not counted" are figures, derived here from the --table run (a class row is counted unless its where cell opens
        # with NOT_COUNTED) and from the committed counts file, never typed twice; the classes carry no count in the section
        # (round 2's decision: the table and the counts file carry the counts), so no digit may sit in the class sentences
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(FIFTH, flat, self.DOC, "the class the scan cannot see is named as not counted, in the section")
        self.assertQuoted(RESIDUAL, flat, self.DOC, "the fifth class in the script's own words")
        rows, rc, err = _table()
        self.assertTrue(rows, "%s --table printed no table (exit %s): %s" % (INVENTORY, rc, err))
        class_rows = [(label, cells) for label, kind, cells in rows if kind == "not derivable by this scan"]
        counted = [label for label, cells in class_rows if not cells[0].startswith(NOT_COUNTED)]
        uncounted = [label for label, cells in class_rows if cells[0].startswith(NOT_COUNTED)]
        self.assertTrue(counted and uncounted, "the table has class rows it counts and a class row it names and does not count: %r"
                        % [label for label, _ in class_rows])
        with open(os.path.join(ROOT, EXPECTED_COUNTS), encoding="utf-8") as f:
            committed = json.load(f)["classes"]
        self.assertEqual(len(counted), len(committed),
                         "the counted class rows are the classes the committed counts file carries: %r" % sorted(committed))
        self.assertQuoted("%s %s" % (NUMBER_WORDS[len(counted)], COUNTED_CLASSES), flat, self.DOC,
                          "the section counts the classes the table counts, in words derived from the table (%d rows)" % len(counted))
        for i, label in enumerate(uncounted):
            self.assertQuoted("A %s %s" % (ORDINALS[len(counted) + 1 + i], FIFTH), flat, self.DOC,
                              "a class named and not counted takes the next ordinal: %r" % label)
            self.assertQuoted(RESIDUAL, _row(rows, label)[0], "the table's where cell of %r" % label,
                              "the section's sentence for the uncounted class is the table's")
        span = flat[flat.find(NUMBER_WORDS[len(counted)] + " " + COUNTED_CLASSES):flat.find(RESIDUAL) + len(RESIDUAL)]
        self.assertTrue(span, "the class sentences run from the count to the fifth class")
        prose = re.sub(r"`[^`]*`", "", span)   # a code span names a program (`python3 -c`), never a count
        self.assertIsNone(re.search(r"\d", prose), "%s: the class sentences name the classes without counts; the counts sit in the "
                          "table and in %s, and a count typed here goes stale with the next scan: %r" % (self.DOC, EXPECTED_COUNTS, span))

    def test_the_residual_and_the_disclosure_sentences_are_the_scripts_words(self):
        # round 3 of the review of PR 878 (rulings A.5 and A.7): the class the census cannot see and the closedness of its shell
        # and browser lists are stated in SECURITY.md in the script's own sentences, so the section and the docstring have one
        # source and a sentence cannot outlive the behaviour it describes (tests/test_price_feed_census.py plants a socket
        # primitive the scan cannot resolve and holds the same sentence to the run's silence)
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(RESIDUAL, flat, self.DOC, "the fifth class, in the script's words")
        self.assertQuoted(DISCLOSURE, flat, self.DOC, "the shell and browser sides are a named list with no completeness gate")
        self.assertNotIn(OLD_EXTERNAL_PROGRAM, flat, "%s: the class holds programs a shell script of romp's, the manager and the "
                         "editor extension start too, not the kernel alone (round 3)" % self.DOC)
        self.assertQuoted(EXTERNAL_PROGRAM, flat, self.DOC)
        self.assertTrue(INVENTORY_SRC, "%s exists: the derivation the section names" % INVENTORY)
        doc = re.match(r'(?s)\A(?:#[^\n]*\n)*"""(.*?)"""', INVENTORY_SRC)
        self.assertTrue(doc, "%s opens with a module docstring" % INVENTORY)
        docstring = _flat(doc.group(1))
        self.assertQuoted(RESIDUAL, docstring, "%s's docstring" % INVENTORY, "one source: the section's sentence is the script's")
        self.assertQuoted(DISCLOSURE, docstring, "%s's docstring" % INVENTORY, "one source: the section's sentence is the script's")
        rows, rc, err = _table()
        self.assertTrue(rows, "%s --table printed no table (exit %s): %s" % (INVENTORY, rc, err))
        cells = _row(rows, UNSEEN_LABEL)
        self.assertTrue(cells, "the table names the class it cannot see as a row: %r" % UNSEEN_LABEL)
        self.assertTrue(cells[0].startswith(NOT_COUNTED), "the row is named and not counted: %r" % cells[0])
        self.assertQuoted(RESIDUAL, cells[0], "the table's where cell", "the same sentence, in the table")

    def test_the_external_program_rows_label_is_the_sections_phrase_read_from_the_scripts_class_rows(self):
        # round 3 of the review of PR 878, after ruling A widened the class: the table labelled it a program the kernel starts
        # while the section said a program started whose far end its arguments do not show, two wordings for one class bridged
        # by a ROAD_PHRASES entry. One wording now: the label is the section's phrase plus the kind suffix every class row
        # carries, read here from the script's CLASS_ROWS binding and never from its text, so neither can move alone
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(EXTERNAL_PROGRAM, flat, self.DOC, "the section's phrase for the class")
        label = _class_label("external-program")
        self.assertEqual(label, EXTERNAL_PROGRAM_LABEL,
                         "one wording for the external-program class: the script's CLASS_ROWS label reads %r and the section's "
                         "phrase with the kind suffix is %r; the class holds programs a shell script of romp's, the manager and the "
                         "editor extension start too, so the table's label is the section's phrase" % (label, EXTERNAL_PROGRAM_LABEL))
        self.assertEqual(ROAD_PHRASES.get(label), (EXTERNAL_PROGRAM,),
                         "the row's entry in ROAD_PHRASES is keyed on that label and says the row with the same phrase")


class TheEditorPromptRunsTheExtensionsOwnInstallScript(_Pins):
    """Round 3 of the review of PR 878 (the section's editor clause): the extension's update prompt runs
    vscode-extension/install.sh (`npm install`, `npx`), not the root install.sh and not pip, and the section says so. The
    pin is on the property, not the spelling: update-target.ts resolves the click's script as `<dir>/install.sh` for a
    vscode-extension candidate, extension.ts hands that resolved script to runInstall, and runInstall runs it through
    execFile("bash", [script]); matched on code with the `//` comments stripped, since extension.ts's comments carry
    `install.sh` five times and satisfied the bare substring pin whichever script the code ran. The executed test behind
    the resolution is vscode-extension/src/update-target.test.ts (script == <vscode-extension dir>/install.sh). Each case
    asserts the section first: red over the archive of the reviewed head at the old clause, green at the tree; the target
    pin is red with the runInstall call repointed at a root install.sh in a scratch copy (the old substring pin stayed
    green under that mutation) and with the executed lines replaced by a comment carrying the same words; the negative
    pin is red with `pip` planted in a scratch copy of vscode-extension/install.sh; the condition pin is red with the
    PACKAGE_ONLY clause deleted from the script's gate."""

    TS = "vscode-extension/src/extension.ts"
    SH = "vscode-extension/install.sh"
    EXECUTED = ("vscode-extension/src/update-target.test.ts asserts script == <vscode-extension dir>/install.sh, the executed test "
                "behind this text pin (node esbuild.js --tests, then node --test on that file)")

    def test_the_section_names_the_script_the_click_runs_and_the_code_resolves_to_it(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(EDITOR_PROMPT, flat, self.DOC, "the click runs the extension's own install.sh: npm install and npx")
        self.assertQuoted(EDITOR_NOT_ROOT, flat, self.DOC, "what the click reaches, and what it does not")
        self.assertQuoted(RELEASE_THROUGH, flat, self.DOC, "the release clause names the two scripts the root install.sh runs")
        self.assertNotIn(OLD_EDITOR_PROMPT, flat, "%s: the click never runs the root install.sh, whose pip half reaches PyPI (round 3)"
                         % self.DOC)
        # the release clause's two scripts, as the root install.sh runs them
        self.assertQuoted('"$ROMP_DIR/bin/romp-sdk-setup"', ROOT_INSTALL, "install.sh", "the release update's pip half")
        self.assertQuoted('"$ROMP_DIR/vscode-extension/install.sh"', ROOT_INSTALL, "install.sh", "the release update's npm half")
        # the click's target: resolved locally as <dir>/install.sh, <dir> the extension's own path or ROMP_DIR/vscode-extension
        resolve = _ts_function(UPDATE_TARGET, "resolveInstallScript")
        self.assertTrue(resolve, "vscode-extension/src/update-target.ts defines resolveInstallScript")
        self.assertQuoted('script: path.join(dir, "install.sh")', resolve, "update-target.ts resolveInstallScript", self.EXECUTED)
        candidates = _ts_function(UPDATE_TARGET, "installCandidates")
        self.assertTrue(candidates, "vscode-extension/src/update-target.ts defines installCandidates")
        self.assertQuoted('path.join(repo, "vscode-extension")', candidates, "update-target.ts installCandidates",
                          "a candidate is the vscode-extension directory, so <dir>/install.sh is the extension's own script")
        self.assertQuoted('assert.equal(t?.script, path.join(CHECKOUT, "install.sh"))', UPDATE_TARGET_TEST,
                          "vscode-extension/src/update-target.test.ts", "the executed test this pin points at asserts the resolution")
        # extension.ts hands the resolved script to runInstall, which runs it through bash: matched on code, comments stripped
        code, comments = _code_lines(EXTENSION)
        for needle, why in (("const script = target.script", "the click's script is the resolved target's"),
                            ("runInstall(script, extDir)", "and it is what runInstall runs")):
            self.assertQuoted(needle, code, self.TS + " (code, comments stripped)", why + "; " + self.EXECUTED)
        run_install = _ts_function(code, "runInstall")
        self.assertTrue(run_install, self.TS + " defines runInstall")
        self.assertQuoted('execFile("bash", [script]', run_install, self.TS + " runInstall", "bash runs the resolved script and nothing else")
        # the control: the comments alone satisfy the old substring pin and none of the needles, which is why the match is
        # on code (the comments name install.sh where the code names its resolved path)
        self.assertIn("install.sh", comments, self.TS + ": the comments carry the bare substring the old pin matched")
        for needle in ("const script = target.script", "runInstall(script, extDir)", 'execFile("bash", [script]'):
            self.assertNotIn(needle, comments, self.TS + ": %r sits in a comment, which runs nothing" % needle)

    def test_the_click_reaches_no_pip_and_no_sdk_setup(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(EDITOR_NOT_ROOT, flat, self.DOC, "the click reaches the npm registry and not PyPI")
        for where, src in ((self.TS, EXTENSION), (self.SH, EXT_INSTALL)):
            self.assertIsNone(re.search(r"\bpip\b", src), "%s carries the word pip: the section says the click reaches no PyPI; if "
                              "the script now runs pip, the sentence and the table's install-ext row move; a comment that names it "
                              "is reworded, since this pin reads the file whole so nothing that runs can hide in what it skips" % where)
            self.assertNotIn("romp-sdk-setup", src, "%s names romp-sdk-setup, the release update's pip half: the click's script "
                             "runs the extension's build and package alone" % where)
        # what the click does reach, by the script's own lines, and where pip is: the release clause's script
        self.assertQuoted("npm install", EXT_INSTALL, self.SH, "the npm registry, on every run")
        self.assertQuoted("npx --yes @vscode/vsce package", EXT_INSTALL, self.SH, "vsce from the same registry")
        self.assertQuoted("pip install", SDK_SETUP, "bin/romp-sdk-setup", "pip runs in the release update's script, not the click's")

    def test_the_install_scripts_condition_is_the_scripts_gate_and_the_tables(self):
        # ruling A.4 of round 3: the install-ext and self-update cells state the condition rather than claim every install
        # fetches, and the section repeats it; here the condition is held to the script's own gate and to the table's cells
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(EXT_CONDITION, flat, self.DOC, "npx runs behind the editor-CLI gate; with neither the script exits after the build")
        rows, rc, err = _table()
        self.assertTrue(rows, "%s --table printed no table (exit %s): %s" % (INVENTORY, rc, err))
        install_ext = [cells for label, _, cells in rows if label.startswith("vscode-extension/install.sh (")]
        self_update = [cells for label, _, cells in rows if label.startswith("self-update to a release (")]
        self.assertEqual((len(install_ext), len(self_update)), (1, 1), "the table has one install-ext row and one self-update row")
        self.assertQuoted(EXT_GATE, install_ext[0][1], "the install-ext row's trigger cell", "the section's condition is the table's")
        self.assertQuoted(SELF_UPDATE_GATE, self_update[0][2], "the self-update row's sent cell", "and the self-update row states it too")
        # the script: PACKAGE_ONLY read from ROMP_EXT_PACKAGE_ONLY; the editor CLIs from PATH and ROMP_EDITOR_APPS; the gate that
        # exits after the build when no CLI was found and PACKAGE_ONLY is empty; npm install and the build before it, npx after it
        gate_line = '[ "${#CLIS[@]}" -eq 0 ] && [ -z "$PACKAGE_ONLY" ]'
        for needle, why in (('PACKAGE_ONLY="${ROMP_EXT_PACKAGE_ONLY:-}"', "the switch the section names"),
                            ("for c in code code-insiders cursor codium", "the editor CLIs looked up on PATH, the four the section names"),
                            ('APPS_DIR="${ROMP_EDITOR_APPS:-/Applications}"', "the editor bundles' directory the section names"),
                            (gate_line, "the gate: no editor CLI found and the switch unset"),
                            ('if [ -n "$PACKAGE_ONLY" ]', "the switch alone: packaged, installed into no editor")):
            self.assertQuoted(needle, EXT_INSTALL, self.SH, why)
        npm, build = EXT_INSTALL.find("npm install"), EXT_INSTALL.find("node esbuild.js")
        gate, npx = EXT_INSTALL.find(gate_line), EXT_INSTALL.find("npx --yes @vscode/vsce package")
        self.assertTrue(0 <= npm < build < gate < npx, "%s: npm install, then the build, then the gate, then npx (the section's order)"
                        % self.SH)
        self.assertIn("exit 0", EXT_INSTALL[gate:npx], "%s: the gate exits before npx, so with neither condition nothing after npm "
                      "install is sent (the section's 'exits after the build and sends nothing more')" % self.SH)


class TheNewProse(_Pins):
    def test_no_em_or_en_dash_and_not_the_banned_word(self):
        self.assertNetwork()
        self.assertQuoted("`%s=off`" % VAR, NETWORK, self.DOC)
        self.assertNotIn(chr(0x2014), NETWORK, "the Network access section")   # em dash
        self.assertNotIn(chr(0x2013), NETWORK, "the Network access section")   # en dash
        self.assertNotIn("fleet", NETWORK.lower(), "the Network access section")


if __name__ == "__main__":
    unittest.main()
