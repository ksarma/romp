// The figure gate's reader of an svg's paint references (figure-gate.ts cssUrls, refUrls, PAINT_ATTRS; decision 8 of
// plans/markdown-viewer.md), executed under node. Review of Slice 4, round 2: an inline svg's `fill`, `stroke`, `filter`,
// `clip-path`, `mask` and `marker-*` attributes are CSS values, and a `url(https://host/p.svg#p)` in any of them fetched
// the host the moment the file rendered, with no placeholder and no click, because the gate read `src`, `srcset`, `poster`
// and `href` alone. The reader follows CSS Syntax's tokenizer, since the browser does: measured 2026-09-09 in headless
// Chromium, every spelling below marked "fetched" made a request, and the ones marked "not fetched" did not. The DOM half
// (paintRefs over a sanitized svg, the placeholder, the click, the URL kind) runs over the real Files bundle in
// md-config-svg-paint-gate-browser.test.ts. Synthetic values only: hosts under .test.
import { test } from "node:test";
import * as assert from "node:assert/strict";

(globalThis as any).localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };   // settings.ts reads it at call time
import { cssUrls, refUrls, remoteHost, PAINT_ATTRS } from "./figure-gate";

const BASE = "http://romp.test/files";

test("cssUrls: a url token in every spelling the browser fetches: plain, quoted, whitespace inside the parens, upper-case URL(, a fallback colour after it, a filter list, two mask layers, an image-set candidate as a string or a url, -webkit-cross-fade's two urls, protocol-relative", () => {
  assert.deepEqual(cssUrls("url(https://fill.test/p.svg#p)"), ["https://fill.test/p.svg#p"]);
  assert.deepEqual(cssUrls('url("https://dq.test/p.svg#p")'), ["https://dq.test/p.svg#p"], "double quotes (the HTML parser has decoded &quot; by now)");
  assert.deepEqual(cssUrls("url('https://sq.test/p.svg#p')"), ["https://sq.test/p.svg#p"]);
  assert.deepEqual(cssUrls("url(   https://sp.test/p.svg#p   )"), ["https://sp.test/p.svg#p"], "whitespace inside the parens is not part of the URL");
  assert.deepEqual(cssUrls("URL(https://upper.test/p.svg#p)"), ["https://upper.test/p.svg#p"], "the function name is case-insensitive");
  assert.deepEqual(cssUrls("url(https://fb.test/p.svg#p) red"), ["https://fb.test/p.svg#p"], "a paint's fallback colour");
  assert.deepEqual(cssUrls("blur(2px) url(https://filt.test/p.svg#f)"), ["https://filt.test/p.svg#f"], "a filter list");
  assert.deepEqual(cssUrls("url(https://ml1.test/a.svg#m), url(https://ml2.test/b.svg#m)"), ["https://ml1.test/a.svg#m", "https://ml2.test/b.svg#m"], "two mask layers");
  assert.deepEqual(cssUrls('image-set("https://ms.test/a.png" 1x)'), ["https://ms.test/a.png"], "a mask reads the CSS shorthand: an image-set candidate written as a string fetched");
  assert.deepEqual(cssUrls("image-set(url(https://msu.test/a.png) 1x)"), ["https://msu.test/a.png"]);
  assert.deepEqual(cssUrls("-webkit-cross-fade(url(https://wcf.test/a.png), url(https://wcf2.test/b.png), 50%)"), ["https://wcf.test/a.png", "https://wcf2.test/b.png"]);
  assert.deepEqual(cssUrls("url(//pr.test/p.svg#p)"), ["//pr.test/p.svg#p"]);
  assert.equal(remoteHost("//pr.test/p.svg#p", BASE), "pr.test", "protocol-relative is a web address");
});

