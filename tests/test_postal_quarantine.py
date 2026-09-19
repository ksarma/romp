#!/usr/bin/env python3
"""Per-host trust model, bus side (postal_service): the inbound gate in _relay_in holds mail from a
DIRECTED peer for human approval instead of injecting it, delivers a TRUSTED peer's mail as today, and
silently drops an ISOLATED peer's mail. The quarantine store + quarantine_decide (approve/deny) back the
feed's blocked card. peer_update carries the per-host trust the gate reads.

Synthetic only — hermetic temp state dir, placeholder mids, invented notes-domain sessions, no real data.
"""
import contextlib
import errno
import json
import os
import sys
import tempfile
import threading
import unittest
from romp_load import load_source
from pathlib import Path
from unittest import mock

from tests.conftest import restore_env

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
# One live local session ("web") via the sessions-file seam (no live kernel needed).
_SESS = os.path.join(os.environ["XDG_STATE_HOME"], "sessions.json")
Path(_SESS).write_text(json.dumps([{"id": "sess-web", "name": "web", "dir": "/tmp/notes-api",
                                    "state": "waiting", "working": ""}]))
os.environ["ROMP_SESSIONS_FILE"] = _SESS
ps = load_source("romp_postal_quar", os.path.join(BIN, "romp-postal-service"))

DEPTH = 100000                                     # past every Python's recursion limit; the free-threaded 3.14 parser takes it
DEEP = "[" * DEPTH + "]" * DEPTH


def _deep_list(depth=DEPTH):
    """The value the free-threaded 3.14 parser returns for DEEP, built iteratively: nothing here parses or formats it."""
    v = []
    for _ in range(depth):
        v = [v]
    return v


@contextlib.contextmanager
def _parser_returning(values):
    """json.loads as the free-threaded Python 3.14 answers a document nested past its predecessors' limit, on every
    Python: a text that starts with one of `values`' keys returns that value, and every other text goes to the real
    parser (the good hold beside it, the route's own reply). The bus calls json.loads through the module, so the patch
    on the module's attribute is what its readers see, on the handler thread too."""
    real = json.loads

    def loads(text, *a, **kw):
        for prefix, value in values.items():
            if text.startswith(prefix):
                return value
        return real(text, *a, **kw)
    with mock.patch.object(json, "loads", loads):
        yield


def _relay(mid, body="ship it", frm="api", origin=None):
    m = {"mid": mid, "to": "web", "frm": frm, "frm_id": "id-" + frm, "body": body, "kind": "coordinate"}
    if origin:
        m["origin"] = origin
    return m


