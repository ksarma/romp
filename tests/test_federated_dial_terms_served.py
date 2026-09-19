"""A federated chat pane dials the remote with the PAGE'S OWN terms (the design in
plans/federated-pane-dial-terms.md; the code it decides). Two hermetic kernels on one box:
a hub that owns no session and a checked-in TESTHOST that owns two ("api" the watched tab, "worker" a cold
one). The hub's /chat page, in a skeleton posture (?skeleton=1) with the watched tab persisted as a REMOTE
session, dials TESTHOST's relay socket. Before this change the remote dial carried only app+wid, so the
remote built every tab whole, held no skeleton set, and filed an anonymous relay row: the cost the user's
long chat thread ran on. Now federation.ts reads the shim's __rompDialTerms and carries them to each remote
socket, so the remote is served the way the local pane is.

Red first at the base (the bare dial), green with the terms, on three observables:
  1. the relay dial URL (window.__dials) carries skeleton=1, delta=1, the watched tab's BARE sid as
     active=, and an iid namespaced by the hub's wid;
  2. the REMOTE kernel's /perf builds.chat.coldSkipped is >0 (it dieted the cold tab for the hub's
     skeleton client), 0 at the base;
  3. the REMOTE kernel's client-diag.jsonl carries a wsopen row of kind "relay" whose iid presence flag is
     true (the stored row records iid as present/absent, not the value: kernel.py _note_ws_open), where the
     bare dial left it the absent one that reads as an anonymous relay.

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no
in-process state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (the same as
tests/test_chat_split_host_served.py, its two-kernel sibling). Synthetic only: placeholder uuids, hostname
TESTHOST, invented transcript text.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID_R0 = "11111111-2222-4333-8444-000000000701"   # "api" on TESTHOST: the tab the page is watching
SID_R1 = "11111111-2222-4333-8444-000000000702"   # "worker" on TESTHOST: a cold tab the skeleton client diets
HOST = "TESTHOST"
REMOTE0 = HOST + ":" + SID_R0                      # …as the hub's dashboard carries it (federation.ts prefixId)
WID = "hublab"                                     # the hub pane's wid: the iid it sends is namespaced by this


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ── the relay dial's caps term, derived from the drive (2026-09-19) ──
# federation.ts writes a relay dial's caps as its own decoder word (REMOTE_DIAL_CAPS) plus the held members it reads from the
# CONN's own bases after connect()'s gated reset: held:feed:<gen>.<rev> from the pair beside the raw feed base, held:bars from
# the receiver's bars base, each omitted when its base is absent or holds no gen. The page's caps string is never a source.
# A lab derives the expectation from the DRIVE, the frames the host's EARLIER relay sockets received as the driver's hook
# records them (type, slot and the stamp fields, never content), by the same rule; on a kernel whose frames carry no gen
# (every kernel in this repo today) that is "feedDelta" on every dial, a redial included, and the labs record exactly that.
REMOTE_DIAL_CAPS = "feedDelta"
STAMP_FIELDS = ("gen", "newGen", "base", "rev", "through")   # what a hook copies off a frame beside its type: the gens as the kernel's strings, the revs as numbers, no content
GEN_FIELDS = ("gen", "newGen")


def _stamp_field(f, k):
    """A stamp field as the client reads it: a gen (view-deltas.ts genOf) is a non-empty string holding neither '.' (the held
    member's own separator) nor ',' (the caps term's), the kernel's boot token and counter joined by '-'; a rev (base, rev,
    through) is a non-negative int. Anything else reads as absent, as the client reads it."""
    v = f.get(k)
    if k in GEN_FIELDS:
        return v if isinstance(v, str) and v and "." not in v and "," not in v else None
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None


def held_pair(frames, slot):
    """The (gen, rev) pair the client holds for `slot` ("feed" or "bars") after `frames`, the recorded frames of a host's relay
    sockets in arrival order, by federation.ts's rule: a full carrying gen leaves (gen, 0) and a full carrying none clears
    the pair; a stamped delta leaves (newGen when carried, else gen; through), which is (newGen, R) for a composed frame and
    (gen, rev) for the stamping kernel's per-cycle delta (through equal to rev, no newGen); a stamped delta carrying no
    through is refused by the client (every stamped delta carries it: a needFullFeed, nothing applied) and moves nothing, as
    a gen-less delta does. A stamped delta the client would otherwise refuse (its gen not the held one, its base above the
    held rev) is not modelled: a lab's stream is the kernel's own and applies. None when no pair is held."""
    full, delta = ("feed", "feedDelta") if slot == "feed" else ("bars", "delta")
    pair = None
    for f in frames:
        t = f.get("t")
        if t == full:
            g = _stamp_field(f, "gen")
            pair = (g, 0) if g is not None else None
        elif t == delta and (slot == "feed" or f.get("slot") == "bars"):
            g = _stamp_field(f, "gen")
            if g is None or pair is None:
                continue
            through, new_gen = _stamp_field(f, "through"), _stamp_field(f, "newGen")
            if through is None:
                continue   # a stamped delta carrying no through is refused by the client and applies nothing: the pair stands
            pair = (new_gen if new_gen is not None else g, through)
    return pair


def drive_pair(tc, frames, slot):
    """held_pair over a lab's recorded drive, telling "no gen key" from "a gen key the client reads as none". A hook records
    `genKey` (a bool: the frame carried a `gen` key, whatever its value; no content) beside the parsed stamp fields, and
    _stamp_field drops a gen the client would refuse (view-deltas.ts genOf: a number, an empty string, a '.' or ','), so
    held_pair alone reads a kernel stamping an unreadable gen exactly as one stamping none. None only when NO recorded frame
    carried the key (a kernel before the stamp: the leg's skip-and-branch case); a frame carried the key but no pair parsed
    is a failure on `tc`: the kernel stamped a gen the client reads as none, a stamped full was followed by a gen-less one
    (the rollback shape), or the key rode a frame this rule reads no pair from (a delta while no full carried one, or a
    frame of another type) while the full carried none, none of which a leg may pass green as "undeclared"."""
    pair = held_pair(frames, slot)
    if pair is None and any(f.get("genKey") for f in frames):
        tc.fail("a frame carried a gen key but no pair parsed for %r: the kernel stamped a gen the client reads as none "
                "(view-deltas.ts genOf), a stamped full was followed by a gen-less one, or the key rode a frame this rule reads "
                "no pair from (a delta while no full carried one, or a frame of another type) while the full carried none: %r"
                % (slot, frames))
    return pair


def composed_frames(frames, slot):
    """The recorded deltas of `slot` whose `newGen` parsed (_stamp_field): the composed frame a declaring dial earns. A
    per-cycle K2 delta carries `through` (equal to its rev) and no `newGen`, so `through` never tells a composed frame; the
    labs count the composed frame by this and never by `through`."""
    delta = "feedDelta" if slot == "feed" else "delta"
    return [f for f in frames if f.get("t") == delta and (slot == "feed" or f.get("slot") == "bars")
            and _stamp_field(f, "newGen") is not None]


def expected_relay_caps(prev_frames):
    """The caps term a relay dial carries: REMOTE_DIAL_CAPS, then held:feed:<g>.<r> and held:bars:<g>.<r> for the pairs the
    host's EARLIER relay sockets left the conn (held_pair over their recorded frames in arrival order: the client keeps a
    base holding a gen across a redial, so a third dial declares what the whole stream left, not what one socket
    received), each omitted when none is held. `prev_frames` is None for a first dial (no socket before it). A redial
    none of whose earlier sockets recorded a frame is an empty drive and an AssertionError: the expectation never rests on
    nothing."""
    if prev_frames is None:
        return REMOTE_DIAL_CAPS
    if not prev_frames:
        raise AssertionError("the host's earlier relay sockets recorded no frames: no drive to derive the redial's caps term from")
    words = [REMOTE_DIAL_CAPS]
    for slot in ("feed", "bars"):
        pair = held_pair(prev_frames, slot)
        if pair is not None:
            words.append("held:%s:%s.%d" % (slot, pair[0], pair[1]))
    return ",".join(words)


def relay_dials(dials):
    """[(index, host, url)] for every /remote/<host>/ws dial among `dials`, the page's dials in order (the index is the hook's
    socket index, the `sock` its frame records carry). Guarded non-empty."""
    out = []
    for i, u in enumerate(dials):
        m = re.search(r"/remote/([^/]+)/ws", u)
        if m:
            out.append((i, unquote(m.group(1)), u))
    if not out:
        raise AssertionError("the page dialed no relay socket: %r" % (dials,))
    return out


def assert_relay_dials(tc, app, dials, frames, caps=True):
    """Every relay dial the page made carries `app`, delta=1 and the caps term expected_relay_caps derives from the frames
    EVERY earlier relay socket of the host received, in arrival order (`frames`: the hook's records, each naming its socket
    index under `sock`; the recorded order is the page's, and a frame the page discarded after abandoning its socket is not
    modelled), or no caps term where the lab strips it (caps False). Returns the dials checked, [(index, host, url)]."""
    earlier = {}   # host -> the socket indices of its earlier relay dials
    checked = relay_dials(dials)
    for i, host, u in checked:
        qs = parse_qs(urlsplit(u).query)
        tc.assertEqual(qs.get("app"), [app], "the pane's app on the relay dial: %r" % (u,))
        tc.assertEqual(qs.get("delta"), ["1"], "the page's delta term rides the relay dial (since 2026-09-15): %r" % (u,))
        drive = [f for f in frames or [] if f.get("sock") in earlier[host]] if host in earlier else None
        expected = expected_relay_caps(drive) if caps else None
        tc.assertEqual(qs.get("caps"), ([expected] if expected else None),
                       "the relay dial's caps term: federation's decoder word and the held members its conn's bases give it, "
                       "derived from the frames the host's earlier sockets received (none on a first dial), or no term where the page strips it: %r" % (u,))
        earlier.setdefault(host, set()).add(i)
    return checked


SEED_PAIRS = 6         # closed pairs per seed transcript: one bar each on the timeline
SEED_PAIR_S = 720      # a stamped seed (t0 given): pair i's user row at t0 + SEED_PAIR_S * i, its assistant row SEED_REPLY_S later
SEED_REPLY_S = 30


def _stamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def seed_uuid(tag, i, role="a"):
    """The uuid _transcript mints for pair `i` of a seed with `tag` ("u" the user row, "a" the assistant row): a later
    append chains its parentUuid to the seed's last assistant row (the bars lab, the corners' transcript change)."""
    return "%s-%s%02d" % (tag, role, i)


def _transcript(sid, tag, cwd, pairs, t0=None):
    """`pairs` CLOSED user/assistant turns for `sid` (an OPEN turn would invite the boot reconcile to resume it).
    Stamped in 2024 by default; with `t0` (epoch seconds) pair i is stamped at t0 + SEED_PAIR_S * i and its reply
    SEED_REPLY_S later, so a lab's timeline page shows the seed as a board of the last hours in plain time. The
    kernel filters no bar by time, and the pane's default view collapses idle gaps, so it draws a 2024 seed too
    (the idle span since is squeezed to a gap); the stamps are for the record's readability and the plain-time
    view, not a condition of the bars being drawn (tests/test_federated_bars_delta_served.py, driven both ways)."""
    out, parent = [], None
    filler = ["The ranking pass reads its weights from the notes-api config now.",
              "Tokenizer edge cases (hyphens, quotes) are covered by the new fixture set.",
              "Index rebuild time is dominated by the stemmer; caching its table halves it."]
    for i in range(pairs):
        u, a = seed_uuid(tag, i, "u"), seed_uuid(tag, i, "a")
        if t0 is None:
            ts_u, ts_a = "2024-01-01T00:%02d:00Z" % (i % 60), "2024-01-01T00:%02d:30Z" % (i % 60)
        else:
            ts_u, ts_a = _stamp(t0 + SEED_PAIR_S * i), _stamp(t0 + SEED_PAIR_S * i + SEED_REPLY_S)
        out.append({"type": "user", "uuid": u, "parentUuid": parent, "sessionId": sid, "cwd": cwd,
                    "timestamp": ts_u, "promptSource": "typed",
                    "message": {"role": "user", "content": "turn %d: what changed in the notes-api search?" % i}})
        out.append({"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": sid, "cwd": cwd,
                    "timestamp": ts_a,
                    "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                                "content": [{"type": "text", "text": filler[i % len(filler)]}]}})
        parent = a
    return "".join(json.dumps(r) + "\n" for r in out)


def _kernel(lab, name, port, token, sessions, bin_dir=BIN, t0=None):
    """Boot one hermetic kernel: its own state root and dist, and `sessions` [(sid, name, tag)] with closed-turn transcripts.
    `bin_dir` is the checkout whose bin/romp-kernel runs: this one by default; another vintage's for a mixed-build lab
    (tests/test_federated_capability_corners_served.py boots an older remote or hub against this checkout's pages).
    `t0` stamps the seed transcripts from that epoch (see _transcript); None keeps the 2024 stamps."""
    state = os.path.join(lab, name, "xdg", "romp")
    claude = os.path.join(lab, name, "claude")
    cwd = os.path.join(lab, name, "proj")
    for d in ("names", "sdk", "states"):
        os.makedirs(os.path.join(state, d), exist_ok=True)
    os.makedirs(cwd, exist_ok=True)
    Path(state, "session-hosts").write_text("off\n")   # a lab root writes its own hosts off (the conftest rule)
    Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))   # park sends
    proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
    os.makedirs(proj, exist_ok=True)
    for sid, sname, tag in sessions:
        Path(state, "names", sid).write_text("%s\t%s\t\t\n" % (sname, cwd))
        Path(state, "sdk", sid + ".json").write_text(json.dumps(
            {"sid": sid, "name": sname, "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True}))
        Path(proj, sid + ".jsonl").write_text(_transcript(sid, tag, cwd, SEED_PAIRS, t0=t0))
    env = _lab.kernel_env(os.path.join(lab, name), claude, os.path.join(lab, "dist"), port, token, ROMP_HOST_NAME=name.upper())
    log = os.path.join(lab, name + "-kernel.log")
    proc = subprocess.Popen([os.path.join(bin_dir, "romp-kernel")], stdout=open(log, "w"), stderr=subprocess.STDOUT, env=env)
    for _ in range(120):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/healthz" % port, timeout=1)
            return proc, log
        except Exception:
            time.sleep(0.5)
    proc.kill(); proc.wait()
    raise unittest.SkipTest("hermetic kernel %s never served /healthz here" % name)


CHANGE_USER_AGO_S = 60    # an appended pair (change_pair): the user row this long before `now`, the reply CHANGE_REPLY_AGO_S before it
CHANGE_REPLY_AGO_S = 30


def change_pair(sid, tag, cwd, prompt, reply, now=None, pairs=SEED_PAIRS):
    """One CLOSED user/assistant pair to append to a seed transcript as a lab's change: fresh uuids, chained to the seed's
    last assistant row (seed_uuid), the user row CHANGE_USER_AGO_S before `now` and the reply CHANGE_REPLY_AGO_S before
    it. Closed, because an open turn on a registry-alive session invites the SDK backend's reconcile; staggered,
    because the timeline pane culls a bar whose start equals its end; both at or before now, because the pane clips a
    bar's end to the live edge. Returns the rows as jsonl text."""
    now = time.time() if now is None else now
    u, a = str(uuid.uuid4()), str(uuid.uuid4())
    rows = [{"type": "user", "uuid": u, "parentUuid": seed_uuid(tag, pairs - 1, "a"), "sessionId": sid, "cwd": cwd,
             "timestamp": _stamp(now - CHANGE_USER_AGO_S), "promptSource": "typed",
             "message": {"role": "user", "content": prompt}},
            {"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": sid, "cwd": cwd,
             "timestamp": _stamp(now - CHANGE_REPLY_AGO_S),
             "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": reply}]}}]
    return "".join(json.dumps(r) + "\n" for r in rows)


