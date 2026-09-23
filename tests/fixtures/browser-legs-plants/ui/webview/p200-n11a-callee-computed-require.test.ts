import { test } from "node:test";
test("p200", async () => { const b = await require("playwright")[process.env.K as string](); await b.close(); });
