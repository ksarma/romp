// The per-file cap a header-less /file load carries (file-cap.ts), against the kernel's own derivation.
//
// The page computes the cap synchronously (fileUrl sets src in the same tick; crypto.subtle is asynchronous and absent
// outside secure contexts), so SHA-256 and HMAC-SHA256 are written out in file-cap.ts. Pinned here five ways:
//   1. SHA-256 and HMAC-SHA256 against node's own crypto (OpenSSL) over every message length from 0 to 300 bytes and keys
//      shorter than, equal to and longer than a block, plus the FIPS 180-4 "abc" digest;
//   2. the cap against tests/fixtures/file-cap-vectors.json, the frozen cross-language vectors the kernel's test also
//      reads (tests/test_file_cap_binding.py), so the two sides share one constant;
//   3. the cap against the KERNEL'S OWN CODE, run at test time: _FILE_CAP_LABEL, _hmac_b64 and _cap_input are read out of
//      kernel/kernel.py by name and executed by python3 over a battery of fixed triples (empty fields, NUL bytes inside a
//      field, digits that look like a length prefix, non-ASCII, an astral character, a 4 KB path) and seeded random ones;
//      and every URL the page builds (fileUrl, local and remote) or caps (withFileCap, over authored spellings) is read
//      back as the kernel reads a request: its _need for the host, parse_qs for path, sid and cap. The cap the page put in
//      the URL must be the cap the kernel computes for it;
//   4. the placement: with no page key no cap and the URL exactly as before (the VS Code webview), with a key the cap
//      appended, and withFileCap leaving every URL that is not this origin's /file or /remote/<host>/file unchanged;
//   5. the key's source: the page reads it only through window.__rompPageKey, which reads the kernel's own storage slot
//      (keyed by its cookie name), and no page module names a slot of its own.
// Synthetic values only: every key is minted at run time; placeholder uuids; host TESTHOST.
import { test } from "node:test";
import assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createHash, createHmac, randomBytes } from "node:crypto";
import { spawnSync } from "node:child_process";
import { sha256, hmacSha256, capInput, capFor, fileCap, withFileCap, FILE_CAP_LABEL } from "./file-cap";
import { fileUrl as previewFileUrl } from "./preview";
import { fileUrl as cardFileUrl } from "./file-preview";

const ROOT = path.resolve(process.cwd(), "..");                      // npm test runs in vscode-extension
const KERNEL = fs.readFileSync(path.join(ROOT, "kernel", "kernel.py"), "utf8");
const VECTORS = JSON.parse(fs.readFileSync(path.join(ROOT, "tests", "fixtures", "file-cap-vectors.json"), "utf8"));
const SID = "11111111-2222-3333-4444-555555555555";
const hex = (b: Uint8Array): string => Buffer.from(b).toString("hex");
const b64url = (b: Buffer): string => b.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const newKey = (): string => b64url(randomBytes(32));               // the shape of a page key, minted per test

/** Run `fn` with a page that holds `key` (window.__rompPageKey, as the kernel's page-key script installs it) at
 *  http://romp.test/chat; "" means a page with no key. */
function withPage<T>(key: string, fn: () => T): T {
  const g: any = globalThis;
  const saved = { window: g.window, location: g.location, hadW: "window" in g, hadL: "location" in g };
  g.window = key ? { __rompPageKey: () => key } : {};
  g.location = { href: "http://romp.test/chat", origin: "http://romp.test", protocol: "http:", host: "romp.test" };
  try { return fn(); }
  finally {
    if (saved.hadW) g.window = saved.window; else delete g.window;
    if (saved.hadL) g.location = saved.location; else delete g.location;
  }
}

// ── 1. the primitives against node's crypto ─────────────────────────────────────────────────────────────
test("SHA-256 matches node's crypto for every length 0..300 and the FIPS 180-4 abc digest", () => {
  const abc = hex(sha256(new TextEncoder().encode("abc")));
  assert.equal(abc, createHash("sha256").update("abc").digest("hex"));
  assert.equal(abc.slice(0, 16), "ba7816bf8f01cfea", "the FIPS 180-4 example's digest");
  for (let n = 0; n <= 300; n++) {
    const m = randomBytes(n);
    assert.equal(hex(sha256(m)), createHash("sha256").update(m).digest("hex"), "length " + n);
  }
});

