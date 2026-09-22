import { test } from "node:test";
test("p48", async () => { const b = await require("playwright").chromium.launch(); await b.close(); });
