import { test } from "node:test";
function load(s: string): any { return s; }
const name = "playwright";
test("p333", async () => { const b = await load(name).firefox.launch(); await b.close(); });
