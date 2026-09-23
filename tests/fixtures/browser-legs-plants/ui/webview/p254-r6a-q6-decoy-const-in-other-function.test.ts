import { test } from "node:test";
function other(): string { const spec = "./decoy-helper"; return spec; }
const PW = "playwright";
function load(spec: string): any { return require(spec); }
const pw = load(PW);
test("p254", async () => { void other(); const b = await pw.firefox.launch(); await b.close(); });
