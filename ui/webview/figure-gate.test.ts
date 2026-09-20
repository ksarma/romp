// The figure gate's pure parts (figure-gate.ts; decision 8 of plans/markdown-viewer.md), executed under node: the srcset
// parse and its serialization, which host a source fetches from against a page's base (the kernel's own route and the
// data: and blob: schemes are nobody's host; a protocol-relative URL is), the allowed set from the setting, the loaded
// set and a document's own host, and the setting's normaliser in settings.ts; and the print's one-placeholder restore
// (loadGatedFigure) over a stand-in, for what it leaves alone: the loaded set and every other placeholder. The DOM half (the
// placeholder, the click, the restore, the regate on a settings change) runs over the real Files bundle in
// file-view-figures-gate-browser.test.ts, and the print's restore over the real viewer in file-print-egress-browser.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { hideEdges } from "../test-dom-shim";

// localStorage before the settings module is read (settings.ts reads it at call time)
const store: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => (k in store ? store[k] : null),
  setItem: (k: string, v: string) => { store[k] = v; },
  removeItem: (k: string) => { delete store[k]; },
};
import { parseSrcset, serializeSrcset, remoteHost, allowedFigureHosts, forgetLoadedHosts, loadGatedHost, loadGatedFigure, FIGURE_SEL, GATE_ACT, GATE_CLASS } from "./figure-gate";
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

/** An element stand-in for the restore: attributes by name, element children, a parent, and the two DOM writes restore makes
 *  (replaceWith on the placeholder, the attribute moves on the figure and its descendants). hideEdges hides the tree edges. */
