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


class TheNewProse(_Pins):
    def test_no_em_or_en_dash_and_not_the_banned_word(self):
        self.assertNetwork()
        self.assertQuoted("`%s=off`" % VAR, NETWORK, self.DOC)
        self.assertNotIn(chr(0x2014), NETWORK, "the Network access section")   # em dash
        self.assertNotIn(chr(0x2013), NETWORK, "the Network access section")   # en dash
        self.assertNotIn("fleet", NETWORK.lower(), "the Network access section")


if __name__ == "__main__":
    unittest.main()