test("HMAC-SHA256 matches node's crypto for keys shorter than, equal to and longer than a block, and messages 0..300", () => {
  for (const kl of [0, 1, 20, 31, 32, 63, 64, 65, 131]) {
    const k = randomBytes(kl);
    for (const n of [0, 1, 50, 55, 56, 63, 64, 65, 119, 120, 300]) {
      const m = randomBytes(n);
      assert.equal(hex(hmacSha256(k, m)), createHmac("sha256", k).update(m).digest("hex"), "key " + kl + ", message " + n);
    }
  }
  // RFC 4231 test case 2's key and message (no key material: the RFC's "Jefe")
  assert.equal(hex(hmacSha256(Buffer.from("Jefe"), Buffer.from("what do ya want for nothing?"))),
               createHmac("sha256", "Jefe").update("what do ya want for nothing?").digest("hex"));
});

// ── 2. the frozen cross-language vectors ────────────────────────────────────────────────────────────────
test("the cap matches every frozen cross-language vector the kernel's test also reads", () => {
  assert.equal(VECTORS.label, FILE_CAP_LABEL, "one label on both sides");
  assert.ok(VECTORS.caps.length >= 5, "the vector file lists its caps");
  for (const v of VECTORS.caps) assert.equal(capFor(VECTORS.key, v.host, v.path, v.sid), v.cap, JSON.stringify([v.host, v.path, v.sid]));
});

test("the MAC input is length-prefixed, so a byte moved across a field boundary makes another input", () => {
  const dec = (b: Uint8Array) => Buffer.from(b).toString("latin1");
  assert.equal(dec(capInput("", "/a", "s")), FILE_CAP_LABEL + "0\0" + "2\0/a" + "1\0s");
  const pairs: [string, string, string][][] = [
    [["a\0", "b", ""], ["a", "\0b", ""]],
    [["", "1\0x", ""], ["1", "x", ""]],
    [["h", "", "s"], ["", "h", "s"]],
    [["", "/p", "q"], ["", "/pq", ""]],
  ];
  const key = newKey();
  for (const [x, y] of pairs) {
    assert.notEqual(hex(capInput(...x)), hex(capInput(...y)), JSON.stringify([x, y]));
    assert.notEqual(capFor(key, ...x), capFor(key, ...y), "two triples a NUL join would merge get two caps: " + JSON.stringify([x, y]));
  }
});

// ── 3. against the kernel's own code, run by python3 ────────────────────────────────────────────────────
const PYTHON = spawnSync("python3", ["-c", "import sys; sys.exit(0)"]).status === 0;

/** The source of a top-level `def NAME` in kernel.py, up to the next line at column 0; or a method `def NAME` at four
 *  spaces, up to the next line at four spaces or less (dedented). Loud when the name is not found. */
function kernelDef(name: string, indent = ""): string {
  const lines = KERNEL.split("\n");
  const at = lines.findIndex((l) => l.startsWith(indent + "def " + name + "("));
  assert.ok(at >= 0, "kernel.py defines " + name);
  let end = at + 1;
  const stop = (l: string) => l.trim() !== "" && (l.length - l.trimStart().length) <= indent.length && !l.trimStart().startsWith("#");
  while (end < lines.length && !stop(lines[end])) end++;
  return lines.slice(at, end).map((l) => l.slice(indent.length)).join("\n");
}
function kernelAssign(name: string): string {
  const m = new RegExp("^" + name + " = .*$", "m").exec(KERNEL);
  assert.ok(m, "kernel.py assigns " + name);
  return m![0];
}

