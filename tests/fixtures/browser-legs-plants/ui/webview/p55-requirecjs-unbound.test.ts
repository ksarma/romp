import { test } from "node:test";
import { requireCjs } from "./real-viewer-leg";
test("p55", async () => { const b = await requireCjs("playwright").chromium.launch(); await b.close(); });
