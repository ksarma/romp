// windowSender's truth table (window-sender.ts): which sender a window message is attributed to, from its source and
// origin, for a framed pane and for a top-level page.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { windowSender } from "./window-sender";

const ORIGIN = "http://127.0.0.1:1";
const parent = { name: "the shell" };
const framed = { parent, location: { origin: ORIGIN } };
const other = { name: "another window" };

test("a sourceless event with no origin is this document's own dispatch; a missing event is foreign", () => {
  assert.equal(windowSender({ source: null, origin: "" }, framed), "dispatch", "the shim's and federation's kernel frames");
  const bare: { source?: unknown; data: unknown } = { data: { type: "session" } };
  assert.equal(windowSender(bare, framed), "dispatch",
    "a handler called with a plain object (no source at all) is a direct call from this document's own script");
  assert.equal(windowSender(null, framed), "foreign");
  assert.equal(windowSender(undefined, framed), "foreign");
});

test("a sourceless event that carries an origin is judged by its origin, never counted as this document's dispatch", () => {
  assert.equal(windowSender({ source: null, origin: "null" }, framed), "foreign", "an opaque origin");
  assert.equal(windowSender({ source: null, origin: "https://example.invalid" }, framed), "foreign", "another origin");
  assert.equal(windowSender({ source: null, origin: ORIGIN }, framed), "peer", "this document's origin");
  const opaque = { parent, location: { origin: "null" } };
  assert.equal(windowSender({ source: null, origin: "null" }, opaque), "foreign", "an opaque origin, on a page whose own origin is opaque");
  assert.equal(windowSender({ source: null, origin: "" }, opaque), "dispatch", "no origin, on a page whose own origin is opaque");
});

// Every source against every origin, for a pane framed in the romp shell, each row's expected class written out. The
// window object alone decides only for this window (self) and its parent (embedder). Any other sender, a sourceless
// one included, is judged by the origin the browser stamps on its post: a window's object says nothing about where it
// is. A sourceless event is this document's own dispatch only when it names no origin (undefined, null or "").
test("the truth table: every source against every origin", () => {
  const ORIGINS: [string, unknown][] = [
    ["this origin", ORIGIN], ["a foreign origin", "https://example.invalid"], ['the string "null"', "null"],
    ["the empty string", ""], ["undefined", undefined], ["null", null],
  ];
  const TABLE: [string, unknown, string[]][] = [
    //                                                            this origin  foreign     "null"      ""          undefined   null
    ["this window",                           framed,           ["self",      "self",     "self",     "self",     "self",     "self"]],
    ["the parent (the romp shell)",           parent,           ["embedder",  "embedder", "embedder", "embedder", "embedder", "embedder"]],
    ["a peer window (a second chat column)",  other,            ["peer",      "foreign",  "foreign",  "foreign",  "foreign",  "foreign"]],
    ["a foreign window (a sandboxed frame)",  { name: "x" },    ["peer",      "foreign",  "foreign",  "foreign",  "foreign",  "foreign"]],
    ["a null source",                         null,             ["peer",      "foreign",  "foreign",  "dispatch", "dispatch", "dispatch"]],
    ["an undefined source",                   undefined,        ["peer",      "foreign",  "foreign",  "dispatch", "dispatch", "dispatch"]],
  ];
  const wrong: string[] = [];
  let rows = 0;
  for (const [sw, src, want] of TABLE) {
    assert.equal(want.length, ORIGINS.length, sw + ": one expected class per origin");
    ORIGINS.forEach(([ow, origin], i) => {
      rows++;
      const got = windowSender({ source: src, origin }, framed);
      if (got !== want[i]) wrong.push(sw + ", " + ow + ": " + got + ", expected " + want[i]);
    });
  }
  assert.equal(rows, 36);
  assert.deepEqual(wrong, [], "rows the helper classifies otherwise:\n  " + wrong.join("\n  "));
});

test("this window is self, whatever the origin says", () => {
  assert.equal(windowSender({ source: framed, origin: ORIGIN }, framed), "self");
  assert.equal(windowSender({ source: framed, origin: "null" }, framed), "self");
});

test("the parent is the embedder, whatever the origin says", () => {
  assert.equal(windowSender({ source: parent, origin: ORIGIN }, framed), "embedder", "the romp shell");
  assert.equal(windowSender({ source: parent, origin: "https://example.invalid" }, framed), "embedder",
    "a parent on another origin is still the parent");
});

