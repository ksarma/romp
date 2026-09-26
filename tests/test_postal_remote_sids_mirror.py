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
closed only when a source vouches for absence, none names it, no source heard in this process has an unanswered
roster, held down or not (the reader's listing-unanswered arm, round 4 of fork PR #897, the twenty-ninth and thirtieth
commits; this module runs no reader, tests/test_dead_session_staleness.py does) and no lost-carry mark stands. Two roads to a false settle closed here, at the
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
hub, vouching for absence, let rule 5 presume a live session closed for one exchange interval of the far host); a
hub's HELD word (round 4 of fork PR #897, the thirty-first commit): a far host's unanswered word through a hub stays
heard on the hub's row across a restarted hub's rosters that omit the host, until the hub names the host again, by
name or by bus id, while an answered word the hub omits is carried as before, and the same hub process's omission, the
far host's answer with an empty listing, releases it (the thirty-second commit; a hub with no bus id holds it) on the
road whose roster last named the host, the hub's dial or its answer to our dial (the thirty-third commit), for a far
bus heard answering in this process (round 6, the reviewer's round-5 ruling B: a word with no viaBus, or whose far bus
this bus has not heard answer, stays held; the sources of that evidence pinned), a hub from before viaBus renaming a
far host holding the old name's word within one process and across its restart (within one process released until
round 6); and
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
one link, no longer hears in no row once the mark clears, the rows a first start writes. And (round 4 of fork PR #897, the
thirty-fourth commit) the release keyed on the read that triggered the write, so a thread-less read landing before the
recorder's write takes the lock keeps no comment thread's row; the mark's bus-log line stating the clearing rule of the
scheme at the write; the JSON literal null marking the document; the mark's second pinned on every conjunct of its shape
check; and JSON true alone counting as answered at the dialer's fold, the writer's read of a gossiped row and a held word.
And (round 6 of fork PR #897, the reviewer's round-5 ruling E and decision 5 on round 5) PEER_STATE's shape comment
naming every key each writer stores, derived by running every writer the lock's census finds, and the recorders' stamps
of the writer state round 4 added: road on each row, heldAt, hubBus and hubRoad on each held word.
tests/test_dead_session_staleness.py ReaderFollowsTheWriter
runs this writer and the judge's reader together over one root; tests/test_postal_bus_lifetime.py
MonitorTick pins the poll's write. SYNTHETIC fixtures only: private synthetic sids, hostname TESTHOST."""
import ast
import builtins
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
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
# Values a peer's JSON can carry for an answered bit (presenceAnswered, viaAnswered) that are truthy and are not JSON true,
# each read as answered by one wrong reading of the bit: the string by bool(), the numbers 1 and 1.0 by == True (both
# equal True in Python). Only `is True` reads all three unanswered (round 4 of fork PR #897: the string pinned at every
# reader since the thirty-fourth commit, the numbers since the thirty-fifth, found by the reviewer's verifier, whose
# == True at all four readers passed every pin).
TRUTHY_NOT_TRUE = ("true", 1, 1.0)


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
    same function, the same shape, stands in that module's child as nested_parse_raises, and that module's PresumedClosed
    ladder derives the class in its own process the same way (round 4 of fork PR #897, the thirty-fourth commit).
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
    "(<class>: " slot with the class of the exception its parse caught; until the thirty-fourth commit
    (round 4 of fork PR #897) it tested the value the parse returned rather than whether the parse failed, so a parse
    that returned None filled the slot with the class of None, "(NoneType: None)", and both cases here passed with the
    parse stubbed to return None. Since that commit a parse that returns None is a JSON value of neither shape, and the
    cause says "a JSON NoneType", with no such slot. NoneType is no exception class, so the check fails there, naming the
    interpreter and the depth. Any name that passes this check is refused at the cause when the parse returns: the
    writer's cause then carries no "(<class>: " slot, or there is no mark. The staleness case keeps the
    identifier check in its child: it also reads the reader's line, which says "(ValueError: not a JSON object)" for a
    parse that returns None, so a derived "NoneType" fails there."""
    cls = (getattr(builtins, name, None) or getattr(json, name, None)) if isinstance(name, str) else None
    return isinstance(cls, type) and issubclass(cls, BaseException)


def _cap():
    """The capture of this bus's dial, built now, for a fold of its answer (round 6 of fork PR #897, the reviewer's round-5
    ruling C: the answer placed after every roster recorded so far); a bus with no capture takes no keyword."""
    return {"built": [pm._PEER_SEQ[0]]} if hasattr(pm, "_PEER_SEQ") else {}


def _answered_buses():
    """The bus's set of far bus ids heard answering in this process (postal_service.py _ANSWERED_BUSES; round 6 of fork PR
    #897, the reviewer's round-5 ruling B), or a fresh empty set where the bus keeps none (the forty-ninth commit, under
    which the red-before runs overlay this module): the fixtures clear and restore it as they do PEER_STATE, and never
    fail on its absence, so a red there is the test's own assertion."""
    seen = getattr(pm, "_ANSWERED_BUSES", None)
    return seen if isinstance(seen, set) else set()


def _peer_state_shape_comment_keys():
    """The keys PEER_STATE's declaration comment names (round 6 of fork PR #897, the reviewer's round-5 ruling E): every
    double-quoted identifier in the comment on the bus's `PEER_STATE = {}` line and the `#` lines that continue it, less
    road's two values, "dial" and "answer", which the comment quotes beside that key. The declaration must stand once."""
    lines = Path(os.path.realpath(os.path.join(BIN, "romp-postal-service"))).read_text().splitlines()
    at = [i for i, ln in enumerate(lines) if ln.startswith("PEER_STATE = {}")]
    if len(at) != 1:
        raise AssertionError("PEER_STATE's declaration stands once in the bus's source: lines %r" % at)
    text = [lines[at[0]].partition("#")[2]]
    for ln in lines[at[0] + 1:]:
        if not ln.startswith("#"):
            break
        text.append(ln[1:])
    return set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', " ".join(text))) - {"dial", "answer"}


class Mirror(unittest.TestCase):
    def setUp(self):
        pm.STATE.mkdir(parents=True, exist_ok=True)
        self.path = pm.STATE / "remote-sids"
        self.path.unlink(missing_ok=True)
        answered = _answered_buses()                  # the far bus ids heard answering (round 6 of fork PR #897, the reviewer's
        saved = (dict(pm.HEARTBEATS), dict(pm.PEER_STATE), dict(pm.PEERS), _listing_record(), pm._PEERS_SEEDED[0],
                 set(answered))                       # round-5 ruling B): one test's far buses are not another's
        pm.HEARTBEATS.clear(); pm.PEER_STATE.clear(); pm.PEERS.clear(); answered.clear()
        _forget_listing()                             # no listing read yet in this "process": the writer releases nothing
        pm._PEERS_SEEDED[0] = False                   # ...and no seed from the kernel's list of links

        def restore():
            for d, v in zip((pm.HEARTBEATS, pm.PEER_STATE, pm.PEERS, answered), saved[:3] + saved[5:]):
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
        """A restarted bus process's memory: nothing heard yet, no far bus heard answering, no listing read yet, no seed from
        the kernel's list of links yet, the file still on disk."""
        pm.HEARTBEATS.clear(); pm.PEER_STATE.clear(); _answered_buses().clear(); _forget_listing()
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

    def _hub_answers_our_dial(self, dialed, presence, bus_id, answered=True):
        """The dialer's half of one exchange, through the real builder and the real fold (peer_exchange_apply): this bus
        dials `dialed`, whose answer carries `presence`, its bus id `bus_id` and presenceAnswered `answered`, the road a
        hub's answer to our dial takes (round 4 of fork PR #897, the thirty-third commit)."""
        kw = _cap()                                   # the build's capture (round 6 of fork PR #897): taken as the build does
        req = pm.build_exchange_request(dialed, wait=False)
        resp = {"host": dialed, "epoch": 1, "proto": pm.PEER_PROTO, "busId": bus_id, "presence": presence,
                "presenceAnswered": answered, "holds": [], "relays": [], "acks": [], "bounces": [], "reads": [],
                "readsKept": []}
        pm.peer_exchange_apply(dialed, req, resp, **kw)

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

    def test_the_recorders_release_is_keyed_on_its_own_read_whatever_read_lands_before_its_write(self):
        """Round 4 of fork PR #897, the reviewer's ruling on its refuter's narrowing (the thirty-fourth commit): the release is
        keyed on the read that triggered the write. _record_heartbeat hands the sid its own answered read owns to the write
        it makes (`released`), and the writer unions it with the last read (_local_listing_owned) under _REMOTE_SIDS_LOCK.
        Until the commit the write read the last read alone, so a thread-less read landing between the recorder's read,
        which asks for thread rows, and the write taking the lock (the autostop gate's present_count_checked here) owned no
        comment thread's sid: the thread's blink row and its HEARTBEATS entry both stayed, and the thread, told local,
        beat no more (the refuter's race leg). The window is held open by this test holding the lock, and the recorder's
        read is known to have returned by an event set inside the wrapped read, never by a sleep."""
        self.assertTrue(pm.peers_on(), "peer mode, the default this module runs under")
        self._forget_presence_cache()
        self._local_listing_unanswered()                      # a comment thread's beat during a blink: filed
        self.assertFalse(pm._record_heartbeat(D, "web-comment-1"))
        self.assertEqual(self._rows(), {HB + D: (True, False, [D])}, "the thread's blink row")
        self._local_listing_answered([{"id": A, "name": "web"},
                                      {"id": D, "name": "web-comment-1", "thread": True, "parent": A}])
        read_returned = threading.Event()
        real_read = pm.local_agents_checked

        def recorder_read(threads=False):                     # the recorder's read (threads=True) says when it has returned
            got = real_read(threads=threads)
            if threads:
                read_returned.set()
            return got
        pm.local_agents_checked = recorder_read
        self.addCleanup(setattr, pm, "local_agents_checked", real_read)
        answer = []
        beat = threading.Thread(target=lambda: answer.append(pm._record_heartbeat(D, "web-comment-1")), daemon=True)
        with pm._REMOTE_SIDS_LOCK:                            # the write cannot take the lock until this block ends
            beat.start()
            self.assertTrue(read_returned.wait(timeout=30), "the recorder's read returned")
            self.assertEqual(_listing_record(), (True, frozenset({A, D})), "the recorder's read owns the thread")
            self.assertEqual(pm.present_count_checked()[1], True, "the autostop gate's read lands in the window, answered")
            self.assertEqual(_listing_record(), (True, frozenset({A})),
                             "...and, asking for no thread rows, is now the last read: it owns no comment thread's sid")
        beat.join(timeout=30)
        self.assertFalse(beat.is_alive(), "the recorder's write took the lock and returned")
        self.assertEqual(answer, [True], "the recorder answered local")
        self.assertEqual((HB + D in self._rows(), D in pm.HEARTBEATS), (False, False),
                         "THE RULED RELEASE: the write releases the sid the read that triggered it owns, whatever read landed "
                         "last, the row gone from the file and the entry from memory (a write reading the last read alone "
                         "keeps both here: (True, True))")

    def test_the_writers_disclosure_names_every_reader_of_the_forgotten_entry(self):
        """Round 4 of fork PR #897, the thirty-fifth commit (the reviewer's verifier at the thirty-fourth, by execution): the
        _write_remote_sids docstring discloses that forgetting a released HEARTBEATS entry removes the session's presence
        from every reader of it past the mirror, and the thirty-fourth commit's list named three of four (recall's by-name
        lookup, _recip_id_for, was missing). The population is DERIVED here from the source, never listed from memory: the
        functions that read HEARTBEATS, of which _with_remote_presence alone serves the entry to other code, and every
        function that refers to _with_remote_presence directly or through all_agents, whose body is that call. Each reader
        is matched by the name the docstring uses for it; the /agents route's reader is its handler's branch on that path,
        so it is matched by the route. A new reader of either kind fails an equality below until this set and the disclosure are both extended,
        and a reader the disclosure does not name fails the last assertions; the witness of the reach by execution is
        tests/test_postal_heartbeat_fetches.py test_after_the_latch_a_local_peer_is_unreachable_by_name_during_a_blink
        (the send and the recall by name)."""
        import ast
        tree = ast.parse(Path(os.path.realpath(os.path.join(BIN, "romp-postal-service"))).read_text())
        refs = []                                             # (the enclosing function's dotted name, the name, its if-tests)

        def walk(node, scope, branches):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    walk(child, scope + [child.name], [])
                    continue
                if isinstance(child, ast.Name) and child.id in ("HEARTBEATS", "_with_remote_presence", "all_agents"):
                    refs.append((".".join(scope), child.id, branches))
                walk(child, scope, branches + [ast.unparse(child.test)] if isinstance(child, ast.If) else branches)
        walk(tree, [], [])
        readers = lambda name: {s for s, n, _ in refs if n == name and s}
        self.assertEqual(readers("HEARTBEATS"),
                         {"_with_remote_presence", "_record_heartbeat", "_remote_sids_document", "_write_remote_sids"},
                         "the functions that touch the table: the presence reader, the recorder and the mirror's two (a new "
                         "reader of HEARTBEATS is a reader the disclosure must weigh)")
        self.assertEqual(readers("_with_remote_presence"), {"all_agents", "present_count_checked", "_recip_id_for"})
        self.assertEqual(readers("all_agents"), {"_recip_id_for", "resolve_recipient", "Handler.do_GET"})
        route = [b for s, n, b in refs if s == "Handler.do_GET"]
        self.assertEqual(len(route), 1, "one reference in the request handler: %r" % route)
        self.assertIn("u.path == '/agents'", route[0], "the handler's reference sits under the /agents route: %r" % route)
        by_name = {"resolve_recipient": "resolve_recipient", "Handler.do_GET": "the /agents listing",
                   "present_count_checked": "present_count_checked", "_recip_id_for": "_recip_id_for"}
        served = (readers("all_agents") | readers("_with_remote_presence")) - {"all_agents"}
        self.assertEqual(set(by_name), served, "every reader of the served presence has the name the disclosure uses for it")
        doc = " ".join(pm._write_remote_sids.__doc__.split())
        disclosure = doc[doc.index("FORGETTING THE ENTRY REACHES PAST THE MIRROR"):].split(". A send")[0]
        missing = [name for name in by_name.values() if name not in disclosure]
        self.assertEqual(missing, [], "THE DISCLOSURE names every reader of the forgotten entry (the thirty-fourth commit's "
                         "named three, _recip_id_for missing): %r" % disclosure)
        self.assertIn("from all %s" % ("one", "two", "three", "four", "five", "six")[len(by_name) - 1], disclosure,
                      "...and counts them: %r" % disclosure)

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
        busId among the heard rows'), whatever the hub now says about the far host, once this process holds the hub's
        word about that host, as it does here: the declared row was heard in this process, and the fold handed its words
        and marks to the alias's row (a hub heard under the SAME name and silent leaves its via row carried: the standing
        pin above, its silence being a restarted hub's; and a row carried from before this bus's restart, whose word the
        restarted process does not hold, follows the hub to its new name instead, the next test, round 6 of fork PR #897).
        The composition with the reader's verdicts is tests/test_dead_session_staleness.py ReaderFollowsTheWriter (the
        hub's two names phase)."""
        self._local_listing_answered_empty()
        gossip = lambda *sids: [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        via_decl = VIA + HUB_DECL + "/" + FAR
        self._notify(HUB, up=True)                         # the kernel dials the alias; the hub's own dial lands here first
        self._far_dials_us(HUB_DECL, gossip(C, D), "hub-bus")
        self.assertEqual(self._reach(), {HUB_DECL: (True, False, False, True, []), via_decl: (True, False, False, True, [C, D])},
                         "the hub under the name it declared, and its word about the far host under that name")
        self.assertEqual(self._vouch()[via_decl], (True, False, False), "the via row follows the hub's link: none under the declared name")
        pm.peer_exchange_apply(HUB, {}, {"presence": gossip(C), "epoch": 1, "holds": [], "busId": "hub-bus", "presenceAnswered": True}, **_cap())   # our dial lands: D ended
        self.assertEqual(sorted(pm.PEER_STATE), [HUB], "the fold: the declared row left PEER_STATE")
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, []), VIA_FAR: (True, False, False, True, [C])},
                         "THE RULE: the hub's bus is heard under the alias, so its row under the declared name is dropped (the "
                         "busId fold) AND its word under via:<declared>/<far> with it, by the same test; its current word stands "
                         "under via:<alias>/<far> and names C alone, so D, ended on the far host, is in no row while the hub "
                         "vouches: rule 5 (a carry keyed on the via key alone carries the declared name's row heard=false for the "
                         "file's life, and D is cannot-determine by it)")
        self.assertEqual(self._vouch()[VIA_FAR], (True, True, True), "the via row now follows the alias's link: known up")
        pm.peer_exchange_apply(HUB, {}, {"presence": gossip(C), "epoch": 1, "holds": [], "busId": "hub-bus", "presenceAnswered": True}, **_cap())
        self.assertEqual(sorted(self._rows()), sorted([HUB, VIA_FAR]), "and it stays dropped at the hub's next exchange")
        # the same fold with the hub now gossiping NOTHING about the far host: the same bus, its silence under its new name
        # its word (no sessions there), so the declared name's row leaves with the hub's own
        self._restart()
        pm.PEERS.clear()
        self.path.unlink()
        self._notify(HUB, up=True)
        self._far_dials_us(HUB_DECL, gossip(C, D), "hub-bus")
        self.assertEqual(sorted(self._rows()), sorted([HUB_DECL, via_decl]))
        pm.peer_exchange_apply(HUB, {}, {"presence": [], "epoch": 1, "holds": [], "busId": "hub-bus", "presenceAnswered": True}, **_cap())
        self.assertEqual(self._rows(), {HUB: (True, False, []), VIA_FAR: (True, False, [C, D])},
                         "the hub's bus heard under another name: its earlier word under the declared name is dropped whatever it "
                         "now says about the far host, this process holding its word (a carry that keeps it while the hub is "
                         "silent names C and D for the file's "
                         "life; the SAME name silent is the standing pin's carry, a restarted hub that has not heard the host yet). "
                         "The words themselves move to the alias's row HELD (round 6 of fork PR #897): the declared row, never "
                         "dialed by this bus, held the far host's answered word unanswered, so the far bus was never heard "
                         "answering here and the same hub process's omission releases nothing (the reviewer's round-5 rulings B "
                         "and C; costs (a) and (ii))")

    def test_after_our_restart_a_carried_hubs_word_follows_the_hub_to_the_name_its_bus_is_heard_under(self):
        """The rename drop's reach after THIS bus restarts (round 6 of fork PR #897, the reviewer's decision 4 on round 5: no
        release fires from state the restarted bus does not hold; its verifier at the fifty-eighth commit drove the road
        through the real builders, handlers and reader, tests/test_dead_session_staleness.py ReaderFollowsTheWriter
        test_decision_4_after_our_restart_a_hub_dialing_first_under_its_declared_name_leaves_the_far_hosts_carried_word_holding).
        The previous process heard the hub, its bus id on its row, gossip two far hosts: FAR's word unanswered (C), FAR2's
        answered (D). This bus restarts, and the hub's dial lands first under the hostname it declares, naming neither, as
        at every start of this bus (no row carries its bus id yet). A word heard in this process is held at a rename, a
        row heard under the old name having handed its words and marks to the row that stays (the next test). Here the
        restarted process holds neither word, so each carried via row FOLLOWS the hub to the name its bus is heard
        under, carried with its bit: FAR's, False, holds the reader's listing-unanswered arm, and FAR2's names D at
        cannot-determine, as each would under the hub's old name (the carry above). At the fifty-eighth commit the rename
        dropped both, C and D were in no row, and nothing held. This bus's dial to the alias then folds the hub there, and
        the rows follow it back. A carried row already under the new key is ONE source with the moved one: their names
        join and the row is unanswered if either is (a file carrying two rows with one bus id, which this build does not
        write, reaches it)."""
        FAR2 = "TESTHOST-far2"
        word = lambda far, sid, ok: {"id": sid, "name": "api", "via": far, "viaBus": far + "-bus", "viaAnswered": ok}
        via_decl, via_far2, via_decl_far2 = VIA + HUB_DECL + "/" + FAR, VIA + HUB + "/" + FAR2, VIA + HUB_DECL + "/" + FAR2
        self._local_listing_answered_empty()
        self._notify(HUB, up=True)
        self._peer(HUB, [{"id": A, "name": "web"}, word(FAR, C, False), word(FAR2, D, True)], bus_id="hub-bus")
        pm._write_remote_sids()
        self.assertEqual((self._rows(), self._answered()),
                         ({HUB: (True, False, [A]), VIA_FAR: (True, False, [C]), via_far2: (True, False, [D])},
                          {HUB: True, VIA_FAR: False, via_far2: True}), "the previous process: FAR's word unanswered, FAR2's answered")
        self._restart()
        pm.PEERS.clear()
        self._notify(HUB, up=True)
        self._far_dials_us(HUB_DECL, [{"id": A, "name": "web"}], "hub-bus")   # the hub's dial first, under its declared name
        self.assertEqual((self._rows(), self._answered()),
                         ({HUB_DECL: (True, False, [A]), via_decl: (False, False, [C]), via_decl_far2: (False, False, [D])},
                          {HUB_DECL: False, via_decl: False, via_decl_far2: True}),
                         "THE RULE: the restarted process holds neither word, so each carried via row follows the hub to its "
                         "declared name with its bit (at the fifty-eighth commit the rename drop took both: C and D in no row)")
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}], "hub-bus")   # our dial to the alias folds the hub there
        self.assertEqual((self._rows(), self._answered()),
                         ({HUB: (True, False, [A]), VIA_FAR: (False, False, [C]), via_far2: (False, False, [D])},
                          {HUB: True, VIA_FAR: False, via_far2: True}),
                         "the fold: the rows follow the hub back to the alias, each with its bit")
        # ONE SOURCE: a carried row already under the key the moved row takes (two rows with one bus id in the previous file)
        self._restart()
        pm.PEERS.clear()
        self.path.unlink()
        self._peer(HUB, [{"id": A, "name": "web"}, word(FAR, C, True), word(FAR2, D, False)], bus_id="hub-bus")
        self._peer(HUB_DECL, [{"id": A, "name": "web"}, word(FAR, E, False), word(FAR2, B, True)], bus_id="hub-bus")
        pm._write_remote_sids()
        self.assertEqual(self._answered(), {HUB: True, HUB_DECL: True, VIA_FAR: True, via_far2: False, via_decl: False,
                                            via_decl_far2: True},
                         "a crafted state: the hub under both names with one bus id, each far host answered under one name and "
                         "not the other")
        self._restart()
        pm.PEERS.clear()
        self._far_dials_us(HUB_DECL, [{"id": A, "name": "web"}], "hub-bus")
        self.assertEqual((self._rows(), self._answered()),
                         ({HUB_DECL: (True, False, [A]), via_decl: (False, False, [C, E]), via_decl_far2: (False, False, [B, D])},
                          {HUB_DECL: False, via_decl: False, via_decl_far2: False}),
                         "each moved row joins the one carried under its new key: both names kept, and unanswered, since one "
                         "of the two was, whichever (an overwrite loses a name either way, and a bit taken from either row "
                         "alone reads one of the two answered)")

    def test_the_rename_drops_a_hubs_older_word_once_this_process_holds_its_word_by_the_far_hosts_mark_or_bus(self):
        """What "this process holds the hub's word about the far host" is, at the carry's rename (round 6 of fork PR #897,
        the fifty-ninth commit; the test above has the row that follows the hub). Either of two: (1) the hub's row, under
        the name its bus is heard under now, carries the far host's mark (`viaMark`, which a recorder stamps for every far
        host a roster names and the fold hands to the row that stays), which holds even once the word has left the hub's
        roster. Within ONE process: the hub's dial lands first under the name it declares, naming FAR's word; a second
        hub's answer to our dial relays FAR answered, so FAR's bus is heard answering here; our dial to the alias then
        folds the declared row, and the same hub process's answer, placed after FAR's word, omits it: the word is
        released (the reviewer's round-5 rulings B and C), and the via row under the declared name leaves with the
        declared row. A rename test blind to the mark would move that row to the alias still unanswered, holding every
        sid nothing names at cannot-determine after a release. (2) The hub's current word names the far host's bus under
        another far name. After this bus restarts, the hub's dial lands first under its declared name, gossiping FAR's bus
        under the alias it now dials it by: the carried row under the old names leaves, the word standing under the new
        key (a rename test blind to that pair would move the carried row beside it, naming C twice)."""
        HUB2, word = "TESTHOST-hub2", lambda far, sid, ok: {"id": sid, "name": "api", "via": far, "viaBus": "far-bus",
                                                             "viaAnswered": ok}
        via_decl, via_hub2 = VIA + HUB_DECL + "/" + FAR, VIA + HUB2 + "/" + FAR
        self._local_listing_answered_empty()
        self._notify(HUB, up=True)
        self._far_dials_us(HUB_DECL, [{"id": A, "name": "web"}, word(FAR, C, True)], "hub-bus")
        self._hub_answers_our_dial(HUB2, [word(FAR, D, True)], "hub2-bus")   # FAR's bus heard answering here, by a gossip
        self.assertEqual((self._rows(), "far-bus" in _answered_buses()),
                         ({HUB_DECL: (True, False, [A]), via_decl: (True, False, [C]), HUB2: (True, False, []),
                           via_hub2: (True, False, [D])}, True), "FAR's word through the hub under its declared name, held")
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}], "hub-bus")   # our dial to the alias: the fold, FAR omitted
        self.assertEqual(((pm.PEER_STATE.get(HUB) or {}).get("viaHeld"), FAR in ((pm.PEER_STATE.get(HUB) or {}).get("viaMark") or {}),
                          self._rows()),
                         ([], True, {HUB: (True, False, [A]), HUB2: (True, False, []), via_hub2: (True, False, [D])}),
                         "(1) BY THE MARK: FAR's word released, the alias's row keeping its mark, and the via row under the "
                         "declared name gone with the declared row (moved instead, it holds C and every sid nothing names)")
        self._restart()
        pm.PEERS.clear()
        self.path.unlink()
        self._peer(HUB, [{"id": A, "name": "web"}, word(FAR, C, False)], bus_id="hub-bus")
        pm._write_remote_sids()
        self._restart()
        self._far_dials_us(HUB_DECL, [{"id": A, "name": "web"}, word(FAR_ALIAS, C, False)], "hub-bus")
        self.assertEqual(self._rows(), {HUB_DECL: (True, False, [A]), VIA + HUB_DECL + "/" + FAR_ALIAS: (True, False, [C])},
                         "(2) BY THE FAR BUS: after our restart the hub's current word names FAR's bus under another far "
                         "name, so the carried row under the old names leaves (moved instead, it names C under a second key)")

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

    def test_residual_2a_a_hub_restarted_under_a_new_bus_id_and_heard_under_another_name_leaves_its_old_rows_carried(self):
        """The named witness of residual (2a) of the writer's docstring, what no identity in the file reaches (round 4 of fork
        PR #897, the reviewer's ruling on its round-3 refuters' findings, the thirty-sixth commit): a hub restarted under a
        new bus id AND heard under another name. The hub, its bus id on its row, names two sessions on a far host nobody
        holds directly, beside a host X; this bus restarts (the links notified again, every row carried); X is heard with
        its link up and vouches for absence; the hub, its own bus restarted under a new id, dials in under the hostname it
        declares, before this bus's own dial has folded it, naming one of the two (the other ended). Nothing in the file
        ties the two names: the carried row's bus id is the old process's, and the hub's current word pairs the far bus
        with the new name. So the hub's old row and its via row stay carried, heard false, across the hub's exchanges under
        the new name, and the via row still names the ended session: the reader answers cannot-determine for it, named by
        an unreachable host, where rule 5 would otherwise fire (this module runs no reader; these rows fix that verdict).
        The event that ends it is the hub heard under the old name again, this bus's own dial to the name the kernel
        dials, whose fold files the hub's current word there and drops the declared name's rows; a hub never heard under
        the old name again leaves them for the file's life. A carry that drops a carried via row when a heard via row from
        a hub with no link here names the same far bus closes the residual and turns this red (the refuter's M3, which
        passed every module at the round-3 head), and the docstring's residual moves with it. Through the real handler,
        the real builder and fold, and this writer."""
        X = "TESTHOST-x"
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        gossip = lambda *sids: [{"id": A, "name": "web"}] + [{"id": s, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": True} for s in sids]
        via_decl = VIA + HUB_DECL + "/" + FAR
        self._notify(HUB, up=True)
        self._notify(X, up=True)
        self._far_dials_us(HUB, gossip(C, D), "hub-bus-1")
        self._far_dials_us(X, [{"id": E, "name": "tests"}], "x-bus")
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [E]),
                                         VIA_FAR: (True, False, False, True, [C, D])},
                         "the hub's word about the far host, under the hub's name, beside X")
        self._restart()
        pm.PEERS.clear()
        self._notify(HUB, up=True)                         # the kernel's seeds: both links up, nothing heard yet (each writes)
        self._notify(X, up=True)
        self._far_dials_us(X, [{"id": E, "name": "tests"}], "x-bus")   # X heard with its link up; its answer to our dial
        self._hub_answers_our_dial(X, [{"id": E, "name": "tests"}], "x-bus")   # releases its row: it vouches for absence
        for _ in range(2):                                 # the hub, restarted under a new bus id, under its declared name; D ended
            self._far_dials_us(HUB_DECL, gossip(C), "hub-bus-2")
            self.assertEqual(self._reach(), {HUB: (False, False, False, False, [A]), X: (True, False, False, True, [E]),
                                             VIA_FAR: (False, False, False, False, [C, D]),
                                             HUB_DECL: (True, False, False, True, [A]), via_decl: (True, False, False, True, [C])},
                             "RESIDUAL (2a): the hub's old row and its via row stay carried, heard false, and the via row still "
                             "names D, which ended: nothing in the file ties the old name to the new (its bus id is the old "
                             "process's, and the current word pairs the far bus with the new name), so D is named by an "
                             "unreachable host, cannot-determine, where rule 5 would otherwise fire (a carry that drops the old "
                             "via row on a heard via row naming the same far bus from a hub with no link here closes this, and D "
                             "reads rule 5)")
            self.assertEqual((self._vouch()[X], self._answered()[HUB_DECL], self._answered()[via_decl]), ((True, True, True), False, False),
                             "X vouches for absence; the declared-name rows, which this bus never dials, are held (round 6 of fork "
                             "PR #897, the reviewer's round-5 ruling C, cost (ii)), so the arm holds too, beside the carried via row "
                             "that names D")
        self._hub_answers_our_dial(HUB, gossip(C), "hub-bus-2")   # this bus's own dial reaches the hub under the old name
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [E]),
                                         VIA_FAR: (True, False, False, True, [C])},
                         "the event: the fold files the hub's current word under the old name and drops the declared name's rows, "
                         "so D is in no row while the hub and X vouch, rule 5")

    def test_residual_2b_a_hub_stamping_no_viabus_that_renames_a_far_host_leaves_the_old_names_row_carried_and_its_restarts_silence_is_no_word(self):
        """The named witness of residual (2b) of the writer's docstring, what no identity in the file reaches (round 4 of fork
        PR #897, the reviewer's ruling on its round-3 refuters' findings, the thirty-sixth commit): a hub that stamps no
        viaBus renaming a far host. One hub process gossips two sessions on a far host under the hostname the far bus
        declared to it, and one session on a second far host, beside a host X that vouches; its own dial then folds the far
        bus under the alias it dials, and its word names one of the two sessions under the new name (the other ended).
        With no bus id on either word there is nothing to match the two names by: the old name's via row stays carried,
        heard false, naming the ended session, so the reader answers cannot-determine for it where rule 5 would otherwise
        fire. A carry that drops a carried via row with no viaBus when its hub currently gossips any via row closes the
        residual and turns this red (the refuter's M2). The same plant pins the rule the carry keeps for such a hub: a
        restarted hub's silence is not a word. The hub restarts and names the far host again but not yet the second far
        host, whose via row stays carried and names its live session (a carry that drops a no-viaBus hub's carried rows
        once its current gossip carries any no-viaBus word, the refuter's M2b, drops it, the live session is in no row
        while X vouches, and rule 5 presumes it closed; nothing turned red under it at the round-3 head). Every word here
        is answered (viaAnswered True), a pairing no released build sends with an empty viaBus: a far bus from before
        busId predates presenceAnswered too, and a hub from before viaBus stamps neither, so a real old hub's words read
        unanswered and are held, not carried, across its restart
        (test_a_hub_from_before_viabus_renaming_a_far_host_holds_the_old_names_word_within_one_process_and_across_its_restart),
        while the listing-unanswered arm holds every sid (cost (a)). The fixture takes the answered bit so that the carried
        rows alone decide each verdict. Through the real handler and this writer. Each roster by the answer road, where this bus places it after the last (round 6 of fork PR
        #897, the reviewer's round-5 ruling C: a dial merges and releases nothing)."""
        X, FAR2 = "TESTHOST-x", "TESTHOST-far2"
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        web = {"id": A, "name": "web"}
        word = lambda far, *sids: [{"id": s, "name": "api", "via": far, "viaAnswered": True} for s in sids]   # no viaBus
        via_decl, via2 = VIA + HUB + "/" + FAR_DECL, VIA + HUB + "/" + FAR2
        self._notify(HUB, up=True)
        self._notify(X, up=True)
        self._hub_answers_our_dial(X, [{"id": E, "name": "tests"}], "x-bus")
        self._hub_answers_our_dial(HUB, [web] + word(FAR_DECL, C, D) + word(FAR2, B), "hub-bus")
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [E]),
                                         via_decl: (True, False, False, True, [C, D]), via2: (True, False, False, True, [B])},
                         "the hub's word about the far host under the name the far bus declared to it, and about the second far host")
        self.assertEqual({k: r.get("viaBus") for k, r in self._doc()["hosts"].items() if k.startswith(VIA)}, {via_decl: "", via2: ""},
                         "no bus id on either word")
        self._hub_answers_our_dial(HUB, [web] + word(FAR, C) + word(FAR2, B), "hub-bus")   # the same process renames the far host; D ended
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [E]),
                                         via_decl: (False, False, False, False, [C, D]), VIA_FAR: (True, False, False, True, [C]),
                                         via2: (True, False, False, True, [B])},
                         "RESIDUAL (2b): the old name's via row stays carried, heard false, naming D, which ended: with no bus id "
                         "on either word nothing matches the two names, so D is named by an unreachable host, cannot-determine, "
                         "where rule 5 would otherwise fire (a carry that drops a carried via row with no viaBus while its hub "
                         "gossips any via row closes this, and D reads rule 5)")
        self.assertEqual((self._vouch()[X], self._answered()[HUB], self._answered()[VIA_FAR], self._answered()[via2]),
                         ((True, True, True), True, True, True),
                         "X vouches for absence, and every heard row is answered: the carried via row alone keeps D from rule 5")
        self._hub_answers_our_dial(HUB, [web] + word(FAR, C), "hub-bus-2")   # the hub restarted: it has heard the far host, not FAR2 yet
        self.assertEqual(self._reach().get(via2), (False, False, False, False, [B]),
                         "A RESTARTED HUB'S SILENCE IS NOT A WORD, for a hub that stamps no viaBus too: its word about the second "
                         "far host is carried, heard false, and still names B, live there, so B is cannot-determine (a carry that "
                         "drops it once the hub's current gossip carries any no-viaBus word leaves B in no row while X vouches, "
                         "and rule 5 presumes a live session closed)")
        self.assertEqual(self._reach(), {HUB: (True, False, False, True, [A]), X: (True, False, False, True, [E]),
                                         via_decl: (False, False, False, False, [C, D]), VIA_FAR: (True, False, False, True, [C]),
                                         via2: (False, False, False, False, [B])},
                         "...beside the old name's row, still carried, and the hub's current word about the far host")

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
        which no bus since 2026-09-22 writes and a crash can leave, is one too; and so is the JSON literal null, a JSON value
        of neither shape (round 4 of fork PR #897, the thirty-fourth commit: the read tested the value its parse returned,
        None, for a failed parse, and carried the file as a legacy row naming the session "null", with no mark and no line).
        A path the bus cannot open is read directly (a directory there: the write's replace would fail too)."""
        doc = self._own_document()
        v1 = doc.replace('"v": 2', '"v": 1')
        files = (("text that is not JSON, a stray brace", doc.replace('"sids"', '"sids"}', 1).encode(), "JSONDecodeError"),
                 ("the document cut short after a literal the whitespace parser would take for a session id",
                  doc[:doc.index("true") + 4].encode(), "JSONDecodeError"),
                 ("nesting past the parser's depth", ("[" * 100000 + "\n").encode(), None),   # None: derived from the parse
                 ("a JSON list", b"[1, 2]\n", "a JSON list, not a document with a hosts table"),
                 ("the JSON literal null", b"null\n", "a JSON NoneType, not a document with a hosts table"),
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

    def test_the_marks_line_states_the_clearing_rule_of_the_scheme_at_the_write(self):
        """Round 4 of fork PR #897, the reviewer's ruling on its refuter's narrowing (the thirty-fourth commit), and the
        thirty-fifth commit's correction of its legacy line: the bus-log line that says a previous file is unreadable and
        the mirror marked states the mark's clearing rule as the scheme at the write holds it (_remote_sids_lost reads
        peers_on). In peer mode the mark stands until a bus process that read the kernel's list of links at its start has
        heard every linked host since it. Under the legacy singleton scheme, ROMP_POSTAL_PEERS=0, the line states that rule
        for a bus in peer mode and adds that no bus on the legacy scheme clears the mark: the seed does not run there, so a
        legacy process never meets _remote_sids_lost_cleared's first condition. The thirty-fourth commit's legacy line said
        the mark stood for the life of the state root, and the reviewer's verifier showed that false by execution: a bus in
        peer mode over the same root clears it. So this test also drives the rule the legacy line states, through the real
        writer and the real seed: the legacy mark stands across legacy writes and a legacy restart, and a restart into peer
        mode that reads the kernel's list and hears the linked host clears it. Until the thirty-fourth commit the line said
        "until every host the kernel holds a link to is heard" under both schemes, which never holds under the legacy one.
        One unreadable file per scheme, peer mode first (the legacy switch holds until the restart into peer mode)."""
        peer_clause = ("until a bus process that read the kernel's list of links at its start has heard every linked host "
                       "since the mark")
        legacy_clause = ("until a bus process in peer mode that read the kernel's list of links at its start has heard every "
                         "linked host since the mark: this bus runs the legacy singleton scheme (ROMP_POSTAL_PEERS=0), which "
                         "holds no list of links, so no bus on that scheme clears it")
        said = {}
        for scheme in ("peer mode", "the legacy scheme"):
            with self.subTest(scheme=scheme):
                if scheme == "the legacy scheme":
                    self._legacy_scheme()
                else:
                    self.assertTrue(pm.peers_on(), "peer mode, the default this module runs under")
                self.path.write_text("{not json\n")
                pm.HEARTBEATS.clear()
                pm.HEARTBEATS[A] = ("web", self.now)
                lines = [ln for ln in self._write_saying() if "previous remote-sids mirror" in ln]
                self.assertEqual(len(lines), 1, "said once: %r" % lines)
                self.assertIsNotNone(self._mark(), "the document is marked")
                said[scheme] = lines[0]
        self.assertTrue(said.get("the legacy scheme", "").endswith(", " + legacy_clause),
                        "THE LEGACY LINE: the peer-mode rule, and no bus on the legacy scheme clears the mark (the thirty-fourth "
                        "commit's line said the mark stood for the life of the state root, false once a bus in peer mode runs "
                        "over the root; until that commit it said the mark stood until every host the kernel holds a link to "
                        "is heard): %r" % said.get("the legacy scheme"))
        self.assertTrue(said.get("peer mode", "").endswith(", " + peer_clause),
                        "the peer-mode line states the clearing rule of _remote_sids_lost_cleared: %r" % said.get("peer mode"))
        # THE RULE THE LEGACY LINE STATES, by execution: the legacy mark (the last write above) stands while buses on the
        # legacy scheme write, a restarted one included, and clears once a bus in peer mode over the same root has read the
        # kernel's list of links at its start and heard every linked host since the mark
        mark = self._mark()
        self.assertFalse(pm.peers_on(), "still the legacy scheme")
        pm.HEARTBEATS[A] = ("web", pm.time.time())
        pm._write_remote_sids()
        self.assertEqual(self._mark(), mark, "a legacy write, a beat heard: the mark stands")
        self._restart()
        pm.HEARTBEATS[B] = ("api", pm.time.time())
        pm._write_remote_sids()
        self.assertEqual(self._mark(), mark, "a restarted legacy bus, a beat heard: the mark stands, carried")
        self._restart()                                       # the root's next bus runs in peer mode
        os.environ.pop("ROMP_POSTAL_PEERS", None)             # (put back as found by _legacy_scheme's cleanup)
        self.assertTrue(pm.peers_on(), "peer mode, the default")
        self.assertTrue(self._seed([(HOST, "up")]), "the peer-mode bus read the kernel's list of links at its start")
        self.assertEqual(self._mark(), mark, "the linked host not heard since the mark: it stands")
        self._peer(HOST, [{"id": B, "name": "api"}])
        pm.PEER_STATE[HOST]["seenAt"] = int(pm.time.time())   # the exchange's own stamp, at or after the mark's second
        cleared = [ln for ln in self._write_saying() if "lost-carry mark" in ln]
        self.assertIsNone(self._mark(), "THE LEGACY MARK IS CLEARED by a bus in peer mode that read the list and heard every "
                          "linked host since it, as the legacy line says (the thirty-fourth commit's 'for the life of the state "
                          "root' is false here, the reviewer's verifier's road)")
        self.assertEqual(len(cleared), 1, "the clear said once: %r" % cleared)
        self.assertIn("cleared", cleared[0])

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
                                                      for s in far_sids]}, **_cap())
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
        mark, and every session its lost rows named would answer rule 5). The carry's shape check is pinned on every
        conjunct of "an int from 1970 through the year 9999" (round 4 of fork PR #897, the thirty-fourth commit): a second
        before 1970, a float second and a bool second are each re-stamped, and each row is red under its own mutant (the
        lower bound dropped; a float accepted; a bool accepted by an isinstance test), which passed every pin until then."""
        base = json.loads(self._own_document())
        for name, mark, data_of, expect in (
                ("a mark as written", {"cause": "earlier", "at": 7}, lambda t: t.encode(), {"cause": "earlier", "at": 7}),
                ("a mark of another shape", "x", lambda t: t.encode(), None),
                ("a mark whose second is past the year 9999", {"cause": "earlier", "at": 10 ** 20}, lambda t: t.encode(), None),
                ("a mark whose second is before 1970", {"cause": "earlier", "at": -1}, lambda t: t.encode(), None),
                ("a mark whose second is a float", {"cause": "earlier", "at": 1.5}, lambda t: t.encode(), None),
                ("a mark whose second is a bool", {"cause": "earlier", "at": True}, lambda t: t.encode(), None),
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
                    self.assertTrue(before <= got["at"] <= after, "re-stamped at the write's second (%s: a mark whose second is "
                                    "not an int from 1970 through the year 9999, carried as written, is refused by the judge's "
                                    "reader, so every sid answers mirror-unparsable until it clears, and a second past the year "
                                    "9999 fails the clearing's log line): %r" % (name, got))
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
        pm.peer_exchange_apply(HOST, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "presenceAnswered": True}, **_cap())
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
        pm.peer_exchange_apply(alias, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "busId": "bus-c", "presenceAnswered": True}, **_cap())
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
                                           "holds": [], "busId": "bus-c", "presenceAnswered": True}, **_cap())
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
        carries an answered listing, the event. A payload lacking the field, an older peer's, or carrying any value but JSON
        true (TRUTHY_NOT_TRUE: a string, which bool() reads True, and the numbers 1 and 1.0, which == True reads True),
        reads unanswered at both recorders (the dialer's fold pinned for a string since the thirty-fourth commit, and both
        recorders for the numbers since the thirty-fifth, round 4 of fork PR #897): the restricted side, so no older peer
        reopens the road. One module plays both buses here: the
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
        dial_held = (self._vouch()[X], pm.PEER_STATE[X].get("presenceAnswered"))
        self._hub_answers_our_dial(X, [{"id": B, "name": "api"}], "x-bus")   # X's answer to our dial releases its row
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
        self.assertEqual(dial_held, ((True, True, False), False),
                         "X's answered DIAL, its first roster in this process, holds its row (round 6 of fork PR #897, the "
                         "reviewer's round-5 ruling C and its decision 4): presence alone")
        self.assertEqual(answered_row, ((True, False, False, True, [B]), (True, True, True), True, True),
                         "released by X's answer to our dial: it vouches for presence and absence, the recorder's bit True")
        # the event: X's next exchange with an answered listing, which now names the session started during the blink
        self._local_listing_answered([{"id": B, "name": "api"}, {"id": C, "name": "tests"}])
        req = x_dials_us()
        self.assertEqual(req.get("presenceAnswered"), True)
        self.assertEqual((self._reach()[X], self._vouch()[X], self._answered()[X]),
                         ((True, False, False, True, [B, C]), (True, True, False), False),
                         "X's answered DIAL names the session and holds the row: a dial releases nothing (round 6 of fork "
                         "PR #897, the reviewer's round-5 ruling C)")
        self._hub_answers_our_dial(X, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "x-bus")
        self.assertEqual((self._reach()[X], self._vouch()[X], self._answered()[X]),
                         ((True, False, False, True, [B, C]), (True, True, True), True),
                         "released by X's answer to our dial built after its cached roster, on that write and nothing else: "
                         "no grace period")
        # the dialer's half, the same road: OUR response, built by the real handler while OUR listing does not answer,
        # folded by the real dialer's fold as X's word
        self._local_listing_unanswered()
        resp = self._far_dials_us(X, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "x-bus")
        self.assertEqual((resp.get("presenceAnswered"), [a["id"] for a in resp["presence"]]), (False, [B, C]),
                         "the response builder rides the bit too: the last answered rows, marked a cache")
        pm.peer_exchange_apply(X, {}, resp, **_cap())
        self.assertIs(pm.PEER_STATE[X].get("presenceAnswered"), False, "the dialer's fold keeps it on the row")
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "recorded by the dialer's fold: presence alone (a fold that drops the bit leaves the row unanswered "
                         "for good, or, defaulting it, answered over a cache)")
        self._local_listing_answered([{"id": B, "name": "api"}, {"id": C, "name": "tests"}])
        resp = self._far_dials_us(X, [{"id": B, "name": "api"}, {"id": C, "name": "tests"}], "x-bus")
        self.assertEqual(resp.get("presenceAnswered"), True)
        pm.peer_exchange_apply(X, {}, resp, **_cap())
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, True), True), "the answering response releases it")
        # the default for a payload without the field (a peer from before it), and for one that spells it as anything but
        # JSON true
        self._far_dials_us(X, [{"id": B, "name": "api"}], "x-bus", answered=None)
        self.assertIs(pm.PEER_STATE[X].get("presenceAnswered"), False, "no field: recorded as unanswered")
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "THE DEFAULT: a payload lacking the field reads unanswered, the restricted side, so an older peer's "
                         "roster vouches for presence alone (a recorder defaulting to answered lets an older peer reopen the road)")
        for junk in TRUTHY_NOT_TRUE:                          # each after an answered exchange, so the pin reads a transition
            with self.subTest(reader="the handler's recorder", presenceAnswered=junk):
                self._hub_answers_our_dial(X, [{"id": B, "name": "api"}], "x-bus")   # released first, so the pin reads a transition
                self.assertEqual(self._answered()[X], True)
                self._far_dials_us(X, [{"id": B, "name": "api"}], "x-bus", answered=junk)
                self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                                 "JSON true alone counts: %r is not it (bool() reads the string True, == True reads 1 and 1.0 "
                                 "True; the numbers since the thirty-fifth commit, round 4 of fork PR #897)" % (junk,))
                self.assertIs(pm.PEER_STATE[X].get("presenceAnswered"), False, "the handler records %r as unanswered" % (junk,))
        pm.peer_exchange_apply(X, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [], "busId": "x-bus"}, **_cap())
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "the same default in the dialer's fold: a response lacking the field is unanswered")
        for junk in TRUTHY_NOT_TRUE:
            with self.subTest(reader="the dialer's fold", presenceAnswered=junk):
                pm.peer_exchange_apply(X, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [],
                                               "busId": "x-bus", "presenceAnswered": True}, **_cap())
                self.assertEqual(self._answered()[X], True)
                pm.peer_exchange_apply(X, {}, {"presence": [{"id": B, "name": "api"}], "epoch": 1, "holds": [],
                                               "busId": "x-bus", "presenceAnswered": junk}, **_cap())
                self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                                 "JSON true alone counts in the dialer's fold too: %r is not it (round 4 of fork PR #897: a fold "
                                 "reading bool() of the field passed every pin until the thirty-fourth commit, one reading == "
                                 "True every pin until the thirty-fifth)" % (junk,))
                self.assertIs(pm.PEER_STATE[X].get("presenceAnswered"), False,
                              "the dialer's fold records %r as unanswered" % (junk,))
        self._far_dials_us(X, [{"id": B, "name": "api"}], "x-bus", answered=True)
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, False), False),
                         "an answered DIAL after the unanswered rosters holds the row")
        self._hub_answers_our_dial(X, [{"id": B, "name": "api"}], "x-bus")
        self.assertEqual((self._vouch()[X], self._answered()[X]), ((True, True, True), True),
                         "and the answer to our dial built after them releases it")

    def test_a_via_row_carries_the_far_hosts_answered_bit_and_not_the_hubs(self):
        """A hub's gossip about a far host is that host's roster as it reported it to the hub, so whether that roster was an
        answered listing is the far host's word, not the hub's (round 3 of fork PR #897, the reviewer's refuters' scope):
        presence_payload stamps every gossiped row with the far host's `presenceAnswered` as its exchange recorded it
        (`viaAnswered`), and the writer's via row takes that bit. A hub whose own listing did not answer still relays a
        far host's answered roster whole, and a hub that answered relays a far host's cache as a cache. An element
        without the field, a hub from before it, reads unanswered, and so does one whose field is not JSON true
        (TRUTHY_NOT_TRUE: a string since the thirty-fourth commit, the numbers 1 and 1.0 since the thirty-fifth, round 4 of
        fork PR #897) and a row one of whose elements lacks it. This
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
        self.assertEqual([pa.get("viaAnswered") for pa in pm.presence_payload(HOST)[0] if pa.get("via")], [False],
                         "the far host's answered DIAL holds its row (round 6 of fork PR #897, the reviewer's round-5 ruling C: "
                         "the held state is what the row stores), so our gossip still says a cache")
        self._hub_answers_our_dial(FAR, [{"id": C, "name": "tests"}], "far-bus", answered=True)
        gossip_answered = [pa for pa in pm.presence_payload(HOST)[0] if pa.get("via")]
        self.assertEqual([pa.get("viaAnswered") for pa in gossip_answered], [True],
                         "...and True once the far host's answer to our dial releases its row")
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
        for junk in TRUTHY_NOT_TRUE:                          # each after an answered relay, so the pin reads a transition
            with self.subTest(reader="the writer's read of viaAnswered", viaAnswered=junk):
                self._peer(HUB, [{"id": A, "name": "web"}, {"id": C, "name": "tests", "via": FAR, "viaBus": "far-bus",
                                                           "viaAnswered": True}], via_answered=None)
                pm._write_remote_sids()
                self.assertEqual(self._answered()[VIA_FAR], True)
                self._peer(HUB, [{"id": A, "name": "web"}, {"id": C, "name": "tests", "via": FAR, "viaBus": "far-bus",
                                                           "viaAnswered": junk}], via_answered=None)
                pm._write_remote_sids()
                self.assertEqual((self._vouch()[VIA_FAR], self._answered()[VIA_FAR]), ((True, True, False), False),
                                 "JSON true alone counts at the writer's read of viaAnswered: %r on the gossiped row is not it "
                                 "(round 4 of fork PR #897: a writer reading bool() of it passed every pin until the thirty-fourth "
                                 "commit, one reading == True, which reads 1 and 1.0 True, every pin until the thirty-fifth)"
                                 % (junk,))
        self._peer(HUB, [{"id": A, "name": "web"}, {"id": C, "name": "tests", "via": FAR, "viaBus": "far-bus", "viaAnswered": True},
                         {"id": D, "name": "api", "via": FAR, "viaBus": "far-bus"}], via_answered=None)
        pm._write_remote_sids()
        self.assertEqual((self._reach()[VIA_FAR][4], self._answered()[VIA_FAR]), ([C, D], False),
                         "every element about the host must carry the bit for the row to be answered")

    def test_a_hubs_held_word_about_a_far_host_stays_heard_until_the_hub_names_that_host_again(self):
        """Round 4 of fork PR #897, the thirty-first commit (the reviewer's verifier at the thirtieth, by execution): a far
        host's UNANSWERED word through a hub stays on the hub's row (`viaHeld`, _via_held) when the hub's next roster omits
        the host (a restarted hub has not heard it yet), and this writer files it as the hub's word, heard in this process,
        unanswered, so the reader's listing-unanswered arm keeps holding; each held row carries the second its word was
        last heard (`heldAt`), which the via row's seenAt reads. The hub's word naming the host again releases it, under
        the hub's name for the host or under a new name by the host's bus id (the hub's own fold). A word whose bit was
        True is NOT held: carried, heard false, as before. Through the real builder and fold of this bus's dial (the answer road, where this bus places each of the hub's rosters after the last: round 6 of fork PR #897, the reviewer's round-5 ruling C; the hub's dials merge and release nothing) and this writer."""
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        self._notify(HUB, up=True)
        far_cached = {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": False}
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, far_cached], "hub-bus")
        self.assertEqual((self._rows()[VIA_FAR], self._answered()[VIA_FAR]), ((True, False, [B]), False),
                         "the hub's word about FAR, the far host's cache: heard, unanswered")
        pm.PEER_STATE[HUB]["seenAt"] -= 100                                 # that exchange landed 100 s before the next
        first_seen = pm.PEER_STATE[HUB]["seenAt"]
        for _ in range(2):                                                  # the hub's bus restarted; then its next exchange
            self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}], "hub-bus-restarted")
            self.assertEqual((self._rows()[VIA_FAR], self._answered()[VIA_FAR]), ((True, False, [B]), False),
                             "HELD: the hub's roster omits FAR, and the far host's unanswered word stays heard (until the "
                             "thirty-first commit carried: (False, False, [B]), out of the arm)")
            self.assertEqual([(pa["id"], pa["via"], pa.get("heldAt")) for pa in pm.PEER_STATE[HUB]["viaHeld"]],
                             [(B, FAR, first_seen)], "the hub's row keeps the word, stamped with the second it was heard")
            self.assertEqual(self._doc()["hosts"][VIA_FAR]["seenAt"], first_seen,
                             "the via row's seenAt is the held word's second, not the hub's later exchange")
            self.assertNotIn(FAR, [pa.get("via") for pa in pm.PEER_STATE[HUB]["presence"]],
                             "the display and routing roster is the hub's word alone")
        for junk in ([{"id": A, "name": "web"}, "not an object"], {"not": "a list"}, 5):   # rosters in shapes no bus sends
            err = io.StringIO()
            with contextlib.redirect_stderr(err):                           # (the writer's own read of them is not under test)
                self._hub_answers_our_dial(HUB, junk, "hub-bus-restarted")          # the exchange still lands: 200
            self.assertEqual([(pa["id"], pa["via"]) for pa in pm.PEER_STATE[HUB]["viaHeld"]], [(B, FAR)],
                             "a roster in a shape no bus sends names no far host, and the recorder, reading what it can, keeps "
                             "the held word (%r)" % (junk,))
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, dict(far_cached, via=FAR_ALIAS, id=C, viaAnswered=True)],
                           "hub-bus-restarted")                             # the hub now calls the far bus FAR_ALIAS
        self.assertEqual(pm.PEER_STATE[HUB]["viaHeld"], [], "the hub's word names the far bus again: the held word is released")
        self.assertNotIn(VIA_FAR, self._rows(), "...and the old name's row is gone (the carry's drop by the hub's current word)")
        self.assertEqual((self._rows()[VIA + HUB + "/" + FAR_ALIAS], self._answered()[VIA + HUB + "/" + FAR_ALIAS]),
                         ((True, False, [C]), True))
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}], "hub-bus-restarted-again")   # an ANSWERED word the hub omits
        self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._rows()[VIA + HUB + "/" + FAR_ALIAS]), ([], (False, False, [C])),
                         "a word whose bit was True is not held: carried, heard false, vouching for nothing")
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, far_cached], "hub-bus-restarted-again")
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, dict(far_cached, viaAnswered=True)], "hub-bus-restarted-again")
        self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._answered()[VIA_FAR]), ([], True),
                         "the hub's word naming the host under the same name, answered: the release")
        no_bus = dict(far_cached, viaBus="")                                # a far bus that sends no bus id: the hub stamps ""
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, no_bus], "hub-bus-restarted-again")
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}], "hub-bus-restarted-thrice")
        self.assertEqual([(pa["id"], pa["via"]) for pa in pm.PEER_STATE[HUB]["viaHeld"]], [(B, FAR)], "held, with no bus id")
        self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, dict(no_bus, viaAnswered=True)], "hub-bus-restarted-thrice")
        self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._answered()[VIA_FAR]), ([], True),
                         "with no bus id on either word the hub's name for the host is the only match, and it releases")
        for n, junk in enumerate(TRUTHY_NOT_TRUE):            # each from a released, answered word, so the pin reads a transition
            with self.subTest(reader="the held-word read", viaAnswered=junk):
                hub_bus = "hub-bus-junk-%d" % n
                self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, dict(far_cached, viaAnswered=True)], hub_bus)
                self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._answered()[VIA_FAR]), ([], True),
                                 "a new hub process names the host, answered: nothing held (whatever an earlier subtest left)")
                self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, dict(far_cached, viaAnswered=junk)], hub_bus)
                self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}], hub_bus + "-restarted")
                self.assertEqual([(pa["id"], pa["via"]) for pa in pm.PEER_STATE[HUB]["viaHeld"]], [(B, FAR)],
                                 "a word whose viaAnswered is %r is not an answered word: held when a restarted hub omits the "
                                 "host (round 4 of fork PR #897: the recorder reading bool() of it carried a string's word heard "
                                 "false, out of the arm, and passed every pin until the thirty-fourth commit; one reading == True, "
                                 "which reads 1 and 1.0 True, every pin until the thirty-fifth)" % (junk,))
                self.assertEqual((self._rows()[VIA_FAR], self._answered()[VIA_FAR]), ((True, False, [B]), False),
                                 "...and written heard, unanswered")
                self._hub_answers_our_dial(HUB, [{"id": A, "name": "web"}, dict(far_cached, viaAnswered=True)], hub_bus + "-restarted")
                self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._answered()[VIA_FAR]), ([], True),
                                 "the restarted hub names the host again, answered: released")

    def test_a_hubs_held_word_is_released_by_the_same_hub_process_omitting_a_far_host_heard_answering_and_held_by_a_hub_that_cannot_say(self):
        """Round 4 of fork PR #897, the thirty-second commit (the reviewer's verifier at the thirty-first, by execution),
        named test_a_hubs_held_word_is_released_by_the_same_hub_process_omitting_the_host_and_held_by_a_hub_that_cannot_say
        until round 6, when the reviewer's round-5 ruling B scoped the release to a far bus heard answering in this process.
        A hub gossips a far host only through that host's session rows, so the far host's answer with an EMPTY listing
        reaches here as the hub's roster omitting the host. The SAME hub process (the bus id its exchanges carry, minted
        per process) omitting a host whose unanswered word its roster named has recorded the host's next exchange, so the
        word is released, carried heard false, when the far bus has been heard answering here (_ANSWERED_BUSES); at the
        thirty-first commit it stayed held for this bus process's life. A far bus never heard answering keeps its word
        held on that omission (the ruling B: a far bus from before the blink honesty gossips an empty roster at its
        kernel's blink, which the omission cannot tell from the answer; at the forty-ninth commit released). A RESTARTED
        hub (a new bus id) omitting it has not heard the host yet, so the word stays held, and it keeps the process that
        last named it (`hubBus`) across the restarted hub's later exchanges, so a second omission by the restarted process
        holds it too. A hub that sends no bus id (from before busId) cannot say it is the same process, so its omission
        holds (the restricted side; cost (g) of the writer's docstring names it). Through the real builder and fold of
        this bus's dial (the answer road, where this bus places each of the hub's rosters after the last: round 6 of fork
        PR #897, the reviewer's round-5 ruling C, which moves the release to that road; the hub's dials merge and release
        nothing) and this writer."""
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        self._notify(HUB, up=True)
        web = {"id": A, "name": "web"}
        far_cached = {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": False}
        self._hub_answers_our_dial(HUB, [web, far_cached], "hub-bus")
        self.assertEqual((self._rows()[VIA_FAR], self._answered()[VIA_FAR]), ((True, False, [B]), False))
        self._hub_answers_our_dial(HUB, [web], "hub-bus")                           # the same hub process: a far bus never heard answering
        self.assertEqual(([(pa["id"], pa["via"], pa.get("hubBus")) for pa in pm.PEER_STATE[HUB]["viaHeld"]], self._rows()[VIA_FAR]),
                         ([(B, FAR, "hub-bus")], (True, False, [B])),
                         "HELD: the same hub process omits FAR, but FAR's bus has not been heard answering here, so the "
                         "omission may be an older far bus's blink (at the forty-ninth commit released: ([], (False, False, [B])))")
        self._hub_answers_our_dial(HUB, [web, far_cached], "hub-bus-2")             # the hub, restarted, names FAR over its cache
        self._hub_answers_our_dial(HUB, [web], "hub-bus-3")                         # ...restarted again: it has not heard FAR
        self.assertEqual([(pa["id"], pa["via"], pa.get("hubBus")) for pa in pm.PEER_STATE[HUB]["viaHeld"]], [(B, FAR, "hub-bus-2")],
                         "HELD across the hub's restart, stamped with the hub process whose roster last named it")
        self._hub_answers_our_dial(HUB, [web], "hub-bus-3")                         # the restarted process's next exchange
        self.assertEqual(([(pa["id"], pa["via"], pa.get("hubBus")) for pa in pm.PEER_STATE[HUB]["viaHeld"]], self._rows()[VIA_FAR]),
                         ([(B, FAR, "hub-bus-2")], (True, False, [B])),
                         "still HELD: the process that omits FAR is not the one that named it (a stamp refreshed at each "
                         "exchange would release the word here, with no word from the far host)")
        self._hub_answers_our_dial(HUB, [web, dict(far_cached, viaAnswered=True)], "hub-bus-3")
        self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._answered()[VIA_FAR], "far-bus" in _answered_buses()),
                         ([], True, True), "named again, answered: released, and FAR's bus is now heard answering")
        self._hub_answers_our_dial(HUB, [web, far_cached], "hub-bus-3")             # FAR's cache again, then the same process omits it
        self._hub_answers_our_dial(HUB, [web], "hub-bus-3")
        self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._rows()[VIA_FAR]), ([], (False, False, [B])),
                         "RELEASED: the same hub process omits FAR, a far bus heard answering, the far host's empty answer; "
                         "the word is carried, heard false (at the thirty-first commit held: ([(B, FAR)], (True, False, [B])))")
        self._hub_answers_our_dial(HUB, [web, far_cached], "")                      # a hub that sends no bus id
        self._hub_answers_our_dial(HUB, [web], "")
        self.assertEqual(([(pa["id"], pa["via"]) for pa in pm.PEER_STATE[HUB]["viaHeld"]], self._rows()[VIA_FAR]),
                         ([(B, FAR)], (True, False, [B])),
                         "HELD: a hub with no bus id cannot say it is the process that named FAR (two empty ids are no "
                         "identity)")

    def test_a_hubs_held_word_is_released_only_by_an_answer_placed_after_it_and_only_for_a_far_bus_heard_answering(self):
        """Named test_a_hubs_held_word_is_released_on_the_road_that_named_it_whatever_bus_id_the_far_host_carries from the
        thirty-third commit and test_a_hubs_held_word_is_released_on_the_road_that_named_it_only_for_a_far_bus_heard_answering
        from round 6's fifty-fourth commit, until round 6's C commit (the reviewer's round-5 ruling C and its decision 1,
        ONE RELEASE RULE). The same hub process's omission of a far host releases its held word only in the hub's answer
        to a dial this bus built after it recorded the host's last unanswered word, the one exact order it has on the
        hub's rosters, whatever road named the host (the road rule of the thirty-third commit, `hubRoad`, released on the
        naming road and held on the other); the hub's dial, and an answer to a dial built before that word, merge and
        release nothing. And only for a far bus heard answering in this process (the reviewer's round-5 ruling B), heard
        on a roster this bus has released, so a word with no viaBus, and a word whose viaBus has never answered here,
        stay held on every omission. For each far host: the hub's answer to our dial relays FAR's answered word first
        where FAR is to be heard answering; the hub's DIAL names FAR's cached word; our dial is built; the hub's next DIAL
        omits FAR (merged, the word kept in the hub's roster, held); the answer to our dial built BEFORE the cached word
        omits FAR (merged, held); the answer to our dial built after it omits FAR: released for a far bus heard answering,
        held in the hub's held words for any other. Through the real handler, the real builder and fold, and this
        writer."""
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        self._notify(HUB, up=True)
        web = {"id": A, "name": "web"}
        omitting = {"host": HUB, "epoch": 1, "proto": pm.PEER_PROTO, "busId": "hub-bus", "presence": [web],
                    "presenceAnswered": True, "holds": [], "relays": [], "acks": [], "bounces": [], "reads": [], "readsKept": []}
        for label, far_cached, heard in (
                ("heard answering", {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": False}, True),
                ("never heard answering", {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus-never", "viaAnswered": False}, False),
                ("with no viaBus", {"id": B, "name": "api", "via": FAR, "viaBus": "", "viaAnswered": False}, False)):
            with self.subTest(far=label):
                if heard:                                                       # the hub's answer relays FAR's answered word first
                    self._hub_answers_our_dial(HUB, [web, dict(far_cached, viaAnswered=True)], "hub-bus")
                early = _cap()                                                  # our dial built BEFORE the cached word is recorded
                self._far_dials_us(HUB, [web, far_cached], "hub-bus")           # the hub's DIAL names FAR's cached word
                self.assertEqual((self._rows()[VIA_FAR], self._answered()[VIA_FAR]), ((True, False, [B]), False))
                self._far_dials_us(HUB, [web], "hub-bus")                       # the hub's next DIAL omits FAR: merged
                self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._rows()[VIA_FAR], self._answered()[VIA_FAR]),
                                 ([], (True, False, [B]), False),
                                 "HELD by the dial: the word stays in the hub's merged roster, unanswered (at the forty-ninth "
                                 "commit released on this road for a far bus heard answering)")
                pm.peer_exchange_apply(HUB, {}, dict(omitting), **early)        # the answer to the dial built before the word
                self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._rows()[VIA_FAR]), ([], (True, False, [B])),
                                 "HELD by an answer this bus cannot place after the word: merged")
                self._hub_answers_our_dial(HUB, [web], "hub-bus")               # the answer to a dial built after the word omits FAR
                if heard:
                    self.assertEqual((pm.PEER_STATE[HUB]["viaHeld"], self._rows()[VIA_FAR]), ([], (False, False, [B])),
                                     "RELEASED: the same hub process's answer, placed after FAR's cached word, omits it")
                else:
                    self.assertEqual(([(pa["id"], pa["via"], pa.get("hubBus")) for pa in pm.PEER_STATE[HUB]["viaHeld"]],
                                      self._rows()[VIA_FAR]), ([(B, FAR, "hub-bus")], (True, False, [B])),
                                     "HELD on the answer road as well: FAR's word is not a far bus heard answering, and it moves "
                                     "to the held words")
                    self._hub_answers_our_dial(HUB, [web, dict(far_cached, viaAnswered=True)], "hub-bus")   # names FAR again
                self._hub_answers_our_dial(HUB, [web], "hub-bus")               # (a clean row for the next far host)

    def test_a_far_bus_is_heard_answering_by_its_own_answer_here_or_by_a_hubs_gossip_this_bus_released_and_by_json_true_alone(self):
        """Round 6 of fork PR #897, the reviewer's round-5 ruling B, with ruling C: this bus remembers the far bus ids it has
        heard answer in this process (_ANSWERED_BUSES, filled by _heard_answering from each recorder's STORED row): a far
        bus's own row carrying presenceAnswered True and its busId, or a gossip row carrying viaAnswered True and that
        viaBus, from any hub. The stored row is what every reader reads, so a roster this bus holds (a dial, which it
        cannot place after its row's last unanswered roster, nor, in this process, after its start) stores its bits False
        and notes nothing: the far bus's own answered DIAL, or a hub's DIAL relaying its answered word, is not yet heard
        answering; the answer to this bus's dial, placed, is (named ..._by_its_own_exchange_here_or_by_any_hubs_gossip_on_either_road_and_by_json_true_alone
        until ruling C's commit, when either road counted). _via_held's release by the same hub process's omission needs
        the omitted word's viaBus there: HUB's dial names that far bus's cached word, and the same HUB process's answer to
        our dial, built after it, omits it: released for a far bus heard answering, held for any other. A far bus whose
        own row carried presenceAnswered False, or whose bit, on its exchange or on a gossip row, is a value other than
        JSON true, is not heard answering, and its word stays held."""
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        self._notify(HUB, up=True)
        web, hub2 = {"id": A, "name": "web"}, "TESTHOST-hub2"

        def omitted(far, bus):                                              # HUB's dial names the far bus's cached word, then
            self._far_dials_us(HUB, [web, {"id": B, "name": "api", "via": far, "viaBus": bus, "viaAnswered": False}], "hub-bus")
            self._hub_answers_our_dial(HUB, [web], "hub-bus")               # the same HUB process's answer to our dial omits it
            return [(pa["id"], pa["via"]) for pa in pm.PEER_STATE[HUB]["viaHeld"] if pa.get("via") == far]

        def gossip(far, bus, answered):                                     # a gossip row about `far`, its bit as `answered`
            return {"id": D, "name": "docs", "via": far, "viaBus": bus, "viaAnswered": answered}

        self._far_dials_us("TESTHOST-far1", [{"id": C, "name": "tests"}], "far1-bus", answered=True)
        self.assertEqual("far1-bus" in _answered_buses(), False,
                         "the far bus's own answered DIAL holds its row (its first roster here): not heard answering")
        self._hub_answers_our_dial("TESTHOST-far1", [{"id": C, "name": "tests"}], "far1-bus", answered=True)
        self.assertEqual(omitted("TESTHOST-far1", "far1-bus"), [],
                         "RELEASED: the far bus's own answer to our dial carried presenceAnswered True and its bus id")
        self._far_dials_us(hub2, [gossip("TESTHOST-far2", "far2-bus", True)], "hub2-bus")
        self.assertEqual("far2-bus" in _answered_buses(), False,
                         "another hub's DIAL relaying the far bus's answered word: held here, not heard answering")
        self._hub_answers_our_dial(hub2, [gossip("TESTHOST-far2", "far2-bus", True)], "hub2-bus")
        self.assertEqual(omitted("TESTHOST-far2", "far2-bus"), [],
                         "RELEASED: another hub's answer to our dial carried the far bus's answered bit")
        self._hub_answers_our_dial(hub2, [gossip("TESTHOST-far3", "far3-bus", True)], "hub2-bus")
        self.assertEqual(omitted("TESTHOST-far3", "far3-bus"), [],
                         "RELEASED: another hub's answer to our dial carried the far bus's answered bit, its first word here")
        self._far_dials_us("TESTHOST-far4", [{"id": C, "name": "tests"}], "far4-bus", answered=False)
        self._hub_answers_our_dial("TESTHOST-far4", [{"id": C, "name": "tests"}], "far4-bus", answered=False)
        self._far_dials_us(hub2, [gossip("TESTHOST-far4", "far4-bus", False)], "hub2-bus")
        self._hub_answers_our_dial(hub2, [gossip("TESTHOST-far4", "far4-bus", False)], "hub2-bus")
        self.assertEqual(omitted("TESTHOST-far4", "far4-bus"), [(B, "TESTHOST-far4")],
                         "HELD: the far bus's own exchanges and a hub's gossip each carried its bit False (at the forty-ninth "
                         "commit released)")
        for n, junk in enumerate(TRUTHY_NOT_TRUE):
            with self.subTest(reader="the answered-bus read", bit=junk):
                far, bus = "TESTHOST-far-junk-%d" % n, "far-junk-%d-bus" % n
                self._far_dials_us(far, [{"id": C, "name": "tests"}], bus, answered=junk)
                self._hub_answers_our_dial(far, [{"id": C, "name": "tests"}], bus, answered=junk)
                self._far_dials_us(hub2, [gossip(far, bus, junk)], "hub2-bus")
                self._hub_answers_our_dial(hub2, [gossip(far, bus, junk)], "hub2-bus")
                self.assertEqual((omitted(far, bus), bus in _answered_buses()), ([(B, far)], False),
                                 "HELD: JSON true alone counts, on the far bus's exchange and on a gossip row, by either road; "
                                 "%r is not it" % (junk,))
        self.assertEqual({"far1-bus", "far2-bus", "far3-bus"} <= _answered_buses(), True, "the ids heard answering: %r"
                         % sorted(_answered_buses()))

    def test_a_hub_from_before_viabus_renaming_a_far_host_holds_the_old_names_word_within_one_process_and_across_its_restart(self):
        """Round 4 of fork PR #897, the thirty-third commit (the reviewer's verifier at the thirty-second, by execution),
        named test_a_hub_from_before_viabus_renaming_a_far_host_releases_the_old_names_word_within_one_process_and_holds_it_across_its_restart
        until round 6. A hub that sends busId but no viaBus (the builds between the two fields; they predate
        presenceAnswered and viaAnswered too, so every word it gossips reads unanswered) renaming a far host WITHIN one
        process omits the old name on the road that named it. Until round 6 that released the old name's word, carried
        heard false; the reviewer's round-5 ruling B counts the release only for a far bus heard answering in this
        process, and a word with no viaBus never qualifies, so the old name's word stays held, heard, beside the new
        name's. ACROSS the hub's restart it stays held the same way, since the restarted process did not name the host
        and no bus id matches the two names: within this process until the far host's own row speaks for it here, and
        after this bus restarts its via row is carried unanswered and holds the arm (the reviewer's decision 4 on round 5). The
        verdicts do not move with it: while such a hub is heard here its own row is unanswered, and the arm holds every sid
        (cost (a)). Through the real builder and fold of this bus's dial (the answer road, where this bus places each of the hub's rosters after the last: round 6 of fork PR #897, the reviewer's round-5 ruling C; the hub's dials merge and release nothing) and this writer."""
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        self._notify(HUB, up=True)
        web = {"id": A, "name": "web"}
        via_alias = VIA + HUB + "/" + FAR_ALIAS
        old = {"id": B, "name": "api", "via": FAR}                          # an old hub's gossip row: no viaBus, no viaAnswered
        self._hub_answers_our_dial(HUB, [web, old], "hub-bus", answered=None)
        self._hub_answers_our_dial(HUB, [web, dict(old, via=FAR_ALIAS)], "hub-bus", answered=None)   # the same process renames FAR
        self.assertEqual(([(pa["id"], pa["via"], pa.get("hubBus")) for pa in pm.PEER_STATE[HUB]["viaHeld"]],
                          self._rows()[VIA_FAR], self._rows()[via_alias]),
                         ([(B, FAR, "hub-bus")], (True, False, [B]), (True, False, [B])),
                         "WITHIN ONE PROCESS: the old name's word stays held, heard, beside the new name's (at the forty-ninth "
                         "commit released: ([], (False, False, [B]), (True, False, [B])))")
        self._hub_answers_our_dial(HUB, [web, old], "hub-bus-2", answered=None)            # the hub restarts and names FAR again
        self._hub_answers_our_dial(HUB, [web, dict(old, via=FAR_ALIAS)], "hub-bus-3", answered=None)   # ...restarts, and renames it
        for _ in range(2):
            self.assertEqual(([(pa["id"], pa["via"], pa.get("hubBus")) for pa in pm.PEER_STATE[HUB]["viaHeld"]],
                              self._rows()[VIA_FAR], self._rows()[via_alias]),
                             ([(B, FAR, "hub-bus-2")], (True, False, [B]), (True, False, [B])),
                             "ACROSS THE HUB'S RESTART: the old name's word stays held, heard, beside the new name's")
            self._hub_answers_our_dial(HUB, [web, dict(old, via=FAR_ALIAS)], "hub-bus-3", answered=None)

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
        self._hub_answers_our_dial(FAR, [{"id": C, "name": "tests"}], "far-bus")   # its answer to our dial releases its row
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
        self.assertEqual((self._answered()[FAR], VIA_FAR in self._reach()), (False, True),
                         "the far host's answered DIAL holds its row, so it does not speak yet: the via row stands (round 6 of "
                         "fork PR #897, the reviewer's round-5 ruling C)")
        self._hub_answers_our_dial(FAR, [{"id": C, "name": "tests"}, {"id": D, "name": "api"}], "far-bus")   # the answer to our dial
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

    def _drive_every_peer_state_writer(self):
        """Run each PEER_STATE writer through the real bus in a synthetic world (round 6 of fork PR #897, the reviewer's
        round-5 ruling E and decision 5 on round 5), and return ({writer: calls}, the snapshots the stamps pin reads, the
        keys found on any row after any step, the keys found on any held word after any step beyond the gossip rows'
        own). The writers are counted as they run, each wrapped on the module, so a call through the
        module's globals is counted too. The kernel links HUB, the alias this bus dials (peer_update, up); this bus builds
        two dials to HUB; the hub dials us under the name it declares, gossiping far host FAR's unanswered word (the
        handler: the row filed under HUB_DECL, since HUB has no row to fold it to); the answer to the first dial, built
        BEFORE that dial (the fold: _drop_peer_name_dupes forgets the declared row and its state moves to HUB, FAR's word
        still on the merged roster, since that answer is not placed after it); the restarted hub's answer to the second,
        also built before (merged: FAR's word stays, the row now carrying the restarted hub's bus id); the restarted
        hub's answer to a dial built after, which omits FAR (the word leaves the roster and is held: a restarted hub, and
        FAR's bus never heard answering, stamped with the bus of the roster that named it, not the row's); the
        restarted hub's dial under its declared name, canonicalized to HUB, gossiping FAR2's unanswered word; its answer
        to our next dial, which omits FAR2 (held: FAR2's bus never heard answering); the kernel's down notify for HUB
        (peer_update, linkDown); and two refused dials (_peer_exchange_once, the far side answering 409 and then 403
        through a stubbed _peer_http, no socket). The seenAt of HUB's row is set back between steps so each held word's
        second tells the row it left."""
        self._forget_presence_cache()
        self._local_listing_answered_empty()
        called = {}
        for name in ("peer_exchange_handle", "peer_exchange_apply", "peer_update", "_peer_exchange_once",
                     "_drop_peer_name_dupes"):
            real = getattr(pm, name)

            def counted(*args, _real=real, _name=name, **kw):
                called[_name] = called.get(_name, 0) + 1
                return _real(*args, **kw)
            setattr(pm, name, counted)
            self.addCleanup(setattr, pm, name, real)
        far2 = FAR + "-two"
        far_word = {"id": B, "name": "api", "via": FAR, "viaBus": "far-bus", "viaAnswered": False}
        far2_word = {"id": C, "name": "tests", "via": far2, "viaBus": "far-two-bus", "viaAnswered": False}
        web = {"id": A, "name": "web"}
        snap, keys, word_keys = {}, set(), set()

        def note():                                   # a row is replaced whole at each exchange: the keys after EACH step
            for row in list(pm.PEER_STATE.values()):
                keys.update(row)
                word_keys.update(k for pa in row.get("viaHeld") or [] for k in pa)

        def held():
            return sorted((pa.get("id"), pa.get("via"), pa.get("heldAt"), pa.get("hubBus"), pa.get("hubRoad"))
                          for pa in (pm.PEER_STATE.get(HUB) or {}).get("viaHeld") or [])

        def hub_dials(presence, bus_id):
            resp, status = pm.peer_exchange_handle(dict(self._exchange_request(HUB_DECL, presence), busId=bus_id,
                                                        tier="trusted"))
            self.assertEqual(status, 200, resp)

        self._notify(HUB, up=True)
        note()
        early = _cap()                                # the captures of our two dials built before the hub's dial below
        sent_early = pm.build_exchange_request(HUB, wait=False)
        early2 = _cap()
        sent_early2 = pm.build_exchange_request(HUB, wait=False)
        hub_dials([web, far_word], "hub-bus")
        note()
        snap["declaredRoad"] = (pm.PEER_STATE.get(HUB_DECL) or {}).get("road")
        for sent, kw, bus_id in ((sent_early, early, "hub-bus"), (sent_early2, early2, "hub-bus-2")):
            pm.peer_exchange_apply(HUB, sent, {"host": HUB, "epoch": 1, "proto": pm.PEER_PROTO, "busId": bus_id,
                                               "presence": [web], "presenceAnswered": True, "holds": [], "relays": [],
                                               "acks": [], "bounces": [], "reads": [], "readsKept": [],
                                               "tier": "trusted"}, **kw)
            note()
        pm.PEER_STATE[HUB]["seenAt"] -= 100
        snap["earlySeenAt"] = pm.PEER_STATE[HUB]["seenAt"]
        snap["earlyAnswer"] = (pm.PEER_STATE[HUB].get("road"), pm.PEER_STATE[HUB].get("busId"), HUB_DECL in pm.PEER_STATE,
                               sorted(pa.get("id") for pa in pm.PEER_STATE[HUB].get("presence") or []), held())
        self._hub_answers_our_dial(HUB, [web], "hub-bus-2")
        note()
        snap["farHeld"] = held()
        hub_dials([web, far2_word], "hub-bus-2")
        note()
        pm.PEER_STATE[HUB]["seenAt"] -= 50
        snap["dialSeenAt"], snap["dialRoad"] = pm.PEER_STATE[HUB]["seenAt"], pm.PEER_STATE[HUB].get("road")
        self._hub_answers_our_dial(HUB, [web], "hub-bus-2")
        note()
        snap["answerRoad"], snap["bothHeld"] = pm.PEER_STATE[HUB].get("road"), held()
        self._notify(HUB, up=False)
        note()

        def refused(code):
            def http(port, payload, token=""):
                raise urllib.error.HTTPError("http://127.0.0.1:%d/peer-exchange" % port, code, "refused", {},
                                             io.BytesIO(b"no"))
            return http
        self.addCleanup(setattr, pm, "_peer_http", pm._peer_http)
        with contextlib.redirect_stderr(io.StringIO()):
            pm._peer_http = refused(409)
            snap["drift"] = pm._peer_exchange_once(FAR_ALIAS, 1, "")
            pm._peer_http = refused(403)
            snap["refused"] = pm._peer_exchange_once(FAR_DECL, 1, "")
        note()
        return called, snap, keys, word_keys - set(far_word) - set(far2_word)

    def test_the_peer_state_shape_comment_names_every_key_each_writer_stores(self):
        """PEER_STATE'S SHAPE COMMENT (round 6 of fork PR #897, the reviewer's round-5 ruling E on its refuter's
        regression-3, and decision 5 on round 5, which approves road, viaHeld, heldAt, hubBus and hubRoad and asks that
        each be named in the shape comment and pinned). Every writer the lock's census derives
        (_peer_state_lock_census's writerFunctions) runs through the real bus (_drive_every_peer_state_writer), and the
        keys found on any row after any step, with the keys _via_held stamps on a held word beyond the gossip row's own
        (a recorder replaces its row whole, so a key one exchange carries, theirTier, is gone after the next), are exactly
        the keys the declaration's comment names in double quotes (road's two values beside them): a key a writer stores
        and the comment omits reds here, and so does a key the comment names that no writer stores. The census's writer
        population must equal the writers the drive ran, so a new writer reds here until the drive runs it and its keys
        are named. Red at the forty-ninth commit, whose comment named presence, presenceAnswered, epoch, seenAt and
        drift alone."""
        called, snap, stored, stamps = self._drive_every_peer_state_writer()
        named = _peer_state_shape_comment_keys()
        self.assertEqual(sorted(named), sorted(stored | stamps),
                         "PEER_STATE's shape comment names, in double quotes, every key a writer stores on a row and every "
                         "key _via_held stamps on a held word, and no other (missing: %r; named, stored by no writer: %r)"
                         % (sorted((stored | stamps) - named), sorted(named - stored - stamps)))
        self.assertTrue({"road", "viaHeld", "heldAt", "hubBus", "hubRoad"} <= stored | stamps,
                        "decision 5's five, each stored by a writer: %r" % sorted(stored | stamps))
        self.assertEqual((snap["drift"], snap["refused"]), ("drift", "refused"), "the dialer's two notes ran")
        census = _peer_state_lock_census(Path(os.path.realpath(os.path.join(BIN, "romp-postal-service"))).read_text())
        self.assertEqual(sorted(called), census["writerFunctions"],
                         "the drive ran every writer the census derives, and no other: %r" % called)

    def test_the_recorders_stamp_road_on_each_row_and_heldat_hubbus_and_hubroad_on_each_held_word(self):
        """The writer state round 4 added, pinned by value (round 6 of fork PR #897, decision 5 on round 5 and the
        reviewer's round-5 ruling E): `road` on every row a recorder files, "dial" from the handler and "answer" from the
        fold; on a hub's row, `viaHeld`, each held word stamped `heldAt` (the seenAt of the hub's row the word left),
        `hubBus` (the bus id of the roster that last named the word, from namedAt) and `hubRoad` (the road of the row the
        word left). FAR's word, named by the hub's dial under its declared name, moves to HUB with the fold and stays on
        the merged roster through the answers to two dials built before that dial (the second from the restarted hub,
        whose bus id the row then carries), then leaves on the restarted hub's answer to a dial built after: held,
        stamped with the merged row's second and road, "answer", though a dial named it (the shape comment's disclosure:
        since the merge a word may leave a row a later roster filed), and with the bus of the roster that named it,
        "hub-bus", not the row's, "hub-bus-2" (a stamp from the row's busId, the forty-ninth commit's, reds). FAR2's
        word, named by the restarted hub's dial and omitted by its answer to our next dial, is stamped with that dial
        row's second, bus and road. Through the real handler, fold, down notify and dialer
        (_drive_every_peer_state_writer)."""
        called, snap, _, _ = self._drive_every_peer_state_writer()
        self.assertEqual(snap["declaredRoad"], "dial", "the handler files the hub's dial with road dial")
        self.assertEqual(snap["earlyAnswer"], ("answer", "hub-bus-2", False, sorted([A, B]), []),
                         "the fold files road answer, forgets the declared row, and FAR's word stays on the merged roster "
                         "through both answers to dials built before it, the row now carrying the restarted hub's bus id")
        self.assertEqual(snap["farHeld"], [(B, FAR, snap["earlySeenAt"], "hub-bus", "answer")],
                         "FAR's held word: the second and road of the row it left, the bus of the roster that named it")
        self.assertEqual((snap["dialRoad"], snap["answerRoad"]), ("dial", "answer"), "each recorder stamps its road")
        self.assertEqual(snap["bothHeld"], sorted([(B, FAR, snap["earlySeenAt"], "hub-bus", "answer"),
                                                   (C, FAR + "-two", snap["dialSeenAt"], "hub-bus-2", "dial")]),
                         "a held word keeps its stamps across the hub's later rosters, and FAR2's carries its dial row's")