const PY_DRIVER = [
  "import sys, json, hmac, hashlib, base64",
  "from urllib.parse import urlparse, parse_qs, unquote",
  "src = json.loads(sys.stdin.read())",
  "ns = {'hmac': hmac, 'hashlib': hashlib, 'base64': base64, 'unquote': unquote,",
  "      '_PAGE_RENDERERS': {}, '_static_route': lambda p: False}",
  "for block in src['code']:",
  "    exec(block, ns)",
  "cap = lambda k, h, p, s: ns['_hmac_b64'](k, ns['_cap_input'](h, p, s), 16)",
  "out = {'inputs': [ns['_cap_input'](h, p, s).encode('utf-8').hex() for h, p, s in src['triples']],",
  "       'caps': [cap(src['key'], h, p, s) for h, p, s in src['triples']], 'urls': []}",
  "for url in src['urls']:",
  "    u = urlparse(url)",
  "    q = parse_qs(u.query)",                                    // do_GET: q = parse_qs(u.query)
  "    need, fhost = ns['_need'](u.path)",
  "    got = (q.get('cap') or [''])[0]",
  "    want = cap(src['key'], fhost, (q.get('path') or [''])[0], (q.get('sid') or [''])[0]) if need == 'file' else ''",
  "    out['urls'].append([need, got == want and got != ''])",
  "sys.stdout.write(json.dumps(out))",
].join("\n");

/** The kernel's reading of the triples and URLs under `key`, by the kernel's own derivation code. */
function kernelReads(key: string, triples: [string, string, string][], urls: string[]): { inputs: string[]; caps: string[]; urls: [string, boolean][] } {
  const code = [kernelAssign("_FILE_CAP_LABEL"), kernelDef("_hmac_b64"), kernelDef("_cap_input"), kernelDef("_need", "    ").replace(/^@staticmethod\n/, "")];
  const r = spawnSync("python3", ["-c", PY_DRIVER], { input: JSON.stringify({ code, key, triples, urls }), encoding: "utf8", timeout: 60000, maxBuffer: 64 * 1024 * 1024 });
  assert.equal(r.status, 0, r.stderr);
  return JSON.parse(r.stdout);
}

test("at source: the kernel reads the cap, path and sid as the parity driver does (first value, parse_qs) and do_GET parses the query with parse_qs", () => {
  assert.match(KERNEL, /_ct_eq\(\(q\.get\("cap"\) or \[""\]\)\[0\], _file_cap\(\s*sess, fhost, \(q\.get\("path"\) or \[""\]\)\[0\], \(q\.get\("sid"\) or \[""\]\)\[0\]\)\)/,
               "_authorize compares the first cap against _file_cap over the first path and sid, the reads PY_DRIVER mirrors");
  assert.match(KERNEL, /need, fhost = self\._need\(urlparse\(getattr\(self, "path", ""\) or ""\)\.path\)/, "_authorize classes the request path through _need, which PY_DRIVER runs");
  assert.match(KERNEL, /def do_GET\(self\):\n(?:.*\n){0,6}?\s+q = parse_qs\(u\.query\)/, "do_GET parses the query with parse_qs's defaults");
});

function battery(): [string, string, string][] {
  const out: [string, string, string][] = [
    ["", "", ""], ["", "/tmp/plot.png", SID], ["TESTHOST", "/srv/notes-api/figs/a.png", SID], ["", "plots/figure.png", ""],
    ["", "a\0b", SID], ["h\0", "/p", ""], ["", "3\0abc", "1\0"], ["", "12", "345"],
    ["hôte", "/tmp/файл.png", SID], ["", "/tmp/rapport-français.pdf", SID], ["", "/tmp/\u{1F600} face.png", SID],
    ["", "/tmp/" + "x".repeat(4096) + ".png", SID], ["", "a+b c%2B&=?#.png", SID], ["", "/a/./b/../c//d/", SID],
  ];
  let seed = 0x9e3779b9;                                            // a seeded generator, so a failure reproduces
  const rnd = (n: number) => { seed = (Math.imul(seed ^ (seed >>> 15), 0x2c1b3c6d) + 0x6d2b79f5) >>> 0; return seed % n; };
  const alphabet = ["a", "Z", "0", "9", "/", ".", " ", "+", "%", "&", "=", "?", "#", "\0", "\n", "é", "ж", "絵", "\u{1F600}", ":", "-", "_"];
  const field = () => Array.from({ length: rnd(24) }, () => alphabet[rnd(alphabet.length)]).join("");
  for (let i = 0; i < 200; i++) out.push([rnd(3) ? "" : field(), field(), rnd(2) ? SID : field()]);
  return out;
}

