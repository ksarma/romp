// The file preview popover's pure half, executed (T351 stage 1): the link's path and anchor, the kernel's verdict on
// what a link may preview, the routes' URLs, the one content shape per kind, and the hover's timing run on fake timers.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { PREVIEW_DWELL_MS, PREVIEW_GRACE_MS, HoverIntent, parsePreviewLink, previewKindOf, sliceUrl, fileUrl, previewRoute, langOf, baseName,
         contentFor, textOnlyContent, remoteLoad, stripRemoteLoads } from "./file-preview";
import { hideEdges } from "../test-dom-shim";   // the fake-DOM rule (ui/test-dom-shim.test.ts): a node enumerates its primitives alone, so a failing dump never walks the tree

test("parsePreviewLink: path#slug splits on a slug, a # that is not a slug stays in the path", () => {
  assert.deepEqual(parsePreviewLink("/home/u/docs/glossary.md#fold"), { path: "/home/u/docs/glossary.md", anchor: "fold" });
  assert.deepEqual(parsePreviewLink("docs/guide.md#install-2"), { path: "docs/guide.md", anchor: "install-2" });
  assert.deepEqual(parsePreviewLink("docs/guide.md"), { path: "docs/guide.md", anchor: "" });
  assert.deepEqual(parsePreviewLink("notes/#tag file.md"), { path: "notes/#tag file.md", anchor: "" }, "a space after the # is no slug");
  assert.deepEqual(parsePreviewLink("a.md#Section"), { path: "a.md#Section", anchor: "" }, "a slug is lower-case");
  assert.deepEqual(parsePreviewLink("#only"), { path: "#only", anchor: "" });
});

test("previewKindOf: the kernel's map by token, then by open target; unknown kinds and absent tokens are text-only", () => {
  const pv = { "docs/guide.md": "markdown", "plots/a.png": "image", "src/app.py": "code", "report.pdf": "pdf", "odd.bin": "zip" };
  assert.equal(previewKindOf("docs/guide.md", pv), "markdown");
  assert.equal(previewKindOf("docs/guide.md#install", pv), "markdown", "the token's own path when the token carries an anchor");
  assert.equal(previewKindOf("plots/a.png", pv), "image");
  assert.equal(previewKindOf("src/app.py", pv), "code");
  assert.equal(previewKindOf("report.pdf", pv), "pdf");
  assert.equal(previewKindOf("odd.bin", pv), null, "a kind the card cannot show");
  assert.equal(previewKindOf("elsewhere.md", pv), null, "absent: the kernel allowed no preview");
  assert.equal(previewKindOf("docs/guide.md", undefined), null, "no map at all (an older kernel): no request");
});

test("the routes: the slice with its anchor and session, the bytes route for media", () => {
  assert.equal(sliceUrl("docs/a b.md", "sid1", "x-y"), "/file?path=docs%2Fa%20b.md&slice=1&sid=sid1&anchor=x-y");
  assert.equal(sliceUrl("/abs/a.md", null, ""), "/file?path=%2Fabs%2Fa.md&slice=1");
  assert.equal(fileUrl("plots/a.png", "s"), "/file?path=plots%2Fa.png&sid=s");
  assert.equal(langOf("src/app.py"), "python"); assert.equal(langOf("x.tsx"), "typescript"); assert.equal(langOf("Makefile"), "");
  assert.equal(baseName("/a/b/c.md"), "c.md"); assert.equal(baseName("c.md"), "c.md");
});

