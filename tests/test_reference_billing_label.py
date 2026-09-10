#!/usr/bin/env python3
"""docs/reference.md's Billing paragraphs quote what ui/webview/billing-label.ts renders.

The tab hover's `Billing` row and the tab menu's Billing sub-line each have four readings: the plain side,
a pick still applying, a pick this machine cannot bill, and a pick the CLI's own report contradicts. The
reference describes them by quoting the rendered text, and nothing else ties the two files together, so
these pins hold the doc to the code: the copy each reading is built from is asserted in the module that
renders it, and the doc is asserted to quote the readings assembled from that same copy. A wording change
in the module reddens here before the reference goes stale, and a retired reading cannot linger in the doc.

Upstream's copy of this module (romp-on/romp #1182, this fork's own offer) pins ui/webview/render.ts, which
renders the row inline there. In this fork render.ts hands the row, the sub-line and the picker's written-out
choice to billing-label.ts (the fork's one renderer, kept under the 2026-09-09 fold's ruling C), so the copy
pins read that module, one pin holds render.ts to calling it, and one holds kernel/credentials.py's WHY_NO_LOGIN
assignment to the sentence the unavailable reading interpolates, so that name is pinned too: the row renders the
frame's loginWhy, which kernel.py fills from that constant (ui/webview/billing-one-auth.test.ts pins the routing
by the same name), and the bare sentence would match any constant that carried it. The other copy pins
(BillingLabelRendersThePinnedCopy's row and sub-line tests, and TheReferenceQuotesEachReading) are the rendered
text, not the expressions around it: a rename, a reshuffle or a further extraction that leaves every rendered
word as it was keeps them green, since the doc is not stale then. Where a fragment is a common word
(`unavailable`) or the warning glyph, the template quote beside it is included, so the pin names the row's own
copy and not a comment or another control's. Two readings keep the fork's punctuation (`(applying, not confirmed
yet)`, `; this session bills that`) where upstream's inline copy uses an em dash: the doc quotes what this tree
renders.

The fork's earlier pins (the billing-label fix's review round 1 and the slice-2 fold, 2026-09-09) stay beside
them, each holding a doc claim to the code it describes. Three read billing-label.ts's expressions on purpose,
the templates, branch and gate the doc's claims rest on (TheWarningFormIsTheModules's two warning templates and
billingSide's body, TheRetiredFormIsGone's authPending branch, ThePickerRowClaimMatchesTheGate's `const show`
gate), so renaming those identifiers reddens here with every rendered word unchanged. Two round-1 pins that the
offer's rewrite dropped and upstream landed under other names retired in the slice-3 fold, an offer coming home
converging on upstream's landed text: the absence of the retired `(CLI reports API key)` form is pinned by
test_no_retired_reading_lingers now, and the contradicted reading's quote by test_the_contradicted_pick_reading.
What stays:

- the warning form the hover-row paragraph quotes is the one billingRowText builds, pinned as the module's two
  template expressions and billingSide's labels (the key is `API key`, never key material);
- no paragraph promises the effort badge's switching dots for a pending billing pick (nothing renders dots for
  one: the two applying texts are billing-label.ts's, and the applying branch is pinned);
- the how-to says the picker and the tooltip row read Claude Code's apiKeyHelper setting to know a key exists
  (the key choice exists when the settings carry a helper; the row follows the CLI's report, and before it the
  launch intent), and no longer names a `Login (...)` reading for it; the fork's `romp keyswap --cycle` pin
  retired with the command (upstream #1128, folded in slice 2);
- the picker paragraph's claim that the row writes out `API key` on a declared helper box with no login
  matches pickerBillingRow's gate (a declared key shows the row);
- the ROMP_EXPECTED_AUTH paragraph states the unpicked rule in one sentence (the fold of upstream #1128,
  slice 2, 2026-09-09): with a helper the key is billed and the declaration is checked against the CLI's
  report (sdk_backend.unpicked_auth reads key_available first, _note_auth_source judges the landing); without
  one the declaration seeds the label. tests/test_session_auth.py executes the helper-box half and
  tests/test_expected_auth.py the seeding half; the pin here holds the words to them, and holds the seeding
  claim to ONE sentence (the fork's restored sentence and upstream's helper sentence were folded into it);
- a default nobody picked is never worded as a contradicted pick (slice-2 ruling 10: billingContradicted
  reads authPicked), the doc says so beside the contradicted reading, and the readings are described in ONE
  paragraph (ruling C of the slice-3 fold), not upstream's beside the fork's.

Text only: labels, never key material.
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


REFERENCE = _flat(_read("docs", "reference.md"))
BILLING = _read("ui", "webview", "billing-label.ts")
RENDER = _read("ui", "webview", "render.ts")
CREDENTIALS = _read("kernel", "credentials.py")

# The hover row's readings, as billing-label.ts assembles them: the side word first, then these fragments
# around an interpolated reason or side.
WARN = "⚠ "
PENDING = " (applying, not confirmed yet)"     # the fork's punctuation; upstream's inline row: " (applying — not confirmed yet)"
UNAVAILABLE_HEAD = " picked, but "
FELL_TAIL = " — this session bills "
NO_FALL_TAIL = " — nothing to fall to, so the launch went out as picked"
CONTRADICTED_HEAD = " picked, but the CLI reports "
CONTRADICTED_TAIL = "; this session bills that"   # the fork's punctuation; upstream's inline row: " — this session bills that"
# The side words the row starts each reading with, and the ones it names a fall or a report with.
HOVER_SIDES = ('"API key"', '"Login"', '"the API key"', '"the login"')
ACCOUNT_FORM = "Login (${"   # the login side with its account name: `Login (name@example.com)` in the doc
# The tab menu's shorter mirror of each reading.
MENU_PENDING = '"applying…"'
MENU_UNAVAILABLE = " unavailable"
MENU_FELL = ", billing "
MENU_CONTRADICTED = "⚠ CLI reports "
MENU_SIDES = ('"API key"', '"login"')
# The kernel's reason for a login pick on a machine with no login, which the hover row interpolates.
WHY_NO_LOGIN = "no Claude login signed in on this machine"


class _Pins(unittest.TestCase):
    def assertQuoted(self, needle, haystack, where, msg=""):
        # a bare assertIn would print the whole file on a miss; name the missing text and the file instead
        self.assertTrue(needle in haystack, "%s does not carry %r%s" % (where, needle, (": " + msg) if msg else ""))

    def assertNotQuoted(self, needle, haystack, where, msg=""):
        self.assertFalse(needle in haystack, "%s still carries %r%s" % (where, needle, (": " + msg) if msg else ""))


class BillingLabelRendersThePinnedCopy(_Pins):
    """Upstream's RenderTsRendersThePinnedCopy, aimed at the module this fork renders the copy from."""
    SRC = "ui/webview/billing-label.ts"

    def test_the_hover_row(self):
        self.assertQuoted('"%s"' % PENDING, BILLING, self.SRC)
        self.assertQuoted("`" + WARN, BILLING, self.SRC, "the warning glyph opens the warning readings")
        self.assertQuoted(UNAVAILABLE_HEAD, BILLING, self.SRC)
        self.assertQuoted(FELL_TAIL, BILLING, self.SRC)
        self.assertQuoted('"%s"' % NO_FALL_TAIL, BILLING, self.SRC)
        self.assertQuoted(CONTRADICTED_HEAD, BILLING, self.SRC)
        self.assertQuoted(CONTRADICTED_TAIL, BILLING, self.SRC)
        for side in HOVER_SIDES:
            self.assertQuoted(side, BILLING, self.SRC, "the key is 'API key', never any key material")
        self.assertQuoted(ACCOUNT_FORM, BILLING, self.SRC)

    def test_the_tab_menu_sub_line(self):
        self.assertQuoted(MENU_PENDING, BILLING, self.SRC)
        self.assertQuoted(MENU_UNAVAILABLE + "`", BILLING, self.SRC, "the word ends the sub-line's template piece")
        self.assertQuoted(MENU_FELL, BILLING, self.SRC)
        self.assertQuoted(MENU_CONTRADICTED, BILLING, self.SRC)
        for side in MENU_SIDES:
            self.assertQuoted(side, BILLING, self.SRC)

    def test_the_kernel_reason_the_unavailable_reading_interpolates(self):
        self.assertQuoted('WHY_NO_LOGIN = "%s"' % WHY_NO_LOGIN, CREDENTIALS, "kernel/credentials.py")

    def test_render_ts_renders_the_row_and_sub_line_through_the_module(self):
        # the doc's "as rendered" claim holds only while render.ts shows the module's text and no inline copy
        self.assertQuoted('rows.push(["Billing", billingRowText(s.status)]);', RENDER, "ui/webview/render.ts")
        self.assertQuoted("sb.textContent = billingSubText(st);", RENDER, "ui/webview/render.ts")
        self.assertNotQuoted(CONTRADICTED_HEAD, RENDER, "ui/webview/render.ts", "the copy lives in billing-label.ts alone")
        self.assertNotQuoted(UNAVAILABLE_HEAD, RENDER, "ui/webview/render.ts", "the copy lives in billing-label.ts alone")


