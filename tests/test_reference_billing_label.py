#!/usr/bin/env python3
"""docs/reference.md's Billing paragraphs say what ui/webview/billing-label.ts renders.

Review round 1 of the billing-label fix (2026-09-09) found the reference describing a `Login (CLI reports
API key)` Billing row the code never produced, in two places: the fix rewrote the hover-row paragraph and
missed the apiKeyHelper how-to, and no test read either, so the drift was silent. These pins hold the doc's
words to the module's strings, so a wording change in billing-label.ts reddens here before the doc goes
stale:

- the warning form the hover-row paragraph quotes is the one billingRowText builds (its fragments are read
  off billing-label.ts, and the doc's line wrap inside the quote is collapsed before comparing);
- the retired `(CLI reports API key)` form appears nowhere in the reference;
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
  claim to ONE sentence (the fork's restored sentence and upstream's helper sentence were folded into it).

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
    """Collapse hard wraps so an assertion survives a rewrap."""
    return re.sub(r"\s+", " ", text).strip()


REFERENCE = _flat(_read("docs", "reference.md"))
BILLING = _read("ui", "webview", "billing-label.ts")

# billingRowText's contradicted branch, assembled from the module's own fragments: `⚠ <side> picked, but the
# CLI reports <the API key|the login>; this session bills that`
WARNING_HEAD = " picked, but the CLI reports "
WARNING_TAIL = "; this session bills that"


class TheWarningFormIsTheModules(unittest.TestCase):
    def test_the_module_builds_the_warning_from_the_pinned_fragments(self):
        self.assertIn("`⚠ ${billingSide(f.auth || \"\")} picked, but the CLI reports `", BILLING)
        self.assertIn("`${f.authLive === \"key\" ? \"the API key\" : \"the login\"}; this session bills that`", BILLING)
        self.assertIn('return side === "key" ? "API key" : (acct ? `Login (${acct})` : "Login");', BILLING,
                      "billingSide's labels: the key is 'API key', never any key material")

    def test_the_hover_row_paragraph_quotes_the_warning_the_module_renders(self):
        # the login-picked, key-landed case, as billingRowText words it
        quoted = "`⚠ Login" + WARNING_HEAD + "the API key" + WARNING_TAIL + "`"
        self.assertIn(quoted, REFERENCE, "the hover-row paragraph quotes billingRowText's warning form")
        self.assertIn("A default nobody picked is never worded that way: a session started unpicked on a box "
                      "whose `apiKeyHelper` supplies the key reads `API key`.", REFERENCE)


class TheRetiredFormIsGone(unittest.TestCase):
    def test_the_switching_paragraph_names_the_applying_texts_the_module_renders(self):
        # the reference once promised the effort badge's switching dots for a pending billing pick; nothing renders
        # dots for one, the two applying texts are billing-label.ts's (verification round 3, 2026-09-09)
        self.assertIn("the menu entry's sub-line reads `applying…`", REFERENCE)
        self.assertIn('if (f.authPending) return "applying…";', BILLING)
        self.assertNotIn("switching-dots the effort", REFERENCE)

    def test_no_paragraph_promises_the_login_cli_reports_api_key_row(self):
        self.assertNotIn("CLI reports API key)", REFERENCE,
                         "the `Login (CLI reports API key)` row never existed in the code; the how-to carried it "
                         "after the hover-row paragraph was fixed")
        self.assertNotIn("(CLI reports", REFERENCE)

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
        self.assertIn("Once the session's CLI has reported which credential it found (its init names the source), "
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
