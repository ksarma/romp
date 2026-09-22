import { test } from "node:test";
test("p113", async () => { const b = await (await import("playwright"))[process.env.ENGINE as string].launch(); await b.close(); });
