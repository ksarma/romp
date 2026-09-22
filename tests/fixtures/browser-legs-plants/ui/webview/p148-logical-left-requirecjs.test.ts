import { test } from "node:test";
import { requireCjs } from "./real-viewer-leg";
const r = requireCjs ?? null;
test("p148", async () => { const b = await r("playwright").firefox.launch(); await b.close(); });