def checkin(hport, htoken, rport, rtoken, host=HOST):
    """Check the remote kernel in with the hub (POST /checkin) and wait until the hub reports the peer up with its token
    (the hub's supervisor probes the peer and reports it up; the browser dials only then). A refusal or a peer that
    never comes up skips the lab."""
    body = json.dumps({"host": host, "kernelPort": rport, "busPort": _free_port(), "token": rtoken}).encode()
    req = urllib.request.Request("http://127.0.0.1:%d/checkin?token=%s" % (hport, htoken), data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        ans = json.loads(resp.read().decode())
    if not ans.get("ok"):
        raise unittest.SkipTest("the hub refused the check-in: %r" % ans)
    rows = []
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/tunnels?token=%s" % (hport, htoken), timeout=3) as r2:
                rows = json.loads(r2.read().decode()).get("tunnels") or []
        except Exception:
            rows = []
        row = next((t for t in rows if t.get("host") == host), None)
        if row and row.get("status") == "up" and row.get("hasToken"):
            return
        time.sleep(0.5)
    raise unittest.SkipTest("the hub never reported the checked-in peer up: %r" % (rows,))


# The Chromium driver: hook every socket URL the page dials (window.__dials) and, on a relay socket, every frame it
# receives by its socket index, type, slot and stamp fields (window.__frames: no content; the drive expected_relay_caps
# reads), persist the watched tab as a REMOTE session before the page's scripts run (the shim's ?active= and
# __rompDialTerms read it), open the hub's /chat page in a skeleton posture, and wait for the relay socket to the remote.
# The kernel-side observables (the remote's /perf and client-diag) are read from Python after this returns.
DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const context = await browser.newContext({ viewport: { width: 1200, height: 700 } });
const page = await context.newPage();
const out = { dials: [], frames: [], died: null, tabSeen: false };
page.on("pageerror", () => {});
await page.addInitScript(() => {
  window.__dials = []; window.__frames = []; const W = window.WebSocket;
  window.WebSocket = function (url, protos) {
    const u = String(url); const idx = window.__dials.length; window.__dials.push(u);
    const w = protos === undefined ? new W(u) : new W(u, protos);
    if (u.indexOf("/remote/") !== -1) {
      w.addEventListener("message", (ev) => {
        try {
          const m = JSON.parse(ev.data);
          if (m && m.type !== "ka") {
            const f = { sock: idx, t: String(m.type), slot: m.slot ? String(m.slot) : "" };
            for (const k of ["gen", "newGen", "base", "rev", "through"]) if (typeof m[k] === "number" || (typeof m[k] === "string" && (k === "gen" || k === "newGen"))) f[k] = m[k];   // the revs as numbers, the gens as the kernel's strings; no content
            if ("gen" in m) f.genKey = true;   // the key's presence, whatever its value: drive_pair tells an unreadable gen from none
            window.__frames.push(f);
          }
        } catch (e) {}
      });
    }
    return w;
  };
  window.WebSocket.prototype = W.prototype; window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1; window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
});
// the watched tab is a REMOTE session, host-prefixed as the dashboard carries it: __rompDialTerms carries it
// to the remote dial, where federation.ts strips the host to the bare sid the remote knows
await page.addInitScript((rid) => { try { localStorage.setItem("romp-vscode-state-chat", JSON.stringify({ activeId: rid })); } catch (e) {} }, cfg.remote0);
try {
  await page.goto(cfg.chat);
  // the FederationManager attaches every checked-in remote on load; wait for its relay socket to be dialed
  await page.waitForFunction(() => (window.__dials || []).some((u) => u.indexOf("/remote/TESTHOST/ws") !== -1), null, { timeout: 30000 });
  // the remote tab surfaces once the relay is open (best-effort confirmation; the assertions read __dials + the remote kernel)
  try { await page.locator("#tabs .tab", { hasText: "TESTHOST" }).first().waitFor({ timeout: 15000 }); out.tabSeen = true; } catch (e) {}
  // let the remote serve the skeleton client: the watched tab full, the cold tab skipped, the relay wsopen row filed
  await page.waitForTimeout(3000);
  Object.assign(out, await page.evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice() })));
} catch (e) {
  out.died = String(e).slice(0, 400);
  try { Object.assign(out, await page.evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice() }))); } catch (e2) {}
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


