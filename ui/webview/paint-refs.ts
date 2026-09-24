// A CSS url() that names a document on another origin, found in an element's attributes and removed before the element
// reaches a live page. An inline svg's `fill`, `stroke`, `mask`, `clip-path`, `filter` and `marker-*` attributes hold a CSS
// value, and a `url(https://host/p.svg#p)` in one makes the browser request that document the moment the svg renders, with
// no click. The sanitizer keeps all eight (DOMPurify's svg attribute list) and its URI test passes `url(`, so this module is
// the step after it: the sanitizer runs dropRemoteRefs on every body it hands back (md-sanitize.ts sanitizeMd, unless the
// caller opts out) and the file preview card's strip runs it beside its element walk (file-preview.ts stripRemoteLoads).
// The file viewer does not strip: it gates the same references behind a click (figure-gate.ts) and reads them through
// cssUrls, which lives here so the two readers are one.
//
// The two sets of names were DERIVED by execution, not listed from memory: on 2026-09-23, in headless Chromium 151,
// Firefox 153 and WebKit 26.5 driven through Playwright. URL_PROPERTIES: `CSS.supports(property, value)` over every
// property the engine exposes, with eighteen value templates that put a url() where a grammar can take one (a bare and a
// quoted url, a paint with a fallback colour, a cursor list, an image-set, a filter list, the background, border-image,
// mask and list-style shorthands among them); a property is in the set when any template is supported (Chromium 30,
// Firefox 28, WebKit 33). URL_ATTRS: every property name the engine knows plus DOMPurify's html, svg, xml and MathML
// attribute lists (988 candidate names in Chromium), each set as an attribute on an svg `<rect>` through innerHTML and its
// computed style read back; a name is in the set when the computed value carries the url() (the same nine in all three
// engines). Each set is the UNION over the three engines, so a name any one engine reads is judged in every engine.
// `cursor` is carried although the sanitizer drops that attribute today: the set is what the engines read, not what the
// sanitizer keeps, so a later widening of the allowlist is covered with no change here (paint-refs-census.test.ts holds
// the sanitizer's surviving attributes to these sets).
//
// The rule, for every URL cssUrls reads out of a value (a url token or a quoted string, in whatever function):
//   STAYS: a same-document reference, `#id` (decided before any parse, so it stays with no base too); a `data:` URL whose
//     media type is a raster image (DATA_RASTER_TYPES: png, jpeg, gif, webp, avif, bmp and the two icon types), the type
//     read as the Fetch standard's data: URL processor reads it (dataMediaType: the essence lower-cased, parameters and
//     `;base64` outside it, a missing type `text/plain`); a URL whose origin is one of the page's own, resolved against the
//     document's base (a relative `url(p.svg#p)` resolves to the page's origin; a `blob:` URL has its inner URL's origin).
//   DROPS: everything else: another host, another scheme or port on the same host, a protocol-relative `//host/x`,
//     `javascript:` and `about:` (an opaque origin, never the page's), a `data:` URL of any other media type, and a value
//     the URL parser refuses. A `data:` SVG document named by a paint attribute with a fragment (`url(data:image/svg+xml,
//     ...#p)`) loads as a resource document in Firefox, and that document's own `@import` fetches another host with no
//     click; an XHTML or XML document does the same (measured in Firefox 153 on 2026-09-23 and 2026-09-24, for fill,
//     stroke, mask, filter and clip-path; Chromium 151 and WebKit 26.5 loaded none). Only a raster cannot be a document.
//     An unparsable value FAILS CLOSED: removing a reference the browser could not have fetched costs nothing, and keeping
//     one it can read costs a request.
// A value with ANY remote member (two mask layers, an image-set with one remote candidate, a paint with a fallback colour)
// drops whole: a presentation attribute is removed, and in a `style` attribute the declaration is removed and the rest of
// the attribute kept. Nothing is rewritten, so a paint's fallback colour goes with its url(), and the element stays and
// paints with the property's initial value (`fill` black, `stroke`, `mask` and `clip-path` none, so a masked shape shows
// whole).
//
// Import-free, and it touches the DOM through querySelectorAll, getAttribute, setAttribute and removeAttribute alone, so
// the node tests run it over a fake tree.

