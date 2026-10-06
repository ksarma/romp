// Where an on-demand chunk is fetched from: the page's own bundle script with the chunk's file name in place of the
// bundle's, the directory and the query kept. The query is the kernel's ?v=<dist token>, so a rebuild moves the chunk's URL
// with the bundle's; the directory is the kernel's /dist/ or, in the VS Code webview, the extension's dist resource root;
// and the nonce is copied from the bundle tag, because the webview's Content-Security-Policy allows a script only by nonce
// (extension.ts buildHtml: `script-src 'nonce-N'`), so a chunk tag without it is never requested.
//
// The bundle tag is document.currentScript read while this module initialises, which is while the bundle's classic script
// runs, so it names the right tag whatever the bundle is called. A bundle that did not run from a tag with a src (a test that
// inlines its bundle) falls back to the first script whose path ends in one of the bundles that carry the math grammar
// (BUNDLE_SRC), and with neither there is no URL: the caller fails loudly rather than guess.
//
// math.ts loads the KaTeX chunk (math-chunk.ts) through this. The editor and PDF loaders in file-view.ts keep their own
// derivation for now.

const OWN: HTMLScriptElement | null = typeof document !== "undefined" ? (document.currentScript as HTMLScriptElement | null) : null;

/** A src whose path ends in one of the bundles that import the math grammar (md-config.ts): the fallback's match. Those bundles
 *  are derived from the build in math-lazy.test.ts, which fails when one of them is missing here. */
export const BUNDLE_SRC = /\/(?:render|feed|files|waiting|artifacts)\.js(?=[?#]|$)/;

/** `bundleSrc` with its file name replaced by `chunk`, its directory and its query or fragment kept; null when the path does not
 *  end in a .js file name. */
export function chunkSrcFor(bundleSrc: string, chunk: string): string | null {
  const m = /^([^?#]*\/)[^/?#]+\.js((?:[?#].*)?)$/.exec(bundleSrc);
  return m ? m[1] + chunk + m[2] : null;
}

/** The src and nonce a script tag for `chunk` takes on this page, or null when no bundle tag can be found to derive them from.
 *  `own` is the tag the bundle ran from (document.currentScript at load) and `doc` the page; both are parameters for the tests. */
export function chunkScript(chunk: string, own: HTMLScriptElement | null = OWN, doc: Document | null = typeof document !== "undefined" ? document : null): { src: string; nonce: string } | null {
  let tag: HTMLScriptElement | null = own && own.src ? own : null;
  if (!tag && doc) tag = (Array.from(doc.querySelectorAll("script[src]")) as HTMLScriptElement[]).find((s) => BUNDLE_SRC.test(s.src)) || null;
  if (!tag) return null;
  const src = chunkSrcFor(tag.src, chunk);
  return src ? { src, nonce: tag.nonce || "" } : null;
}
