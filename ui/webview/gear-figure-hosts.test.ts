// The gear's "Pictures from the web in files" row (decision 8 of plans/markdown-viewer.md; the ruling made the allowed
// hosts a gear setting): a textarea holding the figureHosts list one host per line, saved through the same load/save
// every other row uses, painted on open. gear.js cannot import settings.ts, so it carries a copy of the default list and
// of the normaliser; both are lifted out by anchor and run here against the TS module's (gear-file-comments.test.ts's
// idiom), so the two cannot drift apart without this failing. The wiring that needs the whole modal is pinned at source.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { FIGURE_HOSTS_DEFAULT, figureHosts } from "./settings";

const GEAR = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "gear.js"), "utf8");

function slice(src: string, start: string, stop: string, from = 0): string {
  const a = src.indexOf(start, from);
  assert.ok(a >= 0, "anchor not found, gear.js moved: " + start.slice(0, 60));
  const b = src.indexOf(stop, a);
  assert.ok(b > a, "end anchor not found, gear.js moved: " + stop.slice(0, 60));
  return src.slice(a, b + stop.length);
}
type Lifted = { FIGURE_HOSTS_DEFAULT: string[]; figureHostList: (v: unknown) => string[] };
function lift(): Lifted {
  const list = slice(GEAR, "  var FIGURE_HOSTS_DEFAULT = [", "];\n");
  const fn = slice(GEAR, "  function figureHostList(v) {", "\n  }\n");
  return new Function(list + fn + "return { FIGURE_HOSTS_DEFAULT: FIGURE_HOSTS_DEFAULT, figureHostList: figureHostList };")() as Lifted;
}

test("executed: gear.js's default list is settings.ts's, and its normaliser gives the same answer as settings.ts figureHosts for every shape a store or the textarea can hold", () => {
  const g = lift();
  assert.deepEqual(g.FIGURE_HOSTS_DEFAULT, [...FIGURE_HOSTS_DEFAULT]);
  for (const v of [undefined, null, 42, {}, [], ["A.test", " b.test ", "", 7], "x.test\ny.test, z.test  w.test", "", "  ", ["github.com"]]) {
    assert.deepEqual(g.figureHostList(v), figureHosts(v), JSON.stringify(v));
  }
  assert.notEqual(g.figureHostList(undefined), g.FIGURE_HOSTS_DEFAULT, "a copy of the default, never the array itself (a later push would edit the default)");
});

test("source: the row is a textarea saved through load/save on change and painted on open; load() seeds the default in both of its literals", () => {
  const markup = slice(GEAR, "<b>Pictures from the web in files</b>", "</span></div>' +");
  assert.match(markup, /<textarea id=rs-figurehosts rows=4 spellcheck=false/, "a textarea, one host per line");
  assert.doesNotMatch(markup, /—/, "no em dashes in UI copy");
  assert.doesNotMatch(markup, /fleet/i);
  assert.match(markup, /One host per line\./);
  assert.match(markup, /shows a placeholder naming the host, and loads on a click/);
  assert.match(GEAR, /fh = document\.getElementById\('rs-figurehosts'\),/, "looked up with the other controls");
  assert.match(GEAR, /if \(fh\) fh\.addEventListener\('change', function \(\) \{ var s = load\(\); s\.figureHosts = figureHostList\(fh\.value\); save\(s\); \}\);/, "the change listener: the same load/save every row uses");
  assert.match(GEAR, /if \(fh\) fh\.value = figureHostList\(s\.figureHosts\)\.join\('\\n'\);/, "painted on open from the store, through the normaliser");
  assert.equal(GEAR.split("figureHosts: FIGURE_HOSTS_DEFAULT.slice()").length, 3, "load()'s two default literals both carry the list");
  assert.equal(GEAR.split("var FIGURE_HOSTS_DEFAULT = [").length, 2, "one copy of the list in gear.js");
});

test("source: settings.ts declares the field, normalises it on load, and documents the default's scope", () => {
  const S = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "settings.ts"), "utf8");
  assert.match(S, /^\s*figureHosts: string\[\];/m);
  assert.match(S, /s\.figureHosts = figureHosts\(s\.figureHosts\);/, "normalised on every load");
  assert.match(S, /figureHosts: \[\.\.\.FIGURE_HOSTS_DEFAULT\]/, "DEFAULT_SETTINGS carries a copy");
  assert.match(S, /the kernel's own origin is always allowed and needs no entry/);
});