/** The attributes whose value the engines read as a CSS value that may hold a url(): derived (see the header), sorted. */
export const URL_ATTRS: readonly string[] = [
  "clip-path", "cursor", "fill", "filter", "marker-end", "marker-mid", "marker-start", "mask", "stroke",
];

/** The CSS properties whose value may hold a url(), the union over Chromium, Firefox and WebKit: derived (see the header),
 *  sorted. `-moz-border-image` is Firefox's alone; `-webkit-backdrop-filter`, `mask-border` and `mask-border-source`
 *  WebKit's alone; the other thirty are Chromium's. */
export const URL_PROPERTIES: readonly string[] = [
  "-moz-border-image", "-webkit-backdrop-filter", "-webkit-border-image", "-webkit-clip-path", "-webkit-filter",
  "-webkit-mask", "-webkit-mask-box-image", "-webkit-mask-box-image-source", "-webkit-mask-image", "-webkit-shape-outside",
  "backdrop-filter", "background", "background-image", "border-image", "border-image-source", "clip-path", "content",
  "cursor", "fill", "filter", "list-style", "list-style-image", "marker", "marker-end", "marker-mid", "marker-start", "mask",
  "mask-border", "mask-border-source", "mask-image", "offset", "offset-path", "shape-outside", "stroke",
];

// ── the reader: CSS Syntax's tokenizer, moved from figure-gate.ts unchanged ─────────────────────────────

/** CSS's whitespace: a space, a tab, a newline. After cssPreprocess every newline is one LF; CR and FF stay in the class
 *  so a value that skipped the pass still reads its lone CR or FF as the one newline it is. */
const CSS_WS = /[ \t\n\r\f]/;
const CSS_HEX = /[0-9a-fA-F]/;
/** A name code point: a letter, a digit, `_`, `-`, or any non-ASCII code point. */
const CSS_NAME = /[A-Za-z0-9_\-\u0080-\uffff]/;
/** One CSS escape, `i` at the code point after the backslash: the code point it stands for and the index after it. Up to
 *  six hex digits, with one whitespace after them consumed; any other code point stands for itself; a backslash at the
 *  end of the value is U+FFFD. */
export function cssEscape(s: string, i: number): [string, number] {
  if (i >= s.length) return ["\ufffd", i];
  if (!CSS_HEX.test(s[i])) return [s[i], i + 1];
  let j = i;
  while (j < s.length && j - i < 6 && CSS_HEX.test(s[j])) j++;
  const cp = parseInt(s.slice(i, j), 16);
  if (j < s.length && CSS_WS.test(s[j])) j++;
  return [cp === 0 || cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff) ? "\ufffd" : String.fromCodePoint(cp), j];
}
/** CSS Syntax's preprocessing (section 3.3), run on the whole value before anything is tokenized: a CRLF pair, a lone CR
 *  and a FF are each one LF; U+0000 and a lone surrogate are U+FFFD. The tokenizer's "one whitespace after a hex escape"
 *  then eats a CRLF pair whole, as the browser's does, and a string ends at a CR or a FF as it does in the browser. Read
 *  raw, the escape ate the CR and the LF ended the name at `u`, so `\75&#13;&#10;rl(https://host/p.svg#p)` in a note's
 *  HTML block (the HTML parser keeps a character-reference CR LF in an attribute where it folds a literal pair to LF, and
 *  the sanitizer passes the value) kept its fill and fetched the host on open with no placeholder, in both kinds (review
 *  of Slice 4, round 3). The attribute itself stays as written: the browser preprocesses it the same way. Of the three
 *  rules only the newline one can fire on a parsed attribute (the HTML parser has already made U+0000 and a lone
 *  surrogate U+FFFD); the other two keep the reader exact on a value handed over any other way. */
