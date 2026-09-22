import { test } from "node:test";
import leg from "./real-viewer-leg";
test("p90", async () => { const b = await leg.requireCjs("playwright").firefox.launch(); await b.close(); });
