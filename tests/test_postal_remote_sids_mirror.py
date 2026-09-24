#!/usr/bin/env python3
"""The postal bus's presence mirror (the bus's STATE/remote-sids, <state root>/postal/remote-sids), the
file kernel/judge's dead-session ladder reads for rules 4 and 5 (_presumed_closed_verdict). Since fork PR
#897's round 2 the mirror is a document, one row per PRESENCE SOURCE with the roster it last reported and
whether THIS bus process can vouch for it (postal_service.py _remote_sids_document): `heard` (a heartbeat or
exchange arrived in this process), `expired` (a legacy heartbeat past HEARTBEAT_TTL), `linkDown` (the kernel
holds its link down, or has since it was heard), `linkUp` (the kernel holds its link up and it was heard since
the link last dropped), `answered` (the roster is an ANSWERED listing: the `presenceAnswered` the source's
exchange carried, False while its kernel listing did not answer and the exchange served the last answered rows;
a hub stamps the FAR host's bit on its gossip, `viaAnswered`; a legacy heartbeat is its own answer), `reachable`
(heard and not expired and not linkDown: the source vouches for the PRESENCE of the sids it names, rule 4),
`vouchesAbsence` (heard and not expired and answered and linkUp, or a heartbeat within its TTL under the legacy
singleton scheme alone, ROMP_POSTAL_PEERS=0, peers_on() read at the write: the source vouches for the ABSENCE of a
sid it does not name, rule 5's precondition), `sids`. The reader presumes a sid
closed only when a source vouches for absence, none names it, no reachable source's roster is unanswered (the
reader's listing-unanswered arm, round 4 of fork PR #897, the twenty-ninth commit; this module runs no reader,
tests/test_dead_session_staleness.py does) and no lost-carry mark stands. Two roads to a false settle closed here, at the
writer:
  (1) a bus restarted from empty memory wrote its first mirror from that memory, naming nobody: every key
      the previous file named that this process has not heard is CARRIED FORWARD, its roster kept, heard
      false, until its heartbeat or exchange arrives (the event);
  (2) an expired legacy heartbeat was PRUNED, so a stalled peer past the TTL removed a live session's
      sid: the row stays, marked expired; a beat from the session (the event) makes it reachable again, and a
      session that ended beats no more, so the row stands for the file's life (the disclosed cost; the mirror's
      one release is a heartbeat row whose sid the local kernel's ANSWERED listing owns, dropped by the writer:
      round 3 of fork PR #897, the seventeenth commit).
And the kernel's link state decides what a source vouches for (round 2 of fork PR #897, the reviewer's
ruling): a session started on a host after its last heard roster is in no roster, so a host counted as
vouching for absence while its link is down, or while the kernel has never reported it up, would let rule 5
presume that session closed. A heard source vouches for presence whatever its link state, as long as it is
not held down; it vouches for absence only when its link is KNOWN UP. The kernel's down notify (peer_update,
the /peer route) writes the mirror itself, the host unreachable at once with its roster kept; the host is
reachable again on its first heartbeat or exchange heard with the link up, not on the up notify (the exchange
replaces the PEER_STATE row and with it the mark the down notify set: _link_down), and vouches for absence
from that exchange (_link_up: PEERS up and heard since). A far host gossiped through a hub follows the hub's
link; a source with no link state (no dialable PEERS row: never notified, an origin-only trust row, or a name
the kernel does not dial) vouches for presence alone; a heartbeat has no link and vouches by its TTL under the
legacy singleton scheme alone: in peer mode (the default, which this module runs under) a beat that reaches the bus's
table is a local session's, filed as remote presence by _record_heartbeat while the kernel's listing did not answer,
and its row vouches for presence alone (round 3 of fork PR #897, the reviewer's ruling: counted as vouching, such a
beat let a restarted bus that had heard no host presume every sid nothing named closed within the beat's TTL, and let
a blink's phantom vouch while a peer's link was down); such a row has the mirror's one release: the write after a
listing this bus read answered and owns its sid drops it, heard or carried, and forgets the entry once the file without
the row is in place (round 3 of fork PR #897, the seventeenth commit; the sixteenth had refused a pop in the recorder,
which left the carry a key to re-file, and kept the row).
The gate reaches a peer's row under the name it is filed under, and the kernel notifies the ALIAS it dials:
the dialer's fold files there, the dialed side's handler files a far bus under the name it DECLARES until a
row under a dialable name carries its busId (_canon_peer_name), so before this bus's own dial has folded the
peer, a far bus heard only through its dials to us has no link state: it vouches for the presence of the
sids it names and for nothing else, and the alias's down notify has nothing to withdraw from it. The fold is
the event that files the row where the alias's link reaches it (the declared-name test below runs the road
through the real handler, the real notify handler and the real fold; until the fifth commit that row vouched
for absence by heard alone, the road the fourth commit disclosed). Both recorders write the mirror after the
busId fold (the fourth commit), so the fold's own write has one row per bus.
Pinned here, by writing through the real writer and reading the file back: the document's shape; one
source per heartbeat with its own TTL; a peer's own rows under its name and its gossip as a via row under
via:<hub>/<far>; the hub's word about a directly held host, folded into that host's own row only while the row
is heard and not held down, matched by bus id, or by name when the row carries no different known bus id (the
direct row speaks, and a session the gossip names that the row's older roster does not is in no row until the
host's next exchange: the disclosed window and its event), standing beside a held-down or a carried direct row
otherwise, carried like any key, and dropped by the carry once the direct host speaks again or the hub's current
word about it folds (round 3 of fork PR #897, the reviewer's ruling: never discard a heard source's word); a name
match yielding to a known different bus id (another machine the hub calls by that name, found by the reviewer's
verifier, or the far bus restarted under a new id, in either ordering of who hears it first, leaving no via row
behind once the ids agree); the ruled drop reached with the hub NOT heard, the far host heard again with its link up before
the hub or the hub never heard (the carry's gate, which every earlier pin reached only after the hub's gossip had folded);
the two name axes of a via key, the hub folded from the hostname it declared under the alias the kernel dials (through the
real inbound handler and the real fold) and the hub's own fold of the far host under the alias IT dials, the hub's earlier
word under the old key dropped by identity, its bus heard under another name or its current word naming the far bus under
another name, so a session that ended across the rename is in no row where rule 5 is due; the two identity drops' negatives
with the fixture every real bus presents, a bus id on the hub's row (the reviewer's verifier: every carried-hub fixture until
then had none), a carried hub's word about a host nobody holds standing while its bus is heard under no other name, whatever
another host vouches, and a second hub's current word about the far bus dropping no other hub's carried row; a PEER_STATE row no exchange produced is not a source; the carry-forward across a restart and its release per host; the kernel's
seed of a carried host's link up at a restart, which vouches for nothing until the host is heard; the fold
of a carried row for a bus heard under its other name; the whitespace list of the shape until 2026-09-22
carried as one legacy source and pruned as heard sources name its sids; a file of neither shape carrying
nothing; a write failure said once in the bus log; the two flags at the notify and at the two exchange
recorders, the hub's link for a far host (a hub with no link state included), the sources with no link
state vouching for presence alone, and the declared-name road with the fold that ends it; the cached roster (round 3
of fork PR #897, the reviewer's ruling, found by its refuters through the real handler and this writer): a heard host
the kernel holds up whose exchange served the last answered rows through a kernel blink vouches for presence alone,
the bit riding both payload builders (the real request builder and the real response builder, one module playing both
buses) and recorded by both recorders, released by the next exchange that carries an answered listing, a payload
lacking the field or carrying a non-boolean reading unanswered, a via row carrying the far host's bit and not the
hub's, and the bit stated for a heartbeat, the legacy list and a row carried from a file that predates the field; and
the hub's word beside a CACHED direct row (the reviewer's verifier at the eleventh commit, by execution through the real
builder, handler, writer and reader): a heard row over a cache is the third state, beside carried and held down, in
which a direct row speaks for nothing about a session started on its host since, so a hub's answered word about such a
session stands as a via row beside the cached row, carrying the far host's bit as the hub stamped it, and with the hub
not heard the carried via row stands beside the cached row, until the far host's exchange that answers, the event (at
the eleventh commit the gate read heard and not held down alone, the hub's word folded into the cached row, and the
hub, vouching for absence, let rule 5 presume a live session closed for one exchange interval of the far host); and
the heartbeat row's scheme gate (round 3 of fork PR #897, the reviewer's ruling): a beat through the real recorder
during a listing blink in peer mode vouching for presence alone, nothing vouching beside a peer the kernel holds down,
the same rows under ROMP_POSTAL_PEERS=0 vouching by the TTL; the four earlier heartbeat pins of this module that
asserted the TTL vouch are re-pinned to peer mode's presence alone, each saying so; and the mirror's ONE RELEASE
(round 3 of fork PR #897, the reviewer's ruling, the seventeenth commit): a heartbeat row whose sid the local kernel's
ANSWERED listing owns, as this bus last read it through local_agents_checked, is dropped by the writer, heard or
carried, and the entry forgotten with it so no later write re-emits it; a beat filed while the listing did not answer
is kept, by the recorder's write and by a bare one (a writer reading the presence producer's cache, or the last answered
listing's sids through the blink, drops it); a row the listing does not own is kept, and an answered empty listing
releases nothing; a read without thread rows owns no thread's sid, and the recorder's read, which asks for them, does;
the release reaching heartbeat rows alone, a carried legacy list, peer row and via row naming an owned sid beside another
carried whole (the reviewer's verifier at the seventeenth commit: a carry with its kind test deleted passed every pin),
and a heard peer row and via row doing so written whole (its verifier at the eighteenth: an in-memory drop of the via
row passed every pin); the release's order across a write that fails, at the temporary file or at the replace, the
entry kept and the row re-emitted heard until a write succeeds; the previous-read's bytes (round 3 of fork PR #897, the
reviewer's ruling, the twentieth commit, and its ruling of 14:57Z, the twenty-second): a file whose bytes are not UTF-8 no
longer fails every write, a document nested past the JSON parser's depth neither (RecursionError, found by the twentieth
commit's builder; the class is the interpreter's, and the cases derive it from the parse, the twenty-fifth), and a carried
row's values are coerced, never dropped: its flags bool(), a busId that is not a str ignored, each sid str() and then
validated, one that fails the session-id shape dropped and counted; one bad byte costs one sid, never the document (the
replacing decode for the JSON parse alone, the whitespace list keeping the strict decode, so
garbage whose runs look like session ids is never carried as legacy sids), with one line in the bus log naming the file
and the count; a byte-order mark read before the document and before the list; and a previous file the read cannot read
whole carrying no row and MARKING the document with the cause and the second, said once, for each such file (an empty
one among them), nothing said or marked for no file or a readable one, the mark carried by every write and across a
restart until the bus process that read the kernel's list of links at its start has heard every dialable PEERS host since
it, kept while a linked host stays down, kept in a bus whose seed failed or whose link table is empty, kept when it is read
in another shape or a stray byte hits a top-level key, and cleared, said once, on the ruled event, a host counting toward
it only once heard (a mark at second 0 among them) and an origin-only row never counting; and the clear's first-start
answer (the reviewer's verifier at the twenty-second commit, and the reviewer's ruling of 15:45Z): a session on a host that
no linked host hears now is outside every source after the clear, as on a first start, a far host's session its hub, the
one link, no longer hears in no row once the mark clears, the rows a first start writes.
tests/test_dead_session_staleness.py ReaderFollowsTheWriter
runs this writer and the judge's reader together over one root; tests/test_postal_bus_lifetime.py
MonitorTick pins the poll's write. SYNTHETIC fixtures only: private synthetic sids, hostname TESTHOST."""
import builtins
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from romp_load import load_source
from tests.conftest import restore_env

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the load (the module resolves its state root at import time); `session-hosts` off in
# the minted root, the repo rule for a test that builds its own state root
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
_ROOT = Path(os.environ["XDG_STATE_HOME"]) / "romp"
_ROOT.mkdir(parents=True, exist_ok=True)
(_ROOT / "session-hosts").write_text("off\n")
pm = load_source("romp_postal_mirror", os.path.join(BIN, "romp-postal-service"))

A = "a5a5a5a5-0001-4000-8000-000000000001"   # private synthetic sids, never the shared placeholder
B = "a5a5a5a5-0002-4000-8000-000000000002"
C = "a5a5a5a5-0003-4000-8000-000000000003"
D = "a5a5a5a5-0004-4000-8000-000000000004"
E = "a5a5a5a5-0005-4000-8000-000000000005"
HOST, HUB, FAR = "TESTHOST", "TESTHOST-hub", "TESTHOST-far"
FAR_ALIAS = "TESTHOST-far-alias"               # the name the kernel dials the far host by when the hub knows it as FAR
FAR_DECL = "TESTHOST-far-hostname"             # the hostname the far bus declares to the HUB before the hub's own dial folds it under FAR
HUB_DECL = "TESTHOST-hub-hostname"             # the hostname the hub declares when its own dial lands here before ours folds it under HUB
VIA = "via:"                                   # the key of a hub's word about a far host, via:<hub>/<far> (pm.REMOTE_SIDS_VIA)
VIA_FAR = VIA + HUB + "/" + FAR
HB = "heartbeat:"                              # the key of a legacy heartbeat's row (pm.REMOTE_SIDS_HEARTBEAT)
LEGACY = "legacy:list"                         # the key a whitespace-list mirror is carried under (pm.REMOTE_SIDS_LEGACY)


def _listing_record():
    """The writer's record of the local listing as the bus last read it (_LOCAL_LISTING, round 3 of fork PR #897), read
    directly, so a record renamed or removed fails this module loudly in setUp (the seventeenth commit read it with getattr
    for its red-before over the product before the record, and a fixture that silently did nothing would have outlived
    that need: the reviewer's verifier, the eighteenth commit)."""
    return pm._LOCAL_LISTING[0]


def _forget_listing(value=None):
    """Set the record to `value` (None: no listing read yet in this "process")."""
    pm._LOCAL_LISTING[0] = value


def _nested_parse_raises(data):
    """(the class json.loads raises on the document `data` in THIS interpreter, or None when it returns; the depth of its
    nesting). The class a parse of a document nested past the parser's depth raises is the interpreter's (round 3 of fork PR
    #897, the reviewer's ruling of 17:47Z, the twenty-fifth commit): since 3.14 the depth guard depends on the machine's
    stack, and on a CI runner's 3.14t json.loads parsed the 100000 levels these cases plant to the end and raised
    JSONDecodeError (a ValueError), where this box's 3.12 and 3.14t raise RecursionError. So a case that plants such a
    document parses the SAME bytes here, decoded as both parses decode them, asserts that the parse raised, failing by the
    interpreter and the depth when it returns (its premise, a file the parse cannot read, gone), and asserts the class it
    derived. That the product catches both classes is pinned once, by tests/test_dead_session_staleness.py
    ReaderFollowsTheWriter test_the_writers_previous_read_and_the_reader_catch_both_classes_a_nested_parse_can_raise. The
    same function, the same shape, stands in that module's child as nested_parse_raises.
    The check that the parse raised requires a class name, and the cause assertion requires the derived class in the slot
    the product fills from the exception it caught, "(<class>: " (the reviewer's verifier at the twenty-fifth commit, the
    twenty-sixth): with this function made to return the empty name for a parse that returns, the check read only "not
    None" and the empty name is found in every cause, so the cases passed with the parse stubbed to return. The class name
    is the name of an exception class since the twenty-seventh (_names_an_exception_class, which says why an identifier was
    not enough)."""
    depth = len(data) - len(data.lstrip(b"["))
    try:
        json.loads(data.decode("utf-8-sig"))
    except Exception as e:
        return type(e).__name__, depth
    return None, depth


def _names_an_exception_class(name):
    """True when `name`, the class _nested_parse_raises derived, names an exception class bound in builtins or in the
    json module (json.loads raises RecursionError, ValueError, MemoryError or JSONDecodeError; the check accepts any such
    class, and the cause assertion refuses every one of them when the parse returns). The check that the
    nested document's parse raised requires it (the reviewer's verifier at the twenty-sixth commit, the twenty-seventh).
    The twenty-sixth commit's check required an identifier, and a derivation made to return the name of the type of what
    a parse that returns produced passed it: a parse that returns None derived "NoneType". The writer fills the cause's
    "(<class>: " slot with the class of the exception its parse caught, and when the parse returns None and the text is
    not read as the whitespace list it fills the slot with the class of None, "(NoneType: None)", so both cases here
    passed with the parse stubbed to return None. NoneType is no exception class, so the check fails there, naming the
    interpreter and the depth. Any name that passes this check is refused at the cause when the parse returns: the
    writer's cause then carries "(NoneType: ", or no such slot, or there is no mark. The staleness case keeps the
    identifier check in its child: it also reads the reader's line, which says "(ValueError: not a JSON object)" for a
    parse that returns None, so a derived "NoneType" fails there."""
    cls = (getattr(builtins, name, None) or getattr(json, name, None)) if isinstance(name, str) else None
    return isinstance(cls, type) and issubclass(cls, BaseException)