class TheWarningFormIsTheModules(unittest.TestCase):
    def test_the_module_builds_the_warning_from_the_pinned_fragments(self):
        self.assertIn("`⚠ ${billingSide(f.auth || \"\")} picked, but the CLI reports `", BILLING)
        self.assertIn("`${f.authLive === \"key\" ? \"the API key\" : \"the login\"}; this session bills that`", BILLING)
        self.assertIn('return side === "key" ? "API key" : (acct ? `Login (${acct})` : "Login");', BILLING,
                      "billingSide's labels: the key is 'API key', never any key material")

    def test_the_default_nobody_picked_sentence_stands_beside_the_warning(self):
        # the warning quote itself (the login-picked, key-landed case) is TheReferenceQuotesEachReading's
        # test_the_contradicted_pick_reading, upstream's landed pin; this holds the fork's sentence beside it
        # (slice-2 ruling 10: billingContradicted reads authPicked)
        self.assertIn("A default nobody picked is never worded that way: a session started unpicked on a box "
                      "whose `apiKeyHelper` supplies the key reads `API key`.", REFERENCE)


class TheReferenceQuotesEachReading(_Pins):
    DOC = "docs/reference.md"

    def test_the_plain_readings(self):
        self.assertQuoted("`API key` or `Login (name@example.com)`", REFERENCE, self.DOC)

    def test_the_applying_reading(self):
        self.assertQuoted("`Login%s`" % PENDING, REFERENCE, self.DOC)
        self.assertQuoted("`applying…`", REFERENCE, self.DOC, "the tab menu's sub-line while the switch applies")

    def test_the_unavailable_pick_reading(self):
        self.assertQuoted("`%sLogin%s%s%sthe API key`" % (WARN, UNAVAILABLE_HEAD, WHY_NO_LOGIN, FELL_TAIL),
                          REFERENCE, self.DOC)
        self.assertQuoted("`%slogin%s%sAPI key`" % (WARN, MENU_UNAVAILABLE, MENU_FELL), REFERENCE, self.DOC,
                          "the tab menu's sub-line")

    def test_the_contradicted_pick_reading(self):
        self.assertQuoted("`%sLogin%sthe API key%s`" % (WARN, CONTRADICTED_HEAD, CONTRADICTED_TAIL), REFERENCE, self.DOC)
        self.assertQuoted("`%sAPI key`" % MENU_CONTRADICTED, REFERENCE, self.DOC, "the tab menu's sub-line")

    def test_no_retired_reading_lingers(self):
        # the CLI's report is not a parenthetical after the side: the row leads with the warning
        # (billing-label.ts's contradicted reading)
        self.assertNotQuoted("(CLI reports", REFERENCE, self.DOC)

    def test_the_readings_are_described_in_one_paragraph(self):
        # ruling C (slice 3, 2026-09-09): upstream's four-readings paragraph and the fork's contradicted-pick
        # paragraph were reconciled into one; a second copy of either quote is the two-paragraph state
        self.assertEqual(REFERENCE.count("The row has four readings"), 1)
        self.assertEqual(REFERENCE.count("`%sLogin%sthe API key%s`" % (WARN, CONTRADICTED_HEAD, CONTRADICTED_TAIL)), 1)
        self.assertEqual(REFERENCE.count("`Login%s`" % PENDING), 1)