test("contentFor fills the one shape per kind; a missing anchor falls back to the head with a one-line note", () => {
  const md = contentFor("docs/g.md", "", "markdown", "s", { title: "g.md", text: "# G\nbody", found: true, allowed: true });
  assert.deepEqual(md, { kind: "markdown", title: "g.md", subtitle: undefined, body: { markdown: "# G\nbody" }, note: undefined });
  const sec = contentFor("docs/g.md", "fold", "markdown", "s", { title: "g.md", text: "## Fold\nabout folds", found: true, allowed: true });
  assert.equal(sec.kind, "section"); assert.equal(sec.subtitle, "#fold");
  assert.ok(!("open" in sec), "no open control on a file card: the link itself opens the file at the section (T369); the contract carries no such field since T375");
  const miss = contentFor("docs/g.md", "nope", "markdown", "s", { title: "g.md", text: "# G\nhead", found: false, allowed: true });
  assert.equal(miss.kind, "markdown"); assert.equal(miss.subtitle, undefined);
  assert.equal(miss.note, 'no section "nope" in this file; its head instead'); assert.ok(!("open" in miss));
  const cut = contentFor("docs/g.md", "", "markdown", "s", { title: "g.md", text: "…", found: true, truncated: true, allowed: true });
  assert.equal(cut.note, "the head of the file; the link opens the rest");
  const code = contentFor("src/app.py", "", "code", "s", { title: "app.py", text: "print(1)", allowed: true });
  assert.deepEqual(code.body, { text: "print(1)", lang: "python" }); assert.equal(code.kind, "code");
  const img = contentFor("plots/a.png", "", "image", "s", null);
  assert.deepEqual(img, { kind: "image", title: "a.png", body: { url: "/file?path=plots%2Fa.png&sid=s" } });
  const pdf = contentFor("r.pdf", "", "pdf", null, null);
  assert.equal(pdf.kind, "pdf"); assert.equal(pdf.subtitle, "first page"); assert.equal(pdf.body.url, "/file?path=r.pdf");
  const refused = contentFor("x.md", "", "markdown", "s", { allowed: false, why: "a secrets-shaped name" });
  assert.equal(refused.kind, "text"); assert.equal(refused.note, "a secrets-shaped name"); assert.equal(refused.body.text, "x.md");
  const t = textOnlyContent("/etc/hosts", "", "outside");
  assert.deepEqual(t, { kind: "text", title: "hosts", subtitle: undefined, body: { text: "/etc/hosts" }, note: "outside" });
});

// a fake clock: timers fire in order when advanced
function clock() {
  let now = 0, id = 0;
  const due: { at: number; id: number; fn: () => void }[] = [];
  const setT = (fn: () => void, ms: number) => { const t = { at: now + ms, id: ++id, fn }; due.push(t); return t.id as unknown as ReturnType<typeof setTimeout>; };
  const clearT = (h: ReturnType<typeof setTimeout>) => { const i = due.findIndex((d) => d.id === (h as unknown as number)); if (i >= 0) due.splice(i, 1); };
  const advance = (ms: number) => { now += ms; due.sort((a, b) => a.at - b.at); while (due.length && due[0].at <= now) due.shift()!.fn(); };
  return { setT, clearT, advance };
}

test("HoverIntent: a hover opens after the dwell, a pass-through never opens, leaving closes after the grace", () => {
  const c = clock(); const log: string[] = [];
  const h = new HoverIntent<string>(PREVIEW_DWELL_MS, PREVIEW_GRACE_MS, (t) => log.push("open " + t), () => log.push("close"), c.setT, c.clearT);
  h.enter("a"); c.advance(PREVIEW_DWELL_MS - 1); assert.deepEqual(log, [], "not yet");
  c.advance(1); assert.deepEqual(log, ["open a"]); assert.equal(h.open, "a");
  h.leave(); c.advance(PREVIEW_GRACE_MS - 1); assert.deepEqual(log, ["open a"], "the grace is still running");
  c.advance(1); assert.deepEqual(log, ["open a", "close"]); assert.equal(h.open, null);
  h.enter("b"); c.advance(100); h.leave(); c.advance(1000); assert.deepEqual(log, ["open a", "close"], "a pass-through under the dwell opens nothing");
});

