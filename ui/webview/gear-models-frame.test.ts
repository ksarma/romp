// The settings gear's cached /models list follows the kernel's models frame — and is never overwritten by
// an OLDER response that lands late (fixer round 5, 2026-09-01). BEHAVIORAL: the cache block of gear.js
// (`var choices` through the models listener) is lifted out and run against a fake window and a
// controllable fetch, so these pin what the code DOES. The round-4 pin beside this file only matched the
// listener's text, which proved nothing about the frame reaching the gear or the cache moving — and the
// frame did not reach it: the kernel sent it to the chat and timeline apps while the gear lives in the
// FEED bundle (test_model_versions.py pins the kernel side).
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";

const GEAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.js"), "utf8");
const tick = () => new Promise((r) => setImmediate(r));

// A <select> stand-in with the spec's value semantics the paint relies on (fixer round 6, 2026-09-02):
// setting innerHTML resets the value; assigning a value selects it only if an option carries it, else
// "". The round-5 tests passed NULL selects (fillChoices guards each with `if (jm) …`), which is exactly
// why they could not see the pickers left empty — nothing was there to be empty.
type Sel = { innerHTML: string; value: string; options: string[] };
function sel(): Sel {
  const s: any = { _html: "", _v: "" };
  Object.defineProperty(s, "innerHTML", { get() { return s._html; }, set(h: string) { s._html = h; s._v = ""; } });
  Object.defineProperty(s, "options", { get() { return [...s._html.matchAll(/value="([^"]*)"/g)].map((m) => m[1]); } });
  Object.defineProperty(s, "value", { get() { return s._v; }, set(v: string) { s._v = s.options.includes(v) ? v : ""; } });
  return s as Sel;
}
const SELECTS = ["jm", "im", "je", "ie", "dm", "de", "cmm", "cme"] as const;

// The block, evaluated with the closure variables it reads passed in: `window` (the listener's target),
// `fetch`/`ku` (the read), and the eight <select>s — real stand-ins by default, or null (the guards).
function lift(withSelects = true) {
  const start = GEAR.indexOf("  var choices = null");
  const at = GEAR.indexOf("m.type !== 'models'", start);
  const stop = GEAR.indexOf("\n  });\n", at) + "\n  });\n".length;
  assert.ok(start > 0 && at > start && stop > at, "anchors not found — the gear's models cache block moved; re-anchor");
  const src = GEAR.slice(start, stop);
  const listeners: Array<(e: any) => void> = [];
  const win = { addEventListener: (type: string, fn: (e: any) => void) => { if (type === "message") listeners.push(fn); } };
  const pending: Array<(d: any) => void> = [];        // one resolver per fetch, in request order
  const fetchStub = (url: string) => {
    assert.equal(url, "/models");
    return new Promise<any>((res) => pending.push((d: any) => res({ json: async () => d })));
  };
  const S: Record<(typeof SELECTS)[number], Sel | null> = Object.fromEntries(SELECTS.map((k) => [k, withSelects ? sel() : null])) as any;
  const fn = new Function("window", "fetch", "ku", ...SELECTS,
    src + "\n  return { fillChoices: fillChoices, choices: function () { return choices; } };");
  const api = fn(win, fetchStub, (p: string) => p, ...SELECTS.map((k) => S[k]));
  const frame = (rev: number) => listeners.forEach((l) => l({ data: { type: "models", rev } }));
  return { api, listeners, pending, frame, S };
}
const list = (rev: number | undefined, def: string, versions: Array<{ value: string; label: string }> = []) =>
  ({ ...(rev === undefined ? {} : { rev }), models: [{ label: "Fable", value: "fable", default: def, versions }],
     efforts: [{ label: "High", value: "high" }] });

test("executed: the models frame re-reads /models and replaces the cache the family rows read at click time", async () => {
  const { api, listeners, pending, frame } = lift();
  assert.equal(listeners.length, 1, "the listener is registered on the window");
  const first = api.fillChoices();
  assert.equal(pending.length, 1, "the first fill fetches");
  pending[0](list(1, "claude-fable-5"));
  await first;
  assert.equal(api.choices().models[0].default, "claude-fable-5", "pinned");
  frame(2);                                              // the kernel: Latest un-pinned the family
  assert.equal(pending.length, 2, "the frame fetches again");
  pending[1](list(2, "fable"));
  await tick(); await tick();
  assert.equal(api.choices().models[0].default, "fable", "the next family click sends the alias");
  // a frame that names no type the gear knows, or an unrelated frame, fetches nothing
  listeners[0]({ data: { type: "palette" } });
  listeners[0]({ data: null });
  assert.equal(pending.length, 2);
});

test("executed: an OLDER /models response landing after a newer one is dropped — the newest rev applied wins", async () => {
  // the frame's re-read can overlap the first fill (or two quick frames each other), and the two responses
  // can resolve out of order: without the rev check the stale list overwrote the fresh one
  const { api, pending, frame } = lift();
  const first = api.fillChoices();                       // request 1, in flight
  frame(5);                                              // request 2
  assert.equal(pending.length, 2);
  pending[1](list(5, "fable"));                          // the newer answers first
  await tick(); await tick();
  assert.equal(api.choices().models[0].default, "fable");
  pending[0](list(4, "claude-fable-5"));                 // the older lands late
  await first; await tick();
  assert.equal(api.choices().models[0].default, "fable", "the stale first fill did not win");
  // and the same when two frames' reads cross
  frame(6); frame(7);
  pending[3](list(7, "claude-fable-5-1"));
  pending[2](list(6, "fable"));
  await tick(); await tick();
  assert.equal(api.choices().models[0].default, "claude-fable-5-1", "rev 7 applied; rev 6 dropped");
  assert.equal(api.choices().rev, 7);
});

test("a payload without a rev (an older kernel) always applies", async () => {
  const { api, pending, frame } = lift();
  const first = api.fillChoices();
  pending[0](list(3, "claude-fable-5"));
  await first;
  frame(4);
  pending[1](list(undefined, "fable"));
  await tick(); await tick();
  assert.equal(api.choices().models[0].default, "fable");
});

test("the round-5 guards still hold with no selects in the document", async () => {
  const { api, pending } = lift(false);
  const first = api.fillChoices();
  pending[0](list(1, "fable"));
  assert.equal((await first).models[0].default, "fable", "a fill with nothing to paint still returns the list");
});

test("executed: when the frame's re-read overtakes the page-load fill, every picker is still painted — from the list that won", async () => {
  // (fixer round 6, 2026-09-02) round 5 returned early from the page-load fill when the frame's re-read had
  // already applied a newer list, BEFORE writing any <option>s — and every later fill() short-circuited on
  // the cache, so all eight pickers stayed empty for the life of the page. The paint keys on the list.
  const V = [{ value: "claude-fable-5", label: "Fable 5" }];
  const { api, pending, frame, S } = lift();
  const first = api.fillChoices();                       // page load: request 1
  frame(6);                                              // a pick elsewhere during it: request 2
  pending[1](list(6, "fable", V));                       // request 2 resolves first
  await tick(); await tick();
  pending[0](list(5, "claude-fable-5", V));              // request 1 lands late, older
  await first; await tick();
  assert.equal(api.choices().models[0].default, "fable", "the newer list is the cache");
  for (const k of SELECTS) assert.ok(S[k]!.innerHTML.length > 0, `${k} is painted`);
  assert.deepEqual(S.jm!.options, ["fable", "claude-fable-5"], "family + version options, from the list that won");
  assert.deepEqual(S.je!.options, ["", "high"]);
  assert.deepEqual(S.dm!.options, ["triage", "fable", "claude-fable-5"], "the distilling sentinel leads");
  assert.deepEqual(S.de!.options, ["triage", "none", "high"]);
  assert.deepEqual(S.cmm!.options, ["session", "default", "fable", "claude-fable-5"], "the comment sentinels lead");
  assert.deepEqual(S.cme!.options, ["session", "high"]);
  // a later modal open (fill → fillChoices) is a cache hit and the pickers stay painted
  assert.equal((await api.fillChoices()).models[0].default, "fable");
  assert.equal(pending.length, 2, "no third fetch");
  S.jm!.value = "fable";
  assert.equal(S.jm!.value, "fable", "a pick can land on the painted options");
});

test("executed: a frame's repaint keeps the value each select held while the modal is up", async () => {
  // the round-4 listener never repainted BECAUSE a rewrite resets a select to its first option; the paint
  // gives every select its value back when the new list still offers it — which is why it can repaint
  const V = [{ value: "claude-fable-5", label: "Fable 5" }];
  const { api, pending, frame, S } = lift();
  const first = api.fillChoices();
  pending[0](list(1, "claude-fable-5", V));
  await first;
  S.jm!.value = "claude-fable-5"; S.je!.value = "high"; S.dm!.value = "fable"; S.cme!.value = "session";
  frame(2);                                              // Latest un-pinned the family elsewhere; a session learned 5.1
  const V2 = V.concat([{ value: "claude-fable-5-1", label: "Fable 5.1" }]);
  pending[1](list(2, "fable", V2));
  await tick(); await tick();
  assert.equal(api.choices().models[0].default, "fable", "the cache moved");
  assert.deepEqual(S.jm!.options, ["fable", "claude-fable-5", "claude-fable-5-1"], "…and so did the options");
  assert.deepEqual(S.cmm!.options, ["session", "default", "fable", "claude-fable-5", "claude-fable-5-1"]);
  assert.equal(S.jm!.value, "claude-fable-5", "the pinned version the user had selected is still selected");
  assert.equal(S.je!.value, "high");
  assert.equal(S.dm!.value, "fable");
  assert.equal(S.cme!.value, "session");
  // a stale response repaints nothing (the list did not move), so a value is never disturbed for no reason
  const html = S.jm!.innerHTML;
  frame(3); frame(4);
  pending[3](list(4, "fable", V2));                      // the newer, same list
  pending[2](list(3, "claude-fable-5", V));              // the older, dropped
  await tick(); await tick();
  assert.equal(api.choices().rev, 4);
  assert.equal(S.jm!.innerHTML, html);
  assert.equal(S.jm!.value, "claude-fable-5");
});