test("the kernel's own _cap_input and _hmac_b64, run by python3, give the same bytes and the same cap for every triple", { skip: PYTHON ? false : "python3 not installed on this machine" }, () => {
  const key = newKey();
  const triples = battery();
  const got = kernelReads(key, triples, []);
  assert.equal(got.caps.length, triples.length);
  for (let i = 0; i < triples.length; i++) {
    const label = JSON.stringify(triples[i]).slice(0, 120);
    assert.equal(hex(capInput(...triples[i])), got.inputs[i], "the MAC input's bytes: " + label);
    assert.equal(capFor(key, ...triples[i]), got.caps[i], "the cap: " + label);
  }
});

test("every URL fileUrl builds, local and remote, carries the cap the kernel computes for the request it makes", { skip: PYTHON ? false : "python3 not installed on this machine" }, () => {
  const key = newKey();
  const cases: [string, string | null][] = [];
  for (const [h, p, s] of battery().slice(0, 60)) {
    if (/[\ud800-\udfff]/.test(p)) continue;                          // encodeURIComponent throws on a lone surrogate, before and after
    cases.push([p, s ? (h && !h.includes(":") && !h.includes("\0") ? h + ":" + s : s) : null]);
  }
  const urls = withPage(key, () => cases.flatMap(([p, s]) => [previewFileUrl(p, s), cardFileUrl(p, s)]));
  const read = kernelReads(key, [], urls);
  read.urls.forEach(([need, ok], i) => {
    assert.equal(need, "file", "the kernel classes the URL as the file class: " + urls[i].slice(0, 120));
    assert.ok(ok, "the kernel reads a valid cap in: " + urls[i].slice(0, 160));
  });
});

test("withFileCap puts in every authored spelling of a /file URL the cap the kernel computes for it", { skip: PYTHON ? false : "python3 not installed on this machine" }, () => {
  const key = newKey();
  const p = "/srv/notes-api/figs/a b+c.png";
  const e = encodeURIComponent(p);
  const authored = [
    "/file?path=" + e + "&sid=" + SID,
    "http://romp.test/file?path=" + e + "&sid=" + SID + "&download=1",
    "/file?path=/srv/notes-api/figs/a+b%2Bc.png&sid=" + SID,          // + is a space, %2B a plus, to both readers
    "/file?path=&path=" + e + "&sid=" + SID,                         // a blank first value: parse_qs drops it
    "/file?sid=" + SID + "&path=" + e + "#frag",
    "/file?path=" + e + "&cap=stale-value-from-elsewhere",            // an author's own cap is replaced
    "/remote/TESTHOST/file?path=" + e + "&sid=" + SID,
    "/remote/h%C3%B4te/file?path=%2Ftmp%2F%D1%84.png",
    "/file?path=%E9&sid=" + SID,                                     // invalid UTF-8: U+FFFD to both readers
    "/file?path=" + e + "&pin=abc123.png",
  ];
  const out = withPage(key, () => authored.map((u) => withFileCap(u)));
  out.forEach((u, i) => assert.notEqual(u, authored[i], "capped: " + authored[i]));
  const read = kernelReads(key, [], out.map((u) => "http://romp.test" + u));
  read.urls.forEach(([need, ok], i) => {
    assert.equal(need, "file", authored[i]);
    assert.ok(ok, "the kernel reads a valid cap in the capped form of: " + authored[i]);
  });
});

// ── 4. placement ─────────────────────────────────────────────────────────────────────────────────────────
test("with no page key there is no cap and every URL is exactly what it was (the VS Code webview, a page before sign-in)", () => {
  withPage("", () => {
    assert.equal(fileCap("", "/tmp/a.png", SID), "");
    assert.equal(previewFileUrl("/tmp/a b.png", SID), "/file?path=%2Ftmp%2Fa%20b.png&sid=" + SID);
    assert.equal(previewFileUrl("/tmp/a.png", "TESTHOST:" + SID), "/remote/TESTHOST/file?path=%2Ftmp%2Fa.png&sid=" + SID);
    assert.equal(previewFileUrl("plots/figure.png"), "/file?path=plots%2Ffigure.png");
    assert.equal(cardFileUrl("/tmp/a.png", SID), "/file?path=%2Ftmp%2Fa.png&sid=" + SID);
    assert.equal(cardFileUrl("/tmp/a.png", "TESTHOST:" + SID), "/remote/TESTHOST/file?path=%2Ftmp%2Fa.png&sid=" + SID);
    for (const u of ["/file?path=%2Ftmp%2Fa.png", "/remote/TESTHOST/file?path=x"]) assert.equal(withFileCap(u), u);
  });
  const g: any = globalThis;
  assert.ok(!("window" in g) || g.window === undefined || !g.window.__rompPageKey, "the harness leaves no key behind");
  assert.equal(fileCap("", "/tmp/a.png", SID), "", "no window at all: no cap, no throw");
});

