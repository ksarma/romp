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

// The block, evaluated with the closure variables it reads passed in: `window` (the listener's target),
// `fetch`/`ku` (the read), and the eight <select>s as null — fillChoices guards each (`if (jm) …`).
function lift() {
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
  const fn = new Function("window", "fetch", "ku", "jm", "im", "je", "ie", "dm", "de", "cmm", "cme",
    src + "\n  return { fillChoices: fillChoices, choices: function () { return choices; } };");
  const api = fn(win, fetchStub, (p: string) => p, null, null, null, null, null, null, null, null);
  const frame = (rev: number) => listeners.forEach((l) => l({ data: { type: "models", rev } }));
  return { api, listeners, pending, frame };
}
const list = (rev: number | undefined, def: string) =>
  ({ ...(rev === undefined ? {} : { rev }), models: [{ label: "Fable", value: "fable", default: def, versions: [] }], efforts: [] });

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
