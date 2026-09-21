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

Text only: the behaviour is pinned in tests/test_price_feed_off.py (the kernel), the reference's prose in
tests/test_reference_price_feed.py. The documents and the sources are read as files; nothing loads romp
code, so no state root is minted. Every case asserts SECURITY.md's text FIRST, so a run over a tree
without the paragraph fails at that assertion and never at a missing symbol.
"""
import os
import re
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
    """The review of PR 878: the section's claim is the derivation's, stated positively. Each case asserts the
    section's text first; over the d1026b768 archive every case is red at that assertion (the section there says
    romp makes one outbound request by default and carries none of these phrases), and green at the tree."""

    def test_the_old_quantifier_is_gone_and_the_scoped_sentence_stands(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted(SCOPED, flat, self.DOC, "the claim is scoped to the kernel's own connections, by the derivation")
        self.assertQuoted(PARSED, flat, self.DOC, "the section keeps saying what the response is")
        self.assertQuoted("`%s=off`" % VAR, NETWORK, self.DOC)
        self.assertNotIn(OLD_QUANTIFIER, flat,
                         "%s: 'romp makes one outbound request by default' was false with the feed off and nothing "
                         "configured (the catalog refresh and the release check's git ls-remote still run)" % self.DOC)

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
        self.assertQuoted("`git ls-remote` against the release remote for the release check", flat, self.DOC)
        self.assertQuoted("drift check", flat, self.DOC)
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

    def test_it_names_the_roads_that_open_once_set_up_and_the_settings_that_hold_them(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("Every other connection opens once you set it up", flat, self.DOC)
        for phrase in ("an attached machine", "a PR watch (`gh`) or a watch predicate a session registered",
                       "a subscribed phone (web push, encrypted end to end)",
                       "the apiKeyHelper or stored-login command you configured",
                       "an update taken from the banner or by the auto mode", PICTURES,
                       "Installing by hand (`bootstrap.sh`, `install.sh`)"):
            self.assertQuoted(phrase, flat, self.DOC)
        self.assertQuoted("### Pictures from the web in a viewed file", REFERENCE, "docs/reference.md",
                          "the setting the section names is documented under that heading")
        self.assertQuoted("**%s**" % PICTURES, REFERENCE, "docs/reference.md", "the gear's name for the setting")
        for name in ("def _spawn_tunnel(", "def _pr_watch_read(", "def _watch_run(", "def _push_post("):
            self.assertQuoted(name, KERNEL, "kernel/kernel.py", "a road the section names, by the function that runs it")

    def test_what_a_program_the_kernel_starts_sends_is_that_programs_and_the_telemetry_claim_is_scoped(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("What those programs send is theirs, not the kernel's", flat, self.DOC)
        for name in ("a session's own CLI", "the judges' CLIs", "a watch predicate", "the API key helper",
                     "a login's token program", "`gh`, `git`, `ssh`, `npm` and the browser"):
            self.assertQuoted(name, flat, self.DOC, "a program that opens connections the kernel does not see")
        self.assertQuoted("romp sends no telemetry", flat, self.DOC)
        self.assertQuoted("Session text goes only to the model provider the session or the judge call is billed to", flat, self.DOC)
        self.assertQuoted("encrypted end to end, to the push service of a phone you subscribed", flat, self.DOC)
        self.assertNotIn(OLD_TELEMETRY, flat,
                         "%s: session text does reach the model provider (the sessions and the judges) and, encrypted, a "
                         "subscribed phone's push service; the claim is scoped to what the code does" % self.DOC)

    def test_the_switch_paragraph_states_the_value_rule_the_kernel_applies(self):
        self.assertNetwork()
        flat = _flat(NETWORK)
        self.assertQuoted("Only the value `off`, whitespace and case ignored, turns the feed off", flat, self.DOC)
        self.assertQuoted("any other value leaves it on, and the kernel says so on its stderr, on that line and in that block",
                          flat, self.DOC, "a misspelt switch fails open and is said, never silent")
        self.assertQuoted("def _price_feed_unrecognised():", KERNEL, "kernel/kernel.py",
                          "the read that says so; executed in tests/test_price_feed_off.py OffSwitch")
        self.assertQuoted('.strip().lower() == "off"', KERNEL, "kernel/kernel.py", "the rule: stripped and case-folded, equal to off")


class TheNewProse(_Pins):
    def test_no_em_or_en_dash_and_not_the_banned_word(self):
        self.assertNetwork()
        self.assertQuoted("`%s=off`" % VAR, NETWORK, self.DOC)
        self.assertNotIn(chr(0x2014), NETWORK, "the Network access section")   # em dash
        self.assertNotIn(chr(0x2013), NETWORK, "the Network access section")   # en dash
        self.assertNotIn("fleet", NETWORK.lower(), "the Network access section")


if __name__ == "__main__":
    unittest.main()
