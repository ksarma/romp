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
    GET /quarantine answers it as a 503 with the reason (the /inbox shape), the gossip summary answers one row carrying
    `fault` (since 2026-09-20; it answered nothing until the fork PR's review, and every other machine's section vanished
    in silence: AHolderWhoseStoreCannotBeListedSaysSoOnTheWire has the wire), the fault is said once per episode in the log
    and never as a bell row (the kernel's own reader of the directory files that one), and a clean listing re-arms the
    episode. The two source-text pins that used to sit here run in TheStoresAreListedNeverGlobbed, a class with no root
    skip. Synthetic: a placeholder mid, an invented body."""

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
        rows = ps._hold_rows()
        self.assertEqual([r.get("mid") for r in rows], [""], "one row, and it is not a held message: %r" % (rows,))
        self.assertIn("cannot be listed", rows[0]["fault"])
        self.assertEqual(len(self._said()), 1, self.logged)
        payload = ps.holds_payload("TESTHOST")                          # the exchange payload never raises over it
        self.assertEqual([r.get("fault") for r in payload], [rows[0]["fault"]], "and carries the fault row")
        with self.assertRaises(ps.QuarantineUnreadable):
            ps.quarantine_list()
        self.assertEqual(len(self._said()), 1, "one episode across both readers of the one directory")
        self.assertEqual([p for p, _ in self.told], [])
        os.chmod(ps.QUARANTINE, 0o755)
        self.assertEqual([r["mid"] for r in ps._hold_rows()], [self.HOLD["mid"]])
        self.assertNotIn("fault", ps._hold_rows()[0], "a listable store's rows carry no fault key")

    def test_an_absent_directory_is_nothing_held_and_no_fault(self):
        for f in ps.QUARANTINE.glob("*"):
            f.unlink()
        ps.QUARANTINE.rmdir()
        self.assertEqual(ps.quarantine_list(), [])
        self.assertEqual(ps._hold_rows(), [])
        self.assertEqual(self._said(), [])



class TheStoresAreListedNeverGlobbed(unittest.TestCase):
    """The two source-text pins of the bus side of F3, in a class with NO root skip (the fork PR's tests-4, 2026-09-20):
    they sat in HeldMailStoreUnlistable, whose setUp skips every case as root because a mode-000 directory lists for root,
    so on a root runner nothing pinned the os.listdir-not-Path.glob mechanism that is the whole of the fix. The pins read
    source and need no fixture, no store and no permission bit. Under a geteuid that answers 0 they run and pass; with
    _json_files reverted to Path.glob in a scratch copy they fail under the same simulation."""

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


class _HeldStore(unittest.TestCase):
    """The held-mail store fixture the record-level classes share: one readable hold written, the log and the kernel leg of
    _refused_notice captured, the said-once registries cleared, modes restored and the store emptied in cleanup, and a
    served bus for the route cases. No tests of its own."""

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
        try:
            os.chmod(ps.QUARANTINE, 0o755)
        except OSError:
            pass
        for f in ps.QUARANTINE.iterdir():
            try:
                os.chmod(f, 0o644)
            except OSError:
                pass
        self._clear_store()
        ps._log, ps._kernel_post = self._saved
        getattr(ps, "_HOLD_SKIPPED_SAID", {}).clear()
        getattr(ps, "_UNLISTABLE_SAID", {}).clear()
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

    @staticmethod
    def _act(port, body):
        """POST /quarantine/act as the kernel's card does; (status, json), or the dropped-connection shape."""
        import urllib.error
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d/quarantine/act" % port, data=json.dumps(body).encode(),
                                     headers={"X-Romp-Token": ps.SERVE_TOKEN, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception as e:
            return "no response (%s)" % type(e).__name__, None


class HeldMailRecordsThatCannotBeParsed(_HeldStore):
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
    `body` is that value was skipped by its type for a day (commit 35fad278c); since the fork PR's review (extra8-1,
    2026-09-20) a record that read and parsed is never skipped for a field's type: it is listed, its gist names the body
    by type (_hold_text), the route serves the body as its type name (_hold_wire), and HeldBodyThatIsNotTextKeepsItsHold
    has the decide roads. The fixture is _HeldStore's."""

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

    def test_a_deep_document_the_parser_returns_is_skipped_as_a_list_and_kept_as_a_body_named_by_type(self):
        """json.loads as the free-threaded Python 3.14 answers the deep document, made deterministic here: the parser
        returns the 100000-deep value. As a bare list it is not an object and is skipped, said by type alone. As a
        record's body it is a FIELD of a record that read and parsed, so the record keeps its hold (the fork PR's extra8-1,
        2026-09-20): listed, its gist the type name, the route serving the body as its type name (json.dumps of the value
        would raise RecursionError out of the handler), nothing said for it, and never formatted anywhere. Fails before
        over a git archive of 35fad278c, whose walk skipped the record for its body: absent from the list."""
        deep_list = self._write(self.M2, DEEP)
        deep_body = self._write(self.M3, json.dumps(dict(self.HOLD, mid=self.M3, body="DEEP")).replace('"DEEP"', DEEP))
        value = _deep_list()
        with _parser_returning({"[": value, '{"mid": "%s"' % self.M3: dict(self.HOLD, mid=self.M3, body=value)}):
            self.assertEqual(sorted(h["mid"] for h in ps.quarantine_list()), sorted([self.HOLD["mid"], self.M3]),
                             "the record whose body is the deep value keeps its hold; the bare list is skipped")
            rows = {r["mid"]: r for r in ps._hold_rows()}
            self.assertEqual(sorted(rows), sorted([self.HOLD["mid"], self.M3]))
            self.assertEqual(rows[self.M3]["gist"], "list", "the gist names the body by its type, never its repr")
            self.assertEqual(len(ps.holds_payload("TESTHOST")), 2, "the exchange payload still builds")
            code, body = self._get(self._serve())
        self.assertEqual(code, 200, body)
        served = {h["mid"]: h for h in body["held"]}
        self.assertEqual(sorted(served), sorted([self.HOLD["mid"], self.M3]))
        self.assertEqual((served[self.M3]["body"], served[self.M3]["bodyType"]), ("list", "list"),
                         "the route serves the body as its type name and says it did")
        self.assertNotIn("bodyType", served[self.HOLD["mid"]], "a text body is served as it is")
        said = self._said()
        self.assertEqual(len(said), 1, self.logged)
        self._assert_said_deep(said[0], deep_list, ("not a JSON object (list)",))
        self.assertFalse(any(deep_body.name in l for l in self.logged), "nothing is said of a record that keeps its hold")
        self.assertTrue(deep_list.is_file() and deep_body.is_file(), "left in place: the kernel's reader moves the list aside")
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


def _kernel_hold_text():
    """The kernel's _hold_text, compiled from its source alone (the daemon is never loaded here): the twin the bus's copy
    must agree with over the probe set below."""
    import ast
    tree = ast.parse(Path(os.path.join(BIN, "romp-kernel")).read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_hold_text")
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "kernel _hold_text", "exec"), ns)
    return ns["_hold_text"]


class HeldRecordOnDiskIsNeverReportedAbsent(_HeldStore):
    """quarantine_get folded every read and parse fault to None, and quarantine_decide turned None into "no held message
    '<mid>'", the answer for a mid that was never held: a hold on disk that the bus could not read was reported ABSENT,
    visible and false, on the one road the held-mail feature exists for (the fork PR's extra5-2 and tests-1, 2026-09-20;
    the sibling list reader had been given QuarantineUnreadable for the same class, the one-record reader not). Now
    quarantine_get answers None only for a mid _safe_id refuses or a plain file that is not there, and raises
    HeldRecordUnreadable for a file on disk under the name that it could not read (EACCES), a link with nothing behind it,
    a document it could not parse (not JSON, nested past the parser's depth) or one that parses to null; quarantine_decide
    catches it inside the bus and answers in words (the fault, nothing was done, the message is still held), so
    /quarantine/act answers a refusal and never a dropped connection the kernel would read as the bus unreachable. The
    record stays: the kernel's reader is the one that moves a file aside.

    Fails before over a git archive of 35fad278c for the RecursionError shape (that PR's round 2 added the arm that folded
    it to None: the deep document answers "no held message") and over bc88256e8 for the OSError shape (the fold predates
    the PR; there the deep document raised RecursionError out of the decide instead). The deep case reads the same on the
    3.12 parser (RecursionError, refused as not JSON) and the free-threaded 3.14 one (a list, refused as not an object):
    both are refusals naming the record as one that cannot be read, never absent. Synthetic: placeholder mids."""

    def _refused_not_absent(self, err, *marks):
        self.assertIsInstance(err, str)
        self.assertNotIn("no held message", err, "the file is on disk: never reported absent")
        self.assertIn("cannot be read", err)
        self.assertIn("nothing was done", err)
        for m in marks:
            self.assertIn(m, err)

    def _decide_all_refuse(self, mid, *marks):
        for action, extra in (("approve", {}), ("approve", {"text": "edited by the human"}),
                              ("deny", {"feedback": "invented reviewer note"}), ("deny", {})):
            ok, err = ps.quarantine_decide(mid, action, **extra)
            self.assertFalse(ok, (action, extra, err))
            self._refused_not_absent(err, *marks)

    def _get_refusal(self, mid):
        """quarantine_get's typed refusal for `mid`, as text; asserted after the decide-level checks so a run over the
        pre-fix archive fails at the defect (the absent answer) and not on the class's absence."""
        refusal = getattr(ps, "HeldRecordUnreadable", None)
        self.assertIsNotNone(refusal, "the one-record reader's typed refusal, QuarantineUnreadable's sibling")
        with self.assertRaises(refusal) as cm:
            ps.quarantine_get(mid)
        return str(cm.exception)

    def test_a_deep_document_is_refused_as_unreadable_never_absent_on_either_parser(self):
        deep = self._write(self.M2, DEEP)
        self._decide_all_refuse(self.M2)             # the real parser: RecursionError through 3.13, a list on 3.14t
        self.assertTrue(deep.is_file(), "the decide touched nothing: the kernel's reader moves it aside")
        with _parser_returning({"[": _deep_list()}):  # the 3.14 outcome, deterministic on every Python
            self._decide_all_refuse(self.M2, "JSON list, not an object")
        self.assertTrue(deep.is_file())
        try:
            got = ps.quarantine_get(self.M2)
        except Exception as e:                       # the 3.12 shape: the typed refusal, naming the parser's fault
            self.assertEqual(type(e).__name__, "HeldRecordUnreadable", repr(e)[:200])
            self.assertIn("not JSON (RecursionError)", str(e))
        else:                                        # the 3.14 shape: the value, refused by the decide as not an object
            self.assertIsInstance(got, list)

    def test_a_record_that_cannot_be_read_is_refused_with_its_errno_never_absent(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root reads a mode-000 file; the fault cannot be staged")
        locked = self._write(self.M2, json.dumps(dict(self.HOLD, mid=self.M2)))
        os.chmod(locked, 0)
        self._decide_all_refuse(self.M2, "errno %d" % errno.EACCES, "still held")
        self.assertTrue(locked.is_file(), "left in place")
        code, body = self._act(self._serve(), {"mid": self.M2, "action": "approve"})
        self.assertEqual(code, 400, "the route answers the refusal, never a dropped connection: %r" % (body,))
        self.assertEqual(body["ok"], False)
        self._refused_not_absent(body["error"], "errno %d" % errno.EACCES)
        reason = self._get_refusal(self.M2)
        self.assertIn("unreadable (errno %d" % errno.EACCES, reason)
        self.assertNotIn(str(ps.QUARANTINE), reason, "the reason names the fault, never the path")
        os.chmod(locked, 0o644)
        self.assertEqual(ps.quarantine_get(self.M2)["mid"], self.M2, "readable again: the record itself")

    def test_a_dangling_link_and_a_null_document_are_refused_never_absent(self):
        link = ps.QUARANTINE / (self.M2 + ".json")
        os.symlink(ps.QUARANTINE / "nothing-behind-it.json", link)
        self._decide_all_refuse(self.M2, "a link with nothing behind it")
        self.assertTrue(link.is_symlink(), "left in place")
        null = self._write(self.M3, "null")
        self._decide_all_refuse(self.M3, "NoneType")
        self.assertTrue(null.is_file())
        torn = self._write(self.M4, "{not json")
        self._decide_all_refuse(self.M4, "not JSON")
        self.assertTrue(torn.is_file())
        self.assertFalse(any("not json" in l for l in self.logged), "the file's text never reaches the log")
        self.assertIn("a link with nothing behind it", self._get_refusal(self.M2))
        self.assertIn("not a JSON object (NoneType)", self._get_refusal(self.M3))
        self.assertIn("not JSON (JSONDecodeError)", self._get_refusal(self.M4))

    def test_a_mid_that_was_never_held_is_still_absent(self):
        self.assertIsNone(ps.quarantine_get(self.M2), "a plain file that is not there is the one absent answer")
        self.assertIsNone(ps.quarantine_get("../not-a-component"), "a mid _safe_id refuses was never held")
        ok, err = ps.quarantine_decide(self.M2, "approve")
        self.assertEqual((ok, err), (False, "no held message '%s'" % self.M2))
        self.assertEqual(ps.quarantine_get(self.HOLD["mid"])["mid"], self.HOLD["mid"], "and a readable record reads")


class HeldBodyThatIsNotTextKeepsItsHold(_HeldStore):
    """A record that READ and PARSED is never skipped or declared corrupt for a field's TYPE (the fork PR's extra8-1, with
    extra5-4, 2026-09-20). Commit 35fad278c made the walk skip a record whose `body` is not text, so a message the bus's
    own writer had accepted and acked left the board with no card and could be neither approved nor denied; and
    quarantine_decide's approve arm handed the body to deliver's string concatenation, TypeError out of /quarantine/act
    (a dropped connection the kernel reported as the bus unreachable), while deny with a note took str() of the body for
    its gist, RecursionError on a deep one. Now the walk keeps the record; _hold_rows and the route name the body by its
    type (_hold_text, _hold_wire); deny (bare, or with a note whose gist is the type name) drops the hold; approve with
    edited text delivers that text; and a BARE approve of a non-text body is refused in words, by the type alone, the
    record untouched and still held, the two doors that work named. Only the bare approve changes: the two roads that
    worked before (edited text on approve, a bare deny) work as they did. The bus's _hold_text is the kernel's twin,
    pinned over one probe set.

    Fails before over a git archive of 35fad278c: the list-body record is missing from quarantine_list, the gossip summary
    and the route (skipped for its body), the bare approve raises TypeError out of the decide, and deny with a note over
    the deep body raises RecursionError. Synthetic: placeholder mids, invented text, the deep value built iteratively."""

    LIST_BODY = ["invented", "list", "text"]

    def _clear_mail(self):
        for d in (ps.OUTBOX / "TESTHOST", ps.MAILROOT / "sess-web" / "new"):
            if d.is_dir():
                for f in d.iterdir():
                    f.unlink()

    def setUp(self):
        super().setUp()
        self._clear_mail()
        self.addCleanup(self._clear_mail)

    def test_a_list_body_keeps_its_hold_and_is_named_by_type_everywhere(self):
        f2 = self._write(self.M2, json.dumps(dict(self.HOLD, mid=self.M2, body=self.LIST_BODY)))
        self.assertEqual(sorted(h["mid"] for h in ps.quarantine_list()), sorted([self.HOLD["mid"], self.M2]))
        rows = {r["mid"]: r for r in ps._hold_rows()}
        self.assertEqual(rows[self.M2]["gist"], "list", "the gist is the type name, never the value")
        self.assertEqual(rows[self.HOLD["mid"]]["gist"], "invented held text")
        code, body = self._get(self._serve())
        served = {h["mid"]: h for h in body["held"]}
        self.assertEqual((code, served[self.M2]["body"], served[self.M2]["bodyType"]), (200, "list", "list"))
        self.assertEqual(self._said(), [], "nothing is said of a record that keeps its hold")
        self.assertFalse(any("invented" in l and "list" in l for l in self.logged))
        self.assertTrue(f2.is_file(), "nothing moved aside")
        self.assertEqual([p for p, _ in self.told], [])

    def test_a_bare_approve_of_a_non_text_body_is_refused_in_words_and_the_hold_stands(self):
        f2 = self._write(self.M2, json.dumps(dict(self.HOLD, mid=self.M2, body=self.LIST_BODY)))
        ok, err = ps.quarantine_decide(self.M2, "approve")
        self.assertFalse(ok, err)
        self.assertIn("body of type list, not text", err)
        self.assertIn("still held", err)
        self.assertIn("edit the text and approve, or deny", err, "the two doors that work are named")
        self.assertNotIn("invented", err, "the type alone, never the value")
        self.assertTrue(f2.is_file(), "the record is untouched")
        self.assertEqual(ps.read_box("sess-web", consume=False), [], "nothing was delivered")
        code, body = self._act(self._serve(), {"mid": self.M2, "action": "approve"})
        self.assertEqual((code, body["ok"]), (400, False), "the route answers a refusal, never a dropped connection: %r" % (body,))
        self.assertIn("body of type list", body["error"])
        deep = self._write(self.M3, json.dumps(dict(self.HOLD, mid=self.M3, body="DEEP")).replace('"DEEP"', DEEP))
        with _parser_returning({'{"mid": "%s"' % self.M3: dict(self.HOLD, mid=self.M3, body=_deep_list())}):
            ok, err = ps.quarantine_decide(self.M3, "approve")
        self.assertFalse(ok)
        self.assertIn("body of type list, not text", err)
        self.assertLess(len(err), 400, "the type is named, never the value")
        self.assertTrue(deep.is_file())

    def test_approve_with_edited_text_delivers_and_deny_with_a_note_names_the_type(self):
        f2 = self._write(self.M2, json.dumps(dict(self.HOLD, mid=self.M2, body=self.LIST_BODY)))
        ok, err = ps.quarantine_decide(self.M2, "approve", text="edited by the human")
        self.assertTrue(ok, err)
        self.assertFalse(f2.exists(), "approved: the hold is gone")
        box = ps.read_box("sess-web", consume=False)
        self.assertTrue(any("edited by the human" in (m.get("body") or "") for m in box), "the edited text was delivered")
        deep = self._write(self.M3, json.dumps(dict(self.HOLD, mid=self.M3, body="DEEP")).replace('"DEEP"', DEEP))
        with _parser_returning({'{"mid": "%s"' % self.M3: dict(self.HOLD, mid=self.M3, body=_deep_list())}):
            ok, err = ps.quarantine_decide(self.M3, "deny", feedback="not tonight, we freeze before the demo")
        self.assertTrue(ok, err)
        self.assertFalse(deep.exists(), "denied: the hold is gone")
        notes = [json.loads(f.read_text()) for f in (ps.OUTBOX / "TESTHOST").glob("*.json")]
        self.assertEqual(len(notes), 1, "one note back to the sender")
        self.assertIn('("list")', notes[0]["body"], "the gist names the type")
        self.assertIn("not tonight, we freeze before the demo", notes[0]["body"])
        self.assertLess(len(notes[0]["body"]), 400, "the value is never formatted into the note")
        f4 = self._write(self.M4, json.dumps(dict(self.HOLD, mid=self.M4, body=self.LIST_BODY)))
        ok, err = ps.quarantine_decide(self.M4, "deny")
        self.assertTrue(ok, err)
        self.assertFalse(f4.exists(), "a bare deny drops the hold as it always did")

    def test_the_bus_hold_text_agrees_with_the_kernels_over_a_probe_set(self):
        kernel_hold_text = _kernel_hold_text()
        probes = [("", None, "invented text", " spaced  text ", 0, 7, -3, 2.5, True, False, [], [1, 2], {}, {"a": 1},
                   ("t",), b"bytes"), ]
        labelled = [(repr(v), v) for v in probes[0]] + [("the deep list (never formatted, not even here)", _deep_list())]
        for label, v in labelled:
            self.assertEqual(ps._hold_text(v), kernel_hold_text(v), label)
            self.assertEqual(ps._hold_text(v, "?"), kernel_hold_text(v, "?"), label)
        self.assertEqual(ps._hold_text([1, 2]), "list")
        self.assertEqual(ps._hold_text({"a": 1}), "dict")
        self.assertEqual(ps._hold_text(7), "7")
        self.assertEqual(ps._hold_text("", "?"), "?")


class HeldRecordsUnderAFalseIdAreNeverServed(_HeldStore):
    """The bus decides a hold by its FILE name (quarantine_get), and the walk vetted a record's shape but never its `mid`
    (the fork PR's extra6-1, 2026-09-20): a held file carrying another hold's mid, no mid, a mid of another type, or a mid
    _safe_id refuses was served by quarantine_list and GET /quarantine and gossiped by _hold_rows under a false id, with
    nothing logged, and a decide by the other message's id could act on a file never read. Now the walk applies the rule
    the kernel's reader applies, one rule on both sides: such a record is skipped and said once per file, the line naming
    the FILE and never the id it carries; the good hold beside it stands and is decidable; and quarantine_decide refuses a
    record whose id is not the name it was asked by, so a decide on the collision file's own name acts on nothing. The
    files stay: the kernel's reader is the one that moves them aside. The pinned type-wrong `at` behaviour (sorts oldest,
    stays listed) is untouched.

    Fails before over a git archive of 35fad278c (round 2's walk, which vets no mid): the collision record is listed under
    the good hold's id, the no-mid and integer-mid records are listed, nothing is said. Synthetic: placeholder mids."""

    def _stage(self):
        good = self.HOLD["mid"]
        collision = self._write(self.M2, json.dumps(dict(self.HOLD)))                        # M2.json carrying good's mid
        nomid = self._write(self.M3, json.dumps({k: v for k, v in self.HOLD.items() if k != "mid"}))
        intmid = self._write(self.M4, json.dumps(dict(self.HOLD, mid=7)))
        undecidable = self._write("bad id", json.dumps(dict(self.HOLD, mid="bad id")))       # its own name, one _safe_id refuses
        return good, collision, nomid, intmid, undecidable

    def test_records_under_a_false_id_are_skipped_named_by_file_and_the_good_hold_stands(self):
        good, collision, nomid, intmid, undecidable = self._stage()
        self.assertEqual([h.get("mid") for h in ps.quarantine_list()], [good], "served under a false id, or none")
        self.assertEqual([r.get("mid") for r in ps._hold_rows()], [good], "the gossip summary carries no false id")
        code, body = self._get(self._serve())
        self.assertEqual((code, [h.get("mid") for h in body["held"]]), (200, [good]))
        said = self._said()
        self.assertEqual(len(said), 4, self.logged)
        by_file = {f.name: next(l for l in said if f.name in l) for f in (collision, nomid, intmid, undecidable)}
        self.assertIn("a record whose message id is not the file's name", by_file[collision.name])
        self.assertNotIn(good, by_file[collision.name], "the line names the file, never the foreign id")
        self.assertIn("a record with no message id", by_file[nomid.name])
        self.assertIn("a record whose message id is not the file's name", by_file[intmid.name])
        self.assertIn("a record whose message id the bus cannot decide", by_file[undecidable.name])
        self.assertFalse(any("invented held text" in l for l in self.logged), "never the record's text")
        ps.quarantine_list()
        ps._hold_rows()
        self.assertEqual(len(self._said()), 4, "said once per file per episode")
        self.assertTrue(all(f.is_file() for f in (collision, nomid, intmid, undecidable)), "left in place")
        self.assertEqual([p for p, _ in self.told], [], "no bell row from the bus")

    def test_a_decide_on_the_collision_files_own_name_acts_on_nothing(self):
        good, collision, nomid, intmid, undecidable = self._stage()
        goodfile = ps.QUARANTINE / (good + ".json")
        for name in (self.M2, self.M3, self.M4):
            for action in ("deny", "approve"):
                ok, err = ps.quarantine_decide(name, action)
                self.assertFalse(ok, (name, action, err))
                self.assertIn("cannot be decided under this name", err)
                self.assertNotIn("no held message", err, "the file is on disk: never reported absent")
        self.assertTrue(collision.is_file() and nomid.is_file() and intmid.is_file(), "nothing was dropped")
        self.assertTrue(goodfile.is_file(), "the other message was not acted on")
        self.assertEqual(ps.read_box("sess-web", consume=False), [], "nothing was delivered")
        ok, err = ps.quarantine_decide(good, "deny")
        self.assertTrue(ok, err)
        self.assertFalse(goodfile.exists(), "the good hold beside them is decidable")
        self.assertTrue(collision.is_file(), "and its decide left the collision file where it was")


class ListedNamesForgeNoLogLine(_HeldStore):
    """The hold say-so wrote the listed file's name raw into its log line, so a name carrying a line boundary forged a
    second `[postal]` line and a long name wrote a line of its length, while the kernel's notices half gated its key for
    exactly this (the fork PR's extra8-2, 2026-09-20: log injection through a filename). Now every listed name a line
    carries goes through _listed_name: a name whose stem _safe_id accepts (the only names the bus writes) is rendered as
    it is; any other has every line boundary and control character replaced by U+FFFD (the header rule's class, never the
    LF byte alone) and is cut to 133 characters, the widest name the bus writes. The name is still there to act on, and
    it forges nothing. The recall arm's host-directory label goes through the same rule.

    Fails before over a git archive of 35fad278c (round 2's walk and say-so): the line carries the newline and the
    separator, and the long name whole. Synthetic: placeholder mids with invented suffixes."""

    def test_a_name_carrying_a_line_boundary_forges_no_second_line(self):
        record = "{not json"                                             # skipped and said once, on every walk since round 2
        newline = self._write("11111111-2222-3333-4444-555555550601\n[postal] forged line", record)
        separator = self._write("11111111-2222-3333-4444-555555550602 forged", record)
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]])
        said = self._said()
        self.assertEqual(len(said), 2, self.logged)
        for line in said:
            self.assertIsNone(ps._HDR_BREAK_RE.search(line), "no line boundary inside a line: %r" % line)
            self.assertNotIn("\n", line)
            self.assertNotIn(" ", line)
            self.assertIn("�", line, "the boundary is replaced, visibly, never dropped")
        self.assertTrue(any("555555550601" in l for l in said) and any("555555550602" in l for l in said),
                        "the name is still there to act on")
        self.assertTrue(newline.is_file() and separator.is_file())

    def test_a_long_name_writes_a_bounded_line(self):
        long_stem = "l" * 250                                            # with `.json`, the widest name the filesystem takes
        self._write(long_stem, "{not json")
        ps.quarantine_list()
        said = self._said()
        self.assertEqual(len(said), 1, self.logged)
        self.assertNotIn(long_stem, said[0], "the name is cut")
        self.assertIn("l" * 100, said[0], "and still recognisable")
        self.assertLess(len(said[0]), 133 + 120, "a bounded line")
        self.assertLessEqual(len(ps._listed_name("x" * 300 + ".json")), 133)
        self.assertEqual(ps._listed_name(self.HOLD["mid"] + ".json"), self.HOLD["mid"] + ".json", "a name the bus writes, as it is")
        self.assertEqual(ps._listed_name("a" * 128 + ".json"), "a" * 128 + ".json", "the widest name the bus writes, whole")
        self.assertEqual(ps._listed_name("srv\nfake"), "srv�fake", "a directory name, the same rule")

    def test_a_host_directory_name_in_the_recall_arm_forges_no_bell_line(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root lists a mode-000 directory; the fault cannot be staged")
        prior = os.environ.get("ROMP_POSTAL_PEERS")
        os.environ["ROMP_POSTAL_PEERS"] = "1"                            # the outbox arm runs in peer-bus mode only
        self.addCleanup(restore_env, "ROMP_POSTAL_PEERS", prior)
        hostdir = ps.OUTBOX / "srv\nfake"
        hostdir.mkdir(parents=True, exist_ok=True)
        os.chmod(hostdir, 0)
        self.addCleanup(lambda: (os.chmod(hostdir, 0o755), hostdir.rmdir()))
        saved = (ps.local_agents, ps.local_agents_checked)
        ps.local_agents = lambda threads=False: []
        ps.local_agents_checked = lambda threads=False: ([], True)
        self.addCleanup(lambda: setattr(ps, "local_agents", saved[0]))
        self.addCleanup(lambda: setattr(ps, "local_agents_checked", saved[1]))
        ps._recall("11111111-2222-3333-4444-555555550701", "", "11111111-2222-3333-4444-555555550702", kept=[])
        bells = [b.get("text", "") for p, b in self.told if p == "/postal-notice"]
        lines = [l for l in self.logged if "cannot be listed" in l]
        self.assertEqual((len(bells), len(lines)), (1, 1), (self.told, self.logged))
        for text in bells + lines:
            self.assertNotIn("\n", text, "no forged line: %r" % text)
            self.assertIn("outbox srv�fake", text)


class ADirectoryFaultIsSaidOnceForTheDirectory(_HeldStore):
    """The walk said a single DIRECTORY-level fault once per FILE: a held-mail directory that lists but cannot be searched
    (mode 400) fails every record's read with one errno, and 45 records wrote 45 near-identical log lines per episode
    (the fork PR's correctness-3, 2026-09-20: the kernel's bell keeps a ring of 40 rows, and one chmod evicted every other
    notice there; the bus has the log, flooded the same way). Now a listing none of whose two or more records could be read
    is one fact about the store (_unread_fold): said ONCE for the directory with the count, keyed on the directory and the
    errno so a moving count is not said again, and raised as QuarantineUnreadable like an unlistable directory, because a
    reader that could not read must never report absent what it did not read: GET /quarantine answers 503 and _hold_rows
    a fault row, never nothing held over a store full of mail. A fault some files carry and others do not is the files'
    own and stays said per file; one record alone is said per file too. A clean listing ends the episode.

    Fails before over a git archive of 35fad278c: 45 log lines and quarantine_list answering [] (200 with nothing held).
    Skipped as root, who reads through a mode-400 directory. Synthetic: placeholder mids."""

    def _many(self, n):
        return [self._write("11111111-2222-3333-4444-%012d" % i, json.dumps(dict(self.HOLD, mid="11111111-2222-3333-4444-%012d" % i)))
                for i in range(n)]

    def test_a_directory_that_lists_but_cannot_be_searched_is_said_once_with_the_count(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root reads through a mode-400 directory; the fault cannot be staged")
        self._clear_store()
        files = self._many(45)
        os.chmod(ps.QUARANTINE, 0o400)
        try:
            answer = ps.quarantine_list()
        except ps.QuarantineUnreadable as e:
            answer = e
        self.assertEqual(len(self._said()), 1, "once for the directory, not once per file: %d lines" % len(self._said()))
        self.assertIsInstance(answer, ps.QuarantineUnreadable, "never nothing held over 45 records no reader could read: %r" % (answer,))
        self.assertIn("none of its 45 records can be read", str(answer))
        self.assertIn("errno %d" % errno.EACCES, str(answer))
        rows = ps._hold_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("none of its 45 records can be read", rows[0]["fault"])
        code, body = self._get(self._serve())
        self.assertEqual((code, body["held"]), (503, []), "never 200 with nothing held: %r" % (body,))
        self.assertIn("45 records", body["unreadable"])
        with self.assertRaises(ps.QuarantineUnreadable):
            ps.quarantine_list()
        self.assertEqual(len(self._said()), 1, "the second pass says nothing more")
        self.assertEqual([p for p, _ in self.told], [], "no bell row from the bus: the kernel's reader files it")
        os.chmod(ps.QUARANTINE, 0o755)
        self.assertEqual(len(ps.quarantine_list()), 45, "the records stood the whole time")
        self.assertTrue(all(f.is_file() for f in files), "nothing moved aside")
        self.assertNotIn("fault", ps._hold_rows()[0])
        os.chmod(ps.QUARANTINE, 0o400)
        with self.assertRaises(ps.QuarantineUnreadable):
            ps.quarantine_list()
        self.assertEqual(len(self._said()), 2, "the clean listing ended the episode; the fault's return is said again")

    def test_a_fault_of_the_files_own_stays_said_per_file(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root reads a mode-000 file; the fault cannot be staged")
        f2 = self._write(self.M2, json.dumps(dict(self.HOLD, mid=self.M2)))
        f3 = self._write(self.M3, json.dumps(dict(self.HOLD, mid=self.M3)))
        os.chmod(f2, 0)
        os.chmod(f3, 0)
        self.assertEqual([h["mid"] for h in ps.quarantine_list()], [self.HOLD["mid"]], "the readable hold is listed")
        said = self._said()
        self.assertEqual(len(said), 2, self.logged)
        self.assertTrue(any(f2.name in l for l in said) and any(f3.name in l for l in said), "each file named")
        self.assertFalse(any("none of its" in l for l in said), "not the store's fault: some record read")
        self._clear_store()
        alone = self._write(self.M4, json.dumps(dict(self.HOLD, mid=self.M4)))
        os.chmod(alone, 0)
        self.assertEqual(ps.quarantine_list(), [], "one record alone: skipped and said per file, the accepted shape")
        self.assertTrue(any(alone.name in l and "unreadable (errno" in l for l in self._said()))
        self.assertFalse(any("none of its" in l for l in self._said()))


class AHolderWhoseStoreCannotBeListedSaysSoOnTheWire(_HeldStore):
    """_hold_rows swallowed the store's listing fault and answered no rows, so holds_payload shipped nothing for this host
    and on every OTHER machine's dashboard the held-elsewhere section simply disappeared, silently, with no bell row on the
    viewing machine (the fork PR's extra5-3, 2026-09-20; the holder's own board hears it from the kernel's reader). Now the
    fault rides the exchange as ONE row carrying `fault` (_hold_fault_row: the fault's kind and errno text, never a path or
    a record's text, the ordinary keys empty), stamped `via` on the one hop by holds_payload and `atHost` by remote_holds
    like a hold's row, so the viewing machine's kernel proxy (its peers snapshot's remoteHolds) receives it unchanged and
    its panel can say the holder's store could not be read. A listable store carries no fault key. The wire's CONTRACT is
    in the postal unit's report; tests/test_postal_peers.py drives the same row through a real two-bus exchange.

    Fails before over a git archive of bc88256e8 (the swallow predates the PR: holds_payload is [] over the fault). Skipped
    as root, who lists a mode-000 directory. Synthetic: placeholder mids, the peer name TESTHOST."""

    def setUp(self):
        super().setUp()
        self.addCleanup(ps.PEER_STATE.pop, "TESTHOST", None)

    def test_an_unlistable_store_rides_as_one_fault_row_and_reaches_remote_holds_with_at_host(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root lists a mode-000 directory; the fault cannot be staged")
        os.chmod(ps.QUARANTINE, 0)
        payload = ps.holds_payload("other")
        self.assertEqual(len(payload), 1, payload)
        row = payload[0]
        self.assertIn("cannot be listed", row["fault"])
        self.assertIn("PermissionError", row["fault"])
        self.assertIn("errno %d" % errno.EACCES, row["fault"])
        self.assertNotIn(str(ps.QUARANTINE), row["fault"], "the fault text carries no path")
        self.assertEqual((row["mid"], row["frm"], row["to"], row["gist"], row["at"]), ("", "", "", "", 0))
        self.assertNotIn("via", row, "this host's own row")
        # the receiving bus folds the payload in as the dialer's half of the exchange does
        ps.peer_exchange_apply("TESTHOST", {}, {"presence": [], "epoch": 1, "holds": payload})
        remote = ps.remote_holds()
        self.assertEqual(len(remote), 1, remote)
        self.assertEqual((remote[0]["atHost"], remote[0]["fault"]), ("TESTHOST", row["fault"]))
        self.assertEqual(ps.peers_snapshot()["remoteHolds"], remote, "what the kernel proxies to the panel")
        os.chmod(ps.QUARANTINE, 0o755)
        hop = ps.holds_payload("third")               # the one hop: our own hold, and the fault row labelled via
        self.assertEqual([(r.get("mid"), r.get("via")) for r in hop], [(self.HOLD["mid"], None), ("", "TESTHOST")])
        self.assertEqual(hop[1]["fault"], row["fault"])
        self.assertEqual([r.get("mid") for r in ps.holds_payload("TESTHOST")], [self.HOLD["mid"]], "never gossiped back to its holder")

    def test_a_listable_store_carries_no_fault_key(self):
        payload = ps.holds_payload("other")
        self.assertEqual([r["mid"] for r in payload], [self.HOLD["mid"]])
        self.assertTrue(all("fault" not in r for r in payload))
        ps.peer_exchange_apply("TESTHOST", {}, {"presence": [], "epoch": 1, "holds": payload})
        self.assertTrue(all("fault" not in r for r in ps.remote_holds()))
        self.assertEqual([r["atHost"] for r in ps.remote_holds()], ["TESTHOST"])


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