test("with a page key both fileUrl builders append the cap for the host, path and bare sid, and only that", () => {
  const key = newKey();
  withPage(key, () => {
    for (const [p, s, host, bare, base] of [
      ["/tmp/a b.png", SID, "", SID, "/file"],
      ["/tmp/a.png", "TESTHOST:" + SID, "TESTHOST", SID, "/remote/TESTHOST/file"],
      ["plots/figure.png", null, "", "", "/file"],
    ] as [string, string | null, string, string, string][]) {
      const want = base + "?path=" + encodeURIComponent(p) + (bare ? "&sid=" + bare : "") + "&cap=" + capFor(key, host, p, bare);
      assert.equal(previewFileUrl(p, s), want, "preview.ts fileUrl: " + p);
      assert.equal(cardFileUrl(p, s), want, "file-preview.ts fileUrl: " + p);
    }
    const a = previewFileUrl("/tmp/a.png", SID), b = previewFileUrl("/tmp/b.png", SID);
    assert.notEqual(new URLSearchParams(a.split("?")[1]).get("cap"), new URLSearchParams(b.split("?")[1]).get("cap"), "a cap per file");
  });
  const other = newKey();
  const c1 = withPage(key, () => fileCap("", "/tmp/a.png", SID)), c2 = withPage(other, () => fileCap("", "/tmp/a.png", SID));
  assert.notEqual(c1, c2, "another key (another sign-in) gets another cap: the memo follows the key");
  assert.equal(withPage(key, () => fileCap("", "/tmp/a.png", SID)), c1, "and the first key's cap again after");
});

test("the page reads its key only through window.__rompPageKey: no ui/ source names a storage slot of its own", () => {
  // the kernel keys the slot by its own cookie name (kernel.py _PAGE_KEY_SLOT), so two kernels on one host keep two keys;
  // a page module that read a fixed slot would read another kernel's key, or none
  const UI_ROOT = path.join(ROOT, "ui");
  const hits: string[] = [];
  const walk = (dir: string) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { if (e.name !== "node_modules") walk(p); continue; }
      if (/\.(ts|js|mjs)$/.test(e.name) && !/\.test\.(ts|js|mjs)$/.test(e.name) && fs.readFileSync(p, "utf8").includes("romp.pageKey")) hits.push(path.relative(ROOT, p));
    }
  };
  walk(UI_ROOT);
  assert.deepEqual(hits, [], "no page module names the key's storage slot");
  assert.match(KERNEL, /_PAGE_KEY_SLOT = "romp\.pageKey\." \+ _SESSION_COOKIE/, "the kernel keys the slot by its cookie name, the name this pin keeps the page from hard-coding");
});

test("withFileCap leaves every URL that is not this origin's /file or /remote/<host>/file route unchanged", () => {
  const key = newKey();
  withPage(key, () => {
    for (const u of [
      "https://example.invalid/file?path=x", "//example.invalid/file?path=x", "http://romp.test:8080/file?path=x",
      "/files?path=x", "/filex?path=x", "/file/?path=x", "/remote/TESTHOST/files?path=x", "/remote/a/b/file?path=x",
      "/remote//file?path=x", "/remote/%E0%A4/file?path=x", "plots/figure.png", "/media/romp-swirl-glyph.svg",
      "data:image/png;base64,AAAA", "javascript:alert(1)", "#section",
    ]) assert.equal(withFileCap(u), u, u);
    assert.match(withFileCap("/file?path=x"), /^\/file\?path=x&cap=[A-Za-z0-9_-]{22}$/, "a 16-byte cap, base64url, no padding");
  });
});
