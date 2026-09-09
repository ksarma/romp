// Figures from the web in a viewed file (plans/markdown-viewer.md, decision 8; ruling 2026-09-07): a picture or a
// clip whose source is on an allowed host loads when the file opens; one on any other host shows a placeholder
// that names the host and loads the figure on one click, and a host loaded that way stays loaded for the page.
// Before this every remote `<img src>` fetched the moment a file rendered (a tracking pixel fires, with no click
// and no gate), and so did the sources decision 8's first sketch never named: an `<img srcset>` candidate (the
// browser picks it over a local `src` and never fetches the file the comments poll watches), a `<video poster>`,
// a `<picture><source srcset>`, an `<svg><image href>` and a filter's `<feImage>` (measured 2026-09-08 over the
// real bundles; the Slice 1 note listed them for this slice).
//
// The allowed hosts are the gear's `figureHosts` setting (settings.ts: github.com and its image hosts, localhost
// and 127.0.0.1 by default), plus the page's own origin and the kernel's (the /file route and its /remote relay,
// which every local figure goes through: rewriteFigureSrcs in file-view.ts), plus the hosts the person loaded in
// this document (`loadedHosts`, per document: the chat webview, the feed, the Files pane and each browser tab each
// remember their own, and a reload or a Rendered/Raw round trip keeps a loaded figure loaded because every paint
// reads the set). The URL kind adds the document's own host (file-view.ts mdBlock). The chat's own markdown
// (render.ts md()) is not gated, as the plan scopes the ruling to the viewer.
//
// The gate runs on the SANITIZED DOM, after rewriteFigureSrcs, never on marked's HTML: it wraps the media element
// (an img, a video, an audio, a picture or an inline svg; a `<source>` or a `<track>` is gated through its parent)
// in a `span.fv-gate` placeholder and moves every attribute that fetches (`src`, `srcset`, `poster`, an SVG image's
// `href`) to `data-fv-gated-<name>`, so nothing leaves the page while gated and the element itself is kept, as the
// comments panel's regions layer expects (it wraps THE img). `data-fv-src` moves aside too: the attribute means
// "this viewer rewrote this src to /file", and while gated there is no src to pair an embed with. A data-*
// attribute set here is fine: the sanitizer's ALLOW_DATA_ATTR: false applies during DOMPurify only, and the
// viewer already writes `data-fv-src` the same way. The click is delegated on the viewer's body (file-view.ts,
// `data-act="fv-load"`), never bound to the placeholder, since every paint rebuilds the DOM (ui/CLAUDE.md); it
// restores every gated element of that host in the document and adds the host to the set. The placeholder's text
// is the viewer's, not the file's: the anchor map skips it as a control (anchor-map.ts isControl), so a paragraph
// holding a gated picture still pairs with its source.
import { XLINK_NS } from "./md-links";
import { loadSettings, onExternalSettingsChange } from "./settings";

export const GATE_CLASS = "fv-gate";
export const GATE_LABEL_CLASS = "fv-gate-label";
/** The delegated action on the placeholder (file-view.ts's body listeners read it). */
export const GATE_ACT = "fv-load";
const GATED_PREFIX = "data-fv-gated-";

// ── the attributes a figure fetches ──────────────────────────────────────────────────────────────────
/** One attribute under a root that names something the browser fetches for a picture or a clip. `attr` is the
 *  attribute's own name (`xlink:href` for SVG 1.1's spelling, read through the XLink namespace). */
export type FigureRef = { el: Element; attr: "src" | "srcset" | "poster" | "href" | "xlink:href"; value: string };
/** The elements that fetch, by tag, and what they fetch through. `image` and `feImage` are SVG's (an inline svg's
 *  picture, and a filter's), matched by their own case since a type selector is case-sensitive for a non-HTML element. */
