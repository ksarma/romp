import { test } from "node:test";
test("p95", async () => { const b = await (await import("./real-viewer-leg")).requireCjs("playwright").webkit.launch(); await b.close(); });
