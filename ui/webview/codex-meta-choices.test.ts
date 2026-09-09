// A CODEX session's statusline menus speak Codex's vocabulary (docs/codex.md): the model/effort
// pickers read the /models payload's codex section, and its mode picker offers Sandboxed and
// Auto without exposing unsupported Claude modes. Source-pin over render.ts, the same style
// as picker-backend.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const TIMELINE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "romp-timeline-view.js"), "utf8");

test("the /models payload's codex section populates its own choice arrays (both surfaces)", () => {
  for (const src of [RENDER, TIMELINE]) {
    assert.match(src, /CODEX_MODEL_CHOICES/);
    assert.match(src, /CODEX_EFFORT_CHOICES/);
    assert.match(src, /d\.codex && Array\.isArray\(d\.codex\.models\)/);
    assert.match(src, /d\.codex && Array\.isArray\(d\.codex\.efforts\)/);
  }
});

test("menu construction picks the choice list by the session's backend", () => {
  assert.match(RENDER, /function metaChoices\(kind: MetaKind, st: Status\)/);
  assert.match(RENDER, /st\.backend === "codex"/);
  assert.match(RENDER, /const rows = metaChoices\(kind, s\.status\)\.filter\(/);
  assert.match(RENDER, /for \(const c of rows\) \{/);
  assert.match(TIMELINE, /s\.backend === 'codex'/);
  assert.match(TIMELINE, /\? \(kind === 'model' \? CODEX_MODEL_CHOICES : CODEX_EFFORT_CHOICES\)/);
});

test("Codex offers only its supported modes and opens the mode picker", () => {
  const choices = RENDER.match(/const CODEX_MODE_CHOICES: MetaChoice\[\] = \[([\s\S]*?)\n\];/)![1];
  assert.deepEqual([...choices.matchAll(/value: "([^"]+)"/g)].map(m => m[1]), ["sandboxed", "auto"]);
  assert.match(RENDER, /if \(kind === "mode"\) return CODEX_MODE_CHOICES;/);
  assert.doesNotMatch(RENDER, /if \(kind === "mode" && s\.status\.backend === "codex"\) return;/);
  assert.match(RENDER, /case "sandboxed": return "Sandboxed";/);
});

// The owner's Codex picker (2026-09-09) opened on a BLANK menu while the session's default badge showed:
// the kernel's codex section had `models: []` and no reason (a client in retry backoff, a failed
// model_list, or the /models gate closed when the tab loaded). The section now carries `error`, and a
// Codex menu with nothing to offer shows one non-clickable row naming it, re-reads /models on the open
// itself, and rebuilds when the list lands. Source-pinned, and the loader's slice is EXECUTED below.
test("a Codex menu with no list says why and re-reads /models instead of opening blank", () => {
  assert.match(RENDER, /let CODEX_MODELS_ERROR = "";/);
  assert.match(RENDER, /if \(d\.codex\) CODEX_MODELS_ERROR = typeof d\.codex\.error === "string" \? d\.codex\.error : "";/);
  assert.match(RENDER, /if \(onModelChoicesLoaded\) onModelChoicesLoaded\(\);/);
  assert.match(RENDER, /if \(!rows\.length && s\.status\.backend === "codex" && \(kind === "model" \|\| kind === "effort"\)\) \{/);
  assert.match(RENDER, /el\("div", "meta-item meta-empty"\)/);
  assert.match(RENDER, /"No model list from Codex"/);
  assert.match(RENDER, /sub\.textContent = CODEX_MODELS_ERROR \|\| "asking the Codex app-server for it now";/);
  // the open is the event: one fetch, and the hook rebuilds the SAME open menu when a list arrives
  const block = RENDER.slice(RENDER.indexOf("const empty = el(\"div\", \"meta-item meta-empty\")"), RENDER.indexOf("for (const c of rows) {"));
  assert.match(block, /onModelChoicesLoaded = \(\) => \{/);
  assert.match(block, /if \(metaMenuEl !== menu\) return;/);
  assert.match(block, /if \(now\.length\) \{ closeMetaMenu\(\); toggleMetaMenu\(kind, btn, forSid\); \}/);
  assert.match(block, /loadModelChoices\(\);/);
  // the wait wears the romp loader's dots beside its text (ui/CLAUDE.md), which the reason replaces
  assert.match(block, /if \(!CODEX_MODELS_ERROR\) sub\.appendChild\(metaDots\(\)\);/);
  assert.match(block, /else sub\.textContent = CODEX_MODELS_ERROR \|\| "no model list yet";/);
  assert.doesNotMatch(block, /sent no list/, "the post-read fallback never attributes an answer to the app-server");
  // a FAILED re-read tells the waiting menu (fail loudly): the row would otherwise promise an answer forever
  assert.match(RENDER, /\}\)\.catch\(\(e\) => \{\n(?:[^\n]*\n){1,4}?\s+if \(!onModelChoicesLoaded\) return;\n\s+CODEX_MODELS_ERROR = "could not read \/models: " \+ /);
  // the hook dies with its menu, so a late response never rebuilds a menu the user closed
  assert.match(RENDER, /metaMenuEl = null;\n  onModelChoicesLoaded = null;/);
  // the row is a statement, not a choice: no pointer, no hover wash
  const CSS = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "styles.css"), "utf8");
  assert.match(CSS, /\.meta-item\.meta-empty \{ cursor: default; \}/);
  assert.match(CSS, /\.meta-item\.meta-empty:hover \{ background: none; \}/);
  assert.match(CSS, /\.meta-item-sub \.meta-dots \{ margin-left: 5px;/);
});

// The loader, lifted from render.ts and transpiled (the models-rev.test.ts idiom): the codex section's
// `error` lands in CODEX_MODELS_ERROR, an absent or non-string one clears it, and the completion hook
// fires once per applied read.
function liftLoader() {
  const start = RENDER.indexOf("const MODEL_CHOICES: {");
  const fnAt = RENDER.indexOf("function loadModelChoices(): void {", start);
  const stop = RENDER.indexOf("\n}\n", fnAt) + 3;
  assert.ok(start > 0 && fnAt > start && stop > fnAt, "anchors not found; render.ts's models loader moved; re-anchor");
  const js = requireCjs("esbuild").transformSync(RENDER.slice(start, stop), { loader: "ts" }).code;
  const pending: Array<(d: any) => void> = [];
  const failing: Array<(e: any) => void> = [];   // the same reads, rejected by hand (the kernel unreachable)
  const fetch = () => new Promise<any>((res, rej) => { pending.push((d: any) => res({ json: async () => d })); failing.push(rej); });
  const fn = new Function("kernelUrl", "fetch", "adoptCommentDefaults",
    js + "\nreturn { loadModelChoices, CODEX_MODEL_CHOICES, get error() { return CODEX_MODELS_ERROR; }, set hook(f) { onModelChoicesLoaded = f; } };");
  return { api: fn((p: string) => p, fetch, () => {}), pending, failing };
}
const tick = () => new Promise((r) => setImmediate(r));

test("executed: the codex section's error reaches the picker and the completion hook fires", async () => {
  const { api, pending } = liftLoader();
  let fired = 0;
  api.hook = () => { fired++; };
  api.loadModelChoices();
  pending[0]({ rev: 5, models: [], efforts: [], codex: { models: [], efforts: [], error: "model_list failed: app-server not ready" } });
  await tick(); await tick();
  assert.equal(api.error, "model_list failed: app-server not ready");
  assert.deepEqual(api.CODEX_MODEL_CHOICES, []);
  assert.equal(fired, 1, "the open menu is told the read completed");
  api.loadModelChoices();
  pending[1]({ rev: 6, models: [], efforts: [], codex: { models: [{ value: "gpt-5-test", label: "GPT-5 Test" }], efforts: [], error: null } });
  await tick(); await tick();
  assert.equal(api.error, "", "a held list clears the reason");
  assert.deepEqual(api.CODEX_MODEL_CHOICES, [{ value: "gpt-5-test", label: "GPT-5 Test" }]);
  assert.equal(fired, 2);
});

// A read that FAILS (the kernel restarting or unreachable when the empty menu re-reads /models) used to
// be swallowed by the loader's catch, so the row kept saying it was asking, forever. Now a waiting menu
// hears the failure through the same hook and its row names it; with no menu waiting the catch stays
// quiet, as before.
test("executed: a failed re-read tells the waiting menu, and stays quiet with no menu waiting", async () => {
  const { api, pending, failing } = liftLoader();
  let fired = 0;
  api.loadModelChoices();                                  // the page-load read, no menu open
  failing[0](new Error("kernel unreachable"));
  await tick(); await tick();
  assert.equal(api.error, "", "no menu waiting: nothing recorded, nothing thrown");
  assert.equal(fired, 0);
  api.hook = () => { fired++; };
  api.loadModelChoices();                                  // the empty menu's own re-read
  failing[1](new Error("kernel unreachable"));
  await tick(); await tick();
  assert.equal(api.error, "could not read /models: kernel unreachable");
  assert.equal(fired, 1, "the waiting menu hears that the read failed");
  api.loadModelChoices();
  pending[2]({ rev: 7, models: [], efforts: [], codex: { models: [{ value: "gpt-5-test", label: "GPT-5 Test" }], efforts: [], error: null } });
  await tick(); await tick();
  assert.equal(api.error, "", "the next read that lands clears the failure");
  assert.deepEqual(api.CODEX_MODEL_CHOICES, [{ value: "gpt-5-test", label: "GPT-5 Test" }]);
  assert.equal(fired, 2);
});
