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

Text only: the behaviour is pinned in tests/test_price_feed_off.py (the kernel), the reference's prose in
tests/test_reference_price_feed.py. The documents and the sources are read as files; nothing loads romp
code, so no state root is minted (the table case runs scripts/network-inventory.py, a standard-library scan
of the tree, by subprocess). Every case asserts SECURITY.md's text FIRST, so a run over a tree without the
paragraph fails at that assertion and never at a missing symbol or a script that lacks the flag.
"""
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
EDITOR_PROMPT = "the editor extension's update prompt runs the same `install.sh` on your click"
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
        "an update taken from the banner or by the auto mode (`git fetch`, then for a release `install.sh` with pip and npm",),
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
    "update prompt)": ("and the npm registry", EDITOR_PROMPT),
    "bin/romp-codex-setup (install-time-by-hand)": (
        "`bin/romp-codex-setup`, run by hand for Codex sessions, fetches the Codex SDK from PyPI and the pinned Codex CLI from GitHub",),
    "local, set aside and counted (local)": (),          # nothing leaves the machine: no sentence owed
    "an external program the kernel starts, far end not derivable here (not derivable by this scan)": (
        "an external program the kernel starts whose far end its arguments do not show",),
    "a program supplied at run time (not derivable by this scan)": ("a program whose text is supplied at run time",),
    "a browser request whose URL is computed at run time (not derivable by this scan)": (
        "a browser request whose URL is computed at run time",),
    "the browser DOM's own loads (not derivable by this scan)": ("the loads the browser makes on its own for what a page inserts",),
}
KERNEL_REQUEST_ROWS = ("price feed", "model catalog refresh", "fast-mode organisation probe", "web push")
_TABLE = []


def _pydef(src, name):
    """The text of top-level `def name(...)` up to the next top-level def or class; "" when absent."""
    m = re.search(r"^def " + re.escape(name) + r"\(.*?(?=^(?:def|class) |\Z)", src, re.S | re.M)
    return m.group(0) if m else ""


def _table():
    """The rows of `python3 scripts/network-inventory.py --table`, run once over ROOT: a list of (label, kind) from the
    first cell, header and separator dropped. Parsed from stdout whatever the exit status: the gates (a count that
    drifted, a site with no road) are tests/test_price_feed_census.py's finding, and this module's is the section."""
    if not _TABLE:
        p = subprocess.run([sys.executable, os.path.join(ROOT, INVENTORY), "--table", ROOT],
                           capture_output=True, text=True, timeout=120)
        rows = []
        for line in p.stdout.splitlines():
            if not line.startswith("| ") or line.startswith("| road |") or line.startswith("|---"):
                continue
            label = line.split("|")[1].strip()
            kind = label[label.rfind("(") + 1:-1] if label.endswith(")") else ""
            rows.append((label, kind))
        _TABLE.append((rows, p.returncode, p.stderr[-2000:]))
    return _TABLE[0]


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
        self.assertQuoted("install.sh", EXTENSION, "vscode-extension/src/extension.ts")
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
        labels = [label for label, _ in rows]
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
        kernel_request = [label[:label.rfind(" (")] for label, kind in rows if kind == "kernel-request"]
        self.assertEqual(kernel_request, list(KERNEL_REQUEST_ROWS),
                         "the kernel's own requests to hosts other than an attached machine are the table's kernel-request "
                         "rows, and the telemetry sentence names those four; a fifth is a new sentence")
        for road in kernel_request:
            self.assertTrue(ROAD_PHRASES["%s (kernel-request)" % road], "the row %r has words in the section" % road)
        classes = [label for label, kind in rows if kind == "not derivable by this scan"]
        self.assertEqual(len(classes), 4, "the four classes the scan cannot derive are rows of the table: %r" % classes)
        for label in classes:
            for phrase in ROAD_PHRASES[label]:
                self.assertQuoted(phrase, flat, self.DOC, "a class the scan cannot see, named in the section")


class TheNewProse(_Pins):
    def test_no_em_or_en_dash_and_not_the_banned_word(self):
        self.assertNetwork()
        self.assertQuoted("`%s=off`" % VAR, NETWORK, self.DOC)
        self.assertNotIn(chr(0x2014), NETWORK, "the Network access section")   # em dash
        self.assertNotIn(chr(0x2013), NETWORK, "the Network access section")   # en dash
        self.assertNotIn("fleet", NETWORK.lower(), "the Network access section")


if __name__ == "__main__":
    unittest.main()
