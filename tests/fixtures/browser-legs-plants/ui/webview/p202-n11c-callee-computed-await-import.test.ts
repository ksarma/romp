import { test } from "node:test";
test("p202", async () => { const b = await (await import("playwright"))[process.env.K as string](); await b.close(); });
