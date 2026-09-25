// The capability a header-less load of /file carries. The browser's login cookie holds a session id that opens the page
// documents and the static bundles and nothing else; a JSON read, a POST or a socket also needs the PAGE KEY, which lives
// in this origin's localStorage and rides as the X-Romp-Key header (the fetch wrapper the kernel puts first in every page)
// or as k= on a socket dial (window.__rompKeyQ). An <img>, a <video>, a PDF iframe, an own-tab open or a download cannot
// carry a header, so its /file URL carries `cap`: an HMAC-SHA256 under the page key over the one (host, path, sid) the URL
// names, which the kernel recomputes from the cookie's session (kernel.py _file_cap). A cap opens that one file, and only
// together with the session cookie; nothing about the key can be read back out of it.
//
// Synchronous on purpose: fileUrl feeds DOM builders that set src in the same tick, and crypto.subtle is asynchronous and
// absent outside secure contexts (a dashboard over plain http on a tailnet address). So SHA-256 and HMAC are written out
// here, pinned against node's own crypto and, through tests/fixtures/file-cap-vectors.json and the kernel's code run at
// test time, to the kernel's derivation (file-cap.test.ts; tests/test_file_cap_binding.py reads the same vector file).
//
// No key means no cap, and the URL is exactly what it was: the VS Code webview (which authenticates its kernel requests
// with ?token= and holds no page key) and a page before its first sign-in build the URLs they always built.

const K256 = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