class Mirror(unittest.TestCase):
    def setUp(self):
        pm.STATE.mkdir(parents=True, exist_ok=True)
        self.path = pm.STATE / "remote-sids"
        self.path.unlink(missing_ok=True)
        saved = (dict(pm.HEARTBEATS), dict(pm.PEER_STATE), dict(pm.PEERS), _listing_record(), pm._PEERS_SEEDED[0])
        pm.HEARTBEATS.clear(); pm.PEER_STATE.clear(); pm.PEERS.clear()
        _forget_listing()                             # no listing read yet in this "process": the writer releases nothing
        pm._PEERS_SEEDED[0] = False                   # ...and no seed from the kernel's list of links

        def restore():
            for d, v in zip((pm.HEARTBEATS, pm.PEER_STATE, pm.PEERS), saved):
                d.clear(); d.update(v)
            _forget_listing(saved[3])
            pm._PEERS_SEEDED[0] = saved[4]
            self.path.unlink(missing_ok=True)
        self.addCleanup(restore)
        reconcile = pm._peer_threads_reconcile
        pm._peer_threads_reconcile = lambda host: None    # the notify's dialer bookkeeping is not under test: an up
        self.addCleanup(setattr, pm, "_peer_threads_reconcile", reconcile)   # notify would dial a loopback port nothing listens on
        self.now = pm.time.time()

    def _rows(self):
        """key -> (heard, expired, sids) from the file, or the raw text when it is not a document (so a writer
        of another shape fails a pin by its message rather than by an exception)."""
        text = self.path.read_text()
        try:
            return {k: (r["heard"], r["expired"], r["sids"]) for k, r in json.loads(text)["hosts"].items()}
        except (ValueError, KeyError, TypeError):
            return text

    def _doc(self):
        return json.loads(self.path.read_text())

    def _reach(self):
        """key -> (heard, expired, linkDown, reachable, sids): the row's four flags, the last the reader's. The two link
        flags are read with .get, so a writer that spells neither fails a pin by its message (None where a bool is
        due) rather than by an exception."""
        return {k: (r["heard"], r["expired"], r.get("linkDown"), r.get("reachable"), r["sids"])
                for k, r in json.loads(self.path.read_text())["hosts"].items()}

    def _vouch(self):
        """key -> (reachable, linkUp, vouchesAbsence): what the row vouches for, presence (rule 4) and absence (rule
        5's precondition), and the known-up link the second turns on. Read with .get, so a writer missing a flag
        fails a pin by None where a bool is due rather than by an exception."""
        return {k: (r.get("reachable"), r.get("linkUp"), r.get("vouchesAbsence"))
                for k, r in json.loads(self.path.read_text())["hosts"].items()}

    def _answered(self):
        """key -> answered: whether the row's roster is an answered listing (round 3 of fork PR #897), the second gate
        on absence beside the link. Read with .get, so a writer that does not spell it fails a pin by None."""
        return {k: r.get("answered") for k, r in json.loads(self.path.read_text())["hosts"].items()}

    def _notify(self, host, up, port=50002):
        """The kernel's /peer notify for a tunnel transition, through the real handler (peer_update), which writes
        the mirror itself; nothing else writes between the notify and the read that follows it."""
        payload, status = pm.peer_update({"host": host, "port": port, "up": up})
        self.assertEqual(status, 200, payload)

    def _exchange_request(self, host, presence, answered=True):
        """A dialer's request as build_exchange_request shapes it. `answered` is its `presenceAnswered`, whether its
        listing answered for `presence` (round 3 of fork PR #897); None leaves the field out, a dialer from before it."""
        req = {"host": host, "epoch": 1, "proto": pm.PEER_PROTO, "presence": presence, "holds": [],
               "relays": [], "acks": [], "bounces": [], "wait": False}
        if answered is not None:
            req["presenceAnswered"] = answered
        return req

    def _peer(self, host, presence, seen_ago=5, bus_id=None, answered=True, via_answered=True):
        """The PEER_STATE row a recorder leaves after an exchange from `host`: its presence as sent, its bus id, and
        `presenceAnswered` (`answered`), whether its listing answered for the roster (round 3 of fork PR #897; the
        recorders read JSON true alone). A via element in `presence` that spells no `viaAnswered` of its own is stamped
        `via_answered`, as the hub's presence_payload stamps the FAR host's bit on every gossiped row before sending;
        an element that spells its own keeps it (a far host whose roster was a cache); None stamps nothing, a hub from
        before the field."""
        st = {"presence": [dict(pa, viaAnswered=via_answered)
                           if pa.get("via") and "viaAnswered" not in pa and via_answered is not None else pa
                           for pa in presence],
              "epoch": 1, "holds": [], "seenAt": int(self.now - seen_ago), "presenceAnswered": answered}
        if bus_id:
            st["busId"] = bus_id
        pm.PEER_STATE[host] = st

    def _restart(self):
        """A restarted bus process's memory: nothing heard yet, no listing read yet, no seed from the kernel's list of links
        yet, the file still on disk."""
        pm.HEARTBEATS.clear(); pm.PEER_STATE.clear(); _forget_listing()
        pm._PEERS_SEEDED[0] = False

    def _local_listing_answered_empty(self):
        """The local sessions listing the dialed side's handler gossips in its response presence, answered and
        empty, through the ROMP_SESSIONS_FILE seam; put back as found."""
        seam = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        seam.write("[]"); seam.close()
        self.addCleanup(os.unlink, seam.name)
        self.addCleanup(restore_env, "ROMP_SESSIONS_FILE", os.environ.get("ROMP_SESSIONS_FILE"))
        os.environ["ROMP_SESSIONS_FILE"] = seam.name

    def _far_dials_us(self, declared, presence, bus_id, answered=True):
        """The dialed side of one exchange, through the real handler: the far bus declares `declared` and `bus_id`, and
        `answered` is its presenceAnswered (None: a dialer from before the field). Returns the handler's response."""
        req = dict(self._exchange_request(declared, presence, answered), busId=bus_id)
        resp, status = pm.peer_exchange_handle(req)
        self.assertEqual(status, 200, resp)
        return resp

    def _local_listing_answered(self, rows):
        """The local sessions listing, answered with `rows`, through the ROMP_SESSIONS_FILE seam; put back as found."""
        seam = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        seam.write(json.dumps(rows)); seam.close()
        self.addCleanup(os.unlink, seam.name)
        self.addCleanup(restore_env, "ROMP_SESSIONS_FILE", os.environ.get("ROMP_SESSIONS_FILE"))
        os.environ["ROMP_SESSIONS_FILE"] = seam.name

    def _local_listing_unanswered(self):
        """The local sessions listing NOT answering (the kernel mid-restart): the seam unset, so _kernel_sessions_checked
        fetches the live route, pointed at a loopback port nothing listens on (the relay-honesty module's idiom; never
        the live kernel's port). Both put back as found."""
        self.addCleanup(restore_env, "ROMP_SESSIONS_FILE", os.environ.get("ROMP_SESSIONS_FILE"))
        os.environ.pop("ROMP_SESSIONS_FILE", None)
        base = pm.KERNEL_BASE
        pm.KERNEL_BASE = "http://127.0.0.1:9"
        self.addCleanup(setattr, pm, "KERNEL_BASE", base)

    def _forget_presence_cache(self):
        """The presence producer's last-answered cache (memory and its disk twin) emptied for this test and put back
        after it: _local_presence_checked serves it while the listing does not answer, and other tests' answered
        reads have filled it."""
        saved = (list(pm._LOCAL_PRESENCE_GOOD[0]), pm._LOCAL_PRESENCE_GOOD[1], pm._PRESENCE_SERVE_WARNED[0])
        twin = pm._PRESENCE_GOOD_FILE
        prior = twin.read_bytes() if twin.exists() else None

        def restore():
            pm._LOCAL_PRESENCE_GOOD[0], pm._LOCAL_PRESENCE_GOOD[1] = saved[0], saved[1]
            pm._PRESENCE_SERVE_WARNED[0] = saved[2]
            if prior is None:
                twin.unlink(missing_ok=True)
            else:
                twin.write_bytes(prior)
        self.addCleanup(restore)
        pm._LOCAL_PRESENCE_GOOD[0], pm._LOCAL_PRESENCE_GOOD[1] = [], False
        pm._PRESENCE_SERVE_WARNED[0] = False
        twin.unlink(missing_ok=True)

    def _legacy_scheme(self):
        """The legacy singleton scheme for the rest of this test: ROMP_POSTAL_PEERS=0, the switch peers_on reads at call
        time, put back as found; the mode is read back through the product's own reader, never assumed."""
        self.addCleanup(restore_env, "ROMP_POSTAL_PEERS", os.environ.get("ROMP_POSTAL_PEERS"))
        os.environ["ROMP_POSTAL_PEERS"] = "0"
        self.assertFalse(pm.peers_on(), "the legacy scheme is on for this test")

    def test_the_document_shape(self):
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}], bus_id="bus-1")
        pm._write_remote_sids()
        doc = self._doc()
        self.assertEqual(sorted(doc), ["busStarted", "hosts", "v", "writtenAt"])
        self.assertEqual((doc["v"], doc["busStarted"]), (2, pm.BUS_EPOCH), "the writing process's boot second")
        self.assertIsInstance(doc["writtenAt"], int)
        self.assertTrue(pm.peers_on(), "peer mode, the default this module runs under")
        self.assertEqual(doc["hosts"][HB + A], {"kind": "heartbeat", "sids": [A], "heard": True, "expired": False,
                                                 "linkDown": False, "linkUp": False, "answered": True, "reachable": True,
                                                 "vouchesAbsence": False, "seenAt": int(self.now), "name": "web"},
                         "a heartbeat row in peer mode: no link, and the TTL vouch belongs to the legacy scheme, so it vouches "
                         "for presence alone (RE-PINNED in round 3 of fork PR #897 from the TTL vouch, which "
                         "test_a_heartbeat_row_vouches_for_absence_under_the_legacy_scheme_alone pins under ROMP_POSTAL_PEERS=0); "
                         "the session's own beat is its own answer (answered), so no listing gates it")
        self.assertEqual(doc["hosts"][HOST], {"kind": "peer", "sids": [B], "heard": True, "expired": False,
                                              "linkDown": False, "linkUp": False, "answered": True, "reachable": True,
                                              "vouchesAbsence": False, "seenAt": int(self.now - 5), "busId": "bus-1"},
                         "a heard peer the kernel never notified: no link state, so it vouches for presence alone; its "
                         "exchange carried an answered listing (answered), the seventh flag the reader requires")
        self.assertTrue(self.path.read_text().endswith("}\n"), "one document, newline-terminated")

    def test_each_heartbeat_is_its_own_source_with_its_own_ttl(self):
        pm.HEARTBEATS[A] = ("web", self.now - pm.HEARTBEAT_TTL - 1)   # past the TTL by the recorded time
        pm.HEARTBEATS[B] = ("api", self.now)
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, True, [A]), HB + B: (True, False, [B])},
                         "the expired beat's row stays, marked expired, roster kept: unreachable, not absent (the shape "
                         "until 2026-09-22 pruned it, the second road of fork PR #897's round 1)")

    def test_a_heartbeat_row_vouches_for_absence_under_the_legacy_scheme_alone(self):
        """Round 3 of fork PR #897, the reviewer's ruling on its refuters' finding (by execution): in peer mode, the default,
        the beats that reach HEARTBEATS are LOCAL sessions' beats, filed as remote presence by _record_heartbeat while this
        kernel's listing did not answer (a remote session's presence arrives through the exchange, and a local session stops
        beating once its bus calls it local), so a heartbeat row there names a session of this machine and says nothing about
        any other host: it vouches for presence alone. Counted as vouching by its TTL, as every heartbeat row was until this
        commit, one such beat let a restarted bus that had heard no host presume every sid nothing named closed within the
        beat's TTL, and let a blink's phantom vouch while a peer's link was down. Under the legacy singleton scheme
        (ROMP_POSTAL_PEERS=0) the beats are a remote session's only presence and the row vouches by its TTL as ruled in
        round 1. The scheme is read at each write (peers_on), so the same rows flip with the switch and nothing is stored on
        the row. The beat arrives through the REAL recorder under a listing that does not answer, as in the blink. What
        happens once the listing answers and owns the sid is the writer's release, pinned by
        test_a_heartbeat_row_whose_sid_the_answered_local_listing_owns_is_released_by_the_writer (the seventeenth
        commit). The composition with the reader's verdicts is tests/test_dead_session_staleness.py
        ReaderFollowsTheWriter (the peer-mode beat phase)."""
        self.assertTrue(pm.peers_on(), "peer mode, the default this module runs under")
        self._local_listing_unanswered()                      # the kernel mid-restart: the listing does not answer
        self.assertFalse(pm._record_heartbeat(A, "web"), "the listing did not answer, so the beat is recorded as remote "
                         "presence (never called local from the client's claim)")
        self.assertIn(A, pm.HEARTBEATS, "the recorder filed the beat")
        self.assertEqual((self._reach()[HB + A], self._vouch()[HB + A], self._answered()[HB + A]),
                         ((True, False, False, True, [A]), (True, False, False), True),
                         "THE RULED CLAUSE: in peer mode the beat's row is heard, reachable, its own answer, and vouches for "
                         "presence alone (a writer vouching a heartbeat by its TTL whatever the scheme says (True, False, True) "
                         "here, and a restarted bus that has heard no host presumes every sid nothing names closed within the "
                         "beat's TTL); the recorder's own write, nothing else wrote")
        self._peer(HOST, [{"id": B, "name": "api"}])          # a peer heard, then the kernel holds its link down
        self._notify(HOST, up=False)
        self.assertEqual(self._vouch(), {HB + A: (True, False, False), HOST: (False, False, False)},
                         "THE BLINK PHANTOM beside a down peer: no row vouches for absence, so a sid nothing names is "
                         "cannot-determine (the TTL vouch made the beat vouch here while the peer was down, and rule 5 fired)")
        self._legacy_scheme()                                 # the same rows under the legacy singleton scheme
        pm._write_remote_sids()
        self.assertEqual(self._vouch(), {HB + A: (True, False, True), HOST: (False, False, False)},
                         "LEGACY KEEPS TTL VOUCHING (round 1's ruling): the beat, a remote session's only presence there, vouches "
                         "for absence by its TTL whatever any peer's link (a writer withholding the vouch in both schemes says "
                         "(True, False, False) here; one reading the switch inverted vouched in peer mode and not here)")
        pm.HEARTBEATS[B] = ("api", self.now - pm.HEARTBEAT_TTL - 1)   # a beat past its TTL under the legacy scheme
        pm._write_remote_sids()
        self.assertEqual(self._vouch()[HB + B], (False, False, False), "expired: unreachable, vouching for nothing, as before")

    def test_a_heartbeat_row_whose_sid_the_answered_local_listing_owns_is_released_by_the_writer(self):
        """Round 3 of fork PR #897, the reviewer's ruling (the seventeenth commit): the mirror's ONE release. A heartbeat
        row whose sid the local kernel's ANSWERED listing owns is dropped by the writer, heard or carried, and the
        HEARTBEATS entry is forgotten with it once the file without the row is in place, so the carry has nothing to
        re-file: rules 1 and 2 of the judge's ladder own a sid the local kernel lists (its transcript is local), and in
        peer mode every beat that reaches the table is such a session's, filed during a listing blink. The listing is the
        one this bus LAST read through local_agents_checked (the recorder at every beat, the presence producer at every
        exchange, the autostop gate at every poll), when that read answered; a listing that did not answer releases
        nothing, and the last answered rows the presence producer serves through a blink are a cache, not the listing's
        word at this write. Until this commit no event removed a heartbeat row: a local session's blink beat stood, heard,
        for the file's life, and the sixteenth commit had refused a pop in the recorder because the carry re-filed the
        key from the file (the reviewer's refuters, by execution); the writer's own drop leaves it nothing to re-file.
        Every other row still has no release (the disclosed cost in _remote_sids_document). The composition with the
        reader's verdicts is tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the peer-mode beat phase); the
        poll's write is tests/test_postal_bus_lifetime.py MonitorTick."""
        self.assertTrue(pm.peers_on(), "peer mode, the default this module runs under")
        self._forget_presence_cache()
        self._local_listing_answered([{"id": A, "name": "web"}])   # the kernel answers: A is a local session
        rows, answered = pm._local_presence_checked()
        self.assertEqual(([r["id"] for r in rows], answered), ([A], True),
                         "the presence producer read the answered listing and cached A (the cache a wrong writer would read)")
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {}, "no beat yet: no row")
        self._local_listing_unanswered()                      # the kernel restarts: the listing does not answer
        self.assertFalse(pm._record_heartbeat(A, "web"), "A's beat during the blink: recorded as remote presence")
        self.assertFalse(pm._record_heartbeat(B, "api"), "a second beat, of a sid no listing of this bus owns")
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HB + B: (True, False, [B])},
                         "A SID OF AN UNANSWERED LISTING IS KEPT: the listing did not answer, so the recorder's write releases "
                         "nothing (a writer reading the presence producer's cache, which serves A through the blink, or the last "
                         "answered listing's sids, drops A's row here)")
        pm._write_remote_sids()                               # a bare write (a notify's, a poll's) while the listing still does not answer
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HB + B: (True, False, [B])}, "...and so does a bare write")
        self._local_listing_answered([{"id": A, "name": "web"}])   # the kernel answers again, owning A
        self.assertEqual([r["id"] for r in pm.local_agents_checked()[0]], [A],
                         "a consumer's read of the answered listing (the presence producer's, the autostop gate's): the event")
        pm._write_remote_sids()                               # the next write, a bare one
        self.assertEqual(self._rows(), {HB + B: (True, False, [B])},
                         "THE RULED RELEASE: A's row is dropped at the next write once the listing this bus read answered and owns "
                         "A (rules 1 and 2 own that sid); B's row, which the listing does not own, is kept")
        self.assertNotIn(A, pm.HEARTBEATS, "the entry is forgotten with the row, so no later write re-emits it (a writer that "
                         "drops the row and keeps the key writes A's row again at the next write the listing does not answer for)")
        self.assertIn(B, pm.HEARTBEATS, "B's entry stays")
        self._local_listing_unanswered()                      # the listing blinks again, and a bare write follows
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + B: (True, False, [B])}, "A's row does not return: no memory and no file carries it")
        pm.HEARTBEATS[C] = ("tests", self.now)                # a beat of C in this process, then a restart: both rows carried
        pm._write_remote_sids()
        self._restart()
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + B: (False, False, [B]), HB + C: (False, False, [C])}, "both carried, heard by nobody")
        self._local_listing_answered([{"id": C, "name": "tests"}])
        pm.local_agents_checked()
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + B: (False, False, [B])},
                         "a CARRIED heartbeat row is released the same way (a writer dropping heard rows alone carries C for the "
                         "file's life); B, which no listing owns, is carried on")
        self._local_listing_answered([])                      # an answered EMPTY listing owns nothing
        pm.local_agents_checked()
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + B: (False, False, [B])}, "an answered listing that owns nothing releases nothing")
        self._local_listing_unanswered()                      # a comment thread's beat during a blink, filed like any other
        self.assertFalse(pm._record_heartbeat(D, "web-comment-1"))
        self._local_listing_answered([{"id": D, "name": "web-comment-1", "thread": True, "parent": A}])
        self.assertEqual(pm.local_agents_checked()[0], [], "the default listing hides the thread row (the seam mirrors the route)")
        pm._write_remote_sids()
        self.assertEqual(self._rows()[HB + D], (True, False, [D]), "a read without thread rows does not own the thread: kept")
        self.assertTrue(pm._record_heartbeat(D, "web-comment-1"), "the recorder asks for thread rows: local")
        self.assertNotIn(HB + D, self._rows(), "...and the recorder's own write releases the row")
        self.assertNotIn(D, pm.HEARTBEATS, "...and forgets the entry")

    def test_the_release_reaches_heartbeat_rows_alone_and_a_carried_row_of_another_kind_naming_an_owned_sid_is_carried_whole(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the seventeenth commit (by execution through the real writer and
        reader): a carry with its kind test deleted, releasing EVERY carried row that names a sid the answered local listing
        owns, passed every pin, and it drops the legacy list a bus before 2026-09-22 wrote when that list names a local
        session beside a session on a host this process has not heard yet; that session is then in no row, and a host
        vouching for absence lets rule 5 presume it closed. The release reaches heartbeat rows alone: the legacy list, a peer
        row and a via row naming an owned sid beside another are that source's word about the other sid and are carried
        whole, while the owned sid's own heartbeat row is released at the same write. The same holds IN MEMORY (the reviewer's
        verifier at the eighteenth commit: a writer dropping a heard via row that names an owned sid beside another passed
        every pin, a false rule 5 for the other sid by execution through the real writer and reader): a heard peer row and a
        heard via row naming the owned sid beside another are written whole under an answered listing owning it. The
        composition with the reader's verdicts (the unheard host's session named-by-unreachable-host by the carried list,
        and the far session a heard hub names beside the local one named-by-reachable-host, never rule 5) is
        tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the release's reach phases)."""
        self.assertTrue(pm.peers_on(), "peer mode, the default this module runs under")
        self.path.write_text(A + "\n" + B + "\n")     # a bus before 2026-09-22 wrote A (a local session now) and B (live on a
        self._local_listing_answered([{"id": A, "name": "web"}])   # host this process has not heard yet)
        self.assertEqual([r["id"] for r in pm.local_agents_checked()[0]], [A], "the listing answered, owning A: the record the release reads")
        self._peer(HOST, [{"id": C, "name": "api"}])   # a host heard, its listing answered, naming neither
        self._notify(HOST, up=True)                     # the kernel holds its link up: the notify's own write
        self.assertEqual(self._vouch()[HOST], (True, True, True), "HOST vouches for absence, so a sid in no row here is rule 5's")
        self.assertEqual(self._rows(), {HOST: (True, False, [C]), LEGACY: (False, False, [A, B])},
                         "THE RELEASE'S REACH, the legacy list: carried whole, B with A, though the listing owns A (a carry releasing "
                         "every row kind that names an owned sid drops the list here, B is in no row while HOST vouches, and the "
                         "reader presumes B closed: the verifier's false rule 5)")
        self.path.unlink()                              # a fresh file: a beat of A, a hub naming A beside D and, as its word about
        self._restart(); pm.PEERS.clear()               # the far host, A beside E
        self._local_listing_unanswered()
        self.assertFalse(pm._record_heartbeat(A, "web"), "A's beat during a blink: filed as remote presence")
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": D, "name": "api"},
                         {"id": A, "name": "web", "via": FAR, "viaBus": "far-bus"}, {"id": E, "name": "api", "via": FAR, "viaBus": "far-bus"}],
                   bus_id="hub-bus")
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HUB: (True, False, [A, D]), VIA_FAR: (True, False, [A, E])})
        self._restart()                                 # a restart: every row carried, heard by nobody
        self._local_listing_answered([{"id": A, "name": "web"}])
        pm.local_agents_checked()                       # the listing answers, owning A
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (False, False, [A, D]), VIA_FAR: (False, False, [A, E])},
                         "THE RELEASE'S REACH, a peer row and a via row: each carried whole, A with D and A with E, while A's own "
                         "carried heartbeat row is released at the same write (a carry releasing every row kind that names an "
                         "owned sid drops both rows here, and D and E with them)")
        self.path.unlink()                              # IN MEMORY: a fresh file, the listing answering owning A, and the hub HEARD,
        self._restart()                                 # naming A beside D and, as its word about the far host, A beside E
        self._local_listing_answered([{"id": A, "name": "web"}])
        self.assertEqual([r["id"] for r in pm.local_agents_checked()[0]], [A], "the listing answered, owning A")
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": D, "name": "api"},
                         {"id": A, "name": "web", "via": FAR, "viaBus": "far-bus"}, {"id": E, "name": "api", "via": FAR, "viaBus": "far-bus"}],
                   bus_id="hub-bus")
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A, D]), VIA_FAR: (True, False, [A, E])},
                         "THE RELEASE'S REACH IN MEMORY, a heard peer row and a heard via row: each written whole, A with D and A "
                         "with E, under an answered listing owning A (a writer releasing a heard via row that names an owned sid "
                         "drops the via row here, E in no row, and a host vouching for absence lets rule 5 presume E closed: the "
                         "verifier's false rule 5 at the eighteenth commit; one releasing a heard peer row drops the hub's own "
                         "row here, D with it)")
        self.assertEqual(self._reach()[VIA_FAR], (True, False, False, True, [A, E]),
                         "the via row heard and reachable, its hub's link not held down: E is rule 4's by it")

    def test_a_released_entry_survives_a_write_that_fails_and_its_row_is_written_heard_until_a_write_succeeds(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the seventeenth commit: _write_remote_sids forgets a released
        HEARTBEATS entry only AFTER the file without the row is in place, and the docstring says the order matters, but a
        writer popping the entry before the replace passed every pin. What the order buys, driven through the real writer: a
        write that fails keeps the entry, and the next write under a listing that does not answer re-emits the row heard,
        reachable, this process's own word (rule 4 for the sid); a writer that popped before the replace has lost the entry,
        and that write carries the row from the previous file heard=false, unreachable (cannot-determine for the sid:
        conservative, never closed, but no longer this process's word) until a write under an answered listing releases it.
        The next write that succeeds under an answered listing owning the sid releases the row and forgets the entry, as
        ever. The write fails at each of its two steps: at the temporary file (its path a directory, so the write never
        reaches the replace), and at the replace (os.replace raising for the mirror's path, the temporary file written).
        A pop anywhere before the replace loses the entry at one of them: the reviewer's verifier at the eighteenth commit
        placed the pop between the temporary write and the replace, and the temporary-file case alone passed it."""
        self.assertTrue(pm.peers_on(), "peer mode, the default this module runs under")
        tmp = pm.STATE / "remote-sids.tmp"
        self.addCleanup(lambda: tmp.rmdir() if tmp.is_dir() else tmp.unlink(missing_ok=True))
        said = set(pm._REMOTE_SIDS_SAID)
        self.addCleanup(lambda: (pm._REMOTE_SIDS_SAID.clear(), pm._REMOTE_SIDS_SAID.update(said)))
        real_replace = pm.os.replace
        self.addCleanup(setattr, pm.os, "replace", real_replace)

        def at_the_temporary_file():
            tmp.mkdir()                                 # the write's temporary path a directory: the write fails before the replace
            return tmp.rmdir

        def at_the_replace():
            def replace(src, dst, *args, **kwargs):     # the mirror's replace alone fails; any other replace in the process runs
                if Path(dst) == self.path:
                    raise OSError(5, "the replace failed (synthetic)")
                return real_replace(src, dst, *args, **kwargs)
            pm.os.replace = replace
            return lambda: setattr(pm.os, "replace", real_replace)

        for point, fail, said_as in (("the temporary file", at_the_temporary_file, "(IsADirectoryError"),
                                     ("the replace", at_the_replace, "(OSError: [Errno 5] the replace failed (synthetic)")):
            with self.subTest(failing_at=point):
                pm.HEARTBEATS.clear(); self.path.unlink(missing_ok=True); _forget_listing()
                self._local_listing_unanswered()
                self.assertFalse(pm._record_heartbeat(A, "web"), "A's beat during a blink: filed, and the recorder's write puts its row down")
                self.assertEqual(self._rows(), {HB + A: (True, False, [A])})
                self._local_listing_answered([{"id": A, "name": "web"}])
                pm.local_agents_checked()               # the listing answers, owning A: the next write releases A
                pm._REMOTE_SIDS_SAID.clear()
                err = io.StringIO()
                undo = fail()
                try:
                    with contextlib.redirect_stderr(err):
                        pm._write_remote_sids()
                finally:
                    undo()
                self.assertIn("remote-sids mirror was not written " + said_as, err.getvalue(),
                              "the write failed at %s and said so" % point)
                self.assertIn(A, pm.HEARTBEATS, "THE ORDER: the entry is forgotten only once the file without the row is in place, "
                              "so a write that fails at %s keeps it (a writer popping before the replace has lost it here)" % point)
                self.assertEqual(self._rows(), {HB + A: (True, False, [A])}, "the file is still the recorder's write")
                self._local_listing_unanswered()
                pm.local_agents_checked()               # the listing blinks: the record says unanswered, so nothing is released
                pm._write_remote_sids()
                self.assertEqual(self._reach()[HB + A], (True, False, False, True, [A]),
                                 "the kept entry re-emits the row heard and reachable, rule 4 for A (a writer that popped before the "
                                 "replace carries the row from the previous file here, (False, False, False, False, [A]), unreachable)")
                self._local_listing_answered([{"id": A, "name": "web"}])
                pm.local_agents_checked()
                pm._write_remote_sids()
                self.assertEqual(self._rows(), {}, "the next write that succeeds under an answered listing owning A releases the row")
                self.assertNotIn(A, pm.HEARTBEATS, "...and forgets the entry")

    def test_a_peers_own_rows_under_its_name_and_its_gossip_as_a_via_row_under_the_hub_and_the_far_host(self):
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}], bus_id="hub-bus")
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), VIA_FAR: (True, False, [B])})
        row = self._doc()["hosts"][VIA_FAR]
        self.assertEqual((row["kind"], row["via"], row["host"], row["viaBus"]), ("via", HUB, FAR, "far-bus"),
                         "the hub's word about the far host, keyed by both names under a colon no host name carries (so the "
                         "far host's own row, if any, stands beside it): the hub in via, the far host and its bus id on the row")
        self.assertEqual(self._doc()["hosts"][HUB].get("busId"), "hub-bus", "the hub's own row carries its bus id, as every real bus's does (BUS_ID)")
        # the hub, heard again under the SAME name with the SAME bus id, gossips nothing about the far host: its silence is
        # not a word about the host, so the via row is carried from the previous file, unreachable, instead of its sids
        # vanishing (the road one hop out). The bus id matters to this pin (round 3 of fork PR #897, the reviewer's verifier:
        # every carried-hub fixture until then had none, while every real bus stamps one): the carry's drop of a hub's via
        # rows keys on the hub's bus heard under ANOTHER name, and a carry reading a heard hub's bus id under the same name
        # as that event drops the row here
        self._peer(HUB, [{"id": A, "name": "web"}], bus_id="hub-bus")
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), VIA_FAR: (False, False, [B])},
                         "the same bus under the same name, silent about the far host: its earlier word is carried, not dropped "
                         "(the drop by identity is for a hub heard under another name, whose old rows leave together)")
        # a RESTARTED hub (a bus id is minted per process) that has not heard the far host yet: carried the same
        self._peer(HUB, [{"id": A, "name": "web"}], bus_id="hub-bus-restarted")
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), VIA_FAR: (False, False, [B])},
                         "a restarted hub under its name, silent about the far host it has not heard yet: carried")

    def test_a_hubs_word_about_a_directly_held_host_folds_only_while_that_host_is_heard_and_not_held_down(self):
        """The ruled condition (round 3 of fork PR #897, the reviewer's ruling): the gossip folds into the far host's own
        row only when that row is heard in this process and the kernel does not hold its link down, matched by EITHER
        identity, the name the hub uses for the host or the bus id it stamps on the gossip (the row may sit under the
        alias the kernel dials). Until this round the writer folded it whenever the far host had a dialable PEERS row
        or a heard row, whatever that row's state (_via_duplicate, the display fold), and the second half of this test
        asserted the fold with the direct row CARRIED: the regression round 2 found by execution. The fold's residual
        is witnessed here, disclosed as a bound with the event that closes it, not closed by a timer."""
        self._notify(FAR, up=True)                                            # the kernel's table: a direct link, up
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")       # heard in this process
        self._peer(HUB, [{"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"},
                         {"id": C, "name": "tests", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (True, False, [C])},
                         "heard and not held down: the far host's own word about its sessions, and no via row. THE RESIDUAL, "
                         "disclosed as a bound: the hub names a session on the far host (B) that the far host's older roster "
                         "does not, and that sid is in no row at this write, a window of one exchange interval of the far "
                         "host, closed by its next exchange (the event), not by a timer")
        self._peer(FAR, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], bus_id="far-bus")   # the event
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (True, False, [B, C])},
                         "the far host's next exchange names it")
        # by name alone: a hub that predates viaBus stamps none, and the row under that name speaks
        self._peer(HUB, [{"id": D, "name": "web", "via": FAR}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR: (True, False, [B, C])},
                         "matched by name: folded (a writer folding by bus id alone writes a via row here)")
        # by bus id alone: the far host's row sits under the alias the kernel dials; the hub knows it by another name and
        # stamps the bus id (the notify below writes the mirror itself, so the gossip and the alias row are in place first)
        self._peer(HUB, [{"id": D, "name": "web", "via": FAR, "viaBus": "far-bus"}])
        pm.PEER_STATE.pop(FAR)
        pm.PEERS.pop(FAR)
        self._peer(FAR_ALIAS, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], bus_id="far-bus")
        self._notify(FAR_ALIAS, up=True)
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR_ALIAS: (True, False, [B, C])},
                         "matched by bus id: the row under the alias speaks, folded (a writer folding by name alone writes a "
                         "via row under via:<hub>/<far> beside it); the row under the old name is gone, its bus heard under "
                         "the alias")
        # the negative that flipped: the direct row CARRIED after a restart speaks for nothing, and the hub's word stands
        self._restart()
        pm.PEERS.clear()
        self._notify(FAR_ALIAS, up=True)                  # the kernel's seed: PEERS up for a host this process has not heard
        self._peer(HUB, [{"id": D, "name": "web", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, []), FAR_ALIAS: (False, False, [B, C]), VIA_FAR: (True, False, [D])},
                         "carried: the far host's last roster still protects B and C, unreachable, and the hub's word about a "
                         "session started there since (D) stands as a via row (until this round the gossip was folded because "
                         "a dialable PEERS row existed, D was in no row, and a vouching hub let rule 5 presume it closed: the "
                         "regression round 2 found)")

    def test_a_hubs_word_about_a_directly_held_host_stands_while_it_is_down_or_carried_and_yields_when_it_speaks_again(self):
        """Round 3 of fork PR #897, the reviewer's ruling: never discard a heard source's word. The far host is heard
        directly, then the kernel holds its link down while the hub, up and heard, names a session started on it since:
        that sid must be named, by the hub's row, so the reader answers rule 4 while the hub vouches and never rule 5
        (a writer folding the gossip whatever the direct row's state left it in no row, and the hub, vouching for
        absence, let rule 5 presume it closed). The same with the direct row carried after a restart, the carried via
        row persisting like any carried row. The far host's exchange arriving with its link up is the event that ends
        the via row: dropped by the carry, the direct row speaks. The composition with the reader's verdicts is
        tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the hub's word phase)."""
        gossip = lambda *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        self._notify(FAR, up=True)
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C))
        pm._write_remote_sids()
        self.assertEqual(self._vouch(), {HUB: (True, True, True), FAR: (True, True, True)},
                         "both heard with their links up: the gossip folds, the direct row speaks")
        self._notify(FAR, up=False)                        # the kernel holds the far host's link down
        self.assertEqual(self._reach()[FAR], (True, False, True, False, [C]), "held down: unreachable, its last roster kept")
        self._peer(HUB, gossip(C, D))                      # the hub's next exchange: a session started on the far host since
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (True, False, True, False, [C]),
                                         VIA_FAR: (True, False, False, True, [C, D])},
                         "THE RULE: the direct row is held down, so it speaks for nothing new, and the hub's word stands beside "
                         "it as a via row naming the new session (D): the reader answers rule 4 for D by the hub's row (a "
                         "writer folding the gossip whatever the direct row's state, the display fold, leaves D in no row here, "
                         "and the hub vouching for absence lets rule 5 presume it closed; a writer adding the gossip to the "
                         "direct row credits the far host with a word it did not give, and D is then held down with it)")
        self.assertEqual(self._vouch()[VIA_FAR], (True, True, True), "the via row follows the hub's link: known up, heard")
        row = self._doc()["hosts"][VIA_FAR]
        self.assertEqual((row["kind"], row["via"], row["host"], row["viaBus"]), ("via", HUB, FAR, "far-bus"))
        self._notify(HUB, up=False)                        # the hub's link down too: its word follows it
        self.assertEqual((self._reach()[VIA_FAR], self._vouch()[VIA_FAR]),
                         ((True, False, True, False, [C, D]), (False, False, False)),
                         "a hub the kernel holds down carries no fresh word: the via row is link-down with it, roster kept")
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C, D))
        pm._write_remote_sids()
        self.assertEqual(self._vouch()[VIA_FAR], (True, True, True), "the hub heard again with its link up")
        # the same road with the direct row CARRIED: a restart from this state; the first poll's write carries every row
        self._restart()
        pm.PEERS.clear()
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, [A]), FAR: (False, False, False, False, [C]),
                                         VIA_FAR: (False, False, False, False, [C, D])},
                         "a carried via row persists heard=false like any carried row: the hub's last word about the far host "
                         "still names D (a carry that lets the CARRIED direct row speak drops it here, and D is in no row)")
        self._notify(FAR, up=True)                         # the kernel's seed: both links up, nothing heard yet
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C, D, E))                   # the hub heard first: a further session on the far host
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (False, False, False, False, [C]),
                                         VIA_FAR: (True, False, False, True, [C, D, E])},
                         "carried: the far host's last roster, not heard, still protects C; the hub's word names D and E (a "
                         "writer folding on the seeded PEERS row leaves them in no row while the hub vouches: rule 5, the "
                         "regression; a writer keying the via row by the far host's name overwrites the carried row and "
                         "loses C, the far host's own last word)")
        self.assertEqual(self._vouch()[FAR], (False, True, False), "the seed: linkUp and not heard, vouching for nothing")
        self._peer(FAR, [{"id": C, "name": "tests"}, {"id": D, "name": "api"}, {"id": E, "name": "api"}], bus_id="far-bus")
        pm._write_remote_sids()                            # the event: the far host's exchange arrives with its link up
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), FAR: (True, False, False, True, [C, D, E])},
                         "the direct row speaks again: the gossip folds and the via row is DROPPED by the carry (a writer that "
                         "carries it leaves the hub's older word naming D and E for the file's life, heard=false, and each "
                         "would be cannot-determine by that row once the far host no longer names it)")
        self._peer(HUB, gossip(C, D, E))                   # the hub's next exchange: folded, the direct row still speaks
        pm._write_remote_sids()
        self.assertEqual(sorted(self._reach()), sorted([HUB, FAR]), "no via row while the far host speaks for itself")

    def test_a_name_match_yields_to_a_known_different_bus_id(self):
        """Round 3 of fork PR #897, found by the reviewer's verifier by execution: the direct row under a name is heard
        with its link up and carries one bus id; a hub the kernel holds up gossips a session on a DIFFERENT machine it
        calls by the same name, stamping that machine's bus id. Until the eighth commit _direct_row_speaks matched by
        name OR by bus id, so the hub's word folded into a row that is another bus: the session was in no row, and the
        direct row and the hub, both vouching for absence, let rule 5 presume it closed for as long as the direct row
        was heard and not held down (not a one-interval window: no exchange of the direct row ever names a session on
        the other machine). The rule: both ids known and different, the row does not speak, and the hub's word stands
        as a via row beside it. A row with no bus id, or a gossip with no viaBus, still matches by name, and the hub's
        earlier word under the key is dropped when its current word folds. The composition with the reader's verdicts
        is tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the name collision step of the hub's word
        phase)."""
        X = "TESTHOST-x"
        via_x = VIA + HUB + "/" + X
        self._notify(X, up=True)
        self._peer(X, [{"id": C, "name": "tests"}], bus_id="bus-1")
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": E, "name": "api", "via": X, "viaBus": "bus-2"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [C]),
                                         via_x: (True, False, False, True, [E])},
                         "THE RULE: the row under the hub's name for the host carries bus-1 and the gossip stamps bus-2, so the "
                         "row is another bus and does not speak for a session started on the machine the hub means; the hub's "
                         "word stands as a via row beside it, and E is rule 4's by that row (a writer matching by name whatever "
                         "the ids folds it into the bus-1 row, E is in no row, and two vouching sources let rule 5 presume it "
                         "closed for as long as that row is heard and up)")
        self.assertEqual(self._vouch(), {HUB: (True, True, True), X: (True, True, True), via_x: (True, True, True)},
                         "both direct rows vouch for absence; the via row follows the hub's link")
        row = self._doc()["hosts"][via_x]
        self.assertEqual((row["kind"], row["via"], row["host"], row["viaBus"]), ("via", HUB, X, "bus-2"))
        # a gossip with no viaBus (a hub that predates the field) matches by name, and the hub's current word about the
        # host folding drops its earlier word under the same key (the hub knows one machine by that name)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": E, "name": "api", "via": X}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), X: (True, False, [C])},
                         "no viaBus: matched by name and folded; the via row of the hub's earlier word is dropped, not carried")
        # a row with no bus id (an exchange that carried none) matches by name too
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": E, "name": "api", "via": X, "viaBus": "bus-2"}])
        self._peer(X, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), X: (True, False, [C])},
                         "no busId on the row: matched by name and folded (a writer refusing every name match once a viaBus is "
                         "stamped writes a via row here)")

    def test_a_far_bus_restarted_under_a_hub_parts_the_ids_until_both_sides_hear_it_and_leaves_no_via_row_behind(self):
        """A bus id is minted per process (BUS_ID), so a far bus restart gives the direct row and the hub's gossip
        different ids until the first exchange with the restarted bus reaches each side, and by the rule above the row
        does not speak for that interval: the hub's word stands as a via row, the conservative side. Both orderings.
        The hub hears the restarted bus first: its gossip stamps the new id against our row's old one, the via row
        stands until our own exchange lands with the new id, then the gossip folds and the via row is dropped by the
        gate. We hear it first: our row carries the new id against the hub's last gossip's old one, the via row stands
        until the hub's exchange with the restarted bus, whose gossip then stamps the new id and folds; the via row of
        the hub's earlier word, stamped with the old id, is dropped because the hub's current word about that host
        folded at this write (`folded`): a carry keyed on the ids alone carries it heard=false for the file's life,
        since the old id never returns, and a session that then ends on the far host is cannot-determine by that
        row's last word where rule 5 is due (the linger the ruling's drop clause forbids, shown by execution on a
        scratch copy with the clause alone)."""
        gossip = lambda via_bus, *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": via_bus} for s in sids]
        roster = lambda *sids: [{"id": s, "name": "api"} for s in sids]
        self._notify(FAR, up=True)
        self._notify(HUB, up=True)
        self._peer(FAR, roster(C, D), bus_id="old")
        self._peer(HUB, gossip("old", C, D))
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]), "the same id on both sides: folded")
        # ordering one: the hub hears the restarted bus first
        self._peer(HUB, gossip("new", C, D))
        pm._write_remote_sids()
        self.assertEqual(self._reach().get(VIA_FAR), (True, False, False, True, [C, D]),
                         "the hub stamps the new id and our row still carries the old: by the ids another bus, so the hub's "
                         "word stands as a via row (a writer matching by name folds it, and there is no via row)")
        self.assertEqual(self._doc()["hosts"].get(VIA_FAR, {}).get("viaBus"), "new")
        self._peer(FAR, roster(C, D), bus_id="new")                  # our exchange with the restarted bus
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]), "the ids agree: folded, and the via row is dropped by the gate")
        # ordering two: we hear the restarted bus first (a second restart, a further id)
        self._peer(FAR, roster(C, D), bus_id="newer")
        pm._write_remote_sids()
        self.assertEqual((self._reach().get(VIA_FAR), self._doc()["hosts"].get(VIA_FAR, {}).get("viaBus")),
                         ((True, False, False, True, [C, D]), "new"),
                         "our row carries the newer id and the hub's last gossip the one before: the hub's word stands as a via "
                         "row, stamped with the id the hub knows")
        self._peer(HUB, gossip("newer", C, D))                       # the hub's exchange with the restarted bus
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]),
                         "the hub's current word about the far host folds, and its earlier word under the same key, stamped with "
                         "an id our row no longer carries, is DROPPED (a carry keyed on the ids alone carries it heard=false for "
                         "the file's life: the old id never returns)")
        self._peer(FAR, roster(C), bus_id="newer")                   # D ends on the far host
        self._peer(HUB, gossip("newer", C))
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), FAR: (True, False, [C])},
                         "D is in no row and both sources vouch: rule 5 is the reader's answer (a lingering via row would hold D "
                         "at cannot-determine by the hub's stale word)")
        # the hub not heard across the interval: the via row of its stale word is carried like any key, and dropped when
        # the hub is heard again with the new id
        self._peer(FAR, roster(C), bus_id="newest")
        pm._write_remote_sids()
        self.assertEqual(self._reach().get(VIA_FAR), (True, False, False, True, [C]), "a third restart heard here first: the via row again")
        self._restart()
        pm.PEERS.clear()
        self._notify(FAR, up=True)
        self._notify(HUB, up=True)
        self._peer(FAR, roster(C), bus_id="newest")
        pm._write_remote_sids()
        self.assertEqual(self._reach().get(VIA_FAR), (False, False, False, False, [C]),
                         "the hub not heard in this process: its stale word is carried, unreachable, like any carried row (the "
                         "ids do not agree and nothing of the hub's folded at this write)")
        self._peer(HUB, gossip("newest", C))
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]), "the hub heard with the new id: folded, the carried via row dropped")

    def test_the_direct_host_heard_again_before_the_hub_drops_the_carried_via_row(self):
        """The ruled event on its own (round 3 of fork PR #897, the reviewer's verifier: every earlier pin of the drop had
        the hub heard in the same process, so the hub's gossip folded and the folded-key drop removed the row before the
        carry's gate was reached, and a carry keyed on the folded key alone passed both changed modules). The hub's word
        stands beside a held-down far row; this bus restarts; the far host is heard with its link up BEFORE the hub is
        heard, or the hub never is: the carried via row is dropped at that write by the gate alone (_direct_row_speaks on
        the carried row's host and viaBus), and a session that ended on the far host across the restart is in no row
        while the far host vouches, rule 5 (a carry keyed on the folded key alone carries the via row heard=false until
        the hub's next exchange, for the file's life if the hub never returns, and that sid is cannot-determine by it).
        The far host's exchange heard while the kernel still holds its link down is not the event: the row stays until
        the link is up and the host heard since the drop (_link_down: both hold, here on the up notify's own write). The
        composition with the reader's verdicts is tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the gate
        alone phase)."""
        gossip = lambda *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        self._notify(FAR, up=True)
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C))
        pm._write_remote_sids()
        self._notify(FAR, up=False)                        # the kernel holds the far host's link down
        self._peer(HUB, gossip(C, D))                      # the hub's next exchange: a session started on the far host since
        pm._write_remote_sids()
        self.assertEqual(self._reach()[VIA_FAR], (True, False, False, True, [C, D]), "the hub's word beside the held-down row")
        self._restart()
        pm.PEERS.clear()
        pm._write_remote_sids()                            # the first poll's write: everything carried
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, [A]), FAR: (False, False, False, False, [C]),
                                         VIA_FAR: (False, False, False, False, [C, D])})
        self._notify(FAR, up=False)                        # the kernel's word: the far host's link is down...
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")   # ...and its dial to us lands anyway (D ended)
        pm._write_remote_sids()
        self.assertEqual(self._reach()[VIA_FAR], (False, False, False, False, [C, D]),
                         "the far host heard while the kernel holds its link down speaks for nothing new: the hub's word stays "
                         "carried (a gate on heard alone drops it here)")
        self._notify(FAR, up=True)                         # the link up, and the host heard since it dropped: THE EVENT (this write)
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, [A]), FAR: (True, False, False, True, [C])},
                         "THE RULE: the direct host is reachable again and the hub is NOT heard in this process, so nothing of "
                         "the hub's folded at this write and only the carry's gate can drop the carried via row: it is dropped, "
                         "and D, ended on the far host across the restart, is in no row while the far host vouches, rule 5 (a "
                         "carry keyed on the folded key alone carries the hub's older word heard=false until the hub's next "
                         "exchange, for the file's life if the hub never returns, and D is cannot-determine by that row)")
        self.assertEqual(self._vouch()[FAR], (True, True, True), "the far host vouches for absence: heard, its link known up")
        self._peer(FAR, [{"id": C, "name": "tests"}], bus_id="far-bus")   # a further exchange, the hub still silent
        pm._write_remote_sids()
        self.assertNotIn(VIA_FAR, self._rows(), "and it stays dropped: the hub's carried row alone brings nothing back")
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C))                         # the hub heard at last: its word folds, no via row
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, FAR]))

    def test_a_carried_hubs_word_about_a_far_host_stands_while_its_bus_is_heard_under_no_other_name(self):
        """The identity drop's negative, with the fixture every real bus presents (round 3 of fork PR #897, the reviewer's
        verifier: every carried-hub fixture until this pin had no bus id, while every bus stamps one, BUS_ID, so a carry
        reading a carried row's bus id ALONE as the hub heard under another name passed both changed modules). A hub, its
        bus id on its row, names two sessions on a far host nobody holds directly; another host X is heard beside it; this
        bus restarts; the kernel seeds both links up; X is heard with its link up BEFORE the hub. The hub's row is carried,
        bus id and all, and its word about the far host with it: C and D are named by the carried via row, so the reader
        answers cannot-determine for both while X vouches for absence (the carry above drops the via row at the restarted
        bus's first write, C and D are in no row, and X, vouching, lets rule 5 presume two live sessions closed on the word
        of a host that never gossiped them). The hub heard at last under the same name, naming C alone, is the event that
        settles D. The drop that IS ruled follows, after a second restart: the hub's dial landing here from the hostname it
        declares before ours folds it, the same bus id under ANOTHER name, and its old row and its via row leave together.
        The composition with the reader's verdicts is tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the two
        hubs phase)."""
        X = "TESTHOST-x"
        gossip = lambda *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(C, D), bus_id="hub-bus")
        self._notify(X, up=True)
        self._peer(X, [{"id": E, "name": "tests"}], bus_id="x-bus")
        pm._write_remote_sids()
        self.assertEqual(self._vouch(), {HUB: (True, True, True), X: (True, True, True), VIA_FAR: (True, True, True)},
                         "the hub and X heard with their links up; the hub's word about the far host follows the hub's link")
        self.assertEqual(self._doc()["hosts"][HUB].get("busId"), "hub-bus", "the hub's row carries its bus id, as every real bus's does")
        self._restart()
        pm.PEERS.clear()
        self._notify(HUB, up=True)                         # the kernel's seeds: both links up, nothing heard yet (each writes)
        self._notify(X, up=True)
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, [A]), X: (False, False, False, False, [E]),
                                         VIA_FAR: (False, False, False, False, [C, D])},
                         "THE RULE, at the restarted bus's first write: the hub is carried, its bus id on its row, and its word "
                         "about the far host with it (a carry reading a carried row's bus id alone as the hub heard under another "
                         "name drops the via row here, and C and D are in no row)")
        self.assertEqual(self._doc()["hosts"][HUB].get("busId"), "hub-bus", "the carried row keeps the bus id")
        self._peer(X, [{"id": E, "name": "tests"}], bus_id="x-bus")   # X heard with its link up: it vouches for absence
        pm._write_remote_sids()
        self.assertEqual(self._vouch().get(X), (True, True, True), "X vouches for absence: heard, its link known up")
        self.assertEqual(self._reach().get(VIA_FAR), (False, False, False, False, [C, D]),
                         "X vouching and the hub not heard: the hub's carried word still names C and D, so the reader answers "
                         "cannot-determine for both, named by an unreachable source (with the via row dropped they are in no row "
                         "while X vouches: rule 5 for two sessions live on the far host, on the word of a host that never gossiped "
                         "them)")
        self.assertEqual(self._reach().get(HUB), (False, False, False, False, [A]), "the hub's own row carried too, not heard")
        self._peer(HUB, gossip(C), bus_id="hub-bus")       # the hub heard at last, under its name: D ended on the far host
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [E]),
                                         VIA_FAR: (True, False, False, True, [C])},
                         "the event: the hub's current word names C alone, so D is in no row while the hub and X vouch, rule 5")
        # the drop that IS ruled: after a second restart the hub's own dial lands here from the hostname it declares, before
        # ours folds it under the alias, the same bus id under another name: its row under the old name and its via row leave
        self._local_listing_answered_empty()
        self._restart()
        pm.PEERS.clear()
        self._notify(HUB, up=True)
        self._notify(X, up=True)
        self.assertEqual(sorted(self._rows()), sorted([HUB, X, VIA_FAR]), "carried again, the via row among them")
        self._far_dials_us(HUB_DECL, gossip(C), "hub-bus")
        self.assertEqual(self._rows(), {X: (False, False, [E]), HUB_DECL: (True, False, [A]), VIA + HUB_DECL + "/" + FAR: (True, False, [C])},
                         "the same bus heard under ANOTHER name: the row under the old name is dropped and the hub's earlier word "
                         "under via:<old name>/<far> with it, by the same test, the bus id among the HEARD rows' (not its presence "
                         "on a carried row); the hub's current word stands under its new name")

    def test_a_hubs_current_word_about_a_far_bus_drops_its_own_earlier_word_alone_and_no_other_hubs(self):
        """The pair the carry drops a via row by is (hub, far bus id), not the far bus id alone (round 3 of fork PR #897,
        the reviewer's verifier: a carry dropping a carried via row on ANY heard hub's word about the far bus passed both
        changed modules, every fixture having one hub). Two hubs, each with its bus id, name sessions on a far host nobody
        holds directly; the first names two, the second, whose roster of the far host is older, one. This bus restarts;
        the second hub is heard again, naming its one, before the first is heard: the first hub's carried word still names
        the second session, so the reader answers cannot-determine for it (with that row dropped it is in no row while the
        second hub vouches: rule 5 for a session the second hub never heard of, on that hub's word). The first hub heard
        at last, naming one, is the event. The composition with the reader's verdicts is
        tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the two hubs phase)."""
        HUB2 = "TESTHOST-hub2"
        via2 = VIA + HUB2 + "/" + FAR
        gossip = lambda *sids: [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        self._notify(HUB, up=True)
        self._notify(HUB2, up=True)
        self._peer(HUB, gossip(C, D), bus_id="hub-bus")
        self._peer(HUB2, gossip(C), bus_id="hub2-bus")
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, []), HUB2: (True, False, False, True, []),
                                         VIA_FAR: (True, False, False, True, [C, D]), via2: (True, False, False, True, [C])},
                         "one via row per hub, each under its own key: two words about the far host, side by side")
        self._restart()
        pm.PEERS.clear()
        self._notify(HUB, up=True)                         # the kernel's seeds: both links up, nothing heard yet
        self._notify(HUB2, up=True)
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, []), HUB2: (False, False, False, False, []),
                                         VIA_FAR: (False, False, False, False, [C, D]), via2: (False, False, False, False, [C])},
                         "the first write after the restart: every row carried")
        self._peer(HUB2, gossip(C), bus_id="hub2-bus")     # the second hub heard again, naming C alone; the first hub not heard
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, []), HUB2: (True, False, False, True, []),
                                         VIA_FAR: (False, False, False, False, [C, D]), via2: (True, False, False, True, [C])},
                         "THE RULE: the second hub's current word names the far host's bus, and the pair the carry drops by is "
                         "(hub, bus id), so it supersedes the second hub's own earlier word alone: the FIRST hub's carried word "
                         "stands and still names D, cannot-determine for D by the reader (a carry dropping a carried via row on "
                         "any hub's current word about the far bus drops it here, D is in no row, and the second hub, vouching "
                         "for absence, lets rule 5 presume D closed on the word of a hub that never heard of it)")
        self.assertEqual(self._vouch().get(HUB2), (True, True, True), "the second hub vouches for absence: heard, its link known up")
        self._peer(HUB, gossip(C), bus_id="hub-bus")       # the first hub heard at last, naming C alone: D ended
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, []), HUB2: (True, False, False, True, []),
                                         VIA_FAR: (True, False, False, True, [C]), via2: (True, False, False, True, [C])},
                         "the event: the first hub's own current word supersedes its earlier one, and D is in no row while both "
                         "hubs vouch, rule 5")

    def test_a_hubs_word_follows_the_hub_to_the_alias_and_its_earlier_word_under_the_declared_name_is_dropped(self):
        """The first name axis of a via key (round 3 of fork PR #897, the reviewer's verifier, by execution through the
        real inbound handler and the real fold). A hub dials us first, under the hostname it declares (peer_exchange_handle
        files it there: no dialable row carries its busId yet), gossiping two sessions on a far host nobody holds directly;
        one ends; our own dial lands under the alias the kernel dials (peer_exchange_apply: the busId fold drops the
        declared row from PEER_STATE). The hub's current word is written under via:<alias>/<far>, and the row under
        via:<declared>/<far>, carried by key alone, named the ended session heard=false for the file's life,
        cannot-determine where rule 5 is due (at the sixth commit the via row was keyed by the far name alone, so the
        hub's rename did not duplicate it: the seventh commit's key opened this axis). The rule: a carried via row whose
        hub's bus this process heard under another name is dropped with the hub's own stale row, by the same test (its
        busId among the heard rows'), whatever the hub now says about the far host: a hub in the same process gossiping
        nothing about a host it gossiped before reports no sessions there (a hub heard under the SAME name and silent
        leaves its via row carried: the standing pin above, its silence being a restarted hub's). The composition with the
        reader's verdicts is tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the hub's two names phase)."""
        self._local_listing_answered_empty()
        gossip = lambda *sids: [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        via_decl = VIA + HUB_DECL + "/" + FAR
        self._notify(HUB, up=True)                         # the kernel dials the alias; the hub's own dial lands here first
        self._far_dials_us(HUB_DECL, gossip(C, D), "hub-bus")
        self.assertEqual(self._reach(), {HUB_DECL: (True, False, False, True, []), via_decl: (True, False, False, True, [C, D])},
                         "the hub under the name it declared, and its word about the far host under that name")
        self.assertEqual(self._vouch()[via_decl], (True, False, False), "the via row follows the hub's link: none under the declared name")
        pm.peer_exchange_apply(HUB, {}, {"presence": gossip(C), "epoch": 1, "holds": [], "busId": "hub-bus", "presenceAnswered": True})   # our dial lands: D ended
        self.assertEqual(sorted(pm.PEER_STATE), [HUB], "the fold: the declared row left PEER_STATE")
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, []), VIA_FAR: (True, False, False, True, [C])},
                         "THE RULE: the hub's bus is heard under the alias, so its row under the declared name is dropped (the "
                         "busId fold) AND its word under via:<declared>/<far> with it, by the same test; its current word stands "
                         "under via:<alias>/<far> and names C alone, so D, ended on the far host, is in no row while the hub "
                         "vouches: rule 5 (a carry keyed on the via key alone carries the declared name's row heard=false for the "
                         "file's life, and D is cannot-determine by it)")
        self.assertEqual(self._vouch()[VIA_FAR], (True, True, True), "the via row now follows the alias's link: known up")
        pm.peer_exchange_apply(HUB, {}, {"presence": gossip(C), "epoch": 1, "holds": [], "busId": "hub-bus", "presenceAnswered": True})
        self.assertEqual(sorted(self._rows()), sorted([HUB, VIA_FAR]), "and it stays dropped at the hub's next exchange")
        # the same fold with the hub now gossiping NOTHING about the far host: the same bus, its silence under its new name
        # its word (no sessions there), so the declared name's row leaves with the hub's own
        self._restart()
        pm.PEERS.clear()
        self.path.unlink()
        self._notify(HUB, up=True)
        self._far_dials_us(HUB_DECL, gossip(C, D), "hub-bus")
        self.assertEqual(sorted(self._rows()), sorted([HUB_DECL, via_decl]))
        pm.peer_exchange_apply(HUB, {}, {"presence": [], "epoch": 1, "holds": [], "busId": "hub-bus", "presenceAnswered": True})
        self.assertEqual(self._rows(), {HUB: (True, False, [])},
                         "the hub's bus heard under another name: its earlier word under the declared name is dropped whatever it "
                         "now says about the far host (a carry that keeps it while the hub is silent names C and D for the file's "
                         "life; the SAME name silent is the standing pin's carry, a restarted hub that has not heard the host yet)")

    def test_a_hubs_word_follows_its_own_name_for_the_far_host_and_its_earlier_word_under_the_old_name_is_dropped(self):
        """The second name axis of a via key (round 3 of fork PR #897, the reviewer's verifier, by execution): the hub's
        own fold of the far host, from the hostname the far bus declared to it under the alias the hub dials, changes the
        `via` label the hub stamps while the viaBus stays. The hub's current word is written under via:<hub>/<alias>, and
        the row under via:<hub>/<declared>, carried by key alone, named a session that ended across the rename heard=false
        for the file's life (the same at the sixth commit, whose via rows were keyed by the far name: the class is older
        than the key). The rule: a carried via row whose (hub, viaBus) pair the hub's current gossip names under another
        far name is dropped; the same when that gossip FOLDS into the far host's own row, heard here under the new name
        with no bus id on its row (a name match), where the carry's gate reaches no row by the old name."""
        gossip = lambda far, *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": far, "viaBus": "far-bus"} for s in sids]
        via_decl = VIA + HUB + "/" + FAR_DECL
        self._notify(HUB, up=True)
        self._peer(HUB, gossip(FAR_DECL, C, D))
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), via_decl: (True, False, False, True, [C, D])},
                         "the hub's word about the far host under the name the far bus declared to it")
        self._peer(HUB, gossip(FAR, C))                    # the hub's own dial folded the far bus under the alias it dials; D ended
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), VIA_FAR: (True, False, False, True, [C])},
                         "THE RULE: the hub's current word names the far host's bus (viaBus) under another name, so its earlier "
                         "word under via:<hub>/<declared> is dropped, and D, ended across the rename, is in no row while the hub "
                         "vouches: rule 5 (a carry keyed on the via key alone carries the old name's row heard=false for the "
                         "file's life, and D is cannot-determine by it)")
        # the rename while the far host is heard here under the new name with NO bus id on its row: the gossip folds by
        # name, and the pair still drops the old name's row
        self._peer(HUB, gossip(FAR_DECL, C, D))
        pm._write_remote_sids()
        self.assertEqual(sorted(self._rows()), sorted([HUB, via_decl]), "the old name again (a further session, D)")
        self._notify(FAR, up=True)
        self._peer(FAR, [{"id": C, "name": "tests"}])      # heard directly, no bus id on the row
        self._peer(HUB, gossip(FAR, C))
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HUB: (True, False, [A]), FAR: (True, False, [C])},
                         "folded by name into the far host's own row, and the old name's via row dropped by the pair (the gate "
                         "reaches no row by the old name, and the folded key is the new name's)")

    def test_a_peer_state_row_no_exchange_produced_is_not_a_source(self):
        pm.PEER_STATE[HOST] = {"drift": "proto"}       # the setdefault shape a refusal or drift note leaves
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {}, "no seenAt: nothing was heard from it")

    def test_a_restart_carries_every_host_it_has_not_heard_as_unreachable_and_releases_each_on_its_event(self):
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}])
        self._peer(HUB, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HOST: (True, False, [B]), HUB: (True, False, [C])})
        self._restart()
        pm._write_remote_sids()                        # the first poll's write, before any beat or exchange
        self.assertEqual(self._rows(), {HB + A: (False, False, [A]), HOST: (False, False, [B]), HUB: (False, False, [C])},
                         "a restarted bus writes a first mirror whose hosts are all unreachable, rosters kept (the "
                         "shape until 2026-09-22 wrote an empty list, the first road of fork PR #897's round 1)")
        self._peer(HOST, [{"id": D, "name": "api"}])   # one exchange lands: that host, and only that host, is heard
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (False, False, [A]), HOST: (True, False, [D]), HUB: (False, False, [C])},
                         "per host: the heard host's fresh roster; the others still carried")
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HUB, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HOST: (True, False, [D]), HUB: (True, False, [C])})

    def test_the_kernels_seed_of_a_carried_hosts_link_up_at_a_restart_vouches_for_nothing_until_the_host_is_heard(self):
        """The primary restart road (round 2 of fork PR #897, a verifier's finding at the fifth commit: a writer computing
        vouchesAbsence from the link alone, heard dropped, survived every pin of the five modules and reopened the first
        road of round 1 by execution). A restarted bus starts with an empty peer table, and the kernel seeds it from
        /tunnels (_seed_peers_from_kernel) or re-notifies every tunnel up on its next supervisor pass, through peer_update,
        BEFORE any exchange arrives: a host carried from the previous file, not heard by this process, has PEERS up and no
        mark, so linkUp is True. Its roster is the previous process's last word, not this one's, and the row vouches for
        nothing: unreachable (not heard), and not vouching for absence, so a sid it does not name stays unsettled (a writer
        vouching for absence by the link alone says True here, and a session started on that host since the previous file
        is presumed closed on the restarted bus's first write). The host's exchange is the event: heard with the link up,
        both flags. The composition with the reader's verdicts is tests/test_dead_session_staleness.py
        ReaderFollowsTheWriter (the seeded phase)."""
        self._peer(HOST, [{"id": B, "name": "api"}])
        self._peer(HUB, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self._restart()
        pm.PEERS.clear()                                    # a fresh process: the link table empty until the seed
        self._notify(HOST, up=True)                         # the seed (or the re-notify): PEERS up, nothing heard, no mark
        self.assertEqual(self._reach()[HOST], (False, False, False, False, [B]),
                         "carried from the previous file and not heard: unreachable, its roster kept, the link neither down "
                         "nor marked")
        self.assertEqual(self._vouch()[HOST], (False, True, False),
                         "THE SEED: the kernel holds the link up (linkUp) and this process has heard nothing over it, so the row "
                         "vouches for neither presence nor absence (a writer vouching for absence by the link alone says "
                         "(False, True, True) here, and a sid started on that host since the previous file would be rule 5's)")
        self.assertEqual(self._vouch()[HUB], (False, False, False), "the host the seed did not name: not heard, no link state")
        self._peer(HOST, [{"id": D, "name": "api"}])        # the event: the host's exchange arrives with the link up
        pm._write_remote_sids()
        self.assertEqual((self._reach()[HOST], self._vouch()[HOST]), ((True, False, False, True, [D]), (True, True, True)),
                         "heard with the link up: reachable and vouching for absence, on this exchange and nothing else")
        self.assertEqual(self._vouch()[HUB], (False, False, False), "the other carried host still waits for its own event")

    def test_a_carried_row_for_a_bus_heard_under_its_other_name_is_dropped(self):
        self._peer("TESTHOST-selfname", [{"id": A, "name": "web"}], bus_id="bus-1")
        pm._write_remote_sids()
        self._restart()
        self._peer(HOST, [{"id": A, "name": "web"}], bus_id="bus-1")     # the same bus, under its dialable alias
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HOST: (True, False, [A])},
                         "one row per bus: the stale name's carried row is the same bus (busId), heard under its alias")

    def test_a_whitespace_list_is_carried_as_the_legacy_source_until_heard_sources_name_its_sids(self):
        self.path.write_text(A + "\n" + B + "\n")     # what a bus before 2026-09-22 wrote: live remote sids then
        pm.HEARTBEATS[A] = ("web", self.now)
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), LEGACY: (False, False, [B])},
                         "the old list's sids this process has not heard are carried, unreachable; the one it heard "
                         "is its own source now")
        self.assertEqual(self._answered()[LEGACY], False,
                         "the legacy list's bit: no listing this process can speak for answered for it (a bool, so the "
                         "reader's shape check passes the row; never heard, so it vouches for nothing either way)")
        pm.HEARTBEATS[B] = ("api", self.now)
        pm._write_remote_sids()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HB + B: (True, False, [B])},
                         "every sid heard: the legacy source is gone")

    def _mark(self):
        """The document's lost-carry mark, {"cause", "at"}, or None when the document carries none (round 3 of fork PR #897,
        the reviewer's ruling of 14:57Z, the twenty-second commit)."""
        return self._doc().get("carryLost")

    def _own_document(self):
        """The bus's own document naming B on HOST and C on HUB, both heard and vouching, as a previous process wrote it."""
        row = lambda sids: {"kind": "peer", "sids": sids, "heard": True, "expired": False, "linkDown": False, "linkUp": True,
                            "answered": True, "reachable": True, "vouchesAbsence": True, "seenAt": 1}
        return json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "hosts": {HOST: row([B]), HUB: row([C])}},
                          sort_keys=True) + "\n"

    def _write_saying(self):
        """One write through the real writer; returns the bus log lines it said."""
        pm._REMOTE_SIDS_SAID.clear()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            pm._write_remote_sids()
        return err.getvalue().splitlines()

    def _seed(self, links, known=()):
        """The kernel's tunnel list read at the bus's start, through the REAL seed (_seed_peers_from_kernel) with its transport
        stubbed: `links` is [(host, status)], and `known` the kernel's remembered unattached hosts, each of which the seed
        applies as an ORIGIN-ONLY row (a tier, no port: no link). The seed applies each row through peer_update, which writes
        the mirror for a link, and then sets _PEERS_SEEDED, which this returns for the caller to assert after its own
        verdicts; the transport is put back as found."""
        body = json.dumps({"tunnels": [{"host": h, "busPort": 50002, "status": st} for h, st in links],
                           "known": [{"host": h, "trust": "trusted"} for h in known]}).encode()

        class Answer:
            def read(self):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False
        real = pm.urllib.request.urlopen
        pm.urllib.request.urlopen = lambda req, timeout=None: Answer()
        try:
            pm._seed_peers_from_kernel()
        finally:
            pm.urllib.request.urlopen = real
        return pm._PEERS_SEEDED[0]

    def _heard_now(self, host, sids):
        """An exchange from `host` landing now, after every write before this call (seenAt is the recorders' own stamp,
        int(time.time()) at the exchange), then the write it makes."""
        self._peer(host, [{"id": s, "name": "api"} for s in sids])
        pm.PEER_STATE[host]["seenAt"] = int(pm.time.time())
        pm._write_remote_sids()

    def test_a_file_of_neither_shape_carries_nothing_and_marks_the_document(self):
        for text in ("[1, 2]\n", '{"hosts": 3}\n', "\x00\x01\n"):
            with self.subTest(text=text):
                self.path.write_text(text)
                pm.HEARTBEATS[A] = ("web", self.now)
                pm._write_remote_sids()
                self.assertEqual(self._rows(), {HB + A: (True, False, [A])}, "rewritten as a document from memory alone")
                self.assertIsNotNone(self._mark(), "the rows it may have held are lost: the document is marked (round 3 of fork "
                                     "PR #897, the reviewer's ruling of 14:57Z; until the twenty-second commit it carried no mark)")
        self.path.write_text('{"hosts": {"TESTHOST": "x"}}\n')
        pm._write_remote_sids()
        self.assertEqual((self._rows(), self._mark()), ({HB + A: (True, False, [A])}, None),
                         "a document whose one row is not a roster row: the row is dropped and counted, the document read, "
                         "so no mark")

    def test_a_file_whose_bytes_are_not_utf8_and_no_document_carries_nothing_marks_the_document_and_the_write_replaces_it(self):
        """Round 3 of fork PR #897, the reviewer's ruling on its refuters' corrections, the twentieth commit, and its ruling of
        14:57Z, the twenty-second commit: bytes that are not UTF-8 are decoded with replacement for the JSON parse alone, so
        garbage that is no document at v 2 after it is a file this read cannot read whole: no row carried, the document
        marked, the write replacing the file. Until the twentieth commit the decode's UnicodeDecodeError passed the read's
        OSError catch and failed every write, the file never replaced. The whitespace list keeps the strict decode, so the
        garbage's safe-id-shaped runs (IHDR and tEXt here) never reach its parser (a replacing decode handed to it carries
        them as a legacy row)."""
        garbage = b"\x89PNG\r\n\x1a\n\xff\xd8 IHDR tEXt\n"
        self.path.write_bytes(garbage)
        pm.HEARTBEATS[A] = ("web", self.now)
        lines = self._write_saying()
        self.assertNotEqual(self.path.read_bytes(), garbage,
                            "the write replaced the file (a read whose decode error passes its catch fails every write: %r)" % lines)
        self.assertEqual(self._rows(), {HB + A: (True, False, [A])},
                         "rewritten from memory alone: the garbage carries nothing (a replacing decode handed to the whitespace "
                         "parser carries its safe-id-shaped runs as a legacy row)")
        self.assertIn("UnicodeDecodeError", (self._mark() or {}).get("cause", ""), "the document marked with the cause")
        self.assertEqual([ln for ln in lines if "not written" in ln], [], "no write failure said: %r" % lines)
        said = [ln for ln in lines if "is unreadable" in ln]
        self.assertEqual(len(said), 1, "the discarded file is said once in the bus log: %r" % lines)
        self.assertIn("UnicodeDecodeError", said[0], "the line says what failed")

    def test_one_bad_byte_costs_one_sid_never_the_document(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 14:57Z, clause 1 (the twenty-second commit): the previous-read
        decodes the bus's own document with replacement for its JSON parse, validates every sid, drops the one a stray byte
        made fail the session-id shape, carries every other row, and says once in the bus log which file and how many. Until
        the commit the read was strict and the file carried nothing: HUB's row, which no bad byte touched, was lost with
        HOST's, and a session HUB named was presumed closed by rule 5 once another host vouched (the reviewer's verifier, by
        execution; the verdicts are tests/test_dead_session_staleness.py ReaderFollowsTheWriter's one-byte phase). A stray
        byte inside the key `sids` of a row costs that row alone; one inside a host's key keeps the row under the key as
        read, its sid still named. No mark: the document was read."""
        doc = self._own_document().encode()
        for name, data, rows, sids_dropped, rows_dropped in (
                ("inside the sid HOST names", doc.replace(B.encode(), B[:-1].encode() + b"\xff"),
                 {HB + A: (True, False, [A]), HOST: (False, False, []), HUB: (False, False, [C])}, 1, 0),
                ("inside the key sids of HOST's row", doc.replace(b'"sids"', b'"sid\xff"', 1),
                 {HB + A: (True, False, [A]), HUB: (False, False, [C])}, 0, 1),
                ("inside HUB's key", doc.replace(HUB.encode(), HUB[:-1].encode() + b"\xff"),
                 {HB + A: (True, False, [A]), HOST: (False, False, [B]), HUB[:-1] + "\ufffd": (False, False, [C])}, 0, 0)):
            with self.subTest(byte=name):
                self.path.write_bytes(data)
                pm.HEARTBEATS.clear()
                pm.HEARTBEATS[A] = ("web", self.now)
                lines = self._write_saying()
                self.assertEqual(self._rows(), rows, "every row the byte did not break is carried (a strict read carries none)")
                self.assertIsNone(self._mark(), "the document was read: no mark")
                said = [ln for ln in lines if "previous remote-sids mirror" in ln]
                self.assertEqual(len(said), 1, "said once: %r" % lines)
                self.assertIn(str(self.path), said[0], "the line names the file")
                self.assertIn("%d session id(s) not in the session-id shape and %d row(s)" % (sids_dropped, rows_dropped),
                              said[0], "the line says how many")
                self.assertIn("UnicodeDecodeError", said[0], "the line says the bytes were not UTF-8")
                self.assertEqual([ln for ln in lines if "not written" in ln or "is unreadable" in ln], [],
                                 "no write failure and no whole-file line")

    def test_a_byte_order_mark_is_read_and_its_file_carried(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 14:57Z, clause 1 (the twenty-second commit): a byte-order mark is
        accepted (utf-8-sig) in the previous-read, before the bus's document and before the whitespace list alike, and
        nothing is said. Until the commit the mark made the file unreadable, so it carried nothing."""
        for name, data, rows in (("the bus's own document", b"\xef\xbb\xbf" + self._own_document().encode(),
                                  {HB + A: (True, False, [A]), HOST: (False, False, [B]), HUB: (False, False, [C])}),
                                 ("the whitespace list", b"\xef\xbb\xbf" + (B + "\n").encode(),
                                  {HB + A: (True, False, [A]), LEGACY: (False, False, [B])})):
            with self.subTest(file=name):
                self.path.write_bytes(data)
                pm.HEARTBEATS.clear()
                pm.HEARTBEATS[A] = ("web", self.now)
                lines = self._write_saying()
                self.assertEqual(self._rows(), rows, "read behind the mark and carried (a read refusing the mark carries nothing)")
                self.assertIsNone(self._mark(), "no mark")
                self.assertEqual(lines, [], "nothing said")

    def test_a_file_this_read_cannot_read_whole_carries_no_row_marks_the_document_and_is_said_once(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 14:57Z, clause 2 (the twenty-second commit): a previous file the
        previous-read cannot read whole carries no row, and the write stamps the new document with the lost-carry mark,
        {"cause", "at"}, the cause and the second of the write, and says so once in the bus log naming the file, so the judge
        answers cannot-determine where rule 5 would fire (the verdicts: tests/test_dead_session_staleness.py). Until the
        commit such a file carried nothing, the document carried no mark, and the judge answered rule 5 for a session a lost
        row named. The whitespace list keeps the strict decode, so the list with one byte that is not UTF-8 is such a file
        (a replacing decode handed to its parser carries B as a legacy row); a text that opens with a brace is a document,
        never the list, so the document cut short after `true` is never read as naming the session "true"; an empty file,
        which no bus since 2026-09-22 writes and a crash can leave, is one too. A path the bus cannot open is read directly
        (a directory there: the write's replace would fail too)."""
        doc = self._own_document()
        v1 = doc.replace('"v": 2', '"v": 1')
        files = (("text that is not JSON, a stray brace", doc.replace('"sids"', '"sids"}', 1).encode(), "JSONDecodeError"),
                 ("the document cut short after a literal the whitespace parser would take for a session id",
                  doc[:doc.index("true") + 4].encode(), "JSONDecodeError"),
                 ("nesting past the parser's depth", ("[" * 100000 + "\n").encode(), None),   # None: derived from the parse
                 ("a JSON list", b"[1, 2]\n", "a JSON list, not a document with a hosts table"),
                 ("a JSON object whose hosts are a list", b'{"v": 2, "hosts": []}\n', "a JSON dict, not a document"),
                 ("a text naming no session id", b"??? !!!\n", "JSONDecodeError"),
                 ("an empty file", b"", "an empty file"),
                 ("bytes that are not UTF-8 in no document", b"\x89PNG\r\n\x1a\n\xff\xd8 IHDR tEXt\n", "UnicodeDecodeError"),
                 ("bytes that are not UTF-8 in a document at v 1", v1.encode().replace(B.encode(), B[:-1].encode() + b"\xff"),
                  "not a document at v 2 after the replacing decode"),
                 ("the whitespace list with one byte that is not UTF-8", (B + "\n" + C[:-1]).encode() + b"\xff\n",
                  "UnicodeDecodeError"))
        for name, data, error in files:
            with self.subTest(file=name):
                if error is None:                  # the nested document: the class this interpreter's parse of these bytes raises
                    error, depth = _nested_parse_raises(data)
                    self.assertTrue(_names_an_exception_class(error), "json.loads returned on the document nested %d deep "
                                    "on %s (derived %r, not the name of an exception class in builtins or json): the case's "
                                    "premise, a file the parse cannot read, is gone" % (depth, sys.version, error))
                    error = "(%s: " % error        # the class in the slot the product fills from the exception it caught
                self.path.write_bytes(data)
                pm.HEARTBEATS.clear()
                pm.HEARTBEATS[A] = ("web", self.now)
                before = int(pm.time.time())
                lines = self._write_saying()
                after = int(pm.time.time())
                self.assertEqual(self._rows(), {HB + A: (True, False, [A])}, "the write lands from memory: no row carried")
                mark = self._mark()
                self.assertIsNotNone(mark, "the document is marked (until the twenty-second commit it carried no mark)")
                self.assertEqual(sorted(mark), ["at", "cause"], "the mark's shape")
                self.assertTrue(before <= mark["at"] <= after, "stamped with the write's second: %r" % mark)
                self.assertTrue(mark["cause"].startswith("previous mirror unreadable ("), "the cause: %r" % mark)
                self.assertIn(error, mark["cause"], "the cause says what failed")
                said = [ln for ln in lines if "previous remote-sids mirror" in ln]
                self.assertEqual(len(said), 1, "said once in the bus log: %r" % lines)
                self.assertIn(str(self.path), said[0], "the line names the file")
                self.assertIn(error, said[0], "the line says what failed")
                self.assertIn("marks the mirror", said[0], "the line says the consequence")
                self.assertEqual([ln for ln in lines if "not written" in ln], [], "and no write failure")
        with self.subTest(file="a path the bus cannot open"):
            self.path.unlink(missing_ok=True)
            self.path.mkdir()
            self.addCleanup(self.path.rmdir)
            pm._REMOTE_SIDS_SAID.clear()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                got, mark = pm._remote_sids_previous(self.path, self.now)
            self.assertEqual(got, {}, "carries nothing")
            self.assertIsNotNone(mark, "marked (until the twenty-second commit such a path carried nothing and marked nothing)")
            self.assertEqual((mark["at"], "IsADirectoryError" in mark["cause"]), (int(self.now), True), "marked: %r" % mark)
            said = [ln for ln in err.getvalue().splitlines() if "previous remote-sids mirror" in ln]
            self.assertEqual(len(said), 1, "said once: %r" % err.getvalue())
            self.assertIn("IsADirectoryError", said[0], "the line says what failed")

    def test_no_file_and_a_readable_one_say_nothing_and_an_unreadable_one_is_said_once_per_text(self):
        """No false alarm: no file (the first write under a root), the list shape naming a session, and the bus's own document
        say nothing and mark nothing. And the whole-file line is said once per distinct text, as the write-failure line is:
        the same unreadable file planted again says nothing more. (An empty file, which the twenty-first commit held silent as
        the empty list of the shape until 2026-09-22, is marked since the twenty-second: a crash can leave one, and this read
        cannot tell the two apart.)"""
        pm.HEARTBEATS[A] = ("web", self.now)
        for name, plant in (("no file", lambda: self.path.unlink(missing_ok=True)),
                            ("the list shape naming a session", lambda: self.path.write_text(B + "\n")),
                            ("the bus's own document", lambda: None)):        # the previous subtest's write left one
            with self.subTest(file=name):
                plant()
                self.assertEqual(self._write_saying(), [], "nothing said")
                self.assertIn(HB + A, self._rows(), "the write landed")
                self.assertIsNone(self._mark(), "nothing marked")
        pm._REMOTE_SIDS_SAID.clear()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for _ in range(2):
                self.path.write_bytes(b"\xff\xfe\n")
                pm._write_remote_sids()
        said = [ln for ln in err.getvalue().splitlines() if "previous remote-sids mirror" in ln]
        self.assertEqual(len(said), 1, "the same file twice: said once (%r)" % said)

    def test_a_file_nested_past_the_parsers_depth_carries_nothing_marks_the_document_and_the_write_replaces_it(self):
        """Round 3 of fork PR #897, the twentieth commit, found by its builder in the class of the bytes: a document nested past
        the JSON parser's depth raised RecursionError on this box, which is not a ValueError, so the previous-read's parse let it
        pass and every write failed, the file never replaced. The parse catches it, the write rewrites the file from memory, and
        since the twenty-second commit the document is marked, the rows it may have held being lost. The class in the cause is
        the one this interpreter's parse of the same bytes raises (_nested_parse_raises; the reviewer's ruling of 17:47Z, the
        twenty-fifth commit), a class name, in the cause's "(<class>: " slot (the twenty-sixth), the name of an exception class
        (_names_an_exception_class, the twenty-seventh)."""
        deep = "[" * 100000 + "\n"
        self.path.write_text(deep)
        raised, depth = _nested_parse_raises(self.path.read_bytes())
        self.assertTrue(_names_an_exception_class(raised), "json.loads returned on the document nested %d deep on %s (derived "
                        "%r, not the name of an exception class in builtins or json): the case's premise, a file the parse "
                        "cannot read, is gone" % (depth, sys.version, raised))
        pm.HEARTBEATS[A] = ("web", self.now)
        lines = self._write_saying()
        self.assertNotEqual(self.path.read_text(), deep,
                            "the write replaced the file (a parse catching ValueError alone fails every write: %r)" % lines)
        self.assertEqual(self._rows(), {HB + A: (True, False, [A])}, "rewritten from memory alone: the nesting carries nothing")
        self.assertIn("(%s: " % raised, (self._mark() or {}).get("cause", ""), "marked with the cause, the class this "
                      "interpreter's parse raised")

    def test_the_lost_carry_mark_is_carried_until_every_linked_host_is_heard_since_it_and_then_cleared(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 14:57Z, clause 2 (the twenty-second commit): the mark is carried by
        every write, and across a restart, until the bus process that read the kernel's list of links at its start has heard
        every host that list put in PEERS since the mark (_remote_sids_lost_cleared). A restarted bus seeds both links up
        through the real seed, whose own writes read the unreadable file and mark the document; HOST heard while HUB, linked,
        is not: the mark stands (a clearing on one host heard drops it here, and HUB's lost rows with it); a further restart
        carries it, the same cause and second; HOST and then HUB heard: cleared, said once, and no later write brings it back."""
        self.path.write_text("{not json\n")
        seeded = self._seed([(HOST, "up"), (HUB, "up")])   # the seed's own writes read the file: the mark
        mark = self._mark()
        self.assertIsNotNone(mark, "the seed's first write read the unreadable file and marked the document")
        self.assertTrue(seeded, "the seed read the kernel's list")
        self._heard_now(HOST, [B])
        self.assertEqual(self._mark(), mark, "HOST heard, HUB linked and not heard since the mark: the mark stands")
        self._restart()
        pm.PEERS.clear()
        self.assertTrue(self._seed([(HOST, "up"), (HUB, "up")]), "the restarted bus's seed read the list")
        self.assertEqual(self._mark(), mark, "carried across a restart: the same cause and second")
        self._heard_now(HOST, [B])
        self.assertEqual(self._mark(), mark, "HOST heard in the new process, HUB not: the mark stands")
        pm._REMOTE_SIDS_SAID.clear()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self._heard_now(HUB, [C])
        self.assertIsNone(self._mark(), "every linked host heard since the mark: cleared")
        cleared = [ln for ln in err.getvalue().splitlines() if "lost-carry mark" in ln]
        self.assertEqual(len(cleared), 1, "said once: %r" % err.getvalue())
        self.assertIn(pm.time.strftime("%Y-%m-%dT%H:%M:%SZ", pm.time.gmtime(mark["at"])), cleared[0], "naming the mark's second")
        self.assertIn("cleared", cleared[0])
        pm._write_remote_sids()
        self.assertEqual((self._mark(), self._rows()), (None, {HOST: (True, False, [B]), HUB: (True, False, [C])}),
                         "a later write carries no mark")

    def test_a_linked_host_that_stays_down_keeps_the_mark(self):
        """Round 3 of fork PR #897, the reviewer's ruling of 14:57Z (the twenty-second commit): a host the kernel holds DOWN is
        never heard, so it keeps the mark for as long as it stays down: cannot-determine, never a false rule 5. The up notify
        alone is no hearing; HUB's exchange after it is the event."""
        self.path.write_text("{not json\n")
        seeded = self._seed([(HOST, "up"), (HUB, "down")])
        mark = self._mark()
        self.assertIsNotNone(mark, "the seed's first write marked the document")
        self.assertTrue(seeded, "the seed read the kernel's list")
        self._heard_now(HOST, [B])
        pm._write_remote_sids()
        self.assertEqual(self._mark(), mark, "HUB down and never heard: the mark stands")
        self._notify(HUB, up=True)
        self.assertEqual(self._mark(), mark, "the up notify alone hears nothing: the mark stands")
        self._heard_now(HUB, [C])
        self.assertIsNone(self._mark(), "HUB heard: every linked host heard since the mark, cleared")

    def test_the_mark_clears_only_in_a_bus_that_read_the_kernels_list_of_links_and_holds_a_link(self):
        """Round 3 of fork PR #897, the twenty-second commit: PEERS in a restarted bus is the kernel's whole list only once the
        seed has read it. When the seed fails (no kernel answering at the bus's start: the real seed, its route pointed at a
        loopback port nothing listens on), PEERS fills one host per notify as the kernel re-tells them, so every host it
        holds heard does not mean every host the kernel links to heard: the mark stands for this process's life (a clearing
        without the seed drops it here, over the lost rows of a host the kernel has not re-told yet). And a seeded bus whose
        table holds no dialable link clears nothing (a vacuous clear would drop the mark before the first link is told):
        HOST notified and heard after it is the event."""
        with self.subTest(seed="failed"):
            self.path.write_text("{not json\n")
            base = pm.KERNEL_BASE
            pm.KERNEL_BASE = "http://127.0.0.1:9"
            self.addCleanup(setattr, pm, "KERNEL_BASE", base)
            pm._seed_peers_from_kernel()
            pm.KERNEL_BASE = base
            self._notify(HOST, up=True)                  # the kernel's re-notify, one host at a time
            mark = self._mark()
            self.assertIsNotNone(mark, "the notify's write marked the document")
            self.assertFalse(pm._PEERS_SEEDED[0], "the seed did not read the list")
            self._heard_now(HOST, [B])
            pm._write_remote_sids()
            self.assertEqual(self._mark(), mark, "every host PEERS holds heard, the list never read: the mark stands")
        self._restart()
        pm.PEERS.clear()
        self.path.unlink()
        with self.subTest(seed="read, no link"):
            self.path.write_text("{not json\n")
            seeded = self._seed([])                      # the kernel's list, empty: no notify, so no write yet
            pm._write_remote_sids()
            mark = self._mark()
            self.assertIsNotNone(mark, "the write marked the document")
            self.assertTrue(seeded, "the seed read the kernel's list")
            pm._write_remote_sids()
            self.assertEqual(self._mark(), mark, "no dialable link: the mark stands")
            self._notify(HOST, up=True)
            self._heard_now(HOST, [B])
            self.assertIsNone(self._mark(), "the one link heard since the mark: cleared")

    def test_a_host_counts_toward_the_clearing_only_when_it_has_been_heard(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the twenty-second commit, by execution: a mark whose second is 0
        (the carry accepts it as written, and so does the judge's reader) cleared with no host heard, because the clearing
        read a host with no seenAt as second 0 and 0 >= 0 counted every unheard linked host as heard. No bus writes such a
        mark (its stamp is the write's second), so this is a hand-written file or a clock in the epoch's first second. The
        rule (_remote_sids_lost_cleared): a host counts only when its PEER_STATE row carries a seenAt at or after the mark's
        second, so a row with no seenAt (a refusal or drift note) is not heard either. HOST's row lost under a mark at 0;
        HOST and HUB seeded up; a drift note filed for HOST and HUB heard: the mark stands; HOST heard: cleared."""
        mark = {"cause": "hand-written", "at": 0}
        self.path.write_text(json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "carryLost": mark, "hosts": {}}) + "\n")
        self.assertTrue(self._seed([(HOST, "up"), (HUB, "up")]), "the seed read the kernel's list")
        self.assertEqual(self._mark(), mark, "the mark at second 0 is carried as written")
        pm.PEER_STATE[HOST] = {"drift": "proto"}      # _peer_exchange_once's note of a 409, no exchange landed: no seenAt
        self._heard_now(HUB, [C])
        self.assertEqual(self._mark(), mark,
                         "HUB heard, HOST linked with no seenAt: the mark stands (read as second 0, HOST counted as heard "
                         "and the mark cleared with HOST unheard)")
        self._heard_now(HOST, [B])
        self.assertIsNone(self._mark(), "HOST heard: every linked host heard since the mark, cleared")

    def test_an_origin_only_row_is_no_link_and_does_not_hold_the_mark(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the twenty-second commit (its mutant X9, which counted
        origin-only PEERS rows as links, reddened no pin): an origin-only row is the kernel's remembered tier for a host this
        machine has no tunnel to, no port and no link, so it is never heard and never counts toward the clearing
        (_remote_sids_lost_cleared). The seed applies the kernel's `known` list as such rows beside the links; HOST linked
        and heard since the mark clears it, whatever origin-only rows PEERS holds (counted as links, the mark never clears on
        a machine whose kernel remembers an unattached host with a tier)."""
        self.path.write_text("{not json\n")
        self.assertTrue(self._seed([(HOST, "up")], known=[FAR]), "the seed read the kernel's list")
        self.assertEqual((pm.PEERS[FAR].get("originOnly"), pm.PEERS[FAR].get("port")), (True, None),
                         "the seed applied the remembered host as an origin-only row, no port")
        self.assertIsNotNone(self._mark(), "the seed's write read the unreadable file and marked the document")
        self._heard_now(HOST, [B])
        self.assertIsNone(self._mark(), "the one link heard since the mark: cleared, the origin-only row no link")

    def test_a_cleared_mark_does_not_reach_a_far_host_a_restarted_hub_no_longer_names(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the twenty-second commit, by execution, and the reviewer's ruling
        of 15:45Z (_remote_sids_lost_cleared): a session on a host that no linked host hears now is outside every source after
        the clear, as on a first start. Pinned as ruled, so a rule that reaches the road or widens it turns this red. HUB, the
        one link, gossips FAR's session D; FAR is never linked here. With the file intact, a restart and HUB heard again after
        its own restart, gossiping nothing about FAR: the carried via row names D, unreachable (the carry keeps a hub's word
        while the hub says nothing about its far host). With the file made not JSON, the same road: the mark clears once HUB
        is heard, and D is in no row while HUB vouches for absence, so the judge presumes D closed by rule 5. With no file, a
        first start, the same road writes the same rows (tests/test_dead_session_staleness.py ReaderFollowsTheWriter has the
        verdicts, B the only link there too)."""
        gossip = lambda far_sids, bus_id: pm.peer_exchange_apply(HUB, {}, {
            "epoch": 1, "holds": [], "busId": bus_id, "presenceAnswered": True,
            "presence": [{"id": C, "name": "api"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": "bus-far", "viaAnswered": True}
                                                      for s in far_sids]})
        rows = {}
        for road in ("intact", "lost", "first"):
            with self.subTest(road=road):
                self.path.unlink(missing_ok=True)
                self._restart()
                pm.PEERS.clear()
                self.assertTrue(self._seed([(HUB, "up")]), "the seed read the kernel's list")
                gossip([D], "bus-hub-1")
                self.assertEqual(self._vouch().get(VIA_FAR), (True, True, True), "HUB heard, its word about FAR names D")
                if road == "lost":
                    self.path.write_text(self.path.read_text().replace('"sids"', '"sids"}', 1))
                elif road == "first":
                    self.path.unlink()                # no previous file: the restarted bus is a first start
                self._restart()
                pm.PEERS.clear()
                self.assertTrue(self._seed([(HUB, "up")]), "the restarted bus's seed read the list")
                if road == "lost":
                    self.assertIsNotNone(self._mark(), "the seed's write read the file made not JSON and marked the document")
                elif road == "first":
                    self.assertIsNone(self._mark(), "a first start's seed writes no mark: nothing was lost")
                gossip([], "bus-hub-2")               # HUB restarted since: heard, gossiping nothing about FAR
                vouch = self._vouch()
                if road == "intact":
                    self.assertEqual((self._mark(), self._rows().get(VIA_FAR), vouch.get(HUB)),
                                     (None, (False, False, [D]), (True, True, True)),
                                     "the intact file: the via row carried, naming D, unreachable, beside HUB vouching")
                else:
                    self.assertEqual((self._mark(), VIA_FAR in self._rows(), vouch.get(HUB)), (None, False, (True, True, True)),
                                     "AS ON A FIRST START (%s): no mark, and D, which no linked host hears now, is in no row "
                                     "while HUB vouches for absence (where the intact file carries the via row naming D)" % road)
                    rows[road] = (self._rows(), vouch)
        self.assertEqual(rows.get("lost", "no lost road"), rows.get("first", "no first road"), "the lost file, once the mark "
                         "clears, and a first start write the same rows with the same flags")

    def test_a_standing_mark_survives_a_mark_of_another_shape_and_a_stray_byte_inside_a_top_level_key(self):
        """Round 3 of fork PR #897, the twenty-second commit: a mark read back as written is carried as written; a mark in a
        shape this module does not write is kept, re-stamped at the write's second (a mark present is the restricted side);
        and when the parse read a replacing decode and a top-level key carries a replacement character, the document is
        marked, since that key may have been the mark's (one stray byte inside "carryLost" would otherwise drop a standing
        mark, and every session its lost rows named would answer rule 5)."""
        base = json.loads(self._own_document())
        for name, mark, data_of, expect in (
                ("a mark as written", {"cause": "earlier", "at": 7}, lambda t: t.encode(), {"cause": "earlier", "at": 7}),
                ("a mark of another shape", "x", lambda t: t.encode(), None),
                ("a mark whose second is past the year 9999", {"cause": "earlier", "at": 10 ** 20}, lambda t: t.encode(), None),
                ("a stray byte inside the mark's key", {"cause": "earlier", "at": 7},
                 lambda t: t.encode().replace(b'"carryLost"', b'"carryLos\xff"'), None)):
            with self.subTest(mark=name):
                self.path.write_bytes(data_of(json.dumps(dict(base, carryLost=mark), sort_keys=True) + "\n"))
                pm.HEARTBEATS.clear()
                pm.HEARTBEATS[A] = ("web", self.now)
                before = int(pm.time.time())
                self._write_saying()
                after = int(pm.time.time())
                got = self._mark()
                self.assertIsNotNone(got, "a standing mark survives: %s" % name)
                if expect is not None:
                    self.assertEqual(got, expect, "carried as written")
                else:
                    self.assertTrue(before <= got["at"] <= after, "re-stamped at the write's second (a second past the year "
                                    "9999 carried as written is refused by the judge's reader, and fails the clearing's log "
                                    "line): %r" % got)
                self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HOST: (False, False, [B]), HUB: (False, False, [C])},
                                 "the rows carried beside the mark")

    def test_a_carried_rows_non_bool_flags_are_coerced_never_dropped(self):
        """Round 3 of fork PR #897, the reviewer's ruling on its refuters' corrections, the twentieth commit: a row carried
        from the file whose flags are not booleans is COERCED (bool() of each), never dropped. Until the commit the carry
        copied the values verbatim, and the reader, which requires seven booleans per row, answered cannot-determine for
        every sid until that source was heard again; a drop of the row would leave the sid it named in no row, and a host
        vouching for absence would let rule 5 presume it closed (tests/test_dead_session_staleness.py ReaderFollowsTheWriter
        drives that composition through the reader)."""
        self.path.write_text(json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "hosts": {
            HOST: {"kind": "peer", "sids": [B], "heard": "yes", "expired": "yes", "linkDown": 0, "linkUp": 1,
                   "answered": 1, "reachable": "yes", "vouchesAbsence": "yes", "seenAt": 1}}}) + "\n")
        pm._write_remote_sids()
        self.assertEqual(self._reach().get(HOST), (False, True, False, False, [B]),
                         "carried, its roster kept, `expired` bool('yes'), True: unreachable (a writer that drops a row with a "
                         "non-bool flag leaves None here and B in no row; one that copies the value leaves 'yes')")
        self.assertEqual({k: type(v).__name__ for k, v in self._doc()["hosts"][HOST].items() if k in pm._REMOTE_SIDS_FLAGS},
                         {k: "bool" for k in pm._REMOTE_SIDS_FLAGS}, "every one of the seven flags a bool, as the reader requires")
        self.assertEqual((self._answered()[HOST], self._vouch()[HOST]), (True, (False, False, False)),
                         "`answered` bool(1), True, inert on a carried row: heard False gates both vouching flags")

    def test_a_carried_rows_bus_id_that_is_not_a_str_is_ignored_never_compared(self):
        """Round 3 of fork PR #897, the reviewer's ruling on its refuters' corrections, the twentieth commit: a busId in the
        file that is not a str is IGNORED. Until the commit the carry tested it for membership in the set of the heard rows'
        ids, so an unhashable one raised TypeError and failed every write, the file never replaced; and the identity drop
        compared str() of it, so an int matching a heard id's text dropped the carried hub's word as a hub heard under
        another name, leaving the far host's session in no row."""
        with self.subTest(busId="a list"):
            self.path.write_text(json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "hosts": {
                HOST: {"kind": "peer", "sids": [B], "heard": True, "expired": False, "answered": True, "seenAt": 1,
                       "busId": ["bus-1"]}}}) + "\n")
            pm.HEARTBEATS[A] = ("web", self.now)
            pm._REMOTE_SIDS_SAID.clear()
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                pm._write_remote_sids()
            self.assertEqual(self._rows(), {HB + A: (True, False, [A]), HOST: (False, False, [B])},
                             "the write lands and carries the row (an unhashable busId compared by set membership fails every "
                             "write: %r)" % err.getvalue())
            self.assertNotIn("busId", self._doc()["hosts"][HOST], "the busId that is not a str is not written back")
        pm.HEARTBEATS.clear()
        with self.subTest(busId="an int matching a heard id's text"):
            self.path.write_text(json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "hosts": {
                HUB: {"kind": "peer", "sids": [], "heard": True, "expired": False, "answered": True, "seenAt": 1, "busId": 7},
                VIA_FAR: {"kind": "via", "sids": [C], "heard": True, "expired": False, "answered": True, "seenAt": 1,
                          "via": HUB, "host": FAR, "viaBus": "far-bus"}}}) + "\n")
            self._peer(HOST, [{"id": B, "name": "api"}], bus_id="7")   # a heard row whose id's text is the int's
            pm._write_remote_sids()
            self.assertEqual(self._rows(), {HOST: (True, False, [B]), HUB: (False, False, []), VIA_FAR: (False, False, [C])},
                             "the hub's carried word about the far host stands: an int busId is no identity (a carry comparing "
                             "str() of it reads the hub as heard under another name and drops the via row, C in no row)")

    def test_a_carried_rows_sids_are_coerced_to_str_and_one_not_in_the_session_id_shape_is_dropped_and_said(self):
        """Round 3 of fork PR #897, the twentieth commit, the class of the busId guard: a carried row's sids are str() of
        their values, as the document's final pass writes every sid (until that commit the legacy list's filter tested each
        carried sid for membership in a set, so an unhashable one raised TypeError and failed every write). Since the
        twenty-second commit (the reviewer's ruling of 14:57Z, clause 1) every carried sid is validated as well: the text of
        the unhashable value fails the session-id shape and is dropped, counted in one line of the bus log, and B, beside
        it, is carried. The file is UTF-8, so the line says no replacing decode."""
        self.path.write_text(json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "hosts": {
            LEGACY: {"kind": "legacy", "sids": [["x"], B], "heard": False, "expired": False, "answered": False,
                     "seenAt": 0}}}) + "\n")
        pm.HEARTBEATS[A] = ("web", self.now)
        lines = self._write_saying()
        self.assertEqual(self._rows(), {HB + A: (True, False, [A]), LEGACY: (False, False, [B])},
                         "the write lands and the list is carried with B; the unhashable value's text is no session id and "
                         "is dropped (a filter testing an unhashable sid for set membership fails every write; a carry "
                         "without the shape check writes its text as a sid): %r" % lines)
        said = [ln for ln in lines if "previous remote-sids mirror" in ln]
        self.assertEqual(len(said), 1, "said once: %r" % lines)
        self.assertIn("1 session id(s) not in the session-id shape and 0 row(s)", said[0], "the count")
        self.assertNotIn("UnicodeDecodeError", said[0], "the file was UTF-8")
        self.assertIsNone(self._mark(), "the document was read: no mark")

    def test_the_kernels_down_notify_makes_a_heard_host_unreachable_at_once_and_its_next_exchange_with_the_link_up_reachable(self):
        """Round 2 of fork PR #897, the reviewer's ruling: a host that is down cannot vouch for absence, and neither
        can one whose link the kernel has never reported up. HOST is heard here BEFORE any notify, so it vouches for
        presence alone until the kernel's up notify lands and the host is heard since (the fifth commit)."""
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, False, True, [B])},
                         "heard, its link never reported down: reachable")
        self.assertEqual(self._vouch(), {HB + A: (True, False, False), HOST: (True, False, False)},
                         "the beat, in peer mode, and the heard host with no link state both vouch for presence alone (a "
                         "writer computing vouchesAbsence as reachable says True for both; the beat's pin RE-PINNED in round "
                         "3 of fork PR #897 from the TTL vouch, which belongs to the legacy scheme)")
        self._notify(HOST, up=False)                       # the kernel's down notify; no other write follows it
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, True, False, [B])},
                         "the notify's own write: the host is marked link-down and unreachable at once, its roster kept "
                         "(a writer gating on heard alone leaves it reachable; one that waits for the next tick leaves the "
                         "file as it was; one that drops the roster loses the sid the host last named)")
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._notify(HOST, up=True)                        # the link is back; nothing heard from the host since it dropped
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]),
                         "the up notify alone is not the event: the roster is the one heard before the link dropped, "
                         "and says nothing about a session started there since")
        self.assertEqual(self._vouch()[HOST], (False, False, False),
                         "PEERS says up and the mark stands: linkUp False (a writer reading PEERS alone says True)")
        self._peer(HOST, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}])   # its exchange arrives with the link up
        pm._write_remote_sids()
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B, C]),
                         "heard with the link up: reachable, on the roster that exchange reported")
        self.assertEqual(self._vouch()[HOST], (True, True, True),
                         "the link known up and the host heard since it dropped: it vouches for absence too")

    def test_the_two_exchange_recorders_clear_the_mark_and_an_exchange_heard_while_down_counts_once_the_link_is_up(self):
        """The mark the down notify sets lives on the PEER_STATE row, and both recorders replace that row: the dialer's
        fold (peer_exchange_apply, the path a re-dial after the up notify runs) and the dialed side's handler
        (peer_exchange_handle: the far side may dial us while OUR kernel holds the link to it down). An exchange
        heard while the link is down is heard, and its host is reachable the moment the link is up: what the ruling
        gates is a roster from before the drop, and this one is not."""
        self._notify(HOST, up=True)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._vouch()[HOST], (True, True, True), "notified up, then heard: vouches for presence and absence")
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]))
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._notify(HOST, up=True)
        pm.peer_exchange_apply(HOST, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "presenceAnswered": True})
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B]),
                         "the dialer's fold replaced the row (the mark with it) and wrote: reachable")
        self.assertEqual(self._vouch()[HOST], (True, True, True), "...and, PEERS up, vouching for absence again")
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B]))
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._local_listing_answered_empty()
        resp, status = pm.peer_exchange_handle(self._exchange_request(HOST, [{"id": B, "name": "api"}, {"id": D, "name": "web"}]))
        self.assertEqual(status, 200, resp)
        self.assertEqual(self._reach()[HOST], (True, False, True, False, [B, D]),
                         "heard while the kernel holds the link down: the roster is fresh, the row still unreachable "
                         "(the link, not the roster, is what is down)")
        self.assertEqual(self._vouch()[HOST], (False, False, False), "the link is down: it vouches for nothing yet")
        self._notify(HOST, up=True)
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B, D]),
                         "the link is up and the host was heard since it dropped: reachable on the up notify's own write")
        self.assertEqual(self._vouch()[HOST], (True, True, True),
                         "both hold, the link up and the host heard since the drop: it vouches for absence on that write")

    def test_a_row_a_far_bus_filed_under_its_declared_name_before_the_fold_vouches_for_presence_alone(self):
        """The ruled closure of the road the fourth commit disclosed (round 2 of fork PR #897, the reviewer's ruling: a
        source vouches for a sid's ABSENCE only when its link is known up; every heard source still vouches for
        PRESENCE). The kernel notifies the ALIAS it dials (PEERS[alias]); the dialed side's handler files a far bus
        under the name it DECLARES unless a PEER_STATE row under a dialable name already carries its busId
        (_canon_peer_name). Before this bus's own dial has folded the peer under the alias (a restarted bus whose
        seeded row has no token yet; a dial the far side refuses while its dial to us lands), the far bus's row sits
        under its declared hostname, which has no PEERS row and no link state: it is reachable, so the sid it names is
        rule 4's, and it does not vouch for absence, so a sid it does not name is not settled either way, whether the
        alias is up or down (until the fifth commit heard alone made it vouch, and a sid nothing named was rule 5's
        with this host as the only reachable one). The fold (peer_exchange_apply under the alias with the busId) is
        the event that files the row where the alias's link reaches it: linkUp and vouching for absence on the fold's
        own write, link-down and unreachable on the alias's down notify, and neither on the up notify alone until the
        host is heard since. The road is reached again at every bus restart the far side dials into first: the
        carried alias row is the same bus by busId and gives way to the heard row under the declared name, which
        vouches for presence alone until this bus's dial folds it back."""
        alias, declared = "TESTHOST-c-alias", "TESTHOST-c-hostname"   # the kernel dials the alias; the far bus declares its hostname
        self._local_listing_answered_empty()
        self._notify(alias, up=True)                        # the kernel's link is up; this bus has not dialed yet
        self._far_dials_us(declared, [{"id": B, "name": "api"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [declared], "no row under a dialable name carries the busId: filed as declared")
        self.assertEqual(self._reach(), {declared: (True, False, False, True, [B])})
        self.assertEqual(self._vouch(), {declared: (True, False, False)},
                         "THE RULE: the row under the declared name is heard and not held down, so it vouches for the "
                         "presence of the sid it names (reachable); the kernel dials no such name, so its link is unknown "
                         "(linkUp False, the alias's up notify does not reach it) and it does not vouch for absence (a "
                         "writer computing vouchesAbsence as reachable says True here: the disclosed road, reopened)")
        self._notify(alias, up=False)
        self.assertEqual((pm.PEERS[alias]["up"], (pm.PEER_STATE.get(declared) or {}).get("linkDown")), (False, None),
                         "the kernel holds the alias down; the declared row carries no mark (the notify marks PEER_STATE[alias])")
        self.assertEqual((self._reach(), self._vouch()), ({declared: (True, False, False, True, [B])}, {declared: (True, False, False)}),
                         "the alias down changes nothing for a row with no link state of its own: the sid it names stays "
                         "protected (rule 4), and a sid it does not name is not settled either way (it never vouched for "
                         "absence, so the down notify has nothing to withdraw)")
        # the fold: this bus's own dial lands under the alias with the busId, the event that files the row under the alias
        self._notify(alias, up=True)
        pm.peer_exchange_apply(alias, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "busId": "bus-c", "presenceAnswered": True})
        self.assertEqual(sorted(pm.PEER_STATE), [alias], "the declared row is the same bus (busId), dropped by the fold")
        self.assertEqual(self._reach(), {alias: (True, False, False, True, [B])},
                         "the fold's own write has one row per bus, under the alias: the recorder writes AFTER the busId "
                         "fold (a recorder writing before it leaves the declared row in the file, heard and reachable, "
                         "until the next write)")
        self.assertEqual(self._vouch(), {alias: (True, True, True)},
                         "under the alias the kernel holds up, heard on this exchange: the row vouches for absence now")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [alias], "canonicalized: a row under a dialable name carries the busId now")
        self.assertEqual(self._vouch(), {alias: (True, True, True)})
        self._notify(alias, up=False)
        self.assertEqual((self._reach(), self._vouch()), ({alias: (True, False, True, False, [B, C])}, {alias: (False, False, False)}),
                         "folded under the alias, the row follows the alias's link: down, so unreachable and vouching for nothing")
        self._notify(alias, up=True)
        self.assertEqual(self._vouch(), {alias: (False, False, False)},
                         "the up notify alone leaves the mark: no vouching until the host is heard since the drop")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual((sorted(pm.PEER_STATE), self._vouch()), ([alias], {alias: (True, True, True)}),
                         "heard again (the far bus's dial, canonicalized under the alias) with the link up: both hold")
        # the road again at a restart: empty memory, the file carrying the alias row, the kernel seeding the alias down
        # (a tunnel down at start), the far side dialing in before this bus's own dial (which a down link never makes)
        self._restart()
        pm.PEERS.clear()
        self._notify(alias, up=False)
        self.assertEqual((self._reach(), self._vouch()), ({alias: (False, False, True, False, [B, C])}, {alias: (False, False, False)}),
                         "carried from the previous file, not heard, the seeded link down: unreachable")
        self._far_dials_us(declared, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "bus-c")
        self.assertEqual(sorted(pm.PEER_STATE), [declared], "memory empty: nothing to canonicalize to, filed as declared")
        self.assertEqual((self._reach(), self._vouch()), ({declared: (True, False, False, True, [B, C])}, {declared: (True, False, False)}),
                         "the same road at the restart: the carried alias row gives way to the heard row (same busId), "
                         "which has no link state while the kernel holds the alias down: presence alone, until this bus's "
                         "dial, when the link comes up and the token arrives, folds it back under the alias")
        self._notify(alias, up=True)
        pm.peer_exchange_apply(alias, {}, {"presence": [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "epoch": 1,
                                           "holds": [], "busId": "bus-c", "presenceAnswered": True})
        self.assertEqual((self._reach(), self._vouch()), ({alias: (True, False, False, True, [B, C])}, {alias: (True, True, True)}),
                         "folded again: one row, under the alias, vouching for absence")

    def test_a_far_host_gossiped_through_a_hub_follows_the_hubs_link(self):
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), VIA_FAR: (True, False, False, True, [B])})
        self.assertEqual(self._vouch(), {HUB: (True, True, True), VIA_FAR: (True, True, True)},
                         "the hub's link is known up and the hub heard: the far host vouches for absence by the hub's link "
                         "(a via row has no link of its own)")
        self._notify(HUB, up=False)
        self.assertEqual(self._reach(), {HUB: (True, False, True, False, [A]), VIA_FAR: (True, False, True, False, [B])},
                         "the far host is reached through the hub: a hub the kernel holds down cannot carry fresh word "
                         "about it, so its row is link-down with the hub's, roster kept")
        self.assertEqual(self._vouch(), {HUB: (False, False, False), VIA_FAR: (False, False, False)})
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), VIA_FAR: (True, False, False, True, [B])},
                         "the hub's exchange with its link up: both reachable again")
        self.assertEqual(self._vouch(), {HUB: (True, True, True), VIA_FAR: (True, True, True)}, "...and both vouching for absence")

    def test_a_far_host_gossiped_through_a_hub_the_kernel_never_notified_vouches_for_presence_alone(self):
        self.assertEqual(pm.PEERS, {}, "no notify has landed: the hub has no link state")
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), VIA_FAR: (True, False, False, True, [B])},
                         "heard, not held down: both vouch for the presence of the sids they name")
        self.assertEqual(self._vouch(), {HUB: (True, False, False), VIA_FAR: (True, False, False)},
                         "a hub with no link state vouches for absence for nobody, and neither does the far host it "
                         "gossips (a via row vouching by its own presence, not the hub's link, says True here)")
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus"}])
        pm._write_remote_sids()
        self.assertEqual(self._vouch(), {HUB: (True, True, True), VIA_FAR: (True, True, True)},
                         "the hub notified up and heard since: both vouch for absence")

    def test_a_source_the_kernel_never_notified_has_no_link_state_and_vouches_for_presence_alone(self):
        self.assertEqual(pm.PEERS, {}, "no notify has landed")
        pm.HEARTBEATS[A] = ("web", self.now)
        self._peer(HOST, [{"id": B, "name": "api"}])      # heard, and the kernel never notified it
        pm.peer_update({"host": FAR, "trust": "directed", "originOnly": True})   # a tier for a host with no tunnel
        self._peer(FAR, [{"id": C, "name": "tests"}])
        pm._write_remote_sids()
        self.assertEqual(pm.PEERS[FAR]["port"], None, "origin-only: no port, nothing to dial")
        self.assertFalse(pm.PEERS[FAR]["up"], "the row spells up False, and that is not a link held down")
        self.assertEqual(self._reach(), {HB + A: (True, False, False, True, [A]), HOST: (True, False, False, True, [B]),
                                         FAR: (True, False, False, True, [C])},
                         "no dialable PEERS row: never notified, origin-only, or a heartbeat key no row can match; "
                         "each heard and not held down, so each vouches for the presence of the sids it names")
        self.assertEqual(self._vouch(), {HB + A: (True, False, False), HOST: (True, False, False), FAR: (True, False, False)},
                         "the beat, in peer mode, has no link and no TTL vouch (RE-PINNED in round 3 of fork PR #897 from the "
                         "TTL vouch, the legacy scheme's); the never-notified host and the origin-only host have no link state: "
                         "all three vouch for presence alone (a writer vouching a heartbeat by its TTL whatever the scheme says "
                         "True for the beat; one vouching by heard alone says True for the hosts)")
        # a down notify for a host this process has not heard: its carried row is unreachable already (heard false),
        # and now also says the kernel holds its link down
        self._restart()
        self._notify(HOST, up=False)
        self.assertEqual(self._reach()[HOST], (False, False, True, False, [B]),
                         "carried from the previous file, heard false, link-down true: unreachable, roster kept")
        self.assertEqual(self._vouch()[HOST], (False, False, False))
        self._notify(HOST, up=True)
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm._write_remote_sids()
        self.assertEqual(self._reach()[HOST], (True, False, False, True, [B]))
        self.assertEqual(self._vouch()[HOST], (True, True, True), "notified up and heard since: it vouches for absence now")

    def test_a_heard_link_up_host_whose_exchange_served_a_cache_vouches_for_presence_alone_until_an_exchange_answers(self):
        """Round 3 of fork PR #897, the reviewer's ruling (its refuters found the road by execution through the real
        handler and this writer): while a host's kernel listing does not answer, its presence producer serves the last
        answered rows (_local_presence_checked, the blink honesty of 2026-08-31), and until this round that cache rode the
        exchange with no sign of it, so a session started on the host after that listing was in no roster while its mail
        rode the same exchange, and the host, heard with its link known up, vouched for absence: rule 5 presumed the
        session closed. Now the answered bit the sender already computes rides the payload (`presenceAnswered`, beside
        `presence`, in the request builder and the response builder alike), both recorders keep it on the PEER_STATE row,
        and the writer gives every row `answered`: a row whose last exchange served a cache is reachable (the sids it names
        were live at the last answered listing, rule 4) and does not vouch for absence, released by the next exchange that
        carries an answered listing, the event. A payload lacking the field, an older peer's, or carrying a non-boolean,
        reads unanswered: the restricted side, so no older peer reopens the road. One module plays both buses here: the
        far host's request is built by the real builder under THIS process's listing state and handed to the real handler
        as the far host's, and the real handler's response is folded by the real dialer's fold the same way, so the sender's
        bit, both builders, both recorders and the writer are the product's. The composition with the reader's verdicts is
        tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the cached roster phase)."""
        X = "TESTHOST-x"
        self._forget_presence_cache()
        self._notify(X, up=True)                              # the kernel holds X's link up

        def x_dials_us(bus_id="x-bus"):                       # X's request, the real builder's, handed to the real handler as X's
            req = pm.build_exchange_request(X, wait=False)
            req["host"], req["busId"] = X, bus_id
            resp, status = pm.peer_exchange_handle(req)
            self.assertEqual(status, 200, resp)
            return req
        self._local_listing_answered([{"id": B, "name": "api"}])
        req_answered = x_dials_us()
        answered_row = (self._reach()[X], self._vouch()[X], self._answered()[X], pm.PEER_STATE[X].get("presenceAnswered"))
        # X's kernel restarts: its listing does not answer, and a session starts there meanwhile (in no roster yet)
        self._local_listing_unanswered()
        req = x_dials_us()
        self.assertEqual(self._vouch()[X], (True, True, False),
                         "THE RULE: the cached roster still vouches for the presence of the sid it names (B was live at the "
                         "last answered listing), and NOT for the absence of a sid it does not name, its link known up "
                         "notwithstanding: a session started on X since is in no roster, so the reader answers "
                         "cannot-determine for it, the reason naming X with its listing unanswered (a writer ignoring the "
                         "bit, the tenth commit's among them, says (True, True, True) here, and rule 5 presumes that session "
                         "closed: the false settle)")
        self.assertEqual((self._reach()[X], self._answered()[X]), ((True, False, False, True, [B]), False),
                         "reachable on the cached roster, and the roster marked a cache")
        self.assertEqual((req.get("presenceAnswered"), [a["id"] for a in req["presence"]]), (False, [B]),
                         "the blink: the builder serves the last answered rows AND says they are a cache (a builder riding "
                         "the rows alone leaves the far side to read the cache as X's word about what runs there now)")
        self.assertIs(pm.PEER_STATE[X].get("presenceAnswered"), False, "the handler's recorder keeps it on the row")
        # and the exchange before the blink: the bit True through the builder, the recorder and the writer
        self.assertEqual((req_answered.get("presenceAnswered"), [a["id"] for a in req_answered["presence"]]), (True, [B]),
                         "the request builder rides the bit beside the rows: an answered listing")
        self.assertEqual(answered_row, ((True, False, False, True, [B]), (True, True, True), True, True),
                         "heard with its link up on an answered roster: it vouches for presence and absence, the recorder's bit True")
        # the event: X's next exchange with an answered listing, which now names the session started during the blink
        self._local_listing_answered([{"id": B, "name": "api"}, {"id": C, "name": "tests"}])
        req = x_dials_us()
        self.assertEqual(req.get("presenceAnswered"), True)
        self.assertEqual((self._reach()[X], self._vouch()[X], self._answered()[X]),
                         ((True, False, False, True, [B, C]), (True, True, True), True),
                         "released by the exchange that answers, on that write and nothing else: no grace period")
        # the dialer's half, the same road: OUR response, built by the real handler while OUR listing does not answer,
        # folded by the real dialer's fold as X's word
        self._local_listing_unanswered()
        resp = self._far_dials_us(X, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "x-bus")
        self.assertEqual((resp.get("presenceAnswered"), [a["id"] for a in resp["presence"]]), (False, [B, C]),
                         "the response builder rides the bit too: the last answered rows, marked a cache")
        pm.peer_exchange_apply(X, {}, resp)
        self.assertIs(pm.PEER_STATE[X].get("presenceAnswered"), False, "the dialer's fold keeps it on the row")
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "recorded by the dialer's fold: presence alone (a fold that drops the bit leaves the row unanswered "
                         "for good, or, defaulting it, answered over a cache)")
        self._local_listing_answered([{"id": B, "name": "api"}, {"id": C, "name": "tests"}])
        resp = self._far_dials_us(X, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "x-bus")
        self.assertEqual(resp.get("presenceAnswered"), True)
        pm.peer_exchange_apply(X, {}, resp)
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, True), True), "the answering response releases it")
        # the default for a payload without the field (a peer from before it), and for one that spells it as a string
        self._far_dials_us(X, [{"id": B, "name": "api"}], "x-bus", answered=None)
        self.assertIs(pm.PEER_STATE[X].get("presenceAnswered"), False, "no field: recorded as unanswered")
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "THE DEFAULT: a payload lacking the field reads unanswered, the restricted side, so an older peer's "
                         "roster vouches for presence alone (a recorder defaulting to answered lets an older peer reopen the road)")
        self._far_dials_us(X, [{"id": B, "name": "api"}], "x-bus", answered="true")
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "a string is not the boolean: JSON true alone counts (bool of a non-empty string is True)")
        pm.peer_exchange_apply(X, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "busId": "x-bus"})
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "the same default in the dialer's fold: a response lacking the field is unanswered")
        self._far_dials_us(X, [{"id": B, "name": "api"}], "x-bus", answered=True)
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, True), True))

    def test_a_via_row_carries_the_far_hosts_answered_bit_and_not_the_hubs(self):
        """A hub's gossip about a far host is that host's roster as it reported it to the hub, so whether that roster was an
        answered listing is the far host's word, not the hub's (round 3 of fork PR #897, the reviewer's refuters' scope):
        presence_payload stamps every gossiped row with the far host's `presenceAnswered` as its exchange recorded it
        (`viaAnswered`), and the writer's via row takes that bit. A hub whose own listing did not answer still relays a
        far host's answered roster whole, and a hub that answered relays a far host's cache as a cache. An element
        without the field, a hub from before it, reads unanswered, and so does a row one of whose elements lacks it. This
        bus plays the hub first (the far host dials us, our gossip is built by the real builder), then the spoke (the
        hub's gossip lands here and the writer files it)."""
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        self._notify(FAR, up=True)
        self._far_dials_us(FAR, [{"id": C, "name": "tests"}], "far-bus", answered=False)   # the far host's exchange served a cache
        self.assertEqual((self._vouch()[FAR], self._answered()[FAR]), ((True, True, False), False))
        gossip_cache = [pa for pa in pm.presence_payload(HOST)[0] if pa.get("via")]
        self.assertEqual([(pa["id"], pa["via"], pa["viaBus"], pa.get("viaAnswered")) for pa in gossip_cache],
                         [(C, FAR, "far-bus", False)],
                         "our gossip about the far host carries ITS bit, as its exchange recorded it: a cache (a builder "
                         "stamping our own listing's bit says True here, our listing having answered)")
        self._far_dials_us(FAR, [{"id": C, "name": "tests"}], "far-bus", answered=True)
        gossip_answered = [pa for pa in pm.presence_payload(HOST)[0] if pa.get("via")]
        self.assertEqual([pa.get("viaAnswered") for pa in gossip_answered], [True], "...and True once the far host answers")
        # now this bus is the spoke: the hub's gossip lands here (the hub's own listing answered), and the writer files it
        pm.PEER_STATE.clear(); pm.PEERS.clear(); self.path.unlink()
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}] + gossip_cache, answered=True)
        pm._write_remote_sids()
        self.assertEqual((self._vouch()[HUB], self._answered()[HUB]), ((True, True, True), True), "the hub's own listing answered")
        self.assertEqual((self._reach()[VIA_FAR], self._vouch()[VIA_FAR], self._answered()[VIA_FAR]),
                         ((True, False, False, True, [C]), (True, True, False), False),
                         "THE RULE: the via row takes the FAR host's bit, a cache, so it vouches for the presence of C and not "
                         "for the absence of a session started on the far host since, whatever the hub's link and listing (a "
                         "via row taking the hub's bit says (True, True, True) here, and rule 5 presumes that session closed "
                         "on a roster the far host itself marked stale)")
        self._peer(HUB, [{"id": A, "name": "web"}] + gossip_answered, answered=True)
        pm._write_remote_sids()
        self.assertEqual((self._vouch()[VIA_FAR], self._answered()[VIA_FAR]), ((True, True, True), True),
                         "the far host's next answered roster, relayed: the via row vouches for absence again")
        # the converse: the hub's own listing did not answer, the far host's did
        self._peer(HUB, [{"id": A, "name": "web"}] + gossip_answered, answered=False)
        pm._write_remote_sids()
        self.assertEqual((self._vouch()[HUB], self._vouch()[VIA_FAR]), ((True, True, False), (True, True, True)),
                         "the hub's row vouches for presence alone (its own roster is a cache) while its word about the far host "
                         "vouches for absence: the far host answered (a via row taking the hub's bit says False here, the "
                         "conservative side but the wrong source's word)")
        # a hub from before the field stamps none: unanswered, the restricted side; and one element without it among
        # several about one host makes the row unanswered
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": C, "name": "tests", "via": FAR, "viaBus": "far-bus"}], via_answered=None)
        pm._write_remote_sids()
        self.assertEqual((self._vouch()[VIA_FAR], self._answered()[VIA_FAR]), ((True, True, False), False),
                         "no field on the gossiped row: unanswered (a writer defaulting a missing viaAnswered to True lets an "
                         "older hub's relay reopen the road)")
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": C, "name": "tests", "via": FAR, "viaBus": "far-bus", "viaAnswered": True},
                         {"id": D, "name": "api", "via": FAR, "viaBus": "far-bus"}], via_answered=None)
        pm._write_remote_sids()
        self.assertEqual((self._reach()[VIA_FAR][4], self._answered()[VIA_FAR]), ([C, D], False),
                         "every element about the host must carry the bit for the row to be answered")

    def test_a_hubs_answered_word_about_a_directly_held_host_stands_beside_that_hosts_cached_row_until_it_answers(self):
        """Round 3 of fork PR #897, the reviewer's verifier at the eleventh commit, by execution through the real builder,
        handler, writer and reader: a heard row whose last exchange served a CACHED roster is the third state, beside
        carried and held down, in which a direct row speaks for nothing about a session started on its host since
        (_direct_row_speaks). The far host's kernel blinks and a session starts there meanwhile; its dial to us, built
        by the real builder under this process's listing state and handed to the real handler as the far host's, serves
        the last answered rows marked a cache; the hub, whose own exchange with the far host was answered, names the new
        session. At the eleventh commit the gate read heard and not held down alone, so the hub's word folded into the
        cached row, the session was in no row, and the hub, vouching for absence, let rule 5 presume it closed for one
        exchange interval of the far host (the cached row had joined the fold residual's population). Now the hub's word
        stands as a via row beside the cached row, carrying the far host's bit as the hub stamped it, answered, so the
        reader answers rule 4 for the session; with the hub NOT heard, the carried via row stands beside the cached row
        (a carry letting the cached row speak drops it, and the session is in no row while any other host vouches). The
        far host's next exchange that answers is the event: its row speaks, the via row is dropped by the carry, and
        the hub's next gossip folds. The composition with the reader's verdicts is tests/test_dead_session_staleness.py
        ReaderFollowsTheWriter (the cached roster phase, the hub's word beside the cached row)."""
        self._forget_presence_cache()
        self._notify(FAR, up=True)
        self._notify(HUB, up=True)

        def far_dials_us():                                   # the far host's request, the real builder's under THIS process's
            req = pm.build_exchange_request(FAR, wait=False)   # listing state, handed to the real handler as the far host's
            req["host"], req["busId"] = FAR, "far-bus"
            resp, status = pm.peer_exchange_handle(req)
            self.assertEqual(status, 200, resp)
            return req
        gossip = lambda *sids: [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        self._local_listing_answered([{"id": C, "name": "tests"}])
        far_dials_us()
        self._peer(HUB, gossip(C), answered=True)             # the hub's word about the far host as it reported it, answered
        pm._write_remote_sids()
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, []), FAR: (True, False, False, True, [C])},
                         "both heard with their links up on answered rosters: the gossip folds, the direct row speaks")
        # the far host's kernel blinks; a session (D) starts there meanwhile; its dial to us serves the cache
        self._local_listing_unanswered()
        req = far_dials_us()
        self.assertEqual((req.get("presenceAnswered"), [a["id"] for a in req["presence"]]), (False, [C]),
                         "the blink: the far host's request serves the last answered rows, marked a cache")
        self._peer(HUB, gossip(C, D), answered=True)          # the hub's next exchange: its own exchange with the far host
        pm._write_remote_sids()                               # answered, it names the session started during the blink
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, []), FAR: (True, False, False, True, [C]),
                                         VIA_FAR: (True, False, False, True, [C, D])},
                         "THE RULE: the direct row is heard and not held down but its roster is a cache, so it speaks for "
                         "nothing about a session started on the far host since, and the hub's word stands beside it as a via "
                         "row naming that session (D): the reader answers rule 4 for D by the hub's row (a gate on heard and "
                         "not held down alone, the eleventh commit's, folds the gossip into the cached row, D is in no row, and "
                         "the hub vouching for absence lets rule 5 presume it closed until the far host's next dial)")
        self.assertEqual((self._vouch()[FAR], self._answered()[FAR]), ((True, True, False), False),
                         "the cached row still vouches for the presence of the sid it names and not for absence")
        self.assertEqual((self._vouch()[VIA_FAR], self._answered()[VIA_FAR]), ((True, True, True), True),
                         "the via row carries the FAR host's bit as the hub stamped it, answered (the far host's exchange with "
                         "the hub answered), following the hub's link: it vouches for presence and absence")
        row = self._doc()["hosts"][VIA_FAR]
        self.assertEqual((row["kind"], row["via"], row["host"], row["viaBus"]), ("via", HUB, FAR, "far-bus"))
        # THE CARRY'S HALF: the hub not heard. A restart; the kernel seeds both links up; the far host dials us first, its
        # exchange still a cache (the producer's memory outlives the bus's table here, as the disk twin primes a real one)
        self._restart()
        pm.PEERS.clear()
        self._notify(FAR, up=True)
        self._notify(HUB, up=True)
        req = far_dials_us()
        self.assertEqual(req.get("presenceAnswered"), False)
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, []), FAR: (True, False, False, True, [C]),
                                         VIA_FAR: (False, False, False, False, [C, D])},
                         "the carried via row stands beside the cached direct row, heard=false, the hub's last word about the "
                         "far host still naming D (a carry letting the cached row speak drops it here, so D is in no row, "
                         "cannot-determine by nothing, and rule 5's as soon as any other host vouches for absence)")
        self.assertEqual((self._vouch()[FAR], self._vouch()[VIA_FAR]), ((True, True, False), (False, True, False)),
                         "the cached row vouches for presence alone; the carried via row, the seed's linkUp, for nothing")
        # the event: the far host's next exchange that answers, naming the session
        self._local_listing_answered([{"id": C, "name": "tests"}, {"id": D, "name": "api"}])
        req = far_dials_us()
        self.assertEqual(req.get("presenceAnswered"), True)
        self.assertEqual(self._reach(), {HUB: (False, False, False, False, []), FAR: (True, False, False, True, [C, D])},
                         "the direct row speaks again on an answered listing: the via row is DROPPED by the carry (a carry "
                         "that keeps it leaves the hub's older word naming D for the file's life once D ends there)")
        self.assertEqual((self._vouch()[FAR], self._answered()[FAR]), ((True, True, True), True))
        self._peer(HUB, gossip(C, D), answered=True)          # the hub heard again: its word folds, the direct row speaks
        pm._write_remote_sids()
        self.assertEqual(sorted(self._reach()), sorted([HUB, FAR]), "no via row while the far host speaks for itself")

    def test_a_row_carried_from_a_file_before_the_answered_bit_reads_unanswered(self):
        """A restart over a mirror the round-2 shape wrote (six flags, no `answered`): the carried row gets the bit False,
        the restricted side, and a bool, so the reader's shape check passes the row; carried, it vouches for nothing
        anyway (heard being the first condition of both flags), and the host's exchange in this process replaces the row
        with its own bit. A legacy heartbeat is its own answer (answered True; in peer mode it vouches for presence
        alone all the same), and a row kept across processes keeps its bit."""
        self.path.write_text(json.dumps({"v": 2, "busStarted": 1, "writtenAt": 1, "hosts": {
            HOST: {"kind": "peer", "sids": [B], "heard": True, "expired": False, "linkDown": False, "linkUp": True,
                   "reachable": True, "vouchesAbsence": True, "seenAt": 1}}}) + "\n")
        pm._write_remote_sids()
        self.assertEqual((self._reach()[HOST], self._vouch()[HOST], self._answered()[HOST]),
                         ((False, False, False, False, [B]), (False, False, False), False),
                         "carried from a file before the field: not heard, its roster kept, answered False (a writer copying "
                         "the row without the bit leaves None where the reader requires a bool, and the whole mirror unparsable)")
        self._peer(HOST, [{"id": B, "name": "api"}], answered=True)
        pm._write_remote_sids()
        self.assertEqual(self._answered()[HOST], True, "the host's exchange in this process: its own bit")
        pm.HEARTBEATS[A] = ("web", self.now)
        pm._write_remote_sids()
        self.assertEqual((self._vouch()[HB + A], self._answered()[HB + A]), ((True, False, False), True),
                         "a legacy heartbeat is its own answer: no listing gates it; in peer mode it vouches for presence alone "
                         "(RE-PINNED in round 3 of fork PR #897 from the TTL vouch, the legacy scheme's)")
        self._restart()
        pm._write_remote_sids()
        self.assertEqual((self._answered()[HOST], self._answered()[HB + A], self._vouch()[HOST]), (True, True, (False, False, False)),
                         "rows kept across processes keep their bits, and vouch for nothing until their events (heard first)")

    def test_a_write_failure_is_said_once_in_the_bus_log(self):
        state = pm.STATE
        blocker = tempfile.NamedTemporaryFile(dir=str(state), delete=False)
        blocker.close()
        self.addCleanup(os.unlink, blocker.name)
        pm.STATE = Path(blocker.name) / "under-a-file"   # no directory can exist here: every write fails
        self.addCleanup(setattr, pm, "STATE", state)
        pm._REMOTE_SIDS_SAID.clear()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            pm._write_remote_sids()
            pm._write_remote_sids()
        lines = [ln for ln in err.getvalue().splitlines() if "remote-sids mirror was not written" in ln]
        self.assertEqual(len(lines), 1, "said once per distinct text, never swallowed: %r" % err.getvalue())
        self.assertIn("the judge reads the previous one", lines[0])


if __name__ == "__main__":
    unittest.main()