test("HoverIntent: crossing into the card keeps it (pin), leaving the card closes it; a second link retargets; cancel closes at once", () => {
  const c = clock(); const log: string[] = [];
  const h = new HoverIntent<string>(PREVIEW_DWELL_MS, PREVIEW_GRACE_MS, (t) => log.push("open " + t), () => log.push("close"), c.setT, c.clearT);
  h.enter("a"); c.advance(PREVIEW_DWELL_MS);
  h.leave(); c.advance(PREVIEW_GRACE_MS / 2); h.pin(); c.advance(PREVIEW_GRACE_MS * 3);
  assert.deepEqual(log, ["open a"], "pinned inside the card: it stays through the grace");
  h.unpin(); c.advance(PREVIEW_GRACE_MS); assert.deepEqual(log, ["open a", "close"]);
  h.enter("a"); c.advance(PREVIEW_DWELL_MS); h.leave(); h.enter("b"); c.advance(PREVIEW_GRACE_MS * 2);
  assert.deepEqual(log, ["open a", "close", "open a"], "moving to another link within the grace keeps the card up while its dwell runs");
  c.advance(PREVIEW_DWELL_MS); assert.deepEqual(log, ["open a", "close", "open a", "open b"], "…then it shows the new link");
  h.enter("b"); c.advance(PREVIEW_DWELL_MS * 2); assert.deepEqual(log, ["open a", "close", "open a", "open b"], "re-entering the shown link is a no-op");
  h.cancel(); assert.deepEqual(log, ["open a", "close", "open a", "open b", "close"]); assert.equal(h.open, null);
  h.cancel(); assert.equal(log.length, 5, "cancel with nothing open is silent");
});

// ── the remote-load strip (the review: a hover must never send a request elsewhere) ──

const ORIGIN = "http://127.0.0.1:7777", BASE = ORIGIN + "/chat?token=t";

test("remoteLoad reads a value the way the browser does: every spelling of another origin is remote", () => {
  const remote = ["https://remote.invalid/a.png", "//remote.invalid/a.png", "http://remote.invalid:8080/x",
                  "\\\\remote.invalid/b.png", "/\\remote.invalid/c.png", " https://remote.invalid/d.png", "\thttps://remote.invalid/e.png",
                  // TAB, LF and CR anywhere in the value are deleted by the browser before it reads the URL (the review:
                  // a whitespace split before the parse read each of these as two local tokens)
                  "/\t/remote.invalid/p.png", "/\n/remote.invalid/p.png", "/\r/remote.invalid/p.png", "\\\t\\remote.invalid/p.png",
                  "ht\ttps://remote.invalid/q.png", "//remote.in\nvalid/r.png",
                  "javascript:alert(1)", "about:blank", "blob:https://remote.invalid/0000"];
  for (const v of remote) assert.equal(remoteLoad(v, ORIGIN, BASE), true, JSON.stringify(v));
  const remoteSets = ["https://remote.invalid/a.png 1x, https://remote.invalid/b.png 2x", "plots/x.png 1x, https://remote.invalid/y.png 2x",
                      "/\t/remote.invalid/a.png 1x", "plots/x.png 1x,\n//remote.invalid/z.png 2x"];
  for (const v of remoteSets) assert.equal(remoteLoad(v, ORIGIN, BASE, true), true, JSON.stringify(v));
  const local = ["/file?path=x.png", "plots/figure.png", "./a.png", "../b.png", ORIGIN + "/file?path=a", "#frag", "?q=1",
                 "data:image/png;base64,iVBORw0KGgo=", "blob:" + ORIGIN + "/0000-1111", "", "/file?a=1,2", "plots/a b.png"];
  for (const v of local) assert.equal(remoteLoad(v, ORIGIN, BASE), false, JSON.stringify(v));
  const localSets = ["data:image/png;base64,AAAA,BBBB 1x", "plots/a.png 1x, plots/b.png 2x", "/file?path=a.png 480w,\n/file?path=b.png 960w"];
  for (const v of localSets) assert.equal(remoteLoad(v, ORIGIN, BASE, true), false, JSON.stringify(v));
});

/** A minimal inert element tree: what stripRemoteLoads reads (localName, getAttribute) and does (replaceWith, remove, and the
 *  paint arm's removeAttribute and setAttribute: paint-refs.ts dropRemoteRefs). */
type FakeEl = { localName: string; attrs: Record<string, string>; parent: FakeEl | null; children: (FakeEl | string)[];
                getAttribute(n: string): string | null; setAttribute(n: string, v: string): void; removeAttribute(n: string): void;
                replaceWith(n: unknown): void; remove(): void; ownerDocument: { createTextNode(s: string): string } };
