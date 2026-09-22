import { test } from "node:test";
const { requireCjs } = require("./real-viewer-leg");
test("p91", async () => { const b = await requireCjs("playwright").firefox.launch(); await b.close(); });