/** SHA-256 (FIPS 180-4) of a byte string. */
export function sha256(msg: Uint8Array): Uint8Array {
  const len = msg.length, padded = ((len + 9 + 63) >> 6) << 6;
  const m = new Uint8Array(padded);
  m.set(msg);
  m[len] = 0x80;
  const dv = new DataView(m.buffer);
  dv.setUint32(padded - 8, Math.floor(len / 0x20000000));   // the bit length's high word
  dv.setUint32(padded - 4, (len << 3) >>> 0);                 // and its low word
  const h = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
  const w = new Uint32Array(64);
  const ror = (x: number, n: number) => (x >>> n) | (x << (32 - n));
  for (let off = 0; off < padded; off += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(off + 4 * i);
    for (let i = 16; i < 64; i++) {
      const a = w[i - 15], b = w[i - 2];
      w[i] = w[i - 16] + (ror(a, 7) ^ ror(a, 18) ^ (a >>> 3)) + w[i - 7] + (ror(b, 17) ^ ror(b, 19) ^ (b >>> 10));
    }
    let a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], k = h[7];
    for (let i = 0; i < 64; i++) {
      const t1 = (k + (ror(e, 6) ^ ror(e, 11) ^ ror(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i]) | 0;
      const t2 = ((ror(a, 2) ^ ror(a, 13) ^ ror(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) | 0;
      k = g; g = f; f = e; e = (d + t1) | 0; d = c; c = b; b = a; a = (t1 + t2) | 0;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += k;
  }
  const out = new Uint8Array(32);
  const ov = new DataView(out.buffer);
  for (let i = 0; i < 8; i++) ov.setUint32(4 * i, h[i]);
  return out;
}

/** HMAC-SHA256 (RFC 2104) of `msg` under `key`. */
export function hmacSha256(key: Uint8Array, msg: Uint8Array): Uint8Array {
  const k = new Uint8Array(64);
  k.set(key.length > 64 ? sha256(key) : key);
  const inner = new Uint8Array(64 + msg.length), outer = new Uint8Array(64 + 32);
  for (let i = 0; i < 64; i++) { inner[i] = k[i] ^ 0x36; outer[i] = k[i] ^ 0x5c; }
  inner.set(msg, 64);
  outer.set(sha256(inner), 64);
  return sha256(outer);
}

function b64url(bytes: Uint8Array): string {
  let s = "";
  for (let i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

const enc = new TextEncoder();

/** The cap's fixed label: the domain the cap's MAC lives in, distinct from the session id's and the page key's. */
export const FILE_CAP_LABEL = "romp-file-cap\0";

/** The cap's MAC message: the label, then for each of host, path and sid its UTF-8 byte length in decimal, a NUL, and its
 *  bytes. Length-prefixed, so the map from a triple to bytes is one to one: a separator moved into a field, a byte shifted
 *  across a boundary, or a NUL inside a value all change a declared length. The kernel's _cap_input builds the same bytes. */
export function capInput(host: string, path: string, sid: string): Uint8Array {
  const parts: Uint8Array[] = [enc.encode(FILE_CAP_LABEL)];
  for (const f of [host, path, sid]) {
    const b = enc.encode(f);
    parts.push(enc.encode(b.length + "\0"), b);
  }
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}

/** The cap for (host, path, sid) under `key`: the first 16 bytes of HMAC-SHA256(key, capInput(...)), base64url without
 *  padding. Pure; fileCap below supplies the page's key. */
export function capFor(key: string, host: string, path: string, sid: string): string {
  return b64url(hmacSha256(enc.encode(key), capInput(host, path, sid)).subarray(0, 16));
}

/** The page key the kernel handed this origin at sign-in, read through window.__rompPageKey (installed by the kernel's
 *  page-key script, which reads this kernel's own storage slot); "" when there is none. */
function pageKey(): string {
  try { const f = (window as any).__rompPageKey; return typeof f === "function" ? String(f() || "") : ""; } catch { return ""; }
}

/** Whether this page holds a page key: a page without one (the VS Code webview, a page before sign-in) caps nothing. */
export function hasPageKey(): boolean {
  return pageKey() !== "";
}

let memoKey = "";
const memo = new Map<string, string>();

/** The `cap` for one /file URL: `host` is the attached host a /remote/<host>/file URL names ("" for the local /file),
 *  `path` and `sid` exactly the values the URL's query carries (what the kernel's parse_qs reads back). "" when this page
 *  holds no key. Memoized per key, by the triple itself (a JSON array, one entry per distinct triple). */
export function fileCap(host: string, path: string, sid: string): string {
  const key = pageKey();
  if (!key) return "";
  if (key !== memoKey) { memo.clear(); memoKey = key; }
  const id = JSON.stringify([host, path, sid]);
  let cap = memo.get(id);
  if (cap === undefined) {
    cap = capFor(key, host, path, sid);
    if (memo.size > 4096) memo.clear();
    memo.set(id, cap);
  }
  return cap;
}

/** The first non-empty value of a query parameter: the value the kernel reads, since its parse_qs drops a blank pair
 *  (`path=`) and the kernel takes the first value left. */
function kernelParam(q: URLSearchParams, name: string): string {
  for (const v of q.getAll(name)) if (v !== "") return v;
  return "";
}

/** A kernel /file URL as someone wrote it (a markdown image, a download link, an address typed into a todo or a code
 *  span), with this page's cap for the host, path and sid it names. An absolute URL comes back absolute and a
 *  root-relative one root-relative, so a caller that sorts links by whether they carry a scheme sorts the capped URL
 *  as it sorted the written one. Any other URL (another origin, another route, a malformed host escape), or a page with
 *  no key, comes back unchanged. The bytes such a URL fetches stay in this browser (an element, or the user's own
 *  downloads). */
export function withFileCap(url: string): string {
  try {
    const u = new URL(url, location.href);
    if (u.origin !== location.origin) return url;
    let host = "";
    if (u.pathname !== "/file") {
      const m = /^\/remote\/([^/]+)\/file$/.exec(u.pathname);
      if (!m) return url;
      host = decodeURIComponent(m[1]);
    }
    const cap = fileCap(host, kernelParam(u.searchParams, "path"), kernelParam(u.searchParams, "sid"));
    if (!cap) return url;
    u.searchParams.set("cap", cap);
    return /^\s*(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(url) ? u.href : u.pathname + u.search + u.hash;
  } catch { return url; }
}
