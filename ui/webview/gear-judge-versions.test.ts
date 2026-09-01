// The gear's judge MODEL pickers mirror the session pickers (the user 2026-08-25): families
// top-level, family click = the /models remembered default, a right-facing-caret side submenu of
// versions, right-preferred side (measured). The native select stays hidden as the value holder so
// fill()/mixed marks keep working, and version ids ride as options so any stored pick displays.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const GEAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.js"), "utf8");
const KERNEL = fs.readFileSync(path.resolve(process.cwd(), "..", "kernel", "kernel.py"), "utf8");

test("the three judge model selects grow the version menu; the select stays the value holder", () => {
  assert.match(GEAR, /function versionMenu\(sel, extraFirst\)/);
  assert.match(GEAR, /versionMenu\(jm\);\s*\n\s*versionMenu\(im\);\s*\n\s*versionMenu\(dm, \[\{ value: 'triage', label: 'Follow triage', versions: \[\] \}\]\);/,
    "judge, index, and distill (with its Follow-triage sentinel first)");
  assert.match(GEAR, /sel\.style\.display = 'none';/, "the native select hides — still the value holder");
  assert.match(GEAR, /sel\.dispatchEvent\(new Event\('change'\)\)/, "picks flow through the existing change→post wiring");
  assert.match(GEAR, /versions ride as options too/, "a stored version id still displays and mixed-marks");
  assert.match(GEAR, /pick\(fam\.default \|\| fam\.value\)/, "family click sends the remembered default");
});

test("caret faces RIGHT everywhere; the submenu side is measured with the right preference", () => {
  assert.match(GEAR, /caret\.textContent = '\\u25B8'/);
  assert.ok(!GEAR.includes("\\u25C2"), "no left-facing caret");
  assert.match(GEAR, /if \(rr\.right \+ 4 \+ sw <= window\.innerWidth - 8\) sub\.style\.left = Math\.round\(rr\.right \+ 4\) \+ 'px';/,
    "right side whenever it fits");
  assert.match(GEAR, /else sub\.style\.left = Math\.max\(8, Math\.round\(rr\.left\) - sw - 4\) \+ 'px';/,
    "left only as the measured fallback");
  assert.match(GEAR, /e\.key === 'romp:menu-echo' && e\.newValue/, "cross-pane dismissal adopted");
});

test("the kernel accepts version ids — seed AND learned — on every judge tier", () => {
  // the gear's selects are built from /models' versions, learned rows included, so every tier
  // validates against the LIVE set (_judge_model_values: the seed half ∪ what running sessions'
  // CLIs report) — the kernel never refuses a value it offered (review 2026-09-01)
  assert.match(KERNEL, /_JUDGE_MODEL_VALUES = _MODEL_VALUES \| set\(_VERSION_FAMILY\)/, "the seed half");
  assert.match(KERNEL, /def _judge_model_values\(\):[\s\S]{0,700}return _JUDGE_MODEL_VALUES \| \{v\["value"\] for vs in _learned_versions\(\)\.values\(\) for v in vs\}/,
    "…plus every learned id, computed per call");
  for (const tier of ["judge-model", "index-model"]) {
    assert.match(KERNEL, new RegExp(`_set_judge_state\\("${tier}", v, _judge_model_values\\(\\), gt=gt\\)`), tier);
  }
  assert.match(KERNEL, /_set_judge_state\("distill-model", v, _judge_model_values\(\) \| \{"triage"\}, gt=gt\)/);
  assert.match(KERNEL, /_set_judge_state\("comment-model", v, _judge_model_values\(\) \| \{"session", "default"\}, gt=gt\)/);
  assert.ok(!/_set_judge_state\("[a-z]+-model", v, _JUDGE_MODEL_VALUES/.test(KERNEL),
    "no tier validates against the seed-only set — a learned pick would be refused there");
});

test("the gear's version rows mark a learned version as new, like the chat and timeline pickers", () => {
  // (review 2026-09-01) the chat/timeline submenus wore the marker; the gear's judge/index/distill/
  // comment selects rendered the same learned rows bare — the fail-loudly marker on every surface
  assert.match(GEAR, /if \(v\.learned\) \{[\s\S]{0,600}tag\.textContent = ' new'/);
  assert.match(GEAR, /if \(v\.learned\) \{[\s\S]{0,600}font-size:0\.82em;opacity:0\.6/, "the menu vocabulary's sub-line size and opacity");
  assert.match(GEAR, /if \(v\.learned\) \{[\s\S]{0,600}r2\.title = /, "and says where the version came from");
});

test("the gear's version submenu opens with a Latest row that sends the bare family alias", () => {
  // the session pickers' floating gesture (review 2026-09-01), on the judge tiers too: a tier set
  // to a version stays there until picked off it, and the family row sends the remembered pin —
  // Latest is the row that sends the alias itself, so the tier follows the CLI's newest again
  assert.match(GEAR, /latest\.appendChild\(document\.createTextNode\('Latest'\)\)/);
  assert.match(GEAR, /latest\.addEventListener\('click', function \(e2\) \{ e2\.stopPropagation\(\); pick\(fam\.value\); \}\)/);
  assert.match(GEAR, /sub\.appendChild\(latest\);[\s\S]{0,300}versions\.forEach\(function \(v\)/, "heads the submenu, ahead of the versions");
});

test("the gear's cached /models list re-reads on the kernel's models frame (fixer round 4, 2026-09-01)", () => {
  // fillChoices caches the list after its first fetch and the family rows send `fam.default` from
  // that cache at click time — so a pin or a Latest un-pin made anywhere (this dashboard's chat
  // picker, another dashboard) left the gear's family rows sending a stale default. Event-keyed on
  // the kernel's models frame, like the settingStale listener beside it; never a poll. Only the
  // cache moves — re-filling the <option> sets would reset the selects' values.
  assert.match(GEAR, /if \(!m \|\| m\.type !== 'models'\) return;/);
  const at = GEAR.indexOf("m.type !== 'models'");
  const seg = GEAR.slice(at, at + 400);
  assert.ok(seg.includes("fetch(ku('/models'), { cache: 'no-store' })"), "the same endpoint fillChoices reads");
  assert.ok(seg.includes("if (d && Array.isArray(d.models)) choices = d;"), "replaces the cache the rows read at click time");
  assert.ok(!seg.includes("innerHTML"), "the option sets are left alone");
});
