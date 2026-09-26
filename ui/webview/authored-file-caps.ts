// The /file URLs an AUTHOR wrote into rendered markdown (a message's image, a notice's picture, a download link), capped
// for this page. The page's own URL builders (preview.ts and file-preview.ts fileUrl) add the cap themselves; a URL typed
// by an author reaches the DOM as written, and without the cap a header-less load of it (an <img>, a <video>, an anchor's
// navigation or download) is refused (file-cap.ts). Every renderer of authored markdown runs this pass on the sanitized DOM
// before the nodes join the page, or states why it need not: the list is derived from the sanitizeMd call sites and pinned
// (authored-file-caps.test.ts).
//
// What the pass reads: every attribute a figure fetches through (figure-gate.ts figureRefs: an img's src and srcset, a
// source's src and srcset, a video's src and poster, an audio's and a track's src, an svg image's href and xlink:href), and
// every anchor's href and xlink:href. What it leaves: an svg's paint references and any CSS url(), which the pass does not
// read (a /file URL there is refused and draws nothing), and every URL that is not this origin's /file or
// /remote/<host>/file route. A URL written with a scheme stays absolute (file-cap.ts withFileCap). With no page key (the
// VS Code webview) nothing changes. The surfaces that turn typed text into links outside the markdown renderers (a todo's
// or a note's URL, a todo's link chip, a code span holding one URL) cap as they mint each anchor, through withFileCap
// (url-links.ts, render.ts); the census of every site that creates an anchor holds them (authored-file-caps.test.ts).
import { figureRefs, parseSrcset, serializeSrcset } from "./figure-gate";
import { XLINK_NS } from "./md-links";
import { withFileCap, hasPageKey } from "./file-cap";

/** Cap every authored /file URL under `root` in place; returns how many attributes it rewrote. A page with no key has no
 *  cap to add, so the walk is skipped. */
export function capAuthoredFileUrls(root: ParentNode): number {
  if (!hasPageKey()) return 0;
  let n = 0;
  for (const ref of figureRefs(root)) {
    if (ref.attr === "srcset") {
      const cands = parseSrcset(ref.value);
      let changed = false;
      for (const c of cands) { const v = withFileCap(c.url); if (v !== c.url) { c.url = v; changed = true; } }
      if (changed) { ref.el.setAttribute("srcset", serializeSrcset(cands)); n++; }
      continue;
    }
    const v = withFileCap(ref.value);
    if (v === ref.value) continue;
    if (ref.attr === "xlink:href") ref.el.setAttributeNS(XLINK_NS, "xlink:href", v);
    else ref.el.setAttribute(ref.attr, v);
    n++;
  }
  root.querySelectorAll("a").forEach((a) => {
    const href = a.getAttribute("href");
    if (href) { const v = withFileCap(href); if (v !== href) { a.setAttribute("href", v); n++; } }
    const xh = a.getAttributeNS(XLINK_NS, "href");
    if (xh) { const v = withFileCap(xh); if (v !== xh) { a.setAttributeNS(XLINK_NS, "xlink:href", v); n++; } }
  });
  return n;
}
