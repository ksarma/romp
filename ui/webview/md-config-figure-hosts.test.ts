// The Slice 4 review, round 1 (plans/markdown-viewer.md decision 8): an entry of the gear's figureHosts list reaches the
// gate as a host name its reader can equal. The reader (figure-gate.ts remoteHost) gives a source's URL.hostname; the
// normaliser (settings.ts figureHosts, gear.js figureHostList) used to keep a line as typed, so `https://cdn.test`,
// `cdn.test:8080`, `bücher.test` or `127.000.000.001` in the gear gated the very host it named, with no sign anywhere.
// Pure, under node: the store, the allowed set and the reader; the gear's own copy of the normaliser is held equal to
// settings.ts's in gear-figure-hosts.test.ts, and the DOM half runs in file-view-figures-gate-browser.test.ts.
import { test } from "node:test";
import * as assert from "node:assert/strict";

// localStorage before the settings module is read (settings.ts reads it at call time)
const store: Record<string, string> = {};
(globalThis as any).localStorage = {
  getItem: (k: string) => (k in store ? store[k] : null),
  setItem: (k: string, v: string) => { store[k] = v; },
  removeItem: (k: string) => { delete store[k]; },
};
import { allowedFigureHosts, remoteHost, forgetLoadedHosts } from "./figure-gate";
import { figureHostName } from "./settings";

const BASE = "http://romp.test/files";

test("an entry typed as an address, with a port, a path, an IDN, a leading-zero IPv4, a bracketed IPv6 or a protocol-relative URL allows the host it names", () => {
  forgetLoadedHosts();
  const typed = ["https://cdn.test", "cdn2.test/", "cdn3.test:8080", "bücher.test", "127.000.000.001", "[::1]", "//proto.test/x"];
  const srcs = ["https://cdn.test/x.png", "https://cdn2.test/x.png", "http://cdn3.test:8080/x.png", "https://bücher.test/x.png", "http://127.000.000.001/y.png", "http://[::1]/z.png", "https://proto.test/x.png"];
  store["romp:settings"] = JSON.stringify({ figureHosts: typed });
  const allowed = allowedFigureHosts();
  for (let i = 0; i < srcs.length; i++) {
    const h = remoteHost(srcs[i], BASE);
    assert.ok(h, srcs[i]);
    assert.ok(allowed.has(h as string), srcs[i] + " reads as " + h + ", absent from " + JSON.stringify([...allowed]));
    assert.equal(figureHostName(typed[i]), h, "the setting's spelling is the reader's");
  }
  assert.deepEqual([...allowed].sort(), ["127.0.0.1", "[::1]", "cdn.test", "cdn2.test", "cdn3.test", "proto.test", "xn--bcher-kva.test"]);
  delete store["romp:settings"];
});

test("an entry the URL parser refuses is kept for the gear to name, and allows nothing: no source ever reads as such a host", () => {
  forgetLoadedHosts();
  store["romp:settings"] = JSON.stringify({ figureHosts: ["[bad", "x^y.test", "github.com"] });
  const allowed = allowedFigureHosts();
  assert.ok(allowed.has("github.com"));
  assert.ok(allowed.has("[bad") && allowed.has("x^y.test"), "kept as typed");
  assert.equal(figureHostName("[bad"), null);
  assert.equal(figureHostName("x^y.test"), null);
  assert.equal(remoteHost("http://[bad/x.png", BASE), null, "the reader refuses the same URL, so the entry matches no figure");
  assert.equal(remoteHost("http://x^y.test/x.png", BASE), null);
  delete store["romp:settings"];
});