class Fake {
  attrs = new Map<string, string>();
  kids: Fake[] = [];
  parent: Fake | null = null;
  replacedBy: Fake | null = null;
  constructor(public localName: string, attrs: Record<string, string> = {}) { for (const [k, v] of Object.entries(attrs)) this.attrs.set(k, v); hideEdges(this); }
  get attributes(): Array<{ name: string; value: string }> { return Array.from(this.attrs, ([name, value]) => ({ name, value })); }
  get firstElementChild(): Fake | null { return this.kids[0] || null; }
  getAttribute(k: string): string | null { return this.attrs.has(k) ? this.attrs.get(k)! : null; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  append(...ks: Fake[]): Fake { for (const k of ks) { k.parent = this; this.kids.push(k); } return this; }
  querySelectorAll(sel: string): Fake[] { assert.equal(sel, "*", "the restore walks every descendant"); const out: Fake[] = []; const walk = (n: Fake) => { for (const k of n.kids) { out.push(k); walk(k); } }; walk(this); return out; }
  replaceWith(n: Fake): void { this.replacedBy = n; if (this.parent) { const i = this.parent.kids.indexOf(this); this.parent.kids[i] = n; n.parent = this.parent; this.parent = null; } }
  remove(): void { this.replacedBy = null; if (this.parent) { this.parent.kids.splice(this.parent.kids.indexOf(this), 1); this.parent = null; } }
  /** The attributes as one sorted line, for a plain comparison. */
  line(): string { return Array.from(this.attrs, ([k, v]) => k + "=" + v).sort().join(" "); }
}
/** A stand-in handed to the gate as the Element it reads. */
const asEl = (f: Fake): Element => f as unknown as Element;
/** A placeholder stand-in around `media`, naming `host`, as gate() builds one: the action, the hosts, and a label after the media. */
const placeholder = (host: string, media: Fake): Fake => new Fake("span", { class: GATE_CLASS, "data-act": GATE_ACT, "data-fv-hosts": host, "data-fv-host": host }).append(media, new Fake("span", { "data-fv-label": "" }));

test("loadGatedFigure restores ONE placeholder and grants nothing for the page: the figure's moved attributes come back under their names (src, srcset, poster, an svg image's href, data-fv-src) on it and on its descendants, the figure takes the placeholder's place, the host does NOT join the loaded set, and a second placeholder naming the same host stands untouched; an element that is no placeholder is left alone and answers false", () => {
  forgetLoadedHosts();
  const body = new Fake("div");
  const img = new Fake("img", { alt: "", "data-fv-gated-src": "https://remote.test/a.png", "data-fv-gated-srcset": "https://remote.test/a2.png 2x", "data-fv-gated-fv-src": "1", loading: "lazy" });
  const open = placeholder("remote.test", img);
  const source = new Fake("source", { "data-fv-gated-srcset": "https://remote.test/c.webm", type: "video/webm" });
  const video = new Fake("video", { controls: "", "data-fv-gated-poster": "https://remote.test/p.png" }).append(source);
  const folded = placeholder("remote.test", video);
  body.append(open, new Fake("details").append(folded));
  assert.equal(loadGatedFigure(asEl(open)), true, "a placeholder: restored");
  assert.equal(img.line(), "alt= data-fv-src=1 loading=lazy src=https://remote.test/a.png srcset=https://remote.test/a2.png 2x", "every moved attribute back under its name, the others as they were, no data-fv-gated- left");
  assert.equal(open.replacedBy, img, "the figure took the placeholder's place");
  assert.equal(body.kids[0], img, "…in the body");
  assert.equal(allowedFigureHosts().has("remote.test"), false, "FAILS BEFORE the per-placeholder restore: the host joined the loaded set for the page; here nothing is granted");
  assert.equal(folded.replacedBy, null, "the second placeholder naming the same host stands");
  assert.equal(video.line(), "controls= data-fv-gated-poster=https://remote.test/p.png", "…its figure's attributes still moved aside");
  assert.equal(source.getAttribute("data-fv-gated-srcset"), "https://remote.test/c.webm", "…and its descendant's");
  // the folded one restored on its own turn: the descendant's attribute comes back too
  assert.equal(loadGatedFigure(asEl(folded)), true);
  assert.equal(video.line(), "controls= poster=https://remote.test/p.png"); assert.equal(source.line(), "srcset=https://remote.test/c.webm type=video/webm");
  assert.equal(allowedFigureHosts().has("remote.test"), false, "still nothing granted");
  // not a placeholder: an author's span wearing the class, a bare img
  const authored = new Fake("span", { class: GATE_CLASS }).append(new Fake("img", { "data-fv-gated-src": "https://x.test/p.png" }));
  assert.equal(loadGatedFigure(asEl(authored)), false, "the class is not the mark: an author can type it");
  assert.equal(authored.replacedBy, null); assert.equal(authored.kids[0].getAttribute("data-fv-gated-src"), "https://x.test/p.png", "nothing touched");
  assert.equal(loadGatedFigure(asEl(new Fake("img", { src: "x" }))), false);
  // the click's road, for contrast: the host joins the set
  loadGatedHost("remote.test", { querySelectorAll: () => [] as Element[] } as unknown as ParentNode);
  assert.equal(allowedFigureHosts().has("remote.test"), true, "a click grants the host for the page");
  forgetLoadedHosts();
});

test("loadGatedFigure restores the FIGURE, painting or not: an svg <image> under <defs> beside one that paints gets its href back too, and a hidden <img> inside a <video> its src beside the poster, so a remote URL inside a non-painting element of a figure that paints is fetched (the round-4 review's HIGH 2, 2026-09-20: a consent-text correction, the grant being figure-level by design); the sentence that says so stands in figure-gate.ts, in file-print.ts's header and in printable's docstring, and the sentence it replaced is gone", () => {
  forgetLoadedHosts();
  const shown = new Fake("image", { "data-fv-gated-href": "https://remote.test/shown.svg", width: "8", height: "8" });
  const unshown = new Fake("image", { "data-fv-gated-href": "https://remote.test/defs.svg" });
  const svg = new Fake("svg").append(shown, new Fake("defs").append(unshown));
  const one = placeholder("remote.test", svg);
  const fallback = new Fake("img", { hidden: "", "data-fv-gated-src": "https://remote.test/fallback.svg" });
  const video = new Fake("video", { "data-fv-gated-poster": "https://remote.test/poster.svg" }).append(fallback);
  const two = placeholder("remote.test", video);
  new Fake("div").append(one, two);
  assert.equal(loadGatedFigure(asEl(one)), true);
  assert.equal(shown.line(), "height=8 href=https://remote.test/shown.svg width=8", "the painting image's href is back");
  assert.equal(unshown.line(), "href=https://remote.test/defs.svg", "the image under <defs>, which paints nothing, has its href back as well: the browser is free to fetch it for something never on the paper");
  assert.equal(loadGatedFigure(asEl(two)), true);
  assert.equal(video.line(), "poster=https://remote.test/poster.svg", "the poster is back");
  assert.equal(fallback.line(), "hidden= src=https://remote.test/fallback.svg", "the hidden fallback img's src is back too, hidden or not");
  assert.equal(allowedFigureHosts().has("remote.test"), false, "nothing granted for the page on either restore");
  // the sentence the person and the owner read, in the code and pinned here: the grant covers every URL the figure names
  const read = (f: string): string => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
  const gate = read("figure-gate.ts"), flow = read("file-print.ts");
  assert.ok(gate.includes("The restore is the FIGURE's, not a painting element's:") && gate.includes("is fetched for something that is never on the paper"), "loadGatedFigure's docstring states the figure-level rule");
  assert.ok(flow.includes("The restore is the WHOLE figure's: every") && flow.includes("URL the figure names is fetched, a remote URL inside a non-painting element of a figure that paints among them"), "file-print.ts's header states it where \"with them\" is described");
  assert.ok(flow.includes("so every URL the figure names is fetched, a remote URL inside a") && flow.includes("non-painting element of a painting figure among them (the round-4 review"), "printable's docstring states it where the privacy rule is stated");
  assert.ok(!flow.includes("a print fetches from one only for a picture that is on the paper"), "the sentence that promised less than the code performs is gone");
  forgetLoadedHosts();
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
