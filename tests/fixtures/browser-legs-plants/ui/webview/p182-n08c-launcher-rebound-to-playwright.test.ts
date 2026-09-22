import { test } from "node:test";
let leg: any = require("./real-viewer-leg");
leg = require("playwright");
test("p182", async () => { const b = await leg.firefox.launch(); await b.close(); });
