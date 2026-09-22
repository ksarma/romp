import { test } from "node:test";
test("p92", async () => { const { requireCjs } = await import("./real-viewer-leg"); const b = await requireCjs("playwright").webkit.launch(); await b.close(); });
