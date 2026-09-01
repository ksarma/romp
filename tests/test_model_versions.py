#!/usr/bin/env python3
"""Model selectors expose VERSIONS (the user 2026-08-25): shorthand aliases resolve to the newest —
opus became Opus 5 — silently losing legacy versions that remain live on the API. The kernel's
/models now carries each family's versions (dateless alias ids, verified against the claude-api
reference) plus a DEFAULT: the most recent version the user picked for that family (model-picks.json,
a viewer pref like colormap), else the family ALIAS itself (2026-09-01: the seed table's head used to
stand in for the alias, so a bare family click pinned every session to claude-fable-5 while the
CLI's own `fable` alias moved on to Fable 5.1). The seed table is a SEED: ids a running session's
CLI reports (reg.liveModelId) join the version lists, marked `learned`. The pick memory hooks the
ONE choke point every set path flows through (_set_model_or_park). Synthetic only — hermetic temp
STATE."""
import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
SourceFileLoader("romp_event_model", os.path.join(BIN, "romp-event-model")).load_module()
SourceFileLoader("romp_judge", os.path.join(BIN, "romp-judge")).load_module()
km = SourceFileLoader("romp_kernel_mv", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd


class Catalog(unittest.TestCase):
    """The version catalog's own invariants."""

    def test_every_family_in_the_picker_has_a_version_list(self):
        for c in km.MODEL_CHOICES:
            self.assertIn(c["value"], km.MODEL_VERSIONS, c["value"])
            self.assertTrue(km.MODEL_VERSIONS[c["value"]], c["value"])

    def test_versions_are_dateless_aliases_newest_first(self):
        # ids verified against the claude-api reference (2026-08-25) — dateless aliases only,
        # and the head of each list is the family's newest (what the bare shorthand resolves to)
        for fam, vs in km.MODEL_VERSIONS.items():
            for v in vs:
                self.assertNotRegex(v["value"], r"-20\d{6}$", "dated snapshot id leaked in")
        self.assertEqual(km.MODEL_VERSIONS["opus"][0]["value"], "claude-opus-5")
        self.assertEqual(km.MODEL_VERSIONS["sonnet"][0]["value"], "claude-sonnet-5")
        self.assertIn("claude-opus-4-8", [v["value"] for v in km.MODEL_VERSIONS["opus"]],
                      "legacy versions live on the API stay pickable")

    def test_reverse_map_covers_every_version(self):
        for fam, vs in km.MODEL_VERSIONS.items():
            for v in vs:
                self.assertEqual(km._VERSION_FAMILY[v["value"]], fam)

    def test_the_seed_table_knows_fable_5_1(self):
        # verified against the installed CLI's catalog 2026-09-01 (2.1.257 resolves `fable` to
        # claude-fable-5-1) and the claude-api reference; the seed must not lag the CLI it drives
        self.assertEqual(km.MODEL_VERSIONS["fable"][0], {"value": "claude-fable-5-1", "label": "Fable 5.1"})
        self.assertIn("claude-fable-5", [v["value"] for v in km.MODEL_VERSIONS["fable"]],
                      "Fable 5 stays pickable as an explicit pin")


class PickMemory(unittest.TestCase):
    """Per-family last-picked defaults: written at the choke point, read into /models."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._state = jd.STATE
        jd.STATE = Path(self.td.name)

    def tearDown(self):
        jd.STATE = self._state
        self.td.cleanup()

    def test_a_version_pick_becomes_the_family_default_and_persists(self):
        self.assertEqual(km._model_picks(), {})
        km._note_model_pick("claude-opus-4-8")
        self.assertEqual(km._model_picks(), {"opus": "claude-opus-4-8"})
        # the store is the file (a restart re-reads it) — pin the on-disk shape
        self.assertEqual(json.loads((jd.STATE / km.MODEL_PICKS_FILE_NAME).read_text()),
                         {"opus": "claude-opus-4-8"})

    def test_a_family_shorthand_never_downgrades_an_explicit_legacy_pick(self):
        # THE ALIAS RULE (the user's design): clicking a family sends the REMEMBERED version, and a
        # bare shorthand reaching the setter records nothing — so an explicit Opus 4.8 pick is never
        # silently replaced by "opus" resolving to the newest.
        km._note_model_pick("claude-opus-4-8")
        km._note_model_pick("opus")
        km._note_model_pick("default")
        km._note_model_pick("total-nonsense")
        self.assertEqual(km._model_picks(), {"opus": "claude-opus-4-8"})

    def test_the_choke_point_records_picks_from_every_surface(self):
        # _set_model_or_park is what the WS setModel op, the chat /model command, and POST /new's
        # prefs all call — one hook covers every surface.
        class _BE:
            def set_model(self, sid, value):
                return True
        km._set_model_or_park(_BE(), "11111111-2222-3333-4444-555555555555", "claude-sonnet-4-6")
        self.assertEqual(km._model_picks().get("sonnet"), "claude-sonnet-4-6")

    def test_a_stale_or_foreign_entry_falls_back_on_read(self):
        (jd.STATE / km.MODEL_PICKS_FILE_NAME).write_text(json.dumps(
            {"opus": "claude-opus-9-9", "sonnet": "claude-opus-4-8", "haiku": "claude-haiku-4-5"}))
        self.assertEqual(km._model_picks(), {"haiku": "claude-haiku-4-5"},
                         "unknown ids and cross-family entries never poison the default")


class _ModelsServer(unittest.TestCase):
    """A kernel HTTP handler on a loopback port + a hermetic STATE, for the /models route tests."""

    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), km.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._state = jd.STATE
        jd.STATE = Path(self.td.name)

    def tearDown(self):
        jd.STATE = self._state
        self.td.cleanup()

    def _models(self):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/models" % self.port,
            headers={"X-Romp-Token": os.environ["ROMP_SERVE_TOKEN"]})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())


class ModelsRoute(_ModelsServer):
    """GET /models carries versions + default per family."""

    def test_each_family_carries_versions_and_a_default(self):
        d = self._models()
        rows = {m["value"]: m for m in d["models"]}
        self.assertEqual([v["value"] for v in rows["opus"]["versions"]],
                         [v["value"] for v in km.MODEL_VERSIONS["opus"]])
        self.assertIn("color", rows["opus"], "the colormap tint still rides every family row")
        for v in rows["opus"]["versions"]:
            self.assertFalse(v.get("learned"), "seed-table entries are not marked as learned")

    def test_a_family_with_no_pick_defaults_to_its_alias_not_the_seed_head(self):
        # THE BUG (2026-09-01): the default fell to MODEL_VERSIONS[fam][0], so a bare "Fable" click
        # pinned the session to claude-fable-5 — and when the CLI's `fable` alias advanced to Fable
        # 5.1, every picker-set session stayed behind. The alias is what the CLI resolves LIVE (the
        # authoritative source for "newest"), so a family click sends the alias.
        rows = {m["value"]: m for m in self._models()["models"]}
        for fam in ("fable", "opus", "sonnet", "haiku"):
            self.assertEqual(rows[fam]["default"], fam, "no pick yet → the family alias, never a pinned id")

    def test_the_default_follows_the_users_last_pick(self):
        km._note_model_pick("claude-opus-4-8")
        rows = {m["value"]: m for m in self._models()["models"]}
        self.assertEqual(rows["opus"]["default"], "claude-opus-4-8")
        self.assertEqual(rows["sonnet"]["default"], "sonnet", "other families unaffected: still the alias")

    def test_an_explicit_version_pick_pins_and_a_family_click_never_downgrades_it(self):
        # the version submenu is the ONE place a pin comes from; a later family click (which now
        # carries the alias) records nothing, so the remembered pin stands
        class _BE:
            calls = []

            def set_model(self, sid, value):
                self.calls.append(value)
                return True
        be = _BE()
        sid = "11111111-2222-3333-4444-555555555555"
        km._set_model_or_park(be, sid, "claude-opus-4-8")
        km._set_model_or_park(be, sid, "opus")
        self.assertEqual(be.calls, ["claude-opus-4-8", "opus"], "both reach the backend verbatim")
        rows = {m["value"]: m for m in self._models()["models"]}
        self.assertEqual(rows["opus"]["default"], "claude-opus-4-8", "the explicit pin survives the alias click")


class LearnedVersions(_ModelsServer):
    """The seed table is a SEED, not the catalog: a model id a running session's CLI actually reported
    (reg.liveModelId, persisted by the SDK backend's _learn_model) joins its family's version list —
    the CLI is the authoritative source for what it serves — and is marked so the pickers can say it
    is new rather than hide a live model behind a stale menu."""

    def _reg(self, sid, **fields):
        d = jd.STATE / "sdk"
        d.mkdir(parents=True, exist_ok=True)
        (d / (sid + ".json")).write_text(json.dumps({"sid": sid, "name": "web", "cwd": "/tmp", "alive": True, **fields}))

    def test_a_reported_id_outside_the_seed_table_joins_its_family_marked_learned(self):
        self._reg("11111111-2222-3333-4444-555555555501", liveModel="Opus 5.1", liveModelId="claude-opus-5-1")
        rows = {m["value"]: m for m in self._models()["models"]}
        vs = rows["opus"]["versions"]
        self.assertEqual(vs[0], {"value": "claude-opus-5-1", "label": "Opus 5.1", "learned": True},
                         "newest first — the learned 5.1 lands ahead of the seed's 5")
        self.assertEqual([v["value"] for v in vs[1:]], [v["value"] for v in km.MODEL_VERSIONS["opus"]])
        self.assertEqual(rows["opus"]["default"], "opus", "a learned id changes nothing about the alias default")

    def test_a_learned_id_is_pickable_and_remembered_like_a_seed_one(self):
        self._reg("11111111-2222-3333-4444-555555555501", liveModelId="claude-opus-5-1")
        km._note_model_pick("claude-opus-5-1")
        self.assertEqual(km._model_picks(), {"opus": "claude-opus-5-1"})
        rows = {m["value"]: m for m in self._models()["models"]}
        self.assertEqual(rows["opus"]["default"], "claude-opus-5-1")

    def test_ids_the_seed_already_covers_or_that_are_not_first_party_add_nothing(self):
        # a dated snapshot of a seed version shares its label → the seed's dateless alias covers it;
        # a provider-prefixed id and a non-model string are not the shape the pickers send
        self._reg("11111111-2222-3333-4444-555555555501", liveModelId="claude-opus-4-5-20251101")
        self._reg("11111111-2222-3333-4444-555555555502", liveModelId="us.anthropic.claude-opus-4-8-v1:0")
        self._reg("11111111-2222-3333-4444-555555555503", liveModelId="<synthetic>")
        rows = {m["value"]: m for m in self._models()["models"]}
        self.assertEqual([v["value"] for v in rows["opus"]["versions"]],
                         [v["value"] for v in km.MODEL_VERSIONS["opus"]])

    def test_a_context_tag_is_stripped_and_duplicates_collapse(self):
        # the CLI spells a 1M-context variant with a [1m] tail; two sessions on the same id → one row
        self._reg("11111111-2222-3333-4444-555555555501", liveModelId="claude-sonnet-5-1[1m]")
        self._reg("11111111-2222-3333-4444-555555555502", liveModelId="claude-sonnet-5-1")
        rows = {m["value"]: m for m in self._models()["models"]}
        learned = [v for v in rows["sonnet"]["versions"] if v.get("learned")]
        self.assertEqual(learned, [{"value": "claude-sonnet-5-1", "label": "Sonnet 5.1", "learned": True}])


class AliasMigration(unittest.TestCase):
    """One-time boot pass (2026-09-01), mirroring the CLI's own 2.1.257 `migration_fable5_to_fable_alias`:
    a stored model equal to a family's PRE-FIX seed head (what a bare family click used to record) becomes
    the family alias, so the next reconnect spawns `--model fable` and follows the CLI's newest. An
    explicit non-head pick is a deliberate pin and is left alone. Idempotent, loud, synthetic state."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self._state = jd.STATE
        jd.STATE = Path(self.td.name)
        (jd.STATE / "sdk").mkdir(parents=True)
        (jd.STATE / "sdk-defaults.json").write_text(json.dumps({"model": "claude-fable-5", "effort": "xhigh"}))
        (jd.STATE / km.MODEL_PICKS_FILE_NAME).write_text(json.dumps({"fable": "claude-fable-5", "opus": "claude-opus-4-8"}))
        self._reg("a", model="claude-fable-5", liveModel="Fable 5", alive=True)
        self._reg("b", model="claude-opus-4-8", alive=True)
        self._reg("c", alive=False)
        self._reg("d", model="claude-sonnet-5", alive=False)
        self._reg("e", model="claude-fable-5-1")

    def tearDown(self):
        jd.STATE = self._state
        self.td.cleanup()

    def _reg(self, sid, **fields):
        (jd.STATE / "sdk" / (sid + ".json")).write_text(json.dumps({"sid": sid, "name": sid, "cwd": "/tmp", **fields}))

    def _read(self, sid):
        return json.loads((jd.STATE / "sdk" / (sid + ".json")).read_text())

    def _snapshot(self):
        return {p.name: p.read_text() for p in jd.STATE.rglob("*.json")}

    def test_seed_heads_become_aliases_everywhere_and_explicit_pins_stand(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            n = km._model_alias_boot_pass()
        self.assertEqual(n, 4, "defaults + the fable pick + regs a and d")
        self.assertEqual(json.loads((jd.STATE / "sdk-defaults.json").read_text()), {"model": "fable", "effort": "xhigh"},
                         "the remembered default follows the alias; effort untouched")
        self.assertEqual(km._model_picks(), {"opus": "claude-opus-4-8"},
                         "a head recorded as a pick is dropped — an absent pick IS the alias in that store")
        a = self._read("a")
        self.assertEqual(a["model"], "fable", "the next reconnect spawns --model fable")
        self.assertEqual((a["liveModel"], a["alive"], a["name"]), ("Fable 5", True, "a"), "nothing else on the reg moves")
        self.assertEqual(self._read("b")["model"], "claude-opus-4-8", "an explicit legacy pin is deliberate")
        self.assertNotIn("model", self._read("c"), "a session on the account default stays that way")
        self.assertEqual(self._read("d")["model"], "sonnet", "every family's pre-fix head migrates, dead regs too")
        self.assertEqual(self._read("e")["model"], "claude-fable-5-1",
                         "a post-fix head was never a family-click artefact — an explicit pin, untouched")
        self.assertIn("model-alias", err.getvalue())
        self.assertIn("fable", err.getvalue(), "the stderr line names what moved")

    def test_idempotent_and_silent_once_done(self):
        with contextlib.redirect_stderr(io.StringIO()):
            km._model_alias_boot_pass()
        before = self._snapshot()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(km._model_alias_boot_pass(), 0)
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(err.getvalue(), "", "nothing to say when nothing moved")

    def test_nothing_to_migrate_on_a_fresh_state(self):
        for p in list(jd.STATE.rglob("*.json")):
            p.unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(km._model_alias_boot_pass(), 0)


if __name__ == "__main__":
    unittest.main()
