// An absolute-path figure in a Rendered markdown file — `![p95](/repo/notes-api/figs/a.png)` — is loaded from the
// kernel like a relative one (Slice 3, review round 2). Before this, rewriteFigureSrcs left a src beginning with `/`
// untouched, so the browser fetched it from the dashboard ORIGIN, where no route serves it, and the picture was a
// broken-image box; meanwhile the poll (figurePath) HEADed it as a kernel path, the panel matched the embed by it as
// a path (embedPath / srcIsEmbed), and the host hashed the file on disk — a region could be drawn on the box and
// saved with the hash of a figure the person never saw. The viewer now takes an absolute src the way its three
// readers do: the kernel's /file for that path itself. A protocol-relative `//host/…` is a web address to the browser
// and every markdown reader, so it stays as written, like a scheme URL. Executable over a DOM stand-in (the seam
// test's idiom) against the REAL module, and cross-checked against the model's and the panel's readers, so the three
// cannot drift apart again without this failing. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";

// ── a DOM stand-in: attributes and the one selector rewriteFigureSrcs uses ─────────────────────────
class El {
  tagName: string;
  attrs = new Map<string, string>();
  childNodes: El[] = [];
  constructor(tag: string) { this.tagName = tag.toUpperCase(); }
  appendChild(c: El): El { this.childNodes.push(c); return c; }
  setAttribute(k: string, v: string): void { this.attrs.set(k, v); }
  getAttribute(k: string): string | null { return this.attrs.get(k) ?? null; }
  hasAttribute(k: string): boolean { return this.attrs.has(k); }
  removeAttribute(k: string): void { this.attrs.delete(k); }
  addEventListener(): void { /* inert */ }
  removeEventListener(): void { /* inert */ }
  querySelectorAll(sel: string): El[] {
    assert.equal(sel, "img[src]", "the stand-in answers the one selector the rewrite uses");
    const out: El[] = [];
    const walk = (n: El) => { for (const c of n.childNodes) { if (c.tagName === "IMG" && c.hasAttribute("src")) out.push(c); walk(c); } };
    walk(this);
    return out;
  }
}
const win: any = new EventTarget();
win.parent = win;
(globalThis as any).window = win;
(globalThis as any).document = {
  createElement: (tag: string) => new El(tag),
  createTextNode: (s: string) => s,
  getElementById: () => null,
  addEventListener: () => { /* inert */ },
  removeEventListener: () => { /* inert */ },
  body: new El("body"),
};
const store = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
  setItem: (k: string, v: string) => { store.set(k, String(v)); },
  removeItem: (k: string) => { store.delete(k); },
};

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ROOT = "/repo/notes-api";
const FILE = ROOT + "/docs/report.md";
const DIR = ROOT + "/docs/";
const q = (p: string, sid: string | null = SID) => "/file?path=" + encodeURIComponent(p) + (sid ? "&sid=" + sid : "");
const img = (src: string, extra: Record<string, string> = {}) => {
  const i = new El("img");
  i.setAttribute("src", src);
  for (const k of Object.keys(extra)) i.setAttribute(k, extra[k]);
  return i;
};
const rewrite = async (figures: El[], dir = DIR, sid: string | null = SID) => {
  const fv = await import("./file-view");
  const root = new El("div");
  const p = root.appendChild(new El("p"));
  for (const f of figures) p.appendChild(f);
  fv.rewriteFigureSrcs(root as unknown as ParentNode, dir, sid);
};

