import { test } from "node:test";
test("p12", async (t) => { const { inBrowser } = await import("./real-viewer-leg"); await inBrowser(t, async () => {}); });