export const FIGURE_SEL = "img, source, video, audio, track, image, feImage";
const FETCH_ATTRS: Record<string, Array<FigureRef["attr"]>> = {
  img: ["src", "srcset"], source: ["src", "srcset"], video: ["src", "poster"], audio: ["src"], track: ["src"],
  image: ["href", "xlink:href"], feimage: ["href", "xlink:href"],
};
const tagOf = (el: Element): string => el.tagName.toLowerCase();
/** Every fetching attribute under `root` (the root itself included when it is such an element), in document order. */
export function figureRefs(root: ParentNode): FigureRef[] {
  const out: FigureRef[] = [];
  const nodes: Element[] = [];
  const self = root as Element;
  if (typeof self.tagName === "string" && FETCH_ATTRS[tagOf(self)]) nodes.push(self);
  root.querySelectorAll(FIGURE_SEL).forEach((el) => { nodes.push(el); });
  for (const el of nodes) {
    for (const attr of FETCH_ATTRS[tagOf(el)] || []) {
      const value = attr === "xlink:href" ? el.getAttributeNS(XLINK_NS, "href") : el.getAttribute(attr);
      if (value) out.push({ el, attr, value });
    }
  }
  return out;
}

// ── srcset ──────────────────────────────────────────────────────────────────────────────────────────
export type SrcsetCandidate = { url: string; descriptor: string };
/** The candidates of a `srcset` attribute, by HTML's own parse: a URL runs to whitespace, a comma glued to its end
 *  ends the candidate, else the descriptors run to the next top-level comma (a parenthesised descriptor keeps its
 *  commas). A comma inside a URL therefore survives (`a,b.png 1x`), which a split on commas would cut. */
export function parseSrcset(s: string): SrcsetCandidate[] {
  const out: SrcsetCandidate[] = [];
  let i = 0;
  const n = s.length;
  while (i < n) {
    while (i < n && /[\s,]/.test(s[i])) i++;
    if (i >= n) break;
    let j = i;
    while (j < n && !/\s/.test(s[j])) j++;
    let url = s.slice(i, j);
    i = j;
    let descriptor = "";
    if (/,$/.test(url)) url = url.replace(/,+$/, "");
    else {
      let k = i, depth = 0;
      while (k < n) {
        const c = s[k];
        if (c === "(") depth++;
        else if (c === ")") depth--;
        else if (c === "," && depth <= 0) break;
        k++;
      }
      descriptor = s.slice(i, k).trim();
      i = k + 1;
    }
    if (url) out.push({ url, descriptor });
  }
  return out;
}
export function serializeSrcset(cands: SrcsetCandidate[]): string {
  return cands.map((c) => c.url + (c.descriptor ? " " + c.descriptor : "")).join(", ");
}
/** The URLs one fetching attribute names: a srcset's candidates, else the value itself. */
export function refUrls(ref: FigureRef): string[] {
  return ref.attr === "srcset" ? parseSrcset(ref.value).map((c) => c.url) : [ref.value];
}

// ── which host a source fetches from ──────────────────────────────────────────────────────────────
/** The host a source would fetch from when it is not this page's own, else null: `data:` and `blob:` leave the page
 *  for nothing; a relative or same-origin URL (the kernel's /file route and its /remote relay) is the page's own; the
 *  kernel's base when the page is a webview that reaches it by an absolute URL (`window.__rompKernelBase`) is the
 *  kernel's own. Only http and https count as another host: no other scheme the sanitizer keeps fetches a figure. A
 *  URL the parser refuses is nobody's host, and left alone. */
export function remoteHost(value: string, base: string): string | null {
  let u: URL;
  try { u = new URL(value, base); } catch { return null; }
  if (u.protocol !== "http:" && u.protocol !== "https:") return null;
  const own = originOf(base);
  if (own && u.origin === own) return null;
  const kernel = typeof window !== "undefined" ? originOf(String((window as unknown as { __rompKernelBase?: unknown }).__rompKernelBase || "")) : null;
  if (kernel && u.origin === kernel) return null;
  return u.hostname.toLowerCase();
}
function originOf(href: string): string | null {
  if (!href) return null;
  try { const o = new URL(href).origin; return o === "null" ? null : o; } catch { return null; }
}

