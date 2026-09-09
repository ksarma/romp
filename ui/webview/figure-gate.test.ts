// The figure gate's pure parts (figure-gate.ts; decision 8 of plans/markdown-viewer.md), executed under node: the srcset
// parse and its serialization, which host a source fetches from against a page's base (the kernel's own route and the
// data: and blob: schemes are nobody's host; a protocol-relative URL is), the allowed set from the setting, the loaded
// set and a document's own host, and the setting's normaliser in settings.ts. The DOM half (the placeholder, the click,
// the restore, the regate on a settings change) runs over the real Files bundle in file-view-figures-gate-browser.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";

// localStorage before the settings module is read (settings.ts reads it at call time)
const store: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => (k in store ? store[k] : null),
  setItem: (k: string, v: string) => { store[k] = v; },
  removeItem: (k: string) => { delete store[k]; },
};
import { parseSrcset, serializeSrcset, remoteHost, allowedFigureHosts, forgetLoadedHosts, loadGatedHost, FIGURE_SEL, GATE_ACT, GATE_CLASS } from "./figure-gate";
import { FIGURE_HOSTS_DEFAULT, figureHosts } from "./settings";

test("parseSrcset: HTML's own parse, a URL to whitespace, a glued comma ending a candidate, descriptors to the next top-level comma, a comma inside a URL kept; serializeSrcset the inverse", () => {
  assert.deepEqual(parseSrcset("a.png 1x, b.png 2x"), [{ url: "a.png", descriptor: "1x" }, { url: "b.png", descriptor: "2x" }]);
  assert.deepEqual(parseSrcset("  a.png   100w ,b.png 200w  "), [{ url: "a.png", descriptor: "100w" }, { url: "b.png", descriptor: "200w" }]);
  assert.deepEqual(parseSrcset("a.png, b.png"), [{ url: "a.png", descriptor: "" }, { url: "b.png", descriptor: "" }], "no descriptor: the comma is glued to the URL");
  assert.deepEqual(parseSrcset("a,b.png 1x, c.png 2x"), [{ url: "a,b.png", descriptor: "1x" }, { url: "c.png", descriptor: "2x" }], "a comma inside a URL survives");
  assert.deepEqual(parseSrcset("https://remote.test/x.png 2x"), [{ url: "https://remote.test/x.png", descriptor: "2x" }]);
  assert.deepEqual(parseSrcset(""), []);
  assert.deepEqual(parseSrcset(" , , "), []);
  assert.equal(serializeSrcset(parseSrcset("a.png 1x, b.png 2x")), "a.png 1x, b.png 2x");
  assert.equal(serializeSrcset(parseSrcset("a.png, b.png")), "a.png, b.png");
});