class TheRetiredFormIsGone(unittest.TestCase):
    def test_the_switching_paragraph_names_the_applying_texts_the_module_renders(self):
        # the reference once promised the effort badge's switching dots for a pending billing pick; nothing renders
        # dots for one, the two applying texts are billing-label.ts's (verification round 3, 2026-09-09)
        self.assertIn("the menu entry's sub-line reads `applying…`", REFERENCE)
        self.assertIn('if (f.authPending) return "applying…";', BILLING)
        self.assertNotIn("switching-dots the effort", REFERENCE)

    def test_the_apikeyhelper_how_to_says_the_row_reads_the_helper_setting(self):
        # upstream #1128 (folded in slice 2): romp holds no key of its own, so the how-to's row claims follow
        # Claude Code's apiKeyHelper setting. The fork's "reads `API key` once its CLI has reported the helper's
        # key (before that, the declared side, else `Login`)" and "the Billing picker offers no API-key buttons"
        # sentences are superseded (the key choice exists whenever the settings carry a helper, and an unpicked
        # session bills the key there before any declaration); the pins follow the resolved doc.
        self.assertIn("Romp never sees the key: the Billing picker and the tooltip row read the setting to know "
                      "that a key exists, and no surface of romp's fetches it.", REFERENCE)
        self.assertIn("The key choice exists when Claude Code's settings for the kernel's working directory carry "
                      "a helper; romp reads the setting and never runs it for this.", REFERENCE)
        self.assertIn("once the session's CLI has reported which credential it found (its init names the source), "
                      "the row shows that side; before any report it shows the intent the session was launched "
                      "with.", REFERENCE)
        # the fork's `romp keyswap --cycle` clause (kernel/sdk_backend.py cycle_key's no-source branch) retired
        # with the command: rotation is the vault item's, and the CLI re-runs the helper (#1128)
        self.assertNotIn("keyswap --cycle", REFERENCE)