// ── the allowed set ────────────────────────────────────────────────────────────────────────────────
const loadedHosts = new Set<string>();   // hosts the person loaded in this document (the ruling: for the session)
/** The hosts whose figures load without a click: the setting's, the ones loaded in this document, and `extra` (the
 *  URL kind's own host). Lower-cased; the gate compares host names as the URL parser gives them. */
export function allowedFigureHosts(extra: Iterable<string> = []): Set<string> {
  const s = new Set<string>();
  for (const h of loadSettings().figureHosts) s.add(h.toLowerCase());
  for (const h of loadedHosts) s.add(h);
  for (const h of extra) if (h) s.add(h.toLowerCase());
  return s;
}
/** For tests: the document's loaded hosts, cleared. */
export function forgetLoadedHosts(): void { loadedHosts.clear(); }

/** The hosts, in order of first appearance, that `el` (a media root) would fetch from and `allowed` does not list. */
export function unlistedHosts(el: Element, base: string, allowed: Set<string>): string[] {
  const out: string[] = [];
  for (const ref of figureRefs(el)) {
    for (const url of refUrls(ref)) {
      const h = remoteHost(url, base);
      if (h && !allowed.has(h) && !out.includes(h)) out.push(h);
    }
  }
  return out;
}

// ── the gate ────────────────────────────────────────────────────────────────────────────────────────
/** The media roots under `root` the gate judges one by one: an img, video, audio, picture or svg that is not inside
 *  another (an img inside a picture is the picture's; a `<source>` or `<track>` is its parent's; an svg inside an svg
 *  is the outer one's). */
export function gateRoots(root: ParentNode): Element[] {
  const out: Element[] = [];
  root.querySelectorAll("img, video, audio, picture, svg").forEach((el) => {
    const parent = el.parentElement;
    if (parent && typeof parent.closest === "function" && parent.closest("picture, svg, video, audio")) return;
    out.push(el);
  });
  return out;
}
const isImg = (el: Element): boolean => tagOf(el) === "img";
/** The kind word the placeholder uses for the element. */
function kindOf(el: Element): string {
  const t = tagOf(el);
  return t === "video" ? "Video" : t === "audio" ? "Audio" : "Image";
}
/** An HTML dimension attribute as a pixel length (HTML's dimension rule: digits, an optional fraction; a `%` makes it a
 *  percentage, 0 here), the test file-view.ts's keepVideoShape applies. */
