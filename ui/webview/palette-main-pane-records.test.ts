// The palette's toggle commands for the panes defined at the kernel (palette-main.ts registerPane and recordPanes;
// plans/panes-as-data.md). The shell builds those panes in the browser from its GET /panes read, one source for the pane
// records, and the read can settle before or after the palette's bundle boots. So the palette registers a pane's command from the
// read's state object when the read is in at boot (window.__rompPaneRecords) and from the builder's romp-pane-records event when
// it lands later; registerCommand replaces by id, so the two paths leave one command per pane. The shipped generic panes keep
// their boot read of the body attribute, and list first. palette-main.ts boots the shell's whole palette on import, so its
// registry block is LIFTED (esbuild's ts loader, the browse-route idiom) and run with the real command registry (commands.ts)
// over a stand-in window and body.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { registerCommand, unregisterCommand, commandList } from "./commands";

const requireCjs = createRequire(__filename);
const MAIN = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "palette-main.ts"), "utf8");
const ts = (code: string): string => requireCjs("esbuild").transformSync(code, { loader: "ts" }).code;
// the shell's body attribute: the shipped Artifacts record's row alone (tests/test_pane_registry.py ARTIFACTS_ROW)
const ARTIFACTS_ROW = { id: "artifacts", title: "Artifacts", protocol: "romp", experimental: true, on: false, builtin: true };
// rows as the shell's builder keeps them in the read's state (rows)
const NOTES = { id: "notes", title: "Notebook", on: true, experimental: false, protocol: "romp", src: "/pane/notes/" };
const LAB = { id: "lab", title: "Lab", on: false, experimental: true, protocol: "none", src: "/feed" };

type Records = { state: string; rows: unknown; error: string };
type Settings = { panes: Record<string, boolean> };
/** The registry block lifted from palette-main.ts and run once, as the bundle's boot runs it, with `rr` as the read's state. */
function boot(rr: Records, settings: Settings = { panes: {} }) {
  for (const c of commandList()) if (c.id.startsWith("pane.")) unregisterCommand(c.id);   // the registry is this file's process-wide one
  const a = MAIN.indexOf("  const registry: Array<{ id: string; title: string; experimental: boolean }> = (() => {");
  const b = MAIN.indexOf("  const optional = new Set<string>(OPTIONAL_PANES);", a);
  assert.ok(a > 0 && b > a, "palette-main.ts: the registry block's anchors not found; re-anchor");
  const win: any = new EventTarget();
  win.__rompPaneRecords = rr;
  const toggled: string[] = [];
  win.__rompPaneToggle = (id: string) => { toggled.push(id); };
  const doc = { body: { getAttribute: (k: string) => (k === "data-panes" ? JSON.stringify([ARTIFACTS_ROW]) : null) } };
  new Function("document", "window", "w", "registerCommand", "loadSettings", ts(MAIN.slice(a, b)))(doc, win, win, registerCommand, () => settings);
  return {
    toggled,
    panes: () => commandList().filter((c) => c.id.startsWith("pane.")),
    land: (r: Records) => win.dispatchEvent(new CustomEvent("romp-pane-records", { detail: { state: r.state, rows: r.rows || [], frames: [], error: r.error } })),
  };
}

test("a read already in when the palette boots: each pane it lists gets a toggle command, after the shipped Artifacts pane's, under its title and its gear setting", () => {
  const settings: Settings = { panes: { notes: false } };
  const p = boot({ state: "ok", rows: [NOTES, LAB, { id: 7, title: "x" }, null], error: "" }, settings);
  assert.deepEqual(p.panes().map((c) => [c.id, c.title]), [["pane.artifacts", "Show or hide the Artifacts pane"], ["pane.notes", "Show or hide the Notebook pane"], ["pane.lab", "Show or hide the Lab pane"]],
    "the attribute's pane, then the read's in its order; a row without a string id is skipped");
  const cmd = (id: string) => p.panes().find((c) => c.id === id)!;
  cmd("pane.notes").run();
  assert.deepEqual(p.toggled, ["notes"], "the command toggles the pane by its id, through the shell's controller");
  assert.equal(cmd("pane.notes").when!(), false, "a pane hidden in the gear is not listed");
  assert.equal(cmd("pane.lab").when!(), false, "an experimental pane is not listed until the gear asks for it");
  settings.panes.lab = true; settings.panes.notes = true;
  assert.equal(cmd("pane.lab").when!(), true, "the setting is read at every open");
  assert.equal(cmd("pane.notes").when!(), true);
});

test("a read that lands after the palette booted: the builder's romp-pane-records registers its panes then, and a later event leaves one command per pane", () => {
  const p = boot({ state: "loading", rows: null, error: "" });
  assert.deepEqual(p.panes().map((c) => c.id), ["pane.artifacts"], "while the read is loading: the shipped pane alone");
  p.land({ state: "failed", rows: null, error: "/panes answered HTTP 500" });
  p.land({ state: "failed", rows: [LAB], error: "no answer within 30 s" });
  assert.deepEqual(p.panes().map((c) => c.id), ["pane.artifacts"], "a failed read adds nothing, whatever rows its event carries: only a read that is in registers");
  p.land({ state: "ok", rows: [NOTES], error: "" });
  assert.deepEqual(p.panes().map((c) => c.id), ["pane.artifacts", "pane.notes"], "the read's pane is in once its event arrives");
  p.land({ state: "ok", rows: [NOTES, LAB], error: "" });
  assert.deepEqual(p.panes().map((c) => c.id), ["pane.artifacts", "pane.notes", "pane.lab"], "a later event adds the new pane and repeats none (registerCommand replaces by id)");
  const seen = boot({ state: "ok", rows: [NOTES], error: "" });
  seen.land({ state: "ok", rows: [NOTES], error: "" });
  assert.deepEqual(seen.panes().map((c) => c.id), ["pane.artifacts", "pane.notes"], "a read seen at boot and its event after it: one command for the pane");
});