# ── PEER_STATE's ONE LOCK (round 6 of fork PR #897, the reviewer's round-5 ruling A) ──
_TABLE, _TABLE_LOCK = "PEER_STATE", "_PEER_STATE_LOCK"
_ORDER_LOCK, _ORDER_WRITER = "_REMOTE_SIDS_LOCK", "_write_remote_sids"
_LINK_STATE = ("PEERS", "_PEERS_SEEDED")          # the link state one mirror write reads beside the table
_ANSWERED_SET = "_ANSWERED_BUSES"                  # the far bus ids heard answering (the reviewer's round-5 ruling B)
_SEQUENCE = "_PEER_SEQ"                            # the recording sequence (the reviewer's round-5 ruling C)
_ROW_KINDS = ("row", "rowsdict", "rows", "items", "pair")
_MUTATORS = frozenset({"pop", "popitem", "setdefault", "update", "clear", "append", "extend", "insert", "remove", "add",
                       "discard", "sort", "reverse", "__setitem__", "__delitem__", "__ior__"})
_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _peer_state_lock_census(source):
    """The census of PEER_STATE's lock over the bus's `source`, derived by AST, never listed. Returns {"writers",
    "iterations", "writerReads", "mirrorReads", "mirrorLinkReads", "answered": [[function, line, text]], "protected",
    "takers", "writerFunctions", "writerReach", "mirrorTree", "handoffTakers": [function], "mirrorHolds": [[function,
    line]], "holdBound": [[function, name, line of the hold]], "callSites": {function: n}, "refused": [text]}. The rules
    (the reviewer's round-5 ruling A, and decision 6 at its end; READS IN A WRITER'S FUNCTION and ONE MIRROR WRITE, round
    6 of fork PR #897, the verifier's findings at the fiftieth commit; ONE HOLD and the link state, its findings at the
    fifty-first; ONE HOLD's binding forms, its finding at the fifty-second; THE ANSWERED SET, the reviewer's round-5
    ruling B, the fifty-fourth commit):
      WRITERS, the rule the ruling's scan used: a store, delete or augmented assignment whose target is a subscript
        or attribute rooted at PEER_STATE or at a name bound to a ROW reached from it (PEER_STATE.get, .setdefault,
        .pop, PEER_STATE[k], a value target of a loop over PEER_STATE.items() or .values(), and so on through a copy
        of the table's items, whose rows are still the live rows); a call of a mutating method on either; a rebinding
        of the name. A row handed to a function binds that function's parameter (a starred parameter collects rows),
        so a writer in the callee is a writer too; names propagate to a fixpoint, flow-insensitively (a name once
        bound to a row stays one in its function), and a nested function reads its enclosing functions' names. A
        store or a mutating call rooted at a local container of rows (a copy of the items, a dict of rows) is a
        writer where it reaches a row: a store from depth two, a call from depth one.
      ITERATIONS: every read of the name PEER_STATE other than the three atomic ones (a .get(...) call, a subscript
        read, a membership test): .items(), .values(), a loop, a copy, the name handed on. This covers the two
        readers the ruling names, the canonicalization (_canon_peer_name, reading every row) and the mirror's
        snapshot, and decision 6's live iterations, each of which takes its copy under the lock.
      A node of either population is PROTECTED when it sits lexically inside a `with _PEER_STATE_LOCK` of its own
        function, or in a function every reference to which is a call that is itself protected (a least fixpoint
        over the functions, keyed by name: a function referenced other than by a call, or with no reference, is
        never protected by its callers). The module scope is exempt by its scope, not by name: it runs at import,
        before any thread starts (the declaration is its one node).
      Refused, each naming the function and line: an unprotected writer or iteration (with the call sites outside
        the lock, for a function protected by none); a `with _PEER_STATE_LOCK` in a protected context, or a
        protected call of a function that takes the lock, at any depth (the lock does not re-enter); and, the one
        lock order (_REMOTE_SIDS_LOCK, then this one), a protected `with _REMOTE_SIDS_LOCK` or call of
        _write_remote_sids or of any function that takes _REMOTE_SIDS_LOCK. Calls resolve by name, a method call
        by its attribute name, both over-approximating.
      READS IN A WRITER'S FUNCTION: every read of the name, the three atomic ones included, in a function holding a
        writer node (or nested in one) is protected as above, and so is every read in a function such a function
        reaches by a reference outside the lock, to any depth (references resolve as calls do): a read-modify-write
        never reads outside its hold, whether the read sits in the function or in a helper called before the hold.
        Refused: "read outside the lock in <function>, ...", naming the function holding the read.
      ONE MIRROR WRITE, ONE COPY: the functions one mirror write reaches (_write_remote_sids and every function a
        reference in a reached function names, to a fixpoint) hold ONE `with _PEER_STATE_LOCK`, not under a loop and
        in a function the write reaches by one call outside a loop at each step up to _write_remote_sids, and every
        read of the name among them, the atomic ones included, sits inside it: every table input of one write, each
        row's linkDown mark and each seenAt the lost-carry clear reads among them, comes from one moment of the table.
        So does every read of the LINK STATE among them (the names PEERS and _PEERS_SEEDED: each host's port and up,
        which _link_down and _link_up read, and the seed flag the lost-carry clear reads), so a host's row from the
        copy is never paired with a link state from after it. Refused, each prefixed "one copy:": no hold, a second
        hold, a hold under a loop or reached other than by one call, a read of the table outside the one hold, and a
        read of the link state outside it.
      ONE HOLD: a read-modify-write sits in one hold. In every function, a name bound from a READ OF THE TABLE (an
        expression that loads PEER_STATE, reads a name the rules above bind to a row or to a container of rows, or
        calls a function that reads the table, one whose body loads PEER_STATE or calls such a function, by name to a
        fixpoint) or from a name so bound (to a fixpoint, flow-insensitively, through these binding forms: an
        assignment, an augmented one, a loop target, a with target, a walrus, a match statement's captures, bound from
        its subject, and a def or a class nested in the function, whose name is bound from the whole statement, its
        defaults, decorators and body, as an assignment of a lambda is (so a nested helper whose body reads the
        table, bound outside every hold and called in one, is refused, the refusing side); a comprehension's own
        targets are that comprehension's, as Python 3 scopes them), inside one `with _PEER_STATE_LOCK` or outside
        every hold, is read
        inside another hold of that function only after that hold has rebound it (a binding in the hold that ends before the read starts); and a name so bound inside a hold
        is handed outside it, in any argument of a call, to no function that takes the lock and writes the table
        (a function holding a writer node, or calling one, by name to a fixpoint). A read inside a def or a lambda
        nested in the name's own function, outside every hold of the nested one, is read where that def or lambda
        stands (its defaults and decorators are evaluated there, and its body reads the name whenever it is called,
        so a closure defined in another hold and called only after that hold is refused as well, the refusing
        side), and a default of a def or a lambda, or a def's decorator, resolves its names, and binds a walrus's, in
        the scope around that def or lambda and in the hold where it stands. Not followed, limits of this rule: an
        except target, bound from whatever the try raised; a name declared nonlocal or global, whose binding is taken
        as the declaring function's own, so a value bound there reaches the enclosing function or another function
        unseen; a value stored into a container or an attribute and read back, a store binding no name; a type
        statement (3.12 syntax, which a 3.10 parser refuses). Refused: "split hold in <function>: <name> ...",
        naming the hold or holds it was bound in and the hold that reads it. Read outside every hold (a name chosen
        under the lock and used after it, a log line's decision) it is not refused: the rule is about a value read
        at one moment of the table and written back at another.
      THE ANSWERED SET: every reference of the name _ANSWERED_BUSES, the far bus ids heard answering in this process,
        outside the module scope (its declaration, exempt by its scope) is PROTECTED as above, and is a membership
        test (`x in _ANSWERED_BUSES`) or the receiver of an `.add(...)` call. So the set is written and read under the
        lock alone (ruling A's bullet on the state groups B and C add), and no reference hands it, or a copy of it, out
        of a hold: a name bound to the set, the set handed to a call, a loop over it, a rebinding or any other method is
        refused. Refused: "answered set outside the lock in <function>, ..." and "answered set handed on in <function>
        ...", each naming the function and line.
      THE RECORDING SEQUENCE: every reference of the name _PEER_SEQ, the recording sequence each recorder mints and each
        dial's build reads (round 6 of fork PR #897, the reviewer's round-5 ruling C), outside the module scope is
        PROTECTED as above, and is its one cell, `_PEER_SEQ[0]`, read or written (a row's marks, which hold its numbers,
        live in PEER_STATE and are covered by the rules above). So the sequence is minted and read under the lock alone,
        a number minted in one recording is the order of that recording, and no reference hands the list out of a
        hold. Refused: "recording sequence outside the lock in <function>, ..." and "recording sequence handed on in
        <function> ...", each naming the function and line."""
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    parent, scopes = {}, {}
    for node in nodes:
        for child in ast.iter_child_nodes(node):
            parent[child] = node

    def scope(node):                                  # the nearest enclosing def or lambda, or None (the module scope)
        if node not in scopes:
            p = parent.get(node)
            scopes[node] = p if p is None or isinstance(p, _FUNCS) else scope(p)
        return scopes[node]

    def fname(sc):
        return sc.name if isinstance(sc, _DEFS) else ("<lambda>" if sc is not None else "<module>")

    def names(e, name):
        return (isinstance(e, ast.Name) and e.id == name) or (isinstance(e, ast.Attribute) and e.attr == name)

    def is_with(node, name):
        return isinstance(node, (ast.With, ast.AsyncWith)) and any(names(i.context_expr, name) for i in node.items)

    def lexically_in(node, name):                     # inside the BODY of a `with <name>` within its own function
        child, p = node, parent.get(node)
        while p is not None and not isinstance(p, _FUNCS):
            if is_with(p, name) and any(child is b for b in p.body):
                return True
            child, p = p, parent.get(p)
        return False

    defs = {}
    for node in nodes:
        if isinstance(node, _DEFS):
            defs.setdefault(node.name, []).append(node)
    refs = {n: [] for n in defs}
    for node in nodes:
        nm = node.id if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) else (
            node.attr if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) else None)
        if nm in refs:
            refs[nm].append(node)

    def is_call(r):
        p = parent.get(r)
        return isinstance(p, ast.Call) and p.func is r

    # ── the rows: a kind per name per function, to a fixpoint ──
    env = {}

    def look(name, sc):
        while True:
            k = env.get(sc, {}).get(name)
            if k or sc is None:
                return k
            sc = scope(sc)

    def kind(e, sc):
        if isinstance(e, ast.Name):
            return "table" if e.id == _TABLE else look(e.id, sc)
        if isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Attribute):
                if kind(f.value, sc) in ("table", "rowsdict"):
                    return {"get": "row", "setdefault": "row", "pop": "row", "items": "items", "values": "rows",
                            "copy": "rowsdict"}.get(f.attr)
                return None
            if isinstance(f, ast.Name) and e.args:
                ka = kind(e.args[0], sc)
                if f.id in ("list", "tuple", "sorted", "reversed", "iter"):
                    return ka if ka in ("items", "rows") else None
                if f.id == "dict" and ka in ("table", "rowsdict", "items"):
                    return "rowsdict"
            return None
        if isinstance(e, ast.Subscript):
            kv = kind(e.value, sc)
            return "row" if kv in ("table", "rowsdict", "rows", "pair") else None
        if isinstance(e, ast.BoolOp):
            for v in e.values:
                k = kind(v, sc)
                if k:
                    return k
            return None
        if isinstance(e, ast.IfExp):
            return kind(e.body, sc) or kind(e.orelse, sc)
        if isinstance(e, (ast.NamedExpr, ast.Starred)):
            return kind(e.value, sc)
        if isinstance(e, ast.DictComp):
            return "rowsdict" if kind(e.value, sc) == "row" else None
        if isinstance(e, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            if kind(e.elt, sc) == "row":
                return "rows"
            if isinstance(e.elt, ast.Tuple) and any(kind(x, sc) == "row" for x in e.elt.elts):
                return "items"
            return None
        if isinstance(e, (ast.List, ast.Tuple, ast.Set)):
            return "rows" if any(kind(x, sc) == "row" for x in e.elts) else None
        return None

    def element(k):                                   # what one step of an iteration over a value of kind k yields
        return {"items": "pair", "rows": "row"}.get(k)

    def bind(t, k, sc):
        if not k:
            return False
        if isinstance(t, ast.Name):
            d = env.setdefault(sc, {})
            if d.get(t.id):
                return False
            d[t.id] = k
            return True
        if isinstance(t, (ast.Tuple, ast.List)) and k == "pair" and len(t.elts) == 2:
            return bind(t.elts[1], "row", sc)
        if isinstance(t, ast.Starred):
            return bind(t.value, k, sc)
        return False

    def bind_param(d, name, k):
        e = env.setdefault(d, {})
        if not k or e.get(name):
            return False
        e[name] = k
        return True

    changed, rounds = True, 0
    while changed and rounds < 50:
        changed, rounds = False, rounds + 1
        for node in nodes:
            sc = scope(node)
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    changed |= bind(t, kind(node.value, sc), sc)
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value is not None:
                changed |= bind(node.target, kind(node.value, sc), sc)
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                changed |= bind(node.target, element(kind(node.iter, sc)), sc)
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                changed |= bind(node.optional_vars, kind(node.context_expr, sc), sc)
            elif isinstance(node, ast.Call):
                callee = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else None)
                for d in defs.get(callee, ()):
                    params = [a.arg for a in d.args.posonlyargs + d.args.args]
                    if isinstance(node.func, ast.Attribute) and params and params[0] in ("self", "cls"):
                        params = params[1:]
                    for i, a in enumerate(node.args):
                        k = kind(a, sc)
                        if isinstance(a, ast.Starred):
                            if d.args.vararg is not None:
                                changed |= bind_param(d, d.args.vararg.arg, k if k in ("rows", "items") else None)
                        elif i < len(params):
                            changed |= bind_param(d, params[i], k)
                        elif d.args.vararg is not None:
                            changed |= bind_param(d, d.args.vararg.arg, "rows" if k == "row" else k)
                    for kw in node.keywords:
                        k = kind(kw.value, sc)
                        if kw.arg in params or kw.arg in [a.arg for a in d.args.kwonlyargs]:
                            changed |= bind_param(d, kw.arg, k)
                        elif d.args.kwarg is not None:
                            changed |= bind_param(d, d.args.kwarg.arg, "rowsdict" if k == "row" else None)

    def rooted(e, sc, container_depth):              # a chain rooted at the table or a row (or deep enough in a container)
        depth = 0
        while isinstance(e, (ast.Subscript, ast.Attribute)):
            e, depth = e.value, depth + 1
        k = kind(e, sc) if isinstance(e, ast.Name) else None
        return k in ("table", "row") or (k in ("rowsdict", "rows", "items", "pair") and depth >= container_depth)

    # ── the populations ──
    writers, iterations = [], []
    for node in nodes:
        sc = scope(node)
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        elif isinstance(node, ast.Delete):
            targets = node.targets
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension, ast.NamedExpr)):
            targets = [node.target]
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            targets = [node.optional_vars]
        for t in targets:
            flat = t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t]
            for x in flat:
                x = x.value if isinstance(x, ast.Starred) else x
                if isinstance(x, ast.Name) and x.id == _TABLE:
                    writers.append(x)                 # a rebinding of the name
                elif isinstance(x, (ast.Subscript, ast.Attribute)) and rooted(x, sc, 2):
                    writers.append(x)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _MUTATORS:
            recv = node.func.value
            if (isinstance(recv, ast.Name) and kind(recv, sc) in ("table", "row")) or (
                    isinstance(recv, (ast.Subscript, ast.Attribute)) and rooted(recv, sc, 1)):
                writers.append(node)
        if isinstance(node, ast.Name) and node.id == _TABLE and isinstance(node.ctx, ast.Load):
            p = parent.get(node)
            atomic = ((isinstance(p, ast.Attribute) and p.value is node and p.attr == "get" and is_call(p))
                      or (isinstance(p, ast.Subscript) and p.value is node)
                      or (isinstance(p, ast.Compare) and any(c is node for c in p.comparators)
                          and all(isinstance(o, (ast.In, ast.NotIn)) for o in p.ops)))
            if not atomic:
                iterations.append(node)

    protected = set()

    def locked(node):
        if lexically_in(node, _TABLE_LOCK):
            return True
        sc = scope(node)
        return isinstance(sc, _DEFS) and sc.name in protected

    changed = True
    while changed:
        changed = False
        for name, rs in refs.items():
            if name not in protected and rs and all(is_call(r) and locked(r) for r in rs):
                protected.add(name)
                changed = True

    def takers(lock, also=()):                        # the functions that take `lock`, at any depth of their calls
        out = set(also)
        for node in nodes:
            if is_with(node, lock) and isinstance(scope(node), _DEFS):
                out.add(scope(node).name)
        changed = True
        while changed:
            changed = False
            for node in nodes:
                if isinstance(node, ast.Call):
                    callee = node.func.id if isinstance(node.func, ast.Name) else (
                        node.func.attr if isinstance(node.func, ast.Attribute) else None)
                    sc = scope(node)
                    if callee in out and isinstance(sc, _DEFS) and sc.name not in out:
                        out.add(sc.name)
                        changed = True
        return out

    table_takers, order_takers = takers(_TABLE_LOCK), takers(_ORDER_LOCK, (_ORDER_WRITER,))

    def line(n):
        return [fname(scope(n)), n.lineno, " ".join((ast.get_source_segment(source, n) or "").split())[:100]]

    refused = []
    for label, pop in (("writer", writers), ("iteration", iterations)):
        for n in pop:
            sc = scope(n)
            if sc is None or locked(n):
                continue                              # the module scope runs at import, before any thread starts
            outside = []
            if isinstance(sc, _DEFS) and not lexically_in(n, _TABLE_LOCK):
                outside = ["%s line %d" % (fname(scope(r)), r.lineno) for r in refs.get(sc.name, ())
                           if not (is_call(r) and locked(r))]
            refused.append("%s outside the lock in %s (line %d: %s)%s" % (
                label, line(n)[0], n.lineno, line(n)[2],
                "; its references outside it: " + ", ".join(outside) if outside else
                ("; no call site" if isinstance(sc, _DEFS) and not refs.get(sc.name) else "")))
    for node in nodes:
        if is_with(node, _TABLE_LOCK) and locked(node):
            refused.append("re-entry: a with on the lock under the lock in %s (line %d)" % (fname(scope(node)), node.lineno))
        if is_with(node, _ORDER_LOCK) and locked(node):
            refused.append("order: %s taken under the lock in %s (line %d)" % (_ORDER_LOCK, fname(scope(node)), node.lineno))
        if isinstance(node, ast.Call) and locked(node):
            callee = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else None)
            if callee in table_takers:
                refused.append("re-entry: %s calls %s, which takes the lock, under the lock (line %d)"
                               % (fname(scope(node)), callee, node.lineno))
            if callee in order_takers:
                refused.append("order: %s calls %s, which takes %s or writes the mirror, under the lock (line %d)"
                               % (fname(scope(node)), callee, _ORDER_LOCK, node.lineno))

    # ── every read of the name, the atomic ones included (round 6 of fork PR #897, the verifier's findings at the
    # fiftieth commit) ──
    loads = [n for n in nodes if isinstance(n, ast.Name) and n.id == _TABLE and isinstance(n.ctx, ast.Load)]

    def within(node, fns):                            # inside one of the defs `fns`, at any depth of nesting
        sc = scope(node)
        while sc is not None:
            if sc in fns:
                return True
            sc = scope(sc)
        return False

    def inside(node, hold):                           # inside the BODY of the `with` node `hold`, within its own function
        child, p = node, parent.get(node)
        while p is not None and not isinstance(p, _FUNCS):
            if p is hold and any(child is b for b in p.body):
                return True
            child, p = p, parent.get(p)
        return False

    def in_loop(node):                                # under a loop or a comprehension of its own function
        p = parent.get(node)
        while p is not None and not isinstance(p, _FUNCS):
            if isinstance(p, (ast.For, ast.AsyncFor, ast.While, ast.comprehension)):
                return True
            p = parent.get(p)
        return False

    def reach(roots):                                 # the defs `roots` and, to a fixpoint, every def a reference in a
        out, frontier = set(), list(roots)            # reached def names (by name; a method by its attribute name)
        while frontier:
            d = frontier.pop()
            if d in out:
                continue
            out.add(d)
            for node in ast.walk(d):
                nm = node.id if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) else (
                    node.attr if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) else None)
                frontier.extend(defs.get(nm, ()))
        return out

    # READS IN A WRITER'S FUNCTION: a function holding a writer node reads the table only under the lock (lexically, or
    # in a function every call site of which holds it), so a read-modify-write never reads outside its hold; and so does
    # every function it reaches by a reference outside the lock, to any depth (a read hoisted into a helper called
    # before the hold is the same read)
    writer_fns = {scope(n) for n in writers if isinstance(scope(n), _DEFS)}
    iteration_ids = {id(n) for n in iterations}       # (an iteration outside the lock is refused above, once)
    writer_reads = [n for n in loads if within(n, writer_fns)]
    for n in writer_reads:
        if id(n) not in iteration_ids and not locked(n):
            refused.append("read outside the lock in %s, a function that writes the table or nests in one (line %d: %s)"
                           % (line(n)[0], n.lineno, line(n)[2]))
    reached_from, frontier = {}, []                   # each def reached, with the reference outside the lock it was reached by
    for node in nodes:
        nm = node.id if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) else (
            node.attr if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) else None)
        if nm in defs and within(node, writer_fns) and not locked(node):
            frontier.extend((d, "%s line %d" % (fname(scope(node)), node.lineno)) for d in defs[nm])
    while frontier:
        d, via = frontier.pop()
        if d in reached_from:
            continue
        reached_from[d] = via
        for node in ast.walk(d):
            nm = node.id if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) else (
                node.attr if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) else None)
            frontier.extend((d2, via) for d2 in defs.get(nm, ()) if d2 not in reached_from)
    for n in loads:
        if id(n) in iteration_ids or within(n, writer_fns) or locked(n):
            continue
        sc = scope(n)
        while sc is not None and sc not in reached_from:
            sc = scope(sc)
        if sc is not None:
            refused.append("read outside the lock in %s, which a function that writes the table reaches outside the lock "
                           "(line %d: %s; reached from %s)" % (line(n)[0], n.lineno, line(n)[2], reached_from[sc]))

    # ONE HOLD (round 6 of fork PR #897, the verifier's finding at the fifty-first commit): a read-modify-write sits in ONE
    # hold. A name bound from a read of the table, in one hold or outside every hold, is read in another hold only after
    # that hold rebinds it, and a name bound inside a hold is handed outside it to no function that takes the lock and
    # writes the table. A match's captures and a nested def or class carry the value too, and a read in a nested def or
    # lambda counts where it stands (the verifier's finding at the fifty-second commit)
    def hold_of(node):                                # the innermost `with` on the lock whose BODY holds `node`, in its function
        child, p = node, parent.get(node)
        while p is not None and not isinstance(p, _FUNCS):
            if is_with(p, _TABLE_LOCK) and any(child is b for b in p.body):
                return p
            child, p = p, parent.get(p)
        return None

    def site(n):                                      # where `n` is evaluated: a default or a decorator of a def or lambda
        child, p = n, parent.get(n)                   # where that def stands, in the scope around it; anything else where it is
        while p is not None:
            if isinstance(p, ast.arguments) and isinstance(parent.get(p), _FUNCS) and any(
                    child is d for d in p.defaults + p.kw_defaults):
                return site(parent.get(p))
            if isinstance(p, _DEFS) and any(child is d for d in p.decorator_list):
                return site(p)
            if isinstance(p, _FUNCS):
                return n
            child, p = p, parent.get(p)
        return n

    def home(n):                                      # the scope a name at `n` resolves in (a default's: the scope around its def)
        return scope(site(n))

    def callee_of(call):
        return call.func.id if isinstance(call.func, ast.Name) else (
            call.func.attr if isinstance(call.func, ast.Attribute) else None)

    calls_in = {name: {callee_of(x) for d in ds for x in ast.walk(d) if isinstance(x, ast.Call)} for name, ds in defs.items()}

    def closure(seed):                                # `seed` and every def calling one of them, by name, to a fixpoint
        out, changed = set(seed), True
        while changed:
            changed = False
            for name, called in calls_in.items():
                if name not in out and called & out:
                    out.add(name)
                    changed = True
        return out

    readers = closure({name for name, ds in defs.items() for d in ds for x in ast.walk(d)
                       if isinstance(x, ast.Name) and x.id == _TABLE and isinstance(x.ctx, ast.Load)})
    handoff = closure({d.name for d in writer_fns}) & table_takers

    def reads_table(v, sc):
        for x in ast.walk(v):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and (x.id == _TABLE or look(x.id, sc) in _ROW_KINDS):
                return True
            if isinstance(x, ast.Call) and callee_of(x) in readers:
                return True
        return False

    bindings, bound = [], set()                       # (scope, name, value, hold, end of the binding)
    for node in nodes:
        if isinstance(node, _FUNCS):
            a = node.args
            for arg in a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x is not None]:
                bound.add((node, arg.arg))            # a parameter shadows an enclosing name
        sc, stored = home(node), None
        if sc is None:
            continue                                  # the module scope runs at import, before any thread starts
        if isinstance(node, ast.Assign):
            targets, value, end = node.targets, node.value, node
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value, end = [node.target], node.value, node
        elif isinstance(node, ast.AugAssign):
            targets, value, end = [node.target], node, node
        elif isinstance(node, ast.NamedExpr):
            targets, value, end = [node.target], node.value, node
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets, value, end = [node.target], node.iter, node.target
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            targets, value, end = [node.optional_vars], node.context_expr, node.optional_vars
        elif isinstance(node, getattr(ast, "match_case", ())):   # a match's captures, bound from its subject
            stored = [p.name for p in ast.walk(node.pattern) if isinstance(p, (ast.MatchAs, ast.MatchStar)) and p.name] + [
                p.rest for p in ast.walk(node.pattern) if isinstance(p, ast.MatchMapping) and p.rest]
            value, end = parent[node].subject, node.pattern
        elif isinstance(node, _DEFS + (ast.ClassDef,)):  # a def or a class binds its name from the whole statement, as
            stored, value, end = [node.name], node, node   # an assignment of a lambda does: defaults, decorators, body
        else:
            continue                                  # a comprehension's targets are its own (comp_local)
        if stored is None:
            stored = [x.id for t in targets for x in ast.walk(t) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)]
        for name in stored:
            bindings.append((sc, name, value, hold_of(site(node)), (end.end_lineno, end.end_col_offset)))
            bound.add((sc, name))

    def comp_local(n):                                # a name a comprehension around `n` binds: Python 3 scopes it to that
        p = parent.get(n)                             # comprehension, so it is none of the function's names
        while p is not None and not isinstance(p, _FUNCS):
            if isinstance(p, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)) and any(
                    isinstance(x, ast.Name) and x.id == n.id for g in p.generators for x in ast.walk(g.target)):
                return True
            p = parent.get(p)
        return False

    def owner(sc, name):                              # the function scope a name resolves to: the nearest that binds it
        while sc is not None:
            if (sc, name) in bound:
                return sc
            sc = scope(sc)
        return None

    taint, changed = {}, True                         # (scope, name) -> the holds its value was read from (None: outside every hold)
    while changed:
        changed = False
        for sc, name, value, hold, _ in bindings:
            add = {hold} if reads_table(value, sc) else set()
            for x in ast.walk(value):
                if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and not comp_local(x):
                    o = owner(home(x), x.id)
                    if o is not None:
                        add |= taint.get((o, x.id), set())
            if not add <= taint.get((sc, name), set()):
                taint.setdefault((sc, name), set()).update(add)
                changed = True

    def where(holds_):
        return "; ".join(sorted("in the hold at line %d" % h.lineno if h is not None else "outside every hold"
                                for h in holds_))

    hold_bound = sorted({(fname(sc), name, hold.lineno) for sc, name, value, hold, _ in bindings
                         if hold is not None and hold in taint.get((sc, name), set())})
    for n in nodes:
        if not (isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)) or home(n) is None or comp_local(n):
            continue
        o = owner(home(n), n.id)
        t = taint.get((o, n.id)) if o is not None else None
        if not t:
            continue
        at = site(n)                                  # the innermost hold around the read; outside every hold of a function
        h2 = hold_of(at)                              # nested in the name's own, where that function stands (its body
        while h2 is None and scope(at) is not None and scope(at) is not o:   # reads the name whenever it is called)
            at = site(scope(at))
            h2 = hold_of(at)
        if h2 is not None:
            others = t - {h2}
            rebound = any(b[0] is o and b[1] == n.id and b[3] is h2 and b[4] <= (n.lineno, n.col_offset) for b in bindings)
            if others and not rebound:
                refused.append("split hold in %s: %s, bound from a read of the table %s, is read in the hold at line %d "
                               "(line %d)" % (fname(scope(h2)), n.id, where(others), h2.lineno, n.lineno))
            continue
        if not any(h is not None for h in t):
            continue
        child, p = n, parent.get(n)                   # handed outside its hold: an argument of a call, at any depth of it
        while p is not None and not isinstance(p, (ast.stmt, ast.Lambda)):
            if isinstance(p, ast.Call) and (child in p.args or child in p.keywords) and callee_of(p) in handoff:
                refused.append("split hold in %s: %s, bound from a read of the table %s, is handed outside it to %s, which "
                               "takes the lock and writes the table (line %d)"
                               % (fname(scope(n)), n.id, where(h for h in t if h is not None), callee_of(p), n.lineno))
            child, p = p, parent.get(p)

    # THE ANSWERED SET (round 6 of fork PR #897, the reviewer's round-5 ruling B, and ruling A's bullet on the state groups B
    # and C add): the far bus ids heard answering are written and read under the table's lock alone, each reference a
    # membership test or an add, so no reference carries the set, or a copy of it, out of the hold
    answered_refs = [n for n in nodes if isinstance(n, ast.Name) and n.id == _ANSWERED_SET and scope(n) is not None]
    for n in answered_refs:
        p = parent.get(n)
        if not ((isinstance(p, ast.Compare) and any(c is n for c in p.comparators)
                 and all(isinstance(o, (ast.In, ast.NotIn)) for o in p.ops))
                or (isinstance(p, ast.Attribute) and p.value is n and p.attr == "add" and is_call(p))):
            refused.append("answered set handed on in %s (line %d: %s): a reference is a membership test or an add"
                           % (line(n)[0], n.lineno, line(n)[2]))
        if not locked(n):
            sc = scope(n)
            outside = []
            if isinstance(sc, _DEFS) and not lexically_in(n, _TABLE_LOCK):
                outside = ["%s line %d" % (fname(scope(r)), r.lineno) for r in refs.get(sc.name, ())
                           if not (is_call(r) and locked(r))]
            refused.append("answered set outside the lock in %s (line %d: %s)%s" % (
                line(n)[0], n.lineno, line(n)[2],
                "; its references outside it: " + ", ".join(outside) if outside else
                ("; no call site" if isinstance(sc, _DEFS) and not refs.get(sc.name) else "")))

    # THE RECORDING SEQUENCE (round 6 of fork PR #897, the reviewer's round-5 ruling C, and ruling A's bullet on the state
    # groups B and C add): minted and read under the table's lock alone, each reference its one cell
    sequence_refs = [n for n in nodes if isinstance(n, ast.Name) and n.id == _SEQUENCE and scope(n) is not None]
    for n in sequence_refs:
        p = parent.get(n)
        if not (isinstance(p, ast.Subscript) and p.value is n and isinstance(p.slice, ast.Constant) and p.slice.value == 0):
            refused.append("recording sequence handed on in %s (line %d: %s): a reference is its one cell, _PEER_SEQ[0]"
                           % (line(n)[0], n.lineno, line(n)[2]))
        if not locked(n):
            sc = scope(n)
            outside = []
            if isinstance(sc, _DEFS) and not lexically_in(n, _TABLE_LOCK):
                outside = ["%s line %d" % (fname(scope(r)), r.lineno) for r in refs.get(sc.name, ())
                           if not (is_call(r) and locked(r))]
            refused.append("recording sequence outside the lock in %s (line %d: %s)%s" % (
                line(n)[0], n.lineno, line(n)[2],
                "; its references outside it: " + ", ".join(outside) if outside else
                ("; no call site" if isinstance(sc, _DEFS) and not refs.get(sc.name) else "")))

    # ONE MIRROR WRITE, ONE COPY: every function the mirror write reaches (_write_remote_sids and, to a fixpoint, every
    # function a reference in a reached function names, by name, a method by its attribute name) reads the table only
    # inside ONE `with` on the lock, taken once per write (not under a loop, in a function the write reaches by one call
    # outside a loop, up to the write), so every input of one write comes from one moment of the table
    tree = reach(defs.get(_ORDER_WRITER, ()))
    holds = [n for n in nodes if is_with(n, _TABLE_LOCK) and within(n, tree)]
    mirror_reads = [n for n in loads if within(n, tree)]
    if tree and not holds:
        refused.append("one copy: the mirror write takes no copy of the table under the lock")
    if len(holds) > 1:
        for h in holds:
            refused.append("one copy: the mirror write holds the lock more than once, a second copy of the table, in %s "
                           "(line %d)" % (fname(scope(h)), h.lineno))
    if len(holds) == 1:
        hold = holds[0]
        if in_loop(hold):
            refused.append("one copy: the mirror write's copy is taken under a loop in %s (line %d)"
                           % (fname(scope(hold)), hold.lineno))
        fn, seen = scope(hold), set()
        while isinstance(fn, _DEFS) and fn.name != _ORDER_WRITER and fn not in seen:
            seen.add(fn)
            sites = [r for r in refs.get(fn.name, ()) if within(r, tree)]
            if len(sites) != 1 or not is_call(sites[0]) or in_loop(sites[0]):
                refused.append("one copy: the mirror write's copy is taken in %s, which the write reaches other than by "
                               "one call outside a loop (%s)" % (fn.name, ", ".join(
                                   "%s line %d" % (fname(scope(r)), r.lineno) for r in sites) or "no reference"))
                break
            fn = scope(sites[0])
            while fn is not None and not isinstance(fn, _DEFS):
                fn = scope(fn)
    for n in mirror_reads:
        if not any(inside(n, h) for h in holds[:1]):
            refused.append("one copy: the mirror write reads the table outside its one copy in %s (line %d: %s)"
                           % (line(n)[0], n.lineno, line(n)[2]))
    link_reads = [n for n in nodes if isinstance(n, ast.Name) and n.id in _LINK_STATE and isinstance(n.ctx, ast.Load)
                  and within(n, tree)]            # the link state, read in the same hold as the table (round 6 of fork PR #897)
    for n in link_reads:
        if not any(inside(n, h) for h in holds[:1]):
            refused.append("one copy: the mirror write reads the link state outside its one copy in %s (line %d: %s)"
                           % (line(n)[0], n.lineno, line(n)[2]))
    return {"writers": [line(n) for n in writers], "iterations": [line(n) for n in iterations],
            "protected": sorted(protected), "takers": sorted(table_takers),
            "callSites": {n: len(rs) for n, rs in refs.items() if n in protected},
            "writerFunctions": sorted({d.name for d in writer_fns}), "writerReads": [line(n) for n in writer_reads],
            "writerReach": sorted({d.name for d in reached_from}),
            "mirrorTree": sorted({d.name for d in tree}), "mirrorHolds": [line(h)[:2] for h in holds],
            "mirrorReads": [line(n) for n in mirror_reads], "mirrorLinkReads": [line(n) for n in link_reads],
            "holdBound": [list(x) for x in hold_bound], "handoffTakers": sorted(handoff),
            "answered": [line(n) for n in answered_refs], "sequence": [line(n) for n in sequence_refs], "refused": refused}