// The parse where a JS-flavoured reading parts from HTML's (review of Slice 4, round 1: two gate bypasses over the real Files
// bundle). HTML's srcset parse ends a URL at ASCII whitespace ONLY (tab, LF, FF, CR, space); a JS `\s` also stops at U+00A0,
// U+000B, U+2003, U+FEFF and the rest of Unicode space, so `https://github.com<nbsp>@evil.test/x.png` read as the allowed host
// github.com to the gate while the browser fetched evil.test (github.com became the userinfo). And HTML's descriptor tokenizer
// has ONE in-parens state that ends at the first `)`: a depth counter let `((,) 1x, https://evil.test/b.png` swallow the comma
// that starts the second candidate, so the gate saw one allowed candidate and the browser fetched the second. The non-ASCII
// code points are built with escapes so this source stays ASCII.
test("parseSrcset agrees with HTML's parse where a JS reading would not: a URL runs through non-ASCII whitespace (nbsp, VT, em space, BOM) and stops at ASCII whitespace; a parenthesised descriptor ends at the first closing paren, never nested; the descriptor's edges lose ASCII whitespace only", () => {
  for (const [name, cp] of [["nbsp", "\u00a0"], ["VT", "\u000b"], ["em space", "\u2003"], ["BOM", "\ufeff"]] as Array<[string, string]>) {
    const url = "https://github.com" + cp + "@evil.test/x.png";
    assert.deepEqual(parseSrcset(url), [{ url, descriptor: "" }], name + ": one URL, whole, as the browser reads it");
    assert.equal(remoteHost(url, "http://romp.test/files"), "evil.test", name + ": the host the browser would fetch from");
    assert.deepEqual(parseSrcset("https://github.com/a.png 1x, " + url + " 2x"), [{ url: "https://github.com/a.png", descriptor: "1x" }, { url, descriptor: "2x" }], name + ": beside an allowed candidate");
  }
  assert.deepEqual(parseSrcset("https://github.com\u000c@evil.test/x.png"), [{ url: "https://github.com", descriptor: "@evil.test/x.png" }], "form feed IS ASCII whitespace: the URL ends there for both parsers");
  assert.deepEqual(parseSrcset("a.png\t1x,\nb.png\r2x\f"), [{ url: "a.png", descriptor: "1x" }, { url: "b.png", descriptor: "2x" }], "the four other ASCII whitespace code points separate as a space does");
  assert.deepEqual(parseSrcset("https://github.com/a.png ((,) 1x, https://evil.test/b.png"), [{ url: "https://github.com/a.png", descriptor: "((,) 1x" }, { url: "https://evil.test/b.png", descriptor: "" }], "the first `)` leaves the parens: the comma after 1x starts the second candidate");
  assert.deepEqual(parseSrcset("a.png ((,) 1x, https://hr.test/b.png"), [{ url: "a.png", descriptor: "((,) 1x" }, { url: "https://hr.test/b.png", descriptor: "" }], "the rewrite path's shape: a relative candidate first");
  assert.deepEqual(parseSrcset("a.png (,) 1x, b.png"), [{ url: "a.png", descriptor: "(,) 1x" }, { url: "b.png", descriptor: "" }], "a comma inside one pair of parens still belongs to the descriptor");
  assert.deepEqual(parseSrcset("a.png (b) (c,d) e, f.png"), [{ url: "a.png", descriptor: "(b) (c,d) e" }, { url: "f.png", descriptor: "" }], "two pairs in turn, each closed by its own `)`");
  assert.deepEqual(parseSrcset("a.png (unclosed, b.png"), [{ url: "a.png", descriptor: "(unclosed, b.png" }], "an unclosed paren runs to the end, as HTML's in-parens state does");
  assert.deepEqual(parseSrcset("a.png 1x\u00a0, b.png"), [{ url: "a.png", descriptor: "1x\u00a0" }, { url: "b.png", descriptor: "" }], "a non-ASCII space at a descriptor's edge stays: the browser reads that descriptor as invalid, and the re-serialised attribute must say the same");
  // the serialisation carries each candidate through unchanged, so the browser fetches exactly the URLs the gate judged
  const nb = "https://github.com\u00a0@evil.test/x.png";
  assert.equal(serializeSrcset(parseSrcset("https://github.com/a.png ((,) 1x, " + nb)), "https://github.com/a.png ((,) 1x, " + nb);
  assert.equal(serializeSrcset(parseSrcset("a.png 1x,b.png 2x")), "a.png 1x, b.png 2x", "the canonical form: one comma and one space between candidates");
});

test("remoteHost: the page's own origin (the kernel's /file route, a relative src) and data:/blob: are nobody's host; http(s) elsewhere is its host, lower-cased; a protocol-relative URL is remote; the kernel's own base is never remote", () => {
  const base = "http://romp.test/files";
  assert.equal(remoteHost("/file?path=%2Fa.png&sid=1", base), null);
  assert.equal(remoteHost("fig.png", base), null, "a relative src resolves against the page");
  assert.equal(remoteHost("http://romp.test/x.png", base), null);
  assert.equal(remoteHost("data:image/png;base64,iVBORw0KGgo=", base), null);
  assert.equal(remoteHost("blob:http://romp.test/uuid", base), null);
  assert.equal(remoteHost("https://Remote.TEST/img.png", base), "remote.test");
  assert.equal(remoteHost("//cdn.example.test/x.png", base), "cdn.example.test", "protocol-relative is a web address");
  assert.equal(remoteHost("http://localhost:8000/x.png", base), "localhost", "another port is another origin; the host name is what the list matches");
  assert.equal(remoteHost("https://github.com/u/r/raw/main/gh.png", base), "github.com");
  assert.equal(remoteHost("", base), null);
  assert.equal(remoteHost("http://[bad", base), null, "an unparseable URL is left alone");
  assert.equal(remoteHost("mailto:x@example.test", base), null, "no other scheme fetches a figure");
  // a webview that reaches the kernel by an absolute base: the kernel's own origin is not gated
  (globalThis as any).window = { __rompKernelBase: "http://127.0.0.1:7777" };
  assert.equal(remoteHost("http://127.0.0.1:7777/file?path=%2Fa.png", "vscode-webview://abc/index.html"), null, "the kernel's origin");
  assert.equal(remoteHost("http://kernel-host.test:7777/file?path=%2Fa.png", "vscode-webview://abc/index.html"), "kernel-host.test");
  (globalThis as any).window.__rompKernelBase = "http://kernel-host.test:7777";
  assert.equal(remoteHost("http://kernel-host.test:7777/file?path=%2Fa.png", "vscode-webview://abc/index.html"), null, "…whatever host it is on");
  delete (globalThis as any).window;
});

