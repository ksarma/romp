import { test } from "node:test";
test("p278", async () => { const b = await (await import("playwright")).firefox.launch(); await b.close(); });
