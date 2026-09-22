import { test } from "node:test";
test("p186", async () => { const b = await require`playwright`.firefox.launch(); await b.close(); });
