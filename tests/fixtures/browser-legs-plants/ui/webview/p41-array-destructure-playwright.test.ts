import { test } from "node:test";
const pw = require("playwright");
const [eng] = pw;
test("p41", async () => { const b = await eng.launch(); await b.close(); });
