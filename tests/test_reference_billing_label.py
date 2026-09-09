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
- the how-to says an unpicked session's row reads `API key`, the label billingSide gives the key, and no
  longer names a `Login (...)` reading for it;
- the picker paragraph's claim that the row writes out `API key` on a declared helper box with no login
  matches pickerBillingRow's gate (a declared key shows the row).

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
    def test_no_paragraph_promises_the_login_cli_reports_api_key_row(self):
        self.assertNotIn("CLI reports API key)", REFERENCE,
                         "the `Login (CLI reports API key)` row never existed in the code; the how-to carried it "
                         "after the hover-row paragraph was fixed")
        self.assertNotIn("(CLI reports", REFERENCE)

    def test_the_apikeyhelper_how_to_says_the_row_reads_api_key(self):
        self.assertIn("a session's Billing row reads `API key` once its CLI has reported the helper's key "
                      "(before that report it shows the side `ROMP_EXPECTED_AUTH` declares, else `Login`)",
                      REFERENCE)
        self.assertIn("the Billing picker offers no API-key buttons (under `ROMP_EXPECTED_AUTH=key` its Billing "
                      "row writes out `API key` as the one applying choice)", REFERENCE)
        # the keyswap clause stays: with no key source configured the cycle classifies every session as the
        # login (kernel/sdk_backend.py cycle_key's no-source branch), whatever the CLI reported
        self.assertIn("`romp keyswap --cycle` skips every session as billing the login", REFERENCE)


class ThePickerRowClaimMatchesTheGate(unittest.TestCase):
    def test_the_declared_helper_box_shows_the_row_with_no_login(self):
        self.assertIn('const show = !!(a && (a.login || a.key || a.default === "key"));', BILLING,
                      "pickerBillingRow shows the row for a declared key with neither credential of romp's")
        self.assertIn("the picker's Billing row writes that out even when the box has no Claude login to show "
                      "beside it", REFERENCE)

    def test_the_set_aside_pick_exception_is_documented_where_inertness_is(self):
        self.assertIn("The one exception is an API-key pick remembered from a box that no longer holds a key: it "
                      "is set aside at spawn, so it seeds nothing, and the declaration decides the unpicked "
                      "default again", REFERENCE)
        self.assertIn("an API-key pick remembered from a box that held a key is set aside once it holds none: the "
                      "picker cannot offer it, and such a session starts unpicked", REFERENCE)


if __name__ == "__main__":
    unittest.main()