function pxAttr(el: Element, name: string): number {
  const m = /^[ \t\n\f\r]*(\d+(?:\.\d*)?)(%?)/.exec(el.getAttribute(name) || "");
  return m && !m[2] ? Number(m[1]) : 0;
}
function labelGate(wrap: HTMLElement, hosts: string[]): void {
  const host = hosts[0];
  wrap.setAttribute("data-fv-host", host);
  wrap.setAttribute("title", "Load from " + host);
  const label = wrap.querySelector("." + GATE_LABEL_CLASS) as HTMLElement | null;
  const media = wrap.firstElementChild;
  const more = hosts.length - 1;
  if (label) label.textContent = (media ? kindOf(media) : "Image") + " from " + host + (more > 0 ? " and " + more + " more host" + (more > 1 ? "s" : "") : "") + ". Click to load.";
}
/** Wrap one media root in the placeholder, its fetching attributes moved aside. */
function gate(el: Element, hosts: string[]): void {
  const doc = el.ownerDocument;
  const nodes: Element[] = [el];
  el.querySelectorAll("*").forEach((n) => { nodes.push(n); });
  for (const ref of figureRefs(el)) {
    if (ref.attr === "xlink:href") { ref.el.removeAttributeNS(XLINK_NS, "href"); ref.el.setAttribute(GATED_PREFIX + "href", ref.value); }
    else { ref.el.removeAttribute(ref.attr); ref.el.setAttribute(GATED_PREFIX + ref.attr, ref.value); }
  }
  for (const n of nodes) {
    const kept = n.getAttribute("data-fv-src");
    if (kept !== null) { n.removeAttribute("data-fv-src"); n.setAttribute(GATED_PREFIX + "fv-src", kept); }
  }
  const wrap = doc.createElement("span");
  wrap.className = GATE_CLASS;
  wrap.setAttribute("data-act", GATE_ACT);
  wrap.setAttribute("role", "button");
  wrap.setAttribute("tabindex", "0");
  wrap.setAttribute("data-fv-hosts", hosts.join(" "));
  // the author's size, when the attributes give one in pixels, so the page keeps its shape while the figure waits
  const w = pxAttr(el, "width"), h = pxAttr(el, "height");
  if (w > 0) wrap.style.width = w + "px";
  if (w > 0 && h > 0) wrap.style.aspectRatio = w + " / " + h;
  else if (h > 0) wrap.style.height = h + "px";
  const parent = el.parentNode;
  if (parent) parent.insertBefore(wrap, el);
  wrap.appendChild(el);
  const label = doc.createElement("span");
  label.className = GATE_LABEL_CLASS;
  wrap.appendChild(label);
  labelGate(wrap, hosts);
}
/** Undo one placeholder: every moved attribute back under its name, the media element back in the placeholder's place. */
function restore(wrap: Element): void {
  const el = wrap.firstElementChild;
  if (!el) { wrap.remove(); return; }
  const nodes: Element[] = [el];
  el.querySelectorAll("*").forEach((n) => { nodes.push(n); });
  for (const n of nodes) {
    for (const a of Array.from(n.attributes)) {
      if (!a.name.startsWith(GATED_PREFIX)) continue;
      const name = a.name.slice(GATED_PREFIX.length);
      n.setAttribute(name === "fv-src" ? "data-fv-src" : name, a.value);
      n.removeAttribute(a.name);
    }
  }
  wrap.replaceWith(el);
}

let synced = false;
/** Gate every media root under `root` whose sources name a host outside the allowed set (allowedFigureHosts plus
 *  `extra`); `base` resolves relative sources (the document's baseURI). Installs, once, the settings listener that
 *  re-judges the document's placeholders when the gear's list changes in this or another tab. */
export function gateRemoteFigures(root: ParentNode, base: string, extra: Iterable<string> = []): void {
  const allowed = allowedFigureHosts(extra);
  for (const el of gateRoots(root)) {
    const hosts = unlistedHosts(el, base, allowed);
    if (hosts.length) gate(el, hosts);
  }
  if (!synced) {
    synced = true;
    onExternalSettingsChange(() => { if (typeof document !== "undefined") regateFigures(document); });
  }
}
/** Re-judge every placeholder in `doc` against the allowed set now: a placeholder whose hosts are all allowed is
 *  restored, one still waiting on another host is relabelled with it. A host that was allowed at gate time never
 *  appears in a placeholder's list, so the URL kind's own host needs no repeating here. */
export function regateFigures(doc: ParentNode): void {
  const allowed = allowedFigureHosts();
  Array.from(doc.querySelectorAll("." + GATE_CLASS)).forEach((wrap) => {
    const hosts = (wrap.getAttribute("data-fv-hosts") || "").split(" ").filter((h) => h && !allowed.has(h));
    if (!hosts.length) restore(wrap);
    else if (hosts[0] !== wrap.getAttribute("data-fv-host")) labelGate(wrap as HTMLElement, hosts);
  });
}
/** The click: the host joins the document's loaded set and every placeholder waiting on it (alone) is restored. */
export function loadGatedHost(host: string, doc: ParentNode = document): void {
  if (!host) return;
  loadedHosts.add(host.toLowerCase());
  regateFigures(doc);
}
/** The placeholder a click or a key landed in, if any: for the viewer's body listeners. */
export function gateOf(target: EventTarget | null, within: Element): HTMLElement | null {
  const t = target as Element | null;
  const g = t && typeof t.closest === "function" ? t.closest('[data-act="' + GATE_ACT + '"]') as HTMLElement | null : null;
  return g && within.contains(g) ? g : null;
}