function fakeEl(localName: string, attrs: Record<string, string> = {}, children: FakeEl[] = []): FakeEl {
  const e: FakeEl = {
    localName, attrs, parent: null, children: [...children],
    getAttribute(n) { return Object.prototype.hasOwnProperty.call(attrs, n) ? attrs[n] : null; },
    setAttribute(n, v) { attrs[n] = v; },
    removeAttribute(n) { delete attrs[n]; },
    replaceWith(n) { if (!e.parent) return; const i = e.parent.children.indexOf(e); e.parent.children.splice(i, 1, n as string); e.parent = null; },
    remove() { if (!e.parent) return; const i = e.parent.children.indexOf(e); e.parent.children.splice(i, 1); e.parent = null; },
    ownerDocument: { createTextNode: (s) => s },
  };
  for (const c of children) c.parent = e;
  return hideEdges(e);
}
function all(e: FakeEl): FakeEl[] { const out: FakeEl[] = []; for (const c of e.children) if (typeof c !== "string") { out.push(c, ...all(c)); } return out; }
function asRoot(e: FakeEl): ParentNode { return { querySelectorAll: () => all(e) } as unknown as ParentNode; }
function serialize(e: FakeEl): string {
  return e.children.map((c) => typeof c === "string" ? JSON.stringify(c) : "<" + c.localName + Object.entries(c.attrs).map(([k, v]) => " " + k + "=" + JSON.stringify(v)).join("") + ">" + serialize(c) + "</" + c.localName + ">").join("");
}

test("stripRemoteLoads on the inert tree: an img becomes its alt text, every other remote loader goes, local loads stay", () => {
  const root = fakeEl("body", {}, [
    fakeEl("img", { srcset: "https://remote.invalid/a.png 1x", alt: "srcset-only" }),
    fakeEl("picture", {}, [fakeEl("source", { srcset: "https://remote.invalid/b.png" }), fakeEl("img", { src: "plots/figure.png", alt: "pic" })]),
    fakeEl("video", { poster: "https://remote.invalid/p.png" }, [fakeEl("source", { src: "/file?path=v.mp4" })]),
    fakeEl("video", { src: "/file?path=local.mp4" }, [fakeEl("track", { src: "https://remote.invalid/t.vtt" })]),
    fakeEl("audio", { src: "https://remote.invalid/a.mp3" }),
    fakeEl("svg", {}, [fakeEl("image", { href: "https://remote.invalid/s.png" }), fakeEl("image", { "xlink:href": "//remote.invalid/x.png" }), fakeEl("image", { href: "/file?path=ok.png" })]),
    fakeEl("img", { src: "\\\\remote.invalid/c.png", alt: "backslashes" }),
    fakeEl("img", { src: "\thttps://remote.invalid/d.png", alt: "tabbed" }),
    fakeEl("img", { src: "/\t/remote.invalid/f.png", alt: "tab-inside" }),
    fakeEl("img", { src: "https://remote.invalid/e.png" }),
    fakeEl("img", { src: "data:image/png;base64,iVBORw0KGgo=", alt: "inline" }),
    fakeEl("img", { src: ORIGIN + "/file?path=plots/figure.png", alt: "ours" }),
    fakeEl("a", { href: "https://remote.invalid/page" }, [fakeEl("span", {}, [])]),
    fakeEl("p", {}, []),
  ]);
  const n = stripRemoteLoads(asRoot(root), ORIGIN, BASE);
  assert.equal(n, 11, "eleven remote loaders: the poster'd video's own source is local and goes with its parent, uncounted");
  assert.equal(serialize(root),
    '"srcset-only"'
    + '<picture><img src="plots/figure.png" alt="pic"></img></picture>'
    + '<video src="/file?path=local.mp4"></video>'
    + '<svg><image href="/file?path=ok.png"></image></svg>'
    + '"backslashes""tabbed""tab-inside"""'
    + '<img src="data:image/png;base64,iVBORw0KGgo=" alt="inline"></img>'
    + '<img src="' + ORIGIN + '/file?path=plots/figure.png" alt="ours"></img>'
    + '<a href="https://remote.invalid/page"><span></span></a>'
    + '<p></p>',
    "the remote img is its alt text (empty alt: nothing), the poster'd video and its source are gone, the remote track is gone from the local video, the svg keeps its local image, a link is not a load");
});