test("an absolute-path src goes to the kernel's /file for that path itself, the authored value kept in data-fv-src; percent-encoding is decoded into the path; the file's directory plays no part", async () => {
  const plain = img(ROOT + "/figs/a.png");
  const encoded = img("/srv/figs/p95%20latency.png");
  const malformed = img("/srv/figs/bad%E0%A4%A.png");
  const dotted = img("/srv/figs/../figs/./a.png");
  const rootFile = img("/a.png");
  const authoredAttr = img(ROOT + "/figs/b.png", { "data-fv-src": "spoofed.png" });
  await rewrite([plain, encoded, malformed, dotted, rootFile, authoredAttr], "/some/other/dir/");
  assert.equal(plain.getAttribute("src"), q(ROOT + "/figs/a.png"), "the path itself, not <dir>/<src>");
  assert.equal(plain.getAttribute("data-fv-src"), ROOT + "/figs/a.png", "the authored spelling rides along, as for a relative figure");
  assert.equal(encoded.getAttribute("src"), q("/srv/figs/p95 latency.png"), "marked's percent-encoding decoded back to the file's name on disk");
  assert.equal(encoded.getAttribute("data-fv-src"), "/srv/figs/p95%20latency.png", "…while data-fv-src keeps the embed's own spelling");
  assert.equal(malformed.getAttribute("src"), q("/srv/figs/bad%E0%A4%A.png"), "a malformed escape: taken as written");
  assert.equal(dotted.getAttribute("src"), q("/srv/figs/../figs/./a.png"), "`..` and `.` pass through for the kernel to resolve and gate");
  assert.equal(rootFile.getAttribute("src"), q("/a.png"), "a file at the filesystem root is still a path, not the dashboard's origin");
  assert.equal(authoredAttr.getAttribute("data-fv-src"), ROOT + "/figs/b.png", "an authored data-fv-src is overwritten: the attribute means this viewer rewrote this src");
});

test("a remote session's absolute-path figure relays through the owning host, as the file itself did; no sid: the bare /file route", async () => {
  const remote = img("/srv/figs/a.png");
  await rewrite([remote], DIR, "gpu1:" + SID);
  assert.equal(remote.getAttribute("src"), "/remote/gpu1/file?path=" + encodeURIComponent("/srv/figs/a.png") + "&sid=" + SID);
  const local = img("/srv/figs/a.png");
  await rewrite([local], "", null);
  assert.equal(local.getAttribute("src"), q("/srv/figs/a.png", null));
});

test("a protocol-relative src (`//host/…`) is a web address, not a path with a doubled slash: left as written, no data-fv-src — like a scheme URL", async () => {
  const proto = img("//cdn.example.test/x.png", { "data-fv-src": "authored.png" });
  const https = img("https://example.test/x.png");
  const data = img("data:image/png;base64,iVBORw0KGgo=");
  await rewrite([proto, https, data]);
  for (const f of [proto, https, data]) {
    assert.equal(f.getAttribute("data-fv-src"), null, "untouched: " + f.getAttribute("src"));
  }
  assert.equal(proto.getAttribute("src"), "//cdn.example.test/x.png");
  assert.equal(https.getAttribute("src"), "https://example.test/x.png");
  assert.equal(data.getAttribute("src"), "data:image/png;base64,iVBORw0KGgo=");
});

test("the three readers of an embed's destination agree: the path the viewer loads is the path the poll HEADs (figurePath) and the path the panel matches the embed by (srcIsEmbed / embedPath) — for every path spelling, absolute included", async () => {
  const fc = await import("./file-comments");
  const model = await import("./file-comments-model");
  const dests = [
    "plot.png", "figs/plot.png", "../assets/logo.png", "./plot.png", "six%20seven.png",
    ROOT + "/figs/a.png", "/srv/figs/p95%20latency.png", "/srv/figs/../figs/./a.png", "/a.png",
  ];
  const figures = dests.map((d) => img(d));
  await rewrite(figures);
  for (let i = 0; i < dests.length; i++) {
    const dest = dests[i];
    const loaded = figures[i].getAttribute("src")!;
    const kernelPath = fc.fileUrlPath(loaded);
    assert.ok(kernelPath !== null, "the viewer loads " + dest + " from the kernel's /file");
    assert.equal(kernelPath, model.figurePath(FILE, dest), "the poll HEADs the very path the viewer shows, for " + dest);
    assert.ok(fc.srcIsEmbed(loaded, dest, FILE), "the panel matches the loaded picture to its embed line, for " + dest);
    assert.equal(fc.normPath(kernelPath!), fc.embedPath(FILE, dest), "and names the same file the embed does, for " + dest);
  }
  // a URL is nobody's path: the viewer leaves it, the poll has no target for it
  for (const u of ["https://example.test/x.png", "data:image/png;base64,iVBORw0KGgo="]) {
    const f = img(u);
    await rewrite([f]);
    assert.equal(f.getAttribute("src"), u);
    assert.equal(fc.fileUrlPath(u), null);
    assert.equal(model.figurePath(FILE, u), null);
  }
});
