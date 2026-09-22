import { test } from "node:test";
test("p94", async () => { const b = await require("./real-viewer-leg").requireCjs("playwright").firefox.launch(); await b.close(); });