export function cssPreprocess(value: string): string {
  const newlines = value.replace(/\r\n|[\r\f]/g, "\n");
  return newlines.replace(/\0|[\ud800-\udbff][\udc00-\udfff]|[\ud800-\udfff]/g, (m) => m.length === 2 ? m : "\ufffd");
}
/** Every URL a CSS-valued attribute names, as CSS Syntax's tokenizer reads it, the value preprocessed first (cssPreprocess):
 *  the url tokens (`url(` and an unquoted URL run to the `)` or to whitespace) and every quoted string (the `url("...")`
 *  form, an `image-set("...")` candidate, any other function's argument alike), with comments skipped and escapes decoded
 *  in function names, URLs and strings (so `\75 rl(` is `url(` and `github.com\40 evil.test` is `github.com@evil.test`, as
 *  the browser reads them). Judged on purpose beyond what the browser fetches: a string in a function that takes none, and
 *  a url token the browser refuses (a quote, a paren or inner whitespace before its `)`, read to that point). Gating such a
 *  value costs one click; missing a value the browser reads costs a request (measured 2026-09-09: every spelling above
 *  fetched). The strip below reads the same way for the same reason: removing such a value costs an attribute. */
export function cssUrls(attrValue: string): string[] {
  const value = cssPreprocess(attrValue);
  const out: string[] = [];
  const n = value.length;
  let i = 0;
  while (i < n) {
    const c = value[i];
    if (c === "/" && value[i + 1] === "*") { const e = value.indexOf("*/", i + 2); i = e < 0 ? n : e + 2; continue; }
    if (c === '"' || c === "'") {
      let str = "";
      i++;
      while (i < n && value[i] !== c && value[i] !== "\n") {
        if (value[i] !== "\\") { str += value[i++]; continue; }
        if (value[i + 1] === "\n") { i += 2; continue; }        // a backslash before a newline continues the string
        const [ch, j] = cssEscape(value, i + 1); str += ch; i = j;
      }
      if (i < n && value[i] === c) i++;
      if (str) out.push(str);
      continue;
    }
    if (c === "\\" || CSS_NAME.test(c)) {
      let name = "";
      while (i < n && (value[i] === "\\" || CSS_NAME.test(value[i]))) {
        if (value[i] !== "\\") { name += value[i++]; continue; }
        const [ch, j] = cssEscape(value, i + 1); name += ch; i = j;
      }
      if (value[i] !== "(") continue;
      i++;                                                        // a function: its arguments run through this loop
      if (name.toLowerCase() !== "url") continue;
      while (i < n && CSS_WS.test(value[i])) i++;
      if (value[i] === '"' || value[i] === "'") continue;         // url("..."): the string arm reads it
      let url = "";
      while (i < n && value[i] !== ")" && !CSS_WS.test(value[i]) && value[i] !== '"' && value[i] !== "'" && value[i] !== "(") {
        if (value[i] !== "\\") { url += value[i++]; continue; }
        const [ch, j] = cssEscape(value, i + 1); url += ch; i = j;
      }
      if (url) out.push(url);
      continue;
    }
    i++;
  }
  return out;
}

// ── the judgment ─────────────────────────────────────────────────────────────────────────────────────

/** The media types a `data:` reference may have and stay: the raster image types, sorted. A raster cannot load as a
 *  document, so it fetches nothing, and a raster `data:` mask draws (measured in Chromium 151 and Firefox 153, 2026-09-24).
 *  Every other type drops (the header's rule). */
export const DATA_RASTER_TYPES: readonly string[] = [
  "image/avif", "image/bmp", "image/gif", "image/jpeg", "image/png", "image/vnd.microsoft.icon", "image/webp",
  "image/x-icon",
];

/** HTTP's token code points: the alphabet of a MIME type's type and subtype (the MIME Sniffing standard). */
const HTTP_TOKEN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;

/** The essence (`type/subtype`, lower-cased) of a `data:` URL's media type, read as the Fetch standard's data: URL processor
 *  reads it: the URL serialized without its fragment and with `data:` removed (so a `?` and what follows it are read, as
 *  the processor reads them); the text before the first comma, with ASCII whitespace stripped from both ends; then parsed
 *  as a MIME type, where a type or subtype that is empty or holds anything but token code points is a failure and reads as
 *  `text/plain`. The processor's removal of a trailing `;base64` and its `text/plain` in front of a leading `;` are left
 *  out: the essence ends at the first `;`, so neither can change it. So case, parameters and `;base64` do not change the
 *  essence, a missing type is `text/plain`, and a percent-encoded `/` is no slash. null when there is no comma: the
 *  processor fails and the browser loads nothing. `u.protocol` must be `data:`. Pure. */