test("the allowed set: the setting's hosts (the default list before any change), the hosts loaded in this document, and a document's own host; a store from before the setting reads as the default", () => {
  delete store["romp:settings"];
  forgetLoadedHosts();
  const def = allowedFigureHosts();
  for (const h of FIGURE_HOSTS_DEFAULT) assert.ok(def.has(h), h);
  assert.ok(!def.has("remote.test"));
  store["romp:settings"] = JSON.stringify({ compact: true });
  assert.deepEqual([...allowedFigureHosts()].sort(), [...FIGURE_HOSTS_DEFAULT].sort(), "a store written before the setting existed: the defaults");
  store["romp:settings"] = JSON.stringify({ figureHosts: ["Remote.TEST", " other.test "] });
  const set = allowedFigureHosts(["Doc.Host.test"]);
  assert.ok(set.has("remote.test") && set.has("other.test") && set.has("doc.host.test"), "the setting lower-cased and trimmed, the document's host lower-cased");
  assert.ok(!set.has("github.com"), "the setting is the whole list: a host removed from it is gated");
  store["romp:settings"] = JSON.stringify({ figureHosts: "a.test\nb.test, c.test d.test" });
  assert.deepEqual([...allowedFigureHosts()].sort(), ["a.test", "b.test", "c.test", "d.test"], "one string, as the gear's textarea holds it");
  store["romp:settings"] = JSON.stringify({ figureHosts: 42 });
  assert.deepEqual([...allowedFigureHosts()].sort(), [...FIGURE_HOSTS_DEFAULT].sort(), "a foreign value reads as the default, never as no host at all");
  // the loaded set: per document, kept until forgotten; a click's host joins it (the DOM regate runs over a document with no placeholders here)
  const doc = { querySelectorAll: () => [] as Element[] } as unknown as ParentNode;
  loadGatedHost("Loaded.TEST", doc);
  assert.ok(allowedFigureHosts().has("loaded.test"));
  loadGatedHost("", doc);
  assert.ok(!allowedFigureHosts().has(""), "an empty host is nothing");
  forgetLoadedHosts();
  assert.ok(!allowedFigureHosts().has("loaded.test"));
  delete store["romp:settings"];
});

test("settings.ts: figureHosts normalises to a fresh list of trimmed lower-case names, the default list for anything else; the default names github.com, its image hosts, localhost and 127.0.0.1 and no wildcard", () => {
  assert.deepEqual(figureHosts(["A.test", " b.test", "", 7 as unknown as string]), ["a.test", "b.test"]);
  assert.deepEqual(figureHosts("x.test,y.test\n z.test"), ["x.test", "y.test", "z.test"]);
  assert.deepEqual(figureHosts(undefined), [...FIGURE_HOSTS_DEFAULT]);
  assert.deepEqual(figureHosts({}), [...FIGURE_HOSTS_DEFAULT]);
  assert.notEqual(figureHosts(undefined), FIGURE_HOSTS_DEFAULT, "a copy, never the shared array");
  assert.deepEqual(figureHosts([]), [], "an emptied list is a choice: only the kernel's own origin loads");
  assert.deepEqual([...FIGURE_HOSTS_DEFAULT], ["github.com", "raw.githubusercontent.com", "user-images.githubusercontent.com", "camo.githubusercontent.com", "avatars.githubusercontent.com", "objects.githubusercontent.com", "private-user-images.githubusercontent.com", "github.githubassets.com", "localhost", "127.0.0.1"]);
  for (const h of FIGURE_HOSTS_DEFAULT) assert.match(h, /^[a-z0-9.-]+$/, "an exact host name, no wildcard, no scheme: " + h);
});

test("the names the viewer and the anchor map key on", () => {
  assert.equal(FIGURE_SEL, "img, source, video, audio, track, image, feImage");
  assert.equal(GATE_ACT, "fv-load");
  assert.equal(GATE_CLASS, "fv-gate");
});