class InboundTrustGate(unittest.TestCase):
    def setUp(self):
        self._prior_seam = os.environ.get("ROMP_SESSIONS_FILE")
        os.environ["ROMP_SESSIONS_FILE"] = _SESS   # pin OUR sessions seam (read live; a later-collected postal test clobbers it)
        # fresh peer table + empty stores each test
        ps.PEERS.clear()
        ps._REFUSAL_SAID.clear()                     # no refusal episode left open by an earlier test
        for d in (ps.QUARANTINE, ps.MAILROOT / "sess-web" / "new"):
            try:
                for f in d.glob("*"):
                    f.unlink()
            except OSError:
                pass

    def tearDown(self):
        restore_env("ROMP_SESSIONS_FILE", self._prior_seam)

    def _set_trust(self, host, level, up=True):
        ps.peer_update({"host": host, "port": 47101, "up": up, "trust": level})

    def test_trusted_delivers(self):
        self._set_trust("TESTHOST", "trusted")
        verdict, _ = ps._relay_in("TESTHOST", _relay("q-trusted-1"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(ps.quarantine_list(), [], "trusted mail must NOT be quarantined")
        box = ps.read_box("sess-web", consume=False)
        self.assertTrue(any("ship it" in (msg.get("body") or "") for msg in box),
                        "trusted mail must be delivered to the recipient's maildir")

    def test_directed_quarantines(self):
        self._set_trust("TESTHOST", "directed")
        verdict, _ = ps._relay_in("TESTHOST", _relay("q-directed-1"))
        self.assertEqual(verdict, "ack", "the sender is ack'd (stops resending) even though it's held")
        held = ps.quarantine_list()
        self.assertEqual(len(held), 1)
        self.assertEqual(held[0]["mid"], "q-directed-1")
        self.assertEqual(held[0]["to"], "web")
        self.assertEqual(held[0]["origin"], "TESTHOST")
        self.assertEqual(ps.read_box("sess-web", consume=False), [],
                         "directed mail must NOT reach the session until approved")

    def test_a_hold_that_could_not_be_written_answers_retry_not_ack(self):
        """_quarantine_put says False when the hold file could not be written (ENOSPC, a permission
        bit, a store path that is not a directory), and the directed arm ignored it: the sender was
        ack'd, deleted its record and read 'delivered' forever, the mid was marked seen so the
        re-relay was deduped away, and no hold existed for anyone to approve. The False is now read
        the way the trusted arm reads DeliveryNotRecorded: silence on the wire, nothing marked seen,
        so the sender keeps its record and the re-relay is held once the store writes again. The fault
        also reaches the USER, the way deliver() says a refused publish: one bell row per episode (the
        re-relay that meets the same store is said in the log only), re-armed by the next hold that lands."""
        self._set_trust("TESTHOST", "directed")
        blocker = ps.QUARANTINE.parent / "hold-blocker"
        blocker.parent.mkdir(parents=True, exist_ok=True)   # nothing creates the state dir at import
        blocker.write_text("")                       # a regular file where the store's parent must be
        saved, saved_log, saved_post, logged, told = ps.QUARANTINE, ps._log, ps._kernel_post, [], []
        ps.QUARANTINE = blocker / "quarantine"       # every mkdir/write under it fails with ENOTDIR
        ps._log = lambda line: logged.append(line)
        ps._kernel_post = lambda path, body, timeout=2: told.append((path, body)) or {"ok": True}
        try:
            # twice: the sender re-relays next exchange, and the store is still blocked
            verdicts = [ps._relay_in("TESTHOST", _relay("q-hold-fail")) for _ in range(2)]
        finally:
            ps.QUARANTINE, ps._log, ps._kernel_post = saved, saved_log, saved_post
            blocker.unlink()
        self.assertEqual(verdicts, [("retry", None)] * 2, "silence on the wire, both times: the sender keeps it parked and re-relays")
        cause = [l for l in logged if "q-hold-fail" in l and "could not be written" in l and "[Errno %d]" % errno.ENOTDIR in l]
        self.assertEqual(len(cause), 2, "the store says WHY the hold did not land, with the errno, on every refusal: %r" % logged)
        self.assertTrue(any("the sender re-relays" in l for l in logged), "and the arm says what follows: %r" % logged)
        notices = [b["text"] for path, b in told if path == "/postal-notice"]
        self.assertEqual(len(notices), 1, "the user hears it once per episode, not once per exchange: %r" % told)
        self.assertIn("q-hold-fail", notices[0])
        self.assertIn("could not be written", notices[0])
        self.assertIn("quarantine", ps._REFUSAL_SAID, "the episode stays open while the store is blocked")
        self.assertFalse(ps.peer_seen_check("q-hold-fail"), "not marked seen, so the re-relay is processed in full")
        self.assertEqual(ps.quarantine_list(), [], "nothing is held")
        self.assertEqual(ps.read_box("sess-web", consume=False), [], "and nothing reached the session")
        # the re-relay, with the store writing again, is held exactly as a first arrival would be
        self.assertEqual(ps._relay_in("TESTHOST", _relay("q-hold-fail")), ("ack", None))
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], ["q-hold-fail"])
        self.assertTrue(ps.peer_seen_check("q-hold-fail"))
        self.assertNotIn("quarantine", ps._REFUSAL_SAID, "a hold that landed closes the episode: the next refusal is said again")

    def test_a_mid_no_hold_can_be_named_by_bounces_instead_of_retrying_forever(self):
        # The hold is a file named by the mid, so _quarantine_put also says False for an id that
        # cannot be a path component. That False must not read as 'retry': a peer that keeps
        # sending the crafted id would be re-relaying it every exchange. Final refusal instead,
        # and (as before) nothing held, nothing delivered; unlike before, not marked seen or ack'd.
        self._set_trust("TESTHOST", "directed")
        verdict, bounce = ps._relay_in("TESTHOST", _relay("../q-hold-crafted"))
        self.assertEqual(verdict, "bounce", "final: silence would have the sender re-relay it every exchange")
        self.assertEqual(bounce["mid"], "../q-hold-crafted")
        self.assertFalse(ps.peer_seen_check("../q-hold-crafted"))
        self.assertEqual(ps.quarantine_list(), [])
        self.assertEqual(ps.read_box("sess-web", consume=False), [])

    def test_isolated_drops(self):
        self._set_trust("TESTHOST", "isolated")
        verdict, _ = ps._relay_in("TESTHOST", _relay("q-iso-1"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(ps.quarantine_list(), [], "isolated mail is dropped, not held")
        self.assertEqual(ps.read_box("sess-web", consume=False), [], "isolated mail is not delivered")

    def test_unknown_origin_defaults_to_directed(self):
        # No PEERS entry (a race before the kernel notify lands) → safe default: hold, never auto-inject.
        verdict, _ = ps._relay_in("MYSTERY", _relay("q-unknown-1"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(ps.quarantine_list()), 1)
        self.assertEqual(ps.read_box("sess-web", consume=False), [])

    def test_origin_only_trust_row_governs_relayed_mail(self):
        # Trust-by-origin end to end (the user 2026-07-25): the user tiers a host they have NO
        # tunnel to (an origin-only, portless row); its mail arriving relayed through a hub is
        # judged by that tier — trusted injects instead of holding.
        self._set_trust("EDGE", "trusted")                      # the hub we ARE connected to
        ps.peer_update({"host": "ORIGIN", "trust": "trusted", "originOnly": True})
        verdict, _ = ps._relay_in("EDGE", _relay("q-origin-1", origin="ORIGIN"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(list(ps.QUARANTINE.glob("*.json"))), 0,
                         "an origin-only trusted tier delivers, no hold")

    def test_forwarded_origin_is_the_trust_key(self):
        # A 2-hop message carries m["origin"] = the true origin; the gate keys on it, not the direct peer.
        self._set_trust("EDGE", "trusted")       # the direct peer we received from
        self._set_trust("ORIGIN", "directed")    # the true origin — its level governs
        verdict, _ = ps._relay_in("EDGE", _relay("q-fwd-1", origin="ORIGIN"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(ps.quarantine_list()), 1, "the ORIGIN's directed level must hold it")

    def test_a_forwarder_cannot_outrank_itself_by_stamping_a_trusted_origin(self):
        """The origin stamp is written BY the forwarder, so trust keyed on it alone is a claim the
        claimant makes about itself. A peer you tiered `directed` — one you attached but do not let
        drive your sessions — answers one exchange with origin set to a host you DID tier trusted,
        and its mail is auto-injected: pasted into a live session and entered. The names to guess
        are not secret either; presence gossip hands them out. A forwarded message is now capped at
        the forwarder's own tier, so a directed relay stays directed however it labels its cargo."""
        self._set_trust("EDGE", "directed")       # the peer we actually received from
        self._set_trust("ORIGIN", "trusted")      # the name it claims to be speaking for
        verdict, _ = ps._relay_in("EDGE", _relay("q-forge-1", origin="ORIGIN"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(ps.quarantine_list()), 1,
                         "a directed forwarder's mail must hold, whatever origin it stamps")
        self.assertEqual(len(list((ps.MAILROOT / "sess-web" / "new").glob("*"))), 0,
                         "nothing may reach the session's mailbox")

    def test_an_isolated_forwarder_stays_dropped_however_it_labels_its_mail(self):
        # isolated is the strongest refusal the user can express: no communication at all. It must
        # not become a hold (visible, approvable) by stamping a trusted origin.
        self._set_trust("EDGE", "isolated")
        self._set_trust("ORIGIN", "trusted")
        verdict, _ = ps._relay_in("EDGE", _relay("q-forge-2", origin="ORIGIN"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(ps.quarantine_list()), 0, "isolated drops; it never even holds")
        self.assertEqual(len(list((ps.MAILROOT / "sess-web" / "new").glob("*"))), 0)

    def test_the_cap_never_promotes_a_forwarders_mail(self):
        # The cap is a floor-lowering, not a lookup swap: a trusted forwarder relaying a DIRECTED
        # origin's mail must still hold it (the origin's own tier still applies).
        self._set_trust("EDGE", "trusted")
        self._set_trust("ORIGIN", "directed")
        verdict, _ = ps._relay_in("EDGE", _relay("q-forge-3", origin="ORIGIN"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(ps.quarantine_list()), 1)


class LeastTrust(unittest.TestCase):
    def test_the_more_restrictive_tier_wins_either_way_round(self):
        self.assertEqual(ps.least_trust("trusted", "directed"), "directed")
        self.assertEqual(ps.least_trust("directed", "trusted"), "directed")
        self.assertEqual(ps.least_trust("isolated", "trusted"), "isolated")
        self.assertEqual(ps.least_trust("trusted", "trusted"), "trusted")

    def test_an_unrecognised_tier_is_treated_as_directed_not_trusted(self):
        # A tier this build does not know must never read as permission.
        self.assertEqual(ps.least_trust("nonsense", "trusted"), "nonsense")
        self.assertEqual(ps.least_trust("isolated", "nonsense"), "isolated")


class TokenProvenDialerGate(InboundTrustGate):
    """The DIALED side of an exchange (token_proven=True): the dialer showed OUR serve token, which
    already grants full control of this machine, so holding its own mail protects nothing — the user's
    outgoing delegation to a machine they attached used to sit quarantined THERE (2026-07-26). The
    proof exempts only the unknown-origin default: an explicit tier still wins, and forwarded mail is
    still judged by its origin's tier. Inherits InboundTrustGate so every explicit-tier test above
    reruns with token_proven=True — trusted/directed/isolated rows must gate identically."""

    def setUp(self):
        super().setUp()
        ps._seen_ids = None                          # the inherited tests reuse their mids — reset the
        try:                                         # dedupe window so the rerun isn't swallowed as dupes
            ps.PEER_SEEN.unlink()
        except OSError:
            pass
        self._orig_relay_in = ps._relay_in
        ps._relay_in = lambda host, m, token_proven=False: self._orig_relay_in(host, m, token_proven=True)

    def tearDown(self):
        ps._relay_in = self._orig_relay_in
        super().tearDown()

    def test_unknown_origin_defaults_to_directed(self):
        # OVERRIDES the inherited default-hold test: with the dialer token-proven, unknown-origin
        # DIRECT mail delivers instead of holding — that is the point of this gate.
        verdict, _ = ps._relay_in("MYSTERY", _relay("q-tok-1", body="from the attacher"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(ps.quarantine_list(), [], "a token-proven dialer's own mail is not held")
        box = ps.read_box("sess-web", consume=False)
        self.assertTrue(any("from the attacher" in (m.get("body") or "") for m in box),
                        "it is delivered like trusted mail")

    def test_forwarded_unknown_origin_still_held(self):
        # The token proof covers the DIALER only: mail it forwarded from an unknown third machine
        # keeps the safe default — the third machine never proved anything.
        verdict, _ = ps._relay_in("MYSTERY", _relay("q-tok-2", origin="FARBOX"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(ps.quarantine_list()), 1, "forwarded mail is judged by its origin's tier")
        self.assertEqual(ps.read_box("sess-web", consume=False), [])

    def test_explicit_directed_row_still_holds(self):
        # A tier the user SET for the dialer outranks the token proof — an explicit hold is a choice.
        self._set_trust("MYSTERY", "directed")
        verdict, _ = ps._relay_in("MYSTERY", _relay("q-tok-3"))
        self.assertEqual(verdict, "ack")
        self.assertEqual(len(ps.quarantine_list()), 1)
        self.assertEqual(ps.read_box("sess-web", consume=False), [])


class ExchangeHandleIsTokenProven(unittest.TestCase):
    """peer_exchange_handle passes token_proven=True — it only runs for requests past the HTTP serve-token
    gate — so an attached machine's own relays deliver instead of quarantining on the dialed side."""

    def setUp(self):
        self._prior_seam = os.environ.get("ROMP_SESSIONS_FILE")
        os.environ["ROMP_SESSIONS_FILE"] = _SESS
        os.environ["ROMP_POSTAL_PEERS"] = "1"
        ps.PEERS.clear()
        ps.PEER_STATE.clear()
        ps._seen_ids = None
        for d in (ps.QUARANTINE, ps.MAILROOT / "sess-web" / "new"):
            try:
                for f in d.glob("*"):
                    f.unlink()
            except OSError:
                pass
        try:
            ps.PEER_SEEN.unlink()
        except OSError:
            pass

    def tearDown(self):
        os.environ.pop("ROMP_POSTAL_PEERS", None)
        restore_env("ROMP_SESSIONS_FILE", self._prior_seam)

    def test_handle_delivers_unknown_dialers_direct_relay(self):
        req = {"host": "MYSTERY", "epoch": 1, "proto": ps.PEER_PROTO, "presence": [], "holds": [],
               "relays": [{"mid": "q-hx-1", "to": "web", "frm": "api", "frm_id": "id-api",
                           "body": "checking the deploy", "kind": "coordinate"}],
               "acks": [], "bounces": [], "wait": False}
        resp, status = ps.peer_exchange_handle(req)
        self.assertEqual(status, 200)
        self.assertIn("q-hx-1", resp["acks"])
        self.assertEqual(ps.quarantine_list(), [], "the dialed side does not hold the dialer's own mail")
        box = ps.read_box("sess-web", consume=False)
        self.assertTrue(any("checking the deploy" in (m.get("body") or "") for m in box))

    def test_handle_stamps_senders_origin_host_on_delivered_mail(self):
        """Cross-host delivery stamps from_host = the sender's ORIGIN host (the forwarder's stamp when
        the mail hopped, else the dialing peer) — the only durable record of where a federated sender
        lives; the courier snapshots it into a planted goal's origin (the user 2026-07-26). It rides
        the maildir header AND the messages.jsonl "sent" row."""
        req = {"host": "MYSTERY", "epoch": 1, "proto": ps.PEER_PROTO, "presence": [], "holds": [],
               "relays": [{"mid": "q-hx-2", "to": "web", "frm": "signal", "frm_id": "id-signal",
                           "body": "apply the fix", "kind": "delegate"},
                          {"mid": "q-hx-3", "to": "web", "frm": "api", "frm_id": "id-api",
                           "body": "forwarded along", "kind": "coordinate", "origin": "FARHOST"}],
               "acks": [], "bounces": [], "wait": False}
        ps.peer_update({"host": "FARHOST", "port": 47102, "up": True, "trust": "trusted"})
        resp, status = ps.peer_exchange_handle(req)
        self.assertEqual(status, 200)
        box = {m["body"]: m for m in ps.read_box("sess-web", consume=False)}
        self.assertEqual(box["apply the fix"]["from_host"], "MYSTERY", "direct relay → the dialer's host")
        self.assertEqual(box["forwarded along"]["from_host"], "FARHOST", "hopped mail → the TRUE origin")
        rows = [json.loads(l) for l in (ps.TLDIR / "messages.jsonl").read_text().splitlines()]
        sent = {r["from"]: r for r in rows if r.get("ev") == "sent" and r.get("from_host")}
        self.assertEqual(sent["signal"]["from_host"], "MYSTERY")
        self.assertEqual(sent["api"]["from_host"], "FARHOST")


class QuarantineDecide(unittest.TestCase):
    def setUp(self):
        self._prior_seam = os.environ.get("ROMP_SESSIONS_FILE")
        os.environ["ROMP_SESSIONS_FILE"] = _SESS   # pin OUR sessions seam (see InboundTrustGate.setUp)
        ps.PEERS.clear()
        ps.peer_update({"host": "TESTHOST", "port": 47101, "up": True, "trust": "directed"})
        for d in (ps.QUARANTINE, ps.MAILROOT / "sess-web" / "new"):
            try:
                for f in d.glob("*"):
                    f.unlink()
            except OSError:
                pass

    def tearDown(self):
        restore_env("ROMP_SESSIONS_FILE", self._prior_seam)

    def test_approve_delivers_and_clears(self):
        ps._relay_in("TESTHOST", _relay("q-appr-1", body="original text"))
        ok, err = ps.quarantine_decide("q-appr-1", "approve")
        self.assertTrue(ok, err)
        self.assertEqual(ps.quarantine_list(), [], "approved message leaves the hold")
        box = ps.read_box("sess-web", consume=False)
        self.assertTrue(any("original text" in (m.get("body") or "") for m in box),
                        "approve delivers the held message")
        approved = next(m for m in box if "original text" in (m.get("body") or ""))
        self.assertEqual(approved["from_host"], "TESTHOST",
                         "approve replays the trusted deliver, origin-host stamp included")

    def test_approve_with_edited_text(self):
        ps._relay_in("TESTHOST", _relay("q-appr-2", body="raw peer text"))
        ok, err = ps.quarantine_decide("q-appr-2", "approve", text="edited by the human")
        self.assertTrue(ok, err)
        box = ps.read_box("sess-web", consume=False)
        self.assertTrue(any("edited by the human" in (m.get("body") or "") for m in box))
        self.assertFalse(any("raw peer text" in (m.get("body") or "") for m in box),
                         "the edited text replaces the peer's original")

    def test_deny_drops_without_delivering(self):
        ps._relay_in("TESTHOST", _relay("q-deny-1"))
        ok, err = ps.quarantine_decide("q-deny-1", "deny")
        self.assertTrue(ok, err)
        self.assertEqual(ps.quarantine_list(), [])
        self.assertEqual(ps.read_box("sess-web", consume=False), [], "deny delivers nothing")
        self.assertEqual(list((ps.OUTBOX / "TESTHOST").glob("*.json")) if (ps.OUTBOX / "TESTHOST").is_dir() else [],
                         [], "a bare deny sends nothing back")

    def test_deny_with_feedback_mails_the_sender(self):
        """Deny + a note (the user 2026-07-26): the note parks in the ORIGIN host's outbox as ordinary
        store-and-forward mail addressed to the sender session, so their agent learns why instead of
        waiting forever. The body names the recipient and quotes a gist of what was declined."""
        ps._relay_in("TESTHOST", _relay("q-deny-2", body="please rewrite the ingest job tonight"))
        ok, err = ps.quarantine_decide("q-deny-2", "deny", feedback="not tonight, we freeze before the demo")
        self.assertTrue(ok, err)
        self.assertEqual(ps.quarantine_list(), [])
        rows = [json.loads(f.read_text()) for f in (ps.OUTBOX / "TESTHOST").glob("*.json")]
        self.assertEqual(len(rows), 1, "exactly one note back to the sender")
        m = rows[0]
        self.assertEqual(m["to"], "api", "addressed to the SENDER session by name")
        self.assertEqual(m["frm"], "Romp Postal Service")
        self.assertIn("declined", m["body"])
        self.assertIn("not tonight, we freeze before the demo", m["body"])
        self.assertIn("please rewrite the ingest job", m["body"], "the gist anchors which message this was")
        for f in (ps.OUTBOX / "TESTHOST").glob("*.json"):
            f.unlink()

    def test_a_refused_approve_leaves_the_hold_in_place(self):
        # mutant: no except → deliver's refusal propagates out of the approve (or, worse, quarantine_del
        # runs) and the held message is gone with nothing in new/. Kept at the public-call level on
        # purpose: another change edits this function's body.
        ps._relay_in("TESTHOST", _relay("q-appr-refused", body="held text"))
        self.assertIsNotNone(ps.quarantine_get("q-appr-refused"))
        fd, path = tempfile.mkstemp()
        os.close(fd)
        saved_tl = ps.TLDIR
        ps.TLDIR = Path(path) / "timeline"                   # under a regular file: the REAL append fails
        try:
            ok, err = ps.quarantine_decide("q-appr-refused", "approve")
        finally:
            ps.TLDIR = saved_tl
            ps._TL_FAULT[0] = False
            os.unlink(path)
        self.assertFalse(ok)
        self.assertIn("the held message is untouched", err)
        self.assertIn("not delivered", err)
        self.assertIsNotNone(ps.quarantine_get("q-appr-refused"), "the hold stands")
        box = ps.read_box("sess-web", consume=False)
        self.assertFalse(any("held text" in (m.get("body") or "") for m in box), "nothing landed in new/")

    def test_decide_unknown_mid_errors(self):
        ok, err = ps.quarantine_decide("no-such-mid", "approve")
        self.assertFalse(ok)
        self.assertIn("no held message", err)

    def test_a_deny_whose_note_cannot_park_refuses_and_keeps_the_hold(self):
        # mutant: outbox_put's False ignored (review find, 2026-09-08) → the hold is dropped, ok is
        # answered, and the reviewer's note goes nowhere with nothing saying so
        ps._relay_in("TESTHOST", _relay("q-deny-3", body="please rewrite the ingest job tonight"))
        saved = ps.outbox_put
        ps.outbox_put = lambda h, m: False                   # the outbox could not be written
        try:
            ok, err = ps.quarantine_decide("q-deny-3", "deny", feedback="not tonight, we freeze before the demo")
        finally:
            ps.outbox_put = saved
        self.assertFalse(ok)
        self.assertIn("the held message is untouched", err)
        self.assertIn("deny without a note", err, "the way out is named")
        self.assertIsNotNone(ps.quarantine_get("q-deny-3"), "the hold stands")
        self.assertEqual(list((ps.OUTBOX / "TESTHOST").glob("*.json")) if (ps.OUTBOX / "TESTHOST").is_dir() else [],
                         [], "nothing was parked")
        ok, err = ps.quarantine_decide("q-deny-3", "deny", feedback="not tonight, we freeze before the demo")
        self.assertTrue(ok, err)
        self.assertIsNone(ps.quarantine_get("q-deny-3"), "the retry completes the deny")
        rows = [json.loads(f.read_text()) for f in (ps.OUTBOX / "TESTHOST").glob("*.json")]
        self.assertEqual(len(rows), 1, "and parks exactly one note")
        for f in (ps.OUTBOX / "TESTHOST").glob("*.json"):
            f.unlink()


class HeldMailStoreUnlistable(unittest.TestCase):
    """The bus side of the fold investigation's F3 (2026-09-19): quarantine_list and _hold_rows enumerated the held-mail
    directory with Path.glob, which on Python 3.12 swallows a PermissionError and yields nothing, so their `except
    OSError` never ran for that fault and a directory that could not be listed read as an empty one, nothing said, while every
    hold sat undelivered. Now the listing is os.listdir (_json_files): quarantine_list raises QuarantineUnreadable and
    GET /quarantine answers it as a 503 with the reason (the /inbox shape), the gossip summary answers nothing and says
    so, the fault is said once per episode in the log and never as a bell row (the kernel's own reader of the directory
    files that one), and a clean listing re-arms the episode. Synthetic: a placeholder mid, an invented body."""

    HOLD = {"mid": "11111111-2222-3333-4444-555555550301", "to": "web", "toId": "sess-web", "frm": "api",
            "frmId": "id-api", "body": "invented held text", "kind": "coordinate", "origin": "TESTHOST",
            "via": "TESTHOST", "at": 1700000000}

    def setUp(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root lists a mode-000 directory; the fault cannot be staged")
        self._prior_seam = os.environ.get("ROMP_SESSIONS_FILE")
        os.environ["ROMP_SESSIONS_FILE"] = _SESS
        ps.QUARANTINE.mkdir(parents=True, exist_ok=True)
        for f in ps.QUARANTINE.glob("*"):
            f.unlink()
        (ps.QUARANTINE / (self.HOLD["mid"] + ".json")).write_text(json.dumps(self.HOLD))
        self._saved = (ps._log, ps._kernel_post)
        self.logged, self.told = [], []
        ps._log = lambda line: self.logged.append(line)
        ps._kernel_post = lambda path, body, timeout=2: self.told.append((path, body)) or {"ok": True}
        getattr(ps, "_UNLISTABLE_SAID", {}).clear()   # getattr: absent before the fix, where the run must reach the assertions
        self.addCleanup(self._restore)

    def _restore(self):
        try:
            os.chmod(ps.QUARANTINE, 0o755)
        except OSError:
            pass
        ps._log, ps._kernel_post = self._saved
        getattr(ps, "_UNLISTABLE_SAID", {}).clear()
        restore_env("ROMP_SESSIONS_FILE", self._prior_seam)

    def _said(self):
        return [l for l in self.logged if "held mail" in l and "cannot be listed" in l]

    def test_a_directory_that_cannot_be_listed_is_a_named_fault_never_nothing_held(self):
        os.chmod(ps.QUARANTINE, 0)
        try:
            answer = ps.quarantine_list()
        except Exception as e:
            answer = e
        self.assertNotEqual(answer, [], "an unlistable directory must never read as nothing held")
        self.assertIsInstance(answer, ps.QuarantineUnreadable)
        self.assertIn("cannot be listed", str(answer))
        self.assertEqual(len(self._said()), 1, self.logged)
        self.assertIn("errno %d" % errno.EACCES, self._said()[0], "the log names the errno")
        with self.assertRaises(ps.QuarantineUnreadable):
            ps.quarantine_list()
        self.assertEqual(len(self._said()), 1, "said once per episode, not per call")
        self.assertEqual([p for p, _ in self.told], [], "no bell row from the bus: the kernel's reader of this directory files it")
        os.chmod(ps.QUARANTINE, 0o755)
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]], "the hold was there the whole time")
        self.assertTrue((ps.QUARANTINE / (self.HOLD["mid"] + ".json")).is_file(), "a directory fault moves nothing aside")
        os.chmod(ps.QUARANTINE, 0)
        with self.assertRaises(ps.QuarantineUnreadable):
            ps.quarantine_list()
        self.assertEqual(len(self._said()), 2, "a clean listing ended the episode; the next fault is a new one")

    def test_the_route_answers_the_fault_as_a_503_with_the_reason(self):
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer(("127.0.0.1", 0), ps.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)

        def get():
            req = urllib.request.Request("http://127.0.0.1:%d/quarantine" % srv.server_address[1],
                                         headers={"X-Romp-Token": ps.SERVE_TOKEN})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read().decode() or "{}")

        os.chmod(ps.QUARANTINE, 0)
        code, body = get()
        self.assertEqual(code, 503, "a fault the client can show, never a 200 with nothing held: %r" % (body,))
        self.assertEqual(body["held"], [])
        self.assertIn("cannot be listed", body["unreadable"])
        self.assertEqual(body["error"], body["unreadable"])
        os.chmod(ps.QUARANTINE, 0o755)
        code, body = get()
        self.assertEqual((code, [h["mid"] for h in body["held"]]), (200, [self.HOLD["mid"]]))

    def test_the_gossip_summary_says_the_fault_once_and_the_exchange_payload_still_builds(self):
        os.chmod(ps.QUARANTINE, 0)
        self.assertEqual(ps._hold_rows(), [])
        self.assertEqual(len(self._said()), 1, self.logged)
        self.assertIsInstance(ps.holds_payload("TESTHOST"), list)      # the exchange payload never raises over it
        with self.assertRaises(ps.QuarantineUnreadable):
            ps.quarantine_list()
        self.assertEqual(len(self._said()), 1, "one episode across both readers of the one directory")
        self.assertEqual([p for p, _ in self.told], [])
        os.chmod(ps.QUARANTINE, 0o755)
        self.assertEqual([r["mid"] for r in ps._hold_rows()], [self.HOLD["mid"]])

    def test_an_absent_directory_is_nothing_held_and_no_fault(self):
        for f in ps.QUARANTINE.glob("*"):
            f.unlink()
        ps.QUARANTINE.rmdir()
        self.assertEqual(ps.quarantine_list(), [])
        self.assertEqual(ps._hold_rows(), [])
        self.assertEqual(self._said(), [])

    def test_the_stores_are_listed_never_globbed(self):
        import inspect
        # Since review round 2 quarantine_list and _hold_rows walk the directory through _held_records_bus, the one
        # per-file walk, which lists it through _json_files.
        walk = getattr(ps, "_held_records_bus", None)
        self.assertIsNotNone(walk, "the one held-mail walk behind quarantine_list and _hold_rows")
        for fn, lister in ((ps.quarantine_list, "_held_records_bus("), (ps._hold_rows, "_held_records_bus("),
                           (walk, "_json_files("), (ps._list_json_records, "_json_files(")):
            src = inspect.getsource(fn)
            self.assertIn(lister, src, fn.__name__)
            self.assertNotIn(".glob(", src, fn.__name__)
        lister = inspect.getsource(ps._json_files)
        self.assertIn("os.listdir(", lister)
        self.assertNotIn(".glob(", lister)

    def test_the_recall_lists_the_outbox_never_globs(self):
        import inspect
        # the outbox's recall arm was the store's fourth reader still on Path.glob after round 1, so a mode-000 host
        # directory read as nothing to recall (review round 2; RecallOfAParkedRecordInAStoreThatCannotBeListed has the scene)
        src = inspect.getsource(ps._recall)
        self.assertIn("_json_files(", src)
        self.assertNotIn(".glob(", src)


class HeldMailRecordsThatCannotBeParsed(unittest.TestCase):
    """The bus side of the fold investigation's F4, review round 2 (2026-09-19). quarantine_list wrapped json.loads alone in
    `except (OSError, ValueError)` and then sorted on r.get("at"), so one hold holding a JSON list or null raised
    AttributeError out of the list and out of GET /quarantine (the connection closed with no response), one string `at`
    beside an int one raised TypeError out of the sort the same way, JSON nested past the parser's depth raised
    RecursionError through the except, and _hold_rows, whose .get ran after its own except, raised out of every exchange
    payload the gossip summary rides in; every other bad record was skipped in silence on every pass. Now one walk
    (_held_records_bus) skips a record it cannot read or parse, one that is not an object, and a link with nothing
    behind it, says each once per (file, reason) per episode in the log (the file's name and the fault's kind, never its
    text; no bell row and no move aside, since the kernel's own reader of the directory does both), ends the episode when a
    listing no longer has to skip the file, and a type-wrong `at` sorts as the oldest (_hold_sort_at); quarantine_get
    reads a record that is not an object as nothing a decide could replay. Synthetic: placeholder mids, invented bodies.

    Fails before over a git archive of 4383cc9af with this module copied in, all six cases: the not-an-object case with
    AttributeError from quarantine_list's sort, the type-wrong `at` case with TypeError from the same sort, the nested case
    with RecursionError out of quarantine_list, the decide case with AttributeError from quarantine_decide's approve arm
    (there a bare deny dropped the file unread and approve raised), and the two skip-and-say cases at their said-once
    assertion (0 lines); HeldMailStoreUnlistable's widened pin fails there on the absent walk.

    The free-threaded Python 3.14 (2026-09-19) parses the 100000-deep document every earlier Python refused: the nested
    case's real parse now ends in the not-an-object arm there, so its pin takes either reason, and a sibling case makes
    the 3.14 outcome deterministic on every Python by patching json.loads to return the deep value. A record whose
    `body` is that value is skipped by its type: _hold_rows' gist was str() of the body, its repr. Over a git archive of
    c6f427d0b that case fails at its first assertion (the record is listed as a hold), and _hold_rows past it raises
    RecursionError while getting the repr of the body."""

    HOLD = {"mid": "11111111-2222-3333-4444-555555550301", "to": "web", "toId": "sess-web", "frm": "api",
            "frmId": "id-api", "body": "invented held text", "kind": "coordinate", "origin": "TESTHOST",
            "via": "TESTHOST", "at": 1700000000}
    M2, M3, M4 = ("11111111-2222-3333-4444-555555550302", "11111111-2222-3333-4444-555555550303",
                  "11111111-2222-3333-4444-555555550304")

    def setUp(self):
        self._prior_seam = os.environ.get("ROMP_SESSIONS_FILE")
        os.environ["ROMP_SESSIONS_FILE"] = _SESS
        ps.QUARANTINE.mkdir(parents=True, exist_ok=True)
        self._clear_store()
        self._write(self.HOLD["mid"], json.dumps(self.HOLD))
        self._saved = (ps._log, ps._kernel_post)
        self.logged, self.told = [], []
        ps._log = lambda line: self.logged.append(line)
        ps._kernel_post = lambda path, body, timeout=2: self.told.append((path, body)) or {"ok": True}
        getattr(ps, "_HOLD_SKIPPED_SAID", {}).clear()   # getattr: absent before the fix, where the run must reach the assertions
        getattr(ps, "_UNLISTABLE_SAID", {}).clear()
        self.addCleanup(self._restore)

    def _restore(self):
        for f in ps.QUARANTINE.iterdir():
            try:
                os.chmod(f, 0o644)
            except OSError:
                pass
        self._clear_store()
        ps._log, ps._kernel_post = self._saved
        getattr(ps, "_HOLD_SKIPPED_SAID", {}).clear()
        restore_env("ROMP_SESSIONS_FILE", self._prior_seam)

    def _clear_store(self):
        for f in ps.QUARANTINE.iterdir():
            f.unlink()

    def _write(self, mid, text):
        f = ps.QUARANTINE / (mid + ".json")
        if isinstance(text, bytes):
            f.write_bytes(text)
        else:
            f.write_text(text)
        return f

    def _said(self):
        return [l for l in self.logged if l.startswith("held mail:")]

    def _serve(self):
        import threading
        from http.server import ThreadingHTTPServer
        srv = ThreadingHTTPServer(("127.0.0.1", 0), ps.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        return srv.server_address[1]

    @staticmethod
    def _get(port):
        import urllib.error
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d/quarantine" % port, headers={"X-Romp-Token": ps.SERVE_TOKEN})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception as e:                       # the defect's shape: the handler raised and the connection closed
            return "no response (%s)" % type(e).__name__, None

    def test_a_record_that_is_not_an_object_skips_and_the_readable_hold_is_listed(self):
        f2 = self._write(self.M2, json.dumps(["invented list text"]))
        f3 = self._write(self.M3, "null")
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]])
        self.assertEqual([r["mid"] for r in ps._hold_rows()], [self.HOLD["mid"]], "the gossip summary skips it too")
        self.assertEqual(len(ps.holds_payload("TESTHOST")), 1, "the exchange payload still builds")
        code, body = self._get(self._serve())
        self.assertEqual((code, [h["mid"] for h in body["held"]]), (200, [self.HOLD["mid"]]))
        said = self._said()
        self.assertEqual(len(said), 2, self.logged)
        self.assertTrue(any(f2.name in l and "not a JSON object (list)" in l for l in said), said)
        self.assertTrue(any(f3.name in l and "not a JSON object (NoneType)" in l for l in said), said)
        self.assertFalse(any("invented list text" in l for l in self.logged), "the record's text never reaches the log")
        self.assertEqual([p for p, _ in self.told], [], "no bell row from the bus: the kernel's reader of this directory files it")
        self.assertTrue(f2.is_file() and f3.is_file(), "the bus moves nothing aside: that is the kernel reader's move")
        ps.quarantine_list()
        ps._hold_rows()
        self.assertEqual(len(self._said()), 2, "said once per file per episode, not per pass or per reader")
        f3.unlink()
        ps.quarantine_list()
        self.assertEqual(len(self._said()), 2)
        self._write(self.M3, "null")
        ps.quarantine_list()
        self.assertEqual(len(self._said()), 3, "a listing that no longer had to skip the file ended its episode; its return is said again")

    def test_a_type_wrong_at_sorts_as_the_oldest_and_every_hold_stays_listed(self):
        self._write(self.M2, json.dumps(dict(self.HOLD, mid=self.M2, at="yesterday-at-noon")))
        self._write(self.M3, json.dumps(dict(self.HOLD, mid=self.M3, at="123")))
        self._write(self.M4, json.dumps(dict(self.HOLD, mid=self.M4)).replace(str(self.HOLD["at"]), "1e400"))   # a float infinity
        held = ps.quarantine_list()
        self.assertEqual([h["mid"] for h in held[:2]], [self.HOLD["mid"], self.M3], "newest first; the digit string counts as its value")
        self.assertEqual(sorted(h["mid"] for h in held[2:]), sorted([self.M2, self.M4]), "the two that are not numbers sort as the oldest")
        self.assertEqual(len(ps._hold_rows()), 4)
        code, body = self._get(self._serve())
        self.assertEqual((code, len(body["held"])), (200, 4))
        self.assertEqual(self._said(), [], "a type-wrong `at` is not a skip: the hold is listed and decidable")
        self.assertEqual(len(list(ps.QUARANTINE.iterdir())), 4, "nothing moved aside")

    def test_a_record_that_cannot_be_parsed_or_followed_skips_and_is_said_once(self):
        torn = self._write(self.M2, "{not json")
        raw = self._write(self.M3, b"\xff\xfe{}")
        link = ps.QUARANTINE / (self.M4 + ".json")
        os.symlink(ps.QUARANTINE / "nothing-behind-it.json", link)
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]])
        self.assertEqual([r["mid"] for r in ps._hold_rows()], [self.HOLD["mid"]])
        said = self._said()
        self.assertEqual(len(said), 3, self.logged)
        self.assertTrue(any(torn.name in l and "not JSON (" in l for l in said), said)
        self.assertTrue(any(raw.name in l and "not JSON (" in l for l in said), said)
        self.assertTrue(any(link.name in l and "a link with nothing behind it" in l for l in said), said)
        self.assertFalse(any("not json" in l for l in self.logged), "the file's text never reaches the log")
        ps.quarantine_list()
        self.assertEqual(len(self._said()), 3, "said once per file per episode")
        self.assertTrue(torn.is_file() and raw.is_file() and link.is_symlink(), "left in place")
        self.assertEqual([p for p, _ in self.told], [])

    def _assert_said_deep(self, line, f, reasons):
        """The said line names the file and one of `reasons`, and never the value: a repr of the document would run to
        200000 characters, so a bound on the line is the pin."""
        self.assertIn(f.name, line)
        self.assertTrue(any(r in line for r in reasons), line)
        self.assertLess(len(line), 400, "the file and the type are named, never the value")
        self.assertNotIn("[[", line)

    def test_json_nested_past_the_parsers_depth_skips_instead_of_raising(self):
        """The real parser on the running Python: through 3.13 json.loads raises RecursionError at the depth, the
        free-threaded 3.14 returns the list, which is not an object. Either way: skipped, said once, the hold listed."""
        deep = self._write(self.M2, DEEP)
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]])
        self.assertEqual([r["mid"] for r in ps._hold_rows()], [self.HOLD["mid"]])
        code, body = self._get(self._serve())
        self.assertEqual((code, [h["mid"] for h in body["held"]]), (200, [self.HOLD["mid"]]))
        said = self._said()
        self.assertEqual(len(said), 1, self.logged)
        self._assert_said_deep(said[0], deep, ("not JSON (RecursionError)", "not a JSON object (list)"))

    def test_a_deep_document_the_parser_returns_is_skipped_by_its_type_and_never_formatted(self):
        """json.loads as the free-threaded Python 3.14 answers the deep document, made deterministic here: the parser
        returns the 100000-deep value. As a bare list it is not an object; as a record's body it is not text. Both are
        skipped and said by type alone, on the list, the gossip summary and the route, and the files stay for the
        kernel's reader to move aside."""
        deep_list = self._write(self.M2, DEEP)
        deep_body = self._write(self.M3, json.dumps(dict(self.HOLD, mid=self.M3, body="DEEP")).replace('"DEEP"', DEEP))
        value = _deep_list()
        with _parser_returning({"[": value, '{"mid": "%s"' % self.M3: dict(self.HOLD, mid=self.M3, body=value)}):
            self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]])
            self.assertEqual([r["mid"] for r in ps._hold_rows()], [self.HOLD["mid"]], "the gossip summary skips it: its gist is str() of the body")
            self.assertEqual(len(ps.holds_payload("TESTHOST")), 1, "the exchange payload still builds")
            code, body = self._get(self._serve())
        self.assertEqual((code, [h["mid"] for h in body["held"]]), (200, [self.HOLD["mid"]]))
        said = self._said()
        self.assertEqual(len(said), 2, self.logged)
        self._assert_said_deep(next(l for l in said if deep_list.name in l), deep_list, ("not a JSON object (list)",))
        self._assert_said_deep(next(l for l in said if deep_body.name in l), deep_body, ("a record whose `body` is a list, not text",))
        self.assertTrue(deep_list.is_file() and deep_body.is_file(), "left in place: the kernel's reader moves aside")
        self.assertEqual([p for p, _ in self.told], [], "no bell row from the bus")

    def test_a_record_that_cannot_be_read_is_said_once_with_its_errno_and_the_episode_ends_when_it_reads(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root reads a mode-000 file; the fault cannot be staged")
        locked = self._write(self.M2, json.dumps(dict(self.HOLD, mid=self.M2)))
        os.chmod(locked, 0)
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]])
        said = self._said()
        self.assertEqual(len(said), 1, self.logged)
        self.assertIn(locked.name, said[0])
        self.assertIn("unreadable (errno %d" % errno.EACCES, said[0])
        ps.quarantine_list()
        self.assertEqual(len(self._said()), 1, "said once per (file, reason) per episode")
        os.chmod(locked, 0o644)
        self.assertEqual(sorted(h["mid"] for h in ps.quarantine_list()), sorted([self.HOLD["mid"], self.M2]), "readable again: listed")
        os.chmod(locked, 0)
        ps.quarantine_list()
        self.assertEqual(len(self._said()), 2, "the clean read ended the episode; the fault's return is said again")

    def test_a_decide_on_a_record_that_is_not_an_object_is_refused_in_plain_words_instead_of_raising(self):
        f2 = self._write(self.M2, json.dumps([1]))
        for action, extra in (("approve", {}), ("deny", {"feedback": "invented reviewer note"}), ("deny", {})):
            ok, err = ps.quarantine_decide(self.M2, action, **extra)
            self.assertEqual(ok, False, (action, extra, err))
            self.assertIn("cannot be read as a record (JSON list, not an object)", err, (action, extra))
            self.assertNotIn("no held message", err, "the file is there: never reported absent")
            self.assertTrue(f2.is_file(), "the decide touched nothing: the kernel's reader moves it aside and says so")
        self.assertEqual(ps.quarantine_get(self.M2), [1], "the store's one-record read still answers what it parsed")