# gens in the kernel's form (the boot's 16-hex token, '-', a decimal counter), for the rule's own tests
GEN_STAMP = "0123456789abcdef"
GEN, GEN2, GEN3 = GEN_STAMP + "-7", GEN_STAMP + "-9", GEN_STAMP + "-3"


class HeldPairRule(unittest.TestCase):
    """The drive-derived expectation's rule, pinned on synthetic frame records (no kernel): the labs above run against kernels
    whose frames carry no gen, so the stamped arms of held_pair, expected_relay_caps and assert_relay_dials are exercised
    here alone until a kernel stamps its frames."""

    def test_a_full_carrying_gen_leaves_gen_0_and_a_gen_less_full_clears_the_pair(self):
        self.assertEqual(held_pair([{"t": "feed", "gen": GEN}], "feed"), (GEN, 0))
        self.assertIsNone(held_pair([{"t": "feed"}], "feed"), "a kernel before the stamp: no pair")
        self.assertIsNone(held_pair([{"t": "feed", "gen": GEN}, {"t": "feed"}], "feed"), "a gen-less full after a stamped one clears the pair (a rollback)")
        self.assertIsNone(held_pair([], "feed"))

    def test_the_gens_form_is_the_kernels_string_and_anything_else_reads_as_no_stamp(self):
        # the client's genOf (view-deltas.ts): a non-empty string holding neither '.' nor ','; a number, an empty string, a bool
        # or a string carrying either separator is no stamp, so the full leaves no pair (and the hook's record of it is dropped)
        for bad in (7, 0, "", GEN_STAMP + ".7", GEN_STAMP + ",7", True, None):
            self.assertIsNone(held_pair([{"t": "feed", "gen": bad}], "feed"), repr(bad))
            self.assertIsNone(_stamp_field({"gen": bad}, "gen"), repr(bad))
        self.assertEqual(held_pair([{"t": "feed", "gen": GEN}], "feed"), (GEN, 0))
        self.assertEqual(_stamp_field({"rev": 3}, "rev"), 3)
        for bad in ("3", -1, True, None):
            self.assertIsNone(_stamp_field({"rev": bad}, "rev"), "a rev is a non-negative int: %r" % (bad,))

    def test_a_stamped_delta_advances_the_pair_and_a_gen_less_one_moves_nothing(self):
        frames = [{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(frames, "feed"), (GEN, 1), "a per-cycle stamped delta: (gen, rev)")
        self.assertEqual(held_pair([{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1}], "feed"), (GEN, 0),
                         "a stamped delta carrying no through is refused by the client and moves nothing: every stamped delta carries through")
        frames.append({"t": "feedDelta", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4})
        self.assertEqual(held_pair(frames, "feed"), (GEN2, 4), "a composed frame: (newGen, through)")
        frames.append({"t": "feedDelta", "base": 4, "rev": 5})
        self.assertEqual(held_pair(frames, "feed"), (GEN2, 4), "a gen-less delta moves nothing")
        self.assertIsNone(held_pair([{"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}], "feed"), "a delta before any full: nothing held")

    def test_a_per_cycle_stamped_delta_carrying_through_equal_to_its_rev_leaves_gen_rev(self):
        # the stamping kernel's per-cycle shape: every delta carries gen, base, rev AND through, through equal to rev and no
        # newGen; through's presence does not make it a composed frame, and the pair is (gen, through), through equal to rev
        frames = [{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(frames, "feed"), (GEN, 1))
        frames.append({"t": "feedDelta", "gen": GEN, "base": 1, "rev": 2, "through": 2})
        self.assertEqual(held_pair(frames, "feed"), (GEN, 2))
        bars = [{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "gen": GEN3, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(bars, "bars"), (GEN3, 1))

    def test_the_bars_slot_reads_bars_fulls_and_bars_patches_alone(self):
        frames = [{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "gen": GEN3, "base": 0, "rev": 1, "through": 1},
                  {"t": "delta", "slot": "lanes", "gen": GEN3, "base": 1, "rev": 2, "through": 2}, {"t": "feed", "gen": GEN}]
        self.assertEqual(held_pair(frames, "bars"), (GEN3, 1), "another slot's patch and the feed full do not move the bars pair")
        self.assertEqual(held_pair(frames, "feed"), (GEN, 0))

    def test_drive_pair_skips_on_no_gen_key_and_fails_on_an_unparsed_one(self):
        # the labs' skip-and-branch read: None only when no recorded frame carried a gen key (the leg skips or takes the undeclared
        # arm); a gen key present with a pair parsed is that pair; a gen key present and no pair parsed (a gen the client reads
        # as none, which a hook's record drops) fails, never "undeclared"
        self.assertIsNone(drive_pair(self, [{"t": "feed"}], "feed"), "no gen key on any frame: a kernel before the stamp")
        self.assertIsNone(drive_pair(self, [{"t": "feed"}, {"t": "caps"}, {"t": "feedDelta", "base": 0, "rev": 1}], "feed"))
        self.assertEqual(drive_pair(self, [{"t": "feed", "gen": GEN, "genKey": True}], "feed"), (GEN, 0))
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed", "gen": GEN_STAMP + ".7", "genKey": True}], "feed")   # the key with a gen genOf refuses
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed", "genKey": True}], "feed")   # the same frame as a hook records it: the value dropped, the key noted
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed", "gen": GEN, "genKey": True}, {"t": "feed"}], "feed")   # a stamped full then a gen-less one
        # the third failing shape (peer read, 2026-09-19): the key rode a frame the rule reads no pair from while the full carried
        # none, a stamped delta onto no held pair or a frame of another type; the verdict is the same fail, never "undeclared"
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed"}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], "feed")
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed"}, {"t": "caps", "genKey": True}], "feed")

    def test_composed_frames_are_the_deltas_carrying_newGen(self):
        # a per-cycle K2 delta carries through and no newGen, so through never tells a composed frame; a newGen the client reads as
        # none (a '.' in it) is no composed frame either
        per_cycle = {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}
        composed = {"t": "feedDelta", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4}
        bad = {"t": "feedDelta", "gen": GEN, "newGen": GEN_STAMP + ".9", "base": 4, "rev": 5, "through": 5}
        self.assertEqual(composed_frames([{"t": "feed", "gen": GEN}, per_cycle], "feed"), [], "through and no newGen: not composed")
        self.assertEqual(composed_frames([{"t": "feed", "gen": GEN}, per_cycle, composed, bad], "feed"), [composed])
        bars = {"t": "delta", "slot": "bars", "gen": GEN3, "newGen": GEN2, "base": 0, "rev": 2, "through": 2}
        self.assertEqual(composed_frames([{"t": "bars", "gen": GEN3}, bars, composed], "bars"), [bars], "the bars slot reads bars patches alone")
        self.assertEqual(composed_frames([], "feed"), [])

    def test_expected_relay_caps_is_the_decoder_word_plus_each_held_member_and_fails_on_an_empty_drive(self):
        self.assertEqual(expected_relay_caps(None), "feedDelta", "a first dial: no socket before it")
        self.assertEqual(expected_relay_caps([{"t": "feed"}, {"t": "caps"}]), "feedDelta", "a redial after gen-less frames: undeclared")
        self.assertEqual(expected_relay_caps([{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 2, "through": 2}]), "feedDelta,held:feed:%s.2" % GEN)
        self.assertEqual(expected_relay_caps([{"t": "bars", "gen": GEN3}]), "feedDelta,held:bars:%s.0" % GEN3)
        self.assertEqual(expected_relay_caps([{"t": "feed", "gen": GEN}, {"t": "bars", "gen": GEN3}]), "feedDelta,held:feed:%s.0,held:bars:%s.0" % (GEN, GEN3), "both, feed first")
        with self.assertRaises(AssertionError):
            expected_relay_caps([])   # a redial none of whose earlier sockets recorded a frame: no drive

    def test_assert_relay_dials_derives_a_later_redials_member_from_every_earlier_socket_of_the_host(self):
        # the client keeps a base holding a gen across a redial, so socket 2's composed frame applies onto what socket 1 left and
        # the THIRD dial declares (newGen, through), the pair the whole stream left; read from socket 2's frames alone it would
        # be nothing (a composed frame onto no full), a false red on a correct client
        relay = "ws://hub.local:1/remote/TESTHOST/ws?app=feed&delta=1&caps="
        dials = ["ws://hub.local:1/ws?app=feed&delta=1", relay + "feedDelta",
                 relay + quote("feedDelta,held:feed:%s.1" % GEN, safe=""), relay + quote("feedDelta,held:feed:%s.4" % GEN2, safe="")]
        frames = [{"sock": 1, "t": "feed", "gen": GEN}, {"sock": 1, "t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1},
                  {"sock": 2, "t": "caps"}, {"sock": 2, "t": "feedDelta", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4}]
        self.assertEqual([i for i, _h, _u in assert_relay_dials(self, "feed", dials, frames)], [1, 2, 3])
        # the middle socket recorded nothing (it dropped before a frame): the pair socket 1 left stands, the base kept across
        # the redial, so the third dial declares it and the drive is not empty
        assert_relay_dials(self, "feed", dials[:3] + [dials[2]], [f for f in frames if f["sock"] == 1])
        # a third dial declaring only what socket 1 left where socket 2 composed onward is the wrong term
        with self.assertRaises(AssertionError):
            assert_relay_dials(self, "feed", dials[:3] + [dials[2]], frames)
        # an empty drive: no frame on ANY earlier socket of the host
        with self.assertRaises(AssertionError):
            assert_relay_dials(self, "feed", dials[:3], [])


class FederatedDialTerms(unittest.TestCase):
    """Two kernels (a hub and a checked-in TESTHOST), one page, one driver run in setUpClass; each method asserts one observable."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.procs = []
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here), the served lab needs them")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box, the served lab needs one (CI installs none)")
        cls.lab = tempfile.mkdtemp(prefix="federated-dial-terms-")
        lab_dist.copy_dist(os.path.join(cls.lab, "dist"))   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        # the REMOTE owns both sessions (the watched tab + a cold one); the HUB owns none and shows them through the relay
        cls.rport, cls.rtoken = _free_port(), "testtok-remote-fed"
        cls.hport, cls.htoken = _free_port(), "testtok-hub-fed"
        rp, cls.rlog = _kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)])
        cls.procs.append(rp)
        hp, cls.hlog = _kernel(cls.lab, "hub", cls.hport, cls.htoken, [])
        cls.procs.append(hp)
        body = json.dumps({"host": HOST, "kernelPort": cls.rport, "busPort": _free_port(), "token": cls.rtoken}).encode()
        req = urllib.request.Request("http://127.0.0.1:%d/checkin?token=%s" % (cls.hport, cls.htoken), data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            ans = json.loads(resp.read().decode())
        if not ans.get("ok"):
            raise unittest.SkipTest("the hub refused the check-in: %r" % ans)
        rows = []
        for _ in range(60):   # the hub's supervisor probes the peer and reports it up; the browser dials only then
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/tunnels?token=%s" % (cls.hport, cls.htoken), timeout=3) as r2:
                    rows = json.loads(r2.read().decode()).get("tunnels") or []
            except Exception:
                rows = []
            row = next((t for t in rows if t.get("host") == HOST), None)
            if row and row.get("status") == "up" and row.get("hasToken"):
                break
            time.sleep(0.5)
        else:
            raise unittest.SkipTest("the hub never reported the checked-in peer up: %r" % (rows,))
        cls.result, cls.driver_error = None, None
        cls._drive()
        cls.remote_chat_perf = cls._poll_remote_chat_perf()
        cls.remote_relay_rows = cls._read_relay_wsopen_rows()

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"chat": "http://127.0.0.1:%d/chat?skeleton=1&wid=%s&token=%s" % (cls.hport, WID, cls.htoken),
                       "remote0": REMOTE0}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=240,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            cls.driver_error = "driver timed out; partial output:\n%s" % so
            return
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box, the served leg needs one (CI installs none)")
        if p.returncode != 0:
            cls.driver_error = "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            cls.driver_error = "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        cls.result = json.loads(line[len("RESULT:"):])

    @classmethod
    def _poll_remote_chat_perf(cls):
        """The remote's builds.chat counters, once its push cycle has served the hub's skeleton client (a bounded
        retry, as the /tunnels poll above: no busy loop). At the base the dial states no diet and coldSkipped stays 0."""
        chat = {}
        for _ in range(20):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=3) as r:
                    perf = json.loads(r.read().decode())
                chat = (perf.get("builds") or {}).get("chat") or {}
            except Exception:
                chat = {}
            if chat.get("coldSkipped"):
                break
            time.sleep(0.5)
        return chat

    @classmethod
    def _read_relay_wsopen_rows(cls):
        """The remote kernel's wsopen rows of kind 'relay' (the hub's spliced dial). data.iid is a PRESENCE flag,
        not the value (kernel.py _note_ws_open): true names a per-pane iid, false is the anonymous relay."""
        path = os.path.join(cls.lab, "testhost", "xdg", "romp", "client-diag.jsonl")
        rows = []
        for _ in range(20):
            rows = []
            try:
                with open(path) as fh:
                    for ln in fh:
                        try:
                            rec = json.loads(ln)
                        except ValueError:
                            continue
                        if rec.get("what") == "wsopen" and (rec.get("data") or {}).get("kind") == "relay":
                            rows.append(rec)
            except OSError:
                rows = []
            if rows:
                break
            time.sleep(0.3)
        return rows

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "procs", []):
            try:
                p.kill(); p.wait()
            except Exception:
                pass
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _driver_ran(self):
        if getattr(type(self), "driver_error", None):
            self.fail(type(self).driver_error)
        if getattr(type(self), "result", None) is None:
            raise unittest.SkipTest("the driver produced no result")

    def _relay_dial(self):
        self._driver_ran()
        relay = [u for u in self.result["dials"] if "/remote/TESTHOST/ws" in u]
        self.assertTrue(relay, "the hub page dialed the remote's relay socket: %r" % self.result["dials"])
        return relay[0]

    def test_the_hub_dials_the_remote_relay_socket(self):
        self.assertTrue(self._relay_dial())

    def test_the_remote_dial_carries_the_pages_terms(self):
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        self.assertEqual(qs.get("app"), ["chat"], "the pane's app")
        self.assertEqual(qs.get("delta"), ["1"], "delta rides every dial, as the local pane's does")
        self.assertEqual(qs.get("skeleton"), ["1"], "the page's skeleton posture rode the remote dial")
        self.assertEqual(qs.get("active"), [SID_R0], "the watched remote tab, stripped to its bare sid")

    def test_the_remote_dial_caps_term_is_the_decoder_word_and_the_members_its_conns_bases_hold(self):
        # derived from the drive (assert_relay_dials): a first dial has no socket before it and states the decoder word alone;
        # the frames the relay socket then received are what a redial's held member would be derived from, and on a kernel
        # whose frames carry no gen (this checkout's) that would be the decoder word alone too
        self._driver_ran()
        checked = assert_relay_dials(self, "chat", self.result["dials"], self.result.get("frames"))
        self.assertEqual([h for _i, h, _u in checked], [HOST], "one relay dial, to the checked-in host: %r" % (checked,))
        frames = [f for f in self.result.get("frames") or [] if f.get("sock") == checked[0][0]]
        self.assertTrue(frames, "the relay socket recorded the remote's frames (the drive a redial's member is derived from)")

    def test_the_remote_iid_is_namespaced_by_the_hub_wid(self):
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        iid = (qs.get("iid") or [""])[0]
        self.assertTrue(iid.startswith(WID + ":"),
                        "the iid a hub pane sends is namespaced by its wid so it cannot collide with the remote's own page: %r" % iid)
        self.assertGreater(len(iid), len(WID) + 1, "…and carries the page's own instance id after the prefix")

    def test_the_remote_diets_its_cold_tab_for_the_skeleton_client(self):
        self._driver_ran()
        self.assertGreater(self.remote_chat_perf.get("coldSkipped") or 0, 0,
                           "the remote skipped its cold tab for the hub's skeleton client: %r" % self.remote_chat_perf)

    def test_the_remote_relay_wsopen_row_names_a_per_pane_iid(self):
        self._driver_ran()
        rows = self.remote_relay_rows
        self.assertTrue(rows, "the remote filed a relay wsopen row for the hub's spliced dial")
        self.assertTrue(any((r.get("data") or {}).get("iid") for r in rows),
                        "a relay row names a per-pane iid (present), not the absent one that reads as an anonymous relay: %r"
                        % [r.get("data") for r in rows])


if __name__ == "__main__":
    unittest.main()