export function dataMediaType(u: URL): string | null {
  const href = u.href;
  const hash = href.indexOf("#");
  const input = href.slice(u.protocol.length, hash < 0 ? href.length : hash);
  const comma = input.indexOf(",");
  if (comma < 0) return null;
  const mime = input.slice(0, comma).replace(/^[\t\n\f\r ]+|[\t\n\f\r ]+$/g, "");
  const m = /^([^/;]*)\/([^;]*)/.exec(mime);
  if (!m) return "text/plain";
  const type = m[1], subtype = m[2].replace(/[\t\n\r ]+$/, "");
  if (!HTTP_TOKEN.test(type) || !HTTP_TOKEN.test(subtype)) return "text/plain";
  return (type + "/" + subtype).toLowerCase();
}

/** Whether a `data:` URL may stay as a local reference: its media type's essence (dataMediaType) is one of
 *  DATA_RASTER_TYPES. A URL the processor refuses (no comma) is not, and drops: the browser could not load it, so removing
 *  it costs nothing. `u.protocol` must be `data:`. The one decision for every reader of a `data:` reference. Pure. */
export function dataUrlIsRaster(u: URL): boolean {
  const essence = dataMediaType(u);
  return essence !== null && DATA_RASTER_TYPES.includes(essence);
}

/** Whether `value` names any URL off every origin in `origins`, under the rule in the header: each URL cssUrls reads out of
 *  it stays when it is a `#` reference, a `data:` URL of a raster type (dataUrlIsRaster), or resolves (against `base`; with
 *  no base, parsed as it stands) to one of `origins`; any other, an unparsable one and a `data:` URL of any other type
 *  included, makes the whole value remote. An opaque origin (`null`, the origin of `javascript:`, `about:` and a sandboxed
 *  page alike) is never one of the page's own. Pure. */
export function remoteUrlRef(value: string, origins: readonly string[], base: string): boolean {
  for (const ref of cssUrls(value)) {
    if (ref.startsWith("#")) continue;
    let u: URL;
    try { u = base ? new URL(ref, base) : new URL(ref); } catch { return true; }
    if (u.protocol === "data:") { if (dataUrlIsRaster(u)) continue; return true; }
    if (u.origin !== "null" && origins.includes(u.origin)) continue;
    return true;
  }
  return false;
}

/** Skip CSS whitespace and comments from `i`; the index after them. */
function skipBlank(s: string, i: number): number {
  for (;;) {
    while (i < s.length && CSS_WS.test(s[i])) i++;
    if (s[i] !== "/" || s[i + 1] !== "*") return i;
    const e = s.indexOf("*/", i + 2);
    i = e < 0 ? s.length : e + 2;
  }
}

/** A `style` attribute's declarations as CSS Syntax splits a declaration list, the value preprocessed first: at a `;` that
 *  is outside a string, a comment, a url token (a bad url included, which runs to its `)` whatever it holds) and any `()`,
 *  `[]` or `{}` block, with escapes read as escapes. Each entry is one declaration's text, judged on its own. The split
 *  matters: read whole, `background-image: url(x"y); mask-image: url(https://host/m.png)` is one bad url and then a string
 *  running to the end, so cssUrls finds only same-origin text in it, while the browser ends the bad url at its `)`, drops
 *  that declaration and fetches the mask. */
