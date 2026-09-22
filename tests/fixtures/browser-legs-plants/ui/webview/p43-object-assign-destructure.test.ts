import { test } from "node:test";
const pw = require("playwright");
let chromium: any;
({ chromium } = pw);
test("p43", async () => { const b = await chromium.launch(); await b.close(); });