class PeerStateLock(unittest.TestCase):
    """PEER_STATE's ONE LOCK (round 6 of fork PR #897, the reviewer's round-5 ruling A, and decision 6 at its end). The two
    recorders run at once by design, the handler for a peer's dial and the dialer for the fold of its answer, and each
    derives a hub's held words from the row it replaces; with no lock, a roster one stored between the other's read and its
    store lost a far host's unanswered word, and a session whose mail rode it answered rule 5 while another row vouched
    (every vote of the round reproduced it through the real recorders). _PEER_STATE_LOCK is held by every read-modify-write
    of the table and every iteration takes its copy under it. The census (_peer_state_lock_census) derives both populations
    from the bus's source by AST and refuses a node outside the lock, a re-entry and a lock-order inversion; the
    interleavings through the real recorders are tests/test_dead_session_staleness.py ReaderFollowsTheWriter's
    test_the_recorders_race_* witnesses (executed, the reader's answer). Each census rule has a plant here that it refuses by
    name, and the census over the bus's own source must find non-empty populations, so a census that reads nothing fails.
    Two rules joined at round 6 of fork PR #897, on the verifier's findings at the fiftieth commit: a function that writes
    the table reads it only under the lock (the fold's previous-row read hoisted before its hold passed every other pin
    and lost a far host's word under stress), and one mirror write reads the table only through its one copy (its link
    marks and seenAt read from the live table gave a write a torn table; the interleavings are
    tests/test_dead_session_staleness.py ReaderFollowsTheWriter's test_one_mirror_write_* witnesses). Two more joined on
    the verifier's findings at the fifty-first commit: one mirror write reads the link state (PEERS, the seed flag) only
    inside its one hold as well (read live, B's row from the copy met the up notify written after it and a session on B
    answered rule 5: the test_one_mirror_write_reads_each_hosts_link_state_* witness there), and a read-modify-write
    sits in ONE hold (the fold's row built in one hold and stored in a second, and three shapes like it, each under the
    lock, passed every pin; two of them lost a far host's word under a deterministic interleaving). On the verifier's
    finding at the fifty-second commit, ONE HOLD follows a value through a match statement's captures and a nested def
    or class as well, and counts a read in a nested def or lambda where that def or lambda stands (a split carried by a
    capture, or by a def's default called in the second hold, was accepted); the forms it does not follow are stated
    as limits, each with a witness. On the reviewer's round-5 ruling B (the fifty-fourth commit), the far bus ids heard
    answering (_ANSWERED_BUSES) are written and read under the lock alone, each reference a membership test or an add
    (THE ANSWERED SET). On its ruling C, the recording sequence each recorder mints and each dial's build reads
    (_PEER_SEQ) is read and written under the lock alone, each reference its one cell (THE RECORDING SEQUENCE); the rows'
    marks live in PEER_STATE, under the rules above."""

    SOURCE = Path(os.path.realpath(os.path.join(BIN, "romp-postal-service"))).read_text()
    BASE = None                                       # the bus's own refusals, read once (the plants add to them)

    def _plant(self, text):
        """The census over the bus's source with `text` planted at its end, its refusals reduced to the ones the plant
        adds: each plant pins a rule of the census, whatever the bus's own source holds."""
        return self._over(self.SOURCE + "\n\n" + text)

    def _mutant(self, *edits):
        """The census over the bus's source with each (old, new) edit applied, each `old` found exactly once (a plant
        whose text the source no longer holds fails here, loudly), reduced as _plant's is."""
        source = self.SOURCE
        for old, new in edits:
            self.assertEqual(source.count(old), 1, "the mutation's text is in the bus's source once: %r" % old)
            source = source.replace(old, new)
        return self._over(source)

    def _over(self, source):
        if PeerStateLock.BASE is None:
            PeerStateLock.BASE = set(_peer_state_lock_census(self.SOURCE)["refused"])
        base = PeerStateLock.BASE
        got = _peer_state_lock_census(source)
        got["refused"] = [r for r in got["refused"] if r not in base]
        return got

    def test_every_read_modify_write_and_iteration_of_peer_state_holds_its_one_lock(self):
        got = _peer_state_lock_census(self.SOURCE)
        self.assertEqual(got["refused"], [], "every writer and every iteration of PEER_STATE sits under _PEER_STATE_LOCK, "
                                             "lexically or through every call site; no re-entry; the one lock order")
        self.assertTrue(got["writers"] and got["iterations"] and got["takers"],
                        "the census derived its populations from the source: an empty one proves nothing (%r)" % got)
        self.assertTrue(any(fn != "<module>" for fn, _, _ in got["writers"]), "writers beyond the module's declaration")
        self.assertIn("_exchange_peer_name", got["protected"],
                      "the ruled reader: the canonicalization reads every row, and both of _exchange_peer_name's call sites "
                      "(the handler and the /peer-exchange route) hold the lock")
        self.assertGreaterEqual(got["callSites"].get("_exchange_peer_name", 0), 2, "both call sites were derived: %r" % got)
        self.assertIn("_canon_peer_name", got["protected"], "reached only through _exchange_peer_name")
        self.assertEqual(sorted({fn for fn, _, _ in got["answered"]}), ["_heard_answering", "_via_held"],
                         "THE ANSWERED SET's population, derived from the source: the recorders' note and the release's "
                         "membership test (the reviewer's round-5 ruling B): %r" % got["answered"])
        self.assertTrue({"_heard_answering", "_via_held"} <= set(got["protected"]),
                        "each reached only through call sites that hold the lock")
        self.assertEqual(sorted({fn for fn, _, _ in got["sequence"]}), ["_order_row", "build_exchange_request"],
                         "THE RECORDING SEQUENCE's population, derived from the source: the recorders' mint and the dial's "
                         "capture (the reviewer's round-5 ruling C): %r" % got["sequence"])
        self.assertIn("_order_row", got["protected"], "the mint, reached only through the recorders' holds")
        self.assertIsInstance(pm._PEER_STATE_LOCK, type(threading.Lock()), "a plain lock (it does not re-enter)")
        for other in ("_REMOTE_SIDS_LOCK", "_peer_lock", "_outbox_lock"):
            self.assertIsNot(pm._PEER_STATE_LOCK, getattr(pm, other), "one lock per subject: not %s" % other)

    def test_the_census_refuses_a_planted_writer_outside_the_lock_by_name(self):
        got = self._plant("def _planted_writer(host):\n    st = PEER_STATE.get(host)\n    st[\"planted\"] = True\n")
        self.assertTrue(any("writer outside the lock in _planted_writer" in r for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_writer(host):\n    with _PEER_STATE_LOCK:\n        st = PEER_STATE.get(host)\n"
                          "        st[\"planted\"] = True\n")
        self.assertEqual(got["refused"], [], "the control: the same writer under the lock is accepted")

    def test_the_census_refuses_a_planted_helper_with_one_call_site_outside_the_lock_by_name(self):
        helper = ("def _planted_helper(host):\n    PEER_STATE[host][\"planted\"] = True\n"
                  "def _planted_locked_caller(host):\n    with _PEER_STATE_LOCK:\n        _planted_helper(host)\n")
        got = self._plant(helper)
        self.assertEqual(got["refused"], [], "the control: a helper every call site of which holds the lock is accepted")
        self.assertIn("_planted_helper", got["protected"])
        got = self._plant(helper + "def _planted_unlocked_caller(host):\n    _planted_helper(host)\n")
        self.assertTrue(any("writer outside the lock in _planted_helper" in r and "_planted_unlocked_caller" in r
                            for r in got["refused"]), got["refused"])
        got = self._plant(helper + "_PLANTED_HOOK = _planted_helper\n")
        self.assertTrue(any("writer outside the lock in _planted_helper" in r and "<module>" in r for r in got["refused"]),
                        "a reference other than a call protects nothing: %r" % got["refused"])

    def test_the_census_refuses_a_planted_iteration_outside_the_lock_by_name(self):
        got = self._plant("def _planted_iteration():\n    return [h for h, st in PEER_STATE.items()]\n")
        self.assertTrue(any("iteration outside the lock in _planted_iteration" in r for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_iteration():\n    return sorted(PEER_STATE)\n")
        self.assertTrue(any("iteration outside the lock in _planted_iteration" in r for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_iteration():\n    with _PEER_STATE_LOCK:\n        rows = list(PEER_STATE.items())\n"
                          "    return [h for h, st in rows]\n")
        self.assertEqual(got["refused"], [], "the control: the copy taken under the lock, iterated after it")

    def test_the_census_refuses_the_answered_set_read_outside_the_lock_or_handed_on_by_name(self):
        """THE ANSWERED SET (round 6 of fork PR #897, the reviewer's round-5 ruling B): the far bus ids heard answering
        are written and read under _PEER_STATE_LOCK alone, each reference a membership test or an add."""
        got = self._plant("def _planted_answered(bus):\n    return bus in _ANSWERED_BUSES\n")
        self.assertTrue(any("answered set outside the lock in _planted_answered" in r for r in got["refused"]), got["refused"])
        helper = ("def _planted_note(bus):\n    _ANSWERED_BUSES.add(bus)\n"
                  "def _planted_note_caller(bus):\n    with _PEER_STATE_LOCK:\n        _planted_note(bus)\n")
        got = self._plant(helper)
        self.assertEqual(got["refused"], [], "the control: an add in a helper every call site of which holds the lock")
        got = self._plant(helper + "def _planted_unlocked_note(bus):\n    _planted_note(bus)\n")
        self.assertTrue(any("answered set outside the lock in _planted_note" in r and "_planted_unlocked_note" in r
                            for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_hand():\n    with _PEER_STATE_LOCK:\n        seen = _ANSWERED_BUSES\n    return seen\n")
        self.assertTrue(any("answered set handed on in _planted_hand" in r for r in got["refused"]),
                        "a name bound to the set carries it out of the hold: %r" % got["refused"])
        for form in ("sorted(_ANSWERED_BUSES)", "_ANSWERED_BUSES.discard(bus)", "set(_ANSWERED_BUSES)"):
            with self.subTest(form=form):
                got = self._plant("def _planted_form(bus):\n    with _PEER_STATE_LOCK:\n        return %s\n" % form)
                self.assertTrue(any("answered set handed on in _planted_form" in r for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_member(bus):\n    with _PEER_STATE_LOCK:\n        return bus not in _ANSWERED_BUSES\n")
        self.assertEqual(got["refused"], [], "the control: a membership test under the lock")

    def test_the_census_refuses_the_recording_sequence_read_outside_the_lock_or_handed_on_by_name(self):
        """THE RECORDING SEQUENCE (round 6 of fork PR #897, the reviewer's round-5 ruling C): the sequence each recorder
        mints and each dial's build reads is read and written under the lock alone, each reference its one cell. Refused
        by name: a read outside the lock, a helper with one call site outside it, the list bound to a name in a hold and
        returned, and the list handed to a call; accepted: the cell minted and read inside a hold."""
        got = self._plant("def _planted_capture():\n    return _PEER_SEQ[0]\n")
        self.assertTrue(any(r.startswith("recording sequence outside the lock in _planted_capture") for r in got["refused"]),
                        got["refused"])
        helper = "def _planted_mint():\n    _PEER_SEQ[0] += 1\n"
        got = self._plant(helper + "def _planted_mint_caller():\n    _planted_mint()\n")
        self.assertTrue(any(r.startswith("recording sequence outside the lock in _planted_mint") and "_planted_mint_caller" in r
                            for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_hand():\n    with _PEER_STATE_LOCK:\n        seq = _PEER_SEQ\n    return seq\n")
        self.assertTrue(any(r.startswith("recording sequence handed on in _planted_hand") for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_list():\n    with _PEER_STATE_LOCK:\n        return list(_PEER_SEQ)\n")
        self.assertTrue(any(r.startswith("recording sequence handed on in _planted_list") for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_ok():\n    with _PEER_STATE_LOCK:\n        _PEER_SEQ[0] += 1\n        return _PEER_SEQ[0]\n")
        self.assertEqual(got["refused"], [], "the control: the cell minted and read inside a hold")

    def test_the_census_refuses_a_copied_row_written_outside_the_lock_and_a_row_handed_to_a_function_that_writes_it(self):
        got = self._plant("def _planted_copy_writer():\n    with _PEER_STATE_LOCK:\n        rows = list(PEER_STATE.items())\n"
                          "    for h, st in rows:\n        st[\"planted\"] = True\n")
        self.assertTrue(any("writer outside the lock in _planted_copy_writer" in r for r in got["refused"]),
                        "a copy of the items holds the live rows: %r" % got["refused"])
        got = self._plant("def _planted_mutator(row):\n    row.setdefault(\"planted\", True)\n"
                          "def _planted_hand(host):\n    _planted_mutator(PEER_STATE.get(host))\n")
        self.assertTrue(any("writer outside the lock in _planted_mutator" in r and "_planted_hand" in r
                            for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_varargs(*rows):\n    for r in rows:\n        r[\"planted\"] = True\n"
                          "def _planted_hand(host):\n    _planted_varargs(None, PEER_STATE.get(host))\n")
        self.assertTrue(any("writer outside the lock in _planted_varargs" in r for r in got["refused"]),
                        "a starred parameter collects the rows handed to it: %r" % got["refused"])

    def test_the_census_refuses_a_planted_reentry_and_a_planted_lock_order_inversion_by_name(self):
        taker = ("def _planted_taker():\n    with _PEER_STATE_LOCK:\n        pass\n"
                 "def _planted_mid():\n    return _planted_taker()\n")
        got = self._plant(taker + "def _planted_reentry():\n    with _PEER_STATE_LOCK:\n        return _planted_mid()\n")
        self.assertTrue(any("re-entry: _planted_reentry calls _planted_mid" in r for r in got["refused"]),
                        "a call under the lock of a function that takes it, at any depth: %r" % got["refused"])
        got = self._plant(taker + "def _planted_reentry():\n    _planted_mid()\n")
        self.assertEqual(got["refused"], [], "the control: the same call outside the lock")
        got = self._plant("def _planted_inner():\n    with _PEER_STATE_LOCK:\n        pass\n"
                          "def _planted_outer():\n    with _PEER_STATE_LOCK:\n        _planted_inner()\n")
        self.assertTrue(any("re-entry" in r and "_planted_inner" in r for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_order():\n    with _PEER_STATE_LOCK:\n        _write_remote_sids()\n")
        self.assertTrue(any("order: _planted_order calls _write_remote_sids" in r for r in got["refused"]), got["refused"])
        got = self._plant("def _planted_order():\n    with _PEER_STATE_LOCK:\n        with _REMOTE_SIDS_LOCK:\n            pass\n")
        self.assertTrue(any("order: _REMOTE_SIDS_LOCK taken under the lock in _planted_order" in r for r in got["refused"]),
                        got["refused"])
        got = self._plant("def _planted_order():\n    with _REMOTE_SIDS_LOCK:\n        with _PEER_STATE_LOCK:\n            pass\n")
        self.assertEqual(got["refused"], [], "the control: the one order, _REMOTE_SIDS_LOCK then the table's lock")

    # ── the two rules of round 6 of fork PR #897's verifier's findings at the fiftieth commit ──

    def test_a_writers_function_reads_the_table_only_under_the_lock_and_one_mirror_write_reads_one_copy(self):
        """The populations of the two rules, derived from the bus's own source: the functions holding a writer node and
        their reads of the table (the fold's previous-row read among them, inside its hold), and the functions one mirror
        write reaches, whose one read of the table is the snapshot, inside the write's one hold (the link-mark and
        seenAt reads the verifier named among the functions reached, each reading the copy)."""
        got = _peer_state_lock_census(self.SOURCE)
        self.assertEqual(got["refused"], [])
        self.assertTrue({"peer_exchange_apply", "peer_exchange_handle", "peer_update"} <= set(got["writerFunctions"]),
                        "the writers' functions were derived: %r" % got["writerFunctions"])
        self.assertIn("peer_exchange_apply", [fn for fn, _, _ in got["writerReads"]],
                      "the fold's previous-row read is in the population: %r" % got["writerReads"])
        self.assertTrue({"_remote_sids_document", "_direct_row_speaks", "_link_down", "_link_up", "_source_link_down",
                         "_source_link_up", "_remote_sids_lost_cleared", "heard_since"} <= set(got["mirrorTree"]),
                        "the functions one mirror write reaches were derived to the link and seenAt reads: %r"
                        % got["mirrorTree"])
        self.assertEqual([fn for fn, _ in got["mirrorHolds"]], ["_remote_sids_document"], "one hold, the snapshot's")
        self.assertEqual([fn for fn, _, _ in got["mirrorReads"]], ["_remote_sids_document"],
                         "one read of the table in the whole write, the snapshot's")

    def test_the_census_refuses_a_read_hoisted_out_of_a_writers_hold_by_name(self):
        """A read of the table in a function that writes it, outside the lock: the verifier's mutation (the fold's
        previous-row read hoisted before its `with`, which lost a far host's word in the hook-free stress while every
        other pin passed), the same shape planted, its atomic forms (a subscript read, a membership test), a read in a
        nested helper and one in a helper called before the hold; each refused by name, beside controls it accepts."""
        got = self._mutant(
            ("    with _PEER_STATE_LOCK:                           # the previous row's read, the row's store and the fold: one step, so",
             "    prev_row = PEER_STATE.get(host)\n"
             "    with _PEER_STATE_LOCK:                           # the previous row's read, the row's store and the fold: one step, so"),
            ('        prev = PEER_STATE.get(host)                  # the row this answer is ordered after, and the rows the same bus left',
             '        prev = prev_row              # the row this answer is ordered after, and the rows the same bus left'))
        self.assertTrue(any(r.startswith("read outside the lock in peer_exchange_apply,") for r in got["refused"]),
                        "the verifier's hoisted read: %r" % got["refused"])
        hoisted = ("def _planted_hoisted(host, row):\n    prev = PEER_STATE.get(host)\n    with _PEER_STATE_LOCK:\n"
                   "        PEER_STATE[host] = dict(row, held=_via_held([], \"\", \"answer\", prev))\n")
        got = self._plant(hoisted)
        self.assertTrue(any(r.startswith("read outside the lock in _planted_hoisted,") for r in got["refused"]),
                        got["refused"])
        got = self._plant("def _planted_hoisted(host, row):\n    with _PEER_STATE_LOCK:\n        prev = PEER_STATE.get(host)\n"
                          "        PEER_STATE[host] = dict(row, held=_via_held([], \"\", \"answer\", prev))\n")
        self.assertEqual(got["refused"], [], "the control: the read inside the hold")
        for form in ("prev = PEER_STATE[host]", "prev = host in PEER_STATE"):
            got = self._plant("def _planted_atomic(host, row):\n    %s\n    with _PEER_STATE_LOCK:\n"
                              "        PEER_STATE[host] = dict(row, prev=bool(prev))\n" % form)
            self.assertTrue(any(r.startswith("read outside the lock in _planted_atomic,") for r in got["refused"]),
                            "%s: %r" % (form, got["refused"]))
        got = self._plant("def _planted_nesting(host, row):\n    def prev():\n        return PEER_STATE.get(host)\n"
                          "    p = prev()\n    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = dict(row, prev=p)\n")
        self.assertTrue(any(r.startswith("read outside the lock in prev,") for r in got["refused"]), got["refused"])
        helper = "def _planted_prev_row(host):\n    return PEER_STATE.get(host)\n"
        got = self._plant(helper + "def _planted_helper_hoist(host, row):\n    prev = _planted_prev_row(host)\n"
                          "    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = dict(row, prev=prev)\n")
        self.assertTrue(any(r.startswith("read outside the lock in _planted_prev_row,") and "_planted_helper_hoist" in r
                            for r in got["refused"]), "a read hoisted into a helper called before the hold: %r" % got["refused"])
        got = self._plant(helper + "def _planted_helper_hoist(host, row):\n    with _PEER_STATE_LOCK:\n"
                          "        PEER_STATE[host] = dict(row, prev=_planted_prev_row(host))\n")
        self.assertEqual(got["refused"], [], "the control: the helper called inside the hold, its one call site")

    def test_the_census_refuses_a_mirror_write_that_reads_the_live_table_or_a_second_copy_by_name(self):
        """One mirror write reads the table only through its one copy. Refused by name: a function the write reaches
        reading the live table's mark (the fiftieth commit's _link_down) or seenAt (its heard_since), a second hold (a
        second copy), a copy taken under a loop, and a copy taken in a helper the write reaches by two calls; accepted:
        the same functions reading the copy, and a copy taken once, in the write or in a helper it calls once."""
        first = (self.SOURCE + "\n\n").count("\n") + 1   # the line a plant starts on, after the bus's last line
        got = self._plant("def _link_down(host, table):\n    return bool((PEER_STATE.get(host) or {}).get(\"linkDown\"))\n")
        self.assertTrue(any(r.startswith("one copy: the mirror write reads the table outside its one copy in _link_down "
                                         "(line %d:" % (first + 1)) for r in got["refused"]),
                        "the live mark: %r" % got["refused"])
        got = self._plant("def _link_down(host, table):\n    return bool((table.get(host) or {}).get(\"linkDown\"))\n")
        self.assertEqual(got["refused"], [], "the control: the mark read from the copy")
        got = self._plant("def _remote_sids_lost_cleared(lost, table):\n    def heard_since(host):\n"
                          "        return bool((PEER_STATE.get(host) or {}).get(\"seenAt\"))\n    return heard_since(\"x\")\n")
        self.assertTrue(any(r.startswith("one copy: the mirror write reads the table outside its one copy in heard_since")
                            for r in got["refused"]), "the live seenAt: %r" % got["refused"])
        head = ("PEER_STATE = {}\ndef _write_remote_sids():\n    with _REMOTE_SIDS_LOCK:\n"
                "        return _remote_sids_document()\n")      # a write over a source of its own: whatever the bus holds
        second = head + ("def _remote_sids_document():\n    with _PEER_STATE_LOCK:\n"
                         "        table = {h: dict(st) for h, st in PEER_STATE.items()}\n"
                         "    return _remote_sids_lost_cleared(table)\n"
                         "def _remote_sids_lost_cleared(table):\n    with _PEER_STATE_LOCK:\n"
                         "        seen = PEER_STATE.get(\"x\")\n    return bool(seen)\n")
        refused = _peer_state_lock_census(second)["refused"]
        self.assertTrue(any(r.startswith("one copy: the mirror write holds the lock more than once") and
                            "_remote_sids_lost_cleared (line 10)" in r for r in refused), "a second copy: %r" % refused)
        loop = head + ("def _remote_sids_document():\n    rows = {}\n    for h in list(PEERS):\n        with _PEER_STATE_LOCK:\n"
                       "            rows[h] = dict(PEER_STATE.get(h) or {})\n    return rows\n")
        self.assertTrue(any(r.startswith("one copy: the mirror write's copy is taken under a loop in _remote_sids_document")
                            for r in _peer_state_lock_census(loop)["refused"]), _peer_state_lock_census(loop)["refused"])
        copy = "def _copy():\n    with _PEER_STATE_LOCK:\n        return {h: dict(st) for h, st in PEER_STATE.items()}\n"
        twice = head + "def _remote_sids_document():\n    return _copy(), _copy()\n" + copy
        self.assertTrue(any(r.startswith("one copy: the mirror write's copy is taken in _copy, which the write reaches other "
                                         "than by one call outside a loop") for r in _peer_state_lock_census(twice)["refused"]),
                        _peer_state_lock_census(twice)["refused"])
        once = head + "def _remote_sids_document():\n    table = _copy()\n    return [h for h in table]\n" + copy
        self.assertEqual(_peer_state_lock_census(once)["refused"], [], "the control: a helper the write calls once")
        inline = head + ("def _remote_sids_document():\n    with _PEER_STATE_LOCK:\n"
                         "        table = {h: dict(st) for h, st in PEER_STATE.items()}\n    return [h for h in table]\n")
        got = _peer_state_lock_census(inline)
        self.assertEqual((got["refused"], [fn for fn, _ in got["mirrorHolds"]]), ([], ["_remote_sids_document"]),
                         "the control: the copy taken once, in the write")

    # ── round 6 of fork PR #897, the verifier's findings at the fifty-first commit ──

    def test_the_census_refuses_a_mirror_write_that_reads_the_link_state_outside_its_one_copy_by_name(self):
        """One mirror write reads the link state only through the copies it takes in its one hold: each host's port and
        up from PEERS, which _link_down and _link_up read, and the seed flag and the list of links the lost-carry clear
        reads. The fifty-first commit read them live after its copy of the table (a finding of the reviewer's verifier,
        by execution: B's answered dial heard while the kernel held B down met the up notify written after the copy and
        spoke for B, and a session started on B since answered rule 5; tests/test_dead_session_staleness.py
        ReaderFollowsTheWriter's test_one_mirror_write_reads_each_hosts_link_state_from_its_one_hold_* witness). Refused
        by name: each of those four live reads, put back into the bus's own source, and the copy of the link fields moved
        after the hold there; a copy of PEERS taken after the hold in a source of its own; accepted: the same copies taken
        in the hold."""
        got = _peer_state_lock_census(self.SOURCE)
        self.assertEqual([r for r in got["refused"] if r.startswith("one copy: the mirror write reads the link state")], [],
                         "the bus's own source reads the link state only in the write's one hold")
        self.assertEqual(sorted((fn, text) for fn, _, text in got["mirrorLinkReads"]),
                         [("_remote_sids_document", "PEERS"), ("_remote_sids_document", "_PEERS_SEEDED")],
                         "the link state is read in the whole write twice, both in the snapshot's hold: %r"
                         % got["mirrorLinkReads"])
        live = [   # the fifty-first commit's reads, each put back into the bus's own source
            ("_link_down", [('    p = links.get(host) or {}                          # the writer\'s copy of the link state, '
                             'never the live PEERS\n    if p.get("port") and not p.get("up"):',
                             '    p = PEERS.get(host) or {}\n    if p.get("port") and not p.get("up"):')]),
            ("_link_up", [('    p = links.get(host) or {}                          # the writer\'s copy of the link state, '
                           'never the live PEERS\n    return bool(p.get("port") and p.get("up"))',
                           '    p = PEERS.get(host) or {}\n    return bool(p.get("port") and p.get("up"))')]),
            ("_remote_sids_lost_cleared", [('    dialable = [h for h, p in links.items() if p.get("port")]',
                                            '    dialable = [h for h, p in list(PEERS.items()) if p.get("port")]')]),
            ("_remote_sids_lost_cleared", [('    if not seeded:                                    # the seed flag and the',
                                            '    if not _PEERS_SEEDED[0]:                          # the seed flag and the')]),
            ("_remote_sids_document", [   # and the copy of the link fields moved after the hold, in the bus's own source
                ('        links = {h: {"port": p.get("port"), "up": bool(p.get("up"))} for h, p in dict(PEERS).items()}\n', ''),
                ('    peers = {h: st for h, st in table.items() if st.get("seenAt")}   # the hosts heard in this process',
                 '    links = {h: {"port": p.get("port"), "up": bool(p.get("up"))} for h, p in dict(PEERS).items()}\n'
                 '    peers = {h: st for h, st in table.items() if st.get("seenAt")}   # the hosts heard in this process')]),
        ]
        for fn, edits in live:
            with self.subTest(function=fn, read=edits[-1][1].split("\n")[0].strip()):
                got = self._mutant(*edits)
                self.assertTrue(any(r.startswith("one copy: the mirror write reads the link state outside its one copy in "
                                                 "%s (line" % fn) for r in got["refused"]), got["refused"])
        head = ("PEER_STATE = {}\nPEERS = {}\ndef _write_remote_sids():\n    with _REMOTE_SIDS_LOCK:\n"
                "        return _remote_sids_document()\n")      # a write over a source of its own: whatever the bus holds
        after = head + ("def _remote_sids_document():\n    with _PEER_STATE_LOCK:\n"
                        "        table = {h: dict(st) for h, st in PEER_STATE.items()}\n"
                        "    links = dict(PEERS)\n    return table, links\n")
        with self.subTest(plant="a copy of PEERS after the hold"):
            refused = _peer_state_lock_census(after)["refused"]
            self.assertTrue(any(r.startswith("one copy: the mirror write reads the link state outside its one copy in "
                                             "_remote_sids_document (line 9:") for r in refused),
                            "a copy after the hold: %r" % refused)
        inside = head + ("def _remote_sids_document():\n    with _PEER_STATE_LOCK:\n"
                         "        table = {h: dict(st) for h, st in PEER_STATE.items()}\n        links = dict(PEERS)\n"
                         "    return table, links\n")
        self.assertEqual(_peer_state_lock_census(inside)["refused"], [], "the control: the copy taken in the hold")

    def test_the_census_refuses_a_read_modify_write_split_across_two_holds_by_name(self):
        """A read-modify-write sits in ONE hold (ONE HOLD in _peer_state_lock_census): a name bound from a read of the
        table in one hold, or outside every hold, is read in another hold only after that hold rebinds it, and a name
        bound in a hold is handed outside it to no function that takes the lock and writes the table. The reviewer's
        verifier found at the fifty-first commit that every read and write sitting under SOME hold passed the census:
        the fold's row built in one hold and stored in a second (M13), the same in the handler (M14), the fold's
        previous-row read in a hold of its own (M15), and the down notify's membership test in one hold and its mark in
        another (M16) each refused nothing and passed every group-A pin, and M13 and M15 lost a far host's word under a
        deterministic interleaving. Refused by name here: those four, put into the bus's own source; the shapes planted,
        with a value derived between the holds, a read taken by a helper that holds the lock itself before the hold,
        a value handed after its hold to a function that takes the lock and writes, and a name read in a second hold
        before that hold rebinds it; accepted: each shape in one hold, a name each hold rebinds before reading (the
        dialer's two notes), a name chosen under the lock and used after it by a function that writes no table (the
        handler's host), and a value bound outside every hold from no read of the table (the recorders' bus_id)."""
        got = _peer_state_lock_census(self.SOURCE)
        self.assertEqual([r for r in got["refused"] if r.startswith("split hold")], [],
                         "the bus's own read-modify-writes each sit in one hold")
        bound = {(fn, name) for fn, name, _ in got["holdBound"]}
        self.assertTrue({("peer_exchange_apply", "row"), ("peer_exchange_handle", "row"), ("peer_exchange_handle", "host"),
                         ("_peer_exchange_once", "st")} <= bound,
                        "the population: the names the recorders and the dialer's notes bind from the table in a hold: %r"
                        % got["holdBound"])
        self.assertTrue({"peer_exchange_apply", "peer_exchange_handle", "peer_update", "_peer_exchange_once"}
                        <= set(got["handoffTakers"]), "the functions that take the lock and write: %r" % got["handoffTakers"])
        fold_store = ('        PEER_STATE[host] = row\n        if bus_id:                                   # fold any row it '
                      'left under its self-declared hostname\n')
        hand_store = ('        PEER_STATE[host] = row\n        if bus_id:\n            _drop_peer_name_dupes(host, bus_id)\n'
                      '    _write_remote_sids()                           # presence changed: refresh the deadness mirror, '
                      'AFTER the busId\n')
        fold_hold = ('    with _PEER_STATE_LOCK:                           # the previous row\'s read, the row\'s store and the '
                     'fold: one step, so\n')
        mark = ('    with _PEER_STATE_LOCK:                           # the membership test and the mark, one step (round 6 '
                'of fork PR #897)\n        if not up and host in PEER_STATE:\n')
        mutants = {   # the verifier's four, each read and write under some hold, put into the bus's own source
            "M13": ([(fold_store, "    with _PEER_STATE_LOCK:\n" + fold_store)],
                    "split hold in peer_exchange_apply: row, bound from a read of the table in the hold at line"),
            "M14": ([(hand_store, "    with _PEER_STATE_LOCK:\n" + hand_store)],
                    "split hold in peer_exchange_handle: row, bound from a read of the table in the hold at line"),
            "M15": ([(fold_hold, "    with _PEER_STATE_LOCK:\n        prev_row = PEER_STATE.get(host)\n" + fold_hold),
                     ('        prev = PEER_STATE.get(host)                  # the row this answer is ordered after, and the rows the same bus left',
                      '        prev = prev_row              # the row this answer is ordered after, and the rows the same bus left')],
                    "split hold in peer_exchange_apply: prev_row, bound from a read of the table in the hold at line"),
            "M16": ([(mark, "    with _PEER_STATE_LOCK:\n        marked = not up and host in PEER_STATE\n"
                            "    with _PEER_STATE_LOCK:\n        if marked:\n")],
                    "split hold in peer_update: marked, bound from a read of the table in the hold at line"),
        }
        for name, (edits, want) in mutants.items():
            with self.subTest(mutant=name):
                got = self._mutant(*edits)
                self.assertTrue(any(r.startswith(want) for r in got["refused"]), got["refused"])
        with self.subTest(mutant="M14, the canonicalization"):
            got = self._mutant(*mutants["M14"][0])
            self.assertTrue(any(r.startswith("split hold in peer_exchange_handle: host, bound from a read of the table in "
                                             "the hold at line") for r in got["refused"]),
                            "M14's canonicalization, read in the first hold, keys the second's store: %r" % got["refused"])
        build = '{"presence": resp, "viaHeld": _via_held(resp, "", "answer", %s)}'
        plants = {   # (shape split across two holds, its refusal's start; the one-hold control, or None)
            "M13": ("def _planted_split(host, resp):\n    with _PEER_STATE_LOCK:\n        row = %s\n"
                    "    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = row\n" % (build % "PEER_STATE.get(host)"),
                    "split hold in _planted_split: row, bound from a read of the table in the hold at line",
                    "def _planted_split(host, resp):\n    with _PEER_STATE_LOCK:\n        row = %s\n"
                    "        PEER_STATE[host] = row\n" % (build % "PEER_STATE.get(host)")),
            "M15": ("def _planted_split(host, resp):\n    with _PEER_STATE_LOCK:\n        prev_row = PEER_STATE.get(host)\n"
                    "    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = %s\n" % (build % "prev_row"),
                    "split hold in _planted_split: prev_row, bound from a read of the table in the hold at line",
                    "def _planted_split(host, resp):\n    with _PEER_STATE_LOCK:\n        prev_row = PEER_STATE.get(host)\n"
                    "        PEER_STATE[host] = %s\n" % (build % "prev_row")),
            "M16": ("def _planted_split(host, up):\n    with _PEER_STATE_LOCK:\n        marked = not up and host in PEER_STATE\n"
                    "    with _PEER_STATE_LOCK:\n        if marked:\n            PEER_STATE[host][\"linkDown\"] = True\n",
                    "split hold in _planted_split: marked, bound from a read of the table in the hold at line",
                    "def _planted_split(host, up):\n    with _PEER_STATE_LOCK:\n        marked = not up and host in PEER_STATE\n"
                    "        if marked:\n            PEER_STATE[host][\"linkDown\"] = True\n"),
            "derived between the holds": (
                "def _planted_split(host, resp):\n    with _PEER_STATE_LOCK:\n        prev_row = PEER_STATE.get(host)\n"
                "    held = _via_held(resp, \"\", \"answer\", prev_row)\n"
                "    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = {\"presence\": resp, \"viaHeld\": held}\n",
                "split hold in _planted_split: held, bound from a read of the table in the hold at line", None),
            "a helper's own hold before the hold": (
                "def _planted_prev_locked(host):\n    with _PEER_STATE_LOCK:\n        return PEER_STATE.get(host)\n"
                "def _planted_split(host, resp):\n    prev_row = _planted_prev_locked(host)\n"
                "    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = %s\n" % (build % "prev_row"),
                "split hold in _planted_split: prev_row, bound from a read of the table outside every hold, is read in "
                "the hold at line", None),
            "handed to a function that writes": (
                "def _planted_store_locked(host, row):\n    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = row\n"
                "def _planted_split(host, resp):\n    with _PEER_STATE_LOCK:\n        row = %s\n"
                "    _planted_store_locked(host, row)\n" % (build % "PEER_STATE.get(host)"),
                "split hold in _planted_split: row, bound from a read of the table in the hold at line", None),
            "read before the second hold rebinds it": (
                "def _planted_split(host):\n    with _PEER_STATE_LOCK:\n        st = PEER_STATE.setdefault(host, {})\n"
                "        st[\"a\"] = 1\n    with _PEER_STATE_LOCK:\n        seen = st.get(\"a\")\n"
                "        st = PEER_STATE.setdefault(host, {})\n        st[\"b\"] = seen\n",
                "split hold in _planted_split: st, bound from a read of the table in the hold at line", None),
        }
        for name, (split, want, one) in plants.items():
            with self.subTest(plant=name):
                got = self._plant(split)
                self.assertTrue(any(r.startswith(want) for r in got["refused"]), got["refused"])
                if name == "handed to a function that writes":
                    self.assertTrue(any("is handed outside it to _planted_store_locked, which takes the lock and writes "
                                        "the table" in r for r in got["refused"]), got["refused"])
                if one is not None:
                    self.assertEqual(self._plant(one)["refused"], [], "the control: %s in one hold" % name)
        controls = {
            "each hold rebinds before reading (the dialer's two notes)":
                "def _planted_notes(host):\n    with _PEER_STATE_LOCK:\n        st = PEER_STATE.setdefault(host, {})\n"
                "        st[\"a\"] = 1\n    with _PEER_STATE_LOCK:\n        st = PEER_STATE.setdefault(host, {})\n"
                "        st[\"b\"] = 1\n",
            "a name chosen under the lock and used after it by a function that writes no table (the handler's host)":
                "def _planted_name(host, row):\n    with _PEER_STATE_LOCK:\n"
                "        host = host if host in PEER_STATE else \"x\"\n        PEER_STATE[host] = row\n"
                "    _log(\"peer %s\" % host)\n",
            "a value bound outside every hold from no read of the table (the recorders' bus_id)":
                "def _planted_bus(host, resp):\n    bus_id = str(resp.get(\"busId\") or \"\")\n    with _PEER_STATE_LOCK:\n"
                "        PEER_STATE[host] = {\"busId\": bus_id, \"viaHeld\": _via_held([], bus_id, \"answer\", "
                "PEER_STATE.get(host))}\n",
        }
        for name, text in controls.items():
            with self.subTest(control=name):
                self.assertEqual(self._plant(text)["refused"], [], name)

    # ── round 6 of fork PR #897, the verifier's finding at the fifty-second commit ──

    def test_the_census_follows_a_split_hold_through_a_match_capture_and_a_nested_def_by_name(self):
        """ONE HOLD's binding forms. The paragraph said the census followed a value through every binding form, and the
        reviewer's verifier found at the fifty-second commit that a split carried by a match statement's capture, or by
        a nested def's default called in the second hold, was accepted. Refused by name here: each of those two, beside
        its one-hold control, and the rest of their class, a value a function or a class carries into the second hold
        (a match's star and mapping rest, a nested def's default shadowing the name, its closure and its decorator, a
        walrus in a def's default, which binds in the scope around the def, a def in the second hold whose default
        shadows the name, a lambda's default and its closure in the second hold, a nested class's body). Kept:
        a nested function's own hold reading the enclosing hold's name is refused, and a closure called outside every
        hold is not. The paragraph's two over-approximations are witnessed, each asserted refused: a closure defined in
        another hold and called only after it, and a nested helper that reads the table, bound outside every hold and
        called in one. The limits the paragraph states are witnessed here, each asserted accepted, so a census that
        comes to follow one of them turns this red until the paragraph says so: an except target, a nonlocal and a
        global declaration, a value carried in a container and in an attribute, and a type statement where the parser
        reads one (below 3.12 it refuses the syntax, so a bus holding one cannot pass the census there)."""
        first = (self.SOURCE + "\n\n").count("\n") + 1   # the line a plant starts on, after the bus's last line
        head = "def _planted_split(host, resp):\n"
        read = "    with _PEER_STATE_LOCK:\n        prev = PEER_STATE.get(host)\n"
        store = "    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = {\"presence\": resp, \"viaHeld\": %s}\n"

        def holds(text):                              # the lines of a plant's holds of the lock, in order
            return [first + i for i, ln in enumerate(text.split("\n")) if ln.strip() == "with _PEER_STATE_LOCK:"]

        split = {   # the plant, and the names its refusals name
            "match capture": (head + read + "    match prev:\n        case {\"viaHeld\": held}:\n            pass\n"
                              "        case _:\n            held = []\n" + store % "held", "held"),
            "match star and mapping rest": (head + read + "    match prev:\n        case {\"viaHeld\": [*held], **rest}:\n"
                                            "            pass\n" + store % "(held, rest)", "held rest"),
            "def default": (head + read + "    def held(p=prev):\n        return (p or {}).get(\"viaHeld\")\n"
                            + store % "held()", "held"),
            "def default shadowing the name": (head + read + "    def held(prev=prev):\n"
                                               "        return (prev or {}).get(\"viaHeld\")\n" + store % "held()", "held"),
            "a walrus in a def's default, in the first hold": (
                head + "    with _PEER_STATE_LOCK:\n        def _planted_probe(p=(held := PEER_STATE.get(host))):\n"
                "            return p\n" + store % "held", "held"),
            "def closure": (head + read + "    def held():\n        return (prev or {}).get(\"viaHeld\")\n"
                            + store % "held()", "held"),
            "def decorator": (head + read + "    @functools.partial(_wrap, prev)\n    def held():\n        return None\n"
                              + store % "held()", "held"),
            "def in the second hold, its default shadowing the name": (
                head + read + "    with _PEER_STATE_LOCK:\n        def held(prev=prev):\n"
                "            return (prev or {}).get(\"viaHeld\")\n"
                "        PEER_STATE[host] = {\"presence\": resp, \"viaHeld\": held()}\n", "prev"),
            "lambda default in the second hold": (
                head + read + store % "(lambda prev=prev: (prev or {}).get(\"viaHeld\"))()", "prev"),
            "lambda closure in the second hold": (head + read + store % "(lambda: (prev or {}).get(\"viaHeld\"))()", "prev"),
            "class body": (head + read + "    class Held:\n        value = (prev or {}).get(\"viaHeld\")\n"
                           + store % "Held.value", "Held"),
        }
        for name, (text, bound) in split.items():
            with self.subTest(plant=name):
                h = holds(text)
                self.assertEqual(len(h), 2, "the plant has two holds: %r" % h)
                got = self._plant(text)["refused"]
                for each in bound.split():
                    self.assertTrue(any(r.startswith("split hold in _planted_split: %s, bound from a read of the table in "
                                                     "the hold at line %d" % (each, h[0]))
                                        and ("is read in the hold at line %d (" % h[1]) in r for r in got), (each, got))
        one = {   # the one-hold controls of the two forms the verifier found
            "match capture": (head + "    with _PEER_STATE_LOCK:\n        match PEER_STATE.get(host):\n"
                              "            case {\"viaHeld\": held}:\n                pass\n            case _:\n"
                              "                held = []\n        PEER_STATE[host] = {\"presence\": resp, \"viaHeld\": held}\n"),
            "def default": (head + "    with _PEER_STATE_LOCK:\n        prev = PEER_STATE.get(host)\n"
                            "        def held(p=prev):\n            return (p or {}).get(\"viaHeld\")\n"
                            "        PEER_STATE[host] = {\"presence\": resp, \"viaHeld\": held()}\n"),
        }
        for name, text in one.items():
            with self.subTest(control=name):
                self.assertEqual(self._plant(text)["refused"], [], "the control: %s in one hold" % name)
        with self.subTest(kept="a nested function's own hold reads the enclosing hold's name"):
            text = (head + read + "    def _planted_store():\n        with _PEER_STATE_LOCK:\n"
                    "            PEER_STATE[host] = {\"viaHeld\": prev}\n    _planted_store()\n")
            got = self._plant(text)["refused"]
            self.assertTrue(any(r.startswith("split hold in _planted_store: prev, bound from a read of the table in the hold "
                                             "at line %d, is read in the hold at line %d (" % tuple(holds(text)))
                                for r in got), got)
        with self.subTest(kept="a closure called outside every hold"):
            self.assertEqual(self._plant(head + read + "    def held():\n        return (prev or {}).get(\"viaHeld\")\n"
                                         "    _log(\"held %r\" % held())\n")["refused"], [])
        refusing = {   # the paragraph's two over-approximations, each refused as it says
            "a closure defined in another hold, called only after it": (
                head + read + "    with _PEER_STATE_LOCK:\n        def held():\n            return (prev or {}).get(\"viaHeld\")\n"
                "        PEER_STATE[host] = {\"presence\": resp}\n    _log(\"held %r\" % held())\n",
                "split hold in _planted_split: prev, bound from a read of the table in the hold at line %d, is read in the "
                "hold at line %d ("),
            "a nested helper whose body reads the table, bound outside every hold and called in one": (
                head + "    def _planted_row():\n        return PEER_STATE.get(host)\n"
                "    with _PEER_STATE_LOCK:\n        PEER_STATE[host] = {\"presence\": resp, \"prev\": _planted_row()}\n",
                "split hold in _planted_split: _planted_row, bound from a read of the table outside every hold, is read in "
                "the hold at line %d ("),
        }
        for name, (text, want) in refusing.items():
            with self.subTest(refusing_side=name):
                got = self._plant(text)["refused"]
                self.assertTrue(any(r.startswith(want % tuple(holds(text))) for r in got), got)
        limits = {   # the paragraph's stated limits, each accepted
            "an except target": (head + "    try:\n        with _PEER_STATE_LOCK:\n"
                                 "            raise LookupError(PEER_STATE.get(host))\n    except LookupError as e:\n"
                                 "        held = e.args[0]\n" + store % "held"),
            "a nonlocal declaration": (head + "    held = None\n    def _planted_read():\n        nonlocal held\n"
                                       "        with _PEER_STATE_LOCK:\n            held = PEER_STATE.get(host)\n"
                                       "    _planted_read()\n" + store % "held"),
            "a global declaration": ("def _planted_global_read(host):\n    global _PLANTED_HELD\n    with _PEER_STATE_LOCK:\n"
                                     "        _PLANTED_HELD = PEER_STATE.get(host)\n" + head
                                     + "    _planted_global_read(host)\n" + store % "_PLANTED_HELD"),
            "a container": (head + "    box = {}\n    with _PEER_STATE_LOCK:\n        box[\"held\"] = PEER_STATE.get(host)\n"
                            + store % "box[\"held\"]"),
            "an attribute": (head + "    box = types.SimpleNamespace()\n    with _PEER_STATE_LOCK:\n"
                             "        box.held = PEER_STATE.get(host)\n" + store % "box.held"),
        }
        for name, text in limits.items():
            with self.subTest(limit=name):
                self.assertEqual(self._plant(text)["refused"], [], "a stated limit, not followed: %s" % name)
        typed = head + read + "    type Held = prev\n" + store % "Held.__value__"
        with self.subTest(limit="a type statement"):
            if sys.version_info >= (3, 12):
                self.assertEqual(self._plant(typed)["refused"], [], "a stated limit, not followed: a type statement")
            else:
                with self.assertRaises(SyntaxError, msg="below 3.12 the parser refuses a type statement"):
                    self._plant(typed)

if __name__ == "__main__":
    unittest.main()