function styleDeclarations(style: string): string[] {
  const v = cssPreprocess(style);
  const out: string[] = [];
  const closers: string[] = [];
  let start = 0, i = 0;
  const n = v.length;
  while (i < n) {
    const c = v[i];
    if (c === "/" && v[i + 1] === "*") { const e = v.indexOf("*/", i + 2); i = e < 0 ? n : e + 2; continue; }
    if (c === '"' || c === "'") {
      i++;
      while (i < n && v[i] !== c && v[i] !== "\n") i = v[i] === "\\" ? (v[i + 1] === "\n" ? i + 2 : cssEscape(v, i + 1)[1]) : i + 1;
      if (i < n && v[i] === c) i++;
      continue;
    }
    if (c === "\\" || CSS_NAME.test(c)) {
      let name = "";
      while (i < n && (v[i] === "\\" || CSS_NAME.test(v[i]))) {
        if (v[i] !== "\\") { name += v[i++]; continue; }
        const [ch, j] = cssEscape(v, i + 1); name += ch; i = j;
      }
      if (v[i] !== "(") continue;
      i++;
      if (name.toLowerCase() === "url") {
        let k = i;                                              // after `url(`, whitespace and then a quote make it a function
        while (k < n && CSS_WS.test(v[k])) k++;                 // with a string argument; no comment is read there
        if (v[k] !== '"' && v[k] !== "'") {
          // a url token, or the bad url the browser makes of one with a quote or a paren inside: it runs to the first `)`
          // that is not escaped, whatever it holds
          while (k < n && v[k] !== ")") k = v[k] === "\\" ? cssEscape(v, k + 1)[1] : k + 1;
          i = k < n ? k + 1 : n;
          continue;
        }
      }
      closers.push(")");                                        // a function: its arguments run to its `)`
      continue;
    }
    if (c === "(" || c === "[" || c === "{") { closers.push(c === "(" ? ")" : c === "[" ? "]" : "}"); i++; continue; }
    if (closers.length && c === closers[closers.length - 1]) { closers.pop(); i++; continue; }
    if (c === ";" && !closers.length) { out.push(v.slice(start, i)); start = i + 1; }
    i++;
  }
  out.push(v.slice(start));
  return out;
}

/** A declaration's property name, lower-cased, with its escapes decoded and the comments and whitespace around it skipped,
 *  and its value (the text after the colon); null when the text does not open with a name and a colon, which the browser
 *  drops as an invalid declaration. */
function declaration(text: string): { name: string; value: string } | null {
  let i = skipBlank(text, 0);
  let name = "";
  while (i < text.length && (text[i] === "\\" || CSS_NAME.test(text[i]))) {
    if (text[i] !== "\\") { name += text[i++]; continue; }
    const [ch, j] = cssEscape(text, i + 1); name += ch; i = j;
  }
  i = skipBlank(text, i);
  if (!name || text[i] !== ":") return null;
  return { name: name.toLowerCase(), value: text.slice(i + 1) };
}

/** Remove every url() reference to another origin from `root` and every element under it, the root itself included when it
 *  is an element: each attribute in URL_ATTRS whose value is remoteUrlRef goes; in a `style` attribute each declaration of a
 *  property in URL_PROPERTIES whose value is remoteUrlRef goes, the rest of the attribute is kept as written, and the
 *  attribute goes when nothing is left. A remote reference in any other declaration (a property outside URL_PROPERTIES,
 *  which the browser ignores or, for a custom property, hands to another through var(); or text that opens with no name and
 *  colon) removes the whole attribute, failing closed. `origins` are the page's own; `base` resolves a relative URL ("":
 *  none, so every relative URL is remote). The names are read on EVERY element, HTML ones included: a paint attribute on
 *  an HTML element fetches nothing measured and paints nothing, so removing it costs nothing and the rule stays "these
 *  names", never "these names on these elements". Returns how many removals it made: one per attribute in URL_ATTRS, one
 *  per style declaration, and one for a style attribute removed whole. */
export function dropRemoteRefs(root: ParentNode, origins: readonly string[], base: string): number {
  let removed = 0;
  const rootEl = root as Element;
  const els: Element[] = typeof rootEl.getAttribute === "function" ? [rootEl] : [];
  for (const el of Array.from(root.querySelectorAll("*"))) els.push(el);
  for (const el of els) {
    for (const attr of URL_ATTRS) {
      const v = el.getAttribute(attr);
      if (v != null && remoteUrlRef(v, origins, base)) { el.removeAttribute(attr); removed++; }
    }
    const style = el.getAttribute("style");
    if (style == null) continue;
    const kept: string[] = [];
    let dropped = 0, whole = false;
    for (const text of styleDeclarations(style)) {
      const d = declaration(text);
      if (!remoteUrlRef(d ? d.value : text, origins, base)) { if (text.trim()) kept.push(text.trim()); continue; }
      if (d && URL_PROPERTIES.includes(d.name)) { dropped++; continue; }
      whole = true;
    }
    removed += dropped;
    if (whole) { el.removeAttribute("style"); removed++; }
    else if (dropped && kept.length) el.setAttribute("style", kept.join("; "));
    else if (dropped) el.removeAttribute("style");
  }
  return removed;
}
