import { test } from "node:test";
test("p164", async () => { const b = await module.require("playwright").firefox.launch(); await b.close(); });