class ThePickerRowClaimMatchesTheGate(unittest.TestCase):
    def test_the_declared_helper_box_shows_the_row_with_no_login(self):
        self.assertIn('const show = !!(a && (a.login || a.key || a.default === "key"));', BILLING,
                      "pickerBillingRow shows the row for a declared key with neither credential of romp's")
        self.assertIn("when that side is the key, the picker's Billing row writes `API key` out even when the box "
                      "has no Claude login to show beside it", REFERENCE)

    def test_the_set_aside_pick_exception_is_documented_where_inertness_is(self):
        self.assertIn("The one exception is an API-key pick remembered from a box that no longer holds a key: it "
                      "is set aside at spawn, so it seeds nothing, and the declaration decides the unpicked "
                      "default again", REFERENCE)
        # the same set-aside in the label paragraph, in upstream's words (#1128 replaced the fork's parenthetical
        # "an API-key pick remembered from a box that held a key is set aside once it holds none")
        self.assertIn("A remembered key pick on a box whose settings carry no helper leaves new sessions unpicked, "
                      "and the kernel log says so once, naming the settings file to configure.", REFERENCE)
        # upstream #1147's one-auth paragraph, reconciled with that rule: a set-aside default falls to the
        # unpicked rule (the helper's key, else the declared side, else the login), never straight to a side
        self.assertIn("A remembered default that names the side this box cannot bill is set aside at spawn and the "
                      "unpicked rule below decides instead, in both directions", REFERENCE)


class TheDeclarationRuleIsOneSentence(unittest.TestCase):
    def test_the_rule_names_both_halves(self):
        self.assertIn("With a helper configured, an unpicked session bills the key whatever the box declares, and "
                      "the declaration is checked against the CLI's report at each init, never applied as a label "
                      "(`ROMP_EXPECTED_AUTH=key` describes such a box truthfully and stays quiet; "
                      "`ROMP_EXPECTED_AUTH=login` flags every unpicked session's keyed landing in the Log panel, and "
                      "the session keeps billing the key); without a helper, the declaration seeds what an unpicked "
                      "session is *taken* to bill: the Billing row's fallback before the CLI has reported, the "
                      "picker's written-out choice, and the spend pause's reading of a session that reports nothing "
                      "all read the declared side, where they read the login before.", REFERENCE)

    def test_the_seeding_claim_is_made_once(self):
        # the fork's restored "The declaration also decides what an unpicked session is *taken* to bill when no
        # helper is configured" and upstream's "On a box with a helper every session without a login pick bills
        # the key, so `ROMP_EXPECTED_AUTH=key` describes such a box truthfully" were two claims over the halves
        # of one rule; the paragraph carries the rule once
        self.assertEqual(REFERENCE.count("all read the declared side"), 1)
        self.assertEqual(REFERENCE.count("describes such a box truthfully"), 1)
        self.assertNotIn("The declaration also decides what an unpicked session", REFERENCE)


if __name__ == "__main__":
    unittest.main()