class RecallOfAParkedRecordInAStoreThatCannotBeListed(unittest.TestCase):
    """The outbox store's fourth reader, missed by review round 1's F3 postal fix (review round 2, 2026-09-19): _recall's
    outbox arm (the unsend of a parked cross-host record) enumerated OUTBOX/<host> with Path.glob, which on Python 3.12
    swallows a PermissionError and yields nothing, so a recall over a host directory that could not be listed answered
    nothing removed and nothing kept, the sender was told there was nothing to recall, and no bell row or log line said
    why while the parked record stood for the next exchange. Now the arm lists through _json_files and a directory it
    cannot list is said once per fault episode through _say_unlistable_once with the same key and text as the exchange's
    own listing of the store (_list_json_records): one bell row and one log line across every reader of the one store,
    the record standing, unrecalled, for the listing that can read it. Skipped as root (a mode-000 directory lists for
    root). Synthetic: a placeholder sender id and mid, an invented body, the host name `srv`.

    Fails before over a git archive of 4383cc9af with this module copied in: the case fails at the said-once assertion
    (0 log lines, 0 bell rows), and HeldMailStoreUnlistable.test_the_recall_lists_the_outbox_never_globs fails on
    _recall's `.glob(`."""

    SND = "11111111-2222-3333-4444-555555550401"
    MID = "11111111-2222-3333-4444-555555550402"

    def setUp(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root lists a mode-000 directory; the fault cannot be staged")
        self._prior_seam = os.environ.get("ROMP_SESSIONS_FILE")
        self._prior_peers = os.environ.get("ROMP_POSTAL_PEERS")
        os.environ["ROMP_SESSIONS_FILE"] = _SESS
        os.environ["ROMP_POSTAL_PEERS"] = "1"       # the outbox arm runs in peer-bus mode only
        self._saved = (ps._log, ps._kernel_post, ps.local_agents, ps.local_agents_checked)
        self.logged, self.told = [], []
        ps._log = lambda line: self.logged.append(line)
        ps._kernel_post = lambda path, body, timeout=2: self.told.append((path, body)) or {"ok": True}
        ps.local_agents = lambda threads=False: []
        ps.local_agents_checked = lambda threads=False: ([], True)
        getattr(ps, "_UNLISTABLE_SAID", {}).clear()
        self.hostdir = ps.OUTBOX / "srv"
        self.hostdir.mkdir(parents=True, exist_ok=True)
        for f in self.hostdir.iterdir():
            f.unlink()
        self.addCleanup(self._restore)
        self.assertTrue(ps.outbox_put("srv", {"mid": self.MID, "to": "beta", "frm": "alpha", "frm_id": self.SND,
                                              "body": "invented parked text", "kind": "coordinate"}))

    def _restore(self):
        try:
            os.chmod(self.hostdir, 0o755)
        except OSError:
            pass
        for f in self.hostdir.iterdir():
            f.unlink()
        ps._log, ps._kernel_post, ps.local_agents, ps.local_agents_checked = self._saved
        getattr(ps, "_UNLISTABLE_SAID", {}).clear()
        restore_env("ROMP_POSTAL_PEERS", self._prior_peers)
        restore_env("ROMP_SESSIONS_FILE", self._prior_seam)

    def _said(self):
        return [l for l in self.logged if "outbox srv" in l and "cannot be listed" in l]

    def _bells(self):
        return [b.get("text", "") for p, b in self.told if p == "/postal-notice"]

    def test_a_host_directory_that_cannot_be_listed_is_said_once_and_the_record_stands(self):
        record = self.hostdir / (self.MID + ".json")
        os.chmod(self.hostdir, 0)
        kept = []
        self.assertEqual(ps._recall(self.SND, "", self.MID, kept=kept), [], "a record the recall cannot see is not removed")
        self.assertEqual(kept, [], "and not refused as carried or in flight: nothing about it is known")
        said = self._said()
        self.assertEqual(len(said), 1, self.logged)
        self.assertIn("errno %d" % errno.EACCES, said[0])
        self.assertEqual(len(self._bells()), 1, self.told)
        self.assertIn("outbox srv", self._bells()[0])
        self.assertFalse(any("invented parked text" in l for l in self.logged), "the parked text never reaches the log")
        ps._recall(self.SND, "", self.MID, kept=[])
        self.assertEqual(ps._list_json_records(self.hostdir, "outbox srv"), [], "the exchange's own listing of the store")
        self.assertEqual((len(self._said()), len(self._bells())), (1, 1), "one episode across every reader of the one store")
        os.chmod(self.hostdir, 0o755)
        self.assertTrue(record.is_file(), "the record stood the whole time; a directory fault moves nothing")
        removed = ps._recall(self.SND, "", self.MID, kept=[])
        self.assertEqual([(r["to"], r["id"]) for r in removed], [("srv:beta", self.MID)], "listable again: recalled")
        self.assertFalse(record.exists())
        os.chmod(self.hostdir, 0)
        ps._recall(self.SND, "", self.MID, kept=[])
        self.assertEqual(len(self._said()), 2, "the clean listing ended the episode; the fault's return is said again")


class SkippedSaidPruneReadsASnapshot(unittest.TestCase):
    """The bus side of the kernel's snapshot finding (review round 2 consolidation, 2026-09-19): _held_records_bus runs on
    the exchange thread (build_exchange_request, through holds_payload and _hold_rows) and on a GET /quarantine handler
    thread, so two walks over the directory overlap. Its episode-end loop iterated the module-level _HOLD_SKIPPED_SAID
    live, so the other walk's pop landed mid-iteration and raised RuntimeError (`dictionary changed size during iteration`)
    out of the walk: out of GET /quarantine (a 500 for that request) and out of holds_payload, which runs outside the
    exchange's guards, so one race ended the host's whole exchange, the failure class this bundle exists to remove. The
    loop reads a snapshot now (list(_HOLD_SKIPPED_SAID), one step under the GIL). Stale keys are the ordinary course, not
    a fault: every held file the bus skipped and said, then the kernel's reader moved aside, leaves one.

    Fails before over the round's pre-fix tree at the assertion on `errors` (RuntimeError repr'd from a walk), 3000 stale
    keys under an empty directory, two threads from a barrier, the switch interval at 1e-5 (restored in finally) so the
    interleaving the two doors can produce is made certain; over a git archive of 4383cc9af it fails earlier, on the
    absent walk."""

    def setUp(self):
        self._prior_seam = os.environ.get("ROMP_SESSIONS_FILE")
        os.environ["ROMP_SESSIONS_FILE"] = _SESS
        ps.QUARANTINE.mkdir(parents=True, exist_ok=True)
        for f in ps.QUARANTINE.iterdir():
            f.unlink()
        self._saved_log = ps._log
        ps._log = lambda line: None
        getattr(ps, "_HOLD_SKIPPED_SAID", {}).clear()
        self.addCleanup(self._restore)

    def _restore(self):
        ps._log = self._saved_log
        getattr(ps, "_HOLD_SKIPPED_SAID", {}).clear()
        restore_env("ROMP_SESSIONS_FILE", self._prior_seam)

    def test_two_overlapping_walks_never_raise_out_of_one_another(self):
        walk = getattr(ps, "_held_records_bus", None)
        self.assertIsNotNone(walk, "the one held-mail walk behind quarantine_list and _hold_rows")
        root = str(ps.QUARANTINE) + os.sep
        keys = {root + ("11111111-2222-3333-4444-%012d.json" % i): "not JSON (JSONDecodeError)" for i in range(3000)}
        saved = sys.getswitchinterval()
        sys.setswitchinterval(1e-5)
        errors = []
        try:
            for _ in range(40):
                ps._HOLD_SKIPPED_SAID.update(keys)       # every key stale: the directory is empty, so both walks prune them all
                bar = threading.Barrier(2)

                def listing():
                    try:
                        bar.wait(10)
                        walk()
                    except Exception as e:                # the failure under test, carried to the assertion
                        errors.append(repr(e))
                ts = [threading.Thread(target=listing) for _ in range(2)]
                for t in ts:
                    t.start()
                for t in ts:
                    t.join(30)
                if errors:
                    break
        finally:
            sys.setswitchinterval(saved)
        self.assertEqual(errors, [], "a walk raised out of the exchange or the route over the other's prune")
        self.assertEqual([k for k in ps._HOLD_SKIPPED_SAID if k.startswith(root)], [], "both pruned every stale key")


class PeerUpdateTrust(unittest.TestCase):
    def test_default_and_keep_last_known(self):
        ps.PEERS.clear()
        ps.peer_update({"host": "H", "port": 1, "up": True})                 # no trust → directed
        self.assertEqual(ps.PEERS["H"]["trust"], "directed")
        ps.peer_update({"host": "H", "port": 1, "up": True, "trust": "trusted"})
        self.assertEqual(ps.PEERS["H"]["trust"], "trusted")
        ps.peer_update({"host": "H", "port": 1, "up": False})                # trustless down-notify keeps it
        self.assertEqual(ps.PEERS["H"]["trust"], "trusted")


if __name__ == "__main__":
    unittest.main(verbosity=2)