test("the VS Code webview host is a peer: window.parent in VS Code's frame never refers to the host", () => {
  // VS Code's script in the webview's frame sets window.parent to the frame itself (older releases delete it), and the
  // host forwards the extension's messages from its own window on the webview's origin.
  const VSCODE = "vscode-webview://11111111-2222-3333-4444-555555555555";
  const host = { name: "the VS Code webview host" };
  const replaced: { parent?: unknown; location: { origin: string } } = { location: { origin: VSCODE } };
  replaced.parent = replaced;
  const deleted = { location: { origin: VSCODE } };
  for (const [what, frame] of [["parent replaced by the frame", replaced], ["parent deleted", deleted]] as const) {
    assert.equal(windowSender({ source: host, origin: VSCODE }, frame), "peer", "the host's post, " + what);
    assert.equal(windowSender({ source: frame, origin: VSCODE }, frame), "self", "a same-window post, " + what);
    assert.equal(windowSender({ source: { name: "a sandboxed frame" }, origin: "null" }, frame), "foreign",
      "a sandboxed frame, " + what);
    assert.equal(windowSender({ source: host, origin: "https://example.invalid" }, frame), "foreign",
      "a window on another origin, " + what);
  }
});

// VS Code gives each webview an origin of its own. The host is a peer because it posts on THIS webview's origin; a window
// on another webview's origin (another extension's, another panel's) is another origin like any other, so a rule that
// took every vscode-webview:// origin for a peer would fail here.
test("in a VS Code webview, a window on another webview's origin is foreign, with a source or without one", () => {
  const VSCODE = "vscode-webview://11111111-2222-3333-4444-555555555555";
  const OTHER_WEBVIEW = "vscode-webview://aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
  const host = { name: "the VS Code webview host" };
  const replaced: { parent?: unknown; location: { origin: string } } = { location: { origin: VSCODE } };
  replaced.parent = replaced;
  const deleted = { location: { origin: VSCODE } };
  for (const [what, frame] of [["parent replaced by the frame", replaced], ["parent deleted", deleted]] as const) {
    assert.equal(windowSender({ source: host, origin: VSCODE }, frame), "peer", "the host, on this webview's origin, " + what);
    assert.equal(windowSender({ source: { name: "another webview" }, origin: OTHER_WEBVIEW }, frame), "foreign",
      "a window on another webview's origin, " + what);
    assert.equal(windowSender({ source: host, origin: OTHER_WEBVIEW }, frame), "foreign",
      "the same window object, posting from another webview's origin, " + what);
    assert.equal(windowSender({ source: null, origin: OTHER_WEBVIEW }, frame), "foreign",
      "a sourceless post from another webview's origin, " + what);
    assert.equal(windowSender({ source: { name: "a frame" }, origin: VSCODE + "0" }, frame), "foreign",
      "an origin whose text begins with this webview's, " + what);
  }
});

test("another window on this document's origin is a peer; any other origin is foreign", () => {
  assert.equal(windowSender({ source: other, origin: ORIGIN }, framed), "peer", "a second chat column");
  assert.equal(windowSender({ source: other, origin: "null" }, framed), "foreign", "a sandboxed iframe's opaque origin");
  assert.equal(windowSender({ source: other, origin: "https://example.invalid" }, framed), "foreign");
  assert.equal(windowSender({ source: other, origin: "http://127.0.0.1:2" }, framed), "foreign", "same host, another port");
  assert.equal(windowSender({ source: other }, framed), "foreign", "no origin at all");
});

// Each origin here shares text with ORIGIN: one begins with it, one is a prefix of it, one differs from it only in the
// scheme. A comparison by prefix, or by host and port alone, would call one of them a peer; only an exact match may.
test("an origin whose text overlaps this document's origin is still another origin", () => {
  for (const src of [other, null]) {
    const who = src === null ? "no source, " : "another window, ";
    assert.equal(windowSender({ source: src, origin: ORIGIN + "0" }, framed), "foreign", who + "another port whose text begins with this origin");
    assert.equal(windowSender({ source: src, origin: "http://127.0.0.1" }, framed), "foreign", who + "this origin's text without its port");
    assert.equal(windowSender({ source: src, origin: "https://127.0.0.1:1" }, framed), "foreign", who + "the same host and port on another scheme");
  }
});

