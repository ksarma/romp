import { test } from "node:test";
import { requireCjs } from "./real-viewer-leg";
const r = requireCjs;
test("p97", async () => { const b = await r("playwright").firefox.launch(); await b.close(); });