test("stripRemoteLoads's paint arm on the inert tree: a url() to another origin in an svg paint attribute or in a style declaration is removed from the element, which stays; a same-document url(#g), this origin's own and a relative reference stay; the count adds the removals", () => {
  // guards the strip's contract for the class its element walk never read (the hover card fetched a remote fill during a hover):
  // before the arm the walk returned 0 here and every reference below stayed
  const rect = fakeEl("rect", { width: "12", height: "12", fill: "url(https://remote.invalid/p.svg#p)", stroke: "url(#g)" });
  const masked = fakeEl("rect", { mask: 'image-set("https://remote.invalid/m.png" 1x)', "clip-path": "url(/file?path=p.svg#c)" });
  const own = fakeEl("rect", { fill: "url(" + ORIGIN + "/file?path=p.svg#p)", "marker-end": "url(//remote.invalid/m.svg#m)" });
  const styled = fakeEl("rect", { style: "color: red; mask-image: url(https://remote.invalid/mi.png)" });
  const span = fakeEl("span", { fill: "url(https://remote.invalid/h.svg#p)" });
  const root = fakeEl("body", {}, [fakeEl("svg", { filter: "url(https://remote.invalid/f.svg#f)" }, [rect, masked, own, styled]), span]);
  const n = stripRemoteLoads(asRoot(root), ORIGIN, BASE);
  assert.equal(n, 6, "six removals: the svg's filter, the rect's fill, the mask, the protocol-relative marker-end, the style's mask-image declaration, the span's fill; no element went");
  assert.equal(serialize(root),
    '<svg><rect width="12" height="12" stroke="url(#g)"></rect>'
    + '<rect clip-path="url(/file?path=p.svg#c)"></rect>'
    + '<rect fill="url(' + ORIGIN + '/file?path=p.svg#p)"></rect>'
    + '<rect style="color: red"></rect></svg>'
    + '<span></span>',
    "the remote fill, mask, marker-end and filter are gone and the elements stay; url(#g), the relative clip-path and this origin's fill stay; the style keeps its colour declaration; an HTML span's fill goes too (the names are read on every element)");
});


test("stripRemoteLoads's paint arm on data: references, with the page's base (the hover card) and with none (the notice card): a raster data: URL stays, a data: SVG, XHTML or XML document and a data: URL with no type go", () => {
  // guards the data: rule on the strip's own road (paint-refs.ts dataUrlIsRaster through remoteUrlRef): Firefox loads a
  // document-capable data: reference as a resource document, and its @import fetches another host as the card renders
  for (const base of [BASE, ""]) {
    const RASTER_MASK = "url(data:image/png;base64,iVBORw0KGgo=)", RASTER_FILL = 'url("data:image/webp;base64,UklGRg==")';
    const raster = fakeEl("rect", { mask: RASTER_MASK, fill: RASTER_FILL });
    const svg = fakeEl("rect", { fill: "url(data:image/svg+xml,%3Csvg%2F%3E#p)", stroke: 'url("data:IMAGE/SVG+XML;base64,PHN2Zy8+#p")' });
    const xml = fakeEl("rect", { filter: "url(data:application/xhtml+xml,x#f)", "clip-path": "url(data:text/xml,x#c)", mask: "url(data:application/xml,x#m)" });
    const untyped = fakeEl("rect", { fill: "url(data:,x#p)", width: "4" });
    const root = fakeEl("body", {}, [fakeEl("svg", {}, [raster, svg, xml, untyped])]);
    assert.equal(stripRemoteLoads(asRoot(root), ORIGIN, base), 6, JSON.stringify(base) + ": six removals, the two svg, the three xml and the untyped");
    assert.equal(serialize(root),
      "<svg><rect mask=" + JSON.stringify(RASTER_MASK) + " fill=" + JSON.stringify(RASTER_FILL) + "></rect>"
      + "<rect></rect><rect></rect>"
      + '<rect width="4"></rect></svg>',
      JSON.stringify(base) + ": the raster mask and fill stay as written, every other data: reference goes, the elements stay");
  }
});


