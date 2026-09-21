import { test } from "node:test";
const pw = require("playwright");
test("p15a", async () => { const b = await pw[process.env.ENGINE as string].launch(); await b.close(); });