test("cssUrls decodes CSS escapes as the browser does: in the function name (\\75 rl( and u\\72 l( and a six-digit \\000075 are url(), in an unquoted URL (\\40 is @, so github.com\\40 evil.test fetches evil.test; \\69 inside the host; \\) stays in the URL) and in a string; a comment before the function is skipped", () => {
  assert.deepEqual(cssUrls("\\75 rl(https://escfn.test/p.svg#p)"), ["https://escfn.test/p.svg#p"], "fetched: the escape and its one whitespace spell u");
  assert.deepEqual(cssUrls("u\\72 l(https://escfn2.test/p.svg#p)"), ["https://escfn2.test/p.svg#p"], "fetched");
  assert.deepEqual(cssUrls("\\000075rl(https://six.test/p.svg#p)"), ["https://six.test/p.svg#p"], "six hex digits end the escape without whitespace");
  assert.deepEqual(cssUrls('\\69 mage-set("https://escset.test/a.png" 1x)'), ["https://escset.test/a.png"], "fetched: an escaped image-set");
  const at = cssUrls("url(https://github.com\\40 escat.test/p.svg#p)");
  assert.deepEqual(at, ["https://github.com@escat.test/p.svg#p"], "fetched from escat.test: the text as written names the allowed host, the browser's reading names another");
  assert.equal(remoteHost(at[0], BASE), "escat.test", "the host the browser fetched from");
  assert.deepEqual(cssUrls("url('https://github.com\\40 escatq.test/p.svg#p')"), ["https://github.com@escatq.test/p.svg#p"], "the same inside a string");
  assert.deepEqual(cssUrls("url(https://ev\\69 lhost.test/p.svg#p)"), ["https://evilhost.test/p.svg#p"], "fetched from evilhost.test");
  assert.deepEqual(cssUrls("url(https://uesc.test/p\\)x.svg#p)"), ["https://uesc.test/p)x.svg#p"], "fetched as https://uesc.test/p)x.svg: an escaped paren is part of the URL");
  assert.deepEqual(cssUrls("/**/url(https://cmt.test/p.svg#p)"), ["https://cmt.test/p.svg#p"], "fetched: a comment is not a token");
  assert.deepEqual(cssUrls("/* url(https://incmt.test/p.svg) */ red"), [], "a url inside a comment is nothing");
  assert.deepEqual(cssUrls("url(https://t.test/p\\"), ["https://t.test/p\ufffd"], "a backslash at the end stands for U+FFFD, the host still read");
  assert.deepEqual(cssUrls('"https://co.test/\\\na"'), ["https://co.test/a"], "a backslash before a newline continues a string");
});

test("cssUrls reads nothing where the browser reads no function: a comment inside the name, whitespace between url and its paren, a local fragment reference stays the page's own, plain colours and keywords, an empty url()", () => {
  assert.deepEqual(cssUrls("u/**/rl(https://cmtname.test/p.svg#p)"), [], "not fetched: a comment splits the name");
  assert.deepEqual(cssUrls("url (https://nofn.test/p.svg#p)"), [], "not fetched: an ident then a paren block");
  assert.deepEqual(cssUrls("xurl(https://xfn.test/p.svg#p)"), [], "an unknown function whose argument is not a url token");
  assert.deepEqual(cssUrls("url(#g)"), ["#g"]);
  assert.equal(remoteHost("#g", BASE), null, "a fragment resolves to the page itself: never gated");
  assert.deepEqual(cssUrls("red"), []);
  assert.deepEqual(cssUrls("none"), []);
  assert.deepEqual(cssUrls(""), []);
  assert.deepEqual(cssUrls("url()"), []);
  assert.deepEqual(cssUrls("url( )"), []);
  assert.deepEqual(cssUrls('url("")'), []);
  assert.deepEqual(cssUrls("rgb(1, 2, 3)"), []);
});

test("cssUrls judges on purpose what the browser would refuse, so a bad spelling costs a click and never a request: a url token broken by inner whitespace, a quote or a paren is read to that point; a bare string in a paint is read", () => {
  assert.deepEqual(cssUrls("url(https://badsp.test/p.svg x)"), ["https://badsp.test/p.svg"], "not fetched by the browser (a bad url token); judged as read");
  assert.deepEqual(cssUrls("url(https://badparen.test/p(.svg)"), ["https://badparen.test/p"]);
  assert.deepEqual(cssUrls("url(https://badq.test/p\"x.svg)"), ["https://badq.test/p", "x.svg)"], "the quote starts a string the reader takes to the end");
  assert.deepEqual(cssUrls('"https://strfill.test/p.svg"'), ["https://strfill.test/p.svg"], "not fetched by the browser in a fill; judged");
  assert.deepEqual(cssUrls('"https://unterminated.test/a'), ["https://unterminated.test/a"]);
  assert.deepEqual(cssUrls('"https://nl.test/a\nb"'), ["https://nl.test/a"], "an unescaped newline ends a string (a bad string to the browser)");
});

test("refUrls: a paint attribute's URLs are its tokens, a srcset's its candidates, any other attribute's the value itself; PAINT_ATTRS names the eight presentation attributes DOMPurify's svg profile keeps that take a url()", () => {
  const el = {} as Element;
  assert.deepEqual(refUrls({ el, attr: "fill", value: "url(https://a.test/p.svg#p) red" }), ["https://a.test/p.svg#p"]);
  assert.deepEqual(refUrls({ el, attr: "mask", value: 'image-set("https://b.test/a.png" 1x)' }), ["https://b.test/a.png"]);
  assert.deepEqual(refUrls({ el, attr: "clip-path", value: "url(#c)" }), ["#c"]);
  assert.deepEqual(refUrls({ el, attr: "srcset", value: "a.png 1x, https://c.test/b.png 2x" }), ["a.png", "https://c.test/b.png"]);
  assert.deepEqual(refUrls({ el, attr: "src", value: "url(https://d.test/x.png)" }), ["url(https://d.test/x.png)"], "a src is a URL as written, never CSS");
  assert.deepEqual([...PAINT_ATTRS], ["fill", "stroke", "filter", "clip-path", "mask", "marker-start", "marker-mid", "marker-end"]);
});