test("the notice card's strip passes no base (feed.ts noticeBodyNodes), so its paint arm removes a relative and a root-relative same-origin reference and keeps an absolute same-origin one, url(#g) and a raster data: URL: a disclosed residual that fails closed", () => {
  // guards the statement of a disclosed residual, so it is stated rather than incidental: the notice card hands
  // stripRemoteLoads an empty base, under which no relative URL resolves, and the paint arm fails closed on what it cannot
  // resolve. sanitizeMd's own pass resolves against document.baseURI and keeps these references; this strip then removes
  // them. The same empty base already costs a notice body its relative, same-origin and data: images (the element walk);
  // passing the page's URL fixes both and is the notice card's own follow-up. When that lands, the call-site assertion
  // below goes red: retire this test and the residual's line in the ledger entry with it.
  const rel = fakeEl("rect", { fill: "url(plots/own.svg#p)" });
  const rootRel = fakeEl("rect", { fill: "url(/plots/own.svg#p)" });
  const abs = fakeEl("rect", { fill: "url(" + ORIGIN + "/plots/own.svg#p)" });
  const frag = fakeEl("rect", { fill: "url(#g)" });
  const data = fakeEl("rect", { fill: "url(data:image/png;base64,iVBORw0KGgo=)" });
  const root = fakeEl("body", {}, [fakeEl("svg", {}, [rel, rootRel, abs, frag, data])]);
  assert.equal(stripRemoteLoads(asRoot(root), ORIGIN, ""), 2, "with no base the relative and the root-relative reference cannot resolve and are removed, failing closed");
  assert.deepEqual([rel, rootRel, abs, frag, data].map((e) => e.getAttribute("fill")),
    [null, null, "url(" + ORIGIN + "/plots/own.svg#p)", "url(#g)", "url(data:image/png;base64,iVBORw0KGgo=)"],
    "the absolute same-origin reference, the same-document one and the raster data: URL stay, because none needs a base");
  const FEED = require("node:fs").readFileSync(require("node:path").resolve(process.cwd(), "..", "ui", "webview", "feed.ts"), "utf8") as string;
  assert.deepEqual(FEED.match(/^\s*stripRemoteLoads\(.*$/gm), ['    stripRemoteLoads(clean, (typeof window !== "undefined" && window.location ? window.location.origin : ""), "");'],
    "the notice card's one strip call still passes an empty base: the residual this test states is live (red when the follow-up passes the page's URL: retire this test and the ledger entry's line)");
});


test("a remote session's preview fetches ride the host relay with the bare sid, as the inline images do (T364)", () => {
  // the popover asked the LOCAL origin for a remote session's file and got the wrong kernel's answer; the route is the
  // one preview.ts builds for an inline image: /remote/<host>/file with the sid the remote kernel knows
  const rsid = "TESTHOST:11111111-2222-3333-4444-555555555555";
  assert.deepEqual(previewRoute(rsid), { base: "/remote/TESTHOST/file", sid: "11111111-2222-3333-4444-555555555555" });
  assert.deepEqual(previewRoute("11111111-2222-3333-4444-555555555555"), { base: "/file", sid: "11111111-2222-3333-4444-555555555555" });
  assert.deepEqual(previewRoute(null), { base: "/file", sid: "" });
  assert.equal(sliceUrl("docs/a.md", rsid, "top"), "/remote/TESTHOST/file?path=docs%2Fa.md&slice=1&sid=11111111-2222-3333-4444-555555555555&anchor=top");
  assert.equal(fileUrl("plots/a.png", rsid), "/remote/TESTHOST/file?path=plots%2Fa.png&sid=11111111-2222-3333-4444-555555555555");
  assert.equal(fileUrl("plots/a.png", "s"), "/file?path=plots%2Fa.png&sid=s", "a local session: the local route, unchanged");
  const fs = require("node:fs"), path = require("node:path");
  const PREVIEW = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "preview.ts"), "utf8");
  const FP = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "file-preview.ts"), "utf8");
  for (const src of [PREVIEW, FP]) assert.match(src, /"\/remote\/" \+ encodeURIComponent\(host\) \+ "\/file" : "\/file"/, "the two builders share the relay's shape");
});
