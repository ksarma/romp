// The relay dial to /remote/<host>/ws carries the page key as k=, the socket class's credential on this kernel's origin
// (remoteDialUrl, from the kernel's page-key script's window.__rompKeyQ). The hub reads it and drops it before it dials
// the peer with that host's own credential. Pinned on the wire against the real FederationManager with a fake WebSocket,
// on the first dial and on a redial, and without the page-key script (the dial as it was, no k=). Synthetic only: host
// TESTHOST, placeholder uuids, a key minted at run time.
import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { FederationManager, REMOTE_REDIAL_MS } from "./federation";

const SID = "11111111-2222-3333-4444-555555555555";
const PAGE_IID = "PAGEIID-0001";

class FakeWS {
  static made: FakeWS[] = [];
  readyState = 0;
  sent: any[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: any) => void) | null = null;
  onclose: ((ev: any) => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public url: string) { FakeWS.made.push(this); }
  send(d: string): void { try { this.sent.push(JSON.parse(d)); } catch (e) { this.sent.push(d); } }
  open(): void { this.readyState = 1; this.onopen && this.onopen(); }
  close(): void { this.readyState = 3; }
}

let clock = 1_000_000_000;

async function withManager(keyQ: (() => string) | null, fn: (fm: any) => void): Promise<void> {
  const g: any = globalThis;
  const saved: Record<string, any> = {};
  const set = (k: string, v: any) => { saved[k] = { had: k in g, v: g[k] }; g[k] = v; };
  FakeWS.made = [];
  const realNow = Date.now;
  Date.now = () => clock;
  set("WebSocket", FakeWS);
  set("location", { protocol: "http:", host: "hub.local:1", search: "?wid=hublab" });
  set("localStorage", { getItem: () => null, setItem: () => {} });
  const win: any = {
    dispatchEvent: () => {},
    __rompLocalSend: () => {},
    __rompDialTerms: () => ({ app: "chat", iid: PAGE_IID, active: "TESTHOST:" + SID, col: "", skeleton: 1, provrows: 0, proto: 2, delta: 1 }),
    sessionStorage: { getItem: () => "" },
    parent: { postMessage: () => {} },
  };
  if (keyQ) win.__rompKeyQ = keyQ;
  set("window", win);
  try { fn(new FederationManager()); }
  finally {
    Date.now = realNow;
    for (const [k, r] of Object.entries(saved)) { if (r.had) g[k] = r.v; else delete g[k]; }
  }
}

const qOf = (url: string): URLSearchParams => new URLSearchParams(url.split("?")[1] || "");

test("the relay dial carries the page key as k=, on the first dial and on a redial", async () => {
  const key = randomBytes(32).toString("base64url");
  await withManager(() => "&k=" + encodeURIComponent(key), (fm) => {
    fm.outbound({ type: "ready", proto: 2 });
    fm.openRemote("TESTHOST", true);
    assert.equal(FakeWS.made.length, 1);
    assert.ok(FakeWS.made[0].url.includes("/remote/TESTHOST/ws?"), "the relay route");
    assert.equal(qOf(FakeWS.made[0].url).get("k"), key, "the first dial's k= is the stored page key");
    assert.equal(qOf(FakeWS.made[0].url).getAll("k").length, 1, "once");
    FakeWS.made[0].readyState = 3;
    clock += REMOTE_REDIAL_MS + 1000;
    fm.watchdog(clock);
    assert.equal(FakeWS.made.length, 2, "the watchdog redialed");
    assert.equal(qOf(FakeWS.made[1].url).get("k"), key, "the redial carries the key too (the URL is rebuilt per dial)");
    fm.conns.get("TESTHOST").closed = true;
  });
});

test("a page with no key, or no page-key script, dials as it did: no k=", async () => {
  await withManager(() => "", (fm) => {
    fm.openRemote("TESTHOST", true);
    assert.equal(qOf(FakeWS.made[0].url).get("k"), null, "the script found no stored key");
    fm.conns.get("TESTHOST").closed = true;
  });
  await withManager(null, (fm) => {
    fm.openRemote("TESTHOST", true);
    assert.equal(qOf(FakeWS.made[0].url).get("k"), null, "no page-key script at all");
    assert.equal(qOf(FakeWS.made[0].url).get("app"), "chat", "and the rest of the dial is unchanged");
    fm.conns.get("TESTHOST").closed = true;
  });
});