test("an opaque own origin never makes a peer: \"null\" matches nothing", () => {
  const opaque = { parent, location: { origin: "null" } };
  assert.equal(windowSender({ source: other, origin: "null" }, opaque), "foreign");
  assert.equal(windowSender({ source: parent, origin: "null" }, opaque), "embedder", "the parent is still the parent");
  assert.equal(windowSender({ source: other, origin: "null" }, { parent }), "foreign", "no location: no peer");
});

// With no location, this document's origin is unknown. A post that names no origin must not match that unknown: the
// "null" row above cannot show it, since "null" never equals a missing origin.
test("a window with no location has no peer, even for a post that names no origin", () => {
  const bare = { location: undefined };
  assert.equal(windowSender({ source: other }, bare), "foreign");
  assert.equal(windowSender({ source: other, origin: undefined }, bare), "foreign");
});

test("a top-level page (its parent is itself) has no embedder: a same-window post is self", () => {
  const top: { parent?: unknown; location: { origin: string } } = { location: { origin: ORIGIN } };
  top.parent = top;
  assert.equal(windowSender({ source: top, origin: ORIGIN }, top), "self");
  assert.equal(windowSender({ source: other, origin: ORIGIN }, top), "peer");
  assert.equal(windowSender({ source: other, origin: "null" }, top), "foreign");
  const orphan = { location: { origin: ORIGIN } };
  assert.equal(windowSender({ source: other, origin: "null" }, orphan), "foreign", "no parent at all");
});

// render.ts calls windowSender(e) with no window argument, and every other test here passes one, so this test is the
// only one that reads the default. It sets the global window to a framed pane and restores it after. The pane carries
// the edges a real framed window has, each a different window: top is the shell (its parent, the top-level page), and
// self is the pane itself. So a default that read another window than this one (window.top, the shell's page) would judge
// the shell's post as this window's own and this window's own post as some other window's; and in a VS Code webview,
// whose top is on another origin, reading its location would throw on every message.
test("with no window argument, windowSender reads the global window", () => {
  const g = globalThis as { window?: unknown };
  const had = "window" in g, prev = g.window;
  const pane: { parent: unknown; top: unknown; self?: unknown; location: { origin: string } } = { parent, top: parent, location: { origin: ORIGIN } };
  pane.self = pane;
  assert.ok(pane.top !== pane && pane.self === pane && pane.top !== pane.self, "top and self are different windows");
  g.window = pane;
  try {
    assert.equal(windowSender({ source: pane, origin: ORIGIN }), "self", "a same-window post");
    assert.equal(windowSender({ source: parent, origin: "https://example.invalid" }), "embedder", "the parent, the top window");
    assert.equal(windowSender({ source: other, origin: ORIGIN }), "peer", "a second chat column");
    assert.equal(windowSender({ source: other, origin: "null" }), "foreign", "a sandboxed frame");
    assert.equal(windowSender({ source: null, origin: "" }), "dispatch", "the kernel's frames");
  } finally {
    if (had) g.window = prev; else delete g.window;
  }
});

// The window object decides only for this window (self) and its parent (embedder). A window related to this one in any
// other way (a frame inside it, a window it opened, the window that opened it, its parent's parent) is judged by its
// origin like any other window, so a sandboxed or foreign one is foreign: a page on another origin that opens the chat
// as a top-level page becomes its opener, and a frame inside the chat may be sandboxed.
test("a window related to this one other than as its parent is judged by its origin", () => {
  const grand = { name: "the shell's parent" };
  const opener = { name: "the window that opened this one" };
  const w = { parent: { name: "the shell", parent: grand }, opener, location: { origin: ORIGIN } };
  const RELATED: [string, unknown][] = [
    ["a frame inside this window", { name: "a child frame", parent: w }],
    ["a window this window opened", { name: "a popup", opener: w }],
    ["the window that opened this one", opener],
    ["the parent's parent", grand],
  ];
  for (const [who, src] of RELATED) {
    assert.equal(windowSender({ source: src, origin: "null" }, w), "foreign", who + ", opaque origin");
    assert.equal(windowSender({ source: src, origin: "https://example.invalid" }, w), "foreign", who + ", another origin");
    assert.equal(windowSender({ source: src, origin: ORIGIN }, w), "peer", who + ", this origin");
  }
});
